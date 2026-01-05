"""
Unit tests for Metrics Configuration System (VM-W0.5-1).

Tests validation IDs:
- MT-01: Metrics YAML config loads and validates correctly
- MT-02: Profile switching changes thresholds as expected
"""

import pytest
import os
import tempfile
from pathlib import Path

from tests.validation.config.metrics_config import (
    MetricsConfig,
    MetricDefinition,
    MetricProfile,
    MetricCategory,
    ComparisonOperator,
    load_metrics_config,
    get_metrics_config,
    get_threshold,
    check_metric,
)


class TestMetricDefinition:
    """Tests for MetricDefinition class."""
    
    def test_passes_gte(self):
        """Test greater-than-or-equal comparison."""
        metric = MetricDefinition(
            id="TEST-01",
            name="Test Metric",
            category=MetricCategory.ACCURACY,
            threshold=0.90,
            comparison=ComparisonOperator.GTE
        )
        assert metric.passes(0.91) is True
        assert metric.passes(0.90) is True
        assert metric.passes(0.89) is False
    
    def test_passes_lte(self):
        """Test less-than-or-equal comparison."""
        metric = MetricDefinition(
            id="TEST-02",
            name="Test Metric",
            category=MetricCategory.EFFICIENCY,
            threshold=100,
            comparison=ComparisonOperator.LTE
        )
        assert metric.passes(99) is True
        assert metric.passes(100) is True
        assert metric.passes(101) is False
    
    def test_passes_lt(self):
        """Test less-than comparison."""
        metric = MetricDefinition(
            id="TEST-03",
            name="Test Metric",
            category=MetricCategory.BENCHMARK,
            threshold=50,
            comparison=ComparisonOperator.LT
        )
        assert metric.passes(49) is True
        assert metric.passes(50) is False
        assert metric.passes(51) is False
    
    def test_passes_gt(self):
        """Test greater-than comparison."""
        metric = MetricDefinition(
            id="TEST-04",
            name="Test Metric",
            category=MetricCategory.ACCURACY,
            threshold=0.80,
            comparison=ComparisonOperator.GT
        )
        assert metric.passes(0.81) is True
        assert metric.passes(0.80) is False
        assert metric.passes(0.79) is False
    
    def test_passes_eq(self):
        """Test equal comparison."""
        metric = MetricDefinition(
            id="TEST-05",
            name="Test Metric",
            category=MetricCategory.OUTPUT_QUALITY,
            threshold=1.0,
            comparison=ComparisonOperator.EQ
        )
        assert metric.passes(1.0) is True
        assert metric.passes(0.99) is False
        assert metric.passes(1.01) is False
    
    def test_format_result(self):
        """Test result formatting."""
        metric = MetricDefinition(
            id="AV-03",
            name="Judge Accuracy",
            category=MetricCategory.ACCURACY,
            threshold=0.90,
            comparison=ComparisonOperator.GTE
        )
        result = metric.format_result(0.92)
        assert "AV-03" in result
        assert "Judge Accuracy" in result
        assert "PASS" in result
        
        result = metric.format_result(0.85)
        assert "FAIL" in result


class TestMetricsConfigLoad:
    """Tests for MetricsConfig loading (MT-01)."""
    
    def test_load_yaml_config(self):
        """MT-01: Test loading metrics.yaml configuration."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        # Verify metrics were loaded
        assert len(config.metrics) > 0
        assert "AV-03" in config.metrics
        assert "EV-01" in config.metrics
        
        # Verify profiles were loaded
        assert len(config.profiles) > 0
        assert "development" in config.profiles
        assert "production" in config.profiles
        assert "quick" in config.profiles
        assert "ci" in config.profiles
    
    def test_load_default_config(self):
        """Test fallback to default config when file not found."""
        config = MetricsConfig.load("nonexistent/path/metrics.yaml")
        
        # Default config should have minimal metrics
        assert len(config.metrics) > 0
        assert "AV-03" in config.metrics
        assert "AV-01" in config.metrics
    
    def test_metric_properties(self):
        """MT-01: Verify all metric IDs have valid thresholds."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        for metric_id, metric in config.metrics.items():
            assert metric.id == metric_id
            assert metric.name, f"{metric_id} missing name"
            assert metric.threshold is not None, f"{metric_id} missing threshold"
            assert isinstance(metric.category, MetricCategory)
            assert isinstance(metric.comparison, ComparisonOperator)
    
    def test_all_categories_represented(self):
        """Verify all metric categories have at least one metric."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        for category in MetricCategory:
            metrics = config.get_metrics_by_category(category)
            assert len(metrics) > 0, f"No metrics for category {category.value}"


class TestProfileSwitching:
    """Tests for profile switching (MT-02)."""
    
    def test_apply_development_profile(self):
        """MT-02: Test applying development profile."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        # Get original threshold
        original_threshold = config.get_threshold("AV-03")
        
        # Apply development profile
        config.apply_profile("development")
        
        # Verify threshold was overridden
        assert config.active_profile == "development"
        assert config.get_threshold("AV-03") == 0.85  # Development has 0.85
    
    def test_apply_production_profile(self):
        """MT-02: Test applying production profile."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        config.apply_profile("production")
        
        assert config.active_profile == "production"
        assert config.get_threshold("AV-03") == 0.92  # Production has 0.92
    
    def test_apply_quick_profile_disables_categories(self):
        """MT-02: Test quick profile disables benchmark/e2e categories."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        # Before applying quick profile
        assert MetricCategory.BENCHMARK in config.enabled_categories
        assert MetricCategory.E2E in config.enabled_categories
        
        config.apply_profile("quick")
        
        # After applying quick profile
        assert config.active_profile == "quick"
        assert MetricCategory.BENCHMARK not in config.enabled_categories
        assert MetricCategory.E2E not in config.enabled_categories
        assert MetricCategory.VISUALIZATION not in config.enabled_categories
    
    def test_unknown_profile_raises_error(self):
        """Test that unknown profile raises ValueError."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        with pytest.raises(ValueError) as exc_info:
            config.apply_profile("nonexistent_profile")
        
        assert "Unknown profile" in str(exc_info.value)


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""
    
    def test_env_override_threshold(self, monkeypatch):
        """Test environment variable overrides threshold."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        # Set environment variable
        monkeypatch.setenv("METRIC_AV03_THRESHOLD", "0.75")
        
        # Apply overrides
        config.apply_env_overrides()
        
        # Verify threshold was changed
        assert config.get_threshold("AV-03") == 0.75
    
    def test_env_override_invalid_value(self, monkeypatch):
        """Test invalid environment variable is ignored."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        original_threshold = config.get_threshold("AV-03")
        
        # Set invalid environment variable
        monkeypatch.setenv("METRIC_AV03_THRESHOLD", "not_a_number")
        
        # Apply overrides (should not raise, just log warning)
        config.apply_env_overrides()
        
        # Threshold should remain unchanged
        assert config.get_threshold("AV-03") == original_threshold


class TestCategoryFiltering:
    """Tests for category enable/disable."""
    
    def test_disable_category(self):
        """Test disabling a category."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        assert config.is_category_enabled(MetricCategory.BENCHMARK)
        
        config.disable_category(MetricCategory.BENCHMARK)
        
        assert not config.is_category_enabled(MetricCategory.BENCHMARK)
    
    def test_enable_category(self):
        """Test enabling a category."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        # First disable
        config.disable_category(MetricCategory.BENCHMARK)
        assert not config.is_category_enabled(MetricCategory.BENCHMARK)
        
        # Then enable
        config.enable_category(MetricCategory.BENCHMARK)
        assert config.is_category_enabled(MetricCategory.BENCHMARK)
    
    def test_get_enabled_metrics(self):
        """Test getting only enabled metrics."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        # All metrics should be enabled initially
        all_metrics = config.get_enabled_metrics()
        assert len(all_metrics) == len(config.metrics)
        
        # Disable benchmark category
        config.disable_category(MetricCategory.BENCHMARK)
        
        # Enabled metrics should be less
        enabled_metrics = config.get_enabled_metrics()
        benchmark_metrics = config.get_metrics_by_category(MetricCategory.BENCHMARK)
        
        assert len(enabled_metrics) == len(all_metrics) - len(benchmark_metrics)


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_check_metric_passes(self):
        """Test check_metric convenience function for passing value."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        # Load fresh config
        import tests.validation.config.metrics_config as mc
        mc._metrics_config = None  # Reset global state
        mc.load_metrics_config(str(config_path))
        
        # AV-03 has threshold 0.90 with >=
        assert check_metric("AV-03", 0.92) is True
        assert check_metric("AV-03", 0.85) is False
    
    def test_get_threshold(self):
        """Test get_threshold convenience function."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        import tests.validation.config.metrics_config as mc
        mc._metrics_config = None  # Reset global state
        mc.load_metrics_config(str(config_path))
        
        threshold = get_threshold("AV-03")
        assert threshold == 0.90
    
    def test_unknown_metric_raises_error(self):
        """Test that unknown metric ID raises KeyError."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        import tests.validation.config.metrics_config as mc
        mc._metrics_config = None  # Reset global state
        mc.load_metrics_config(str(config_path))
        
        with pytest.raises(KeyError):
            get_threshold("UNKNOWN-99")


class TestGlobalConfigAccessor:
    """Tests for global configuration accessor."""
    
    def test_load_and_get_metrics_config(self):
        """Test load and get metrics config functions."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        import tests.validation.config.metrics_config as mc
        mc._metrics_config = None  # Reset global state
        
        # Load config
        loaded_config = load_metrics_config(str(config_path), profile="development")
        
        # Get same config
        got_config = get_metrics_config()
        
        assert loaded_config is got_config
        assert got_config.active_profile == "development"
    
    def test_load_with_profile(self):
        """Test loading config with profile applied."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        import tests.validation.config.metrics_config as mc
        mc._metrics_config = None  # Reset global state
        
        config = load_metrics_config(str(config_path), profile="production")
        
        assert config.active_profile == "production"
        assert config.get_threshold("AV-03") == 0.92


class TestYAMLSchema:
    """Tests for YAML schema validation."""
    
    def test_all_metrics_have_required_fields(self):
        """Verify all metrics in YAML have required fields."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        for metric_id, metric in config.metrics.items():
            assert metric.id, f"Missing id for {metric_id}"
            assert metric.name, f"Missing name for {metric_id}"
            assert metric.category, f"Missing category for {metric_id}"
            assert metric.threshold is not None, f"Missing threshold for {metric_id}"
    
    def test_all_profiles_have_descriptions(self):
        """Verify all profiles have descriptions."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        for profile_name, profile in config.profiles.items():
            assert profile.description, f"Missing description for profile {profile_name}"
    
    def test_profile_thresholds_reference_valid_metrics(self):
        """Verify profile thresholds reference existing metrics."""
        config_path = Path(__file__).parent.parent / "config" / "metrics.yaml"
        config = MetricsConfig.load(str(config_path))
        
        for profile_name, profile in config.profiles.items():
            for metric_id in profile.threshold_overrides:
                assert metric_id in config.metrics, (
                    f"Profile '{profile_name}' references unknown metric: {metric_id}"
                )
