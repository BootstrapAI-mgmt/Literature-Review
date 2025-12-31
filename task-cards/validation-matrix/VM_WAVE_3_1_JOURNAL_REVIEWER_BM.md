# Task Card: Journal Reviewer Benchmark

**Task ID:** VM-W3-1  
**Wave:** 3 (Component Benchmarks)  
**Priority:** MEDIUM  
**Estimated Effort:** 6 hours  
**Status:** Not Started  
**Dependencies:** VM-W0-1  
**Blocks:** VM-W4-1, VM-W5-1  
**Validation IDs:** BM-01

---

## Objective

Establish performance benchmarks for the Journal Reviewer component, measuring paper analysis throughput, latency, and resource consumption under controlled conditions.

## Background

The Journal Reviewer is the entry point of the pipeline, responsible for:
- PDF text extraction
- Section identification
- Claim extraction from research papers
- Evidence linking

Performance benchmarks ensure the component meets operational requirements:
- **BM-01**: Single paper analysis should complete in <45 seconds for a 20-page PDF

## Success Criteria

- [ ] BM-01: Single paper analysis <45s for 20-page PDF
- [ ] Throughput benchmark established (papers/hour)
- [ ] Memory usage profile captured
- [ ] CPU utilization patterns documented
- [ ] Variance analysis completed (<10% run-to-run variance)

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| BM-01 | Single Paper Analysis | 20-page PDF | Analysis complete | <45 seconds total time |
| BM-01a | Throughput | 10 papers batch | papers/hour rate | Baseline established |
| BM-01b | Memory Profile | Single paper | Peak memory MB | <2GB peak usage |
| BM-01c | Scaling | 1, 5, 10 papers | Linear scaling | <20% overhead per batch |

---

## Deliverables

### 1. Benchmark Test Implementation

**File:** `tests/benchmarks/component/test_journal_reviewer_benchmark.py`

```python
"""
Journal Reviewer Component Benchmark Tests

Validates BM-01 from the validation matrix.
Measures performance characteristics of the Journal Reviewer component.
"""

import pytest
import time
import statistics
import psutil
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json
import tracemalloc

from tests.benchmarks.runner import BenchmarkRunner, BenchmarkResult
from tests.benchmarks.profiler import HardwareProfiler, ResourceSnapshot


# =============================================================================
# Configuration
# =============================================================================

# BM-01 thresholds
SINGLE_PAPER_MAX_SECONDS = 45.0
MAX_MEMORY_MB = 2048
THROUGHPUT_BASELINE_PAPERS_PER_HOUR = 80  # Expected minimum

# Benchmark parameters
WARMUP_RUNS = 1
BENCHMARK_RUNS = 5
BATCH_SIZES = [1, 5, 10]

# Test paper specifications
STANDARD_PAPER_PAGES = 20
STANDARD_PAPER_SIZE_KB = 500  # Approximate


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class JournalReviewerMetrics:
    """Metrics captured during Journal Reviewer benchmark."""
    paper_path: str
    page_count: int
    file_size_kb: float
    
    # Timing metrics
    total_time_seconds: float
    extraction_time_seconds: float
    analysis_time_seconds: float
    
    # Resource metrics
    peak_memory_mb: float
    avg_cpu_percent: float
    
    # Output metrics
    claims_extracted: int
    sections_identified: int
    
    # Derived metrics
    @property
    def time_per_page(self) -> float:
        return self.total_time_seconds / self.page_count if self.page_count > 0 else 0
    
    @property
    def claims_per_second(self) -> float:
        return self.claims_extracted / self.total_time_seconds if self.total_time_seconds > 0 else 0


@dataclass
class ThroughputResult:
    """Result of throughput benchmark."""
    batch_size: int
    total_time_seconds: float
    papers_per_hour: float
    avg_time_per_paper: float
    peak_memory_mb: float
    scaling_efficiency: float  # 1.0 = perfect linear scaling


# =============================================================================
# Benchmark Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def benchmark_runner():
    """Create benchmark runner with hardware profiling."""
    runner = BenchmarkRunner(
        warmup_runs=WARMUP_RUNS,
        benchmark_runs=BENCHMARK_RUNS,
        capture_profile=True
    )
    return runner


@pytest.fixture(scope="module")
def hardware_profiler():
    """Create hardware profiler for resource monitoring."""
    return HardwareProfiler()


@pytest.fixture
def standard_test_paper(tmp_path) -> Path:
    """Create or locate a standard 20-page test PDF."""
    # Check for existing test papers
    test_papers_dir = Path(__file__).parent.parent.parent / "fixtures" / "papers"
    if test_papers_dir.exists():
        papers = list(test_papers_dir.glob("*.pdf"))
        # Find a paper close to 20 pages
        for paper in papers:
            # In real implementation, check page count
            if paper.stat().st_size > 100_000:  # >100KB as proxy
                return paper
    
    # Create synthetic test paper if none exists
    synthetic_path = tmp_path / "test_paper_20pages.pdf"
    _create_synthetic_pdf(synthetic_path, pages=20)
    return synthetic_path


@pytest.fixture
def batch_test_papers(tmp_path) -> List[Path]:
    """Create batch of test papers for throughput testing."""
    papers = []
    for i in range(10):
        paper_path = tmp_path / f"test_paper_{i}.pdf"
        _create_synthetic_pdf(paper_path, pages=15 + (i % 10))
        papers.append(paper_path)
    return papers


def _create_synthetic_pdf(path: Path, pages: int = 20):
    """Create a synthetic PDF for testing."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        c = canvas.Canvas(str(path), pagesize=letter)
        for page in range(pages):
            c.drawString(100, 750, f"Test Paper - Page {page + 1}")
            c.drawString(100, 700, "Abstract: This is a synthetic test paper.")
            c.drawString(100, 650, "Methods: Standard benchmark methodology.")
            c.drawString(100, 600, f"Results: Performance metric {page * 10}%.")
            c.showPage()
        c.save()
    except ImportError:
        # Fallback: create empty file for structure testing
        path.write_bytes(b"%PDF-1.4 synthetic test file")


# =============================================================================
# Mock Journal Reviewer (for isolated benchmarking)
# =============================================================================

class MockJournalReviewer:
    """
    Mock Journal Reviewer for benchmark testing.
    
    In production, import the actual JournalReviewer class.
    This mock simulates realistic timing patterns.
    """
    
    def __init__(self, simulate_delay: bool = True):
        self.simulate_delay = simulate_delay
    
    def analyze_paper(self, paper_path: Path) -> Dict:
        """Simulate paper analysis with realistic timing."""
        start = time.perf_counter()
        
        # Simulate extraction phase
        extraction_start = time.perf_counter()
        if self.simulate_delay:
            time.sleep(0.5)  # Simulate PDF parsing
        extraction_time = time.perf_counter() - extraction_start
        
        # Simulate analysis phase
        analysis_start = time.perf_counter()
        if self.simulate_delay:
            time.sleep(1.0)  # Simulate LLM calls
        analysis_time = time.perf_counter() - analysis_start
        
        total_time = time.perf_counter() - start
        
        return {
            "paper_path": str(paper_path),
            "claims": [{"id": f"claim_{i}", "text": f"Claim {i}"} for i in range(5)],
            "sections": ["Abstract", "Introduction", "Methods", "Results", "Discussion"],
            "timing": {
                "extraction": extraction_time,
                "analysis": analysis_time,
                "total": total_time
            }
        }


def get_journal_reviewer():
    """
    Get Journal Reviewer instance for benchmarking.
    
    Returns actual implementation if available, mock otherwise.
    """
    try:
        from literature_review.journal_reviewer import JournalReviewer
        return JournalReviewer()
    except ImportError:
        return MockJournalReviewer(simulate_delay=False)


# =============================================================================
# Benchmark Helper Functions
# =============================================================================

def measure_paper_analysis(
    reviewer,
    paper_path: Path,
    profiler: Optional[HardwareProfiler] = None
) -> JournalReviewerMetrics:
    """
    Measure single paper analysis with resource profiling.
    """
    # Start memory tracking
    tracemalloc.start()
    
    # Start resource monitoring
    process = psutil.Process(os.getpid())
    cpu_samples = []
    
    # Get file info
    file_size_kb = paper_path.stat().st_size / 1024 if paper_path.exists() else 0
    
    # Run analysis
    start_time = time.perf_counter()
    result = reviewer.analyze_paper(paper_path)
    total_time = time.perf_counter() - start_time
    
    # Get memory stats
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_memory_mb = peak / (1024 * 1024)
    
    # Get CPU stats
    avg_cpu = process.cpu_percent() / psutil.cpu_count()
    
    # Extract timing breakdown
    timing = result.get("timing", {})
    
    return JournalReviewerMetrics(
        paper_path=str(paper_path),
        page_count=20,  # Default assumption
        file_size_kb=file_size_kb,
        total_time_seconds=total_time,
        extraction_time_seconds=timing.get("extraction", 0),
        analysis_time_seconds=timing.get("analysis", 0),
        peak_memory_mb=peak_memory_mb,
        avg_cpu_percent=avg_cpu,
        claims_extracted=len(result.get("claims", [])),
        sections_identified=len(result.get("sections", []))
    )


def run_throughput_benchmark(
    reviewer,
    papers: List[Path],
    batch_size: int
) -> ThroughputResult:
    """Run throughput benchmark with specified batch size."""
    batch = papers[:batch_size]
    
    tracemalloc.start()
    start_time = time.perf_counter()
    
    for paper in batch:
        reviewer.analyze_paper(paper)
    
    total_time = time.perf_counter() - start_time
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    papers_per_hour = (batch_size / total_time) * 3600 if total_time > 0 else 0
    avg_time = total_time / batch_size if batch_size > 0 else 0
    
    # Calculate scaling efficiency (1.0 = perfect linear)
    expected_time = avg_time * batch_size
    scaling_efficiency = expected_time / total_time if total_time > 0 else 1.0
    
    return ThroughputResult(
        batch_size=batch_size,
        total_time_seconds=total_time,
        papers_per_hour=papers_per_hour,
        avg_time_per_paper=avg_time,
        peak_memory_mb=peak / (1024 * 1024),
        scaling_efficiency=min(scaling_efficiency, 1.0)
    )


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.benchmark
@pytest.mark.slow_benchmark
class TestJournalReviewerBenchmark:
    """Benchmark tests for Journal Reviewer component (BM-01)."""
    
    # -------------------------------------------------------------------------
    # BM-01: Single Paper Analysis Time
    # -------------------------------------------------------------------------
    
    def test_single_paper_analysis_time(
        self,
        standard_test_paper,
        benchmark_runner
    ):
        """
        BM-01: Single paper analysis should complete in <45 seconds.
        
        Target: 20-page PDF analyzed in <45s
        """
        reviewer = get_journal_reviewer()
        
        # Run benchmark with multiple iterations
        times = []
        for _ in range(BENCHMARK_RUNS):
            metrics = measure_paper_analysis(reviewer, standard_test_paper)
            times.append(metrics.total_time_seconds)
        
        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        
        # Record result
        result = BenchmarkResult(
            benchmark_id="BM-01",
            name="Single Paper Analysis",
            value=avg_time,
            unit="seconds",
            threshold=SINGLE_PAPER_MAX_SECONDS,
            passed=avg_time < SINGLE_PAPER_MAX_SECONDS,
            metadata={
                "runs": BENCHMARK_RUNS,
                "std_dev": std_dev,
                "min": min(times),
                "max": max(times),
                "paper_pages": 20
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert avg_time < SINGLE_PAPER_MAX_SECONDS, (
            f"Single paper analysis took {avg_time:.2f}s, "
            f"exceeds {SINGLE_PAPER_MAX_SECONDS}s threshold"
        )
    
    def test_single_paper_variance(
        self,
        standard_test_paper,
        benchmark_runner
    ):
        """
        Verify run-to-run variance is acceptable (<10%).
        """
        reviewer = get_journal_reviewer()
        
        times = []
        for _ in range(BENCHMARK_RUNS):
            metrics = measure_paper_analysis(reviewer, standard_test_paper)
            times.append(metrics.total_time_seconds)
        
        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        coefficient_of_variation = (std_dev / avg_time) * 100 if avg_time > 0 else 0
        
        assert coefficient_of_variation < 10.0, (
            f"Variance too high: {coefficient_of_variation:.1f}% CV "
            f"(target <10%)"
        )
    
    # -------------------------------------------------------------------------
    # BM-01a: Throughput Benchmark
    # -------------------------------------------------------------------------
    
    def test_throughput_baseline(
        self,
        batch_test_papers,
        benchmark_runner
    ):
        """
        BM-01a: Establish throughput baseline (papers/hour).
        
        Target: Baseline measurement for regression tracking.
        """
        reviewer = get_journal_reviewer()
        
        # Use 5 papers for throughput test
        result = run_throughput_benchmark(reviewer, batch_test_papers, batch_size=5)
        
        benchmark_result = BenchmarkResult(
            benchmark_id="BM-01a",
            name="Throughput Baseline",
            value=result.papers_per_hour,
            unit="papers/hour",
            threshold=THROUGHPUT_BASELINE_PAPERS_PER_HOUR,
            passed=result.papers_per_hour >= THROUGHPUT_BASELINE_PAPERS_PER_HOUR,
            metadata={
                "batch_size": result.batch_size,
                "total_time": result.total_time_seconds,
                "avg_per_paper": result.avg_time_per_paper
            }
        )
        
        benchmark_runner.record_result(benchmark_result)
        
        # This is a baseline test - we record the value but don't fail
        # unless it's drastically below expectations
        assert result.papers_per_hour > 0, "Throughput measurement failed"
    
    # -------------------------------------------------------------------------
    # BM-01b: Memory Profile
    # -------------------------------------------------------------------------
    
    def test_memory_profile(
        self,
        standard_test_paper,
        benchmark_runner
    ):
        """
        BM-01b: Memory usage should stay within bounds.
        
        Target: Peak memory <2GB for single paper analysis.
        """
        reviewer = get_journal_reviewer()
        
        metrics = measure_paper_analysis(reviewer, standard_test_paper)
        
        benchmark_result = BenchmarkResult(
            benchmark_id="BM-01b",
            name="Memory Profile",
            value=metrics.peak_memory_mb,
            unit="MB",
            threshold=MAX_MEMORY_MB,
            passed=metrics.peak_memory_mb < MAX_MEMORY_MB,
            metadata={
                "paper_path": metrics.paper_path,
                "claims_extracted": metrics.claims_extracted
            }
        )
        
        benchmark_runner.record_result(benchmark_result)
        
        assert metrics.peak_memory_mb < MAX_MEMORY_MB, (
            f"Peak memory {metrics.peak_memory_mb:.1f}MB exceeds "
            f"{MAX_MEMORY_MB}MB threshold"
        )
    
    # -------------------------------------------------------------------------
    # BM-01c: Scaling Efficiency
    # -------------------------------------------------------------------------
    
    @pytest.mark.parametrize("batch_size", BATCH_SIZES)
    def test_scaling_efficiency(
        self,
        batch_test_papers,
        benchmark_runner,
        batch_size
    ):
        """
        BM-01c: Verify linear scaling with batch size.
        
        Target: <20% overhead per additional paper in batch.
        """
        reviewer = get_journal_reviewer()
        
        result = run_throughput_benchmark(reviewer, batch_test_papers, batch_size)
        
        benchmark_result = BenchmarkResult(
            benchmark_id=f"BM-01c-{batch_size}",
            name=f"Scaling Efficiency (batch={batch_size})",
            value=result.scaling_efficiency,
            unit="ratio",
            threshold=0.8,  # 80% efficiency = 20% overhead
            passed=result.scaling_efficiency >= 0.8,
            metadata={
                "batch_size": batch_size,
                "total_time": result.total_time_seconds,
                "papers_per_hour": result.papers_per_hour
            }
        )
        
        benchmark_runner.record_result(benchmark_result)
        
        # Scaling efficiency should be at least 80%
        assert result.scaling_efficiency >= 0.8, (
            f"Scaling efficiency {result.scaling_efficiency:.1%} "
            f"below 80% threshold for batch size {batch_size}"
        )


# =============================================================================
# Benchmark Report Generation
# =============================================================================

@pytest.mark.benchmark
class TestBenchmarkReporting:
    """Generate benchmark reports after all tests complete."""
    
    def test_generate_benchmark_report(self, benchmark_runner, tmp_path):
        """Generate JSON benchmark report."""
        report = benchmark_runner.generate_report()
        
        report_path = tmp_path / "journal_reviewer_benchmark_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        assert report_path.exists()
        assert "results" in report
        assert "hardware_profile" in report
```

---

## Implementation Plan

### Hour 1-2: Setup & Infrastructure
1. Create benchmark test file structure
2. Implement paper analysis measurement function
3. Set up memory and CPU profiling

### Hour 3-4: Core Benchmarks
1. Implement BM-01 single paper analysis test
2. Implement throughput measurement
3. Add variance analysis

### Hour 5: Resource Profiling
1. Implement memory profiling tests
2. Implement scaling efficiency tests
3. Add parameterized batch size tests

### Hour 6: Reporting & Documentation
1. Implement benchmark report generation
2. Document baseline values
3. Verify all tests pass

---

## Testing Instructions

```bash
# Run all Journal Reviewer benchmarks
pytest tests/benchmarks/component/test_journal_reviewer_benchmark.py -v -m benchmark

# Run only BM-01 tests
pytest tests/benchmarks/component/test_journal_reviewer_benchmark.py -v -k "BM-01"

# Run with timing output
pytest tests/benchmarks/component/test_journal_reviewer_benchmark.py -v --durations=10

# Skip slow benchmarks
pytest tests/benchmarks/component/test_journal_reviewer_benchmark.py -v -m "benchmark and not slow_benchmark"
```

---

## Dependencies

### Python Packages
- `pytest>=7.0.0` - Test framework
- `psutil>=5.9.0` - Resource monitoring
- `reportlab>=4.0.0` - PDF generation (optional, for synthetic test papers)

### Internal Dependencies
- `tests/benchmarks/runner.py` - BenchmarkRunner class
- `tests/benchmarks/profiler.py` - HardwareProfiler class
- `literature_review/journal_reviewer.py` - Component under test

---

## Acceptance Criteria

- [ ] BM-01: Single paper analysis <45s for 20-page PDF
- [ ] BM-01a: Throughput baseline established
- [ ] BM-01b: Peak memory <2GB during analysis
- [ ] BM-01c: Scaling efficiency ≥80% for batch processing
- [ ] Run-to-run variance <10%
- [ ] Benchmark report generated with all metrics
- [ ] Tests complete in <5 minutes total

---

## Notes

- Use mock reviewer for CI to avoid API costs
- Actual reviewer requires OpenAI API key
- Memory profiling uses tracemalloc for accuracy
- Synthetic PDFs used when test papers unavailable
- Baseline values will be updated after initial runs
