# Doc Chain - Distributor: Step-Through Validation

> **Workflow ID**: `3lTsmIsQFmzpwLE8`  
> **Version**: DIS_V001  
> **Total Nodes**: 12 active (+ legacy nodes)  
> **Last n8n Update**: 2025-12-24T17:29:41.662Z

---

## Checkout Status

| Field | Value |
|-------|-------|
| **Review Status** | 📋 Ready for Review |
| **Checked Out By** | - |
| **Checkout Time** | - |

---

## Architecture Overview

The Distributor has **4 entry points** (webhooks):

| Entry Point | Path | Purpose |
|-------------|------|---------|
| Receive List | `/task-distributor` | Accept new task lists |
| Receive Callback | `/task-callback` | Task completion callbacks |
| Get Status | `/distributor-status` | Query current state |
| Reset State | `/distributor-reset` | Clear all state |

### Primary Flow (Callback-Based Sequential)
```
Receive List → Queue and Dispatch First → Should Dispatch?
                                               ↓ (yes)
                                         Dispatch to Agent
                                               
Receive Callback → Process Callback and Dispatch Next → Has Next Task?
                                                             ↓ (yes)
                                                       Dispatch to Next
```

### State Management
Uses `$getWorkflowStaticData('global')` with structure:
```json
{
  "pending_tasks": [],
  "in_progress": null,
  "completed": []
}
```

---

## Node-by-Node Validation

### Entry Point 1: Receive List
| ID | `96282d7a-6e69-4eef-8dd8-873d39ecf75d` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Path: `task-distributor` | [ ] | |
| Method: POST | [ ] | |
| Matches Trigger's `Send to Distributor` URL | [ ] | Cross-ref |

**Sign-off**: [ ] ________ Date: ________

---

### Node: Queue and Dispatch First
| ID | `fbd97a45-d78e-4102-8f4d-0b899fd98fe2` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Initializes state if missing | [ ] | |
| Handles `.body` nesting | [ ] | Webhook data nested |
| Stale task recovery (10 min) | [ ] | Clears stuck in_progress |
| Deduplication (1 hour) | [ ] | Skips recent duplicates |
| Queues new tasks | [ ] | With metadata |
| Dispatches if nothing in_progress | [ ] | |
| Returns `should_dispatch` flag | [ ] | For conditional |

**Input**: `{ body: { update_list_id, tasks: [...], trigger } }`

**Output**:
```json
{
  "action": "dispatch|queued|skipped",
  "should_dispatch": true|false,
  "task": {...},
  "list_id": "...",
  "trigger": {...}
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node: Should Dispatch?
| ID | `d9e7a9f0-5b78-4300-8c96-5b2dc0f9ea1c` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `$json.should_dispatch === true` | [ ] | |
| True → Dispatch to Agent | [ ] | |
| False → (ends) | [ ] | Task queued for later |

**Sign-off**: [ ] ________ Date: ________

---

### Node: Dispatch to Agent
| ID | `01b0720c-a9cf-4637-bb88-6ead04077218` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: `https://gitlitreview.app.n8n.cloud/webhook/domain-agent` | [ ] | |
| Method: POST | [ ] | |
| Body params: task, list_id, trigger | [ ] | JSON stringified |
| Matches Agent webhook path | [ ] | Cross-ref AGENT-STEP.md |

**Sign-off**: [ ] ________ Date: ________

---

### Entry Point 2: Receive Callback
| ID | `e01f24b9-f1dc-463f-9bc3-c60ea95b2da6` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Path: `/task-callback` | [ ] | |
| Method: POST | [ ] | |
| Expected payload: `{ task_id, status }` | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node: Process Callback and Dispatch Next
| ID | `6c4d4b50-a6e5-4ea5-bb79-012fb60d8ff1` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Parses callback data | [ ] | Handles .body nesting |
| Marks in_progress complete | [ ] | Sets status, completed_at |
| Moves to completed array | [ ] | Keeps last 20 |
| Clears in_progress | [ ] | Sets to null |
| Pops next from pending | [ ] | |
| Sets new in_progress if found | [ ] | |
| Returns action: dispatch or done | [ ] | |

**Output**:
```json
{
  "action": "dispatch|done",
  "task": {...},
  "pending_remaining": 5
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node: Has Next Task
| ID | `bc730621-b84a-494c-b86c-2eaa83292554` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `action === "dispatch"` | [ ] | |
| True → Dispatch to Next | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node: Dispatch to Next
| ID | `d2c90603-881e-41ca-8eea-7e12f79eedf3` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Same config as Dispatch to Agent | [ ] | |
| URL: domain-agent webhook | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Entry Point 3: Get Status
| ID | `2f57b267-cd22-4cd9-a2af-196d3da7d4cf` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Path: `/distributor-status` | [ ] | |
| Method: GET (default) | [ ] | |
| Response mode: lastNode | [ ] | Returns status JSON |

**Sign-off**: [ ] ________ Date: ________

---

### Node: Return Status
| ID | `26764f24-67fa-4689-a477-953a78b28bb5` |
|----|-------|

| Output Check | Status | Notes |
|--------------|--------|-------|
| Returns `pending_count` | [ ] | |
| Returns `pending_tasks` array | [ ] | task_id, document, queued_at |
| Returns `in_progress` object | [ ] | Or null |
| Returns `completed_count` | [ ] | |
| Returns `recent_completed` (last 5) | [ ] | |
| Includes timestamp | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Entry Point 4: Reset State
| ID | `ec38ed93-7f6b-4620-81f5-5f0d0ae4d80c` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Path: `/distributor-reset` | [ ] | |
| Method: POST | [ ] | |
| Response mode: lastNode | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node: Clear State
| ID | `78b441d0-44c2-47e7-a0e9-b610d7758aa4` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Clears pending_tasks | [ ] | Empty array |
| Clears in_progress | [ ] | null |
| Clears completed | [ ] | Empty array |
| Returns cleared counts | [ ] | For confirmation |

**Sign-off**: [ ] ________ Date: ________

---

## Integration Points

| This Workflow | Connects To | Direction | Status |
|---------------|-------------|-----------|--------|
| Receive List | Trigger → Send to Distributor | ← | [ ] |
| Dispatch to Agent | Agent → Receive Task | → | [ ] |
| Receive Callback | Agent → Send Callback | ← | [ ] |
| Get Status | Testing / State Recon | ← | [ ] |

---

## Test Scenarios

### Scenario 1: Single Task Dispatch
| Step | Expected | Status |
|------|----------|--------|
| POST to /task-distributor with 1 task | Queued and dispatched | [ ] |
| Check /distributor-status | in_progress shows task | [ ] |
| POST callback with completed | in_progress cleared | [ ] |

### Scenario 2: Queue Multiple Tasks
| Step | Expected | Status |
|------|----------|--------|
| POST with 3 tasks | First dispatched, 2 queued | [ ] |
| Check status | pending_count = 2 | [ ] |
| Send callbacks | Tasks process sequentially | [ ] |

### Scenario 3: Deduplication
| Step | Expected | Status |
|------|----------|--------|
| POST task for doc A | Queued | [ ] |
| POST task for doc A again | Skipped (duplicate) | [ ] |

---

## Final Sign-Off

| Reviewer | Date | Status |
|----------|------|--------|
| | | |

**Workflow Approved**: [ ] Yes [ ] No

---

*Document Version: 1.0*  
*Created: 2024-12-24*
