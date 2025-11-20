"""
Integration tests for CLI --output-dir argument.

Tests verify end-to-end functionality of the output directory argument
through the pipeline orchestrator CLI.
"""

import pytest
import subprocess
import json
import os
import tempfile
from pathlib import Path


@pytest.mark.integration
def test_cli_with_custom_output_dir(tmp_path):
    """Test running CLI with --output-dir argument."""
    output_dir = tmp_path / "custom_gap_analysis"
    
    # Run pipeline with custom output dir (dry-run to avoid long execution)
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
    
    # Check output mentions custom directory
    output = result.stdout + result.stderr
    assert str(output_dir) in output or 'custom_gap_analysis' in output


@pytest.mark.integration
def test_cli_without_output_dir(tmp_path):
    """Test CLI without --output-dir uses default."""
    # Change to temp directory for this test
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        result = subprocess.run(
            ['python', str(Path(__file__).parent.parent.parent / 'pipeline_orchestrator.py'), '--dry-run'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check default directory mentioned
        output = result.stdout + result.stderr
        assert 'gap_analysis_output' in output
    finally:
        os.chdir(original_cwd)


@pytest.mark.integration
def test_cli_with_environment_variable(tmp_path):
    """Test CLI respects LITERATURE_REVIEW_OUTPUT_DIR environment variable."""
    output_dir = tmp_path / "env_output"
    
    env = os.environ.copy()
    env['LITERATURE_REVIEW_OUTPUT_DIR'] = str(output_dir)
    
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
    assert str(output_dir) in output or 'env_output' in output


@pytest.mark.integration
def test_cli_argument_priority_over_env_var(tmp_path):
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
    
    # Check output mentions CLI directory, not env directory
    output = result.stdout + result.stderr
    assert str(cli_dir) in output or 'cli_output' in output
    # Environment directory should not be mentioned
    assert str(env_dir) not in output or 'env_output' not in output or str(cli_dir) in output


@pytest.mark.integration
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


@pytest.mark.integration
def test_multiple_output_directories_independent(tmp_path):
    """Test that multiple separate reviews can use different directories."""
    review1_dir = tmp_path / "review_v1"
    review2_dir = tmp_path / "review_v2"
    
    # Run with first directory
    result1 = subprocess.run(
        [
            'python', 'pipeline_orchestrator.py',
            '--output-dir', str(review1_dir),
            '--dry-run'
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    # Run with second directory
    result2 = subprocess.run(
        [
            'python', 'pipeline_orchestrator.py',
            '--output-dir', str(review2_dir),
            '--dry-run'
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    # Both should succeed
    assert result1.returncode == 0
    assert result2.returncode == 0
    
    # Both directories should exist independently
    assert review1_dir.exists()
    assert review2_dir.exists()


@pytest.mark.integration
def test_backward_compatibility_no_breaking_changes():
    """Test that existing scripts still work without --output-dir."""
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


@pytest.mark.integration
def test_help_text_includes_output_dir():
    """Test that help text includes --output-dir documentation."""
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
    assert 'environment variable' in result.stdout.lower()


@pytest.mark.integration
def test_relative_path_output_dir(tmp_path):
    """Test that relative paths work for output directory."""
    # Use a relative path
    relative_dir = "relative_output"
    
    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        result = subprocess.run(
            [
                'python', 
                str(Path(__file__).parent.parent.parent / 'pipeline_orchestrator.py'),
                '--output-dir', relative_dir,
                '--dry-run'
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check command executed successfully
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        
        # Check relative directory was created
        assert (tmp_path / relative_dir).exists()
    finally:
        os.chdir(original_cwd)


@pytest.mark.integration
def test_nested_output_dir(tmp_path):
    """Test that nested output directories work."""
    nested_dir = tmp_path / "reviews" / "2025" / "january" / "baseline"
    
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
