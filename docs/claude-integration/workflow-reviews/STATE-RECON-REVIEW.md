# Doc Chain - State Reconciliation Workflow Review

> **Workflow ID:** JVAjIrsS4yKbYIxW  
> **Status:** ✅ Active  
> **Version:** STATE-V001  
> **Last Updated:** 2025-12-23T17:16:24.248Z

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

Runs daily at 3 AM (or via manual webhook), performs deep content analysis of task cards and status reports, compares actual repository state against documentation claims, identifies mismatches (file counts, completion percentages, status inconsistencies), generates correction tasks via Gemini AI, and dispatches to Distributor.

---

## Trigger Configuration

| Trigger | Schedule | Notes |
|---------|----------|-------|
| Daily Check | Every day at 3:00 AM | `scheduleTrigger` |
| Manual Trigger | POST `/webhook/state-reconciliation` | Returns last node response |

---

## Node-by-Node Validation (34 Nodes)

### INITIALIZATION (Nodes 1-6)

#### Node 1: Daily Check
| Check | Status | Notes |
|-------|--------|-------|
| Schedule: Daily 3 AM | [ ] | `triggerAtHour: 3` |

#### Node 2: Manual Trigger
| Check | Status | Notes |
|-------|--------|-------|
| Path correct | [ ] | `state-reconciliation` |
| Response mode | [ ] | `lastNode` |

#### Node 3: Start (Merge)
| Check | Status | Notes |
|-------|--------|-------|
| Combines both triggers | [ ] | |

#### Node 4: Workflow Configuration
| Check | Status | Notes |
|-------|--------|-------|
| Reconciliation targets defined | [ ] | README, INDEX, ROADMAP |
| Status patterns defined | [ ] | Regex patterns |
| Status mappings defined | [ ] | Normalization |
| Mismatch tolerance | [ ] | 5% |

**Reconciliation Targets:**
- `task-cards/README.md` (index)
- `task-cards/INDEX.md` (index)
- `docs/CONSOLIDATED_ROADMAP.md` (roadmap)

**Status Patterns:**
- `task_status`: `/^\\*?\\*?Status:?\\*?\\*?\\s*(.+)$/im`
- `completion_pct`: `/(\\d+)%\\s*(?:complete|done|finished)/i`
- `checkbox_checked`: `/- \\[x\\]/gi`
- `fraction`: `/(\\d+)\\/(\\d+)\\s*Complete/i`

---

### TASK CARD SCANNING (Nodes 7-12)

#### Node 7: List All Files
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | GitHub Trees API (recursive) |
| Auth header | [ ] | `Bearer {{ env.GITHUB_TOKEN }}` |

**URL:** `https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/git/trees/main?recursive=1`

#### Node 8: Filter Task Cards
| Check | Status | Notes |
|-------|--------|-------|
| Filters to task-cards/*.md | [ ] | |
| Excludes README.md | [ ] | |
| Excludes INDEX.md | [ ] | |
| Returns items for loop | [ ] | |

#### Node 9: Process Each Task Card (SplitInBatches)
| Check | Status | Notes |
|-------|--------|-------|
| Iterates over cards | [ ] | |
| Reset: false | [ ] | |

#### Node 10: Fetch Card Content
| Check | Status | Notes |
|-------|--------|-------|
| GitHub Contents API | [ ] | |
| onError: continueRegularOutput | [ ] | |

#### Node 11: Parse Card Status
| Check | Status | Notes |
|-------|--------|-------|
| Decodes base64 | [ ] | |
| Extracts status field | [ ] | Using config patterns |
| Normalizes status | [ ] | Using config mappings |
| Counts checkboxes | [ ] | |

#### Node 12: Aggregate Card Status
| Check | Status | Notes |
|-------|--------|-------|
| Groups by directory | [ ] | |
| Counts by status | [ ] | Complete, In Progress, etc. |
| Calculates overall % | [ ] | |

---

### STATUS REPORT SCANNING (Nodes 13-18)

#### Node 13: Filter Status Reports
| Check | Status | Notes |
|-------|--------|-------|
| Filters to docs/status-reports/*.md | [ ] | |
| Handles empty case | [ ] | Returns `has_reports: false` |

#### Node 14: Has Status Reports? (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `has_reports !== false` |

#### Node 15: Process Each Report (SplitInBatches)
| Check | Status | Notes |
|-------|--------|-------|
| Iterates over reports | [ ] | |

#### Node 16: Fetch Report Content
| Check | Status | Notes |
|-------|--------|-------|
| GitHub Contents API | [ ] | |
| onError: continueRegularOutput | [ ] | |

#### Node 17: Parse Report Statuses
| Check | Status | Notes |
|-------|--------|-------|
| Extracts date from filename | [ ] | |
| Extracts overall status | [ ] | |
| Extracts completion % | [ ] | |

#### Node 18: Aggregate Report Status
| Check | Status | Notes |
|-------|--------|-------|
| Sorts by date descending | [ ] | |
| Identifies latest report | [ ] | |

---

### DATA AGGREGATION (Nodes 19-24)

#### Node 19: Merge Aggregated Data
| Check | Status | Notes |
|-------|--------|-------|
| Combines task cards + reports | [ ] | |
| **⚠️ VERIFY:** Both branches converge | [ ] | May need attention |

#### Node 20: Prepare Target Fetch
| Check | Status | Notes |
|-------|--------|-------|
| Consolidates data | [ ] | |
| Prepares target paths | [ ] | |

#### Node 21: Fetch Target Readme
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | task-cards/README.md |

#### Node 22: Fetch Target Index
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | task-cards/INDEX.md |
| onError: continueRegularOutput | [ ] | May not exist |

#### Node 23: Fetch Target Roadmap
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | docs/CONSOLIDATED_ROADMAP.md |
| onError: continueRegularOutput | [ ] | May not exist |

---

### MISMATCH DETECTION (Nodes 24-26)

#### Node 24: Find All Mismatches
| Check | Status | Notes |
|-------|--------|-------|
| Decodes all target content | [ ] | |
| FILE_COUNT_MISMATCH | [ ] | Actual vs claimed totals |
| COMPLETION_COUNT_MISMATCH | [ ] | Complete count differences |
| PERCENTAGE_MISMATCH | [ ] | % differences > tolerance |
| STATUS_FORMAT_ISSUE | [ ] | >20% unknown status |
| STATUS_REPORT_MISMATCH | [ ] | Report vs roadmap |
| Sorts by severity | [ ] | high, medium, low |

**Mismatch Types:**
| Type | Severity | Description |
|------|----------|-------------|
| FILE_COUNT_MISMATCH | high | README claims wrong file count |
| COMPLETION_COUNT_MISMATCH | high | README claims wrong complete count |
| PERCENTAGE_MISMATCH | medium | README % differs from actual |
| ROADMAP_PERCENTAGE_MISMATCH | medium | Roadmap % differs from cards |
| STATUS_FORMAT_ISSUE | low | Cards with unrecognized status |
| STATUS_REPORT_MISMATCH | medium | Report vs roadmap conflict |

#### Node 25: Has Mismatches? (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `has_mismatches === true` |
| True → Format AI Prompt | [ ] | |
| False → Log in Sync | [ ] | |

---

### CORRECTION GENERATION (Nodes 26-32)

#### Node 26: Format AI Prompt
| Check | Status | Notes |
|-------|--------|-------|
| Builds user message | [ ] | With mismatch data |

#### Node 27: Generate Corrections (AI Agent)
| Check | Status | Notes |
|-------|--------|-------|
| Uses Gemini model | [ ] | |
| System prompt: consolidation rules | [ ] | One task per file |
| Output: raw JSON | [ ] | No markdown |

**Task Consolidation Rules:**
- Group updates for SAME FILE into ONE task
- Never create multiple tasks for same document
- Include SPECIFIC changes with actual values

#### Node 28: Gemini 2.5 Flash
| Check | Status | Notes |
|-------|--------|-------|
| Credential valid | [ ] | |
| Connected to Generate Corrections | [ ] | |

#### Node 29: Clean AI Output
| Check | Status | Notes |
|-------|--------|-------|
| Strips markdown code blocks | [ ] | |
| Fixes trailing commas | [ ] | |
| Extracts JSON | [ ] | |

#### Node 30: Prepare for Distributor
| Check | Status | Notes |
|-------|--------|-------|
| Validates task structure | [ ] | |
| Normalizes task fields | [ ] | |
| Sets source: state-reconciliation-full | [ ] | |

#### Node 31: Has Tasks (IF)
| Check | Status | Notes |
|-------|--------|-------|
| Condition | [ ] | `skip === false` |

#### Node 32: Send Corrections
| Check | Status | Notes |
|-------|--------|-------|
| URL correct | [ ] | `/webhook/task-distributor` |
| Body format | [ ] | JSON |

---

### COMPLETION (Nodes 33-34)

#### Node 33: Summary Report
| Check | Status | Notes |
|-------|--------|-------|
| Generates execution summary | [ ] | |

#### Node 34: Log in Sync
| Check | Status | Notes |
|-------|--------|-------|
| Returns healthy status | [ ] | |

---

## Issues Found

| # | Severity | Description | Recommendation |
|---|----------|-------------|----------------|
| 1 | 🟡 MED | Merge node timing with empty status reports | Test with empty directory |
| 2 | 🟢 LOW | Many parallel fetches may hit rate limits | Monitor for 403 errors |

---

## Sign-off

- [ ] All 34 nodes validated
- [ ] Mismatch detection logic verified
- [ ] AI consolidation rules confirmed
- [ ] Merge timing validated

**Reviewer:** ________________________  
**Date:** ________________________  
**Signature:** ________________________
