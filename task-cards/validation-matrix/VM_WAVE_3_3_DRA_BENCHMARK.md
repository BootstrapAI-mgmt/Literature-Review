# Task Card: DRA Benchmark

**Task ID:** VM-W3-3  
**Wave:** 3 (Component Benchmarks)  
**Priority:** MEDIUM  
**Estimated Effort:** 6 hours  
**Status:** Not Started  
**Dependencies:** VM-W0-1  
**Blocks:** VM-W4-1, VM-W5-1  
**Validation IDs:** BM-03

---

## Objective

Establish performance benchmarks for the Deep Review Agent (DRA) component, measuring deep analysis latency, document re-read efficiency, and batch processing performance under controlled conditions.

## Background

The DRA is responsible for:
- Re-analyzing rejected claims for potential recovery
- Deep document analysis to find additional evidence
- Providing detailed rationale for recovery decisions
- Operating as an "appeal" mechanism in the pipeline

Performance benchmarks ensure the component meets operational requirements:
- **BM-03**: Deep analysis per claim should complete in <30 seconds

## Success Criteria

- [ ] BM-03: Deep analysis <30s per claim
- [ ] Document re-read efficiency measured
- [ ] Batch processing performance profiled
- [ ] Recovery rate stability verified
- [ ] Memory usage during deep analysis tracked

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| BM-03 | Deep Analysis Time | 1 rejected claim | Analysis complete | <30 seconds |
| BM-03a | Batch DRA | 10 rejected claims | All analyzed | Baseline throughput |
| BM-03b | Re-read Efficiency | Same document, 2nd pass | Efficiency ratio | <50% of first pass time |
| BM-03c | Recovery Stability | 20 claims × 3 runs | Consistent rate | <5% variance in recovery rate |

---

## Deliverables

### 1. Benchmark Test Implementation

**File:** `tests/benchmarks/component/test_dra_benchmark.py`

```python
"""
Deep Review Agent (DRA) Component Benchmark Tests

Validates BM-03 from the validation matrix.
Measures performance characteristics of the DRA component.
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

# BM-03 thresholds
SINGLE_CLAIM_MAX_SECONDS = 30.0
REREAD_EFFICIENCY_TARGET = 0.5  # <50% of first pass time
RECOVERY_RATE_VARIANCE_MAX = 0.05  # <5% variance

# Benchmark parameters
WARMUP_RUNS = 1
BENCHMARK_RUNS = 3
BATCH_SIZE = 10
STABILITY_RUNS = 3


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class DRAMetrics:
    """Metrics captured during DRA benchmark."""
    claim_id: str
    total_time_seconds: float
    evidence_found: bool
    recovery_recommended: bool
    
    # Analysis breakdown
    document_read_time: float
    analysis_time: float
    reasoning_time: float
    
    # Output metrics
    new_evidence_count: int
    confidence_score: float
    
    # Resource metrics
    peak_memory_mb: float


@dataclass
class BatchDRAMetrics:
    """Metrics for batch DRA processing."""
    total_claims: int
    total_time_seconds: float
    claims_per_minute: float
    
    recovered_count: int
    not_recovered_count: int
    recovery_rate: float
    
    avg_time_per_claim: float
    peak_memory_mb: float


@dataclass
class RereadEfficiency:
    """Metrics for document re-read efficiency."""
    first_pass_time: float
    second_pass_time: float
    efficiency_ratio: float  # second / first, lower is better
    cache_hit_rate: float


@dataclass
class StabilityResult:
    """Result of recovery rate stability test."""
    recovery_rates: List[float]
    mean_rate: float
    std_dev: float
    variance_percent: float
    is_stable: bool


# =============================================================================
# Mock DRA (for isolated benchmarking)
# =============================================================================

class MockDRA:
    """
    Mock Deep Review Agent for benchmark testing.
    
    In production, import the actual DeepReviewAgent class.
    This mock simulates realistic timing and recovery patterns.
    """
    
    def __init__(self, simulate_delay: bool = True):
        self.simulate_delay = simulate_delay
        self.document_cache = {}  # Simulates document caching
    
    def analyze_rejected_claim(
        self,
        claim: Dict,
        original_evidence: Dict,
        source_document: str
    ) -> Dict:
        """Perform deep analysis on a rejected claim."""
        start = time.perf_counter()
        
        # Document read phase
        doc_read_start = time.perf_counter()
        is_cached = source_document in self.document_cache
        if self.simulate_delay:
            if is_cached:
                time.sleep(0.1)  # Cache hit
            else:
                time.sleep(0.5)  # Full document read
                self.document_cache[source_document] = True
        doc_read_time = time.perf_counter() - doc_read_start
        
        # Analysis phase
        analysis_start = time.perf_counter()
        if self.simulate_delay:
            time.sleep(0.8)  # LLM analysis
        analysis_time = time.perf_counter() - analysis_start
        
        # Reasoning phase
        reasoning_start = time.perf_counter()
        if self.simulate_delay:
            time.sleep(0.3)  # Generate rationale
        reasoning_time = time.perf_counter() - reasoning_start
        
        total_time = time.perf_counter() - start
        
        # Simulate recovery decision (40-50% recovery rate)
        import random
        recovery_recommended = random.random() < 0.45
        
        return {
            "claim_id": claim.get("id", "unknown"),
            "recovery_recommended": recovery_recommended,
            "new_evidence": [
                {"text": "Additional evidence found", "relevance": 0.85}
            ] if recovery_recommended else [],
            "rationale": "Deep analysis found additional supporting evidence" if recovery_recommended else "No additional evidence found",
            "confidence": random.uniform(0.6, 0.95),
            "timing": {
                "document_read": doc_read_time,
                "analysis": analysis_time,
                "reasoning": reasoning_time,
                "total": total_time
            },
            "cache_hit": is_cached
        }
    
    def analyze_batch(
        self,
        claims: List[Dict],
        evidence_map: Dict[str, Dict],
        document_map: Dict[str, str]
    ) -> List[Dict]:
        """Analyze batch of rejected claims."""
        results = []
        for claim in claims:
            claim_id = claim.get("id", "")
            evidence = evidence_map.get(claim_id, {})
            document = document_map.get(claim_id, "default_doc.pdf")
            result = self.analyze_rejected_claim(claim, evidence, document)
            results.append(result)
        return results
    
    def clear_cache(self):
        """Clear document cache for fresh analysis."""
        self.document_cache = {}


def get_dra():
    """
    Get DRA instance for benchmarking.
    
    Returns actual implementation if available, mock otherwise.
    """
    try:
        from literature_review.deep_reviewer import DeepReviewAgent
        return DeepReviewAgent()
    except ImportError:
        return MockDRA(simulate_delay=False)


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
def rejected_claims() -> List[Dict]:
    """Generate sample rejected claims for DRA testing."""
    return [
        {
            "id": f"rejected_{i:03d}",
            "text": f"Claim {i} that was initially rejected by Judge.",
            "pillar": f"P{(i % 4) + 1}",
            "original_verdict": "rejected",
            "original_score": 2.5 + (i % 10) * 0.05,
            "source_paper": f"paper_{i % 5}.pdf"
        }
        for i in range(BATCH_SIZE)
    ]


@pytest.fixture
def evidence_map(rejected_claims) -> Dict[str, Dict]:
    """Generate original evidence for rejected claims."""
    return {
        claim["id"]: {
            "text": f"Original evidence for {claim['id']}",
            "pages": [5, 7],
            "relevance_score": 0.4
        }
        for claim in rejected_claims
    }


@pytest.fixture
def document_map(rejected_claims) -> Dict[str, str]:
    """Map claims to their source documents."""
    return {
        claim["id"]: claim["source_paper"]
        for claim in rejected_claims
    }


@pytest.fixture
def stability_claims() -> List[Dict]:
    """Generate claims for stability testing."""
    return [
        {
            "id": f"stability_{i:03d}",
            "text": f"Stability test claim {i}",
            "pillar": "P1",
            "source_paper": f"paper_{i % 3}.pdf"
        }
        for i in range(20)
    ]


# =============================================================================
# Benchmark Helper Functions
# =============================================================================

def measure_single_analysis(
    dra,
    claim: Dict,
    evidence: Dict,
    document: str
) -> DRAMetrics:
    """Measure single claim deep analysis."""
    tracemalloc.start()
    
    result = dra.analyze_rejected_claim(claim, evidence, document)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    timing = result.get("timing", {})
    
    return DRAMetrics(
        claim_id=claim.get("id", "unknown"),
        total_time_seconds=timing.get("total", 0),
        evidence_found=len(result.get("new_evidence", [])) > 0,
        recovery_recommended=result.get("recovery_recommended", False),
        document_read_time=timing.get("document_read", 0),
        analysis_time=timing.get("analysis", 0),
        reasoning_time=timing.get("reasoning", 0),
        new_evidence_count=len(result.get("new_evidence", [])),
        confidence_score=result.get("confidence", 0),
        peak_memory_mb=peak / (1024 * 1024)
    )


def measure_batch_analysis(
    dra,
    claims: List[Dict],
    evidence_map: Dict[str, Dict],
    document_map: Dict[str, str]
) -> BatchDRAMetrics:
    """Measure batch DRA processing."""
    tracemalloc.start()
    
    start = time.perf_counter()
    results = dra.analyze_batch(claims, evidence_map, document_map)
    total_time = time.perf_counter() - start
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    recovered = sum(1 for r in results if r.get("recovery_recommended", False))
    recovery_rate = recovered / len(results) if results else 0
    
    return BatchDRAMetrics(
        total_claims=len(claims),
        total_time_seconds=total_time,
        claims_per_minute=(len(claims) / total_time) * 60 if total_time > 0 else 0,
        recovered_count=recovered,
        not_recovered_count=len(results) - recovered,
        recovery_rate=recovery_rate,
        avg_time_per_claim=total_time / len(claims) if claims else 0,
        peak_memory_mb=peak / (1024 * 1024)
    )


def measure_reread_efficiency(
    dra,
    claim: Dict,
    evidence: Dict,
    document: str
) -> RereadEfficiency:
    """Measure document re-read efficiency with caching."""
    # Clear cache for fresh first pass
    dra.clear_cache()
    
    # First pass (cold cache)
    start = time.perf_counter()
    result1 = dra.analyze_rejected_claim(claim, evidence, document)
    first_time = time.perf_counter() - start
    
    # Second pass (warm cache)
    start = time.perf_counter()
    result2 = dra.analyze_rejected_claim(claim, evidence, document)
    second_time = time.perf_counter() - start
    
    efficiency_ratio = second_time / first_time if first_time > 0 else 1.0
    cache_hit = result2.get("cache_hit", False)
    
    return RereadEfficiency(
        first_pass_time=first_time,
        second_pass_time=second_time,
        efficiency_ratio=efficiency_ratio,
        cache_hit_rate=1.0 if cache_hit else 0.0
    )


def measure_recovery_stability(
    dra,
    claims: List[Dict],
    evidence_map: Dict[str, Dict],
    document_map: Dict[str, str],
    runs: int = 3
) -> StabilityResult:
    """Measure stability of recovery rate across multiple runs."""
    recovery_rates = []
    
    for _ in range(runs):
        dra.clear_cache()
        results = dra.analyze_batch(claims, evidence_map, document_map)
        recovered = sum(1 for r in results if r.get("recovery_recommended", False))
        rate = recovered / len(results) if results else 0
        recovery_rates.append(rate)
    
    mean_rate = statistics.mean(recovery_rates)
    std_dev = statistics.stdev(recovery_rates) if len(recovery_rates) > 1 else 0
    variance_percent = (std_dev / mean_rate) * 100 if mean_rate > 0 else 0
    
    return StabilityResult(
        recovery_rates=recovery_rates,
        mean_rate=mean_rate,
        std_dev=std_dev,
        variance_percent=variance_percent,
        is_stable=variance_percent < RECOVERY_RATE_VARIANCE_MAX * 100
    )


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.benchmark
@pytest.mark.slow_benchmark
class TestDRABenchmark:
    """Benchmark tests for DRA component (BM-03)."""
    
    # -------------------------------------------------------------------------
    # BM-03: Single Claim Deep Analysis
    # -------------------------------------------------------------------------
    
    def test_single_claim_analysis_time(
        self,
        rejected_claims,
        evidence_map,
        document_map,
        benchmark_runner
    ):
        """
        BM-03: Deep analysis should complete in <30 seconds per claim.
        """
        dra = get_dra()
        claim = rejected_claims[0]
        evidence = evidence_map[claim["id"]]
        document = document_map[claim["id"]]
        
        times = []
        for _ in range(BENCHMARK_RUNS):
            dra.clear_cache()
            metrics = measure_single_analysis(dra, claim, evidence, document)
            times.append(metrics.total_time_seconds)
        
        avg_time = statistics.mean(times)
        
        result = BenchmarkResult(
            benchmark_id="BM-03",
            name="Single Claim Deep Analysis",
            value=avg_time,
            unit="seconds",
            threshold=SINGLE_CLAIM_MAX_SECONDS,
            passed=avg_time < SINGLE_CLAIM_MAX_SECONDS,
            metadata={
                "runs": BENCHMARK_RUNS,
                "min": min(times),
                "max": max(times),
                "std_dev": statistics.stdev(times) if len(times) > 1 else 0
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert avg_time < SINGLE_CLAIM_MAX_SECONDS, (
            f"Deep analysis took {avg_time:.2f}s, "
            f"exceeds {SINGLE_CLAIM_MAX_SECONDS}s threshold"
        )
    
    # -------------------------------------------------------------------------
    # BM-03a: Batch DRA Processing
    # -------------------------------------------------------------------------
    
    def test_batch_processing_throughput(
        self,
        rejected_claims,
        evidence_map,
        document_map,
        benchmark_runner
    ):
        """
        BM-03a: Measure batch DRA processing throughput.
        """
        dra = get_dra()
        dra.clear_cache()
        
        metrics = measure_batch_analysis(dra, rejected_claims, evidence_map, document_map)
        
        result = BenchmarkResult(
            benchmark_id="BM-03a",
            name="Batch DRA Processing",
            value=metrics.claims_per_minute,
            unit="claims/minute",
            threshold=2.0,  # At least 2 claims/min (30s each)
            passed=metrics.claims_per_minute >= 2.0,
            metadata={
                "total_claims": metrics.total_claims,
                "total_time": metrics.total_time_seconds,
                "recovery_rate": metrics.recovery_rate,
                "peak_memory_mb": metrics.peak_memory_mb
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert metrics.claims_per_minute >= 2.0, (
            f"Batch throughput {metrics.claims_per_minute:.2f} claims/min too low"
        )
    
    # -------------------------------------------------------------------------
    # BM-03b: Document Re-read Efficiency
    # -------------------------------------------------------------------------
    
    def test_document_reread_efficiency(
        self,
        rejected_claims,
        evidence_map,
        document_map,
        benchmark_runner
    ):
        """
        BM-03b: Second pass should be <50% of first pass time.
        
        Tests document caching effectiveness.
        """
        dra = get_dra()
        claim = rejected_claims[0]
        evidence = evidence_map[claim["id"]]
        document = document_map[claim["id"]]
        
        efficiency = measure_reread_efficiency(dra, claim, evidence, document)
        
        result = BenchmarkResult(
            benchmark_id="BM-03b",
            name="Document Re-read Efficiency",
            value=efficiency.efficiency_ratio,
            unit="ratio",
            threshold=REREAD_EFFICIENCY_TARGET,
            passed=efficiency.efficiency_ratio <= REREAD_EFFICIENCY_TARGET,
            metadata={
                "first_pass_time": efficiency.first_pass_time,
                "second_pass_time": efficiency.second_pass_time,
                "cache_hit_rate": efficiency.cache_hit_rate
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert efficiency.efficiency_ratio <= REREAD_EFFICIENCY_TARGET, (
            f"Re-read efficiency {efficiency.efficiency_ratio:.1%} "
            f"exceeds {REREAD_EFFICIENCY_TARGET:.0%} threshold"
        )
    
    # -------------------------------------------------------------------------
    # BM-03c: Recovery Rate Stability
    # -------------------------------------------------------------------------
    
    def test_recovery_rate_stability(
        self,
        stability_claims,
        benchmark_runner
    ):
        """
        BM-03c: Recovery rate should be stable (<5% variance).
        
        Ensures consistent decision-making across runs.
        """
        dra = get_dra()
        evidence_map = {c["id"]: {"text": "evidence"} for c in stability_claims}
        document_map = {c["id"]: c["source_paper"] for c in stability_claims}
        
        stability = measure_recovery_stability(
            dra, stability_claims, evidence_map, document_map,
            runs=STABILITY_RUNS
        )
        
        result = BenchmarkResult(
            benchmark_id="BM-03c",
            name="Recovery Rate Stability",
            value=stability.variance_percent,
            unit="percent",
            threshold=RECOVERY_RATE_VARIANCE_MAX * 100,
            passed=stability.is_stable,
            metadata={
                "runs": STABILITY_RUNS,
                "recovery_rates": stability.recovery_rates,
                "mean_rate": stability.mean_rate,
                "std_dev": stability.std_dev
            }
        )
        
        benchmark_runner.record_result(result)
        
        assert stability.is_stable, (
            f"Recovery rate variance {stability.variance_percent:.1f}% "
            f"exceeds {RECOVERY_RATE_VARIANCE_MAX * 100:.0f}% threshold. "
            f"Rates: {stability.recovery_rates}"
        )
    
    # -------------------------------------------------------------------------
    # Timing Breakdown Analysis
    # -------------------------------------------------------------------------
    
    def test_timing_breakdown(
        self,
        rejected_claims,
        evidence_map,
        document_map,
        benchmark_runner
    ):
        """
        Analyze where time is spent during deep analysis.
        """
        dra = get_dra()
        dra.clear_cache()
        
        claim = rejected_claims[0]
        metrics = measure_single_analysis(
            dra, claim, evidence_map[claim["id"]], document_map[claim["id"]]
        )
        
        result = BenchmarkResult(
            benchmark_id="BM-03-breakdown",
            name="Timing Breakdown",
            value=metrics.total_time_seconds,
            unit="seconds",
            threshold=SINGLE_CLAIM_MAX_SECONDS,
            passed=True,  # Informational
            metadata={
                "document_read_time": metrics.document_read_time,
                "analysis_time": metrics.analysis_time,
                "reasoning_time": metrics.reasoning_time,
                "document_read_pct": (metrics.document_read_time / metrics.total_time_seconds) * 100 if metrics.total_time_seconds > 0 else 0,
                "analysis_pct": (metrics.analysis_time / metrics.total_time_seconds) * 100 if metrics.total_time_seconds > 0 else 0
            }
        )
        
        benchmark_runner.record_result(result)
```

---

## Implementation Plan

### Hour 1-2: Setup & Infrastructure
1. Create benchmark test file structure
2. Implement single analysis measurement
3. Set up document caching simulation

### Hour 3-4: Core Benchmarks
1. Implement BM-03 single claim test
2. Implement batch processing measurement
3. Add timing breakdown analysis

### Hour 5: Efficiency & Stability Tests
1. Implement re-read efficiency test
2. Implement recovery rate stability test
3. Add variance analysis

### Hour 6: Reporting & Documentation
1. Document baseline values
2. Create benchmark report format
3. Verify all tests pass

---

## Testing Instructions

```bash
# Run all DRA benchmarks
pytest tests/benchmarks/component/test_dra_benchmark.py -v -m benchmark

# Run only BM-03 tests
pytest tests/benchmarks/component/test_dra_benchmark.py -v -k "BM-03"

# Run stability tests
pytest tests/benchmarks/component/test_dra_benchmark.py -v -k "stability"

# Run with detailed timing
pytest tests/benchmarks/component/test_dra_benchmark.py -v --durations=10
```

---

## Dependencies

### Python Packages
- `pytest>=7.0.0` - Test framework
- `psutil>=5.9.0` - Resource monitoring (optional)

### Internal Dependencies
- `tests/benchmarks/runner.py` - BenchmarkRunner class
- `literature_review/deep_reviewer.py` - Component under test

---

## Acceptance Criteria

- [ ] BM-03: Deep analysis <30s per claim
- [ ] BM-03a: Batch throughput ≥2 claims/minute
- [ ] BM-03b: Re-read efficiency <50% of first pass
- [ ] BM-03c: Recovery rate variance <5%
- [ ] Timing breakdown captured for optimization insights
- [ ] Benchmark report generated with all metrics

---

## Notes

- DRA is the most time-intensive pipeline component
- Document caching critical for batch efficiency
- Recovery rate ~40-50% expected for realistic rejected claims
- LLM calls dominate timing in analysis phase
- Consider parallel document processing for optimization
