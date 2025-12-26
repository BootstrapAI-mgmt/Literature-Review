# Workflow Issues Tracker
**Last Updated:** 2025-12-26T09:20:00Z

---

## Open Issues

### ISSUE-001: State Reconciliation AI Correction Pipeline
| Field | Value |
|-------|-------|
| **Workflow** | Doc Chain - State Reconciliation |
| **Workflow ID** | JVAjIrsS4yKbYIxW |
| **Severity** | Medium |
| **Status** | 🔴 Open |
| **Discovered** | 2025-12-25 |

**Symptom:**
- Mismatch detection working (5 mismatches found)
- AI correction generation produces 0 tasks dispatched

**Impact:**
- Core detection functionality: ✅ Working
- Auto-remediation: ❌ Not functioning
- Manual review still required for corrections

**Root Cause Hypothesis:**
1. Gemini AI response not parsing correctly in "Clean AI Output" node
2. Task validation in "Prepare for Distributor" filtering all tasks
3. AI generating empty or malformed JSON

**Investigation Steps:**
1. [ ] Open n8n UI and examine execution details for the live test
2. [ ] Check "Generate Corrections" node output
3. [ ] Check "Clean AI Output" node - is it throwing errors?
4. [ ] Check "Prepare for Distributor" - what's in `validTasks`?
5. [ ] Test with modified AI prompt if needed

**Workaround:**
Manual review of mismatch detection output until fixed.

---

### ISSUE-002: Exposed GitHub Token in Agent Workflow
| Field | Value |
|-------|-------|
| **Workflow** | Doc Chain - Agent |
| **Workflow ID** | 5vQ8lMCyatxB8Fdd |
| **Severity** | 🔴 CRITICAL |
| **Status** | 🟢 Resolved |
| **Discovered** | 2025-12-25 |
| **Resolved** | 2025-12-26 |

**Symptom:**
- GitHub Personal Access Token exposed in workflow nodes array
- Token visible in: Get File SHA, Commit to GitHub, Fetch Matrix, Commit Matrix Update
- Token format: `ghp_****REDACTED****` (40 char PAT)

**Resolution:**
- ✅ GitHub PAT rotated on 2025-12-26
- ✅ New token configured in n8n credentials
- ✅ activeVersion correctly uses `{{ env.GITHUB_TOKEN }}`

---

## Resolved Issues

### ISSUE-002 (Resolved 2025-12-26)
See above - GitHub PAT rotated successfully.

---

## Issue Template
```markdown
### ISSUE-XXX: [Title]
| Field | Value |
|-------|-------|
| **Workflow** | [Name] |
| **Workflow ID** | [ID] |
| **Severity** | High/Medium/Low |
| **Status** | 🔴 Open / 🟡 In Progress / 🟢 Resolved |
| **Discovered** | [Date] |

**Symptom:**
[What's happening]

**Impact:**
[What's affected]

**Root Cause:**
[Why it's happening]

**Fix:**
[How to resolve]
```
