# Master To-Do — Literature Review

## How to Read This

- `[x]` = completed, `[ ]` = pending
- `[TC-LRXX]` = task card ID (see `docs/tasks/` for full specs)
- Priority tags: `P0` = blocks milestone gate, `P1` = critical path, `P2` = quality improvement
- `Blocked by:` indicates a dependency on another task

## Summary

| Phase | Total | Done | Remaining | Blocked |
|-------|-------|------|-----------|---------|
| Phase 1: Core Pipeline | 4 | 4 | 0 | 0 |
| Phase 2: Evidence Quality | 3 | 3 | 0 | 0 |
| Phase 3: Advanced Automation | 3 | 3 | 0 | 0 |
| Phase 4: Golden Dataset | 4 | 3 | 1 | 0 |
| Phase 5: Governance | 5 | 0 | 5 | 0 |
| **Total** | **19** | **13** | **6** | **0** |

## Phase 1: Core Pipeline

- [x] **[TC-LR01]** Implement 5-stage pipeline orchestrator with single-command execution *(PR #6)*
  - Deliverable: `pipeline_orchestrator.py` coordinating journal-reviewer, judge, DRA, sync, orchestrator
  - **Acceptance:** `python pipeline_orchestrator.py --batch-mode` completes all 5 stages

- [x] **[TC-LR02]** Set up test infrastructure with tiered pytest markers *(PR #7)*
  - Deliverable: `tests/` directory with unit/component/integration/e2e tiers and shared fixtures
  - **Acceptance:** `pytest tests/unit/ -q` runs 745+ tests with zero failures

- [x] **[TC-LR03]** Add checkpoint/resume and retry logic to pipeline *(PR #10, commit cd05939d)*
  - Deliverable: `pipeline_checkpoint.json` written per stage; `--resume` and `--resume-from` flags
  - **Acceptance:** Kill pipeline mid-run, re-run with `--resume`, pipeline continues from last checkpoint

- [x] **[TC-LR04]** Refactor to `literature_review/` Python package with organized submodules *(commit 0af7c91e)*
  - Deliverable: 12 subpackages under `literature_review/` with proper `__init__.py` files
  - **Acceptance:** `python -c "import literature_review"` succeeds; all existing tests pass

## Phase 2: Evidence Quality

- [x] **[TC-LR05]** Add multi-dimensional evidence scoring and claim provenance tracking *(PR #14)*
  - Deliverable: Provenance metadata (source, page, method) on each claim in version history
  - **Acceptance:** `review_version_history.json` entries contain `provenance` field with non-empty values

- [x] **[TC-LR06]** Implement 3-judge consensus evaluation with inter-rater reliability *(PR #18, PR #20)*
  - Deliverable: Consensus judgment in `literature_review/analysis/judge.py` with 3 independent verdicts
  - **Acceptance:** Version history shows `consensus_judgment` entries with 3 judge scores per claim

- [x] **[TC-LR07]** Build integration test suite for cross-stage data flows *(PR #16, PR #17, PR #21)*
  - Deliverable: Integration tests for journal-to-judge, CSV sync, appeal flow, and orchestrator
  - **Acceptance:** `pytest tests/integration/ -q` passes with zero failures

## Phase 3: Advanced Automation

- [x] **[TC-LR08]** Add parallel processing, smart retry, and API quota management *(PR #19)*
  - Deliverable: Parallel batch processing in pipeline; circuit breaker; per-provider quota tracking
  - **Acceptance:** `pipeline_config.json` v2 features enabled; pipeline processes papers in parallel batches

- [x] **[TC-LR09]** Build FastAPI web dashboard with real-time job monitoring *(PR #19, commit ac80048f)*
  - Deliverable: `webdashboard/app.py` serving REST API + WebSocket at port 8000
  - **Acceptance:** `./run_dashboard.sh` starts; PDF upload creates a job; WebSocket streams progress

- [x] **[TC-LR10]** Implement ROI-based search optimization and incremental analysis *(PR #19)*
  - Deliverable: `literature_review/optimization/search_optimizer.py` with budget-aware paper selection
  - **Acceptance:** Pipeline with `roi_optimizer.enabled=true` skips low-ROI papers and tracks cost savings

## Phase 4: Golden Dataset

- [x] **[TC-LR11]** Build paper sourcing and registry infrastructure *(PR #137, PR #138, PR #139)*
  - Deliverable: CLI tool for sourcing OA papers; registry of 80+ papers with metadata
  - **Acceptance:** `tests/golden_dataset/` contains paper registry JSON with 80+ entries

- [x] **[TC-LR12]** Implement bi-directional validation framework *(PR #140, PR #141, PR #142)*
  - Deliverable: Precision + recall metrics comparing pipeline output to ground truth annotations
  - **Acceptance:** `pytest tests/golden_dataset/ -q` runs validation metrics without errors

- [x] **[TC-LR13]** Complete manual paper annotations (batch 2+) `P0` *(PR #TBD, batch-2 generator at tests/golden_dataset/scripts/batch2_annotate.py)*
  - Deliverable: Manually annotated claim JSONs for 20+ papers across multiple domains
  - **Acceptance:** Annotation JSONs exist for 22 papers (5 batch-1 + 17 batch-2) spanning 5 domains; each contains verified claims with `page_number`, `claim_text`, `pillar_mapping` enforced by `tests/golden_dataset/test_batch_annotations.py`

- [ ] **[TC-LR14]** Run full accuracy benchmark against golden dataset `P1`
  - Deliverable: Benchmark report showing precision/recall/F1 for claim extraction and gap analysis
  - **Acceptance:** `pytest tests/golden_dataset/ -q` passes; benchmark report written to `reports/`
  - **Unblocked by:** TC-LR13

## Phase 5: Governance

- [ ] **[TC-LR15]** Create ARCHITECTURE.md following command-center schema `P0`
  - Deliverable: `ARCHITECTURE.md` with 6 required sections populated from actual codebase
  - **Acceptance:** All paths in Project Structure exist on disk; no future-tense in "What This Is"

- [ ] **[TC-LR16]** Create ROADMAP.md with verifiable milestones `P0`
  - Deliverable: `ROADMAP.md` with phases, milestones, verification steps, and evidence
  - **Acceptance:** All complete phases have non-placeholder evidence; milestones use tangible verbs

- [ ] **[TC-LR17]** Create TODO-MASTER.md with phase-based task tracker `P0`
  - Deliverable: `TODO-MASTER.md` with TC-IDs, summary table, checkbox items with PR references
  - **Acceptance:** Summary table counts match actual checkboxes; TC-IDs are unique

- [ ] **[TC-LR18]** Create task card files under docs/tasks/ `P1`
  - Deliverable: Task card files for open work items with required fields per CC schema
  - **Acceptance:** Each card has TC-ID, Priority, Status, Dependencies, Problem, Deliverables, Files, Acceptance Criteria

- [ ] **[TC-LR19]** Create CLAUDE.md agent context file `P1`
  - Deliverable: `CLAUDE.md` with project structure, commands, conventions
  - **Acceptance:** File exists at repo root with accurate project information
