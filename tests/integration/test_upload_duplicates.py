"""
Integration tests for upload duplicate detection
"""

import io
import json
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for testing"""
    temp_dir = Path(tempfile.mkdtemp())
    workspace = temp_dir / "workspace"
    workspace.mkdir()
    
    # Create subdirectories
    (workspace / "uploads").mkdir()
    (workspace / "jobs").mkdir()
    (workspace / "status").mkdir()
    (workspace / "logs").mkdir()
    
    yield workspace
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_review_log(temp_workspace):
    """Create a temporary review_log.json with existing papers"""
    review_log_path = temp_workspace.parent / "review_log.json"
    
    # Create sample existing papers
    existing_papers = [
        {
            "title": "Existing Paper 1",
            "hash": "abc123",
            "id": "existing1"
        },
        {
            "title": "Machine Learning Survey",
            "hash": "def456",
            "id": "existing2"
        }
    ]
    
    with open(review_log_path, 'w') as f:
        json.dump(existing_papers, f)
    
    yield review_log_path
    
    # Cleanup
    if review_log_path.exists():
        review_log_path.unlink()


@pytest.fixture
def test_client(temp_workspace, temp_review_log, monkeypatch):
    """Create a test client with temporary workspace"""
    # Monkeypatch paths
    monkeypatch.setattr("webdashboard.app.BASE_DIR", temp_workspace.parent)
    monkeypatch.setattr("webdashboard.app.WORKSPACE_DIR", temp_workspace)
    monkeypatch.setattr("webdashboard.app.UPLOADS_DIR", temp_workspace / "uploads")
    monkeypatch.setattr("webdashboard.app.JOBS_DIR", temp_workspace / "jobs")
    monkeypatch.setattr("webdashboard.app.STATUS_DIR", temp_workspace / "status")
    monkeypatch.setattr("webdashboard.app.LOGS_DIR", temp_workspace / "logs")
    
    from webdashboard.app import app
    
    return TestClient(app)


@pytest.fixture
def api_key():
    """Return test API key"""
    return "dev-key-change-in-production"


@pytest.fixture
def sample_pdf():
    """Create a minimal PDF file for testing"""
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
178
%%EOF
"""
    return pdf_content


class TestUploadWithDuplicates:
    """Tests for upload endpoint with duplicate detection"""
    
    def test_upload_no_duplicates(self, test_client, api_key, sample_pdf):
        """Test upload with no duplicates"""
        files = [
            ("files", ("new_paper.pdf", io.BytesIO(sample_pdf), "application/pdf"))
        ]
        
        response = test_client.post(
            "/api/upload/batch",
            files=files,
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"
        assert data["file_count"] == 1
        assert "duplicates" not in data
    
    def test_upload_with_title_duplicate(self, test_client, api_key, sample_pdf):
        """Test upload detects duplicate by title"""
        # Upload file with same title as existing paper
        files = [
            ("files", ("Machine Learning Survey.pdf", io.BytesIO(sample_pdf), "application/pdf"))
        ]
        
        response = test_client.post(
            "/api/upload/batch",
            files=files,
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "duplicates_found"
        assert len(data["duplicates"]) == 1
        assert len(data["new"]) == 0
        assert "job_id" in data
    
    def test_upload_mixed_duplicates_and_new(self, test_client, api_key, sample_pdf):
        """Test upload with both duplicates and new papers"""
        files = [
            ("files", ("Existing Paper 1.pdf", io.BytesIO(sample_pdf), "application/pdf")),
            ("files", ("New Paper.pdf", io.BytesIO(sample_pdf), "application/pdf")),
            ("files", ("Machine Learning Survey.pdf", io.BytesIO(sample_pdf), "application/pdf"))
        ]
        
        response = test_client.post(
            "/api/upload/batch",
            files=files,
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "duplicates_found"
        assert len(data["duplicates"]) == 2
        assert len(data["new"]) == 1
        assert data["message"] == "2 of 3 papers already exist"


class TestUploadConfirm:
    """Tests for upload confirmation after duplicate detection"""
    
    def test_skip_duplicates_action(self, test_client, api_key, sample_pdf):
        """Test skip duplicates action"""
        # First upload to trigger duplicate detection
        files = [
            ("files", ("Existing Paper 1.pdf", io.BytesIO(sample_pdf), "application/pdf")),
            ("files", ("New Paper.pdf", io.BytesIO(sample_pdf), "application/pdf"))
        ]
        
        upload_response = test_client.post(
            "/api/upload/batch",
            files=files,
            headers={"X-API-KEY": api_key}
        )
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["status"] == "duplicates_found"
        job_id = upload_data["job_id"]
        
        # Confirm with skip duplicates action
        confirm_response = test_client.post(
            "/api/upload/confirm",
            json={"action": "skip_duplicates", "job_id": job_id},
            headers={"X-API-KEY": api_key}
        )
        
        assert confirm_response.status_code == 200
        confirm_data = confirm_response.json()
        assert confirm_data["status"] == "success"
        assert confirm_data["uploaded"] == 1  # Only new paper
        assert confirm_data["skipped"] == 1  # One duplicate skipped
    
    def test_overwrite_all_action(self, test_client, api_key, sample_pdf):
        """Test overwrite all action"""
        # First upload to trigger duplicate detection
        files = [
            ("files", ("Existing Paper 1.pdf", io.BytesIO(sample_pdf), "application/pdf")),
            ("files", ("New Paper.pdf", io.BytesIO(sample_pdf), "application/pdf"))
        ]
        
        upload_response = test_client.post(
            "/api/upload/batch",
            files=files,
            headers={"X-API-KEY": api_key}
        )
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        job_id = upload_data["job_id"]
        
        # Confirm with overwrite all action
        confirm_response = test_client.post(
            "/api/upload/confirm",
            json={"action": "overwrite_all", "job_id": job_id},
            headers={"X-API-KEY": api_key}
        )
        
        assert confirm_response.status_code == 200
        confirm_data = confirm_response.json()
        assert confirm_data["status"] == "success"
        assert confirm_data["uploaded"] == 2  # All papers uploaded
    
    def test_invalid_action(self, test_client, api_key, sample_pdf):
        """Test that invalid action returns error"""
        # Create a job first
        files = [
            ("files", ("test.pdf", io.BytesIO(sample_pdf), "application/pdf"))
        ]
        
        upload_response = test_client.post(
            "/api/upload/batch",
            files=files,
            headers={"X-API-KEY": api_key}
        )
        
        job_id = upload_response.json()["job_id"]
        
        # Try invalid action
        confirm_response = test_client.post(
            "/api/upload/confirm",
            json={"action": "invalid_action", "job_id": job_id},
            headers={"X-API-KEY": api_key}
        )
        
        assert confirm_response.status_code == 400
        assert "Invalid action" in confirm_response.json()["detail"]
    
    def test_nonexistent_job(self, test_client, api_key):
        """Test confirmation with non-existent job ID"""
        confirm_response = test_client.post(
            "/api/upload/confirm",
            json={"action": "skip_duplicates", "job_id": "nonexistent"},
            headers={"X-API-KEY": api_key}
        )
        
        assert confirm_response.status_code == 404
        assert "Job not found" in confirm_response.json()["detail"]
