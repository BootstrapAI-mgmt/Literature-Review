# Literature Review Automation System

Automated pipeline for conducting comprehensive literature reviews in neuromorphic computing research.

## Quick Start

### Automated Pipeline (Recommended)

Run the full 5-stage pipeline with a single command:

```bash
python pipeline_orchestrator.py
```

**With logging:**
```bash
python pipeline_orchestrator.py --log-file pipeline.log
```

**With custom configuration:**
```bash
python pipeline_orchestrator.py --config pipeline_config.json
```

**Resume from checkpoint:**
```bash
python pipeline_orchestrator.py --resume
```

**Resume from specific stage:**
```bash
python pipeline_orchestrator.py --resume-from judge
```

### Manual Execution

For step-by-step control, run each stage individually:

```bash
# Stage 1: Initial paper review
python Journal-Reviewer.py

# Stage 2: Judge claims
python Judge.py

# Stage 3: Deep requirements analysis (if rejections exist)
python DeepRequirementsAnalyzer.py
python Judge.py  # Re-judge DRA claims

# Stage 4: Sync to database
python sync_history_to_db.py

# Stage 5: Gap analysis and convergence
python Orchestrator.py
```

## Pipeline Stages

1. **Journal-Reviewer**: Screen papers and extract claims
2. **Judge**: Evaluate claims against requirements
3. **DeepRequirementsAnalyzer (DRA)**: Re-analyze rejected claims (conditional)
4. **Sync**: Update CSV database from version history
5. **Orchestrator**: Identify gaps and drive convergence

## Configuration

Create a `pipeline_config.json` file:

```json
{
  "version": "1.2.0",
  "version_history_path": "review_version_history.json",
  "stage_timeout": 7200,
  "log_level": "INFO",
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
        "retryable_patterns": ["timeout", "rate limit", "connection error"]
      }
    }
  }
}
```

### Retry Configuration

The pipeline automatically retries transient failures like network timeouts and rate limits:

**Enable retry (default):**
```json
{
  "retry_policy": {
    "enabled": true,
    "default_max_attempts": 3
  }
}
```

**Disable retry:**
```json
{
  "retry_policy": {
    "enabled": false
  }
}
```

**Custom retry per stage:**
```json
{
  "retry_policy": {
    "per_stage": {
      "journal_reviewer": {
        "max_attempts": 5,
        "backoff_base": 2,
        "backoff_max": 120
      }
    }
  }
}
```

**Retryable errors:**
- Network timeouts and connection errors
- Rate limiting (429, "too many requests")
- Service unavailable (503, 502, 504)
- Temporary failures

**Non-retryable errors:**
- Syntax errors, import errors
- File not found
- Permission denied (401, 403)
- Invalid configuration

## Requirements

```bash
pip install -r requirements-dev.txt
```

Create a `.env` file with your API key:
```
GEMINI_API_KEY=your_api_key_here
```

## Documentation

- **[WORKFLOW_EXECUTION_GUIDE.md](WORKFLOW_EXECUTION_GUIDE.md)**: Detailed workflow documentation
- **[ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md)**: System architecture
- **[TESTING_STATUS_SUMMARY.md](TESTING_STATUS_SUMMARY.md)**: Test coverage and status

## Pipeline Orchestrator Features

- ✅ **Automated Execution**: Runs all 5 stages sequentially
- ✅ **Conditional DRA**: Only runs when rejections are detected
- ✅ **Progress Logging**: Timestamps and status for each stage
- ✅ **Error Handling**: Halts on failure with clear error messages
- ✅ **Configurable**: Customizable timeouts and paths
- ✅ **Checkpoint/Resume**: Resume from interruption points
- ✅ **Automatic Retry**: Retry transient failures with exponential backoff
- ✅ **Circuit Breaker**: Prevents infinite retry loops
- ✅ **Retry History**: Track all retry attempts in checkpoint file

### Checkpoint & Resume

The pipeline creates a `pipeline_checkpoint.json` file to track progress. If a pipeline fails, you can resume from the last successful stage:

```bash
# Resume from last checkpoint
python pipeline_orchestrator.py --resume

# Resume from specific stage
python pipeline_orchestrator.py --resume-from sync
```

**View checkpoint status:**
```bash
cat pipeline_checkpoint.json | jq '.stages'
```

**View retry history:**
```bash
cat pipeline_checkpoint.json | jq '.stages.journal_reviewer.retry_history'
```

### Error Recovery

The pipeline automatically retries transient failures:

1. **Network Timeout** → Retry with exponential backoff
2. **Rate Limit** → Wait and retry with increasing delays
3. **Syntax Error** → Fail immediately (no retry)
4. **Circuit Breaker** → Stop after 3 consecutive failures

**Example retry flow:**
- Attempt 1: Fails with "Connection timeout" → Wait 2s, retry
- Attempt 2: Fails with "Rate limit" → Wait 4s, retry
- Attempt 3: Succeeds → Continue to next stage

## Testing

Run the test suite:

```bash
pytest
```

Run specific test categories:

```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
```

## License

See [LICENSE](LICENSE) file for details.
