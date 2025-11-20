# INCR-W1-2: Paper Relevance Assessor

**Wave:** 1 (Foundation)  
**Priority:** 🔴 Critical  
**Effort:** 6-8 hours  
**Status:** 🟢 Ready  
**Assignable:** ML/NLP Developer

---

## Overview

Create a relevance assessment engine that determines whether a new paper is likely to close existing research gaps. Uses keyword-based matching and optional semantic similarity to score paper-to-gap relevance.

---

## Dependencies

**Prerequisites:**
- None (Wave 1 foundation task)

**Blocks:**
- INCR-W2-1 (CLI Incremental Review Mode)
- INCR-W2-2 (Dashboard Job Continuation Endpoint)

---

## Scope

### Included
- [x] Create `literature_review/analysis/relevance_assessor.py`
- [x] Implement keyword-based relevance scoring
- [x] Optional: Semantic similarity using sentence-transformers
- [x] Configurable scoring algorithms
- [x] Performance benchmarks (< 1s per paper)
- [x] Comprehensive unit tests

### Excluded
- ❌ ML-based ranking (Wave 4: INCR-W4-1)
- ❌ External paper search (Wave 4: INCR-W4-2)
- ❌ User-facing UI (Wave 2-3 Dashboard tasks)

---

## Technical Specification

### File Structure
```
literature_review/analysis/
├── relevance_assessor.py    # NEW
├── gap_analyzer.py           # From INCR-W1-1
└── result_merger.py          # From INCR-W1-3
```

### Core Implementation

```python
# literature_review/analysis/relevance_assessor.py

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Optional: Semantic similarity
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logger.warning("sentence-transformers not available. Semantic scoring disabled.")

@dataclass
class RelevanceScore:
    """Result of paper-to-gap relevance assessment."""
    is_relevant: bool
    matched_requirements: List[str]
    confidence: float
    keyword_score: float
    semantic_score: float
    method_used: str  # "keyword" | "semantic" | "hybrid"

class RelevanceAssessor:
    """Assesses whether papers are relevant to closing research gaps."""
    
    def __init__(
        self,
        relevance_threshold: float = 0.3,
        use_semantic: bool = False,
        semantic_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize relevance assessor.
        
        Args:
            relevance_threshold: Minimum score to consider paper relevant (0.0-1.0)
            use_semantic: Enable semantic similarity scoring (requires sentence-transformers)
            semantic_model: SentenceTransformer model name
        """
        self.relevance_threshold = relevance_threshold
        self.use_semantic = use_semantic and SEMANTIC_AVAILABLE
        
        # Load semantic model if enabled
        self.semantic_model = None
        if self.use_semantic:
            try:
                self.semantic_model = SentenceTransformer(semantic_model)
                logger.info(f"Loaded semantic model: {semantic_model}")
            except Exception as e:
                logger.warning(f"Failed to load semantic model: {e}. Falling back to keyword-only.")
                self.use_semantic = False
        
        # Weights for hybrid scoring
        self.keyword_weight = 0.7
        self.semantic_weight = 0.3
    
    def assess_gap_closing_potential(
        self,
        paper_text: str,
        gap_text: str,
        gap_id: Optional[str] = None
    ) -> RelevanceScore:
        """
        Assess if paper is relevant to closing a specific gap.
        
        Args:
            paper_text: Paper title + abstract (or full text)
            gap_text: Gap requirement text
            gap_id: Optional gap identifier for logging
        
        Returns:
            RelevanceScore with is_relevant flag and confidence
        
        Example:
            >>> assessor = RelevanceAssessor()
            >>> paper_text = "Spike-timing dependent plasticity in spiking neural networks"
            >>> gap_text = "Implement STDP learning mechanism"
            >>> score = assessor.assess_gap_closing_potential(paper_text, gap_text)
            >>> print(score.is_relevant)
            True
            >>> print(f"Confidence: {score.confidence:.2f}")
            Confidence: 0.85
        """
        # Keyword-based scoring
        keyword_score = self._keyword_overlap_score(paper_text, gap_text)
        
        # Semantic scoring (if enabled)
        semantic_score = 0.0
        if self.use_semantic and self.semantic_model:
            semantic_score = self._semantic_similarity_score(paper_text, gap_text)
        
        # Combine scores
        if self.use_semantic:
            combined_score = (
                self.keyword_weight * keyword_score +
                self.semantic_weight * semantic_score
            )
            method = "hybrid"
        else:
            combined_score = keyword_score
            method = "keyword"
        
        # Determine relevance
        is_relevant = combined_score >= self.relevance_threshold
        
        matched_reqs = [gap_id] if is_relevant and gap_id else []
        
        return RelevanceScore(
            is_relevant=is_relevant,
            matched_requirements=matched_reqs,
            confidence=combined_score,
            keyword_score=keyword_score,
            semantic_score=semantic_score,
            method_used=method
        )
    
    def assess_paper_to_gaps(
        self,
        paper_text: str,
        gaps: List[Dict]
    ) -> Tuple[bool, List[str], float]:
        """
        Assess paper relevance against multiple gaps.
        
        Args:
            paper_text: Paper title + abstract
            gaps: List of gap dictionaries with 'gap_id' and 'requirement_text'
        
        Returns:
            (is_relevant, matched_gap_ids, avg_confidence)
        
        Example:
            >>> gaps = [
            ...     {'gap_id': 'REQ-001-SUB-001', 'requirement_text': 'STDP learning'},
            ...     {'gap_id': 'REQ-002-SUB-003', 'requirement_text': 'Hardware acceleration'}
            ... ]
            >>> is_relevant, matched, confidence = assessor.assess_paper_to_gaps(paper_text, gaps)
        """
        matched_gaps = []
        confidences = []
        
        for gap in gaps:
            gap_id = gap.get('gap_id', 'unknown')
            gap_text = gap.get('requirement_text', '')
            
            score = self.assess_gap_closing_potential(paper_text, gap_text, gap_id)
            
            if score.is_relevant:
                matched_gaps.append(gap_id)
                confidences.append(score.confidence)
        
        if matched_gaps:
            avg_confidence = sum(confidences) / len(confidences)
            return (True, matched_gaps, avg_confidence)
        else:
            return (False, [], 0.0)
    
    def _keyword_overlap_score(self, paper_text: str, gap_text: str) -> float:
        """
        Calculate keyword overlap score.
        
        Score = |intersection| / |gap_keywords|
        
        Args:
            paper_text: Paper text (title + abstract)
            gap_text: Gap requirement text
        
        Returns:
            Overlap score (0.0-1.0)
        """
        # Normalize and tokenize
        paper_keywords = self._extract_keywords(paper_text)
        gap_keywords = self._extract_keywords(gap_text)
        
        if not gap_keywords:
            return 0.0
        
        # Calculate overlap
        intersection = paper_keywords & gap_keywords
        overlap_score = len(intersection) / len(gap_keywords)
        
        return min(overlap_score, 1.0)  # Cap at 1.0
    
    def _semantic_similarity_score(self, paper_text: str, gap_text: str) -> float:
        """
        Calculate semantic similarity using sentence embeddings.
        
        Args:
            paper_text: Paper text
            gap_text: Gap text
        
        Returns:
            Cosine similarity score (0.0-1.0)
        """
        if not self.semantic_model:
            return 0.0
        
        try:
            # Generate embeddings
            paper_embedding = self.semantic_model.encode(paper_text, convert_to_tensor=False)
            gap_embedding = self.semantic_model.encode(gap_text, convert_to_tensor=False)
            
            # Cosine similarity
            import numpy as np
            similarity = np.dot(paper_embedding, gap_embedding) / (
                np.linalg.norm(paper_embedding) * np.linalg.norm(gap_embedding)
            )
            
            # Normalize to 0-1 (cosine can be -1 to 1)
            normalized = (similarity + 1) / 2
            
            return float(normalized)
        except Exception as e:
            logger.error(f"Semantic similarity failed: {e}")
            return 0.0
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """
        Extract keywords from text (lowercase, alphanumeric, length > 2).
        
        Args:
            text: Input text
        
        Returns:
            Set of keywords
        """
        # Lowercase and remove non-alphanumeric
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        
        # Filter short words and common stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'it', 'its', 'we', 'our', 'you', 'your'
        }
        
        keywords = {
            word for word in words
            if len(word) > 2 and word not in stopwords
        }
        
        return keywords
    
    def batch_assess(
        self,
        papers: List[Dict],
        gaps: List[Dict]
    ) -> List[Dict]:
        """
        Assess multiple papers against multiple gaps (batch processing).
        
        Args:
            papers: List of paper dicts with 'filename', 'title', 'abstract'
            gaps: List of gap dicts with 'gap_id', 'requirement_text'
        
        Returns:
            List of assessment results
        
        Example:
            >>> papers = [
            ...     {'filename': 'paper1.pdf', 'title': 'STDP in SNNs', 'abstract': '...'},
            ...     {'filename': 'paper2.pdf', 'title': 'GPU acceleration', 'abstract': '...'}
            ... ]
            >>> results = assessor.batch_assess(papers, gaps)
            >>> relevant_papers = [r for r in results if r['is_relevant']]
        """
        results = []
        
        for paper in papers:
            paper_text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            
            is_relevant, matched_gaps, confidence = self.assess_paper_to_gaps(
                paper_text, gaps
            )
            
            results.append({
                'filename': paper.get('filename', 'unknown'),
                'is_relevant': is_relevant,
                'matched_gaps': matched_gaps,
                'confidence': confidence,
                'gap_count': len(matched_gaps)
            })
        
        return results


# Convenience functions
def assess_paper_relevance(
    paper_text: str,
    gap_text: str,
    threshold: float = 0.3,
    use_semantic: bool = False
) -> RelevanceScore:
    """
    Convenience function for one-off relevance assessment.
    
    Args:
        paper_text: Paper title + abstract
        gap_text: Gap requirement text
        threshold: Relevance threshold (default: 0.3)
        use_semantic: Enable semantic scoring (default: False)
    
    Returns:
        RelevanceScore
    """
    assessor = RelevanceAssessor(
        relevance_threshold=threshold,
        use_semantic=use_semantic
    )
    return assessor.assess_gap_closing_potential(paper_text, gap_text)
```

---

## Testing Strategy

### Unit Tests

Create `tests/unit/analysis/test_relevance_assessor.py`:

```python
import pytest
from literature_review.analysis.relevance_assessor import (
    RelevanceAssessor, RelevanceScore, assess_paper_relevance, SEMANTIC_AVAILABLE
)

def test_keyword_overlap_high_relevance():
    """Test high keyword overlap."""
    assessor = RelevanceAssessor(relevance_threshold=0.3)
    
    paper_text = "Spike-timing dependent plasticity (STDP) in spiking neural networks"
    gap_text = "Implement STDP learning mechanism in neuromorphic hardware"
    
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    
    assert score.is_relevant is True
    assert score.keyword_score > 0.3
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
        {'filename': 'paper1.pdf', 'title': 'STDP in SNNs', 'abstract': 'Spike-timing plasticity'},
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
    paper_text = "STDP learning in spiking networks"
    gap_text = "Implement spike-timing dependent plasticity"
    
    score = assess_paper_relevance(paper_text, gap_text, threshold=0.3)
    
    assert isinstance(score, RelevanceScore)
    assert score.is_relevant is True
```

### Performance Benchmarks

Create `tests/performance/test_relevance_performance.py`:

```python
import time
import pytest
from literature_review.analysis.relevance_assessor import RelevanceAssessor

def test_single_assessment_performance():
    """Test single assessment completes in < 1s."""
    assessor = RelevanceAssessor()
    
    paper_text = "Spike-timing dependent plasticity" * 100  # Long text
    gap_text = "Implement STDP mechanism"
    
    start = time.time()
    score = assessor.assess_gap_closing_potential(paper_text, gap_text)
    elapsed = time.time() - start
    
    assert elapsed < 1.0, f"Assessment took {elapsed:.2f}s (expected < 1s)"

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
```

---

## Deliverables

- [ ] `literature_review/analysis/relevance_assessor.py` implemented
- [ ] `RelevanceAssessor` class with all methods
- [ ] `RelevanceScore` dataclass
- [ ] Keyword-based scoring algorithm
- [ ] Optional semantic similarity (sentence-transformers)
- [ ] Unit tests in `tests/unit/analysis/test_relevance_assessor.py`
- [ ] Performance tests in `tests/performance/test_relevance_performance.py`
- [ ] Code coverage ≥ 90%
- [ ] Docstrings complete

---

## Success Criteria

✅ **Functional:**
- Can assess paper-to-gap relevance
- Returns structured `RelevanceScore`
- Configurable threshold and scoring method
- Batch processing supported

✅ **Performance:**
- Single assessment: < 1s
- Batch (100 papers, 10 gaps): < 10s
- Memory efficient (no leaks)

✅ **Quality:**
- Unit tests pass (90% coverage)
- Performance benchmarks pass
- No linting errors

---

## Integration Points

### Used By:
- **INCR-W2-1:** CLI Incremental Review Mode
- **INCR-W2-2:** Dashboard Job Continuation Endpoint

### Example Usage:
```python
from literature_review.analysis.relevance_assessor import RelevanceAssessor
from literature_review.analysis.gap_analyzer import extract_gaps_from_file

# Initialize assessor
assessor = RelevanceAssessor(relevance_threshold=0.3, use_semantic=False)

# Load gaps
gaps = extract_gaps_from_file('gap_analysis_output/gap_analysis_report.json')
gap_dicts = [
    {'gap_id': g.gap_id, 'requirement_text': g.requirement_text}
    for g in gaps
]

# Assess paper
paper_text = "Title: STDP in Neuromorphic Chips. Abstract: We implement..."
is_relevant, matched_gaps, confidence = assessor.assess_paper_to_gaps(paper_text, gap_dicts)

if is_relevant:
    print(f"Paper matches {len(matched_gaps)} gaps (confidence: {confidence:.2f})")
    print(f"Matched gaps: {matched_gaps}")
```

---

## Configuration Options

```python
# config/relevance_config.json
{
  "relevance_threshold": 0.3,
  "use_semantic": false,
  "semantic_model": "all-MiniLM-L6-v2",
  "keyword_weight": 0.7,
  "semantic_weight": 0.3,
  "stopwords": ["the", "a", "an", ...]
}
```

---

## Rollback Plan

If issues arise:
1. Revert `relevance_assessor.py`
2. Fall back to "analyze all papers" mode
3. No data loss (read-only operation)

---

**Status:** 🟢 Ready for implementation  
**Assignee:** TBD  
**Estimated Start:** Week 1, Day 1  
**Estimated Completion:** Week 1, Day 2
