# Dashboard-CLI Parity Task Cards - Complete Package

**Created:** November 21, 2025  
**Purpose:** Close the 68% → 95% Dashboard-CLI parity gap  
**Total Tasks:** 12 across 3 waves  
**Total Effort:** 92-126 hours (11-16 developer-days)

---

## 📦 Package Contents

This directory contains comprehensive task cards for achieving Dashboard-CLI feature parity in the Literature Review system.

### Documentation Structure

```
task-cards/dashboard-cli-parity/
├── README.md                                    # Overview & navigation
├── IMPLEMENTATION_PLAN.md                       # 4-week roadmap
├── PARITY-W1-1-Output-Directory-Selector.md    # CRITICAL (12-16h)
├── PARITY-W1-2-Advanced-Options-Panel.md       # CRITICAL (10-14h)
├── PARITY-W1-3-Fresh-Analysis-Trigger.md       # CRITICAL (6-8h)
├── PARITY-W2-1-Config-File-Upload.md           # HIGH (8-10h)
├── PARITY-W2-2-Force-Reanalysis-Control.md     # HIGH (4-6h)
├── PARITY-W2-3-Cache-Management.md             # HIGH (6-8h)
├── PARITY-W2-W3-TASK-CARDS.md                  # Abbreviated Wave 2&3
├── WAVE_2_3_REMAINING_CARDS.md                 # Detailed remaining tasks
└── COMPLETE_PACKAGE_SUMMARY.md                 # This file
```

---

## 🎯 Executive Summary

### Problem Statement

The Dashboard currently has **68% functional parity** with CLI, creating friction for users who need advanced features. Three critical gaps prevent full Dashboard adoption:

1. **No output directory control** (CLI has `--output-dir`)
2. **Limited configuration flags** (only 7/20 CLI flags exposed)
3. **Cannot trigger fresh analysis** in chosen directories

### Solution Overview

Implement 12 task cards across 3 development waves:
- **Wave 1 (Critical):** Output directory selector, advanced options panel, fresh analysis trigger
- **Wave 2 (High Priority):** Config upload, force re-analysis, cache management, resume controls, pre-filter config
- **Wave 3 (Medium Priority):** Resource monitoring, direct directory access, dry-run mode, experimental features

### Expected Outcomes

- **Parity Improvement:** 68% → 95% (+27 percentage points)
- **User Satisfaction:** Dashboard becomes viable CLI replacement
- **Feature Count:** 116 → 162 Dashboard features
- **Timeline:** 4 weeks with 2-3 developers

---

## 📊 Detailed Task Breakdown

### Wave 1: Critical Gaps (Week 1)

| Task | File | Priority | Effort | Description |
|------|------|----------|--------|-------------|
| **W1-1** | `PARITY-W1-1-Output-Directory-Selector.md` | 🔴 CRITICAL | 12-16h | 3-mode output directory selector (auto/custom/existing) with security validation |
| **W1-2** | `PARITY-W1-2-Advanced-Options-Panel.md` | 🔴 CRITICAL | 10-14h | Collapsible panel exposing 17/20 CLI flags with validation |
| **W1-3** | `PARITY-W1-3-Fresh-Analysis-Trigger.md` | 🔴 CRITICAL | 6-8h | Auto-detection of directory state to trigger fresh vs continuation analysis |

**Wave 1 Total:** 28-38 hours  
**Parity Increase:** 68% → 82% (+14%)

### Wave 2: High Priority Features (Weeks 2-3)

| Task | File | Priority | Effort | Description |
|------|------|----------|--------|-------------|
| **W2-1** | `PARITY-W2-1-Config-File-Upload.md` | 🟠 HIGH | 8-10h | Upload custom `pipeline_config.json` with schema validation and preview |
| **W2-2** | `PARITY-W2-2-Force-Reanalysis-Control.md` | 🟠 HIGH | 4-6h | Force re-analysis checkbox with cost impact warnings |
| **W2-3** | `PARITY-W2-3-Cache-Management.md` | 🟠 HIGH | 6-8h | Cache statistics dashboard + selective clearing (by age/model/cache type) |
| **W2-4** | `WAVE_2_3_REMAINING_CARDS.md#W2-4` | 🟠 HIGH | 8-12h | Resume from stage/checkpoint with auto-detection |
| **W2-5** | `WAVE_2_3_REMAINING_CARDS.md#W2-5` | 🟠 HIGH | 6-8h | Pre-filter threshold slider with live cost estimation |

**Wave 2 Total:** 32-44 hours  
**Parity Increase:** 82% → 88% (+6%)

### Wave 3: Medium Priority Enhancements (Week 4)

| Task | File | Priority | Effort | Description |
|------|------|----------|--------|-------------|
| **W3-1** | `WAVE_2_3_REMAINING_CARDS.md#W3-1` | 🟡 MEDIUM | 10-14h | Real-time WebSocket resource monitoring (CPU, memory, cost, API calls) |
| **W3-2** | `WAVE_2_3_REMAINING_CARDS.md#W3-2` | 🟡 MEDIUM | 12-16h | In-place directory access with symlinks (no file copying) |
| **W3-3** | `WAVE_2_3_REMAINING_CARDS.md#W3-3` | 🟡 MEDIUM | 6-8h | Dry-run validation with execution plan preview |
| **W3-4** | `WAVE_2_3_REMAINING_CARDS.md#W3-4` | 🟡 MEDIUM | 4-6h | Experimental features toggle with stability warnings |

**Wave 3 Total:** 32-44 hours  
**Parity Increase:** 88% → 95% (+7%)

---

## 🔍 Task Card Format

Each detailed task card includes:

### Standard Sections

1. **Problem Statement** - Current state, CLI capability, user impact, gap description
2. **Objective** - What the task achieves
3. **Design** - Complete UI mockups (HTML/CSS/JavaScript) and backend implementation (Python/FastAPI)
4. **Acceptance Criteria** - Functional requirements, UX requirements, CLI parity checklist, edge cases
5. **Testing Plan** - Unit tests, integration tests, E2E tests, manual testing checklist
6. **Documentation Updates** - User guide examples, API documentation
7. **Deployment Checklist** - Step-by-step deployment validation
8. **Success Metrics** - Parity scores, monitoring KPIs

### Example Structure

```markdown
# PARITY-WX-Y: Task Name

**Priority:** 🔴/🟠/🟡 | **Effort:** X-Yh | **Wave:** N

## Problem Statement
[Current state vs CLI capability]

## Objective
[What this task achieves]

## Design
### UI Components
[Complete HTML/JS code]

### Backend Implementation
[Complete Python/FastAPI code]

## Acceptance Criteria
- [ ] Functional requirement 1
- [ ] Functional requirement 2
...

## Testing Plan
[Unit tests, integration tests, E2E tests]

## Documentation Updates
[User guide excerpts]

## Deployment Checklist
[Step-by-step verification]

## Success Metrics
[Parity improvement, KPIs]
```

---

## 🚀 Implementation Strategy

### Week-by-Week Plan

**Week 1: Critical Foundation**
- Mon-Tue: Implement W1-1 (Output Directory Selector)
- Wed-Thu: Implement W1-2 (Advanced Options Panel)
- Fri: Implement W1-3 (Fresh Analysis Trigger)
- Weekend: Integration testing

**Week 2: High Priority Features Part 1**
- Mon-Tue: Implement W2-1 (Config Upload) + W2-2 (Force Re-analysis)
- Wed-Thu: Implement W2-3 (Cache Management)
- Fri: Testing and documentation

**Week 3: High Priority Features Part 2**
- Mon-Tue: Implement W2-4 (Resume Controls)
- Wed-Thu: Implement W2-5 (Pre-filter Config)
- Fri: Integration testing and Wave 2 review

**Week 4: Polish and Enhancements**
- Mon-Tue: Implement W3-1 (Resource Monitoring) + W3-2 (Direct Directory)
- Wed-Thu: Implement W3-3 (Dry-Run) + W3-4 (Experimental Features)
- Fri: Final testing, documentation, deployment

### Team Allocation

**2-Developer Team:**
- **Developer A (Frontend Focus):** W1-1 UI, W1-2 UI, W1-3 UI, W2-1 validation, W2-5 UI, W3-1 WebSocket UI
- **Developer B (Backend Focus):** W1-1 API, W1-3 detection, W2-1 schema, W2-3 cache, W2-4 resume, W3-2 symlinks

**3-Developer Team:**
- **Frontend Dev:** All UI work (W1-1, W1-2, W1-3, W2-5, W3-1 displays)
- **Backend Dev 1:** Core features (W1-1 API, W1-3, W2-1, W2-3)
- **Backend Dev 2:** Advanced features (W2-2, W2-4, W3-1 WebSocket, W3-2, W3-3, W3-4)

---

## ✅ Success Criteria

### Quantitative Metrics

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **Parity Score** | 68% | 95% | +27 pp |
| **Dashboard Features** | 116 | 162 | +46 features |
| **CLI Flags Exposed** | 7/20 | 17/20 | +10 flags |
| **User Satisfaction** | 3.2/5 | 4.5/5 | +1.3 points |

### Qualitative Outcomes

✅ **Users can:**
- Select custom output directories (like CLI `--output-dir`)
- Trigger fresh analysis in empty folders (like CLI behavior)
- Access all major CLI flags through Dashboard UI
- Upload custom configurations (like CLI `--config`)
- Manage cache visibility and clearing (better than CLI)
- Monitor resource usage in real-time (Dashboard advantage)
- Resume failed jobs from checkpoints (like CLI resume)
- Preview execution plans before running (like CLI `--dry-run`)

✅ **System provides:**
- 95%+ functional parity with CLI
- No critical feature gaps preventing Dashboard adoption
- Enhanced capabilities CLI lacks (cache visibility, resource monitoring)
- Seamless CLI-Dashboard interoperability

---

## 📚 Related Documentation

### Assessment Documents
- `DASHBOARD_CLI_PARITY_ASSESSMENT_V2.md` - Detailed parity analysis showing 68% current state
- `INCREMENTAL_REVIEW_IMPLEMENTATION_STATUS.md` - Incremental features (85% complete)

### Reference Implementation
- `pipeline_orchestrator.py` - CLI implementation (all flags and features)
- `webdashboard/app.py` - Current Dashboard backend
- `webdashboard/templates/index.html` - Current Dashboard frontend
- `pipeline_config.json` - Configuration schema reference

### User Documentation
- `docs/DASHBOARD_CLI_PARITY.md` - Original parity doc (superseded, now has warning)
- User guides will be updated as part of each task card

---

## 🔄 Continuous Improvement

### After Deployment

**Monitor:**
- Feature usage analytics (which advanced options used most)
- Error rates (new vs existing endpoints)
- Performance impact (resource monitoring overhead)
- User feedback (surveys, support tickets)

**Track Parity:**
- Quarterly parity reassessments
- New CLI features trigger Dashboard task cards
- Maintain 95%+ parity as system evolves

**Iterate:**
- Expand abbreviated task cards as needed
- Add new waves for emerging features
- Optimize based on usage patterns

---

## 📞 Support

### Questions About Task Cards?

1. **Which task to start with?** → Wave 1 in order (W1-1 → W1-2 → W1-3)
2. **Need more detail on abbreviated cards?** → See `WAVE_2_3_REMAINING_CARDS.md` or request full expansion
3. **Found a gap in task card?** → Update task card with lessons learned
4. **Need architecture guidance?** → Reference CLI implementation in `pipeline_orchestrator.py`

### Development Resources

- **CLI Reference:** `python pipeline_orchestrator.py --help`
- **Dashboard API:** `http://localhost:8000/docs` (FastAPI Swagger)
- **Testing:** `pytest tests/dashboard/ -v`
- **Code Reviews:** Required before merging each task

---

## 🎓 Key Takeaways

### For Project Managers
- **Clear Roadmap:** 4-week timeline with concrete deliverables
- **Measurable Progress:** Parity score increases wave-by-wave (68→82→88→95%)
- **Resource Planning:** 2-3 developers, 11-16 developer-days total
- **Risk Mitigation:** Each wave independently deployable

### For Developers
- **Complete Specifications:** Every task has full code examples
- **Testing Guidance:** Unit/integration/E2E tests for each feature
- **Incremental Delivery:** Can implement in any order within wave
- **Quality Assurance:** 90%+ test coverage required per task

### For Users
- **Feature Parity:** Dashboard will match CLI capabilities
- **Enhanced UX:** Visual controls better than CLI flags
- **Transparency:** Cache stats, cost estimates, resource monitoring
- **Flexibility:** Choose Dashboard or CLI based on preference, not limitation

---

**Package Version:** 1.0  
**Last Updated:** November 21, 2025  
**Status:** Ready for Implementation  
**Estimated Completion:** December 19, 2025 (4 weeks from start)
