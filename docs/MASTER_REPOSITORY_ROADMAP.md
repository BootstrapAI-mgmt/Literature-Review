# Master Repository Roadmap

> **Status:** Living Document - Updated with each wave completion  
> **Purpose:** Tracks completed work and planned development for the Literature Review repository

**Version:** 2.0.0  
**Created:** December 19, 2025  
**Supersedes:** CONSOLIDATED_ROADMAP.md (Version 1.3, November 14, 2025)

---

## Executive Summary

This roadmap consolidates all development waves for the Literature Review Automation System. It includes completed infrastructure, evidence quality enhancements, and the newly planned Operationalization Wave for research actionability.

### At a Glance

| Wave | Status | Completion | Hours | Task Cards |
|------|--------|------------|-------|------------|
| Wave 1: Foundation | ✅ Complete | 100% | ~40h | 5 |
| Wave 2: Core Features | ✅ Complete | 100% | ~45h | 6 |
| Wave 3: Advanced Features | ✅ Near Complete | 86% | ~52h | 7 |
| Wave 4: Production Polish | 📋 Planned | 0% | 108-145h | 8 |
| Enhancement Wave 1 | ✅ Complete | 100% | ~25h | 4 |
| Enhancement Wave 2 | ✅ Complete | 100% | ~24h | 3 |
| Enhancement Wave 3 | ✅ Complete | 100% | ~32h | 4 |
| **Operationalization Wave** | 📋 Planned | 0% | 80-100h | 8 |

**Total Task Cards:** 45  
**Completed:** 29  
**In Progress:** 1 (Temporal Coherence)  
**Planned:** 15

---

## Completed Development

### ✅ Wave 1: Foundation (Complete - November 2025)

**Objective:** Establish core pipeline and test infrastructure

| Task | Description | PR | Status |
|------|-------------|----|----|
| Pipeline Orchestrator | 5-stage review pipeline with CLI | - | ✅ Complete |
| Package Refactoring | Flat files → `literature_review/` package | - | ✅ Complete |
| Test Infrastructure | pytest with unit/component/integration/e2e | - | ✅ Complete |
| Unit Test Suite | 745+ passing unit tests | - | ✅ Complete |
| Documentation | Architecture and refactoring docs | - | ✅ Complete |

**Achievements:**
- Single-command pipeline execution
- Organized package structure
- Comprehensive test foundation
- 745+ passing tests

---

### ✅ Wave 2: Core Features (Complete - November 14, 2025)

**Objective:** Implement checkpoint/resume, evidence scoring, and integration testing

| Task | Description | PR | Status |
|------|-------------|----|----|
| #13.1 Checkpoint/Resume | Interrupt recovery capability | #11 | ✅ Merged |
| #13.2 Error Recovery | Retry logic with exponential backoff | #12 | ✅ Merged |
| #16 Multi-Dimensional Scoring | 6-dimension evidence scoring | #14 | ✅ Merged |
| #17 Claim Provenance | Page, section, quote tracking | #14 | ✅ Merged |
| #6 INT-001 Journal→Judge | Integration test for review flow | #16 | ✅ Merged |
| #7 INT-003 CSV Sync | Integration test for sync stage | #17 | ✅ Merged |

**Achievements:**
- Pipeline resilient to interruptions
- Automatic retry prevents 80%+ transient failures
- Evidence quality framework with 6 dimensions
- Provenance tracking for all claims
- Integration test coverage established

---

### ✅ Wave 3: Advanced Features (86% Complete - November 2025)

**Objective:** Parallel processing, consensus review, and advanced testing

| Task | Description | PR | Status |
|------|-------------|----|----|
| #14.1 Parallel Processing | Multi-paper batch processing | #19 | ✅ Merged |
| #14.2 Smart Retry Logic | Advanced retry with backoff | #19 | ✅ Merged |
| #14.3 API Quota Management | Rate limiting and quota tracking | #19 | ✅ Merged |
| #18 Inter-Rater Reliability | Multi-judge consensus review | #20 | ✅ Merged |
| #8 INT-002 Appeal Flow | Judge→DRA integration test | #18 | ✅ Merged |
| #9 INT-004/005 Orchestrator | Orchestrator integration tests | #21 | ✅ Merged |
| #19 Temporal Coherence | Time-based quality trends | - | 📋 Ready |

**Achievements:**
- 3-4x faster multi-paper processing
- Consensus review for borderline claims (2.5-3.5 composite)
- 90%+ reduction in manual intervention
- Comprehensive orchestrator testing

**Remaining:**
- Task #19: Temporal Coherence Analysis (8-10 hours)

---

### ✅ Enhancement Wave 1: Core Capabilities (Complete)

**Objective:** Manual deep review, proof scorecards, cost tracking

| Task Card | Description | Status |
|-----------|-------------|--------|
| ENHANCEMENT_WAVE_1_1 | Manual Deep Review | ✅ Complete |
| ENHANCEMENT_WAVE_1_2 | Proof Scorecard | ✅ Complete |
| ENHANCEMENT_WAVE_1_3 | Cost Tracker | ✅ Complete |
| ENHANCEMENT_WAVE_1_4 | Incremental Mode | ✅ Complete |

---

### ✅ Enhancement Wave 2: Analysis Depth (Complete)

**Objective:** Sufficiency matrix, proof chains, triangulation

| Task Card | Description | Status |
|-----------|-------------|--------|
| ENHANCEMENT_WAVE_2_1 | Sufficiency Matrix | ✅ Complete |
| ENHANCEMENT_WAVE_2_2 | Proof Chain Analysis | ✅ Complete |
| ENHANCEMENT_WAVE_2_3 | Evidence Triangulation | ✅ Complete |

---

### ✅ Enhancement Wave 3: Automation (Complete)

**Objective:** Intelligent triggers, search optimization, deduplication

| Task Card | Description | Status |
|-----------|-------------|--------|
| ENHANCEMENT_WAVE_3_1 | Intelligent Triggers | ✅ Complete |
| ENHANCEMENT_WAVE_3_2 | Search Optimizer | ✅ Complete |
| ENHANCEMENT_WAVE_3_3 | Smart Deduplication | ✅ Complete |
| ENHANCEMENT_WAVE_3_4 | Evidence Decay Tracker | ✅ Complete |

---

## Planned Development

### 📋 Wave 4: Production Polish (Planned)

**Objective:** Web dashboard, E2E testing, CI/CD, advanced evidence quality

**Estimated Effort:** 108-145 hours

| Task | Description | Priority | Effort |
|------|-------------|----------|--------|
| #15 Web Dashboard | Full-featured job management UI | 🟢 Medium | 40-60h |
| #20 Evidence Triangulation | Cross-source contradiction flagging | 🟢 Medium | 10-12h |
| #21 GRADE Assessment | Evidence quality level assignment | 🟢 Low | 8-10h |
| #22 Publication Bias | Bias detection and adjustment | 🟢 Low | 12-15h |
| #23 Conflict-of-Interest | COI analysis for sources | 🟢 Low | 10-12h |
| #10 E2E-001 Full Pipeline | End-to-end pipeline test | 🔴 Critical | 12-16h |
| #11 E2E-002 Convergence | Convergence loop testing | 🟡 High | 10-12h |
| #12 GitHub Actions CI/CD | Automated testing pipeline | 🟢 Medium | 6-8h |

**Dependencies:**
- Web Dashboard builds on completed pipeline
- E2E tests require all integration tests complete
- CI/CD wraps all test infrastructure

---

### 📋 Operationalization Wave (Planned - NEW)

**Objective:** Transform research findings into actionable, validated, trackable outputs

**Created:** December 19, 2025  
**Source:** Research Loop Integration Assessment  
**Estimated Effort:** 80-100 hours

#### Overview

This wave implements four major enhancements:
1. **Action Vectors** - Extract executable implementation plans from research
2. **Benchmark Linkage** - Connect performance targets to validation benchmarks
3. **Validation Coverage** - Track design-to-validation gap closure
4. **Pillar Evolution** - Manage pillar lifecycle with approval workflows

#### Visual Roadmap

```
Week 1-2 (Foundation)                 Week 3-4 (Extraction)
┌────────────────────────┐            ┌────────────────────────┐
│  OP-W1-1: Schema       │────────────│  OP-W2-1: Action       │
│  Foundation            │            │  Extraction            │
│  (8h)                  │            │  (12h)                 │
└────────────────────────┘            └────────────────────────┘
         │                                      │
         │                            ┌────────────────────────┐
         │                            │  OP-W2-2: Benchmark    │
         │                            │  Extraction            │
         │                            │  (8h)                  │
         │                            └────────────────────────┘
         ▼                                      │
Week 5-6 (Analysis)                   Week 7-8 (Evolution)
┌────────────────────────┐            ┌────────────────────────┐
│  OP-W3-1: Validation   │◀───────────│  OP-W4-1: Pillar       │
│  Tracker               │            │  Research Log          │
│  (10h)                 │            │  (8h)                  │
└────────────────────────┘            └────────────────────────┘
         │                                      │
┌────────────────────────┐            ┌────────────────────────┐
│  OP-W3-2: Action       │            │  OP-W4-2: Modification │
│  Vector Generator      │            │  Proposals             │
│  (12h)                 │            │  (12h)                 │
└────────────────────────┘            └────────────────────────┘
                                               │
                                      ┌────────────────────────┐
                                      │  OP-W4-3: Stakeholder  │
                                      │  Matrix                │
                                      │  (8h)                  │
                                      └────────────────────────┘
```

#### Task Cards

| ID | Task | Wave | Effort | Dependencies |
|----|------|------|--------|--------------|
| OP-W1-1 | Schema Foundation | 1 | 8h | None |
| OP-W2-1 | Action Extraction | 2 | 12h | OP-W1-1 |
| OP-W2-2 | Benchmark Extraction | 2 | 8h | OP-W1-1 |
| OP-W3-1 | Validation Tracker | 3 | 10h | OP-W2-1, OP-W2-2 |
| OP-W3-2 | Action Vector Generator | 3 | 12h | OP-W2-1 |
| OP-W4-1 | Pillar Research Log | 4 | 8h | OP-W3-1 |
| OP-W4-2 | Modification Proposals | 4 | 12h | OP-W4-1 |
| OP-W4-3 | Stakeholder Matrix | 4 | 8h | OP-W4-2 |

#### Output Files

Each task card produces new output files for the literature review system:

| Task | Primary Output | Description |
|------|----------------|-------------|
| OP-W1-1 | Schema definitions | Base dataclasses and interfaces |
| OP-W2-1 | `action_vectors.json` | Executable implementation plans |
| OP-W2-2 | `requirement_benchmark_matrix.json` | Performance-benchmark linkages |
| OP-W3-1 | `validation_gap_matrix.json` | Design-validation coverage |
| OP-W3-2 | Enhanced `action_vectors.json` | Enriched with vectors |
| OP-W4-1 | `pillar_research_log.json` | Research accumulation log |
| OP-W4-2 | `pillar_proposals.json` | Modification proposals |
| OP-W4-3 | `stakeholder_impact_matrix.json` | Change impact analysis |

#### Detailed Task Card Locations

All task cards are located in `task-cards/`:

- [OPERATIONALIZATION_WAVE_INDEX.md](../task-cards/OPERATIONALIZATION_WAVE_INDEX.md) - Complete index
- [OP_WAVE_1_1_SCHEMA_FOUNDATION.md](../task-cards/OP_WAVE_1_1_SCHEMA_FOUNDATION.md)
- [OP_WAVE_2_1_ACTION_EXTRACTION.md](../task-cards/OP_WAVE_2_1_ACTION_EXTRACTION.md)
- [OP_WAVE_2_2_BENCHMARK_EXTRACTION.md](../task-cards/OP_WAVE_2_2_BENCHMARK_EXTRACTION.md)
- [OP_WAVE_3_1_VALIDATION_TRACKER.md](../task-cards/OP_WAVE_3_1_VALIDATION_TRACKER.md)
- [OP_WAVE_3_2_ACTION_VECTOR_GENERATOR.md](../task-cards/OP_WAVE_3_2_ACTION_VECTOR_GENERATOR.md)
- [OP_WAVE_4_1_PILLAR_RESEARCH_LOG.md](../task-cards/OP_WAVE_4_1_PILLAR_RESEARCH_LOG.md)
- [OP_WAVE_4_2_MODIFICATION_PROPOSALS.md](../task-cards/OP_WAVE_4_2_MODIFICATION_PROPOSALS.md)
- [OP_WAVE_4_3_STAKEHOLDER_MATRIX.md](../task-cards/OP_WAVE_4_3_STAKEHOLDER_MATRIX.md)

---

## Agent Task Cards (Critical Path - Optional)

These cards address core AI agent improvements. They can be implemented at any time.

| Card | Name | Priority | Effort | Status |
|------|------|----------|--------|--------|
| #1 | Fix DRA Prompting for Judge Alignment | 🔴 Critical | 2-3h | 📋 Ready |
| #2 | Refactor Judge to Use Version History | 🔴 Critical | 4-6h | 📋 Ready |
| #3 | Implement Large Document Chunking | 🟡 Important | 4-6h | 📋 Ready |
| #4 | Design Decision - Deep Coverage Database | 🟢 Minor | 3-4h | 📋 Ready |

**Total Agent Cards Effort:** 14-20 hours

---

## Development Priority Order

### Immediate (Next Sprint)

1. **Complete Wave 3** (8-10h)
   - Task #19: Temporal Coherence Analysis

2. **Begin Operationalization Wave 1** (8h)
   - OP-W1-1: Schema Foundation

### Short Term (Next 2-4 Weeks)

3. **Operationalization Wave 2** (20h)
   - OP-W2-1: Action Extraction (12h)
   - OP-W2-2: Benchmark Extraction (8h)

4. **Agent Cards** (14-20h - can be parallel)
   - #1: DRA Prompting Fix
   - #2: Judge Version History

### Medium Term (4-8 Weeks)

5. **Operationalization Wave 3** (22h)
   - OP-W3-1: Validation Tracker (10h)
   - OP-W3-2: Action Vector Generator (12h)

6. **Wave 4: Production Polish** (108-145h)
   - Begin with E2E testing and CI/CD
   - Dashboard as major undertaking

### Long Term (8+ Weeks)

7. **Operationalization Wave 4** (28h)
   - OP-W4-1: Pillar Research Log (8h)
   - OP-W4-2: Modification Proposals (12h)
   - OP-W4-3: Stakeholder Matrix (8h)

8. **Optional Evidence Enhancements**
   - Publication Bias Detection
   - Conflict-of-Interest Analysis

---

## Metrics & Tracking

### Completed Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Unit Tests Passing | >700 | 745+ | ✅ Exceeded |
| Wave 1 Completion | 100% | 100% | ✅ Met |
| Wave 2 Completion | 100% | 100% | ✅ Met |
| Wave 3 Completion | 100% | 86% | 🔄 In Progress |
| Integration Test Coverage | >80% | ~85% | ✅ Exceeded |
| Pipeline Reliability | >95% | >98% | ✅ Exceeded |

### Target Metrics

| Metric | Target | Current | Wave |
|--------|--------|---------|------|
| E2E Test Coverage | 100% critical flows | 0% | Wave 4 |
| Dashboard Operational | Yes | No | Wave 4 |
| CI/CD Pipeline | Automated | Manual | Wave 4 |
| Actionable Outputs | All claims → actions | None | OP Wave |

---

## Risk Assessment

### 🟢 Low Risk

- **Operationalization Wave 1-2**: Clear designs, builds on existing infrastructure
- **Agent Cards**: Isolated changes, low integration risk
- **Temporal Coherence**: Structure validated, algorithm straightforward

### 🟡 Medium Risk

- **Operationalization Wave 3-4**: New output formats may require iteration
- **Web Dashboard**: Large effort, full-stack development
- **E2E Testing**: Complex setup, environment dependencies

### 🔴 High Risk

- **None currently identified** - All high-risk items mitigated

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [MASTER_ARCHITECTURE_BLUEPRINT.md](MASTER_ARCHITECTURE_BLUEPRINT.md) | Current architecture snapshot |
| [RESEARCH_LOOP_INTEGRATION_ASSESSMENT.md](RESEARCH_LOOP_INTEGRATION_ASSESSMENT.md) | OP Wave source assessment |
| [task-cards/OPERATIONALIZATION_WAVE_INDEX.md](../task-cards/OPERATIONALIZATION_WAVE_INDEX.md) | OP Wave task card index |
| [task-cards/INDEX.md](../task-cards/INDEX.md) | All task card index |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | December 19, 2025 | Complete rewrite; added Operationalization Wave (8 cards, 80-100h); consolidated all waves; supersedes CONSOLIDATED_ROADMAP.md |
| 1.3 | November 14, 2025 | (Previous version in CONSOLIDATED_ROADMAP.md) |

---

## Archived Documentation

The following documents are superseded by this roadmap:

- `docs/CONSOLIDATED_ROADMAP.md` - Original roadmap (Version 1.3, November 14, 2025)

These files are retained for historical reference but should not be used for planning.

---

*This is a living document. Update after each wave completion or significant milestone.*
