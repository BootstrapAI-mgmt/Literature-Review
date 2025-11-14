"""
Test fixtures for Web Dashboard tests
"""

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
    
    return TestClient(app)


@pytest.fixture
def api_key():
    """Return test API key"""
    return "dev-key-change-in-production"


@pytest.fixture
def sample_pdf():
    """Create a minimal PDF file for testing"""
    # Minimal PDF content
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
    return pdf_content


@pytest.fixture
def create_job(temp_workspace):
    """Factory fixture to create test jobs"""
    def _create_job(job_id, status="queued", filename="test.pdf", error=None):
        job_data = {
            "id": job_id,
            "status": status,
            "filename": filename,
            "file_path": str(temp_workspace / "uploads" / f"{job_id}.pdf"),
            "created_at": "2024-01-01T00:00:00",
            "started_at": "2024-01-01T00:00:05" if status != "queued" else None,
            "completed_at": "2024-01-01T00:01:00" if status in ["completed", "failed"] else None,
            "error": error,
            "progress": {}
        }
        
        job_file = temp_workspace / "jobs" / f"{job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(job_data, f)
        
        return job_data
    
    return _create_job
