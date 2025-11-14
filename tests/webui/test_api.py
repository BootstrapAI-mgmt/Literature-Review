"""
Unit tests for Web Dashboard API endpoints

Tests the FastAPI endpoints for:
- Health check
- File upload
- Job listing
- Job details
- Job retry
- Log retrieval
"""

import io
import json
from pathlib import Path


def test_health_check(test_client):
    """Test health check endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_upload_pdf_success(test_client, api_key, sample_pdf):
    """Test successful PDF upload"""
    files = {"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    headers = {"X-API-KEY": api_key}
    
    response = test_client.post("/api/upload", files=files, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["filename"] == "test.pdf"


def test_upload_without_api_key(test_client, sample_pdf):
    """Test upload fails without API key"""
    files = {"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    
    response = test_client.post("/api/upload", files=files)
    
    assert response.status_code == 401
    assert "Invalid or missing API key" in response.json()["detail"]


def test_upload_invalid_api_key(test_client, sample_pdf):
    """Test upload fails with invalid API key"""
    files = {"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    headers = {"X-API-KEY": "invalid-key"}
    
    response = test_client.post("/api/upload", files=files, headers=headers)
    
    assert response.status_code == 401


def test_upload_non_pdf_file(test_client, api_key):
    """Test upload fails for non-PDF files"""
    files = {"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")}
    headers = {"X-API-KEY": api_key}
    
    response = test_client.post("/api/upload", files=files, headers=headers)
    
    assert response.status_code == 400
    assert "Only PDF files are allowed" in response.json()["detail"]


def test_list_jobs_empty(test_client, api_key):
    """Test listing jobs when there are none"""
    headers = {"X-API-KEY": api_key}
    
    response = test_client.get("/api/jobs", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["jobs"] == []
    assert data["count"] == 0


def test_list_jobs_with_jobs(test_client, api_key, create_job):
    """Test listing jobs when jobs exist"""
    # Create test jobs
    job1 = create_job("test-job-1", "completed")
    job2 = create_job("test-job-2", "running")
    job3 = create_job("test-job-3", "queued")
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] == 3
    assert len(data["jobs"]) == 3
    
    # Jobs should be sorted by created_at (newest first)
    job_ids = [j["id"] for j in data["jobs"]]
    assert "test-job-1" in job_ids
    assert "test-job-2" in job_ids
    assert "test-job-3" in job_ids


def test_get_job_detail_success(test_client, api_key, create_job):
    """Test getting job details for existing job"""
    job = create_job("test-job-1", "completed")
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs/test-job-1", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == "test-job-1"
    assert data["status"] == "completed"
    assert data["filename"] == "test.pdf"


def test_get_job_detail_not_found(test_client, api_key):
    """Test getting details for non-existent job"""
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs/nonexistent", headers=headers)
    
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


def test_retry_job_success(test_client, api_key, create_job):
    """Test retrying a failed job"""
    job = create_job("test-job-1", "failed", error="Some error")
    
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    body = {"force": False}
    
    response = test_client.post("/api/jobs/test-job-1/retry", json=body, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == "test-job-1"
    assert data["status"] == "queued"
    assert "Retry requested" in data["message"]


def test_retry_job_not_found(test_client, api_key):
    """Test retrying non-existent job"""
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    body = {"force": False}
    
    response = test_client.post("/api/jobs/nonexistent/retry", json=body, headers=headers)
    
    assert response.status_code == 404


def test_get_logs_no_logs(test_client, api_key, create_job):
    """Test getting logs when no log file exists"""
    job = create_job("test-job-1", "queued")
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/logs/test-job-1", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == "test-job-1"
    assert data["logs"] == ""
    assert "No logs available" in data["message"]


def test_get_logs_with_logs(test_client, api_key, create_job, temp_workspace):
    """Test getting logs when log file exists"""
    job = create_job("test-job-1", "running")
    
    # Create log file
    log_file = temp_workspace / "logs" / "test-job-1.log"
    log_content = "Line 1\nLine 2\nLine 3\n"
    log_file.write_text(log_content)
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/logs/test-job-1", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == "test-job-1"
    assert data["logs"] == log_content
    assert data["line_count"] == 3


def test_get_logs_tail_limit(test_client, api_key, create_job, temp_workspace):
    """Test log tailing with limit"""
    job = create_job("test-job-1", "running")
    
    # Create log file with many lines
    log_file = temp_workspace / "logs" / "test-job-1.log"
    log_lines = [f"Line {i}\n" for i in range(1, 201)]
    log_file.write_text(''.join(log_lines))
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/logs/test-job-1?tail=50", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["line_count"] == 50
    assert "Line 151" in data["logs"]  # Should start from line 151 (200-50+1)


def test_download_file_success(test_client, api_key, create_job, temp_workspace, sample_pdf):
    """Test downloading uploaded PDF"""
    job = create_job("test-job-1", "completed")
    
    # Create the actual PDF file
    pdf_file = temp_workspace / "uploads" / "test-job-1.pdf"
    pdf_file.write_bytes(sample_pdf)
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/download/test-job-1", headers=headers)
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_download_file_not_found(test_client, api_key):
    """Test downloading non-existent file"""
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/download/nonexistent", headers=headers)
    
    assert response.status_code == 404


def test_root_endpoint(test_client):
    """Test root endpoint returns HTML"""
    response = test_client.get("/")
    
    assert response.status_code == 200
    # Should contain HTML content
    assert "html" in response.text.lower()
