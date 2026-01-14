# Validation Matrix & Benchmarking Wave - Complete Index

**Created:** December 31, 2025  
**Source:** Third-Party Assessment & Internal Review  
**Total Tasks:** 26 (8 Waves) *(updated: added Wave 0.5, Wave 1.5, and Wave 2.5)*  
**Total Effort:** 214 hours base *(+26h for Wave 0.5, +46h for Wave 1.5 enhanced, +24h for Wave 2.5, +4h for Wave 4 VI-*)*  
**Timeline:** 14-16 weeks

---

## Revision History

| Date | Change | Source |
|------|--------|--------|
| 2025-12-31 | Initial creation | Third-party assessment |
| 2025-12-31 | Added FV-07→10, AV-07; expanded Wave 5 | Third-party review feedback |
| 2025-12-31 | Added Wave 2.5 (OQ-*, RA-*, VI-*); output validation | Third-party output gap analysis |
| 2025-12-31 | Added Wave 0.5 (MT-*, DF-*, MC-*); modularization infrastructure | Third-party modularization assessment |
| 2026-01-10 | Added Wave 1.5 (Paper Sourcing, Annotation); cross-domain validation | Golden dataset enhancement |
| 2026-01-12 | Added VM-W1.5-0 (Ground Truth Design); bi-directional validation | Golden dataset strategy assessment |
| 2026-01-13 | Added VM-W1.5-3 (Gap Scenario Execution); FP-02/FP-03/ITER-01 metrics | Third-party gap closure |
| 2026-01-13 | Decomposed VM-W1.5-2 into 10 sub-tasks (2a-2j); parallel execution | Agent capacity assessment |

---

## Executive Summary

This wave implements a comprehensive validation matrix and benchmarking framework for the Literature Review Automation System. The framework ensures:

1. **Functional Validation** - Core pipeline operations work correctly
2. **Accuracy Validation** - AI decisions meet quality thresholds
3. **Efficiency Validation** - Performance meets cost/time targets
4. **Benchmark Suite** - Reproducible performance measurements
5. **Golden Dataset** - Ground truth for accuracy testing
6. **Cross-Domain Validation** - System works across diverse scientific domains *(added)*
7. **Output Quality Validation** - User-facing deliverables are accurate and complete *(added)*
8. **Bi-Directional Validation** - Tests both finding AND not-finding correctly *(added 2026-01-12)*

## Wave Architecture

```
                    WAVE 0: Infrastructure Foundation
                    ┌─────────────────────────────────────┐
                    │  VM-W0-1: Test Infrastructure Setup │
                    │  VM-W0-2: Golden Dataset Spec       │
                    └───────────────┬─────────────────────┘
                                    │ (Week 1-2)
                                    ▼
                    WAVE 0.5: Modularization Infrastructure
                    ┌─────────────────────────────────────┐
                    │  VM-W0.5-1: Metrics Configuration   │
                    │  VM-W0.5-2: Domain Test Fixtures    │
                    │  VM-W0.5-3: Model Abstraction Layer │
                    └───────────────┬─────────────────────┘
                                    │ (Week 2-3)
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        WAVE 1A: Functional Tests       WAVE 1B: Golden Dataset
┌───────────────────────────────┐ ┌───────────────────────────────┐
│ VM-W1-1: PDF Extraction       │ │ VM-W1-4: Golden Dataset       │
│ VM-W1-2: Claim Identification │ │          Creation             │
│ VM-W1-3: Judge Decisions      │ └───────────────────────────────┘
└───────────────────────────────┘   (Week 4-5)
                    │
                    ▼
        WAVE 1.5: Ground Truth Infrastructure (ENHANCED)
┌───────────────────────────────────────────────────────────┐
│ VM-W1.5-0: Ground Truth Design    (PREREQUISITE)         │
│ VM-W1.5-1: Paper Sourcing         (✅ COMPLETE 2026-01-14)│
│ VM-W1.5-1B: Paper Population      (✅ 150 papers, 120 PDFs)│
│ VM-W1.5-2: Paper Annotation       (Enhanced - Ready)     │
│ VM-W1.5-3: Gap Scenario Execution (NEW - FP/ITER tests)  │
└───────────────────────────────────────────────────────────┘
                    │ (Week 5-6)
                    ▼
              WAVE 2: Accuracy & Efficiency
┌───────────────────────────────────────────────────────────┐
│ VM-W2-1: Accuracy Baseline    │ VM-W2-3: Efficiency Metrics│
│ VM-W2-2: Judge Calibration    │ VM-W2-4: Cost Tracking     │
└───────────────────────────────┴───────────────────────────┘
                    │ (Week 6-7)
                    ▼
        WAVE 2.5: Output Quality Validation
┌───────────────────────────────────────────────────────────┐
│ VM-W2.5-1: Core Output Schema   │ VM-W2.5-3: Evidence     │
│ VM-W2.5-2: Recommendation       │            Enhancement  │
│            Quality              │                         │
└───────────────────────────────┴───────────────────────────┘
                    │ (Week 7-8)
                    ▼
              WAVE 3: Component Benchmarks
┌───────────────────────────────────────────────────────────┐
│ VM-W3-1: Journal Reviewer BM  │ VM-W3-3: DRA Benchmark     │
│ VM-W3-2: Judge Benchmark      │ VM-W3-4: Orchestrator BM   │
└───────────────────────────────┴───────────────────────────┘
                    │ (Week 8-9)
                    ▼
              WAVE 4: E2E & Quality
┌───────────────────────────────────────────────────────────┐
│ VM-W4-1: E2E Scenario Suite   │ VM-W4-2: Quality Benchmarks│
│          + Visualization (VI) │                            │
└───────────────────────────────┴───────────────────────────┘
                    │ (Week 10-11)
                    ▼
              WAVE 5: Integration & CI/CD
┌───────────────────────────────────────────────────────────┐
│ VM-W5-1: CI/CD Integration    │ VM-W5-2: Dashboard/Reports │
└───────────────────────────────┴───────────────────────────┘
```

---

## Validation Matrix ID Mapping

| Task Card ID | Assessment ID(s) | Description |
|--------------|------------------|-------------|
| VM-W0-1 | - | Test infrastructure foundation |
| VM-W0-2 | QB-01→05 (spec) | Golden dataset specification |
| **VM-W0.5-1** | **MT-01, MT-02** | Metrics configuration system |
| **VM-W0.5-2** | **DF-01, DF-02** | Domain test fixtures |
| **VM-W0.5-3** | **MC-01, MC-02, MC-03** | Model abstraction layer |
| VM-W1-1 | FV-01, FV-02 | PDF extraction validation |
| VM-W1-2 | FV-03, AV-01, AV-02 | Claim identification accuracy |
| VM-W1-3 | FV-04, FV-05, FV-06, **FV-10** | Judge decisions + Version sync |
| VM-W1-4 | QB-01→05 (impl) | Golden dataset creation |
| **VM-W1.5-0** | **FP-01, FP-02, FP-03, ITER-01** | **Ground truth design validation** |
| **VM-W1.5-1** | QB-01, QB-02 | Open access paper sourcing (✅ Complete) |
| **VM-W1.5-1B** | QB-01, QB-02 | Paper population (80+ papers) |
| **VM-W1.5-2** | QB-01→05, **FP-01, FP-02, FP-03, ITER-01** | Paper annotation (enhanced) |
| VM-W2-1 | AV-03, AV-05, AV-06, **FV-07** | Accuracy baseline + Gap detection |
| VM-W2-2 | AV-04, AV-08 | Judge calibration analysis |
| VM-W2-3 | EV-01, EV-02, EV-03, EV-07, **FV-08** | Efficiency + Incremental detection |
| VM-W2-4 | EV-04, EV-05, EV-06, **FV-09, AV-07** | Cost tracking + Pre-filter validation |
| **VM-W2.5-1** | **OQ-01, OQ-02** | Core output schema validation |
| **VM-W2.5-2** | **OQ-03, OQ-04, OQ-05, RA-01→05** | Recommendation quality |
| **VM-W2.5-3** | **OQ-06→10** | Evidence enhancement validation |
| VM-W3-1 | BM-01 | Journal Reviewer benchmark |
| VM-W3-2 | BM-02 | Judge benchmark |
| VM-W3-3 | BM-03 | DRA benchmark |
| VM-W3-4 | BM-04, BM-05, BM-06 | Orchestrator & component BM |
| VM-W4-1 | E2E-01→06, **VI-01→04** | E2E scenario suite + Visualization |
| VM-W4-2 | QB-01→05 | Quality benchmark tests |
| VM-W5-1 | - | CI/CD integration |
| VM-W5-2 | - | Dashboard & reporting |

> **Note:** Items in **bold** were added based on third-party assessment feedback:
> - FV-07→10, AV-07: Pipeline gap coverage
> - OQ-01→10: Output Quality validation
> - RA-01→05: Recommendation Accuracy validation
> - VI-01→04: Visualization Integrity validation
> - MT-01→02: Metrics configuration validation
> - DF-01→02: Domain fixture validation
> - MC-01→03: Model comparison benchmarks
> - **FP-01: Extraction False Positive Rate (<5%)** *(added 2026-01-12)*
> - **FP-02: Gap Detection False Positive Rate (0%)** *(added 2026-01-12)*
> - **FP-03: Decoy Paper Contribution Rate (0%)** *(added 2026-01-12)*
> - **ITER-01: Iterative Gap Closing Validation** *(added 2026-01-12)*

---

## Wave 0: Infrastructure Foundation (Week 1-2) - 16 hours

### VM-W0-1: Test Infrastructure Setup
- **File:** `VM_WAVE_0_1_TEST_INFRASTRUCTURE.md`
- **Effort:** 8 hours
- **Priority:** CRITICAL (Blocks all other tasks)
- **Status:** Not Started
- **Dependencies:** None
- **Deliverables:**
  - `tests/validation/` directory structure
  - `tests/benchmarks/` directory structure
  - `ValidationTestCase` base class with fixtures
  - `BenchmarkRunner` utility class
  - pytest configuration for validation markers
  - Baseline hardware/environment capture utility

### VM-W0-2: Golden Dataset Specification
- **File:** `VM_WAVE_0_2_GOLDEN_DATASET_SPEC.md`
- **Effort:** 8 hours
- **Priority:** CRITICAL
- **Status:** Not Started
- **Dependencies:** None (parallel with VM-W0-1)
- **Deliverables:**
  - Golden dataset requirements document
  - Schema for annotated claims (JSON)
  - Schema for expected verdicts (JSON)
  - Annotation guidelines for human reviewers
  - Golden dataset generation script (skeleton)

---

## Wave 0.5: Modularization Infrastructure (Week 2-3) - 26 hours

> **Added in response to third-party Modularization Assessment**
> 
> This wave addresses key modularization gaps that limit the pipeline's flexibility
> and testability across different domains, LLM providers, and threshold configurations.
> Implements infrastructure for domain-agnostic validation and model comparison benchmarks.

### VM-W0.5-1: Metrics Configuration System
- **File:** `VM_WAVE_0.5_1_METRICS_CONFIG.md`
- **Effort:** 6 hours
- **Priority:** HIGH (P1 - Lowest risk, immediate benefit)
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Validation IDs:** MT-01, MT-02
- **Deliverables:**
  - `tests/validation/config/metrics_config.py` - MetricsConfig dataclass
  - `tests/validation/config/metrics.yaml` - Externalized thresholds
  - Profile system (dev, prod, quick, ci)
  - Environment variable overrides
  - `--metrics-profile` CLI flag for pytest

### VM-W0.5-2: Domain Test Fixtures
- **File:** `VM_WAVE_0.5_2_DOMAIN_FIXTURES.md`
- **Effort:** 8 hours
- **Priority:** HIGH (P2 - Builds on existing ResearchConfig)
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Validation IDs:** DF-01, DF-02
- **Deliverables:**
  - `tests/validation/fixtures/domain_fixture.py` - DomainTestFixture class
  - `tests/validation/fixtures/domain_registry.py` - DomainRegistry
  - `golden_dataset.schema.json` - Domain-agnostic schema
  - `--domain` and `--all-domains` CLI flags for pytest
  - Cross-domain validation report generator

### VM-W0.5-3: Model Abstraction Layer
- **File:** `VM_WAVE_0.5_3_MODEL_ABSTRACTION.md`
- **Effort:** 12 hours
- **Priority:** HIGH (P3 - Highest effort, enables model comparison)
- **Status:** Not Started
- **Dependencies:** None (can start in parallel)
- **Validation IDs:** MC-01, MC-02, MC-03
- **Deliverables:**
  - `literature_review/config/model_config.py` - ModelConfig abstraction
  - `literature_review/utils/llm_client.py` - Provider-agnostic LLM client
  - Support for Gemini, OpenAI, Anthropic, local (Ollama)
  - `--model` CLI flag for pipeline_orchestrator.py
  - Model comparison benchmark tests

---

## Wave 1: Core Functional Validation (Week 4-5) - 32 hours

### VM-W1-1: PDF Extraction Validation
- **File:** `VM_WAVE_1_1_PDF_EXTRACTION.md`
- **Effort:** 8 hours
- **Priority:** HIGH
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/validation/test_pdf_extraction.py`
  - Test fixture PDFs (valid, corrupted, scanned)
  - FV-01: Text extraction fidelity test (≥90%)
  - FV-02: Edge case handling tests
  - Metadata extraction validation

### VM-W1-2: Claim Identification Validation
- **File:** `VM_WAVE_1_2_CLAIM_IDENTIFICATION.md`
- **Effort:** 8 hours
- **Priority:** HIGH
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/validation/test_claim_identification.py`
  - FV-03: Pillar mapping accuracy tests
  - AV-01: Claim extraction precision test (≥85%)
  - AV-02: Claim extraction recall test (≥80%)
  - Claim-to-requirement mapping tests

### VM-W1-3: Judge Decision Validation
- **File:** `VM_WAVE_1_3_JUDGE_DECISIONS.md`
- **Effort:** 8 hours
- **Priority:** CRITICAL
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/validation/test_judge_decisions.py`
  - FV-04: Accept decision validation (composite ≥3.0)
  - FV-05: Reject decision validation
  - FV-06: DRA resubmission flow test
  - Judge score threshold boundary tests

### VM-W1-4: Golden Dataset Creation
- **File:** `VM_WAVE_1_4_GOLDEN_DATASET.md`
- **Effort:** 8 hours
- **Priority:** HIGH
- **Status:** Not Started
- **Dependencies:** VM-W0-2
- **Deliverables:**
  - 50 human-annotated claims (QB-01)
  - 100 claims with known pillar mappings (QB-02)
  - 30 weak-evidence claims for false-positive testing (QB-04)
  - 10 gaps with known solutions for recommendations (QB-05)
  - Golden dataset loader utility

---

## Wave 1.5: Ground Truth Infrastructure (Week 5-6) - 40 hours *(Enhanced 2026-01-12)*

> **Enhanced with Bi-Directional Validation**
> 
> This wave creates a comprehensive ground truth dataset using a hybrid approach:
> - **Exhaustive annotation** for 5-10 anchor papers (true ground truth)
> - **Standard annotation** for 70+ additional papers (volume coverage)
> - **Controlled gap scenarios** for iterative validation
> - **Bi-directional validation** testing both finding AND not-finding correctly

### VM-W1.5-0: Ground Truth Design Validation *(NEW - PREREQUISITE)*
- **File:** `VM_WAVE_1.5_0_GROUND_TRUTH_DESIGN.md`
- **Effort:** 12 hours
- **Priority:** CRITICAL (Prerequisite for VM-W1.5-2)
- **Status:** Not Started
- **Dependencies:** VM-W1-4
- **Validation IDs:** FP-01, GAP-NEG, ITER-01 (enables all bi-directional validation)
- **Deliverables:**
  - Anchor paper selection criteria document
  - Exhaustive annotation protocol with two-annotator reconciliation
  - Gap scenario design template with Pass 1/Pass 2 structure
  - Extractability classification scheme (HIGH/MEDIUM/LOW/IRRELEVANT)
  - Pilot annotation of 3-5 anchor papers
  - Inter-rater agreement validation (target: κ ≥ 0.7)
  - Anchor paper and gap scenario schema extensions

### VM-W1.5-1: Open Access Paper Sourcing (Infrastructure)
- **File:** `VM_WAVE_1.5_1_PAPER_SOURCING.md`
- **Effort:** 4 hours *(reduced: infrastructure only)*
- **Priority:** HIGH
- **Status:** ✅ COMPLETE (2026-01-14)
- **Dependencies:** VM-W1-4
- **Validation IDs:** QB-01, QB-02 (data quality expansion)
- **Deliverables:**
  - ✅ Enhanced `source_papers.py` CLI (status, add, validate, report, download)
  - ✅ Paper registry schema (`paper_registry.json`) - 150 papers
  - ✅ Domain sourcing guides (SOURCING.md per domain)
  - ✅ PDF download infrastructure - 120 PDFs (314 MB)
  - ✅ Source verification - All arXiv IDs verified
  - ✅ 15 papers per domain (exceeds 10 target)

### VM-W1.5-1B: Paper Population (80+ Papers)
- **File:** `VM_WAVE_1.5_1B_PAPER_POPULATION.md`
- **Effort:** 8 hours
- **Priority:** HIGH
- **Status:** ✅ COMPLETE (2026-01-14)
- **Dependencies:** VM-W1.5-1
- **Validation IDs:** QB-01, QB-02 (data population)
- **Deliverables:**
  - ✅ 150 papers registered (exceeds 80 target)
  - ✅ 120 PDFs downloaded (15 per domain)
  - ✅ All papers with open access (arXiv sourced)
  - ✅ Registry validation passes
  - ✅ Tracking dashboard updated

### VM-W1.5-2: Paper Annotation for Golden Dataset *(Decomposed)*
- **File:** `VM_WAVE_1.5_2_PAPER_ANNOTATION.md`
- **Effort:** 28 hours total *(decomposed into 10 sub-tasks)*
- **Priority:** HIGH
- **Status:** Decomposed (2026-01-13)
- **Dependencies:** VM-W1-4, **VM-W1.5-0**, VM-W1.5-1, VM-W1.5-1B
- **Validation IDs:** QB-01→05, **FP-01, FP-02, FP-03, ITER-01** (real data + negative cases)
- **Sub-Tasks:**

| Sub-Task | Name | Effort | Papers | Parallelizable |
|----------|------|--------|--------|----------------|
| VM-W1.5-2a | Anchor Neuromorphic | 3h | 2-3 | No (first) |
| VM-W1.5-2b | Anchor Cross-Domain | 4h | 3-5 | No (after 2a) |
| VM-W1.5-2c | Standard Neuromorphic | 3h | 8 | Yes |
| VM-W1.5-2d | Standard Quantum | 3h | 10 | Yes |
| VM-W1.5-2e | Standard Microbiology | 3h | 10 | Yes |
| VM-W1.5-2f | Standard Fusion/Nano | 4h | 20 | Yes |
| VM-W1.5-2g | Standard Climate/Materials | 4h | 20 | Yes |
| VM-W1.5-2h | Standard Biomedical | 3h | 10 | Yes |
| VM-W1.5-2i | Gap Scenario Design | 3h | 5+ decoys | No (after 2c-2h) |
| VM-W1.5-2j | Merge & Validation | 2h | - | No (final) |

- **Execution Strategy:**
  1. Sequential: 2a → 2b (anchor establishment)
  2. Parallel: 2c-2h (standard annotation)
  3. Sequential: 2i → 2j (scenarios and merge)
- **Deliverables:**
  - 75-150 anchor claims (exhaustive annotation)
  - 350-560 standard claims (8 domains)
  - 50+ non-extraction items (false positive tests)
  - 3+ gap scenarios with Pass 1/Pass 2 states
  - 5+ decoy paper annotations
  - 160+ known gaps
  - Merged golden dataset v2.0

### VM-W1.5-3: Gap Scenario Execution Framework *(NEW)*
- **File:** `VM_WAVE_1.5_3_GAP_SCENARIO_EXECUTION.md`
- **Effort:** 6 hours
- **Priority:** HIGH
- **Status:** Not Started
- **Dependencies:** VM-W1.5-0, VM-W1.5-2
- **Validation IDs:** **FP-02, FP-03, GAP-NEG, ITER-01** (gap scenario execution)
- **Deliverables:**
  - `tests/validation/gap_scenarios/executor.py` - GapScenarioExecutor class
  - `tests/validation/gap_scenarios/state_manager.py` - DatabaseStateManager
  - `tests/validation/gap_scenarios/test_scenarios.py` - pytest test suite
  - 3+ gap scenario JSON definitions (GAP-001, GAP-002, GAP-003)
  - FP-02 metric: Gap detection false positive rate (0%)
  - FP-03 metric: Decoy paper contribution rate (0%)
  - GAP-NEG metric: Non-gap accuracy (100%)
  - ITER-01 metric: Iterative gap closure accuracy (≥95%)

---

## Wave 2: Accuracy & Efficiency (Week 6-7) - 32 hours

### VM-W2-1: Accuracy Baseline Tests
- **File:** `VM_WAVE_2_1_ACCURACY_BASELINE.md`
- **Effort:** 8 hours
- **Priority:** HIGH
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W1-3, VM-W1-4
- **Deliverables:**
  - `tests/validation/accuracy/test_accuracy_baseline.py`
  - AV-03: Judge accuracy test (≥90%)
  - AV-05: DRA recovery rate test (≥40%)
  - AV-06: Gap false negative rate test (<5%)
  - Accuracy regression baseline capture
  - Confidence interval calculations (Wilson score)

### VM-W2-2: Judge Calibration Analysis
- **File:** `VM_WAVE_2_2_JUDGE_CALIBRATION.md`
- **Effort:** 8 hours
- **Priority:** MEDIUM
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W1-4
- **Deliverables:**
  - `tests/validation/accuracy/test_judge_calibration.py`
  - AV-04: Brier score calculation (target <0.15)
  - AV-08: Human correlation test (r ≥0.8)
  - Calibration curve generator
  - Score distribution analysis
  - Brier score decomposition (reliability, resolution, uncertainty)

### VM-W2-3: Efficiency Metrics Tests
- **File:** `VM_WAVE_2_3_EFFICIENCY_METRICS.md`
- **Effort:** 8 hours
- **Priority:** HIGH
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/validation/efficiency/test_efficiency_metrics.py`
  - EV-01: Pipeline full run time test (<2h for 100 papers)
  - EV-02: Incremental mode speedup test (60-80% faster)
  - EV-03: Cache hit rate test (≥70%)
  - EV-07: Checkpoint recovery time test (<30s)
  - Performance regression detector

### VM-W2-4: Cost Tracking Validation
- **File:** `VM_WAVE_2_4_COST_TRACKING.md`
- **Effort:** 8 hours
- **Priority:** MEDIUM
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/validation/efficiency/test_cost_tracking.py`
  - EV-04: API cost per paper test (<$0.50)
  - EV-05: Pre-filter reduction test (30-50%)
  - EV-06: Rate limit compliance test (0 violations)
  - Cost estimation accuracy test
  - API cost calculator with model pricing

---

## Wave 2.5: Output Quality Validation (Week 6-7) - 24 hours

> **Added in response to third-party Output Gap Analysis**
> 
> This wave addresses the finding that 75% of user-facing outputs were not validated
> in the original matrix. These tests validate the actual deliverables that users
> consume, not just the pipeline mechanics that produce them.

### VM-W2.5-1: Core Output Schema Validation
- **File:** `VM_WAVE_2.5_1_OUTPUT_SCHEMA.md`
- **Effort:** 6 hours
- **Priority:** HIGH
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W2-1
- **Deliverables:**
  - `tests/validation/outputs/test_output_schemas.py`
  - OQ-01: gap_analysis_report.json schema validation
  - OQ-02: executive_summary.md completeness test
  - JSON schema definitions for all output files
  - Markdown section presence validators

### VM-W2.5-2: Recommendation Quality Validation
- **File:** `VM_WAVE_2.5_2_RECOMMENDATION_QUALITY.md`
- **Effort:** 8 hours
- **Priority:** HIGH
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W2-1, VM-W1-4
- **Deliverables:**
  - `tests/validation/outputs/test_recommendation_quality.py`
  - OQ-03: suggested_searches.json schema validation
  - OQ-04: suggested_searches.md human-readable format test
  - OQ-05: optimized_search_plan.json strategy coherence test
  - RA-01: Search suggestion relevance (golden dataset match)
  - RA-02: Priority ranking accuracy (human-validated order)
  - RA-03: Gap-to-recommendation traceability
  - RA-04: Actionability score (parseable by downstream tools)
  - RA-05: Recommendation deduplication quality

### VM-W2.5-3: Evidence Enhancement Validation
- **File:** `VM_WAVE_2.5_3_EVIDENCE_ENHANCEMENT.md`
- **Effort:** 6 hours
- **Priority:** MEDIUM
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W2-1
- **Deliverables:**
  - `tests/validation/outputs/test_evidence_outputs.py`
  - OQ-06: proof_chain.json completeness (all approved claims linked)
  - OQ-07: sufficiency_matrix.json coverage (all pillars represented)
  - OQ-08: triangulation.json cross-validation accuracy
  - OQ-09: evidence_decay.json temporal weighting correctness
  - OQ-10: Output file consistency (no orphaned references)
  - Evidence chain integrity checker

---

## Wave 3: Component Benchmarks (Week 10-11) - 24 hours

### VM-W3-1: Journal Reviewer Benchmark
- **File:** `VM_WAVE_3_1_JOURNAL_REVIEWER_BM.md`
- **Effort:** 6 hours
- **Priority:** MEDIUM
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/benchmarks/component/test_journal_reviewer_benchmark.py`
  - BM-01: Single paper analysis (<45s for 20-page PDF)
  - Throughput benchmark (papers/hour)
  - Memory usage profiling (<2GB)
  - Scaling efficiency tests (10→50 papers)

### VM-W3-2: Judge Benchmark
- **File:** `VM_WAVE_3_2_JUDGE_BENCHMARK.md`
- **Effort:** 6 hours
- **Priority:** MEDIUM
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/benchmarks/component/test_judge_benchmark.py`
  - BM-02: Batch claim evaluation (≥20 claims/min)
  - Single claim latency (<3s)
  - Consensus mode overhead (<2x single judge)
  - Score calculation performance (<100ms)
  - Stress testing (100 claims sustained)

### VM-W3-3: DRA Benchmark
- **File:** `VM_WAVE_3_3_DRA_BENCHMARK.md`
- **Effort:** 6 hours
- **Priority:** MEDIUM
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/benchmarks/component/test_dra_benchmark.py`
  - BM-03: Deep analysis per claim (<30s)
  - Document re-read efficiency (<50% of first pass)
  - Batch processing performance (≥2 claims/min)
  - Recovery rate stability (<5% variance)

### VM-W3-4: Orchestrator & Support Benchmarks
- **File:** `VM_WAVE_3_4_ORCHESTRATOR_SUPPORT_BM.md`
- **Effort:** 6 hours
- **Priority:** MEDIUM
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/benchmarks/component/test_orchestrator_benchmark.py`
  - BM-04: Gap report generation (<5min for 500 papers)
  - BM-04a: Scaling analysis (linear or sub-linear)
  - BM-05: Pre-filter scoring (≥10 papers/sec)
  - BM-05a: Batch pre-filter (≥15 papers/sec)
  - BM-06: DB write (≥100 records/sec)
  - BM-06a: DB read (≥200 records/sec)

---

## Wave 4: E2E & Quality + Visualization (Week 11-12) - 24 hours *(expanded for VI-*)*

### VM-W4-1: E2E Scenario Suite + Visualization Integrity
- **File:** `VM_WAVE_4_1_E2E_VISUALIZATION.md`
- **Effort:** 14 hours *(expanded from 12h to include VI-*)*
- **Priority:** HIGH
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W2-1, VM-W2-3, VM-W2.5-1, VM-W3-1, VM-W3-2, VM-W3-3, VM-W3-4
- **Deliverables:**
  - `tests/e2e/test_validation_scenarios.py`
  - E2E-01: Small fresh run (10 papers, <15min, <$5)
  - E2E-02: Medium fresh run (50 papers, <1h, <$25)
  - E2E-03: Large fresh run (200 papers, <4h, <$100)
  - E2E-04: Incremental run (+5 papers, <10min)
  - E2E-05: Recovery test (checkpoint restore, <30s)
  - E2E-06: Multi-domain test (no cross-contamination)
  - `tests/validation/outputs/test_visualization_integrity.py`
  - VI-01: INCR_W2_3_UI_PREVIEW.html renders correctly
  - VI-02: genealogy_test.html interactive elements work
  - VI-03: Dashboard data binding validation
  - VI-04: Cross-browser compatibility (Chrome, Firefox)

### VM-W4-2: Quality Benchmark Tests
- **File:** `VM_WAVE_4_2_QUALITY_BENCHMARKS.md`
- **Effort:** 10 hours *(expanded from 8h)*
- **Priority:** HIGH
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W1-4, VM-W2-1, VM-W2.5-2
- **Deliverables:**
  - `tests/benchmarks/quality/test_quality_benchmarks.py`
  - QB-01: Evidence strength scoring (MAE <0.5)
  - QB-02: Pillar mapping accuracy (≥95%)
  - QB-03: Gap detection completeness (100%)
  - QB-04: False approval rate (<10%)
  - QB-05: Recommendation relevance (≥4/5)
  - Per-pillar and per-category breakdowns
  - Golden dataset integration

---

## Wave 5: Integration & Reporting (Week 12-14) - 16 hours *(expanded per review feedback)*

### VM-W5-1: CI/CD Integration
- **File:** `VM_WAVE_5_1_CICD_INTEGRATION.md`
- **Effort:** 8 hours *(expanded from 6h)*
- **Priority:** MEDIUM
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W4-1, VM-W4-2
- **Deliverables:**
  - `.github/workflows/validation-matrix.yml`
  - `.github/workflows/pr-validation.yml`
  - Validation gate configuration (required for PR merge)
  - Benchmark regression detection (15% threshold)
  - PR validation checks with matrix builds (Python 3.10-3.12)
  - `scripts/ci/check_benchmark_regression.py`
  - Artifact preservation for benchmark history (90 days)
  - Baseline update on main branch

### VM-W5-2: Dashboard & Reporting
- **File:** `VM_WAVE_5_2_DASHBOARD_REPORTING.md`
- **Effort:** 8 hours *(expanded from 6h)*
- **Priority:** MEDIUM *(upgraded from LOW)*
- **Status:** ✅ Task Card Created
- **Dependencies:** VM-W5-1
- **Deliverables:**
  - `scripts/dashboard/generate_validation_data.py`
  - `webdashboard/validation-matrix.html`
  - Validation matrix dashboard panel (health score, pass rate, categories)
  - Benchmark trend visualization (30-day window)
  - Automated validation report generation
  - `scripts/notifications/slack_notify.py`
  - Historical trend analysis
  - Regression alert thresholds with notifications

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Golden dataset annotation quality | Medium | High | Clear guidelines, multiple reviewers |
| Benchmark variance across hardware | High | Medium | Capture hardware profile, use ratios |
| API cost during testing | Medium | Medium | Mock API calls where possible |
| Calibration data insufficient | Low | High | Iteratively expand golden dataset |
| CI/CD timeout on large E2E | Medium | Low | Separate nightly workflow |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Coverage Increase | +15% | Coverage reports |
| Golden Dataset Size | 200+ claims | Dataset file |
| Benchmark Reproducibility | <5% variance | Multiple runs |
| Accuracy Baseline Established | All AV-* pass | Test results |
| E2E Scenario Coverage | 6/6 scenarios | Test results |
| Output Schema Compliance | All OQ-* pass | Schema validation |
| Recommendation Quality | RA-01 ≥80% | Golden dataset match |
| Visualization Integrity | All VI-* pass | Browser tests |

---

## Quick Reference: pytest Markers

```python
# New markers for validation framework (add to pytest.ini)
markers =
    validation: Validation matrix tests
    benchmark: Benchmark tests (may take longer)
    golden: Tests requiring golden dataset
    accuracy: Accuracy validation tests
    efficiency: Efficiency validation tests
    quality: Quality benchmark tests
    requires_golden_dataset: Tests that require golden dataset to be present
    incremental: Tests for incremental mode functionality  # Added per review
    prefilter: Tests for pre-filter/relevance scoring      # Added per review
    calibration: Tests for Judge score calibration
    cost: Tests for API cost tracking
    output_quality: Tests for output file validation        # Added Wave 2.5
    recommendation: Tests for recommendation accuracy       # Added Wave 2.5
    visualization: Tests for HTML visualization integrity   # Added Wave 2.5
```

---

## Related Documentation

- [VALIDATION_MATRIX_ASSESSMENT.md](../docs/VALIDATION_MATRIX_ASSESSMENT.md) - Third-party assessment
- [pytest.ini](../pytest.ini) - Test configuration
- [tests/fixtures/test_data_generator.py](../tests/fixtures/test_data_generator.py) - Synthetic data generation
- [OPERATIONALIZATION_WAVE_INDEX.md](./OPERATIONALIZATION_WAVE_INDEX.md) - Related operationalization tasks
