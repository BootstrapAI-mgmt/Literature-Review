# Core Chain Validation Report
**Date:** 2025-12-25
**Workflows:** Trigger → Distributor → Agent
**Status:** 🔴 CRITICAL - Security Issue Found

---

## 🚨 CRITICAL SECURITY FINDING

### ISSUE-002: Exposed GitHub Token in Agent Workflow

**Severity:** 🔴 CRITICAL
**Workflow:** Doc Chain - Agent (5vQ8lMCyatxB8Fdd)
**Location:** Current nodes array (not activeVersion)

**Problem:**
The workflow's `nodes` array contains hardcoded GitHub PAT:
- Node: "Get File SHA" - Authorization header: `ghp_i27OnHGN7...`
- Node: "Commit to GitHub" - Authorization header: `ghp_i27OnHGN7...`
- Node: "Fetch Matrix" - Authorization header: `ghp_i27OnHGN7...`
- Node: "Commit Matrix Update" - Authorization header: `ghp_i27OnHGN7...`

**Note:** The `activeVersion` correctly uses `Bearer {{ env.GITHUB_TOKEN }}` but the current edits expose the raw token.

**Immediate Action Required:**
1. Rotate the exposed GitHub PAT immediately
2. Update n8n workflow to use only `{{ env.GITHUB_TOKEN }}`
3. Publish new version to ensure activeVersion is current

---

## Workflow Summary

| Workflow | ID | Nodes | Status | Auth Method |
|----------|-----|-------|--------|-------------|
| Trigger | qQKXewWTby495ix7 | 11 | ✅ Active | None (public API) |
| Distributor | 3lTsmIsQFmzpwLE8 | 24 (mixed) | ✅ Active | None (internal) |
| Agent | 5vQ8lMCyatxB8Fdd | 14 | 🔴 EXPOSED | Hardcoded PAT |

---

## Trigger Workflow Analysis

**ID:** qQKXewWTby495ix7
**Nodes:** 11
**Flow:**
```
GitHub Webhook → Filter Valid Events → Parse Changes → Fetch Matrix
                                          ↓
                 ← Task Master (AI) ← Find Affected Docs
                                          ↓
              Parse AI Response → Send to Distributor
                                  (or No Updates Needed)
```

### Key Features
- **Feedback Loop Prevention:** Filters `[n8n] docs:` and `[n8n] chore:` commits
- **AI Task Generation:** Uses Gemini to create task lists
- **Domain Awareness:** Supports owner domains from documentation_matrix.json

### Validation Checks
| Check | Status | Notes |
|-------|--------|-------|
| Webhook path | ✅ | `/github-doc-trigger` |
| Commit filter logic | ✅ | Prevents infinite loops |
| Matrix fetch | ✅ | Uses raw.githubusercontent.com |
| AI response parsing | ✅ | JSON extraction with fallback |
| Distributor URL | ✅ | Points to correct webhook |

---

## Distributor Workflow Analysis

**ID:** 3lTsmIsQFmzpwLE8
**Nodes:** 24 (mixed old/new patterns)
**Architecture:** Dual-mode (simplified + legacy)

### Entry Points
1. `Receive List` → Simplified queue-based dispatch
2. `Load State` → Legacy list-based processing
3. `Receive Callback` → Task completion handling
4. `Get Status` → State inspection endpoint
5. `Reset State` → State reset endpoint

### Simplified Pattern (Active)
```
Receive List → Queue and Dispatch First → Should Dispatch?
                                              ↓ (yes)
                                       Dispatch to Agent
```

### Legacy Pattern (Still Connected)
```
Load State → Add To Queue → Should Process → Pop Next List
                                                ↓
Get Runnable Tasks → Has Runnable → Prepare Agent Payload
                                              ↓
                    Dispatch to Agent-old → Wait for Callback
                                              ↓
                    Update Task Status → All Done → Finalize List
```

### Validation Checks
| Check | Status | Notes |
|-------|--------|-------|
| Stale task recovery | ✅ | 10-minute timeout |
| Deduplication | ✅ | Document-level |
| Callback handling | ✅ | Task completion |
| State management | ⚠️ | Dual patterns may conflict |

---

## Agent Workflow Analysis

**ID:** 5vQ8lMCyatxB8Fdd
**Nodes:** 14
**Flow:**
```
Receive Task → Parse Webhook Data → Fetch Document → Update Document (AI)
                                                          ↓
          ← Changes Needed? ← Parse AI Output
          ↓ (yes)                    ↓ (no)
     Get File SHA                Fetch Matrix
          ↓                          ↓
     Prepare Commit          Update Review Tracking
          ↓                          ↓
  Commit to GitHub           Commit Matrix Update
          ↓                          ↓
     Fetch Matrix ─────────→ Send Callback
```

### Key Features
- **Document Normalization:** Handles both `document` and `target` field names
- **Review Tracking:** Updates last_reviewed and next_review dates
- **Commit Prefix:** Uses `[n8n] docs:` and `[n8n] chore:` to prevent loops

### Validation Checks
| Check | Status | Notes |
|-------|--------|-------|
| Webhook path | ✅ | `/domain-agent` |
| Task parsing | ✅ | Handles JSON strings |
| AI integration | ✅ | Gemini + JSON output |
| GitHub auth | 🔴 | **EXPOSED TOKEN** |
| Callback URL | ✅ | Points to Distributor |

---

## Cross-Workflow Integration

### Data Flow Validation
```
Trigger                    Distributor                 Agent
   │                           │                         │
   ├─ update_list_id ─────────→│                         │
   ├─ tasks[] ────────────────→│                         │
   │                           ├─ task ─────────────────→│
   │                           ├─ list_id ──────────────→│
   │                           ├─ trigger ──────────────→│
   │                           │                         │
   │                           │←──── task_id ───────────┤
   │                           │←──── status ────────────┤
```

### Field Compatibility
| Field | Trigger | Distributor | Agent | Status |
|-------|---------|-------------|-------|--------|
| update_list_id | ✅ Produces | ✅ Consumes | ✅ Passes | ✅ |
| tasks[] | ✅ Produces | ✅ Consumes | ✅ Consumes | ✅ |
| task_id | ✅ In tasks | ✅ Tracks | ✅ Callbacks | ✅ |
| document/target | ✅ Uses document | ✅ Passes | ✅ Normalizes | ✅ |

---

## Action Items

### Immediate (Today)
- [ ] **CRITICAL:** Rotate exposed GitHub PAT
- [ ] Update Agent workflow to use only env.GITHUB_TOKEN
- [ ] Publish new Agent workflow version

### Short-term
- [ ] Clean up Distributor dual-pattern architecture
- [ ] Add error handling for failed GitHub commits
- [ ] Test end-to-end flow with live commit

### Documentation
- [ ] Update ISSUES-TRACKER.md with ISSUE-002
- [ ] Document credential rotation procedure
