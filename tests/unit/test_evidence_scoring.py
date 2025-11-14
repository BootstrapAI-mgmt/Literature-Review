"""
Unit Tests for Evidence Scoring (Task Card #16)
Tests composite score calculation, validation, and approval criteria.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis.judge import (
    calculate_composite_score,
    validate_judge_response_enhanced,
    meets_approval_criteria
)


class TestCompositeScoreCalculation:
    """Test suite for calculate_composite_score function."""
    
    @pytest.mark.unit
    def test_composite_score_calculation_high_quality(self):
        """Test composite score formula with high-quality evidence."""
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
    def test_composite_score_calculation_moderate_quality(self):
        """Test composite score formula with moderate-quality evidence."""
        quality = {
            "strength_score": 3,
            "rigor_score": 3,
            "relevance_score": 3,
            "directness": 2,
            "is_recent": False,
            "reproducibility_score": 3
        }
        
        score = calculate_composite_score(quality)
        
        # Expected: (3*0.3) + (3*0.25) + (3*0.25) + (2/3*0.1) + (0*0.05) + (3*0.05)
        # = 0.9 + 0.75 + 0.75 + 0.067 + 0 + 0.15 = 2.617
        assert abs(score - 2.62) < 0.01
    
    @pytest.mark.unit
    def test_composite_score_calculation_low_quality(self):
        """Test composite score formula with low-quality evidence."""
        quality = {
            "strength_score": 1,
            "rigor_score": 1,
            "relevance_score": 1,
            "directness": 1,
            "is_recent": False,
            "reproducibility_score": 1
        }
        
        score = calculate_composite_score(quality)
        
        # Expected: (1*0.3) + (1*0.25) + (1*0.25) + (1/3*0.1) + (0*0.05) + (1*0.05)
        # = 0.3 + 0.25 + 0.25 + 0.033 + 0 + 0.05 = 0.883
        assert abs(score - 0.88) < 0.01
    
    @pytest.mark.unit
    def test_composite_score_with_recency_bonus(self):
        """Test that recency bonus affects composite score."""
        quality_with_recency = {
            "strength_score": 3,
            "rigor_score": 3,
            "relevance_score": 3,
            "directness": 2,
            "is_recent": True,
            "reproducibility_score": 3
        }
        
        quality_without_recency = quality_with_recency.copy()
        quality_without_recency["is_recent"] = False
        
        score_with = calculate_composite_score(quality_with_recency)
        score_without = calculate_composite_score(quality_without_recency)
        
        # Difference should be exactly 0.05 (the recency weight)
        assert abs((score_with - score_without) - 0.05) < 0.01
    
    @pytest.mark.unit
    def test_composite_score_directness_normalization(self):
        """Test that directness is properly normalized (divide by 3)."""
        quality_direct = {
            "strength_score": 3,
            "rigor_score": 3,
            "relevance_score": 3,
            "directness": 3,
            "is_recent": False,
            "reproducibility_score": 3
        }
        
        quality_indirect = quality_direct.copy()
        quality_indirect["directness"] = 1
        
        score_direct = calculate_composite_score(quality_direct)
        score_indirect = calculate_composite_score(quality_indirect)
        
        # Difference should be (3-1)/3 * 0.1 = 0.0667
        assert abs((score_direct - score_indirect) - 0.07) < 0.01


class TestValidateJudgeResponseEnhanced:
    """Test suite for validate_judge_response_enhanced function."""
    
    @pytest.mark.unit
    def test_valid_approved_response(self):
        """Test validation of valid approved response."""
        response = {
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
        
        result = validate_judge_response_enhanced(response)
        assert result == response
    
    @pytest.mark.unit
    def test_valid_rejected_response(self):
        """Test validation of valid rejected response."""
        response = {
            "verdict": "rejected",
            "evidence_quality": {
                "strength_score": 2,
                "strength_rationale": "Weak evidence",
                "rigor_score": 2,
                "study_type": "opinion",
                "relevance_score": 2,
                "relevance_notes": "Tangential relevance",
                "directness": 1,
                "is_recent": False,
                "reproducibility_score": 1,
                "composite_score": 1.8,
                "confidence_level": "low"
            },
            "judge_notes": "Rejected. Insufficient evidence quality."
        }
        
        result = validate_judge_response_enhanced(response)
        assert result == response
    
    @pytest.mark.unit
    def test_missing_verdict(self):
        """Test rejection when verdict is missing."""
        response = {
            "evidence_quality": {
                "strength_score": 4,
                "rigor_score": 5,
                "relevance_score": 4,
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 4,
                "composite_score": 4.2,
                "confidence_level": "high",
                "study_type": "experimental"
            },
            "judge_notes": "Test"
        }
        
        result = validate_judge_response_enhanced(response)
        assert result is None
    
    @pytest.mark.unit
    def test_missing_evidence_quality(self):
        """Test rejection when evidence_quality is missing."""
        response = {
            "verdict": "approved",
            "judge_notes": "Test"
        }
        
        result = validate_judge_response_enhanced(response)
        assert result is None
    
    @pytest.mark.unit
    def test_invalid_verdict_value(self):
        """Test rejection when verdict has invalid value."""
        response = {
            "verdict": "maybe",
            "evidence_quality": {
                "strength_score": 4,
                "rigor_score": 5,
                "relevance_score": 4,
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 4,
                "composite_score": 4.2,
                "confidence_level": "high",
                "study_type": "experimental"
            },
            "judge_notes": "Test"
        }
        
        result = validate_judge_response_enhanced(response)
        assert result is None
    
    @pytest.mark.unit
    def test_score_out_of_range_strength(self):
        """Test rejection when strength_score is out of range."""
        response = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 6,  # Invalid: should be 1-5
                "rigor_score": 5,
                "relevance_score": 4,
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 4,
                "composite_score": 4.2,
                "confidence_level": "high",
                "study_type": "experimental"
            },
            "judge_notes": "Test"
        }
        
        result = validate_judge_response_enhanced(response)
        assert result is None
    
    @pytest.mark.unit
    def test_score_out_of_range_directness(self):
        """Test rejection when directness is out of range."""
        response = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 4,
                "rigor_score": 5,
                "relevance_score": 4,
                "directness": 4,  # Invalid: should be 1-3
                "is_recent": True,
                "reproducibility_score": 4,
                "composite_score": 4.2,
                "confidence_level": "high",
                "study_type": "experimental"
            },
            "judge_notes": "Test"
        }
        
        result = validate_judge_response_enhanced(response)
        assert result is None
    
    @pytest.mark.unit
    def test_invalid_study_type(self):
        """Test rejection when study_type is invalid."""
        response = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 4,
                "rigor_score": 5,
                "relevance_score": 4,
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 4,
                "composite_score": 4.2,
                "confidence_level": "high",
                "study_type": "invalid_type"
            },
            "judge_notes": "Test"
        }
        
        result = validate_judge_response_enhanced(response)
        assert result is None
    
    @pytest.mark.unit
    def test_invalid_confidence_level(self):
        """Test rejection when confidence_level is invalid."""
        response = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 4,
                "rigor_score": 5,
                "relevance_score": 4,
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 4,
                "composite_score": 4.2,
                "confidence_level": "very_high",
                "study_type": "experimental"
            },
            "judge_notes": "Test"
        }
        
        result = validate_judge_response_enhanced(response)
        assert result is None
    
    @pytest.mark.unit
    def test_is_recent_not_boolean(self):
        """Test rejection when is_recent is not boolean."""
        response = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 4,
                "rigor_score": 5,
                "relevance_score": 4,
                "directness": 3,
                "is_recent": "yes",  # Invalid: should be boolean
                "reproducibility_score": 4,
                "composite_score": 4.2,
                "confidence_level": "high",
                "study_type": "experimental"
            },
            "judge_notes": "Test"
        }
        
        result = validate_judge_response_enhanced(response)
        assert result is None
    
    @pytest.mark.unit
    def test_not_dict(self):
        """Test rejection when response is not a dict."""
        result = validate_judge_response_enhanced("not a dict")
        assert result is None
    
    @pytest.mark.unit
    def test_missing_score_field(self):
        """Test rejection when a required score field is missing."""
        response = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 4,
                # Missing rigor_score
                "relevance_score": 4,
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 4,
                "composite_score": 4.2,
                "confidence_level": "high",
                "study_type": "experimental"
            },
            "judge_notes": "Test"
        }
        
        result = validate_judge_response_enhanced(response)
        assert result is None


class TestMeetsApprovalCriteria:
    """Test suite for meets_approval_criteria function."""
    
    @pytest.mark.unit
    def test_approval_threshold_met(self):
        """Test that composite ≥3.0 AND strength ≥3 AND relevance ≥3 approves."""
        quality = {
            "strength_score": 4,
            "rigor_score": 3,
            "relevance_score": 4,
            "directness": 3,
            "is_recent": False,
            "reproducibility_score": 3,
            "composite_score": 3.5
        }
        
        assert meets_approval_criteria(quality) == True
    
    @pytest.mark.unit
    def test_approval_threshold_exactly_met(self):
        """Test boundary case where all criteria are exactly met."""
        quality = {
            "strength_score": 3,
            "rigor_score": 3,
            "relevance_score": 3,
            "directness": 2,
            "is_recent": False,
            "reproducibility_score": 3,
            "composite_score": 3.0
        }
        
        assert meets_approval_criteria(quality) == True
    
    @pytest.mark.unit
    def test_low_strength_rejects(self):
        """Test that low strength rejects even with high composite."""
        quality = {
            "strength_score": 2,  # Too low
            "rigor_score": 5,
            "relevance_score": 5,
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 5,
            "composite_score": 3.6  # Composite high but strength too low
        }
        
        assert meets_approval_criteria(quality) == False
    
    @pytest.mark.unit
    def test_low_relevance_rejects(self):
        """Test that low relevance rejects even with high composite."""
        quality = {
            "strength_score": 5,
            "rigor_score": 5,
            "relevance_score": 2,  # Too low
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 5,
            "composite_score": 3.8  # Composite high but relevance too low
        }
        
        assert meets_approval_criteria(quality) == False
    
    @pytest.mark.unit
    def test_low_composite_rejects(self):
        """Test that low composite rejects even with high strength and relevance."""
        quality = {
            "strength_score": 4,
            "rigor_score": 1,
            "relevance_score": 4,
            "directness": 1,
            "is_recent": False,
            "reproducibility_score": 1,
            "composite_score": 2.5  # Too low
        }
        
        assert meets_approval_criteria(quality) == False
    
    @pytest.mark.unit
    def test_missing_scores_default_to_reject(self):
        """Test that missing scores default to 0 and reject."""
        quality = {}
        
        assert meets_approval_criteria(quality) == False
    
    @pytest.mark.unit
    def test_boundary_composite_below_threshold(self):
        """Test boundary case just below composite threshold."""
        quality = {
            "strength_score": 3,
            "rigor_score": 3,
            "relevance_score": 3,
            "directness": 2,
            "is_recent": False,
            "reproducibility_score": 3,
            "composite_score": 2.99  # Just below threshold
        }
        
        assert meets_approval_criteria(quality) == False
    
    @pytest.mark.unit
    def test_boundary_strength_below_threshold(self):
        """Test boundary case just below strength threshold."""
        quality = {
            "strength_score": 2.99,  # Just below threshold
            "rigor_score": 4,
            "relevance_score": 4,
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 4,
            "composite_score": 3.5
        }
        
        assert meets_approval_criteria(quality) == False
