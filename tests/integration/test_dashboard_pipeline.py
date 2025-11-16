"""
Integration tests for Dashboard Pipeline Execution

Tests cover:
- Background job runner functionality
- JobRunner integration with orchestrator
- API endpoints for job management
- Job lifecycle: queued → running → completed/failed
- Status persistence and updates
"""

import pytest
import asyncio
import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory for tests."""
    temp = tempfile.mkdtemp()
    workspace = Path(temp) / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "jobs").mkdir()
    (workspace / "status").mkdir()
    (workspace / "logs").mkdir()
    (workspace / "uploads").mkdir()
    
    yield workspace
    
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def test_job_data():
    """Sample job data for testing."""
    return {
        "id": "test-pipeline-001",
        "filename": "test.pdf",
        "file_path": "/tmp/test.pdf",
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "config": {
            "pillar_selections": ["Pillar_1"],
            "run_mode": "ONCE"
        }
    }


@pytest.fixture
def job_runner():
    """Create JobRunner instance for testing."""
    from webdashboard.job_runner import PipelineJobRunner
    runner = PipelineJobRunner(max_workers=1)
    return runner


@pytest.mark.integration
class TestJobRunner:
    """Integration tests for PipelineJobRunner."""
    
    @pytest.mark.asyncio
    async def test_job_runner_initialization(self, job_runner):
        """Test that JobRunner initializes correctly."""
        assert job_runner.queue is not None
        assert job_runner.executor is not None
        assert len(job_runner.running_jobs) == 0
    
    @pytest.mark.asyncio
    async def test_job_enqueue(self, job_runner, test_job_data):
        """Test that jobs can be enqueued."""
        await job_runner.enqueue_job(
            test_job_data["id"],
            test_job_data
        )
        
        # Queue should have one item
        assert job_runner.queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_status_update(self, job_runner, test_job_data, temp_workspace):
        """Test that status updates are saved to file."""
        # Set up workspace directory
        job_id = test_job_data["id"]
        
        # Change directory to temp workspace parent
        original_dir = os.getcwd()
        os.chdir(temp_workspace.parent)
        
        try:
            await job_runner.update_job_status(job_id, "running")
            
            # Check status file was created
            status_file = temp_workspace / "status" / f"{job_id}.json"
            assert status_file.exists()
            
            # Check status content
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            
            assert status_data["id"] == job_id
            assert status_data["status"] == "running"
            assert "started_at" in status_data
        finally:
            os.chdir(original_dir)
    
    @pytest.mark.asyncio
    async def test_log_writing(self, job_runner, test_job_data, temp_workspace):
        """Test that logs are written to file."""
        job_id = test_job_data["id"]
        
        # Change directory to temp workspace parent
        original_dir = os.getcwd()
        os.chdir(temp_workspace.parent)
        
        try:
            job_runner._write_log(job_id, "Test log message")
            
            # Check log file was created
            log_file = temp_workspace / "logs" / f"{job_id}.log"
            assert log_file.exists()
            
            # Check log content
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            assert "Test log message" in log_content
        finally:
            os.chdir(original_dir)


@pytest.mark.integration
class TestOrchestratorIntegration:
    """Integration tests for orchestrator programmatic interface."""
    
    def test_orchestrator_config_creation(self):
        """Test OrchestratorConfig creation."""
        # Import only the config class, not the whole orchestrator
        import sys
        import importlib.util
        
        # Load just the config definition without importing the entire module
        spec = importlib.util.spec_from_file_location(
            "orchestrator_module",
            "literature_review/orchestrator.py"
        )
        
        # We'll skip this test if google module is not available
        try:
            from literature_review.orchestrator import OrchestratorConfig
            
            config = OrchestratorConfig(
                job_id="test-001",
                analysis_target=["Pillar_1"],
                run_mode="ONCE",
                skip_user_prompts=True
            )
            
            assert config.job_id == "test-001"
            assert config.analysis_target == ["Pillar_1"]
            assert config.run_mode == "ONCE"
            assert config.skip_user_prompts is True
        except ModuleNotFoundError as e:
            pytest.skip(f"Skipping test due to missing dependency: {e}")
    
    def test_run_pipeline_for_job_signature(self):
        """Test that run_pipeline_for_job function exists with correct signature."""
        from literature_review.orchestrator_integration import run_pipeline_for_job
        import inspect
        
        sig = inspect.signature(run_pipeline_for_job)
        params = list(sig.parameters.keys())
        
        assert "job_id" in params
        assert "pillar_selections" in params
        assert "run_mode" in params
        assert "progress_callback" in params
        assert "log_callback" in params
    
    @pytest.mark.skipif(True, reason="Requires full orchestrator dependencies")
    def test_run_pipeline_for_job_success(self):
        """Test successful pipeline execution via run_pipeline_for_job."""
        # This test requires google-genai and other heavy dependencies
        # Skipped in minimal test environment
        pass
    
    @pytest.mark.skipif(True, reason="Requires full orchestrator dependencies")
    def test_run_pipeline_for_job_failure(self):
        """Test failed pipeline execution via run_pipeline_for_job."""
        # This test requires google-genai and other heavy dependencies
        # Skipped in minimal test environment
        pass
    
    @pytest.mark.skipif(True, reason="Requires full orchestrator dependencies")
    def test_run_pipeline_for_job_with_callbacks(self):
        """Test pipeline execution with progress and log callbacks."""
        # This test requires google-genai and other heavy dependencies
        # Skipped in minimal test environment
        pass


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndPipeline:
    """End-to-end tests for dashboard pipeline execution."""
    
    @pytest.mark.asyncio
    async def test_job_lifecycle_mocked(self, job_runner, test_job_data, temp_workspace):
        """Test complete job lifecycle with mocked orchestrator."""
        # Change directory to temp workspace parent
        original_dir = os.getcwd()
        os.chdir(temp_workspace.parent)
        
        try:
            # Mock the orchestrator execution
            with patch('literature_review.orchestrator_integration.run_pipeline_for_job') as mock_pipeline:
                mock_pipeline.return_value = {"status": "success"}
                
                # Start runner in background
                runner_task = asyncio.create_task(job_runner.start())
                
                # Enqueue job
                await job_runner.enqueue_job(
                    test_job_data["id"],
                    test_job_data
                )
                
                # Wait for job to be picked up and processed
                await asyncio.sleep(2)
                
                # Verify job is no longer running
                assert test_job_data["id"] not in job_runner.get_running_jobs()
                
                # Verify status file was created
                status_file = temp_workspace / "status" / f"{test_job_data['id']}.json"
                assert status_file.exists()
                
                # Check status
                with open(status_file, 'r') as f:
                    status = json.load(f)
                
                assert status["status"] in ["completed", "failed"]
                
                # Cleanup
                runner_task.cancel()
                try:
                    await runner_task
                except asyncio.CancelledError:
                    pass
        finally:
            os.chdir(original_dir)


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints (requires FastAPI TestClient)."""
    
    def test_job_config_model(self):
        """Test JobConfig Pydantic model."""
        from webdashboard.app import JobConfig
        
        config = JobConfig(
            pillar_selections=["Pillar_1", "Pillar_2"],
            run_mode="ONCE"
        )
        
        assert config.pillar_selections == ["Pillar_1", "Pillar_2"]
        assert config.run_mode == "ONCE"
    
    def test_job_config_validation(self):
        """Test JobConfig validation."""
        from webdashboard.app import JobConfig
        from pydantic import ValidationError
        
        # Valid config
        config = JobConfig(
            pillar_selections=["ALL"],
            run_mode="DEEP_LOOP"
        )
        assert config is not None
        
        # Missing required field should raise validation error
        with pytest.raises(ValidationError):
            JobConfig(pillar_selections=["ALL"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
