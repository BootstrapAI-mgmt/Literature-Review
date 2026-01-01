# Task Card: Metrics Configuration System

**Task ID:** VM-W0.5-1  
**Wave:** 0.5 (Modularization Infrastructure)  
**Priority:** HIGH (P1 - Lowest risk, immediate benefit)  
**Estimated Effort:** 6 hours  
**Status:** Not Started  
**Dependencies:** None (parallel with VM-W0-1)  
**Blocks:** All validation tests (enables configurable thresholds)  
**Validation IDs:** MT-01, MT-02

---

## Objective

Create a centralized, YAML-based metrics configuration system that allows validation thresholds to be modified without code changes, enables profile-based threshold switching (dev/production/quick), and supports category-level enable/disable for validation runs.

## Background

The third-party modularization assessment (Score: 4/10) identified that validation thresholds are hardcoded across multiple task cards:

```python
# Current: Hardcoded in test code
assert relevance_rate >= 0.80  # Cannot change without editing code
assert accuracy >= 0.90        # No dev vs prod distinction
```

This prevents:
- Adjusting thresholds for different contexts (development vs production)
- Enabling/disabling specific metrics per run
- Adding new metrics without modifying task card implementations

## Success Criteria

- [ ] MT-01: Metrics YAML config loads and validates correctly
- [ ] MT-02: Profile switching changes thresholds as expected
- [ ] All existing hardcoded thresholds externalized to YAML
- [ ] `--metrics-profile` CLI flag available in pytest
- [ ] Category filtering works (run only accuracy tests, skip benchmarks)

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| MT-01 | Metrics Config Validation | `metrics.yaml` | Valid config object | YAML schema valid, all IDs defined |
| MT-02 | Profile Switching | Profile name | Updated thresholds | Thresholds change per profile |

---

## Deliverables

### 1. Metrics Configuration Module

**File:** `tests/validation/config/metrics_config.py`

```python
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
```

### 2. Metrics YAML Configuration

**File:** `tests/validation/config/metrics.yaml`

```yaml
# =============================================================================
# Validation Matrix Metrics Configuration
# =============================================================================
# 
# This file defines all validation thresholds externally from test code.
# Thresholds can be overridden via:
#   1. Profile selection (--metrics-profile dev|production|quick)
#   2. Environment variables (METRIC_AV03_THRESHOLD=0.85)
#
# =============================================================================

# Enable/disable entire categories (uncomment to disable)
enabled_categories:
  - accuracy
  - efficiency
  - output_quality
  - benchmark
  - visualization
  - e2e

# =============================================================================
# Metric Definitions
# =============================================================================

metrics:
  # ---------------------------------------------------------------------------
  # Accuracy Metrics (AV-*)
  # ---------------------------------------------------------------------------
  - id: AV-01
    name: Claim Extraction Precision
    category: accuracy
    threshold: 0.85
    comparison: ">="
    unit: ratio
    description: "True positives / (True positives + False positives)"

  - id: AV-02
    name: Claim Extraction Recall
    category: accuracy
    threshold: 0.80
    comparison: ">="
    unit: ratio
    description: "True positives / (True positives + False negatives)"

  - id: AV-03
    name: Judge Accuracy
    category: accuracy
    threshold: 0.90
    comparison: ">="
    unit: ratio
    description: "Judge verdicts matching golden dataset"

  - id: AV-04
    name: Judge Calibration (Brier Score)
    category: accuracy
    threshold: 0.15
    comparison: "<"
    unit: score
    description: "Lower is better; measures probability calibration"

  - id: AV-05
    name: DRA Recovery Rate
    category: accuracy
    threshold: 0.40
    comparison: ">="
    unit: ratio
    description: "Deep review recovers initially rejected claims"

  - id: AV-06
    name: Gap False Negative Rate
    category: accuracy
    threshold: 0.05
    comparison: "<"
    unit: ratio
    description: "Known gaps missed by pipeline"

  - id: AV-07
    name: Pre-filter Accuracy
    category: accuracy
    threshold: 0.95
    comparison: ">="
    unit: ratio
    description: "Pre-filter correctly identifies relevant papers"

  - id: AV-08
    name: Human Correlation
    category: accuracy
    threshold: 0.80
    comparison: ">="
    unit: correlation
    description: "Spearman correlation with human rankings"

  # ---------------------------------------------------------------------------
  # Efficiency Metrics (EV-*)
  # ---------------------------------------------------------------------------
  - id: EV-01
    name: Pipeline Full Run Time
    category: efficiency
    threshold: 7200
    comparison: "<"
    unit: seconds
    description: "Full pipeline run for 100 papers"

  - id: EV-02
    name: Incremental Mode Speedup
    category: efficiency
    threshold: 0.60
    comparison: ">="
    unit: ratio
    description: "Speed improvement vs fresh run"

  - id: EV-03
    name: Cache Hit Rate
    category: efficiency
    threshold: 0.70
    comparison: ">="
    unit: ratio
    description: "API cache hit rate"

  - id: EV-04
    name: API Cost per Paper
    category: efficiency
    threshold: 0.50
    comparison: "<"
    unit: dollars
    description: "Average API cost per paper processed"

  - id: EV-05
    name: Pre-filter Reduction
    category: efficiency
    threshold: 0.30
    comparison: ">="
    unit: ratio
    description: "Percentage of papers filtered before deep analysis"

  - id: EV-06
    name: Rate Limit Violations
    category: efficiency
    threshold: 0
    comparison: "=="
    unit: count
    description: "Number of rate limit errors"

  - id: EV-07
    name: Checkpoint Recovery Time
    category: efficiency
    threshold: 30
    comparison: "<"
    unit: seconds
    description: "Time to resume from checkpoint"

  # ---------------------------------------------------------------------------
  # Output Quality Metrics (OQ-*, RA-*)
  # ---------------------------------------------------------------------------
  - id: OQ-01
    name: Gap Report Schema Valid
    category: output_quality
    threshold: 1.0
    comparison: "=="
    unit: boolean
    description: "gap_analysis_report.json passes JSON schema"

  - id: OQ-02
    name: Executive Summary Sections
    category: output_quality
    threshold: 5
    comparison: ">="
    unit: count
    description: "Required sections present in executive_summary.md"

  - id: RA-01
    name: Search Query Relevance
    category: output_quality
    threshold: 0.80
    comparison: ">="
    unit: ratio
    description: "Percentage of queries rated relevant by experts"

  - id: RA-02
    name: Priority Classification Accuracy
    category: output_quality
    threshold: 0.90
    comparison: ">="
    unit: ratio
    description: "Correct CRITICAL/HIGH/MEDIUM/LOW assignment"

  - id: RA-03
    name: Database Appropriateness
    category: output_quality
    threshold: 0.95
    comparison: ">="
    unit: ratio
    description: "Domain→database mapping correctness"

  - id: RA-04
    name: Query Uniqueness
    category: output_quality
    threshold: 0.95
    comparison: ">="
    unit: ratio
    description: "Non-duplicate recommendation rate"

  - id: RA-05
    name: Recommendation Completeness
    category: output_quality
    threshold: 1.0
    comparison: "=="
    unit: ratio
    description: "All gaps have at least one recommendation"

  # ---------------------------------------------------------------------------
  # Benchmark Metrics (BM-*)
  # ---------------------------------------------------------------------------
  - id: BM-01
    name: Journal Reviewer Latency
    category: benchmark
    threshold: 45
    comparison: "<"
    unit: seconds
    description: "Single paper analysis time (20-page PDF)"

  - id: BM-02
    name: Judge Throughput
    category: benchmark
    threshold: 20
    comparison: ">="
    unit: claims_per_minute
    description: "Batch claim evaluation rate"

  - id: BM-03
    name: DRA Analysis Time
    category: benchmark
    threshold: 30
    comparison: "<"
    unit: seconds
    description: "Deep review analysis per claim"

  - id: BM-04
    name: Orchestrator Throughput
    category: benchmark
    threshold: 10
    comparison: ">="
    unit: papers_per_hour
    description: "Full orchestrator pipeline throughput"

  - id: BM-05
    name: Component Memory Usage
    category: benchmark
    threshold: 2048
    comparison: "<"
    unit: megabytes
    description: "Peak memory per component"

  - id: BM-06
    name: Parallel Scaling Efficiency
    category: benchmark
    threshold: 0.75
    comparison: ">="
    unit: ratio
    description: "Efficiency when scaling to 4 workers"

  # ---------------------------------------------------------------------------
  # Quality Benchmark Metrics (QB-*)
  # ---------------------------------------------------------------------------
  - id: QB-01
    name: Golden Dataset Coverage
    category: benchmark
    threshold: 50
    comparison: ">="
    unit: claims
    description: "Minimum annotated claims in golden dataset"

  - id: QB-02
    name: Pillar Mapping Coverage
    category: benchmark
    threshold: 100
    comparison: ">="
    unit: claims
    description: "Claims with known pillar mappings"

  - id: QB-03
    name: Cross-Domain Diversity
    category: benchmark
    threshold: 3
    comparison: ">="
    unit: domains
    description: "Number of domains represented in golden dataset"

  - id: QB-04
    name: Weak Evidence Cases
    category: benchmark
    threshold: 30
    comparison: ">="
    unit: claims
    description: "False-positive testing claims"

  - id: QB-05
    name: Known Gap Coverage
    category: benchmark
    threshold: 10
    comparison: ">="
    unit: gaps
    description: "Gaps with known solution recommendations"

  # ---------------------------------------------------------------------------
  # Output Quality Metrics (OQ-03 to OQ-10)
  # ---------------------------------------------------------------------------
  - id: OQ-03
    name: Search Suggestions Schema Valid
    category: output_quality
    threshold: 1.0
    comparison: "=="
    unit: boolean
    description: "suggested_searches.json passes JSON schema"

  - id: OQ-04
    name: Search Suggestions Readable
    category: output_quality
    threshold: 1.0
    comparison: "=="
    unit: boolean
    description: "suggested_searches.md is human-readable"

  - id: OQ-05
    name: Search Plan Coherence
    category: output_quality
    threshold: 0.90
    comparison: ">="
    unit: ratio
    description: "optimized_search_plan.json strategy coherence"

  - id: OQ-06
    name: Proof Chain Completeness
    category: output_quality
    threshold: 1.0
    comparison: "=="
    unit: ratio
    description: "All approved claims linked in proof_chain.json"

  - id: OQ-07
    name: Sufficiency Matrix Coverage
    category: output_quality
    threshold: 1.0
    comparison: "=="
    unit: ratio
    description: "All pillars represented in sufficiency_matrix.json"

  - id: OQ-08
    name: Triangulation Accuracy
    category: output_quality
    threshold: 0.85
    comparison: ">="
    unit: ratio
    description: "Cross-validation accuracy in triangulation.json"

  - id: OQ-09
    name: Evidence Decay Correctness
    category: output_quality
    threshold: 1.0
    comparison: "=="
    unit: boolean
    description: "Temporal weighting correct in evidence_decay.json"

  - id: OQ-10
    name: Output File Consistency
    category: output_quality
    threshold: 0
    comparison: "=="
    unit: count
    description: "No orphaned references between output files"

  # ---------------------------------------------------------------------------
  # E2E Metrics (E2E-*)
  # ---------------------------------------------------------------------------
  - id: E2E-01
    name: Small Run Time
    category: e2e
    threshold: 900
    comparison: "<"
    unit: seconds
    description: "10 papers complete run"

  - id: E2E-01-COST
    name: Small Run Cost
    category: e2e
    threshold: 5.0
    comparison: "<"
    unit: dollars
    description: "10 papers API cost"

  - id: E2E-02
    name: Medium Run Time
    category: e2e
    threshold: 3600
    comparison: "<"
    unit: seconds
    description: "50 papers complete run"

  - id: E2E-03
    name: Large Run Time
    category: e2e
    threshold: 14400
    comparison: "<"
    unit: seconds
    description: "200 papers complete run"

  # ---------------------------------------------------------------------------
  # Visualization Metrics (VI-*)
  # ---------------------------------------------------------------------------
  - id: VI-01
    name: HTML Render Count
    category: visualization
    threshold: 10
    comparison: ">="
    unit: count
    description: "All 10 HTML visualizations render"

  - id: VI-02
    name: Plotly Features
    category: visualization
    threshold: 4
    comparison: ">="
    unit: count
    description: "Zoom, pan, hover, download all work"


# =============================================================================
# Threshold Profiles
# =============================================================================

profiles:
  development:
    description: "Relaxed thresholds for development/debugging"
    thresholds:
      AV-03: 0.85      # Lower judge accuracy for dev
      AV-05: 0.35      # Lower DRA recovery for dev
      EV-01: 14400     # Allow 4 hours in dev
      EV-04: 1.00      # Allow higher cost in dev
      BM-01: 60        # Relaxed latency for dev
    disabled_categories: []
    disabled_metrics: []

  production:
    description: "Strict thresholds for production validation"
    thresholds:
      AV-03: 0.92      # Higher judge accuracy for prod
      AV-05: 0.45      # Higher DRA recovery for prod
      EV-04: 0.40      # Stricter cost control
      RA-01: 0.85      # Higher relevance bar
    disabled_categories: []
    disabled_metrics: []

  quick:
    description: "Fast validation run (accuracy only, skip benchmarks)"
    thresholds:
      EV-01: 3600      # 1 hour max
    disabled_categories:
      - benchmark
      - e2e
      - visualization
    disabled_metrics:
      - BM-01
      - BM-02
      - BM-03

  ci:
    description: "CI/CD pipeline validation (balanced speed/coverage)"
    thresholds:
      EV-01: 1800      # 30 min max for CI
      E2E-01: 600      # Faster E2E timeout
    disabled_categories:
      - benchmark      # Skip full benchmarks in CI
    disabled_metrics: []
```

### 3. pytest Integration

**File:** `tests/conftest.py` (additions)

```python
# =============================================================================
# Metrics Configuration Integration
# =============================================================================

import pytest
from pathlib import Path

# Import metrics config (will be created by VM-W0.5-1)
try:
    from tests.validation.config.metrics_config import (
        load_metrics_config,
        get_metrics_config,
        MetricsConfig,
        MetricCategory
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--metrics-profile",
        action="store",
        default="development",
        help="Metrics profile: development, production, quick, ci"
    )
    parser.addoption(
        "--skip-category",
        action="append",
        default=[],
        help="Skip metric categories: accuracy, efficiency, benchmark, e2e"
    )
    parser.addoption(
        "--only-category",
        action="store",
        default=None,
        help="Run only this metric category"
    )


@pytest.fixture(scope="session")
def metrics_config(request) -> "MetricsConfig":
    """Load metrics configuration with profile applied."""
    if not METRICS_AVAILABLE:
        pytest.skip("Metrics config not available")
    
    profile = request.config.getoption("--metrics-profile")
    config = load_metrics_config(profile=profile)
    
    # Apply category skips
    skip_cats = request.config.getoption("--skip-category")
    for cat_name in skip_cats:
        try:
            cat = MetricCategory(cat_name)
            config.disable_category(cat)
        except ValueError:
            pass
    
    # Apply only-category filter
    only_cat = request.config.getoption("--only-category")
    if only_cat:
        try:
            target = MetricCategory(only_cat)
            for cat in list(MetricCategory):
                if cat != target:
                    config.disable_category(cat)
        except ValueError:
            pass
    
    return config


@pytest.fixture
def get_threshold(metrics_config):
    """Fixture to get thresholds by ID."""
    def _get(metric_id: str) -> float:
        return metrics_config.get_threshold(metric_id)
    return _get


@pytest.fixture
def check_metric(metrics_config):
    """Fixture to check if a value passes a metric."""
    def _check(metric_id: str, value: float) -> bool:
        return metrics_config.check(metric_id, value)
    return _check
```

### 4. Metrics Config Validation Script

**File:** `scripts/validate_metrics_config.py`

```python
#!/usr/bin/env python3
"""
Validate metrics.yaml configuration file.

Usage:
    python scripts/validate_metrics_config.py
    python scripts/validate_metrics_config.py --config path/to/metrics.yaml
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.validation.config.metrics_config import MetricsConfig, MetricCategory


def validate_config(config_path: str) -> bool:
    """Validate metrics configuration file."""
    print(f"Validating: {config_path}")
    
    try:
        config = MetricsConfig.load(config_path)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return False
    
    errors = []
    warnings = []
    
    # Check all metrics have required fields
    for metric_id, metric in config.metrics.items():
        if not metric.name:
            errors.append(f"{metric_id}: Missing name")
        if metric.threshold is None:
            errors.append(f"{metric_id}: Missing threshold")
    
    # Check profiles reference valid metrics
    for profile_name, profile in config.profiles.items():
        for metric_id in profile.threshold_overrides:
            if metric_id not in config.metrics:
                warnings.append(f"Profile '{profile_name}': Unknown metric {metric_id}")
        for metric_id in profile.disabled_metrics:
            if metric_id not in config.metrics:
                warnings.append(f"Profile '{profile_name}': Unknown disabled metric {metric_id}")
    
    # Report results
    print(f"\n📊 Metrics: {len(config.metrics)}")
    print(f"📋 Profiles: {len(config.profiles)}")
    print(f"🏷️  Categories: {len(config.enabled_categories)}")
    
    for cat in MetricCategory:
        count = len(config.get_metrics_by_category(cat))
        status = "✓" if cat in config.enabled_categories else "○"
        print(f"   {status} {cat.value}: {count} metrics")
    
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"   - {w}")
    
    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for e in errors:
            print(f"   - {e}")
        return False
    
    print("\n✅ Configuration valid!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Validate metrics configuration")
    parser.add_argument(
        "--config",
        default="tests/validation/config/metrics.yaml",
        help="Path to metrics.yaml"
    )
    args = parser.parse_args()
    
    success = validate_config(args.config)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

---

## Usage Examples

### Command-Line Usage

```bash
# Run with development profile (relaxed thresholds)
pytest tests/validation/ --metrics-profile development

# Run with production profile (strict thresholds)
pytest tests/validation/ --metrics-profile production

# Quick run (accuracy only, skip benchmarks)
pytest tests/validation/ --metrics-profile quick

# Skip specific categories
pytest tests/validation/ --skip-category benchmark --skip-category e2e

# Run only accuracy tests
pytest tests/validation/ --only-category accuracy

# Override via environment variable
METRIC_AV03_THRESHOLD=0.85 pytest tests/validation/
```

### In-Test Usage

```python
# OLD: Hardcoded threshold
def test_judge_accuracy_old(golden_dataset):
    accuracy = calculate_accuracy(...)
    assert accuracy >= 0.90  # Hardcoded!

# NEW: Configurable threshold
def test_judge_accuracy(golden_dataset, metrics_config):
    accuracy = calculate_accuracy(...)
    threshold = metrics_config.get_threshold("AV-03")
    assert accuracy >= threshold, (
        f"Judge accuracy {accuracy:.1%} below threshold {threshold:.1%}"
    )

# OR using convenience fixture
def test_judge_accuracy_simple(golden_dataset, check_metric):
    accuracy = calculate_accuracy(...)
    assert check_metric("AV-03", accuracy)
```

---

## Dependencies

### Python Packages
- `pyyaml>=6.0.0` - YAML parsing
- `pytest>=7.0.0` - Test framework

### Internal Dependencies
- None (this is a foundation module)

---

## Acceptance Criteria

- [ ] `metrics_config.py` loads YAML without errors
- [ ] MT-01: All metric IDs defined with valid thresholds
- [ ] MT-02: Profile switching modifies thresholds correctly
- [ ] `--metrics-profile` CLI flag works in pytest
- [ ] Environment variable overrides work
- [ ] Category enable/disable works
- [ ] Validation script passes on default config
- [ ] Tests run in < 1 second

---

## Notes

- Thresholds should start conservative and tighten over time
- Keep `development` profile relaxed to avoid blocking iteration
- `production` profile should match acceptance criteria from task cards
- `quick` profile enables fast feedback during development
- Environment overrides are useful for CI matrix testing

---

## Cross-Task Integration

This task integrates with the other Wave 0.5 tasks:

### Integration with VM-W0.5-2 (Domain Fixtures)

Domain fixtures can reference this metrics config for domain-specific thresholds:

```python
# Domain fixtures can override metrics per domain
from tests.validation.config.metrics_config import get_metrics_config

class DomainTestFixture:
    def get_domain_threshold(self, metric_id: str) -> float:
        """Get threshold, with optional domain override."""
        base = get_metrics_config().get_threshold(metric_id)
        domain_override = self.baselines.get(metric_id)
        return domain_override if domain_override is not None else base
```

### Integration with VM-W0.5-3 (Model Abstraction)

Model-specific metrics can be added for per-model thresholds:

```yaml
# Model-specific latency thresholds
metrics:
  - id: MC-03-GEMINI
    name: Gemini Latency Baseline
    category: benchmark
    threshold: 2.0
    unit: seconds
    
  - id: MC-03-GPT4
    name: GPT-4 Latency Baseline
    category: benchmark
    threshold: 5.0
    unit: seconds
```

### Combined Validation Context Fixture

```python
# tests/conftest.py - Combined fixture for all Wave 0.5 features
@pytest.fixture
def validation_context(metrics_config, domain_fixture, request):
    """Combined validation context with all modularization features."""
    from literature_review.config.model_config import get_model_config
    
    model_name = request.config.getoption("--model", default=None)
    
    return {
        "metrics": metrics_config,
        "domain": domain_fixture,
        "model": get_model_config() if model_name else None,
        "profile": metrics_config.active_profile,
    }
```
