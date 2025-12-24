# Workflow Review: Doc Chain - State Reconciliation

**Workflow ID:** `JVAjIrsS4yKbYIxW`
**Version:** STATE-V001
**Updated:** 2025-12-23T17:16:24.248Z
**Nodes:** 35

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

Daily deep-content scan that:
1. Scans all task-cards for actual status
2. Scans status reports for completion data
3. Compares against index files (README, INDEX, ROADMAP)
4. Uses AI to generate correction tasks for mismatches
5. Sends corrections to Distributor

---

## Trigger Configuration

| Trigger | Schedule | Purpose |
|---------|----------|---------|
| Daily Check | 3:00 AM daily | Automated |
| Manual Trigger | POST `/state-reconciliation` | On-demand |

---

## Node Flow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRIGGER PHASE                             │
│  Daily Check ──┐                                                 │
│  Manual Trigger─┴─▶ Start ──▶ Config ──▶ List All Files          │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PARALLEL SCAN PHASE                           │
│  ┌──────────────────────┐    ┌────────────────────────────┐     │
│  │ Task Card Branch     │    │ Status Report Branch       │     │
│  │                      │    │                            │     │
│  │ Filter Task Cards    │    │ Filter Status Reports      │     │
│  │        ↓             │    │        ↓                   │     │
│  │ Process Each Card    │    │ Has Status Reports?        │     │
│  │ (SplitInBatches)     │    │        ↓                   │     │
│  │        ↓             │    │ Process Each Report        │     │
│  │ Fetch Card Content   │    │        ↓                   │     │
│  │        ↓             │    │ Fetch Report Content       │     │
│  │ Parse Card Status    │    │        ↓                   │     │
│  │        ↓             │    │ Parse Report Statuses      │     │
│  │ Aggregate Card Status│    │        ↓                   │     │
│  │                      │    │ Aggregate Report Status    │     │
│  └──────────┬───────────┘    └────────────┬───────────────┘     │
│             └──────────┬──────────────────┘                      │
│                        ↓                                         │
│              Merge Aggregated Data                               │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    COMPARISON PHASE                              │
│  Prepare Target Fetch                                           │
│         ↓                                                        │
│  ┌──────────────┬──────────────┬───────────────┐                │
│  │ Fetch README │ Fetch INDEX  │ Fetch ROADMAP │                │
│  └──────────────┴──────────────┴───────────────┘                │
│         ↓                                                        │
│  Find All Mismatches                                            │
│         ↓                                                        │
│  Has Mismatches?                                                │
│    ├─ YES → Format AI Prompt → Generate Corrections             │
│    └─ NO → Log in Sync                                          │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CORRECTION PHASE                              │
│  Clean AI Output → Prepare for Distributor → Has Tasks?         │
│                                                   │              │
│                                 YES ─────────────────────────    │
│                                   ↓                              │
│                           Send Corrections → Summary Report      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Nodes Review

### Workflow Configuration
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Reconciliation targets defined | ⬜ | README, INDEX, ROADMAP |
| Status patterns defined | ⬜ | Regex for parsing |
| Status mappings defined | ⬜ | Normalization rules |
| Mismatch tolerance | ⬜ | 5% default |

**Status Mappings:**
```javascript
{
  'complete': 'Complete',
  'completed': 'Complete',
  '✅ complete': 'Complete',
  'in progress': 'In Progress',
  '🔄 in progress': 'In Progress',
  'not started': 'Not Started',
  '🟢 ready': 'Not Started',
  'blocked': 'Blocked'
}
```

---

### Parse Card Status
**Type:** `n8n-nodes-base.code`

| Check | Status | Notes |
|-------|--------|-------|
| Status pattern extraction | ⬜ | `**Status:** X` format |
| Checkbox counting | ⬜ | `- [x]` vs `- [ ]` |
| Normalization works | ⬜ | Maps to standard values |

---

### Find All Mismatches
**Type:** `n8n-nodes-base.code`

**Mismatch Types Detected:**

| Type | Severity | Example |
|------|----------|---------|
| FILE_COUNT_MISMATCH | high | README says 10 files, has 12 |
| COMPLETION_COUNT_MISMATCH | high | Claims 5 complete, actually 3 |
| PERCENTAGE_MISMATCH | medium | Claims 50%, actually 40% |
| ROADMAP_PERCENTAGE_MISMATCH | medium | Roadmap out of sync |
| STATUS_FORMAT_ISSUE | low | Cards missing Status field |
| STATUS_REPORT_MISMATCH | medium | Report vs roadmap conflict |

| Check | Status | Notes |
|-------|--------|-------|
| All mismatch types detected | ⬜ | 6 types |
| Severity sorting works | ⬜ | high → medium → low |
| Tolerance applied | ⬜ | 5% threshold |

---

### Generate Corrections (AI Agent)
**Type:** `@n8n/n8n-nodes-langchain.agent`

| Check | Status | Notes |
|-------|--------|-------|
| Consolidation rules | ⬜ | One task per file |
| Uses actual values | ⬜ | Not placeholders |
| Output format | ⬜ | Valid JSON |

**Task Consolidation Rules:**
- ⬜ Groups updates to same file into ONE task
- ⬜ Priority based on severity
- ⬜ Includes specific `changes[]` array

---

### Send Corrections
**Type:** `n8n-nodes-base.httpRequest`
**URL:** `https://gitlitreview.app.n8n.cloud/webhook/task-distributor`

| Check | Status | Notes |
|-------|--------|-------|
| Payload format | ⬜ | Task list schema |
| source: state-reconciliation | ⬜ | Identifies origin |

---

## Mismatch Detection Logic

### File Count Check
```javascript
// For each directory in task-cards/
const dirPattern = new RegExp(`${dirName}.*?(\\d+)/(\\d+)\\s*Complete`, 'i');
// Compare claimed vs actual
if (claimedTotal !== stats.total) {
  // FILE_COUNT_MISMATCH
}
```

### Completion Percentage Check
```javascript
const actualOverallPct = taskCards.overall_completion_pct;
const readmePctMatch = readmeContent.match(/(?:Overall|Total).*?(\\d+)%/i);
if (Math.abs(claimedPct - actualOverallPct) > tolerance) {
  // PERCENTAGE_MISMATCH
}
```

---

## Test Scenarios

### Test 1: Manual Trigger
```bash
curl -X POST https://gitlitreview.app.n8n.cloud/webhook/state-reconciliation
```
**Expected:** Scans, finds mismatches (if any), sends corrections.

### Test 2: Create Intentional Mismatch
1. Update a task-card status to Complete
2. Leave README count unchanged
3. Trigger reconciliation
4. Verify mismatch detected

### Test 3: No Mismatches
**Expected:** `Log in Sync` node executes, summary returned.

---

## Sign-off

| Item | Verified | Date | Reviewer |
|------|----------|------|----------|
| All 35 nodes reviewed | ⬜ | - | - |
| Task card scanning works | ⬜ | - | - |
| Mismatch detection accurate | ⬜ | - | - |
| AI consolidation correct | ⬜ | - | - |
| Corrections sent to Distributor | ⬜ | - | - |

**Final Sign-off:** ⬜ Pending
