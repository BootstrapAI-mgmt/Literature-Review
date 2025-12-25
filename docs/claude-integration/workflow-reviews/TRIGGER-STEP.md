# Doc Chain - Trigger: Step-Through Validation

> **Workflow ID**: `qQKXewWTby495ix7`  
> **Version**: TRIG-V001  
> **Total Nodes**: 10 (+ 1 AI sub-node)  
> **Last n8n Update**: 2025-12-23T17:16:04.951Z

---

## Checkout Status

| Field | Value |
|-------|-------|
| **Review Status** | 📋 Ready for Review |
| **Checked Out By** | - |
| **Checkout Time** | - |
| **Last Activity** | - |

---

## Flow Diagram

```
GitHub Webhook → Filter Valid Events → Parse Changes → Fetch Matrix
                                                           ↓
                                                    Find Affected Docs
                                                           ↓
                                                      Has Updates?
                                                    ↙          ↘
                                          Task Master      No Updates Needed
                                    (+ Gemini Model)
                                              ↓
                                      Parse AI Response
                                              ↓
                                      Send to Distributor
```

---

## Node-by-Node Validation

### Node 1: GitHub Webhook
| ID | `e2d89007-3cb2-45f6-9938-08c8bc618011` |
|----|-------|
| Type | `n8n-nodes-base.webhook` |
| Position | [-1344, 352] |

#### Configuration Check
| Item | Expected | Actual | Status | Reviewer |
|------|----------|--------|--------|----------|
| HTTP Method | POST | POST | [ ] | |
| Path | `github-doc-trigger` | `github-doc-trigger` | [ ] | |
| Webhook ID | Valid UUID | `c4c0f6f8-fc59-4fb4-bc61-ac1af114b726` | [ ] | |

#### Input Expectation
```json
{
  "body": {
    "ref": "refs/heads/main",
    "commits": [...],
    "head_commit": {...},
    "pusher": {...}
  }
}
```

#### Output Schema
```json
{
  "body": { /* GitHub webhook payload */ },
  "headers": {...},
  "query": {...}
}
```

#### Repository Alignment
| Check | Status | Notes |
|-------|--------|-------|
| URL accessible from GitHub | [ ] | `https://gitlitreview.app.n8n.cloud/webhook/github-doc-trigger` |
| Webhook configured in repo settings | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 2: Filter Valid Events
| ID | `557a8e03-2257-45e7-8ff0-bfd1bf82cbfe` |
|----|-------|
| Type | `n8n-nodes-base.code` |
| Position | [-1136, 352] |

#### Logic Validation
| Check | Status | Notes |
|-------|--------|-------|
| Filters `[n8n] docs:` commits | [ ] | Prevents feedback loops |
| Filters `[n8n] chore:` commits | [ ] | Prevents feedback loops |
| Allows `[n8n] fix:` commits | [ ] | Manual commits processed |
| Handles merged PRs | [ ] | `pull_request.merged === true` |
| Returns empty array for invalid events | [ ] | Stops workflow cleanly |

#### Input Expectation (from Node 1)
```json
{
  "body": {
    "commits": [...],
    "head_commit": { "message": "..." },
    "pusher": {...}
  }
}
```

#### Output Schema
```json
{
  "body": { /* original payload */ },
  "is_valid": true
}
```
*Or empty array `[]` if filtered out*

**Sign-off**: [ ] ________ Date: ________

---

### Node 3: Parse Changes
| ID | `b3e4c7b1-f1ba-49af-aad3-61f6213293a5` |
|----|-------|
| Type | `n8n-nodes-base.code` |
| Position | [-896, 256] |

#### Logic Validation
| Check | Status | Notes |
|-------|--------|-------|
| Accesses `.body` for GitHub data | [ ] | Critical: data is nested |
| Extracts added/modified files | [ ] | From all commits |
| Deduplicates files | [ ] | Uses `new Set()` |
| Excludes `documentation_matrix.json` | [ ] | Internal tracking file |
| Handles PR merge format | [ ] | `pull_request.merge_commit_sha` |

#### Output Schema
```json
{
  "commit_sha": "abc123...",
  "author": "username",
  "message": "commit message",
  "changed_files": ["docs/file1.md", "src/script.py"]
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 4: Fetch Matrix
| ID | `d61e4d5d-d7f1-4122-acd2-ebe54de8b481` |
|----|-------|
| Type | `n8n-nodes-base.httpRequest` |
| Position | [-672, 256] |

#### Configuration Check
| Item | Expected | Actual | Status | Reviewer |
|------|----------|--------|--------|----------|
| URL | Raw GitHub content | `https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/docs/documentation_matrix.json` | [ ] | |
| Method | GET (default) | GET | [ ] | |

#### Repository Alignment
| Check | Status | Notes |
|-------|--------|-------|
| File exists in repo | [ ] | Verify `docs/documentation_matrix.json` exists |
| JSON is valid | [ ] | |
| Contains `owner_domains` | [ ] | |
| Contains `documents` array | [ ] | |
| Contains `script_to_docs` mapping | [ ] | |

#### Output Schema
```json
{
  "data": "{ JSON string of matrix }"
}
```
*Note: Returns JSON as string, must be parsed*

**Sign-off**: [ ] ________ Date: ________

---

### Node 5: Find Affected Docs
| ID | `62ea2e36-3e63-46a7-a4af-c15065510c2e` |
|----|-------|
| Type | `n8n-nodes-base.code` |
| Position | [-448, 256] |

#### Logic Validation
| Check | Status | Notes |
|-------|--------|-------|
| Parses matrix from string | [ ] | `JSON.parse(matrixRaw.data)` |
| Handles old array format | [ ] | `owner_domains` as array |
| Handles new object format | [ ] | `owner_domains` with `.documents` |
| Maps script changes to docs | [ ] | Uses `script_to_docs` |
| Includes doc dependencies | [ ] | `depends_on` reverse lookup |
| Includes domain siblings | [ ] | Same owner's docs |
| Tracks new docs not in matrix | [ ] | `new_docs` array |
| Falls back to @docs domain | [ ] | For unmatched new docs |

#### Output Schema
```json
{
  "affected_docs": [
    { "path": "docs/README.md", "owner": "@core", "level": "L1" }
  ],
  "trigger": { /* from Parse Changes */ },
  "new_docs": ["docs/new-file.md"],
  "has_updates": true
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 6: Has Updates
| ID | `2a93a2bc-17f6-4da7-aced-44497a6e4fc5` |
|----|-------|
| Type | `n8n-nodes-base.if` |
| Position | [-224, 256] |

#### Configuration Check
| Item | Expected | Status | Reviewer |
|------|----------|--------|----------|
| Condition | `$json.has_updates === true` | [ ] | |
| True branch → Task Master | [ ] | |
| False branch → No Updates Needed | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 7: Task Master (AI Agent)
| ID | `7e888bd8-5869-4cc6-801c-aa363aabff9b` |
|----|-------|
| Type | `@n8n/n8n-nodes-langchain.agent` |
| Position | [0, 0] |

#### Configuration Check
| Item | Status | Notes |
|------|--------|-------|
| System message defines update types | [ ] | UPDATE_REFERENCE, UPDATE_INDEX, etc. |
| Task card awareness documented | [ ] | task-cards/*.md handling |
| Output format specified | [ ] | JSON with update_list_id, tasks |
| Uses Gemini Model sub-node | [ ] | Connected via ai_languageModel |

#### Expected Update Types
- [ ] `UPDATE_REFERENCE` - Cross-reference updates
- [ ] `UPDATE_INDEX` - Index/summary updates  
- [ ] `CASCADE_UPDATE` - Dependent doc updates
- [ ] `REVIEW_NEEDED` - Human review flags
- [ ] `STATUS_UPDATE` - Task card status
- [ ] `CHECKBOX_TOGGLE` - Task checkboxes
- [ ] `COMPLETION_PERCENTAGE` - Roadmap counts

#### Output Schema (AI-generated)
```json
{
  "update_list_id": "ul-2024-12-24-123456",
  "tasks": [
    {
      "task_id": "task-001",
      "document": "docs/README.md",
      "owner": "@core",
      "update_type": "UPDATE_REFERENCE",
      "description": "Update cross-references",
      "depends_on": [],
      "priority": 1
    }
  ]
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 7a: Gemini Model (Sub-node)
| ID | `1e4b422f-f8b9-49b9-a39f-2ece2ffd2e40` |
|----|-------|
| Type | `@n8n/n8n-nodes-langchain.lmChatGoogleGemini` |
| Position | [64, 224] |

#### Configuration Check
| Item | Status | Notes |
|------|--------|-------|
| Credential configured | [ ] | `Google Gemini(PaLM) Api account` |
| Model defaults used | [ ] | No custom options |

**Sign-off**: [ ] ________ Date: ________

---

### Node 8: Parse AI Response
| ID | `45a69aba-398f-40e3-9338-f102b4401245` |
|----|-------|
| Type | `n8n-nodes-base.code` |
| Position | [352, 112] |

#### Logic Validation
| Check | Status | Notes |
|-------|--------|-------|
| Extracts JSON from response | [ ] | Regex: `/\{[\s\S]*\}/` |
| Handles `.text` property | [ ] | |
| Handles `.output` property | [ ] | |
| Provides fallback on parse failure | [ ] | `ul-fallback` with empty tasks |

#### Output Schema
```json
{
  "update_list_id": "ul-...",
  "tasks": [...]
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 9: Send to Distributor
| ID | `a2f885ff-84c7-4932-a757-b73745a0b9a0` |
|----|-------|
| Type | `n8n-nodes-base.httpRequest` |
| Position | [576, 112] |

#### Configuration Check
| Item | Expected | Actual | Status | Reviewer |
|------|----------|--------|--------|----------|
| Method | POST | POST | [ ] | |
| URL | Distributor webhook | `https://gitlitreview.app.n8n.cloud/webhook/task-distributor` | [ ] | |
| Body | JSON passthrough | `={{ $json }}` | [ ] | |

#### Integration Check
| Check | Status | Notes |
|-------|--------|-------|
| URL matches Distributor webhook | [ ] | Cross-reference with DISTRIBUTOR-STEP.md |
| Body format matches Distributor input | [ ] | `update_list_id`, `tasks` array |

**Sign-off**: [ ] ________ Date: ________

---

### Node 10: No Updates Needed
| ID | `c6ccf5fd-0893-418f-86e4-dca2b5664686` |
|----|-------|
| Type | `n8n-nodes-base.noOp` |
| Position | [64, 400] |

#### Purpose
Terminal node for events with no documentation impact.

**Sign-off**: [ ] ________ Date: ________

---

## End-to-End Test Scenarios

### Scenario 1: Normal Push Event
| Step | Expected | Status |
|------|----------|--------|
| Receive webhook | Body contains commits | [ ] |
| Filter allows | Not [n8n] automated | [ ] |
| Parse extracts files | changed_files populated | [ ] |
| Matrix fetched | Valid JSON | [ ] |
| Docs found | affected_docs > 0 | [ ] |
| Tasks generated | Valid JSON with tasks | [ ] |
| Sent to Distributor | HTTP 200 | [ ] |

### Scenario 2: Automated [n8n] Commit
| Step | Expected | Status |
|------|----------|--------|
| Receive webhook | `[n8n] docs:` message | [ ] |
| Filter blocks | Returns empty array | [ ] |
| Workflow stops | No further processing | [ ] |

### Scenario 3: No Doc Impact
| Step | Expected | Status |
|------|----------|--------|
| Receive webhook | Valid commits | [ ] |
| Parse extracts files | Only non-doc files | [ ] |
| Matrix checked | No matches | [ ] |
| has_updates = false | Goes to No Updates Needed | [ ] |

---

## Final Sign-Off

| Reviewer | Date | Status | Notes |
|----------|------|--------|-------|
| | | | |

**Workflow Approved**: [ ] Yes [ ] No - Issues documented below

### Issues Found
| Node | Issue | Severity | Resolution |
|------|-------|----------|------------|
| | | | |

---

*Document Version: 1.0*  
*Created: 2024-12-24*
