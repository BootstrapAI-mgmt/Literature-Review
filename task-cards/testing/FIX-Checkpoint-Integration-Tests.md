# Task Card: Fix Checkpoint Integration Tests

**Status**: 🔴 Not Started  
**Priority**: Medium  
**Effort Estimate**: 3-4 hours  
**Category**: Testing / Orchestrator  

---

## Problem Statement

4 integration tests in `tests/integration/test_checkpoint_integration.py` are failing with:
```
OSError: pytest: reading from stdin while output is captured!
```

This occurs because the pipeline orchestrator calls `input()` for user prompts during execution, which is incompatible with pytest's output capture mode.

### Failing Tests:
1. `test_checkpoint_file_created_during_run`
2. `test_resume_after_failure`
3. `test_resume_from_specific_stage`
4. `test_dra_stage_handling_in_checkpoint`

---

## Root Cause Analysis

The orchestrator uses interactive prompts via `input()` for:
- Selecting which pillars to analyze
- Choosing analysis modes (ALL, DEEP, NONE)
- Confirming actions during execution

When pytest runs these tests, it captures stdout/stderr by default, making `input()` unavailable and causing the OSError.

**Key Code Location**: 
- `pipeline_orchestrator.py` - User prompt handling
- `webdashboard/prompt_handler.py` - Prompt utilities

---

## Proposed Solution

### Option 1: Add Non-Interactive Mode (Recommended)

**Implementation Steps**:

1. **Add `--batch-mode` or `--skip-prompts` CLI flag**
   ```python
   parser.add_argument(
       '--batch-mode',
       action='store_true',
       help='Run in non-interactive mode (skip all user prompts, use defaults)'
   )
   ```

2. **Update prompt handling to respect batch mode**
   ```python
   def get_user_input(prompt, default=None, batch_mode=False):
       if batch_mode:
           logger.info(f"Batch mode: using default for '{prompt}': {default}")
           return default
       return input(prompt)
   ```

3. **Set sensible defaults for batch mode**:
   - Pillar selection: ALL
   - Analysis mode: Standard (not DEEP)
   - Confirmations: Yes/proceed

4. **Update tests to use batch mode**:
   ```python
   result = subprocess.run(
       [sys.executable, 'pipeline_orchestrator.py', '--batch-mode', ...],
       capture_output=True,
       text=True
   )
   ```

### Option 2: Mock Input via Environment Variable

Use environment variable to provide pre-determined inputs:
```python
monkeypatch.setenv("ORCHESTRATOR_TEST_MODE", "1")
monkeypatch.setenv("ORCHESTRATOR_TEST_INPUTS", "ALL\nyes\n...")
```

**Pros**: Less intrusive code changes  
**Cons**: More complex test setup, less maintainable

---

## Implementation Checklist

- [ ] Add `--batch-mode` flag to `pipeline_orchestrator.py`
- [ ] Create `get_user_input()` wrapper function in orchestrator
- [ ] Replace all `input()` calls with `get_user_input()` wrapper
- [ ] Update prompt_handler.py to support batch mode
- [ ] Define default values for all prompts
- [ ] Add batch mode documentation to README
- [ ] Update 4 failing tests to use `--batch-mode` flag
- [ ] Run tests locally to verify fixes
- [ ] Verify CI/CD integration tests pass

---

## Acceptance Criteria

1. All 4 checkpoint integration tests pass in CI/CD
2. Orchestrator can run completely non-interactively with `--batch-mode`
3. Batch mode behavior is documented
4. No regression in interactive mode (default behavior unchanged)
5. Integration test suite achieves >95% pass rate

---

## Testing Plan

### Unit Tests
```bash
pytest tests/unit/test_orchestrator.py -k batch
```

### Integration Tests
```bash
pytest tests/integration/test_checkpoint_integration.py -v
```

### Manual Testing
```bash
# Verify batch mode works
python pipeline_orchestrator.py --batch-mode --dry-run

# Verify interactive mode still works
python pipeline_orchestrator.py --dry-run
```

---

## Files to Modify

1. **`pipeline_orchestrator.py`**
   - Add `--batch-mode` argument
   - Create `get_user_input()` wrapper
   - Replace `input()` calls

2. **`webdashboard/prompt_handler.py`**
   - Add batch mode support
   - Define default responses

3. **`tests/integration/test_checkpoint_integration.py`**
   - Add `--batch-mode` to test commands
   - Remove/update assertions affected by non-interactive mode

4. **`README.md` / `docs/USER_MANUAL.md`**
   - Document `--batch-mode` flag
   - Add examples for CI/CD usage

---

## Success Metrics

- **Before**: 4/4 checkpoint tests failing (100% failure rate)
- **After**: 4/4 checkpoint tests passing (100% pass rate)
- **Integration Tests Overall**: 96% pass rate (142/147) → 98% pass rate (146/147)

---

## Related Issues

- CI/CD integration test failures
- Pipeline automation requirements
- Future: Support for scheduled/automated pipeline runs

---

## Notes

- This change will also enable easier automation of the pipeline for scheduled runs
- Consider adding validation mode that reports what would be done without prompts
- May want to add JSON output of checkpoint status for programmatic access

---

## Dependencies

None - self-contained change

---

## Timeline

- **Investigation**: 30 minutes (already completed)
- **Implementation**: 2-3 hours
- **Testing**: 30-60 minutes
- **Documentation**: 30 minutes
- **Total**: 3-4 hours
