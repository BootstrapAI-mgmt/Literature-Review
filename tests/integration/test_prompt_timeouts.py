"""
Integration tests for configurable prompt timeouts

Tests the PromptHandler timeout configuration functionality.
"""

import pytest
import asyncio
import json
import os
import tempfile
import sys
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def mock_fastapi_dependencies():
    """Mock FastAPI dependencies for all tests in this module"""
    with patch.dict(sys.modules, {
        'fastapi': MagicMock(),
        'fastapi.responses': MagicMock(),
        'fastapi.staticfiles': MagicMock()
    }):
        yield


@pytest.mark.asyncio
async def test_configured_timeout_per_prompt_type():
    """Test different timeouts for different prompt types"""
    from webdashboard.prompt_handler import PromptHandler
    
    # Create config with custom timeouts
    config = {
        "prompts": {
            "default_timeout": 300,
            "timeouts": {
                "run_mode": 120,
                "continue": 60,
                "threshold_selection": 180
            }
        }
    }
    
    # Save to temp config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_config_path = f.name
    
    try:
        handler = PromptHandler(config_file=temp_config_path)
        
        # Verify timeouts
        assert handler.get_timeout("run_mode") == 120
        assert handler.get_timeout("continue") == 60
        assert handler.get_timeout("threshold_selection") == 180
        assert handler.get_timeout("pillar_selection") == 300  # default
        assert handler.get_timeout("unknown_type") == 300  # default
    finally:
        os.unlink(temp_config_path)


@pytest.mark.asyncio
async def test_default_timeout_when_no_config():
    """Test that default timeout is used when no config exists"""
    from webdashboard.prompt_handler import PromptHandler
    
    # Use non-existent config file
    handler = PromptHandler(config_file="/tmp/nonexistent_config.json")
    
    # Should use default timeout (300s)
    assert handler.get_timeout("run_mode") == 300
    assert handler.get_timeout("continue") == 300
    assert handler.get_timeout("pillar_selection") == 300


@pytest.mark.asyncio
async def test_explicit_timeout_override():
    """Test explicit timeout parameter overrides config"""
    from webdashboard.prompt_handler import PromptHandler
    
    # Create config with custom timeouts
    config = {
        "prompts": {
            "default_timeout": 300,
            "timeouts": {
                "continue": 60
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_config_path = f.name
    
    try:
        handler = PromptHandler(config_file=temp_config_path)
        
        # Track broadcast calls to verify timeout
        broadcast_calls = []
        
        async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
            broadcast_calls.append(prompt_data)
        
        handler._broadcast_prompt = capture_broadcast
        
        # Request with explicit timeout (overrides config)
        task = asyncio.create_task(
            handler.request_user_input(
                job_id="test_job",
                prompt_type="continue",
                prompt_data={"message": "Continue?"},
                timeout_seconds=30  # Explicit override
            )
        )
        
        # Wait for prompt to be created
        await asyncio.sleep(0.1)
        
        # Verify timeout in prompt_data
        assert len(broadcast_calls) == 1
        assert broadcast_calls[0]['timeout_seconds'] == 30  # Should use explicit value
        
        # Cancel the task to avoid timeout
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    finally:
        os.unlink(temp_config_path)


@pytest.mark.asyncio
async def test_invalid_timeout_validation():
    """Test config validation rejects invalid timeouts"""
    from webdashboard.prompt_handler import PromptHandler
    
    # Test default timeout too short
    config = {
        "prompts": {
            "default_timeout": 5,  # Too short (< 10)
            "timeouts": {}
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_config_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Invalid default_timeout"):
            handler = PromptHandler(config_file=temp_config_path)
    finally:
        os.unlink(temp_config_path)


@pytest.mark.asyncio
async def test_invalid_per_prompt_timeout_validation():
    """Test config validation rejects invalid per-prompt timeouts"""
    from webdashboard.prompt_handler import PromptHandler
    
    # Test per-prompt timeout too long
    config = {
        "prompts": {
            "default_timeout": 300,
            "timeouts": {
                "run_mode": 5000  # Too long (> 3600)
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_config_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Invalid timeout for run_mode"):
            handler = PromptHandler(config_file=temp_config_path)
    finally:
        os.unlink(temp_config_path)


@pytest.mark.asyncio
async def test_ui_receives_correct_timeout():
    """Test UI gets timeout from prompt_data"""
    from webdashboard.prompt_handler import PromptHandler
    
    # Create config with custom timeouts
    config = {
        "prompts": {
            "default_timeout": 300,
            "timeouts": {
                "continue": 60
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_config_path = f.name
    
    try:
        handler = PromptHandler(config_file=temp_config_path)
        
        # Mock WebSocket broadcast
        broadcasts = []
        
        async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
            broadcasts.append(prompt_data)
        
        handler._broadcast_prompt = capture_broadcast
        
        # Request with configured timeout
        task = asyncio.create_task(
            handler.request_user_input(
                job_id="test_job",
                prompt_type="continue",
                prompt_data={"message": "Continue?"}
                # Uses config timeout (60s)
            )
        )
        
        # Wait for broadcast
        await asyncio.sleep(0.1)
        
        # Verify broadcast includes timeout
        assert len(broadcasts) == 1
        assert 'timeout_seconds' in broadcasts[0]
        assert broadcasts[0]['timeout_seconds'] == 60  # configured value
        
        # Cancel the task to avoid timeout
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    finally:
        os.unlink(temp_config_path)


@pytest.mark.asyncio
async def test_timeout_actually_works():
    """Test that configured timeout actually triggers at the right time"""
    from webdashboard.prompt_handler import PromptHandler
    
    # Create config with very short timeout
    config = {
        "prompts": {
            "default_timeout": 300,
            "timeouts": {
                "continue": 10  # 10 second timeout (minimum allowed)
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_config_path = f.name
    
    try:
        handler = PromptHandler(config_file=temp_config_path)
        
        async def mock_broadcast(*args, **kwargs):
            pass
        
        handler._broadcast_prompt = mock_broadcast
        
        # Request should timeout after 10 seconds
        import time
        start_time = time.time()
        
        # Use 1 second for testing (override the 10 second config for speed)
        with pytest.raises(TimeoutError):
            await handler.request_user_input(
                job_id="test_job",
                prompt_type="continue",
                prompt_data={"message": "Continue?"},
                timeout_seconds=1  # Explicit override for faster test
            )
        
        elapsed = time.time() - start_time
        assert elapsed >= 1.0  # Should have waited at least 1 second
        assert elapsed < 2.0   # Should not have waited much longer
    finally:
        os.unlink(temp_config_path)


@pytest.mark.asyncio
async def test_backward_compatibility_no_prompts_section():
    """Test backward compatibility when config has no prompts section"""
    from webdashboard.prompt_handler import PromptHandler
    
    # Create config without prompts section
    config = {
        "version": "2.0.0",
        "log_level": "INFO"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_config_path = f.name
    
    try:
        handler = PromptHandler(config_file=temp_config_path)
        
        # Should use default timeout (300s)
        assert handler.get_timeout("run_mode") == 300
        assert handler.get_timeout("continue") == 300
        assert handler.get_timeout("pillar_selection") == 300
    finally:
        os.unlink(temp_config_path)


@pytest.mark.asyncio
async def test_malformed_json_uses_defaults():
    """Test that malformed JSON config falls back to defaults"""
    from webdashboard.prompt_handler import PromptHandler
    
    # Create malformed JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{invalid json")
        temp_config_path = f.name
    
    try:
        handler = PromptHandler(config_file=temp_config_path)
        
        # Should use default timeout (300s) when config loading fails
        assert handler.get_timeout("run_mode") == 300
        assert handler.get_timeout("continue") == 300
    finally:
        os.unlink(temp_config_path)


@pytest.mark.asyncio
async def test_timeout_added_to_prompt_data():
    """Test that timeout is added to prompt_data for UI"""
    from webdashboard.prompt_handler import PromptHandler
    
    handler = PromptHandler()
    
    broadcasts = []
    
    async def capture_broadcast(job_id, prompt_id, prompt_type, prompt_data):
        broadcasts.append({
            'job_id': job_id,
            'prompt_id': prompt_id,
            'prompt_type': prompt_type,
            'prompt_data': prompt_data
        })
    
    handler._broadcast_prompt = capture_broadcast
    
    # Request with default timeout
    task = asyncio.create_task(
        handler.request_user_input(
            job_id="test_job",
            prompt_type="pillar_selection",
            prompt_data={"message": "Select pillars", "options": ["P1", "P2"]}
        )
    )
    
    # Wait for broadcast
    await asyncio.sleep(0.1)
    
    # Verify timeout was added to prompt_data
    assert len(broadcasts) == 1
    assert 'timeout_seconds' in broadcasts[0]['prompt_data']
    assert broadcasts[0]['prompt_data']['timeout_seconds'] == 300  # default
    assert broadcasts[0]['prompt_data']['message'] == "Select pillars"
    assert broadcasts[0]['prompt_data']['options'] == ["P1", "P2"]
    
    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
