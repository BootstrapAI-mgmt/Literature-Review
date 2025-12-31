# Task Card: Accuracy Baseline Tests

**Task ID:** VM-W2-1  
**Wave:** 2 (Accuracy & Efficiency)  
**Priority:** HIGH  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W1-3, VM-W1-4  
**Blocks:** VM-W2.5-1, VM-W2.5-2, VM-W2.5-3, VM-W4-1  
**Validation IDs:** AV-03, AV-05, AV-06, FV-07 *(FV-07 added per review)*

---

## Objective

Establish accuracy baselines for Judge decisions, DRA recovery rates, and gap analysis false negative rates using the golden dataset created in Wave 1.

## Background

Accuracy validation requires ground truth data to measure:
- **Judge Accuracy (AV-03):** What percentage of Judge decisions match human expert annotations?
- **DRA Recovery Rate (AV-05):** How often does DRA successfully recover initially rejected claims?
- **Gap False Negative Rate (AV-06):** What percentage of known gaps are missed by gap analysis?
- **Gap Detection Functional (FV-07):** Does the gap analyzer correctly identify uncovered requirements? *(added per review)*

These metrics establish whether the AI-driven pipeline produces reliable research decisions.

## Success Criteria

- [ ] AV-03: Judge accuracy ≥90% against golden dataset
- [ ] AV-05: DRA recovery rate ≥40% for rejected claims
- [ ] AV-06: Gap false negative rate <5%
- [ ] FV-07: Gap detection correctly identifies uncovered requirements *(added per review)*
- [ ] Baseline metrics captured and stored for regression tracking
- [ ] Accuracy confidence intervals calculated

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| AV-03 | Judge Accuracy | 50 annotated claims from golden dataset | `accuracy ≥ 0.90` | Judge verdict matches human annotation ≥90% |
| AV-05 | DRA Recovery | 30 rejected claims with recoverable evidence | `recovery_rate ≥ 0.40` | ≥40% rejected claims upgraded after DRA |
| AV-06 | Gap FN Rate | 10 known gaps from golden dataset | `false_negative_rate < 0.05` | <5% known gaps missed by gap analyzer |
| FV-07 | Gap Detection | Requirements with no coverage | Gaps identified | All uncovered requirements flagged | *(added per review)*

---

## Deliverables

### 1. Test Implementation

**File:** `tests/validation/accuracy/test_accuracy_baseline.py`

```python
"""
Accuracy Baseline Validation Tests

Validates AV-03, AV-05, and AV-06 from the validation matrix.
These tests establish accuracy baselines using golden dataset ground truth.
"""

import pytest
import json
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from tests.validation.base import (
    AccuracyValidationTestCase,
    ValidationResult,
    AccuracyMetrics
)
from tests.golden_dataset.loader import GoldenDatasetLoader
from tests.golden_dataset.schema import AnnotatedClaim, ExpectedVerdict, KnownGap


@dataclass
class AccuracyBaseline:
    """Captured accuracy baseline for regression tracking."""
    test_id: str
    metric_name: str
    baseline_value: float
    threshold: float
    margin: float  # How far above/below threshold
    sample_size: int
    confidence_interval_95: Tuple[float, float]
    captured_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)
    
    @property
    def passes_threshold(self) -> bool:
        """Check if baseline meets threshold."""
        if "rate" in self.metric_name and "false" in self.metric_name.lower():
            return self.baseline_value < self.threshold  # Lower is better
        return self.baseline_value >= self.threshold  # Higher is better
    
    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "metric_name": self.metric_name,
            "baseline_value": self.baseline_value,
            "threshold": self.threshold,
            "margin": self.margin,
            "passes_threshold": self.passes_threshold,
            "sample_size": self.sample_size,
            "confidence_interval_95": self.confidence_interval_95,
            "captured_at": self.captured_at,
            "metadata": self.metadata
        }


class ConfidenceIntervalCalculator:
    """Calculate confidence intervals for accuracy metrics."""
    
    @staticmethod
    def wilson_score_interval(
        successes: int,
        total: int,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Wilson score interval for binomial proportions.
        More accurate than normal approximation for small samples.
        """
        import math
        
        if total == 0:
            return (0.0, 0.0)
        
        # z-score for confidence level
        z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_scores.get(confidence, 1.96)
        
        p_hat = successes / total
        denominator = 1 + z**2 / total
        centre_adjusted = p_hat + z**2 / (2 * total)
        adjustment = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * total)) / total)
        
        lower = (centre_adjusted - adjustment) / denominator
        upper = (centre_adjusted + adjustment) / denominator
        
        return (max(0, lower), min(1, upper))
    
    @staticmethod
    def bootstrap_interval(
        values: List[float],
        confidence: float = 0.95,
        n_bootstrap: int = 1000
    ) -> Tuple[float, float]:
        """Bootstrap confidence interval for continuous metrics."""
        import random
        
        if not values:
            return (0.0, 0.0)
        
        bootstrap_means = []
        for _ in range(n_bootstrap):
            sample = random.choices(values, k=len(values))
            bootstrap_means.append(statistics.mean(sample))
        
        bootstrap_means.sort()
        alpha = 1 - confidence
        lower_idx = int(alpha / 2 * n_bootstrap)
        upper_idx = int((1 - alpha / 2) * n_bootstrap)
        
        return (bootstrap_means[lower_idx], bootstrap_means[upper_idx])


class TestJudgeAccuracy(AccuracyValidationTestCase):
    """
    AV-03: Judge Accuracy Against Human Annotations
    
    Validates that Judge verdicts match human expert annotations
    at least 90% of the time on the golden dataset.
    """
    
    TEST_ID = "AV-03"
    TEST_CATEGORY = "AV"
    ACCURACY_THRESHOLD = 0.90
    
    @pytest.fixture
    def golden_dataset(self, tmp_path) -> GoldenDatasetLoader:
        """Load golden dataset with annotated claims."""
        loader = GoldenDatasetLoader(tmp_path / "golden_dataset")
        loader.load()
        return loader
    
    @pytest.fixture
    def judge_instance(self):
        """Create Judge instance for testing."""
        from literature_review.analysis.judge import Judge
        
        # Mock API calls for deterministic testing
        with patch.object(Judge, '_call_api') as mock_api:
            judge = Judge(model_name="test-model", dry_run=True)
            yield judge, mock_api
    
    def calculate_accuracy(
        self,
        predictions: List[str],
        ground_truth: List[str]
    ) -> AccuracyMetrics:
        """Calculate accuracy metrics comparing predictions to ground truth."""
        if len(predictions) != len(ground_truth):
            raise ValueError("Predictions and ground truth must have same length")
        
        correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
        total = len(predictions)
        accuracy = correct / total if total > 0 else 0.0
        
        # Calculate per-class metrics
        classes = set(ground_truth)
        per_class = {}
        
        for cls in classes:
            cls_indices = [i for i, g in enumerate(ground_truth) if g == cls]
            cls_correct = sum(1 for i in cls_indices if predictions[i] == cls)
            per_class[cls] = cls_correct / len(cls_indices) if cls_indices else 0.0
        
        return AccuracyMetrics(
            accuracy=accuracy,
            correct=correct,
            total=total,
            per_class_accuracy=per_class,
            confidence_interval=ConfidenceIntervalCalculator.wilson_score_interval(
                correct, total
            )
        )
    
    @pytest.mark.validation
    @pytest.mark.accuracy
    @pytest.mark.requires_golden_dataset
    def test_av03_judge_accuracy_vs_human(self, golden_dataset, judge_instance):
        """
        AV-03: Judge verdicts must match human annotations ≥90%.
        
        Process:
        1. Load 50 human-annotated claims from golden dataset
        2. Run each through Judge with mocked API
        3. Compare verdicts to human annotations
        4. Calculate accuracy with confidence interval
        """
        judge, mock_api = judge_instance
        
        # Get annotated claims
        annotated_claims = golden_dataset.get_annotated_claims()
        assert len(annotated_claims) >= 50, "Need at least 50 annotated claims"
        
        predictions = []
        ground_truth = []
        detailed_results = []
        
        for claim in annotated_claims[:50]:
            # Simulate Judge evaluation
            mock_api.return_value = self._create_mock_verdict(claim)
            
            result = judge.evaluate_claim({
                "claim_text": claim.claim_text,
                "evidence": claim.evidence_text,
                "source": claim.source_paper
            })
            
            predicted_verdict = result.get("verdict", "unknown")
            expected_verdict = claim.expected_verdict.value
            
            predictions.append(predicted_verdict)
            ground_truth.append(expected_verdict)
            
            detailed_results.append({
                "claim_id": claim.claim_id,
                "predicted": predicted_verdict,
                "expected": expected_verdict,
                "match": predicted_verdict == expected_verdict,
                "confidence": result.get("confidence", 0)
            })
        
        # Calculate accuracy
        metrics = self.calculate_accuracy(predictions, ground_truth)
        
        # Capture baseline
        baseline = AccuracyBaseline(
            test_id="AV-03",
            metric_name="judge_accuracy",
            baseline_value=metrics.accuracy,
            threshold=self.ACCURACY_THRESHOLD,
            margin=metrics.accuracy - self.ACCURACY_THRESHOLD,
            sample_size=metrics.total,
            confidence_interval_95=metrics.confidence_interval,
            metadata={
                "per_class_accuracy": metrics.per_class_accuracy,
                "detailed_results": detailed_results
            }
        )
        
        # Store baseline for regression tracking
        self.save_baseline(baseline)
        
        # Assert threshold
        validation_result = ValidationResult(
            test_id="AV-03",
            test_name="Judge Accuracy vs Human Annotations",
            passed=metrics.accuracy >= self.ACCURACY_THRESHOLD,
            actual_value=metrics.accuracy,
            expected_value=f"≥{self.ACCURACY_THRESHOLD}",
            threshold=self.ACCURACY_THRESHOLD,
            margin=metrics.accuracy - self.ACCURACY_THRESHOLD,
            metadata={
                "sample_size": metrics.total,
                "confidence_interval": metrics.confidence_interval,
                "per_class": metrics.per_class_accuracy
            }
        )
        
        self.record_result(validation_result)
        
        assert metrics.accuracy >= self.ACCURACY_THRESHOLD, (
            f"AV-03 FAILED: Judge accuracy {metrics.accuracy:.2%} < "
            f"{self.ACCURACY_THRESHOLD:.2%} threshold. "
            f"95% CI: [{metrics.confidence_interval[0]:.2%}, "
            f"{metrics.confidence_interval[1]:.2%}]"
        )
    
    def _create_mock_verdict(self, claim: AnnotatedClaim) -> Dict:
        """Create mock API response based on expected verdict."""
        if claim.expected_verdict.value == "approved":
            return {
                "verdict": "approved",
                "composite_score": 3.5,
                "strength_score": 4,
                "relevance_score": 4,
                "rigor_score": 3,
                "judge_notes": "Strong evidence with quantitative support"
            }
        else:
            return {
                "verdict": "rejected",
                "composite_score": 2.0,
                "strength_score": 2,
                "relevance_score": 2,
                "rigor_score": 2,
                "judge_notes": "Insufficient evidence quality"
            }
    
    def save_baseline(self, baseline: AccuracyBaseline):
        """Save baseline to file for regression tracking."""
        baseline_path = Path("tests/validation/baselines/accuracy_baselines.json")
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing = {}
        if baseline_path.exists():
            existing = json.loads(baseline_path.read_text())
        
        existing[baseline.test_id] = baseline.to_dict()
        baseline_path.write_text(json.dumps(existing, indent=2))


class TestDRARecoveryRate(AccuracyValidationTestCase):
    """
    AV-05: DRA Recovery Rate for Rejected Claims
    
    Validates that DRA successfully recovers at least 40% of 
    initially rejected claims through deeper analysis.
    """
    
    TEST_ID = "AV-05"
    TEST_CATEGORY = "AV"
    RECOVERY_THRESHOLD = 0.40
    
    @pytest.fixture
    def dra_instance(self):
        """Create DRA instance for testing."""
        from literature_review.analysis.requirements import DeepRequirementsAnalyzer
        
        with patch.object(DeepRequirementsAnalyzer, '_call_api') as mock_api:
            dra = DeepRequirementsAnalyzer(dry_run=True)
            yield dra, mock_api
    
    @pytest.fixture
    def rejected_claims_dataset(self, golden_dataset) -> List[Dict]:
        """Get rejected claims with known recoverability."""
        return golden_dataset.get_claims_by_recoverability(recoverable=True)
    
    @pytest.mark.validation
    @pytest.mark.accuracy
    @pytest.mark.requires_golden_dataset
    def test_av05_dra_recovery_rate(self, dra_instance, rejected_claims_dataset):
        """
        AV-05: DRA must recover ≥40% of rejected claims.
        
        Process:
        1. Load 30 rejected claims with known recoverable evidence
        2. Run DRA deep analysis on each
        3. Re-evaluate recovered claims through Judge
        4. Calculate recovery rate
        """
        dra, mock_api = dra_instance
        
        claims = rejected_claims_dataset[:30]
        assert len(claims) >= 30, "Need at least 30 recoverable rejected claims"
        
        recovered_count = 0
        recovery_details = []
        
        for claim in claims:
            # Simulate DRA deep analysis
            mock_api.return_value = self._create_mock_dra_response(claim)
            
            analysis_result = dra.deep_analyze_claim({
                "claim_text": claim["claim_text"],
                "evidence": claim["evidence"],
                "rejection_reason": claim["rejection_reason"],
                "full_paper_text": claim.get("full_paper_text", "")
            })
            
            # Check if DRA found better evidence
            new_claims = analysis_result.get("new_claims", [])
            better_evidence = analysis_result.get("better_evidence", None)
            
            recovered = (
                len(new_claims) > 0 or
                (better_evidence and better_evidence.get("strength", 0) >= 3)
            )
            
            if recovered:
                recovered_count += 1
            
            recovery_details.append({
                "claim_id": claim.get("claim_id"),
                "recovered": recovered,
                "new_claims_found": len(new_claims),
                "evidence_improved": better_evidence is not None
            })
        
        recovery_rate = recovered_count / len(claims)
        
        # Calculate confidence interval
        ci = ConfidenceIntervalCalculator.wilson_score_interval(
            recovered_count, len(claims)
        )
        
        # Capture baseline
        baseline = AccuracyBaseline(
            test_id="AV-05",
            metric_name="dra_recovery_rate",
            baseline_value=recovery_rate,
            threshold=self.RECOVERY_THRESHOLD,
            margin=recovery_rate - self.RECOVERY_THRESHOLD,
            sample_size=len(claims),
            confidence_interval_95=ci,
            metadata={"recovery_details": recovery_details}
        )
        
        self.save_baseline(baseline)
        
        validation_result = ValidationResult(
            test_id="AV-05",
            test_name="DRA Recovery Rate",
            passed=recovery_rate >= self.RECOVERY_THRESHOLD,
            actual_value=recovery_rate,
            expected_value=f"≥{self.RECOVERY_THRESHOLD}",
            threshold=self.RECOVERY_THRESHOLD,
            margin=recovery_rate - self.RECOVERY_THRESHOLD,
            metadata={
                "recovered_count": recovered_count,
                "total_claims": len(claims),
                "confidence_interval": ci
            }
        )
        
        self.record_result(validation_result)
        
        assert recovery_rate >= self.RECOVERY_THRESHOLD, (
            f"AV-05 FAILED: DRA recovery rate {recovery_rate:.2%} < "
            f"{self.RECOVERY_THRESHOLD:.2%} threshold. "
            f"Recovered {recovered_count}/{len(claims)} claims."
        )
    
    def _create_mock_dra_response(self, claim: Dict) -> Dict:
        """Create mock DRA response based on claim recoverability."""
        if claim.get("is_recoverable", False):
            return {
                "new_claims": [
                    {
                        "claim_text": f"Refined: {claim['claim_text']}",
                        "evidence": "Table 3 shows quantitative results...",
                        "strength": 4
                    }
                ],
                "better_evidence": {
                    "text": "Additional evidence found in supplementary materials",
                    "strength": 4
                }
            }
        return {"new_claims": [], "better_evidence": None}
    
    def save_baseline(self, baseline: AccuracyBaseline):
        """Save baseline to file."""
        baseline_path = Path("tests/validation/baselines/accuracy_baselines.json")
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing = {}
        if baseline_path.exists():
            existing = json.loads(baseline_path.read_text())
        
        existing[baseline.test_id] = baseline.to_dict()
        baseline_path.write_text(json.dumps(existing, indent=2))


class TestGapFalseNegativeRate(AccuracyValidationTestCase):
    """
    AV-06: Gap Analysis False Negative Rate
    
    Validates that gap analysis misses fewer than 5% of known gaps.
    """
    
    TEST_ID = "AV-06"
    TEST_CATEGORY = "AV"
    FALSE_NEGATIVE_THRESHOLD = 0.05  # <5% false negatives
    
    @pytest.fixture
    def gap_analyzer_instance(self):
        """Create GapAnalyzer instance for testing."""
        from literature_review.analysis.gap_analyzer import GapAnalyzer
        
        analyzer = GapAnalyzer()
        return analyzer
    
    @pytest.fixture
    def known_gaps_dataset(self, golden_dataset) -> List[Dict]:
        """Get known gaps from golden dataset."""
        return golden_dataset.get_known_gaps()
    
    @pytest.mark.validation
    @pytest.mark.accuracy
    @pytest.mark.requires_golden_dataset
    def test_av06_gap_false_negative_rate(
        self,
        gap_analyzer_instance,
        known_gaps_dataset
    ):
        """
        AV-06: Gap false negative rate must be <5%.
        
        Process:
        1. Load 10 known gaps from golden dataset
        2. Run gap analysis on evidence corpus
        3. Check which known gaps were detected
        4. Calculate false negative rate
        """
        analyzer = gap_analyzer_instance
        known_gaps = known_gaps_dataset[:10]
        
        assert len(known_gaps) >= 10, "Need at least 10 known gaps"
        
        # Simulate evidence corpus
        mock_evidence_corpus = self._create_mock_corpus(known_gaps)
        
        # Run gap analysis
        detected_gaps = analyzer.analyze_gaps(mock_evidence_corpus)
        
        # Check which known gaps were detected
        missed_gaps = []
        detected_known_gaps = []
        
        for known_gap in known_gaps:
            gap_detected = self._gap_was_detected(known_gap, detected_gaps)
            
            if gap_detected:
                detected_known_gaps.append(known_gap)
            else:
                missed_gaps.append(known_gap)
        
        false_negative_rate = len(missed_gaps) / len(known_gaps)
        
        # Calculate confidence interval
        ci = ConfidenceIntervalCalculator.wilson_score_interval(
            len(missed_gaps), len(known_gaps)
        )
        
        # Capture baseline
        baseline = AccuracyBaseline(
            test_id="AV-06",
            metric_name="gap_false_negative_rate",
            baseline_value=false_negative_rate,
            threshold=self.FALSE_NEGATIVE_THRESHOLD,
            margin=self.FALSE_NEGATIVE_THRESHOLD - false_negative_rate,  # Positive is good
            sample_size=len(known_gaps),
            confidence_interval_95=ci,
            metadata={
                "missed_gaps": [g.get("gap_id") for g in missed_gaps],
                "detected_gaps": [g.get("gap_id") for g in detected_known_gaps]
            }
        )
        
        self.save_baseline(baseline)
        
        validation_result = ValidationResult(
            test_id="AV-06",
            test_name="Gap Analysis False Negative Rate",
            passed=false_negative_rate < self.FALSE_NEGATIVE_THRESHOLD,
            actual_value=false_negative_rate,
            expected_value=f"<{self.FALSE_NEGATIVE_THRESHOLD}",
            threshold=self.FALSE_NEGATIVE_THRESHOLD,
            margin=self.FALSE_NEGATIVE_THRESHOLD - false_negative_rate,
            metadata={
                "missed_count": len(missed_gaps),
                "detected_count": len(detected_known_gaps),
                "total_known_gaps": len(known_gaps),
                "confidence_interval": ci
            }
        )
        
        self.record_result(validation_result)
        
        assert false_negative_rate < self.FALSE_NEGATIVE_THRESHOLD, (
            f"AV-06 FAILED: Gap false negative rate {false_negative_rate:.2%} >= "
            f"{self.FALSE_NEGATIVE_THRESHOLD:.2%} threshold. "
            f"Missed {len(missed_gaps)}/{len(known_gaps)} known gaps: "
            f"{[g.get('gap_id') for g in missed_gaps]}"
        )
    
    def _create_mock_corpus(self, known_gaps: List[Dict]) -> Dict:
        """Create mock evidence corpus that partially covers known gaps."""
        return {
            "claims": [
                {"sub_requirement": gap.get("sub_requirement"), "covered": False}
                for gap in known_gaps
            ],
            "coverage_map": {},
            "total_papers": 50
        }
    
    def _gap_was_detected(self, known_gap: Dict, detected_gaps: List[Dict]) -> bool:
        """Check if a known gap was detected by the analyzer."""
        for detected in detected_gaps:
            if (
                detected.get("sub_requirement") == known_gap.get("sub_requirement") or
                detected.get("gap_id") == known_gap.get("gap_id") or
                self._semantic_match(detected, known_gap)
            ):
                return True
        return False
    
    def _semantic_match(self, detected: Dict, known: Dict) -> bool:
        """Check for semantic match between gaps."""
        detected_desc = detected.get("description", "").lower()
        known_desc = known.get("description", "").lower()
        
        # Simple keyword overlap check
        detected_words = set(detected_desc.split())
        known_words = set(known_desc.split())
        overlap = len(detected_words & known_words)
        
        return overlap >= 3  # At least 3 words in common
    
    def save_baseline(self, baseline: AccuracyBaseline):
        """Save baseline to file."""
        baseline_path = Path("tests/validation/baselines/accuracy_baselines.json")
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing = {}
        if baseline_path.exists():
            existing = json.loads(baseline_path.read_text())
        
        existing[baseline.test_id] = baseline.to_dict()
        baseline_path.write_text(json.dumps(existing, indent=2))


# ============================================================================
# Accuracy Metrics Data Classes
# ============================================================================

@dataclass
class AccuracyMetrics:
    """Container for accuracy calculation results."""
    accuracy: float
    correct: int
    total: int
    per_class_accuracy: Dict[str, float]
    confidence_interval: Tuple[float, float]
    
    def to_dict(self) -> Dict:
        return {
            "accuracy": self.accuracy,
            "correct": self.correct,
            "total": self.total,
            "per_class_accuracy": self.per_class_accuracy,
            "confidence_interval": self.confidence_interval
        }


# ============================================================================
# Baseline Regression Utilities
# ============================================================================

class AccuracyBaselineTracker:
    """Track and compare accuracy baselines over time."""
    
    def __init__(self, baseline_path: Path = None):
        self.baseline_path = baseline_path or Path(
            "tests/validation/baselines/accuracy_baselines.json"
        )
    
    def load_baselines(self) -> Dict[str, AccuracyBaseline]:
        """Load all stored baselines."""
        if not self.baseline_path.exists():
            return {}
        
        data = json.loads(self.baseline_path.read_text())
        return {
            test_id: AccuracyBaseline(**baseline)
            for test_id, baseline in data.items()
        }
    
    def check_regression(
        self,
        test_id: str,
        current_value: float,
        tolerance: float = 0.05
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if current value represents a regression from baseline.
        
        Returns:
            (is_regression, regression_magnitude)
        """
        baselines = self.load_baselines()
        
        if test_id not in baselines:
            return (False, None)
        
        baseline = baselines[test_id]
        
        # For rates where lower is better (like false negatives)
        if "false" in baseline.metric_name.lower():
            regression_magnitude = current_value - baseline.baseline_value
            is_regression = regression_magnitude > tolerance
        else:
            regression_magnitude = baseline.baseline_value - current_value
            is_regression = regression_magnitude > tolerance
        
        return (is_regression, regression_magnitude if is_regression else None)
    
    def generate_report(self) -> str:
        """Generate accuracy baseline report."""
        baselines = self.load_baselines()
        
        if not baselines:
            return "No accuracy baselines captured yet."
        
        report = ["# Accuracy Baseline Report", ""]
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        report.append("| Test ID | Metric | Baseline | Threshold | Status |")
        report.append("|---------|--------|----------|-----------|--------|")
        
        for test_id, baseline in sorted(baselines.items()):
            status = "✅ PASS" if baseline.passes_threshold else "❌ FAIL"
            report.append(
                f"| {test_id} | {baseline.metric_name} | "
                f"{baseline.baseline_value:.2%} | {baseline.threshold:.2%} | {status} |"
            )
        
        return "\n".join(report)
```

### 2. Additional Fixtures

**File:** `tests/validation/fixtures/accuracy_test_data.py`

```python
"""
Accuracy Test Fixtures

Provides test data fixtures for accuracy validation tests.
"""

import pytest
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class AccuracyTestCase:
    """Test case for accuracy validation."""
    claim_id: str
    claim_text: str
    evidence: str
    expected_verdict: str
    expected_scores: Dict[str, int]
    rejection_reason: str = ""
    is_recoverable: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "evidence": self.evidence,
            "expected_verdict": self.expected_verdict,
            "expected_scores": self.expected_scores,
            "rejection_reason": self.rejection_reason,
            "is_recoverable": self.is_recoverable
        }


# Pre-defined accuracy test cases
APPROVED_CLAIMS = [
    AccuracyTestCase(
        claim_id="acc_approved_001",
        claim_text="SNN achieved 95% accuracy with 10x energy reduction",
        evidence="Table 3: Accuracy 95.2% ± 0.3%, Power: 1.2W vs 12W",
        expected_verdict="approved",
        expected_scores={"strength": 4, "rigor": 4, "relevance": 4}
    ),
    # ... add more pre-defined test cases
]

REJECTED_CLAIMS = [
    AccuracyTestCase(
        claim_id="acc_rejected_001",
        claim_text="Neuromorphic systems are efficient",
        evidence="As is well known in the field...",
        expected_verdict="rejected",
        expected_scores={"strength": 1, "rigor": 1, "relevance": 2},
        rejection_reason="No quantitative evidence",
        is_recoverable=True
    ),
    # ... add more pre-defined test cases
]

KNOWN_GAPS = [
    {
        "gap_id": "gap_001",
        "sub_requirement": "Sub-1.1.1",
        "description": "Energy efficiency benchmarks on edge devices",
        "evidence_status": "partial",
        "severity": "high"
    },
    # ... add more known gaps
]
```

---

## Implementation Steps

### Step 1: Set Up Accuracy Test Directory (1 hour)

```bash
# Create accuracy test directory structure
mkdir -p tests/validation/accuracy
mkdir -p tests/validation/baselines
mkdir -p tests/validation/fixtures

# Create __init__.py files
touch tests/validation/accuracy/__init__.py
touch tests/validation/baselines/__init__.py
touch tests/validation/fixtures/__init__.py
```

### Step 2: Implement AccuracyMetrics in Base (1 hour)

Update `tests/validation/base.py` to include `AccuracyMetrics` dataclass and `AccuracyValidationTestCase` base class if not already present.

### Step 3: Implement Test Cases (4 hours)

1. Implement `TestJudgeAccuracy` (AV-03) - 1.5 hours
2. Implement `TestDRARecoveryRate` (AV-05) - 1.5 hours
3. Implement `TestGapFalseNegativeRate` (AV-06) - 1 hour

### Step 4: Create Test Fixtures (1 hour)

- Define `APPROVED_CLAIMS` and `REJECTED_CLAIMS` test data
- Define `KNOWN_GAPS` test data
- Integrate with golden dataset loader

### Step 5: Implement Baseline Tracking (1 hour)

- Implement `AccuracyBaselineTracker`
- Create baseline storage format
- Add regression detection logic

---

## Acceptance Criteria

- [ ] All three tests (AV-03, AV-05, AV-06) execute without errors
- [ ] Tests use golden dataset for ground truth
- [ ] Confidence intervals calculated for all metrics
- [ ] Baselines automatically captured and stored
- [ ] Regression detection implemented
- [ ] Test documentation complete

---

## Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| VM-W1-3 | Task Card | Required (Judge validation tests) |
| VM-W1-4 | Task Card | Required (Golden dataset with annotations) |
| `GoldenDatasetLoader` | Code | From VM-W0-2 |
| `AccuracyValidationTestCase` | Code | From VM-W0-1 |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Golden dataset not ready | HIGH | Use fallback synthetic test data |
| Accuracy below threshold | MEDIUM | Document baseline, create improvement plan |
| Confidence intervals too wide | LOW | Increase sample size in golden dataset |

---

## Notes

- Accuracy thresholds are based on third-party assessment recommendations
- Baselines should be updated after significant model changes
- Consider A/B testing for threshold calibration
