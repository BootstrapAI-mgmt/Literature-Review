---
description: How to manage and interact with the local n8n server
---

# n8n Workflow Management

This workflow describes how agents should interact with the local n8n server using the `bridge.py` script.

## Pre-requisites
- **Bridge Script**: `n8n-server/bridge.py`
- **Environment**: Must have `N8N_API_KEY` set (or pass it in execution context).
- **Python**: Requires `python` and `requests`.

## Standard Procedures

### 1. Check Server Status
Before performing operations, check if the server is responsive. This helps coordinate with other clients (like Claude Desktop) by ensuring the server is not undergoing a restart or heavy load timeout.

```bash
python n8n-server/bridge.py health
```
*If this fails, wait or notify the user.*

### 2. List Workflows
To see what automation is available:
```bash
python n8n-server/bridge.py list
```
*Returns: ID | Active Status | Name*

### 3. Activate/Deactivate
To enable or disable a specific workflow logic:
```bash
python n8n-server/bridge.py activate [WORKFLOW_ID]
python n8n-server/bridge.py deactivate [WORKFLOW_ID]
```

### 4. Direct API Interaction
If more complex interaction is needed (e.g., triggering a webhook execution), use `curl` or construct a custom Python request based on the ID retrieved from `list`.

**Concurrency Note**: 
It is safe to interact with the n8n server (port 5678) even while the user is connected via Claude Desktop (MCP). The n8n server handles concurrent API requests. However, avoid **modifying** (saving) the same workflow at the exact same time someone else is editing it in the UI.

## Troubleshooting
- **401 Unauthorized**: Check `N8N_API_KEY`.
- **Connection Refused**: Check if `start-all.bat` or `start-n8n.bat` is running.
