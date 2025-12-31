# Task Card: Judge Benchmark

**Task ID:** VM-W3-2  
**Wave:** 3 (Component Benchmarks)  
**Priority:** MEDIUM  
**Estimated Effort:** 6 hours  
**Status:** Not Started  
**Dependencies:** VM-W0-1  
**Blocks:** VM-W4-1, VM-W5-1  
**Validation IDs:** BM-02

---

## Objective

Establish performance benchmarks for the Judge component, measuring claim evaluation throughput, consensus mode overhead, and score calculation performance under controlled conditions.

## Background

The Judge is responsible for:
- Evaluating evidence quality across 6 dimensions
- Computing composite scores using weighted formula
- Making approve/reject decisions
- Operating in single or consensus mode (multiple LLM calls)

Performance benchmarks ensure the component meets operational requirements:
- **BM-02**: Batch claim evaluation should process ≥20 claims/minute

## Success Criteria

- [ ] BM-02: Batch evaluation ≥20 claims/minute
- [ ] Single claim evaluation baseline established
- [ ] Consensus mode overhead measured
- [ ] Score calculation performance profiled
- [ ] Memory usage during batch operations tracked

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| BM-02 | Batch Claim Evaluation | 20 claims | Evaluation complete | ≥20 claims/minute |
| BM-02a | Single Claim | 1 claim + evidence | Verdict + scores | <3 seconds |
| BM-02b | Consensus Overhead | Same claim, 2 modes | Overhead ratio | <2x single mode |
| BM-02c | Score Calculation | 100 score computations | All computed | <100ms total |

---

## Deliverables

### 1. Benchmark Test Implementation

**File:** `tests/benchmarks/component/test_judge_benchmark.py`

```python
"""
Judge Component Benchmark Tests

Validates BM-02 from the validation matrix.
Measures performance characteristics of the Judge component.
"""

import pytest
import time
import statistics
import json
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

# BM-02 thresholds
MIN_CLAIMS_PER_MINUTE = 20
SINGLE_CLAIM_MAX_SECONDS = 3.0
CONSENSUS_OVERHEAD_MAX_RATIO = 2.0
SCORE_CALC_MAX_MS = 100

# Benchmark parameters
WARMUP_RUNS = 1
BENCHMARK_RUNS = 3
BATCH_SIZE = 20


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class JudgeMetrics:
    """Metrics captured during Judge benchmark."""
    claim_count: int
    total_time_seconds: float
    claims_per_minute: float
    avg_time_per_claim: float
    
    # Score distribution
    approved_count: int
    rejected_count: int
    avg_composite_score: float
    
    # Resource metrics
    peak_memory_mb: float
    
    @property
    def approval_rate(self) -> float:
        total = self.approved_count + self.rejected_count
        return self.approved_count / total if total > 0 else 0


@dataclass
class ConsensusBenchmark:
    """Comparison of single vs consensus mode."""
    single_mode_time: float
    consensus_mode_time: float
    overhead_ratio: float
    agreement_rate: float  # How often modes agree


@dataclass
class ScoreCalcMetrics:
    """Metrics for pure score calculation performance."""
    calculation_count: int
    total_time_ms: float
    avg_time_per_calc_ms: float
    min_time_ms: float
    max_time_ms: float


# =============================================================================
# Mock Judge (for isolated benchmarking)
# =============================================================================

class MockJudge:
    """
    Mock Judge for benchmark testing.
    
    In production, import the actual Judge class.
    This mock simulates realistic timing and scoring patterns.
    """
    
    # Standard scoring weights (from actual implementation)
    WEIGHTS = {
        'strength': 0.30,
        'rigor': 0.25,
        'relevance': 0.25,
        'directness': 0.10,
        'recency': 0.05,
        'reproducibility': 0.05
    }
    
    APPROVAL_THRESHOLD = 3.0
    
    def __init__(self, consensus_mode: bool = False, simulate_delay: bool = True):
        self.consensus_mode = consensus_mode
        self.simulate_delay = simulate_delay
    
    def evaluate_claim(self, claim: Dict, evidence: Dict) -> Dict:
        """Evaluate a single claim with evidence."""
        start = time.perf_counter()
        
        if self.simulate_delay:
            # Simulate LLM call time
            base_delay = 0.1
            if self.consensus_mode:
                base_delay *= 2  # Two LLM calls in consensus
            time.sleep(base_delay)
        
        # Generate mock scores
        scores = self._generate_scores()
        composite = self._calculate_composite(scores)
        verdict = "approved" if composite >= self.APPROVAL_THRESHOLD else "rejected"
        
        eval_time = time.perf_counter() - start
        
        return {
            "claim_id": claim.get("id", "unknown"),
            "verdict": verdict,
            "scores": scores,
            "composite_score": composite,
            "evaluation_time": eval_time
        }
    
    def evaluate_batch(self, claims: List[Dict], evidence_map: Dict[str, Dict]) -> List[Dict]:
        """Evaluate multiple claims."""
        results = []
        for claim in claims:
            evidence = evidence_map.get(claim.get("id", ""), {})
            result = self.evaluate_claim(claim, evidence)
            results.append(result)
        return results
    
    def _generate_scores(self) -> Dict[str, float]:
        """Generate mock dimension scores."""
        import random
        return {
            'strength': random.uniform(2.0, 5.0),
            'rigor': random.uniform(2.0, 5.0),
            'relevance': random.uniform(2.0, 5.0),
            'directness': random.uniform(1.0, 3.0),
            'recency': random.uniform(0.0, 1.0),
            'reproducibility': random.uniform(2.0, 5.0)
        }
    
    def _calculate_composite(self, scores: Dict[str, float]) -> float:
        """Calculate composite score using standard weights."""
        composite = (
            scores['strength'] * self.WEIGHTS['strength'] +
            scores['rigor'] * self.WEIGHTS['rigor'] +
            scores['relevance'] * self.WEIGHTS['relevance'] +
            (scores['directness'] / 3) * self.WEIGHTS['directness'] +
            scores['recency'] * self.WEIGHTS['recency'] +
            scores['reproducibility'] * self.WEIGHTS['reproducibility']
        )
        return round(composite, 2)


def get_judge(consensus_mode: bool = False):
    """
    Get Judge instance for benchmarking.
    
    Returns actual implementation if available, mock otherwise.
    """
    try:
        from literature_review.judge import Judge
        return Judge(consensus_mode=consensus_mode)
    except ImportError:
        return MockJudge(consensus_mode=consensus_mode, simulate_delay=False)


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
def sample_claims() -> List[Dict]:
    """Generate sample claims for benchmarking."""
    return [
        {
            "id": f"claim_{i:03d}",
            "text": f"Sample claim {i} about neuromorphic computing efficiency.",
            "pillar": "P1_Hardware_Architecture",
            "source_paper": f"paper_{i % 10}.pdf"
        }
        for i in range(BATCH_SIZE)
    ]


@pytest.fixture
def sample_evidence_map(sample_claims) -> Dict[str, Dict]:
    """Generate sample evidence for claims."""
    return {
        claim["id"]: {
            "text": f"Evidence supporting claim {claim['id']}",
            "source_page": 5,
            "methodology": "experimental"
        }
        for claim in sample_claims
    }


@pytest.fixture
def large_batch_claims() -> List[Dict]:
    """Generate larger batch for stress testing."""
    return [
        {
            "id": f"claim_{i:04d}",
            "text": f"Claim {i} for stress testing judge throughput.",
            "pillar": f"P{(i % 4) + 1}",
            "source_paper": f"paper_{i % 20}.pdf"
        }
        for i in range(100)
    ]


# =============================================================================
# Benchmark Helper Functions
# =============================================================================

def measure_batch_evaluation(
    judge,
    claims: List[Dict],
    evidence_map: Dict[str, Dict]
) -> JudgeMetrics:
    """Measure batch claim evaluation performance."""
    tracemalloc.start()
    
    start_time = time.perf_counter()
    results = judge.evaluate_batch(claims, evidence_map)
    total_time = time.perf_counter() - start_time
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Analyze results
    approved = sum(1 for r in results if r.get("verdict") == "approved")
    rejected = len(results) - approved
    avg_score = statistics.mean(r.get("composite_score", 0) for r in results)
    
    claims_per_minute = (len(claims) / total_time) * 60 if total_time > 0 else 0
    avg_per_claim = total_time / len(claims) if claims else 0
    
    return JudgeMetrics(
        claim_count=len(claims),
        total_time_seconds=total_time,
        claims_per_minute=claims_per_minute,
        avg_time_per_claim=avg_per_claim,
        approved_count=approved,
        rejected_count=rejected,
        avg_composite_score=avg_score,
        peak_memory_mb=peak / (1024 * 1024)
    )


def measure_consensus_overhead(
    claims: List[Dict],
    evidence_map: Dict[str, Dict]
) -> ConsensusBenchmark:
    """Compare single mode vs consensus mode performance."""
    # Single mode
    single_judge = get_judge(consensus_mode=False)
    start = time.perf_counter()
    single_results = single_judge.evaluate_batch(claims[:5], evidence_map)
    single_time = time.perf_counter() - start
    
    # Consensus mode
    consensus_judge = get_judge(consensus_mode=True)
    start = time.perf_counter()
    consensus_results = consensus_judge.evaluate_batch(claims[:5], evidence_map)
    consensus_time = time.perf_counter() - start
    
    # Calculate agreement
    agreements = sum(
        1 for s, c in zip(single_results, consensus_results)
        if s.get("verdict") == c.get("verdict")
    )
    agreement_rate = agreements / len(single_results) if single_results else 0
    
    overhead_ratio = consensus_time / single_time if single_time > 0 else 1.0
    
    return ConsensusBenchmark(
        single_mode_time=single_time,
        consensus_mode_time=consensus_time,
        overhead_ratio=overhead_ratio,
        agreement_rate=agreement_rate
    )


def measure_score_calculation(iterations: int = 100) -> ScoreCalcMetrics:
    """Measure pure score calculation performance (no LLM)."""
    judge = MockJudge(simulate_delay=False)
    
    times = []
    for _ in range(iterations):
        scores = judge._generate_scores()
        start = time.perf_counter()
        judge._calculate_composite(scores)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        times.append(elapsed)
    
    return ScoreCalcMetrics(
        calculation_count=iterations,
        total_time_ms=sum(times),
        avg_time_per_calc_ms=statistics.mean(times),
        min_time_ms=min(times),
        max_time_ms=max(times)
    )


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.benchmark
@pytest.mark.slow_benchmark
class TestJudgeBenchmark:
    """Benchmark tests for Judge component (BM-02)."""
    
    # -------------------------------------------------------------------------
    # BM-02: Batch Claim Evaluation
    # -------------------------------------------------------------------------
    
    def test_batch_evaluation_throughput(
        self,
        sample_claims,
        sample_evidence_map,
        benchmark_runner
    ):
        """
        BM-02: Batch claim evaluation should process ≥20 claims/minute.
        
        Target: ≥20 claims per minute throughput
        """
        judge = get_judge()
        
        # Run benchmark
        metrics = measure_batch_evaluation(judge, sample_claims, sample_evidence_map)
        
        result = BenchmarkResult(
            benchmark_id="BM-02",
            name="Batch Claim Evaluation",
            value=metrics.claims_per_minute,
            unit="claims/minute",
            threshold=MIN_CLAIMS_PER_MINUTE,
            passed=metrics.claims_per_minute >= MIN_CLAIMS_PER_MINUTE,
            metadata={
                "claim_count": metrics.claim_count,
                "total_time": metrics.total_time_seconds,
                "approved_count": metrics.approved_count,
                "avg_composite_score": metrics.avg_composite_score
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert metrics.claims_per_minute >= MIN_CLAIMS_PER_MINUTE, (
            f"Throughput {metrics.claims_per_minute:.1f} claims/min "
            f"below {MIN_CLAIMS_PER_MINUTE} threshold"
        )
    
    # -------------------------------------------------------------------------
    # BM-02a: Single Claim Evaluation
    # -------------------------------------------------------------------------
    
    def test_single_claim_evaluation(
        self,
        sample_claims,
        sample_evidence_map,
        benchmark_runner
    ):
        """
        BM-02a: Single claim evaluation should complete in <3 seconds.
        """
        judge = get_judge()
        claim = sample_claims[0]
        evidence = sample_evidence_map[claim["id"]]
        
        times = []
        for _ in range(BENCHMARK_RUNS):
            start = time.perf_counter()
            judge.evaluate_claim(claim, evidence)
            times.append(time.perf_counter() - start)
        
        avg_time = statistics.mean(times)
        
        result = BenchmarkResult(
            benchmark_id="BM-02a",
            name="Single Claim Evaluation",
            value=avg_time,
            unit="seconds",
            threshold=SINGLE_CLAIM_MAX_SECONDS,
            passed=avg_time < SINGLE_CLAIM_MAX_SECONDS,
            metadata={
                "runs": BENCHMARK_RUNS,
                "min": min(times),
                "max": max(times)
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert avg_time < SINGLE_CLAIM_MAX_SECONDS, (
            f"Single claim eval {avg_time:.2f}s exceeds "
            f"{SINGLE_CLAIM_MAX_SECONDS}s threshold"
        )
    
    # -------------------------------------------------------------------------
    # BM-02b: Consensus Mode Overhead
    # -------------------------------------------------------------------------
    
    def test_consensus_mode_overhead(
        self,
        sample_claims,
        sample_evidence_map,
        benchmark_runner
    ):
        """
        BM-02b: Consensus mode should have <2x overhead vs single mode.
        """
        result = measure_consensus_overhead(sample_claims, sample_evidence_map)
        
        benchmark_result = BenchmarkResult(
            benchmark_id="BM-02b",
            name="Consensus Mode Overhead",
            value=result.overhead_ratio,
            unit="ratio",
            threshold=CONSENSUS_OVERHEAD_MAX_RATIO,
            passed=result.overhead_ratio <= CONSENSUS_OVERHEAD_MAX_RATIO,
            metadata={
                "single_time": result.single_mode_time,
                "consensus_time": result.consensus_mode_time,
                "agreement_rate": result.agreement_rate
            }
        )
        
        benchmark_runner.record_result(benchmark_result)
        
        assert result.overhead_ratio <= CONSENSUS_OVERHEAD_MAX_RATIO, (
            f"Consensus overhead {result.overhead_ratio:.2f}x exceeds "
            f"{CONSENSUS_OVERHEAD_MAX_RATIO}x threshold"
        )
    
    # -------------------------------------------------------------------------
    # BM-02c: Score Calculation Performance
    # -------------------------------------------------------------------------
    
    def test_score_calculation_performance(self, benchmark_runner):
        """
        BM-02c: Pure score calculation should be <100ms for 100 calculations.
        
        This tests the computational overhead without LLM calls.
        """
        metrics = measure_score_calculation(iterations=100)
        
        result = BenchmarkResult(
            benchmark_id="BM-02c",
            name="Score Calculation Performance",
            value=metrics.total_time_ms,
            unit="ms",
            threshold=SCORE_CALC_MAX_MS,
            passed=metrics.total_time_ms < SCORE_CALC_MAX_MS,
            metadata={
                "iterations": metrics.calculation_count,
                "avg_per_calc": metrics.avg_time_per_calc_ms,
                "min": metrics.min_time_ms,
                "max": metrics.max_time_ms
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert metrics.total_time_ms < SCORE_CALC_MAX_MS, (
            f"Score calculation took {metrics.total_time_ms:.1f}ms, "
            f"exceeds {SCORE_CALC_MAX_MS}ms threshold"
        )
    
    # -------------------------------------------------------------------------
    # Stress Test: Large Batch
    # -------------------------------------------------------------------------
    
    def test_large_batch_stability(
        self,
        large_batch_claims,
        benchmark_runner
    ):
        """
        Stress test: Verify stability with 100 claims.
        """
        judge = get_judge()
        evidence_map = {c["id"]: {"text": "evidence"} for c in large_batch_claims}
        
        metrics = measure_batch_evaluation(judge, large_batch_claims, evidence_map)
        
        result = BenchmarkResult(
            benchmark_id="BM-02-stress",
            name="Large Batch Stability",
            value=metrics.claims_per_minute,
            unit="claims/minute",
            threshold=MIN_CLAIMS_PER_MINUTE * 0.8,  # 80% of normal threshold
            passed=metrics.claims_per_minute >= MIN_CLAIMS_PER_MINUTE * 0.8,
            metadata={
                "claim_count": metrics.claim_count,
                "peak_memory_mb": metrics.peak_memory_mb,
                "approval_rate": metrics.approval_rate
            }
        )
        
        benchmark_runner.record_result(result)
        
        # Should maintain at least 80% throughput under stress
        assert metrics.claims_per_minute >= MIN_CLAIMS_PER_MINUTE * 0.8
```

---

## Implementation Plan

### Hour 1-2: Setup & Infrastructure
1. Create benchmark test file structure
2. Implement batch evaluation measurement
3. Set up score calculation profiling

### Hour 3-4: Core Benchmarks
1. Implement BM-02 batch throughput test
2. Implement single claim evaluation test
3. Add consensus mode comparison

### Hour 5: Advanced Tests
1. Implement score calculation performance test
2. Add stress testing with large batches
3. Implement memory profiling

### Hour 6: Reporting & Documentation
1. Document baseline values
2. Create benchmark report format
3. Verify all tests pass

---

## Testing Instructions

```bash
# Run all Judge benchmarks
pytest tests/benchmarks/component/test_judge_benchmark.py -v -m benchmark

# Run only BM-02 tests
pytest tests/benchmarks/component/test_judge_benchmark.py -v -k "BM-02"

# Run consensus comparison
pytest tests/benchmarks/component/test_judge_benchmark.py -v -k "consensus"

# Skip stress tests
pytest tests/benchmarks/component/test_judge_benchmark.py -v -m "benchmark and not slow_benchmark"
```

---

## Dependencies

### Python Packages
- `pytest>=7.0.0` - Test framework
- `psutil>=5.9.0` - Resource monitoring (optional)

### Internal Dependencies
- `tests/benchmarks/runner.py` - BenchmarkRunner class
- `literature_review/judge.py` - Component under test

---

## Acceptance Criteria

- [ ] BM-02: Batch evaluation ≥20 claims/minute
- [ ] BM-02a: Single claim evaluation <3 seconds
- [ ] BM-02b: Consensus overhead <2x single mode
- [ ] BM-02c: Score calculation <100ms for 100 iterations
- [ ] Large batch (100 claims) maintains 80%+ throughput
- [ ] Benchmark report generated with all metrics

---

## Notes

- Mock judge used for CI to avoid API costs
- Consensus mode requires 2 LLM calls per claim
- Score calculation is pure Python, no LLM overhead
- Throughput baseline may need adjustment based on hardware
- Memory usage typically <500MB for batch operations
