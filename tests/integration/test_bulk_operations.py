"""
Integration tests for bulk operations API endpoints.

Tests cover:
- Bulk delete multiple jobs
- Bulk export jobs as ZIP
- Bulk comparison of multiple jobs
- Error handling and validation
"""

import json
import tempfile
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory for tests"""
    temp = tempfile.mkdtemp()
    workspace = Path(temp) / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "jobs").mkdir()
    (workspace / "uploads").mkdir()
    (workspace / "status").mkdir()
    (workspace / "logs").mkdir()
    
    yield workspace
    
    import shutil
    shutil.rmtree(temp, ignore_errors=True)


def create_test_job(workspace, job_id, status="completed", filename="test.pdf"):
    """Create a test job with minimal data"""
    # Create job metadata
    job_data = {
        "id": job_id,
        "status": status,
        "filename": filename,
        "created_at": "2025-01-01T00:00:00",
        "files": [{"original_name": filename}],
        "summary": {
            "completeness": 75.0,
            "paper_count": 1
        }
    }
    
    job_file = workspace / "jobs" / f"{job_id}.json"
    with open(job_file, 'w') as f:
        json.dump(job_data, f)
    
    # Create job directory
    job_dir = workspace / "jobs" / job_id
    job_dir.mkdir(parents=True)
    
    # Create outputs directory
    output_dir = job_dir / "outputs"
    output_dir.mkdir()
    
    # Create a simple output file
    (output_dir / "test.txt").write_text("test output")
    
    return job_id


@pytest.fixture
def test_client(temp_workspace, monkeypatch):
    """Create a test client with mocked workspace directories"""
    # Set dummy GEMINI_API_KEY for tests
    monkeypatch.setenv("GEMINI_API_KEY", "test-dummy-key-for-integration-tests")
    
    # Remove app module if already imported to ensure clean state
    import sys
    modules_to_remove = [m for m in list(sys.modules.keys()) if m.startswith('webdashboard.')]
    for mod in modules_to_remove:
        del sys.modules[mod]
    
    # Create review_log.json in the parent directory
    review_log_path = temp_workspace.parent / "review_log.json"
    review_log_path.write_text("[]")
    
    # Import and patch the app module
    from webdashboard import app as app_module
    
    # Patch all directory paths
    app_module.WORKSPACE_DIR = temp_workspace
    app_module.JOBS_DIR = temp_workspace / "jobs"
    app_module.UPLOADS_DIR = temp_workspace / "uploads"
    app_module.STATUS_DIR = temp_workspace / "status"
    app_module.LOGS_DIR = temp_workspace / "logs"
    app_module.BASE_DIR = temp_workspace.parent
    
    return TestClient(app_module.app, raise_server_exceptions=True)


@pytest.mark.integration
class TestBulkOperations:
    """Integration tests for bulk operations API"""
    
    def test_bulk_delete_single_job(self, test_client, temp_workspace):
        """Test deleting a single job via bulk delete"""
        job_id = create_test_job(temp_workspace, "bulk-del-001")
        
        response = test_client.post(
            "/api/jobs/bulk-delete",
            json={"job_ids": [job_id]},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["deleted_count"] == 1
        assert data["error_count"] == 0
        assert job_id in data["deleted"]
        
        # Verify job file is deleted
        job_file = temp_workspace / "jobs" / f"{job_id}.json"
        assert not job_file.exists()
        
        # Verify job directory is deleted
        job_dir = temp_workspace / "jobs" / job_id
        assert not job_dir.exists()
    
    def test_bulk_delete_multiple_jobs(self, test_client, temp_workspace):
        """Test deleting multiple jobs at once"""
        job_ids = [
            create_test_job(temp_workspace, "bulk-del-002"),
            create_test_job(temp_workspace, "bulk-del-003"),
            create_test_job(temp_workspace, "bulk-del-004")
        ]
        
        response = test_client.post(
            "/api/jobs/bulk-delete",
            json={"job_ids": job_ids},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["deleted_count"] == 3
        assert data["error_count"] == 0
        assert set(data["deleted"]) == set(job_ids)
        
        # Verify all jobs are deleted
        for job_id in job_ids:
            job_file = temp_workspace / "jobs" / f"{job_id}.json"
            assert not job_file.exists()
    
    def test_bulk_delete_nonexistent_job(self, test_client, temp_workspace):
        """Test deleting a job that doesn't exist"""
        response = test_client.post(
            "/api/jobs/bulk-delete",
            json={"job_ids": ["nonexistent-job"]},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should report as error
        assert data["deleted_count"] == 0
        assert data["error_count"] == 1
        assert "nonexistent-job" in data["errors"][0]
    
    def test_bulk_delete_no_jobs(self, test_client, temp_workspace):
        """Test bulk delete with empty job list"""
        response = test_client.post(
            "/api/jobs/bulk-delete",
            json={"job_ids": []},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 400
        assert "No job IDs provided" in response.json()["detail"]
    
    def test_bulk_delete_authentication(self, test_client, temp_workspace):
        """Test that bulk delete requires authentication"""
        job_id = create_test_job(temp_workspace, "bulk-del-005")
        
        # No API key
        response = test_client.post(
            "/api/jobs/bulk-delete",
            json={"job_ids": [job_id]}
        )
        assert response.status_code == 401
        
        # Wrong API key
        response = test_client.post(
            "/api/jobs/bulk-delete",
            json={"job_ids": [job_id]},
            headers={"X-API-KEY": "wrong-key"}
        )
        assert response.status_code == 401
    
    def test_bulk_export_single_job(self, test_client, temp_workspace):
        """Test exporting a single job as ZIP"""
        job_id = create_test_job(temp_workspace, "bulk-exp-001")
        
        response = test_client.post(
            "/api/jobs/bulk-export",
            json={"job_ids": [job_id]},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        
        # Verify ZIP content
        import io
        zip_data = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_data, 'r') as zipf:
            files = zipf.namelist()
            assert f"{job_id}/{job_id}.json" in files
            assert any("test.txt" in f for f in files)
    
    def test_bulk_export_multiple_jobs(self, test_client, temp_workspace):
        """Test exporting multiple jobs as ZIP"""
        job_ids = [
            create_test_job(temp_workspace, "bulk-exp-002", filename="paper1.pdf"),
            create_test_job(temp_workspace, "bulk-exp-003", filename="paper2.pdf")
        ]
        
        response = test_client.post(
            "/api/jobs/bulk-export",
            json={"job_ids": job_ids},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        
        # Verify ZIP contains both jobs
        import io
        zip_data = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_data, 'r') as zipf:
            files = zipf.namelist()
            for job_id in job_ids:
                assert f"{job_id}/{job_id}.json" in files
    
    def test_bulk_export_no_jobs(self, test_client, temp_workspace):
        """Test bulk export with empty job list"""
        response = test_client.post(
            "/api/jobs/bulk-export",
            json={"job_ids": []},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 400
        assert "No job IDs provided" in response.json()["detail"]
    
    def test_bulk_export_authentication(self, test_client, temp_workspace):
        """Test that bulk export requires authentication"""
        job_id = create_test_job(temp_workspace, "bulk-exp-004")
        
        # No API key
        response = test_client.post(
            "/api/jobs/bulk-export",
            json={"job_ids": [job_id]}
        )
        assert response.status_code == 401
    
    def test_compare_two_jobs(self, test_client, temp_workspace):
        """Test comparing two jobs"""
        job_id_1 = create_test_job(temp_workspace, "bulk-cmp-001", filename="paper1.pdf")
        job_id_2 = create_test_job(temp_workspace, "bulk-cmp-002", filename="paper2.pdf")
        
        response = test_client.post(
            "/api/jobs/compare",
            json={"job_ids": [job_id_1, job_id_2]},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert "metrics" in data
        assert len(data["jobs"]) == 2
        
        # Verify job data structure
        for job in data["jobs"]:
            assert "job_id" in job
            assert "name" in job
            assert "papers_analyzed" in job
            assert "overall_coverage" in job
        
        # Verify metrics
        assert "avg_coverage" in data["metrics"]
        assert "total_papers" in data["metrics"]
        assert "coverage_range" in data["metrics"]
    
    def test_compare_multiple_jobs(self, test_client, temp_workspace):
        """Test comparing 3+ jobs"""
        job_ids = [
            create_test_job(temp_workspace, f"bulk-cmp-{i:03d}")
            for i in range(3, 6)
        ]
        
        response = test_client.post(
            "/api/jobs/compare",
            json={"job_ids": job_ids},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["jobs"]) == 3
        assert data["metrics"]["total_papers"] == 3
    
    def test_compare_too_few_jobs(self, test_client, temp_workspace):
        """Test comparison with only one job"""
        job_id = create_test_job(temp_workspace, "bulk-cmp-006")
        
        response = test_client.post(
            "/api/jobs/compare",
            json={"job_ids": [job_id]},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 400
        assert "at least 2 jobs" in response.json()["detail"].lower()
    
    def test_compare_too_many_jobs(self, test_client, temp_workspace):
        """Test comparison with more than 5 jobs"""
        job_ids = [
            create_test_job(temp_workspace, f"bulk-cmp-{i:03d}")
            for i in range(7, 14)
        ]
        
        response = test_client.post(
            "/api/jobs/compare",
            json={"job_ids": job_ids},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 400
        assert "cannot compare more than 5" in response.json()["detail"].lower()
    
    def test_compare_nonexistent_job(self, test_client, temp_workspace):
        """Test comparison with nonexistent job"""
        job_id = create_test_job(temp_workspace, "bulk-cmp-007")
        
        response = test_client.post(
            "/api/jobs/compare",
            json={"job_ids": [job_id, "nonexistent-job"]},
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_compare_authentication(self, test_client, temp_workspace):
        """Test that comparison requires authentication"""
        job_ids = [
            create_test_job(temp_workspace, "bulk-cmp-008"),
            create_test_job(temp_workspace, "bulk-cmp-009")
        ]
        
        # No API key
        response = test_client.post(
            "/api/jobs/compare",
            json={"job_ids": job_ids}
        )
        assert response.status_code == 401
