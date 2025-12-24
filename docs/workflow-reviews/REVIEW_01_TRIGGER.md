# Workflow Review: Doc Chain - Trigger

**Workflow ID:** `qQKXewWTby495ix7`
**Version:** TRIGGER-V001
**Updated:** 2025-12-23T17:16:04.951Z
**Nodes:** 11

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

Receives GitHub webhook push events, filters valid documentation changes, uses AI to generate task lists, and forwards to the Distributor.

---

## Node-by-Node Review

### Node 1: GitHub Webhook
**Type:** `n8n-nodes-base.webhook`
**Path:** `/github-doc-trigger`

| Check | Status | Notes |
|-------|--------|-------|
| Endpoint accessible | ⬜ | POST method |
| Headers validated | ⬜ | GitHub signature verification? |
| Body parsing works | ⬜ | - |

**Input Schema:**
```json
{
  "commits": [...],
  "ref": "refs/heads/main",
  "pusher": { "name": "..." }
}
```

---

### Node 2: Filter Valid Events
**Type:** `n8n-nodes-base.if`

| Check | Status | Notes |
|-------|--------|-------|
| Filters [n8n] commits | ⬜ | Prevents loops |
| Allows manual [n8n] commits | ⬜ | [n8n] fix: passes |
| Branch filter correct | ⬜ | main only? |

**Logic Validation:**
- ⬜ `[n8n] docs:` commits are BLOCKED
- ⬜ `[n8n] chore:` commits are BLOCKED  
- ⬜ `[n8n] fix:` commits are ALLOWED
- ⬜ Regular commits are ALLOWED

---

### Node 3: Parse Changes
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Extracts commit data | ⬜ | - |
| Maps file changes | ⬜ | added/modified/removed |
| Filters docs paths | ⬜ | docs/, task-cards/ |

**Output Schema:**
```json
{
  "changes": [
    { "path": "docs/file.md", "action": "modified" }
  ],
  "commit_message": "...",
  "author": "..."
}
```

---

### Node 4: Fetch Matrix
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `https://raw.githubusercontent.com/.../documentation_matrix.json`

| Check | Status | Notes |
|-------|--------|-------|
| URL correct | ⬜ | BootstrapAI-mgmt/Literature-Review |
| Auth not needed | ⬜ | Public repo |
| Response parsed | ⬜ | JSON format |

---

### Node 5: Find Affected Docs
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Dependency lookup works | ⬜ | Finds dependents |
| New docs handled | ⬜ | Not in matrix yet |
| Domain inference | ⬜ | From path patterns |

**Dependency Resolution Logic:**
- ⬜ If doc A depends on doc B, and B changes, A is flagged
- ⬜ Parent indexes are found from `parent_index` field
- ⬜ New docs get domain from path (e.g., `task-cards/automation/` → `@automation`)

---

### Node 6: Has Updates
**Type:** `n8n-nodes-base.if`

| Check | Status | Notes |
|-------|--------|-------|
| True path connected | ⬜ | → Task Master |
| False path connected | ⬜ | → No Updates Needed |

---

### Node 7: Task Master (AI Agent)
**Type:** `@n8n/n8n-nodes-langchain.agent`
**Credential:** `kJmLsDFHzgrlPJhY` (Google Gemini)

| Check | Status | Notes |
|-------|--------|-------|
| System prompt correct | ⬜ | Task generation rules |
| Output format enforced | ⬜ | JSON task list |
| Task types valid | ⬜ | UPDATE_REFERENCE, etc. |

**Task Types Generated:**
- ⬜ UPDATE_REFERENCE
- ⬜ UPDATE_INDEX
- ⬜ CASCADE_UPDATE
- ⬜ REVIEW_NEEDED
- ⬜ STATUS_UPDATE
- ⬜ CHECKBOX_TOGGLE
- ⬜ COMPLETION_PERCENTAGE

---

### Node 8: Gemini Model
**Type:** `@n8n/n8n-nodes-langchain.lmChatGoogleGemini`

| Check | Status | Notes |
|-------|--------|-------|
| Credential valid | ⬜ | Test API call |
| Model version | ⬜ | Default Gemini |

---

### Node 9: Parse AI Response
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| JSON extraction | ⬜ | Handles markdown blocks |
| Error handling | ⬜ | Invalid JSON fallback |
| Task validation | ⬜ | Required fields present |

---

### Node 10: Send to Distributor
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `https://gitlitreview.app.n8n.cloud/webhook/task-distributor`

| Check | Status | Notes |
|-------|--------|-------|
| URL matches Distributor | ⬜ | Endpoint exists |
| Payload format correct | ⬜ | Task schema |
| POST method | ⬜ | - |

---

### Node 11: No Updates Needed
**Type:** `n8n-nodes-base.noOp`

| Check | Status | Notes |
|-------|--------|-------|
| Terminal node | ⬜ | No downstream |

---

## Integration Points

| Target | Method | Validation |
|--------|--------|------------|
| GitHub API | GET | Matrix fetch |
| Distributor Webhook | POST | Task dispatch |

---

## Test Scenarios

### Test 1: Normal Documentation Commit
```bash
# Simulate push event
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/github-doc-trigger \
  -H "Content-Type: application/json" \
  -d '{"commits":[{"message":"Update docs","modified":["docs/README.md"]}]}'
```
**Expected:** Tasks generated and sent to Distributor

### Test 2: N8N Automated Commit (Should Block)
```bash
# Should be filtered out
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/github-doc-trigger \
  -H "Content-Type: application/json" \
  -d '{"commits":[{"message":"[n8n] docs: auto update","modified":["docs/file.md"]}]}'
```
**Expected:** Blocked at Filter Valid Events

### Test 3: No Documentation Changes
**Expected:** Has Updates → False → No Updates Needed

---

## Sign-off

| Item | Verified | Date | Reviewer |
|------|----------|------|----------|
| All nodes reviewed | ⬜ | - | - |
| Connections validated | ⬜ | - | - |
| Test scenarios passed | ⬜ | - | - |
| Integration verified | ⬜ | - | - |

**Final Sign-off:** ⬜ Pending
