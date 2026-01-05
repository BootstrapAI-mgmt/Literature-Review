"""
Centralized Metrics Configuration System

Enables:
- Externalized validation thresholds (YAML-based)
- Profile-based threshold switching (dev/prod/quick)
- Category filtering (accuracy/efficiency/benchmark/output_quality)
- Runtime threshold overrides via environment variables
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path
import yaml
import os
import logging

logger = logging.getLogger(__name__)


class MetricCategory(Enum):
    """Categories of validation metrics."""
    ACCURACY = "accuracy"
    EFFICIENCY = "efficiency"
    OUTPUT_QUALITY = "output_quality"
    BENCHMARK = "benchmark"
    VISUALIZATION = "visualization"
    E2E = "e2e"


class ComparisonOperator(Enum):
    """Threshold comparison operators."""
    GTE = ">="  # Greater than or equal
    LTE = "<="  # Less than or equal
    GT = ">"    # Greater than
    LT = "<"    # Less than
    EQ = "=="   # Equal


@dataclass
class MetricDefinition:
    """Definition of a single validation metric."""
    id: str                              # e.g., "AV-03"
    name: str                            # e.g., "Judge Accuracy"
    category: MetricCategory
    threshold: float                     # e.g., 0.90
    comparison: ComparisonOperator = ComparisonOperator.GTE
    enabled: bool = True
    description: str = ""
    unit: str = ""                       # e.g., "percent", "seconds", "dollars"
    
    def passes(self, value: float) -> bool:
        """Check if value passes threshold."""
        ops = {
            ComparisonOperator.GTE: lambda v, t: v >= t,
            ComparisonOperator.LTE: lambda v, t: v <= t,
            ComparisonOperator.GT: lambda v, t: v > t,
            ComparisonOperator.LT: lambda v, t: v < t,
            ComparisonOperator.EQ: lambda v, t: v == t,
        }
        return ops[self.comparison](value, self.threshold)
    
    def format_result(self, value: float) -> str:
        """Format a result message."""
        status = "✓ PASS" if self.passes(value) else "✗ FAIL"
        return f"{self.id} {self.name}: {value:.2f} {self.comparison.value} {self.threshold} → {status}"


@dataclass
class MetricProfile:
    """Threshold profile for different contexts."""
    name: str
    description: str
    threshold_overrides: Dict[str, float] = field(default_factory=dict)
    disabled_categories: List[MetricCategory] = field(default_factory=list)
    disabled_metrics: List[str] = field(default_factory=list)


@dataclass
class MetricsConfig:
    """Complete metrics configuration for validation runs."""
    metrics: Dict[str, MetricDefinition] = field(default_factory=dict)
    profiles: Dict[str, MetricProfile] = field(default_factory=dict)
    active_profile: Optional[str] = None
    enabled_categories: List[MetricCategory] = field(
        default_factory=lambda: list(MetricCategory)
    )
    
    @classmethod
    def load(cls, path: str = "tests/validation/config/metrics.yaml") -> "MetricsConfig":
        """Load metrics configuration from YAML."""
        config_path = Path(path)
        
        if not config_path.exists():
            logger.warning(f"Metrics config not found at {path}, using defaults")
            return cls._default_config()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Parse metrics
        metrics = {}
        for m in data.get("metrics", []):
            comparison = ComparisonOperator(m.get("comparison", ">="))
            category = MetricCategory(m["category"])
            metrics[m["id"]] = MetricDefinition(
                id=m["id"],
                name=m["name"],
                category=category,
                threshold=float(m["threshold"]),
                comparison=comparison,
                enabled=m.get("enabled", True),
                description=m.get("description", ""),
                unit=m.get("unit", "")
            )
        
        # Parse profiles
        profiles = {}
        for name, pdata in data.get("profiles", {}).items():
            profiles[name] = MetricProfile(
                name=name,
                description=pdata.get("description", ""),
                threshold_overrides=pdata.get("thresholds", {}),
                disabled_categories=[
                    MetricCategory(c) for c in pdata.get("disabled_categories", [])
                ],
                disabled_metrics=pdata.get("disabled_metrics", [])
            )
        
        # Parse enabled categories
        enabled_cats = data.get("enabled_categories")
        if enabled_cats:
            enabled_categories = [MetricCategory(c) for c in enabled_cats]
        else:
            enabled_categories = list(MetricCategory)
        
        return cls(
            metrics=metrics,
            profiles=profiles,
            enabled_categories=enabled_categories
        )
    
    @classmethod
    def _default_config(cls) -> "MetricsConfig":
        """Return default configuration if YAML not found."""
        return cls(
            metrics={
                "AV-03": MetricDefinition(
                    id="AV-03", name="Judge Accuracy",
                    category=MetricCategory.ACCURACY,
                    threshold=0.90
                ),
                "AV-01": MetricDefinition(
                    id="AV-01", name="Claim Precision",
                    category=MetricCategory.ACCURACY,
                    threshold=0.85
                ),
                "EV-01": MetricDefinition(
                    id="EV-01", name="Pipeline Runtime",
                    category=MetricCategory.EFFICIENCY,
                    threshold=7200, comparison=ComparisonOperator.LT,
                    unit="seconds"
                ),
            }
        )
    
    def apply_profile(self, profile_name: str) -> None:
        """Apply a named profile to override thresholds."""
        if profile_name not in self.profiles:
            raise ValueError(f"Unknown profile: {profile_name}. Available: {list(self.profiles.keys())}")
        
        profile = self.profiles[profile_name]
        self.active_profile = profile_name
        
        # Apply threshold overrides
        for metric_id, new_threshold in profile.threshold_overrides.items():
            if metric_id in self.metrics:
                self.metrics[metric_id].threshold = new_threshold
                logger.info(f"Profile '{profile_name}': {metric_id} threshold → {new_threshold}")
        
        # Apply category disables
        for cat in profile.disabled_categories:
            if cat in self.enabled_categories:
                self.enabled_categories.remove(cat)
        
        # Apply metric disables
        for metric_id in profile.disabled_metrics:
            if metric_id in self.metrics:
                self.metrics[metric_id].enabled = False
    
    def apply_env_overrides(self) -> None:
        """Apply environment variable overrides (e.g., METRIC_AV03_THRESHOLD=0.85)."""
        for metric_id, metric in self.metrics.items():
            env_key = f"METRIC_{metric_id.replace('-', '')}_THRESHOLD"
            env_value = os.environ.get(env_key)
            if env_value:
                try:
                    metric.threshold = float(env_value)
                    logger.info(f"Env override: {metric_id} threshold → {metric.threshold}")
                except ValueError:
                    logger.warning(f"Invalid env value for {env_key}: {env_value}")
    
    def get_metric(self, metric_id: str) -> MetricDefinition:
        """Get a specific metric definition."""
        if metric_id not in self.metrics:
            raise KeyError(f"Unknown metric ID: {metric_id}")
        return self.metrics[metric_id]
    
    def get_threshold(self, metric_id: str) -> float:
        """Get threshold for a specific metric."""
        return self.get_metric(metric_id).threshold
    
    def check(self, metric_id: str, value: float) -> bool:
        """Check if a value passes the metric threshold."""
        return self.get_metric(metric_id).passes(value)
    
    def get_enabled_metrics(self) -> List[MetricDefinition]:
        """Get all enabled metrics in enabled categories."""
        return [
            m for m in self.metrics.values()
            if m.enabled and m.category in self.enabled_categories
        ]
    
    def get_metrics_by_category(self, category: MetricCategory) -> List[MetricDefinition]:
        """Get all metrics in a specific category."""
        return [m for m in self.metrics.values() if m.category == category]
    
    def is_category_enabled(self, category: MetricCategory) -> bool:
        """Check if a category is enabled."""
        return category in self.enabled_categories
    
    def disable_category(self, category: MetricCategory) -> None:
        """Disable a category of metrics."""
        if category in self.enabled_categories:
            self.enabled_categories.remove(category)
    
    def enable_category(self, category: MetricCategory) -> None:
        """Enable a category of metrics."""
        if category not in self.enabled_categories:
            self.enabled_categories.append(category)


# =============================================================================
# Global Configuration Accessor
# =============================================================================

_metrics_config: Optional[MetricsConfig] = None


def load_metrics_config(
    path: str = "tests/validation/config/metrics.yaml",
    profile: Optional[str] = None
) -> MetricsConfig:
    """Load and cache metrics configuration."""
    global _metrics_config
    _metrics_config = MetricsConfig.load(path)
    
    if profile:
        _metrics_config.apply_profile(profile)
    
    _metrics_config.apply_env_overrides()
    return _metrics_config


def get_metrics_config() -> MetricsConfig:
    """Get cached metrics configuration."""
    global _metrics_config
    if _metrics_config is None:
        _metrics_config = load_metrics_config()
    return _metrics_config


def get_threshold(metric_id: str) -> float:
    """Convenience function to get a threshold."""
    return get_metrics_config().get_threshold(metric_id)


def check_metric(metric_id: str, value: float) -> bool:
    """Convenience function to check a metric."""
    return get_metrics_config().check(metric_id, value)
