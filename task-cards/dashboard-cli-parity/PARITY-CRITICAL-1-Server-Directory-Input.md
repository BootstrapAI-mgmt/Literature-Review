# Task Card: Server Directory Input for Dashboard

**Task ID:** PARITY-CRITICAL-1  
**Title:** Add Server-Side Directory Input (Alternative to File Upload)  
**Priority:** 🔴 CRITICAL  
**Effort:** 8-12 hours  
**Wave:** Critical Fix (Before Wave 2)  
**Dependencies:** None  
**Blocks:** Production Dashboard usage  
**Status:** ⚠️ PARTIALLY STARTED - UI hooks added, backend implementation needed

---

## 📋 Problem Statement

### Current Issue
Dashboard forces users to **upload PDFs through browser**, but the CLI's primary workflow is **pointing to existing directories on the server**. This creates a fundamental mismatch:

**CLI Workflow (90% of production use):**
```bash
# Papers already exist in server directory
ls /project/papers/
# neuromorphic_1.pdf, neuromorphic_2.pdf, ... (50 files)

python pipeline_orchestrator.py \
    --data-dir /project/papers/ \
    --output-dir /project/results/review_v1/
```

**Current Dashboard Workflow (Broken):**
```
1. User: "My papers are at /project/papers/"
2. Dashboard: "You must upload them through your browser"
3. User: *uploads 50 files over network*
4. Dashboard: *copies to workspace/uploads/{job_id}/*
5. Result: Duplicate files, wasted bandwidth, slow
```

### Impact
- **90%** of production workflows unsupported
- Forces inefficient file duplication
- Dashboard unusable for typical production scenarios
- CLI remains only viable option
- **Dashboard-CLI parity: 0%** for data input

### User Quote
> "We wouldn't generally 'upload' anything, we'd simply point the software to the directory containing our papers (which may be a mix of new and previously reviewed papers)"

---

## 🔧 Recent Updates (Nov 22, 2025)

### Missing Buttons Added ✅
Based on screenshot analysis and user feedback, the following critical buttons were added:

1. **"Configure & Start" button** on DRAFT job cards
   - Location: Each job card in Jobs list
   - Function: `configureAndStartJob(jobId, jobName)`
   - Opens configuration modal for existing DRAFT jobs
   - Unblocks users who have uploaded files but can't start them

2. **"New Analysis (No Upload)" button** in main upload section header
   - Location: Top-right of "Upload Research Papers" card
   - Function: `openNewAnalysisModal()`
   - **HOOKS INTO THIS TASK:** Currently shows placeholder alert
   - Will trigger server directory workflow when implemented

3. **Bulk action buttons** for selected jobs
   - "▶️ Start Selected" - `startSelectedJobs()`
   - "🗑️ Delete Selected" - `deleteSelectedJobs()`
   - Enables multi-job management

4. **Per-job action buttons** based on status:
   - DRAFT: "Configure & Start", "Delete"
   - RUNNING: "Cancel"
   - FAILED: "Retry", "Delete"
   - COMPLETED: "Full Results", "Delete"

### Integration Point
The `openNewAnalysisModal()` function is the **entry point** for this task card's implementation:

```javascript
// Current implementation (line ~3470 in index.html)
async function openNewAnalysisModal() {
    // This will trigger PARITY-CRITICAL-1 workflow when implemented
    alert('Server directory input feature coming soon!...');
}
```

**To implement this task:** Replace the alert with the server directory UI workflow described below.

---

## 🎯 Acceptance Criteria

### Must Have
1. ✅ Radio button option: "Upload from computer" vs. "Use server directory"
2. ✅ Text input for server directory path (e.g., `/project/papers/`)
3. ✅ "Browse..." button to explore server filesystem
4. ✅ Directory validation (exists, contains PDFs)
5. ✅ PDF count display after scanning directory
6. ✅ Support recursive directory scanning (like CLI `--data-dir`)
7. ✅ No file copying - reference files in place
8. ✅ Works with all existing features (output dir, config, advanced options)
9. ✅ Security validation (prevent access to system directories)
10. ✅ Error handling for permissions, missing directories

### Should Have
11. ✅ Directory browser UI (expandable tree)
12. ✅ Show preview of found PDF files (name, size, date)
13. ✅ Filter options (exclude subdirectories, file patterns)
14. ✅ Support for mixed workflows (some uploaded, some from server)

### Nice to Have
15. ⚠️ Recently used directories dropdown
16. ⚠️ Bookmark/favorite directories
17. ⚠️ Workspace-relative path shortcuts (e.g., `./data/`)

---

## 🏗️ Solution Design

### UI Changes

#### Upload Section (Modified)
```html
<!-- New: Data Source Selector -->
<div class="card mb-3">
    <div class="card-header">
        <h6>📂 Paper Source</h6>
    </div>
    <div class="card-body">
        <div class="mb-3">
            <label class="form-label">Where are your papers?</label>
            
            <div class="form-check">
                <input class="form-check-input" type="radio" 
                       name="dataSource" id="dataSourceUpload" 
                       value="upload" checked
                       onchange="toggleDataSource()">
                <label class="form-check-label" for="dataSourceUpload">
                    <strong>📤 Upload from My Computer</strong>
                    <small class="text-muted d-block">
                        Select PDFs from your local machine to upload
                    </small>
                </label>
            </div>
            
            <div class="form-check mt-2">
                <input class="form-check-input" type="radio" 
                       name="dataSource" id="dataSourceServer" 
                       value="server"
                       onchange="toggleDataSource()">
                <label class="form-check-label" for="dataSourceServer">
                    <strong>📁 Use Existing Directory on Server</strong>
                    <small class="text-muted d-block">
                        Point to papers already on the server (like CLI --data-dir)
                    </small>
                </label>
            </div>
        </div>
    </div>
</div>

<!-- Upload Section (shown when dataSource=upload) -->
<div id="uploadSection" class="card mb-3">
    <div class="card-body">
        <!-- Existing upload UI (files/folder inputs) -->
    </div>
</div>

<!-- Server Directory Section (shown when dataSource=server) -->
<div id="serverDirectorySection" class="card mb-3" style="display: none;">
    <div class="card-body">
        <div class="mb-3">
            <label for="serverDataDir" class="form-label">Server Directory Path:</label>
            <div class="input-group">
                <input type="text" class="form-control" id="serverDataDir" 
                       placeholder="/workspaces/Literature-Review/data/"
                       onchange="validateServerDirectory()">
                <button class="btn btn-outline-secondary" type="button" 
                        onclick="openDirectoryBrowser()">
                    📁 Browse...
                </button>
                <button class="btn btn-outline-primary" type="button" 
                        onclick="scanServerDirectory()">
                    🔍 Scan
                </button>
            </div>
            <div class="form-text">
                Enter absolute path (e.g., /project/papers/) or relative (e.g., ./data/)
            </div>
        </div>
        
        <!-- Directory Scan Results -->
        <div id="serverDirResults" style="display: none;" class="alert alert-success">
            <h6>✅ Directory Scanned</h6>
            <dl class="row mb-0">
                <dt class="col-sm-3">Path:</dt>
                <dd class="col-sm-9" id="scannedPath">-</dd>
                
                <dt class="col-sm-3">PDF Files Found:</dt>
                <dd class="col-sm-9">
                    <strong id="pdfCount">-</strong> files
                    (<span id="totalSize">-</span>)
                </dd>
                
                <dt class="col-sm-3">Subdirectories:</dt>
                <dd class="col-sm-9" id="subdirCount">-</dd>
            </dl>
            
            <!-- File List Preview -->
            <button class="btn btn-sm btn-outline-primary mt-2" 
                    data-bs-toggle="collapse" data-bs-target="#fileListPreview">
                👁️ View Files (<span id="fileListCount">-</span>)
            </button>
            
            <div id="fileListPreview" class="collapse mt-2">
                <div class="list-group" id="fileList" 
                     style="max-height: 200px; overflow-y: auto;">
                    <!-- Populated dynamically -->
                </div>
            </div>
        </div>
        
        <!-- Scan Options -->
        <div class="mb-3">
            <div class="form-check">
                <input class="form-check-input" type="checkbox" 
                       id="recursiveScan" checked>
                <label class="form-check-label" for="recursiveScan">
                    Recursive (include subdirectories)
                </label>
            </div>
        </div>
    </div>
</div>

<!-- Directory Browser Modal -->
<div class="modal fade" id="directoryBrowserModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">📁 Browse Server Directories</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <!-- Breadcrumb Navigation -->
                <nav aria-label="breadcrumb">
                    <ol class="breadcrumb" id="dirBreadcrumb">
                        <li class="breadcrumb-item"><a href="#" onclick="browseDir('/')">Root</a></li>
                    </ol>
                </nav>
                
                <!-- Directory Tree -->
                <div id="directoryTree" class="border rounded p-3" 
                     style="max-height: 400px; overflow-y: auto;">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    Cancel
                </button>
                <button type="button" class="btn btn-primary" onclick="selectBrowserDirectory()">
                    ✅ Select Directory
                </button>
            </div>
        </div>
    </div>
</div>
```

### JavaScript Implementation

#### Toggle Data Source
```javascript
function toggleDataSource() {
    const source = document.querySelector('input[name="dataSource"]:checked').value;
    
    if (source === 'upload') {
        document.getElementById('uploadSection').style.display = 'block';
        document.getElementById('serverDirectorySection').style.display = 'none';
    } else {
        document.getElementById('uploadSection').style.display = 'none';
        document.getElementById('serverDirectorySection').style.display = 'block';
    }
}
```

#### Scan Server Directory
```javascript
async function scanServerDirectory() {
    const dirPath = document.getElementById('serverDataDir').value.trim();
    
    if (!dirPath) {
        alert('Please enter a directory path');
        return;
    }
    
    const recursive = document.getElementById('recursiveScan').checked;
    const apiKey = document.getElementById('apiKeyInput').value;
    
    try {
        const response = await fetch(`${API_BASE}/api/scan-data-directory`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': apiKey
            },
            body: JSON.stringify({
                directory_path: dirPath,
                recursive: recursive
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to scan directory');
        }
        
        const result = await response.json();
        
        // Update UI with results
        document.getElementById('scannedPath').textContent = result.directory;
        document.getElementById('pdfCount').textContent = result.pdf_count;
        document.getElementById('totalSize').textContent = formatBytes(result.total_size);
        document.getElementById('subdirCount').textContent = result.subdir_count;
        document.getElementById('fileListCount').textContent = result.pdf_count;
        
        // Populate file list
        const fileList = document.getElementById('fileList');
        fileList.innerHTML = result.files.map(file => `
            <div class="list-group-item list-group-item-action">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${file.name}</h6>
                    <small>${formatBytes(file.size)}</small>
                </div>
                <small class="text-muted">${file.relative_path}</small>
            </div>
        `).join('');
        
        document.getElementById('serverDirResults').style.display = 'block';
        
        // Enable job configuration
        currentServerDir = result.directory;
        currentFiles = result.files;
        
    } catch (error) {
        alert('Failed to scan directory: ' + error.message);
        document.getElementById('serverDirResults').style.display = 'none';
    }
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}
```

#### Directory Browser
```javascript
let currentBrowserPath = '/';
let selectedBrowserPath = null;

async function openDirectoryBrowser() {
    const modal = new bootstrap.Modal(document.getElementById('directoryBrowserModal'));
    modal.show();
    
    // Start at workspace root
    const workspaceRoot = '/workspaces/Literature-Review';
    await browseDir(workspaceRoot);
}

async function browseDir(path) {
    currentBrowserPath = path;
    const apiKey = document.getElementById('apiKeyInput').value;
    
    try {
        const response = await fetch(`${API_BASE}/api/browse-directories`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': apiKey
            },
            body: JSON.stringify({ path: path })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to browse directory');
        }
        
        const result = await response.json();
        
        // Update breadcrumb
        updateBreadcrumb(path);
        
        // Render directory tree
        const tree = document.getElementById('directoryTree');
        tree.innerHTML = result.directories.map(dir => `
            <div class="d-flex align-items-center p-2 border-bottom directory-item" 
                 style="cursor: pointer;"
                 onclick="browseDir('${dir.path}')"
                 ondblclick="selectDirectory('${dir.path}')">
                <span class="me-2">📁</span>
                <span class="flex-grow-1">${dir.name}</span>
                <small class="text-muted">${dir.item_count} items</small>
            </div>
        `).join('');
        
        if (result.directories.length === 0) {
            tree.innerHTML = '<p class="text-muted">No subdirectories</p>';
        }
        
    } catch (error) {
        alert('Failed to browse directory: ' + error.message);
    }
}

function updateBreadcrumb(path) {
    const parts = path.split('/').filter(p => p);
    const breadcrumb = document.getElementById('dirBreadcrumb');
    
    let crumbs = '<li class="breadcrumb-item"><a href="#" onclick="browseDir(\'/\')">Root</a></li>';
    let currentPath = '';
    
    for (let part of parts) {
        currentPath += '/' + part;
        crumbs += `<li class="breadcrumb-item"><a href="#" onclick="browseDir('${currentPath}')">${part}</a></li>`;
    }
    
    breadcrumb.innerHTML = crumbs;
}

function selectDirectory(path) {
    selectedBrowserPath = path;
    document.getElementById('serverDataDir').value = path;
    bootstrap.Modal.getInstance(document.getElementById('directoryBrowserModal')).hide();
    scanServerDirectory();
}

function selectBrowserDirectory() {
    if (currentBrowserPath) {
        selectDirectory(currentBrowserPath);
    }
}
```

#### Modified Job Creation
```javascript
// Modify batchUploadForm handler to support server directories
document.getElementById('batchUploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const dataSource = document.querySelector('input[name="dataSource"]:checked').value;
    const apiKey = document.getElementById('apiKeyInput').value;
    
    try {
        if (dataSource === 'upload') {
            // Existing upload logic
            const uploadMode = document.querySelector('input[name="uploadMode"]:checked').value;
            const fileInput = uploadMode === 'files' 
                ? document.getElementById('batchFileInput')
                : document.getElementById('folderInput');
            
            let files = Array.from(fileInput.files);
            
            if (uploadMode === 'folder') {
                files = files.filter(f => f.name.toLowerCase().endsWith('.pdf'));
            }
            
            if (files.length === 0) {
                alert('Please select at least one PDF file');
                return;
            }
            
            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file);
            }
            
            const response = await fetch(`${API_BASE}/api/upload/batch`, {
                method: 'POST',
                headers: { 'X-API-KEY': apiKey },
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }
            
            const result = await response.json();
            
            if (result.status === 'duplicates_found') {
                showDuplicateWarning(result);
            } else {
                currentJobId = result.job_id;
                document.getElementById('configJobId').textContent = result.job_id;
                document.getElementById('configFileCount').textContent = result.file_count;
                
                const modal = new bootstrap.Modal(document.getElementById('configModal'));
                modal.show();
            }
            
        } else { // dataSource === 'server'
            
            if (!currentServerDir || !currentFiles) {
                alert('Please scan a server directory first');
                return;
            }
            
            // Create job from server directory
            const response = await fetch(`${API_BASE}/api/jobs/create-from-directory`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-KEY': apiKey
                },
                body: JSON.stringify({
                    directory_path: currentServerDir,
                    files: currentFiles,
                    recursive: document.getElementById('recursiveScan').checked
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create job from directory');
            }
            
            const result = await response.json();
            
            currentJobId = result.job_id;
            document.getElementById('configJobId').textContent = result.job_id;
            document.getElementById('configFileCount').textContent = result.file_count;
            
            const modal = new bootstrap.Modal(document.getElementById('configModal'));
            modal.show();
        }
        
    } catch (error) {
        alert('Error: ' + error.message);
    }
});
```

---

## 🔧 Backend Implementation

### New Endpoints

#### 1. Scan Data Directory
```python
class ScanDirectoryRequest(BaseModel):
    """Request to scan server directory for PDFs"""
    directory_path: str
    recursive: bool = True

@app.post(
    "/api/scan-data-directory",
    tags=["Papers"],
    summary="Scan server directory for PDF files",
    responses={
        200: {"description": "Directory scanned successfully"},
        400: {"description": "Invalid directory path"},
        401: {"description": "Invalid or missing API key"},
        403: {"description": "Permission denied"},
        404: {"description": "Directory not found"}
    }
)
async def scan_data_directory(
    request: ScanDirectoryRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Scan a server directory for PDF files without uploading.
    
    **Security:**
    - Validates path is within allowed directories
    - Prevents directory traversal attacks
    - Checks file permissions
    
    **Returns:**
    - directory: Resolved absolute path
    - pdf_count: Number of PDF files found
    - total_size: Total size in bytes
    - subdir_count: Number of subdirectories
    - files: List of PDF files with metadata
    """
    verify_api_key(api_key)
    
    # Resolve path
    dir_path = Path(request.directory_path).expanduser().resolve()
    
    # Security: Validate path
    if not dir_path.is_absolute():
        dir_path = (BASE_DIR / dir_path).resolve()
    
    # Security: Check against allowed directories
    allowed_roots = [
        BASE_DIR,
        Path('/workspaces'),
        Path('/project'),
        Path('/data')
    ]
    
    if not any(dir_path.is_relative_to(root) for root in allowed_roots):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: {dir_path} is outside allowed directories"
        )
    
    # Security: Block system directories
    system_dirs = ['/etc', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/boot', '/sys', '/proc', '/root', '/home']
    if any(str(dir_path).startswith(sys_dir) for sys_dir in system_dirs):
        raise HTTPException(
            status_code=403,
            detail="Access denied: Cannot access system directories"
        )
    
    # Validate directory exists
    if not dir_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Directory not found: {dir_path}"
        )
    
    if not dir_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {dir_path}"
        )
    
    # Scan for PDFs
    try:
        if request.recursive:
            pdf_files = list(dir_path.rglob("*.pdf"))
        else:
            pdf_files = list(dir_path.glob("*.pdf"))
        
        # Get file metadata
        files = []
        total_size = 0
        
        for pdf_path in pdf_files:
            try:
                stat = pdf_path.stat()
                files.append({
                    "name": pdf_path.name,
                    "path": str(pdf_path),
                    "relative_path": str(pdf_path.relative_to(dir_path)),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
                total_size += stat.st_size
            except Exception as e:
                logger.warning(f"Failed to stat {pdf_path}: {e}")
                continue
        
        # Count subdirectories
        subdirs = [d for d in dir_path.iterdir() if d.is_dir()]
        
        return {
            "directory": str(dir_path),
            "pdf_count": len(files),
            "total_size": total_size,
            "subdir_count": len(subdirs),
            "files": files,
            "recursive": request.recursive
        }
        
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: Cannot read {dir_path}"
        )
    except Exception as e:
        logger.error(f"Error scanning directory {dir_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan directory: {str(e)}"
        )
```

#### 2. Browse Directories
```python
class BrowseDirectoryRequest(BaseModel):
    """Request to browse server directories"""
    path: str

@app.post(
    "/api/browse-directories",
    tags=["Papers"],
    summary="Browse server filesystem directories",
    responses={
        200: {"description": "Directory listing retrieved"},
        401: {"description": "Invalid or missing API key"},
        403: {"description": "Permission denied"},
        404: {"description": "Directory not found"}
    }
)
async def browse_directories(
    request: BrowseDirectoryRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Browse server directories (for directory picker UI).
    
    Returns list of subdirectories in the specified path.
    """
    verify_api_key(api_key)
    
    dir_path = Path(request.path).resolve()
    
    # Same security checks as scan_data_directory
    allowed_roots = [BASE_DIR, Path('/workspaces'), Path('/project'), Path('/data')]
    if not any(dir_path.is_relative_to(root) for root in allowed_roots):
        raise HTTPException(403, detail="Access denied")
    
    system_dirs = ['/etc', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/boot', '/sys', '/proc', '/root']
    if any(str(dir_path).startswith(sys_dir) for sys_dir in system_dirs):
        raise HTTPException(403, detail="Access denied: System directory")
    
    if not dir_path.exists() or not dir_path.is_dir():
        raise HTTPException(404, detail="Directory not found")
    
    try:
        directories = []
        for item in sorted(dir_path.iterdir()):
            if item.is_dir() and not item.name.startswith('.'):
                try:
                    item_count = len(list(item.iterdir()))
                    directories.append({
                        "name": item.name,
                        "path": str(item),
                        "item_count": item_count
                    })
                except PermissionError:
                    continue
        
        return {
            "current_path": str(dir_path),
            "directories": directories
        }
        
    except PermissionError:
        raise HTTPException(403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(500, detail=str(e))
```

#### 3. Create Job from Directory
```python
class CreateJobFromDirectoryRequest(BaseModel):
    """Request to create job from server directory"""
    directory_path: str
    files: List[Dict[str, Any]]
    recursive: bool = True

@app.post(
    "/api/jobs/create-from-directory",
    tags=["Jobs"],
    summary="Create job from existing server directory",
    responses={
        200: {"description": "Job created successfully"},
        401: {"description": "Invalid or missing API key"},
        400: {"description": "Invalid request"}
    }
)
async def create_job_from_directory(
    request: CreateJobFromDirectoryRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Create a job that references files in an existing server directory.
    
    Instead of uploading/copying files, this creates a job that points
    to files in place (like CLI --data-dir).
    
    **Returns:**
    - job_id: Unique job identifier
    - file_count: Number of PDF files
    - data_dir: Path to source directory
    """
    verify_api_key(api_key)
    
    job_id = str(uuid.uuid4())
    
    # Create job record
    job_data = {
        "id": job_id,
        "status": "configured",  # Skip upload phase
        "data_source": "server_directory",
        "data_dir": request.directory_path,
        "file_count": len(request.files),
        "files": request.files,
        "recursive": request.recursive,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
        "progress": {},
        "config": {
            "pillar_selections": ["ALL"],
            "run_mode": "ONCE"
        }
    }
    
    save_job(job_id, job_data)
    
    # Broadcast update
    await manager.broadcast({
        "type": "job_created",
        "job": job_data
    })
    
    return {
        "job_id": job_id,
        "file_count": len(request.files),
        "data_dir": request.directory_path,
        "status": "configured"
    }
```

#### 4. Modify Start Job Endpoint
```python
# In start_job() function, handle server directory jobs differently

@app.post("/api/jobs/{job_id}/start")
async def start_job(job_id: str, api_key: str = Header(None, alias="X-API-KEY")):
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(404, detail="Job not found")
    
    # ... existing configuration logic ...
    
    # Build CLI command
    cmd = ["python", str(BASE_DIR / "pipeline_orchestrator.py")]
    
    # Handle data source
    if job_data.get("data_source") == "server_directory":
        # Use --data-dir flag (server directory)
        cmd.extend(["--data-dir", job_data["data_dir"]])
    else:
        # Build database from uploaded files (existing behavior)
        data_file = build_research_database(job_id, job_data)
        cmd.extend(["--data-file", str(data_file)])
    
    # ... rest of command building ...
```

---

## 🧪 Testing Plan

### Unit Tests
```python
def test_scan_data_directory_valid():
    """Test scanning valid directory"""
    response = client.post(
        "/api/scan-data-directory",
        json={"directory_path": "/workspaces/Literature-Review/data", "recursive": True},
        headers={"X-API-KEY": "test-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pdf_count"] >= 0
    assert "files" in data

def test_scan_data_directory_security():
    """Test security rejection of system directories"""
    response = client.post(
        "/api/scan-data-directory",
        json={"directory_path": "/etc", "recursive": False},
        headers={"X-API-KEY": "test-key"}
    )
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]

def test_create_job_from_directory():
    """Test job creation from server directory"""
    files = [{"name": "test.pdf", "path": "/data/test.pdf", "size": 1024}]
    response = client.post(
        "/api/jobs/create-from-directory",
        json={
            "directory_path": "/workspaces/Literature-Review/data",
            "files": files,
            "recursive": True
        },
        headers={"X-API-KEY": "test-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["file_count"] == 1
```

### Integration Tests
1. **Server directory workflow:**
   - Select "Use server directory"
   - Enter path `/workspaces/Literature-Review/data/`
   - Click "Scan" → verify PDF count displayed
   - Configure job
   - Start job
   - Verify job uses `--data-dir` flag
   - Verify no files copied to uploads/

2. **Mixed workflow:**
   - Use server directory for 10 PDFs
   - Upload 5 additional PDFs
   - Verify all 15 processed

3. **Security tests:**
   - Try `/etc` → rejected
   - Try `../../etc` → rejected
   - Try `/root` → rejected

### Manual Testing
1. Real production scenario: 50 PDFs in `/project/papers/`
2. Verify no file duplication
3. Verify faster job creation (no upload time)
4. Compare CLI vs Dashboard output (should match)

---

## 📚 Documentation Updates

### User Guide Addition
```markdown
## Using Existing Server Directories

If your PDF files already exist on the server, you can reference them directly
instead of uploading:

1. Select **"Use Existing Directory on Server"**
2. Enter the directory path (e.g., `/project/papers/`)
3. Click **"Scan"** to validate and count PDFs
4. Review the file list
5. Configure and start your analysis

**Benefits:**
- No file uploads required
- No file duplication
- Faster job setup
- Same functionality as CLI `--data-dir`

**Security:** Only directories within allowed paths can be accessed.
```

### API Documentation
- Add new endpoints to OpenAPI docs
- Include security notes
- Provide curl examples

---

## 🚀 Deployment Checklist

### Code Changes
- [ ] Add frontend UI (radio buttons, directory input, browser modal)
- [ ] Add JavaScript functions (scan, browse, toggle)
- [ ] Add backend endpoints (scan, browse, create-from-directory)
- [ ] Modify start_job to handle server directories
- [ ] Add security validation

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Security tests pass
- [ ] Manual testing complete

### Documentation
- [ ] User guide updated
- [ ] API docs updated
- [ ] Task card complete marker added

### Deployment
- [ ] Merge to main branch
- [ ] Deploy to production
- [ ] Verify on production environment
- [ ] User acceptance testing

---

## 🔗 Related Issues

- **DASHBOARD_UX_ISSUES_CRITICAL.md** - Issue #3
- **PARITY-W3-2-Direct-Directory-Input.md** - Original task card
- **DASHBOARD_CLI_PARITY_ASSESSMENT_V2.md** - Parity analysis

---

## ✅ Success Metrics

### Quantitative
- [ ] 100% of production workflows supported
- [ ] 0% file duplication for server directory mode
- [ ] < 5 seconds job creation (vs. minutes for upload)
- [ ] Dashboard-CLI parity for data input: 0% → 100%

### Qualitative
- [ ] Users can use Dashboard for production workflows
- [ ] No confusion about upload vs. directory selection
- [ ] CLI users can transition to Dashboard seamlessly

---

**Status:** 📝 Ready for Implementation  
**Assigned To:** TBD  
**Target Completion:** Week 9, Sprint 2  
**Estimated Hours:** 8-12 hours
