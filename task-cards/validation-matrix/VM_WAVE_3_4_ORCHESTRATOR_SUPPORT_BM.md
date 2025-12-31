# Task Card: Orchestrator & Support Component Benchmarks

**Task ID:** VM-W3-4  
**Wave:** 3 (Component Benchmarks)  
**Priority:** MEDIUM  
**Estimated Effort:** 6 hours  
**Status:** Not Started  
**Dependencies:** VM-W0-1  
**Blocks:** VM-W4-1, VM-W4-2, VM-W5-1  
**Validation IDs:** BM-04, BM-05, BM-06

---

## Objective

Establish performance benchmarks for the Pipeline Orchestrator and support components (pre-filter, database sync), measuring gap report generation, scoring throughput, and database synchronization performance.

## Background

Support components enable efficient pipeline operation:
- **Orchestrator**: Coordinates entire review pipeline, generates gap reports
- **Pre-filter**: Rapid relevance scoring to reduce LLM calls
- **Database Sync**: Maintains persistent storage for results

Performance benchmarks ensure operational viability:
- **BM-04**: Gap report generation <5 minutes for 500 papers
- **BM-05**: Pre-filter scoring ≥10 papers/second
- **BM-06**: Database sync ≥100 records/second

## Success Criteria

- [ ] BM-04: Gap report <5min for 500 papers
- [ ] BM-05: Pre-filter ≥10 papers/sec
- [ ] BM-06: DB sync ≥100 records/sec
- [ ] Memory usage profiled for all components
- [ ] Scaling characteristics documented

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| BM-04 | Gap Report Generation | 500 papers dataset | Complete gap report | <5 minutes |
| BM-04a | Report Scaling | 100, 250, 500 papers | Scaling curve | Linear or sub-linear |
| BM-05 | Pre-filter Throughput | 100 papers | All scored | ≥10 papers/sec |
| BM-05a | Pre-filter Batch | 500 papers | All scored | ≥15 papers/sec |
| BM-06 | DB Sync Write | 100 records | All persisted | ≥100 records/sec |
| BM-06a | DB Sync Read | 500 records | All retrieved | ≥200 records/sec |

---

## Deliverables

### 1. Orchestrator Benchmark Implementation

**File:** `tests/benchmarks/component/test_orchestrator_benchmark.py`

```python
"""
Orchestrator & Support Components Benchmark Tests

Validates BM-04, BM-05, BM-06 from the validation matrix.
Measures performance of orchestrator, pre-filter, and database sync.
"""

import pytest
import time
import statistics
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import tracemalloc

from tests.benchmarks.runner import BenchmarkRunner, BenchmarkResult
from tests.benchmarks.profiler import HardwareProfiler


# =============================================================================
# Configuration
# =============================================================================

# BM-04 thresholds (Orchestrator/Gap Report)
GAP_REPORT_MAX_SECONDS = 300.0  # 5 minutes for 500 papers
GAP_REPORT_PAPER_COUNT = 500

# BM-05 thresholds (Pre-filter)
PREFILTER_MIN_PAPERS_PER_SEC = 10.0
PREFILTER_BATCH_MIN_PAPERS_PER_SEC = 15.0

# BM-06 thresholds (Database Sync)
DB_WRITE_MIN_RECORDS_PER_SEC = 100.0
DB_READ_MIN_RECORDS_PER_SEC = 200.0

# Benchmark parameters
WARMUP_RUNS = 1
BENCHMARK_RUNS = 3


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class GapReportMetrics:
    """Metrics for gap report generation."""
    total_papers: int
    total_time_seconds: float
    papers_per_second: float
    
    # Report content metrics
    gaps_identified: int
    pillars_covered: int
    coverage_percentage: float
    
    # Resource metrics
    peak_memory_mb: float


@dataclass
class PrefilterMetrics:
    """Metrics for pre-filter scoring."""
    total_papers: int
    total_time_seconds: float
    papers_per_second: float
    
    # Scoring results
    relevant_count: int
    irrelevant_count: int
    relevance_rate: float
    
    # Resource metrics
    peak_memory_mb: float


@dataclass
class DBSyncMetrics:
    """Metrics for database synchronization."""
    operation: str  # "write" or "read"
    total_records: int
    total_time_seconds: float
    records_per_second: float
    
    # Resource metrics
    peak_memory_mb: float


@dataclass
class ScalingResult:
    """Result of scaling analysis."""
    sizes: List[int]
    times: List[float]
    rates: List[float]
    is_linear: bool  # True if scales linearly or better
    scaling_factor: float  # Time multiplier per 2x data


# =============================================================================
# Mock Components (for isolated benchmarking)
# =============================================================================

class MockOrchestrator:
    """
    Mock Pipeline Orchestrator for benchmark testing.
    
    In production, import actual PipelineOrchestrator.
    """
    
    def __init__(self, simulate_delay: bool = True):
        self.simulate_delay = simulate_delay
    
    def generate_gap_report(
        self,
        papers: List[Dict],
        pillar_definitions: Dict
    ) -> Dict:
        """Generate coverage gap report."""
        start = time.perf_counter()
        
        # Simulate analysis per paper (2-10ms each)
        for i, paper in enumerate(papers):
            if self.simulate_delay:
                time.sleep(0.005)  # 5ms per paper average
            
            # Simulate periodic progress
            if i > 0 and i % 100 == 0:
                pass  # Progress checkpoint
        
        total_time = time.perf_counter() - start
        
        # Generate report content
        pillars = list(pillar_definitions.keys()) if pillar_definitions else ["P1", "P2", "P3", "P4"]
        coverage = {p: len([pa for pa in papers if pa.get("pillar") == p]) / len(papers) for p in pillars}
        gaps = [p for p, c in coverage.items() if c < 0.2]
        
        return {
            "total_papers": len(papers),
            "pillars_covered": len([p for p, c in coverage.items() if c > 0]),
            "gaps_identified": len(gaps),
            "coverage_percentage": sum(coverage.values()) / len(coverage) * 100,
            "gap_details": gaps,
            "timing": total_time
        }


class MockPrefilter:
    """
    Mock Pre-filter scoring component.
    
    In production, import actual PrefilterScorer.
    """
    
    def __init__(self, simulate_delay: bool = True):
        self.simulate_delay = simulate_delay
    
    def score_papers(self, papers: List[Dict], query: str) -> List[Dict]:
        """Score papers for relevance."""
        import random
        
        results = []
        for paper in papers:
            if self.simulate_delay:
                time.sleep(0.05)  # 50ms per paper (allows ~20 papers/sec)
            
            score = random.uniform(0.3, 0.9)
            results.append({
                "paper_id": paper.get("id", ""),
                "title": paper.get("title", ""),
                "relevance_score": score,
                "is_relevant": score >= 0.5
            })
        
        return results
    
    def score_batch(self, papers: List[Dict], query: str, batch_size: int = 50) -> List[Dict]:
        """Score papers in batches for better throughput."""
        results = []
        
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i + batch_size]
            if self.simulate_delay:
                time.sleep(0.02 * len(batch))  # 20ms per paper in batch
            
            import random
            for paper in batch:
                score = random.uniform(0.3, 0.9)
                results.append({
                    "paper_id": paper.get("id", ""),
                    "relevance_score": score,
                    "is_relevant": score >= 0.5
                })
        
        return results


class MockDBSync:
    """
    Mock Database Sync component.
    
    Uses SQLite for realistic I/O testing.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or ":memory:"
        self._setup_db()
    
    def _setup_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY,
                paper_id TEXT,
                claim_text TEXT,
                verdict TEXT,
                score REAL,
                evidence TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def write_records(self, records: List[Dict]) -> int:
        """Write records to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for record in records:
            cursor.execute("""
                INSERT INTO reviews (paper_id, claim_text, verdict, score, evidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record.get("paper_id", ""),
                record.get("claim_text", ""),
                record.get("verdict", ""),
                record.get("score", 0.0),
                json.dumps(record.get("evidence", {})),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        count = cursor.rowcount
        conn.close()
        
        return len(records)
    
    def read_records(self, limit: int = 500) -> List[Dict]:
        """Read records from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(f"SELECT * FROM reviews LIMIT {limit}")
        
        records = []
        for row in cursor:
            records.append({
                "id": row[0],
                "paper_id": row[1],
                "claim_text": row[2],
                "verdict": row[3],
                "score": row[4],
                "evidence": json.loads(row[5]) if row[5] else {},
                "timestamp": row[6]
            })
        
        conn.close()
        return records
    
    def clear(self):
        """Clear all records."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM reviews")
        conn.commit()
        conn.close()


def get_orchestrator():
    """Get orchestrator instance."""
    try:
        from literature_review.orchestrator import PipelineOrchestrator
        return PipelineOrchestrator()
    except ImportError:
        return MockOrchestrator(simulate_delay=False)


def get_prefilter():
    """Get pre-filter instance."""
    try:
        from literature_review.prefilter import PrefilterScorer
        return PrefilterScorer()
    except ImportError:
        return MockPrefilter(simulate_delay=False)


def get_db_sync(db_path: Optional[str] = None):
    """Get database sync instance."""
    try:
        from literature_review.db_sync import DatabaseSync
        return DatabaseSync(db_path)
    except ImportError:
        return MockDBSync(db_path)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def benchmark_runner():
    """Create benchmark runner."""
    return BenchmarkRunner(
        warmup_runs=WARMUP_RUNS,
        benchmark_runs=BENCHMARK_RUNS,
        capture_profile=True
    )


@pytest.fixture
def sample_papers_100() -> List[Dict]:
    """Generate 100 sample papers."""
    return [
        {
            "id": f"paper_{i:04d}",
            "title": f"Research Paper {i}",
            "abstract": f"Abstract text for paper {i}",
            "pillar": f"P{(i % 4) + 1}",
            "year": 2020 + (i % 5)
        }
        for i in range(100)
    ]


@pytest.fixture
def sample_papers_500() -> List[Dict]:
    """Generate 500 sample papers."""
    return [
        {
            "id": f"paper_{i:04d}",
            "title": f"Research Paper {i}",
            "abstract": f"Abstract text for paper {i}",
            "pillar": f"P{(i % 4) + 1}",
            "year": 2020 + (i % 5)
        }
        for i in range(500)
    ]


@pytest.fixture
def pillar_definitions() -> Dict:
    """Sample pillar definitions."""
    return {
        "P1": {"name": "Core Architecture", "weight": 0.3},
        "P2": {"name": "Learning Mechanisms", "weight": 0.3},
        "P3": {"name": "Applications", "weight": 0.2},
        "P4": {"name": "Future Directions", "weight": 0.2}
    }


@pytest.fixture
def sample_records_100() -> List[Dict]:
    """Generate 100 sample review records."""
    return [
        {
            "paper_id": f"paper_{i:04d}",
            "claim_text": f"Claim {i} from paper",
            "verdict": "approved" if i % 3 == 0 else "rejected",
            "score": 3.0 + (i % 20) * 0.1,
            "evidence": {"text": f"Evidence for claim {i}"}
        }
        for i in range(100)
    ]


@pytest.fixture
def sample_records_500() -> List[Dict]:
    """Generate 500 sample review records."""
    return [
        {
            "paper_id": f"paper_{i:04d}",
            "claim_text": f"Claim {i} from paper",
            "verdict": "approved" if i % 3 == 0 else "rejected",
            "score": 3.0 + (i % 20) * 0.1,
            "evidence": {"text": f"Evidence for claim {i}"}
        }
        for i in range(500)
    ]


@pytest.fixture
def temp_db():
    """Create temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


# =============================================================================
# Tests: BM-04 (Orchestrator/Gap Report)
# =============================================================================

@pytest.mark.benchmark
@pytest.mark.slow_benchmark
class TestOrchestratorBenchmark:
    """Benchmark tests for Orchestrator (BM-04)."""
    
    def test_gap_report_500_papers(
        self,
        sample_papers_500,
        pillar_definitions,
        benchmark_runner
    ):
        """
        BM-04: Gap report should generate in <5 minutes for 500 papers.
        """
        orchestrator = get_orchestrator()
        
        tracemalloc.start()
        start = time.perf_counter()
        
        report = orchestrator.generate_gap_report(sample_papers_500, pillar_definitions)
        
        total_time = time.perf_counter() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        metrics = GapReportMetrics(
            total_papers=len(sample_papers_500),
            total_time_seconds=total_time,
            papers_per_second=len(sample_papers_500) / total_time if total_time > 0 else 0,
            gaps_identified=report.get("gaps_identified", 0),
            pillars_covered=report.get("pillars_covered", 0),
            coverage_percentage=report.get("coverage_percentage", 0),
            peak_memory_mb=peak / (1024 * 1024)
        )
        
        result = BenchmarkResult(
            benchmark_id="BM-04",
            name="Gap Report Generation (500 papers)",
            value=total_time,
            unit="seconds",
            threshold=GAP_REPORT_MAX_SECONDS,
            passed=total_time < GAP_REPORT_MAX_SECONDS,
            metadata={
                "papers": len(sample_papers_500),
                "papers_per_second": metrics.papers_per_second,
                "gaps_identified": metrics.gaps_identified,
                "peak_memory_mb": metrics.peak_memory_mb
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert total_time < GAP_REPORT_MAX_SECONDS, (
            f"Gap report took {total_time:.1f}s, "
            f"exceeds {GAP_REPORT_MAX_SECONDS}s threshold"
        )
    
    def test_gap_report_scaling(
        self,
        pillar_definitions,
        benchmark_runner
    ):
        """
        BM-04a: Test scaling characteristics of gap report generation.
        """
        orchestrator = get_orchestrator()
        
        sizes = [100, 250, 500]
        times = []
        rates = []
        
        for size in sizes:
            papers = [
                {"id": f"p{i}", "pillar": f"P{i%4+1}"}
                for i in range(size)
            ]
            
            start = time.perf_counter()
            orchestrator.generate_gap_report(papers, pillar_definitions)
            elapsed = time.perf_counter() - start
            
            times.append(elapsed)
            rates.append(size / elapsed if elapsed > 0 else 0)
        
        # Check if scaling is linear or better
        # Compare time ratio to size ratio
        time_ratio = times[-1] / times[0] if times[0] > 0 else 0
        size_ratio = sizes[-1] / sizes[0]
        is_linear = time_ratio <= size_ratio * 1.2  # Allow 20% margin
        
        scaling = ScalingResult(
            sizes=sizes,
            times=times,
            rates=rates,
            is_linear=is_linear,
            scaling_factor=time_ratio / (size_ratio / 2) if size_ratio > 0 else 0
        )
        
        result = BenchmarkResult(
            benchmark_id="BM-04a",
            name="Gap Report Scaling",
            value=scaling.scaling_factor,
            unit="factor",
            threshold=2.5,  # Should not increase more than 2.5x per 2x data
            passed=is_linear,
            metadata={
                "sizes": sizes,
                "times": times,
                "rates": rates,
                "time_ratio": time_ratio,
                "size_ratio": size_ratio
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert is_linear, (
            f"Gap report scaling is super-linear: "
            f"time ratio {time_ratio:.2f} vs size ratio {size_ratio:.2f}"
        )


# =============================================================================
# Tests: BM-05 (Pre-filter)
# =============================================================================

@pytest.mark.benchmark
class TestPrefilterBenchmark:
    """Benchmark tests for Pre-filter (BM-05)."""
    
    def test_prefilter_throughput_100(
        self,
        sample_papers_100,
        benchmark_runner
    ):
        """
        BM-05: Pre-filter should score ≥10 papers/second.
        """
        prefilter = get_prefilter()
        query = "neuromorphic computing hardware implementation"
        
        tracemalloc.start()
        start = time.perf_counter()
        
        results = prefilter.score_papers(sample_papers_100, query)
        
        total_time = time.perf_counter() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        papers_per_second = len(sample_papers_100) / total_time if total_time > 0 else 0
        relevant = sum(1 for r in results if r.get("is_relevant", False))
        
        metrics = PrefilterMetrics(
            total_papers=len(sample_papers_100),
            total_time_seconds=total_time,
            papers_per_second=papers_per_second,
            relevant_count=relevant,
            irrelevant_count=len(results) - relevant,
            relevance_rate=relevant / len(results) if results else 0,
            peak_memory_mb=peak / (1024 * 1024)
        )
        
        result = BenchmarkResult(
            benchmark_id="BM-05",
            name="Pre-filter Throughput",
            value=papers_per_second,
            unit="papers/sec",
            threshold=PREFILTER_MIN_PAPERS_PER_SEC,
            passed=papers_per_second >= PREFILTER_MIN_PAPERS_PER_SEC,
            metadata={
                "total_papers": len(sample_papers_100),
                "total_time": total_time,
                "relevant_rate": metrics.relevance_rate,
                "peak_memory_mb": metrics.peak_memory_mb
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert papers_per_second >= PREFILTER_MIN_PAPERS_PER_SEC, (
            f"Pre-filter throughput {papers_per_second:.1f} papers/sec "
            f"below {PREFILTER_MIN_PAPERS_PER_SEC} threshold"
        )
    
    def test_prefilter_batch_throughput(
        self,
        sample_papers_500,
        benchmark_runner
    ):
        """
        BM-05a: Batch pre-filter should score ≥15 papers/second.
        """
        prefilter = get_prefilter()
        query = "neuromorphic computing hardware implementation"
        
        start = time.perf_counter()
        results = prefilter.score_batch(sample_papers_500, query)
        total_time = time.perf_counter() - start
        
        papers_per_second = len(sample_papers_500) / total_time if total_time > 0 else 0
        
        result = BenchmarkResult(
            benchmark_id="BM-05a",
            name="Pre-filter Batch Throughput",
            value=papers_per_second,
            unit="papers/sec",
            threshold=PREFILTER_BATCH_MIN_PAPERS_PER_SEC,
            passed=papers_per_second >= PREFILTER_BATCH_MIN_PAPERS_PER_SEC,
            metadata={
                "total_papers": len(sample_papers_500),
                "total_time": total_time,
                "batch_size": 50
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert papers_per_second >= PREFILTER_BATCH_MIN_PAPERS_PER_SEC, (
            f"Batch throughput {papers_per_second:.1f} papers/sec "
            f"below {PREFILTER_BATCH_MIN_PAPERS_PER_SEC} threshold"
        )


# =============================================================================
# Tests: BM-06 (Database Sync)
# =============================================================================

@pytest.mark.benchmark
class TestDBSyncBenchmark:
    """Benchmark tests for Database Sync (BM-06)."""
    
    def test_db_write_throughput(
        self,
        sample_records_100,
        temp_db,
        benchmark_runner
    ):
        """
        BM-06: DB write should handle ≥100 records/second.
        """
        db_sync = get_db_sync(temp_db)
        
        tracemalloc.start()
        start = time.perf_counter()
        
        written = db_sync.write_records(sample_records_100)
        
        total_time = time.perf_counter() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        records_per_second = len(sample_records_100) / total_time if total_time > 0 else 0
        
        metrics = DBSyncMetrics(
            operation="write",
            total_records=len(sample_records_100),
            total_time_seconds=total_time,
            records_per_second=records_per_second,
            peak_memory_mb=peak / (1024 * 1024)
        )
        
        result = BenchmarkResult(
            benchmark_id="BM-06",
            name="DB Write Throughput",
            value=records_per_second,
            unit="records/sec",
            threshold=DB_WRITE_MIN_RECORDS_PER_SEC,
            passed=records_per_second >= DB_WRITE_MIN_RECORDS_PER_SEC,
            metadata={
                "total_records": len(sample_records_100),
                "total_time": total_time,
                "peak_memory_mb": metrics.peak_memory_mb
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert records_per_second >= DB_WRITE_MIN_RECORDS_PER_SEC, (
            f"DB write throughput {records_per_second:.1f} records/sec "
            f"below {DB_WRITE_MIN_RECORDS_PER_SEC} threshold"
        )
    
    def test_db_read_throughput(
        self,
        sample_records_500,
        temp_db,
        benchmark_runner
    ):
        """
        BM-06a: DB read should handle ≥200 records/second.
        """
        db_sync = get_db_sync(temp_db)
        
        # First write records
        db_sync.write_records(sample_records_500)
        
        # Measure read
        start = time.perf_counter()
        records = db_sync.read_records(500)
        total_time = time.perf_counter() - start
        
        records_per_second = len(records) / total_time if total_time > 0 else 0
        
        result = BenchmarkResult(
            benchmark_id="BM-06a",
            name="DB Read Throughput",
            value=records_per_second,
            unit="records/sec",
            threshold=DB_READ_MIN_RECORDS_PER_SEC,
            passed=records_per_second >= DB_READ_MIN_RECORDS_PER_SEC,
            metadata={
                "total_records": len(records),
                "total_time": total_time
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert records_per_second >= DB_READ_MIN_RECORDS_PER_SEC, (
            f"DB read throughput {records_per_second:.1f} records/sec "
            f"below {DB_READ_MIN_RECORDS_PER_SEC} threshold"
        )
```

---

## Implementation Plan

### Hour 1-2: Orchestrator Benchmarks
1. Implement gap report generation measurement
2. Test with 500 paper dataset
3. Add scaling analysis (100 → 500 papers)

### Hour 3-4: Pre-filter Benchmarks
1. Implement single-paper scoring benchmark
2. Implement batch scoring benchmark
3. Profile memory usage

### Hour 5: Database Sync Benchmarks
1. Implement write throughput test
2. Implement read throughput test
3. Add SQLite I/O profiling

### Hour 6: Integration & Reporting
1. Run full benchmark suite
2. Document baseline values
3. Generate comparison report

---

## Testing Instructions

```bash
# Run all support component benchmarks
pytest tests/benchmarks/component/test_orchestrator_benchmark.py -v -m benchmark

# Run orchestrator benchmarks only
pytest tests/benchmarks/component/test_orchestrator_benchmark.py -v -k "Orchestrator"

# Run pre-filter benchmarks
pytest tests/benchmarks/component/test_orchestrator_benchmark.py -v -k "Prefilter"

# Run database sync benchmarks
pytest tests/benchmarks/component/test_orchestrator_benchmark.py -v -k "DBSync"

# Run with timing details
pytest tests/benchmarks/component/test_orchestrator_benchmark.py -v --durations=10
```

---

## Dependencies

### Python Packages
- `pytest>=7.0.0` - Test framework
- `sqlite3` - Database operations (stdlib)
- `psutil>=5.9.0` - Resource monitoring (optional)

### Internal Dependencies
- `tests/benchmarks/runner.py` - BenchmarkRunner class
- `literature_review/orchestrator.py` - Gap report generation
- `literature_review/prefilter.py` - Pre-filter scoring
- `literature_review/db_sync.py` - Database synchronization

---

## Acceptance Criteria

- [ ] BM-04: Gap report <5 minutes for 500 papers
- [ ] BM-04a: Scaling is linear or sub-linear
- [ ] BM-05: Pre-filter ≥10 papers/second
- [ ] BM-05a: Batch pre-filter ≥15 papers/second
- [ ] BM-06: DB write ≥100 records/second
- [ ] BM-06a: DB read ≥200 records/second
- [ ] Memory usage profiled for all operations
- [ ] Benchmark report generated with all metrics

---

## Notes

- Orchestrator is critical for gap analysis and prioritization
- Pre-filter reduces LLM costs by 60-80% when tuned correctly
- SQLite adequate for single-user; consider PostgreSQL for production
- Gap report generation benefits from parallel processing
- Pre-filter can be GPU-accelerated with sentence-transformers
- Database batch operations significantly improve throughput
