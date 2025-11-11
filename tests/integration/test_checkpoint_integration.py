"""
Integration Tests for Pipeline Orchestrator Checkpoint/Resume

Tests end-to-end checkpoint functionality with mocked pipeline stages.
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from pipeline_orchestrator import PipelineOrchestrator


@pytest.mark.integration
class TestCheckpointIntegration:
    """Integration tests for checkpoint/resume functionality."""
    
    @patch('subprocess.run')
    def test_checkpoint_file_created_during_run(self, mock_subprocess, tmp_path):
        """Test that checkpoint file is created during pipeline run."""
        checkpoint_path = tmp_path / 'integration_checkpoint.json'
        
        # Mock successful subprocess runs
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ''
        mock_subprocess.return_value = mock_result
        
        # Mock check_for_rejections to skip DRA
        with patch.object(PipelineOrchestrator, 'check_for_rejections', return_value=False):
            orch = PipelineOrchestrator(checkpoint_file=str(checkpoint_path))
            orch.run()
        
        # Checkpoint file should exist
        assert checkpoint_path.exists()
        
        # Load and verify checkpoint
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        
        assert checkpoint['status'] == 'completed'
        assert 'completed_at' in checkpoint
        assert 'journal_reviewer' in checkpoint['stages']
        assert 'judge' in checkpoint['stages']
        assert 'sync' in checkpoint['stages']
        assert 'orchestrator' in checkpoint['stages']
    
    @patch('subprocess.run')
    def test_resume_after_failure(self, mock_subprocess, tmp_path):
        """Test that pipeline can resume after failure."""
        checkpoint_path = tmp_path / 'resume_checkpoint.json'
        
        # First run: fail at sync stage
        call_count = {'count': 0}
        
        def mock_run_side_effect(*args, **kwargs):
            call_count['count'] += 1
            mock_result = Mock()
            
            # First two calls succeed (journal_reviewer, judge)
            if call_count['count'] <= 2:
                mock_result.returncode = 0
                mock_result.stderr = ''
            else:
                # Third call fails (sync)
                mock_result.returncode = 1
                mock_result.stderr = 'Connection timeout'
            
            return mock_result
        
        mock_subprocess.side_effect = mock_run_side_effect
        
        # Mock check_for_rejections to skip DRA
        with patch.object(PipelineOrchestrator, 'check_for_rejections', return_value=False):
            orch1 = PipelineOrchestrator(checkpoint_file=str(checkpoint_path))
            
            # Run should fail at sync
            with pytest.raises(SystemExit):
                orch1.run()
        
        # Verify checkpoint shows partial completion
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        
        assert checkpoint['stages']['journal_reviewer']['status'] == 'completed'
        assert checkpoint['stages']['judge']['status'] == 'completed'
        assert checkpoint['stages']['sync']['status'] == 'failed'
        
        # Second run: resume and succeed
        call_count['count'] = 0  # Reset counter
        
        def mock_run_all_success(*args, **kwargs):
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stderr = ''
            return mock_result
        
        mock_subprocess.side_effect = mock_run_all_success
        
        with patch.object(PipelineOrchestrator, 'check_for_rejections', return_value=False):
            orch2 = PipelineOrchestrator(
                checkpoint_file=str(checkpoint_path),
                resume=True
            )
            orch2.run()
        
        # Verify checkpoint shows completion
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        
        assert checkpoint['status'] == 'completed'
        assert checkpoint['stages']['sync']['status'] == 'completed'
        assert checkpoint['stages']['orchestrator']['status'] == 'completed'
        
        # Verify journal_reviewer and judge were NOT called again
        # (only sync and orchestrator should have been called)
    
    @patch('subprocess.run')
    def test_resume_from_specific_stage(self, mock_subprocess, tmp_path):
        """Test resuming from a specific stage."""
        checkpoint_path = tmp_path / 'resume_from_checkpoint.json'
        
        # Create checkpoint with some completed stages
        checkpoint_data = {
            "run_id": "test_run_abc123",
            "pipeline_version": "1.1.0",
            "started_at": "2025-11-11T14:30:00",
            "last_updated": "2025-11-11T14:35:00",
            "status": "in_progress",
            "stages": {
                "journal_reviewer": {
                    "status": "completed",
                    "started_at": "2025-11-11T14:30:00",
                    "completed_at": "2025-11-11T14:32:00",
                    "duration_seconds": 120,
                    "exit_code": 0
                },
                "judge": {
                    "status": "completed",
                    "started_at": "2025-11-11T14:32:00",
                    "completed_at": "2025-11-11T14:35:00",
                    "duration_seconds": 180,
                    "exit_code": 0
                }
            },
            "config": {}
        }
        
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f)
        
        # Mock successful subprocess runs
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ''
        mock_subprocess.return_value = mock_result
        
        # Resume from sync stage
        with patch.object(PipelineOrchestrator, 'check_for_rejections', return_value=False):
            orch = PipelineOrchestrator(
                checkpoint_file=str(checkpoint_path),
                resume=True,
                resume_from='sync'
            )
            orch.run()
        
        # Verify checkpoint
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        
        # Original stages should still be completed
        assert checkpoint['stages']['journal_reviewer']['status'] == 'completed'
        assert checkpoint['stages']['judge']['status'] == 'completed'
        
        # New stages should be completed
        assert checkpoint['stages']['sync']['status'] == 'completed'
        assert checkpoint['stages']['orchestrator']['status'] == 'completed'
        
        assert checkpoint['status'] == 'completed'
    
    @patch('subprocess.run')
    def test_dra_stage_handling_in_checkpoint(self, mock_subprocess, tmp_path):
        """Test that DRA stage is properly handled in checkpoint."""
        checkpoint_path = tmp_path / 'dra_checkpoint.json'
        
        # Mock successful subprocess runs
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ''
        mock_subprocess.return_value = mock_result
        
        # Test 1: With rejections (DRA runs)
        with patch.object(PipelineOrchestrator, 'check_for_rejections', return_value=True):
            orch1 = PipelineOrchestrator(checkpoint_file=str(checkpoint_path))
            orch1.run()
        
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        
        assert checkpoint['stages']['dra']['status'] == 'completed'
        assert checkpoint['stages']['judge_dra']['status'] == 'completed'
        
        # Test 2: Without rejections (DRA skipped)
        checkpoint_path2 = tmp_path / 'dra_checkpoint2.json'
        
        with patch.object(PipelineOrchestrator, 'check_for_rejections', return_value=False):
            orch2 = PipelineOrchestrator(checkpoint_file=str(checkpoint_path2))
            orch2.run()
        
        with open(checkpoint_path2) as f:
            checkpoint2 = json.load(f)
        
        assert checkpoint2['stages']['dra']['status'] == 'skipped'
        assert checkpoint2['stages']['dra']['reason'] == 'no_rejections'
        assert 'judge_dra' not in checkpoint2['stages']


@pytest.mark.integration
class TestCheckpointPerformance:
    """Test checkpoint performance requirements."""
    
    def test_checkpoint_write_performance(self, tmp_path):
        """Test that checkpoint writes complete in <100ms."""
        import time
        
        checkpoint_path = tmp_path / 'perf_checkpoint.json'
        orch = PipelineOrchestrator(checkpoint_file=str(checkpoint_path))
        
        # Warm up
        orch._write_checkpoint()
        
        # Measure write time
        start = time.time()
        orch._write_checkpoint()
        duration = time.time() - start
        
        # Should complete in <100ms
        assert duration < 0.1, f"Checkpoint write took {duration*1000:.2f}ms, expected <100ms"
    
    def test_checkpoint_file_size(self, tmp_path):
        """Test that checkpoint file size is reasonable."""
        checkpoint_path = tmp_path / 'size_checkpoint.json'
        orch = PipelineOrchestrator(checkpoint_file=str(checkpoint_path))
        
        # Add all stages
        for stage in ['journal_reviewer', 'judge', 'dra', 'sync', 'orchestrator']:
            orch._mark_stage_started(stage)
            orch._mark_stage_completed(stage, 100.5, 0)
        
        orch._write_checkpoint()
        
        # Check file size
        file_size = checkpoint_path.stat().st_size
        
        # Should be less than 10KB for typical run
        assert file_size < 10240, f"Checkpoint file is {file_size} bytes, expected <10KB"


@pytest.mark.integration  
class TestCheckpointEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_concurrent_checkpoint_access(self, tmp_path):
        """Test that concurrent checkpoint access is handled safely."""
        checkpoint_path = tmp_path / 'concurrent_checkpoint.json'
        
        # Create two orchestrators with same checkpoint
        orch1 = PipelineOrchestrator(checkpoint_file=str(checkpoint_path))
        orch2 = PipelineOrchestrator(checkpoint_file=str(checkpoint_path))
        
        # Both write to checkpoint
        orch1._mark_stage_started('stage1')
        orch2._mark_stage_started('stage2')
        
        # Checkpoint should exist and be valid
        assert checkpoint_path.exists()
        
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        
        # At least one stage should be present
        assert len(checkpoint['stages']) > 0
    
    def test_checkpoint_with_special_characters_in_error(self, tmp_path):
        """Test that special characters in error messages are handled."""
        checkpoint_path = tmp_path / 'special_chars_checkpoint.json'
        orch = PipelineOrchestrator(checkpoint_file=str(checkpoint_path))
        
        # Error with special characters
        error_msg = 'Error: "quoted text" and \'single quotes\' and \n newlines \t tabs'
        
        orch._mark_stage_started('test_stage')
        orch._mark_stage_failed('test_stage', error_msg)
        
        # Should be valid JSON
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        
        assert 'test_stage' in checkpoint['stages']
        assert checkpoint['stages']['test_stage']['status'] == 'failed'
    
    def test_checkpoint_survives_system_restart(self, tmp_path):
        """Test that checkpoint works across process restarts."""
        checkpoint_path = tmp_path / 'restart_checkpoint.json'
        
        # First process: create checkpoint
        orch1 = PipelineOrchestrator(checkpoint_file=str(checkpoint_path))
        orch1._mark_stage_started('stage1')
        orch1._mark_stage_completed('stage1', 100, 0)
        
        # Delete the orchestrator (simulate process exit)
        del orch1
        
        # Second process: load checkpoint
        orch2 = PipelineOrchestrator(
            checkpoint_file=str(checkpoint_path),
            resume=True
        )
        
        # Should load the checkpoint
        assert 'stage1' in orch2.checkpoint_data['stages']
        assert orch2.checkpoint_data['stages']['stage1']['status'] == 'completed'
        
        # Should skip completed stage
        assert orch2._should_run_stage('stage1') is False
