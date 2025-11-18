# API Reference

**Version:** 2.0.0  
**Base URL:** `http://localhost:5001`  
**API Docs:** `http://localhost:5001/api/docs` (Swagger UI)  
**ReDoc:** `http://localhost:5001/api/redoc` (Alternative documentation)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
   - [Papers](#papers)
   - [Jobs](#jobs)
   - [Results](#results)
   - [Logs](#logs)
   - [Prompts](#prompts)
   - [Analysis](#analysis)
3. [Error Codes](#error-codes)
4. [Pagination](#pagination)
5. [Rate Limiting](#rate-limiting)
6. [WebSocket Support](#websocket-support)

---

## Authentication

All API endpoints require authentication via API key.

**Header:** `X-API-KEY`  
**Value:** Your API key (configure via `DASHBOARD_API_KEY` environment variable)

### Example

```bash
curl -H "X-API-KEY: your-api-key" http://localhost:5001/api/jobs
```

### Development

For development, the default API key is: `dev-key-change-in-production`

**⚠️ Security Warning:** Always change the API key in production environments!

---

## Endpoints

### Papers

#### Upload Single PDF

**POST** `/api/upload`

Upload a single PDF file and create a new analysis job.

**Headers:**
- `X-API-KEY`: Required authentication key
- `Content-Type`: `multipart/form-data`

**Request:**
```bash
curl -X POST "http://localhost:5001/api/upload" \
  -H "X-API-KEY: dev-key-change-in-production" \
  -F "file=@/path/to/paper.pdf"
```

**Response:** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "filename": "research_paper.pdf"
}
```

**Errors:**
- `400`: Invalid file type (not PDF)
- `401`: Invalid or missing API key
- `500`: Server error during upload

---

#### Upload Multiple PDFs (Batch)

**POST** `/api/upload/batch`

Upload multiple PDF files for a single analysis job with duplicate detection.

**Headers:**
- `X-API-KEY`: Required authentication key
- `Content-Type`: `multipart/form-data`

**Request:**
```bash
curl -X POST "http://localhost:5001/api/upload/batch" \
  -H "X-API-KEY: dev-key-change-in-production" \
  -F "files=@paper1.pdf" \
  -F "files=@paper2.pdf" \
  -F "files=@paper3.pdf"
```

**Response (No Duplicates):** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "draft",
  "file_count": 3,
  "files": [
    {
      "original_name": "paper1.pdf",
      "path": "workspace/uploads/550e8400.../paper1.pdf",
      "size": 1024000,
      "title": "paper1"
    }
  ]
}
```

**Response (Duplicates Found):** `200 OK`
```json
{
  "status": "duplicates_found",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "duplicates": [
    {
      "original_name": "paper1.pdf",
      "title": "Paper Title from Database"
    }
  ],
  "new": [
    {
      "original_name": "paper2.pdf",
      "title": "paper2"
    }
  ],
  "matches": [
    {
      "uploaded": "paper1.pdf",
      "existing": "Paper Title from Database",
      "similarity": 0.95
    }
  ],
  "message": "1 of 3 papers already exist"
}
```

---

#### Confirm Upload (After Duplicates)

**POST** `/api/upload/confirm`

Confirm batch upload after duplicate detection warning.

**Headers:**
- `X-API-KEY`: Required authentication key
- `Content-Type`: `application/json`

**Request Body:**
```json
{
  "action": "skip_duplicates",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Actions:**
- `skip_duplicates`: Remove duplicate files, upload only new papers
- `overwrite_all`: Upload all files including duplicates

**Response:** `200 OK`
```json
{
  "status": "success",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "uploaded": 2,
  "skipped": 1,
  "message": "Uploaded 2 new papers, skipped 1 duplicates"
}
```

---

### Jobs

#### List All Jobs

**GET** `/api/jobs`

List all jobs with summary metrics, sorted by creation time (newest first).

**Headers:**
- `X-API-KEY`: Required authentication key

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs
```

**Response:** `200 OK`
```json
{
  "jobs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "filename": "research.pdf",
      "created_at": "2024-11-17T12:00:00Z",
      "started_at": "2024-11-17T12:01:00Z",
      "completed_at": "2024-11-17T13:00:00Z",
      "config": {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "convergence_threshold": 5.0
      },
      "summary": {
        "completeness": 68.5,
        "critical_gaps": 3,
        "paper_count": 5,
        "recommendations_preview": [
          "Search for 'transformer architecture' papers",
          "Add more recent publications (2023-2024)"
        ],
        "has_results": true
      }
    }
  ],
  "count": 1
}
```

---

#### Get Job Details

**GET** `/api/jobs/{job_id}`

Get detailed information for a specific job.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier (UUID)

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "filename": "research.pdf",
  "created_at": "2024-11-17T12:00:00Z",
  "started_at": "2024-11-17T12:01:00Z",
  "completed_at": null,
  "error": null,
  "progress": {
    "percentage": 45.3,
    "stage": "gap_analysis",
    "current_pillar": "Technical Foundation"
  },
  "config": {
    "pillar_selections": ["ALL"],
    "run_mode": "ONCE",
    "convergence_threshold": 5.0
  }
}
```

**Errors:**
- `404`: Job not found

---

#### Configure Job

**POST** `/api/jobs/{job_id}/configure`

Configure job parameters before execution.

**Headers:**
- `X-API-KEY`: Required authentication key
- `Content-Type`: `application/json`

**Path Parameters:**
- `job_id`: Unique job identifier

**Request Body:**
```json
{
  "pillar_selections": ["ALL"],
  "run_mode": "ONCE",
  "convergence_threshold": 5.0
}
```

**Pillar Selections:**
- `["ALL"]`: Analyze all pillars
- Specific pillars: `["Technical Foundation", "Methodology"]`, etc.

**Run Modes:**
- `ONCE`: Single-pass analysis
- `DEEP_LOOP`: Iterative analysis until convergence

**Request:**
```bash
curl -X POST "http://localhost:5001/api/jobs/550e8400.../configure" \
  -H "X-API-KEY: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "pillar_selections": ["ALL"],
    "run_mode": "ONCE",
    "convergence_threshold": 5.0
  }'
```

**Response:** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "config": {
    "pillar_selections": ["ALL"],
    "run_mode": "ONCE",
    "convergence_threshold": 5.0
  }
}
```

---

#### Start Job

**POST** `/api/jobs/{job_id}/start`

Start execution of a configured job.

**Prerequisites:**
- Job status must be `draft` or `failed`
- Job must be configured (via `/api/jobs/{job_id}/configure`)
- At least one PDF must be uploaded

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier

**Request:**
```bash
curl -X POST "http://localhost:5001/api/jobs/550e8400.../start" \
  -H "X-API-KEY: dev-key-change-in-production"
```

**Response:** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Job queued for execution"
}
```

**Errors:**
- `400`: Job cannot be started (invalid status, missing config, or no PDFs)
- `404`: Job not found
- `500`: Failed to build research database

---

#### Retry Job

**POST** `/api/jobs/{job_id}/retry`

Retry a failed job.

**Headers:**
- `X-API-KEY`: Required authentication key
- `Content-Type`: `application/json`

**Path Parameters:**
- `job_id`: Unique job identifier

**Request Body:**
```json
{
  "force": false
}
```

**Request:**
```bash
curl -X POST "http://localhost:5001/api/jobs/550e8400.../retry" \
  -H "X-API-KEY: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

**Response:** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Retry requested"
}
```

---

### Results

#### Get Job Results

**GET** `/api/jobs/{job_id}/results`

Get list of all output files for a completed job.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400.../results
```

**Response:** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "output_count": 15,
  "outputs": [
    {
      "filename": "gap_analysis_report.json",
      "path": "gap_analysis_report.json",
      "size": 52480,
      "category": "data",
      "mime_type": "application/json",
      "modified": 1700234567.0
    },
    {
      "filename": "_OVERALL_completeness.html",
      "path": "_OVERALL_completeness.html",
      "size": 8192,
      "category": "visualizations",
      "mime_type": "text/html",
      "modified": 1700234567.0
    }
  ],
  "output_dir": "workspace/jobs/550e8400.../outputs/gap_analysis_output"
}
```

**Categories:**
- `data`: JSON files with raw analysis data
- `reports`: Markdown reports
- `visualizations`: HTML charts and graphs
- `pillar_waterfalls`: Waterfall charts per pillar
- `other`: Miscellaneous files

**Errors:**
- `400`: Job not completed
- `404`: Job not found

---

#### Download Specific Result File

**GET** `/api/jobs/{job_id}/results/{file_path}`

Download a specific output file.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier
- `file_path`: Relative path to file (from results list)

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400.../results/gap_analysis_report.json \
  -o gap_analysis_report.json
```

**Response:** File download (content type varies)

**Errors:**
- `400`: Job not completed
- `403`: Access denied (path traversal attempt)
- `404`: Job or file not found

---

#### Download All Results (ZIP)

**GET** `/api/jobs/{job_id}/results/download/all`

Download all job results as a ZIP archive.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400.../results/download/all \
  -o results.zip
```

**Response:** `application/zip`

The ZIP file contains:
- All output files from gap analysis
- `prompt_history.json` (if user prompts were used)
- `prompt_history.txt` (human-readable summary)

**Errors:**
- `400`: Job not completed
- `404`: Job not found or no results available

---

#### Get Proof Scorecard Summary

**GET** `/api/jobs/{job_id}/proof-scorecard`

Get proof scorecard summary with overall score and recommendations.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400.../proof-scorecard
```

**Response (Available):** `200 OK`
```json
{
  "available": true,
  "overall_score": 72.5,
  "verdict": "Moderate Proof Readiness",
  "headline": "Research shows promise but needs strengthening",
  "publication_viability": {
    "score": 65,
    "recommendation": "Target tier-2 journals"
  },
  "research_goals": [
    "Improve evidence quality in Technical Foundation",
    "Add more recent citations",
    "Expand methodology section"
  ],
  "next_steps": [
    "Conduct additional experiments",
    "Strengthen statistical analysis",
    "Address reviewer feedback from pilot submission"
  ],
  "html_path": "/api/jobs/550e8400.../files/proof_scorecard_output/proof_readiness.html"
}
```

**Response (Not Available):** `200 OK`
```json
{
  "available": false,
  "message": "Proof scorecard not yet generated"
}
```

---

#### Get Cost Summary

**GET** `/api/jobs/{job_id}/cost-summary`

Get API cost summary with total cost and module breakdown.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400.../cost-summary
```

**Response (Available):** `200 OK`
```json
{
  "available": true,
  "total_cost": 2.45,
  "budget_percent": 24.5,
  "per_paper_cost": 0.49,
  "module_breakdown": {
    "deep_reviewer": 1.20,
    "gap_analyzer": 0.85,
    "proof_evaluator": 0.40
  },
  "cache_savings": 0.35,
  "total_tokens": 125000,
  "html_path": "/api/jobs/550e8400.../files/cost_reports/api_usage_report.html"
}
```

**Response (Not Available):** `200 OK`
```json
{
  "available": false,
  "total_cost": 0,
  "message": "No cost data available"
}
```

---

#### Get Sufficiency Summary

**GET** `/api/jobs/{job_id}/sufficiency-summary`

Get evidence sufficiency summary with quadrant distribution.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400.../sufficiency-summary
```

**Response (Available):** `200 OK`
```json
{
  "available": true,
  "quadrants": {
    "Strong Evidence": 12,
    "Emerging Evidence": 8,
    "Weak Coverage": 5,
    "Critical Gap": 3
  },
  "total_requirements": 28,
  "recommendations": [
    "Focus on Critical Gap requirements first",
    "Strengthen Weak Coverage areas",
    "Validate Emerging Evidence with additional sources"
  ],
  "html_path": "/api/jobs/550e8400.../files/gap_analysis_output/sufficiency_matrix.html"
}
```

---

#### Get Progress History

**GET** `/api/jobs/{job_id}/progress-history`

Get historical progress timeline for completed job with stage durations.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400.../progress-history
```

**Response:** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_duration_seconds": 3600,
  "total_duration_human": "1h 0min",
  "timeline": [
    {
      "stage": "deep_review",
      "start_time": "2024-11-17T12:01:00Z",
      "end_time": "2024-11-17T12:45:00Z",
      "duration_seconds": 2640,
      "duration_human": "44min 0s",
      "status": "completed",
      "percentage": 73.3
    },
    {
      "stage": "gap_analysis",
      "start_time": "2024-11-17T12:45:00Z",
      "end_time": "2024-11-17T13:00:00Z",
      "duration_seconds": 900,
      "duration_human": "15min 0s",
      "status": "completed",
      "percentage": 25.0
    }
  ],
  "slowest_stage": "deep_review",
  "start_time": "2024-11-17T12:01:00Z",
  "end_time": "2024-11-17T13:00:00Z"
}
```

**Errors:**
- `400`: Job not completed
- `404`: Job not found or no progress data

---

#### Export Progress History (CSV)

**GET** `/api/jobs/{job_id}/progress-history.csv`

Download progress history as CSV file.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/jobs/550e8400.../progress-history.csv \
  -o progress.csv
```

**Response:** `text/csv`
```csv
Stage,Start Time,End Time,Duration (seconds),Duration (human),% of Total,Status
deep_review,2024-11-17T12:01:00Z,2024-11-17T12:45:00Z,2640,44min 0s,73.3%,completed
gap_analysis,2024-11-17T12:45:00Z,2024-11-17T13:00:00Z,900,15min 0s,25.0%,completed

TOTAL,,,3600,1h 0min,100%,
```

---

#### Compare Two Jobs

**GET** `/api/compare-jobs/{job_id_1}/{job_id_2}`

Compare two gap analysis jobs to identify improvements and changes.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id_1`: First job identifier (baseline)
- `job_id_2`: Second job identifier (comparison)

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  http://localhost:5001/api/compare-jobs/550e8400.../660f9500...
```

**Response:** `200 OK`
```json
{
  "job1": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-11-17T12:00:00Z",
    "completeness": 68.5,
    "paper_count": 5,
    "gap_count": 12
  },
  "job2": {
    "id": "660f9500-e29b-41d4-a716-446655440001",
    "timestamp": "2024-11-18T14:00:00Z",
    "completeness": 82.3,
    "paper_count": 8,
    "gap_count": 6
  },
  "delta": {
    "completeness_change": 13.8,
    "papers_added": ["new_paper1.pdf", "new_paper2.pdf", "new_paper3.pdf"],
    "papers_removed": [],
    "papers_added_count": 3,
    "papers_removed_count": 0,
    "gaps_filled": [
      {
        "gap": "Technical Foundation - Transformer Architecture",
        "pillar": "Technical Foundation",
        "improvement": 45.2,
        "old_completeness": 35.0,
        "new_completeness": 80.2
      }
    ],
    "gaps_filled_count": 6,
    "new_gaps": [],
    "new_gaps_count": 0
  }
}
```

**Errors:**
- `400`: One or both jobs not completed
- `404`: One or both jobs not found

---

### Logs

#### Get Job Logs

**GET** `/api/logs/{job_id}`

Get logs for a specific job.

**Headers:**
- `X-API-KEY`: Required authentication key

**Path Parameters:**
- `job_id`: Unique job identifier

**Query Parameters:**
- `tail`: Number of lines to return from end of log (default: 100)

**Request:**
```bash
curl -H "X-API-KEY: dev-key-change-in-production" \
  "http://localhost:5001/api/logs/550e8400...?tail=50"
```

**Response:** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "logs": "[2024-11-17 12:01:00] Starting deep review...\n[2024-11-17 12:05:00] Processing paper 1/5...\n",
  "line_count": 50
}
```

**Response (No Logs):** `200 OK`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "logs": "",
  "message": "No logs available"
}
```

---

### Prompts

#### Respond to Prompt

**POST** `/api/prompts/{prompt_id}/respond`

Submit user response to an interactive prompt.

**Headers:**
- `X-API-KEY`: Required authentication key
- `Content-Type`: `application/json`

**Path Parameters:**
- `prompt_id`: Prompt identifier (received via WebSocket)

**Request Body:**
```json
{
  "response": "yes"
}
```

**Request:**
```bash
curl -X POST "http://localhost:5001/api/prompts/prompt_123/respond" \
  -H "X-API-KEY: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"response": "yes"}'
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "prompt_id": "prompt_123"
}
```

**Errors:**
- `404`: Prompt not found
- `500`: Error submitting response

---

### Analysis

#### Suggest Research Field

**POST** `/api/suggest-field`

Auto-suggest research field based on paper titles and abstracts.

**Headers:**
- `Content-Type`: `application/json`

**Request Body:**
```json
{
  "papers": [
    {
      "title": "Deep Learning for Natural Language Processing",
      "abstract": "This paper explores transformer architectures..."
    },
    {
      "title": "BERT: Pre-training of Deep Bidirectional Transformers",
      "abstract": "We introduce a new language representation model..."
    }
  ]
}
```

**Request:**
```bash
curl -X POST "http://localhost:5001/api/suggest-field" \
  -H "Content-Type: application/json" \
  -d '{
    "papers": [
      {"title": "Deep Learning for NLP", "abstract": "..."}
    ]
  }'
```

**Response:** `200 OK`
```json
{
  "suggested_field": "ai_ml",
  "field_name": "AI & Machine Learning",
  "half_life_years": 3.0,
  "description": "Artificial Intelligence and Machine Learning research with rapid innovation cycles",
  "examples": ["neural networks", "deep learning", "transformers"],
  "confidence": "high"
}
```

**Confidence Levels:**
- `high`: Strong match to known research field
- `low`: Fallback to custom field (manual configuration recommended)

---

#### Get Field Presets

**GET** `/api/field-presets`

Get all available research field presets for evidence decay configuration.

**Request:**
```bash
curl http://localhost:5001/api/field-presets
```

**Response:** `200 OK`
```json
{
  "presets": {
    "ai_ml": {
      "name": "AI & Machine Learning",
      "half_life_years": 3.0,
      "description": "Fast-moving field with rapid innovation",
      "examples": ["neural networks", "transformers", "LLMs"]
    },
    "mathematics": {
      "name": "Pure Mathematics",
      "half_life_years": 50.0,
      "description": "Theoretical field with long-lasting foundational work",
      "examples": ["number theory", "topology", "algebra"]
    },
    "biology": {
      "name": "Biology & Life Sciences",
      "half_life_years": 10.0,
      "description": "Moderate pace with periodic breakthroughs",
      "examples": ["genetics", "molecular biology", "ecology"]
    }
  }
}
```

---

## Error Codes

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Successful deletion |
| 400 | Bad Request | Invalid input data, missing parameters, job in wrong state |
| 401 | Unauthorized | Missing or invalid API key |
| 403 | Forbidden | Access denied (e.g., path traversal attempt) |
| 404 | Not Found | Job, file, or prompt not found |
| 409 | Conflict | Job already running, cannot perform operation |
| 413 | Payload Too Large | PDF file exceeds size limit (50 MB) |
| 500 | Internal Server Error | Unexpected server error |

### Common Error Scenarios

**Invalid API Key:**
```json
{
  "detail": "Invalid or missing API key"
}
```

**Job Not Found:**
```json
{
  "detail": "Job not found"
}
```

**Invalid File Type:**
```json
{
  "detail": "Only PDF files are allowed"
}
```

**Job Cannot Be Started:**
```json
{
  "detail": "Job cannot be started (current status: running)"
}
```

---

## Pagination

Currently, list endpoints return all results. Future versions may implement pagination for large result sets.

**Planned Parameters:**
- `limit`: Maximum results per page (default: 100)
- `offset`: Number of items to skip
- `page`: Page number (alternative to offset)

**Planned Response Format:**
```json
{
  "items": [...],
  "total": 250,
  "limit": 100,
  "offset": 0,
  "next": "/api/jobs?limit=100&offset=100",
  "previous": null
}
```

---

## Rate Limiting

**Current Status:** No rate limiting implemented

**Future Plans:**
- 100 requests/minute per IP
- 1000 requests/hour per IP
- Separate limits for upload endpoints

**Future Response Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1700234567
```

When rate limit exceeded:
```json
{
  "detail": "Rate limit exceeded. Try again in 42 seconds.",
  "retry_after": 42
}
```

---

## WebSocket Support

Real-time updates are available via WebSocket connections.

### Job Updates Stream

**WebSocket URL:** `ws://localhost:5001/ws/jobs`

Subscribe to all job status changes.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:5001/ws/jobs');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

**Message Types:**

**Initial State:**
```json
{
  "type": "initial_state",
  "jobs": [...]
}
```

**Job Created:**
```json
{
  "type": "job_created",
  "job": {...}
}
```

**Job Update:**
```json
{
  "type": "job_update",
  "job": {...}
}
```

**Job Retry:**
```json
{
  "type": "job_retry",
  "job": {...}
}
```

---

### Job Progress Stream

**WebSocket URL:** `ws://localhost:5001/ws/jobs/{job_id}/progress`

Subscribe to real-time progress updates for a specific job.

**Connection:**
```javascript
const jobId = '550e8400-e29b-41d4-a716-446655440000';
const ws = new WebSocket(`ws://localhost:5001/ws/jobs/${jobId}/progress`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data);
};
```

**Message Types:**

**Initial Status:**
```json
{
  "type": "initial_status",
  "job": {...}
}
```

**Progress Update:**
```json
{
  "type": "progress",
  "event": {
    "stage": "gap_analysis",
    "phase": "starting",
    "timestamp": "2024-11-17T12:45:00Z",
    "percentage": 45.3
  }
}
```

**Log Lines:**
```json
{
  "type": "logs",
  "lines": [
    "[2024-11-17 12:45:00] Starting gap analysis...\n",
    "[2024-11-17 12:45:05] Processing pillar 1/5...\n"
  ]
}
```

**Job Complete:**
```json
{
  "type": "job_complete",
  "status": "completed"
}
```

---

## Interactive API Documentation

**Swagger UI:** http://localhost:5001/api/docs

Interactive API documentation with:
- Try-it-out functionality
- Request/response examples
- Schema definitions
- Authentication support

**ReDoc:** http://localhost:5001/api/redoc

Alternative documentation interface with:
- Three-panel layout
- Search functionality
- Code samples
- Downloadable OpenAPI spec

**OpenAPI Specification:** http://localhost:5001/api/openapi.json

Download the raw OpenAPI 3.0 specification in JSON format for:
- Client SDK generation
- Postman import
- Custom tooling integration

---

## Best Practices

### Authentication
- Always use HTTPS in production
- Rotate API keys regularly
- Use environment variables for API keys
- Never commit API keys to version control

### File Uploads
- Validate PDF files before upload
- Check file sizes (max 50 MB per file)
- Use batch upload for multiple papers
- Handle duplicate detection appropriately

### Job Management
- Configure jobs before starting
- Monitor progress via WebSocket for real-time updates
- Download results before deleting jobs
- Use comparison endpoint to track improvements

### Error Handling
- Implement exponential backoff for retries
- Parse error responses for detailed messages
- Check job status before performing operations
- Validate required prerequisites (config, files, etc.)

### Performance
- Use WebSocket for real-time updates instead of polling
- Download results as ZIP for complete archives
- Request only needed log lines with `tail` parameter
- Cache field preset data locally

---

## Support

For issues, questions, or feature requests:
- **Documentation:** `/docs` directory in repository
- **GitHub Issues:** [Create an issue](https://github.com/BootstrapAI-mgmt/Literature-Review/issues)
- **User Manual:** See `docs/USER_MANUAL.md`

---

**Last Updated:** November 18, 2024  
**API Version:** 2.0.0
