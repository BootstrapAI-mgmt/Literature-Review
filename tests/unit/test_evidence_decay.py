"""Unit tests for evidence decay tracker."""

import pytest
import json
import tempfile
from datetime import datetime
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.evidence_decay import EvidenceDecayTracker, generate_decay_report
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
def sample_version_history(tmp_path):
    """Create sample version history file."""
    version_data = {
        "paper1.pdf": [
            {
                "timestamp": "2024-01-01T00:00:00",
                "review": {
                    "TITLE": "Recent Paper",
                    "PUBLICATION_YEAR": 2024
                }
            }
        ],
        "paper2.pdf": [
            {
                "timestamp": "2024-01-01T00:00:00",
                "review": {
                    "TITLE": "Old Paper",
                    "PUBLICATION_YEAR": 2014
                }
            }
        ]
    }
    
    version_file = tmp_path / "review_version_history.json"
    with open(version_file, 'w') as f:
        json.dump(version_data, f)
    
    return str(version_file)


@pytest.fixture
def sample_gap_data(tmp_path):
    """Create sample gap analysis file."""
    gap_data = {
        "Test Pillar": {
            "completeness": 50.0,
            "analysis": {
                "REQ-1": {
                    "Sub-1.1": {
                        "completeness_percent": 70,
                        "gap_analysis": "Some gap",
                        "contributing_papers": [
                            {
                                "filename": "paper1.pdf",
                                "contribution_summary": "Recent contribution",
                                "estimated_contribution_percent": 80
                            },
                            {
                                "filename": "paper2.pdf",
                                "contribution_summary": "Old contribution",
                                "estimated_contribution_percent": 60
                            }
                        ]
                    }
                }
            }
        }
    }
    
    gap_file = tmp_path / "gap_analysis.json"
    with open(gap_file, 'w') as f:
        json.dump(gap_data, f)
    
    return str(gap_file)


@pytest.fixture
def sample_review_log(tmp_path):
    """Create sample review log file."""
    review_log = ["paper1.pdf", "paper2.pdf"]
    
    review_file = tmp_path / "review_log.json"
    with open(review_file, 'w') as f:
        json.dump(review_log, f)
    
    return str(review_file)


def test_freshness_analysis(tmp_path, sample_review_log, sample_gap_data, sample_version_history):
    """Test freshness metric calculation."""
    tracker = EvidenceDecayTracker(half_life_years=5.0)
    report = tracker.analyze_evidence_freshness(sample_review_log, sample_gap_data)
    
    assert 'requirement_analysis' in report
    assert 'Sub-1.1' in report['requirement_analysis']
    
    req_analysis = report['requirement_analysis']['Sub-1.1']
    assert 'avg_age_years' in req_analysis
    assert 'avg_decay_weight' in req_analysis
    assert 'freshness_score' in req_analysis
    assert req_analysis['paper_count'] == 2


def test_stale_evidence_detection(tmp_path, sample_review_log, sample_gap_data, sample_version_history):
    """Test detection of stale evidence."""
    tracker = EvidenceDecayTracker(half_life_years=5.0)
    report = tracker.analyze_evidence_freshness(sample_review_log, sample_gap_data)
    
    # With one 10-year-old paper and one current, avg weight should be calculated
    summary = report['summary']
    assert summary['total_requirements'] == 1
    assert 'needs_update_count' in summary
    assert summary['needs_update_count'] >= 0


def test_generate_decay_report(tmp_path, sample_review_log, sample_gap_data, sample_version_history, capsys):
    """Test report generation function."""
    output_file = tmp_path / "decay_report.json"
    
    report = generate_decay_report(
        review_log=sample_review_log,
        gap_analysis=sample_gap_data,
        output_file=str(output_file),
        half_life_years=5.0
    )
    
    # Check report was created
    assert output_file.exists()
    
    # Check report structure
    assert 'requirement_analysis' in report
    assert 'summary' in report
    
    # Check console output
    captured = capsys.readouterr()
    assert 'EVIDENCE DECAY ANALYSIS' in captured.out
    assert 'Summary:' in captured.out


def test_empty_gap_analysis(tmp_path):
    """Test handling of gap analysis with no contributing papers."""
    # Create empty gap analysis
    gap_data = {
        "Test Pillar": {
            "completeness": 0.0,
            "analysis": {
                "REQ-1": {
                    "Sub-1.1": {
                        "completeness_percent": 0,
                        "gap_analysis": "No papers",
                        "contributing_papers": []
                    }
                }
            }
        }
    }
    
    gap_file = tmp_path / "gap_analysis.json"
    with open(gap_file, 'w') as f:
        json.dump(gap_data, f)
    
    review_log = tmp_path / "review_log.json"
    with open(review_log, 'w') as f:
        json.dump([], f)
    
    tracker = EvidenceDecayTracker(half_life_years=5.0)
    report = tracker.analyze_evidence_freshness(str(review_log), str(gap_file))
    
    # Should handle gracefully
    assert report['summary']['total_requirements'] == 0


def test_missing_version_history(tmp_path):
    """Test handling when version history file is missing."""
    # Create gap analysis with papers
    gap_data = {
        "Test Pillar": {
            "completeness": 50.0,
            "analysis": {
                "REQ-1": {
                    "Sub-1.1": {
                        "completeness_percent": 70,
                        "contributing_papers": [
                            {
                                "filename": "paper1.pdf",
                                "estimated_contribution_percent": 80
                            }
                        ]
                    }
                }
            }
        }
    }
    
    gap_file = tmp_path / "gap_analysis.json"
    with open(gap_file, 'w') as f:
        json.dump(gap_data, f)
    
    review_log = tmp_path / "review_log.json"
    with open(review_log, 'w') as f:
        json.dump(["paper1.pdf"], f)
    
    # No version history file created
    tracker = EvidenceDecayTracker(half_life_years=5.0)
    report = tracker.analyze_evidence_freshness(str(review_log), str(gap_file))
    
    # Should use default year (current_year - 3)
    assert report['summary']['total_requirements'] == 1
    req_data = report['requirement_analysis']['Sub-1.1']
    assert req_data['paper_count'] == 1
    # Default is 3 years ago
    assert req_data['avg_age_years'] == 3.0
