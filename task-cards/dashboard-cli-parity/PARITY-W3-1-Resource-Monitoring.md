# PARITY-W3-1: Resource Monitoring Dashboard

**Priority:** 🟡 **MEDIUM**  
**Effort:** 10-14 hours  
**Wave:** 3 (Enhancement Features)  
**Dependencies:** None (standalone feature)

---

## 📋 Problem Statement

**Current State:**  
Dashboard provides no visibility into resource consumption during pipeline execution. Users cannot monitor API usage, costs, cache hits, or processing rates in real-time.

**CLI Capability:**
```bash
# CLI shows resource metrics in logs
[INFO] API calls: 45/100 budget
[INFO] Cost: $2.35/$10.00
[INFO] Cache hits: 12/45 (26.7%)
[INFO] Processing: 8/50 papers (16%)
```

**User Problems:**
- No real-time cost tracking → surprise bills
- Cannot see cache effectiveness
- No API rate limit visibility → unexpected throttling
- Cannot estimate time remaining
- No processing rate metrics
- Cannot tell if analysis is progressing or stuck

**Gap:** Zero visibility into resource consumption and processing state.

---

## 🎯 Objective

Add real-time resource monitoring dashboard showing API usage, costs, cache performance, and processing progress during job execution. Exceeds CLI capabilities with visual dashboard.

---

## 📐 Design

### UI Components

**Location:** Job Detail Page (`webdashboard/templates/job_detail.html`)

**Resource Monitoring Dashboard:**

```html
<!-- Resource Monitoring Dashboard (on job detail page) -->
<div id="resourceMonitoring" style="display: none;" class="mb-4">
    <div class="card border-primary">
        <div class="card-header bg-primary text-white">
            <div class="d-flex justify-content-between align-items-center">
                <h5 class="mb-0">📊 Resource Monitoring</h5>
                <div>
                    <span class="badge bg-light text-dark me-2">
                        Auto-refresh: <span id="refreshCountdown">5</span>s
                    </span>
                    <button class="btn btn-sm btn-outline-light" onclick="refreshResourceMetrics()">
                        🔄 Refresh Now
                    </button>
                </div>
            </div>
        </div>
        <div class="card-body">
            
            <!-- Row 1: API Usage & Costs -->
            <div class="row mb-4">
                
                <!-- API Calls -->
                <div class="col-md-3">
                    <div class="card border-info h-100">
                        <div class="card-body text-center">
                            <div class="small text-muted mb-2">API Calls</div>
                            <div class="display-6 fw-bold" id="apiCallsCount">0</div>
                            <div class="small text-muted">
                                of <span id="apiBudget">1000</span> budget
                            </div>
                            <div class="progress mt-2" style="height: 8px;">
                                <div class="progress-bar bg-info" role="progressbar" 
                                     id="apiCallsProgress" style="width: 0%">
                                </div>
                            </div>
                            <div class="small mt-2">
                                <span id="apiCallsPercent">0%</span> used
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Cost -->
                <div class="col-md-3">
                    <div class="card border-success h-100">
                        <div class="card-body text-center">
                            <div class="small text-muted mb-2">Total Cost</div>
                            <div class="display-6 fw-bold text-success" id="totalCost">$0.00</div>
                            <div class="small text-muted">
                                of <span id="costBudget">$100.00</span> budget
                            </div>
                            <div class="progress mt-2" style="height: 8px;">
                                <div class="progress-bar bg-success" role="progressbar" 
                                     id="costProgress" style="width: 0%">
                                </div>
                            </div>
                            <div class="small mt-2">
                                Avg: <span id="avgCostPerPaper">$0.00</span>/paper
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Cache Performance -->
                <div class="col-md-3">
                    <div class="card border-warning h-100">
                        <div class="card-body text-center">
                            <div class="small text-muted mb-2">Cache Hit Rate</div>
                            <div class="display-6 fw-bold text-warning" id="cacheHitRate">0%</div>
                            <div class="small text-muted">
                                <span id="cacheHits">0</span> hits / 
                                <span id="cacheMisses">0</span> misses
                            </div>
                            <div class="progress mt-2" style="height: 8px;">
                                <div class="progress-bar bg-warning" role="progressbar" 
                                     id="cacheHitProgress" style="width: 0%">
                                </div>
                            </div>
                            <div class="small mt-2">
                                Saved: <span id="cacheSavings">$0.00</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Processing Rate -->
                <div class="col-md-3">
                    <div class="card border-secondary h-100">
                        <div class="card-body text-center">
                            <div class="small text-muted mb-2">Processing Rate</div>
                            <div class="display-6 fw-bold text-secondary" id="processingRate">0</div>
                            <div class="small text-muted">papers/minute</div>
                            <div class="mt-2">
                                <div class="small">ETA: <strong id="eta">Calculating...</strong></div>
                            </div>
                            <div class="small mt-2">
                                Elapsed: <span id="elapsed">0m 0s</span>
                            </div>
                        </div>
                    </div>
                </div>
                
            </div>
            
            <!-- Row 2: Processing Progress -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card border-primary">
                        <div class="card-body">
                            <div class="d-flex justify-content-between mb-2">
                                <h6 class="mb-0">Processing Progress</h6>
                                <span class="badge bg-primary" id="currentStage">Initializing</span>
                            </div>
                            
                            <div class="progress mb-2" style="height: 30px;">
                                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                     role="progressbar" id="overallProgress" style="width: 0%">
                                    <strong id="overallProgressText">0%</strong>
                                </div>
                            </div>
                            
                            <div class="row small">
                                <div class="col-md-3">
                                    <strong>Papers:</strong> 
                                    <span id="papersProcessed">0</span> / 
                                    <span id="totalPapers">0</span>
                                </div>
                                <div class="col-md-3">
                                    <strong>Stage:</strong> 
                                    <span id="stageProgress">0/4</span>
                                </div>
                                <div class="col-md-3">
                                    <strong>Started:</strong> 
                                    <span id="startTime">-</span>
                                </div>
                                <div class="col-md-3">
                                    <strong>Est. Complete:</strong> 
                                    <span id="estimatedCompletion">-</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Row 3: Stage Breakdown -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">Stage Breakdown</h6>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm table-borderless mb-0">
                                <thead>
                                    <tr>
                                        <th>Stage</th>
                                        <th>Status</th>
                                        <th>API Calls</th>
                                        <th>Cost</th>
                                        <th>Cache Hits</th>
                                        <th>Duration</th>
                                    </tr>
                                </thead>
                                <tbody id="stageBreakdownTable">
                                    <tr>
                                        <td>Gap Analysis</td>
                                        <td><span class="badge bg-secondary">Pending</span></td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                    </tr>
                                    <tr>
                                        <td>Relevance Scoring</td>
                                        <td><span class="badge bg-secondary">Pending</span></td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                    </tr>
                                    <tr>
                                        <td>Deep Review</td>
                                        <td><span class="badge bg-secondary">Pending</span></td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                    </tr>
                                    <tr>
                                        <td>Visualization</td>
                                        <td><span class="badge bg-secondary">Pending</span></td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Row 4: Resource Timeline Chart -->
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">Resource Usage Timeline</h6>
                        </div>
                        <div class="card-body">
                            <canvas id="resourceTimelineChart" height="80"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
// Resource monitoring state
let resourceChart = null;
let refreshInterval = null;
let refreshCountdown = 5;

// Initialize resource monitoring
function initResourceMonitoring() {
    const jobStatus = document.getElementById('jobStatus').textContent;
    
    if (jobStatus === 'running') {
        document.getElementById('resourceMonitoring').style.display = 'block';
        refreshResourceMetrics();
        startAutoRefresh();
    } else {
        stopAutoRefresh();
    }
}

// Refresh resource metrics
async function refreshResourceMetrics() {
    const jobId = getCurrentJobId();
    
    try {
        const response = await fetch(`/api/jobs/${jobId}/resources`, {
            headers: {'X-API-KEY': API_KEY}
        });
        
        const data = await response.json();
        updateResourceDashboard(data);
        
    } catch (error) {
        console.error('Failed to fetch resource metrics:', error);
    }
}

// Update dashboard with new data
function updateResourceDashboard(data) {
    // API Calls
    document.getElementById('apiCallsCount').textContent = data.api_calls.total;
    document.getElementById('apiBudget').textContent = data.api_calls.budget || 'unlimited';
    
    const apiPercent = data.api_calls.budget ? 
        (data.api_calls.total / data.api_calls.budget * 100).toFixed(1) : 0;
    document.getElementById('apiCallsPercent').textContent = apiPercent + '%';
    document.getElementById('apiCallsProgress').style.width = Math.min(apiPercent, 100) + '%';
    
    // Cost
    document.getElementById('totalCost').textContent = '$' + data.cost.total.toFixed(2);
    document.getElementById('costBudget').textContent = '$' + (data.cost.budget || 100).toFixed(2);
    document.getElementById('avgCostPerPaper').textContent = 
        '$' + (data.cost.total / Math.max(data.progress.papers_processed, 1)).toFixed(3);
    
    const costPercent = data.cost.budget ? 
        (data.cost.total / data.cost.budget * 100).toFixed(1) : 0;
    document.getElementById('costProgress').style.width = Math.min(costPercent, 100) + '%';
    
    // Cache
    const hitRate = data.cache.total > 0 ? 
        (data.cache.hits / data.cache.total * 100).toFixed(1) : 0;
    document.getElementById('cacheHitRate').textContent = hitRate + '%';
    document.getElementById('cacheHits').textContent = data.cache.hits;
    document.getElementById('cacheMisses').textContent = data.cache.misses;
    document.getElementById('cacheHitProgress').style.width = hitRate + '%';
    document.getElementById('cacheSavings').textContent = '$' + (data.cache.savings || 0).toFixed(2);
    
    // Processing Rate
    document.getElementById('processingRate').textContent = 
        (data.processing.rate || 0).toFixed(2);
    document.getElementById('eta').textContent = data.processing.eta || 'Calculating...';
    document.getElementById('elapsed').textContent = formatDuration(data.processing.elapsed);
    
    // Progress
    document.getElementById('currentStage').textContent = data.progress.current_stage;
    document.getElementById('papersProcessed').textContent = data.progress.papers_processed;
    document.getElementById('totalPapers').textContent = data.progress.total_papers;
    
    const overallPercent = data.progress.total_papers > 0 ? 
        (data.progress.papers_processed / data.progress.total_papers * 100).toFixed(1) : 0;
    document.getElementById('overallProgress').style.width = overallPercent + '%';
    document.getElementById('overallProgressText').textContent = overallPercent + '%';
    
    document.getElementById('stageProgress').textContent = 
        `${data.progress.stage_number}/4`;
    document.getElementById('startTime').textContent = 
        new Date(data.progress.start_time).toLocaleTimeString();
    
    if (data.processing.eta_timestamp) {
        document.getElementById('estimatedCompletion').textContent = 
            new Date(data.processing.eta_timestamp).toLocaleTimeString();
    }
    
    // Stage breakdown
    updateStageBreakdown(data.stages);
    
    // Timeline chart
    updateResourceChart(data.timeline);
}

// Update stage breakdown table
function updateStageBreakdown(stages) {
    const tbody = document.getElementById('stageBreakdownTable');
    tbody.innerHTML = '';
    
    const stageNames = ['gap_analysis', 'relevance_scoring', 'deep_review', 'visualization'];
    const stageLabels = ['Gap Analysis', 'Relevance Scoring', 'Deep Review', 'Visualization'];
    
    stageNames.forEach((stageName, index) => {
        const stage = stages[stageName] || {};
        const row = tbody.insertRow();
        
        // Stage name
        row.insertCell().textContent = stageLabels[index];
        
        // Status badge
        const statusCell = row.insertCell();
        const statusBadge = document.createElement('span');
        statusBadge.className = 'badge bg-' + getStatusColor(stage.status);
        statusBadge.textContent = stage.status || 'Pending';
        statusCell.appendChild(statusBadge);
        
        // Metrics
        row.insertCell().textContent = stage.api_calls || '-';
        row.insertCell().textContent = stage.cost ? '$' + stage.cost.toFixed(2) : '-';
        row.insertCell().textContent = stage.cache_hits || '-';
        row.insertCell().textContent = stage.duration ? formatDuration(stage.duration) : '-';
    });
}

function getStatusColor(status) {
    const colors = {
        'Pending': 'secondary',
        'Running': 'primary',
        'Completed': 'success',
        'Failed': 'danger',
        'Skipped': 'warning'
    };
    return colors[status] || 'secondary';
}

// Update timeline chart
function updateResourceChart(timelineData) {
    const ctx = document.getElementById('resourceTimelineChart').getContext('2d');
    
    if (resourceChart) {
        resourceChart.destroy();
    }
    
    resourceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timelineData.map(d => new Date(d.timestamp).toLocaleTimeString()),
            datasets: [
                {
                    label: 'API Calls/min',
                    data: timelineData.map(d => d.api_rate),
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    yAxisID: 'y'
                },
                {
                    label: 'Cost/min ($)',
                    data: timelineData.map(d => d.cost_rate),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'API Calls/min' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: 'Cost/min ($)' },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}

// Auto-refresh logic
function startAutoRefresh() {
    refreshCountdown = 5;
    
    refreshInterval = setInterval(() => {
        refreshCountdown--;
        document.getElementById('refreshCountdown').textContent = refreshCountdown;
        
        if (refreshCountdown <= 0) {
            refreshResourceMetrics();
            refreshCountdown = 5;
        }
    }, 1000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Format duration (seconds to human-readable)
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initResourceMonitoring);

// Stop auto-refresh when page unloads
window.addEventListener('beforeunload', stopAutoRefresh);
</script>
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**Resource Metrics Endpoint:**

```python
from datetime import datetime, timedelta
from typing import Dict, List
import json

@app.get(
    "/api/jobs/{job_id}/resources",
    tags=["Monitoring"],
    summary="Get real-time resource metrics"
)
async def get_job_resources(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get real-time resource consumption metrics for running job.
    
    Returns API usage, costs, cache performance, and processing rates.
    """
    verify_api_key(api_key)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Load job metadata
    metadata = load_job_metadata(job_id)
    
    # Parse cost tracker
    cost_data = parse_cost_tracker(job_dir)
    
    # Parse orchestrator state
    state_file = job_dir / "orchestrator_state.json"
    state = {}
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
    
    # Calculate metrics
    start_time = datetime.fromisoformat(metadata.get("started_at", datetime.now().isoformat()))
    elapsed = (datetime.now() - start_time).total_seconds()
    
    papers_processed = state.get("papers_processed", 0)
    total_papers = state.get("total_papers", metadata.get("paper_count", 0))
    
    processing_rate = papers_processed / (elapsed / 60) if elapsed > 0 else 0
    remaining_papers = total_papers - papers_processed
    eta_minutes = remaining_papers / processing_rate if processing_rate > 0 else 0
    
    return {
        "api_calls": {
            "total": cost_data.get("total_api_calls", 0),
            "budget": metadata.get("api_budget"),
            "remaining": metadata.get("api_budget", 0) - cost_data.get("total_api_calls", 0)
        },
        "cost": {
            "total": cost_data.get("total_cost", 0.0),
            "budget": metadata.get("cost_budget", 100.0),
            "remaining": metadata.get("cost_budget", 100.0) - cost_data.get("total_cost", 0.0),
            "by_model": cost_data.get("by_model", {})
        },
        "cache": {
            "hits": cost_data.get("cache_hits", 0),
            "misses": cost_data.get("cache_misses", 0),
            "total": cost_data.get("cache_hits", 0) + cost_data.get("cache_misses", 0),
            "savings": cost_data.get("cache_savings", 0.0)
        },
        "processing": {
            "rate": processing_rate,
            "elapsed": elapsed,
            "eta": format_eta(eta_minutes),
            "eta_timestamp": (datetime.now() + timedelta(minutes=eta_minutes)).isoformat()
        },
        "progress": {
            "papers_processed": papers_processed,
            "total_papers": total_papers,
            "current_stage": state.get("current_stage", "Unknown"),
            "stage_number": state.get("stage_number", 0),
            "start_time": start_time.isoformat()
        },
        "stages": {
            "gap_analysis": get_stage_metrics(job_dir, "gap_analysis", cost_data),
            "relevance_scoring": get_stage_metrics(job_dir, "relevance_scoring", cost_data),
            "deep_review": get_stage_metrics(job_dir, "deep_review", cost_data),
            "visualization": get_stage_metrics(job_dir, "visualization", cost_data)
        },
        "timeline": get_resource_timeline(job_dir)
    }


def parse_cost_tracker(job_dir: Path) -> Dict:
    """Parse cost tracker CSV for resource metrics."""
    cost_file = job_dir / "outputs" / "cost_reports" / "cost_tracker.csv"
    
    if not cost_file.exists():
        return {
            "total_api_calls": 0,
            "total_cost": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_savings": 0.0,
            "by_model": {}
        }
    
    import csv
    
    total_calls = 0
    total_cost = 0.0
    cache_hits = 0
    cache_misses = 0
    by_model = {}
    
    with open(cost_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_calls += 1
            cost = float(row.get("cost", 0.0))
            total_cost += cost
            
            if row.get("cache_hit", "").lower() == "true":
                cache_hits += 1
            else:
                cache_misses += 1
            
            model = row.get("model", "unknown")
            if model not in by_model:
                by_model[model] = {"calls": 0, "cost": 0.0}
            by_model[model]["calls"] += 1
            by_model[model]["cost"] += cost
    
    # Estimate savings (cached calls would have cost average)
    avg_cost = total_cost / cache_misses if cache_misses > 0 else 0
    cache_savings = cache_hits * avg_cost
    
    return {
        "total_api_calls": total_calls,
        "total_cost": total_cost,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "cache_savings": cache_savings,
        "by_model": by_model
    }


def get_stage_metrics(job_dir: Path, stage_name: str, cost_data: Dict) -> Dict:
    """Get metrics for specific pipeline stage."""
    # Check if stage completed
    stage_marker = job_dir / f".{stage_name}_complete"
    
    if not stage_marker.exists():
        return {"status": "Pending"}
    
    # Parse stage-specific cost data
    stage_costs = [
        row for row in cost_data.get("rows", [])
        if stage_name in row.get("stage", "")
    ]
    
    return {
        "status": "Completed",
        "api_calls": len(stage_costs),
        "cost": sum(float(row.get("cost", 0)) for row in stage_costs),
        "cache_hits": sum(1 for row in stage_costs if row.get("cache_hit") == "true"),
        "duration": get_stage_duration(stage_marker)
    }


def get_stage_duration(marker_file: Path) -> float:
    """Calculate stage duration from marker file timestamp."""
    if not marker_file.exists():
        return 0.0
    
    # Simplified: use file modification time
    # In production, parse actual stage start/end from logs
    return (datetime.now() - datetime.fromtimestamp(
        marker_file.stat().st_mtime
    )).total_seconds()


def get_resource_timeline(job_dir: Path, points: int = 20) -> List[Dict]:
    """
    Get timeline of resource usage over job execution.
    
    Returns list of data points for charting.
    """
    # Simplified implementation
    # In production, parse timestamped log entries or checkpoints
    
    timeline = []
    
    # Stub data for demonstration
    # Replace with actual log parsing
    for i in range(points):
        timeline.append({
            "timestamp": (datetime.now() - timedelta(minutes=points-i)).isoformat(),
            "api_rate": 5 + (i % 3) * 2,  # Simulated
            "cost_rate": 0.05 + (i % 3) * 0.02  # Simulated
        })
    
    return timeline


def format_eta(minutes: float) -> str:
    """Format ETA in human-readable form."""
    if minutes < 1:
        return f"{int(minutes * 60)}s"
    elif minutes < 60:
        return f"{int(minutes)}m"
    else:
        hours = int(minutes / 60)
        mins = int(minutes % 60)
        return f"{hours}h {mins}m"
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Resource dashboard appears for running jobs
- [ ] API calls counter tracks total calls and budget
- [ ] Cost tracker shows total cost and average per paper
- [ ] Cache hit rate displays hits, misses, percentage
- [ ] Processing rate calculates papers/minute
- [ ] ETA estimates time remaining
- [ ] Stage breakdown shows per-stage metrics
- [ ] Timeline chart visualizes resource usage over time
- [ ] Auto-refresh updates metrics every 5 seconds

### User Experience
- [ ] Dashboard layout clear and organized
- [ ] Progress bars visual and intuitive
- [ ] Metrics update smoothly without flicker
- [ ] Countdown shows time until next refresh
- [ ] Manual refresh button works instantly
- [ ] Chart readable and informative

### Data Accuracy
- [ ] API call count matches cost tracker
- [ ] Cost calculation correct (matches cost reports)
- [ ] Cache hit rate calculation accurate
- [ ] Processing rate realistic (papers/elapsed time)
- [ ] ETA updates as job progresses
- [ ] Stage status reflects actual pipeline state

### Performance
- [ ] Refresh doesn't block UI
- [ ] Chart rendering smooth (<100ms)
- [ ] Auto-refresh interval reasonable (not too frequent)
- [ ] Resource endpoint responds quickly (<500ms)

### Edge Cases
- [ ] No cost data yet → shows zeros gracefully
- [ ] No budget set → shows "unlimited"
- [ ] Processing rate zero → ETA shows "Calculating..."
- [ ] Job completes → auto-refresh stops

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_resource_monitoring.py

def test_get_resources_success():
    """Test fetching resource metrics."""
    job_id = create_running_job()
    
    response = client.get(f"/api/jobs/{job_id}/resources",
                         headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert "api_calls" in data
    assert "cost" in data
    assert "cache" in data
    assert "processing" in data

def test_resource_calculations():
    """Test resource metric calculations."""
    # Create job with known cost data
    job_id = create_job_with_cost_data(
        api_calls=50,
        cost=2.5,
        cache_hits=10,
        cache_misses=40
    )
    
    response = client.get(f"/api/jobs/{job_id}/resources").json()
    
    assert response["api_calls"]["total"] == 50
    assert response["cost"]["total"] == 2.5
    assert response["cache"]["hits"] == 10
    assert response["cache"]["total"] == 50

def test_eta_calculation():
    """Test ETA calculation logic."""
    # 100 papers, 25 done in 10 minutes = 2.5 papers/min
    # 75 remaining / 2.5 = 30 minutes ETA
    
    job_id = create_job_with_progress(
        total=100,
        processed=25,
        elapsed_minutes=10
    )
    
    response = client.get(f"/api/jobs/{job_id}/resources").json()
    
    assert abs(response["processing"]["rate"] - 2.5) < 0.1
    assert "30m" in response["processing"]["eta"]
```

### Integration Tests

```python
def test_e2e_resource_monitoring():
    """End-to-end: start job → monitor resources → complete."""
    # Start job
    job_id = upload_and_start_job()
    
    # Wait briefly
    time.sleep(5)
    
    # Fetch resources
    resources = client.get(f"/api/jobs/{job_id}/resources").json()
    
    # Verify metrics present
    assert resources["api_calls"]["total"] > 0
    assert resources["cost"]["total"] > 0
    assert resources["processing"]["rate"] >= 0
    
    # Wait for completion
    wait_for_job_completion(job_id)
    
    # Final metrics
    final = client.get(f"/api/jobs/{job_id}/resources").json()
    assert final["progress"]["papers_processed"] == final["progress"]["total_papers"]
```

### Manual Testing Checklist

- [ ] Start job → resource dashboard appears
- [ ] Metrics update automatically every 5 seconds
- [ ] Countdown shows 5→4→3→2→1→5 (refresh)
- [ ] Manual refresh button updates immediately
- [ ] Progress bar fills as job progresses
- [ ] ETA decreases as job progresses
- [ ] Stage breakdown updates when stage changes
- [ ] Timeline chart shows data points
- [ ] Job completes → auto-refresh stops

---

## 📚 Documentation Updates

### User Guide

```markdown
## Resource Monitoring

The Resource Monitoring dashboard provides real-time visibility into pipeline resource consumption during job execution.

### Dashboard Overview

**Top Row (4 Metric Cards):**
1. **API Calls:** Total API calls vs budget, usage percentage
2. **Total Cost:** Cumulative cost vs budget, average per paper
3. **Cache Hit Rate:** Cache hits/misses, savings estimate
4. **Processing Rate:** Papers per minute, estimated completion time

**Processing Progress:**
- Overall progress bar (papers processed / total)
- Current stage indicator
- Started time and estimated completion

**Stage Breakdown Table:**
- Per-stage metrics: API calls, cost, cache hits, duration
- Status indicators (Pending/Running/Completed/Failed)

**Resource Timeline Chart:**
- API calls per minute over time (left axis)
- Cost per minute over time (right axis)
- Visual trends and spikes

### Auto-Refresh

Dashboard auto-refreshes every 5 seconds while job is running. Countdown shows time until next refresh. Click "Refresh Now" for immediate update.

### Use Cases

**Monitor Costs:**
- Track spending in real-time
- Catch budget overruns early
- Compare actual vs estimated costs

**Optimize Performance:**
- Identify slow stages
- Verify cache is working (high hit rate)
- Estimate total job duration

**Debug Issues:**
- Zero processing rate → pipeline stalled
- High API rate → possible inefficiency
- Low cache hit rate → cache not effective

### Interpreting Metrics

**Good Cache Hit Rate:** 30-60% (depends on resume/force settings)  
**Typical Processing Rate:** 2-5 papers/minute (varies by analysis depth)  
**Expected Cost:** $0.01-$0.10 per paper (baseline mode)

Dashboard exceeds CLI capabilities by providing real-time visual monitoring.
```

---

## 🚀 Deployment Checklist

- [ ] Resource dashboard UI implemented
- [ ] 4 metric cards styled correctly
- [ ] Progress bar and stage breakdown working
- [ ] Timeline chart rendering with Chart.js
- [ ] Auto-refresh logic implemented (5s interval)
- [ ] Resource endpoint deployed (`/api/jobs/{id}/resources`)
- [ ] Cost tracker parsing working
- [ ] ETA calculation accurate
- [ ] Stage metrics extraction working
- [ ] Timeline data generation working
- [ ] Unit tests passing (3+ tests, 85% coverage)
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Deployed to staging
- [ ] Performance validated (<500ms response)
- [ ] User acceptance testing passed
- [ ] Deployed to production

---

## 📊 Success Metrics

**After Deployment:**
- Resource monitoring functional (100%)
- Dashboard **exceeds** CLI (real-time visual monitoring)
- Users can track costs in real-time
- Users can estimate completion times

**Monitoring:**
- Track usage of resource dashboard (% of running jobs viewed)
- Track manual vs auto refreshes
- Collect user feedback on metrics usefulness
- Monitor endpoint performance

---

**Task Card Version:** 1.0  
**Created:** November 22, 2025  
**Estimated Effort:** 10-14 hours  
**Priority:** 🟡 MEDIUM  
**Dependency:** None (standalone enhancement)
