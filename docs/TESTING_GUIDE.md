# Testing Guide

This guide covers all testing practices for the Literature Review system, including unit tests, integration tests, and end-to-end (E2E) tests.

## Table of Contents

1. [Overview](#overview)
2. [Test Types](#test-types)
3. [Running Tests](#running-tests)
4. [End-to-End Dashboard Tests](#end-to-end-dashboard-tests)
5. [Writing Tests](#writing-tests)
6. [CI/CD Integration](#cicd-integration)
7. [Troubleshooting](#troubleshooting)

## Overview

The testing infrastructure follows the test pyramid approach:

```
      /\
     /  \  E2E Tests (70+ coverage)
    /____\
   /      \  Integration Tests (80+ coverage)
  /________\
 /          \  Unit Tests (90+ coverage)
/____________\
```

### Test Coverage Goals

- **Unit Tests**: 90%+ (fast, isolated tests)
- **Integration Tests**: 80%+ (component interaction tests)
- **E2E Tests**: 70%+ (full workflow tests)

## Test Types

### Unit Tests

Located in `tests/unit/`, these test individual functions and classes in isolation.

**Markers**: `@pytest.mark.unit`

**Example**:
```python
@pytest.mark.unit
def test_extract_paper_metadata():
    """Test metadata extraction from paper"""
    metadata = extract_metadata(sample_paper)
    assert metadata["title"] is not None
```

### Component Tests

Located in `tests/component/`, these test multiple components working together with mocks.

**Markers**: `@pytest.mark.component`

### Integration Tests

Located in `tests/integration/`, these test full subsystems without mocks.

**Markers**: `@pytest.mark.integration`

### End-to-End Tests

Located in `tests/e2e/`, these test complete workflows.

**Markers**: `@pytest.mark.e2e`

### Dashboard E2E Tests

Located in `tests/e2e/test_dashboard_workflows.py`, these test the web dashboard using Playwright.

**Markers**: `@pytest.mark.e2e_dashboard`

## Running Tests

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Install Playwright Browsers** (for E2E dashboard tests):
   ```bash
   playwright install
   ```

### Running All Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html
```

### Running Specific Test Types

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# E2E tests only
pytest -m e2e

# Dashboard E2E tests only
pytest -m e2e_dashboard
```

### Running Specific Test Files

```bash
# Run specific test file
pytest tests/unit/test_metadata_extraction.py

# Run specific test
pytest tests/unit/test_metadata_extraction.py::test_extract_title

# Run tests matching pattern
pytest -k "upload"
```

## End-to-End Dashboard Tests

Dashboard E2E tests use Playwright to automate browser interactions and test full workflows.

### Prerequisites

1. **Start the Dashboard**:
   ```bash
   python webdashboard/app.py
   ```
   
   Or use the run script:
   ```bash
   ./run_dashboard.sh
   ```

2. **Verify Dashboard is Running**:
   ```bash
   curl http://localhost:8000/health
   ```

### Running Dashboard E2E Tests

**All Dashboard E2E Tests**:
```bash
pytest tests/e2e/test_dashboard_workflows.py -m e2e_dashboard -v
```

**Specific Test Class**:
```bash
pytest tests/e2e/test_dashboard_workflows.py::TestDashboardWorkflows -v
```

**Specific Test**:
```bash
pytest tests/e2e/test_dashboard_workflows.py::TestDashboardWorkflows::test_upload_pdf_workflow -v
```

**With Browser Visible (Debug Mode)**:
```bash
pytest tests/e2e/test_dashboard_workflows.py -m e2e_dashboard --headed --slowmo=1000
```

**Performance Tests Only**:
```bash
pytest tests/e2e/test_dashboard_workflows.py -m performance -v
```

### Dashboard Test Coverage

Current dashboard E2E tests cover:

- ✅ Dashboard page loading
- ✅ Navigation elements presence
- ✅ API health check
- ✅ Upload workflow validation
- ✅ Jobs list visibility
- ✅ Console error detection
- ✅ Responsive layout testing
- ✅ Performance metrics
- ✅ API response times

### Configuring Dashboard URL

By default, tests use `http://localhost:8000`. To use a different URL:

```bash
export DASHBOARD_URL=http://localhost:5001
pytest tests/e2e/test_dashboard_workflows.py -m e2e_dashboard
```

## Writing Tests

### Test Structure

Follow the Arrange-Act-Assert (AAA) pattern:

```python
def test_example():
    # Arrange - Set up test data
    input_data = create_test_data()
    
    # Act - Perform the action
    result = function_under_test(input_data)
    
    # Assert - Verify the outcome
    assert result == expected_output
```

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

**Examples**:
- `test_metadata_extraction.py`
- `class TestPaperUpload:`
- `def test_upload_valid_pdf():`

### Using Fixtures

Fixtures provide reusable test data and setup:

```python
@pytest.fixture
def sample_paper():
    """Provide a sample paper for testing"""
    return create_minimal_pdf()

def test_with_fixture(sample_paper):
    """Test using the fixture"""
    result = process_paper(sample_paper)
    assert result is not None
```

### Playwright E2E Test Patterns

**Page Navigation**:
```python
def test_navigation(page: Page, dashboard_url):
    page.goto(dashboard_url)
    page.wait_for_load_state("networkidle")
```

**Element Interaction**:
```python
# Click button
page.click("button:has-text('Upload')")

# Fill input
page.fill("input[name='filename']", "test.pdf")

# Upload file
page.set_input_files("input[type='file']", "path/to/file.pdf")
```

**Assertions**:
```python
from playwright.sync_api import expect

# Check element visibility
expect(page.locator(".success-message")).to_be_visible()

# Check text content
expect(page.locator("h1")).to_contain_text("Dashboard")

# Check element count
expect(page.locator(".job-item")).to_have_count(3)
```

## CI/CD Integration

Tests run automatically in GitHub Actions on:
- Pull requests to `main`
- Pushes to `main`
- Nightly schedule (E2E tests)

### GitHub Actions Workflows

**Integration Tests** (`.github/workflows/integration-tests.yml`):
- Runs on every PR
- Executes unit, component, and integration tests
- Uploads coverage reports

**E2E Tests** (`.github/workflows/e2e-tests.yml`):
- Runs nightly at 2 AM
- Executes full pipeline E2E tests
- Can be triggered manually

### Running Tests Locally Like CI

```bash
# Run the same tests as CI
pytest -m unit -v --cov=. --cov-report=xml
pytest -m component -v --cov=. --cov-append --cov-report=xml
pytest -m integration -v --cov=. --cov-append --cov-report=xml
```

## Troubleshooting

### Common Issues

#### Playwright Installation Issues

**Problem**: `playwright: command not found`

**Solution**:
```bash
pip install playwright pytest-playwright
playwright install
```

**Problem**: Browser launch fails

**Solution**:
```bash
# Reinstall browsers
playwright install --force

# Install system dependencies (Linux)
playwright install-deps
```

#### Dashboard Not Responding

**Problem**: E2E tests fail with connection errors

**Solution**:
1. Verify dashboard is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check dashboard logs for errors

3. Verify port 8000 is not in use:
   ```bash
   lsof -i :8000
   ```

4. Try restarting the dashboard:
   ```bash
   pkill -f "python webdashboard/app.py"
   python webdashboard/app.py &
   ```

#### Test Timeouts

**Problem**: Tests timeout waiting for elements

**Solution**:
1. Increase timeout in test:
   ```python
   page.wait_for_selector(".element", timeout=10000)
   ```

2. Check if element selector is correct

3. Run with visible browser to debug:
   ```bash
   pytest --headed --slowmo=1000
   ```

#### Import Errors

**Problem**: `ModuleNotFoundError` when running tests

**Solution**:
```bash
# Ensure you're in the project root
cd /path/to/Literature-Review

# Install in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Debugging Tips

1. **Run with Verbose Output**:
   ```bash
   pytest -v -s
   ```

2. **Run Single Test for Debugging**:
   ```bash
   pytest tests/path/test_file.py::test_name -v
   ```

3. **Use Playwright Inspector** (interactive debugging):
   ```bash
   PWDEBUG=1 pytest tests/e2e/test_dashboard_workflows.py::test_name
   ```

4. **Capture Screenshots on Failure**:
   ```python
   @pytest.fixture(autouse=True)
   def screenshot_on_failure(page, request):
       yield
       if request.node.rep_call.failed:
           page.screenshot(path=f"failure_{request.node.name}.png")
   ```

5. **View Test Logs**:
   ```bash
   pytest --log-cli-level=DEBUG
   ```

### Getting Help

- Check existing test files for examples
- Review test output for detailed error messages
- Check GitHub Actions logs for CI failures
- Consult Playwright documentation: https://playwright.dev/python/

## Best Practices

1. **Keep Tests Independent**: Each test should run successfully in isolation
2. **Use Descriptive Names**: Test names should describe what they test
3. **Mock External Dependencies**: Don't call real APIs in unit tests
4. **Clean Up After Tests**: Use fixtures with cleanup to avoid state pollution
5. **Test Edge Cases**: Don't just test the happy path
6. **Keep Tests Fast**: Unit tests should run in milliseconds
7. **Use Markers**: Tag tests appropriately (unit, integration, e2e, slow)
8. **Document Complex Tests**: Add docstrings explaining what is being tested
9. **Avoid Test Interdependence**: Tests should not rely on execution order
10. **Regular Test Maintenance**: Keep tests updated as code changes

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright Python Documentation](https://playwright.dev/python/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- Project-specific test examples in `tests/` directory
