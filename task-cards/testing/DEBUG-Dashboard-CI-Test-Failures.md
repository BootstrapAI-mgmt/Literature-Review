# Task Card: Debug Dashboard Integration Test Failures in CI

**Status:** Open  
**Priority:** High  
**Component:** Testing / Dashboard / CI/CD  
**Estimated Effort:** 4-6 hours  
**Created:** 2025-11-20

---

## Problem Statement

31 dashboard integration tests consistently fail in GitHub Actions CI with HTTP 500 Internal Server Error, but **all tests pass locally** in the same environment. This is a CI environment-specific issue that persists across Python versions and test fixture improvements.

### Failure Pattern

**Local Environment (✅ PASS):**
```
Python 3.12.1 (Codespaces)
30/31 tests pass (97% pass rate)
```

**CI Environment (❌ FAIL):**
```
Python 3.12 (GitHub Actions ubuntu-latest)
0/31 dashboard tests pass (0% pass rate)
ALL tests return HTTP 500 Internal Server Error
```

### Symptoms

All failing tests show identical error pattern:
```
HTTP Request: POST http://testserver/api/upload/batch "HTTP/1.1 500 Internal Server Error"
assert 500 == 200
  +  where 500 = <Response [500 Internal Server Error]>.status_code
```

**NO server-side traceback visible** because `TestClient(raise_server_exceptions=False)` swallows the actual exception.

---

## Affected Tests (31 total)

### Batch Upload Tests (10 tests)
- `test_batch_upload_creates_draft_job`
- `test_batch_upload_single_file`
- `test_batch_upload_rejects_non_pdf`
- `test_batch_upload_without_api_key`
- `test_configure_draft_job`
- `test_configure_nonexistent_job`
- `test_start_configured_job`
- `test_start_unconfigured_job`
- `test_start_job_without_files`
- `test_complete_input_pipeline`

### Job Comparison Tests (9 tests)
- `test_compare_jobs_basic`
- `test_compare_jobs_with_regression`
- `test_compare_jobs_job1_not_found`
- `test_compare_jobs_job2_not_found`
- `test_compare_jobs_job1_not_completed`
- `test_compare_jobs_job2_not_completed`
- `test_compare_jobs_multiple_pillars`
- `test_compare_jobs_no_changes`
- `test_compare_jobs_authentication`

### Results Visualization Tests (12 tests)
- `test_results_listing`
- `test_results_listing_job_not_found`
- `test_results_listing_job_not_completed`
- `test_file_categorization`
- `test_file_retrieval`
- `test_file_retrieval_not_found`
- `test_path_traversal_prevention`
- `test_zip_download`
- `test_zip_download_job_not_completed`
- `test_results_no_outputs`
- `test_temporal_visualization_generation`
- `test_api_key_authentication`

---

## Investigation History

### Actions Taken (Chronological)

1. **✅ Fixed All Syntax Errors**
   - Resolved Unicode characters in state_manager.py
   - Fixed missing punctuation in orchestrator.py
   - All code now syntactically valid

2. **✅ Updated API Mocking**
   - Fixed test_judge_with_mocks.py for new google-genai SDK
   - All component tests passing

3. **✅ Upgraded to Python 3.12**
   - Changed Dockerfile from 3.11 to 3.12
   - Updated all CI workflows to Python 3.12
   - Documented requirement in README.md
   - **Result:** Tests still fail in CI

4. **✅ Improved Test Fixtures**
   - Added BASE_DIR patching to test_client fixtures
   - Clear sys.modules cache for clean app imports
   - Ensure proper test isolation
   - **Result:** Tests still fail in CI

### What We Know

- ✅ Python version is NOT the issue (both local and CI use 3.12)
- ✅ Code is syntactically valid (passes locally)
- ✅ Test fixtures are properly isolated (improved patching)
- ✅ Dependencies are installed correctly (CI install step succeeds)
- ❌ Something in CI environment causes FastAPI app to crash
- ❌ No traceback visible due to raise_server_exceptions=False

---

## Environment Comparison

| Aspect | Local (✅ PASSING) | CI (❌ FAILING) |
|--------|-------------------|-----------------|
| **OS** | Ubuntu 24.04 (Codespaces) | ubuntu-latest (GitHub Actions) |
| **Python** | 3.12.1 | 3.12.x |
| **Test Framework** | pytest 8.4.2 | pytest 8.4.2 |
| **FastAPI** | Same version | Same version |
| **Working Directory** | /workspaces/Literature-Review | /home/runner/work/Literature-Review/Literature-Review |
| **File Paths** | Patched to temp workspace | Patched to temp workspace |
| **Environment Variables** | Codespace env | GitHub Actions env |
| **Disk I/O** | Normal filesystem | GitHub Actions filesystem |
| **review_log.json** | Exists at BASE_DIR | May not exist? |

---

## Root Cause Hypotheses

### Hypothesis 1: Missing Files in CI
**Theory:** `review_log.json` or other required files don't exist in CI workspace

**Evidence:**
- Line 742 in app.py: `review_log_path = BASE_DIR / "review_log.json"`
- `load_existing_papers_from_review_log()` handles missing file (returns [])
- But maybe BASE_DIR is different in CI?

**Test:**
```bash
# In CI, check if BASE_DIR resolves correctly
pytest -xvs tests/integration/test_dashboard_input_pipeline.py::TestBatchUpload::test_batch_upload_creates_draft_job --capture=no
```

### Hypothesis 2: Import Order / Module State
**Theory:** App module imports in different order in CI, causing initialization failures

**Evidence:**
- Module-level code in app.py creates directories (lines 91-92)
- Test fixtures delete sys.modules['webdashboard.app'] and re-import
- Timing or import caching could differ between environments

**Test:**
- Add logging to app.py module-level code
- Check if directories are created successfully

### Hypothesis 3: Async/Event Loop Issues
**Theory:** TestClient async handling differs between environments

**Evidence:**
- All endpoints are async
- TestClient manages event loop internally
- GitHub Actions may have different asyncio behavior

**Test:**
- Temporarily set `raise_server_exceptions=True` to see actual error
- Check if event loop errors occur

### Hypothesis 4: File I/O Permissions
**Theory:** CI environment has different file permissions preventing file operations

**Evidence:**
- Tests create temp directories with tempfile.mkdtemp()
- File uploads involve shutil.copyfileobj()
- PDF validation reads file content

**Test:**
```python
# Add to test
import os
print(f"Temp dir permissions: {oct(os.stat(temp_workspace).st_mode)}")
```

---

## Investigation Plan

### Phase 1: Expose the Actual Error (1 hour)

**Goal:** See the real exception instead of HTTP 500

1. **Temporarily Enable Exceptions in CI:**
   ```python
   # tests/integration/test_dashboard_input_pipeline.py
   return TestClient(app_module.app, raise_server_exceptions=True)
   ```

2. **Add Server-Side Logging:**
   ```python
   # webdashboard/app.py (add at top of upload_batch function)
   logger.info(f"upload_batch called - BASE_DIR: {BASE_DIR}, WORKSPACE_DIR: {WORKSPACE_DIR}")
   logger.info(f"review_log_path exists: {(BASE_DIR / 'review_log.json').exists()}")
   ```

3. **Run Single Test with Full Output:**
   ```bash
   pytest -xvs tests/integration/test_dashboard_input_pipeline.py::TestBatchUpload::test_batch_upload_creates_draft_job
   ```

4. **Expected Outcome:**
   - See actual Python exception (ImportError, AttributeError, FileNotFoundError, etc.)
   - Understand what's crashing the FastAPI app

### Phase 2: Identify Root Cause (1-2 hours)

Based on the actual error from Phase 1:

**If ImportError:**
- Check if all dashboard dependencies are installed in CI
- Verify import paths are correct

**If FileNotFoundError:**
- Check which file is missing
- Ensure review_log.json exists or handle missing file gracefully
- Verify temp workspace paths are correct

**If AttributeError:**
- Check if module-level variables are initialized correctly
- Verify monkeypatch is working as expected

**If Permission Error:**
- Check file/directory permissions in CI
- Ensure temp directories are writable

### Phase 3: Implement Fix (1-2 hours)

Likely fixes based on common patterns:

**Fix Option A: Ensure review_log.json exists**
```python
# In test fixture or conftest.py
@pytest.fixture(autouse=True)
def ensure_review_log(temp_workspace):
    review_log = temp_workspace.parent / "review_log.json"
    review_log.write_text("[]")
    yield
    if review_log.exists():
        review_log.unlink()
```

**Fix Option B: Make BASE_DIR handling more robust**
```python
# webdashboard/app.py
review_log_path = BASE_DIR / "review_log.json"
if not review_log_path.exists():
    logger.warning(f"review_log.json not found at {review_log_path}, using empty list")
    existing_papers = []
else:
    existing_papers = load_existing_papers_from_review_log(review_log_path)
```

**Fix Option C: Improve test fixture isolation**
```python
# Create a completely isolated BASE_DIR for tests
app_module.BASE_DIR = temp_workspace.parent
(temp_workspace.parent / "review_log.json").write_text("[]")
```

### Phase 4: Validate Fix (1 hour)

1. **Run all dashboard tests locally:**
   ```bash
   pytest tests/integration/test_dashboard_input_pipeline.py -v
   pytest tests/integration/test_job_comparison_api.py -v
   pytest tests/integration/test_results_visualization.py -v
   ```

2. **Push to CI and verify:**
   ```bash
   git commit -am "Fix dashboard CI test failures"
   git push origin main
   gh run watch
   ```

3. **Expected Result:**
   - All 31 dashboard tests pass in CI
   - No regression in local tests

---

## Success Criteria

- [ ] Actual exception/error identified and documented
- [ ] Root cause understood and explained
- [ ] Fix implemented and tested locally
- [ ] All 31 dashboard integration tests pass in CI
- [ ] All dashboard tests continue to pass locally
- [ ] No regression in other test suites
- [ ] Documentation updated with findings

---

## Files to Investigate

### Primary Files
- `webdashboard/app.py` - Main FastAPI application (lines 82-92, 742-745)
- `tests/integration/test_dashboard_input_pipeline.py` - Test fixtures (lines 41-64)
- `tests/integration/test_job_comparison_api.py` - Test fixtures (lines 80-99)
- `tests/integration/test_results_visualization.py` - Test fixtures (lines 87-106)
- `webdashboard/duplicate_detector.py` - File loading logic (lines 145-178)

### CI Configuration
- `.github/workflows/integration-tests.yml` - CI workflow definition

### Supporting Files
- `review_log.json` - May or may not exist in CI
- `pytest.ini` - Test configuration
- `requirements-dashboard.txt` - Dashboard dependencies

---

## Debugging Commands

### Local Testing
```bash
# Run with full output
pytest -xvs tests/integration/test_dashboard_input_pipeline.py::TestBatchUpload::test_batch_upload_creates_draft_job

# Run with exception raising
# (modify test_client fixture temporarily)

# Check file paths
python -c "from pathlib import Path; from webdashboard import app; print(f'BASE_DIR: {app.BASE_DIR}')"
```

### CI Debugging
```bash
# View latest CI run
gh run view --log-failed

# Watch current run
gh run watch

# Re-run specific job
gh run rerun <run-id> --job <job-id>
```

### Add Temporary Logging
```python
# In webdashboard/app.py at line 668 (start of upload_batch)
import sys
logger.error(f"DEBUG: Python version: {sys.version}")
logger.error(f"DEBUG: BASE_DIR: {BASE_DIR}")
logger.error(f"DEBUG: review_log exists: {(BASE_DIR / 'review_log.json').exists()}")
logger.error(f"DEBUG: WORKSPACE_DIR: {WORKSPACE_DIR}")
logger.error(f"DEBUG: temp_workspace via fixture: check if properly patched")
```

---

## Related Issues

- ✅ Task Card: `FIX-Checkpoint-Integration-Tests.md` - 4 checkpoint tests (different root cause)
- ✅ Commit `44ea6db`: Upgraded all environments to Python 3.12
- ✅ Commit `784768b`: Fixed test fixtures to patch BASE_DIR
- ✅ All syntax errors resolved
- ✅ All component tests passing

---

## Notes

### Why Tests Pass Locally But Fail in CI

This is a classic "works on my machine" problem. Possible reasons:

1. **Environment Variables:** CI may have different env vars set/unset
2. **File System Differences:** GitHub Actions uses ephemeral runners with fresh filesystems
3. **Timing Issues:** CI may be slower/faster, exposing race conditions
4. **Import Caching:** Python module imports may behave differently
5. **Working Directory:** Different pwd affects relative path resolution
6. **Missing Files:** Files committed to repo exist locally but may not be checked out in CI

### Why We Can't See the Error

The `raise_server_exceptions=False` parameter in TestClient is necessary for async endpoint testing, but it hides the actual server-side exceptions. The first step must be to temporarily enable exceptions to see what's really happening.

### Priority Justification

**High Priority** because:
- 31 tests failing (21% of integration test suite)
- Blocks CI/CD pipeline green status
- Dashboard is a key feature for user interaction
- Issue has persisted through multiple fix attempts
- Quick investigation (Phase 1) will reveal root cause

---

## Implementation Checklist

- [ ] Phase 1: Enable exception logging and identify actual error
- [ ] Phase 2: Analyze root cause based on actual exception
- [ ] Phase 3: Implement appropriate fix
- [ ] Phase 4: Validate fix in both local and CI environments
- [ ] Document findings in this task card
- [ ] Update test fixtures if needed
- [ ] Update dashboard code if needed
- [ ] Ensure no regression
- [ ] Close task card with summary
