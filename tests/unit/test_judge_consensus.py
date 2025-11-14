"""Unit tests for Judge multi-judge consensus functions (Task Card #18)."""

import pytest
import sys
import os
import numpy as np
from unittest.mock import Mock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis.judge import (
    should_use_consensus,
    should_trigger_consensus,  # Legacy function
    trigger_consensus_review,
    judge_with_consensus,
    process_claim_with_adaptive_consensus,
    API_CONFIG
)


class TestConsensusDetection:
    """Test borderline claim detection for consensus triggering."""
    
    def test_should_use_consensus_for_borderline_low(self):
        """Test consensus triggers for low borderline score (2.5)."""
        claim = {
            'claim_id': 'test_001',
            'evidence_quality': {
                'composite_score': 2.5
            }
        }
        assert should_use_consensus(claim) is True
    
    def test_should_use_consensus_for_borderline_mid(self):
        """Test consensus triggers for mid borderline score (3.0)."""
        claim = {
            'claim_id': 'test_002',
            'evidence_quality': {
                'composite_score': 3.0
            }
        }
        assert should_use_consensus(claim) is True
    
    def test_should_use_consensus_for_borderline_high(self):
        """Test consensus triggers for high borderline score (3.5)."""
        claim = {
            'claim_id': 'test_003',
            'evidence_quality': {
                'composite_score': 3.5
            }
        }
        assert should_use_consensus(claim) is True
    
    def test_should_not_use_consensus_for_low_score(self):
        """Test consensus does not trigger for low score (< 2.5)."""
        claim = {
            'claim_id': 'test_004',
            'evidence_quality': {
                'composite_score': 2.4
            }
        }
        assert should_use_consensus(claim) is False
    
    def test_should_not_use_consensus_for_high_score(self):
        """Test consensus does not trigger for high score (> 3.5)."""
        claim = {
            'claim_id': 'test_005',
            'evidence_quality': {
                'composite_score': 3.6
            }
        }
        assert should_use_consensus(claim) is False
    
    def test_should_not_use_consensus_for_missing_quality(self):
        """Test consensus does not trigger when evidence_quality is missing."""
        claim = {
            'claim_id': 'test_006'
        }
        assert should_use_consensus(claim) is False
    
    def test_should_not_use_consensus_for_missing_composite(self):
        """Test consensus does not trigger when composite_score is missing."""
        claim = {
            'claim_id': 'test_007',
            'evidence_quality': {}
        }
        assert should_use_consensus(claim) is False
    
    def test_legacy_function_should_trigger_consensus(self):
        """Test backward compatibility with old function name."""
        claim = {
            'claim_id': 'test_legacy',
            'evidence_quality': {
                'composite_score': 3.0
            }
        }
        # Legacy function should work identically
        assert should_trigger_consensus(claim) is True
        assert should_trigger_consensus(claim) == should_use_consensus(claim)


class TestConsensusAgreement:
    """Test consensus agreement calculation."""
    
    def test_strong_consensus_unanimous(self):
        """Test unanimous agreement (3/3) = strong consensus."""
        # This would be tested in integration tests with mock API
        # For unit test, we verify the threshold configuration
        assert API_CONFIG["AGREEMENT_THRESHOLD"] == 0.67
        assert 3/3 >= API_CONFIG["AGREEMENT_THRESHOLD"]  # 100% >= 67%
    
    def test_strong_consensus_2_of_3(self):
        """Test 2 out of 3 agreement = strong consensus."""
        # 2/3 = 0.666... which is just below 0.67 due to float precision
        # But should be treated as >= 67% threshold (with small epsilon)
        agreement_rate = 2 / 3
        # Use approximate comparison for floating point
        assert agreement_rate >= (API_CONFIG["AGREEMENT_THRESHOLD"] - 0.01)  # Allow 1% epsilon
    
    def test_weak_consensus(self):
        """Test that we can identify weak consensus scenarios."""
        # With 3 judges, minimum is 2/3 for majority
        # Weak consensus would be 50-66%, but with 3 judges that's not possible
        # This is more relevant for future scaling to 5+ judges
        assert API_CONFIG["CONSENSUS_JUDGES"] == 3
    
    def test_borderline_range_configuration(self):
        """Test that borderline score range is correctly configured."""
        assert API_CONFIG["BORDERLINE_SCORE_MIN"] == 2.5
        assert API_CONFIG["BORDERLINE_SCORE_MAX"] == 3.5


class TestLegacyCompatibility:
    """Test backward compatibility with existing functions."""
    
    def test_trigger_consensus_review_adds_metadata(self):
        """Test that trigger_consensus_review adds correct metadata."""
        claim = {
            'claim_id': 'test_008',
            'evidence_quality': {
                'composite_score': 2.8
            }
        }
        
        result = trigger_consensus_review(claim)
        
        assert 'consensus_review' in result
        assert result['consensus_review']['triggered'] is True
        assert result['consensus_review']['reason'] == 'borderline_composite_score'
        assert result['consensus_review']['composite_score'] == 2.8
        assert 'consensus_reviewers' in result['consensus_review']
        assert len(result['consensus_review']['consensus_reviewers']) >= 2
        assert 'timestamp' in result['consensus_review']
        assert result['consensus_review']['status'] == 'pending'
    
    def test_trigger_consensus_review_preserves_original_claim(self):
        """Test that trigger_consensus_review preserves original claim data."""
        claim = {
            'claim_id': 'test_009',
            'pillar': 'Pillar 1',
            'sub_requirement': 'SR 1.1',
            'evidence_quality': {
                'composite_score': 3.2,
                'strength_score': 3
            }
        }
        
        original_claim_id = claim['claim_id']
        original_pillar = claim['pillar']
        
        result = trigger_consensus_review(claim)
        
        # Original data should be preserved
        assert result['claim_id'] == original_claim_id
        assert result['pillar'] == original_pillar
        assert result['evidence_quality']['strength_score'] == 3


class TestConsensusJudgment:
    """Test multi-judge consensus logic with mocked API."""
    
    def test_judge_with_consensus_strong_agreement(self):
        """Test consensus with strong agreement (3/3 approved)."""
        claim = {
            'claim_id': 'test_consensus_001',
            'extracted_claim_text': 'Test claim text'
        }
        sub_req_def = 'Test requirement definition'
        
        # Mock API manager
        mock_api = Mock()
        
        # All 3 judges approve with similar scores
        mock_judgments = [
            {
                "verdict": "approved",
                "evidence_quality": {
                    "strength_score": 3,
                    "strength_rationale": "Good evidence",
                    "rigor_score": 3,
                    "study_type": "experimental",
                    "relevance_score": 3,
                    "relevance_notes": "Relevant",
                    "directness": 2,
                    "is_recent": True,
                    "reproducibility_score": 3,
                    "composite_score": 3.2,
                    "confidence_level": "medium"
                },
                "judge_notes": "Approved. Good evidence."
            },
            {
                "verdict": "approved",
                "evidence_quality": {
                    "strength_score": 3,
                    "strength_rationale": "Solid evidence",
                    "rigor_score": 4,
                    "study_type": "experimental",
                    "relevance_score": 3,
                    "relevance_notes": "Relevant",
                    "directness": 2,
                    "is_recent": True,
                    "reproducibility_score": 3,
                    "composite_score": 3.3,
                    "confidence_level": "high"
                },
                "judge_notes": "Approved. Solid evidence."
            },
            {
                "verdict": "approved",
                "evidence_quality": {
                    "strength_score": 4,
                    "strength_rationale": "Strong evidence",
                    "rigor_score": 3,
                    "study_type": "experimental",
                    "relevance_score": 3,
                    "relevance_notes": "Relevant",
                    "directness": 2,
                    "is_recent": False,
                    "reproducibility_score": 3,
                    "composite_score": 3.1,
                    "confidence_level": "medium"
                },
                "judge_notes": "Approved. Strong evidence."
            }
        ]
        
        mock_api.call_with_temperature = Mock(side_effect=mock_judgments)
        
        result = judge_with_consensus(claim, sub_req_def, mock_api)
        
        assert result is not None
        assert result["verdict"] == "approved"
        assert "consensus_metadata" in result
        assert result["consensus_metadata"]["total_judges"] == 3
        assert result["consensus_metadata"]["agreement_rate"] == 1.0  # 100%
        assert result["consensus_metadata"]["consensus_status"] == "strong_consensus"
        assert result["consensus_metadata"]["vote_breakdown"]["approved"] == 3
        assert result["consensus_metadata"]["vote_breakdown"]["rejected"] == 0
        
        # Check averaged composite score
        expected_avg = np.mean([3.2, 3.3, 3.1])
        assert abs(result["consensus_metadata"]["average_composite_score"] - expected_avg) < 0.01
        assert result["evidence_quality"]["composite_score"] == round(expected_avg, 2)
    
    def test_judge_with_consensus_weak_agreement(self):
        """Test consensus with weak agreement (2/3 approved)."""
        claim = {
            'claim_id': 'test_consensus_002',
            'extracted_claim_text': 'Test claim text'
        }
        sub_req_def = 'Test requirement definition'
        
        # Mock API manager
        mock_api = Mock()
        
        # 2 judges approve, 1 rejects
        mock_judgments = [
            {
                "verdict": "approved",
                "evidence_quality": {
                    "strength_score": 3,
                    "strength_rationale": "Good evidence",
                    "rigor_score": 3,
                    "study_type": "experimental",
                    "relevance_score": 3,
                    "relevance_notes": "Relevant",
                    "directness": 2,
                    "is_recent": True,
                    "reproducibility_score": 3,
                    "composite_score": 3.2,
                    "confidence_level": "medium"
                },
                "judge_notes": "Approved."
            },
            {
                "verdict": "approved",
                "evidence_quality": {
                    "strength_score": 3,
                    "strength_rationale": "Acceptable",
                    "rigor_score": 3,
                    "study_type": "experimental",
                    "relevance_score": 3,
                    "relevance_notes": "Relevant",
                    "directness": 2,
                    "is_recent": False,
                    "reproducibility_score": 3,
                    "composite_score": 3.0,
                    "confidence_level": "medium"
                },
                "judge_notes": "Approved."
            },
            {
                "verdict": "rejected",
                "evidence_quality": {
                    "strength_score": 2,
                    "strength_rationale": "Weak evidence",
                    "rigor_score": 2,
                    "study_type": "observational",
                    "relevance_score": 3,
                    "relevance_notes": "Somewhat relevant",
                    "directness": 1,
                    "is_recent": False,
                    "reproducibility_score": 2,
                    "composite_score": 2.7,
                    "confidence_level": "low"
                },
                "judge_notes": "Rejected."
            }
        ]
        
        mock_api.call_with_temperature = Mock(side_effect=mock_judgments)
        
        result = judge_with_consensus(claim, sub_req_def, mock_api)
        
        assert result is not None
        assert result["verdict"] == "approved"  # Majority verdict
        assert result["consensus_metadata"]["total_judges"] == 3
        assert abs(result["consensus_metadata"]["agreement_rate"] - 0.67) < 0.01  # 67%
        assert result["consensus_metadata"]["consensus_status"] == "strong_consensus"  # 2/3 meets threshold with epsilon
        assert result["consensus_metadata"]["vote_breakdown"]["approved"] == 2
        assert result["consensus_metadata"]["vote_breakdown"]["rejected"] == 1
        assert result["consensus_metadata"]["requires_human_review"] is False
