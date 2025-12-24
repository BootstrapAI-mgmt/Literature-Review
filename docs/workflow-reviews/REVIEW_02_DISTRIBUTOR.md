# Workflow Review: Doc Chain - Distributor

**Workflow ID:** `3lTsmIsQFmzpwLE8`
**Version:** DIST-V001
**Updated:** 2025-12-23T17:11:33.660Z
**Nodes:** 24

---

## ⚠️ CRITICAL: Dual Architecture Present

This workflow contains **TWO ARCHITECTURES** that may conflict:

| Architecture | Nodes | Status | Pattern |
|--------------|-------|--------|---------|
| OLD | 2-12, 14, 22 | ❓ Unknown | Queue + Wait node |
| NEW | 1, 15-21, 23-24 | ❓ Unknown | Direct dispatch + dedup |

**PRIORITY:** Determine which architecture is actually ACTIVE and CONNECTED.

---

## Checkout Status

| Field | Value |
|-------|-------|
| Reviewer | ⬜ Unclaimed |
| Checkout Time | - |
| Status | 🟢 Available |
| Sign-off | ⬜ Pending |

---

## Purpose

Central task dispatcher that receives task lists from Trigger/Reconciliation/Staleness workflows, manages state, deduplicates, and dispatches to Agent workflow one task at a time.

---

## Webhook Endpoints

| Path | Method | Purpose | Node |
|------|--------|---------|------|
| `/task-distributor` | POST | Receive task lists | Receive List |
| `/task-callback` | POST | Agent completions | Receive Callback |
| `/distributor-reset` | POST | Clear all state | Reset State |
| `/distributor-status` | GET | Status check | Get Status |

---

## NEW Architecture (Nodes 1, 15-21, 23-24)

### Node 1: Receive List
**Type:** `n8n-nodes-base.webhook`
**Path:** `/task-distributor`

| Check | Status | Notes |
|-------|--------|-------|
| Endpoint active | ⬜ | POST method |
| Connects to Queue and Dispatch | ⬜ | Node 15 |

---

### Node 15: Queue and Dispatch First
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Initializes state | ⬜ | pending_tasks, in_progress, completed |
| Deduplication logic | ⬜ | Skips recent/pending |
| Dispatches first task | ⬜ | Sets in_progress |

**Deduplication Rules:**
- ⬜ Skip if doc already in pending_tasks
- ⬜ Skip if doc completed within 1 hour
- ⬜ Clear stale tasks (>10 min in_progress)

---

### Node 16: Should Dispatch?
**Type:** `n8n-nodes-base.if`

| Check | Status | Notes |
|-------|--------|-------|
| True → Dispatch to Agent | ⬜ | Has runnable task |
| False → End | ⬜ | No tasks to run |

---

### Node 17: Dispatch to Agent
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `https://gitlitreview.app.n8n.cloud/webhook/domain-agent`

| Check | Status | Notes |
|-------|--------|-------|
| URL matches Agent webhook | ⬜ | - |
| Payload includes task + trigger | ⬜ | JSON body |

---

### Node 18: Receive Callback
**Type:** `n8n-nodes-base.webhook`
**Path:** `/task-callback`

| Check | Status | Notes |
|-------|--------|-------|
| Accepts completion callbacks | ⬜ | POST method |
| Returns webhook response | ⬜ | - |

---

### Node 19: Process Callback and Dispatch Next
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Marks task complete | ⬜ | Moves to completed[] |
| Clears in_progress | ⬜ | - |
| Gets next task | ⬜ | From pending_tasks |

---

### Node 20: Has Next Task
**Type:** `n8n-nodes-base.if`

| Check | Status | Notes |
|-------|--------|-------|
| True → Dispatch Next | ⬜ | More pending |
| False → End | ⬜ | Queue empty |

---

### Node 21: Dispatch to Next
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `https://gitlitreview.app.n8n.cloud/webhook/domain-agent`

| Check | Status | Notes |
|-------|--------|-------|
| Same as Node 17 | ⬜ | - |

---

### Node 23: Reset State
**Type:** `n8n-nodes-base.webhook`
**Path:** `/distributor-reset`

| Check | Status | Notes |
|-------|--------|-------|
| Clears all state | ⬜ | POST method |
| Returns confirmation | ⬜ | - |

---

### Node 24: Get Status
**Type:** `n8n-nodes-base.webhook`
**Path:** `/distributor-status`

| Check | Status | Notes |
|-------|--------|-------|
| Returns counts | ⬜ | GET method |
| Shows pending/in_progress/completed | ⬜ | - |

---

## OLD Architecture (Nodes 2-12, 14, 22) - DEPRECATED?

### Node 2: Load State
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | Verify input source |

### Node 3: Add To Queue
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | From Load State? |

### Node 4: Should Process
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | Decision node |

### Node 5: Pop Next List
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | Queue pop logic |

### Node 6: Get Runnable Tasks
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | Dependency resolution |

### Node 7: Has Runnable
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | Decision node |

### Node 8: Prepare Agent Payload
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | Payload formatting |

### Node 9: Dispatch to Agent-old
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | HTTP request |

### Node 10: Wait for Callback
| Check | Status | Notes |
|-------|--------|-------|
| 10-minute timeout | ⬜ | Wait node |

### Node 11: Update Task Status
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | After callback |

### Node 12: All Done
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | Check completion |

### Node 14: Finalize List
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | List complete |

### Node 22: More Queued
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | ⬜ | Loop check |

---

## Architecture Decision Required

After tracing connections:

| Question | Answer |
|----------|--------|
| Which webhook triggers the primary flow? | ⬜ |
| Is OLD architecture orphaned? | ⬜ |
| Is NEW architecture complete? | ⬜ |
| Should OLD nodes be removed? | ⬜ |

---

## State Management

**Static Data Location:** Workflow static data

**State Schema:**
```json
{
  "pending_tasks": [
    { "task_id": "...", "document": "...", "queued_at": "..." }
  ],
  "in_progress": { "task_id": "...", "started_at": "..." } | null,
  "completed": [
    { "task_id": "...", "document": "...", "completed_at": "..." }
  ]
}
```

---

## Test Scenarios

### Test 1: Submit Task List
```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/task-distributor \
  -H "Content-Type: application/json" \
  -d '{
    "update_list_id": "ul-test-001",
    "source": "manual-test",
    "tasks": [
      {"task_id":"t1","document":"docs/test.md","description":"Test update"}
    ]
  }'
```

### Test 2: Check Status
```bash
curl https://gitlitreview.app.n8n.cloud/webhook/distributor-status
```

### Test 3: Reset State
```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/distributor-reset
```

### Test 4: Deduplication
Submit same document twice within 1 hour → Second should be skipped

---

## Sign-off

| Item | Verified | Date | Reviewer |
|------|----------|------|----------|
| Architecture identified | ⬜ | - | - |
| All active nodes reviewed | ⬜ | - | - |
| State management verified | ⬜ | - | - |
| Deduplication tested | ⬜ | - | - |
| Callback flow tested | ⬜ | - | - |

**Final Sign-off:** ⬜ Pending
