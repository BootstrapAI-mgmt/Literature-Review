"""
Integration tests for Web Dashboard

Tests the complete job lifecycle:
1. Upload PDF
2. Job appears in list
3. Job status updates
4. Logs are accessible
5. File download works
"""

import io
import json
import time
from pathlib import Path


def test_complete_job_lifecycle(test_client, api_key, sample_pdf, temp_workspace):
    """Test complete job workflow from upload to completion"""
    headers = {"X-API-KEY": api_key}
    
    # Step 1: Upload a PDF
    files = {"file": ("research_paper.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    upload_response = test_client.post("/api/upload", files=files, headers=headers)
    
    assert upload_response.status_code == 200
    job_id = upload_response.json()["job_id"]
    
    # Step 2: Verify job appears in list
    list_response = test_client.get("/api/jobs", headers=headers)
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    
    assert len(jobs) == 1
    assert jobs[0]["id"] == job_id
    assert jobs[0]["status"] == "queued"
    assert jobs[0]["filename"] == "research_paper.pdf"
    
    # Step 3: Simulate orchestrator updating job status
    status_file = temp_workspace / "status" / f"{job_id}.json"
    status_update = {
        "id": job_id,
        "status": "running",
        "started_at": "2024-01-01T00:00:05",
        "progress": {"stage": "journal_reviewer", "percent": 50}
    }
    with open(status_file, 'w') as f:
        json.dump(status_update, f)
    
    # Step 4: Get job details and verify status update
    detail_response = test_client.get(f"/api/jobs/{job_id}", headers=headers)
    assert detail_response.status_code == 200
    job_detail = detail_response.json()
    
    assert job_detail["status"] == "running"
    assert job_detail["progress"]["stage"] == "journal_reviewer"
    
    # Step 5: Add some logs
    log_file = temp_workspace / "logs" / f"{job_id}.log"
    log_file.write_text("Starting job...\nProcessing PDF...\nCompleted successfully\n")
    
    # Step 6: Get logs
    logs_response = test_client.get(f"/api/logs/{job_id}", headers=headers)
    assert logs_response.status_code == 200
    logs_data = logs_response.json()
    
    assert "Starting job" in logs_data["logs"]
    assert "Completed successfully" in logs_data["logs"]
    
    # Step 7: Update to completed
    status_update["status"] = "completed"
    status_update["completed_at"] = "2024-01-01T00:01:00"
    with open(status_file, 'w') as f:
        json.dump(status_update, f)
    
    detail_response = test_client.get(f"/api/jobs/{job_id}", headers=headers)
    assert detail_response.json()["status"] == "completed"
    
    # Step 8: Download the file
    download_response = test_client.get(f"/api/download/{job_id}", headers=headers)
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"


def test_failed_job_retry_workflow(test_client, api_key, sample_pdf, temp_workspace):
    """Test job failure and retry workflow"""
    headers = {"X-API-KEY": api_key}
    
    # Upload a PDF
    files = {"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    upload_response = test_client.post("/api/upload", files=files, headers=headers)
    job_id = upload_response.json()["job_id"]
    
    # Simulate job failure
    status_file = temp_workspace / "status" / f"{job_id}.json"
    status_update = {
        "id": job_id,
        "status": "failed",
        "started_at": "2024-01-01T00:00:05",
        "completed_at": "2024-01-01T00:00:30",
        "error": "Connection timeout"
    }
    with open(status_file, 'w') as f:
        json.dump(status_update, f)
    
    # Get job details to verify failure
    detail_response = test_client.get(f"/api/jobs/{job_id}", headers=headers)
    job_detail = detail_response.json()
    assert job_detail["status"] == "failed"
    assert job_detail["error"] == "Connection timeout"
    
    # Retry the job
    retry_response = test_client.post(
        f"/api/jobs/{job_id}/retry",
        json={"force": False},
        headers=headers
    )
    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == "queued"
    
    # Verify job is back to queued status
    detail_response = test_client.get(f"/api/jobs/{job_id}", headers=headers)
    job_detail = detail_response.json()
    assert job_detail["status"] == "queued"
    assert job_detail["error"] is None


def test_multiple_concurrent_jobs(test_client, api_key, sample_pdf):
    """Test handling multiple jobs simultaneously"""
    headers = {"X-API-KEY": api_key}
    
    # Upload multiple PDFs
    job_ids = []
    for i in range(5):
        files = {"file": (f"paper_{i}.pdf", io.BytesIO(sample_pdf), "application/pdf")}
        response = test_client.post("/api/upload", files=files, headers=headers)
        assert response.status_code == 200
        job_ids.append(response.json()["job_id"])
    
    # List all jobs
    list_response = test_client.get("/api/jobs", headers=headers)
    assert list_response.status_code == 200
    
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 5
    
    # Verify all jobs are present
    returned_ids = [j["id"] for j in jobs]
    for job_id in job_ids:
        assert job_id in returned_ids
    
    # Verify each job can be accessed individually
    for job_id in job_ids:
        detail_response = test_client.get(f"/api/jobs/{job_id}", headers=headers)
        assert detail_response.status_code == 200


def test_job_status_progression(test_client, api_key, sample_pdf, temp_workspace):
    """Test job status progression through all states"""
    headers = {"X-API-KEY": api_key}
    
    # Upload PDF
    files = {"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = test_client.post("/api/upload", files=files, headers=headers)
    job_id = response.json()["job_id"]
    
    # Check initial status
    response = test_client.get(f"/api/jobs/{job_id}", headers=headers)
    assert response.json()["status"] == "queued"
    
    # Transition to running
    status_file = temp_workspace / "status" / f"{job_id}.json"
    with open(status_file, 'w') as f:
        json.dump({"id": job_id, "status": "running", "started_at": "2024-01-01T00:00:05"}, f)
    
    response = test_client.get(f"/api/jobs/{job_id}", headers=headers)
    assert response.json()["status"] == "running"
    
    # Transition to completed
    with open(status_file, 'w') as f:
        json.dump({
            "id": job_id,
            "status": "completed",
            "started_at": "2024-01-01T00:00:05",
            "completed_at": "2024-01-01T00:01:00"
        }, f)
    
    response = test_client.get(f"/api/jobs/{job_id}", headers=headers)
    assert response.json()["status"] == "completed"


def test_status_file_updates_reflected(test_client, api_key, create_job, temp_workspace):
    """Test that status file updates are reflected in job details"""
    # Create initial job
    job = create_job("test-job-1", "queued")
    headers = {"X-API-KEY": api_key}
    
    # Create status file with updates
    status_file = temp_workspace / "status" / "test-job-1.json"
    status_data = {
        "id": "test-job-1",
        "status": "running",
        "started_at": "2024-01-01T00:00:10",
        "progress": {
            "current_stage": "judge",
            "stages_completed": 2,
            "total_stages": 5,
            "percent": 40
        }
    }
    with open(status_file, 'w') as f:
        json.dump(status_data, f)
    
    # Get job details
    response = test_client.get("/api/jobs/test-job-1", headers=headers)
    assert response.status_code == 200
    
    job_detail = response.json()
    assert job_detail["status"] == "running"
    assert job_detail["progress"]["current_stage"] == "judge"
    assert job_detail["progress"]["percent"] == 40
