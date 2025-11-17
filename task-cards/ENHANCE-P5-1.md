# ENHANCE-P5-1: Add pytest-asyncio to requirements-dev.txt

**Category:** Configuration & Dependencies  
**Priority:** 🔴 HIGH (CRITICAL)  
**Effort:** 1 minute  
**Created:** November 17, 2025  
**Source:** PR #46 Review - Phase 5 Interactive Prompts

---

## Problem Statement

`pytest-asyncio` was installed manually during PR #46 testing but not added to `requirements-dev.txt`. This creates a missing dependency issue that will:
- Cause CI/CD pipeline failures when running async tests
- Create developer onboarding friction (missing dependency error)
- Result in incomplete test suite in clean environments

**Current Workaround:** Manual `pip install pytest-asyncio` required

---

## Acceptance Criteria

- [x] Package installed (done in PR #46)
- [ ] Added to `requirements-dev.txt` with version constraint
- [ ] Verified in CI pipeline (if applicable)
- [ ] `pytest.ini` configured with `asyncio_mode = auto` (✅ already done in PR #46)

---

## Implementation Plan

### 1. Add Package to requirements-dev.txt

```bash
echo "pytest-asyncio>=0.21.0" >> requirements-dev.txt
```

**Rationale:**
- Version 0.21.0+ supports `asyncio_mode = auto` in pytest.ini
- Uses `>=` to allow minor updates while ensuring compatibility

### 2. Verify Installation

```bash
pip install -r requirements-dev.txt
pytest tests/integration/test_interactive_prompts.py -v
```

**Expected Output:**
- 6 passing tests
- 4 skipped tests (expected in environments without live connection manager)
- No import errors or missing dependency warnings

### 3. Update CI Configuration (if applicable)

If CI/CD pipeline exists, ensure it installs dev dependencies:

```yaml
# Example: .github/workflows/tests.yml
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    pip install -r requirements-dev.txt  # Ensure this line exists
```

---

## Testing

### Validation Steps

1. **Clean Environment Test:**
   ```bash
   # In fresh virtualenv
   python -m venv test_env
   source test_env/bin/activate
   pip install -r requirements-dev.txt
   pytest tests/integration/test_interactive_prompts.py
   ```
   
   **Expected:** All tests run (6 pass, 4 skip)

2. **Verify Package Listed:**
   ```bash
   grep pytest-asyncio requirements-dev.txt
   ```
   
   **Expected:** `pytest-asyncio>=0.21.0`

3. **Check Installed Version:**
   ```bash
   pip show pytest-asyncio
   ```
   
   **Expected:** Version 0.21.0 or higher

---

## Impact

**Without Fix:**
- ❌ CI/CD failures on async tests
- ❌ New developer onboarding issues
- ❌ Incomplete test coverage in clean environments

**With Fix:**
- ✅ Reliable test suite execution
- ✅ Smooth developer experience
- ✅ CI/CD pipeline stability

**Estimated Time Saved:** 10-30 minutes per developer/environment setup

---

## Dependencies

**Blocks:**
- CI/CD pipeline reliability
- Developer onboarding documentation accuracy

**Blocked By:**
- None (ready to implement immediately)

---

## Related Items

- **PR #46:** Interactive Prompts implementation
- **Test File:** `tests/integration/test_interactive_prompts.py` (277 lines, 10 tests)
- **Configuration:** `pytest.ini` (already has `asyncio_mode = auto`)

---

## Notes

- This is a **1-minute fix** that prevents future issues
- Should be merged immediately to prevent CI failures
- Consider adding to PR checklist: "Update requirements files if new dependencies added"
