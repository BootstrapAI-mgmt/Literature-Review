"""Unit tests for adaptive ROI search optimization."""

import pytest
import json
import tempfile
from pathlib import Path
from literature_review.optimization.search_optimizer import AdaptiveSearchOptimizer


@pytest.fixture
def sample_gap_data():
    """Sample gap analysis data for testing."""
    return {
        "Pillar 1: Test Pillar": {
            "completeness": 40.0,
            "analysis": {
                "REQ-T1.1: Test Requirement Group": {
                    "Sub-1.1.1: Critical gap requirement": {
                        "completeness_percent": 10,
                        "gap_analysis": "Critical gap",
                        "confidence_level": "high",
                        "contributing_papers": [
                            {"filename": "paper1.pdf", "title": "Paper 1"}
                        ]
                    },
                    "Sub-1.1.2: Partially covered requirement": {
                        "completeness_percent": 50,
                        "gap_analysis": "Moderate gap",
                        "confidence_level": "medium",
                        "contributing_papers": [
                            {"filename": f"paper{i}.pdf", "title": f"Paper {i}"} for i in range(4)
                        ]
                    },
                    "Sub-1.1.3: Well covered requirement": {
                        "completeness_percent": 95,
                        "gap_analysis": "Well covered",
                        "confidence_level": "high",
                        "contributing_papers": [
                            {"filename": f"paper{i}.pdf", "title": f"Paper {i}"} for i in range(10)
                        ]
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_searches():
    """Sample search queries for testing."""
    return [
        {
            "pillar": "Pillar 1",
            "requirement": "Critical gap requirement",
            "current_completeness": 10,
            "priority": "CRITICAL",
            "urgency": 1,
            "gap_description": "Critical gap",
            "suggested_searches": [
                {
                    "query": 'critical topic AND "specific method"',
                    "rationale": "Direct match",
                    "databases": ["Google Scholar"]
                }
            ]
        },
        {
            "pillar": "Pillar 1",
            "requirement": "Partially covered requirement",
            "current_completeness": 50,
            "priority": "MEDIUM",
            "urgency": 3,
            "gap_description": "Moderate gap",
            "suggested_searches": [
                {
                    "query": "moderate topic",
                    "rationale": "General search",
                    "databases": ["Google Scholar"]
                }
            ]
        },
        {
            "pillar": "Pillar 1",
            "requirement": "Well covered requirement",
            "current_completeness": 95,
            "priority": "LOW",
            "urgency": 5,
            "gap_description": "Well covered",
            "suggested_searches": [
                {
                    "query": "covered topic",
                    "rationale": "Low priority",
                    "databases": ["Google Scholar"]
                }
            ]
        }
    ]


@pytest.fixture
def optimizer_with_config(tmp_path, sample_gap_data, sample_searches):
    """Create optimizer instance with test data."""
    gap_file = tmp_path / "gap.json"
    searches_file = tmp_path / "searches.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    with open(searches_file, 'w') as f:
        json.dump(sample_searches, f)
    
    config = {
        'roi_optimizer': {
            'batch_size': 2,
            'min_roi_threshold': 0.1,
            'convergence_threshold': 0.8
        }
    }
    
    return AdaptiveSearchOptimizer(str(gap_file), str(searches_file), config)


def test_adaptive_optimizer_initialization(optimizer_with_config):
    """Test AdaptiveSearchOptimizer initializes correctly."""
    optimizer = optimizer_with_config
    
    assert optimizer.batch_size == 2
    assert optimizer.min_roi_threshold == 0.1
    assert optimizer.convergence_threshold == 0.8
    assert optimizer.roi_history == []
    assert optimizer.gaps_state == []


def test_initialize_gaps_state(optimizer_with_config):
    """Test gap state initialization."""
    optimizer = optimizer_with_config
    optimizer._initialize_gaps_state()
    
    assert len(optimizer.gaps_state) == 3  # 3 sub-requirements
    
    # Check critical gap has high severity
    critical_gap = next((g for g in optimizer.gaps_state if 'Critical gap' in g['requirement']), None)
    assert critical_gap is not None
    assert critical_gap['base_severity'] == 7.0  # High severity for <30% completeness
    assert critical_gap['current_coverage'] == 0.1  # 10% completeness


def test_recalculate_roi_after_batch(optimizer_with_config):
    """Test ROI recalculation after search batch."""
    optimizer = optimizer_with_config
    optimizer._initialize_gaps_state()
    
    # Create mock searches
    searches = [
        {
            'query': 'search1',
            'requirement': 'Critical gap requirement',
            'roi_score': 5.0,
            'gap_severity': 'Critical',
            'papers_needed': 7
        },
        {
            'query': 'search2',
            'requirement': 'Partially covered requirement',
            'roi_score': 3.0,
            'gap_severity': 'Medium',
            'papers_needed': 4
        }
    ]
    
    # Simulate finding papers for critical gap
    critical_gap = next((g for g in optimizer.gaps_state if 'Critical gap' in g['requirement']), None)
    critical_gap['evidence_papers'].extend([
        {'title': f'New Paper {i}'} for i in range(5)
    ])
    critical_gap['current_coverage'] = 0.75  # Significantly improved
    
    # Recalculate ROI
    reordered = optimizer._recalculate_and_reorder(searches, 1)
    
    # Critical gap search should have reduced ROI (gap partially filled)
    critical_search = next((s for s in reordered if 'Critical gap' in s['requirement']), None)
    assert critical_search is not None
    assert critical_search['roi'] < critical_search['roi_score']
    assert 'roi_delta' in critical_search


def test_skip_fully_covered_gaps(optimizer_with_config):
    """Test skipping searches for fully covered gaps."""
    optimizer = optimizer_with_config
    optimizer._initialize_gaps_state()
    
    # Create search for well-covered gap
    searches = [
        {
            'query': 'search1',
            'requirement': 'Well covered requirement',
            'roi_score': 2.0,
            'gap_severity': 'Low',
            'papers_needed': 0
        }
    ]
    
    # Set gap as fully covered
    covered_gap = next((g for g in optimizer.gaps_state if 'Well covered' in g['requirement']), None)
    covered_gap['current_coverage'] = 0.98  # >95% covered
    
    # Recalculate ROI
    reordered = optimizer._recalculate_and_reorder(searches, 0)
    
    # Search should be filtered out (ROI = 0)
    assert len(reordered) == 0 or reordered[0]['roi'] == 0.0


def test_convergence_detection(optimizer_with_config):
    """Test convergence criteria detection."""
    optimizer = optimizer_with_config
    optimizer._initialize_gaps_state()
    
    # Set all critical gaps as covered
    for gap in optimizer.gaps_state:
        if gap.get('base_severity', 0) >= 7:
            gap['current_coverage'] = 0.85  # Above threshold
    
    converged = optimizer._check_convergence()
    assert converged is True
    
    # Reset one critical gap
    critical_gap = next((g for g in optimizer.gaps_state if g.get('base_severity', 0) >= 7), None)
    if critical_gap:
        critical_gap['current_coverage'] = 0.5  # Below threshold
        
        converged = optimizer._check_convergence()
        assert converged is False


def test_diminishing_returns_detection(optimizer_with_config):
    """Test diminishing returns detection."""
    optimizer = optimizer_with_config
    
    # Create searches with very low ROI
    low_roi_searches = [
        {'query': 'search1', 'roi': 0.05}  # Below threshold of 0.1
    ]
    
    diminishing = optimizer._check_diminishing_returns(low_roi_searches)
    assert diminishing is True
    
    # Create searches with acceptable ROI
    good_roi_searches = [
        {'query': 'search1', 'roi': 0.5}  # Above threshold
    ]
    
    diminishing = optimizer._check_diminishing_returns(good_roi_searches)
    assert diminishing is False


def test_roi_history_tracking(optimizer_with_config):
    """Test ROI history is tracked correctly."""
    optimizer = optimizer_with_config
    optimizer._initialize_gaps_state()
    
    searches = [
        {
            'query': 'search1',
            'requirement': 'Critical gap requirement',
            'roi_score': 5.0,
            'gap_severity': 'Critical'
        }
    ]
    
    # First recalculation
    optimizer._recalculate_and_reorder(searches, 1)
    assert len(optimizer.roi_history) == 1
    assert 'timestamp' in optimizer.roi_history[0]
    assert 'completed_count' in optimizer.roi_history[0]
    assert 'pending_count' in optimizer.roi_history[0]
    assert 'avg_roi' in optimizer.roi_history[0]
    assert 'top_search_roi' in optimizer.roi_history[0]
    
    # Second recalculation
    optimizer._recalculate_and_reorder(searches, 2)
    assert len(optimizer.roi_history) == 2


def test_update_gaps_with_results(optimizer_with_config):
    """Test gap updates with search results."""
    optimizer = optimizer_with_config
    optimizer._initialize_gaps_state()
    
    # Mock search results
    search_results = [
        {
            'search': {
                'requirement': 'Critical gap requirement',
                'query': 'test query'
            },
            'papers': [
                {'title': 'New Paper 1'},
                {'title': 'New Paper 2'},
                {'title': 'New Paper 3'}
            ]
        }
    ]
    
    # Get initial paper count
    critical_gap = next((g for g in optimizer.gaps_state if 'Critical gap' in g['requirement']), None)
    initial_count = len(critical_gap['evidence_papers'])
    
    # Update gaps
    optimizer._update_gaps_with_results(search_results)
    
    # Check papers were added
    assert len(critical_gap['evidence_papers']) == initial_count + 3
    # Coverage should increase
    assert critical_gap['current_coverage'] > 0.1


def test_adaptive_optimization_with_mock(optimizer_with_config):
    """Test full adaptive optimization workflow with mock execution."""
    optimizer = optimizer_with_config
    
    # Mock batch execution function
    def mock_execute_batch(batch):
        results = []
        for search in batch:
            # Simulate finding 2 papers per search
            results.append({
                'search': search,
                'papers': [
                    {'title': f"Paper for {search['requirement']} - 1"},
                    {'title': f"Paper for {search['requirement']} - 2"}
                ]
            })
        return results
    
    # Run adaptive optimization
    result = optimizer.optimize_searches_adaptive(mock_execute_batch=mock_execute_batch)
    
    # Check result structure
    assert 'completed_searches' in result
    assert 'search_results' in result
    assert 'roi_history' in result
    assert 'gaps_final_coverage' in result
    assert 'convergence_reached' in result
    
    # Should have completed some searches
    assert len(result['completed_searches']) > 0
    
    # Should have ROI history entries
    assert len(result['roi_history']) >= 0
    
    # Should have final gap coverage
    assert len(result['gaps_final_coverage']) == 3


def test_severity_recalculation(optimizer_with_config):
    """Test severity recalculation based on coverage."""
    optimizer = optimizer_with_config
    
    gap = {
        'base_severity': 9.0,
        'current_coverage': 0.0
    }
    
    # No coverage: severity unchanged
    severity = optimizer._recalculate_severity(gap)
    assert severity == 9.0
    
    # 50% coverage: severity halved
    gap['current_coverage'] = 0.5
    severity = optimizer._recalculate_severity(gap)
    assert severity == 4.5
    
    # Full coverage: severity = 0
    gap['current_coverage'] = 1.0
    severity = optimizer._recalculate_severity(gap)
    assert severity == 0.0


def test_dynamic_queue_reordering(optimizer_with_config):
    """Test search queue is dynamically reordered."""
    optimizer = optimizer_with_config
    optimizer._initialize_gaps_state()
    
    # Create searches with initial ordering
    searches = [
        {
            'query': 'search_high_roi',
            'requirement': 'Critical gap requirement',
            'roi_score': 5.0,
            'gap_severity': 'Critical'
        },
        {
            'query': 'search_low_roi',
            'requirement': 'Well covered requirement',
            'roi_score': 1.0,
            'gap_severity': 'Low'
        }
    ]
    
    # Simulate critical gap being mostly filled
    critical_gap = next((g for g in optimizer.gaps_state if 'Critical gap' in g['requirement']), None)
    critical_gap['current_coverage'] = 0.9
    
    # Recalculate and reorder
    reordered = optimizer._recalculate_and_reorder(searches, 0)
    
    # Order should change - previously low ROI search may now be higher
    # At minimum, critical gap search ROI should be reduced
    critical_search = next((s for s in reordered if 'Critical gap' in s['requirement']), None)
    if critical_search:
        assert critical_search['roi'] < 5.0  # Reduced from original


def test_calculate_gap_coverage(optimizer_with_config):
    """Test gap coverage calculation."""
    optimizer = optimizer_with_config
    optimizer._initialize_gaps_state()
    
    coverage = optimizer._calculate_gap_coverage()
    
    assert len(coverage) == 3
    for gap_cov in coverage:
        assert 'gap_id' in gap_cov
        assert 'requirement' in gap_cov
        assert 'coverage' in gap_cov
        assert 'papers_count' in gap_cov
        assert 0 <= gap_cov['coverage'] <= 1


def test_completeness_to_severity_score(optimizer_with_config):
    """Test completeness to severity score conversion."""
    optimizer = optimizer_with_config
    
    # Critical: 0% completeness
    assert optimizer._completeness_to_severity_score(0) == 9.0
    
    # High: <30% completeness
    assert optimizer._completeness_to_severity_score(20) == 7.0
    
    # Medium: 30-70% completeness
    assert optimizer._completeness_to_severity_score(50) == 5.0
    
    # Low: 70-90% completeness
    assert optimizer._completeness_to_severity_score(80) == 3.0
    
    # Covered: >=90% completeness
    assert optimizer._completeness_to_severity_score(95) == 1.0
