"""
Pytest configuration and shared fixtures for all tests.

This file provides fixtures that are available to all tests in the suite.
"""

import pytest
import tempfile
import shutil
import os
import json
from pathlib import Path
from typing import Dict, Any, TYPE_CHECKING

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.fixtures.test_data_generator import TestDataGenerator

# =============================================================================
# Metrics Configuration Integration
# =============================================================================

# Import metrics config (created by VM-W0.5-1)
try:
    from tests.validation.config.metrics_config import (
        load_metrics_config,
        get_metrics_config,
        MetricsConfig,
        MetricCategory
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    MetricsConfig = None
    MetricCategory = None


def pytest_addoption(parser):
    """Add custom command-line options for metrics and domain configuration."""
    # Metrics configuration options (VM-W0.5-1)
    parser.addoption(
        "--metrics-profile",
        action="store",
        default="development",
        help="Metrics profile: development, production, quick, ci"
    )
    parser.addoption(
        "--skip-category",
        action="append",
        default=[],
        help="Skip metric categories: accuracy, efficiency, benchmark, e2e"
    )
    parser.addoption(
        "--only-category",
        action="store",
        default=None,
        help="Run only this metric category"
    )
    # Domain fixture options (VM-W0.5-2)
    parser.addoption(
        "--domain",
        action="store",
        default="neuromorphic-computing",
        help="Domain to test (default: neuromorphic-computing)"
    )
    parser.addoption(
        "--all-domains",
        action="store_true",
        default=False,
        help="Run tests on all available domains"
    )


@pytest.fixture(scope="function")
def temp_dir():
    """
    Create a temporary directory for test files.
    
    Yields:
        Path to temporary directory
    
    Cleanup:
        Removes directory and all contents after test
    """
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope="function")
def test_data_generator():
    """
    Provide a TestDataGenerator instance.
    
    Returns:
        TestDataGenerator instance
    """
    return TestDataGenerator()


@pytest.fixture(scope="function")
def mock_version_history(temp_dir):
    """
    Create a mock version history file.
    
    Args:
        temp_dir: Temporary directory fixture
        
    Returns:
        Tuple of (filepath, data dict)
    """
    generator = TestDataGenerator()
    filepath = os.path.join(temp_dir, "review_version_history.json")
    
    data = generator.create_version_history(
        filenames=["test_paper_1.pdf", "test_paper_2.pdf"],
        num_versions_per_file=1,
        approved_ratio=0.8
    )
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath, data


@pytest.fixture(scope="function")
def mock_version_history_with_rejections(temp_dir):
    """
    Create a mock version history with rejected claims.
    
    Args:
        temp_dir: Temporary directory fixture
        
    Returns:
        Tuple of (filepath, data dict)
    """
    generator = TestDataGenerator()
    filepath = os.path.join(temp_dir, "review_version_history.json")
    
    data = generator.create_rejected_claims_scenario(
        filename="test_paper_rejected.pdf",
        num_rejected=3
    )
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath, data


@pytest.fixture(scope="function")
def mock_pillar_definitions(temp_dir):
    """
    Create mock pillar definitions.
    
    Args:
        temp_dir: Temporary directory fixture
        
    Returns:
        Tuple of (filepath, data dict)
    """
    generator = TestDataGenerator()
    filepath = os.path.join(temp_dir, "pillar_definitions_enhanced.json")
    
    data = generator.create_mock_pillar_definitions()
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath, data


@pytest.fixture(scope="session")
def sample_paper_filenames():
    """
    Provide a list of sample paper filenames for testing.
    
    Returns:
        List of PDF filenames
    """
    return [
        "neuromorphic_snn_2023.pdf",
        "event_based_vision_2024.pdf",
        "memristive_computing_2022.pdf",
        "hardware_accelerators_2023.pdf",
        "photonic_neural_nets_2024.pdf"
    ]


@pytest.fixture(scope="function")
def mock_api_response():
    """
    Create a mock API response for testing.
    
    Returns:
        Dict representing a typical API response
    """
    return {
        "verdict": "approved",
        "reasoning": "The claim is well-supported by the evidence provided.",
        "confidence": 0.95
    }


@pytest.fixture(scope="function")
def mock_judge_response():
    """
    Create a mock Judge response.
    
    Returns:
        Dict representing Judge verdict
    """
    return {
        "status": "approved",
        "reasoning": "Evidence clearly supports the claim.",
        "timestamp": "2024-11-10T12:00:00"
    }


@pytest.fixture(scope="function")
def cleanup_test_files():
    """
    Fixture to clean up test files after test execution.
    
    Yields:
        List to track files that should be cleaned up
    """
    files_to_cleanup = []
    
    yield files_to_cleanup
    
    # Cleanup after test
    for filepath in files_to_cleanup:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass  # Ignore cleanup errors


# Markers are defined in pytest.ini, but we document them here for reference:
# - unit: Fast unit tests, no external dependencies
# - component: Component tests with mocks
# - integration: Integration tests (may be slow)
# - e2e: End-to-end tests (slowest)
# - e2e_dashboard: E2E dashboard tests with Playwright
# - slow: Tests that take >5 seconds
# - requires_api: Tests requiring Gemini API access


# Playwright configuration for E2E dashboard tests
def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Playwright will be configured through pytest-playwright plugin
    # Default browser: chromium
    # Headless mode: true (can be overridden with --headed flag)
    pass


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Configure browser context for Playwright tests.
    
    Sets default viewport size and other browser context options.
    """
    return {
        **browser_context_args,
        "viewport": {
            "width": 1920,
            "height": 1080,
        },
        "ignore_https_errors": True,
    }


# =============================================================================
# Metrics Configuration Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def metrics_config(request):
    """Load metrics configuration with profile applied."""
    if not METRICS_AVAILABLE:
        pytest.skip("Metrics config not available")
    
    profile = request.config.getoption("--metrics-profile")
    config = load_metrics_config(profile=profile)
    
    # Apply category skips
    skip_cats = request.config.getoption("--skip-category")
    for cat_name in skip_cats:
        try:
            cat = MetricCategory(cat_name)
            config.disable_category(cat)
        except ValueError:
            pass
    
    # Apply only-category filter
    only_cat = request.config.getoption("--only-category")
    if only_cat:
        try:
            target = MetricCategory(only_cat)
            for cat in list(MetricCategory):
                if cat != target:
                    config.disable_category(cat)
        except ValueError:
            pass
    
    return config


@pytest.fixture
def get_threshold(metrics_config):
    """Fixture to get thresholds by ID."""
    def _get(metric_id: str) -> float:
        return metrics_config.get_threshold(metric_id)
    return _get


@pytest.fixture
def check_metric(metrics_config):
    """Fixture to check if a value passes a metric."""
    def _check(metric_id: str, value: float) -> bool:
        return metrics_config.check(metric_id, value)
    return _check


# =============================================================================
# Domain Fixture Integration (VM-W0.5-2)
# =============================================================================

# Import domain fixtures
try:
    from tests.validation.fixtures.domain_fixture import (
        get_domain_registry,
        get_domain_fixture,
        DomainTestFixture,
        list_available_domains
    )
    DOMAINS_AVAILABLE = True
except ImportError:
    DOMAINS_AVAILABLE = False

# Default domain - the primary research domain for this project
DEFAULT_DOMAIN = "neuromorphic-computing"


@pytest.fixture(scope="session")
def domain_fixture(request) -> "DomainTestFixture":
    """Load domain fixture for single-domain tests."""
    if not DOMAINS_AVAILABLE:
        pytest.skip("Domain fixtures not available")
    
    domain_id = request.config.getoption("--domain")
    try:
        return get_domain_fixture(domain_id)
    except KeyError as e:
        pytest.fail(str(e))


@pytest.fixture(scope="session")
def all_domain_fixtures(request) -> dict:
    """Load all domain fixtures for cross-domain tests."""
    if not DOMAINS_AVAILABLE:
        pytest.skip("Domain fixtures not available")
    
    return get_domain_registry().get_all()


def pytest_generate_tests(metafunc):
    """Parameterize tests across domains if requested."""
    if not DOMAINS_AVAILABLE:
        return
    
    if "domain_id" in metafunc.fixturenames:
        all_domains_flag = metafunc.config.getoption("--all-domains", default=False)
        
        if all_domains_flag:
            domains = list_available_domains()
        else:
            domains = [metafunc.config.getoption("--domain", default=DEFAULT_DOMAIN)]
        
        metafunc.parametrize("domain_id", domains)


@pytest.fixture
def domain_golden_dataset(domain_fixture):
    """Get golden dataset from domain fixture."""
    if not domain_fixture.has_golden_dataset():
        pytest.skip(f"No golden dataset for domain: {domain_fixture.domain_id}")
    return domain_fixture.golden_dataset


@pytest.fixture
def domain_baselines(domain_fixture):
    """Get expected baselines from domain fixture."""
    return domain_fixture.baselines


@pytest.fixture
def domain_pillars(domain_fixture):
    """Get pillar names from domain fixture."""
    return domain_fixture.get_pillar_names()
