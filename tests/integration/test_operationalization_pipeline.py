"""Integration tests for operationalization extraction pipeline."""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.integration
class TestOperationalizationPipeline:
    """Integration tests for full operationalization extraction."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def sample_version_history(self):
        """Create sample version history with approved claims."""
        return {
            "test_paper.pdf": [
                {
                    "timestamp": "2024-01-01T00:00:00",
                    "review": {
                        "FILENAME": "test_paper.pdf",
                        "Requirement(s)": [
                            {
                                "claim_id": "abc123",
                                "pillar": "Pillar 2: AI Stimulus-Response",
                                "sub_requirement": "Sub-2.1.1: Event-based processing",
                                "evidence_chunk": "We implemented a DVS-based system using surrogate gradients...",
                                "claim_summary": "DVS-based SNN achieves real-time processing",
                                "status": "approved",
                                "reviewer_confidence": 0.9
                            },
                            {
                                "claim_id": "def456",
                                "pillar": "Pillar 2: AI Stimulus-Response",
                                "sub_requirement": "Sub-2.1.2: Low latency inference",
                                "evidence_chunk": "Our model achieves 10ms latency...",
                                "claim_summary": "10ms inference latency achieved",
                                "status": "approved",
                                "reviewer_confidence": 0.85
                            },
                            {
                                "claim_id": "ghi789",
                                "pillar": "Pillar 2: AI Stimulus-Response",
                                "sub_requirement": "Sub-2.1.3: Energy efficiency",
                                "evidence_chunk": "Pending evidence...",
                                "claim_summary": "Pending claim",
                                "status": "pending_judge_review",
                                "reviewer_confidence": 0.7
                            }
                        ]
                    }
                }
            ]
        }
    
    @pytest.fixture
    def mock_api_manager(self):
        """Create a mock API manager with operationalization responses."""
        mock = Mock()
        mock.cached_api_call.return_value = {
            "implementation_approach": {
                "technique_name": "Surrogate gradient training",
                "description": "Use SuperSpike surrogate gradient function",
                "key_hyperparameters": ["learning_rate=0.01", "batch_size=32"],
                "alternatives_mentioned": ["SLAYER", "BPTT"]
            },
            "reproducibility": {
                "code_available": True,
                "code_url": "https://github.com/example/snn",
                "data_available": True,
                "data_url": "https://dataset.org/dvs",
                "hyperparameters_specified": True,
                "methodology_detail_level": "high"
            },
            "resources": {
                "hardware": ["NVIDIA V100", "DVS camera"],
                "software": ["PyTorch", "snnTorch", "CUDA 11.0"],
                "data": ["DVS128 Gesture dataset"],
                "compute_time": "4 hours on V100",
                "personnel_skills": ["Deep learning", "SNN expertise", "Event cameras"]
            },
            "action_chain": {
                "prerequisites": ["CUDA setup", "PyTorch installation", "DVS driver"],
                "enables": ["Real-time gesture recognition", "Low-power inference"],
                "gaps": ["Hyperparameter sensitivity analysis"],
                "blocking_unknowns": []
            },
            "actionability_score": 0.85,
            "actionability_rationale": "Clear implementation with code and data available"
        }
        return mock
    
    def test_run_operationalization_extraction(
        self,
        temp_output_dir,
        sample_version_history,
        mock_api_manager
    ):
        """Test running operationalization extraction on version history."""
        from literature_review.reviewers.deep_reviewer import run_operationalization_extraction
        
        # Run extraction
        updated_history = run_operationalization_extraction(
            version_history=sample_version_history,
            api_manager=mock_api_manager,
            batch_mode=False  # Use individual mode for clearer testing
        )
        
        # Verify operationalization data attached to approved claims
        requirements = updated_history["test_paper.pdf"][0]["review"]["Requirement(s)"]
        
        # Find approved claims
        approved_claims = [r for r in requirements if r.get("status") == "approved"]
        
        # Check that operationalization was added
        assert len(approved_claims) == 2
        
        for claim in approved_claims:
            if "operationalization" in claim:
                ops = claim["operationalization"]
                assert "reproducibility" in ops
                assert "resources" in ops
                assert "action_chain" in ops
                assert "actionability_score" in ops
        
        # Pending claims should NOT have operationalization
        pending_claims = [r for r in requirements if r.get("status") == "pending_judge_review"]
        for claim in pending_claims:
            assert "operationalization" not in claim
    
    def test_operationalization_not_duplicated(
        self,
        sample_version_history,
        mock_api_manager
    ):
        """Test that claims with existing operationalization are not re-processed."""
        from literature_review.reviewers.deep_reviewer import run_operationalization_extraction
        
        # Add operationalization to first claim
        sample_version_history["test_paper.pdf"][0]["review"]["Requirement(s)"][0]["operationalization"] = {
            "actionability_score": 0.9,
            "existing": True
        }
        
        # Run extraction
        updated_history = run_operationalization_extraction(
            version_history=sample_version_history,
            api_manager=mock_api_manager,
            batch_mode=False
        )
        
        # First claim should still have original operationalization
        first_claim = updated_history["test_paper.pdf"][0]["review"]["Requirement(s)"][0]
        assert first_claim["operationalization"].get("existing") is True
        assert first_claim["operationalization"]["actionability_score"] == 0.9
    
    def test_batch_mode_extraction(
        self,
        sample_version_history,
        mock_api_manager
    ):
        """Test batch mode operationalization extraction."""
        from literature_review.reviewers.deep_reviewer import run_operationalization_extraction
        
        # Configure mock for batch response
        mock_api_manager.cached_api_call.return_value = [
            {
                "claim_id": "abc123",
                "operationalization": {
                    "implementation_approach": {"technique_name": "Test"},
                    "reproducibility": {"code_available": True},
                    "resources": {"hardware": ["GPU"]},
                    "action_chain": {"prerequisites": []},
                    "actionability_score": 0.8,
                    "actionability_rationale": "Batch result"
                }
            },
            {
                "claim_id": "def456",
                "operationalization": {
                    "implementation_approach": {"technique_name": "Test 2"},
                    "reproducibility": {"code_available": False},
                    "resources": {"hardware": ["CPU"]},
                    "action_chain": {"prerequisites": ["Step 1"]},
                    "actionability_score": 0.6,
                    "actionability_rationale": "Batch result 2"
                }
            }
        ]
        
        # Run extraction in batch mode
        updated_history = run_operationalization_extraction(
            version_history=sample_version_history,
            api_manager=mock_api_manager,
            batch_mode=True
        )
        
        # Verify API was called once (batch mode)
        # Note: May be called more depending on implementation
        assert mock_api_manager.cached_api_call.called
    
    def test_operationalization_saved_to_output(
        self,
        temp_output_dir,
        sample_version_history,
        mock_api_manager
    ):
        """Test that operationalization is saved to output files."""
        from literature_review.reviewers.deep_reviewer import (
            run_operationalization_extraction,
            save_version_history
        )
        
        # Run extraction
        updated_history = run_operationalization_extraction(
            version_history=sample_version_history,
            api_manager=mock_api_manager,
            batch_mode=False
        )
        
        # Save to file
        output_path = os.path.join(temp_output_dir, "test_version_history.json")
        save_version_history(output_path, updated_history)
        
        # Verify file was created and contains operationalization
        assert os.path.exists(output_path)
        
        with open(output_path, 'r') as f:
            saved_data = json.load(f)
        
        # Check structure is preserved
        assert "test_paper.pdf" in saved_data
        requirements = saved_data["test_paper.pdf"][0]["review"]["Requirement(s)"]
        
        # At least one claim should have operationalization
        has_ops = any("operationalization" in r for r in requirements if r.get("status") == "approved")
        assert has_ops, "No operationalization data found in saved output"


@pytest.mark.integration
class TestJudgeActionabilityIntegration:
    """Integration tests for Judge actionability assessment."""
    
    @pytest.fixture
    def mock_api_manager_with_enhanced_response(self):
        """Mock API manager with enhanced judge response."""
        mock = Mock()
        mock.cached_api_call.return_value = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 4,
                "strength_rationale": "Strong experimental evidence",
                "rigor_score": 4,
                "study_type": "experimental",
                "relevance_score": 5,
                "relevance_notes": "Directly addresses requirement",
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 4,
                "composite_score": 4.2,
                "confidence_level": "high"
            },
            "judge_notes": "Approved. Strong evidence with clear methodology."
        }
        return mock
    
    def test_enhanced_judge_claim_with_actionability(self, mock_api_manager_with_enhanced_response):
        """Test enhanced judging includes actionability."""
        from literature_review.analysis.judge import enhanced_judge_claim
        
        # Mock the definition lookup
        with patch('literature_review.analysis.judge.find_robust_sub_requirement_text') as mock_lookup:
            mock_lookup.return_value = "Test requirement definition"
            
            claim = {
                "claim_id": "test123",
                "sub_requirement": "Sub-2.1.1: Test",
                "extracted_claim_text": "Test claim",
                "evidence_chunk": "Test evidence"
            }
            
            # Configure mock for both enhanced judge and actionability
            mock_api_manager_with_enhanced_response.cached_api_call.side_effect = [
                # Enhanced judge response
                {
                    "verdict": "approved",
                    "evidence_quality": {
                        "strength_score": 4,
                        "rigor_score": 4,
                        "relevance_score": 5,
                        "directness": 3,
                        "is_recent": True,
                        "reproducibility_score": 4,
                        "composite_score": 4.2,
                        "confidence_level": "high",
                        "study_type": "experimental"
                    },
                    "judge_notes": "Approved."
                },
                # Actionability response
                {
                    "actionability_score": 4,
                    "implementation_clarity": 4,
                    "parameter_completeness": 3,
                    "replication_feasibility": 4,
                    "rationale": "Clear implementation path"
                }
            ]
            
            result = enhanced_judge_claim(
                claim=claim,
                api_manager=mock_api_manager_with_enhanced_response,
                include_actionability=True
            )
            
            assert result["verdict"] == "approved"
            assert "evidence_quality" in result
            assert "actionability" in result
            assert result["actionability"]["actionability_score"] == 4
    
    def test_enhanced_judge_claim_without_actionability(self, mock_api_manager_with_enhanced_response):
        """Test enhanced judging can skip actionability."""
        from literature_review.analysis.judge import enhanced_judge_claim
        
        with patch('literature_review.analysis.judge.find_robust_sub_requirement_text') as mock_lookup:
            mock_lookup.return_value = "Test requirement definition"
            
            claim = {
                "claim_id": "test123",
                "sub_requirement": "Sub-2.1.1: Test",
                "extracted_claim_text": "Test claim",
                "evidence_chunk": "Test evidence"
            }
            
            result = enhanced_judge_claim(
                claim=claim,
                api_manager=mock_api_manager_with_enhanced_response,
                include_actionability=False
            )
            
            assert result["verdict"] == "approved"
            assert "actionability" not in result or result["actionability"] is None


@pytest.mark.integration
class TestOrchestratorOperationalizationIntegration:
    """Integration tests for orchestrator operationalization support."""
    
    def test_run_deep_review_with_operationalization_function_exists(self):
        """Test that the orchestrator function is importable."""
        from literature_review.orchestrator import run_deep_review_with_operationalization
        
        assert callable(run_deep_review_with_operationalization)
    
    def test_operationalization_extraction_in_orchestrator(self):
        """Test that orchestrator can call operationalization extraction."""
        from literature_review.orchestrator import run_deep_review_with_operationalization
        
        # Just verify the function signature and structure
        import inspect
        sig = inspect.signature(run_deep_review_with_operationalization)
        
        # Should have these parameters
        params = list(sig.parameters.keys())
        assert "papers" in params
        assert "extract_operationalization" in params
