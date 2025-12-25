# Doc Chain - Agent: Step-Through Validation

> **Workflow ID**: `5vQ8lMCyatxB8Fdd`  
> **Version**: AGENT-V001  
> **Total Nodes**: 14 (including AI sub-node)  
> **Last n8n Update**: 2025-12-24T15:00:26.856Z

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
Receive Task → Parse Webhook Data → Fetch Document → Update Document (AI)
                                                            ↓
                                                     Parse AI Output
                                                            ↓
                                                     Changes Needed?
                                              ↙ (yes)              ↘ (no)
                                    Get File SHA              Fetch Matrix
                                         ↓                         ↓
                                   Prepare Commit          Update Review Tracking
                                         ↓                         ↓
                                  Commit to GitHub         Commit Matrix Update
                                         ↓                         ↓
                                    Fetch Matrix ─────────→ Send Callback
                                         ↓
                               Update Review Tracking
                                         ↓
                               Commit Matrix Update
                                         ↓
                                   Send Callback
```

---

## Node-by-Node Validation

### Node 1: Receive Task
| ID | `d5bb5a1f-8a79-4e13-8ab5-13722c1399b1` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Path: `domain-agent` | [ ] | |
| Method: POST | [ ] | |
| Matches Distributor's dispatch URL | [ ] | Cross-ref DISTRIBUTOR-STEP.md |

**Expected Input**:
```json
{
  "body": {
    "task": "{\"task_id\":\"...\",\"document\":\"...\",\"description\":\"...\"}",
    "list_id": "\"ul-...\"",
    "trigger": "{\"message\":\"...\"}"
  }
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 2: Parse Webhook Data
| ID | `d9267d29-7aae-45cb-9676-a5215d723672` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Parses JSON string `task` | [ ] | Distributor sends stringified |
| Parses JSON string `trigger` | [ ] | |
| Cleans `list_id` quotes | [ ] | Removes extra quotes |
| Normalizes `target` → `document` | [ ] | State Recon uses `target` |
| Handles already-parsed objects | [ ] | Checks `typeof` first |

**Output Schema**:
```json
{
  "task": { "task_id": "...", "document": "docs/README.md", "description": "..." },
  "trigger": { "message": "commit message" },
  "list_id": "ul-2024-12-24"
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 3: Fetch Document
| ID | `3d769c13-f25f-44d4-8a18-2dec9b46c97b` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL template correct | [ ] | `raw.githubusercontent.com/.../main/` + document |
| Response format: text | [ ] | Not JSON |
| Repo: BootstrapAI-mgmt/Literature-Review | [ ] | |
| Branch: main | [ ] | |

**Repository Alignment**:
| Check | Status | Notes |
|-------|--------|-------|
| Can fetch existing docs | [ ] | Test with known doc path |
| Returns 404 for missing | [ ] | Error handling needed? |

**Sign-off**: [ ] ________ Date: ________

---

### Node 4: Update Document (AI Agent)
| ID | `4ec71404-fa1a-4f5c-bcb1-7731cc645672` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| References `$('Parse Webhook Data')` | [ ] | Not $input |
| System message defines doc types | [ ] | Regular, Task Cards, Roadmaps |
| Output format specified | [ ] | JSON with changes_needed, updated_content |
| Uses Gemini Model sub-node | [ ] | Connected via ai_languageModel |

**Expected Update Types**:
- [ ] `PROSE` - Regular documentation updates
- [ ] `STATUS` - Task card status field changes
- [ ] `CHECKBOX` - Task card checkbox toggles
- [ ] `PERCENTAGE` - Completion percentage updates

**Output Schema (AI-generated)**:
```json
{
  "changes_needed": true,
  "updated_content": "# Full document content...",
  "summary": "Updated cross-references",
  "update_type": "PROSE"
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 4a: Gemini Model (Sub-node)
| ID | `36b1e4e2-fb31-438f-ab62-180cbc8864b2` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Credential: Google Gemini API | [ ] | |
| Default options | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 5: Parse AI Output
| ID | `bdfe8767-2578-432b-90de-5815456f94d7` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Extracts JSON with greedy regex | [ ] | `/\{[\s\S]*\}/` |
| Handles `.text` property | [ ] | |
| Handles `.output` property | [ ] | |
| Fallback on parse failure | [ ] | `changes_needed: false` |
| Attaches task_id from webhook | [ ] | For callback |
| Attaches document path | [ ] | For commit |

**Sign-off**: [ ] ________ Date: ________

---

### Node 6: Changes Needed
| ID | `f4e2007d-6532-4272-92ac-7f66a8dc1a32` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `$json.changes_needed === true` | [ ] | Strict boolean |
| True → Get File SHA | [ ] | Document update path |
| False → Fetch Matrix | [ ] | Skip commit, just update tracking |

**Sign-off**: [ ] ________ Date: ________

---

### Node 7: Get File SHA
| ID | `b7283f50-cc25-4994-b388-c163942ced12` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: GitHub Contents API | [ ] | `/repos/.../contents/{document}` |
| Auth header present | [ ] | ⚠️ Check if hardcoded or env var |
| Returns SHA for update | [ ] | Required for PUT |

**⚠️ Security Note**: Verify authorization uses environment variable, not hardcoded token.

**Sign-off**: [ ] ________ Date: ________

---

### Node 8: Prepare Commit
| ID | `f3bfd720-69ff-4ec4-8e65-8dbf91b05d7c` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Base64 encodes content | [ ] | Required for GitHub API |
| Sanitizes summary | [ ] | Removes special chars |
| Limits message length | [ ] | 68 chars max |
| Prefixes with `[n8n] docs:` | [ ] | **CRITICAL**: Loop prevention |

**Output Schema**:
```json
{
  "commit_message": "[n8n] docs: Updated cross-references",
  "commit_content": "base64...",
  "commit_sha": "abc123..."
}
```

**Sign-off**: [ ] ________ Date: ________

---

### Node 9: Commit to GitHub
| ID | `7ff86ca9-f027-4600-9950-c13692479da4` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Method: PUT | [ ] | Update existing file |
| URL: Contents API | [ ] | `/repos/.../contents/{document}` |
| Body: message, content, sha | [ ] | |
| Auth header present | [ ] | ⚠️ Check if env var |

**Sign-off**: [ ] ________ Date: ________

---

### Node 10: Fetch Matrix
| ID | `80360815-6e06-47bd-8580-2d1112598481` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: `documentation_matrix.json` | [ ] | Via Contents API |
| Returns base64 content | [ ] | Must decode |
| Returns SHA | [ ] | For update commit |

**Repository Alignment**:
| Check | Status | Notes |
|-------|--------|-------|
| File exists: `docs/documentation_matrix.json` | [ ] | |
| Valid JSON structure | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 11: Update Review Tracking
| ID | `4e6aa9ed-ce5e-4f9e-9f7b-ea0d0227bdad` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Decodes matrix from base64 | [ ] | |
| Finds document in matrix | [ ] | By path |
| Updates `last_reviewed` | [ ] | Today's date |
| Calculates `next_review` | [ ] | Based on `review_interval_days` |
| Updates `last_updated` if changed | [ ] | Only if changes_needed |
| Sets `status: 'current'` | [ ] | If changes made |
| Re-encodes to base64 | [ ] | For commit |
| Sanitizes callback summary | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Node 12: Commit Matrix Update
| ID | `cf614e9e-a531-4a86-8d6b-4a96fb365d50` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Method: PUT | [ ] | |
| Message: `[n8n] chore:` prefix | [ ] | **CRITICAL**: Loop prevention |
| onError: continueRegularOutput | [ ] | Don't fail on matrix conflict |

**Sign-off**: [ ] ________ Date: ________

---

### Node 13: Send Callback
| ID | `b6e946a6-2686-481e-a86b-6e681b6f76d0` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: `/webhook/task-callback` | [ ] | Distributor callback endpoint |
| Method: POST | [ ] | |
| Body: task_id, status, result | [ ] | |
| References `$('Update Review Tracking')` | [ ] | Gets callback_status |
| onError: continueRegularOutput | [ ] | Don't fail on callback error |

**Integration Check**:
| This Workflow | Connects To | Status |
|---------------|-------------|--------|
| Send Callback | Distributor → Receive Callback | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

## Loop Prevention Verification

| Commit Type | Prefix | Filtered By |
|-------------|--------|-------------|
| Document update | `[n8n] docs:` | Trigger → Filter Valid Events |
| Matrix update | `[n8n] chore:` | Trigger → Filter Valid Events |

**Verify in TRIGGER-STEP.md**: Filter Valid Events checks for these prefixes.

---

## Test Scenarios

### Scenario 1: Document Needs Update
| Step | Expected | Status |
|------|----------|--------|
| Receive task for stale doc | Parsed correctly | [ ] |
| Fetch current content | Raw markdown returned | [ ] |
| AI determines changes needed | `changes_needed: true` | [ ] |
| Get SHA, prepare, commit | New commit created | [ ] |
| Matrix updated | `last_reviewed` set | [ ] |
| Callback sent | status: completed | [ ] |

### Scenario 2: No Changes Needed
| Step | Expected | Status |
|------|----------|--------|
| AI determines no changes | `changes_needed: false` | [ ] |
| Skips document commit | Goes to Fetch Matrix | [ ] |
| Matrix still updated | `last_reviewed` set | [ ] |
| Callback sent | status: completed | [ ] |

### Scenario 3: Document Not in Matrix
| Step | Expected | Status |
|------|----------|--------|
| Process doc not in matrix | Continues | [ ] |
| Matrix find returns null | No update to doc entry | [ ] |
| Matrix `last_updated` still set | [ ] | |

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
