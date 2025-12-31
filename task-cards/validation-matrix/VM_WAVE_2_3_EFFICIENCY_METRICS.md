# Task Card: Efficiency Metrics Tests

**Task ID:** VM-W2-3  
**Wave:** 2 (Accuracy & Efficiency)  
**Priority:** HIGH  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W0-1  
**Blocks:** VM-W4-1  
**Validation IDs:** EV-01, EV-02, EV-03, EV-07, FV-08 *(FV-08 added per review)*

---

## Objective

Validate pipeline efficiency metrics including full run time, incremental mode speedup, cache hit rates, and checkpoint recovery time.

## Background

Efficiency validation ensures the pipeline meets operational requirements:
- **EV-01: Full Run Time** - Complete 100-paper pipeline run in <2 hours
- **EV-02: Incremental Speedup** - Incremental mode is 60-80% faster than full mode
- **EV-03: Cache Hit Rate** - ≥70% cache hits for repeated evaluations
- **EV-07: Checkpoint Recovery** - Resume from checkpoint in <30 seconds
- **FV-08: Incremental Detection** - Correctly detect new/modified/unchanged papers (100% accuracy) *(added per review)*

These metrics directly impact:
1. User experience (waiting time)
2. Operational costs (compute time)
3. Reliability (recovery from failures)

## Success Criteria

- [ ] EV-01: 100-paper pipeline completes in <2 hours
- [ ] EV-02: Incremental mode achieves 60-80% speedup
- [ ] EV-03: Cache hit rate ≥70% on repeated runs
- [ ] EV-07: Checkpoint recovery completes in <30 seconds
- [ ] FV-08: Incremental change detection 100% accurate *(added per review)*
- [ ] Efficiency baselines captured for regression tracking

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| EV-01 | Full Run Time | 100 test papers | `duration < 7200s` | Complete in <2 hours |
| EV-02 | Incremental Speedup | Pre-processed corpus | `speedup >= 0.60` | 60-80% faster |
| EV-03 | Cache Hit Rate | Duplicate claim set | `hit_rate >= 0.70` | ≥70% cache hits |
| EV-07 | Checkpoint Recovery | Interrupted state | `resume_time < 30s` | Resume in <30s |
| FV-08 | Incremental Detection | Mixed corpus (new/modified/unchanged) | `detection_accuracy = 1.0` | 100% accurate change detection | *(added per review)*

---

## Deliverables

### 1. Test Implementation

**File:** `tests/validation/efficiency/test_efficiency_metrics.py`

```python
"""
Efficiency Metrics Validation Tests

Validates EV-01, EV-02, EV-03, EV-07 from the validation matrix.
Measures pipeline performance against operational thresholds.
"""

import pytest
import time
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

from tests.validation.base import (
    EfficiencyValidationTestCase,
    ValidationResult,
    TimingContext
)
from tests.benchmarks.runner import BenchmarkRunner
from tests.benchmarks.profiler import HardwareProfiler


@dataclass
class EfficiencyMetric:
    """Container for efficiency measurement results."""
    metric_id: str
    metric_name: str
    value: float
    unit: str
    threshold: float
    passed: bool
    measured_at: str = field(default_factory=lambda: datetime.now().isoformat())
    environment: Dict = field(default_factory=dict)
    
    @property
    def margin(self) -> float:
        """Calculate margin relative to threshold."""
        if "time" in self.unit.lower() or "rate" in self.metric_name.lower():
            # For time metrics, lower is better
            return self.threshold - self.value
        return self.value - self.threshold
    
    def to_dict(self) -> Dict:
        return {
            "metric_id": self.metric_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "threshold": self.threshold,
            "passed": self.passed,
            "margin": self.margin,
            "measured_at": self.measured_at,
            "environment": self.environment
        }


class EfficiencyMetricsTracker:
    """Track and store efficiency metrics over time."""
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path(
            "tests/validation/baselines/efficiency_metrics.json"
        )
        self.metrics: List[EfficiencyMetric] = []
    
    def record(self, metric: EfficiencyMetric):
        """Record a new efficiency metric."""
        self.metrics.append(metric)
        self._persist()
    
    def _persist(self):
        """Save metrics to disk."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing = []
        if self.storage_path.exists():
            existing = json.loads(self.storage_path.read_text())
        
        # Append new metrics
        for m in self.metrics:
            existing.append(m.to_dict())
        
        self.storage_path.write_text(json.dumps(existing, indent=2))
        self.metrics = []  # Clear after persisting
    
    def get_baseline(self, metric_id: str) -> Optional[float]:
        """Get the baseline value for a metric."""
        if not self.storage_path.exists():
            return None
        
        data = json.loads(self.storage_path.read_text())
        for entry in reversed(data):
            if entry.get("metric_id") == metric_id and entry.get("passed"):
                return entry.get("value")
        
        return None
    
    def check_regression(
        self,
        metric_id: str,
        current_value: float,
        tolerance_percent: float = 10.0
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if current value represents a regression.
        
        Returns:
            (is_regression, regression_magnitude)
        """
        baseline = self.get_baseline(metric_id)
        if baseline is None:
            return (False, None)
        
        tolerance = baseline * tolerance_percent / 100
        
        # For time metrics, increase is regression
        if metric_id in ["EV-01", "EV-07"]:
            is_regression = current_value > baseline + tolerance
            magnitude = current_value - baseline if is_regression else None
        # For speedup/hit rate, decrease is regression
        else:
            is_regression = current_value < baseline - tolerance
            magnitude = baseline - current_value if is_regression else None
        
        return (is_regression, magnitude)


class TestPipelineRunTime(EfficiencyValidationTestCase):
    """
    EV-01: Full Pipeline Run Time Test
    
    Validates that processing 100 papers completes in under 2 hours.
    """
    
    TEST_ID = "EV-01"
    TEST_CATEGORY = "EV"
    TIME_THRESHOLD_SECONDS = 7200  # 2 hours
    
    @pytest.fixture
    def test_papers(self, tmp_path) -> List[Path]:
        """Generate 100 test paper files."""
        papers_dir = tmp_path / "test_papers"
        papers_dir.mkdir()
        
        for i in range(100):
            paper_path = papers_dir / f"test_paper_{i:03d}.pdf"
            # Create minimal test PDFs (or mock PDF paths)
            paper_path.write_bytes(self._generate_minimal_pdf(i))
        
        return list(papers_dir.glob("*.pdf"))
    
    @pytest.fixture
    def orchestrator_instance(self):
        """Create orchestrator instance for testing."""
        from pipeline_orchestrator import Orchestrator
        
        # Configure for test mode
        with patch.dict('os.environ', {'PIPELINE_TEST_MODE': 'true'}):
            orchestrator = Orchestrator(dry_run=True)
            yield orchestrator
    
    def _generate_minimal_pdf(self, index: int) -> bytes:
        """Generate minimal PDF content for testing."""
        # Minimal PDF structure
        content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 50 >>
stream
BT /F1 12 Tf 100 700 Td (Test Paper {index}) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
314
%%EOF"""
        return content.encode('latin-1')
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    @pytest.mark.slow
    def test_ev01_full_pipeline_time(self, orchestrator_instance, test_papers):
        """
        EV-01: Full pipeline run must complete in <2 hours for 100 papers.
        
        Note: This test is marked 'slow' and may be skipped in CI.
        For CI, use the mock-accelerated version below.
        """
        orchestrator = orchestrator_instance
        hardware_profile = HardwareProfiler.capture()
        
        start_time = time.perf_counter()
        
        # Run pipeline on 100 papers
        result = orchestrator.run_pipeline(
            input_files=test_papers,
            mode="full",
            max_papers=100
        )
        
        end_time = time.perf_counter()
        duration_seconds = end_time - start_time
        
        # Create efficiency metric
        metric = EfficiencyMetric(
            metric_id="EV-01",
            metric_name="full_pipeline_time",
            value=duration_seconds,
            unit="seconds",
            threshold=self.TIME_THRESHOLD_SECONDS,
            passed=duration_seconds < self.TIME_THRESHOLD_SECONDS,
            environment=hardware_profile.to_dict()
        )
        
        # Track metric
        tracker = EfficiencyMetricsTracker()
        tracker.record(metric)
        
        # Check for regression
        is_regression, magnitude = tracker.check_regression(
            "EV-01", duration_seconds
        )
        
        # Create validation result
        validation_result = ValidationResult(
            test_id="EV-01",
            test_name="Full Pipeline Run Time (100 papers)",
            passed=duration_seconds < self.TIME_THRESHOLD_SECONDS,
            actual_value=duration_seconds,
            expected_value=f"<{self.TIME_THRESHOLD_SECONDS}s",
            threshold=self.TIME_THRESHOLD_SECONDS,
            margin=self.TIME_THRESHOLD_SECONDS - duration_seconds,
            execution_time_ms=duration_seconds * 1000,
            metadata={
                "papers_processed": len(test_papers),
                "papers_per_minute": len(test_papers) / (duration_seconds / 60),
                "hardware_profile": hardware_profile.to_dict(),
                "is_regression": is_regression,
                "regression_magnitude": magnitude
            }
        )
        
        self.record_result(validation_result)
        
        print(f"\n{'='*60}")
        print(f"EV-01: Full Pipeline Run Time")
        print(f"{'='*60}")
        print(f"Duration: {duration_seconds:.1f}s ({duration_seconds/60:.1f} min)")
        print(f"Threshold: {self.TIME_THRESHOLD_SECONDS}s ({self.TIME_THRESHOLD_SECONDS/60:.0f} min)")
        print(f"Papers processed: {len(test_papers)}")
        print(f"Rate: {len(test_papers) / (duration_seconds / 60):.1f} papers/min")
        print(f"{'='*60}")
        
        assert duration_seconds < self.TIME_THRESHOLD_SECONDS, (
            f"EV-01 FAILED: Pipeline took {duration_seconds:.1f}s "
            f"(threshold: {self.TIME_THRESHOLD_SECONDS}s = 2 hours). "
            f"Processing rate: {len(test_papers) / (duration_seconds / 60):.1f} papers/min"
        )
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    def test_ev01_time_estimation(self, orchestrator_instance, test_papers):
        """
        EV-01 (Accelerated): Estimate full pipeline time from sample.
        
        Process 10 papers and extrapolate to 100.
        """
        orchestrator = orchestrator_instance
        sample_size = 10
        sample_papers = test_papers[:sample_size]
        
        start_time = time.perf_counter()
        
        # Run on sample
        result = orchestrator.run_pipeline(
            input_files=sample_papers,
            mode="full",
            max_papers=sample_size
        )
        
        end_time = time.perf_counter()
        sample_duration = end_time - start_time
        
        # Extrapolate to 100 papers (with 20% overhead for batching effects)
        extrapolated_duration = (sample_duration / sample_size) * 100 * 1.2
        
        validation_result = ValidationResult(
            test_id="EV-01-estimated",
            test_name="Full Pipeline Time (Estimated from sample)",
            passed=extrapolated_duration < self.TIME_THRESHOLD_SECONDS,
            actual_value=extrapolated_duration,
            expected_value=f"<{self.TIME_THRESHOLD_SECONDS}s",
            threshold=self.TIME_THRESHOLD_SECONDS,
            margin=self.TIME_THRESHOLD_SECONDS - extrapolated_duration,
            metadata={
                "sample_size": sample_size,
                "sample_duration": sample_duration,
                "extrapolation_factor": 1.2
            }
        )
        
        self.record_result(validation_result)
        
        assert extrapolated_duration < self.TIME_THRESHOLD_SECONDS, (
            f"EV-01 (estimated) FAILED: Extrapolated time {extrapolated_duration:.1f}s "
            f"exceeds threshold {self.TIME_THRESHOLD_SECONDS}s"
        )


class TestIncrementalSpeedup(EfficiencyValidationTestCase):
    """
    EV-02: Incremental Mode Speedup Test
    
    Validates that incremental mode is 60-80% faster than full mode.
    """
    
    TEST_ID = "EV-02"
    TEST_CATEGORY = "EV"
    SPEEDUP_MIN = 0.60  # At least 60% faster
    SPEEDUP_MAX = 0.80  # At most 80% faster (sanity check)
    
    @pytest.fixture
    def pre_processed_state(self, tmp_path):
        """
        Create pre-processed pipeline state.
        
        Simulates a previous full run with cached results.
        """
        state_dir = tmp_path / "pipeline_state"
        state_dir.mkdir()
        
        # Create cached claims
        claims_cache = state_dir / "claims_cache.json"
        claims_cache.write_text(json.dumps({
            f"paper_{i}": [
                {"claim_id": f"claim_{i}_{j}", "cached": True}
                for j in range(5)
            ]
            for i in range(50)
        }))
        
        # Create cached verdicts
        verdicts_cache = state_dir / "verdicts_cache.json"
        verdicts_cache.write_text(json.dumps({
            f"claim_{i}_{j}": {"verdict": "approved", "cached": True}
            for i in range(50) for j in range(5)
        }))
        
        return state_dir
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    def test_ev02_incremental_speedup(
        self,
        orchestrator_instance,
        test_papers,
        pre_processed_state
    ):
        """
        EV-02: Incremental mode must be 60-80% faster than full mode.
        
        Process:
        1. Run full mode on test corpus (measure time)
        2. Run incremental mode on same corpus (measure time)
        3. Calculate speedup percentage
        """
        orchestrator = orchestrator_instance
        sample_papers = test_papers[:20]  # Use 20 papers for reasonable test time
        
        # Full mode timing
        with TimingContext() as full_timer:
            orchestrator.run_pipeline(
                input_files=sample_papers,
                mode="full"
            )
        full_duration = full_timer.duration
        
        # Reset to use cache
        orchestrator.load_state(pre_processed_state)
        
        # Add some new papers to test incremental
        new_papers = sample_papers[-5:]  # Last 5 are "new"
        
        # Incremental mode timing
        with TimingContext() as incr_timer:
            orchestrator.run_pipeline(
                input_files=sample_papers,
                mode="incremental"
            )
        incremental_duration = incr_timer.duration
        
        # Calculate speedup
        speedup = 1.0 - (incremental_duration / full_duration) if full_duration > 0 else 0
        
        # Create metric
        metric = EfficiencyMetric(
            metric_id="EV-02",
            metric_name="incremental_speedup",
            value=speedup,
            unit="ratio",
            threshold=self.SPEEDUP_MIN,
            passed=self.SPEEDUP_MIN <= speedup <= self.SPEEDUP_MAX
        )
        
        tracker = EfficiencyMetricsTracker()
        tracker.record(metric)
        
        validation_result = ValidationResult(
            test_id="EV-02",
            test_name="Incremental Mode Speedup",
            passed=self.SPEEDUP_MIN <= speedup,
            actual_value=speedup,
            expected_value=f"{self.SPEEDUP_MIN:.0%}-{self.SPEEDUP_MAX:.0%}",
            threshold=self.SPEEDUP_MIN,
            margin=speedup - self.SPEEDUP_MIN,
            metadata={
                "full_duration": full_duration,
                "incremental_duration": incremental_duration,
                "papers_processed": len(sample_papers),
                "new_papers": len(new_papers),
                "cached_papers": len(sample_papers) - len(new_papers)
            }
        )
        
        self.record_result(validation_result)
        
        print(f"\n{'='*60}")
        print(f"EV-02: Incremental Speedup")
        print(f"{'='*60}")
        print(f"Full mode: {full_duration:.1f}s")
        print(f"Incremental mode: {incremental_duration:.1f}s")
        print(f"Speedup: {speedup:.1%}")
        print(f"Expected: {self.SPEEDUP_MIN:.0%}-{self.SPEEDUP_MAX:.0%}")
        print(f"{'='*60}")
        
        assert speedup >= self.SPEEDUP_MIN, (
            f"EV-02 FAILED: Incremental speedup {speedup:.1%} < "
            f"{self.SPEEDUP_MIN:.0%} minimum. "
            f"Full: {full_duration:.1f}s, Incremental: {incremental_duration:.1f}s"
        )


class TestCacheHitRate(EfficiencyValidationTestCase):
    """
    EV-03: Cache Hit Rate Test
    
    Validates that repeated evaluations achieve ≥70% cache hit rate.
    """
    
    TEST_ID = "EV-03"
    TEST_CATEGORY = "EV"
    CACHE_HIT_THRESHOLD = 0.70
    
    @pytest.fixture
    def cache_instance(self, tmp_path):
        """Create cache instance for testing."""
        from literature_review.cache.judge_cache import JudgeCache
        
        cache = JudgeCache(cache_dir=tmp_path / "judge_cache")
        return cache
    
    @pytest.fixture
    def test_claims(self) -> List[Dict]:
        """Generate test claims with some duplicates."""
        base_claims = [
            {
                "claim_id": f"claim_{i}",
                "claim_text": f"Test claim number {i} about neuromorphic computing",
                "evidence": f"Evidence {i}: Quantitative results show improvement."
            }
            for i in range(50)
        ]
        
        # Add 30 duplicates (for 60% duplicate rate)
        duplicates = base_claims[:30]
        
        return base_claims + duplicates  # 80 total, 30 duplicates
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    def test_ev03_cache_hit_rate(self, cache_instance, test_claims):
        """
        EV-03: Cache hit rate must be ≥70% for repeated evaluations.
        
        Process:
        1. First pass: Evaluate all claims (populating cache)
        2. Second pass: Evaluate same claims (should hit cache)
        3. Calculate hit rate
        """
        cache = cache_instance
        
        # First pass - populate cache
        cache_stats_before = {"hits": 0, "misses": 0}
        
        for claim in test_claims[:50]:  # Unique claims
            cache_key = cache.make_key(claim)
            
            # Check cache
            cached = cache.get(cache_key)
            if cached:
                cache_stats_before["hits"] += 1
            else:
                cache_stats_before["misses"] += 1
                # Simulate evaluation and cache storage
                result = {"verdict": "approved", "composite_score": 3.5}
                cache.set(cache_key, result)
        
        # Second pass - should hit cache
        cache_stats_after = {"hits": 0, "misses": 0}
        
        for claim in test_claims:  # All 80 claims
            cache_key = cache.make_key(claim)
            cached = cache.get(cache_key)
            
            if cached:
                cache_stats_after["hits"] += 1
            else:
                cache_stats_after["misses"] += 1
        
        # Calculate overall hit rate
        total_lookups = cache_stats_after["hits"] + cache_stats_after["misses"]
        hit_rate = cache_stats_after["hits"] / total_lookups if total_lookups > 0 else 0
        
        metric = EfficiencyMetric(
            metric_id="EV-03",
            metric_name="cache_hit_rate",
            value=hit_rate,
            unit="ratio",
            threshold=self.CACHE_HIT_THRESHOLD,
            passed=hit_rate >= self.CACHE_HIT_THRESHOLD
        )
        
        tracker = EfficiencyMetricsTracker()
        tracker.record(metric)
        
        validation_result = ValidationResult(
            test_id="EV-03",
            test_name="Cache Hit Rate",
            passed=hit_rate >= self.CACHE_HIT_THRESHOLD,
            actual_value=hit_rate,
            expected_value=f"≥{self.CACHE_HIT_THRESHOLD:.0%}",
            threshold=self.CACHE_HIT_THRESHOLD,
            margin=hit_rate - self.CACHE_HIT_THRESHOLD,
            metadata={
                "total_lookups": total_lookups,
                "cache_hits": cache_stats_after["hits"],
                "cache_misses": cache_stats_after["misses"],
                "unique_claims": 50,
                "total_claims": len(test_claims)
            }
        )
        
        self.record_result(validation_result)
        
        print(f"\n{'='*60}")
        print(f"EV-03: Cache Hit Rate")
        print(f"{'='*60}")
        print(f"Total lookups: {total_lookups}")
        print(f"Cache hits: {cache_stats_after['hits']}")
        print(f"Cache misses: {cache_stats_after['misses']}")
        print(f"Hit rate: {hit_rate:.1%}")
        print(f"Threshold: ≥{self.CACHE_HIT_THRESHOLD:.0%}")
        print(f"{'='*60}")
        
        assert hit_rate >= self.CACHE_HIT_THRESHOLD, (
            f"EV-03 FAILED: Cache hit rate {hit_rate:.1%} < "
            f"{self.CACHE_HIT_THRESHOLD:.0%} threshold. "
            f"Hits: {cache_stats_after['hits']}, "
            f"Misses: {cache_stats_after['misses']}"
        )


class TestCheckpointRecovery(EfficiencyValidationTestCase):
    """
    EV-07: Checkpoint Recovery Time Test
    
    Validates that resuming from checkpoint completes in <30 seconds.
    """
    
    TEST_ID = "EV-07"
    TEST_CATEGORY = "EV"
    RECOVERY_THRESHOLD_SECONDS = 30
    
    @pytest.fixture
    def checkpoint_state(self, tmp_path):
        """Create checkpoint state file simulating interrupted run."""
        checkpoint_file = tmp_path / "checkpoint.json"
        
        checkpoint_data = {
            "run_id": "test_run_001",
            "started_at": "2025-12-31T10:00:00",
            "interrupted_at": "2025-12-31T10:30:00",
            "total_papers": 100,
            "processed_papers": 45,
            "pending_papers": list(range(45, 100)),
            "claims_processed": 225,  # ~5 per paper
            "claims_pending": 275,
            "cached_results": {
                f"paper_{i}": {"status": "complete"} for i in range(45)
            },
            "pending_claims": [
                {"claim_id": f"pending_{i}", "paper_idx": i // 5 + 45}
                for i in range(275)
            ],
            "state_version": "1.0"
        }
        
        checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))
        return checkpoint_file
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    def test_ev07_checkpoint_recovery_time(
        self,
        orchestrator_instance,
        checkpoint_state
    ):
        """
        EV-07: Resume from checkpoint must complete in <30 seconds.
        
        Process:
        1. Load checkpoint state
        2. Measure time to restore state and resume
        3. Validate against threshold
        """
        orchestrator = orchestrator_instance
        
        start_time = time.perf_counter()
        
        # Load checkpoint and restore state
        with open(checkpoint_state) as f:
            checkpoint_data = json.load(f)
        
        # Restore state
        orchestrator.restore_from_checkpoint(checkpoint_data)
        
        # Verify state is ready to resume
        assert orchestrator.is_ready_to_resume()
        
        # Measure time to first operation
        orchestrator.prepare_for_resume()
        
        end_time = time.perf_counter()
        recovery_time = end_time - start_time
        
        metric = EfficiencyMetric(
            metric_id="EV-07",
            metric_name="checkpoint_recovery_time",
            value=recovery_time,
            unit="seconds",
            threshold=self.RECOVERY_THRESHOLD_SECONDS,
            passed=recovery_time < self.RECOVERY_THRESHOLD_SECONDS
        )
        
        tracker = EfficiencyMetricsTracker()
        tracker.record(metric)
        
        validation_result = ValidationResult(
            test_id="EV-07",
            test_name="Checkpoint Recovery Time",
            passed=recovery_time < self.RECOVERY_THRESHOLD_SECONDS,
            actual_value=recovery_time,
            expected_value=f"<{self.RECOVERY_THRESHOLD_SECONDS}s",
            threshold=self.RECOVERY_THRESHOLD_SECONDS,
            margin=self.RECOVERY_THRESHOLD_SECONDS - recovery_time,
            metadata={
                "checkpoint_size_bytes": checkpoint_state.stat().st_size,
                "papers_in_checkpoint": checkpoint_data["total_papers"],
                "papers_processed": checkpoint_data["processed_papers"],
                "claims_cached": len(checkpoint_data.get("cached_results", {}))
            }
        )
        
        self.record_result(validation_result)
        
        print(f"\n{'='*60}")
        print(f"EV-07: Checkpoint Recovery Time")
        print(f"{'='*60}")
        print(f"Recovery time: {recovery_time:.3f}s")
        print(f"Threshold: <{self.RECOVERY_THRESHOLD_SECONDS}s")
        print(f"Checkpoint size: {checkpoint_state.stat().st_size / 1024:.1f} KB")
        print(f"Papers in checkpoint: {checkpoint_data['processed_papers']}/{checkpoint_data['total_papers']}")
        print(f"{'='*60}")
        
        assert recovery_time < self.RECOVERY_THRESHOLD_SECONDS, (
            f"EV-07 FAILED: Checkpoint recovery took {recovery_time:.3f}s "
            f"(threshold: {self.RECOVERY_THRESHOLD_SECONDS}s)"
        )
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    def test_ev07_large_checkpoint_recovery(self, orchestrator_instance, tmp_path):
        """
        EV-07 (Stress): Recovery with large checkpoint file.
        
        Tests recovery with 1000 papers worth of state.
        """
        # Create large checkpoint
        large_checkpoint = tmp_path / "large_checkpoint.json"
        
        large_data = {
            "run_id": "stress_test_001",
            "total_papers": 1000,
            "processed_papers": 800,
            "cached_results": {
                f"paper_{i}": {
                    "status": "complete",
                    "claims": [{"claim_id": f"c_{i}_{j}"} for j in range(10)]
                }
                for i in range(800)
            }
        }
        
        large_checkpoint.write_text(json.dumps(large_data))
        
        start_time = time.perf_counter()
        orchestrator_instance.restore_from_checkpoint(large_data)
        recovery_time = time.perf_counter() - start_time
        
        # Should still be under threshold even with large state
        validation_result = ValidationResult(
            test_id="EV-07-stress",
            test_name="Large Checkpoint Recovery",
            passed=recovery_time < self.RECOVERY_THRESHOLD_SECONDS,
            actual_value=recovery_time,
            expected_value=f"<{self.RECOVERY_THRESHOLD_SECONDS}s",
            threshold=self.RECOVERY_THRESHOLD_SECONDS,
            metadata={
                "papers_in_checkpoint": 1000,
                "checkpoint_size_mb": large_checkpoint.stat().st_size / (1024 * 1024)
            }
        )
        
        self.record_result(validation_result)
        
        assert recovery_time < self.RECOVERY_THRESHOLD_SECONDS, (
            f"EV-07 (stress) FAILED: Large checkpoint recovery took "
            f"{recovery_time:.3f}s"
        )


# ============================================================================
# Timing Utilities
# ============================================================================

class TimingContext:
    """Context manager for timing code blocks."""
    
    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.duration: float = 0
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        return False


# ============================================================================
# Performance Regression Detector
# ============================================================================

class PerformanceRegressionDetector:
    """Detect performance regressions between runs."""
    
    def __init__(self, threshold_percent: float = 10.0):
        self.threshold_percent = threshold_percent
        self.tracker = EfficiencyMetricsTracker()
    
    def check_all_metrics(
        self,
        current_metrics: Dict[str, float]
    ) -> List[Dict]:
        """Check all metrics for regressions."""
        regressions = []
        
        for metric_id, current_value in current_metrics.items():
            is_regression, magnitude = self.tracker.check_regression(
                metric_id, current_value, self.threshold_percent
            )
            
            if is_regression:
                baseline = self.tracker.get_baseline(metric_id)
                regressions.append({
                    "metric_id": metric_id,
                    "baseline": baseline,
                    "current": current_value,
                    "regression_magnitude": magnitude,
                    "regression_percent": (magnitude / baseline * 100) if baseline else 0
                })
        
        return regressions
    
    def generate_report(self, regressions: List[Dict]) -> str:
        """Generate regression report."""
        if not regressions:
            return "✅ No performance regressions detected."
        
        report = ["⚠️ Performance Regressions Detected", ""]
        report.append("| Metric | Baseline | Current | Regression |")
        report.append("|--------|----------|---------|------------|")
        
        for r in regressions:
            report.append(
                f"| {r['metric_id']} | {r['baseline']:.2f} | "
                f"{r['current']:.2f} | {r['regression_percent']:.1f}% |"
            )
        
        return "\n".join(report)
```

---

## Implementation Steps

### Step 1: Create Efficiency Test Directory (30 min)

```bash
mkdir -p tests/validation/efficiency
mkdir -p tests/validation/baselines
touch tests/validation/efficiency/__init__.py
```

### Step 2: Implement Timing Utilities (1 hour)

- `TimingContext` context manager
- `EfficiencyMetric` dataclass
- `EfficiencyMetricsTracker` class

### Step 3: Implement Tests (5 hours)

1. `TestPipelineRunTime` (EV-01) - 1.5 hours
2. `TestIncrementalSpeedup` (EV-02) - 1.5 hours
3. `TestCacheHitRate` (EV-03) - 1 hour
4. `TestCheckpointRecovery` (EV-07) - 1 hour

### Step 4: Regression Detection (1 hour)

- `PerformanceRegressionDetector`
- Historical baseline comparison
- Report generation

### Step 5: Documentation (30 min)

- Document test running instructions
- Add pytest markers documentation
- Create efficiency threshold justifications

---

## Acceptance Criteria

- [ ] All four tests (EV-01, EV-02, EV-03, EV-07) execute without errors
- [ ] Timing measurements accurate to millisecond precision
- [ ] Metrics stored for regression tracking
- [ ] Regression detection implemented
- [ ] Performance reports generated

---

## Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| VM-W0-1 | Task Card | Required (`EfficiencyValidationTestCase`) |
| `BenchmarkRunner` | Code | From VM-W0-1 |
| `HardwareProfiler` | Code | From VM-W0-1 |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test environment variability | HIGH | Capture hardware profile, normalize results |
| Long test execution times | MEDIUM | Provide sample-based estimation option |
| Cache implementation differences | LOW | Mock cache for consistent behavior |

---

## Notes

- EV-01 marked as 'slow' - can be skipped in CI with estimation option
- All time measurements use `time.perf_counter()` for precision
- Hardware profile captured for reproducibility
- Consider running efficiency tests on dedicated hardware for consistency
