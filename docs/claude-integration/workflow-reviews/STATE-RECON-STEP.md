# Doc Chain - State Reconciliation: Step-Through Validation

> **Workflow ID**: `JVAjIrsS4yKbYIxW`  
> **Version**: STATE-V001  
> **Total Nodes**: 28 (including AI sub-node)  
> **Last n8n Update**: 2025-12-24T14:58:58.192Z

---

## Checkout Status

| Field | Value |
|-------|-------|
| **Review Status** | 📋 Ready for Review |
| **Checked Out By** | - |
| **Checkout Time** | - |

---

## Flow Diagram (Simplified)

```
┌─ Daily Check (3 AM) ─┐
│                      ├→ Start → Workflow Configuration → List All Files
└─ Manual Trigger ─────┘                                         │
                                                    ┌────────────┴────────────┐
                                                    ↓                         ↓
                                           Filter Task Cards         Filter Status Reports
                                                    ↓                         ↓
                                           Process Each Card    Has Reports? → Process Each Report
                                              (loop)                             (loop)
                                                    ↓                         ↓
                                           Aggregate Card Status    Aggregate Report Status
                                                    └────────┬────────────────┘
                                                             ↓
                                                   Merge Aggregated Data
                                                             ↓
                                                   Prepare Target Fetch
                                               ┌─────────┼─────────┐
                                               ↓         ↓         ↓
                                         Fetch Readme  Index   Roadmap
                                               └─────────┼─────────┘
                                                         ↓
                                                Find All Mismatches
                                                         ↓
                                                  Has Mismatches?
                                          (yes) ↓              ↓ (no)
                                       Format AI Prompt    Log in Sync
                                              ↓
                                      Generate Corrections (AI)
                                              ↓
                                        Clean AI Output
                                              ↓
                                     Prepare for Distributor
                                              ↓
                                          Has Tasks?
                                              ↓ (yes)
                                       Send Corrections → Summary Report
```

---

## Node-by-Node Validation

### Trigger Section

#### Node 1: Daily Check
| ID | `036eb768-aeb0-4245-9b65-743f08929082` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Type: Schedule Trigger | [ ] | |
| Time: 3 AM daily | [ ] | `triggerAtHour: 3` |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 2: Manual Trigger
| ID | `1e053bfa-77b7-4d63-94c5-a17d6002358a` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Path: `/state-reconciliation` | [ ] | |
| Method: POST | [ ] | |
| Response mode: lastNode | [ ] | Returns final result |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 3: Start (Merge)
| ID | `9b3a4f0d-cfac-4ba1-bc89-eec082a00e39` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Merges both triggers | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### Configuration Section

#### Node 4: Workflow Configuration
| ID | `29a5393b-2a11-46f6-bd87-867172e7d21c` |
|----|-------|

| Configuration Item | Value | Status |
|--------------------|-------|--------|
| Reconciliation targets | README.md, INDEX.md, CONSOLIDATED_ROADMAP.md | [ ] |
| Status patterns defined | task_status, completion_pct, checkboxes, etc. | [ ] |
| Status mappings | Complete, In Progress, Not Started, Blocked, Deferred | [ ] |
| Mismatch tolerance | 5% | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

### Data Collection Section

#### Node 5: List All Files
| ID | `71979f1d-1b4f-4c9d-bc70-c78c290a9ea7` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: Git Trees API | [ ] | `?recursive=1` |
| Returns full repo tree | [ ] | |
| ⚠️ Auth header check | [ ] | Verify env var vs hardcoded |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 6: Filter Task Cards
| ID | `c26587cd-2f18-4a42-9fa9-13499c735b2e` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Filters to `task-cards/*.md` | [ ] | |
| Excludes README.md, INDEX.md | [ ] | |
| Returns array for loop | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 7: Process Each Task Card (Loop)
| ID | `69aabe99-4b70-4832-abf4-4114deb1353f` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Type: splitInBatches | [ ] | |
| Reset: false | [ ] | Continues accumulating |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 8: Fetch Card Content
| ID | `0dd55a5f-4dee-4b2f-8ec6-7bb16194982a` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: Contents API | [ ] | Dynamic path |
| onError: continueRegularOutput | [ ] | Doesn't break loop |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 9: Parse Card Status
| ID | `007e5cde-955a-4f3a-b672-a014ba0ae7b5` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Decodes base64 content | [ ] | |
| Extracts Status field | [ ] | Pattern matching |
| Normalizes status values | [ ] | Uses mappings |
| Counts checkboxes | [ ] | Additional context |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 10: Aggregate Card Status
| ID | `025c8f00-e1da-4243-aab7-40bcdac36502` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Groups by directory | [ ] | |
| Counts by status | [ ] | Complete, In Progress, etc. |
| Calculates overall totals | [ ] | |
| Calculates completion percentage | [ ] | |

**Output Schema**:
```json
{
  "source": "task_cards",
  "by_directory": { "task-cards/automation/": { "complete": 2, "total": 4 } },
  "overall": { "complete": 10, "total": 25 },
  "overall_completion_pct": 40
}
```

**Sign-off**: [ ] ________ Date: ________

---

#### Nodes 11-16: Status Reports Processing (Parallel Path)

| Node | Purpose | Status |
|------|---------|--------|
| Filter Status Reports | Filter `docs/status-reports/*.md` | [ ] |
| Has Status Reports? | Skip if none | [ ] |
| Process Each Report | Loop through reports | [ ] |
| Fetch Report Content | Get report content | [ ] |
| Parse Report Statuses | Extract dates, percentages | [ ] |
| Aggregate Report Status | Combine and sort by date | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

### Merge and Target Fetch Section

#### Node 17: Merge Aggregated Data
| ID | `943959ec-c35b-41f9-9b76-9d81e9b0e27a` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Combines task cards + reports | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 18: Prepare Target Fetch
| ID | `7eb9a617-13c9-40f4-bee6-38c806cc3e85` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Extracts target paths | [ ] | From config |
| Passes data forward | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Nodes 19-21: Target Document Fetches

| Node | Target | Status |
|------|--------|--------|
| Fetch Target Readme | `task-cards/README.md` | [ ] |
| Fetch Target Index | `task-cards/INDEX.md` | [ ] |
| Fetch Target Roadmap | `docs/CONSOLIDATED_ROADMAP.md` | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

### Mismatch Detection Section

#### Node 22: Find All Mismatches
| ID | `a234a7b4-2b66-4670-8038-15285999ae9a` |
|----|-------|

| Mismatch Type | Detection Logic | Status |
|---------------|-----------------|--------|
| FILE_COUNT_MISMATCH | README claims vs actual | [ ] |
| COMPLETION_COUNT_MISMATCH | X/Y Complete accuracy | [ ] |
| PERCENTAGE_MISMATCH | Overall % accuracy | [ ] |
| ROADMAP_PERCENTAGE_MISMATCH | Roadmap vs actual | [ ] |
| STATUS_FORMAT_ISSUE | Unknown statuses | [ ] |
| STATUS_REPORT_MISMATCH | Report vs roadmap | [ ] |

**Severity Levels**:
- HIGH: File count, completion count
- MEDIUM: Percentage mismatches
- LOW: Status format issues

**Sign-off**: [ ] ________ Date: ________

---

#### Node 23: Has Mismatches?
| ID | `54ce1b06-ce78-4470-8031-f8a1d99e1efd` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `has_mismatches === true` | [ ] | |
| True → Format AI Prompt | [ ] | |
| False → Log in Sync | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

### AI Correction Generation Section

#### Node 24: Format AI Prompt
| ID | `770ce2ab-67ac-4dcf-8d3f-27e130c9eceb` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Builds JSON for AI | [ ] | Mismatches + actual state |
| Creates user message | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 25: Generate Corrections (AI Agent)
| ID | `b0815cb0-e6ca-4ae5-81d4-8d5c1fc7eb6b` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| System message defines task structure | [ ] | |
| Consolidation rules | [ ] | Group by same file |
| Priority mapping | [ ] | HIGH=1, MEDIUM=2, LOW=3 |
| Output format: raw JSON | [ ] | No markdown |
| Uses Gemini sub-node | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 25a: Gemini 2.5 Flash (Sub-node)
| ID | `fe8ec068-7651-4bec-982f-8d77f3229a24` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Credential: Google Gemini API | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 26: Clean AI Output
| ID | `3f19b793-0433-49ac-886c-514bca9d875b` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Strips ```json``` blocks | [ ] | |
| Fixes trailing commas | [ ] | Common AI error |
| Handles object vs string | [ ] | |
| Falls back to extraction | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 27: Prepare for Distributor
| ID | `cfeb58c5-f9b3-47e6-9495-6ec29afb7267` |
|----|-------|

| Logic Check | Status | Notes |
|-------------|--------|-------|
| Validates task structure | [ ] | task_id, target, description |
| Normalizes fields | [ ] | Adds document, source_workflow |
| Sets skip flag if no tasks | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 28: Has Tasks
| ID | `a9be8547-832f-4156-a1ce-38f1cea7120c` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Condition: `skip === false` | [ ] | |
| True → Send Corrections | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 29: Send Corrections
| ID | `8dd437a3-0b36-4626-939d-b4192b319f6e` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| URL: `/webhook/task-distributor` | [ ] | Distributor endpoint |
| Method: POST | [ ] | |
| Body: Full task list | [ ] | |

**Integration Check**:
| This Workflow | Connects To | Status |
|---------------|-------------|--------|
| Send Corrections | Distributor → Receive List | [ ] |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 30: Summary Report
| ID | `65da80f3-4ce9-4bb8-80a0-0e96b04de3e9` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Returns execution summary | [ ] | |
| Includes mismatch count | [ ] | |
| Lists dispatched tasks | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

#### Node 31: Log in Sync
| ID | `451a6c2d-d1c0-4292-9dbe-60ccbbc1931e` |
|----|-------|

| Check | Status | Notes |
|-------|--------|-------|
| Returns in_sync status | [ ] | |
| Includes verification details | [ ] | |

**Sign-off**: [ ] ________ Date: ________

---

## Test Scenarios

### Scenario 1: No Mismatches
| Step | Expected | Status |
|------|----------|--------|
| Scan task cards | All parsed | [ ] |
| Compare to targets | No mismatches | [ ] |
| Log in Sync | status: in_sync | [ ] |

### Scenario 2: Completion Count Mismatch
| Step | Expected | Status |
|------|----------|--------|
| README says 5/10 Complete | Found | [ ] |
| Actual: 7/10 Complete | Mismatch detected | [ ] |
| AI generates correction | Task created | [ ] |
| Sent to Distributor | task_count: 1 | [ ] |

### Scenario 3: Multiple Mismatches
| Step | Expected | Status |
|------|----------|--------|
| Multiple directories wrong | Multiple mismatches | [ ] |
| AI consolidates by file | 1 task per file | [ ] |

### Scenario 4: Manual Trigger
| Step | Expected | Status |
|------|----------|--------|
| POST to webhook | Workflow starts | [ ] |
| Returns summary | Response in lastNode | [ ] |

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
