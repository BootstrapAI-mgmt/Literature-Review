"""Unit tests for search optimization."""

import pytest
import json
import tempfile
from pathlib import Path
from literature_review.optimization.search_optimizer import SearchOptimizer


@pytest.fixture
def sample_gap_data():
    return {
        "Pillar 1: Test Pillar": {
            "completeness": 40.0,
            "analysis": {
                "REQ-T1.1: Test Requirement Group": {
                    "Sub-1.1.1: High priority requirement": {
                        "completeness_percent": 10,
                        "gap_analysis": "Critical gap",
                        "confidence_level": "high",
                        "contributing_papers": [
                            {"filename": "paper1.pdf"}
                        ]
                    },
                    "Sub-1.1.2: Low priority requirement": {
                        "completeness_percent": 95,
                        "gap_analysis": "Well covered",
                        "confidence_level": "high",
                        "contributing_papers": [
                            {"filename": f"paper{i}.pdf"} for i in range(10)
                        ]
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_searches():
    return [
        {
            "pillar": "Pillar 1",
            "requirement": "High priority requirement",
            "current_completeness": 10,
            "priority": "CRITICAL",
            "urgency": 1,
            "gap_description": "Critical gap",
            "suggested_searches": [
                {
                    "query": 'scalable microservices AND "fault tolerance"',
                    "rationale": "Direct match",
                    "databases": ["Google Scholar"]
                }
            ]
        },
        {
            "pillar": "Pillar 1",
            "requirement": "Low priority requirement",
            "current_completeness": 95,
            "priority": "LOW",
            "urgency": 5,
            "gap_description": "Well covered",
            "suggested_searches": [
                {
                    "query": "api design",
                    "rationale": "General search",
                    "databases": ["Google Scholar"]
                }
            ]
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
    critical_search = next((s for s in plan['search_plan'] 
                           if 'High priority' in s['requirement']), None)
    low_search = next((s for s in plan['search_plan'] 
                      if 'Low priority' in s['requirement']), None)
    
    assert critical_search is not None, "Critical search not found"
    assert low_search is not None, "Low priority search not found"
    assert critical_search['roi_score'] > low_search['roi_score'], \
        f"Critical ROI {critical_search['roi_score']} should be > Low ROI {low_search['roi_score']}"


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
        assert search['priority'] in ['HIGH', 'MEDIUM', 'LOW'], \
            f"Invalid priority: {search['priority']}"


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
    first_query = plan['execution_order'][0] if plan['execution_order'] else ''
    assert "microservices" in first_query.lower() or "fault tolerance" in first_query.lower(), \
        f"First query should be from high-priority requirement, got: {first_query}"


def test_gap_severity_mapping(tmp_path, sample_gap_data, sample_searches):
    """Test gap severity is correctly mapped from completeness."""
    gap_file = tmp_path / "gap.json"
    searches_file = tmp_path / "searches.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    with open(searches_file, 'w') as f:
        json.dump(sample_searches, f)
    
    optimizer = SearchOptimizer(str(gap_file), str(searches_file))
    plan = optimizer.optimize_search_plan()
    
    # Check gap severity assignments
    for search in plan['search_plan']:
        assert search['gap_severity'] in ['Critical', 'High', 'Medium', 'Low', 'Covered'], \
            f"Invalid gap severity: {search['gap_severity']}"


def test_papers_needed_calculation(tmp_path, sample_gap_data, sample_searches):
    """Test papers_needed is calculated correctly."""
    gap_file = tmp_path / "gap.json"
    searches_file = tmp_path / "searches.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    with open(searches_file, 'w') as f:
        json.dump(sample_searches, f)
    
    optimizer = SearchOptimizer(str(gap_file), str(searches_file))
    plan = optimizer.optimize_search_plan()
    
    # High priority requirement has 1 paper, should need 7 more (target 8)
    high_priority = next((s for s in plan['search_plan'] 
                         if 'High priority' in s['requirement']), None)
    assert high_priority is not None
    assert high_priority['papers_needed'] == 7, \
        f"Expected 7 papers needed, got {high_priority['papers_needed']}"


def test_output_structure(tmp_path, sample_gap_data, sample_searches):
    """Test output plan has correct structure."""
    gap_file = tmp_path / "gap.json"
    searches_file = tmp_path / "searches.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    with open(searches_file, 'w') as f:
        json.dump(sample_searches, f)
    
    optimizer = SearchOptimizer(str(gap_file), str(searches_file))
    plan = optimizer.optimize_search_plan()
    
    # Check required keys
    assert 'total_searches' in plan
    assert 'high_priority_searches' in plan
    assert 'search_plan' in plan
    assert 'execution_order' in plan
    
    # Check types
    assert isinstance(plan['total_searches'], int)
    assert isinstance(plan['high_priority_searches'], int)
    assert isinstance(plan['search_plan'], list)
    assert isinstance(plan['execution_order'], list)
    
    # Check search plan entries
    if plan['search_plan']:
        search = plan['search_plan'][0]
        assert 'query' in search
        assert 'requirement' in search
        assert 'pillar' in search
        assert 'roi_score' in search
        assert 'gap_severity' in search
        assert 'papers_needed' in search
        assert 'priority' in search
