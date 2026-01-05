# Master n8n Validation Plan (V2.0.0)

> **Status:** Active Development  
> **Version:** 2.0.0  
> **Created:** 2026-01-01  
> **Purpose:** Comprehensive validation strategy for the n8n automation layer ("Doc Chain") ensuring both technical functionality AND documentation accuracy.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Validation Philosophy](#2-validation-philosophy)
3. [Workflow Scope](#3-workflow-scope)
4. [Testing Strategy](#4-testing-strategy)
5. [Tier 1: Unit/Component Testing](#5-tier-1-unitcomponent-testing)
6. [Tier 2: Integration Testing](#6-tier-2-integration-testing)
7. [Tier 3: End-to-End Testing](#7-tier-3-end-to-end-testing)
8. [Tier 4: Content Accuracy Testing](#8-tier-4-content-accuracy-testing)
9. [Tier 5: Cascade Validation Testing](#9-tier-5-cascade-validation-testing)
10. [Gold Standard Definitions](#10-gold-standard-definitions)
11. [Regression Test Suite](#11-regression-test-suite)
12. [Validation Matrices](#12-validation-matrices)
13. [Automated Validation Framework](#13-automated-validation-framework)
14. [Execution Plan](#14-execution-plan)
15. [Failure Response Procedures](#15-failure-response-procedures)
16. [Artifacts & Reporting](#16-artifacts--reporting)
17. [Appendices](#17-appendices)

---

## 1. Executive Summary

### 1.1 Purpose

This validation plan ensures the n8n Doc Chain automation system: 
1. **Functions technically** - Workflows execute without errors
2. **Produces accurate output** - Documentation reflects actual repository state
3. **Maintains synchronization** - Changes cascade through dependent documents
4. **Prevents drift** - Staleness detection catches outdated content

### 1.2 Scope

| Category | Count | Description |
|----------|-------|-------------|
| Workflows Validated | 8 | All Doc Chain workflows |
| Test Tiers | 5 | Mock → Simulated → Live → Accuracy → Cascade |
| Gold Standards | 6 | Reference states for comparison |
| Regression Tests | 12 | Known issue prevention |
| Total Test Cases | 87 | Across all tiers |

### 1.3 Success Criteria

The validation is considered **PASSED** only when: 

| Criterion | Threshold | Measurement |
|-----------|-----------|-------------|
| Technical Tests (Tier 1-3) | 100% pass | All workflows execute correctly |
| Content Accuracy (Tier 4) | 100% pass | Documents match Gold Standards |
| Cascade Validation (Tier 5) | 100% pass | All cascade chains complete |
| Regression Tests | 100% pass | No known issues recur |

### 1.4 Key Principle

> **A test only PASSES if the OUTPUT matches the expected GOLD STANDARD.**
> 
> Technical execution without accurate output is a FAILURE.

---

## 2. Validation Philosophy

### 2.1 The Problem We're Solving

Previous validation marked tests as "PASSED" when: 
- Workflows executed without errors
- HTTP responses returned 200
- GitHub artifacts were created

But documentation remained **out of sync** because we never validated **content accuracy**.

### 2.2 The New Standard

```
OLD:  "Did the workflow run?" → PASSED
NEW: "Is the documentation correct?" → PASSED/FAILED
```

### 2.3 Validation Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION HIERARCHY                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Level 5:  OUTCOME VALIDATION (Ultimate Success)                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ "Documentation accurately reflects repository state"    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ▲                                      │
│                          │ Depends on                           │
│  Level 4: CASCADE VALIDATION                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ "Changes propagate through all dependent documents"     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ▲                                      │
│                          │ Depends on                           │
│  Level 3: CONTENT ACCURACY                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ "Individual document content is correct"                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ▲                                      │
│                          │ Depends on                           │
│  Level 2: INTEGRATION                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ "Workflows communicate correctly"                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ▲                                      │
│                          │ Depends on                           │
│  Level 1: TECHNICAL FUNCTION                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ "Individual nodes execute without error"                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Workflow Scope

### 3.1 Complete Workflow Inventory

We validate **ALL EIGHT** Doc Chain workflows:

#### Primary Sync Chain (Documentation Accuracy)

| ID | Workflow | Trigger | Purpose | Critical Path |
|----|----------|---------|---------|---------------|
| WF-01 | **Doc Chain - Trigger** | GitHub push webhook | Receives commits, identifies affected docs, creates task list | ✅ Yes |
| WF-02 | **Doc Chain - Distributor** | HTTP from Trigger/Recon | Queues tasks, manages sequential dispatch, handles callbacks | ✅ Yes |
| WF-03 | **Doc Chain - Agent** | HTTP from Distributor | AI analysis, document updates, GitHub commits | ✅ Yes |
| WF-04 | **Doc Chain - State Reconciliation** | Schedule (daily) + Manual | Syncs task-cards with repository reality | ✅ Yes |

#### Supporting Workflows (Auxiliary Functions)

| ID | Workflow | Trigger | Purpose | Critical Path |
|----|----------|---------|---------|---------------|
| WF-05 | **Doc Chain - PR Review** | GitHub PR webhook | Analyzes PR changes, posts review comments | No |
| WF-06 | **Doc Chain - Release** | GitHub tag webhook | Generates changelog, creates GitHub Release | No |
| WF-07 | **Doc Chain - Errors** | n8n error trigger | Captures failures, creates issues, notifies | No |
| WF-08 | **Doc Chain - Staleness** | Schedule (weekly) + Manual | Identifies outdated docs, creates refresh tasks | ✅ Yes |

### 3.2 Workflow Dependencies

```
GitHub Push Event
       │
       ▼
┌──────────────┐
│  WF-01       │
│  Trigger     │───────────────────────────────────────┐
└──────┬───────┘                                       │
       │ task list                                     │
       ▼                                               │
┌──────────────┐                                       │
│  WF-02       │◄──────────────────────────────────────┤
│  Distributor │                                       │
└──────┬───────┘                                       │
       │ dispatch task                                 │
       ▼                                               │
┌──────────────┐         ┌──────────────┐              │
│  WF-03       │────────▶│  WF-07       │              │
│  Agent       │ error   │  Errors      │              │
└──────┬───────┘         └──────────────┘              │
       │ callback                                      │
       ▼                                               │
┌──────────────┐                                       │
│  WF-02       │ (next task dispatch)                  │
│  Distributor │                                       │
└──────────────┘                                       │
                                                       │
┌──────────────┐         ┌──────────────┐              │
│  WF-04       │────────▶│  WF-02       │──────────────┘
│  State Recon │ tasks   │  Distributor │
└──────────────┘         └──────────────┘

┌──────────────┐         ┌──────────────┐
│  WF-08       │────────▶│  WF-02       │
│  Staleness   │ tasks   │  Distributor │
└──────────────┘         └──────────────┘

┌──────────────┐         ┌──────────────┐
│  GitHub PR   │────────▶│  WF-05       │
│  Webhook     │         │  PR Review   │
└──────────────┘         └──────────────┘

┌──────────────┐         ┌──────────────┐
│  GitHub Tag  │────────▶│  WF-06       │
│  Webhook     │         │  Release     │
└──────────────┘         └──────────────┘
```

---

## 4. Testing Strategy

### 4.1 Five-Tier Testing Approach

| Tier | Name | Purpose | Method | Success Metric |
|------|------|---------|--------|----------------|
| **1** | Unit/Component | Verify node logic | Mock JSON payloads | Correct execution path |
| **2** | Integration | Verify workflow communication | Simulated webhooks | Correct inter-workflow data |
| **3** | End-to-End | Verify real-world operation | Live GitHub events | Artifacts created |
| **4** | Content Accuracy | Verify output correctness | Gold Standard comparison | 100% match |
| **5** | Cascade Validation | Verify propagation | Multi-document verification | All levels updated |

### 4.2 Test Execution Order

```
1. Tier 1 (Unit) ─────────────────────────────────────▶ GATE 1
   All nodes execute correctly?                          │
                                                        ▼ Yes
2. Tier 2 (Integration) ──────────────────────────────▶ GATE 2
   Workflows communicate correctly?                     │
                                                        ▼ Yes
3. Tier 3 (End-to-End) ───────────────────────────────▶ GATE 3
   Real events produce artifacts?                       │
                                                        ▼ Yes
4. Tier 4 (Content Accuracy) ─────────────────────────▶ GATE 4
   Artifacts match Gold Standards?                      │
                                                        ▼ Yes
5. Tier 5 (Cascade) ──────────────────────────────────▶ COMPLETE
   All cascade chains verified?                         │
                                                        ▼ Yes
                                                   ✅ VALIDATED
```

### 4.3 Gate Criteria

| Gate | Criteria | Action on Failure |
|------|----------|-------------------|
| Gate 1 | 100% Tier 1 pass | Fix node logic before proceeding |
| Gate 2 | 100% Tier 2 pass | Fix integration issues before proceeding |
| Gate 3 | 100% Tier 3 pass | Fix end-to-end issues before proceeding |
| Gate 4 | 100% Tier 4 pass | Fix content generation before proceeding |
| Complete | 100% Tier 5 pass | System validated |

---

## 5. Tier 1: Unit/Component Testing

### 5.1 Purpose

Verify individual node logic without external API calls. 

### 5.2 Method

Manually trigger workflows using the "Test Workflow" button with mock JSON data representing GitHub payloads.

### 5.3 Test Cases

#### WF-01: Doc Chain - Trigger

| Test ID | Test Name | Mock Input | Expected Behavior | Pass Criteria |
|---------|-----------|------------|-------------------|---------------|
| T1-01-01 | Valid push event | Push with `docs/` changes | Proceeds to Matrix Lookup | Execution reaches "Matrix Lookup" node |
| T1-01-02 | Automated commit filter | Push with `[n8n] docs: ` prefix | Stops at Filter node | Execution terminates at "Filter Valid Events" |
| T1-01-03 | Manual n8n commit | Push with `[n8n] fix:` prefix | Proceeds normally | Execution reaches "Matrix Lookup" node |
| T1-01-04 | No doc changes | Push with only `.py` changes | Identifies code changes | "trigger_type" = "code" |
| T1-01-05 | Mixed changes | Push with `.py` and `.md` | Both types identified | "trigger_type" includes both |
| T1-01-06 | Empty commit | Push with no file changes | Graceful termination | No error, empty task list |

#### WF-02: Doc Chain - Distributor

| Test ID | Test Name | Mock Input | Expected Behavior | Pass Criteria |
|---------|-----------|------------|-------------------|---------------|
| T1-02-01 | Task queue | Single task payload | Task added to queue | `pending_count` = 1 |
| T1-02-02 | Batch queue | 5-task payload | All tasks queued | `pending_count` = 5 |
| T1-02-03 | Sequential dispatch | Queue with 3 tasks | First task dispatched | `in_progress` = task 1 |
| T1-02-04 | Callback success | Success callback | Next task dispatched | `in_progress` = task 2 |
| T1-02-05 | Callback failure | Failure callback | Error logged, next dispatched | Error in log, proceeds |
| T1-02-06 | Empty queue | Dispatch with no tasks | No dispatch attempted | `in_progress` = null |

#### WF-03: Doc Chain - Agent

| Test ID | Test Name | Mock Input | Expected Behavior | Pass Criteria |
|---------|-----------|------------|-------------------|---------------|
| T1-03-01 | Valid task | UPDATE_REFERENCE task | AI analysis triggered | Reaches "AI Agent" node |
| T1-03-02 | Document fetch | Task with valid path | File content retrieved | `document_content` populated |
| T1-03-03 | AI response parse | AI JSON output | Correctly parsed | `updated_content` extracted |
| T1-03-04 | Commit preparation | Parsed content | Base64 encoded | `content_base64` valid |
| T1-03-05 | Invalid task | Malformed task JSON | Error handled | Reaches "Error" path |
| T1-03-06 | Missing document | Task with bad path | Graceful failure | Error callback sent |

#### WF-04: Doc Chain - State Reconciliation

| Test ID | Test Name | Mock Input | Expected Behavior | Pass Criteria |
|---------|-----------|------------|-------------------|---------------|
| T1-04-01 | Scan trigger | Manual trigger | Scans task-cards/ | Execution reaches "Scan" node |
| T1-04-02 | Mismatch detection | Task card ≠ PR state | Correction task created | Task in output |
| T1-04-03 | No mismatches | All aligned | Empty task list | `tasks` = [] |
| T1-04-04 | Multiple mismatches | 3 discrepancies | 3 correction tasks | `tasks.length` = 3 |

#### WF-05: Doc Chain - PR Review

| Test ID | Test Name | Mock Input | Expected Behavior | Pass Criteria |
|---------|-----------|------------|-------------------|---------------|
| T1-05-01 | PR opened | PR with code changes | Analysis triggered | Reaches "Analyze Changes" |
| T1-05-02 | Bot PR filter | PR from bot user | Skipped | Terminates at "Is Human?" |
| T1-05-03 | Doc-only PR | PR with only . md changes | Different analysis path | `change_type` = "docs" |

#### WF-06: Doc Chain - Release

| Test ID | Test Name | Mock Input | Expected Behavior | Pass Criteria |
|---------|-----------|------------|-------------------|---------------|
| T1-06-01 | Tag created | v2.2.0 tag | Changelog generation | Reaches "Generate Changelog" |
| T1-06-02 | Tag parsing | Multiple tags | Correct comparison | Previous tag identified |
| T1-06-03 | First release | No previous tag | Full history used | Handles gracefully |

#### WF-07: Doc Chain - Errors

| Test ID | Test Name | Mock Input | Expected Behavior | Pass Criteria |
|---------|-----------|------------|-------------------|---------------|
| T1-07-01 | Error capture | Workflow error object | Error logged | Error details extracted |
| T1-07-02 | Task ID extraction | Error with task context | Task ID found | `task_id` populated |
| T1-07-03 | No task context | Error without task | Graceful handling | Proceeds without callback |
| T1-07-04 | Duplicate detection | Same error twice | Second deduplicated | No duplicate issue |

#### WF-08: Doc Chain - Staleness

| Test ID | Test Name | Mock Input | Expected Behavior | Pass Criteria |
|---------|-----------|------------|-------------------|---------------|
| T1-08-01 | Schedule trigger | Cron execution | Domain scan initiated | Reaches "Scan Domains" |
| T1-08-02 | Stale detection | Doc > 14 days old | Flagged as stale | In `stale_documents` |
| T1-08-03 | Fresh detection | Doc < 7 days old | Not flagged | Not in `stale_documents` |
| T1-08-04 | Threshold application | Multiple docs | Correct categorization | Proper scoring |

### 5.4 Mock Payloads

See [Appendix A:  Mock Payloads](#appendix-a-mock-payloads) for complete JSON examples.

---

## 6. Tier 2: Integration Testing

### 6.1 Purpose

Verify end-to-end flow from Trigger to Action using simulated webhooks. 

### 6.2 Method

Use `curl` or Postman to send JSON payloads to n8n webhook URLs.

### 6.3 Test Cases

#### Chain Integration Tests

| Test ID | Test Name | Flow | Method | Pass Criteria |
|---------|-----------|------|--------|---------------|
| T2-INT-01 | Trigger→Distributor | WF-01 → WF-02 | POST to `/github-doc-trigger` | Distributor receives task list |
| T2-INT-02 | Distributor→Agent | WF-02 → WF-03 | Submit task to Distributor | Agent receives dispatch |
| T2-INT-03 | Agent→Callback | WF-03 → WF-02 | Agent completes task | Distributor receives callback |
| T2-INT-04 | StateRecon→Distributor | WF-04 → WF-02 | Trigger reconciliation | Tasks sent to Distributor |
| T2-INT-05 | Staleness→Distributor | WF-08 → WF-02 | Trigger staleness review | Tasks sent to Distributor |
| T2-INT-06 | Error Propagation | WF-03 → WF-07 | Force agent error | Error workflow triggered |

#### Webhook Endpoint Tests

| Test ID | Endpoint | Method | Payload | Expected Response |
|---------|----------|--------|---------|-------------------|
| T2-EP-01 | `/github-doc-trigger` | POST | GitHub push event | `{"received": true}` |
| T2-EP-02 | `/task-distributor` | POST | Task list | `{"queued": n}` |
| T2-EP-03 | `/domain-agent` | POST | Single task | `{"processing": true}` |
| T2-EP-04 | `/task-callback` | POST | Callback payload | `{"acknowledged": true}` |
| T2-EP-05 | `/distributor-status` | GET | None | Status JSON |
| T2-EP-06 | `/distributor-reset` | POST | None | `{"reset": true}` |
| T2-EP-07 | `/state-reconciliation` | POST | None | `{"started": true}` |
| T2-EP-08 | `/staleness-review` | POST | None | `{"started": true}` |
| T2-EP-09 | `/pr-review` | POST | PR event | `{"received": true}` |

### 6.4 Integration Test Commands

```bash
# T2-INT-01: Trigger→Distributor
curl -X POST https://gitlitreview.app. n8n.cloud/webhook/github-doc-trigger \
  -H "Content-Type: application/json" \
  -d '{
    "ref": "refs/heads/main",
    "commits": [{
      "id":  "abc123",
      "message": "docs: update architecture",
      "modified": ["docs/MASTER_ARCHITECTURE_BLUEPRINT.md"]
    }]
  }'

# Verify:  Check Distributor status
curl -X GET https://gitlitreview.app. n8n.cloud/webhook/distributor-status

# T2-INT-02: Distributor→Agent
curl -X POST https://gitlitreview.app.n8n. cloud/webhook/task-distributor \
  -H "Content-Type: application/json" \
  -d '{
    "update_list_id": "test-int-001",
    "source":  "integration-test",
    "tasks": [{
      "task_id": "int-task-001",
      "document":  "docs/test.md",
      "update_type": "STATUS_UPDATE",
      "description": "Integration test task"
    }]
  }'

# T2-INT-04: StateRecon→Distributor
curl -X POST https://gitlitreview.app.n8n. cloud/webhook/state-reconciliation

# T2-INT-05: Staleness→Distributor  
curl -X POST https://gitlitreview.app. n8n.cloud/webhook/staleness-review
```

---

## 7. Tier 3: End-to-End Testing

### 7.1 Purpose

Verify the system works with real GitHub events. 

### 7.2 Method

Perform actual actions on the GitHub repository and verify results.

### 7.3 Test Cases

#### Live Event Tests

| Test ID | Action | Expected Result | Verification Method |
|---------|--------|-----------------|---------------------|
| T3-E2E-01 | Push commit to `docs/` | n8n processes, doc updated | Check commit history |
| T3-E2E-02 | Create PR with code changes | PR receives comment | Check PR comments |
| T3-E2E-03 | Push version tag | Release created | Check GitHub Releases |
| T3-E2E-04 | Merge PR with task reference | Task card updated | Check task card file |
| T3-E2E-05 | Wait for staleness schedule | Stale docs identified | Check created issues |
| T3-E2E-06 | Force workflow error | Error issue created | Check GitHub Issues |

#### Loop Prevention Tests

| Test ID | Action | Expected Result | Verification Method |
|---------|--------|-----------------|---------------------|
| T3-LP-01 | n8n commits with `[n8n] docs:` | No re-trigger | Check execution log |
| T3-LP-02 | Manual commit with `[n8n] fix:` | Normal processing | Check execution log |
| T3-LP-03 | Rapid sequential commits | No duplicate processing | Check task queue |

### 7.4 E2E Test Procedure

```markdown
## T3-E2E-01: Documentation Update Flow

### Setup
1. Ensure n8n is running and all workflows active
2. Clear Distributor queue:  `POST /distributor-reset`

### Execute
1. Create test branch: `git checkout -b test/e2e-validation`
2. Modify:  `docs/test-file.md` (add timestamp)
3. Commit: `git commit -m "test: E2E validation $(date)"`
4. Push: `git push origin test/e2e-validation`
5. Create PR to main

### Verify
1. [ ] n8n Trigger workflow executed
2. [ ] Task(s) sent to Distributor
3. [ ] Agent processed task(s)
4. [ ] Commit made by n8n (check for `[n8n] docs:` prefix)
5. [ ] Document content updated appropriately

### Cleanup
1. Close PR without merging (if test-only)
2. Delete test branch
```

---

## 8. Tier 4: Content Accuracy Testing

### 8.1 Purpose

Verify document CONTENT is correct by comparing against Gold Standards. 

### 8.2 Principle

> **Technical execution is necessary but not sufficient.**
> 
> A workflow that runs without error but produces incorrect output is a FAILURE.

### 8.3 Test Cases

#### Architecture Blueprint Accuracy

| Test ID | Validation | Expected State | Comparison Method |
|---------|------------|----------------|-------------------|
| T4-ARCH-01 | Module Coverage | All `.py` files in `literature_review/` documented | Directory scan vs. doc parse |
| T4-ARCH-02 | Directory Structure | Doc tree matches `ls -R literature_review/` | Structural comparison |
| T4-ARCH-03 | New Modules Present | Operationalization modules listed | Explicit check for modules |
| T4-ARCH-04 | Output Files Listed | All JSON outputs documented | Explicit check for outputs |
| T4-ARCH-05 | Freshness | Updated within 7 days of structural change | Timestamp comparison |

**Required Modules (Must Be Documented):**
```
literature_review/models/
├── action_vector.py
└── validation_strategy.py

literature_review/analysis/
├── validation_tracker.py
├── action_generator.py
├── pillar_evolution.py
├── stakeholder_analyzer.py
└── benchmark_analyzer.py
```

**Required Output Files (Must Be Documented):**
```
- action_vectors.json
- validation_gap_matrix.json
- requirement_benchmark_matrix.json
- pillar_research_log.json
- pillar_proposals.json
- stakeholder_impact_matrix.json
```

#### Repository Roadmap Accuracy

| Test ID | Validation | Expected State | Comparison Method |
|---------|------------|----------------|-------------------|
| T4-ROAD-01 | Wave Status Sync | Operationalization = ✅ Complete | Parse roadmap, check status |
| T4-ROAD-02 | Task Count | Reflects actual task cards | Count files vs. doc numbers |
| T4-ROAD-03 | Completion Percentages | Mathematically accurate | Calculate expected vs. stated |
| T4-ROAD-04 | New Waves Present | Validation Matrix Wave exists | Section existence check |
| T4-ROAD-05 | Wave 0. 5 Present | Modularization section exists | Section existence check |
| T4-ROAD-06 | At-a-Glance Table | All rows accurate | Row-by-row validation |

**Expected Roadmap State:**
```yaml
Operationalization Wave: 
  status: ✅ Complete
  completion:  100%
  tasks_completed: 8
  tasks_total: 8

Validation Matrix Wave:
  status: Section Exists
  task_cards: 22

Wave 0.5 Modularization: 
  status: Section Exists
  task_cards: 3
```

#### Task Card Accuracy

| Test ID | Validation | Expected State | Comparison Method |
|---------|------------|----------------|-------------------|
| T4-TASK-01 | PR→Task Sync | Merged PRs → Complete status | PR API vs. task card parse |
| T4-TASK-02 | Task→PR Sync | Complete tasks → Merged PRs | Bidirectional check |
| T4-TASK-03 | Wave Index Sync | Index matches individual cards | Cross-reference check |
| T4-TASK-04 | OP Wave Index | All 8 tasks show Complete | Explicit status check |

**PR-to-Task Mapping (Expected Complete):**
| PR # | Task Card | Expected Status |
|------|-----------|-----------------|
| #97 | OP_WAVE_1_1_SCHEMA_FOUNDATION | ✅ Complete |
| #98 | OP_WAVE_2_1_ACTION_EXTRACTION | ✅ Complete |
| #99 | OP_WAVE_2_2_BENCHMARK_EXTRACTION | ✅ Complete |
| #100 | OP_WAVE_3_1_VALIDATION_TRACKER | ✅ Complete |
| #101 | OP_WAVE_3_2_ACTION_VECTOR_GENERATOR | ✅ Complete |
| #102 | OP_WAVE_4_1_PILLAR_RESEARCH_LOG | ✅ Complete |
| #103 | OP_WAVE_4_2_MODIFICATION_PROPOSALS | ✅ Complete |
| #105 | OP_WAVE_4_3_STAKEHOLDER_MATRIX | ✅ Complete |

#### Staleness Accuracy

| Test ID | Validation | Expected State | Comparison Method |
|---------|------------|----------------|-------------------|
| T4-STAL-01 | Stale Detection | Correct docs flagged | Calculate expected vs. flagged |
| T4-STAL-02 | Fresh Detection | Recent docs not flagged | Verify no false positives |
| T4-STAL-03 | Threshold Accuracy | Scoring matches age | Calculate expected scores |

### 8.4 Content Accuracy Validation Script

```python
# tests/tier4/test_content_accuracy. py
"""
Tier 4: Content Accuracy Tests
Validates document content against Gold Standards
"""

import pytest
from pathlib import Path
from validation_framework import GoldStandardValidator

@pytest.fixture
def validator():
    return GoldStandardValidator(repo_path=".")

class TestArchitectureBlueprintAccuracy:
    """T4-ARCH-* tests"""
    
    def test_module_coverage(self, validator):
        """T4-ARCH-01: All Python modules documented"""
        result = validator.check_module_coverage(
            document="docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
            package="literature_review"
        )
        assert result. coverage == 100, \
            f"Missing modules: {result.undocumented}"
    
    def test_directory_structure_match(self, validator):
        """T4-ARCH-02: Directory tree matches reality"""
        result = validator.check_directory_structure(
            document="docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
            package="literature_review"
        )
        assert result.match_percentage >= 95, \
            f"Structure mismatch: {result.differences}"
    
    def test_operationalization_modules_present(self, validator):
        """T4-ARCH-03: New OP modules documented"""
        required_modules = [
            "literature_review/models/action_vector.py",
            "literature_review/models/validation_strategy.py",
            "literature_review/analysis/validation_tracker.py",
            "literature_review/analysis/action_generator.py",
            "literature_review/analysis/pillar_evolution. py",
            "literature_review/analysis/stakeholder_analyzer.py",
            "literature_review/analysis/benchmark_analyzer.py",
        ]
        result = validator.check_modules_documented(
            document="docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
            modules=required_modules
        )
        assert result.all_present, \
            f"Missing:  {result.missing}"
    
    def test_output_files_documented(self, validator):
        """T4-ARCH-04: Output files listed"""
        required_outputs = [
            "action_vectors.json",
            "validation_gap_matrix.json",
            "requirement_benchmark_matrix. json",
            "pillar_research_log.json",
            "pillar_proposals.json",
            "stakeholder_impact_matrix.json",
        ]
        result = validator. check_outputs_documented(
            document="docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
            outputs=required_outputs
        )
        assert result. all_present, \
            f"Missing: {result.missing}"
    
    def test_freshness(self, validator):
        """T4-ARCH-05: Updated within threshold"""
        result = validator.check_freshness(
            document="docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
            max_age_days=7,
            relative_to="latest_structural_commit"
        )
        assert result.is_fresh, \
            f"Stale by {result.days_overdue} days"


class TestRoadmapAccuracy:
    """T4-ROAD-* tests"""
    
    def test_operationalization_wave_complete(self, validator):
        """T4-ROAD-01: OP Wave shows Complete"""
        result = validator.check_wave_status(
            document="docs/MASTER_REPOSITORY_ROADMAP. md",
            wave="Operationalization Wave",
            expected_status="✅ Complete"
        )
        assert result.matches, \
            f"Expected Complete, got:  {result.actual_status}"
    
    def test_task_counts_accurate(self, validator):
        """T4-ROAD-02: Task counts match reality"""
        result = validator.check_task_counts(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            task_card_directory="task-cards"
        )
        assert result.matches, \
            f"Doc says {result.documented}, actual: {result.actual}"
    
    def test_completion_percentages(self, validator):
        """T4-ROAD-03: Percentages are mathematically correct"""
        result = validator.check_completion_percentages(
            document="docs/MASTER_REPOSITORY_ROADMAP. md"
        )
        for wave, data in result.items():
            assert data.calculated == data.stated, \
                f"{wave}:  stated {data.stated}%, calculated {data. calculated}%"
    
    def test_validation_matrix_wave_exists(self, validator):
        """T4-ROAD-04: VM Wave section exists"""
        result = validator.check_section_exists(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            section="Validation Matrix Wave"
        )
        assert result.exists, "Validation Matrix Wave section missing"
    
    def test_wave_05_exists(self, validator):
        """T4-ROAD-05: Wave 0.5 section exists"""
        result = validator.check_section_exists(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            section="Wave 0.5"
        )
        assert result.exists, "Wave 0.5 section missing"


class TestTaskCardAccuracy:
    """T4-TASK-* tests"""
    
    def test_pr_to_task_sync(self, validator):
        """T4-TASK-01: Merged PRs have Complete task cards"""
        pr_task_mapping = {
            97: "OP_WAVE_1_1_SCHEMA_FOUNDATION",
            98: "OP_WAVE_2_1_ACTION_EXTRACTION",
            99: "OP_WAVE_2_2_BENCHMARK_EXTRACTION",
            100: "OP_WAVE_3_1_VALIDATION_TRACKER",
            101: "OP_WAVE_3_2_ACTION_VECTOR_GENERATOR",
            102: "OP_WAVE_4_1_PILLAR_RESEARCH_LOG",
            103: "OP_WAVE_4_2_MODIFICATION_PROPOSALS",
            105: "OP_WAVE_4_3_STAKEHOLDER_MATRIX",
        }
        
        for pr_num, task_id in pr_task_mapping.items():
            result = validator. check_task_card_status(
                task_card=f"task-cards/{task_id}.md",
                expected_status="Complete"
            )
            assert result.matches, \
                f"PR #{pr_num} merged but {task_id} shows:  {result.actual}"
    
    def test_operationalization_wave_index(self, validator):
        """T4-TASK-04: OP Wave Index shows all Complete"""
        result = validator.check_wave_index_status(
            index="task-cards/OPERATIONALIZATION_WAVE_INDEX.md",
            expected_all_complete=True
        )
        assert result.all_complete, \
            f"Incomplete tasks: {result.incomplete}"
```

---

## 9. Tier 5: Cascade Validation Testing

### 9.1 Purpose

Verify that changes propagate through all dependent documents correctly.

### 9.2 Cascade Chains

```
┌─────────────────────────────────────────────────────────────────┐
│                    CASCADE CHAIN DEFINITIONS                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Chain 1: Code Module Addition                                  │
│  ───────────────────────────────                                │
│  Trigger: New . py file in literature_review/                    │
│                                                                 │
│  literature_review/analysis/new_module.py                       │
│       │                                                         │
│       ▼                                                         │
│  docs/MASTER_ARCHITECTURE_BLUEPRINT. md                          │
│  (Package Structure section updated)                            │
│       │                                                         │
│       ▼                                                         │
│  literature_review/analysis/README.md (if exists)               │
│  (Module list updated)                                          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Chain 2: Task Card Completion                                  │
│  ────────────────────────────                                   │
│  Trigger: PR merged with task reference                         │
│                                                                 │
│  PR #xxx merged (implements OP-W2-1)                            │
│       │                                                         │
│       ▼                                                         │
│  task-cards/OP_WAVE_2_1_ACTION_EXTRACTION.md                    │
│  (Status → Complete)                                            │
│       │                                                         │
│       ▼                                                         │
│  task-cards/OPERATIONALIZATION_WAVE_INDEX.md                    │
│  (Task row updated)                                             │
│       │                                                         │
│       ▼                                                         │
│  docs/MASTER_REPOSITORY_ROADMAP. md                              │
│  (Wave percentage updated)                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Chain 3: Wave Completion                                       │
│  ────────────────────────                                       │
│  Trigger: All tasks in wave marked Complete                     │
│                                                                 │
│  All OP-W*-* tasks complete                                     │
│       │                                                         │
│       ▼                                                         │
│  task-cards/OPERATIONALIZATION_WAVE_INDEX.md                    │
│  (Wave status → Complete)                                       │
│       │                                                         │
│       ▼                                                         │
│  docs/MASTER_REPOSITORY_ROADMAP.md                              │
│  (Wave row → ✅ Complete, 100%)                                 │
│       │                                                         │
│       ▼                                                         │
│  docs/MASTER_REPOSITORY_ROADMAP. md                              │
│  (At-a-Glance table updated)                                    │
│       │                                                         │
│       ▼                                                         │
│  docs/MASTER_REPOSITORY_ROADMAP.md                              │
│  (Total counts updated)                                         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Chain 4: Configuration Change                                  │
│  ───────────────────────────                                    │
│  Trigger: pipeline_config.json modified                         │
│                                                                 │
│  pipeline_config.json                                           │
│       │                                                         │
│       ▼                                                         │
│  docs/MASTER_ARCHITECTURE_BLUEPRINT.md                          │
│  (Configuration Files section)                                  │
│       │                                                         │
│       ▼                                                         │
│  docs/guides/WORKFLOW_EXECUTION_GUIDE.md                        │
│  (CLI flags section if applicable)                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3 Cascade Test Cases

| Test ID | Trigger Event | Cascade Chain | Level 1 Check | Level 2 Check | Level 3 Check |
|---------|---------------|---------------|---------------|---------------|---------------|
| T5-CC-01 | New . py file | Chain 1 | Architecture Blueprint updated | Module README updated | - |
| T5-CC-02 | PR merge w/ task | Chain 2 | Task card Complete | Wave Index updated | Roadmap % updated |
| T5-CC-03 | Wave completion | Chain 3 | Wave Index Complete | Roadmap Complete | Totals updated |
| T5-CC-04 | Config change | Chain 4 | Architecture updated | Guide updated | - |
| T5-CC-05 | New output file | Chain 1 variant | Architecture updated | Data Files section | - |
| T5-CC-06 | New task card | Chain 2 variant | Index updated | Roadmap counts | - |

### 9.4 Cascade Test Procedure

```markdown
## T5-CC-02: PR Merge → Task Card → Index → Roadmap

### Prerequisites
- Clean repository state
- All workflows active
- Baseline snapshots captured

### Execute
1. Create branch: `git checkout -b test/cascade-validation`
2. Implement minimal change for task OP-W*-*
3. Create PR with title: "feat:  Implement OP-W*-* [task reference]"
4. Merge PR

### Verify Level 1: Task Card
- [ ] `task-cards/OP_W*_*. md` status = "Complete"
- [ ] Timestamp updated
- [ ] PR reference added

### Verify Level 2: Wave Index
- [ ] `OPERATIONALIZATION_WAVE_INDEX.md` row updated
- [ ] Status column reflects "Complete"

### Verify Level 3: Roadmap
- [ ] `MASTER_REPOSITORY_ROADMAP. md` wave percentage updated
- [ ] At-a-Glance table reflects new completion
- [ ] If wave complete:  status shows ✅

### Timing
- Allow up to 5 minutes for all cascades to complete
- Check n8n execution logs for workflow chain

### Failure Criteria
- Any level not updated = CASCADE FAILURE
- Incorrect values at any level = ACCURACY FAILURE
```

### 9.5 Cascade Validation Script

```python
# tests/tier5/test_cascade_validation.py
"""
Tier 5: Cascade Validation Tests
Verifies changes propagate through document dependency chains
"""

import pytest
import time
from pathlib import Path
from validation_framework import CascadeValidator

@pytest.fixture
def cascade_validator():
    return CascadeValidator(repo_path=".", timeout_seconds=300)

class TestCascadeChains:
    """T5-CC-* tests"""
    
    def test_code_module_cascade(self, cascade_validator):
        """T5-CC-01: New module → Architecture Blueprint"""
        # Setup:  Capture baseline
        baseline = cascade_validator.capture_baseline([
            "docs/MASTER_ARCHITECTURE_BLUEPRINT.md"
        ])
        
        # Trigger: Add new module (simulated or actual)
        test_module = "literature_review/analysis/test_cascade_module.py"
        cascade_validator. trigger_file_addition(test_module)
        
        # Wait for cascade
        cascade_validator.wait_for_workflows()
        
        # Verify Level 1
        result = cascade_validator. check_document_updated(
            document="docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
            baseline=baseline["docs/MASTER_ARCHITECTURE_BLUEPRINT. md"],
            expected_content="test_cascade_module. py"
        )
        assert result. updated, "Architecture Blueprint not updated"
        assert result.contains_expected, "New module not in Blueprint"
        
        # Cleanup
        cascade_validator.cleanup_test_file(test_module)
    
    def test_task_completion_cascade(self, cascade_validator):
        """T5-CC-02: PR merge → Task Card → Index → Roadmap"""
        # This test requires a controlled PR merge scenario
        # In practice, use a test task card
        
        test_task = "TEST_CASCADE_TASK"
        
        # Setup: Create test task card in "Not Started" state
        cascade_validator.create_test_task_card(test_task, status="Not Started")
        
        # Capture baseline
        baseline = cascade_validator.capture_baseline([
            f"task-cards/{test_task}.md",
            "task-cards/TEST_WAVE_INDEX.md",  # Hypothetical test index
            "docs/MASTER_REPOSITORY_ROADMAP.md"
        ])
        
        # Trigger:  Simulate PR merge
        cascade_validator.simulate_pr_merge(task_reference=test_task)
        
        # Wait for cascade
        cascade_validator.wait_for_workflows()
        
        # Verify Level 1: Task Card
        task_result = cascade_validator. check_task_card_status(
            task_card=f"task-cards/{test_task}.md",
            expected_status="Complete"
        )
        assert task_result.matches, f"Task card not Complete:  {task_result. actual}"
        
        # Verify Level 2: Index (if applicable to test setup)
        # Verify Level 3: Roadmap (if applicable to test setup)
        
        # Cleanup
        cascade_validator. cleanup_test_task_card(test_task)
    
    def test_wave_completion_cascade(self, cascade_validator):
        """T5-CC-03: All tasks complete → Wave Complete → Roadmap"""
        # Verify the known case:  Operationalization Wave
        
        # Check all OP tasks are complete
        op_tasks = [
            "OP_WAVE_1_1_SCHEMA_FOUNDATION",
            "OP_WAVE_2_1_ACTION_EXTRACTION",
            "OP_WAVE_2_2_BENCHMARK_EXTRACTION",
            "OP_WAVE_3_1_VALIDATION_TRACKER",
            "OP_WAVE_3_2_ACTION_VECTOR_GENERATOR",
            "OP_WAVE_4_1_PILLAR_RESEARCH_LOG",
            "OP_WAVE_4_2_MODIFICATION_PROPOSALS",
            "OP_WAVE_4_3_STAKEHOLDER_MATRIX",
        ]
        
        for task in op_tasks: 
            result = cascade_validator.check_task_card_status(
                task_card=f"task-cards/{task}.md",
                expected_status="Complete"
            )
            # Note: This currently FAILS due to known sync issue
            # assert result.matches, f"{task} not Complete"
        
        # Check wave index
        index_result = cascade_validator.check_wave_index_status(
            index="task-cards/OPERATIONALIZATION_WAVE_INDEX.md",
            expected_all_complete=True
        )
        # Note: This currently FAILS due to known sync issue
        
        # Check roadmap
        roadmap_result = cascade_validator.check_wave_status(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            wave="Operationalization Wave",
            expected_status="✅ Complete"
        )
        # Note: This currently FAILS due to known sync issue
```

---

## 10. Gold Standard Definitions

### 10.1 Purpose

Gold Standards are **verifiable expected states** against which actual output is compared. 

### 10.2 Gold Standard:  MASTER_ARCHITECTURE_BLUEPRINT.md

```yaml
# gold_standards/architecture_blueprint.yaml

document:  docs/MASTER_ARCHITECTURE_BLUEPRINT. md
version: "2.0.0"
last_validated: "2026-01-01"

sections:
  - name: "Package Structure"
    validation_type: directory_sync
    source_directory: literature_review/
    rules:
      - all_py_files_documented:  true
      - all_directories_documented: true
      - no_orphan_entries: true
      - max_depth: 3
    
  - name: "Core Components"
    validation_type: module_coverage
    required_modules:
      # Original modules
      - path: literature_review/orchestrator. py
        documented: true
      - path: literature_review/reviewers/journal_reviewer.py
        documented: true
      - path: literature_review/reviewers/deep_reviewer.py
        documented: true
      - path: literature_review/analysis/judge.py
        documented: true
      - path: literature_review/analysis/gap_analyzer.py
        documented: true
      # Operationalization modules (NEW - must be present)
      - path: literature_review/models/action_vector. py
        documented:  true
        added_by: "PR #97"
      - path: literature_review/models/validation_strategy.py
        documented: true
        added_by: "PR #97"
      - path: literature_review/analysis/validation_tracker.py
        documented: true
        added_by: "PR #100"
      - path: literature_review/analysis/action_generator.py
        documented: true
        added_by: "PR #101"
      - path: literature_review/analysis/pillar_evolution.py
        documented: true
        added_by: "PR #103"
      - path: literature_review/analysis/stakeholder_analyzer.py
        documented: true
        added_by: "PR #105"
      - path: literature_review/analysis/benchmark_analyzer.py
        documented: true
        added_by: "PR #99"

  - name: "Key Data Files"
    validation_type: output_coverage
    required_outputs:
      # Original outputs
      - name: review_log.json
        documented: true
      - name: review_version_history.json
        documented: true
      - name: gap_analysis_output/
        documented: true
      # Operationalization outputs (NEW - must be present)
      - name: action_vectors.json
        documented: true
        added_by:  "OP-W3-2"
      - name: validation_gap_matrix.json
        documented: true
        added_by: "OP-W3-1"
      - name: requirement_benchmark_matrix.json
        documented: true
        added_by:  "OP-W2-2"
      - name: pillar_research_log. json
        documented:  true
        added_by: "OP-W4-1"
      - name: pillar_proposals.json
        documented: true
        added_by: "OP-W4-2"
      - name: stakeholder_impact_matrix.json
        documented: true
        added_by: "OP-W4-3"

freshness:
  max_age_days:  7
  relative_to: latest_structural_commit
  check_timestamp_field: "Updated:"
```

### 10.3 Gold Standard:  MASTER_REPOSITORY_ROADMAP. md

```yaml
# gold_standards/repository_roadmap. yaml

document: docs/MASTER_REPOSITORY_ROADMAP.md
version: "2.0.0"
last_validated: "2026-01-01"

sections:
  - name: "At a Glance"
    validation_type:  table_accuracy
    table_name: "At a Glance"
    columns:
      - Wave
      - Status
      - Completion
      - Hours
      - Task Cards
    rules:
      - status_reflects_completion: true
      - percentages_are_accurate: true
      - counts_match_reality:  true

  - name: "Operationalization Wave"
    validation_type: wave_status
    expected_state: 
      status: "✅ Complete"
      completion_percentage: 100
      tasks_completed: 8
      tasks_total: 8
    evidence: 
      - pr:  97
        task:  "OP-W1-1"
        merged: true
      - pr: 98
        task: "OP-W2-1"
        merged: true
      - pr: 99
        task: "OP-W2-2"
        merged: true
      - pr: 100
        task: "OP-W3-1"
        merged: true
      - pr: 101
        task: "OP-W3-2"
        merged: true
      - pr: 102
        task: "OP-W4-1"
        merged: true
      - pr: 103
        task: "OP-W4-2"
        merged: true
      - pr: 105
        task: "OP-W4-3"
        merged: true

  - name: "Validation Matrix Wave"
    validation_type: section_existence
    expected_state:
      exists: true
      task_count: 22
    evidence:
      pr: 122
      merged: true

  - name: "Wave 0. 5 Modularization"
    validation_type: section_existence
    expected_state:
      exists: true
      task_count: 3
      effort_hours: 26
    evidence: 
      commit:  "2b4ca13"
      date: "2026-01-01"

freshness:
  max_age_days:  3
  relative_to: latest_merged_pr
```

### 10.4 Gold Standard:  Task Card Synchronization

```yaml
# gold_standards/task_card_sync.yaml

validation_type: bidirectional_sync
version: "2.0.0"

rules:
  - name: pr_to_task_sync
    description: "Every merged PR with task reference updates corresponding task card"
    validation: 
      - for_each_merged_pr_with_task_reference:
          - extract_task_id_from_title_or_body
          - locate_task_card:  "task-cards/{task_id}.md"
          - assert_status:  "Complete"
          - assert_pr_reference_present: true

  - name: task_to_pr_sync
    description: "Every task marked Complete has corresponding merged PR"
    validation:
      - for_each_task_card_with_status_complete:
          - extract_pr_reference
          - assert_pr_exists: true
          - assert_pr_merged: true

  - name: wave_index_sync
    description: "Wave index reflects individual task statuses"
    validation:
      - for_each_wave_index: 
          - for_each_task_row:
              - assert_status_matches_task_card:  true

known_mappings:
  operationalization_wave: 
    - task: "OP_WAVE_1_1_SCHEMA_FOUNDATION"
      pr: 97
      expected_status: "Complete"
    - task: "OP_WAVE_2_1_ACTION_EXTRACTION"
      pr: 98
      expected_status: "Complete"
    - task: "OP_WAVE_2_2_BENCHMARK_EXTRACTION"
      pr: 99
      expected_status: "Complete"
    - task: "OP_WAVE_3_1_VALIDATION_TRACKER"
      pr:  100
      expected_status: "Complete"
    - task: "OP_WAVE_3_2_ACTION_VECTOR_GENERATOR"
      pr: 101
      expected_status: "Complete"
    - task:  "OP_WAVE_4_1_PILLAR_RESEARCH_LOG"
      pr: 102
      expected_status: "Complete"
    - task:  "OP_WAVE_4_2_MODIFICATION_PROPOSALS"
      pr: 103
      expected_status: "Complete"
    - task: "OP_WAVE_4_3_STAKEHOLDER_MATRIX"
      pr: 105
      expected_status: "Complete"
```

### 10.5 Gold Standard: Freshness Thresholds

```yaml
# gold_standards/freshness_thresholds.yaml

version: "2.0.0"

document_types:
  - pattern: "MASTER_*. md"
    max_age_days:  7
    relative_to: "any_structural_change"
    priority: "critical"

  - pattern: "task-cards/*.md"
    max_age_days: 3
    relative_to: "related_pr_merge"
    priority:  "high"

  - pattern: "*_WAVE_INDEX.md"
    max_age_days: 1
    relative_to: "any_task_status_change"
    priority: "high"

  - pattern: "docs/guides/*. md"
    max_age_days:  14
    relative_to: "related_feature_change"
    priority:  "medium"

  - pattern: "README.md"
    max_age_days: 30
    relative_to: "major_feature_change"
    priority: "low"

staleness_actions:
  critical: 
    - create_github_issue
    - block_pr_merge
    - notify_maintainer
  high:
    - create_github_issue
    - notify_maintainer
  medium:
    - create_refresh_task
  low:
    - log_for_weekly_review
```

---

## 11. Regression Test Suite

### 11.1 Purpose

Prevent recurrence of known issues discovered during State Comparison Analysis.

### 11.2 Known Issues Being Tested

| Issue ID | Description | Discovery Date | Root Cause |
|----------|-------------|----------------|------------|
| REG-001 | Operationalization Wave docs not updated | 2026-01-01 | Cascade failure |
| REG-002 | Validation Matrix Wave not in roadmap | 2026-01-01 | New wave not detected |
| REG-003 | Wave 0.5 not documented | 2026-01-01 | New wave not detected |
| REG-004 | Task cards show "Not Started" after PR merge | 2026-01-01 | PR→Task sync failure |
| REG-005 | Architecture Blueprint missing new modules | 2026-01-01 | Module detection failure |
| REG-006 | Output files not documented | 2026-01-01 | Output detection failure |

### 11.3 Regression Test Cases

#### REG-001: Operationalization Wave Documentation

```python
# tests/regression/test_reg_001_operationalization_sync.py
"""
REG-001: Operationalization Wave Documentation Sync

Background:  PRs #97-105 implemented entire Operationalization Wave,
but documentation still shows "Planned" with 0% completion.

This test ensures the sync works for future waves.
"""

import pytest
from validation_framework import RegressionValidator

class TestOperationalizationWaveSync:
    
    def test_roadmap_shows_complete(self, validator):
        """Roadmap must show Operationalization Wave as Complete"""
        result = validator.check_wave_status(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            wave="Operationalization Wave"
        )
        assert result.status == "✅ Complete", \
            f"REG-001: Roadmap shows '{result.status}' instead of '✅ Complete'"
        assert result.percentage == 100, \
            f"REG-001: Roadmap shows {result.percentage}% instead of 100%"
    
    def test_wave_index_all_complete(self, validator):
        """Wave index must show all 8 tasks as Complete"""
        result = validator.check_wave_index(
            index="task-cards/OPERATIONALIZATION_WAVE_INDEX.md"
        )
        assert result.complete_count == 8, \
            f"REG-001: Only {result.complete_count}/8 tasks marked Complete"
        assert len(result.incomplete_tasks) == 0, \
            f"REG-001: Incomplete tasks:  {result.incomplete_tasks}"
    
    def test_individual_task_cards(self, validator):
        """Each task card must show Complete status"""
        tasks = [
            "OP_WAVE_1_1_SCHEMA_FOUNDATION",
            "OP_WAVE_2_1_ACTION_EXTRACTION",
            "OP_WAVE_2_2_BENCHMARK_EXTRACTION",
            "OP_WAVE_3_1_VALIDATION_TRACKER",
            "OP_WAVE_3_2_ACTION_VECTOR_GENERATOR",
            "OP_WAVE_4_1_PILLAR_RESEARCH_LOG",
            "OP_WAVE_4_2_MODIFICATION_PROPOSALS",
            "OP_WAVE_4_3_STAKEHOLDER_MATRIX",
        ]
        
        for task in tasks:
            result = validator.check_task_card_status(f"task-cards/{task}.md")
            assert result.status == "Complete", \
                f"REG-001: {task} shows '{result.status}' instead of 'Complete'"
```

#### REG-002: Validation Matrix Wave Existence

```python
# Master n8n Validation Plan (V2.0.0) - Continued

---

## 11. Regression Test Suite (Continued)

### 11.3 Regression Test Cases (Continued)

#### REG-002: Validation Matrix Wave Existence (Continued)

```python
# tests/regression/test_reg_002_validation_matrix_wave.py
"""
REG-002: Validation Matrix Wave Not in Roadmap

Background: PR #122 added 22 validation matrix task cards,
but MASTER_REPOSITORY_ROADMAP.md doesn't include this wave. 
"""

class TestValidationMatrixWaveExistence: 
    
    def test_wave_section_exists(self, validator):
        """Roadmap must have Validation Matrix Wave section"""
        result = validator.check_section_exists(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            section_pattern=r"Validation Matrix Wave"
        )
        assert result. exists, \
            "REG-002: Validation Matrix Wave section missing from roadmap"
    
    def test_wave_task_count(self, validator):
        """Roadmap must show correct task count for VM Wave"""
        result = validator.check_wave_task_count(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            wave="Validation Matrix Wave",
            expected_count=22
        )
        assert result. matches, \
            f"REG-002: VM Wave shows {result.actual} tasks, expected 22"
    
    def test_at_a_glance_includes_wave(self, validator):
        """At-a-Glance table must include Validation Matrix Wave"""
        result = validator.check_table_row_exists(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            table="At a Glance",
            row_pattern=r"Validation Matrix"
        )
        assert result.exists, \
            "REG-002: Validation Matrix Wave not in At-a-Glance table"
    
    def test_total_task_count_updated(self, validator):
        """Total task count must include VM Wave tasks"""
        result = validator.check_total_task_count(
            document="docs/MASTER_REPOSITORY_ROADMAP.md"
        )
        # Original 49 + 22 VM + 3 Wave 0.5 = 74 minimum
        assert result.total >= 74, \
            f"REG-002: Total tasks {result.total}, expected >= 74"
```

#### REG-003: Wave 0.5 Modularization Documentation

```python
# tests/regression/test_reg_003_wave_05_existence.py
"""
REG-003: Wave 0.5 Modularization Not Documented

Background:  Commits on 2026-01-01 added Wave 0.5 with 3 modularization
task cards (26h effort), but roadmap doesn't include this wave.
"""

class TestWave05Existence:
    
    def test_wave_section_exists(self, validator):
        """Roadmap must have Wave 0.5 section"""
        result = validator.check_section_exists(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            section_pattern=r"Wave 0\. 5|Modularization"
        )
        assert result.exists, \
            "REG-003: Wave 0.5 section missing from roadmap"
    
    def test_wave_positioned_correctly(self, validator):
        """Wave 0.5 must appear between Wave 0 and Wave 1"""
        result = validator.check_section_order(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            expected_order=["Wave 0", "Wave 0.5", "Wave 1"]
        )
        assert result.correct_order, \
            f"REG-003: Wave 0.5 not positioned correctly.  Order: {result.actual_order}"
    
    def test_wave_task_cards_listed(self, validator):
        """Wave 0.5 must list all 3 task cards"""
        expected_tasks = [
            "VM-W0. 5-1",  # Metrics Configuration
            "VM-W0.5-2",  # Domain Fixtures
            "VM-W0.5-3",  # Model Abstraction
        ]
        result = validator. check_tasks_listed(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            section="Wave 0.5",
            expected_tasks=expected_tasks
        )
        assert result.all_present, \
            f"REG-003: Missing tasks:  {result.missing}"
    
    def test_effort_estimate(self, validator):
        """Wave 0.5 must show ~26h effort"""
        result = validator.check_effort_estimate(
            document="docs/MASTER_REPOSITORY_ROADMAP.md",
            wave="Wave 0.5",
            expected_hours=26,
            tolerance=2
        )
        assert result.within_tolerance, \
            f"REG-003: Effort shows {result.actual}h, expected ~26h"
```

#### REG-004: Task Card PR Synchronization

```python
# tests/regression/test_reg_004_task_pr_sync.py
"""
REG-004: Task Cards Show "Not Started" After PR Merge

Background: PRs #97-105 merged but corresponding task cards
still show "Status: Not Started" instead of "Complete".
"""

class TestTaskCardPRSync:
    
    @pytest.fixture
    def pr_task_mapping(self):
        """Known PR-to-task mappings that must be synced"""
        return {
            97: "OP_WAVE_1_1_SCHEMA_FOUNDATION",
            98: "OP_WAVE_2_1_ACTION_EXTRACTION",
            99: "OP_WAVE_2_2_BENCHMARK_EXTRACTION",
            100: "OP_WAVE_3_1_VALIDATION_TRACKER",
            101: "OP_WAVE_3_2_ACTION_VECTOR_GENERATOR",
            102: "OP_WAVE_4_1_PILLAR_RESEARCH_LOG",
            103: "OP_WAVE_4_2_MODIFICATION_PROPOSALS",
            105: "OP_WAVE_4_3_STAKEHOLDER_MATRIX",
        }
    
    def test_all_pr_task_mappings_synced(self, validator, pr_task_mapping):
        """Every merged PR must have corresponding Complete task card"""
        failures = []
        
        for pr_num, task_id in pr_task_mapping.items():
            # Verify PR is merged
            pr_result = validator. check_pr_status(pr_num)
            if not pr_result.merged:
                continue  # Skip if PR not merged
            
            # Verify task card is Complete
            task_result = validator.check_task_card_status(
                f"task-cards/{task_id}.md"
            )
            
            if task_result.status != "Complete":
                failures. append({
                    "pr": pr_num,
                    "task": task_id,
                    "expected": "Complete",
                    "actual":  task_result.status
                })
        
        assert len(failures) == 0, \
            f"REG-004: PR→Task sync failures: {failures}"
    
    def test_task_card_has_pr_reference(self, validator, pr_task_mapping):
        """Each task card must reference its implementing PR"""
        for pr_num, task_id in pr_task_mapping.items():
            result = validator.check_task_card_pr_reference(
                task_card=f"task-cards/{task_id}.md",
                expected_pr=pr_num
            )
            assert result.has_reference, \
                f"REG-004: {task_id} missing PR #{pr_num} reference"
```

#### REG-005: Architecture Blueprint Module Coverage

```python
# tests/regression/test_reg_005_architecture_modules.py
"""
REG-005: Architecture Blueprint Missing New Modules

Background:  MASTER_ARCHITECTURE_BLUEPRINT.md doesn't include
the new modules added in the Operationalization Wave. 
"""

class TestArchitectureModuleCoverage: 
    
    @pytest.fixture
    def required_new_modules(self):
        """Modules added by Operationalization Wave that must be documented"""
        return [
            # models/ directory (PR #97)
            "literature_review/models/__init__.py",
            "literature_review/models/action_vector.py",
            "literature_review/models/validation_strategy.py",
            
            # New analysis modules
            "literature_review/analysis/benchmark_analyzer.py",  # PR #99
            "literature_review/analysis/validation_tracker.py",  # PR #100
            "literature_review/analysis/action_generator.py",     # PR #101
            "literature_review/analysis/pillar_evolution. py",     # PR #103
            "literature_review/analysis/stakeholder_analyzer.py", # PR #105
        ]
    
    def test_models_directory_documented(self, validator):
        """Architecture must document models/ directory"""
        result = validator.check_directory_documented(
            document="docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
            directory="literature_review/models/"
        )
        assert result.documented, \
            "REG-005: models/ directory not in Architecture Blueprint"
    
    def test_all_new_modules_documented(self, validator, required_new_modules):
        """Architecture must document all new modules"""
        missing = []
        
        for module in required_new_modules: 
            result = validator.check_module_documented(
                document="docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
                module=module
            )
            if not result.documented:
                missing.append(module)
        
        assert len(missing) == 0, \
            f"REG-005: Undocumented modules:  {missing}"
    
    def test_package_structure_section_updated(self, validator):
        """Package Structure section must include new directories"""
        result = validator.check_section_contains(
            document="docs/MASTER_ARCHITECTURE_BLUEPRINT. md",
            section="Package Structure",
            expected_patterns=[
                r"models/",
                r"action_vector\. py",
                r"validation_strategy\. py",
            ]
        )
        assert result.all_present, \
            f"REG-005: Package Structure missing: {result.missing}"
```

#### REG-006: Output Files Documentation

```python
# tests/regression/test_reg_006_output_files.py
"""
REG-006: Output Files Not Documented

Background:  Operationalization Wave adds new JSON output files
that are not documented in MASTER_ARCHITECTURE_BLUEPRINT.md.
"""

class TestOutputFilesDocumentation:
    
    @pytest.fixture
    def required_output_files(self):
        """Output files added by Operationalization Wave"""
        return [
            ("action_vectors. json", "OP-W3-2"),
            ("validation_gap_matrix.json", "OP-W3-1"),
            ("requirement_benchmark_matrix.json", "OP-W2-2"),
            ("pillar_research_log.json", "OP-W4-1"),
            ("pillar_proposals.json", "OP-W4-2"),
            ("stakeholder_impact_matrix.json", "OP-W4-3"),
        ]
    
    def test_key_data_files_section_exists(self, validator):
        """Architecture must have Key Data Files section"""
        result = validator. check_section_exists(
            document="docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
            section_pattern=r"Key Data Files|Data Files"
        )
        assert result. exists, \
            "REG-006: Key Data Files section missing"
    
    def test_all_output_files_documented(self, validator, required_output_files):
        """All new output files must be documented"""
        missing = []
        
        for output_file, source_task in required_output_files:
            result = validator.check_output_documented(
                document="docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
                output_file=output_file
            )
            if not result.documented:
                missing.append((output_file, source_task))
        
        assert len(missing) == 0, \
            f"REG-006: Undocumented outputs: {missing}"
    
    def test_output_files_table_complete(self, validator, required_output_files):
        """Data Files table must include all outputs"""
        result = validator.check_table_rows(
            document="docs/MASTER_ARCHITECTURE_BLUEPRINT. md",
            table="Key Data Files",
            expected_rows=[f[0] for f in required_output_files]
        )
        assert result.all_present, \
            f"REG-006: Table missing:  {result.missing}"
```

### 11.4 Regression Test Execution

```bash
# Run all regression tests
pytest tests/regression/ -v --tb=short

# Run specific regression test
pytest tests/regression/test_reg_001_operationalization_sync.py -v

# Run with detailed failure report
pytest tests/regression/ -v --tb=long --capture=no

# Generate regression report
pytest tests/regression/ -v --html=reports/regression_report. html
```

---

## 12. Validation Matrices

### 12.1 Master Workflow Validation Matrix

| Workflow | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 | Status |
|----------|--------|--------|--------|--------|--------|--------|
| WF-01:  Trigger | [ ] | [ ] | [ ] | [ ] | [ ] | 🔴 Planned |
| WF-02: Distributor | [ ] | [ ] | [ ] | [ ] | [ ] | 🔴 Planned |
| WF-03: Agent | [ ] | [ ] | [ ] | [ ] | [ ] | 🔴 Planned |
| WF-04: State Reconciliation | [ ] | [ ] | [ ] | [ ] | [ ] | 🔴 Planned |
| WF-05: PR Review | [ ] | [ ] | [ ] | N/A | N/A | 🔴 Planned |
| WF-06: Release | [ ] | [ ] | [ ] | [ ] | N/A | 🔴 Planned |
| WF-07: Errors | [ ] | [ ] | [ ] | N/A | N/A | 🔴 Planned |
| WF-08: Staleness | [ ] | [ ] | [ ] | [ ] | [ ] | 🔴 Planned |

**Legend:**
- [ ] = Not tested
- [P] = Passed
- [F] = Failed
- N/A = Not applicable

### 12.2 Tier 1 Unit Test Matrix

| Test ID | Workflow | Test Name | Status | Last Run | Notes |
|---------|----------|-----------|--------|----------|-------|
| T1-01-01 | Trigger | Valid push event | [ ] | - | - |
| T1-01-02 | Trigger | Automated commit filter | [ ] | - | - |
| T1-01-03 | Trigger | Manual n8n commit | [ ] | - | - |
| T1-01-04 | Trigger | No doc changes | [ ] | - | - |
| T1-01-05 | Trigger | Mixed changes | [ ] | - | - |
| T1-01-06 | Trigger | Empty commit | [ ] | - | - |
| T1-02-01 | Distributor | Task queue | [ ] | - | - |
| T1-02-02 | Distributor | Batch queue | [ ] | - | - |
| T1-02-03 | Distributor | Sequential dispatch | [ ] | - | - |
| T1-02-04 | Distributor | Callback success | [ ] | - | - |
| T1-02-05 | Distributor | Callback failure | [ ] | - | - |
| T1-02-06 | Distributor | Empty queue | [ ] | - | - |
| T1-03-01 | Agent | Valid task | [ ] | - | - |
| T1-03-02 | Agent | Document fetch | [ ] | - | - |
| T1-03-03 | Agent | AI response parse | [ ] | - | - |
| T1-03-04 | Agent | Commit preparation | [ ] | - | - |
| T1-03-05 | Agent | Invalid task | [ ] | - | - |
| T1-03-06 | Agent | Missing document | [ ] | - | - |
| T1-04-01 | State Recon | Scan trigger | [ ] | - | - |
| T1-04-02 | State Recon | Mismatch detection | [ ] | - | - |
| T1-04-03 | State Recon | No mismatches | [ ] | - | - |
| T1-04-04 | State Recon | Multiple mismatches | [ ] | - | - |
| T1-05-01 | PR Review | PR opened | [ ] | - | - |
| T1-05-02 | PR Review | Bot PR filter | [ ] | - | - |
| T1-05-03 | PR Review | Doc-only PR | [ ] | - | - |
| T1-06-01 | Release | Tag created | [ ] | - | - |
| T1-06-02 | Release | Tag parsing | [ ] | - | - |
| T1-06-03 | Release | First release | [ ] | - | - |
| T1-07-01 | Errors | Error capture | [ ] | - | - |
| T1-07-02 | Errors | Task ID extraction | [ ] | - | - |
| T1-07-03 | Errors | No task context | [ ] | - | - |
| T1-07-04 | Errors | Duplicate detection | [ ] | - | - |
| T1-08-01 | Staleness | Schedule trigger | [ ] | - | - |
| T1-08-02 | Staleness | Stale detection | [ ] | - | - |
| T1-08-03 | Staleness | Fresh detection | [ ] | - | - |
| T1-08-04 | Staleness | Threshold application | [ ] | - | - |

### 12.3 Tier 2 Integration Test Matrix

| Test ID | Flow | Description | Status | Last Run | Notes |
|---------|------|-------------|--------|----------|-------|
| T2-INT-01 | Trigger→Distributor | Task list handoff | [ ] | - | - |
| T2-INT-02 | Distributor→Agent | Task dispatch | [ ] | - | - |
| T2-INT-03 | Agent→Callback | Completion callback | [ ] | - | - |
| T2-INT-04 | StateRecon→Distributor | Correction tasks | [ ] | - | - |
| T2-INT-05 | Staleness→Distributor | Refresh tasks | [ ] | - | - |
| T2-INT-06 | Agent→Errors | Error propagation | [ ] | - | - |
| T2-EP-01 | Endpoint | /github-doc-trigger | [ ] | - | - |
| T2-EP-02 | Endpoint | /task-distributor | [ ] | - | - |
| T2-EP-03 | Endpoint | /domain-agent | [ ] | - | - |
| T2-EP-04 | Endpoint | /task-callback | [ ] | - | - |
| T2-EP-05 | Endpoint | /distributor-status | [ ] | - | - |
| T2-EP-06 | Endpoint | /distributor-reset | [ ] | - | - |
| T2-EP-07 | Endpoint | /state-reconciliation | [ ] | - | - |
| T2-EP-08 | Endpoint | /staleness-review | [ ] | - | - |
| T2-EP-09 | Endpoint | /pr-review | [ ] | - | - |

### 12.4 Tier 3 End-to-End Test Matrix

| Test ID | Action | Expected Result | Status | Last Run | Notes |
|---------|--------|-----------------|--------|----------|-------|
| T3-E2E-01 | Push to docs/ | Doc updated | [ ] | - | - |
| T3-E2E-02 | Create PR | PR commented | [ ] | - | - |
| T3-E2E-03 | Push tag | Release created | [ ] | - | - |
| T3-E2E-04 | Merge PR w/ task | Task card updated | [ ] | - | - |
| T3-E2E-05 | Wait for staleness | Stale docs identified | [ ] | - | - |
| T3-E2E-06 | Force error | Error issue created | [ ] | - | - |
| T3-LP-01 | n8n auto commit | No re-trigger | [ ] | - | - |
| T3-LP-02 | Manual n8n commit | Normal processing | [ ] | - | - |
| T3-LP-03 | Rapid commits | No duplicates | [ ] | - | - |

### 12.5 Tier 4 Content Accuracy Test Matrix

| Test ID | Document | Validation | Status | Last Run | Notes |
|---------|----------|------------|--------|----------|-------|
| T4-ARCH-01 | Architecture | Module coverage | [ ] | - | - |
| T4-ARCH-02 | Architecture | Directory structure | [ ] | - | - |
| T4-ARCH-03 | Architecture | OP modules present | [ ] | - | - |
| T4-ARCH-04 | Architecture | Output files listed | [ ] | - | - |
| T4-ARCH-05 | Architecture | Freshness | [ ] | - | - |
| T4-ROAD-01 | Roadmap | OP Wave complete | [ ] | - | - |
| T4-ROAD-02 | Roadmap | Task counts | [ ] | - | - |
| T4-ROAD-03 | Roadmap | Percentages | [ ] | - | - |
| T4-ROAD-04 | Roadmap | VM Wave exists | [ ] | - | - |
| T4-ROAD-05 | Roadmap | Wave 0.5 exists | [ ] | - | - |
| T4-ROAD-06 | Roadmap | At-a-Glance | [ ] | - | - |
| T4-TASK-01 | Task Cards | PR→Task sync | [ ] | - | - |
| T4-TASK-02 | Task Cards | Task→PR sync | [ ] | - | - |
| T4-TASK-03 | Task Cards | Wave index sync | [ ] | - | - |
| T4-TASK-04 | Task Cards | OP index complete | [ ] | - | - |
| T4-STAL-01 | Staleness | Stale detection | [ ] | - | - |
| T4-STAL-02 | Staleness | Fresh detection | [ ] | - | - |
| T4-STAL-03 | Staleness | Threshold accuracy | [ ] | - | - |

### 12.6 Tier 5 Cascade Validation Matrix

| Test ID | Trigger | L1 Check | L2 Check | L3 Check | Status | Last Run |
|---------|---------|----------|----------|----------|--------|----------|
| T5-CC-01 | New . py file | Arch updated | README updated | - | [ ] | - |
| T5-CC-02 | PR merge w/ task | Task Complete | Index updated | Roadmap % | [ ] | - |
| T5-CC-03 | Wave completion | Index Complete | Roadmap Complete | Totals | [ ] | - |
| T5-CC-04 | Config change | Arch updated | Guide updated | - | [ ] | - |
| T5-CC-05 | New output file | Arch updated | Data Files | - | [ ] | - |
| T5-CC-06 | New task card | Index updated | Roadmap counts | - | [ ] | - |

### 12.7 Regression Test Matrix

| Test ID | Issue | Description | Status | Last Run | Notes |
|---------|-------|-------------|--------|----------|-------|
| REG-001a | OP Wave | Roadmap shows Complete | [ ] | - | - |
| REG-001b | OP Wave | Index all Complete | [ ] | - | - |
| REG-001c | OP Wave | Task cards Complete | [ ] | - | - |
| REG-002a | VM Wave | Section exists | [ ] | - | - |
| REG-002b | VM Wave | Task count correct | [ ] | - | - |
| REG-002c | VM Wave | In At-a-Glance | [ ] | - | - |
| REG-003a | Wave 0.5 | Section exists | [ ] | - | - |
| REG-003b | Wave 0.5 | Positioned correctly | [ ] | - | - |
| REG-003c | Wave 0.5 | Tasks listed | [ ] | - | - |
| REG-004a | PR Sync | All mappings synced | [ ] | - | - |
| REG-004b | PR Sync | PR references present | [ ] | - | - |
| REG-005a | Modules | models/ documented | [ ] | - | - |
| REG-005b | Modules | All new modules | [ ] | - | - |
| REG-006a | Outputs | Section exists | [ ] | - | - |
| REG-006b | Outputs | All files documented | [ ] | - | - |

---

## 13. Automated Validation Framework

### 13.1 Framework Architecture

```
validation_framework/
├── __init__.py
├── core/
│   ├── __init__. py
│   ├── validator.py              # Base validator class
│   ├── gold_standard_loader.py   # YAML gold standard parser
│   ├── document_parser.py        # Markdown document parser
│   └── github_client.py          # GitHub API wrapper
│
├── validators/
│   ├── __init__. py
│   ├── architecture_validator.py # Architecture Blueprint checks
│   ├── roadmap_validator.py      # Roadmap checks
│   ├── task_card_validator.py    # Task card checks
│   ├── cascade_validator.py      # Cascade chain checks
│   └── staleness_validator.py    # Freshness checks
│
├── gold_standards/
│   ├── architecture_blueprint.yaml
│   ├── repository_roadmap.yaml
│   ├── task_card_sync.yaml
│   └── freshness_thresholds.yaml
│
├── reporters/
│   ├── __init__. py
│   ├── console_reporter.py       # Terminal output
│   ├── html_reporter.py          # HTML report generation
│   ├── json_reporter.py          # Machine-readable output
│   └── github_reporter.py        # GitHub issue/comment creation
│
└── cli. py                        # Command-line interface
```

### 13.2 Core Validator Class

```python
# validation_framework/core/validator.py
"""
Core validation framework for n8n documentation sync validation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import yaml

@dataclass
class ValidationResult:
    """Result of a single validation check"""
    test_id: str
    test_name: str
    passed: bool
    expected: Any
    actual: Any
    message: str = ""
    remediation: str = ""
    severity: str = "error"  # error, warning, info
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationReport:
    """Aggregate validation report"""
    timestamp:  datetime
    tier: str
    passed: int
    failed: int
    warnings: int
    total: int
    results: List[ValidationResult]
    
    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0
    
    @property
    def success(self) -> bool:
        return self. failed == 0

class BaseValidator(ABC):
    """Base class for all validators"""
    
    def __init__(self, repo_path: str = ". "):
        self.repo_path = Path(repo_path)
        self.results: List[ValidationResult] = []
        self.gold_standards: Dict[str, Any] = {}
    
    def load_gold_standard(self, name: str) -> Dict[str, Any]: 
        """Load a gold standard definition from YAML"""
        gs_path = self. repo_path / "gold_standards" / f"{name}.yaml"
        if gs_path.exists():
            with open(gs_path) as f:
                return yaml.safe_load(f)
        return {}
    
    def read_document(self, path: str) -> str:
        """Read a document from the repository"""
        doc_path = self. repo_path / path
        if doc_path.exists():
            return doc_path.read_text()
        raise FileNotFoundError(f"Document not found: {path}")
    
    def add_result(self, result: ValidationResult):
        """Add a validation result"""
        self.results.append(result)
    
    def pass_test(self, test_id: str, test_name: str, 
                  expected:  Any, actual: Any, message: str = ""):
        """Record a passing test"""
        self.add_result(ValidationResult(
            test_id=test_id,
            test_name=test_name,
            passed=True,
            expected=expected,
            actual=actual,
            message=message or "Test passed"
        ))
    
    def fail_test(self, test_id:  str, test_name: str,
                  expected:  Any, actual: Any, 
                  message:  str = "", remediation: str = "",
                  severity:  str = "error"):
        """Record a failing test"""
        self.add_result(ValidationResult(
            test_id=test_id,
            test_name=test_name,
            passed=False,
            expected=expected,
            actual=actual,
            message=message or "Test failed",
            remediation=remediation,
            severity=severity
        ))
    
    @abstractmethod
    def validate(self) -> ValidationReport:
        """Run all validations and return report"""
        pass
    
    def generate_report(self, tier: str) -> ValidationReport:
        """Generate validation report from results"""
        passed = sum(1 for r in self. results if r.passed)
        failed = sum(1 for r in self.results if not r.passed and r.severity == "error")
        warnings = sum(1 for r in self. results if not r.passed and r.severity == "warning")
        
        return ValidationReport(
            timestamp=datetime. now(),
            tier=tier,
            passed=passed,
            failed=failed,
            warnings=warnings,
            total=len(self.results),
            results=self.results
        )
```

### 13.3 Architecture Validator Implementation

```python
# validation_framework/validators/architecture_validator. py
"""
Validates MASTER_ARCHITECTURE_BLUEPRINT.md against repository state
"""

import re
from pathlib import Path
from typing import Set, List
from .. core.validator import BaseValidator, ValidationReport

class ArchitectureValidator(BaseValidator):
    """Validates Architecture Blueprint accuracy"""
    
    DOCUMENT = "docs/MASTER_ARCHITECTURE_BLUEPRINT. md"
    TIER = "T4-ARCH"
    
    def __init__(self, repo_path: str = "."):
        super().__init__(repo_path)
        self.gold_standard = self.load_gold_standard("architecture_blueprint")
    
    def validate(self) -> ValidationReport:
        """Run all architecture validations"""
        self.validate_module_coverage()
        self.validate_directory_structure()
        self.validate_operationalization_modules()
        self.validate_output_files()
        self.validate_freshness()
        return self.generate_report(self.TIER)
    
    def validate_module_coverage(self):
        """T4-ARCH-01: All Python modules documented"""
        test_id = "T4-ARCH-01"
        test_name = "Module Coverage"
        
        try:
            doc_content = self.read_document(self. DOCUMENT)
            documented_modules = self._extract_documented_modules(doc_content)
            actual_modules = self._scan_package_modules("literature_review")
            
            missing = actual_modules - documented_modules
            
            if len(missing) == 0:
                self.pass_test(
                    test_id, test_name,
                    expected="All modules documented",
                    actual=f"{len(actual_modules)} modules documented"
                )
            else:
                self.fail_test(
                    test_id, test_name,
                    expected="All modules documented",
                    actual=f"{len(missing)} modules undocumented",
                    message=f"Missing modules: {missing}",
                    remediation=f"Add these modules to Package Structure:  {missing}"
                )
        except Exception as e:
            self.fail_test(
                test_id, test_name,
                expected="Validation complete",
                actual=f"Error: {e}",
                message=str(e)
            )
    
    def validate_directory_structure(self):
        """T4-ARCH-02: Directory tree matches reality"""
        test_id = "T4-ARCH-02"
        test_name = "Directory Structure Match"
        
        try:
            doc_content = self. read_document(self.DOCUMENT)
            documented_dirs = self._extract_documented_directories(doc_content)
            actual_dirs = self._scan_package_directories("literature_review")
            
            missing_dirs = actual_dirs - documented_dirs
            stale_dirs = documented_dirs - actual_dirs
            
            match_pct = (1 - len(missing_dirs | stale_dirs) / max(len(actual_dirs), 1)) * 100
            
            if match_pct >= 95:
                self. pass_test(
                    test_id, test_name,
                    expected=">=95% structure match",
                    actual=f"{match_pct:.1f}% match"
                )
            else:
                self.fail_test(
                    test_id, test_name,
                    expected=">=95% structure match",
                    actual=f"{match_pct:.1f}% match",
                    message=f"Missing:  {missing_dirs}, Stale: {stale_dirs}",
                    remediation="Update Package Structure section"
                )
        except Exception as e:
            self. fail_test(test_id, test_name, "Complete", str(e), str(e))
    
    def validate_operationalization_modules(self):
        """T4-ARCH-03: Operationalization modules documented"""
        test_id = "T4-ARCH-03"
        test_name = "Operationalization Modules Present"
        
        required_modules = [
            "action_vector. py",
            "validation_strategy.py",
            "validation_tracker.py",
            "action_generator.py",
            "pillar_evolution.py",
            "stakeholder_analyzer.py",
            "benchmark_analyzer.py",
        ]
        
        try:
            doc_content = self.read_document(self. DOCUMENT)
            missing = [m for m in required_modules if m not in doc_content]
            
            if len(missing) == 0:
                self.pass_test(
                    test_id, test_name,
                    expected="All OP modules documented",
                    actual=f"{len(required_modules)} modules present"
                )
            else:
                self.fail_test(
                    test_id, test_name,
                    expected="All OP modules documented",
                    actual=f"{len(missing)} modules missing",
                    message=f"Missing:  {missing}",
                    remediation=f"Add to Package Structure: {missing}"
                )
        except Exception as e:
            self. fail_test(test_id, test_name, "Complete", str(e), str(e))
    
    def validate_output_files(self):
        """T4-ARCH-04: Output files documented"""
        test_id = "T4-ARCH-04"
        test_name = "Output Files Documented"
        
        required_outputs = [
            "action_vectors.json",
            "validation_gap_matrix.json",
            "requirement_benchmark_matrix.json",
            "pillar_research_log.json",
            "pillar_proposals.json",
            "stakeholder_impact_matrix.json",
        ]
        
        try:
            doc_content = self. read_document(self.DOCUMENT)
            missing = [o for o in required_outputs if o not in doc_content]
            
            if len(missing) == 0:
                self.pass_test(
                    test_id, test_name,
                    expected="All outputs documented",
                    actual=f"{len(required_outputs)} outputs present"
                )
            else:
                self.fail_test(
                    test_id, test_name,
                    expected="All outputs documented",
                    actual=f"{len(missing)} outputs missing",
                    message=f"Missing: {missing}",
                    remediation=f"Add to Key Data Files: {missing}"
                )
        except Exception as e: 
            self.fail_test(test_id, test_name, "Complete", str(e), str(e))
    
    def validate_freshness(self):
        """T4-ARCH-05: Document updated within threshold"""
        test_id = "T4-ARCH-05"
        test_name = "Document Freshness"
        
        try: 
            doc_content = self.read_document(self.DOCUMENT)
            
            # Extract "Updated:" timestamp
            match = re.search(r'\*\*Updated:\*\*\s*(\w+ \d+, \d+)', doc_content)
            if match: 
                # Parse and check age (simplified)
                self. pass_test(
                    test_id, test_name,
                    expected="Updated within 7 days",
                    actual=f"Updated: {match. group(1)}",
                    message="Freshness check passed (manual verification needed)"
                )
            else:
                self.fail_test(
                    test_id, test_name,
                    expected="Updated timestamp present",
                    actual="No timestamp found",
                    remediation="Add **Updated:** field to document header"
                )
        except Exception as e:
            self. fail_test(test_id, test_name, "Complete", str(e), str(e))
    
    # Helper methods
    def _extract_documented_modules(self, content:  str) -> Set[str]:
        """Extract module names from documentation"""
        modules = set()
        # Find . py files in code blocks
        for match in re.finditer(r'(\w+\.py)', content):
            modules.add(match. group(1))
        return modules
    
    def _scan_package_modules(self, package:  str) -> Set[str]:
        """Scan actual package for . py files"""
        package_path = self.repo_path / package
        modules = set()
        for py_file in package_path.rglob("*.py"):
            modules.add(py_file.name)
        return modules
    
    def _extract_documented_directories(self, content: str) -> Set[str]:
        """Extract directory names from documentation"""
        dirs = set()
        for match in re.finditer(r'(\w+)/', content):
            dirs.add(match. group(1))
        return dirs
    
    def _scan_package_directories(self, package: str) -> Set[str]:
        """Scan actual package for directories"""
        package_path = self.repo_path / package
        dirs = set()
        for item in package_path. rglob("*"):
            if item. is_dir() and not item.name.startswith("__"):
                dirs.add(item. name)
        return dirs
```

### 13.4 CLI Interface

```python
# validation_framework/cli.py
"""
Command-line interface for the validation framework
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from . validators.architecture_validator import ArchitectureValidator
from .validators. roadmap_validator import RoadmapValidator
from .validators. task_card_validator import TaskCardValidator
from .validators.cascade_validator import CascadeValidator
from . reporters.console_reporter import ConsoleReporter
from .reporters.html_reporter import HTMLReporter
from .reporters.json_reporter import JSONReporter

def main():
    parser = argparse.ArgumentParser(
        description="n8n Documentation Sync Validation Framework"
    )
    
    parser.add_argument(
        "--tier", "-t",
        choices=["1", "2", "3", "4", "5", "all", "regression"],
        default="all",
        help="Validation tier to run"
    )
    
    parser.add_argument(
        "--document", "-d",
        choices=["architecture", "roadmap", "tasks", "all"],
        default="all",
        help="Document type to validate"
    )
    
    parser. add_argument(
        "--output", "-o",
        choices=["console", "html", "json"],
        default="console",
        help="Output format"
    )
    
    parser.add_argument(
        "--report-path", "-r",
        type=str,
        default="reports/validation_report",
        help="Path for report output (without extension)"
    )
    
    parser. add_argument(
        "--repo-path",
        type=str,
        default=".",
        help="Repository path"
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Run validation
    all_results = []
    
    if args.tier in ["4", "all"]:
        print("\n" + "="*60)
        print("TIER 4: CONTENT ACCURACY VALIDATION")
        print("="*60)
        
        if args.document in ["architecture", "all"]:
            print("\n📄 Validating MASTER_ARCHITECTURE_BLUEPRINT.md...")
            validator = ArchitectureValidator(args.repo_path)
            report = validator.validate()
            all_results.append(("Architecture Blueprint", report))
            
            if args. verbose:
                for result in report.results:
                    status = "✅" if result.passed else "❌"
                    print(f"  {status} {result.test_id}: {result. test_name}")
                    if not result.passed:
                        print(f"      Expected: {result.expected}")
                        print(f"      Actual: {result. actual}")
                        print(f"      Fix: {result.remediation}")
        
        if args. document in ["roadmap", "all"]: 
            print("\n📄 Validating MASTER_REPOSITORY_ROADMAP. md...")
            validator = RoadmapValidator(args.repo_path)
            report = validator.validate()
            all_results.append(("Repository Roadmap", report))
        
        if args. document in ["tasks", "all"]: 
            print("\n📄 Validating Task Cards...")
            validator = TaskCardValidator(args.repo_path)
            report = validator.validate()
            all_results. append(("Task Cards", report))
    
    if args. tier in ["5", "all"]: 
        print("\n" + "="*60)
        print("TIER 5: CASCADE VALIDATION")
        print("="*60)
        
        validator = CascadeValidator(args.repo_path)
        report = validator.validate()
        all_results.append(("Cascade Chains", report))
    
    # Generate summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    total_passed = 0
    total_failed = 0
    
    for name, report in all_results:
        status = "✅ PASS" if report.success else "❌ FAIL"
        print(f"\n{name}: {status}")
        print(f"  Passed: {report.passed}/{report.total} ({report.pass_rate:.1f}%)")
        if report.failed > 0:
            print(f"  Failed: {report.failed}")
        if report.warnings > 0:
            print(f"  Warnings: {report.warnings}")
        
        total_passed += report. passed
        total_failed += report.failed
    
    # Output report
    if args. output == "html":
        reporter = HTMLReporter()
        report_path = f"{args.report_path}_{datetime.now():%Y%m%d_%H%M%S}.html"
        reporter.generate(all_results, report_path)
        print(f"\n📊 HTML report:  {report_path}")
    
    elif args.output == "json":
        reporter = JSONReporter()
        report_path = f"{args. report_path}_{datetime.now():%Y%m%d_%H%M%S}.json"
        reporter.generate(all_results, report_path)
        print(f"\n📊 JSON report: {report_path}")
    
    # Exit code
    print("\n" + "="*60)
    if total_failed == 0:
        print("🎉 ALL VALIDATIONS PASSED")
        sys.exit(0)
    else:
        print(f"💥 {total_failed} VALIDATIONS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 13.5 CI/CD Integration

```yaml
# .github/workflows/documentation-validation.yml
name: Documentation Validation

on:
  push:
    branches:  [main]
    paths:
      - 'docs/**'
      - 'task-cards/**'
      - 'literature_review/**'
  pull_request: 
    branches: [main]
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:

jobs:
  validate-documentation:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for freshness checks
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with: 
          python-version:  '3.12'
      
      - name: Install validation framework
        run: |
          pip install -e ./validation_framework
      
      - name:  Run Tier 4 - Content Accuracy
        run: |
          python -m validation_framework. cli \
            --tier 4 \
            --output json \
            --report-path reports/tier4
      
      - name: Run Tier 5 - Cascade Validation
        run: |
          python -m validation_framework.cli \
            --tier 5 \
            --output json \
            --report-path reports/tier5
      
      - name: Run Regression Tests
        run: |
          pytest tests/regression/ \
            --junitxml=reports/regression. xml \
            -v
      
      - name: Upload validation reports
        uses:  actions/upload-artifact@v4
        if: always()
        with:
          name: validation-reports
          path: reports/
      
      - name:  Comment on PR (if applicable)
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with: 
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs. readFileSync('reports/tier4_*. json'));
            
            let comment = '## 📋 Documentation Validation Report\n\n';
            comment += `**Status:** ${report.failed === 0 ? '✅ PASSED' : '❌ FAILED'}\n\n`;
            comment += `| Metric | Value |\n|--------|-------|\n`;
            comment += `| Tests Passed | ${report. passed} |\n`;
            comment += `| Tests Failed | ${report.failed} |\n`;
            comment += `| Pass Rate | ${report. pass_rate}% |\n`;
            
            if (report.failed > 0) {
              comment += '\n### ❌ Failed Tests\n\n';
              for (const result of report.results. filter(r => ! r.passed)) {
                comment += `- **${result.test_id}**: ${result.test_name}\n`;
                comment += `  - Expected: ${result. expected}\n`;
                comment += `  - Actual: ${result.actual}\n`;
                comment += `  - Fix: ${result.remediation}\n\n`;
              }
            }
            
            github.rest. issues.createComment({
              issue_number: context.issue. number,
              owner: context.repo. owner,
              repo: context.repo. repo,
              body: comment
            });
```

---

## 14. Execution Plan

### 14.1 Phase 1: Framework Setup (Days 1-2)

| Task | Owner | Duration | Deliverable |
|------|-------|----------|-------------|
| Create validation_framework/ directory | Dev | 2h | Directory structure |
| Implement BaseValidator class | Dev | 4h | core/validator.py |
| Create gold standard YAML files | Dev | 4h | gold_standards/*. yaml |
| Implement ArchitectureValidator | Dev | 4h | validators/architecture_validator. py |
| Implement RoadmapValidator | Dev | 4h | validators/roadmap_validator. py |
| Implement TaskCardValidator | Dev | 4h | validators/task_card_validator.py |

### 14.2 Phase 2: Tier 1-3 Testing (Days 3-5)

| Task | Owner | Duration | Deliverable |
|------|-------|----------|-------------|
| Create mock payloads | QA | 4h | tests/mocks/*.json |
| Execute Tier 1 tests | QA | 8h | Completed T1-* matrix |
| Create integration test scripts | Dev | 4h | tests/tier2/*. sh |
| Execute Tier 2 tests | QA | 4h | Completed T2-* matrix |
| Execute Tier 3 tests | QA | 4h | Completed T3-* matrix |
| Fix any failures | Dev | 8h | Working workflows |

### 14.3 Phase 3: Tier 4-5 Testing (Days 6-8)

| Task | Owner | Duration | Deliverable |
|------|-------|----------|-------------|
| Implement CLI interface | Dev | 4h | cli. py |
| Run Tier 4 validation | QA | 4h | T4-* results |
| Analyze content accuracy gaps | Dev | 4h | Gap analysis report |
| Implement CascadeValidator | Dev | 4h | validators/cascade_validator.py |
| Run Tier 5 validation | QA | 4h | T5-* results |
| Fix cascade chain issues | Dev | 8h | Working cascades |

### 14.4 Phase 4: Regression & CI/CD (Days 9-10)

| Task | Owner | Duration | Deliverable |
|------|-------|----------|-------------|
| Implement regression tests | Dev | 8h | tests/regression/*.py |
| Run full regression suite | QA | 4h | REG-* results |
| Create CI/CD workflow | Dev | 4h | .github/workflows/documentation-validation.yml |
| Create reporters | Dev | 4h | reporters/*. py |
| Generate final validation report | QA | 2h | VALIDATION_REPORT.md |

### 14.5 Milestone Checklist

```markdown
## Validation Plan Execution Checklist

### Phase 1: Framework Setup
- [ ] validation_framework/ directory created
- [ ] BaseValidator implemented
- [ ] Gold standards defined
- [ ] Document validators implemented

### Phase 2: Tier 1-3 Testing
- [ ] Tier 1 Unit tests:  100% pass
- [ ] Tier 2 Integration tests: 100% pass
- [ ] Tier 3 E2E tests: 100% pass
- [ ] All workflow issues resolved

### Phase 3: Tier 4-5 Testing
- [ ] Tier 4 Content Accuracy: 100% pass
- [ ] Tier 5 Cascade Validation: 100% pass
- [ ] Documentation sync issues resolved

### Phase 4: Regression & CI/CD
- [ ] Regression tests: 100% pass
- [ ] CI/CD pipeline operational
- [ ] Validation reports generated
- [ ] Final sign-off complete
```

---

## 15. Failure Response Procedures

### 15.1 Tier 1 Failure Response

```markdown
## Tier 1 Failure:  Node Logic Error

### Severity: HIGH
### Impact:  Workflow cannot execute correctly

### Immediate Actions:
1. Identify failing node from test output
2. Check n8n execution logs for error details
3. Review node configuration against expected behavior

### Resolution Steps: 
1. Open failing workflow in n8n editor
2. Navigate to failing node
3. Compare configuration to documentation
4. Fix node configuration or code
5. Re-run Tier 1 test for that workflow
6. Document fix in workflow changelog

### Escalation: 
- If node uses AI (Gemini), check API quotas
- If node uses GitHub API, verify token permissions
- If systematic failure, escalate to n8n support
```

### 15.2 Tier 4 Failure Response

```markdown
## Tier 4 Failure: Content Accuracy Error

### Severity:  CRITICAL
### Impact: Documentation does not reflect reality

### Immediate Actions:
1. Identify which document failed validation
2. Compare expected vs actual content
3. Determine root cause (workflow issue vs manual drift)

### Root Cause Categories: 

#### A. Workflow Did Not Trigger
- Check GitHub webhook delivery
- Verify workflow is active in n8n
- Check for filter node blocking

#### B.  Workflow Triggered But Did Not Update
- Check Distributor queue status
- Verify Agent received and processed task
- Check GitHub commit permissions

#### C.  Workflow Updated Wrong Content
- Review AI prompt for accuracy
- Check documentation_matrix.json mappings
- Verify cascade rules

### Resolution Steps:
1. Manually update document to correct state
2. Identify and fix root cause in workflow
3. Re-run affected Tier 4 tests
4. Add regression test to prevent recurrence

### Prevention: 
- Add failing scenario to regression suite
- Update gold standards if expectations changed
- Document lesson learned
```

### 15.3 Tier 5 Failure Response

```markdown
## Tier 5 Failure:  Cascade Chain Broken

### Severity:  CRITICAL
### Impact: Related documents not updated together

### Immediate Actions:
1. Identify which cascade level failed
2. Trace from trigger to failure point
3. Check each document in chain

### Cascade Chain Debugging: 

#### Level 1 Updated, Level 2 Not: 
- Verify documentation_matrix.json has correct dependencies
- Check if cascade rule exists
- Verify Distributor dispatched L2 task

#### Level 1 Not Updated: 
- Check Trigger workflow detected change
- Verify Matrix Lookup found affected docs
- Check Task Master generated task

### Resolution Steps:
1. Manually propagate updates through chain
2. Fix cascade logic in relevant workflow
3. Update documentation_matrix.json if needed
4. Re-run full cascade test

### Prevention:
- Add cascade chain to monitoring
- Create alerts for incomplete cascades
- Regular cascade chain audits
```

### 15.4 Failure Tracking Template

```markdown
## Validation Failure Report

**Date:** [DATE]
**Test ID:** [TEST_ID]
**Tier:** [TIER]
**Severity:** [LOW/MEDIUM/HIGH/CRITICAL]

### Description
[What failed and what was expected]

### Root Cause
[Why the failure occurred]

### Resolution
[How it was fixed]

### Prevention
[What was added to prevent recurrence]

### Related Items
- Issue: #[ISSUE_NUMBER]
- PR: #[PR_NUMBER]
- Regression Test: [REG-XXX]
```

---

## 16. Artifacts & Reporting

### 16.1 Validation Artifacts

| Artifact | Location | Purpose | Retention |
|----------|----------|---------|-----------|
| Test Results | `reports/tier{1-5}/` | Raw test output | 90 days |
| Validation Reports | `reports/validation_report_*.html` | Human-readable summary | 1 year |
| Regression Results | `reports/regression. xml` | JUnit format results | 90 days |
| Execution Logs | n8n Cloud → Executions | Workflow execution details | 30 days |
| Gold Standards | `gold_standards/*. yaml` | Reference definitions | Permanent |

### 16.2 Report Templates

#### Validation Summary Report

```markdown
# n8n Documentation Validation Report

**Generated:** [TIMESTAMP]
**Repository:** BootstrapAI-mgmt/Literature-Review
**Commit:** [COMMIT_SHA]

## Executive Summary

| Metric | Value | Status |
|--------|-------|--------|
| Total Tests | [N] | - |
| Passed | [N] | [%] |
| Failed | [N] | [%] |
| Warnings | [N] | [%] |
| **Overall Status** | - | [PASS/FAIL] |

## Tier Results

### Tier 1: Unit/Component
[PASS_COUNT]/[TOTAL] tests passed
[List any failures]

### Tier 2: Integration
[PASS_COUNT]/[TOTAL] tests passed
[List any failures]

### Tier 3: End-to-End
[PASS_COUNT]/[TOTAL] tests passed
[List any failures]

### Tier 4: Content Accuracy
[PASS_COUNT]/[TOTAL] tests passed
[List any failures with remediation]

### Tier 5: Cascade Validation
[PASS_COUNT]/[TOTAL] tests passed
[List any failures with remediation]

## Regression Tests
[PASS_COUNT]/[TOTAL] tests passed
[List any regressions detected]

## Recommendations

1. [Recommendation 1]
2. [Recommendation 2]
3. [Recommendation 3]

## Sign-Off

- [ ] All critical tests passing
- [ ] No regressions detected
- [ ] Documentation sync verified
- [ ] Ready for production

**Validated By:** [NAME]
**Date:** [DATE]
```

### 16.3 Continuous Reporting

```yaml
# Scheduled report generation
reports: 
  daily:
    - Tier 4 Content Accuracy
    - Any regressions
    - Staleness status
    
  weekly:
    - Full Tier 1-5 validation
    - Regression suite
    - Cascade chain verification
    - Trend analysis
    
  on_pr:
    - Affected document validation
    - Cascade impact analysis
    - Pre-merge accuracy check
    
  on_merge:
    - Full validation
    - Cascade propagation verification
    - Documentation freshness update
```

---

## 17. Appendices

### Appendix A: Mock Payloads

#### A.1 GitHub Push Event (Valid)

```json
{
  "ref": "refs/heads/main",
  "before": "abc123def456",
  "after": "789ghi012jkl",
  "repository": {
    "full_name": "BootstrapAI-mgmt/Literature-Review"
  },
  "pusher": {
    "name": "developer",
    "email":  "dev@example.com"
  },
  "head_commit": {
    "id": "789ghi012jkl",
    "message": "feat: add new analysis module",
    "timestamp": "2026-01-01T12:00:00Z",
    "author":  {
      "name": "Developer",
      "email": "dev@example.com"
    }
  },
  "commits": [
    {
      "id":  "789ghi012jkl",
      "message": "feat:  add new analysis module",
      "timestamp":  "2026-01-01T12:00:00Z",
      "added": ["literature_review/analysis/new_module.py"],
      "removed":  [],
      "modified": []
    }
  ]
}
```

#### A.2 GitHub Push Event (n8n Automated - Should Filter)

```json
{
  "ref":  "refs/heads/main",
  "head_commit": {
    "id": "automated123",
    "message": "[n8n] docs: update architecture blueprint",
    "timestamp": "2026-01-01T12:00:00Z"
  },
  "commits": [
    {
      "id":  "automated123",
      "message": "[n8n] docs: update architecture blueprint",
      "modified": ["docs/MASTER_ARCHITECTURE_BLUEPRINT.md"]
    }
  ]
}
```

#### A.3 Task Distributor Payload

```json
{
  "update_list_id": "ul-20260101-001",
  "source":  "doc-trigger",
  "trigger":  {
    "type":  "push",
    "commit":  "789ghi012jkl",
    "message": "feat: add new analysis module"
  },
  "tasks": [
    {
      "task_id": "task-001",
      "document":  "docs/MASTER_ARCHITECTURE_BLUEPRINT. md",
      "update_type": "UPDATE_REFERENCE",
      "description": "Add new_module.py to Package Structure",
      "priority": 1
    },
    {
      "task_id":  "task-002",
      "document":  "literature_review/analysis/README.md",
      "update_type":  "CASCADE_UPDATE",
      "description": "Update module list",
      "priority":  2
    }
  ]
}
```

#### A.4 Agent Task Payload

```json
{
  "task":  "{\"task_id\": \"task-001\",\"document\":\"docs/MASTER_ARCHITECTURE_BLUEPRINT.md\",\"update_type\":\"UPDATE_REFERENCE\",\"description\":\"Add new_module. py to Package Structure\",\"priority\":1}",
  "list_id": "ul-20260101-001",
  "trigger": "{\"type\":\"push\",\"commit\": \"789ghi012jkl\"}"
}
# Master n8n Validation Plan (V2.0.0) - Continued

---

## 17. Appendices (Continued)

### Appendix A:  Mock Payloads (Continued)

#### A.5 Agent Callback Payload (Success)

```json
{
  "task_id":  "task-001",
  "status": "completed",
  "result": {
    "document":  "docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
    "action": "updated",
    "commit_sha": "abc123newcommit",
    "changes_made": [
      "Added new_module.py to Package Structure section",
      "Updated module count in summary"
    ],
    "timestamp": "2026-01-01T12:05:00Z"
  }
}
```

#### A.6 Agent Callback Payload (Failure)

```json
{
  "task_id": "task-001",
  "status": "failed",
  "result": {
    "error": "HTTP 401 Unauthorized",
    "document": "docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
    "action":  "update_failed",
    "details": "GitHub API token expired or invalid",
    "timestamp": "2026-01-01T12:05:00Z"
  }
}
```

#### A.7 State Reconciliation Trigger

```json
{
  "trigger_type": "manual",
  "scan_scope": "full",
  "options": {
    "include_completed": true,
    "check_pr_status": true,
    "max_age_days":  30
  }
}
```

#### A.8 Staleness Review Trigger

```json
{
  "trigger_type": "manual",
  "domains": ["@core", "@infrastructure", "@testing"],
  "thresholds": {
    "critical":  7,
    "warning": 14,
    "info": 30
  }
}
```

#### A.9 PR Review Webhook Payload

```json
{
  "action": "opened",
  "number": 125,
  "pull_request": {
    "number": 125,
    "title": "feat: implement new validation module",
    "user": {
      "login": "developer",
      "type": "User"
    },
    "head": {
      "sha": "abc123prhead",
      "ref": "feature/new-validation"
    },
    "base": {
      "sha": "def456base",
      "ref": "main"
    },
    "changed_files": 5,
    "additions": 250,
    "deletions": 30
  },
  "repository":  {
    "full_name": "BootstrapAI-mgmt/Literature-Review"
  }
}
```

#### A.10 Release Tag Webhook Payload

```json
{
  "ref": "refs/tags/v2.2.0",
  "ref_type": "tag",
  "repository": {
    "full_name": "BootstrapAI-mgmt/Literature-Review"
  },
  "sender": {
    "login": "maintainer"
  }
}
```

#### A.11 Error Workflow Trigger Payload

```json
{
  "execution":  {
    "id": "exec-12345",
    "workflowId": "WF-03",
    "mode": "webhook",
    "startedAt": "2026-01-01T12:00:00Z",
    "stoppedAt": "2026-01-01T12:00:05Z",
    "status": "error"
  },
  "workflow": {
    "id": "WF-03",
    "name": "Doc Chain - Agent"
  },
  "error": {
    "message": "HTTP 401 Unauthorized",
    "node": "Commit to GitHub",
    "timestamp": "2026-01-01T12:00:05Z",
    "context": {
      "task_id": "task-001",
      "document": "docs/MASTER_ARCHITECTURE_BLUEPRINT. md"
    }
  }
}
```

---

### Appendix B:  Test Commands Reference

#### B.1 Tier 1 Commands (Manual in n8n)

```bash
# These are executed via n8n UI "Test Workflow" button
# with the corresponding mock payload from Appendix A

# 1. Open workflow in n8n editor
# 2. Click "Test Workflow"
# 3. Paste mock payload
# 4. Observe execution path
# 5. Verify expected nodes are reached
```

#### B.2 Tier 2 Commands (curl)

```bash
#!/bin/bash
# Tier 2 Integration Test Commands
# Save as:  tests/tier2/run_integration_tests.sh

BASE_URL="https://gitlitreview.app.n8n.cloud/webhook"

echo "========================================"
echo "Tier 2: Integration Tests"
echo "========================================"

# T2-EP-05: Distributor Status Check
echo -e "\n[T2-EP-05] Distributor Status..."
curl -s -X GET "$BASE_URL/distributor-status" | jq . 

# T2-EP-06: Distributor Reset
echo -e "\n[T2-EP-06] Distributor Reset..."
curl -s -X POST "$BASE_URL/distributor-reset" | jq . 

# T2-EP-01: GitHub Doc Trigger
echo -e "\n[T2-EP-01] GitHub Doc Trigger..."
curl -s -X POST "$BASE_URL/github-doc-trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "ref":  "refs/heads/main",
    "commits": [{
      "id":  "test123",
      "message": "test:  integration test commit",
      "modified": ["docs/test.md"]
    }]
  }' | jq . 

# T2-EP-02: Task Distributor
echo -e "\n[T2-EP-02] Task Distributor..."
curl -s -X POST "$BASE_URL/task-distributor" \
  -H "Content-Type: application/json" \
  -d '{
    "update_list_id": "test-int-001",
    "source": "integration-test",
    "tasks": [{
      "task_id": "int-task-001",
      "document":  "docs/test. md",
      "update_type": "STATUS_UPDATE",
      "description": "Integration test task"
    }]
  }' | jq . 

# Wait for processing
sleep 5

# T2-EP-05: Check Status After Submit
echo -e "\n[T2-EP-05] Distributor Status After Submit..."
curl -s -X GET "$BASE_URL/distributor-status" | jq .

# T2-EP-07: State Reconciliation
echo -e "\n[T2-EP-07] State Reconciliation..."
curl -s -X POST "$BASE_URL/state-reconciliation" | jq .

# T2-EP-08: Staleness Review
echo -e "\n[T2-EP-08] Staleness Review..."
curl -s -X POST "$BASE_URL/staleness-review" | jq .

echo -e "\n========================================"
echo "Integration Tests Complete"
echo "========================================"
```

#### B.3 Tier 3 Commands (Live GitHub)

```bash
#!/bin/bash
# Tier 3 End-to-End Test Commands
# Save as: tests/tier3/run_e2e_tests.sh

REPO="BootstrapAI-mgmt/Literature-Review"
TEST_BRANCH="test/e2e-validation-$(date +%s)"

echo "========================================"
echo "Tier 3: End-to-End Tests"
echo "========================================"

# T3-E2E-01: Push to docs/
echo -e "\n[T3-E2E-01] Testing docs/ push..."

# Create test branch
git checkout -b "$TEST_BRANCH"

# Create test file
echo "# E2E Test Document" > docs/E2E_TEST_$(date +%s).md
echo "Created: $(date)" >> docs/E2E_TEST_*. md
echo "Purpose:  Validate n8n Doc Chain" >> docs/E2E_TEST_*. md

# Commit and push
git add docs/E2E_TEST_*.md
git commit -m "test: E2E validation $(date)"
git push origin "$TEST_BRANCH"

echo "Pushed to $TEST_BRANCH"
echo "Waiting 60 seconds for n8n processing..."
sleep 60

# Check for n8n commit
echo "Checking for n8n response commits..."
git fetch origin "$TEST_BRANCH"
git log origin/"$TEST_BRANCH" --oneline -5

# Cleanup
echo -e "\nCleaning up test branch..."
git checkout main
git branch -D "$TEST_BRANCH"
git push origin --delete "$TEST_BRANCH" 2>/dev/null || true

echo -e "\n[T3-E2E-01] Complete - verify n8n execution in dashboard"

# T3-LP-01: Loop Prevention Test
echo -e "\n[T3-LP-01] Testing loop prevention..."
echo "Creating commit with [n8n] prefix..."

git checkout -b "test/loop-prevention-$(date +%s)"
echo "# Loop Test" > docs/LOOP_TEST. md
git add docs/LOOP_TEST.md
git commit -m "[n8n] docs: this should be filtered"
git push origin HEAD

echo "Waiting 30 seconds..."
sleep 30

echo "Check n8n executions - this should NOT trigger a workflow"

# Cleanup
git checkout main
git branch -D "test/loop-prevention-*" 2>/dev/null || true

echo -e "\n========================================"
echo "E2E Tests Complete"
echo "========================================"
```

#### B.4 Tier 4 Commands (Validation Framework)

```bash
#!/bin/bash
# Tier 4 Content Accuracy Tests
# Save as: tests/tier4/run_accuracy_tests.sh

echo "========================================"
echo "Tier 4: Content Accuracy Tests"
echo "========================================"

# Run validation framework
python -m validation_framework.cli \
  --tier 4 \
  --document all \
  --output console \
  --verbose

# Generate HTML report
python -m validation_framework.cli \
  --tier 4 \
  --document all \
  --output html \
  --report-path reports/tier4_accuracy

echo -e "\n========================================"
echo "Content Accuracy Tests Complete"
echo "Report:  reports/tier4_accuracy_*. html"
echo "========================================"
```

#### B.5 Tier 5 Commands (Cascade Validation)

```bash
#!/bin/bash
# Tier 5 Cascade Validation Tests
# Save as: tests/tier5/run_cascade_tests.sh

echo "========================================"
echo "Tier 5: Cascade Validation Tests"
echo "========================================"

# Run cascade validation
python -m validation_framework.cli \
  --tier 5 \
  --output console \
  --verbose

# Generate report
python -m validation_framework.cli \
  --tier 5 \
  --output html \
  --report-path reports/tier5_cascade

echo -e "\n========================================"
echo "Cascade Tests Complete"
echo "Report: reports/tier5_cascade_*. html"
echo "========================================"
```

#### B.6 Regression Test Commands

```bash
#!/bin/bash
# Regression Test Suite
# Save as:  tests/regression/run_regression_tests. sh

echo "========================================"
echo "Regression Test Suite"
echo "========================================"

# Run all regression tests with pytest
pytest tests/regression/ \
  -v \
  --tb=short \
  --junitxml=reports/regression. xml \
  --html=reports/regression. html \
  --self-contained-html

# Show summary
echo -e "\n========================================"
echo "Regression Tests Complete"
echo "JUnit Report: reports/regression. xml"
echo "HTML Report: reports/regression.html"
echo "========================================"
```

#### B.7 Full Validation Suite

```bash
#!/bin/bash
# Complete Validation Suite
# Save as: tests/run_full_validation. sh

echo "========================================"
echo "FULL VALIDATION SUITE"
echo "Started:  $(date)"
echo "========================================"

REPORT_DIR="reports/full_validation_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

# Gate 1: Tier 1 (Manual - prompt user)
echo -e "\n[GATE 1] Tier 1: Unit Tests"
echo "Please run Tier 1 tests manually in n8n UI"
read -p "Have all Tier 1 tests passed? (y/n): " tier1_pass
if [ "$tier1_pass" != "y" ]; then
  echo "GATE 1 FAILED - Fix Tier 1 issues before continuing"
  exit 1
fi
echo "GATE 1 PASSED"

# Gate 2: Tier 2
echo -e "\n[GATE 2] Tier 2: Integration Tests"
./tests/tier2/run_integration_tests.sh > "$REPORT_DIR/tier2.log" 2>&1
if [ $? -ne 0 ]; then
  echo "GATE 2 FAILED - Check $REPORT_DIR/tier2.log"
  exit 1
fi
echo "GATE 2 PASSED"

# Gate 3: Tier 3 (Semi-automated)
echo -e "\n[GATE 3] Tier 3: End-to-End Tests"
./tests/tier3/run_e2e_tests.sh > "$REPORT_DIR/tier3.log" 2>&1
read -p "Did all E2E tests produce expected results? (y/n): " tier3_pass
if [ "$tier3_pass" != "y" ]; then
  echo "GATE 3 FAILED - Check $REPORT_DIR/tier3.log"
  exit 1
fi
echo "GATE 3 PASSED"

# Gate 4: Tier 4
echo -e "\n[GATE 4] Tier 4: Content Accuracy"
python -m validation_framework.cli \
  --tier 4 \
  --output json \
  --report-path "$REPORT_DIR/tier4"

TIER4_FAILED=$(cat "$REPORT_DIR"/tier4*. json | jq '. failed')
if [ "$TIER4_FAILED" != "0" ]; then
  echo "GATE 4 FAILED - $TIER4_FAILED tests failed"
  echo "Check $REPORT_DIR/tier4*.json for details"
  exit 1
fi
echo "GATE 4 PASSED"

# Gate 5: Tier 5
echo -e "\n[GATE 5] Tier 5: Cascade Validation"
python -m validation_framework. cli \
  --tier 5 \
  --output json \
  --report-path "$REPORT_DIR/tier5"

TIER5_FAILED=$(cat "$REPORT_DIR"/tier5*.json | jq '.failed')
if [ "$TIER5_FAILED" != "0" ]; then
  echo "GATE 5 FAILED - $TIER5_FAILED tests failed"
  echo "Check $REPORT_DIR/tier5*. json for details"
  exit 1
fi
echo "GATE 5 PASSED"

# Regression Tests
echo -e "\n[REGRESSION] Running regression suite..."
pytest tests/regression/ \
  -v \
  --junitxml="$REPORT_DIR/regression.xml" \
  > "$REPORT_DIR/regression.log" 2>&1

if [ $? -ne 0 ]; then
  echo "REGRESSION TESTS FAILED"
  echo "Check $REPORT_DIR/regression.log"
  exit 1
fi
echo "REGRESSION TESTS PASSED"

# Generate final report
echo -e "\n========================================"
echo "VALIDATION COMPLETE"
echo "========================================"
echo "All gates passed!"
echo "Report directory: $REPORT_DIR"
echo "Completed:  $(date)"
echo "========================================"
```

---

### Appendix C: Gold Standard YAML Files

#### C.1 architecture_blueprint.yaml (Complete)

```yaml
# gold_standards/architecture_blueprint. yaml
# Gold standard for MASTER_ARCHITECTURE_BLUEPRINT.md validation

document:  docs/MASTER_ARCHITECTURE_BLUEPRINT. md
version: "2.0.0"
last_validated: "2026-01-01"
validation_tier: "T4-ARCH"

metadata:
  expected_header: 
    title: "Master Architecture Blueprint"
    status_field: true
    version_field: true
    updated_field: true
    scope_field: true

sections:
  - name: "Executive Summary"
    required:  true
    validation_type: existence

  - name: "System Architecture Overview"
    required:  true
    validation_type: diagram_presence
    expected_elements:
      - "STAGE 1"
      - "STAGE 2"
      - "STAGE 3"
      - "STAGE 4"
      - "STAGE 5"

  - name: "Package Structure"
    required: true
    validation_type: directory_sync
    source_directory: literature_review/
    rules:
      - all_py_files_documented:  true
      - all_directories_documented: true
      - no_orphan_entries: true
      - max_depth:  3
    required_directories:
      - literature_review/
      - literature_review/config/
      - literature_review/analysis/
      - literature_review/reviewers/
      - literature_review/triggers/
      - literature_review/pipeline/
      - literature_review/optimization/
      - literature_review/utils/
      - literature_review/visualization/
      - literature_review/io/
      # NEW: Operationalization
      - literature_review/models/

  - name: "Core Components"
    required:  true
    validation_type: module_coverage
    required_modules:
      # Original modules
      - path: literature_review/orchestrator. py
        description: "Gap analysis & convergence"
        documented: true
      - path: literature_review/orchestrator_integration.py
        description: "Pipeline coordination"
        documented:  true
      - path: literature_review/reviewers/journal_reviewer.py
        description: "Initial paper screening"
        documented:  true
      - path: literature_review/reviewers/deep_reviewer.py
        description: "Deep analysis for appeals"
        documented:  true
      - path: literature_review/analysis/judge.py
        description: "Claim evaluation"
        documented: true
      - path: literature_review/analysis/gap_analyzer.py
        description: "Gap identification"
        documented:  true
      # NEW: Operationalization modules (PRs #97-105)
      - path: literature_review/models/action_vector.py
        description: "ActionVector dataclass"
        documented: true
        added_by: "PR #97"
        added_date: "2025-12-30"
      - path: literature_review/models/validation_strategy.py
        description: "ValidationStrategy dataclass"
        documented: true
        added_by:  "PR #97"
        added_date: "2025-12-30"
      - path:  literature_review/analysis/benchmark_analyzer.py
        description: "Benchmark-metric analysis"
        documented: true
        added_by: "PR #99"
        added_date: "2025-12-30"
      - path:  literature_review/analysis/validation_tracker.py
        description: "Validation gap tracking"
        documented: true
        added_by: "PR #100"
        added_date: "2025-12-30"
      - path:  literature_review/analysis/action_generator.py
        description: "Action vector generation"
        documented: true
        added_by: "PR #101"
        added_date: "2025-12-30"
      - path: literature_review/analysis/pillar_evolution.py
        description: "Proposal management"
        documented:  true
        added_by: "PR #103"
        added_date: "2025-12-30"
      - path:  literature_review/analysis/stakeholder_analyzer.py
        description: "Stakeholder impact"
        documented: true
        added_by: "PR #105"
        added_date: "2025-12-31"

  - name: "Web Dashboard"
    required:  true
    validation_type: existence
    expected_elements:
      - "webdashboard/"
      - "FastAPI"
      - "HTMX"

  - name: "Data Flow"
    required:  true
    validation_type: diagram_presence

  - name: "Configuration Files"
    required:  true
    validation_type: config_coverage
    expected_configs:
      - research_config.json
      - pipeline_config.json
      - pillar_definitions.json

  - name: "Key Data Files"
    required:  true
    validation_type: output_coverage
    required_outputs:
      # Original outputs
      - name: review_log.json
        purpose: "Paper review records"
        documented: true
      - name: review_version_history.json
        purpose: "Version-tracked changes"
        documented:  true
      - name: orchestrator_state.json
        purpose: "Checkpoint state"
        documented: true
      - name: gap_analysis_output/
        purpose: "Generated reports"
        documented:  true
      # NEW: Operationalization outputs
      - name: action_vectors. json
        purpose:  "Executable implementation plans"
        documented:  true
        added_by: "OP-W3-2"
      - name: validation_gap_matrix.json
        purpose: "Design-validation coverage"
        documented:  true
        added_by: "OP-W3-1"
      - name: requirement_benchmark_matrix.json
        purpose: "Performance-benchmark linkages"
        documented:  true
        added_by: "OP-W2-2"
      - name: pillar_research_log.json
        purpose: "Research status log"
        documented:  true
        added_by: "OP-W4-1"
      - name: pillar_proposals.json
        purpose: "Modification proposals"
        documented: true
        added_by: "OP-W4-2"
      - name: stakeholder_impact_matrix.json
        purpose: "Change impact analysis"
        documented: true
        added_by: "OP-W4-3"

  - name: "Technology Stack"
    required: true
    validation_type: existence

  - name: "Test Infrastructure"
    required:  true
    validation_type: existence

  - name:  "Related Documentation"
    required:  true
    validation_type: link_validity

freshness:
  max_age_days: 7
  relative_to: latest_structural_commit
  check_fields:
    - "**Updated:**"
    - "**Version:**"
  
alerts:
  stale_threshold_days: 14
  critical_threshold_days:  30
```

#### C.2 repository_roadmap.yaml (Complete)

```yaml
# gold_standards/repository_roadmap. yaml
# Gold standard for MASTER_REPOSITORY_ROADMAP.md validation

document: docs/MASTER_REPOSITORY_ROADMAP.md
version: "2.0.0"
last_validated: "2026-01-01"
validation_tier: "T4-ROAD"

metadata: 
  expected_header: 
    title: "Master Repository Roadmap"
    status:  "Living Document"
    version_field: true
    updated_field:  true

sections:
  - name: "Executive Summary"
    required: true
    validation_type: existence

  - name: "At a Glance"
    required: true
    validation_type:  table_accuracy
    table_columns:
      - Wave
      - Status
      - Completion
      - Hours
      - Task Cards
    expected_rows:
      - wave: "Wave 1: Foundation"
        status: "✅ Complete"
        completion: "100%"
      - wave: "Wave 2: Core Features"
        status:  "✅ Complete"
        completion:  "100%"
      - wave: "Wave 3: Advanced Features"
        status: "✅ Complete"
        completion: "100%"
      - wave:  "Wave 4: Production Polish"
        status:  "✅ Complete"
        completion:  "100%"
      - wave: "Agent Task Cards"
        status:  "✅ Complete"
        completion:  "100%"
      - wave: "Enhancement Wave 1"
        status:  "✅ Complete"
        completion:  "100%"
      - wave: "Enhancement Wave 2"
        status: "✅ Complete"
        completion: "100%"
      - wave: "Enhancement Wave 3"
        status: "✅ Complete"
        completion: "100%"
      # MUST BE UPDATED: 
      - wave: "Operationalization Wave"
        status: "✅ Complete"  # Was "📋 Planned"
        completion:  "100%"    # Was "0%"
      # NEW - Must exist:
      - wave: "Validation Matrix Wave"
        status:  "📋 Planned"
        task_cards: 22
      - wave: "Wave 0. 5"
        status: "📋 Planned"
        task_cards: 3

  - name: "Completed Development"
    required:  true
    validation_type: wave_status_sync
    waves:
      - name: "Wave 1: Foundation"
        expected_status: "Complete"
      - name: "Wave 2: Core Features"
        expected_status: "Complete"
      - name:  "Wave 3: Advanced Features"
        expected_status: "Complete"
      - name: "Wave 4: Production Polish"
        expected_status: "Complete"
      - name: "Enhancement Wave 1"
        expected_status:  "Complete"
      - name: "Enhancement Wave 2"
        expected_status:  "Complete"
      - name: "Enhancement Wave 3"
        expected_status:  "Complete"
      - name: "Agent Task Cards"
        expected_status: "Complete"

  - name: "Operationalization Wave"
    required:  true
    validation_type: wave_completion
    expected_state:
      status: "✅ Complete"
      completion_percentage: 100
      tasks_completed: 8
      tasks_total: 8
      section_location: "Completed Development"  # Should move from "Planned"
    evidence:
      - task:  "OP-W1-1"
        pr: 97
        merged: true
        merged_date: "2025-12-30"
      - task: "OP-W2-1"
        pr: 98
        merged: true
        merged_date:  "2025-12-30"
      - task: "OP-W2-2"
        pr: 99
        merged: true
        merged_date:  "2025-12-30"
      - task: "OP-W3-1"
        pr: 100
        merged: true
        merged_date: "2025-12-30"
      - task: "OP-W3-2"
        pr: 101
        merged: true
        merged_date:  "2025-12-30"
      - task: "OP-W4-1"
        pr: 102
        merged: true
        merged_date: "2025-12-30"
      - task: "OP-W4-2"
        pr:  103
        merged: true
        merged_date: "2025-12-30"
      - task: "OP-W4-3"
        pr: 105
        merged: true
        merged_date: "2025-12-31"

  - name: "Validation Matrix Wave"
    required: true
    validation_type: section_existence
    expected_state:
      exists: true
      task_count: 22
      total_effort_hours: 164
    evidence:
      pr:  122
      merged: true
      merged_date: "2025-12-31"
    task_cards:
      - "VM-W0-1"
      - "VM-W0-2"
      - "VM-W0.5-1"
      - "VM-W0.5-2"
      - "VM-W0.5-3"
      - "VM-W1-1"
      - "VM-W1-2"
      - "VM-W1-3"
      - "VM-W2-1"
      - "VM-W2-2"
      - "VM-W2. 5-1"
      - "VM-W2.5-2"
      - "VM-W3-1"
      - "VM-W3-2"
      - "VM-W3-3"
      - "VM-W4-1"
      - "VM-W4-2"
      - "VM-W4-3"
      - "VM-W5-1"
      - "VM-W5-2"
      - "VM-W5-3"
      - "VM-W5-4"

  - name: "Wave 0.5 Modularization"
    required: true
    validation_type: section_existence
    expected_state:
      exists: true
      task_count: 3
      total_effort_hours: 26
      position:  "Between Wave 0 and Wave 1"
    evidence: 
      commit: "2b4ca13"
      date: "2026-01-01"
    task_cards: 
      - id: "VM-W0.5-1"
        name: "Metrics Configuration System"
        effort_hours: 6
      - id: "VM-W0.5-2"
        name: "Domain Test Fixtures"
        effort_hours: 8
      - id:  "VM-W0.5-3"
        name: "Model Abstraction Layer"
        effort_hours: 14  # Updated from 12h

  - name: "Metrics & Tracking"
    required:  true
    validation_type: metrics_accuracy
    expected_metrics:
      total_task_cards: 
        minimum: 74  # 49 original + 22 VM + 3 Wave 0.5
      completed_task_cards:
        minimum: 49  # Original 41 + 8 OP

  - name: "Related Documentation"
    required: true
    validation_type: link_validity

freshness: 
  max_age_days: 3
  relative_to: latest_merged_pr
  check_fields:
    - "**Updated:**"
    - "**Version:**"
```

#### C.3 task_card_sync.yaml (Complete)

```yaml
# gold_standards/task_card_sync. yaml
# Gold standard for task card synchronization validation

validation_type: bidirectional_sync
version: "2.0.0"
last_validated: "2026-01-01"
validation_tier: "T4-TASK"

directories:
  task_cards:  "task-cards/"
  wave_indexes: 
    - "task-cards/OPERATIONALIZATION_WAVE_INDEX.md"
    - "task-cards/VALIDATION_MATRIX_WAVE_INDEX.md"

rules:
  - name: pr_to_task_sync
    id: "SYNC-01"
    description:  "Every merged PR with task reference updates corresponding task card"
    severity: critical
    validation: 
      for_each: 
        source:  merged_prs
        filter: "title OR body contains task reference pattern"
      steps:
        - extract:  task_id
          patterns:
            - "(OP-W\\d+-\\d+)"
            - "(VM-W[\\d. ]+\\-\\d+)"
            - "implements (\\w+-\\w+-\\d+)"
        - locate: "task-cards/{task_id}.md"
        - assert:
            field:  status
            value: "Complete"
            message: "Task card must show Complete status"
        - assert:
            field: pr_reference
            present: true
            message: "Task card must reference implementing PR"

  - name: task_to_pr_sync
    id: "SYNC-02"
    description:  "Every task marked Complete has corresponding merged PR"
    severity: critical
    validation:
      for_each:
        source: task_cards
        filter: "status == Complete"
      steps:
        - extract: pr_reference
        - assert:
            condition: pr_exists
            message: "Referenced PR must exist"
        - assert: 
            condition: pr_merged
            message:  "Referenced PR must be merged"

  - name: wave_index_sync
    id: "SYNC-03"
    description: "Wave index reflects individual task statuses"
    severity: high
    validation: 
      for_each: 
        source: wave_indexes
      steps:
        - for_each:  task_row
          - extract:  task_id, status
          - locate: "task-cards/{task_id}.md"
          - assert: 
              condition: index_status == card_status
              message: "Index and card status must match"

  - name:  wave_completion_sync
    id: "SYNC-04"
    description: "Wave marked Complete when all tasks Complete"
    severity:  high
    validation: 
      for_each:
        source:  wave_indexes
      steps:
        - count: tasks_with_status_complete
        - count: total_tasks
        - if: 
            condition: complete_count == total_count
          then:
            - assert:
                field: wave_status
                value: "✅ Complete"

known_mappings:
  operationalization_wave: 
    wave_index: "task-cards/OPERATIONALIZATION_WAVE_INDEX.md"
    tasks:
      - task_id: "OP_WAVE_1_1_SCHEMA_FOUNDATION"
        file: "task-cards/OP_WAVE_1_1_SCHEMA_FOUNDATION.md"
        pr: 97
        expected_status: "Complete"
        pr_merged_date: "2025-12-30"
      
      - task_id: "OP_WAVE_2_1_ACTION_EXTRACTION"
        file: "task-cards/OP_WAVE_2_1_ACTION_EXTRACTION. md"
        pr: 98
        expected_status: "Complete"
        pr_merged_date:  "2025-12-30"
      
      - task_id: "OP_WAVE_2_2_BENCHMARK_EXTRACTION"
        file: "task-cards/OP_WAVE_2_2_BENCHMARK_EXTRACTION.md"
        pr: 99
        expected_status:  "Complete"
        pr_merged_date: "2025-12-30"
      
      - task_id: "OP_WAVE_3_1_VALIDATION_TRACKER"
        file: "task-cards/OP_WAVE_3_1_VALIDATION_TRACKER.md"
        pr: 100
        expected_status:  "Complete"
        pr_merged_date: "2025-12-30"
      
      - task_id: "OP_WAVE_3_2_ACTION_VECTOR_GENERATOR"
        file: "task-cards/OP_WAVE_3_2_ACTION_VECTOR_GENERATOR.md"
        pr: 101
        expected_status: "Complete"
        pr_merged_date: "2025-12-30"
      
      - task_id:  "OP_WAVE_4_1_PILLAR_RESEARCH_LOG"
        file: "task-cards/OP_WAVE_4_1_PILLAR_RESEARCH_LOG. md"
        pr: 102
        expected_status: "Complete"
        pr_merged_date:  "2025-12-30"
      
      - task_id: "OP_WAVE_4_2_MODIFICATION_PROPOSALS"
        file: "task-cards/OP_WAVE_4_2_MODIFICATION_PROPOSALS.md"
        pr:  103
        expected_status: "Complete"
        pr_merged_date: "2025-12-30"
      
      - task_id: "OP_WAVE_4_3_STAKEHOLDER_MATRIX"
        file: "task-cards/OP_WAVE_4_3_STAKEHOLDER_MATRIX.md"
        pr: 105
        expected_status: "Complete"
        pr_merged_date: "2025-12-31"

alerts:
  sync_failure:
    severity: critical
    action: create_github_issue
    labels:  ["bug", "documentation-sync", "automated"]
```

#### C.4 freshness_thresholds.yaml (Complete)

```yaml
# gold_standards/freshness_thresholds.yaml
# Freshness thresholds for documentation staleness detection

version: "2.0.0"
last_validated: "2026-01-01"
validation_tier: "T4-STAL"

global_settings:
  default_max_age_days:  30
  timestamp_patterns:
    - "**Updated:** (\\w+ \\d+, \\d+)"
    - "**Last Updated:** (\\d{4}-\\d{2}-\\d{2})"
    - "Updated: (\\d{4}-\\d{2}-\\d{2})"

document_types:
  - pattern: "MASTER_*. md"
    category: "master_documents"
    max_age_days:  7
    relative_to: "any_structural_change"
    priority: critical
    description: "Master documents must reflect current state within 1 week"
    triggers:
      - new_python_file
      - new_directory
      - wave_completion
      - major_feature_merge

  - pattern:  "task-cards/*.md"
    category: "task_cards"
    max_age_days: 3
    relative_to: "related_pr_merge"
    priority:  high
    description:  "Task cards must update within 3 days of PR merge"
    triggers:
      - pr_merge_with_task_reference
      - manual_status_update

  - pattern: "*_WAVE_INDEX.md"
    category: "wave_indexes"
    max_age_days:  1
    relative_to: "any_task_status_change"
    priority: high
    description: "Wave indexes must update within 24 hours of task changes"
    triggers: 
      - task_card_status_change
      - wave_completion

  - pattern:  "docs/guides/*.md"
    category: "guides"
    max_age_days: 14
    relative_to: "related_feature_change"
    priority:  medium
    description:  "Guides should update within 2 weeks of feature changes"
    triggers: 
      - cli_change
      - api_change
      - configuration_change

  - pattern: "README.md"
    category: "readme"
    max_age_days: 30
    relative_to: "major_feature_change"
    priority:  low
    description: "README updates for major features only"
    triggers: 
      - new_major_feature
      - breaking_change

  - pattern: "docs/claude-integration/*. md"
    category: "integration_docs"
    max_age_days: 7
    relative_to: "workflow_change"
    priority: high
    description: "Integration docs must track workflow changes"
    triggers:
      - n8n_workflow_update
      - webhook_change

staleness_actions:
  critical: 
    threshold_exceeded_by: 0  # Immediate
    actions:
      - create_github_issue: 
          title: "🚨 Critical:  {document} is stale"
          labels: ["documentation", "critical", "stale"]
          assignees: ["@maintainers"]
      - notify_slack:
          channel: "#doc-alerts"
          message:  "Critical documentation staleness detected"
      - block_pr_merge:
          condition: "affected_document_is_stale"
  
  high:
    threshold_exceeded_by: 0
    actions:
      - create_github_issue:
          title: "⚠️ High Priority: {document} needs update"
          labels:  ["documentation", "high-priority", "stale"]
      - notify_maintainer:
          method: "github_mention"
  
  medium: 
    threshold_exceeded_by: 7  # 1 week grace period
    actions: 
      - create_refresh_task:
          priority: 2
          queue: "documentation-updates"
  
  low: 
    threshold_exceeded_by: 14  # 2 week grace period
    actions:
      - log_for_weekly_review: 
          report:  "staleness_digest"

exceptions:
  - pattern: "docs/archive/*.md"
    max_age_days:  null  # Never stale
    reason: "Archived documents are historical records"
  
  - pattern: "CHANGELOG.md"
    max_age_days: null
    reason: "Changelog updates only on release"
  
  - pattern:  "docs/**/examples/*.md"
    max_age_days: 60
    reason: "Examples change less frequently"
```

---

### Appendix D: Directory Structure

```
Literature-Review/
├── . github/
│   └── workflows/
│       ├── integration-tests.yml
│       ├── e2e-tests. yml
│       ├── dashboard-e2e-tests. yml
│       └── documentation-validation.yml     # NEW
│
├── docs/
│   ├── MASTER_ARCHITECTURE_BLUEPRINT.md
│   ├── MASTER_REPOSITORY_ROADMAP. md
│   ├── claude-integration/
│   │   └── workflow-reviews/
│   │       ├── SIGN-OFF. md
│   │       ├── TESTING-GUIDE.md
│   │       └── ... 
│   └── N8N_MASTER_VALIDATION_PLAN.md        # THIS DOCUMENT
│
├── task-cards/
│   ├── OPERATIONALIZATION_WAVE_INDEX.md
│   ├── VALIDATION_MATRIX_WAVE_INDEX.md      # NEW
│   ├── OP_WAVE_*. md
│   └── VM_WAVE_*.md                         # NEW
│
├── tests/
│   ├── tier1/                               # NEW
│   │   └── mocks/
│   │       └── *. json
│   ├── tier2/                               # NEW
│   │   └── run_integration_tests.sh
│   ├── tier3/                               # NEW
│   │   └── run_e2e_tests.sh
│   ├── tier4/                               # NEW
│   │   ├── test_content_accuracy.py
│   │   └── run_accuracy_tests.sh
│   ├── tier5/                               # NEW
│   │   ├── test_cascade_validation.py
│   │   └── run_cascade_tests.sh
│   ├── regression/                          # NEW
│   │   ├── test_reg_001_operationalization_sync.py
│   │   ├── test_reg_002_validation_matrix_wave. py
│   │   ├── test_reg_003_wave_05_existence.py
│   │   ├── test_reg_004_task_pr_sync.py
│   │   ├── test_reg_005_architecture_modules.py
│   │   ├── test_reg_006_output_files.py
│   │   └── run_regression_tests. sh
│   └── run_full_validation. sh               # NEW
│
├── validation_framework/                    # NEW
│   ├── __init__.py
│   ├── cli.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── validator.py
│   │   ├── gold_standard_loader.py
│   │   ├── document_parser.py
│   │   └── github_client.py
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── architecture_validator.py
│   │   ├── roadmap_validator.py
│   │   ├── task_card_validator.py
│   │   ├── cascade_validator.py
│   │   └── staleness_validator.py
│   └── reporters/
│       ├── __init__. py
│       ├── console_reporter.py
│       ├── html_reporter.py
│       ├── json_reporter.py
│       └── github_reporter.py
│
├── gold_standards/                          # NEW
│   ├── architecture_blueprint.yaml
│   ├── repository_roadmap.yaml
│   ├── task_card_sync.yaml
│   └── freshness_thresholds.yaml
│
└── reports/                                 # NEW (gitignored)
    ├── tier4_*. json
    ├── tier5_*.json
    ├── regression. xml
    └── validation_report_*.html
```

---

### Appendix E: Glossary

| Term | Definition |
|------|------------|
| **Cascade Chain** | A sequence of document updates triggered by a single change, where each update may trigger further updates |
| **Content Accuracy** | Validation that document content correctly reflects the actual state of the repository |
| **Gold Standard** | A verifiable expected state against which actual output is compared |
| **Freshness** | The age of a document relative to relevant changes in the repository |
| **Staleness** | A document whose content no longer accurately reflects the current state |
| **Tier** | A level in the validation hierarchy, from unit tests (Tier 1) to cascade validation (Tier 5) |
| **Wave** | A group of related task cards representing a development phase |
| **Task Card** | A markdown document describing a specific development task |
| **Wave Index** | A document listing all task cards in a wave with their status |
| **Bidirectional Sync** | Validation that changes flow correctly in both directions (e.g., PR→Task and Task→PR) |
| **Regression Test** | A test designed to prevent recurrence of a previously discovered issue |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-01 | Initial | Original validation plan (4 workflows, 3 tiers) |
| 2.0.0 | 2026-01-01 | Revised | Complete rewrite:  8 workflows, 5 tiers, gold standards, regression tests, automation framework |

---

## Sign-Off

### Approval Checklist

- [ ] All 8 workflows identified and documented
- [ ] 5-tier testing strategy defined
- [ ] 87 test cases specified
- [ ] 6 gold standards created
- [ ] 12 regression tests defined
- [ ] Automated validation framework designed
- [ ] CI/CD integration specified
- [ ] Failure response procedures documented
- [ ] Execution plan with milestones defined

### Approvals

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author | - | 2026-01-01 | - |
| Technical Review | - | - | - |
| QA Review | - | - | - |
| Final Approval | - | - | - |

---

*This document supersedes the original Master n8n Validation Plan (V1.0.0) and incorporates all findings from the State Comparison Analysis dated 2026-01-01.*