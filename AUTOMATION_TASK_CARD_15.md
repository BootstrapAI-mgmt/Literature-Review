# Task Card #15 - Web Dashboard

**Priority:** 🟢 MEDIUM
**Estimated Effort:** 40-60 hours
**Risk Level:** MEDIUM
**Dependencies:** Task Cards #13, #14
**Wave:** Wave 4

---

## Problem Statement

The command-line pipeline is powerful but not accessible to non-developers and lacks real-time monitoring. A lightweight web dashboard enables non-technical users to upload PDFs, monitor pipeline progress, view logs and reports, and trigger retries or re-runs. The dashboard also provides a place for team members to observe convergence metrics and download generated outputs.

## Acceptance Criteria

Functional:
- [ ] Web UI allows uploading PDFs to the workspace
- [ ] Dashboard shows running pipeline jobs and per-paper status
- [ ] Real-time logs and stage durations viewable in browser
- [ ] Users can download generated reports and view convergence graphs
- [ ] Users can trigger a re-run for a single paper or the full pipeline

Non-Functional:
- [ ] Authenticated access (basic) for team members
- [ ] WebSocket or Server-Sent Events (SSE) for real-time updates
- [ ] Runs locally for testing and deploys easily to small VM/container
- [ ] Minimal external dependencies (prefer lightweight stack)

---

## Recommended Stack

- Backend: FastAPI (preferred) or Flask
- Frontend: Simple single-page app using Bootstrap + plain JS or small framework (React optional)
- Real-time: WebSocket via `fastapi_websocket` or `socket.io` bridge
- Storage: Local filesystem for uploads in v1; optional S3 later
- Auth: Basic token-based auth for v1 (env var), or OAuth for later

---

## Architecture Overview

- API server exposes endpoints:
  - POST /upload → accept PDF, returns job id
  - GET /jobs → list jobs and statuses
  - GET /jobs/{job_id} → job details
  - POST /jobs/{job_id}/retry → trigger retry
  - GET /logs/{job_id} → tail logs
  - WebSocket /ws/jobs → push job status updates
- The dashboard listens for WebSocket updates and updates UI in real time.
- The Orchestrator posts job status events (or the orchestrator writes small status files which the API polls) — see integration options below.

---

## Integration Patterns (How orchestrator communicates with dashboard)

Option A (Recommended): Orchestrator emits status events by writing small JSON status files into `workspace/status/` and the API server watches that directory (or polls) and broadcasts updates via WebSocket.

Option B: Orchestrator issues HTTP callbacks to the API server (requires the orchestrator to have credentials and the API to be reachable from orchestrator environment).

Option C: Use a shared message queue (Redis or RabbitMQ) for event bus (more robust, heavier to run).

---

## Minimal Implementation Plan (MVP)

Phase 1 (Week 7, local MVP):
- FastAPI app with endpoints: `/upload`, `/jobs`, `/jobs/{id}`, `/logs/{id}` and WebSocket `/ws/jobs`.
- Local storage: save uploads to `uploads/`, create `jobs/` dir with job JSON files. Orchestrator writes `jobs/{id}.json` and `status/{id}.json` updates.
- Frontend: simple HTML page with upload form, job list, job detail modal, basic charts using Chart.js for convergence.
- Authentication: simple API key in env var.

Phase 2 (Week 8, polish):
- Add user-friendly log viewer with tailing
- Add report viewer (HTML/PDF preview) and download
- Add monitoring page with counters and charts
- Add unit and integration tests for API endpoints
- Dockerfile for containerized run

---

## Example API (FastAPI) skeleton

```python
from fastapi import FastAPI, UploadFile, File, WebSocket, HTTPException
from fastapi.responses import FileResponse
import uuid
import shutil
import json
from pathlib import Path

app = FastAPI()
BASE = Path(__file__).parent
UPLOADS = BASE / 'uploads'
JOBS = BASE / 'jobs'
UPLOADS.mkdir(exist_ok=True)
JOBS.mkdir(exist_ok=True)

@app.post('/upload')
async def upload(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    target = UPLOADS / f"{job_id}.pdf"
    with open(target, 'wb') as out:
        shutil.copyfileobj(file.file, out)
    # create job file
    job = {"id": job_id, "status": "queued", "file": str(target)}
    with open(JOBS / f"{job_id}.json", 'w') as f:
        json.dump(job, f)
    return {"job_id": job_id}

@app.get('/jobs')
async def list_jobs():
    jobs = []
    for p in JOBS.glob('*.json'):
        jobs.append(json.loads(p.read_text()))
    return jobs

@app.get('/jobs/{job_id}')
async def job_detail(job_id: str):
    p = JOBS / f"{job_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail='Job not found')
    return json.loads(p.read_text())
```

WebSocket example (very small):

```python
from fastapi import WebSocket

@app.websocket('/ws/jobs')
async def ws_jobs(ws: WebSocket):
    await ws.accept()
    # naive implementation: tail status dir and push changes
    while True:
        await asyncio.sleep(1)
        # read status files and send minimal updates
        await ws.send_json({"time": time.time()})
```

---

## Frontend Sketch

- Single page with:
  - Upload form
  - Jobs table (status, start time, elapsed, actions)
  - Job detail modal with logs and download button
  - Real-time progress area powered by WebSocket
  - Convergence chart using Chart.js

Keep it simple — start with plain HTML + Bootstrap, add small JS to connect the WebSocket and update DOM.

---

## Tests to Add

- API unit tests (pytest + `httpx.AsyncClient`) for `/upload`, `/jobs`, `/jobs/{id}`
- Integration test that simulates an upload, then creates a job JSON to mimic orchestrator progress and asserts the API returns updated job state
- WebSocket test to verify broadcast behavior (simple smoke)

Add tests under `tests/webui/`.

---

## Deployment & Run Local

1. Create virtualenv and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn python-multipart
```

2. Run locally:

```bash
uvicorn webdashboard:app --reload --port 8000
# open http://localhost:8000 in browser
```

3. Dockerfile (optional) provided in v1 for easy deployment.

---

## Security & Operational Notes

- Start with basic API key check for endpoints (`X-API-KEY` header) and an env var `DASHBOARD_API_KEY`.
- For production, move to OAuth or internal auth provider and TLS termination.
- Logs should be stored in job-specific files under `jobs/logs/{id}.log` and accessible via the API only to authenticated users.
- Monitor disk usage for uploads and implement retention policies.

---

## Acceptance Test Plan

1. Manual: Upload a sample PDF → verify job appears as queued and `jobs/{id}.json` is created.
2. Simulate orchestrator updates by writing `jobs/status/{id}.json` updates and confirm the WebSocket pushes the updates to the UI.
3. API test: upload → GET /jobs → job present → GET /jobs/{id} returns correct file path.
4. UI test: open dashboard, upload file, watch job appear and update.

---

## Implementation Checklist

- [ ] FastAPI skeleton with endpoints
- [ ] Frontend HTML + JS with WebSocket client
- [ ] Simple auth (API key)
- [ ] Log viewer and report download
- [ ] Dockerfile and run instructions
- [ ] Unit & integration tests
- [ ] Documentation in repo `docs/` and README

---

## Estimated Lines: ~1500-2000 (full stack)

**Notes:** Start small — local MVP with file-based communication between orchestrator and dashboard. Do not couple the orchestrator tightly to the API until the integration tests validate the interaction model.
