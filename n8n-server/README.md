# n8n Server for Literature Review

This directory contains tools for integrating [n8n](https://n8n.io/) workflow automation with the Literature Review project. It supports both local n8n instances and remote servers.

## Quick Start

### For GitHub Codespaces

```bash
# Setup environment
./setup-codespace.sh

# Set your n8n API credentials (use GitHub Secrets for persistence)
export N8N_API_URL='https://your-n8n-server.example.com/api/v1'
export N8N_API_KEY='your-api-key'

# Test connection
python3 bridge.py health
python3 bridge.py list
```

### For Local Development (Windows/Mac/Linux)

1. **Start the Server**: Run `npm start` in this directory
2. **Access n8n**: Open [http://localhost:5678](http://localhost:5678)
3. **Setup**: Follow on-screen instructions to create your account

## Files Overview

| File | Purpose |
|------|---------|
| `bridge.py` | Python CLI & library for n8n API |
| `n8n_mcp_server.py` | MCP server for AI assistant integration |
| `curl-mcp.mjs` | Node.js HTTP bridge (alternative) |
| `start-mcp.sh` | Start the MCP server (Linux/Mac) |
| `start-n8n-local.sh` | Start local n8n instance |
| `setup-codespace.sh` | One-time codespace setup |
| `Doc Chain - *.json` | Workflow definitions to import |

## Workflows

The documentation workflows described in `../docs/N8N_AI_BUILDER_PROMPT.md` can be imported here.

## Configuration

- **Port**: 5678 (default)
- **Data**: Stored in `~/.n8n` by default

## API Key Setup

1. **Generate API Key**:
   - Open n8n at [http://localhost:5678](http://localhost:5678)
   - Go to **Settings** > **Personal API Keys**
   - Create a new API Key and copy it

2. **Set Environment Variables**:
   ```bash
   export N8N_API_URL='http://localhost:5678/api/v1'
   export N8N_API_KEY='your-api-key'
   ```

## CLI Usage (bridge.py)

```bash
# Check server health
python3 bridge.py health

# List all workflows
python3 bridge.py list

# Get workflow details
python3 bridge.py get <workflow_id>

# Activate/deactivate workflows
python3 bridge.py activate <workflow_id>
python3 bridge.py deactivate <workflow_id>

# Execute a workflow
python3 bridge.py execute <workflow_id>

# View executions
python3 bridge.py executions [workflow_id]

# Get JSON output
python3 bridge.py list --json
```

## MCP Integration

### For GitHub Codespaces / VS Code

The Python MCP server can be started with:

```bash
./start-mcp.sh
# or
python3 n8n_mcp_server.py
```

This exposes tools like `n8n_list_workflows`, `n8n_execute_workflow`, etc.

### For Claude Desktop

To connect Claude Desktop to this n8n server, you must edit your configuration file:

1.  **Locate Config File**:
    *   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
    *   **Mac/Linux**: `~/.config/Claude/claude_desktop_config.json`

2.  **Add n8n Server**:
    Add the following entry to the `mcpServers` object (replace `YOUR_API_KEY`):

    ```json
    {
      "mcpServers": {
        "n8n": {
          "command": "npx.cmd",
          "args": [
            "-y",
            "@leonardsellem/n8n-mcp-server"
          ],
          "env": {
            "N8N_API_URL": "http://localhost:5678/api/v1",
            "N8N_API_KEY": "YOUR_GENERATED_API_KEY_HERE"
          }
        }
      }
    }
    ```

    > **Note**: On Windows, we use `npx.cmd`. On Mac/Linux, use `npx`.

3.  **Restart Claude**: Fully quit and restart Claude Desktop to pick up the changes.

    ### Curl / HTTP Request Bridge

    To allow Claude to make direct HTTP requests (curls) from your local machine (bypassing proxy restrictions), add this additional server to your configuration:

    ```json
    "curl-bridge": {
      "command": "node",
      "args": [
        "C:\\Users\\jpcol\\Documents\\Literature-Review\\Literature-Review\\n8n-server\\curl-mcp.mjs"
      ]
    }
    ```

    Ensure the path to `curl-mcp.mjs` is absolute and matches where the file is located.
