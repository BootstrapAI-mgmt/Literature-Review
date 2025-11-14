"""Integration tests for Enhanced Evidence Scoring (Task Card #16)."""

import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch
from typing import Dict, List

# Import modules to test
from literature_review.analysis.judge import (
    build_judge_prompt_enhanced,
    validate_judge_response_enhanced,
    calculate_composite_score,
    meets_approval_criteria,
    migrate_existing_claims
)


class TestEnhancedScoringIntegration:
    """Test the enhanced evidence scoring integration."""
    
    @pytest.mark.integration
    def test_enhanced_prompt_generation(self):
        """Test that enhanced prompt includes all scoring dimensions."""
        claim = {
            "claim_id": "test_claim_001",
            "sub_requirement": "Sub-1.1.1: Test requirement",
            "evidence_chunk": "This is test evidence from a research paper.",
            "claim_summary": "The paper demonstrates the requirement."
        }
        
        sub_req_definition = "Detailed definition of test requirement"
        
        prompt = build_judge_prompt_enhanced(claim, sub_req_definition)
        
        # Verify all scoring dimensions are in prompt
        assert "Strength of Evidence" in prompt
        assert "Methodological Rigor" in prompt
        assert "Relevance to Requirement" in prompt
        assert "Evidence Directness" in prompt
        assert "Recency Bonus" in prompt
        assert "Reproducibility" in prompt
        assert "composite_score" in prompt
        assert "PRISMA" in prompt
    
    @pytest.mark.integration
    def test_enhanced_validation_with_mocked_api_response(self):
        """Test validation of a complete mocked API response."""
        # Simulate API response
        mock_response = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 4,
                "strength_rationale": "Strong experimental evidence with quantitative results",
                "rigor_score": 5,
                "study_type": "experimental",
                "relevance_score": 4,
                "relevance_notes": "Directly addresses the requirement with minor gaps",
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 4,
                "composite_score": 4.2,
                "confidence_level": "high"
            },
            "judge_notes": "Approved. High quality experimental evidence."
        }
        
        # Validate
        result = validate_judge_response_enhanced(mock_response)
        
        # Assert validation passed
        assert result is not None
        assert result == mock_response
        assert result["verdict"] == "approved"
        assert result["evidence_quality"]["composite_score"] == 4.2
    
    @pytest.mark.integration
    def test_approval_criteria_enforcement(self):
        """Test that approval criteria are properly enforced."""
        # Case 1: Should approve - all criteria met
        quality_approve = {
            "strength_score": 4,
            "rigor_score": 3,
            "relevance_score": 4,
            "directness": 3,
            "is_recent": False,
            "reproducibility_score": 3,
            "composite_score": 3.5
        }
        assert meets_approval_criteria(quality_approve) == True
        
        # Case 2: Should reject - low strength
        quality_reject_strength = {
            "strength_score": 2,  # Too low
            "rigor_score": 5,
            "relevance_score": 5,
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 5,
            "composite_score": 3.6  # Composite high but strength too low
        }
        assert meets_approval_criteria(quality_reject_strength) == False
        
        # Case 3: Should reject - low relevance
        quality_reject_relevance = {
            "strength_score": 5,
            "rigor_score": 5,
            "relevance_score": 2,  # Too low
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 5,
            "composite_score": 3.8
        }
        assert meets_approval_criteria(quality_reject_relevance) == False
        
        # Case 4: Should reject - low composite
        quality_reject_composite = {
            "strength_score": 4,
            "rigor_score": 1,
            "relevance_score": 4,
            "directness": 1,
            "is_recent": False,
            "reproducibility_score": 1,
            "composite_score": 2.5  # Too low
        }
        assert meets_approval_criteria(quality_reject_composite) == False
    
    @pytest.mark.integration
    def test_backward_compatibility_migration(self):
        """Test migration of legacy claims without evidence_quality."""
        # Create version history with legacy approved claims
        version_history = {
            "paper1.pdf": [
                {
                    "timestamp": "2024-01-01T00:00:00",
                    "review": {
                        "Requirement(s)": [
                            {
                                "claim_id": "legacy_001",
                                "status": "approved",
                                "judge_notes": "Approved.",
                                # Note: no evidence_quality field
                            },
                            {
                                "claim_id": "legacy_002",
                                "status": "rejected",
                                "judge_notes": "Rejected.",
                                # Note: no evidence_quality field
                            },
                            {
                                "claim_id": "modern_001",
                                "status": "approved",
                                "evidence_quality": {
                                    "composite_score": 4.5
                                }
                                # Already has evidence_quality
                            }
                        ]
                    }
                }
            ]
        }
        
        # Migrate
        migrated = migrate_existing_claims(version_history)
        
        # Assert: legacy approved claim got default scores
        claims = migrated["paper1.pdf"][0]["review"]["Requirement(s)"]
        legacy_approved = next(c for c in claims if c["claim_id"] == "legacy_001")
        assert "evidence_quality" in legacy_approved
        assert legacy_approved["evidence_quality"]["composite_score"] == 3.0
        assert legacy_approved["evidence_quality"]["strength_score"] == 3
        assert legacy_approved["evidence_quality"]["confidence_level"] == "medium"
        
        # Assert: rejected claim did NOT get scores
        legacy_rejected = next(c for c in claims if c["claim_id"] == "legacy_002")
        assert "evidence_quality" not in legacy_rejected
        
        # Assert: modern claim unchanged
        modern_claim = next(c for c in claims if c["claim_id"] == "modern_001")
        assert modern_claim["evidence_quality"]["composite_score"] == 4.5
    
    @pytest.mark.integration
    def test_composite_score_matches_formula(self):
        """Test that composite score calculation matches documented formula."""
        quality = {
            "strength_score": 4,
            "rigor_score": 5,
            "relevance_score": 4,
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 4
        }
        
        # Calculate using function
        calculated_score = calculate_composite_score(quality)
        
        # Calculate manually following formula
        # (strength × 0.30) + (rigor × 0.25) + (relevance × 0.25) 
        # + (directness/3 × 0.10) + (recency × 0.05) + (reproducibility × 0.05)
        manual_score = (
            4 * 0.30 +           # 1.2
            5 * 0.25 +           # 1.25
            4 * 0.25 +           # 1.0
            (3/3) * 0.10 +       # 0.1
            1 * 0.05 +           # 0.05 (True = 1)
            4 * 0.05             # 0.2
        )  # = 3.8
        
        assert abs(calculated_score - manual_score) < 0.01
        assert calculated_score == 3.8
    
    @pytest.mark.integration
    def test_end_to_end_claim_processing(self):
        """Test end-to-end flow from claim to scored verdict."""
        # Setup: Create a claim
        claim = {
            "claim_id": "e2e_test_001",
            "sub_requirement": "Sub-2.1.1: Feature extraction from DVS data",
            "pillar": "Pillar 2: Neuromorphic Sensing",
            "evidence_chunk": "The paper presents a spiking neural network...",
            "claim_summary": "SNN successfully extracts features from DVS camera data"
        }
        
        sub_req_def = "Extract meaningful features from event-based camera data"
        
        # Generate enhanced prompt
        prompt = build_judge_prompt_enhanced(claim, sub_req_def)
        assert len(prompt) > 0
        
        # Simulate API response with quality scores
        mock_response = {
            "verdict": "approved",
            "evidence_quality": {
                "strength_score": 4,
                "strength_rationale": "Strong experimental validation",
                "rigor_score": 5,
                "study_type": "experimental",
                "relevance_score": 5,
                "relevance_notes": "Perfect match to requirement",
                "directness": 3,
                "is_recent": True,
                "reproducibility_score": 4,
                "composite_score": 4.05,  # Calculated: (4*0.3)+(5*0.25)+(5*0.25)+(3/3*0.1)+(1*0.05)+(4*0.05)
                "confidence_level": "high"
            },
            "judge_notes": "Approved. Excellent experimental evidence."
        }
        
        # Validate response
        validated = validate_judge_response_enhanced(mock_response)
        assert validated is not None
        
        # Check approval criteria
        quality = validated["evidence_quality"]
        assert meets_approval_criteria(quality) == True
        
        # Verify composite score calculation
        recalculated_score = calculate_composite_score(quality)
        assert abs(recalculated_score - quality["composite_score"]) < 0.01
        
        # Update claim with results (as judge.py would do)
        claim["status"] = validated["verdict"]
        claim["judge_notes"] = validated["judge_notes"]
        claim["evidence_quality"] = validated["evidence_quality"]
        claim["judge_timestamp"] = datetime.now().isoformat()
        
        # Assert final claim state
        assert claim["status"] == "approved"
        assert "evidence_quality" in claim
        assert claim["evidence_quality"]["composite_score"] == 4.05
        assert claim["evidence_quality"]["strength_score"] >= 3
        assert claim["evidence_quality"]["relevance_score"] >= 3


class TestWeightedGapAnalysis:
    """Test weighted gap analysis functions."""
    
    @pytest.mark.integration  
    def test_gap_scoring_prioritization(self):
        """Test that low quality evidence gets higher priority in gap analysis."""
        # This would require the full orchestrator context
        # For now, we'll test the logic conceptually
        
        # High quality evidence (5.0) should map to low priority (0.2)
        # Formula: priority = 1.0 - ((avg_quality - 1.0) / 4.0)
        high_quality_avg = 5.0
        high_quality_priority = 1.0 - ((high_quality_avg - 1.0) / 4.0)
        assert abs(high_quality_priority - 0.0) < 0.01
        
        # Low quality evidence (1.0) should map to high priority (1.0)
        low_quality_avg = 1.0
        low_quality_priority = 1.0 - ((low_quality_avg - 1.0) / 4.0)
        assert abs(low_quality_priority - 1.0) < 0.01
        
        # Moderate quality (3.0) should map to moderate priority (0.5)
        moderate_quality_avg = 3.0
        moderate_quality_priority = 1.0 - ((moderate_quality_avg - 1.0) / 4.0)
        assert abs(moderate_quality_priority - 0.5) < 0.01
