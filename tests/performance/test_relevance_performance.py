"""Performance tests for relevance assessor."""

import time
import pytest
from literature_review.analysis.relevance_assessor import RelevanceAssessor


@pytest.mark.performance
def test_single_assessment_performance():
    """Test single assessment completes in < 1s."""
    assessor = RelevanceAssessor()
    
    paper_text = "Spike-timing dependent plasticity" * 100  # Long text
    gap_text = "Implement STDP mechanism"
    
    start = time.time()
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    elapsed = time.time() - start
    
    assert elapsed < 1.0, f"Assessment took {elapsed:.2f}s (expected < 1s)"


@pytest.mark.performance
def test_batch_assessment_performance():
    """Test batch assessment scales linearly."""
    assessor = RelevanceAssessor()
    
    papers = [
        {'filename': f'paper{i}.pdf', 'title': f'Title {i}', 'abstract': 'Abstract text'}
        for i in range(100)
    ]
    
    gaps = [
        {'gap_id': f'GAP-{i}', 'requirement_text': f'Requirement {i}'}
        for i in range(10)
    ]
    
    start = time.time()
    results = assessor.batch_assess(papers, gaps)
    elapsed = time.time() - start
    
    # 100 papers x 10 gaps = 1000 assessments
    # Should complete in < 10s (< 10ms per assessment)
    assert elapsed < 10.0, f"Batch assessment took {elapsed:.2f}s (expected < 10s)"
    assert len(results) == 100


@pytest.mark.performance
def test_keyword_extraction_performance():
    """Test keyword extraction is efficient."""
    assessor = RelevanceAssessor()
    
    # Large text with many words
    text = " ".join([f"word{i}" for i in range(1000)])
    
    start = time.time()
    for _ in range(100):
        keywords = assessor._extract_keywords(text)
    elapsed = time.time() - start
    
    # 100 extractions should be very fast
    assert elapsed < 1.0, f"Keyword extraction took {elapsed:.2f}s (expected < 1s)"


@pytest.mark.performance
def test_multiple_gap_assessment_performance():
    """Test performance when assessing against many gaps."""
    assessor = RelevanceAssessor()
    
    paper_text = "Neural network implementation with STDP learning"
    
    # Create many gaps
    gaps = [
        {'gap_id': f'GAP-{i}', 'requirement_text': f'Requirement about topic {i}'}
        for i in range(50)
    ]
    
    start = time.time()
    is_relevant, matched_gaps, confidence = assessor.assess_paper_to_gaps(paper_text, gaps)
    elapsed = time.time() - start
    
    # Should assess against 50 gaps quickly
    assert elapsed < 0.5, f"Multi-gap assessment took {elapsed:.2f}s (expected < 0.5s)"
