# End-to-End (E2E) Tests

This directory contains end-to-end tests that validate:
1. Complete literature review pipeline from PDF ingestion to CSV export
2. Web dashboard workflows using browser automation

## Test Files

### test_dashboard_workflows.py ⭐ NEW
Browser-based E2E tests for the web dashboard using Playwright.

**Test Classes:**

1. **TestDashboardWorkflows** - Basic dashboard functionality
   - `test_dashboard_loads`: Verifies dashboard home page loads
   - `test_upload_pdf_workflow`: Tests PDF upload flow
   - `test_jobs_list_visible`: Validates jobs section renders
   - `test_api_health_check`: Tests health endpoint via browser
   - `test_navigation_elements`: Verifies UI elements are present

2. **TestDashboardAdvancedWorkflows** - Advanced features
   - `test_multiple_page_loads`: Performance testing for page loads
   - `test_console_errors`: Detects JavaScript errors
   - `test_responsive_layout`: Tests different screen sizes

3. **TestDashboardPerformance** - Performance benchmarks
   - `test_page_load_performance`: Measures DOM load times
   - `test_api_response_time`: Tests API endpoint speed

**Prerequisites:**
```bash
# Install Playwright
pip install -r requirements-dev.txt
playwright install chromium

# Start dashboard
python webdashboard/app.py
```

**Running Dashboard Tests:**
```bash
# All dashboard E2E tests
pytest tests/e2e/test_dashboard_workflows.py -m e2e_dashboard -v

# With visible browser (debug mode)
pytest tests/e2e/test_dashboard_workflows.py -m e2e_dashboard --headed --slowmo=1000

# Performance tests only
pytest tests/e2e/test_dashboard_workflows.py -m performance -v
```

See [Testing Guide](../../docs/TESTING_GUIDE.md) for detailed dashboard testing documentation.

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

E2E tests use the following markers:

- `@pytest.mark.e2e`: Full pipeline E2E tests
- `@pytest.mark.e2e_dashboard`: Dashboard browser-based E2E tests
- `@pytest.mark.slow`: Tests that take >5 seconds
- `@pytest.mark.performance`: Performance benchmark tests

**Run E2E tests by marker:**
```bash
# Pipeline E2E tests only
pytest -m "e2e and not e2e_dashboard" -v

# Dashboard E2E tests only
pytest -m e2e_dashboard -v

# All E2E tests
pytest -m "e2e or e2e_dashboard" -v
```

## Test Fixtures

E2E tests use the following fixtures defined in `conftest.py`:

- **e2e_workspace**: Creates a complete workspace with all required directories and file paths
- **e2e_sample_papers**: Creates sample PDF files for testing
- **dashboard_test_pdf**: Creates a minimal test PDF for dashboard upload tests
- **browser_context_args**: Configures Playwright browser context (viewport, HTTPS settings)
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

**Pipeline Tests:**
- pytest>=7.4.0
- pytest-cov>=4.1.0
- pandas>=2.0.0

**Dashboard Tests:**
- playwright>=1.40.0
- pytest-playwright>=0.4.3

All dependencies are listed in `requirements-dev.txt`.

## Related Documentation

- [Integration Testing Guide](../INTEGRATION_TESTING_GUIDE.md)
- [Test Fixtures Documentation](../fixtures/README.md)
- Task Card #10: E2E-001 Full Pipeline Test
- Task Card #9: Orchestrator Integration Tests
- Task Cards #16-21: Evidence Quality Enhancement Tests
