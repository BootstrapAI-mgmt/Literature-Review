# ENHANCE-TEST-1: End-to-End Dashboard Tests

**Status:** PARTIALLY IMPLEMENTED  
**Priority:** 🟡 Medium  
**Effort Estimate:** 4 hours (reduced from 8 hours - interactive prompt tests already complete)  
**Category:** Testing  
**Created:** November 17, 2025  
**Related PRs:** #36 (Input Handling), #38 (Progress Monitoring), #39 (Results API), #46 (Interactive Prompts)

---

## 📋 Overview

Add comprehensive end-to-end tests covering full dashboard workflows from PDF upload through job execution to results viewing.

**Current State:**
- ✅ Interactive prompts tested (PR #46, 10 tests)
- ✅ WebSocket communication tested (Phase 3)
- ✅ Progress monitoring tested (Phase 3)
- ❌ No full workflow tests (upload → job → results)
- ❌ No error handling tests

**Remaining Coverage Needed:**
- Upload PDFs → verify database insertion
- Start job → monitor progress → check completion
- View results → download outputs
- Error scenarios (network failures, invalid inputs)

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] E2E test: Upload PDFs → verify in database
- [ ] E2E test: Start job → job completes successfully
- [ ] E2E test: View job results → download ZIP
- [ ] E2E test: Error handling (invalid PDF, job failure)

### Should Have
- [ ] E2E test: Multiple concurrent jobs
- [ ] E2E test: Job cancellation mid-execution
- [ ] E2E test: Resume failed job
- [ ] Performance test: 100 jobs in database

### Nice to Have
- [ ] Visual regression testing (screenshot comparison)
- [ ] Accessibility testing (WCAG compliance)
- [ ] Mobile responsiveness tests
- [ ] Browser compatibility tests (Chrome, Firefox, Safari)

---

## 🛠️ Technical Implementation

### 1. Test Framework Setup

**Dependencies:** `requirements-dev.txt`

```
pytest>=7.4.0
pytest-asyncio>=0.21.0  # Already added in PR #46
playwright>=1.40.0  # For E2E browser testing
pytest-playwright>=0.4.3
requests>=2.31.0
```

**Installation:**
```bash
pip install -r requirements-dev.txt
playwright install  # Install browser drivers
```

### 2. E2E Test Suite

**New File:** `tests/e2e/test_dashboard_workflows.py`

```python
import pytest
from playwright.sync_api import Page, expect
import os
import time
import json

@pytest.fixture(scope="session")
def dashboard_url():
    """Dashboard URL (assumes running locally)"""
    return "http://localhost:5001"

@pytest.fixture
def test_pdf():
    """Create a test PDF file"""
    pdf_path = "tests/fixtures/test_paper.pdf"
    # Ensure test PDF exists
    assert os.path.exists(pdf_path), f"Test PDF not found: {pdf_path}"
    return pdf_path

class TestDashboardWorkflows:
    """End-to-end tests for full dashboard workflows"""
    
    def test_upload_pdf_workflow(self, page: Page, dashboard_url, test_pdf):
        """Test PDF upload → database verification"""
        # Navigate to dashboard
        page.goto(dashboard_url)
        
        # Click upload button
        page.click("button:has-text('Upload Papers')")
        
        # Upload file
        page.set_input_files("input[type='file']", test_pdf)
        
        # Submit upload
        page.click("button:has-text('Upload')")
        
        # Wait for success message
        expect(page.locator(".alert-success")).to_be_visible(timeout=5000)
        expect(page.locator(".alert-success")).to_contain_text("uploaded successfully")
        
        # Verify paper appears in database view
        page.click("a:has-text('Papers')")
        expect(page.locator(".paper-list")).to_contain_text("test_paper.pdf")
    
    def test_start_job_workflow(self, page: Page, dashboard_url):
        """Test job creation → execution → completion"""
        page.goto(dashboard_url)
        
        # Navigate to job creation
        page.click("button:has-text('New Job')")
        
        # Fill job configuration
        page.fill("input[name='job_name']", "E2E Test Job")
        page.select_option("select[name='pillar']", "ALL")
        page.select_option("select[name='run_mode']", "ONCE")
        
        # Start job
        page.click("button:has-text('Start Job')")
        
        # Wait for job to appear in list
        expect(page.locator(".job-item")).to_be_visible(timeout=3000)
        
        # Verify job status
        job_item = page.locator(".job-item").first
        expect(job_item.locator(".status-badge")).to_contain_text("running")
        
        # Wait for completion (or timeout)
        page.wait_for_selector(".status-badge:has-text('completed')", timeout=60000)
        
        # Verify completion
        expect(job_item.locator(".status-badge")).to_contain_text("completed")
    
    def test_view_results_workflow(self, page: Page, dashboard_url):
        """Test viewing job results → download outputs"""
        page.goto(dashboard_url)
        
        # Find completed job
        page.click(".job-item:has(.status-badge:has-text('completed'))")
        
        # Click "View Results"
        page.click("button:has-text('View Results')")
        
        # Wait for results modal
        expect(page.locator("#resultsModal")).to_be_visible(timeout=3000)
        
        # Verify results content
        expect(page.locator("#resultsModal")).to_contain_text("Gap Coverage")
        expect(page.locator("#resultsModal")).to_contain_text("Completeness")
        
        # Download ZIP
        with page.expect_download() as download_info:
            page.click("button:has-text('Download ZIP')")
        
        download = download_info.value
        assert download.suggested_filename.endswith(".zip")
        
        # Verify ZIP contains files
        import zipfile
        with zipfile.ZipFile(download.path()) as zf:
            assert len(zf.namelist()) > 0
    
    def test_error_handling_invalid_pdf(self, page: Page, dashboard_url):
        """Test error handling for invalid PDF upload"""
        page.goto(dashboard_url)
        
        # Try uploading non-PDF file
        page.click("button:has-text('Upload Papers')")
        page.set_input_files("input[type='file']", "tests/fixtures/invalid_file.txt")
        page.click("button:has-text('Upload')")
        
        # Should show error
        expect(page.locator(".alert-danger")).to_be_visible(timeout=3000)
        expect(page.locator(".alert-danger")).to_contain_text("Invalid file type")
    
    def test_job_cancellation(self, page: Page, dashboard_url):
        """Test cancelling a running job"""
        page.goto(dashboard_url)
        
        # Start a job
        page.click("button:has-text('New Job')")
        page.fill("input[name='job_name']", "Cancellation Test")
        page.click("button:has-text('Start Job')")
        
        # Wait for job to start
        expect(page.locator(".status-badge:has-text('running')")).to_be_visible(timeout=5000)
        
        # Click cancel
        page.click(".job-item button:has-text('Cancel')")
        
        # Confirm cancellation
        page.click("button:has-text('Confirm')")
        
        # Verify status changed to cancelled
        expect(page.locator(".status-badge:has-text('cancelled')")).to_be_visible(timeout=5000)
    
    def test_concurrent_jobs(self, page: Page, dashboard_url):
        """Test multiple jobs running concurrently"""
        page.goto(dashboard_url)
        
        # Start 3 jobs
        for i in range(3):
            page.click("button:has-text('New Job')")
            page.fill("input[name='job_name']", f"Concurrent Job {i+1}")
            page.click("button:has-text('Start Job')")
            time.sleep(1)  # Slight delay
        
        # Verify all 3 jobs exist
        job_items = page.locator(".job-item")
        expect(job_items).to_have_count(3)
        
        # Verify all are running or queued
        for i in range(3):
            status = job_items.nth(i).locator(".status-badge").text_content()
            assert status in ['running', 'queued', 'completed']
    
    def test_progress_monitoring(self, page: Page, dashboard_url):
        """Test real-time progress updates"""
        page.goto(dashboard_url)
        
        # Start job
        page.click("button:has-text('New Job')")
        page.click("button:has-text('Start Job')")
        
        # Wait for progress bar to appear
        expect(page.locator(".progress-bar")).to_be_visible(timeout=5000)
        
        # Verify progress increases
        initial_progress = int(page.locator(".progress-bar").get_attribute("aria-valuenow"))
        time.sleep(3)
        updated_progress = int(page.locator(".progress-bar").get_attribute("aria-valuenow"))
        
        assert updated_progress >= initial_progress
```

### 3. Performance Tests

**New File:** `tests/e2e/test_dashboard_performance.py`

```python
def test_large_job_list_performance(page: Page, dashboard_url):
    """Test dashboard performance with 100 jobs"""
    page.goto(dashboard_url)
    
    # Measure page load time
    start_time = time.time()
    page.wait_for_load_state("networkidle")
    load_time = time.time() - start_time
    
    assert load_time < 3.0, f"Page load too slow: {load_time:.2f}s"
    
    # Verify job list renders
    expect(page.locator(".job-item")).to_have_count(100, timeout=5000)

def test_large_pdf_upload(page: Page, dashboard_url):
    """Test uploading 50 PDFs at once"""
    page.goto(dashboard_url)
    
    pdf_files = [f"tests/fixtures/paper_{i}.pdf" for i in range(50)]
    
    page.click("button:has-text('Upload Papers')")
    page.set_input_files("input[type='file']", pdf_files)
    
    start_time = time.time()
    page.click("button:has-text('Upload')")
    
    # Wait for completion
    expect(page.locator(".alert-success")).to_be_visible(timeout=30000)
    
    upload_time = time.time() - start_time
    assert upload_time < 30.0, f"Upload too slow: {upload_time:.2f}s"
```

### 4. Configuration

**New File:** `pytest.ini` (enhance existing)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# E2E test markers
markers =
    e2e: End-to-end tests (requires running dashboard)
    slow: Slow tests (>10s)
    performance: Performance tests

# Playwright configuration
playwright_browser = chromium
playwright_headless = true
```

**Run E2E Tests:**
```bash
# Start dashboard first
python webdashboard/app.py &

# Run E2E tests
pytest tests/e2e/ -m e2e -v

# Run with browser visible (for debugging)
pytest tests/e2e/ -m e2e --headed
```

---

## 🧪 Testing Strategy

### Test Coverage Goals

- **Unit Tests**: 90%+ (already mostly achieved)
- **Integration Tests**: 80%+ (some gaps remain)
- **E2E Tests**: 70%+ (major workflows covered)

### Test Pyramid

```
      /\
     /  \  E2E Tests (70+ coverage)
    /____\
   /      \  Integration Tests (80+ coverage)
  /________\
 /          \  Unit Tests (90+ coverage)
/____________\
```

### CI/CD Integration

**GitHub Actions:** `.github/workflows/test.yml`

```yaml
name: Dashboard Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          playwright install
      
      - name: Run unit tests
        run: pytest tests/unit/ -v
      
      - name: Start dashboard
        run: |
          python webdashboard/app.py &
          sleep 5
      
      - name: Run E2E tests
        run: pytest tests/e2e/ -m e2e -v
      
      - name: Upload test reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: htmlcov/
```

---

## 📚 Documentation Updates

**File:** `docs/TESTING_GUIDE.md`

**New Content:**
```markdown
## Running End-to-End Tests

### Prerequisites

1. **Install Playwright:**
   ```bash
   pip install playwright pytest-playwright
   playwright install
   ```

2. **Start Dashboard:**
   ```bash
   python webdashboard/app.py
   ```

### Running Tests

**All E2E Tests:**
```bash
pytest tests/e2e/ -m e2e -v
```

**Specific Test:**
```bash
pytest tests/e2e/test_dashboard_workflows.py::TestDashboardWorkflows::test_upload_pdf_workflow -v
```

**With Browser Visible (Debug):**
```bash
pytest tests/e2e/ --headed --slowmo=1000
```

### Troubleshooting

**Dashboard not responding:**
- Verify dashboard running on http://localhost:5001
- Check firewall settings
- Review dashboard logs

**Playwright errors:**
- Reinstall browsers: `playwright install --force`
- Update dependencies: `pip install --upgrade playwright`
```

---

## ✅ Definition of Done

- [ ] Playwright installed and configured
- [ ] E2E test suite implemented (8+ tests)
- [ ] Upload → database verification test
- [ ] Start job → completion test
- [ ] View results → download test
- [ ] Error handling tests
- [ ] Concurrent jobs test
- [ ] Performance tests
- [ ] CI/CD integration (GitHub Actions)
- [ ] Documentation updated (TESTING_GUIDE.md)
- [ ] All tests passing
- [ ] Code review approved
- [ ] Merged to main branch
