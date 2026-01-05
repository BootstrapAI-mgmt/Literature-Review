# Benchmark Tests

This directory contains benchmarking infrastructure and tests for the Literature Review system.

## Directory Structure

```
benchmarks/
├── __init__.py
├── conftest.py          # Benchmark-specific fixtures
├── runner.py            # BenchmarkRunner class
├── profiler.py          # Hardware profiler utilities
├── component/           # BM-* tests (Component Benchmarks)
│   ├── __init__.py
│   ├── test_journal_reviewer_benchmark.py
│   ├── test_judge_benchmark.py
│   ├── test_dra_benchmark.py
│   └── test_orchestrator_benchmark.py
└── quality/             # QB-* tests (Quality Benchmarks)
    ├── __init__.py
    └── test_quality_benchmarks.py
```

## BenchmarkRunner

The `BenchmarkRunner` class provides utilities for running benchmarks with statistical analysis:

### Basic Usage

```python
from tests.benchmarks.runner import BenchmarkRunner

runner = BenchmarkRunner()

# Run a simple benchmark
result = runner.run(
    benchmark_id="BM-01",
    benchmark_name="Single paper analysis",
    func=analyze_paper,
    args=(paper_path,),
    iterations=5,
    warmup=1,
    threshold_ms=45000
)

print(f"Mean time: {result.mean_time_ms}ms")
print(f"Passed: {result.passed}")
```

### Throughput Benchmarks

```python
result = runner.run_throughput(
    benchmark_id="BM-02",
    benchmark_name="Batch processing",
    func=process_batch,
    args=(papers,),
    items_count=10,
    threshold_per_second=0.5,
    unit="papers"
)

print(f"Throughput: {result.throughput} {result.throughput_unit}")
```

### Saving Results

```python
# Save all results to JSON
results_file = runner.save_results(output_dir="benchmark_results")
```

### Regression Detection

```python
# Compare with baseline
comparison = runner.compare_with_baseline(
    baseline_file="baselines/v1.0.0.json",
    regression_threshold_percent=10.0
)

if comparison["has_regressions"]:
    print("Performance regression detected!")
    for reg in comparison["regressions"]:
        print(f"  {reg['benchmark_id']}: {reg['change_percent']}% slower")
```

## HardwareProfiler

Captures hardware information for reproducibility:

```python
from tests.benchmarks.runner import HardwareProfiler

profile = HardwareProfiler.capture()

print(f"CPU cores: {profile['cpu']['logical_cores']}")
print(f"Memory: {profile['memory']['total_gb']} GB")
print(f"Python: {profile['platform']['python_version']}")
```

## BenchmarkResult

Each benchmark returns a `BenchmarkResult` with:

- `benchmark_id`: Test ID (e.g., "BM-01")
- `benchmark_name`: Human-readable name
- `iterations`: Number of timed runs
- `mean_time_ms`: Average execution time
- `median_time_ms`: Median execution time
- `std_dev_ms`: Standard deviation
- `min_time_ms`: Minimum time
- `max_time_ms`: Maximum time
- `passed`: Whether threshold was met
- `threshold_ms`: Target threshold
- `throughput`: Items per second (for throughput benchmarks)
- `hardware_profile`: System information

## Test Markers

```python
@pytest.mark.benchmark
def test_component_speed():
    ...

@pytest.mark.benchmark
@pytest.mark.slow_benchmark  # For benchmarks taking >60 seconds
def test_full_pipeline():
    ...
```

## Fixtures

Available fixtures in `conftest.py`:

- `benchmark_runner`: BenchmarkRunner without hardware profiling
- `benchmark_runner_with_hardware`: BenchmarkRunner with hardware profiling
- `hardware_profile`: Current hardware profile
- `benchmark_workspace`: Temporary workspace for results
- `sample_benchmark_baseline`: Sample baseline for comparison testing

## Running Benchmarks

```bash
# Run all benchmarks
pytest tests/benchmarks/ -m benchmark

# Run component benchmarks
pytest tests/benchmarks/component/ -m benchmark

# Skip slow benchmarks
pytest tests/benchmarks/ -m "benchmark and not slow_benchmark"

# Run with verbose timing
pytest tests/benchmarks/ -v --tb=short
```

## CI/CD Integration

Benchmark results are saved as JSON for CI/CD integration:

```json
{
    "timestamp": "2024-01-15T10:30:00",
    "total_benchmarks": 5,
    "passed": 4,
    "failed": 1,
    "results": [...]
}
```

Use the `compare_with_baseline()` method to detect regressions in CI:

```python
def test_no_regressions():
    runner = BenchmarkRunner()
    # Run benchmarks...
    
    comparison = runner.compare_with_baseline(
        "baselines/main.json",
        regression_threshold_percent=10.0
    )
    
    assert not comparison["has_regressions"], \
        f"Regressions: {comparison['regressions']}"
```
