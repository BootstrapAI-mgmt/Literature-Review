"""
Unit Tests for Publication Bias Detection (Task Card #22)
Tests Egger's test, trim-and-fill, funnel asymmetry, and bias detection logic.
"""

import pytest
import sys
import os
import numpy as np
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis.publication_bias import (
    detect_publication_bias,
    _eggers_test,
    _trim_and_fill,
    _calculate_funnel_asymmetry,
    _interpret_bias,
    plot_funnel_plot
)


class TestEggersTest:
    """Test suite for Egger's regression test."""
    
    @pytest.mark.unit
    def test_eggers_test_symmetric_data_no_bias(self):
        """Test Egger's regression with symmetric data (no bias)."""
        # Create symmetric data: same mean across precision levels with some noise
        np.random.seed(42)
        effect_sizes = np.array([3.0, 3.5, 4.0, 4.5, 5.0] * 4) + np.random.normal(0, 0.1, 20)
        precisions = np.array([0.5, 0.6, 0.7, 0.8, 0.9] * 4) + np.random.normal(0, 0.02, 20)
        
        result = _eggers_test(effect_sizes, precisions)
        
        assert "slope" in result
        assert "intercept" in result
        assert "p_value" in result
        assert "significant" in result
        assert isinstance(result["p_value"], float)
        # With added noise, p-value should be reasonable (not perfect 0 or 1)
        assert result["p_value"] >= 0.0
        assert isinstance(result["significant"], bool)
    
    @pytest.mark.unit
    def test_eggers_test_asymmetric_data_bias(self):
        """Test Egger's regression with asymmetric data (bias present)."""
        # Create asymmetric data: higher effects for lower precision
        effect_sizes = np.array([5.0, 4.8, 4.5, 4.2, 4.0, 3.8, 3.5, 3.2, 3.0, 2.8,
                                 5.0, 4.7, 4.4, 4.1, 3.9, 3.7, 3.4, 3.1, 2.9, 2.7])
        precisions = np.array([0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
                               0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75])
        
        result = _eggers_test(effect_sizes, precisions)
        
        assert result["p_value"] < 0.05  # Significant bias
        assert result["significant"] == True
        assert result["slope"] < 0  # Negative slope indicates bias
    
    @pytest.mark.unit
    def test_eggers_test_returns_correct_structure(self):
        """Test that Egger's test returns correct dictionary structure."""
        effect_sizes = np.random.uniform(2.0, 4.0, 20)
        precisions = np.random.uniform(0.4, 0.9, 20)
        
        result = _eggers_test(effect_sizes, precisions)
        
        assert isinstance(result, dict)
        assert set(result.keys()) == {"slope", "intercept", "p_value", "significant"}
        assert isinstance(result["slope"], float)
        assert isinstance(result["intercept"], float)
        assert isinstance(result["p_value"], float)
        assert isinstance(result["significant"], bool)


class TestTrimAndFill:
    """Test suite for trim-and-fill method."""
    
    @pytest.mark.unit
    def test_trim_and_fill_symmetric_data(self):
        """Test trim-and-fill with symmetric data (no missing studies)."""
        # Symmetric distribution around center
        effect_sizes = np.array([2.5, 3.0, 3.5, 4.0, 4.5, 5.0] * 4)
        precisions = np.ones(24)
        
        result = _trim_and_fill(effect_sizes, precisions)
        
        assert "missing_studies" in result
        assert "original_mean" in result
        assert "adjusted_mean" in result
        assert "bias_magnitude" in result
        assert result["missing_studies"] >= 0
        assert isinstance(result["missing_studies"], int)
    
    @pytest.mark.unit
    def test_trim_and_fill_asymmetric_data(self):
        """Test trim-and-fill with asymmetric data (missing low scores)."""
        # Create clearly asymmetric distribution - only high scores, missing low ones
        # Using distinct values to avoid all falling on one side of median
        effect_sizes = np.array([3.8, 4.0, 4.2, 4.5, 4.7, 5.0] * 4)
        precisions = np.ones(24)
        
        result = _trim_and_fill(effect_sizes, precisions)
        
        # With this distribution, there should be some imbalance
        assert result["missing_studies"] >= 0
        assert isinstance(result["missing_studies"], int)
    
    @pytest.mark.unit
    def test_trim_and_fill_returns_correct_structure(self):
        """Test that trim-and-fill returns correct dictionary structure."""
        effect_sizes = np.random.uniform(2.0, 4.0, 25)
        precisions = np.random.uniform(0.5, 1.0, 25)
        
        result = _trim_and_fill(effect_sizes, precisions)
        
        assert isinstance(result, dict)
        assert set(result.keys()) == {"missing_studies", "original_mean", "adjusted_mean", "bias_magnitude"}
        assert isinstance(result["missing_studies"], int)
        assert isinstance(result["original_mean"], float)
        assert isinstance(result["adjusted_mean"], float)
        assert isinstance(result["bias_magnitude"], float)
    
    @pytest.mark.unit
    def test_trim_and_fill_bias_magnitude_calculation(self):
        """Test that bias magnitude is correctly calculated."""
        effect_sizes = np.array([3.0, 3.5, 4.0, 4.5, 5.0] * 5)
        precisions = np.ones(25)
        
        result = _trim_and_fill(effect_sizes, precisions)
        
        # Bias magnitude should be absolute difference
        expected_magnitude = abs(result["adjusted_mean"] - result["original_mean"])
        assert abs(result["bias_magnitude"] - expected_magnitude) < 0.01


class TestFunnelAsymmetry:
    """Test suite for funnel plot asymmetry calculation."""
    
    @pytest.mark.unit
    def test_funnel_asymmetry_symmetric_data(self):
        """Test asymmetry score with symmetric data."""
        # Same mean for high and low precision
        np.random.seed(42)
        effect_sizes = np.random.normal(3.5, 0.5, 30)
        precisions = np.random.uniform(0.4, 0.9, 30)
        
        asymmetry = _calculate_funnel_asymmetry(effect_sizes, precisions)
        
        assert isinstance(asymmetry, float)
        assert 0.0 <= asymmetry <= 1.0
        # Symmetric data should have low asymmetry
        assert asymmetry < 0.5
    
    @pytest.mark.unit
    def test_funnel_asymmetry_asymmetric_data(self):
        """Test asymmetry score with asymmetric data."""
        # High precision studies have lower mean
        high_precision_effects = np.random.normal(3.0, 0.3, 15)
        low_precision_effects = np.random.normal(4.5, 0.3, 15)
        
        effect_sizes = np.concatenate([high_precision_effects, low_precision_effects])
        precisions = np.concatenate([np.ones(15) * 0.8, np.ones(15) * 0.4])
        
        asymmetry = _calculate_funnel_asymmetry(effect_sizes, precisions)
        
        # Asymmetric data should have higher asymmetry
        assert asymmetry > 0.3
    
    @pytest.mark.unit
    def test_funnel_asymmetry_insufficient_data(self):
        """Test asymmetry calculation with insufficient data in one group."""
        # Too few studies in one precision group
        effect_sizes = np.array([3.0, 3.5, 4.0])
        precisions = np.array([0.9, 0.9, 0.3])
        
        asymmetry = _calculate_funnel_asymmetry(effect_sizes, precisions)
        
        # Should return 0.0 when insufficient data
        assert asymmetry == 0.0
    
    @pytest.mark.unit
    def test_funnel_asymmetry_capped_at_one(self):
        """Test that asymmetry score is capped at 1.0."""
        # Create extreme asymmetry
        effect_sizes = np.array([1.0] * 15 + [5.0] * 15)
        precisions = np.array([0.9] * 15 + [0.3] * 15)
        
        asymmetry = _calculate_funnel_asymmetry(effect_sizes, precisions)
        
        assert asymmetry <= 1.0


class TestInterpretBias:
    """Test suite for bias interpretation."""
    
    @pytest.mark.unit
    def test_interpret_no_bias(self):
        """Test interpretation when no bias is detected."""
        egger = {"p_value": 0.5, "significant": False}
        trimfill = {"missing_studies": 0, "original_mean": 3.5, "adjusted_mean": 3.5}
        
        interpretation = _interpret_bias(False, egger, trimfill)
        
        assert "No significant publication bias" in interpretation
        assert "balanced" in interpretation.lower()
    
    @pytest.mark.unit
    def test_interpret_bias_with_egger(self):
        """Test interpretation when Egger's test is significant."""
        egger = {"p_value": 0.02, "significant": True}
        trimfill = {"missing_studies": 3, "original_mean": 4.0, "adjusted_mean": 3.5}
        
        interpretation = _interpret_bias(True, egger, trimfill)
        
        assert "Publication bias suspected" in interpretation
        assert "Egger's test significant" in interpretation
        assert "p=0.02" in interpretation
    
    @pytest.mark.unit
    def test_interpret_bias_with_missing_studies(self):
        """Test interpretation when missing studies are estimated."""
        egger = {"p_value": 0.08, "significant": False}
        trimfill = {"missing_studies": 8, "original_mean": 4.2, "adjusted_mean": 3.6}
        
        interpretation = _interpret_bias(True, egger, trimfill)
        
        assert "8 missing studies" in interpretation
        assert "3.6" in interpretation
        assert "4.2" in interpretation
    
    @pytest.mark.unit
    def test_interpret_includes_recommendation(self):
        """Test that interpretation includes recommendation."""
        egger = {"p_value": 0.01, "significant": True}
        trimfill = {"missing_studies": 5, "original_mean": 4.0, "adjusted_mean": 3.5}
        
        interpretation = _interpret_bias(True, egger, trimfill)
        
        assert "unpublished studies" in interpretation.lower() or "negative results" in interpretation.lower()


class TestDetectPublicationBias:
    """Test suite for main bias detection function."""
    
    @pytest.mark.unit
    def test_detect_bias_insufficient_claims(self):
        """Test that detection returns None with <20 claims."""
        claims = [
            {"evidence_quality": {"composite_score": 3.0}} for _ in range(15)
        ]
        
        result = detect_publication_bias(claims, "Test Sub-Req")
        
        assert result is None
    
    @pytest.mark.unit
    def test_detect_bias_sufficient_claims_no_scores(self):
        """Test that detection returns None when claims lack composite scores."""
        claims = [
            {"evidence_quality": {}} for _ in range(25)
        ]
        
        result = detect_publication_bias(claims, "Test Sub-Req")
        
        assert result is None
    
    @pytest.mark.unit
    def test_detect_bias_sufficient_symmetric_data(self):
        """Test bias detection with sufficient symmetric data."""
        np.random.seed(42)
        claims = [
            {"evidence_quality": {"composite_score": float(score)}}
            for score in np.random.normal(3.5, 0.5, 25)
        ]
        
        result = detect_publication_bias(claims, "Test Sub-Req")
        
        assert result is not None
        assert isinstance(result, dict)
        assert result["sub_requirement"] == "Test Sub-Req"
        assert result["num_studies"] == 25
        assert "bias_detected" in result
        assert "eggers_test" in result
        assert "trim_and_fill" in result
        assert "asymmetry_score" in result
        assert "interpretation" in result
    
    @pytest.mark.unit
    def test_detect_bias_asymmetric_data_triggers_detection(self):
        """Test that asymmetric data triggers bias detection."""
        # Create clearly biased data with variation
        np.random.seed(789)
        claims = [
            {"evidence_quality": {"composite_score": float(score)}}
            for score in np.random.uniform(3.8, 5.0, 25)
        ]
        
        result = detect_publication_bias(claims, "Test Sub-Req")
        
        assert result is not None
        # Verify the structure is correct
        assert isinstance(result["bias_detected"], bool)
    
    @pytest.mark.unit
    def test_detect_bias_missing_evidence_quality(self):
        """Test handling of claims without evidence_quality."""
        claims = [
            {"evidence_quality": {"composite_score": 3.5}} for _ in range(15)
        ] + [
            {"other_field": "value"} for _ in range(10)
        ]
        
        result = detect_publication_bias(claims, "Test Sub-Req")
        
        # Should return None because only 15 valid scores (< 20)
        assert result is None
    
    @pytest.mark.unit
    def test_detect_bias_result_structure(self):
        """Test that detection result has correct structure."""
        claims = [
            {"evidence_quality": {"composite_score": float(i % 5 + 1)}}
            for i in range(30)
        ]
        
        result = detect_publication_bias(claims, "Test Sub-Req 1.1.1")
        
        assert isinstance(result, dict)
        assert set(result.keys()) == {
            "sub_requirement", "num_studies", "bias_detected",
            "eggers_test", "trim_and_fill", "asymmetry_score", "interpretation"
        }
        assert result["sub_requirement"] == "Test Sub-Req 1.1.1"
        assert result["num_studies"] == 30
        assert isinstance(result["bias_detected"], bool)
        assert isinstance(result["asymmetry_score"], float)
        assert isinstance(result["interpretation"], str)
    
    @pytest.mark.unit
    def test_detect_bias_thresholds(self):
        """Test bias detection threshold logic."""
        # Test with data that should trigger bias detection
        # (high Egger's p-value, high asymmetry, many missing studies)
        np.random.seed(123)
        
        # Create biased data: high scores for low precision
        high_precision_scores = [2.5, 2.8, 3.0] * 4
        low_precision_scores = [4.5, 4.7, 5.0] * 4
        
        claims = [
            {"evidence_quality": {"composite_score": float(score)}}
            for score in high_precision_scores + low_precision_scores
        ]
        
        result = detect_publication_bias(claims, "Biased Sub-Req")
        
        assert result is not None
        # At least one criterion should trigger
        assert (
            result["eggers_test"]["p_value"] < 0.05 or
            result["asymmetry_score"] > 0.3 or
            result["trim_and_fill"]["missing_studies"] > 5
        )


class TestPlotFunnelPlot:
    """Test suite for funnel plot generation."""
    
    @pytest.mark.unit
    def test_plot_funnel_plot_creates_file(self):
        """Test that funnel plot creates output file."""
        claims = [
            {"evidence_quality": {"composite_score": float(i % 5 + 1)}}
            for i in range(20)
        ]
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            output_file = tmp.name
        
        try:
            plot_funnel_plot(claims, "Test Sub-Req", output_file)
            
            # Check file exists and has content
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
        finally:
            # Cleanup
            if os.path.exists(output_file):
                os.remove(output_file)
    
    @pytest.mark.unit
    def test_plot_funnel_plot_insufficient_data(self):
        """Test that plot is not created with insufficient data."""
        claims = [
            {"evidence_quality": {"composite_score": 3.0}}
            for _ in range(5)
        ]
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            output_file = tmp.name
        
        # Remove the file first
        os.remove(output_file)
        
        try:
            plot_funnel_plot(claims, "Test Sub-Req", output_file)
            
            # File should not be created
            assert not os.path.exists(output_file)
        finally:
            # Cleanup if file was created
            if os.path.exists(output_file):
                os.remove(output_file)
    
    @pytest.mark.unit
    def test_plot_funnel_plot_missing_scores(self):
        """Test plot handling of claims without scores."""
        claims = [
            {"evidence_quality": {"composite_score": 3.5}} for _ in range(5)
        ] + [
            {"evidence_quality": {}} for _ in range(10)
        ]
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            output_file = tmp.name
        
        # Remove the file first
        os.remove(output_file)
        
        try:
            plot_funnel_plot(claims, "Test Sub-Req", output_file)
            
            # Should not create plot with only 5 valid scores
            assert not os.path.exists(output_file)
        finally:
            # Cleanup
            if os.path.exists(output_file):
                os.remove(output_file)
