"""
GRADE (Grading of Recommendations Assessment, Development and Evaluation) Framework
Version: 1.0
Date: 2025-11-14

This module implements GRADE evidence quality assessment for systematic reviews.
GRADE is the gold standard framework used in high-quality systematic review journals.

Key GRADE Principles:
1. Start with study design baseline (RCT=high, observational=low)
2. Downgrade for: risk of bias, indirectness, imprecision, inconsistency
3. Classify as: Very Low, Low, Moderate, High
4. Provide transparent rationale for quality ratings

References:
- GRADE Working Group: https://www.gradeworkinggroup.org/
- Balshem et al. (2011). GRADE guidelines: 3. Rating the quality of evidence. J Clin Epidemiol.
"""

from typing import Dict, List


def assess_methodological_quality(claim: Dict, paper_metadata: Dict = None) -> Dict:
    """
    Apply GRADE criteria to assess evidence quality.
    
    GRADE Criteria:
    1. Study Design (RCT=high, Observational=low)
    2. Risk of Bias (reproducibility, methodological rigor)
    3. Indirectness (relevance to requirement)
    4. Imprecision (sample size, confidence intervals)
    5. Inconsistency (handled by triangulation)
    6. Publication Bias (handled separately)
    
    Args:
        claim: Claim dictionary containing evidence_quality scores
        paper_metadata: Optional paper metadata (reserved for future use)
    
    Returns:
        Dictionary with GRADE assessment:
        {
            "grade_quality_level": "very_low|low|moderate|high",
            "grade_score": 1-4,
            "baseline_quality": 1-4,
            "bias_adjustment": -2 to 0,
            "indirectness_adjustment": -2 to 0,
            "downgrade_reasons": [...],
            "interpretation": "..."
        }
    """
    # Extract evidence quality scores from claim
    evidence_quality = claim.get("evidence_quality", {})
    
    # Start with study design baseline
    study_type = evidence_quality.get("study_type", "unknown")
    baseline_quality = _get_baseline_quality(study_type)
    
    # Adjust for risk of bias (based on reproducibility)
    reproducibility = evidence_quality.get("reproducibility_score", 3)
    bias_adjustment = _assess_bias_risk(reproducibility)
    
    # Adjust for indirectness (based on relevance)
    relevance = evidence_quality.get("relevance_score", 3)
    indirectness_adjustment = _assess_indirectness(relevance)
    
    # Compute final quality score
    final_quality_score = baseline_quality + bias_adjustment + indirectness_adjustment
    final_quality_score = max(1, min(4, final_quality_score))  # Clamp to 1-4
    
    # Map score to quality level
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
    
    GRADE framework starts with:
    - RCT/Experimental: High (4)
    - Observational: Low (2)
    - Theoretical/Opinion: Very Low (1)
    
    Args:
        study_type: Type of study (experimental, observational, theoretical, review, opinion)
    
    Returns:
        Baseline quality score (1-4)
    """
    baseline_map = {
        "experimental": 4,  # High (RCT, controlled experiments)
        "review": 3,        # Moderate (systematic reviews)
        "observational": 2, # Low (cohort, case-control)
        "theoretical": 1,   # Very Low (models, simulations)
        "opinion": 1,       # Very Low (expert opinion)
        "unknown": 2        # Default to Low when unknown
    }
    return baseline_map.get(study_type, 2)


def _assess_bias_risk(reproducibility_score: int) -> int:
    """
    Assess risk of bias from reproducibility.
    
    GRADE downgrades for serious or very serious risk of bias.
    Reproducibility score indicates methodological transparency.
    
    Args:
        reproducibility_score: Score from 1-5
            5 = Code + data available
            4 = Detailed methods, replicable
            3 = Basic methods described
            2 = Vague methods
            1 = No methodological detail
    
    Returns:
        Downgrade adjustment:
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
    
    GRADE downgrades when evidence doesn't directly address the question.
    Relevance score indicates how well evidence matches requirement.
    
    Args:
        relevance_score: Score from 1-5
            5 = Perfect match (directly addresses requirement)
            4 = Strong match (clearly related)
            3 = Moderate match (related but requires inference)
            2 = Tangential (peripherally related)
            1 = Weak (very indirect connection)
    
    Returns:
        Downgrade adjustment:
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


def _get_downgrade_reasons(bias_adj: int, indirect_adj: int) -> List[str]:
    """
    Generate list of downgrade reasons for transparency.
    
    Args:
        bias_adj: Bias adjustment (-2, -1, or 0)
        indirect_adj: Indirectness adjustment (-2, -1, or 0)
    
    Returns:
        List of human-readable downgrade reasons
    """
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
    """
    Map GRADE quality level to standard interpretation.
    
    These are the official GRADE interpretations used in systematic reviews.
    
    Args:
        quality_level: GRADE quality level (very_low, low, moderate, high)
    
    Returns:
        Standard GRADE interpretation string
    """
    interpretations = {
        "high": "High confidence that true effect is close to estimated effect",
        "moderate": "Moderate confidence; true effect likely close but may differ substantially",
        "low": "Limited confidence; true effect may differ substantially",
        "very_low": "Very little confidence; true effect likely substantially different"
    }
    return interpretations.get(quality_level, "Unknown quality")


def generate_grade_summary_table(claims: List[Dict]) -> str:
    """
    Generate GRADE summary table in markdown format.
    
    This table provides an overview of evidence quality across all claims,
    suitable for inclusion in systematic review reports.
    
    Args:
        claims: List of claim dictionaries with grade_assessment field
    
    Returns:
        Markdown-formatted GRADE summary table
    """
    lines = [
        "# GRADE Evidence Quality Summary",
        "",
        "| Sub-Requirement | Quality Level | Study Type | Downgrade Reasons | Interpretation |",
        "|-----------------|---------------|------------|-------------------|----------------|"
    ]
    
    for claim in claims:
        grade = claim.get("grade_assessment", {})
        sub_req = claim.get("sub_requirement", "Unknown")
        quality = grade.get("grade_quality_level", "unknown").replace("_", " ").title()
        study_type = claim.get("evidence_quality", {}).get("study_type", "unknown").title()
        reasons = ", ".join(grade.get("downgrade_reasons", [])) or "None"
        interp = grade.get("interpretation", "")
        
        lines.append(f"| {sub_req} | {quality} | {study_type} | {reasons} | {interp} |")
    
    return "\n".join(lines)
