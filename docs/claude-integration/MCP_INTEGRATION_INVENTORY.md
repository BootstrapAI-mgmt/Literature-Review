# MCP Integration Inventory

Comprehensive documentation of the Claude Desktop - n8n - GitHub integration setup.

**Last Updated**: 2025-12-29

## Overview

This document serves as the single source of truth for the Model Context Protocol (MCP) integration that enables Claude Desktop to interact with n8n workflows and GitHub repositories.

## n8n Workflow Inventory

### Active Workflows (8 total)

| Workflow Name | ID | Status | Purpose |
|---------------|-------|--------|----------|
| Doc Chain - Trigger | 85OVKyBKrzQFA1kg | Active | Entry point for documentation chain |
| Doc Chain - Distributor | 9kOmwTpPU5SAPvxE | Active | Distributes tasks to Agent workflows |
| Doc Chain - Agent | LpZ7jA5sxXy4QieO | Active | AI-powered document updates |
| Doc Chain - Staleness | tSWCWLMGOBRluw87 | Active | Detects stale documentation |
| Doc Chain - State Reconciliation | NF3XjMIBrimCTYja | Active | Reconciles documentation_matrix.json |
| Doc Chain - PR Review | CHI7LYvp70EPOmUi | Active | AI-powered PR documentation review |
| Doc Chain - Release | 4Qn2t3z6HgJwEBEH | Active | Automated changelog generation |
| Doc Chain - Errors | btKQeVWvPRe6eqPP | **INACTIVE** | Error handler - creates GitHub issues |

### Webhook Endpoints

Base URL: https://gitlitreview.app.n8n.cloud

| Endpoint | Workflow | Purpose |
|----------|----------|----------|
| /webhook/docs-trigger | Trigger | Start documentation chain |
| /webhook/doc-task | Distributor | Receive task for distribution |
| /webhook/doc-agent | Agent | Process document update task |
| /webhook/task-callback | Agent | Task completion callback |
| /webhook/pr-review | PR Review | GitHub PR webhook receiver |
| /webhook/release-automation | Release | Trigger release creation |

## Claude Desktop MCP Configuration

Location: %APPDATA%\Claude\claude_desktop_config.json (Windows)

### Required MCP Servers

1. **n8n Server** (@leonardsellem/n8n-mcp-server)
   - N8N_API_URL: https://gitlitreview.app.n8n.cloud/api/v1
   - N8N_API_KEY: (secured)

2. **GitHub Server** (@modelcontextprotocol/server-github)
   - GITHUB_PERSONAL_ACCESS_TOKEN: (secured)

3. **Desktop Commander** - File system operations
4. **Filesystem MCP** - Directory access
5. **Mermaid Chart** - Diagram generation

## Repository Workflow Exports

All workflow JSON exports are stored in n8n-server/ directory:
- Doc Chain - Agent.json
- Doc Chain - Distributor.json
- Doc Chain - Errors.json
- Doc Chain - PR Review.json (NEW)
- Doc Chain - Release.json (NEW)
- Doc Chain - Staleness.json
- Doc Chain - State Reconciliation.json
- Doc Chain - Trigger.json

## Security Notes

- Never commit claude_desktop_config.json with real credentials
- Rotate API keys every 90 days
- Workflow JSON exports contain credential IDs but not secrets

## Maintenance

### Sync Status Check
1. Run n8n:list_workflows to see live workflows
2. Compare with n8n-server/*.json files
3. Export any missing workflows

### Activate Error Handler
n8n:activate_workflow(workflowId: "btKQeVWvPRe6eqPP")

---
*Last verified: 2025-12-29*
