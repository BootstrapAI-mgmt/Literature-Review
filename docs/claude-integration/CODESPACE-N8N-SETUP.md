# n8n Integration for GitHub Codespaces

This guide covers setting up and using n8n workflow management directly from a GitHub Codespace. This enables AI coding assistants (like GitHub Copilot or Claude) to interact with, view, and manage n8n workflows for more efficient building and troubleshooting.

## 🚀 One-Line Bootstrap

For any new Codespace in this repository, run:

```bash
source ./bootstrap-n8n.sh
```

This will:
- Set up the n8n Cloud URL (`gitlitreview.app.n8n.cloud`)
- Check for the API key (must be added as a Codespace secret)
- Install dependencies if needed
- Test the connection

## Prerequisites (One-Time Setup)

**Add the N8N_API_KEY as a Codespace Secret:**

1. Go to: [Repository Secrets](https://github.com/BootstrapAI-mgmt/Literature-Review/settings/secrets/codespaces)
2. Click **New repository secret**
3. Name: `N8N_API_KEY`
4. Value: Get from n8n Cloud → Settings → Personal API Keys
5. Click **Add secret**

> **Note**: After adding the secret, you must rebuild the codespace or run `source /etc/environment` for it to take effect.

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                      GITHUB CODESPACE                               │
│  ┌──────────────────┐     ┌──────────────────┐                     │
│  │  AI Assistant    │────▶│  bridge.py       │                     │
│  │  (Copilot/Chat)  │◀────│  (CLI & Library) │                     │
│  └──────────────────┘     └────────┬─────────┘                     │
└───────────────────────────────────┼────────────────────────────────┘
                                    │
                                    ▼ HTTP API (JWT Auth)
┌──────────────────────────────────────────────────────────────────┐
│              n8n CLOUD: gitlitreview.app.n8n.cloud               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │
│  │ Doc Chain   │ │ Staleness   │ │   State     │                 │
│  │ Workflows   │ │ Review      │ │   Recon     │ + 8 more        │
│  └─────────────┘ └─────────────┘ └─────────────┘                 │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Using the Bootstrap Script (Recommended)

```bash
# Run once when opening a new codespace
source ./bootstrap-n8n.sh
```

### Manual Setup (Alternative)

```bash
# Set environment variables (already configured via Codespace secret)
export N8N_API_URL='https://gitlitreview.app.n8n.cloud/api/v1'
# N8N_API_KEY should be set via Codespace secret

# Test connection
python3 n8n-server/bridge.py health

# List workflows
python3 n8n-server/bridge.py list
```

### Running n8n Locally (Development Only)

For development/testing with a local n8n instance:

```bash
# Setup and install dependencies
cd n8n-server
./setup-codespace.sh

# Start n8n in background
./start-n8n-local.sh --background

# Wait for n8n to start, then open http://localhost:5678
# Create an API key in Settings > Personal API Keys

# Set the API key
export N8N_API_KEY='your-new-api-key'

# Test
python3 bridge.py health
```

## Available Tools

### CLI Bridge (`bridge.py`)

Direct command-line interface for n8n operations:

| Command | Description |
|---------|-------------|
| `python3 bridge.py health` | Check n8n server health |
| `python3 bridge.py list` | List all workflows |
| `python3 bridge.py get <id>` | Get workflow details |
| `python3 bridge.py activate <id>` | Activate a workflow |
| `python3 bridge.py deactivate <id>` | Deactivate a workflow |
| `python3 bridge.py execute <id>` | Execute a workflow |
| `python3 bridge.py executions [id]` | List recent executions |

Add `--json` for raw JSON output.

### MCP Server (`n8n_mcp_server.py`)

For AI assistant integration, the MCP server exposes these tools:

| Tool | Description |
|------|-------------|
| `n8n_health` | Check server health |
| `n8n_list_workflows` | List all workflows with status |
| `n8n_get_workflow` | Get workflow details including nodes |
| `n8n_activate_workflow` | Activate a workflow |
| `n8n_deactivate_workflow` | Deactivate a workflow |
| `n8n_execute_workflow` | Execute a workflow with optional input |
| `n8n_list_executions` | List recent executions |
| `n8n_get_execution` | Get execution details and output |

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `N8N_API_URL` | No | `http://localhost:5678/api/v1` | n8n API endpoint |
| `N8N_API_KEY` | Yes | - | API key from n8n |

### Storing Credentials Securely

For Codespaces, use GitHub Secrets:

1. Go to Repository Settings > Secrets and variables > Codespaces
2. Add `N8N_API_KEY` as a secret
3. Add `N8N_API_URL` as a variable (if using remote n8n)

These will be automatically available as environment variables.

## Integration Examples

### From AI Chat

Once configured, you can ask the AI assistant:

- "List all my n8n workflows"
- "Check if n8n server is healthy"
- "Show me the details of the Doc Chain - Agent workflow"
- "Execute the Staleness Review workflow"
- "What were the recent workflow executions?"

### From Python Scripts

```python
from n8n_server.bridge import N8nBridge

# Initialize (uses environment variables)
bridge = N8nBridge()

# Check health
status = bridge.health()
print(f"n8n is {status['status']}")

# List workflows
workflows = bridge.list_workflows()
for wf in workflows:
    print(f"  {wf['id']}: {wf['name']} (active={wf['active']})")

# Execute a workflow
result = bridge.execute_workflow('workflow-id', {'input': 'data'})
print(f"Execution ID: {result['executionId']}")
```

### From Shell Scripts

```bash
#!/bin/bash
# Check n8n and list active workflows

if python3 n8n-server/bridge.py health > /dev/null 2>&1; then
    echo "n8n is running"
    python3 n8n-server/bridge.py list | grep "✓"
else
    echo "n8n is not available"
fi
```

## Troubleshooting

### Connection Refused

```
Error: Connection Error: Connection refused
```

- Verify n8n is running: `curl http://localhost:5678/api/v1/workflows`
- Check `N8N_API_URL` is correct
- For remote servers, check network/firewall rules

### Authentication Failed

```
Error: API Error (401): Unauthorized
```

- Verify `N8N_API_KEY` is set correctly
- Generate a new API key in n8n if needed
- Check the API key hasn't expired

### Workflow Not Found

```
Error: API Error (404): Workflow not found
```

- List workflows to verify the ID: `python3 bridge.py list`
- Workflow IDs may change after import

## Security Notes

- **Never commit API keys** to the repository
- Use GitHub Secrets for Codespaces
- Rotate API keys periodically
- For local development, keep n8n on localhost only
- For remote n8n, use HTTPS

## Files Reference

```
n8n-server/
├── bridge.py              # Python API bridge (CLI & library)
├── n8n_mcp_server.py      # MCP server for AI integration
├── start-mcp.sh           # Start MCP server
├── start-n8n-local.sh     # Start local n8n instance
├── setup-codespace.sh     # One-time codespace setup
├── curl-mcp.mjs           # Node.js HTTP bridge (alternative)
├── README.md              # General n8n-server documentation
└── Doc Chain - *.json     # Workflow definitions
```

## Related Documentation

- [Claude Integration Architecture](./ARCHITECTURE.md)
- [Claude Integration Setup](./SETUP.md)
- [n8n Documentation Chain Blueprint](../N8N_DOCUMENTATION_CHAIN_BLUEPRINT.md)
- [n8n AI Builder Prompt](../N8N_AI_BUILDER_PROMPT.md)

---

*Last Updated: 2024-12-29*
