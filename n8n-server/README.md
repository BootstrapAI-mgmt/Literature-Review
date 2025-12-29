# n8n Server for Literature Review

This directory contains a local installation of [n8n](https://n8n.io/) for automating documentation and other workflows in the Literature Review project.

## Getting Started

1.  **Start the Server**: Run `start-n8n.bat` or execute `npm start` in this directory.
2.  **Access n8n**: Open your browser to [http://localhost:5678](http://localhost:5678).
3.  **Setup**: Follow the on-screen instructions to set up your owner account.

## Workflows

The documentation workflows described in `../docs/N8N_AI_BUILDER_PROMPT.md` can be imported or built here.

## Configuration

-   **Port**: 5678 (default)
-   **Data**: Stored in `~/.n8n` by default.

## Quick Start

1.  **Generate API Key**:
    *   Open n8n at [http://localhost:5678](http://localhost:5678).
    *   Go to **Settings** > **Personal API Keys**.
    *   Create a new API Key and copy it.

2.  **Start Everything**:
    *   Run `start-all.bat`.
    *   Paste your API Key when prompted.
    *   This will:
        *   Import all "Doc Chain" workflows.
        *   Start n8n in the background (logs to `n8n.log`).
        *   Start the MCP server in the background (logs to `mcp.log`).

## MCP Integration

### Claude Desktop Configuration

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
