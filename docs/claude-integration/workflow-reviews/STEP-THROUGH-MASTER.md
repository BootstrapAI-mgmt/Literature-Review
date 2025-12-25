# Workflow Step-Through Master Document

> **Purpose**: Track node-by-node review progress across all workflows  
> **Created**: 2024-12-24  
> **Methodology**: Validate each node's input/output against expected behavior and repository state

---

## Checkout Protocol

### How to Check Out a Section
1. Update the `Checked Out By` field with your identifier (e.g., `Claude-Session-123`)
2. Update `Checkout Time` with ISO timestamp
3. Set status to `🔒 Locked`
4. Commit changes before starting work

### How to Release a Section
1. Complete all validation checks
2. Update `Sign-off By` and `Sign-off Time`
3. Set status to `✅ Signed Off` or `⚠️ Issues Found`
4. Clear `Checked Out By` field
5. Commit changes

### Status Legend
| Status | Meaning |
|--------|---------|
| 📋 Ready | Available for review |
| 🔒 Locked | Currently being reviewed |
| ✅ Signed Off | Review complete, all checks pass |
| ⚠️ Issues Found | Review complete, issues documented |
| 🔄 Needs Update | Workflow changed, re-review needed |

---

## Workflow Review Status

| # | Workflow | Doc | Status | Checked Out By | Nodes | Progress |
|---|----------|-----|--------|----------------|-------|----------|
| 1 | Doc Chain - Trigger | [TRIGGER-STEP.md](./TRIGGER-STEP.md) | ✅ Static Complete | - | 11 | Static ✅ |
| 2 | Doc Chain - Distributor | [DISTRIBUTOR-STEP.md](./DISTRIBUTOR-STEP.md) | ✅ Static Complete | - | 24 | Static ✅ |
| 3 | Doc Chain - Agent | [AGENT-STEP.md](./AGENT-STEP.md) | 🔴 CRITICAL ISSUE | - | 14 | ISSUE-002 |
| 4 | Doc Chain - State Reconciliation | [STATE-RECON-STEP.md](./STATE-RECON-STEP.md) | ⚠️ Issues Found | - | 32 | ISSUE-001 |
| 5 | Doc Chain - Staleness | [STALENESS-STEP.md](./STALENESS-STEP.md) | ✅ Static Complete | - | 31 | Live ⏸️ |
| 6 | Doc Chain - Errors | [ERRORS-STEP.md](./ERRORS-STEP.md) | 📋 Ready | - | 8 | 0/8 |
| 7 | Doc Chain - Release | [RELEASE-STEP.md](./RELEASE-STEP.md) | 📋 Ready | - | 10 | 0/10 |
| 8 | Doc Chain - PR Review | [PR-REVIEW-STEP.md](./PR-REVIEW-STEP.md) | 📋 Ready | - | 12 | 0/12 |

**Total Nodes**: 142 (updated count)  
**Reviewed**: 112 (static)
**Critical Issues**: 1 (ISSUE-002: Exposed Token)
**Medium Issues**: 1 (ISSUE-001: AI Pipeline)

---

## Validation Criteria

### Three Dimensions of Validation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    VALIDATION FRAMEWORK                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DIMENSION 1: FUNCTIONAL CORRECTNESS                                     │
│  "Does the node/workflow execute without errors?"                        │
│  → Configuration validity, credential access, API connectivity           │
│                                                                          │
│  DIMENSION 2: LOGIC ALIGNMENT                                            │
│  "Does the workflow architecture produce expected transformations?"      │
│  → Input/output matching, flow sequencing, conditional routing           │
│                                                                          │
│  DIMENSION 3: REPOSITORY STATE ALIGNMENT                                 │
│  "Do outputs accurately reflect the actual repository content?"          │
│  → File counts match reality, statuses match task cards, paths exist     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### For Each Node, Verify:

#### Dimension 1: Functional Correctness
- [ ] Parameters match expected values
- [ ] Credentials referenced correctly and accessible
- [ ] Position in workflow makes sense
- [ ] Node executes without errors (test execution)
- [ ] API endpoints respond correctly
- [ ] Error handling paths function

#### Dimension 2: Logic Alignment  
- [ ] Expected input format documented
- [ ] Handles edge cases (empty, null, malformed)
- [ ] Previous node output matches this node's input
- [ ] Output schema documented
- [ ] Output matches next node's expected input
- [ ] Conditional logic routes correctly (IF nodes tested both paths)
- [ ] Loop nodes iterate expected number of times
- [ ] Data transformations produce expected structure

#### Dimension 3: Repository State Alignment
- [ ] URLs/paths reference correct repo (BootstrapAI-mgmt/Literature-Review)
- [ ] Branch references correct (main)
- [ ] File paths referenced actually exist in repo
- [ ] **File counts in output match actual repo file counts**
- [ ] **Status values extracted match actual task card content**
- [ ] **Completion percentages calculated match reality**
- [ ] **Directory structures match current repo state**
- [ ] **Cross-references (README↔task-cards↔ROADMAP) are accurate**

### Live Validation Protocol

For workflows that read/analyze repository content, perform **live validation**:

1. **Baseline Capture**: Before test, document actual repo state
   ```
   - Count files in task-cards/: ___
   - Count Complete tasks: ___
   - Count In Progress tasks: ___
   - README claimed completion: ___
   ```

2. **Execute Workflow**: Trigger manually via webhook

3. **Compare Outputs**: Verify workflow outputs match baseline
   ```
   - Workflow reported file count: ___ (matches baseline? Y/N)
   - Workflow reported Complete: ___ (matches baseline? Y/N)
   - Mismatches detected: ___ (accurate? Y/N)
   ```

4. **Document Discrepancies**: Any delta between workflow output and reality

---

## Quick Start: Begin a Review

### Option 1: Start with Trigger (Recommended - Entry Point)
```
1. Check out TRIGGER-STEP.md
2. Validate Node 1 → Node 10 sequentially
3. Sign off when complete
```

### Option 2: Review in Parallel
```
Agent A: TRIGGER-STEP.md + DISTRIBUTOR-STEP.md
Agent B: AGENT-STEP.md + ERRORS-STEP.md
Agent C: STATE-RECON-STEP.md + STALENESS-STEP.md
Agent D: RELEASE-STEP.md + PR-REVIEW-STEP.md
```

---

## Session Log

| Timestamp | Agent | Action | Workflow | Notes |
|-----------|-------|--------|----------|-------|
| 2024-12-24T01:00:00Z | Setup | Created master doc | ALL | Initial setup |
| 2024-12-25T15:30:00Z | Claude | Created all step-through docs | ALL | 8/8 workflows documented, 127 total nodes |
| 2024-12-25T16:00:00Z | Claude | Enhanced validation criteria | ALL | Added 3 dimensions: Functional, Logic, Repo State |
| 2025-12-25T17:00:00Z | Claude | Static validation | State Recon | Live test: Detection ✅, AI remediation ❌ (ISSUE-001) |
| 2025-12-25T17:15:00Z | Claude | Static validation | Staleness | 31 nodes, live test triggered (async) |
| 2025-12-25T17:30:00Z | Claude | Static validation | Core Chain | Trigger (11), Distributor (24), Agent (14) |
| 2025-12-25T17:30:00Z | Claude | 🔴 CRITICAL FINDING | Agent | Exposed GitHub PAT in nodes array (ISSUE-002) |

---

## Cross-Workflow Integration Matrix

Workflows must be validated not just individually but at integration points:

| Source Workflow | Integration Point | Target Workflow | Validation Check |
|-----------------|-------------------|-----------------|------------------|
| Trigger | `/webhook/task-distributor` | Distributor | Task payload schema matches |
| State Reconciliation | `/webhook/task-distributor` | Distributor | Correction tasks dispatched correctly |
| Staleness | `/webhook/task-distributor` | Distributor | Update tasks dispatched correctly |
| Distributor | `/webhook/doc-agent` | Agent | Individual tasks route correctly |
| Agent | GitHub Commits API | Repository | Commits actually appear in repo |
| PR Review | PR Comments API | Repository | Review comments posted correctly |
| Errors | GitHub Issues API | Repository | Error issues created correctly |
| Release | GitHub Releases API | Repository | Releases created correctly |

---

## Workflow-Specific Live Validation Requirements

| Workflow | Live Validation Required | What to Check |
|----------|--------------------------|---------------|
| State Reconciliation | **CRITICAL** | File counts, completion %, status accuracy |
| Staleness | **CRITICAL** | Domain activity dates, staleness scores vs reality |
| Trigger | Medium | Webhook receives and parses correctly |
| Distributor | Medium | Tasks route to correct agents |
| Agent | High | Commits match task descriptions |
| Errors | Medium | Issues created with correct content |
| Release | Medium | Release notes accurate |
| PR Review | High | Doc impact analysis accuracy |

---

*Last Updated: 2024-12-25*
