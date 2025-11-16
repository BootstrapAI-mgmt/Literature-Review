# Dashboard Manual Testing Guide

## Test Results Summary

### ✅ Task 1: Deep Reviewer Instantiation - COMPLETE
**Status**: Ready for manual use

**Key Findings**:
- Deep Reviewer can be instantiated successfully
- All required components (APIManager, TextExtractor) working
- Required files present:
  - ✅ Gap analysis report
  - ✅ Deep review directions  
  - ✅ Version history
  - ✅ Papers folder (though empty)
  - ❌ Research database (expected location issue)

**To Run Manually**:
```bash
# Method 1: As module
python -m literature_review.reviewers.deep_reviewer

# Method 2: Import in Python
from literature_review.reviewers.deep_reviewer import main
main()
```

**Test Script Created**: `test_deep_reviewer_instantiation.py`

---

### ✅ Task 2: User Input Selection - FIXED
**Status**: Fixed and validated

**Issues Found**:
1. ❌ Hardcoded prompt range (1-6) didn't match actual options (1-10)
2. ❌ Metadata sections (Framework_Overview, Cross_Cutting_Requirements, Success_Criteria) shown as options
3. ❌ User could select non-analyzable sections

**Fixes Applied**:
- ✅ Removed metadata sections from user menu
- ✅ Dynamic prompt range: Now shows (1-7) for 7 analyzable pillars
- ✅ Simplified selection logic - no metadata sections visible
- ✅ Clear pillar names without confusing "(metadata - skip)" tags

**New User Experience**:
```
--- No new data detected ---
What would you like to re-assess?
  1. Pillar 1
  2. Pillar 2
  3. Pillar 3
  4. Pillar 4
  5. Pillar 5
  6. Pillar 6
  7. Pillar 7

  ALL - Run analysis on all pillars (one pass)
  DEEP - Run iterative deep-review loop on all pillars
  NONE - Exit (default)

Enter choice (1-7, ALL, DEEP, NONE):
```

**Test Script Created**: `test_user_input_selection.py`

---

### 🔄 Task 3: Web Dashboard Testing - READY FOR MANUAL
**Status**: Automated tests prepared, manual testing needed

**Dashboard Status**:
- Server configured to run on http://localhost:8000
- FastAPI backend with Uvicorn
- WebSocket support enabled
- File: `webdashboard/app.py`

**Manual Testing Checklist**:
See `DASHBOARD_SMOKE_TEST.md` for comprehensive checklist

---

## Quick Start for Manual Dashboard Testing

### Step 1: Start Dashboard
```bash
cd /workspaces/Literature-Review
bash run_dashboard.sh
```

Expected output:
```
Starting Literature Review Dashboard...
Port: 8000
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: Application startup complete
```

### Step 2: Test Basic Access

#### In Web Browser:
1. Open: http://localhost:8000
2. Verify homepage loads
3. Check for any console errors (F12 → Console)

#### Using curl (Terminal):
```bash
# Health check
curl http://localhost:8000/api/health

# Jobs list
curl http://localhost:8000/api/jobs

# Gap analysis
curl http://localhost:8000/api/analysis/gaps

# Pillars (should return 7)
curl http://localhost:8000/api/analysis/pillars

# Recommendations (should return 97)
curl http://localhost:8000/api/analysis/recommendations
```

### Step 3: Test Core Workflows

#### Workflow 1: View Gap Analysis
1. Navigate to gap analysis page
2. Verify 7 pillars displayed
3. Check visualizations load
4. Verify data matches `gap_analysis_output/` files

#### Workflow 2: View Recommendations  
1. Navigate to recommendations page
2. Verify 97 recommendations shown
3. Check priority levels (CRITICAL, HIGH, MEDIUM)
4. Verify database-specific guidance present

#### Workflow 3: Job Management (if implemented)
1. Try creating a new analysis job
2. Check job status updates
3. Verify job completion
4. Check output files generated

### Step 4: Test File Uploads (if implemented)
1. Upload a test PDF
2. Verify file validation works
3. Check file appears in system
4. Test with invalid file types

### Step 5: Error Handling
1. Try invalid API requests
2. Test with missing files
3. Check error messages are user-friendly
4. Verify system recovers gracefully

---

## Known Issues & Limitations

### Current Known Issues:
1. **Research Database Location**:
   - Expected: `data/neuromorphic-research_database.csv`
   - Actual: Not found
   - Impact: Deep Reviewer may not have full data access
   - Fix: Run journal reviewer to generate database

2. **No PDFs in Papers Folder**:
   - Location: `data/raw/`
   - Count: 0 PDFs
   - Impact: Deep Reviewer cannot extract evidence
   - Fix: Add PDF files to `data/raw/` directory

3. **Dashboard WebSocket Features**:
   - Real-time updates not tested
   - Progress monitoring needs validation
   - Log streaming needs verification

### Non-Issues (By Design):
1. Metadata sections not selectable in orchestrator ✅
2. Only 7 analyzable pillars (3 metadata sections excluded) ✅  
3. Gap-closing recommendations count may vary based on analysis ✅

---

## Test Environment

**Date**: November 16, 2025
**Branch**: main
**Commit**: 507b5c9 (Production-ready pipeline)
**Python**: 3.12.1
**Platform**: Ubuntu 24.04.3 LTS (Dev Container)

**Key Files**:
- ✅ `pillar_definitions.json` - 10 sections (7 analyzable)
- ✅ `gap_analysis_output/` - 16 files generated
- ✅ `orchestrator_state.json` - 99KB checkpoint
- ✅ `review_version_history.json` - 5 papers
- ✅ `SMOKE_TEST_REPORT.md` - Production readiness assessment

---

## Smoke Test Execution Log

### Pre-Smoke Test
- [x] All code synced with `origin/main`
- [x] Production-ready commit pushed
- [x] Deep Reviewer instantiation verified
- [x] User input selection fixed
- [ ] Dashboard manual testing (IN PROGRESS)

### Post-Smoke Test
- [ ] All critical issues documented
- [ ] Fix PRs created for any blockers
- [ ] Dashboard approved for user access
- [ ] Documentation updated

---

## Next Steps

1. **Complete Manual Dashboard Testing**:
   - Use checklist in `DASHBOARD_SMOKE_TEST.md`
   - Test all API endpoints
   - Verify UI/UX functionality
   - Document any issues found

2. **Address Any Issues**:
   - Create GitHub issues for bugs
   - Prioritize critical vs. nice-to-have fixes
   - Update documentation as needed

3. **User Acceptance Testing**:
   - Provide access to stakeholders
   - Gather feedback on usability
   - Iterate based on user input

4. **Production Deployment**:
   - Configure production environment
   - Set up monitoring/alerting
   - Deploy with proper security settings

---

## Questions for Manual Tester

Please answer these as you test:

1. **Dashboard Accessibility**:
   - [ ] Can you access http://localhost:8000?
   - [ ] Does the homepage load without errors?
   - [ ] Are there any console errors (check browser dev tools)?

2. **Data Display**:
   - [ ] Do you see gap analysis data?
   - [ ] Are visualizations rendering correctly?
   - [ ] Is the data accurate compared to output files?

3. **User Experience**:
   - [ ] Is the interface intuitive?
   - [ ] Are error messages helpful?
   - [ ] Can you complete workflows without confusion?

4. **Performance**:
   - [ ] Do pages load quickly (< 3 seconds)?
   - [ ] Are there any laggy interactions?
   - [ ] Does the dashboard handle large datasets?

5. **Issues Encountered**:
   - What broke? ___________
   - What was confusing? ___________
   - What's missing? ___________

---

**Tester**: _________________ 
**Date**: _________________
**Sign-off**: [ ] Approved for Production / [ ] Needs Fixes
