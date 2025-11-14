# Pipeline Orchestrator v2.0 - Advanced Features Documentation

## Overview

The Pipeline Orchestrator v2.0 introduces production-ready features for running the literature review pipeline at scale with enhanced reliability, observability, and performance.

### Key Features

1. **Dry-run Mode** - Validate pipeline configuration without executing stages
2. **Smart Error Classification** - Distinguish transient vs permanent errors for intelligent retry
3. **API Quota Management** - Token bucket rate limiting to prevent API throttling
4. **Parallel Processing** - Process multiple papers concurrently (experimental, feature-flagged)
5. **Enhanced Checkpointing** - Per-paper tracking with atomic writes and thread-safety
6. **Retry with Backoff** - Exponential backoff with jitter for failed operations

## Installation

No additional dependencies required beyond the base requirements:

```bash
pip install -r requirements-dev.txt
```

## Quick Start

### Basic Usage (v1.x Compatible)

```bash
# Run full pipeline
python pipeline_orchestrator.py

# With custom config
python pipeline_orchestrator.py --config pipeline_config.json

# Resume from checkpoint
python pipeline_orchestrator.py --resume

# Resume from specific stage
python pipeline_orchestrator.py --resume-from judge
```

### New v2.0 Features

```bash
# Dry-run mode (validate without execution)
python pipeline_orchestrator.py --dry-run

# Enable experimental features
python pipeline_orchestrator.py --enable-experimental

# Combine dry-run with config
python pipeline_orchestrator.py --dry-run --config pipeline_config.json
```

## Feature Details

### 1. Dry-run Mode

**Purpose**: Validate pipeline configuration and dependencies without executing actual stages.

**Usage**:
```bash
python pipeline_orchestrator.py --dry-run
```

**What it does**:
- Validates all pipeline stages are configured correctly
- Simulates execution flow
- Creates checkpoint file for review
- Reports estimated execution path
- **Does NOT** call external APIs or modify databases

**Output Example**:
```
[2025-11-14 03:16:29] [WARNING] DRY-RUN MODE ENABLED
[2025-11-14 03:16:29] [INFO] [DRY-RUN] Would execute: literature_review.reviewers.journal_reviewer
[2025-11-14 03:16:29] [SUCCESS] ✅ Stage validated: Stage 1: Initial Paper Review
...
[2025-11-14 03:16:29] [SUCCESS] 🎉 Pipeline Complete!
```

**Use Cases**:
- Testing configuration changes
- Validating pipeline flow before production run
- CI/CD integration testing
- Training and documentation

### 2. Smart Error Classification

**Purpose**: Automatically classify errors as transient (retryable) or permanent (fail fast).

**How it works**:
- Analyzes error messages and HTTP status codes
- Classifies as:
  - **Transient**: Timeouts, rate limits, network errors, 429/503/504
  - **Permanent**: Syntax errors, authentication failures, 401/403/404
  - **Unknown**: Conservative fallback (no retry)

**Code Example**:
```python
from literature_review.pipeline.orchestrator_v2 import ErrorClassifier

# Classify an error
error_type = ErrorClassifier.classify_error("Connection timeout", http_status=429)
# Returns: ErrorType.TRANSIENT

should_retry = ErrorClassifier.should_retry("File not found")
# Returns: False (permanent error)
```

**Configuration**:
Integrated automatically with retry policy. No additional configuration needed.

### 3. API Quota Management

**Purpose**: Prevent API rate limit violations through token bucket rate limiting.

**How it works**:
- Token bucket algorithm with configurable rate
- Thread-safe for concurrent operations
- Automatic token refill over time
- Blocks when quota exceeded (configurable wait vs fail)

**Code Example**:
```python
from literature_review.pipeline.orchestrator_v2 import SimpleQuotaManager

# Create quota manager (60 requests per 60 seconds)
quota = SimpleQuotaManager(rate=60, per_seconds=60)

# Consume quota before API call
quota.consume(tokens=1, wait=True)  # Blocks if quota exceeded
# Make API call...

# Get statistics
stats = quota.get_stats()
print(f"Consumed: {stats['consumed_count']}, Throttled: {stats['throttle_count']}")
```

**Configuration** (`pipeline_config.json`):
```json
{
  "v2_features": {
    "quota": {
      "gemini_api": {
        "rate": 60,
        "per_seconds": 60
      }
    }
  }
}
```

### 4. Enhanced Checkpointing

**Purpose**: Track per-paper progress with atomic writes and thread-safety.

**Features**:
- Per-paper status tracking
- Atomic file writes (no corruption on crash)
- Thread-safe for concurrent access
- Retry count tracking
- Error history
- Dry-run support

**Checkpoint File Format**:
```json
{
  "run_id": "2025-11-14T03:16:29_abc123",
  "version": "2.0.0",
  "created_at": "2025-11-14T03:16:29",
  "last_updated": "2025-11-14T03:20:45",
  "papers": {
    "paper_0001.pdf": {
      "stage": "completed",
      "stages": {
        "journal_reviewer": "2025-11-14T03:17:00",
        "judge": "2025-11-14T03:19:30"
      },
      "retries": 0,
      "started_at": "2025-11-14T03:16:30",
      "completed_at": "2025-11-14T03:19:30"
    },
    "paper_0002.pdf": {
      "stage": "in_progress",
      "stages": {
        "journal_reviewer": "2025-11-14T03:17:15"
      },
      "retries": 1,
      "last_error": "Connection timeout"
    }
  },
  "stats": {
    "total_papers": 2,
    "completed_papers": 1,
    "failed_papers": 0,
    "retries": 1
  }
}
```

**Code Example**:
```python
from literature_review.pipeline.orchestrator_v2 import CheckpointManagerV2

# Create checkpoint manager
checkpoint = CheckpointManagerV2('checkpoint.json', dry_run=False)

# Update paper status
checkpoint.update_paper_status(
    paper_id='paper_0001.pdf',
    stage='in_progress',
    stages_completed=['journal_reviewer']
)

# Increment retry count
checkpoint.increment_retries('paper_0001.pdf')

# Get incomplete papers
incomplete = checkpoint.get_incomplete_papers()
```

### 5. Retry with Exponential Backoff

**Purpose**: Automatically retry failed operations with intelligent backoff.

**Features**:
- Configurable max attempts
- Exponential backoff: delay = base^(attempt-1)
- Random jitter (±20%) to prevent thundering herd
- Max delay cap
- Smart error classification integration

**Code Example**:
```python
from literature_review.pipeline.orchestrator_v2 import RetryHelper, ErrorClassifier

def api_call():
    # Your API call here
    response = call_external_api()
    return response

# Retry with backoff
result = RetryHelper.retry_with_backoff(
    func=api_call,
    attempts=3,
    base=0.5,
    factor=2.0,
    max_delay=60.0,
    jitter=True,
    error_classifier=ErrorClassifier
)
```

**Retry Schedule Example**:
- Attempt 1: Immediate
- Attempt 2: 0.5s + jitter
- Attempt 3: 1.0s + jitter
- Attempt 4: 2.0s + jitter
- (capped at max_delay)

**Configuration** (`pipeline_config.json`):
```json
{
  "v2_features": {
    "retry": {
      "attempts": 3,
      "base": 0.5,
      "factor": 2.0,
      "max_delay": 60.0,
      "enable_jitter": true
    }
  }
}
```

### 6. Parallel Processing (Experimental)

⚠️ **WARNING**: Experimental feature, disabled by default. Enable with caution.

**Purpose**: Process multiple papers concurrently for improved throughput.

**Features**:
- ThreadPoolExecutor for IO-bound operations
- Configurable worker count
- Integrated quota management
- Per-paper checkpoint tracking
- Dry-run support

**Enable**:
```bash
python pipeline_orchestrator.py --enable-experimental
```

Or in config:
```json
{
  "v2_features": {
    "max_workers": 4,
    "feature_flags": {
      "enable_parallel_processing": true
    }
  }
}
```

**Code Example**:
```python
from literature_review.pipeline.orchestrator_v2 import (
    ParallelPipelineCoordinator,
    SimpleQuotaManager,
    CheckpointManagerV2
)

# Setup
quota = SimpleQuotaManager(rate=60, per_seconds=60)
checkpoint = CheckpointManagerV2('checkpoint.json')

coordinator = ParallelPipelineCoordinator(
    max_workers=4,
    quota_manager=quota,
    checkpoint_manager=checkpoint
)

# Define paper processing function
def process_paper(paper_path):
    # Process single paper through all stages
    return {
        'paper': paper_path,
        'status': 'success',
        'stages_completed': ['journal_reviewer', 'judge']
    }

# Process papers in parallel
papers = ['paper1.pdf', 'paper2.pdf', 'paper3.pdf', 'paper4.pdf']
results = coordinator.process_papers_parallel(papers, process_paper)

# Get statistics
stats = coordinator.get_stats()
print(f"Successful: {stats['successful']}, Failed: {stats['failed']}")
```

**Safety Considerations**:
- Only enable after thorough testing (INT-001/INT-003)
- Start with low worker count (2-4)
- Monitor for race conditions
- Ensure idempotent stages
- Watch API rate limits

## Configuration Reference

### Complete `pipeline_config.json` v2.0 Schema

```json
{
  "version": "2.0.0",
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
        "backoff_max": 120
      }
    }
  },
  
  "v2_features": {
    "max_workers": 4,
    "enable_parallel": false,
    "checkpoint_file": "pipeline_checkpoint.json",
    
    "retry": {
      "attempts": 3,
      "base": 0.5,
      "factor": 2.0,
      "max_delay": 60.0,
      "enable_jitter": true
    },
    
    "quota": {
      "gemini_api": {
        "rate": 60,
        "per_seconds": 60
      }
    },
    
    "feature_flags": {
      "enable_parallel_processing": false,
      "enable_quota_management": true,
      "enable_smart_retry": true
    }
  }
}
```

## Testing

### Run All Tests

```bash
# Unit tests
python -m pytest tests/unit/test_orchestrator_v2.py -v

# Integration tests
python -m pytest tests/integration/test_orchestrator_v2_integration.py -v

# CLI tests
python -m pytest tests/integration/test_orchestrator_cli.py -v

# All tests
python -m pytest tests/ -v -m "not requires_api"
```

### Test Coverage

- Unit tests: 38 tests, 93.4% coverage
- Integration tests: 12 tests
- CLI tests: 5 tests
- Backward compatibility: 12 tests
- **Total: 67 tests passing**

## Troubleshooting

### Common Issues

**Issue**: "FileNotFoundError: checkpoint.tmp"
- **Solution**: Ensure checkpoint directory exists and is writable

**Issue**: Rate limit errors despite quota management
- **Solution**: Reduce `max_workers` or decrease `quota.rate`

**Issue**: Dry-run mode not activating
- **Solution**: Ensure `--dry-run` flag is used OR `dry_run: true` in config

**Issue**: Experimental features not working
- **Solution**: Use `--enable-experimental` flag OR enable in config

### Debug Mode

Enable verbose logging:
```bash
python pipeline_orchestrator.py --log-file debug.log --dry-run
```

## Migration Guide

### Upgrading from v1.x to v2.0

1. **Backup** existing checkpoint files
2. **Test** with dry-run mode:
   ```bash
   python pipeline_orchestrator.py --dry-run
   ```
3. **Review** configuration changes
4. **Run** in production (v2.0 is backward compatible)

### Backward Compatibility

All v1.x commands work unchanged:
```bash
# These still work as before
python pipeline_orchestrator.py
python pipeline_orchestrator.py --resume
python pipeline_orchestrator.py --config pipeline_config.json
```

## Performance Tips

1. **Use dry-run** for configuration validation
2. **Start with sequential** processing (parallel disabled)
3. **Monitor quota usage** before enabling parallel
4. **Incremental rollout** of experimental features
5. **Enable smart retry** for flaky APIs

## Roadmap

Future enhancements:
- [ ] ProcessPoolExecutor for CPU-bound operations
- [ ] Distributed checkpointing (Redis/S3)
- [ ] Real-time metrics dashboard
- [ ] Auto-scaling based on queue depth
- [ ] Advanced scheduling (priority queues)

## Support

For issues or questions:
1. Check test examples in `tests/integration/test_orchestrator_v2_integration.py`
2. Review error messages and logs
3. Enable dry-run mode for debugging
4. Consult code documentation in `literature_review/pipeline/orchestrator_v2.py`

## License

Same as parent project (see LICENSE file).
