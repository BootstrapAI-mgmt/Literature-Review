#!/usr/bin/env python3
"""
Antigravity MCP Client for n8n

A simple client to interact with the n8n MCP Bridge workflow.
This provides Antigravity agents with direct access to n8n via webhooks,
bypassing API key authentication issues.

Usage:
    python mcp_client.py health
    python mcp_client.py list_workflows
    python mcp_client.py get_workflow <workflow_id>
    python mcp_client.py get_executions [limit]
    python mcp_client.py trigger <file1> [file2] ...
    python mcp_client.py help
"""

import os
import sys
import json
from typing import Optional, List, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class MCPClient:
    """Client for the n8n MCP Bridge workflow."""
    
    # Default MCP Bridge webhook URL
    DEFAULT_URL = "https://gitlitreview.app.n8n.cloud/webhook/antigravity-bridge"
    
    def __init__(self, webhook_url: Optional[str] = None, timeout: int = 30):
        """Initialize the MCP client."""
        self.webhook_url = webhook_url or os.environ.get('N8N_MCP_URL', self.DEFAULT_URL)
        self.timeout = timeout
    
    def _request(self, action: str, params: Dict = None) -> Dict[str, Any]:
        """Make a request to the MCP Bridge."""
        payload = {
            "action": action,
            "params": params or {},
            "request_id": f"ag-{int(__import__('time').time() * 1000)}"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Antigravity-MCP-Client/1.0'
        }
        
        body = json.dumps(payload).encode('utf-8')
        request = Request(self.webhook_url, data=body, headers=headers, method='POST')
        
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            try:
                error_json = json.loads(error_body)
                return {"error": f"HTTP {e.code}", "details": error_json}
            except json.JSONDecodeError:
                return {"error": f"HTTP {e.code}", "details": error_body}
        except URLError as e:
            return {"error": "Connection Error", "details": str(e.reason)}
    
    def health(self) -> Dict[str, Any]:
        """Check n8n server health."""
        return self._request("health")
    
    def help(self) -> Dict[str, Any]:
        """Get list of available tools."""
        return self._request("help")
    
    def list_workflows(self) -> Dict[str, Any]:
        """List all n8n workflows."""
        return self._request("list_workflows")
    
    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow details."""
        return self._request("get_workflow", {"workflow_id": workflow_id})
    
    def get_executions(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent executions."""
        return self._request("get_executions", {"limit": limit})
    
    def trigger(self, modified_files: List[str]) -> Dict[str, Any]:
        """Trigger a workflow with modified files."""
        return self._request("trigger_workflow", {"modified_files": modified_files})


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python mcp_client.py <action> [args]")
        print("Actions: health, help, list_workflows, get_workflow, get_executions, trigger")
        sys.exit(1)
    
    client = MCPClient()
    action = sys.argv[1].lower()
    
    result = None
    
    if action == "health":
        result = client.health()
    elif action == "help":
        result = client.help()
    elif action in ["list", "list_workflows"]:
        result = client.list_workflows()
    elif action in ["get", "get_workflow"]:
        if len(sys.argv) < 3:
            print("Error: workflow_id required")
            sys.exit(1)
        result = client.get_workflow(sys.argv[2])
    elif action in ["executions", "get_executions"]:
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        result = client.get_executions(limit)
    elif action == "trigger":
        if len(sys.argv) < 3:
            print("Error: at least one file path required")
            sys.exit(1)
        result = client.trigger(sys.argv[2:])
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
