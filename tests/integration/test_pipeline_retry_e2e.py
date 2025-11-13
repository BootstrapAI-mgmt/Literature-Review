"""
End-to-end test for pipeline orchestrator with retry logic.

Tests the full integration of retry, checkpointing, and pipeline execution.
"""

import pytest
import json
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pipeline_orchestrator import PipelineOrchestrator


class TestPipelineRetryE2E:
    """End-to-end tests for pipeline with retry logic."""
    
    @pytest.mark.integration
    def test_successful_stage_no_retry(self, temp_dir):
        """Test successful stage execution without retry."""
        config = {
            'retry_policy': {
                'enabled': True,
                'default_max_attempts': 3
            },
            'stage_timeout': 10
        }
        
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        # Run successful stage
        script_path = 'tests/mock_scripts/success_script.py'
        result = orchestrator.run_stage(
            'test_success',
            script_path,
            'Test Success Stage'
        )
        
        assert result == True
        
        # Verify checkpoint
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        assert data['stages']['test_success']['status'] == 'completed'
        assert data['stages']['test_success']['exit_code'] == 0
        assert 'retry_history' not in data['stages']['test_success']
    
    @pytest.mark.integration
    def test_permanent_error_no_retry(self, temp_dir):
        """Test that permanent errors are not retried."""
        config = {
            'retry_policy': {
                'enabled': True,
                'default_max_attempts': 3
            },
            'stage_timeout': 10
        }
        
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        # Run stage with permanent error (required=False to not exit)
        script_path = 'tests/mock_scripts/permanent_error_script.py'
        result = orchestrator.run_stage(
            'test_permanent',
            script_path,
            'Test Permanent Error Stage',
            required=False
        )
        
        assert result == False
        
        # Verify checkpoint - should fail without retry
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        assert data['stages']['test_permanent']['status'] == 'failed'
        # Should not have retry history for permanent error
        assert 'retry_history' not in data['stages']['test_permanent'] or \
               len(data['stages']['test_permanent'].get('retry_history', [])) == 0
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_flaky_stage_with_retry(self, temp_dir):
        """Test flaky stage with retry (may succeed eventually)."""
        config = {
            'retry_policy': {
                'enabled': True,
                'default_max_attempts': 5,
                'default_backoff_base': 1.1,  # Small for faster test
                'default_backoff_max': 2
            },
            'stage_timeout': 10
        }
        
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        # Run flaky stage (may fail/succeed randomly)
        script_path = 'tests/mock_scripts/flaky_script.py'
        
        # Note: This test may succeed or fail depending on random chance
        # We mainly want to verify the retry mechanism works
        result = orchestrator.run_stage(
            'test_flaky',
            script_path,
            'Test Flaky Stage',
            required=False
        )
        
        # Verify checkpoint was created
        assert os.path.exists(checkpoint_file)
        
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        # Stage should be either completed or failed
        assert data['stages']['test_flaky']['status'] in ['completed', 'failed']
        
        # If failed, should have retry history
        if data['stages']['test_flaky']['status'] == 'failed':
            assert 'retry_history' in data['stages']['test_flaky']
            # Should have attempted retries
            assert len(data['stages']['test_flaky']['retry_history']) > 0
    
    @pytest.mark.integration
    def test_checkpoint_resume(self, temp_dir):
        """Test resuming from checkpoint."""
        config = {
            'retry_policy': {'enabled': True},
            'stage_timeout': 10
        }
        
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        
        # First run - complete one stage
        orchestrator1 = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        script_path = 'tests/mock_scripts/success_script.py'
        orchestrator1.run_stage('stage1', script_path, 'Stage 1')
        
        # Verify stage1 completed
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        assert data['stages']['stage1']['status'] == 'completed'
        
        # Second run - resume and run stage2
        orchestrator2 = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file,
            resume=True
        )
        
        # stage1 should be skipped
        assert orchestrator2._should_run_stage('stage1') == False
        
        # stage2 should run
        orchestrator2.run_stage('stage2', script_path, 'Stage 2')
        
        # Verify both stages in checkpoint
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        assert data['stages']['stage1']['status'] == 'completed'
        assert data['stages']['stage2']['status'] == 'completed'
    
    @pytest.mark.integration
    def test_retry_with_backoff(self, temp_dir):
        """Test that retry uses exponential backoff."""
        config = {
            'retry_policy': {
                'enabled': True,
                'default_max_attempts': 3,
                'default_backoff_base': 1.5,
                'default_backoff_max': 10
            },
            'stage_timeout': 10
        }
        
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        # Calculate expected delays
        retry_policy = orchestrator.retry_policy
        
        # First retry: 1.5^0 = 1s (+ jitter)
        delay1 = retry_policy.calculate_backoff(1, 'test_stage')
        assert 0.8 <= delay1 <= 1.2
        
        # Second retry: 1.5^1 = 1.5s (+ jitter)
        delay2 = retry_policy.calculate_backoff(2, 'test_stage')
        assert 1.2 <= delay2 <= 1.8
        
        # Third retry: 1.5^2 = 2.25s (+ jitter)
        delay3 = retry_policy.calculate_backoff(3, 'test_stage')
        assert 1.8 <= delay3 <= 2.7
