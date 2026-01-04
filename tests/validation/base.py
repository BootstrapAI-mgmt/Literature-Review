"""
Validation Test Base Classes

Provides base classes and utilities for validation matrix tests.
"""

import pytest
import time
import json
import os
from abc import ABC
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of a validation test."""
    test_id: str                          # e.g., "FV-01", "AV-03"
    test_name: str
    passed: bool
    actual_value: Any
    expected_value: Any
    threshold: Optional[float] = None
    margin: Optional[float] = None        # How close to threshold
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def margin_percentage(self) -> Optional[float]:
        """Calculate margin as percentage of threshold."""
        if self.threshold and isinstance(self.actual_value, (int, float)):
            return ((self.actual_value - self.threshold) / self.threshold) * 100
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "passed": self.passed,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "threshold": self.threshold,
            "margin": self.margin,
            "margin_percentage": self.margin_percentage,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class ValidationTestCase(ABC):
    """
    Base class for validation matrix tests.
    
    Provides consistent structure for:
    - Test identification (FV-*, AV-*, EV-*)
    - Result tracking and reporting
    - Threshold validation
    - Execution timing
    """
    
    # Override in subclasses
    TEST_CATEGORY = "FV"  # FV, AV, EV, QB, BM, E2E
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.start_time: Optional[float] = None
    
    def setup_method(self, method):
        """Called before each test method."""
        self.start_time = time.perf_counter()
    
    def teardown_method(self, method):
        """Called after each test method."""
        pass
    
    def get_execution_time_ms(self) -> float:
        """Get execution time since setup."""
        if self.start_time:
            return (time.perf_counter() - self.start_time) * 1000
        return 0.0
    
    def validate_threshold(
        self,
        test_id: str,
        test_name: str,
        actual: float,
        threshold: float,
        comparison: str = "gte",  # gte, lte, eq
        metadata: Optional[Dict] = None,
        tolerance: float = 0.001
    ) -> ValidationResult:
        """
        Validate a value against a threshold.
        
        Args:
            test_id: Validation matrix ID (e.g., "FV-01")
            test_name: Human-readable test name
            actual: Actual measured value
            threshold: Expected threshold
            comparison: "gte" (>=), "lte" (<=), "eq" (==)
            metadata: Additional test metadata
            tolerance: Tolerance for equality comparison (default: 0.001)
        
        Returns:
            ValidationResult with pass/fail status
        """
        if comparison == "gte":
            passed = actual >= threshold
        elif comparison == "lte":
            passed = actual <= threshold
        else:  # eq
            passed = abs(actual - threshold) < tolerance
        
        result = ValidationResult(
            test_id=test_id,
            test_name=test_name,
            passed=passed,
            actual_value=actual,
            expected_value=f"{comparison} {threshold}",
            threshold=threshold,
            margin=actual - threshold,
            execution_time_ms=self.get_execution_time_ms(),
            metadata=metadata or {}
        )
        
        self.results.append(result)
        return result
    
    def validate_percentage(
        self,
        test_id: str,
        test_name: str,
        numerator: float,
        denominator: float,
        threshold_percent: float,
        comparison: str = "gte",
        metadata: Optional[Dict] = None
    ) -> ValidationResult:
        """Validate a percentage against threshold.
        
        Args:
            test_id: Validation matrix ID (e.g., "AV-01")
            test_name: Human-readable test name
            numerator: Numerator value (int or float)
            denominator: Denominator value (int or float)
            threshold_percent: Expected threshold percentage
            comparison: "gte" (>=), "lte" (<=), "eq" (==)
            metadata: Additional test metadata
        
        Returns:
            ValidationResult with pass/fail status
        """
        if denominator == 0:
            actual = 0.0
        else:
            actual = (numerator / denominator) * 100
        
        return self.validate_threshold(
            test_id=test_id,
            test_name=test_name,
            actual=actual,
            threshold=threshold_percent,
            comparison=comparison,
            metadata={
                **(metadata or {}),
                "numerator": numerator,
                "denominator": denominator
            }
        )
    
    def save_results(self, output_dir: str = "validation_results"):
        """Save validation results to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        
        results_file = os.path.join(
            output_dir,
            f"{self.TEST_CATEGORY}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(results_file, 'w') as f:
            json.dump(
                {
                    "category": self.TEST_CATEGORY,
                    "timestamp": datetime.now().isoformat(),
                    "total_tests": len(self.results),
                    "passed": sum(1 for r in self.results if r.passed),
                    "failed": sum(1 for r in self.results if not r.passed),
                    "results": [r.to_dict() for r in self.results]
                },
                f,
                indent=2
            )
        
        return results_file


class AccuracyValidationTestCase(ValidationTestCase):
    """Base class for accuracy validation tests (AV-*)."""
    TEST_CATEGORY = "AV"
    
    def calculate_precision(
        self,
        true_positives: int,
        false_positives: int
    ) -> float:
        """Calculate precision: TP / (TP + FP)."""
        total = true_positives + false_positives
        return (true_positives / total) * 100 if total > 0 else 0.0
    
    def calculate_recall(
        self,
        true_positives: int,
        false_negatives: int
    ) -> float:
        """Calculate recall: TP / (TP + FN)."""
        total = true_positives + false_negatives
        return (true_positives / total) * 100 if total > 0 else 0.0
    
    def calculate_f1(self, precision: float, recall: float) -> float:
        """Calculate F1 score."""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    def calculate_brier_score(
        self,
        predictions: List[float],
        outcomes: List[int]
    ) -> float:
        """
        Calculate Brier score for calibration.
        
        Lower is better. Perfect calibration = 0.
        """
        if len(predictions) != len(outcomes):
            raise ValueError("Predictions and outcomes must have same length")
        
        n = len(predictions)
        if n == 0:
            return 0.0
        
        return sum((p - o) ** 2 for p, o in zip(predictions, outcomes)) / n


class EfficiencyValidationTestCase(ValidationTestCase):
    """Base class for efficiency validation tests (EV-*)."""
    TEST_CATEGORY = "EV"
    
    def measure_execution_time(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """
        Measure execution time of a function.
        
        Returns:
            Tuple of (result, execution_time_seconds)
        """
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return result, elapsed
    
    def calculate_speedup(
        self,
        baseline_time: float,
        optimized_time: float
    ) -> float:
        """Calculate speedup percentage."""
        if baseline_time == 0:
            return 0.0
        return ((baseline_time - optimized_time) / baseline_time) * 100
