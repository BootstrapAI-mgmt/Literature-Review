"""
Tier 4 Live Test Fixtures
"""

import pytest
from pathlib import Path
import sys

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.tier4_live.workflow_runner import WorkflowRunner
from tests.tier4_live.gold_standard_comparator import GoldStandardComparator


@pytest.fixture
def repo_path():
    """Path to repository root"""
    return PROJECT_ROOT


@pytest.fixture
def workflow_runner():
    """WorkflowRunner instance for triggering n8n workflows"""
    return WorkflowRunner(timeout=300)


@pytest.fixture
def gold_comparator(repo_path):
    """GoldStandardComparator instance"""
    return GoldStandardComparator(repo_path)


@pytest.fixture
def n8n_available():
    """Check if n8n Cloud is reachable"""
    try:
        runner = WorkflowRunner()
        status = runner.check_mcp_status()
        return status.get("success", False)
    except Exception:
        return False


@pytest.fixture
def require_live_n8n(n8n_available):
    """Skip test if n8n is not available"""
    if not n8n_available:
        pytest.skip("REQUIRES LIVE N8N: n8n Cloud not reachable")
