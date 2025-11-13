# TASK CARD #16: Multi-Dimensional Evidence Scoring

**Priority:** 🔴 CRITICAL  
**Estimated Effort:** 6-8 hours  
**Risk Level:** MEDIUM  
**Wave:** Wave 2 (Weeks 3-4)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Cards #13 (Orchestrator), #5 (Test Infrastructure)  
**Blocks:** Task Cards #18, #19, #20, #21 (all depend on scoring)

## Problem Statement

Current system uses binary approve/reject decisions with no quality gradation. This prevents:
- Prioritizing high-quality evidence over weak evidence
- Identifying borderline claims needing human review
- Weighted gap analysis in Orchestrator
- Meta-analytic aggregation of findings

A multi-dimensional scoring system enables evidence tiers, quality-based prioritization, and transparent decision-making aligned with systematic review best practices.

## Acceptance Criteria

**Functional Requirements:**
- [ ] Judge.py outputs 6-dimensional evidence quality scores
- [ ] Composite score calculated via weighted average
- [ ] Scores persisted in version history
- [ ] Orchestrator uses scores for weighted gap analysis
- [ ] Visualization shows evidence quality distribution

**Scoring Dimensions (1-5 scale except directness):**
- [ ] Strength of Evidence (1-5): Strong experimental → Weak observational
- [ ] Methodological Rigor (1-5): RCT → Case study → Opinion
- [ ] Relevance to Requirement (1-5): Perfect match → Tangential
- [ ] Evidence Directness (1-3): Direct statement → Inferred
- [ ] Recency Bonus (boolean): Published within 3 years
- [ ] Reproducibility (1-5): Code+data available → None

**Non-Functional Requirements:**
- [ ] Backward compatible with existing claims (default scores)
- [ ] Score calculation <10ms per claim
- [ ] Composite score formula: strength(0.3) + rigor(0.25) + relevance(0.25) + directness/3(0.1) + recency(0.05) + reproducibility(0.05)
- [ ] Approval threshold: composite ≥ 3.0 AND strength ≥ 3 AND relevance ≥ 3

## Implementation Guide

**Files to Modify:**

### 1. literature_review/analysis/judge.py (~150 lines new/modified)

```python
def build_judge_prompt_enhanced(claim: Dict, sub_requirement_definition: str) -> str:
    """
    Enhanced prompt with multi-dimensional scoring.
    
    Returns prompt requesting 6-dimensional evidence quality scores
    following PRISMA systematic review standards.
    """
    return f"""
You are an impartial "Judge" AI evaluating scientific evidence quality.

**Claim to Evaluate:**
{json.dumps(claim, indent=2)}

**Target Requirement:**
{sub_requirement_definition}

**Your Task:**
Assess this claim using PRISMA systematic review standards across 6 dimensions:

1. **Strength of Evidence** (1-5):
   - 5: Strong (Multiple RCTs, meta-analysis, direct experimental proof)
   - 4: Moderate (Single well-designed study, clear experimental validation)
   - 3: Weak (Observational study, indirect evidence)
   - 2: Very Weak (Case reports, anecdotal evidence)
   - 1: Insufficient (Opinion, speculation, no empirical support)

2. **Methodological Rigor** (1-5):
   - 5: Gold standard (Randomized controlled trial, peer-reviewed, replicated)
   - 4: Controlled study (Experimental with controls, proper statistics)
   - 3: Observational (Real-world data, no controls)
   - 2: Case study (Single instance, n=1)
   - 1: Opinion (Expert opinion without empirical basis)

3. **Relevance to Requirement** (1-5):
   - 5: Perfect match (Directly addresses this exact requirement)
   - 4: Strong (Clearly related, minor gap)
   - 3: Moderate (Related but requires inference)
   - 2: Tangential (Peripherally related)
   - 1: Weak (Very indirect connection)

4. **Evidence Directness** (1-3):
   - 3: Direct (Paper explicitly states this finding)
   - 2: Indirect (Finding can be inferred from results)
   - 1: Inferred (Requires significant interpretation)

5. **Recency Bonus**:
   - true if published within last 3 years, false otherwise

6. **Reproducibility** (1-5):
   - 5: Code + data publicly available
   - 4: Detailed methods, replicable
   - 3: Basic methods described
   - 2: Vague methods
   - 1: No methodological detail

**Decision Criteria:**
- APPROVE if composite_score ≥ 3.0 AND strength_score ≥ 3 AND relevance_score ≥ 3
- REJECT otherwise

**Return Format (JSON only):**
{{
  "verdict": "approved|rejected",
  "evidence_quality": {{
    "strength_score": <1-5>,
    "strength_rationale": "<brief justification>",
    "rigor_score": <1-5>,
    "study_type": "experimental|observational|theoretical|review|opinion",
    "relevance_score": <1-5>,
    "relevance_notes": "<brief explanation>",
    "directness": <1-3>,
    "is_recent": <true|false>,
    "reproducibility_score": <1-5>,
    "composite_score": <calculated weighted average>,
    "confidence_level": "high|medium|low"
  }},
  "judge_notes": "<1-2 sentence summary>"
}}

**Composite Score Formula:**
composite_score = (strength × 0.30) + (rigor × 0.25) + (relevance × 0.25) + (directness/3 × 0.10) + (recency × 0.05) + (reproducibility × 0.05)
"""

def validate_judge_response_enhanced(response: Any) -> Optional[Dict]:
    """Validate enhanced Judge response with quality scores."""
    if not isinstance(response, dict):
        return None
    
    # Check required fields
    if "verdict" not in response or "evidence_quality" not in response:
        return None
    
    verdict = response["verdict"]
    if verdict not in ["approved", "rejected"]:
        return None
    
    quality = response["evidence_quality"]
    
    # Validate score ranges
    required_scores = {
        "strength_score": (1, 5),
        "rigor_score": (1, 5),
        "relevance_score": (1, 5),
        "directness": (1, 3),
        "reproducibility_score": (1, 5),
        "composite_score": (1, 5)
    }
    
    for score_name, (min_val, max_val) in required_scores.items():
        if score_name not in quality:
            return None
        score = quality[score_name]
        if not isinstance(score, (int, float)) or score < min_val or score > max_val:
            return None
    
    # Validate study type
    if quality.get("study_type") not in ["experimental", "observational", "theoretical", "review", "opinion"]:
        return None
    
    # Validate confidence level
    if quality.get("confidence_level") not in ["high", "medium", "low"]:
        return None
    
    return response

def calculate_composite_score(quality: Dict) -> float:
    """
    Calculate composite evidence quality score.
    
    Formula: (strength × 0.30) + (rigor × 0.25) + (relevance × 0.25) 
             + (directness/3 × 0.10) + (recency × 0.05) + (reproducibility × 0.05)
    """
    weights = {
        "strength_score": 0.30,
        "rigor_score": 0.25,
        "relevance_score": 0.25,
        "directness": 0.10,  # Normalized to 0-1 range (divide by 3)
        "is_recent": 0.05,   # Boolean treated as 0 or 1
        "reproducibility_score": 0.05
    }
    
    score = 0.0
    score += quality["strength_score"] * weights["strength_score"]
    score += quality["rigor_score"] * weights["rigor_score"]
    score += quality["relevance_score"] * weights["relevance_score"]
    score += (quality["directness"] / 3.0) * weights["directness"]  # Normalize to 0-1
    score += (1.0 if quality["is_recent"] else 0.0) * weights["is_recent"]
    score += quality["reproducibility_score"] * weights["reproducibility_score"]
    
    return round(score, 2)
```

### 2. Version History Schema (~30 lines)

```python
# Example claim with enhanced evidence quality
enhanced_claim = {
    "claim_id": "c1a2b3",
    "status": "approved",
    "evidence_quality": {
        "strength_score": 4,
        "strength_rationale": "Direct experimental validation with quantitative metrics",
        "rigor_score": 5,
        "study_type": "experimental",
        "relevance_score": 4,
        "relevance_notes": "Directly addresses SNN feature extraction on DVS data",
        "directness": 3,
        "is_recent": True,
        "reproducibility_score": 4,
        "composite_score": 4.2,
        "confidence_level": "high"
    },
    "judge_notes": "Strong experimental evidence with public code repository.",
    "sub_requirement": "Sub-2.1.1",
    # ... other fields
}
```

### 3. literature_review/orchestrator.py Updates (~80 lines)

```python
def calculate_weighted_gap_score(db: pd.DataFrame, pillar_definitions: Dict) -> Dict:
    """
    Calculate gap scores weighted by evidence quality.
    
    Prioritizes filling gaps where evidence is weak or missing.
    """
    gap_scores = {}
    
    for pillar_name, pillar_data in pillar_definitions.items():
        for req_key, req_data in pillar_data.get("requirements", {}).items():
            for sub_req in req_data:
                # Get all claims for this sub-requirement
                claims = db[db["Requirement(s)"].str.contains(sub_req, na=False)]
                
                if claims.empty:
                    # No evidence: highest priority
                    gap_scores[sub_req] = {
                        "priority": 1.0,
                        "reason": "no_evidence",
                        "avg_quality": 0.0,
                        "claim_count": 0
                    }
                else:
                    # Extract quality scores
                    quality_scores = []
                    for _, row in claims.iterrows():
                        req_list = json.loads(row["Requirement(s)"])
                        for claim in req_list:
                            if sub_req in claim.get("sub_requirement", ""):
                                quality = claim.get("evidence_quality", {})
                                composite = quality.get("composite_score", 3.0)
                                quality_scores.append(composite)
                    
                    avg_quality = np.mean(quality_scores) if quality_scores else 3.0
                    
                    # Priority inversely proportional to quality
                    # Low quality (1.0) = High priority (1.0)
                    # High quality (5.0) = Low priority (0.2)
                    priority = 1.0 - ((avg_quality - 1.0) / 4.0)
                    
                    gap_scores[sub_req] = {
                        "priority": priority,
                        "reason": "low_quality_evidence" if avg_quality < 3.5 else "sufficient_evidence",
                        "avg_quality": avg_quality,
                        "claim_count": len(quality_scores)
                    }
    
    return gap_scores

def plot_evidence_quality_distribution(db: pd.DataFrame, output_file: str):
    """Generate histogram of evidence quality scores."""
    import matplotlib.pyplot as plt
    
    quality_scores = []
    for _, row in db.iterrows():
        req_list = json.loads(row.get("Requirement(s)", "[]"))
        for claim in req_list:
            quality = claim.get("evidence_quality", {})
            score = quality.get("composite_score")
            if score:
                quality_scores.append(score)
    
    plt.figure(figsize=(10, 6))
    plt.hist(quality_scores, bins=20, edgecolor='black', alpha=0.7)
    plt.xlabel("Composite Evidence Quality Score")
    plt.ylabel("Number of Claims")
    plt.title("Distribution of Evidence Quality Scores")
    plt.axvline(x=3.0, color='r', linestyle='--', label='Approval Threshold')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
```

## Testing Strategy

### Unit Tests (`tests/unit/test_evidence_scoring.py`)

```python
@pytest.mark.unit
def test_composite_score_calculation():
    """Test composite score formula."""
    quality = {
        "strength_score": 4,
        "rigor_score": 5,
        "relevance_score": 4,
        "directness": 3,
        "is_recent": True,
        "reproducibility_score": 4
    }
    
    score = calculate_composite_score(quality)
    
    # Expected: (4*0.3) + (5*0.25) + (4*0.25) + (3/3*0.1) + (1*0.05) + (4*0.05)
    # = 1.2 + 1.25 + 1.0 + 0.1 + 0.05 + 0.2 = 3.8
    assert abs(score - 3.8) < 0.01

@pytest.mark.unit  
def test_approval_threshold():
    """Test that composite ≥3.0 AND strength ≥3 AND relevance ≥3 required."""
    # Should approve
    quality_approve = {
        "strength_score": 4,
        "rigor_score": 3,
        "relevance_score": 4,
        "directness": 3,
        "is_recent": False,
        "reproducibility_score": 3,
        "composite_score": 3.5
    }
    
    # Should reject (low strength)
    quality_reject = {
        "strength_score": 2,
        "rigor_score": 5,
        "relevance_score": 5,
        "directness": 3,
        "is_recent": True,
        "reproducibility_score": 5,
        "composite_score": 3.6  # Composite high but strength too low
    }
    
    assert meets_approval_criteria(quality_approve) == True
    assert meets_approval_criteria(quality_reject) == False
```

### Integration Tests (Modify existing Task Card #6)

```python
from literature_review.analysis.judge import judge_claim_enhanced

@pytest.mark.integration
def test_judge_outputs_quality_scores(temp_workspace, test_data_generator):
    """Test Judge outputs evidence quality scores."""
    
    # Setup version history
    version_history = test_data_generator.create_version_history(
        filename="quality_test.pdf",
        num_versions=1,
        claim_statuses=['pending_judge_review']
    )
    
    # Mock Judge with quality scores
    mock_response = {
        "verdict": "approved",
        "evidence_quality": {
            "strength_score": 4,
            "strength_rationale": "Strong experimental evidence",
            "rigor_score": 5,
            "study_type": "experimental",
            "relevance_score": 4,
            "relevance_notes": "Directly relevant",
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 4,
            "composite_score": 4.2,
            "confidence_level": "high"
        },
        "judge_notes": "Approved. High quality evidence."
    }
    
    # Execute Judge
    with patch.object(Judge.APIManager, 'cached_api_call') as mock_api:
        mock_api.return_value = mock_response
        
        # ... (run Judge logic)
    
    # Assert quality scores present in version history
    with open(version_history_file) as f:
        history = json.load(f)
    
    claim = history["quality_test.pdf"][-1]["review"]["Requirement(s)"][0]
    assert "evidence_quality" in claim
    assert claim["evidence_quality"]["composite_score"] == 4.2
```

## Success Criteria

- [ ] literature_review/analysis/judge.py prompt includes 6-dimensional scoring instructions
- [ ] literature_review/analysis/judge.py validates score ranges (1-5 for most, 1-3 for directness)
- [ ] Composite score calculation matches formula
- [ ] Approval threshold enforced (composite ≥3.0, strength ≥3, relevance ≥3)
- [ ] Version history stores quality scores
- [ ] Orchestrator uses scores for weighted gap analysis
- [ ] Visualization shows quality distribution
- [ ] Unit tests pass (100% coverage for scoring logic)
- [ ] Integration tests validate end-to-end flow
- [ ] Documentation updated with scoring methodology

## Migration Strategy

**Backward Compatibility:**

```python
def migrate_existing_claims():
    """Add default scores to claims without evidence_quality."""
    with open('review_version_history.json', 'r') as f:
        history = json.load(f)
    
    for filename, versions in history.items():
        for version in versions:
            claims = version.get('review', {}).get('Requirement(s)', [])
            for claim in claims:
                if 'evidence_quality' not in claim and claim.get('status') == 'approved':
                    # Assign default moderate scores
                    claim['evidence_quality'] = {
                        "strength_score": 3,
                        "strength_rationale": "Legacy claim (default score)",
                        "rigor_score": 3,
                        "study_type": "unknown",
                        "relevance_score": 3,
                        "relevance_notes": "Legacy claim",
                        "directness": 2,
                        "is_recent": False,
                        "reproducibility_score": 3,
                        "composite_score": 3.0,
                        "confidence_level": "medium"
                    }
    
    with open('review_version_history.json', 'w') as f:
        json.dump(history, f, indent=2)
```

---

**Status:** Ready for implementation  
**Wave:** Wave 2 (Weeks 3-4)  
**Next Steps:** Implement literature_review/analysis/judge.py enhancements, update version history schema, add literature_review/orchestrator.py weighted analysis
