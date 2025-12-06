# Critical Dashboard UX Issues - November 22, 2025

**Status:** 🔴 **BLOCKING ISSUES FOUND**  
**Severity:** HIGH - Prevents normal workflow usage  
**Reporter:** User testing on production Dashboard

---

## 🚨 Issue Summary

Three critical issues discovered during manual verification of tasks W1-1 through W2-3:

1. **Config Template Download Fails** - 401 Unauthorized error
2. **No "Start Analysis" Button for Baseline Mode** - Modal-only workflow confusing
3. **Upload-Centric Design** - Dashboard doesn't support local directory analysis (CLI's primary use case)

---

## Issue #1: Config Template Download Returns 401 Error

### Problem
When clicking "Download template" link in Custom Configuration section, user receives error:
```
Upload failed: Unexpected token '<', "<h"... is not valid JSON
<br>... is not valid JSON
```

**Screenshot:** User reported seeing popup with this error.

### Root Cause
The template download link (`/api/config/template`) requires API key authentication, but the HTML link doesn't pass credentials:

```html
<!-- Current (broken) -->
<a href="/api/config/template" download>Download template</a>
```

**Code Location:** `webdashboard/templates/index.html` line 958

### Impact
- Users cannot download configuration template
- Forces manual creation of `pipeline_config.json`
- Breaks W2-1 (Config File Upload) workflow

### Solution Required
Change link to JavaScript function that passes API key:

```html
<!-- Fixed -->
<a href="#" onclick="downloadConfigTemplate(); return false;">Download template</a>
```

```javascript
async function downloadConfigTemplate() {
    const response = await fetch(`${API_BASE}/api/config/template`, {
        headers: { 'X-API-KEY': apiKey }
    });
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pipeline_config_template.json';
    a.click();
}
```

---

## Issue #2: No "Start Analysis" Button for Baseline (New Review) Mode

### Problem
After uploading PDFs in "New Review" (baseline) mode:
1. User uploads files successfully
2. Configuration modal appears
3. User configures settings (pillars, mode, advanced options)
4. User clicks "🚀 Save & Start Analysis" button
5. **BUT:** The button doesn't actually start the analysis - just saves config

**Expected:** Clicking "Start Analysis" should begin the pipeline execution  
**Actual:** Button only saves configuration, no analysis starts

### Current Workflow (Confusing)
```
Upload PDFs → Config Modal → Save Config → ??? → How to start?
```

**Missing:** The final "Start" trigger after configuration

### Root Cause Analysis

#### What Works (Incremental Mode)
Line 1227: Incremental mode HAS a clear start button:
```html
<button type="button" class="btn btn-success" 
        onclick="if(window.continuationMode) window.continuationMode.startAnalysis()">
    🚀 Start Incremental Analysis
</button>
```

#### What's Broken (Baseline Mode)
Line 1456: The config modal button (`saveConfigAndStart()`) should start analysis but doesn't:
```html
<button type="button" class="btn btn-success" onclick="saveConfigAndStart()">
    🚀 Save & Start Analysis
</button>
```

**Code Location:** `webdashboard/templates/index.html` line 3278
```javascript
async function saveConfigAndStart() {
    // Saves configuration... but doesn't call start job API!
    // Missing: await fetch(`${API_BASE}/api/jobs/${currentJobId}/start`, ...)
}
```

### Impact
- Users cannot start baseline analysis via Dashboard
- Must use CLI to actually run analysis
- Defeats purpose of Dashboard interface
- **BLOCKS:** W1-1, W1-2, W1-3, W2-1, W2-2 from being usable

### Solution Required
Fix `saveConfigAndStart()` function to:
1. Configure job with settings
2. Call `/api/jobs/{job_id}/start` endpoint
3. Close modal
4. Show job in progress in jobs list
5. Navigate to job detail view

---

## Issue #3: Upload-Centric Design Doesn't Match CLI Workflow

### Problem
**Dashboard Assumption:** User uploads PDFs from local computer  
**Reality:** Papers are already on the server in local directories

#### Typical CLI Workflow
```bash
# Papers are already in /project/papers/ directory
cd /project/papers/
ls *.pdf
# neuromorphic_1.pdf, neuromorphic_2.pdf, ... neuromorphic_50.pdf

# Point CLI to this directory
python pipeline_orchestrator.py \
    --data-dir /project/papers/ \
    --output-dir /project/results/review_v1/
```

#### Current Dashboard Workflow (Broken for this use case)
```
1. Dashboard: "Upload papers"
2. User: "My papers are already on the server at /project/papers/"
3. Dashboard: "You must upload them through the browser"
4. User: *uploads 50 files over network*
5. Dashboard: *saves to workspace/uploads/{job_id}/*
6. Result: DUPLICATE files, wasted bandwidth, slow workflow
```

### Why This Is Critical
- Most production use: Papers already exist in project directories
- Server-side file browser exists in HTML (line 1751: "File browser") but not implemented
- CLI's `--data-dir` flag has no Dashboard equivalent
- Forces inefficient workflow (re-uploading existing files)

### Missing Features
1. **Directory Browser:**
   - Select existing directory on server
   - Example: `/workspaces/Literature-Review/data/`
   - Like W3-2 task card (Direct Directory Input)

2. **Server File Picker:**
   - Browse server filesystem
   - Select PDFs without uploading
   - Symlink or reference in place

3. **Data Directory Input:**
   - Text input for path: `/path/to/papers/`
   - Validate directory exists
   - Use files in place (no copy/upload)

### Current Partial Implementation
**Found:** Folder upload via `webkitdirectory` (line 1070)
```html
<input type="file" id="folderInput" webkitdirectory directory multiple>
```

**Problem:** Still uploads files from client, not server filesystem

### Impact
- Dashboard unusable for production workflows
- CLI remains only viable option
- 90% of real-world use cases not supported
- Dashboard-CLI parity = 0% for data input

### Solution Required
Implement one of these approaches:

#### Option A: Server Directory Selector (Recommended)
```html
<div class="mb-3">
    <label>Papers Location:</label>
    <div class="form-check">
        <input type="radio" name="dataSource" value="upload" checked>
        <label>Upload from my computer</label>
    </div>
    <div class="form-check">
        <input type="radio" name="dataSource" value="server">
        <label>Use existing directory on server</label>
    </div>
</div>

<div id="serverDirSection" style="display: none;">
    <input type="text" id="serverDataDir" 
           placeholder="/workspaces/Literature-Review/data/">
    <button onclick="scanServerDirectory()">📁 Browse...</button>
</div>
```

Backend endpoint needed:
```python
@app.post("/api/scan-data-directory")
async def scan_data_directory(directory_path: str):
    """Scan server directory for PDF files"""
    path = Path(directory_path)
    if not path.exists() or not path.is_dir():
        raise HTTPException(404, "Directory not found")
    
    pdfs = list(path.glob("**/*.pdf"))
    return {
        "directory": str(path),
        "pdf_count": len(pdfs),
        "files": [{"name": p.name, "path": str(p)} for p in pdfs]
    }
```

#### Option B: File Browser UI
Add interactive directory tree browser (like VS Code file explorer)

#### Option C: Symlink Upload Directory
Allow specifying existing directory as upload source:
```python
# Instead of copying files, create job that references existing directory
job_data["data_dir"] = "/path/to/existing/papers/"
job_data["files_referenced"] = True  # Don't copy
```

---

## 📊 Impact Assessment

### Severity Breakdown
| Issue | Severity | Blocks Tasks | Users Affected |
|-------|----------|--------------|----------------|
| #1 Config Download | MEDIUM | W2-1 | 100% wanting custom config |
| #2 No Start Button | **CRITICAL** | W1-1, W1-2, W1-3, W2-1, W2-2 | 100% using baseline mode |
| #3 Upload-Only Design | **CRITICAL** | All workflows | 90% of production use |

### User Impact
- **Issue #1:** Workaround exists (manually create config) - annoying but not blocking
- **Issue #2:** **NO WORKAROUND** - Dashboard completely broken for starting analysis
- **Issue #3:** **NO WORKAROUND** - Forces inefficient upload of existing files

### Parity Impact
Current assessment claimed 68% → 95% parity target.

**Reality:**
- Config download: Implemented but broken
- Start analysis: **NOT IMPLEMENTED** (critical gap)
- Local directory support: **NOT IMPLEMENTED** (fundamental design issue)

**Revised Parity:** ~40% (accounting for broken/missing core workflows)

---

## 🔧 Immediate Fixes Required

### Priority 1: Fix Start Analysis (CRITICAL)
**Estimate:** 1-2 hours  
**Files:** `webdashboard/templates/index.html` (function `saveConfigAndStart`)

```javascript
async function saveConfigAndStart() {
    try {
        // 1. Save configuration
        const config = {
            pillar_selections: getSelectedPillars(),
            run_mode: document.getElementById('runMode').value,
            convergence_threshold: parseFloat(document.getElementById('convergenceThreshold').value),
            output_dir_mode: document.querySelector('input[name="outputDirMode"]:checked').value,
            output_dir_path: document.getElementById('customOutputPath').value || null,
            dry_run: document.getElementById('dryRunMode').checked,
            force: document.getElementById('forceReanalysis').checked,
            clear_cache: document.getElementById('clearCache').checked,
            budget: parseFloat(document.getElementById('budgetLimit').value) || null,
            relevance_threshold: parseFloat(document.getElementById('relevanceThreshold').value),
            experimental: document.getElementById('experimentalFeatures').checked
        };
        
        // 2. Configure job
        const configResponse = await fetch(`${API_BASE}/api/jobs/${currentJobId}/configure`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': apiKey
            },
            body: JSON.stringify(config)
        });
        
        if (!configResponse.ok) throw new Error('Failed to configure job');
        
        // 3. START THE JOB (CURRENTLY MISSING!)
        const startResponse = await fetch(`${API_BASE}/api/jobs/${currentJobId}/start`, {
            method: 'POST',
            headers: { 'X-API-KEY': apiKey }
        });
        
        if (!startResponse.ok) throw new Error('Failed to start job');
        
        // 4. Close modal and show success
        const modal = bootstrap.Modal.getInstance(document.getElementById('configModal'));
        modal.hide();
        
        alert(`✅ Analysis started! Job ID: ${currentJobId}`);
        
        // 5. Refresh jobs list
        loadJobs();
        
    } catch (error) {
        alert('Failed to start analysis: ' + error.message);
    }
}
```

### Priority 2: Fix Config Template Download
**Estimate:** 30 minutes  
**Files:** `webdashboard/templates/index.html`

Add function and change link (see Issue #1 solution above).

### Priority 3: Add Server Directory Support (Design Decision Needed)
**Estimate:** 4-8 hours  
**Decision Required:** Which approach (A, B, or C)?

---

## 🧪 Testing Validation

### Test Case: Issue #2 (Start Analysis)
1. Upload PDF files in baseline mode
2. Configure job (select pillars, set run mode)
3. Click "🚀 Save & Start Analysis"
4. **Expected:** Job status changes to "running", appears in jobs list
5. **Expected:** Pipeline begins execution (logs show activity)
6. **Expected:** Can view real-time progress

### Test Case: Issue #3 (Local Directory)
1. Have PDFs in `/workspaces/Literature-Review/data/`
2. Navigate to Dashboard
3. Select "Use existing directory on server"
4. Enter path: `/workspaces/Literature-Review/data/`
5. Click "Scan" - shows 5 PDFs found
6. Configure and start
7. **Expected:** Analysis runs on existing files (no upload)
8. **Verify:** No files copied to `workspace/uploads/`

---

## 📋 Related Issues

### From Task Cards
- **W3-2:** Direct Directory Input - Addresses issue #3
- **PARITY-W1-1:** Output Directory Selector - Partially implemented
- **PARITY-W2-1:** Config File Upload - Issue #1 breaks this

### Verification Documents
- `PARITY_W1-1_TO_W2-3_MANUAL_VERIFICATION.md` - Test 1-40
- `PARITY_W1-1_TO_W2-3_AUTOMATED_TEST_RESULTS.md` - Shows 5/6 complete

**Gap:** Automated verification checked code existence, not functional workflows

---

## 🎯 Recommendation

### Immediate Actions (Week 9, Sprint 1)
1. **Fix Issue #2** (start analysis) - **MUST DO** - 1-2 hours
2. **Fix Issue #1** (config download) - **SHOULD DO** - 30 min
3. **Decide on Issue #3** approach - **DISCUSS** - 1 hour planning

### Short-term (Week 9, Sprint 2)
4. **Implement Issue #3** solution - 4-8 hours
5. **Re-test all W1-W2 tasks** - 2-3 hours
6. **Update parity assessment** - 1 hour

### Testing Protocol
- Manual testing REQUIRED for all workflows
- Automated checks insufficient (found code but not functionality)
- User acceptance testing before claiming "implemented"

---

## 📝 Lessons Learned

### Code Inspection ≠ Functional Testing
- Found all UI elements ✅
- Found all backend endpoints ✅  
- **BUT:** Workflows broken/incomplete ❌

### Missing Integration Testing
- Individual components work
- End-to-end workflows not tested
- Modal → Configuration → Start → Execute chain broken

### Dashboard Design Assumptions
- Assumed upload-centric workflow
- Didn't account for server-side file analysis
- CLI parity requires rethinking data input model

---

**Status:** 🔴 **BLOCKING**  
**Next:** Fix Issue #2 immediately to unblock testing  
**Owner:** Development team  
**Due:** Before completing Wave 1 tasks

**Document Version:** 1.0  
**Date:** November 22, 2025  
**Reporter:** User manual testing session
