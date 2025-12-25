# Doc Chain - Errors: Step-Through Validation

> **Workflow ID**: `gplUON3gG47QIMpi`  
> **Version**: Enhanced (Phase 4)  
> **Total Nodes**: 8  
> **Last n8n Update**: 2025-12-25T00:48:33.048Z

---

## Checkout Status

| Field | Value |
|-------|-------|
| **Review Status** | 📋 Ready for Review |
| **Checked Out By** | - |
| **Checkout Time** | - |

---

## Flow Diagram (Two Parallel Paths)

```
Catch Errors → Log Error ─┬→ Search Existing Error Issues → No Duplicate? → Create Error Issue
                          │
                          └→ Has Task ID? → Send Failure Callback → Log Callback Result
```

---

## Node-by-Node Validation

### Node 1: Catch Errors
| ID | `3de8134a-e845-4242-a486-3075116bcca6` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Type: errorTrigger | [ ] | System-level trigger |
| Catches errors from same owner | [ ] | `callerPolicy: workflowsFromSameOwner` |

**Input**: n8n error object from any failing workflow

**Sign-off**: [ ] ________ Date: ________

---

### Node 2: Log Error
| ID | `4eb59ced-85b3-45fa-a72f-88043eb421c9` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Extracts workflow name | [ ] | `error.workflow?.name` |
| Extracts workflow_id | [ ] | For tracking |
| Extracts node name | [ ] | `lastNodeExecuted` |
| Extracts error message | [ ] | |
| Extracts task_id (3 methods) | [ ] | Data, body, URI match |
| Extracts execution_id | [ ] | For n8n UI lookup |
| Logs to console | [ ] | For n8n logs |

**Output Schema**:
```json
{
  "workflow": "Doc Chain - Agent",
  "workflow_id": "5vQ8lMCyatxB8Fdd",
  "node": "Commit to GitHub",
  "message": "HTTP 403: Forbidden",
  "timestamp": "2024-12-24T12:00:00.000Z",
  "task_id": "task-001",
  "execution_id": "exec-abc123"
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 3: Search Existing Error Issues
| ID | `search-error-issues` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: GitHub Search API | [ ] | `/search/issues` |
| Query filters: repo, is:open, label:workflow-error | [ ] | |
| Searches for workflow name | [ ] | Prevents duplicates |
| Uses Header Auth credential | [ ] | Not hardcoded token |

**Query Example**:
```
repo:BootstrapAI-mgmt/Literature-Review+is:open+label:workflow-error+"Doc Chain - Agent"
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 4: No Duplicate?
| ID | `no-dup-check` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `total_count === 0` | [ ] | No existing open issue |
| True → Create Error Issue | [ ] | |
| False → (ends, no new issue) | [ ] | Prevents spam |

**Sign-off**: [ ] ________ Date: ________

---

### Node 5: Create Error Issue
| ID | `create-error-issue` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: GitHub Issues API | [ ] | `/repos/.../issues` |
| Method: POST | [ ] | |
| Title includes workflow + node | [ ] | 🚨 prefix |
| Body includes all error details | [ ] | Formatted markdown |
| Labels: bug, automated, workflow-error | [ ] | |
| Uses Header Auth credential | [ ] | Not hardcoded |

**Issue Template Verification**:
| Field | Included | Status |
|-------|----------|--------|
| Workflow name | [ ] | |
| Workflow ID | [ ] | |
| Failed node | [ ] | |
| Timestamp | [ ] | |
| Execution ID | [ ] | |
| Error message | [ ] | Code block |
| Task context | [ ] | If available |

**Sign-off**: [ ] ________ Date: ________

---

### Node 6: Has Task ID
| ID | `211f2c6c-b49f-4b10-ad3e-59f39c638348` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: task_id not empty | [ ] | |
| True → Send Failure Callback | [ ] | |
| False → (ends) | [ ] | No callback possible |

**Sign-off**: [ ] ________ Date: ________

---

### Node 7: Send Failure Callback
| ID | `f5b1d490-4d61-47f1-8f57-55acc916ac36` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: `/webhook/task-done-{task_id}` | [ ] | ⚠️ Verify this matches Distributor |
| Method: POST | [ ] | |
| Body: task_id, status=failed, error | [ ] | |
| onError: continueRegularOutput | [ ] | Don't fail on callback error |

**⚠️ Note**: URL uses `/task-done-{task_id}` but Distributor callback is `/task-callback`. Verify compatibility.

**Sign-off**: [ ] ________ Date: ________

---

### Node 8: Log Callback Result
| ID | `882f0aff-513c-4b96-a04d-446889ccc285` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Checks for error in response | [ ] | |
| Logs status (notified/expired) | [ ] | |
| Returns callback_status | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

## Integration Points

| This Workflow | Connects To | Direction | Status |
|---------------|-------------|-----------|--------|
| Catch Errors | All other workflows | ← | [ ] |
| Create Error Issue | GitHub Issues | → | [ ] |
| Send Failure Callback | Distributor (?) | → | [ ] Verify endpoint |

---

## Repository Alignment

| Check | Status | Notes |
|-------|--------|-------|
| Repository: BootstrapAI-mgmt/Literature-Review | [ ] | |
| Labels exist: bug, automated, workflow-error | [ ] | May need to create |

---

## Test Scenarios

### Scenario 1: New Error Creates Issue
| Step | Expected | Status |
|------|----------|--------|
| Workflow fails | Error caught | [ ] |
| Log Error extracts details | All fields populated | [ ] |
| Search finds no duplicate | total_count = 0 | [ ] |
| Issue created | New GitHub issue | [ ] |

### Scenario 2: Duplicate Error Suppressed
| Step | Expected | Status |
|------|----------|--------|
| Same workflow fails again | Error caught | [ ] |
| Search finds existing issue | total_count > 0 | [ ] |
| No new issue created | Flow ends | [ ] |

### Scenario 3: Error with Task ID
| Step | Expected | Status |
|------|----------|--------|
| Task fails with ID | task_id extracted | [ ] |
| Callback sent | status: failed | [ ] |
| Distributor notified | Task marked failed | [ ] |

---

## Final Sign-Off

| Reviewer | Date | Status |
|----------|------|--------|
| | | |

**Workflow Approved**: [ ] Yes [ ] No

### Issues Found
| Node | Issue | Severity | Resolution |
|------|-------|----------|------------|
| Send Failure Callback | URL may not match Distributor | Medium | Verify endpoint |

---

*Document Version: 1.0*  
*Created: 2024-12-24*
