# ENHANCE-P3-2: Progress Replay for Historical Jobs

**Status:** NOT IMPLEMENTED  
**Priority:** 🟢 Low  
**Effort Estimate:** 4 hours  
**Category:** Phase 3 - Progress Monitoring  
**Created:** November 17, 2025  
**Related PR:** #38 (Real-time Progress Monitoring)

---

## 📋 Overview

Add ability to view progress timeline for completed jobs, showing how long each stage took. Useful for debugging slow runs and understanding job performance.

**Use Case:**
- User completes job in 45 minutes (expected 20 minutes)
- Wants to see: "Which stage was slow? Deep review took 30 min instead of usual 10 min"
- Current limitation: Progress tracking only works for active jobs, no history

**Current State:**
- Progress bar shows real-time progress during job execution
- Once job completes, progress data is lost
- No way to see historical stage durations
- Can't compare performance across jobs

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Save stage timestamps to job metadata
- [ ] Reconstruct progress timeline from completed job
- [ ] Display as read-only progress visualization
- [ ] Show duration for each stage

### Should Have
- [ ] Color-coded stages (green = fast, yellow = normal, red = slow)
- [ ] Compare to average duration (e.g., "2x slower than average")
- [ ] Timeline chart (Gantt-style visualization)
- [ ] Filter/sort jobs by total duration

### Nice to Have
- [ ] Identify bottleneck stage automatically
- [ ] Export progress report as CSV
- [ ] Progress comparison between two jobs
- [ ] Performance trend over time (are jobs getting slower?)

---

## 🛠️ Technical Implementation

### 1. Enhanced Job Metadata Schema

**Already Implemented (from ENHANCE-P3-1):**
```json
{
  "id": "job_123",
  "status": "completed",
  "progress": {
    "stages": {
      "gap_analysis": {
        "status": "completed",
        "start_time": "2025-11-17T10:00:00Z",
        "end_time": "2025-11-17T10:05:30Z",
        "duration_seconds": 330
      },
      "deep_review": {
        "status": "completed",
        "start_time": "2025-11-17T10:05:30Z",
        "end_time": "2025-11-17T10:25:00Z",
        "duration_seconds": 1170
      }
    }
  }
}
```

### 2. Backend: Progress Replay API

**New Endpoint:** `GET /api/jobs/<job_id>/progress-history`

```python
@app.route('/api/jobs/<job_id>/progress-history')
def get_progress_history(job_id):
    """Get historical progress timeline for completed job"""
    job_data = load_job_data(job_id)
    
    if job_data['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    stages = job_data.get('progress', {}).get('stages', {})
    
    if not stages:
        return jsonify({'error': 'No progress data available'}), 404
    
    # Calculate stage statistics
    timeline = []
    total_duration = 0
    
    for stage_name, stage_data in stages.items():
        duration = stage_data.get('duration_seconds', 0)
        total_duration += duration
        
        timeline.append({
            'stage': stage_name,
            'start_time': stage_data['start_time'],
            'end_time': stage_data['end_time'],
            'duration_seconds': duration,
            'duration_human': format_duration(duration),
            'percentage': 0  # Calculated after total known
        })
    
    # Calculate percentages
    for item in timeline:
        item['percentage'] = round((item['duration_seconds'] / total_duration) * 100, 1)
    
    # Compare to historical averages
    eta_calculator = AdaptiveETACalculator()
    for item in timeline:
        avg_duration = eta_calculator.get_average_duration(item['stage'])
        if avg_duration:
            item['vs_average'] = round((item['duration_seconds'] / avg_duration) * 100, 1)
            item['performance'] = 'fast' if item['vs_average'] < 80 else 'slow' if item['vs_average'] > 120 else 'normal'
        else:
            item['vs_average'] = None
            item['performance'] = 'unknown'
    
    return jsonify({
        'job_id': job_id,
        'total_duration_seconds': total_duration,
        'total_duration_human': format_duration(total_duration),
        'timeline': timeline,
        'slowest_stage': max(timeline, key=lambda x: x['duration_seconds'])['stage'],
        'start_time': job_data.get('start_time'),
        'end_time': job_data.get('end_time')
    })

def format_duration(seconds):
    """Format seconds as human-readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}min {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}min"
```

### 3. Frontend: Progress History Viewer

**New Modal:** `webdashboard/templates/index.html`

```html
<!-- Progress History Modal -->
<div class="modal" id="progressHistoryModal" tabindex="-1">
    <div class="modal-dialog modal-xl">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Progress Timeline - Job <span id="history-job-id"></span></h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <!-- Total Duration Summary -->
                <div class="alert alert-info">
                    <strong>Total Duration:</strong> <span id="total-duration"></span>
                    <br>
                    <strong>Slowest Stage:</strong> <span id="slowest-stage"></span>
                </div>
                
                <!-- Timeline Chart (Gantt-style) -->
                <div id="timeline-chart" style="height: 200px;"></div>
                
                <!-- Stage Details Table -->
                <h6 class="mt-4">Stage Breakdown</h6>
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Stage</th>
                            <th>Duration</th>
                            <th>% of Total</th>
                            <th>vs Average</th>
                            <th>Performance</th>
                        </tr>
                    </thead>
                    <tbody id="stage-details">
                        <!-- Populated dynamically -->
                    </tbody>
                </table>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                <button class="btn btn-primary" onclick="exportProgressReport()">Export CSV</button>
            </div>
        </div>
    </div>
</div>
```

**JavaScript:**
```javascript
async function viewProgressHistory(jobId) {
    const response = await fetch(`/api/jobs/${jobId}/progress-history`);
    const data = await response.json();
    
    // Populate modal
    document.getElementById('history-job-id').textContent = jobId;
    document.getElementById('total-duration').textContent = data.total_duration_human;
    document.getElementById('slowest-stage').textContent = data.slowest_stage;
    
    // Render timeline chart
    renderTimelineChart(data.timeline);
    
    // Populate stage details table
    const tbody = document.getElementById('stage-details');
    tbody.innerHTML = '';
    
    for (let stage of data.timeline) {
        const row = `
            <tr>
                <td>${stage.stage}</td>
                <td>${stage.duration_human}</td>
                <td>${stage.percentage}%</td>
                <td>${stage.vs_average ? stage.vs_average + '%' : 'N/A'}</td>
                <td>
                    <span class="badge bg-${performanceColor(stage.performance)}">
                        ${stage.performance}
                    </span>
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    }
    
    // Show modal
    new bootstrap.Modal(document.getElementById('progressHistoryModal')).show();
}

function renderTimelineChart(timeline) {
    """Render Gantt-style timeline chart using Plotly"""
    const traces = timeline.map(stage => ({
        x: [new Date(stage.start_time), new Date(stage.end_time)],
        y: [stage.stage, stage.stage],
        mode: 'lines',
        line: {
            width: 20,
            color: performanceColor(stage.performance)
        },
        hovertemplate: `<b>${stage.stage}</b><br>Duration: ${stage.duration_human}<br><extra></extra>`
    }));
    
    const layout = {
        title: 'Stage Timeline',
        xaxis: {title: 'Time'},
        yaxis: {title: 'Stage'},
        showlegend: false,
        hovermode: 'closest'
    };
    
    Plotly.newPlot('timeline-chart', traces, layout);
}

function performanceColor(performance) {
    switch(performance) {
        case 'fast': return 'success';  // Green
        case 'normal': return 'primary';  // Blue
        case 'slow': return 'warning';  // Yellow
        default: return 'secondary';  // Gray
    }
}

function exportProgressReport() {
    """Export progress timeline as CSV"""
    const jobId = document.getElementById('history-job-id').textContent;
    
    // Trigger CSV download
    window.location.href = `/api/jobs/${jobId}/progress-history.csv`;
}
```

**CSS:**
```css
.timeline-chart {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 16px;
}

.stage-details tbody tr:hover {
    background-color: #f1f3f5;
    cursor: pointer;
}

.badge.bg-success {
    background-color: #28a745 !important;
}

.badge.bg-warning {
    background-color: #ffc107 !important;
    color: #000;
}
```

### 4. CSV Export Endpoint

**New Route:** `GET /api/jobs/<job_id>/progress-history.csv`

```python
import csv
from io import StringIO
from flask import Response

@app.route('/api/jobs/<job_id>/progress-history.csv')
def export_progress_history_csv(job_id):
    """Export progress history as CSV"""
    # Get progress data
    response_json = get_progress_history(job_id)
    data = response_json.get_json()
    
    if 'error' in data:
        return jsonify(data), 404
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Stage', 'Start Time', 'End Time', 'Duration (seconds)', 'Duration (human)', '% of Total', 'vs Average', 'Performance'])
    
    # Rows
    for stage in data['timeline']:
        writer.writerow([
            stage['stage'],
            stage['start_time'],
            stage['end_time'],
            stage['duration_seconds'],
            stage['duration_human'],
            f"{stage['percentage']}%",
            f"{stage['vs_average']}%" if stage['vs_average'] else 'N/A',
            stage['performance']
        ])
    
    # Total row
    writer.writerow([])
    writer.writerow(['TOTAL', '', '', data['total_duration_seconds'], data['total_duration_human'], '100%', '', ''])
    
    # Return as downloadable file
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=job_{job_id}_progress.csv'}
    )
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `tests/unit/test_progress_history.py`

```python
def test_progress_history_endpoint():
    """Test progress history API endpoint"""
    job_data = create_completed_job_with_progress()
    
    response = client.get(f'/api/jobs/{job_data["id"]}/progress-history')
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert 'timeline' in data
    assert 'total_duration_seconds' in data
    assert len(data['timeline']) > 0

def test_progress_history_incomplete_job():
    """Test error when job not completed"""
    job_data = create_running_job()
    
    response = client.get(f'/api/jobs/{job_data["id"]}/progress-history')
    
    assert response.status_code == 400
    assert 'not completed' in response.get_json()['error'].lower()

def test_stage_performance_calculation():
    """Test performance comparison to average"""
    # Mock slow stage (2x average)
    stage_data = {
        'duration_seconds': 600,  # 10 minutes
        'stage': 'gap_analysis'
    }
    
    # Mock average: 5 minutes
    avg_duration = 300
    
    vs_average = (stage_data['duration_seconds'] / avg_duration) * 100
    performance = 'slow' if vs_average > 120 else 'normal'
    
    assert vs_average == 200  # 2x slower
    assert performance == 'slow'

def test_csv_export():
    """Test CSV export format"""
    job_data = create_completed_job_with_progress()
    
    response = client.get(f'/api/jobs/{job_data["id"]}/progress-history.csv')
    
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    
    csv_content = response.data.decode('utf-8')
    assert 'Stage,Start Time,End Time' in csv_content
    assert 'gap_analysis' in csv_content
```

---

## 📚 Documentation Updates

**File:** `docs/DASHBOARD_GUIDE.md`

```markdown
## Viewing Historical Job Progress

### Progress Timeline

For completed jobs, click "View Progress" to see how long each stage took.

**What You'll See:**
- **Timeline Chart**: Gantt-style visualization of stage execution
- **Stage Breakdown**: Table with duration, percentage, and performance
- **Performance Indicators**:
  - 🟢 Green (Fast): <80% of average duration
  - 🔵 Blue (Normal): 80-120% of average
  - 🟡 Yellow (Slow): >120% of average

### Using Progress History

**Debugging Slow Jobs:**
1. Open completed job
2. Click "View Progress"
3. Identify slowest stage (highlighted)
4. Compare to average duration

**Example:**
```
Job #123 took 45 minutes (expected 20 minutes)

Stage Breakdown:
- Gap Analysis: 5min (normal)
- Deep Review: 35min (SLOW - 3x average)  ← Bottleneck!
- Proof Generation: 3min (fast)
- Final Report: 2min (normal)

Diagnosis: Deep review stage was slow. Likely cause:
- Too many papers (100 vs usual 10)
- API rate limiting
- Complex pillars
```

### Exporting Progress Reports

Click "Export CSV" to download progress timeline as spreadsheet. Useful for:
- Performance analysis
- Billing/time tracking
- Comparing multiple jobs
```

---

## 🚀 Deployment Notes

### Data Migration

**Backward Compatibility:**
- Old jobs without progress data: show "No progress data available"
- New jobs automatically track progress (from ENHANCE-P3-1)

**No Schema Changes Required:**
- Progress data already saved in job JSON (if ENHANCE-P3-1 implemented)

### Performance Considerations

- Progress history endpoint: <100ms (reads single JSON file)
- Timeline chart rendering: <500ms (Plotly client-side)
- CSV export: <200ms for typical job

---

## 🔗 Related Issues

- ENHANCE-P3-1: Improve ETA Accuracy (provides progress tracking data)
- PR #38: Real-time Progress Monitoring (live progress bar)
- Future: Performance trends dashboard (aggregate stats across all jobs)

---

## 📈 Success Metrics

**User Impact:**
- Understand why jobs took longer than expected
- Identify performance bottlenecks
- Make informed decisions (e.g., reduce paper count if deep review is slow)

**Technical Metrics:**
- 100% of completed jobs have progress history (if created after ENHANCE-P3-1)
- <1s to load progress history modal
- CSV export works for all completed jobs

---

## ✅ Definition of Done

- [ ] Backend: `/api/jobs/<id>/progress-history` endpoint implemented
- [ ] Backend: CSV export endpoint implemented
- [ ] Frontend: Progress history modal UI
- [ ] Frontend: Timeline chart rendering (Plotly/Chart.js)
- [ ] Frontend: Stage performance color coding
- [ ] Unit tests (≥90% coverage)
- [ ] Integration tests (API endpoints)
- [ ] Documentation updated (DASHBOARD_GUIDE.md)
- [ ] Manual testing with real jobs
- [ ] Code review approved
- [ ] Merged to main branch
