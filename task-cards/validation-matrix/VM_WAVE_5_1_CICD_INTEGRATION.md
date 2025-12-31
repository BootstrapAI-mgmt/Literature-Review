# Task Card: CI/CD Integration

**Task ID:** VM-W5-1  
**Wave:** 5 (Integration & Reporting)  
**Priority:** MEDIUM  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W4-1, VM-W4-2  
**Blocks:** None (Final wave)  
**Validation IDs:** N/A (Infrastructure)

---

## Objective

Integrate the validation matrix and benchmark suite into the CI/CD pipeline, enabling automated validation gates, benchmark regression detection, and PR validation checks.

## Background

CI/CD integration ensures:
- Every PR is validated against the full test suite
- Performance regressions are caught before merge
- Validation gates prevent broken code from reaching main
- Benchmark history is preserved for trend analysis
- Multiple environments can be tested in matrix builds

## Success Criteria

- [ ] GitHub Actions workflow for validation matrix
- [ ] Benchmark regression detection with configurable thresholds
- [ ] PR validation checks with pass/fail status
- [ ] Matrix builds for multiple Python versions
- [ ] Artifact preservation for benchmark history
- [ ] Caching for test dependencies

---

## Deliverables

### 1. GitHub Actions Workflow

**File:** `.github/workflows/validation-matrix.yml`

```yaml
name: Validation Matrix & Benchmarks

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:
    inputs:
      run_benchmarks:
        description: 'Run full benchmark suite'
        required: false
        default: 'false'
        type: boolean
      benchmark_size:
        description: 'Benchmark dataset size'
        required: false
        default: 'small'
        type: choice
        options:
          - small
          - medium
          - large

env:
  PYTHON_VERSION_PRIMARY: '3.11'
  CACHE_VERSION: v1

jobs:
  # ===========================================================================
  # Job 1: Validation Tests (Fast)
  # ===========================================================================
  validation-tests:
    name: Validation Tests
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.10', '3.11', '3.12']
        test-category: ['functional', 'accuracy', 'efficiency', 'output_quality']
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Cache pip dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ env.CACHE_VERSION }}-${{ hashFiles('requirements*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-${{ env.CACHE_VERSION }}-
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run validation tests - ${{ matrix.test-category }}
        run: |
          pytest tests/validation/ \
            -v \
            -m "${{ matrix.test-category }}" \
            --junitxml=results/validation-${{ matrix.test-category }}-py${{ matrix.python-version }}.xml \
            --tb=short
        continue-on-error: false
      
      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: validation-results-${{ matrix.test-category }}-py${{ matrix.python-version }}
          path: results/
          retention-days: 30

  # ===========================================================================
  # Job 2: Benchmark Tests (Slower, Primary Python Only)
  # ===========================================================================
  benchmark-tests:
    name: Benchmark Tests
    runs-on: ubuntu-latest
    needs: validation-tests
    if: |
      github.event_name == 'push' ||
      github.event.inputs.run_benchmarks == 'true' ||
      contains(github.event.pull_request.labels.*.name, 'run-benchmarks')
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION_PRIMARY }}
      
      - name: Cache pip dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ env.CACHE_VERSION }}-${{ hashFiles('requirements*.txt') }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run component benchmarks
        run: |
          pytest tests/benchmarks/component/ \
            -v \
            -m "benchmark and not slow_benchmark" \
            --benchmark-json=results/benchmarks-component.json \
            --junitxml=results/benchmarks-component.xml
      
      - name: Run quality benchmarks
        run: |
          pytest tests/benchmarks/quality/ \
            -v \
            -m "quality" \
            --benchmark-json=results/benchmarks-quality.json \
            --junitxml=results/benchmarks-quality.xml
      
      - name: Upload benchmark results
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-results-${{ github.sha }}
          path: results/
          retention-days: 90
      
      - name: Download baseline benchmarks
        uses: dawidd6/action-download-artifact@v3
        with:
          workflow: validation-matrix.yml
          branch: main
          name: benchmark-results-baseline
          path: baseline/
        continue-on-error: true
      
      - name: Check for regressions
        run: |
          python scripts/ci/check_benchmark_regression.py \
            --current results/benchmarks-component.json \
            --baseline baseline/benchmarks-component.json \
            --threshold 0.15
        continue-on-error: false

  # ===========================================================================
  # Job 3: E2E Tests (Long Running)
  # ===========================================================================
  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: validation-tests
    if: |
      github.event_name == 'push' && github.ref == 'refs/heads/main' ||
      github.event.inputs.run_benchmarks == 'true'
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION_PRIMARY }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run E2E tests (small)
        run: |
          pytest tests/e2e/ \
            -v \
            -m "e2e and not slow" \
            -k "small or incremental or recovery" \
            --junitxml=results/e2e-small.xml
      
      - name: Upload E2E results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: e2e-results-${{ github.sha }}
          path: results/

  # ===========================================================================
  # Job 4: Visualization Tests
  # ===========================================================================
  visualization-tests:
    name: Visualization Tests
    runs-on: ubuntu-latest
    needs: validation-tests
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION_PRIMARY }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run visualization tests
        run: |
          pytest tests/validation/outputs/ \
            -v \
            -m "visualization" \
            --junitxml=results/visualization.xml
      
      - name: Upload results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: visualization-results
          path: results/

  # ===========================================================================
  # Job 5: Validation Gate (Required for PR)
  # ===========================================================================
  validation-gate:
    name: Validation Gate
    runs-on: ubuntu-latest
    needs: [validation-tests, visualization-tests]
    if: always()
    
    steps:
      - name: Check validation results
        run: |
          if [[ "${{ needs.validation-tests.result }}" != "success" ]]; then
            echo "❌ Validation tests failed"
            exit 1
          fi
          if [[ "${{ needs.visualization-tests.result }}" != "success" ]]; then
            echo "❌ Visualization tests failed"
            exit 1
          fi
          echo "✅ All validation gates passed"

  # ===========================================================================
  # Job 6: Update Baseline (Main Branch Only)
  # ===========================================================================
  update-baseline:
    name: Update Baseline
    runs-on: ubuntu-latest
    needs: [benchmark-tests, e2e-tests]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
      - name: Download current benchmarks
        uses: actions/download-artifact@v4
        with:
          name: benchmark-results-${{ github.sha }}
          path: results/
      
      - name: Upload as new baseline
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-results-baseline
          path: results/
          retention-days: 365
```

### 2. Benchmark Regression Checker

**File:** `scripts/ci/check_benchmark_regression.py`

```python
#!/usr/bin/env python3
"""
Benchmark Regression Checker

Compares current benchmark results against baseline to detect regressions.
Used in CI/CD pipeline to prevent performance degradation.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RegressionResult:
    """Result of regression check for a single benchmark."""
    benchmark_id: str
    name: str
    baseline_value: float
    current_value: float
    change_percent: float
    threshold_percent: float
    is_regression: bool
    is_improvement: bool


def load_benchmark_results(path: Path) -> Dict:
    """Load benchmark results from JSON file."""
    if not path.exists():
        return {}
    
    with open(path) as f:
        return json.load(f)


def extract_benchmarks(results: Dict) -> Dict[str, Dict]:
    """Extract benchmark values from results structure."""
    benchmarks = {}
    
    # Handle different result formats
    if "benchmarks" in results:
        for bm in results["benchmarks"]:
            bm_id = bm.get("benchmark_id") or bm.get("name", "unknown")
            benchmarks[bm_id] = {
                "name": bm.get("name", bm_id),
                "value": bm.get("value", bm.get("stats", {}).get("mean", 0)),
                "unit": bm.get("unit", ""),
                "threshold": bm.get("threshold", None)
            }
    elif "results" in results:
        for bm_id, bm in results["results"].items():
            benchmarks[bm_id] = bm
    else:
        # Assume flat structure
        benchmarks = results
    
    return benchmarks


def check_regression(
    baseline: Dict,
    current: Dict,
    threshold_percent: float = 15.0
) -> Tuple[List[RegressionResult], bool]:
    """
    Check for regressions between baseline and current results.
    
    Args:
        baseline: Baseline benchmark results
        current: Current benchmark results
        threshold_percent: Maximum allowed performance degradation (%)
    
    Returns:
        Tuple of (list of results, has_regression)
    """
    results = []
    has_regression = False
    
    baseline_benchmarks = extract_benchmarks(baseline)
    current_benchmarks = extract_benchmarks(current)
    
    for bm_id, current_bm in current_benchmarks.items():
        if bm_id not in baseline_benchmarks:
            # New benchmark, no comparison possible
            continue
        
        baseline_bm = baseline_benchmarks[bm_id]
        baseline_value = baseline_bm.get("value", 0)
        current_value = current_bm.get("value", 0)
        
        if baseline_value == 0:
            change_percent = 0
        else:
            change_percent = ((current_value - baseline_value) / baseline_value) * 100
        
        # For most benchmarks, higher value = worse (time, cost, etc.)
        # Some benchmarks are inverse (throughput, accuracy)
        unit = current_bm.get("unit", "").lower()
        inverse_metrics = ["accuracy", "throughput", "papers/sec", "claims/min", "records/sec"]
        
        is_inverse = any(m in unit for m in inverse_metrics)
        
        if is_inverse:
            is_regression = change_percent < -threshold_percent
            is_improvement = change_percent > threshold_percent
        else:
            is_regression = change_percent > threshold_percent
            is_improvement = change_percent < -threshold_percent
        
        if is_regression:
            has_regression = True
        
        results.append(RegressionResult(
            benchmark_id=bm_id,
            name=current_bm.get("name", bm_id),
            baseline_value=baseline_value,
            current_value=current_value,
            change_percent=change_percent,
            threshold_percent=threshold_percent,
            is_regression=is_regression,
            is_improvement=is_improvement
        ))
    
    return results, has_regression


def format_report(results: List[RegressionResult]) -> str:
    """Format regression check results as a report."""
    lines = [
        "=" * 70,
        "BENCHMARK REGRESSION REPORT",
        "=" * 70,
        ""
    ]
    
    regressions = [r for r in results if r.is_regression]
    improvements = [r for r in results if r.is_improvement]
    stable = [r for r in results if not r.is_regression and not r.is_improvement]
    
    if regressions:
        lines.append("❌ REGRESSIONS DETECTED:")
        lines.append("-" * 40)
        for r in regressions:
            lines.append(f"  {r.benchmark_id}: {r.name}")
            lines.append(f"    Baseline: {r.baseline_value:.4f}")
            lines.append(f"    Current:  {r.current_value:.4f}")
            lines.append(f"    Change:   {r.change_percent:+.1f}% (threshold: {r.threshold_percent:.0f}%)")
            lines.append("")
    
    if improvements:
        lines.append("✅ IMPROVEMENTS:")
        lines.append("-" * 40)
        for r in improvements:
            lines.append(f"  {r.benchmark_id}: {r.name} ({r.change_percent:+.1f}%)")
        lines.append("")
    
    if stable:
        lines.append(f"➖ STABLE: {len(stable)} benchmarks within threshold")
        lines.append("")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Check for benchmark regressions")
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to current benchmark results JSON"
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline benchmark results JSON"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=15.0,
        help="Regression threshold percentage (default: 15%%)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for regression report"
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        default=True,
        help="Exit with error code if regression detected"
    )
    
    args = parser.parse_args()
    
    # Load results
    if not args.current.exists():
        print(f"Error: Current results not found: {args.current}")
        sys.exit(1)
    
    current = load_benchmark_results(args.current)
    
    if not args.baseline.exists():
        print(f"Warning: Baseline not found: {args.baseline}")
        print("Skipping regression check (no baseline to compare)")
        sys.exit(0)
    
    baseline = load_benchmark_results(args.baseline)
    
    # Check regressions
    results, has_regression = check_regression(
        baseline, current, args.threshold
    )
    
    # Generate report
    report = format_report(results)
    print(report)
    
    if args.output:
        args.output.write_text(report)
    
    # Exit with appropriate code
    if has_regression and args.fail_on_regression:
        print("\n❌ Regression detected! Failing build.")
        sys.exit(1)
    else:
        print("\n✅ No regressions detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### 3. PR Validation Check Configuration

**File:** `.github/workflows/pr-validation.yml`

```yaml
name: PR Validation

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  quick-validation:
    name: Quick Validation
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run quick validation suite
        run: |
          pytest tests/validation/ \
            -v \
            -m "not slow and not slow_benchmark" \
            --maxfail=5 \
            --tb=short
      
      - name: Run output schema validation
        run: |
          pytest tests/validation/outputs/ \
            -v \
            -m "output_quality" \
            --maxfail=3
```

---

## Implementation Plan

### Hour 1-2: Workflow Foundation
1. Create main validation-matrix.yml workflow
2. Set up matrix builds for Python versions
3. Configure caching and dependencies

### Hour 3-4: Benchmark Integration
1. Implement benchmark job with JSON output
2. Create baseline download/upload logic
3. Implement regression checker script

### Hour 5-6: E2E & Visualization Jobs
1. Add E2E test job with conditional execution
2. Add visualization test job
3. Configure artifact retention

### Hour 7-8: Gates & Reporting
1. Implement validation gate job
2. Create PR validation workflow
3. Document workflow usage
4. Test end-to-end

---

## Testing Instructions

```bash
# Test workflow locally with act (if installed)
act -j validation-tests

# Run regression checker manually
python scripts/ci/check_benchmark_regression.py \
  --current results/benchmarks-current.json \
  --baseline results/benchmarks-baseline.json \
  --threshold 15

# Validate workflow syntax
yamllint .github/workflows/validation-matrix.yml
```

---

## Dependencies

### GitHub Actions
- `actions/checkout@v4`
- `actions/setup-python@v5`
- `actions/cache@v4`
- `actions/upload-artifact@v4`
- `actions/download-artifact@v4`
- `dawidd6/action-download-artifact@v3`

### Python Packages
- `pytest>=7.0.0`
- `pytest-benchmark>=4.0.0` (optional, for advanced benchmarking)

---

## Acceptance Criteria

- [ ] Workflow runs on push to main/develop
- [ ] Workflow runs on PRs to main/develop
- [ ] Matrix builds test Python 3.10, 3.11, 3.12
- [ ] Benchmarks run only on main or when labeled
- [ ] Regression checker catches >15% degradation
- [ ] Artifacts preserved for 30-90 days
- [ ] Validation gate blocks PR merge on failure
- [ ] Baseline updated automatically on main

---

## Notes

- E2E tests run only on main branch (long running)
- Benchmark regression threshold set to 15% by default
- Consider adding Slack notifications for failures
- Artifact retention: 30 days for tests, 90 days for benchmarks
- Baseline updated only when all tests pass
