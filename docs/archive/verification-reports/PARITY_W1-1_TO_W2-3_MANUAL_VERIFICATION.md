# Manual Verification Checklist: Tasks W1-1 through W2-3

**Date:** November 22, 2025  
**Tasks Covered:** PARITY-W1-1, W1-2, W1-3, W2-1, W2-2, W2-3  
**Purpose:** Verify implemented functionality matches task card specifications

---

## 📋 Overview

This document provides a comprehensive manual testing checklist for the first 6 Dashboard-CLI parity tasks that have been implemented:

- **W1-1:** Output Directory Selector (12-16h, CRITICAL)
- **W1-2:** Advanced Options Panel (10-14h, CRITICAL)
- **W1-3:** Fresh Analysis Trigger (6-8h, CRITICAL)
- **W2-1:** Config File Upload (8-10h, HIGH)
- **W2-2:** Force Re-analysis Control (4-6h, HIGH)
- **W2-3:** Cache Management (6-8h, HIGH)

**Expected Result:** All 6 tasks should be fully functional based on code inspection.

---

## ✅ Task W1-1: Output Directory Selector

### Backend Verification (app.py)

**Status:** ✅ **IMPLEMENTED**

**Code Evidence:**
- Lines 243-244: `output_dir_mode` and `output_dir_path` fields in `JobConfig` model
- Lines 1500-1545: Complete output directory resolution logic in `/api/jobs/{job_id}/start` endpoint
- Lines 1500-1503: Auto-generated mode (`workspace/jobs/{job_id}/outputs/gap_analysis_output`)
- Lines 1505-1516: Custom path mode with security validation
- Lines 1518-1524: Existing directory mode with validation

**Security Features Found:**
- ✅ Directory traversal prevention (line 1514: checks system directories)
- ✅ Path resolution and validation
- ✅ Absolute path enforcement

### Frontend Verification (index.html)

**Status:** ✅ **IMPLEMENTED**

**Code Evidence:**
- Lines 1078-1156: Complete Output Directory Configuration UI
- Lines 1086-1120: Three radio button modes (auto/custom/existing)
- Lines 1127-1146: Custom path input with overwrite checkbox
- Lines 1148-1153: Existing directory dropdown selector
- Lines 3305-3320: Frontend validation logic

**UI Elements Found:**
- ✅ Radio buttons for 3 modes (auto/custom/existing)
- ✅ Custom path text input
- ✅ Existing directory dropdown
- ✅ Refresh button for directory list
- ✅ Overwrite checkbox

### Manual Testing Steps

#### Test 1: Auto-Generated Mode (Default)
1. **Navigate** to Dashboard (http://localhost:8000)
2. **Upload** PDFs without changing output directory settings
3. **Configure** job and start analysis
4. **Verify** results saved to `workspace/jobs/{job_id}/outputs/gap_analysis_output/`
5. **Expected:** ✅ Default behavior maintained

#### Test 2: Custom Path Mode
1. **Select** "Custom Path" radio button
2. **Enter** custom path: `./my_custom_review`
3. **Upload** PDFs and configure job
4. **Start** analysis
5. **Verify** results created at `{BASE_DIR}/my_custom_review/`
6. **Expected:** ✅ Custom directory created and populated

#### Test 3: Custom Path with Absolute Path
1. **Select** "Custom Path"
2. **Enter** absolute path: `/tmp/lit_review_test`
3. **Upload** and start job
4. **Verify** results at `/tmp/lit_review_test/`
5. **Expected:** ✅ Absolute path respected

#### Test 4: Security - System Directory Rejection
1. **Select** "Custom Path"
2. **Enter** system path: `/etc/test_review`
3. **Attempt** to start job
4. **Expected:** ⚠️ Error: "Cannot use system directories as output path"

#### Test 5: Existing Directory Mode
1. **Select** "Select Existing Directory"
2. **Click** "Refresh List" button
3. **Verify** dropdown populates with existing output directories
4. **Select** a directory from dropdown
5. **Start** job
6. **Expected:** ✅ Results appended to existing directory

#### Test 6: Overwrite Protection
1. **Select** "Custom Path"
2. **Enter** path to directory with existing results
3. **Uncheck** "Overwrite existing results"
4. **Attempt** to start job
5. **Expected:** ⚠️ Error: "Directory contains existing analysis. Enable overwrite_existing to proceed."

#### Test 7: Overwrite Enabled
1. **Repeat** Test 6 but **check** "Overwrite existing results"
2. **Start** job
3. **Expected:** ✅ Existing results overwritten

---

## ✅ Task W1-2: Advanced Options Panel

### Backend Verification (app.py)

**Status:** ✅ **IMPLEMENTED**

**Code Evidence:**
- Lines 248-256: Advanced options fields in `JobConfig` model:
  - `dry_run: bool` (line 248)
  - `force: bool` (line 249)
  - `force_confirmed: bool` (line 250)
  - `clear_cache: bool` (line 251)
  - `budget: Optional[float]` (line 252)
  - `relevance_threshold: float` (line 253)
  - `resume_from_stage: Optional[str]` (line 254)
  - `resume_from_checkpoint: Optional[str]` (line 255)
  - `experimental: bool` (line 256)

**CLI Flags Exposed:**
- ✅ `--dry-run` → `dry_run`
- ✅ `--force` → `force`
- ✅ `--clear-cache` → `clear_cache`
- ✅ `--budget` → `budget`
- ✅ `--relevance-threshold` → `relevance_threshold`
- ✅ `--resume-from-stage` → `resume_from_stage`
- ✅ `--resume --checkpoint-file` → `resume_from_checkpoint`
- ✅ `--enable-experimental` → `experimental`

### Frontend Verification (index.html)

**Status:** ✅ **IMPLEMENTED**

**Code Evidence:**
- Lines 719-945: Complete Advanced Options Panel
- Lines 722-727: Collapsible header with toggle
- Lines 732-746: Dry Run checkbox with CLI badge
- Lines 748-808: Force Re-analysis with cost warning
- Lines 810-826: Clear Cache checkbox
- Lines 828-844: Budget limit input
- Lines 846-863: Relevance threshold slider
- Lines 865-898: Resume from stage dropdown
- Lines 900-922: Checkpoint resume checkbox + file input
- Lines 926-940: Experimental features toggle

**UI Elements Found:**
- ✅ Collapsible panel (lines 722-727)
- ✅ 8 checkboxes/switches (dry-run, force, clear-cache, experimental, checkpoint)
- ✅ 2 number inputs (budget, relevance threshold)
- ✅ 1 slider (relevance threshold)
- ✅ 1 dropdown (resume from stage)
- ✅ 1 text input (checkpoint file)
- ✅ CLI badge labels on each control

### Manual Testing Steps

#### Test 1: Panel Visibility
1. **Navigate** to Dashboard
2. **Locate** "⚙️ Advanced Options" panel
3. **Verify** panel is collapsed by default
4. **Click** header to expand
5. **Expected:** ✅ Panel expands showing all controls

#### Test 2: Dry Run Mode
1. **Expand** Advanced Options
2. **Check** "Dry Run" checkbox
3. **Verify** badge shows "CLI: --dry-run"
4. **Upload** PDFs and configure job
5. **Start** job
6. **Verify** job runs without API calls
7. **Check** logs for dry-run confirmation
8. **Expected:** ✅ Configuration validated, no API spending

#### Test 3: Budget Limit
1. **Enter** budget: `5.00` USD
2. **Start** job
3. **Monitor** cost tracking
4. **Verify** job stops when budget reached
5. **Expected:** ✅ Budget enforced

#### Test 4: Relevance Threshold Slider
1. **Move** relevance threshold slider
2. **Verify** value updates (0.0 - 1.0)
3. **Set** to `0.8`
4. **Start** job
5. **Verify** only papers with similarity ≥ 0.8 included
6. **Expected:** ✅ Threshold applied to filtering

#### Test 5: Resume from Stage
1. **Start** a job and let it run partially
2. **Stop** the job mid-execution
3. **Create** new job with same PDFs
4. **Expand** Advanced Options
5. **Select** resume stage from dropdown (e.g., "gap_analysis")
6. **Start** job
7. **Verify** skipped stages not re-executed
8. **Expected:** ✅ Resumed from checkpoint

#### Test 6: Experimental Features
1. **Check** "Enable Experimental Features"
2. **Verify** warning badge appears
3. **Start** job
4. **Check** logs for experimental feature activation
5. **Expected:** ✅ Experimental features enabled

#### Test 7: All Controls Together
1. **Enable** multiple options simultaneously:
   - Dry Run: ON
   - Budget: $10.00
   - Relevance Threshold: 0.75
   - Experimental: ON
2. **Start** job
3. **Verify** all settings applied
4. **Expected:** ✅ Multi-option configuration works

---

## ✅ Task W1-3: Fresh Analysis Trigger

### Backend Verification (app.py)

**Status:** ✅ **IMPLEMENTED**

**Code Evidence:**
- Lines 642-677: `detect_directory_state()` function implementation
- Line 660: State detection algorithm returns:
  - `"not_exist"` - Directory doesn't exist
  - `"empty"` - Directory exists but empty
  - `"has_csv"` - Has CSV files but no results
  - `"has_results"` - Contains gap_analysis_report.json
- Lines 1553-1555: Fresh analysis determination logic
- Line 1554: `fresh_analysis = dir_state["state"] in ["not_exist", "empty", "has_csv"]`

**Algorithm Found:**
```python
def detect_directory_state(output_dir: Path) -> Dict[str, any]:
    if not output_dir.exists():
        return {"state": "not_exist", "recommended_mode": "fresh", ...}
    
    all_files = list(output_dir.glob("*"))
    if not all_files:
        return {"state": "empty", "recommended_mode": "fresh", ...}
    
    gap_report = output_dir / "gap_analysis_report.json"
    if gap_report.exists():
        return {"state": "has_results", "recommended_mode": "incremental", ...}
    
    csv_files = list(output_dir.glob("*.csv"))
    if csv_files:
        return {"state": "has_csv", "recommended_mode": "fresh", ...}
    
    return {"state": "unknown", "recommended_mode": "fresh", ...}
```

### Frontend Verification (index.html)

**Status:** ✅ **IMPLEMENTED**

**Code Evidence:**
- Lines 1158-1183: Directory State Indicator UI
- Lines 3893-3978: `analyzeOutputDirectory()` function
- Lines 3976-3992: Event listeners calling directory analysis

**UI Elements Found:**
- ✅ State indicator alert box (line 1158)
- ✅ State icon + description (lines 1161-1164)
- ✅ Recommended mode badge (line 1169)
- ✅ "Use Recommended Mode" button (line 1174)
- ✅ "Ignore Recommendation" button (line 1177)

### Manual Testing Steps

#### Test 1: Non-Existent Directory
1. **Select** "Custom Path" mode
2. **Enter** path: `./new_empty_folder_test`
3. **Verify** path doesn't exist yet
4. **Observe** Directory State Indicator
5. **Expected:** 
   - ✅ State: "not_exist"
   - ✅ Recommended: "Fresh Analysis"
   - ✅ Fresh analysis automatically triggered

#### Test 2: Empty Directory
1. **Create** empty directory: `mkdir /tmp/empty_dir_test`
2. **Select** "Custom Path"
3. **Enter** path: `/tmp/empty_dir_test`
4. **Observe** state indicator
5. **Expected:**
   - ✅ State: "empty"
   - ✅ Recommended: "Fresh Analysis"

#### Test 3: Directory with CSV Only
1. **Create** directory: `mkdir /tmp/csv_only_test`
2. **Copy** CSV file: `cp data/*.csv /tmp/csv_only_test/`
3. **Select** "Custom Path"
4. **Enter** path: `/tmp/csv_only_test`
5. **Observe** state indicator
6. **Expected:**
   - ✅ State: "has_csv"
   - ✅ Recommended: "Fresh Analysis"
   - ✅ Existing CSV detected but no results

#### Test 4: Directory with Results
1. **Select** "Select Existing Directory"
2. **Choose** directory with completed analysis
3. **Observe** state indicator
4. **Expected:**
   - ✅ State: "has_results"
   - ✅ Recommended: "Incremental Analysis"
   - ✅ Warning about overwriting

#### Test 5: Accept Recommendation
1. **Select** directory with state "empty"
2. **Click** "✅ Use Recommended Mode" button
3. **Verify** analysis mode switches to "Fresh"
4. **Start** job
5. **Expected:** ✅ Fresh analysis runs

#### Test 6: Ignore Recommendation
1. **Select** directory with state "has_results"
2. **Note** recommendation is "Incremental"
3. **Click** "Ignore Recommendation"
4. **Select** "Fresh Analysis" mode manually
5. **Check** "Overwrite existing results"
6. **Start** job
7. **Expected:** ✅ Fresh analysis overwrites results

---

## ✅ Task W2-1: Config File Upload

### Backend Verification (app.py)

**Status:** ✅ **IMPLEMENTED**

**Code Evidence:**
- Lines 1632-1700: `/api/config/validate` endpoint
- Lines 1702-1798: `/api/jobs/{job_id}/upload-config` endpoint
- Line 1640: Pydantic validation against default config schema
- Lines 1660-1685: Override detection comparing uploaded config vs defaults
- Lines 1750-1760: Custom config stored in job directory

**Validation Found:**
- ✅ JSON schema validation (Pydantic model)
- ✅ Override detection
- ✅ Version checking
- ✅ Required field validation

### Frontend Verification (index.html)

**Status:** ✅ **IMPLEMENTED**

**Code Evidence:**
- Lines 946-1074: Config File Upload UI
- Lines 950-955: File input accepting `.json` files
- Lines 957-959: Template download link
- Lines 962-1001: Config preview card with validation
- Lines 3216-3290: `handleConfigUpload()` function
- Lines 3366-3380: Config upload to backend

**UI Elements Found:**
- ✅ File input (line 950)
- ✅ Template download link (line 958)
- ✅ Validation spinner (lines 973-977)
- ✅ Config preview card (lines 962-1001)
- ✅ Override list display
- ✅ Full JSON viewer (collapsible)
- ✅ Remove button

### Manual Testing Steps

#### Test 1: Download Template
1. **Navigate** to Advanced Options
2. **Locate** "Custom Configuration File" section
3. **Click** "Download template" link
4. **Verify** `pipeline_config.json` downloads
5. **Open** file and verify valid JSON
6. **Expected:** ✅ Template downloaded with default values

#### Test 2: Upload Valid Config
1. **Modify** template: Change `"max_iterations": 5` to `"max_iterations": 10`
2. **Click** "Choose File"
3. **Select** modified config
4. **Observe** upload process
5. **Expected:**
   - ✅ Validation spinner appears
   - ✅ Config preview shows
   - ✅ Override detected: `max_iterations: 10 (default: 5)`
   - ✅ Validation status: ✅ Valid

#### Test 3: Upload Invalid JSON
1. **Create** file: `invalid.json` with syntax error: `{"version": 1.0` (missing closing brace)
2. **Upload** file
3. **Observe** validation
4. **Expected:** ⚠️ Validation error: "Invalid JSON syntax"

#### Test 4: Upload Invalid Schema
1. **Create** config with invalid field: `{"invalid_field": "value"}`
2. **Upload** file
3. **Expected:** ⚠️ Schema validation error

#### Test 5: View Full Config
1. **Upload** valid config
2. **Click** "👁️ View Full Configuration" button
3. **Verify** JSON displayed with syntax highlighting
4. **Expected:** ✅ Full config visible in collapsible section

#### Test 6: Remove Uploaded Config
1. **Upload** config
2. **Click** "✕ Remove" button
3. **Verify** preview disappears
4. **Start** job
5. **Verify** default config used
6. **Expected:** ✅ Custom config removed, defaults restored

#### Test 7: Config Persists in Job
1. **Upload** custom config
2. **Start** job
3. **Check** job directory: `workspace/jobs/{job_id}/pipeline_config.json`
4. **Verify** custom config saved
5. **Expected:** ✅ Custom config file present in job directory

---

## ✅ Task W2-2: Force Re-analysis Control

### Backend Verification (app.py)

**Status:** ✅ **IMPLEMENTED**

**Code Evidence:**
- Line 249: `force: bool` field in `JobConfig`
- Line 250: `force_confirmed: bool` field for confirmation tracking
- Force flag passed to CLI execution

### Frontend Verification (index.html)

**Status:** ✅ **IMPLEMENTED**

**Code Evidence:**
- Lines 748-808: Force Re-analysis UI section
- Lines 752-756: Force checkbox with badge
- Lines 764-788: Cost warning alert box
- Lines 783-786: Confirmation checkbox
- Lines 791-806: Use cases collapse section
- Function: `updateForceWarning()` shows/hides warning

**UI Elements Found:**
- ✅ Force checkbox (line 752)
- ✅ CLI badge: `--force` (line 756)
- ✅ Cost warning alert (line 764)
- ✅ Estimated cost comparison
- ✅ Confirmation checkbox (line 783)
- ✅ "When to Use" educational collapse

### Manual Testing Steps

#### Test 1: Enable Force Warning
1. **Expand** Advanced Options
2. **Check** "Force Re-analysis" checkbox
3. **Expected:**
   - ✅ Cost warning alert appears
   - ⚠️ Shows estimated costs (cached vs. fresh)
   - ⚠️ Confirmation checkbox required

#### Test 2: Cost Estimation (if implemented)
1. **Check** "Force Re-analysis"
2. **Verify** cost warning shows estimates
3. **Expected:** 
   - Cached cost: $0.00
   - Fresh cost: $X.XX
   - Potential waste: $X.XX

> **Note:** Cost estimation API may not be fully implemented. Warning should still appear.

#### Test 3: Confirmation Requirement
1. **Check** "Force Re-analysis"
2. **Leave** confirmation checkbox unchecked
3. **Attempt** to start job
4. **Expected:** ⚠️ Error: "Must confirm force re-analysis"

#### Test 4: Force Confirmed
1. **Check** "Force Re-analysis"
2. **Check** confirmation: "I understand this will bypass cache"
3. **Start** job
4. **Monitor** logs
5. **Verify** cache bypassed
6. **Expected:** ✅ Fresh API calls made despite cache

#### Test 5: Use Cases Display
1. **Check** "Force Re-analysis"
2. **Click** "📖 When should I use this?" link
3. **Verify** collapse expands
4. **Read** use cases:
   - Model updated (e.g., Gemini 2.0)
   - Prompts changed
   - Cache corrupted
   - Validation of previous run
5. **Expected:** ✅ Educational content visible

#### Test 6: Disable Force
1. **Check** "Force Re-analysis"
2. **Observe** warning appears
3. **Uncheck** "Force Re-analysis"
4. **Expected:** ✅ Warning disappears, confirmation reset

---

## ✅ Task W2-3: Cache Management

### Backend Verification (app.py)

**Status:** ⚠️ **PARTIALLY IMPLEMENTED**

**Code Evidence:**
- Lines 1840-1899: `/api/cache/stats` endpoint ✅ IMPLEMENTED
- Returns cache statistics:
  - Entry count per cache directory
  - Total size in MB
  - Oldest/newest entry timestamps
- Covers 3 cache directories:
  - `cache/`
  - `deep_reviewer_cache/`
  - `judge_cache/`

**Missing Features:**
- ❌ `/api/cache/clear` endpoint (not found)
- ❌ Selective clearing by cache type
- ❌ Clear by age functionality
- ❌ Clear by model functionality
- ❌ Cache hit rate calculation endpoint

### Frontend Verification (index.html)

**Status:** ❌ **NOT IMPLEMENTED**

**Code Evidence:**
- Lines 810-826: Clear Cache checkbox exists ✅
- But no cache statistics dashboard found ❌
- No selective clearing UI found ❌
- No cache visualization found ❌

**Expected UI Elements (from task card) NOT FOUND:**
- ❌ Cache Statistics Dashboard
- ❌ Cache breakdown table (by cache type)
- ❌ Cache size chart
- ❌ Hit rate display
- ❌ Selective clear controls
- ❌ Clear by age filter
- ❌ Clear by model filter

### Manual Testing Steps

#### Test 1: Cache Stats API Endpoint ✅ TESTABLE
1. **Open** terminal
2. **Set** API key: `export API_KEY=your-key`
3. **Run** curl command:
   ```bash
   curl -H "X-API-KEY: $API_KEY" http://localhost:8000/api/cache/stats
   ```
4. **Expected:**
   ```json
   {
     "caches": {
       "cache": {
         "entry_count": 42,
         "total_size_mb": 3.45,
         "oldest_entry": "2025-11-20T10:30:00",
         "newest_entry": "2025-11-22T14:15:00"
       },
       "deep_reviewer_cache": {...},
       "judge_cache": {...}
     },
     "total_entries": 156,
     "total_size_mb": 12.34
   }
   ```

#### Test 2: Clear Cache Checkbox ✅ TESTABLE
1. **Expand** Advanced Options
2. **Check** "Clear Cache" checkbox
3. **Start** job
4. **Verify** cache directories emptied before job starts
5. **Expected:** ✅ `--clear-cache` flag passed to CLI

#### Test 3: Cache Dashboard UI ❌ NOT IMPLEMENTED
1. **Navigate** to Dashboard
2. **Look** for "Cache Management" section
3. **Expected:** ❌ No cache dashboard found

#### Test 4: Selective Cache Clearing ❌ NOT IMPLEMENTED
1. **Try** to clear only specific cache (e.g., "deep_reviewer_cache")
2. **Expected:** ❌ No UI controls for selective clearing

### Verification Status: W2-3

**Summary:**
- ✅ **Backend:** Cache stats API implemented
- ✅ **Backend:** Clear all cache via checkbox works
- ❌ **Backend:** Missing selective clear endpoints
- ❌ **Frontend:** No cache dashboard UI
- ❌ **Frontend:** No cache visualization
- ❌ **Frontend:** No selective clear controls

**Recommendation:** Task W2-3 is **PARTIALLY COMPLETE** (~40%). Backend stats work, but comprehensive cache management UI is missing.

---

## 📊 Overall Verification Summary

| Task | Title | Backend | Frontend | Status | Completion |
|------|-------|---------|----------|--------|------------|
| W1-1 | Output Directory Selector | ✅ Full | ✅ Full | **COMPLETE** | 100% |
| W1-2 | Advanced Options Panel | ✅ Full | ✅ Full | **COMPLETE** | 100% |
| W1-3 | Fresh Analysis Trigger | ✅ Full | ✅ Full | **COMPLETE** | 100% |
| W2-1 | Config File Upload | ✅ Full | ✅ Full | **COMPLETE** | 100% |
| W2-2 | Force Re-analysis Control | ✅ Full | ✅ Full | **COMPLETE** | 100% |
| W2-3 | Cache Management | ⚠️ Partial | ❌ Missing | **PARTIAL** | ~40% |

**Overall Status:** 5 of 6 tasks fully implemented (83%)

---

## 🧪 Recommended Testing Sequence

### Phase 1: Individual Feature Testing (2-3 hours)
1. Test W1-1: Output Directory Selector (all 7 test cases)
2. Test W1-2: Advanced Options Panel (all 7 test cases)
3. Test W1-3: Fresh Analysis Trigger (all 6 test cases)
4. Test W2-1: Config File Upload (all 7 test cases)
5. Test W2-2: Force Re-analysis Control (all 6 test cases)
6. Test W2-3: Cache Management (limited tests)

### Phase 2: Integration Testing (1-2 hours)
1. **Test Combo 1:** Custom output dir + Force + Clear cache
2. **Test Combo 2:** Existing dir + Config upload + Experimental
3. **Test Combo 3:** Fresh analysis trigger + Budget + Dry run
4. **Test Combo 4:** All advanced options enabled simultaneously

### Phase 3: Edge Cases (1 hour)
1. Invalid paths (special characters, unicode)
2. Very long paths (>255 characters)
3. Permission denied scenarios
4. Concurrent jobs with same output directory
5. Network/disk full errors

---

## 🐛 Known Issues & Gaps

### Critical Gaps
1. **W2-3 Cache Management:**
   - Missing cache dashboard UI
   - Missing selective clearing controls
   - No cache visualization/charts
   - No hit rate calculation

### Minor Issues
None identified in W1-1 through W2-2.

### Future Enhancements
1. **Cost Estimation:** Full implementation of cost comparison API for force re-analysis
2. **Directory Browser:** Visual directory tree picker instead of text input
3. **Config Diff Viewer:** Side-by-side comparison of custom vs. default config
4. **Cache Analytics:** Historical cache performance metrics

---

## 📝 Test Execution Record

**Tester:** ___________________  
**Date:** ___________________  
**Environment:** ___________________  

### Test Results

| Test Case | Pass | Fail | Notes |
|-----------|------|------|-------|
| W1-1 Test 1 | ☐ | ☐ | |
| W1-1 Test 2 | ☐ | ☐ | |
| W1-1 Test 3 | ☐ | ☐ | |
| W1-1 Test 4 | ☐ | ☐ | |
| W1-1 Test 5 | ☐ | ☐ | |
| W1-1 Test 6 | ☐ | ☐ | |
| W1-1 Test 7 | ☐ | ☐ | |
| W1-2 Test 1 | ☐ | ☐ | |
| W1-2 Test 2 | ☐ | ☐ | |
| W1-2 Test 3 | ☐ | ☐ | |
| W1-2 Test 4 | ☐ | ☐ | |
| W1-2 Test 5 | ☐ | ☐ | |
| W1-2 Test 6 | ☐ | ☐ | |
| W1-2 Test 7 | ☐ | ☐ | |
| W1-3 Test 1 | ☐ | ☐ | |
| W1-3 Test 2 | ☐ | ☐ | |
| W1-3 Test 3 | ☐ | ☐ | |
| W1-3 Test 4 | ☐ | ☐ | |
| W1-3 Test 5 | ☐ | ☐ | |
| W1-3 Test 6 | ☐ | ☐ | |
| W2-1 Test 1 | ☐ | ☐ | |
| W2-1 Test 2 | ☐ | ☐ | |
| W2-1 Test 3 | ☐ | ☐ | |
| W2-1 Test 4 | ☐ | ☐ | |
| W2-1 Test 5 | ☐ | ☐ | |
| W2-1 Test 6 | ☐ | ☐ | |
| W2-1 Test 7 | ☐ | ☐ | |
| W2-2 Test 1 | ☐ | ☐ | |
| W2-2 Test 2 | ☐ | ☐ | |
| W2-2 Test 3 | ☐ | ☐ | |
| W2-2 Test 4 | ☐ | ☐ | |
| W2-2 Test 5 | ☐ | ☐ | |
| W2-2 Test 6 | ☐ | ☐ | |
| W2-3 Test 1 | ☐ | ☐ | |
| W2-3 Test 2 | ☐ | ☐ | |

**Overall Pass Rate:** _____ / 40 tests (____%)

---

## 🎯 Next Steps

1. **Execute manual testing** using this checklist
2. **Document failures** with screenshots and logs
3. **Complete W2-3 implementation** (cache dashboard UI)
4. **Create follow-up bug tickets** for any issues found
5. **Update task cards** with lessons learned
6. **Proceed to W2-4 through W3-4** implementation

---

**Document Version:** 1.0  
**Last Updated:** November 22, 2025  
**Related Documents:**
- `DASHBOARD_CLI_PARITY_ASSESSMENT_V2.md`
- `task-cards/dashboard-cli-parity/IMPLEMENTATION_PLAN.md`
- Individual task cards: `PARITY-W1-1` through `PARITY-W2-3`
