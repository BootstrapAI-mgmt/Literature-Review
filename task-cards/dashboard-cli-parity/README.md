# Dashboard-CLI Parity Task Cards

**Created:** November 21, 2025  
**Last Updated:** December 9, 2025  
**Based On:** DASHBOARD_CLI_PARITY_ASSESSMENT_V2.md  
**Objective:** Close critical gaps between Dashboard and CLI functionality

---

## 📊 Overview

This directory contains task cards to achieve **feature parity** between the Dashboard and CLI, focusing on closing the **68% → 95%** parity gap.

**Current Parity:** ✅ **95%** (Target Achieved)  
**Starting Parity:** 68%  
**Critical Gaps:** 3 → ✅ 0  
**High Priority Gaps:** 8 → ✅ 0  
**Total Tasks:** 12 → ✅ 12 Complete

---

## 🎯 Task Organization

### Wave 1: Critical Gaps (Week 1) - 3 Tasks ✅ COMPLETE
**Goal:** Close the 3 critical gaps preventing Dashboard from matching core CLI functionality

| Task | Priority | Effort | Status |
|------|----------|--------|--------|
| PARITY-W1-1: Output Directory Selector | 🔴 CRITICAL | 12-16h | ✅ DONE |
| PARITY-W1-2: Advanced Options Panel | 🔴 CRITICAL | 10-14h | ✅ DONE |
| PARITY-W1-3: Fresh Analysis Trigger | 🔴 CRITICAL | 6-8h | ✅ DONE |

### Wave 2: High Priority Features (Weeks 2-3) - 5 Tasks ✅ COMPLETE
**Goal:** Add commonly-used CLI flags to Dashboard

| Task | Priority | Effort | Status |
|------|----------|--------|--------|
| PARITY-W2-1: Config File Upload | 🟠 HIGH | 8-10h | ✅ DONE |
| PARITY-W2-2: Force Re-analysis Control | 🟠 HIGH | 4-6h | ✅ DONE |
| PARITY-W2-3: Cache Management | 🟠 HIGH | 6-8h | ✅ DONE |
| PARITY-W2-4: Resume Controls | 🟠 HIGH | 8-12h | ✅ DONE |
| PARITY-W2-5: Pre-filter Configuration | 🟠 HIGH | 6-8h | ✅ DONE |

### Wave 3: Medium Priority Enhancements (Week 4) - 4 Tasks ✅ COMPLETE
**Goal:** Add nice-to-have features for power users

| Task | Priority | Effort | Status | PR |
|------|----------|--------|--------|-----|
| PARITY-W3-1: Resource Monitoring Dashboard | 🟡 MEDIUM | 10-14h | ✅ DONE | #88 |
| PARITY-W3-2: Direct Directory Access | 🟡 MEDIUM | 12-16h | ✅ DONE | #89 |
| PARITY-W3-3: Dry-Run Mode | 🟡 MEDIUM | 6-8h | ✅ DONE | #90 |
| PARITY-W3-4: Experimental Features Toggle | 🟡 MEDIUM | 4-6h | ✅ DONE | #91 |

---

## 📈 Effort Summary

**Total Estimated Effort:** 92-126 hours (11-16 developer-days)

**Wave Breakdown:**
- Wave 1 (Critical): 28-38 hours (3.5-4.5 days)
- Wave 2 (High): 32-44 hours (4-5.5 days)
- Wave 3 (Medium): 32-44 hours (4-5.5 days)

**Team Recommendation:**
- 2-3 full-stack developers (Python + JavaScript)
- 3-4 weeks with parallel execution
- Sprint-based approach (1 wave per sprint)

---

## 🎯 Success Criteria

### Wave 1 Completion (Critical)
- [x] Users can select custom output directories in Dashboard
- [x] Advanced options panel exposes key CLI flags
- [x] Fresh analysis can be triggered in empty/existing directories
- [x] Dashboard parity increases to **80%+**

### Wave 2 Completion (High Priority)
- [x] Config file upload working
- [x] Force re-analysis, cache clearing available
- [x] Resume from stage/checkpoint functional
- [x] Pre-filter controls exposed
- [x] Dashboard parity increases to **88%+**

### Wave 3 Completion (Medium Priority)
- [x] Resource monitoring visible (CPU, memory, cost)
- [x] Dashboard can work with user-specified directories directly
- [x] Dry-run validation available
- [x] Experimental features toggleable
- [x] Dashboard parity reaches **95%+**

---

## 🚀 Deployment Strategy

### Sprint 1 (Week 1): Critical Gaps
```
Mon-Tue: PARITY-W1-1 (Output Directory Selector)
Wed-Thu: PARITY-W1-2 (Advanced Options Panel)
Fri:     PARITY-W1-3 (Fresh Analysis Trigger)
Weekend: Testing & integration
```

### Sprint 2 (Weeks 2-3): High Priority
```
Week 2:
  Mon-Wed: PARITY-W2-1, PARITY-W2-2
  Thu-Fri: PARITY-W2-3, PARITY-W2-4
Week 3:
  Mon-Tue: PARITY-W2-5
  Wed-Fri: Testing, documentation
```

### Sprint 3 (Week 4): Medium Priority
```
Mon-Tue: PARITY-W3-1
Wed-Thu: PARITY-W3-2
Fri:     PARITY-W3-3, PARITY-W3-4
Weekend: Final testing, release
```

---

## 📝 Documentation Updates Required

Each task should update:
1. User guide (how to use new features)
2. API documentation (if endpoints added)
3. Migration guide (CLI → Dashboard workflows)
4. Dashboard help tooltips

---

## 🧪 Testing Requirements

**Per Task:**
- Unit tests (90% coverage)
- Integration tests (happy path + edge cases)
- E2E tests (user workflows)
- Regression tests (existing features)

**Final Validation:**
- All 12 tasks pass tests
- Dashboard parity ≥ 95%
- No regressions in existing functionality
- Performance benchmarks maintained

---

## 📞 Dependencies

**External:**
- None (all internal implementation)

**Internal:**
- Existing Dashboard architecture (FastAPI)
- Existing CLI implementation (reference for features)
- UI component library (Bootstrap)
- Frontend frameworks (JavaScript, WebSockets)

**Blockers:**
- None identified (can start immediately)

---

## 🎓 References

**Assessment Document:**
- `/workspaces/Literature-Review/DASHBOARD_CLI_PARITY_ASSESSMENT_V2.md`

**CLI Implementation:**
- `pipeline_orchestrator.py` (all CLI flags)
- `literature_review/orchestrator.py` (core logic)

**Dashboard Implementation:**
- `webdashboard/app.py` (backend API)
- `webdashboard/templates/index.html` (frontend UI)

**Configuration:**
- `pipeline_config.json` (default configuration)

---

## 📖 Quick Navigation

### By Priority
- **🔴 CRITICAL Tasks:** [W1-1](PARITY-W1-1-Output-Directory-Selector.md) | [W1-2](PARITY-W1-2-Advanced-Options-Panel.md) | [W1-3](PARITY-W1-3-Fresh-Analysis-Trigger.md)
- **🟠 HIGH Tasks:** [W2-1](PARITY-W2-1-Config-File-Upload.md) | [W2-2](PARITY-W2-2-Force-Reanalysis-Control.md) | [W2-3](PARITY-W2-3-Cache-Management.md) | [W2-4 & W2-5](WAVE_2_3_REMAINING_CARDS.md)
- **🟡 MEDIUM Tasks:** [W3-1 through W3-4](WAVE_2_3_REMAINING_CARDS.md)

### By Document Type
- **Implementation Guide:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - 4-week roadmap with team structure
- **Complete Summary:** [COMPLETE_PACKAGE_SUMMARY.md](COMPLETE_PACKAGE_SUMMARY.md) - Package overview
- **Detailed Task Cards:** Individual `PARITY-W*-*.md` files (Waves 1 & 2)
- **Condensed Task Cards:** [WAVE_2_3_REMAINING_CARDS.md](WAVE_2_3_REMAINING_CARDS.md) (remaining tasks)
- **Original Reference:** [PARITY-W2-W3-TASK-CARDS.md](PARITY-W2-W3-TASK-CARDS.md) (abbreviated overview)

### By Week
- **Week 1:** [W1-1](PARITY-W1-1-Output-Directory-Selector.md), [W1-2](PARITY-W1-2-Advanced-Options-Panel.md), [W1-3](PARITY-W1-3-Fresh-Analysis-Trigger.md)
- **Week 2-3:** [W2-1](PARITY-W2-1-Config-File-Upload.md), [W2-2](PARITY-W2-2-Force-Reanalysis-Control.md), [W2-3](PARITY-W2-3-Cache-Management.md), [W2-4 & W2-5](WAVE_2_3_REMAINING_CARDS.md)
- **Week 4:** [W3 Tasks](WAVE_2_3_REMAINING_CARDS.md)

---

**Plan Version:** 1.0  
**Next Review:** After Wave 1 completion  
**Owner:** Development Team  
**Package Status:** ✅ Complete - Ready for Implementation
