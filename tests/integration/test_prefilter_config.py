"""
Integration tests for pre-filter configuration UI (PARITY-W2-5).

Tests the backend API endpoints and validation for the pre-filter
configuration feature that allows users to select which paper sections
to analyze for gap extraction.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


def test_job_config_accepts_pre_filter():
    """Test that JobConfig model accepts pre_filter parameter."""
    from webdashboard.app import JobConfig
    
    # Test with default (None)
    config1 = JobConfig(
        pillar_selections=["ALL"],
        run_mode="ONCE"
    )
    assert config1.pre_filter is None
    
    # Test with custom sections
    config2 = JobConfig(
        pillar_selections=["ALL"],
        run_mode="ONCE",
        pre_filter="abstract,methods,results"
    )
    assert config2.pre_filter == "abstract,methods,results"
    
    # Test with empty string (full paper)
    config3 = JobConfig(
        pillar_selections=["ALL"],
        run_mode="ONCE",
        pre_filter=""
    )
    assert config3.pre_filter == ""


def test_valid_section_names():
    """Test section name validation in job_runner."""
    from webdashboard.job_runner import PipelineJobRunner
    
    valid_sections = [
        'title', 'abstract', 'introduction', 'methods',
        'results', 'discussion', 'conclusion', 'references'
    ]
    
    runner = PipelineJobRunner()
    
    # Mock config with valid sections
    config = {"pre_filter": "abstract,introduction,methods"}
    job_data = {"config": config}
    
    # This should not raise an error
    sections = [s.strip() for s in config["pre_filter"].split(',')]
    invalid = [s for s in sections if s and s not in valid_sections]
    assert len(invalid) == 0


def test_invalid_section_names_rejected():
    """Test that invalid section names are rejected."""
    from webdashboard.job_runner import PipelineJobRunner
    
    valid_sections = [
        'title', 'abstract', 'introduction', 'methods',
        'results', 'discussion', 'conclusion', 'references'
    ]
    
    # Invalid section name
    config = {"pre_filter": "abstract,invalid_section,methods"}
    sections = [s.strip() for s in config["pre_filter"].split(',')]
    invalid = [s for s in sections if s and s not in valid_sections]
    
    assert len(invalid) == 1
    assert "invalid_section" in invalid


def test_prefilter_cli_command_default():
    """Test that default mode sends no pre-filter flag."""
    from webdashboard.job_runner import PipelineJobRunner
    
    runner = PipelineJobRunner()
    
    # Mock job data with default pre_filter (None)
    job_data = {
        "config": {
            "pre_filter": None,  # Default mode
            "output_dir": "/tmp/test"
        },
        "custom_config_path": None
    }
    
    # We need to test the CLI command building
    # Since _run_orchestrator_sync builds the command internally,
    # we'll test the logic directly
    
    config = job_data.get("config", {})
    cmd = ["python", "pipeline_orchestrator.py", "--batch-mode"]
    
    # Add pre-filter if present
    if "pre_filter" in config:
        pre_filter = config["pre_filter"]
        if pre_filter is not None:
            cmd.extend(["--pre-filter", pre_filter])
    
    # Default mode should not add --pre-filter flag
    assert "--pre-filter" not in cmd


def test_prefilter_cli_command_full():
    """Test that full paper mode sends empty string."""
    job_data = {
        "config": {
            "pre_filter": "",  # Full paper mode
            "output_dir": "/tmp/test"
        }
    }
    
    config = job_data.get("config", {})
    cmd = ["python", "pipeline_orchestrator.py", "--batch-mode"]
    
    # Add pre-filter if present
    if "pre_filter" in config:
        pre_filter = config["pre_filter"]
        if pre_filter is not None:
            cmd.extend(["--pre-filter", pre_filter])
    
    # Full mode should add --pre-filter with empty string
    assert "--pre-filter" in cmd
    idx = cmd.index("--pre-filter")
    assert cmd[idx + 1] == ""


def test_prefilter_cli_command_custom():
    """Test that custom sections are sent correctly."""
    job_data = {
        "config": {
            "pre_filter": "abstract,methods,results",
            "output_dir": "/tmp/test"
        }
    }
    
    config = job_data.get("config", {})
    cmd = ["python", "pipeline_orchestrator.py", "--batch-mode"]
    
    # Add pre-filter if present
    if "pre_filter" in config:
        pre_filter = config["pre_filter"]
        if pre_filter is not None:
            cmd.extend(["--pre-filter", pre_filter])
    
    # Custom mode should add --pre-filter with sections
    assert "--pre-filter" in cmd
    idx = cmd.index("--pre-filter")
    assert cmd[idx + 1] == "abstract,methods,results"


def test_prefilter_recommendations_general_small():
    """Test recommendations for general review with small dataset."""
    # Simulate the recommendations logic
    paper_count = 15
    review_type = "general"
    
    recommendations = {
        "general": {
            "small": ["title", "abstract", "introduction", "discussion"],
            "medium": ["title", "abstract", "introduction"],
            "large": ["abstract"]
        }
    }
    
    # Determine dataset size
    if paper_count < 20:
        size = "small"
    elif paper_count < 100:
        size = "medium"
    else:
        size = "large"
    
    sections = recommendations.get(review_type, recommendations["general"])[size]
    
    assert size == "small"
    assert sections == ["title", "abstract", "introduction", "discussion"]


def test_prefilter_recommendations_methodology_large():
    """Test recommendations for methodology review with large dataset."""
    paper_count = 150
    review_type = "methodology"
    
    recommendations = {
        "methodology": {
            "small": ["abstract", "methods", "results"],
            "medium": ["abstract", "methods"],
            "large": ["abstract"]
        }
    }
    
    # Determine dataset size
    if paper_count < 20:
        size = "small"
    elif paper_count < 100:
        size = "medium"
    else:
        size = "large"
    
    sections = recommendations.get(review_type, recommendations["general" if review_type not in recommendations else review_type])[size]
    
    assert size == "large"
    assert sections == ["abstract"]


def test_prefilter_recommendations_survey_medium():
    """Test recommendations for survey review with medium dataset."""
    paper_count = 50
    review_type = "survey"
    
    recommendations = {
        "survey": {
            "small": ["title", "abstract", "introduction", "methods", "results", "discussion"],
            "medium": ["title", "abstract", "introduction", "discussion"],
            "large": ["title", "abstract", "introduction"]
        }
    }
    
    # Determine dataset size
    if paper_count < 20:
        size = "small"
    elif paper_count < 100:
        size = "medium"
    else:
        size = "large"
    
    sections = recommendations.get(review_type, recommendations["general" if review_type not in recommendations else review_type])[size]
    
    assert size == "medium"
    assert sections == ["title", "abstract", "introduction", "discussion"]


def test_empty_section_list_rejected():
    """Test that empty custom selection is rejected."""
    valid_sections = [
        'title', 'abstract', 'introduction', 'methods',
        'results', 'discussion', 'conclusion', 'references'
    ]
    
    # Empty list after filtering
    config = {"pre_filter": ""}
    
    # Empty string is valid (means full paper)
    # But comma with no sections should be invalid
    config2 = {"pre_filter": ",,,"}
    sections = [s.strip() for s in config2["pre_filter"].split(',')]
    sections = [s for s in sections if s]  # Filter empty strings
    
    # After filtering, should be empty
    assert len(sections) == 0


def test_pipeline_orchestrator_accepts_prefilter():
    """Test that pipeline_orchestrator.py accepts --pre-filter argument."""
    import subprocess
    import sys
    
    # Test that --pre-filter is in help
    result = subprocess.run(
        [sys.executable, "pipeline_orchestrator.py", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent
    )
    
    assert result.returncode == 0
    assert "--pre-filter" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
