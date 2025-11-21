"""
Integration tests for job comparison API endpoint

Tests cover:
- /api/compare-jobs endpoint with valid jobs
- Comparison with invalid/missing jobs
- Completeness delta calculations
- Papers added/removed differentials
- Gaps filled tracking
- API authentication
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
    """Create temporary workspace directory for tests"""
    temp = tempfile.mkdtemp()
    workspace = Path(temp) / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "jobs").mkdir()
    
    yield workspace
    
    import shutil
    shutil.rmtree(temp, ignore_errors=True)


def create_test_job(workspace, job_id, completeness_values, papers, created_at="2025-01-01T00:00:00"):
    """Create a test job with specified completeness and papers"""
    # Create job metadata
    job_data = {
        "id": job_id,
        "status": "completed",
        "files": [{"original_name": p} for p in papers],
        "created_at": created_at,
        "completed_at": "2025-01-01T01:00:00"
    }
    
    job_file = workspace / "jobs" / f"{job_id}.json"
    with open(job_file, 'w') as f:
        json.dump(job_data, f)
    
    # Create output directory and gap analysis report
    output_dir = workspace / "jobs" / job_id / "outputs" / "gap_analysis_output"
    output_dir.mkdir(parents=True)
    
    # Create gap analysis report
    report = {}
    for pillar_name, completeness in completeness_values.items():
        report[pillar_name] = {
            "completeness": completeness,
            "analysis": {
                "REQ-1: Test Requirement": {
                    "Sub-1.1: Test Sub-requirement": {
                        "completeness_percent": completeness,
                        "gap_analysis": f"Test gap for {pillar_name}",
                        "confidence_level": "high",
                        "contributing_papers": []
                    }
                }
            }
        }
    
    with open(output_dir / "gap_analysis_report.json", 'w') as f:
        json.dump(report, f)
    
    return job_id


@pytest.fixture
def test_client(temp_workspace, monkeypatch):
    """Create a test client with mocked workspace directories"""
    # Remove app module if already imported to ensure clean state
    import sys
    if 'webdashboard.app' in sys.modules:
        del sys.modules['webdashboard.app']
    
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
class TestComparisonAPI:
    """Integration tests for job comparison API"""
    
    def test_compare_jobs_basic(self, test_client, temp_workspace):
        """Test basic job comparison with completeness improvement"""
        # Create two jobs
        job1_id = create_test_job(
            temp_workspace,
            "job-001",
            {"Pillar 1: Test": 60.0},
            ["paper1.pdf", "paper2.pdf"],
            "2025-01-01T00:00:00"
        )
        
        job2_id = create_test_job(
            temp_workspace,
            "job-002",
            {"Pillar 1: Test": 75.0},
            ["paper1.pdf", "paper2.pdf", "paper3.pdf"],
            "2025-01-02T00:00:00"
        )
        
        response = test_client.get(
            f"/api/compare-jobs/{job1_id}/{job2_id}",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "job1" in data
        assert "job2" in data
        assert "delta" in data
        
        # Verify job1 data
        assert data["job1"]["id"] == job1_id
        assert data["job1"]["completeness"] == 60.0
        assert data["job1"]["paper_count"] == 2
        
        # Verify job2 data
        assert data["job2"]["id"] == job2_id
        assert data["job2"]["completeness"] == 75.0
        assert data["job2"]["paper_count"] == 3
        
        # Verify delta
        assert data["delta"]["completeness_change"] == 15.0
        assert data["delta"]["papers_added_count"] == 1
        assert "paper3.pdf" in data["delta"]["papers_added"]
        assert data["delta"]["papers_removed_count"] == 0
    
    def test_compare_jobs_with_regression(self, test_client, temp_workspace):
        """Test comparison when completeness decreases (regression)"""
        job1_id = create_test_job(
            temp_workspace,
            "job-003",
            {"Pillar 1: Test": 80.0},
            ["paper1.pdf", "paper2.pdf"],
            "2025-01-01T00:00:00"
        )
        
        job2_id = create_test_job(
            temp_workspace,
            "job-004",
            {"Pillar 1: Test": 70.0},
            ["paper1.pdf"],
            "2025-01-02T00:00:00"
        )
        
        response = test_client.get(
            f"/api/compare-jobs/{job1_id}/{job2_id}",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify regression is detected
        assert data["delta"]["completeness_change"] == -10.0
        assert data["delta"]["papers_removed_count"] == 1
        assert "paper2.pdf" in data["delta"]["papers_removed"]
    
    def test_compare_jobs_job1_not_found(self, test_client, temp_workspace):
        """Test comparison with non-existent first job"""
        job2_id = create_test_job(
            temp_workspace,
            "job-005",
            {"Pillar 1: Test": 75.0},
            ["paper1.pdf"],
            "2025-01-02T00:00:00"
        )
        
        response = test_client.get(
            f"/api/compare-jobs/nonexistent-job/{job2_id}",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_compare_jobs_job2_not_found(self, test_client, temp_workspace):
        """Test comparison with non-existent second job"""
        job1_id = create_test_job(
            temp_workspace,
            "job-006",
            {"Pillar 1: Test": 60.0},
            ["paper1.pdf"],
            "2025-01-01T00:00:00"
        )
        
        response = test_client.get(
            f"/api/compare-jobs/{job1_id}/nonexistent-job",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_compare_jobs_job1_not_completed(self, test_client, temp_workspace):
        """Test comparison when first job is not completed"""
        # Create incomplete job
        job1_data = {
            "id": "job-007",
            "status": "running",
            "files": [{"original_name": "paper1.pdf"}],
            "created_at": "2025-01-01T00:00:00"
        }
        
        job1_file = temp_workspace / "jobs" / "job-007.json"
        with open(job1_file, 'w') as f:
            json.dump(job1_data, f)
        
        # Create completed job
        job2_id = create_test_job(
            temp_workspace,
            "job-008",
            {"Pillar 1: Test": 75.0},
            ["paper1.pdf"],
            "2025-01-02T00:00:00"
        )
        
        response = test_client.get(
            f"/api/compare-jobs/job-007/{job2_id}",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()
    
    def test_compare_jobs_job2_not_completed(self, test_client, temp_workspace):
        """Test comparison when second job is not completed"""
        job1_id = create_test_job(
            temp_workspace,
            "job-009",
            {"Pillar 1: Test": 60.0},
            ["paper1.pdf"],
            "2025-01-01T00:00:00"
        )
        
        # Create incomplete job
        job2_data = {
            "id": "job-010",
            "status": "running",
            "files": [{"original_name": "paper1.pdf"}],
            "created_at": "2025-01-02T00:00:00"
        }
        
        job2_file = temp_workspace / "jobs" / "job-010.json"
        with open(job2_file, 'w') as f:
            json.dump(job2_data, f)
        
        response = test_client.get(
            f"/api/compare-jobs/{job1_id}/job-010",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()
    
    def test_compare_jobs_multiple_pillars(self, test_client, temp_workspace):
        """Test comparison with multiple pillars"""
        job1_id = create_test_job(
            temp_workspace,
            "job-011",
            {
                "Pillar 1: Test": 60.0,
                "Pillar 2: Test": 50.0
            },
            ["paper1.pdf"],
            "2025-01-01T00:00:00"
        )
        
        job2_id = create_test_job(
            temp_workspace,
            "job-012",
            {
                "Pillar 1: Test": 75.0,
                "Pillar 2: Test": 80.0
            },
            ["paper1.pdf", "paper2.pdf"],
            "2025-01-02T00:00:00"
        )
        
        response = test_client.get(
            f"/api/compare-jobs/{job1_id}/{job2_id}",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Average completeness: (60+50)/2 = 55 for job1, (75+80)/2 = 77.5 for job2
        assert data["job1"]["completeness"] == 55.0
        assert data["job2"]["completeness"] == 77.5
        assert data["delta"]["completeness_change"] == 22.5
    
    def test_compare_jobs_no_changes(self, test_client, temp_workspace):
        """Test comparison when nothing changed between jobs"""
        job1_id = create_test_job(
            temp_workspace,
            "job-013",
            {"Pillar 1: Test": 60.0},
            ["paper1.pdf", "paper2.pdf"],
            "2025-01-01T00:00:00"
        )
        
        job2_id = create_test_job(
            temp_workspace,
            "job-014",
            {"Pillar 1: Test": 60.0},
            ["paper1.pdf", "paper2.pdf"],
            "2025-01-02T00:00:00"
        )
        
        response = test_client.get(
            f"/api/compare-jobs/{job1_id}/{job2_id}",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["delta"]["completeness_change"] == 0.0
        assert data["delta"]["papers_added_count"] == 0
        assert data["delta"]["papers_removed_count"] == 0
    
    def test_compare_jobs_authentication(self, test_client, temp_workspace):
        """Test that API key authentication works for comparison endpoint"""
        job1_id = create_test_job(
            temp_workspace,
            "job-015",
            {"Pillar 1: Test": 60.0},
            ["paper1.pdf"],
            "2025-01-01T00:00:00"
        )
        
        job2_id = create_test_job(
            temp_workspace,
            "job-016",
            {"Pillar 1: Test": 75.0},
            ["paper1.pdf", "paper2.pdf"],
            "2025-01-02T00:00:00"
        )
        
        # Request without API key
        response = test_client.get(f"/api/compare-jobs/{job1_id}/{job2_id}")
        assert response.status_code == 401
        
        # Request with wrong API key
        response = test_client.get(
            f"/api/compare-jobs/{job1_id}/{job2_id}",
            headers={"X-API-KEY": "wrong-key"}
        )
        assert response.status_code == 401
        
        # Request with correct API key
        response = test_client.get(
            f"/api/compare-jobs/{job1_id}/{job2_id}",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        assert response.status_code == 200
