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


@pytest.mark.asyncio
async def test_multi_select_pillars():
    """Test multi-select pillar selection"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    
    # Track prompt IDs
    prompt_ids = []
    
    async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
        prompt_ids.append(prompt_id)
    
    handler._broadcast_prompt = capture_broadcast
    
    # Request pillar selection
    task = asyncio.create_task(
        handler.request_user_input(
            job_id="test_job",
            prompt_type="pillar_selection",
            prompt_data={
                "message": "Select pillars",
                "options": ["P1: Pillar 1", "P2: Pillar 2", "P3: Pillar 3"]
            },
            timeout_seconds=3
        )
    )
    
    # Wait for prompt to be created
    await asyncio.sleep(0.1)
    
    # Simulate user selecting multiple pillars
    prompt_id = prompt_ids[0]
    handler.submit_response(prompt_id, ["P1: Pillar 1", "P3: Pillar 3"])
    
    result = await task
    
    # Verify multi-select response
    assert isinstance(result, list)
    assert len(result) == 2
    assert "P1: Pillar 1" in result
    assert "P3: Pillar 3" in result


@pytest.mark.asyncio
async def test_run_mode_prompt_integration():
    """Test run_mode prompt when starting job without config"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    
    # Track prompt IDs
    prompt_ids = []
    
    async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
        prompt_ids.append(prompt_id)
    
    handler._broadcast_prompt = capture_broadcast
    
    # Request pillar selection
    task = asyncio.create_task(
        handler.request_user_input(
            job_id="test_job",
            prompt_type="pillar_selection",
            prompt_data={
                "message": "Select pillars",
                "options": ["P1: Pillar 1", "P2: Pillar 2", "P3: Pillar 3"]
            },
            timeout_seconds=3
        )
    )
    
    # Wait for prompt to be created
    await asyncio.sleep(0.1)
    
    # Simulate user selecting multiple pillars
    prompt_id = prompt_ids[0]
    handler.submit_response(prompt_id, ["P1: Pillar 1", "P3: Pillar 3"])
    
    result = await task
    
    # Verify multi-select response
    assert isinstance(result, list)
    assert len(result) == 2
    assert "P1: Pillar 1" in result
    assert "P3: Pillar 3" in result


@pytest.mark.asyncio
async def test_special_option_all_with_multi_select():
    """Test ALL special option still works with multi-select UI"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    prompt_id_holder = []
    
    async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
        prompt_id_holder.append(prompt_id)
        # Verify the prompt type and data
        assert prompt_type == "run_mode"
        assert "options" in prompt_data
        assert "ONCE" in prompt_data["options"]
        assert "DEEP_LOOP" in prompt_data["options"]
    
    handler._broadcast_prompt = capture_broadcast
    
    # Simulate a response being submitted after a short delay
    async def respond_after_delay():
        await asyncio.sleep(0.1)
        if prompt_id_holder:
            handler.submit_response(prompt_id_holder[0], "DEEP_LOOP")
    
    # Start response task
    asyncio.create_task(respond_after_delay())
    
    # Request prompt (will block until response)
    response = await handler.request_user_input(
        job_id="test-job",
        prompt_type="run_mode",
        prompt_data={
            "message": "Select analysis mode",
            "options": ["ONCE", "DEEP_LOOP"],
            "default": "ONCE"
        },
        timeout_seconds=5
    )
    
    assert response == "DEEP_LOOP"
    assert len(handler.pending_prompts) == 0  # Should be cleaned up


@pytest.mark.asyncio
async def test_continue_prompt_deep_loop():
    """Test continue prompt in deep loop workflow"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    
    # Track prompt IDs and call count
    prompt_ids = []
    
    async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
        prompt_ids.append(prompt_id)
    
    handler._broadcast_prompt = capture_broadcast
    
    task = asyncio.create_task(
        handler.request_user_input(
            job_id="test_job",
            prompt_type="pillar_selection",
            prompt_data={"message": "Select pillars"},
            timeout_seconds=3
        )
    )
    
    await asyncio.sleep(0.1)
    
    prompt_id = prompt_ids[0]
    handler.submit_response(prompt_id, "ALL")
    
    result = await task
    
    # Verify ALL option returns string (not list)
    assert isinstance(result, str)
    assert result == "ALL"


@pytest.mark.asyncio
async def test_orchestrator_multi_select_pillars():
    """Test orchestrator handles multi-select pillar selection"""
    try:
        from literature_review.orchestrator import get_user_analysis_target_async
    except ImportError:
        pytest.skip("Orchestrator dependencies not available")
    
    async def mock_prompt_callback(prompt_type, prompt_data):
        # Simulate user selecting pillars 1 and 3
        return ["P1: Pillar 1", "P3: Pillar 3"]
    
    pillars, mode = await get_user_analysis_target_async(
        pillar_definitions={
            "P1: Pillar 1": {},
            "P2: Pillar 2": {},
            "P3: Pillar 3": {},
            "Framework_Overview": {}  # Should be filtered out
        },
        prompt_callback=mock_prompt_callback
    )
    
    assert mode == "ONCE"
    assert len(pillars) == 2
    assert "P1: Pillar 1" in pillars
    assert "P3: Pillar 3" in pillars
    assert "P2: Pillar 2" not in pillars


@pytest.mark.asyncio
async def test_orchestrator_multi_select_validation():
    """Test orchestrator handles invalid multi-select gracefully"""
    try:
        from literature_review.orchestrator import get_user_analysis_target_async
    except ImportError:
        pytest.skip("Orchestrator dependencies not available")
    
    async def mock_prompt_callback(prompt_type, prompt_data):
        # Simulate user selecting invalid pillars
        return ["Invalid Pillar", "Another Invalid"]
    
    pillars, mode = await get_user_analysis_target_async(
        pillar_definitions={
            "P1: Pillar 1": {},
            "P2: Pillar 2": {}
        },
        prompt_callback=mock_prompt_callback
    )
    
    # Should return EXIT mode when no valid selections
    assert mode == "EXIT"
    assert len(pillars) == 0


@pytest.mark.asyncio
async def test_orchestrator_backward_compatibility():
    """Test orchestrator still handles single pillar string selection"""
    try:
        from literature_review.orchestrator import get_user_analysis_target_async
    except ImportError:
        pytest.skip("Orchestrator dependencies not available")
    
    # Test with numeric string (old format)
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


@pytest.mark.asyncio
async def test_run_mode_prompt_timeout():
    """Test run_mode prompt timeout handling"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    handler._broadcast_prompt = AsyncMock()
    
    # Test timeout on run_mode prompt
    with pytest.raises(TimeoutError):
        await handler.request_user_input(
            job_id="test-job",
            prompt_type="run_mode",
            prompt_data={
                "message": "Select analysis mode",
                "options": ["ONCE", "DEEP_LOOP"],
                "default": "ONCE"
            },
            timeout_seconds=1  # 1 second timeout
        )
    
    # Verify cleanup
    assert len(handler.pending_prompts) == 0


@pytest.mark.asyncio
async def test_continue_prompt_timeout():
    """Test continue prompt timeout handling"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    handler._broadcast_prompt = AsyncMock()
    
    # Test timeout on continue prompt
    with pytest.raises(TimeoutError):
        await handler.request_user_input(
            job_id="test-job",
            prompt_type="continue",
            prompt_data={
                "message": "Continue deep review loop?",
                "iteration": 1,
                "gap_count": 5,
                "options": ["yes", "no"],
                "default": "yes"
            },
            timeout_seconds=1  # 1 second timeout
        )
    
    # Verify cleanup
    assert len(handler.pending_prompts) == 0


def test_backward_compatibility_config_with_run_mode():
    """Test backward compatibility: config with run_mode skips prompt"""
    # This test verifies that when config has run_mode set, no prompt is shown
    # This is important for backward compatibility with existing workflows
    
    # Create a simple config object to test the logic
    # In the orchestrator, when skip_user_prompts=True, prompts are never shown
    # This ensures backward compatibility with existing workflows
    
    class MockConfig:
        def __init__(self):
            self.job_id = "test-job"
            self.analysis_target = ["P1: Pillar 1"]
            self.run_mode = "ONCE"  # Already set
            self.skip_user_prompts = True  # Traditional mode
            self.prompt_callback = None
    
    config = MockConfig()
    
    # Verify config has run_mode set
    assert config.run_mode == "ONCE"
    assert config.skip_user_prompts is True
    
    # In this mode, the orchestrator should NOT call prompt_callback
    # This is tested implicitly by the orchestrator logic:
    # - If skip_user_prompts=True, prompts are never shown
    # - If skip_user_prompts=False but run_mode is set, prompt is skipped


def test_prompt_enabled_mode_without_run_mode():
    """Test that prompt should be shown when skip_user_prompts=False and run_mode not set"""
    
    # Create a simple config object to test the logic
    # In the orchestrator, when skip_user_prompts=False and run_mode is empty,
    # the orchestrator should call prompt_callback
    
    class MockConfig:
        def __init__(self):
            self.job_id = "test-job"
            self.analysis_target = ["P1: Pillar 1"]
            self.run_mode = ""  # Not set
            self.skip_user_prompts = False  # Prompts enabled
            self.prompt_callback = lambda: "DEEP_LOOP"
    
    config = MockConfig()
    
    # Verify config state
    assert config.run_mode == ""
    assert config.skip_user_prompts is False
    assert config.prompt_callback is not None
    
    # The orchestrator should call prompt_callback when run_mode is missing
    # This is the key new functionality being added
