# Validation Matrix & Benchmarking Wave - Complete Index

**Created:** December 31, 2025  
**Source:** Third-Party Assessment & Internal Review  
**Total Tasks:** 16 (5 Waves)  
**Total Effort:** 120-150 hours  
**Timeline:** 8-10 weeks

---

## Executive Summary

This wave implements a comprehensive validation matrix and benchmarking framework for the Literature Review Automation System. The framework ensures:

1. **Functional Validation** - Core pipeline operations work correctly
2. **Accuracy Validation** - AI decisions meet quality thresholds
3. **Efficiency Validation** - Performance meets cost/time targets
4. **Benchmark Suite** - Reproducible performance measurements
5. **Golden Dataset** - Ground truth for accuracy testing

## Wave Architecture

```
                    WAVE 0: Infrastructure Foundation
                    ┌─────────────────────────────────────┐
                    │  VM-W0-1: Test Infrastructure Setup │
                    │  VM-W0-2: Golden Dataset Spec       │
                    └───────────────┬─────────────────────┘
                                    │ (Week 1-2)
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        WAVE 1A: Functional Tests       WAVE 1B: Golden Dataset
┌───────────────────────────────┐ ┌───────────────────────────────┐
│ VM-W1-1: PDF Extraction       │ │ VM-W1-4: Golden Dataset       │
│ VM-W1-2: Claim Identification │ │          Creation             │
│ VM-W1-3: Judge Decisions      │ └───────────────────────────────┘
└───────────────────────────────┘   (Week 3-4)
                    │
                    ▼
              WAVE 2: Accuracy & Efficiency
┌───────────────────────────────────────────────────────────┐
│ VM-W2-1: Accuracy Baseline    │ VM-W2-3: Efficiency Metrics│
│ VM-W2-2: Judge Calibration    │ VM-W2-4: Cost Tracking     │
└───────────────────────────────┴───────────────────────────┘
                    │ (Week 5-6)
                    ▼
              WAVE 3: Component Benchmarks
┌───────────────────────────────────────────────────────────┐
│ VM-W3-1: Journal Reviewer BM  │ VM-W3-3: DRA Benchmark     │
│ VM-W3-2: Judge Benchmark      │ VM-W3-4: Orchestrator BM   │
└───────────────────────────────┴───────────────────────────┘
                    │ (Week 7-8)
                    ▼
              WAVE 4: E2E & Quality
┌───────────────────────────────────────────────────────────┐
│ VM-W4-1: E2E Scenario Suite   │ VM-W4-2: Quality Benchmarks│
└───────────────────────────────┴───────────────────────────┘
                    │ (Week 9-10)
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
| VM-W1-1 | FV-01, FV-02 | PDF extraction validation |
| VM-W1-2 | FV-03, AV-01, AV-02 | Claim identification accuracy |
| VM-W1-3 | FV-04, FV-05, FV-06 | Judge decision validation |
| VM-W1-4 | QB-01→05 (impl) | Golden dataset creation |
| VM-W2-1 | AV-03, AV-05, AV-06 | Accuracy baseline tests |
| VM-W2-2 | AV-04, AV-08 | Judge calibration analysis |
| VM-W2-3 | EV-01, EV-02, EV-03 | Efficiency metrics tests |
| VM-W2-4 | EV-04, EV-05, EV-06 | Cost tracking validation |
| VM-W3-1 | BM-01 | Journal Reviewer benchmark |
| VM-W3-2 | BM-02 | Judge benchmark |
| VM-W3-3 | BM-03 | DRA benchmark |
| VM-W3-4 | BM-04, BM-05, BM-06 | Orchestrator & component BM |
| VM-W4-1 | E2E-01→06 | E2E scenario suite |
| VM-W4-2 | QB-01→05 | Quality benchmark tests |
| VM-W5-1 | - | CI/CD integration |
| VM-W5-2 | - | Dashboard & reporting |

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

## Wave 1: Core Functional Validation (Week 3-4) - 32 hours

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

## Wave 2: Accuracy & Efficiency (Week 5-6) - 32 hours

### VM-W2-1: Accuracy Baseline Tests
- **File:** `VM_WAVE_2_1_ACCURACY_BASELINE.md`
- **Effort:** 8 hours
- **Priority:** HIGH
- **Status:** Not Started
- **Dependencies:** VM-W1-3, VM-W1-4
- **Deliverables:**
  - `tests/validation/test_accuracy_baseline.py`
  - AV-03: Judge accuracy test (≥90%)
  - AV-05: DRA recovery rate test (≥40%)
  - AV-06: Gap false negative rate test (<5%)
  - Accuracy regression baseline capture

### VM-W2-2: Judge Calibration Analysis
- **File:** `VM_WAVE_2_2_JUDGE_CALIBRATION.md`
- **Effort:** 8 hours
- **Priority:** MEDIUM
- **Status:** Not Started
- **Dependencies:** VM-W1-4
- **Deliverables:**
  - `tests/validation/test_judge_calibration.py`
  - AV-04: Brier score calculation (target <0.15)
  - AV-08: Human correlation test (r ≥0.8)
  - Calibration curve generator
  - Score distribution analysis

### VM-W2-3: Efficiency Metrics Tests
- **File:** `VM_WAVE_2_3_EFFICIENCY_METRICS.md`
- **Effort:** 8 hours
- **Priority:** HIGH
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/validation/test_efficiency_metrics.py`
  - EV-01: Pipeline full run time test (<2h for 100 papers)
  - EV-02: Incremental mode speedup test (60-80% faster)
  - EV-03: Cache hit rate test (≥70%)
  - EV-07: Checkpoint recovery time test (<30s)

### VM-W2-4: Cost Tracking Validation
- **File:** `VM_WAVE_2_4_COST_TRACKING.md`
- **Effort:** 8 hours
- **Priority:** MEDIUM
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/validation/test_cost_tracking.py`
  - EV-04: API cost per paper test (<$0.50)
  - EV-05: Pre-filter reduction test (30-50%)
  - EV-06: Rate limit compliance test (0 violations)
  - Cost estimation accuracy test

---

## Wave 3: Component Benchmarks (Week 7-8) - 24 hours

### VM-W3-1: Journal Reviewer Benchmark
- **File:** `VM_WAVE_3_1_JOURNAL_REVIEWER_BM.md`
- **Effort:** 6 hours
- **Priority:** MEDIUM
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/benchmarks/test_journal_reviewer_benchmark.py`
  - BM-01: Single paper analysis (<45s for 20-page PDF)
  - Throughput benchmark (papers/hour)
  - Memory usage profiling

### VM-W3-2: Judge Benchmark
- **File:** `VM_WAVE_3_2_JUDGE_BENCHMARK.md`
- **Effort:** 6 hours
- **Priority:** MEDIUM
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/benchmarks/test_judge_benchmark.py`
  - BM-02: Batch claim evaluation (≥20 claims/min)
  - Consensus mode overhead measurement
  - Score calculation performance

### VM-W3-3: DRA Benchmark
- **File:** `VM_WAVE_3_3_DRA_BENCHMARK.md`
- **Effort:** 6 hours
- **Priority:** MEDIUM
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/benchmarks/test_dra_benchmark.py`
  - BM-03: Deep analysis per claim (<30s)
  - Document re-read efficiency
  - Batch processing performance

### VM-W3-4: Orchestrator & Support Benchmarks
- **File:** `VM_WAVE_3_4_ORCHESTRATOR_BENCHMARK.md`
- **Effort:** 6 hours
- **Priority:** MEDIUM
- **Status:** Not Started
- **Dependencies:** VM-W0-1
- **Deliverables:**
  - `tests/benchmarks/test_orchestrator_benchmark.py`
  - BM-04: Gap report generation (<5min for 500 papers)
  - BM-05: Pre-filter scoring (≥10 papers/sec)
  - BM-06: DB sync (≥100 records/sec)

---

## Wave 4: E2E & Quality (Week 9-10) - 20 hours

### VM-W4-1: E2E Scenario Suite
- **File:** `VM_WAVE_4_1_E2E_SCENARIOS.md`
- **Effort:** 12 hours
- **Priority:** HIGH
- **Status:** Not Started
- **Dependencies:** VM-W2-1, VM-W2-3
- **Deliverables:**
  - `tests/e2e/test_validation_scenarios.py`
  - E2E-01: Small fresh run (10 papers, <15min, <$5)
  - E2E-02: Medium fresh run (50 papers, <1h, <$25)
  - E2E-03: Large fresh run (200 papers, <4h, <$100)
  - E2E-04: Incremental run (+5 papers, <10min)
  - E2E-05: Recovery test (checkpoint restore)
  - E2E-06: Multi-domain test (no cross-contamination)

### VM-W4-2: Quality Benchmark Tests
- **File:** `VM_WAVE_4_2_QUALITY_BENCHMARKS.md`
- **Effort:** 8 hours
- **Priority:** HIGH
- **Status:** Not Started
- **Dependencies:** VM-W1-4, VM-W2-1
- **Deliverables:**
  - `tests/benchmarks/test_quality_benchmarks.py`
  - QB-01: Evidence strength scoring (MAE <0.5)
  - QB-02: Pillar mapping accuracy (≥95%)
  - QB-03: Gap detection completeness (100%)
  - QB-04: False approval rate (<10%)
  - QB-05: Recommendation relevance (≥4/5)

---

## Wave 5: Integration & Reporting (Week 10+) - 12 hours

### VM-W5-1: CI/CD Integration
- **File:** `VM_WAVE_5_1_CICD_INTEGRATION.md`
- **Effort:** 6 hours
- **Priority:** MEDIUM
- **Status:** Not Started
- **Dependencies:** VM-W4-1, VM-W4-2
- **Deliverables:**
  - `.github/workflows/validation-matrix.yml`
  - Validation gate configuration
  - Benchmark regression detection
  - PR validation checks

### VM-W5-2: Dashboard & Reporting
- **File:** `VM_WAVE_5_2_DASHBOARD_REPORTING.md`
- **Effort:** 6 hours
- **Priority:** LOW
- **Status:** Not Started
- **Dependencies:** VM-W5-1
- **Deliverables:**
  - Validation matrix dashboard panel
  - Benchmark trend visualization
  - Automated validation report generation
  - Slack/notification integration

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
```

---

## Related Documentation

- [VALIDATION_MATRIX_ASSESSMENT.md](../docs/VALIDATION_MATRIX_ASSESSMENT.md) - Third-party assessment
- [pytest.ini](../pytest.ini) - Test configuration
- [tests/fixtures/test_data_generator.py](../tests/fixtures/test_data_generator.py) - Synthetic data generation
- [OPERATIONALIZATION_WAVE_INDEX.md](./OPERATIONALIZATION_WAVE_INDEX.md) - Related operationalization tasks
