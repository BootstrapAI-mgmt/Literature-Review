# ENHANCE-DOC-2: API Reference Documentation

**Status:** INLINE DOCS ONLY  
**Priority:** 🟢 Low  
**Effort Estimate:** 2 hours  
**Category:** Documentation  
**Created:** November 17, 2025  
**Related Docs:** README.md, USER_MANUAL.md

---

## 📋 Overview

Generate comprehensive API reference documentation using OpenAPI/Swagger specification for all dashboard REST endpoints.

**Current State:**
- ✅ Inline docstrings in Flask routes
- ✅ Basic README.md with usage examples
- ❌ No auto-generated API documentation
- ❌ No interactive API explorer (Swagger UI)
- ❌ No request/response examples

**Gap:** Developers cannot easily discover/test API endpoints without reading source code.

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] OpenAPI 3.0 specification generated
- [ ] Swagger UI integrated at `/api/docs`
- [ ] All endpoints documented (requests, responses, errors)
- [ ] Authentication guide (if applicable)

### Should Have
- [ ] Example requests/responses for each endpoint
- [ ] Error code reference (400, 401, 404, 500)
- [ ] Rate limiting documentation
- [ ] Pagination guide

### Nice to Have
- [ ] Postman collection export
- [ ] Client SDK generation (Python, JavaScript)
- [ ] Webhook documentation
- [ ] API versioning guide

---

## 🛠️ Technical Implementation

### 1. Install OpenAPI Tools

**Dependencies:** `requirements-dashboard.txt`

```
flask-swagger-ui>=4.11.1
flask-restx>=1.1.0  # OpenAPI support
```

**Install:**
```bash
pip install flask-swagger-ui flask-restx
```

### 2. Generate OpenAPI Specification

**New File:** `webdashboard/openapi_spec.py`

```python
"""
OpenAPI 3.0 specification for Literature Review Dashboard API
"""

from flask import Flask
from flask_restx import Api, Resource, fields, Namespace

# Initialize API
api = Api(
    title='Literature Review Dashboard API',
    version='2.0',
    description='REST API for managing literature review jobs, papers, and results',
    doc='/api/docs',  # Swagger UI location
    prefix='/api/v1'
)

# Namespaces
jobs_ns = Namespace('jobs', description='Job management operations')
papers_ns = Namespace('papers', description='Paper management operations')
results_ns = Namespace('results', description='Results and analysis operations')

# Models (Schemas)
paper_model = api.model('Paper', {
    'id': fields.String(required=True, description='Paper unique identifier'),
    'title': fields.String(required=True, description='Paper title'),
    'authors': fields.List(fields.String, description='List of author names'),
    'year': fields.Integer(description='Publication year'),
    'doi': fields.String(description='Digital Object Identifier'),
    'pdf_path': fields.String(description='Path to PDF file'),
    'upload_date': fields.DateTime(description='Upload timestamp')
})

job_model = api.model('Job', {
    'id': fields.String(required=True, description='Job unique identifier'),
    'name': fields.String(required=True, description='Job name'),
    'status': fields.String(description='Job status', enum=['queued', 'running', 'completed', 'failed', 'cancelled']),
    'pillar': fields.String(description='Analysis pillar or ALL'),
    'run_mode': fields.String(description='Run mode', enum=['ONCE', 'CONTINUOUS', 'INCREMENTAL']),
    'progress': fields.Float(description='Progress percentage (0-100)'),
    'created_at': fields.DateTime(description='Creation timestamp'),
    'completed_at': fields.DateTime(description='Completion timestamp')
})

gap_model = api.model('Gap', {
    'id': fields.String(required=True, description='Gap identifier'),
    'description': fields.String(required=True, description='Gap description'),
    'pillar': fields.String(description='Associated pillar'),
    'severity': fields.String(description='Severity level', enum=['critical', 'major', 'minor']),
    'coverage': fields.Float(description='Coverage percentage (0-100)'),
    'evidence_count': fields.Integer(description='Number of supporting evidence items')
})

# Error models
error_model = api.model('Error', {
    'error': fields.String(required=True, description='Error message'),
    'code': fields.Integer(required=True, description='HTTP status code'),
    'details': fields.Raw(description='Additional error details')
})

# Register namespaces
api.add_namespace(jobs_ns)
api.add_namespace(papers_ns)
api.add_namespace(results_ns)
```

### 3. Annotate Flask Routes

**Update:** `webdashboard/app.py`

```python
from flask_restx import Resource, fields
from webdashboard.openapi_spec import api, jobs_ns, job_model, error_model

@jobs_ns.route('/')
class JobList(Resource):
    @jobs_ns.doc('list_jobs')
    @jobs_ns.marshal_list_with(job_model)
    def get(self):
        """List all jobs"""
        return get_all_jobs()
    
    @jobs_ns.doc('create_job')
    @jobs_ns.expect(job_model)
    @jobs_ns.marshal_with(job_model, code=201)
    @jobs_ns.response(400, 'Validation Error', error_model)
    def post(self):
        """Create a new job"""
        data = api.payload
        return create_job(data), 201

@jobs_ns.route('/<string:job_id>')
@jobs_ns.param('job_id', 'The job identifier')
class Job(Resource):
    @jobs_ns.doc('get_job')
    @jobs_ns.marshal_with(job_model)
    @jobs_ns.response(404, 'Job not found', error_model)
    def get(self, job_id):
        """Get job by ID"""
        job = get_job_by_id(job_id)
        if not job:
            api.abort(404, f"Job {job_id} not found")
        return job
    
    @jobs_ns.doc('delete_job')
    @jobs_ns.response(204, 'Job deleted')
    @jobs_ns.response(404, 'Job not found', error_model)
    def delete(self, job_id):
        """Delete a job"""
        delete_job_by_id(job_id)
        return '', 204

@jobs_ns.route('/<string:job_id>/start')
class JobStart(Resource):
    @jobs_ns.doc('start_job')
    @jobs_ns.response(200, 'Job started', job_model)
    @jobs_ns.response(409, 'Job already running', error_model)
    def post(self, job_id):
        """Start a job"""
        return start_job(job_id)

@jobs_ns.route('/<string:job_id>/cancel')
class JobCancel(Resource):
    @jobs_ns.doc('cancel_job')
    @jobs_ns.response(200, 'Job cancelled', job_model)
    @jobs_ns.response(404, 'Job not found', error_model)
    def post(self, job_id):
        """Cancel a running job"""
        return cancel_job(job_id)
```

### 4. Swagger UI Integration

**Update:** `webdashboard/app.py`

```python
from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint
from webdashboard.openapi_spec import api

app = Flask(__name__)

# Initialize API
api.init_app(app)

# Swagger UI
SWAGGER_URL = '/api/docs'
API_SPEC_URL = '/api/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_SPEC_URL,
    config={
        'app_name': "Literature Review Dashboard API",
        'defaultModelsExpandDepth': 3,
        'defaultModelExpandDepth': 3
    }
)

app.register_blueprint(swaggerui_blueprint)

# Serve OpenAPI spec
@app.route('/api/swagger.json')
def swagger_spec():
    return api.__schema__
```

**Access Swagger UI:**
```
http://localhost:5001/api/docs
```

### 5. Full API Documentation

**New File:** `docs/API_REFERENCE.md`

```markdown
# API Reference

Base URL: `http://localhost:5001/api/v1`

---

## Authentication

Currently no authentication required. Future versions may use API keys.

```bash
# Example with API key (future)
curl -H "X-API-Key: your-api-key" http://localhost:5001/api/v1/jobs
```

---

## Endpoints

### Jobs

#### `GET /jobs`
List all jobs.

**Response:**
```json
[
  {
    "id": "job_20241117_123456",
    "name": "My Review Job",
    "status": "completed",
    "pillar": "ALL",
    "run_mode": "ONCE",
    "progress": 100.0,
    "created_at": "2024-11-17T12:34:56Z",
    "completed_at": "2024-11-17T13:45:00Z"
  }
]
```

#### `POST /jobs`
Create a new job.

**Request:**
```json
{
  "name": "My Review Job",
  "pillar": "ALL",
  "run_mode": "ONCE",
  "paper_ids": ["paper1", "paper2"]
}
```

**Response:** `201 Created`
```json
{
  "id": "job_20241117_123456",
  "name": "My Review Job",
  "status": "queued",
  ...
}
```

#### `GET /jobs/{job_id}`
Get job details.

**Response:**
```json
{
  "id": "job_20241117_123456",
  "name": "My Review Job",
  "status": "running",
  "progress": 45.3,
  ...
}
```

**Errors:**
- `404`: Job not found

#### `POST /jobs/{job_id}/start`
Start a job.

**Response:**
```json
{
  "id": "job_20241117_123456",
  "status": "running",
  ...
}
```

**Errors:**
- `409`: Job already running

#### `POST /jobs/{job_id}/cancel`
Cancel a running job.

**Response:**
```json
{
  "id": "job_20241117_123456",
  "status": "cancelled",
  ...
}
```

#### `DELETE /jobs/{job_id}`
Delete a job.

**Response:** `204 No Content`

---

### Papers

#### `GET /papers`
List all papers.

**Query Parameters:**
- `limit` (int): Max results (default: 100)
- `offset` (int): Pagination offset
- `sort` (string): Sort field (title, year, upload_date)

**Response:**
```json
{
  "papers": [
    {
      "id": "paper_abc123",
      "title": "Deep Learning for NLP",
      "authors": ["Smith, J.", "Doe, A."],
      "year": 2023,
      "doi": "10.1234/example",
      "pdf_path": "data/raw/paper.pdf",
      "upload_date": "2024-11-17T10:00:00Z"
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

#### `POST /papers/upload`
Upload PDF papers.

**Request:** `multipart/form-data`
```
files: [file1.pdf, file2.pdf, ...]
```

**Response:** `201 Created`
```json
{
  "uploaded": 2,
  "papers": [
    {"id": "paper_abc123", "title": "..."},
    {"id": "paper_def456", "title": "..."}
  ]
}
```

**Errors:**
- `400`: Invalid file type (not PDF)
- `413`: File too large (>50 MB)

#### `GET /papers/{paper_id}`
Get paper details.

**Response:**
```json
{
  "id": "paper_abc123",
  "title": "Deep Learning for NLP",
  "authors": ["Smith, J."],
  "year": 2023,
  "abstract": "...",
  "doi": "10.1234/example",
  ...
}
```

#### `DELETE /papers/{paper_id}`
Delete a paper.

**Response:** `204 No Content`

---

### Results

#### `GET /results/{job_id}`
Get job results (gaps, coverage, recommendations).

**Response:**
```json
{
  "job_id": "job_20241117_123456",
  "gaps": [
    {
      "id": "gap_1",
      "description": "Limited coverage of transformer architectures",
      "pillar": "Technical Foundation",
      "severity": "critical",
      "coverage": 35.0,
      "evidence_count": 3
    }
  ],
  "overall_completeness": 68.5,
  "recommendations": [
    "Search for 'transformer architecture' papers"
  ]
}
```

#### `GET /results/{job_id}/download`
Download results ZIP file.

**Response:** `application/zip`

---

## Error Codes

| Code | Description | Example |
|------|-------------|---------|
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing API key (future) |
| 404 | Not Found | Job/paper not found |
| 409 | Conflict | Job already running |
| 413 | Payload Too Large | PDF >50 MB |
| 500 | Internal Server Error | Unexpected error |

**Error Response Format:**
```json
{
  "error": "Job not found",
  "code": 404,
  "details": {
    "job_id": "invalid_id"
  }
}
```

---

## Rate Limiting

Currently no rate limiting. Future versions may enforce:
- 100 requests/minute per IP
- 1000 requests/hour per IP

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1700234567
```

---

## Pagination

For list endpoints (e.g., `/jobs`, `/papers`):

```bash
# Page 1 (first 50 items)
GET /api/v1/papers?limit=50&offset=0

# Page 2 (next 50 items)
GET /api/v1/papers?limit=50&offset=50
```

**Response includes:**
```json
{
  "papers": [...],
  "total": 250,
  "limit": 50,
  "offset": 50,
  "next": "/api/v1/papers?limit=50&offset=100"
}
```

---

## Webhooks (Future)

Subscribe to job events:

```bash
POST /api/v1/webhooks
{
  "url": "https://your-app.com/webhook",
  "events": ["job.completed", "job.failed"]
}
```

**Webhook Payload:**
```json
{
  "event": "job.completed",
  "job_id": "job_20241117_123456",
  "timestamp": "2024-11-17T14:00:00Z"
}
```
```

---

## 📚 Additional Documentation

**File:** `docs/CLIENT_SDK.md`

**New Content:**
```markdown
# Client SDK

## Python Client

**Installation:**
```bash
pip install literature-review-client
```

**Usage:**
```python
from literature_review import DashboardClient

client = DashboardClient(base_url="http://localhost:5001")

# List jobs
jobs = client.jobs.list()

# Create job
job = client.jobs.create(name="My Job", pillar="ALL")

# Start job
client.jobs.start(job.id)

# Get results
results = client.results.get(job.id)
```

## JavaScript Client

**Installation:**
```bash
npm install @yourorg/literature-review-client
```

**Usage:**
```javascript
import { DashboardClient } from '@yourorg/literature-review-client';

const client = new DashboardClient({ baseURL: 'http://localhost:5001' });

// List jobs
const jobs = await client.jobs.list();

// Create job
const job = await client.jobs.create({ name: 'My Job', pillar: 'ALL' });

// Start job
await client.jobs.start(job.id);
```
```

---

## ✅ Definition of Done

- [ ] `flask-swagger-ui` and `flask-restx` installed
- [ ] `openapi_spec.py` created (OpenAPI 3.0 schema)
- [ ] All Flask routes annotated with `@api.doc` decorators
- [ ] Swagger UI accessible at `/api/docs`
- [ ] `API_REFERENCE.md` created (comprehensive guide)
- [ ] Request/response examples for all endpoints
- [ ] Error code reference table
- [ ] Pagination guide
- [ ] Authentication guide (placeholder for future)
- [ ] Rate limiting documentation
- [ ] `CLIENT_SDK.md` created (Python/JavaScript examples)
- [ ] Postman collection exported (optional)
- [ ] Code review approved
- [ ] Merged to main branch
