# INCR-W1-5: Orchestrator State Manager

**Wave:** 1 (Foundation)  
**Priority:** 🟠 High  
**Effort:** 6-8 hours  
**Status:** 🟢 Ready  
**Assignable:** Backend Developer

---

## Overview

Enhance the existing `orchestrator_state.json` persistence mechanism to include gap-closing metrics and incremental analysis state. This enables the orchestrator to track which gaps are being addressed over time and provides the foundation for continuation logic in INCR-W2-1.

---

## Dependencies

**Prerequisites:**
- INCR-W1-1 (Gap Extraction Engine) - uses gap structure

**Blocks:**
- INCR-W2-1 (CLI Incremental Review Mode) - requires enhanced state
- INCR-W3-1 (Dashboard Job Genealogy) - uses state lineage

---

## Scope

### Included
- [x] Extend `orchestrator_state.json` schema with gap metrics
- [x] Add `StateManager` class for atomic state operations
- [x] Track gap closure progress over time
- [x] Store parent-child job relationships (for continuation)
- [x] Add state validation and schema versioning
- [x] Migration script for existing state files
- [x] Unit tests and integration tests

### Excluded
- ❌ Real-time state synchronization (single process only)
- ❌ Distributed state management (future: Redis/DB)
- ❌ State compression (JSON is sufficient)

---

## Technical Specification

### Current State Schema

```python
# Current orchestrator_state.json (orchestrator.py ~line 254)
{
    "timestamp": "2025-01-15T10:30:00",
    "database_hash": "abc123",
    "database_size": 150,
    "analysis_completed": true,
    "analysis_timestamp": "2025-01-15T11:00:00",
    "total_papers": 150,
    "total_pillars": 6,
    "overall_coverage": 72.5
}
```

### Enhanced State Schema

```python
# Enhanced orchestrator_state.json (v2)
{
    # --- Metadata ---
    "schema_version": "2.0",  # NEW: For backward compatibility
    "job_id": "review_20250115_103000",  # NEW: Unique identifier
    "parent_job_id": null,  # NEW: For incremental runs
    "job_type": "full" | "incremental",  # NEW
    
    # --- Timestamps ---
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T11:00:00",
    "completed_at": "2025-01-15T11:30:00",  # NEW
    
    # --- Database State ---
    "database_hash": "abc123",
    "database_size": 150,
    "database_path": "neuromorphic-research_database.csv",  # NEW
    
    # --- Analysis State ---
    "analysis_completed": true,
    "analysis_timestamp": "2025-01-15T11:00:00",
    "total_papers": 150,
    "papers_analyzed": 150,  # NEW: May differ from total in incremental
    "papers_skipped": 0,  # NEW: Pre-filtered papers
    
    # --- Coverage Metrics ---
    "total_pillars": 6,
    "overall_coverage": 72.5,
    "coverage_by_pillar": {  # NEW
        "pillar_1": 80.5,
        "pillar_2": 65.0,
        # ...
    },
    
    # --- Gap Metrics (NEW) ---
    "gap_metrics": {
        "total_gaps": 28,  # Gaps below threshold
        "total_requirements": 42,
        "gap_threshold": 0.7,  # From pillar_definitions.json
        
        "gaps_by_pillar": {
            "pillar_1": {
                "total_gaps": 5,
                "total_requirements": 8,
                "coverage": 62.5
            },
            # ...
        },
        
        "gap_details": [
            {
                "pillar_id": "pillar_1",
                "requirement_id": "req_1_2",
                "sub_requirement_id": "sub_req_1_2_3",
                "current_coverage": 0.45,
                "target_coverage": 0.7,
                "gap_size": 0.25,
                "keywords": ["neuromorphic hardware", "spike timing"],
                "evidence_count": 3  # Papers currently addressing this
            },
            # ...
        ]
    },
    
    # --- Incremental State (NEW) ---
    "incremental_state": {
        "is_continuation": false,
        "parent_job_id": null,
        "gap_extraction_mode": "full" | "targeted",
        "papers_added_since_parent": 0,
        "gaps_closed_since_parent": 0,
        "new_gaps_identified": 0
    },
    
    # --- Execution Metrics (NEW) ---
    "execution_metrics": {
        "duration_seconds": 1800,
        "api_calls": 450,
        "api_cost_usd": 2.35,
        "cache_hit_rate": 0.67,
        "error_count": 0
    }
}
```

### New StateManager Class

Create `literature_review/utils/state_manager.py`:

```python
"""
State Manager for Gap Analysis Orchestrator

Provides atomic operations for reading/writing orchestrator state with:
- Schema versioning and migration
- Gap metrics tracking
- Job lineage (parent-child relationships)
- Validation and error handling
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class JobType(Enum):
    """Type of analysis job."""
    FULL = "full"  # Complete re-analysis
    INCREMENTAL = "incremental"  # Gap-targeted update


@dataclass
class GapDetail:
    """Individual gap within a pillar requirement."""
    pillar_id: str
    requirement_id: str
    sub_requirement_id: str
    current_coverage: float
    target_coverage: float
    gap_size: float
    keywords: List[str]
    evidence_count: int


@dataclass
class GapMetrics:
    """Aggregated gap analysis metrics."""
    total_gaps: int
    total_requirements: int
    gap_threshold: float
    gaps_by_pillar: Dict[str, Dict[str, Any]]
    gap_details: List[GapDetail]


@dataclass
class IncrementalState:
    """State for incremental analysis jobs."""
    is_continuation: bool
    parent_job_id: Optional[str]
    gap_extraction_mode: str  # "full" or "targeted"
    papers_added_since_parent: int
    gaps_closed_since_parent: int
    new_gaps_identified: int


@dataclass
class ExecutionMetrics:
    """Runtime performance metrics."""
    duration_seconds: float
    api_calls: int
    api_cost_usd: float
    cache_hit_rate: float
    error_count: int


@dataclass
class OrchestratorState:
    """Complete orchestrator state."""
    # Metadata
    schema_version: str
    job_id: str
    parent_job_id: Optional[str]
    job_type: JobType
    
    # Timestamps
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    
    # Database State
    database_hash: str
    database_size: int
    database_path: str
    
    # Analysis State
    analysis_completed: bool
    analysis_timestamp: str
    total_papers: int
    papers_analyzed: int
    papers_skipped: int
    
    # Coverage Metrics
    total_pillars: int
    overall_coverage: float
    coverage_by_pillar: Dict[str, float]
    
    # Gap Metrics
    gap_metrics: GapMetrics
    
    # Incremental State
    incremental_state: IncrementalState
    
    # Execution Metrics
    execution_metrics: ExecutionMetrics


class StateManager:
    """
    Manages orchestrator state with atomic operations and validation.
    
    Features:
    - Schema versioning (v1 → v2 migration)
    - Atomic read/write with file locking
    - Validation and error recovery
    - Gap metrics tracking
    - Job lineage management
    """
    
    CURRENT_SCHEMA_VERSION = "2.0"
    
    def __init__(self, state_file: str = "orchestrator_state.json"):
        """
        Initialize state manager.
        
        Args:
            state_file: Path to state JSON file
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load_state(self) -> Optional[OrchestratorState]:
        """
        Load state from file, migrating if needed.
        
        Returns:
            OrchestratorState if file exists, None otherwise
        """
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            
            # Check schema version and migrate if needed
            schema_version = data.get('schema_version', '1.0')
            
            if schema_version == '1.0':
                data = self._migrate_v1_to_v2(data)
            
            return self._deserialize_state(data)
        
        except Exception as e:
            print(f"⚠️  Error loading state: {e}")
            return None
    
    def save_state(self, state: OrchestratorState) -> bool:
        """
        Save state to file atomically.
        
        Args:
            state: OrchestratorState to save
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update timestamp
            state.updated_at = datetime.now().isoformat()
            
            # Serialize to dict
            data = self._serialize_state(state)
            
            # Write atomically (temp file + rename)
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            temp_file.replace(self.state_file)
            
            return True
        
        except Exception as e:
            print(f"❌ Error saving state: {e}")
            return False
    
    def create_new_state(
        self,
        database_path: str,
        database_hash: str,
        database_size: int,
        job_type: JobType = JobType.FULL,
        parent_job_id: Optional[str] = None
    ) -> OrchestratorState:
        """
        Create new orchestrator state.
        
        Args:
            database_path: Path to research database CSV
            database_hash: MD5 hash of database
            database_size: Number of papers
            job_type: FULL or INCREMENTAL
            parent_job_id: Parent job ID (for incremental)
        
        Returns:
            New OrchestratorState
        """
        now = datetime.now().isoformat()
        job_id = f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return OrchestratorState(
            schema_version=self.CURRENT_SCHEMA_VERSION,
            job_id=job_id,
            parent_job_id=parent_job_id,
            job_type=job_type,
            created_at=now,
            updated_at=now,
            completed_at=None,
            database_hash=database_hash,
            database_size=database_size,
            database_path=database_path,
            analysis_completed=False,
            analysis_timestamp="",
            total_papers=database_size,
            papers_analyzed=0,
            papers_skipped=0,
            total_pillars=0,
            overall_coverage=0.0,
            coverage_by_pillar={},
            gap_metrics=GapMetrics(
                total_gaps=0,
                total_requirements=0,
                gap_threshold=0.7,
                gaps_by_pillar={},
                gap_details=[]
            ),
            incremental_state=IncrementalState(
                is_continuation=(parent_job_id is not None),
                parent_job_id=parent_job_id,
                gap_extraction_mode="full" if job_type == JobType.FULL else "targeted",
                papers_added_since_parent=0,
                gaps_closed_since_parent=0,
                new_gaps_identified=0
            ),
            execution_metrics=ExecutionMetrics(
                duration_seconds=0.0,
                api_calls=0,
                api_cost_usd=0.0,
                cache_hit_rate=0.0,
                error_count=0
            )
        )
    
    def update_gap_metrics(
        self,
        state: OrchestratorState,
        gap_details: List[GapDetail],
        gap_threshold: float = 0.7
    ) -> OrchestratorState:
        """
        Update gap metrics in state.
        
        Args:
            state: Current state
            gap_details: List of individual gaps
            gap_threshold: Coverage threshold for gap identification
        
        Returns:
            Updated state
        """
        # Aggregate by pillar
        gaps_by_pillar = {}
        for gap in gap_details:
            if gap.pillar_id not in gaps_by_pillar:
                gaps_by_pillar[gap.pillar_id] = {
                    'total_gaps': 0,
                    'total_requirements': 0,
                    'coverage': 0.0
                }
            gaps_by_pillar[gap.pillar_id]['total_gaps'] += 1
        
        # Update state
        state.gap_metrics = GapMetrics(
            total_gaps=len(gap_details),
            total_requirements=sum(
                pillar['total_requirements'] 
                for pillar in gaps_by_pillar.values()
            ),
            gap_threshold=gap_threshold,
            gaps_by_pillar=gaps_by_pillar,
            gap_details=gap_details
        )
        
        return state
    
    def _migrate_v1_to_v2(self, v1_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate schema v1 → v2.
        
        Args:
            v1_data: Old state format
        
        Returns:
            New state format
        """
        now = datetime.now().isoformat()
        
        v2_data = {
            'schema_version': '2.0',
            'job_id': f"migrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'parent_job_id': None,
            'job_type': 'full',
            'created_at': v1_data.get('timestamp', now),
            'updated_at': now,
            'completed_at': v1_data.get('analysis_timestamp'),
            'database_hash': v1_data.get('database_hash', ''),
            'database_size': v1_data.get('database_size', 0),
            'database_path': 'neuromorphic-research_database.csv',  # Default
            'analysis_completed': v1_data.get('analysis_completed', False),
            'analysis_timestamp': v1_data.get('analysis_timestamp', ''),
            'total_papers': v1_data.get('total_papers', 0),
            'papers_analyzed': v1_data.get('total_papers', 0),
            'papers_skipped': 0,
            'total_pillars': v1_data.get('total_pillars', 0),
            'overall_coverage': v1_data.get('overall_coverage', 0.0),
            'coverage_by_pillar': {},
            'gap_metrics': {
                'total_gaps': 0,
                'total_requirements': 0,
                'gap_threshold': 0.7,
                'gaps_by_pillar': {},
                'gap_details': []
            },
            'incremental_state': {
                'is_continuation': False,
                'parent_job_id': None,
                'gap_extraction_mode': 'full',
                'papers_added_since_parent': 0,
                'gaps_closed_since_parent': 0,
                'new_gaps_identified': 0
            },
            'execution_metrics': {
                'duration_seconds': 0.0,
                'api_calls': 0,
                'api_cost_usd': 0.0,
                'cache_hit_rate': 0.0,
                'error_count': 0
            }
        }
        
        print(f"✅ Migrated state from v1.0 → v2.0")
        return v2_data
    
    def _serialize_state(self, state: OrchestratorState) -> Dict[str, Any]:
        """Convert OrchestratorState → JSON dict."""
        data = asdict(state)
        
        # Convert enums
        data['job_type'] = state.job_type.value
        
        # Convert gap details
        data['gap_metrics']['gap_details'] = [
            asdict(gap) for gap in state.gap_metrics.gap_details
        ]
        
        return data
    
    def _deserialize_state(self, data: Dict[str, Any]) -> OrchestratorState:
        """Convert JSON dict → OrchestratorState."""
        # Parse gap details
        gap_details = [
            GapDetail(**gap_dict)
            for gap_dict in data['gap_metrics']['gap_details']
        ]
        
        data['gap_metrics']['gap_details'] = gap_details
        data['gap_metrics'] = GapMetrics(**data['gap_metrics'])
        data['incremental_state'] = IncrementalState(**data['incremental_state'])
        data['execution_metrics'] = ExecutionMetrics(**data['execution_metrics'])
        data['job_type'] = JobType(data['job_type'])
        
        return OrchestratorState(**data)
```

### Integration with Orchestrator

Update `literature_review/orchestrator.py`:

```python
# orchestrator.py - Replace existing save_orchestrator_state()

from literature_review.utils.state_manager import StateManager, JobType, GapDetail

# At module level
state_manager = StateManager(ORCHESTRATOR_STATE_FILE)

def save_orchestrator_state_enhanced(
    database_hash: str,
    database_size: int,
    database_path: str,
    analysis_completed: bool,
    total_papers: int,
    papers_analyzed: int,
    papers_skipped: int,
    total_pillars: int,
    overall_coverage: float,
    coverage_by_pillar: Dict[str, float],
    gap_details: List[GapDetail],
    gap_threshold: float = 0.7,
    job_type: JobType = JobType.FULL,
    parent_job_id: Optional[str] = None,
    execution_metrics: Optional[Dict[str, Any]] = None
):
    """
    Save enhanced orchestrator state with gap metrics.
    
    Args:
        ... (database and analysis params)
        gap_details: List of GapDetail objects from gap extraction
        gap_threshold: Coverage threshold for gap identification
        job_type: FULL or INCREMENTAL
        parent_job_id: Parent job ID for incremental runs
        execution_metrics: Runtime metrics (API calls, cost, etc.)
    """
    # Load existing state or create new
    state = state_manager.load_state()
    
    if state is None:
        state = state_manager.create_new_state(
            database_path=database_path,
            database_hash=database_hash,
            database_size=database_size,
            job_type=job_type,
            parent_job_id=parent_job_id
        )
    
    # Update fields
    state.analysis_completed = analysis_completed
    state.analysis_timestamp = datetime.now().isoformat()
    state.total_papers = total_papers
    state.papers_analyzed = papers_analyzed
    state.papers_skipped = papers_skipped
    state.total_pillars = total_pillars
    state.overall_coverage = overall_coverage
    state.coverage_by_pillar = coverage_by_pillar
    
    # Update gap metrics
    state = state_manager.update_gap_metrics(state, gap_details, gap_threshold)
    
    # Update execution metrics if provided
    if execution_metrics:
        from literature_review.utils.state_manager import ExecutionMetrics
        state.execution_metrics = ExecutionMetrics(**execution_metrics)
    
    # Mark as completed
    if analysis_completed:
        state.completed_at = datetime.now().isoformat()
    
    # Save
    success = state_manager.save_state(state)
    
    if success:
        logger.info(f"✅ State saved: {state.job_id}")
    else:
        logger.error(f"❌ Failed to save state")
```

---

## Testing Strategy

### Unit Tests

Create `tests/unit/test_state_manager.py`:

```python
import pytest
import json
from pathlib import Path
from literature_review.utils.state_manager import (
    StateManager, JobType, GapDetail, GapMetrics, 
    IncrementalState, ExecutionMetrics, OrchestratorState
)

def test_create_new_state(tmp_path):
    """Test creating new state."""
    state_file = tmp_path / "state.json"
    manager = StateManager(str(state_file))
    
    state = manager.create_new_state(
        database_path="test.csv",
        database_hash="abc123",
        database_size=100,
        job_type=JobType.FULL
    )
    
    assert state.schema_version == "2.0"
    assert state.job_type == JobType.FULL
    assert state.database_size == 100
    assert state.parent_job_id is None

def test_save_and_load_state(tmp_path):
    """Test state persistence."""
    state_file = tmp_path / "state.json"
    manager = StateManager(str(state_file))
    
    # Create and save
    state = manager.create_new_state(
        database_path="test.csv",
        database_hash="abc123",
        database_size=100
    )
    assert manager.save_state(state)
    
    # Load
    loaded_state = manager.load_state()
    assert loaded_state is not None
    assert loaded_state.database_hash == "abc123"
    assert loaded_state.database_size == 100

def test_gap_metrics_update(tmp_path):
    """Test updating gap metrics."""
    state_file = tmp_path / "state.json"
    manager = StateManager(str(state_file))
    
    state = manager.create_new_state(
        database_path="test.csv",
        database_hash="abc123",
        database_size=100
    )
    
    # Add gap details
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
        ),
        GapDetail(
            pillar_id="pillar_1",
            requirement_id="req_1_2",
            sub_requirement_id="sub_1_2_1",
            current_coverage=0.30,
            target_coverage=0.7,
            gap_size=0.40,
            keywords=["spike timing"],
            evidence_count=2
        )
    ]
    
    state = manager.update_gap_metrics(state, gaps, gap_threshold=0.7)
    
    assert state.gap_metrics.total_gaps == 2
    assert len(state.gap_metrics.gap_details) == 2
    assert state.gap_metrics.gap_threshold == 0.7

def test_schema_migration_v1_to_v2(tmp_path):
    """Test migrating old state format."""
    state_file = tmp_path / "state.json"
    
    # Create v1 state file
    v1_state = {
        "timestamp": "2025-01-15T10:00:00",
        "database_hash": "old_hash",
        "database_size": 50,
        "analysis_completed": True,
        "total_papers": 50,
        "total_pillars": 5,
        "overall_coverage": 65.0
    }
    
    with open(state_file, 'w') as f:
        json.dump(v1_state, f)
    
    # Load and migrate
    manager = StateManager(str(state_file))
    state = manager.load_state()
    
    assert state is not None
    assert state.schema_version == "2.0"
    assert state.database_hash == "old_hash"
    assert state.database_size == 50
    assert state.total_papers == 50

def test_incremental_state_tracking(tmp_path):
    """Test incremental job lineage."""
    state_file = tmp_path / "state.json"
    manager = StateManager(str(state_file))
    
    # Create parent job
    parent_state = manager.create_new_state(
        database_path="test.csv",
        database_hash="abc123",
        database_size=100,
        job_type=JobType.FULL
    )
    parent_job_id = parent_state.job_id
    manager.save_state(parent_state)
    
    # Create child job
    child_state = manager.create_new_state(
        database_path="test.csv",
        database_hash="def456",
        database_size=120,
        job_type=JobType.INCREMENTAL,
        parent_job_id=parent_job_id
    )
    
    assert child_state.parent_job_id == parent_job_id
    assert child_state.job_type == JobType.INCREMENTAL
    assert child_state.incremental_state.is_continuation == True

def test_atomic_save(tmp_path):
    """Test atomic file writing (temp + rename)."""
    state_file = tmp_path / "state.json"
    manager = StateManager(str(state_file))
    
    state = manager.create_new_state(
        database_path="test.csv",
        database_hash="abc123",
        database_size=100
    )
    
    # Save should create temp file then rename
    assert manager.save_state(state)
    assert state_file.exists()
    
    # Temp file should not exist after save
    temp_file = state_file.with_suffix('.tmp')
    assert not temp_file.exists()
```

### Integration Tests

Create `tests/integration/test_orchestrator_state_integration.py`:

```python
import pytest
from pathlib import Path
from literature_review.orchestrator import save_orchestrator_state_enhanced
from literature_review.utils.state_manager import StateManager, GapDetail, JobType

def test_full_workflow_state_persistence(tmp_path):
    """Test complete workflow: create → update → load."""
    state_file = tmp_path / "orchestrator_state.json"
    
    # Simulate gap extraction
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
    
    # Save state
    save_orchestrator_state_enhanced(
        database_hash="abc123",
        database_size=100,
        database_path="test.csv",
        analysis_completed=True,
        total_papers=100,
        papers_analyzed=100,
        papers_skipped=0,
        total_pillars=6,
        overall_coverage=72.5,
        coverage_by_pillar={"pillar_1": 80.0},
        gap_details=gaps,
        gap_threshold=0.7,
        job_type=JobType.FULL
    )
    
    # Load and verify
    manager = StateManager(str(state_file))
    state = manager.load_state()
    
    assert state is not None
    assert state.gap_metrics.total_gaps == 1
    assert state.overall_coverage == 72.5
```

---

## Deliverables

- [ ] `StateManager` class in `literature_review/utils/state_manager.py`
- [ ] Enhanced state schema (v2.0) with gap metrics
- [ ] Migration function (v1 → v2)
- [ ] Integration with `orchestrator.py`
- [ ] Unit tests in `tests/unit/test_state_manager.py`
- [ ] Integration tests
- [ ] Migration script for existing state files
- [ ] Documentation in code comments

---

## Success Criteria

✅ **Functional:**
- State saves/loads correctly
- Gap metrics tracked accurately
- Job lineage preserved
- v1 → v2 migration works

✅ **Quality:**
- Unit tests pass (95% coverage)
- Atomic writes (no corruption)
- Schema validation

✅ **Performance:**
- <10ms state save/load
- <1KB state file size

---

## Notes

- This is a **non-breaking change** (v1 states auto-migrate)
- Safe to deploy independently
- Enables INCR-W2-1 (CLI incremental mode)

---

**Status:** 🟢 Ready for implementation  
**Assignee:** TBD  
**Estimated Start:** Week 1, Day 1  
**Estimated Completion:** Week 1, Day 3
