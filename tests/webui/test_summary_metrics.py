"""
Unit tests for summary metrics extraction

Tests the extract_summary_metrics function that calculates:
- Completeness percentage
- Critical gaps count
- Paper count
- Recommendations preview
"""

import json
from pathlib import Path


def test_extract_summary_metrics_with_results(test_client, api_key, create_job, temp_workspace):
    """Test summary metric extraction for completed job with results"""
    # Create a job
    job = create_job("test-job-1", "completed")
    
    # Create output directory structure
    job_output_dir = temp_workspace / "jobs" / "test-job-1" / "outputs" / "gap_analysis_output"
    job_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create gap analysis results
    gap_analysis = {
        "overall_completeness": 85.5,
        "gaps": [
            {"severity": 9, "description": "Critical gap 1"},
            {"severity": 8, "description": "Critical gap 2"},
            {"severity": 5, "description": "Medium gap"}
        ],
        "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"]
    }
    
    gap_file = job_output_dir / "gap_analysis.json"
    with open(gap_file, 'w') as f:
        json.dump(gap_analysis, f)
    
    # Update job data with papers
    job_file = temp_workspace / "jobs" / "test-job-1.json"
    job_data = json.loads(job_file.read_text())
    job_data["papers"] = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]
    with open(job_file, 'w') as f:
        json.dump(job_data, f)
    
    # Get jobs list with summary
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Find our test job
    job = next((j for j in data["jobs"] if j["id"] == "test-job-1"), None)
    assert job is not None
    
    # Check summary metrics
    assert "summary" in job
    summary = job["summary"]
    
    assert summary["completeness"] == 85.5
    assert summary["critical_gaps"] == 2  # Only severity >= 8
    assert summary["paper_count"] == 3
    assert len(summary["recommendations_preview"]) == 2  # First 2 recommendations
    assert summary["has_results"] is True


def test_extract_summary_no_results(test_client, api_key, create_job):
    """Test summary when job has no results (not completed)"""
    job = create_job("test-job-2", "running")
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    job = next((j for j in data["jobs"] if j["id"] == "test-job-2"), None)
    assert job is not None
    
    summary = job["summary"]
    assert summary["has_results"] is False
    assert summary["completeness"] == 0
    assert summary["critical_gaps"] == 0
    assert summary["paper_count"] == 0
    assert summary["recommendations_preview"] == []


def test_extract_summary_with_file_count(test_client, api_key, create_job, temp_workspace):
    """Test summary uses file_count when papers list not available"""
    job = create_job("test-job-3", "completed")
    
    # Update job data with file_count instead of papers
    job_file = temp_workspace / "jobs" / "test-job-3.json"
    job_data = json.loads(job_file.read_text())
    job_data["file_count"] = 5
    with open(job_file, 'w') as f:
        json.dump(job_data, f)
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    job = next((j for j in data["jobs"] if j["id"] == "test-job-3"), None)
    assert job is not None
    
    summary = job["summary"]
    assert summary["paper_count"] == 5


def test_extract_summary_pillar_completeness(test_client, api_key, create_job, temp_workspace):
    """Test completeness calculation from pillar data"""
    job = create_job("test-job-4", "completed")
    
    # Create output directory structure
    job_output_dir = temp_workspace / "jobs" / "test-job-4" / "outputs" / "gap_analysis_output"
    job_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create gap analysis results with pillar data
    gap_analysis = {
        "pillars": {
            "Pillar 1": {"completeness": 80.0},
            "Pillar 2": {"completeness": 90.0},
            "Pillar 3": {"completeness": 70.0}
        },
        "gaps": [],
        "recommendations": []
    }
    
    gap_file = job_output_dir / "gap_analysis.json"
    with open(gap_file, 'w') as f:
        json.dump(gap_analysis, f)
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    job = next((j for j in data["jobs"] if j["id"] == "test-job-4"), None)
    assert job is not None
    
    summary = job["summary"]
    # Average of 80, 90, 70 = 80
    assert summary["completeness"] == 80.0
    assert summary["has_results"] is True


def test_completeness_color_thresholds(test_client, api_key, create_job, temp_workspace):
    """Test that different completeness values would be color-coded correctly"""
    # This test verifies the data is correct for frontend color coding
    # Frontend uses: >=80 green, >=60 yellow, <60 red
    
    test_cases = [
        ("job-90", 90.0),  # Should be green
        ("job-75", 75.0),  # Should be yellow
        ("job-50", 50.0),  # Should be red
        ("job-80", 80.0),  # Boundary - should be green
    ]
    
    for job_id, completeness in test_cases:
        job = create_job(job_id, "completed")
        
        # Create output with specific completeness
        job_output_dir = temp_workspace / "jobs" / job_id / "outputs" / "gap_analysis_output"
        job_output_dir.mkdir(parents=True, exist_ok=True)
        
        gap_analysis = {
            "overall_completeness": completeness,
            "gaps": [],
            "recommendations": []
        }
        
        gap_file = job_output_dir / "gap_analysis.json"
        with open(gap_file, 'w') as f:
            json.dump(gap_analysis, f)
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify each job has correct completeness
    for job_id, expected_completeness in test_cases:
        job = next((j for j in data["jobs"] if j["id"] == job_id), None)
        assert job is not None
        assert job["summary"]["completeness"] == expected_completeness


def test_critical_gaps_threshold(test_client, api_key, create_job, temp_workspace):
    """Test that only gaps with severity >= 8 are counted as critical"""
    job = create_job("test-job-gaps", "completed")
    
    # Create output with various severity gaps
    job_output_dir = temp_workspace / "jobs" / "test-job-gaps" / "outputs" / "gap_analysis_output"
    job_output_dir.mkdir(parents=True, exist_ok=True)
    
    gap_analysis = {
        "overall_completeness": 70.0,
        "gaps": [
            {"severity": 10, "description": "Critical 1"},
            {"severity": 9, "description": "Critical 2"},
            {"severity": 8, "description": "Critical 3"},  # Boundary - should count
            {"severity": 7, "description": "High but not critical"},
            {"severity": 5, "description": "Medium"},
            {"severity": 3, "description": "Low"}
        ],
        "recommendations": []
    }
    
    gap_file = job_output_dir / "gap_analysis.json"
    with open(gap_file, 'w') as f:
        json.dump(gap_analysis, f)
    
    headers = {"X-API-KEY": api_key}
    response = test_client.get("/api/jobs", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    job = next((j for j in data["jobs"] if j["id"] == "test-job-gaps"), None)
    assert job is not None
    
    # Should count only severity 8, 9, 10 = 3 critical gaps
    assert job["summary"]["critical_gaps"] == 3
