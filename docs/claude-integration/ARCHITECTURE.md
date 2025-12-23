# Claude Integration Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLAUDE DESKTOP                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         MCP Server Layer                             │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │   │
│  │  │   Desktop    │ │  Filesystem  │ │    n8n       │ │   GitHub    │ │   │
│  │  │  Commander   │ │     MCP      │ │    MCP       │ │    MCP      │ │   │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬──────┘ │   │
│  └─────────┼────────────────┼────────────────┼────────────────┼────────┘   │
└────────────┼────────────────┼────────────────┼────────────────┼────────────┘
             │                │                │                │
             ▼                ▼                ▼                ▼
┌────────────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐
│  Local Filesystem  │ │ Literature- │ │ n8n Server  │ │     GitHub API      │
│  - Shell commands  │ │ Review Repo │ │ :5678       │ │  - Repository       │
│  - Git CLI         │ │ (read/write)│ │ - Workflows │ │  - Actions          │
│  - Process mgmt    │ │             │ │ - Execution │ │  - Issues/PRs       │
└────────────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘
```

## Component Details

### 1. Desktop Commander MCP

**Purpose**: General-purpose shell access and process management

**Capabilities**:
- Execute PowerShell/CMD commands
- File read/write operations (unrestricted)
- Process management (start, monitor, terminate)
- Git CLI operations
- Search and navigation

**Configuration**: Built-in Claude Desktop extension
```json
{
  "isEnabled": true,
  "allowedDirectories": []  // Empty = unrestricted
}
```

### 2. Filesystem MCP

**Purpose**: Structured file access with explicit directory permissions

**Capabilities**:
- Read/write files in allowed directories
- Directory listing and navigation
- File metadata retrieval

**Configuration**: `Claude Extensions Settings/ant.dir.ant.anthropic.filesystem.json`
```json
{
  "isEnabled": true,
  "userConfig": {
    "allowed_directories": [
      "C:\\Users\\jpcol\\PycharmProjects\\FileFolderStructure",
      "C:\\Users\\jpcol\\Documents\\Literature-Review\\Literature-Review"
    ]
  }
}
```


### 3. n8n MCP Server

**Purpose**: Workflow automation management and execution

**Package**: `@leonardsellem/n8n-mcp-server`

**Capabilities**:
- List, create, update, delete workflows
- Execute workflows programmatically
- Manage workflow credentials
- Access execution history

**Configuration**: `claude_desktop_config.json`
```json
{
  "n8n": {
    "command": "npx.cmd",
    "args": ["-y", "@leonardsellem/n8n-mcp-server"],
    "env": {
      "N8N_API_URL": "http://localhost:5678/api/v1",
      "N8N_API_KEY": "<your-api-key>"
    }
  }
}
```

**Available Workflows** (in `/n8n-server/`):
- `Doc Chain - Agent.json` - Documentation agent
- `Doc Chain - Distributor.json` - Content distribution
- `Doc Chain - Errors.json` - Error handling
- `Doc Chain - Staleness.json` - Staleness detection
- `Doc Chain - State Reconciliation.json` - State sync
- `Doc Chain - Trigger.json` - Workflow triggers

### 4. GitHub MCP Server

**Purpose**: Full GitHub API integration

**Package**: `@modelcontextprotocol/server-github`

**Capabilities**:
- Repository operations (clone, fork, create)
- Issue and PR management
- GitHub Actions (list, trigger, view logs)
- Codespaces management
- Branch and tag operations
- Code search

**Configuration**: `claude_desktop_config.json`
```json
{
  "github": {
    "command": "npx.cmd",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-pat>"
    }
  }
}
```

**Required PAT Scopes**:
- `repo` - Full repository access
- `workflow` - GitHub Actions
- `codespace` - Codespaces management
- `read:org` - Organization access (if needed)

## Data Flow Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User Query    │────▶│  Claude Desktop │────▶│   MCP Router    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        │                                │                                │
                        ▼                                ▼                                ▼
               ┌────────────────┐              ┌────────────────┐              ┌────────────────┐
               │ Local Actions  │              │  n8n Workflows │              │  GitHub API    │
               │ - File ops     │              │  - Automation  │              │  - Remote ops  │
               │ - Git CLI      │              │  - Scheduling  │              │  - CI/CD       │
               └────────────────┘              └────────────────┘              └────────────────┘
```

## Security Considerations

### Authentication
- **n8n**: API key stored in environment variable
- **GitHub**: Personal Access Token with minimal required scopes
- **Local**: Filesystem permissions via allowed directories

### Best Practices
1. Never commit API keys or tokens to the repository
2. Use `.env` files for local development secrets
3. Rotate credentials periodically
4. Monitor API usage and rate limits

## File Locations

| Item | Path |
|------|------|
| Claude Desktop Config | `%APPDATA%\Claude\claude_desktop_config.json` |
| Extension Settings | `%APPDATA%\Claude\Claude Extensions Settings\` |
| Literature-Review Repo | `C:\Users\jpcol\Documents\Literature-Review\Literature-Review` |
| n8n Server | `./n8n-server/` |
| n8n Data | `~/.n8n/` |

---

*Last Updated: 2024-12-23*
