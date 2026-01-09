# Antigravity-n8n-GitHub Integration Architecture

## Overview

This document comprehensively covers the current bridge/architecture capabilities connecting Antigravity AI agents, n8n Cloud, and GitHub.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ANTIGRAVITY AGENT                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         AVAILABLE TOOLS                                  ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌──────────────┐││
│  │  │ mcp_client.py │ │ bridge.py     │ │ payloader.py  │ │ gh CLI       │││
│  │  │ (Webhook)     │ │ (n8n API)     │ │ (Test Webhook)│ │ (GitHub API) │││
│  │  │ ✅ WORKING    │ │ ⚠️ KEY ISSUES │ │ ✅ WORKING    │ │ ✅ WORKING   │││
│  │  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └──────┬───────┘││
│  └──────────┼─────────────────┼─────────────────┼─────────────────┼────────┘│
└─────────────┼─────────────────┼─────────────────┼─────────────────┼─────────┘
              │                 │                 │                 │
              ▼                 ▼                 ▼                 ▼
     ┌─────────────────────────────────────┐              ┌─────────────────┐
     │           n8n CLOUD                  │              │   GITHUB API    │
     │      gitlitreview.app.n8n.cloud      │              │   (gh CLI)      │
     │                                      │              │                 │
     │  ┌────────────────────────────────┐ │              │  • Create PRs   │
     │  │ WEBHOOKS (Public, No Auth)     │ │              │  • Commit/Push  │
     │  │ ✅ /github-doc-trigger         │ │              │  • Issue CRUD   │
     │  │ ✅ /task-distributor           │ │              │  • Repo Admin   │
     │  │ ✅ /pr-review                  │ │              │                 │
     │  │ ✅ /staleness-review           │ │              └─────────────────┘
     │  │ ✅ /antigravity-bridge (MCP)   │ │
     │  │ ⚠️ /state-reconciliation (slow)│ │
     │  │ ❌ /distributor-status (none)  │ │
     │  │ ❌ /error-handler (none)       │ │
     │  └────────────────────────────────┘ │
     │                                      │
     │  ┌────────────────────────────────┐ │
     │  │ API (Requires N8N_API_KEY)     │ │
     │  │ ⚠️ Key instability issues      │ │
     │  └────────────────────────────────┘ │
     └─────────────────────────────────────┘
```

---

## Integration Components

### 1. MCP Client (`mcp_client.py`) ✅ RECOMMENDED

**Status:** Fully operational, no authentication issues

**Capabilities:**
| Action | Description | Status |
|--------|-------------|--------|
| `health` | Check n8n Cloud status | ✅ Working |
| `list_workflows` | List all 11 workflows | ✅ Working |
| `get_workflow` | Get workflow info by ID | ✅ Working |
| `get_executions` | Link to executions UI | ✅ Working |
| `trigger_workflow` | Info for github-doc-trigger | ✅ Working |
| `help` | List all available tools | ✅ Working |

**Usage:**
```bash
python n8n-server/mcp_client.py health
python n8n-server/mcp_client.py list_workflows
python n8n-server/mcp_client.py help
```

**Limitations:**
- Returns cached workflow list (not live API query)
- Cannot modify workflows (read-only)
- No execution history details (links to UI only)

---

### 2. Payloader (`payloader.py`) ✅ WORKING

**Status:** Fully operational for webhook triggering

**Capabilities:**
| Method | Description | Status |
|--------|-------------|--------|
| `send_to_webhook()` | Send to any webhook | ✅ Working |
| `trigger_github_push()` | Simulate push event | ✅ Working |
| `trigger_pr_event()` | Simulate PR event | ✅ Working |
| `check_distributor_status()` | Check queue status | ❌ 404 |
| `reset_distributor()` | Reset queue | ❌ Not implemented |
| `wait_for_execution()` | Poll for completion | ⚠️ Depends on status endpoint |

**Working Webhooks:**
- `/github-doc-trigger` - Trigger doc chain
- `/task-distributor` - Send tasks directly
- `/pr-review` - Trigger PR review workflow
- `/staleness-review` - Trigger staleness check
- `/antigravity-bridge` - MCP Bridge

**Non-Working Webhooks:**
- `/distributor-status` - Not configured (no status endpoint)
- `/error-handler` - Uses internal errorTrigger
- `/state-reconciliation` - Slow (AI analysis, may timeout)

---

### 3. API Bridge (`bridge.py`) ⚠️ UNSTABLE

**Status:** Full functionality but authentication unstable

**Capabilities:**
| Method | Description | Status |
|--------|-------------|--------|
| `health()` | Check API connectivity | ⚠️ Key issues |
| `list_workflows()` | Get all workflows | ⚠️ Key issues |
| `get_workflow()` | Get workflow details | ⚠️ Key issues |
| `activate_workflow()` | Activate workflow | ⚠️ Key issues |
| `deactivate_workflow()` | Deactivate workflow | ⚠️ Key issues |
| `execute_workflow()` | Execute workflow | ⚠️ Key issues |
| `list_executions()` | Get execution history | ⚠️ Key issues |
| `get_execution()` | Get execution details | ⚠️ Key issues |
| `create_workflow()` | Create new workflow | ⚠️ Key issues |
| `update_workflow()` | Update workflow | ⚠️ Key issues |
| `delete_workflow()` | Delete workflow | ⚠️ Key issues |

**Issue:** n8n API key (`N8N_API_KEY`) frequently becomes unauthorized.

**Potential Fix:** Generate "no expiration" API key in n8n Cloud Settings.

---

### 4. GitHub CLI (`gh`) ✅ WORKING

**Status:** Fully operational via GITHUB_TOKEN

**Capabilities:**
- Create/manage PRs
- Create/manage Issues
- Commit and push changes
- Repository administration
- View/manage workflows (GitHub Actions)

---

## n8n Workflows (10 total)

| Workflow | Webhook | Purpose | Status |
|----------|---------|---------|--------|
| Doc Chain - Trigger | `/github-doc-trigger` | Entry point for push events | ✅ Active |
| Doc Chain - Distributor | `/task-distributor` | Routes tasks to agents | ✅ Active |
| Doc Chain - Agent | Internal | Executes documentation updates | ✅ Active |
| Doc Chain - PR Review | `/pr-review` | Reviews PRs for doc impact | ✅ Active |
| Doc Chain - Release | Internal | Handles release documentation | ✅ Active |
| Doc Chain - Staleness | `/staleness-review` | Checks for stale docs | ✅ Active |
| Doc Chain - State Reconciliation | `/state-reconciliation` | Deep AI analysis | ⚠️ Slow |
| Doc Chain - Errors | Internal (errorTrigger) | Handles workflow errors | ✅ Active |
| Doc Chain - Antigravity MCP Bridge | `/antigravity-bridge` | AI agent access | ✅ Active |
| Integration Test - Hello World | Internal | Test workflow | ✅ Active |

---

## What We CAN Do ✅

### Via Webhooks (Recommended)
1. **Trigger documentation chains** - Push events, PR reviews
2. **Query workflow status** - Via MCP Bridge
3. **List all workflows** - Via MCP Bridge
4. **Execute staleness checks** - Direct webhook call
5. **Send custom payloads** - Any workflow with webhook trigger

### Via GitHub CLI
1. **Full repository management** - Commits, PRs, Issues
2. **Trigger GitHub Actions** - Workflow dispatch
3. **Manage repository settings** - Branches, protections

---

## What We CANNOT Do ❌

### Due to Missing Endpoints
1. **Check distributor queue status** - No `/distributor-status` endpoint
2. **Trigger error handler directly** - Uses internal errorTrigger
3. **Wait for workflow completion** - No polling endpoint

### Due to API Key Issues
1. **Activate/deactivate workflows** - Requires stable API key
2. **View execution history** - Requires stable API key
3. **Modify workflow definitions** - Requires stable API key
4. **Create new workflows programmatically** - Requires stable API key

### Architectural Limitations
1. **Real-time workflow monitoring** - n8n doesn't expose WebSocket
2. **Cross-workflow state access** - Each workflow is isolated
3. **Programmatic credential management** - Must use n8n UI

---

## Recommendations

### Short-term (No Changes to n8n)
1. ✅ Use **MCP Bridge** for all status queries
2. ✅ Use **webhooks** for triggering workflows
3. ✅ Use **gh CLI** for all GitHub operations
4. ⚠️ Avoid API-dependent operations

### Medium-term (Requires n8n Changes)
1. Add `/distributor-status` webhook endpoint
2. Generate "no expiration" API key
3. Add `/workflow-status` for execution polling

### Long-term (Architecture Improvements)
1. Implement callback webhooks for completion notifications
2. Add execution tracking via GitHub Issues
3. Consider Zapier/Make for additional integrations

---

## Quick Reference

```bash
# Check n8n status
python n8n-server/mcp_client.py health

# List workflows
python n8n-server/mcp_client.py list_workflows

# Trigger push event
python -c "from tests.tier2.payloader import Payloader; p=Payloader(); print(p.trigger_github_push(['docs/test.md']))"

# Create GitHub PR
gh pr create --title "Title" --body "Description"
```
