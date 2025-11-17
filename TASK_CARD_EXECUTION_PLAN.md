# Task Card Execution Plan

**Created:** November 17, 2025  
**Total Cards:** 20  
**Total Effort:** 51.25 hours  
**Estimated Completion:** ~7 working days (with parallelization)

---

## 📊 Execution Overview

This document tracks the phased execution of enhancement task cards, showing parallel execution opportunities and dependencies.

### Completion Status

- **Wave 0 (Quick Win):** ⏳ 0/1 complete
- **Wave 1 (Core Infrastructure):** ⏳ 0/5 complete  
- **Wave 2 (User Features):** ⏳ 0/6 complete  
- **Wave 3 (Advanced Features):** ⏳ 0/5 complete  
- **Wave 4 (Testing & Documentation):** ⏳ 0/3 complete  
- **Total:** ⏳ 0/20 complete

---

## 🚀 Wave 0: Quick Win (1 minute)

**Execute First** - Prevents CI failures

| Card | Priority | Effort | Dependencies | Status |
|------|----------|--------|--------------|--------|
| ENHANCE-P5-1 | 🔴 HIGH | 1 min | None | ⏳ Not Started |

**Tasks:**
- [ ] ENHANCE-P5-1: Add pytest-asyncio to requirements-dev.txt

**Execution:** Single PR, immediate merge

---

## 🌊 Wave 1: Core Infrastructure (8 hours)

**Can Execute in Parallel** - No dependencies between tasks

| Card | Priority | Effort | Dependencies | Status | Assignee |
|------|----------|--------|--------------|--------|----------|
| ENHANCE-P2-1 | 🟡 MEDIUM | 3h | None | ⏳ Not Started | - |
| ENHANCE-P2-2 | 🟡 MEDIUM | 5h | None | ⏳ Not Started | - |

**Tasks:**
- [ ] ENHANCE-P2-1: Cross-batch duplicate detection (PDF hashing, fuzzy matching)
- [ ] ENHANCE-P2-2: PDF metadata extraction improvements (PyMuPDF, DOI detection)

**Dependencies:**
- None - can work in parallel

**Execution Strategy:**
```
Developer A → ENHANCE-P2-1 (3h)
Developer B → ENHANCE-P2-2 (5h)
Total wall-clock time: 5 hours (parallel)
```

**Output:**
- Enhanced input validation
- Better metadata extraction
- Reduced duplicate papers

---

## 🌊 Wave 2: User Experience Features (17 hours)

**Can Execute in Parallel** - Independent features

| Card | Priority | Effort | Dependencies | Status | Assignee |
|------|----------|--------|--------------|--------|----------|
| ENHANCE-P3-1 | 🟡 MEDIUM | 2h | None | ⏳ Not Started | - |
| ENHANCE-P3-2 | 🟡 MEDIUM | 4h | None | ⏳ Not Started | - |
| ENHANCE-P4-3 | 🟡 MEDIUM | 5h | None | ⏳ Not Started | - |
| ENHANCE-P4-4 | 🟡 MEDIUM | 3h | None | ⏳ Not Started | - |
| ENHANCE-P5-2 | 🟡 MEDIUM | 2h | ENHANCE-P5-1 ✅ | ⏳ Not Started | - |
| ENHANCE-P5-4 | 🟡 MEDIUM | 2h | ENHANCE-P5-1 ✅ | ⏳ Not Started | - |

**Tasks:**
- [ ] ENHANCE-P3-1: Improve ETA accuracy (historical tracking, confidence intervals)
- [ ] ENHANCE-P3-2: Progress replay for historical jobs (timeline reconstruction)
- [ ] ENHANCE-P4-3: Results comparison view (side-by-side job comparison)
- [ ] ENHANCE-P4-4: Results summary cards (quick-view metrics)
- [ ] ENHANCE-P5-2: Integrate run_mode and continue prompts
- [ ] ENHANCE-P5-4: Multi-select pillar support

**Dependencies:**
- ENHANCE-P5-2 & P5-4 require ENHANCE-P5-1 (pytest-asyncio) to be merged first
- All others independent

**Execution Strategy:**
```
Team 1 (Progress):
  Dev A → ENHANCE-P3-1 (2h) → ENHANCE-P3-2 (4h)
  
Team 2 (Results):
  Dev B → ENHANCE-P4-4 (3h) → ENHANCE-P4-3 (5h)
  
Team 3 (Prompts):
  Dev C → ENHANCE-P5-2 (2h) → ENHANCE-P5-4 (2h)
  
Total wall-clock time: 8 hours (parallel)
```

**Output:**
- Better progress tracking
- Job comparison tools
- Enhanced interactive prompts

---

## 🌊 Wave 3: Advanced Features (15.25 hours)

**Mixed Dependencies** - Some parallelization possible

| Card | Priority | Effort | Dependencies | Status | Assignee |
|------|----------|--------|--------------|--------|----------|
| ENHANCE-P5-3 | 🟡 MEDIUM | 3h | ENHANCE-P5-2 ✅ | ⏳ Not Started | - |
| ENHANCE-P5-5 | 🟡 MEDIUM | 1h | ENHANCE-P5-2 ✅ | ⏳ Not Started | - |
| ENHANCE-P5-6 | 🟡 MEDIUM | 2h | P5-2, P5-3, P5-4, P5-5 ✅ | ⏳ Not Started | - |
| ENHANCE-W3-4A | 🟡 MEDIUM | 4h | None | ⏳ Not Started | - |
| ENHANCE-W3-4B | 🟡 MEDIUM | 2h | ENHANCE-W3-4A ✅ | ⏳ Not Started | - |
| ENHANCE-W3-2A | 🟡 MEDIUM | 3h | None | ⏳ Not Started | - |
| ENHANCE-W3-2B | 🟡 MEDIUM | 2h | ENHANCE-W3-2A ✅ | ⏳ Not Started | - |

**Tasks:**
- [ ] ENHANCE-P5-3: Prompt history/replay (job metadata integration)
- [ ] ENHANCE-P5-5: Configurable timeout per prompt type
- [ ] ENHANCE-P5-6: Interactive prompts documentation
- [ ] ENHANCE-W3-4A: Evidence decay integration with gap analysis
- [ ] ENHANCE-W3-4B: Field-specific half-life presets
- [ ] ENHANCE-W3-2A: Dynamic ROI priority adjustment
- [ ] ENHANCE-W3-2B: Cost-aware search ordering

**Dependencies:**
- **Chain 1 (Prompts):** P5-3 & P5-5 require P5-2 → P5-6 requires all Phase 5 cards
- **Chain 2 (Evidence):** W3-4B requires W3-4A
- **Chain 3 (Search):** W3-2B requires W3-2A

**Execution Strategy:**
```
Team 1 (Prompts):
  Dev A → ENHANCE-P5-3 (3h)
  Dev B → ENHANCE-P5-5 (1h) → wait → ENHANCE-P5-6 (2h)
  
Team 2 (Evidence):
  Dev C → ENHANCE-W3-4A (4h) → ENHANCE-W3-4B (2h)
  
Team 3 (Search):
  Dev D → ENHANCE-W3-2A (3h) → ENHANCE-W3-2B (2h)
  
Total wall-clock time: 9 hours (parallel)
```

**Output:**
- Full interactive prompts feature suite
- Evidence decay system
- Intelligent search optimization

---

## 🌊 Wave 4: Testing & Documentation (9 hours)

**Can Execute in Parallel** - Independent deliverables

| Card | Priority | Effort | Dependencies | Status | Assignee |
|------|----------|--------|--------------|--------|----------|
| ENHANCE-TEST-1 | 🟡 MEDIUM | 4h | All features ✅ | ⏳ Not Started | - |
| ENHANCE-DOC-1 | 🟡 MEDIUM | 3h | None | ⏳ Not Started | - |
| ENHANCE-DOC-2 | 🟢 LOW | 2h | None | ⏳ Not Started | - |

**Tasks:**
- [ ] ENHANCE-TEST-1: End-to-end dashboard tests (Playwright/Selenium)
- [ ] ENHANCE-DOC-1: Production deployment guide
- [ ] ENHANCE-DOC-2: API reference documentation (OpenAPI/Swagger)

**Dependencies:**
- ENHANCE-TEST-1 should ideally run after all features implemented
- Documentation can start anytime

**Execution Strategy:**
```
Dev A → ENHANCE-TEST-1 (4h)  [After Wave 3 complete]
Dev B → ENHANCE-DOC-1 (3h)   [Can start immediately]
Dev C → ENHANCE-DOC-2 (2h)   [Can start immediately]

Total wall-clock time: 4 hours (parallel)
```

**Output:**
- Comprehensive test coverage
- Production-ready deployment docs
- Auto-generated API docs

---

## 📈 Execution Timeline

### Sequential Execution (Single Developer)
```
Total: 51.25 hours ≈ 6.4 working days
```

### Parallel Execution (4 Developers)
```
Wave 0: 1 minute
Wave 1: 5 hours   (2 devs in parallel)
Wave 2: 8 hours   (3 devs in parallel)
Wave 3: 9 hours   (4 devs in parallel)
Wave 4: 4 hours   (3 devs in parallel)
─────────────────
Total:  26 hours ≈ 3.3 working days
```

### Optimized Execution (2 Developers)
```
Wave 0: 1 minute
Wave 1: 5 hours   (2 devs in parallel)
Wave 2: 9.5 hours (2 devs in parallel: 8h+6h, 9h+8.5h)
Wave 3: 9 hours   (2 devs in parallel: 9h chain, 8h chain)
Wave 4: 4 hours   (DOC-1+DOC-2 parallel=3h, then TEST-1=4h)
─────────────────
Total:  27.5 hours ≈ 3.5 working days
```

---

## 🔗 Dependency Graph

```
Wave 0: Quick Win
  └─ P5-1 (1m) ───┐
                  │
Wave 1: Core      │
  ├─ P2-1 (3h)    │
  └─ P2-2 (5h)    │
                  │
Wave 2: UX        ▼
  ├─ P3-1 (2h)
  ├─ P3-2 (4h)
  ├─ P4-3 (5h)
  ├─ P4-4 (3h)
  ├─ P5-2 (2h) ◄──┘
  └─ P5-4 (2h) ◄──┘
      │       │
Wave 3: Advanced
  ├─ P5-3 (3h) ◄──┘
  ├─ P5-5 (1h) ◄──┘
  │     │     │
  │     └─────┴──► P5-6 (2h)
  │
  ├─ W3-4A (4h) ──► W3-4B (2h)
  └─ W3-2A (3h) ──► W3-2B (2h)
      │
Wave 4: Test/Doc
  ├─ TEST-1 (4h) ◄─┴─ (ideally after all features)
  ├─ DOC-1 (3h)
  └─ DOC-2 (2h)
```

---

## 📋 PR Submission Plan

### Wave 0: Immediate
- **PR #1:** ENHANCE-P5-1 (pytest-asyncio dependency)
  - Reviewers: 1
  - Merge: Immediate

### Wave 1: Week 1
- **PR #2:** ENHANCE-P2-1 (Duplicate detection)
  - Reviewers: 2
  - Tests: Unit tests for SHA256 hashing, fuzzy matching
  
- **PR #3:** ENHANCE-P2-2 (PDF metadata extraction)
  - Reviewers: 2
  - Tests: PyMuPDF integration tests

### Wave 2: Week 1-2
- **PR #4:** ENHANCE-P3-1 + ENHANCE-P3-2 (Progress monitoring)
  - Combined PR (related features)
  - Reviewers: 2
  - Tests: ETA calculation tests, timeline reconstruction
  
- **PR #5:** ENHANCE-P4-3 + ENHANCE-P4-4 (Results visualization)
  - Combined PR (related features)
  - Reviewers: 2
  - Tests: API endpoint tests, UI rendering tests
  
- **PR #6:** ENHANCE-P5-2 + ENHANCE-P5-4 (Interactive prompts)
  - Combined PR (related features)
  - Reviewers: 2
  - Tests: Prompt flow tests

### Wave 3: Week 2-3
- **PR #7:** ENHANCE-P5-3 + ENHANCE-P5-5 (Prompt enhancements)
  - Reviewers: 2
  - Tests: History persistence, timeout handling
  
- **PR #8:** ENHANCE-P5-6 (Interactive prompts docs)
  - Reviewers: 1
  - Tests: Documentation review
  
- **PR #9:** ENHANCE-W3-4A + ENHANCE-W3-4B (Evidence decay)
  - Combined PR (related features)
  - Reviewers: 2
  - Tests: Decay calculation tests, field preset tests
  
- **PR #10:** ENHANCE-W3-2A + ENHANCE-W3-2B (Search optimization)
  - Combined PR (related features)
  - Reviewers: 2
  - Tests: ROI calculation tests, cost estimation tests

### Wave 4: Week 3
- **PR #11:** ENHANCE-TEST-1 (E2E tests)
  - Reviewers: 2
  - Tests: All E2E tests must pass
  
- **PR #12:** ENHANCE-DOC-1 (Deployment guide)
  - Reviewers: 1
  - Tests: Documentation review, deployment testing
  
- **PR #13:** ENHANCE-DOC-2 (API reference)
  - Reviewers: 1
  - Tests: Swagger UI validation

---

## ✅ Completion Tracking

### Phase 5: Interactive Prompts
- [ ] ENHANCE-P5-1 (pytest-asyncio) - **Wave 0**
- [ ] ENHANCE-P5-2 (run_mode prompts) - **Wave 2**
- [ ] ENHANCE-P5-3 (prompt history) - **Wave 3**
- [ ] ENHANCE-P5-4 (multi-select) - **Wave 2**
- [ ] ENHANCE-P5-5 (timeout config) - **Wave 3**
- [ ] ENHANCE-P5-6 (documentation) - **Wave 3**

### Phase 4: Results Visualization
- [ ] ENHANCE-P4-3 (comparison view) - **Wave 2**
- [ ] ENHANCE-P4-4 (summary cards) - **Wave 2**

### Phase 2 & 3: Input & Progress
- [ ] ENHANCE-P2-1 (duplicate detection) - **Wave 1**
- [ ] ENHANCE-P2-2 (metadata extraction) - **Wave 1**
- [ ] ENHANCE-P3-1 (ETA accuracy) - **Wave 2**
- [ ] ENHANCE-P3-2 (progress replay) - **Wave 2**

### Wave 3: Enhancements
- [ ] ENHANCE-W3-4A (evidence decay) - **Wave 3**
- [ ] ENHANCE-W3-4B (field presets) - **Wave 3**
- [ ] ENHANCE-W3-2A (dynamic ROI) - **Wave 3**
- [ ] ENHANCE-W3-2B (cost-aware search) - **Wave 3**

### Testing & Documentation
- [ ] ENHANCE-TEST-1 (E2E tests) - **Wave 4**
- [ ] ENHANCE-DOC-1 (deployment) - **Wave 4**
- [ ] ENHANCE-DOC-2 (API reference) - **Wave 4**

---

## 🎯 Success Metrics

### Velocity Tracking
- **Target:** 1-2 PRs merged per day
- **Current:** 0 PRs merged
- **On Track:** Yes/No

### Quality Gates
- [ ] All PRs have ≥90% test coverage
- [ ] All PRs reviewed by ≥2 developers
- [ ] No breaking changes without migration guide
- [ ] Documentation updated with each feature

### Timeline
- **Start Date:** TBD
- **Target Completion:** Start + 7 working days
- **Actual Completion:** TBD

---

## 📝 Notes

### Execution Recommendations

1. **Start with Wave 0** - 1 minute fix prevents CI failures for all future PRs
2. **Maximize Wave 1 parallelization** - Two independent features, assign to different devs
3. **Combine related PRs** - Reduces review overhead (e.g., P4-3 + P4-4)
4. **Documentation can start early** - DOC-1 and DOC-2 have no feature dependencies
5. **Hold E2E tests until late** - TEST-1 should run after most features complete

### Risk Mitigation

- **Dependency chains** - Phase 5 cards have longest dependency chain (P5-1 → P5-2 → P5-3 → P5-6)
- **Resource constraints** - With 1-2 devs, expect ~4-5 working days
- **Testing bottleneck** - E2E tests (4h) must run after Wave 3, can't parallelize much

### Future Enhancements

After completing all 20 cards:
- Monitor user feedback for 2-4 weeks
- Prioritize next round of enhancements based on actual usage patterns
- Consider automation for evidence decay parameter tuning
