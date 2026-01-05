"""
Golden Dataset Schemas

Pydantic models for golden dataset validation.
"""

from pydantic import BaseModel, Field, field_validator, computed_field
from typing import List, Dict, Optional, Literal, Tuple
from enum import Enum
from datetime import datetime


class Verdict(str, Enum):
    """Expected verdict for a claim."""
    APPROVED = "approved"
    REJECTED = "rejected"
    BORDERLINE = "borderline"  # For calibration testing


class ConfidenceLevel(str, Enum):
    """Annotator confidence in the verdict."""
    HIGH = "high"        # 90%+ confident
    MEDIUM = "medium"    # 70-90% confident
    LOW = "low"          # 50-70% confident


class EvidenceQualityAnnotation(BaseModel):
    """Human-annotated evidence quality scores."""
    
    strength_score: int = Field(..., ge=1, le=5, description="Evidence strength 1-5")
    rigor_score: int = Field(..., ge=1, le=5, description="Methodological rigor 1-5")
    relevance_score: int = Field(..., ge=1, le=5, description="Requirement relevance 1-5")
    directness: int = Field(..., ge=1, le=3, description="Evidence directness 1-3")
    reproducibility_score: int = Field(..., ge=1, le=5, description="Reproducibility 1-5")
    recency_bonus: float = Field(default=0.0, ge=0.0, le=1.0)
    
    rationale: str = Field(..., description="Brief explanation for scores")
    
    @computed_field
    @property
    def composite_score(self) -> float:
        """Calculate composite score using standard weights."""
        return (
            self.strength_score * 0.30 +
            self.rigor_score * 0.25 +
            self.relevance_score * 0.25 +
            (self.directness / 3) * 0.10 +
            self.recency_bonus * 0.05 +
            self.reproducibility_score * 0.05
        )


class AnnotatedClaim(BaseModel):
    """
    A claim with human annotations for ground truth.
    
    This represents a single claim extracted from a paper with
    expert annotations for testing claim extraction, judge decisions,
    and evidence quality assessment.
    """
    
    # Identification
    claim_id: str = Field(..., pattern=r'^GD-CLM-\d{4}$')
    dataset_version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$')
    
    # Source Information
    source_paper: str = Field(..., description="Filename or identifier of source paper")
    source_page: Optional[int] = Field(None, description="Page number if applicable")
    source_section: Optional[str] = Field(None, description="Section name if known")
    
    # Claim Content
    claim_text: str = Field(..., min_length=10)
    evidence_text: str = Field(..., min_length=10)
    
    # Ground Truth Mappings
    correct_pillar: str = Field(..., description="Full pillar name")
    correct_requirement: str = Field(..., description="Requirement ID (e.g., REQ-B1.1)")
    correct_sub_requirement: str = Field(..., description="Sub-requirement ID")
    mapping_rationale: str = Field(..., description="Why this mapping is correct")
    
    # Ground Truth Verdict
    expected_verdict: Verdict
    verdict_rationale: str = Field(..., description="Why this verdict is expected")
    verdict_confidence: ConfidenceLevel
    
    # Evidence Quality Annotations
    evidence_quality: EvidenceQualityAnnotation
    
    # Annotation Metadata
    annotator_ids: List[str] = Field(..., min_length=1)
    annotation_date: datetime
    inter_rater_agreement: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Test Categories
    test_categories: List[str] = Field(
        default_factory=list,
        description="Which tests this sample is designed for: precision, recall, calibration, etc."
    )
    
    # Edge Case Flags
    is_edge_case: bool = Field(default=False)
    edge_case_type: Optional[str] = Field(
        None,
        description="Type of edge case: ambiguous, borderline, multi-pillar, etc."
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "claim_id": "GD-CLM-0001",
                "dataset_version": "1.0.0",
                "source_paper": "neuromorphic_computing_2024.pdf",
                "source_page": 5,
                "source_section": "Results",
                "claim_text": "The spiking neural network achieved 95% accuracy on MNIST classification.",
                "evidence_text": "Figure 3 shows classification accuracy of 95.2% ± 0.3% across 10 trials.",
                "correct_pillar": "Pillar 1: Biological Stimulus-Response",
                "correct_requirement": "REQ-B1.1",
                "correct_sub_requirement": "Sub-1.1.1",
                "mapping_rationale": "Demonstrates sensory encoding capability with quantitative results.",
                "expected_verdict": "approved",
                "verdict_rationale": "Strong quantitative evidence with reproducible methodology.",
                "verdict_confidence": "high",
                "evidence_quality": {
                    "strength_score": 4,
                    "rigor_score": 4,
                    "relevance_score": 5,
                    "directness": 3,
                    "reproducibility_score": 4,
                    "recency_bonus": 0.8,
                    "rationale": "Clear quantitative results with error bars and multiple trials."
                },
                "annotator_ids": ["annotator_001", "annotator_002"],
                "annotation_date": "2025-01-15T10:30:00Z",
                "inter_rater_agreement": 0.95,
                "test_categories": ["precision", "judge_accuracy"],
                "is_edge_case": False
            }
        }
    }


class ExpectedVerdict(BaseModel):
    """
    Expected judge verdict for a claim.
    
    Used for testing judge decision accuracy.
    """
    
    claim_id: str = Field(..., pattern=r'^GD-CLM-\d{4}$')
    expected_verdict: Verdict
    expected_composite_score_range: Tuple[float, float] = Field(
        ...,
        description="Expected composite score range (min, max)"
    )
    expected_strength_range: Tuple[int, int]
    expected_relevance_range: Tuple[int, int]
    
    # For calibration testing
    true_positive_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probability this should be approved (for calibration)"
    )
    
    rejection_reasons: List[str] = Field(
        default_factory=list,
        description="Expected rejection reasons if rejected"
    )


class KnownGap(BaseModel):
    """
    A gap with known correct identification.
    
    Used for testing gap detection completeness.
    """
    
    gap_id: str = Field(..., pattern=r'^GD-GAP-\d{4}$')
    dataset_version: str
    
    # Gap Definition
    pillar: str
    requirement_id: str
    sub_requirement_id: str
    requirement_text: str
    
    # Expected Detection
    current_completeness: float = Field(..., ge=0.0, le=100.0)
    expected_severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    
    # Database State
    database_state_file: str = Field(
        ...,
        description="JSON file with database state for this gap test"
    )
    
    # Verification
    why_is_gap: str = Field(..., description="Explanation of why this is a gap")
    expected_in_report: bool = Field(default=True)


class RecommendationQuality(BaseModel):
    """
    Gap with expected recommendation quality criteria.
    
    Used for testing recommendation relevance (QB-05).
    """
    
    gap_id: str = Field(..., pattern=r'^GD-GAP-\d{4}$')
    
    # Expected Themes
    expected_recommendation_themes: List[str] = Field(
        ...,
        min_length=1,
        description="Keywords/themes expected in good recommendations"
    )
    
    # Quality Criteria
    expected_minimum_rating: int = Field(..., ge=1, le=5)
    
    # Human-Created Reference
    reference_recommendation: str = Field(
        ...,
        description="Expert-written reference recommendation"
    )


class GoldenDataset(BaseModel):
    """
    Complete golden dataset container.
    """
    
    version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$')
    created_date: datetime
    last_updated: datetime
    description: str
    
    # Dataset Contents
    annotated_claims: List[AnnotatedClaim] = Field(default_factory=list)
    expected_verdicts: List[ExpectedVerdict] = Field(default_factory=list)
    known_gaps: List[KnownGap] = Field(default_factory=list)
    recommendation_quality: List[RecommendationQuality] = Field(default_factory=list)
    
    @computed_field
    @property
    def stats(self) -> Dict:
        """Calculate dataset statistics."""
        return {
            "total_claims": len(self.annotated_claims),
            "total_verdicts": len(self.expected_verdicts),
            "total_gaps": len(self.known_gaps),
            "total_recommendations": len(self.recommendation_quality),
            "approved_claims": len([c for c in self.annotated_claims if c.expected_verdict == Verdict.APPROVED]),
            "rejected_claims": len([c for c in self.annotated_claims if c.expected_verdict == Verdict.REJECTED]),
            "borderline_claims": len([c for c in self.annotated_claims if c.expected_verdict == Verdict.BORDERLINE]),
            "edge_cases": len([c for c in self.annotated_claims if c.is_edge_case])
        }
