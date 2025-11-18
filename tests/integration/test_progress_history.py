"""
Integration tests for progress history endpoints.

Tests:
- Progress history endpoint for completed jobs
- CSV export endpoint
- Error handling for non-completed jobs
- Error handling for jobs without progress data
"""

import pytest
import json
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from datetime import datetime, timedelta


@pytest.fixture
def test_client():
    """Create test client for dashboard app."""
    from webdashboard.app import app
    return TestClient(app)


@pytest.fixture
def mock_completed_job(tmp_path, monkeypatch):
    """Create mock completed job with progress data."""
    job_id = "test-job-progress-123"
    
    # Mock workspace directories
    workspace_dir = tmp_path / "workspace"
    jobs_dir = workspace_dir / "jobs"
    status_dir = workspace_dir / "status"
    
    jobs_dir.mkdir(parents=True, exist_ok=True)
    status_dir.mkdir(parents=True, exist_ok=True)
    
    # Patch the BASE_DIR to use our temp directory
    monkeypatch.setattr("webdashboard.app.JOBS_DIR", jobs_dir)
    monkeypatch.setattr("webdashboard.app.STATUS_DIR", status_dir)
    
    # Create job data
    start_time = datetime.utcnow()
    job_data = {
        "id": job_id,
        "status": "completed",
        "filename": "test.pdf",
        "created_at": (start_time - timedelta(minutes=30)).isoformat(),
        "started_at": start_time.isoformat(),
        "completed_at": (start_time + timedelta(minutes=15)).isoformat(),
        "error": None
    }
    
    with open(jobs_dir / f"{job_id}.json", 'w') as f:
        json.dump(job_data, f)
    
    # Create progress events
    progress_events = [
        {
            "timestamp": start_time.isoformat(),
            "stage": "initialization",
            "phase": "starting",
            "message": "Starting initialization",
            "percentage": 0,
            "metadata": {}
        },
        {
            "timestamp": (start_time + timedelta(minutes=2)).isoformat(),
            "stage": "initialization",
            "phase": "complete",
            "message": "Initialization complete",
            "percentage": 10,
            "metadata": {}
        },
        {
            "timestamp": (start_time + timedelta(minutes=2)).isoformat(),
            "stage": "judge",
            "phase": "starting",
            "message": "Starting judge validation",
            "percentage": 10,
            "metadata": {}
        },
        {
            "timestamp": (start_time + timedelta(minutes=5)).isoformat(),
            "stage": "judge",
            "phase": "complete",
            "message": "Judge validation complete",
            "percentage": 30,
            "metadata": {}
        },
        {
            "timestamp": (start_time + timedelta(minutes=5)).isoformat(),
            "stage": "deep_review",
            "phase": "starting",
            "message": "Starting deep review",
            "percentage": 30,
            "metadata": {}
        },
        {
            "timestamp": (start_time + timedelta(minutes=10)).isoformat(),
            "stage": "deep_review",
            "phase": "complete",
            "message": "Deep review complete",
            "percentage": 60,
            "metadata": {}
        },
        {
            "timestamp": (start_time + timedelta(minutes=10)).isoformat(),
            "stage": "gap_analysis",
            "phase": "starting",
            "message": "Starting gap analysis",
            "percentage": 60,
            "metadata": {}
        },
        {
            "timestamp": (start_time + timedelta(minutes=13)).isoformat(),
            "stage": "gap_analysis",
            "phase": "complete",
            "message": "Gap analysis complete",
            "percentage": 90,
            "metadata": {}
        },
        {
            "timestamp": (start_time + timedelta(minutes=13)).isoformat(),
            "stage": "finalization",
            "phase": "starting",
            "message": "Starting finalization",
            "percentage": 90,
            "metadata": {}
        },
        {
            "timestamp": (start_time + timedelta(minutes=15)).isoformat(),
            "stage": "finalization",
            "phase": "complete",
            "message": "Finalization complete",
            "percentage": 100,
            "metadata": {}
        }
    ]
    
    # Write progress events to JSONL file
    progress_file = status_dir / f"{job_id}_progress.jsonl"
    with open(progress_file, 'w') as f:
        for event in progress_events:
            f.write(json.dumps(event) + '\n')
    
    return {
        'job_id': job_id,
        'job_data': job_data,
        'progress_events': progress_events
    }


@pytest.fixture
def mock_running_job(tmp_path, monkeypatch):
    """Create mock running job (not completed)."""
    job_id = "test-job-running-456"
    
    workspace_dir = tmp_path / "workspace"
    jobs_dir = workspace_dir / "jobs"
    
    jobs_dir.mkdir(parents=True, exist_ok=True)
    
    monkeypatch.setattr("webdashboard.app.JOBS_DIR", jobs_dir)
    
    job_data = {
        "id": job_id,
        "status": "running",
        "filename": "test.pdf",
        "created_at": datetime.utcnow().isoformat(),
        "started_at": datetime.utcnow().isoformat()
    }
    
    with open(jobs_dir / f"{job_id}.json", 'w') as f:
        json.dump(job_data, f)
    
    return {
        'job_id': job_id,
        'job_data': job_data
    }


def test_progress_history_endpoint(test_client, mock_completed_job):
    """Test progress history API endpoint for completed job."""
    job_id = mock_completed_job['job_id']
    
    response = test_client.get(
        f"/api/jobs/{job_id}/progress-history",
        headers={"X-API-KEY": "dev-key-change-in-production"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate response structure
    assert 'timeline' in data
    assert 'total_duration_seconds' in data
    assert 'total_duration_human' in data
    assert 'slowest_stage' in data
    assert 'job_id' in data
    
    # Validate timeline data
    assert len(data['timeline']) > 0
    
    # Check that all stages have required fields
    for stage in data['timeline']:
        assert 'stage' in stage
        assert 'start_time' in stage
        assert 'end_time' in stage
        assert 'duration_seconds' in stage
        assert 'duration_human' in stage
        assert 'percentage' in stage
        assert 'status' in stage
    
    # Verify percentages add up to ~100%
    total_percentage = sum(stage['percentage'] for stage in data['timeline'])
    assert 95 <= total_percentage <= 105  # Allow for rounding
    
    # Verify slowest stage is identified
    assert data['slowest_stage'] is not None
    stage_names = [s['stage'] for s in data['timeline']]
    assert data['slowest_stage'] in stage_names


def test_progress_history_running_job(test_client, mock_running_job):
    """Test error when requesting progress history for running job."""
    job_id = mock_running_job['job_id']
    
    response = test_client.get(
        f"/api/jobs/{job_id}/progress-history",
        headers={"X-API-KEY": "dev-key-change-in-production"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert 'detail' in data
    assert 'not completed' in data['detail'].lower()


def test_progress_history_nonexistent_job(test_client):
    """Test error when requesting progress history for nonexistent job."""
    response = test_client.get(
        "/api/jobs/nonexistent-job-999/progress-history",
        headers={"X-API-KEY": "dev-key-change-in-production"}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert 'detail' in data


def test_progress_history_no_data(test_client, tmp_path, monkeypatch):
    """Test error when job has no progress data."""
    job_id = "test-job-no-progress-789"
    
    workspace_dir = tmp_path / "workspace"
    jobs_dir = workspace_dir / "jobs"
    status_dir = workspace_dir / "status"
    
    jobs_dir.mkdir(parents=True, exist_ok=True)
    status_dir.mkdir(parents=True, exist_ok=True)
    
    monkeypatch.setattr("webdashboard.app.JOBS_DIR", jobs_dir)
    monkeypatch.setattr("webdashboard.app.STATUS_DIR", status_dir)
    
    # Create completed job without progress data
    job_data = {
        "id": job_id,
        "status": "completed",
        "filename": "test.pdf",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat()
    }
    
    with open(jobs_dir / f"{job_id}.json", 'w') as f:
        json.dump(job_data, f)
    
    # No progress file created
    
    response = test_client.get(
        f"/api/jobs/{job_id}/progress-history",
        headers={"X-API-KEY": "dev-key-change-in-production"}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert 'no progress data' in data['detail'].lower()


def test_csv_export(test_client, mock_completed_job):
    """Test CSV export functionality."""
    job_id = mock_completed_job['job_id']
    
    response = test_client.get(
        f"/api/jobs/{job_id}/progress-history.csv",
        headers={"X-API-KEY": "dev-key-change-in-production"}
    )
    
    assert response.status_code == 200
    assert response.headers['content-type'] == 'text/csv; charset=utf-8'
    assert 'attachment' in response.headers['content-disposition']
    assert job_id in response.headers['content-disposition']
    
    # Verify CSV content
    csv_content = response.text
    assert 'Stage,Start Time,End Time' in csv_content
    assert 'initialization' in csv_content
    assert 'TOTAL' in csv_content


def test_stage_duration_calculation(test_client, mock_completed_job):
    """Test that stage durations are calculated correctly."""
    job_id = mock_completed_job['job_id']
    
    response = test_client.get(
        f"/api/jobs/{job_id}/progress-history",
        headers={"X-API-KEY": "dev-key-change-in-production"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Find initialization stage (should be 2 minutes = 120 seconds)
    init_stage = next((s for s in data['timeline'] if s['stage'] == 'initialization'), None)
    assert init_stage is not None
    assert init_stage['duration_seconds'] == 120
    assert 'min' in init_stage['duration_human']
    
    # Find judge stage (should be 3 minutes = 180 seconds)
    judge_stage = next((s for s in data['timeline'] if s['stage'] == 'judge'), None)
    assert judge_stage is not None
    assert judge_stage['duration_seconds'] == 180


def test_authorization_required(test_client, mock_completed_job):
    """Test that API key is required."""
    job_id = mock_completed_job['job_id']
    
    # Request without API key
    response = test_client.get(f"/api/jobs/{job_id}/progress-history")
    
    assert response.status_code == 401


def test_duration_formatting():
    """Test the format_duration helper function."""
    from webdashboard.app import format_duration
    
    # Test seconds
    assert format_duration(30) == "30s"
    assert format_duration(59) == "59s"
    
    # Test minutes
    assert format_duration(60) == "1min 0s"
    assert format_duration(90) == "1min 30s"
    assert format_duration(3599) == "59min 59s"
    
    # Test hours
    assert format_duration(3600) == "1h 0min"
    assert format_duration(3660) == "1h 1min"
    assert format_duration(7200) == "2h 0min"
    assert format_duration(7380) == "2h 3min"
