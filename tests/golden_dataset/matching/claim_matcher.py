"""
Claim Matching Algorithm for Ground Truth Validation

Matches extracted claims to exhaustive ground truth inventories
using semantic similarity and location-based validation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, TYPE_CHECKING
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..schema_anchor import ExhaustiveClaim, AnchorPaper


@dataclass
class MatchResult:
    """Result of matching extracted claims to ground truth."""
    true_positives: List[Tuple[Dict[str, Any], str]] = field(default_factory=list)  # (extracted, ground_truth_id)
    false_positives: List[Dict[str, Any]] = field(default_factory=list)  # Extracted with no match
    false_negatives: List[str] = field(default_factory=list)  # HIGH extractability claim_ids not matched
    acceptable_misses: List[str] = field(default_factory=list)  # LOW extractability claim_ids not matched
    
    @property
    def precision(self) -> float:
        """Extraction precision: TP / (TP + FP)."""
        tp = len(self.true_positives)
        fp = len(self.false_positives)
        return tp / (tp + fp) if (tp + fp) > 0 else 0.0
    
    @property
    def recall(self) -> float:
        """Extraction recall: TP / (TP + FN)."""
        tp = len(self.true_positives)
        fn = len(self.false_negatives)
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    @property
    def f1(self) -> float:
        """F1 score: 2 * P * R / (P + R)."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


class ClaimMatcher:
    """
    Match extracted claims to ground truth for validation.
    
    Uses semantic similarity with location-based validation
    to prevent matching semantically similar but wrong claims.
    
    This matcher supports two modes:
    1. Semantic matching using sentence transformers (when available)
    2. Fallback to sequence matching for environments without ML dependencies
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.8,
        location_tolerance: int = 1,  # Page tolerance
        model_name: str = 'all-MiniLM-L6-v2',
        use_semantic: bool = True
    ):
        """
        Initialize the claim matcher.
        
        Args:
            similarity_threshold: Minimum similarity score for a match (0-1)
            location_tolerance: Number of pages tolerance for location matching
            model_name: Sentence transformer model name (if using semantic mode)
            use_semantic: If True, attempt to use sentence transformers
        """
        self.threshold = similarity_threshold
        self.location_tolerance = location_tolerance
        self.model_name = model_name
        self._model = None
        self._use_semantic = use_semantic and self._check_semantic_available()
    
    def _check_semantic_available(self) -> bool:
        """Check if sentence transformers is available."""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            return True
        except ImportError:
            logger.info("sentence-transformers not available, using sequence matching")
            return False
    
    def _get_model(self):
        """Lazy-load the sentence transformer model."""
        if self._model is None and self._use_semantic:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                logger.warning("Could not load sentence transformer, falling back to sequence matching")
                self._use_semantic = False
        return self._model
    
    def _calculate_sequence_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity using sequence matching (fallback)."""
        from difflib import SequenceMatcher
        
        # Normalize texts
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        return SequenceMatcher(None, t1, t2).ratio()
    
    def _calculate_semantic_similarity(self, texts1: List[str], texts2: List[str]) -> List[List[float]]:
        """Calculate semantic similarity matrix using sentence transformers."""
        model = self._get_model()
        if model is None:
            # Fallback to sequence matching
            matrix = []
            for t1 in texts1:
                row = [self._calculate_sequence_similarity(t1, t2) for t2 in texts2]
                matrix.append(row)
            return matrix
        
        try:
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            logger.warning("scikit-learn not available, falling back to sequence matching")
            self._use_semantic = False
            matrix = []
            for t1 in texts1:
                row = [self._calculate_sequence_similarity(t1, t2) for t2 in texts2]
                matrix.append(row)
            return matrix
        
        embeddings1 = model.encode(texts1)
        embeddings2 = model.encode(texts2)
        
        return cosine_similarity(embeddings1, embeddings2).tolist()
    
    def match(
        self,
        extracted: List[Dict[str, Any]],
        ground_truth: List["ExhaustiveClaim"]
    ) -> MatchResult:
        """
        Match extracted claims to ground truth.
        
        Args:
            extracted: List of extracted claims with 'claim_text' and optionally 'source_page'
            ground_truth: List of ExhaustiveClaim from anchor paper
        
        Returns:
            MatchResult with precision/recall components
        """
        if not extracted or not ground_truth:
            return MatchResult(
                true_positives=[],
                false_positives=extracted if extracted else [],
                false_negatives=[g.claim_id for g in ground_truth 
                                if g.extractability.value == 'high'],
                acceptable_misses=[g.claim_id for g in ground_truth 
                                  if g.extractability.value == 'low']
            )
        
        # Extract texts
        ext_texts = [e.get('claim_text', '') for e in extracted]
        gt_texts = [g.exact_text for g in ground_truth]
        
        # Calculate similarity matrix
        if self._use_semantic:
            similarities = self._calculate_semantic_similarity(ext_texts, gt_texts)
        else:
            similarities = []
            for ext_text in ext_texts:
                row = [self._calculate_sequence_similarity(ext_text, gt_text) 
                       for gt_text in gt_texts]
                similarities.append(row)
        
        # Apply location-based filtering
        for i, ext in enumerate(extracted):
            ext_page = ext.get('source_page', 0)
            for j, gt in enumerate(ground_truth):
                gt_page = gt.location.page if gt.location else 0
                if ext_page > 0 and gt_page > 0:
                    if abs(ext_page - gt_page) > self.location_tolerance:
                        similarities[i][j] = 0  # Disqualify distant matches
        
        # Greedy matching (highest similarity first)
        matches = []
        used_ext = set()
        used_gt = set()
        
        # Sort by similarity descending
        flat_scores = []
        for i in range(len(similarities)):
            for j in range(len(similarities[i])):
                flat_scores.append((similarities[i][j], i, j))
        flat_scores.sort(reverse=True)
        
        for score, i, j in flat_scores:
            if i in used_ext or j in used_gt:
                continue
            if score >= self.threshold:
                matches.append((extracted[i], ground_truth[j].claim_id))
                used_ext.add(i)
                used_gt.add(j)
        
        # Classify unmatched
        false_positives = [
            extracted[i] for i in range(len(extracted)) 
            if i not in used_ext
        ]
        
        false_negatives = [
            ground_truth[j].claim_id for j in range(len(ground_truth))
            if j not in used_gt 
            and ground_truth[j].extractability.value == 'high'
        ]
        
        acceptable_misses = [
            ground_truth[j].claim_id for j in range(len(ground_truth))
            if j not in used_gt 
            and ground_truth[j].extractability.value == 'low'
        ]
        
        return MatchResult(
            true_positives=matches,
            false_positives=false_positives,
            false_negatives=false_negatives,
            acceptable_misses=acceptable_misses
        )
    
    def validate_anchor_paper(
        self,
        extracted: List[Dict[str, Any]],
        anchor_paper: "AnchorPaper"
    ) -> Dict[str, Any]:
        """
        Full validation of extraction against an anchor paper.
        
        Args:
            extracted: List of extracted claims from the pipeline
            anchor_paper: AnchorPaper with exhaustive annotations
        
        Returns:
            Dict with precision, recall, and detailed breakdown
        """
        result = self.match(extracted, anchor_paper.claim_inventory)
        
        # Check non-extraction items (false positive test)
        non_extraction_violations = []
        for ne_item in anchor_paper.non_extraction_items:
            for ext in extracted:
                ext_text = ext.get('claim_text', '')
                if self._use_semantic:
                    sims = self._calculate_semantic_similarity([ext_text], [ne_item.item_text])
                    sim = sims[0][0]
                else:
                    sim = self._calculate_sequence_similarity(ext_text, ne_item.item_text)
                
                if sim >= self.threshold:
                    non_extraction_violations.append({
                        'extracted': ext,
                        'should_not_extract': ne_item.item_id,
                        'similarity': float(sim),
                        'reason': ne_item.reason_not_relevant
                    })
        
        return {
            'precision': result.precision,
            'recall': result.recall,
            'f1': result.f1,
            'true_positives': len(result.true_positives),
            'false_positives': len(result.false_positives),
            'false_negatives': len(result.false_negatives),
            'acceptable_misses': len(result.acceptable_misses),
            'non_extraction_violations': non_extraction_violations,
            'passed': (
                result.recall >= 0.85 and  # AV-02 threshold
                result.precision >= 0.85 and  # AV-01 threshold
                len(non_extraction_violations) == 0  # FP-01
            )
        }
