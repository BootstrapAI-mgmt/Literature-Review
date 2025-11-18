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

## PDF Upload and Metadata Extraction

### Overview

When you upload a PDF, the system automatically extracts comprehensive metadata to help identify and organize research papers. The extraction process uses multiple strategies to ensure accuracy.

### What Gets Extracted

The system extracts the following metadata from uploaded PDFs:

- **Title**: Paper title (from embedded metadata or first page)
- **Authors**: Author names (multiple sources)
- **Year**: Publication year
- **Abstract**: Paper abstract (if available)
- **DOI**: Digital Object Identifier (for citation tracking)
- **Journal/Venue**: Publication venue (conference or journal)

### Extraction Methods

The system uses a multi-strategy approach with the following priority order:

1. **Embedded PDF metadata** (most reliable)
   - Extracts title, authors, and dates from PDF properties
   - Highest confidence when available

2. **First-page text parsing** (heuristic)
   - Analyzes layout and text patterns
   - Identifies title based on font size and position
   - Detects author names using common patterns
   - Locates abstract sections

3. **Content analysis**
   - Pattern matching for DOI identifiers
   - Year detection from various formats (copyright notices, publication dates)
   - Journal/venue extraction from headers

### Confidence Scores

Each extracted field has a confidence score (0.0-1.0) indicating extraction quality:

- **0.9-1.0**: High confidence
  - Verified via DOI or embedded metadata
  - Strong pattern matches
  - Example: DOI extracted from text, title from PDF metadata

- **0.7-0.9**: Good confidence
  - Strong heuristic match
  - Multiple indicators agree
  - Example: Title from first-page text with good formatting

- **0.5-0.7**: Medium confidence
  - Weak heuristic match
  - Limited supporting evidence
  - Example: Authors extracted from ambiguous text

- **< 0.5**: Low confidence (flagged for review)
  - Extraction uncertain
  - Manual review recommended
  - Example: No clear abstract boundary found

### Quality Indicators

Papers with low-confidence metadata are flagged in the system logs. You can identify potential issues by:

- Checking the job logs for "Low confidence metadata" warnings
- Reviewing extracted metadata before starting analysis
- Manually correcting metadata if needed

### Troubleshooting

**Poor Extraction Quality:**

- **Scanned PDFs (images)**: Text layer required for extraction
  - Solution: Use OCR preprocessing or manually enter metadata
  
- **Non-standard formats**: Unusual layouts confuse heuristics
  - Solution: Manually enter metadata or use standard PDF format
  
- **Missing DOI**: Cannot track citations or verify title
  - Solution: Look up on Google Scholar and add manually

**Improving Extraction:**

- Use PDFs with text layers (not scanned images)
- Prefer papers with embedded metadata
- Choose papers with DOIs when available
- Check PDF properties before upload (title, author fields should be filled)

### Technical Details

The system uses **PyMuPDF** for enhanced PDF processing, which provides:
- Better text extraction than basic libraries
- Access to embedded PDF metadata
- Font and layout information for heuristics
- Fast processing (typically under 1 second per PDF)

### Example Metadata

```json
{
  "title": "Deep Learning for Natural Language Processing",
  "authors": ["John Smith", "Jane Doe"],
  "year": 2023,
  "abstract": "This paper presents a novel approach...",
  "doi": "10.1234/example.2023.001",
  "journal": "Nature Machine Intelligence",
  "confidence": {
    "title": 0.9,
    "authors": 0.8,
    "year": 0.9,
    "abstract": 0.8,
    "doi": 0.95,
    "journal": 0.7
  }
}
```

---

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
- **View Progress History**: View timeline for completed jobs (see below)
- **Close**: Close the detail modal

### 5. Viewing Historical Job Progress

For completed jobs, you can view a detailed timeline showing how long each stage took. This is useful for:
- **Debugging slow jobs**: Identify which stage took longer than expected
- **Performance analysis**: Compare job durations over time
- **Understanding bottlenecks**: See which stages consume the most time

#### Accessing Progress History

1. Click on a completed job in the jobs table
2. In the job details modal, click the **"⏱️ View Progress History"** button
3. A new modal will open showing the progress timeline

#### What You'll See

The Progress Timeline modal displays:

**Total Duration Summary:**
- Total job duration (human-readable format: e.g., "15min 30s")
- Slowest stage identification

**Timeline Visualization:**
- Horizontal bar chart showing duration of each stage
- Color-coded bars:
  - 🟢 Green: Completed successfully
  - 🔴 Red: Completed with error
  - ⚪ Gray: Unknown status

**Stage Breakdown Table:**
- **Stage**: Pipeline stage name (e.g., "initialization", "judge", "deep_review")
- **Start Time**: When the stage began
- **End Time**: When the stage finished
- **Duration**: How long the stage took (human-readable)
- **% of Total**: Percentage of total job time consumed by this stage
- **Status**: Completion status (Completed, Error, Unknown)

#### Example Timeline

```
Job #abc-123 took 15min 30s (expected 10min)

Stage Breakdown:
- Initialization:   2min 0s   (13% of total) ✓ Completed
- Judge Validation: 3min 0s   (19% of total) ✓ Completed  
- Deep Review:      5min 30s  (35% of total) ✓ Completed
- Gap Analysis:     3min 0s   (19% of total) ✓ Completed
- Finalization:     2min 0s   (13% of total) ✓ Completed

Slowest Stage: Deep Review (5min 30s)
```

#### Interpreting Results

**Debugging Slow Jobs:**
If a job took longer than expected, check:
1. **Which stage was slowest?** The progress bar will highlight it
2. **Compare to other jobs:** Run the same analysis and compare timelines
3. **Check for outliers:** A stage taking 3x longer than usual may indicate an issue

**Common Bottlenecks:**
- **Deep Review**: Scales with number of papers and pillar complexity
- **Gap Analysis**: Depends on number of requirements and evidence triangulation
- **Judge Validation**: Usually fast unless there are many validation errors

#### Exporting Progress Reports

Click the **"📥 Export CSV"** button to download the progress timeline as a CSV file.

The CSV includes:
- Stage name
- Start and end timestamps
- Duration (seconds and human-readable)
- Percentage of total time
- Status

**Use Cases for CSV Export:**
- Performance tracking across multiple jobs
- Billing/time tracking
- Historical analysis
- Importing into spreadsheets for further analysis

**Example CSV:**
```csv
Stage,Start Time,End Time,Duration (seconds),Duration (human),% of Total,Status
initialization,2025-11-17T10:00:00Z,2025-11-17T10:02:00Z,120,2min 0s,13.3%,completed
judge,2025-11-17T10:02:00Z,2025-11-17T10:05:00Z,180,3min 0s,20.0%,completed
deep_review,2025-11-17T10:05:00Z,2025-11-17T10:10:30Z,330,5min 30s,36.7%,completed
gap_analysis,2025-11-17T10:10:30Z,2025-11-17T10:13:30Z,180,3min 0s,20.0%,completed
finalization,2025-11-17T10:13:30Z,2025-11-17T10:15:30Z,120,2min 0s,13.3%,completed

TOTAL,,,900,15min 0s,100%,
```

#### Limitations

- Progress history is only available for **completed jobs**
- Jobs must have been run with progress tracking enabled (standard in v2.0+)
- If a job was run before progress tracking was implemented, you'll see "No progress data available"

### 6. Real-time Updates

The dashboard uses WebSockets for real-time updates:
- Connection status shown in top-right corner
- Jobs automatically update when status changes
- No need to refresh the page

### 6. Understanding ETA (Estimated Time to Arrival)

The dashboard provides intelligent ETA estimates that improve with each job run.

#### How ETA is Calculated

The dashboard learns from past job runs to provide accurate ETAs based on:

1. **Historical stage durations**: Actual time taken for each pipeline stage in previous runs
2. **Paper count scaling**: ETA scales linearly with the number of papers being processed
3. **Current progress**: How fast the current job is progressing compared to historical averages

**Factors Considered:**
- Time per paper for each stage (normalized across different job sizes)
- Number of papers in current job
- Historical variance in execution times

#### Confidence Levels

ETAs are displayed with confidence indicators based on the amount of historical data:

- **🟢 High Confidence**: 10+ past runs, ETA accurate to ±5%
  - Example: "12-13 min remaining"
  - Narrow confidence interval with precise estimates

- **🟡 Medium Confidence**: 3-9 past runs, ETA accurate to ±10-20%
  - Example: "10-15 min remaining"
  - Moderate confidence interval with good estimates

- **🔴 Low Confidence**: <3 past runs, ETA may vary significantly
  - Example: "~15 min remaining (First run, estimate may vary)"
  - Wide confidence interval (±30%) using fallback estimates

#### First Run Behavior

On your first job, the dashboard uses conservative fallback estimates:
- Gap Analysis: 30 seconds per paper
- Deep Review: 120 seconds per paper
- Proof Generation: 45 seconds per paper
- Final Report: 15 seconds per paper

After a few runs, the system adapts to your actual hardware performance and ETAs become much more accurate.

**Example Evolution:**
```
First run:  "~15 min remaining (low confidence)"
After 3 runs:  "12-15 min remaining (medium confidence)"
After 10 runs: "12-13 min remaining (high confidence)"
```

#### ETA Display Features

- **Confidence Badge**: Color-coded indicator (green/yellow/red) showing estimate reliability
- **Time Range**: For uncertain estimates, shows a range (e.g., "10-15 min")
- **Auto-Update**: ETA refreshes every 10 seconds and on each progress event
- **First Run Warning**: Special notice when historical data is limited
- **Stage Breakdown**: Hover over ETA to see per-stage time estimates (coming soon)

#### Improving ETA Accuracy

To get the most accurate ETAs:
1. Run a few jobs to build historical data
2. Keep paper counts consistent when possible
3. Allow jobs to complete (cancelled jobs don't contribute to history)
4. Historical data is saved in `workspace/eta_history.json`

#### Technical Details

The ETA calculator uses:
- **Median-based estimation**: Robust against outliers in execution time
- **Paper count normalization**: Stores "time per paper" to handle variable job sizes
- **Adaptive blending**: Combines historical data with fallback estimates for partial data
- **Confidence intervals**: Statistical ranges based on data quality
- **Automatic history management**: Keeps last 50 runs per stage to prevent unbounded growth

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

#### Get job ETA (Estimated Time to Arrival)
```bash
curl http://localhost:8000/api/jobs/{job_id}/eta \
  -H "X-API-KEY: your-key"
```

Response:
```json
{
  "job_id": "abc-123",
  "status": "running",
  "current_stage": "deep_review",
  "eta": {
    "total_eta_seconds": 720,
    "min_eta_seconds": 648,
    "max_eta_seconds": 864,
    "confidence": "medium",
    "stage_breakdown": {
      "proof_generation": 450,
      "final_report": 150
    },
    "remaining_stages": ["proof_generation", "final_report"]
  }
}
```

The ETA information includes:
- `total_eta_seconds`: Best estimate for remaining time
- `min_eta_seconds` / `max_eta_seconds`: Confidence interval bounds
- `confidence`: "high", "medium", or "low" based on historical data
- `stage_breakdown`: Estimated time for each remaining stage
- `remaining_stages`: List of stages yet to complete

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
│   ├── {job_id}.json
│   └── {job_id}_progress.jsonl  # Progress events stream
├── logs/            # Job logs
│   └── {job_id}.log
└── eta_history.json  # Historical ETA data for accuracy
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
