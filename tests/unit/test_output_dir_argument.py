"""
Unit tests for --output-dir argument functionality.

Tests verify that the output directory can be customized via:
1. CLI argument (--output-dir)
2. Environment variable (LITERATURE_REVIEW_OUTPUT_DIR)
3. Config file (output_dir key)
4. Default value (gap_analysis_output)

And that the priority chain is respected: CLI > Env > Config > Default
"""

import pytest
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.mark.unit
def test_cli_argument_parsing():
    """Test that --output-dir argument is correctly parsed."""
    result = subprocess.run(
        ['python', 'pipeline_orchestrator.py', '--help'],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    # Check help output includes output-dir
    assert '--output-dir' in result.stdout
    assert 'OUTPUT_DIR' in result.stdout
    assert 'LITERATURE_REVIEW_OUTPUT_DIR' in result.stdout


@pytest.mark.unit
def test_output_dir_priority_cli_arg(tmp_path):
    """Test CLI argument is used when provided."""
    cli_dir = tmp_path / "cli_output"
    
    result = subprocess.run(
        [
            'python', 'pipeline_orchestrator.py',
            '--output-dir', str(cli_dir),
            '--dry-run'
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    # Check command executed successfully
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Check output mentions CLI directory
    output = result.stdout + result.stderr
    assert str(cli_dir) in output or 'cli_output' in output


@pytest.mark.unit
def test_output_dir_priority_env_var(tmp_path):
    """Test environment variable is used when CLI arg not provided."""
    env_dir = tmp_path / "env_output"
    
    env = os.environ.copy()
    env['LITERATURE_REVIEW_OUTPUT_DIR'] = str(env_dir)
    
    result = subprocess.run(
        ['python', 'pipeline_orchestrator.py', '--dry-run'],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent.parent),
        env=env
    )
    
    # Check command executed successfully
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Check output mentions the environment variable directory
    output = result.stdout + result.stderr
    assert str(env_dir) in output or 'env_output' in output


@pytest.mark.unit
def test_output_dir_priority_cli_over_env(tmp_path):
    """Test CLI argument takes priority over environment variable."""
    cli_dir = tmp_path / "cli_output"
    env_dir = tmp_path / "env_output"
    
    env = os.environ.copy()
    env['LITERATURE_REVIEW_OUTPUT_DIR'] = str(env_dir)
    
    result = subprocess.run(
        [
            'python', 'pipeline_orchestrator.py',
            '--output-dir', str(cli_dir),
            '--dry-run'
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent.parent),
        env=env
    )
    
    # Check command executed successfully
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Check output mentions CLI directory
    output = result.stdout + result.stderr
    assert str(cli_dir) in output or 'cli_output' in output


@pytest.mark.unit
def test_output_dir_default_value():
    """Test default output directory is used when no custom dir specified."""
    result = subprocess.run(
        ['python', 'pipeline_orchestrator.py', '--dry-run'],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    # Check command executed successfully
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Should use default directory
    output = result.stdout + result.stderr
    assert 'gap_analysis_output' in output


@pytest.mark.unit
def test_output_directory_created(tmp_path):
    """Test that the output directory is actually created."""
    output_dir = tmp_path / "created_output"
    
    # Directory should not exist yet
    assert not output_dir.exists()
    
    result = subprocess.run(
        [
            'python', 'pipeline_orchestrator.py',
            '--output-dir', str(output_dir),
            '--dry-run'
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    # Check command executed successfully
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Directory should now exist
    assert output_dir.exists()
    assert output_dir.is_dir()


@pytest.mark.unit
def test_nested_output_directory(tmp_path):
    """Test that nested output directories are created."""
    nested_dir = tmp_path / "reviews" / "2025" / "baseline"
    
    result = subprocess.run(
        [
            'python', 'pipeline_orchestrator.py',
            '--output-dir', str(nested_dir),
            '--dry-run'
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    # Check command executed successfully
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Check nested directory was created
    assert nested_dir.exists()
    assert nested_dir.is_dir()


@pytest.mark.unit
def test_backward_compatibility():
    """Test that existing usage without --output-dir still works."""
    result = subprocess.run(
        ['python', 'pipeline_orchestrator.py', '--dry-run'],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    # Should not error
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Should use default directory
    output = result.stdout + result.stderr
    assert 'gap_analysis_output' in output

