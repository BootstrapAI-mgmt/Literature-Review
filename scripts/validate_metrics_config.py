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
