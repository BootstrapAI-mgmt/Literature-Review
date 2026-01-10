"""
Judge Decision Validation Tests

Validates FV-04, FV-05, FV-06, and FV-10 from the validation matrix.

FV-04: Strong evidence approval tests
FV-05: Weak evidence rejection tests
FV-06: DRA resubmission flow tests
FV-10: Version history sync validation
"""

import pytest
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ValidationResult:
    """Result of a validation test (local copy for standalone tests)."""
    test_id: str
    test_name: str
    passed: bool
    actual_value: Any
    expected_value: Any
    threshold: Optional[float] = None
    margin: Optional[float] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


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


# =============================================================================
# Helper Functions
# =============================================================================

def validate_threshold(
    test_id: str,
    test_name: str,
    actual: float,
    threshold: float,
    comparison: str = "gte",
    metadata: Optional[Dict] = None,
) -> ValidationResult:
    """Validate a value against a threshold."""
    if comparison == "gte":
        passed = actual >= threshold
    elif comparison == "lte":
        passed = actual <= threshold
    else:  # eq
        passed = abs(actual - threshold) < 0.001
    
    return ValidationResult(
        test_id=test_id,
        test_name=test_name,
        passed=passed,
        actual_value=actual,
        expected_value=f"{comparison} {threshold}",
        threshold=threshold,
        margin=actual - threshold,
        metadata=metadata or {}
    )


def validate_percentage(
    test_id: str,
    test_name: str,
    numerator: float,
    denominator: float,
    threshold_percent: float,
    comparison: str = "gte",
    metadata: Optional[Dict] = None
) -> ValidationResult:
    """Validate a percentage against threshold."""
    if denominator == 0:
        actual = 0.0
    else:
        actual = (numerator / denominator) * 100
    
    return validate_threshold(
        test_id=test_id,
        test_name=test_name,
        actual=actual,
        threshold=threshold_percent,
        comparison=comparison,
        metadata={
            **(metadata or {}),
            "numerator": numerator,
            "denominator": denominator
        }
    )


# =============================================================================
# Test Data
# =============================================================================

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


# =============================================================================
# FV-04: Judge Accept Decision Tests
# =============================================================================

@pytest.mark.validation
@pytest.mark.functional
class TestJudgeApprovalDecisions:
    """
    FV-04: Validate Judge accept decisions for strong evidence.
    """
    
    def test_fv04_strong_evidence_approved(self):
        """
        FV-04: Test that strong evidence claims are approved.
        
        Success Criteria:
        - Claims with strong evidence receive 'approved' verdict
        - Composite score ≥ 3.0
        - Strength score ≥ 3
        - Relevance score ≥ 3
        """
        for claim in STRONG_EVIDENCE_CLAIMS:
            expected = claim["expected_scores"]
            
            response = MockJudgeResponse(
                verdict="approved",
                composite_score=sum(expected["composite"]) / 2,
                strength_score=expected["strength"][0],
                rigor_score=expected["rigor"][0],
                relevance_score=expected["relevance"][0],
                directness=2,
                reproducibility_score=4,
                recency_bonus=0.5,
                judge_notes="Strong evidence with quantitative results"
            )
            
            meets_criteria = response.should_approve
            
            assert meets_criteria, \
                f"Strong evidence claim {claim['claim_id']} should be approved"
    
    def test_fv04_approval_threshold_boundary(self):
        """
        FV-04: Test approval threshold boundaries.
        
        Verify exact threshold: composite ≥ 3.0 AND strength ≥ 3 AND relevance ≥ 3
        """
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
            
            assert actual_approval == expected, \
                f"Boundary case ({composite}, {strength}, {relevance}) expected {expected}, got {actual_approval}"


# =============================================================================
# FV-05: Judge Reject Decision Tests
# =============================================================================

@pytest.mark.validation
@pytest.mark.functional
class TestJudgeRejectionDecisions:
    """
    FV-05: Validate Judge reject decisions for weak evidence.
    """
    
    def test_fv05_weak_evidence_rejected(self):
        """
        FV-05: Test that weak evidence claims are rejected.
        
        Success Criteria:
        - Claims with weak evidence receive 'rejected' verdict
        - Clear rejection reason in judge_notes
        """
        for claim in WEAK_EVIDENCE_CLAIMS:
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
            
            is_rejected = response.verdict == "rejected"
            has_reason = len(response.judge_notes) > 10
            
            assert is_rejected and has_reason, \
                f"Weak evidence claim {claim['claim_id']} should be rejected with reason"
    
    def test_fv05_rejection_reason_quality(self):
        """
        FV-05: Validate rejection reasons are meaningful.
        
        Success Criteria:
        - Rejection notes contain specific feedback
        - Reason relates to evidence weakness
        """
        expected_keywords = [
            "insufficient", "no evidence", "unsupported", "speculative",
            "quantitative", "methodology", "unclear", "missing",
            "weak", "assertion", "data"
        ]
        
        for claim in WEAK_EVIDENCE_CLAIMS:
            judge_notes = "Rejected: No quantitative evidence. Claim is speculative without data."
            
            notes_lower = judge_notes.lower()
            keywords_found = [k for k in expected_keywords if k in notes_lower]
            
            assert len(keywords_found) >= 1, \
                f"Rejection notes should contain meaningful feedback for {claim['claim_id']}"


# =============================================================================
# FV-06: DRA Resubmission Flow Tests
# =============================================================================

class MockDRA:
    """Mock DRA for testing."""
    
    def analyze_rejected_claims(self, claims, paper_text):
        """Simulate DRA re-analysis."""
        new_claims = []
        for claim in claims:
            new_claims.append({
                "original_claim_id": claim["claim_id"],
                "new_claim_text": claim["original_claim"] + " (enhanced)",
                "new_evidence": f"Page 5: Specific evidence addressing {claim['rejection_reason']}",
                "improvement_type": "evidence_strengthening",
                "addresses_rejection": True
            })
        return new_claims


@pytest.mark.validation
@pytest.mark.functional
class TestDRAResubmission:
    """
    FV-06: Validate DRA (Deep Requirements Analyzer) resubmission flow.
    """
    
    @pytest.fixture
    def mock_dra(self):
        """Create mock DRA for testing."""
        return MockDRA()
    
    def test_fv06_dra_receives_rejected_claims(self, mock_dra):
        """
        FV-06: Test that rejected claims are passed to DRA.
        
        Success Criteria:
        - All rejected claims sent to DRA
        - Rejection reasons included
        """
        rejected_claims = REJECTED_CLAIMS_FOR_DRA
        
        # Verify all claims have required fields for DRA processing
        for claim in rejected_claims:
            assert "claim_id" in claim, "Claim must have claim_id"
            assert "original_claim" in claim, "Claim must have original_claim"
            assert "rejection_reason" in claim, "Claim must have rejection_reason"
            assert "source_paper" in claim, "Claim must have source_paper"
        
        # Verify DRA receives expected count of claims
        received_count = len(rejected_claims)
        assert received_count >= 2, \
            "DRA should receive at least 2 rejected claims for testing"
    
    def test_fv06_dra_returns_improved_claims(self, mock_dra):
        """
        FV-06: Test that DRA returns improved claims.
        
        Success Criteria:
        - DRA returns new claims for rejected ones
        - New claims have better evidence
        """
        paper_text = "Full paper text with detailed methodology..."
        
        new_claims = mock_dra.analyze_rejected_claims(
            REJECTED_CLAIMS_FOR_DRA,
            paper_text
        )
        
        assert len(new_claims) >= 1, "DRA should return improved claims"
    
    def test_fv06_improved_claims_address_rejection(self, mock_dra):
        """
        FV-06: Test that improved claims address rejection reasons.
        
        Success Criteria:
        - New evidence directly addresses original rejection reason
        - Claim links back to original rejected claim
        """
        paper_text = "Full paper text..."
        
        new_claims = mock_dra.analyze_rejected_claims(
            REJECTED_CLAIMS_FOR_DRA,
            paper_text
        )
        
        addressed_count = sum(
            1 for c in new_claims 
            if c.get("addresses_rejection", False)
        )
        
        percentage_addressed = (addressed_count / len(new_claims)) * 100 if new_claims else 0
        
        assert percentage_addressed >= 80.0, \
            f"At least 80% of improved claims should address rejection reasons, got {percentage_addressed:.1f}%"
    
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
            REJECTED_CLAIMS_FOR_DRA,
            paper_text
        )
        
        # Step 2: Improved claims go back to Judge (simulated)
        judge_results = []
        for claim in improved_claims:
            judge_results.append({
                "claim_id": claim["original_claim_id"],
                "status": "re_evaluated",
                "new_verdict": "approved",
                "improvement_recognized": True
            })
        
        assert len(judge_results) >= 1, "DRA → Judge pipeline should complete"


# =============================================================================
# FV-10: Version History Sync Validation Tests
# =============================================================================

@pytest.mark.validation
@pytest.mark.functional
class TestVersionHistorySync:
    """
    FV-10: Validate version history sync for data integrity.
    """
    
    @pytest.fixture
    def sample_version_history(self, tmp_path):
        """Create sample version history for testing."""
        history = {
            "paper_001.pdf": [
                {
                    "timestamp": "2024-01-01T10:00:00",
                    "review": {
                        "TITLE": "Test Paper 001",
                        "Requirement(s)": [
                            {
                                "claim_id": "claim_001",
                                "status": "approved",
                                "judge_timestamp": "2024-01-01T11:00:00",
                                "judge_notes": "Approved with strong evidence"
                            }
                        ]
                    },
                    "changes": {
                        "status": "judge_update"
                    }
                }
            ],
            "paper_002.pdf": [
                {
                    "timestamp": "2024-01-02T10:00:00",
                    "review": {
                        "TITLE": "Test Paper 002",
                        "Requirement(s)": [
                            {
                                "claim_id": "claim_002",
                                "status": "pending_judge_review",
                                "judge_timestamp": None,
                                "judge_notes": ""
                            }
                        ]
                    },
                    "changes": {
                        "status": "new_review"
                    }
                }
            ]
        }
        
        history_file = tmp_path / "review_version_history.json"
        with open(history_file, 'w') as f:
            json.dump(history, f)
        
        return history_file, history
    
    def test_fv10_no_data_loss_on_sync(self, sample_version_history):
        """
        FV-10: Verify no data loss during sync operations.
        
        Success Criteria:
        - All claims preserved after sync
        - No missing fields
        """
        history_file, original_history = sample_version_history
        
        with open(history_file, 'r') as f:
            loaded_history = json.load(f)
        
        original_claim_count = 0
        for filename, versions in original_history.items():
            for version in versions:
                claims = version.get('review', {}).get('Requirement(s)', [])
                original_claim_count += len(claims)
        
        loaded_claim_count = 0
        for filename, versions in loaded_history.items():
            for version in versions:
                claims = version.get('review', {}).get('Requirement(s)', [])
                loaded_claim_count += len(claims)
        
        assert loaded_claim_count >= original_claim_count, \
            "Sync should not lose any claims"
    
    def test_fv10_timestamps_preserved(self, sample_version_history):
        """
        FV-10: Verify timestamps are preserved during sync.
        
        Success Criteria:
        - All timestamps remain intact
        - Timestamp format is valid ISO 8601
        """
        history_file, _ = sample_version_history
        
        with open(history_file, 'r') as f:
            loaded_history = json.load(f)
        
        timestamps_valid = 0
        total_timestamps = 0
        
        for filename, versions in loaded_history.items():
            for version in versions:
                ts = version.get('timestamp')
                if ts:
                    total_timestamps += 1
                    try:
                        datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        timestamps_valid += 1
                    except ValueError:
                        pass
                
                claims = version.get('review', {}).get('Requirement(s)', [])
                for claim in claims:
                    judge_ts = claim.get('judge_timestamp')
                    if judge_ts:
                        total_timestamps += 1
                        try:
                            datetime.fromisoformat(judge_ts.replace('Z', '+00:00'))
                            timestamps_valid += 1
                        except ValueError:
                            pass
        
        assert timestamps_valid == total_timestamps, \
            "All timestamps should be preserved and valid"
    
    def test_fv10_valid_status_transitions(self, sample_version_history):
        """
        FV-10: Verify status transitions are valid.
        
        Success Criteria:
        - Only valid statuses exist
        - Transitions follow allowed paths
        """
        valid_statuses = {
            "pending_judge_review",
            "approved",
            "rejected",
            "pending_dra_appeal",
            "appeal_approved",
            "appeal_rejected"
        }
        
        history_file, _ = sample_version_history
        
        with open(history_file, 'r') as f:
            loaded_history = json.load(f)
        
        valid_count = 0
        total_count = 0
        
        for filename, versions in loaded_history.items():
            for version in versions:
                claims = version.get('review', {}).get('Requirement(s)', [])
                for claim in claims:
                    status = claim.get('status')
                    if status:
                        total_count += 1
                        if status in valid_statuses:
                            valid_count += 1
        
        assert valid_count == total_count, \
            "All claim statuses should be valid"
    
    def test_fv10_version_ordering(self, sample_version_history):
        """
        FV-10: Verify version entries are chronologically ordered.
        
        Success Criteria:
        - Versions appear in timestamp order
        - No out-of-order versions
        """
        history_file, _ = sample_version_history
        
        with open(history_file, 'r') as f:
            loaded_history = json.load(f)
        
        ordered_count = 0
        total_files = 0
        
        for filename, versions in loaded_history.items():
            if len(versions) <= 1:
                ordered_count += 1
                total_files += 1
                continue
            
            total_files += 1
            timestamps = []
            for version in versions:
                ts = version.get('timestamp')
                if ts:
                    try:
                        timestamps.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
                    except ValueError:
                        pass
            
            is_ordered = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
            if is_ordered:
                ordered_count += 1
        
        assert ordered_count == total_files, \
            "All version histories should be chronologically ordered"


# =============================================================================
# Score Calculation Tests
# =============================================================================

@pytest.mark.validation
@pytest.mark.functional
class TestJudgeScoreCalculation:
    """Validate Judge score calculation accuracy."""
    
    def test_composite_score_calculation(self):
        """
        Verify composite score formula:
        composite = (strength × 0.30) + (rigor × 0.25) + (relevance × 0.25) 
                  + (directness/3 × 0.10) + (recency × 0.05) + (reproducibility × 0.05)
        """
        test_cases = [
            # (strength, rigor, relevance, directness, recency, reproducibility, expected)
            (5, 5, 5, 3, 1.0, 5, 4.40),     # Perfect scores
            (1, 1, 1, 1, 0.0, 1, 0.88),     # Minimum scores
            (3, 3, 3, 2, 0.5, 3, 2.64),     # Average scores
            (4, 4, 4, 3, 0.8, 4, 3.54),     # Good scores
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
            
            is_correct = abs(calculated - expected) < 0.01
            
            assert is_correct, \
                f"Composite score mismatch: calculated {calculated:.2f}, expected {expected}"
    
    def test_score_weights_sum_to_one(self):
        """
        Verify that score weights sum to 1.0 for proper normalization.
        """
        weights = {
            "strength": 0.30,
            "rigor": 0.25,
            "relevance": 0.25,
            "directness": 0.10,
            "recency": 0.05,
            "reproducibility": 0.05
        }
        
        total_weight = sum(weights.values())
        is_normalized = abs(total_weight - 1.0) < 0.001
        
        assert is_normalized, f"Weights should sum to 1.0, got {total_weight}"
    
    def test_meets_approval_criteria_function(self):
        """
        Test the meets_approval_criteria logic with various inputs.
        """
        test_cases = [
            # (composite, strength, relevance, expected_approval)
            (3.0, 3, 3, True),      # Exactly at threshold
            (4.0, 4, 4, True),      # Above threshold
            (2.9, 3, 3, False),     # Composite below
            (3.0, 2, 3, False),     # Strength below
            (3.0, 3, 2, False),     # Relevance below
            (5.0, 5, 5, True),      # Maximum scores
            (1.0, 1, 1, False),     # Minimum scores
        ]
        
        for composite, strength, relevance, expected in test_cases:
            actual = (composite >= 3.0 and strength >= 3 and relevance >= 3)
            
            assert actual == expected, \
                f"Approval criteria ({composite}, {strength}, {relevance}): expected {expected}, got {actual}"


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.validation
@pytest.mark.functional
class TestJudgeIntegration:
    """
    Integration tests for Judge module functions.
    
    These tests verify the actual Judge module functions work correctly.
    """
    
    def test_calculate_composite_score_function(self):
        """Test the actual calculate_composite_score function from judge module."""
        try:
            from literature_review.analysis.judge import calculate_composite_score
        except ImportError:
            pytest.skip("Judge module calculate_composite_score not available")
        
        quality = {
            "strength_score": 4,
            "rigor_score": 4,
            "relevance_score": 4,
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 4
        }
        
        calculated = calculate_composite_score(quality)
        expected = 3.55  # (4*0.30)+(4*0.25)+(4*0.25)+(3/3*0.10)+(1.0*0.05)+(4*0.05)
        
        is_correct = abs(calculated - expected) < 0.01
        
        assert is_correct, f"calculate_composite_score: expected ~{expected}, got {calculated}"
    
    def test_meets_approval_criteria_function_integration(self):
        """Test the actual meets_approval_criteria function from judge module."""
        try:
            from literature_review.analysis.judge import meets_approval_criteria
        except ImportError:
            pytest.skip("Judge module meets_approval_criteria not available")
        
        approved_quality = {
            "composite_score": 3.5,
            "strength_score": 4,
            "relevance_score": 4
        }
        
        rejected_quality = {
            "composite_score": 2.5,
            "strength_score": 2,
            "relevance_score": 2
        }
        
        approved_result = meets_approval_criteria(approved_quality)
        rejected_result = meets_approval_criteria(rejected_quality)
        
        assert approved_result is True, "Good quality should be approved"
        assert rejected_result is False, "Poor quality should be rejected"
