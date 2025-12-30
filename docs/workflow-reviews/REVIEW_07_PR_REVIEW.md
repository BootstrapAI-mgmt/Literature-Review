# Workflow Review: Doc Chain - PR Review

**Workflow ID:** `03ONuhFTJGDhmtJ9`
**Version:** PR-REVIEW-V001
**Updated:** 2025-12-25
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

Analyzes incoming Pull Requests to determine if documentation updates are needed. Uses AI to scan code changes and suggest documentation improvements, posting a comment on the PR with findings.

---

## Node-by-Node Review

### Node 1: PR Webhook
**Type:** `n8n-nodes-base.webhook`
**Path:** `/pr-review`

| Check | Status | Notes |
|-------|--------|-------|
| Endpoint accessible | ⬜ | POST method |
| Events handled | ⬜ | opened, synchronize |

---

### Node 2: Configuration
**Type:** `n8n-nodes-base.set`

| Check | Status | Notes |
|-------|--------|-------|
| Extract PR details | ⬜ | number, title, author |
| Extract Repo details | ⬜ | Hardcoded owner/name? |
| Bot detection | ⬜ | user.type === 'Bot' |

---

### Node 3: Is Human PR?
**Type:** `n8n-nodes-base.if`

| Check | Status | Notes |
|-------|--------|-------|
| Filters bots | ⬜ | !is_bot |

---

### Node 4: Get PR Files
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `https://api.github.com/repos/.../pulls/{number}/files`

| Check | Status | Notes |
|-------|--------|-------|
| Auth header | ⬜ | Generic Credential |
| Fetch limit | ⬜ | Default 30? Needs pagination? |

---

### Node 5: Analyze Files
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Categorization | ⬜ | code vs doc vs config |
| Patch extraction | ⬜ | Truncates to 500 chars |
| Summary generation | ⬜ | Counts file types |

---

### Node 6: AI Doc Impact Analysis
**Type:** `@n8n/n8n-nodes-langchain.agent`

| Check | Status | Notes |
|-------|--------|-------|
| System prompt | ⬜ | "Documentation impact analyzer" |
| Input context | ⬜ | Includes patches |
| Output JSON | ⬜ | needs_doc_update, confidence |

---

### Node 7: Parse AI Response
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| JSON parsing | ⬜ | Robust regex fallback |
| Default values | ⬜ | confidence: 0.5 |

---

### Node 8: Has Doc Impact?
**Type:** `n8n-nodes-base.if`

| Check | Status | Notes |
|-------|--------|-------|
| Threshold | ⬜ | confidence >= 0.6 |

---

### Node 9: Post Review Comment
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `.../pulls/{number}/reviews`

| Check | Status | Notes |
|-------|--------|-------|
| Comment body | ⬜ | Formatted markdown |
| Event type | ⬜ | COMMENT (not REQUEST_CHANGES) |

---

## Data Flow

```
Webhook → Config → Is Human? ── YES → Get Files → Analyze → AI Agent
                                                          ↓
                               Post Comment ← YES ── Has Impact?
```

---

## Test Scenarios

### Test 1: Code-only PR
PR with Python changes but no doc changes.
**Expected:** AI suggests documentation updates (needs_doc_update: true).

### Test 2: Doc-only PR
PR with only .md changes.
**Expected:** AI detects docs present (needs_doc_update: false).

### Test 3: Bot PR
**Expected:** Workflow skips analysis.

---

## Sign-off

| Item | Verified | Date | Reviewer |
|------|----------|------|----------|
| All nodes reviewed | ⬜ | - | - |
| Bot filter works | ⬜ | - | - |
| GitHub API auth | ⬜ | - | - |
| AI Prompt effectiveness | ⬜ | - | - |

**Final Sign-off:** ⬜ Pending
