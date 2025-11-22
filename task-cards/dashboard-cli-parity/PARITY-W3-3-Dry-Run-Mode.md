# PARITY-W3-3: Dry-Run Mode

**Priority:** 🟡 **MEDIUM**  
**Effort:** 6-8 hours  
**Wave:** 3 (Enhancement Features)  
**Dependencies:** PARITY-W1-2 (Advanced Options Panel)

---

## 📋 Problem Statement

**Current State:**  
Dashboard immediately executes analysis when user starts job. Users cannot preview what will happen, estimate costs, or validate configuration before committing to full execution.

**CLI Capability:**
```bash
# Dry-run mode: show plan without executing
python pipeline_orchestrator.py --dry-run

# Output:
# [DRY RUN] Would process 50 papers
# [DRY RUN] Would execute: gap_analysis → relevance_scoring → deep_review → visualization
# [DRY RUN] Estimated API calls: 450
# [DRY RUN] Estimated cost: $2.50-$3.00
# [DRY RUN] Estimated duration: 15-20 minutes
# [DRY RUN] No actual execution performed
```

**User Problems:**
- Cannot preview analysis plan before execution
- Cannot estimate costs before committing
- Cannot validate configuration (file paths, options)
- No way to test setup without spending money
- Cannot see what stages will run (especially with resume)
- Costly mistakes if configuration wrong

**Gap:** No dry-run preview capability in Dashboard.

---

## 🎯 Objective

Add dry-run mode matching CLI's `--dry-run` flag, allowing users to preview analysis plan, cost estimates, and execution stages without performing actual analysis.

---

## 📐 Design

### UI Components

**Location 1:** Advanced Options Panel (checkbox to enable)  
**Location 2:** Start button (changes behavior when dry-run enabled)  
**Location 3:** Dry-run results modal (shows preview)

**Dry-Run Checkbox in Advanced Options:**

```html
<!-- Dry-Run Mode Control (in Advanced Options Panel) -->
<div class="card mb-3 border-info">
    <div class="card-header bg-info bg-opacity-10">
        <h6 class="mb-0">🧪 Dry-Run Mode</h6>
    </div>
    <div class="card-body">
        
        <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" 
                   id="enableDryRun" onchange="updateDryRunMode()">
            <label class="form-check-label" for="enableDryRun">
                <strong>Enable Dry-Run (Preview Only)</strong>
                <span class="badge bg-info">CLI: --dry-run</span>
            </label>
        </div>
        
        <div class="form-text mt-2">
            Preview analysis plan and cost estimates without executing. 
            No API calls made, no charges incurred. Use to validate configuration.
        </div>
        
        <div id="dryRunBenefits" style="display: none;" class="alert alert-info mt-3 mb-0">
            <strong>Dry-Run Benefits:</strong>
            <ul class="mb-0">
                <li>✅ Preview analysis stages and order</li>
                <li>✅ Estimate API calls and costs</li>
                <li>✅ Validate file paths and configuration</li>
                <li>✅ See which papers will be processed</li>
                <li>✅ Verify resume/cache behavior</li>
                <li>❌ No actual analysis performed</li>
                <li>❌ No results generated</li>
            </ul>
        </div>
        
    </div>
</div>

<script>
function updateDryRunMode() {
    const enabled = document.getElementById('enableDryRun').checked;
    
    document.getElementById('dryRunBenefits').style.display = 
        enabled ? 'block' : 'none';
    
    // Update start button text
    const startButton = document.getElementById('startAnalysisButton');
    if (enabled) {
        startButton.textContent = '🧪 Preview Analysis (Dry-Run)';
        startButton.classList.remove('btn-success');
        startButton.classList.add('btn-info');
    } else {
        startButton.textContent = '🚀 Start Analysis';
        startButton.classList.remove('btn-info');
        startButton.classList.add('btn-success');
    }
}
</script>
```

**Dry-Run Results Modal:**

```html
<!-- Dry-Run Results Modal -->
<div class="modal fade" id="dryRunResultsModal" tabindex="-1">
    <div class="modal-dialog modal-xl">
        <div class="modal-content">
            <div class="modal-header bg-info text-white">
                <h5 class="modal-title">🧪 Dry-Run Preview</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                
                <!-- Summary Cards -->
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card border-primary">
                            <div class="card-body text-center">
                                <div class="small text-muted">Papers to Process</div>
                                <div class="display-6 fw-bold" id="dryRunPaperCount">0</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card border-warning">
                            <div class="card-body text-center">
                                <div class="small text-muted">Est. API Calls</div>
                                <div class="display-6 fw-bold text-warning" id="dryRunApiCalls">0</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card border-success">
                            <div class="card-body text-center">
                                <div class="small text-muted">Est. Cost</div>
                                <div class="display-6 fw-bold text-success" id="dryRunCost">$0.00</div>
                                <div class="small text-muted" id="dryRunCostRange">$0.00 - $0.00</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card border-secondary">
                            <div class="card-body text-center">
                                <div class="small text-muted">Est. Duration</div>
                                <div class="display-6 fw-bold text-secondary" id="dryRunDuration">0m</div>
                                <div class="small text-muted" id="dryRunDurationRange">0-0 min</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Execution Plan -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h6 class="mb-0">📋 Execution Plan</h6>
                    </div>
                    <div class="card-body">
                        <ol id="dryRunExecutionPlan" class="mb-0">
                            <!-- Populated dynamically -->
                        </ol>
                    </div>
                </div>
                
                <!-- Configuration Summary -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h6 class="mb-0">⚙️ Configuration</h6>
                    </div>
                    <div class="card-body">
                        <dl class="row mb-0" id="dryRunConfig">
                            <!-- Populated dynamically -->
                        </dl>
                    </div>
                </div>
                
                <!-- File List -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h6 class="mb-0">📄 Files to Process</h6>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>Filename</th>
                                        <th>Type</th>
                                        <th>Size</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody id="dryRunFileList">
                                    <!-- Populated dynamically -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                
                <!-- Warnings -->
                <div id="dryRunWarnings" style="display: none;">
                    <div class="alert alert-warning">
                        <h6>⚠️ Warnings</h6>
                        <ul id="dryRunWarningList" class="mb-0">
                            <!-- Populated if warnings exist -->
                        </ul>
                    </div>
                </div>
                
                <!-- Notice -->
                <div class="alert alert-info mb-0">
                    <strong>ℹ️ Notice:</strong> This is a preview only. No actual analysis has been performed. 
                    Estimates are based on historical averages and may vary. Click "Proceed with Analysis" to execute.
                </div>
                
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    Close Preview
                </button>
                <button type="button" class="btn btn-success" onclick="proceedWithAnalysis()">
                    ✅ Proceed with Analysis
                </button>
            </div>
        </div>
    </div>
</div>

<script>
// Display dry-run results
function displayDryRunResults(data) {
    // Summary cards
    document.getElementById('dryRunPaperCount').textContent = data.paper_count;
    document.getElementById('dryRunApiCalls').textContent = data.estimated_api_calls;
    document.getElementById('dryRunCost').textContent = '$' + data.estimated_cost.toFixed(2);
    document.getElementById('dryRunCostRange').textContent = 
        `$${data.cost_range.min.toFixed(2)} - $${data.cost_range.max.toFixed(2)}`;
    document.getElementById('dryRunDuration').textContent = 
        Math.round(data.estimated_duration_minutes) + 'm';
    document.getElementById('dryRunDurationRange').textContent = 
        `${data.duration_range.min}-${data.duration_range.max} min`;
    
    // Execution plan
    const planList = document.getElementById('dryRunExecutionPlan');
    planList.innerHTML = '';
    data.execution_plan.forEach((step, index) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <strong>${step.stage}</strong> 
            <span class="badge bg-${step.status === 'skip' ? 'secondary' : 'primary'}">
                ${step.status}
            </span>
            <br>
            <small class="text-muted">${step.description}</small>
            <br>
            <small>Est. API calls: ${step.estimated_api_calls}, Cost: $${step.estimated_cost.toFixed(2)}</small>
        `;
        planList.appendChild(li);
    });
    
    // Configuration
    const configDl = document.getElementById('dryRunConfig');
    configDl.innerHTML = '';
    Object.entries(data.configuration).forEach(([key, value]) => {
        const dt = document.createElement('dt');
        dt.className = 'col-sm-3';
        dt.textContent = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        
        const dd = document.createElement('dd');
        dd.className = 'col-sm-9';
        dd.textContent = typeof value === 'object' ? JSON.stringify(value) : value;
        
        configDl.appendChild(dt);
        configDl.appendChild(dd);
    });
    
    // File list
    const fileList = document.getElementById('dryRunFileList');
    fileList.innerHTML = '';
    data.files.forEach((file, index) => {
        const row = fileList.insertRow();
        row.insertCell().textContent = index + 1;
        row.insertCell().textContent = file.filename;
        row.insertCell().textContent = file.type.toUpperCase();
        row.insertCell().textContent = (file.size_bytes / 1024).toFixed(1) + ' KB';
        
        const statusCell = row.insertCell();
        const statusBadge = document.createElement('span');
        statusBadge.className = 'badge bg-' + (file.cached ? 'success' : 'secondary');
        statusBadge.textContent = file.cached ? 'Cached' : 'New';
        statusCell.appendChild(statusBadge);
    });
    
    // Warnings
    if (data.warnings && data.warnings.length > 0) {
        document.getElementById('dryRunWarnings').style.display = 'block';
        const warningList = document.getElementById('dryRunWarningList');
        warningList.innerHTML = '';
        data.warnings.forEach(warning => {
            const li = document.createElement('li');
            li.textContent = warning;
            warningList.appendChild(li);
        });
    } else {
        document.getElementById('dryRunWarnings').style.display = 'none';
    }
    
    // Store data for proceed action
    window.dryRunData = data;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('dryRunResultsModal'));
    modal.show();
}

// Proceed with actual analysis after dry-run
function proceedWithAnalysis() {
    // Disable dry-run
    document.getElementById('enableDryRun').checked = false;
    updateDryRunMode();
    
    // Close modal
    bootstrap.Modal.getInstance(document.getElementById('dryRunResultsModal')).hide();
    
    // Trigger actual start
    startAnalysis();
}
</script>
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**Dry-Run Endpoint:**

```python
class JobConfig(BaseModel):
    """Job configuration with dry-run option."""
    mode: str = "baseline"
    dry_run: bool = False
    # ... other options ...


@app.post(
    "/api/jobs/{job_id}/dry-run",
    tags=["Analysis"],
    summary="Preview analysis plan without execution"
)
async def dry_run_job(
    job_id: str,
    config: JobConfig,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Perform dry-run: estimate costs and preview execution plan.
    
    No actual analysis performed. No API calls made.
    """
    verify_api_key(api_key)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Load job metadata
    metadata = load_job_metadata(job_id)
    
    # Get file list
    files = get_job_files(job_dir, metadata)
    
    # Build execution plan
    execution_plan = build_execution_plan(config, metadata, files)
    
    # Estimate costs and duration
    estimates = estimate_job_resources(execution_plan, files, config)
    
    # Detect potential issues
    warnings = detect_dry_run_warnings(config, metadata, files)
    
    return {
        "job_id": job_id,
        "dry_run": True,
        "paper_count": len(files),
        "estimated_api_calls": estimates["api_calls"],
        "estimated_cost": estimates["cost"],
        "cost_range": {
            "min": estimates["cost_min"],
            "max": estimates["cost_max"]
        },
        "estimated_duration_minutes": estimates["duration_minutes"],
        "duration_range": {
            "min": estimates["duration_min"],
            "max": estimates["duration_max"]
        },
        "execution_plan": execution_plan,
        "configuration": {
            "mode": config.mode,
            "output_dir": metadata.get("output_dir", "auto"),
            "pre_filter": config.pre_filter or "default",
            "resume_from_stage": config.resume_from_stage,
            "force_reanalysis": config.force,
            "cache_enabled": not config.clear_cache
        },
        "files": [
            {
                "filename": f["filename"],
                "type": f["type"],
                "size_bytes": f["size"],
                "cached": check_if_cached(f["path"])
            }
            for f in files
        ],
        "warnings": warnings
    }


def build_execution_plan(config: JobConfig, metadata: Dict, files: List) -> List[Dict]:
    """Build execution plan showing stages and status."""
    stages = [
        {
            "name": "gap_analysis",
            "display": "Gap Analysis",
            "description": "Extract research gaps from papers"
        },
        {
            "name": "relevance_scoring",
            "display": "Relevance Scoring",
            "description": "Score gaps by relevance to query"
        },
        {
            "name": "deep_review",
            "display": "Deep Review",
            "description": "Detailed analysis of top gaps"
        },
        {
            "name": "visualization",
            "display": "Visualization",
            "description": "Generate interactive HTML reports"
        }
    ]
    
    plan = []
    resume_from = config.resume_from_stage
    
    for stage in stages:
        # Determine if stage will run or be skipped
        status = "run"
        estimated_calls = 0
        estimated_cost = 0.0
        
        if resume_from and stage["name"] != resume_from:
            # Skipped due to resume
            status = "skip"
        else:
            # Calculate estimates
            if stage["name"] == "gap_analysis":
                estimated_calls = len(files) * 2  # ~2 calls per paper
                estimated_cost = estimated_calls * 0.005  # ~$0.005 per call
            elif stage["name"] == "relevance_scoring":
                estimated_calls = len(files) * 1
                estimated_cost = estimated_calls * 0.003
            elif stage["name"] == "deep_review":
                estimated_calls = min(len(files), 10) * 3  # Top 10 papers
                estimated_cost = estimated_calls * 0.01
            elif stage["name"] == "visualization":
                estimated_calls = 0  # No API calls
                estimated_cost = 0.0
            
            # Reset resume flag once we hit resume stage
            if resume_from == stage["name"]:
                resume_from = None
        
        plan.append({
            "stage": stage["display"],
            "stage_name": stage["name"],
            "description": stage["description"],
            "status": status,
            "estimated_api_calls": estimated_calls,
            "estimated_cost": estimated_cost
        })
    
    return plan


def estimate_job_resources(execution_plan: List, files: List, config: JobConfig) -> Dict:
    """Estimate total resources needed."""
    total_calls = sum(s["estimated_api_calls"] for s in execution_plan if s["status"] == "run")
    total_cost = sum(s["estimated_cost"] for s in execution_plan if s["status"] == "run")
    
    # Apply variance for range estimates
    cost_min = total_cost * 0.8
    cost_max = total_cost * 1.2
    
    # Estimate duration (rough: 2-5 papers/minute)
    papers_per_minute = 3.5
    duration_minutes = len(files) / papers_per_minute
    duration_min = duration_minutes * 0.7
    duration_max = duration_minutes * 1.3
    
    return {
        "api_calls": total_calls,
        "cost": total_cost,
        "cost_min": cost_min,
        "cost_max": cost_max,
        "duration_minutes": duration_minutes,
        "duration_min": int(duration_min),
        "duration_max": int(duration_max)
    }


def detect_dry_run_warnings(config: JobConfig, metadata: Dict, files: List) -> List[str]:
    """Detect potential configuration issues."""
    warnings = []
    
    # Large dataset warning
    if len(files) > 100:
        warnings.append(
            f"Large dataset ({len(files)} papers). Consider using pre-filter to reduce analysis scope."
        )
    
    # Output directory warning
    if metadata.get("output_dir") and Path(metadata["output_dir"]).exists():
        existing_results = list(Path(metadata["output_dir"]).glob("*.csv"))
        if existing_results and not config.force:
            warnings.append(
                f"Output directory contains existing results. Use 'Force Re-analysis' to overwrite."
            )
    
    # Resume without existing results
    if config.resume_from_stage:
        output_dir = Path(metadata.get("output_dir", ""))
        if not output_dir.exists():
            warnings.append(
                f"Resume requested but output directory does not exist. Cannot resume."
            )
    
    # Budget warning
    estimates = estimate_job_resources(
        build_execution_plan(config, metadata, files),
        files,
        config
    )
    
    if config.cost_budget and estimates["cost"] > config.cost_budget:
        warnings.append(
            f"Estimated cost (${estimates['cost']:.2f}) exceeds budget (${config.cost_budget:.2f})"
        )
    
    return warnings


def get_job_files(job_dir: Path, metadata: Dict) -> List[Dict]:
    """Get list of files for job."""
    files = []
    
    if metadata.get("input_method") == "directory":
        # Directory input: scan directory
        data_dir = Path(metadata["data_dir"])
        for pdf in data_dir.glob("**/*.pdf"):
            files.append({
                "filename": pdf.name,
                "path": str(pdf),
                "type": "pdf",
                "size": pdf.stat().st_size
            })
        for csv in data_dir.glob("**/*.csv"):
            files.append({
                "filename": csv.name,
                "path": str(csv),
                "type": "csv",
                "size": csv.stat().st_size
            })
    else:
        # Upload method: scan uploads directory
        upload_dir = job_dir / "uploads"
        if upload_dir.exists():
            for file in upload_dir.iterdir():
                if file.suffix.lower() in ['.pdf', '.csv']:
                    files.append({
                        "filename": file.name,
                        "path": str(file),
                        "type": file.suffix.lstrip('.').lower(),
                        "size": file.stat().st_size
                    })
    
    return files


def check_if_cached(file_path: str) -> bool:
    """Check if file results are cached."""
    # Simplified: check if file exists in cache directory
    # In production, check actual cache keys
    cache_dir = Path("gap_extraction_cache")
    if not cache_dir.exists():
        return False
    
    file_hash = hashlib.md5(Path(file_path).read_bytes()).hexdigest()
    return any(file_hash in str(cache_file) for cache_file in cache_dir.glob("*.json"))
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Dry-run checkbox in Advanced Options
- [ ] Start button changes when dry-run enabled
- [ ] Dry-run endpoint returns preview without execution
- [ ] Preview modal shows paper count, API calls, cost estimates
- [ ] Execution plan lists stages (run/skip)
- [ ] Configuration summary displays all settings
- [ ] File list shows papers to process
- [ ] Warnings detect potential issues
- [ ] "Proceed with Analysis" button starts actual execution

### User Experience
- [ ] Checkbox toggle clear and intuitive
- [ ] Preview modal comprehensive and readable
- [ ] Estimates presented with ranges (min-max)
- [ ] Warnings prominent but not alarming
- [ ] Easy transition from preview to execution

### Estimation Accuracy
- [ ] API call estimates within 20% of actual
- [ ] Cost estimates within 25% of actual
- [ ] Duration estimates within 30% of actual
- [ ] Execution plan matches actual stages run

### CLI Parity
- [ ] Dry-run → `--dry-run` (100% parity)
- [ ] Same estimation logic as CLI
- [ ] Same warning detection as CLI

### Edge Cases
- [ ] Dry-run with resume → shows skipped stages
- [ ] Dry-run with force → no cache savings shown
- [ ] Dry-run with cached papers → shows cache hits
- [ ] Large dataset → appropriate warnings

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_dry_run.py

def test_dry_run_basic():
    """Test basic dry-run request."""
    job_id = create_test_job(paper_count=10)
    
    response = client.post(f"/api/jobs/{job_id}/dry-run",
                          json={"mode": "baseline"},
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"] is True
    assert data["paper_count"] == 10
    assert data["estimated_api_calls"] > 0
    assert data["estimated_cost"] > 0

def test_dry_run_execution_plan():
    """Test execution plan generation."""
    job_id = create_test_job(paper_count=5)
    
    response = client.post(f"/api/jobs/{job_id}/dry-run",
                          json={"mode": "baseline"}).json()
    
    plan = response["execution_plan"]
    assert len(plan) == 4  # 4 stages
    assert all(s["status"] == "run" for s in plan)

def test_dry_run_with_resume():
    """Test dry-run with resume from stage."""
    job_id = create_test_job()
    
    response = client.post(f"/api/jobs/{job_id}/dry-run",
                          json={
                              "mode": "baseline",
                              "resume_from_stage": "deep_review"
                          }).json()
    
    plan = response["execution_plan"]
    
    # First two stages should be skipped
    assert plan[0]["status"] == "skip"  # gap_analysis
    assert plan[1]["status"] == "skip"  # relevance_scoring
    assert plan[2]["status"] == "run"   # deep_review
    assert plan[3]["status"] == "run"   # visualization

def test_dry_run_warnings():
    """Test warning detection."""
    job_id = create_test_job(paper_count=150)
    
    response = client.post(f"/api/jobs/{job_id}/dry-run",
                          json={"mode": "baseline"}).json()
    
    assert len(response["warnings"]) > 0
    assert any("Large dataset" in w for w in response["warnings"])
```

### Integration Tests

```python
def test_e2e_dry_run_workflow():
    """End-to-end: dry-run → review → proceed → execute."""
    # 1. Create job
    job_id = upload_test_files()
    
    # 2. Dry-run
    dry_run = client.post(f"/api/jobs/{job_id}/dry-run",
                         json={"mode": "baseline"}).json()
    
    assert dry_run["dry_run"] is True
    estimated_cost = dry_run["estimated_cost"]
    
    # 3. Proceed with actual execution
    client.post(f"/api/jobs/{job_id}/start",
               json={"mode": "baseline", "dry_run": False})
    
    # 4. Wait for completion
    wait_for_job_completion(job_id)
    
    # 5. Compare actual vs estimated
    actual_cost = get_actual_cost(job_id)
    assert abs(actual_cost - estimated_cost) / estimated_cost < 0.25  # Within 25%
```

### Manual Testing Checklist

- [ ] Enable dry-run → checkbox checked, button changes
- [ ] Start with dry-run → preview modal appears
- [ ] Preview shows paper count, estimates, plan
- [ ] Execution plan shows 4 stages
- [ ] File list shows all papers
- [ ] Configuration accurate
- [ ] Close preview → can reconfigure
- [ ] "Proceed" → dry-run disabled, analysis starts
- [ ] Dry-run with resume → skip stages shown
- [ ] Large dataset → warning appears

---

## 📚 Documentation Updates

### User Guide

```markdown
## Dry-Run Mode

Preview your analysis plan and cost estimates before execution. No API calls made, no charges incurred.

### When to Use

- **First time users:** Validate setup before committing
- **Large datasets:** Estimate costs for 100+ papers
- **Complex config:** Verify resume, force, pre-filter settings
- **Budget conscious:** Ensure staying within budget

### How to Use

1. Configure analysis normally (upload files, select options)
2. Expand **Advanced Options**
3. Check **Enable Dry-Run (Preview Only)**
4. Notice "Start Analysis" button changes to "Preview Analysis (Dry-Run)"
5. Click preview button
6. Review:
   - **Summary:** Papers, API calls, cost estimates
   - **Execution Plan:** Stages to run (with resume, some may be skipped)
   - **Configuration:** All settings being used
   - **Files:** Papers to process (cached status)
   - **Warnings:** Potential issues detected
7. Either:
   - **Close Preview:** Adjust configuration, run dry-run again
   - **Proceed with Analysis:** Execute for real

### What Dry-Run Shows

**Estimates (with ranges):**
- API calls needed
- Total cost (min-max)
- Duration (min-max)

**Execution Plan:**
- Stages that will run
- Stages that will be skipped (resume)
- Per-stage API calls and costs

**Warnings:**
- Large datasets requiring pre-filter
- Existing results that won't be overwritten
- Budget overruns
- Configuration conflicts

### Accuracy

Estimates based on historical averages:
- **API calls:** ±20% actual
- **Cost:** ±25% actual
- **Duration:** ±30% actual

Actual values depend on paper content, model performance, cache hits.

### CLI Equivalent

Dry-Run Mode: `--dry-run`
```

---

## 🚀 Deployment Checklist

- [ ] Dry-run checkbox in Advanced Options
- [ ] Start button text/style updates
- [ ] Dry-run results modal implemented
- [ ] Dry-run endpoint deployed (`/api/jobs/{id}/dry-run`)
- [ ] Execution plan builder working
- [ ] Resource estimation accurate
- [ ] Warning detection working
- [ ] "Proceed" workflow functional
- [ ] Unit tests passing (4+ tests, 85% coverage)
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Estimation accuracy validated
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Deployed to staging
- [ ] User acceptance testing
- [ ] Deployed to production

---

## 📊 Success Metrics

**After Deployment:**
- Dry-run mode functional (100%)
- Dashboard parity increases by 1% (preview capability)
- Users can validate configuration before execution
- Cost surprises reduced

**Monitoring:**
- Track % of jobs using dry-run first
- Track dry-run → proceed conversion rate
- Track estimation accuracy (actual vs predicted)
- Collect user feedback on estimates

---

**Task Card Version:** 1.0  
**Created:** November 22, 2025  
**Estimated Effort:** 6-8 hours  
**Priority:** 🟡 MEDIUM  
**Dependency:** Requires PARITY-W1-2 (Advanced Options Panel)
