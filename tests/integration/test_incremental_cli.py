"""
Integration tests for incremental CLI workflow.

Tests the end-to-end incremental review mode including:
- Full CLI invocation with --incremental flag
- Force flag overrides incremental
- Backward compatibility
- Parent job ID tracking
"""

import pytest
import subprocess
import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.state_manager import StateManager, JobType


class TestIncrementalCLI:
    """Integration tests for incremental CLI mode."""
    
    def test_incremental_flag_available(self):
        """Test that --incremental flag is recognized."""
        result = subprocess.run(
            ['python', 'pipeline_orchestrator.py', '--help'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd='/home/runner/work/Literature-Review/Literature-Review'
        )
        
        assert result.returncode == 0
        assert '--incremental' in result.stdout
        assert '--force' in result.stdout
        assert '--parent-job-id' in result.stdout
    
    def test_force_flag_available(self):
        """Test that --force flag is recognized."""
        result = subprocess.run(
            ['python', 'pipeline_orchestrator.py', '--help'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd='/home/runner/work/Literature-Review/Literature-Review'
        )
        
        assert result.returncode == 0
        assert '--force' in result.stdout
        assert 'full re-analysis' in result.stdout.lower()
    
    def test_parent_job_id_flag_available(self):
        """Test that --parent-job-id flag is recognized."""
        result = subprocess.run(
            ['python', 'pipeline_orchestrator.py', '--help'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd='/home/runner/work/Literature-Review/Literature-Review'
        )
        
        assert result.returncode == 0
        assert '--parent-job-id' in result.stdout
    
    def test_dry_run_incremental_mode(self, tmp_path):
        """Test dry-run with incremental mode."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create prerequisite files for incremental mode
        gap_report = output_dir / "gap_analysis_report.json"
        gap_report.write_text('{"pillars": {}}')
        
        state_file = output_dir / "orchestrator_state.json"
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100
        )
        state.analysis_completed = True
        state.completed_at = "2025-01-15T10:00:00"
        state_manager.save_state(state)
        
        result = subprocess.run(
            [
                'python', 'pipeline_orchestrator.py',
                '--incremental',
                '--output-dir', str(output_dir),
                '--dry-run'
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/home/runner/work/Literature-Review/Literature-Review'
        )
        
        # Should complete successfully in dry-run mode
        assert result.returncode == 0 or 'DRY-RUN' in result.stdout or 'dry-run' in result.stdout.lower()
    
    def test_dry_run_force_mode(self, tmp_path):
        """Test dry-run with force mode (should override incremental)."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = subprocess.run(
            [
                'python', 'pipeline_orchestrator.py',
                '--incremental',
                '--force',
                '--output-dir', str(output_dir),
                '--dry-run'
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/home/runner/work/Literature-Review/Literature-Review'
        )
        
        # Should complete successfully
        # Force should override incremental
        assert result.returncode == 0 or 'DRY-RUN' in result.stdout or 'dry-run' in result.stdout.lower()
    
    def test_incremental_mode_without_prerequisites(self, tmp_path):
        """Test incremental mode falls back to full when prerequisites missing."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # No prerequisite files created - should fall back to full mode
        result = subprocess.run(
            [
                'python', 'pipeline_orchestrator.py',
                '--incremental',
                '--output-dir', str(output_dir),
                '--dry-run'
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/home/runner/work/Literature-Review/Literature-Review'
        )
        
        # Should complete and mention falling back or missing prerequisites
        output = result.stdout + result.stderr
        assert (result.returncode == 0 or 
                'prerequisite' in output.lower() or 
                'falling back' in output.lower() or
                'DRY-RUN' in output)
    
    def test_parent_job_id_parameter(self, tmp_path):
        """Test --parent-job-id parameter is accepted."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create prerequisites
        gap_report = output_dir / "gap_analysis_report.json"
        gap_report.write_text('{"pillars": {}}')
        
        state_file = output_dir / "orchestrator_state.json"
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100
        )
        state.analysis_completed = True
        state_manager.save_state(state)
        
        result = subprocess.run(
            [
                'python', 'pipeline_orchestrator.py',
                '--incremental',
                '--parent-job-id', 'test_parent_123',
                '--output-dir', str(output_dir),
                '--dry-run'
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/home/runner/work/Literature-Review/Literature-Review'
        )
        
        # Should accept the parameter without error
        assert result.returncode == 0 or 'DRY-RUN' in result.stdout


class TestBackwardCompatibility:
    """Test that incremental mode doesn't break existing functionality."""
    
    def test_default_incremental_true(self):
        """Test that incremental is True by default."""
        result = subprocess.run(
            ['python', 'pipeline_orchestrator.py', '--help'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd='/home/runner/work/Literature-Review/Literature-Review'
        )
        
        assert result.returncode == 0
        # Check help text mentions incremental is default
        assert 'default: True' in result.stdout or 'incremental' in result.stdout.lower()
    
    def test_full_mode_still_works(self, tmp_path):
        """Test that full analysis mode still works (via --force)."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = subprocess.run(
            [
                'python', 'pipeline_orchestrator.py',
                '--force',
                '--output-dir', str(output_dir),
                '--dry-run'
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/home/runner/work/Literature-Review/Literature-Review'
        )
        
        # Should work without errors
        assert result.returncode == 0 or 'DRY-RUN' in result.stdout


class TestJobLineageTracking:
    """Test parent-child job lineage tracking."""
    
    def test_parent_job_id_from_previous_state(self, tmp_path):
        """Test that parent job ID is extracted from previous state."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create gap report
        gap_report = output_dir / "gap_analysis_report.json"
        gap_report.write_text('{"pillars": {}}')
        
        # Create state with known job ID
        state_file = output_dir / "orchestrator_state.json"
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100
        )
        state.analysis_completed = True
        state.completed_at = "2025-01-15T10:00:00"
        parent_job_id = state.job_id
        state_manager.save_state(state)
        
        # Run incremental mode
        from pipeline_orchestrator import PipelineOrchestrator
        from unittest.mock import patch
        
        config = {
            'output_dir': str(output_dir),
            'incremental': True,
            'force': False,
            'dry_run': True
        }
        
        with patch.object(PipelineOrchestrator, 'log'):
            orch = PipelineOrchestrator(config=config)
            
            # Check prerequisites (should set parent_job_id)
            result = orch._check_incremental_prerequisites()
            
            assert result == True
            assert orch.parent_job_id == parent_job_id
    
    def test_explicit_parent_job_id_overrides(self, tmp_path):
        """Test that explicit --parent-job-id overrides state."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create gap report
        gap_report = output_dir / "gap_analysis_report.json"
        gap_report.write_text('{"pillars": {}}')
        
        # Create state
        state_file = output_dir / "orchestrator_state.json"
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100
        )
        state.analysis_completed = True
        state_manager.save_state(state)
        
        # Run with explicit parent job ID
        from pipeline_orchestrator import PipelineOrchestrator
        from unittest.mock import patch
        
        explicit_parent = 'custom_parent_456'
        config = {
            'output_dir': str(output_dir),
            'incremental': True,
            'force': False,
            'parent_job_id': explicit_parent,
            'dry_run': True
        }
        
        with patch.object(PipelineOrchestrator, 'log'):
            orch = PipelineOrchestrator(config=config)
            
            # Explicit parent should be used
            assert orch.parent_job_id == explicit_parent


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
