# Test Infrastructure Guide

This guide covers the test infrastructure for the Literature Review automation system.

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

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test categories
pytest -m unit              # Unit tests only
pytest -m component         # Component tests only

# Run specific test file
pytest tests/unit/test_judge_pure_functions.py

# Run with verbose output
pytest -v

# Run and show print statements
pytest -s
```

### Running Demos

```bash
# Data validation demo
python demos/demo_validate_data.py

# Fuzzy matching demo
python demos/demo_fuzzy_matching.py

# Mock API demo
python demos/demo_mock_api.py
```

## Test Structure

```
tests/
├── __init__.py
├── unit/                           # Unit tests (pure functions)
│   ├── __init__.py
│   ├── test_judge_pure_functions.py    # Tests for Judge.py pure functions
│   └── test_data_validation.py         # Data schema validation tests
├── component/                      # Component tests (with mocks)
│   ├── __init__.py
│   └── test_judge_with_mocks.py        # Tests for Judge.py with mocked APIs
└── fixtures/                       # Test data fixtures
    └── (test data files)
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)

**Fast, no external dependencies**

- String normalization (`_normalize_string`)
- Circular reference detection (`detect_circular_refs`)
- Prompt building (`build_judge_prompt`)
- Response validation (`validate_judge_response`)
- Data schema validation

**Run unit tests:**
```bash
pytest -m unit
```

### Component Tests (`@pytest.mark.component`)

**Use mocks for external dependencies**

- Pillar definition loading (mocked file I/O)
- Fuzzy matching (mocked definitions)
- API Manager (mocked Gemini API)
- Caching behavior

**Run component tests:**
```bash
pytest -m component
```

### Integration Tests (`@pytest.mark.integration`)

**Slow, require full system setup**

*Currently blocked by open task cards - coming soon*

## Coverage

View test coverage:

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Current Coverage Targets:**
- Unit tests (pure functions): >90%
- Component tests: >70%
- Overall: >80% (after all tests implemented)

## Demo Scripts

### 1. Data Validation Demo

Validates all data files for schema compliance.

```bash
python demos/demo_validate_data.py
```

**Checks:**
- Version history JSON structure
- CSV database schema
- Pillar definitions format
- Circular references
- Required fields

### 2. Fuzzy Matching Demo

Demonstrates string normalization and fuzzy matching.

```bash
python demos/demo_fuzzy_matching.py
```

**Shows:**
- String normalization process
- Exact vs fuzzy matching
- Pillar key resolution
- Lookup statistics

### 3. Mock API Demo

Shows how to test API-dependent code without API calls.

```bash
python demos/demo_mock_api.py
```

**Demonstrates:**
- Mocking approved/rejected verdicts
- Error handling
- Cache behavior verification
- Quota preservation

## Writing New Tests

### Unit Test Template

```python
import pytest
from Judge import your_function

class TestYourFunction:
    
    @pytest.mark.unit
    def test_basic_case(self):
        """Test basic functionality."""
        result = your_function("input")
        assert result == "expected"
    
    @pytest.mark.unit
    def test_edge_case(self):
        """Test edge case."""
        result = your_function(None)
        assert result is None
```

### Component Test Template

```python
import pytest
from unittest.mock import Mock, patch

class TestWithMocks:
    
    @pytest.mark.component
    @patch('Judge.external_dependency')
    def test_with_mock(self, mock_dep):
        """Test with mocked dependency."""
        mock_dep.return_value = "mocked"
        result = function_using_dependency()
        assert result == "expected"
```

## Test Markers

Available pytest markers:

- `@pytest.mark.unit` - Fast unit tests, no dependencies
- `@pytest.mark.component` - Component tests with mocks
- `@pytest.mark.integration` - Integration tests (requires full setup)
- `@pytest.mark.slow` - Tests taking >5 seconds
- `@pytest.mark.requires_api` - Tests requiring Gemini API access

## Continuous Integration

(Coming soon - after Task Cards completed)

Planned CI workflow:
1. Run unit tests on every commit
2. Run component tests on every PR
3. Run integration tests nightly
4. Generate coverage reports

## Troubleshooting

### Import Errors

If you get import errors:

```python
# Add this to test files
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
```

### Fixture Not Found

Ensure you're running from repo root:

```bash
cd /path/to/Literature-Review
pytest
```

### Mock Not Working

Check that you're patching the right location:

```python
# Patch where it's USED, not where it's DEFINED
@patch('Judge.genai.Client')  # Correct - where Judge imports it
# NOT
@patch('google.genai.Client')  # Wrong - original location
```

## What's Next

### After Task Card #1 (DRA Fix)
- Add DRA integration tests
- Test >60% approval rate validation

### After Task Card #2 (Version History Refactor)
- Add Judge → Version History → Sync flow tests
- Test no direct database writes

### After Task Card #3 (Chunking)
- Add large document processing tests
- Performance benchmarks

### After All Task Cards
- Full end-to-end pipeline tests
- Stress testing with 100+ papers
- CI/CD integration

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock guide](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py docs](https://coverage.readthedocs.io/)

## Questions?

See the main project documentation or check:
- `ARCHITECTURE_ANALYSIS.md` - System architecture
- `AGENT_TASK_CARDS.md` - Pending improvements
- `TEST_ASSESSMENT.md` - Detailed test planning
