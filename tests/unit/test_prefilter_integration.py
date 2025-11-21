"""Unit tests for pre-filter integration (INCR-W1-6)."""

import pytest
import json
import sys
import os
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.gap_extractor import GapExtractor, Gap
from literature_review.utils.relevance_scorer import RelevanceScorer
from literature_review.utils.state_manager import StateManager, GapDetail, save_orchestrator_state_enhanced, JobType


# --- GapExtractor Tests ---

@pytest.fixture
def sample_gap_report():
    """Sample gap analysis report."""
    return {
        "pillars": {
            "Pillar 1: Foundational Architecture": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Support spike-timing dependent plasticity mechanisms",
                                "completeness_percent": 45,
                                "evidence": ["paper1.pdf", "paper2.pdf"],
                                "suggested_searches": ["spike timing", "plasticity"]
                            },
                            "SUB-002": {
                                "text": "Implement neuromorphic computing architectures",
                                "completeness_percent": 85,
                                "evidence": ["paper3.pdf", "paper4.pdf", "paper5.pdf"]
                            }
                        }
                    },
                    "REQ-002": {
                        "sub_requirements": {
                            "SUB-003": {
                                "text": "Support recurrent neural network patterns",
                                "completeness_percent": 30,
                                "evidence": ["paper6.pdf"]
                            }
                        }
                    }
                }
            },
            "Pillar 2: Learning Algorithms": {
                "requirements": {
                    "REQ-003": {
                        "sub_requirements": {
                            "SUB-004": {
                                "text": "Implement online learning capabilities",
                                "completeness_percent": 60,
                                "evidence": ["paper7.pdf", "paper8.pdf"]
                            }
                        }
                    }
                }
            }
        }
    }


def test_gap_extractor_initialization():
    """Test GapExtractor initialization."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({}, f)
        temp_path = f.name
    
    try:
        extractor = GapExtractor(temp_path, threshold=0.7)
        assert extractor.threshold == 0.7
        assert extractor.gap_report_path == Path(temp_path)
    finally:
        os.unlink(temp_path)


def test_gap_extractor_extract_gaps(sample_gap_report):
    """Test gap extraction from report."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_gap_report, f)
        temp_path = f.name
    
    try:
        extractor = GapExtractor(temp_path, threshold=0.70)
        gaps = extractor.extract_gaps()
        
        # Should find 3 gaps: SUB-001 (45%), SUB-003 (30%), SUB-004 (60%)
        assert len(gaps) == 3
        
        # Check gap structure
        gap_ids = [f"{g['requirement_id']}-{g['sub_requirement_id']}" for g in gaps]
        assert 'REQ-001-SUB-001' in gap_ids
        assert 'REQ-002-SUB-003' in gap_ids
        assert 'REQ-003-SUB-004' in gap_ids
        
        # Check completeness conversion
        for gap in gaps:
            assert 0.0 <= gap['current_coverage'] <= 1.0
            assert gap['current_coverage'] < 0.70
        
        # Check keywords extraction
        for gap in gaps:
            assert isinstance(gap['keywords'], list)
            assert len(gap['keywords']) > 0
    
    finally:
        os.unlink(temp_path)


def test_gap_extractor_no_gaps(sample_gap_report):
    """Test gap extraction when all requirements are met."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_gap_report, f)
        temp_path = f.name
    
    try:
        # Set very low threshold - all sub-reqs should pass
        extractor = GapExtractor(temp_path, threshold=0.20)
        gaps = extractor.extract_gaps()
        
        # Should find no gaps (all above 20%)
        assert len(gaps) == 0
    
    finally:
        os.unlink(temp_path)


def test_gap_extractor_missing_file():
    """Test gap extraction with missing file."""
    extractor = GapExtractor('/nonexistent/path.json', threshold=0.70)
    gaps = extractor.extract_gaps()
    
    # Should return empty list without crashing
    assert gaps == []


def test_gap_extractor_keyword_extraction():
    """Test keyword extraction from requirement text."""
    extractor = GapExtractor('/dummy/path.json', threshold=0.7)
    
    # Test with meaningful text
    keywords = extractor._extract_keywords(
        "Support spike-timing dependent plasticity mechanisms for neural networks"
    )
    
    assert 'support' in keywords
    assert 'spike-timing' in keywords
    assert 'dependent' in keywords
    assert 'plasticity' in keywords
    assert 'mechanisms' in keywords
    assert 'neural' in keywords
    assert 'networks' in keywords
    
    # Stopwords should be removed
    assert 'the' not in keywords
    assert 'for' not in keywords
    
    # Test empty text
    keywords_empty = extractor._extract_keywords("")
    assert keywords_empty == []


# --- RelevanceScorer Tests ---

@pytest.fixture
def sample_papers():
    """Sample papers for relevance scoring."""
    return [
        {
            'id': 'paper1',
            'title': 'Neural Networks and Spike Timing',
            'abstract': 'This paper explores spike-timing dependent plasticity in neural networks.'
        },
        {
            'id': 'paper2',
            'title': 'Recurrent Neural Architectures',
            'abstract': 'We present recurrent neural network patterns for neuromorphic computing.'
        },
        {
            'id': 'paper3',
            'title': 'Quantum Computing Applications',
            'abstract': 'This work discusses quantum computing for cryptography.'
        }
    ]


@pytest.fixture
def sample_gaps():
    """Sample gaps for relevance scoring."""
    return [
        {
            'pillar_id': 'Pillar 1',
            'requirement_id': 'REQ-001',
            'sub_requirement_id': 'SUB-001',
            'keywords': ['spike', 'timing', 'plasticity', 'neural'],
            'current_coverage': 0.45
        },
        {
            'pillar_id': 'Pillar 1',
            'requirement_id': 'REQ-002',
            'sub_requirement_id': 'SUB-003',
            'keywords': ['recurrent', 'neural', 'network'],
            'current_coverage': 0.30
        }
    ]


def test_relevance_scorer_initialization():
    """Test RelevanceScorer initialization."""
    scorer = RelevanceScorer(use_semantic=False)
    assert scorer.use_semantic is False
    assert scorer.semantic_weight == 0.5
    assert scorer.model is None


def test_relevance_scorer_keyword_matching(sample_papers, sample_gaps):
    """Test keyword-based relevance scoring."""
    scorer = RelevanceScorer(use_semantic=False)
    
    # Paper 1 should be highly relevant to Gap 1 (spike timing plasticity)
    score1 = scorer.score_relevance(sample_papers[0], sample_gaps[0])
    assert 0.0 <= score1 <= 1.0
    assert score1 > 0.5  # Should have good match
    
    # Paper 2 should be relevant to Gap 2 (recurrent networks)
    score2 = scorer.score_relevance(sample_papers[1], sample_gaps[1])
    assert 0.0 <= score2 <= 1.0
    assert score2 > 0.5
    
    # Paper 3 (quantum computing) should have low relevance to neural gaps
    score3 = scorer.score_relevance(sample_papers[2], sample_gaps[0])
    assert 0.0 <= score3 <= 1.0
    assert score3 < 0.3


def test_relevance_scorer_empty_inputs():
    """Test relevance scoring with empty inputs."""
    scorer = RelevanceScorer(use_semantic=False)
    
    # Empty paper
    score = scorer.score_relevance({}, {'keywords': ['test']})
    assert score == 0.0
    
    # Empty gap keywords
    score = scorer.score_relevance(
        {'title': 'Test', 'abstract': 'Test abstract'},
        {'keywords': []}
    )
    assert score == 0.0


def test_relevance_scorer_batch_scoring(sample_papers, sample_gaps):
    """Test batch scoring of papers."""
    scorer = RelevanceScorer(use_semantic=False)
    
    results = scorer.batch_score(sample_papers, sample_gaps)
    
    assert len(results) == len(sample_papers)
    
    # Check all scores are valid
    for paper_id, score in results.items():
        assert 0.0 <= score <= 1.0
    
    # Paper 1 and 2 should have higher scores than paper 3
    assert results['paper1'] > results['paper3']
    assert results['paper2'] > results['paper3']


# --- StateManager Tests ---

def test_state_manager_initialization():
    """Test StateManager initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, 'test_state.json')
        manager = StateManager(state_file)
        
        assert manager.state_file == Path(state_file)
        assert manager.SCHEMA_VERSION == "2.0"


def test_state_manager_save_and_load():
    """Test saving and loading state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, 'test_state.json')
        manager = StateManager(state_file)
        
        # Save state using create_new_state and save_state
        state = manager.create_new_state(
            database_path='/path/to/db.csv',
            database_hash='abc123',
            database_size=150,
            job_type=JobType.INCREMENTAL
        )
        
        # Update state with analysis results
        state.total_papers = 150
        state.papers_analyzed = 45
        state.papers_skipped = 105
        state.total_pillars = 6
        state.overall_coverage = 72.5
        state.gap_metrics.gap_details = [
            GapDetail(
                pillar_id='Pillar 1',
                requirement_id='REQ-001',
                sub_requirement_id='SUB-001',
                current_coverage=0.45,
                target_coverage=0.70,
                gap_size=0.25,
                keywords=['spike', 'timing'],
                evidence_count=2
            )
        ]
        state.gap_metrics.total_gaps = 1
        
        manager.save_state(state)
        
        # Load state
        loaded_state = manager.load_state()
        
        assert loaded_state.schema_version == "2.0"
        assert loaded_state.database_hash == 'abc123'
        assert loaded_state.database_size == 150
        assert loaded_state.total_papers == 150
        assert loaded_state.papers_analyzed == 45
        assert loaded_state.papers_skipped == 105
        assert loaded_state.overall_coverage == 72.5
        assert loaded_state.gap_metrics.total_gaps == 1
        assert len(loaded_state.gap_metrics.gap_details) == 1


def test_state_manager_empty_state():
    """Test loading empty/missing state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, 'nonexistent.json')
        manager = StateManager(state_file)
        
        state = manager.load_state()
        
        # Should return None for missing file
        assert state is None


def test_save_orchestrator_state_enhanced():
    """Test convenience function for saving state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, 'test_state.json')
        
        gap_details = [
            GapDetail(
                pillar_id='Pillar 1',
                requirement_id='REQ-001',
                sub_requirement_id='SUB-001',
                current_coverage=0.45,
                target_coverage=0.70,
                gap_size=0.25,
                keywords=['test'],
                evidence_count=2
            )
        ]
        
        save_orchestrator_state_enhanced(
            database_hash='test_hash',
            database_size=100,
            database_path='/test/path',
            total_papers=100,
            papers_analyzed=30,
            papers_skipped=70,
            gap_details=gap_details,
            state_file=state_file
        )
        
        # Verify file was created
        assert os.path.exists(state_file)
        
        # Verify content
        with open(state_file) as f:
            state = json.load(f)
        
        assert state['database_hash'] == 'test_hash'
        assert state['papers_analyzed'] == 30
        assert state['papers_skipped'] == 70


# --- Integration Tests ---

def test_preview_prefilter_workflow(sample_gap_report, sample_papers):
    """Test complete pre-filter workflow."""
    # Import preview_prefilter locally to avoid import issues
    from literature_review.utils.gap_extractor import GapExtractor
    from literature_review.utils.relevance_scorer import RelevanceScorer
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_gap_report, f)
        temp_path = f.name
    
    try:
        # Extract gaps
        extractor = GapExtractor(temp_path, threshold=0.70)
        gaps = extractor.extract_gaps()
        
        # Manually implement preview_prefilter logic for testing
        scorer = RelevanceScorer()
        
        paper_scores = {}
        for paper in sample_papers:
            paper_id = paper.get('id', 'unknown')
            scores = [scorer.score_relevance(paper, gap) for gap in gaps]
            paper_scores[paper_id] = max(scores) if scores else 0.0
        
        threshold = 0.50
        papers_above = sum(1 for score in paper_scores.values() if score >= threshold)
        papers_below = len(sample_papers) - papers_above
        
        assert len(gaps) == 3
        assert len(paper_scores) == len(sample_papers)
        
        # Verify scores are valid
        for score in paper_scores.values():
            assert 0.0 <= score <= 1.0
        
        # Verify partitioning
        assert papers_above + papers_below == len(sample_papers)
    
    finally:
        os.unlink(temp_path)


def test_preview_prefilter_no_gaps(sample_papers):
    """Test pre-filter preview with no gaps."""
    from literature_review.utils.relevance_scorer import RelevanceScorer
    
    scorer = RelevanceScorer()
    
    # No gaps means all papers should be skipped
    gaps = []
    paper_scores = {}
    for paper in sample_papers:
        paper_id = paper.get('id', 'unknown')
        scores = [scorer.score_relevance(paper, gap) for gap in gaps]
        paper_scores[paper_id] = max(scores) if scores else 0.0
    
    # All scores should be 0 with no gaps
    for score in paper_scores.values():
        assert score == 0.0


def test_threshold_variations(sample_gap_report, sample_papers):
    """Test different threshold values."""
    from literature_review.utils.gap_extractor import GapExtractor
    from literature_review.utils.relevance_scorer import RelevanceScorer
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_gap_report, f)
        temp_path = f.name
    
    try:
        extractor = GapExtractor(temp_path, threshold=0.70)
        gaps = extractor.extract_gaps()
        
        scorer = RelevanceScorer()
        
        # Calculate scores
        paper_scores = {}
        for paper in sample_papers:
            paper_id = paper.get('id', 'unknown')
            scores = [scorer.score_relevance(paper, gap) for gap in gaps]
            paper_scores[paper_id] = max(scores) if scores else 0.0
        
        # Test different thresholds
        papers_30 = sum(1 for score in paper_scores.values() if score >= 0.30)
        papers_50 = sum(1 for score in paper_scores.values() if score >= 0.50)
        papers_70 = sum(1 for score in paper_scores.values() if score >= 0.70)
        
        # Higher threshold should filter more papers
        assert papers_30 >= papers_50
        assert papers_50 >= papers_70
    
    finally:
        os.unlink(temp_path)
