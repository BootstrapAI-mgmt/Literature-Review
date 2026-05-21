# Roadmap — Literature Review Automation System

## Strategic Direction

The Literature Review system automates systematic literature reviews end-to-end: from PDF ingestion through claim evaluation, gap analysis, and actionable recommendations. Development follows a phased approach that first established the core pipeline and testing infrastructure, then added evidence quality features (scoring, consensus, triangulation), then advanced automation (cost optimization, incremental processing, dashboard), and is now focused on validation accuracy through a golden dataset benchmark. Future phases target production hardening and multi-domain deployment.

## Phases

### Phase 1: Core Pipeline + Infrastructure

**Goal:** Establish the 5-stage automated pipeline with package structure and test infrastructure.

**Milestone:** `pipeline_orchestrator.py` produces a complete gap analysis report from raw PDFs in a single command, with checkpoint/resume capability.

**Verification:**
1. Run `python pipeline_orchestrator.py --batch-mode --resume` and confirm it completes all 5 stages (journal-reviewer, judge, DRA, sync, orchestrator).
2. Verify `gap_analysis_output/gap_analysis_report.json` exists and contains gap entries.
3. Run `pytest tests/unit/ -q` and confirm 745+ tests pass.

**Status:** complete

**Completed:** 2025-11-13

**Evidence:** PR #6 (task card #13 pipeline orchestrator), PR #7 (task card #5 test infrastructure), PR #1 (judge version history refactor), PR #2 (DRA prompting fix), PR #3 (large document chunking), PR #10 (checkpoint/resume + retry sub-tasks), commit cd05939d (checkpoint/resume), commit d6309cab (retry logic)

---

### Phase 2: Evidence Quality Framework

**Goal:** Add multi-dimensional evidence scoring, claim provenance tracking, and consensus judgment to the claim evaluation pipeline.

**Milestone:** `Judge.py` produces consensus verdicts from 3 independent judges with provenance-tracked scores written to `review_version_history.json`.

**Verification:**
1. Run `python Judge.py --batch-mode` on a set of papers and confirm `review_version_history.json` contains `consensus_judgment` entries with 3 judge scores per claim.
2. Verify each claim entry includes `provenance` metadata (source paper, page, extraction method).
3. Run `pytest tests/integration/ -q` and confirm integration tests for journal-to-judge flow, appeal flow, and CSV sync pass.

**Status:** complete

**Completed:** 2025-11-14

**Evidence:** PR #14 (multi-dimensional scoring + provenance), PR #16 (INT-001 journal-to-judge), PR #17 (INT-003 CSV sync), PR #18 (INT-002 appeal flow + consensus), PR #20 (inter-rater reliability)

---

### Phase 3: Advanced Automation

**Goal:** Add parallel processing, API quota management, ROI-based search optimization, and the web dashboard.

**Milestone:** `pipeline_orchestrator.py` serves a FastAPI dashboard at `http://localhost:8000` that accepts PDF uploads, runs pipeline jobs, and streams real-time progress via WebSocket.

**Verification:**
1. Run `./run_dashboard.sh` and navigate to `http://localhost:8000`.
2. Upload a PDF via the `/api/uploads` endpoint and confirm a job starts.
3. Connect to `/ws/jobs` WebSocket and confirm real-time progress events arrive.
4. Run `pytest tests/integration/ tests/e2e/ -q` and confirm orchestrator integration and E2E tests pass.

**Status:** complete

**Completed:** 2025-11-14

**Evidence:** PR #19 (parallel processing, smart retry, API quota management), PR #21 (orchestrator integration tests), commit ac80048f (pipeline accuracy improvements), commit 3568abef (database filename + encoding fixes)

---

### Phase 4: Validation & Golden Dataset

**Goal:** Build a golden dataset benchmark with manual annotations to measure pipeline extraction accuracy against ground truth.

**Milestone:** `pytest tests/golden_dataset/ -q` runs bi-directional validation (precision + recall) of pipeline outputs against manually annotated papers and produces a coverage report.

**Verification:**
1. Run `pytest tests/golden_dataset/ -q` and confirm all golden dataset tests pass.
2. Verify `tests/golden_dataset/` contains annotated paper JSONs with manually verified claims.
3. Run `pytest tests/tier4/ -q` and confirm tier-4 live validation tests pass.

**Status:** in-progress

**Completed:** N/A

**Evidence:** PR #137 (paper sourcing infrastructure), PR #138 (80 OA papers populated), PR #139 (paper registry), PR #140 (bi-directional validation framework), PR #141 (gap scenario execution), PR #142 (ground truth design validation), PR #143 (annotation sub-tasks), commit dd5f8b92 (golden dataset JSON schema), commit e6314ce7 (batch 1 annotations, 5 papers), PR #TBD (TC-LR13: batch 2 annotations — 17 additional papers across 5 domains via `tests/golden_dataset/scripts/batch2_annotate.py`, 4 enforcement tests in `tests/golden_dataset/test_batch_annotations.py`)

---

### Phase 5: Governance Bootstrap

**Goal:** Add command-center governance documentation to bring the repo from L0 to L2+ compliance.

**Milestone:** `ccv scan Literature-Review` produces zero errors against command-center schema validation for ARCHITECTURE.md, ROADMAP.md, TODO-MASTER.md, and task card files.

**Verification:**
1. Run `cd ~/Documents/command-center && python -m validator.cli scan Literature-Review --chain-enforce=error`.
2. Confirm output contains zero `error`-severity findings.
3. Verify `ARCHITECTURE.md`, `ROADMAP.md`, `TODO-MASTER.md`, and `docs/tasks/` exist and contain real content.

**Status:** in-progress

**Completed:** N/A

**Evidence:** PR #147 (governance bootstrap)

---

### Future: Production Hardening

**Goal:** Harden the pipeline for unattended production use with monitoring, alerting, and multi-domain deployment.

**Milestone:** The pipeline runs as a scheduled job that processes new papers, generates updated gap reports, and sends alerts when evidence coverage crosses configurable thresholds.

**Verification:**
1. Configure a cron-based pipeline run with `pipeline_config.json` and confirm it completes without manual intervention.
2. Verify alert notifications fire when a pillar's evidence coverage drops below the configured threshold.

**Status:** future-direction

**Completed:** N/A

**Evidence:** N/A

---

## Phase Gate Criteria

| Phase | Gate Test | Status |
|-------|-----------|--------|
| Phase 1: Core Pipeline | `pipeline_orchestrator.py --batch-mode` completes 5 stages; 745+ unit tests pass | Passed |
| Phase 2: Evidence Quality | Consensus judgments with provenance in version history; integration tests pass | Passed |
| Phase 3: Advanced Automation | Dashboard serves at :8000 with WebSocket progress; E2E tests pass | Passed |
| Phase 4: Golden Dataset | Golden dataset tests pass with bi-directional validation metrics | Pending |
| Phase 5: Governance | `ccv scan Literature-Review` produces zero errors | Pending |
| Future: Production Hardening | Unattended scheduled runs with alerting | Not started |

## Known Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM provider API changes break claim extraction | Pipeline stages 1-3 fail silently or produce degraded output | Provider abstraction layer isolates changes; fallback chain switches to alternate provider; golden dataset catches accuracy regressions |
| Golden dataset annotations contain subjective judgments | Validation metrics are unreliable; false confidence in pipeline accuracy | Multi-annotator protocol with inter-rater reliability scoring; consensus-based ground truth |
| Large PDF corpus exceeds API cost budget | Pipeline runs become prohibitively expensive | ROI optimizer with budget limits; incremental mode re-processes only new papers; gap-targeted pre-filtering skips irrelevant papers |
| Governance docs drift from codebase reality | L3 compliance fails; docs mislead developers | Governance docs reference actual file paths checked by `ccv scan`; CI integration planned |
