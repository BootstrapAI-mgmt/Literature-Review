"""
Integration tests for interactive prompt system

Tests the PromptHandler, orchestrator integration, and WebSocket prompt flow.
"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime


# Mock FastAPI dependencies before importing prompt_handler
sys.modules['fastapi'] = MagicMock()
sys.modules['fastapi.responses'] = MagicMock()
sys.modules['fastapi.staticfiles'] = MagicMock()


@pytest.mark.asyncio
async def test_prompt_handler_basic():
    """Test basic prompt request and response"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    handler._broadcast_prompt = AsyncMock()
    
    # We need to track the prompt_id
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
        job_id="test-job",
        prompt_type="pillar_selection",
        prompt_data={"options": ["P1", "P2"], "message": "Select pillars"},
        timeout_seconds=5
    )
    
    assert response == "ALL"
    assert len(handler.pending_prompts) == 0  # Should be cleaned up


@pytest.mark.asyncio
async def test_prompt_timeout():
    """Test that prompts timeout correctly"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    handler._broadcast_prompt = AsyncMock()
    
    with pytest.raises(TimeoutError):
        await handler.request_user_input(
            job_id="test-job",
            prompt_type="pillar_selection",
            prompt_data={"options": ["P1"]},
            timeout_seconds=1  # 1 second timeout
        )


def test_prompt_handler_invalid_response():
    """Test that invalid prompt IDs raise ValueError"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    
    with pytest.raises(ValueError):
        handler.submit_response("invalid-prompt-id", "response")


@pytest.mark.asyncio
async def test_orchestrator_with_prompts():
    """Test orchestrator uses prompt callback"""
    # Import with mocked dependencies if needed
    try:
        from literature_review.orchestrator import get_user_analysis_target_async
    except ImportError:
        pytest.skip("Orchestrator dependencies not available")
    
    # Create a mock prompt callback
    async def mock_prompt_callback(prompt_type, prompt_data):
        assert prompt_type == "pillar_selection"
        assert "options" in prompt_data
        return "ALL"
    
    pillars, mode = await get_user_analysis_target_async(
        pillar_definitions={
            "P1: Pillar 1": {},
            "P2: Pillar 2": {},
            "Framework_Overview": {}  # Should be filtered out
        },
        prompt_callback=mock_prompt_callback
    )
    
    assert mode == "ONCE"
    assert len(pillars) == 2  # Excludes metadata sections
    assert "P1: Pillar 1" in pillars
    assert "P2: Pillar 2" in pillars


@pytest.mark.asyncio
async def test_orchestrator_deep_mode_selection():
    """Test orchestrator handles DEEP mode selection"""
    try:
        from literature_review.orchestrator import get_user_analysis_target_async
    except ImportError:
        pytest.skip("Orchestrator dependencies not available")
    
    async def mock_prompt_callback(prompt_type, prompt_data):
        return "DEEP"
    
    pillars, mode = await get_user_analysis_target_async(
        pillar_definitions={
            "P1: Pillar 1": {},
            "P2: Pillar 2": {}
        },
        prompt_callback=mock_prompt_callback
    )
    
    assert mode == "DEEP_LOOP"
    assert len(pillars) == 2


@pytest.mark.asyncio
async def test_orchestrator_none_selection():
    """Test orchestrator handles NONE (exit) selection"""
    try:
        from literature_review.orchestrator import get_user_analysis_target_async
    except ImportError:
        pytest.skip("Orchestrator dependencies not available")
    
    async def mock_prompt_callback(prompt_type, prompt_data):
        return "NONE"
    
    pillars, mode = await get_user_analysis_target_async(
        pillar_definitions={
            "P1: Pillar 1": {},
            "P2: Pillar 2": {}
        },
        prompt_callback=mock_prompt_callback
    )
    
    assert mode == "EXIT"
    assert len(pillars) == 0


@pytest.mark.asyncio
async def test_orchestrator_numeric_selection():
    """Test orchestrator handles numeric pillar selection"""
    try:
        from literature_review.orchestrator import get_user_analysis_target_async
    except ImportError:
        pytest.skip("Orchestrator dependencies not available")
    
    async def mock_prompt_callback(prompt_type, prompt_data):
        return "1"  # Select first pillar
    
    pillars, mode = await get_user_analysis_target_async(
        pillar_definitions={
            "P1: Pillar 1": {},
            "P2: Pillar 2": {}
        },
        prompt_callback=mock_prompt_callback
    )
    
    assert mode == "ONCE"
    assert len(pillars) == 1
    assert "P1: Pillar 1" in pillars


def test_get_pending_prompts():
    """Test getting pending prompts by job_id"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    
    # Create some pending prompts
    future1 = asyncio.Future()
    future2 = asyncio.Future()
    
    handler.pending_prompts["prompt1"] = future1
    handler.pending_prompts["prompt2"] = future2
    handler.prompt_job_ids["prompt1"] = "job1"
    handler.prompt_job_ids["prompt2"] = "job2"
    
    # Get prompts for job1
    prompts = handler.get_pending_prompts("job1")
    assert len(prompts) == 1
    assert "prompt1" in prompts
    
    # Get all prompts
    all_prompts = handler.get_pending_prompts()
    assert len(all_prompts) == 2


@pytest.mark.asyncio
async def test_prompt_handler_cleanup_on_timeout():
    """Test that prompt handler cleans up properly on timeout"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    handler._broadcast_prompt = AsyncMock()
    
    try:
        await handler.request_user_input(
            job_id="test-job",
            prompt_type="pillar_selection",
            prompt_data={"options": ["P1"]},
            timeout_seconds=1
        )
    except TimeoutError:
        pass
    
    # Verify cleanup
    assert len(handler.pending_prompts) == 0
    assert len(handler.prompt_timeouts) == 0
    assert len(handler.prompt_job_ids) == 0


@pytest.mark.asyncio
async def test_multiple_concurrent_prompts():
    """Test handling multiple concurrent prompts"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    
    # Track prompt IDs
    prompt_ids = []
    
    async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
        prompt_ids.append(prompt_id)
    
    handler._broadcast_prompt = capture_broadcast
    
    # Create responses for the prompts
    async def request_and_respond(job_id, delay=0.1):
        # Start the prompt request
        task = asyncio.create_task(
            handler.request_user_input(
                job_id=job_id,
                prompt_type="pillar_selection",
                prompt_data={"options": ["P1"]},
                timeout_seconds=3
            )
        )
        
        # Wait for prompt to be created
        await asyncio.sleep(delay)
        
        # Find the prompt for this job
        job_prompts = handler.get_pending_prompts(job_id)
        if job_prompts:
            handler.submit_response(job_prompts[0], "ALL")
        
        return await task
    
    # Start multiple prompts
    results = await asyncio.gather(
        request_and_respond("job1", 0.1),
        request_and_respond("job2", 0.1)
    )
    
    assert results == ["ALL", "ALL"]
    assert len(handler.pending_prompts) == 0
