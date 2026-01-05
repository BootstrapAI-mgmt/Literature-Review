"""
Benchmark Test Fixtures

Shared fixtures for benchmark tests.
"""

import pytest
from tests.benchmarks.runner import BenchmarkRunner, HardwareProfiler


def pytest_addoption(parser):
    """Add model comparison options."""
    try:
        parser.addoption(
            "--models",
            action="store",
            default=None,
            help="Comma-separated list of models to compare for model comparison benchmarks"
        )
    except ValueError:
        # Option already exists
        pass


@pytest.fixture
def benchmark_runner():
    """Create a BenchmarkRunner instance for testing."""
    return BenchmarkRunner(capture_hardware=False)


@pytest.fixture
def benchmark_runner_with_hardware():
    """Create a BenchmarkRunner instance with hardware profiling."""
    return BenchmarkRunner(capture_hardware=True)


@pytest.fixture
def hardware_profile():
    """Capture current hardware profile."""
    return HardwareProfiler.capture()


@pytest.fixture
def benchmark_workspace(tmp_path):
    """Create a temporary workspace for benchmark tests."""
    workspace = {
        "root": tmp_path,
        "results_dir": tmp_path / "benchmark_results",
        "baseline_dir": tmp_path / "baselines"
    }
    
    # Create directories
    workspace["results_dir"].mkdir(parents=True)
    workspace["baseline_dir"].mkdir(parents=True)
    
    return workspace


@pytest.fixture
def sample_benchmark_baseline(benchmark_workspace):
    """Create a sample baseline file for comparison testing."""
    import json
    from datetime import datetime
    
    baseline = {
        "timestamp": datetime.now().isoformat(),
        "total_benchmarks": 2,
        "passed": 2,
        "failed": 0,
        "results": [
            {
                "benchmark_id": "BM-01",
                "benchmark_name": "Test Benchmark 1",
                "iterations": 5,
                "timing": {
                    "mean_ms": 100.0,
                    "median_ms": 98.0,
                    "std_dev_ms": 5.0,
                    "min_ms": 95.0,
                    "max_ms": 110.0
                },
                "threshold_ms": 150.0,
                "passed": True,
                "hardware_profile": {},
                "metadata": {},
                "timestamp": datetime.now().isoformat()
            },
            {
                "benchmark_id": "BM-02",
                "benchmark_name": "Test Benchmark 2",
                "iterations": 5,
                "timing": {
                    "mean_ms": 200.0,
                    "median_ms": 195.0,
                    "std_dev_ms": 10.0,
                    "min_ms": 185.0,
                    "max_ms": 220.0
                },
                "threshold_ms": 250.0,
                "passed": True,
                "hardware_profile": {},
                "metadata": {},
                "timestamp": datetime.now().isoformat()
            }
        ]
    }
    
    baseline_file = benchmark_workspace["baseline_dir"] / "baseline.json"
    with open(baseline_file, 'w') as f:
        json.dump(baseline, f, indent=2)
    
    return baseline_file
