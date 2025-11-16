# Smoke Testing Best Practices
# Literature Review Pipeline - Comprehensive Guide

**Version:** 1.0  
**Effective Date:** November 15, 2025  
**Audience:** Developers, QA Engineers, DevOps  
**Based On:** Production smoke test experience (Nov 14-15, 2025)

---

## Table of Contents

1. [Introduction](#introduction)
2. [Pre-Test Preparation](#pre-test-preparation)
3. [Test Execution Strategy](#test-execution-strategy)
4. [Debugging Methodology](#debugging-methodology)
5. [Checkpoint Validation](#checkpoint-validation)
6. [Performance Testing](#performance-testing)
7. [Output Verification](#output-verification)
8. [Documentation Standards](#documentation-standards)
9. [Lessons Learned](#lessons-learned)
10. [Test Checklist](#test-checklist)

---

## Introduction

### Purpose of This Guide

This document captures best practices learned from comprehensive E2E smoke testing of the Literature Review Pipeline. It provides a systematic approach to validating complex AI-driven systems with multiple stages, external API dependencies, and checkpoint mechanisms.

### When to Use Smoke Testing

**Always:**
- After major refactoring or architectural changes
- Before production deployment
- After dependency upgrades (especially AI SDKs)
- When integrating new pipeline stages

**Consider:**
- After bug fixes affecting multiple components
- When adding new configuration options
- Before performance optimization work

### Success Criteria

A successful smoke test validates:
- ✅ All pipeline stages execute without crashes
- ✅ Checkpoints save and resume correctly
- ✅ API rate limiting prevents quota violations
- ✅ Error handling degrades gracefully
- ✅ Outputs match expected format and content
- ✅ Performance meets acceptable thresholds

---

## Pre-Test Preparation

### 1. Environment Setup

**Create Isolated Test Environment:**
```bash
# Use dedicated branch
git checkout -b smoke-test-$(date +%Y%m%d)

# Fresh virtual environment
python3 -m venv venv-smoke-test
source venv-smoke-test/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Verify Python version
python --version  # Should be 3.12+
```

**Environment Variables:**
```bash
# API credentials (use test account if available)
export GEMINI_API_KEY="test-key-with-quota"

# Optional: Separate test workspace
export TEST_DATA_DIR="/tmp/smoke-test-data"
```

### 2. Test Data Preparation

**Small Representative Dataset:**
- **Papers:** 5-10 PDFs covering diverse topics
- **Size:** Mix of small (5 pages) and large (50+ pages)
- **Quality:** Include both high-quality and edge cases

**Example Test Set:**
```
data/raw/Research-Papers/
├── high_quality_experimental.pdf    # Gold standard paper
├── low_quality_opinion.pdf          # Should score low
├── theoretical_framework.pdf        # Edge case: no experiments
├── malformed_text.pdf              # PDF parsing challenge
└── multi_topic_survey.pdf          # Tests claim extraction
```

**Why This Matters:**
- Small corpus = faster iteration during debugging
- Diverse quality = validates scoring logic
- Edge cases = exposes hidden bugs

### 3. Baseline Configuration

**Create Test Configuration:**
```json
// pipeline_config.test.json
{
  "version": "2.0.0-test",
  "retry_policies": {
    "max_attempts": 2,        // Faster failure for testing
    "base_delay": 2,          // Shorter delays
    "exponential_backoff": true,
    "jitter": false           // Deterministic for debugging
  },
  "circuit_breaker": {
    "failure_threshold": 2,   // Lower threshold
    "reset_timeout": 30
  }
}
```

**Orchestrator Test Settings:**
```python
# In orchestrator.py or via config file
TEST_CONFIG = {
    "ENABLE_SEMANTIC_SEARCH": False,  # Start with performance mode
    "MAX_ITERATIONS": 2,              # Limit convergence loops
    "VERBOSE_LOGGING": True,          # Extra debug output
    "SAVE_INTERMEDIATE": True         // Keep all temp files
}
```

### 4. Pre-Flight Checks

**Automated Validation Script:**
```bash
#!/bin/bash
# pre_smoke_test.sh

echo "🔍 Pre-Smoke Test Validation"

# Check Python version
python --version | grep -q "3.12" || { echo "❌ Python 3.12 required"; exit 1; }

# Check dependencies
python -c "from google import genai" 2>/dev/null || { echo "❌ google-genai not installed"; exit 1; }
python -c "from sentence_transformers import SentenceTransformer" 2>/dev/null || { echo "❌ sentence-transformers missing"; exit 1; }

# Check API key
[ -n "$GEMINI_API_KEY" ] || { echo "❌ GEMINI_API_KEY not set"; exit 1; }

# Check test data
[ -d "data/raw/Research-Papers" ] || { echo "❌ Papers directory missing"; exit 1; }
paper_count=$(find data/raw/Research-Papers -name "*.pdf" | wc -l)
[ "$paper_count" -ge 5 ] || { echo "⚠️  Only $paper_count papers (recommend 5+)"; }

# Check config files
[ -f "pipeline_config.json" ] || { echo "❌ pipeline_config.json missing"; exit 1; }
[ -f "pillar_definitions.json" ] || { echo "❌ pillar_definitions.json missing"; exit 1; }

echo "✅ All pre-flight checks passed"
echo "📊 Test corpus: $paper_count papers"
```

---

## Test Execution Strategy

### 1. Incremental Testing Approach

**Phase 1: Individual Stages (Isolation Testing)**

```bash
# Test each stage independently before E2E
# Stage 1: Judge
python -m literature_review.analysis.judge
echo "Exit code: $?"  # Should be 0

# Verify outputs
[ -f "data/review_version_history.json" ] || echo "❌ Version history not created"
grep -q "approved" data/review_version_history.json || echo "⚠️  No approved claims"

# Stage 2: DRA (requires Judge output)
# python -m literature_review.analysis.dra  # If standalone entry point exists

# Stage 3: Gap Analysis
python -m literature_review.orchestrator --skip-judge
```

**Why Incremental:**
- Isolates bugs to specific stages
- Faster debug cycles (don't wait for full E2E)
- Validates handoff data structures

**Phase 2: End-to-End (Integration Testing)**

```bash
# Full pipeline with monitoring
timeout 600 python -m literature_review.orchestrator 2>&1 | tee /tmp/smoke_test_$(date +%Y%m%d_%H%M%S).log

# Check exit code
if [ $? -eq 0 ]; then
    echo "✅ Pipeline completed successfully"
else
    echo "❌ Pipeline failed or timed out"
    # Analyze logs for root cause
fi
```

**Timeout Rationale:**
- 600 seconds (10 min) for 5-10 papers
- Prevents infinite hangs
- Adjust based on corpus size

### 2. Logging Strategy

**Multi-Level Logging:**
```python
# In each module, use structured logging
import logging

# Main pipeline log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('smoke_test_main.log'),
        logging.StreamHandler()  # Also print to console
    ]
)

# Stage-specific logs
stage_logger = logging.getLogger('judge')
stage_handler = logging.FileHandler('smoke_test_judge.log')
stage_logger.addHandler(stage_handler)
```

**What to Log:**
- ✅ Stage entry/exit with timestamps
- ✅ API call counts and response times
- ✅ Checkpoint save/load events
- ✅ Error categorization (rate limit vs validation vs network)
- ✅ Resource usage (memory, CPU spikes)
- ❌ Avoid logging sensitive data (API keys, full paper text)

**Log Parsing Tips:**
```bash
# Extract all errors
grep "ERROR" smoke_test_main.log > errors_only.log

# Count API calls by endpoint
grep "HTTP Request" smoke_test_main.log | grep -oP "POST.*generateContent" | wc -l

# Find performance bottlenecks
grep -E "(Stage.*complete|took [0-9]+ seconds)" smoke_test_main.log

# Track checkpoint events
grep -i "checkpoint" smoke_test_main.log
```

### 3. Parallel vs Sequential Testing

**When to Test Sequentially:**
- First run of a new feature
- Debugging crashes or data corruption
- Validating exact execution order

**When to Test in Parallel:**
- Batch validation of different configurations
- Performance benchmarking
- Testing with multiple API keys (quota distribution)

**Parallel Testing Example:**
```bash
# Test 3 configurations simultaneously
(cd /tmp/test1 && ENABLE_SEMANTIC_SEARCH=True python -m literature_review.orchestrator) &
(cd /tmp/test2 && ENABLE_SEMANTIC_SEARCH=False python -m literature_review.orchestrator) &
(cd /tmp/test3 && MAX_ITERATIONS=1 python -m literature_review.orchestrator) &

wait  # Wait for all to complete
```

**⚠️ Warning:** Respect API rate limits when parallelizing!

---

## Debugging Methodology

### 1. Systematic Bug Isolation

**When a Test Fails:**

**Step 1: Identify Failure Point**
```bash
# Check last successful log entry
tail -20 smoke_test_main.log

# Find the exact error
grep -A 5 "ERROR\|Exception\|Traceback" smoke_test_main.log
```

**Step 2: Reproduce Minimally**
```bash
# Reduce to smallest failing case
# Example: If judge fails on claim 52/57
# Extract just that claim and test in isolation

python -c "
import json
with open('data/review_version_history.json') as f:
    data = json.load(f)
    # Extract claim 52
    claim = data['papers']['specific_paper.pdf']['claims'][51]
    # Test just this claim
"
```

**Step 3: Add Instrumentation**
```python
# Add debug prints around suspected code
def process_claim(claim):
    print(f"DEBUG: Claim ID = {claim.get('claim_id')}")
    print(f"DEBUG: Claim text length = {len(claim.get('claim_text', ''))}")
    
    result = ai_call(claim)
    
    print(f"DEBUG: AI response type = {type(result)}")
    print(f"DEBUG: AI response keys = {result.keys() if isinstance(result, dict) else 'N/A'}")
    
    return result
```

**Step 4: Bisect History**
```bash
# If test worked before, find breaking commit
git bisect start
git bisect bad HEAD          # Current broken state
git bisect good v1.0         # Last known good version
# Git will checkout middle commit, test, then:
git bisect good/bad  # Repeat until found
```

### 2. Common Bug Patterns from Nov 14-15 Testing

**Pattern 1: Argument Mismatches**
```python
# Symptom: TypeError: run_analysis() takes 2 positional arguments but 3 were given
# Root Cause: Function signature changed but caller not updated

# How to Find:
grep -n "run_analysis" literature_review/**/*.py
# Check all call sites match definition

# Fix:
def run_analysis(claims, api_manager):  # Removed 3rd param
    pass
```

**Pattern 2: Tuple Unpacking Errors**
```python
# Symptom: ValueError: not enough values to unpack (expected 2, got 1)
# Root Cause: Function returns single value, caller expects tuple

# How to Find:
# Add logging before unpacking
result = some_function()
print(f"DEBUG: Result type = {type(result)}, value = {result}")
category, reason = result  # Will crash here if single value

# Fix:
category = categorize_error(error)
reason = str(error)  # Don't unpack
```

**Pattern 3: JSON Schema Validation Failures**
```python
# Symptom: ValidationError: 0.5 is not valid under any of the given schemas
# Root Cause: AI returns valid but unexpected values

# How to Find:
# Log raw AI responses
logger.debug(f"Raw AI response: {response_text}")

# Fix: Update schema to match reality
composite_score: float  # Range (0, 5) instead of (1, 5)
```

**Pattern 4: Missing Dictionary Keys**
```python
# Symptom: KeyError: 'requirements'
# Root Cause: Iterating over mixed data structures

# How to Find:
for key in data.keys():
    print(f"DEBUG: Processing key={key}, type={type(data[key])}")
    # Will show which key doesn't have 'requirements'

# Fix: Filter before iteration
metadata_sections = ['Framework_Overview', 'Cross_Cutting_Requirements']
analyzable_pillars = [k for k in data.keys() if k not in metadata_sections]
```

### 3. API Debugging

**Rate Limit Analysis:**
```bash
# Extract API timing
grep "HTTP Request" smoke_test_main.log | awk '{print $1, $2}' > api_timestamps.txt

# Calculate RPM
python3 << EOF
from datetime import datetime
with open('api_timestamps.txt') as f:
    times = [datetime.strptime(line.split()[0] + ' ' + line.split()[1], '%Y-%m-%d %H:%M:%S,%f') for line in f]
    
if len(times) > 1:
    duration_min = (times[-1] - times[0]).total_seconds() / 60
    rpm = len(times) / duration_min
    print(f"Average RPM: {rpm:.2f}")
    print(f"Max safe RPM: 10")
    print(f"Status: {'⚠️ OVER LIMIT' if rpm > 10 else '✅ OK'}")
EOF
```

**Malformed Response Debugging:**
```python
# Save all AI responses for inspection
import json

def call_ai_with_logging(prompt):
    response = ai_client.generate(prompt)
    
    # Save raw response
    with open(f'/tmp/ai_response_{uuid.uuid4()}.json', 'w') as f:
        f.write(response.text)
    
    try:
        parsed = json.loads(response.text)
        return parsed
    except json.JSONDecodeError as e:
        # Try repair
        repaired = response.text.replace('""', '"')
        try:
            return json.loads(repaired)
        except:
            logger.error(f"Unfixable JSON: {response.text[:200]}")
            raise
```

### 4. Performance Profiling

**CPU Profiling:**
```bash
# Use cProfile for detailed analysis
python -m cProfile -o smoke_test.prof -m literature_review.orchestrator

# Analyze results
python -c "
import pstats
p = pstats.Stats('smoke_test.prof')
p.sort_stats('cumulative')
p.print_stats(20)  # Top 20 time consumers
"
```

**Memory Profiling:**
```bash
# Install memory profiler
pip install memory_profiler

# Add @profile decorator to suspect functions
# Run with:
python -m memory_profiler literature_review/orchestrator.py
```

**Identify Bottlenecks:**
```python
import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        if duration > 5:  # Log slow functions
            logger.warning(f"{func.__name__} took {duration:.2f}s (SLOW)")
        else:
            logger.info(f"{func.__name__} took {duration:.2f}s")
        
        return result
    return wrapper

# Apply to suspect functions
@timing_decorator
def analyze_gap():
    pass
```

---

## Checkpoint Validation

### 1. Testing Checkpoint Integrity

**Checkpoint Save Test:**
```bash
# Run pipeline until first checkpoint
timeout 60 python -m literature_review.analysis.judge

# Verify checkpoint created
[ -f "data/review_version_history.json" ] || echo "❌ Checkpoint not saved"

# Check file size (should be > 1KB for real data)
size=$(stat -f%z "data/review_version_history.json" 2>/dev/null || stat -c%s "data/review_version_history.json")
[ "$size" -gt 1000 ] || echo "⚠️  Checkpoint suspiciously small: $size bytes"

# Validate JSON structure
jq empty data/review_version_history.json || echo "❌ Invalid JSON in checkpoint"
```

**Checkpoint Resume Test:**
```bash
# Save current state
cp data/review_version_history.json /tmp/checkpoint_backup.json

# Simulate crash mid-pipeline
# Option 1: Kill process
python -m literature_review.orchestrator &
PID=$!
sleep 30  # Let it run partially
kill -9 $PID

# Option 2: Inject controlled crash
# (Add raise Exception("TEST CRASH") at specific line)

# Verify checkpoint still intact
jq empty data/review_version_history.json || echo "❌ Checkpoint corrupted by crash"

# Resume pipeline
python -m literature_review.orchestrator

# Verify no data loss
diff <(jq -S . /tmp/checkpoint_backup.json) <(jq -S . data/review_version_history.json) || echo "Some data changed (expected for append)"
```

### 2. Checkpoint Recovery Scenarios

**Scenario 1: Corrupted Checkpoint**
```python
# Test recovery from malformed JSON
import json

# Intentionally corrupt
with open('data/review_version_history.json', 'w') as f:
    f.write('{"incomplete": ')  # Missing closing brace

# Pipeline should detect and either:
# 1. Restore from backup (.bak file)
# 2. Start fresh with warning
# 3. Fail gracefully with clear error

python -m literature_review.orchestrator
# Expected: "WARNING: Checkpoint corrupted, using backup from ..."
```

**Scenario 2: Missing Checkpoint**
```bash
# Delete checkpoint mid-run
rm data/review_version_history.json

# Pipeline should:
# 1. Detect missing checkpoint
# 2. Start from beginning
# 3. Log warning (not error)

python -m literature_review.orchestrator 2>&1 | grep -i "checkpoint.*not found"
# Expected: "INFO: No checkpoint found, starting fresh analysis"
```

**Scenario 3: Partial Checkpoint**
```python
# Test interrupted write
import json

with open('data/review_version_history.json', 'r+') as f:
    data = json.load(f)
    # Remove last claim (simulate interrupted write)
    if data['papers']:
        first_paper = list(data['papers'].keys())[0]
        if data['papers'][first_paper]['claims']:
            data['papers'][first_paper]['claims'].pop()
    
    f.seek(0)
    json.dump(data, f)
    f.truncate()

# Pipeline should handle gracefully
```

### 3. Checkpoint Performance Impact

**Measure Overhead:**
```python
import time

# Test 1: Without checkpointing
start = time.time()
process_claims_no_checkpoint(claims)
time_no_checkpoint = time.time() - start

# Test 2: With checkpointing every 10 claims
start = time.time()
process_claims_with_checkpoint(claims, batch_size=10)
time_with_checkpoint = time.time() - start

overhead_pct = ((time_with_checkpoint - time_no_checkpoint) / time_no_checkpoint) * 100
print(f"Checkpoint overhead: {overhead_pct:.1f}%")
# Acceptable: < 5%
```

**Expected Results:**
- Batch size 10: ~1-2% overhead (acceptable)
- Batch size 1: ~10-15% overhead (too frequent)
- Batch size 100: ~0.1% overhead but risky (too infrequent)

---

## Performance Testing

### 1. Baseline Metrics

**Establish Performance Baseline:**
```bash
# Run multiple times to get average
for i in {1..3}; do
    echo "Run $i:"
    /usr/bin/time -v python -m literature_review.orchestrator 2>&1 | grep -E "(Elapsed|Maximum resident|User time)"
done

# Example output to record:
# Elapsed time: 180.5 seconds
# Maximum resident set size: 1.2 GB
# User time: 165.3 seconds
```

**Store Baseline:**
```json
// performance_baseline.json
{
  "date": "2025-11-15",
  "configuration": {
    "papers": 7,
    "semantic_search": false,
    "python_version": "3.12.1"
  },
  "metrics": {
    "total_runtime_sec": 180,
    "peak_memory_mb": 1200,
    "api_calls": 104,
    "cpu_time_sec": 165
  }
}
```

### 2. Performance Regression Detection

**Automated Regression Check:**
```python
#!/usr/bin/env python3
# check_performance_regression.py

import json
import time
import psutil
import sys

def run_with_monitoring():
    process = psutil.Process()
    start_time = time.time()
    start_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Run pipeline
    from literature_review.orchestrator import main
    main()
    
    end_time = time.time()
    peak_memory = max([p.memory_info().rss for p in process.children(recursive=True)] + 
                      [process.memory_info().rss]) / 1024 / 1024
    
    return {
        'runtime_sec': end_time - start_time,
        'peak_memory_mb': peak_memory
    }

# Load baseline
with open('performance_baseline.json') as f:
    baseline = json.load(f)

# Run test
results = run_with_monitoring()

# Check for regression
runtime_regression = (results['runtime_sec'] - baseline['metrics']['total_runtime_sec']) / baseline['metrics']['total_runtime_sec']
memory_regression = (results['peak_memory_mb'] - baseline['metrics']['peak_memory_mb']) / baseline['metrics']['peak_memory_mb']

if runtime_regression > 0.20:  # 20% slower
    print(f"❌ RUNTIME REGRESSION: {runtime_regression*100:.1f}% slower")
    sys.exit(1)

if memory_regression > 0.30:  # 30% more memory
    print(f"❌ MEMORY REGRESSION: {memory_regression*100:.1f}% increase")
    sys.exit(1)

print("✅ No performance regression detected")
```

### 3. Scalability Testing

**Test with Increasing Load:**
```bash
# Test 1: Small (5 papers)
echo "Small corpus test..."
cp small_corpus/*.pdf data/raw/Research-Papers/
/usr/bin/time -f "%E elapsed, %M KB max memory" python -m literature_review.orchestrator

# Test 2: Medium (25 papers)
echo "Medium corpus test..."
cp medium_corpus/*.pdf data/raw/Research-Papers/
/usr/bin/time -f "%E elapsed, %M KB max memory" python -m literature_review.orchestrator

# Test 3: Large (100 papers)
echo "Large corpus test..."
cp large_corpus/*.pdf data/raw/Research-Papers/
timeout 1800 /usr/bin/time -f "%E elapsed, %M KB max memory" python -m literature_review.orchestrator

# Plot results
python3 << EOF
import matplotlib.pyplot as plt
data = [
    (5, 180, 1200),    # (papers, runtime_sec, memory_mb)
    (25, 950, 2100),
    (100, 3800, 4500)
]
plt.subplot(1, 2, 1)
plt.plot([d[0] for d in data], [d[1] for d in data], 'o-')
plt.xlabel('Papers')
plt.ylabel('Runtime (sec)')
plt.title('Scalability: Runtime')

plt.subplot(1, 2, 2)
plt.plot([d[0] for d in data], [d[2] for d in data], 'o-')
plt.xlabel('Papers')
plt.ylabel('Memory (MB)')
plt.title('Scalability: Memory')

plt.tight_layout()
plt.savefig('scalability_results.png')
print("Saved to scalability_results.png")
EOF
```

**Expected Scalability Characteristics:**
- Runtime: Should scale sub-linearly (caching helps)
- Memory: Should scale linearly (proportional to claims)
- API Calls: Should scale linearly (one pass per claim)

---

## Output Verification

### 1. Structural Validation

**Automated Output Schema Check:**
```python
#!/usr/bin/env python3
# validate_outputs.py

import json
import os
from jsonschema import validate, ValidationError

# Define expected schemas
ORCHESTRATOR_STATE_SCHEMA = {
    "type": "object",
    "required": ["last_run_timestamp", "last_completed_stage", "previous_results"],
    "properties": {
        "last_run_timestamp": {"type": "string"},
        "last_completed_stage": {"type": "string"},
        "previous_results": {
            "type": "object",
            "patternProperties": {
                "^Pillar \\d+$": {
                    "type": "object",
                    "required": ["completeness"],
                    "properties": {
                        "completeness": {"type": "number", "minimum": 0, "maximum": 100}
                    }
                }
            }
        }
    }
}

DEEP_REVIEW_SCHEMA = {
    "type": "object",
    "patternProperties": {
        "^Pillar \\d+$": {
            "type": "object",
            "patternProperties": {
                "^Sub-": {
                    "type": "object",
                    "required": ["completeness_percent", "gap_analysis"],
                    "properties": {
                        "completeness_percent": {"type": "number"},
                        "gap_analysis": {"type": "string"}
                    }
                }
            }
        }
    }
}

def validate_outputs():
    errors = []
    
    # Check orchestrator state
    if not os.path.exists('orchestrator_state.json'):
        errors.append("Missing: orchestrator_state.json")
    else:
        with open('orchestrator_state.json') as f:
            try:
                data = json.load(f)
                validate(instance=data, schema=ORCHESTRATOR_STATE_SCHEMA)
                print("✅ orchestrator_state.json valid")
            except ValidationError as e:
                errors.append(f"Invalid orchestrator_state.json: {e.message}")
    
    # Check deep review directions
    if not os.path.exists('gap_analysis_output/deep_review_directions.json'):
        errors.append("Missing: deep_review_directions.json")
    else:
        with open('gap_analysis_output/deep_review_directions.json') as f:
            try:
                data = json.load(f)
                validate(instance=data, schema=DEEP_REVIEW_SCHEMA)
                print("✅ deep_review_directions.json valid")
            except ValidationError as e:
                errors.append(f"Invalid deep_review_directions.json: {e.message}")
    
    # Check HTML outputs
    html_files = [f for f in os.listdir('gap_analysis_output/') if f.endswith('.html')]
    if not html_files:
        errors.append("No HTML visualizations generated")
    else:
        print(f"✅ {len(html_files)} HTML visualization(s) generated")
    
    if errors:
        print("\n❌ Output validation failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ All outputs valid")
        return True

if __name__ == '__main__':
    import sys
    sys.exit(0 if validate_outputs() else 1)
```

### 2. Content Validation

**Sanity Checks on Results:**
```python
# Check for unrealistic values
import json

with open('orchestrator_state.json') as f:
    state = json.load(f)

for pillar, data in state['previous_results'].items():
    completeness = data.get('completeness', 0)
    
    # Flag suspicious values
    if completeness < 0 or completeness > 100:
        print(f"❌ {pillar}: Invalid completeness {completeness}%")
    elif completeness == 0:
        print(f"⚠️  {pillar}: 0% completeness (expected for new framework)")
    elif completeness == 100:
        print(f"⚠️  {pillar}: 100% completeness (rare, verify manually)")
    elif completeness > 50:
        print(f"✅ {pillar}: Good coverage ({completeness}%)")
    else:
        print(f"ℹ️  {pillar}: Moderate coverage ({completeness}%)")
```

**Cross-Reference Validation:**
```python
# Ensure consistency between outputs
import json

# Load both outputs
with open('orchestrator_state.json') as f:
    state = json.load(f)

with open('gap_analysis_output/deep_review_directions.json') as f:
    directions = json.load(f)

# Check that all pillars in state have directions
state_pillars = set(state['previous_results'].keys())
direction_pillars = set(directions.keys())

missing = state_pillars - direction_pillars
if missing:
    print(f"❌ Pillars in state but not in directions: {missing}")
else:
    print("✅ All pillars have deep review directions")

# Check that completeness values match
for pillar in state_pillars & direction_pillars:
    state_comp = state['previous_results'][pillar]['completeness']
    # Calculate average from directions
    dir_comps = [sub['completeness_percent'] for sub in directions[pillar].values()]
    avg_comp = sum(dir_comps) / len(dir_comps) if dir_comps else 0
    
    if abs(state_comp - avg_comp) > 5:  # Allow 5% tolerance
        print(f"⚠️  {pillar}: Completeness mismatch (state={state_comp}%, avg={avg_comp}%)")
```

### 3. Regression Testing with Golden Outputs

**Create Golden Output Set:**
```bash
# After validating outputs manually
mkdir -p test_fixtures/golden_outputs/
cp orchestrator_state.json test_fixtures/golden_outputs/
cp gap_analysis_output/deep_review_directions.json test_fixtures/golden_outputs/

# Commit to version control
git add test_fixtures/golden_outputs/
git commit -m "Add golden outputs for regression testing"
```

**Compare Against Golden Outputs:**
```python
#!/usr/bin/env python3
# compare_to_golden.py

import json
import sys

def load_json(path):
    with open(path) as f:
        return json.load(f)

golden_state = load_json('test_fixtures/golden_outputs/orchestrator_state.json')
current_state = load_json('orchestrator_state.json')

# Compare structure (keys should match exactly)
golden_pillars = set(golden_state['previous_results'].keys())
current_pillars = set(current_state['previous_results'].keys())

if golden_pillars != current_pillars:
    print(f"❌ Pillar set changed!")
    print(f"   Golden: {sorted(golden_pillars)}")
    print(f"   Current: {sorted(current_pillars)}")
    sys.exit(1)

# Compare completeness values (allow small variance for AI non-determinism)
for pillar in golden_pillars:
    golden_comp = golden_state['previous_results'][pillar]['completeness']
    current_comp = current_state['previous_results'][pillar]['completeness']
    
    variance = abs(golden_comp - current_comp)
    if variance > 15:  # Allow 15% variance (AI responses vary)
        print(f"⚠️  {pillar}: Significant variance ({variance:.1f}%)")
        print(f"   Golden: {golden_comp}%, Current: {current_comp}%")
    elif variance > 5:
        print(f"ℹ️  {pillar}: Minor variance ({variance:.1f}%)")
    else:
        print(f"✅ {pillar}: Consistent ({variance:.1f}% variance)")

print("\n✅ Output structure matches golden outputs")
```

---

## Documentation Standards

### 1. Test Report Template

**Required Sections:**
```markdown
# Smoke Test Report - [Date]

## Executive Summary
- Status: PASS/FAIL/PARTIAL
- Total Runtime: X minutes
- Bugs Found: X (Y critical, Z minor)
- Production Readiness: YES/NO/CONDITIONAL

## Test Environment
- Python Version: X.Y.Z
- Key Dependencies: package==version
- Test Data: X papers, Y claims

## Test Results
### Stage 1: Judge
- Claims Processed: X/Y
- Approved: X%
- Rejected: Y%
- Errors: Z

[Repeat for each stage]

## Bugs Found
### Bug 1: [Title]
- **Severity:** CRITICAL/HIGH/MEDIUM/LOW
- **Location:** file.py:line
- **Symptom:** Error message or behavior
- **Root Cause:** Explanation
- **Fix:** Code changes made
- **Verification:** How was fix tested

## Performance Metrics
- Baseline: X sec, Y MB
- Current: A sec, B MB
- Delta: +/-C% runtime, +/-D% memory

## Outputs Generated
- orchestrator_state.json (size)
- deep_review_directions.json (size)
- [List all outputs]

## Recommendations
1. [Action item]
2. [Action item]

## Sign-off
- Tester: [Name]
- Date: [Date]
- Approved for Production: YES/NO
```

### 2. Bug Documentation

**Bug Report Format:**
```markdown
## Bug #XXX: [Short Title]

**Reported:** 2025-11-15 14:32 UTC  
**Severity:** CRITICAL  
**Status:** FIXED  

### Description
[2-3 sentence description of the issue]

### Reproduction Steps
1. Run `python -m literature_review.orchestrator`
2. Wait until claim 52/57
3. Observe `TypeError: run_analysis() takes 2 positional arguments but 3 were given`

### Root Cause Analysis
The `run_analysis()` function signature was changed from 3 parameters to 2, but the calling code in `judge.py` line 1195 was not updated.

**Before:**
```python
def run_analysis(claims, api_manager, papers_folder_path):
```

**After:**
```python
def run_analysis(claims, api_manager):
```

**Caller (not updated):**
```python
dra.run_analysis(claims, api_manager, papers_folder_path)  # ERROR: 3 args
```

### Fix
**File:** `literature_review/analysis/judge.py`  
**Line:** 1195  
**Change:**
```python
# Before
dra.run_analysis(claims, api_manager, papers_folder_path)

# After
dra.run_analysis(claims, api_manager)
```

### Verification
```bash
# Test with full pipeline
python -m literature_review.orchestrator
# Result: DRA phase completed successfully, 41 claims processed

# Unit test (if exists)
pytest tests/unit/test_dra.py::test_run_analysis
```

### Lessons Learned
- Always grep for function calls when changing signatures
- Add type hints to catch these at dev time
- Consider adding integration tests for stage handoffs

### Related Issues
- Similar issue in `deep_reviewer.py` (checked, not affected)
```

### 3. Decision Log

**Track Key Decisions During Testing:**
```markdown
# Smoke Test Decision Log

## Decision 1: Disable Semantic Search for Testing
**Date:** 2025-11-15  
**Context:** Pipeline hanging for 180+ seconds in gap analysis phase  
**Options Considered:**
1. Wait it out (timeout at 300 sec)
2. Add GPU acceleration
3. Disable semantic search temporarily

**Decision:** Disable semantic search (`ENABLE_SEMANTIC_SEARCH=False`)  
**Rationale:** 
- Testing focus is on correctness, not accuracy
- GPU not available in test environment
- Can re-enable for production

**Impact:**
- Runtime reduced from 180+ sec to ~3 min total
- Allows completion of E2E test
- May miss some semantic similarity features in gap analysis

**Reversibility:** High (config flag, easy to re-enable)

---

## Decision 2: Set Rate Limit to 10 RPM
**Date:** 2025-11-14  
**Context:** Need to avoid hitting Gemini API free tier quota  
**Options Considered:**
1. 15 RPM (Google's free tier limit)
2. 10 RPM (conservative)
3. 5 RPM (very conservative)

**Decision:** 10 RPM  
**Rationale:**
- Provides safety margin below 15 RPM limit
- Still reasonably fast for testing (104 calls in ~10 min)
- Allows for slight timing variance

**Impact:**
- 7 observed rate limit pauses (expected)
- 0 HTTP 429 errors (success)
- Total API usage: 12/1000 RPM (well under limit)

**Reversibility:** High (config parameter)
```

---

## Lessons Learned

### From November 14-15, 2025 Testing

#### 1. Always Test with Small Data First
**What Happened:** Attempted to process all 7 papers immediately, hit multiple bugs  
**What Should Have Happened:** Start with 1-2 papers to validate basic flow  
**Takeaway:** Incremental complexity saves debugging time

#### 2. Log Everything, Especially API Responses
**What Happened:** JSON parsing errors appeared random until we logged raw responses  
**Discovery:** Gemini AI occasionally returns `""key"` instead of `"key"`  
**Takeaway:** Add extensive logging before parsing external data

#### 3. Checkpoints Are Not Optional
**What Happened:** Pipeline crashed at claim 52/57, lost all progress  
**Impact:** Had to re-run from beginning (10+ minutes wasted)  
**Fix:** Implemented batch checkpointing (every ~10 claims)  
**Takeaway:** Checkpoint frequently in long-running processes

#### 4. Validation Ranges Should Match Reality
**What Happened:** Composite score validation rejected scores < 1.0  
**Discovery:** AI correctly generates scores like 0.5, 0.75 for very poor evidence  
**Fix:** Changed range from (1, 5) to (0, 5)  
**Takeaway:** Don't assume AI output ranges, validate empirically

#### 5. Performance Bottlenecks Hide in Unexpected Places
**What Happened:** Assumed API calls were slow, turned out to be sentence transformer  
**Discovery:** CPU-bound embedding generation took 180+ seconds  
**Fix:** Added config flag to disable semantic search  
**Takeaway:** Profile before optimizing, don't guess

#### 6. Error Handling Is Your Friend
**What Happened:** Tuple unpacking failed when function returned single value  
**Root Cause:** Refactored function but didn't update all call sites  
**Fix:** Changed `category, reason = func()` to `category = func(); reason = str(error)`  
**Takeaway:** Search for all usages when changing return types

#### 7. Metadata Matters
**What Happened:** Gap analysis crashed with `KeyError: 'requirements'`  
**Root Cause:** Framework JSON has metadata sections without requirements  
**Fix:** Filter metadata sections before iteration  
**Takeaway:** Always validate data structure assumptions

#### 8. Rate Limiting Prevents Disasters
**What Happened:** 104 API calls over ~10 minutes, 0 quota errors  
**Success Factor:** Global rate limiter enforced 10 RPM limit  
**Evidence:** 7 pauses observed, perfectly timed  
**Takeaway:** Proactive rate limiting > reactive error handling

---

## Test Checklist

### Pre-Test Checklist

- [ ] Fresh virtual environment created
- [ ] All dependencies installed (`pip install -r requirements-dev.txt`)
- [ ] API key configured (`GEMINI_API_KEY` set)
- [ ] Test data prepared (5-10 PDFs)
- [ ] Baseline configuration saved
- [ ] Old checkpoints cleared or backed up
- [ ] Pre-flight script passes
- [ ] Git branch created for testing

### During Test Checklist

- [ ] Log all stages to separate files
- [ ] Monitor API usage (stay under quota)
- [ ] Take screenshots of errors
- [ ] Save intermediate outputs
- [ ] Document unexpected behaviors immediately
- [ ] Check checkpoint creation after each stage
- [ ] Verify no memory leaks (monitor RAM)
- [ ] Note performance anomalies

### Post-Test Checklist

- [ ] All expected outputs generated
- [ ] Output schemas validated
- [ ] Completeness scores in reasonable range (0-100%)
- [ ] HTML visualizations render correctly
- [ ] Checkpoint resume tested
- [ ] Performance metrics recorded
- [ ] Bugs documented with fixes
- [ ] Smoke test report written
- [ ] Artifacts committed to git
- [ ] Stakeholders notified of results

### Bug Found Checklist

- [ ] Bug title and ID assigned
- [ ] Severity assessed (CRITICAL/HIGH/MEDIUM/LOW)
- [ ] Reproduction steps documented
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Fix verified with test
- [ ] Related code checked for similar issues
- [ ] Unit test added (if applicable)
- [ ] Bug report written

### Production Sign-off Checklist

- [ ] All stages complete end-to-end
- [ ] Zero critical bugs
- [ ] Performance meets baseline (+/-20%)
- [ ] Checkpoints save and resume correctly
- [ ] API usage within quota
- [ ] Error handling graceful
- [ ] Documentation updated
- [ ] Smoke test report approved
- [ ] Deployment plan ready

---

## Appendix: Useful Scripts

### Script 1: Quick Environment Check
```bash
#!/bin/bash
# quick_check.sh - Run before every smoke test

set -e

echo "🔍 Environment Check"
python --version
pip list | grep -E "(google-genai|sentence-transformers)"
[ -n "$GEMINI_API_KEY" ] && echo "✅ API key set" || echo "❌ API key missing"
[ -d "data/raw/Research-Papers" ] && echo "✅ Papers dir exists" || echo "❌ Papers dir missing"
echo "Papers: $(find data/raw/Research-Papers -name '*.pdf' | wc -l)"
echo "✅ Ready to test"
```

### Script 2: Extract Performance Metrics
```bash
#!/bin/bash
# extract_metrics.sh - Parse logs for key metrics

LOG_FILE="${1:-review_pipeline.log}"

echo "📊 Performance Metrics from $LOG_FILE"
echo ""
echo "API Calls:"
grep -c "HTTP Request.*generateContent" "$LOG_FILE" || echo "0"

echo ""
echo "Rate Limit Pauses:"
grep -c "rate limit" "$LOG_FILE" || echo "0"

echo ""
echo "Errors:"
grep -c "ERROR" "$LOG_FILE" || echo "0"

echo ""
echo "Approved Claims:"
grep -c "verdict.*approved" "$LOG_FILE" || echo "0"

echo ""
echo "Runtime:"
START=$(head -1 "$LOG_FILE" | awk '{print $1" "$2}')
END=$(tail -1 "$LOG_FILE" | awk '{print $1" "$2}')
echo "Start: $START"
echo "End: $END"
```

### Script 3: Cleanup Test Artifacts
```bash
#!/bin/bash
# cleanup_test.sh - Reset to clean state

echo "🧹 Cleaning test artifacts..."

rm -f orchestrator_state.json
rm -f data/review_version_history.json
rm -rf gap_analysis_output/
rm -f *.log
rm -f pipeline_checkpoint.json

echo "✅ Clean slate ready"
```

---

**Document Version:** 1.0  
**Last Updated:** November 15, 2025  
**Maintained By:** BootstrapAI QA Team  
**Next Review:** December 15, 2025
