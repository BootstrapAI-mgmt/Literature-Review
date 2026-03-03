---
description: Manage n8n server, workflows, and deployment
domain: n8n-management
converts_from: "n8n MCP tools (read operations)"
distilled_date: 2026-03-03
---

## When to Use

Use this skill for n8n workflow management: deploying changes, syncing workflows, verifying environment, and service management. For complex n8n workflow CRUD (create/update/delete), the n8n MCP server remains active.

## Prerequisites

- Python 3.9+
- n8n running locally on port 5678
- `.env` file with `N8N_API_KEY`, `GITHUB_TOKEN`
- npm and git available

## CLI Commands

Run: `.agents/cli/n8n-manage.sh {verify|deploy|sync-export|sync-import|patch|services|health} [args]`

| Command | Purpose |
|---------|---------|
| `n8n-manage.sh verify` | Check all environment prerequisites |
| `n8n-manage.sh deploy` | Deploy changes (git pull + npm install + import) |
| `n8n-manage.sh deploy --restart` | Deploy and restart n8n |
| `n8n-manage.sh sync-export` | Export workflows from n8n to JSON files |
| `n8n-manage.sh sync-import` | Import workflows from JSON files to n8n |
| `n8n-manage.sh patch` | Patch workflows with repository env vars |
| `n8n-manage.sh services start` | Start n8n and MCP services |
| `n8n-manage.sh services stop` | Stop services |
| `n8n-manage.sh health` | Quick n8n health check |

## Underlying Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `verify_env.py` | `n8n-server/scripts/` | Checks npm, git, gh, Python, .env, n8n connectivity |
| `deploy.py` | `n8n-server/scripts/` | Git pull + npm install + workflow import |
| `sync_workflows.py` | `n8n-server/scripts/` | Bidirectional workflow sync (export/import) |
| `sync_workflows_api.py` | `n8n-server/scripts/` | Patches workflows with env vars (REPO_OWNER, etc.) |
| `manage_services.py` | `n8n-server/scripts/` | Service lifecycle management with PID tracking |

## n8n Workflows (10 total)

| Workflow | Status | Notes |
|----------|--------|-------|
| Doc Chain - Distributor | MCP-keep | Stateful task distribution |
| Doc Chain - State Reconciliation | MCP-keep | Complex mismatch scanning |
| Doc Chain - Staleness | MCP-keep | Temporal monitoring |
| Doc Chain - Trigger | MCP-keep | Event-driven |
| Doc Chain - Agent | MCP-keep | Agent coordination |
| Doc Chain - PR Review | Hybrid | Trigger is stateful, review logic documentable |
| Doc Chain - Release | Hybrid | Repeatable release management |
| Doc Chain - Errors | Skill-documented | Error handling patterns |
| Doc Chain - Antigravity MCP Bridge | MCP-keep | External MCP bridge |
| Integration Test | CLI-converted | Simple hello-world test |

## Typical Workflow

```bash
# 1. Verify environment
.agents/cli/n8n-manage.sh verify

# 2. Deploy latest changes
.agents/cli/n8n-manage.sh deploy --restart

# 3. Export current workflows as backup
.agents/cli/n8n-manage.sh sync-export

# 4. Check health
.agents/cli/n8n-manage.sh health
```

## Fallback to MCP

For complex workflow CRUD operations, the n8n MCP server remains active:
```json
"n8n": {
  "url": "http://localhost:5678/mcp"
}
```

## Related Skills

- [Literature Pipeline](literature-pipeline.md) — Pipeline that n8n workflows support
- [Testing Suite](testing-suite.md) — Integration tests including n8n
