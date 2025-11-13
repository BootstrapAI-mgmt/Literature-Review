# Workflow Execution Guide

**Last Updated:** November 10, 2025  
**Status:** Production-Ready Architecture  
**Version:** 2.0 (Post Task Cards #1-4)

This guide explains how to execute the full Literature Review automation workflow end-to-end.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Workflow Stages](#workflow-stages)
4. [Execution Methods](#execution-methods)
5. [Stage-by-Stage Guide](#stage-by-stage-guide)
6. [Configuration](#configuration)
7. [Monitoring and Logs](#monitoring-and-logs)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Literature Review system consists of **5 primary stages**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     FULL WORKFLOW PIPELINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Journal-Reviewer.py                                         │
│     Initial paper screening → version_history.json              │
│                                                                 │
│  2. Judge.py                                                    │
│     Evaluate claims → update version_history.json               │
│                                                                 │
│  3. DeepRequirementsAnalyzer.py (DRA)                           │
│     Re-analyze rejected claims → new claims                     │
│                                                                 │
│  4. sync_history_to_db.py                                       │
│     Version history → CSV database                              │
│                                                                 │
│  5. Orchestrator.py (Iterative Loop)                            │
│     Gap analysis → Deep-Reviewer → convergence                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Data Flow:**
```
PDFs → Journal-Reviewer → version_history.json
                              ↓
                           Judge.py
                              ↓
                           DRA.py (if rejections)
                              ↓
                      sync_history_to_db.py
                              ↓
                CSV Database ← Orchestrator.py → Iterative Improvement
                                  ↓
                              Deep-Reviewer.py
                                  ↓
                          Gap Closure (convergence)
```

---

## Prerequisites

### 1. Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with API key
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

### 2. Required Files

Ensure these files exist in the project root:

- ✅ `pillar_definitions_enhanced.json` - Neuromorphic computing requirements
- ✅ `review_version_history.json` - Version history (or will be created)
- ✅ `Research-Papers/` - Directory with PDF papers
- ✅ `.env` - Gemini API key

### 3. Directory Structure

```bash
Literature-Review/
├── Research-Papers/          # Input PDFs
├── gap_analysis_output/      # Orchestrator outputs (auto-created)
├── generated_plots/          # Visualization outputs (auto-created)
├── pillar_definitions_enhanced.json
├── review_version_history.json
├── neuromorphic-research_database.csv (generated)
└── .env
```

---

## Workflow Stages

### Stage 1: Journal Reviewer (Initial Screening)

**Purpose:** Screen new papers against neuromorphic requirements  
**Input:** PDF files in `Research-Papers/`  
**Output:** `review_version_history.json` with pending claims  
**Runtime:** ~2-5 minutes per paper

**What it does:**
- Extracts text from PDFs
- Identifies claims matching neuromorphic requirements
- Creates version history entries with status `pending_judge_review`

---

### Stage 2: Judge (Claim Validation)

**Purpose:** Evaluate pending claims with detailed judgment  
**Input:** `review_version_history.json` (pending claims)  
**Output:** Updated `review_version_history.json` (approved/rejected)  
**Runtime:** ~10-30 seconds per claim (batched in groups of 10)

**What it does:**
- Reads pending claims from version history
- Judges each claim against pillar definitions
- Updates claim status: `approved` or `rejected`
- Adds judge notes and timestamps
- Processes in batches to respect API limits

---

### Stage 3: DRA (Deep Requirements Analyzer)

**Purpose:** Re-analyze rejected claims with deeper scrutiny  
**Input:** Rejected claims from version history  
**Output:** New claims with enhanced evidence  
**Runtime:** ~3-7 minutes per paper with rejections

**What it does:**
- Identifies rejected claims
- Re-analyzes source papers for stronger evidence
- Creates new claims with improved evidence
- Adds claims back to version history for re-judgment
- Chunked processing for large documents (50k chars per chunk)

---

### Stage 4: Sync (Version History → Database)

**Purpose:** Synchronize approved claims to CSV database  
**Input:** `review_version_history.json`  
**Output:** `neuromorphic-research_database.csv`  
**Runtime:** <10 seconds

**What it does:**
- Extracts only `approved` claims from version history
- Formats claims as CSV entries
- Preserves all claim metadata
- Ensures database reflects latest judgments

**Run:**
```bash
python sync_history_to_db.py
```

---

### Stage 5: Orchestrator (Iterative Improvement)

**Purpose:** Identify gaps and drive convergence to 100% coverage  
**Input:** CSV database + version history  
**Output:** Gap analysis reports, visualizations, directed analysis  
**Runtime:** ~10-30 minutes per iteration (depends on paper count)

**What it does:**
- Calculates completeness score (% of requirements met)
- Identifies missing sub-requirements
- Prioritizes papers for deep analysis
- Triggers Deep-Reviewer for targeted analysis
- **Iterates until <5% gap remains**

**Iterative Loop:**
```
Calculate gaps → Deep-Reviewer → Judge new claims → Re-sync → 
Check convergence → Repeat if gap >5%
```

---

## Execution Methods

### Method 1: **Manual Stage-by-Stage** (Recommended for First Run)

Run each stage individually to understand the workflow:

#### Step 1: Journal Reviewer

```bash
python Journal-Reviewer.py
```

**Prompts:**
- Path to PDF folder: `Research-Papers/`
- Review type: `journal` (or press Enter for default)

**Expected Output:**
```
Processing paper: research_paper_1.pdf
Found 15 claims matching requirements
Version history updated: review_version_history.json
```

---

#### Step 2: Judge Claims

```bash
python Judge.py
```

**No prompts** - Automatically:
- Loads pending claims from version history
- Judges claims in batches of 10
- Updates version history with verdicts

**Expected Output:**
```
Loaded 15 pending claims from version history
Processing batch 1/2 (10 claims)...
  Claim c1a2b3: approved
  Claim d4e5f6: rejected
  ...
Processing batch 2/2 (5 claims)...
Updated version history with judgments
Total: 12 approved, 3 rejected
```

---

#### Step 3: DRA (If Rejections Exist)

```bash
python DeepRequirementsAnalyzer.py
```

**Prompts:**
- Confirm papers with rejections

**Expected Output:**
```
Found 3 rejected claims in version history
Re-analyzing papers:
  - research_paper_1.pdf (2 rejections)
  - research_paper_2.pdf (1 rejection)

Chunking large document (3 chunks)...
Processing chunk 1/3 (Pages 1-50)...
Processing chunk 2/3 (Pages 51-100)...
Processing chunk 3/3 (Pages 101-150)...

Found 2 new claims with enhanced evidence
Added to version history for re-judgment
```

**After DRA:** Re-run Judge to evaluate new claims!

```bash
python Judge.py  # Re-judge DRA claims
```

---

#### Step 4: Sync to Database

```bash
python sync_history_to_db.py
```

**Expected Output:**
```
Syncing version history to CSV database...
Extracted 14 approved claims from 2 papers
Updated: neuromorphic-research_database.csv
```

---

#### Step 5: Orchestrator (Iterative Gap Closure)

```bash
python Orchestrator.py
```

**Prompts:**
- Database path: `neuromorphic-research_database.csv` (or Enter for default)
- Max iterations: `5` (or Enter for default)

**Expected Output:**
```
=== ITERATION 1 ===
Completeness Score: 42.5% (17/40 sub-requirements met)
Gap: 23 missing sub-requirements

Prioritizing papers for deep analysis...
Top papers:
  1. research_paper_5.pdf (8 potential matches)
  2. research_paper_3.pdf (6 potential matches)

Triggering Deep-Reviewer for targeted analysis...
Deep-Reviewer found 5 new claims
Adding to version history...

=== ITERATION 2 ===
Completeness Score: 55.0% (22/40 sub-requirements met)
Gap: 18 missing sub-requirements
...

=== CONVERGENCE ACHIEVED ===
Final Score: 96.5% (gap <5%)
Iterations: 4
Reports generated in gap_analysis_output/
```

---

### Method 2: **Automated End-to-End** (Using Pipeline Orchestrator)

**✅ NEW:** The `pipeline_orchestrator.py` script now automates all 5 stages in a single command.

**Basic Usage:**
```bash
python pipeline_orchestrator.py
```

**With Logging:**
```bash
python pipeline_orchestrator.py --log-file pipeline.log
```

**With Configuration:**
```bash
python pipeline_orchestrator.py --config pipeline_config.json
```

**What it does:**
- Runs all 5 stages sequentially
- Conditionally executes DRA only if rejections are detected
- Logs progress with timestamps to console and optional file
- Halts pipeline on any stage failure with clear error messages
- Provides total execution time summary
- **Creates checkpoint file for resume capability**

**Configuration File (`pipeline_config.json`):**
```json
{
  "version_history_path": "review_version_history.json",
  "stage_timeout": 7200,
  "log_level": "INFO"
}
```

**Note:** The orchestrator requires that all Python scripts (Journal-Reviewer.py, Judge.py, etc.) are in the same directory and can run non-interactively.

---

### Method 3: **Resume After Interruption** (Checkpoint/Resume)

**✅ NEW in v1.1:** Resume pipeline execution after failures or interruptions.

The pipeline orchestrator automatically creates a checkpoint file (`pipeline_checkpoint.json`) that tracks the progress of each stage. If the pipeline is interrupted, you can resume from where it left off.

**Resume from Last Checkpoint:**
```bash
python pipeline_orchestrator.py --resume
```

This will:
- Load the checkpoint file
- Skip stages that have already completed successfully
- Re-run any stage that was in progress when interrupted
- Continue with remaining stages

**Resume from a Specific Stage:**
```bash
# Resume from sync stage onwards (skip earlier stages)
python pipeline_orchestrator.py --resume-from sync
```

Available stages for `--resume-from`:
- `journal_reviewer` - Stage 1: Initial Paper Review
- `judge` - Stage 2: Judge Claims
- `dra` - Stage 3: DRA Appeal (if rejections detected)
- `sync` - Stage 4: Sync to Database
- `orchestrator` - Stage 5: Gap Analysis & Convergence

**Custom Checkpoint File:**
```bash
# Use a different checkpoint file
python pipeline_orchestrator.py --checkpoint-file batch_001_checkpoint.json

# Resume from custom checkpoint
python pipeline_orchestrator.py --resume --checkpoint-file batch_001_checkpoint.json
```

**Use Cases:**
- **Network Failure:** Resume after connection timeout during sync
- **Manual Interruption:** Resume after Ctrl+C
- **System Crash:** Resume after unexpected shutdown
- **Iterative Development:** Re-run only modified stages
- **Batch Processing:** Separate checkpoints for different batches

**Checkpoint File Structure:**

The checkpoint file is human-readable JSON:

```json
{
  "run_id": "2025-11-11T14:30:00_abc123",
  "pipeline_version": "1.1.0",
  "started_at": "2025-11-11T14:30:00",
  "last_updated": "2025-11-11T14:45:30",
  "status": "in_progress",
  "stages": {
    "journal_reviewer": {
      "status": "completed",
      "started_at": "2025-11-11T14:30:05",
      "completed_at": "2025-11-11T14:35:12",
      "duration_seconds": 307,
      "exit_code": 0
    },
    "judge": {
      "status": "completed",
      "started_at": "2025-11-11T14:35:15",
      "completed_at": "2025-11-11T14:40:22",
      "duration_seconds": 307,
      "exit_code": 0
    },
    "sync": {
      "status": "failed",
      "started_at": "2025-11-11T14:40:25",
      "failed_at": "2025-11-11T14:42:10",
      "error": "Connection timeout"
    }
  }
}
```

**Safety Features:**
- **Atomic writes** prevent checkpoint corruption
- **Corrupted checkpoint detection** with clear error messages
- **No sensitive data** stored in checkpoint (no API keys)
- **Works across system restarts**

**Example Workflow:**

```bash
# Start pipeline
python pipeline_orchestrator.py --log-file run1.log

# [Pipeline runs Stage 1 and 2, then network fails at Stage 3]
# Checkpoint shows: journal_reviewer=completed, judge=completed, sync=failed

# Resume after fixing network
python pipeline_orchestrator.py --resume --log-file run1_resumed.log
# Output: Skipping journal_reviewer (already completed)
#         Skipping judge (already completed)
#         Re-running sync (was interrupted)
#         Running orchestrator
```

---

## Configuration

### API Configuration

Edit API settings in each module:

**Judge.py:**
```python
API_CONFIG = {
    'CLAIM_BATCH_SIZE': 10,        # Claims per batch
    'BATCH_DELAY_SECONDS': 2       # Delay between batches
}
```

**DeepRequirementsAnalyzer.py:**
```python
REVIEW_CONFIG = {
    'DRA_CHUNK_SIZE': 50000,       # Chunk size (chars)
    'DRA_CHUNK_OVERLAP': 0.1       # 10% overlap
}
```

**Deep-Reviewer.py:**
```python
REVIEW_CONFIG = {
    'DEEP_REVIEWER_CHUNK_SIZE': 75000,  # Chunk size (chars)
    'DEDUPLICATION_ENABLED': True
}
```

**Orchestrator.py:**
```python
ORCHESTRATOR_CONFIG = {
    'MAX_ITERATIONS': 10,                # Max improvement iterations
    'CONVERGENCE_THRESHOLD': 0.05,       # 5% gap threshold
    'MIN_PAPERS_PER_ITERATION': 2        # Papers to analyze per iteration
}
```

---

## Monitoring and Logs

### Progress Tracking

Each module provides real-time progress:

**Judge Batching:**
```
Processing batch 3/7 (10 claims)...
  Claim a1b2c3: approved (Evidence supports requirement)
  Claim d4e5f6: rejected (Insufficient detail)
  ...
Progress: 30/70 claims (42.9%)
```

**DRA Chunking:**
```
Chunking document: research_paper.pdf (150 pages, 250k chars)
Created 5 chunks with 10% overlap
Processing chunk 1/5 (Pages 1-30)...
Processing chunk 2/5 (Pages 28-58)...
...
```

**Orchestrator Convergence:**
```
Iteration 3: Score 67.5% → 72.5% (+5.0%)
Gap reduction: 13 → 11 missing requirements
Estimated iterations to convergence: 2-3
```

### Log Files

Currently, logs are printed to console. To save logs:

```bash
# Redirect to file
python Judge.py > judge_run.log 2>&1

# Or use tee for both console and file
python Orchestrator.py | tee orchestrator_run.log
```

---

## Troubleshooting

### Issue: "No pending claims found"

**Cause:** Version history doesn't have claims with status `pending_judge_review`

**Solution:**
1. Run Journal-Reviewer first: `python Journal-Reviewer.py`
2. Or check version history has pending claims:
   ```bash
   grep "pending_judge_review" review_version_history.json
   ```

---

### Issue: "DRA finds no new claims"

**Possible Causes:**
- Rejected claims are truly unsupportable
- Paper doesn't contain relevant evidence
- Prompting needs adjustment

**Solution:**
1. Check rejected claims in version history
2. Manually review judge notes to understand why rejected
3. Consider if paper is truly relevant to requirements

---

### Issue: "Orchestrator doesn't converge"

**Cause:** Gap remains >5% after max iterations

**Solutions:**
1. Increase max iterations in config
2. Add more papers to `Research-Papers/`
3. Check if missing requirements are too specific
4. Review gap analysis reports in `gap_analysis_output/`

---

### Issue: "API quota exceeded"

**Cause:** Too many API calls

**Solutions:**
1. **Use batching:** Judge automatically batches (10 claims/batch)
2. **Reduce batch size:** Lower `CLAIM_BATCH_SIZE` in Judge.py
3. **Increase delays:** Raise `BATCH_DELAY_SECONDS`
4. **Chunking:** Enabled by default for large documents
5. **Wait:** API quotas reset periodically

---

### Issue: "Circular reference error in JSON"

**Cause:** Bug in claim metadata (should be fixed in latest version)

**Solution:**
1. Verify using Judge v2.0+ (has fix for ISSUE-004)
2. Run validation:
   ```bash
   python demos/demo_validate_data.py
   ```

---

### Issue: "Pillar definitions not found"

**Cause:** Missing `pillar_definitions_enhanced.json`

**Solution:**
1. Ensure file exists in project root
2. Check file is valid JSON:
   ```bash
   python -m json.tool pillar_definitions_enhanced.json > /dev/null
   ```

---

## Advanced Workflows

### Workflow A: New Paper Batch Processing

**Scenario:** You have 50 new papers to process

```bash
# 1. Add PDFs to Research-Papers/
cp /path/to/new/papers/*.pdf Research-Papers/

# 2. Run Journal Reviewer
python Journal-Reviewer.py  # 2-3 hours for 50 papers

# 3. Judge all claims
python Judge.py  # 30-60 minutes

# 4. DRA for rejections (if any)
python DeepRequirementsAnalyzer.py  # 1-2 hours

# 5. Re-judge DRA claims
python Judge.py  # 10-20 minutes

# 6. Sync to database
python sync_history_to_db.py  # <1 minute

# 7. Run orchestrator for convergence
python Orchestrator.py  # 2-5 hours (iterative)
```

**Total Time:** ~6-12 hours (mostly API wait time)

---

### Workflow B: Targeted Gap Filling

**Scenario:** You have 85% coverage, want to reach 95%

```bash
# 1. Run Orchestrator to identify gaps
python Orchestrator.py

# 2. Review gap analysis report
cat gap_analysis_output/iteration_1_gap_analysis.json

# 3. Add papers targeting specific gaps
# (Use recommendations from gap analysis)

# 4. Run Deep-Reviewer on targeted papers
# (Orchestrator will trigger this automatically)

# 5. Judge new claims
python Judge.py

# 6. Sync and re-check score
python sync_history_to_db.py
python Orchestrator.py  # Check if gap <5%
```

---

### Workflow C: Re-process Specific Paper

**Scenario:** Paper was incorrectly reviewed, need to re-run

```bash
# 1. Remove paper's entries from version history
python -c "
import json
with open('review_version_history.json', 'r+') as f:
    history = json.load(f)
    del history['target_paper.pdf']
    f.seek(0)
    f.truncate()
    json.dump(history, f, indent=2)
"

# 2. Re-run Journal Reviewer on that paper
python Journal-Reviewer.py
# (Specify just that one PDF)

# 3. Judge new claims
python Judge.py

# 4. Re-sync
python sync_history_to_db.py
```

---

## Performance Optimization

### Tip 1: Use Caching

Judge and DRA use prompt caching automatically. To maximize cache hits:
- Process similar papers together
- Avoid changing pillar definitions mid-batch

### Tip 2: Use Pipeline Orchestrator

For batch processing, use the `pipeline_orchestrator.py` to automate all stages:
```bash
python pipeline_orchestrator.py --log-file pipeline.log
```

Benefits:
- No manual intervention between stages
- Automatic DRA triggering when needed
- Complete execution log for auditing
- Error handling and graceful failure

### Tip 3: Parallel Processing (Future)

Currently, stages run sequentially. Future enhancement:
- Run Judge on multiple papers in parallel (separate processes)
- Requires careful version history locking

### Tip 4: Incremental Syncing

Sync script is fast (<10s) but can be optimized:
- Only sync changed papers (track timestamps)
- Use `--incremental` flag (future feature)

### Tip 4: Monitor Chunk Counts

Check logs for chunk statistics:
```
DRA: 150-page document → 5 chunks (efficient)
DRA: 50-page document → 1 chunk (no chunking needed)
```

Adjust chunk sizes if seeing inefficiencies.

---

## Summary: Typical Full Run

**For 20 papers (average 50 pages each):**

| Stage                  | Time      | API Calls | Output                      |
|------------------------|-----------|-----------|------------------------------|
| Journal-Reviewer       | 40-60 min | ~40-60    | version_history.json         |
| Judge (Initial)        | 20-30 min | ~100-150  | Updated version_history.json |
| DRA (If rejections)    | 30-45 min | ~40-60    | New claims added             |
| Judge (DRA Re-judge)   | 10-15 min | ~20-30    | Final verdicts               |
| Sync                   | <1 min    | 0         | CSV database                 |
| Orchestrator (2-3 iter)| 1-2 hours | ~80-120   | Gap reports, convergence     |
| **TOTAL**              | **3-5 hr**| **~300**  | **Complete analysis**        |

**Cost Estimate:** ~$15-25 for 20 papers (at Gemini API pricing)

---

## Next Steps

1. **Start Small:** Process 2-3 papers end-to-end first
2. **Verify Outputs:** Check version history, database, reports
3. **Scale Up:** Gradually add more papers
4. **Monitor:** Track convergence scores and API usage
5. **Iterate:** Use Orchestrator to drive continuous improvement

---

## Future Enhancements

**Planned Infrastructure Improvements:**

1. **Automated Pipeline Script**
   - Single command: `./run_full_pipeline.sh`
   - Automatic stage transitions
   - Progress checkpoints

2. **Web Dashboard**
   - Real-time progress monitoring
   - Visualization of convergence
   - Paper management interface

3. **Parallel Processing**
   - Multi-paper concurrent processing
   - Version history locking
   - Load balancing

4. **Incremental Mode**
   - Only process new/changed papers
   - Delta syncing
   - Faster iterations

5. **CI/CD Integration**
   - Automated testing of new papers
   - Regression detection
   - Quality gates

---

**Document Status:** ✅ Production-Ready  
**Last Validated:** November 10, 2025  
**Validation:** Post-merge testing of PRs #1-4 complete

For questions or issues, see:
- `ARCHITECTURE_ANALYSIS.md` - System design
- `TESTING_STATUS_SUMMARY.md` - Current test coverage
- `INTEGRATION_TESTING_TASK_CARDS.md` - Planned improvements
