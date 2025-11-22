# PARITY-W1-3: Fresh Analysis Trigger

**Priority:** 🔴 **CRITICAL**  
**Effort:** 6-8 hours  
**Wave:** 1 (Critical Gaps)  
**Dependencies:** PARITY-W1-1 (Output Directory Selector)

---

## 📋 Problem Statement

**Current State:**  
Dashboard always creates new UUID-based job directory (`workspace/jobs/{uuid}/`), making it impossible to trigger fresh analysis in a specific directory. Users cannot replicate the CLI workflow of selecting an empty folder to start fresh.

**CLI Capability:**
```bash
# Select empty folder → fresh analysis starts
python pipeline_orchestrator.py --output-dir ./new_review_v2
```

**User Requirement (from context):**
> "When selecting an output folder that did not already contain valid results files, a 'new analysis' would be triggered - so in the case of no new files being available for a test, we should be able to simply choose an empty folder and the pipeline would freshly run and populate that folder with results."

**Current Dashboard Behavior:**
- Always generates new `job_id = uuid.uuid4()`
- Cannot specify "start fresh in this directory"
- Must rely on import workflow (which copies files)

**Gap:** Users cannot initiate fresh analysis in a chosen empty directory.

---

## 🎯 Objective

Enable Dashboard to detect empty/non-existent output directories and automatically trigger fresh (baseline) analysis, matching CLI's behavior when `--output-dir` points to empty folder.

---

## 📐 Design

### Logic Flow

```
User selects output directory (from PARITY-W1-1)
    ↓
Dashboard checks directory state:
    ├─ Directory doesn't exist → CREATE + FRESH ANALYSIS
    ├─ Directory exists but empty → FRESH ANALYSIS
    ├─ Has CSV files but no gap_analysis_report.json → FRESH ANALYSIS
    └─ Has gap_analysis_report.json → OFFER CONTINUATION or OVERWRITE
```

### Detection Algorithm

**File:** `webdashboard/app.py`

```python
from pathlib import Path
from typing import Tuple, Dict

def detect_directory_state(output_dir: Path) -> Dict[str, any]:
    """
    Analyze output directory to determine what analysis mode to use.
    
    Returns:
        {
            "state": "empty" | "has_csv" | "has_results" | "not_exist",
            "recommended_mode": "baseline" | "continuation",
            "file_count": int,
            "has_gap_report": bool,
            "csv_files": List[str],
            "last_modified": str (ISO datetime)
        }
    """
    result = {
        "state": "not_exist",
        "recommended_mode": "baseline",
        "file_count": 0,
        "has_gap_report": False,
        "csv_files": [],
        "last_modified": None
    }
    
    # Case 1: Directory doesn't exist
    if not output_dir.exists():
        result["state"] = "not_exist"
        result["recommended_mode"] = "baseline"
        return result
    
    # Count files
    all_files = list(output_dir.glob("*"))
    result["file_count"] = len(all_files)
    
    # Check for gap analysis report
    gap_report = output_dir / "gap_analysis_report.json"
    result["has_gap_report"] = gap_report.exists()
    
    # Find CSV files
    csv_files = list(output_dir.glob("*.csv"))
    result["csv_files"] = [f.name for f in csv_files]
    
    # Get last modified time
    if all_files:
        latest_file = max(all_files, key=lambda f: f.stat().st_mtime)
        result["last_modified"] = datetime.fromtimestamp(
            latest_file.stat().st_mtime
        ).isoformat()
    
    # Determine state
    if result["file_count"] == 0:
        # Empty directory
        result["state"] = "empty"
        result["recommended_mode"] = "baseline"
        
    elif result["has_gap_report"]:
        # Has previous analysis results
        result["state"] = "has_results"
        result["recommended_mode"] = "continuation"
        
    elif len(result["csv_files"]) > 0:
        # Has CSV files but no analysis results
        result["state"] = "has_csv"
        result["recommended_mode"] = "baseline"
        
    else:
        # Has files but nothing recognizable
        result["state"] = "empty"
        result["recommended_mode"] = "baseline"
    
    return result


@app.post("/api/upload/analyze-directory")
async def analyze_directory_state(
    directory_path: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Analyze directory to recommend baseline vs continuation mode.
    
    Called by frontend when user selects output directory.
    """
    verify_api_key(api_key)
    
    output_dir = Path(directory_path).expanduser().resolve()
    
    # Security check
    if not str(output_dir).startswith(str(BASE_DIR)) and not output_dir.is_absolute():
        raise HTTPException(400, "Invalid directory path")
    
    state = detect_directory_state(output_dir)
    
    return {
        "directory": str(output_dir),
        "state": state,
        "recommendation": {
            "mode": state["recommended_mode"],
            "reason": get_recommendation_reason(state)
        }
    }


def get_recommendation_reason(state: Dict) -> str:
    """Generate human-readable recommendation."""
    if state["state"] == "not_exist":
        return "Directory doesn't exist. Will create and run fresh analysis."
    elif state["state"] == "empty":
        return "Directory is empty. Will run fresh baseline analysis."
    elif state["state"] == "has_csv":
        return f"Found {len(state['csv_files'])} CSV files. Will run fresh analysis on these papers."
    elif state["state"] == "has_results":
        return f"Found existing analysis (last updated: {state['last_modified']}). Can continue or overwrite."
    else:
        return "Will run fresh baseline analysis."
```

---

### UI Integration

**File:** `webdashboard/templates/index.html`

**Auto-Detection Display:**

```html
<!-- Directory State Indicator (shown after directory selection) -->
<div id="directoryStateIndicator" style="display: none;" class="alert mt-3">
    <h6 class="alert-heading">
        <span id="stateIcon"></span>
        Directory Analysis
    </h6>
    <p id="stateDescription"></p>
    
    <div id="recommendationBox" class="mt-3">
        <strong>Recommended Mode:</strong>
        <span id="recommendedMode" class="badge"></span>
        <p id="recommendationReason" class="mb-0 mt-2"></p>
    </div>
    
    <!-- Action Buttons -->
    <div class="btn-group mt-3" role="group">
        <button type="button" class="btn btn-primary" id="acceptRecommendation">
            ✅ Use Recommended Mode
        </button>
        <button type="button" class="btn btn-outline-secondary" id="changeMode">
            🔀 Choose Different Mode
        </button>
    </div>
</div>

<script>
// Analyze directory when path changes
async function analyzeOutputDirectory(directoryPath) {
    if (!directoryPath) return;
    
    try {
        const response = await fetch('/api/upload/analyze-directory', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            },
            body: JSON.stringify({ directory_path: directoryPath })
        });
        
        const data = await response.json();
        displayDirectoryState(data);
        
    } catch (error) {
        console.error('Failed to analyze directory:', error);
    }
}

function displayDirectoryState(data) {
    const indicator = document.getElementById('directoryStateIndicator');
    const stateIcon = document.getElementById('stateIcon');
    const stateDescription = document.getElementById('stateDescription');
    const recommendedMode = document.getElementById('recommendedMode');
    const recommendationReason = document.getElementById('recommendationReason');
    
    // Set state icon and color
    const stateConfig = {
        'not_exist': { icon: '📁', color: 'primary', text: 'New Directory' },
        'empty': { icon: '📂', color: 'info', text: 'Empty Directory' },
        'has_csv': { icon: '📄', color: 'warning', text: 'Contains CSV Files' },
        'has_results': { icon: '✅', color: 'success', text: 'Has Previous Results' }
    };
    
    const config = stateConfig[data.state.state] || stateConfig['empty'];
    
    stateIcon.textContent = config.icon;
    indicator.className = `alert alert-${config.color} mt-3`;
    stateDescription.innerHTML = `
        <strong>${config.text}</strong><br>
        Files: ${data.state.file_count}<br>
        ${data.state.has_gap_report ? '✅ Has analysis report' : '❌ No analysis report'}
    `;
    
    // Set recommendation
    recommendedMode.textContent = data.recommendation.mode.toUpperCase();
    recommendedMode.className = `badge bg-${data.recommendation.mode === 'baseline' ? 'primary' : 'success'}`;
    recommendationReason.textContent = data.recommendation.reason;
    
    // Show indicator
    indicator.style.display = 'block';
    
    // Auto-select recommended mode
    document.querySelector(`input[value="${data.recommendation.mode}"]`).checked = true;
}

// Accept recommendation button
document.getElementById('acceptRecommendation').addEventListener('click', () => {
    // Mode already set by auto-selection, just proceed
    document.getElementById('uploadForm').scrollIntoView({ behavior: 'smooth' });
});

// Change mode button
document.getElementById('changeMode').addEventListener('click', () => {
    // Show mode selector
    document.getElementById('modeSelector').scrollIntoView({ behavior: 'smooth' });
});

// Trigger analysis when custom path entered
document.getElementById('customOutputPath').addEventListener('blur', (e) => {
    analyzeOutputDirectory(e.target.value);
});

// Trigger analysis when existing directory selected
document.getElementById('existingDirDropdown').addEventListener('change', (e) => {
    analyzeOutputDirectory(e.target.value);
});
</script>
```

---

### Backend Job Creation

**Modified Upload Logic:**

```python
@app.post("/api/upload/batch")
async def upload_batch(
    files: List[UploadFile],
    config: UploadConfig,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Upload with automatic fresh analysis detection."""
    verify_api_key(api_key)
    
    # Determine output directory (from PARITY-W1-1)
    output_dir = get_output_directory(config)
    
    # Detect directory state
    dir_state = detect_directory_state(output_dir)
    
    # Override mode based on directory state if not explicitly forced
    if not config.get('force_mode'):
        if dir_state["state"] in ["not_exist", "empty", "has_csv"]:
            # Fresh analysis required
            config["mode"] = "baseline"
            logger.info(f"Auto-detected fresh analysis needed for {output_dir}")
        elif dir_state["state"] == "has_results":
            # Continuation possible
            if config["mode"] != "continuation":
                logger.warning(
                    f"Directory {output_dir} has results but mode is {config['mode']}. "
                    "Consider using continuation mode."
                )
    
    # Create/prepare output directory
    if dir_state["state"] == "not_exist":
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created new output directory: {output_dir}")
    
    # Save uploaded files
    for uploaded_file in files:
        file_path = output_dir / uploaded_file.filename
        with open(file_path, "wb") as f:
            content = await uploaded_file.read()
            f.write(content)
    
    # Generate job_id based on output_dir
    job_id = f"job_{hashlib.md5(str(output_dir).encode()).hexdigest()[:12]}"
    
    job_data = {
        "id": job_id,
        "output_dir": str(output_dir),
        "mode": config["mode"],
        "directory_state": dir_state,
        "fresh_analysis": dir_state["state"] in ["not_exist", "empty", "has_csv"],
        "created_at": datetime.now().isoformat()
    }
    
    save_job_metadata(job_id, job_data)
    
    return {
        "status": "uploaded",
        "job_id": job_id,
        "output_dir": str(output_dir),
        "mode": config["mode"],
        "fresh_analysis": job_data["fresh_analysis"],
        "directory_state": dir_state
    }
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Backend detects directory states: not_exist, empty, has_csv, has_results
- [ ] API endpoint `/api/upload/analyze-directory` returns state + recommendation
- [ ] Frontend displays directory state indicator with icon + description
- [ ] Recommendation auto-selects baseline mode for empty directories
- [ ] Recommendation auto-selects continuation mode for directories with results
- [ ] User can accept recommendation or manually change mode
- [ ] Fresh analysis triggered automatically in empty/new directories
- [ ] Job metadata includes `fresh_analysis: true/false` flag

### User Experience
- [ ] Directory analysis happens automatically on path selection
- [ ] Clear visual indicators (icons, colors) for each state
- [ ] Recommendation reason explained in plain language
- [ ] "Accept Recommendation" button for quick workflow
- [ ] Manual override available (not forced)
- [ ] Works seamlessly with PARITY-W1-1 output directory selector

### CLI Parity
- [ ] Selecting empty folder → fresh baseline (matches CLI)
- [ ] Selecting folder with CSVs → fresh baseline (matches CLI)
- [ ] Selecting folder with results → continuation offered (better than CLI)
- [ ] Creating new directory → fresh baseline (matches CLI)

### Edge Cases
- [ ] Directory exists but permission denied → clear error
- [ ] Symlink to directory → follows link, analyzes target
- [ ] Directory has partial results (interrupted job) → recommend fresh
- [ ] Multiple result files from different runs → use most recent

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_fresh_analysis_trigger.py

def test_detect_directory_not_exist():
    """Test detection of non-existent directory."""
    state = detect_directory_state(Path("/tmp/does_not_exist"))
    assert state["state"] == "not_exist"
    assert state["recommended_mode"] == "baseline"

def test_detect_directory_empty():
    """Test detection of empty directory."""
    empty_dir = Path("/tmp/empty_test")
    empty_dir.mkdir(exist_ok=True)
    
    state = detect_directory_state(empty_dir)
    assert state["state"] == "empty"
    assert state["recommended_mode"] == "baseline"
    assert state["file_count"] == 0

def test_detect_directory_has_csv():
    """Test detection of directory with CSV files."""
    csv_dir = Path("/tmp/csv_test")
    csv_dir.mkdir(exist_ok=True)
    (csv_dir / "test1.csv").touch()
    (csv_dir / "test2.csv").touch()
    
    state = detect_directory_state(csv_dir)
    assert state["state"] == "has_csv"
    assert state["recommended_mode"] == "baseline"
    assert len(state["csv_files"]) == 2

def test_detect_directory_has_results():
    """Test detection of directory with analysis results."""
    results_dir = Path("/tmp/results_test")
    results_dir.mkdir(exist_ok=True)
    (results_dir / "gap_analysis_report.json").touch()
    (results_dir / "test.csv").touch()
    
    state = detect_directory_state(results_dir)
    assert state["state"] == "has_results"
    assert state["recommended_mode"] == "continuation"
    assert state["has_gap_report"] is True

def test_analyze_directory_api():
    """Test directory analysis API endpoint."""
    response = client.post("/api/upload/analyze-directory",
                          json={"directory_path": "/tmp/test_dir"},
                          headers={"X-API-KEY": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert "recommendation" in data

def test_fresh_analysis_auto_trigger():
    """Test that empty directory automatically triggers baseline mode."""
    empty_dir = Path("/tmp/fresh_test")
    empty_dir.mkdir(exist_ok=True)
    
    config = {
        "output_dir_mode": "custom",
        "output_dir_path": str(empty_dir),
        "mode": "continuation"  # User selected continuation
    }
    
    response = client.post("/api/upload/batch",
                          files=test_files,
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    # Should override to baseline (fresh analysis)
    job_data = response.json()
    assert job_data["mode"] == "baseline"
    assert job_data["fresh_analysis"] is True
```

### Integration Tests

```python
def test_e2e_fresh_analysis_workflow():
    """End-to-end: select empty dir → auto baseline → run → verify."""
    # 1. Create empty directory
    test_dir = Path("/tmp/e2e_fresh_test")
    test_dir.mkdir(exist_ok=True)
    
    # 2. Upload files to empty directory
    config = {
        "output_dir_mode": "custom",
        "output_dir_path": str(test_dir)
    }
    upload_response = client.post("/api/upload/batch", 
                                  files=test_files,
                                  json=config)
    job_id = upload_response.json()["id"]
    
    # 3. Verify fresh analysis auto-detected
    assert upload_response.json()["fresh_analysis"] is True
    assert upload_response.json()["mode"] == "baseline"
    
    # 4. Start job
    client.post(f"/api/jobs/{job_id}/start")
    
    # 5. Wait for completion
    wait_for_job_completion(job_id)
    
    # 6. Verify results in specified directory
    assert (test_dir / "gap_analysis_report.json").exists()
```

---

## 📚 Documentation Updates

### User Guide

```markdown
## Fresh Analysis in Custom Directories

The Dashboard automatically detects whether to run fresh analysis or continuation based on the selected output directory.

### Automatic Detection

When you select an output directory, the Dashboard analyzes its state:

| Directory State | Auto Mode | Behavior |
|----------------|-----------|----------|
| Doesn't exist | **Baseline** | Creates directory, runs fresh analysis |
| Empty | **Baseline** | Runs fresh analysis |
| Has CSV files only | **Baseline** | Analyzes those papers |
| Has previous results | **Continuation** | Offers to continue analysis |

### Example: Fresh Analysis in Empty Folder

1. Select **Output Directory** → **Custom Path**
2. Enter path: `/project/new_review`
3. Dashboard detects: "Directory doesn't exist. Will create and run fresh analysis."
4. Mode auto-selected: **Baseline**
5. Click "Start Analysis"
6. Results saved to `/project/new_review/`

This matches CLI behavior:
```bash
python pipeline_orchestrator.py --output-dir /project/new_review
# Fresh analysis starts automatically
```

### Manual Override

You can override the recommendation:
- Click "Choose Different Mode" to manually select
- Enable "Force Re-analysis" to overwrite existing results
```

---

## 🚀 Deployment Checklist

- [ ] Directory state detection logic implemented
- [ ] API endpoint `/api/upload/analyze-directory` deployed
- [ ] Frontend directory state indicator implemented
- [ ] Auto-recommendation logic working
- [ ] Fresh analysis auto-trigger functional
- [ ] Manual override controls working
- [ ] Unit tests passing (8+ tests)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Deployed to staging
- [ ] Manual testing (all 4 directory states)
- [ ] User acceptance testing
- [ ] Deployed to production

---

## 📊 Success Metrics

**After Deployment:**
- Users can trigger fresh analysis in empty directories (100% parity with CLI)
- Auto-detection accuracy: >95% (correct mode recommended)
- User satisfaction: "Just like CLI workflow"

**Monitoring:**
- Track fresh_analysis: true/false ratio in job metadata
- Track manual overrides vs accepted recommendations
- Collect user feedback on auto-detection accuracy

---

**Task Card Version:** 1.0  
**Created:** November 21, 2025  
**Estimated Effort:** 6-8 hours  
**Priority:** 🔴 CRITICAL  
**Dependency:** Requires PARITY-W1-1 (Output Directory Selector)
