# Doc Chain - PR Review: Step-Through Validation

> **Workflow ID**: `03ONuhFTJGDhmtJ9`  
> **Version**: PRR-V001 (Phase 4 New)  
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
                                ↓ (yes)           ↓ (no)
                          Get PR Files        Skip Bot PR
                                ↓
                          Analyze Files
                                ↓
                      AI Doc Impact Analysis (+ Gemini)
                                ↓
                        Parse AI Response
                                ↓
                         Has Doc Impact?
                        (≥60% confidence)
                      ↙                ↘
              Post Review Comment    Log No Action
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
| Expects GitHub PR webhook payload | [ ] | `opened`, `synchronize` events |

**⚠️ Prerequisite**: GitHub webhook must be configured:
- URL: `https://gitlitreview.app.n8n.cloud/webhook/pr-review`
- Events: Pull requests (opened, synchronize)
- Content type: application/json

**Sign-off**: [ ] ________ Date: ________

---

### Node 2: Configuration
| ID | `config` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Extracts pr_number | [ ] | From `pull_request.number` |
| Extracts pr_title | [ ] | |
| Extracts pr_author | [ ] | `user.login` |
| Extracts pr_action | [ ] | `opened`, `synchronize` |
| Sets repo_owner | [ ] | `BootstrapAI-mgmt` |
| Sets repo_name | [ ] | `Literature-Review` |
| Detects is_bot | [ ] | `user.type === 'Bot'` |

**Sign-off**: [ ] ________ Date: ________

---

### Node 3: Is Human PR?
| ID | `is-human` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `is_bot === false` | [ ] | |
| True → Get PR Files | [ ] | Human PRs processed |
| False → Skip Bot PR | [ ] | Dependabot, etc. skipped |

**Sign-off**: [ ] ________ Date: ________

---

### Node 4: Skip Bot PR
| ID | `skip-bot` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Returns skipped status | [ ] | |
| Logs pr_author | [ ] | For debugging |

**Sign-off**: [ ] ________ Date: ________

---

### Node 5: Get PR Files
| ID | `get-files` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: PR Files API | [ ] | `/pulls/{pr_number}/files` |
| Uses Header Auth | [ ] | Not hardcoded |
| Returns file list | [ ] | Array of file objects |

**Sign-off**: [ ] ________ Date: ________

---

### Node 6: Analyze Files
| ID | `analyze-files` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Categorizes code files | [ ] | py, js, ts, jsx, tsx, java, go, rs |
| Categorizes doc files | [ ] | docs/*, *.md, *.rst |
| Categorizes config files | [ ] | json, yaml, yml, toml, ini, env |
| Includes patch (truncated) | [ ] | First 500 chars for AI context |
| Preserves config from previous node | [ ] | `...config` spread |

**Output Schema**:
```json
{
  "pr_number": 123,
  "pr_title": "...",
  "total_files": 5,
  "code_files": [{ "path": "...", "status": "modified", "changes": 42, "patch": "..." }],
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
| System message defines role | [ ] | Documentation impact analyzer |
| Prompt includes file categories | [ ] | Code, docs, config |
| Prompt includes code patches | [ ] | First 3 files |
| Expects JSON response | [ ] | Specified format |
| Uses Gemini sub-node | [ ] | |

**AI Considerations Verified**:
- [ ] New features needing docs
- [ ] Changed behavior
- [ ] Removed functionality
- [ ] Config changes
- [ ] Existing doc coverage

**Expected AI Output**:
```json
{
  "needs_doc_update": true,
  "confidence": 0.8,
  "affected_docs": ["docs/API.md", "README.md"],
  "suggestions": ["Add section for new endpoint"],
  "summary": "New API endpoint added without documentation"
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 7a: Gemini Chat (Sub-node)
| ID | `gemini` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Credential configured | [ ] | Google Gemini API |

**Sign-off**: [ ] ________ Date: ________

---

### Node 8: Parse AI Response
| ID | `parse-response` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Handles ```json code blocks | [ ] | Regex extraction |
| Handles raw JSON | [ ] | Fallback regex |
| Provides default on parse failure | [ ] | needs_doc_update: false |
| Preserves config from Analyze Files | [ ] | `...config` spread |

**Sign-off**: [ ] ________ Date: ________

---

### Node 9: Has Doc Impact?
| ID | `has-impact` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: needs_doc_update AND confidence ≥ 0.6 | [ ] | Threshold prevents false positives |
| True → Post Review Comment | [ ] | |
| False → Log No Action | [ ] | |

**Threshold Logic**:
- 60% confidence = moderate certainty
- Prevents spam on uncertain analysis
- Errs on side of not commenting

**Sign-off**: [ ] ________ Date: ________

---

### Node 10: Post Review Comment
| ID | `post-comment` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: PR Reviews API | [ ] | `/pulls/{pr_number}/reviews` |
| Method: POST | [ ] | |
| Event: COMMENT | [ ] | Not APPROVE or REQUEST_CHANGES |
| Body includes confidence % | [ ] | |
| Body includes affected docs | [ ] | |
| Body includes suggestions | [ ] | |
| Uses Header Auth | [ ] | |

**Comment Template Verification**:
| Section | Included | Status |
|---------|----------|--------|
| 📚 Header | [ ] | |
| AI confidence | [ ] | |
| Summary | [ ] | |
| Affected docs list | [ ] | |
| Numbered suggestions | [ ] | |
| Footer attribution | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 11: Log No Action
| ID | `log-no-action` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Returns status: no_action | [ ] | |
| Returns reason | [ ] | `low_confidence` or `no_doc_impact` |
| Logs pr details | [ ] | For debugging |

**Sign-off**: [ ] ________ Date: ________

---

## GitHub Webhook Setup Required

| Check | Status | Notes |
|-------|--------|-------|
| Webhook URL configured | [ ] | `https://gitlitreview.app.n8n.cloud/webhook/pr-review` |
| Content-Type: application/json | [ ] | |
| Events: Pull requests | [ ] | |
| Active: Yes | [ ] | |

---

## Test Scenarios

### Scenario 1: Human PR with Code Changes
| Step | Expected | Status |
|------|----------|--------|
| PR opened by human | is_bot = false | [ ] |
| Files fetched | Array of files | [ ] |
| Files analyzed | code_files > 0 | [ ] |
| AI analyzes | JSON response | [ ] |
| High confidence + needs update | Comment posted | [ ] |

### Scenario 2: Bot PR (Dependabot)
| Step | Expected | Status |
|------|----------|--------|
| PR from dependabot[bot] | is_bot = true | [ ] |
| Skipped | No further processing | [ ] |

### Scenario 3: Low Confidence Analysis
| Step | Expected | Status |
|------|----------|--------|
| AI returns confidence < 0.6 | Goes to Log No Action | [ ] |
| No comment posted | Avoids spam | [ ] |

### Scenario 4: PR Already Has Docs
| Step | Expected | Status |
|------|----------|--------|
| PR includes doc files | AI sees docs_included | [ ] |
| AI determines adequate | needs_doc_update: false | [ ] |
| No comment posted | [ ] | |

---

## Final Sign-Off

| Reviewer | Date | Status |
|----------|------|--------|
| | | |

**Workflow Approved**: [ ] Yes [ ] No

---

*Document Version: 1.0*  
*Created: 2024-12-24*
