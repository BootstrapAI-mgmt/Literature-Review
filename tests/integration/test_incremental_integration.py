"""
Integration test for incremental analysis feature.

Tests the integration between IncrementalAnalyzer and PipelineOrchestrator.
"""

import pytest
import tempfile
import os
import json
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestIncrementalAnalysisIntegration:
    """Test incremental analysis integration with pipeline orchestrator."""
    
    def test_orchestrator_cli_help(self):
        """Test that orchestrator CLI includes incremental flags."""
        result = subprocess.run(
            [sys.executable, 'pipeline_orchestrator.py', '--help'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        
        assert result.returncode == 0
        assert '--incremental' in result.stdout
        assert '--force' in result.stdout
        assert '--clear-cache' in result.stdout
    
    def test_dry_run_with_no_changes(self):
        """Test dry-run mode with no changes exits early."""
        result = subprocess.run(
            [sys.executable, 'pipeline_orchestrator.py', '--dry-run', '--incremental'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            timeout=30
        )
        
        assert result.returncode == 0
        assert 'No changes detected' in result.stdout or 'No changes detected' in result.stderr
    
    def test_dry_run_with_force(self):
        """Test dry-run mode with force runs all stages."""
        result = subprocess.run(
            [sys.executable, 'pipeline_orchestrator.py', '--dry-run', '--force'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            timeout=30
        )
        
        assert result.returncode == 0
        # Should run stages
        output = result.stdout + result.stderr
        assert 'Stage 1: Initial Paper Review' in output or 'Full analysis mode' in output
    
    def test_clear_cache_flag(self):
        """Test --clear-cache flag works."""
        result = subprocess.run(
            [sys.executable, 'pipeline_orchestrator.py', '--clear-cache', '--dry-run'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            timeout=30
        )
        
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert 'cache cleared' in output.lower() or 'cleared' in output.lower()
    
    def test_incremental_status_script(self):
        """Test incremental status script runs without errors."""
        result = subprocess.run(
            [sys.executable, 'scripts/incremental_status.py'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            timeout=30
        )
        
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert 'INCREMENTAL ANALYSIS STATUS' in output
        assert 'Cache Statistics' in output
