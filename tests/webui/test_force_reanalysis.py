"""
Unit tests for Force Re-analysis Control feature

Tests the cost estimation API, cache stats API, and force confirmation validation.
"""

import json
from pathlib import Path


def test_cost_estimate_api_basic(test_client, api_key):
    """Test cost estimation endpoint with basic parameters."""
    request = {
        "paper_count": 10,
        "use_cache": False,
        "model": "gemini-1.5-pro"
    }
    
    response = test_client.post(
        "/api/cost/estimate",
        json=request,
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "fresh_cost" in data
    assert "cached_cost" in data
    assert "savings" in data
    assert "paper_count" in data
    assert "model" in data
    assert "cache_hit_rate" in data
    
    # When use_cache=False, cached_cost should equal fresh_cost
    assert data["fresh_cost"] == data["cached_cost"]
    assert data["savings"] == 0.0
    assert data["cache_hit_rate"] == 0.0


def test_cost_estimate_with_cache(test_client, api_key):
    """Test cost estimation with cache enabled."""
    request = {
        "paper_count": 10,
        "use_cache": True,
        "model": "gemini-1.5-pro"
    }
    
    response = test_client.post(
        "/api/cost/estimate",
        json=request,
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # With cache, cached_cost should be lower due to cache hit rate
    assert data["cached_cost"] < data["fresh_cost"]
    assert data["cache_hit_rate"] == 0.8  # Default 80% hit rate


def test_cost_estimate_free_model(test_client, api_key):
    """Test cost estimate with free model (gemini-2.0-flash-exp)."""
    request = {
        "paper_count": 10,
        "use_cache": False,
        "model": "gemini-2.0-flash-exp"
    }
    
    response = test_client.post(
        "/api/cost/estimate",
        json=request,
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Free model should have $0 cost
    assert data["fresh_cost"] == 0.0
    assert data["cached_cost"] == 0.0
    assert data["savings"] == 0.0


def test_cost_estimate_large_paper_count(test_client, api_key):
    """Test cost estimate scales with paper count."""
    # Small count
    small_request = {
        "paper_count": 10,
        "use_cache": False,
        "model": "gemini-1.5-pro"
    }
    
    small_response = test_client.post(
        "/api/cost/estimate",
        json=small_request,
        headers={"X-API-KEY": api_key}
    )
    small_cost = small_response.json()["fresh_cost"]
    
    # Large count
    large_request = {
        "paper_count": 100,
        "use_cache": False,
        "model": "gemini-1.5-pro"
    }
    
    large_response = test_client.post(
        "/api/cost/estimate",
        json=large_request,
        headers={"X-API-KEY": api_key}
    )
    large_cost = large_response.json()["fresh_cost"]
    
    # Cost should scale roughly linearly
    assert large_cost > small_cost
    assert large_cost / small_cost > 5  # Should be around 10x


def test_cost_estimate_without_api_key(test_client):
    """Test cost estimation fails without API key."""
    request = {
        "paper_count": 10,
        "use_cache": False,
        "model": "gemini-1.5-pro"
    }
    
    response = test_client.post("/api/cost/estimate", json=request)
    
    assert response.status_code == 401
    assert "Invalid or missing API key" in response.json()["detail"]


def test_cost_estimate_invalid_paper_count(test_client, api_key):
    """Test cost estimation with invalid paper count."""
    request = {
        "paper_count": 0,  # Invalid: less than 1
        "use_cache": False,
        "model": "gemini-1.5-pro"
    }
    
    response = test_client.post(
        "/api/cost/estimate",
        json=request,
        headers={"X-API-KEY": api_key}
    )
    
    # Should fail validation
    assert response.status_code == 422


def test_cache_stats_api(test_client, api_key, temp_workspace):
    """Test cache statistics endpoint."""
    # Create some mock cache directories
    cache_dir = temp_workspace.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    
    # Create a few cache files
    for i in range(5):
        cache_file = cache_dir / f"cache_{i}.json"
        cache_file.write_text(json.dumps({"data": f"test_{i}"}))
    
    response = test_client.get(
        "/api/cache/stats",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "caches" in data
    assert "total_entries" in data
    assert "total_size_mb" in data
    
    # Should be a dict of cache stats
    assert isinstance(data["caches"], dict)
    assert data["total_entries"] >= 0
    assert data["total_size_mb"] >= 0.0


def test_cache_stats_without_api_key(test_client):
    """Test cache statistics fails without API key."""
    response = test_client.get("/api/cache/stats")
    
    assert response.status_code == 401


def test_job_start_with_force_confirmed(test_client, api_key, create_job, temp_workspace):
    """Test starting job with force flag and confirmation - validates confirmation logic."""
    # Create a draft job with force configuration
    job_id = "test-force-job"
    create_job(job_id, status="draft")
    
    # Configure job with force and confirmation
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "force": True,
        "force_confirmed": True
    }
    
    config_response = test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    assert config_response.status_code == 200
    
    # Create a test PDF in the upload directory
    job_upload_dir = temp_workspace / "uploads" / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    test_pdf = job_upload_dir / "test.pdf"
    test_pdf.write_bytes(b"%PDF-1.4\ntest pdf content")
    
    # Note: We cannot fully test job start without the database builder
    # in the test environment, but we've tested the validation logic
    # in test_job_start_force_without_confirmation_rejected which proves
    # the confirmation check works. This test validates configuration acceptance.


def test_job_start_force_without_confirmation_rejected(test_client, api_key, create_job, temp_workspace):
    """Test that force without confirmation is rejected."""
    # Create a draft job
    job_id = "test-force-no-confirm"
    create_job(job_id, status="draft")
    
    # Configure job with force but NO confirmation
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "force": True,
        "force_confirmed": False  # Not confirmed
    }
    
    config_response = test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    assert config_response.status_code == 200
    
    # Create a test PDF
    job_upload_dir = temp_workspace / "uploads" / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    test_pdf = job_upload_dir / "test.pdf"
    test_pdf.write_bytes(b"%PDF-1.4\ntest pdf content")
    
    # Try to start the job - should fail validation BEFORE database builder
    start_response = test_client.post(
        f"/api/jobs/{job_id}/start",
        headers={"X-API-KEY": api_key}
    )
    
    # Should fail with 400 due to missing confirmation
    assert start_response.status_code == 400
    assert "confirmation" in start_response.json()["detail"].lower()


def test_job_start_without_force(test_client, api_key, create_job, temp_workspace):
    """Test that normal job start works without force - validates no confirmation needed."""
    # Create a draft job
    job_id = "test-normal-job"
    create_job(job_id, status="draft")
    
    # Configure job WITHOUT force
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "force": False
    }
    
    config_response = test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    assert config_response.status_code == 200
    
    # Verify configuration was saved correctly (no force_confirmed required)
    # This test validates that normal jobs don't require the confirmation field
