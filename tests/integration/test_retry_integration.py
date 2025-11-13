"""
Integration tests for retry and checkpoint functionality.

Tests cover:
- Retry on transient failures
- Checkpoint persistence
- Resume from checkpoint
- Retry history tracking
"""

import pytest
import json
import os
import sys
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pipeline_orchestrator import PipelineOrchestrator, RetryPolicy


class TestRetryIntegration:
    """Integration tests for retry functionality."""
    
    @pytest.mark.integration
    def test_retry_policy_initialization(self, temp_dir):
        """Test that retry policy is initialized correctly."""
        config = {
            'retry_policy': {
                'enabled': True,
                'default_max_attempts': 3
            }
        }
        
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        assert orchestrator.retry_policy is not None
        assert orchestrator.retry_policy.enabled == True
        assert orchestrator.retry_policy.default_max_attempts == 3
    
    @pytest.mark.integration
    def test_checkpoint_creation(self, temp_dir):
        """Test that checkpoint file is created."""
        config = {'retry_policy': {'enabled': True}}
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        # Write checkpoint
        orchestrator._write_checkpoint()
        
        # Verify file exists
        assert os.path.exists(checkpoint_file)
        
        # Verify content
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        assert 'run_id' in data
        assert 'pipeline_version' in data
        assert data['pipeline_version'] == '1.3.0'
        assert 'status' in data
        assert 'stages' in data
    
    @pytest.mark.integration
    def test_checkpoint_stage_tracking(self, temp_dir):
        """Test that stages are tracked in checkpoint."""
        config = {'retry_policy': {'enabled': True}}
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        # Mark stage as started
        orchestrator._mark_stage_started('test_stage')
        
        # Verify checkpoint
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        assert 'test_stage' in data['stages']
        assert data['stages']['test_stage']['status'] == 'in_progress'
        assert 'started_at' in data['stages']['test_stage']
        
        # Mark stage as completed
        orchestrator._mark_stage_completed('test_stage', 10.5, 0)
        
        # Verify checkpoint
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        assert data['stages']['test_stage']['status'] == 'completed'
        assert data['stages']['test_stage']['duration_seconds'] == 10.5
        assert data['stages']['test_stage']['exit_code'] == 0
    
    @pytest.mark.integration
    def test_checkpoint_retry_tracking(self, temp_dir):
        """Test that retry attempts are tracked in checkpoint."""
        config = {'retry_policy': {'enabled': True}}
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        # Mark stage as started
        orchestrator._mark_stage_started('test_stage')
        
        # Mark retry attempts
        orchestrator._mark_stage_retry('test_stage', 1, 'Connection timeout', 2.0)
        orchestrator._mark_stage_retry('test_stage', 2, 'Rate limit', 4.0)
        
        # Verify checkpoint
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        assert data['stages']['test_stage']['status'] == 'retrying'
        assert data['stages']['test_stage']['current_attempt'] == 2
        assert 'retry_history' in data['stages']['test_stage']
        
        retry_history = data['stages']['test_stage']['retry_history']
        assert len(retry_history) == 2
        assert retry_history[0]['attempt'] == 1
        assert 'Connection timeout' in retry_history[0]['error']
        assert retry_history[0]['next_retry_delay'] == 2.0
        assert retry_history[1]['attempt'] == 2
        assert 'Rate limit' in retry_history[1]['error']
    
    @pytest.mark.integration
    def test_checkpoint_atomic_write(self, temp_dir):
        """Test that checkpoint writes are atomic."""
        config = {'retry_policy': {'enabled': True}}
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        # Write checkpoint
        orchestrator._write_checkpoint()
        
        # Verify no temp file remains
        temp_file = f"{checkpoint_file}.tmp"
        assert not os.path.exists(temp_file)
        
        # Verify checkpoint is valid JSON
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)  # Should not raise
        
        assert data is not None
    
    @pytest.mark.integration
    def test_resume_skips_completed_stages(self, temp_dir):
        """Test that resume skips completed stages."""
        config = {'retry_policy': {'enabled': True}}
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        
        # Create checkpoint with completed stage
        checkpoint_data = {
            'run_id': 'test_run_123',
            'pipeline_version': '1.2.0',
            'started_at': '2025-11-11T10:00:00',
            'last_updated': '2025-11-11T10:05:00',
            'status': 'in_progress',
            'stages': {
                'stage1': {
                    'status': 'completed',
                    'completed_at': '2025-11-11T10:05:00'
                },
                'stage2': {
                    'status': 'not_started'
                }
            },
            'config': {}
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f)
        
        # Create orchestrator with resume
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file,
            resume=True
        )
        
        # Check which stages should run
        assert orchestrator._should_run_stage('stage1') == False  # Completed
        assert orchestrator._should_run_stage('stage2') == True   # Not started
    
    @pytest.mark.integration
    def test_resume_from_specific_stage(self, temp_dir):
        """Test resume from specific stage."""
        config = {'retry_policy': {'enabled': True}}
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        
        # Create checkpoint
        checkpoint_data = {
            'run_id': 'test_run_123',
            'pipeline_version': '1.2.0',
            'started_at': '2025-11-11T10:00:00',
            'last_updated': '2025-11-11T10:05:00',
            'status': 'in_progress',
            'stages': {
                'stage1': {'status': 'completed'},
                'stage2': {'status': 'completed'},
                'stage3': {'status': 'failed'}
            },
            'config': {}
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f)
        
        # Create orchestrator with resume from stage2
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file,
            resume=True,
            resume_from='stage2'
        )
        
        # stage2 and later should run
        assert orchestrator._should_run_stage('stage2') == True
        assert orchestrator._should_run_stage('stage3') == True
    
    @pytest.mark.integration
    def test_checkpoint_preserves_run_id(self, temp_dir):
        """Test that run_id is preserved when resuming."""
        config = {'retry_policy': {'enabled': True}}
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        
        # Create initial checkpoint
        checkpoint_data = {
            'run_id': 'original_run_123',
            'pipeline_version': '1.2.0',
            'started_at': '2025-11-11T10:00:00',
            'status': 'in_progress',
            'stages': {},
            'config': {}
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f)
        
        # Resume with same checkpoint
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file,
            resume=True
        )
        
        # run_id should be preserved
        assert orchestrator.run_id == 'original_run_123'
    
    @pytest.mark.integration
    def test_stage_config_override(self, temp_dir):
        """Test that per-stage config overrides defaults."""
        config = {
            'retry_policy': {
                'enabled': True,
                'default_max_attempts': 3,
                'per_stage': {
                    'special_stage': {
                        'max_attempts': 5,
                        'backoff_base': 1.5
                    }
                }
            }
        }
        
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        # Default stage
        default_config = orchestrator.retry_policy.get_stage_config('normal_stage')
        assert default_config['max_attempts'] == 3
        
        # Special stage
        special_config = orchestrator.retry_policy.get_stage_config('special_stage')
        assert special_config['max_attempts'] == 5
        assert special_config['backoff_base'] == 1.5


class TestCheckpointRobustness:
    """Tests for checkpoint robustness and error handling."""
    
    @pytest.mark.integration
    def test_missing_checkpoint_file_resume(self, temp_dir):
        """Test handling of missing checkpoint file with resume flag."""
        config = {'retry_policy': {'enabled': True}}
        checkpoint_file = os.path.join(temp_dir, 'nonexistent_checkpoint.json')
        
        # Should create new checkpoint instead of failing
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file,
            resume=True
        )
        
        # Should have created new checkpoint data
        assert orchestrator.checkpoint_data is not None
        assert orchestrator.checkpoint_data['status'] == 'in_progress'
    
    @pytest.mark.integration
    def test_invalid_checkpoint_json(self, temp_dir):
        """Test handling of corrupted checkpoint file."""
        config = {'retry_policy': {'enabled': True}}
        checkpoint_file = os.path.join(temp_dir, 'corrupted_checkpoint.json')
        
        # Create corrupted checkpoint
        with open(checkpoint_file, 'w') as f:
            f.write('{ invalid json content }')
        
        # Should handle gracefully
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file,
            resume=True
        )
        
        # Should have created new checkpoint data
        assert orchestrator.checkpoint_data is not None
        assert orchestrator.checkpoint_data['status'] == 'in_progress'
    
    @pytest.mark.integration
    def test_checkpoint_last_updated_timestamp(self, temp_dir):
        """Test that last_updated timestamp is updated."""
        config = {'retry_policy': {'enabled': True}}
        checkpoint_file = os.path.join(temp_dir, 'test_checkpoint.json')
        
        orchestrator = PipelineOrchestrator(
            config=config,
            checkpoint_file=checkpoint_file
        )
        
        # Write checkpoint
        orchestrator._write_checkpoint()
        
        # Get first timestamp
        with open(checkpoint_file, 'r') as f:
            data1 = json.load(f)
        timestamp1 = data1['last_updated']
        
        # Wait a moment and write again
        import time
        time.sleep(0.1)
        
        orchestrator._write_checkpoint()
        
        # Get second timestamp
        with open(checkpoint_file, 'r') as f:
            data2 = json.load(f)
        timestamp2 = data2['last_updated']
        
        # Timestamps should be different
        assert timestamp1 != timestamp2
