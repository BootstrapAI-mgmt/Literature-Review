"""
Integration tests for dashboard enhanced output endpoints.

Tests:
- Proof scorecard endpoint
- Cost summary endpoint
- Sufficiency matrix summary endpoint
- Output file serving

Note: These tests use TestClient which properly handles async endpoints internally.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create test client for dashboard app."""
    # Import here to avoid circular dependencies
    from webdashboard.app import app
    return TestClient(app)


@pytest.fixture
def mock_job_outputs(tmp_path):
    """Create mock job output files for testing."""
    job_id = "test-job-123"
    job_dir = tmp_path / "workspace" / "jobs" / job_id / "outputs"
    
    # Create proof scorecard output
    scorecard_dir = job_dir / "proof_scorecard_output"
    scorecard_dir.mkdir(parents=True, exist_ok=True)
    
    scorecard_data = {
        "overall_proof_status": {
            "proof_readiness_score": 65,
            "verdict": "MODERATE",
            "headline": "Research shows promise but needs strengthening"
        },
        "publication_viability": {
            "tier": "2",
            "venues": ["Conference A", "Journal B"]
        },
        "research_goals": [
            {"goal": "Goal 1", "score": 80},
            {"goal": "Goal 2", "score": 60},
            {"goal": "Goal 3", "score": 50}
        ],
        "critical_next_steps": [
            "Add more evidence for claim X",
            "Strengthen foundation Y",
            "Fill gap Z",
            "Verify claim W",
            "Expand coverage V"
        ]
    }
    
    with open(scorecard_dir / "proof_scorecard.json", 'w') as f:
        json.dump(scorecard_data, f)
    
    with open(scorecard_dir / "proof_readiness.html", 'w') as f:
        f.write("<html><body>Proof Scorecard</body></html>")
    
    # Create cost report
    cost_dir = job_dir / "cost_reports"
    cost_dir.mkdir(parents=True, exist_ok=True)
    
    cost_data = {
        "total_cost_usd": 5.23,
        "budget_percent_used": 52.3,
        "cost_per_paper": 0.52,
        "total_tokens": 150000,
        "module_breakdown": {
            "journal_reviewer": 2.50,
            "judge": 1.50,
            "gap_analysis": 1.23
        },
        "cache_savings_usd": 0.75
    }
    
    with open(cost_dir / "api_usage_report.json", 'w') as f:
        json.dump(cost_data, f)
    
    with open(cost_dir / "api_usage_report.html", 'w') as f:
        f.write("<html><body>Cost Report</body></html>")
    
    # Create sufficiency matrix
    gap_dir = job_dir / "gap_analysis_output"
    gap_dir.mkdir(parents=True, exist_ok=True)
    
    sufficiency_data = {
        "requirements": [
            {"id": "REQ-1", "quadrant": "Q1-Strong-Foundation"},
            {"id": "REQ-2", "quadrant": "Q1-Strong-Foundation"},
            {"id": "REQ-3", "quadrant": "Q2-Promising-Seeds"},
            {"id": "REQ-4", "quadrant": "Q3-Hollow-Coverage"},
            {"id": "REQ-5", "quadrant": "Q4-Critical-Gaps"}
        ],
        "recommendations": [
            "Focus on Q4 gaps",
            "Strengthen Q2 evidence",
            "Maintain Q1 quality",
            "Address Q3 depth",
            "Prioritize critical gaps"
        ]
    }
    
    with open(gap_dir / "sufficiency_matrix.json", 'w') as f:
        json.dump(sufficiency_data, f)
    
    with open(gap_dir / "sufficiency_matrix.html", 'w') as f:
        f.write("<html><body>Sufficiency Matrix</body></html>")
    
    return job_dir, job_id


class TestEnhancedOutputEndpoints:
    """Test enhanced output API endpoints."""
    
    def test_proof_scorecard_endpoint_available(self, test_client, mock_job_outputs, monkeypatch):
        """Test proof scorecard endpoint when data is available."""
        job_dir, job_id = mock_job_outputs
        
        # Mock the JOBS_DIR to point to our temp directory
        monkeypatch.setattr(
            'webdashboard.app.JOBS_DIR',
            job_dir.parent.parent
        )
        
        response = test_client.get(
            f"/api/jobs/{job_id}/proof-scorecard",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["available"] is True
        assert data["overall_score"] == 65
        assert data["verdict"] == "MODERATE"
        assert "headline" in data
        assert len(data["research_goals"]) == 3
        assert len(data["next_steps"]) == 5
    
    def test_proof_scorecard_endpoint_not_available(self, test_client):
        """Test proof scorecard endpoint when data is not available."""
        response = test_client.get(
            "/api/jobs/nonexistent-job/proof-scorecard",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["available"] is False
        assert "message" in data
    
    def test_cost_summary_endpoint_available(self, test_client, mock_job_outputs, monkeypatch):
        """Test cost summary endpoint when data is available."""
        job_dir, job_id = mock_job_outputs
        
        monkeypatch.setattr(
            'webdashboard.app.JOBS_DIR',
            job_dir.parent.parent
        )
        
        response = test_client.get(
            f"/api/jobs/{job_id}/cost-summary",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["available"] is True
        assert data["total_cost"] == 5.23
        assert data["budget_percent"] == 52.3
        assert data["per_paper_cost"] == 0.52
        assert "module_breakdown" in data
        assert data["cache_savings"] == 0.75
    
    def test_cost_summary_endpoint_not_available(self, test_client):
        """Test cost summary endpoint when data is not available."""
        response = test_client.get(
            "/api/jobs/nonexistent-job/cost-summary",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["available"] is False
        assert data["total_cost"] == 0
    
    def test_sufficiency_summary_endpoint_available(self, test_client, mock_job_outputs, monkeypatch):
        """Test sufficiency summary endpoint when data is available."""
        job_dir, job_id = mock_job_outputs
        
        monkeypatch.setattr(
            'webdashboard.app.JOBS_DIR',
            job_dir.parent.parent
        )
        
        response = test_client.get(
            f"/api/jobs/{job_id}/sufficiency-summary",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["available"] is True
        assert data["total_requirements"] == 5
        assert "quadrants" in data
        assert data["quadrants"]["Q1-Strong-Foundation"] == 2
        assert len(data["recommendations"]) == 5
    
    def test_sufficiency_summary_endpoint_not_available(self, test_client):
        """Test sufficiency summary endpoint when data is not available."""
        response = test_client.get(
            "/api/jobs/nonexistent-job/sufficiency-summary",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["available"] is False
        assert data["quadrants"] == {}
    
    def test_output_file_serving_html(self, test_client, mock_job_outputs, monkeypatch):
        """Test serving HTML output files."""
        job_dir, job_id = mock_job_outputs
        
        monkeypatch.setattr(
            'webdashboard.app.JOBS_DIR',
            job_dir.parent.parent
        )
        
        response = test_client.get(
            f"/api/jobs/{job_id}/files/proof_scorecard_output/proof_readiness.html",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Proof Scorecard" in response.content
    
    def test_output_file_serving_json(self, test_client, mock_job_outputs, monkeypatch):
        """Test serving JSON output files."""
        job_dir, job_id = mock_job_outputs
        
        monkeypatch.setattr(
            'webdashboard.app.JOBS_DIR',
            job_dir.parent.parent
        )
        
        response = test_client.get(
            f"/api/jobs/{job_id}/files/cost_reports/api_usage_report.json",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
    
    def test_output_file_serving_not_found(self, test_client):
        """Test serving non-existent file returns 404."""
        response = test_client.get(
            "/api/jobs/test-job/files/nonexistent/file.html",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        assert response.status_code == 404
    
    def test_output_file_path_traversal_blocked(self, test_client):
        """Test that path traversal attacks are blocked."""
        response = test_client.get(
            "/api/jobs/test-job/files/../../etc/passwd",
            headers={"X-API-KEY": "dev-key-change-in-production"}
        )
        
        # Should get 400 or 403, not 200
        assert response.status_code in [400, 403, 404]
