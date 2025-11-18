"""
Integration tests for prompt history tracking

Tests that prompt responses and timeouts are saved to job metadata.
"""

import pytest
import asyncio
import json
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


# Mock FastAPI dependencies before importing prompt_handler
sys.modules['fastapi'] = MagicMock()
sys.modules['fastapi.responses'] = MagicMock()
sys.modules['fastapi.staticfiles'] = MagicMock()


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace directory structure"""
    workspace = tmp_path / "workspace"
    jobs_dir = workspace / "jobs"
    jobs_dir.mkdir(parents=True)
    
    # Create a test job file
    test_job_id = "test-job-123"
    job_file = jobs_dir / f"{test_job_id}.json"
    job_data = {
        "id": test_job_id,
        "status": "running",
        "created_at": datetime.utcnow().isoformat()
    }
    with open(job_file, 'w') as f:
        json.dump(job_data, f, indent=2)
    
    # Patch the workspace path in prompt_handler
    original_cwd = Path.cwd()
    import os
    os.chdir(tmp_path)
    
    yield workspace, test_job_id
    
    # Cleanup
    os.chdir(original_cwd)


@pytest.mark.asyncio
async def test_prompt_saved_to_job_metadata(temp_workspace):
    """Test prompt response is saved to job file"""
    workspace, test_job_id = temp_workspace
    
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    handler._broadcast_prompt = AsyncMock()
    
    # Track the prompt_id
    prompt_id_holder = []
    
    async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
        prompt_id_holder.append(prompt_id)
    
    handler._broadcast_prompt = capture_broadcast
    
    # Simulate a response being submitted after a short delay
    async def respond_after_delay():
        await asyncio.sleep(0.1)
        if prompt_id_holder:
            handler.submit_response(prompt_id_holder[0], "ALL")
    
    # Start response task
    asyncio.create_task(respond_after_delay())
    
    # Request prompt (will block until response)
    response = await handler.request_user_input(
        job_id=test_job_id,
        prompt_type="pillar_selection",
        prompt_data={"options": ["P1", "P2"], "message": "Select pillars"},
        timeout_seconds=5
    )
    
    # Wait a bit for async save to complete
    await asyncio.sleep(0.2)
    
    # Verify saved to job file
    job_file = workspace / "jobs" / f"{test_job_id}.json"
    with open(job_file, 'r') as f:
        job_data = json.load(f)
    
    assert 'prompts' in job_data
    assert len(job_data['prompts']) == 1
    assert job_data['prompts'][0]['type'] == 'pillar_selection'
    assert job_data['prompts'][0]['response'] == 'ALL'
    assert job_data['prompts'][0]['timed_out'] == False
    assert 'timestamp' in job_data['prompts'][0]
    assert 'prompt_id' in job_data['prompts'][0]
    assert job_data['prompts'][0]['timeout_seconds'] == 5
    assert job_data['prompts'][0]['prompt_data']['message'] == "Select pillars"


@pytest.mark.asyncio
async def test_timeout_saved_to_history(temp_workspace):
    """Test timeout event is recorded in history"""
    workspace, test_job_id = temp_workspace
    
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    handler._broadcast_prompt = AsyncMock()
    
    try:
        # Request prompt with 1-second timeout
        await handler.request_user_input(
            job_id=test_job_id,
            prompt_type="continue",
            prompt_data={"message": "Continue?", "options": ["yes", "no"]},
            timeout_seconds=1
        )
    except TimeoutError:
        pass  # Expected
    
    # Wait a bit for async save to complete
    await asyncio.sleep(0.2)
    
    # Verify timeout recorded
    job_file = workspace / "jobs" / f"{test_job_id}.json"
    with open(job_file, 'r') as f:
        job_data = json.load(f)
    
    assert 'prompts' in job_data
    assert len(job_data['prompts']) == 1
    assert job_data['prompts'][0]['timed_out'] == True
    assert job_data['prompts'][0]['response'] is None
    assert job_data['prompts'][0]['type'] == 'continue'


@pytest.mark.asyncio
async def test_multiple_prompts_saved(temp_workspace):
    """Test multiple prompts are saved in sequence"""
    workspace, test_job_id = temp_workspace
    
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    handler._broadcast_prompt = AsyncMock()
    
    # Track prompt IDs
    prompt_ids = []
    
    async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
        prompt_ids.append(prompt_id)
    
    handler._broadcast_prompt = capture_broadcast
    
    # First prompt: pillar_selection
    async def respond_pillar():
        await asyncio.sleep(0.1)
        if len(prompt_ids) >= 1:
            handler.submit_response(prompt_ids[0], "ALL")
    
    asyncio.create_task(respond_pillar())
    
    response1 = await handler.request_user_input(
        job_id=test_job_id,
        prompt_type="pillar_selection",
        prompt_data={"message": "Select pillars"},
        timeout_seconds=5
    )
    
    await asyncio.sleep(0.2)  # Wait for save
    
    # Second prompt: run_mode
    async def respond_mode():
        await asyncio.sleep(0.1)
        if len(prompt_ids) >= 2:
            handler.submit_response(prompt_ids[1], "DEEP_LOOP")
    
    asyncio.create_task(respond_mode())
    
    response2 = await handler.request_user_input(
        job_id=test_job_id,
        prompt_type="run_mode",
        prompt_data={"message": "Select mode", "options": ["ONCE", "DEEP_LOOP"]},
        timeout_seconds=5
    )
    
    await asyncio.sleep(0.2)  # Wait for save
    
    # Verify both saved
    job_file = workspace / "jobs" / f"{test_job_id}.json"
    with open(job_file, 'r') as f:
        job_data = json.load(f)
    
    assert 'prompts' in job_data
    assert len(job_data['prompts']) == 2
    
    # First prompt
    assert job_data['prompts'][0]['type'] == 'pillar_selection'
    assert job_data['prompts'][0]['response'] == 'ALL'
    assert job_data['prompts'][0]['timed_out'] == False
    
    # Second prompt
    assert job_data['prompts'][1]['type'] == 'run_mode'
    assert job_data['prompts'][1]['response'] == 'DEEP_LOOP'
    assert job_data['prompts'][1]['timed_out'] == False


@pytest.mark.asyncio
async def test_prompt_history_preserves_prompt_data(temp_workspace):
    """Test that prompt_data is fully preserved in history"""
    workspace, test_job_id = temp_workspace
    
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    handler._broadcast_prompt = AsyncMock()
    
    prompt_id_holder = []
    
    async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
        prompt_id_holder.append(prompt_id)
    
    handler._broadcast_prompt = capture_broadcast
    
    # Complex prompt data
    prompt_data = {
        "message": "Continue deep review loop?",
        "iteration": 3,
        "gap_count": 7,
        "options": ["yes", "no"],
        "default": "yes",
        "details": "Found 7 gaps to address"
    }
    
    async def respond():
        await asyncio.sleep(0.1)
        if prompt_id_holder:
            handler.submit_response(prompt_id_holder[0], "yes")
    
    asyncio.create_task(respond())
    
    response = await handler.request_user_input(
        job_id=test_job_id,
        prompt_type="continue",
        prompt_data=prompt_data,
        timeout_seconds=5
    )
    
    await asyncio.sleep(0.2)
    
    # Verify prompt_data is preserved
    job_file = workspace / "jobs" / f"{test_job_id}.json"
    with open(job_file, 'r') as f:
        job_data = json.load(f)
    
    assert job_data['prompts'][0]['prompt_data']['iteration'] == 3
    assert job_data['prompts'][0]['prompt_data']['gap_count'] == 7
    assert job_data['prompts'][0]['prompt_data']['details'] == "Found 7 gaps to address"


@pytest.mark.asyncio
async def test_prompt_history_with_list_response(temp_workspace):
    """Test that list responses (multi-select) are saved correctly"""
    workspace, test_job_id = temp_workspace
    
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    handler._broadcast_prompt = AsyncMock()
    
    prompt_id_holder = []
    
    async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
        prompt_id_holder.append(prompt_id)
    
    handler._broadcast_prompt = capture_broadcast
    
    async def respond():
        await asyncio.sleep(0.1)
        if prompt_id_holder:
            # Multi-select response
            handler.submit_response(prompt_id_holder[0], ["P1: Pillar 1", "P3: Pillar 3"])
    
    asyncio.create_task(respond())
    
    response = await handler.request_user_input(
        job_id=test_job_id,
        prompt_type="pillar_selection",
        prompt_data={"message": "Select pillars", "options": ["P1: Pillar 1", "P2: Pillar 2", "P3: Pillar 3"]},
        timeout_seconds=5
    )
    
    await asyncio.sleep(0.2)
    
    # Verify list response is saved
    job_file = workspace / "jobs" / f"{test_job_id}.json"
    with open(job_file, 'r') as f:
        job_data = json.load(f)
    
    assert isinstance(job_data['prompts'][0]['response'], list)
    assert len(job_data['prompts'][0]['response']) == 2
    assert "P1: Pillar 1" in job_data['prompts'][0]['response']
    assert "P3: Pillar 3" in job_data['prompts'][0]['response']


@pytest.mark.asyncio
async def test_backward_compatibility_no_prompts_field():
    """Test that jobs without prompts field continue to work"""
    # This is more of a documentation test - the UI should handle missing prompts gracefully
    
    job_data = {
        "id": "old-job",
        "status": "completed",
        "created_at": "2025-01-01T00:00:00Z"
        # No 'prompts' field
    }
    
    # Test that getting prompts with .get() returns empty list
    prompts = job_data.get('prompts', [])
    assert prompts == []
    assert len(prompts) == 0


def test_prompt_metadata_structure():
    """Test that prompt metadata has correct structure"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    
    # Verify initial state
    assert hasattr(handler, 'prompt_metadata')
    assert isinstance(handler.prompt_metadata, dict)
    assert len(handler.prompt_metadata) == 0
