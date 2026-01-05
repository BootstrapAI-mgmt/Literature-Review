"""
Golden Dataset Loader

Utilities for loading and working with the golden dataset.
"""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import functools

from .schema import (
    GoldenDataset,
    AnnotatedClaim,
    ExpectedVerdict,
    KnownGap,
    RecommendationQuality,
    Verdict
)

logger = logging.getLogger(__name__)


class GoldenDatasetLoader:
    """
    Load and query the golden dataset.
    
    Example:
        loader = GoldenDatasetLoader()
        dataset = loader.load()
        
        # Get claims for precision testing
        precision_claims = loader.get_claims_for_test("precision")
        
        # Get approved claims only
        approved = loader.get_claims_by_verdict(Verdict.APPROVED)
    """
    
    DEFAULT_PATH = Path(__file__).parent / "data" / "golden_dataset.json"
    
    def __init__(self, dataset_path: Optional[Path] = None):
        """
        Initialize loader.
        
        Args:
            dataset_path: Path to golden dataset JSON. Uses default if not specified.
        """
        self.dataset_path = dataset_path or self.DEFAULT_PATH
        self._dataset: Optional[GoldenDataset] = None
    
    def load(self) -> GoldenDataset:
        """Load the golden dataset from disk."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Golden dataset not found at {self.dataset_path}. "
                "Run the generation script first."
            )
        
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._dataset = GoldenDataset(**data)
        logger.info(f"Loaded golden dataset v{self._dataset.version}: {self._dataset.stats}")
        return self._dataset
    
    @property
    def dataset(self) -> GoldenDataset:
        """Get loaded dataset, loading if necessary."""
        if self._dataset is None:
            self.load()
        return self._dataset
    
    def get_claims_for_test(self, test_category: str) -> List[AnnotatedClaim]:
        """Get claims designated for a specific test category."""
        return [
            claim for claim in self.dataset.annotated_claims
            if test_category in claim.test_categories
        ]
    
    def get_claims_by_verdict(self, verdict: Verdict) -> List[AnnotatedClaim]:
        """Get claims with a specific expected verdict."""
        return [
            claim for claim in self.dataset.annotated_claims
            if claim.expected_verdict == verdict
        ]
    
    def get_edge_cases(self) -> List[AnnotatedClaim]:
        """Get all edge case claims."""
        return [
            claim for claim in self.dataset.annotated_claims
            if claim.is_edge_case
        ]
    
    def get_claims_by_pillar(self, pillar_name: str) -> List[AnnotatedClaim]:
        """Get claims for a specific pillar."""
        return [
            claim for claim in self.dataset.annotated_claims
            if pillar_name in claim.correct_pillar
        ]
    
    def get_high_confidence_claims(self) -> List[AnnotatedClaim]:
        """Get claims with high annotator confidence."""
        return [
            claim for claim in self.dataset.annotated_claims
            if claim.verdict_confidence.value == "high"
        ]
    
    def get_calibration_data(self) -> List[tuple]:
        """
        Get data for calibration analysis.
        
        Returns:
            List of (predicted_probability, actual_outcome) tuples
            where outcome is 1 for approved, 0 for rejected.
        """
        calibration_data = []
        
        for claim in self.dataset.annotated_claims:
            # Find matching verdict entry
            verdict_entry = next(
                (v for v in self.dataset.expected_verdicts if v.claim_id == claim.claim_id),
                None
            )
            
            if verdict_entry:
                probability = verdict_entry.true_positive_probability
                outcome = 1 if claim.expected_verdict == Verdict.APPROVED else 0
                calibration_data.append((probability, outcome))
        
        return calibration_data
    
    def get_gap_test_cases(self) -> List[KnownGap]:
        """Get all known gap test cases."""
        return self.dataset.known_gaps
    
    def get_recommendation_test_cases(self) -> List[RecommendationQuality]:
        """Get recommendation quality test cases."""
        return self.dataset.recommendation_quality
    
    def validate_dataset(self) -> Dict[str, Any]:
        """
        Validate dataset integrity.
        
        Returns:
            Validation report with any issues found.
        """
        issues = []
        
        # Check for duplicate claim IDs
        claim_ids = [c.claim_id for c in self.dataset.annotated_claims]
        duplicates = [id for id in claim_ids if claim_ids.count(id) > 1]
        if duplicates:
            issues.append(f"Duplicate claim IDs: {set(duplicates)}")
        
        # Check verdict entries match claims
        claim_id_set = set(claim_ids)
        for verdict in self.dataset.expected_verdicts:
            if verdict.claim_id not in claim_id_set:
                issues.append(f"Verdict references unknown claim: {verdict.claim_id}")
        
        # Check minimum dataset sizes (these are advisory for sample datasets)
        stats = self.dataset.stats
        if stats["total_claims"] < 50:
            issues.append(f"Insufficient claims: {stats['total_claims']} < 50 minimum")
        if stats["total_gaps"] < 20:
            issues.append(f"Insufficient gaps: {stats['total_gaps']} < 20 minimum")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "stats": stats
        }


def check_golden_dataset_available() -> bool:
    """Check if golden dataset is available for testing."""
    loader = GoldenDatasetLoader()
    return loader.dataset_path.exists()


def requires_golden_dataset(func):
    """Decorator to skip test if golden dataset not available."""
    import pytest
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not check_golden_dataset_available():
            pytest.skip("Golden dataset not available")
        return func(*args, **kwargs)
    
    return wrapper
