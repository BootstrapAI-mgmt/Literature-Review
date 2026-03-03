---
description: How to manage and interact with the local n8n server
---

# n8n Workflow Management

This workflow describes how agents should interact with the n8n server using the `bridge.py` script.

## Pre-requisites
- **Bridge Script**: `n8n-server/bridge.py`
- **MCP Server**: `n8n-server/n8n_mcp_server.py` (for MCP integration)
- **Environment**: Must have `N8N_API_KEY` set (required) and optionally `N8N_API_URL`
- **Python**: Requires `python3` (no additional dependencies)

## Environment Setup

```bash
# Required - set your n8n API key
export N8N_API_KEY='your-api-key-here'

# Optional - for remote n8n servers (default is localhost:5678)
export N8N_API_URL='https://your-n8n-server.com/api/v1'
```

## Standard Procedures

### 1. Check Server Status
Before performing operations, check if the server is responsive:

```bash
python3 n8n-server/bridge.py health
```
*If this fails, wait or notify the user.*

### 2. List Workflows
To see what automation is available:

```bash
python3 n8n-server/bridge.py list
```
*Returns: ID | Active Status | Name*

### 3. Get Workflow Details
To see the full configuration of a workflow:

```bash
python3 n8n-server/bridge.py get <WORKFLOW_ID>
python3 n8n-server/bridge.py get <WORKFLOW_ID> --json  # For raw JSON
```

### 4. Activate/Deactivate
To enable or disable a specific workflow:

```bash
python3 n8n-server/bridge.py activate <WORKFLOW_ID>
python3 n8n-server/bridge.py deactivate <WORKFLOW_ID>
```

### 5. Execute a Workflow
To manually trigger a workflow execution:

```bash
python3 n8n-server/bridge.py execute <WORKFLOW_ID>
python3 n8n-server/bridge.py execute <WORKFLOW_ID> --data '{"key": "value"}'
```

### 6. View Execution History
To see recent workflow executions:

```bash
python3 n8n-server/bridge.py executions
python3 n8n-server/bridge.py executions <WORKFLOW_ID>  # Filter by workflow
```

## MCP Server (for AI Integration)

For MCP-compatible clients, start the MCP server:

```bash
cd n8n-server && ./start-mcp.sh
# or directly:
python3 n8n-server/n8n_mcp_server.py
```

Available MCP tools:
- `n8n_health` - Check server health
- `n8n_list_workflows` - List all workflows
- `n8n_get_workflow` - Get workflow details
- `n8n_activate_workflow` - Activate a workflow
- `n8n_deactivate_workflow` - Deactivate a workflow
- `n8n_execute_workflow` - Execute a workflow
- `n8n_list_executions` - List recent executions
- `n8n_get_execution` - Get execution details

## Concurrency Note
It is safe to interact with the n8n server (port 5678) even while the user is connected via Claude Desktop (MCP). The n8n server handles concurrent API requests. However, avoid **modifying** (saving) the same workflow at the exact same time someone else is editing it in the UI.

## Troubleshooting
- **401 Unauthorized**: Check `N8N_API_KEY` is set correctly
- **Connection Refused**: Check if n8n server is running and `N8N_API_URL` is correct
- **Workflow Not Found**: Verify workflow ID with `python3 bridge.py list`
- **Timeout**: n8n server may be overloaded; wait and retry
