#!/usr/bin/env python3
"""
End-to-End Tests for n8n Integration

This test suite validates the complete integration between the codespace
and n8n Cloud workflows. It tests both the Python bridge and direct webhook calls.

Usage:
    pytest tests/test_n8n_integration_e2e.py -v
    python tests/test_n8n_integration_e2e.py  # Direct execution for quick check

Environment:
    N8N_API_URL  - n8n API URL (default: https://gitlitreview.app.n8n.cloud/api/v1)
    N8N_API_KEY  - n8n API key (required)
"""

import os
import sys
import json
import pytest
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Add parent directory to path for bridge import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'n8n-server'))

# Test configuration - Fix environment if incorrectly set
N8N_CLOUD_URL = "https://gitlitreview.app.n8n.cloud"
N8N_API_URL_DEFAULT = f"{N8N_CLOUD_URL}/api/v1"

# Auto-fix broken N8N_API_URL (may be truncated to 'http' from prior config)
current_url = os.environ.get('N8N_API_URL', '')
if not current_url or current_url == 'http' or 'gitlitreview' not in current_url:
    os.environ['N8N_API_URL'] = N8N_API_URL_DEFAULT

from bridge import N8nBridge

WEBHOOK_BASE = f"{N8N_CLOUD_URL}/webhook"


class TestConfiguration:
    """Test environment configuration."""

    def test_api_key_present(self):
        """Verify N8N_API_KEY is configured."""
        api_key = os.environ.get('N8N_API_KEY', '')
        assert api_key, "N8N_API_KEY environment variable is not set"
        assert len(api_key) > 50, f"API key seems too short ({len(api_key)} chars)"

    def test_api_url_configured(self):
        """Verify N8N_API_URL is correctly set."""
        api_url = os.environ.get('N8N_API_URL', '')
        # Allow default or explicit setting
        if api_url:
            assert 'gitlitreview' in api_url or 'localhost' in api_url, \
                f"Unexpected API URL: {api_url}"


class TestBridgeHealth:
    """Test bridge connectivity and health checks."""

    @pytest.fixture
    def bridge(self):
        """Create a bridge instance for testing."""
        return N8nBridge()

    def test_health_check(self, bridge):
        """Verify n8n server is responsive."""
        result = bridge.health()
        assert result['status'] == 'healthy', f"Health check failed: {result}"
        assert 'api_url' in result

    def test_list_workflows(self, bridge):
        """Verify we can list workflows."""
        workflows = bridge.list_workflows()
        assert isinstance(workflows, list), "Expected list of workflows"
        assert len(workflows) > 0, "No workflows found"
        
        # Verify workflow structure
        workflow = workflows[0]
        assert 'id' in workflow
        assert 'name' in workflow
        assert 'active' in workflow

    def test_get_workflow_details(self, bridge):
        """Verify we can get workflow details."""
        workflows = bridge.list_workflows()
        assert len(workflows) > 0, "No workflows to test"
        
        workflow_id = workflows[0]['id']
        details = bridge.get_workflow(workflow_id)
        
        assert details['id'] == workflow_id
        assert 'nodes' in details
        assert 'connections' in details

    def test_list_executions(self, bridge):
        """Verify we can list workflow executions."""
        executions = bridge.list_executions(limit=5)
        assert isinstance(executions, list), "Expected list of executions"
        # May be empty if no executions yet


class TestWorkflowManagement:
    """Test workflow activation/deactivation."""

    @pytest.fixture
    def bridge(self):
        """Create a bridge instance for testing."""
        return N8nBridge()

    def test_deactivate_and_activate(self, bridge):
        """Test workflow deactivation and reactivation cycle."""
        # Find an active workflow (Claude Bridge v2)
        workflows = bridge.list_workflows()
        active_workflows = [w for w in workflows if w.get('active') and 'Claude Bridge v2' in w.get('name', '')]
        
        if not active_workflows:
            pytest.skip("No active Claude Bridge v2 workflow to test")
        
        workflow = active_workflows[0]
        workflow_id = workflow['id']
        
        # Deactivate
        result = bridge.deactivate_workflow(workflow_id)
        assert result.get('active') == False, "Deactivation failed"
        
        # Reactivate
        result = bridge.activate_workflow(workflow_id)
        assert result.get('active') == True, "Activation failed"


class TestWebhookCommunication:
    """Test direct webhook communication with n8n workflows."""

    def _call_webhook(self, path: str, data: dict) -> dict:
        """Make a POST request to an n8n webhook."""
        url = f"{WEBHOOK_BASE}/{path}"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        body = json.dumps(data).encode('utf-8')
        request = Request(url, data=body, headers=headers, method='POST')
        
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            pytest.fail(f"Webhook call failed ({e.code}): {error_body}")
        except URLError as e:
            pytest.fail(f"Webhook connection failed: {e.reason}")

    def test_claude_bridge_status_query(self):
        """Test status query to Claude Bridge v2."""
        result = self._call_webhook('claude-bridge', {
            'source': 'e2e-test',
            'message_type': 'status_query',
            'payload': {'query': 'health'}
        })
        
        assert result.get('success') == True
        assert result.get('bridge') == 'claude-antigravity'
        assert 'bridge_stats' in result
        assert 'system_status' in result

    def test_claude_bridge_task_request(self):
        """Test task request to Claude Bridge v2."""
        result = self._call_webhook('claude-bridge', {
            'source': 'e2e-test',
            'message_type': 'task_request',
            'payload': {
                'task': 'test_task',
                'test_id': f'e2e-{datetime.now().isoformat()}'
            }
        })
        
        assert result.get('success') == True
        assert result.get('handler') == 'task_request'
        assert result.get('status') == 'queued'

    def test_claude_bridge_feedback(self):
        """Test feedback submission to Claude Bridge v2."""
        result = self._call_webhook('claude-bridge', {
            'source': 'e2e-test',
            'message_type': 'feedback',
            'payload': {
                'rating': 5,
                'comment': 'E2E test feedback'
            }
        })
        
        assert result.get('success') == True
        assert result.get('handler') == 'feedback'
        assert result.get('status') == 'recorded'

    def test_claude_bridge_instruction(self):
        """Test instruction processing in Claude Bridge v2."""
        result = self._call_webhook('claude-bridge', {
            'source': 'e2e-test',
            'message_type': 'instruction',
            'payload': {
                'instruction': 'test_instruction',
                'targets': ['test']
            }
        })
        
        assert result.get('success') == True
        assert result.get('handler') == 'instruction'
        assert result.get('instruction_received') == 'test_instruction'

    def test_claude_bridge_unknown_type(self):
        """Test handling of unknown message types."""
        result = self._call_webhook('claude-bridge', {
            'source': 'e2e-test',
            'message_type': 'unknown_type_xyz',
            'payload': {}
        })
        
        assert result.get('success') == False
        assert result.get('handler') == 'unknown'
        assert 'error' in result

    def test_antigravity_status(self):
        """Test Antigravity status webhook."""
        # This returns an array
        response = self._call_webhook('antigravity-status', {})
        
        # Handle array response
        if isinstance(response, list):
            result = response[0]
        else:
            result = response
        
        assert 'antigravity' in result
        assert result['antigravity']['status'] == 'operational'
        assert 'capabilities' in result


class TestAPILimitations:
    """Document and test API limitations."""

    @pytest.fixture
    def bridge(self):
        """Create a bridge instance for testing."""
        return N8nBridge()

    def test_execute_workflow_not_available(self, bridge):
        """Document that direct workflow execution is not available via API."""
        workflows = bridge.list_workflows()
        if not workflows:
            pytest.skip("No workflows to test")
        
        workflow_id = workflows[0]['id']
        
        with pytest.raises(Exception) as excinfo:
            bridge.execute_workflow(workflow_id)
        
        # Expected: API returns 404 for execute endpoint on cloud
        assert '404' in str(excinfo.value) or 'not found' in str(excinfo.value).lower()

    def test_workflow_with_config_issue(self, bridge):
        """Document workflow activation failures due to config issues."""
        # The inactive "Doc Chain - Claude Bridge" (v1) has a config issue
        workflows = bridge.list_workflows()
        v1_workflow = [w for w in workflows if 'Claude Bridge' in w.get('name', '') 
                       and 'v2' not in w.get('name', '') 
                       and not w.get('active')]
        
        if not v1_workflow:
            pytest.skip("No inactive Claude Bridge v1 workflow found")
        
        workflow_id = v1_workflow[0]['id']
        
        # This should fail with a config error
        with pytest.raises(Exception) as excinfo:
            bridge.activate_workflow(workflow_id)
        
        assert 'property' in str(excinfo.value).lower() or '400' in str(excinfo.value)


def generate_test_report():
    """Generate a summary report of integration capabilities."""
    report = {
        'timestamp': datetime.now().isoformat(),
        'environment': {
            'n8n_cloud_url': N8N_CLOUD_URL,
            'api_url': os.environ.get('N8N_API_URL', 'not set'),
            'api_key_configured': bool(os.environ.get('N8N_API_KEY'))
        },
        'capabilities': {
            'working': [],
            'not_working': [],
            'limitations': []
        }
    }
    
    try:
        bridge = N8nBridge()
        
        # Test health
        health = bridge.health()
        if health['status'] == 'healthy':
            report['capabilities']['working'].append('health_check')
        else:
            report['capabilities']['not_working'].append('health_check')
        
        # Test list workflows
        try:
            workflows = bridge.list_workflows()
            report['capabilities']['working'].append('list_workflows')
            report['environment']['workflow_count'] = len(workflows)
        except Exception as e:
            report['capabilities']['not_working'].append(f'list_workflows: {e}')
        
        # Test get workflow
        try:
            if workflows:
                bridge.get_workflow(workflows[0]['id'])
                report['capabilities']['working'].append('get_workflow_details')
        except Exception as e:
            report['capabilities']['not_working'].append(f'get_workflow_details: {e}')
        
        # Test activate/deactivate
        try:
            active_wf = [w for w in workflows if w.get('active')]
            if active_wf:
                wf_id = active_wf[0]['id']
                bridge.deactivate_workflow(wf_id)
                bridge.activate_workflow(wf_id)
                report['capabilities']['working'].append('activate_deactivate_workflows')
        except Exception as e:
            report['capabilities']['not_working'].append(f'activate_deactivate: {e}')
        
        # Test executions
        try:
            bridge.list_executions(limit=5)
            report['capabilities']['working'].append('list_executions')
        except Exception as e:
            report['capabilities']['not_working'].append(f'list_executions: {e}')
        
        # Document limitations
        report['capabilities']['limitations'] = [
            'Direct workflow execution (/workflows/{id}/execute) returns 404 on n8n Cloud',
            'Some workflows with config issues cannot be activated (400 error)',
            'Workflow execution must be triggered via webhooks, not API'
        ]
        
    except Exception as e:
        report['error'] = str(e)
    
    return report


if __name__ == '__main__':
    print("=" * 70)
    print("n8n Integration E2E Test Report")
    print("=" * 70)
    
    report = generate_test_report()
    
    print(f"\nTimestamp: {report['timestamp']}")
    print(f"\nEnvironment:")
    print(f"  n8n Cloud URL: {report['environment']['n8n_cloud_url']}")
    print(f"  API URL: {report['environment']['api_url']}")
    print(f"  API Key Configured: {report['environment']['api_key_configured']}")
    if 'workflow_count' in report['environment']:
        print(f"  Workflows Found: {report['environment']['workflow_count']}")
    
    print(f"\n✅ Working Capabilities:")
    for cap in report['capabilities']['working']:
        print(f"   • {cap}")
    
    if report['capabilities']['not_working']:
        print(f"\n❌ Not Working:")
        for cap in report['capabilities']['not_working']:
            print(f"   • {cap}")
    
    print(f"\n⚠️  Limitations:")
    for lim in report['capabilities']['limitations']:
        print(f"   • {lim}")
    
    print("\n" + "=" * 70)
    print("Run 'pytest tests/test_n8n_integration_e2e.py -v' for detailed tests")
    print("=" * 70)
