"""
Unit tests for Dry-Run Mode feature (PARITY-W3-3)

Tests the dry-run API endpoint that allows users to preview analysis
plans, cost estimates, and execution stages without performing actual analysis.
"""

import json
from pathlib import Path


def test_dry_run_basic(test_client, api_key, create_job, temp_workspace):
    """Test basic dry-run request with configured job."""
    # Create a draft job
    job_id = "test-dry-run-basic"
    create_job(job_id, status="draft")
    
    # Create some test files
    job_upload_dir = temp_workspace / "uploads" / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    for i in range(3):
        test_pdf = job_upload_dir / f"paper_{i}.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest pdf content")
    
    # Configure the job first
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "dry_run": True
    }
    
    config_response = test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    assert config_response.status_code == 200
    
    # Run dry-run
    response = test_client.post(
        f"/api/jobs/{job_id}/dry-run",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert data["dry_run"] is True
    assert data["job_id"] == job_id
    assert data["paper_count"] == 3
    assert data["estimated_api_calls"] > 0
    assert data["estimated_cost"] >= 0
    assert "cost_range" in data
    assert "min" in data["cost_range"]
    assert "max" in data["cost_range"]
    assert data["estimated_duration_minutes"] > 0
    assert "duration_range" in data
    assert "execution_plan" in data
    assert "configuration" in data
    assert "files" in data
    assert "warnings" in data


def test_dry_run_execution_plan(test_client, api_key, create_job, temp_workspace):
    """Test that execution plan shows all stages."""
    # Create a draft job
    job_id = "test-dry-run-plan"
    create_job(job_id, status="draft")
    
    # Create some test files
    job_upload_dir = temp_workspace / "uploads" / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    for i in range(5):
        test_pdf = job_upload_dir / f"paper_{i}.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest pdf content")
    
    # Configure without resume
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE"
    }
    
    test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    
    response = test_client.post(
        f"/api/jobs/{job_id}/dry-run",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    plan = data["execution_plan"]
    assert len(plan) == 4  # 4 stages: gap_analysis, relevance_scoring, deep_review, visualization
    
    # All stages should run when no resume is specified
    assert all(s["status"] == "run" for s in plan)
    
    # Verify stage names
    stage_names = [s["stage_name"] for s in plan]
    assert "gap_analysis" in stage_names
    assert "relevance_scoring" in stage_names
    assert "deep_review" in stage_names
    assert "visualization" in stage_names


def test_dry_run_with_resume(test_client, api_key, create_job, temp_workspace):
    """Test dry-run with resume from stage - shows skipped stages."""
    # Create a draft job
    job_id = "test-dry-run-resume"
    create_job(job_id, status="draft")
    
    # Create some test files
    job_upload_dir = temp_workspace / "uploads" / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    for i in range(3):
        test_pdf = job_upload_dir / f"paper_{i}.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest pdf content")
    
    # Configure with resume from deep_review
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "resume_from_stage": "deep_review"
    }
    
    test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    
    response = test_client.post(
        f"/api/jobs/{job_id}/dry-run",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    plan = data["execution_plan"]
    
    # First two stages should be skipped
    gap_analysis = next(s for s in plan if s["stage_name"] == "gap_analysis")
    relevance = next(s for s in plan if s["stage_name"] == "relevance_scoring")
    deep_review = next(s for s in plan if s["stage_name"] == "deep_review")
    visualization = next(s for s in plan if s["stage_name"] == "visualization")
    
    assert gap_analysis["status"] == "skip"
    assert relevance["status"] == "skip"
    assert deep_review["status"] == "run"
    assert visualization["status"] == "run"


def test_dry_run_warnings_large_dataset(test_client, api_key, create_job, temp_workspace):
    """Test that warnings are generated for large datasets."""
    # Create a draft job
    job_id = "test-dry-run-warnings"
    create_job(job_id, status="draft")
    
    # Create many test files (> 100)
    job_upload_dir = temp_workspace / "uploads" / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    for i in range(150):
        test_pdf = job_upload_dir / f"paper_{i}.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest pdf content")
    
    # Configure the job
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE"
    }
    
    test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    
    response = test_client.post(
        f"/api/jobs/{job_id}/dry-run",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have warning about large dataset
    assert len(data["warnings"]) > 0
    assert any("Large dataset" in w for w in data["warnings"])


def test_dry_run_no_files_warning(test_client, api_key, create_job, temp_workspace):
    """Test that warning is shown when no files are available."""
    # Create a draft job without files
    job_id = "test-dry-run-no-files"
    create_job(job_id, status="draft")
    
    # Don't create any files
    
    # Configure the job
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE"
    }
    
    test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    
    response = test_client.post(
        f"/api/jobs/{job_id}/dry-run",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have warning about no files
    assert data["paper_count"] == 0
    assert any("No files found" in w for w in data["warnings"])


def test_dry_run_without_api_key(test_client):
    """Test dry-run fails without API key."""
    response = test_client.post("/api/jobs/test-job/dry-run")
    
    assert response.status_code == 401
    assert "Invalid or missing API key" in response.json()["detail"]


def test_dry_run_job_not_found(test_client, api_key):
    """Test dry-run returns 404 for non-existent job."""
    response = test_client.post(
        "/api/jobs/nonexistent-job-id/dry-run",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 404


def test_dry_run_configuration_summary(test_client, api_key, create_job, temp_workspace):
    """Test that configuration summary is accurate."""
    # Create a draft job
    job_id = "test-dry-run-config"
    create_job(job_id, status="draft")
    
    # Create test files
    job_upload_dir = temp_workspace / "uploads" / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    test_pdf = job_upload_dir / "paper.pdf"
    test_pdf.write_bytes(b"%PDF-1.4\ntest pdf content")
    
    # Configure with various options
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "DEEP_LOOP",
        "force": False,
        "clear_cache": False,
        "budget": 10.00,
        "relevance_threshold": 0.8,
        "experimental": True
    }
    
    test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    
    response = test_client.post(
        f"/api/jobs/{job_id}/dry-run",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify configuration summary reflects settings
    config_summary = data["configuration"]
    assert config_summary["mode"] == "DEEP_LOOP"
    assert config_summary["force_reanalysis"] is False
    assert config_summary["cache_enabled"] is True
    assert config_summary["budget"] == 10.00
    assert config_summary["relevance_threshold"] == 0.8
    assert config_summary["experimental"] is True


def test_dry_run_file_list(test_client, api_key, create_job, temp_workspace):
    """Test that file list includes correct metadata."""
    # Create a draft job
    job_id = "test-dry-run-files"
    create_job(job_id, status="draft")
    
    # Create test files with different sizes
    job_upload_dir = temp_workspace / "uploads" / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    test_pdf1 = job_upload_dir / "paper1.pdf"
    test_pdf1.write_bytes(b"%PDF-1.4\n" + b"x" * 1000)
    
    test_pdf2 = job_upload_dir / "paper2.pdf"
    test_pdf2.write_bytes(b"%PDF-1.4\n" + b"y" * 2000)
    
    # Configure the job
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE"
    }
    
    test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    
    response = test_client.post(
        f"/api/jobs/{job_id}/dry-run",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify file list
    assert len(data["files"]) == 2
    
    for file_info in data["files"]:
        assert "filename" in file_info
        assert "type" in file_info
        assert "size_bytes" in file_info
        assert "cached" in file_info
        assert file_info["type"] == "PDF"


def test_dry_run_budget_warning(test_client, api_key, create_job, temp_workspace):
    """Test that budget warning is generated when estimates exceed budget."""
    # Create a draft job
    job_id = "test-dry-run-budget"
    create_job(job_id, status="draft")
    
    # Create many test files to generate high cost estimate
    job_upload_dir = temp_workspace / "uploads" / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    for i in range(50):
        test_pdf = job_upload_dir / f"paper_{i}.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest pdf content")
    
    # Configure with very low budget
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "budget": 0.01  # Very low budget to trigger warning
    }
    
    test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers={"X-API-KEY": api_key}
    )
    
    response = test_client.post(
        f"/api/jobs/{job_id}/dry-run",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have warning about budget
    assert any("exceeds budget" in w for w in data["warnings"])
