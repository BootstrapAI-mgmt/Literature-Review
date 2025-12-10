# CI/CD Workflows Guide

**Last Updated:** 2025-12-10  
**Owner:** @cicd  
**Status:** Current

---

## Overview

This document describes the GitHub Actions CI/CD workflows that automate testing, validation, and quality assurance for the Literature Review Automation System.

---

## Workflow Inventory

### 1. Integration Tests (`integration-tests.yml`)

**Trigger:** Push/PR to `main`  
**Purpose:** Run unit, component, and integration tests on every code change  
**Timeout:** 30 minutes

| Step | Description |
|------|-------------|
| Checkout | Clone repository |
| Setup Python | Python 3.12 |
| Cache Dependencies | pip cache for faster builds |
| Install Dependencies | `requirements.txt`, `requirements-dev.txt`, `requirements-dashboard.txt` |
| Unit Tests | `pytest -m unit` |
| Component Tests | `pytest -m component` |
| Integration Tests | `pytest -m integration` |
| Coverage Upload | Codecov integration |

**Secrets Required:**
- None (tests use mocks)

**Artifacts:** Coverage reports to Codecov

---

### 2. E2E Tests - Nightly (`e2e-tests.yml`)

**Trigger:** Scheduled daily at 2:00 AM UTC  
**Purpose:** Full end-to-end pipeline tests with real API calls  
**Timeout:** 120 minutes

| Step | Description |
|------|-------------|
| Checkout | Clone repository |
| Setup Python | Python 3.12 |
| Install Dependencies | `requirements.txt`, `requirements-dev.txt` |
| Run E2E Tests | `pytest -m e2e` (excludes webui tests) |
| Upload Artifacts | Test results, logs, generated outputs |

**Secrets Required:**
- `GEMINI_API_KEY` - For AI model API calls

**Artifacts:**
- `gap_analysis_output/` - Generated analysis results
- `generated_plots/` - Visualization outputs
- `*.log` - Execution logs

---

### 3. Dashboard E2E Tests (`dashboard-e2e-tests.yml`)

**Trigger:** Push/PR to `main` affecting `webdashboard/` or `tests/webui/`  
**Purpose:** Browser-based testing of the web dashboard  
**Timeout:** 15 minutes

| Step | Description |
|------|-------------|
| Checkout | Clone repository |
| Setup Python | Python 3.12 |
| Cache Dependencies | pip cache |
| Install Dependencies | All requirements |
| Install Playwright | Chromium browser for UI testing |
| Start Dashboard | Background process on localhost:8000 |
| Health Check | Verify dashboard started |
| Run Dashboard E2E | `pytest -m e2e_dashboard` |
| Upload Screenshots | On failure, save screenshots |
| Upload Reports | Test reports and coverage |
| Stop Dashboard | Cleanup |

**Secrets Required:**
- `DASHBOARD_API_KEY` (test value used)

**Artifacts:**
- `test-results/` - Playwright test artifacts
- `*.png` - Failure screenshots
- `htmlcov/` - Coverage reports

---

## Action Version Policy

All GitHub Actions must use current, supported versions. The project maintains:

| Action | Minimum Version | Purpose |
|--------|-----------------|---------|
| `actions/checkout` | v4 | Repository checkout |
| `actions/setup-python` | v5 | Python environment |
| `actions/cache` | v4 | Dependency caching |
| `actions/upload-artifact` | v4 | Artifact storage |
| `codecov/codecov-action` | v5 | Coverage reporting |

**Update Policy:** Monitor [GitHub Actions Changelog](https://github.blog/changelog/) for deprecation notices. Action versions should be updated within 30 days of deprecation announcements.

---

## Test Markers Reference

Tests are organized using pytest markers:

| Marker | Workflow | Description |
|--------|----------|-------------|
| `@pytest.mark.unit` | integration-tests | Pure function tests, fast |
| `@pytest.mark.component` | integration-tests | Single component with mocks |
| `@pytest.mark.integration` | integration-tests | Multi-component, no network |
| `@pytest.mark.e2e` | e2e-tests | Full pipeline, real APIs |
| `@pytest.mark.e2e_dashboard` | dashboard-e2e-tests | Browser-based UI tests |

---

## Troubleshooting

### Common Issues

#### "Resource not accessible by integration"
- **Cause:** Insufficient permissions for workflow dispatch
- **Fix:** Ensure repository has Actions enabled and secrets configured

#### "Deprecated action version"
- **Cause:** GitHub has deprecated an action version
- **Fix:** Update action versions in workflow files (see Action Version Policy)

#### E2E tests timing out
- **Cause:** API rate limits or slow responses
- **Fix:** Check GEMINI_API_KEY validity; review rate limiting

#### Dashboard health check fails
- **Cause:** Port conflict or startup error
- **Fix:** Check app.py logs; ensure port 8000 available

---

## Adding New Workflows

When adding new CI/CD workflows:

1. Create workflow file in `.github/workflows/`
2. Update this documentation
3. Add appropriate test markers to `pytest.ini`
4. Configure required secrets in repository settings
5. Update `documentation_matrix.json` with staleness indicators

---

## Related Documentation

- [Testing Guide](./TESTING_GUIDE.md) - Test writing best practices
- [Smoke Testing Best Practices](./SMOKE_TESTING_BEST_PRACTICES.md) - Smoke test patterns
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Production deployment
- [Integration E2E Testing Assessment](./assessments/INTEGRATION_E2E_TESTING_ASSESSMENT.md) - Test strategy analysis

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-12-10 | Initial documentation; fixed deprecated action versions | @cicd |
