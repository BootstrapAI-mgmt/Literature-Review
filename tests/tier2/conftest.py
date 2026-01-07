"""
Tier 2 Test Fixtures
Shared fixtures for all Tier 2 integration tests.
"""

import pytest
import os
from .payloader import Payloader, PayloaderError, REQUESTS_AVAILABLE


@pytest.fixture
def payloader():
    """Create a payloader instance for webhook calls"""
    return Payloader(timeout=10)


@pytest.fixture
def n8n_available():
    """Check if n8n Cloud is reachable"""
    if not REQUESTS_AVAILABLE:
        return False
    
    try:
        payloader = Payloader(timeout=5)
        # Try a simple endpoint check
        payloader.check_distributor_status()
        return True
    except PayloaderError:
        return False


@pytest.fixture
def skip_if_n8n_unavailable(n8n_available):
    """Skip test if n8n is not available"""
    if not n8n_available:
        pytest.skip("n8n Cloud not available for integration testing")


@pytest.fixture
def reset_distributor(payloader):
    """Reset distributor before test"""
    payloader.reset_distributor()
    yield
    # Cleanup: reset again after test
    payloader.reset_distributor()


# Endpoint definitions per Master Validation Plan
ENDPOINTS = {
    "github_doc_trigger": "/github-doc-trigger",
    "task_distributor": "/task-distributor", 
    "domain_agent": "/domain-agent",
    "task_callback": "/task-callback",
    "distributor_status": "/distributor-status",
    "distributor_reset": "/distributor-reset",
    "state_reconciliation": "/state-reconciliation",
    "staleness_review": "/staleness-review",
    "pr_review": "/pr-review",
    "error_workflow": "/error-handler",
}



@pytest.fixture
def endpoints():
    """Provide endpoint mapping"""
    return ENDPOINTS


# Sample payloads for integration tests
@pytest.fixture
def sample_push_payload():
    """Sample GitHub push payload for integration tests"""
    return {
        "ref": "refs/heads/main",
        "repository": {"full_name": "BootstrapAI-mgmt/Literature-Review"},
        "pusher": {"name": "integration-test"},
        "commits": [{
            "id": "integration-test-001",
            "message": "test: integration test commit",
            "modified": ["docs/MASTER_ARCHITECTURE_BLUEPRINT.md"]
        }]
    }


@pytest.fixture
def sample_pr_payload():
    """Sample PR webhook payload for integration tests"""
    return {
        "action": "opened",
        "number": 9999,
        "pull_request": {
            "number": 9999,
            "title": "Integration Test PR",
            "body": "This is an integration test PR for validation framework",
            "state": "open",
            "head": {"ref": "test-branch", "sha": "abc123"},
            "base": {"ref": "main"}
        },
        "repository": {"full_name": "BootstrapAI-mgmt/Literature-Review"}
    }


@pytest.fixture
def sample_task_payload():
    """Sample task dispatch payload"""
    return {
        "task_id": "integration-test-task-001",
        "domain": "documentation",
        "action": "test_action",
        "document": "docs/test.md",
        "context": {"test": True}
    }
