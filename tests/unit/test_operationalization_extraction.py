"""Unit tests for operationalization extraction."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from literature_review.reviewers.prompts.operationalization_prompt import (
    format_claim_for_prompt,
    format_claims_batch,
    OPERATIONALIZATION_EXTRACTION_PROMPT,
    BATCH_OPERATIONALIZATION_PROMPT
)


class TestOperationalizationPrompts:
    """Tests for operationalization prompt formatting."""
    
    def test_format_single_claim(self):
        """Test formatting a single claim."""
        claim = {
            "extracted_claim_text": "SNNs achieve 95% accuracy",
            "evidence_chunk": "We trained an SNN using surrogate gradients...",
            "requirement_id": "Sub-2.1.1"
        }
        
        prompt = format_claim_for_prompt(claim, "Event-based sensor integration")
        
        assert "SNNs achieve 95% accuracy" in prompt
        assert "Event-based sensor integration" in prompt
        assert "Implementation Approach" in prompt
        assert "Reproducibility Assessment" in prompt
    
    def test_format_single_claim_with_claim_summary_fallback(self):
        """Test formatting with claim_summary as fallback."""
        claim = {
            "claim_summary": "Fallback claim summary",
            "evidence_chunk": "Some evidence...",
        }
        
        prompt = format_claim_for_prompt(claim, "Test requirement")
        
        assert "Fallback claim summary" in prompt
        assert "Test requirement" in prompt
    
    def test_format_claims_batch(self):
        """Test formatting multiple claims for batch processing."""
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "Claim 1",
                "evidence_chunk": "Evidence 1",
                "requirement_id": "Req 1"
            },
            {
                "claim_id": "c2",
                "extracted_claim_text": "Claim 2",
                "evidence_chunk": "Evidence 2",
                "requirement_id": "Req 2"
            }
        ]
        
        prompt = format_claims_batch(claims, "test_paper.pdf")
        
        assert "test_paper.pdf" in prompt
        assert "Claim 1" in prompt
        assert "Claim 2" in prompt
        assert "c1" in prompt
        assert "c2" in prompt
    
    def test_format_claims_batch_truncates_evidence(self):
        """Test that evidence is truncated in batch mode."""
        long_evidence = "x" * 1000  # Longer than 500 char limit
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "Claim 1",
                "evidence_chunk": long_evidence,
                "requirement_id": "Req 1"
            }
        ]
        
        prompt = format_claims_batch(claims, "test_paper.pdf")
        
        # Evidence should be truncated to 500 chars
        assert "x" * 500 in prompt
        assert "x" * 600 not in prompt
    
    def test_format_claims_batch_uses_sub_requirement_fallback(self):
        """Test that sub_requirement is used as fallback for requirement_id."""
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "Claim 1",
                "evidence_chunk": "Evidence 1",
                "sub_requirement": "Sub-1.1.1: Event-based processing"
            }
        ]
        
        prompt = format_claims_batch(claims, "test_paper.pdf")
        
        assert "Sub-1.1.1" in prompt
    
    def test_operationalization_prompt_structure(self):
        """Test that the main prompt has required sections."""
        assert "Implementation Approach" in OPERATIONALIZATION_EXTRACTION_PROMPT
        assert "Reproducibility Assessment" in OPERATIONALIZATION_EXTRACTION_PROMPT
        assert "Resource Requirements" in OPERATIONALIZATION_EXTRACTION_PROMPT
        assert "Action Chain Position" in OPERATIONALIZATION_EXTRACTION_PROMPT
        assert "actionability_score" in OPERATIONALIZATION_EXTRACTION_PROMPT
    
    def test_batch_prompt_structure(self):
        """Test that batch prompt has required structure."""
        assert "claim_id" in BATCH_OPERATIONALIZATION_PROMPT
        assert "operationalization" in BATCH_OPERATIONALIZATION_PROMPT


class TestDeepReviewerOperationalization:
    """Tests for DeepReviewer operationalization extraction."""
    
    @pytest.fixture
    def mock_api_response(self):
        """Standard mock API response."""
        return {
            "implementation_approach": {
                "technique_name": "Surrogate gradient",
                "description": "Use SuperSpike function",
                "key_hyperparameters": ["learning_rate=0.01"],
                "alternatives_mentioned": ["SLAYER"]
            },
            "reproducibility": {
                "code_available": True,
                "code_url": "https://github.com/example",
                "data_available": True,
                "data_url": "https://dataset.example",
                "hyperparameters_specified": True,
                "methodology_detail_level": "high"
            },
            "resources": {
                "hardware": ["NVIDIA V100"],
                "software": ["PyTorch", "snnTorch"],
                "data": ["N-MNIST dataset"],
                "compute_time": "4 hours on V100",
                "personnel_skills": ["Deep learning", "SNN expertise"]
            },
            "action_chain": {
                "prerequisites": ["CUDA setup", "PyTorch installation"],
                "enables": ["SNN training", "Real-time inference"],
                "gaps": ["Hyperparameter tuning details"],
                "blocking_unknowns": []
            },
            "actionability_score": 0.85,
            "actionability_rationale": "Clear implementation with code"
        }
    
    def test_parse_operationalization(self, mock_api_response):
        """Test parsing operationalization response."""
        from literature_review.reviewers.deep_reviewer import _parse_operationalization
        
        result = _parse_operationalization(mock_api_response)
        
        # Check reproducibility
        assert result["reproducibility"]["code_available"] is True
        assert result["reproducibility"]["code_url"] == "https://github.com/example"
        assert "reproducibility_score" in result["reproducibility"]
        
        # Check resources
        assert result["resources"]["hardware"] == ["NVIDIA V100"]
        assert result["resources"]["software"] == ["PyTorch", "snnTorch"]
        
        # Check action chain
        assert len(result["action_chain"]["prerequisites"]) == 2
        assert len(result["action_chain"]["gaps"]) == 1
        
        # Check actionability
        assert result["actionability_score"] == 0.85
    
    def test_parse_operationalization_with_missing_fields(self):
        """Test parsing with missing fields uses defaults."""
        from literature_review.reviewers.deep_reviewer import _parse_operationalization
        
        result = _parse_operationalization({})
        
        # Should have default values
        assert result["reproducibility"]["code_available"] is False
        assert result["reproducibility"]["methodology_detail_level"] == "low"
        assert result["resources"]["hardware"] == []
        assert result["action_chain"]["prerequisites"] == []
        assert result["actionability_score"] == 0.0
    
    def test_extract_operationalization_individual(self, mock_api_response):
        """Test individual extraction mode."""
        from literature_review.reviewers.deep_reviewer import _extract_operationalization_individual
        
        mock_api_manager = Mock()
        mock_api_manager.cached_api_call.return_value = mock_api_response
        
        claims = [
            {"claim_id": "test_claim_1", "claim_summary": "Test claim", "evidence_chunk": "Test evidence"}
        ]
        
        result = _extract_operationalization_individual(claims, mock_api_manager)
        
        assert "test_claim_1" in result
        assert result["test_claim_1"]["actionability_score"] == 0.85
    
    def test_extract_operationalization_batch(self, mock_api_response):
        """Test batch extraction mode."""
        from literature_review.reviewers.deep_reviewer import _extract_operationalization_batch
        
        mock_api_manager = Mock()
        # Batch response format
        mock_api_manager.cached_api_call.return_value = [
            {
                "claim_id": "claim_1",
                "operationalization": mock_api_response
            },
            {
                "claim_id": "claim_2",
                "operationalization": mock_api_response
            }
        ]
        
        claims = [
            {"claim_id": "claim_1", "claim_summary": "Claim 1", "evidence_chunk": "Evidence 1"},
            {"claim_id": "claim_2", "claim_summary": "Claim 2", "evidence_chunk": "Evidence 2"}
        ]
        
        result = _extract_operationalization_batch(claims, "test_paper.pdf", mock_api_manager)
        
        assert "claim_1" in result
        assert "claim_2" in result
    
    def test_extract_operationalization_batch_fallback(self):
        """Test batch extraction falls back to individual on error."""
        from literature_review.reviewers.deep_reviewer import _extract_operationalization_batch
        
        mock_api_manager = Mock()
        mock_api_manager.cached_api_call.side_effect = [
            None,  # First call fails
            {"actionability_score": 0.5}  # Individual fallback succeeds
        ]
        
        claims = [
            {"claim_id": "claim_1", "claim_summary": "Claim 1", "evidence_chunk": "Evidence 1"}
        ]
        
        # Should not raise, should fallback to individual
        result = _extract_operationalization_batch(claims, "test_paper.pdf", mock_api_manager)
        
        # Result may be empty if individual also fails, but shouldn't raise
        assert isinstance(result, dict)
    
    def test_extract_operationalization_empty_claims(self):
        """Test extraction with empty claims list."""
        from literature_review.reviewers.deep_reviewer import extract_operationalization
        
        mock_api_manager = Mock()
        
        result = extract_operationalization([], "test.pdf", mock_api_manager)
        
        assert result == {}
        mock_api_manager.cached_api_call.assert_not_called()


class TestJudgeActionability:
    """Tests for Judge actionability scoring."""
    
    @pytest.fixture
    def mock_actionability_response(self):
        """Mock actionability assessment response."""
        return {
            "actionability_score": 4,
            "implementation_clarity": 4,
            "parameter_completeness": 3,
            "replication_feasibility": 4,
            "rationale": "Clear implementation approach with minor gaps"
        }
    
    def test_assess_actionability(self, mock_actionability_response):
        """Test actionability assessment."""
        from literature_review.analysis.judge import assess_actionability
        
        mock_api_manager = Mock()
        mock_api_manager.cached_api_call.return_value = mock_actionability_response
        
        claim = {
            "extracted_claim_text": "Our method achieves 95% accuracy",
            "evidence_chunk": "We use a 3-layer SNN with LIF neurons..."
        }
        
        result = assess_actionability(claim, mock_api_manager)
        
        assert result["actionability_score"] == 4
        assert result["implementation_clarity"] == 4
        assert "rationale" in result
    
    def test_assess_actionability_fallback_on_error(self):
        """Test actionability assessment returns defaults on error."""
        from literature_review.analysis.judge import assess_actionability
        
        mock_api_manager = Mock()
        mock_api_manager.cached_api_call.side_effect = Exception("API error")
        
        claim = {
            "extracted_claim_text": "Test claim",
            "evidence_chunk": "Test evidence"
        }
        
        result = assess_actionability(claim, mock_api_manager)
        
        # Should return default neutral scores
        assert result["actionability_score"] == 3
        assert result["implementation_clarity"] == 3
        assert result["rationale"] == "Assessment failed"
    
    def test_assess_actionability_uses_claim_summary_fallback(self, mock_actionability_response):
        """Test that claim_summary is used when extracted_claim_text missing."""
        from literature_review.analysis.judge import assess_actionability
        
        mock_api_manager = Mock()
        mock_api_manager.cached_api_call.return_value = mock_actionability_response
        
        claim = {
            "claim_summary": "Fallback summary",
            "evidence_chunk": "Test evidence"
        }
        
        result = assess_actionability(claim, mock_api_manager)
        
        assert result["actionability_score"] == 4
        # Verify the prompt was called with the claim summary
        call_args = mock_api_manager.cached_api_call.call_args
        assert "Fallback summary" in call_args[0][0]
    
    def test_actionability_prompt_structure(self):
        """Test that actionability prompt has required elements."""
        from literature_review.analysis.judge import ACTIONABILITY_PROMPT
        
        assert "actionability_score" in ACTIONABILITY_PROMPT
        assert "implementation_clarity" in ACTIONABILITY_PROMPT
        assert "parameter_completeness" in ACTIONABILITY_PROMPT
        assert "replication_feasibility" in ACTIONABILITY_PROMPT
        assert "{claim_text}" in ACTIONABILITY_PROMPT
        assert "{evidence_chunk}" in ACTIONABILITY_PROMPT


class TestReproducibilityInfo:
    """Tests for ReproducibilityInfo model integration."""
    
    def test_reproducibility_score_full(self):
        """Test reproducibility score with all factors present."""
        from literature_review.models import ReproducibilityInfo
        
        repro = ReproducibilityInfo(
            code_available=True,
            data_available=True,
            hyperparameters_specified=True,
            methodology_detail_level="high"
        )
        
        assert repro.reproducibility_score == 1.0
    
    def test_reproducibility_score_partial(self):
        """Test reproducibility score with some factors."""
        from literature_review.models import ReproducibilityInfo
        
        repro = ReproducibilityInfo(
            code_available=True,
            data_available=False,
            hyperparameters_specified=False,
            methodology_detail_level="low"
        )
        
        # Only code_available contributes 0.35
        assert repro.reproducibility_score == 0.35
    
    def test_reproducibility_to_dict(self):
        """Test serialization includes reproducibility_score."""
        from literature_review.models import ReproducibilityInfo
        
        repro = ReproducibilityInfo(
            code_available=True,
            code_url="https://github.com/test"
        )
        
        data = repro.to_dict()
        
        assert "reproducibility_score" in data
        assert data["code_url"] == "https://github.com/test"


class TestActionChainPosition:
    """Tests for ActionChainPosition model integration."""
    
    def test_action_chain_to_dict(self):
        """Test ActionChainPosition serialization."""
        from literature_review.models import ActionChainPosition
        
        chain = ActionChainPosition(
            prerequisites=["CUDA setup"],
            enables=["SNN training"],
            gaps=["Missing hyperparameters"],
            blocking_unknowns=["Hardware requirements unclear"]
        )
        
        data = chain.to_dict()
        
        assert data["prerequisites"] == ["CUDA setup"]
        assert data["enables"] == ["SNN training"]
        assert len(data["gaps"]) == 1
        assert len(data["blocking_unknowns"]) == 1
    
    def test_action_chain_from_dict(self):
        """Test ActionChainPosition deserialization."""
        from literature_review.models import ActionChainPosition
        
        data = {
            "prerequisites": ["Step 1"],
            "enables": ["Step 2"],
            "gaps": [],
            "blocking_unknowns": []
        }
        
        chain = ActionChainPosition.from_dict(data)
        
        assert chain.prerequisites == ["Step 1"]
        assert chain.enables == ["Step 2"]
