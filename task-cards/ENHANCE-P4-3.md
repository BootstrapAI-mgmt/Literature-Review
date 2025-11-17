# ENHANCE-P4-3: Results Comparison View

**Status:** NOT IMPLEMENTED  
**Priority:** 🟡 Medium  
**Effort Estimate:** 5 hours  
**Category:** Phase 4 - Results Visualization  
**Created:** November 17, 2025  
**Related PR:** #39 (Results Visualization API)

---

## 📋 Overview

Add side-by-side comparison of gap analysis runs to track research progress over time. Users need to see how incremental updates (adding more papers) improve completeness scores.

**Use Case:**
- Researcher runs gap analysis with 10 papers → 60% complete
- Adds 5 more papers → re-runs gap analysis
- Wants to see: "Which gaps were filled? How much did completeness improve?"

**Current Limitation:**
- Can view individual job results
- No way to compare two jobs side-by-side
- No visualization of improvement trends

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] UI component for selecting two jobs to compare
- [ ] Side-by-side comparison table showing delta in completeness
- [ ] Papers added/removed differential view
- [ ] Highlight which gaps were filled between runs

### Should Have
- [ ] Trend chart showing completeness improvement over time (line graph)
- [ ] Color-coded indicators (green = improved, red = regressed, gray = unchanged)
- [ ] Filter by pillar (compare specific pillar across runs)

### Nice to Have
- [ ] Export comparison report as PDF/CSV
- [ ] "Improvement Score" metric (percentage points gained)
- [ ] Annotations/notes on why certain runs performed better

---

## 🛠️ Technical Implementation

### 1. Backend API Endpoint

**New Route:** `GET /api/compare-jobs/<job_id_1>/<job_id_2>`

```python
@app.route('/api/compare-jobs/<job_id_1>/<job_id_2>')
def compare_jobs(job_id_1, job_id_2):
    """Compare two gap analysis jobs"""
    job1 = load_job_data(job_id_1)
    job2 = load_job_data(job_id_2)
    
    comparison = {
        'job1': {
            'id': job_id_1,
            'timestamp': job1['timestamp'],
            'completeness': extract_completeness(job1),
            'papers': extract_papers(job1),
            'gaps': extract_gaps(job1)
        },
        'job2': {
            'id': job_id_2,
            'timestamp': job2['timestamp'],
            'completeness': extract_completeness(job2),
            'papers': extract_papers(job2),
            'gaps': extract_gaps(job2)
        },
        'delta': {
            'completeness_change': job2_completeness - job1_completeness,
            'papers_added': list(set(job2_papers) - set(job1_papers)),
            'papers_removed': list(set(job1_papers) - set(job2_papers)),
            'gaps_filled': [g for g in job1_gaps if g not in job2_gaps],
            'new_gaps': [g for g in job2_gaps if g not in job1_gaps]
        }
    }
    return jsonify(comparison)
```

### 2. Frontend UI Component

**Location:** `webdashboard/templates/index.html`

```html
<!-- Comparison Modal -->
<div class="modal" id="comparisonModal">
    <div class="modal-dialog modal-xl">
        <div class="modal-content">
            <div class="modal-header">
                <h5>Compare Gap Analysis Results</h5>
                <button class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <!-- Job Selector -->
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label>Baseline Job (Earlier Run)</label>
                        <select id="baseline-job" class="form-select">
                            <!-- Populated dynamically -->
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label>Comparison Job (Later Run)</label>
                        <select id="comparison-job" class="form-select">
                            <!-- Populated dynamically -->
                        </select>
                    </div>
                </div>
                
                <!-- Comparison Results -->
                <div id="comparison-results">
                    <!-- Populated via AJAX -->
                </div>
            </div>
        </div>
    </div>
</div>
```

**JavaScript:**
```javascript
async function loadComparison(job1, job2) {
    const response = await fetch(`/api/compare-jobs/${job1}/${job2}`);
    const data = await response.json();
    
    const html = `
        <div class="comparison-summary">
            <h6>Completeness Improvement</h6>
            <div class="progress-comparison">
                <div>Baseline: ${data.job1.completeness}%</div>
                <div>Current: ${data.job2.completeness}%</div>
                <div class="delta ${data.delta.completeness_change >= 0 ? 'positive' : 'negative'}">
                    ${data.delta.completeness_change > 0 ? '+' : ''}${data.delta.completeness_change.toFixed(2)}%
                </div>
            </div>
        </div>
        
        <div class="papers-diff">
            <h6>Papers Changed</h6>
            <ul>
                ${data.delta.papers_added.map(p => `<li class="added">+ ${p}</li>`).join('')}
                ${data.delta.papers_removed.map(p => `<li class="removed">- ${p}</li>`).join('')}
            </ul>
        </div>
        
        <div class="gaps-diff">
            <h6>Gaps Filled (${data.delta.gaps_filled.length})</h6>
            <ul>
                ${data.delta.gaps_filled.map(g => `<li class="filled">✓ ${g}</li>`).join('')}
            </ul>
        </div>
    `;
    
    document.getElementById('comparison-results').innerHTML = html;
}
```

### 3. Trend Visualization (Optional Enhancement)

**Library:** Chart.js or Plotly

```javascript
function renderTrendChart(jobs) {
    const timestamps = jobs.map(j => j.timestamp);
    const completeness = jobs.map(j => j.completeness);
    
    const trace = {
        x: timestamps,
        y: completeness,
        mode: 'lines+markers',
        name: 'Completeness Over Time',
        line: {color: 'green'}
    };
    
    Plotly.newPlot('trend-chart', [trace], {
        title: 'Gap Analysis Progress',
        xaxis: {title: 'Date'},
        yaxis: {title: 'Completeness (%)', range: [0, 100]}
    });
}
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `tests/unit/test_comparison.py`

```python
def test_compare_jobs_basic():
    """Test basic job comparison"""
    job1 = create_mock_job(completeness=60, papers=['paper1', 'paper2'])
    job2 = create_mock_job(completeness=75, papers=['paper1', 'paper2', 'paper3'])
    
    comparison = compare_jobs(job1, job2)
    
    assert comparison['delta']['completeness_change'] == 15
    assert len(comparison['delta']['papers_added']) == 1
    assert 'paper3' in comparison['delta']['papers_added']

def test_compare_jobs_with_gaps():
    """Test gap differential calculation"""
    job1 = create_mock_job(gaps=['gap1', 'gap2', 'gap3'])
    job2 = create_mock_job(gaps=['gap2'])  # gap1 and gap3 filled
    
    comparison = compare_jobs(job1, job2)
    
    assert len(comparison['delta']['gaps_filled']) == 2
    assert 'gap1' in comparison['delta']['gaps_filled']
    assert 'gap3' in comparison['delta']['gaps_filled']

def test_compare_jobs_regression():
    """Test when completeness decreases (regression)"""
    job1 = create_mock_job(completeness=80)
    job2 = create_mock_job(completeness=70)  # Worse!
    
    comparison = compare_jobs(job1, job2)
    
    assert comparison['delta']['completeness_change'] == -10
    # Should flag as regression
```

### Integration Tests

**File:** `tests/integration/test_comparison_api.py`

```python
def test_comparison_endpoint(client):
    """Test /api/compare-jobs endpoint"""
    # Create two jobs
    job1_id = create_test_job(completeness=60)
    job2_id = create_test_job(completeness=75)
    
    response = client.get(f'/api/compare-jobs/{job1_id}/{job2_id}')
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'delta' in data
    assert data['delta']['completeness_change'] == 15

def test_comparison_with_invalid_job(client):
    """Test comparison with non-existent job"""
    response = client.get('/api/compare-jobs/invalid_id/also_invalid')
    
    assert response.status_code == 404
    assert 'error' in response.get_json()
```

### UI Tests (Manual)

**Test Cases:**
1. Select two jobs from dropdown → see comparison results
2. View papers added/removed → verify accuracy
3. Check completeness delta → verify math
4. Filter by pillar → see pillar-specific comparison
5. Export comparison report → verify CSV format

---

## 📚 Documentation Updates

### User Guide Addition

**File:** `docs/DASHBOARD_GUIDE.md`

**New Section:**
```markdown
## Comparing Gap Analysis Results

### Why Compare Jobs?

Track your research progress by comparing gap analysis runs over time. See which gaps were filled, how completeness improved, and which papers contributed most.

### How to Compare

1. **Navigate to Jobs List**
2. **Click "Compare" button** (available when ≥2 jobs exist)
3. **Select Baseline Job** (earlier run)
4. **Select Comparison Job** (later run)
5. **Review Results:**
   - Completeness improvement (%)
   - Papers added/removed
   - Gaps filled
   - New gaps (if any)

### Interpreting Results

**Positive Delta (Green):** Completeness improved ✅  
**Negative Delta (Red):** Completeness decreased ⚠️ (possibly due to stricter criteria or removed papers)  
**Zero Delta (Gray):** No change

### Example Workflow

1. Run initial gap analysis with 10 papers → 60% complete
2. Add 5 more targeted papers
3. Re-run gap analysis → 75% complete
4. Compare runs → see which gaps were filled by new papers
5. Identify remaining gaps → target next paper search
```

---

## 🚀 Deployment Notes

### Configuration Changes

**No new dependencies required** (uses existing Chart.js/Plotly if available)

**Optional Configuration** (`pipeline_config.json`):
```json
{
  "comparison": {
    "max_jobs_in_dropdown": 50,
    "default_metric": "completeness",
    "enable_trend_chart": true
  }
}
```

### Database Schema (No Changes Required)

Uses existing job JSON structure. No migration needed.

---

## 🔗 Related Issues

- PR #39: Results Visualization API (foundation for this feature)
- Phase 4 Documentation: Results viewing already implemented
- Future: Multi-job trend analysis (compare 3+ jobs simultaneously)

---

## 📈 Success Metrics

**User Impact:**
- Researchers can track progress visually
- Identify which papers contribute most to gap coverage
- Make data-driven decisions on next papers to add

**Technical Metrics:**
- API response time: <500ms for comparison
- UI load time: <2s for rendering comparison
- Comparison accuracy: 100% (deterministic calculation)

---

## ✅ Definition of Done

- [ ] Backend `/api/compare-jobs` endpoint implemented
- [ ] Frontend comparison modal with job selectors
- [ ] Side-by-side completeness comparison
- [ ] Papers added/removed differential view
- [ ] Gaps filled visualization
- [ ] Unit tests (≥90% coverage)
- [ ] Integration tests (API endpoint)
- [ ] Documentation updated (DASHBOARD_GUIDE.md)
- [ ] Manual UI testing completed
- [ ] Code review approved
- [ ] Merged to main branch
