# ENHANCE-W3-2A: Dynamic Priority Adjustment for ROI Search Optimizer

**Status:** STATIC ROI CALCULATION  
**Priority:** 🟢 Low  
**Effort Estimate:** 3 hours  
**Category:** Enhancement Wave 3 - ROI Search Optimizer  
**Created:** November 17, 2025  
**Related PR:** #43 (ROI-based Search Optimization)

---

## 📋 Overview

Make ROI calculation adaptive by recalculating priorities after each search batch completes, deprioritizing searches that found sufficient papers and boosting searches for gaps still critical.

**Current Limitation:**
- ROI calculated once at start of job
- Doesn't update as searches complete
- May waste effort on already-covered gaps
- Misses opportunities to prioritize newly-critical gaps

**Proposed Enhancement:**
- Recalculate ROI after each search batch
- Deprioritize searches that found sufficient papers
- Boost searches for gaps still critical
- Adaptive search strategy

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Recalculate ROI after each search batch completes
- [ ] Update search queue dynamically (reorder pending searches)
- [ ] Skip searches for fully-covered gaps (>95% coverage)
- [ ] Log ROI adjustments in job metadata

### Should Have
- [ ] "Diminishing returns" detection (stop if next search ROI <threshold)
- [ ] Convergence criteria (stop when all critical gaps >80% covered)
- [ ] Visualization of ROI changes over time
- [ ] Configuration for recalculation frequency

### Nice to Have
- [ ] Predictive ROI (estimate future ROI based on past results)
- [ ] Multi-objective optimization (balance coverage vs cost vs time)
- [ ] User override (manual priority adjustment mid-job)

---

## 🛠️ Technical Implementation

### 1. Enhanced Search Optimizer

**Modified:** `literature_review/search_optimizer.py`

```python
class AdaptiveSearchOptimizer(SearchOptimizer):
    """Search optimizer with dynamic priority adjustment"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.recalculation_frequency = config.get('roi_optimizer', {}).get('recalculation_frequency', 'per_batch')
        self.min_roi_threshold = config.get('roi_optimizer', {}).get('min_roi_threshold', 0.1)
        self.convergence_threshold = config.get('roi_optimizer', {}).get('convergence_threshold', 0.8)
        
        self.roi_history = []  # Track ROI changes over time
    
    def optimize_searches_adaptive(self, gaps, initial_searches):
        """Run searches with adaptive ROI recalculation"""
        # Initial prioritization
        prioritized_searches = self.prioritize_searches(gaps, initial_searches)
        completed_searches = []
        search_results = []
        
        while prioritized_searches:
            # Execute next batch (top N searches)
            batch_size = self.config.get('roi_optimizer', {}).get('batch_size', 5)
            current_batch = prioritized_searches[:batch_size]
            
            # Run batch
            batch_results = self._execute_search_batch(current_batch)
            search_results.extend(batch_results)
            completed_searches.extend(current_batch)
            
            # Update gaps with new papers found
            self._update_gaps_with_results(gaps, batch_results)
            
            # Remove completed searches from queue
            prioritized_searches = prioritized_searches[batch_size:]
            
            # Recalculate ROI for remaining searches
            if prioritized_searches:
                prioritized_searches = self._recalculate_and_reorder(
                    gaps, 
                    prioritized_searches,
                    completed_searches
                )
                
                # Log ROI adjustment
                self._log_roi_adjustment(prioritized_searches)
                
                # Check convergence
                if self._check_convergence(gaps):
                    print("Convergence reached. Stopping search.")
                    break
                
                # Check diminishing returns
                if self._check_diminishing_returns(prioritized_searches):
                    print("Diminishing returns detected. Stopping search.")
                    break
        
        return {
            'completed_searches': completed_searches,
            'search_results': search_results,
            'roi_history': self.roi_history,
            'gaps_final_coverage': self._calculate_gap_coverage(gaps),
            'convergence_reached': self._check_convergence(gaps)
        }
    
    def _recalculate_and_reorder(self, gaps, pending_searches, completed_searches):
        """Recalculate ROI for pending searches and reorder"""
        # Recalculate gap severity (may have changed after new papers)
        for gap in gaps:
            gap['current_coverage'] = self._calculate_coverage(gap)
            gap['severity'] = self._recalculate_severity(gap)
        
        # Recalculate ROI for pending searches
        for search in pending_searches:
            # Original ROI
            old_roi = search['roi']
            
            # Find gaps this search targets
            target_gaps = [g for g in gaps if g['id'] in search['target_gap_ids']]
            
            # Skip if all target gaps fully covered
            if all(g.get('current_coverage', 0) > 0.95 for g in target_gaps):
                search['roi'] = 0.0
                search['skip_reason'] = 'all_gaps_covered'
                continue
            
            # Recalculate based on current gap state
            max_severity = max([g['severity'] for g in target_gaps]) if target_gaps else 0
            expected_papers = search.get('expected_papers', 5)
            search_cost = search.get('cost', 1.0)
            
            new_roi = (max_severity * expected_papers) / max(search_cost, 0.1)
            search['roi'] = new_roi
            search['roi_delta'] = new_roi - old_roi
        
        # Filter out zero-ROI searches
        pending_searches = [s for s in pending_searches if s['roi'] > 0]
        
        # Re-sort by ROI
        pending_searches.sort(key=lambda x: x['roi'], reverse=True)
        
        # Record in history
        self.roi_history.append({
            'timestamp': datetime.now().isoformat(),
            'completed_count': len(completed_searches),
            'pending_count': len(pending_searches),
            'avg_roi': sum([s['roi'] for s in pending_searches]) / len(pending_searches) if pending_searches else 0,
            'top_search_roi': pending_searches[0]['roi'] if pending_searches else 0
        })
        
        return pending_searches
    
    def _update_gaps_with_results(self, gaps, search_results):
        """Update gap coverage based on new papers found"""
        for result in search_results:
            papers = result.get('papers', [])
            target_gap_ids = result.get('target_gap_ids', [])
            
            for gap_id in target_gap_ids:
                gap = next((g for g in gaps if g['id'] == gap_id), None)
                if gap:
                    # Add papers to gap's evidence
                    if 'evidence_papers' not in gap:
                        gap['evidence_papers'] = []
                    gap['evidence_papers'].extend(papers)
    
    def _calculate_coverage(self, gap):
        """Calculate current coverage for a gap"""
        papers = gap.get('evidence_papers', [])
        if not papers:
            return 0.0
        
        # Calculate max alignment score
        alignments = [self._align_paper_to_gap(paper, gap) for paper in papers]
        return max(alignments) if alignments else 0.0
    
    def _recalculate_severity(self, gap):
        """Recalculate gap severity based on current coverage"""
        base_severity = gap.get('base_severity', 5.0)  # Original severity
        current_coverage = gap.get('current_coverage', 0.0)
        
        # Reduce severity as coverage improves
        # Severity drops exponentially: fully covered gap = 0 severity
        adjusted_severity = base_severity * (1 - current_coverage)
        
        return adjusted_severity
    
    def _check_convergence(self, gaps):
        """Check if convergence criteria met"""
        critical_gaps = [g for g in gaps if g.get('base_severity', 0) >= 7]
        
        if not critical_gaps:
            return True  # No critical gaps
        
        # Check if all critical gaps are sufficiently covered
        covered_critical = [g for g in critical_gaps if g.get('current_coverage', 0) >= self.convergence_threshold]
        
        return len(covered_critical) == len(critical_gaps)
    
    def _check_diminishing_returns(self, pending_searches):
        """Check if next search has diminishing returns"""
        if not pending_searches:
            return True
        
        # Check if top search ROI below threshold
        top_roi = pending_searches[0]['roi']
        
        return top_roi < self.min_roi_threshold
    
    def _log_roi_adjustment(self, searches):
        """Log ROI adjustments for debugging"""
        print("\n=== ROI Recalculation ===")
        print(f"Pending Searches: {len(searches)}")
        
        if searches:
            print(f"Top 3 searches by ROI:")
            for i, search in enumerate(searches[:3]):
                delta_str = f" (Δ{search.get('roi_delta', 0):+.2f})" if 'roi_delta' in search else ""
                print(f"  {i+1}. {search['query']} - ROI: {search['roi']:.2f}{delta_str}")
```

### 2. Configuration

**Enhanced:** `pipeline_config.json`

```json
{
  "roi_optimizer": {
    "enabled": true,
    "adaptive_recalculation": true,  // NEW
    "recalculation_frequency": "per_batch",  // NEW: "per_batch" or "every_n_searches"
    "batch_size": 5,  // Execute 5 searches before recalculating
    "min_roi_threshold": 0.1,  // NEW: Stop if ROI drops below this
    "convergence_threshold": 0.8,  // NEW: Stop when critical gaps >80% covered
    "diminishing_returns_threshold": 0.5  // NEW: ROI must be >50% of initial avg
  }
}
```

### 3. Visualization

**New Endpoint:** `GET /api/jobs/<job_id>/roi-history`

```python
@app.route('/api/jobs/<job_id>/roi-history')
def get_roi_history(job_id):
    """Get ROI adjustment history for a job"""
    job_data = load_job_data(job_id)
    roi_history = job_data.get('roi_history', [])
    
    return jsonify({
        'job_id': job_id,
        'roi_history': roi_history,
        'total_adjustments': len(roi_history),
        'convergence_reached': job_data.get('convergence_reached', False)
    })
```

**Frontend Chart:**
```javascript
function renderROIHistoryChart(roiHistory) {
    const timestamps = roiHistory.map(h => h.timestamp);
    const avgROI = roiHistory.map(h => h.avg_roi);
    const topROI = roiHistory.map(h => h.top_search_roi);
    
    const trace1 = {
        x: timestamps,
        y: avgROI,
        mode: 'lines+markers',
        name: 'Average ROI',
        line: {color: 'blue'}
    };
    
    const trace2 = {
        x: timestamps,
        y: topROI,
        mode: 'lines+markers',
        name: 'Top Search ROI',
        line: {color: 'green'}
    };
    
    Plotly.newPlot('roi-history-chart', [trace1, trace2], {
        title: 'ROI Evolution During Job',
        xaxis: {title: 'Time'},
        yaxis: {title: 'ROI'},
        hovermode: 'x unified'
    });
}
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `tests/unit/test_adaptive_roi.py`

```python
def test_recalculate_roi_after_batch():
    """Test ROI recalculation after search batch"""
    gaps = [
        {'id': 'gap1', 'base_severity': 8, 'current_coverage': 0.5},  # Partially covered
        {'id': 'gap2', 'base_severity': 7, 'current_coverage': 0.0}   # Not covered
    ]
    
    searches = [
        {'query': 'search1', 'target_gap_ids': ['gap1'], 'roi': 5.0},
        {'query': 'search2', 'target_gap_ids': ['gap2'], 'roi': 4.0}
    ]
    
    optimizer = AdaptiveSearchOptimizer()
    reordered = optimizer._recalculate_and_reorder(gaps, searches, [])
    
    # gap2 search should have higher ROI now (gap1 partially covered)
    assert reordered[0]['query'] == 'search2'

def test_skip_fully_covered_gaps():
    """Test skipping searches for fully covered gaps"""
    gaps = [
        {'id': 'gap1', 'base_severity': 8, 'current_coverage': 0.98}  # Fully covered
    ]
    
    searches = [
        {'query': 'search1', 'target_gap_ids': ['gap1'], 'roi': 5.0}
    ]
    
    optimizer = AdaptiveSearchOptimizer()
    reordered = optimizer._recalculate_and_reorder(gaps, searches, [])
    
    # Search should be skipped (ROI = 0)
    assert len(reordered) == 0 or reordered[0]['roi'] == 0.0

def test_convergence_detection():
    """Test convergence criteria"""
    gaps = [
        {'id': 'gap1', 'base_severity': 8, 'current_coverage': 0.85},  # Critical & covered
        {'id': 'gap2', 'base_severity': 9, 'current_coverage': 0.90}   # Critical & covered
    ]
    
    optimizer = AdaptiveSearchOptimizer({'roi_optimizer': {'convergence_threshold': 0.8}})
    converged = optimizer._check_convergence(gaps)
    
    assert converged is True

def test_diminishing_returns():
    """Test diminishing returns detection"""
    searches = [
        {'query': 'search1', 'roi': 0.05}  # Very low ROI
    ]
    
    optimizer = AdaptiveSearchOptimizer({'roi_optimizer': {'min_roi_threshold': 0.1}})
    diminishing = optimizer._check_diminishing_returns(searches)
    
    assert diminishing is True
```

---

## 📚 Documentation Updates

**File:** `docs/SEARCH_OPTIMIZATION_GUIDE.md`

**New Section:**
```markdown
## Adaptive ROI Recalculation

### How It Works

Instead of calculating ROI once at the start, the optimizer continuously adjusts priorities:

**Workflow:**
1. Calculate initial ROI for all searches
2. Execute top 5 searches (batch)
3. Update gap coverage based on papers found
4. **Recalculate ROI** for remaining searches
5. Re-prioritize search queue
6. Repeat until convergence or diminishing returns

### Example

```
Initial State:
  Gap 1 (severity 8, coverage 0%) → Search A (ROI 5.0)
  Gap 2 (severity 7, coverage 0%) → Search B (ROI 4.5)

After Search A completes:
  Gap 1 (severity 8, coverage 70%) → ROI reduced to 2.0
  Gap 2 (severity 7, coverage 0%) → ROI stays 4.5
  
Priority changes: Search B now first!
```

### Configuration

```json
{
  "roi_optimizer": {
    "adaptive_recalculation": true,
    "batch_size": 5,
    "min_roi_threshold": 0.1,
    "convergence_threshold": 0.8
  }
}
```

### When to Use

**Enable Adaptive ROI if:**
- Large search queue (>20 searches)
- Want to minimize wasted effort
- Critical gaps must be covered ASAP

**Disable if:**
- Small search queue (<10 searches)
- Want to execute all searches regardless
- Deterministic execution preferred
```

---

## ✅ Definition of Done

- [ ] `AdaptiveSearchOptimizer` class implemented
- [ ] ROI recalculation after each batch
- [ ] Skip fully-covered gaps
- [ ] Convergence detection
- [ ] Diminishing returns detection
- [ ] ROI history tracking
- [ ] Frontend ROI history chart
- [ ] Unit tests (≥90% coverage)
- [ ] Documentation updated
- [ ] Code review approved
- [ ] Merged to main branch
