# Claude ↔ n8n ↔ Antigravity Bridge Architecture

> **Version**: 1.0.0  
> **Last Updated**: 2024-12-29  
> **Status**: ✅ Operational

## Overview

This document describes the bidirectional integration between Claude (AI assistant), n8n (workflow automation), and Antigravity (agent framework), enabling seamless communication and task orchestration across all three systems.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     CLAUDE ↔ N8N ↔ ANTIGRAVITY BRIDGE                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────┐                      ┌─────────────────────────────┐  │
│  │    CLAUDE           │                      │    LOCAL MCP SERVERS        │  │
│  │  (claude.ai or      │  ◄─── MCP Protocol ──►  │                           │  │
│  │   Claude Desktop)   │                      │  ┌─────────────────────┐    │  │
│  └─────────────────────┘                      │  │   curl-bridge       │    │  │
│           │                                   │  │   (curl-mcp.mjs)    │    │  │
│           │ Tool Calls                        │  │                     │    │  │
│           ↓                                   │  │  Tools:             │    │  │
│  ┌─────────────────────────────────────┐     │  │  • curl             │    │  │
│  │         MCP TOOL LAYER              │     │  │  • n8n_status       │    │  │
│  │  curl-bridge | n8n | github         │     │  │  • n8n_health       │    │  │
│  └─────────────────────────────────────┘     │  │  • n8n_submit_task  │    │  │
│           │                                   │  │  • antigravity_send │    │  │
│           │ HTTP via Local Machine           │  │  • antigravity_query│    │  │
│           ↓                                   │  └─────────────────────┘    │  │
│  ┌─────────────────────────────────────┐     │                              │  │
│  │      N8N CLOUD WEBHOOKS             │     │  ┌─────────────────────┐    │  │
│  │  gitlitreview.app.n8n.cloud         │     │  │   n8n MCP           │    │  │
│  │                                     │     │  │   (API access)      │    │  │
│  │  Endpoints:                         │     │  └─────────────────────┘    │  │
│  │  • /distributor-status              │     │                              │  │
│  │  • /distributor-reset               │     │  ┌─────────────────────┐    │  │
│  │  • /task-distributor                │     │  │   github MCP        │    │  │
│  │  • /claude-antigravity-bridge       │     │  │   (repo access)     │    │  │
│  │  • /antigravity-status              │     │  └─────────────────────┘    │  │
│  │  • /state-reconciliation            │     └─────────────────────────────┘  │
│  └─────────────────────────────────────┘                                       │
│           │                                                                     │
│           │ Workflow Processing                                                │
│           ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐      │
│  │                    N8N WORKFLOW ENGINE                               │      │
│  │                                                                      │      │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │      │
│  │   │   Trigger    │─►│ Distributor  │─►│    Agent     │             │      │
│  │   │  (GitHub)    │  │  (Queue)     │  │  (AI Tasks)  │             │      │
│  │   └──────────────┘  └──────────────┘  └──────────────┘             │      │
│  │                                              │                       │      │
│  │   ┌──────────────┐  ┌──────────────┐        ↓                      │      │
│  │   │   Release    │  │  PR Review   │  ┌──────────────┐             │      │
│  │   │  (Tags)      │  │  (PRs)       │  │   Errors     │             │      │
│  │   └──────────────┘  └──────────────┘  │  (Handler)   │             │      │
│  │                                        └──────────────┘             │      │
│  │   ┌──────────────┐  ┌──────────────┐                                │      │
│  │   │  Staleness   │  │   State      │  ┌──────────────────────────┐ │      │
│  │   │  (Weekly)    │  │   Recon      │  │  Claude-Antigravity      │ │      │
│  │   └──────────────┘  │  (Daily)     │  │  Bridge Workflow         │ │      │
│  │                      └──────────────┘  │  (b2hw3xA7DvFn7XCV)      │ │      │
│  │                                        └──────────────────────────┘ │      │
│  └─────────────────────────────────────────────────────────────────────┘      │
│           │                                                                     │
│           │ Future Integration                                                 │
│           ↓                                                                     │
│  ┌─────────────────────────────────────┐                                       │
│  │      ANTIGRAVITY AGENTS             │                                       │
│  │   (Task Processing & Automation)    │                                       │
│  └─────────────────────────────────────┘                                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. curl-bridge MCP Server

**Location**: `n8n-server/curl-mcp.mjs`  
**Purpose**: Bypass Anthropic's network proxy restrictions by routing HTTP requests through the local machine.

#### Why It's Needed
Claude's container environment routes all outbound HTTP through Anthropic's egress proxy, which blocks non-allowlisted domains. The curl-bridge MCP server runs on the user's machine, outside Claude's container, enabling direct access to any HTTP endpoint.

```
Claude Container ─── bash/curl ───► Anthropic Proxy ─── ✗ BLOCKED
Claude Container ─── MCP Protocol ───► Local Machine ─── curl-bridge ───► n8n ✓
```

#### Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `curl` | Generic HTTP requests | url, method, headers, body |
| `n8n_status` | Get Distributor queue status | (none) |
| `n8n_health` | Check workflow health | (none) |
| `n8n_reset` | Reset Distributor state | confirm: boolean |
| `n8n_reconcile` | Trigger State Reconciliation | scan_type: 'quick'\|'deep' |
| `n8n_submit_task` | Submit task to Distributor | document, update_type, description, priority |
| `antigravity_send` | Send message to Antigravity | message_type, payload, callback_expected |
| `antigravity_query` | Query Antigravity status | query_type |

### 2. Claude-Antigravity Bridge Workflow

**Workflow ID**: `b2hw3xA7DvFn7XCV`  
**Status**: ✅ Active  
**Created**: 2024-12-29

#### Webhook Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/claude-antigravity-bridge` | POST | Receive commands, queries, notifications from Claude |
| `/antigravity-status` | POST | Return system status and capabilities |

#### Message Types

```json
{
  "source": "claude",
  "message_type": "command | query | notification | task_request",
  "payload": { ... },
  "correlation_id": "unique-id",
  "callback_expected": false
}
```

#### Message Type Handlers

| Type | Response |
|------|----------|
| `command` | Queued for Antigravity processing |
| `query` | Returns system status and capabilities |
| `notification` | Acknowledged |
| `task_request` | Queued with task_id |

### 3. n8n MCP Server

**Package**: `@leonardsellem/n8n-mcp-server`  
**Purpose**: Direct API access to n8n workflow management

#### Available Operations

- List/get/create/update/delete workflows
- Activate/deactivate workflows
- List/get/delete executions
- Trigger webhooks

### 4. GitHub MCP Server

**Package**: `@modelcontextprotocol/server-github`  
**Purpose**: Repository operations for Literature-Review

## Communication Patterns

### Pattern 1: Synchronous Request/Response

Claude sends a request and receives an immediate response.

```
Claude ──► curl-bridge:n8n_status ──► n8n webhook ──► Response
                                                        │
Claude ◄────────────────────────────────────────────────┘
```

**Example**:
```javascript
// Claude calls:
curl-bridge:n8n_status

// Receives:
{
  "status": "ok",
  "pending_count": 12,
  "in_progress": { "task_id": "task-005", ... },
  "completed_count": 7
}
```

### Pattern 2: Fire-and-Forget Notification

Claude sends a notification without expecting a detailed response.

```
Claude ──► curl-bridge:antigravity_send(notification) ──► n8n ──► "acknowledged"
```

**Example**:
```javascript
// Claude calls:
curl-bridge:antigravity_send({
  message_type: "notification",
  payload: { event: "session_started" }
})

// Receives:
{ "status": "acknowledged" }
```

### Pattern 3: Async Task with Polling (Future)

Claude submits a long-running task and polls for results.

```
Claude ──► submit_task(callback_expected: true) ──► n8n
                                                     │
                                                     ↓
                                              Process async
                                                     │
                                              Store result
                                                     │
Claude ──► poll_result(correlation_id) ◄─────────────┘
```

## Configuration

### Claude Desktop Config

**Location**: `%APPDATA%\Claude\claude_desktop_config.json`

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
        "N8N_API_KEY": "<your-api-key>"
      }
    },
    "github": {
      "command": "npx.cmd",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-pat>"
      }
    }
  }
}
```

### n8n Webhook URLs

| Endpoint | Full URL |
|----------|----------|
| Distributor Status | `https://gitlitreview.app.n8n.cloud/webhook/distributor-status` |
| Distributor Reset | `https://gitlitreview.app.n8n.cloud/webhook/distributor-reset` |
| Task Distributor | `https://gitlitreview.app.n8n.cloud/webhook/task-distributor` |
| Claude Bridge | `https://gitlitreview.app.n8n.cloud/webhook/claude-antigravity-bridge` |
| Antigravity Status | `https://gitlitreview.app.n8n.cloud/webhook/antigravity-status` |
| State Reconciliation | `https://gitlitreview.app.n8n.cloud/webhook/state-reconciliation` |

## Usage Examples

### Check System Health

```javascript
// Using convenience tool
const health = await curl_bridge.n8n_health();

// Response
{
  "overall": "healthy",
  "services": [
    { "name": "Distributor", "status": "healthy", "response_time_ms": 331 }
  ]
}
```

### Query Antigravity Capabilities

```javascript
// Using convenience tool
const caps = await curl_bridge.antigravity_query({ query_type: "capabilities" });

// Response
{
  "antigravity": { "status": "operational", "version": "1.0.0" },
  "bridge": { "status": "connected", "claude_integration": "active" },
  "capabilities": {
    "commands": ["workflow_trigger", "status_check", "task_submit"],
    "queries": ["status", "capabilities", "active_tasks", "history"]
  }
}
```

### Submit a Documentation Task

```javascript
// Using convenience tool
const result = await curl_bridge.n8n_submit_task({
  document: "docs/README.md",
  update_type: "CONTENT_REVIEW",
  description: "Review for accuracy after recent changes",
  priority: 2
});

// Response
{
  "task_id": "claude-task-1767034641156",
  "status": 200,
  "data": { "message": "Workflow was started" }
}
```

### Send Command to Antigravity

```javascript
// Using convenience tool
const result = await curl_bridge.antigravity_send({
  message_type: "command",
  payload: {
    command: "workflow_trigger",
    target: "state-reconciliation"
  }
});

// Response
{
  "status": "accepted",
  "correlation_id": "cmd-1767034500000",
  "message": "Command 'workflow_trigger' received and queued"
}
```

## Workflow Integration

### Doc Chain Workflows

The bridge integrates with the existing Doc Chain workflow system:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| Trigger | GitHub push | Detect documentation changes |
| Distributor | Webhook/Trigger | Queue and dispatch tasks |
| Agent | Distributor | Process individual doc tasks |
| State Reconciliation | Schedule/Manual | Find doc mismatches |
| Staleness | Weekly schedule | Flag outdated docs |
| Errors | Workflow failures | Create GitHub issues |
| Release | GitHub tags | Generate release notes |
| PR Review | GitHub PRs | Review documentation PRs |

### Claude Bridge Flow

```
1. Claude detects need for doc update
   ↓
2. Claude calls n8n_submit_task via curl-bridge
   ↓
3. Task enters Distributor queue
   ↓
4. Agent processes task with AI
   ↓
5. Agent commits to GitHub
   ↓
6. Claude can verify via github MCP
```

## Security Considerations

1. **API Keys**: Store securely in environment variables, never commit
2. **Credential Rotation**: Rotate GitHub PAT and n8n API keys periodically
3. **Network Isolation**: curl-bridge runs locally, credentials stay on user's machine
4. **Webhook Authentication**: n8n webhooks should use authentication in production

## Troubleshooting

### curl-bridge not working
1. Restart Claude Desktop after config changes
2. Verify node.js is installed and in PATH
3. Check curl-mcp.mjs path in config

### n8n webhooks returning errors
1. Verify workflow is active in n8n cloud
2. Check webhook path matches exactly
3. Ensure Content-Type: application/json header

### GitHub operations failing
1. Verify PAT has required scopes (repo, workflow)
2. Check PAT hasn't expired
3. Ensure correct owner/repo names

## Future Enhancements

1. **Async Callbacks**: Store results by correlation_id for polling
2. **Antigravity Integration**: Connect real Antigravity agents
3. **Workflow Automation**: Auto-trigger reconciliation on schedules
4. **Monitoring Dashboard**: Real-time bridge status visualization

---

*Documentation generated: 2024-12-29*
