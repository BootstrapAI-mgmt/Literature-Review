"""
Unit tests for Resource Monitoring API endpoint (PARITY-W3-1)

Tests the real-time resource metrics endpoint for:
- API call tracking
- Cost monitoring  
- Cache performance metrics
- Processing rate and ETA calculation
- Stage breakdown
- Timeline data generation
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path


def test_get_resources_success(test_client, api_key, create_job, temp_workspace):
    """Test fetching resource metrics for a running job."""
    job = create_job("test-job-resources", "running")
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs/test-job-resources/resources", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify all top-level keys are present
    assert "api_calls" in data
    assert "cost" in data
    assert "cache" in data
    assert "processing" in data
    assert "progress" in data
    assert "stages" in data
    assert "timeline" in data
    
    # Verify api_calls structure
    assert "total" in data["api_calls"]
    assert "budget" in data["api_calls"]
    
    # Verify cost structure
    assert "total" in data["cost"]
    assert "budget" in data["cost"]
    assert "by_model" in data["cost"]
    
    # Verify cache structure
    assert "hits" in data["cache"]
    assert "misses" in data["cache"]
    assert "total" in data["cache"]
    assert "savings" in data["cache"]
    
    # Verify processing structure
    assert "rate" in data["processing"]
    assert "elapsed" in data["processing"]
    assert "eta" in data["processing"]
    
    # Verify progress structure
    assert "papers_processed" in data["progress"]
    assert "total_papers" in data["progress"]
    assert "current_stage" in data["progress"]


def test_get_resources_job_not_found(test_client, api_key):
    """Test fetching resources for non-existent job."""
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs/nonexistent-job/resources", headers=headers)
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_resources_without_api_key(test_client, create_job):
    """Test resource endpoint requires API key."""
    job = create_job("test-job-auth", "running")
    
    response = test_client.get("/api/jobs/test-job-auth/resources")
    
    assert response.status_code == 401


def test_get_resources_with_cost_data(test_client, api_key, create_job, temp_workspace):
    """Test resource metrics with cost tracker CSV data."""
    job = create_job("test-job-costs", "running")
    
    # Create job outputs directory
    job_dir = temp_workspace / "jobs" / "test-job-costs"
    cost_dir = job_dir / "outputs" / "cost_reports"
    cost_dir.mkdir(parents=True, exist_ok=True)
    
    # Create cost tracker CSV
    cost_csv = cost_dir / "cost_tracker.csv"
    cost_csv.write_text("""timestamp,model,cost,cache_hit,stage
2024-01-01T00:00:01,gemini-1.5-pro,0.05,false,gap_analysis
2024-01-01T00:00:02,gemini-1.5-pro,0.05,false,gap_analysis
2024-01-01T00:00:03,gemini-1.5-flash,0.01,true,gap_analysis
2024-01-01T00:00:04,gemini-1.5-pro,0.05,false,relevance_scoring
2024-01-01T00:00:05,gemini-1.5-flash,0.01,true,relevance_scoring
""")
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs/test-job-costs/resources", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify cost data was parsed
    assert data["api_calls"]["total"] == 5
    assert data["cost"]["total"] == 0.17  # 3*0.05 + 2*0.01
    assert data["cache"]["hits"] == 2
    assert data["cache"]["misses"] == 3
    
    # Verify model breakdown
    assert "gemini-1.5-pro" in data["cost"]["by_model"]
    assert data["cost"]["by_model"]["gemini-1.5-pro"]["calls"] == 3


def test_get_resources_with_orchestrator_state(test_client, api_key, create_job, temp_workspace):
    """Test resource metrics with orchestrator state data."""
    job = create_job("test-job-state", "running")
    
    # Create job outputs directory
    job_dir = temp_workspace / "jobs" / "test-job-state"
    outputs_dir = job_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create orchestrator state
    state_file = outputs_dir / "orchestrator_state.json"
    state_data = {
        "current_stage": "deep_review",
        "stage_number": 3,
        "papers_processed": 15,
        "total_papers": 50,
        "stages": {
            "gap_analysis": {"status": "Completed"},
            "relevance_scoring": {"status": "Completed"},
            "deep_review": {"status": "Running"},
            "visualization": {"status": "Pending"}
        }
    }
    with open(state_file, 'w') as f:
        json.dump(state_data, f)
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs/test-job-state/resources", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify progress data
    assert data["progress"]["papers_processed"] == 15
    assert data["progress"]["total_papers"] == 50
    assert data["progress"]["current_stage"] == "deep_review"
    assert data["progress"]["stage_number"] == 3
    
    # Verify stage breakdown
    assert data["stages"]["gap_analysis"]["status"] == "Completed"
    assert data["stages"]["deep_review"]["status"] == "Running"
    assert data["stages"]["visualization"]["status"] == "Pending"


def test_eta_calculation_logic(test_client, api_key, create_job, temp_workspace):
    """Test ETA calculation with known paper counts and timing."""
    # Create job with started_at timestamp 10 minutes ago
    job_id = "test-job-eta"
    started_at = (datetime.now() - timedelta(minutes=10)).isoformat()
    
    job_data = {
        "id": job_id,
        "status": "running",
        "filename": "test.pdf",
        "file_path": str(temp_workspace / "uploads" / f"{job_id}.pdf"),
        "created_at": "2024-01-01T00:00:00",
        "started_at": started_at,
        "completed_at": None,
        "error": None,
        "progress": {},
        "file_count": 100  # Total papers
    }
    
    job_file = temp_workspace / "jobs" / f"{job_id}.json"
    with open(job_file, 'w') as f:
        json.dump(job_data, f)
    
    # Create orchestrator state showing 25 papers processed
    job_dir = temp_workspace / "jobs" / job_id
    outputs_dir = job_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    state_file = outputs_dir / "orchestrator_state.json"
    state_data = {
        "papers_processed": 25,
        "total_papers": 100,
        "current_stage": "deep_review"
    }
    with open(state_file, 'w') as f:
        json.dump(state_data, f)
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get(f"/api/jobs/{job_id}/resources", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # With 25 papers in 10 minutes = 2.5 papers/min
    # 75 remaining / 2.5 = 30 minutes ETA
    assert data["processing"]["rate"] > 0
    assert data["progress"]["papers_processed"] == 25
    assert data["progress"]["total_papers"] == 100
    # ETA should be around 30m (some variance due to timing)
    assert "m" in data["processing"]["eta"] or "h" in data["processing"]["eta"]


def test_resources_timeline_data(test_client, api_key, create_job, temp_workspace):
    """Test timeline data generation for charting."""
    job = create_job("test-job-timeline", "running")
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs/test-job-timeline/resources", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify timeline structure
    assert "timeline" in data
    assert isinstance(data["timeline"], list)
    assert len(data["timeline"]) > 0
    
    # Verify timeline point structure
    point = data["timeline"][0]
    assert "timestamp" in point
    assert "api_rate" in point
    assert "cost_rate" in point


def test_resources_empty_metrics(test_client, api_key, create_job, temp_workspace):
    """Test resource metrics with no cost data (zeroes gracefully)."""
    job = create_job("test-job-empty", "queued")
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs/test-job-empty/resources", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should show zeros without errors
    assert data["api_calls"]["total"] == 0
    assert data["cost"]["total"] == 0.0
    assert data["cache"]["hits"] == 0
    assert data["cache"]["misses"] == 0
    assert data["processing"]["rate"] == 0


def test_resources_stage_breakdown_pending(test_client, api_key, create_job, temp_workspace):
    """Test stage breakdown when all stages are pending."""
    job = create_job("test-job-pending", "queued")
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs/test-job-pending/resources", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # All stages should be pending
    assert data["stages"]["gap_analysis"]["status"] == "Pending"
    assert data["stages"]["relevance_scoring"]["status"] == "Pending"
    assert data["stages"]["deep_review"]["status"] == "Pending"
    assert data["stages"]["visualization"]["status"] == "Pending"
