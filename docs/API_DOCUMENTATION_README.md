# API Documentation - Quick Start Guide

This guide helps you get started with the Literature Review Dashboard API documentation.

---

## 📚 Documentation Overview

The API documentation is available in multiple formats to suit different needs:

### 1. Interactive Documentation (Recommended)
**Best for:** Exploring the API, testing endpoints, learning workflows

**Swagger UI:** http://localhost:5001/api/docs
- Interactive "Try it out" functionality
- Live request/response testing
- Automatic request generation
- Authentication support

**ReDoc:** http://localhost:5001/api/redoc
- Three-panel responsive layout
- Search functionality
- Print-friendly format
- Clean, professional appearance

### 2. Reference Documentation
**Best for:** Integration, development, detailed specifications

**[API_REFERENCE.md](./API_REFERENCE.md)** (27 KB)
- Complete endpoint documentation
- Request/response examples
- Authentication guide
- Error codes reference
- WebSocket documentation
- Best practices

### 3. Client SDK Guide
**Best for:** Building applications, quick integration

**[CLIENT_SDK.md](./CLIENT_SDK.md)** (25 KB)
- Python client implementation
- JavaScript/Node.js client implementation
- Complete workflow examples
- Error handling patterns
- Postman collection guide

### 4. Implementation Summary
**Best for:** Understanding the implementation

**[API_DOCUMENTATION_SUMMARY.md](./API_DOCUMENTATION_SUMMARY.md)** (12 KB)
- Implementation details
- Test results
- File changes
- Usage instructions

---

## 🚀 Quick Start

### Step 1: Start the Dashboard
```bash
# From repository root
./run_dashboard.sh

# Or manually
cd webdashboard
python app.py
```

### Step 2: Access Documentation
Open your browser to:
- **Swagger UI:** http://localhost:5001/api/docs
- **ReDoc:** http://localhost:5001/api/redoc

### Step 3: Try an Endpoint
1. Open Swagger UI
2. Expand any endpoint (e.g., `GET /health`)
3. Click "Try it out"
4. Click "Execute"
5. View the response

---

## 📖 Common Workflows

### Upload and Analyze Papers

**Using cURL:**
```bash
# 1. Upload PDF
curl -X POST "http://localhost:5001/api/upload" \
  -H "X-API-KEY: dev-key-change-in-production" \
  -F "file=@paper.pdf"

# 2. Configure job
curl -X POST "http://localhost:5001/api/jobs/{job_id}/configure" \
  -H "X-API-KEY: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"pillar_selections": ["ALL"], "run_mode": "ONCE"}'

# 3. Start job
curl -X POST "http://localhost:5001/api/jobs/{job_id}/start" \
  -H "X-API-KEY: dev-key-change-in-production"

# 4. Check status
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/{job_id}
```

**Using Python:**
```python
from literature_review_client import LiteratureReviewClient

client = LiteratureReviewClient(
    base_url="http://localhost:5001",
    api_key="dev-key-change-in-production"
)

# Upload
result = client.upload_pdf("paper.pdf")
job_id = result['job_id']

# Configure and start
client.configure_job(job_id, pillar_selections=["ALL"])
client.start_job(job_id)

# Monitor
status = client.get_job(job_id)
print(f"Status: {status['status']}")
```

### Download Results
```bash
# List available results
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/{job_id}/results

# Download all as ZIP
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/{job_id}/results/download/all \
  -o results.zip
```

---

## 🔑 Authentication

All API endpoints (except `/health`) require authentication via API key.

**Header:** `X-API-KEY`  
**Default (Dev):** `dev-key-change-in-production`

**Example:**
```bash
curl -H "X-API-KEY: your-api-key" http://localhost:5001/api/jobs
```

**⚠️ Security:** Always change the default API key in production!

**Set via environment variable:**
```bash
export DASHBOARD_API_KEY="your-secure-api-key"
./run_dashboard.sh
```

---

## 📊 API Endpoints Summary

### Papers (4 endpoints)
- `POST /api/upload` - Upload single PDF
- `POST /api/upload/batch` - Upload multiple PDFs
- `POST /api/upload/confirm` - Confirm batch upload
- `GET /api/download/{job_id}` - Download original PDF

### Jobs (7 endpoints)
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{job_id}` - Get job details
- `POST /api/jobs/{job_id}/configure` - Configure job
- `POST /api/jobs/{job_id}/start` - Start job
- `POST /api/jobs/{job_id}/retry` - Retry failed job
- `GET /api/jobs/{job_id}/progress-history` - Progress timeline
- `GET /api/jobs/{job_id}/progress-history.csv` - Export as CSV

### Results (7 endpoints)
- `GET /api/jobs/{job_id}/results` - List result files
- `GET /api/jobs/{job_id}/results/{file_path}` - Download file
- `GET /api/jobs/{job_id}/results/download/all` - Download ZIP
- `GET /api/jobs/{job_id}/proof-scorecard` - Proof summary
- `GET /api/jobs/{job_id}/cost-summary` - Cost breakdown
- `GET /api/jobs/{job_id}/sufficiency-summary` - Evidence sufficiency
- `GET /api/jobs/{job_id}/files/{filepath}` - Access output files

### Analysis (3 endpoints)
- `GET /api/compare-jobs/{job_id_1}/{job_id_2}` - Compare jobs
- `POST /api/suggest-field` - Auto-suggest field
- `GET /api/field-presets` - Get field presets

### Logs (1 endpoint)
- `GET /api/logs/{job_id}` - Get job logs

### Interactive (1 endpoint)
- `POST /api/prompts/{prompt_id}/respond` - Respond to prompt

### System (1 endpoint)
- `GET /health` - Health check

**Total:** 24 endpoints

---

## 🛠️ Tools & Integrations

### Postman
Import the OpenAPI specification:
1. Open Postman
2. Click **Import**
3. Select **Link**
4. Enter: `http://localhost:5001/api/openapi.json`
5. Click **Import**

### Client SDK Generation
Download the OpenAPI spec:
```bash
curl http://localhost:5001/api/openapi.json > openapi.json
```

Generate clients:
- **Python:** Use `openapi-generator-cli` or `datamodel-code-generator`
- **JavaScript:** Use `openapi-generator-cli`
- **Java/Go/Rust:** Use `openapi-generator`

### Example: Python Client Generation
```bash
# Install generator
pip install openapi-python-client

# Generate client
openapi-python-client generate --url http://localhost:5001/api/openapi.json

# Or use our pre-built client from CLIENT_SDK.md
```

---

## 📋 Testing

Run the documentation test suite:
```bash
python tests/test_api_documentation.py
```

Expected output:
```
============================================================
API Documentation Test Suite
============================================================

✓ 24 endpoints documented
✓ 24 endpoints properly tagged
✓ 11 data schemas defined
✓ All documentation files validated
✓ 100% endpoint coverage
✓ 100% schema coverage

============================================================
✅ ALL TESTS PASSED
============================================================
```

---

## 🔍 Troubleshooting

### Swagger UI Not Loading
- **Check server is running:** `curl http://localhost:5001/health`
- **Check CDN access:** Ensure internet connectivity for CDN resources
- **Try ReDoc instead:** http://localhost:5001/api/redoc

### API Key Issues
- **401 Unauthorized:** Check X-API-KEY header is set correctly
- **Default key:** `dev-key-change-in-production`
- **Custom key:** Set via `DASHBOARD_API_KEY` environment variable

### OpenAPI Schema Issues
- **Verify generation:** `curl http://localhost:5001/api/openapi.json`
- **Run tests:** `python tests/test_api_documentation.py`
- **Check logs:** Look for errors in server output

---

## 📚 Additional Resources

### Documentation Files
- **[API_REFERENCE.md](./API_REFERENCE.md)** - Complete API reference
- **[CLIENT_SDK.md](./CLIENT_SDK.md)** - Client SDK guide
- **[API_DOCUMENTATION_SUMMARY.md](./API_DOCUMENTATION_SUMMARY.md)** - Implementation summary
- **[USER_MANUAL.md](./USER_MANUAL.md)** - User manual
- **[DASHBOARD_GUIDE.md](./DASHBOARD_GUIDE.md)** - Dashboard guide

### Links
- **GitHub Repository:** https://github.com/BootstrapAI-mgmt/Literature-Review
- **OpenAPI Specification:** http://localhost:5001/api/openapi.json
- **Swagger UI:** http://localhost:5001/api/docs
- **ReDoc:** http://localhost:5001/api/redoc

### Related Issues
- **ENHANCE-DOC-2:** API Reference Documentation (this implementation)
- **Task Cards:** See `/task-cards` directory

---

## ✅ Validation Checklist

- [x] OpenAPI 3.1.0 specification generated
- [x] Swagger UI accessible at `/api/docs`
- [x] ReDoc accessible at `/api/redoc`
- [x] All 24 endpoints documented
- [x] All endpoints have examples
- [x] All endpoints have error responses
- [x] Authentication documented
- [x] WebSocket endpoints documented
- [x] Client SDKs provided (Python, JavaScript)
- [x] cURL examples provided
- [x] Postman import guide provided
- [x] Test suite created and passing
- [x] Security scan passed (0 vulnerabilities)

---

## 🎯 Next Steps

1. **Explore the API:** Open Swagger UI and try the endpoints
2. **Read the guides:** Review API_REFERENCE.md and CLIENT_SDK.md
3. **Build an integration:** Use the client SDK examples
4. **Provide feedback:** Open issues for documentation improvements

---

**Last Updated:** November 18, 2024  
**Version:** 2.0.0  
**Status:** ✅ Complete
