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

**Files Used (No Changes)**:
1. `webdashboard/prompt_handler.py` - Existing prompt infrastructure
2. `webdashboard/templates/index.html` - Existing UI components

**Test Results**: 12 passed, 4 skipped, 0 failed

**Lines of Code**: 
- Orchestrator: ~60 lines added
- Tests: ~180 lines added
- Total: ~240 lines
