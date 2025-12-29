#!/usr/bin/env python3
"""
n8n MCP Server for Codespace

A Model Context Protocol (MCP) server that exposes n8n workflow management
capabilities to AI coding assistants in GitHub Codespaces.

This server provides tools for:
- Listing and managing n8n workflows
- Executing workflows
- Viewing execution history
- Health monitoring

Usage:
    python n8n_mcp_server.py

Environment:
    N8N_API_URL  - n8n API URL (default: http://localhost:5678/api/v1)
    N8N_API_KEY  - n8n API key (required)

Protocol:
    Uses JSON-RPC 2.0 over stdin/stdout as per MCP specification.
"""

import os
import sys
import json
import logging
from typing import Optional, Dict, Any, List

# Import the bridge for n8n operations
from bridge import N8nBridge

# Configure logging to stderr (MCP uses stdout for protocol)
logging.basicConfig(
    level=logging.INFO,
    format='[n8n-mcp] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class N8nMCPServer:
    """MCP Server for n8n workflow management."""
    
    def __init__(self):
        """Initialize the MCP server."""
        self.bridge = None
        self.request_id = 0
        
        # Server info
        self.server_info = {
            "name": "n8n-mcp-server",
            "version": "1.0.0"
        }
        
        # Define available tools
        self.tools = [
            {
                "name": "n8n_health",
                "description": "Check the health status of the n8n server. Returns whether the server is responsive and accessible.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "n8n_list_workflows",
                "description": "List all workflows in n8n. Returns workflow IDs, names, and active status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "n8n_get_workflow",
                "description": "Get detailed information about a specific n8n workflow including its nodes and connections.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow to retrieve"
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "n8n_activate_workflow",
                "description": "Activate an n8n workflow so it can respond to triggers.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow to activate"
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "n8n_deactivate_workflow",
                "description": "Deactivate an n8n workflow so it stops responding to triggers.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow to deactivate"
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "n8n_execute_workflow",
                "description": "Manually execute an n8n workflow. Optionally provide input data for the workflow.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow to execute"
                        },
                        "input_data": {
                            "type": "object",
                            "description": "Optional input data to pass to the workflow"
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "n8n_list_executions",
                "description": "List recent workflow executions. Optionally filter by workflow ID.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "Optional workflow ID to filter executions"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of executions to return (default: 20)",
                            "default": 20
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "n8n_get_execution",
                "description": "Get detailed information about a specific workflow execution including its output.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "The ID of the execution to retrieve"
                        }
                    },
                    "required": ["execution_id"]
                }
            }
        ]
    
    def _ensure_bridge(self) -> bool:
        """Ensure the bridge is initialized."""
        if self.bridge is None:
            try:
                self.bridge = N8nBridge()
                return True
            except ValueError as e:
                logger.error(f"Failed to initialize bridge: {e}")
                return False
        return True
    
    def _send_response(self, request_id: Any, result: Any = None, error: Any = None):
        """Send a JSON-RPC response."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }
        if error:
            response["error"] = error
        else:
            response["result"] = result
        
        output = json.dumps(response) + "\n"
        sys.stdout.write(output)
        sys.stdout.flush()
    
    def _handle_initialize(self, request_id: Any, params: Dict) -> None:
        """Handle initialization request."""
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": self.server_info
        }
        self._send_response(request_id, result)
    
    def _handle_list_tools(self, request_id: Any, params: Dict) -> None:
        """Handle tools/list request."""
        self._send_response(request_id, {"tools": self.tools})
    
    def _handle_call_tool(self, request_id: Any, params: Dict) -> None:
        """Handle tools/call request."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        try:
            result = self._execute_tool(tool_name, arguments)
            self._send_response(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
                    }
                ]
            })
        except Exception as e:
            self._send_response(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            })
    
    def _execute_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Execute a tool and return the result."""
        if not self._ensure_bridge():
            raise Exception("n8n bridge not configured. Set N8N_API_KEY environment variable.")
        
        if tool_name == "n8n_health":
            return self.bridge.health()
        
        elif tool_name == "n8n_list_workflows":
            workflows = self.bridge.list_workflows()
            return {
                "count": len(workflows),
                "workflows": [
                    {
                        "id": wf.get("id"),
                        "name": wf.get("name"),
                        "active": wf.get("active"),
                        "createdAt": wf.get("createdAt"),
                        "updatedAt": wf.get("updatedAt")
                    }
                    for wf in workflows
                ]
            }
        
        elif tool_name == "n8n_get_workflow":
            workflow_id = arguments.get("workflow_id")
            if not workflow_id:
                raise Exception("workflow_id is required")
            return self.bridge.get_workflow(workflow_id)
        
        elif tool_name == "n8n_activate_workflow":
            workflow_id = arguments.get("workflow_id")
            if not workflow_id:
                raise Exception("workflow_id is required")
            self.bridge.activate_workflow(workflow_id)
            return {"status": "activated", "workflow_id": workflow_id}
        
        elif tool_name == "n8n_deactivate_workflow":
            workflow_id = arguments.get("workflow_id")
            if not workflow_id:
                raise Exception("workflow_id is required")
            self.bridge.deactivate_workflow(workflow_id)
            return {"status": "deactivated", "workflow_id": workflow_id}
        
        elif tool_name == "n8n_execute_workflow":
            workflow_id = arguments.get("workflow_id")
            if not workflow_id:
                raise Exception("workflow_id is required")
            input_data = arguments.get("input_data")
            result = self.bridge.execute_workflow(workflow_id, input_data)
            return {
                "status": "executed",
                "workflow_id": workflow_id,
                "execution_id": result.get("executionId"),
                "result": result
            }
        
        elif tool_name == "n8n_list_executions":
            workflow_id = arguments.get("workflow_id")
            limit = arguments.get("limit", 20)
            executions = self.bridge.list_executions(workflow_id, limit)
            return {
                "count": len(executions),
                "executions": [
                    {
                        "id": ex.get("id"),
                        "status": ex.get("status"),
                        "startedAt": ex.get("startedAt"),
                        "stoppedAt": ex.get("stoppedAt"),
                        "workflowId": ex.get("workflowId"),
                        "workflowName": ex.get("workflowData", {}).get("name")
                    }
                    for ex in executions
                ]
            }
        
        elif tool_name == "n8n_get_execution":
            execution_id = arguments.get("execution_id")
            if not execution_id:
                raise Exception("execution_id is required")
            return self.bridge.get_execution(execution_id)
        
        else:
            raise Exception(f"Unknown tool: {tool_name}")
    
    def _handle_request(self, request: Dict) -> None:
        """Handle an incoming JSON-RPC request."""
        method = request.get("method", "")
        request_id = request.get("id")
        params = request.get("params", {})
        
        logger.debug(f"Handling method: {method}")
        
        if method == "initialize":
            self._handle_initialize(request_id, params)
        elif method == "initialized":
            # Notification, no response needed
            pass
        elif method == "tools/list":
            self._handle_list_tools(request_id, params)
        elif method == "tools/call":
            self._handle_call_tool(request_id, params)
        elif method == "ping":
            self._send_response(request_id, {})
        else:
            self._send_response(request_id, error={
                "code": -32601,
                "message": f"Method not found: {method}"
            })
    
    def run(self):
        """Main server loop - reads JSON-RPC requests from stdin."""
        logger.info("n8n MCP Server starting...")
        
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                self._handle_request(request)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                self._send_response(None, error={
                    "code": -32700,
                    "message": f"Parse error: {e}"
                })
            except Exception as e:
                logger.error(f"Unexpected error: {e}")


def main():
    """Entry point."""
    server = N8nMCPServer()
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Server shutting down")
        sys.exit(0)


if __name__ == "__main__":
    main()
