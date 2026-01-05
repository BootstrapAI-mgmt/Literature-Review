"""
Tier 1 Test Fixtures
Shared fixtures for all Tier 1 unit/component tests.
"""

import pytest
import json
from pathlib import Path


@pytest.fixture
def mocks_dir():
    """Path to mock payloads directory"""
    return Path(__file__).parent / "mocks"


@pytest.fixture
def load_mock(mocks_dir):
    """Factory fixture to load mock payloads"""
    def _load(filename):
        path = mocks_dir / filename
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        raise FileNotFoundError(f"Mock not found: {filename}")
    return _load


@pytest.fixture
def github_push_valid(load_mock):
    """Valid GitHub push event payload"""
    return load_mock("github_push_valid.json")


@pytest.fixture
def github_push_n8n_automated(load_mock):
    """n8n automated push (should be filtered out)"""
    return load_mock("github_push_n8n_automated.json")


@pytest.fixture
def task_distributor_payload(load_mock):
    """Task distributor queue payload"""
    return load_mock("task_distributor_payload.json")


@pytest.fixture
def agent_task_payload(load_mock):
    """Agent task payload"""
    return load_mock("agent_task_payload.json")


@pytest.fixture
def agent_callback_success(load_mock):
    """Successful agent callback"""
    return load_mock("agent_callback_success.json")


@pytest.fixture
def agent_callback_failure(load_mock):
    """Failed agent callback"""
    return load_mock("agent_callback_failure.json")


@pytest.fixture
def state_reconciliation(load_mock):
    """State reconciliation trigger payload"""
    return load_mock("state_reconciliation.json")


@pytest.fixture
def staleness_review(load_mock):
    """Staleness review payload"""
    return load_mock("staleness_review.json")


@pytest.fixture
def pr_review_webhook(load_mock):
    """PR review webhook payload"""
    return load_mock("pr_review_webhook.json")


@pytest.fixture
def release_tag_webhook(load_mock):
    """Release tag webhook payload"""
    return load_mock("release_tag_webhook.json")


@pytest.fixture
def error_workflow_trigger(load_mock):
    """Error workflow trigger payload"""
    return load_mock("error_workflow_trigger.json")


# Workflow simulation helpers
class WorkflowSimulator:
    """Simulates n8n workflow execution for testing"""
    
    def __init__(self):
        self.executions = []
        self.current_node = None
    
    def execute_node(self, node_name: str, input_data: dict) -> dict:
        """Simulate executing a workflow node"""
        self.current_node = node_name
        execution = {
            "node": node_name,
            "input": input_data,
            "output": None,
            "status": "pending"
        }
        self.executions.append(execution)
        return execution
    
    def complete_node(self, output: dict, status: str = "success"):
        """Complete the current node execution"""
        if self.executions:
            self.executions[-1]["output"] = output
            self.executions[-1]["status"] = status
    
    def get_execution_path(self) -> list:
        """Get the list of executed nodes"""
        return [e["node"] for e in self.executions]


@pytest.fixture
def workflow_simulator():
    """Create a workflow simulator instance"""
    return WorkflowSimulator()
