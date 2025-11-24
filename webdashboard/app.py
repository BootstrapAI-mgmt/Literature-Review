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
import traceback
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, Header, Request, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Any

from webdashboard.duplicate_detector import (
    check_for_duplicates,
    load_existing_papers_from_review_log
)
from webdashboard.api.incremental import router as incremental_router
from webdashboard.api.bulk_operations import router as bulk_router
from webdashboard.api.system_metrics import router as system_metrics_router

# Setup logger
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Literature Review Dashboard API",
    description="""
## REST API for Managing Literature Review Pipeline

This API enables you to:
* **Upload PDFs** - Single or batch upload of academic papers
* **Create Jobs** - Configure and start literature review analysis jobs
* **Monitor Progress** - Real-time job status and progress tracking
* **View Results** - Access gap analysis, proof scorecards, and cost summaries
* **Download Reports** - Export results as ZIP archives

### Authentication
API endpoints require an API key passed via the `X-API-KEY` header.

**Example:**
```bash
curl -H "X-API-KEY: your-api-key" http://localhost:5001/api/jobs
```

### Base URL
- Development: `http://localhost:5001`
- Production: Configure via environment variables

### WebSocket Support
Real-time updates available via WebSocket endpoints at `/ws/jobs` and `/ws/jobs/{job_id}/progress`
    """,
    version="2.0.0",
    contact={
        "name": "Literature Review Team",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
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

# Register API routers
app.include_router(incremental_router)
app.include_router(bulk_router)
app.include_router(system_metrics_router)

# Global exception handler for better error logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Log all unhandled exceptions with full traceback"""
    logger.error(f"Unhandled exception in {request.method} {request.url.path}")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception message: {str(exc)}")
    logger.error(f"Full traceback:\n{traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# API Key for authentication (from environment)
API_KEY = os.getenv("DASHBOARD_API_KEY", "dev-key-change-in-production")

# Cost estimation constants
DEFAULT_CACHE_HIT_RATE = 0.8  # Assume 80% cache hit rate for cost estimates

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

# Pydantic models with enhanced documentation
class JobStatus(BaseModel):
    """
    Job status information
    
    Represents the current state of a literature review job.
    """
    id: str
    status: str  # queued, running, completed, failed
    filename: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[Dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "filename": "research_paper.pdf",
                "created_at": "2024-11-17T12:00:00Z",
                "started_at": "2024-11-17T12:01:00Z",
                "completed_at": "2024-11-17T13:00:00Z",
                "error": None,
                "progress": {"percentage": 100, "stage": "complete"}
            }
        }

class RetryRequest(BaseModel):
    """
    Request to retry a failed job
    
    Args:
        force: Force retry even if job is not in failed state
    """
    force: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "force": False
            }
        }

class JobConfig(BaseModel):
    """
    Job configuration parameters
    
    Defines how the literature review analysis should be performed.
    
    Args:
        pillar_selections: List of analysis pillars to include (use ["ALL"] for all pillars)
        run_mode: Execution mode - "ONCE" for single pass, "DEEP_LOOP" for iterative analysis
        convergence_threshold: Threshold percentage for convergence in DEEP_LOOP mode (default: 5.0)
        output_dir_mode: Output directory mode - "auto", "custom", or "existing" (default: "auto")
        output_dir_path: Custom output directory path (required if output_dir_mode is "custom" or "existing")
        overwrite_existing: Whether to overwrite existing results (default: False)
        
        Input method options (PARITY-W3-2):
        input_method: Input method - "upload" or "directory" (default: "upload")
        data_dir: Server directory path for directory input method
        scan_recursive: Whether to scan subdirectories (default: True)
        follow_symlinks: Whether to follow symbolic links (default: False)
        
        Advanced options:
        dry_run: Validate configuration without making API calls (default: False)
        force: Force re-analysis even if recent results exist (default: False)
        clear_cache: Delete all cached API responses before starting (default: False)
        budget: Maximum spending for this job in USD (default: None for unlimited)
        relevance_threshold: Minimum semantic similarity for paper relevance (0.0-1.0, default: 0.7)
        resume_from_stage: Skip completed stages and resume from checkpoint (default: None)
        resume_from_checkpoint: Continue from saved checkpoint file (default: None)
        experimental: Enable cutting-edge experimental features (default: False)
    """
    pillar_selections: List[str]
    run_mode: str  # "ONCE" or "DEEP_LOOP"
    convergence_threshold: float = 5.0
    output_dir_mode: str = "auto"  # "auto" | "custom" | "existing"
    output_dir_path: Optional[str] = None
    overwrite_existing: bool = False
    
    # Input method options (PARITY-W3-2)
    input_method: str = "upload"  # "upload" or "directory"
    data_dir: Optional[str] = None  # Server directory path for directory input
    scan_recursive: bool = True
    follow_symlinks: bool = False
    
    # Advanced options
    dry_run: bool = False
    force: bool = False
    force_confirmed: bool = False
    clear_cache: bool = False
    budget: Optional[float] = None
    relevance_threshold: float = 0.7
    resume_from_stage: Optional[str] = None
    resume_from_checkpoint: Optional[str] = None
    experimental: bool = False
    
    # Pre-filter configuration (PARITY-W2-5)
    pre_filter: Optional[str] = None  # None=default, ""=full, "section1,section2"=custom
    
    class Config:
        json_schema_extra = {
            "example": {
                "pillar_selections": ["ALL"],
                "run_mode": "ONCE",
                "convergence_threshold": 5.0,
                "output_dir_mode": "auto",
                "output_dir_path": None,
                "overwrite_existing": False,
                "input_method": "upload",
                "data_dir": None,
                "scan_recursive": True,
                "follow_symlinks": False,
                "dry_run": False,
                "force": False,
                "clear_cache": False,
                "budget": 5.00,
                "relevance_threshold": 0.7,
                "experimental": False
            }
        }

class PromptResponse(BaseModel):
    """
    User response to an interactive prompt
    
    Args:
        response: The user's response value (type varies by prompt)
    """
    response: Any
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "yes"
            }
        }

class UploadConfirmRequest(BaseModel):
    """
    Request to confirm upload after duplicate detection
    
    Args:
        action: Action to take - "skip_duplicates" to exclude duplicates, "overwrite_all" to include all
        job_id: Job identifier returned from batch upload
    """
    action: str  # "skip_duplicates" or "overwrite_all"
    job_id: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "skip_duplicates",
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }

class UploadResponse(BaseModel):
    """Response from file upload"""
    job_id: str
    status: str
    filename: Optional[str] = None
    file_count: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "queued",
                "filename": "research_paper.pdf"
            }
        }

class JobListResponse(BaseModel):
    """Response containing list of jobs"""
    jobs: List[Dict]
    count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "completed",
                        "filename": "paper.pdf",
                        "created_at": "2024-11-17T12:00:00Z"
                    }
                ],
                "count": 1
            }
        }

class ImportResultsRequest(BaseModel):
    """Request to import existing analysis results"""
    results_dir: str
    job_name: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "results_dir": "/workspaces/Literature-Review/gap_analysis_output",
                "job_name": "My Analysis"
            }
        }

class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Job not found"
            }
        }


class CheckpointScanRequest(BaseModel):
    """Request to scan directory for checkpoint files"""
    directory: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "directory": "/workspaces/Literature-Review/workspace/jobs/abc123/outputs"
            }
        }


class ResumeJobRequest(BaseModel):
    """Request to resume a failed job"""
    auto_resume: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "auto_resume": True
            }
        }


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""
    paper_count: int = Field(..., ge=1, le=1000)
    use_cache: bool = True
    model: Optional[str] = "gemini-1.5-pro"
    
    class Config:
        json_schema_extra = {
            "example": {
                "paper_count": 10,
                "use_cache": False,
                "model": "gemini-1.5-pro"
            }
        }


class DirectoryScanRequest(BaseModel):
    """
    Request to scan a server directory for paper files (PDFs/CSVs).
    
    This enables users to point to existing papers on the server without uploading.
    
    Args:
        path: Absolute path to directory containing papers
        recursive: Whether to scan subdirectories (default: True)
        follow_symlinks: Whether to follow symbolic links (default: False)
    """
    path: str
    recursive: bool = True
    follow_symlinks: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "path": "/workspaces/Literature-Review/data/papers",
                "recursive": True,
                "follow_symlinks": False
            }
        }


class DirectoryScanResponse(BaseModel):
    """Response from directory scan operation."""
    path: str
    pdf_count: int
    csv_count: int
    total_files: int
    total_size_bytes: int
    subdirectory_count: int
    recursive: bool
    follow_symlinks: bool
    files: List[Dict[str, Any]]
    
    class Config:
        json_schema_extra = {
            "example": {
                "path": "/workspaces/Literature-Review/data/papers",
                "pdf_count": 10,
                "csv_count": 2,
                "total_files": 12,
                "total_size_bytes": 52428800,
                "subdirectory_count": 3,
                "recursive": True,
                "follow_symlinks": False,
                "files": [
                    {
                        "filename": "paper1.pdf",
                        "relative_path": "paper1.pdf",
                        "absolute_path": "/workspaces/Literature-Review/data/papers/paper1.pdf",
                        "type": "pdf",
                        "size_bytes": 1024000,
                        "modified": "2024-01-15T10:30:00",
                        "created": "2024-01-10T08:00:00"
                    }
                ]
            }
        }


class PipelineConfig(BaseModel):
    """
    Pipeline configuration schema matching pipeline_config.json.
    
    This validates custom configuration files uploaded by users.
    """
    version: str
    models: Optional[Dict[str, str]] = None
    pre_filtering: Optional[Dict[str, Any]] = None
    prefilter: Optional[Dict[str, Any]] = None  # Alternative name
    roi_optimizer: Optional[Dict[str, Any]] = None
    retry_policy: Optional[Dict[str, Any]] = None
    evidence_decay: Optional[Dict[str, Any]] = None
    deduplication: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    v2_features: Optional[Dict[str, Any]] = None
    stage_timeout: Optional[int] = None
    log_level: Optional[str] = None
    version_history_path: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "version": "2.0.0",
                "models": {
                    "gap_extraction": "gemini-1.5-pro",
                    "relevance": "gemini-1.5-flash"
                },
                "pre_filtering": {
                    "enabled": True,
                    "threshold": 0.6
                }
            }
        }


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


# Allowed directory prefixes for security (directory input feature)
# Users can only scan directories within these paths
ALLOWED_DIRECTORY_PREFIXES = [
    Path.home(),  # User's home directory
    Path("/workspaces"),  # GitHub Codespaces workspaces
    Path("/data"),  # Shared data directory
    Path("/mnt"),  # Mounted drives
    Path("/tmp"),  # Temporary directory
]


def get_allowed_directory_prefixes() -> List[Path]:
    """
    Get allowed directory prefixes, including the BASE_DIR.
    
    Returns:
        List of Path objects representing allowed directory prefixes
    """
    prefixes = list(ALLOWED_DIRECTORY_PREFIXES)
    # Always allow BASE_DIR (project root)
    prefixes.append(BASE_DIR)
    return prefixes


def is_path_allowed(path: Path) -> bool:
    """
    Check if a path is within allowed directories.
    
    Security check to prevent path traversal attacks.
    
    Args:
        path: Resolved absolute path to check
        
    Returns:
        True if path is within an allowed prefix
    """
    allowed_prefixes = get_allowed_directory_prefixes()
    path_str = str(path)
    return any(path_str.startswith(str(prefix)) for prefix in allowed_prefixes)


def extract_file_metadata(file_path: Path, base_dir: Path) -> Dict[str, Any]:
    """
    Extract metadata from a file for directory scan results.
    
    Args:
        file_path: Absolute path to the file
        base_dir: Base directory for computing relative path
        
    Returns:
        Dictionary with file metadata
    """
    stat = file_path.stat()
    
    return {
        "filename": file_path.name,
        "relative_path": str(file_path.relative_to(base_dir)),
        "absolute_path": str(file_path),
        "type": file_path.suffix.lstrip('.').lower(),
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
    }


def find_config_overrides(
    custom: Dict[str, Any],
    default: Dict[str, Any],
    path: str = ""
) -> List[str]:
    """
    Find all configuration overrides recursively.
    
    Args:
        custom: Custom configuration dictionary
        default: Default configuration dictionary
        path: Current path in the config tree (for nested keys)
    
    Returns:
        List of override descriptions
    """
    overrides = []
    
    for key, value in custom.items():
        current_path = f"{path}.{key}" if path else key
        
        if key not in default:
            overrides.append(f"Added: {current_path} = {value}")
            
        elif isinstance(value, dict) and isinstance(default.get(key), dict):
            # Recurse for nested dicts
            overrides.extend(
                find_config_overrides(value, default[key], current_path)
            )
            
        elif value != default.get(key):
            overrides.append(
                f"Changed: {current_path} from {default.get(key)} to {value}"
            )
    
    return overrides


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

def detect_directory_state(output_dir: Path) -> Dict[str, any]:
    """
    Analyze output directory to determine what analysis mode to use.
    
    Returns:
        {
            "state": "empty" | "has_csv" | "has_results" | "not_exist",
            "recommended_mode": "baseline" | "continuation",
            "file_count": int,
            "has_gap_report": bool,
            "csv_files": List[str],
            "last_modified": str (ISO datetime)
        }
    """
    result = {
        "state": "not_exist",
        "recommended_mode": "baseline",
        "file_count": 0,
        "has_gap_report": False,
        "csv_files": [],
        "last_modified": None
    }
    
    # Case 1: Directory doesn't exist
    if not output_dir.exists():
        result["state"] = "not_exist"
        result["recommended_mode"] = "baseline"
        return result
    
    # Count files
    all_files = list(output_dir.glob("*"))
    result["file_count"] = len(all_files)
    
    # Check for gap analysis report
    gap_report = output_dir / "gap_analysis_report.json"
    result["has_gap_report"] = gap_report.exists()
    
    # Find CSV files
    csv_files = list(output_dir.glob("*.csv"))
    result["csv_files"] = [f.name for f in csv_files]
    
    # Get last modified time
    if all_files:
        latest_file = max(all_files, key=lambda f: f.stat().st_mtime)
        result["last_modified"] = datetime.fromtimestamp(
            latest_file.stat().st_mtime
        ).isoformat()
    
    # Determine state
    if result["file_count"] == 0:
        # Empty directory
        result["state"] = "empty"
        result["recommended_mode"] = "baseline"
        
    elif result["has_gap_report"]:
        # Has previous analysis results
        result["state"] = "has_results"
        result["recommended_mode"] = "continuation"
        
    elif len(result["csv_files"]) > 0:
        # Has CSV files but no analysis results
        result["state"] = "has_csv"
        result["recommended_mode"] = "baseline"
        
    else:
        # Has files but nothing recognizable
        result["state"] = "empty"
        result["recommended_mode"] = "baseline"
    
    return result


def get_recommendation_reason(state: Dict) -> str:
    """Generate human-readable recommendation."""
    if state["state"] == "not_exist":
        return "Directory doesn't exist. Will create and run fresh analysis."
    elif state["state"] == "empty":
        return "Directory is empty. Will run fresh baseline analysis."
    elif state["state"] == "has_csv":
        return f"Found {len(state['csv_files'])} CSV files. Will run fresh analysis on these papers."
    elif state["state"] == "has_results":
        return f"Found existing analysis (last updated: {state['last_modified']}). Can continue or overwrite."
    else:
        return "Will run fresh baseline analysis."


def validate_checkpoint_file(checkpoint_path: str) -> Path:
    """
    Validate checkpoint file exists and has valid structure.
    
    Returns validated Path object.
    Raises HTTPException if invalid.
    """
    checkpoint = Path(checkpoint_path)
    
    if not checkpoint.exists():
        raise HTTPException(404, f"Checkpoint file not found: {checkpoint_path}")
    
    try:
        with open(checkpoint) as f:
            data = json.load(f)
        
        # Validate required fields
        required_fields = ["pipeline_version", "status", "stages"]
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            raise HTTPException(
                400,
                f"Invalid checkpoint: missing fields {missing}"
            )
        
        return checkpoint
        
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Invalid checkpoint JSON: {str(e)}")


# API Endpoints
@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["System"],
    summary="Dashboard homepage",
    include_in_schema=False  # Hide from API docs (it's a web page)
)
async def root():
    """Serve the main dashboard page"""
    template_file = Path(__file__).parent / "templates" / "index.html"
    if template_file.exists():
        return template_file.read_text()
    return "<h1>Literature Review Dashboard</h1><p>Template not found. Please check installation.</p>"

@app.get(
    "/genealogy",
    response_class=HTMLResponse,
    tags=["System"],
    summary="Job genealogy visualization page",
    include_in_schema=False  # Hide from API docs (it's a web page)
)
async def genealogy():
    """Serve the job genealogy visualization page"""
    template_file = Path(__file__).parent / "templates" / "job_genealogy.html"
    if template_file.exists():
        return template_file.read_text()
    return "<h1>Job Genealogy</h1><p>Template not found. Please check installation.</p>"

@app.post(
    "/api/upload",
    response_model=UploadResponse,
    tags=["Papers"],
    summary="Upload a PDF file",
    responses={
        200: {
            "description": "PDF uploaded successfully and job created",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "queued",
                        "filename": "research_paper.pdf"
                    }
                }
            }
        },
        400: {
            "description": "Invalid file type (not PDF)",
            "model": ErrorResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        500: {
            "description": "Server error during file upload",
            "model": ErrorResponse
        }
    }
)
async def upload_file(
    file: UploadFile = File(..., description="PDF file to upload"),
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Upload a single PDF file and create a new analysis job.
    
    This endpoint:
    1. Validates the uploaded file is a PDF
    2. Creates a unique job ID
    3. Saves the file to the uploads directory
    4. Queues the job for processing
    5. Broadcasts the update to WebSocket clients
    
    **Requirements:**
    - File must be in PDF format
    - Valid API key required in X-API-KEY header
    
    **Returns:**
    - job_id: Unique identifier for tracking the job
    - status: Initial status (always "queued")
    - filename: Original filename of uploaded PDF
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

@app.post(
    "/api/upload/batch",
    tags=["Papers"],
    summary="Upload multiple PDFs (batch)",
    responses={
        200: {
            "description": "PDFs uploaded successfully (may include duplicate warning)",
        },
        400: {
            "description": "Invalid file type (not PDF)",
            "model": ErrorResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        500: {
            "description": "Server error during upload",
            "model": ErrorResponse
        }
    }
)
async def upload_batch(
    files: List[UploadFile] = File(..., description="List of PDF files to upload"),
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Upload multiple PDF files for a single analysis job with duplicate detection.
    
    This endpoint:
    1. Validates all files are PDFs
    2. Creates a job directory
    3. Saves uploaded files
    4. Checks for duplicates against existing papers in review_log.json
    5. Returns duplicate warning if matches found
    
    **Duplicate Handling:**
    - If duplicates detected, response includes `status: "duplicates_found"`
    - Use `/api/upload/confirm` to choose action:
      - `skip_duplicates`: Upload only new papers
      - `overwrite_all`: Upload all papers including duplicates
    
    **Requirements:**
    - All files must be PDF format
    - Valid API key required in X-API-KEY header
    
    **Returns:**
    - job_id: Unique identifier for the job
    - status: "draft" (no duplicates) or "duplicates_found"
    - file_count: Number of files uploaded
    - files: List of uploaded file metadata
    - duplicates: List of duplicate files (if any)
    - new: List of new files (if duplicates found)
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

@app.post(
    "/api/upload/confirm",
    tags=["Papers"],
    summary="Confirm batch upload after duplicate detection",
    responses={
        200: {
            "description": "Upload confirmed and processed",
        },
        400: {
            "description": "Invalid action or no duplicate check results",
            "model": ErrorResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Job not found",
            "model": ErrorResponse
        }
    }
)
async def confirm_upload(
    request: UploadConfirmRequest,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Confirm batch upload after receiving duplicate detection warning.
    
    **Actions:**
    - `skip_duplicates`: Remove duplicate files from job, upload only new papers
    - `overwrite_all`: Keep all files including duplicates
    
    This endpoint:
    1. Validates job exists with duplicate check results
    2. Processes action (skip or overwrite)
    3. Updates job data accordingly
    4. Broadcasts update to WebSocket clients
    
    **Use Case:**
    1. POST /api/upload/batch returns `status: "duplicates_found"`
    2. User reviews duplicates list
    3. User calls this endpoint with chosen action
    4. Job proceeds with final file list
    
    **Returns:**
    - status: "success"
    - job_id: Job identifier
    - uploaded: Number of files kept
    - skipped: Number of duplicates removed (if skip_duplicates)
    - message: Human-readable confirmation
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

@app.post(
    "/api/directory/scan",
    response_model=DirectoryScanResponse,
    tags=["Papers"],
    summary="Scan server directory for paper files",
    responses={
        200: {
            "description": "Directory scanned successfully",
        },
        400: {
            "description": "Invalid path (not a directory or invalid format)",
            "model": ErrorResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        403: {
            "description": "Access denied (path traversal or restricted directory)",
            "model": ErrorResponse
        },
        404: {
            "description": "Directory not found or no papers found",
            "model": ErrorResponse
        }
    }
)
async def scan_directory(
    request: DirectoryScanRequest,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Scan a server directory for PDF and CSV paper files.
    
    This endpoint enables users to point to existing papers on the server
    instead of uploading files. The directory is scanned for PDF and CSV files,
    with optional recursive scanning and symlink following.
    
    **Security:**
    - Only directories within allowed paths can be scanned
    - Path traversal attempts are rejected
    - Requires valid API key
    
    **Use Cases:**
    - Papers already exist on the server
    - Large number of files (50+)
    - Papers on mounted drives or network shares
    - Avoiding re-upload of existing files
    
    **CLI Equivalent:**
    This maps to the CLI's `--data-dir` flag.
    
    **Request Body:**
    - path: Absolute path to directory (e.g., "/workspaces/Literature-Review/data/")
    - recursive: Scan subdirectories (default: true)
    - follow_symlinks: Follow symbolic links (default: false)
    
    **Returns:**
    - File counts (PDF/CSV)
    - Total size in bytes
    - Subdirectory count
    - List of discovered files with metadata
    """
    verify_api_key(api_key)
    
    # Validate and resolve path
    try:
        directory = Path(request.path).expanduser().resolve()
    except Exception as e:
        raise HTTPException(400, f"Invalid path format: {str(e)}")
    
    # Security: Must be absolute path
    if not request.path.startswith('/') and not request.path.startswith('~'):
        # Allow Windows paths too
        if len(request.path) < 2 or request.path[1] != ':':
            raise HTTPException(
                400,
                "Path must be absolute (e.g., /path/to/directory or C:\\path)"
            )
    
    # Security: Prevent path traversal - check if resolved path is within allowed directories
    if not is_path_allowed(directory):
        allowed_list = ", ".join(str(p) for p in get_allowed_directory_prefixes())
        raise HTTPException(
            403,
            f"Access denied. Directory must be within allowed locations: {allowed_list}"
        )
    
    # Check directory exists
    if not directory.exists():
        raise HTTPException(404, f"Directory not found: {directory}")
    
    # Check is directory (not a file)
    if not directory.is_dir():
        raise HTTPException(400, f"Path is not a directory: {directory}")
    
    # Check read permissions
    if not os.access(directory, os.R_OK):
        raise HTTPException(403, f"No read permission for directory: {directory}")
    
    # Scan for files
    files: List[Dict[str, Any]] = []
    pdf_count = 0
    csv_count = 0
    total_size = 0
    subdirs: set = set()
    
    try:
        if request.recursive:
            # Recursive scan using glob
            for pattern in ["**/*.pdf", "**/*.PDF"]:
                for pdf_file in directory.glob(pattern):
                    if pdf_file.is_file():
                        # Check if we should follow symlinks
                        if pdf_file.is_symlink() and not request.follow_symlinks:
                            continue
                        
                        files.append(extract_file_metadata(pdf_file, directory))
                        pdf_count += 1
                        total_size += pdf_file.stat().st_size
                        
                        # Track subdirectory
                        if pdf_file.parent != directory:
                            subdirs.add(pdf_file.parent)
            
            for pattern in ["**/*.csv", "**/*.CSV"]:
                for csv_file in directory.glob(pattern):
                    if csv_file.is_file():
                        if csv_file.is_symlink() and not request.follow_symlinks:
                            continue
                        
                        files.append(extract_file_metadata(csv_file, directory))
                        csv_count += 1
                        total_size += csv_file.stat().st_size
                        
                        if csv_file.parent != directory:
                            subdirs.add(csv_file.parent)
        else:
            # Non-recursive: only top level
            for item in directory.iterdir():
                if item.is_file():
                    # Check symlinks
                    if item.is_symlink() and not request.follow_symlinks:
                        continue
                    
                    suffix = item.suffix.lower()
                    if suffix == '.pdf':
                        files.append(extract_file_metadata(item, directory))
                        pdf_count += 1
                        total_size += item.stat().st_size
                    elif suffix == '.csv':
                        files.append(extract_file_metadata(item, directory))
                        csv_count += 1
                        total_size += item.stat().st_size
        
    except PermissionError as e:
        raise HTTPException(403, f"Permission denied while scanning: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Error scanning directory: {str(e)}")
    
    # Validate found files
    if pdf_count == 0 and csv_count == 0:
        raise HTTPException(
            404,
            f"No PDF or CSV files found in directory: {directory}"
        )
    
    # Sort files by relative path
    files.sort(key=lambda f: f["relative_path"])
    
    return DirectoryScanResponse(
        path=str(directory),
        pdf_count=pdf_count,
        csv_count=csv_count,
        total_files=pdf_count + csv_count,
        total_size_bytes=total_size,
        subdirectory_count=len(subdirs),
        recursive=request.recursive,
        follow_symlinks=request.follow_symlinks,
        files=files
    )

@app.post(
    "/api/upload/analyze-directory",
    tags=["Papers"],
    summary="Analyze directory state for fresh analysis detection",
    responses={
        200: {
            "description": "Directory state analysis completed",
        },
        400: {
            "description": "Invalid directory path",
            "model": ErrorResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    }
)
async def analyze_directory_state(
    request: Request,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Analyze directory to recommend baseline vs continuation mode.
    
    Called by frontend when user selects output directory.
    This endpoint detects whether a directory is empty, has CSV files,
    or contains previous analysis results, and recommends the appropriate
    analysis mode.
    
    **Request Body:**
    - directory_path: Path to the output directory to analyze
    
    **Returns:**
    - directory: Resolved directory path
    - state: Directory state information (file count, has_gap_report, etc.)
    - recommendation: Recommended mode and reason
    """
    verify_api_key(api_key)
    
    # Parse request body
    body = await request.json()
    directory_path = body.get("directory_path")
    
    if not directory_path:
        raise HTTPException(status_code=400, detail="directory_path is required")
    
    output_dir = Path(directory_path).expanduser().resolve()
    
    # Security check: validate path is safe
    if not output_dir.is_absolute():
        output_dir = (BASE_DIR / output_dir).resolve()
    
    # Validate path is not a system directory
    system_dirs = ['/etc', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/boot', '/sys', '/proc']
    if any(str(output_dir).startswith(sys_dir) for sys_dir in system_dirs):
        raise HTTPException(status_code=400, detail="Cannot use system directories as output path")
    
    state = detect_directory_state(output_dir)
    
    return {
        "directory": str(output_dir),
        "state": state,
        "recommendation": {
            "mode": state["recommended_mode"],
            "reason": get_recommendation_reason(state)
        }
    }

@app.get(
    "/api/jobs",
    response_model=JobListResponse,
    tags=["Jobs"],
    summary="List all jobs",
    responses={
        200: {
            "description": "List of all jobs with summary metrics",
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    }
)
async def list_jobs(
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    List all jobs with summary metrics.
    
    Returns all jobs sorted by creation time (newest first) with:
    - Basic job information (ID, status, timestamps)
    - Summary metrics (completeness, critical gaps, paper count)
    - Progress indicators
    
    **Response includes:**
    - jobs: Array of job objects with full details
    - count: Total number of jobs
    
    **Summary metrics for each job:**
    - completeness: Overall analysis completeness percentage (0-100)
    - critical_gaps: Number of critical gaps identified
    - paper_count: Number of papers in the analysis
    - recommendations_preview: First 2 recommendations
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

@app.get(
    "/api/jobs/{job_id}",
    tags=["Jobs"],
    summary="Get job details",
    responses={
        200: {
            "description": "Job details including status and progress",
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Job not found",
            "model": ErrorResponse
        }
    }
)
async def get_job(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Get detailed information for a specific job.
    
    Retrieves comprehensive job information including:
    - Job configuration (pillar selections, run mode)
    - Current status and progress
    - Timestamps (created, started, completed)
    - Error information (if failed)
    - Latest status updates
    
    **Path Parameters:**
    - job_id: Unique job identifier (UUID format)
    
    **Returns:**
    Complete job object with all metadata and status information
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

@app.post(
    "/api/jobs/{job_id}/retry",
    tags=["Jobs"],
    summary="Retry a failed job",
    responses={
        200: {
            "description": "Job retry initiated",
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Job not found",
            "model": ErrorResponse
        }
    }
)
async def retry_job(
    job_id: str,
    retry_req: RetryRequest,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Retry a failed job.
    
    This endpoint:
    1. Updates job status to "queued"
    2. Clears error information
    3. Removes old status file
    4. Re-queues job for processing
    5. Broadcasts update to WebSocket clients
    
    **Use Cases:**
    - Job failed due to temporary error (network, API rate limit, etc.)
    - Job failed due to invalid configuration (after fixing config)
    - Force retry a job for debugging purposes
    
    **Parameters:**
    - force: Force retry even if job is not in failed state (default: false)
    
    **Path Parameters:**
    - job_id: Unique job identifier
    
    **Returns:**
    - job_id: Job identifier
    - status: New status (always "queued")
    - message: Confirmation message
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

@app.post(
    "/api/jobs/{job_id}/configure",
    tags=["Jobs"],
    summary="Configure job parameters",
    responses={
        200: {
            "description": "Job configured successfully",
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Job not found",
            "model": ErrorResponse
        }
    }
)
async def configure_job(
    job_id: str,
    config: JobConfig,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Configure job parameters before execution.
    
    **Configuration Options:**
    
    **Pillar Selections:**
    - `["ALL"]`: Analyze all available pillars
    - Specific pillars: `["Technical Foundation", "Methodology", ...]`
    
    **Run Modes:**
    - `ONCE`: Single-pass analysis (faster, recommended for most cases)
    - `DEEP_LOOP`: Iterative analysis until convergence (thorough but slower)
    
    **Convergence Threshold:**
    - Only applies to DEEP_LOOP mode
    - Percentage change threshold to stop iterations (default: 5.0)
    - Lower values = more iterations, higher precision
    
    **Output Directory Configuration:**
    - `output_dir_mode`: "auto" (default), "custom", or "existing"
    - `output_dir_path`: Required for "custom" and "existing" modes
    - `overwrite_existing`: Whether to overwrite existing results
    
    **Advanced Options:**
    - `dry_run`: Validate configuration without making API calls
    - `force`: Force re-analysis even if recent results exist
    - `clear_cache`: Delete all cached API responses before starting
    - `budget`: Maximum spending for this job in USD
    - `relevance_threshold`: Minimum semantic similarity for paper relevance (0.0-1.0)
    - `resume_from_stage`: Skip completed stages and resume from checkpoint
    - `resume_from_checkpoint`: Continue from saved checkpoint file
    - `experimental`: Enable cutting-edge experimental features
    
    **Workflow:**
    1. Upload PDFs (via /api/upload or /api/upload/batch)
    2. Call this endpoint to configure the job
    3. (Optional) Call /api/jobs/{job_id}/upload-config to upload custom config file
    4. Call /api/jobs/{job_id}/start to begin processing
    
    **Path Parameters:**
    - job_id: Unique job identifier
    
    **Returns:**
    - job_id: Job identifier
    - config: Configured parameters
    - output_dir: Resolved output directory path
    """
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Determine output directory based on mode
    if config.output_dir_mode == "auto":
        # Original behavior: auto-generate job_id directory
        output_dir = JOBS_DIR / job_id / "outputs" / "gap_analysis_output"
        
    elif config.output_dir_mode == "custom":
        # User-specified custom path
        if not config.output_dir_path:
            raise HTTPException(status_code=400, detail="Custom path required when output_dir_mode is 'custom'")
        
        output_dir = Path(config.output_dir_path).expanduser().resolve()
        
        # Security check: prevent directory traversal
        # Allow paths within project or explicit absolute paths
        if not output_dir.is_absolute():
            # Resolve relative paths from BASE_DIR
            output_dir = (BASE_DIR / output_dir).resolve()
        
        # Validate path is not a system directory
        system_dirs = ['/etc', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/boot', '/sys', '/proc']
        if any(str(output_dir).startswith(sys_dir) for sys_dir in system_dirs):
            raise HTTPException(status_code=400, detail="Cannot use system directories as output path")
        
    elif config.output_dir_mode == "existing":
        # Reuse existing directory
        if not config.output_dir_path:
            raise HTTPException(status_code=400, detail="Existing path required when output_dir_mode is 'existing'")
        
        output_dir = Path(config.output_dir_path).resolve()
        if not output_dir.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {output_dir}")
        
        # Always overwrite when reusing existing directory
        config.overwrite_existing = True
    else:
        raise HTTPException(status_code=400, detail=f"Invalid output_dir_mode: {config.output_dir_mode}")
    
    # Detect directory state for fresh analysis determination
    dir_state = detect_directory_state(output_dir)
    
    # Create/validate output directory
    if config.overwrite_existing or not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        # Check if directory has existing analysis
        if (output_dir / "gap_analysis_report.json").exists():
            raise HTTPException(
                status_code=409,
                detail=f"Directory {output_dir} contains existing analysis. "
                       "Enable 'overwrite_existing' to proceed."
            )
    
    # Determine if this is fresh analysis
    # Fresh analysis is triggered for: not_exist, empty, or has_csv states
    fresh_analysis = dir_state["state"] in ["not_exist", "empty", "has_csv"]
    
    # Handle directory input method (PARITY-W3-2)
    if config.input_method == "directory":
        if not config.data_dir:
            raise HTTPException(
                status_code=400,
                detail="data_dir is required when input_method is 'directory'"
            )
        
        # Validate the data directory using the scan endpoint logic
        try:
            scan_request = DirectoryScanRequest(
                path=config.data_dir,
                recursive=config.scan_recursive,
                follow_symlinks=config.follow_symlinks
            )
            scan_result = await scan_directory(scan_request, api_key)
            
            # Store directory input metadata in job data
            job_data["input_method"] = "directory"
            job_data["data_dir"] = scan_result.path
            job_data["file_count"] = scan_result.total_files
            job_data["pdf_count"] = scan_result.pdf_count
            job_data["csv_count"] = scan_result.csv_count
            job_data["scan_recursive"] = config.scan_recursive
            job_data["follow_symlinks"] = config.follow_symlinks
            
        except HTTPException as e:
            # Re-raise with more context
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Directory validation failed: {e.detail}"
            )
    
    # Update job configuration with resolved output directory
    config_dict = config.dict()
    config_dict["output_dir"] = str(output_dir)
    job_data["config"] = config_dict
    job_data["fresh_analysis"] = fresh_analysis
    job_data["directory_state"] = dir_state
    save_job(job_id, job_data)
    
    return {
        "job_id": job_id,
        "config": config_dict,
        "output_dir": str(output_dir),
        "fresh_analysis": fresh_analysis,
        "directory_state": dir_state,
        "input_method": job_data.get("input_method", "upload"),
        "data_dir": job_data.get("data_dir"),
        "file_count": job_data.get("file_count")
    }


@app.post(
    "/api/config/validate",
    tags=["Configuration"],
    summary="Validate custom pipeline configuration",
    responses={
        200: {
            "description": "Configuration validation result",
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    }
)
async def validate_config(
    config: Dict[str, Any],
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Validate uploaded pipeline configuration against schema.
    
    This endpoint validates a custom pipeline_config.json file and returns
    information about what settings will be overridden compared to defaults.
    
    **Request Body:**
    - config: Configuration dictionary to validate
    
    **Returns:**
    - valid: Boolean indicating if configuration is valid
    - config: Validated configuration (if valid)
    - overrides: List of settings that differ from defaults
    - overrides_count: Number of override settings
    - errors: List of validation errors (if invalid)
    """
    verify_api_key(api_key)
    
    try:
        # Validate against schema
        validated_config = PipelineConfig(**config)
        
        # Load default config for comparison
        default_config_path = BASE_DIR / "pipeline_config.json"
        with open(default_config_path) as f:
            default_config = json.load(f)
        
        # Find overrides
        overrides = find_config_overrides(config, default_config)
        
        return {
            "valid": True,
            "config": validated_config.dict(exclude_none=True),
            "overrides": overrides,
            "overrides_count": len(overrides)
        }
        
    except Exception as e:
        logger.error(f"Config validation error: {e}")
        error_message = str(e)
        
        # Extract more user-friendly error messages from Pydantic errors
        errors = [error_message]
        
        return {
            "valid": False,
            "errors": errors,
            "config": None,
            "overrides": [],
            "overrides_count": 0
        }


@app.get(
    "/api/config/template",
    tags=["Configuration"],
    summary="Download default configuration template",
    responses={
        200: {
            "description": "Configuration template file",
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Template file not found",
            "model": ErrorResponse
        }
    }
)
async def download_config_template(
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Download default pipeline_config.json as template.
    
    This returns the default configuration file that can be used as a starting
    point for creating custom configurations.
    
    **Returns:**
    - File download of pipeline_config_template.json
    """
    verify_api_key(api_key)
    
    config_path = BASE_DIR / "pipeline_config.json"
    
    if not config_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Configuration template file not found"
        )
    
    return FileResponse(
        path=config_path,
        filename="pipeline_config_template.json",
        media_type="application/json"
    )


@app.post(
    "/api/jobs/{job_id}/upload-config",
    tags=["Jobs"],
    summary="Upload custom config file for job",
    responses={
        200: {
            "description": "Config file uploaded successfully",
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Job not found",
            "model": ErrorResponse
        }
    }
)
async def upload_config_file(
    job_id: str,
    config_file: UploadFile = File(...),
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Upload a custom pipeline_config.json file for a job.
    
    **Path Parameters:**
    - job_id: Unique job identifier
    
    **Returns:**
    - job_id: Job identifier
    - config_path: Path to uploaded config file
    - valid: Whether config is valid
    - errors: Validation errors (if any)
    """
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Validate it's a JSON file
    if not config_file.filename or not config_file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Config file must be JSON")
    
    # Create job directory
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    custom_config_path = job_dir / "custom_config.json"
    
    try:
        # Read and parse config content
        content = await config_file.read()
        config_data = json.loads(content)
        
        # Validate config
        try:
            validated_config = PipelineConfig(**config_data)
            is_valid = True
            errors = []
        except Exception as e:
            is_valid = False
            errors = [str(e)]
            logger.warning(f"Invalid config uploaded for job {job_id}: {e}")
        
        # Save uploaded config file
        with open(custom_config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Store path in job data
        job_data["custom_config_path"] = str(custom_config_path)
        job_data["config_uploaded"] = True
        job_data["config_valid"] = is_valid
        save_job(job_id, job_data)
        
        return {
            "job_id": job_id,
            "config_path": str(custom_config_path),
            "valid": is_valid,
            "errors": errors
        }
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save config file: {str(e)}"
        )

@app.post(
    "/api/cost/estimate",
    tags=["Cost Management"],
    summary="Estimate analysis cost with/without cache",
    responses={
        200: {"description": "Cost estimate calculated successfully"},
        401: {"description": "Invalid or missing API key", "model": ErrorResponse}
    }
)
async def estimate_cost(
    request: CostEstimateRequest,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Estimate cost for analysis with and without cache.
    
    Used by force re-analysis warning to show cost impact.
    Provides estimates based on paper count and model selection.
    """
    verify_api_key(api_key)
    
    # Model pricing (input/output per 1M tokens)
    model_pricing = {
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-2.0-flash-exp": {"input": 0.00, "output": 0.00},  # Free tier
    }
    
    pricing = model_pricing.get(request.model, model_pricing["gemini-1.5-pro"])
    
    # Estimate tokens per paper per stage
    tokens_per_paper = {
        "gap_extraction": {"input": 3000, "output": 500},
        "relevance": {"input": 2000, "output": 200},
        "deep_review": {"input": 5000, "output": 1500}
    }
    
    # Calculate fresh cost (no cache)
    fresh_cost = 0.0
    for stage, tokens in tokens_per_paper.items():
        input_cost = (tokens["input"] * request.paper_count / 1_000_000) * pricing["input"]
        output_cost = (tokens["output"] * request.paper_count / 1_000_000) * pricing["output"]
        fresh_cost += input_cost + output_cost
    
    # Cached cost (assume default cache hit rate)
    cache_hit_rate = DEFAULT_CACHE_HIT_RATE if request.use_cache else 0.0
    cached_cost = fresh_cost * (1 - cache_hit_rate)
    
    return {
        "paper_count": request.paper_count,
        "model": request.model,
        "fresh_cost": round(fresh_cost, 2),
        "cached_cost": round(cached_cost, 2),
        "savings": round(fresh_cost - cached_cost, 2),
        "cache_hit_rate": cache_hit_rate
    }


@app.get(
    "/api/cache/stats",
    tags=["Cache Management"],
    summary="Get cache statistics",
    responses={
        200: {"description": "Cache statistics retrieved successfully"},
        401: {"description": "Invalid or missing API key", "model": ErrorResponse}
    }
)
async def get_cache_stats(
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Get cache statistics for all cache directories.
    
    Shows size, entry count, hit rate, age.
    """
    verify_api_key(api_key)
    
    cache_dirs = [
        BASE_DIR / "cache",
        BASE_DIR / "deep_reviewer_cache",
        BASE_DIR / "judge_cache"
    ]
    
    stats = {}
    
    for cache_dir in cache_dirs:
        if not cache_dir.exists():
            continue
        
        # Count files and size
        files = list(cache_dir.rglob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        
        # Get oldest and newest
        if files:
            oldest = min(files, key=lambda f: f.stat().st_mtime)
            newest = max(files, key=lambda f: f.stat().st_mtime)
            
            stats[cache_dir.name] = {
                "entry_count": len(files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_entry": datetime.fromtimestamp(
                    oldest.stat().st_mtime
                ).isoformat(),
                "newest_entry": datetime.fromtimestamp(
                    newest.stat().st_mtime
                ).isoformat()
            }
        else:
            stats[cache_dir.name] = {
                "entry_count": 0,
                "total_size_mb": 0.0,
                "oldest_entry": None,
                "newest_entry": None
            }
    
    return {
        "caches": stats,
        "total_entries": sum(s["entry_count"] for s in stats.values()),
        "total_size_mb": sum(s["total_size_mb"] for s in stats.values())
    }

@app.post(
    "/api/jobs/{job_id}/start",
    tags=["Jobs"],
    summary="Start a configured job",
    responses={
        200: {
            "description": "Job started successfully",
        },
        400: {
            "description": "Job cannot be started (invalid status or missing configuration)",
            "model": ErrorResponse
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        },
        404: {
            "description": "Job not found",
            "model": ErrorResponse
        },
        500: {
            "description": "Failed to build research database",
            "model": ErrorResponse
        }
    }
)
async def start_job(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Start execution of a configured job.
    
    This endpoint:
    1. Validates job exists and is in 'draft' or 'failed' status
    2. Verifies job configuration is complete
    3. Builds research database from uploaded PDFs
    4. Queues job for processing
    5. Broadcasts update to WebSocket clients
    
    **Prerequisites:**
    - Job must be in 'draft' or 'failed' status
    - Job configuration must be set (via /api/jobs/{job_id}/configure)
    - At least one PDF file must be uploaded for the job
    
    **Path Parameters:**
    - job_id: Unique job identifier
    
    **Returns:**
    - job_id: Job identifier
    - status: New status (always "queued")
    - message: Confirmation message
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
    
    # Validate force re-analysis confirmation
    config = job_data.get("config", {})
    if config.get("force") and not config.get("force_confirmed"):
        raise HTTPException(
            status_code=400,
            detail="Force re-analysis requires cost impact confirmation"
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

@app.post(
    "/api/prompts/{prompt_id}/respond",
    tags=["Interactive"],
    summary="Respond to interactive prompt",
    responses={
        200: {"description": "Response submitted successfully"},
        404: {"description": "Prompt not found", "model": ErrorResponse},
        500: {"description": "Error submitting response", "model": ErrorResponse}
    }
)
async def respond_to_prompt(
    prompt_id: str,
    response: PromptResponse,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Submit user response to an interactive prompt.
    
    During job execution, the system may pause to request user input
    (e.g., paper selection, configuration confirmation). This endpoint
    allows you to respond to those prompts.
    
    **Workflow:**
    1. Job execution pauses and emits prompt via WebSocket
    2. Prompt includes unique `prompt_id`
    3. User reviews prompt and makes decision
    4. User calls this endpoint with response
    5. Job execution resumes
    
    **Path Parameters:**
    - prompt_id: Unique prompt identifier (from WebSocket message)
    
    **Request Body:**
    - response: User's response (type varies by prompt)
      - Boolean: true/false
      - String: user input text
      - Number: numeric selection
      - Array: multi-select options
    
    **Returns:**
    - status: "success"
    - prompt_id: Prompt identifier
    
    **Note:** Prompts have a timeout (default: 5 minutes). If no response
    is received, the job may continue with default behavior or fail.
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

@app.get(
    "/api/compare-jobs/{job_id_1}/{job_id_2}",
    tags=["Analysis"],
    summary="Compare two jobs",
    responses={
        200: {"description": "Job comparison data"},
        400: {"description": "One or both jobs not completed", "model": ErrorResponse},
        404: {"description": "One or both jobs not found", "model": ErrorResponse}
    }
)
async def compare_jobs(
    job_id_1: str,
    job_id_2: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Compare two gap analysis jobs to identify improvements and changes.
    
    Analyzes differences between two literature review runs to track:
    - Overall completeness improvements
    - Papers added or removed
    - Gaps filled (requirements that improved)
    - New gaps discovered
    
    **Use Cases:**
    - Track progress after adding new papers
    - Measure impact of methodology changes
    - Identify regression in completeness
    - Audit literature review evolution
    
    **Path Parameters:**
    - job_id_1: First job identifier (baseline/earlier)
    - job_id_2: Second job identifier (comparison/later)
    
    **Prerequisites:**
    - Both jobs must be in "completed" status
    
    **Returns:**
    - job1: Baseline job summary
    - job2: Comparison job summary
    - delta: Detailed differences
      - completeness_change: Percentage point change
      - papers_added/removed: Paper differences
      - gaps_filled: Requirements that improved
      - new_gaps: New requirements needing attention
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

@app.get(
    "/api/jobs/{job_id}/progress-history",
    tags=["Jobs"],
    summary="Get progress history timeline",
    responses={
        200: {"description": "Progress history with stage durations"},
        400: {"description": "Job not completed", "model": ErrorResponse},
        404: {"description": "Job not found or no progress data", "model": ErrorResponse}
    }
)
async def get_progress_history(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Get historical progress timeline for completed job with stage durations.
    
    Returns detailed breakdown of time spent in each processing stage,
    useful for performance analysis and optimization.
    
    **Path Parameters:**
    - job_id: Unique job identifier
    
    **Prerequisites:**
    - Job must be in "completed" status
    - Progress tracking must have been enabled
    
    **Returns:**
    - job_id: Job identifier
    - total_duration_seconds: Total job runtime in seconds
    - total_duration_human: Human-readable format (e.g., "1h 23min")
    - timeline: Array of stage objects with durations
    - slowest_stage: Name of stage that took longest
    - start_time/end_time: Job timestamps
    
    **Stage Information:**
    - stage: Stage name (e.g., "deep_review", "gap_analysis")
    - start_time/end_time: ISO timestamps
    - duration_seconds: Time in seconds
    - duration_human: Human-readable format
    - status: "completed" or "error"
    - percentage: Percentage of total runtime
    
    **Use Cases:**
    - Performance analysis
    - Identify bottlenecks
    - Estimate future job durations
    - Optimize processing configuration
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

@app.get(
    "/api/jobs/{job_id}/progress-history.csv",
    tags=["Jobs"],
    summary="Export progress history as CSV",
    responses={
        200: {"description": "CSV file download"},
        400: {"description": "Job not completed", "model": ErrorResponse},
        404: {"description": "Job not found or no progress data", "model": ErrorResponse}
    }
)
async def export_progress_history_csv(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Export progress history as CSV file for analysis in spreadsheet tools.
    
    Downloads the same data as /api/jobs/{job_id}/progress-history
    but in CSV format for easier analysis in Excel, Google Sheets, etc.
    
    **Path Parameters:**
    - job_id: Unique job identifier
    
    **Prerequisites:**
    - Job must be in "completed" status
    
    **Returns:**
    CSV file with columns:
    - Stage
    - Start Time
    - End Time
    - Duration (seconds)
    - Duration (human)
    - % of Total
    - Status
    
    **Use Cases:**
    - Import into spreadsheet for analysis
    - Create custom visualizations
    - Compare multiple job runs
    - Generate performance reports
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

@app.get(
    "/api/logs/{job_id}",
    tags=["Logs"],
    summary="Get job logs",
    responses={
        200: {
            "description": "Job logs retrieved successfully",
        },
        401: {
            "description": "Invalid or missing API key",
            "model": ErrorResponse
        }
    }
)
async def get_job_logs(
    job_id: str,
    tail: int = 100,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Get logs for a specific job.
    
    Returns the most recent log lines for debugging and monitoring purposes.
    
    **Query Parameters:**
    - tail: Number of lines to return from end of log (default: 100)
      - Set to 0 or negative value for entire log
      - Maximum practical limit: ~10000 lines
    
    **Path Parameters:**
    - job_id: Unique job identifier
    
    **Returns:**
    - job_id: Job identifier
    - logs: Log content as string (newline-separated)
    - line_count: Number of lines returned
    - message: Info message if no logs available
    
    **Log Format:**
    ```
    [2024-11-17 12:01:00] Starting deep review...
    [2024-11-17 12:05:00] Processing paper 1/5...
    [2024-11-17 12:10:00] Gap analysis starting...
    ```
    
    **Use Cases:**
    - Monitor job progress in real-time
    - Debug failed jobs
    - Audit job execution
    - Track resource usage
    
    **Note:** For real-time log streaming, use WebSocket endpoint:
    `ws://localhost:5001/ws/jobs/{job_id}/progress`
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

@app.get(
    "/api/download/{job_id}",
    tags=["Papers"],
    summary="Download uploaded PDF",
    responses={
        200: {"description": "PDF file download"},
        404: {"description": "Job or file not found", "model": ErrorResponse}
    }
)
async def download_job_file(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Download the original uploaded PDF file for a job.
    
    **Path Parameters:**
    - job_id: Unique job identifier
    
    **Returns:**
    PDF file with original filename
    
    **Use Cases:**
    - Retrieve original papers for reference
    - Backup uploaded files
    - Verify uploaded content
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

@app.get(
    "/api/jobs/{job_id}/proof-scorecard",
    tags=["Results"],
    summary="Get proof scorecard summary",
    responses={
        200: {"description": "Proof scorecard summary or not available message"}
    }
)
async def get_proof_scorecard(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Get proof scorecard summary with overall score and recommendations.
    
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

@app.get(
    "/api/jobs/{job_id}/cost-summary",
    tags=["Results"],
    summary="Get API cost summary",
    responses={
        200: {"description": "Cost summary or not available message"}
    }
)
async def get_cost_summary(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Get API cost summary with total cost and module breakdown.
    
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

@app.get(
    "/api/jobs/{job_id}/sufficiency-summary",
    tags=["Results"],
    summary="Get evidence sufficiency summary",
    responses={
        200: {"description": "Sufficiency summary or not available message"}
    }
)
async def get_sufficiency_summary(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Get evidence sufficiency summary with quadrant distribution.
    
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

@app.get(
    "/api/jobs/{job_id}/files/{filepath:path}",
    tags=["Results"],
    summary="Get job output file",
    responses={
        200: {"description": "File content"},
        400: {"description": "Invalid file path", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "File not found", "model": ErrorResponse}
    }
)
async def get_job_output_file(
    job_id: str,
    filepath: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Serve output files from job directory (e.g., HTML reports).
    
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

@app.get(
    "/api/jobs/{job_id}/results",
    tags=["Results"],
    summary="Get list of result files",
    responses={
        200: {
            "description": "List of output files with metadata",
        },
        400: {
            "description": "Job not completed",
            "model": ErrorResponse
        },
        404: {
            "description": "Job not found",
            "model": ErrorResponse
        }
    }
)
async def get_job_results(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Get list of all output files for a completed job.
    
    Returns metadata for all generated files including:
    - JSON data files (gap analysis, scores, etc.)
    - HTML visualizations (charts, reports, etc.)
    - Markdown reports
    - Waterfall charts per pillar
    
    **File Categories:**
    - `data`: JSON files with raw analysis data
    - `reports`: Markdown reports
    - `visualizations`: HTML charts and graphs
    - `pillar_waterfalls`: Waterfall charts per pillar
    - `other`: Miscellaneous files
    
    **Prerequisites:**
    - Job must be in "completed" status
    
    **Path Parameters:**
    - job_id: Unique job identifier
    
    **Returns:**
    - job_id: Job identifier
    - output_count: Total number of files
    - outputs: Array of file metadata objects
    - output_dir: Path to output directory
    
    **Use this data to:**
    - Browse available result files
    - Download specific files via /api/jobs/{job_id}/results/{file_path}
    - Download all files via /api/jobs/{job_id}/results/download/all
    """
    # Verify API key
    verify_api_key(api_key)
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_data.get("status") not in ["completed", "imported"]:
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

@app.get(
    "/api/jobs/{job_id}/results/download/all",
    tags=["Results"],
    summary="Download all results as ZIP",
    responses={
        200: {"description": "ZIP archive download"},
        400: {"description": "Job not completed", "model": ErrorResponse},
        404: {"description": "Job not found or no results", "model": ErrorResponse}
    }
)
async def download_all_results(
    job_id: str,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Download all job results as a ZIP archive.
    
    **Path Parameters:**
    - job_id: Unique job identifier
    
    **Prerequisites:**
    - Job must be in "completed" status
    
    **ZIP Contents:**
    - All output files from gap_analysis_output/
    - prompt_history.json (if prompts were used)
    - prompt_history.txt (human-readable summary)
    
    **Returns:**
    application/zip file named `job_{job_id}_results.zip`
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

@app.get(
    "/api/jobs/{job_id}/results/{file_path:path}",
    tags=["Results"],
    summary="Download specific result file",
    responses={
        200: {"description": "File content"},
        400: {"description": "Job not completed", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "File not found", "model": ErrorResponse}
    }
)
async def get_job_result_file(
    job_id: str,
    file_path: str
):
    """
    Download a specific output file from job results.
    
    **Path Parameters:**
    - job_id: Unique job identifier
    - file_path: Relative path to file (from /api/jobs/{job_id}/results)
    
    **Prerequisites:**
    - Job must be in "completed" status
    
    **Security:**
    - Path traversal attempts are blocked
    - Access limited to job's output directory
    
    **Returns:**
    File content with appropriate MIME type
    """
    # No API key required for viewing results (read-only)
    
    # Validate job exists and completed
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_data.get("status") not in ["completed", "imported"]:
        raise HTTPException(status_code=400, detail="Job not completed")
    
    # Build full file path (prevent directory traversal)
    output_dir = JOBS_DIR / job_id / "outputs" / "gap_analysis_output"
    full_path = (output_dir / file_path).resolve()
    
    # Security check: ensure path is within output directory
    if not str(full_path).startswith(str(output_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine content type
    content_type = mimetypes.guess_type(full_path.name)[0] or "application/octet-stream"
    
    # For HTML files - return as HTMLResponse for inline display
    # Use FileResponse for large files to avoid memory issues
    if full_path.suffix.lower() == '.html':
        file_size = full_path.stat().st_size
        if file_size > 1_000_000:  # Files larger than 1MB
            # Use FileResponse with proper headers for large HTML files
            return FileResponse(
                path=full_path,
                media_type='text/html',
                headers={
                    "Content-Disposition": "inline",
                    "Cache-Control": "no-cache"
                }
            )
        else:
            # Read and return small HTML files directly
            with open(full_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
    
    # For JSON, text, markdown - display inline
    elif content_type in ['application/json', 'text/plain', 'text/markdown'] or full_path.suffix.lower() in ['.json', '.md', '.txt']:
        return FileResponse(
            path=full_path,
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename={full_path.name}"}
        )
    else:
        # Return file for download
        return FileResponse(
            path=full_path,
            media_type=content_type,
            filename=full_path.name
        )

@app.get(
    "/health",
    tags=["System"],
    summary="Health check endpoint",
    responses={
        200: {
            "description": "Service is healthy",
        }
    }
)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns basic service status and version information.
    
    **Use Cases:**
    - Kubernetes/Docker health probes
    - Load balancer health checks
    - Service monitoring and alerting
    - Uptime monitoring
    
    **Returns:**
    - status: "healthy" (always if service is running)
    - version: API version
    - timestamp: Current server time (UTC ISO format)
    
    **Example Response:**
    ```json
    {
      "status": "healthy",
      "version": "2.0.0",
      "timestamp": "2024-11-17T12:00:00.000000"
    }
    ```
    
    **Note:** This endpoint does not require API key authentication.
    """
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post(
    "/api/suggest-field",
    tags=["Analysis"],
    summary="Auto-suggest research field",
    responses={
        200: {
            "description": "Research field suggestion",
        },
        400: {
            "description": "No papers provided",
            "model": ErrorResponse
        }
    }
)
async def suggest_research_field(request: dict):
    """
    Auto-suggest research field based on paper titles and abstracts.
    
    Uses AI to analyze paper content and suggest the most appropriate
    research field configuration for evidence decay settings.
    
    **Request Body:**
    ```json
    {
      "papers": [
        {
          "title": "Deep Learning for Natural Language Processing",
          "abstract": "This paper explores transformer architectures..."
        }
      ]
    }
    ```
    
    **Response:**
    ```json
    {
      "suggested_field": "ai_ml",
      "field_name": "AI & Machine Learning",
      "half_life_years": 3.0,
      "description": "Fast-moving field with rapid innovation",
      "examples": ["neural networks", "transformers", "LLMs"],
      "confidence": "high"
    }
    ```
    
    **Confidence Levels:**
    - `high`: Strong match to known research field
    - `medium`: Partial match, consider reviewing suggestion
    - `low`: Fallback to custom field, manual configuration recommended
    
    **Supported Fields:**
    - AI & Machine Learning (3 year half-life)
    - Computer Science (7 year half-life)
    - Mathematics (50 year half-life)
    - Biology & Life Sciences (10 year half-life)
    - Physics (15 year half-life)
    - And more...
    
    **Use Cases:**
    - Configure evidence decay for new literature review
    - Validate field selection
    - Explore field characteristics
    
    **Note:** This endpoint does not require API key authentication.
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


@app.get(
    "/api/field-presets",
    tags=["Analysis"],
    summary="Get research field presets",
    responses={
        200: {
            "description": "All available field presets",
        }
    }
)
async def get_field_presets():
    """
    Get all available research field presets for evidence decay configuration.
    
    Returns complete catalog of pre-configured research fields with their
    evidence decay parameters (half-life), descriptions, and examples.
    
    **Response Structure:**
    ```json
    {
      "presets": {
        "ai_ml": {
          "name": "AI & Machine Learning",
          "half_life_years": 3.0,
          "description": "Fast-moving field with rapid innovation cycles",
          "examples": ["neural networks", "deep learning", "transformers"]
        },
        "mathematics": {
          "name": "Pure Mathematics",
          "half_life_years": 50.0,
          "description": "Theoretical field with long-lasting foundational work",
          "examples": ["number theory", "topology", "algebra"]
        }
      }
    }
    ```
    
    **Half-Life Explanation:**
    - Number of years for evidence to decay to 50% relevance
    - Lower values = faster-moving fields (e.g., AI/ML: 3 years)
    - Higher values = slower-moving fields (e.g., Mathematics: 50 years)
    
    **Available Presets:**
    - ai_ml: AI & Machine Learning (3 years)
    - computer_science: Computer Science (7 years)
    - biology: Biology & Life Sciences (10 years)
    - physics: Physics (15 years)
    - chemistry: Chemistry (12 years)
    - medicine: Medicine & Healthcare (8 years)
    - mathematics: Pure Mathematics (50 years)
    - engineering: Engineering (12 years)
    - social_sciences: Social Sciences (15 years)
    - custom: Custom field (configure manually)
    
    **Use Cases:**
    - Browse available research fields
    - Select appropriate field for literature review
    - Understand evidence decay characteristics
    - Configure custom half-life based on similar field
    
    **Note:** This endpoint does not require API key authentication.
    """
    from literature_review.utils.decay_presets import list_all_presets
    
    return {
        "presets": list_all_presets()
    }


@app.get(
    "/api/scan-import-directories",
    tags=["Results"],
    summary="Scan workspace for importable result directories",
    responses={
        200: {"description": "List of importable directories"},
        401: {"description": "Invalid or missing API key", "model": ErrorResponse}
    }
)
async def scan_import_directories(
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Scan the workspace for directories containing gap analysis results.
    
    Returns a list of directories that contain at least one of:
    - gap_analysis_report.json
    - executive_summary.md
    """
    verify_api_key(api_key)
    
    workspace_path = Path("/workspaces/Literature-Review")
    importable_dirs = []
    
    # Check common locations
    common_paths = [
        workspace_path / "gap_analysis_output",
        workspace_path / "outputs",
        workspace_path / "proof_scorecard_output"
    ]
    
    # Also scan for any gap_analysis_output directories
    for item in workspace_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            if 'output' in item.name.lower() or 'results' in item.name.lower():
                common_paths.append(item)
    
    for dir_path in set(common_paths):
        if dir_path.exists() and dir_path.is_dir():
            # Check for required files
            has_report = (dir_path / "gap_analysis_report.json").exists()
            has_summary = (dir_path / "executive_summary.md").exists()
            
            if has_report or has_summary:
                importable_dirs.append({
                    "path": str(dir_path),
                    "name": dir_path.name,
                    "has_report": has_report,
                    "has_summary": has_summary,
                    "file_count": sum(1 for _ in dir_path.rglob("*") if _.is_file())
                })
    
    return {"directories": importable_dirs}


@app.get(
    "/api/scan-output-directories",
    tags=["Configuration"],
    summary="Scan for existing output directories",
    responses={
        200: {"description": "List of existing output directories"},
        401: {"description": "Invalid or missing API key", "model": ErrorResponse}
    }
)
async def scan_output_directories(
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Scan for existing gap analysis output directories.
    
    Returns directories containing gap_analysis_report.json for reuse.
    This enables users to:
    - Continue analysis in existing directories
    - Select existing directories from dropdown
    - View metadata about existing analyses
    
    **Search Locations:**
    - gap_analysis_output/ (default CLI output)
    - workspace/jobs/*/outputs/gap_analysis_output/ (dashboard outputs)
    - ~/literature_review_outputs/ (user home directory)
    
    **Response Fields:**
    - path: Full path to output directory
    - file_count: Number of files in directory
    - last_modified: ISO timestamp of last modification
    - has_report: Whether gap_analysis_report.json exists
    """
    verify_api_key(api_key)
    
    directories = []
    
    # Scan common locations - use current working directory and workspace
    search_paths = [
        Path.cwd() / "gap_analysis_output",
        WORKSPACE_DIR / "gap_analysis_output",
        JOBS_DIR,
        Path.home() / "literature_review_outputs"
    ]
    
    for search_path in search_paths:
        if not search_path.exists():
            continue
        
        # Find directories with gap_analysis_report.json
        try:
            for report_file in search_path.rglob("gap_analysis_report.json"):
                output_dir = report_file.parent
                
                # Skip if already in list
                output_dir_str = str(output_dir)
                if any(d['path'] == output_dir_str for d in directories):
                    continue
                
                # Count files
                file_count = sum(1 for _ in output_dir.glob("*") if _.is_file())
                
                # Get last modified time
                last_modified = datetime.fromtimestamp(
                    output_dir.stat().st_mtime
                ).isoformat()
                
                directories.append({
                    "path": output_dir_str,
                    "file_count": file_count,
                    "last_modified": last_modified,
                    "has_report": True
                })
        except (PermissionError, OSError):
            # Skip directories we can't access
            continue
    
    return {"directories": directories, "count": len(directories)}


@app.post(
    "/api/import-results",
    tags=["Results"],
    summary="Import existing analysis results from external directory",
    responses={
        200: {"description": "Results imported successfully"},
        400: {"description": "Invalid directory or no results found", "model": ErrorResponse},
        401: {"description": "Invalid or missing API key", "model": ErrorResponse}
    }
)
async def import_results(
    request: ImportResultsRequest,
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Import existing gap analysis results from an external directory.
    
    This enables viewing and comparing results from:
    - Previous CLI runs (e.g., gap_analysis_output/)
    - Historical analyses
    - Manually copied result folders
    
    **Parameters:**
    - results_dir: Path to directory containing gap analysis outputs
    - job_name: Optional friendly name for imported results
    
    **Prerequisites:**
    - Directory must contain at least one of:
      - gap_analysis_report.json
      - executive_summary.md
      - Waterfall chart HTML files
    
    **Returns:**
    - job_id: Generated ID for the imported results
    - imported_files: Count of files imported
    - job_name: Name assigned to the import
    
    **Behavior:**
    - Creates a pseudo-job entry with status "imported"
    - Copies result files to workspace/jobs/{job_id}/outputs/
    - Makes results browsable like regular dashboard jobs
    - Preserves original file timestamps where possible
    """
    verify_api_key(api_key)
    
    logger.info(f"Import request: results_dir={request.results_dir}, job_name={request.job_name}")
    
    # Validate results directory exists
    source_dir = Path(request.results_dir).resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory not found: {request.results_dir}")
    
    # Check for required files
    required_files = [
        "gap_analysis_report.json",
        "executive_summary.md"
    ]
    
    has_required = any((source_dir / f).exists() for f in required_files)
    if not has_required:
        raise HTTPException(
            status_code=400,
            detail=f"No valid gap analysis results found in {request.results_dir}. "
                   "Expected at least gap_analysis_report.json or executive_summary.md"
        )
    
    # Validate gap_analysis_report.json structure if it exists
    report_path = source_dir / "gap_analysis_report.json"
    if report_path.exists():
        try:
            import json
            with open(report_path, 'r') as f:
                report_data = json.load(f)
                # Check for expected structure from our literature review system
                if not isinstance(report_data, dict):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid gap_analysis_report.json: Expected JSON object"
                    )
                # Optionally check for key fields (pillars, gaps, etc.)
                if 'pillars' not in report_data and 'gaps' not in report_data:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid gap_analysis_report.json: Missing expected fields (pillars or gaps)"
                    )
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid gap_analysis_report.json: Not valid JSON"
            )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=400,
                detail=f"Error validating gap_analysis_report.json: {str(e)}"
            )
    
    # Generate job ID for imported results
    import_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    # Create job directory structure
    job_dir = JOBS_DIR / import_id
    output_dir = job_dir / "outputs" / "gap_analysis_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all files from source to destination
    imported_count = 0
    for item in source_dir.rglob("*"):
        if item.is_file():
            # Calculate relative path
            rel_path = item.relative_to(source_dir)
            dest_path = output_dir / rel_path
            
            # Create parent directories
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(item, dest_path)
            imported_count += 1
    
    # Check if we have source PDFs (indicates pipeline can be re-run)
    has_source_pdfs = any(
        f.suffix.lower() == '.pdf' 
        for f in source_dir.rglob('*.pdf')
    )
    
    # Create job metadata
    job_data = {
        "id": import_id,
        "status": "imported",
        "filename": request.job_name or f"Imported from {source_dir.name}",
        "created_at": datetime.now().isoformat(),
        "source": "import",
        "source_directory": str(source_dir),
        "imported_files": imported_count,
        "completed_at": datetime.now().isoformat(),
        "has_source_pdfs": has_source_pdfs,
        "rerunnable": has_source_pdfs,  # Can only re-run if we have source PDFs
        "import_note": "Results-only import" if not has_source_pdfs else "Import includes source PDFs"
    }
    
    # Save job metadata
    save_job(import_id, job_data)
    
    logger.info(f"Imported {imported_count} files from {request.results_dir} as job {import_id} (has_source_pdfs={has_source_pdfs})")
    
    return {
        "job_id": import_id,
        "imported_files": imported_count,
        "job_name": job_data["filename"],
        "message": f"Successfully imported {imported_count} files",
        "has_source_pdfs": has_source_pdfs,
        "rerunnable": has_source_pdfs
    }


@app.get(
    "/api/prefilter/recommendations",
    tags=["Pre-Filter"],
    summary="Get pre-filter recommendations",
    responses={
        200: {"description": "Pre-filter recommendations based on dataset characteristics"},
        401: {"description": "Invalid or missing API key", "model": ErrorResponse}
    }
)
async def get_prefilter_recommendations(
    paper_count: int,
    review_type: str = "general",
    api_key: str = Header(None, alias="X-API-KEY", description="API authentication key")
):
    """
    Get recommended pre-filter configuration based on review characteristics.
    
    Returns optimal section selection for speed/cost balance.
    
    **Parameters:**
    - paper_count: Number of papers to analyze (determines dataset size category)
    - review_type: Type of review - "general", "methodology", or "survey"
    
    **Dataset Size Categories:**
    - Small: < 20 papers - Can afford comprehensive analysis
    - Medium: 20-100 papers - Need to balance coverage and efficiency
    - Large: > 100 papers - Must optimize for speed and cost
    
    **Review Types:**
    - general: Standard literature reviews (focus on intro/discussion)
    - methodology: Methods-focused reviews (focus on methods/results)
    - survey: Broad surveys (need comprehensive coverage)
    
    **Returns:**
    - recommended_sections: List of section names to analyze
    - section_string: Comma-separated section list (for --pre-filter flag)
    - paper_count: Number of papers (echoed from request)
    - review_type: Review type (echoed from request)
    - dataset_size: Calculated size category (small/medium/large)
    - rationale: Explanation of recommendation
    """
    verify_api_key(api_key)
    
    # Validate paper_count
    if paper_count <= 0:
        raise HTTPException(status_code=400, detail="paper_count must be a positive integer")
    
    recommendations = {
        "general": {
            "small": ["title", "abstract", "introduction", "discussion"],
            "medium": ["title", "abstract", "introduction"],
            "large": ["abstract"]
        },
        "methodology": {
            "small": ["abstract", "methods", "results"],
            "medium": ["abstract", "methods"],
            "large": ["abstract"]
        },
        "survey": {
            "small": ["title", "abstract", "introduction", "methods", "results", "discussion"],
            "medium": ["title", "abstract", "introduction", "discussion"],
            "large": ["title", "abstract", "introduction"]
        }
    }
    
    # Determine dataset size
    if paper_count < 20:
        size = "small"
    elif paper_count < 100:
        size = "medium"
    else:
        size = "large"
    
    sections = recommendations.get(review_type, recommendations["general"])[size]
    
    return {
        "recommended_sections": sections,
        "section_string": ",".join(sections),
        "paper_count": paper_count,
        "review_type": review_type,
        "dataset_size": size,
        "rationale": f"For {review_type} reviews with {size} datasets ({paper_count} papers), "
                    f"analyzing {len(sections)} sections balances coverage and efficiency."
    }


@app.post(
    "/api/checkpoints/scan",
    tags=["Resume"],
    summary="Scan directory for checkpoint files"
)
async def scan_checkpoints(
    request: CheckpointScanRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Scan output directory for pipeline checkpoint files.
    
    Returns list of found checkpoints with metadata.
    """
    verify_api_key(api_key)
    
    directory = Path(request.directory).expanduser().resolve()
    
    if not directory.exists():
        raise HTTPException(404, f"Directory not found: {directory}")
    
    # Find checkpoint files
    checkpoint_files = list(directory.glob("*checkpoint*.json"))
    
    # Remove duplicates
    checkpoint_files = list(set(checkpoint_files))
    
    checkpoints = []
    
    for checkpoint_file in checkpoint_files:
        try:
            with open(checkpoint_file) as f:
                checkpoint_data = json.load(f)
            
            # Extract metadata - handle different checkpoint structures
            last_stage = "Unknown"
            resume_stage = "Unknown"
            
            # Try to find last completed stage from stages dict
            stages = checkpoint_data.get("stages", {})
            if stages:
                completed_stages = [
                    stage for stage, data in stages.items()
                    if isinstance(data, dict) and data.get("status") == "completed"
                ]
                last_stage = completed_stages[-1] if completed_stages else "Unknown"
                
                # Find next stage to resume
                not_started = [
                    stage for stage, data in stages.items()
                    if isinstance(data, dict) and data.get("status") in ["not_started", "failed"]
                ]
                if not_started:
                    resume_stage = not_started[0]
            
            checkpoints.append({
                "path": str(checkpoint_file),
                "filename": checkpoint_file.name,
                "modified": datetime.fromtimestamp(
                    checkpoint_file.stat().st_mtime
                ).isoformat(),
                "last_stage": last_stage,
                "resume_stage": resume_stage,
                "papers_processed": checkpoint_data.get("papers_processed", 0),
                "valid": True
            })
            
        except Exception as e:
            logger.warning(f"Failed to parse checkpoint {checkpoint_file}: {e}")
            checkpoints.append({
                "path": str(checkpoint_file),
                "filename": checkpoint_file.name,
                "modified": datetime.fromtimestamp(
                    checkpoint_file.stat().st_mtime
                ).isoformat(),
                "valid": False,
                "error": str(e)
            })
    
    # Sort by modification time (newest first)
    checkpoints.sort(key=lambda c: c["modified"], reverse=True)
    
    return {
        "checkpoints": checkpoints,
        "count": len(checkpoints),
        "directory": str(directory)
    }


@app.post(
    "/api/jobs/{job_id}/resume",
    tags=["Resume"],
    summary="Resume failed job automatically"
)
async def resume_job(
    job_id: str,
    request: ResumeJobRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Resume a failed job from its last checkpoint.
    
    Automatically finds and uses the most recent checkpoint.
    """
    verify_api_key(api_key)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    
    job_data = load_job(job_id)
    if not job_data:
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Find output directory
    output_dir = job_dir / "outputs" / "gap_analysis_output"
    if not output_dir.exists():
        # Try to find it from config
        config = job_data.get("config", {})
        if config.get("output_dir_path"):
            output_dir = Path(config["output_dir_path"])
    
    # Scan for checkpoints
    scan_result = await scan_checkpoints(
        CheckpointScanRequest(directory=str(output_dir)),
        api_key
    )
    
    if scan_result["count"] == 0:
        raise HTTPException(
            404,
            "No checkpoint files found. Cannot auto-resume."
        )
    
    # Use most recent valid checkpoint
    checkpoint = next(
        (c for c in scan_result["checkpoints"] if c.get("valid", False)),
        None
    )
    
    if not checkpoint:
        raise HTTPException(
            400,
            "No valid checkpoint files found. Cannot auto-resume."
        )
    
    # Update job config with resume from checkpoint
    if not job_data.get("config"):
        job_data["config"] = {}
    
    job_data["config"]["resume_from_checkpoint"] = checkpoint["path"]
    job_data["status"] = "draft"  # Reset to draft so it can be started
    save_job(job_id, job_data)
    
    # Start the job
    return await start_job(job_id, api_key)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
