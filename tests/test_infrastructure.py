"""
Test Infrastructure Tests

Tests for the validation and benchmark infrastructure itself.
"""

import pytest
import time
from tests.validation.base import (
    ValidationTestCase,
    AccuracyValidationTestCase,
    EfficiencyValidationTestCase,
    ValidationResult
)
from tests.benchmarks.runner import BenchmarkRunner, HardwareProfiler, BenchmarkResult


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
            threshold=90.0,
            margin=5.0
        )
        
        assert result.passed
        assert result.margin == 5.0
        assert result.margin_percentage == pytest.approx(5.56, rel=0.1)
    
    @pytest.mark.unit
    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization."""
        result = ValidationResult(
            test_id="FV-01",
            test_name="Test",
            passed=True,
            actual_value=95.0,
            expected_value=">= 90.0",
            threshold=90.0,
            margin=5.0
        )
        
        d = result.to_dict()
        assert d["test_id"] == "FV-01"
        assert d["passed"] is True
        assert d["actual_value"] == 95.0
    
    @pytest.mark.unit
    def test_threshold_validation_gte(self):
        """Test greater-than-or-equal validation."""
        class TestCase(ValidationTestCase):
            TEST_CATEGORY = "FV"
        
        tc = TestCase()
        tc.start_time = time.perf_counter()
        
        result = tc.validate_threshold(
            test_id="FV-01",
            test_name="PDF Extraction",
            actual=92.0,
            threshold=90.0,
            comparison="gte"
        )
        
        assert result.passed
        assert result.margin == 2.0
    
    @pytest.mark.unit
    def test_threshold_validation_lte(self):
        """Test less-than-or-equal validation."""
        class TestCase(ValidationTestCase):
            TEST_CATEGORY = "EV"
        
        tc = TestCase()
        tc.start_time = time.perf_counter()
        
        result = tc.validate_threshold(
            test_id="EV-01",
            test_name="Processing Time",
            actual=40.0,
            threshold=45.0,
            comparison="lte"
        )
        
        assert result.passed
    
    @pytest.mark.unit
    def test_threshold_validation_failure(self):
        """Test threshold validation failure."""
        class TestCase(ValidationTestCase):
            TEST_CATEGORY = "FV"
        
        tc = TestCase()
        tc.start_time = time.perf_counter()
        
        result = tc.validate_threshold(
            test_id="FV-01",
            test_name="Test",
            actual=85.0,
            threshold=90.0,
            comparison="gte"
        )
        
        assert not result.passed
        assert result.margin == -5.0
    
    @pytest.mark.unit
    def test_percentage_validation(self):
        """Test percentage validation helper."""
        class TestCase(ValidationTestCase):
            TEST_CATEGORY = "AV"
        
        tc = TestCase()
        tc.start_time = time.perf_counter()
        
        result = tc.validate_percentage(
            test_id="AV-01",
            test_name="Precision",
            numerator=85,
            denominator=100,
            threshold_percent=80.0
        )
        
        assert result.passed
        assert result.actual_value == 85.0
    
    @pytest.mark.unit
    def test_percentage_validation_zero_denominator(self):
        """Test percentage validation with zero denominator."""
        class TestCase(ValidationTestCase):
            TEST_CATEGORY = "AV"
        
        tc = TestCase()
        tc.start_time = time.perf_counter()
        
        result = tc.validate_percentage(
            test_id="AV-01",
            test_name="Precision",
            numerator=0,
            denominator=0,
            threshold_percent=80.0
        )
        
        assert not result.passed
        assert result.actual_value == 0.0


class TestAccuracyValidationTestCase:
    """Test AccuracyValidationTestCase functionality."""
    
    @pytest.mark.unit
    def test_calculate_precision(self):
        """Test precision calculation."""
        tc = AccuracyValidationTestCase()
        
        precision = tc.calculate_precision(true_positives=85, false_positives=15)
        assert precision == 85.0
    
    @pytest.mark.unit
    def test_calculate_precision_no_positives(self):
        """Test precision with no positives."""
        tc = AccuracyValidationTestCase()
        
        precision = tc.calculate_precision(true_positives=0, false_positives=0)
        assert precision == 0.0
    
    @pytest.mark.unit
    def test_calculate_recall(self):
        """Test recall calculation."""
        tc = AccuracyValidationTestCase()
        
        recall = tc.calculate_recall(true_positives=80, false_negatives=20)
        assert recall == 80.0
    
    @pytest.mark.unit
    def test_calculate_f1(self):
        """Test F1 score calculation."""
        tc = AccuracyValidationTestCase()
        
        f1 = tc.calculate_f1(precision=80.0, recall=80.0)
        assert f1 == 80.0
    
    @pytest.mark.unit
    def test_calculate_f1_zero(self):
        """Test F1 score with zero values."""
        tc = AccuracyValidationTestCase()
        
        f1 = tc.calculate_f1(precision=0.0, recall=0.0)
        assert f1 == 0.0
    
    @pytest.mark.unit
    def test_calculate_brier_score(self):
        """Test Brier score calculation."""
        tc = AccuracyValidationTestCase()
        
        # Perfect predictions
        brier = tc.calculate_brier_score(
            predictions=[1.0, 0.0, 1.0],
            outcomes=[1, 0, 1]
        )
        assert brier == 0.0
        
        # Imperfect predictions
        brier = tc.calculate_brier_score(
            predictions=[0.8, 0.2, 0.9],
            outcomes=[1, 0, 1]
        )
        assert brier == pytest.approx(0.03, rel=0.1)
    
    @pytest.mark.unit
    def test_calculate_brier_score_mismatch(self):
        """Test Brier score with mismatched lengths."""
        tc = AccuracyValidationTestCase()
        
        with pytest.raises(ValueError):
            tc.calculate_brier_score(
                predictions=[1.0, 0.0],
                outcomes=[1, 0, 1]
            )


class TestEfficiencyValidationTestCase:
    """Test EfficiencyValidationTestCase functionality."""
    
    @pytest.mark.unit
    def test_measure_execution_time(self):
        """Test execution time measurement."""
        tc = EfficiencyValidationTestCase()
        
        def slow_function():
            time.sleep(0.01)  # 10ms
            return 42
        
        result, elapsed = tc.measure_execution_time(slow_function)
        
        assert result == 42
        assert elapsed >= 0.01  # At least 10ms
    
    @pytest.mark.unit
    def test_calculate_speedup(self):
        """Test speedup calculation."""
        tc = EfficiencyValidationTestCase()
        
        speedup = tc.calculate_speedup(baseline_time=100.0, optimized_time=80.0)
        assert speedup == 20.0  # 20% speedup
    
    @pytest.mark.unit
    def test_calculate_speedup_zero_baseline(self):
        """Test speedup with zero baseline."""
        tc = EfficiencyValidationTestCase()
        
        speedup = tc.calculate_speedup(baseline_time=0.0, optimized_time=80.0)
        assert speedup == 0.0


class TestBenchmarkRunner:
    """Test BenchmarkRunner functionality."""
    
    @pytest.mark.unit
    def test_benchmark_runner_basic(self):
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
    def test_benchmark_runner_with_threshold_pass(self):
        """Test BenchmarkRunner with passing threshold."""
        runner = BenchmarkRunner(capture_hardware=False)
        
        def fast_func():
            return 1 + 1
        
        result = runner.run(
            benchmark_id="BM-TEST",
            benchmark_name="Test Benchmark",
            func=fast_func,
            iterations=3,
            warmup=1,
            threshold_ms=1000  # 1 second - should easily pass
        )
        
        assert result.passed
        assert result.threshold_ms == 1000
    
    @pytest.mark.unit
    def test_benchmark_runner_statistics(self):
        """Test BenchmarkRunner statistics calculation."""
        runner = BenchmarkRunner(capture_hardware=False)
        
        def dummy_func():
            return sum(range(100))
        
        result = runner.run(
            benchmark_id="BM-TEST",
            benchmark_name="Test Benchmark",
            func=dummy_func,
            iterations=5,
            warmup=1
        )
        
        assert result.iterations == 5
        assert result.mean_time_ms > 0
        assert result.median_time_ms > 0
        assert result.min_time_ms <= result.mean_time_ms
        assert result.max_time_ms >= result.mean_time_ms
    
    @pytest.mark.unit
    def test_benchmark_runner_throughput(self):
        """Test BenchmarkRunner throughput benchmark."""
        runner = BenchmarkRunner(capture_hardware=False)
        
        def process_items():
            time.sleep(0.01)  # 10ms
            return True
        
        result = runner.run_throughput(
            benchmark_id="BM-TEST",
            benchmark_name="Test Throughput",
            func=process_items,
            items_count=10,
            iterations=2,
            warmup=1,
            unit="items"
        )
        
        assert result.throughput is not None
        assert result.throughput > 0
        assert result.throughput_unit == "items/second"
    
    @pytest.mark.unit
    def test_benchmark_result_to_dict(self):
        """Test BenchmarkResult serialization."""
        result = BenchmarkResult(
            benchmark_id="BM-01",
            benchmark_name="Test",
            iterations=5,
            mean_time_ms=100.0,
            median_time_ms=98.0,
            std_dev_ms=5.0,
            min_time_ms=90.0,
            max_time_ms=110.0,
            passed=True
        )
        
        d = result.to_dict()
        assert d["benchmark_id"] == "BM-01"
        assert d["timing"]["mean_ms"] == 100.0
        assert d["passed"] is True


class TestHardwareProfiler:
    """Test HardwareProfiler functionality."""
    
    @pytest.mark.unit
    def test_hardware_profiler_capture(self):
        """Test hardware profile capture."""
        profile = HardwareProfiler.capture()
        
        assert "platform" in profile
        assert "cpu" in profile
        assert "memory" in profile
        assert profile["cpu"]["logical_cores"] is not None
        assert profile["cpu"]["logical_cores"] > 0
    
    @pytest.mark.unit
    def test_hardware_profiler_platform_info(self):
        """Test platform information capture."""
        profile = HardwareProfiler.capture()
        
        assert "system" in profile["platform"]
        assert "python_version" in profile["platform"]
        assert profile["platform"]["python_version"] is not None
