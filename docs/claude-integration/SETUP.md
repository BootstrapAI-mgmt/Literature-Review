# Claude Integration Setup Guide

This guide walks through the complete setup process for integrating Claude Desktop with GitHub and n8n.

## Prerequisites

- **Claude Desktop** (v1.0.2339 or later)
- **Node.js** (v18 or later)
- **Git** configured with GitHub credentials
- **n8n** server installed locally

## Step 1: Verify Claude Desktop Installation

1. Ensure Claude Desktop is installed and running
2. Verify MCP extensions are available:
   - Desktop Commander
   - Filesystem MCP
   - PDF Tools (optional)

## Step 2: Start n8n Server

```powershell
cd C:\Users\jpcol\Documents\Literature-Review\Literature-Review\n8n-server
npm start
```

Access n8n at: [http://localhost:5678](http://localhost:5678)

## Step 3: Generate n8n API Key

1. Open n8n in browser: `http://localhost:5678`
2. Complete initial setup (if first time)
3. Navigate to **Settings** → **Personal API Keys**
4. Click **Create API Key**
5. Name it (e.g., "Claude Desktop")
6. Copy the generated key immediately (won't be shown again)

## Step 4: Generate GitHub Personal Access Token

1. Go to [GitHub Token Settings](https://github.com/settings/tokens)
2. Click **Generate new token** → **Generate new token (classic)**
3. Set expiration (recommend 90 days)
4. Select scopes:
   - [x] `repo` - Full control of private repositories
   - [x] `workflow` - Update GitHub Action workflows
   - [x] `read:org` - Read org membership (if using org repos)
   - [x] `codespace` - Codespace management (optional)
5. Click **Generate token**
6. Copy the token immediately

## Step 5: Configure Claude Desktop

### Location
```
Windows: %APPDATA%\Claude\claude_desktop_config.json
Mac/Linux: ~/.config/Claude/claude_desktop_config.json
```

### Configuration File


Edit the config file and add your credentials:

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
        "N8N_API_KEY": "YOUR_N8N_API_KEY_HERE"
      }
    },
    "github": {
      "command": "npx.cmd",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_GITHUB_PAT_HERE"
      }
    }
  }
}
```

> **Note**: On Mac/Linux, use `npx` instead of `npx.cmd`

## Step 6: Configure Filesystem Access

### Location
```
%APPDATA%\Claude\Claude Extensions Settings\ant.dir.ant.anthropic.filesystem.json
```

### Configuration
```json
{
  "isEnabled": true,
  "userConfig": {
    "allowed_directories": [
      "C:\\Users\\jpcol\\Documents\\Literature-Review\\Literature-Review"
    ]
  }
}
```

## Step 7: Restart Claude Desktop

1. Fully quit Claude Desktop (not just close window)
2. Reopen Claude Desktop
3. Wait for MCP servers to initialize

## Step 8: Verify Connections

### Test n8n Connection
Ask Claude: "List my n8n workflows"

Expected: List of available workflows or empty list if none created

### Test GitHub Connection
Ask Claude: "Show me the latest commits on BootstrapAI-mgmt/Literature-Review"

Expected: Recent commit history

### Test File Access
Ask Claude: "Read the README.md from the Literature-Review repository"

Expected: Contents of the README file

## Troubleshooting

### n8n MCP Not Connecting

1. Verify n8n is running: `http://localhost:5678`
2. Check API key is valid
3. View logs: `%APPDATA%\Claude\logs\mcp.log`

### GitHub MCP Not Connecting

1. Verify PAT hasn't expired
2. Check PAT has required scopes
3. Test PAT with curl:
```powershell
curl -H "Authorization: token YOUR_PAT" https://api.github.com/user
```

### Filesystem Access Denied

1. Verify path in allowed_directories
2. Use double backslashes in Windows paths
3. Restart Claude Desktop after config changes

## Quick Reference

| Component | Config Location |
|-----------|-----------------|
| MCP Servers | `%APPDATA%\Claude\claude_desktop_config.json` |
| Filesystem | `%APPDATA%\Claude\Claude Extensions Settings\ant.dir.ant.anthropic.filesystem.json` |
| Desktop Commander | `%APPDATA%\Claude\Claude Extensions Settings\ant.dir.gh.wonderwhy-er.desktopcommandermcp.json` |
| Logs | `%APPDATA%\Claude\logs\` |

## Security Reminders

- ⚠️ Never commit `claude_desktop_config.json` with real credentials
- ⚠️ Rotate API keys periodically
- ⚠️ Use minimal required scopes for GitHub PAT
- ⚠️ Keep n8n server on localhost only

---

*Last Updated: 2024-12-23*
