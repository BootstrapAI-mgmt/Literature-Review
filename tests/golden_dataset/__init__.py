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
from .schema_anchor import (
    Extractability,
    DetectionSeverity,
    ClaimLocation,
    ExhaustiveClaim,
    NonExtractionItem,
    AnchorPaper,
    GapScenarioPaper,
    DecoyPaper,
    ExpectedGap,
    ExpectedNonGap,
    GapScenario,
    MatchResult,
    ScenarioResult,
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
    # Anchor paper schema exports
    "Extractability",
    "DetectionSeverity",
    "ClaimLocation",
    "ExhaustiveClaim",
    "NonExtractionItem",
    "AnchorPaper",
    "GapScenarioPaper",
    "DecoyPaper",
    "ExpectedGap",
    "ExpectedNonGap",
    "GapScenario",
    "MatchResult",
    "ScenarioResult",
]
