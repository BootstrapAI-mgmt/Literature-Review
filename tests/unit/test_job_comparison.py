"""
Unit tests for job comparison functionality

Tests cover:
- Basic job comparison
- Gap differential calculation
- Completeness change detection
- Regression detection
"""

import json
import tempfile
from pathlib import Path

import pytest


def create_mock_job_data(job_id, completeness=60.0, papers=None, gaps=None, status="completed", created_at="2025-01-01T00:00:00"):
    """Create mock job data for testing"""
    if papers is None:
        papers = ["paper1.pdf", "paper2.pdf"]
    
    return {
        "id": job_id,
        "status": status,
        "filename": papers[0] if len(papers) == 1 else None,
        "files": [{"original_name": p} for p in papers] if len(papers) > 1 else None,
        "created_at": created_at,
        "completed_at": "2025-01-01T01:00:00"
    }


def create_mock_gap_analysis_report(completeness_values=None):
    """Create mock gap analysis report"""
    if completeness_values is None:
        completeness_values = {"Pillar 1: Test": 60.0}
    
    report = {}
    for pillar_name, completeness in completeness_values.items():
        report[pillar_name] = {
            "completeness": completeness,
            "analysis": {
                "REQ-1: Test Requirement": {
                    "Sub-1.1: Test Sub-requirement": {
                        "completeness_percent": 50,
                        "gap_analysis": "Test gap",
                        "confidence_level": "high",
                        "contributing_papers": []
                    }
                }
            }
        }
    
    return report


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


@pytest.mark.unit
class TestJobComparisonHelpers:
    """Unit tests for job comparison helper functions"""
    
    def test_extract_completeness(self, temp_workspace, monkeypatch):
        """Test extracting completeness from job data"""
        from webdashboard.app import extract_completeness
        
        # Monkeypatch JOBS_DIR
        monkeypatch.setattr('webdashboard.app.JOBS_DIR', temp_workspace / "jobs")
        
        job_id = "test-job-001"
        job_data = create_mock_job_data(job_id)
        
        # Create output directory and gap analysis report
        output_dir = temp_workspace / "jobs" / job_id / "outputs" / "gap_analysis_output"
        output_dir.mkdir(parents=True)
        
        report = create_mock_gap_analysis_report({
            "Pillar 1: Test": 60.0,
            "Pillar 2: Test": 80.0
        })
        
        with open(output_dir / "gap_analysis_report.json", 'w') as f:
            json.dump(report, f)
        
        # Test extraction
        completeness = extract_completeness(job_data)
        assert completeness == 70.0  # Average of 60 and 80
    
    def test_extract_completeness_no_report(self, temp_workspace, monkeypatch):
        """Test extracting completeness when report doesn't exist"""
        from webdashboard.app import extract_completeness
        
        monkeypatch.setattr('webdashboard.app.JOBS_DIR', temp_workspace / "jobs")
        
        job_id = "test-job-002"
        job_data = create_mock_job_data(job_id)
        
        # Don't create report file
        completeness = extract_completeness(job_data)
        assert completeness == 0.0
    
    def test_extract_papers_multiple_files(self, temp_workspace):
        """Test extracting papers from job with multiple files"""
        from webdashboard.app import extract_papers
        
        job_data = create_mock_job_data("test-job", papers=["paper1.pdf", "paper2.pdf", "paper3.pdf"])
        
        papers = extract_papers(job_data)
        assert len(papers) == 3
        assert "paper1.pdf" in papers
        assert "paper2.pdf" in papers
        assert "paper3.pdf" in papers
    
    def test_extract_papers_single_file(self, temp_workspace):
        """Test extracting papers from job with single file"""
        from webdashboard.app import extract_papers
        
        job_data = {
            "id": "test-job",
            "filename": "single.pdf",
            "status": "completed"
        }
        
        papers = extract_papers(job_data)
        assert len(papers) == 1
        assert "single.pdf" in papers
    
    def test_extract_gaps(self, temp_workspace, monkeypatch):
        """Test extracting gaps from job data"""
        from webdashboard.app import extract_gaps
        
        monkeypatch.setattr('webdashboard.app.JOBS_DIR', temp_workspace / "jobs")
        
        job_id = "test-job-003"
        job_data = create_mock_job_data(job_id)
        
        # Create output directory and gap analysis report
        output_dir = temp_workspace / "jobs" / job_id / "outputs" / "gap_analysis_output"
        output_dir.mkdir(parents=True)
        
        report = {
            "Pillar 1: Test": {
                "completeness": 60.0,
                "analysis": {
                    "REQ-1: Test Requirement": {
                        "Sub-1.1: Test Sub-requirement 1": {
                            "completeness_percent": 50,
                            "gap_analysis": "Gap 1",
                        },
                        "Sub-1.2: Test Sub-requirement 2": {
                            "completeness_percent": 100,
                            "gap_analysis": "No gap",
                        }
                    }
                }
            }
        }
        
        with open(output_dir / "gap_analysis_report.json", 'w') as f:
            json.dump(report, f)
        
        gaps = extract_gaps(job_data)
        
        # Should only return the gap with completeness < 100
        assert len(gaps) == 1
        assert gaps[0]["completeness"] == 50
        assert gaps[0]["pillar"] == "Pillar 1: Test"
    
    def test_extract_gaps_no_report(self, temp_workspace, monkeypatch):
        """Test extracting gaps when report doesn't exist"""
        from webdashboard.app import extract_gaps
        
        monkeypatch.setattr('webdashboard.app.JOBS_DIR', temp_workspace / "jobs")
        
        job_id = "test-job-004"
        job_data = create_mock_job_data(job_id)
        
        gaps = extract_gaps(job_data)
        assert gaps == []


@pytest.mark.unit
class TestJobComparisonLogic:
    """Unit tests for job comparison logic"""
    
    def test_papers_added(self):
        """Test detection of papers added between jobs"""
        job1_papers = ["paper1.pdf", "paper2.pdf"]
        job2_papers = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]
        
        papers_added = [p for p in job2_papers if p not in job1_papers]
        
        assert len(papers_added) == 1
        assert "paper3.pdf" in papers_added
    
    def test_papers_removed(self):
        """Test detection of papers removed between jobs"""
        job1_papers = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]
        job2_papers = ["paper1.pdf", "paper2.pdf"]
        
        papers_removed = [p for p in job1_papers if p not in job2_papers]
        
        assert len(papers_removed) == 1
        assert "paper3.pdf" in papers_removed
    
    def test_completeness_improvement(self):
        """Test calculation of completeness improvement"""
        job1_completeness = 60.0
        job2_completeness = 75.0
        
        improvement = job2_completeness - job1_completeness
        
        assert improvement == 15.0
    
    def test_completeness_regression(self):
        """Test detection of completeness regression"""
        job1_completeness = 80.0
        job2_completeness = 70.0
        
        change = job2_completeness - job1_completeness
        
        assert change == -10.0
        assert change < 0  # Regression detected
    
    def test_gap_filled_detection(self):
        """Test detection of gaps that were filled"""
        # Gap present in job1 but not in job2
        job1_gaps = [
            {
                "pillar": "Pillar 1",
                "requirement": "REQ-1",
                "sub_requirement": "Sub-1.1",
                "completeness": 50
            }
        ]
        job2_gaps = []  # Gap was filled
        
        # Create gap dictionaries
        job1_gap_dict = {
            f"{g['pillar']}|{g['requirement']}|{g['sub_requirement']}": g
            for g in job1_gaps
        }
        job2_gap_dict = {
            f"{g['pillar']}|{g['requirement']}|{g['sub_requirement']}": g
            for g in job2_gaps
        }
        
        gaps_filled = []
        for gap_key, gap1 in job1_gap_dict.items():
            if gap_key not in job2_gap_dict:
                # Gap completely filled
                gaps_filled.append({
                    "gap": f"{gap1['requirement']} - {gap1['sub_requirement']}",
                    "improvement": 100 - gap1['completeness']
                })
        
        assert len(gaps_filled) == 1
        assert gaps_filled[0]["improvement"] == 50
    
    def test_gap_improvement_detection(self):
        """Test detection of gaps that improved but weren't fully filled"""
        job1_gaps = [
            {
                "pillar": "Pillar 1",
                "requirement": "REQ-1",
                "sub_requirement": "Sub-1.1",
                "completeness": 50
            }
        ]
        job2_gaps = [
            {
                "pillar": "Pillar 1",
                "requirement": "REQ-1",
                "sub_requirement": "Sub-1.1",
                "completeness": 80
            }
        ]
        
        # Create gap dictionaries
        job1_gap_dict = {
            f"{g['pillar']}|{g['requirement']}|{g['sub_requirement']}": g
            for g in job1_gaps
        }
        job2_gap_dict = {
            f"{g['pillar']}|{g['requirement']}|{g['sub_requirement']}": g
            for g in job2_gaps
        }
        
        gaps_improved = []
        for gap_key, gap1 in job1_gap_dict.items():
            if gap_key in job2_gap_dict:
                gap2 = job2_gap_dict[gap_key]
                if gap2['completeness'] > gap1['completeness']:
                    gaps_improved.append({
                        "gap": f"{gap1['requirement']} - {gap1['sub_requirement']}",
                        "improvement": gap2['completeness'] - gap1['completeness']
                    })
        
        assert len(gaps_improved) == 1
        assert gaps_improved[0]["improvement"] == 30
