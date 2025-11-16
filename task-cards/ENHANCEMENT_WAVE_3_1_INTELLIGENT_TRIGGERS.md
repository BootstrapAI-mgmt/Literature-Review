# Task Card: Deep Reviewer Intelligent Trigger System

**Task ID:** ENHANCE-W3-1  
**Wave:** 3 (Automation & Optimization)  
**Priority:** LOW  
**Estimated Effort:** 12 hours  
**Status:** Not Started  
**Dependencies:** ENHANCE-W1-1 (Manual Deep Review), ENHANCE-W2-1 (Sufficiency Matrix)

---

## Objective

Automate Deep Reviewer invocation based on intelligent triggers (3-metric system: gap severity, paper quality, ROI potential).

## Background

From Deep Reviewer Trigger Metrics proposal, simplified from 6 metrics to 3 essential metrics based on synthesis analysis.

## Success Criteria

- [ ] 3-metric trigger system implemented
- [ ] Automatically identifies high-value Deep Review candidates
- [ ] Prevents wasteful Deep Review on weak papers
- [ ] Logs trigger decisions for transparency
- [ ] 60-80% reduction in unnecessary Deep Review calls

## Deliverables

### File: `literature_review/triggers/deep_review_triggers.py`

```python
"""Intelligent Deep Reviewer Trigger System."""

import json
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class DeepReviewTriggerEngine:
    """Decide when to invoke Deep Reviewer based on 3 metrics."""
    
    THRESHOLDS = {
        'gap_severity': 0.7,      # Invoke if gap > 70%
        'paper_quality': 0.6,     # Invoke if quality > 60%
        'roi_potential': 5.0      # Invoke if ROI > 5 (hours saved / cost)
    }
    
    def __init__(self, gap_analysis_file: str, review_log_file: str):
        with open(gap_analysis_file, 'r') as f:
            self.gap_data = json.load(f)
        with open(review_log_file, 'r') as f:
            self.reviews = json.load(f)
    
    def evaluate_triggers(self) -> List[Dict]:
        """Evaluate which papers should trigger Deep Review."""
        candidates = []
        
        for paper_file, review in self.reviews.items():
            # Metric 1: Gap Severity (does this paper fill critical gaps?)
            gap_score = self._calculate_gap_impact(paper_file)
            
            # Metric 2: Paper Quality (is it worth deep analysis?)
            quality_score = review.get('judge_analysis', {}).get('overall_alignment', 0.0)
            
            # Metric 3: ROI Potential (time saved vs. cost)
            roi_score = self._calculate_roi(paper_file, gap_score, quality_score)
            
            # Decision: trigger if ANY metric exceeds threshold
            should_trigger = (
                gap_score > self.THRESHOLDS['gap_severity'] or
                quality_score > self.THRESHOLDS['paper_quality'] or
                roi_score > self.THRESHOLDS['roi_potential']
            )
            
            if should_trigger:
                candidates.append({
                    'paper': paper_file,
                    'title': review.get('metadata', {}).get('title', paper_file),
                    'gap_score': round(gap_score, 2),
                    'quality_score': round(quality_score, 2),
                    'roi_score': round(roi_score, 1),
                    'trigger_reason': self._get_trigger_reason(gap_score, quality_score, roi_score)
                })
        
        # Rank by combined score
        candidates.sort(key=lambda x: x['gap_score'] + x['quality_score'] + (x['roi_score'] / 10), reverse=True)
        
        return candidates
    
    def _calculate_gap_impact(self, paper_file: str) -> float:
        """Calculate how much this paper fills critical gaps."""
        # Simplified: check if it addresses high-severity gaps
        review = self.reviews.get(paper_file, {})
        judge = review.get('judge_analysis', {})
        
        critical_contributions = 0
        total_contributions = 0
        
        for pillar_contrib in judge.get('pillar_contributions', []):
            pillar_name = pillar_contrib['pillar_name']
            
            for sub_req in pillar_contrib.get('sub_requirements_addressed', []):
                total_contributions += 1
                
                # Check if this requirement has high gap severity
                req_gap = self._get_requirement_gap_severity(sub_req['requirement_id'], pillar_name)
                
                if req_gap in ['High', 'Critical']:
                    critical_contributions += 1
        
        return critical_contributions / max(total_contributions, 1)
    
    def _get_requirement_gap_severity(self, req_id: str, pillar: str) -> str:
        """Get gap severity for a requirement."""
        for p in self.gap_data['pillars']:
            if p['name'] == pillar:
                for r in p['requirements']:
                    if r['id'] == req_id:
                        return r.get('gap_severity', 'Unknown')
        return 'Unknown'
    
    def _calculate_roi(self, paper_file: str, gap_score: float, quality_score: float) -> float:
        """Estimate ROI of Deep Review (hours saved / cost)."""
        # Simplified: high-gap + high-quality = high ROI
        # Assume Deep Review costs $0.50, saves 2 hours if valuable
        
        potential_value = gap_score * quality_score * 2.0  # Hours potentially saved
        cost = 0.5  # Deep Review API cost estimate
        
        return potential_value / cost
    
    def _get_trigger_reason(self, gap_score: float, quality_score: float, roi_score: float) -> str:
        """Explain why trigger fired."""
        reasons = []
        
        if gap_score > self.THRESHOLDS['gap_severity']:
            reasons.append(f"Critical gap coverage ({gap_score:.0%})")
        if quality_score > self.THRESHOLDS['paper_quality']:
            reasons.append(f"High quality ({quality_score:.0%})")
        if roi_score > self.THRESHOLDS['roi_potential']:
            reasons.append(f"Strong ROI ({roi_score:.1f}x)")
        
        return ", ".join(reasons) if reasons else "Below threshold"


def generate_trigger_report(gap_file: str, review_log: str, output_file: str = 'deep_reviewer_cache/trigger_decisions.json'):
    """Generate trigger decision report."""
    import os
    
    engine = DeepReviewTriggerEngine(gap_file, review_log)
    candidates = engine.evaluate_triggers()
    
    report = {
        'total_papers': len(engine.reviews),
        'triggered_papers': len(candidates),
        'trigger_rate': round(len(candidates) / max(len(engine.reviews), 1), 2),
        'candidates': candidates
    }
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDeep Review Trigger Analysis:")
    print(f"  Total Papers: {report['total_papers']}")
    print(f"  Triggered: {report['triggered_papers']} ({report['trigger_rate']:.0%})")
    print(f"\nTop 5 Candidates:")
    for c in candidates[:5]:
        print(f"  - {c['title'][:60]}")
        print(f"    Reason: {c['trigger_reason']}")
    
    return report
```

### Integration

Add to `pipeline_orchestrator.py`:

```python
from literature_review.triggers.deep_review_triggers import generate_trigger_report

# After gap analysis
generate_trigger_report('gap_analysis_output/gap_analysis_report.json', 'review_log.json')
```

## Testing Plan

```bash
python -c "from literature_review.triggers.deep_review_triggers import generate_trigger_report; generate_trigger_report('gap_analysis_output/gap_analysis_report.json', 'review_log.json')"
```

## Acceptance Criteria

- [ ] 3-metric system works correctly
- [ ] Triggers 20-40% of papers (not all, not none)
- [ ] Prioritizes high-value papers
- [ ] Transparent decision logging
- [ ] Reduces Deep Review costs

---

**Created:** 2025-11-16  
**Assigned To:** TBD  
**Target Completion:** Wave 3 (Week 5-6)