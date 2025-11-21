"""
Bulk job operations API endpoints.

Provides endpoints for:
- Bulk delete multiple jobs
- Bulk export jobs as ZIP archive
- Compare multiple jobs side-by-side
"""

import io
import json
import shutil
import zipfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel


# Create router
router = APIRouter(prefix="/api/jobs", tags=["Bulk Operations"])


class BulkDeleteRequest(BaseModel):
    """Request to delete multiple jobs"""
    job_ids: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_ids": ["job-001", "job-002", "job-003"]
            }
        }


class BulkExportRequest(BaseModel):
    """Request to export multiple jobs"""
    job_ids: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_ids": ["job-001", "job-002"]
            }
        }


class CompareJobsRequest(BaseModel):
    """Request to compare multiple jobs"""
    job_ids: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_ids": ["job-001", "job-002"]
            }
        }


def get_jobs_dir() -> Path:
    """Get the jobs directory path from app module"""
    from webdashboard import app as app_module
    return app_module.JOBS_DIR


def verify_api_key(x_api_key: str = Header(None, alias="X-API-KEY")):
    """Verify API key from request header"""
    import os
    API_KEY = os.getenv("DASHBOARD_API_KEY", "dev-key-change-in-production")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key


def load_job(job_id: str) -> dict:
    """Load job data from file"""
    jobs_dir = get_jobs_dir()
    job_file = jobs_dir / f"{job_id}.json"
    
    if not job_file.exists():
        return None
    
    try:
        with open(job_file, 'r') as f:
            return json.load(f)
    except Exception:
        return None


@router.post(
    "/bulk-delete",
    summary="Delete multiple jobs",
    responses={
        200: {"description": "Jobs deleted successfully"},
        400: {"description": "No job IDs provided"},
        401: {"description": "Invalid or missing API key"}
    }
)
async def bulk_delete_jobs(
    request: BulkDeleteRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Delete multiple jobs at once.
    
    **Request Body:**
    - job_ids: Array of job IDs to delete
    
    **Returns:**
    - deleted: Array of successfully deleted job IDs
    - errors: Array of error messages for failed deletions
    - deleted_count: Number of jobs deleted
    - error_count: Number of errors
    
    **Security:**
    - Requires valid API key
    - Permanently deletes job data and all associated files
    """
    verify_api_key(api_key)
    
    if not request.job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")
    
    jobs_dir = get_jobs_dir()
    deleted = []
    errors = []
    
    for job_id in request.job_ids:
        try:
            # Check if job exists
            job_file = jobs_dir / f"{job_id}.json"
            if not job_file.exists():
                errors.append(f"{job_id}: Job not found")
                continue
            
            # Delete job metadata file
            job_file.unlink()
            
            # Delete job directory (outputs, uploads, etc.)
            job_dir = jobs_dir / job_id
            if job_dir.exists():
                shutil.rmtree(job_dir)
            
            # Delete status files
            from webdashboard import app as app_module
            status_file = app_module.STATUS_DIR / f"{job_id}.json"
            if status_file.exists():
                status_file.unlink()
            
            progress_file = app_module.STATUS_DIR / f"{job_id}_progress.jsonl"
            if progress_file.exists():
                progress_file.unlink()
            
            # Delete log file
            log_file = app_module.LOGS_DIR / f"{job_id}.log"
            if log_file.exists():
                log_file.unlink()
            
            # Delete upload directory
            upload_dir = app_module.UPLOADS_DIR / job_id
            if upload_dir.exists():
                shutil.rmtree(upload_dir)
            
            deleted.append(job_id)
            
        except Exception as e:
            errors.append(f"{job_id}: {str(e)}")
    
    return {
        "deleted": deleted,
        "errors": errors,
        "deleted_count": len(deleted),
        "error_count": len(errors)
    }


@router.post(
    "/bulk-export",
    summary="Export multiple jobs as ZIP archive",
    responses={
        200: {"description": "ZIP archive download"},
        400: {"description": "No job IDs provided"},
        401: {"description": "Invalid or missing API key"}
    }
)
async def bulk_export_jobs(
    request: BulkExportRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Export multiple jobs as a ZIP archive.
    
    **Request Body:**
    - job_ids: Array of job IDs to export
    
    **ZIP Contents:**
    For each job:
    - Job metadata (JSON)
    - All output files
    - Status and logs
    - Uploaded PDFs
    
    **Returns:**
    application/zip file with all job data
    
    **Security:**
    - Requires valid API key
    """
    verify_api_key(api_key)
    
    if not request.job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")
    
    jobs_dir = get_jobs_dir()
    from webdashboard import app as app_module
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for job_id in request.job_ids:
            # Add job metadata
            job_file = jobs_dir / f"{job_id}.json"
            if job_file.exists():
                zipf.write(job_file, arcname=f"{job_id}/{job_id}.json")
            
            # Add job directory (outputs)
            job_dir = jobs_dir / job_id
            if job_dir.exists():
                for file_path in job_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(jobs_dir)
                        zipf.write(file_path, arcname=str(arcname))
            
            # Add status files
            status_file = app_module.STATUS_DIR / f"{job_id}.json"
            if status_file.exists():
                zipf.write(status_file, arcname=f"{job_id}/status.json")
            
            progress_file = app_module.STATUS_DIR / f"{job_id}_progress.jsonl"
            if progress_file.exists():
                zipf.write(progress_file, arcname=f"{job_id}/progress.jsonl")
            
            # Add log file
            log_file = app_module.LOGS_DIR / f"{job_id}.log"
            if log_file.exists():
                zipf.write(log_file, arcname=f"{job_id}/job.log")
            
            # Add uploaded files
            upload_dir = app_module.UPLOADS_DIR / job_id
            if upload_dir.exists():
                for file_path in upload_dir.rglob('*'):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(app_module.UPLOADS_DIR)
                        zipf.write(file_path, arcname=f"uploads/{rel_path}")
    
    zip_buffer.seek(0)
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=jobs_export.zip"
        }
    )


@router.post(
    "/compare",
    summary="Compare multiple jobs side-by-side",
    responses={
        200: {"description": "Job comparison data"},
        400: {"description": "Invalid request (need at least 2 jobs)"},
        401: {"description": "Invalid or missing API key"}
    }
)
async def compare_jobs(
    request: CompareJobsRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Compare multiple jobs side-by-side.
    
    **Request Body:**
    - job_ids: Array of 2-5 job IDs to compare
    
    **Returns:**
    - jobs: Array of job summaries with metrics
    - metrics: Aggregate comparison metrics
    
    **Metrics for each job:**
    - job_id: Job identifier
    - name: Job name or filename
    - created_at: Creation timestamp
    - papers_analyzed: Number of papers
    - overall_coverage: Completeness percentage
    - status: Job status
    
    **Aggregate metrics:**
    - avg_coverage: Average coverage across all jobs
    - total_papers: Total unique papers across jobs
    - coverage_range: Min and max coverage
    
    **Security:**
    - Requires valid API key
    """
    verify_api_key(api_key)
    
    if len(request.job_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 jobs to compare"
        )
    
    if len(request.job_ids) > 5:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare more than 5 jobs at once"
        )
    
    jobs_dir = get_jobs_dir()
    comparison = []
    
    for job_id in request.job_ids:
        job_data = load_job(job_id)
        
        if not job_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Extract metrics
        name = job_data.get('filename', job_id)
        created_at = job_data.get('created_at', '')
        status = job_data.get('status', 'unknown')
        
        # Get paper count
        papers_analyzed = 0
        if 'files' in job_data:
            papers_analyzed = len(job_data.get('files', []))
        elif 'file_count' in job_data:
            papers_analyzed = job_data.get('file_count', 0)
        
        # Get coverage/completeness
        overall_coverage = 0.0
        summary = job_data.get('summary', {})
        if summary and 'completeness' in summary:
            overall_coverage = summary.get('completeness', 0.0)
        
        comparison.append({
            'job_id': job_id,
            'name': name,
            'created_at': created_at,
            'papers_analyzed': papers_analyzed,
            'overall_coverage': overall_coverage,
            'status': status
        })
    
    # Calculate aggregate metrics
    coverage_values = [j['overall_coverage'] for j in comparison if j['overall_coverage'] > 0]
    avg_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
    
    total_papers = sum(j['papers_analyzed'] for j in comparison)
    
    coverage_range = {
        'min': min(coverage_values) if coverage_values else 0.0,
        'max': max(coverage_values) if coverage_values else 0.0
    }
    
    return {
        'jobs': comparison,
        'metrics': {
            'avg_coverage': round(avg_coverage, 1),
            'total_papers': total_papers,
            'coverage_range': coverage_range
        }
    }
