# Task Card: Test Infrastructure Setup

**Task ID:** VM-W0-1  
**Wave:** 0 (Infrastructure Foundation)  
**Priority:** CRITICAL  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** None  
**Blocks:** All VM-W1-*, VM-W2-*, VM-W2.5-*, VM-W3-*, VM-W4-*, VM-W5-*

---

## Objective

Establish the foundational test infrastructure for the validation matrix and benchmarking framework, including directory structure, base classes, utility functions, and pytest configuration.

## Background

The current test infrastructure has:
- Basic pytest markers (unit, component, integration, e2e, performance)
- Test data generator in `tests/fixtures/test_data_generator.py`
- Limited performance tests (only 2 files in `tests/performance/`)

This task establishes:
1. Dedicated validation test directory with proper organization
2. Benchmark test infrastructure with timing utilities
3. Base classes for consistent test patterns
4. Hardware/environment profiling for reproducibility

## Success Criteria

- [ ] `tests/validation/` directory created with subdirectories
- [ ] `tests/benchmarks/` directory created with proper structure
- [ ] `ValidationTestCase` base class implemented
- [ ] `BenchmarkRunner` utility class implemented
- [ ] Hardware profile capture utility created
- [ ] New pytest markers added to `pytest.ini`
- [ ] All infrastructure tests pass
- [ ] Documentation for validation test authoring

---

## Deliverables

### 1. Directory Structure

```
tests/
├── validation/
│   ├── __init__.py
│   ├── conftest.py                    # Validation-specific fixtures
│   ├── base.py                        # ValidationTestCase base class
│   ├── functional/                    # FV-* tests
│   │   ├── __init__.py
│   │   ├── test_pdf_extraction.py
│   │   ├── test_claim_identification.py
│   │   └── test_judge_decisions.py
│   ├── accuracy/                      # AV-* tests
│   │   ├── __init__.py
│   │   ├── test_accuracy_baseline.py
│   │   └── test_judge_calibration.py
│   ├── efficiency/                    # EV-* tests
│   │   ├── __init__.py
│   │   ├── test_efficiency_metrics.py
│   │   └── test_cost_tracking.py
│   └── outputs/                       # OQ-*, RA-* tests (Wave 2.5)
│       ├── __init__.py
│       ├── schemas/                   # JSON schema definitions
│       │   ├── gap_analysis_report.schema.json
│       │   ├── suggested_searches.schema.json
│       │   ├── optimized_search_plan.schema.json
│       │   ├── proof_chain.schema.json
│       │   ├── sufficiency_matrix.schema.json
│       │   ├── triangulation.schema.json
│       │   └── evidence_decay.schema.json
│       ├── test_output_schemas.py
│       ├── test_recommendation_quality.py
│       └── test_evidence_outputs.py
├── benchmarks/
│   ├── __init__.py
│   ├── conftest.py                    # Benchmark-specific fixtures
│   ├── runner.py                      # BenchmarkRunner class
│   ├── profiler.py                    # Hardware profiler
│   ├── component/                     # BM-* tests
│   │   ├── __init__.py
│   │   ├── test_journal_reviewer_benchmark.py
│   │   ├── test_judge_benchmark.py
│   │   ├── test_dra_benchmark.py
│   │   └── test_orchestrator_benchmark.py
│   └── quality/                       # QB-* tests
│       ├── __init__.py
│       └── test_quality_benchmarks.py
└── golden_dataset/
    ├── __init__.py
    ├── schema.py                      # Golden dataset schemas
    ├── loader.py                      # Dataset loading utilities
    └── data/                          # Actual golden dataset files
        └── .gitkeep
```

### 2. ValidationTestCase Base Class

**File:** `tests/validation/base.py`

```python
"""
Validation Test Base Classes

Provides base classes and utilities for validation matrix tests.
"""

import pytest
import time
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of a validation test."""
    test_id: str                          # e.g., "FV-01", "AV-03"
    test_name: str
    passed: bool
    actual_value: Any
    expected_value: Any
    threshold: Optional[float] = None
    margin: Optional[float] = None        # How close to threshold
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def margin_percentage(self) -> Optional[float]:
        """Calculate margin as percentage of threshold."""
        if self.threshold and isinstance(self.actual_value, (int, float)):
            return ((self.actual_value - self.threshold) / self.threshold) * 100
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "passed": self.passed,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "threshold": self.threshold,
            "margin": self.margin,
            "margin_percentage": self.margin_percentage,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class ValidationTestCase(ABC):
    """
    Base class for validation matrix tests.
    
    Provides consistent structure for:
    - Test identification (FV-*, AV-*, EV-*)
    - Result tracking and reporting
    - Threshold validation
    - Execution timing
    """
    
    # Override in subclasses
    TEST_CATEGORY = "FV"  # FV, AV, EV, QB, BM, E2E
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.start_time: Optional[float] = None
    
    def setup_method(self, method):
        """Called before each test method."""
        self.start_time = time.perf_counter()
    
    def teardown_method(self, method):
        """Called after each test method."""
        pass
    
    def get_execution_time_ms(self) -> float:
        """Get execution time since setup."""
        if self.start_time:
            return (time.perf_counter() - self.start_time) * 1000
        return 0.0
    
    def validate_threshold(
        self,
        test_id: str,
        test_name: str,
        actual: float,
        threshold: float,
        comparison: str = "gte",  # gte, lte, eq
        metadata: Optional[Dict] = None
    ) -> ValidationResult:
        """
        Validate a value against a threshold.
        
        Args:
            test_id: Validation matrix ID (e.g., "FV-01")
            test_name: Human-readable test name
            actual: Actual measured value
            threshold: Expected threshold
            comparison: "gte" (>=), "lte" (<=), "eq" (==)
            metadata: Additional test metadata
        
        Returns:
            ValidationResult with pass/fail status
        """
        if comparison == "gte":
            passed = actual >= threshold
        elif comparison == "lte":
            passed = actual <= threshold
        else:  # eq
            passed = abs(actual - threshold) < 0.001
        
        result = ValidationResult(
            test_id=test_id,
            test_name=test_name,
            passed=passed,
            actual_value=actual,
            expected_value=f"{comparison} {threshold}",
            threshold=threshold,
            margin=actual - threshold,
            execution_time_ms=self.get_execution_time_ms(),
            metadata=metadata or {}
        )
        
        self.results.append(result)
        return result
    
    def validate_percentage(
        self,
        test_id: str,
        test_name: str,
        numerator: int,
        denominator: int,
        threshold_percent: float,
        comparison: str = "gte",
        metadata: Optional[Dict] = None
    ) -> ValidationResult:
        """Validate a percentage against threshold."""
        if denominator == 0:
            actual = 0.0
        else:
            actual = (numerator / denominator) * 100
        
        return self.validate_threshold(
            test_id=test_id,
            test_name=test_name,
            actual=actual,
            threshold=threshold_percent,
            comparison=comparison,
            metadata={
                **(metadata or {}),
                "numerator": numerator,
                "denominator": denominator
            }
        )
    
    def save_results(self, output_dir: str = "validation_results"):
        """Save validation results to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        
        results_file = os.path.join(
            output_dir,
            f"{self.TEST_CATEGORY}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(results_file, 'w') as f:
            json.dump(
                {
                    "category": self.TEST_CATEGORY,
                    "timestamp": datetime.now().isoformat(),
                    "total_tests": len(self.results),
                    "passed": sum(1 for r in self.results if r.passed),
                    "failed": sum(1 for r in self.results if not r.passed),
                    "results": [r.to_dict() for r in self.results]
                },
                f,
                indent=2
            )
        
        return results_file


class AccuracyValidationTestCase(ValidationTestCase):
    """Base class for accuracy validation tests (AV-*)."""
    TEST_CATEGORY = "AV"
    
    def calculate_precision(
        self,
        true_positives: int,
        false_positives: int
    ) -> float:
        """Calculate precision: TP / (TP + FP)."""
        total = true_positives + false_positives
        return (true_positives / total) * 100 if total > 0 else 0.0
    
    def calculate_recall(
        self,
        true_positives: int,
        false_negatives: int
    ) -> float:
        """Calculate recall: TP / (TP + FN)."""
        total = true_positives + false_negatives
        return (true_positives / total) * 100 if total > 0 else 0.0
    
    def calculate_f1(self, precision: float, recall: float) -> float:
        """Calculate F1 score."""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    def calculate_brier_score(
        self,
        predictions: List[float],
        outcomes: List[int]
    ) -> float:
        """
        Calculate Brier score for calibration.
        
        Lower is better. Perfect calibration = 0.
        """
        if len(predictions) != len(outcomes):
            raise ValueError("Predictions and outcomes must have same length")
        
        n = len(predictions)
        if n == 0:
            return 0.0
        
        return sum((p - o) ** 2 for p, o in zip(predictions, outcomes)) / n


class EfficiencyValidationTestCase(ValidationTestCase):
    """Base class for efficiency validation tests (EV-*)."""
    TEST_CATEGORY = "EV"
    
    def measure_execution_time(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """
        Measure execution time of a function.
        
        Returns:
            Tuple of (result, execution_time_seconds)
        """
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return result, elapsed
    
    def calculate_speedup(
        self,
        baseline_time: float,
        optimized_time: float
    ) -> float:
        """Calculate speedup percentage."""
        if baseline_time == 0:
            return 0.0
        return ((baseline_time - optimized_time) / baseline_time) * 100
```

### 3. BenchmarkRunner Utility

**File:** `tests/benchmarks/runner.py`

```python
"""
Benchmark Runner Utility

Provides utilities for running and recording benchmarks with
statistical analysis and hardware profiling.
"""

import time
import statistics
import json
import os
import platform
import psutil
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    benchmark_id: str                     # e.g., "BM-01"
    benchmark_name: str
    iterations: int
    mean_time_ms: float
    median_time_ms: float
    std_dev_ms: float
    min_time_ms: float
    max_time_ms: float
    passed: bool
    threshold_ms: Optional[float] = None
    throughput: Optional[float] = None    # e.g., papers/second
    throughput_unit: Optional[str] = None
    hardware_profile: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "benchmark_id": self.benchmark_id,
            "benchmark_name": self.benchmark_name,
            "iterations": self.iterations,
            "timing": {
                "mean_ms": self.mean_time_ms,
                "median_ms": self.median_time_ms,
                "std_dev_ms": self.std_dev_ms,
                "min_ms": self.min_time_ms,
                "max_ms": self.max_time_ms
            },
            "threshold_ms": self.threshold_ms,
            "passed": self.passed,
            "throughput": self.throughput,
            "throughput_unit": self.throughput_unit,
            "hardware_profile": self.hardware_profile,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class HardwareProfiler:
    """Capture hardware profile for benchmark reproducibility."""
    
    @staticmethod
    def capture() -> Dict[str, Any]:
        """Capture current hardware profile."""
        return {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            },
            "cpu": {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "frequency_mhz": getattr(psutil.cpu_freq(), 'current', None) if psutil.cpu_freq() else None,
                "usage_percent": psutil.cpu_percent(interval=0.1)
            },
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "used_percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
            }
        }


class BenchmarkRunner:
    """
    Run benchmarks with statistical analysis.
    
    Example:
        runner = BenchmarkRunner()
        result = runner.run(
            benchmark_id="BM-01",
            benchmark_name="Single paper analysis",
            func=analyze_paper,
            args=(paper_path,),
            iterations=5,
            warmup=1,
            threshold_ms=45000
        )
    """
    
    def __init__(self, capture_hardware: bool = True):
        self.capture_hardware = capture_hardware
        self.results: List[BenchmarkResult] = []
    
    def run(
        self,
        benchmark_id: str,
        benchmark_name: str,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        iterations: int = 5,
        warmup: int = 1,
        threshold_ms: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> BenchmarkResult:
        """
        Run a benchmark with multiple iterations.
        
        Args:
            benchmark_id: Benchmark matrix ID (e.g., "BM-01")
            benchmark_name: Human-readable name
            func: Function to benchmark
            args: Positional arguments for func
            kwargs: Keyword arguments for func
            iterations: Number of timed iterations
            warmup: Number of warmup iterations (not timed)
            threshold_ms: Optional pass/fail threshold in milliseconds
            metadata: Additional metadata
        
        Returns:
            BenchmarkResult with timing statistics
        """
        kwargs = kwargs or {}
        
        # Warmup runs
        for _ in range(warmup):
            func(*args, **kwargs)
        
        # Timed runs
        times_ms: List[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times_ms.append(elapsed)
        
        # Calculate statistics
        mean_time = statistics.mean(times_ms)
        median_time = statistics.median(times_ms)
        std_dev = statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0
        min_time = min(times_ms)
        max_time = max(times_ms)
        
        # Determine pass/fail
        passed = threshold_ms is None or mean_time <= threshold_ms
        
        # Capture hardware profile
        hardware = HardwareProfiler.capture() if self.capture_hardware else {}
        
        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            benchmark_name=benchmark_name,
            iterations=iterations,
            mean_time_ms=round(mean_time, 2),
            median_time_ms=round(median_time, 2),
            std_dev_ms=round(std_dev, 2),
            min_time_ms=round(min_time, 2),
            max_time_ms=round(max_time, 2),
            passed=passed,
            threshold_ms=threshold_ms,
            hardware_profile=hardware,
            metadata=metadata or {}
        )
        
        self.results.append(result)
        return result
    
    def run_throughput(
        self,
        benchmark_id: str,
        benchmark_name: str,
        func: Callable,
        items_count: int,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        iterations: int = 3,
        warmup: int = 1,
        threshold_per_second: Optional[float] = None,
        unit: str = "items"
    ) -> BenchmarkResult:
        """
        Run a throughput benchmark.
        
        Args:
            items_count: Number of items processed per iteration
            threshold_per_second: Minimum items/second for pass
            unit: Unit name for throughput (e.g., "papers", "claims")
        """
        result = self.run(
            benchmark_id=benchmark_id,
            benchmark_name=benchmark_name,
            func=func,
            args=args,
            kwargs=kwargs,
            iterations=iterations,
            warmup=warmup,
            metadata={"items_count": items_count}
        )
        
        # Calculate throughput
        seconds_per_iteration = result.mean_time_ms / 1000
        if seconds_per_iteration > 0:
            throughput = items_count / seconds_per_iteration
        else:
            throughput = 0.0
        
        result.throughput = round(throughput, 2)
        result.throughput_unit = f"{unit}/second"
        
        # Update pass/fail based on throughput threshold
        if threshold_per_second is not None:
            result.passed = throughput >= threshold_per_second
            result.threshold_ms = None  # Clear time threshold
            result.metadata["threshold_per_second"] = threshold_per_second
        
        return result
    
    def save_results(self, output_dir: str = "benchmark_results"):
        """Save all benchmark results to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        
        results_file = os.path.join(
            output_dir,
            f"benchmarks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(results_file, 'w') as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "total_benchmarks": len(self.results),
                    "passed": sum(1 for r in self.results if r.passed),
                    "failed": sum(1 for r in self.results if not r.passed),
                    "results": [r.to_dict() for r in self.results]
                },
                f,
                indent=2
            )
        
        return results_file
    
    def compare_with_baseline(
        self,
        baseline_file: str,
        regression_threshold_percent: float = 10.0
    ) -> Dict[str, Any]:
        """
        Compare current results with baseline for regression detection.
        
        Args:
            baseline_file: Path to baseline results JSON
            regression_threshold_percent: Percentage increase that triggers regression
        
        Returns:
            Comparison report with regressions flagged
        """
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
        
        baseline_by_id = {r["benchmark_id"]: r for r in baseline.get("results", [])}
        
        comparisons = []
        regressions = []
        
        for result in self.results:
            baseline_result = baseline_by_id.get(result.benchmark_id)
            
            if baseline_result:
                baseline_mean = baseline_result["timing"]["mean_ms"]
                current_mean = result.mean_time_ms
                
                change_percent = ((current_mean - baseline_mean) / baseline_mean) * 100
                is_regression = change_percent > regression_threshold_percent
                
                comparison = {
                    "benchmark_id": result.benchmark_id,
                    "baseline_mean_ms": baseline_mean,
                    "current_mean_ms": current_mean,
                    "change_percent": round(change_percent, 2),
                    "is_regression": is_regression
                }
                
                comparisons.append(comparison)
                if is_regression:
                    regressions.append(comparison)
        
        return {
            "comparisons": comparisons,
            "regressions": regressions,
            "has_regressions": len(regressions) > 0
        }
```

### 4. pytest Configuration Updates

**Add to `pytest.ini`:**

```ini
# Validation matrix markers (add to existing markers section)
markers =
    # ... existing markers ...
    validation: Validation matrix tests (FV-*, AV-*, EV-*)
    benchmark: Benchmark tests (BM-*, may take longer)
    golden: Tests requiring golden dataset
    accuracy: Accuracy validation tests (AV-*)
    efficiency: Efficiency validation tests (EV-*)
    quality: Quality benchmark tests (QB-*)
    functional: Functional validation tests (FV-*)
    requires_golden_dataset: Tests that require golden dataset to be present
    slow_benchmark: Benchmarks that take >60 seconds
    # Wave 2.5 markers (output quality validation)
    output_quality: Tests for output file validation (OQ-*)
    recommendation: Tests for recommendation accuracy (RA-*)
    visualization: Tests for HTML visualization integrity (VI-*)
    incremental: Tests for incremental mode functionality
    prefilter: Tests for pre-filter/relevance scoring
    calibration: Tests for Judge score calibration
    cost: Tests for API cost tracking
```

### 5. Validation Fixtures

**File:** `tests/validation/conftest.py`

```python
"""
Validation Test Fixtures

Shared fixtures for validation matrix tests.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path


@pytest.fixture
def validation_workspace(tmp_path):
    """Create a temporary workspace for validation tests."""
    workspace = {
        "root": tmp_path,
        "papers_dir": tmp_path / "data" / "raw",
        "output_dir": tmp_path / "output",
        "cache_dir": tmp_path / "cache",
        "version_history": tmp_path / "review_version_history.json",
        "csv_db": tmp_path / "test_database.csv"
    }
    
    # Create directories
    workspace["papers_dir"].mkdir(parents=True)
    workspace["output_dir"].mkdir(parents=True)
    workspace["cache_dir"].mkdir(parents=True)
    
    # Initialize empty files
    with open(workspace["version_history"], 'w') as f:
        json.dump({}, f)
    
    with open(workspace["csv_db"], 'w') as f:
        f.write("filename,title,authors\n")
    
    return workspace


@pytest.fixture
def sample_claims():
    """Sample claims for validation testing."""
    return [
        {
            "claim_id": "test_claim_001",
            "sub_requirement": "Sub-1.1.1",
            "pillar": "Pillar 1: Biological Stimulus-Response",
            "extracted_claim_text": "The neural network demonstrates spike-timing dependent plasticity.",
            "evidence": "Figure 3 shows STDP curves with timing windows of ±20ms.",
            "evidence_quality": {
                "strength_score": 4,
                "rigor_score": 4,
                "relevance_score": 4,
                "directness": 3,
                "reproducibility_score": 4,
                "composite_score": 3.95
            },
            "status": "pending_judge_review"
        },
        {
            "claim_id": "test_claim_002",
            "sub_requirement": "Sub-1.2.1",
            "pillar": "Pillar 1: Biological Stimulus-Response",
            "extracted_claim_text": "Energy consumption is reduced by 10x compared to GPUs.",
            "evidence": "Table 2 shows power measurements across different workloads.",
            "evidence_quality": {
                "strength_score": 3,
                "rigor_score": 3,
                "relevance_score": 3,
                "directness": 2,
                "reproducibility_score": 3,
                "composite_score": 2.85
            },
            "status": "pending_judge_review"
        }
    ]


@pytest.fixture
def mock_pillar_definitions():
    """Minimal pillar definitions for testing."""
    return {
        "Pillar 1: Biological Stimulus-Response": {
            "description": "Test pillar for validation",
            "requirements": {
                "REQ-B1.1: Sensory Transduction & Encoding": [
                    "Sub-1.1.1: Conclusive model of how raw sensory data is transduced",
                    "Sub-1.1.2: Proven mechanism for sensory feature extraction"
                ],
                "REQ-B1.2: Neural Pathways & Integration": [
                    "Sub-1.2.1: Detailed mapping of thalamic relay pathways"
                ]
            }
        }
    }


@pytest.fixture
def golden_dataset_dir(tmp_path):
    """Create golden dataset directory structure."""
    golden_dir = tmp_path / "golden_dataset"
    golden_dir.mkdir()
    
    (golden_dir / "claims").mkdir()
    (golden_dir / "verdicts").mkdir()
    (golden_dir / "gaps").mkdir()
    
    return golden_dir
```

---

## Implementation Steps

### Step 1: Create Directory Structure (1 hour)
```bash
mkdir -p tests/validation/{functional,accuracy,efficiency}
mkdir -p tests/benchmarks/{component,quality}
mkdir -p tests/golden_dataset/data
touch tests/validation/__init__.py
touch tests/benchmarks/__init__.py
touch tests/golden_dataset/__init__.py
```

### Step 2: Implement Base Classes (3 hours)
1. Create `tests/validation/base.py` with `ValidationTestCase`
2. Create `tests/benchmarks/runner.py` with `BenchmarkRunner`
3. Create `tests/benchmarks/profiler.py` with `HardwareProfiler`

### Step 3: Create Fixtures (2 hours)
1. Create `tests/validation/conftest.py`
2. Create `tests/benchmarks/conftest.py`
3. Update `tests/conftest.py` with shared fixtures

### Step 4: Update pytest Configuration (30 minutes)
1. Add new markers to `pytest.ini`
2. Configure coverage for new directories

### Step 5: Create Documentation (1.5 hours)
1. Create `tests/validation/README.md`
2. Create `tests/benchmarks/README.md`
3. Add validation test authoring guide

---

## Testing

```python
# tests/test_infrastructure.py

import pytest
from tests.validation.base import (
    ValidationTestCase,
    AccuracyValidationTestCase,
    ValidationResult
)
from tests.benchmarks.runner import BenchmarkRunner, HardwareProfiler


class TestValidationInfrastructure:
    """Test the validation infrastructure itself."""
    
    @pytest.mark.unit
    def test_validation_result_creation(self):
        """Test ValidationResult dataclass."""
        result = ValidationResult(
            test_id="FV-01",
            test_name="Test",
            passed=True,
            actual_value=95.0,
            expected_value=">= 90.0",
            threshold=90.0
        )
        
        assert result.passed
        assert result.margin == 5.0
        assert result.margin_percentage == pytest.approx(5.56, rel=0.1)
    
    @pytest.mark.unit
    def test_threshold_validation_gte(self):
        """Test greater-than-or-equal validation."""
        class TestCase(ValidationTestCase):
            TEST_CATEGORY = "FV"
        
        tc = TestCase()
        tc.start_time = 0  # Mock
        
        result = tc.validate_threshold(
            test_id="FV-01",
            test_name="PDF Extraction",
            actual=92.0,
            threshold=90.0,
            comparison="gte"
        )
        
        assert result.passed
    
    @pytest.mark.unit
    def test_benchmark_runner(self):
        """Test BenchmarkRunner basic functionality."""
        runner = BenchmarkRunner(capture_hardware=False)
        
        def dummy_func():
            return sum(range(1000))
        
        result = runner.run(
            benchmark_id="BM-TEST",
            benchmark_name="Test Benchmark",
            func=dummy_func,
            iterations=3,
            warmup=1
        )
        
        assert result.iterations == 3
        assert result.mean_time_ms > 0
        assert result.passed  # No threshold set
    
    @pytest.mark.unit
    def test_hardware_profiler(self):
        """Test hardware profile capture."""
        profile = HardwareProfiler.capture()
        
        assert "platform" in profile
        assert "cpu" in profile
        assert "memory" in profile
        assert profile["cpu"]["logical_cores"] > 0
```

---

## Acceptance Criteria Checklist

- [ ] `tests/validation/` directory exists with proper structure
- [ ] `tests/benchmarks/` directory exists with proper structure
- [ ] `ValidationTestCase` base class works correctly
- [ ] `AccuracyValidationTestCase` provides precision/recall helpers
- [ ] `EfficiencyValidationTestCase` provides timing utilities
- [ ] `BenchmarkRunner` runs benchmarks with statistics
- [ ] `HardwareProfiler` captures hardware profile
- [ ] New pytest markers are recognized
- [ ] Infrastructure tests pass
- [ ] Documentation is complete

---

## Related Tasks

- **Next:** VM-W0-2 (Golden Dataset Specification)
- **Enables:** All Wave 1, 2, 3, 4 tasks

---

## Notes

- Hardware profiler uses `psutil` - add to requirements-dev.txt if not present
- BenchmarkRunner saves results to JSON for CI/CD integration
- ValidationTestCase provides consistent result structure for reporting
