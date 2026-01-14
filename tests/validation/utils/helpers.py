"""
Validation Helper Functions

Common utility functions for validation tests including accuracy calculations
and result validation.
"""

from typing import Dict, Optional

from tests.validation.base import ValidationResult


def calculate_precision(true_positives: int, false_positives: int) -> float:
    """
    Calculate precision: TP / (TP + FP).
    
    Args:
        true_positives: Number of true positive predictions
        false_positives: Number of false positive predictions
    
    Returns:
        Precision as a percentage (0-100)
    """
    total = true_positives + false_positives
    return (true_positives / total) * 100 if total > 0 else 0.0


def calculate_recall(true_positives: int, false_negatives: int) -> float:
    """
    Calculate recall: TP / (TP + FN).
    
    Args:
        true_positives: Number of true positive predictions
        false_negatives: Number of false negative predictions
    
    Returns:
        Recall as a percentage (0-100)
    """
    total = true_positives + false_negatives
    return (true_positives / total) * 100 if total > 0 else 0.0


def calculate_f1(precision: float, recall: float) -> float:
    """
    Calculate F1 score: 2 * (Precision * Recall) / (Precision + Recall).
    
    Args:
        precision: Precision value (percentage)
        recall: Recall value (percentage)
    
    Returns:
        F1 score as a percentage (0-100)
    """
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def validate_threshold(
    test_id: str,
    test_name: str,
    actual: float,
    threshold: float,
    comparison: str = "gte",
    metadata: Optional[Dict] = None
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
    
    Returns:
        ValidationResult with pass/fail status
    """
    if comparison == "gte":
        passed = actual >= threshold
    elif comparison == "lte":
        passed = actual <= threshold
    else:  # eq
        passed = abs(actual - threshold) < 0.001
    
    return ValidationResult(
        test_id=test_id,
        test_name=test_name,
        passed=passed,
        actual_value=actual,
        expected_value=f"{comparison} {threshold}",
        threshold=threshold,
        margin=actual - threshold,
        execution_time_ms=0.0,
        metadata=metadata or {}
    )


def validate_percentage(
    test_id: str,
    test_name: str,
    numerator: float,
    denominator: float,
    threshold_percent: float,
    comparison: str = "gte",
    metadata: Optional[Dict] = None
) -> ValidationResult:
    """
    Validate a percentage against threshold.
    
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
    
    if comparison == "gte":
        passed = actual >= threshold_percent
    elif comparison == "lte":
        passed = actual <= threshold_percent
    else:  # eq
        passed = abs(actual - threshold_percent) < 0.001
    
    return ValidationResult(
        test_id=test_id,
        test_name=test_name,
        passed=passed,
        actual_value=actual,
        expected_value=f"{comparison} {threshold_percent}",
        threshold=threshold_percent,
        margin=actual - threshold_percent,
        execution_time_ms=0.0,
        metadata={
            **(metadata or {}),
            "numerator": numerator,
            "denominator": denominator
        }
    )
