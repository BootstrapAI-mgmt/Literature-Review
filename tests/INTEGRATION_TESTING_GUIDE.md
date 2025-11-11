# Integration & E2E Testing Guide

This guide covers the integration and end-to-end testing infrastructure for the Literature Review automation system.

## Quick Start

### Installation

```bash
# Install test dependencies
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run only integration tests
pytest -m integration

# Run only E2E tests
pytest -m e2e

# Run unit and component tests (fast)
pytest -m "unit or component"

# Skip slow tests
pytest -m "not slow"

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/integration/test_journal_to_judge.py
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                          # Shared fixtures for all tests
├── README.md                            # Original test guide
├── INTEGRATION_TESTING_GUIDE.md         # This file
│
├── unit/                                # Unit tests (pure functions)
│   ├── __init__.py
│   └── (unit test files)
│
├── component/                           # Component tests (with mocks)
│   ├── __init__.py
│   └── (component test files)
│
├── integration/                         # Integration tests
│   ├── __init__.py
│   ├── conftest.py                      # Integration-specific fixtures
│   └── test_*.py                        # Integration test files
│
├── e2e/                                 # End-to-end tests
│   ├── __init__.py
│   ├── conftest.py                      # E2E-specific fixtures
│   └── test_*.py                        # E2E test files
│
└── fixtures/                            # Test data and utilities
    ├── __init__.py
    ├── test_data_generator.py           # Test data generation utilities
    ├── sample_papers/                   # Sample PDF files
    ├── version_history_fixtures/        # Version history samples
    └── csv_fixtures/                    # CSV database samples
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)

**Characteristics:**
- Fast execution (<1 second each)
- No external dependencies
- Test pure functions only
- No file I/O or API calls

**Examples:**
- String normalization
- Data validation functions
- Circular reference detection
- Prompt building logic

**Run with:**
```bash
pytest -m unit
```

### Component Tests (`@pytest.mark.component`)

**Characteristics:**
- Use mocks for external dependencies
- Test individual components in isolation
- May use temporary files
- Moderate execution time (<5 seconds each)

**Examples:**
- Pillar definition loading (mocked file I/O)
- API Manager (mocked Gemini API)
- Fuzzy matching with mocked definitions
- Cache behavior verification

**Run with:**
```bash
pytest -m component
```

### Integration Tests (`@pytest.mark.integration`)

**Characteristics:**
- Test interactions between multiple components
- Use mocks for external APIs only
- Real file I/O with test data
- Slower execution (5-30 seconds each)

**Examples:**
- Journal-Reviewer → Judge → Version History flow
- Judge → DRA → Re-judge workflow
- Version History → CSV sync
- Orchestrator convergence loop

**Run with:**
```bash
pytest -m integration
```

### End-to-End Tests (`@pytest.mark.e2e`)

**Characteristics:**
- Run complete pipeline workflows
- Minimal mocking (use real components)
- Slowest execution (30+ seconds each)
- Most comprehensive coverage

**Examples:**
- Full pipeline: PDF → Reports
- Multi-iteration convergence
- Error recovery scenarios
- Performance benchmarks

**Run with:**
```bash
pytest -m e2e
```

## Test Fixtures

### Shared Fixtures (available to all tests)

Defined in `tests/conftest.py`:

#### `temp_dir`
Creates a temporary directory for test files, automatically cleaned up after test.

```python
def test_example(temp_dir):
    filepath = os.path.join(temp_dir, "test.json")
    # Use filepath for testing
    # Cleanup is automatic
```

#### `test_data_generator`
Provides a TestDataGenerator instance for creating test data.

```python
def test_example(test_data_generator):
    history = test_data_generator.create_version_history(
        filenames=["test.pdf"],
        num_versions_per_file=1
    )
```

#### `mock_version_history`
Creates a mock version history file with sample data.

```python
def test_example(mock_version_history):
    filepath, data = mock_version_history
    # Use filepath or data for testing
```

#### `mock_version_history_with_rejections`
Creates a version history with rejected claims (for DRA testing).

```python
def test_dra(mock_version_history_with_rejections):
    filepath, data = mock_version_history_with_rejections
    # Test DRA appeal process
```

#### `mock_pillar_definitions`
Creates mock pillar definitions file.

```python
def test_pillars(mock_pillar_definitions):
    filepath, data = mock_pillar_definitions
    # Test pillar loading
```

#### `sample_paper_filenames`
Provides a list of realistic paper filenames.

```python
def test_batch(sample_paper_filenames):
    for filename in sample_paper_filenames[:3]:
        # Process each file
```

### Integration Test Fixtures

Defined in `tests/integration/conftest.py`:

#### `integration_temp_workspace`
Creates a complete workspace with typical file structure.

```python
@pytest.mark.integration
def test_workflow(integration_temp_workspace):
    workspace = integration_temp_workspace
    # workspace['version_history']
    # workspace['csv_db']
    # workspace['pillar_definitions']
    # workspace['papers_dir']
```

#### `mock_journal_output`
Creates mock Journal-Reviewer output for integration tests.

```python
@pytest.mark.integration
def test_judge_integration(mock_journal_output):
    version_history_path = mock_journal_output
    # Test Judge with Journal output
```

### E2E Test Fixtures

Defined in `tests/e2e/conftest.py`:

#### `e2e_workspace`
Creates a complete workspace for E2E tests with all required directories.

```python
@pytest.mark.e2e
def test_full_pipeline(e2e_workspace):
    workspace = e2e_workspace
    # workspace['root']
    # workspace['papers_dir']
    # workspace['reports_dir']
    # workspace['logs_dir']
```

#### `e2e_sample_papers`
Creates sample paper files for E2E testing.

```python
@pytest.mark.e2e
def test_batch_processing(e2e_sample_papers):
    papers = e2e_sample_papers
    # Process list of papers
```

## Test Data Generator

The `TestDataGenerator` class (in `tests/fixtures/test_data_generator.py`) provides utilities for creating realistic test data.

### Creating Version History

```python
from tests.fixtures.test_data_generator import TestDataGenerator

generator = TestDataGenerator()

# Create version history for multiple files
history = generator.create_version_history(
    filenames=["paper1.pdf", "paper2.pdf"],
    num_versions_per_file=2,
    approved_ratio=0.8  # 80% approved
)

# Save to file
generator.save_version_history(
    filepath="test_history.json",
    filenames=["paper1.pdf"],
    num_versions_per_file=1
)
```

### Creating Rejected Claims Scenario

```python
# For DRA testing
rejected_history = generator.create_rejected_claims_scenario(
    filename="paper.pdf",
    num_rejected=3
)
```

### Creating CSV Rows

```python
# Create CSV database row
row = generator.create_csv_row(
    filename="paper.pdf",
    num_claims=5,
    approved_ratio=0.8
)
```

### Helper Functions

Quick fixture creation:

```python
from tests.fixtures.test_data_generator import (
    create_minimal_version_history,
    create_rejected_scenario,
    create_multi_version_history
)

# Minimal history (1 file, 1 version, all approved)
history = create_minimal_version_history()

# Scenario with rejections
history = create_rejected_scenario()

# Multi-version history
history = create_multi_version_history()
```

## Writing Integration Tests

### Test Template

```python
import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import modules to test
from Judge import process_claims
from sync_history_to_db import sync_to_csv


class TestJournalToJudgeFlow:
    """INT-001: Test Journal → Judge → Version History flow."""
    
    @pytest.mark.integration
    def test_judge_updates_version_history(self, integration_temp_workspace, mock_journal_output):
        """Test that Judge updates version history correctly."""
        workspace = integration_temp_workspace
        
        # Run Judge on mock Journal output
        # ... test logic ...
        
        # Verify version history updated
        assert os.path.exists(workspace['version_history'])
        
        # Verify no direct database writes
        assert not os.path.exists(workspace['csv_db'])
    
    @pytest.mark.integration
    def test_sync_propagates_to_csv(self, integration_temp_workspace):
        """Test that sync script propagates changes to CSV."""
        workspace = integration_temp_workspace
        
        # Create version history with updates
        # ... setup ...
        
        # Run sync
        # ... test logic ...
        
        # Verify CSV updated correctly
        assert os.path.exists(workspace['csv_db'])
```

### Best Practices

1. **Use descriptive test names** that explain what is being tested
2. **Arrange-Act-Assert** structure:
   - Arrange: Set up test data
   - Act: Execute the code being tested
   - Assert: Verify the results
3. **Clean up resources** using fixtures or try/finally
4. **Mock external dependencies** (APIs, network calls)
5. **Use realistic test data** from TestDataGenerator
6. **Test both success and failure paths**
7. **Verify no side effects** (unwanted file writes, etc.)

## Writing E2E Tests

### Test Template

```python
import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestFullPipeline:
    """E2E-001: Test complete pipeline from PDF to reports."""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_pipeline_execution(self, e2e_workspace, e2e_sample_papers):
        """Test full pipeline with sample papers."""
        workspace = e2e_workspace
        papers = e2e_sample_papers
        
        # Run complete pipeline
        # 1. Journal-Reviewer
        # 2. Judge
        # 3. DRA (if needed)
        # 4. Sync
        # 5. Orchestrator
        
        # Verify all outputs created
        assert os.path.exists(workspace['version_history'])
        assert os.path.exists(workspace['csv_db'])
        
        # Verify no errors in logs
        # ... assertions ...
```

### E2E Best Practices

1. **Test realistic scenarios** end-to-end
2. **Minimize mocking** - use real components when possible
3. **Test error recovery** - what happens when stages fail?
4. **Verify data integrity** through entire pipeline
5. **Check performance** - does pipeline complete in reasonable time?
6. **Test concurrent execution** if applicable

## Test Markers Reference

Use pytest markers to categorize and filter tests:

```python
@pytest.mark.unit
def test_pure_function():
    """Fast, no dependencies."""
    pass

@pytest.mark.component
def test_with_mocks():
    """Component with mocked dependencies."""
    pass

@pytest.mark.integration
def test_component_interaction():
    """Multiple components working together."""
    pass

@pytest.mark.e2e
def test_full_workflow():
    """Complete pipeline test."""
    pass

@pytest.mark.slow
def test_long_running():
    """Test takes >5 seconds."""
    pass

@pytest.mark.requires_api
def test_with_real_api():
    """Requires Gemini API key."""
    pass
```

Run specific markers:
```bash
pytest -m unit                    # Only unit tests
pytest -m "integration or e2e"    # Integration + E2E
pytest -m "not slow"              # Skip slow tests
pytest -m "not requires_api"      # Skip API tests
```

## Coverage Reports

### Generate Coverage

```bash
# HTML report
pytest --cov=. --cov-report=html

# Terminal report
pytest --cov=. --cov-report=term-missing

# Both
pytest --cov=. --cov-report=html --cov-report=term
```

### View Coverage

```bash
# Open HTML report
open htmlcov/index.html       # macOS
xdg-open htmlcov/index.html   # Linux
start htmlcov/index.html      # Windows
```

### Coverage Targets

- **Unit tests (pure functions):** >90%
- **Component tests:** >70%
- **Integration tests:** >60%
- **Overall:** >80%

## Troubleshooting

### Import Errors

If you get import errors in tests:

```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
```

### Fixture Not Found

Make sure you're running from repo root:

```bash
cd /path/to/Literature-Review
pytest
```

### Tests Not Discovered

Check pytest.ini configuration:

```bash
# See what tests pytest finds
pytest --collect-only

# Verbose collection
pytest --collect-only -v
```

### Temporary Files Not Cleaned Up

Use `temp_dir` fixture which auto-cleans:

```python
def test_example(temp_dir):
    # Files in temp_dir are auto-cleaned after test
    pass
```

### Mock Not Working

Patch where the function is **used**, not where it's **defined**:

```python
# Correct - where Judge imports it
@patch('Judge.genai.Client')

# Wrong - original location
@patch('google.genai.Client')
```

## CI/CD Integration

(Coming in Task Card #12)

Planned workflow:
1. Run unit tests on every commit
2. Run component tests on every PR
3. Run integration tests on PR approval
4. Run E2E tests nightly
5. Generate coverage reports
6. Block merge if coverage drops

## Next Steps

### After Task Card #6 (INT-001 Tests)
- Test Journal → Judge → Version History flow
- Verify no direct database writes

### After Task Card #7 (INT-003 Tests)
- Test Version History → CSV sync
- Verify data integrity

### After Task Card #8 (INT-002 Tests)
- Test Judge → DRA → Re-judge workflow
- Verify appeal process

### After Task Card #9 (INT-004/005 Tests)
- Test Orchestrator convergence loop
- Test Deep-Reviewer iteration

### After Task Card #10 (E2E-001 Tests)
- Test complete pipeline
- Verify end-to-end data flow

### After Task Card #11 (E2E-002 Tests)
- Test convergence validation
- Verify <5% gap achievement

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest fixtures guide](https://docs.pytest.org/en/stable/fixture.html)
- [unittest.mock guide](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py docs](https://coverage.readthedocs.io/)

## Questions?

See also:
- `tests/README.md` - Original test guide
- `INTEGRATION_E2E_TESTING_ASSESSMENT.md` - Testing strategy
- `INTEGRATION_TESTING_TASK_CARDS.md` - Task card details
- `ARCHITECTURE_ANALYSIS.md` - System architecture
