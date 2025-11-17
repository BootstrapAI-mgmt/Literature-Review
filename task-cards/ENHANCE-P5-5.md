# ENHANCE-P5-5: Make Prompt Timeout Configurable Per Prompt Type

**Category:** Interactive Prompts Enhancement  
**Priority:** 🟢 LOW  
**Effort:** 1 hour  
**Created:** November 17, 2025  
**Source:** PR #46 Review - Deferred Items Section #5

---

## Problem Statement

All prompts currently use a hardcoded 300-second (5-minute) timeout. Different prompt types have different complexity levels and should have different timeout durations.

**Current Limitation:**
```python
# In job_runner.py - hardcoded timeout
response = await prompt_handler.request_user_input(
    job_id=job_id,
    prompt_type=prompt_type,
    prompt_data=prompt_data,
    timeout_seconds=300  # Same for all prompts
)
```

---

## Rationale

Different prompts have different cognitive complexity:

| Prompt Type | Complexity | Current Timeout | Proposed Timeout | Justification |
|-------------|-----------|----------------|-----------------|---------------|
| `pillar_selection` | High | 5 min (300s) | **5 min (300s)** | Complex choice, need to understand pillars |
| `run_mode` | Low | 5 min (300s) | **2 min (120s)** | Simple binary: ONCE vs DEEP_LOOP |
| `continue` | Low | 5 min (300s) | **1 min (60s)** | Simple yes/no decision |
| `threshold_selection` | Medium | 5 min (300s) | **3 min (180s)** | Requires understanding gap threshold concept |

**Problems with one-size-fits-all:**
- Simple prompts (yes/no) don't need 5 minutes
- User might walk away, job sits idle unnecessarily
- Complex prompts might need _more_ than 5 minutes in some cases

---

## Use Cases

### 1. Quick Decisions
**Scenario:** Deep loop asks "Continue? Yes/No"  
**Current:** 5-minute timeout (excessive for binary choice)  
**Desired:** 60-second timeout (appropriate for simple decision)

### 2. Complex Configuration
**Scenario:** User selecting from 15 pillars, needs to read descriptions  
**Current:** 5-minute timeout (might be insufficient)  
**Desired:** Configurable to 10 minutes for this specific deployment

### 3. Automated Workflows
**Scenario:** Scripted deployment with automated prompt responses  
**Current:** Must wait up to 5 minutes for each timeout  
**Desired:** Short 30-second timeouts for all prompts

---

## Acceptance Criteria

- [ ] Timeout configurable in `pipeline_config.json`
- [ ] Per-prompt-type timeout configuration
- [ ] UI displays appropriate countdown timer from `prompt_data.timeout_seconds`
- [ ] Fallback to default (300s) if not configured
- [ ] Tests verify different timeouts work correctly
- [ ] Backward compatible (existing jobs use 300s default)

---

## Configuration Design

### pipeline_config.json

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

### Environment-Specific Overrides

**Development:**
```json
{
  "prompts": {
    "default_timeout": 600,  // 10 minutes for development
    "timeouts": {
      "pillar_selection": 900  // 15 minutes (reading docs)
    }
  }
}
```

**Production/Automated:**
```json
{
  "prompts": {
    "default_timeout": 30,  // 30 seconds (fast-paced)
    "timeouts": {
      "pillar_selection": 60
    }
  }
}
```

---

## Implementation Plan

### 1. Add Timeout Configuration Loader

**File:** `webdashboard/prompt_handler.py`

```python
class PromptHandler:
    def __init__(self, config_file: str = "pipeline_config.json"):
        self.pending_prompts = {}
        self.timeout_tasks = {}
        
        # NEW: Load timeout configuration
        self.config = self._load_config(config_file)
        self.default_timeout = self.config.get('prompts', {}).get('default_timeout', 300)
        self.prompt_timeouts = self.config.get('prompts', {}).get('timeouts', {})
    
    def _load_config(self, config_file: str) -> dict:
        """Load pipeline configuration"""
        import json
        import os
        
        if not os.path.exists(config_file):
            return {}
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def get_timeout(self, prompt_type: str) -> int:
        """
        Get timeout for specific prompt type
        
        Args:
            prompt_type: Type of prompt (pillar_selection, run_mode, etc.)
        
        Returns:
            Timeout in seconds
        
        Examples:
            >>> handler.get_timeout("run_mode")
            120  # 2 minutes
            >>> handler.get_timeout("unknown_type")
            300  # default
        """
        return self.prompt_timeouts.get(prompt_type, self.default_timeout)
    
    async def request_user_input(
        self,
        job_id: str,
        prompt_type: str,
        prompt_data: dict,
        timeout_seconds: Optional[int] = None  # NEW: optional override
    ):
        """
        Request user input via prompt
        
        Args:
            timeout_seconds: Optional timeout override. If None, uses config.
        """
        # NEW: Use configured timeout if not explicitly provided
        if timeout_seconds is None:
            timeout_seconds = self.get_timeout(prompt_type)
        
        # Add timeout to prompt_data for UI display
        prompt_data['timeout_seconds'] = timeout_seconds
        
        # ... rest of existing code ...
```

---

### 2. Update Job Runner to Use Configured Timeouts

**File:** `webdashboard/job_runner.py`

```python
async def run_job_with_prompts(job_id: str, prompt_handler: PromptHandler):
    """Run job with interactive prompts"""
    
    # Pillar selection prompt (uses configured timeout)
    pillar_response = await prompt_handler.request_user_input(
        job_id=job_id,
        prompt_type="pillar_selection",
        prompt_data={"message": "Select pillars", "pillars": [...]}
        # No timeout_seconds arg → uses config (300s by default)
    )
    
    # Run mode prompt (uses configured timeout)
    run_mode = await prompt_handler.request_user_input(
        job_id=job_id,
        prompt_type="run_mode",
        prompt_data={"message": "Select mode", "options": ["ONCE", "DEEP_LOOP"]}
        # Uses config (120s if configured, 300s default)
    )
    
    # Continue prompt in deep loop (uses configured timeout)
    if run_mode == "DEEP_LOOP":
        while True:
            # ... gap analysis ...
            
            continue_choice = await prompt_handler.request_user_input(
                job_id=job_id,
                prompt_type="continue",
                prompt_data={"message": "Continue?", "iteration": 2}
                # Uses config (60s if configured, 300s default)
            )
            
            if continue_choice != "Yes":
                break
```

**Explicit Override Example:**
```python
# Force 10-minute timeout for this specific prompt (override config)
response = await prompt_handler.request_user_input(
    job_id=job_id,
    prompt_type="pillar_selection",
    prompt_data={...},
    timeout_seconds=600  # Explicit override
)
```

---

### 3. Update UI to Display Correct Timeout

**File:** `webdashboard/templates/index.html`

**Current UI** already reads `prompt_data.timeout_seconds`:

```javascript
function showPrompt(promptData) {
    const timeoutSeconds = promptData.timeout_seconds || 300;  // Already exists
    
    // Start countdown timer
    startCountdown(timeoutSeconds);
}

function startCountdown(seconds) {
    let remaining = seconds;
    const timer = setInterval(() => {
        remaining--;
        
        // Update UI
        const minutes = Math.floor(remaining / 60);
        const secs = remaining % 60;
        $('#countdown-timer').text(`${minutes}:${secs.toString().padStart(2, '0')}`);
        
        if (remaining <= 0) {
            clearInterval(timer);
            // Timeout occurred
        }
    }, 1000);
}
```

**No UI changes needed** - UI already reads timeout from `prompt_data.timeout_seconds`.

---

### 4. Add Configuration Validation

**File:** `webdashboard/prompt_handler.py`

```python
def _load_config(self, config_file: str) -> dict:
    """Load and validate pipeline configuration"""
    import json
    import os
    
    if not os.path.exists(config_file):
        return {}
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Validate prompt timeout configuration
    if 'prompts' in config:
        default = config['prompts'].get('default_timeout', 300)
        
        # Validate default timeout
        if not isinstance(default, int) or default < 10 or default > 3600:
            raise ValueError(f"Invalid default_timeout: {default} (must be 10-3600 seconds)")
        
        # Validate per-prompt timeouts
        timeouts = config['prompts'].get('timeouts', {})
        for prompt_type, timeout in timeouts.items():
            if not isinstance(timeout, int) or timeout < 10 or timeout > 3600:
                raise ValueError(
                    f"Invalid timeout for {prompt_type}: {timeout} (must be 10-3600 seconds)"
                )
    
    return config
```

---

### 5. Update Tests

**File:** `tests/integration/test_prompt_timeouts.py`

```python
@pytest.mark.asyncio
async def test_configured_timeout_per_prompt_type():
    """Test different timeouts for different prompt types"""
    # Create config with custom timeouts
    config = {
        "prompts": {
            "default_timeout": 300,
            "timeouts": {
                "run_mode": 120,
                "continue": 60
            }
        }
    }
    
    # Save to temp config file
    with open("test_config.json", "w") as f:
        json.dump(config, f)
    
    handler = PromptHandler(config_file="test_config.json")
    
    # Verify timeouts
    assert handler.get_timeout("run_mode") == 120
    assert handler.get_timeout("continue") == 60
    assert handler.get_timeout("pillar_selection") == 300  # default
    assert handler.get_timeout("unknown_type") == 300  # default

@pytest.mark.asyncio
async def test_explicit_timeout_override():
    """Test explicit timeout parameter overrides config"""
    handler = PromptHandler()
    
    # Request with explicit timeout (overrides config)
    future = handler.request_user_input(
        job_id="test_job",
        prompt_type="continue",
        prompt_data={"message": "Continue?"},
        timeout_seconds=30  # Explicit override
    )
    
    # Verify timeout used
    prompt_id = list(handler.pending_prompts.keys())[0]
    assert handler.pending_prompts[prompt_id]['timeout'] == 30

@pytest.mark.asyncio
async def test_invalid_timeout_validation():
    """Test config validation rejects invalid timeouts"""
    config = {
        "prompts": {
            "default_timeout": 5,  # Too short (< 10)
            "timeouts": {
                "run_mode": 5000  # Too long (> 3600)
            }
        }
    }
    
    with open("invalid_config.json", "w") as f:
        json.dump(config, f)
    
    with pytest.raises(ValueError, match="Invalid default_timeout"):
        handler = PromptHandler(config_file="invalid_config.json")

@pytest.mark.asyncio
async def test_ui_receives_correct_timeout():
    """Test UI gets timeout from prompt_data"""
    handler = PromptHandler()
    
    # Mock WebSocket broadcast
    broadcasts = []
    handler.broadcast = lambda data: broadcasts.append(data)
    
    # Request with configured timeout
    handler.request_user_input(
        job_id="test_job",
        prompt_type="continue",
        prompt_data={"message": "Continue?"}
        # Uses config timeout (60s if configured)
    )
    
    # Verify broadcast includes timeout
    assert len(broadcasts) == 1
    assert 'timeout_seconds' in broadcasts[0]['prompt_data']
    assert broadcasts[0]['prompt_data']['timeout_seconds'] == 60  # or configured value
```

---

## Configuration Examples

### Default Configuration

```json
{
  "prompts": {
    "default_timeout": 300,
    "timeouts": {
      "pillar_selection": 300,
      "run_mode": 120,
      "continue": 60,
      "threshold_selection": 180
    }
  }
}
```

### Aggressive Timeouts (Production)

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

### Relaxed Timeouts (Development)

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

---

## Backward Compatibility

### Existing Jobs
```python
# If config not provided, uses 300s default
timeout = prompt_data.get('timeout_seconds', 300)
```

### Migration
- No migration needed
- Existing `pipeline_config.json` without `prompts` section uses 300s default
- Add `prompts` section to enable feature

---

## Documentation Updates

### Update INTERACTIVE_PROMPTS_GUIDE.md

```markdown
## Timeout Configuration

Configure timeout durations per prompt type in `pipeline_config.json`:

```json
{
  "prompts": {
    "default_timeout": 300,
    "timeouts": {
      "pillar_selection": 300,
      "run_mode": 120,
      "continue": 60
    }
  }
}
```

**Timeout Ranges:**
- Minimum: 10 seconds
- Maximum: 3600 seconds (1 hour)
- Default: 300 seconds (5 minutes)

**Recommendations:**
- Simple yes/no prompts: 30-60 seconds
- Binary choices (run_mode): 60-120 seconds
- Complex selections (pillars): 180-300 seconds
```

---

## Testing Plan

### Unit Tests
1. Load config with custom timeouts
2. `get_timeout()` returns correct value per prompt type
3. Fallback to default for unconfigured types
4. Validation rejects invalid timeouts

### Integration Tests
1. Full workflow with configured timeouts
2. Explicit override works
3. UI displays correct countdown
4. Timeout triggers at expected time

### Manual Testing
1. Configure 60s timeout for `continue` prompt
2. Start job, verify countdown shows 1:00
3. Wait 60 seconds, verify auto-cancel
4. Configure 120s for `run_mode`, verify 2:00 countdown

---

## Estimated Breakdown

- **PromptHandler updates:** 30 minutes
  - Config loading: 15 min
  - `get_timeout()` method: 10 min
  - Validation: 5 min
- **Testing:** 20 minutes
- **Documentation:** 10 minutes
- **Total:** 1 hour

---

## Dependencies

**Requires:**
- ✅ `prompt_handler.py` (done in PR #46)
- ✅ `pipeline_config.json` infrastructure

**Synergy:**
- Works with ENHANCE-P5-2 (run_mode/continue prompts) - different timeouts for each
- Complements ENHANCE-P5-3 (Prompt History) - records timeout used

---

## Success Metrics

- [ ] Configurable timeouts work for all prompt types
- [ ] UI countdown reflects configured timeout
- [ ] Validation prevents invalid configs
- [ ] Backward compatible with existing deployments
- [ ] Zero timeout-related bugs
