"""
Tier 3 E2E Test Fixtures
Shared fixtures for all Tier 3 end-to-end tests.
"""

import pytest
from pathlib import Path
from .e2e_orchestrator import (
    E2EOrchestrator, 
    E2ETestContext, 
    StateCapture, 
    check_n8n_available
)


@pytest.fixture(scope="session")
def repo_path():
    """Path to the repository root"""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def orchestrator(repo_path):
    """Create an E2E orchestrator instance"""
    return E2EOrchestrator(repo_path, n8n_timeout=60)


@pytest.fixture
def state_capture(repo_path):
    """Create a state capture instance"""
    return StateCapture(repo_path)


@pytest.fixture
def n8n_available():
    """Check if n8n Cloud is reachable"""
    return check_n8n_available()


@pytest.fixture
def skip_if_n8n_unavailable(n8n_available):
    """Skip test if n8n is not available"""
    if not n8n_available:
        pytest.skip("n8n Cloud not available - test requires live n8n environment")


@pytest.fixture
def require_live_n8n(n8n_available):
    """
    Marker for tests requiring live n8n environment.
    These tests cover the skipped Tier 2 integration tests.
    """
    if not n8n_available:
        pytest.skip("REQUIRES LIVE N8N: This test validates n8n webhook connectivity")


# Document path fixtures
@pytest.fixture
def architecture_blueprint_path():
    return "docs/MASTER_ARCHITECTURE_BLUEPRINT.md"


@pytest.fixture
def roadmap_path():
    return "docs/MASTER_REPOSITORY_ROADMAP.md"


@pytest.fixture
def op_wave_index_path():
    return "task-cards/OPERATIONALIZATION_WAVE_INDEX.md"


@pytest.fixture
def monitored_docs(architecture_blueprint_path, roadmap_path, op_wave_index_path):
    """List of monitored documentation paths"""
    return [architecture_blueprint_path, roadmap_path, op_wave_index_path]


# Test scenario fixtures
@pytest.fixture
def push_affecting_architecture():
    """Push event affecting architecture documentation"""
    return {
        "modified_files": ["literature_review/models/new_module.py"],
        "expected_changes": ["docs/MASTER_ARCHITECTURE_BLUEPRINT.md"]
    }


@pytest.fixture
def push_affecting_task_cards():
    """Push event that should update task cards"""
    return {
        "modified_files": ["literature_review/analysis/validation_tracker.py"],
        "expected_changes": []  # May or may not trigger task updates
    }


@pytest.fixture
def pr_merge_event():
    """PR merge event scenario"""
    return {
        "pr_number": 128,
        "task_id": "OP_WAVE_1_1_SCHEMA_FOUNDATION",
        "expected_task_status": "Complete"
    }
