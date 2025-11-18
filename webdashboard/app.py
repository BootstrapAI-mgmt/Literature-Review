"""
FastAPI Web Dashboard for Literature Review Pipeline

Provides RESTful API and WebSocket endpoints for:
- Uploading PDFs
- Monitoring job status
- Viewing logs
- Triggering retries
"""

import asyncio
import io
import json
import logging
import mimetypes
import os
import shutil
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any

from webdashboard.duplicate_detector import (
    check_for_duplicates,
    load_existing_papers_from_review_log
)

# Setup logger
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Literature Review Dashboard",
    description="Web dashboard for monitoring and managing literature review pipeline jobs",
    version="1.0.0"
)

# Base paths
BASE_DIR = Path(__file__).parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
UPLOADS_DIR = WORKSPACE_DIR / "uploads"
JOBS_DIR = WORKSPACE_DIR / "jobs"
STATUS_DIR = WORKSPACE_DIR / "status"
LOGS_DIR = WORKSPACE_DIR / "logs"

# Create necessary directories
for directory in [WORKSPACE_DIR, UPLOADS_DIR, JOBS_DIR, STATUS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# API Key for authentication (from environment)
API_KEY = os.getenv("DASHBOARD_API_KEY", "dev-key-change-in-production")

# Global job runner instance
job_runner: Optional["PipelineJobRunner"] = None

# WebSocket connections manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Startup event to initialize JobRunner
@app.on_event("startup")
async def startup_event():
    """Initialize background services on app startup"""
    global job_runner
    from webdashboard.job_runner import PipelineJobRunner
    
    job_runner = PipelineJobRunner(max_workers=2)
    
    # Start background worker
    asyncio.create_task(job_runner.start())
    
    print("Dashboard started with background job runner")

# Pydantic models
class JobStatus(BaseModel):
    """Job status information"""
    id: str
    status: str  # queued, running, completed, failed
    filename: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[Dict] = None

class RetryRequest(BaseModel):
    """Request to retry a job"""
    force: bool = False

class JobConfig(BaseModel):
    """Job configuration parameters"""
    pillar_selections: List[str]
    run_mode: str  # "ONCE" or "DEEP_LOOP"
    convergence_threshold: float = 5.0  # Default convergence threshold

class PromptResponse(BaseModel):
    """User response to a prompt"""
    response: Any

class UploadConfirmRequest(BaseModel):
    """Request to confirm upload after duplicate detection"""
    action: str  # "skip_duplicates" or "overwrite_all"
    job_id: str

# Helper functions
def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key from request header"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key

def get_job_file(job_id: str) -> Path:
    """Get path to job file"""
    return JOBS_DIR / f"{job_id}.json"

def get_status_file(job_id: str) -> Path:
    """Get path to status file"""
    return STATUS_DIR / f"{job_id}.json"

def get_log_file(job_id: str) -> Path:
    """Get path to log file"""
    return LOGS_DIR / f"{job_id}.log"

def load_job(job_id: str) -> Optional[dict]:
    """Load job data from file"""
    job_file = get_job_file(job_id)
    if not job_file.exists():
        return None
    
    try:
        with open(job_file, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def save_job(job_id: str, job_data: dict):
    """Save job data to file"""
    job_file = get_job_file(job_id)
    with open(job_file, 'w') as f:
        json.dump(job_data, f, indent=2)

def extract_completeness(job_data: dict) -> float:
    """Extract overall completeness percentage from job results"""
    try:
        # Try to load gap_analysis_report.json from job outputs
        job_id = job_data.get("id")
        if not job_id:
            return 0.0
        
        report_file = JOBS_DIR / job_id / "outputs" / "gap_analysis_output" / "gap_analysis_report.json"
        if not report_file.exists():
            return 0.0
        
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        # Calculate average completeness across all pillars
        total_completeness = 0.0
        pillar_count = 0
        
        for pillar_name, pillar_data in report.items():
            if isinstance(pillar_data, dict) and "completeness" in pillar_data:
                total_completeness += pillar_data["completeness"]
                pillar_count += 1
        
        return total_completeness / pillar_count if pillar_count > 0 else 0.0
    except Exception:
        return 0.0

def extract_papers(job_data: dict) -> list:
    """Extract list of papers from job data"""
    try:
        # Get papers from uploaded files
        files = job_data.get("files", [])
        if files:
            return [f.get("original_name", f.get("filename", "")) for f in files]
        
        # Single file upload
        filename = job_data.get("filename", "")
        if filename:
            return [filename]
        
        return []
    except Exception:
        return []

def extract_gaps(job_data: dict) -> list:
    """Extract list of gaps from job results"""
    try:
        job_id = job_data.get("id")
        if not job_id:
            return []
        
        report_file = JOBS_DIR / job_id / "outputs" / "gap_analysis_output" / "gap_analysis_report.json"
        if not report_file.exists():
            return []
        
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        gaps = []
        for pillar_name, pillar_data in report.items():
            if isinstance(pillar_data, dict) and "analysis" in pillar_data:
                for req_name, req_data in pillar_data["analysis"].items():
                    if isinstance(req_data, dict):
                        for sub_req_name, sub_req_data in req_data.items():
                            if isinstance(sub_req_data, dict):
                                completeness = sub_req_data.get("completeness_percent", 0)
                                # Consider anything below 100% as a gap
                                if completeness < 100:
                                    gaps.append({
                                        "pillar": pillar_name,
                                        "requirement": req_name,
                                        "sub_requirement": sub_req_name,
                                        "completeness": completeness,
                                        "gap_analysis": sub_req_data.get("gap_analysis", "")
                                    })
        
        return gaps
    except Exception:
        return []

def extract_summary_metrics(job_data: dict) -> dict:
    """
    Extract key metrics for summary card display
    
    Args:
        job_data: Complete job data dictionary
    
    Returns:
        Dictionary with summary metrics:
        - completeness: Overall completeness percentage
        - critical_gaps: Count of critical gaps (severity >= 8)
        - paper_count: Number of papers analyzed
        - recommendations_preview: First 2 recommendations
        - has_results: Whether analysis has completed with results
    """
    # Check if job has results
    status = job_data.get("status", "")
    if status != "completed":
        return {
            "completeness": 0,
            "critical_gaps": 0,
            "paper_count": 0,
            "recommendations_preview": [],
            "has_results": False
        }
    
    # Try to load results from job outputs
    job_id = job_data.get("id")
    results = {}
    
    # Look for gap analysis results
    gap_analysis_file = JOBS_DIR / job_id / "outputs" / "gap_analysis_output" / "gap_analysis.json"
    if gap_analysis_file.exists():
        try:
            with open(gap_analysis_file, 'r') as f:
                results = json.load(f)
        except Exception:
            pass
    
    # Calculate completeness
    completeness = 0
    if results:
        # Try to get overall completeness from results
        if "overall_completeness" in results:
            completeness = results["overall_completeness"]
        elif "completeness" in results:
            completeness = results["completeness"]
        elif "pillars" in results:
            # Calculate average completeness across pillars
            pillar_data = results["pillars"]
            if isinstance(pillar_data, dict) and pillar_data:
                completeness_values = []
                for pillar_info in pillar_data.values():
                    if isinstance(pillar_info, dict) and "completeness" in pillar_info:
                        completeness_values.append(pillar_info["completeness"])
                if completeness_values:
                    completeness = sum(completeness_values) / len(completeness_values)
    
    # Count critical gaps (severity >= 8)
    critical_gaps = 0
    gaps = results.get("gaps", [])
    if isinstance(gaps, list):
        for gap in gaps:
            if isinstance(gap, dict):
                severity = gap.get("severity", 0)
                if severity >= 8:
                    critical_gaps += 1
    
    # Get paper count
    paper_count = 0
    if "papers" in job_data:
        papers = job_data.get("papers", [])
        paper_count = len(papers) if isinstance(papers, list) else 0
    elif "files" in job_data:
        files = job_data.get("files", [])
        paper_count = len(files) if isinstance(files, list) else 0
    elif "file_count" in job_data:
        paper_count = job_data.get("file_count", 0)
    
    # Get recommendations preview (first 2)
    recommendations = results.get("recommendations", [])
    if isinstance(recommendations, list):
        recommendations_preview = recommendations[:2]
    else:
        recommendations_preview = []
    
    return {
        "completeness": round(completeness, 1) if completeness else 0,
        "critical_gaps": critical_gaps,
        "paper_count": paper_count,
        "recommendations_preview": recommendations_preview,
        "has_results": bool(results)
    }

# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard page"""
    template_file = Path(__file__).parent / "templates" / "index.html"
    if template_file.exists():
        return template_file.read_text()
    return "<h1>Literature Review Dashboard</h1><p>Template not found. Please check installation.</p>"

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Upload a PDF file and create a new job
    
    Returns:
        Job ID and status
    """
    verify_api_key(api_key)
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    target_path = UPLOADS_DIR / f"{job_id}.pdf"
    try:
        with open(target_path, 'wb') as out:
            shutil.copyfileobj(file.file, out)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Create job record with default configuration
    job_data = {
        "id": job_id,
        "status": "queued",
        "filename": file.filename,
        "file_path": str(target_path),
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
        "progress": {},
        "config": {
            "pillar_selections": ["ALL"],  # Default
            "run_mode": "ONCE"  # Default
        }
    }
    
    save_job(job_id, job_data)
    
    # ENQUEUE JOB FOR PROCESSING
    if job_runner:
        await job_runner.enqueue_job(job_id, job_data)
    
    # Broadcast update to WebSocket clients
    await manager.broadcast({
        "type": "job_created",
        "job": job_data
    })
    
    return {"job_id": job_id, "status": "queued", "filename": file.filename}

@app.post("/api/upload/batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Upload multiple PDF files for a single analysis job
    
    Includes duplicate detection across existing papers in review_log.json
    
    Args:
        files: List of PDF files to upload
    
    Returns:
        Job ID and file count, or duplicate warning if duplicates detected
    """
    verify_api_key(api_key)
    
    # Validate all files are PDFs
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only PDFs allowed."
            )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Create job directory
    job_dir = UPLOADS_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    # Save all uploaded files
    uploaded_files = []
    try:
        for file in files:
            # Sanitize filename
            safe_filename = "".join(c for c in file.filename if c.isalnum() or c in "._- ")
            target_path = job_dir / safe_filename
            
            with open(target_path, 'wb') as out:
                shutil.copyfileobj(file.file, out)
            uploaded_files.append({
                "original_name": file.filename,
                "path": str(target_path),
                "size": target_path.stat().st_size,
                "title": file.filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ')
            })
    except Exception as e:
        # Cleanup on error
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save files: {str(e)}"
        )
    
    # Check for duplicates against existing papers in review_log.json
    review_log_path = BASE_DIR / "review_log.json"
    existing_papers = load_existing_papers_from_review_log(review_log_path)
    
    duplicate_check = check_for_duplicates(uploaded_files, existing_papers)
    
    # Create job record - status is "draft" until configured
    job_data = {
        "id": job_id,
        "status": "draft",  # Not queued until configured
        "files": uploaded_files,
        "file_count": len(uploaded_files),
        "created_at": datetime.utcnow().isoformat(),
        "config": None,  # Will be set when user configures job
        "duplicate_check": duplicate_check  # Store duplicate check results
    }
    
    save_job(job_id, job_data)
    
    # Check if duplicates were found
    if duplicate_check['duplicates']:
        # Return duplicate warning to user
        return {
            "status": "duplicates_found",
            "job_id": job_id,
            "duplicates": duplicate_check['duplicates'],
            "new": duplicate_check['new'],
            "matches": duplicate_check['matches'],
            "message": f"{len(duplicate_check['duplicates'])} of {len(uploaded_files)} papers already exist"
        }
    else:
        # No duplicates, proceed normally
        # Broadcast update
        await manager.broadcast({
            "type": "job_created",
            "job": job_data
        })
        
        return {
            "job_id": job_id,
            "status": "draft",
            "file_count": len(uploaded_files),
            "files": uploaded_files
        }

@app.post("/api/upload/confirm")
async def confirm_upload(
    request: UploadConfirmRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Confirm upload after duplicate warning
    
    Args:
        request: Confirmation request with action and job_id
    
    Returns:
        Updated job status
    """
    verify_api_key(api_key)
    
    job_id = request.job_id
    action = request.action
    
    # Load job data
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get duplicate check results
    duplicate_check = job_data.get('duplicate_check')
    if not duplicate_check:
        raise HTTPException(
            status_code=400,
            detail="No duplicate check results found for this job"
        )
    
    if action == "skip_duplicates":
        # Remove duplicate files from job
        new_files = [f for f in job_data['files'] 
                    if f['original_name'] not in [d['original_name'] 
                                                  for d in duplicate_check['duplicates']]]
        
        # Delete duplicate files from disk
        job_dir = UPLOADS_DIR / job_id
        for dup in duplicate_check['duplicates']:
            dup_path = Path(dup['path'])
            if dup_path.exists():
                dup_path.unlink()
        
        # Update job data
        job_data['files'] = new_files
        job_data['file_count'] = len(new_files)
        job_data['duplicates_skipped'] = len(duplicate_check['duplicates'])
        save_job(job_id, job_data)
        
        # Broadcast update
        await manager.broadcast({
            "type": "job_created",
            "job": job_data
        })
        
        return {
            "status": "success",
            "job_id": job_id,
            "uploaded": len(new_files),
            "skipped": len(duplicate_check['duplicates']),
            "message": f"Uploaded {len(new_files)} new papers, skipped {len(duplicate_check['duplicates'])} duplicates"
        }
    
    elif action == "overwrite_all":
        # Keep all files (including duplicates)
        # Just clear the duplicate check flag
        job_data['duplicates_overwritten'] = len(duplicate_check['duplicates'])
        save_job(job_id, job_data)
        
        # Broadcast update
        await manager.broadcast({
            "type": "job_created",
            "job": job_data
        })
        
        return {
            "status": "success",
            "job_id": job_id,
            "uploaded": len(job_data['files']),
            "message": f"Uploaded all {len(job_data['files'])} papers (including {len(duplicate_check['duplicates'])} duplicates)"
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {action}. Must be 'skip_duplicates' or 'overwrite_all'"
        )

@app.get("/api/jobs")
async def list_jobs(
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    List all jobs with summary metrics
    
    Returns:
        List of all jobs with their current status and summary metrics
    """
    verify_api_key(api_key)
    
    jobs = []
    for job_file in JOBS_DIR.glob("*.json"):
        try:
            with open(job_file, 'r') as f:
                job_data = json.load(f)
                
                # Extract summary metrics for each job
                summary = extract_summary_metrics(job_data)
                job_data["summary"] = summary
                
                jobs.append(job_data)
        except Exception:
            continue
    
    # Sort by created_at (newest first)
    jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"jobs": jobs, "count": len(jobs)}

@app.get("/api/jobs/{job_id}")
async def get_job(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get details for a specific job
    
    Args:
        job_id: Job identifier
    
    Returns:
        Job details including status and progress
    """
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Try to load latest status update
    status_file = get_status_file(job_id)
    if status_file.exists():
        try:
            with open(status_file, 'r') as f:
                status_data = json.load(f)
                job_data.update(status_data)
        except Exception:
            pass
    
    return job_data

@app.post("/api/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    retry_req: RetryRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Trigger a retry for a failed job
    
    Args:
        job_id: Job identifier
        retry_req: Retry request parameters
    
    Returns:
        Updated job status
    """
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Update job status to queued for retry
    job_data["status"] = "queued"
    job_data["error"] = None
    job_data["retry_requested_at"] = datetime.utcnow().isoformat()
    
    save_job(job_id, job_data)
    
    # Clear status file so it doesn't override the retry
    status_file = get_status_file(job_id)
    if status_file.exists():
        status_file.unlink()
    
    # Broadcast update
    await manager.broadcast({
        "type": "job_retry",
        "job": job_data
    })
    
    return {"job_id": job_id, "status": "queued", "message": "Retry requested"}

@app.post("/api/jobs/{job_id}/configure")
async def configure_job(
    job_id: str,
    config: JobConfig,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Configure job parameters before execution
    
    Args:
        job_id: Job identifier
        config: Job configuration (pillar selections and run mode)
    
    Returns:
        Updated job configuration
    """
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Update job configuration
    job_data["config"] = config.dict()
    save_job(job_id, job_data)
    
    return {"job_id": job_id, "config": config.dict()}

@app.post("/api/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Start execution of a configured job
    
    Args:
        job_id: Job identifier
    
    Returns:
        Confirmation with job status
    """
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_data.get("status") not in ["draft", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot be started (current status: {job_data['status']})"
        )
    
    if not job_data.get("config"):
        raise HTTPException(
            status_code=400,
            detail="Job must be configured before starting"
        )
    
    # Build research database from uploaded files
    try:
        from webdashboard.database_builder import ResearchDatabaseBuilder
        
        job_dir = UPLOADS_DIR / job_id
        pdf_files = list(job_dir.glob("*.pdf"))
        
        if not pdf_files:
            raise HTTPException(
                status_code=400,
                detail="No PDF files found for this job"
            )
        
        builder = ResearchDatabaseBuilder(job_id, pdf_files)
        csv_path = builder.build_database()
        
        # Update job data with database path
        job_data["research_database"] = str(csv_path)
        
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Database builder module not available"
        )
    except Exception as e:
        logger.error(f"Failed to build database for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build research database: {str(e)}"
        )
    
    # Update job status to queued
    job_data["status"] = "queued"
    job_data["queued_at"] = datetime.utcnow().isoformat()
    save_job(job_id, job_data)
    
    # Enqueue for processing
    if job_runner:
        await job_runner.enqueue_job(job_id, job_data)
    
    # Broadcast update
    await manager.broadcast({
        "type": "job_started",
        "job": job_data
    })
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Job queued for execution"
    }

@app.post("/api/prompts/{prompt_id}/respond")
async def respond_to_prompt(
    prompt_id: str,
    response: PromptResponse,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Submit user response to a prompt
    
    Args:
        prompt_id: Prompt identifier
        response: User's response
    
    Returns:
        Confirmation of response submission
    """
    verify_api_key(api_key)
    
    try:
        from webdashboard.prompt_handler import prompt_handler
        prompt_handler.submit_response(prompt_id, response.response)
        return {"status": "success", "prompt_id": prompt_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting prompt response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compare-jobs/{job_id_1}/{job_id_2}")
async def compare_jobs(
    job_id_1: str,
    job_id_2: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Compare two gap analysis jobs
    
    Args:
        job_id_1: First job identifier (baseline)
        job_id_2: Second job identifier (comparison)
    
    Returns:
        Comparison data with deltas and improvements
    """
    verify_api_key(api_key)
    
    # Load both jobs
    job1 = load_job(job_id_1)
    job2 = load_job(job_id_2)
    
    if not job1:
        raise HTTPException(status_code=404, detail=f"Job {job_id_1} not found")
    if not job2:
        raise HTTPException(status_code=404, detail=f"Job {job_id_2} not found")
    
    # Verify both jobs are completed
    if job1.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id_1} has not completed (status: {job1.get('status')})"
        )
    if job2.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id_2} has not completed (status: {job2.get('status')})"
        )
    
    # Extract data from both jobs
    job1_completeness = extract_completeness(job1)
    job2_completeness = extract_completeness(job2)
    job1_papers = extract_papers(job1)
    job2_papers = extract_papers(job2)
    job1_gaps = extract_gaps(job1)
    job2_gaps = extract_gaps(job2)
    
    # Calculate papers differential
    papers_added = [p for p in job2_papers if p not in job1_papers]
    papers_removed = [p for p in job1_papers if p not in job2_papers]
    
    # Calculate gaps differential
    # A gap is "filled" if it existed in job1 but not in job2 (or has higher completeness)
    gaps_filled = []
    new_gaps = []
    
    # Create dictionaries for easier comparison
    job1_gap_dict = {
        f"{g['pillar']}|{g['requirement']}|{g['sub_requirement']}": g
        for g in job1_gaps
    }
    job2_gap_dict = {
        f"{g['pillar']}|{g['requirement']}|{g['sub_requirement']}": g
        for g in job2_gaps
    }
    
    # Find gaps that were filled
    for gap_key, gap1 in job1_gap_dict.items():
        if gap_key in job2_gap_dict:
            gap2 = job2_gap_dict[gap_key]
            # Check if completeness improved
            if gap2['completeness'] > gap1['completeness']:
                gaps_filled.append({
                    "gap": f"{gap1['requirement']} - {gap1['sub_requirement']}",
                    "pillar": gap1['pillar'],
                    "improvement": gap2['completeness'] - gap1['completeness'],
                    "old_completeness": gap1['completeness'],
                    "new_completeness": gap2['completeness']
                })
        else:
            # Gap completely filled (100% in job2)
            gaps_filled.append({
                "gap": f"{gap1['requirement']} - {gap1['sub_requirement']}",
                "pillar": gap1['pillar'],
                "improvement": 100 - gap1['completeness'],
                "old_completeness": gap1['completeness'],
                "new_completeness": 100
            })
    
    # Find new gaps that appeared in job2
    for gap_key, gap2 in job2_gap_dict.items():
        if gap_key not in job1_gap_dict:
            new_gaps.append({
                "gap": f"{gap2['requirement']} - {gap2['sub_requirement']}",
                "pillar": gap2['pillar'],
                "completeness": gap2['completeness']
            })
    
    # Build comparison response
    comparison = {
        "job1": {
            "id": job_id_1,
            "timestamp": job1.get("created_at", ""),
            "completeness": round(job1_completeness, 2),
            "papers": job1_papers,
            "paper_count": len(job1_papers),
            "gap_count": len(job1_gaps)
        },
        "job2": {
            "id": job_id_2,
            "timestamp": job2.get("created_at", ""),
            "completeness": round(job2_completeness, 2),
            "papers": job2_papers,
            "paper_count": len(job2_papers),
            "gap_count": len(job2_gaps)
        },
        "delta": {
            "completeness_change": round(job2_completeness - job1_completeness, 2),
            "papers_added": papers_added,
            "papers_removed": papers_removed,
            "papers_added_count": len(papers_added),
            "papers_removed_count": len(papers_removed),
            "gaps_filled": gaps_filled,
            "gaps_filled_count": len(gaps_filled),
            "new_gaps": new_gaps,
            "new_gaps_count": len(new_gaps)
        }
    }
    
    return comparison

def format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}min {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}min"

@app.get("/api/jobs/{job_id}/progress-history")
async def get_progress_history(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get historical progress timeline for completed job
    
    Args:
        job_id: Job identifier
    
    Returns:
        Progress timeline with stage durations and performance metrics
    """
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_data.get('status') != 'completed':
        raise HTTPException(
            status_code=400,
            detail="Job not completed. Progress history only available for completed jobs."
        )
    
    # Read progress events from JSONL file
    progress_file = STATUS_DIR / f"{job_id}_progress.jsonl"
    if not progress_file.exists():
        raise HTTPException(
            status_code=404,
            detail="No progress data available for this job"
        )
    
    # Parse progress events
    events = []
    try:
        with open(progress_file, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse progress data: {str(e)}"
        )
    
    # Group events by stage and calculate durations
    stages = {}
    for event in events:
        stage = event.get('stage')
        phase = event.get('phase')
        timestamp = event.get('timestamp')
        
        if not stage or not phase or not timestamp:
            continue
        
        if stage not in stages:
            stages[stage] = {
                'stage': stage,
                'start_time': None,
                'end_time': None,
                'status': 'unknown'
            }
        
        # Track start and end times
        if phase == 'starting':
            stages[stage]['start_time'] = timestamp
            stages[stage]['status'] = 'started'
        elif phase == 'complete':
            stages[stage]['end_time'] = timestamp
            stages[stage]['status'] = 'completed'
        elif phase == 'error':
            stages[stage]['end_time'] = timestamp
            stages[stage]['status'] = 'error'
    
    # Calculate durations
    timeline = []
    total_duration = 0
    
    for stage_name, stage_data in stages.items():
        if stage_data['start_time'] and stage_data['end_time']:
            try:
                start = datetime.fromisoformat(stage_data['start_time'])
                end = datetime.fromisoformat(stage_data['end_time'])
                duration_seconds = int((end - start).total_seconds())
                
                timeline.append({
                    'stage': stage_name,
                    'start_time': stage_data['start_time'],
                    'end_time': stage_data['end_time'],
                    'duration_seconds': duration_seconds,
                    'duration_human': format_duration(duration_seconds),
                    'status': stage_data['status'],
                    'percentage': 0  # Will be calculated later
                })
                
                total_duration += duration_seconds
            except Exception:
                continue
    
    # Calculate percentages
    for item in timeline:
        if total_duration > 0:
            item['percentage'] = round((item['duration_seconds'] / total_duration) * 100, 1)
        else:
            item['percentage'] = 0
    
    # Find slowest stage
    slowest_stage = max(timeline, key=lambda x: x['duration_seconds'])['stage'] if timeline else None
    
    return {
        'job_id': job_id,
        'total_duration_seconds': total_duration,
        'total_duration_human': format_duration(total_duration),
        'timeline': timeline,
        'slowest_stage': slowest_stage,
        'start_time': job_data.get('started_at'),
        'end_time': job_data.get('completed_at')
    }

@app.get("/api/jobs/{job_id}/progress-history.csv")
async def export_progress_history_csv(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Export progress history as CSV file
    
    Args:
        job_id: Job identifier
    
    Returns:
        CSV file download
    """
    verify_api_key(api_key)
    
    # Get progress data using the existing endpoint logic
    try:
        progress_data = await get_progress_history(job_id, api_key)
    except HTTPException as e:
        raise e
    
    # Create CSV content
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Stage',
        'Start Time',
        'End Time',
        'Duration (seconds)',
        'Duration (human)',
        '% of Total',
        'Status'
    ])
    
    # Rows
    for stage in progress_data['timeline']:
        writer.writerow([
            stage['stage'],
            stage['start_time'],
            stage['end_time'],
            stage['duration_seconds'],
            stage['duration_human'],
            f"{stage['percentage']}%",
            stage['status']
        ])
    
    # Total row
    writer.writerow([])
    writer.writerow([
        'TOTAL',
        '',
        '',
        progress_data['total_duration_seconds'],
        progress_data['total_duration_human'],
        '100%',
        ''
    ])
    
    csv_content = output.getvalue()
    
    # Return as downloadable file
    from fastapi.responses import Response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=progress_history_{job_id}.csv"
        }
    )

@app.get("/api/logs/{job_id}")
async def get_job_logs(
    job_id: str,
    tail: int = 100,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get logs for a specific job
    
    Args:
        job_id: Job identifier
        tail: Number of lines to return from end of log
    
    Returns:
        Log content
    """
    verify_api_key(api_key)
    
    log_file = get_log_file(job_id)
    if not log_file.exists():
        return {"job_id": job_id, "logs": "", "message": "No logs available"}
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if tail > 0:
                lines = lines[-tail:]
            log_content = ''.join(lines)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")
    
    return {"job_id": job_id, "logs": log_content, "line_count": len(lines)}

@app.get("/api/download/{job_id}")
async def download_job_file(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Download the uploaded PDF file for a job
    
    Args:
        job_id: Job identifier
    
    Returns:
        PDF file
    """
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    file_path = Path(job_data.get("file_path", ""))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=job_data.get("filename", f"{job_id}.pdf")
    )

@app.websocket("/ws/jobs")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time job updates
    
    Clients connect here to receive live updates about job status changes
    """
    await manager.connect(websocket)
    
    try:
        # Send initial state
        jobs = []
        for job_file in JOBS_DIR.glob("*.json"):
            try:
                with open(job_file, 'r') as f:
                    jobs.append(json.load(f))
            except Exception:
                continue
        
        await websocket.send_json({
            "type": "initial_state",
            "jobs": jobs
        })
        
        # Keep connection alive and watch for status updates
        last_check = time.time()
        status_mtimes = {}
        
        while True:
            await asyncio.sleep(1)
            
            # Check for status file updates every second
            current_time = time.time()
            if current_time - last_check >= 1:
                last_check = current_time
                
                # Check all status files for updates
                for status_file in STATUS_DIR.glob("*.json"):
                    try:
                        mtime = status_file.stat().st_mtime
                        if status_file not in status_mtimes or status_mtimes[status_file] < mtime:
                            status_mtimes[status_file] = mtime
                            
                            # Read and broadcast update
                            with open(status_file, 'r') as f:
                                status_data = json.load(f)
                                await websocket.send_json({
                                    "type": "job_update",
                                    "job": status_data
                                })
                    except Exception:
                        continue
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@app.websocket("/ws/jobs/{job_id}/progress")
async def job_progress_stream(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates
    
    Streams:
    - Progress percentage
    - Stage updates
    - Log messages
    - Iteration counts
    
    Args:
        job_id: Unique job identifier
    """
    await websocket.accept()
    
    try:
        # Send initial status
        job_data = load_job(job_id)
        if job_data:
            await websocket.send_json({
                "type": "initial_status",
                "job": job_data
            })
        
        # Watch for progress updates
        progress_file = Path(f"workspace/status/{job_id}_progress.jsonl")
        log_file = Path(f"workspace/logs/{job_id}.log")
        
        last_progress_pos = 0
        last_log_pos = 0
        
        while True:
            # Check if job is still active
            current_job = load_job(job_id)
            if current_job and current_job.get("status") in ["completed", "failed"]:
                await websocket.send_json({
                    "type": "job_complete",
                    "status": current_job["status"]
                })
                break
            
            # Stream progress updates
            if progress_file.exists():
                with open(progress_file, 'r') as f:
                    f.seek(last_progress_pos)
                    new_lines = f.readlines()
                    last_progress_pos = f.tell()
                
                for line in new_lines:
                    try:
                        event = json.loads(line)
                        await websocket.send_json({
                            "type": "progress",
                            "event": event
                        })
                    except json.JSONDecodeError:
                        pass
            
            # Stream log updates
            if log_file.exists():
                with open(log_file, 'r') as f:
                    f.seek(last_log_pos)
                    new_lines = f.readlines()
                    last_log_pos = f.tell()
                
                if new_lines:
                    await websocket.send_json({
                        "type": "logs",
                        "lines": new_lines
                    })
            
            await asyncio.sleep(0.5)  # Poll every 500ms
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")

@app.get("/api/jobs/{job_id}/proof-scorecard")
async def get_proof_scorecard(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get proof scorecard summary for a job
    
    Args:
        job_id: Job identifier
    
    Returns:
        Proof scorecard summary with overall score, verdict, and recommendations
    """
    verify_api_key(api_key)
    
    scorecard_file = JOBS_DIR / job_id / "outputs" / "proof_scorecard_output" / "proof_scorecard.json"
    
    if not scorecard_file.exists():
        # Return empty response instead of 404 - this is optional output
        return {
            "available": False,
            "message": "Proof scorecard not yet generated"
        }
    
    try:
        with open(scorecard_file, 'r') as f:
            scorecard = json.load(f)
        
        return {
            "available": True,
            "overall_score": scorecard['overall_proof_status']['proof_readiness_score'],
            "verdict": scorecard['overall_proof_status']['verdict'],
            "headline": scorecard['overall_proof_status']['headline'],
            "publication_viability": scorecard.get('publication_viability', {}),
            "research_goals": scorecard.get('research_goals', [])[:3],  # Top 3
            "next_steps": scorecard.get('critical_next_steps', [])[:5],  # Top 5
            "html_path": f"/api/jobs/{job_id}/files/proof_scorecard_output/proof_readiness.html"
        }
    except Exception as e:
        logger.error(f"Failed to read proof scorecard for job {job_id}: {e}")
        return {
            "available": False,
            "message": f"Error reading proof scorecard: {str(e)}"
        }

@app.get("/api/jobs/{job_id}/cost-summary")
async def get_cost_summary(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get API cost summary for a job
    
    Args:
        job_id: Job identifier
    
    Returns:
        Cost summary with total cost, budget usage, and module breakdown
    """
    verify_api_key(api_key)
    
    cost_file = JOBS_DIR / job_id / "outputs" / "cost_reports" / "api_usage_report.json"
    
    if not cost_file.exists():
        return {
            "available": False,
            "total_cost": 0,
            "message": "No cost data available"
        }
    
    try:
        with open(cost_file, 'r') as f:
            cost_data = json.load(f)
        
        return {
            "available": True,
            "total_cost": cost_data.get("total_cost_usd", 0),
            "budget_percent": cost_data.get("budget_percent_used", 0),
            "per_paper_cost": cost_data.get("cost_per_paper", 0),
            "module_breakdown": cost_data.get("module_breakdown", {}),
            "cache_savings": cost_data.get("cache_savings_usd", 0),
            "total_tokens": cost_data.get("total_tokens", 0),
            "html_path": f"/api/jobs/{job_id}/files/cost_reports/api_usage_report.html"
        }
    except Exception as e:
        logger.error(f"Failed to read cost summary for job {job_id}: {e}")
        return {
            "available": False,
            "total_cost": 0,
            "message": f"Error reading cost data: {str(e)}"
        }

@app.get("/api/jobs/{job_id}/sufficiency-summary")
async def get_sufficiency_summary(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get evidence sufficiency summary for a job
    
    Args:
        job_id: Job identifier
    
    Returns:
        Sufficiency matrix summary with quadrant distribution
    """
    verify_api_key(api_key)
    
    sufficiency_file = JOBS_DIR / job_id / "outputs" / "gap_analysis_output" / "sufficiency_matrix.json"
    
    if not sufficiency_file.exists():
        return {
            "available": False,
            "quadrants": {},
            "message": "No sufficiency data available"
        }
    
    try:
        with open(sufficiency_file, 'r') as f:
            data = json.load(f)
        
        # Summarize by quadrant
        quadrant_summary = {}
        for req in data.get("requirements", []):
            quadrant = req.get("quadrant", "Unknown")
            if quadrant not in quadrant_summary:
                quadrant_summary[quadrant] = 0
            quadrant_summary[quadrant] += 1
        
        return {
            "available": True,
            "quadrants": quadrant_summary,
            "total_requirements": len(data.get("requirements", [])),
            "recommendations": data.get("recommendations", [])[:5],
            "html_path": f"/api/jobs/{job_id}/files/gap_analysis_output/sufficiency_matrix.html"
        }
    except Exception as e:
        logger.error(f"Failed to read sufficiency summary for job {job_id}: {e}")
        return {
            "available": False,
            "quadrants": {},
            "message": f"Error reading sufficiency data: {str(e)}"
        }

@app.get("/api/jobs/{job_id}/files/{filepath:path}")
async def get_job_output_file(
    job_id: str,
    filepath: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Serve output files from job directory
    
    Args:
        job_id: Job identifier
        filepath: Relative path to file within job outputs directory
    
    Returns:
        Requested file
    """
    verify_api_key(api_key)
    
    # Construct safe path
    full_path = JOBS_DIR / job_id / "outputs" / filepath
    
    # Security check: ensure path is within job directory
    try:
        full_path = full_path.resolve()
        job_dir = (JOBS_DIR / job_id).resolve()
        if not str(full_path).startswith(str(job_dir)):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    media_type = "text/html" if filepath.endswith(".html") else "application/json"
    
    return FileResponse(
        path=full_path,
        media_type=media_type,
        filename=full_path.name
    )

def categorize_output_file(filename: str) -> str:
    """
    Categorize output file by name pattern
    
    Args:
        filename: Name of the output file
    
    Returns:
        Category string for grouping files
    """
    if filename.startswith("waterfall_"):
        return "pillar_waterfalls"
    elif filename.startswith("_OVERALL_") or filename.startswith("_"):
        return "visualizations"
    elif filename.endswith(".json"):
        return "data"
    elif filename.endswith(".md"):
        return "reports"
    elif filename.endswith(".html"):
        return "visualizations"
    else:
        return "other"

@app.get("/api/jobs/{job_id}/results")
async def get_job_results(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get list of all output files for a job
    
    Args:
        job_id: Job identifier
    
    Returns:
        List of output files with metadata
    """
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job has not completed (status: {job_data['status']})"
        )
    
    # Get output directory
    output_dir = JOBS_DIR / job_id / "outputs" / "gap_analysis_output"
    
    if not output_dir.exists():
        return {
            "job_id": job_id,
            "output_count": 0,
            "outputs": []
        }
    
    # Collect all output files
    outputs = []
    for file_path in output_dir.rglob("*"):
        if file_path.is_file():
            # Determine file category
            category = categorize_output_file(file_path.name)
            
            outputs.append({
                "filename": file_path.name,
                "path": str(file_path.relative_to(output_dir)),
                "size": file_path.stat().st_size,
                "category": category,
                "mime_type": mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
                "modified": file_path.stat().st_mtime
            })
    
    # Sort by category then name
    outputs.sort(key=lambda x: (x["category"], x["filename"]))
    
    return {
        "job_id": job_id,
        "output_count": len(outputs),
        "outputs": outputs,
        "output_dir": str(output_dir)
    }

@app.get("/api/jobs/{job_id}/results/download/all")
async def download_all_results(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Download all job results as a ZIP file
    
    Args:
        job_id: Job identifier
    
    Returns:
        ZIP archive of all output files
    """
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_data.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    output_dir = JOBS_DIR / job_id / "outputs" / "gap_analysis_output"
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="No results found")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                # Add file to ZIP with relative path
                arcname = file_path.relative_to(output_dir)
                zip_file.write(file_path, arcname=arcname)
        
        # Add prompt history if available
        if 'prompts' in job_data and job_data['prompts']:
            # Add prompt_history.json
            prompt_history_json = json.dumps(job_data['prompts'], indent=2)
            zip_file.writestr('prompt_history.json', prompt_history_json)
            
            # Add human-readable summary
            summary = "Prompt History Summary\n" + "="*50 + "\n\n"
            for p in job_data['prompts']:
                summary += f"[{p['timestamp']}] {p['type']}\n"
                summary += f"  Response: {p.get('response', 'N/A')}\n"
                summary += f"  Status: {'TIMED OUT' if p['timed_out'] else 'OK'}\n"
                if 'prompt_data' in p and 'message' in p['prompt_data']:
                    summary += f"  Message: {p['prompt_data']['message']}\n"
                summary += "\n"
            
            zip_file.writestr('prompt_history.txt', summary)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=job_{job_id}_results.zip"
        }
    )

@app.get("/api/jobs/{job_id}/results/{file_path:path}")
async def get_job_result_file(
    job_id: str,
    file_path: str,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get a specific output file
    
    Args:
        job_id: Job identifier
        file_path: Relative path to file within output directory
    
    Returns:
        File content
    """
    verify_api_key(api_key)
    
    # Validate job exists and completed
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_data.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    # Build full file path (prevent directory traversal)
    output_dir = JOBS_DIR / job_id / "outputs" / "gap_analysis_output"
    full_path = (output_dir / file_path).resolve()
    
    # Security check: ensure path is within output directory
    if not str(full_path).startswith(str(output_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Return file
    return FileResponse(
        path=full_path,
        media_type=mimetypes.guess_type(full_path.name)[0] or "application/octet-stream",
        filename=full_path.name
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/suggest-field")
async def suggest_research_field(request: dict):
    """
    Auto-suggest research field based on paper titles and abstracts.
    
    Request body:
        {
            "papers": [
                {"title": "...", "abstract": "..."},
                ...
            ]
        }
    
    Response:
        {
            "suggested_field": "ai_ml",
            "field_name": "AI & Machine Learning",
            "half_life_years": 3.0,
            "description": "...",
            "confidence": "high|medium|low"
        }
    """
    from literature_review.utils.decay_presets import suggest_field_from_papers, get_preset
    
    papers = request.get('papers', [])
    
    if not papers:
        raise HTTPException(status_code=400, detail="No papers provided")
    
    # Analyze papers and suggest field
    suggested_field_key = suggest_field_from_papers(papers)
    preset = get_preset(suggested_field_key)
    
    # Determine confidence based on whether we got a specific field or fell back to custom
    confidence = "low" if suggested_field_key == 'custom' else "high"
    
    return {
        "suggested_field": suggested_field_key,
        "field_name": preset['name'],
        "half_life_years": preset['half_life_years'],
        "description": preset['description'],
        "examples": preset['examples'],
        "confidence": confidence
    }


@app.get("/api/field-presets")
async def get_field_presets():
    """
    Get all available research field presets.
    
    Response:
        {
            "presets": {
                "ai_ml": {...},
                "mathematics": {...},
                ...
            }
        }
    """
    from literature_review.utils.decay_presets import list_all_presets
    
    return {
        "presets": list_all_presets()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
