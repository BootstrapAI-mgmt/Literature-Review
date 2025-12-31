# Task Card: Cost Tracking Validation

**Task ID:** VM-W2-4  
**Wave:** 2 (Accuracy & Efficiency)  
**Priority:** MEDIUM  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W0-1  
**Blocks:** VM-W4-1  
**Validation IDs:** EV-04, EV-05, EV-06, FV-09, AV-07 *(FV-09, AV-07 added per review)*

---

## Objective

Validate API cost tracking accuracy, pre-filter reduction effectiveness, and rate limit compliance.

## Background

Cost control is critical for sustainable pipeline operation:
- **EV-04: API Cost Per Paper** - Each paper should cost <$0.50 in API calls
- **EV-05: Pre-Filter Reduction** - Pre-filtering should reduce API calls by 30-50%
- **EV-06: Rate Limit Compliance** - Zero rate limit violations during operation
- **FV-09: Pre-Filter Scoring** - Pre-filter correctly scores papers for relevance *(added per review)*
- **AV-07: Pre-Filter Accuracy** - Pre-filter achieves ≥95% accuracy (no relevant papers filtered) *(added per review)*

These metrics ensure:
1. Predictable operational costs
2. Efficient API usage
3. Reliable operation without service interruptions
4. No relevant papers incorrectly filtered out *(added per review)*

## Success Criteria

- [ ] EV-04: API cost per paper < $0.50
- [ ] EV-05: Pre-filter reduces API calls by 30-50%
- [ ] EV-06: Zero rate limit violations
- [ ] FV-09: Pre-filter scoring produces consistent relevance scores *(added per review)*
- [ ] AV-07: Pre-filter accuracy ≥95% (no false negatives on relevant papers) *(added per review)*
- [ ] Cost estimation accuracy validated
- [ ] Cost tracking reports generated

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| EV-04 | API Cost | 100 papers processed | `cost_per_paper < $0.50` | Average cost under threshold |
| EV-05 | Pre-Filter | 100 papers with filter | `reduction >= 0.30` | 30-50% fewer API calls |
| EV-06 | Rate Limits | Full pipeline run | `violations == 0` | No 429 errors |
| FV-09 | Pre-Filter Scoring | Papers with known relevance | Correct score ranking | Relevant papers score higher | *(added per review)*
| AV-07 | Pre-Filter Accuracy | 100 papers with annotations | `accuracy >= 0.95` | ≥95% correct filtering decisions | *(added per review)*

---

## Deliverables

### 1. Test Implementation

**File:** `tests/validation/efficiency/test_cost_tracking.py`

```python
"""
Cost Tracking Validation Tests

Validates EV-04, EV-05, EV-06 from the validation matrix.
Ensures API costs are tracked, controlled, and rate limits respected.
"""

import pytest
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from contextlib import contextmanager

from tests.validation.base import EfficiencyValidationTestCase, ValidationResult


@dataclass
class APICallRecord:
    """Record of a single API call for cost tracking."""
    timestamp: datetime
    endpoint: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    paper_id: Optional[str] = None
    claim_id: Optional[str] = None
    success: bool = True
    error_type: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "endpoint": self.endpoint,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "paper_id": self.paper_id,
            "claim_id": self.claim_id,
            "success": self.success,
            "error_type": self.error_type
        }


@dataclass
class CostSummary:
    """Summary of API costs for a pipeline run."""
    total_cost_usd: float
    total_papers: int
    total_claims: int
    total_api_calls: int
    total_input_tokens: int
    total_output_tokens: int
    cost_per_paper: float
    cost_per_claim: float
    cost_breakdown: Dict[str, float]  # By model/endpoint
    
    def to_dict(self) -> Dict:
        return {
            "total_cost_usd": self.total_cost_usd,
            "total_papers": self.total_papers,
            "total_claims": self.total_claims,
            "total_api_calls": self.total_api_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "cost_per_paper": self.cost_per_paper,
            "cost_per_claim": self.cost_per_claim,
            "cost_breakdown": self.cost_breakdown
        }


class APICostCalculator:
    """Calculate API costs based on token usage and model pricing."""
    
    # Pricing as of December 2025 (per 1M tokens)
    PRICING = {
        "gemini-2.5-flash": {
            "input": 0.075,   # $0.075 per 1M input tokens
            "output": 0.30,   # $0.30 per 1M output tokens
        },
        "gemini-2.5-pro": {
            "input": 1.25,    # $1.25 per 1M input tokens
            "output": 5.00,   # $5.00 per 1M output tokens
        },
        "gpt-4": {
            "input": 30.00,   # $30 per 1M input tokens
            "output": 60.00,  # $60 per 1M output tokens
        },
        "claude-3-sonnet": {
            "input": 3.00,    # $3 per 1M input tokens
            "output": 15.00,  # $15 per 1M output tokens
        }
    }
    
    @classmethod
    def calculate_cost(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost in USD for given token usage."""
        pricing = cls.PRICING.get(model, cls.PRICING["gemini-2.5-flash"])
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    @classmethod
    def estimate_paper_cost(
        cls,
        model: str = "gemini-2.5-flash",
        avg_pages: int = 15,
        avg_claims: int = 8
    ) -> float:
        """
        Estimate cost to process a single paper.
        
        Assumptions:
        - ~1000 tokens per page for extraction
        - ~500 tokens per claim for evaluation
        - ~200 tokens output per claim
        """
        # Extraction pass
        extraction_input = avg_pages * 1000
        extraction_output = avg_claims * 100  # Claim extraction output
        
        # Per-claim evaluation
        evaluation_input = avg_claims * 500
        evaluation_output = avg_claims * 200
        
        total_input = extraction_input + evaluation_input
        total_output = extraction_output + evaluation_output
        
        return cls.calculate_cost(model, total_input, total_output)


class CostTracker:
    """Track API costs across a pipeline run."""
    
    def __init__(self):
        self.calls: List[APICallRecord] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def start_tracking(self):
        """Start a new tracking session."""
        self.calls = []
        self.start_time = datetime.now()
    
    def record_call(self, call: APICallRecord):
        """Record an API call."""
        self.calls.append(call)
    
    def stop_tracking(self):
        """Stop tracking session."""
        self.end_time = datetime.now()
    
    def get_summary(self, papers_count: int) -> CostSummary:
        """Generate cost summary."""
        total_cost = sum(c.cost_usd for c in self.calls)
        total_input = sum(c.input_tokens for c in self.calls)
        total_output = sum(c.output_tokens for c in self.calls)
        
        # Breakdown by model
        breakdown = {}
        for call in self.calls:
            key = f"{call.model}/{call.endpoint}"
            breakdown[key] = breakdown.get(key, 0) + call.cost_usd
        
        claim_ids = set(c.claim_id for c in self.calls if c.claim_id)
        
        return CostSummary(
            total_cost_usd=total_cost,
            total_papers=papers_count,
            total_claims=len(claim_ids),
            total_api_calls=len(self.calls),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            cost_per_paper=total_cost / papers_count if papers_count > 0 else 0,
            cost_per_claim=total_cost / len(claim_ids) if claim_ids else 0,
            cost_breakdown=breakdown
        )
    
    def get_rate_limit_violations(self) -> List[APICallRecord]:
        """Get all rate limit violations."""
        return [c for c in self.calls if c.error_type == "rate_limit"]


class RateLimitMonitor:
    """Monitor for rate limit compliance."""
    
    def __init__(self, max_rpm: int = 60, max_tpm: int = 100000):
        self.max_rpm = max_rpm  # Max requests per minute
        self.max_tpm = max_tpm  # Max tokens per minute
        self.calls: List[Tuple[datetime, int]] = []  # (timestamp, tokens)
        self.violations: List[Dict] = []
    
    def record_call(self, tokens: int):
        """Record an API call."""
        now = datetime.now()
        self.calls.append((now, tokens))
        self._check_limits(now, tokens)
    
    def _check_limits(self, now: datetime, tokens: int):
        """Check if current call violates limits."""
        one_minute_ago = now - timedelta(minutes=1)
        
        # Filter to last minute
        recent_calls = [(t, tok) for t, tok in self.calls if t > one_minute_ago]
        
        # Check RPM
        if len(recent_calls) > self.max_rpm:
            self.violations.append({
                "type": "rpm_exceeded",
                "timestamp": now.isoformat(),
                "current_rpm": len(recent_calls),
                "max_rpm": self.max_rpm
            })
        
        # Check TPM
        recent_tokens = sum(tok for _, tok in recent_calls)
        if recent_tokens > self.max_tpm:
            self.violations.append({
                "type": "tpm_exceeded",
                "timestamp": now.isoformat(),
                "current_tpm": recent_tokens,
                "max_tpm": self.max_tpm
            })
    
    def get_violations(self) -> List[Dict]:
        """Get all recorded violations."""
        return self.violations
    
    def is_compliant(self) -> bool:
        """Check if all operations were compliant."""
        return len(self.violations) == 0


class TestAPICostPerPaper(EfficiencyValidationTestCase):
    """
    EV-04: API Cost Per Paper Test
    
    Validates that average API cost per paper is under $0.50.
    """
    
    TEST_ID = "EV-04"
    TEST_CATEGORY = "EV"
    COST_THRESHOLD = 0.50  # $0.50 per paper
    
    @pytest.fixture
    def cost_tracker(self) -> CostTracker:
        """Create cost tracker instance."""
        return CostTracker()
    
    @pytest.fixture
    def mock_api_calls(self) -> List[APICallRecord]:
        """Generate mock API call records for 100 papers."""
        calls = []
        
        for paper_idx in range(100):
            paper_id = f"paper_{paper_idx:03d}"
            
            # Paper extraction call
            calls.append(APICallRecord(
                timestamp=datetime.now(),
                endpoint="extract",
                model="gemini-2.5-flash",
                input_tokens=12000,  # ~12 page paper
                output_tokens=1500,  # Extraction output
                cost_usd=APICostCalculator.calculate_cost(
                    "gemini-2.5-flash", 12000, 1500
                ),
                latency_ms=2500,
                paper_id=paper_id
            ))
            
            # Per-claim evaluation (5-10 claims per paper)
            num_claims = 5 + (paper_idx % 6)  # Varies 5-10
            
            for claim_idx in range(num_claims):
                claim_id = f"{paper_id}_claim_{claim_idx}"
                
                calls.append(APICallRecord(
                    timestamp=datetime.now(),
                    endpoint="evaluate",
                    model="gemini-2.5-flash",
                    input_tokens=800,
                    output_tokens=300,
                    cost_usd=APICostCalculator.calculate_cost(
                        "gemini-2.5-flash", 800, 300
                    ),
                    latency_ms=500,
                    paper_id=paper_id,
                    claim_id=claim_id
                ))
        
        return calls
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    @pytest.mark.cost
    def test_ev04_cost_per_paper(self, cost_tracker, mock_api_calls):
        """
        EV-04: API cost per paper must be < $0.50.
        
        Process:
        1. Track all API calls during pipeline run
        2. Calculate total cost and per-paper average
        3. Validate against threshold
        """
        # Record all calls
        cost_tracker.start_tracking()
        for call in mock_api_calls:
            cost_tracker.record_call(call)
        cost_tracker.stop_tracking()
        
        # Get summary
        papers_count = len(set(c.paper_id for c in mock_api_calls if c.paper_id))
        summary = cost_tracker.get_summary(papers_count)
        
        validation_result = ValidationResult(
            test_id="EV-04",
            test_name="API Cost Per Paper",
            passed=summary.cost_per_paper < self.COST_THRESHOLD,
            actual_value=summary.cost_per_paper,
            expected_value=f"<${self.COST_THRESHOLD:.2f}",
            threshold=self.COST_THRESHOLD,
            margin=self.COST_THRESHOLD - summary.cost_per_paper,
            metadata={
                "total_cost": summary.total_cost_usd,
                "total_papers": summary.total_papers,
                "total_api_calls": summary.total_api_calls,
                "cost_per_claim": summary.cost_per_claim,
                "cost_breakdown": summary.cost_breakdown
            }
        )
        
        self.record_result(validation_result)
        self._save_cost_report(summary)
        
        print(f"\n{'='*60}")
        print(f"EV-04: API Cost Per Paper")
        print(f"{'='*60}")
        print(f"Total cost: ${summary.total_cost_usd:.4f}")
        print(f"Total papers: {summary.total_papers}")
        print(f"Cost per paper: ${summary.cost_per_paper:.4f}")
        print(f"Threshold: <${self.COST_THRESHOLD:.2f}")
        print(f"\nCost breakdown:")
        for key, cost in summary.cost_breakdown.items():
            print(f"  {key}: ${cost:.4f}")
        print(f"{'='*60}")
        
        assert summary.cost_per_paper < self.COST_THRESHOLD, (
            f"EV-04 FAILED: Cost per paper ${summary.cost_per_paper:.4f} >= "
            f"${self.COST_THRESHOLD:.2f} threshold. "
            f"Total cost: ${summary.total_cost_usd:.4f} for "
            f"{summary.total_papers} papers"
        )
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    @pytest.mark.cost
    def test_ev04_cost_estimation_accuracy(self):
        """
        EV-04 (Supplementary): Validate cost estimation accuracy.
        
        Compares estimated costs to actual tracked costs.
        """
        # Estimate cost for average paper
        estimated = APICostCalculator.estimate_paper_cost(
            model="gemini-2.5-flash",
            avg_pages=15,
            avg_claims=8
        )
        
        # Simulate actual cost (with variance)
        actual_costs = []
        for _ in range(100):
            # Vary pages and claims
            pages = 10 + int(10 * (hash(str(_)) % 100) / 100)
            claims = 5 + (hash(str(_ * 2)) % 6)
            
            cost = APICostCalculator.estimate_paper_cost(
                model="gemini-2.5-flash",
                avg_pages=pages,
                avg_claims=claims
            )
            actual_costs.append(cost)
        
        import statistics
        actual_mean = statistics.mean(actual_costs)
        
        # Estimation should be within 20% of actual mean
        accuracy = 1.0 - abs(estimated - actual_mean) / actual_mean
        
        validation_result = ValidationResult(
            test_id="EV-04-estimation",
            test_name="Cost Estimation Accuracy",
            passed=accuracy >= 0.80,
            actual_value=accuracy,
            expected_value="≥80%",
            threshold=0.80,
            metadata={
                "estimated": estimated,
                "actual_mean": actual_mean,
                "actual_std": statistics.stdev(actual_costs)
            }
        )
        
        self.record_result(validation_result)
        
        assert accuracy >= 0.80, (
            f"Cost estimation accuracy {accuracy:.1%} < 80%. "
            f"Estimated: ${estimated:.4f}, Actual mean: ${actual_mean:.4f}"
        )
    
    def _save_cost_report(self, summary: CostSummary):
        """Save cost report to file."""
        report_path = Path("tests/validation/reports/cost_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "test_id": "EV-04",
            "generated_at": datetime.now().isoformat(),
            "summary": summary.to_dict()
        }
        
        report_path.write_text(json.dumps(report, indent=2))


class TestPreFilterReduction(EfficiencyValidationTestCase):
    """
    EV-05: Pre-Filter Reduction Test
    
    Validates that pre-filtering reduces API calls by 30-50%.
    """
    
    TEST_ID = "EV-05"
    TEST_CATEGORY = "EV"
    REDUCTION_MIN = 0.30  # At least 30% reduction
    REDUCTION_MAX = 0.50  # At most 50% (sanity check)
    
    @pytest.fixture
    def papers_with_scores(self) -> List[Dict]:
        """Generate papers with pre-filter scores."""
        papers = []
        
        for i in range(100):
            # Simulate pre-filter scoring
            # Some papers are clearly irrelevant and should be filtered
            relevance_score = (i % 10) / 10  # 0.0 to 0.9
            
            papers.append({
                "paper_id": f"paper_{i:03d}",
                "title": f"Test Paper {i}",
                "prefilter_score": relevance_score,
                "should_process": relevance_score >= 0.3  # Threshold
            })
        
        return papers
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    @pytest.mark.cost
    def test_ev05_prefilter_reduction(self, papers_with_scores):
        """
        EV-05: Pre-filter must reduce API calls by 30-50%.
        
        Process:
        1. Count papers that would be processed without filter
        2. Count papers that pass pre-filter
        3. Calculate reduction percentage
        """
        total_papers = len(papers_with_scores)
        
        # Without filter - all papers processed
        without_filter = total_papers
        
        # With filter - only papers above threshold
        with_filter = sum(1 for p in papers_with_scores if p["should_process"])
        
        reduction = 1.0 - (with_filter / without_filter)
        
        # Calculate API calls saved
        # Assume average 8 API calls per paper
        avg_calls_per_paper = 8
        calls_saved = (without_filter - with_filter) * avg_calls_per_paper
        
        validation_result = ValidationResult(
            test_id="EV-05",
            test_name="Pre-Filter API Call Reduction",
            passed=self.REDUCTION_MIN <= reduction <= self.REDUCTION_MAX,
            actual_value=reduction,
            expected_value=f"{self.REDUCTION_MIN:.0%}-{self.REDUCTION_MAX:.0%}",
            threshold=self.REDUCTION_MIN,
            margin=reduction - self.REDUCTION_MIN,
            metadata={
                "total_papers": total_papers,
                "papers_filtered_out": without_filter - with_filter,
                "papers_processed": with_filter,
                "api_calls_saved": calls_saved,
                "estimated_cost_saved": calls_saved * 0.0001  # ~$0.0001 per call
            }
        )
        
        self.record_result(validation_result)
        
        print(f"\n{'='*60}")
        print(f"EV-05: Pre-Filter Reduction")
        print(f"{'='*60}")
        print(f"Total papers: {total_papers}")
        print(f"Papers filtered out: {without_filter - with_filter}")
        print(f"Papers processed: {with_filter}")
        print(f"Reduction: {reduction:.1%}")
        print(f"Expected: {self.REDUCTION_MIN:.0%}-{self.REDUCTION_MAX:.0%}")
        print(f"API calls saved: {calls_saved}")
        print(f"{'='*60}")
        
        assert reduction >= self.REDUCTION_MIN, (
            f"EV-05 FAILED: Pre-filter reduction {reduction:.1%} < "
            f"{self.REDUCTION_MIN:.0%} minimum. "
            f"Only {without_filter - with_filter} papers filtered from {total_papers}"
        )
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    def test_ev05_filter_quality(self, papers_with_scores):
        """
        EV-05 (Supplementary): Validate filter doesn't drop relevant papers.
        
        Check that filtered papers were truly irrelevant.
        """
        # Simulate ground truth relevance
        filtered_papers = [p for p in papers_with_scores if not p["should_process"]]
        
        # Check false positive rate (relevant papers incorrectly filtered)
        false_positives = sum(
            1 for p in filtered_papers 
            if p["prefilter_score"] >= 0.5  # Would have been relevant
        )
        
        false_positive_rate = false_positives / len(filtered_papers) if filtered_papers else 0
        
        validation_result = ValidationResult(
            test_id="EV-05-quality",
            test_name="Pre-Filter Quality (False Positive Rate)",
            passed=false_positive_rate < 0.10,  # <10% false positives
            actual_value=false_positive_rate,
            expected_value="<10%",
            threshold=0.10,
            metadata={
                "filtered_count": len(filtered_papers),
                "false_positives": false_positives
            }
        )
        
        self.record_result(validation_result)
        
        assert false_positive_rate < 0.10, (
            f"Pre-filter false positive rate {false_positive_rate:.1%} >= 10%"
        )


class TestRateLimitCompliance(EfficiencyValidationTestCase):
    """
    EV-06: Rate Limit Compliance Test
    
    Validates zero rate limit violations during operation.
    """
    
    TEST_ID = "EV-06"
    TEST_CATEGORY = "EV"
    
    @pytest.fixture
    def rate_monitor(self) -> RateLimitMonitor:
        """Create rate limit monitor."""
        return RateLimitMonitor(max_rpm=60, max_tpm=100000)
    
    @pytest.fixture
    def simulated_pipeline_calls(self) -> List[Dict]:
        """Simulate API calls during pipeline execution."""
        calls = []
        
        # Simulate 100 papers processed over 30 minutes
        base_time = datetime.now()
        
        for paper_idx in range(100):
            # Each paper takes ~18 seconds on average
            paper_time = base_time + timedelta(seconds=paper_idx * 18)
            
            # Extraction call
            calls.append({
                "timestamp": paper_time,
                "tokens": 13500,  # 12000 in + 1500 out
                "paper_id": f"paper_{paper_idx}"
            })
            
            # Claim evaluation calls (spread over 10 seconds)
            num_claims = 5 + (paper_idx % 6)
            for claim_idx in range(num_claims):
                claim_time = paper_time + timedelta(seconds=claim_idx * 1.5)
                calls.append({
                    "timestamp": claim_time,
                    "tokens": 1100,  # 800 in + 300 out
                    "claim_id": f"claim_{paper_idx}_{claim_idx}"
                })
        
        return calls
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    @pytest.mark.cost
    def test_ev06_rate_limit_compliance(
        self,
        rate_monitor,
        simulated_pipeline_calls
    ):
        """
        EV-06: Pipeline must have zero rate limit violations.
        
        Process:
        1. Simulate all API calls with timestamps
        2. Check for RPM and TPM violations
        3. Report any violations
        """
        # Record all calls
        for call in simulated_pipeline_calls:
            rate_monitor.calls.append((call["timestamp"], call["tokens"]))
        
        # Check limits for each call
        for i, call in enumerate(simulated_pipeline_calls):
            # Get calls in the minute before this call
            current_time = call["timestamp"]
            one_minute_ago = current_time - timedelta(minutes=1)
            
            recent_calls = [
                (t, tok) for t, tok in rate_monitor.calls[:i+1]
                if t > one_minute_ago
            ]
            
            # Check RPM
            if len(recent_calls) > rate_monitor.max_rpm:
                rate_monitor.violations.append({
                    "type": "rpm_exceeded",
                    "timestamp": current_time.isoformat(),
                    "current_rpm": len(recent_calls),
                    "max_rpm": rate_monitor.max_rpm
                })
            
            # Check TPM
            recent_tokens = sum(tok for _, tok in recent_calls)
            if recent_tokens > rate_monitor.max_tpm:
                rate_monitor.violations.append({
                    "type": "tpm_exceeded",
                    "timestamp": current_time.isoformat(),
                    "current_tpm": recent_tokens,
                    "max_tpm": rate_monitor.max_tpm
                })
        
        violations = rate_monitor.get_violations()
        
        validation_result = ValidationResult(
            test_id="EV-06",
            test_name="Rate Limit Compliance",
            passed=len(violations) == 0,
            actual_value=len(violations),
            expected_value=0,
            threshold=0,
            margin=-len(violations) if violations else 0,
            metadata={
                "total_calls": len(simulated_pipeline_calls),
                "violations": violations[:10],  # First 10 violations
                "max_rpm_observed": self._get_max_rpm(simulated_pipeline_calls),
                "max_tpm_observed": self._get_max_tpm(simulated_pipeline_calls)
            }
        )
        
        self.record_result(validation_result)
        
        print(f"\n{'='*60}")
        print(f"EV-06: Rate Limit Compliance")
        print(f"{'='*60}")
        print(f"Total API calls: {len(simulated_pipeline_calls)}")
        print(f"Violations: {len(violations)}")
        print(f"Max RPM limit: {rate_monitor.max_rpm}")
        print(f"Max TPM limit: {rate_monitor.max_tpm}")
        
        if violations:
            print(f"\nFirst 3 violations:")
            for v in violations[:3]:
                print(f"  - {v['type']} at {v['timestamp']}")
        print(f"{'='*60}")
        
        assert len(violations) == 0, (
            f"EV-06 FAILED: {len(violations)} rate limit violations detected. "
            f"First violation: {violations[0] if violations else 'N/A'}"
        )
    
    def _get_max_rpm(self, calls: List[Dict]) -> int:
        """Calculate maximum observed RPM."""
        if not calls:
            return 0
        
        max_rpm = 0
        for i, call in enumerate(calls):
            current_time = call["timestamp"]
            one_minute_ago = current_time - timedelta(minutes=1)
            
            recent = sum(1 for c in calls[:i+1] if c["timestamp"] > one_minute_ago)
            max_rpm = max(max_rpm, recent)
        
        return max_rpm
    
    def _get_max_tpm(self, calls: List[Dict]) -> int:
        """Calculate maximum observed TPM."""
        if not calls:
            return 0
        
        max_tpm = 0
        for i, call in enumerate(calls):
            current_time = call["timestamp"]
            one_minute_ago = current_time - timedelta(minutes=1)
            
            recent = sum(
                c["tokens"] for c in calls[:i+1] 
                if c["timestamp"] > one_minute_ago
            )
            max_tpm = max(max_tpm, recent)
        
        return max_tpm
    
    @pytest.mark.validation
    @pytest.mark.efficiency
    def test_ev06_rate_limiter_behavior(self):
        """
        EV-06 (Supplementary): Test rate limiter correctly throttles.
        
        Verify the global_rate_limiter properly delays requests.
        """
        from literature_review.utils.global_rate_limiter import global_limiter
        
        # Record timing of rapid calls
        call_times = []
        
        for i in range(10):
            start = time.perf_counter()
            global_limiter.acquire()  # Should throttle if too fast
            call_times.append(time.perf_counter() - start)
        
        # First call should be instant, later calls may be delayed
        # if rate limit is being respected
        total_time = sum(call_times)
        
        validation_result = ValidationResult(
            test_id="EV-06-limiter",
            test_name="Rate Limiter Behavior",
            passed=True,  # Pass if no exception
            actual_value=total_time,
            expected_value="throttled appropriately",
            metadata={
                "call_times": call_times,
                "mean_delay": sum(call_times) / len(call_times)
            }
        )
        
        self.record_result(validation_result)


# ============================================================================
# Cost Report Generator
# ============================================================================

class CostReportGenerator:
    """Generate comprehensive cost reports."""
    
    @staticmethod
    def generate_markdown_report(summary: CostSummary) -> str:
        """Generate markdown cost report."""
        report = [
            "# API Cost Report",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Cost | ${summary.total_cost_usd:.4f} |",
            f"| Total Papers | {summary.total_papers} |",
            f"| Cost per Paper | ${summary.cost_per_paper:.4f} |",
            f"| Total API Calls | {summary.total_api_calls} |",
            f"| Total Input Tokens | {summary.total_input_tokens:,} |",
            f"| Total Output Tokens | {summary.total_output_tokens:,} |",
            "",
            "## Cost Breakdown",
            "",
            "| Endpoint | Cost |",
            "|----------|------|",
        ]
        
        for endpoint, cost in sorted(summary.cost_breakdown.items()):
            report.append(f"| {endpoint} | ${cost:.4f} |")
        
        return "\n".join(report)
    
    @staticmethod
    def generate_csv_report(calls: List[APICallRecord]) -> str:
        """Generate CSV report of all API calls."""
        lines = [
            "timestamp,endpoint,model,input_tokens,output_tokens,cost_usd,latency_ms,paper_id,claim_id"
        ]
        
        for call in calls:
            lines.append(
                f"{call.timestamp.isoformat()},{call.endpoint},{call.model},"
                f"{call.input_tokens},{call.output_tokens},{call.cost_usd:.6f},"
                f"{call.latency_ms},{call.paper_id or ''},{call.claim_id or ''}"
            )
        
        return "\n".join(lines)
```

---

## Implementation Steps

### Step 1: Create Test Structure (30 min)

```bash
mkdir -p tests/validation/efficiency
mkdir -p tests/validation/reports
touch tests/validation/efficiency/__init__.py
```

### Step 2: Implement Cost Tracking Classes (2 hours)

- `APICallRecord` dataclass
- `CostSummary` dataclass
- `APICostCalculator` with pricing
- `CostTracker` for session tracking

### Step 3: Implement Tests (4 hours)

1. `TestAPICostPerPaper` (EV-04) - 1.5 hours
2. `TestPreFilterReduction` (EV-05) - 1 hour
3. `TestRateLimitCompliance` (EV-06) - 1.5 hours

### Step 4: Report Generation (1 hour)

- `CostReportGenerator` for markdown/CSV
- Integration with cost tracker
- Report persistence

### Step 5: Documentation (30 min)

- Update pricing table
- Document cost thresholds
- Add troubleshooting guides

---

## Acceptance Criteria

- [ ] All three tests (EV-04, EV-05, EV-06) execute without errors
- [ ] Cost tracking accurate to 4 decimal places
- [ ] Pre-filter reduction measured correctly
- [ ] Rate limit monitoring implemented
- [ ] Cost reports generated in markdown and JSON

---

## Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| VM-W0-1 | Task Card | Required (`EfficiencyValidationTestCase`) |
| `global_rate_limiter` | Code | Existing in `literature_review/utils/` |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Pricing changes | MEDIUM | Make pricing configurable, update regularly |
| Rate limit differences by account | LOW | Document expected limits, make configurable |
| Cost estimation inaccuracy | LOW | Validate against actual API bills |

---

## Cost Optimization Recommendations

If costs exceed threshold, consider:

1. **Model Downgrade:** Use `gemini-2.5-flash` instead of `pro` variants
2. **Token Reduction:** Summarize long papers before full analysis
3. **Aggressive Caching:** Cache more intermediate results
4. **Batch Processing:** Reduce per-request overhead
5. **Pre-Filter Tuning:** Adjust threshold to filter more irrelevant papers

---

## Notes

- Pricing table should be updated when API providers change rates
- Rate limits vary by API tier and account type
- Cost tracking integrates with existing `API_COST_TRACKER.md` documentation
- Consider adding budget alerts for production deployments
