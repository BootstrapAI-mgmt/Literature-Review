#!/usr/bin/env python3
"""
n8n API Bridge for Literature Review

A Python-based bridge for interacting with n8n workflows from the codespace.
This provides a consistent interface for both direct CLI usage and MCP server integration.

Usage:
    python bridge.py health              # Check server status
    python bridge.py list                # List all workflows
    python bridge.py get <workflow_id>   # Get workflow details
    python bridge.py activate <id>       # Activate a workflow
    python bridge.py deactivate <id>     # Deactivate a workflow
    python bridge.py execute <id>        # Execute a workflow
    python bridge.py executions [id]     # List executions (optionally for workflow)

Environment:
    N8N_API_URL  - n8n API URL (default: http://localhost:5678/api/v1)
    N8N_API_KEY  - n8n API key (required)
"""

import os
import sys
import json
import argparse
from typing import Optional, Dict, Any, List
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin


class N8nBridge:
    """Bridge for n8n API interactions."""
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize the bridge with API credentials."""
        self.api_url = api_url or os.environ.get('N8N_API_URL', 'http://localhost:5678/api/v1')
        self.api_key = api_key or os.environ.get('N8N_API_KEY', '')
        
        # Ensure URL ends with /
        if not self.api_url.endswith('/'):
            self.api_url += '/'
            
        if not self.api_key:
            raise ValueError("N8N_API_KEY environment variable is required")
    
    def _request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """Make an authenticated request to the n8n API."""
        url = urljoin(self.api_url, endpoint)
        headers = {
            'X-N8N-API-KEY': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        body = json.dumps(data).encode('utf-8') if data else None
        request = Request(url, data=body, headers=headers, method=method)
        
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            try:
                error_json = json.loads(error_body)
                raise Exception(f"API Error ({e.code}): {error_json.get('message', error_body)}")
            except json.JSONDecodeError:
                raise Exception(f"API Error ({e.code}): {error_body}")
        except URLError as e:
            raise Exception(f"Connection Error: {e.reason}")
    
    def health(self) -> Dict[str, Any]:
        """Check n8n server health status."""
        try:
            # Try to list workflows as a health check
            self._request('workflows')
            return {
                'status': 'healthy',
                'api_url': self.api_url,
                'message': 'n8n server is responsive'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'api_url': self.api_url,
                'message': str(e)
            }
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows."""
        result = self._request('workflows')
        return result.get('data', [])
    
    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a specific workflow by ID."""
        return self._request(f'workflows/{workflow_id}')
    
    def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Activate a workflow."""
        return self._request(f'workflows/{workflow_id}/activate', method='POST')
    
    def deactivate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Deactivate a workflow."""
        return self._request(f'workflows/{workflow_id}/deactivate', method='POST')
    
    def execute_workflow(self, workflow_id: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a workflow with optional input data."""
        payload = data or {}
        return self._request(f'workflows/{workflow_id}/execute', method='POST', data=payload)
    
    def list_executions(self, workflow_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """List workflow executions."""
        endpoint = 'executions'
        if workflow_id:
            endpoint += f'?workflowId={workflow_id}&limit={limit}'
        else:
            endpoint += f'?limit={limit}'
        result = self._request(endpoint)
        return result.get('data', [])
    
    def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Get a specific execution by ID."""
        return self._request(f'executions/{execution_id}')
    
    def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow."""
        return self._request('workflows', method='POST', data=workflow_data)
    
    def update_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing workflow."""
        return self._request(f'workflows/{workflow_id}', method='PUT', data=workflow_data)
    
    def delete_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Delete a workflow."""
        return self._request(f'workflows/{workflow_id}', method='DELETE')


def format_workflows_table(workflows: List[Dict]) -> str:
    """Format workflows as a readable table."""
    if not workflows:
        return "No workflows found."
    
    lines = ["ID | Active | Name", "-" * 60]
    for wf in workflows:
        active = "✓" if wf.get('active') else "✗"
        lines.append(f"{wf.get('id', 'N/A'):>6} | {active:^6} | {wf.get('name', 'Unnamed')}")
    return "\n".join(lines)


def format_executions_table(executions: List[Dict]) -> str:
    """Format executions as a readable table."""
    if not executions:
        return "No executions found."
    
    lines = ["ID | Status | Started | Workflow", "-" * 80]
    for ex in executions:
        status = ex.get('status', 'unknown')
        started = ex.get('startedAt', 'N/A')[:19] if ex.get('startedAt') else 'N/A'
        workflow = ex.get('workflowData', {}).get('name', ex.get('workflowId', 'Unknown'))
        lines.append(f"{ex.get('id', 'N/A'):>8} | {status:^10} | {started} | {workflow[:30]}")
    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='n8n API Bridge for Literature Review',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--api-url', help='n8n API URL (or set N8N_API_URL)')
    parser.add_argument('--api-key', help='n8n API key (or set N8N_API_KEY)')
    parser.add_argument('--json', action='store_true', help='Output raw JSON')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Health check
    subparsers.add_parser('health', help='Check n8n server health')
    
    # List workflows
    subparsers.add_parser('list', help='List all workflows')
    
    # Get workflow
    get_parser = subparsers.add_parser('get', help='Get workflow details')
    get_parser.add_argument('workflow_id', help='Workflow ID')
    
    # Activate workflow
    activate_parser = subparsers.add_parser('activate', help='Activate a workflow')
    activate_parser.add_argument('workflow_id', help='Workflow ID')
    
    # Deactivate workflow
    deactivate_parser = subparsers.add_parser('deactivate', help='Deactivate a workflow')
    deactivate_parser.add_argument('workflow_id', help='Workflow ID')
    
    # Execute workflow
    execute_parser = subparsers.add_parser('execute', help='Execute a workflow')
    execute_parser.add_argument('workflow_id', help='Workflow ID')
    execute_parser.add_argument('--data', help='JSON input data for execution')
    
    # List executions
    executions_parser = subparsers.add_parser('executions', help='List executions')
    executions_parser.add_argument('workflow_id', nargs='?', help='Optional workflow ID filter')
    executions_parser.add_argument('--limit', type=int, default=20, help='Max results')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        bridge = N8nBridge(api_url=args.api_url, api_key=args.api_key)
        result = None
        
        if args.command == 'health':
            result = bridge.health()
            if not args.json:
                status = result['status']
                emoji = "✓" if status == 'healthy' else "✗"
                print(f"{emoji} Status: {status}")
                print(f"  URL: {result['api_url']}")
                print(f"  Message: {result['message']}")
                sys.exit(0 if status == 'healthy' else 1)
        
        elif args.command == 'list':
            result = bridge.list_workflows()
            if not args.json:
                print(format_workflows_table(result))
                sys.exit(0)
        
        elif args.command == 'get':
            result = bridge.get_workflow(args.workflow_id)
        
        elif args.command == 'activate':
            result = bridge.activate_workflow(args.workflow_id)
            if not args.json:
                print(f"✓ Workflow {args.workflow_id} activated")
                sys.exit(0)
        
        elif args.command == 'deactivate':
            result = bridge.deactivate_workflow(args.workflow_id)
            if not args.json:
                print(f"✓ Workflow {args.workflow_id} deactivated")
                sys.exit(0)
        
        elif args.command == 'execute':
            data = json.loads(args.data) if args.data else None
            result = bridge.execute_workflow(args.workflow_id, data)
            if not args.json:
                print(f"✓ Workflow {args.workflow_id} executed")
                print(f"  Execution ID: {result.get('executionId', 'N/A')}")
                sys.exit(0)
        
        elif args.command == 'executions':
            result = bridge.list_executions(args.workflow_id, args.limit)
            if not args.json:
                print(format_executions_table(result))
                sys.exit(0)
        
        # Default JSON output
        print(json.dumps(result, indent=2))
        
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
