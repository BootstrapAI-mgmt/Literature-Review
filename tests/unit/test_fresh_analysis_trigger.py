"""
Unit tests for Fresh Analysis Trigger (PARITY-W1-3)

Tests cover:
- Directory state detection (not_exist, empty, has_csv, has_results)
- Recommendation generation
- API endpoint for directory analysis
- Fresh analysis flag setting in job metadata
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webdashboard.app import (
    detect_directory_state,
    get_recommendation_reason
)


class TestDetectDirectoryState:
    """Tests for detect_directory_state function."""
    
    def test_detect_directory_not_exist(self):
        """Test detection of non-existent directory."""
        non_existent = Path("/tmp/does_not_exist_test_" + str(datetime.now().timestamp()))
        
        state = detect_directory_state(non_existent)
        
        assert state["state"] == "not_exist"
        assert state["recommended_mode"] == "baseline"
        assert state["file_count"] == 0
        assert state["has_gap_report"] is False
        assert state["csv_files"] == []
        assert state["last_modified"] is None
    
    def test_detect_directory_empty(self):
        """Test detection of empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)
            
            state = detect_directory_state(empty_dir)
            
            assert state["state"] == "empty"
            assert state["recommended_mode"] == "baseline"
            assert state["file_count"] == 0
            assert state["has_gap_report"] is False
            assert state["csv_files"] == []
    
    def test_detect_directory_has_csv(self):
        """Test detection of directory with CSV files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_dir = Path(tmpdir)
            
            # Create CSV files
            (csv_dir / "test1.csv").write_text("col1,col2\nval1,val2")
            (csv_dir / "test2.csv").write_text("col1,col2\nval1,val2")
            
            state = detect_directory_state(csv_dir)
            
            assert state["state"] == "has_csv"
            assert state["recommended_mode"] == "baseline"
            assert len(state["csv_files"]) == 2
            assert "test1.csv" in state["csv_files"]
            assert "test2.csv" in state["csv_files"]
            assert state["has_gap_report"] is False
            assert state["last_modified"] is not None
    
    def test_detect_directory_has_results(self):
        """Test detection of directory with analysis results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            
            # Create gap analysis report
            (results_dir / "gap_analysis_report.json").write_text(
                json.dumps({"pillars": [], "gaps": []})
            )
            # Also add a CSV file
            (results_dir / "test.csv").write_text("col1,col2\nval1,val2")
            
            state = detect_directory_state(results_dir)
            
            assert state["state"] == "has_results"
            assert state["recommended_mode"] == "continuation"
            assert state["has_gap_report"] is True
            assert len(state["csv_files"]) == 1
            assert state["file_count"] == 2
            assert state["last_modified"] is not None
    
    def test_detect_directory_has_other_files(self):
        """Test detection of directory with non-CSV, non-report files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            other_dir = Path(tmpdir)
            
            # Create some other files
            (other_dir / "readme.txt").write_text("Some text")
            (other_dir / "image.png").write_text("fake image data")
            
            state = detect_directory_state(other_dir)
            
            # Should treat as empty (no recognizable analysis files)
            assert state["state"] == "empty"
            assert state["recommended_mode"] == "baseline"
            assert state["has_gap_report"] is False
            assert len(state["csv_files"]) == 0
            assert state["file_count"] == 2


class TestGetRecommendationReason:
    """Tests for get_recommendation_reason function."""
    
    def test_reason_not_exist(self):
        """Test reason for non-existent directory."""
        state = {"state": "not_exist"}
        reason = get_recommendation_reason(state)
        assert "doesn't exist" in reason.lower()
        assert "create" in reason.lower()
    
    def test_reason_empty(self):
        """Test reason for empty directory."""
        state = {"state": "empty"}
        reason = get_recommendation_reason(state)
        assert "empty" in reason.lower()
        assert "baseline" in reason.lower()
    
    def test_reason_has_csv(self):
        """Test reason for directory with CSV files."""
        state = {
            "state": "has_csv",
            "csv_files": ["test1.csv", "test2.csv"]
        }
        reason = get_recommendation_reason(state)
        assert "2" in reason
        assert "csv" in reason.lower()
    
    def test_reason_has_results(self):
        """Test reason for directory with analysis results."""
        state = {
            "state": "has_results",
            "last_modified": "2024-11-17T12:00:00"
        }
        reason = get_recommendation_reason(state)
        assert "existing analysis" in reason.lower()
        assert "2024-11-17" in reason
        assert "continue" in reason.lower()


class TestDirectoryAnalysisIntegration:
    """Integration tests for directory analysis in job workflow."""
    
    def test_fresh_analysis_empty_directory(self):
        """Test that empty directory triggers fresh analysis flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)
            
            state = detect_directory_state(empty_dir)
            fresh_analysis = state["state"] in ["not_exist", "empty", "has_csv"]
            
            assert fresh_analysis is True
            assert state["recommended_mode"] == "baseline"
    
    def test_fresh_analysis_has_csv(self):
        """Test that directory with CSV triggers fresh analysis flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_dir = Path(tmpdir)
            (csv_dir / "test.csv").write_text("col1,col2\nval1,val2")
            
            state = detect_directory_state(csv_dir)
            fresh_analysis = state["state"] in ["not_exist", "empty", "has_csv"]
            
            assert fresh_analysis is True
            assert state["recommended_mode"] == "baseline"
    
    def test_continuation_has_results(self):
        """Test that directory with results does NOT trigger fresh analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_dir = Path(tmpdir)
            (results_dir / "gap_analysis_report.json").write_text(
                json.dumps({"pillars": [], "gaps": []})
            )
            
            state = detect_directory_state(results_dir)
            fresh_analysis = state["state"] in ["not_exist", "empty", "has_csv"]
            
            assert fresh_analysis is False
            assert state["recommended_mode"] == "continuation"


# API endpoint tests would require FastAPI TestClient
# These are simplified unit tests for the core logic
class TestAPIEndpointLogic:
    """Tests for API endpoint logic (without full API testing)."""
    
    def test_directory_state_response_structure(self):
        """Test that directory state has correct response structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            (test_dir / "test.csv").write_text("data")
            
            state = detect_directory_state(test_dir)
            
            # Verify response has all required fields
            assert "state" in state
            assert "recommended_mode" in state
            assert "file_count" in state
            assert "has_gap_report" in state
            assert "csv_files" in state
            assert "last_modified" in state
            
            # Verify state is one of expected values
            assert state["state"] in ["not_exist", "empty", "has_csv", "has_results"]
            assert state["recommended_mode"] in ["baseline", "continuation"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
