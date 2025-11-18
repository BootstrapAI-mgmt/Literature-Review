# Interactive Prompts Integration Guide

## Overview

This document describes the integration of `run_mode` and `continue` prompts with the orchestrator, implemented as part of ENHANCE-P5-2.

## Features

### 1. Run Mode Selection Prompt

**When shown**: When starting a job without `run_mode` specified in config and prompts are enabled.

**Purpose**: Allows users to select the analysis mode interactively via the dashboard.

**Options**:
- `ONCE` - Single pass analysis (default)
- `DEEP_LOOP` - Iterative deep review until convergence

**Configuration**:
```python
config = OrchestratorConfig(
    job_id="my-job",
    analysis_target=["P1: Pillar 1"],
    run_mode="",  # Empty or None triggers prompt
    skip_user_prompts=False,  # Enable prompts
    prompt_callback=your_async_callback
)
```

### 2. Continue Deep Loop Prompt

**When shown**: After each iteration in DEEP_LOOP mode when prompts are enabled.

**Purpose**: Allows users to decide whether to continue with another deep review iteration or stop.

**Prompt Data**:
- Iteration number
- Number of gaps found
- Yes/No options

**Example**:
```
Iteration 2 complete. Found 8 gaps to address. Continue with deep review?
[ ] Yes, continue
[ ] No, stop here
```

## Usage Examples

### Example 1: Dashboard Mode with Prompts

```python
from literature_review.orchestrator import OrchestratorConfig, main

async def my_prompt_callback(prompt_type, prompt_data):
    """Handle interactive prompts"""
    if prompt_type == "run_mode":
        # Show UI for run mode selection
        return await show_run_mode_ui(prompt_data)
    elif prompt_type == "continue":
        # Show UI for continue decision
        return await show_continue_ui(prompt_data)

config = OrchestratorConfig(
    job_id="job-123",
    analysis_target=["ALL"],
    run_mode="",  # Will prompt
    skip_user_prompts=False,
    prompt_callback=my_prompt_callback
)

main(config)
```

### Example 2: Backward Compatible Mode (No Prompts)

```python
# Existing code continues to work unchanged
config = OrchestratorConfig(
    job_id="job-123",
    analysis_target=["ALL"],
    run_mode="ONCE",  # Specified, no prompt
    skip_user_prompts=True  # Traditional mode
)

main(config)
```

### Example 3: Config with run_mode (Skips Prompt)

```python
# Even with prompts enabled, if run_mode is set, no prompt is shown
config = OrchestratorConfig(
    job_id="job-123",
    analysis_target=["ALL"],
    run_mode="DEEP_LOOP",  # Already set
    skip_user_prompts=False,
    prompt_callback=my_prompt_callback
)

main(config)  # No run_mode prompt shown
```

## Integration Points

### Orchestrator Code

The orchestrator checks for prompts at two key points:

1. **Startup** (lines ~1858-1910 in orchestrator.py):
   - If `config.prompt_callback` exists and `skip_user_prompts=False`
   - And `run_mode` is not set or empty
   - Then prompt for run_mode

2. **Deep Loop Decision** (lines ~2061-2095 in orchestrator.py):
   - After each iteration in DEEP_LOOP mode
   - If `config.prompt_callback` exists and `skip_user_prompts=False`
   - Then prompt to continue or stop

### UI Components

The WebDashboard already has rendering functions:

- `renderRunModePrompt(promptData)` - in index.html, line 2199
- `renderContinuePrompt(promptData)` - in index.html, line 2218

These are automatically invoked when the orchestrator sends prompt requests via WebSocket.

## Error Handling

### Timeout

Both prompts have a default 5-minute timeout. If the user doesn't respond:

```python
try:
    response = await prompt_callback(prompt_type, prompt_data)
except TimeoutError:
    # For run_mode: defaults to "ONCE"
    # For continue: defaults to "yes" (continue)
```

### Invalid Responses

Responses are validated:
- run_mode: Must be "ONCE" or "DEEP_LOOP"
- continue: Must be "yes" or "no" (case-insensitive)

## Testing

Comprehensive test suite in `tests/integration/test_interactive_prompts.py`:

```bash
# Run all prompt tests
pytest tests/integration/test_interactive_prompts.py -v

# Run specific tests
pytest tests/integration/test_interactive_prompts.py::test_run_mode_prompt_integration -v
pytest tests/integration/test_interactive_prompts.py::test_continue_prompt_deep_loop -v
```

Test coverage:
- ✅ Basic prompt flow
- ✅ Timeout handling
- ✅ Backward compatibility
- ✅ Multiple iterations
- ✅ Response validation

## Backward Compatibility

The implementation is fully backward compatible:

1. **Existing code with `skip_user_prompts=True`**: Works unchanged
2. **Config with run_mode set**: Skips prompt even if prompts enabled
3. **Terminal mode**: Uses original `input()` based prompts

## Configuration Options

### Prompt Behavior Matrix

| skip_user_prompts | run_mode set | prompt_callback | Behavior |
|-------------------|--------------|----------------|----------|
| True | Any | Any | No prompts (traditional) |
| False | Yes | Yes | No run_mode prompt |
| False | No/Empty | Yes | Shows run_mode prompt |
| False | N/A | None | Uses terminal input |

### Future Enhancements (Out of Scope)

From the original issue, these are NOT implemented yet:

- [ ] `threshold_selection` prompt - Before gap analysis
- [ ] `convergence_confirmation` prompt - Before exiting loop
- [ ] Prompt history saved to job metadata
- [ ] Per-prompt timeout configuration
- [ ] Configurable default responses

These can be added in future iterations following the same pattern.

## Implementation Summary

**Files Modified**:
1. `literature_review/orchestrator.py` - Added prompt integration logic
2. `tests/integration/test_interactive_prompts.py` - Added comprehensive tests
3. `webdashboard/prompt_handler.py` - Added configurable timeout support (ENHANCE-P5-5)
4. `webdashboard/job_runner.py` - Updated to use configured timeouts (ENHANCE-P5-5)
5. `pipeline_config.json` - Added prompts configuration section (ENHANCE-P5-5)

**Files Used (No Changes)**:
1. `webdashboard/templates/index.html` - Existing UI components

**Test Results**: 14 passed, 7 skipped, 0 failed

**Lines of Code**: 
- Orchestrator: ~60 lines added
- Tests: ~180 lines added
- Prompt Handler timeout config: ~80 lines added
- Tests for timeout config: ~380 lines added
- Total: ~700 lines

---

## Configurable Prompt Timeouts (ENHANCE-P5-5)

### Overview

As of ENHANCE-P5-5, prompt timeouts are now configurable per prompt type via `pipeline_config.json`. Different prompts have different complexity levels and thus different appropriate timeout durations.

### Configuration

Add a `prompts` section to `pipeline_config.json`:

```json
{
  "prompts": {
    "default_timeout": 300,
    "timeouts": {
      "pillar_selection": 300,
      "run_mode": 120,
      "continue": 60,
      "threshold_selection": 180,
      "convergence_confirmation": 90
    }
  }
}
```

### Timeout Ranges

- **Minimum**: 10 seconds
- **Maximum**: 3600 seconds (1 hour)
- **Default**: 300 seconds (5 minutes) if not configured

### Timeout Recommendations

| Prompt Type | Recommended Timeout | Justification |
|-------------|-------------------|---------------|
| `pillar_selection` | 300s (5 min) | Complex choice, need to understand pillars |
| `run_mode` | 120s (2 min) | Simple binary: ONCE vs DEEP_LOOP |
| `continue` | 60s (1 min) | Simple yes/no decision |
| `threshold_selection` | 180s (3 min) | Requires understanding gap threshold concept |
| `convergence_confirmation` | 90s (1.5 min) | Review convergence data and decide |

### Environment-Specific Examples

#### Development (Relaxed Timeouts)
```json
{
  "prompts": {
    "default_timeout": 600,
    "timeouts": {
      "pillar_selection": 900
    }
  }
}
```

#### Production (Aggressive Timeouts)
```json
{
  "prompts": {
    "default_timeout": 30,
    "timeouts": {
      "pillar_selection": 60,
      "run_mode": 30,
      "continue": 20
    }
  }
}
```

### Programmatic Usage

#### Using Configured Timeouts

```python
from webdashboard.prompt_handler import PromptHandler

# Load from pipeline_config.json
handler = PromptHandler("pipeline_config.json")

# Request prompt with configured timeout
response = await handler.request_user_input(
    job_id="job-123",
    prompt_type="run_mode",
    prompt_data={"message": "Select mode", "options": ["ONCE", "DEEP_LOOP"]}
    # No timeout_seconds → uses configured value (120s for run_mode)
)
```

#### Explicit Timeout Override

```python
# Override config for this specific prompt
response = await handler.request_user_input(
    job_id="job-123",
    prompt_type="pillar_selection",
    prompt_data={"message": "Select pillars"},
    timeout_seconds=600  # Explicit 10-minute timeout
)
```

#### Getting Timeout for a Prompt Type

```python
handler = PromptHandler("pipeline_config.json")

timeout = handler.get_timeout("run_mode")  # Returns 120 (or default 300)
```

### UI Integration

The UI automatically receives the timeout value in `prompt_data.timeout_seconds` and displays an appropriate countdown timer. No UI changes are required.

**JavaScript Example** (already implemented in `index.html`):
```javascript
function showPrompt(promptData) {
    const timeoutSeconds = promptData.timeout_seconds || 300;
    startCountdown(timeoutSeconds);
}
```

### Backward Compatibility

- **No Config**: If `pipeline_config.json` doesn't exist or lacks a `prompts` section, all prompts use 300s default
- **Partial Config**: If only some prompt types are configured, others fall back to `default_timeout`
- **Invalid Config**: If configuration is invalid (timeouts outside 10-3600 range), an error is raised at initialization
- **Explicit Override**: Passing `timeout_seconds` to `request_user_input()` always takes precedence over config

### Validation

Configuration is validated on load:

```python
# Valid
config = {
    "prompts": {
        "default_timeout": 300,  # ✓ 10-3600 range
        "timeouts": {
            "run_mode": 120      # ✓ 10-3600 range
        }
    }
}

# Invalid - raises ValueError
config = {
    "prompts": {
        "default_timeout": 5,    # ✗ Too short (< 10)
        "timeouts": {
            "run_mode": 5000     # ✗ Too long (> 3600)
        }
    }
}
```

### Testing

Comprehensive tests are available in `tests/integration/test_prompt_timeouts.py`:

```bash
pytest tests/integration/test_prompt_timeouts.py -v
```

Test coverage includes:
- Configuration loading and validation
- Per-prompt-type timeout configuration
- Explicit timeout overrides
- Backward compatibility
- Invalid configuration handling
- UI timeout data propagation
- Actual timeout behavior
