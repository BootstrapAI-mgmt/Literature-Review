# Web Dashboard Smoke Test Checklist

**Date**: November 16, 2025  
**Dashboard URL**: http://localhost:8000  
**Status**: ✅ AUTOMATED TESTS PASSED - Ready for Manual Testing  
**API Key**: `dev-key-change-in-production`

---

## ✅ Automated Test Results (Completed)

| Test | Status | Details |
|------|--------|---------|
| Homepage Loading | ✅ PASS | 200 OK, 21KB response |
| Health Endpoint | ✅ PASS | `/health` returns `{"status": "healthy", "version": "1.0.0"}` |
| Jobs List (Auth) | ✅ PASS | `/api/jobs` with X-API-KEY header |
| Auth Required | ✅ PASS | Returns 401 without API key |
| File Upload | ✅ PASS | Creates job: `a3bfbbfb-048f-4850-a561-b0dc240e398c` |
| Job Details | ✅ PASS | `/api/jobs/{job_id}` accessible |
| Static Files | ✅ PASS | `/static/` route configured |

### API Authentication

All `/api/*` endpoints require authentication header:
```bash
X-API-KEY: dev-key-change-in-production
```

---

## Pre-Test Setup
- [x] Dashboard server started successfully
- [x] Server running on http://0.0.0.0:8000
- [x] Automated API tests passed
- [ ] Browser access confirmed by user

## 1. Basic Connectivity Tests

### 1.1 Homepage Access
- [ ] Navigate to http://localhost:8000
- [ ] Page loads without errors
- [ ] HTML renders correctly
- [ ] No console errors in browser dev tools

### 1.2 API Health Check
- [ ] GET /api/health returns 200
- [ ] Response contains status information
- [ ] No error messages in response

## 2. API Endpoint Tests

### 2.1 Job Management Endpoints

#### GET /api/jobs
- [ ] Endpoint accessible
- [ ] Returns JSON array
- [ ] Status code: 200
- [ ] Response format matches expected schema

#### POST /api/jobs
- [ ] Can create new job
- [ ] Accepts job configuration JSON
- [ ] Returns job ID
- [ ] Status code: 201 or 200

#### GET /api/jobs/{job_id}
- [ ] Can retrieve specific job
- [ ] Returns job details
- [ ] 404 for non-existent jobs

#### DELETE /api/jobs/{job_id}
- [ ] Can delete job
- [ ] Returns success confirmation
- [ ] Job no longer in list

### 2.2 File Management Endpoints

#### GET /api/files
- [ ] Lists available files
- [ ] Returns file metadata
- [ ] Status code: 200

#### POST /api/files/upload
- [ ] Can upload PDF file
- [ ] File validation works
- [ ] Returns upload confirmation

#### GET /api/files/{filename}
- [ ] Can download files
- [ ] Correct content-type headers
- [ ] File serves correctly

### 2.3 Analysis Endpoints

#### GET /api/analysis/gaps
- [ ] Returns gap analysis data
- [ ] JSON format correct
- [ ] Contains expected fields

#### GET /api/analysis/pillars
- [ ] Returns pillar information
- [ ] All 7 pillars listed
- [ ] Metadata sections excluded

#### GET /api/analysis/recommendations
- [ ] Returns search recommendations
- [ ] Priority levels included
- [ ] Database-specific guidance present

## 3. UI/UX Manual Testing

### 3.1 Navigation
- [ ] All navigation links work
- [ ] Back button functions correctly
- [ ] Breadcrumbs (if present) accurate

### 3.2 Job Creation Flow
- [ ] Form validation works
- [ ] Required fields enforced
- [ ] Error messages clear
- [ ] Success messages displayed
- [ ] Redirects work correctly

### 3.3 File Upload
- [ ] Drag-and-drop works (if implemented)
- [ ] File picker works
- [ ] Upload progress indicator
- [ ] File size validation
- [ ] File type validation (PDF only)

### 3.4 Results Display
- [ ] Gap analysis visualizations load
- [ ] Charts render correctly
- [ ] Tables formatted properly
- [ ] Data exports work (if implemented)

### 3.5 Job Monitoring
- [ ] Job status updates
- [ ] Progress indicators work
- [ ] Log streaming (if implemented)
- [ ] WebSocket connections stable

## 4. Error Handling

### 4.1 Network Errors
- [ ] Graceful handling of API failures
- [ ] Retry mechanisms work
- [ ] User-friendly error messages

### 4.2 Validation Errors
- [ ] Client-side validation catches issues
- [ ] Server-side validation works
- [ ] Error messages actionable

### 4.3 Edge Cases
- [ ] Empty state displays correctly
- [ ] Large file uploads handled
- [ ] Concurrent requests work
- [ ] Session timeout handled

## 5. Performance Tests

### 5.1 Load Times
- [ ] Homepage loads < 2 seconds
- [ ] API responses < 500ms
- [ ] Visualizations render < 3 seconds

### 5.2 Resource Usage
- [ ] No memory leaks
- [ ] CPU usage reasonable
- [ ] Network requests optimized

## 6. Integration Tests

### 6.1 Pipeline Integration
- [ ] Can trigger journal review
- [ ] Can trigger judge analysis
- [ ] Can trigger gap analysis
- [ ] Can view pipeline status

### 6.2 Data Synchronization
- [ ] Version history displays correctly
- [ ] Database updates reflected in UI
- [ ] Checkpoint state accurate

## 7. Security Tests

### 7.1 Authentication (if implemented)
- [ ] Login/logout works
- [ ] Session management secure
- [ ] Unauthorized access blocked

### 7.2 Input Sanitization
- [ ] XSS protection active
- [ ] SQL injection prevented
- [ ] File upload restrictions enforced

### 7.3 API Security
- [ ] CORS configured correctly
- [ ] Rate limiting active
- [ ] API keys validated

## 8. Browser Compatibility

### 8.1 Chrome/Edge
- [ ] All features work
- [ ] UI renders correctly
- [ ] No console errors

### 8.2 Firefox
- [ ] All features work
- [ ] UI renders correctly
- [ ] No console errors

### 8.3 Safari (if available)
- [ ] All features work
- [ ] UI renders correctly
- [ ] No console errors

## 9. Responsive Design

### 9.1 Desktop (1920x1080)
- [ ] Layout appropriate
- [ ] All elements visible
- [ ] No horizontal scroll

### 9.2 Tablet (768x1024)
- [ ] Responsive layout active
- [ ] Touch interactions work
- [ ] Readable text size

### 9.3 Mobile (375x667)
- [ ] Mobile layout active
- [ ] Navigation accessible
- [ ] Forms usable

## Test Execution Commands

```bash
# Start Dashboard (if not running)
cd /workspaces/Literature-Review
bash run_dashboard.sh

# Dashboard will be at: http://localhost:8000

# Test API Endpoints (in separate terminal)
# Note: All /api/* endpoints require X-API-KEY header

# Health check (no auth required)
curl http://localhost:8000/health

# List jobs (requires auth)
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:8000/api/jobs

# Upload file (requires auth)
curl -X POST \
  -H "X-API-KEY: dev-key-change-in-production" \
  -F "file=@path/to/your.pdf" \
  http://localhost:8000/api/upload

# Get job details (requires auth)
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:8000/api/jobs/<job_id>

# Check dashboard logs
tail -f /workspaces/Literature-Review/dashboard.log
```

### Python API Test Script

```python
import requests

BASE_URL = 'http://localhost:8000'
API_KEY = 'dev-key-change-in-production'
HEADERS = {'X-API-KEY': API_KEY}

# List all jobs
response = requests.get(f'{BASE_URL}/api/jobs', headers=HEADERS)
print(response.json())

# Upload a file
with open('paper.pdf', 'rb') as f:
    files = {'file': ('paper.pdf', f, 'application/pdf')}
    response = requests.post(f'{BASE_URL}/api/upload', 
                            files=files, 
                            headers=HEADERS)
    print(response.json())
```

## Workspace Structure

The dashboard creates the following workspace:

```
workspace/
├── uploads/           # Uploaded PDF files
├── jobs/              # Job metadata JSON files
├── status/            # Job status updates
└── logs/              # Job execution logs
```

## Issues Found

### Critical Issues
_(To be filled during testing)_

### Minor Issues
_(To be filled during testing)_

### Enhancement Opportunities
_(To be filled during testing)_

## Sign-off

- [ ] All critical tests passed
- [ ] No blocking issues found
- [ ] Dashboard ready for user testing
- [ ] Documentation updated

**Tester**: _________________  
**Date**: _________________  
**Notes**: _________________
