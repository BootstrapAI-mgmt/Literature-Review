# Task Card: Judge Calibration Analysis

**Task ID:** VM-W2-2  
**Wave:** 2 (Accuracy & Efficiency)  
**Priority:** MEDIUM  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W1-4  
**Blocks:** VM-W4-2  
**Validation IDs:** AV-04, AV-08

---

## Objective

Analyze Judge score calibration by measuring Brier score and human-AI correlation. Well-calibrated scores ensure predicted confidence matches actual accuracy.

## Background

**Calibration** measures whether the Judge's confidence scores are reliable:
- A score of 4/5 should mean the claim is approved ~80% of the time
- A score of 2/5 should mean the claim is rejected ~60% of the time

**Key Metrics:**
- **Brier Score (AV-04):** Measures accuracy of probabilistic predictions. Lower is better (0 = perfect, 1 = worst). Target: <0.15
- **Human Correlation (AV-08):** Pearson correlation between Judge scores and human expert scores. Target: r ≥ 0.8

Proper calibration is critical for:
1. Trust in AI decisions
2. Appropriate DRA triggering
3. Accurate gap severity assessment

## Success Criteria

- [ ] AV-04: Brier score < 0.15 (well-calibrated predictions)
- [ ] AV-08: Human correlation r ≥ 0.8 (high agreement)
- [ ] Calibration curves generated and analyzed
- [ ] Score distribution analysis complete
- [ ] Recommendations for calibration improvements documented

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| AV-04 | Brier Score | 50 claims with probabilities | `brier_score < 0.15` | Well-calibrated predictions |
| AV-08 | Human Correlation | Claims with human & AI scores | `pearson_r ≥ 0.8` | High agreement with experts |

---

## Deliverables

### 1. Test Implementation

**File:** `tests/validation/accuracy/test_judge_calibration.py`

```python
"""
Judge Calibration Analysis Tests

Validates AV-04 and AV-08 from the validation matrix.
Measures how well Judge confidence scores match actual outcomes.
"""

import pytest
import json
import math
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from tests.validation.base import AccuracyValidationTestCase, ValidationResult
from tests.golden_dataset.loader import GoldenDatasetLoader


@dataclass
class CalibrationBin:
    """Bin for calibration curve analysis."""
    bin_start: float
    bin_end: float
    predictions: List[float] = field(default_factory=list)
    outcomes: List[int] = field(default_factory=list)  # 0 = rejected, 1 = approved
    
    @property
    def mean_prediction(self) -> float:
        """Mean predicted probability in this bin."""
        return statistics.mean(self.predictions) if self.predictions else 0.0
    
    @property
    def actual_rate(self) -> float:
        """Actual approval rate in this bin."""
        return statistics.mean(self.outcomes) if self.outcomes else 0.0
    
    @property
    def count(self) -> int:
        """Number of samples in this bin."""
        return len(self.predictions)
    
    @property
    def calibration_error(self) -> float:
        """Absolute difference between predicted and actual."""
        return abs(self.mean_prediction - self.actual_rate)


@dataclass
class CalibrationReport:
    """Complete calibration analysis report."""
    brier_score: float
    expected_calibration_error: float  # ECE
    maximum_calibration_error: float   # MCE
    bins: List[CalibrationBin]
    total_samples: int
    reliability_diagram_data: Dict
    
    def to_dict(self) -> Dict:
        return {
            "brier_score": self.brier_score,
            "expected_calibration_error": self.expected_calibration_error,
            "maximum_calibration_error": self.maximum_calibration_error,
            "total_samples": self.total_samples,
            "bins": [
                {
                    "range": f"{b.bin_start:.1f}-{b.bin_end:.1f}",
                    "mean_prediction": b.mean_prediction,
                    "actual_rate": b.actual_rate,
                    "count": b.count,
                    "calibration_error": b.calibration_error
                }
                for b in self.bins
            ],
            "reliability_diagram_data": self.reliability_diagram_data
        }


class BrierScoreCalculator:
    """Calculate Brier score and related calibration metrics."""
    
    @staticmethod
    def brier_score(
        predictions: List[float],
        outcomes: List[int]
    ) -> float:
        """
        Calculate Brier score.
        
        Brier = (1/N) * Σ(prediction - outcome)²
        
        Where:
        - prediction = probability of approval (0-1)
        - outcome = 1 if approved, 0 if rejected
        
        Lower is better:
        - 0.0 = perfect predictions
        - 0.25 = random guessing (for 50/50 outcomes)
        - 1.0 = completely wrong
        """
        if len(predictions) != len(outcomes):
            raise ValueError("Predictions and outcomes must have same length")
        
        if not predictions:
            return 0.0
        
        squared_errors = [
            (pred - outcome) ** 2 
            for pred, outcome in zip(predictions, outcomes)
        ]
        
        return sum(squared_errors) / len(squared_errors)
    
    @staticmethod
    def decompose_brier(
        predictions: List[float],
        outcomes: List[int]
    ) -> Dict[str, float]:
        """
        Decompose Brier score into reliability, resolution, and uncertainty.
        
        Brier = Reliability - Resolution + Uncertainty
        
        - Reliability: How well calibrated (lower is better)
        - Resolution: How much predictions vary from base rate (higher is better)
        - Uncertainty: Inherent uncertainty in outcomes
        """
        n = len(predictions)
        if n == 0:
            return {"reliability": 0, "resolution": 0, "uncertainty": 0}
        
        # Base rate
        base_rate = sum(outcomes) / n
        uncertainty = base_rate * (1 - base_rate)
        
        # Bin predictions for reliability calculation
        bins = CalibrationAnalyzer.create_bins(predictions, outcomes, n_bins=10)
        
        reliability = sum(
            b.count * (b.mean_prediction - b.actual_rate) ** 2
            for b in bins
        ) / n
        
        resolution = sum(
            b.count * (b.actual_rate - base_rate) ** 2
            for b in bins
        ) / n
        
        return {
            "reliability": reliability,
            "resolution": resolution,
            "uncertainty": uncertainty
        }


class CalibrationAnalyzer:
    """Analyze calibration curves and metrics."""
    
    @staticmethod
    def create_bins(
        predictions: List[float],
        outcomes: List[int],
        n_bins: int = 10
    ) -> List[CalibrationBin]:
        """Create calibration bins from predictions and outcomes."""
        bins = []
        bin_width = 1.0 / n_bins
        
        for i in range(n_bins):
            bin_start = i * bin_width
            bin_end = (i + 1) * bin_width
            bins.append(CalibrationBin(bin_start=bin_start, bin_end=bin_end))
        
        for pred, outcome in zip(predictions, outcomes):
            bin_idx = min(int(pred * n_bins), n_bins - 1)
            bins[bin_idx].predictions.append(pred)
            bins[bin_idx].outcomes.append(outcome)
        
        return bins
    
    @staticmethod
    def expected_calibration_error(bins: List[CalibrationBin]) -> float:
        """
        Calculate Expected Calibration Error (ECE).
        
        ECE = Σ (|bin_samples| / total) * |accuracy(bin) - confidence(bin)|
        """
        total = sum(b.count for b in bins)
        if total == 0:
            return 0.0
        
        return sum(
            (b.count / total) * b.calibration_error
            for b in bins if b.count > 0
        )
    
    @staticmethod
    def maximum_calibration_error(bins: List[CalibrationBin]) -> float:
        """
        Calculate Maximum Calibration Error (MCE).
        
        MCE = max(|accuracy(bin) - confidence(bin)|)
        """
        errors = [b.calibration_error for b in bins if b.count > 0]
        return max(errors) if errors else 0.0
    
    @staticmethod
    def generate_reliability_diagram_data(
        bins: List[CalibrationBin]
    ) -> Dict:
        """Generate data for reliability diagram visualization."""
        return {
            "perfect_calibration": [(i/10, i/10) for i in range(11)],
            "model_calibration": [
                (b.mean_prediction, b.actual_rate)
                for b in bins if b.count > 0
            ],
            "bin_counts": [b.count for b in bins],
            "bin_ranges": [f"{b.bin_start:.1f}-{b.bin_end:.1f}" for b in bins]
        }


class CorrelationAnalyzer:
    """Analyze correlation between AI and human scores."""
    
    @staticmethod
    def pearson_correlation(
        x: List[float],
        y: List[float]
    ) -> Tuple[float, float]:
        """
        Calculate Pearson correlation coefficient.
        
        Returns:
            (correlation, p_value)
        """
        n = len(x)
        if n != len(y) or n < 3:
            return (0.0, 1.0)
        
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)
        
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        
        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)
        
        denominator = math.sqrt(sum_sq_x * sum_sq_y)
        
        if denominator == 0:
            return (0.0, 1.0)
        
        r = numerator / denominator
        
        # Calculate t-statistic and p-value
        t_stat = r * math.sqrt((n - 2) / (1 - r**2)) if abs(r) < 1 else float('inf')
        
        # Approximate p-value (two-tailed)
        # Using Student's t-distribution approximation
        df = n - 2
        p_value = 2 * (1 - CorrelationAnalyzer._t_cdf(abs(t_stat), df))
        
        return (r, p_value)
    
    @staticmethod
    def _t_cdf(t: float, df: int) -> float:
        """Approximate CDF of Student's t-distribution."""
        # Simple approximation for large df
        if df > 100:
            # Use normal approximation
            return 0.5 * (1 + math.erf(t / math.sqrt(2)))
        
        # Beta function approximation for smaller df
        x = df / (df + t**2)
        return 1 - 0.5 * CorrelationAnalyzer._incomplete_beta(df/2, 0.5, x)
    
    @staticmethod
    def _incomplete_beta(a: float, b: float, x: float) -> float:
        """Simple incomplete beta approximation."""
        # Very rough approximation
        return x ** a * (1 - x) ** b
    
    @staticmethod
    def spearman_correlation(
        x: List[float],
        y: List[float]
    ) -> float:
        """Calculate Spearman rank correlation."""
        n = len(x)
        if n != len(y) or n < 3:
            return 0.0
        
        # Rank the values
        x_ranks = CorrelationAnalyzer._rank(x)
        y_ranks = CorrelationAnalyzer._rank(y)
        
        # Calculate Pearson on ranks
        r, _ = CorrelationAnalyzer.pearson_correlation(x_ranks, y_ranks)
        return r
    
    @staticmethod
    def _rank(values: List[float]) -> List[float]:
        """Convert values to ranks (1-indexed)."""
        n = len(values)
        indexed = [(v, i) for i, v in enumerate(values)]
        indexed.sort()
        
        ranks = [0.0] * n
        for rank, (_, original_idx) in enumerate(indexed, 1):
            ranks[original_idx] = float(rank)
        
        return ranks


class TestBrierScore(AccuracyValidationTestCase):
    """
    AV-04: Brier Score Calibration Test
    
    Measures how well Judge confidence predictions match actual outcomes.
    Target: Brier score < 0.15
    """
    
    TEST_ID = "AV-04"
    TEST_CATEGORY = "AV"
    BRIER_THRESHOLD = 0.15
    
    @pytest.fixture
    def golden_dataset(self, tmp_path) -> GoldenDatasetLoader:
        """Load golden dataset."""
        loader = GoldenDatasetLoader(tmp_path / "golden_dataset")
        loader.load()
        return loader
    
    @pytest.fixture
    def judge_predictions(self, golden_dataset) -> Tuple[List[float], List[int]]:
        """
        Get Judge predictions and outcomes from golden dataset.
        
        Returns:
            (predictions, outcomes) where predictions are probabilities
            and outcomes are 0 (rejected) or 1 (approved)
        """
        claims = golden_dataset.get_claims_with_predictions()
        
        predictions = []
        outcomes = []
        
        for claim in claims:
            # Convert composite score to probability
            # Score 0-5 maps to probability 0-1
            composite = claim.get("judge_composite_score", 2.5)
            probability = min(1.0, max(0.0, composite / 5.0))
            predictions.append(probability)
            
            # Outcome: 1 if approved, 0 if rejected
            outcome = 1 if claim.get("expected_verdict") == "approved" else 0
            outcomes.append(outcome)
        
        return predictions, outcomes
    
    @pytest.mark.validation
    @pytest.mark.accuracy
    @pytest.mark.calibration
    @pytest.mark.requires_golden_dataset
    def test_av04_brier_score(self, judge_predictions):
        """
        AV-04: Brier score must be < 0.15.
        
        Process:
        1. Load 50 claims with Judge predictions
        2. Convert composite scores to probabilities
        3. Calculate Brier score against actual outcomes
        4. Generate calibration report
        """
        predictions, outcomes = judge_predictions
        
        assert len(predictions) >= 50, "Need at least 50 claims for calibration"
        
        # Calculate Brier score
        brier = BrierScoreCalculator.brier_score(predictions, outcomes)
        
        # Decompose for analysis
        decomposition = BrierScoreCalculator.decompose_brier(predictions, outcomes)
        
        # Generate calibration bins
        bins = CalibrationAnalyzer.create_bins(predictions, outcomes, n_bins=10)
        
        # Calculate calibration metrics
        ece = CalibrationAnalyzer.expected_calibration_error(bins)
        mce = CalibrationAnalyzer.maximum_calibration_error(bins)
        
        # Generate calibration report
        report = CalibrationReport(
            brier_score=brier,
            expected_calibration_error=ece,
            maximum_calibration_error=mce,
            bins=bins,
            total_samples=len(predictions),
            reliability_diagram_data=CalibrationAnalyzer.generate_reliability_diagram_data(bins)
        )
        
        # Save report
        self.save_calibration_report(report)
        
        # Create validation result
        validation_result = ValidationResult(
            test_id="AV-04",
            test_name="Brier Score Calibration",
            passed=brier < self.BRIER_THRESHOLD,
            actual_value=brier,
            expected_value=f"<{self.BRIER_THRESHOLD}",
            threshold=self.BRIER_THRESHOLD,
            margin=self.BRIER_THRESHOLD - brier,  # Positive margin is good
            metadata={
                "ece": ece,
                "mce": mce,
                "decomposition": decomposition,
                "sample_size": len(predictions),
                "non_empty_bins": len([b for b in bins if b.count > 0])
            }
        )
        
        self.record_result(validation_result)
        
        # Log calibration details for debugging
        self.log_calibration_details(report, decomposition)
        
        assert brier < self.BRIER_THRESHOLD, (
            f"AV-04 FAILED: Brier score {brier:.4f} >= {self.BRIER_THRESHOLD} threshold.\n"
            f"ECE: {ece:.4f}, MCE: {mce:.4f}\n"
            f"Decomposition: reliability={decomposition['reliability']:.4f}, "
            f"resolution={decomposition['resolution']:.4f}, "
            f"uncertainty={decomposition['uncertainty']:.4f}"
        )
    
    def save_calibration_report(self, report: CalibrationReport):
        """Save calibration report to file."""
        report_path = Path("tests/validation/reports/calibration_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report.to_dict(), indent=2))
    
    def log_calibration_details(self, report: CalibrationReport, decomposition: Dict):
        """Log detailed calibration analysis."""
        print("\n" + "=" * 60)
        print("CALIBRATION ANALYSIS")
        print("=" * 60)
        print(f"\nBrier Score: {report.brier_score:.4f}")
        print(f"ECE (Expected Calibration Error): {report.expected_calibration_error:.4f}")
        print(f"MCE (Maximum Calibration Error): {report.maximum_calibration_error:.4f}")
        print("\nBrier Decomposition:")
        print(f"  Reliability: {decomposition['reliability']:.4f} (lower is better)")
        print(f"  Resolution: {decomposition['resolution']:.4f} (higher is better)")
        print(f"  Uncertainty: {decomposition['uncertainty']:.4f} (inherent)")
        print("\nCalibration Bins:")
        print("-" * 50)
        print(f"{'Range':<12} {'Predicted':>10} {'Actual':>10} {'Count':>8} {'Error':>8}")
        print("-" * 50)
        for b in report.bins:
            if b.count > 0:
                print(
                    f"{b.bin_start:.1f}-{b.bin_end:.1f}   "
                    f"{b.mean_prediction:>10.3f} {b.actual_rate:>10.3f} "
                    f"{b.count:>8} {b.calibration_error:>8.3f}"
                )
        print("=" * 60)


class TestHumanCorrelation(AccuracyValidationTestCase):
    """
    AV-08: Human-AI Correlation Test
    
    Measures correlation between Judge scores and human expert scores.
    Target: Pearson r ≥ 0.8
    """
    
    TEST_ID = "AV-08"
    TEST_CATEGORY = "AV"
    CORRELATION_THRESHOLD = 0.8
    
    @pytest.fixture
    def paired_scores(self, golden_dataset) -> Tuple[List[float], List[float]]:
        """
        Get paired human and AI scores from golden dataset.
        
        Returns:
            (ai_scores, human_scores)
        """
        claims = golden_dataset.get_claims_with_human_annotations()
        
        ai_scores = []
        human_scores = []
        
        for claim in claims:
            ai_composite = claim.get("judge_composite_score")
            human_composite = claim.get("human_composite_score")
            
            if ai_composite is not None and human_composite is not None:
                ai_scores.append(ai_composite)
                human_scores.append(human_composite)
        
        return ai_scores, human_scores
    
    @pytest.mark.validation
    @pytest.mark.accuracy
    @pytest.mark.calibration
    @pytest.mark.requires_golden_dataset
    def test_av08_human_correlation(self, paired_scores):
        """
        AV-08: Pearson correlation must be ≥ 0.8.
        
        Process:
        1. Load claims with paired human & AI scores
        2. Calculate Pearson and Spearman correlations
        3. Analyze dimension-by-dimension agreement
        """
        ai_scores, human_scores = paired_scores
        
        assert len(ai_scores) >= 50, "Need at least 50 paired scores"
        
        # Calculate Pearson correlation
        pearson_r, p_value = CorrelationAnalyzer.pearson_correlation(
            ai_scores, human_scores
        )
        
        # Calculate Spearman for robustness check
        spearman_r = CorrelationAnalyzer.spearman_correlation(
            ai_scores, human_scores
        )
        
        # Calculate agreement statistics
        agreement_stats = self.calculate_agreement_stats(ai_scores, human_scores)
        
        # Create validation result
        validation_result = ValidationResult(
            test_id="AV-08",
            test_name="Human-AI Correlation",
            passed=pearson_r >= self.CORRELATION_THRESHOLD,
            actual_value=pearson_r,
            expected_value=f"≥{self.CORRELATION_THRESHOLD}",
            threshold=self.CORRELATION_THRESHOLD,
            margin=pearson_r - self.CORRELATION_THRESHOLD,
            metadata={
                "spearman_r": spearman_r,
                "p_value": p_value,
                "sample_size": len(ai_scores),
                "agreement_stats": agreement_stats
            }
        )
        
        self.record_result(validation_result)
        
        # Save correlation report
        self.save_correlation_report(
            pearson_r, spearman_r, p_value, agreement_stats, len(ai_scores)
        )
        
        assert pearson_r >= self.CORRELATION_THRESHOLD, (
            f"AV-08 FAILED: Pearson r = {pearson_r:.3f} < "
            f"{self.CORRELATION_THRESHOLD} threshold.\n"
            f"Spearman r = {spearman_r:.3f}, p-value = {p_value:.4f}\n"
            f"Sample size: {len(ai_scores)}"
        )
    
    def calculate_agreement_stats(
        self,
        ai_scores: List[float],
        human_scores: List[float]
    ) -> Dict:
        """Calculate detailed agreement statistics."""
        differences = [abs(ai - human) for ai, human in zip(ai_scores, human_scores)]
        
        return {
            "mean_absolute_difference": statistics.mean(differences),
            "max_difference": max(differences),
            "std_difference": statistics.stdev(differences) if len(differences) > 1 else 0,
            "exact_match_rate": sum(1 for d in differences if d < 0.1) / len(differences),
            "within_0.5_rate": sum(1 for d in differences if d <= 0.5) / len(differences),
            "within_1.0_rate": sum(1 for d in differences if d <= 1.0) / len(differences)
        }
    
    def save_correlation_report(
        self,
        pearson_r: float,
        spearman_r: float,
        p_value: float,
        agreement_stats: Dict,
        sample_size: int
    ):
        """Save correlation report to file."""
        report = {
            "test_id": "AV-08",
            "pearson_r": pearson_r,
            "spearman_r": spearman_r,
            "p_value": p_value,
            "sample_size": sample_size,
            "agreement_stats": agreement_stats,
            "generated_at": datetime.now().isoformat()
        }
        
        report_path = Path("tests/validation/reports/correlation_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))


# ============================================================================
# Calibration Curve Generator
# ============================================================================

class CalibrationCurveGenerator:
    """Generate calibration curve visualizations."""
    
    @staticmethod
    def generate_reliability_diagram_script(
        output_path: Path,
        report: CalibrationReport
    ):
        """
        Generate Python script for reliability diagram.
        
        This creates a matplotlib-based visualization script.
        """
        script = f'''"""
Reliability Diagram Generator

Generated automatically from calibration analysis.
"""

import matplotlib.pyplot as plt
import numpy as np

# Data from calibration report
bin_ranges = {report.reliability_diagram_data['bin_ranges']}
model_calibration = {report.reliability_diagram_data['model_calibration']}
bin_counts = {report.reliability_diagram_data['bin_counts']}

# Extract x and y for model calibration
if model_calibration:
    x_model = [p[0] for p in model_calibration]
    y_model = [p[1] for p in model_calibration]
else:
    x_model, y_model = [], []

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Reliability Diagram
ax1.plot([0, 1], [0, 1], 'k--', label='Perfect Calibration')
ax1.scatter(x_model, y_model, s=100, c='blue', alpha=0.7, label='Model')
ax1.set_xlabel('Mean Predicted Probability')
ax1.set_ylabel('Fraction of Positives')
ax1.set_title(f'Reliability Diagram\\nBrier Score: {report.brier_score:.4f}')
ax1.legend()
ax1.set_xlim([0, 1])
ax1.set_ylim([0, 1])
ax1.grid(True, alpha=0.3)

# Histogram of predictions
ax2.bar(range(len(bin_counts)), bin_counts, tick_label=bin_ranges)
ax2.set_xlabel('Predicted Probability Bin')
ax2.set_ylabel('Count')
ax2.set_title('Prediction Distribution')
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('{output_path / "reliability_diagram.png"}')
plt.close()

print(f"Saved reliability diagram to {output_path / 'reliability_diagram.png'}")
'''
        script_path = output_path / "generate_reliability_diagram.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script)


# ============================================================================
# Score Distribution Analyzer
# ============================================================================

class ScoreDistributionAnalyzer:
    """Analyze distribution of Judge scores."""
    
    @staticmethod
    def analyze_distribution(scores: List[float]) -> Dict:
        """Analyze score distribution statistics."""
        if not scores:
            return {}
        
        return {
            "count": len(scores),
            "mean": statistics.mean(scores),
            "median": statistics.median(scores),
            "std": statistics.stdev(scores) if len(scores) > 1 else 0,
            "min": min(scores),
            "max": max(scores),
            "quartiles": {
                "q1": ScoreDistributionAnalyzer._percentile(scores, 25),
                "q2": ScoreDistributionAnalyzer._percentile(scores, 50),
                "q3": ScoreDistributionAnalyzer._percentile(scores, 75)
            },
            "skewness": ScoreDistributionAnalyzer._skewness(scores),
            "kurtosis": ScoreDistributionAnalyzer._kurtosis(scores)
        }
    
    @staticmethod
    def _percentile(data: List[float], p: float) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_data[int(k)]
        return sorted_data[int(f)] * (c - k) + sorted_data[int(c)] * (k - f)
    
    @staticmethod
    def _skewness(data: List[float]) -> float:
        """Calculate skewness."""
        n = len(data)
        if n < 3:
            return 0.0
        
        mean = statistics.mean(data)
        std = statistics.stdev(data)
        
        if std == 0:
            return 0.0
        
        return sum((x - mean) ** 3 for x in data) / (n * std ** 3)
    
    @staticmethod
    def _kurtosis(data: List[float]) -> float:
        """Calculate kurtosis."""
        n = len(data)
        if n < 4:
            return 0.0
        
        mean = statistics.mean(data)
        std = statistics.stdev(data)
        
        if std == 0:
            return 0.0
        
        return sum((x - mean) ** 4 for x in data) / (n * std ** 4) - 3
```

---

## Implementation Steps

### Step 1: Create Test Structure (30 min)

```bash
mkdir -p tests/validation/reports
touch tests/validation/accuracy/__init__.py
```

### Step 2: Implement Core Calculators (2 hours)

1. `BrierScoreCalculator` - Brier score and decomposition
2. `CalibrationAnalyzer` - Bin creation and ECE/MCE
3. `CorrelationAnalyzer` - Pearson and Spearman correlation

### Step 3: Implement Tests (3 hours)

1. `TestBrierScore` (AV-04) - 1.5 hours
2. `TestHumanCorrelation` (AV-08) - 1.5 hours

### Step 4: Implement Visualization (1.5 hours)

1. `CalibrationCurveGenerator` - Reliability diagram script
2. `ScoreDistributionAnalyzer` - Distribution statistics

### Step 5: Integration & Documentation (1 hour)

- Integrate with golden dataset
- Document interpretation guidelines
- Create calibration improvement recommendations

---

## Acceptance Criteria

- [ ] AV-04: Brier score calculated and tested against threshold
- [ ] AV-08: Pearson correlation calculated and tested
- [ ] Calibration bins correctly created
- [ ] ECE and MCE metrics calculated
- [ ] Correlation p-value calculated
- [ ] Reliability diagram script generated
- [ ] Score distribution analysis complete
- [ ] Reports saved to `tests/validation/reports/`

---

## Interpretation Guidelines

### Brier Score Interpretation

| Brier Score | Interpretation |
|-------------|----------------|
| 0.00 - 0.10 | Excellent calibration |
| 0.10 - 0.15 | Good calibration (target) |
| 0.15 - 0.25 | Fair calibration, needs improvement |
| 0.25+ | Poor calibration, significant issues |

### Correlation Interpretation

| Pearson r | Interpretation |
|-----------|----------------|
| 0.90 - 1.00 | Very strong agreement |
| 0.80 - 0.89 | Strong agreement (target) |
| 0.70 - 0.79 | Moderate agreement |
| < 0.70 | Weak agreement, investigate |

---

## Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| VM-W1-4 | Task Card | Required (Golden dataset with human annotations) |
| `GoldenDatasetLoader` | Code | From VM-W0-2 |
| `AccuracyValidationTestCase` | Code | From VM-W0-1 |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Insufficient human annotations | HIGH | Prioritize annotation of diverse claims |
| Low correlation discovered | MEDIUM | Analyze by dimension, identify systematic biases |
| Calibration issues | MEDIUM | Implement temperature scaling or Platt calibration |

---

## Calibration Improvement Recommendations

If calibration fails, consider:

1. **Temperature Scaling:** Divide logits by temperature T to calibrate
2. **Platt Scaling:** Fit sigmoid to map scores to probabilities
3. **Isotonic Regression:** Non-parametric calibration method
4. **Histogram Binning:** Assign calibrated probabilities per bin

These can be implemented as post-processing steps without retraining.
