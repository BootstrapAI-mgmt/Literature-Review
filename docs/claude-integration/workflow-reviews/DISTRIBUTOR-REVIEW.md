# Doc Chain - Distributor Workflow Review

> **Workflow ID:** 3lTsmIsQFmzpwLE8  
> **Status:** ⚠️ Active (Dual Architecture Detected)  
> **Version:** DIST-V001  
> **Last Updated:** 2025-12-23T17:11:33.660Z

---

## Checkout Information

| Field | Value |
|-------|-------|
| **Review Status** | 📋 Ready for Review |
| **Checked Out By** | - |
| **Checkout Time** | - |
| **Sign-off By** | - |
| **Sign-off Time** | - |

---

## ⚠️ CRITICAL: Dual Architecture Issue

This workflow contains **24 nodes** with **TWO distinct processing architectures**:

### OLD Architecture (Nodes 2-12, 14, 22)
- Queue-based processing
- Uses `Wait` node with 10-minute timeout
- Dependency resolution before dispatch
- May have orphaned/disconnected nodes

### NEW Architecture (Nodes 1, 15-21, 23-24)
- Callback-based sequential dispatch
- Deduplication logic (pending + recently completed)
- Stale task recovery (>10 min in_progress cleared)
- Appears to be the active architecture

**RECOMMENDATION:** Audit which architecture is actually connected and remove orphaned nodes.

---

## Workflow Purpose

Receives task lists from Trigger/StateRecon/Staleness workflows, manages task queue with deduplication, dispatches tasks sequentially to the Agent, handles callbacks, and tracks completion status.

---

## Webhook Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/webhook/task-distributor` | POST | Receive new task lists |
| `/webhook/task-callback` | POST | Receive task completion callbacks |
| `/webhook/distributor-reset` | POST | Clear all state |
| `/webhook/distributor-status` | GET | Return current status |

---

## Node-by-Node Validation

### NEW ARCHITECTURE NODES

#### Node 1: Receive List (Webhook)
| Check | Status | Notes |
|-------|--------|-------|
| Path correct | [ ] | `task-distributor` |
| Method: POST | [ ] | |
| Response mode | [ ] | `lastNode` |

---

#### Node 15: Queue and Dispatch First
| Check | Status | Notes |
|-------|--------|-------|
| Loads existing state | [ ] | `$getWorkflowStaticData('global')` |
| Deduplication logic | [ ] | Filters pending + recent completed |
| First task extraction | [ ] | |
| State persistence | [ ] | |

**State Structure:**
```javascript
{
  pending_tasks: [],      // Queue of tasks waiting
  in_progress: null,      // Currently executing task
  completed: [],          // Recently completed (within 1 hour)
  last_trigger: {}        // Last trigger context
}
```

**Deduplication Logic:**
```javascript
// Skip if already pending
if (state.pending_tasks.some(p => p.document === task.document)) skip;
// Skip if completed within 1 hour
if (state.completed.some(c => c.document === task.document && 
    (Date.now() - c.completed_at) < 3600000)) skip;
```

---

#### Node 16: Should Dispatch? (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `firstTask !== null && !in_progress` |
| True → Dispatch to Agent | [ ] | |
| False → End (queue updated) | [ ] | |

---

#### Node 17: Dispatch to Agent
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | `/webhook/domain-agent` |
| Method: POST | [ ] | |
| Stringifies task/trigger | [ ] | JSON.stringify for nested objects |

**Request Body:**
```json
{
  "task": "{...stringified...}",
  "trigger": "{...stringified...}",
  "list_id": "ul-..."
}
```

---

#### Node 18: Receive Callback (Webhook)
| Check | Status | Notes |
|-------|--------|-------|
| Path correct | [ ] | `task-callback` |
| Method: POST | [ ] | |

**Expected Callback:**
```json
{
  "task_id": "task-001",
  "status": "completed",
  "result": { "summary": "..." }
}
```

---

#### Node 19: Process Callback and Dispatch Next
| Check | Status | Notes |
|-------|--------|-------|
| Clears in_progress | [ ] | |
| Adds to completed[] | [ ] | With timestamp |
| Extracts next task | [ ] | From pending_tasks |
| Stale recovery | [ ] | Clears >10 min in_progress |

**Stale Task Recovery:**
```javascript
if (state.in_progress && 
    (Date.now() - state.in_progress.started_at) > 600000) {
  state.in_progress = null;  // Clear stale task
}
```

---

#### Node 20: Has Next Task (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `nextTask !== null` |
| True → Dispatch to Next | [ ] | |
| False → End (queue empty) | [ ] | |

---

#### Node 21: Dispatch to Next
| Check | Status | Notes |
|-------|--------|-------|
| Same as Node 17 | [ ] | |
| Updates in_progress | [ ] | |

---

#### Node 23: Reset State (Webhook)
| Check | Status | Notes |
|-------|--------|-------|
| Path correct | [ ] | `distributor-reset` |
| Clears all state | [ ] | |

---

#### Node 24: Get Status (Webhook)
| Check | Status | Notes |
|-------|--------|-------|
| Path correct | [ ] | `distributor-status` |
| Method: GET | [ ] | |
| Returns counts | [ ] | pending/in_progress/completed |

---

### OLD ARCHITECTURE NODES (May be orphaned)

#### Node 2: Load State
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 3: Add To Queue
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 4: Should Process (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 5: Pop Next List
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 6: Get Runnable Tasks
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 7: Has Runnable (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 8: Prepare Agent Payload
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 9: Dispatch to Agent-old
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 10: Wait for Callback
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |
| Timeout: 10 min | [ ] | |

#### Node 11: Update Task Status
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 12: All Done (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 14: Finalize List
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

#### Node 22: More Queued (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Connected? | [ ] | **VERIFY CONNECTION** |

---

## Connection Map

### NEW Architecture Connections
| From | To | Connected? |
|------|-----|-----------|
| Receive List | Queue and Dispatch First | [ ] |
| Queue and Dispatch First | Should Dispatch? | [ ] |
| Should Dispatch? (true) | Dispatch to Agent | [ ] |
| Receive Callback | Process Callback and Dispatch Next | [ ] |
| Process Callback... | Has Next Task | [ ] |
| Has Next Task (true) | Dispatch to Next | [ ] |
| Reset State | (terminal) | [ ] |
| Get Status | (terminal) | [ ] |

### OLD Architecture Connections
**ACTION REQUIRED:** Verify if these are connected or orphaned.

---

## State Management

### Global Static Data
```javascript
const state = $getWorkflowStaticData('global');
```

### State Fields
| Field | Type | Purpose |
|-------|------|---------|
| `pending_tasks` | Array | Tasks waiting to be processed |
| `in_progress` | Object/null | Currently executing task with `started_at` |
| `completed` | Array | Tasks completed within last hour |
| `last_trigger` | Object | Context from triggering workflow |

---

## Issues Found

| # | Severity | Description | Recommendation |
|---|----------|-------------|----------------|
| 1 | 🔴 HIGH | Dual architecture - 24 nodes with 2 patterns | Audit connections, remove orphaned nodes |
| 2 | 🟡 MED | Old Wait node (10 min timeout) may cause issues | Ensure old architecture is disconnected |
| 3 | 🟢 LOW | Completed array cleanup not visible | Verify 1-hour cleanup happens |

---

## Architecture Cleanup Recommendations

1. **Export current workflow JSON** for backup
2. **Map all node connections** visually in n8n UI
3. **Identify disconnected nodes** (no incoming connections)
4. **Remove orphaned OLD architecture nodes** if not connected
5. **Test after cleanup** with manual webhook trigger

---

## Sign-off

- [ ] New architecture nodes validated
- [ ] Old architecture nodes audited
- [ ] Orphaned nodes identified
- [ ] Connection map verified
- [ ] State management confirmed

**Reviewer:** ________________________  
**Date:** ________________________  
**Signature:** ________________________
