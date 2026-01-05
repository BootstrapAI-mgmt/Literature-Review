# Golden Dataset

This directory contains the golden dataset infrastructure for accuracy validation,
calibration testing, and quality benchmarking of the Literature Review pipeline.

## Structure

```
tests/golden_dataset/
├── __init__.py           # Package exports
├── schema.py             # Pydantic models for validation
├── loader.py             # Dataset loading and querying utilities
├── test_schema.py        # Unit tests for schemas
├── README.md             # This file
└── data/
    ├── golden_dataset.json         # Full golden dataset (when created)
    └── golden_dataset_sample.json  # Sample dataset for development
```

## Quick Start

### Loading the Dataset

```python
from tests.golden_dataset import GoldenDatasetLoader, Verdict

# Load the sample dataset
loader = GoldenDatasetLoader(
    dataset_path=Path("tests/golden_dataset/data/golden_dataset_sample.json")
)
dataset = loader.load()

# Query claims by verdict
approved_claims = loader.get_claims_by_verdict(Verdict.APPROVED)
rejected_claims = loader.get_claims_by_verdict(Verdict.REJECTED)

# Get claims for specific test categories
precision_claims = loader.get_claims_for_test("precision")
calibration_claims = loader.get_claims_for_test("calibration")

# Get edge cases
edge_cases = loader.get_edge_cases()
```

### Using in Tests

```python
import pytest
from tests.golden_dataset import requires_golden_dataset, GoldenDatasetLoader, Verdict

class TestJudgeAccuracy:
    @requires_golden_dataset
    def test_judge_verdicts(self):
        """Test judge verdicts against golden dataset."""
        loader = GoldenDatasetLoader()
        
        for claim in loader.get_high_confidence_claims():
            # Run your judge against the claim
            actual_verdict = run_judge(claim.claim_text, claim.evidence_text)
            
            # Compare to expected verdict
            assert actual_verdict == claim.expected_verdict.value
```

### Validating the Dataset

```python
from tests.golden_dataset import GoldenDatasetLoader

loader = GoldenDatasetLoader()
loader.load()

validation = loader.validate_dataset()
print(f"Valid: {validation['valid']}")
print(f"Issues: {validation['issues']}")
print(f"Stats: {validation['stats']}")
```

## Schema Models

### AnnotatedClaim
A claim with human annotations for ground truth testing.

Key fields:
- `claim_id`: Unique identifier (pattern: GD-CLM-NNNN)
- `expected_verdict`: APPROVED, REJECTED, or BORDERLINE
- `evidence_quality`: Nested quality scores
- `test_categories`: List of test categories this claim is designed for

### ExpectedVerdict
Expected judge verdict with scoring ranges for calibration testing.

Key fields:
- `expected_composite_score_range`: Min/max expected score
- `true_positive_probability`: Probability for calibration analysis

### KnownGap
A gap with known correct identification for testing gap detection.

Key fields:
- `expected_severity`: CRITICAL, HIGH, MEDIUM, or LOW
- `database_state_file`: Path to database state JSON for testing

### RecommendationQuality
Gap with expected recommendation quality criteria.

Key fields:
- `expected_recommendation_themes`: Keywords/themes expected
- `reference_recommendation`: Expert-written reference

## Test Categories

Claims can be tagged with test categories:

- `precision`: For precision testing (should correctly approve)
- `recall`: For recall testing (should correctly reject)
- `calibration`: For calibration analysis (borderline cases)
- `judge_accuracy`: For general judge accuracy testing
- `pillar_mapping`: For pillar assignment testing
- `false_approval_prevention`: For testing rejection of weak evidence

## Documentation

- [Golden Dataset Requirements](../../docs/GOLDEN_DATASET_REQUIREMENTS.md) - Full requirements
- [Annotation Guidelines](../../docs/GOLDEN_DATASET_ANNOTATION_GUIDELINES.md) - How to annotate

## Running Tests

```bash
# Run golden dataset schema tests
pytest tests/golden_dataset/test_schema.py -v

# Run only unit tests
pytest tests/golden_dataset/test_schema.py -v -m unit
```

## Expanding the Dataset

To create a full golden dataset:

1. Follow the annotation guidelines in `docs/GOLDEN_DATASET_ANNOTATION_GUIDELINES.md`
2. Create annotations using the schema defined in `schema.py`
3. Save as `data/golden_dataset.json`
4. Run validation: `loader.validate_dataset()`

Target sizes:
- Annotated claims: 50+ samples
- Known gaps: 20+ samples
- Recommendation quality: 10+ samples
