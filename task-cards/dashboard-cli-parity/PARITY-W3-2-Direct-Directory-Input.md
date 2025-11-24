# PARITY-W3-2: Direct Directory Input

**Priority:** 🔴 **HIGH** (was MEDIUM - upgraded due to production need)  
**Effort:** 6-8 hours (was 12-16 - reduced due to simple subprocess implementation)  
**Wave:** 3 (Enhancement Features)  
**Dependencies:** PARITY-W1-1 (Output Directory Selector)  
**Relation:** Essentially same as PARITY-CRITICAL-1 (server directory input)

---

## 📋 Problem Statement

**Current State:**  
Dashboard requires users to upload individual PDF/CSV files through file picker. Users with papers already on the server cannot directly point to those directories - must upload via browser or manually select all files.

**CLI Capability:**
```bash
# Direct directory input (server paths)
python pipeline_orchestrator.py --data-dir /path/to/papers/

# Pipeline scans directory for PDFs/CSVs automatically
# Supports nested directories
```

**User Problems:**
- Have 100 PDFs in server folder → must upload or select all individually
- Cannot use existing organized paper directories on server
- Cannot leverage server file organization
- Time-consuming multi-file selection
- No support for nested directories
- Cannot point to server network shares or mounted drives

**Gap:** No directory input option in Dashboard.

---

## 🎯 Objective

Add direct directory input capability matching CLI's `--data-dir` flag, allowing users to provide a directory path that the pipeline scans for papers automatically.

**Architecture Note:** Dashboard runs server-side Python and executes the CLI via `subprocess.run()`. This means the Dashboard can access any directory on the server filesystem, just like the CLI. The "directory path" input refers to **server paths** (e.g., `/workspaces/Literature-Review/data/`), not the user's local computer.

---

## 📐 Design

### UI Components

**Location:** Main upload panel in `webdashboard/templates/index.html`

**Enhanced Upload Panel with Directory Input:**

```html
<!-- Enhanced Upload Panel with Directory Input -->
<div class="card mb-4">
    <div class="card-header bg-primary text-white">
        <h5 class="mb-0">📂 Step 1: Provide Papers</h5>
    </div>
    <div class="card-body">
        
        <!-- Input Method Selector -->
        <div class="btn-group w-100 mb-3" role="group">
            <input type="radio" class="btn-check" name="inputMethod" 
                   id="inputMethodUpload" value="upload" checked
                   onchange="updateInputMethod()">
            <label class="btn btn-outline-primary" for="inputMethodUpload">
                📤 Upload Files
                <br><small class="text-muted">Select PDFs/CSVs</small>
            </label>
            
            <input type="radio" class="btn-check" name="inputMethod" 
                   id="inputMethodDirectory" value="directory"
                   onchange="updateInputMethod()">
            <label class="btn btn-outline-primary" for="inputMethodDirectory">
                📁 Directory Path
                <br><small class="text-muted">Point to folder</small>
            </label>
        </div>
        
        <!-- Upload Method (Original) -->
        <div id="uploadMethodPanel">
            <div class="mb-3">
                <label for="pdfFiles" class="form-label">
                    <strong>Upload Paper Files</strong>
                </label>
                <input class="form-control" type="file" id="pdfFiles" 
                       accept=".pdf,.csv" multiple
                       onchange="handleFileSelection(this)">
                <div class="form-text">
                    Select one or more PDF or CSV files (max 100MB total)
                </div>
            </div>
            
            <div id="uploadPreview" style="display: none;">
                <div class="alert alert-info">
                    <strong>📄 Selected Files:</strong> 
                    <span id="uploadFileCount">0</span> files, 
                    <span id="uploadTotalSize">0 MB</span>
                    <button class="btn btn-sm btn-outline-secondary float-end" 
                            onclick="clearFileSelection()">Clear</button>
                </div>
            </div>
        </div>
        
        <!-- Directory Method (New) -->
        <div id="directoryMethodPanel" style="display: none;">
            
            <!-- Directory Path Input -->
            <div class="mb-3">
                <label for="directoryPath" class="form-label">
                    <strong>Directory Path</strong>
                    <span class="badge bg-primary">CLI: --data-dir</span>
                </label>
                <div class="input-group">
                    <span class="input-group-text">📁</span>
                    <input type="text" class="form-control" id="directoryPath"
                           placeholder="/path/to/papers" 
                           onblur="validateDirectoryPath()">
                    <button class="btn btn-outline-secondary" type="button"
                            onclick="browseDirectory()">
                        Browse...
                    </button>
                    <button class="btn btn-outline-primary" type="button"
                            onclick="scanDirectory()">
                        🔍 Scan
                    </button>
                </div>
                <div class="form-text">
                    Absolute path to directory containing PDFs or CSVs. 
                    Pipeline will scan recursively for papers.
                </div>
            </div>
            
            <!-- Directory Scan Options -->
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" 
                           id="scanRecursive" checked>
                    <label class="form-check-label" for="scanRecursive">
                        <strong>Scan subdirectories recursively</strong>
                        <small class="text-muted d-block">
                            Find papers in nested folders
                        </small>
                    </label>
                </div>
                
                <div class="form-check mt-2">
                    <input class="form-check-input" type="checkbox" 
                           id="followSymlinks">
                    <label class="form-check-label" for="followSymlinks">
                        <strong>Follow symbolic links</strong>
                        <small class="text-muted d-block">
                            Include papers from linked directories
                        </small>
                    </label>
                </div>
            </div>
            
            <!-- Directory Validation Results -->
            <div id="directoryValidation" style="display: none;">
                <!-- Success -->
                <div id="directoryValid" style="display: none;" class="alert alert-success">
                    <h6>✅ Directory Valid</h6>
                    <dl class="row mb-0">
                        <dt class="col-sm-3">Path:</dt>
                        <dd class="col-sm-9"><code id="validDirPath"></code></dd>
                        
                        <dt class="col-sm-3">PDFs Found:</dt>
                        <dd class="col-sm-9" id="validDirPdfs">0</dd>
                        
                        <dt class="col-sm-3">CSVs Found:</dt>
                        <dd class="col-sm-9" id="validDirCsvs">0</dd>
                        
                        <dt class="col-sm-3">Total Size:</dt>
                        <dd class="col-sm-9" id="validDirSize">0 MB</dd>
                        
                        <dt class="col-sm-3">Subdirectories:</dt>
                        <dd class="col-sm-9" id="validDirSubdirs">0</dd>
                    </dl>
                    
                    <button class="btn btn-sm btn-outline-primary mt-2" 
                            onclick="showDirectoryContents()">
                        📋 View File List
                    </button>
                </div>
                
                <!-- Error -->
                <div id="directoryInvalid" style="display: none;" class="alert alert-danger">
                    <h6>❌ Directory Issue</h6>
                    <p id="directoryError" class="mb-0"></p>
                    <div class="mt-2">
                        <strong>Common Issues:</strong>
                        <ul class="mb-0">
                            <li>Directory does not exist</li>
                            <li>No read permissions</li>
                            <li>Path is not a directory (is a file)</li>
                            <li>No PDFs or CSVs found in directory</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <!-- Directory Contents Modal Trigger (hidden, populated by scan) -->
            <div id="directoryContents" style="display: none;">
                <!-- Populated by scan results -->
            </div>
            
            <!-- Security Warning -->
            <div class="alert alert-warning">
                <strong>🔒 Security Note:</strong> 
                Server will validate directory path and permissions. 
                Only accessible directories can be used. 
                Path traversal attempts will be rejected.
            </div>
            
        </div>
        
    </div>
</div>

<!-- Directory File List Modal -->
<div class="modal fade" id="directoryFilesModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">📋 Files in Directory</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Filename</th>
                                <th>Type</th>
                                <th>Size</th>
                                <th>Modified</th>
                            </tr>
                        </thead>
                        <tbody id="directoryFilesList">
                            <!-- Populated by scan -->
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>

<script>
// Update input method display
function updateInputMethod() {
    const method = document.querySelector('input[name="inputMethod"]:checked').value;
    
    document.getElementById('uploadMethodPanel').style.display = 
        method === 'upload' ? 'block' : 'none';
    document.getElementById('directoryMethodPanel').style.display = 
        method === 'directory' ? 'block' : 'none';
    
    // Clear validation when switching methods
    document.getElementById('directoryValidation').style.display = 'none';
}

// Validate directory path (basic format check before server validation)
function validateDirectoryPath() {
    const path = document.getElementById('directoryPath').value.trim();
    
    if (!path) {
        return;
    }
    
    // Basic validation
    if (!path.startsWith('/') && !path.match(/^[A-Za-z]:\\/)) {
        alert('Please provide an absolute path (starting with / or C:\\)');
        return;
    }
    
    // Trigger scan for full validation
    scanDirectory();
}

// Browse for directory (server-side directory browser)
function browseDirectory() {
    // Note: This opens a server-side directory browser
    // Users navigate the server filesystem, not their local machine
    
    // Open server directory browser modal
    openServerDirectoryBrowser();
}

// Scan directory for papers
async function scanDirectory() {
    const path = document.getElementById('directoryPath').value.trim();
    
    if (!path) {
        alert('Please enter a directory path');
        return;
    }
    
    const recursive = document.getElementById('scanRecursive').checked;
    const followSymlinks = document.getElementById('followSymlinks').checked;
    
    try {
        const response = await fetch('/api/directory/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            },
            body: JSON.stringify({
                path: path,
                recursive: recursive,
                follow_symlinks: followSymlinks
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayDirectoryScanSuccess(data);
        } else {
            displayDirectoryScanError(data.detail || 'Failed to scan directory');
        }
        
    } catch (error) {
        console.error('Directory scan failed:', error);
        displayDirectoryScanError('Network error: ' + error.message);
    }
}

// Display successful scan results
function displayDirectoryScanSuccess(data) {
    document.getElementById('directoryValidation').style.display = 'block';
    document.getElementById('directoryValid').style.display = 'block';
    document.getElementById('directoryInvalid').style.display = 'none';
    
    document.getElementById('validDirPath').textContent = data.path;
    document.getElementById('validDirPdfs').textContent = data.pdf_count;
    document.getElementById('validDirCsvs').textContent = data.csv_count;
    document.getElementById('validDirSize').textContent = 
        (data.total_size_bytes / 1024 / 1024).toFixed(2) + ' MB';
    document.getElementById('validDirSubdirs').textContent = data.subdirectory_count;
    
    // Store scan results for job creation
    window.directoryScanResults = data;
}

// Display scan error
function displayDirectoryScanError(errorMessage) {
    document.getElementById('directoryValidation').style.display = 'block';
    document.getElementById('directoryValid').style.display = 'none';
    document.getElementById('directoryInvalid').style.display = 'block';
    
    document.getElementById('directoryError').textContent = errorMessage;
}

// Show directory contents in modal
function showDirectoryContents() {
    if (!window.directoryScanResults) {
        alert('No scan results available');
        return;
    }
    
    const tbody = document.getElementById('directoryFilesList');
    tbody.innerHTML = '';
    
    window.directoryScanResults.files.forEach(file => {
        const row = tbody.insertRow();
        row.insertCell().textContent = file.filename;
        row.insertCell().textContent = file.type.toUpperCase();
        row.insertCell().textContent = (file.size_bytes / 1024).toFixed(1) + ' KB';
        row.insertCell().textContent = new Date(file.modified).toLocaleString();
    });
    
    const modal = new bootstrap.Modal(document.getElementById('directoryFilesModal'));
    modal.show();
}

// Get input data for job creation
function getInputData() {
    const method = document.querySelector('input[name="inputMethod"]:checked').value;
    
    if (method === 'upload') {
        // Existing upload logic
        return {
            method: 'upload',
            files: document.getElementById('pdfFiles').files
        };
    } else {
        // Directory input
        if (!window.directoryScanResults) {
            throw new Error('Please scan directory first');
        }
        
        return {
            method: 'directory',
            path: window.directoryScanResults.path,
            recursive: document.getElementById('scanRecursive').checked,
            follow_symlinks: document.getElementById('followSymlinks').checked,
            file_count: window.directoryScanResults.pdf_count + window.directoryScanResults.csv_count
        };
    }
}
</script>
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**Directory Scanning Endpoint:**

```python
from pathlib import Path
from typing import List, Dict
import os

class DirectoryScanRequest(BaseModel):
    """Request to scan directory for papers."""
    path: str
    recursive: bool = True
    follow_symlinks: bool = False


@app.post(
    "/api/directory/scan",
    tags=["Input"],
    summary="Scan directory for paper files"
)
async def scan_directory(
    request: DirectoryScanRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Scan directory for PDF and CSV files.
    
    Returns file list with metadata and validation results.
    """
    verify_api_key(api_key)
    
    # Security: Validate and sanitize path
    try:
        directory = Path(request.path).expanduser().resolve()
    except Exception as e:
        raise HTTPException(400, f"Invalid path: {str(e)}")
    
    # Security: Prevent path traversal
    # Only allow paths within allowed directories
    allowed_prefixes = [
        Path.home(),  # User's home directory
        Path("/data"),  # Shared data directory
        Path("/mnt"),  # Mounted drives
    ]
    
    if not any(str(directory).startswith(str(prefix)) for prefix in allowed_prefixes):
        raise HTTPException(
            403,
            f"Access denied. Directory must be within: {', '.join(str(p) for p in allowed_prefixes)}"
        )
    
    # Check directory exists
    if not directory.exists():
        raise HTTPException(404, f"Directory not found: {directory}")
    
    # Check is directory
    if not directory.is_dir():
        raise HTTPException(400, f"Path is not a directory: {directory}")
    
    # Check read permissions
    if not os.access(directory, os.R_OK):
        raise HTTPException(403, f"No read permission for directory: {directory}")
    
    # Scan for files
    files = []
    pdf_count = 0
    csv_count = 0
    total_size = 0
    subdirs = set()
    
    try:
        if request.recursive:
            # Recursive scan
            pattern_pdf = "**/*.pdf" if request.follow_symlinks else "**/*.pdf"
            pattern_csv = "**/*.csv" if request.follow_symlinks else "**/*.csv"
            
            for pdf_file in directory.glob(pattern_pdf):
                if pdf_file.is_file():
                    files.append(extract_file_metadata(pdf_file, directory))
                    pdf_count += 1
                    total_size += pdf_file.stat().st_size
                    
                    # Track subdirectory
                    if pdf_file.parent != directory:
                        subdirs.add(pdf_file.parent)
            
            for csv_file in directory.glob(pattern_csv):
                if csv_file.is_file():
                    files.append(extract_file_metadata(csv_file, directory))
                    csv_count += 1
                    total_size += csv_file.stat().st_size
                    
                    if csv_file.parent != directory:
                        subdirs.add(csv_file.parent)
        else:
            # Non-recursive: only top level
            for item in directory.iterdir():
                if item.is_file():
                    if item.suffix.lower() == '.pdf':
                        files.append(extract_file_metadata(item, directory))
                        pdf_count += 1
                        total_size += item.stat().st_size
                    elif item.suffix.lower() == '.csv':
                        files.append(extract_file_metadata(item, directory))
                        csv_count += 1
                        total_size += item.stat().st_size
        
    except PermissionError as e:
        raise HTTPException(403, f"Permission denied scanning directory: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Error scanning directory: {str(e)}")
    
    # Validate found files
    if pdf_count == 0 and csv_count == 0:
        raise HTTPException(
            404,
            f"No PDF or CSV files found in directory: {directory}"
        )
    
    # Sort files by name
    files.sort(key=lambda f: f["filename"])
    
    return {
        "path": str(directory),
        "pdf_count": pdf_count,
        "csv_count": csv_count,
        "total_files": pdf_count + csv_count,
        "total_size_bytes": total_size,
        "subdirectory_count": len(subdirs),
        "recursive": request.recursive,
        "follow_symlinks": request.follow_symlinks,
        "files": files
    }


def extract_file_metadata(file_path: Path, base_dir: Path) -> Dict:
    """Extract metadata from file."""
    stat = file_path.stat()
    
    return {
        "filename": file_path.name,
        "relative_path": str(file_path.relative_to(base_dir)),
        "absolute_path": str(file_path),
        "type": file_path.suffix.lstrip('.').lower(),
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
    }


class JobConfig(BaseModel):
    """Job configuration with directory input support."""
    mode: str = "baseline"
    
    # Input method
    input_method: str = "upload"  # "upload" or "directory"
    data_dir: Optional[str] = None  # For directory method
    scan_recursive: bool = True
    follow_symlinks: bool = False


@app.post("/api/jobs", tags=["Jobs"])
async def create_job(
    config: JobConfig,
    files: Optional[List[UploadFile]] = File(None),
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Create job with file upload or directory input."""
    verify_api_key(api_key)
    
    job_id = str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    if config.input_method == "directory":
        # Directory input method
        if not config.data_dir:
            raise HTTPException(400, "data_dir required for directory input method")
        
        # Validate directory (reuse scan logic)
        scan_result = await scan_directory(
            DirectoryScanRequest(
                path=config.data_dir,
                recursive=config.scan_recursive,
                follow_symlinks=config.follow_symlinks
            ),
            api_key
        )
        
        # Store directory reference (no file copy)
        metadata = {
            "job_id": job_id,
            "created_at": datetime.now().isoformat(),
            "input_method": "directory",
            "data_dir": scan_result["path"],
            "file_count": scan_result["total_files"],
            "pdf_count": scan_result["pdf_count"],
            "csv_count": scan_result["csv_count"],
            "scan_recursive": config.scan_recursive,
            "follow_symlinks": config.follow_symlinks
        }
        
    else:
        # Upload method (existing logic)
        if not files or len(files) == 0:
            raise HTTPException(400, "No files uploaded")
        
        # Save uploaded files
        upload_dir = job_dir / "uploads"
        upload_dir.mkdir(exist_ok=True)
        
        for file in files:
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
        
        metadata = {
            "job_id": job_id,
            "created_at": datetime.now().isoformat(),
            "input_method": "upload",
            "file_count": len(files)
        }
    
    save_job_metadata(job_id, metadata)
    
    return {
        "job_id": job_id,
        "status": "created",
        "input_method": config.input_method,
        "file_count": metadata["file_count"]
    }
```

**Job Runner Integration:**

**File:** `webdashboard/job_runner.py`

The critical change is in `_run_orchestrator_sync()` method where the CLI command is built. The job runner needs to check if the job uses directory input and pass the appropriate `--data-dir` flag:

```python
def _run_orchestrator_sync(self, job_id: str, job_data: dict):
    """
    Run orchestrator synchronously (called in thread pool)
    """
    import subprocess
    import sys
    from pathlib import Path
    
    config = job_data.get("config", {})
    
    # Build CLI command for pipeline orchestrator
    cmd = [sys.executable, "pipeline_orchestrator.py"]
    cmd.append("--batch-mode")
    cmd.extend(["--parent-job-id", job_id])
    
    # ===== KEY CHANGE: Handle directory input vs upload =====
    input_method = job_data.get("input_method", "upload")
    
    if input_method == "directory":
        # Directory input: pass server directory path directly to CLI
        data_dir = job_data.get("data_dir")
        if not data_dir:
            raise ValueError("Directory input method requires data_dir")
        
        cmd.extend(["--data-dir", data_dir])
        self._write_log(job_id, f"Using server directory: {data_dir}")
        
    else:
        # Upload method: point to job's upload directory
        upload_dir = UPLOADS_DIR / job_id
        if not upload_dir.exists() or not list(upload_dir.glob("*.pdf")):
            raise ValueError("No uploaded files found for job")
        
        cmd.extend(["--data-dir", str(upload_dir)])
        self._write_log(job_id, f"Using uploaded files from: {upload_dir}")
    
    # Add other CLI flags (dry_run, force, budget, etc.)
    if config.get("dry_run"):
        cmd.append("--dry-run")
    if config.get("force"):
        cmd.append("--force")
    # ... rest of config flags ...
    
    # Set output directory
    if config.get("output_dir"):
        output_dir = Path(config["output_dir"])
    else:
        output_dir = Path(f"workspace/jobs/{job_id}/outputs/gap_analysis_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd.extend(["--output-dir", str(output_dir)])
    
    # Execute CLI
    self._write_log(job_id, f"Executing: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
        timeout=7200
    )
    
    # Handle result...
```

**Key Points:**
1. Check `job_data.get("input_method")` to determine if directory or upload
2. For directory: pass `job_data["data_dir"]` directly to `--data-dir`
3. For upload: pass job's upload directory to `--data-dir` (existing behavior)
4. No database building needed for directory input - CLI handles it

---

**Job Data Storage:**

When directory input is used, the job metadata must store:

```python
# In /api/jobs/create endpoint
job_data = {
    "id": job_id,
    "input_method": "directory",  # or "upload"
    "data_dir": "/path/to/server/directory",  # for directory input
    "file_count": scan_result["pdf_count"] + scan_result["csv_count"],
    "created_at": datetime.utcnow().isoformat(),
    "status": "draft"
}
```

---

## 🔄 Complete Workflow

### Directory Input Flow (End-to-End)

```
1. User selects "Directory Path" input method
   ↓
2. User types server path: /workspaces/Literature-Review/data/papers/
   ↓
3. User clicks "Scan" button
   ↓
4. Frontend → POST /api/directory/scan
   ↓
5. Backend validates path (security checks)
   ↓
6. Backend scans directory (finds 50 PDFs)
   ↓
7. Frontend displays scan results
   ↓
8. User clicks "Create Job"
   ↓
9. Frontend → POST /api/jobs/create
   {
     "input_method": "directory",
     "data_dir": "/workspaces/Literature-Review/data/papers/"
   }
   ↓
10. Backend creates job metadata (status: "draft")
    ↓
11. User clicks "Configure & Start" (or config modal)
    ↓
12. User selects pillars, analysis mode
    ↓
13. Frontend → POST /api/jobs/{job_id}/configure
    ↓
14. Backend saves configuration
    ↓
15. Frontend → POST /api/jobs/{job_id}/start
    ↓
16. Backend queues job (status: "queued")
    ↓
17. JobRunner picks up job
    ↓
18. JobRunner builds CLI command:
    cmd = ["python", "pipeline_orchestrator.py",
           "--batch-mode",
           "--data-dir", "/workspaces/Literature-Review/data/papers/",
           "--output-dir", "/workspaces/jobs/{job_id}/outputs/",
           ...other flags...]
    ↓
19. JobRunner executes: subprocess.run(cmd)
    ↓
20. CLI processes papers directly from server directory
    ↓
21. Results saved to output directory
    ↓
22. Job status updated to "completed"
    ↓
23. User views results in Dashboard
```

### Key Differences from Upload Method

| Aspect | Upload Method | Directory Method |
|--------|--------------|------------------|
| **Data location** | Browser upload → server temp dir | Already on server |
| **Transfer** | Network transfer required | No transfer (local) |
| **Storage** | Duplicate files created | No duplication |
| **--data-dir value** | `workspace/uploads/{job_id}/` | User-provided path |
| **Database building** | ResearchDatabaseBuilder runs | CLI handles it |
| **File validation** | On upload | On scan |

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Two input method buttons: Upload Files, Directory Path
- [ ] Directory path input field accepts absolute paths
- [ ] Scan button validates directory and finds papers
- [ ] Recursive scan checkbox controls subdirectory scanning
- [ ] Follow symlinks checkbox controls link following
- [ ] Scan results show PDF/CSV counts, total size, subdirs
- [ ] File list modal shows all discovered files
- [ ] Directory path passed to CLI via `--data-dir`
- [ ] Security validation prevents path traversal

### User Experience
- [ ] Method switching clear and intuitive
- [ ] Scan button provides feedback (loading state)
- [ ] Success state shows comprehensive scan results
- [ ] Error state shows helpful troubleshooting tips
- [ ] File list modal readable and sortable
- [ ] Security warning visible but not alarming

### Validation
- [ ] Non-existent directories rejected (404)
- [ ] Files (not directories) rejected (400)
- [ ] Unreadable directories rejected (403)
- [ ] Empty directories rejected (404, no papers found)
- [ ] Path traversal attempts blocked (403)
- [ ] Relative paths rejected (must be absolute)

### CLI Parity
- [ ] Directory input → `--data-dir /path` (100% parity)
- [ ] Recursive scan (default behavior, 100% parity)
- [ ] Symlink handling configurable

### Edge Cases
- [ ] Very large directories (1000+ files) → scan completes
- [ ] Network mounted directories → scan works
- [ ] Mixed PDF/CSV directories → both counted
- [ ] No permissions → clear error message
- [ ] Empty subdirectories → ignored gracefully

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_directory_input.py

def test_scan_directory_success():
    """Test scanning valid directory."""
    # Create test directory with papers
    test_dir = Path("/tmp/test_papers")
    test_dir.mkdir(exist_ok=True)
    (test_dir / "paper1.pdf").touch()
    (test_dir / "data.csv").touch()
    
    response = client.post("/api/directory/scan",
                          json={"path": str(test_dir)},
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["pdf_count"] == 1
    assert data["csv_count"] == 1
    assert data["total_files"] == 2

def test_scan_nonexistent_directory():
    """Test scanning non-existent directory."""
    response = client.post("/api/directory/scan",
                          json={"path": "/nonexistent/path"},
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 404

def test_scan_recursive():
    """Test recursive directory scan."""
    # Create nested structure
    test_dir = Path("/tmp/test_nested")
    (test_dir / "subdir").mkdir(parents=True, exist_ok=True)
    (test_dir / "paper1.pdf").touch()
    (test_dir / "subdir" / "paper2.pdf").touch()
    
    response = client.post("/api/directory/scan",
                          json={"path": str(test_dir), "recursive": True},
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    assert response.json()["pdf_count"] == 2

def test_path_traversal_blocked():
    """Test path traversal attempts rejected."""
    response = client.post("/api/directory/scan",
                          json={"path": "/../../etc/passwd"},
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 403

def test_create_job_with_directory():
    """Test creating job with directory input."""
    test_dir = create_test_directory_with_papers()
    
    response = client.post("/api/jobs",
                          json={
                              "input_method": "directory",
                              "data_dir": str(test_dir)
                          },
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    assert response.json()["input_method"] == "directory"
```

### Integration Tests

```python
def test_e2e_directory_input():
    """End-to-end: scan directory → create job → start → complete."""
    # 1. Create directory with test papers
    test_dir = create_test_directory_with_papers(count=5)
    
    # 2. Scan directory
    scan_result = client.post("/api/directory/scan",
                             json={"path": str(test_dir)}).json()
    assert scan_result["pdf_count"] == 5
    
    # 3. Create job
    job_response = client.post("/api/jobs",
                               json={
                                   "input_method": "directory",
                                   "data_dir": str(test_dir)
                               }).json()
    job_id = job_response["job_id"]
    
    # 4. Start job
    client.post(f"/api/jobs/{job_id}/start")
    
    # 5. Wait for completion
    wait_for_job_completion(job_id)
    
    # 6. Verify results
    metadata = load_job_metadata(job_id)
    assert metadata["input_method"] == "directory"
    assert metadata["data_dir"] == str(test_dir)
```

### Manual Testing Checklist

- [ ] Select Directory Path → directory panel appears
- [ ] Enter valid path → scan button enabled
- [ ] Click Scan → loading state shown
- [ ] Valid directory → success message with counts
- [ ] Click "View File List" → modal shows files
- [ ] Check Recursive → subdirectories included
- [ ] Uncheck Recursive → only top level
- [ ] Invalid path → clear error message
- [ ] Empty directory → "no papers found" error
- [ ] Create job with directory → job created successfully
- [ ] Start job → CLI receives `--data-dir` flag

---

## 📚 Documentation Updates

### User Guide

```markdown
## Directory Input

Instead of uploading files, you can provide a directory path containing your papers. The pipeline will automatically scan the directory for PDFs and CSVs.

### When to Use Directory Input

**Use Upload Files when:**
- Papers are scattered across different locations
- Working with small number of files (<20)
- Papers not yet on server (need to upload from your computer)

**Use Directory Path when:**
- Papers already exist in server directory
- Large number of files (50+)
- Papers on server network share or mounted drive
- Want to avoid re-uploading files already on server

### How to Use

1. Select **Directory Path** input method
2. Enter absolute path to directory on server:
   - Example: `/workspaces/Literature-Review/data/papers/`
   - Example: `/data/research_2024/neuromorphic/`
3. Configure options:
   - **Recursive:** Include subdirectories (recommended)
   - **Follow symlinks:** Include linked directories
4. Click **Scan** to validate directory
5. Review scan results (file counts, total size)
6. Optionally view file list
7. Proceed to configure analysis

### Security

For security, only directories within allowed server locations can be accessed:
- Project workspace (`/workspaces/Literature-Review/`)
- Shared data directory (`/data/`)
- Mounted drives (`/mnt/`)

Path traversal attempts will be rejected.

### Tips

- Use absolute paths (starting with `/` or `C:\`)
- Ensure read permissions for directory
- Large directories may take time to scan
- Empty directories will be rejected

### CLI Equivalent

Directory Path: `--data-dir /path/to/papers`
