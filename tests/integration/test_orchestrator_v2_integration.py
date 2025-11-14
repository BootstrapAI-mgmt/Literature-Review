"""
Integration tests for Pipeline Orchestrator v2.0 features.

Tests cover:
- End-to-end checkpoint/resume with per-paper tracking
- Quota management during pipeline execution
- Parallel processing coordination
- Dry-run mode validation
- Retry with smart error classification
"""

import pytest
import json
import os
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from literature_review.pipeline.orchestrator_v2 import (
    ErrorClassifier,
    SimpleQuotaManager,
    CheckpointManagerV2,
    ParallelPipelineCoordinator,
    RetryHelper,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.mark.integration
class TestCheckpointIntegrationV2:
    """Integration tests for checkpoint v2 functionality."""
    
    def test_checkpoint_full_pipeline_simulation(self, temp_dir):
        """Test checkpoint through simulated pipeline execution."""
        checkpoint_file = os.path.join(temp_dir, 'checkpoint.json')
        checkpoint = CheckpointManagerV2(checkpoint_file)
        
        # Simulate processing multiple papers through pipeline stages
        papers = ['paper1.pdf', 'paper2.pdf', 'paper3.pdf']
        stages = ['journal_reviewer', 'judge', 'sync']
        
        # Process paper1 completely
        for stage in stages:
            checkpoint.update_paper_status(
                'paper1.pdf',
                'in_progress',
                stages_completed=[stage]
            )
            time.sleep(0.01)  # Simulate processing
        checkpoint.update_paper_status('paper1.pdf', 'completed')
        
        # Process paper2 partially (fail at judge)
        checkpoint.update_paper_status(
            'paper2.pdf',
            'in_progress',
            stages_completed=['journal_reviewer']
        )
        checkpoint.update_paper_status(
            'paper2.pdf',
            'failed',
            error='API timeout during judge stage'
        )
        
        # Process paper3 - in progress
        checkpoint.update_paper_status(
            'paper3.pdf',
            'in_progress',
            stages_completed=['journal_reviewer', 'judge']
        )
        
        # Verify checkpoint state
        assert checkpoint.data['stats']['completed_papers'] == 1
        assert checkpoint.data['stats']['failed_papers'] == 1
        
        # Verify we can load and resume
        checkpoint2 = CheckpointManagerV2(checkpoint_file)
        checkpoint2.load()
        
        incomplete = checkpoint2.get_incomplete_papers()
        assert 'paper3.pdf' in incomplete
        assert 'paper1.pdf' not in incomplete
        assert 'paper2.pdf' not in incomplete
        
        # Verify paper status details
        paper1_status = checkpoint2.get_paper_status('paper1.pdf')
        assert paper1_status['stage'] == 'completed'
        assert len(paper1_status['stages']) == 3
        assert 'journal_reviewer' in paper1_status['stages']
        
        paper2_status = checkpoint2.get_paper_status('paper2.pdf')
        assert paper2_status['stage'] == 'failed'
        assert 'API timeout' in paper2_status['last_error']
    
    def test_checkpoint_resume_after_interruption(self, temp_dir):
        """Test resuming from checkpoint after interruption."""
        checkpoint_file = os.path.join(temp_dir, 'checkpoint.json')
        
        # First run - process some papers
        checkpoint1 = CheckpointManagerV2(checkpoint_file)
        checkpoint1.update_paper_status('paper1.pdf', 'completed')
        checkpoint1.update_paper_status('paper2.pdf', 'in_progress')
        
        # Simulate interruption (create new checkpoint manager)
        checkpoint2 = CheckpointManagerV2(checkpoint_file)
        loaded = checkpoint2.load()
        
        assert loaded is True
        assert checkpoint2.data['run_id'] == checkpoint1.data['run_id']
        
        # Resume processing
        incomplete = checkpoint2.get_incomplete_papers()
        assert 'paper2.pdf' in incomplete
        assert 'paper1.pdf' not in incomplete
        
        # Complete remaining papers
        checkpoint2.update_paper_status('paper2.pdf', 'completed')
        
        # Verify final state
        assert checkpoint2.data['stats']['completed_papers'] == 2


@pytest.mark.integration
class TestQuotaIntegration:
    """Integration tests for quota management."""
    
    def test_quota_enforcement_during_processing(self, temp_dir):
        """Test quota enforcement during simulated API calls."""
        quota = SimpleQuotaManager(rate=10, per_seconds=1)  # 10 per second
        
        # Simulate rapid API calls
        start_time = time.time()
        for i in range(15):
            quota.consume(wait=True)
        elapsed = time.time() - start_time
        
        # Should take at least 0.5 seconds due to quota
        # (consumed 15 tokens with rate of 10/sec, so needed ~0.5s to refill 5 tokens)
        assert elapsed >= 0.4  # Allow some margin
        assert quota.consumed_count == 15
    
    def test_quota_with_parallel_workers(self, temp_dir):
        """Test quota manager with concurrent workers."""
        import threading
        
        quota = SimpleQuotaManager(rate=10, per_seconds=1)  # 10 per second
        results = []
        
        def worker(worker_id):
            for i in range(5):
                quota.consume(wait=True)
                results.append((worker_id, i))
        
        # Create multiple worker threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        
        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start_time
        
        # Should have consumed 20 tokens total (4 workers * 5 calls)
        assert len(results) == 20
        assert quota.consumed_count == 20
        
        # With rate of 10/sec and 20 tokens consumed, should take at least 1 second
        # (first 10 tokens are immediate, next 10 require 1 second refill)
        assert elapsed >= 0.9  # At least some throttling occurred


@pytest.mark.integration
class TestRetryIntegration:
    """Integration tests for retry logic."""
    
    def test_retry_with_transient_errors(self):
        """Test retry succeeds with transient errors."""
        attempt_count = [0]
        
        def flaky_api_call():
            attempt_count[0] += 1
            if attempt_count[0] <= 2:
                raise Exception("Connection timeout - please retry")
            return "success"
        
        result = RetryHelper.retry_with_backoff(
            flaky_api_call,
            attempts=3,
            base=0.1,
            error_classifier=ErrorClassifier
        )
        
        assert result == "success"
        assert attempt_count[0] == 3
    
    def test_retry_fails_with_permanent_errors(self):
        """Test retry stops immediately with permanent errors."""
        attempt_count = [0]
        
        def api_call_with_auth_error():
            attempt_count[0] += 1
            raise Exception("401 Unauthorized - Invalid API key")
        
        with pytest.raises(Exception, match="401 Unauthorized"):
            RetryHelper.retry_with_backoff(
                api_call_with_auth_error,
                attempts=5,
                base=0.1,
                error_classifier=ErrorClassifier
            )
        
        # Should only attempt once (no retry for permanent error)
        assert attempt_count[0] == 1


@pytest.mark.integration
class TestParallelCoordinator:
    """Integration tests for parallel pipeline coordinator."""
    
    def test_parallel_processing_with_checkpoint(self, temp_dir):
        """Test parallel processing with checkpoint tracking."""
        checkpoint_file = os.path.join(temp_dir, 'checkpoint.json')
        checkpoint = CheckpointManagerV2(checkpoint_file)
        quota = SimpleQuotaManager(rate=100, per_seconds=60)
        
        coordinator = ParallelPipelineCoordinator(
            max_workers=2,
            quota_manager=quota,
            checkpoint_manager=checkpoint
        )
        
        # Simulate paper processing function
        def process_paper(paper):
            time.sleep(0.1)  # Simulate work
            return {
                'paper': paper,
                'status': 'success',
                'stages_completed': ['journal_reviewer', 'judge']
            }
        
        papers = ['paper1.pdf', 'paper2.pdf', 'paper3.pdf', 'paper4.pdf']
        
        start_time = time.time()
        results = coordinator.process_papers_parallel(papers, process_paper)
        elapsed = time.time() - start_time
        
        # Verify all papers processed
        assert len(results) == 4
        assert coordinator.stats['successful'] == 4
        
        # Verify parallel execution (should be faster than sequential)
        # Sequential would take ~0.4s, parallel with 2 workers should take ~0.2s
        assert elapsed < 0.35  # Allow margin for overhead
        
        # Verify checkpoint was updated
        checkpoint2 = CheckpointManagerV2(checkpoint_file)
        checkpoint2.load()
        
        for paper in papers:
            status = checkpoint2.get_paper_status(paper)
            assert status is not None
            assert status['stage'] == 'completed'
    
    def test_parallel_processing_with_failures(self, temp_dir):
        """Test parallel processing handles failures correctly."""
        checkpoint_file = os.path.join(temp_dir, 'checkpoint.json')
        checkpoint = CheckpointManagerV2(checkpoint_file)
        
        coordinator = ParallelPipelineCoordinator(
            max_workers=2,
            checkpoint_manager=checkpoint
        )
        
        def process_paper(paper):
            if paper == 'paper2.pdf':
                raise Exception("Processing failed for paper2")
            return {
                'paper': paper,
                'status': 'success',
                'stages_completed': ['journal_reviewer']
            }
        
        papers = ['paper1.pdf', 'paper2.pdf', 'paper3.pdf']
        results = coordinator.process_papers_parallel(papers, process_paper)
        
        # Verify mixed results
        assert len(results) == 3
        assert coordinator.stats['successful'] == 2
        assert coordinator.stats['failed'] == 1
        
        # Verify checkpoint reflects failures
        checkpoint2 = CheckpointManagerV2(checkpoint_file)
        checkpoint2.load()
        
        paper2_status = checkpoint2.get_paper_status('paper2.pdf')
        assert paper2_status['stage'] == 'failed'
        assert 'Processing failed' in paper2_status['last_error']
    
    def test_dry_run_mode_no_side_effects(self, temp_dir):
        """Test dry-run mode doesn't execute actual processing."""
        checkpoint_file = os.path.join(temp_dir, 'checkpoint.json')
        checkpoint = CheckpointManagerV2(checkpoint_file, dry_run=True)
        
        coordinator = ParallelPipelineCoordinator(
            max_workers=2,
            checkpoint_manager=checkpoint,
            dry_run=True
        )
        
        # This function should not be called in dry-run
        def process_paper(paper):
            raise Exception("Should not be called in dry-run mode")
        
        papers = ['paper1.pdf', 'paper2.pdf']
        results = coordinator.process_papers_parallel(papers, process_paper)
        
        # Should complete without calling process_paper
        assert len(results) == 2
        for result in results:
            assert result['dry_run'] is True
        
        # Checkpoint file should not exist
        assert not os.path.exists(checkpoint_file)


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests combining multiple features."""
    
    def test_complete_pipeline_workflow(self, temp_dir):
        """Test complete workflow with all v2 features."""
        checkpoint_file = os.path.join(temp_dir, 'checkpoint.json')
        checkpoint = CheckpointManagerV2(checkpoint_file)
        quota = SimpleQuotaManager(rate=50, per_seconds=1)
        
        coordinator = ParallelPipelineCoordinator(
            max_workers=2,
            quota_manager=quota,
            checkpoint_manager=checkpoint
        )
        
        # Simulated processing with retries
        process_attempts = {}
        
        def process_paper_with_retry(paper):
            if paper not in process_attempts:
                process_attempts[paper] = 0
            
            process_attempts[paper] += 1
            
            # Simulate transient failure on first attempt for paper2
            if paper == 'paper2.pdf' and process_attempts[paper] == 1:
                raise Exception("Temporary network timeout")
            
            return {
                'paper': paper,
                'status': 'success',
                'stages_completed': ['journal_reviewer', 'judge', 'sync']
            }
        
        # Wrap with retry logic
        def process_with_retry(paper):
            return RetryHelper.retry_with_backoff(
                lambda: process_paper_with_retry(paper),
                attempts=3,
                base=0.1,
                error_classifier=ErrorClassifier
            )
        
        papers = ['paper1.pdf', 'paper2.pdf', 'paper3.pdf']
        results = coordinator.process_papers_parallel(papers, process_with_retry)
        
        # All should succeed (paper2 after retry)
        assert len(results) == 3
        assert coordinator.stats['successful'] == 3
        
        # Verify paper2 was retried
        assert process_attempts['paper2.pdf'] == 2
        
        # Verify quota was consumed
        assert quota.consumed_count == 3
        
        # Verify checkpoint state
        checkpoint2 = CheckpointManagerV2(checkpoint_file)
        checkpoint2.load()
        
        for paper in papers:
            status = checkpoint2.get_paper_status(paper)
            assert status['stage'] == 'completed'
            assert len(status['stages']) == 3


@pytest.mark.integration
class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with v1.x."""
    
    def test_v2_features_can_be_disabled(self, temp_dir):
        """Test that v2 features can be completely disabled."""
        # Create coordinator without v2 features
        coordinator = ParallelPipelineCoordinator(
            max_workers=1,  # Sequential execution
            quota_manager=None,  # No quota
            checkpoint_manager=None,  # No checkpoint
            dry_run=False
        )
        
        def process_paper(paper):
            return {'paper': paper, 'status': 'success'}
        
        papers = ['paper1.pdf']
        results = coordinator.process_papers_parallel(papers, process_paper)
        
        # Should work without v2 features
        assert len(results) == 1
        assert results[0]['status'] == 'success'
    
    def test_checkpoint_v2_data_structure(self, temp_dir):
        """Test that checkpoint v2 has required fields for compatibility."""
        checkpoint_file = os.path.join(temp_dir, 'checkpoint.json')
        checkpoint = CheckpointManagerV2(checkpoint_file)
        
        checkpoint.update_paper_status('paper1.pdf', 'completed')
        
        # Verify data structure
        assert 'run_id' in checkpoint.data
        assert 'version' in checkpoint.data
        assert checkpoint.data['version'] == '2.0.0'
        assert 'papers' in checkpoint.data
        assert 'stats' in checkpoint.data
        
        # Verify can be loaded as JSON
        checkpoint.save()
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        assert data['version'] == '2.0.0'
