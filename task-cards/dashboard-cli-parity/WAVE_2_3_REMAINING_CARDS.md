# Remaining Task Cards - Waves 2 & 3

This document contains streamlined task cards for the remaining 6 tasks. Each includes key sections but in condensed format. Full expansion available upon request.

---

## PARITY-W2-4: Resume Controls

**Priority:** 🟠 HIGH | **Effort:** 8-12h | **Wave:** 2

### Problem
CLI has `--resume-from-stage X` and `--resume-from-checkpoint X.json` for recovery. Dashboard must restart from beginning.

### Solution
Add stage selector and checkpoint resumption in Advanced Options (already designed in W1-2).

### Key Features
- **Stage Progress Indicator:** Visual diagram showing Gap Analysis → Relevance → Deep Review → Visualization
- **Stage Selector:** Dropdown to skip completed stages
- **Checkpoint Auto-detection:** Scan output directory for `pipeline_checkpoint.json`
- **Manual Checkpoint Upload:** For external checkpoints
- **Resume Failed Jobs:** Button in job detail view

### UI Components
```html
<!-- Resume from Stage -->
<div class="form-check mb-2">
    <input type="checkbox" id="enableResume">
    <label>Resume from Stage</label>
</div>
<select id="resumeStage" disabled>
    <option value="gap_analysis">Gap Analysis</option>
    <option value="relevance_scoring">Relevance Scoring</option>
    <option value="deep_review">Deep Review</option>
    <option value="visualization">Visualization</option>
</select>

<!-- Resume from Checkpoint -->
<div class="form-check mb-2">
    <input type="checkbox" id="enableCheckpointResume">
    <label>Resume from Checkpoint</label>
</div>
<input type="text" id="checkpointFile" placeholder="pipeline_checkpoint.json" disabled>
<button onclick="scanForCheckpoint()">Auto-detect</button>
```

### Backend
```python
# Add to job start
if config.resume_from_stage:
    cmd.extend(["--resume-from-stage", config.resume_from_stage])

if config.resume_from_checkpoint:
    checkpoint_path = validate_checkpoint_file(config.resume_from_checkpoint)
    cmd.extend(["--resume-from-checkpoint", str(checkpoint_path)])

@app.get("/api/jobs/{job_id}/checkpoints")
async def scan_checkpoints(job_id: str):
    """Scan job directory for checkpoint files."""
    output_dir = get_job_output_dir(job_id)
    checkpoints = list(output_dir.glob("*checkpoint*.json"))
    return {"checkpoints": [str(c) for c in checkpoints]}
```

### Testing
- Checkpoint auto-detection works
- Resume from each stage functional
- Failed jobs resumable from UI
- Invalid checkpoints rejected

### CLI Parity: 100%

---

## PARITY-W2-5: Pre-filter Configuration

**Priority:** 🟠 HIGH | **Effort:** 6-8h | **Wave:** 2

### Problem
CLI allows configuring pre-filter threshold. Dashboard uses hardcoded 50%.

### Solution
Add slider for pre-filter percentage (0-100%) with live paper count estimate.

### Key Features
- **Threshold Slider:** 0-100% with visual indicator
- **Live Preview:** "Will pre-filter ~X of Y papers"
- **Cost Estimation:** "Estimated savings: $X.XX"
- **Toggle:** Enable/disable pre-filtering entirely

### UI Components
```html
<div class="mb-3">
    <label>Pre-filter Threshold</label>
    <div class="row align-items-center">
        <div class="col-8">
            <input type="range" id="prefilterThreshold" 
                   min="0" max="100" value="50" step="5"
                   oninput="updatePrefilterPreview(this.value)">
        </div>
        <div class="col-4">
            <input type="number" id="prefilterValue" 
                   value="50" min="0" max="100">%
        </div>
    </div>
    <div class="form-text">
        Higher = more papers filtered out (faster, cheaper)
    </div>
    
    <!-- Live Preview -->
    <div id="prefilterPreview" class="alert alert-info mt-2">
        <strong>Preview:</strong><br>
        Papers uploaded: <span id="totalPapers">10</span><br>
        Will pass pre-filter: <span id="passedPapers">5</span> (~50%)<br>
        Estimated cost: $<span id="estimatedCost">2.50</span>
    </div>
</div>

<script>
async function updatePrefilterPreview(threshold) {
    const totalPapers = getUploadedFileCount();
    const passRate = (100 - threshold) / 100;
    const passedPapers = Math.round(totalPapers * passRate);
    
    document.getElementById('totalPapers').textContent = totalPapers;
    document.getElementById('passedPapers').textContent = passedPapers;
    
    // Get cost estimate
    const response = await fetch('/api/cost/estimate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-API-KEY': API_KEY},
        body: JSON.stringify({paper_count: passedPapers})
    });
    const estimate = await response.json();
    document.getElementById('estimatedCost').textContent = estimate.fresh_cost.toFixed(2);
}
</script>
```

### Backend
```python
# Load default config
with open("pipeline_config.json") as f:
    config = json.load(f)

# Override pre-filter threshold
if request.prefilter_threshold is not None:
    config["pre_filtering"]["threshold"] = request.prefilter_threshold / 100.0
    
    # Save modified config
    custom_config_path = job_dir / "custom_config.json"
    with open(custom_config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    cmd.extend(["--config", str(custom_config_path)])
```

### Testing
- Slider updates preview in real-time
- Cost estimate accurate
- Config override works
- 0% and 100% edge cases handled

### CLI Parity: 85% (config file approach, not direct flag)

---

## PARITY-W3-1: Resource Monitoring Dashboard

**Priority:** 🟡 MEDIUM | **Effort:** 10-14h | **Wave:** 3

### Problem
CLI shows resource usage in logs. Dashboard has no live monitoring.

### Solution
Real-time WebSocket-based resource monitoring widget with live cost tracking.

### Key Features
- **Live Cost Tracker:** Updates as API calls made
- **Budget Progress Bar:** Visual indicator with 75%, 90%, 100% warnings
- **API Call Counter:** By model and stage
- **CPU/Memory Graphs:** Line charts (last 5 minutes)
- **Rate Limit Status:** Calls remaining, reset time

### UI Components
```html
<!-- Resource Monitor Widget -->
<div class="card">
    <div class="card-header">⚡ Live Resource Monitor</div>
    <div class="card-body">
        
        <!-- Budget Progress -->
        <div class="mb-3">
            <label>Budget: $<span id="currentCost">0.00</span> / $<span id="budgetLimit">5.00</span></label>
            <div class="progress">
                <div id="budgetProgress" class="progress-bar" style="width: 0%"></div>
            </div>
        </div>
        
        <!-- API Calls -->
        <div class="row mb-3">
            <div class="col-6">
                <strong>API Calls:</strong> <span id="apiCallCount">0</span>
            </div>
            <div class="col-6">
                <strong>Cache Hits:</strong> <span id="cacheHitCount">0</span>
            </div>
        </div>
        
        <!-- CPU/Memory Chart -->
        <canvas id="resourceChart" height="100"></canvas>
        
    </div>
</div>

<script>
// WebSocket connection for live updates
const ws = new WebSocket(`ws://localhost:8000/ws/jobs/${jobId}/monitor`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Update budget
    document.getElementById('currentCost').textContent = data.cost.toFixed(2);
    const budgetPercent = (data.cost / data.budget) * 100;
    document.getElementById('budgetProgress').style.width = budgetPercent + '%';
    
    // Change color based on threshold
    if (budgetPercent >= 90) {
        document.getElementById('budgetProgress').className = 'progress-bar bg-danger';
    } else if (budgetPercent >= 75) {
        document.getElementById('budgetProgress').className = 'progress-bar bg-warning';
    }
    
    // Update counters
    document.getElementById('apiCallCount').textContent = data.api_calls;
    document.getElementById('cacheHitCount').textContent = data.cache_hits;
    
    // Update chart
    updateResourceChart(data.cpu, data.memory, data.timestamp);
};
</script>
```

### Backend
```python
@app.websocket("/ws/jobs/{job_id}/monitor")
async def websocket_monitor(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time resource monitoring."""
    await websocket.accept()
    
    try:
        while True:
            # Get current job stats
            stats = get_job_resource_stats(job_id)
            
            await websocket.send_json({
                "cost": stats["total_cost"],
                "budget": stats["budget_limit"],
                "api_calls": stats["api_calls"],
                "cache_hits": stats["cache_hits"],
                "cpu": stats["cpu_percent"],
                "memory": stats["memory_mb"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Update every second
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info(f"Monitor disconnected for job {job_id}")


def get_job_resource_stats(job_id: str) -> dict:
    """Get current resource usage for running job."""
    # Load cost report
    cost_report_path = BASE_DIR / "cost_reports" / f"{job_id}_cost.json"
    if cost_report_path.exists():
        with open(cost_report_path) as f:
            cost_data = json.load(f)
    else:
        cost_data = {"total_cost": 0.0, "api_calls": 0, "cache_hits": 0}
    
    # Get process stats (if running)
    cpu_percent = 0.0
    memory_mb = 0.0
    
    # Find running process for this job
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if job_id in ' '.join(proc.info['cmdline'] or []):
                cpu_percent = proc.cpu_percent(interval=0.1)
                memory_mb = proc.memory_info().rss / (1024 * 1024)
                break
        except:
            pass
    
    # Get budget from job metadata
    job_metadata = load_job_metadata(job_id)
    budget_limit = job_metadata.get("budget_limit", 0.0)
    
    return {
        "total_cost": cost_data["total_cost"],
        "budget_limit": budget_limit,
        "api_calls": cost_data["api_calls"],
        "cache_hits": cost_data["cache_hits"],
        "cpu_percent": cpu_percent,
        "memory_mb": memory_mb
    }
```

### Testing
- WebSocket connects successfully
- Updates arrive every second
- Budget warnings trigger at correct thresholds
- Charts render correctly
- Handles job completion (websocket close)

### CLI Parity: 120% (Dashboard advantage - CLI only has logs)

---

## PARITY-W3-2: Direct Directory Access

**Priority:** 🟡 MEDIUM | **Effort:** 12-16h | **Wave:** 3

### Problem
Dashboard import copies files. Should work in-place like CLI.

### Solution
Add "Work in-place" mode using symlinks, no copying.

### Key Features
- **In-place Checkbox:** Work directly with user directory
- **Symlink Creation:** Link to input files instead of copying
- **Direct Output:** Write to user path, no UUID intermediary
- **Import-free Continuation:** Continue CLI jobs without copying

### Implementation
```python
@app.post("/api/upload/batch")
async def upload_batch(
    files: List[UploadFile],
    config: UploadConfig,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Upload with optional in-place mode."""
    
    if config.work_in_place:
        # Don't copy files, use symlinks
        for uploaded_file in files:
            src_path = config.source_directory / uploaded_file.filename
            link_path = output_dir / uploaded_file.filename
            
            # Create symlink instead of copying
            link_path.symlink_to(src_path)
        
        logger.info(f"Created symlinks for in-place work (no copying)")
    else:
        # Normal upload: copy files
        for uploaded_file in files:
            dest_path = output_dir / uploaded_file.filename
            with open(dest_path, "wb") as f:
                content = await uploaded_file.read()
                f.write(content)
```

### Testing
- Symlinks created correctly
- Pipeline runs with symlinked files
- No disk duplication
- Works across filesystem boundaries (when possible)

### CLI Parity: 100%

---

## PARITY-W3-3: Dry-Run Mode

**Priority:** 🟡 MEDIUM | **Effort:** 6-8h | **Wave:** 3

### Problem
CLI has `--dry-run` to validate without execution. Dashboard has no preview.

### Solution
Dry-run checkbox (already in W1-2) with execution plan preview.

### Key Features
- **Execution Plan:** Shows stages, papers, API calls
- **Cost Estimation:** Model calls and pricing
- **Configuration Validation:** Errors highlighted before running
- **Convert to Real Run:** One-click button

### UI Components
```html
<!-- Dry Run Results -->
<div id="dryRunResults" class="card">
    <div class="card-header">🔍 Dry Run Results</div>
    <div class="card-body">
        
        <h6>Execution Plan:</h6>
        <ol>
            <li>Gap Analysis: <strong>10 papers</strong> → gemini-1.5-pro → ~30 API calls</li>
            <li>Relevance Scoring: <strong>10 papers</strong> → gemini-1.5-flash → ~10 API calls</li>
            <li>Deep Review: <strong>5 papers</strong> (filtered) → gemini-1.5-pro → ~15 API calls</li>
            <li>Visualization: Local processing (no API calls)</li>
        </ol>
        
        <h6>Cost Estimate:</h6>
        <table class="table table-sm">
            <tr><td>Gap Analysis:</td><td>$3.75</td></tr>
            <tr><td>Relevance Scoring:</td><td>$0.50</td></tr>
            <tr><td>Deep Review:</td><td>$2.25</td></tr>
            <tr><th>Total:</th><th>$6.50</th></tr>
        </table>
        
        <button class="btn btn-primary" onclick="convertToRealRun()">
            ▶️ Convert to Real Run
        </button>
    </div>
</div>
```

### Backend
```python
if config.dry_run:
    # Don't execute, just validate and estimate
    plan = generate_execution_plan(job_id, config)
    
    return {
        "status": "validated",
        "dry_run": True,
        "execution_plan": plan,
        "estimated_cost": plan["total_cost"],
        "estimated_duration": plan["total_duration_minutes"]
    }
```

### Testing
- Dry run shows accurate plan
- Cost estimate matches actual (within 10%)
- No API calls made during dry run
- Convert to real run works

### CLI Parity: 100%

---

## PARITY-W3-4: Experimental Features Toggle

**Priority:** 🟡 MEDIUM | **Effort:** 4-6h | **Wave:** 3

### Problem
CLI has `--experimental` flag. Dashboard doesn't expose experimental features.

### Solution
Experimental features checkbox (already in W1-2) with individual feature toggles.

### Key Features
- **Master Toggle:** "Enable Experimental Features"
- **Individual Toggles:** When multiple experimental features exist
- **Warnings:** Clear stability/support notices
- **Changelog:** List of experimental features
- **Feedback Form:** Report bugs in experimental features

### UI Components
```html
<!-- Experimental Features -->
<div class="mb-3">
    <div class="form-check form-switch">
        <input type="checkbox" id="experimentalFeatures">
        <label>Enable Experimental Features</label>
    </div>
    <div class="alert alert-warning mt-2">
        ⚠️ <strong>Unstable Features</strong><br>
        Experimental features may change or break without notice.
        Not recommended for production use.
    </div>
    
    <!-- Individual Features (when expanded) -->
    <div id="experimentalFeaturesDetail" style="display: none;">
        <div class="form-check">
            <input type="checkbox" id="expFeature1">
            <label>Advanced Caching (v0.9 beta)</label>
        </div>
        <div class="form-check">
            <input type="checkbox" id="expFeature2">
            <label>Parallel Scoring (v0.8 alpha)</label>
        </div>
    </div>
</div>
```

### Backend
```python
if config.experimental:
    cmd.append("--experimental")
    
    # Log experimental usage
    logger.warning(f"Job {job_id} using experimental features")
    
    job_metadata["experimental_enabled"] = True
    job_metadata["experimental_features"] = config.experimental_features_list
```

### Testing
- Master toggle enables/disables all
- Individual toggles work independently
- Warning shown prominently
- Experimental flag passed to CLI

### CLI Parity: 100%

---

## Summary

All 6 remaining tasks provide essential functionality:

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| W2-4: Resume Controls | 🟠 HIGH | 8-12h | Failed job recovery |
| W2-5: Pre-filter Config | 🟠 HIGH | 6-8h | Cost optimization |
| W3-1: Resource Monitor | 🟡 MEDIUM | 10-14h | Live visibility |
| W3-2: Direct Directory | 🟡 MEDIUM | 12-16h | No duplication |
| W3-3: Dry-Run | 🟡 MEDIUM | 6-8h | Preview/validation |
| W3-4: Experimental | 🟡 MEDIUM | 4-6h | Opt-in features |

**Total:** 46-64 hours (6-8 developer-days)

Combined with Wave 1 (28-38h) and completed Wave 2 tasks (18-24h), achieves **95%+ parity** target.

