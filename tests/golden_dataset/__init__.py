"""
Golden Dataset Package

Provides schemas, loaders, and utilities for golden dataset validation testing.
"""

from .schema import (
    Verdict,
    ConfidenceLevel,
    EvidenceQualityAnnotation,
    AnnotatedClaim,
    ExpectedVerdict,
    KnownGap,
    RecommendationQuality,
    GoldenDataset,
)
from .loader import (
    GoldenDatasetLoader,
    check_golden_dataset_available,
    requires_golden_dataset,
)

__all__ = [
    # Schema exports
    "Verdict",
    "ConfidenceLevel",
    "EvidenceQualityAnnotation",
    "AnnotatedClaim",
    "ExpectedVerdict",
    "KnownGap",
    "RecommendationQuality",
    "GoldenDataset",
    # Loader exports
    "GoldenDatasetLoader",
    "check_golden_dataset_available",
    "requires_golden_dataset",
]
