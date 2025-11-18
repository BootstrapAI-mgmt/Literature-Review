"""Unit tests for evidence decay integration with gap analysis."""

import pytest
import json
import tempfile
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis.gap_analyzer import GapAnalyzer, load_config
from literature_review.utils.evidence_decay import EvidenceDecayTracker


@pytest.fixture
def config_no_decay():
    """Configuration with decay disabled."""
    return {
        'evidence_decay': {
            'enabled': True,
            'half_life_years': 5.0,
            'weight_in_gap_analysis': False,
            'decay_weight': 0.7,
            'apply_to_pillars': ['all'],
            'min_freshness_threshold': 0.3
        }
    }


@pytest.fixture
def config_with_decay():
    """Configuration with decay enabled."""
    return {
        'evidence_decay': {
            'enabled': True,
            'half_life_years': 5.0,
            'weight_in_gap_analysis': True,
            'decay_weight': 0.7,
            'apply_to_pillars': ['all'],
            'min_freshness_threshold': 0.3
        }
    }


@pytest.fixture
def config_full_decay():
    """Configuration with full decay weight (1.0)."""
    return {
        'evidence_decay': {
            'enabled': True,
            'half_life_years': 5.0,
            'weight_in_gap_analysis': True,
            'decay_weight': 1.0,
            'apply_to_pillars': ['all'],
            'min_freshness_threshold': 0.3
        }
    }


@pytest.fixture
def config_partial_decay():
    """Configuration with partial decay weight (0.5)."""
    return {
        'evidence_decay': {
            'enabled': True,
            'half_life_years': 5.0,
            'weight_in_gap_analysis': True,
            'decay_weight': 0.5,
            'apply_to_pillars': ['all'],
            'min_freshness_threshold': 0.3
        }
    }


@pytest.fixture
def sample_version_history():
    """Sample version history for testing."""
    from datetime import datetime
    current_year = datetime.now().year
    
    return {
        "old_paper.pdf": [
            {
                "timestamp": "2024-01-01T00:00:00",
                "review": {
                    "TITLE": "Old Paper",
                    "PUBLICATION_YEAR": current_year - 10
                }
            }
        ],
        "recent_paper.pdf": [
            {
                "timestamp": "2024-01-01T00:00:00",
                "review": {
                    "TITLE": "Recent Paper",
                    "PUBLICATION_YEAR": current_year - 1
                }
            }
        ]
    }


def test_gap_analyzer_initialization_no_decay(config_no_decay):
    """Test GapAnalyzer initialization with decay disabled."""
    analyzer = GapAnalyzer(config=config_no_decay)
    
    assert analyzer.decay_enabled is False
    assert analyzer.decay_tracker is None


def test_gap_analyzer_initialization_with_decay(config_with_decay):
    """Test GapAnalyzer initialization with decay enabled."""
    analyzer = GapAnalyzer(config=config_with_decay)
    
    assert analyzer.decay_enabled is True
    assert analyzer.decay_tracker is not None
    assert analyzer.decay_weight == 0.7


def test_apply_decay_weighting_disabled(config_no_decay):
    """Test that decay weighting is not applied when disabled."""
    analyzer = GapAnalyzer(config=config_no_decay)
    
    raw_score = 80.0
    papers = [
        {
            'filename': 'old_paper.pdf',
            'contribution_summary': 'Main contribution',
            'estimated_contribution_percent': 80,
            'year': 2015
        }
    ]
    
    final_score, metadata = analyzer.apply_decay_weighting(raw_score, papers)
    
    assert final_score == raw_score
    assert metadata['decay_applied'] is False
    assert metadata['raw_score'] == raw_score
    assert metadata['final_score'] == raw_score


def test_apply_decay_weighting_enabled_old_paper(config_with_decay, sample_version_history):
    """Test decay weighting reduces score for old papers."""
    from datetime import datetime
    analyzer = GapAnalyzer(config=config_with_decay)
    
    current_year = datetime.now().year
    raw_score = 80.0
    papers = [
        {
            'filename': 'old_paper.pdf',
            'contribution_summary': 'Main contribution',
            'estimated_contribution_percent': 80,
            'year': current_year - 10  # 10 years old
        }
    ]
    
    final_score, metadata = analyzer.apply_decay_weighting(
        raw_score, papers, version_history=sample_version_history
    )
    
    # Score should be reduced
    assert final_score < raw_score
    assert metadata['decay_applied'] is True
    assert metadata['raw_score'] == raw_score
    assert 'freshness_score' in metadata
    # 10 years old with 5-year half-life: freshness ~0.25
    assert metadata['freshness_score'] < 0.3


def test_apply_decay_weighting_enabled_recent_paper(config_with_decay, sample_version_history):
    """Test decay weighting maintains score for recent papers."""
    from datetime import datetime
    analyzer = GapAnalyzer(config=config_with_decay)
    
    current_year = datetime.now().year
    raw_score = 80.0
    papers = [
        {
            'filename': 'recent_paper.pdf',
            'contribution_summary': 'Main contribution',
            'estimated_contribution_percent': 80,
            'year': current_year - 1  # 1 year old
        }
    ]
    
    final_score, metadata = analyzer.apply_decay_weighting(
        raw_score, papers, version_history=sample_version_history
    )
    
    # Score should be slightly reduced but close to raw score
    assert final_score <= raw_score
    assert final_score > raw_score * 0.9  # Within 10%
    assert metadata['decay_applied'] is True
    assert metadata['freshness_score'] > 0.8  # Recent paper has high freshness


def test_decay_weight_blending(config_partial_decay, sample_version_history):
    """Test decay weight parameter controls blending."""
    from datetime import datetime
    current_year = datetime.now().year
    
    papers = [
        {
            'filename': 'old_paper.pdf',
            'contribution_summary': 'Main contribution',
            'estimated_contribution_percent': 80,
            'year': current_year - 10
        }
    ]
    
    raw_score = 80.0
    
    # No decay (weight=0)
    config_no = {
        'evidence_decay': {
            'enabled': True,
            'weight_in_gap_analysis': True,
            'decay_weight': 0.0,
            'half_life_years': 5.0,
            'apply_to_pillars': ['all']
        }
    }
    analyzer_no = GapAnalyzer(config=config_no)
    score_no, _ = analyzer_no.apply_decay_weighting(raw_score, papers, version_history=sample_version_history)
    
    # Full decay (weight=1)
    config_full = {
        'evidence_decay': {
            'enabled': True,
            'weight_in_gap_analysis': True,
            'decay_weight': 1.0,
            'half_life_years': 5.0,
            'apply_to_pillars': ['all']
        }
    }
    analyzer_full = GapAnalyzer(config=config_full)
    score_full, _ = analyzer_full.apply_decay_weighting(raw_score, papers, version_history=sample_version_history)
    
    # Partial decay (weight=0.5)
    analyzer_partial = GapAnalyzer(config=config_partial_decay)
    score_partial, _ = analyzer_partial.apply_decay_weighting(raw_score, papers, version_history=sample_version_history)
    
    # Verify ordering
    assert score_no >= score_partial >= score_full
    # No decay should equal raw score
    assert score_no == raw_score


def test_apply_decay_no_papers(config_with_decay):
    """Test decay weighting with no contributing papers."""
    analyzer = GapAnalyzer(config=config_with_decay)
    
    raw_score = 80.0
    papers = []
    
    final_score, metadata = analyzer.apply_decay_weighting(raw_score, papers)
    
    assert final_score == raw_score
    assert metadata['decay_applied'] is False
    assert metadata['reason'] == 'no_papers'


def test_pillar_specific_decay():
    """Test pillar-specific decay application."""
    config = {
        'evidence_decay': {
            'enabled': True,
            'half_life_years': 5.0,
            'weight_in_gap_analysis': True,
            'decay_weight': 0.7,
            'apply_to_pillars': ['Security', 'Performance'],  # Only specific pillars
            'min_freshness_threshold': 0.3
        }
    }
    
    analyzer = GapAnalyzer(config=config)
    
    from datetime import datetime
    current_year = datetime.now().year
    raw_score = 80.0
    papers = [
        {
            'filename': 'old_paper.pdf',
            'contribution_summary': 'Main contribution',
            'estimated_contribution_percent': 80,
            'year': current_year - 10
        }
    ]
    
    # Decay should apply to Security pillar
    final_score_security, metadata_security = analyzer.apply_decay_weighting(
        raw_score, papers, pillar_name='Security'
    )
    assert metadata_security['decay_applied'] is True
    assert final_score_security < raw_score
    
    # Decay should NOT apply to different pillar
    final_score_other, metadata_other = analyzer.apply_decay_weighting(
        raw_score, papers, pillar_name='Other Pillar'
    )
    assert metadata_other['decay_applied'] is False
    assert final_score_other == raw_score


def test_generate_decay_impact_report(config_with_decay, sample_version_history):
    """Test A/B comparison report generation."""
    from datetime import datetime
    current_year = datetime.now().year
    
    analyzer = GapAnalyzer(config=config_with_decay)
    
    requirements = {
        'REQ-1': ['Sub-1.1', 'Sub-1.2']
    }
    
    analysis_results = {
        'REQ-1': {
            'Sub-1.1': {
                'completeness_percent': 80,
                'gap_analysis': 'Some gap',
                'contributing_papers': [
                    {
                        'filename': 'old_paper.pdf',
                        'contribution_summary': 'Old contribution',
                        'estimated_contribution_percent': 80,
                        'year': current_year - 10
                    }
                ]
            },
            'Sub-1.2': {
                'completeness_percent': 75,
                'gap_analysis': 'Another gap',
                'contributing_papers': [
                    {
                        'filename': 'recent_paper.pdf',
                        'contribution_summary': 'Recent contribution',
                        'estimated_contribution_percent': 75,
                        'year': current_year - 1
                    }
                ]
            }
        }
    }
    
    report = analyzer.generate_decay_impact_report(
        'Test Pillar', requirements, analysis_results, sample_version_history
    )
    
    assert 'pillar' in report
    assert report['pillar'] == 'Test Pillar'
    assert 'requirements' in report
    assert len(report['requirements']) == 2
    assert 'summary' in report
    
    summary = report['summary']
    assert summary['total_requirements'] == 2
    assert 'avg_delta' in summary
    assert 'significant_changes' in summary
    assert 'impact_breakdown' in summary
    
    # Check impact breakdown
    breakdown = summary['impact_breakdown']
    assert 'decreased' in breakdown
    assert 'increased' in breakdown
    assert 'minimal' in breakdown


def test_evidence_decay_tracker_config_init():
    """Test EvidenceDecayTracker initialization with config."""
    config = {
        'evidence_decay': {
            'enabled': True,
            'half_life_years': 3.0,
            'weight_in_gap_analysis': True,
            'decay_weight': 0.8,
            'apply_to_pillars': ['Security'],
            'min_freshness_threshold': 0.2
        }
    }
    
    tracker = EvidenceDecayTracker(config=config)
    
    assert tracker.half_life == 3.0
    assert tracker.enabled is True
    assert tracker.weight_in_gap_analysis is True
    assert tracker.decay_weight == 0.8
    assert tracker.apply_to_pillars == ['Security']
    assert tracker.min_freshness_threshold == 0.2


def test_evidence_decay_tracker_should_apply():
    """Test should_apply_decay method."""
    config = {
        'evidence_decay': {
            'enabled': True,
            'half_life_years': 5.0,
            'weight_in_gap_analysis': True,
            'apply_to_pillars': ['Security', 'Performance']
        }
    }
    
    tracker = EvidenceDecayTracker(config=config)
    
    # Should apply to Security
    assert tracker.should_apply_decay('Security') is True
    
    # Should apply to Performance
    assert tracker.should_apply_decay('Performance') is True
    
    # Should NOT apply to other pillars
    assert tracker.should_apply_decay('Other') is False
    
    # Test with 'all' pillars
    config_all = {
        'evidence_decay': {
            'enabled': True,
            'weight_in_gap_analysis': True,
            'apply_to_pillars': ['all']
        }
    }
    tracker_all = EvidenceDecayTracker(config=config_all)
    assert tracker_all.should_apply_decay('Any Pillar') is True


def test_evidence_decay_tracker_disabled():
    """Test that decay is not applied when disabled."""
    config = {
        'evidence_decay': {
            'enabled': False,
            'weight_in_gap_analysis': False
        }
    }
    
    tracker = EvidenceDecayTracker(config=config)
    
    assert tracker.should_apply_decay('Any Pillar') is False


def test_calculate_freshness_for_paper():
    """Test freshness calculation for individual papers."""
    from datetime import datetime
    current_year = datetime.now().year
    
    tracker = EvidenceDecayTracker(half_life_years=5.0)
    
    # Current year paper
    paper_current = {'year': current_year}
    freshness_current = tracker.calculate_freshness_for_paper(paper_current)
    assert freshness_current == 1.0
    
    # 5-year-old paper (one half-life)
    paper_5y = {'year': current_year - 5}
    freshness_5y = tracker.calculate_freshness_for_paper(paper_5y)
    assert abs(freshness_5y - 0.5) < 0.01
    
    # 10-year-old paper (two half-lives)
    paper_10y = {'year': current_year - 10}
    freshness_10y = tracker.calculate_freshness_for_paper(paper_10y)
    assert abs(freshness_10y - 0.25) < 0.01
    
    # Paper with no year (should return neutral 0.5)
    paper_no_year = {'filename': 'test.pdf'}
    freshness_no_year = tracker.calculate_freshness_for_paper(paper_no_year)
    assert freshness_no_year == 0.5


def test_metadata_structure(config_with_decay):
    """Test that metadata structure is correct."""
    from datetime import datetime
    analyzer = GapAnalyzer(config=config_with_decay)
    
    current_year = datetime.now().year
    raw_score = 75.0
    papers = [
        {
            'filename': 'test.pdf',
            'contribution_summary': 'Test contribution',
            'estimated_contribution_percent': 75,
            'year': current_year - 5
        }
    ]
    
    final_score, metadata = analyzer.apply_decay_weighting(raw_score, papers)
    
    # Check all required metadata fields
    assert 'raw_score' in metadata
    assert 'final_score' in metadata
    assert 'decay_applied' in metadata
    assert 'freshness_score' in metadata
    assert 'best_paper' in metadata
    assert 'decay_weight' in metadata
    
    # Check values
    assert metadata['raw_score'] == raw_score
    assert metadata['decay_applied'] is True
    assert metadata['best_paper'] == 'test.pdf'
    assert metadata['decay_weight'] == 0.7
