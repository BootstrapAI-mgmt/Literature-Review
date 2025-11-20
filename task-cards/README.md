# Task Cards

This folder contains all implementation task cards organized by category and wave.

## 📁 Folder Structure

### `/agent/` - Core Agent Tasks (4 cards)
**Critical path tasks for agent functionality improvements**

**Files:**
- `AGENT_TASK_CARDS.md` - All 4 agent task cards:
  - Task #1: Fix DRA Prompting (2-3h) - 🟢 Ready
  - Task #2: Refactor Judge Version History (4-6h) - 🟢 Ready
  - Task #3: Document Chunking (6-8h) - 🟢 Ready
  - Task #4: Deep Coverage Database Decision (2-3h) - ✅ COMPLETE

**Wave:** Wave 1 (Foundation)  
**Status:** 1/4 Complete

---

### `/automation/` - Automation & Error Handling (4 cards)
**Reliability and operational improvements**

**Files:**
- `AUTOMATION_TASK_CARD_13.1.md` - Enhanced Retry Logic (6-8h) - 🟢 Ready
- `AUTOMATION_TASK_CARD_13.2.md` - File Locking & Concurrency (4-6h) - ✅ COMPLETE
- `AUTOMATION_TASK_CARD_14.md` - Improved Logging (4-6h) - 🟢 Ready
- `AUTOMATION_TASK_CARD_15.md` - Health Checks (3-4h) - 🟢 Ready

**Wave:** Wave 2  
**Status:** 1/4 Complete

---

### `/integration/` - Integration Tests (5 cards)
**Component-level integration test specifications**

**Files:**
- `INTEGRATION_TESTING_TASK_CARDS.md` - Original 8 integration test cards (master reference)
- `INTEGRATION_TASK_CARD_6.md` - INT-001: Journal→Judge Flow (8-10h) - 🟢 Ready
- `INTEGRATION_TASK_CARD_7.md` - INT-003: Version History→CSV Sync (5-7h) - 🟢 Ready
- `INTEGRATION_TASK_CARD_8.md` - INT-002: Judge DRA Appeal Flow (8-10h) - 🟢 Ready
- `INTEGRATION_TASK_CARD_9.md` - INT-004/005: Orchestrator Integration (8-10h) - 🟢 Ready

**Wave:** Wave 2-3  
**Status:** 0/5 Complete (enhanced scope with evidence quality features)  
**Dependencies:** Evidence enhancement cards #16-21

---

### `/e2e/` - End-to-End Tests (2 cards)
**Full pipeline validation tests**

**Files:**
- `INTEGRATION_TASK_CARD_10.md` - E2E-001: Full Pipeline Test (12-16h) - 🟢 Ready
- `INTEGRATION_TASK_CARD_11.md` - E2E-002: Convergence Loop Test (12-16h) - 🟢 Ready

**Wave:** Wave 4  
**Status:** 0/2 Complete  
**Dependencies:** All integration tests (#6-9), Evidence enhancement (#16-21)

---

### `/evidence-enhancement/` - Evidence Quality Features (8 cards)
**Advanced evidence quality assessment features**

**Files:**
- `EVIDENCE_ENHANCEMENT_TASK_CARDS.md` - Master reference for all 8 cards
- `TASK-16-Multi-Dimensional-Scoring.md` - Multi-dimensional evidence scoring (8-10h) - 🟢 Ready
- `TASK-17-Provenance-Tracking.md` - Evidence provenance tracking (6-8h) - 🟢 Ready
- `TASK-18-Inter-Rater-Reliability.md` - Consensus for borderline claims (6-8h) - 🟢 Ready
- `TASK-19-Temporal-Coherence.md` - Temporal analysis (4-6h) - 🟢 Ready
- `TASK-20-Evidence-Triangulation.md` - Multi-reviewer triangulation (6-8h) - 🟢 Ready
- `TASK-21-GRADE-Quality-Assessment.md` - GRADE quality levels (8-10h) - 🟢 Ready
- `TASK-22-Publication-Bias-Detection.md` - Publication bias detection (6-8h) - 🟡 Optional
- `TASK-23-Conflict-of-Interest-Analysis.md` - COI analysis (4-6h) - 🟡 Optional

**Wave:** Waves 2-4  
**Status:** 0/8 Complete  
**Priority:** Core features (#16-21) required for integration tests

---

### `/incremental-review/` - Incremental Review & CLI/Dashboard Parity (16 cards) ⭐ NEW
**Incremental review logic and dashboard/CLI feature parity improvements**

**Files:**
- **[README.md](incremental-review/README.md)** - Task card index and progress tracking
- **[INCR-W1-1-Gap-Extraction-Engine.md](incremental-review/INCR-W1-1-Gap-Extraction-Engine.md)** - Gap extraction engine (6-8h) - 🟢 Ready
- 15 additional task cards (pending specification)

**Master Plan:**
- **[INCREMENTAL_REVIEW_WAVE_PLAN.md](INCREMENTAL_REVIEW_WAVE_PLAN.md)** - Complete wave implementation roadmap

**Waves:** 4 waves (Foundation → Integration → UX → Advanced)  
**Effort:** 85-110 hours (10-14 developer-days)  
**Status:** 1/16 Complete (6% specified)  
**Priority:** 🔴 Critical for production readiness

**Wave Breakdown:**
- **Wave 1 (Foundation):** 6 tasks, 28-36 hours
- **Wave 2 (Integration):** 5 tasks, 32-42 hours
- **Wave 3 (UX):** 3 tasks, 14-18 hours
- **Wave 4 (Advanced):** 2 tasks, 11-14 hours (optional)

---

## 📄 Root Task Card Files

- **`INDIVIDUAL_TASK_CARDS_SUMMARY.md`** - Summary of all individual integration task cards with implementation guide
- **`INCREMENTAL_REVIEW_WAVE_PLAN.md`** ⭐ NEW - Master wave plan for incremental review implementation

---

## 📊 Overall Progress

| Category | Total | Complete | In Progress | Ready | Completion % |
|----------|-------|----------|-------------|-------|--------------|
| Agent | 4 | 1 | 0 | 3 | 25% |
| Automation | 4 | 1 | 0 | 3 | 25% |
| Integration | 5 | 0 | 0 | 5 | 0% |
| E2E | 2 | 0 | 0 | 2 | 0% |
| Evidence Enhancement | 8 | 0 | 0 | 8 | 0% |
| **Incremental Review** ⭐ | **16** | **0** | **0** | **1** | **6%** |
| **TOTAL** | **39** | **2** | **0** | **22** | **6%** |

---

## 🎯 Implementation Order

### Wave 1 (Foundation) - ✅ COMPLETE
1. ✅ Task #4: Deep Coverage Decision
2. ✅ Task #13.2: File Locking & Concurrency
3. ✅ Orchestrator refactoring (PR #11)
4. ✅ Test infrastructure setup (Task #5)

### Wave 2 (Core Features) - 🔄 IN PROGRESS
**Automation:**
- Task #13.1: Enhanced Retry Logic (6-8h)
- Task #14: Improved Logging (4-6h)

**Evidence Quality (Parallel):**
- Task #16: Multi-Dimensional Scoring (8-10h) ⭐ BLOCKS integration tests
- Task #17: Provenance Tracking (6-8h) ⭐ BLOCKS integration tests

**Integration Tests (After #16, #17):**
- Task #6: Journal→Judge Flow (8-10h)
- Task #7: Version History→CSV Sync (5-7h)

### Wave 3 (Advanced Features)
**Evidence Quality:**
- Task #18: Inter-Rater Reliability (6-8h)
- Task #19: Temporal Coherence (4-6h)
- Task #20: Evidence Triangulation (6-8h)

**Integration Tests:**
- Task #8: Judge DRA Appeal Flow (8-10h)
- Task #9: Orchestrator Integration (8-10h)

### Wave 4 (Completion & Polish)
**Evidence Quality:**
- Task #21: GRADE Quality Assessment (8-10h)

**E2E Tests:**
- Task #10: Full Pipeline Test (12-16h)
- Task #11: Convergence Loop Test (12-16h)

**Remaining:**
- Task #1: Fix DRA Prompting (2-3h)
- Task #2: Refactor Judge Version History (4-6h)
- Task #3: Document Chunking (6-8h)
- Task #15: Health Checks (3-4h)

**Optional:**
- Task #22: Publication Bias Detection (6-8h)
- Task #23: COI Analysis (4-6h)

---

## 🔗 Dependencies

```
Evidence Enhancement (#16, #17)
    ↓
Integration Tests Wave 2 (#6, #7)
    ↓
Evidence Enhancement (#18, #19, #20)
    ↓
Integration Tests Wave 3 (#8, #9)
    ↓
Evidence Enhancement (#21)
    ↓
E2E Tests (#10, #11)
```

---

## 📝 Task Card Format

Each task card includes:
- **Problem Statement** - What needs to be solved
- **Acceptance Criteria** - Original + Enhanced (for evidence quality)
- **Implementation Guide** - Step-by-step with code examples
- **Test Cases** - Core + Enhanced validation
- **Success Criteria** - Measurable outcomes
- **Estimated Effort** - Time estimates
- **Dependencies** - Blocking tasks
- **Status Indicators** - Ready, In Progress, Complete

---

## 🎨 Status Legend

- ✅ **COMPLETE** - Implemented and merged
- 🔄 **IN PROGRESS** - Currently being developed
- 🟢 **READY** - Specifications complete, ready for implementation
- 🟡 **OPTIONAL** - Nice-to-have features
- 🔴 **BLOCKED** - Waiting on dependencies

---

**Last Updated:** November 14, 2025  
**Next Milestone:** Complete Wave 2 (Evidence Enhancement #16-17, Integration Tests #6-7)  
**Reference:** `/docs/CONSOLIDATED_ROADMAP.md` for complete project overview
