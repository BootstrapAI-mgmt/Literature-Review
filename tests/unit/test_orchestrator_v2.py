"""
Unit tests for Pipeline Orchestrator v2.0 features.

Tests cover:
- Error classification
- Quota management
- Retry helper
- Checkpoint manager v2
- Parallel coordinator
"""

import pytest
import json
import os
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from literature_review.pipeline.orchestrator_v2 import (
    ErrorType,
    ErrorClassifier,
    SimpleQuotaManager,
    RetryHelper,
    CheckpointManagerV2,
    ParallelPipelineCoordinator,
    create_v2_config_defaults,
)


class TestErrorClassifier:
    """Tests for error classification logic."""
    
    def test_classify_transient_timeout(self):
        """Test classification of timeout errors as transient."""
        error = "Connection timeout after 30 seconds"
        assert ErrorClassifier.classify_error(error) == ErrorType.TRANSIENT
        assert ErrorClassifier.should_retry(error) is True
    
    def test_classify_transient_rate_limit(self):
        """Test classification of rate limit errors as transient."""
        error = "Rate limit exceeded, too many requests"
        assert ErrorClassifier.classify_error(error) == ErrorType.TRANSIENT
        assert ErrorClassifier.should_retry(error) is True
    
    def test_classify_transient_http_429(self):
        """Test classification of HTTP 429 as transient."""
        error = "HTTP 429: Too Many Requests"
        assert ErrorClassifier.classify_error(error, http_status=429) == ErrorType.TRANSIENT
        assert ErrorClassifier.should_retry(error, http_status=429) is True
    
    def test_classify_transient_http_503(self):
        """Test classification of HTTP 503 as transient."""
        error = "Service unavailable"
        assert ErrorClassifier.classify_error(error, http_status=503) == ErrorType.TRANSIENT
        assert ErrorClassifier.should_retry(error, http_status=503) is True
    
    def test_classify_permanent_syntax_error(self):
        """Test classification of syntax errors as permanent."""
        error = "SyntaxError: invalid syntax on line 42"
        assert ErrorClassifier.classify_error(error) == ErrorType.PERMANENT
        assert ErrorClassifier.should_retry(error) is False
    
    def test_classify_permanent_file_not_found(self):
        """Test classification of file not found as permanent."""
        error = "FileNotFoundError: No such file or directory"
        assert ErrorClassifier.classify_error(error) == ErrorType.PERMANENT
        assert ErrorClassifier.should_retry(error) is False
    
    def test_classify_permanent_http_401(self):
        """Test classification of HTTP 401 as permanent."""
        error = "Unauthorized access"
        assert ErrorClassifier.classify_error(error, http_status=401) == ErrorType.PERMANENT
        assert ErrorClassifier.should_retry(error, http_status=401) is False
    
    def test_classify_permanent_http_404(self):
        """Test classification of HTTP 404 as permanent."""
        error = "Not found"
        assert ErrorClassifier.classify_error(error, http_status=404) == ErrorType.PERMANENT
        assert ErrorClassifier.should_retry(error, http_status=404) is False
    
    def test_classify_unknown_error(self):
        """Test classification of unknown errors (conservative: no retry)."""
        error = "Some unknown error occurred"
        assert ErrorClassifier.classify_error(error) == ErrorType.UNKNOWN
        assert ErrorClassifier.should_retry(error) is False
    
    def test_case_insensitive_matching(self):
        """Test that error matching is case-insensitive."""
        error1 = "TIMEOUT OCCURRED"
        error2 = "timeout occurred"
        error3 = "TimeOut Occurred"
        
        assert ErrorClassifier.classify_error(error1) == ErrorType.TRANSIENT
        assert ErrorClassifier.classify_error(error2) == ErrorType.TRANSIENT
        assert ErrorClassifier.classify_error(error3) == ErrorType.TRANSIENT


class TestSimpleQuotaManager:
    """Tests for quota management."""
    
    def test_quota_manager_initialization(self):
        """Test quota manager initializes correctly."""
        manager = SimpleQuotaManager(rate=60, per_seconds=60)
        
        assert manager.rate == 60
        assert manager.per_seconds == 60
        assert manager.allowance == 60.0
        assert manager.consumed_count == 0
        assert manager.throttle_count == 0
    
    def test_quota_consume_within_limit(self):
        """Test consuming tokens within quota limit."""
        manager = SimpleQuotaManager(rate=10, per_seconds=60)
        
        # Should succeed without waiting
        result = manager.consume(tokens=5, wait=False)
        assert result is True
        assert manager.consumed_count == 5
        assert manager.allowance == 5.0
    
    def test_quota_consume_exceeds_limit_no_wait(self):
        """Test consuming tokens that exceed quota without waiting."""
        manager = SimpleQuotaManager(rate=10, per_seconds=60)
        
        # Consume all tokens
        manager.consume(tokens=10, wait=False)
        
        # Try to consume more without waiting - should fail
        result = manager.consume(tokens=1, wait=False)
        assert result is False
        assert manager.throttle_count > 0
    
    def test_quota_refill_over_time(self):
        """Test that quota refills over time."""
        manager = SimpleQuotaManager(rate=10, per_seconds=1)  # 10 tokens per second
        
        # Consume all tokens
        manager.consume(tokens=10, wait=False)
        assert manager.allowance == 0.0
        
        # Wait for refill
        time.sleep(0.5)  # Should refill ~5 tokens
        
        # Try to consume - should have some tokens
        result = manager.consume(tokens=3, wait=False)
        assert result is True
    
    def test_quota_stats(self):
        """Test quota statistics tracking."""
        manager = SimpleQuotaManager(rate=100, per_seconds=60)
        
        manager.consume(tokens=10, wait=False)
        manager.consume(tokens=5, wait=False)
        
        stats = manager.get_stats()
        
        assert stats['rate'] == 100
        assert stats['consumed_count'] == 15
        # Allow for small floating point drift due to time refill
        assert 84.0 < stats['current_allowance'] < 86.0
    
    def test_quota_thread_safety(self):
        """Test that quota manager is thread-safe."""
        import threading
        
        manager = SimpleQuotaManager(rate=100, per_seconds=60)
        results = []
        
        def consume_tokens():
            result = manager.consume(tokens=1, wait=False)
            results.append(result)
        
        # Create multiple threads
        threads = [threading.Thread(target=consume_tokens) for _ in range(50)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Should have consumed exactly 50 tokens (or failed some if quota exceeded)
        assert manager.consumed_count <= 50
        assert len(results) == 50


class TestRetryHelper:
    """Tests for retry helper with exponential backoff."""
    
    def test_retry_succeeds_first_attempt(self):
        """Test successful execution on first attempt."""
        call_count = [0]
        
        def func():
            call_count[0] += 1
            return "success"
        
        result = RetryHelper.retry_with_backoff(func, attempts=3)
        
        assert result == "success"
        assert call_count[0] == 1
    
    def test_retry_succeeds_after_failures(self):
        """Test successful execution after transient failures."""
        call_count = [0]
        
        def func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = RetryHelper.retry_with_backoff(func, attempts=3)
        
        assert result == "success"
        assert call_count[0] == 3
    
    def test_retry_all_attempts_fail(self):
        """Test that exception is raised after all attempts fail."""
        def func():
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            RetryHelper.retry_with_backoff(func, attempts=3)
    
    def test_retry_exponential_backoff(self):
        """Test exponential backoff delays."""
        call_times = []
        
        def func():
            call_times.append(time.time())
            raise Exception("Fail")
        
        with pytest.raises(Exception):
            RetryHelper.retry_with_backoff(
                func,
                attempts=3,
                base=0.1,
                factor=2.0,
                jitter=False
            )
        
        # Check timing between attempts
        assert len(call_times) == 3
        
        # First retry delay should be ~0.1 seconds
        delay1 = call_times[1] - call_times[0]
        assert 0.08 < delay1 < 0.15
        
        # Second retry delay should be ~0.2 seconds
        delay2 = call_times[2] - call_times[1]
        assert 0.18 < delay2 < 0.25
    
    def test_retry_with_error_classifier(self):
        """Test retry with smart error classification."""
        call_count = [0]
        
        def func():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("File not found")  # Permanent error
            return "success"
        
        # Should not retry permanent errors
        with pytest.raises(Exception, match="File not found"):
            RetryHelper.retry_with_backoff(
                func,
                attempts=3,
                error_classifier=ErrorClassifier
            )
        
        # Should only attempt once (no retry for permanent error)
        assert call_count[0] == 1
    
    def test_retry_max_delay(self):
        """Test that retry delay is capped at max_delay."""
        call_times = []
        
        def func():
            call_times.append(time.time())
            raise Exception("Fail")
        
        with pytest.raises(Exception):
            RetryHelper.retry_with_backoff(
                func,
                attempts=4,
                base=10.0,
                factor=10.0,
                max_delay=0.5,
                jitter=False
            )
        
        # All delays should be capped at max_delay
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i-1]
            assert delay <= 0.6  # 0.5 + small margin


class TestCheckpointManagerV2:
    """Tests for checkpoint manager v2."""
    
    @pytest.fixture
    def temp_checkpoint(self):
        """Create temporary checkpoint file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            checkpoint_file = f.name
        yield checkpoint_file
        # Cleanup
        if os.path.exists(checkpoint_file):
            os.unlink(checkpoint_file)
        tmp_file = checkpoint_file + '.tmp'
        if os.path.exists(tmp_file):
            os.unlink(tmp_file)
    
    def test_checkpoint_initialization(self, temp_checkpoint):
        """Test checkpoint manager initialization."""
        manager = CheckpointManagerV2(temp_checkpoint)
        
        assert manager.checkpoint_file == temp_checkpoint
        assert manager.dry_run is False
        assert 'run_id' in manager.data
        assert manager.data['version'] == '2.0.0'
        assert manager.data['papers'] == {}
    
    def test_checkpoint_save_and_load(self, temp_checkpoint):
        """Test saving and loading checkpoint."""
        manager = CheckpointManagerV2(temp_checkpoint)
        
        # Add some data
        manager.update_paper_status('paper1', 'in_progress')
        
        # Create new manager and load
        manager2 = CheckpointManagerV2(temp_checkpoint)
        loaded = manager2.load()
        
        assert loaded is True
        assert 'paper1' in manager2.data['papers']
        assert manager2.data['papers']['paper1']['stage'] == 'in_progress'
    
    def test_checkpoint_atomic_write(self, temp_checkpoint):
        """Test atomic write of checkpoint."""
        manager = CheckpointManagerV2(temp_checkpoint)
        manager.save()
        
        # Verify checkpoint file exists
        assert os.path.exists(temp_checkpoint)
        
        # Verify no temp file remains
        tmp_file = temp_checkpoint + '.tmp'
        assert not os.path.exists(tmp_file)
        
        # Verify valid JSON
        with open(temp_checkpoint, 'r') as f:
            data = json.load(f)
        assert data is not None
    
    def test_checkpoint_paper_status_tracking(self, temp_checkpoint):
        """Test tracking paper status through pipeline stages."""
        manager = CheckpointManagerV2(temp_checkpoint)
        
        # Start paper
        manager.update_paper_status('paper1', 'in_progress')
        
        # Complete stages
        manager.update_paper_status(
            'paper1',
            'in_progress',
            stages_completed=['journal_reviewer', 'judge']
        )
        
        # Complete paper
        manager.update_paper_status('paper1', 'completed')
        
        # Verify
        status = manager.get_paper_status('paper1')
        assert status is not None
        assert status['stage'] == 'completed'
        assert 'journal_reviewer' in status['stages']
        assert 'judge' in status['stages']
        assert status['started_at'] is not None
        assert status['completed_at'] is not None
    
    def test_checkpoint_error_tracking(self, temp_checkpoint):
        """Test tracking errors for papers."""
        manager = CheckpointManagerV2(temp_checkpoint)
        
        manager.update_paper_status(
            'paper1',
            'failed',
            error='Connection timeout'
        )
        
        status = manager.get_paper_status('paper1')
        assert status['last_error'] == 'Connection timeout'
        assert 'errors' in status
        assert len(status['errors']) == 1
        assert 'Connection timeout' in status['errors'][0]['message']
    
    def test_checkpoint_retry_counting(self, temp_checkpoint):
        """Test retry count tracking."""
        manager = CheckpointManagerV2(temp_checkpoint)
        
        manager.update_paper_status('paper1', 'in_progress')
        manager.increment_retries('paper1')
        manager.increment_retries('paper1')
        
        status = manager.get_paper_status('paper1')
        assert status['retries'] == 2
        assert manager.data['stats']['retries'] == 2
    
    def test_checkpoint_stats(self, temp_checkpoint):
        """Test checkpoint statistics."""
        manager = CheckpointManagerV2(temp_checkpoint)
        
        manager.update_paper_status('paper1', 'completed')
        manager.update_paper_status('paper2', 'failed')
        manager.update_paper_status('paper3', 'in_progress')
        
        stats = manager.data['stats']
        assert stats['completed_papers'] == 1
        assert stats['failed_papers'] == 1
    
    def test_checkpoint_get_incomplete_papers(self, temp_checkpoint):
        """Test getting list of incomplete papers."""
        manager = CheckpointManagerV2(temp_checkpoint)
        
        manager.update_paper_status('paper1', 'completed')
        manager.update_paper_status('paper2', 'in_progress')
        manager.update_paper_status('paper3', 'not_started')
        manager.update_paper_status('paper4', 'failed')
        
        incomplete = manager.get_incomplete_papers()
        
        assert 'paper2' in incomplete
        assert 'paper3' in incomplete
        assert 'paper1' not in incomplete
        assert 'paper4' not in incomplete
    
    def test_checkpoint_dry_run(self, temp_checkpoint):
        """Test dry-run mode doesn't write files."""
        # Remove the temp file first if it exists
        if os.path.exists(temp_checkpoint):
            os.unlink(temp_checkpoint)
        
        manager = CheckpointManagerV2(temp_checkpoint, dry_run=True)
        
        manager.update_paper_status('paper1', 'in_progress')
        
        # File should not exist in dry-run mode
        # Note: The temp file is created by the fixture but shouldn't be written by manager
        # We need to check the manager didn't write to it after initialization
        
        # Load the checkpoint - it should not have been updated
        manager2 = CheckpointManagerV2(temp_checkpoint, dry_run=False)
        loaded = manager2.load()
        
        # Either file doesn't exist (preferred) or it doesn't contain paper1
        if loaded:
            assert 'paper1' not in manager2.data.get('papers', {})


class TestParallelPipelineCoordinator:
    """Tests for parallel pipeline coordinator."""
    
    def test_coordinator_initialization(self):
        """Test coordinator initialization."""
        coordinator = ParallelPipelineCoordinator(max_workers=4)
        
        assert coordinator.max_workers == 4
        assert coordinator.quota_manager is None
        assert coordinator.checkpoint is None
        assert coordinator.dry_run is False
    
    def test_process_papers_sequential(self):
        """Test processing papers (simulated parallel)."""
        def process_func(paper):
            return {
                'paper': paper,
                'status': 'success',
                'result': f'Processed {paper}'
            }
        
        coordinator = ParallelPipelineCoordinator(max_workers=2)
        papers = ['paper1', 'paper2', 'paper3']
        
        results = coordinator.process_papers_parallel(papers, process_func)
        
        assert len(results) == 3
        assert coordinator.stats['successful'] == 3
        assert coordinator.stats['failed'] == 0
    
    def test_process_papers_with_failures(self):
        """Test processing papers with some failures."""
        def process_func(paper):
            if paper == 'paper2':
                raise Exception("Processing failed")
            return {
                'paper': paper,
                'status': 'success'
            }
        
        coordinator = ParallelPipelineCoordinator(max_workers=2)
        papers = ['paper1', 'paper2', 'paper3']
        
        results = coordinator.process_papers_parallel(papers, process_func)
        
        assert len(results) == 3
        assert coordinator.stats['successful'] == 2
        assert coordinator.stats['failed'] == 1
    
    def test_process_papers_with_quota(self):
        """Test processing with quota management."""
        quota = SimpleQuotaManager(rate=10, per_seconds=60)
        coordinator = ParallelPipelineCoordinator(
            max_workers=2,
            quota_manager=quota
        )
        
        def process_func(paper):
            return {'paper': paper, 'status': 'success'}
        
        papers = ['paper1', 'paper2', 'paper3']
        results = coordinator.process_papers_parallel(papers, process_func)
        
        assert len(results) == 3
        # Quota should have consumed 3 tokens
        assert quota.consumed_count == 3
    
    def test_process_papers_dry_run(self):
        """Test dry-run mode."""
        coordinator = ParallelPipelineCoordinator(max_workers=2, dry_run=True)
        
        def process_func(paper):
            raise Exception("Should not be called in dry-run")
        
        papers = ['paper1', 'paper2']
        results = coordinator.process_papers_parallel(papers, process_func)
        
        # Should complete without calling process_func
        assert len(results) == 2
        for result in results:
            assert result.get('dry_run') is True
    
    def test_get_stats(self):
        """Test getting coordinator statistics."""
        coordinator = ParallelPipelineCoordinator(max_workers=2)
        
        def process_func(paper):
            return {'paper': paper, 'status': 'success'}
        
        papers = ['paper1', 'paper2']
        coordinator.process_papers_parallel(papers, process_func)
        
        stats = coordinator.get_stats()
        
        assert stats['total_processed'] == 2
        assert stats['successful'] == 2
        assert stats['failed'] == 0


class TestV2ConfigDefaults:
    """Tests for v2.0 configuration defaults."""
    
    def test_create_defaults(self):
        """Test creating default v2.0 configuration."""
        config = create_v2_config_defaults()
        
        assert config['max_workers'] == 4
        assert config['enable_parallel'] is False
        assert 'retry' in config
        assert 'quota' in config
        assert 'feature_flags' in config
        
        # Verify retry defaults
        assert config['retry']['attempts'] == 3
        assert config['retry']['base'] == 0.5
        assert config['retry']['factor'] == 2.0
        
        # Verify feature flags
        assert config['feature_flags']['enable_parallel_processing'] is False
        assert config['feature_flags']['enable_quota_management'] is True
