# Checkpoint Architecture - Critical Gaps & Remediation Plan

**Date**: November 15, 2025  
**Issue**: Pipeline lacks incremental state-saving, causing work loss on crashes/timeouts

## Problem Statement

During E2E testing, the orchestrator processed 56/57 claims (9+ minutes of work) but lost ALL progress when it hit the 600-second timeout. This revealed critical architectural gaps in state persistence.

## Current State Analysis

### 1. Judge Pipeline (`literature_review/analysis/judge.py`)

**Current Behavior:**
- Processes 57 claims in 6 batches of ~10 claims each
- Logs "Batch N complete" after each batch
- **Only saves to `review_version_history.json` at the very end** (line 1312)

**Gap:**
```python
# Line 1172 - After each batch completes
logger.info(f"\nBatch {batch_num} complete. Progress: {init_approved_count} approved, {init_rejected_count} rejected")
# ❌ NO SAVE HERE - Should checkpoint progress

# Line 1312 - Only save point
save_version_history(VERSION_HISTORY_FILE, version_history)  # PHASE 4: Final save only
```

**Impact:**
- If crash at claim 56/57: Lose ALL 56 completed verdicts
- Must re-judge all claims from scratch
- Wastes API quota and time (~9 minutes per run)

**Required Fix:**
```python
# After each batch completes (line 1172)
logger.info(f"\nBatch {batch_num} complete. Progress: {init_approved_count} approved, {init_rejected_count} rejected")

# ✅ ADD: Incremental checkpoint save
version_history = update_claims_in_history(version_history, all_judged_claims)
save_version_history(VERSION_HISTORY_FILE, version_history)
logger.info(f"✓ Checkpoint saved: {len(all_judged_claims)} claims persisted")
```

### 2. Orchestrator (`literature_review/orchestrator.py`)

**Current Behavior:**
- Runs 6 major stages: Judge → DRA → Gap Analysis → Convergence → Deep Review → Recommendations
- **Only saves at final completion** (line 1528)

**Gap:**
```python
# Line 1528 - Only save point
save_orchestrator_state(ORCHESTRATOR_STATE_FILE, all_results, score_history)
```

**Impact:**
- If crash after Judge completes: Must re-run Judge
- If crash after 3 gap analysis iterations: Lose all iteration work
- No resume capability between stages

**Required Fix:**
```python
# ✅ ADD: Save after each major stage
# After Judge completes
save_orchestrator_state(ORCHESTRATOR_STATE_FILE, all_results, score_history, stage="judge_complete")

# After DRA completes  
save_orchestrator_state(ORCHESTRATOR_STATE_FILE, all_results, score_history, stage="dra_complete")

# After each gap analysis iteration
save_orchestrator_state(ORCHESTRATOR_STATE_FILE, all_results, score_history, 
                        stage=f"gap_analysis_iteration_{iteration_count}")

# After deep review completes
save_orchestrator_state(ORCHESTRATOR_STATE_FILE, all_results, score_history, stage="deep_review_complete")
```

### 3. Orchestrator V2 Checkpoint System (`literature_review/pipeline/orchestrator_v2.py`)

**Current Behavior:**
- Has full `CheckpointManagerV2` class (lines 263-343)
- Supports atomic writes, per-paper tracking, dry-run mode
- **NEVER INSTANTIATED OR USED**

**Gap:**
```python
# Line 263-343: Full checkpoint system exists
class CheckpointManagerV2:
    """Enhanced checkpoint manager for v2.0 with per-paper tracking."""
    # ... complete implementation ...
    
# ❌ NO USAGE - Class is never instantiated anywhere in codebase
```

**Impact:**
- Wasted development effort
- Zero actual checkpointing happening
- False sense of robustness

**Required Fix:**
1. Integrate `CheckpointManagerV2` into judge.py main loop
2. Call `checkpoint.save()` after each batch
3. Add recovery logic on startup to resume from last checkpoint

### 4. Deep Reviewer (Need Analysis)

**Status:** TBD - Need to check if incremental saves exist

## Remediation Plan

### Phase 1: Judge Incremental Checkpointing (HIGHEST PRIORITY)

**Implementation:**
1. Add checkpoint save after each batch completion
2. Add startup recovery to skip already-judged claims
3. Add claim-level status tracking (pending → in_progress → complete)

**Files to Modify:**
- `literature_review/analysis/judge.py`
  - Add `save_after_batch=True` parameter
  - Insert `save_version_history()` call after line 1172
  - Add startup logic to detect incomplete batches

**Expected Behavior:**
```
Batch 1 complete → Save checkpoint (10 claims)
Batch 2 complete → Save checkpoint (20 claims)
Batch 3 complete → Save checkpoint (30 claims)
[CRASH]
Restart → Detect 30 claims done, resume from Batch 4
```

### Phase 2: Orchestrator Stage Checkpointing

**Implementation:**
1. Add stage tracking to orchestrator state
2. Save after each major pipeline stage
3. Add resume logic to skip completed stages

**Files to Modify:**
- `literature_review/orchestrator.py`
  - Enhance `save_orchestrator_state()` to include stage info
  - Add saves after Judge, DRA, each gap iteration
  - Add startup logic to resume from last completed stage

### Phase 3: Integrate CheckpointManagerV2

**Implementation:**
1. Instantiate CheckpointManagerV2 in judge.py
2. Replace manual save calls with checkpoint.save()
3. Add per-claim status tracking

**Files to Modify:**
- `literature_review/analysis/judge.py`
  - Import and instantiate CheckpointManagerV2
  - Use checkpoint.update_paper_status() for each claim
  - Call checkpoint.save() after batches

### Phase 4: Deep Reviewer Checkpointing

**Implementation:**
1. Analyze current deep_reviewer.py save behavior
2. Add per-paper checkpoint saves
3. Add recovery for partial deep review runs

## Success Criteria

### Immediate Fix (Phase 1):
- [ ] Judge saves progress after each batch (every 10 claims)
- [ ] Judge detects partial completion on restart
- [ ] Judge resumes from last completed batch
- [ ] Test: Kill judge at claim 56 → Restart → Complete claim 57 only

### Full Solution (All Phases):
- [ ] Every module saves incrementally at logical checkpoints
- [ ] All modules detect and resume from crashes
- [ ] No work is lost on timeout/crash/interrupt
- [ ] State files are human-readable JSON with timestamps
- [ ] Atomic writes prevent corruption on crash during save

## Testing Plan

### Test 1: Judge Batch Recovery
```bash
# Run judge, kill after batch 2
timeout 30s python -m literature_review.analysis.judge

# Verify checkpoint saved
cat review_version_history.json | jq '.files[0].claims | length'

# Resume and complete
python -m literature_review.analysis.judge
```

### Test 2: Orchestrator Stage Recovery
```bash
# Run orchestrator, kill after judge completes
timeout 120s python -m literature_review.orchestrator

# Verify judge stage saved
cat orchestrator_state.json | jq '.last_completed_stage'

# Resume from DRA stage
python -m literature_review.orchestrator --resume
```

### Test 3: Claim-Level Recovery
```bash
# Kill mid-batch (e.g., claim 5/10 in batch 1)
timeout 15s python -m literature_review.analysis.judge

# Verify partial batch saved (claims 1-4)
# Resume should pick up at claim 5
python -m literature_review.analysis.judge
```

## Implementation Priority

1. **URGENT** (Today): Judge batch checkpointing - Fixes your immediate pain point
2. **HIGH** (This Week): Orchestrator stage checkpointing - Prevents pipeline work loss
3. **MEDIUM** (Next Sprint): Integrate CheckpointManagerV2 - Clean up architecture
4. **LOW** (Future): Per-claim granular checkpointing - Ultimate resilience

## Estimated Effort

- Phase 1 (Judge batches): 2-3 hours
- Phase 2 (Orchestrator stages): 3-4 hours  
- Phase 3 (CheckpointManagerV2 integration): 4-6 hours
- Phase 4 (Deep Reviewer): 2-3 hours

**Total**: ~12-16 hours for complete checkpoint architecture

## Related Issues

- Timeout issue: 600-second timeout too short for 57 claims at 10 RPM
- Rate limiting: May need to increase from 10 RPM to speed up runs
- Error handling: Invalid judge responses should also trigger checkpoint saves

## Recommendations

### Immediate Actions:
1. Increase orchestrator timeout from 600s → 900s (15 minutes)
2. Implement Phase 1 judge checkpointing today
3. Re-run E2E test with new checkpoint system

### Long-term Improvements:
1. Add `--resume` flag to all pipeline modules
2. Add checkpoint validation on load (detect corruption)
3. Add checkpoint cleanup (auto-delete on successful completion)
4. Add progress dashboard showing checkpoint status

---

**Author**: GitHub Copilot  
**Reviewer**: TBD  
**Status**: Draft - Awaiting Review
