# TASK CARD #21: Methodological Quality Assessment (GRADE)

**Priority:** 🟢 LOW  
**Estimated Effort:** 8-10 hours  
**Risk Level:** LOW  
**Wave:** Wave 4 (Weeks 7-8)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Card #16 (Evidence Scoring)  
**Blocks:** None

## Problem Statement

Current evidence scoring doesn't formally assess methodological quality using established systematic review frameworks. This prevents:
- Publication in high-quality systematic review journals
- PRISMA compliance for evidence quality assessment
- Standardized quality comparisons across studies
- Transparent communication of evidence certainty

GRADE (Grading of Recommendations Assessment, Development and Evaluation) is the gold standard framework for evidence quality assessment in systematic reviews.

## Acceptance Criteria

**Functional Requirements:**
- [ ] Assess evidence using GRADE framework
- [ ] Classify quality as: Very Low, Low, Moderate, High
- [ ] Account for study design, risk of bias, indirectness
- [ ] Store GRADE assessment in version history
- [ ] Generate GRADE summary table for reports

**GRADE Quality Levels:**
- [ ] **High**: High confidence in effect estimate
- [ ] **Moderate**: Moderate confidence; true effect likely close but may differ
- [ ] **Low**: Limited confidence; true effect may differ substantially  
- [ ] **Very Low**: Very little confidence; true effect likely substantially different

**Technical Requirements:**
- [ ] GRADE assessment adds <5% to Judge processing time
- [ ] Quality levels map to existing composite scores
- [ ] Downgrade factors documented (bias, indirectness, imprecision)
- [ ] GRADE interpretation strings generated automatically

## Implementation Guide

**Files to Modify:**

### 1. New Module: literature_review/analysis/grade_assessment.py (~100 lines)

```python
from typing import Dict, Tuple

def assess_methodological_quality(claim: Dict, paper_metadata: Dict) -> Dict:
    """
    Apply GRADE criteria to assess evidence quality.
    
    GRADE Criteria:
    1. Study Design (RCT=high, Observational=low)
    2. Risk of Bias (reproducibility, methodological rigor)
    3. Indirectness (relevance to requirement)
    4. Imprecision (sample size, confidence intervals)
    5. Inconsistency (handled by triangulation)
    6. Publication Bias (handled separately)
    
    Returns:
        {
            "grade_quality_level": "very_low|low|moderate|high",
            "grade_score": 1-4,
            "baseline_quality": 1-4,
            "bias_adjustment": -2 to 0,
            "indirectness_adjustment": -2 to 0,
            "interpretation": "..."
        }
    """
    
    # Start with study design baseline
    study_type = claim.get("evidence_quality", {}).get("study_type", "unknown")
    
    baseline_quality = _get_baseline_quality(study_type)
    
    # Adjust for risk of bias (based on reproducibility)
    reproducibility = claim.get("evidence_quality", {}).get("reproducibility_score", 3)
    bias_adjustment = _assess_bias_risk(reproducibility)
    
    # Adjust for indirectness (based on relevance)
    relevance = claim.get("evidence_quality", {}).get("relevance_score", 3)
    indirectness_adjustment = _assess_indirectness(relevance)
    
    # Compute final quality
    final_quality_score = baseline_quality + bias_adjustment + indirectness_adjustment
    final_quality_score = max(1, min(4, final_quality_score))  # Clamp to 1-4
    
    quality_levels = {
        1: "very_low",
        2: "low",
        3: "moderate",
        4: "high"
    }
    
    quality_level = quality_levels[final_quality_score]
    
    return {
        "grade_quality_level": quality_level,
        "grade_score": final_quality_score,
        "baseline_quality": baseline_quality,
        "bias_adjustment": bias_adjustment,
        "indirectness_adjustment": indirectness_adjustment,
        "downgrade_reasons": _get_downgrade_reasons(bias_adjustment, indirectness_adjustment),
        "interpretation": _get_grade_interpretation(quality_level)
    }

def _get_baseline_quality(study_type: str) -> int:
    """
    Get baseline GRADE quality from study design.
    
    GRADE starts with:
    - RCT/Experimental: High (4)
    - Observational: Low (2)
    - Theoretical/Opinion: Very Low (1)
    """
    baseline_map = {
        "experimental": 4,  # High
        "review": 3,        # Moderate (if systematic)
        "observational": 2, # Low
        "theoretical": 1,   # Very Low
        "opinion": 1        # Very Low
    }
    return baseline_map.get(study_type, 2)  # Default to Low

def _assess_bias_risk(reproducibility_score: int) -> int:
    """
    Assess risk of bias from reproducibility.
    
    Returns downgrade adjustment:
    - 0: No serious risk
    - -1: Serious risk of bias
    - -2: Very serious risk of bias
    """
    if reproducibility_score >= 4:
        return 0   # Code + data available → no bias risk
    elif reproducibility_score >= 3:
        return -1  # Basic methods → serious risk
    else:
        return -2  # Vague/no methods → very serious risk

def _assess_indirectness(relevance_score: int) -> int:
    """
    Assess indirectness from relevance to requirement.
    
    Returns downgrade adjustment:
    - 0: Direct evidence
    - -1: Some indirectness
    - -2: Very indirect
    """
    if relevance_score >= 4:
        return 0   # Perfect/strong match → direct
    elif relevance_score >= 3:
        return -1  # Moderate match → some indirectness
    else:
        return -2  # Tangential → very indirect

def _get_downgrade_reasons(bias_adj: int, indirect_adj: int) -> list:
    """Generate list of downgrade reasons."""
    reasons = []
    if bias_adj == -1:
        reasons.append("Serious risk of bias (limited reproducibility)")
    elif bias_adj == -2:
        reasons.append("Very serious risk of bias (no reproducibility)")
    
    if indirect_adj == -1:
        reasons.append("Some indirectness (moderate relevance)")
    elif indirect_adj == -2:
        reasons.append("Very indirect evidence (weak relevance)")
    
    return reasons

def _get_grade_interpretation(quality_level: str) -> str:
    """Map GRADE quality to interpretation."""
    interpretations = {
        "high": "High confidence that true effect is close to estimated effect",
        "moderate": "Moderate confidence; true effect likely close but may differ substantially",
        "low": "Limited confidence; true effect may differ substantially",
        "very_low": "Very little confidence; true effect likely substantially different"
    }
    return interpretations.get(quality_level, "Unknown quality")

def generate_grade_summary_table(claims: list) -> str:
    """Generate GRADE summary table in markdown."""
    
    lines = [
        "# GRADE Evidence Quality Summary",
        "",
        "| Sub-Requirement | Quality Level | Study Type | Downgrade Reasons | Interpretation |",
        "|-----------------|---------------|------------|-------------------|----------------|"
    ]
    
    for claim in claims:
        grade = claim.get("grade_assessment", {})
        sub_req = claim.get("sub_requirement", "Unknown")
        quality = grade.get("grade_quality_level", "unknown").title()
        study_type = claim.get("evidence_quality", {}).get("study_type", "unknown").title()
        reasons = ", ".join(grade.get("downgrade_reasons", [])) or "None"
        interp = grade.get("interpretation", "")
        
        lines.append(f"| {sub_req} | {quality} | {study_type} | {reasons} | {interp} |")
    
    return "\n".join(lines)
```

### 2. Integration with literature_review/analysis/judge.py (~20 lines)

```python
def judge_with_grade_assessment(claim: Dict, sub_req_def: str, api_manager) -> Dict:
    """Enhanced Judge with GRADE assessment."""
    
    # Standard Judge evaluation
    judgment = judge_claim_enhanced(claim, sub_req_def, api_manager)
    
    # Add GRADE assessment
    from literature_review.analysis.grade_assessment import assess_methodological_quality
    
    grade = assess_methodological_quality(judgment, paper_metadata={})
    judgment["grade_assessment"] = grade
    
    return judgment
```

## Testing Strategy

### Unit Tests

```python
from literature_review.analysis.grade_assessment import (
    assess_methodological_quality,
    _get_baseline_quality,
    _assess_bias_risk,
    _get_grade_interpretation
)

@pytest.mark.unit
def test_grade_baseline_quality():
    """Test baseline quality from study design."""
    assert _get_baseline_quality("experimental") == 4  # High
    assert _get_baseline_quality("observational") == 2  # Low
    assert _get_baseline_quality("opinion") == 1  # Very Low

@pytest.mark.unit
def test_grade_downgrade_logic():
    """Test downgrade adjustments."""
    claim = {
        "evidence_quality": {
            "study_type": "experimental",  # Baseline: 4
            "reproducibility_score": 2,    # -2 (very serious bias)
            "relevance_score": 3           # -1 (some indirectness)
        }
    }
    
    grade = assess_methodological_quality(claim, {})
    
    # 4 (baseline) - 2 (bias) - 1 (indirect) = 1 (very low)
    assert grade["grade_score"] == 1
    assert grade["grade_quality_level"] == "very_low"
    assert "Very serious risk of bias" in grade["downgrade_reasons"]

@pytest.mark.unit
def test_grade_interpretation():
    """Test GRADE interpretation strings."""
    interp_high = _get_grade_interpretation("high")
    assert "High confidence" in interp_high
    
    interp_low = _get_grade_interpretation("low")
    assert "Limited confidence" in interp_low
```

## Success Criteria

- [ ] GRADE assessment integrated with literature_review/analysis/judge.py
- [ ] Quality levels calculated correctly
- [ ] Downgrade factors documented
- [ ] GRADE summary table generated
- [ ] Processing time increase <5%
- [ ] Unit tests pass (100% coverage for GRADE logic)
- [ ] GRADE assessments stored in version history

## Benefits

1. **Standardized quality** - Uses established GRADE framework
2. **Explainable decisions** - Clear rationale for quality ratings
3. **Publication-ready** - GRADE required for systematic reviews in top journals
4. **Risk communication** - Transparent uncertainty quantification
5. **PRISMA compliance** - Meets systematic review reporting standards

---

**Status:** Ready for implementation  
**Wave:** Wave 4 (Weeks 7-8)  
**Next Steps:** Create literature_review/analysis/grade_assessment.py module, integrate with literature_review/analysis/judge.py, add GRADE table to reports
