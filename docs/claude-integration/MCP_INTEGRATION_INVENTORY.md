# MCP Integration Inventory

Comprehensive documentation of the Claude Desktop - n8n - GitHub - Antigravity integration setup.

**Last Updated**: 2024-12-29  
**Version**: 2.0.0

## Overview

This document serves as the single source of truth for the Model Context Protocol (MCP) integration that enables Claude Desktop/claude.ai to interact with n8n workflows, GitHub repositories, and Antigravity agents.

---

## MCP Server Inventory

### 1. curl-bridge (Custom)

**Location**: `n8n-server/curl-mcp.mjs`  
**Purpose**: Bypass Anthropic's network proxy to access n8n webhooks directly  
**Status**: ✅ Active

#### Tools

| Tool | Description |
|------|-------------|
| `curl` | Generic HTTP requests |
| `n8n_status` | Get Distributor queue status |
| `n8n_health` | Check workflow health |
| `n8n_reset` | Reset Distributor state |
| `n8n_reconcile` | Trigger State Reconciliation |
| `n8n_submit_task` | Submit task to Distributor |
| `antigravity_send` | Send message to Antigravity bridge |
| `antigravity_query` | Query Antigravity system status |

### 2. n8n Server

**Package**: `@leonardsellem/n8n-mcp-server`  
**Purpose**: Direct API access to n8n workflow management  
**Status**: ✅ Active

#### Configuration
- `N8N_API_URL`: https://gitlitreview.app.n8n.cloud/api/v1
- `N8N_API_KEY`: (secured JWT token)

#### Tools
- `list_workflows`, `get_workflow`, `create_workflow`, `update_workflow`
- `activate_workflow`, `deactivate_workflow`, `delete_workflow`
- `list_executions`, `get_execution`, `delete_execution`
- `run_webhook`

### 3. GitHub Server

**Package**: `@modelcontextprotocol/server-github`  
**Purpose**: Repository operations for Literature-Review  
**Status**: ✅ Active

#### Configuration
- `GITHUB_PERSONAL_ACCESS_TOKEN`: (secured PAT)

#### Tools
- Repository: `get_file_contents`, `push_files`, `create_or_update_file`
- Issues: `list_issues`, `create_issue`, `update_issue`, `add_issue_comment`
- PRs: `list_pull_requests`, `create_pull_request`, `get_pull_request`
- Commits: `list_commits`, `create_branch`

### 4. Desktop Commander

**Purpose**: Local file system operations and command execution  
**Status**: ✅ Active

### 5. Filesystem MCP

**Purpose**: Directory access with permissions  
**Status**: ✅ Active

### 6. Mermaid Chart

**Purpose**: Diagram generation and visualization  
**Status**: ✅ Active

---

## n8n Workflow Inventory

### Active Workflows (11 total)

| Workflow Name | ID | Status | Purpose |
|---------------|-------|--------|----------|
| Doc Chain - Trigger | 85OVKyBKrzQFA1kg | ✅ Active | GitHub push detection |
| Doc Chain - Distributor | 9kOmwTpPU5SAPvxE | ✅ Active | Task queue management |
| Doc Chain - Agent | LpZ7jA5sxXy4QieO | ✅ Active | AI-powered document updates |
| Doc Chain - Staleness | tSWCWLMGOBRluw87 | ✅ Active | Detect stale documentation |
| Doc Chain - State Reconciliation | NF3XjMIBrimCTYja | ✅ Active | Documentation matrix sync |
| Doc Chain - PR Review | CHI7LYvp70EPOmUi | ✅ Active | AI PR review |
| Doc Chain - Release | 4Qn2t3z6HgJwEBEH | ✅ Active | Changelog generation |
| Doc Chain - Errors | btKQeVWvPRe6eqPP | ⚠️ Inactive | Error handler |
| Doc Chain - Claude Bridge | PARiTxsX57k0ny6P | ⚠️ Inactive | Legacy bridge (v1) |
| Doc Chain - Claude Bridge v2 | r6GoavRSv9pjatqE | ✅ Active | Bridge variant |
| Doc Chain - Claude Antigravity Bridge | b2hw3xA7DvFn7XCV | ✅ Active | **Main bridge** |

### Webhook Endpoints

**Base URL**: `https://gitlitreview.app.n8n.cloud/webhook`

| Endpoint | Workflow | Purpose |
|----------|----------|---------|
| `/distributor-status` | Distributor | Queue status (GET/POST) |
| `/distributor-reset` | Distributor | Reset queue state |
| `/task-distributor` | Distributor | Submit new tasks |
| `/domain-agent` | Agent | Process doc task |
| `/agent-callback` | Distributor | Task completion |
| `/state-reconciliation` | State Recon | Trigger sync |
| `/claude-antigravity-bridge` | Bridge | Claude → Antigravity |
| `/antigravity-status` | Bridge | System status |

---

## Claude Desktop Configuration

**Location**: `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "curl-bridge": {
      "command": "node",
      "args": ["C:\\path\\to\\n8n-server\\curl-mcp.mjs"]
    },
    "n8n": {
      "command": "npx.cmd",
      "args": ["-y", "@leonardsellem/n8n-mcp-server"],
      "env": {
        "N8N_API_URL": "https://gitlitreview.app.n8n.cloud/api/v1",
        "N8N_API_KEY": "<your-n8n-api-key>"
      }
    },
    "n8n-local": {
      "command": "npx.cmd",
      "args": ["-y", "@leonardsellem/n8n-mcp-server"],
      "env": {
        "N8N_API_URL": "http://localhost:5678/api/v1",
        "N8N_API_KEY": "<your-local-api-key>"
      }
    },
    "github": {
      "command": "npx.cmd",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-github-pat>"
      }
    }
  }
}
```

---

## Repository Structure

### Workflow Exports

All workflow JSON exports are stored in `n8n-server/`:

| File | Workflow | Version |
|------|----------|---------|
| `Doc Chain - Trigger.json` | GitHub Trigger | Latest |
| `Doc Chain - Distributor.json` | Task Queue | Latest |
| `Doc Chain - Agent.json` | AI Processor | Latest |
| `Doc Chain - Errors.json` | Error Handler | Latest |
| `Doc Chain - Staleness.json` | Staleness Check | Latest |
| `Doc Chain - State Reconciliation.json` | Matrix Sync | Latest |
| `Doc Chain - PR Review.json` | PR Review | Latest |
| `Doc Chain - Release.json` | Release Notes | Latest |

### Bridge Components

| File | Purpose |
|------|---------|
| `curl-mcp.mjs` | MCP server for HTTP bridging |
| `bridge.py` | CLI tool for n8n management |
| `package.json` | Dependencies |

---

## Integration Test Commands

### Quick Health Check
```javascript
curl-bridge:n8n_health()
// Returns overall system health
```

### Get Queue Status
```javascript
curl-bridge:n8n_status()
// Returns pending, in-progress, completed tasks
```

### Query Capabilities
```javascript
curl-bridge:antigravity_query({ query_type: "capabilities" })
// Returns available commands and queries
```

### Submit Task
```javascript
curl-bridge:n8n_submit_task({
  document: "docs/README.md",
  update_type: "CONTENT_REVIEW",
  description: "Review accuracy",
  priority: 2
})
```

---

## Security Notes

1. **Never commit** `claude_desktop_config.json` with real credentials
2. **Rotate API keys** every 90 days
3. **Workflow JSON exports** contain credential IDs but not secrets
4. **GitHub PAT** requires scopes: `repo`, `workflow`

---

## Maintenance Checklist

### Weekly
- [ ] Check workflow execution logs for errors
- [ ] Verify Distributor queue is not stuck
- [ ] Review GitHub issues created by Error workflow

### Monthly
- [ ] Export updated workflow JSONs to repo
- [ ] Verify all credentials are valid
- [ ] Check for MCP server package updates

### Quarterly
- [ ] Rotate GitHub PAT
- [ ] Rotate n8n API key
- [ ] Review and prune old executions

---

## Related Documentation

- [BRIDGE-ARCHITECTURE.md](./BRIDGE-ARCHITECTURE.md) - Detailed architecture
- [PROGRESS.md](./PROGRESS.md) - Session progress tracking
- [CHECKPOINT-SYSTEM.md](./CHECKPOINT-SYSTEM.md) - Checkpoint protocol

---

*Last verified: 2024-12-29*
