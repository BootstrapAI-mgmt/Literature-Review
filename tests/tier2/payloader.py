"""
Tier 2 Payloader Utility
Sends payloads to n8n webhooks for integration testing.
"""

import os
import json
import time
from typing import Dict, Optional, Any
from pathlib import Path

# requests is optional - graceful degradation for offline testing
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class PayloaderError(Exception):
    """Base exception for payloader errors"""
    pass


class ConnectionError(PayloaderError):
    """Failed to connect to n8n endpoint"""
    pass


class WebhookError(PayloaderError):
    """Webhook returned an error response"""
    pass


class Payloader:
    """
    Utility class for sending payloads to n8n webhooks.
    
    Usage:
        payloader = Payloader()
        response = payloader.send_to_webhook("/github-doc-trigger", payload)
    """
    
    # Default n8n Cloud base URL - can be overridden via environment
    DEFAULT_BASE_URL = "https://gitlitreview.app.n8n.cloud/webhook"
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = base_url or os.environ.get("N8N_WEBHOOK_URL", self.DEFAULT_BASE_URL)
        self.timeout = timeout
        self._session = None
    
    @property
    def session(self):
        """Lazy-load requests session"""
        if not REQUESTS_AVAILABLE:
            raise PayloaderError("requests library not installed")
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Content-Type": "application/json",
                "User-Agent": "ValidationFramework/2.0"
            })
        return self._session
    
    def send_to_webhook(self, endpoint: str, payload: Dict) -> Dict:
        """
        Send a payload to an n8n webhook endpoint.
        
        Args:
            endpoint: Webhook endpoint (e.g., "/github-doc-trigger")
            payload: JSON-serializable payload
            
        Returns:
            Response from webhook as dict
        """
        if not REQUESTS_AVAILABLE:
            # Return mock response for offline testing
            return {"status": "mock", "endpoint": endpoint, "received": True}
        
        url = f"{self.base_url}{endpoint}" if endpoint.startswith("/") else f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"status": "ok", "raw": response.text}
                
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to {url}: {e}")
        except requests.exceptions.Timeout:
            raise ConnectionError(f"Timeout connecting to {url}")
        except requests.exceptions.HTTPError as e:
            raise WebhookError(f"Webhook error: {e.response.status_code} - {e.response.text}")
    
    def check_distributor_status(self) -> Dict:
        """Check the status of the task distributor"""
        return self.send_to_webhook("/distributor-status", {})
    
    def reset_distributor(self) -> bool:
        """Reset the distributor queue"""
        try:
            response = self.send_to_webhook("/distributor-reset", {})
            return response.get("status") == "ok" or response.get("reset", False)
        except PayloaderError:
            return False
    
    def wait_for_execution(self, timeout: int = 60, poll_interval: int = 5) -> Optional[Dict]:
        """
        Wait for a workflow execution to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks
            
        Returns:
            Final execution status or None if timed out
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                status = self.check_distributor_status()
                if status.get("queue_empty", True) and status.get("processing", 0) == 0:
                    return status
            except PayloaderError:
                pass
            time.sleep(poll_interval)
        return None
    
    def trigger_github_push(self, modified_files: list = None) -> Dict:
        """Convenience method to trigger a GitHub push event"""
        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "BootstrapAI-mgmt/Literature-Review"},
            "pusher": {"name": "test-user"},
            "commits": [{
                "id": "test-commit-123",
                "message": "test: integration test commit",
                "modified": modified_files or ["docs/test.md"]
            }]
        }
        return self.send_to_webhook("/github-doc-trigger", payload)
    
    def trigger_pr_event(self, pr_number: int = 999, action: str = "opened") -> Dict:
        """Convenience method to trigger a PR event"""
        payload = {
            "action": action,
            "number": pr_number,
            "pull_request": {
                "number": pr_number,
                "title": f"Test PR #{pr_number}",
                "body": "Integration test PR",
                "state": "open",
                "head": {"ref": "test-branch"},
                "base": {"ref": "main"}
            },
            "repository": {"full_name": "BootstrapAI-mgmt/Literature-Review"}
        }
        return self.send_to_webhook("/pr-review", payload)


def send_to_webhook(endpoint: str, payload: Dict) -> Dict:
    """Convenience function for one-off webhook calls"""
    payloader = Payloader()
    return payloader.send_to_webhook(endpoint, payload)


def check_endpoint_available(endpoint: str) -> bool:
    """Check if an endpoint is reachable"""
    payloader = Payloader(timeout=5)
    try:
        payloader.send_to_webhook(endpoint, {})
        return True
    except PayloaderError:
        return False
