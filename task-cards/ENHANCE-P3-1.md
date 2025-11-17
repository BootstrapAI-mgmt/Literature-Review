# ENHANCE-P3-1: Improve ETA Accuracy

**Status:** IMPLEMENTED BUT INACCURATE  
**Priority:** 🟢 Low  
**Effort Estimate:** 2 hours  
**Category:** Phase 3 - Progress Monitoring  
**Created:** November 17, 2025  
**Related PR:** #38 (Real-time Progress Monitoring)

---

## 📋 Overview

Improve ETA (Estimated Time to Arrival) accuracy by using historical stage durations and factoring in paper count/complexity instead of fixed estimates.

**Current Issues:**
- Uses hardcoded time estimates per stage (e.g., "deep review = 10 min")
- Doesn't account for paper count (10 papers vs 100 papers)
- No learning from past runs (first run has no calibration data)
- ETA often wrong by 2-5x actual time

**Impact:**
- Users can't trust ETA
- Poor planning (don't know when job will finish)
- Frustration with inaccurate estimates

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Track actual stage durations in job metadata
- [ ] Use historical averages for ETA calculation
- [ ] Factor in paper count (linear scaling: 2min/paper for deep review)
- [ ] Show confidence interval (e.g., "15-20 min remaining")

### Should Have
- [ ] Per-pillar ETA calibration (some pillars slower than others)
- [ ] Complexity scoring (PDF length, abstract quality affect time)
- [ ] Adaptive ETA (updates as job progresses)
- [ ] Display "learning" status ("First run, ETA may be inaccurate")

### Nice to Have
- [ ] User-specific calibration (different hardware = different speeds)
- [ ] API rate limit awareness (slower when rate-limited)
- [ ] Historical trend visualization (show ETA accuracy over time)

---

## 🛠️ Technical Implementation

### 1. Stage Duration Tracking

**Enhanced Job Metadata:** `workspace/job_<id>.json`

```json
{
  "id": "job_123",
  "status": "running",
  "progress": {
    "current_stage": "deep_review",
    "stages": {
      "gap_analysis": {
        "status": "completed",
        "start_time": "2025-11-17T10:00:00Z",
        "end_time": "2025-11-17T10:05:30Z",
        "duration_seconds": 330,
        "paper_count": 10
      },
      "deep_review": {
        "status": "running",
        "start_time": "2025-11-17T10:05:30Z",
        "end_time": null,
        "duration_seconds": null,
        "paper_count": 10
      }
    }
  }
}
```

**Backend Changes:** `webdashboard/job_runner.py`

```python
import time
from datetime import datetime, timezone

class JobRunner:
    def track_stage_duration(self, job_id: str, stage_name: str, action: str):
        """Track stage start/end times"""
        job_data = load_job_data(job_id)
        
        if 'progress' not in job_data:
            job_data['progress'] = {'stages': {}}
        
        stages = job_data['progress']['stages']
        
        if action == 'start':
            stages[stage_name] = {
                'status': 'running',
                'start_time': datetime.now(timezone.utc).isoformat(),
                'paper_count': len(job_data.get('papers', []))
            }
        
        elif action == 'end':
            stage = stages.get(stage_name, {})
            stage['status'] = 'completed'
            stage['end_time'] = datetime.now(timezone.utc).isoformat()
            
            # Calculate duration
            start = datetime.fromisoformat(stage['start_time'])
            end = datetime.fromisoformat(stage['end_time'])
            stage['duration_seconds'] = (end - start).total_seconds()
        
        save_job_data(job_id, job_data)
    
    async def run_job(self, job_id: str):
        """Run job with stage tracking"""
        # Gap Analysis
        self.track_stage_duration(job_id, 'gap_analysis', 'start')
        await run_gap_analysis(job_id)
        self.track_stage_duration(job_id, 'gap_analysis', 'end')
        
        # Deep Review
        self.track_stage_duration(job_id, 'deep_review', 'start')
        await run_deep_review(job_id)
        self.track_stage_duration(job_id, 'deep_review', 'end')
        
        # ... other stages
```

### 2. Historical ETA Calculator

**New Module:** `webdashboard/eta_calculator.py`

```python
from typing import Dict, Optional, Tuple
import statistics
import json
import os

class AdaptiveETACalculator:
    """Calculate ETA using historical data and paper count"""
    
    STAGE_ORDER = ['gap_analysis', 'deep_review', 'proof_generation', 'final_report']
    
    # Fallback estimates (used when no historical data)
    FALLBACK_ESTIMATES = {
        'gap_analysis': 30,  # seconds per paper
        'deep_review': 120,  # seconds per paper
        'proof_generation': 45,
        'final_report': 15
    }
    
    def __init__(self, history_file='workspace/eta_history.json'):
        self.history_file = history_file
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """Load historical stage durations"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_history(self):
        """Save historical data"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def record_stage_completion(self, stage_name: str, duration_seconds: float, paper_count: int):
        """Record completed stage for future ETA calculations"""
        if stage_name not in self.history:
            self.history[stage_name] = []
        
        # Store time per paper (normalizes for different paper counts)
        time_per_paper = duration_seconds / max(paper_count, 1)
        
        self.history[stage_name].append({
            'duration_seconds': duration_seconds,
            'paper_count': paper_count,
            'time_per_paper': time_per_paper,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Keep only last 50 runs per stage (prevent unbounded growth)
        if len(self.history[stage_name]) > 50:
            self.history[stage_name] = self.history[stage_name][-50:]
        
        self._save_history()
    
    def calculate_eta(self, current_stage: str, paper_count: int) -> Dict:
        """Calculate ETA for remaining stages"""
        current_index = self.STAGE_ORDER.index(current_stage)
        remaining_stages = self.STAGE_ORDER[current_index + 1:]
        
        total_eta_seconds = 0
        confidence = 'high'
        stage_etas = {}
        
        for stage in remaining_stages:
            eta, stage_confidence = self._estimate_stage_duration(stage, paper_count)
            stage_etas[stage] = eta
            total_eta_seconds += eta
            
            if stage_confidence == 'low':
                confidence = 'low'
            elif stage_confidence == 'medium' and confidence == 'high':
                confidence = 'medium'
        
        # Calculate confidence interval (±20% for low confidence)
        if confidence == 'low':
            min_eta = total_eta_seconds * 0.8
            max_eta = total_eta_seconds * 1.5
        elif confidence == 'medium':
            min_eta = total_eta_seconds * 0.9
            max_eta = total_eta_seconds * 1.2
        else:
            min_eta = total_eta_seconds * 0.95
            max_eta = total_eta_seconds * 1.05
        
        return {
            'total_eta_seconds': int(total_eta_seconds),
            'min_eta_seconds': int(min_eta),
            'max_eta_seconds': int(max_eta),
            'confidence': confidence,
            'stage_breakdown': stage_etas,
            'remaining_stages': remaining_stages
        }
    
    def _estimate_stage_duration(self, stage_name: str, paper_count: int) -> Tuple[float, str]:
        """Estimate duration for a stage"""
        historical_data = self.history.get(stage_name, [])
        
        if len(historical_data) >= 3:
            # Good historical data: use median time per paper
            times_per_paper = [d['time_per_paper'] for d in historical_data]
            median_time_per_paper = statistics.median(times_per_paper)
            estimated_duration = median_time_per_paper * paper_count
            
            # High confidence if we have 10+ data points
            confidence = 'high' if len(historical_data) >= 10 else 'medium'
            
            return estimated_duration, confidence
        
        elif len(historical_data) > 0:
            # Some data but not enough: blend with fallback
            avg_time_per_paper = statistics.mean([d['time_per_paper'] for d in historical_data])
            fallback_time_per_paper = self.FALLBACK_ESTIMATES.get(stage_name, 60)
            
            # Weighted average: 70% historical, 30% fallback
            blended_time_per_paper = (avg_time_per_paper * 0.7) + (fallback_time_per_paper * 0.3)
            estimated_duration = blended_time_per_paper * paper_count
            
            return estimated_duration, 'medium'
        
        else:
            # No historical data: use fallback
            fallback_time_per_paper = self.FALLBACK_ESTIMATES.get(stage_name, 60)
            estimated_duration = fallback_time_per_paper * paper_count
            
            return estimated_duration, 'low'
    
    def get_accuracy_report(self) -> Dict:
        """Generate report on ETA accuracy"""
        report = {}
        
        for stage, data in self.history.items():
            if len(data) < 2:
                continue
            
            times = [d['duration_seconds'] for d in data]
            times_per_paper = [d['time_per_paper'] for d in data]
            
            report[stage] = {
                'sample_size': len(data),
                'avg_duration': statistics.mean(times),
                'median_duration': statistics.median(times),
                'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
                'avg_time_per_paper': statistics.mean(times_per_paper),
                'min_duration': min(times),
                'max_duration': max(times)
            }
        
        return report
```

### 3. Frontend Integration

**Modified:** `webdashboard/templates/index.html`

```javascript
async function updateJobProgress(jobId) {
    const response = await fetch(`/api/jobs/${jobId}/progress`);
    const data = await response.json();
    
    // Display ETA with confidence interval
    const eta = data.eta;
    let etaDisplay = '';
    
    if (eta.confidence === 'high') {
        etaDisplay = `${formatDuration(eta.total_eta_seconds)} remaining`;
    } else if (eta.confidence === 'medium') {
        etaDisplay = `${formatDuration(eta.min_eta_seconds)}-${formatDuration(eta.max_eta_seconds)} remaining`;
    } else {
        etaDisplay = `~${formatDuration(eta.total_eta_seconds)} remaining (first run, estimate may vary)`;
    }
    
    document.getElementById('eta-display').innerHTML = `
        <div class="eta-container">
            <strong>ETA:</strong> ${etaDisplay}
            <span class="confidence-badge ${eta.confidence}">${eta.confidence} confidence</span>
        </div>
    `;
    
    // Show stage breakdown on hover
    const breakdown = eta.stage_breakdown;
    const breakdownHtml = Object.entries(breakdown)
        .map(([stage, duration]) => `<li>${stage}: ${formatDuration(duration)}</li>`)
        .join('');
    
    document.getElementById('eta-breakdown').innerHTML = `<ul>${breakdownHtml}</ul>`;
}

function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}min`;
    return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}min`;
}
```

**CSS:**
```css
.eta-container {
    display: flex;
    align-items: center;
    gap: 8px;
}

.confidence-badge {
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    text-transform: uppercase;
}

.confidence-badge.high {
    background-color: #d4edda;
    color: #155724;
}

.confidence-badge.medium {
    background-color: #fff3cd;
    color: #856404;
}

.confidence-badge.low {
    background-color: #f8d7da;
    color: #721c24;
}
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `tests/unit/test_eta_calculator.py`

```python
def test_eta_with_historical_data():
    """Test ETA calculation with good historical data"""
    calculator = AdaptiveETACalculator()
    
    # Mock historical data
    calculator.history = {
        'deep_review': [
            {'duration_seconds': 1200, 'paper_count': 10, 'time_per_paper': 120},
            {'duration_seconds': 2400, 'paper_count': 20, 'time_per_paper': 120},
            {'duration_seconds': 600, 'paper_count': 5, 'time_per_paper': 120}
        ]
    }
    
    eta = calculator.calculate_eta('gap_analysis', paper_count=10)
    
    assert eta['confidence'] == 'medium'  # 3 data points
    assert 1000 < eta['total_eta_seconds'] < 1500  # ~120s/paper * 10

def test_eta_fallback_no_history():
    """Test ETA falls back to estimates when no history"""
    calculator = AdaptiveETACalculator()
    calculator.history = {}  # No historical data
    
    eta = calculator.calculate_eta('gap_analysis', paper_count=10)
    
    assert eta['confidence'] == 'low'
    assert eta['total_eta_seconds'] > 0

def test_confidence_interval_calculation():
    """Test confidence interval width based on confidence level"""
    calculator = AdaptiveETACalculator()
    
    # High confidence: narrow interval (±5%)
    calculator.history = {
        'deep_review': [{'time_per_paper': 100} for _ in range(15)]
    }
    eta_high = calculator.calculate_eta('gap_analysis', 10)
    high_range = eta_high['max_eta_seconds'] - eta_high['min_eta_seconds']
    
    # Low confidence: wide interval (±30%)
    calculator.history = {}
    eta_low = calculator.calculate_eta('gap_analysis', 10)
    low_range = eta_low['max_eta_seconds'] - eta_low['min_eta_seconds']
    
    assert low_range > high_range * 3  # Low confidence has wider range

def test_record_stage_completion():
    """Test historical data recording"""
    calculator = AdaptiveETACalculator()
    
    calculator.record_stage_completion('gap_analysis', duration_seconds=300, paper_count=10)
    
    assert 'gap_analysis' in calculator.history
    assert len(calculator.history['gap_analysis']) == 1
    assert calculator.history['gap_analysis'][0]['time_per_paper'] == 30
```

---

## 📚 Documentation Updates

**File:** `docs/DASHBOARD_GUIDE.md`

```markdown
## Understanding ETA (Estimated Time of Arrival)

### How ETA is Calculated

The dashboard learns from past job runs to provide accurate ETAs:

**Factors Considered:**
- Historical stage durations (your past runs)
- Paper count (10 papers vs 100 papers)
- Current progress (how fast current job is running)

**Confidence Levels:**
- **High**: 10+ past runs, ETA accurate to ±5%
- **Medium**: 3-9 past runs, ETA accurate to ±10-20%
- **Low**: <3 past runs, ETA may vary significantly

### First Run

On your first job, the dashboard uses conservative estimates. After a few runs, ETAs become much more accurate.

**Example:**
```
First run: "~15 min remaining (low confidence)"
After 10 runs: "12-13 min remaining (high confidence)"
```

### ETA Breakdown

Hover over ETA to see per-stage breakdown:
- Gap Analysis: 2 min
- Deep Review: 8 min
- Proof Generation: 3 min
- Final Report: 1 min
```

---

## ✅ Definition of Done

- [ ] Stage duration tracking implemented in job_runner.py
- [ ] `AdaptiveETACalculator` class complete
- [ ] Historical data persistence (eta_history.json)
- [ ] Confidence interval calculation
- [ ] Frontend ETA display with confidence badge
- [ ] Unit tests (≥90% coverage)
- [ ] Documentation updated
- [ ] Code review approved
- [ ] Merged to main branch
