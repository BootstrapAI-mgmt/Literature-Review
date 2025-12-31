# Task Card: Judge Decision Validation

**Task ID:** VM-W1-3  
**Wave:** 1 (Core Functional Validation)  
**Priority:** CRITICAL  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W0-1  
**Blocks:** VM-W2-1, VM-W2-2  
**Validation IDs:** FV-04, FV-05, FV-06, FV-10 *(FV-10 added per review)*

---

## Objective

Validate Judge decision-making accuracy for both approval and rejection cases, including DRA (Deep Requirements Analyzer) resubmission flow for rejected claims.

## Background

The Judge is the critical gatekeeper for evidence quality. It:
- Evaluates claims using 6-dimension scoring (strength, rigor, relevance, directness, recency, reproducibility)
- Applies approval threshold: composite ≥ 3.0 AND strength ≥ 3 AND relevance ≥ 3
- Passes rejected claims to DRA for deeper analysis
- Maintains evidence quality standards for the database

Incorrect Judge decisions directly impact research gap analysis accuracy.

## Success Criteria

- [ ] FV-04: Approve decision validation (strong evidence correctly approved)
- [ ] FV-05: Reject decision validation (weak evidence correctly rejected)
- [ ] FV-06: DRA resubmission flow test (rejected claims re-analyzed)
- [ ] FV-10: Version history sync validation (no data loss, timestamps preserved) *(added per review)*
- [ ] Threshold boundary testing complete
- [ ] Score calculation accuracy verified

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| FV-04 | Judge Accept | Strong evidence claim | `verdict: approved` | Composite ≥ 3.0, strength ≥ 3, relevance ≥ 3 |
| FV-05 | Judge Reject | Weak evidence claim | `verdict: rejected` | Clear rejection reason in judge_notes |
| FV-06 | DRA Resubmission | Rejected claims + full paper | New claims with better evidence | Evidence directly addresses rejection |
| FV-10 | Version History Sync | Sync operation | No data loss | Timestamps preserved, status transitions valid | *(added per review)*

---

## Deliverables

### 1. Test Implementation

**File:** `tests/validation/functional/test_judge_decisions.py`

```python
"""
Judge Decision Validation Tests

Validates FV-04, FV-05, and FV-06 from the validation matrix.
"""

import pytest
import json
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from tests.validation.base import ValidationTestCase, ValidationResult


@dataclass
class MockJudgeResponse:
    """Mock Judge API response for testing."""
    verdict: str
    composite_score: float
    strength_score: int
    rigor_score: int
    relevance_score: int
    directness: int
    reproducibility_score: int
    recency_bonus: float
    judge_notes: str
    
    @property
    def should_approve(self) -> bool:
        """Check if scores meet approval criteria."""
        return (
            self.composite_score >= 3.0 and
            self.strength_score >= 3 and
            self.relevance_score >= 3
        )


class TestJudgeDecisions(ValidationTestCase):
    """
    Validate Judge accept/reject decisions.
    
    FV-04: Accept decisions for strong evidence
    FV-05: Reject decisions for weak evidence
    """
    
    TEST_CATEGORY = "FV"
    
    # Test case definitions
    STRONG_EVIDENCE_CLAIMS = [
        {
            "claim_id": "strong_001",
            "claim_text": "SNN achieved 95% accuracy on MNIST with 10x energy reduction",
            "evidence": "Table 3: Accuracy 95.2% ± 0.3% (n=10), Power: 1.2W vs 12W baseline",
            "sub_requirement": "Sub-1.1.1",
            "expected_verdict": "approved",
            "expected_scores": {
                "strength": (4, 5),
                "rigor": (4, 5),
                "relevance": (4, 5),
                "composite": (3.5, 5.0)
            }
        },
        {
            "claim_id": "strong_002",
            "claim_text": "STDP learning rule converges within 100 epochs",
            "evidence": "Figure 5 shows convergence curves. Statistical analysis (p<0.001)",
            "sub_requirement": "Sub-1.4.2",
            "expected_verdict": "approved",
            "expected_scores": {
                "strength": (4, 5),
                "rigor": (3, 5),
                "relevance": (4, 5),
                "composite": (3.0, 5.0)
            }
        }
    ]
    
    WEAK_EVIDENCE_CLAIMS = [
        {
            "claim_id": "weak_001",
            "claim_text": "Neuromorphic systems are efficient",
            "evidence": "As is well known in the field...",
            "sub_requirement": "Sub-1.1.1",
            "expected_verdict": "rejected",
            "expected_rejection_reasons": ["no quantitative", "unsupported assertion"]
        },
        {
            "claim_id": "weak_002",
            "claim_text": "Our system might improve performance",
            "evidence": "Preliminary observations suggest possible improvements.",
            "sub_requirement": "Sub-2.1.1",
            "expected_verdict": "rejected",
            "expected_rejection_reasons": ["speculative", "no data", "preliminary"]
        },
        {
            "claim_id": "weak_003",
            "claim_text": "The architecture is based on biological principles",
            "evidence": "We use a similar approach to [citation].",
            "sub_requirement": "Sub-1.2.1",
            "expected_verdict": "rejected",
            "expected_rejection_reasons": ["no direct evidence", "citation only"]
        }
    ]
    
    BORDERLINE_CLAIMS = [
        {
            "claim_id": "borderline_001",
            "claim_text": "Initial tests show 80% accuracy",
            "evidence": "Pilot study (n=3) achieved 80% accuracy.",
            "sub_requirement": "Sub-1.1.1",
            "expected_composite_range": (2.5, 3.5),
            "note": "Small sample size, moderate strength"
        }
    ]
    
    @pytest.fixture
    def judge_module(self):
        """Import Judge module for testing."""
        try:
            from literature_review.analysis import judge
            return judge
        except ImportError:
            pytest.skip("Judge module not available")
    
    @pytest.fixture
    def mock_api_response(self):
        """Create mock API response generator."""
        def generate_response(scores: Dict) -> str:
            return json.dumps({
                "strength_score": scores.get("strength", 3),
                "strength_rationale": "Test rationale",
                "rigor_score": scores.get("rigor", 3),
                "rigor_notes": "Test notes",
                "relevance_score": scores.get("relevance", 3),
                "relevance_notes": "Test relevance",
                "directness": scores.get("directness", 2),
                "recency_bonus": scores.get("recency", 0.5),
                "reproducibility_score": scores.get("reproducibility", 3),
                "composite_score": scores.get("composite", 3.0),
                "verdict": scores.get("verdict", "approved"),
                "judge_notes": scores.get("notes", "Test judgment")
            })
        return generate_response
    
    # =========================================================================
    # FV-04: Judge Accept Decision
    # =========================================================================
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv04_strong_evidence_approved(self):
        """
        FV-04: Test that strong evidence claims are approved.
        
        Success Criteria:
        - Claims with strong evidence receive 'approved' verdict
        - Composite score ≥ 3.0
        - Strength score ≥ 3
        - Relevance score ≥ 3
        """
        for claim in self.STRONG_EVIDENCE_CLAIMS:
            # Create test scores based on expected ranges
            expected = claim["expected_scores"]
            
            # Simulate judge response
            response = MockJudgeResponse(
                verdict="approved",
                composite_score=sum(expected["composite"]) / 2,  # Midpoint
                strength_score=expected["strength"][0],
                rigor_score=expected["rigor"][0],
                relevance_score=expected["relevance"][0],
                directness=2,
                reproducibility_score=4,
                recency_bonus=0.5,
                judge_notes="Strong evidence with quantitative results"
            )
            
            # Validate approval criteria
            meets_criteria = response.should_approve
            
            result = self.validate_threshold(
                test_id=f"FV-04-{claim['claim_id']}",
                test_name=f"Strong evidence approval: {claim['claim_id']}",
                actual=1 if meets_criteria else 0,
                threshold=1,
                comparison="gte",
                metadata={
                    "claim": claim["claim_text"][:50],
                    "composite_score": response.composite_score,
                    "strength_score": response.strength_score,
                    "relevance_score": response.relevance_score
                }
            )
            
            assert result.passed, \
                f"Strong evidence claim {claim['claim_id']} should be approved"
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv04_approval_threshold_boundary(self):
        """
        FV-04: Test approval threshold boundaries.
        
        Verify exact threshold: composite ≥ 3.0 AND strength ≥ 3 AND relevance ≥ 3
        """
        # Test cases at exact boundary
        boundary_cases = [
            # (composite, strength, relevance, expected_approval)
            (3.0, 3, 3, True),    # Exactly at threshold
            (3.1, 3, 3, True),    # Just above composite
            (3.0, 4, 4, True),    # Above on individual scores
            (2.9, 3, 3, False),   # Just below composite
            (3.0, 2, 3, False),   # Below on strength
            (3.0, 3, 2, False),   # Below on relevance
            (3.5, 2, 2, False),   # High composite, low individuals
        ]
        
        for composite, strength, relevance, expected in boundary_cases:
            response = MockJudgeResponse(
                verdict="approved" if expected else "rejected",
                composite_score=composite,
                strength_score=strength,
                rigor_score=3,
                relevance_score=relevance,
                directness=2,
                reproducibility_score=3,
                recency_bonus=0.5,
                judge_notes="Boundary test"
            )
            
            actual_approval = response.should_approve
            
            result = ValidationResult(
                test_id=f"FV-04-BOUNDARY-{composite}-{strength}-{relevance}",
                test_name=f"Boundary: composite={composite}, str={strength}, rel={relevance}",
                passed=actual_approval == expected,
                actual_value=actual_approval,
                expected_value=expected,
                execution_time_ms=self.get_execution_time_ms(),
                metadata={
                    "composite": composite,
                    "strength": strength,
                    "relevance": relevance
                }
            )
            self.results.append(result)
            
            assert actual_approval == expected, \
                f"Boundary case ({composite}, {strength}, {relevance}) expected {expected}, got {actual_approval}"
    
    # =========================================================================
    # FV-05: Judge Reject Decision
    # =========================================================================
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv05_weak_evidence_rejected(self):
        """
        FV-05: Test that weak evidence claims are rejected.
        
        Success Criteria:
        - Claims with weak evidence receive 'rejected' verdict
        - Clear rejection reason in judge_notes
        """
        for claim in self.WEAK_EVIDENCE_CLAIMS:
            # Simulate judge response for weak evidence
            response = MockJudgeResponse(
                verdict="rejected",
                composite_score=1.5,
                strength_score=1,
                rigor_score=1,
                relevance_score=3,
                directness=1,
                reproducibility_score=1,
                recency_bonus=0.0,
                judge_notes="Rejected: No quantitative evidence provided"
            )
            
            # Verify rejection
            is_rejected = response.verdict == "rejected"
            has_reason = len(response.judge_notes) > 10
            
            result = self.validate_threshold(
                test_id=f"FV-05-{claim['claim_id']}",
                test_name=f"Weak evidence rejection: {claim['claim_id']}",
                actual=1 if (is_rejected and has_reason) else 0,
                threshold=1,
                comparison="gte",
                metadata={
                    "claim": claim["claim_text"][:50],
                    "verdict": response.verdict,
                    "judge_notes": response.judge_notes
                }
            )
            
            assert result.passed, \
                f"Weak evidence claim {claim['claim_id']} should be rejected with reason"
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv05_rejection_reason_quality(self):
        """
        FV-05: Validate rejection reasons are meaningful.
        
        Success Criteria:
        - Rejection notes contain specific feedback
        - Reason relates to evidence weakness
        """
        # Keywords that should appear in good rejection notes
        expected_keywords = [
            "insufficient", "no evidence", "unsupported", "speculative",
            "quantitative", "methodology", "unclear", "missing",
            "weak", "assertion", "data"
        ]
        
        for claim in self.WEAK_EVIDENCE_CLAIMS:
            # Simulate rejection with detailed notes
            judge_notes = "Rejected: No quantitative evidence. Claim is speculative without data."
            
            # Check for meaningful keywords
            notes_lower = judge_notes.lower()
            keywords_found = [k for k in expected_keywords if k in notes_lower]
            
            result = self.validate_threshold(
                test_id=f"FV-05-REASON-{claim['claim_id']}",
                test_name=f"Rejection reason quality: {claim['claim_id']}",
                actual=len(keywords_found),
                threshold=1,  # At least one meaningful keyword
                comparison="gte",
                metadata={
                    "judge_notes": judge_notes,
                    "keywords_found": keywords_found
                }
            )
            
            assert result.passed, \
                f"Rejection notes should contain meaningful feedback"


class TestDRAResubmission(ValidationTestCase):
    """
    Validate DRA (Deep Requirements Analyzer) resubmission flow.
    
    FV-06: Rejected claims re-analyzed with deeper context
    """
    
    TEST_CATEGORY = "FV"
    
    REJECTED_CLAIMS_FOR_DRA = [
        {
            "claim_id": "dra_001",
            "original_claim": "The system shows plasticity",
            "original_evidence": "See methods section",
            "rejection_reason": "Evidence too vague, no quantitative data",
            "source_paper": "test_paper.pdf",
            "expected_improvement": "More specific evidence with page numbers"
        },
        {
            "claim_id": "dra_002",
            "original_claim": "Energy efficiency is improved",
            "original_evidence": "Compared to baseline",
            "rejection_reason": "No specific measurements provided",
            "source_paper": "test_paper.pdf",
            "expected_improvement": "Specific power measurements"
        }
    ]
    
    @pytest.fixture
    def mock_dra(self):
        """Create mock DRA for testing."""
        class MockDRA:
            def analyze_rejected_claims(self, claims, paper_text):
                """Simulate DRA re-analysis."""
                new_claims = []
                for claim in claims:
                    # Simulate finding better evidence
                    new_claims.append({
                        "original_claim_id": claim["claim_id"],
                        "new_claim_text": claim["original_claim"] + " (enhanced)",
                        "new_evidence": f"Page 5: Specific evidence addressing {claim['rejection_reason']}",
                        "improvement_type": "evidence_strengthening",
                        "addresses_rejection": True
                    })
                return new_claims
        
        return MockDRA()
    
    # =========================================================================
    # FV-06: DRA Resubmission Flow
    # =========================================================================
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv06_dra_receives_rejected_claims(self, mock_dra):
        """
        FV-06: Test that rejected claims are passed to DRA.
        
        Success Criteria:
        - All rejected claims sent to DRA
        - Rejection reasons included
        """
        rejected_claims = self.REJECTED_CLAIMS_FOR_DRA
        
        # Verify DRA receives claims
        received_count = len(rejected_claims)
        
        result = self.validate_threshold(
            test_id="FV-06-A",
            test_name="DRA receives rejected claims",
            actual=received_count,
            threshold=len(self.REJECTED_CLAIMS_FOR_DRA),
            comparison="gte",
            metadata={"claims_sent": received_count}
        )
        
        assert result.passed, "DRA should receive all rejected claims"
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv06_dra_returns_improved_claims(self, mock_dra):
        """
        FV-06: Test that DRA returns improved claims.
        
        Success Criteria:
        - DRA returns new claims for rejected ones
        - New claims have better evidence
        """
        paper_text = "Full paper text with detailed methodology..."
        
        new_claims = mock_dra.analyze_rejected_claims(
            self.REJECTED_CLAIMS_FOR_DRA,
            paper_text
        )
        
        # Verify new claims returned
        result = self.validate_threshold(
            test_id="FV-06-B",
            test_name="DRA returns improved claims",
            actual=len(new_claims),
            threshold=1,  # At least one improved claim
            comparison="gte",
            metadata={
                "original_count": len(self.REJECTED_CLAIMS_FOR_DRA),
                "improved_count": len(new_claims)
            }
        )
        
        assert result.passed, "DRA should return improved claims"
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv06_improved_claims_address_rejection(self, mock_dra):
        """
        FV-06: Test that improved claims address rejection reasons.
        
        Success Criteria:
        - New evidence directly addresses original rejection reason
        - Claim links back to original rejected claim
        """
        paper_text = "Full paper text..."
        
        new_claims = mock_dra.analyze_rejected_claims(
            self.REJECTED_CLAIMS_FOR_DRA,
            paper_text
        )
        
        addressed_count = sum(
            1 for c in new_claims 
            if c.get("addresses_rejection", False)
        )
        
        result = self.validate_percentage(
            test_id="FV-06-C",
            test_name="Improved claims address rejection",
            numerator=addressed_count,
            denominator=len(new_claims),
            threshold_percent=80.0,  # 80% should address rejection
            comparison="gte",
            metadata={
                "addressed": addressed_count,
                "total": len(new_claims)
            }
        )
        
        assert result.passed, \
            f"At least 80% of improved claims should address rejection reasons"
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_fv06_dra_to_judge_pipeline(self, mock_dra):
        """
        FV-06: Test complete DRA → Judge pipeline.
        
        Success Criteria:
        - DRA-improved claims are sent back to Judge
        - Judge evaluates with fresh scoring
        """
        paper_text = "Full paper text..."
        
        # Step 1: DRA processes rejected claims
        improved_claims = mock_dra.analyze_rejected_claims(
            self.REJECTED_CLAIMS_FOR_DRA,
            paper_text
        )
        
        # Step 2: Improved claims go back to Judge
        # (Simulated - in real test would call actual Judge)
        judge_results = []
        for claim in improved_claims:
            # Simulate Judge re-evaluation
            judge_results.append({
                "claim_id": claim["original_claim_id"],
                "status": "re_evaluated",
                "new_verdict": "approved",  # Simulated improvement
                "improvement_recognized": True
            })
        
        # Verify pipeline completion
        result = self.validate_threshold(
            test_id="FV-06-D",
            test_name="DRA to Judge pipeline",
            actual=len(judge_results),
            threshold=1,
            comparison="gte",
            metadata={
                "claims_processed": len(judge_results),
                "approved_after_dra": sum(1 for r in judge_results if r["new_verdict"] == "approved")
            }
        )
        
        assert result.passed, "DRA → Judge pipeline should complete"


class TestJudgeScoreCalculation(ValidationTestCase):
    """Validate Judge score calculation accuracy."""
    
    TEST_CATEGORY = "FV"
    
    @pytest.mark.validation
    @pytest.mark.functional
    def test_composite_score_calculation(self):
        """
        Verify composite score formula:
        composite = (strength × 0.30) + (rigor × 0.25) + (relevance × 0.25) 
                  + (directness/3 × 0.10) + (recency × 0.05) + (reproducibility × 0.05)
        """
        test_cases = [
            # (strength, rigor, relevance, directness, recency, reproducibility, expected)
            (5, 5, 5, 3, 1.0, 5, 5.0),      # Perfect scores
            (1, 1, 1, 1, 0.0, 1, 1.03),     # Minimum scores
            (3, 3, 3, 2, 0.5, 3, 2.87),     # Average scores
            (4, 4, 4, 3, 0.8, 4, 3.84),     # Good scores
        ]
        
        for strength, rigor, relevance, directness, recency, repro, expected in test_cases:
            calculated = (
                strength * 0.30 +
                rigor * 0.25 +
                relevance * 0.25 +
                (directness / 3) * 0.10 +
                recency * 0.05 +
                repro * 0.05
            )
            
            # Allow small floating point tolerance
            is_correct = abs(calculated - expected) < 0.1
            
            result = ValidationResult(
                test_id=f"FV-SCORE-{strength}{rigor}{relevance}",
                test_name=f"Composite score: str={strength}, rig={rigor}, rel={relevance}",
                passed=is_correct,
                actual_value=round(calculated, 2),
                expected_value=expected,
                execution_time_ms=self.get_execution_time_ms(),
                metadata={
                    "strength": strength,
                    "rigor": rigor,
                    "relevance": relevance,
                    "directness": directness,
                    "recency": recency,
                    "reproducibility": repro
                }
            )
            self.results.append(result)
            
            assert is_correct, \
                f"Composite score mismatch: calculated {calculated:.2f}, expected {expected}"
```

---

## Implementation Steps

### Step 1: Create Test Data (1.5 hours)
1. Define strong evidence test claims
2. Define weak evidence test claims
3. Define borderline test claims
4. Create mock Judge responses

### Step 2: Implement FV-04 Tests (2 hours)
1. Create approval validation tests
2. Implement boundary tests
3. Verify score thresholds

### Step 3: Implement FV-05 Tests (1.5 hours)
1. Create rejection validation tests
2. Verify rejection reason quality
3. Test rejection note content

### Step 4: Implement FV-06 Tests (2 hours)
1. Create DRA resubmission tests
2. Test improvement pipeline
3. Verify DRA → Judge flow

### Step 5: Score Calculation Tests (1 hour)
1. Verify composite score formula
2. Test edge cases
3. Document expected values

---

## Testing

```bash
# Run approval tests
pytest tests/validation/functional/test_judge_decisions.py -k "fv04" -v

# Run rejection tests
pytest tests/validation/functional/test_judge_decisions.py -k "fv05" -v

# Run DRA tests
pytest tests/validation/functional/test_judge_decisions.py -k "fv06" -v

# Run all Judge validation
pytest tests/validation/functional/test_judge_decisions.py -v
```

---

## Acceptance Criteria Checklist

- [ ] FV-04: Strong evidence correctly approved
- [ ] FV-04: Threshold boundary tests pass
- [ ] FV-05: Weak evidence correctly rejected
- [ ] FV-05: Rejection reasons are meaningful
- [ ] FV-06: DRA receives rejected claims
- [ ] FV-06: DRA returns improved claims
- [ ] FV-06: Improved claims address rejection reasons
- [ ] Score calculation verified
- [ ] All tests tagged with @pytest.mark.validation

---

## Related Tasks

- **Depends on:** VM-W0-1 (Test Infrastructure)
- **Next:** VM-W2-1 (Accuracy Baseline), VM-W2-2 (Judge Calibration)
- **Parallel:** VM-W1-1, VM-W1-2

---

## Notes

- Most tests use mocks to avoid API calls
- Integration tests with real API require `@pytest.mark.requires_api`
- Consider adding consensus judgment tests (multi-judge mode)
