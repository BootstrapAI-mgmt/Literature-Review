"""
Unit Tests for GRADE Assessment (Task Card #21)
Tests GRADE framework implementation for methodological quality assessment.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis.grade_assessment import (
    assess_methodological_quality,
    _get_baseline_quality,
    _assess_bias_risk,
    _assess_indirectness,
    _get_downgrade_reasons,
    _get_grade_interpretation,
    generate_grade_summary_table
)


class TestBaselineQuality:
    """Test suite for _get_baseline_quality function."""
    
    @pytest.mark.unit
    def test_experimental_baseline(self):
        """Test baseline quality for experimental studies (RCT)."""
        assert _get_baseline_quality("experimental") == 4  # High
    
    @pytest.mark.unit
    def test_review_baseline(self):
        """Test baseline quality for review studies."""
        assert _get_baseline_quality("review") == 3  # Moderate
    
    @pytest.mark.unit
    def test_observational_baseline(self):
        """Test baseline quality for observational studies."""
        assert _get_baseline_quality("observational") == 2  # Low
    
    @pytest.mark.unit
    def test_theoretical_baseline(self):
        """Test baseline quality for theoretical studies."""
        assert _get_baseline_quality("theoretical") == 1  # Very Low
    
    @pytest.mark.unit
    def test_opinion_baseline(self):
        """Test baseline quality for opinion pieces."""
        assert _get_baseline_quality("opinion") == 1  # Very Low
    
    @pytest.mark.unit
    def test_unknown_baseline(self):
        """Test baseline quality for unknown study type defaults to Low."""
        assert _get_baseline_quality("unknown") == 2  # Low (default)
        assert _get_baseline_quality("random_type") == 2  # Low (default)


class TestBiasRiskAssessment:
    """Test suite for _assess_bias_risk function."""
    
    @pytest.mark.unit
    def test_high_reproducibility_no_downgrade(self):
        """Test no downgrade with high reproducibility (code + data available)."""
        assert _assess_bias_risk(5) == 0  # Code + data available
        assert _assess_bias_risk(4) == 0  # Detailed methods
    
    @pytest.mark.unit
    def test_moderate_reproducibility_serious_risk(self):
        """Test serious risk downgrade with moderate reproducibility."""
        assert _assess_bias_risk(3) == -1  # Basic methods
    
    @pytest.mark.unit
    def test_low_reproducibility_very_serious_risk(self):
        """Test very serious risk downgrade with low reproducibility."""
        assert _assess_bias_risk(2) == -2  # Vague methods
        assert _assess_bias_risk(1) == -2  # No methodological detail


class TestIndirectnessAssessment:
    """Test suite for _assess_indirectness function."""
    
    @pytest.mark.unit
    def test_high_relevance_no_downgrade(self):
        """Test no downgrade with high relevance (direct evidence)."""
        assert _assess_indirectness(5) == 0  # Perfect match
        assert _assess_indirectness(4) == 0  # Strong match
    
    @pytest.mark.unit
    def test_moderate_relevance_some_indirectness(self):
        """Test some indirectness downgrade with moderate relevance."""
        assert _assess_indirectness(3) == -1  # Moderate match
    
    @pytest.mark.unit
    def test_low_relevance_very_indirect(self):
        """Test very indirect downgrade with low relevance."""
        assert _assess_indirectness(2) == -2  # Tangential
        assert _assess_indirectness(1) == -2  # Weak connection


class TestDowngradeReasons:
    """Test suite for _get_downgrade_reasons function."""
    
    @pytest.mark.unit
    def test_no_downgrades(self):
        """Test no downgrade reasons when quality is high."""
        reasons = _get_downgrade_reasons(0, 0)
        assert reasons == []
    
    @pytest.mark.unit
    def test_serious_bias_only(self):
        """Test downgrade reason for serious bias risk."""
        reasons = _get_downgrade_reasons(-1, 0)
        assert len(reasons) == 1
        assert "Serious risk of bias" in reasons[0]
        assert "limited reproducibility" in reasons[0]
    
    @pytest.mark.unit
    def test_very_serious_bias_only(self):
        """Test downgrade reason for very serious bias risk."""
        reasons = _get_downgrade_reasons(-2, 0)
        assert len(reasons) == 1
        assert "Very serious risk of bias" in reasons[0]
        assert "no reproducibility" in reasons[0]
    
    @pytest.mark.unit
    def test_some_indirectness_only(self):
        """Test downgrade reason for some indirectness."""
        reasons = _get_downgrade_reasons(0, -1)
        assert len(reasons) == 1
        assert "Some indirectness" in reasons[0]
        assert "moderate relevance" in reasons[0]
    
    @pytest.mark.unit
    def test_very_indirect_only(self):
        """Test downgrade reason for very indirect evidence."""
        reasons = _get_downgrade_reasons(0, -2)
        assert len(reasons) == 1
        assert "Very indirect evidence" in reasons[0]
        assert "weak relevance" in reasons[0]
    
    @pytest.mark.unit
    def test_multiple_downgrades(self):
        """Test multiple downgrade reasons."""
        reasons = _get_downgrade_reasons(-2, -1)
        assert len(reasons) == 2
        assert any("Very serious risk of bias" in r for r in reasons)
        assert any("Some indirectness" in r for r in reasons)


class TestGradeInterpretation:
    """Test suite for _get_grade_interpretation function."""
    
    @pytest.mark.unit
    def test_high_quality_interpretation(self):
        """Test interpretation for high quality evidence."""
        interp = _get_grade_interpretation("high")
        assert "High confidence" in interp
        assert "close to estimated effect" in interp
    
    @pytest.mark.unit
    def test_moderate_quality_interpretation(self):
        """Test interpretation for moderate quality evidence."""
        interp = _get_grade_interpretation("moderate")
        assert "Moderate confidence" in interp
        assert "may differ substantially" in interp
    
    @pytest.mark.unit
    def test_low_quality_interpretation(self):
        """Test interpretation for low quality evidence."""
        interp = _get_grade_interpretation("low")
        assert "Limited confidence" in interp
        assert "may differ substantially" in interp
    
    @pytest.mark.unit
    def test_very_low_quality_interpretation(self):
        """Test interpretation for very low quality evidence."""
        interp = _get_grade_interpretation("very_low")
        assert "Very little confidence" in interp
        assert "likely substantially different" in interp
    
    @pytest.mark.unit
    def test_unknown_quality_interpretation(self):
        """Test interpretation for unknown quality level."""
        interp = _get_grade_interpretation("unknown")
        assert "Unknown quality" in interp


class TestGradeAssessment:
    """Test suite for assess_methodological_quality function."""
    
    @pytest.mark.unit
    def test_high_quality_experimental_study(self):
        """Test GRADE assessment for high-quality experimental study."""
        claim = {
            "evidence_quality": {
                "study_type": "experimental",  # Baseline: 4
                "reproducibility_score": 5,    # No downgrade (0)
                "relevance_score": 5           # No downgrade (0)
            }
        }
        
        grade = assess_methodological_quality(claim, {})
        
        # 4 (baseline) + 0 (bias) + 0 (indirect) = 4 (high)
        assert grade["grade_score"] == 4
        assert grade["grade_quality_level"] == "high"
        assert grade["baseline_quality"] == 4
        assert grade["bias_adjustment"] == 0
        assert grade["indirectness_adjustment"] == 0
        assert grade["downgrade_reasons"] == []
        assert "High confidence" in grade["interpretation"]
    
    @pytest.mark.unit
    def test_moderate_quality_review_study(self):
        """Test GRADE assessment for moderate-quality review study."""
        claim = {
            "evidence_quality": {
                "study_type": "review",         # Baseline: 3
                "reproducibility_score": 4,     # No downgrade (0)
                "relevance_score": 4            # No downgrade (0)
            }
        }
        
        grade = assess_methodological_quality(claim, {})
        
        # 3 (baseline) + 0 (bias) + 0 (indirect) = 3 (moderate)
        assert grade["grade_score"] == 3
        assert grade["grade_quality_level"] == "moderate"
        assert "Moderate confidence" in grade["interpretation"]
    
    @pytest.mark.unit
    def test_low_quality_observational_study(self):
        """Test GRADE assessment for low-quality observational study."""
        claim = {
            "evidence_quality": {
                "study_type": "observational",  # Baseline: 2
                "reproducibility_score": 3,     # -1 (serious risk)
                "relevance_score": 4            # 0 (direct)
            }
        }
        
        grade = assess_methodological_quality(claim, {})
        
        # 2 (baseline) - 1 (bias) + 0 (indirect) = 1 (very low)
        assert grade["grade_score"] == 1
        assert grade["grade_quality_level"] == "very_low"
        assert len(grade["downgrade_reasons"]) == 1
        assert "Serious risk of bias" in grade["downgrade_reasons"][0]
    
    @pytest.mark.unit
    def test_downgrade_from_experimental_to_low(self):
        """Test GRADE downgrade from experimental baseline to low quality."""
        claim = {
            "evidence_quality": {
                "study_type": "experimental",  # Baseline: 4
                "reproducibility_score": 2,    # -2 (very serious bias)
                "relevance_score": 3           # -1 (some indirectness)
            }
        }
        
        grade = assess_methodological_quality(claim, {})
        
        # 4 (baseline) - 2 (bias) - 1 (indirect) = 1 (very low)
        assert grade["grade_score"] == 1
        assert grade["grade_quality_level"] == "very_low"
        assert grade["baseline_quality"] == 4
        assert grade["bias_adjustment"] == -2
        assert grade["indirectness_adjustment"] == -1
        assert len(grade["downgrade_reasons"]) == 2
        assert any("Very serious risk of bias" in r for r in grade["downgrade_reasons"])
        assert any("Some indirectness" in r for r in grade["downgrade_reasons"])
    
    @pytest.mark.unit
    def test_minimum_score_clamping(self):
        """Test that GRADE score is clamped to minimum of 1."""
        claim = {
            "evidence_quality": {
                "study_type": "opinion",       # Baseline: 1
                "reproducibility_score": 1,    # -2 (very serious bias)
                "relevance_score": 1           # -2 (very indirect)
            }
        }
        
        grade = assess_methodological_quality(claim, {})
        
        # 1 (baseline) - 2 (bias) - 2 (indirect) = -3 → clamped to 1
        assert grade["grade_score"] == 1
        assert grade["grade_quality_level"] == "very_low"
    
    @pytest.mark.unit
    def test_maximum_score_clamping(self):
        """Test that GRADE score is clamped to maximum of 4."""
        claim = {
            "evidence_quality": {
                "study_type": "experimental",  # Baseline: 4
                "reproducibility_score": 5,    # 0 (no downgrade)
                "relevance_score": 5           # 0 (no downgrade)
            }
        }
        
        grade = assess_methodological_quality(claim, {})
        
        # 4 (baseline) + 0 + 0 = 4 (already at max)
        assert grade["grade_score"] == 4
        assert grade["grade_quality_level"] == "high"
    
    @pytest.mark.unit
    def test_default_values_for_missing_scores(self):
        """Test GRADE assessment handles missing evidence quality scores."""
        claim = {
            "evidence_quality": {}  # Empty evidence quality
        }
        
        grade = assess_methodological_quality(claim, {})
        
        # Should use defaults: unknown study (2), reproducibility 3 (-1), relevance 3 (-1)
        # 2 - 1 - 1 = 0 → clamped to 1
        assert grade["grade_score"] >= 1
        assert grade["grade_quality_level"] in ["very_low", "low", "moderate", "high"]


class TestGradeSummaryTable:
    """Test suite for generate_grade_summary_table function."""
    
    @pytest.mark.unit
    def test_empty_claims_list(self):
        """Test GRADE summary table with no claims."""
        table = generate_grade_summary_table([])
        
        assert "# GRADE Evidence Quality Summary" in table
        assert "| Sub-Requirement | Quality Level | Study Type | Downgrade Reasons | Interpretation |" in table
        assert "|-----------------|---------------|------------|-------------------|----------------|" in table
    
    @pytest.mark.unit
    def test_single_claim_summary(self):
        """Test GRADE summary table with single claim."""
        claims = [
            {
                "sub_requirement": "SR-1.1: Test requirement",
                "evidence_quality": {
                    "study_type": "experimental"
                },
                "grade_assessment": {
                    "grade_quality_level": "high",
                    "downgrade_reasons": [],
                    "interpretation": "High confidence that true effect is close to estimated effect"
                }
            }
        ]
        
        table = generate_grade_summary_table(claims)
        
        assert "SR-1.1: Test requirement" in table
        assert "High" in table
        assert "Experimental" in table
        assert "None" in table
        assert "High confidence" in table
    
    @pytest.mark.unit
    def test_multiple_claims_summary(self):
        """Test GRADE summary table with multiple claims."""
        claims = [
            {
                "sub_requirement": "SR-1.1: First requirement",
                "evidence_quality": {"study_type": "experimental"},
                "grade_assessment": {
                    "grade_quality_level": "high",
                    "downgrade_reasons": [],
                    "interpretation": "High confidence"
                }
            },
            {
                "sub_requirement": "SR-1.2: Second requirement",
                "evidence_quality": {"study_type": "observational"},
                "grade_assessment": {
                    "grade_quality_level": "low",
                    "downgrade_reasons": ["Serious risk of bias (limited reproducibility)"],
                    "interpretation": "Limited confidence"
                }
            }
        ]
        
        table = generate_grade_summary_table(claims)
        
        assert "SR-1.1: First requirement" in table
        assert "SR-1.2: Second requirement" in table
        assert table.count("|") > 10  # Multiple rows
    
    @pytest.mark.unit
    def test_downgrade_reasons_in_table(self):
        """Test GRADE summary table includes downgrade reasons."""
        claims = [
            {
                "sub_requirement": "SR-2.1: Test",
                "evidence_quality": {"study_type": "experimental"},
                "grade_assessment": {
                    "grade_quality_level": "very_low",
                    "downgrade_reasons": [
                        "Very serious risk of bias (no reproducibility)",
                        "Some indirectness (moderate relevance)"
                    ],
                    "interpretation": "Very little confidence"
                }
            }
        ]
        
        table = generate_grade_summary_table(claims)
        
        assert "Very serious risk of bias" in table
        assert "Some indirectness" in table
    
    @pytest.mark.unit
    def test_table_formatting(self):
        """Test GRADE summary table is properly formatted markdown."""
        claims = [
            {
                "sub_requirement": "SR-1.1: Test",
                "evidence_quality": {"study_type": "experimental"},
                "grade_assessment": {
                    "grade_quality_level": "high",
                    "downgrade_reasons": [],
                    "interpretation": "High confidence"
                }
            }
        ]
        
        table = generate_grade_summary_table(claims)
        
        # Check markdown table structure
        lines = table.split("\n")
        assert lines[0] == "# GRADE Evidence Quality Summary"
        assert lines[1] == ""
        assert lines[2].startswith("|")
        assert lines[3].startswith("|--")
        assert lines[4].startswith("|")
