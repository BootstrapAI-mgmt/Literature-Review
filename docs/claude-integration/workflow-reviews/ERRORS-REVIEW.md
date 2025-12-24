# Doc Chain - Errors Workflow Review

> **Workflow ID:** gplUON3gG47QIMpi  
> **Status:** ✅ Active  
> **Version:** Err-V001  
> **Last Updated:** 2025-12-23T17:11:54.795Z

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

## Workflow Purpose

Global error handler for all Doc Chain workflows. Catches errors from any workflow execution, extracts task_id if available, and sends failure callback to Distributor to unblock the queue.

---

## Trigger Configuration

| Trigger | Type | Notes |
|---------|------|-------|
| Catch Errors | errorTrigger | Catches errors from all workflows |

---

## Node-by-Node Validation (5 Nodes)

### Node 1: Catch Errors
| Check | Status | Notes |
|-------|--------|-------|
| Type: errorTrigger | [ ] | n8n built-in |
| Catches all workflow errors | [ ] | |

**Error Object Structure:**
```javascript
{
  workflow: { id, name },
  execution: {
    id,
    lastNodeExecuted,
    error: {
      message,
      context: {
        request: { uri, body }
      }
    },
    data: { task_id }
  }
}
```

---

### Node 2: Log Error
| Check | Status | Notes |
|-------|--------|-------|
| Console.error logging | [ ] | |
| Extracts task_id (3 paths) | [ ] | See below |
| Returns normalized error | [ ] | |

**Task ID Extraction Paths:**
1. `error.execution.data.task_id` - If workflow passed it through
2. `error.execution.error.context.request.body.task_id` - From failed HTTP request body
3. Parse from failed URL: `/webhook/task-done-{task_id}` - Regex extraction

**Output Schema:**
```javascript
{
  workflow: "Doc Chain - Agent",
  node: "Commit to GitHub",
  message: "HTTP 401 Unauthorized",
  timestamp: "2025-12-24T00:00:00.000Z",
  task_id: "task-001" // or null
}
```

---

### Node 3: Has Task ID (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `$json.task_id` is not empty |
| True → Send Failure Callback | [ ] | |
| False → End (no callback needed) | [ ] | |

---

### Node 4: Send Failure Callback
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | `/webhook/task-done-{task_id}` |
| Method: POST | [ ] | |
| Status: failed | [ ] | |
| Includes error message | [ ] | |
| onError: continueRegularOutput | [ ] | Graceful on 404 |

**Request Body:**
```json
{
  "task_id": "task-001",
  "status": "failed",
  "result": {
    "error": "HTTP 401 Unauthorized"
  }
}
```

**Note:** URL uses `task-done-{task_id}` pattern which differs from Agent callback URL (`task-callback`). This may be intentional for different handling or could be a mismatch.

---

### Node 5: Log Callback Result
| Check | Status | Notes |
|-------|--------|-------|
| Checks callback success | [ ] | |
| Handles 404 gracefully | [ ] | Wait node expired = OK |
| Logs status | [ ] | `notified` or `expired` |

---

## Connection Validation

| From Node | To Node | Type | Status |
|-----------|---------|------|--------|
| Catch Errors | Log Error | main | [ ] |
| Log Error | Has Task ID | main | [ ] |
| Has Task ID (true) | Send Failure Callback | main | [ ] |
| Send Failure Callback | Log Callback Result | main | [ ] |

---

## Callback URL Investigation

**Potential Issue:**
- Agent sends to: `https://gitlitreview.app.n8n.cloud/webhook/task-callback`
- Errors sends to: `https://gitlitreview.app.n8n.cloud/webhook/task-done-{task_id}`

These are different endpoints. Need to verify:
1. Does Distributor have both webhooks?
2. Is `task-done-{task_id}` a dynamic webhook pattern?
3. Is this intentional for different error handling?

**Resolution:** Check Distributor workflow for webhook endpoints.

---

## Error Scenarios Handled

| Scenario | Task ID Available? | Callback Sent? |
|----------|-------------------|----------------|
| GitHub API 401 | Yes (from request) | ✅ |
| GitHub API 404 | Yes (from request) | ✅ |
| AI Model Timeout | Maybe (if passed through) | Depends |
| Network Error | Maybe (if in body) | Depends |
| Workflow Logic Error | Unlikely | ❌ |
| Webhook Parse Error | No | ❌ |

---

## Issues Found

| # | Severity | Description | Recommendation |
|---|----------|-------------|----------------|
| 1 | 🟡 MED | Callback URL differs from Agent | Verify both endpoints exist in Distributor |
| 2 | 🟢 LOW | task_id not always available | Expected - some errors won't have task context |

---

## Sign-off

- [ ] All 5 nodes validated
- [ ] Task ID extraction paths verified
- [ ] Callback URL confirmed in Distributor
- [ ] Error scenarios documented

**Reviewer:** ________________________  
**Date:** ________________________  
**Signature:** ________________________
