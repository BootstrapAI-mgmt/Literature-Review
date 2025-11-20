"""
Integration tests for Dashboard Input Pipeline

Tests cover:
- Batch file upload
- Job configuration
- Database building
- Complete upload → configure → start workflow
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
def test_client(temp_workspace, monkeypatch):
    """Create a test client with temporary workspace"""
    # Import app after monkeypatching paths
    monkeypatch.setattr("webdashboard.app.WORKSPACE_DIR", temp_workspace)
    monkeypatch.setattr("webdashboard.app.UPLOADS_DIR", temp_workspace / "uploads")
    monkeypatch.setattr("webdashboard.app.JOBS_DIR", temp_workspace / "jobs")
    monkeypatch.setattr("webdashboard.app.STATUS_DIR", temp_workspace / "status")
    monkeypatch.setattr("webdashboard.app.LOGS_DIR", temp_workspace / "logs")
    
    from webdashboard.app import app
    
    # Use raise_server_exceptions=False to allow async handling
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def api_key():
    """Return test API key"""
    return "dev-key-change-in-production"


@pytest.fixture
def sample_pdfs():
    """Create multiple minimal PDF files for testing"""
    # Minimal PDF content (same as in webui/conftest.py)
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
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF
"""
    return [pdf_content, pdf_content]  # Return two identical PDFs


@pytest.mark.integration
class TestBatchUpload:
    """Test batch file upload functionality"""
    
    def test_batch_upload_creates_draft_job(self, test_client, api_key, sample_pdfs):
        """Test that batch upload creates a draft job"""
        files = [
            ("files", ("paper1.pdf", io.BytesIO(sample_pdfs[0]), "application/pdf")),
            ("files", ("paper2.pdf", io.BytesIO(sample_pdfs[1]), "application/pdf"))
        ]
        headers = {"X-API-KEY": api_key}
        
        response = test_client.post("/api/upload/batch", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "draft"
        assert data["file_count"] == 2
        assert len(data["files"]) == 2
        assert "job_id" in data
        
        # Verify files were saved
        job_id = data["job_id"]
        for file_info in data["files"]:
            file_path = Path(file_info["path"])
            assert file_path.exists()
            assert file_path.stat().st_size > 0
    
    def test_batch_upload_single_file(self, test_client, api_key, sample_pdfs):
        """Test batch upload with single file"""
        files = [
            ("files", ("paper1.pdf", io.BytesIO(sample_pdfs[0]), "application/pdf"))
        ]
        headers = {"X-API-KEY": api_key}
        
        response = test_client.post("/api/upload/batch", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_count"] == 1
    
    def test_batch_upload_rejects_non_pdf(self, test_client, api_key, sample_pdfs):
        """Test batch upload rejects non-PDF files"""
        files = [
            ("files", ("paper1.pdf", io.BytesIO(sample_pdfs[0]), "application/pdf")),
            ("files", ("notpdf.txt", io.BytesIO(b"text file"), "text/plain"))
        ]
        headers = {"X-API-KEY": api_key}
        
        response = test_client.post("/api/upload/batch", files=files, headers=headers)
        
        assert response.status_code == 400
        assert "Only PDFs allowed" in response.json()["detail"]
    
    def test_batch_upload_without_api_key(self, test_client, sample_pdfs):
        """Test batch upload fails without API key"""
        files = [
            ("files", ("paper1.pdf", io.BytesIO(sample_pdfs[0]), "application/pdf"))
        ]
        
        response = test_client.post("/api/upload/batch", files=files)
        
        assert response.status_code == 401


@pytest.mark.integration
class TestJobConfiguration:
    """Test job configuration endpoint"""
    
    def test_configure_draft_job(self, test_client, api_key, sample_pdfs):
        """Test configuring a draft job"""
        # First create a draft job
        files = [
            ("files", ("paper1.pdf", io.BytesIO(sample_pdfs[0]), "application/pdf"))
        ]
        headers = {"X-API-KEY": api_key}
        upload_response = test_client.post("/api/upload/batch", files=files, headers=headers)
        job_id = upload_response.json()["job_id"]
        
        # Configure the job
        config = {
            "pillar_selections": ["Pillar_1", "Pillar_2"],
            "run_mode": "ONCE",
            "convergence_threshold": 5.0
        }
        
        response = test_client.post(
            f"/api/jobs/{job_id}/configure",
            json=config,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["pillar_selections"] == ["Pillar_1", "Pillar_2"]
        assert data["config"]["run_mode"] == "ONCE"
        assert data["config"]["convergence_threshold"] == 5.0
    
    def test_configure_nonexistent_job(self, test_client, api_key):
        """Test configuring a nonexistent job fails"""
        config = {
            "pillar_selections": ["ALL"],
            "run_mode": "ONCE",
            "convergence_threshold": 5.0
        }
        headers = {"X-API-KEY": api_key}
        
        response = test_client.post(
            "/api/jobs/nonexistent-job-id/configure",
            json=config,
            headers=headers
        )
        
        assert response.status_code == 404


@pytest.mark.integration
class TestJobStart:
    """Test job start endpoint and database building"""
    
    def test_start_configured_job(self, test_client, api_key, sample_pdfs, temp_workspace, monkeypatch):
        """Test starting a configured job builds database and queues it"""
        # Mock the database builder to avoid PyPDF2 dependency issues in test
        class MockDatabaseBuilder:
            def __init__(self, job_id, pdf_files):
                self.job_id = job_id
                self.pdf_files = pdf_files
                self.output_dir = temp_workspace / "jobs" / job_id
                self.output_dir.mkdir(parents=True, exist_ok=True)
            
            def build_database(self):
                # Create a simple CSV for testing
                csv_path = self.output_dir / "research_database.csv"
                csv_path.write_text(
                    "Title,Authors,Year,File,Abstract,Requirement(s),Score,Keywords\n"
                    "Test Paper,Test Author,2024,test.pdf,Test abstract,[],,'test'\n"
                )
                return csv_path
        
        monkeypatch.setattr("webdashboard.database_builder.ResearchDatabaseBuilder", MockDatabaseBuilder)
        
        # Create and configure job
        files = [
            ("files", ("paper1.pdf", io.BytesIO(sample_pdfs[0]), "application/pdf"))
        ]
        headers = {"X-API-KEY": api_key}
        upload_response = test_client.post("/api/upload/batch", files=files, headers=headers)
        job_id = upload_response.json()["job_id"]
        
        config = {
            "pillar_selections": ["ALL"],
            "run_mode": "ONCE",
            "convergence_threshold": 5.0
        }
        test_client.post(f"/api/jobs/{job_id}/configure", json=config, headers=headers)
        
        # Start job
        response = test_client.post(f"/api/jobs/{job_id}/start", headers=headers)
        
        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        
        # Verify database was created
        db_path = temp_workspace / "jobs" / job_id / "research_database.csv"
        assert db_path.exists()
        assert "Title" in db_path.read_text()
    
    def test_start_unconfigured_job(self, test_client, api_key, sample_pdfs):
        """Test starting an unconfigured job fails"""
        # Create draft job without configuration
        files = [
            ("files", ("paper1.pdf", io.BytesIO(sample_pdfs[0]), "application/pdf"))
        ]
        headers = {"X-API-KEY": api_key}
        upload_response = test_client.post("/api/upload/batch", files=files, headers=headers)
        job_id = upload_response.json()["job_id"]
        
        # Try to start without configuration
        response = test_client.post(f"/api/jobs/{job_id}/start", headers=headers)
        
        assert response.status_code == 400
        assert "must be configured" in response.json()["detail"]
    
    def test_start_job_without_files(self, test_client, api_key, temp_workspace):
        """Test starting a job without PDF files fails"""
        # Manually create a job without files
        job_id = "test-no-files"
        job_data = {
            "id": job_id,
            "status": "draft",
            "files": [],
            "file_count": 0,
            "created_at": "2024-01-01T00:00:00",
            "config": {
                "pillar_selections": ["ALL"],
                "run_mode": "ONCE",
                "convergence_threshold": 5.0
            }
        }
        
        job_file = temp_workspace / "jobs" / f"{job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(job_data, f)
        
        # Create empty job directory
        (temp_workspace / "uploads" / job_id).mkdir()
        
        headers = {"X-API-KEY": api_key}
        response = test_client.post(f"/api/jobs/{job_id}/start", headers=headers)
        
        # Should fail with 500 due to import error or 400 due to no files
        assert response.status_code in [400, 500]
        detail = response.json()["detail"]
        assert "No PDF files found" in detail or "Database builder" in detail


@pytest.mark.integration
class TestCompleteWorkflow:
    """Test the complete upload → configure → start workflow"""
    
    def test_complete_input_pipeline(self, test_client, api_key, sample_pdfs, temp_workspace, monkeypatch):
        """Test complete workflow from upload to job start"""
        # Mock database builder
        class MockDatabaseBuilder:
            def __init__(self, job_id, pdf_files):
                self.job_id = job_id
                self.pdf_files = pdf_files
                self.output_dir = temp_workspace / "jobs" / job_id
                self.output_dir.mkdir(parents=True, exist_ok=True)
            
            def build_database(self):
                csv_path = self.output_dir / "research_database.csv"
                csv_path.write_text(
                    "Title,Authors,Year,File,Abstract,Requirement(s),Score,Keywords\n"
                    f"Paper 1,Author 1,2024,{self.pdf_files[0]},Abstract 1,[],,''\n"
                    f"Paper 2,Author 2,2024,{self.pdf_files[1]},Abstract 2,[],,''\n"
                )
                return csv_path
        
        monkeypatch.setattr("webdashboard.database_builder.ResearchDatabaseBuilder", MockDatabaseBuilder)
        
        headers = {"X-API-KEY": api_key}
        
        # Step 1: Upload multiple files
        files = [
            ("files", ("paper1.pdf", io.BytesIO(sample_pdfs[0]), "application/pdf")),
            ("files", ("paper2.pdf", io.BytesIO(sample_pdfs[1]), "application/pdf"))
        ]
        upload_response = test_client.post("/api/upload/batch", files=files, headers=headers)
        assert upload_response.status_code == 200
        
        job_data = upload_response.json()
        job_id = job_data["job_id"]
        assert job_data["status"] == "draft"
        assert job_data["file_count"] == 2
        
        # Step 2: Configure job
        config = {
            "pillar_selections": ["Pillar_1", "Pillar_2"],
            "run_mode": "DEEP_LOOP",
            "convergence_threshold": 3.0
        }
        config_response = test_client.post(
            f"/api/jobs/{job_id}/configure",
            json=config,
            headers=headers
        )
        assert config_response.status_code == 200
        
        # Step 3: Start job
        start_response = test_client.post(f"/api/jobs/{job_id}/start", headers=headers)
        assert start_response.status_code == 200
        assert start_response.json()["status"] == "queued"
        
        # Step 4: Verify job details
        job_response = test_client.get(f"/api/jobs/{job_id}", headers=headers)
        assert job_response.status_code == 200
        job = job_response.json()
        assert job["status"] == "queued"
        assert job["config"]["pillar_selections"] == ["Pillar_1", "Pillar_2"]
        assert job["config"]["run_mode"] == "DEEP_LOOP"
        
        # Step 5: Verify database was created
        db_path = temp_workspace / "jobs" / job_id / "research_database.csv"
        assert db_path.exists()
        csv_content = db_path.read_text()
        assert "Paper 1" in csv_content
        assert "Paper 2" in csv_content
