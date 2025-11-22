"""
Integration test for Fresh Analysis Trigger API endpoint

Tests the /api/upload/analyze-directory endpoint
"""

import pytest
import tempfile
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Import the FastAPI app
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webdashboard.app import app, API_KEY


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def api_headers():
    """Return API headers with auth key."""
    return {"X-API-KEY": API_KEY}


class TestDirectoryAnalysisAPI:
    """Integration tests for directory analysis API endpoint."""
    
    def test_analyze_nonexistent_directory(self, client, api_headers):
        """Test analysis of non-existent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "nonexistent"
            
            response = client.post(
                "/api/upload/analyze-directory",
                json={"directory_path": str(test_path)},
                headers=api_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "directory" in data
            assert "state" in data
            assert "recommendation" in data
            
            assert data["state"]["state"] == "not_exist"
            assert data["recommendation"]["mode"] == "baseline"
            assert "doesn't exist" in data["recommendation"]["reason"].lower()
    
    def test_analyze_empty_directory(self, client, api_headers):
        """Test analysis of empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            response = client.post(
                "/api/upload/analyze-directory",
                json={"directory_path": tmpdir},
                headers=api_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["state"]["state"] == "empty"
            assert data["state"]["file_count"] == 0
            assert data["recommendation"]["mode"] == "baseline"
            assert "empty" in data["recommendation"]["reason"].lower()
    
    def test_analyze_directory_with_csv(self, client, api_headers):
        """Test analysis of directory with CSV files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CSV files
            (Path(tmpdir) / "test1.csv").write_text("col1,col2\nval1,val2")
            (Path(tmpdir) / "test2.csv").write_text("col1,col2\nval1,val2")
            
            response = client.post(
                "/api/upload/analyze-directory",
                json={"directory_path": tmpdir},
                headers=api_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["state"]["state"] == "has_csv"
            assert len(data["state"]["csv_files"]) == 2
            assert data["recommendation"]["mode"] == "baseline"
            assert "csv" in data["recommendation"]["reason"].lower()
    
    def test_analyze_directory_with_results(self, client, api_headers):
        """Test analysis of directory with gap analysis results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create gap analysis report
            report = {"pillars": [], "gaps": []}
            (Path(tmpdir) / "gap_analysis_report.json").write_text(
                json.dumps(report)
            )
            
            response = client.post(
                "/api/upload/analyze-directory",
                json={"directory_path": tmpdir},
                headers=api_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["state"]["state"] == "has_results"
            assert data["state"]["has_gap_report"] is True
            assert data["recommendation"]["mode"] == "continuation"
            assert "existing analysis" in data["recommendation"]["reason"].lower()
    
    def test_analyze_directory_missing_path(self, client, api_headers):
        """Test analysis with missing directory_path."""
        response = client.post(
            "/api/upload/analyze-directory",
            json={},
            headers=api_headers
        )
        
        assert response.status_code == 400
        assert "directory_path is required" in response.json()["detail"]
    
    def test_analyze_directory_invalid_api_key(self, client):
        """Test analysis with invalid API key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            response = client.post(
                "/api/upload/analyze-directory",
                json={"directory_path": tmpdir},
                headers={"X-API-KEY": "invalid-key"}
            )
            
            assert response.status_code == 401
    
    def test_analyze_directory_system_dir_rejection(self, client, api_headers):
        """Test that system directories are rejected."""
        response = client.post(
            "/api/upload/analyze-directory",
            json={"directory_path": "/etc"},
            headers=api_headers
        )
        
        assert response.status_code == 400
        assert "system directories" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--no-cov"])
