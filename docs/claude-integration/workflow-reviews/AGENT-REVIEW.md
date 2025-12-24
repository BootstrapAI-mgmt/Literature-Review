# Doc Chain - Agent Workflow Review

> **Workflow ID:** 5vQ8lMCyatxB8Fdd  
> **Status:** ✅ Active  
> **Version:** AGENT-V001  
> **Last Updated:** 2025-12-23T17:17:55.101Z

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

Receives individual tasks from Distributor, fetches target document from GitHub, uses Gemini AI to generate updates, commits changes back to GitHub, updates `documentation_matrix.json` review tracking, and sends callback to Distributor.

---

## Node-by-Node Validation (14 Nodes)

### Node 1: Receive Task (Webhook)
| Check | Status | Notes |
|-------|--------|-------|
| Path correct | [ ] | `domain-agent` |
| Method: POST | [ ] | |

**Expected Input:**
```json
{
  "body": {
    "task": "{...stringified JSON...}",
    "trigger": "{...stringified JSON...}",
    "list_id": "ul-..."
  }
}
```

---

### Node 2: Parse Webhook Data
| Check | Status | Notes |
|-------|--------|-------|
| Parses stringified task | [ ] | `JSON.parse()` with fallback |
| Parses stringified trigger | [ ] | |
| Normalizes target/document | [ ] | `task.target` → `task.document` |
| Cleans list_id quotes | [ ] | |

**Output Schema:**
```javascript
{
  task: { task_id, document, update_type, description, ... },
  trigger: { type, message, ... },
  list_id: "ul-..."
}
```

---

### Node 3: Fetch Document
| Check | Status | Notes |
|-------|--------|-------|
| URL pattern correct | [ ] | `raw.githubusercontent.com/.../main/{document}` |
| Response format: text | [ ] | |
| Error handling | [ ] | |

**URL:** `https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/{{ $json.task.document }}`

---

### Node 4: Update Document (AI Agent)
| Check | Status | Notes |
|-------|--------|-------|
| Uses Gemini model | [ ] | Credential: `kJmLsDFHzgrlPJhY` |
| System prompt complete | [ ] | Document types defined |
| User message includes context | [ ] | Task, trigger, content |

**System Prompt Handles:**
- Regular Documentation (prose, references, dates)
- Task Cards (status, checkboxes, completion dates)
- Roadmaps/Indexes (percentages, status tables)

**Expected Output:**
```json
{
  "changes_needed": true,
  "updated_content": "full updated document...",
  "summary": "brief description",
  "update_type": "PROSE|STATUS|CHECKBOX|PERCENTAGE"
}
```

---

### Node 5: Gemini Model
| Check | Status | Notes |
|-------|--------|-------|
| Credential valid | [ ] | `Google Gemini(PaLM) Api account` |
| Connected to Update Document | [ ] | `ai_languageModel` connection |

---

### Node 6: Parse AI Output
| Check | Status | Notes |
|-------|--------|-------|
| Greedy JSON match | [ ] | `/\{[\s\S]*\}/` |
| Handles parsing errors | [ ] | Default: `changes_needed: false` |
| Preserves task_id | [ ] | From Parse Webhook Data |

---

### Node 7: Changes Needed (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `$json.changes_needed === true` |
| True → Get File SHA | [ ] | |
| False → Fetch Matrix | [ ] | Skip to review tracking |

---

### Node 8: Get File SHA
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | GitHub Contents API |
| Auth header | [ ] | `Bearer {{ env.GITHUB_TOKEN }}` |
| Accept header | [ ] | `application/vnd.github.v3+json` |

**URL:** `https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/contents/{{ $json.document }}`

---

### Node 9: Prepare Commit
| Check | Status | Notes |
|-------|--------|-------|
| Base64 encodes content | [ ] | `Buffer.from().toString('base64')` |
| Sanitizes commit message | [ ] | Removes special chars |
| Adds `[n8n] docs:` prefix | [ ] | **CRITICAL for loop prevention** |
| Limits message length | [ ] | 68 chars |

**Commit Message Format:** `[n8n] docs: {sanitized summary}`

---

### Node 10: Commit to GitHub
| Check | Status | Notes |
|-------|--------|-------|
| Method: PUT | [ ] | |
| URL correct | [ ] | GitHub Contents API |
| Body includes message, content, sha | [ ] | |
| Auth header | [ ] | `Bearer {{ env.GITHUB_TOKEN }}` |

---

### Node 11: Fetch Matrix
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | `/contents/docs/documentation_matrix.json` |
| Auth header | [ ] | |
| Called after commit OR when no changes | [ ] | Both paths converge |

---

### Node 12: Update Review Tracking
| Check | Status | Notes |
|-------|--------|-------|
| Decodes matrix from base64 | [ ] | |
| Finds document in matrix | [ ] | By path |
| Updates `last_reviewed` | [ ] | Today's date |
| Calculates `next_review` | [ ] | Based on `review_interval_days` |
| Updates `last_updated` if changed | [ ] | |
| Adds `[n8n] chore:` prefix | [ ] | **CRITICAL for loop prevention** |

**Commit Message Format:** `[n8n] chore: update review tracking for {document}`

---

### Node 13: Commit Matrix Update
| Check | Status | Notes |
|-------|--------|-------|
| Method: PUT | [ ] | |
| URL correct | [ ] | Matrix file path |
| onError: continueRegularOutput | [ ] | Graceful failure |

---

### Node 14: Send Callback
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | `https://gitlitreview.app.n8n.cloud/webhook/task-callback` |
| Method: POST | [ ] | |
| Includes task_id | [ ] | |
| Includes status | [ ] | `completed` |
| Includes result summary | [ ] | |
| onError: continueRegularOutput | [ ] | |

**Callback Body:**
```json
{
  "task_id": "...",
  "status": "completed",
  "result": { "summary": "..." }
}
```

---

## Connection Validation

| From Node | To Node | Type | Status |
|-----------|---------|------|--------|
| Receive Task | Parse Webhook Data | main | [ ] |
| Parse Webhook Data | Fetch Document | main | [ ] |
| Fetch Document | Update Document | main | [ ] |
| Gemini Model | Update Document | ai_languageModel | [ ] |
| Update Document | Parse AI Output | main | [ ] |
| Parse AI Output | Changes Needed | main | [ ] |
| Changes Needed (true) | Get File SHA | main | [ ] |
| Changes Needed (false) | Fetch Matrix | main | [ ] |
| Get File SHA | Prepare Commit | main | [ ] |
| Prepare Commit | Commit to GitHub | main | [ ] |
| Commit to GitHub | Fetch Matrix | main | [ ] |
| Fetch Matrix | Update Review Tracking | main | [ ] |
| Update Review Tracking | Commit Matrix Update | main | [ ] |
| Commit Matrix Update | Send Callback | main | [ ] |

---

## Loop Prevention Verification

| Mechanism | Implemented? | Notes |
|-----------|--------------|-------|
| Document commit prefix | [ ] | `[n8n] docs:` |
| Matrix commit prefix | [ ] | `[n8n] chore:` |
| Trigger filters these | [ ] | Verified in TRIGGER-REVIEW.md |

---

## Environment Variables Required

| Variable | Purpose | Status |
|----------|---------|--------|
| `GITHUB_TOKEN` | GitHub API authentication | [ ] Verify in n8n |

---

## Issues Found

| # | Severity | Description | Recommendation |
|---|----------|-------------|----------------|
| 1 | - | - | - |

---

## Sign-off

- [ ] All 14 nodes validated
- [ ] All connections verified
- [ ] Loop prevention confirmed
- [ ] Callback URL matches Distributor
- [ ] Environment variables confirmed

**Reviewer:** ________________________  
**Date:** ________________________  
**Signature:** ________________________
