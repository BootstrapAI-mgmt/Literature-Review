# PARITY-W1-2: Advanced Options Panel

**Priority:** 🔴 **CRITICAL**  
**Effort:** 10-14 hours  
**Wave:** 1 (Critical Gaps)  
**Dependencies:** None

---

## 📋 Problem Statement

**Current State:**  
Dashboard exposes only **2 modes** (baseline/continuation) while CLI has **20+ configuration flags**. Power users cannot access advanced features like dry-run, force re-analysis, custom budgets, or experimental settings.

**CLI Capabilities:**
```bash
python pipeline_orchestrator.py \
  --dry-run \
  --force \
  --budget 10.00 \
  --relevance-threshold 0.75 \
  --clear-cache \
  --resume-from-stage deep_review \
  --experimental \
  --config custom_config.json
```

**Dashboard Limitations:**
- Only baseline vs continuation mode selector
- No access to advanced flags
- Cannot customize budgets or thresholds
- No experimental features toggle

**Gap:** **35% parity** in configuration features (7/20 CLI flags exposed)

---

## 🎯 Objective

Create collapsible "Advanced Options" panel in Dashboard UI to expose commonly-used CLI configuration flags, increasing parity from 35% → 85%+.

---

## 📐 Design

### UI Components

**Location:** Below mode selector in `webdashboard/templates/index.html`

**New UI Panel:**

```html
<!-- Advanced Options Panel -->
<div class="card mb-3">
    <div class="card-header" style="cursor: pointer;" 
         data-bs-toggle="collapse" data-bs-target="#advancedOptions">
        <h6 class="mb-0">
            ⚙️ Advanced Options
            <span class="badge bg-secondary float-end">Optional</span>
            <i class="bi bi-chevron-down float-end me-2"></i>
        </h6>
    </div>
    <div id="advancedOptions" class="collapse">
        <div class="card-body">
            
            <!-- Dry Run Mode -->
            <div class="mb-3">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" 
                           id="dryRunMode">
                    <label class="form-check-label" for="dryRunMode">
                        <strong>Dry Run</strong>
                        <span class="badge bg-info">CLI: --dry-run</span>
                    </label>
                    <div class="form-text">
                        Validate configuration without making API calls or spending credits.
                        Shows what would run.
                    </div>
                </div>
            </div>
            
            <!-- Force Re-analysis -->
            <div class="mb-3">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" 
                           id="forceReanalysis">
                    <label class="form-check-label" for="forceReanalysis">
                        <strong>Force Re-analysis</strong>
                        <span class="badge bg-warning text-dark">CLI: --force</span>
                    </label>
                    <div class="form-text">
                        Re-run analysis even if recent results exist. Ignores cache.
                    </div>
                </div>
            </div>
            
            <!-- Clear Cache -->
            <div class="mb-3">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" 
                           id="clearCache">
                    <label class="form-check-label" for="clearCache">
                        <strong>Clear Cache</strong>
                        <span class="badge bg-danger">CLI: --clear-cache</span>
                    </label>
                    <div class="form-text">
                        Delete all cached API responses before starting. 
                        Use when switching models or updating prompts.
                    </div>
                </div>
            </div>
            
            <hr class="my-4">
            
            <!-- Budget Control -->
            <div class="mb-3">
                <label for="budgetLimit" class="form-label">
                    <strong>Budget Limit (USD)</strong>
                    <span class="badge bg-primary">CLI: --budget</span>
                </label>
                <div class="input-group">
                    <span class="input-group-text">$</span>
                    <input type="number" class="form-control" 
                           id="budgetLimit" 
                           placeholder="5.00" 
                           step="0.01" 
                           min="0">
                    <button class="btn btn-outline-secondary" type="button"
                            onclick="document.getElementById('budgetLimit').value = ''">
                        Clear
                    </button>
                </div>
                <div class="form-text">
                    Maximum spending for this job. Pipeline stops when reached.
                    Leave empty for unlimited.
                </div>
            </div>
            
            <!-- Relevance Threshold -->
            <div class="mb-3">
                <label for="relevanceThreshold" class="form-label">
                    <strong>Relevance Threshold</strong>
                    <span class="badge bg-success">CLI: --relevance-threshold</span>
                </label>
                <div class="row align-items-center">
                    <div class="col-8">
                        <input type="range" class="form-range" 
                               id="relevanceThreshold" 
                               min="0.5" max="1.0" step="0.05" 
                               value="0.7"
                               oninput="updateThresholdDisplay(this.value)">
                    </div>
                    <div class="col-4">
                        <input type="number" class="form-control form-control-sm" 
                               id="relevanceThresholdValue" 
                               value="0.7" 
                               min="0.5" max="1.0" step="0.05"
                               oninput="document.getElementById('relevanceThreshold').value = this.value">
                    </div>
                </div>
                <div class="form-text">
                    Minimum semantic similarity for papers to be considered relevant.
                    Higher = stricter filtering (0.5-1.0).
                </div>
            </div>
            
            <hr class="my-4">
            
            <!-- Resume Controls -->
            <div class="mb-3">
                <div class="form-check mb-2">
                    <input class="form-check-input" type="checkbox" 
                           id="enableResume">
                    <label class="form-check-label" for="enableResume">
                        <strong>Resume from Stage</strong>
                        <span class="badge bg-info">CLI: --resume-from-stage</span>
                    </label>
                </div>
                
                <select class="form-select" id="resumeStage" disabled>
                    <option value="">-- Select Stage --</option>
                    <option value="gap_analysis">Gap Analysis</option>
                    <option value="relevance_scoring">Relevance Scoring</option>
                    <option value="deep_review">Deep Review</option>
                    <option value="visualization">Visualization</option>
                </select>
                <div class="form-text">
                    Skip completed stages and resume from specific checkpoint.
                </div>
            </div>
            
            <!-- Checkpoint Resume -->
            <div class="mb-3">
                <div class="form-check mb-2">
                    <input class="form-check-input" type="checkbox" 
                           id="enableCheckpointResume">
                    <label class="form-check-label" for="enableCheckpointResume">
                        <strong>Resume from Checkpoint</strong>
                        <span class="badge bg-info">CLI: --resume-from-checkpoint</span>
                    </label>
                </div>
                
                <input type="text" class="form-control" 
                       id="checkpointFile" 
                       placeholder="pipeline_checkpoint.json" 
                       disabled>
                <div class="form-text">
                    Continue from saved checkpoint file. Auto-detected if exists.
                </div>
            </div>
            
            <hr class="my-4">
            
            <!-- Experimental Features -->
            <div class="mb-3">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" 
                           id="experimentalFeatures">
                    <label class="form-check-label" for="experimentalFeatures">
                        <strong>Enable Experimental Features</strong>
                        <span class="badge bg-warning text-dark">CLI: --experimental</span>
                    </label>
                    <div class="form-text">
                        ⚠️ Use cutting-edge features (may be unstable). 
                        Includes: advanced caching, parallel scoring, new prompts.
                    </div>
                </div>
            </div>
            
            <!-- Config File Upload -->
            <div class="mb-3">
                <label for="configFileUpload" class="form-label">
                    <strong>Custom Configuration File</strong>
                    <span class="badge bg-secondary">CLI: --config</span>
                </label>
                <input class="form-control" type="file" 
                       id="configFileUpload" 
                       accept=".json">
                <div class="form-text">
                    Upload custom pipeline_config.json to override defaults.
                </div>
            </div>
            
            <!-- Reset to Defaults -->
            <div class="text-end">
                <button type="button" class="btn btn-sm btn-outline-secondary" 
                        onclick="resetAdvancedOptions()">
                    🔄 Reset to Defaults
                </button>
            </div>
            
        </div>
    </div>
</div>

<script>
// Update threshold display
function updateThresholdDisplay(value) {
    document.getElementById('relevanceThresholdValue').value = value;
}

// Enable/disable resume controls
document.getElementById('enableResume').addEventListener('change', (e) => {
    document.getElementById('resumeStage').disabled = !e.target.checked;
});

document.getElementById('enableCheckpointResume').addEventListener('change', (e) => {
    document.getElementById('checkpointFile').disabled = !e.target.checked;
});

// Reset all advanced options
function resetAdvancedOptions() {
    document.getElementById('dryRunMode').checked = false;
    document.getElementById('forceReanalysis').checked = false;
    document.getElementById('clearCache').checked = false;
    document.getElementById('budgetLimit').value = '';
    document.getElementById('relevanceThreshold').value = 0.7;
    document.getElementById('relevanceThresholdValue').value = 0.7;
    document.getElementById('enableResume').checked = false;
    document.getElementById('resumeStage').disabled = true;
    document.getElementById('resumeStage').value = '';
    document.getElementById('enableCheckpointResume').checked = false;
    document.getElementById('checkpointFile').disabled = true;
    document.getElementById('checkpointFile').value = '';
    document.getElementById('experimentalFeatures').checked = false;
    document.getElementById('configFileUpload').value = '';
}

// Collect advanced options for API request
function getAdvancedOptions() {
    return {
        dry_run: document.getElementById('dryRunMode').checked,
        force: document.getElementById('forceReanalysis').checked,
        clear_cache: document.getElementById('clearCache').checked,
        budget: document.getElementById('budgetLimit').value 
                 ? parseFloat(document.getElementById('budgetLimit').value) 
                 : null,
        relevance_threshold: parseFloat(document.getElementById('relevanceThresholdValue').value),
        resume_from_stage: document.getElementById('enableResume').checked 
                          ? document.getElementById('resumeStage').value 
                          : null,
        resume_from_checkpoint: document.getElementById('enableCheckpointResume').checked 
                               ? document.getElementById('checkpointFile').value 
                               : null,
        experimental: document.getElementById('experimentalFeatures').checked,
        custom_config: document.getElementById('configFileUpload').files[0] || null
    };
}
</script>
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**Modified Job Configuration:**

```python
class JobConfig(BaseModel):
    """Extended job configuration with advanced options."""
    mode: str = "baseline"
    base_job_id: Optional[str] = None
    
    # Advanced options (new)
    dry_run: bool = False
    force: bool = False
    clear_cache: bool = False
    budget: Optional[float] = None
    relevance_threshold: float = 0.7
    resume_from_stage: Optional[str] = None
    resume_from_checkpoint: Optional[str] = None
    experimental: bool = False
    
@app.post("/api/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    config: JobConfig,
    config_file: Optional[UploadFile] = File(None),
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Start job with advanced configuration options."""
    verify_api_key(api_key)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Build CLI command with advanced flags
    cmd = ["python", "pipeline_orchestrator.py", "--batch-mode"]
    
    # Add advanced flags
    if config.dry_run:
        cmd.append("--dry-run")
    
    if config.force:
        cmd.append("--force")
    
    if config.clear_cache:
        cmd.append("--clear-cache")
    
    if config.budget:
        cmd.extend(["--budget", str(config.budget)])
    
    if config.relevance_threshold != 0.7:  # Non-default
        cmd.extend(["--relevance-threshold", str(config.relevance_threshold)])
    
    if config.resume_from_stage:
        cmd.extend(["--resume-from-stage", config.resume_from_stage])
    
    if config.resume_from_checkpoint:
        cmd.extend(["--resume-from-checkpoint", config.resume_from_checkpoint])
    
    if config.experimental:
        cmd.append("--experimental")
    
    # Handle custom config file
    if config_file:
        custom_config_path = job_dir / "custom_config.json"
        with open(custom_config_path, "wb") as f:
            f.write(await config_file.read())
        cmd.extend(["--config", str(custom_config_path)])
    
    # Add mode-specific flags
    if config.mode == "continuation":
        cmd.append("--incremental")
        if config.base_job_id:
            base_output_dir = JOBS_DIR / config.base_job_id / "outputs" / "gap_analysis_output"
            cmd.extend(["--base-results", str(base_output_dir)])
    
    # Execute pipeline in background
    job_metadata = load_job_metadata(job_id)
    job_metadata["config"] = config.dict()
    job_metadata["command"] = " ".join(cmd)
    job_metadata["status"] = "running"
    job_metadata["started_at"] = datetime.now().isoformat()
    save_job_metadata(job_id, job_metadata)
    
    # Start async execution
    asyncio.create_task(execute_pipeline_async(job_id, cmd))
    
    return {
        "status": "started",
        "job_id": job_id,
        "command": " ".join(cmd),
        "dry_run": config.dry_run
    }
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Collapsible "Advanced Options" panel renders correctly
- [ ] All 10 advanced controls functional (checkboxes, inputs, sliders, file upload)
- [ ] Controls enable/disable based on dependencies (e.g., resume controls)
- [ ] Values passed to backend API correctly
- [ ] Backend builds CLI command with appropriate flags
- [ ] "Reset to Defaults" button clears all settings
- [ ] Custom config file uploaded and used by pipeline
- [ ] Dry run mode shows preview without executing

### User Experience
- [ ] Panel collapsed by default (not overwhelming)
- [ ] Each option has clear label + help text
- [ ] CLI flag badges show equivalent command
- [ ] Slider + number input synced for threshold
- [ ] File upload shows selected filename
- [ ] Validation feedback (e.g., budget must be positive)
- [ ] Tooltips on hover for complex options

### CLI Parity
- [ ] `--dry-run` → Dry Run checkbox
- [ ] `--force` → Force Re-analysis checkbox
- [ ] `--clear-cache` → Clear Cache checkbox
- [ ] `--budget X` → Budget Limit input
- [ ] `--relevance-threshold X` → Relevance Threshold slider
- [ ] `--resume-from-stage X` → Resume Stage dropdown
- [ ] `--resume-from-checkpoint X` → Checkpoint file input
- [ ] `--experimental` → Experimental Features checkbox
- [ ] `--config X` → Config file upload

### Edge Cases
- [ ] Empty budget → no --budget flag passed
- [ ] Default threshold (0.7) → no flag passed (optimization)
- [ ] Resume enabled but no stage selected → validation error
- [ ] Invalid config JSON → clear error message
- [ ] Conflicting options (e.g., dry-run + force) → warning shown

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_advanced_options.py

def test_advanced_options_all_flags():
    """Test job start with all advanced options enabled."""
    config = {
        "mode": "baseline",
        "dry_run": True,
        "force": True,
        "clear_cache": True,
        "budget": 10.50,
        "relevance_threshold": 0.85,
        "experimental": True
    }
    response = client.post(f"/api/jobs/{job_id}/start", 
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    assert response.status_code == 200
    
    # Verify command built correctly
    command = response.json()["command"]
    assert "--dry-run" in command
    assert "--force" in command
    assert "--clear-cache" in command
    assert "--budget 10.5" in command
    assert "--relevance-threshold 0.85" in command
    assert "--experimental" in command

def test_advanced_options_resume_from_stage():
    """Test resume from specific stage."""
    config = {
        "resume_from_stage": "deep_review"
    }
    response = client.post(f"/api/jobs/{job_id}/start", 
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    assert "--resume-from-stage deep_review" in response.json()["command"]

def test_custom_config_upload():
    """Test custom configuration file upload."""
    custom_config = {"test": "config"}
    config_file = BytesIO(json.dumps(custom_config).encode())
    
    response = client.post(
        f"/api/jobs/{job_id}/start",
        files={"config_file": ("config.json", config_file, "application/json")},
        headers={"X-API-KEY": "test-key"}
    )
    assert response.status_code == 200
    assert "--config" in response.json()["command"]
    
    # Verify file saved
    saved_config = Path(f"workspace/jobs/{job_id}/custom_config.json")
    assert saved_config.exists()
    assert json.loads(saved_config.read_text()) == custom_config

def test_dry_run_no_execution():
    """Test dry run doesn't execute pipeline."""
    config = {"dry_run": True}
    response = client.post(f"/api/jobs/{job_id}/start", 
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    # Should return command but not execute
    assert response.json()["dry_run"] is True
    assert response.json()["status"] == "validated"  # Not "running"
```

### Integration Tests

```python
def test_e2e_advanced_options():
    """End-to-end: upload → configure advanced options → run → verify."""
    # 1. Upload files
    job_id = upload_test_files()
    
    # 2. Start with advanced options
    config = {
        "force": True,
        "budget": 5.00,
        "relevance_threshold": 0.8
    }
    client.post(f"/api/jobs/{job_id}/start", json=config)
    
    # 3. Wait for completion
    wait_for_job_completion(job_id)
    
    # 4. Verify advanced options were applied
    job_metadata = get_job_metadata(job_id)
    assert job_metadata["config"]["force"] is True
    assert job_metadata["config"]["budget"] == 5.00
    
    # 5. Check cost didn't exceed budget
    cost_report = load_cost_report(job_id)
    assert cost_report["total_cost"] <= 5.00
```

---

## 📚 Documentation Updates

### User Guide

```markdown
## Advanced Configuration Options

The Dashboard exposes advanced CLI flags through the **Advanced Options** panel. Click to expand and customize pipeline behavior.

### Options Reference

| Option | CLI Equivalent | Description |
|--------|----------------|-------------|
| Dry Run | `--dry-run` | Preview what will run without API calls |
| Force Re-analysis | `--force` | Ignore cache, re-run everything |
| Clear Cache | `--clear-cache` | Delete cached responses before starting |
| Budget Limit | `--budget X` | Stop when spending reaches $X |
| Relevance Threshold | `--relevance-threshold X` | Minimum similarity score (0.5-1.0) |
| Resume from Stage | `--resume-from-stage X` | Skip completed stages |
| Resume from Checkpoint | `--resume-from-checkpoint X` | Continue from saved checkpoint |
| Experimental Features | `--experimental` | Enable cutting-edge (unstable) features |
| Custom Config | `--config X` | Upload custom pipeline_config.json |

### Example Workflows

**Cost-Conscious Analysis:**
```
Budget Limit: $3.00
Relevance Threshold: 0.8 (stricter filtering)
→ Reduces API calls by filtering more papers upfront
```

**Quick Validation:**
```
Dry Run: Enabled
→ Shows what would run, no API calls, $0 cost
```

**Resume After Failure:**
```
Resume from Stage: Deep Review
→ Skips gap analysis + relevance scoring (already done)
```
```

---

## 🚀 Deployment Checklist

- [ ] Frontend panel implemented with all controls
- [ ] JavaScript validation and state management working
- [ ] Backend `JobConfig` model extended with advanced options
- [ ] Command builder generates correct CLI flags
- [ ] Custom config file upload functional
- [ ] Unit tests passing (15+ tests)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Deployed to staging
- [ ] Manual testing completed
- [ ] User acceptance testing passed
- [ ] Deployed to production

---

## 📊 Success Metrics

**After Deployment:**
- Configuration parity: 35% → 85%+ (17/20 CLI flags exposed)
- Dashboard parity: 68% → 80%+ (combined with other Wave 1 tasks)
- Power user adoption: Track % of jobs using advanced options

**User Feedback:**
- "Can now do everything in Dashboard I could in CLI"
- Reduced requests for CLI-only features

---

**Task Card Version:** 1.0  
**Created:** November 21, 2025  
**Estimated Effort:** 10-14 hours  
**Priority:** 🔴 CRITICAL
