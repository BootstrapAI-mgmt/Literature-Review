# Phase 4: Golden Dataset — Task Cards

## TC-LR13: Complete Manual Paper Annotations

**Priority:** P0
**Status:** in-progress
**Dependencies:** TC-LR11, TC-LR12

**Problem:**
The golden dataset validation framework exists (PR #140-#142) and batch 1 annotations are done (5 papers), but the dataset needs 20+ annotated papers across multiple domains to produce statistically meaningful accuracy benchmarks. Without sufficient ground truth, pipeline accuracy claims are unverifiable.

**Deliverables:**
- Manually annotated claim JSONs for 20+ papers following the golden dataset JSON schema
- Annotations covering at least 2 research domains (neuromorphic-computing + one other)
- Each annotation includes verified claims with page references and pillar mappings

**Files to create/modify:**
- `tests/golden_dataset/annotations/*.json` (new annotation files)
- `tests/golden_dataset/paper_registry.json` (update with annotated paper status)

**Acceptance Criteria:**
1. At least 20 paper annotation JSON files exist in `tests/golden_dataset/annotations/`
2. Each annotation file conforms to the golden dataset JSON schema defined in `tests/golden_dataset/`
3. Annotations span at least 2 distinct research domains
4. Each claim annotation includes `page_number`, `claim_text`, and `pillar_mapping` fields

**Notes:**
Batch 1 (5 papers) was completed in commit e6314ce7. The annotation checklist and update script from commit fbe8fadc should be used for consistency.

---

## TC-LR14: Run Full Accuracy Benchmark Against Golden Dataset

**Priority:** P1
**Status:** not-started
**Dependencies:** TC-LR13

**Problem:**
The pipeline's claim extraction and gap analysis accuracy has never been measured against verified ground truth. Without a benchmark, there is no objective way to detect accuracy regressions when the pipeline or LLM models change.

**Deliverables:**
- Benchmark test suite that compares pipeline output to golden dataset annotations
- Precision, recall, and F1 metrics for claim extraction and gap identification
- Benchmark report written to `reports/golden_dataset_benchmark.md`

**Files to create/modify:**
- `tests/golden_dataset/test_benchmark.py` (new benchmark test)
- `reports/golden_dataset_benchmark.md` (new report output)
- `scripts/run_benchmark.py` (new benchmark runner script)

**Acceptance Criteria:**
1. `pytest tests/golden_dataset/test_benchmark.py -q` runs without errors
2. Benchmark report contains precision, recall, and F1 for claim extraction
3. Benchmark report contains precision, recall, and F1 for gap identification
4. Report file is written to `reports/golden_dataset_benchmark.md`
