# Workflow Review: Doc Chain - Agent

**Workflow ID:** `5vQ8lMCyatxB8Fdd`
**Version:** AGENT-V001
**Updated:** 2025-12-23T17:17:55.101Z
**Nodes:** 14

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

Receives individual tasks from Distributor, fetches document content, uses AI to make updates, commits changes to GitHub, updates documentation_matrix.json, and sends completion callback.

---

## Node-by-Node Review

### Node 1: Receive Task
**Type:** `n8n-nodes-base.webhook`
**Path:** `/domain-agent`

| Check | Status | Notes |
|-------|--------|-------|
| Endpoint accessible | ⬜ | POST method |
| Receives from Distributor | ⬜ | - |

**Expected Input:**
```json
{
  "task": "{\"task_id\":\"...\",\"document\":\"...\",\"description\":\"...\"}",
  "trigger": "{\"type\":\"...\",\"message\":\"...\"}",
  "list_id": "..."
}
```

---

### Node 2: Parse Webhook Data
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Parses JSON strings | ⬜ | task, trigger may be stringified |
| Normalizes field names | ⬜ | target → document |
| Cleans list_id | ⬜ | Removes quotes |

**Key Logic:**
```javascript
// Normalize: State Reconciliation uses "target", Trigger uses "document"
if (task && task.target && !task.document) {
  task.document = task.target;
}
```

---

### Node 3: Fetch Document
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `https://raw.githubusercontent.com/.../main/{document}`

| Check | Status | Notes |
|-------|--------|-------|
| URL constructed correctly | ⬜ | Dynamic path |
| Response as text | ⬜ | Not JSON |
| Handles 404 | ⬜ | New documents? |

---

### Node 4: Update Document (AI Agent)
**Type:** `@n8n/n8n-nodes-langchain.agent`

| Check | Status | Notes |
|-------|--------|-------|
| System prompt correct | ⬜ | Document types |
| Input references work | ⬜ | $('Parse Webhook Data') |
| Output format enforced | ⬜ | JSON with updated_content |

**Document Types Handled:**
- ⬜ Regular Documentation (prose updates)
- ⬜ Task Cards (status, checkboxes, dates)
- ⬜ Roadmaps/Indexes (percentages, tables)

**Expected Output:**
```json
{
  "changes_needed": true,
  "updated_content": "full updated document",
  "summary": "brief description",
  "update_type": "PROSE|STATUS|CHECKBOX|PERCENTAGE"
}
```

---

### Node 5: Gemini Model
**Type:** `@n8n/n8n-nodes-langchain.lmChatGoogleGemini`
**Credential:** `kJmLsDFHzgrlPJhY`

| Check | Status | Notes |
|-------|--------|-------|
| Credential valid | ⬜ | - |
| Connected to agent | ⬜ | ai_languageModel |

---

### Node 6: Parse AI Output
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Greedy JSON match | ⬜ | `/{[\s\S]*}/` |
| Error handling | ⬜ | Fallback defaults |
| Passes task_id through | ⬜ | For callback |

---

### Node 7: Changes Needed
**Type:** `n8n-nodes-base.if`

| Check | Status | Notes |
|-------|--------|-------|
| True → Get File SHA | ⬜ | Proceed to commit |
| False → Fetch Matrix | ⬜ | Skip commit, update tracking |

---

### Node 8: Get File SHA
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `https://api.github.com/repos/.../contents/{document}`

| Check | Status | Notes |
|-------|--------|-------|
| Auth header | ⬜ | Bearer env.GITHUB_TOKEN |
| Gets current SHA | ⬜ | Required for update |

---

### Node 9: Prepare Commit
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Base64 encodes content | ⬜ | - |
| Sanitizes summary | ⬜ | Removes special chars |
| [n8n] prefix | ⬜ | Prevents trigger loops |

**Commit Message Format:**
```
[n8n] docs: {sanitized summary}
```

---

### Node 10: Commit to GitHub
**Type:** `n8n-nodes-base.httpRequest`
**Method:** PUT
**URL:** `https://api.github.com/repos/.../contents/{document}`

| Check | Status | Notes |
|-------|--------|-------|
| Auth header | ⬜ | Bearer env.GITHUB_TOKEN |
| Body fields | ⬜ | message, content, sha |
| Success handling | ⬜ | - |

---

### Node 11: Fetch Matrix
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `.../docs/documentation_matrix.json`

| Check | Status | Notes |
|-------|--------|-------|
| Fetches current matrix | ⬜ | For update |
| Gets SHA | ⬜ | For commit |

---

### Node 12: Update Review Tracking
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Finds document in matrix | ⬜ | By path |
| Updates last_reviewed | ⬜ | Today's date |
| Calculates next_review | ⬜ | Based on interval |
| Updates last_updated if changed | ⬜ | - |

---

### Node 13: Commit Matrix Update
**Type:** `n8n-nodes-base.httpRequest`
**Method:** PUT

| Check | Status | Notes |
|-------|--------|-------|
| Commits matrix changes | ⬜ | - |
| [n8n] chore: prefix | ⬜ | Won't trigger chain |
| onError: continueRegularOutput | ⬜ | Doesn't fail workflow |

---

### Node 14: Send Callback
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `https://gitlitreview.app.n8n.cloud/webhook/task-callback`

| Check | Status | Notes |
|-------|--------|-------|
| POST method | ⬜ | - |
| Includes task_id | ⬜ | From Update Review Tracking |
| Includes status | ⬜ | completed |
| onError: continueRegularOutput | ⬜ | Doesn't fail |

**Callback Payload:**
```json
{
  "task_id": "...",
  "status": "completed",
  "result": { "summary": "..." }
}
```

---

## Data Flow

```
Receive Task → Parse Webhook Data → Fetch Document → AI Update
                                                      ↓
Changes Needed ─── YES → Get SHA → Prepare → Commit to GitHub
       │                                          ↓
       └── NO ─────────────────────────────→ Fetch Matrix
                                                  ↓
                                    Update Review Tracking
                                                  ↓
                                    Commit Matrix Update
                                                  ↓
                                    Send Callback (to Distributor)
```

---

## Integration Points

| Target | Method | Purpose |
|--------|--------|---------|
| GitHub Raw | GET | Fetch document content |
| GitHub API | GET | Get file SHA |
| GitHub API | PUT | Commit document |
| GitHub API | PUT | Commit matrix |
| Distributor | POST | Completion callback |

---

## Test Scenarios

### Test 1: Document Update Task
```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/domain-agent \
  -H "Content-Type: application/json" \
  -d '{
    "task": "{\"task_id\":\"t1\",\"document\":\"docs/README.md\",\"description\":\"Update version\"}",
    "trigger": "{\"type\":\"manual\",\"message\":\"test\"}",
    "list_id": "test-001"
  }'
```

### Test 2: Task Card Status Update
Test with a task-card document to verify checkbox/status handling.

### Test 3: No Changes Needed
AI determines no changes → Should still update matrix and callback.

---

## Sign-off

| Item | Verified | Date | Reviewer |
|------|----------|------|----------|
| All nodes reviewed | ⬜ | - | - |
| AI prompt validated | ⬜ | - | - |
| GitHub commits work | ⬜ | - | - |
| Callback sent | ⬜ | - | - |
| Loop prevention verified | ⬜ | - | - |

**Final Sign-off:** ⬜ Pending
