"""
Anchor Paper Schema Extensions

Extended Pydantic models for exhaustive anchor paper annotation.
"""

from pydantic import BaseModel, Field, computed_field
from typing import List, Optional, Literal, Dict, Any, Tuple
from datetime import datetime
from enum import Enum


class Extractability(str, Enum):
    """Claim extractability classification."""
    HIGH = "high"        # MUST be extracted
    MEDIUM = "medium"    # SHOULD be extracted
    LOW = "low"          # BONUS if extracted
    IRRELEVANT = "irrelevant"  # Must NOT be extracted


class DetectionSeverity(str, Enum):
    """Severity if expected behavior not met."""
    CRITICAL_ERROR = "critical_error"
    ERROR = "error"
    WARNING = "warning"
    ACCEPTABLE = "acceptable"


class ClaimLocation(BaseModel):
    """Precise claim location in paper."""
    page: int = Field(..., ge=1)
    paragraph: int = Field(..., ge=1)
    sentence: Optional[int] = None
    section: Optional[str] = None


class ExhaustiveClaim(BaseModel):
    """
    A claim from exhaustive anchor paper annotation.
    
    Unlike standard claims, exhaustive claims include extractability
    classification and explicit expectations for pipeline behavior.
    """
    
    claim_id: str = Field(..., pattern=r'^AP-\d{3}-C\d{2,3}$')
    location: ClaimLocation
    exact_text: str = Field(..., min_length=10)
    paraphrased_text: Optional[str] = None
    
    # Classification
    claim_type: Literal["quantitative", "qualitative", "methodology", 
                        "conclusion", "comparison", "future_work"]
    
    # Extractability
    extractability: Extractability
    extractability_rationale: str
    
    # Expected Extraction Behavior
    expected_to_be_extracted: bool
    if_not_extracted_severity: DetectionSeverity = DetectionSeverity.WARNING
    if_extracted_when_irrelevant_severity: DetectionSeverity = DetectionSeverity.ERROR
    
    # Expected Mapping (if should be extracted)
    expected_pillar: Optional[str] = None
    expected_requirement: Optional[str] = None
    expected_sub_requirement: Optional[str] = None
    mapping_confidence: Optional[Literal["high", "medium", "low"]] = None
    
    # Expected Verdict (if should be extracted)
    expected_verdict: Optional[Literal["approved", "rejected", "borderline"]] = None
    expected_composite_range: Optional[Tuple[float, float]] = None
    verdict_confidence: Optional[Literal["high", "medium", "low"]] = None
    
    # Annotation Metadata
    found_by_annotator_a: bool = True
    found_by_annotator_b: bool = True
    reconciliation_notes: Optional[str] = None


class NonExtractionItem(BaseModel):
    """
    Content that should NOT be extracted (false positive test).
    """
    
    item_id: str = Field(..., pattern=r'^AP-\d{3}-NE-\d{2,3}$')
    location: ClaimLocation
    item_text: str
    item_type: Literal["future_work", "background", "opinion", 
                       "related_work", "off_topic", "definition"]
    
    reason_not_relevant: str
    if_extracted_severity: DetectionSeverity = DetectionSeverity.ERROR


class AnchorPaper(BaseModel):
    """
    Real paper with exhaustive claim annotation.
    
    Anchor papers receive full bi-directional annotation for
    ground-truth extraction validation.
    """
    
    # Identification
    paper_id: str = Field(..., pattern=r'^AP-\d{3}$')
    source_paper_id: str  # Link to paper registry
    paper_file: str
    
    # Metadata
    title: str
    authors: List[str]
    year: int
    venue: str
    domain: str
    page_count: int
    
    # Exhaustive Claim Inventory
    claim_inventory: List[ExhaustiveClaim] = Field(default_factory=list)
    non_extraction_items: List[NonExtractionItem] = Field(default_factory=list)
    
    # Annotation Metadata
    primary_annotator: str
    secondary_annotator: str
    annotation_date: datetime
    reconciliation_date: Optional[datetime] = None
    inter_rater_agreement: float = Field(..., ge=0.0, le=1.0)
    reconciliation_notes: str = ""
    
    @computed_field
    @property
    def stats(self) -> Dict[str, Any]:
        """Calculate annotation statistics."""
        claims = self.claim_inventory
        return {
            "total_claims": len(claims),
            "high_extractability": sum(1 for c in claims if c.extractability == Extractability.HIGH),
            "medium_extractability": sum(1 for c in claims if c.extractability == Extractability.MEDIUM),
            "low_extractability": sum(1 for c in claims if c.extractability == Extractability.LOW),
            "irrelevant": sum(1 for c in claims if c.extractability == Extractability.IRRELEVANT),
            "non_extraction_items": len(self.non_extraction_items),
            "expected_approved": sum(1 for c in claims if c.expected_verdict == "approved"),
            "expected_rejected": sum(1 for c in claims if c.expected_verdict == "rejected"),
            "expected_borderline": sum(1 for c in claims if c.expected_verdict == "borderline"),
            "both_annotators_found": sum(1 for c in claims if c.found_by_annotator_a and c.found_by_annotator_b),
            "single_annotator_only": sum(1 for c in claims if c.found_by_annotator_a != c.found_by_annotator_b),
        }
    
    def get_must_find_claims(self) -> List[ExhaustiveClaim]:
        """Claims that MUST be extracted (validation errors if missed)."""
        return [c for c in self.claim_inventory 
                if c.extractability == Extractability.HIGH and c.expected_to_be_extracted]
    
    def get_should_not_extract(self) -> List[NonExtractionItem]:
        """Items that should NOT be extracted (false positive tests)."""
        return self.non_extraction_items


class GapScenarioPaper(BaseModel):
    """Paper within a gap scenario."""
    paper_id: str
    provides_coverage: List[Dict[str, Any]] = Field(default_factory=list)


class DecoyPaper(BaseModel):
    """Paper that should NOT contribute to gaps."""
    paper_id: str
    should_not_close: List[str]  # Requirement IDs
    reason: str
    if_contributes_severity: DetectionSeverity = DetectionSeverity.ERROR


class ExpectedGap(BaseModel):
    """Gap expected to be detected."""
    requirement_id: str
    expected_severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    expected_completeness: float = Field(..., ge=0, le=100)
    must_be_detected: bool = True
    if_not_detected_severity: DetectionSeverity = DetectionSeverity.ERROR


class ExpectedNonGap(BaseModel):
    """Requirement that should NOT be flagged as a gap."""
    requirement_id: str
    current_completeness: float = Field(..., ge=0, le=100)
    reason: str
    if_flagged_as_gap_severity: DetectionSeverity = DetectionSeverity.ERROR


class GapScenario(BaseModel):
    """
    Controlled gap detection scenario.
    
    Tests gap detection accuracy with known database states.
    """
    
    scenario_id: str = Field(..., pattern=r'^GAP-\d{3}$')
    scenario_name: str
    scenario_type: Literal["single_pass", "iterative", "edge_case"]
    
    # Pass 1: Initial State
    initial_papers: List[GapScenarioPaper] = Field(default_factory=list)
    expected_gaps: List[ExpectedGap] = Field(default_factory=list)
    expected_non_gaps: List[ExpectedNonGap] = Field(default_factory=list)
    
    # Pass 2: Gap Closing (for iterative scenarios)
    gap_closing_papers: List[GapScenarioPaper] = Field(default_factory=list)
    decoy_papers: List[DecoyPaper] = Field(default_factory=list)
    
    # Expected Final State
    expected_final_coverage: Dict[str, float] = Field(default_factory=dict)
    expected_severity_changes: Dict[str, str] = Field(default_factory=dict)
    
    # Annotation
    designer: str
    design_date: datetime
    validated: bool = False
    validation_notes: Optional[str] = None


class MatchResult(BaseModel):
    """Result of matching extracted claims to ground truth."""
    true_positives: List[Tuple[Dict[str, Any], str]] = Field(default_factory=list)  # (extracted, ground_truth_id) pairs
    false_positives: List[Dict[str, Any]] = Field(default_factory=list)  # Extracted with no match
    false_negatives: List[str] = Field(default_factory=list)  # HIGH extractability claim_ids not matched
    acceptable_misses: List[str] = Field(default_factory=list)  # LOW extractability claim_ids not matched
    
    @computed_field
    @property
    def precision(self) -> float:
        """Extraction precision: TP / (TP + FP)."""
        tp = len(self.true_positives)
        fp = len(self.false_positives)
        return tp / (tp + fp) if (tp + fp) > 0 else 0.0
    
    @computed_field
    @property
    def recall(self) -> float:
        """Extraction recall: TP / (TP + FN)."""
        tp = len(self.true_positives)
        fn = len(self.false_negatives)
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    @computed_field
    @property
    def f1(self) -> float:
        """F1 score: 2 * P * R / (P + R)."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


class ScenarioResult(BaseModel):
    """Result of executing a gap scenario."""
    scenario_id: str
    pass_1_gaps_detected: List[str] = Field(default_factory=list)
    pass_1_false_gaps: List[str] = Field(default_factory=list)  # Non-gaps flagged as gaps
    pass_1_missed_gaps: List[str] = Field(default_factory=list)  # Expected gaps not detected
    pass_2_severity_changes: Dict[str, str] = Field(default_factory=dict)
    pass_2_decoy_contributions: List[str] = Field(default_factory=list)  # Should be empty
    passed: bool = False
    failure_reasons: List[str] = Field(default_factory=list)
