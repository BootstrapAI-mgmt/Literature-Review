# ENHANCE-P5-2: Integrate run_mode and continue Prompts with Orchestrator

**Category:** Interactive Prompts Enhancement  
**Priority:** 🟡 MEDIUM  
**Effort:** 2 hours  
**Created:** November 17, 2025  
**Source:** PR #46 Review - Deferred Items Section #2

---

## Problem Statement

UI components for `run_mode` and `continue` prompts exist (`renderRunModePrompt()`, `renderContinuePrompt()`), but the orchestrator doesn't call them. Only `pillar_selection` is fully integrated.

**Current Behavior:**
- ✅ `pillar_selection`: Fully working (orchestrator + UI + tests)
- ⚠️ `run_mode`: UI exists but orchestrator uses config or defaults
- ⚠️ `continue`: UI exists but deep loop has hardcoded logic
- ❌ `threshold_selection`: Not implemented
- ❌ `convergence_confirmation`: Not implemented

---

## Use Cases

### 1. Run Mode Selection
**Scenario:** User starts job without `run_mode` in config  
**Expected:** Dashboard prompts "Select analysis mode: ONCE or DEEP_LOOP?"  
**Current:** Uses default or requires config edit

### 2. Deep Loop Continuation
**Scenario:** Deep loop iteration finishes  
**Expected:** Prompt "Continue deep review loop? Yes/No"  
**Current:** Hardcoded logic or config-based

### 3. Threshold Selection (Future)
**Scenario:** Gap analysis starts  
**Expected:** Prompt "Enter convergence threshold (e.g., 5.0, 10.0)"  
**Current:** Uses default threshold

### 4. Convergence Confirmation (Future)
**Scenario:** Deep loop reaches convergence  
**Expected:** Prompt "Gap below threshold. Exit loop? Yes/No"  
**Current:** Auto-exits

---

## Acceptance Criteria

### Phase 1: Core Integration (Required)
- [ ] `run_mode` prompt integrated when mode not in config
- [ ] `continue` prompt used in deep loop workflow (after each iteration)
- [ ] Tests updated to cover new prompt types
- [ ] Error handling for timeout/invalid responses
- [ ] Backward compatibility maintained (config overrides prompts)

### Phase 2: Advanced Prompts (Optional)
- [ ] `threshold_selection` prompt before gap analysis
- [ ] `convergence_confirmation` before exiting loop
- [ ] Prompt history saved to job metadata (if ENHANCE-P5-3 completed)

---

## Implementation Plan

### 1. Add run_mode Prompt to Orchestrator

**File:** `pipeline_orchestrator.py`

```python
async def main():
    """Main orchestrator entry point"""
    config = load_config()
    
    # NEW: Prompt for run_mode if not in config
    if config.prompt_callback and not config.run_mode:
        run_mode_str = await config.prompt_callback(
            prompt_type="run_mode",
            prompt_data={
                "message": "Select analysis mode",
                "options": ["ONCE", "DEEP_LOOP"],
                "default": "ONCE"
            }
        )
        config.run_mode = RunMode[run_mode_str]  # Convert to enum
    
    # Rest of orchestrator logic...
```

**Test Case:**
```python
async def test_run_mode_prompt():
    """Test run_mode prompt when not in config"""
    config = OrchestratorConfig(run_mode=None, prompt_callback=mock_prompt)
    
    # Mock prompt response
    mock_prompt.return_value = "DEEP_LOOP"
    
    await main()
    
    # Verify prompt was called
    mock_prompt.assert_called_once_with(
        prompt_type="run_mode",
        prompt_data={"message": "Select analysis mode", ...}
    )
```

---

### 2. Add continue Prompt to Deep Loop

**File:** `pipeline_orchestrator.py`

```python
async def deep_loop_workflow(config, papers):
    """Execute deep review loop until convergence"""
    iteration = 1
    
    while True:
        logger.info(f"Deep loop iteration {iteration}")
        
        # Run gap analysis
        gap_analysis_results = await run_gap_analysis(papers, config)
        
        # Check convergence
        if gap_analysis_results['converged']:
            logger.info("Convergence achieved!")
            break
        
        # NEW: Prompt user to continue (instead of hardcoded logic)
        if config.prompt_callback:
            continue_choice = await config.prompt_callback(
                prompt_type="continue",
                prompt_data={
                    "message": f"Iteration {iteration} complete. Continue deep review loop?",
                    "iteration": iteration,
                    "gap_count": len(gap_analysis_results['gaps']),
                    "options": ["Yes", "No"],
                    "default": "Yes"
                }
            )
            
            if continue_choice.lower() != "yes":
                logger.info("User chose to stop deep loop")
                break
        
        # Run deep review for critical gaps
        await run_deep_review(gap_analysis_results['gaps'], config)
        
        iteration += 1
        
        # Safety limit
        if iteration > config.max_iterations:
            logger.warning("Max iterations reached")
            break
```

**Test Case:**
```python
async def test_continue_prompt_in_deep_loop():
    """Test continue prompt during deep loop"""
    config = OrchestratorConfig(
        run_mode=RunMode.DEEP_LOOP,
        prompt_callback=mock_prompt
    )
    
    # Mock: continue once, then stop
    mock_prompt.side_effect = ["Yes", "No"]
    
    await deep_loop_workflow(config, papers)
    
    # Verify prompt called twice
    assert mock_prompt.call_count == 2
```

---

### 3. Update UI Rendering (Already Exists)

**Current UI** (`webdashboard/templates/index.html`):

```javascript
function renderRunModePrompt(promptData) {
    // Already implemented - just needs orchestrator integration
    const options = promptData.options || ["ONCE", "DEEP_LOOP"];
    const html = `
        <div class="form-check">
            <input type="radio" name="run_mode" value="ONCE" checked>
            <label>ONCE - Single analysis pass</label>
        </div>
        <div class="form-check">
            <input type="radio" name="run_mode" value="DEEP_LOOP">
            <label>DEEP_LOOP - Iterative deep review until convergence</label>
        </div>
    `;
    return html;
}

function renderContinuePrompt(promptData) {
    // Already implemented - just needs orchestrator integration
    const iteration = promptData.iteration || 1;
    const gapCount = promptData.gap_count || 0;
    const html = `
        <p>Iteration ${iteration} complete. Found ${gapCount} gaps.</p>
        <div class="form-check">
            <input type="radio" name="continue" value="Yes" checked>
            <label>Yes - Continue deep review loop</label>
        </div>
        <div class="form-check">
            <input type="radio" name="continue" value="No">
            <label>No - Stop and finalize results</label>
        </div>
    `;
    return html;
}
```

**No UI changes needed** - these functions already exist from PR #46.

---

### 4. Update Tests

**File:** `tests/integration/test_interactive_prompts.py`

Add 2 new test cases:

```python
@pytest.mark.asyncio
async def test_run_mode_prompt_integration():
    """Test run_mode prompt when starting job without config"""
    # Test implementation
    pass

@pytest.mark.asyncio
async def test_continue_prompt_deep_loop():
    """Test continue prompt in deep loop workflow"""
    # Test implementation
    pass
```

---

## Testing Plan

### Unit Tests
1. **Test run_mode prompt:** Config without run_mode triggers prompt
2. **Test continue prompt:** Deep loop calls prompt after each iteration
3. **Test timeout handling:** Timeout on run_mode defaults to ONCE
4. **Test invalid response:** Invalid choice reprompts or uses default

### Integration Tests
1. **Full workflow:** Start job without config → prompt for mode → run
2. **Deep loop workflow:** Run deep loop → prompt to continue → verify stop
3. **Backward compatibility:** Config with run_mode skips prompt

### Manual Testing
1. Start dashboard, create job without run_mode, verify prompt appears
2. Run deep loop job, verify continue prompt after iteration 1
3. Test timeout behavior (wait 5 minutes, verify default chosen)

---

## Configuration

### Optional: Add prompt_type enabling

**File:** `pipeline_config.json`

```json
{
  "prompts": {
    "enabled_types": [
      "pillar_selection",
      "run_mode",
      "continue"
    ],
    "defaults": {
      "run_mode": "ONCE",
      "continue": "Yes"
    }
  }
}
```

**Behavior:**
- If `run_mode` not in `enabled_types`, use config or default
- Allows gradual rollout of new prompt types

---

## Rollout Strategy

### Phase 1: Internal Testing (Week 1)
- Implement run_mode and continue prompts
- Test with internal users
- Gather feedback on UX

### Phase 2: Beta Release (Week 2)
- Enable prompts for beta users
- Monitor usage patterns
- Fix bugs

### Phase 3: General Availability (Week 3)
- Enable for all users
- Update documentation
- Announce new features

---

## Dependencies

**Requires:**
- ✅ `prompt_handler.py` (done in PR #46)
- ✅ UI components (done in PR #46)
- ✅ WebSocket infrastructure (done in PR #38)

**Blocks:**
- ENHANCE-P5-3 (Prompt History) - needs prompts to record
- ENHANCE-P5-6 (Documentation) - needs feature to document

**Synergy:**
- Works well with ENHANCE-P5-4 (Multi-Select) - similar UX pattern
- Complements ENHANCE-P5-5 (Configurable Timeout) - per-prompt timeouts

---

## Future Enhancements (Out of Scope)

### threshold_selection Prompt
```python
threshold = await config.prompt_callback(
    prompt_type="threshold_selection",
    prompt_data={
        "message": "Enter convergence threshold",
        "default": "10.0",
        "min": 0.0,
        "max": 100.0
    }
)
```

### convergence_confirmation Prompt
```python
confirm = await config.prompt_callback(
    prompt_type="convergence_confirmation",
    prompt_data={
        "message": "Gap below threshold. Exit deep loop?",
        "current_gap": 4.2,
        "threshold": 5.0
    }
)
```

---

## Estimated Breakdown

- **Orchestrator Integration:** 45 minutes
  - run_mode prompt: 20 min
  - continue prompt: 25 min
- **Test Updates:** 45 minutes
  - 2 new test cases: 30 min
  - Manual testing: 15 min
- **Code Review & Refinement:** 30 minutes
- **Total:** 2 hours

---

## Success Metrics

- [ ] Users can start jobs without pre-configured run_mode
- [ ] Deep loop workflow allows interactive continuation
- [ ] No regressions in existing prompt functionality
- [ ] Test coverage maintained at >90% for prompt_handler.py
- [ ] Zero timeout-related bugs reported
