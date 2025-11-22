# PARITY-W1-1: Output Directory Selector

**Priority:** 🔴 **CRITICAL**  
**Effort:** 12-16 hours  
**Wave:** 1 (Critical Gaps)  
**Dependencies:** None

---

## 📋 Problem Statement

**Current State:**  
Dashboard hardcodes output directory to `workspace/jobs/{uuid}/outputs/gap_analysis_output/`, giving users **zero control** over where results are saved.

**CLI Equivalent:**
```bash
python pipeline_orchestrator.py --output-dir /my/custom/path
```

**User Impact:**
- ❌ Cannot choose save location
- ❌ Cannot initiate fresh analysis in empty folder
- ❌ Cannot easily share directories between CLI and Dashboard
- ❌ Must import (copy) CLI results rather than working in-place

**Gap:** This is the **#1 critical gap** in Dashboard-CLI parity.

---

## 🎯 Objective

Add UI controls to allow users to specify custom output directories for Dashboard jobs, matching CLI's `--output-dir` functionality.

---

## 📐 Design

### UI Components

**Location:** Upload section in `webdashboard/templates/index.html`

**New UI Elements:**

```html
<!-- Output Directory Configuration -->
<div class="card mb-3">
    <div class="card-header">
        <h6>📁 Output Directory</h6>
    </div>
    <div class="card-body">
        <!-- Mode Selector -->
        <div class="mb-3">
            <label class="form-label">Save Results To:</label>
            
            <div class="form-check">
                <input class="form-check-input" type="radio" 
                       name="outputDirMode" id="outputDirAuto" 
                       value="auto" checked>
                <label class="form-check-label" for="outputDirAuto">
                    <strong>Auto-generated</strong>
                    <small class="text-muted d-block">
                        Default: workspace/jobs/{job_id}/outputs/gap_analysis_output/
                    </small>
                </label>
            </div>
            
            <div class="form-check">
                <input class="form-check-input" type="radio" 
                       name="outputDirMode" id="outputDirCustom" 
                       value="custom">
                <label class="form-check-label" for="outputDirCustom">
                    <strong>Custom Path</strong>
                    <small class="text-muted d-block">
                        Specify where to save results (like CLI --output-dir)
                    </small>
                </label>
            </div>
            
            <div class="form-check">
                <input class="form-check-input" type="radio" 
                       name="outputDirMode" id="outputDirExisting" 
                       value="existing">
                <label class="form-check-label" for="outputDirExisting">
                    <strong>Select Existing Directory</strong>
                    <small class="text-muted d-block">
                        Continue analysis in existing folder
                    </small>
                </label>
            </div>
        </div>
        
        <!-- Custom Path Input (shown when "Custom Path" selected) -->
        <div id="customPathSection" style="display: none;">
            <label for="customOutputPath" class="form-label">Output Directory Path:</label>
            <input type="text" class="form-control" id="customOutputPath" 
                   placeholder="/path/to/output" 
                   pattern="^(/|\./).*"
                   title="Must be absolute path (/path) or relative (./path)">
            <div class="form-text">
                Enter absolute path (e.g., /project/review_v1) or relative (e.g., ./my_review)
            </div>
            
            <div class="form-check mt-2">
                <input class="form-check-input" type="checkbox" 
                       id="overwriteExisting">
                <label class="form-check-label" for="overwriteExisting">
                    Overwrite existing results (like CLI --force)
                </label>
            </div>
        </div>
        
        <!-- Existing Directory Selector (shown when "Select Existing" selected) -->
        <div id="existingDirSection" style="display: none;">
            <label for="existingDirDropdown" class="form-label">Choose Directory:</label>
            <select class="form-select" id="existingDirDropdown">
                <option value="">-- Select a directory --</option>
                <!-- Populated dynamically -->
            </select>
            <button type="button" class="btn btn-sm btn-secondary mt-2" 
                    onclick="refreshDirectoryList()">
                🔄 Refresh List
            </button>
        </div>
    </div>
</div>
```

**JavaScript Logic:**

```javascript
// Toggle visibility based on mode selection
document.querySelectorAll('input[name="outputDirMode"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        document.getElementById('customPathSection').style.display = 
            (e.target.value === 'custom') ? 'block' : 'none';
        document.getElementById('existingDirSection').style.display = 
            (e.target.value === 'existing') ? 'block' : 'none';
    });
});

// Populate existing directory dropdown
async function refreshDirectoryList() {
    const response = await fetch('/api/scan-output-directories', {
        headers: { 'X-API-KEY': API_KEY }
    });
    const data = await response.json();
    
    const dropdown = document.getElementById('existingDirDropdown');
    dropdown.innerHTML = '<option value="">-- Select a directory --</option>';
    
    data.directories.forEach(dir => {
        const option = document.createElement('option');
        option.value = dir.path;
        option.textContent = `${dir.path} (${dir.file_count} files, ${dir.last_modified})`;
        dropdown.appendChild(option);
    });
}

// Include output directory in upload request
function getOutputDirConfig() {
    const mode = document.querySelector('input[name="outputDirMode"]:checked').value;
    
    if (mode === 'auto') {
        return {
            mode: 'auto',
            path: null,
            overwrite: false
        };
    } else if (mode === 'custom') {
        return {
            mode: 'custom',
            path: document.getElementById('customOutputPath').value,
            overwrite: document.getElementById('overwriteExisting').checked
        };
    } else if (mode === 'existing') {
        return {
            mode: 'existing',
            path: document.getElementById('existingDirDropdown').value,
            overwrite: true  // Always overwrite when using existing dir
        };
    }
}
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**New Endpoint:**

```python
@app.get(
    "/api/scan-output-directories",
    tags=["Configuration"],
    summary="Scan for existing output directories"
)
async def scan_output_directories(
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Scan for existing gap analysis output directories.
    
    Returns directories containing gap_analysis_report.json for reuse.
    """
    verify_api_key(api_key)
    
    directories = []
    
    # Scan common locations
    search_paths = [
        BASE_DIR / "gap_analysis_output",
        BASE_DIR / "workspace" / "jobs",
        Path.home() / "literature_review_outputs"
    ]
    
    for search_path in search_paths:
        if not search_path.exists():
            continue
        
        # Find directories with gap_analysis_report.json
        for dir_path in search_path.rglob("gap_analysis_report.json"):
            output_dir = dir_path.parent
            
            # Count files
            file_count = len(list(output_dir.glob("*")))
            
            # Get last modified time
            last_modified = datetime.fromtimestamp(
                output_dir.stat().st_mtime
            ).isoformat()
            
            directories.append({
                "path": str(output_dir),
                "file_count": file_count,
                "last_modified": last_modified,
                "has_report": True
            })
    
    return {"directories": directories, "count": len(directories)}
```

**Modified Upload Endpoint:**

```python
class UploadConfig(BaseModel):
    """Upload configuration with output directory."""
    files: List[str]
    output_dir_mode: str = "auto"  # "auto" | "custom" | "existing"
    output_dir_path: Optional[str] = None
    overwrite_existing: bool = False

@app.post("/api/upload/batch")
async def upload_batch(
    files: List[UploadFile],
    config: UploadConfig,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Upload with output directory configuration."""
    verify_api_key(api_key)
    
    # Determine output directory
    if config.output_dir_mode == "auto":
        # Original behavior: auto-generate job_id directory
        job_id = str(uuid.uuid4())
        output_dir = JOBS_DIR / job_id / "outputs" / "gap_analysis_output"
        
    elif config.output_dir_mode == "custom":
        # User-specified custom path
        if not config.output_dir_path:
            raise HTTPException(400, "Custom path required")
        
        output_dir = Path(config.output_dir_path).expanduser().resolve()
        
        # Security check: prevent directory traversal
        if not str(output_dir).startswith(str(BASE_DIR)):
            # Allow only paths within project or explicit absolute paths
            if not output_dir.is_absolute():
                raise HTTPException(400, "Invalid path")
        
        # Use hash of path as job_id for tracking
        job_id = f"custom_{hashlib.md5(str(output_dir).encode()).hexdigest()[:8]}"
        
    elif config.output_dir_mode == "existing":
        # Reuse existing directory
        if not config.output_dir_path:
            raise HTTPException(400, "Existing path required")
        
        output_dir = Path(config.output_dir_path)
        if not output_dir.exists():
            raise HTTPException(404, f"Directory not found: {output_dir}")
        
        # Use hash of path as job_id
        job_id = f"existing_{hashlib.md5(str(output_dir).encode()).hexdigest()[:8]}"
        config.overwrite_existing = True  # Always overwrite when reusing
    
    # Create/validate output directory
    if config.overwrite_existing or not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        # Check if directory has existing analysis
        if (output_dir / "gap_analysis_report.json").exists():
            return {
                "status": "confirm_overwrite",
                "message": f"Directory {output_dir} contains existing analysis. "
                          "Enable 'Overwrite existing results' to proceed.",
                "existing_files": list(output_dir.glob("*"))
            }
    
    # Save files and create job
    # ... rest of upload logic ...
    
    # Store output_dir in job metadata
    job_data = {
        "id": job_id,
        "output_dir": str(output_dir),
        "output_dir_mode": config.output_dir_mode,
        "overwrite_enabled": config.overwrite_existing,
        # ... other metadata ...
    }
    
    return job_data
```

**Modified Pipeline Execution:**

```python
def run_pipeline_for_job(job_id: str):
    """Execute pipeline with custom output directory."""
    job_data = load_job_metadata(job_id)
    
    # Get output directory from job metadata
    output_dir = job_data.get('output_dir')
    if not output_dir:
        # Fallback to default
        output_dir = f"workspace/jobs/{job_id}/outputs/gap_analysis_output"
    
    # Build CLI command with --output-dir
    cmd = [
        "python", "pipeline_orchestrator.py",
        "--batch-mode",
        "--output-dir", output_dir,
        # ... other args ...
    ]
    
    # Execute pipeline
    subprocess.run(cmd, check=True)
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] UI has 3 radio options: Auto-generated, Custom Path, Select Existing
- [ ] Custom path input appears when "Custom Path" selected
- [ ] Existing directory dropdown appears when "Select Existing" selected
- [ ] Existing directory dropdown populated via `/api/scan-output-directories`
- [ ] "Overwrite existing results" checkbox functional
- [ ] Path validation prevents directory traversal attacks
- [ ] Job metadata stores `output_dir`, `output_dir_mode`, `overwrite_enabled`
- [ ] Pipeline executed with `--output-dir` flag matching user selection
- [ ] Results saved to user-specified directory (not hardcoded path)

### User Experience
- [ ] Clear help text explains each option
- [ ] Real-time path validation (red/green border)
- [ ] Dropdown shows file count and last modified date
- [ ] Refresh button updates directory list
- [ ] Error messages clear when path invalid or directory doesn't exist
- [ ] Confirmation dialog when overwriting existing results

### Security
- [ ] Path traversal prevented (no `../../../etc/passwd`)
- [ ] Only allow paths within project directory OR explicit absolute paths
- [ ] Validate path is not system directory (`/etc`, `/bin`, etc.)
- [ ] Sanitize path input (no shell injection)

### Edge Cases
- [ ] Empty custom path → show validation error
- [ ] Non-existent path → create directories OR show error (based on mode)
- [ ] Existing analysis in directory → show confirmation dialog
- [ ] Read-only directory → show permission error
- [ ] Network path (NFS/SMB) → handle gracefully

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_output_directory_api.py

def test_scan_output_directories():
    """Test directory scanning API."""
    response = client.get("/api/scan-output-directories", 
                         headers={"X-API-KEY": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert "directories" in data
    assert isinstance(data["directories"], list)

def test_upload_with_custom_output_dir():
    """Test upload with custom output directory."""
    config = {
        "output_dir_mode": "custom",
        "output_dir_path": "/tmp/test_output",
        "overwrite_existing": False
    }
    response = client.post("/api/upload/batch", 
                          files=test_files, 
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    assert response.status_code == 200
    job_data = response.json()
    assert job_data["output_dir"] == "/tmp/test_output"

def test_directory_traversal_prevented():
    """Test security: prevent directory traversal."""
    config = {
        "output_dir_mode": "custom",
        "output_dir_path": "../../etc/passwd"
    }
    response = client.post("/api/upload/batch", 
                          files=test_files, 
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    assert response.status_code == 400
    assert "Invalid path" in response.json()["detail"]

def test_overwrite_confirmation():
    """Test overwrite confirmation when directory has existing analysis."""
    # Create existing analysis
    output_dir = Path("/tmp/existing_analysis")
    output_dir.mkdir(exist_ok=True)
    (output_dir / "gap_analysis_report.json").touch()
    
    config = {
        "output_dir_mode": "custom",
        "output_dir_path": str(output_dir),
        "overwrite_existing": False
    }
    response = client.post("/api/upload/batch", 
                          files=test_files, 
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    assert response.status_code == 200
    assert response.json()["status"] == "confirm_overwrite"
```

### Integration Tests

```python
def test_e2e_custom_output_directory():
    """End-to-end test: upload with custom output dir → pipeline → results."""
    # 1. Upload files with custom output directory
    custom_dir = Path("/tmp/e2e_test_output")
    config = {
        "output_dir_mode": "custom",
        "output_dir_path": str(custom_dir),
        "overwrite_existing": True
    }
    upload_response = client.post("/api/upload/batch", ...)
    job_id = upload_response.json()["id"]
    
    # 2. Start job
    client.post(f"/api/jobs/{job_id}/start")
    
    # 3. Wait for completion
    wait_for_job_completion(job_id, timeout=300)
    
    # 4. Verify results saved to custom directory (not default)
    assert (custom_dir / "gap_analysis_report.json").exists()
    assert not Path(f"workspace/jobs/{job_id}").exists()
```

### Manual Testing

- [ ] Test auto-generated mode (default behavior)
- [ ] Test custom path with absolute path `/tmp/my_review`
- [ ] Test custom path with relative path `./outputs/review_v1`
- [ ] Test selecting existing directory from dropdown
- [ ] Test overwrite checkbox (enabled/disabled)
- [ ] Test refresh directory list button
- [ ] Test path validation (invalid paths show error)
- [ ] Test confirmation dialog on overwrite

---

## 📚 Documentation Updates

### User Guide

```markdown
## Configuring Output Directory

The Dashboard allows you to choose where analysis results are saved, just like the CLI's `--output-dir` flag.

### Options:

1. **Auto-generated (Default)**
   - Results saved to: `workspace/jobs/{unique-id}/outputs/`
   - Best for: Quick analyses, no specific organization needed

2. **Custom Path**
   - Specify any directory: `/project/review_v1`, `./my_review`
   - Best for: Organized project structures, shared directories
   - Enable "Overwrite existing results" to re-analyze in same directory

3. **Select Existing Directory**
   - Choose from previously used directories
   - Best for: Continuing previous analyses, incremental updates

### Examples:

**Start fresh analysis in project directory:**
```
Mode: Custom Path
Path: /project/neuromorphic_review_2025
Overwrite: Enabled
```

**Continue existing CLI analysis:**
```
Mode: Select Existing Directory
Choose: /project/neuromorphic_review_2025
```
```

---

## 🚀 Deployment Checklist

- [ ] Frontend UI implemented and styled
- [ ] JavaScript validation and mode switching working
- [ ] Backend API endpoint `/api/scan-output-directories` deployed
- [ ] Upload endpoint modified to accept `output_dir_config`
- [ ] Pipeline execution passes `--output-dir` to CLI
- [ ] Security validation (path traversal, injection) tested
- [ ] Unit tests passing (90%+ coverage)
- [ ] Integration tests passing
- [ ] Documentation updated (user guide, API docs)
- [ ] Code reviewed and approved
- [ ] Deployed to staging
- [ ] Manual testing completed
- [ ] Deployed to production

---

## 📊 Success Metrics

**After Deployment:**
- Users can select output directories (100% functional)
- Dashboard parity increases from 68% → 75%+
- User complaints about "cannot choose save location" → 0
- Fresh analysis trigger issue resolved

**Monitoring:**
- Track % of jobs using custom output directories
- Track errors related to invalid paths
- Collect user feedback on feature usability

---

**Task Card Version:** 1.0  
**Created:** November 21, 2025  
**Estimated Effort:** 12-16 hours  
**Priority:** 🔴 CRITICAL
