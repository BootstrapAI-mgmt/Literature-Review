# Workflow Review: Doc Chain - Errors

**Workflow ID:** `gplUON3gG47QIMpi`
**Version:** Err-V001
**Updated:** 2025-12-23T17:11:54.795Z
**Nodes:** 5

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

Global error handler that catches errors from other Doc Chain workflows, extracts task_id if possible, and sends failure callbacks to the Distributor.

---

## Node-by-Node Review

### Node 1: Catch Errors
**Type:** `n8n-nodes-base.errorTrigger`

| Check | Status | Notes |
|-------|--------|-------|
| Error trigger type | ⬜ | Catches all workflow errors |
| Configured in other workflows | ⬜ | Must be set as error handler |

**Error Structure Received:**
```json
{
  "workflow": { "name": "..." },
  "execution": {
    "lastNodeExecuted": "...",
    "error": {
      "message": "...",
      "context": {
        "request": {
          "body": { "task_id": "..." },
          "uri": "..."
        }
      }
    },
    "data": { "task_id": "..." }
  }
}
```

---

### Node 2: Log Error
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Console.error called | ⬜ | Logs full error |
| task_id extraction | ⬜ | 3 fallback paths |
| Clean output | ⬜ | Standardized structure |

**task_id Extraction Paths:**
1. `error.execution.data.task_id` - Direct from execution data
2. `error.execution.error.context.request.body.task_id` - From HTTP request body
3. Parse from URL: `/webhook/task-done-{task_id}`

**Output:**
```json
{
  "workflow": "Doc Chain - Agent",
  "node": "Commit to GitHub",
  "message": "API rate limit exceeded",
  "timestamp": "2025-12-24T...",
  "task_id": "task-001" | null
}
```

---

### Node 3: Has Task ID
**Type:** `n8n-nodes-base.if`

| Check | Status | Notes |
|-------|--------|-------|
| True → Send Failure Callback | ⬜ | Has task_id |
| False → End | ⬜ | No task_id to report |

---

### Node 4: Send Failure Callback
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `https://gitlitreview.app.n8n.cloud/webhook/task-done-{task_id}`

| Check | Status | Notes |
|-------|--------|-------|
| URL construction | ⬜ | Dynamic task_id |
| POST method | ⬜ | - |
| Payload format | ⬜ | status: failed, error message |
| onError: continueRegularOutput | ⬜ | Doesn't fail if callback fails |

**⚠️ Potential Issue:**
This sends to `/webhook/task-done-{task_id}` but Distributor receives callbacks at `/task-callback`. Need to verify compatibility.

**Payload:**
```json
{
  "task_id": "task-001",
  "status": "failed",
  "result": {
    "error": "API rate limit exceeded"
  }
}
```

---

### Node 5: Log Callback Result
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Success logging | ⬜ | status: notified |
| 404 handling | ⬜ | status: expired (Wait node timeout) |

**Logic:**
```javascript
const success = !result.error && !result.errorMessage;
const status = success ? 'notified' : 'expired';
```

---

## Integration Points

| Target | Method | Purpose |
|--------|--------|---------|
| Distributor | POST | Failure callback |

---

## Configuration in Other Workflows

For this error handler to work, other workflows must:
1. Go to workflow settings
2. Set "Error Workflow" to "Doc Chain - Errors"

| Workflow | Error Handler Set? |
|----------|-------------------|
| Doc Chain - Trigger | ⬜ Verify |
| Doc Chain - Distributor | ⬜ Verify |
| Doc Chain - Agent | ⬜ Verify |
| Doc Chain - State Reconciliation | ⬜ Verify |
| Doc Chain - Staleness | ⬜ Verify |

---

## Test Scenarios

### Test 1: Simulate Error in Agent
1. Cause GitHub API failure (invalid token)
2. Verify error is caught
3. Verify callback sent

### Test 2: Error Without task_id
**Expected:** Logs error, no callback sent (no task_id).

### Test 3: Callback Failure (404)
**Expected:** Logged as 'expired', no workflow failure.

---

## Known Issues

| Issue | Severity | Status |
|-------|----------|--------|
| Callback URL mismatch | 🟡 Medium | Verify Distributor accepts |
| Other workflows may not have error handler set | 🟡 Medium | Need verification |

---

## Sign-off

| Item | Verified | Date | Reviewer |
|------|----------|------|----------|
| All 5 nodes reviewed | ⬜ | - | - |
| task_id extraction works | ⬜ | - | - |
| Callback sent correctly | ⬜ | - | - |
| Other workflows configured | ⬜ | - | - |

**Final Sign-off:** ⬜ Pending
