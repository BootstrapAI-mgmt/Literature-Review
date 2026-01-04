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
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Import psutil if available, provide fallback otherwise
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


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
        profile = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            }
        }
        
        if PSUTIL_AVAILABLE:
            # CPU information
            cpu_freq = psutil.cpu_freq()
            profile["cpu"] = {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "frequency_mhz": getattr(cpu_freq, 'current', None) if cpu_freq else None,
                "usage_percent": psutil.cpu_percent(interval=0.1)
            }
            
            # Memory information
            mem = psutil.virtual_memory()
            profile["memory"] = {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_percent": mem.percent
            }
            
            # Disk information
            try:
                disk = psutil.disk_usage('/')
                profile["disk"] = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2)
                }
            except OSError:
                profile["disk"] = {"error": "Unable to read disk info"}
        else:
            # Fallback when psutil is not available
            profile["cpu"] = {
                "physical_cores": os.cpu_count(),
                "logical_cores": os.cpu_count(),
                "frequency_mhz": None,
                "usage_percent": None
            }
            profile["memory"] = {
                "total_gb": None,
                "available_gb": None,
                "used_percent": None
            }
            profile["disk"] = {
                "total_gb": None,
                "free_gb": None
            }
        
        return profile


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
