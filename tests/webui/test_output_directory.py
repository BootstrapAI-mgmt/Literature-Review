"""
Unit tests for Output Directory Configuration API endpoints

Tests the FastAPI endpoints for:
- Scanning output directories
- Configuring jobs with custom output directories
- Security validation (directory traversal prevention)
"""

import io
import json
from pathlib import Path


def test_scan_output_directories_empty(test_client, api_key):
    """Test scanning for output directories when none exist"""
    headers = {"X-API-KEY": api_key}
    
    response = test_client.get("/api/scan-output-directories", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "directories" in data
    assert "count" in data
    assert isinstance(data["directories"], list)
    assert data["count"] == 0


def test_scan_output_directories_with_existing(test_client, api_key, temp_workspace, monkeypatch):
    """Test scanning finds existing output directories"""
    # Monkeypatch BASE_DIR and WORKSPACE_DIR to use temp workspace
    monkeypatch.setattr("webdashboard.app.BASE_DIR", temp_workspace.parent)
    monkeypatch.setattr("webdashboard.app.WORKSPACE_DIR", temp_workspace)
    monkeypatch.setattr("webdashboard.app.JOBS_DIR", temp_workspace / "jobs")
    
    # Create a mock output directory with gap_analysis_report.json in temp_workspace
    output_dir = temp_workspace / "gap_analysis_output"
    output_dir.mkdir()
    (output_dir / "gap_analysis_report.json").write_text('{"test": "data"}')
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/scan-output-directories", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] >= 1
    assert len(data["directories"]) >= 1
    
    # Check directory structure
    found_dir = None
    for d in data["directories"]:
        if d["path"] == str(output_dir):
            found_dir = d
            break
    
    assert found_dir is not None
    assert found_dir["has_report"] is True
    assert found_dir["file_count"] >= 1


def test_scan_output_directories_requires_auth(test_client):
    """Test that scanning requires API key"""
    response = test_client.get("/api/scan-output-directories")
    assert response.status_code == 401


def test_configure_job_with_auto_output_dir(test_client, api_key, create_job):
    """Test configuring job with auto-generated output directory"""
    job = create_job("test-job-1", "draft")
    
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "convergence_threshold": 5.0,
        "output_dir_mode": "auto"
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{job['id']}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "output_dir" in data
    assert "gap_analysis_output" in data["output_dir"]
    assert data["config"]["output_dir_mode"] == "auto"


def test_configure_job_with_custom_output_dir(test_client, api_key, create_job, temp_workspace):
    """Test configuring job with custom output directory"""
    job = create_job("test-job-2", "draft")
    
    custom_path = temp_workspace / "my_custom_output"
    
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "convergence_threshold": 5.0,
        "output_dir_mode": "custom",
        "output_dir_path": str(custom_path),
        "overwrite_existing": True
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{job['id']}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "output_dir" in data
    assert str(custom_path) in data["output_dir"]
    assert data["config"]["output_dir_mode"] == "custom"
    assert data["config"]["overwrite_existing"] is True


def test_configure_job_custom_mode_requires_path(test_client, api_key, create_job):
    """Test that custom mode requires output_dir_path"""
    job = create_job("test-job-3", "draft")
    
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "custom"
        # Missing output_dir_path
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{job['id']}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 400
    assert "Custom path required" in response.json()["detail"]


def test_configure_job_with_existing_directory(test_client, api_key, create_job, temp_workspace):
    """Test configuring job with existing output directory"""
    job = create_job("test-job-4", "draft")
    
    # Create existing output directory
    existing_dir = temp_workspace / "existing_output"
    existing_dir.mkdir()
    (existing_dir / "gap_analysis_report.json").write_text('{"test": "data"}')
    
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "existing",
        "output_dir_path": str(existing_dir)
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{job['id']}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["config"]["output_dir_mode"] == "existing"
    # Should auto-enable overwrite for existing directories
    assert data["config"]["overwrite_existing"] is True


def test_configure_job_existing_mode_requires_existing_path(test_client, api_key, create_job, temp_workspace):
    """Test that existing mode requires path that exists"""
    job = create_job("test-job-5", "draft")
    
    non_existent_path = temp_workspace / "does_not_exist"
    
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "existing",
        "output_dir_path": str(non_existent_path)
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{job['id']}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_configure_job_prevents_system_directories(test_client, api_key, create_job):
    """Test security: prevent using system directories"""
    job = create_job("test-job-6", "draft")
    
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "custom",
        "output_dir_path": "/etc/malicious_output"
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{job['id']}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 400
    assert "system directories" in response.json()["detail"]


def test_configure_job_overwrite_protection(test_client, api_key, create_job, temp_workspace):
    """Test that overwrite protection works correctly"""
    job = create_job("test-job-7", "draft")
    
    # Create existing output directory with report
    existing_dir = temp_workspace / "protected_output"
    existing_dir.mkdir()
    (existing_dir / "gap_analysis_report.json").write_text('{"test": "data"}')
    
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "custom",
        "output_dir_path": str(existing_dir),
        "overwrite_existing": False  # Overwrite disabled
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{job['id']}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 409
    assert "existing analysis" in response.json()["detail"]


def test_configure_job_allows_overwrite_when_enabled(test_client, api_key, create_job, temp_workspace):
    """Test that overwrite works when explicitly enabled"""
    job = create_job("test-job-8", "draft")
    
    # Create existing output directory with report
    existing_dir = temp_workspace / "overwrite_output"
    existing_dir.mkdir()
    (existing_dir / "gap_analysis_report.json").write_text('{"test": "data"}')
    
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "custom",
        "output_dir_path": str(existing_dir),
        "overwrite_existing": True  # Overwrite enabled
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{job['id']}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["overwrite_existing"] is True


def test_configure_job_relative_paths_resolved(test_client, api_key, create_job, temp_workspace):
    """Test that relative paths are resolved correctly"""
    job = create_job("test-job-9", "draft")
    
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "output_dir_mode": "custom",
        "output_dir_path": "./relative_output",
        "overwrite_existing": True
    }
    
    headers = {"X-API-KEY": api_key}
    response = test_client.post(
        f"/api/jobs/{job['id']}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Output directory should be absolute path
    assert Path(data["output_dir"]).is_absolute()
    assert "relative_output" in data["output_dir"]
