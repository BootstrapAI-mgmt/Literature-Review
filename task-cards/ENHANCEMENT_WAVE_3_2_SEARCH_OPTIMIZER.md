# Task Card: ROI-Optimized Search Strategy

**Task ID:** ENHANCE-W3-2  
**Wave:** 3 (Automation & Optimization)  
**Priority:** LOW  
**Estimated Effort:** 10 hours  
**Status:** Not Started  
**Dependencies:** ENHANCE-W2-1 (Sufficiency Matrix)

---

## Objective

Rank search queries by expected ROI and prioritize high-value searches based on gap analysis.

## Background

From Enhanced Analysis Proposal: "Not all searches are equally valuable. Prioritize searches likely to fill critical gaps."

## Success Criteria

- [ ] Rank suggested searches by expected value
- [ ] Estimate papers needed per requirement
- [ ] Calculate search priority scores
- [ ] Generate optimized search plan
- [ ] Reduce wasted search effort by 30-50%

## Deliverables

### 1. Core Optimizer Module

**File:** `literature_review/optimization/search_optimizer.py`

```python
"""ROI-Optimized Search Strategy."""

import json
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class SearchOptimizer:
    """Optimize search strategy based on gap analysis."""
    
    def __init__(self, gap_analysis_file: str, suggested_searches_file: str):
        with open(gap_analysis_file, 'r') as f:
            self.gap_data = json.load(f)
        with open(suggested_searches_file, 'r') as f:
            self.searches = json.load(f)
    
    def optimize_search_plan(self) -> Dict:
        """Generate optimized search plan."""
        logger.info("Optimizing search strategy...")
        
        # Score each search query
        scored_searches = []
        
        for search in self.searches:
            req_id = search.get('requirement_id')
            pillar = search.get('pillar')
            
            # Get gap info
            gap_info = self._get_gap_info(req_id, pillar)
            
            if not gap_info:
                continue
            
            # Calculate ROI score
            roi_score = self._calculate_search_roi(search, gap_info)
            
            scored_searches.append({
                'query': search['query'],
                'requirement': search['requirement'],
                'pillar': pillar,
                'roi_score': roi_score,
                'gap_severity': gap_info['gap_severity'],
                'papers_needed': gap_info['papers_needed'],
                'priority': self._assign_priority(roi_score)
            })
        
        # Sort by ROI
        scored_searches.sort(key=lambda x: x['roi_score'], reverse=True)
        
        return {
            'total_searches': len(scored_searches),
            'high_priority_searches': len([s for s in scored_searches if s['priority'] == 'HIGH']),
            'search_plan': scored_searches,
            'execution_order': [s['query'] for s in scored_searches[:20]]  # Top 20
        }
    
    def _get_gap_info(self, req_id: str, pillar: str) -> Dict:
        """Get gap analysis info for requirement."""
        for p in self.gap_data['pillars']:
            if p['name'] == pillar:
                for r in p['requirements']:
                    if r['id'] == req_id:
                        papers_found = r['papers_found']
                        papers_needed = max(0, 8 - papers_found)  # Target 8 papers
                        
                        return {
                            'gap_severity': r['gap_severity'],
                            'papers_found': papers_found,
                            'papers_needed': papers_needed,
                            'avg_alignment': r.get('avg_alignment', 0.0)
                        }
        return {}
    
    def _calculate_search_roi(self, search: Dict, gap_info: Dict) -> float:
        """Calculate ROI score for a search query."""
        # Factors:
        # 1. Gap severity (Critical = 3, High = 2, Medium = 1, Low = 0.5)
        # 2. Papers needed (more needed = higher priority)
        # 3. Query specificity (more specific = higher success rate)
        
        severity_weights = {
            'Critical': 3.0,
            'High': 2.0,
            'Medium': 1.0,
            'Low': 0.5,
            'Covered': 0.1
        }
        
        severity_score = severity_weights.get(gap_info['gap_severity'], 1.0)
        papers_score = min(gap_info['papers_needed'] / 5.0, 1.0)  # Normalize to 0-1
        
        # Query specificity (count AND operators, quotes, etc.)
        query = search['query'].lower()
        specificity = 0.5
        if ' and ' in query or '"' in query:
            specificity = 0.8
        if len(query.split()) > 5:
            specificity = 0.9
        
        # Combined ROI score
        roi = severity_score * papers_score * specificity
        
        return round(roi, 2)
    
    def _assign_priority(self, roi_score: float) -> str:
        """Assign priority level."""
        if roi_score >= 2.0:
            return 'HIGH'
        elif roi_score >= 1.0:
            return 'MEDIUM'
        else:
            return 'LOW'


def generate_search_plan(gap_file: str, searches_file: str, output_file: str = 'gap_analysis_output/optimized_search_plan.json'):
    """Generate optimized search plan."""
    import os
    
    optimizer = SearchOptimizer(gap_file, searches_file)
    plan = optimizer.optimize_search_plan()
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(plan, f, indent=2)
    
    print("\n" + "="*60)
    print("OPTIMIZED SEARCH PLAN")
    print("="*60)
    print(f"\nTotal Searches: {plan['total_searches']}")
    print(f"High Priority: {plan['high_priority_searches']}")
    print(f"\nTop 10 Searches (Execute First):")
    for i, query in enumerate(plan['execution_order'][:10], 1):
        print(f"  {i}. {query}")
    print("\n" + "="*60)
    
    return plan
```

### 2. Integration with Gap Analysis

**File:** `DeepRequirementsAnalyzer.py` (additions)

```python
from literature_review.optimization.search_optimizer import generate_search_plan

class DeepRequirementsAnalyzer:
    def generate_outputs(self):
        """Generate all analysis outputs."""
        
        # ... existing outputs (suggested_searches.json) ...
        
        # NEW: Optimize search plan
        logger.info("Optimizing search strategy...")
        generate_search_plan(
            gap_file='gap_analysis_output/gap_analysis_report.json',
            searches_file='gap_analysis_output/suggested_searches.json',
            output_file='gap_analysis_output/optimized_search_plan.json'
        )
```

### 3. CLI Tool

**File:** `scripts/optimize_searches.py`

```python
#!/usr/bin/env python3
"""Optimize search query execution order based on ROI."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.optimization.search_optimizer import generate_search_plan
import argparse
import json


def main():
    parser = argparse.ArgumentParser(
        description='Generate ROI-optimized search plan'
    )
    parser.add_argument(
        '--gap-file',
        default='gap_analysis_output/gap_analysis_report.json',
        help='Path to gap analysis report'
    )
    parser.add_argument(
        '--searches-file',
        default='gap_analysis_output/suggested_searches.json',
        help='Path to suggested searches'
    )
    parser.add_argument(
        '--output',
        default='gap_analysis_output/optimized_search_plan.json',
        help='Output file for optimized plan'
    )
    parser.add_argument(
        '--top-n',
        type=int,
        default=20,
        help='Number of top searches to execute'
    )
    parser.add_argument(
        '--priority',
        choices=['HIGH', 'MEDIUM', 'LOW'],
        help='Filter by priority level'
    )
    
    args = parser.parse_args()
    
    # Generate plan
    print("Optimizing search strategy...")
    plan = generate_search_plan(
        gap_file=args.gap_file,
        searches_file=args.searches_file,
        output_file=args.output
    )
    
    # Filter by priority if specified
    if args.priority:
        filtered = [s for s in plan['search_plan'] if s['priority'] == args.priority]
        print(f"\n{args.priority} Priority Searches ({len(filtered)}):")
        for i, search in enumerate(filtered[:args.top_n], 1):
            print(f"  {i}. {search['query']}")
            print(f"     ROI: {search['roi_score']:.2f}, Gap: {search['gap_severity']}")
    else:
        print(f"\nTop {args.top_n} Searches (Highest ROI):")
        for i, query in enumerate(plan['execution_order'][:args.top_n], 1):
            search = next(s for s in plan['search_plan'] if s['query'] == query)
            print(f"  {i}. {query}")
            print(f"     ROI: {search['roi_score']:.2f}, Priority: {search['priority']}")
    
    print(f"\n✅ Optimized plan saved to: {args.output}")


if __name__ == '__main__':
    main()
```

## Testing Plan

### Unit Tests

**File:** `tests/unit/test_search_optimizer.py`

```python
"""Unit tests for search optimization."""

import pytest
import json
import tempfile
from literature_review.optimization.search_optimizer import SearchOptimizer


@pytest.fixture
def sample_gap_data():
    return {
        "pillars": [
            {
                "name": "Test Pillar",
                "requirements": [
                    {
                        "id": "P1-R1",
                        "requirement": "High priority requirement",
                        "gap_severity": "Critical",
                        "papers_found": 1,
                        "avg_alignment": 0.5
                    },
                    {
                        "id": "P1-R2",
                        "requirement": "Low priority requirement",
                        "gap_severity": "Low",
                        "papers_found": 10,
                        "avg_alignment": 0.8
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_searches():
    return [
        {
            "requirement_id": "P1-R1",
            "pillar": "Test Pillar",
            "requirement": "High priority requirement",
            "query": 'scalable microservices AND "fault tolerance"'
        },
        {
            "requirement_id": "P1-R2",
            "pillar": "Test Pillar",
            "requirement": "Low priority requirement",
            "query": "api design"
        }
    ]


def test_roi_calculation(tmp_path, sample_gap_data, sample_searches):
    """Test ROI score calculation."""
    gap_file = tmp_path / "gap.json"
    searches_file = tmp_path / "searches.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    with open(searches_file, 'w') as f:
        json.dump(sample_searches, f)
    
    optimizer = SearchOptimizer(str(gap_file), str(searches_file))
    plan = optimizer.optimize_search_plan()
    
    # Critical gap search should have higher ROI
    critical_search = next(s for s in plan['search_plan'] if s['requirement'].startswith('High'))
    low_search = next(s for s in plan['search_plan'] if s['requirement'].startswith('Low'))
    
    assert critical_search['roi_score'] > low_search['roi_score']


def test_priority_assignment(tmp_path, sample_gap_data, sample_searches):
    """Test priority level assignment."""
    gap_file = tmp_path / "gap.json"
    searches_file = tmp_path / "searches.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    with open(searches_file, 'w') as f:
        json.dump(sample_searches, f)
    
    optimizer = SearchOptimizer(str(gap_file), str(searches_file))
    plan = optimizer.optimize_search_plan()
    
    # Check priority levels exist
    for search in plan['search_plan']:
        assert search['priority'] in ['HIGH', 'MEDIUM', 'LOW']


def test_execution_order(tmp_path, sample_gap_data, sample_searches):
    """Test searches are ordered by ROI."""
    gap_file = tmp_path / "gap.json"
    searches_file = tmp_path / "searches.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    with open(searches_file, 'w') as f:
        json.dump(sample_searches, f)
    
    optimizer = SearchOptimizer(str(gap_file), str(searches_file))
    plan = optimizer.optimize_search_plan()
    
    # Execution order should prioritize critical gaps
    first_query = plan['execution_order'][0]
    assert "microservices" in first_query.lower() or "fault tolerance" in first_query.lower()
```

### Integration Tests

```bash
# Generate optimized search plan
python scripts/optimize_searches.py

# Check high priority searches
python scripts/optimize_searches.py --priority HIGH

# Get top 10 searches
python scripts/optimize_searches.py --top-n 10

# Verify output structure
cat gap_analysis_output/optimized_search_plan.json | jq '.execution_order | length'
cat gap_analysis_output/optimized_search_plan.json | jq '.high_priority_searches'
```

### Manual Testing

- [ ] Run optimizer with real gap analysis
- [ ] Verify critical gaps prioritized
- [ ] Check specificity scoring works
- [ ] Validate execution order makes sense
- [ ] Confirm papers_needed calculation

## Acceptance Criteria

- [ ] Searches ranked by ROI score (gap severity × papers needed × specificity)
- [ ] Priority levels assigned correctly (HIGH/MEDIUM/LOW)
- [ ] Execution order prioritizes critical gaps
- [ ] Reduces wasted effort on low-value searches
- [ ] Integrated seamlessly with gap analysis
- [ ] CLI tool provides filtering and top-N selection
- [ ] Query specificity affects ranking

---

**Created:** 2025-11-16  
**Assigned To:** TBD  
**Target Completion:** Wave 3 (Week 5-6)
