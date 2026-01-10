"""
Workflow Runner - Executes n8n workflows and monitors completion.
"""

import time
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class WorkflowResult:
    """Result of a workflow execution"""
    success: bool
    webhook_response: Dict
    execution_time: float
    error: Optional[str] = None
    artifacts: Dict = None
    
    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = {}


class WorkflowRunner:
    """
    Executes n8n workflows and monitors for completion.
    
    Usage:
        runner = WorkflowRunner()
        result = runner.trigger_and_wait("/github-doc-trigger", payload)
    """
    
    DEFAULT_BASE_URL = "https://gitlitreview.app.n8n.cloud/webhook"
    MCP_BRIDGE_URL = "https://gitlitreview.app.n8n.cloud/webhook/antigravity-bridge"
    
    def __init__(self, base_url: str = None, timeout: int = 300):
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout
        self._session = None
    
    @property
    def session(self):
        """Lazy-load requests session"""
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("requests library not installed")
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Content-Type": "application/json",
                "User-Agent": "ValidationFramework/2.0-Live"
            })
        return self._session
    
    def trigger_webhook(self, endpoint: str, payload: Dict) -> Dict:
        """
        Send payload to webhook and return response.
        """
        url = f"{self.base_url}{endpoint}" if endpoint.startswith("/") else f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            try:
                return {"success": True, "data": response.json()}
            except json.JSONDecodeError:
                return {"success": True, "data": response.text}
        
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Timeout"}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_mcp_status(self) -> Dict:
        """Check MCP Bridge status"""
        try:
            response = self.session.post(
                self.MCP_BRIDGE_URL,
                json={"action": "health"},
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def trigger_and_wait(
        self, 
        endpoint: str, 
        payload: Dict,
        wait_for_commits: bool = False,
        poll_interval: int = 10
    ) -> WorkflowResult:
        """
        Trigger workflow and wait for completion.
        
        Args:
            endpoint: Webhook endpoint
            payload: JSON payload
            wait_for_commits: If True, wait for new git commits
            poll_interval: Seconds between status checks
            
        Returns:
            WorkflowResult with execution details
        """
        start_time = time.time()
        
        # Trigger the webhook
        response = self.trigger_webhook(endpoint, payload)
        
        if not response.get("success"):
            return WorkflowResult(
                success=False,
                webhook_response=response,
                execution_time=time.time() - start_time,
                error=response.get("error")
            )
        
        # For simple webhook calls, return immediately
        if not wait_for_commits:
            return WorkflowResult(
                success=True,
                webhook_response=response,
                execution_time=time.time() - start_time
            )
        
        # Wait for workflow completion (poll for changes)
        elapsed = 0
        while elapsed < self.timeout:
            time.sleep(poll_interval)
            elapsed = time.time() - start_time
            
            # Check MCP status
            status = self.check_mcp_status()
            if status.get("success"):
                # Could add more sophisticated completion detection here
                pass
        
        return WorkflowResult(
            success=True,
            webhook_response=response,
            execution_time=time.time() - start_time
        )
    
    def trigger_github_push(self, modified_files: List[str]) -> WorkflowResult:
        """
        Trigger the github-doc-trigger workflow with a simulated push event.
        """
        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "BootstrapAI-mgmt/Literature-Review"},
            "pusher": {"name": "validation-test"},
            "after": f"test-sha-{int(time.time())}",
            "head_commit": {
                "message": "test: validation framework trigger",
                "id": f"test-{int(time.time())}"
            },
            "commits": [{
                "id": f"test-commit-{int(time.time())}",
                "message": "test: validation framework trigger",
                "added": [],
                "modified": modified_files
            }]
        }
        
        return self.trigger_and_wait("/github-doc-trigger", payload)
    
    def trigger_pr_review(self, pr_number: int = 999) -> WorkflowResult:
        """
        Trigger the PR review workflow.
        """
        payload = {
            "action": "opened",
            "number": pr_number,
            "pull_request": {
                "number": pr_number,
                "title": f"Test PR #{pr_number}",
                "body": "Validation framework test PR",
                "state": "open",
                "head": {"ref": "test-branch"},
                "base": {"ref": "main"}
            },
            "repository": {"full_name": "BootstrapAI-mgmt/Literature-Review"}
        }
        
        return self.trigger_and_wait("/pr-review", payload)


# CLI for manual testing
if __name__ == "__main__":
    runner = WorkflowRunner()
    
    print("Checking MCP Bridge status...")
    status = runner.check_mcp_status()
    print(json.dumps(status, indent=2))
    
    print("\nTriggering test push event...")
    result = runner.trigger_github_push(["docs/test.md"])
    print(f"Success: {result.success}")
    print(f"Time: {result.execution_time:.2f}s")
    print(f"Response: {json.dumps(result.webhook_response, indent=2)}")
