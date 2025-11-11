# Task Card #13.2 - Error Recovery & Retry Logic

**Priority:** 🟡 HIGH  
**Estimated Effort:** 4-6 hours  
**Risk Level:** MEDIUM  
**Dependencies:** Task Card #13 (Basic Pipeline Orchestrator), Task Card #13.1 (Checkpointing)  
**Wave:** Wave 2

---

## Problem Statement

The basic pipeline orchestrator fails immediately on any error, making it fragile against transient failures like:
- Network timeouts when calling LLM APIs
- Rate limiting / API quota errors
- Temporary file system issues
- Intermittent subprocess crashes

A robust retry system enables:
- Automatic recovery from transient failures
- Exponential backoff to avoid hammering failing services
- Distinguishing permanent vs. temporary errors
- Reduced manual intervention and babysitting

---

## Acceptance Criteria

### Functional Requirements
- [ ] Configurable retry policy per stage (max attempts, backoff)
- [ ] Exponential backoff with jitter for retries
- [ ] Automatic retry on specific error types (timeout, network, rate limit)
- [ ] No retry on permanent errors (syntax errors, missing files)
- [ ] Retry counter persisted in checkpoint
- [ ] Clear logging of retry attempts and reasons

### Non-Functional Requirements
- [ ] Max retry delay configurable (default: 60s)
- [ ] Total retry time doesn't exceed stage timeout
- [ ] Backward compatible with v1.0 config (retry is opt-in)
- [ ] Retry logic doesn't mask real errors

### Safety
- [ ] Circuit breaker: stop retrying if 3+ consecutive failures
- [ ] Exponential backoff prevents API hammering
- [ ] Logs clearly distinguish retry attempts from new runs

---

## Design Contract

**Inputs:**
- Retry configuration in `pipeline_config.json`
- Stage execution result (exit code, stderr)
- Checkpoint data (previous retry attempts)

**Outputs:**
- Retry decision (retry/fail)
- Updated checkpoint with retry count
- Backoff delay calculation

**Error Classification:**
- **Retryable:** Network errors, timeouts, rate limits, transient API errors
- **Non-Retryable:** Syntax errors, file not found, invalid config, logic errors

**Success:**
- Transient failures automatically recovered
- No infinite retry loops
- Clear audit trail of retry attempts

---

## Edge Cases

1. **Retry during pipeline resume** - Don't double-count previous attempts
2. **Timeout during backoff delay** - Don't exceed total stage timeout
3. **Error classification ambiguity** - Conservative retry policy
4. **Concurrent API failures** - Respect global rate limits
5. **Infinite retry loop** - Circuit breaker activation
6. **Manual intervention** - Allow user to skip retries

---

## Implementation Guide

### 1. Retry Configuration Schema

**Add to `pipeline_config.json`:**

```json
{
  "version": "1.2.0",
  "retry_policy": {
    "enabled": true,
    "default_max_attempts": 3,
    "default_backoff_base": 2,
    "default_backoff_max": 60,
    "circuit_breaker_threshold": 3,
    "per_stage": {
      "journal_reviewer": {
        "max_attempts": 5,
        "backoff_base": 2,
        "backoff_max": 120,
        "retryable_patterns": [
          "timeout",
          "rate limit",
          "connection error",
          "temporary failure"
        ]
      },
      "sync": {
        "max_attempts": 3,
        "backoff_base": 1.5,
        "backoff_max": 30
      }
    }
  },
  "stage_timeout": 7200
}
```

### 2. Code Changes to `pipeline_orchestrator.py`

**Add retry logic class:**

```python
import time
import random
import re
from typing import List, Tuple, Optional

class RetryPolicy:
    """Manages retry logic and exponential backoff."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('retry_policy', {})
        self.enabled = self.config.get('enabled', True)
        self.default_max_attempts = self.config.get('default_max_attempts', 3)
        self.default_backoff_base = self.config.get('default_backoff_base', 2)
        self.default_backoff_max = self.config.get('default_backoff_max', 60)
        self.circuit_breaker_threshold = self.config.get('circuit_breaker_threshold', 3)
        self.consecutive_failures = 0
    
    def get_stage_config(self, stage_name: str) -> Dict[str, Any]:
        """Get retry config for specific stage."""
        per_stage = self.config.get('per_stage', {})
        stage_config = per_stage.get(stage_name, {})
        
        return {
            'max_attempts': stage_config.get('max_attempts', self.default_max_attempts),
            'backoff_base': stage_config.get('backoff_base', self.default_backoff_base),
            'backoff_max': stage_config.get('backoff_max', self.default_backoff_max),
            'retryable_patterns': stage_config.get('retryable_patterns', [
                'timeout', 'connection', 'rate limit', 'temporary'
            ])
        }
    
    def is_retryable_error(self, stderr: str, stage_name: str) -> Tuple[bool, str]:
        """
        Classify error as retryable or permanent.
        
        Returns:
            (is_retryable, reason)
        """
        if not self.enabled:
            return False, "Retry disabled"
        
        # Circuit breaker check
        if self.consecutive_failures >= self.circuit_breaker_threshold:
            return False, f"Circuit breaker tripped ({self.consecutive_failures} failures)"
        
        stderr_lower = stderr.lower()
        stage_config = self.get_stage_config(stage_name)
        retryable_patterns = stage_config['retryable_patterns']
        
        # Check for retryable patterns
        for pattern in retryable_patterns:
            if re.search(pattern, stderr_lower, re.IGNORECASE):
                return True, f"Matched pattern: {pattern}"
        
        # Check for common retryable error types
        retryable_keywords = [
            'timeout', 'timed out', 'time out',
            'connection refused', 'connection reset', 'connection error',
            'rate limit', 'too many requests', '429',
            'temporary failure', 'transient',
            'network error', 'network unreachable',
            'service unavailable', '503', '502', '504'
        ]
        
        for keyword in retryable_keywords:
            if keyword in stderr_lower:
                return True, f"Retryable error: {keyword}"
        
        # Non-retryable errors (permanent)
        permanent_keywords = [
            'syntax error', 'name error', 'type error',
            'file not found', 'no such file',
            'invalid', 'parse error',
            'attribute error', 'import error',
            'permission denied', '401', '403'
        ]
        
        for keyword in permanent_keywords:
            if keyword in stderr_lower:
                return False, f"Permanent error: {keyword}"
        
        # Default: don't retry unknown errors (conservative)
        return False, "Unknown error type (conservative: no retry)"
    
    def calculate_backoff(self, attempt: int, stage_name: str) -> float:
        """
        Calculate exponential backoff delay with jitter.
        
        Args:
            attempt: Current attempt number (1-indexed)
            stage_name: Name of stage for config lookup
        
        Returns:
            Delay in seconds
        """
        stage_config = self.get_stage_config(stage_name)
        base = stage_config['backoff_base']
        max_delay = stage_config['backoff_max']
        
        # Exponential backoff: base^(attempt-1)
        delay = base ** (attempt - 1)
        
        # Cap at max delay
        delay = min(delay, max_delay)
        
        # Add jitter (±20%)
        jitter = delay * 0.2 * (random.random() * 2 - 1)
        delay += jitter
        
        return max(1, delay)  # Minimum 1 second
    
    def should_retry(self, attempt: int, stage_name: str, stderr: str) -> Tuple[bool, str, float]:
        """
        Determine if stage should be retried.
        
        Returns:
            (should_retry, reason, backoff_delay)
        """
        stage_config = self.get_stage_config(stage_name)
        max_attempts = stage_config['max_attempts']
        
        # Check if max attempts exceeded
        if attempt >= max_attempts:
            return False, f"Max attempts ({max_attempts}) reached", 0
        
        # Check if error is retryable
        is_retryable, reason = self.is_retryable_error(stderr, stage_name)
        if not is_retryable:
            return False, reason, 0
        
        # Calculate backoff
        backoff = self.calculate_backoff(attempt, stage_name)
        
        return True, f"Retrying: {reason}", backoff
    
    def record_failure(self):
        """Record a failure for circuit breaker."""
        self.consecutive_failures += 1
    
    def record_success(self):
        """Record a success, resetting circuit breaker."""
        self.consecutive_failures = 0
```

**Update `PipelineOrchestrator` class:**

```python
class PipelineOrchestrator:
    def __init__(self, log_file: Optional[str] = None, config: Optional[Dict[str, Any]] = None,
                 checkpoint_file: Optional[str] = None, resume: bool = False,
                 resume_from: Optional[str] = None):
        self.log_file = log_file
        self.config = config or {}
        self.start_time = datetime.now()
        self.checkpoint_file = checkpoint_file or 'pipeline_checkpoint.json'
        self.resume = resume
        self.resume_from = resume_from
        self.run_id = self._generate_run_id()
        self.checkpoint_data = self._load_or_create_checkpoint()
        
        # NEW: Initialize retry policy
        self.retry_policy = RetryPolicy(self.config)
    
    def _mark_stage_retry(self, stage_name: str, attempt: int, error: str, next_delay: float):
        """Mark retry attempt in checkpoint."""
        if "retry_history" not in self.checkpoint_data["stages"][stage_name]:
            self.checkpoint_data["stages"][stage_name]["retry_history"] = []
        
        self.checkpoint_data["stages"][stage_name]["retry_history"].append({
            "attempt": attempt,
            "failed_at": datetime.now().isoformat(),
            "error": error[:200],  # Truncate
            "next_retry_delay": next_delay
        })
        
        self.checkpoint_data["stages"][stage_name].update({
            "status": "retrying",
            "current_attempt": attempt,
            "last_error": error[:200]
        })
        
        self._write_checkpoint()
    
    def run_stage(self, stage_name: str, script: str, description: str, 
                  required: bool = True) -> bool:
        """
        Run a pipeline stage with retry support.
        
        Args:
            stage_name: Unique stage identifier
            script: Python script to run
            description: Human-readable stage description
            required: If True, exit on failure; if False, continue
        
        Returns:
            True if successful, False otherwise
        """
        # Check if stage should run based on checkpoint
        if not self._should_run_stage(stage_name):
            return True  # Already completed
        
        # Get retry state from checkpoint
        stage_data = self.checkpoint_data.get("stages", {}).get(stage_name, {})
        current_attempt = stage_data.get("current_attempt", 0)
        
        # Get retry config
        stage_config = self.retry_policy.get_stage_config(stage_name)
        max_attempts = stage_config['max_attempts']
        
        # Attempt loop
        for attempt in range(current_attempt + 1, max_attempts + 1):
            self.log(f"Starting stage: {description} (attempt {attempt}/{max_attempts})", "INFO")
            self._mark_stage_started(stage_name)
            
            stage_start = datetime.now()
            
            try:
                result = subprocess.run(
                    [sys.executable, script],
                    capture_output=True,
                    text=True,
                    timeout=self.config.get('stage_timeout', 3600)
                )
                
                duration = (datetime.now() - stage_start).total_seconds()
                
                if result.returncode == 0:
                    self.log(f"✅ Stage complete: {description}", "SUCCESS")
                    self._mark_stage_completed(stage_name, duration, result.returncode)
                    self.retry_policy.record_success()
                    return True
                else:
                    # Stage failed - check if retryable
                    self.log(f"❌ Stage failed: {description} (attempt {attempt})", "ERROR")
                    self.log(f"Error output:\n{result.stderr}", "ERROR")
                    
                    # Determine if should retry
                    should_retry, retry_reason, backoff_delay = self.retry_policy.should_retry(
                        attempt, stage_name, result.stderr
                    )
                    
                    if should_retry:
                        self.log(f"🔄 {retry_reason} - waiting {backoff_delay:.1f}s before retry", "WARNING")
                        self._mark_stage_retry(stage_name, attempt, result.stderr, backoff_delay)
                        self.retry_policy.record_failure()
                        
                        # Wait before retry
                        time.sleep(backoff_delay)
                        continue  # Retry
                    else:
                        # Don't retry
                        self.log(f"🚫 Not retrying: {retry_reason}", "ERROR")
                        self._mark_stage_failed(stage_name, result.stderr[:500])
                        
                        if required:
                            self.log("Pipeline halted due to required stage failure", "ERROR")
                            sys.exit(1)
                        return False
                        
            except subprocess.TimeoutExpired:
                self.log(f"⏱️ Stage timeout: {description} (attempt {attempt})", "ERROR")
                
                # Timeout is usually retryable
                should_retry, retry_reason, backoff_delay = self.retry_policy.should_retry(
                    attempt, stage_name, "timeout"
                )
                
                if should_retry:
                    self.log(f"🔄 {retry_reason} - waiting {backoff_delay:.1f}s before retry", "WARNING")
                    self._mark_stage_retry(stage_name, attempt, "Timeout", backoff_delay)
                    time.sleep(backoff_delay)
                    continue
                else:
                    self._mark_stage_failed(stage_name, "Timeout exceeded")
                    if required:
                        sys.exit(1)
                    return False
                    
            except Exception as e:
                self.log(f"💥 Stage exception: {description} - {e}", "ERROR")
                self._mark_stage_failed(stage_name, str(e))
                if required:
                    sys.exit(1)
                return False
        
        # Max attempts exceeded
        self.log(f"🛑 Max retry attempts ({max_attempts}) exceeded for {description}", "ERROR")
        self._mark_stage_failed(stage_name, f"Failed after {max_attempts} attempts")
        
        if required:
            self.log("Pipeline halted due to required stage failure", "ERROR")
            sys.exit(1)
        
        return False
```

### 3. Checkpoint Schema Update

**Updated checkpoint with retry history:**

```json
{
  "run_id": "2025-11-11T15:00:00_xyz789",
  "pipeline_version": "1.2.0",
  "started_at": "2025-11-11T15:00:00",
  "last_updated": "2025-11-11T15:10:45",
  "status": "in_progress",
  "stages": {
    "journal_reviewer": {
      "status": "retrying",
      "current_attempt": 2,
      "started_at": "2025-11-11T15:00:05",
      "last_error": "Connection timeout after 30s",
      "retry_history": [
        {
          "attempt": 1,
          "failed_at": "2025-11-11T15:05:00",
          "error": "Connection timeout",
          "next_retry_delay": 2.0
        },
        {
          "attempt": 2,
          "failed_at": "2025-11-11T15:10:30",
          "error": "Rate limit exceeded",
          "next_retry_delay": 4.5
        }
      ]
    },
    "judge": {
      "status": "not_started"
    }
  },
  "config": {
    "retry_policy": {
      "enabled": true,
      "default_max_attempts": 3
    }
  }
}
```

---

## Usage Examples

### Enable Retry (Default Config)
```bash
python pipeline_orchestrator.py --config pipeline_config.json
# Uses retry policy from config
```

### Disable Retry
```json
{
  "retry_policy": {
    "enabled": false
  }
}
```

### Custom Retry Per Stage
```json
{
  "retry_policy": {
    "per_stage": {
      "journal_reviewer": {
        "max_attempts": 5,
        "backoff_base": 2,
        "backoff_max": 120,
        "retryable_patterns": ["timeout", "rate limit"]
      }
    }
  }
}
```

### View Retry History
```bash
cat pipeline_checkpoint.json | jq '.stages.journal_reviewer.retry_history'
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/automation/test_retry_policy.py`

```python
import pytest
from pipeline_orchestrator import RetryPolicy

class TestRetryPolicy:
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        config = {
            'retry_policy': {
                'default_backoff_base': 2,
                'default_backoff_max': 60
            }
        }
        policy = RetryPolicy(config)
        
        # Attempt 1: 2^0 = 1s (+ jitter)
        delay1 = policy.calculate_backoff(1, 'test_stage')
        assert 0.8 <= delay1 <= 1.2
        
        # Attempt 2: 2^1 = 2s (+ jitter)
        delay2 = policy.calculate_backoff(2, 'test_stage')
        assert 1.6 <= delay2 <= 2.4
        
        # Attempt 3: 2^2 = 4s (+ jitter)
        delay3 = policy.calculate_backoff(3, 'test_stage')
        assert 3.2 <= delay3 <= 4.8
        
        # Attempt 10: capped at max_delay (60s)
        delay10 = policy.calculate_backoff(10, 'test_stage')
        assert delay10 <= 60 * 1.2  # Max + jitter
    
    def test_error_classification_retryable(self):
        """Test that retryable errors are identified."""
        policy = RetryPolicy({'retry_policy': {'enabled': True}})
        
        # Retryable errors
        assert policy.is_retryable_error("Connection timeout", "test")[0] == True
        assert policy.is_retryable_error("Rate limit exceeded", "test")[0] == True
        assert policy.is_retryable_error("Network error occurred", "test")[0] == True
        assert policy.is_retryable_error("HTTP 503 Service Unavailable", "test")[0] == True
    
    def test_error_classification_permanent(self):
        """Test that permanent errors are not retried."""
        policy = RetryPolicy({'retry_policy': {'enabled': True}})
        
        # Permanent errors
        assert policy.is_retryable_error("SyntaxError: invalid syntax", "test")[0] == False
        assert policy.is_retryable_error("FileNotFoundError: file.json", "test")[0] == False
        assert policy.is_retryable_error("NameError: 'x' is not defined", "test")[0] == False
        assert policy.is_retryable_error("HTTP 401 Unauthorized", "test")[0] == False
    
    def test_circuit_breaker(self):
        """Test circuit breaker stops retries after threshold."""
        config = {
            'retry_policy': {
                'enabled': True,
                'circuit_breaker_threshold': 3
            }
        }
        policy = RetryPolicy(config)
        
        # First 3 failures
        policy.record_failure()
        policy.record_failure()
        policy.record_failure()
        
        # Should not retry after circuit breaker trips
        is_retryable, reason = policy.is_retryable_error("Connection timeout", "test")
        assert is_retryable == False
        assert "circuit breaker" in reason.lower()
    
    def test_max_attempts_exceeded(self):
        """Test that max attempts limit is enforced."""
        config = {
            'retry_policy': {
                'default_max_attempts': 3
            }
        }
        policy = RetryPolicy(config)
        
        # Attempt 3 (max is 3)
        should_retry, reason, delay = policy.should_retry(3, 'test', 'timeout')
        assert should_retry == False
        assert "max attempts" in reason.lower()
```

### Integration Tests

**File:** `tests/integration/test_retry_integration.py`

```python
@pytest.mark.integration
def test_retry_on_transient_failure(integration_temp_workspace):
    """Test that pipeline retries transient failures."""
    # TODO: Create mock script that fails twice then succeeds
    # Run orchestrator with retry enabled
    # Verify 3 attempts made (2 failures + 1 success)
    # Verify checkpoint shows retry history
```

### Simulation Testing

**Create test script:** `tests/mock_scripts/flaky_script.py`

```python
import sys
import random

# Simulate flaky behavior (fails 50% of time)
if random.random() < 0.5:
    print("Simulated transient failure: Connection timeout", file=sys.stderr)
    sys.exit(1)
else:
    print("Success!")
    sys.exit(0)
```

**Test command:**

```bash
# Configure retry for flaky stage
cat > test_retry_config.json << EOF
{
  "retry_policy": {
    "enabled": true,
    "default_max_attempts": 5,
    "default_backoff_base": 1.5
  }
}
EOF

# Run with flaky script - should eventually succeed
python pipeline_orchestrator.py --config test_retry_config.json
```

---

## Success Criteria

### Functional
- [ ] Pipeline automatically retries on timeout/network errors
- [ ] Exponential backoff prevents API hammering
- [ ] Permanent errors (syntax, file not found) don't retry
- [ ] Circuit breaker prevents infinite loops
- [ ] Retry history persisted in checkpoint

### Performance
- [ ] Backoff calculation <1ms
- [ ] No retry delay for permanent errors
- [ ] Total retry time respects stage timeout

### Reliability
- [ ] Max 3 consecutive retries without circuit breaker trip
- [ ] Retry state survives pipeline restart
- [ ] Clear logs distinguish retry vs new attempt

### Usability
- [ ] Config schema is self-documenting
- [ ] Error messages explain why retry/no-retry
- [ ] Checkpoint shows full retry history for debugging

---

## Documentation Updates

### Update `README.md`

```markdown
### Retry Configuration

Configure automatic retry for transient failures:

\`\`\`json
{
  "retry_policy": {
    "enabled": true,
    "default_max_attempts": 3,
    "default_backoff_base": 2,
    "per_stage": {
      "journal_reviewer": {
        "max_attempts": 5,
        "backoff_base": 2
      }
    }
  }
}
\`\`\`

Disable retry:

\`\`\`json
{
  "retry_policy": {
    "enabled": false
  }
}
\`\`\`
```

### Update `WORKFLOW_EXECUTION_GUIDE.md`

Add section on retry behavior, error classification, and debugging failed retries.

---

## Rollout Plan

1. **Development:** Implement retry logic (4-6 hours)
2. **Testing:** Unit + integration + simulation (3 hours)
3. **Documentation:** Update README and guide (1 hour)
4. **Code Review:** Submit PR for review
5. **Merge:** Merge to main after approval
6. **Validation:** Test with real LLM API rate limits

---

## Estimated Lines of Code

- RetryPolicy class: ~200 lines
- PipelineOrchestrator updates: ~100 lines
- Tests: ~150 lines
- Documentation: ~50 lines
- **Total: ~500 lines**

---

## Notes

- Error classification is conservative (unknown errors = don't retry)
- Circuit breaker prevents runaway costs on persistent API failures
- Jitter prevents thundering herd when multiple pipelines retry simultaneously
- Retry history in checkpoint enables post-mortem analysis
- Future enhancement: Adaptive retry based on error frequency
- Consider adding `--force-retry` flag to override circuit breaker

---

**Task Card Status:** ✅ Ready for Implementation  
**Next Step:** Begin implementation after Task Card #13.1 (checkpointing) is complete  
**Integration Point:** Works with Task Card #13.1 (checkpoint system stores retry state)
