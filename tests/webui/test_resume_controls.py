"""
Unit tests for Resume Controls feature

Tests the FastAPI endpoints for:
- Scanning checkpoints in output directory
- Resuming jobs from checkpoints
- Validating checkpoint files
- Resume from stage configuration
"""

import io
import json
import tempfile
from pathlib import Path
from datetime import datetime
import pytest


@pytest.fixture
def test_job_id(test_client, api_key, sample_pdf):
    """Create a test job and return its ID"""
    headers = {"X-API-KEY": api_key}
    files = {"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")}
    response = test_client.post("/api/upload", files=files, headers=headers)
    return response.json()["job_id"]


def test_scan_checkpoints_success(test_client, api_key, tmp_path):
    """Test scanning directory for checkpoint files"""
    # Create test checkpoint
    checkpoint_data = {
        "pipeline_version": "1.3.0",
        "run_id": "test-run",
        "status": "in_progress",
        "stages": {
            "journal_reviewer": {
                "status": "completed",
                "started_at": "2024-01-01T00:00:00",
                "completed_at": "2024-01-01T00:10:00"
            },
            "judge": {
                "status": "completed",
                "started_at": "2024-01-01T00:10:00",
                "completed_at": "2024-01-01T00:20:00"
            },
            "sync": {
                "status": "not_started"
            }
        },
        "papers_processed": 10
    }
    
    checkpoint_file = tmp_path / "pipeline_checkpoint.json"
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint_data, f)
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        "/api/checkpoints/scan",
        json={"directory": str(tmp_path)},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert data["directory"] == str(tmp_path)
    
    # Check first checkpoint details
    checkpoint = next((c for c in data["checkpoints"] if c["valid"]), None)
    assert checkpoint is not None
    assert checkpoint["last_stage"] == "judge"
    assert checkpoint["papers_processed"] == 10


def test_scan_checkpoints_no_directory(test_client, api_key):
    """Test scanning non-existent directory"""
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        "/api/checkpoints/scan",
        json={"directory": "/nonexistent/path"},
        headers=headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_scan_checkpoints_empty_directory(test_client, api_key, tmp_path):
    """Test scanning directory with no checkpoints"""
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        "/api/checkpoints/scan",
        json={"directory": str(tmp_path)},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["checkpoints"] == []


def test_scan_checkpoints_invalid_json(test_client, api_key, tmp_path):
    """Test scanning directory with invalid checkpoint file"""
    # Create invalid checkpoint
    checkpoint_file = tmp_path / "pipeline_checkpoint.json"
    with open(checkpoint_file, "w") as f:
        f.write("not valid json{")
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        "/api/checkpoints/scan",
        json={"directory": str(tmp_path)},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    
    # Check that invalid checkpoint is marked as invalid
    invalid_checkpoint = next((c for c in data["checkpoints"] if not c.get("valid", True)), None)
    assert invalid_checkpoint is not None
    assert "error" in invalid_checkpoint


def test_configure_job_with_resume_from_stage(test_client, api_key, test_job_id):
    """Test configuring job with resume from stage"""
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "auto",
        "resume_from_stage": "orchestrator"
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{test_job_id}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["resume_from_stage"] == "orchestrator"


def test_configure_job_with_invalid_stage(test_client, api_key, test_job_id):
    """Test that invalid stage name is accepted by configure but will fail at runtime"""
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "auto",
        "resume_from_stage": "invalid_stage"
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{test_job_id}/configure",
        json=config,
        headers=headers
    )
    
    # Configure accepts any string, validation happens at runtime
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["resume_from_stage"] == "invalid_stage"


def test_configure_job_with_resume_from_checkpoint(test_client, api_key, test_job_id, tmp_path):
    """Test configuring job with resume from checkpoint"""
    # Create a valid checkpoint file
    checkpoint_data = {
        "pipeline_version": "1.3.0",
        "run_id": "test-run",
        "status": "in_progress",
        "stages": {
            "journal_reviewer": {"status": "completed"}
        }
    }
    
    checkpoint_file = tmp_path / "test_checkpoint.json"
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint_data, f)
    
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "auto",
        "resume_from_checkpoint": str(checkpoint_file)
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{test_job_id}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["resume_from_checkpoint"] == str(checkpoint_file)


def test_resume_job_no_checkpoints(test_client, api_key, test_job_id):
    """Test auto-resume fails when no checkpoints exist"""
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{test_job_id}/resume",
        json={"auto_resume": True},
        headers=headers
    )
    
    # Should fail because no checkpoints exist in output directory
    assert response.status_code == 404
    detail_lower = response.json()["detail"].lower()
    assert "checkpoint" in detail_lower or "not found" in detail_lower


def test_resume_job_nonexistent_job(test_client, api_key):
    """Test resume fails for nonexistent job"""
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        "/api/jobs/nonexistent-job-id/resume",
        json={"auto_resume": True},
        headers=headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_scan_checkpoints_multiple_files(test_client, api_key, tmp_path):
    """Test scanning directory with multiple checkpoint files"""
    # Create multiple checkpoints
    for i in range(3):
        checkpoint_data = {
            "pipeline_version": "1.3.0",
            "run_id": f"test-run-{i}",
            "status": "in_progress",
            "stages": {
                "journal_reviewer": {"status": "completed"}
            },
            "papers_processed": i * 10
        }
        
        checkpoint_file = tmp_path / f"checkpoint_{i}.json"
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f)
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        "/api/checkpoints/scan",
        json={"directory": str(tmp_path)},
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    
    # Verify checkpoints are sorted by modification time (newest first)
    valid_checkpoints = [c for c in data["checkpoints"] if c["valid"]]
    assert len(valid_checkpoints) == 3
    
    # Check modification times are in descending order
    mod_times = [c["modified"] for c in valid_checkpoints]
    assert mod_times == sorted(mod_times, reverse=True)


def test_validate_checkpoint_file_valid(test_client, api_key, tmp_path):
    """Test checkpoint file validation with valid file"""
    checkpoint_data = {
        "pipeline_version": "1.3.0",
        "status": "in_progress",
        "stages": {
            "journal_reviewer": {"status": "completed"}
        }
    }
    
    checkpoint_file = tmp_path / "valid_checkpoint.json"
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint_data, f)
    
    # This tests the validate_checkpoint_file helper indirectly through configure
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "auto",
        "resume_from_checkpoint": str(checkpoint_file)
    }
    
    headers = {"X-API-KEY": api_key}
    # Create a job first
    job_response = test_client.post("/api/upload",
                                     files={"file": ("test.pdf", io.BytesIO(b"%PDF-test"), "application/pdf")},
                                     headers=headers)
    job_id = job_response.json()["job_id"]
    
    response = test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200


def test_scan_checkpoints_without_api_key(test_client, tmp_path):
    """Test scanning checkpoints fails without API key"""
    response = test_client.post(
        "/api/checkpoints/scan",
        json={"directory": str(tmp_path)}
    )
    
    assert response.status_code == 401


def test_resume_job_without_api_key(test_client):
    """Test resume job fails without API key"""
    response = test_client.post(
        "/api/jobs/test-job-id/resume",
        json={"auto_resume": True}
    )
    
    assert response.status_code == 401
