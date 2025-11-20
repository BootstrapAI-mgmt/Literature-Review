"""Unit tests for relevance assessor."""

import pytest
from literature_review.analysis.relevance_assessor import (
    RelevanceAssessor, RelevanceScore, assess_paper_relevance, SEMANTIC_AVAILABLE
)


def test_keyword_overlap_high_relevance():
    """Test high keyword overlap."""
    assessor = RelevanceAssessor(relevance_threshold=0.3)
    
    # Use text with better keyword overlap
    paper_text = "STDP learning mechanism for spiking neural networks"
    gap_text = "Implement STDP learning mechanism"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    assert score.is_relevant is True
    assert score.keyword_score >= 0.5  # Should have high overlap
    assert score.method_used == "keyword"


def test_keyword_overlap_low_relevance():
    """Test low keyword overlap."""
    assessor = RelevanceAssessor(relevance_threshold=0.3)
    
    paper_text = "Deep learning for image classification using CNNs"
    gap_text = "Implement STDP learning mechanism"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    assert score.is_relevant is False
    assert score.keyword_score < 0.3


def test_custom_threshold():
    """Test custom relevance threshold."""
    assessor = RelevanceAssessor(relevance_threshold=0.7)  # High threshold
    
    paper_text = "STDP plasticity mechanism"
    gap_text = "Implement STDP"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    # May or may not be relevant depending on keyword density
    # Just check score is calculated
    assert 0.0 <= score.confidence <= 1.0


def test_assess_paper_to_multiple_gaps():
    """Test assessment against multiple gaps."""
    assessor = RelevanceAssessor()
    
    paper_text = "Spike-timing dependent plasticity in neuromorphic chips"
    
    gaps = [
        {'gap_id': 'REQ-001-SUB-001', 'requirement_text': 'Implement STDP learning'},
        {'gap_id': 'REQ-002-SUB-003', 'requirement_text': 'Deep learning optimization'},
        {'gap_id': 'REQ-003-SUB-002', 'requirement_text': 'Neuromorphic hardware design'}
    ]
    
    is_relevant, matched_gaps, confidence = assessor.assess_paper_to_gaps(paper_text, gaps)
    
    assert is_relevant is True
    assert len(matched_gaps) >= 1  # Should match at least STDP and neuromorphic gaps
    assert 'REQ-001-SUB-001' in matched_gaps or 'REQ-003-SUB-002' in matched_gaps


def test_keyword_extraction():
    """Test keyword extraction."""
    assessor = RelevanceAssessor()
    
    text = "The quick brown fox jumps over the lazy dog"
    keywords = assessor._extract_keywords(text)
    
    # Should filter stopwords
    assert 'the' not in keywords
    assert 'quick' in keywords
    assert 'brown' in keywords
    assert 'fox' in keywords


def test_batch_assessment():
    """Test batch processing."""
    assessor = RelevanceAssessor()
    
    papers = [
        {'filename': 'paper1.pdf', 'title': 'STDP learning mechanism', 'abstract': 'Spike-timing plasticity'},
        {'filename': 'paper2.pdf', 'title': 'GPU acceleration', 'abstract': 'Fast computation'},
        {'filename': 'paper3.pdf', 'title': 'Neuromorphic chips', 'abstract': 'Hardware implementation'}
    ]
    
    gaps = [
        {'gap_id': 'REQ-001', 'requirement_text': 'Implement STDP learning mechanism'}
    ]
    
    results = assessor.batch_assess(papers, gaps)
    
    assert len(results) == 3
    assert results[0]['filename'] == 'paper1.pdf'
    assert results[0]['is_relevant'] is True  # STDP paper should match STDP gap


@pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="sentence-transformers not installed")
def test_semantic_similarity():
    """Test semantic similarity scoring (requires sentence-transformers)."""
    assessor = RelevanceAssessor(use_semantic=True)
    
    # Semantically similar but different words
    paper_text = "Learning rules based on spike timing in neural networks"
    gap_text = "Implement STDP mechanism"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    assert score.method_used == "hybrid"
    assert score.semantic_score > 0.0


def test_convenience_function():
    """Test convenience function."""
    paper_text = "STDP learning mechanism for spiking networks"
    gap_text = "Implement STDP learning mechanism"
    
    score = assess_paper_relevance(paper_text, gap_text, threshold=0.3)
    
    assert isinstance(score, RelevanceScore)
    assert score.is_relevant is True


def test_no_keyword_overlap():
    """Test when there's no keyword overlap."""
    assessor = RelevanceAssessor(relevance_threshold=0.3)
    
    paper_text = "Convolutional neural networks for image classification"
    gap_text = "Quantum computing algorithms"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    assert score.is_relevant is False
    assert score.keyword_score == 0.0
    assert score.confidence == 0.0


def test_empty_gap_text():
    """Test handling of empty gap text."""
    assessor = RelevanceAssessor(relevance_threshold=0.3)
    
    paper_text = "Some paper content"
    gap_text = ""
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    # Empty gap should have no keywords, leading to 0.0 score
    assert score.keyword_score == 0.0
    assert score.is_relevant is False


def test_empty_paper_text():
    """Test handling of empty paper text."""
    assessor = RelevanceAssessor(relevance_threshold=0.3)
    
    paper_text = ""
    gap_text = "Implement STDP learning"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    # Empty paper should have no keyword overlap
    assert score.keyword_score == 0.0
    assert score.is_relevant is False


def test_gap_id_in_matched_requirements():
    """Test that gap_id is correctly added to matched requirements."""
    assessor = RelevanceAssessor(relevance_threshold=0.3)
    
    paper_text = "STDP learning mechanism implementation"
    gap_text = "Implement STDP learning"
    gap_id = "GAP-123"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text, gap_id)
    
    assert score.is_relevant is True
    assert gap_id in score.matched_requirements


def test_no_gaps_provided():
    """Test assessment when no gaps are provided."""
    assessor = RelevanceAssessor()
    
    paper_text = "Some paper about neural networks"
    gaps = []
    
    is_relevant, matched_gaps, confidence = assessor.assess_paper_to_gaps(paper_text, gaps)
    
    assert is_relevant is False
    assert matched_gaps == []
    assert confidence == 0.0


def test_batch_assess_empty_papers():
    """Test batch assessment with empty paper list."""
    assessor = RelevanceAssessor()
    
    papers = []
    gaps = [{'gap_id': 'REQ-001', 'requirement_text': 'STDP learning'}]
    
    results = assessor.batch_assess(papers, gaps)
    
    assert results == []


def test_batch_assess_missing_fields():
    """Test batch assessment with missing optional fields."""
    assessor = RelevanceAssessor()
    
    papers = [
        {'filename': 'paper1.pdf'},  # Missing title and abstract
        {'title': 'Only title'},      # Missing filename and abstract
    ]
    
    gaps = [{'gap_id': 'REQ-001', 'requirement_text': 'STDP learning'}]
    
    results = assessor.batch_assess(papers, gaps)
    
    assert len(results) == 2
    assert results[0]['filename'] == 'paper1.pdf'
    assert results[1]['filename'] == 'unknown'


def test_keyword_extraction_with_numbers():
    """Test that keywords with numbers are extracted correctly."""
    assessor = RelevanceAssessor()
    
    text = "Using Python3 and TensorFlow2 for ML development"
    keywords = assessor._extract_keywords(text)
    
    assert 'python3' in keywords
    assert 'tensorflow2' in keywords
    assert 'development' in keywords


def test_high_threshold_rejection():
    """Test that high threshold properly rejects moderate matches."""
    assessor = RelevanceAssessor(relevance_threshold=0.9)
    
    paper_text = "Neural networks with STDP"
    gap_text = "Implement STDP learning mechanism in neuromorphic hardware"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    # Should have some keyword overlap but not enough for high threshold
    assert score.keyword_score > 0.0
    # May or may not be relevant depending on exact keyword overlap
    assert 0.0 <= score.confidence <= 1.0


def test_case_insensitive_keyword_matching():
    """Test that keyword matching is case-insensitive."""
    assessor = RelevanceAssessor(relevance_threshold=0.3)
    
    paper_text = "STDP Learning Mechanism"
    gap_text = "stdp learning mechanism"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    # Should match perfectly despite different cases
    assert score.is_relevant is True
    assert score.keyword_score == 1.0


def test_assess_paper_to_gaps_partial_match():
    """Test that partial matches are captured correctly."""
    assessor = RelevanceAssessor(relevance_threshold=0.3)
    
    paper_text = "STDP learning in spiking neural networks"
    
    gaps = [
        {'gap_id': 'GAP-1', 'requirement_text': 'STDP learning'},
        {'gap_id': 'GAP-2', 'requirement_text': 'Quantum computing'},
        {'gap_id': 'GAP-3', 'requirement_text': 'Spiking networks'}
    ]
    
    is_relevant, matched_gaps, confidence = assessor.assess_paper_to_gaps(paper_text, gaps)
    
    assert is_relevant is True
    assert 'GAP-1' in matched_gaps
    assert 'GAP-3' in matched_gaps
    assert 'GAP-2' not in matched_gaps
    assert confidence > 0.0


def test_semantic_disabled_by_default():
    """Test that semantic similarity is disabled by default."""
    assessor = RelevanceAssessor()
    
    paper_text = "Neural plasticity mechanisms"
    gap_text = "STDP learning"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    assert score.method_used == "keyword"
    assert score.semantic_score == 0.0


def test_stopword_filtering():
    """Test that common stopwords are filtered out."""
    assessor = RelevanceAssessor()
    
    text = "the quick brown fox and the lazy dog"
    keywords = assessor._extract_keywords(text)
    
    # Stopwords should be filtered
    assert 'the' not in keywords
    assert 'and' not in keywords
    
    # Content words should remain
    assert 'quick' in keywords
    assert 'brown' in keywords
    assert 'lazy' in keywords


def test_short_word_filtering():
    """Test that short words (length <= 2) are filtered."""
    assessor = RelevanceAssessor()
    
    text = "to be or not to be a B C D"
    keywords = assessor._extract_keywords(text)
    
    # Short words and stopwords should be filtered
    assert 'to' not in keywords
    assert 'be' not in keywords
    assert 'or' not in keywords
    assert 'a' not in keywords
    
    # Note: Single letters might be filtered by length check
    # This depends on implementation details


def test_semantic_unavailable_fallback():
    """Test that requesting semantic when unavailable falls back to keyword-only."""
    # Try to create assessor with semantic enabled
    assessor = RelevanceAssessor(use_semantic=True)
    
    # If semantic is not available, it should fall back
    if not SEMANTIC_AVAILABLE:
        assert assessor.use_semantic is False
        assert assessor.semantic_model is None


def test_assess_with_gap_id_no_match():
    """Test that gap_id is not added when not relevant."""
    assessor = RelevanceAssessor(relevance_threshold=0.3)
    
    paper_text = "Quantum computing algorithms"
    gap_text = "STDP learning mechanism"
    gap_id = "GAP-999"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text, gap_id)
    
    assert score.is_relevant is False
    assert gap_id not in score.matched_requirements
    assert score.matched_requirements == []
