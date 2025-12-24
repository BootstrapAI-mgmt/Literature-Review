# Doc Chain Workflow Testing Guide

> **Status:** Phase 3 - Manual Testing  
> **Last Updated:** 2024-12-24

## Overview

This guide provides test payloads for manually validating each Doc Chain workflow. Use curl, Postman, or the n8n webhook tester.

---

## Test 1: Distributor Status Check

**Purpose:** Verify Distributor is responding and state is clean

```bash
curl -X GET https://gitlitreview.app.n8n.cloud/webhook/distributor-status
```

**Expected Response:**
```json
{
  "status": "ok",
  "pending_count": 0,
  "pending_tasks": [],
  "in_progress": null,
  "completed_count": 0,
  "recent_completed": [],
  "timestamp": "2024-12-24T..."
}
```

---

## Test 2: Distributor Reset

**Purpose:** Clear any stale state before testing

```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/distributor-reset
```

**Expected Response:**
```json
{
  "reset": true,
  "cleared_pending": 0,
  "cleared_in_progress": null
}
```

---

## Test 3: Distributor Task Submission

**Purpose:** Submit a test task and verify queuing

```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/task-distributor \
  -H "Content-Type: application/json" \
  -d '{
    "update_list_id": "test-list-001",
    "source": "manual-test",
    "trigger": {
      "type": "manual",
      "message": "Integration test"
    },
    "tasks": [
      {
        "task_id": "test-task-001",
        "document": "docs/test-doc.md",
        "update_type": "STATUS_UPDATE",
        "description": "Test task for validation",
        "priority": 1
      }
    ]
  }'
```

**Expected:** Task dispatched to Agent (check Agent executions)

---

## Test 4: Agent Direct Test

**Purpose:** Test Agent processing without Distributor

```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/domain-agent \
  -H "Content-Type: application/json" \
  -d '{
    "task": "{\"task_id\":\"direct-test-001\",\"document\":\"README.md\",\"update_type\":\"REVIEW_NEEDED\",\"description\":\"Direct agent test\"}",
    "list_id": "direct-test-list",
    "trigger": "{\"type\":\"manual\",\"message\":\"Direct test\"}"
  }'
```

**Note:** Agent expects stringified JSON for task and trigger fields

---

## Test 5: State Reconciliation Manual Trigger

**Purpose:** Trigger daily reconciliation on demand

```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/state-reconciliation
```

**Expected:** Scans task-cards, finds mismatches, generates correction tasks

---

## Test 6: Staleness Review Manual Trigger

**Purpose:** Trigger weekly staleness check on demand

```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/staleness-review
```

**Expected:** Checks domain staleness, may create GitHub issues or update tasks

---

## Test 7: End-to-End Flow (Trigger → Distributor → Agent)

**Purpose:** Simulate a GitHub push triggering the full chain

### Step 1: Send mock GitHub webhook to Trigger
```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/github-doc-trigger \
  -H "Content-Type: application/json" \
  -d '{
    "ref": "refs/heads/main",
    "commits": [
      {
        "id": "test123abc",
        "message": "docs: test documentation update",
        "timestamp": "2024-12-24T12:00:00Z",
        "added": [],
        "modified": ["docs/README.md"],
        "removed": []
      }
    ]
  }'
```

### Step 2: Check Distributor Status
```bash
curl -X GET https://gitlitreview.app.n8n.cloud/webhook/distributor-status
```

### Step 3: Check n8n Executions
Review executions in n8n UI for:
- Trigger workflow
- Distributor workflow
- Agent workflow

---

## Test 8: Error Handler Test

**Purpose:** Verify error workflow catches and reports failures

This requires triggering an error in another workflow. Options:
1. Send malformed data to Agent
2. Temporarily break Agent and observe Error workflow execution

---

## Validation Checklist

| Test | Command | Expected | Result |
|------|---------|----------|--------|
| Distributor Status | GET /distributor-status | JSON response | [ ] |
| Distributor Reset | POST /distributor-reset | Reset confirmation | [ ] |
| Distributor Submit | POST /task-distributor | Task dispatched | [ ] |
| Agent Direct | POST /domain-agent | Document processed | [ ] |
| State Reconciliation | POST /state-reconciliation | Scan completed | [ ] |
| Staleness Review | POST /staleness-review | Review completed | [ ] |
| End-to-End | POST /github-doc-trigger | Full chain executes | [ ] |

---

## Monitoring Executions

After running tests, check executions in n8n:
- URL: https://gitlitreview.app.n8n.cloud
- Navigate to: Executions → Filter by workflow

Or use MCP:
```
n8n:list_executions with limit=10
```

---

## Troubleshooting

### Task Stuck in Distributor
```bash
# Check status
curl -X GET https://gitlitreview.app.n8n.cloud/webhook/distributor-status

# Reset if needed
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/distributor-reset
```

### Agent Not Receiving Tasks
1. Check Distributor status for pending tasks
2. Verify Agent webhook URL is correct
3. Check Agent workflow is active

### Loop Prevention
Commits with these prefixes are filtered by Trigger:
- `[n8n] docs:`
- `[n8n] chore:`

---

*Created: 2024-12-24*
