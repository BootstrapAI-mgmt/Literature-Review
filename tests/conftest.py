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
from typing import Dict, Any

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.fixtures.test_data_generator import TestDataGenerator


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
def temp_workspace(temp_dir):
    """
    Create a workspace directory for tests (alias for temp_dir).
    
    Yields:
        Path object to temporary directory
    
    Cleanup:
        Removes directory and all contents after test
    """
    yield Path(temp_dir)


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
# - slow: Tests that take >5 seconds
# - requires_api: Tests requiring Gemini API access
