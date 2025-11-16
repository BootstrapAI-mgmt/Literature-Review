# Task Card: Evidence Decay Tracker

**Task ID:** ENHANCE-W3-4  
**Wave:** 3 (Automation & Optimization)  
**Priority:** LOW  
**Estimated Effort:** 5 hours  
**Status:** Not Started  
**Dependencies:** None

---

## Objective

Track temporal freshness of evidence and weight recent papers more heavily in gap analysis.

## Background

Strategic addition from synthesis: Evidence ages over time. A 2024 paper is more valuable than a 2018 paper for current research. Need temporal weighting in gap calculations.

## Success Criteria

- [ ] Calculate evidence decay scores based on publication year
- [ ] Apply temporal weights to gap analysis (exponential decay)
- [ ] Identify requirements with stale evidence
- [ ] Flag requirements needing updated searches
- [ ] Configurable decay rate (default: 5-year half-life)

## Deliverables

### File: `literature_review/utils/evidence_decay.py`

```python
"""Evidence Decay Tracker - temporal weighting of evidence."""

import json
from datetime import datetime
from typing import Dict, List
import math
import logging

logger = logging.getLogger(__name__)


class EvidenceDecayTracker:
    """Track and weight evidence based on publication age."""
    
    def __init__(self, half_life_years: float = 5.0):
        \"\"\"
        Initialize decay tracker.
        
        Args:
            half_life_years: Years for evidence value to decay to 50%
        \"\"\"
        self.half_life = half_life_years
        self.current_year = datetime.now().year
    
    def calculate_decay_weight(self, publication_year: int) -> float:
        \"\"\"
        Calculate decay weight for a paper.
        
        Uses exponential decay: weight = 2^(-age / half_life)
        
        Args:
            publication_year: Year of publication
        
        Returns:
            Decay weight (0-1, where 1 = current year)
        \"\"\"
        if publication_year > self.current_year:
            # Future publication (preprint?) - use current year
            publication_year = self.current_year
        
        age_years = self.current_year - publication_year
        
        # Exponential decay
        weight = math.pow(2, -age_years / self.half_life)
        
        return round(weight, 3)
    
    def analyze_evidence_freshness(self, review_log_file: str, gap_analysis_file: str) -> Dict:
        \"\"\"Analyze freshness of evidence for each requirement.\"\"\"
        logger.info(\"Analyzing evidence freshness...\")\n        \n        with open(review_log_file, 'r') as f:\n            reviews = json.load(f)\n        with open(gap_analysis_file, 'r') as f:\n            gap_data = json.load(f)\n        \n        # Analyze each requirement\n        freshness_analysis = {}\n        \n        for pillar in gap_data['pillars']:\n            pillar_name = pillar['name']\n            \n            for req in pillar['requirements']:\n                req_id = req['id']\n                \n                # Get contributing papers\n                papers = self._get_contributing_papers(req_id, pillar_name, reviews)\n                \n                if not papers:\n                    continue\n                \n                # Calculate freshness metrics\n                freshness = self._calculate_freshness_metrics(papers)\n                \n                freshness_analysis[req_id] = {\n                    'requirement': req['requirement'],\n                    'pillar': pillar_name,\n                    'paper_count': len(papers),\n                    'avg_age_years': freshness['avg_age'],\n                    'oldest_paper_year': freshness['oldest_year'],\n                    'newest_paper_year': freshness['newest_year'],\n                    'avg_decay_weight': freshness['avg_weight'],\n                    'freshness_score': freshness['freshness_score'],\n                    'needs_update': freshness['needs_update'],\n                    'papers': freshness['papers']\n                }\n        \n        return {\n            'analysis_date': datetime.now().isoformat(),\n            'current_year': self.current_year,\n            'half_life_years': self.half_life,\n            'requirement_analysis': freshness_analysis,\n            'summary': self._generate_summary(freshness_analysis)\n        }\n    \n    def _get_contributing_papers(self, req_id: str, pillar: str, reviews: Dict) -> List[Dict]:\n        \"\"\"Get papers contributing to a requirement with publication years.\"\"\"
        papers = []
        
        for paper_file, review in reviews.items():
            metadata = review.get('metadata', {})
            pub_year = metadata.get('publication_year', self.current_year - 3)  # Default to 3 years ago
            
            # Check if paper contributes to this requirement
            judge = review.get('judge_analysis', {})
            
            for pillar_contrib in judge.get('pillar_contributions', []):
                if pillar_contrib.get('pillar_name') == pillar:
                    for sub_req in pillar_contrib.get('sub_requirements_addressed', []):
                        if sub_req.get('requirement_id') == req_id:
                            papers.append({
                                'file': paper_file,
                                'title': metadata.get('title', paper_file),
                                'year': pub_year,
                                'alignment': sub_req.get('alignment_score', 0.0)
                            })
        
        return papers
    
    def _calculate_freshness_metrics(self, papers: List[Dict]) -> Dict:
        \"\"\"Calculate freshness metrics for a set of papers.\"\"\"
        if not papers:
            return {
                'avg_age': 0,
                'oldest_year': 0,
                'newest_year': 0,
                'avg_weight': 0,
                'freshness_score': 0,
                'needs_update': True,
                'papers': []
            }
        
        years = [p['year'] for p in papers]
        weights = [self.calculate_decay_weight(y) for y in years]
        
        avg_age = self.current_year - (sum(years) / len(years))
        avg_weight = sum(weights) / len(weights)
        
        # Freshness score: weighted average of alignment scores
        weighted_alignments = sum(p['alignment'] * self.calculate_decay_weight(p['year']) 
                                 for p in papers)
        total_weights = sum(self.calculate_decay_weight(p['year']) for p in papers)
        freshness_score = weighted_alignments / total_weights if total_weights > 0 else 0
        
        # Needs update if avg weight < 0.5 (evidence more than 1 half-life old)
        needs_update = avg_weight < 0.5
        
        # Add decay weights to papers
        papers_with_weights = [
            {
                **p,
                'decay_weight': self.calculate_decay_weight(p['year']),
                'age_years': self.current_year - p['year']
            }
            for p in papers
        ]
        
        return {
            'avg_age': round(avg_age, 1),
            'oldest_year': min(years),
            'newest_year': max(years),
            'avg_weight': round(avg_weight, 2),
            'freshness_score': round(freshness_score, 2),
            'needs_update': needs_update,
            'papers': papers_with_weights
        }
    
    def _generate_summary(self, freshness_analysis: Dict) -> Dict:
        \"\"\"Generate summary statistics.\"\"\"
        if not freshness_analysis:
            return {}
        
        needs_update = sum(1 for r in freshness_analysis.values() if r['needs_update'])
        avg_age = sum(r['avg_age_years'] for r in freshness_analysis.values()) / len(freshness_analysis)
        avg_freshness = sum(r['freshness_score'] for r in freshness_analysis.values()) / len(freshness_analysis)
        
        return {
            'total_requirements': len(freshness_analysis),
            'needs_update_count': needs_update,
            'avg_evidence_age_years': round(avg_age, 1),
            'avg_freshness_score': round(avg_freshness, 2)
        }


def generate_decay_report(review_log: str, gap_analysis: str, 
                         output_file: str = 'gap_analysis_output/evidence_decay.json'):\n    \"\"\"Generate evidence decay report.\"\"\"
    import os
    
    tracker = EvidenceDecayTracker(half_life_years=5.0)
    report = tracker.analyze_evidence_freshness(review_log, gap_analysis)
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(\"\\n\" + \"=\"*60)
    print(\"EVIDENCE DECAY ANALYSIS\")
    print(\"=\"*60)
    
    summary = report['summary']
    print(f\"\\nSummary:\")
    print(f\"  Requirements Analyzed: {summary['total_requirements']}\")
    print(f\"  Need Updated Searches: {summary['needs_update_count']}\")
    print(f\"  Avg Evidence Age: {summary['avg_evidence_age_years']} years\")
    print(f\"  Avg Freshness Score: {summary['avg_freshness_score']}\")
    
    print(f\"\\n⚠️ Requirements Needing Update (Top 5):\")
    stale = sorted(
        [(req_id, data) for req_id, data in report['requirement_analysis'].items() if data['needs_update']],
        key=lambda x: x[1]['avg_age_years'],
        reverse=True
    )
    for req_id, data in stale[:5]:
        print(f\"  {req_id}: {data['requirement'][:60]}...\")
        print(f\"    Avg Age: {data['avg_age_years']} years, Weight: {data['avg_decay_weight']}\")
    
    print(\"\\n\" + \"=\"*60)
    print(f\"Full report saved to: {output_file}\")
    print(\"=\"*60 + \"\\n\")
    
    return report
```

### Integration

Add to `DeepRequirementsAnalyzer.py`:

```python
from literature_review.utils.evidence_decay import generate_decay_report

# After gap analysis
generate_decay_report('review_log.json', 'gap_analysis_output/gap_analysis_report.json')
```

## Testing Plan

```bash
# Test decay calculation
python -c \"from literature_review.utils.evidence_decay import EvidenceDecayTracker; t = EvidenceDecayTracker(); print(t.calculate_decay_weight(2024), t.calculate_decay_weight(2019), t.calculate_decay_weight(2014))\"

# Generate report
python -c \"from literature_review.utils.evidence_decay import generate_decay_report; generate_decay_report('review_log.json', 'gap_analysis_output/gap_analysis_report.json')\"
```

## Acceptance Criteria

- [ ] Decay weights calculated correctly (exponential)
- [ ] Identifies requirements with stale evidence
- [ ] Temporal weighting applied to freshness scores
- [ ] Configurable half-life parameter
- [ ] Integrated with gap analysis
- [ ] Clear visualization of evidence age

## Configuration

Default: 5-year half-life (evidence loses 50% value every 5 years)

**File:** `pipeline_config.json` (additions)

```json
{
  "evidence_decay": {
    "enabled": true,
    "half_life_years": 5.0,
    "stale_threshold": 0.5,
    "weight_in_gap_analysis": true
  }
}
```

### 2. Weighted Gap Analysis Integration

**File:** `DeepRequirementsAnalyzer.py` (modifications)

```python
from literature_review.utils.evidence_decay import EvidenceDecayTracker

class DeepRequirementsAnalyzer:
    def __init__(self, config):
        # ... existing code ...
        self.decay_enabled = config.get('evidence_decay', {}).get('enabled', True)
        self.decay_tracker = EvidenceDecayTracker(
            half_life_years=config.get('evidence_decay', {}).get('half_life_years', 5.0)
        )
    
    def calculate_requirement_gap(self, pillar_name, requirement_id, contributing_papers):
        """
        Calculate gap severity with optional temporal weighting.
        
        Args:
            pillar_name: Name of pillar
            requirement_id: Requirement ID
            contributing_papers: List of papers with metadata
        
        Returns:
            Gap analysis with temporal weighting
        """
        # Standard gap calculation
        paper_count = len(contributing_papers)
        avg_alignment = sum(p['alignment'] for p in contributing_papers) / max(paper_count, 1)
        
        if self.decay_enabled:
            # Apply temporal weighting
            weighted_alignments = 0
            total_weights = 0
            
            for paper in contributing_papers:
                pub_year = paper.get('publication_year', datetime.now().year - 3)
                decay_weight = self.decay_tracker.calculate_decay_weight(pub_year)
                
                weighted_alignments += paper['alignment'] * decay_weight
                total_weights += decay_weight
            
            # Weighted average alignment
            temporal_alignment = weighted_alignments / max(total_weights, 1) if total_weights > 0 else 0
            
            logger.debug(f"{requirement_id}: Standard avg={avg_alignment:.2f}, Temporal avg={temporal_alignment:.2f}")
            
            # Use temporal alignment for gap severity
            avg_alignment = temporal_alignment
        
        # Calculate gap severity based on alignment
        if avg_alignment >= 0.8:
            gap_severity = 'Covered'
        elif avg_alignment >= 0.6:
            gap_severity = 'Low'
        elif avg_alignment >= 0.4:
            gap_severity = 'Medium'
        elif avg_alignment >= 0.2:
            gap_severity = 'High'
        else:
            gap_severity = 'Critical'
        
        return {
            'papers_found': paper_count,
            'avg_alignment': round(avg_alignment, 2),
            'gap_severity': gap_severity
        }
```

### 3. CLI Tool Enhancement

**File:** `scripts/analyze_evidence_decay.py`

```python
#!/usr/bin/env python3
"""Analyze evidence freshness and temporal decay."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.utils.evidence_decay import generate_decay_report, EvidenceDecayTracker
import argparse
import json


def main():
    parser = argparse.ArgumentParser(
        description='Analyze evidence decay and freshness'
    )
    parser.add_argument(
        '--review-log',
        default='review_log.json',
        help='Path to review log'
    )
    parser.add_argument(
        '--gap-analysis',
        default='gap_analysis_output/gap_analysis_report.json',
        help='Path to gap analysis'
    )
    parser.add_argument(
        '--output',
        default='gap_analysis_output/evidence_decay.json',
        help='Output file'
    )
    parser.add_argument(
        '--half-life',
        type=float,
        default=5.0,
        help='Half-life in years (default: 5.0)'
    )
    parser.add_argument(
        '--show-weights',
        action='store_true',
        help='Show decay weights for each year'
    )
    
    args = parser.parse_args()
    
    if args.show_weights:
        print("\nDecay Weight Table (Half-life: {:.1f} years)".format(args.half_life))
        print("=" * 50)
        print(f"{'Year':<10} {'Age':<10} {'Weight':<10}")
        print("=" * 50)
        
        tracker = EvidenceDecayTracker(half_life_years=args.half_life)
        for year in range(tracker.current_year, tracker.current_year - 15, -1):
            weight = tracker.calculate_decay_weight(year)
            age = tracker.current_year - year
            print(f"{year:<10} {age:<10} {weight:.3f}")
        
        print("=" * 50 + "\n")
    
    # Generate report
    print("Analyzing evidence decay...")
    report = generate_decay_report(
        review_log=args.review_log,
        gap_analysis=args.gap_analysis,
        output_file=args.output
    )
    
    print(f"\n✅ Analysis complete!")
    print(f"   Report: {args.output}")


if __name__ == '__main__':
    main()
```

## Testing Plan

### Unit Tests

**File:** `tests/unit/test_evidence_decay.py`

```python
"""Unit tests for evidence decay tracker."""

import pytest
import json
import tempfile
from datetime import datetime
from literature_review.utils.evidence_decay import EvidenceDecayTracker
import math


def test_decay_weight_calculation():
    """Test exponential decay weight calculation."""
    tracker = EvidenceDecayTracker(half_life_years=5.0)
    current_year = tracker.current_year
    
    # Current year should be weight 1.0
    assert tracker.calculate_decay_weight(current_year) == 1.0
    
    # Half-life year should be weight 0.5
    half_life_year = current_year - 5
    weight = tracker.calculate_decay_weight(half_life_year)
    assert abs(weight - 0.5) < 0.001
    
    # 10 years old (2 half-lives) should be weight 0.25
    old_year = current_year - 10
    weight = tracker.calculate_decay_weight(old_year)
    assert abs(weight - 0.25) < 0.001


def test_future_year_handling():
    """Test handling of future publication years."""
    tracker = EvidenceDecayTracker()
    current_year = tracker.current_year
    
    # Future year should be treated as current year
    future_weight = tracker.calculate_decay_weight(current_year + 1)
    current_weight = tracker.calculate_decay_weight(current_year)
    
    assert future_weight == current_weight == 1.0


def test_configurable_half_life():
    """Test different half-life configurations."""
    # 3-year half-life
    tracker_fast = EvidenceDecayTracker(half_life_years=3.0)
    weight_3y = tracker_fast.calculate_decay_weight(tracker_fast.current_year - 3)
    
    # 10-year half-life
    tracker_slow = EvidenceDecayTracker(half_life_years=10.0)
    weight_10y = tracker_slow.calculate_decay_weight(tracker_slow.current_year - 10)
    
    # Both should be approximately 0.5 at their respective half-lives
    assert abs(weight_3y - 0.5) < 0.001
    assert abs(weight_10y - 0.5) < 0.001


@pytest.fixture
def sample_review_log():
    return {
        "paper1.json": {
            "metadata": {
                "title": "Recent Paper",
                "publication_year": 2024
            },
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "alignment_score": 0.8
                            }
                        ]
                    }
                ]
            }
        },
        "paper2.json": {
            "metadata": {
                "title": "Old Paper",
                "publication_year": 2014  # 10 years old
            },
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "alignment_score": 0.8
                            }
                        ]
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_gap_data():
    return {
        "pillars": [
            {
                "name": "Test Pillar",
                "requirements": [
                    {
                        "id": "P1-R1",
                        "requirement": "Test requirement",
                        "papers_found": 2
                    }
                ]
            }
        ]
    }


def test_freshness_analysis(tmp_path, sample_review_log, sample_gap_data):
    """Test freshness metric calculation."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"
    
    with open(review_file, 'w') as f:
        json.dump(sample_review_log, f)
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    tracker = EvidenceDecayTracker(half_life_years=5.0)
    report = tracker.analyze_evidence_freshness(str(review_file), str(gap_file))
    
    assert 'requirement_analysis' in report
    assert 'P1-R1' in report['requirement_analysis']
    
    req_analysis = report['requirement_analysis']['P1-R1']
    assert 'avg_age_years' in req_analysis
    assert 'avg_decay_weight' in req_analysis
    assert 'freshness_score' in req_analysis


def test_stale_evidence_detection(tmp_path, sample_review_log, sample_gap_data):
    """Test detection of stale evidence."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"
    
    with open(review_file, 'w') as f:
        json.dump(sample_review_log, f)
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    tracker = EvidenceDecayTracker(half_life_years=5.0)
    report = tracker.analyze_evidence_freshness(str(review_file), str(gap_file))
    
    # With one 10-year-old paper, avg weight should be < 0.5
    # This should trigger needs_update flag
    summary = report['summary']
    assert summary['needs_update_count'] >= 0
```

### Integration Tests

```bash
# Show decay weight table
python scripts/analyze_evidence_decay.py --show-weights

# Different half-life
python scripts/analyze_evidence_decay.py --half-life 3.0 --show-weights

# Generate full report
python scripts/analyze_evidence_decay.py

# Verify stale requirements detected
cat gap_analysis_output/evidence_decay.json | jq '.summary.needs_update_count'

# Check freshness scores
cat gap_analysis_output/evidence_decay.json | jq '.requirement_analysis[] | select(.needs_update == true) | .requirement'
```

## Acceptance Criteria

- [ ] Decay weights calculated correctly using exponential decay
- [ ] Identifies requirements with stale evidence (avg weight < 50%)
- [ ] Temporal weighting applied to gap analysis calculations
- [ ] Configurable half-life parameter (default 5 years)
- [ ] Integrated with gap analysis pipeline
- [ ] Clear visualization of evidence age distribution
- [ ] CLI tool shows decay weight table
- [ ] Handles missing publication years gracefully
- [ ] Future dates treated as current year
- [ ] Summary statistics accurate

## Notes

### Decay Model

**Formula:** `weight = 2^(-age / half_life)`

**Examples (5-year half-life):**
- 0 years old: 100% weight
- 2.5 years old: 70.7% weight
- 5 years old: 50% weight
- 10 years old: 25% weight
- 15 years old: 12.5% weight

### Field-Specific Half-Lives

Different research fields age at different rates:

- **Computer Science / AI:** 3-4 years (fast-moving)
- **Engineering:** 5-7 years (moderate)
- **Mathematics:** 10+ years (slow-moving)
- **Medical:** 5 years (moderate, guidelines-driven)

Adjust `half_life_years` parameter accordingly.

### Impact on Gap Analysis

When `weight_in_gap_analysis` is enabled:

1. Alignment scores are weighted by publication age
2. Older papers contribute less to coverage
3. Gap severity may increase if evidence is stale
4. Encourages refreshing evidence with recent papers

### Default Behavior

- Papers without `publication_year`: Default to 3 years ago
- Future years (preprints): Treated as current year
- Threshold for "needs update": avg_weight < 0.5 (configurable)

---

**Created:** 2025-11-16  
**Assigned To:** TBD  
**Target Completion:** Wave 3 (Week 5-6)
