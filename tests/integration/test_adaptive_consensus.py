"""Integration tests for adaptive consensus workflow."""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis.judge import (
    process_claim_with_adaptive_consensus,
    API_CONFIG
)


@pytest.fixture
def mock_api_manager():
    """Create a mock API manager for testing."""
    mock_api = Mock()
    return mock_api


@pytest.fixture
def sample_claim():
    """Create a sample claim for testing."""
    return {
        'claim_id': 'test_integration_001',
        'extracted_claim_text': 'This is a test claim about neuromorphic computing.',
        'pillar': 'Pillar 1',
        'sub_requirement': 'SR 1.1'
    }


@pytest.fixture
def sample_sub_req_def():
    """Create a sample sub-requirement definition."""
    return "This requirement addresses neuromorphic computing principles."


class TestAdaptiveConsensusIntegration:
    """Integration tests for adaptive consensus workflow."""
    
    def test_clear_approval_skips_consensus(self, mock_api_manager, sample_claim, sample_sub_req_def):
        """Test that clear approval (score > 3.5) skips consensus."""
        # Mock a clear approval (high score)
        high_score_judgment = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 5,
                "strength_rationale": "Excellent evidence",
                "rigor_score": 5,
                "study_type": "experimental",
                "relevance_score": 5,
                "relevance_notes": "Highly relevant",
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 5,
                "composite_score": 4.8,  # Well above borderline
                "confidence_level": "high"
            },
            "judge_notes": "Approved. Excellent evidence."
        }
        
        # Mock single API call returning high score
        mock_api_manager.cached_api_call = Mock(return_value=high_score_judgment)
        
        result = process_claim_with_adaptive_consensus(
            sample_claim,
            sample_sub_req_def,
            mock_api_manager
        )
        
        # Should return result without consensus
        assert result is not None
        assert result["verdict"] == "approved"
        assert result["evidence_quality"]["composite_score"] == 4.8
        assert "consensus_metadata" not in result
        
        # Should only call API once (no consensus)
        assert mock_api_manager.cached_api_call.call_count == 1
    
    def test_clear_rejection_skips_consensus(self, mock_api_manager, sample_claim, sample_sub_req_def):
        """Test that clear rejection (score < 2.5) skips consensus."""
        # Mock a clear rejection (low score)
        low_score_judgment = {
            "verdict": "rejected",
            "evidence_quality": {
                "strength_score": 1,
                "strength_rationale": "Weak evidence",
                "rigor_score": 2,
                "study_type": "opinion",
                "relevance_score": 2,
                "relevance_notes": "Limited relevance",
                "directness": 1,
                "is_recent": False,
                "reproducibility_score": 1,
                "composite_score": 1.5,  # Well below borderline
                "confidence_level": "low"
            },
            "judge_notes": "Rejected. Weak evidence."
        }
        
        # Mock single API call returning low score
        mock_api_manager.cached_api_call = Mock(return_value=low_score_judgment)
        
        result = process_claim_with_adaptive_consensus(
            sample_claim,
            sample_sub_req_def,
            mock_api_manager
        )
        
        # Should return result without consensus
        assert result is not None
        assert result["verdict"] == "rejected"
        assert result["evidence_quality"]["composite_score"] == 1.5
        assert "consensus_metadata" not in result
        
        # Should only call API once (no consensus)
        assert mock_api_manager.cached_api_call.call_count == 1
    
    def test_borderline_triggers_consensus(self, mock_api_manager, sample_claim, sample_sub_req_def):
        """Test that borderline score (2.5-3.5) triggers consensus."""
        # Mock initial borderline judgment
        borderline_judgment = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 3,
                "strength_rationale": "Moderate evidence",
                "rigor_score": 3,
                "study_type": "experimental",
                "relevance_score": 3,
                "relevance_notes": "Relevant",
                "directness": 2,
                "is_recent": True,
                "reproducibility_score": 3,
                "composite_score": 3.0,  # Borderline
                "confidence_level": "medium"
            },
            "judge_notes": "Approved. Moderate evidence."
        }
        
        # Mock consensus judgments (3 judges)
        consensus_judgments = [
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
                    "composite_score": 2.9,
                    "confidence_level": "medium"
                },
                "judge_notes": "Approved."
            },
            {
                "verdict": "rejected",
                "evidence_quality": {
                    "strength_score": 2,
                    "strength_rationale": "Weak",
                    "rigor_score": 3,
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
        
        # Set up mock to return initial judgment, then consensus judgments
        mock_api_manager.cached_api_call = Mock(return_value=borderline_judgment)
        mock_api_manager.call_with_temperature = Mock(side_effect=consensus_judgments)
        
        result = process_claim_with_adaptive_consensus(
            sample_claim,
            sample_sub_req_def,
            mock_api_manager
        )
        
        # Should return consensus result
        assert result is not None
        assert result["verdict"] == "approved"  # Majority verdict (2 approved, 1 rejected)
        assert "consensus_metadata" in result
        assert result["consensus_metadata"]["total_judges"] == 3
        assert result["consensus_metadata"]["consensus_status"] == "strong_consensus"
        assert result["consensus_metadata"]["vote_breakdown"]["approved"] == 2
        assert result["consensus_metadata"]["vote_breakdown"]["rejected"] == 1
        
        # Should call API once for initial, then 3 times for consensus
        assert mock_api_manager.cached_api_call.call_count == 1
        assert mock_api_manager.call_with_temperature.call_count == 3
    
    def test_consensus_with_fallback_on_failure(self, mock_api_manager, sample_claim, sample_sub_req_def):
        """Test that consensus falls back to single judge if consensus fails."""
        # Mock initial borderline judgment
        borderline_judgment = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 3,
                "strength_rationale": "Moderate evidence",
                "rigor_score": 3,
                "study_type": "experimental",
                "relevance_score": 3,
                "relevance_notes": "Relevant",
                "directness": 2,
                "is_recent": True,
                "reproducibility_score": 3,
                "composite_score": 3.0,
                "confidence_level": "medium"
            },
            "judge_notes": "Approved."
        }
        
        # Mock consensus failure (only 1 judge responds, others return None)
        mock_api_manager.cached_api_call = Mock(return_value=borderline_judgment)
        mock_api_manager.call_with_temperature = Mock(return_value=None)
        
        result = process_claim_with_adaptive_consensus(
            sample_claim,
            sample_sub_req_def,
            mock_api_manager
        )
        
        # Should fall back to single judge
        assert result is not None
        assert result["verdict"] == "approved"
        assert result["evidence_quality"]["composite_score"] == 3.0
        # Should not have consensus metadata since consensus failed
        assert "consensus_metadata" not in result
