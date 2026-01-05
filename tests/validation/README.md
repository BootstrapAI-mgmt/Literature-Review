# Validation Matrix Tests

This directory contains tests organized according to the validation matrix for the Literature Review system.

## Directory Structure

```
validation/
├── __init__.py
├── conftest.py          # Validation-specific fixtures
├── base.py              # ValidationTestCase base classes
├── functional/          # FV-* tests (Functional Validation)
│   ├── __init__.py
│   ├── test_pdf_extraction.py
│   ├── test_claim_identification.py
│   └── test_judge_decisions.py
├── accuracy/            # AV-* tests (Accuracy Validation)
│   ├── __init__.py
│   ├── test_accuracy_baseline.py
│   └── test_judge_calibration.py
├── efficiency/          # EV-* tests (Efficiency Validation)
│   ├── __init__.py
│   ├── test_efficiency_metrics.py
│   └── test_cost_tracking.py
└── outputs/             # OQ-*, RA-*, VI-* tests
    ├── __init__.py
    ├── schemas/         # JSON schema definitions
    └── test_output_schemas.py
```

## Base Classes

### ValidationTestCase

Base class for all validation tests. Provides:

- **Test identification**: Consistent ID structure (FV-*, AV-*, EV-*)
- **Result tracking**: Automatic collection of validation results
- **Threshold validation**: `validate_threshold()` for pass/fail checks
- **Timing**: Automatic execution time measurement

```python
from tests.validation.base import ValidationTestCase, ValidationResult

class TestPDFExtraction(ValidationTestCase):
    TEST_CATEGORY = "FV"
    
    def test_extraction_accuracy(self):
        # Your test logic
        actual_accuracy = calculate_accuracy()
        
        result = self.validate_threshold(
            test_id="FV-01",
            test_name="PDF Text Extraction",
            actual=actual_accuracy,
            threshold=95.0,
            comparison="gte"
        )
        
        assert result.passed
```

### AccuracyValidationTestCase

Extended base class for accuracy validation (AV-*) tests:

- **Precision/Recall**: `calculate_precision()`, `calculate_recall()`
- **F1 Score**: `calculate_f1()`
- **Brier Score**: `calculate_brier_score()` for calibration

```python
from tests.validation.base import AccuracyValidationTestCase

class TestJudgeCalibration(AccuracyValidationTestCase):
    def test_calibration(self):
        precision = self.calculate_precision(true_positives=85, false_positives=5)
        recall = self.calculate_recall(true_positives=85, false_negatives=10)
        f1 = self.calculate_f1(precision, recall)
        
        result = self.validate_threshold(
            test_id="AV-03",
            test_name="Judge Calibration F1",
            actual=f1,
            threshold=85.0,
            comparison="gte"
        )
        
        assert result.passed
```

### EfficiencyValidationTestCase

Extended base class for efficiency validation (EV-*) tests:

- **Execution timing**: `measure_execution_time()`
- **Speedup calculation**: `calculate_speedup()`

```python
from tests.validation.base import EfficiencyValidationTestCase

class TestProcessingSpeed(EfficiencyValidationTestCase):
    def test_paper_processing_time(self):
        result, elapsed = self.measure_execution_time(
            process_paper, paper_path
        )
        
        validation = self.validate_threshold(
            test_id="EV-01",
            test_name="Paper Processing Time",
            actual=elapsed * 1000,  # Convert to ms
            threshold=45000,
            comparison="lte"
        )
        
        assert validation.passed
```

## Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.validation
@pytest.mark.functional
def test_pdf_extraction():
    ...

@pytest.mark.validation
@pytest.mark.accuracy
def test_judge_calibration():
    ...

@pytest.mark.validation
@pytest.mark.efficiency
def test_processing_speed():
    ...
```

## Fixtures

Common fixtures available in `conftest.py`:

- `validation_workspace`: Temporary workspace with standard directories
- `sample_claims`: Sample claims for testing
- `validation_pillar_definitions`: Minimal pillar definitions
- `golden_dataset_dir`: Golden dataset directory structure

## Running Validation Tests

```bash
# Run all validation tests
pytest tests/validation/ -m validation

# Run specific category
pytest tests/validation/functional/ -m functional
pytest tests/validation/accuracy/ -m accuracy
pytest tests/validation/efficiency/ -m efficiency

# Run with verbose output
pytest tests/validation/ -v --tb=short
```

## Saving Results

Validation results can be saved for CI/CD reporting:

```python
class TestSuite(ValidationTestCase):
    def teardown_class(cls):
        if cls.results:
            cls.save_results(output_dir="validation_results")
```
