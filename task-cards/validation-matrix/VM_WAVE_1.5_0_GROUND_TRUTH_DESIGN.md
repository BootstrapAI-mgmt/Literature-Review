# Task Card: Ground Truth Design Validation

**Task ID:** VM-W1.5-0  
**Wave:** 1.5 (Ground Truth Infrastructure)  
**Priority:** CRITICAL (Prerequisite for VM-W1.5-2)  
**Estimated Effort:** 12 hours  
**Status:** Not Started  
**Dependencies:** VM-W1-4  
**Blocks:** VM-W1.5-2, VM-W2-1, VM-W4-2  
**Validation IDs:** Enables all AV-*, FV-07, QB-*, RA-* with ground-truth coverage

---

## Objective

Design and validate the ground truth construction methodology BEFORE creating the full golden dataset. This ensures:

1. **Bi-directional validation** - Tests both "finding correctly" AND "not finding correctly"
2. **Multi-annotator reliability** - Reduces single-annotator bias
3. **Exhaustive annotation protocol** - Captures complete claim inventory from anchor papers
4. **Controlled gap scenarios** - Tests iterative gap-closing behavior
5. **Negative case coverage** - Validates false positive rejection

## Background

The third-party assessment identified a critical structural gap: the current golden dataset approach uses **forward-designed validation** (defining what SHOULD be found), but the pipeline is an **extraction system** that requires **ground-truth validation** (verifying it finds what IS in papers).

### The Fundamental Problem

```
Current Approach (Recognition Test):
  "Can you identify this claim?" (given the answer)

Required Approach (Extraction Test):
  "What claims are in this paper?" (discover the answer)
```

This task card establishes the methodology to create **true ground truth** that validates the pipeline's extraction capability.

---

## Success Criteria

- [ ] Anchor paper selection criteria documented
- [ ] Exhaustive annotation protocol complete with examples
- [ ] Two-annotator reconciliation process defined
- [ ] Inter-rater reliability measurement approach established
- [ ] Gap scenario design template created with 3+ scenarios
- [ ] Decoy paper/claim concept defined with examples
- [ ] Extractability classification scheme complete
- [ ] Pilot annotation of 3-5 anchor papers complete
- [ ] Inter-rater agreement measured (target: Cohen's κ ≥ 0.7)
- [ ] Annotation time estimates validated

---

## Deliverables

### 1. Anchor Paper Selection Criteria

**File:** `tests/golden_dataset/docs/ANCHOR_PAPER_CRITERIA.md`

```markdown
# Anchor Paper Selection Criteria

## Purpose

Anchor papers are real academic papers that receive **exhaustive annotation** -
every extractable claim is documented, classified, and mapped. These provide
true ground truth for extraction validation.

## Selection Criteria

### Required Criteria (All must be met)

| Criterion | Requirement | Rationale |
|-----------|-------------|-----------|
| **Open Access** | CC-BY or equivalent license | Legal compliance |
| **Peer Reviewed** | Published in peer-reviewed venue | Quality assurance |
| **Claim Density** | 10-30 extractable claims | Testable volume |
| **Requirement Coverage** | Covers 3-6 requirements | Mapping diversity |
| **Text Extractable** | Selectable PDF text | Technical requirement |
| **Clear Structure** | Standard IMRAD format | Annotation consistency |
| **Recency** | Published 2020-2025 | Relevance |

### Preferred Criteria (At least 2)

| Criterion | Preference | Rationale |
|-----------|------------|-----------|
| **Quantitative Results** | Contains numerical benchmarks | Strongest evidence type |
| **Methodology Detail** | Complete methods section | Reproducibility testing |
| **Multi-Claim Types** | Mix of strong/weak/borderline | Verdict distribution |
| **Domain Diversity** | Different from other anchors | Cross-domain validation |
| **Available Data/Code** | Open source artifacts | Ground truth verification |

### Anti-Criteria (Disqualifying)

| Criterion | Disqualification |
|-----------|------------------|
| Review/survey paper | Too many indirect claims |
| < 5 pages | Insufficient content |
| Workshop paper only | Quality uncertainty |
| Heavy on figures/tables | Text extraction issues |
| Domain not in registry | Outside scope |

## Target Distribution

| Domain | Anchor Papers | Rationale |
|--------|---------------|-----------|
| Neuromorphic | 2 | Primary domain, most coverage |
| Quantum | 1 | Maximum domain distance |
| Microbiology | 1 | Life sciences representation |
| Climate | 1 | Earth sciences representation |
| Materials/Other | 1 | Additional diversity |
| **Total** | 5-7 | Manageable for exhaustive annotation |

## Candidate Identification Process

1. Review paper registry for papers meeting required criteria
2. Read abstract and methods for each candidate
3. Estimate claim density (target: 10-30 claims)
4. Score against preferred criteria
5. Select diverse set ensuring domain coverage
6. Document selection rationale
```

### 2. Exhaustive Annotation Protocol

**File:** `tests/golden_dataset/docs/EXHAUSTIVE_ANNOTATION_PROTOCOL.md`

```markdown
# Exhaustive Annotation Protocol for Anchor Papers

## Overview

Exhaustive annotation differs from standard annotation:
- **Standard:** Extract 5-8 representative claims per paper
- **Exhaustive:** Document EVERY statement that could be a claim

This creates true ground truth for testing extraction completeness.

## Annotation Phases

### Phase 1: Claim Discovery (Annotator A)

**Goal:** Identify ALL potential claims in the paper

**Process:**
1. Read entire paper sequentially
2. Mark every statement that could be a claim
3. Include uncertain cases (err on side of inclusion)
4. Document location precisely (page, paragraph, sentence)

**What to mark:**
- Quantitative assertions with numerical evidence
- Qualitative assertions with supporting evidence
- Methodology descriptions with specific details
- Conclusions supported by results
- Comparative statements with baselines
- Performance metrics of any kind

**What NOT to mark:**
- Background/introduction context
- Related work summaries (unless comparative)
- Future work statements (mark separately)
- Pure definitions
- Acknowledgments

### Phase 2: Independent Discovery (Annotator B)

**Goal:** Independent claim identification for reliability measurement

**Process:**
- Same as Phase 1, completely independent
- No access to Annotator A's results
- Same paper, same guidelines

### Phase 3: Reconciliation

**Goal:** Create unified exhaustive claim inventory

**Process:**
1. Union both annotators' claims
2. Identify intersection (high confidence)
3. Identify differences (discuss)
4. Categorize each claim:
   - **Intersection:** Both found → High confidence
   - **A only:** Discuss → Accept or reject with rationale
   - **B only:** Discuss → Accept or reject with rationale
5. Document reconciliation decisions

**Agreement Calculation:**
```
Cohen's κ = (P_observed - P_expected) / (1 - P_expected)

P_observed = % of claims both annotators agreed on
P_expected = expected agreement by chance
```

Target: κ ≥ 0.7 (substantial agreement)

### Phase 4: Extractability Classification

**Goal:** Classify each claim by extraction expectation

For each claim in the unified inventory:

| Extractability | Description | Pipeline Expectation |
|----------------|-------------|----------------------|
| **HIGH** | Clear, prominent, well-structured claim | MUST be extracted |
| **MEDIUM** | Valid claim, may require inference | SHOULD be extracted |
| **LOW** | Edge case, technical jargon, embedded | BONUS if extracted |
| **IRRELEVANT** | Off-topic, future work, opinions | Must NOT be extracted |

**Classification Criteria:**

| Factor | High | Medium | Low | Irrelevant |
|--------|------|--------|-----|------------|
| Location | Results, abstract | Methods, discussion | Footnotes, captions | Background |
| Clarity | Explicit claim | Moderate clarity | Requires interpretation | Ambiguous |
| Evidence | Immediate support | Same section | Elsewhere in paper | None |
| Relevance | Core contribution | Supporting result | Tangential | Off-topic |

### Phase 5: Expected Behavior Documentation

For each claim, document:

```yaml
claim_id: "AP-001-C01"
claim_text: "We achieved 95.2% accuracy..."
location:
  page: 5
  paragraph: 2
  sentence: 1
extractability: "high"
extractability_rationale: "Clear quantitative result in Results section"

expected_extraction:
  should_be_extracted: true
  if_not_extracted_severity: "error"  # error, warning, acceptable
  
expected_mapping:
  pillar: "Pillar 1: Biological Stimulus-Response"
  requirement: "REQ-B1.1"
  sub_requirement: "Sub-1.1.1"
  mapping_confidence: "high"  # high, medium, low
  
expected_verdict:
  verdict: "approved"
  composite_score_range: [3.5, 4.5]
  confidence: "high"
```

### Phase 6: Non-Extraction Documentation

For each IRRELEVANT item:

```yaml
item_id: "AP-001-NE-01"
item_text: "Future work will explore..."
location:
  page: 10
  paragraph: 4
item_type: "future_work"

expected_behavior:
  should_be_extracted: false
  if_extracted_severity: "error"  # false positive
  reason_not_relevant: "Future work statement, not a current finding"
```

## Quality Assurance Checklist

Before finalizing anchor paper annotation:

- [ ] All sections of paper reviewed
- [ ] Both annotators completed independently
- [ ] Reconciliation meeting held
- [ ] Agreement score calculated (κ ≥ 0.7)
- [ ] All claims have extractability classification
- [ ] All claims have expected verdict
- [ ] All irrelevant items documented
- [ ] At least 15+ claims in inventory
- [ ] Mix of extractability levels (high/medium/low)
- [ ] Mix of expected verdicts (approved/rejected/borderline)
```

### 3. Gap Scenario Design Template

**File:** `tests/golden_dataset/docs/GAP_SCENARIO_DESIGN.md`

```markdown
# Controlled Gap Scenario Design

## Purpose

Gap scenarios are controlled database states designed to test:
1. Correct gap detection (finding gaps that exist)
2. Correct non-gap handling (not flagging covered requirements)
3. Iterative gap closing (Pass 2 paper attribution)
4. Decoy paper rejection (irrelevant paper handling)

## Scenario Structure

### Basic Scenario Template

```yaml
scenario_id: "GAP-SCENARIO-001"
scenario_name: "STDP Learning Rule Gap"
scenario_type: "iterative"  # single, iterative

# Pass 1: Initial State
initial_state:
  papers:
    - paper_id: "NEURO-001"
      provides_coverage:
        - requirement: "REQ-B1.1"
          completeness_contribution: 45
    - paper_id: "NEURO-002"
      provides_coverage:
        - requirement: "REQ-B1.2"
          completeness_contribution: 30
  
  expected_coverage:
    REQ-B1.1: 45
    REQ-B1.2: 30
    REQ-B1.4: 0  # This is the gap
  
  expected_gaps:
    - requirement: "REQ-B1.4"
      expected_severity: "CRITICAL"
      expected_completeness: 0
      must_be_detected: true
      if_not_detected: "critical_error"
  
  expected_non_gaps:
    - requirement: "REQ-B1.1"
      current_completeness: 45
      must_not_be_flagged_as_gap: true
      if_flagged_as_gap: "error"
      reason: "45% exceeds gap threshold"

# Pass 2: Gap-Closing Papers
gap_closing_additions:
  papers:
    - paper_id: "NEURO-003"
      designed_to_close: ["REQ-B1.4"]
      known_claims:
        - claim_text: "Our STDP implementation shows..."
          expected_contribution: 60
      expected_impact:
        REQ-B1.4:
          before: 0
          after: 60
          severity_change: "CRITICAL → MEDIUM"
  
  decoy_papers:
    - paper_id: "CLIMATE-001"  # Wrong domain
      should_not_close: ["REQ-B1.4"]
      reason: "Climate paper, not relevant to neuromorphic"
      if_contributes: "critical_error"
    
    - paper_id: "NEURO-004"  # Same domain, different topic
      should_not_close: ["REQ-B1.4"]
      reason: "Addresses inference, not learning"
      if_contributes: "error"

# Expected Final State
expected_final_state:
  coverage:
    REQ-B1.1: 45
    REQ-B1.2: 30
    REQ-B1.4: 60
  
  gaps_remaining:
    - requirement: "REQ-B1.4"
      severity: "MEDIUM"  # Reduced from CRITICAL
  
  recommendation_changes:
    - requirement: "REQ-B1.4"
      priority_should_decrease: true
      if_still_critical: "error"
```

## Scenario Types

### Type 1: Single-Pass Gap Detection

**Purpose:** Test initial gap identification accuracy

**Structure:**
- Fixed database state with known gaps
- Test gap detection only (no iteration)
- Validate severity classification

**Validation Points:**
- All critical gaps detected
- Non-gaps not flagged
- Severity levels correct

### Type 2: Iterative Gap Closing

**Purpose:** Test multi-pass behavior

**Structure:**
- Pass 1: Initial gaps
- Pass 2: Add gap-closing papers
- Validate gap reduction

**Validation Points:**
- Gaps close appropriately
- Decoy papers rejected
- Recommendations update

### Type 3: Edge Case Scenarios

**Purpose:** Test boundary conditions

**Examples:**
- Requirement at exactly gap threshold (50%)
- Multiple papers partially closing a gap
- Paper closing multiple gaps
- Conflicting evidence

## Minimum Scenario Coverage

| Scenario Type | Count | Purpose |
|--------------|-------|---------|
| Single-Pass Detection | 2 | Basic gap detection |
| Iterative Closing | 2 | Gap closing validation |
| Decoy Rejection | 2 | False positive prevention |
| Edge Cases | 2 | Boundary testing |
| **Total** | 8 | Comprehensive coverage |
```

### 4. Anchor Paper Annotation Schema Extension

**File:** `tests/golden_dataset/schema_anchor.py`

```python
"""
Anchor Paper Schema Extensions

Extended Pydantic models for exhaustive anchor paper annotation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
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
    expected_composite_range: Optional[tuple[float, float]] = None
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
    
    # Statistics
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
    
    # Validation
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
```

### 5. Pilot Annotation Checklist

**File:** `tests/golden_dataset/docs/PILOT_ANNOTATION_CHECKLIST.md`

```markdown
# Pilot Annotation Checklist

## Purpose

Validate the exhaustive annotation protocol with 3-5 anchor papers
before full implementation of VM-W1.5-2.

## Pre-Pilot Preparation

- [ ] Anchor paper selection criteria finalized
- [ ] Exhaustive annotation protocol document complete
- [ ] Two annotators identified and briefed
- [ ] Annotation tools/templates prepared
- [ ] Inter-rater agreement calculation method defined
- [ ] 3-5 candidate anchor papers selected

## Pilot Paper Selection

| Paper # | Paper ID | Domain | Est. Claims | Annotator A | Annotator B |
|---------|----------|--------|-------------|-------------|-------------|
| 1 | | Neuromorphic | | | |
| 2 | | Quantum | | | |
| 3 | | Microbiology | | | |
| 4 | | [Optional] | | | |
| 5 | | [Optional] | | | |

## Per-Paper Pilot Process

### Phase 1: Independent Annotation

**Annotator A:**
- [ ] Read full paper
- [ ] Marked all potential claims
- [ ] Documented locations precisely
- [ ] Time recorded: ___ hours

**Annotator B:**
- [ ] Read full paper (independently)
- [ ] Marked all potential claims
- [ ] Documented locations precisely
- [ ] Time recorded: ___ hours

### Phase 2: Reconciliation

- [ ] Claims from A and B compared
- [ ] Intersection identified (agreed claims)
- [ ] Differences discussed
- [ ] Final unified inventory created
- [ ] Cohen's κ calculated: ___
- [ ] Reconciliation notes documented

### Phase 3: Classification

- [ ] All claims classified by extractability
- [ ] All claims have expected verdict
- [ ] Irrelevant items documented
- [ ] Non-extraction items documented

### Phase 4: Quality Check

- [ ] At least 15 claims in inventory
- [ ] Mix of extractability levels present
- [ ] Mix of expected verdicts present
- [ ] Statistics calculated and recorded

## Pilot Metrics Targets

| Metric | Target | Actual |
|--------|--------|--------|
| Inter-rater agreement (κ) | ≥ 0.7 | |
| Claims per paper | 15-30 | |
| Annotation time per paper | 2-4 hours | |
| High extractability % | 30-50% | |
| Irrelevant items per paper | 5-15 | |

## Post-Pilot Assessment

### Protocol Effectiveness

- [ ] Protocol was clear and followable
- [ ] Annotators had sufficient guidance
- [ ] Edge cases were manageable
- [ ] Time estimates are realistic

### Issues Identified

| Issue | Impact | Resolution |
|-------|--------|------------|
| | | |
| | | |

### Protocol Updates Needed

- [ ] Update EXHAUSTIVE_ANNOTATION_PROTOCOL.md with findings
- [ ] Adjust time estimates if needed
- [ ] Add examples for edge cases found
- [ ] Refine extractability criteria if needed

## Pilot Sign-Off

- [ ] Annotator A confirms protocol is workable
- [ ] Annotator B confirms protocol is workable
- [ ] Inter-rater agreement meets threshold (κ ≥ 0.7)
- [ ] Time estimates validated
- [ ] Protocol ready for full implementation

**Sign-off Date:** _______________  
**Approved By:** _______________
```

---

## Implementation Plan

### Phase 1: Documentation (4 hours)
1. Create ANCHOR_PAPER_CRITERIA.md
2. Create EXHAUSTIVE_ANNOTATION_PROTOCOL.md
3. Create GAP_SCENARIO_DESIGN.md
4. Create schema_anchor.py

### Phase 2: Anchor Paper Selection (2 hours)
1. Review paper registry for candidates
2. Evaluate against selection criteria
3. Select 5 diverse anchor papers
4. Document selection rationale

### Phase 3: Pilot Annotation (4 hours)
1. Complete exhaustive annotation of 2-3 papers
2. Measure inter-rater agreement
3. Validate time estimates
4. Refine protocol based on findings

### Phase 4: Gap Scenario Design (2 hours)
1. Design 3+ controlled gap scenarios
2. Define Pass 1 and Pass 2 states
3. Identify decoy papers from registry
4. Document expected outcomes

---

## Acceptance Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Anchor paper criteria | Complete | Document review |
| Exhaustive protocol | Complete | Document review |
| Pilot papers annotated | ≥3 | Anchor paper count |
| Inter-rater agreement | κ ≥ 0.7 | Cohen's Kappa |
| Claims per anchor | 15-30 | Inventory count |
| Gap scenarios | ≥3 | Scenario count |
| Decoy papers identified | ≥5 | Registry review |
| Protocol validated | Sign-off | Checklist complete |

---

## Integration with VM-W1.5-2

Upon completion of this task:

1. **VM-W1.5-2 Update Required:**
   - Add anchor paper exhaustive annotation workflow
   - Integrate extractability classification
   - Add non-extraction documentation
   - Reference gap scenario design

2. **Schema Updates:**
   - Import AnchorPaper model
   - Import GapScenario model
   - Extend GoldenDataset to include anchor papers

3. **Validation Coverage Enhancement:**
   - AV-01 (Precision): Add false positive tests from non-extraction items
   - AV-02 (Recall): Use must-find claims from anchor papers
   - FV-07 (Gap Detection): Use controlled gap scenarios
   - NEW validations for negative cases

---

## Notes

- **Quality over speed:** Pilot annotation should be thorough
- **Protocol refinement:** Expect 1-2 iterations on the protocol
- **Annotator training:** Brief annotators on expectations
- **Tool support:** Consider annotation tool to reduce friction
- **Documentation:** Decisions during pilot inform full implementation
