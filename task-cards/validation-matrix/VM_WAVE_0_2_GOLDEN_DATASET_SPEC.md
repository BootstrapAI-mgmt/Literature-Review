# Task Card: Golden Dataset Specification

**Task ID:** VM-W0-2  
**Wave:** 0 (Infrastructure Foundation)  
**Priority:** CRITICAL  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** None (parallel with VM-W0-1)  
**Blocks:** VM-W1-4, VM-W2-1, VM-W2-2, VM-W2.5-2, VM-W4-2

---

## Objective

Define comprehensive specifications for a golden dataset that serves as ground truth for accuracy validation, calibration testing, quality benchmarks, and output quality validation. This dataset will enable reproducible accuracy measurements across the entire pipeline.

## Background

The third-party assessment identified a **critical gap**: no golden dataset infrastructure exists for accuracy testing. The validation matrix requires:

- **AV-01/AV-02**: Claim extraction precision/recall vs. ground truth
- **AV-03**: Judge accuracy vs. human-annotated verdicts
- **AV-04**: Judge calibration (Brier score)
- **AV-08**: Correlation with human ratings
- **QB-01→05**: Quality benchmarks against known-correct data

A golden dataset provides the reference standard for all these measurements.

## Success Criteria

- [ ] Golden dataset requirements document complete
- [ ] JSON schema for annotated claims defined
- [ ] JSON schema for expected verdicts defined
- [ ] JSON schema for known gaps defined
- [ ] Human annotation guidelines document created
- [ ] Golden dataset generation script skeleton implemented
- [ ] Sample golden dataset entries created (5 examples)
- [ ] Validation of schema with Pydantic models

---

## Deliverables

### 1. Golden Dataset Requirements Document

**File:** `docs/GOLDEN_DATASET_REQUIREMENTS.md`

```markdown
# Golden Dataset Requirements

## Purpose

The golden dataset provides human-verified ground truth data for:
1. **Accuracy Testing** - Measuring precision, recall, and F1 scores
2. **Calibration Analysis** - Validating confidence score reliability
3. **Regression Detection** - Ensuring model updates don't degrade quality
4. **Quality Benchmarking** - Establishing quality baselines

## Dataset Components

### 1. Annotated Claims (50+ samples)
Human-labeled claims from research papers with:
- Correct pillar assignment
- Correct sub-requirement mapping
- Evidence quality scores (1-5 scale)
- Expected verdict (approve/reject)
- Confidence level for the expected verdict

### 2. Evidence Quality Ratings (100+ samples)
Human-rated evidence with:
- Strength score (1-5)
- Rigor score (1-5)
- Relevance score (1-5)
- Directness rating (1-3)
- Reproducibility score (1-5)
- Overall composite assessment

### 3. Pillar Mapping Ground Truth (100+ samples)
Claims with verified pillar/requirement mappings:
- Paper context
- Claim text
- Correct pillar
- Correct requirement
- Correct sub-requirement
- Rationale for mapping

### 4. Known Gaps (20+ samples)
Deliberately constructed database states with known gaps:
- Input database state
- Pillar definitions
- Expected gaps identified
- Severity classifications

### 5. Recommendation Quality (10+ samples)
Gaps with expert-recommended solutions:
- Gap description
- Expected recommendation themes
- Quality rating criteria

### 6. Search Suggestion Ground Truth (15+ samples) *(Added for Wave 2.5)*
Validated search suggestions for RA-01/RA-02 testing:
- Gap with known solution papers
- Expected search queries that would find solutions
- Human-validated priority ranking
- Expected source databases (arxiv, ieee, etc.)
- Relevance match criteria

### 7. Output Sample Collection (5+ complete runs) *(Added for Wave 2.5)*
Complete pipeline output snapshots for OQ-* validation:
- gap_analysis_report.json with verified content
- executive_summary.md with all required sections
- suggested_searches.json/md pairs
- proof_chain.json with verified links
- Evidence enhancement files (triangulation, decay, sufficiency)

## Annotation Standards

### Inter-Rater Reliability
- Minimum 2 independent annotators per sample
- Cohen's Kappa > 0.7 required for inclusion
- Disagreements resolved by third annotator

### Annotator Qualifications
- PhD or equivalent research experience
- Domain expertise in neuromorphic computing OR
- Extensive literature review experience

### Quality Assurance
- 10% of samples re-annotated for consistency
- Systematic bias checks across annotators
- Quarterly dataset review and refresh

## Versioning

- Semantic versioning (MAJOR.MINOR.PATCH)
- MAJOR: Schema changes or >20% content change
- MINOR: New samples added, annotations updated
- PATCH: Error corrections

## Storage & Access

- Location: `tests/golden_dataset/data/`
- Format: JSON with schema validation
- Version controlled with Git LFS for large files
```

### 2. Annotated Claim Schema

**File:** `tests/golden_dataset/schema.py`

```python
"""
Golden Dataset Schemas

Pydantic models for golden dataset validation.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Literal
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
    annotator_ids: List[str] = Field(..., min_items=1)
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
    
    class Config:
        json_schema_extra = {
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


class ExpectedVerdict(BaseModel):
    """
    Expected judge verdict for a claim.
    
    Used for testing judge decision accuracy.
    """
    
    claim_id: str = Field(..., pattern=r'^GD-CLM-\d{4}$')
    expected_verdict: Verdict
    expected_composite_score_range: tuple[float, float] = Field(
        ...,
        description="Expected composite score range (min, max)"
    )
    expected_strength_range: tuple[int, int]
    expected_relevance_range: tuple[int, int]
    
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
        min_items=1,
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
    
    # Statistics
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
```

### 3. Annotation Guidelines

**File:** `docs/GOLDEN_DATASET_ANNOTATION_GUIDELINES.md`

```markdown
# Golden Dataset Annotation Guidelines

## Overview

This document provides guidelines for annotating claims, evidence, and verdicts
for the Literature Review golden dataset. Consistent annotation is critical for
accurate validation testing.

## Claim Annotation Process

### Step 1: Read the Full Paper Context
- Read at least 2 pages around the claim
- Understand the paper's methodology
- Note the publication date and venue

### Step 2: Evaluate Claim-Requirement Mapping
1. Read the claim text carefully
2. Review all pillar definitions
3. Select the BEST matching pillar (primary topic)
4. Select the specific requirement
5. Select the sub-requirement
6. Document your rationale

**Mapping Rules:**
- If claim spans multiple pillars, choose the PRIMARY one
- If uncertain, mark as edge case
- Never force a mapping - mark as "unmappable" if no fit

### Step 3: Evaluate Evidence Quality

Rate each dimension independently:

#### Strength (1-5)
- 5: Direct experimental proof with statistical significance
- 4: Strong quantitative data with clear methodology
- 3: Good qualitative or limited quantitative evidence
- 2: Weak or indirect evidence
- 1: Anecdotal or unsupported claims

#### Rigor (1-5)
- 5: Peer-reviewed, replicated, validated methodology
- 4: Peer-reviewed with sound methodology
- 3: Reasonable methodology, minor issues
- 2: Methodology concerns or limited description
- 1: No methodology described or major flaws

#### Relevance (1-5)
- 5: Directly addresses the sub-requirement
- 4: Strongly related to the sub-requirement
- 3: Moderately relevant
- 2: Tangentially related
- 1: Not relevant

#### Directness (1-3)
- 3: Direct evidence (first-hand experimental results)
- 2: Indirect evidence (derived or secondary analysis)
- 1: Tertiary evidence (citations, reviews)

#### Reproducibility (1-5)
- 5: Complete code/data available, fully reproducible
- 4: Detailed methodology, could be reproduced
- 3: Moderate detail, reproduction possible with effort
- 2: Limited details, reproduction difficult
- 1: Cannot be reproduced

### Step 4: Determine Expected Verdict

Apply the Judge's criteria:
- **APPROVE** if: composite ≥ 3.0 AND strength ≥ 3 AND relevance ≥ 3
- **REJECT** if: criteria not met
- **BORDERLINE** if: composite between 2.8-3.2 (for calibration)

Document your confidence:
- **HIGH**: 90%+ confident in verdict
- **MEDIUM**: 70-90% confident
- **LOW**: 50-70% confident

### Step 5: Identify Edge Cases

Flag as edge case if:
- Mapping is ambiguous
- Evidence quality is borderline
- Multiple reasonable interpretations exist
- Technical domain knowledge required
- Claim is unusually complex

## Quality Assurance

### Self-Check
Before submitting, verify:
- [ ] All fields are completed
- [ ] Rationales are clear and specific
- [ ] Scores are justified
- [ ] Verdict matches score thresholds
- [ ] Edge cases are flagged

### Disagreement Resolution
When annotators disagree:
1. Document both perspectives
2. Third annotator reviews independently
3. Majority vote determines final
4. Significant disagreements trigger discussion
5. Unresolvable cases marked as edge cases

## Examples

### Example 1: Clear Approval
```json
{
  "claim_text": "Our SNN achieved 98.2% accuracy on DVS gesture recognition",
  "evidence_text": "Table 3: Cross-validation results (n=10) show 98.2% ± 0.4%",
  "expected_verdict": "approved",
  "evidence_quality": {
    "strength_score": 5,
    "rigor_score": 4,
    "relevance_score": 5,
    "directness": 3,
    "reproducibility_score": 4
  },
  "verdict_rationale": "Clear quantitative results with proper validation"
}
```

### Example 2: Clear Rejection
```json
{
  "claim_text": "Neuromorphic systems are more efficient",
  "evidence_text": "As commonly known in the field...",
  "expected_verdict": "rejected",
  "evidence_quality": {
    "strength_score": 1,
    "rigor_score": 1,
    "relevance_score": 3,
    "directness": 1,
    "reproducibility_score": 1
  },
  "verdict_rationale": "No quantitative evidence, unsupported assertion"
}
```

### Example 3: Borderline Case
```json
{
  "claim_text": "Our chip shows promise for real-time processing",
  "evidence_text": "Preliminary tests indicate sub-10ms latency",
  "expected_verdict": "borderline",
  "evidence_quality": {
    "strength_score": 3,
    "rigor_score": 3,
    "relevance_score": 3,
    "directness": 2,
    "reproducibility_score": 2
  },
  "verdict_rationale": "Composite ~3.0, on threshold boundary"
}
```
```

### 4. Golden Dataset Loader

**File:** `tests/golden_dataset/loader.py`

```python
"""
Golden Dataset Loader

Utilities for loading and working with the golden dataset.
"""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

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
    
    def get_calibration_data(self) -> List[tuple[float, int]]:
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
        
        # Check minimum dataset sizes
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


# Pytest skip decorator for tests requiring golden dataset
def requires_golden_dataset(func):
    """Decorator to skip test if golden dataset not available."""
    import pytest
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not check_golden_dataset_available():
            pytest.skip("Golden dataset not available")
        return func(*args, **kwargs)
    
    return wrapper
```

### 5. Sample Golden Dataset

**File:** `tests/golden_dataset/data/golden_dataset_sample.json`

```json
{
  "version": "0.1.0",
  "created_date": "2025-12-31T00:00:00Z",
  "last_updated": "2025-12-31T00:00:00Z",
  "description": "Sample golden dataset for development and testing. Replace with full dataset.",
  "annotated_claims": [
    {
      "claim_id": "GD-CLM-0001",
      "dataset_version": "0.1.0",
      "source_paper": "sample_neuromorphic_2024.pdf",
      "source_page": 5,
      "source_section": "Results",
      "claim_text": "The spiking neural network achieved 95% accuracy on MNIST classification using only 1mW power.",
      "evidence_text": "Figure 3 shows classification accuracy of 95.2% ± 0.3% across 10 trials, with power consumption measured at 0.98mW.",
      "correct_pillar": "Pillar 1: Biological Stimulus-Response",
      "correct_requirement": "REQ-B1.1",
      "correct_sub_requirement": "Sub-1.1.1",
      "mapping_rationale": "Demonstrates sensory encoding and classification capability with clear quantitative evidence.",
      "expected_verdict": "approved",
      "verdict_rationale": "Strong quantitative evidence with statistical measures and reproducible methodology.",
      "verdict_confidence": "high",
      "evidence_quality": {
        "strength_score": 4,
        "rigor_score": 4,
        "relevance_score": 5,
        "directness": 3,
        "reproducibility_score": 4,
        "recency_bonus": 0.8,
        "rationale": "Clear quantitative results with error bars, multiple trials, and power measurements."
      },
      "annotator_ids": ["dev_annotator"],
      "annotation_date": "2025-12-31T00:00:00Z",
      "inter_rater_agreement": null,
      "test_categories": ["precision", "judge_accuracy", "pillar_mapping"],
      "is_edge_case": false,
      "edge_case_type": null
    },
    {
      "claim_id": "GD-CLM-0002",
      "dataset_version": "0.1.0",
      "source_paper": "sample_review_2023.pdf",
      "source_page": 12,
      "source_section": "Discussion",
      "claim_text": "Neuromorphic systems are generally more energy-efficient than traditional computing.",
      "evidence_text": "As is well-known in the field, neuromorphic approaches offer efficiency advantages.",
      "correct_pillar": "Pillar 1: Biological Stimulus-Response",
      "correct_requirement": "REQ-B1.4",
      "correct_sub_requirement": "Sub-1.4.1",
      "mapping_rationale": "Relates to efficiency claims but lacks specific evidence.",
      "expected_verdict": "rejected",
      "verdict_rationale": "No quantitative evidence provided. Relies on general assertion without data.",
      "verdict_confidence": "high",
      "evidence_quality": {
        "strength_score": 1,
        "rigor_score": 1,
        "relevance_score": 3,
        "directness": 1,
        "reproducibility_score": 1,
        "recency_bonus": 0.0,
        "rationale": "No methodology, no data, purely assertion-based claim."
      },
      "annotator_ids": ["dev_annotator"],
      "annotation_date": "2025-12-31T00:00:00Z",
      "inter_rater_agreement": null,
      "test_categories": ["recall", "false_approval_prevention"],
      "is_edge_case": false,
      "edge_case_type": null
    },
    {
      "claim_id": "GD-CLM-0003",
      "dataset_version": "0.1.0",
      "source_paper": "sample_stdp_2024.pdf",
      "source_page": 8,
      "source_section": "Methods",
      "claim_text": "Our STDP implementation shows timing-dependent weight changes.",
      "evidence_text": "Preliminary experiments suggest weight modifications occur, though statistical analysis is ongoing.",
      "correct_pillar": "Pillar 1: Biological Stimulus-Response",
      "correct_requirement": "REQ-B1.4",
      "correct_sub_requirement": "Sub-1.4.2",
      "mapping_rationale": "Directly addresses STDP mechanisms.",
      "expected_verdict": "borderline",
      "verdict_rationale": "Evidence exists but is incomplete. Composite score expected around threshold.",
      "verdict_confidence": "medium",
      "evidence_quality": {
        "strength_score": 3,
        "rigor_score": 2,
        "relevance_score": 4,
        "directness": 2,
        "reproducibility_score": 2,
        "recency_bonus": 0.8,
        "rationale": "Relevant but preliminary results without statistical validation."
      },
      "annotator_ids": ["dev_annotator"],
      "annotation_date": "2025-12-31T00:00:00Z",
      "inter_rater_agreement": null,
      "test_categories": ["calibration", "borderline"],
      "is_edge_case": true,
      "edge_case_type": "borderline_evidence"
    }
  ],
  "expected_verdicts": [
    {
      "claim_id": "GD-CLM-0001",
      "expected_verdict": "approved",
      "expected_composite_score_range": [3.5, 4.5],
      "expected_strength_range": [4, 5],
      "expected_relevance_range": [4, 5],
      "true_positive_probability": 0.95,
      "rejection_reasons": []
    },
    {
      "claim_id": "GD-CLM-0002",
      "expected_verdict": "rejected",
      "expected_composite_score_range": [1.0, 2.0],
      "expected_strength_range": [1, 2],
      "expected_relevance_range": [2, 4],
      "true_positive_probability": 0.05,
      "rejection_reasons": ["Insufficient evidence strength", "No quantitative data"]
    },
    {
      "claim_id": "GD-CLM-0003",
      "expected_verdict": "borderline",
      "expected_composite_score_range": [2.7, 3.3],
      "expected_strength_range": [2, 4],
      "expected_relevance_range": [3, 5],
      "true_positive_probability": 0.50,
      "rejection_reasons": ["Preliminary results", "Statistical analysis incomplete"]
    }
  ],
  "known_gaps": [
    {
      "gap_id": "GD-GAP-0001",
      "dataset_version": "0.1.0",
      "pillar": "Pillar 2: Neuromorphic Implementation",
      "requirement_id": "REQ-N2.1",
      "sub_requirement_id": "Sub-2.1.3",
      "requirement_text": "Hardware implementation of temporal coding mechanisms",
      "current_completeness": 15.0,
      "expected_severity": "CRITICAL",
      "database_state_file": "gap_test_states/gap_0001_state.json",
      "why_is_gap": "No papers in database address temporal coding hardware implementation.",
      "expected_in_report": true
    }
  ],
  "recommendation_quality": [
    {
      "gap_id": "GD-GAP-0001",
      "expected_recommendation_themes": [
        "temporal coding",
        "hardware implementation",
        "spike timing",
        "neuromorphic chip"
      ],
      "expected_minimum_rating": 4,
      "reference_recommendation": "Search for papers on temporal coding circuits in neuromorphic hardware, particularly implementations on Intel Loihi or IBM TrueNorth platforms."
    }
  ]
}
```

---

## Implementation Steps

### Step 1: Create Schema (2 hours)
1. Create `tests/golden_dataset/schema.py` with Pydantic models
2. Validate schema with sample data
3. Add JSON export capability

### Step 2: Create Annotation Guidelines (2 hours)
1. Write detailed annotation guidelines document
2. Create example annotations
3. Define quality assurance process

### Step 3: Create Loader Utility (2 hours)
1. Implement `GoldenDatasetLoader` class
2. Add query methods for different test types
3. Implement validation checks

### Step 4: Create Sample Dataset (1.5 hours)
1. Create 5 sample annotated claims
2. Include approved, rejected, and borderline examples
3. Create 1 known gap sample
4. Validate against schema

### Step 5: Documentation (0.5 hours)
1. Create README in golden_dataset directory
2. Document usage patterns
3. Link to annotation guidelines

---

## Testing

```python
# tests/golden_dataset/test_schema.py

import pytest
from datetime import datetime
from .schema import (
    AnnotatedClaim,
    EvidenceQualityAnnotation,
    GoldenDataset,
    Verdict
)
from .loader import GoldenDatasetLoader


class TestGoldenDatasetSchema:
    """Test golden dataset schema validation."""
    
    @pytest.mark.unit
    def test_annotated_claim_creation(self):
        """Test AnnotatedClaim model."""
        claim = AnnotatedClaim(
            claim_id="GD-CLM-0001",
            dataset_version="1.0.0",
            source_paper="test.pdf",
            claim_text="Test claim text for validation",
            evidence_text="Test evidence text for validation",
            correct_pillar="Pillar 1: Test",
            correct_requirement="REQ-T1.1",
            correct_sub_requirement="Sub-1.1.1",
            mapping_rationale="Test rationale",
            expected_verdict=Verdict.APPROVED,
            verdict_rationale="Test verdict rationale",
            verdict_confidence="high",
            evidence_quality=EvidenceQualityAnnotation(
                strength_score=4,
                rigor_score=4,
                relevance_score=4,
                directness=3,
                reproducibility_score=4,
                rationale="Test evidence rationale"
            ),
            annotator_ids=["test_annotator"],
            annotation_date=datetime.now()
        )
        
        assert claim.claim_id == "GD-CLM-0001"
        assert claim.expected_verdict == Verdict.APPROVED
    
    @pytest.mark.unit
    def test_evidence_composite_score(self):
        """Test composite score calculation."""
        evidence = EvidenceQualityAnnotation(
            strength_score=4,
            rigor_score=4,
            relevance_score=4,
            directness=3,
            reproducibility_score=4,
            recency_bonus=0.8,
            rationale="Test"
        )
        
        # Expected: 4*0.30 + 4*0.25 + 4*0.25 + 1*0.10 + 0.8*0.05 + 4*0.05
        # = 1.2 + 1.0 + 1.0 + 0.1 + 0.04 + 0.2 = 3.54
        assert 3.5 <= evidence.composite_score <= 3.6
    
    @pytest.mark.unit
    def test_claim_id_pattern(self):
        """Test claim ID pattern validation."""
        with pytest.raises(ValueError):
            AnnotatedClaim(
                claim_id="invalid-id",  # Should match GD-CLM-NNNN
                # ... other required fields
            )
```

---

## Acceptance Criteria Checklist

- [ ] Golden dataset requirements document complete
- [ ] `AnnotatedClaim` Pydantic model validates correctly
- [ ] `ExpectedVerdict` Pydantic model validates correctly
- [ ] `KnownGap` Pydantic model validates correctly
- [ ] Annotation guidelines document is comprehensive
- [ ] `GoldenDatasetLoader` loads and queries dataset
- [ ] Sample dataset validates against schema
- [ ] Schema tests pass
- [ ] Documentation is complete

---

## Related Tasks

- **Parallel:** VM-W0-1 (Test Infrastructure)
- **Next:** VM-W1-4 (Golden Dataset Creation)
- **Enables:** VM-W2-1, VM-W2-2, VM-W4-2

---

## Notes

- Start with minimal viable dataset (50 claims) and expand iteratively
- Prioritize high-confidence annotations for initial testing
- Consider using domain experts for annotation quality
- Plan for quarterly dataset updates and version increments
