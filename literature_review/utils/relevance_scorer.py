"""
Paper Relevance Scoring Utility for Incremental Review Mode.

Scores papers based on relevance to open gaps using keyword matching
and optional semantic similarity.
Part of INCR-W1-2: Paper Relevance Assessor.
"""

import logging
from typing import Dict, List, Optional
import re

logger = logging.getLogger(__name__)

# Optional semantic similarity support
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logger.info("sentence-transformers not available. Using keyword-only scoring.")


class RelevanceScorer:
    """Scores paper relevance to research gaps."""
    
    def __init__(
        self,
        use_semantic: bool = False,
        semantic_weight: float = 0.5
    ):
        """
        Initialize relevance scorer.
        
        Args:
            use_semantic: Enable semantic similarity (requires sentence-transformers)
            semantic_weight: Weight for semantic score (0.0-1.0).
                           Final = keyword_score * (1-weight) + semantic_score * weight
        """
        self.use_semantic = use_semantic and SEMANTIC_AVAILABLE
        self.semantic_weight = semantic_weight
        
        if self.use_semantic:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Semantic similarity enabled")
            except Exception as e:
                logger.warning(f"Failed to load semantic model: {e}. Using keyword-only.")
                self.use_semantic = False
        else:
            self.model = None
    
    def score_relevance(self, paper: Dict, gap: Dict) -> float:
        """
        Score paper relevance to a gap.
        
        Args:
            paper: Paper dictionary with 'title', 'abstract', etc.
            gap: Gap dictionary with 'keywords', 'requirement_text', etc.
        
        Returns:
            Relevance score (0.0-1.0)
        """
        # Get paper text
        paper_text = self._get_paper_text(paper)
        
        # Get gap keywords
        gap_keywords = gap.get('keywords', [])
        
        # Calculate keyword-based score
        keyword_score = self._keyword_match_score(paper_text, gap_keywords)
        
        # If semantic scoring is enabled, compute semantic similarity
        if self.use_semantic and self.model:
            gap_text = gap.get('requirement_text', '') or ' '.join(gap_keywords)
            semantic_score = self._semantic_similarity_score(paper_text, gap_text)
            
            # Blend scores
            final_score = (
                keyword_score * (1 - self.semantic_weight) +
                semantic_score * self.semantic_weight
            )
        else:
            final_score = keyword_score
        
        return min(1.0, max(0.0, final_score))
    
    def _get_paper_text(self, paper: Dict) -> str:
        """Extract searchable text from paper."""
        title = paper.get('title', '')
        abstract = paper.get('abstract', '')
        
        # Combine title and abstract (title weighted more)
        text = f"{title} {title} {abstract}".lower()
        return text
    
    def _keyword_match_score(self, text: str, keywords: List[str]) -> float:
        """
        Calculate keyword match score.
        
        Uses TF-based scoring: count keyword occurrences.
        
        Args:
            text: Paper text
            keywords: Gap keywords
        
        Returns:
            Score (0.0-1.0)
        """
        if not keywords or not text:
            return 0.0
        
        text_lower = text.lower()
        
        # Count matches for each keyword
        total_matches = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Count occurrences (whole word matches)
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            matches = len(re.findall(pattern, text_lower))
            total_matches += matches
        
        # Normalize by number of keywords
        # Score = min(1.0, matches / keywords)
        # This gives 1.0 if all keywords appear at least once
        if total_matches == 0:
            return 0.0
        
        normalized_score = min(1.0, total_matches / len(keywords))
        
        return normalized_score
    
    def _semantic_similarity_score(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity using sentence transformers.
        
        Args:
            text1: First text (paper)
            text2: Second text (gap)
        
        Returns:
            Cosine similarity (0.0-1.0)
        """
        if not self.model or not text1 or not text2:
            return 0.0
        
        try:
            # Encode texts
            embedding1 = self.model.encode(text1, convert_to_numpy=True)
            embedding2 = self.model.encode(text2, convert_to_numpy=True)
            
            # Compute cosine similarity
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            
            # Normalize to 0-1 range (cosine similarity is already -1 to 1, but usually 0-1)
            return max(0.0, min(1.0, float(similarity)))
        
        except Exception as e:
            logger.warning(f"Semantic similarity failed: {e}")
            return 0.0
    
    def batch_score(
        self,
        papers: List[Dict],
        gaps: List[Dict]
    ) -> Dict[str, float]:
        """
        Score all papers against all gaps (batch processing).
        
        For each paper, computes max relevance across all gaps.
        
        Args:
            papers: List of paper dictionaries
            gaps: List of gap dictionaries
        
        Returns:
            Dictionary mapping paper_id -> max_relevance_score
        """
        results = {}
        
        for paper in papers:
            paper_id = paper.get('id') or paper.get('filename', 'unknown')
            
            # Compute relevance to each gap
            scores = [self.score_relevance(paper, gap) for gap in gaps]
            
            # Take max score (most relevant gap)
            max_score = max(scores) if scores else 0.0
            
            results[paper_id] = max_score
        
        return results
