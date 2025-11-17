# Web Dashboard Guide

## Overview

The Literature Review Web Dashboard provides a user-friendly interface for monitoring and managing pipeline jobs. It allows non-technical users to upload PDFs, track job progress, view logs, and trigger retries without using the command line.

## Features

### Core Functionality
- **PDF Upload**: Upload research papers for processing
- **Job Management**: View all jobs with status, timestamps, and durations
- **Real-time Updates**: WebSocket-based live status updates
- **Log Viewing**: Access job logs directly in the browser
- **Job Retry**: Retry failed jobs with a single click
- **File Download**: Download uploaded PDFs

### Dashboard Metrics
- Total Jobs
- Completed Jobs
- Running Jobs
- Failed Jobs

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements-dashboard.txt
```

This installs:
- FastAPI - Modern web framework
- Uvicorn - ASGI server
- python-multipart - File upload support
- websockets - Real-time updates

### 2. Set API Key

The dashboard uses API key authentication. Set the key as an environment variable:

```bash
export DASHBOARD_API_KEY="your-secure-api-key-here"
```

For development, you can use the default key:
```bash
export DASHBOARD_API_KEY="dev-key-change-in-production"
```

⚠️ **Security Note**: Always use a strong, unique API key in production environments.

## Running the Dashboard

### Option 1: Using the Run Script (Recommended)

```bash
./run_dashboard.sh
```

With custom options:
```bash
./run_dashboard.sh --port 8080 --api-key "my-secret-key"
```

### Option 2: Direct Uvicorn Command

```bash
uvicorn webdashboard.app:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Docker Container

```bash
# Build the image
docker build -t literature-review-dashboard .

# Run the container
docker run -d -p 8000:8000 \
  -e DASHBOARD_API_KEY="your-api-key" \
  -v $(pwd)/workspace:/app/workspace \
  literature-review-dashboard
```

## Using the Dashboard

### 1. Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8000
```

You should see:
- Dashboard header with title
- Metrics cards (Total, Completed, Running, Failed)
- Upload form
- Jobs table

### 2. Upload a PDF

#### Single File Upload

1. Click "Choose File" and select a PDF
2. Enter your API key (default: `dev-key-change-in-production`)
3. Click "Upload & Queue Job"
4. The job will appear in the jobs table with status "QUEUED"

#### Batch Upload with Duplicate Detection

When uploading multiple PDFs, the dashboard automatically checks for duplicates:

1. Select multiple PDF files (Ctrl/Cmd + click)
2. Enter your API key
3. Click "Upload Batch"
4. If duplicates are detected, a warning modal will appear:
   - **Duplicates Found**: Papers that already exist in your database
   - **Match Type**: How the duplicate was detected:
     - 🔴 **Exact File Match**: Same PDF file content (SHA256 hash)
     - 🟡 **Title Match**: Exact title match (case-insensitive)
     - 🔵 **Similar Title**: Fuzzy title match (≥95% similarity)
   - **Confidence**: Match confidence percentage
   - **New Papers**: Papers that don't exist yet

5. Choose an action:
   - **Skip Duplicates**: Upload only new papers (recommended)
   - **Overwrite All**: Upload all papers, including duplicates
   - **Cancel**: Cancel the entire upload

**Example Scenario:**
```
Upload 5 PDFs:
- paper1.pdf (already exists) ✗
- paper2.pdf (new) ✓
- paper3.pdf (already exists with 97% similar title) ✗
- paper4.pdf (new) ✓
- paper5.pdf (new) ✓

Result: 2 duplicates detected, 3 new papers
Action: Skip Duplicates → Only uploads paper2, paper4, paper5
```

**Benefits:**
- Prevents accidental re-uploads across sessions
- Saves processing time and costs
- Maintains database cleanliness
- Clear visibility into what's already in your database

### 3. Monitor Jobs

The jobs table shows:
- **Job ID**: Shortened UUID (first 8 characters)
- **Filename**: Original PDF filename
- **Status**: Current job status (QUEUED, RUNNING, COMPLETED, FAILED)
- **Created**: Timestamp when job was created
- **Duration**: Elapsed time
- **Actions**: View button for details

Status badges are color-coded:
- 🟦 QUEUED (gray)
- 🔵 RUNNING (blue)
- 🟢 COMPLETED (green)
- 🔴 FAILED (red)

### 4. View Job Details

Click "View" or click on a job row to see:
- Full Job ID
- Current Status
- Filename
- Created timestamp
- Error message (if failed)
- Progress information (if available)
- Job logs

Actions available in detail view:
- **Download PDF**: Download the original uploaded file
- **Retry Job**: Retry a failed job
- **Close**: Close the detail modal

### 5. Real-time Updates

The dashboard uses WebSockets for real-time updates:
- Connection status shown in top-right corner
- Jobs automatically update when status changes
- No need to refresh the page

## API Integration

### For Pipeline Orchestrator

To integrate with the dashboard, the orchestrator should write status updates to:
```
workspace/status/{job_id}.json
```

Status file format:
```json
{
  "id": "job-uuid",
  "status": "running",
  "started_at": "2024-01-01T00:00:05",
  "progress": {
    "current_stage": "judge",
    "stages_completed": 2,
    "total_stages": 5,
    "percent": 40
  }
}
```

The dashboard watches this directory and broadcasts updates via WebSocket.

### For Custom Integrations

The dashboard exposes a REST API:

#### Upload a file
```bash
curl -X POST http://localhost:8000/api/upload \
  -H "X-API-KEY: your-key" \
  -F "file=@paper.pdf"
```

#### Batch upload with duplicate detection
```bash
curl -X POST http://localhost:8000/api/upload/batch \
  -H "X-API-KEY: your-key" \
  -F "files=@paper1.pdf" \
  -F "files=@paper2.pdf" \
  -F "files=@paper3.pdf"
```

Response when duplicates are found:
```json
{
  "status": "duplicates_found",
  "job_id": "abc-123",
  "duplicates": [
    {
      "title": "Machine Learning Survey",
      "original_name": "paper1.pdf",
      "match_info": {
        "method": "exact_title",
        "confidence": 1.0
      }
    }
  ],
  "new": [
    {
      "title": "Deep Learning Review",
      "original_name": "paper2.pdf"
    }
  ],
  "message": "1 of 2 papers already exist"
}
```

#### Confirm upload after duplicate detection
```bash
# Skip duplicates - upload only new papers
curl -X POST http://localhost:8000/api/upload/confirm \
  -H "X-API-KEY: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "skip_duplicates",
    "job_id": "abc-123"
  }'

# Overwrite all - upload all papers including duplicates
curl -X POST http://localhost:8000/api/upload/confirm \
  -H "X-API-KEY: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "overwrite_all",
    "job_id": "abc-123"
  }'
```

#### List all jobs
```bash
curl http://localhost:8000/api/jobs \
  -H "X-API-KEY: your-key"
```

#### Get job details
```bash
curl http://localhost:8000/api/jobs/{job_id} \
  -H "X-API-KEY: your-key"
```

#### Get job logs
```bash
curl http://localhost:8000/api/logs/{job_id}?tail=100 \
  -H "X-API-KEY: your-key"
```

#### Retry a job
```bash
curl -X POST http://localhost:8000/api/jobs/{job_id}/retry \
  -H "X-API-KEY: your-key" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

#### Download a file
```bash
curl http://localhost:8000/api/download/{job_id} \
  -H "X-API-KEY: your-key" \
  -o downloaded.pdf
```

## File Structure

```
workspace/
├── uploads/          # Uploaded PDF files
│   └── {job_id}.pdf
├── jobs/            # Job metadata
│   └── {job_id}.json
├── status/          # Status updates from orchestrator
│   └── {job_id}.json
└── logs/            # Job logs
    └── {job_id}.log
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DASHBOARD_API_KEY` | API key for authentication | `dev-key-change-in-production` |

### Application Settings

Edit `webdashboard/app.py` to customize:
- `WORKSPACE_DIR` - Base directory for all data
- `UPLOADS_DIR` - Directory for uploaded files
- `JOBS_DIR` - Directory for job metadata
- `STATUS_DIR` - Directory for status updates
- `LOGS_DIR` - Directory for job logs

## Security Best Practices

1. **Use Strong API Keys**: Generate cryptographically secure random keys
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Enable HTTPS**: Use a reverse proxy (nginx/Caddy) with TLS in production

3. **Restrict Access**: Use firewall rules to limit dashboard access

4. **Implement Rate Limiting**: Add rate limiting for API endpoints

5. **Regular Updates**: Keep dependencies up to date
   ```bash
   pip install --upgrade -r requirements-dashboard.txt
   ```

## Troubleshooting

### Dashboard won't start
- Check if port 8000 is already in use
- Verify all dependencies are installed
- Check the server logs for errors

### Upload fails with 401 Unauthorized
- Verify the API key matches the environment variable
- Check that `X-API-KEY` header is being sent

### WebSocket won't connect
- Ensure WebSocket support is enabled in your reverse proxy
- Check firewall rules allow WebSocket connections

### Jobs not updating in real-time
- Check WebSocket connection status (top-right corner)
- Verify status files are being created in `workspace/status/`
- Check browser console for errors

## Development

### Running Tests

```bash
# Run all dashboard tests
pytest tests/webui/ -v

# Run with coverage
pytest tests/webui/ --cov=webdashboard

# Run specific test file
pytest tests/webui/test_api.py -v
```

### Hot Reload

During development, uvicorn automatically reloads on code changes:
```bash
uvicorn webdashboard.app:app --reload
```

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Deployment

### Using Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  dashboard:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DASHBOARD_API_KEY=${DASHBOARD_API_KEY}
    volumes:
      - ./workspace:/app/workspace
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

### Behind a Reverse Proxy

#### Nginx Configuration
```nginx
server {
    listen 80;
    server_name dashboard.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### Caddy Configuration
```
dashboard.example.com {
    reverse_proxy localhost:8000
}
```

## Limitations

- **v1.0 Limitations**:
  - File-based storage (not suitable for high-scale deployments)
  - Single server deployment
  - Basic authentication only
  - No user management

- **Future Enhancements** (v2.0):
  - Database backend (PostgreSQL/MongoDB)
  - OAuth/SSO integration
  - Multi-user support with roles
  - Job scheduling and cron triggers
  - S3/cloud storage for uploads
  - Advanced analytics and reporting

## Support

For issues or questions:
1. Check the [troubleshooting section](#troubleshooting)
2. Review logs in `/tmp/server.log` (if using run script)
3. Open an issue on GitHub with error details

## License

See main repository LICENSE file.
