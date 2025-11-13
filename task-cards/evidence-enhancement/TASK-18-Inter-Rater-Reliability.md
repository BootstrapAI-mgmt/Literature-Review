# TASK CARD #18: Inter-Rater Reliability (Multi-Judge Consensus)

**Priority:** 🟡 MEDIUM  
**Estimated Effort:** 6-8 hours  
**Risk Level:** MEDIUM  
**Wave:** Wave 3 (Weeks 5-6)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Card #16 (Evidence Scoring)  
**Blocks:** None

## Problem Statement

Current system uses single Judge evaluation per claim. For borderline cases (composite_score 2.5-3.5), a single judgment may not be reliable due to:
- LLM temperature variability
- Subjective interpretation of evidence
- No validation of borderline decisions
- Lack of confidence metrics

Multi-judge consensus provides higher confidence in critical decisions, especially for claims near the approval threshold where single-judge errors are most impactful.

## Acceptance Criteria

**Functional Requirements:**
- [ ] Judge.py supports multi-judge consensus mode
- [ ] 3 independent judgments per borderline claim
- [ ] Agreement rate calculated (67% threshold for strong consensus)
- [ ] Consensus metadata stored in version history
- [ ] Cost optimization: Apply only to borderline claims (composite 2.5-3.5)

**Consensus Classifications:**
- [ ] Strong consensus: ≥67% agreement (2/3 or 3/3 judges agree)
- [ ] Weak consensus: 50-66% agreement (simple majority)
- [ ] No consensus: <50% agreement (flagged for human review)

**Technical Requirements:**
- [ ] Temperature variation across judges (0.3, 0.4, 0.5) for diversity
- [ ] Parallel API calls where possible
- [ ] Score aggregation via averaging
- [ ] Agreement rate and standard deviation tracked

## Implementation Guide

**Files to Modify:**

### 1. literature_review/analysis/judge.py (~120 lines new)

```python
# Configuration
API_CONFIG = {
    "CONSENSUS_JUDGES": 3,  # Number of independent judgments
    "AGREEMENT_THRESHOLD": 0.67,  # 67% must agree (2 out of 3)
    "TIE_BREAKER_ENABLED": True,
    "BORDERLINE_SCORE_MIN": 2.5,  # Apply consensus to scores 2.5-3.5
    "BORDERLINE_SCORE_MAX": 3.5
}

def judge_with_consensus(claim: Dict, sub_req_def: str, api_manager) -> Dict:
    """
    Get multiple independent judgments and compute consensus.
    
    Args:
        claim: Claim dict to evaluate
        sub_req_def: Sub-requirement definition
        api_manager: API manager for Gemini calls
        
    Returns:
        Consensus judgment with aggregated scores and metadata
    """
    judgments = []
    
    for judge_num in range(API_CONFIG["CONSENSUS_JUDGES"]):
        # Each judge gets identical prompt but different temperature for diversity
        prompt = build_judge_prompt_enhanced(claim, sub_req_def)
        
        judgment = api_manager.call_api(
            prompt,
            temperature=0.3 + (judge_num * 0.1),  # 0.3, 0.4, 0.5
            cache_key=f"{claim['claim_id']}_judge_{judge_num}"
        )
        
        validated = validate_judge_response_enhanced(judgment)
        if validated:
            judgments.append(validated)
    
    # Require all judges to respond
    if len(judgments) < API_CONFIG["CONSENSUS_JUDGES"]:
        # Fall back to single judge if consensus fails
        return judgments[0] if judgments else None
    
    # Analyze agreement
    verdicts = [j["verdict"] for j in judgments]
    verdict_counts = {
        "approved": verdicts.count("approved"),
        "rejected": verdicts.count("rejected")
    }
    
    # Compute agreement
    majority_verdict = max(verdict_counts, key=verdict_counts.get)
    agreement_rate = verdict_counts[majority_verdict] / len(verdicts)
    
    # Classify consensus strength
    if agreement_rate >= API_CONFIG["AGREEMENT_THRESHOLD"]:
        consensus_status = "strong_consensus"
    elif agreement_rate >= 0.5:
        consensus_status = "weak_consensus"
    else:
        consensus_status = "no_consensus"
    
    # Aggregate scores (average across judges)
    composite_scores = [
        j["evidence_quality"]["composite_score"] 
        for j in judgments
    ]
    avg_composite_score = np.mean(composite_scores)
    score_std_dev = np.std(composite_scores)
    
    # Build consensus judgment
    consensus_judgment = {
        "verdict": majority_verdict,
        "consensus_metadata": {
            "total_judges": len(judgments),
            "agreement_rate": round(agreement_rate, 2),
            "consensus_status": consensus_status,
            "vote_breakdown": verdict_counts,
            "individual_judgments": judgments,
            "average_composite_score": round(avg_composite_score, 2),
            "score_std_dev": round(score_std_dev, 2),
            "requires_human_review": consensus_status == "no_consensus"
        },
        "evidence_quality": {
            **judgments[0]["evidence_quality"],  # Use first judge's detailed scores
            "composite_score": round(avg_composite_score, 2)  # Override with average
        },
        "judge_notes": f"{consensus_status.replace('_', ' ').title()}: {verdict_counts}"
    }
    
    return consensus_judgment

def should_use_consensus(claim: Dict) -> bool:
    """
    Determine if claim needs multi-judge consensus.
    
    Only apply to borderline claims (composite 2.5-3.5) to control costs.
    """
    # First, get single judge evaluation
    quality = claim.get("evidence_quality", {})
    composite = quality.get("composite_score")
    
    if composite is None:
        return False
    
    # Check if borderline
    return (API_CONFIG["BORDERLINE_SCORE_MIN"] <= composite <= 
            API_CONFIG["BORDERLINE_SCORE_MAX"])
```

### 2. literature_review/orchestrator.py Integration (~30 lines)

```python
def process_claim_with_adaptive_consensus(claim: Dict, sub_req_def: str, api_manager):
    """
    Intelligently apply consensus only where needed.
    
    Workflow:
    1. Single judge evaluation (fast, cheap)
    2. If borderline score → consensus (slow, expensive)
    3. If clear approve/reject → skip consensus
    """
    # Initial single-judge evaluation
    single_judgment = judge_claim(claim, sub_req_def, api_manager)
    
    # Check if needs consensus
    if should_use_consensus(single_judgment):
        # Borderline case: use multi-judge consensus
        consensus_judgment = judge_with_consensus(claim, sub_req_def, api_manager)
        return consensus_judgment
    else:
        # Clear decision: trust single judge
        return single_judgment
```

### 3. Version History Schema (~20 lines)

```python
# Claim with consensus metadata
claim_with_consensus = {
    "claim_id": "c1a2b3",
    "status": "approved",
    "verdict": "approved",
    "consensus_metadata": {
        "total_judges": 3,
        "agreement_rate": 0.67,
        "consensus_status": "strong_consensus",
        "vote_breakdown": {"approved": 2, "rejected": 1},
        "average_composite_score": 3.1,
        "score_std_dev": 0.25,
        "requires_human_review": False,
        "individual_judgments": [
            # Full judgment from each judge
            {...},
            {...},
            {...}
        ]
    },
    "evidence_quality": {
        "composite_score": 3.1,  # Average of 3 judges
        # ... other fields
    }
}
```

## Testing Strategy

### Unit Tests

```python
@pytest.mark.unit
def test_consensus_agreement_calculation():
    """Test agreement rate calculation."""
    judgments = [
        {"verdict": "approved", "evidence_quality": {"composite_score": 3.2}},
        {"verdict": "approved", "evidence_quality": {"composite_score": 3.0}},
        {"verdict": "rejected", "evidence_quality": {"composite_score": 2.8}}
    ]
    
    verdicts = [j["verdict"] for j in judgments]
    verdict_counts = {
        "approved": verdicts.count("approved"),
        "rejected": verdicts.count("rejected")
    }
    
    majority = "approved"
    agreement_rate = verdict_counts[majority] / len(verdicts)
    
    assert agreement_rate == 0.67  # 2 out of 3
    assert verdict_counts == {"approved": 2, "rejected": 1}

@pytest.mark.unit
def test_borderline_detection():
    """Test detection of borderline claims."""
    claim_borderline = {
        "evidence_quality": {"composite_score": 3.0}
    }
    assert should_use_consensus(claim_borderline) == True
    
    claim_clear_approve = {
        "evidence_quality": {"composite_score": 4.5}
    }
    assert should_use_consensus(claim_clear_approve) == False
    
    claim_clear_reject = {
        "evidence_quality": {"composite_score": 1.5}
    }
    assert should_use_consensus(claim_clear_reject) == False
```

### Integration Tests (Modify Task Card #6)

```python
from literature_review.analysis.judge import judge_with_consensus, should_use_consensus

@pytest.mark.integration
def test_consensus_for_borderline_claims(temp_workspace, mock_api_manager):
    """Test that borderline claims trigger consensus."""
    
    # Create borderline claim
    claim = {
        "claim_id": "test_borderline",
        "extracted_claim_text": "Some borderline claim..."
    }
    
    # Mock first judge: borderline score
    mock_api_manager.add_response({
        "verdict": "approved",
        "evidence_quality": {"composite_score": 3.0}
    })
    
    # Mock consensus judges
    mock_api_manager.add_responses([
        {"verdict": "approved", "evidence_quality": {"composite_score": 3.2}},
        {"verdict": "approved", "evidence_quality": {"composite_score": 2.9}},
        {"verdict": "rejected", "evidence_quality": {"composite_score": 2.7}}
    ])
    
    result = process_claim_with_adaptive_consensus(claim, "Sub-1.1.1", mock_api_manager)
    
    assert "consensus_metadata" in result
    assert result["consensus_metadata"]["total_judges"] == 3
    assert result["consensus_metadata"]["agreement_rate"] == 0.67
```

## Success Criteria

- [ ] Consensus logic correctly aggregates 3 judgments
- [ ] Agreement rate calculation accurate
- [ ] Consensus status classification correct (strong/weak/none)
- [ ] Only borderline claims (2.5-3.5) trigger consensus
- [ ] Score averaging and std dev calculated correctly
- [ ] No consensus cases flagged for human review
- [ ] Cost impact: <20% increase (only ~15-20% of claims are borderline)
- [ ] Unit tests pass (100% coverage for consensus logic)
- [ ] Integration tests validate adaptive consensus workflow

## Cost-Benefit Analysis

**Costs:**
- 3x API calls for borderline claims (~15-20% of total)
- Net increase: ~30-40% overall API costs

**Benefits:**
- Higher confidence in critical decisions
- Reduced false positives/negatives at threshold
- Explicit uncertainty flagging (no consensus → human review)
- Quality metric (low agreement = ambiguous claim)

**Mitigation:**
- Apply only to borderline range (2.5-3.5)
- Clear cases (>3.5 or <2.5) use single judge

---

**Status:** Ready for implementation  
**Wave:** Wave 3 (Weeks 5-6)  
**Next Steps:** Implement consensus logic in literature_review/analysis/judge.py, integrate with literature_review/orchestrator.py adaptive routing
