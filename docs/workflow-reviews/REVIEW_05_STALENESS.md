# Workflow Review: Doc Chain - Staleness

**Workflow ID:** `WRzBAw1oMYLbnu7d`
**Version:** STALE-V001
**Updated:** 2025-12-23T17:17:16.841Z
**Nodes:** 32

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

Weekly documentation staleness review that:
1. Reads domain configuration from documentation_matrix.json
2. Checks last activity per domain via GitHub commits
3. Fetches recent repository changes
4. Uses AI to assess staleness score (0-1)
5. Routes by score to: Auto Update, Manual Review, Create Issue, or Healthy

---

## Trigger Configuration

| Trigger | Schedule | Purpose |
|---------|----------|---------|
| Weekly Review | Every week, 2:00 AM | Automated |
| Manual Trigger | POST `/staleness-review` | On-demand |

---

## Staleness Score Thresholds

| Score | Status | Action |
|-------|--------|--------|
| 0.0 - 0.3 | Healthy | Log only |
| 0.3 - 0.5 | Minor Drift | Create GitHub Issue |
| 0.5 - 0.7 | Moderate | Create GitHub Issue |
| 0.7 - 1.0 | Critical | Send to Distributor for auto-update |

---

## Key Nodes Review

### Workflow Configuration
**Type:** `n8n-nodes-base.set`

| Check | Status | Notes |
|-------|--------|-------|
| matrixUrl correct | ⬜ | Points to raw GitHub |
| githubRepo correct | ⬜ | BootstrapAI-mgmt/Literature-Review |
| distributorWebhook | ⬜ | ⚠️ PLACEHOLDER VALUE |

**⚠️ Issue Found:**
```
distributorWebhook: "<__PLACEHOLDER_VALUE__Task Distributor Webhook URL__>"
```
This needs to be updated to the actual webhook URL.

---

### Get Domains
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Parses owner_domains | ⬜ | From matrix |
| Handles old/new format | ⬜ | Array vs object |
| Stagger day filtering | ⬜ | Optional per-domain schedule |

---

### Get Last Activity
**Type:** `n8n-nodes-base.httpRequest`
**Credential:** `Ho5S7HOxBPdmEAL0` (Header Auth)

| Check | Status | Notes |
|-------|--------|-------|
| GitHub commits API | ⬜ | Per document path |
| Auth header works | ⬜ | - |
| per_page=1 | ⬜ | Just need latest |

---

### Calculate Inactivity
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Days calculation | ⬜ | now - last_commit |
| Compares to interval | ⬜ | review_interval_days |
| Handles no commits | ⬜ | Defaults to 2000-01-01 |

---

### Filter Changes
**Type:** `n8n-nodes-base.code`

**Ignored Commit Patterns:**
- `test(` / `test:`
- `ci(` / `ci:`
- `chore(` / `chore:`
- `style(` / `style:`
- `docs(` / `docs:` (checking FOR staleness, not FROM doc changes)

| Check | Status | Notes |
|-------|--------|-------|
| Patterns exclude noise | ⬜ | Test/CI/style commits |
| Relevant changes extracted | ⬜ | Feature commits |

---

### Staleness Assessment (AI Agent)
**Type:** `@n8n/n8n-nodes-langchain.agent`
**Model:** Gemini 2.5 Flash

| Check | Status | Notes |
|-------|--------|-------|
| System prompt | ⬜ | Staleness reviewer role |
| Output parser | ⬜ | Structured JSON schema |
| Findings array | ⬜ | Specific issues |

**Output Schema:**
```json
{
  "staleness_score": 0.5,
  "findings": ["string"],
  "recommended_action": "update|review|monitor",
  "update_tasks": ["string"]
}
```

---

### Route By Score
**Type:** `n8n-nodes-base.switch`

| Output | Condition | Destination |
|--------|-----------|-------------|
| Auto Update | score >= 0.7 AND has tasks | Send to Distributor |
| Manual Review | 0.5 <= score < 0.7 | Search Existing Issues |
| Create Issue | 0.3 <= score < 0.5 | Search Existing Issues |
| Healthy | score < 0.3 | Log Healthy |

---

### Search Existing Issues
**Type:** `n8n-nodes-base.httpRequest`

| Check | Status | Notes |
|-------|--------|-------|
| GitHub search API | ⬜ | Issues with staleness-review label |
| Deduplication | ⬜ | Skip if issue exists for domain |

---

### Create Review Issue
**Type:** `n8n-nodes-base.httpRequest`

| Check | Status | Notes |
|-------|--------|-------|
| Issue title format | ⬜ | `📚 Staleness Review: {domain} (score: X%)` |
| Labels | ⬜ | documentation, staleness-review, automated |
| Findings included | ⬜ | In body |

---

### Generate Digest
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Week ID calculation | ⬜ | YYYY-WNN format |
| Summary stats | ⬜ | domains_reviewed, healthy, need_attention |
| Domain statuses | ⬜ | Array of results |

---

### Create Digest Issue
**Type:** `n8n-nodes-base.httpRequest`

| Check | Status | Notes |
|-------|--------|-------|
| Only if has findings | ⬜ | After Has Findings? check |
| Weekly summary table | ⬜ | Markdown table |

---

## Test Scenarios

### Test 1: Manual Trigger
```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/staleness-review
```

### Test 2: Force Stale Domain
Create a domain with documents not updated for >7 days.
**Expected:** AI assesses staleness, routes appropriately.

### Test 3: Duplicate Issue Prevention
Run twice in succession.
**Expected:** Second run skips issue creation if exists.

---

## Known Issues

| Issue | Severity | Status |
|-------|----------|--------|
| distributorWebhook is placeholder | 🔴 High | Needs fix |

---

## Sign-off

| Item | Verified | Date | Reviewer |
|------|----------|------|----------|
| All 32 nodes reviewed | ⬜ | - | - |
| Placeholder values fixed | ⬜ | - | - |
| Staleness scoring accurate | ⬜ | - | - |
| Issue creation works | ⬜ | - | - |
| Deduplication works | ⬜ | - | - |

**Final Sign-off:** ⬜ Pending
