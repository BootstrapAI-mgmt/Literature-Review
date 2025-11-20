"""Paper Relevance Assessment Engine.

Assesses whether papers are relevant to closing research gaps using keyword-based
matching and optional semantic similarity scoring.
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import re
import logging

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
