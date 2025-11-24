"""
Unit tests for Direct Directory Input feature (PARITY-W3-2)

Tests the directory scan endpoint and directory input support for jobs.
"""

import io
import json
import tempfile
from pathlib import Path

import pytest


class TestDirectoryScanEndpoint:
    """Tests for /api/directory/scan endpoint."""
    
    def test_scan_directory_success(self, test_client, api_key, temp_workspace):
        """Test scanning a valid directory with papers."""
        # Create test directory with papers
        test_dir = temp_workspace / "test_papers"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "paper1.pdf").touch()
        (test_dir / "paper2.pdf").touch()
        (test_dir / "data.csv").touch()
        
        response = test_client.post(
            "/api/directory/scan",
            json={"path": str(test_dir)},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pdf_count"] == 2
        assert data["csv_count"] == 1
        assert data["total_files"] == 3
        assert data["path"] == str(test_dir)
        assert data["recursive"] is True  # Default
        assert data["follow_symlinks"] is False  # Default
        assert len(data["files"]) == 3
        
        # Check file metadata
        filenames = {f["filename"] for f in data["files"]}
        assert "paper1.pdf" in filenames
        assert "paper2.pdf" in filenames
        assert "data.csv" in filenames
    
    def test_scan_directory_recursive(self, test_client, api_key, temp_workspace):
        """Test recursive directory scanning."""
        # Create nested structure
        test_dir = temp_workspace / "test_nested"
        (test_dir / "subdir" / "deep").mkdir(parents=True, exist_ok=True)
        
        (test_dir / "paper1.pdf").touch()
        (test_dir / "subdir" / "paper2.pdf").touch()
        (test_dir / "subdir" / "deep" / "paper3.pdf").touch()
        
        response = test_client.post(
            "/api/directory/scan",
            json={"path": str(test_dir), "recursive": True},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pdf_count"] == 3
        assert data["subdirectory_count"] == 2  # subdir and subdir/deep
    
    def test_scan_directory_non_recursive(self, test_client, api_key, temp_workspace):
        """Test non-recursive directory scanning (top level only)."""
        # Create nested structure
        test_dir = temp_workspace / "test_flat"
        (test_dir / "subdir").mkdir(parents=True, exist_ok=True)
        
        (test_dir / "paper1.pdf").touch()
        (test_dir / "subdir" / "paper2.pdf").touch()
        
        response = test_client.post(
            "/api/directory/scan",
            json={"path": str(test_dir), "recursive": False},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pdf_count"] == 1  # Only top level
        assert data["subdirectory_count"] == 0
    
    def test_scan_nonexistent_directory(self, test_client, api_key, temp_workspace):
        """Test scanning non-existent directory."""
        # Use a path within temp_workspace so it passes security check
        nonexistent_dir = temp_workspace / "nonexistent_subdir"
        
        response = test_client.post(
            "/api/directory/scan",
            json={"path": str(nonexistent_dir)},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_scan_empty_directory(self, test_client, api_key, temp_workspace):
        """Test scanning directory with no papers."""
        # Create empty directory
        test_dir = temp_workspace / "empty_dir"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        response = test_client.post(
            "/api/directory/scan",
            json={"path": str(test_dir)},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 404
        assert "No PDF or CSV files found" in response.json()["detail"]
    
    def test_scan_directory_with_only_other_files(self, test_client, api_key, temp_workspace):
        """Test scanning directory with non-paper files."""
        test_dir = temp_workspace / "other_files"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "readme.md").touch()
        (test_dir / "image.png").touch()
        (test_dir / "config.json").touch()
        
        response = test_client.post(
            "/api/directory/scan",
            json={"path": str(test_dir)},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 404
        assert "No PDF or CSV files found" in response.json()["detail"]
    
    def test_scan_file_not_directory(self, test_client, api_key, temp_workspace):
        """Test scanning a file (not directory)."""
        test_file = temp_workspace / "test.pdf"
        test_file.touch()
        
        response = test_client.post(
            "/api/directory/scan",
            json={"path": str(test_file)},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 400
        assert "not a directory" in response.json()["detail"].lower()
    
    def test_scan_relative_path_rejected(self, test_client, api_key):
        """Test that relative paths are rejected."""
        response = test_client.post(
            "/api/directory/scan",
            json={"path": "relative/path/to/papers"},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 400
        assert "absolute" in response.json()["detail"].lower()
    
    def test_scan_requires_api_key(self, test_client, temp_workspace):
        """Test that API key is required."""
        test_dir = temp_workspace / "test_papers"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "paper.pdf").touch()
        
        response = test_client.post(
            "/api/directory/scan",
            json={"path": str(test_dir)}
        )
        
        assert response.status_code == 401
    
    def test_scan_mixed_case_extensions(self, test_client, api_key, temp_workspace):
        """Test scanning with mixed case file extensions."""
        test_dir = temp_workspace / "mixed_case"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "paper1.pdf").touch()
        (test_dir / "paper2.PDF").touch()
        (test_dir / "data1.csv").touch()
        (test_dir / "data2.CSV").touch()
        
        response = test_client.post(
            "/api/directory/scan",
            json={"path": str(test_dir)},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find all 4 files regardless of case
        assert data["total_files"] == 4
    
    def test_scan_file_metadata(self, test_client, api_key, temp_workspace):
        """Test that file metadata is correctly extracted."""
        test_dir = temp_workspace / "metadata_test"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a file with some content
        paper_file = test_dir / "research_paper.pdf"
        paper_file.write_bytes(b"PDF content here" * 100)  # ~1.5KB
        
        response = test_client.post(
            "/api/directory/scan",
            json={"path": str(test_dir)},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["files"]) == 1
        file_meta = data["files"][0]
        
        assert file_meta["filename"] == "research_paper.pdf"
        assert file_meta["type"] == "pdf"
        assert file_meta["size_bytes"] > 0
        assert "modified" in file_meta
        assert "created" in file_meta
        assert file_meta["relative_path"] == "research_paper.pdf"


class TestDirectoryInputJobCreation:
    """Tests for creating jobs with directory input method."""
    
    def test_configure_job_with_directory_input(self, test_client, api_key, create_job, temp_workspace):
        """Test configuring a job with directory input method."""
        # Create job first
        job = create_job("dir-input-job-1", "draft")
        
        # Create test directory with papers
        test_dir = temp_workspace / "papers_for_job"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "paper1.pdf").touch()
        (test_dir / "paper2.pdf").touch()
        
        # Configure with directory input
        response = test_client.post(
            f"/api/jobs/dir-input-job-1/configure",
            json={
                "pillar_selections": ["ALL"],
                "run_mode": "ONCE",
                "input_method": "directory",
                "data_dir": str(test_dir),
                "scan_recursive": True,
                "follow_symlinks": False
            },
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["input_method"] == "directory"
        assert data["data_dir"] == str(test_dir)
        assert data["file_count"] == 2
    
    def test_configure_job_directory_not_found(self, test_client, api_key, create_job, temp_workspace):
        """Test configuring job with non-existent directory."""
        job = create_job("dir-input-job-2", "draft")
        
        # Use a path within temp_workspace so it passes security check but doesn't exist
        nonexistent_dir = temp_workspace / "nonexistent_papers"
        
        response = test_client.post(
            f"/api/jobs/dir-input-job-2/configure",
            json={
                "pillar_selections": ["ALL"],
                "run_mode": "ONCE",
                "input_method": "directory",
                "data_dir": str(nonexistent_dir)
            },
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_configure_job_directory_empty(self, test_client, api_key, create_job, temp_workspace):
        """Test configuring job with empty directory."""
        job = create_job("dir-input-job-3", "draft")
        
        # Create empty directory
        empty_dir = temp_workspace / "empty_papers"
        empty_dir.mkdir(parents=True, exist_ok=True)
        
        response = test_client.post(
            f"/api/jobs/dir-input-job-3/configure",
            json={
                "pillar_selections": ["ALL"],
                "run_mode": "ONCE",
                "input_method": "directory",
                "data_dir": str(empty_dir)
            },
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 404
        assert "No PDF or CSV" in response.json()["detail"]
    
    def test_configure_job_directory_missing_data_dir(self, test_client, api_key, create_job):
        """Test that data_dir is required for directory input method."""
        job = create_job("dir-input-job-4", "draft")
        
        response = test_client.post(
            f"/api/jobs/dir-input-job-4/configure",
            json={
                "pillar_selections": ["ALL"],
                "run_mode": "ONCE",
                "input_method": "directory"
                # Missing data_dir
            },
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code == 400
        assert "data_dir" in response.json()["detail"].lower()


class TestPathSecurityValidation:
    """Tests for path security validation."""
    
    def test_path_traversal_blocked_parent(self, test_client, api_key):
        """Test that parent directory traversal is blocked."""
        response = test_client.post(
            "/api/directory/scan",
            json={"path": "/tmp/../etc/passwd"},
            headers={"X-API-KEY": api_key}
        )
        
        # Should be blocked - either 403 (access denied) or 404 (not found)
        # depending on how path resolution works
        assert response.status_code in [403, 404]
    
    def test_path_traversal_blocked_double_dots(self, test_client, api_key):
        """Test that .. traversal attempts are handled."""
        response = test_client.post(
            "/api/directory/scan",
            json={"path": "/../../etc/passwd"},
            headers={"X-API-KEY": api_key}
        )
        
        assert response.status_code in [400, 403, 404]
    
    def test_restricted_system_directory(self, test_client, api_key):
        """Test that system directories are restricted."""
        # Try to access /etc
        response = test_client.post(
            "/api/directory/scan",
            json={"path": "/etc"},
            headers={"X-API-KEY": api_key}
        )
        
        # Should be blocked or have no papers
        assert response.status_code in [403, 404]
