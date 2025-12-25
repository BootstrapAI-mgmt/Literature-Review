# Doc Chain - PR Review: Step-Through Validation

> **Workflow ID**: `03ONuhFTJGDhmtJ9`  
> **Version**: PRR-V001 (Phase 4.3 New)  
> **Total Nodes**: 12 (including AI sub-node)  
> **Last n8n Update**: 2025-12-25T00:56:13.724Z

---

## Checkout Status

| Field | Value |
|-------|-------|
| **Review Status** | 📋 Ready for Review |
| **Checked Out By** | - |
| **Checkout Time** | - |

---

## Flow Diagram

```
PR Webhook → Configuration → Is Human PR?
                                ↓ (yes)              ↓ (no)
                           Get PR Files         Skip Bot PR
                                ↓
                          Analyze Files
                                ↓
                      AI Doc Impact Analysis
                         (+ Gemini Chat)
                                ↓
                        Parse AI Response
                                ↓
                         Has Doc Impact?
                    (needs_doc_update && confidence >= 60%)
                         ↓ (yes)              ↓ (no)
                  Post Review Comment      Log No Action
```

---

## Node-by-Node Validation

### Node 1: PR Webhook
| ID | `pr-webhook` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Path: `/pr-review` | [ ] | |
| Method: POST | [ ] | |
| Webhook ID configured | [ ] | `pr-review-webhook` |

**GitHub Webhook Configuration Required**:
| Setting | Value | Status |
|---------|-------|--------|
| URL | `https://gitlitreview.app.n8n.cloud/webhook/pr-review` | [ ] |
| Content type | `application/json` | [ ] |
| Events | Pull requests (opened, synchronize) | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

### Node 2: Configuration
| ID | `config` |
|----|-------|

| Field | Source | Status |
|-------|--------|--------|
| pr_number | `body.pull_request.number` | [ ] |
| pr_title | `body.pull_request.title` | [ ] |
| pr_author | `body.pull_request.user.login` | [ ] |
| pr_action | `body.action` | [ ] |
| repo_owner | `BootstrapAI-mgmt` (hardcoded) | [ ] |
| repo_name | `Literature-Review` (hardcoded) | [ ] |
| is_bot | Checks user.type === 'Bot' | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

### Node 3: Is Human PR?
| ID | `is-human` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `is_bot === false` | [ ] | |
| True → Get PR Files | [ ] | Human PRs |
| False → Skip Bot PR | [ ] | Dependabot, etc. |

**Sign-off**: [ ] ________ Date: ________

---

### Node 4: Skip Bot PR
| ID | `skip-bot` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Returns skip status | [ ] | |
| Logs reason: bot_pr | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 5: Get PR Files
| ID | `get-files` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: GitHub PR Files API | [ ] | `/pulls/{pr_number}/files` |
| Uses Header Auth credential | [ ] | Not hardcoded |
| Response format: JSON | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 6: Analyze Files
| ID | `analyze-files` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Categorizes code files | [ ] | py, js, ts, jsx, tsx, java, go, rs |
| Categorizes doc files | [ ] | docs/, .md, .rst |
| Categorizes config files | [ ] | json, yaml, yml, toml, ini, env |
| Truncates patches to 500 chars | [ ] | Prevents token overflow |
| Generates summary | [ ] | File count by type |

**Output Schema**:
```json
{
  "pr_number": 123,
  "pr_title": "Add feature",
  "total_files": 5,
  "code_files": [...],
  "doc_files": [...],
  "config_files": [...],
  "code_changed": true,
  "docs_included": false,
  "summary": "3 code, 0 docs, 2 config files"
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 7: AI Doc Impact Analysis
| ID | `ai-analysis` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| System message defines analysis criteria | [ ] | |
| Includes PR title and author | [ ] | |
| Lists changed files by category | [ ] | |
| Includes truncated code patches | [ ] | First 3 files |
| Specifies JSON output format | [ ] | |
| Uses Gemini Chat sub-node | [ ] | |

**Analysis Criteria (from system message)**:
- [ ] New features/APIs needing docs
- [ ] Changed behavior affecting docs
- [ ] Removed functionality
- [ ] Configuration changes
- [ ] Whether docs already included

**Expected Output**:
```json
{
  "needs_doc_update": true,
  "confidence": 0.8,
  "affected_docs": ["docs/README.md"],
  "suggestions": ["Add API documentation"],
  "summary": "New API endpoint added without docs"
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 7a: Gemini Chat (Sub-node)
| ID | `gemini` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Uses Google Gemini API credential | [ ] | |
| Default options | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 8: Parse AI Response
| ID | `parse-response` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Handles ```json``` code blocks | [ ] | |
| Handles raw JSON | [ ] | |
| Fallback on parse failure | [ ] | confidence: 0.3 |
| Preserves config from Analyze Files | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 9: Has Doc Impact?
| ID | `has-impact` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `needs_doc_update === true` | [ ] | |
| AND: `confidence >= 0.6` | [ ] | 60% threshold |
| True → Post Review Comment | [ ] | |
| False → Log No Action | [ ] | |

**Threshold Verification**:
| Confidence | needs_doc_update | Result |
|------------|------------------|--------|
| 0.8 | true | Post comment |
| 0.5 | true | No action (low confidence) |
| 0.9 | false | No action (no impact) |

**Sign-off**: [ ] ________ Date: ________

---

### Node 10: Post Review Comment
| ID | `post-comment` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: PR Reviews API | [ ] | `/pulls/{pr_number}/reviews` |
| Method: POST | [ ] | |
| Event: COMMENT | [ ] | Not REQUEST_CHANGES |
| Body formatted with markdown | [ ] | |
| Uses Header Auth | [ ] | |

**Comment Template Verification**:
| Section | Included | Status |
|---------|----------|--------|
| Header (📚 Documentation Review) | [ ] | |
| Confidence percentage | [ ] | |
| AI summary | [ ] | |
| Affected docs list | [ ] | |
| Suggestions list | [ ] | |
| Footer attribution | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 11: Log No Action
| ID | `log-no-action` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Returns no_action status | [ ] | |
| Logs reason (low_confidence or no_doc_impact) | [ ] | |
| Includes PR details | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

## GitHub Webhook Setup (REQUIRED)

**⚠️ ACTION REQUIRED**: This workflow requires a GitHub webhook to function.

| Step | Status | Notes |
|------|--------|-------|
| Navigate to repo settings/hooks | [ ] | |
| Add new webhook | [ ] | |
| URL: `https://gitlitreview.app.n8n.cloud/webhook/pr-review` | [ ] | |
| Content type: application/json | [ ] | |
| Events: Pull requests | [ ] | opened, synchronize |
| Active: checked | [ ] | |

---

## Test Scenarios

### Scenario 1: Human PR with Code Changes
| Step | Expected | Status |
|------|----------|--------|
| Receive PR webhook | is_bot = false | [ ] |
| Get files | Code files returned | [ ] |
| Analyze | Code changed, no docs | [ ] |
| AI analysis | needs_doc_update = true | [ ] |
| Comment posted | Review visible on PR | [ ] |

### Scenario 2: Bot PR (Dependabot)
| Step | Expected | Status |
|------|----------|--------|
| Receive PR webhook | user.type = 'Bot' | [ ] |
| Is Human? | False | [ ] |
| Skip Bot PR | Logged and ended | [ ] |

### Scenario 3: PR Already Has Docs
| Step | Expected | Status |
|------|----------|--------|
| Get files | doc_files.length > 0 | [ ] |
| AI analysis | needs_doc_update = false | [ ] |
| No comment posted | Log No Action | [ ] |

### Scenario 4: Low Confidence
| Step | Expected | Status |
|------|----------|--------|
| AI says needs_doc = true | confidence = 0.4 | [ ] |
| Has Doc Impact? | False (< 0.6) | [ ] |
| No comment posted | reason: low_confidence | [ ] |

---

## Final Sign-Off

| Reviewer | Date | Status |
|----------|------|--------|
| | | |

**Workflow Approved**: [ ] Yes [ ] No

### Issues Found
| Node | Issue | Severity | Resolution |
|------|-------|----------|------------|
| | | | |

---

*Document Version: 1.0*  
*Created: 2024-12-24*
