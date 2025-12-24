# Doc Chain - Trigger Workflow Review

> **Workflow ID:** qQKXewWTby495ix7  
> **Status:** ✅ Active  
> **Version:** TRIGGER-V001  
> **Last Updated:** 2025-12-23T17:16:04.951Z

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

Receives GitHub webhook events on repository pushes, filters out automated commits, identifies affected documents using `documentation_matrix.json`, generates update tasks via Gemini AI, and dispatches task lists to the Distributor.

---

## Node-by-Node Validation

### Node 1: GitHub Webhook
| Check | Status | Notes |
|-------|--------|-------|
| Webhook URL correct | [ ] | `POST /webhook/github-doc-trigger` |
| HTTP Method: POST | [ ] | |
| Response mode configured | [ ] | |

**Parameters:**
```json
{
  "httpMethod": "POST",
  "path": "github-doc-trigger",
  "options": {}
}
```

---

### Node 2: Filter Valid Events
| Check | Status | Notes |
|-------|--------|-------|
| Filters push events | [ ] | Requires `body.commits` array |
| Excludes empty commits | [ ] | |
| Excludes n8n automated commits | [ ] | `[n8n] docs:`, `[n8n] chore:` |

**Logic:**
- Returns: `!commitMessage.startsWith('[n8n] docs:') && !commitMessage.startsWith('[n8n] chore:')`
- Purpose: Prevents infinite loop from Agent's commits

---

### Node 3: Parse Changes
| Check | Status | Notes |
|-------|--------|-------|
| Extracts commit data | [ ] | `sha`, `message`, `timestamp` |
| Collects modified files | [ ] | `.added`, `.modified`, `.removed` |
| Handles multiple commits | [ ] | Merges all file arrays |

**Output Schema:**
```javascript
{
  commits: [...],
  allFiles: { added: [], modified: [], removed: [] },
  branch: "main"
}
```

---

### Node 4: Fetch Matrix
| Check | Status | Notes |
|-------|--------|-------|
| Correct URL | [ ] | `https://raw.githubusercontent.com/.../documentation_matrix.json` |
| Response format: JSON | [ ] | |
| Error handling | [ ] | |

**URL:** `https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/docs/documentation_matrix.json`

---

### Node 5: Find Affected Docs
| Check | Status | Notes |
|-------|--------|-------|
| Matches files to matrix entries | [ ] | By path |
| Identifies dependencies | [ ] | `depends_on` field |
| Handles new docs not in matrix | [ ] | Infers domain from path |
| Excludes matrix file itself | [ ] | |

**Key Logic:**
- New docs: Creates entry with inferred `owner` from path (e.g., `docs/api/` → `@api`)
- Cascade: Collects documents that `depend_on` modified files

---

### Node 6: Has Updates (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition correct | [ ] | `affectedDocs.length > 0` |
| True → Task Master | [ ] | |
| False → No Updates Needed | [ ] | |

---

### Node 7: Task Master (AI Agent)
| Check | Status | Notes |
|-------|--------|-------|
| Uses Gemini model | [ ] | Credential: `kJmLsDFHzgrlPJhY` |
| System prompt complete | [ ] | Task types defined |
| Output format: JSON | [ ] | |

**Task Types Generated:**
- `UPDATE_REFERENCE` - Update doc references
- `UPDATE_INDEX` - Update index/README files
- `CASCADE_UPDATE` - Propagate changes to dependents
- `REVIEW_NEEDED` - Flag for human review
- `STATUS_UPDATE` - Update status fields
- `CHECKBOX_TOGGLE` - Toggle task checkboxes
- `COMPLETION_PERCENTAGE` - Recalculate completion %

**Output Schema:**
```json
{
  "update_list_id": "ul-...",
  "tasks": [
    {
      "task_id": "...",
      "document": "path/to/doc.md",
      "update_type": "UPDATE_REFERENCE",
      "description": "...",
      "depends_on": [],
      "priority": 1
    }
  ]
}
```

---

### Node 8: Gemini Model
| Check | Status | Notes |
|-------|--------|-------|
| Credential valid | [ ] | `Google Gemini(PaLM) Api account` |
| Connected to Task Master | [ ] | `ai_languageModel` connection |

---

### Node 9: Parse AI Response
| Check | Status | Notes |
|-------|--------|-------|
| Extracts JSON from response | [ ] | Greedy match `{...}` |
| Handles markdown code blocks | [ ] | Strips ` ```json ``` ` |
| Error fallback | [ ] | Empty tasks array |

---

### Node 10: Send to Distributor
| Check | Status | Notes |
|-------|--------|-------|
| Correct URL | [ ] | `https://gitlitreview.app.n8n.cloud/webhook/task-distributor` |
| HTTP Method: POST | [ ] | |
| Body format: JSON | [ ] | |

**Request Body:**
```json
{
  "update_list_id": "...",
  "source": "github-trigger",
  "trigger": { "type": "push", "commits": [...] },
  "tasks": [...]
}
```

---

### Node 11: No Updates Needed
| Check | Status | Notes |
|-------|--------|-------|
| Terminal node | [ ] | No-op |
| Logs appropriately | [ ] | |

---

## Connection Validation

| From Node | To Node | Type | Status |
|-----------|---------|------|--------|
| GitHub Webhook | Filter Valid Events | main | [ ] |
| Filter Valid Events | Parse Changes | main | [ ] |
| Parse Changes | Fetch Matrix | main | [ ] |
| Fetch Matrix | Find Affected Docs | main | [ ] |
| Find Affected Docs | Has Updates | main | [ ] |
| Has Updates (true) | Task Master | main | [ ] |
| Has Updates (false) | No Updates Needed | main | [ ] |
| Gemini Model | Task Master | ai_languageModel | [ ] |
| Task Master | Parse AI Response | main | [ ] |
| Parse AI Response | Send to Distributor | main | [ ] |

---

## Input/Output Schema Verification

### Expected Webhook Input (GitHub Push)
```json
{
  "ref": "refs/heads/main",
  "commits": [
    {
      "id": "abc123",
      "message": "Update documentation",
      "timestamp": "2025-12-24T00:00:00Z",
      "added": ["docs/new-file.md"],
      "modified": ["docs/existing.md"],
      "removed": []
    }
  ]
}
```

### Expected Distributor Output
```json
{
  "update_list_id": "ul-1703376000-abc123",
  "source": "github-trigger",
  "trigger": {
    "type": "push",
    "commits": [...],
    "message": "Update documentation"
  },
  "tasks": [
    {
      "task_id": "task-001",
      "document": "docs/existing.md",
      "update_type": "UPDATE_REFERENCE",
      "description": "Update references to new-file.md",
      "priority": 1
    }
  ]
}
```

---

## Issues Found

| # | Severity | Description | Recommendation |
|---|----------|-------------|----------------|
| 1 | - | - | - |

---

## Sign-off

- [ ] All nodes validated
- [ ] All connections verified
- [ ] Input/output schemas confirmed
- [ ] No critical issues found

**Reviewer:** ________________________  
**Date:** ________________________  
**Signature:** ________________________
