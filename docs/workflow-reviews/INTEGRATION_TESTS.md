# Doc Chain Integration Test Scenarios

**Version:** 1.0
**Created:** 2025-12-24

---

## Overview

This document defines end-to-end integration test scenarios for validating the complete Doc Chain workflow system.

---

## Prerequisites

Before running integration tests:

1. ✅ All 6 workflows activated in n8n
2. ⬜ GitHub webhook configured for repository
3. ⬜ documentation_matrix.json exists with valid entries
4. ⬜ GITHUB_TOKEN environment variable set in n8n
5. ⬜ Error handler workflow set in all workflows

---

## Test Suite 1: Happy Path - Documentation Update

### Test 1.1: Manual Documentation Change Triggers Full Chain

**Objective:** Verify complete flow from GitHub push to document update.

**Steps:**
1. Edit a markdown file in the repository
2. Commit with message: `docs: update README for testing`
3. Push to main branch

**Expected Results:**
| Workflow | Action | Verification |
|----------|--------|--------------|
| Trigger | Receives webhook | Check execution log |
| Trigger | Generates tasks | Task list created |
| Distributor | Queues tasks | Status endpoint shows pending |
| Agent | Updates document | GitHub commit created |
| Agent | Updates matrix | last_reviewed updated |
| Agent | Sends callback | Distributor receives |
| Distributor | Clears task | Status shows completed |

**Verification Commands:**
```bash
# Check Distributor status
curl https://gitlitreview.app.n8n.cloud/webhook/distributor-status

# Check GitHub for n8n commit
git log --oneline -5
```

---

### Test 1.2: Multiple Files Changed

**Objective:** Verify task ordering and sequential processing.

**Steps:**
1. Edit 3 markdown files in one commit
2. Push to main

**Expected Results:**
- 3 tasks generated
- Tasks processed sequentially (one at a time)
- All callbacks received

---

## Test Suite 2: Loop Prevention

### Test 2.1: N8N Automated Commit Filtered

**Objective:** Verify n8n commits don't trigger infinite loops.

**Steps:**
1. Run a workflow that creates a commit
2. Observe Trigger workflow

**Expected Results:**
- Trigger receives webhook
- `[n8n] docs:` commit filtered at "Filter Valid Events"
- No tasks generated

---

### Test 2.2: Documentation Matrix Update Ignored

**Objective:** Matrix updates don't trigger chain.

**Steps:**
1. Agent updates matrix
2. GitHub sends webhook for matrix commit

**Expected Results:**
- Filtered at "Filter Valid Events" (path exclusion)

---

## Test Suite 3: Deduplication

### Test 3.1: Same Document Submitted Twice

**Objective:** Verify duplicate tasks are skipped.

**Steps:**
1. Trigger update for `docs/README.md`
2. Before completion, trigger again for same file

**Expected Results:**
- First task queued and processed
- Second task skipped (deduplicated)
- Only one commit to GitHub

---

### Test 3.2: Recently Completed Document

**Objective:** Documents completed within 1 hour are skipped.

**Steps:**
1. Process update for `docs/README.md`
2. Wait 1 minute
3. Submit same document again

**Expected Results:**
- Skipped due to recent completion

---

## Test Suite 4: State Reconciliation

### Test 4.1: Intentional Mismatch Detection

**Objective:** Verify mismatch detection works.

**Setup:**
1. Update a task-card status to "Complete"
2. Leave README count unchanged
3. Run reconciliation

**Steps:**
```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/state-reconciliation
```

**Expected Results:**
- COMPLETION_COUNT_MISMATCH detected
- AI generates correction task
- Task sent to Distributor
- README updated by Agent

---

### Test 4.2: No Mismatches

**Objective:** Clean state returns "in_sync".

**Steps:**
1. Ensure all counts match
2. Run reconciliation

**Expected Results:**
- "Log in Sync" node executes
- Response shows `status: in_sync`

---

## Test Suite 5: Error Handling

### Test 5.1: GitHub API Failure

**Objective:** Errors caught and callback sent.

**Setup:**
1. Temporarily invalidate GITHUB_TOKEN

**Steps:**
1. Trigger a document update

**Expected Results:**
- Agent fails at GitHub API call
- Errors workflow catches error
- Failure callback sent to Distributor
- Task marked as failed

---

### Test 5.2: AI Model Failure

**Objective:** Graceful degradation on AI errors.

**Expected Results:**
- Parse AI Output uses fallback defaults
- Workflow continues or fails gracefully

---

## Test Suite 6: Staleness Review

### Test 6.1: Weekly Review Generates Digest

**Objective:** Staleness review creates GitHub issues.

**Steps:**
```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/staleness-review
```

**Expected Results:**
- All domains scanned
- Staleness scores assigned
- Issues created for score >= 0.3
- Digest issue created if any findings

---

### Test 6.2: Duplicate Issue Prevention

**Steps:**
1. Run staleness review twice

**Expected Results:**
- First run creates issues
- Second run skips (issues exist)

---

## Test Suite 7: Utility Endpoints

### Test 7.1: Distributor Status

```bash
curl https://gitlitreview.app.n8n.cloud/webhook/distributor-status
```

**Expected Response:**
```json
{
  "pending": 0,
  "in_progress": null,
  "completed_count": 5
}
```

---

### Test 7.2: Distributor Reset

```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/distributor-reset
```

**Expected Results:**
- All state cleared
- Status shows zeros

---

## Execution Checklist

| Test | Status | Date | Notes |
|------|--------|------|-------|
| 1.1 Manual change triggers chain | ✅ | 2025-12-30 | Verified E2E flow from commit to matrix update. |
| 1.2 Multiple files changed | ✅ | 2025-12-30 | Sequential processing verified (Execution 100, 101, 102). |
| 2.1 N8N commit filtered | ✅ | 2025-12-30 | Filtered at "Filter Valid Events" (Execution 94). |
| 2.2 Matrix update ignored | ✅ | 2025-12-30 | Filtered at "Find Affected Docs" (Execution 95). |
| 3.1 Duplicate submission | ✅ | 2025-12-30 | Distributor deduplication verified. |
| 3.2 Recently completed | ✅ | 2025-12-31 | Distributor deduplication verified (Execution 180). |
| 4.1 Mismatch detection | ✅ | 2025-12-30 | Detected discrepancy in docs count. |
| 4.2 No mismatches | ✅ | 2025-12-30 | Reached "Log in Sync" after corrections. |
| 5.1 GitHub API failure | ✅ | 2025-12-31 | Verified Error Handler extraction of task_id. |
| 5.2 AI model failure | ✅ | 2025-12-31 | Issue #120 displays backticked Task ID. |
| 6.1 Staleness digest | ✅ | 2025-12-30 | Gemini suggested AUTOMATED_UPDATE (Execution 85). |
| 6.2 Duplicate issue prevention | ✅ | 2025-12-31 | Execution 193 completed successfully. |
| 7.1 Status endpoint | ✅ | 2025-12-30 | Verified /webhook/distributor-status returns JSON. |
| 7.2 Reset endpoint | ✅ | 2025-12-30 | Verified /webhook/distributor-reset clears state. |

---

## Sign-off

| Phase | Status | Date | Reviewer |
|-------|--------|------|----------|
| All tests executed | ✅ | 2025-12-31 | Antigravity |
| Issues documented | ✅ | 2025-12-31 | Antigravity |
| Fixes verified | ✅ | 2025-12-31 | Antigravity |

**Final Integration Sign-off:** ✅ Complete / Verified
