# PARITY-W2-4: Resume Controls

**Priority:** 🟠 **HIGH**  
**Effort:** 8-12 hours  
**Wave:** 2 (High Priority Features)  
**Dependencies:** PARITY-W1-2 (Advanced Options Panel)

---

## 📋 Problem Statement

**Current State:**  
Dashboard jobs that fail or are interrupted must be restarted from the beginning. Users cannot skip completed stages or resume from saved checkpoints, wasting time and money repeating work.

**CLI Capability:**
```bash
# Resume from specific stage
python pipeline_orchestrator.py --resume-from-stage deep_review

# Resume from checkpoint file
python pipeline_orchestrator.py --resume-from-checkpoint pipeline_checkpoint.json
```

**User Problems:**
- Job fails at deep review → must re-run gap analysis and relevance scoring
- Network interruption → loses all progress, starts over
- Want to re-run only visualization → must run entire pipeline
- Cannot utilize saved checkpoint files
- No visibility into which stages are complete

**Gap:** No recovery mechanism in Dashboard for failed or partial jobs.

---

## 🎯 Objective

Add resume capabilities to Dashboard matching CLI's `--resume-from-stage` and `--resume-from-checkpoint` flags, allowing users to skip completed stages and recover from failures efficiently.

---

## 📐 Design

### UI Components

**Location 1:** Advanced Options Panel in `webdashboard/templates/index.html`

**Location 2:** Job Detail Page (Resume button for failed jobs)

**Advanced Options - Resume Controls:**

```html
<!-- Resume Controls (in Advanced Options Panel) -->
<div class="card mb-3 border-info">
    <div class="card-header bg-info bg-opacity-10">
        <h6 class="mb-0">♻️ Resume Controls</h6>
    </div>
    <div class="card-body">
        
        <!-- Resume from Stage -->
        <div class="mb-3">
            <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" 
                       id="enableResumeStage"
                       onchange="toggleResumeStage()">
                <label class="form-check-label" for="enableResumeStage">
                    <strong>Resume from Stage</strong>
                    <span class="badge bg-info">CLI: --resume-from-stage</span>
                </label>
            </div>
            
            <!-- Stage Selector -->
            <select class="form-select" id="resumeStage" disabled>
                <option value="">-- Select Stage to Resume From --</option>
                <option value="gap_analysis">Gap Analysis</option>
                <option value="relevance_scoring">Relevance Scoring</option>
                <option value="deep_review">Deep Review</option>
                <option value="visualization">Visualization</option>
            </select>
            
            <div class="form-text">
                Skip completed stages and start from selected stage.
                Requires previous results in output directory.
            </div>
            
            <!-- Stage Progress Diagram -->
            <div class="mt-3" id="stageProgressDiagram">
                <small class="text-muted">Pipeline Stages:</small>
                <div class="d-flex align-items-center mt-2">
                    <div class="stage-box" id="stage-gap">
                        <small>Gap<br>Analysis</small>
                    </div>
                    <div class="stage-arrow">→</div>
                    <div class="stage-box" id="stage-relevance">
                        <small>Relevance<br>Scoring</small>
                    </div>
                    <div class="stage-arrow">→</div>
                    <div class="stage-box" id="stage-review">
                        <small>Deep<br>Review</small>
                    </div>
                    <div class="stage-arrow">→</div>
                    <div class="stage-box" id="stage-viz">
                        <small>Visualiz-<br>ation</small>
                    </div>
                </div>
            </div>
        </div>
        
        <hr>
        
        <!-- Resume from Checkpoint -->
        <div class="mb-3">
            <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" 
                       id="enableResumeCheckpoint"
                       onchange="toggleResumeCheckpoint()">
                <label class="form-check-label" for="enableResumeCheckpoint">
                    <strong>Resume from Checkpoint</strong>
                    <span class="badge bg-info">CLI: --resume-from-checkpoint</span>
                </label>
            </div>
            
            <!-- Checkpoint File Input -->
            <div id="checkpointInputSection" style="display: none;">
                <div class="input-group mb-2">
                    <input type="text" class="form-control" 
                           id="checkpointFilePath" 
                           placeholder="pipeline_checkpoint.json" readonly>
                    <button class="btn btn-outline-secondary" type="button"
                            onclick="scanForCheckpoints()">
                        🔍 Auto-detect
                    </button>
                    <button class="btn btn-outline-primary" type="button"
                            onclick="document.getElementById('checkpointFileUpload').click()">
                        📤 Upload
                    </button>
                </div>
                <input type="file" id="checkpointFileUpload" 
                       accept=".json" style="display: none;"
                       onchange="handleCheckpointUpload(this)">
                
                <div class="form-text">
                    Continue from saved checkpoint. Auto-detect scans output directory.
                </div>
                
                <!-- Detected Checkpoints -->
                <div id="detectedCheckpoints" style="display: none;" class="mt-2">
                    <small><strong>Detected Checkpoints:</strong></small>
                    <div class="list-group list-group-flush" id="checkpointList">
                        <!-- Populated dynamically -->
                    </div>
                </div>
                
                <!-- Checkpoint Preview -->
                <div id="checkpointPreview" style="display: none;" class="mt-3">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">Checkpoint Details</h6>
                            <dl class="row mb-0 small">
                                <dt class="col-sm-4">Created:</dt>
                                <dd class="col-sm-8" id="checkpointCreated">-</dd>
                                
                                <dt class="col-sm-4">Last Stage:</dt>
                                <dd class="col-sm-8" id="checkpointLastStage">-</dd>
                                
                                <dt class="col-sm-4">Papers Processed:</dt>
                                <dd class="col-sm-8" id="checkpointPapersProcessed">-</dd>
                                
                                <dt class="col-sm-4">Will Resume From:</dt>
                                <dd class="col-sm-8" id="checkpointResumeFrom">-</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Mutual Exclusion Warning -->
        <div id="resumeConflictWarning" style="display: none;" class="alert alert-warning">
            ⚠️ Only one resume method can be used at a time. 
            Using checkpoint will override stage selection.
        </div>
        
    </div>
</div>

<style>
.stage-box {
    border: 2px solid #ccc;
    border-radius: 8px;
    padding: 10px;
    text-align: center;
    min-width: 80px;
    background: white;
    transition: all 0.3s;
}

.stage-box.completed {
    background: #d4edda;
    border-color: #28a745;
}

.stage-box.active {
    background: #fff3cd;
    border-color: #ffc107;
    font-weight: bold;
}

.stage-box.pending {
    background: #f8f9fa;
    border-color: #ccc;
    opacity: 0.6;
}

.stage-arrow {
    margin: 0 10px;
    font-size: 20px;
    color: #6c757d;
}
</style>

<script>
// Toggle resume from stage controls
function toggleResumeStage() {
    const enabled = document.getElementById('enableResumeStage').checked;
    document.getElementById('resumeStage').disabled = !enabled;
    
    if (enabled) {
        document.getElementById('enableResumeCheckpoint').checked = false;
        toggleResumeCheckpoint();
        updateStageHighlight();
    } else {
        resetStageHighlight();
    }
    
    checkResumeConflict();
}

// Toggle resume from checkpoint controls
function toggleResumeCheckpoint() {
    const enabled = document.getElementById('enableResumeCheckpoint').checked;
    document.getElementById('checkpointInputSection').style.display = 
        enabled ? 'block' : 'none';
    
    if (enabled) {
        document.getElementById('enableResumeStage').checked = false;
        toggleResumeStage();
    }
    
    checkResumeConflict();
}

// Check for mutual exclusion
function checkResumeConflict() {
    const stageEnabled = document.getElementById('enableResumeStage').checked;
    const checkpointEnabled = document.getElementById('enableResumeCheckpoint').checked;
    
    document.getElementById('resumeConflictWarning').style.display = 
        (stageEnabled && checkpointEnabled) ? 'block' : 'none';
}

// Update stage diagram highlighting
function updateStageHighlight() {
    const selectedStage = document.getElementById('resumeStage').value;
    const stages = ['gap_analysis', 'relevance_scoring', 'deep_review', 'visualization'];
    
    stages.forEach((stage, index) => {
        const box = document.getElementById(`stage-${stage.split('_')[0]}`);
        const stageIndex = stages.indexOf(stage);
        const selectedIndex = stages.indexOf(selectedStage);
        
        box.classList.remove('completed', 'active', 'pending');
        
        if (stageIndex < selectedIndex) {
            box.classList.add('completed');
        } else if (stageIndex === selectedIndex) {
            box.classList.add('active');
        } else {
            box.classList.add('pending');
        }
    });
}

function resetStageHighlight() {
    ['gap', 'relevance', 'review', 'viz'].forEach(stage => {
        const box = document.getElementById(`stage-${stage}`);
        box.classList.remove('completed', 'active', 'pending');
    });
}

// Listen to stage selection changes
document.getElementById('resumeStage').addEventListener('change', updateStageHighlight);

// Scan for checkpoint files
async function scanForCheckpoints() {
    const outputDir = document.getElementById('customOutputPath')?.value || 
                      document.getElementById('existingDirDropdown')?.value;
    
    if (!outputDir) {
        alert('Please select an output directory first');
        return;
    }
    
    try {
        const response = await fetch(`/api/checkpoints/scan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            },
            body: JSON.stringify({ directory: outputDir })
        });
        
        const data = await response.json();
        
        if (data.checkpoints.length === 0) {
            alert('No checkpoint files found in output directory');
            return;
        }
        
        // Display detected checkpoints
        displayDetectedCheckpoints(data.checkpoints);
        
    } catch (error) {
        console.error('Failed to scan for checkpoints:', error);
        alert('Failed to scan for checkpoints');
    }
}

// Display detected checkpoint files
function displayDetectedCheckpoints(checkpoints) {
    const listContainer = document.getElementById('checkpointList');
    listContainer.innerHTML = '';
    
    checkpoints.forEach(checkpoint => {
        const item = document.createElement('a');
        item.href = '#';
        item.className = 'list-group-item list-group-item-action';
        item.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1">${checkpoint.filename}</h6>
                <small>${new Date(checkpoint.modified).toLocaleString()}</small>
            </div>
            <p class="mb-1 small">
                Last Stage: <strong>${checkpoint.last_stage}</strong> | 
                Papers: ${checkpoint.papers_processed}
            </p>
        `;
        
        item.onclick = (e) => {
            e.preventDefault();
            selectCheckpoint(checkpoint);
        };
        
        listContainer.appendChild(item);
    });
    
    document.getElementById('detectedCheckpoints').style.display = 'block';
}

// Select a checkpoint
function selectCheckpoint(checkpoint) {
    document.getElementById('checkpointFilePath').value = checkpoint.path;
    
    // Show preview
    document.getElementById('checkpointCreated').textContent = 
        new Date(checkpoint.modified).toLocaleString();
    document.getElementById('checkpointLastStage').textContent = checkpoint.last_stage;
    document.getElementById('checkpointPapersProcessed').textContent = checkpoint.papers_processed;
    document.getElementById('checkpointResumeFrom').textContent = checkpoint.resume_stage;
    
    document.getElementById('checkpointPreview').style.display = 'block';
}

// Handle checkpoint file upload
async function handleCheckpointUpload(input) {
    const file = input.files[0];
    if (!file) return;
    
    try {
        const text = await file.text();
        const checkpoint = JSON.parse(text);
        
        // Validate checkpoint structure
        if (!checkpoint.last_completed_stage || !checkpoint.state) {
            alert('Invalid checkpoint file format');
            return;
        }
        
        // Display as selected
        selectCheckpoint({
            path: file.name,
            filename: file.name,
            modified: new Date().toISOString(),
            last_stage: checkpoint.last_completed_stage,
            papers_processed: checkpoint.state?.papers_processed || 'Unknown',
            resume_stage: checkpoint.next_stage || 'Unknown'
        });
        
        // Store file for upload
        window.uploadedCheckpointFile = file;
        
    } catch (error) {
        alert('Failed to parse checkpoint file: ' + error.message);
    }
}

// Get resume configuration for submission
function getResumeConfig() {
    const config = {
        resume_from_stage: null,
        resume_from_checkpoint: null
    };
    
    if (document.getElementById('enableResumeStage').checked) {
        config.resume_from_stage = document.getElementById('resumeStage').value;
    }
    
    if (document.getElementById('enableResumeCheckpoint').checked) {
        config.resume_from_checkpoint = document.getElementById('checkpointFilePath').value;
        config.checkpoint_file = window.uploadedCheckpointFile || null;
    }
    
    return config;
}
</script>
```

**Job Detail Page - Resume Button:**

```html
<!-- Resume Failed Job Button (in job detail page) -->
<div id="jobFailedResume" style="display: none;" class="alert alert-danger">
    <h6>⚠️ Job Failed</h6>
    <p>
        This job failed at stage: <strong id="failedStage">-</strong><br>
        <small>Last checkpoint: <span id="lastCheckpoint">-</span></small>
    </p>
    
    <div class="btn-group">
        <button class="btn btn-warning" onclick="resumeFromLastCheckpoint()">
            ♻️ Resume from Last Checkpoint
        </button>
        <button class="btn btn-outline-warning" onclick="showResumeOptions()">
            ⚙️ Custom Resume Options
        </button>
        <button class="btn btn-outline-secondary" onclick="restartFromBeginning()">
            🔄 Restart from Beginning
        </button>
    </div>
</div>

<script>
// Resume from last checkpoint (one-click)
async function resumeFromLastCheckpoint() {
    const jobId = getCurrentJobId();
    
    try {
        const response = await fetch(`/api/jobs/${jobId}/resume`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            },
            body: JSON.stringify({ auto_resume: true })
        });
        
        const result = await response.json();
        
        if (result.status === 'started') {
            alert('Job resumed from last checkpoint');
            location.reload();
        } else {
            alert('Failed to resume job: ' + result.message);
        }
        
    } catch (error) {
        console.error('Failed to resume job:', error);
        alert('Failed to resume job');
    }
}
</script>
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**Checkpoint Scanning Endpoint:**

```python
from pathlib import Path
from typing import List, Dict
import json

class CheckpointScanRequest(BaseModel):
    """Request to scan directory for checkpoints."""
    directory: str


@app.post(
    "/api/checkpoints/scan",
    tags=["Resume"],
    summary="Scan directory for checkpoint files"
)
async def scan_checkpoints(
    request: CheckpointScanRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Scan output directory for pipeline checkpoint files.
    
    Returns list of found checkpoints with metadata.
    """
    verify_api_key(api_key)
    
    directory = Path(request.directory).expanduser().resolve()
    
    if not directory.exists():
        raise HTTPException(404, f"Directory not found: {directory}")
    
    # Find checkpoint files
    checkpoint_files = list(directory.glob("*checkpoint*.json"))
    checkpoint_files.extend(directory.glob("pipeline_checkpoint.json"))
    
    checkpoints = []
    
    for checkpoint_file in checkpoint_files:
        try:
            with open(checkpoint_file) as f:
                checkpoint_data = json.load(f)
            
            # Extract metadata
            checkpoints.append({
                "path": str(checkpoint_file),
                "filename": checkpoint_file.name,
                "modified": datetime.fromtimestamp(
                    checkpoint_file.stat().st_mtime
                ).isoformat(),
                "last_stage": checkpoint_data.get("last_completed_stage", "Unknown"),
                "resume_stage": checkpoint_data.get("next_stage", "Unknown"),
                "papers_processed": checkpoint_data.get("state", {}).get(
                    "papers_processed", 0
                ),
                "valid": True
            })
            
        except Exception as e:
            logger.warning(f"Failed to parse checkpoint {checkpoint_file}: {e}")
            checkpoints.append({
                "path": str(checkpoint_file),
                "filename": checkpoint_file.name,
                "modified": datetime.fromtimestamp(
                    checkpoint_file.stat().st_mtime
                ).isoformat(),
                "valid": False,
                "error": str(e)
            })
    
    # Sort by modification time (newest first)
    checkpoints.sort(key=lambda c: c["modified"], reverse=True)
    
    return {
        "checkpoints": checkpoints,
        "count": len(checkpoints),
        "directory": str(directory)
    }


def validate_checkpoint_file(checkpoint_path: str) -> Path:
    """
    Validate checkpoint file exists and has valid structure.
    
    Returns validated Path object.
    """
    checkpoint = Path(checkpoint_path)
    
    if not checkpoint.exists():
        raise HTTPException(404, f"Checkpoint file not found: {checkpoint_path}")
    
    try:
        with open(checkpoint) as f:
            data = json.load(f)
        
        # Validate required fields
        required_fields = ["last_completed_stage", "next_stage", "state"]
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            raise HTTPException(
                400,
                f"Invalid checkpoint: missing fields {missing}"
            )
        
        return checkpoint
        
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Invalid checkpoint JSON: {str(e)}")
```

**Modified Job Start with Resume:**

```python
class JobConfig(BaseModel):
    """Job configuration with resume options."""
    mode: str = "baseline"
    # ... other options ...
    
    # Resume options
    resume_from_stage: Optional[str] = None
    resume_from_checkpoint: Optional[str] = None


@app.post("/api/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    config: JobConfig,
    checkpoint_file: Optional[UploadFile] = File(None),
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Start job with optional resume from stage or checkpoint."""
    verify_api_key(api_key)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Build CLI command
    cmd = ["python", "pipeline_orchestrator.py", "--batch-mode"]
    
    # Add resume from stage
    if config.resume_from_stage:
        valid_stages = ["gap_analysis", "relevance_scoring", "deep_review", "visualization"]
        
        if config.resume_from_stage not in valid_stages:
            raise HTTPException(
                400,
                f"Invalid stage: {config.resume_from_stage}. "
                f"Must be one of: {', '.join(valid_stages)}"
            )
        
        cmd.extend(["--resume-from-stage", config.resume_from_stage])
        
        logger.info(f"Job {job_id} resuming from stage: {config.resume_from_stage}")
    
    # Add resume from checkpoint (overrides stage if both specified)
    if config.resume_from_checkpoint or checkpoint_file:
        if checkpoint_file:
            # Save uploaded checkpoint
            checkpoint_path = job_dir / "uploaded_checkpoint.json"
            with open(checkpoint_path, "wb") as f:
                content = await checkpoint_file.read()
                f.write(content)
        else:
            # Use specified checkpoint path
            checkpoint_path = Path(config.resume_from_checkpoint)
        
        # Validate checkpoint
        checkpoint_path = validate_checkpoint_file(str(checkpoint_path))
        
        cmd.extend(["--resume-from-checkpoint", str(checkpoint_path)])
        
        logger.info(f"Job {job_id} resuming from checkpoint: {checkpoint_path}")
    
    # ... rest of command building ...
    
    # Store resume info in metadata
    job_metadata = load_job_metadata(job_id)
    job_metadata["resume_from_stage"] = config.resume_from_stage
    job_metadata["resume_from_checkpoint"] = str(checkpoint_path) if checkpoint_file or config.resume_from_checkpoint else None
    job_metadata["is_resumed_job"] = bool(config.resume_from_stage or config.resume_from_checkpoint)
    save_job_metadata(job_id, job_metadata)
    
    # Execute pipeline
    asyncio.create_task(execute_pipeline_async(job_id, cmd))
    
    return {
        "status": "started",
        "job_id": job_id,
        "resumed": job_metadata["is_resumed_job"],
        "resume_from_stage": config.resume_from_stage,
        "resume_from_checkpoint": bool(checkpoint_file or config.resume_from_checkpoint),
        "command": " ".join(cmd)
    }


@app.post(
    "/api/jobs/{job_id}/resume",
    tags=["Resume"],
    summary="Resume failed job automatically"
)
async def resume_job(
    job_id: str,
    auto_resume: bool = True,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Resume a failed job from its last checkpoint.
    
    Automatically finds and uses the most recent checkpoint.
    """
    verify_api_key(api_key)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Find output directory
    job_metadata = load_job_metadata(job_id)
    output_dir = Path(job_metadata.get("output_dir", job_dir / "outputs" / "gap_analysis_output"))
    
    # Scan for checkpoints
    scan_result = await scan_checkpoints(
        CheckpointScanRequest(directory=str(output_dir)),
        api_key
    )
    
    if scan_result["count"] == 0:
        raise HTTPException(
            404,
            "No checkpoint files found. Cannot auto-resume."
        )
    
    # Use most recent valid checkpoint
    checkpoint = next(
        (c for c in scan_result["checkpoints"] if c.get("valid", False)),
        None
    )
    
    if not checkpoint:
        raise HTTPException(
            400,
            "No valid checkpoint files found. Cannot auto-resume."
        )
    
    # Create new job config with resume from checkpoint
    config = JobConfig(
        mode=job_metadata.get("mode", "baseline"),
        resume_from_checkpoint=checkpoint["path"]
    )
    
    # Start resumed job
    return await start_job(job_id, config, None, api_key)
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Resume from stage checkbox enables/disables stage selector
- [ ] Stage selector dropdown populated with 4 stages
- [ ] Resume from checkpoint checkbox enables/disables checkpoint controls
- [ ] Auto-detect button scans output directory for checkpoints
- [ ] Checkpoint upload accepts .json files
- [ ] Checkpoint preview shows metadata (created, last stage, papers)
- [ ] Resume controls pass correct flags to CLI (`--resume-from-stage`, `--resume-from-checkpoint`)
- [ ] Job detail page shows resume button for failed jobs
- [ ] One-click resume finds and uses latest checkpoint

### User Experience
- [ ] Stage progress diagram highlights completed/active/pending stages
- [ ] Mutual exclusion warning when both resume methods enabled
- [ ] Detected checkpoints listed with metadata (filename, date, stage)
- [ ] Checkpoint preview clear and informative
- [ ] Failed job resume prominent and easy to use
- [ ] Resume options don't overwhelm new users (collapsible/optional)

### Resume Logic
- [ ] Resume from stage requires existing results in output directory
- [ ] Resume from checkpoint validates checkpoint file structure
- [ ] Checkpoint overrides stage selection if both specified
- [ ] Invalid checkpoints rejected with clear errors
- [ ] Auto-resume finds most recent valid checkpoint

### CLI Parity
- [ ] `--resume-from-stage X` → Stage selector (100%)
- [ ] `--resume-from-checkpoint X` → Checkpoint upload/auto-detect (100%)
- [ ] Same validation as CLI (stage names, checkpoint structure)

### Edge Cases
- [ ] No checkpoint files found → clear message
- [ ] Corrupted checkpoint → parse error shown
- [ ] Resume without output directory → validation error
- [ ] Multiple checkpoints → newest selected by default
- [ ] Checkpoint from different job → warning shown

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_resume_controls.py

def test_scan_checkpoints_success():
    """Test scanning directory for checkpoint files."""
    # Create test checkpoint
    output_dir = Path("/tmp/test_checkpoints")
    output_dir.mkdir(exist_ok=True)
    
    checkpoint_data = {
        "last_completed_stage": "gap_analysis",
        "next_stage": "relevance_scoring",
        "state": {"papers_processed": 10}
    }
    
    checkpoint_file = output_dir / "pipeline_checkpoint.json"
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint_data, f)
    
    response = client.post("/api/checkpoints/scan",
                          json={"directory": str(output_dir)},
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["checkpoints"][0]["last_stage"] == "gap_analysis"

def test_resume_from_stage():
    """Test starting job with resume from stage."""
    config = {
        "resume_from_stage": "deep_review"
    }
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["resumed"] is True
    assert "--resume-from-stage deep_review" in data["command"]

def test_resume_from_checkpoint():
    """Test starting job with checkpoint file."""
    checkpoint_data = {
        "last_completed_stage": "relevance_scoring",
        "next_stage": "deep_review",
        "state": {"papers_processed": 10}
    }
    
    checkpoint_file = BytesIO(json.dumps(checkpoint_data).encode())
    
    response = client.post(
        f"/api/jobs/{job_id}/start",
        files={"checkpoint_file": ("checkpoint.json", checkpoint_file, "application/json")},
        headers={"X-API-KEY": "test-key"}
    )
    
    assert response.status_code == 200
    assert response.json()["resume_from_checkpoint"] is True

def test_invalid_stage_rejected():
    """Test that invalid stage name is rejected."""
    config = {
        "resume_from_stage": "invalid_stage"
    }
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 400
    assert "Invalid stage" in response.json()["detail"]

def test_auto_resume_job():
    """Test automatic resume from latest checkpoint."""
    # Create job with checkpoint
    job_id = create_test_job_with_checkpoint()
    
    response = client.post(f"/api/jobs/{job_id}/resume",
                          json={"auto_resume": True},
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    assert response.json()["resumed"] is True
```

### Integration Tests

```python
def test_e2e_resume_workflow():
    """End-to-end: job fails → scan checkpoint → resume → complete."""
    # 1. Start initial job
    job_id = upload_test_files()
    client.post(f"/api/jobs/{job_id}/start")
    
    # 2. Simulate failure at deep review (create checkpoint)
    create_simulated_checkpoint(job_id, "relevance_scoring")
    
    # 3. Scan for checkpoints
    output_dir = get_job_output_dir(job_id)
    scan_result = client.post("/api/checkpoints/scan",
                             json={"directory": str(output_dir)}).json()
    assert scan_result["count"] >= 1
    
    # 4. Resume from checkpoint
    resume_response = client.post(f"/api/jobs/{job_id}/resume",
                                  json={"auto_resume": True})
    assert resume_response.json()["status"] == "started"
    
    # 5. Wait for completion
    wait_for_job_completion(job_id)
    
    # 6. Verify skipped stages (gap analysis, relevance)
    job_metadata = load_job_metadata(job_id)
    assert job_metadata["is_resumed_job"] is True
```

### Manual Testing Checklist

- [ ] Enable resume from stage → stage selector enabled
- [ ] Select stage → diagram highlights correctly
- [ ] Disable resume → selector disabled, diagram reset
- [ ] Enable resume from checkpoint → controls appear
- [ ] Click auto-detect → checkpoints listed (if exist)
- [ ] Select checkpoint → preview shown
- [ ] Upload checkpoint → preview shown
- [ ] Start with resume → job runs from selected stage
- [ ] Failed job → resume button appears
- [ ] Click resume → job restarts from checkpoint

---

## 📚 Documentation Updates

### User Guide

```markdown
## Resuming Failed or Partial Jobs

The Dashboard allows you to resume jobs from specific stages or checkpoints, matching CLI's `--resume-from-stage` and `--resume-from-checkpoint` capabilities.

### Resume from Stage

Skip completed stages and start from a specific point:

1. Expand **Advanced Options**
2. Check **Resume from Stage**
3. Select stage to resume from:
   - Gap Analysis (start)
   - Relevance Scoring
   - Deep Review
   - Visualization
4. Ensure output directory contains previous results
5. Start analysis

**Use when:** You want to re-run only later stages (e.g., update visualization without re-analyzing papers)

### Resume from Checkpoint

Continue from saved checkpoint file:

1. Expand **Advanced Options**
2. Check **Resume from Checkpoint**
3. Choose checkpoint:
   - **Auto-detect:** Scans output directory for checkpoints
   - **Upload:** Provide checkpoint file manually
4. Review checkpoint details (last stage, papers processed)
5. Start analysis

**Use when:** Job failed or was interrupted, and you want to continue exactly where it left off

### Resume Failed Jobs (One-Click)

If a job fails, the job detail page shows a resume button:

1. Navigate to failed job
2. Click **Resume from Last Checkpoint**
3. Job automatically continues from last saved state

No configuration needed - Dashboard finds and uses the most recent checkpoint.

### Stage Progress

The stage diagram shows:
- **Green boxes:** Completed stages (will be skipped)
- **Yellow box:** Current resume point (starts here)
- **Gray boxes:** Pending stages (will execute)

### Tips

- Checkpoints auto-save during pipeline execution
- Resume from stage requires output directory with existing results
- Resume from checkpoint more precise (exact state recovery)
- Both methods save time and money by not repeating work
```

---

## 🚀 Deployment Checklist

- [ ] Resume controls UI implemented in Advanced Options
- [ ] Stage progress diagram styled correctly
- [ ] Checkpoint scanning endpoint deployed (`/api/checkpoints/scan`)
- [ ] Job start modified to handle resume flags
- [ ] Auto-resume endpoint deployed (`/api/jobs/{id}/resume`)
- [ ] Job detail page resume button implemented
- [ ] Checkpoint validation working
- [ ] Unit tests passing (8+ tests, 90% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Deployed to staging
- [ ] Manual testing completed (all scenarios)
- [ ] User acceptance testing passed
- [ ] Deployed to production

---

## 📊 Success Metrics

**After Deployment:**
- Resume controls functional (100%)
- Dashboard parity increases by 2% (resume capabilities)
- Failed jobs recoverable (reduce wasted re-runs)
- User time saved (skip completed stages)

**Monitoring:**
- Track % of jobs using resume features
- Track success rate of resumed jobs
- Track time/cost saved by resuming vs restarting
- Collect user feedback on resume UX

---

**Task Card Version:** 1.0  
**Created:** November 22, 2025  
**Estimated Effort:** 8-12 hours  
**Priority:** 🟠 HIGH  
**Dependency:** Requires PARITY-W1-2 (Advanced Options Panel)
