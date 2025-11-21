"""
Integration tests for Results Visualization

Tests cover:
- Results listing API endpoint
- Individual file retrieval
- ZIP download functionality
- File categorization
- Security (path traversal prevention)
"""

import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory for tests."""
    temp = tempfile.mkdtemp()
    workspace = Path(temp) / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "jobs").mkdir()
    
    yield workspace
    
    import shutil
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def completed_job(temp_workspace):
    """Create a completed job with sample output files."""
    job_id = "test-job-001"
    job_dir = temp_workspace / "jobs" / job_id
    job_dir.mkdir()
    
    # Create job metadata
    job_data = {
        "id": job_id,
        "status": "completed",
        "filename": "test.pdf",
        "created_at": "2025-01-01T00:00:00",
        "completed_at": "2025-01-01T01:00:00"
    }
    
    job_file = temp_workspace / "jobs" / f"{job_id}.json"
    with open(job_file, 'w') as f:
        json.dump(job_data, f)
    
    # Create output directory with sample files
    output_dir = job_dir / "outputs" / "gap_analysis_output"
    output_dir.mkdir(parents=True)
    
    # Create sample output files
    sample_files = {
        "gap_analysis_report.json": {"test": "data", "pillar_results": {}},
        "executive_summary.md": "# Executive Summary\n\nTest summary",
        "waterfall_Pillar 1.html": "<html><body>Waterfall Chart</body></html>",
        "_OVERALL_Research_Gap_Radar.html": "<html><body>Radar Chart</body></html>",
        "sufficiency_matrix.json": {"requirements": []},
    }
    
    for filename, content in sample_files.items():
        file_path = output_dir / filename
        if filename.endswith('.json'):
            with open(file_path, 'w') as f:
                json.dump(content, f)
        else:
            with open(file_path, 'w') as f:
                f.write(content)
    
    return {
        "job_id": job_id,
        "workspace": temp_workspace,
        "output_dir": output_dir,
        "job_data": job_data
    }


@pytest.fixture
def test_client(temp_workspace, monkeypatch):
    """Create a test client with mocked workspace directories."""
    # Remove app module and related modules if already imported to ensure clean state
    import sys
    modules_to_remove = [m for m in list(sys.modules.keys()) if m.startswith('webdashboard.')]
    for mod in modules_to_remove:
        del sys.modules[mod]
    
    # Import and patch the app module
    from webdashboard import app as app_module
    
    # Patch all directory paths including BASE_DIR
    app_module.WORKSPACE_DIR = temp_workspace
    app_module.JOBS_DIR = temp_workspace / "jobs"
    app_module.UPLOADS_DIR = temp_workspace / "uploads"
    app_module.STATUS_DIR = temp_workspace / "status"
    app_module.LOGS_DIR = temp_workspace / "logs"
    app_module.BASE_DIR = temp_workspace.parent
    
    # TEMPORARY: Enable exception raising to diagnose CI failures
    # Use raise_server_exceptions=True to see actual errors in CI
    return TestClient(app_module.app, raise_server_exceptions=True)


@pytest.mark.integration
class TestResultsVisualization:
    """Integration tests for Results Visualization API."""
    
    def test_results_listing(self, test_client, completed_job):
        """Test results listing endpoint returns all output files."""
        job_id = completed_job["job_id"]
        
        response = test_client.get(
            f"/api/jobs/{job_id}/results",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == job_id
        assert data["output_count"] == 5
        assert len(data["outputs"]) == 5
        
        # Verify file metadata
        for output in data["outputs"]:
            assert "filename" in output
            assert "path" in output
            assert "size" in output
            assert "category" in output
            assert "mime_type" in output
    
    def test_results_listing_job_not_found(self, test_client):
        """Test results listing returns 404 for non-existent job."""
        response = test_client.get(
            "/api/jobs/nonexistent-job/results",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 404
    
    def test_results_listing_job_not_completed(self, test_client, temp_workspace):
        """Test results listing returns 400 for incomplete job."""
        job_id = "incomplete-job"
        job_data = {
            "id": job_id,
            "status": "running",
            "filename": "test.pdf"
        }
        
        job_file = temp_workspace / "jobs" / f"{job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(job_data, f)
        
        response = test_client.get(
            f"/api/jobs/{job_id}/results",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 400
    
    def test_file_categorization(self, test_client, completed_job):
        """Test that files are correctly categorized."""
        job_id = completed_job["job_id"]
        
        response = test_client.get(
            f"/api/jobs/{job_id}/results",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        data = response.json()
        outputs = data["outputs"]
        
        # Find specific files and verify their categories
        categories = {f["filename"]: f["category"] for f in outputs}
        
        assert categories["gap_analysis_report.json"] == "data"
        assert categories["executive_summary.md"] == "reports"
        assert categories["waterfall_Pillar 1.html"] == "pillar_waterfalls"
        assert categories["_OVERALL_Research_Gap_Radar.html"] == "visualizations"
    
    def test_file_retrieval(self, test_client, completed_job):
        """Test retrieving individual result file."""
        job_id = completed_job["job_id"]
        
        # Get file list first
        results = test_client.get(
            f"/api/jobs/{job_id}/results",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        ).json()
        
        # Find a JSON file
        json_file = next(f for f in results["outputs"] if f["filename"].endswith(".json"))
        
        # Retrieve the file
        response = test_client.get(
            f"/api/jobs/{job_id}/results/{json_file['path']}",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
    
    def test_file_retrieval_not_found(self, test_client, completed_job):
        """Test retrieving non-existent file returns 404."""
        job_id = completed_job["job_id"]
        
        response = test_client.get(
            f"/api/jobs/{job_id}/results/nonexistent.json",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 404
    
    def test_path_traversal_prevention(self, test_client, completed_job):
        """Test that path traversal attacks are prevented."""
        job_id = completed_job["job_id"]
        
        # Attempt path traversal
        response = test_client.get(
            f"/api/jobs/{job_id}/results/../../other_job/secret.txt",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        # Should return 403 (Access Denied) or 404
        assert response.status_code in [403, 404]
    
    def test_zip_download(self, test_client, completed_job):
        """Test ZIP download of all results."""
        job_id = completed_job["job_id"]
        
        response = test_client.get(
            f"/api/jobs/{job_id}/results/download/all",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        
        # Verify ZIP is valid and contains files
        zip_data = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_data) as zf:
            file_list = zf.namelist()
            assert len(file_list) == 5
            
            # Verify specific files are in the ZIP
            assert "gap_analysis_report.json" in file_list
            assert "executive_summary.md" in file_list
    
    def test_zip_download_job_not_completed(self, test_client, temp_workspace):
        """Test ZIP download returns 400 for incomplete job."""
        job_id = "incomplete-job"
        job_data = {
            "id": job_id,
            "status": "running",
            "filename": "test.pdf"
        }
        
        job_file = temp_workspace / "jobs" / f"{job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(job_data, f)
        
        response = test_client.get(
            f"/api/jobs/{job_id}/results/download/all",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 400
    
    def test_results_no_outputs(self, test_client, temp_workspace):
        """Test results endpoint when job has no output files."""
        job_id = "no-outputs-job"
        job_data = {
            "id": job_id,
            "status": "completed",
            "filename": "test.pdf"
        }
        
        # Create job metadata
        job_file = temp_workspace / "jobs" / f"{job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(job_data, f)
        
        # Don't create output directory
        
        response = test_client.get(
            f"/api/jobs/{job_id}/results",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["output_count"] == 0
        assert data["outputs"] == []
    
    def test_api_key_authentication(self, test_client, completed_job):
        """Test that API key authentication works."""
        job_id = completed_job["job_id"]
        
        # Request without API key
        response = test_client.get(f"/api/jobs/{job_id}/results")
        assert response.status_code == 401
        
        # Request with wrong API key
        response = test_client.get(
            f"/api/jobs/{job_id}/results",
            headers={"X-API-KEY": "wrong-key"}
        )
        assert response.status_code == 401
        
        # Request with correct API key
        response = test_client.get(
            f"/api/jobs/{job_id}/results",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        assert response.status_code == 200


@pytest.mark.integration
def test_categorize_output_file():
    """Test the categorize_output_file helper function."""
    from webdashboard.app import categorize_output_file
    
    # Test pillar waterfalls
    assert categorize_output_file("waterfall_Pillar 1.html") == "pillar_waterfalls"
    assert categorize_output_file("waterfall_Test.html") == "pillar_waterfalls"
    
    # Test visualizations
    assert categorize_output_file("_OVERALL_Radar.html") == "visualizations"
    assert categorize_output_file("_Research_Trends.html") == "visualizations"
    
    # Test data files
    assert categorize_output_file("gap_analysis_report.json") == "data"
    assert categorize_output_file("data.json") == "data"
    
    # Test reports
    assert categorize_output_file("executive_summary.md") == "reports"
    assert categorize_output_file("README.md") == "reports"
    
    # Test HTML visualizations (not starting with waterfall_ or _)
    assert categorize_output_file("chart.html") == "visualizations"
    
    # Test other
    assert categorize_output_file("data.csv") == "other"
    assert categorize_output_file("image.png") == "other"
