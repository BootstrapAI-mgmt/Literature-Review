# Literature Review Pipeline - User Manual

**Version:** 2.0  
**Last Updated:** November 15, 2025  
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Running the Pipeline](#running-the-pipeline)
5. [Understanding the Outputs](#understanding-the-outputs)
6. [Configuration Guide](#configuration-guide)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Usage](#advanced-usage)
9. [API Reference](#api-reference)

---

## Overview

The Literature Review Pipeline is an AI-powered system that analyzes research papers against a defined knowledge framework, identifies gaps in coverage, and provides recommendations for targeted literature searches.

### Key Features

- **Automated Evidence Extraction**: AI-driven analysis of PDF research papers
- **Multi-Stage Validation**: Judge → DRA → Gap Analysis → Convergence Detection
- **Checkpoint System**: Automatic progress saving for crash recovery
- **Rate Limiting**: Built-in API quota management (10 RPM default)
- **Interactive Outputs**: JSON reports and HTML visualizations
- **Web Dashboard**: Real-time monitoring and visualization (optional)

### Pipeline Stages

```
┌─────────────────┐
│ Source PDFs     │
└────────┬────────┘
         ↓
┌─────────────────┐
│ Judge Reviewer  │ ← Validates claims against pillar definitions
└────────┬────────┘
         ↓
┌─────────────────┐
│ DRA (Appeals)   │ ← Re-evaluates rejected claims
└────────┬────────┘
         ↓
┌─────────────────┐
│ Gap Analysis    │ ← Calculates pillar completeness
└────────┬────────┘
         ↓
┌─────────────────┐
│ Convergence     │ ← Detects if more reviews needed
└────────┬────────┘
         ↓
┌─────────────────┐
│ Deep Review     │ ← Generates targeted search directions
└─────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Google AI API key (Gemini)
- 2GB+ free disk space
- 4GB+ RAM recommended

### 5-Minute Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd Literature-Review

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Set API key
export GEMINI_API_KEY="your-api-key-here"

# 4. Add research papers
cp your-papers/*.pdf data/raw/Research-Papers/

# 5. Run pipeline
python -m literature_review.orchestrator
```

**Expected Output:** Gap analysis JSON, HTML visualizations, and deep review directions in `gap_analysis_output/`

---

## Installation

### Standard Installation

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install core dependencies
pip install -r requirements-dev.txt

# Verify installation
python -c "from google import genai; print('✓ Google AI SDK installed')"
python -c "from sentence_transformers import SentenceTransformer; print('✓ Sentence Transformers installed')"
```

### Docker Installation

```bash
# Build container
docker build -t literature-review .

# Run pipeline
docker run -v $(pwd)/data:/data \
           -e GEMINI_API_KEY="your-key" \
           literature-review
```

### Web Dashboard Installation

```bash
# Install dashboard dependencies
pip install -r requirements-dashboard.txt

# Launch dashboard
bash run_dashboard.sh

# Access at http://localhost:8000
```

---

## Running the Pipeline

### Basic Execution

```bash
# Full pipeline with default settings
python -m literature_review.orchestrator
```

**What happens:**
1. Loads approved claims from `data/review_version_history.json`
2. Analyzes gap coverage across 7 pillars
3. Checks for convergence (< 5% change threshold)
4. Generates deep review directions if gaps exist
5. Saves outputs to `gap_analysis_output/` and `orchestrator_state.json`

### Stage-by-Stage Execution

```bash
# Run only the Judge stage
python -m literature_review.analysis.judge

# Run only Gap Analysis (requires prior Judge run)
python -m literature_review.orchestrator --skip-judge
```

### With Performance Optimization

For faster testing (disables semantic search):

```python
# Edit literature_review/orchestrator.py
ANALYSIS_CONFIG = {
    "ENABLE_SEMANTIC_SEARCH": False,  # Set to False for 10x speed
    # ... other settings
}
```

Then run:
```bash
python -m literature_review.orchestrator
```

**Performance Impact:**
- Enabled: ~180+ seconds per iteration (CPU bottleneck)
- Disabled: ~2-3 minutes total runtime

### Resuming from Checkpoint

The pipeline automatically resumes from the last checkpoint:

```bash
# Pipeline crashed during gap analysis?
# Just re-run - it will pick up from where it left off
python -m literature_review.orchestrator
```

**Checkpoint Files:**
- `data/review_version_history.json` - Judge stage progress
- `orchestrator_state.json` - Gap analysis progress

---

## Understanding the Outputs

### Primary Output Files

#### 1. `orchestrator_state.json` (99KB typical)

**Purpose:** Complete pipeline state with gap analysis results

**Structure:**
```json
{
  "last_run_timestamp": "2025-11-15T19:31:15",
  "last_completed_stage": "gap_analysis_iteration_1",
  "previous_results": {
    "Pillar 1": {
      "completeness": 8.4,
      "sub_requirements": {
        "Sub-1.1.1": {
          "completeness_percent": 50.0,
          "gap_analysis": "Partial coverage from gk8117.pdf...",
          "confidence_level": "medium",
          "contributing_papers": ["gk8117.pdf"]
        }
      }
    }
  }
}
```

**Key Fields:**
- `completeness`: Overall pillar coverage percentage (0-100)
- `gap_analysis`: Human-readable explanation of what's missing
- `confidence_level`: AI's certainty (low/medium/high)
- `contributing_papers`: Which papers provide evidence

#### 2. `gap_analysis_output/deep_review_directions.json` (20KB typical)

**Purpose:** Internal gap analysis with sub-requirement details

**Structure:**
```json
{
  "Pillar 1": {
    "Sub-1.1.1": {
      "completeness_percent": 50.0,
      "gap_analysis": "Need more evidence on neural spike timing mechanisms",
      "confidence_level": "medium",
      "contributing_papers": ["paper1.pdf"]
    }
  }
}
```

#### 3. `gap_analysis_output/suggested_searches.json` (120KB typical) 🆕

**Purpose:** Machine-readable gap-closing search recommendations

**Structure:**
```json
[
  {
    "pillar": "Pillar 1",
    "requirement": "Conclusive model of how raw sensory data is transduced into neural spikes",
    "current_completeness": 0,
    "priority": "CRITICAL",
    "urgency": 1,
    "gap_description": "The provided literature does not address...",
    "suggested_searches": [
      {
        "query": "\"sensory transduction neural spikes\"",
        "rationale": "Direct match for requirement topic",
        "databases": ["Google Scholar", "arXiv", "PubMed", "IEEE Xplore"]
      },
      {
        "query": "neuroscience AND (sensory transduction)",
        "rationale": "Neuroscience research context",
        "databases": ["PubMed", "Nature", "Science Direct"]
      }
    ]
  }
]
```

**Priority Levels:**
- **CRITICAL** 🔴: 0% completeness (no coverage)
- **HIGH** 🟠: 1-19% completeness (minimal coverage)
- **MEDIUM** 🟡: 20-49% completeness (partial coverage)

#### 4. `gap_analysis_output/suggested_searches.md` (80KB typical) 🆕

**Purpose:** Human-readable gap-closing search recommendations

**Features:**
- Organized by priority (CRITICAL → HIGH → MEDIUM)
- Emoji indicators for quick scanning
- Current coverage percentages
- Gap descriptions
- 4 targeted search queries per gap
- Database-specific recommendations

**Example:**
```markdown
## 🔴 CRITICAL Priority (72 gaps)

### 1. Pillar 1 - Model of sensory transduction
**Current Coverage:** 0.0%  
**Gap:** No evidence found for sensory encoding mechanisms

**Suggested Searches:**
1. `"sensory transduction neural spikes"`
   - *Rationale:* Direct match for requirement
   - *Databases:* Google Scholar, PubMed, arXiv
2. `neuroscience AND (sensory encoding)`
   - *Rationale:* Neuroscience context
   - *Databases:* PubMed, Nature, Frontiers
```

**How to Use:**
1. Open `suggested_searches.md` in your browser or text editor
2. Start with CRITICAL priority gaps (🔴)
3. Copy search queries to academic databases:
   - Google Scholar: https://scholar.google.com
   - PubMed: https://pubmed.ncbi.nlm.nih.gov
   - arXiv: https://arxiv.org
   - IEEE Xplore: https://ieeexplore.ieee.org
4. Download relevant papers
5. Add to `data/raw/Research-Papers/`
6. Re-run pipeline to update coverage and get updated recommendations

#### 5. `gap_analysis_output/waterfall_Pillar X.html` (4-5MB each)

**Purpose:** Interactive visualization of sub-requirement coverage

**Features:**
- Hierarchical view of requirements
- Color-coded completeness (red = gaps, green = complete)
- Click to expand sub-requirements
- Hover for detailed gap analysis

**How to View:**
```bash
# Open in browser
$BROWSER gap_analysis_output/waterfall_Pillar\ 1.html

# Or from Python
python -m http.server 8080
# Navigate to http://localhost:8080/gap_analysis_output/
```

#### 6. `data/review_version_history.json` (varies)

**Purpose:** Complete history of all judged claims

**Structure:**
```json
{
  "papers": {
    "gk8117.pdf": {
      "claims": [
        {
          "claim_id": "claim_001",
          "claim_text": "Neural networks exhibit spike-timing dependent plasticity",
          "pillar": "Pillar 1",
          "verdict": "approved",
          "composite_score": 3.95,
          "evidence_quality": "high"
        }
      ]
    }
  }
}
```

**Key Fields:**
- `verdict`: "approved", "rejected", "pending"
- `composite_score`: 0-5 quality score (0 = reject, 5 = excellent)
- `evidence_quality`: low/medium/high

### Interpreting Completeness Scores

| Score | Interpretation | Action Required |
|-------|----------------|-----------------|
| 0-10% | **Critical Gap** | Immediate deep review needed |
| 11-30% | **Major Gap** | High priority for literature search |
| 31-60% | **Moderate Gap** | Medium priority, some coverage exists |
| 61-85% | **Minor Gap** | Low priority, mostly covered |
| 86-100% | **Complete** | No action needed, well covered |

### Convergence Detection

**Threshold:** 5% change between iterations

**Example Output:**
```
Convergence: NOT MET (37 sub-requirements with >5% change)
```

**What this means:**
- 37 sub-requirements had significant completeness changes
- More literature reviews likely to improve coverage
- Pipeline recommends another iteration with new papers

**When convergence is met:**
```
Convergence: MET (2 sub-requirements with >5% change)
```
- Framework is stable
- Further reviews unlikely to find new evidence
- Consider framework complete for current research corpus

---

## Configuration Guide

### Pipeline Configuration (`pipeline_config.json`)

```json
{
  "version": "2.0.0",
  "retry_policies": {
    "max_attempts": 3,        // API retry attempts
    "base_delay": 5,          // Initial delay (seconds)
    "exponential_backoff": true,
    "jitter": true            // Randomize delay slightly
  },
  "circuit_breaker": {
    "failure_threshold": 3,   // Failures before circuit opens
    "reset_timeout": 60       // Seconds before retry
  }
}
```

### Orchestrator Configuration (`literature_review/orchestrator.py`)

**Performance Settings:**
```python
ANALYSIS_CONFIG = {
    "ENABLE_SEMANTIC_SEARCH": False,  # True = slower but more accurate
    "MAX_ITERATIONS": 5,              # Convergence loop limit
    "CONVERGENCE_THRESHOLD": 0.05,    # 5% change threshold
    "MIN_CONFIDENCE": 0.6             // Minimum AI confidence
}
```

**Rate Limiting:**
```python
# Global rate limiter (10 RPM default)
from literature_review.utils.global_rate_limiter import global_rate_limiter

global_rate_limiter.set_rate_limit(
    requests_per_minute=10,  # Adjust based on API tier
    burst_size=3             # Allow short bursts
)
```

### Pillar Definitions (`pillar_definitions.json`)

**Structure:**
```json
{
  "Pillar 1": {
    "title": "Biological Stimulus-Response Mapping",
    "requirements": {
      "Sub-1.1.1": {
        "description": "Neural encoding mechanisms",
        "keywords": ["spike timing", "neural code"],
        "weight": 1.0
      }
    }
  }
}
```

**Customization:**
1. Add new pillars by duplicating structure
2. Modify requirements to match your domain
3. Adjust weights for priority (0.5 = low, 1.0 = normal, 2.0 = high)

---

## Troubleshooting

### Common Issues

#### 1. API Quota Exhausted

**Symptom:**
```
ERROR - 429 RESOURCE_EXHAUSTED: Quota exceeded for metric: generate_content_free_tier_requests
```

**Solutions:**
- **Wait:** Free tier resets every minute (10 RPM limit)
- **Upgrade:** Switch to paid tier for higher limits
- **Optimize:** Set `ENABLE_SEMANTIC_SEARCH: False` to reduce API calls
- **Batch:** Process fewer papers per run

#### 2. Pipeline Hangs in Gap Analysis

**Symptom:** No log output for 3+ minutes

**Cause:** Sentence transformer CPU bottleneck (if enabled)

**Solutions:**
```python
# Option 1: Disable semantic search
ENABLE_SEMANTIC_SEARCH = False

# Option 2: Use GPU acceleration
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Option 3: Pre-generate embeddings
python scripts/precompute_embeddings.py
```

#### 3. JSON Parsing Errors

**Symptom:**
```
ERROR - JSON parsing failed: Expecting ':' delimiter
```

**Cause:** Gemini AI occasionally returns malformed JSON (`""key"` instead of `"key"`)

**Solution:** Already handled automatically by JSON repair logic in `api_manager.py`

If still occurring:
```bash
# Check logs for raw response
grep "response_text" review_pipeline.log

# Manual fix in version history
python scripts/repair_json.py data/review_version_history.json
```

#### 4. Missing Output Files

**Symptom:** `gap_analysis_output/` directory empty

**Causes:**
- Pipeline didn't complete gap analysis stage
- No approved claims in version history
- Convergence met on first iteration (unlikely)

**Solutions:**
```bash
# Check orchestrator state
cat orchestrator_state.json | jq '.last_completed_stage'

# Verify approved claims exist
cat data/review_version_history.json | jq '[.papers[].claims[] | select(.verdict=="approved")] | length'

# Re-run with verbose logging
python -m literature_review.orchestrator --log-level DEBUG
```

### Log Analysis

**Key Log Files:**
- `review_pipeline.log` - Judge/DRA execution
- `gap_analysis.log` - Gap analysis details
- `orchestrator.log` - High-level pipeline flow

**Useful Grep Patterns:**
```bash
# Find errors
grep "ERROR" review_pipeline.log

# Check API usage
grep "HTTP Request" review_pipeline.log | wc -l

# Find approved claims
grep "verdict.*approved" review_pipeline.log

# Check completeness scores
grep "Completeness:" gap_analysis.log
```

---

## Advanced Usage

### Custom Pillar Frameworks

**Step 1: Create New Framework**
```bash
cp pillar_definitions.json my_custom_framework.json
# Edit my_custom_framework.json with your domain requirements
```

**Step 2: Update Orchestrator**
```python
# In literature_review/orchestrator.py
PILLAR_DEFINITIONS_PATH = "my_custom_framework.json"
```

**Step 3: Run Pipeline**
```bash
python -m literature_review.orchestrator
```

### Batch Processing Multiple Corpora

```python
# batch_runner.py
import os
from literature_review.orchestrator import run_pipeline

paper_sets = [
    "data/raw/AI_Papers/",
    "data/raw/Neuroscience_Papers/",
    "data/raw/Hybrid_Papers/"
]

for paper_dir in paper_sets:
    os.environ['PAPERS_PATH'] = paper_dir
    run_pipeline()
    # Outputs saved to gap_analysis_output/{corpus_name}/
```

### Integration with External Systems

**Export to CSV:**
```python
import json
import csv

# Load gap analysis
with open('gap_analysis_output/deep_review_directions.json') as f:
    gaps = json.load(f)

# Convert to CSV
with open('gaps.csv', 'w') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=['pillar', 'sub_req', 'completeness', 'priority'])
    writer.writeheader()
    for pillar, subs in gaps.items():
        for sub, data in subs.items():
            writer.writerow({
                'pillar': pillar,
                'sub_req': sub,
                'completeness': data['completeness_percent'],
                'priority': data.get('priority', 'medium')
            })
```

**Webhook Notifications:**
```python
# Add to orchestrator.py after gap analysis
import requests

def notify_completion(results):
    webhook_url = "https://your-webhook.com/pipeline-complete"
    requests.post(webhook_url, json={
        'status': 'complete',
        'completeness_scores': results,
        'timestamp': datetime.now().isoformat()
    })
```

### Parallel Processing

**WARNING:** Respect rate limits when parallelizing!

```python
from concurrent.futures import ThreadPoolExecutor
from literature_review.analysis.judge import judge_claim

# Process claims in parallel (max 2 concurrent to stay under 10 RPM)
with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(judge_claim, claim) for claim in claims]
    results = [f.result() for f in futures]
```

---

## API Reference

### Command Line Interface

```bash
# Full pipeline
python -m literature_review.orchestrator [OPTIONS]

OPTIONS:
  --dry-run              Validate config without running
  --skip-judge           Skip judge stage (use existing claims)
  --max-iterations N     Override convergence loop limit
  --log-level LEVEL      DEBUG|INFO|WARNING|ERROR
  --output-dir PATH      Custom output directory
  --convergence-mode     Continue until convergence met
```

### Python API

```python
from literature_review.orchestrator import LiteratureReviewOrchestrator

# Initialize
orchestrator = LiteratureReviewOrchestrator(
    pillar_definitions_path="pillar_definitions.json",
    papers_folder_path="data/raw/Research-Papers/",
    enable_semantic_search=False
)

# Run analysis
results = orchestrator.run_gap_analysis()

# Access results
for pillar, data in results.items():
    print(f"{pillar}: {data['completeness']}%")
```

### Web Dashboard API

**Base URL:** `http://localhost:8000`

**Endpoints:**

```bash
# Get all jobs
GET /api/jobs
Response: [{"id": "job_123", "status": "running", "progress": 45}]

# Submit new job
POST /api/jobs
Body: {"papers": ["file1.pdf"], "framework": "pillar_definitions.json"}
Response: {"job_id": "job_456"}

# Get job status
GET /api/jobs/{job_id}
Response: {"status": "complete", "outputs": [...]}

# Download results
GET /api/jobs/{job_id}/results
Response: JSON or HTML file
```

---

## Best Practices

### 1. Incremental Analysis

**Don't:** Process all papers at once  
**Do:** Start with 5-10 papers, analyze gaps, then add targeted papers

```bash
# Iteration 1: Initial corpus
cp initial_papers/*.pdf data/raw/Research-Papers/
python -m literature_review.orchestrator

# Iteration 2: Fill high-priority gaps
cp gap_filling_papers/*.pdf data/raw/Research-Papers/
python -m literature_review.orchestrator
```

### 2. Version Control Outputs

```bash
# Commit after each successful run
git add orchestrator_state.json data/review_version_history.json
git commit -m "Analysis run $(date +%Y%m%d): 8 papers, 42 approved claims"
```

### 3. Monitor API Usage

```python
# Add to orchestrator.py
from literature_review.utils.global_rate_limiter import global_rate_limiter

print(f"API calls this run: {global_rate_limiter.request_count}")
print(f"Current RPM: {global_rate_limiter.get_current_rpm()}")
```

### 4. Validate Before Deep Reviews

```bash
# Check gap priorities before downloading 100s of papers
jq '[.[][] | select(.priority=="high")] | length' gap_analysis_output/deep_review_directions.json
# Output: 12 high-priority gaps
```

### 5. Checkpoint Hygiene

```bash
# Clean checkpoints before fresh run
rm orchestrator_state.json
rm data/review_version_history.json

# Or preserve history
mv data/review_version_history.json backups/history_$(date +%Y%m%d).json
```

---

## Performance Optimization

### Recommended Settings by Scale

**Small Corpus (< 10 papers):**
```python
ENABLE_SEMANTIC_SEARCH = True   # Full accuracy
MAX_ITERATIONS = 3
```

**Medium Corpus (10-50 papers):**
```python
ENABLE_SEMANTIC_SEARCH = False  # Speed priority
MAX_ITERATIONS = 5
```

**Large Corpus (50+ papers):**
```python
ENABLE_SEMANTIC_SEARCH = False
MAX_ITERATIONS = 10
# Consider GPU acceleration or pre-computed embeddings
```

### Benchmarks

| Configuration | Papers | Runtime | API Calls |
|---------------|--------|---------|-----------|
| Semantic ON   | 7      | 180 sec | 104       |
| Semantic OFF  | 7      | 3 min   | 104       |
| Semantic ON   | 50     | ~20 min | ~700      |
| Semantic OFF  | 50     | ~8 min  | ~700      |

---

## Support & Resources

### Documentation
- Architecture Guide: `docs/RESEARCH_AGNOSTIC_ARCHITECTURE.md`
- Evidence Extraction: `docs/EVIDENCE_EXTRACTION_ENHANCEMENTS.md`
- Triangulation Guide: `docs/EVIDENCE_TRIANGULATION_GUIDE.md`

### Troubleshooting
- Smoke Test Report: `SMOKE_TEST_REPORT.md`
- Test Modifications: `docs/TEST_MODIFICATIONS.md`

### Community
- Issue Tracker: [GitHub Issues]
- Discussions: [GitHub Discussions]

---

**Last Updated:** November 15, 2025  
**Version:** 2.0  
**Maintainer:** BootstrapAI Team
