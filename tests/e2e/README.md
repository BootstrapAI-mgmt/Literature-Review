# End-to-End (E2E) Tests

This directory contains end-to-end tests that validate the complete literature review pipeline from PDF ingestion to CSV export.

## Test Files

### test_full_pipeline.py
Comprehensive E2E tests for the complete literature review workflow (Task Card #10: E2E-001).

**Tests Included:**

1. **test_complete_pipeline_single_paper**
   - Tests the full pipeline for a single paper
   - Flow: PDF → Journal-Reviewer → Judge → CSV
   - Validates version history tracking and CSV sync
   - Verifies performance (<60s per paper)

2. **test_complete_pipeline_multiple_papers**
   - Tests batch processing of multiple papers
   - Flow: [PDF1, PDF2, PDF3] → Reviewers → Judge → CSV
   - Validates all papers are processed correctly
   - Ensures CSV aggregates claims from multiple sources

3. **test_pipeline_data_integrity**
   - Validates data integrity throughout the pipeline
   - Ensures no data loss during processing
   - Verifies field preservation and JSON serialization
   - Checks that only approved claims appear in CSV

4. **test_complete_evidence_quality_workflow**
   - Tests all evidence quality enhancements
   - Validates multi-dimensional quality scoring (strength, rigor, relevance, directness, reproducibility)
   - Verifies provenance metadata tracking from extraction to CSV
   - Tests evidence triangulation across Journal and Deep reviewers
   - Validates quality thresholds are enforced (composite ≥3.0 for approval)
   - Checks complete audit trail in version history

5. **test_pipeline_audit_trail_completeness**
   - Tests complete audit trail in version history
   - Validates all component executions are logged
   - Ensures timestamps are preserved
   - Verifies status transitions are tracked
   - Checks quality score evolution over time

6. **test_pipeline_idempotency**
   - Tests that the pipeline can be rerun safely
   - Validates that reprocessing the same paper doesn't corrupt data
   - Ensures version history maintains integrity

### test_infrastructure.py
Basic infrastructure tests to verify E2E test fixtures work correctly.

## Running the Tests

### Run all E2E tests:
```bash
pytest tests/e2e/ -v
```

### Run specific test file:
```bash
pytest tests/e2e/test_full_pipeline.py -v
```

### Run specific test:
```bash
pytest tests/e2e/test_full_pipeline.py::TestFullPipeline::test_complete_pipeline_single_paper -v
```

### Run with coverage:
```bash
pytest tests/e2e/ --cov=literature_review --cov-report=html
```

### Run with performance profiling:
```bash
pytest tests/e2e/test_full_pipeline.py -v --durations=10
```

## Test Markers

All E2E tests are marked with `@pytest.mark.e2e`. You can run only E2E tests using:

```bash
pytest -m e2e -v
```

## Test Fixtures

E2E tests use the following fixtures defined in `conftest.py`:

- **e2e_workspace**: Creates a complete workspace with all required directories and file paths
- **e2e_sample_papers**: Creates sample PDF files for testing
- **test_data_generator**: Provides utilities for generating test data
- **temp_dir**: Provides a temporary directory (auto-cleanup after test)

## Test Data

Tests use mock PDF files and simulated reviewer outputs to avoid dependencies on:
- Real PDF parsing
- Gemini API calls
- External services

This ensures tests are:
- Fast (complete in <1 second per test)
- Deterministic (same results every run)
- Isolated (no external dependencies)

## Success Criteria

All E2E tests validate:
- ✅ Complete PDF → CSV pipeline works
- ✅ All components execute in sequence
- ✅ Version history tracks full workflow
- ✅ Final CSV contains approved claims only
- ✅ Data integrity maintained end-to-end
- ✅ Multi-dimensional quality scores computed
- ✅ Provenance metadata tracked from extraction to CSV
- ✅ Evidence triangulation across reviewers
- ✅ Quality thresholds enforced (composite ≥3.0 for approval)
- ✅ Complete audit trail in version history
- ✅ Pipeline can be rerun safely (idempotency)
- ✅ Processing time acceptable (<60s per paper)

## Dependencies

E2E tests require:
- pytest>=7.4.0
- pytest-cov>=4.1.0
- pandas>=2.0.0

All dependencies are listed in `requirements-dev.txt`.

## Related Documentation

- [Integration Testing Guide](../INTEGRATION_TESTING_GUIDE.md)
- [Test Fixtures Documentation](../fixtures/README.md)
- Task Card #10: E2E-001 Full Pipeline Test
- Task Card #9: Orchestrator Integration Tests
- Task Cards #16-21: Evidence Quality Enhancement Tests
