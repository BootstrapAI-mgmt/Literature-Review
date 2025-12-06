# Comprehensive Production Smoke Test Report
# Literature Review Pipeline

**Test Date:** November 21, 2025  
**Test Environment:** Dev Container (Ubuntu 24.04.3 LTS)  
**Python Version:** 3.12.1  
**Tester:** GitHub Copilot (Automated Testing Agent)

---

## Executive Summary

**Status:** 🔄 IN PROGRESS  
**Test Coverage:**
- ✅ Pre-flight checks
- 🔄 Terminal/CLI workflow
- ⏳ Web dashboard workflow
- ⏳ Output verification
- ⏳ Recommendations validation

**Critical Findings:** TBD  
**Production Readiness:** TBD

---

## Table of Contents

1. [Test Environment](#test-environment)
2. [Pre-Flight Checks](#pre-flight-checks)
3. [Terminal/CLI Workflow Testing](#terminalcli-workflow-testing)
4. [Web Dashboard Workflow Testing](#web-dashboard-workflow-testing)
5. [Output Verification](#output-verification)
6. [Performance Metrics](#performance-metrics)
7. [Issues & Recommendations](#issues--recommendations)
8. [Sign-Off](#sign-off)

---

## Test Environment

### System Information
- **OS:** Ubuntu 24.04.3 LTS (Dev Container)
- **Python:** 3.12.1
- **Working Directory:** `/workspaces/Literature-Review`
- **API Keys:** ✅ Configured (GEMINI_API_KEY, DASHBOARD_API_KEY)

### Test Data
- **Total PDFs Available:** 6 papers
- **Test Corpus Location:** `data/raw/Research-Papers/`
  - journal-1: 3 PDFs
  - journal-2: 3 PDFs

### Configuration Files
- ✅ `pipeline_config.json` - Version 2.0.0
- ✅ `pillar_definitions.json` - Present
- ✅ `.env` - API keys configured

### Previous State
- **orchestrator_state.json:** 98KB (Last modified: Nov 18)
- **review_version_history.json:** 2.0MB (Last modified: Nov 15)
- **gap_analysis_output/:** Empty directory

---

## Pre-Flight Checks

### ✅ Environment Validation

```bash
# Python version
Python 3.12.1 ✅

# API Key present  
GEMINI_API_KEY=AIzaSyC76lypLpW0Bf7nZqMXeYEgWqMBCuEvl6M ✅
DASHBOARD_API_KEY=test-key-for-smoke-testing ✅

# Test data availability
6 PDFs available (3 in journal-1, 3 in journal-2) ✅
Database: neuromorphic-research_database.csv (6 papers) ✅

# Configuration files
pipeline_config.json (Version 2.0.0) ✅
pillar_definitions.json ✅
```

### ✅ Dependencies Check

```bash
# Core dependencies installed
google-genai                 1.50.1 ✅
pandas                       2.3.3 ✅
pdfplumber                   0.11.8 ✅
plotly                       6.4.0 ✅
sentence-transformers        5.1.2 ✅
```

**Status:** All critical dependencies present and versions confirmed.

---

## Terminal/CLI Workflow Testing

### Test 1: Pipeline Help & Version
**Objective:** Verify pipeline orchestrator is accessible and documented.

**Test Steps:**
```bash
python pipeline_orchestrator.py --help
```

**Expected Output:**
- Usage instructions
- Available flags (--incremental, --force, --output-dir, etc.)
- Configuration options

**Status:** ⏳ PENDING

---

### Test 2: Full Pipeline Execution (Small Corpus)
**Objective:** Run complete 5-stage pipeline on minimal dataset.

**Test Configuration:**
- Mode: Full analysis (not incremental)
- Papers: 3 PDFs from journal-1
- Output: `gap_analysis_output/`
- Batch mode: Enabled (non-interactive)

**Test Steps:**
```bash
# Backup current state
cp orchestrator_state.json orchestrator_state.backup
cp review_version_history.json review_version_history.backup

# Run pipeline in batch mode with logging
python pipeline_orchestrator.py \
  --batch-mode \
  --log-file smoke_test_full_pipeline.log \
  --output-dir gap_analysis_output
```

**Expected Results:**
- All 5 stages complete successfully
- No crashes or unhandled exceptions
- Checkpoint file created
- Outputs generated in gap_analysis_output/

**Monitoring:**
- Runtime: Expected < 15 minutes
- API calls: ~50-100 requests
- Memory usage: < 2GB peak
- Rate limiting: Proper 10 RPM enforcement

**Status:** ⏳ PENDING

---

### Test 3: Incremental Mode (New Papers)
**Objective:** Test incremental review with new papers added.

**Prerequisites:**
- Test 2 completed successfully
- Baseline analysis exists in gap_analysis_output/

**Test Steps:**
```bash
# Simulate adding new papers (copy from journal-2)
cp data/raw/Research-Papers/journal-2/*.pdf data/raw/Research-Papers/journal-1/

# Run incremental analysis
python pipeline_orchestrator.py \
  --incremental \
  --output-dir gap_analysis_output \
  --log-file smoke_test_incremental.log
```

**Expected Results:**
- New papers detected (3 additional PDFs)
- Gap extraction successful
- Relevance scoring applied
- Only relevant papers analyzed
- Results merged with baseline
- 40-60% faster than full re-analysis

**Status:** ⏳ PENDING

---

### Test 4: Resume from Checkpoint
**Objective:** Verify pipeline can resume after interruption.

**Test Steps:**
```bash
# Start pipeline
python pipeline_orchestrator.py --output-dir gap_analysis_output &
PID=$!

# Wait 2 minutes then interrupt
sleep 120
kill -SIGINT $PID

# Wait for graceful shutdown
sleep 5

# Resume from checkpoint
python pipeline_orchestrator.py --resume
```

**Expected Results:**
- Checkpoint saved before interruption
- Resume flag recognized
- Pipeline continues from last stage
- No data loss

**Status:** ⏳ PENDING

---

### Test 5: CLI Flags & Options
**Objective:** Verify all CLI flags work correctly.

**Test Cases:**

#### 5.1: Dry Run Mode
```bash
python pipeline_orchestrator.py --incremental --dry-run
```
Expected: Preview of changes, no actual execution

#### 5.2: Custom Output Directory
```bash
python pipeline_orchestrator.py --output-dir reviews/test_review
```
Expected: Outputs in custom directory

#### 5.3: Relevance Threshold Adjustment
```bash
python pipeline_orchestrator.py --incremental --relevance-threshold 0.70
```
Expected: Stricter pre-filtering (fewer papers analyzed)

#### 5.4: Force Full Re-analysis
```bash
python pipeline_orchestrator.py --force --output-dir gap_analysis_output
```
Expected: Ignore incremental mode, re-analyze all papers

**Status:** ⏳ PENDING

---

## Web Dashboard Workflow Testing

### Test 6: Dashboard Startup
**Objective:** Verify dashboard launches successfully.

**Test Steps:**
```bash
# Start dashboard
./run_dashboard.sh

# Or direct uvicorn
uvicorn webdashboard.app:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Results:**
- Server starts on port 8000
- No startup errors
- API endpoints accessible
- Static files served

**Verification:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/ | grep "Literature Review Dashboard"
```

**Status:** ⏳ PENDING

---

### Test 7: PDF Upload via Dashboard
**Objective:** Upload PDFs through web interface.

**Test Steps:**
1. Navigate to http://localhost:8000
2. Click "Upload" tab
3. Select 2-3 PDFs
4. Click "Start Analysis"
5. Monitor job status page

**Expected Results:**
- Files upload successfully
- Metadata extracted (title, authors, year)
- Job created with unique ID
- Status shows "Running"
- Real-time progress updates

**Status:** ⏳ PENDING

---

### Test 8: Job Monitoring & Logs
**Objective:** Track job progress and view logs.

**Test Steps:**
1. Navigate to job details page
2. Check status updates
3. View real-time logs
4. Monitor progress percentage

**Expected Results:**
- WebSocket connection established
- Live status updates
- Logs stream in real-time
- Progress bar updates
- Stage transitions visible

**Status:** ⏳ PENDING

---

### Test 9: Incremental Review via Dashboard
**Objective:** Continue existing review from dashboard.

**Prerequisites:**
- Previous dashboard job completed

**Test Steps:**
1. Navigate to Upload page
2. Toggle "Continue Existing Review"
3. Select base job from dropdown
4. View gap summary
5. Upload new PDFs
6. Adjust relevance threshold (slider)
7. Start incremental analysis

**Expected Results:**
- Base job list populated
- Gap summary displays correctly
- Relevance preview shows papers to analyze
- Threshold slider functional
- Incremental job starts successfully

**Status:** ⏳ PENDING

---

### Test 10: Job Genealogy Visualization
**Objective:** View parent-child job relationships.

**Test Steps:**
1. Navigate to job details
2. Click "Lineage" tab
3. View genealogy tree

**Expected Results:**
- Parent job displayed
- Child jobs listed
- Timeline visualization
- Gap reduction over time shown

**Status:** ⏳ PENDING

---

### Test 11: Download Results
**Objective:** Export analysis results from dashboard.

**Test Steps:**
1. Navigate to completed job
2. Click "Download Results"
3. Click "Download PDF" for uploaded papers

**Expected Results:**
- ZIP file downloads with all outputs
- gap_analysis_report.json included
- HTML visualizations included
- PDFs downloadable individually

**Status:** ⏳ PENDING

---

## Output Verification

### Test 12: Structural Validation
**Objective:** Verify all expected outputs generated.

**Required Outputs:**
- [ ] orchestrator_state.json
- [ ] gap_analysis_report.json
- [ ] deep_review_directions.json
- [ ] executive_summary.md
- [ ] Waterfall charts (7 pillars)
- [ ] Overall radar chart
- [ ] Paper network graph
- [ ] Research trends visualization
- [ ] Suggested searches (JSON + Markdown)

**Validation Script:**
```python
import os
import json

required_files = [
    'gap_analysis_output/gap_analysis_report.json',
    'gap_analysis_output/executive_summary.md',
    'orchestrator_state.json'
]

for file in required_files:
    assert os.path.exists(file), f"Missing: {file}"
    print(f"✅ {file}")
```

**Status:** ⏳ PENDING

---

### Test 13: Content Validation
**Objective:** Verify output content quality.

**Checks:**
- Completeness scores in range 0-100%
- No negative values
- JSON schemas valid
- HTML files render correctly
- No empty or null critical fields

**Validation Script:**
```python
import json

with open('orchestrator_state.json') as f:
    state = json.load(f)

for pillar, data in state['previous_results'].items():
    comp = data.get('completeness', 0)
    assert 0 <= comp <= 100, f"{pillar}: Invalid completeness {comp}%"
    print(f"✅ {pillar}: {comp}% completeness")
```

**Status:** ⏳ PENDING

---

### Test 14: Visualization Rendering
**Objective:** Verify HTML visualizations display correctly.

**Test Steps:**
```bash
# Open in browser
$BROWSER gap_analysis_output/waterfall_Pillar_1.html
$BROWSER gap_analysis_output/_OVERALL_Research_Gap_Radar.html
```

**Expected Results:**
- Charts render without errors
- Interactive elements functional
- Data labels readable
- Colors and legends correct

**Status:** ⏳ PENDING

---

## Performance Metrics

### Baseline Metrics (Full Analysis - 6 Papers)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Total Runtime | < 20 min | TBD | ⏳ |
| Peak Memory | < 2 GB | TBD | ⏳ |
| API Calls | 80-150 | TBD | ⏳ |
| Rate Limit Pauses | 5-15 | TBD | ⏳ |
| HTTP 429 Errors | 0 | TBD | ⏳ |

### Incremental Analysis Metrics (3 New Papers)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Total Runtime | < 10 min | TBD | ⏳ |
| Speedup vs Full | 40-60% | TBD | ⏳ |
| Papers Analyzed | 1-2 (filtered) | TBD | ⏳ |
| API Calls | 20-50 | TBD | ⏳ |

### Dashboard Performance

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Startup Time | < 5 sec | TBD | ⏳ |
| Upload Speed | > 1 MB/s | TBD | ⏳ |
| WebSocket Latency | < 100 ms | TBD | ⏳ |
| Page Load Time | < 2 sec | TBD | ⏳ |

---

## Issues & Recommendations

### Critical Issues
_None found yet_

### High Priority Issues
_TBD_

### Medium Priority Issues
_TBD_

### Recommendations
_TBD_

---

## Test Execution Log

### Session 1: CLI Testing
**Start Time:** TBD  
**End Time:** TBD  
**Duration:** TBD

**Tests Executed:**
- [ ] Test 1: Pipeline Help
- [ ] Test 2: Full Pipeline
- [ ] Test 3: Incremental Mode
- [ ] Test 4: Resume Checkpoint
- [ ] Test 5: CLI Flags

**Results:** TBD

---

### Session 2: Dashboard Testing
**Start Time:** TBD  
**End Time:** TBD  
**Duration:** TBD

**Tests Executed:**
- [ ] Test 6: Dashboard Startup
- [ ] Test 7: PDF Upload
- [ ] Test 8: Job Monitoring
- [ ] Test 9: Incremental Review
- [ ] Test 10: Job Genealogy
- [ ] Test 11: Download Results

**Results:** TBD

---

### Session 3: Output Validation
**Start Time:** TBD  
**End Time:** TBD  
**Duration:** TBD

**Tests Executed:**
- [ ] Test 12: Structural Validation
- [ ] Test 13: Content Validation
- [ ] Test 14: Visualization Rendering

**Results:** TBD

---

## Sign-Off

### Test Completion
- [ ] All tests executed
- [ ] Results documented
- [ ] Issues logged
- [ ] Recommendations provided

### Production Readiness Assessment
**Status:** ⏳ IN PROGRESS

**Criteria:**
- [ ] All critical tests passed
- [ ] Zero critical bugs
- [ ] Performance within acceptable range
- [ ] Documentation complete

**Approved for Production:** TBD

---

**Report Status:** 🔄 Live Document (Updates in Progress)  
**Next Update:** After completing CLI tests
