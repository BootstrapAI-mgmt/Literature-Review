# Orchestrator State Manager

## Overview

The StateManager provides a robust, versioned state management system for the gap analysis orchestrator. It tracks:

- **Gap metrics**: Which gaps exist and how they're evolving over time
- **Job lineage**: Parent-child relationships for incremental analysis runs
- **Execution metrics**: API costs, duration, cache efficiency
- **Coverage data**: Per-pillar completeness tracking

## Features

✅ **Schema Versioning**: Automatic v1→v2 migration with backward compatibility  
✅ **Atomic Operations**: Safe concurrent reads, atomic writes via temp file + rename  
✅ **Gap Tracking**: Detailed tracking of coverage gaps for targeted improvements  
✅ **Job Genealogy**: Parent-child job relationships for incremental workflows  
✅ **Comprehensive Testing**: 19 unit and integration tests

## Schema v2.0 Format

```json
{
  "schema_version": "2.0",
  "job_id": "review_20251120_143000",
  "parent_job_id": null,
  "job_type": "full",
  
  "created_at": "2025-11-20T14:30:00",
  "updated_at": "2025-11-20T15:00:00",
  "completed_at": "2025-11-20T15:30:00",
  
  "database_hash": "abc123",
  "database_size": 150,
  "database_path": "neuromorphic-research_database.csv",
  
  "analysis_completed": true,
  "total_papers": 150,
  "papers_analyzed": 150,
  "papers_skipped": 0,
  
  "total_pillars": 6,
  "overall_coverage": 72.5,
  "coverage_by_pillar": {
    "pillar_1": 80.5,
    "pillar_2": 65.0
  },
  
  "gap_metrics": {
    "total_gaps": 28,
    "total_requirements": 42,
    "gap_threshold": 0.7,
    "gaps_by_pillar": {...},
    "gap_details": [...]
  },
  
  "incremental_state": {
    "is_continuation": false,
    "parent_job_id": null,
    "gap_extraction_mode": "full",
    "papers_added_since_parent": 0,
    "gaps_closed_since_parent": 0,
    "new_gaps_identified": 0
  },
  
  "execution_metrics": {
    "duration_seconds": 1800.0,
    "api_calls": 450,
    "api_cost_usd": 2.35,
    "cache_hit_rate": 0.67,
    "error_count": 0
  }
}
```

## Usage

### Basic Usage

```python
from literature_review.utils.state_manager import (
    StateManager, JobType, GapDetail
)

# Initialize manager
manager = StateManager("orchestrator_state.json")

# Create new state
state = manager.create_new_state(
    database_path="neuromorphic-research_database.csv",
    database_hash="abc123",
    database_size=100,
    job_type=JobType.FULL
)

# Update gap metrics
gaps = [
    GapDetail(
        pillar_id="pillar_1",
        requirement_id="req_1_1",
        sub_requirement_id="sub_1_1_1",
        current_coverage=0.45,
        target_coverage=0.7,
        gap_size=0.25,
        keywords=["neural networks"],
        evidence_count=3
    )
]
state = manager.update_gap_metrics(state, gaps, gap_threshold=0.7)

# Save state
manager.save_state(state)

# Load state (with automatic migration if needed)
state = manager.load_state()
```

### Incremental Analysis

```python
# Load parent state
parent_state = manager.load_state()
parent_job_id = parent_state.job_id

# Create incremental job
incr_state = manager.create_new_state(
    database_path="neuromorphic-research_database.csv",
    database_hash="def456",
    database_size=120,
    job_type=JobType.INCREMENTAL,
    parent_job_id=parent_job_id
)

# Track incremental progress
incr_state.incremental_state.papers_added_since_parent = 20
incr_state.incremental_state.gaps_closed_since_parent = 3
incr_state.incremental_state.new_gaps_identified = 1

manager.save_state(incr_state)
```

## Migration

### Automatic Migration

Migration happens automatically when loading a v1 state file:

```python
manager = StateManager("orchestrator_state.json")
state = manager.load_state()  # Automatically migrates if needed
```

### Manual Migration Script

```bash
# Migrate with backup
python scripts/migrate_state.py orchestrator_state.json

# Migrate without backup
python scripts/migrate_state.py --no-backup orchestrator_state.json
```

## Testing

Run the test suite:

```bash
# Unit tests
pytest tests/unit/test_state_manager.py -v

# Integration tests
pytest tests/integration/test_orchestrator_state_integration.py -v

# All state manager tests
pytest tests/unit/test_state_manager.py tests/integration/test_orchestrator_state_integration.py -v
```

## Architecture

### Dataclasses

- **`OrchestratorState`**: Main state container
- **`GapDetail`**: Individual gap information
- **`GapMetrics`**: Aggregated gap statistics
- **`IncrementalState`**: Incremental analysis tracking
- **`ExecutionMetrics`**: Runtime performance metrics
- **`JobType`**: Enum for FULL vs INCREMENTAL jobs

### Key Methods

- `create_new_state()`: Initialize new job state
- `load_state()`: Load and migrate existing state
- `save_state()`: Atomically save state to disk
- `update_gap_metrics()`: Update gap tracking data

## Implementation Details

### Atomic Writes

State files are written atomically using a temp file + rename pattern:

1. Write to `orchestrator_state.tmp`
2. Atomically rename to `orchestrator_state.json`
3. Prevents corruption from interrupted writes

### Migration Support

The StateManager handles two v1 formats:

1. **Simple format**: Direct fields (timestamp, database_hash, etc.)
2. **Nested format**: Current orchestrator.py format with last_run_state

Both are automatically migrated to v2.0 schema.

## Future Enhancements

Per the task card scope exclusions:

- ❌ Real-time state synchronization (single process only)
- ❌ Distributed state management (future: Redis/DB)
- ❌ State compression (JSON is sufficient for now)

## Dependencies

The StateManager has minimal dependencies:

- Python 3.8+
- Standard library only (json, os, pathlib, datetime, dataclasses)

No external packages required!

## Related Components

- **Gap Extraction Engine** (INCR-W1-1): Provides gap data to track
- **CLI Incremental Review Mode** (INCR-W2-1): Uses state for continuation
- **Dashboard Job Genealogy** (INCR-W3-1): Visualizes job lineage

## Success Metrics

✅ State saves/loads correctly  
✅ Gap metrics tracked accurately  
✅ Job lineage preserved  
✅ v1 → v2 migration works  
✅ Unit tests pass (95%+ coverage)  
✅ Atomic writes (no corruption)  
✅ <10ms state save/load  
✅ <1KB state file size (without large gap_details)
