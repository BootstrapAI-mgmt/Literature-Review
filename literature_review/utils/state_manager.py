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
Orchestrator State Manager for Incremental Review Mode.

Enhanced state persistence with gap metrics and incremental analysis tracking.
Part of INCR-W1-5: Orchestrator State Manager.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GapDetail:
    """Individual gap within a pillar requirement."""
    """Detailed gap information for state tracking."""
    
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
class StateManager:
    """Manages orchestrator state with gap metrics."""
    
    SCHEMA_VERSION = "2.0"
    
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
        
        # Count total requirements from gap details
        requirements_set = set()
        for gap in gap_details:
            requirements_set.add(f"{gap.pillar_id}:{gap.requirement_id}:{gap.sub_requirement_id}")
        
        # Update state
        state.gap_metrics = GapMetrics(
            total_gaps=len(gap_details),
            total_requirements=len(requirements_set),
            gap_threshold=gap_threshold,
            gaps_by_pillar=gaps_by_pillar,
            gap_details=gap_details
        )
        
        return state
    
    def _migrate_v1_to_v2(self, v1_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate schema v1 → v2.
        
        Handles both old orchestrator state formats:
        1. Simple format with timestamp, database_hash, etc.
        2. Nested format with last_run_state, previous_results, score_history
        
        Args:
            v1_data: Old state format
        
        Returns:
            New state format
        """
        now = datetime.now().isoformat()
        
        # Check if this is the nested format (current orchestrator.py format)
        is_nested = 'last_run_state' in v1_data or 'previous_results' in v1_data
        
        if is_nested:
            # Extract from nested structure
            last_run = v1_data.get('last_run_state', {})
            file_states = last_run.get('file_states', {})
            previous_results = v1_data.get('previous_results', {})
            
            # Calculate overall coverage from previous results
            overall_coverage = 0.0
            total_pillars = len(previous_results)
            if total_pillars > 0:
                coverage_sum = sum(p.get('completeness', 0) for p in previous_results.values())
                overall_coverage = coverage_sum / total_pillars
            
            # Extract coverage by pillar
            coverage_by_pillar = {
                pillar_name: pillar_data.get('completeness', 0.0)
                for pillar_name, pillar_data in previous_results.items()
            }
            
            v2_data = {
                'schema_version': '2.0',
                'job_id': f"migrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'parent_job_id': None,
                'job_type': 'full',
                'created_at': v1_data.get('last_run_timestamp', now),
                'updated_at': now,
                'completed_at': v1_data.get('last_run_timestamp'),
                'database_hash': '',  # Not available in nested format
                'database_size': 0,  # Not available in nested format
                'database_path': 'neuromorphic-research_database.csv',  # Default
                'analysis_completed': v1_data.get('last_completed_stage') == 'final',
                'analysis_timestamp': v1_data.get('last_run_timestamp', ''),
                'total_papers': 0,  # Not available in nested format
                'papers_analyzed': 0,
                'papers_skipped': 0,
                'total_pillars': total_pillars,
                'overall_coverage': overall_coverage,
                'coverage_by_pillar': coverage_by_pillar,
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
        else:
            # Simple format
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
        
        print(f"✅ Migrated state from v1.0 → v2.0 ({'nested' if is_nested else 'simple'} format)")
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
            state_file: Path to state file
        """
        self.state_file = Path(state_file)
    
    def load_state(self) -> Dict:
        """
        Load orchestrator state from file.
        
        Returns:
            State dictionary
        """
        if not self.state_file.exists():
            logger.info("No state file found. Starting fresh.")
            return self._create_empty_state()
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Validate schema version
            version = state.get('schema_version', '1.0')
            if version != self.SCHEMA_VERSION:
                logger.warning(
                    f"State file schema mismatch: {version} != {self.SCHEMA_VERSION}. "
                    "Some fields may be missing."
                )
            
            logger.info("Successfully loaded orchestrator state")
            return state
        
        except Exception as e:
            logger.error(f"Failed to load state: {e}. Starting fresh.")
            return self._create_empty_state()
    
    def save_state(
        self,
        database_hash: str,
        database_size: int,
        database_path: str,
        analysis_completed: bool = True,
        total_papers: int = 0,
        papers_analyzed: Optional[int] = None,
        papers_skipped: Optional[int] = None,
        total_pillars: int = 0,
        overall_coverage: float = 0.0,
        coverage_by_pillar: Optional[Dict] = None,
        gap_details: Optional[List[GapDetail]] = None,
        gap_threshold: float = 0.7,
        job_id: Optional[str] = None,
        parent_job_id: Optional[str] = None,
        job_type: str = "full"
    ) -> None:
        """
        Save enhanced orchestrator state.
        
        Args:
            database_hash: Hash of research database
            database_size: Number of papers in database
            database_path: Path to research database
            analysis_completed: Whether analysis finished
            total_papers: Total papers in database
            papers_analyzed: Papers analyzed (after filtering)
            papers_skipped: Papers skipped by pre-filter
            total_pillars: Number of pillars
            overall_coverage: Overall coverage percentage
            coverage_by_pillar: Coverage breakdown by pillar
            gap_details: List of GapDetail objects
            gap_threshold: Gap extraction threshold
            job_id: Unique job identifier
            parent_job_id: Parent job ID (for incremental runs)
            job_type: "full" or "incremental"
        """
        now = datetime.now().isoformat()
        
        # Convert gap_details to dictionaries
        gaps_list = []
        if gap_details:
            for gap in gap_details:
                if isinstance(gap, GapDetail):
                    gaps_list.append(asdict(gap))
                elif isinstance(gap, dict):
                    gaps_list.append(gap)
        
        state = {
            # Metadata
            "schema_version": self.SCHEMA_VERSION,
            "job_id": job_id or f"job_{now.replace(':', '').replace('-', '').replace('.', '')}",
            "parent_job_id": parent_job_id,
            "job_type": job_type,
            
            # Timestamps
            "created_at": now,
            "updated_at": now,
            "completed_at": now if analysis_completed else None,
            
            # Database state
            "database_hash": database_hash,
            "database_size": database_size,
            "database_path": database_path,
            
            # Analysis state
            "analysis_completed": analysis_completed,
            "total_papers": total_papers,
            "papers_analyzed": papers_analyzed if papers_analyzed is not None else total_papers,
            "papers_skipped": papers_skipped or 0,
            
            # Coverage metrics
            "total_pillars": total_pillars,
            "overall_coverage": overall_coverage,
            "coverage_by_pillar": coverage_by_pillar or {},
            
            # Gap metrics
            "gap_count": len(gaps_list),
            "gap_threshold": gap_threshold,
            "gap_details": gaps_list
        }
        
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save state
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Successfully saved state to {self.state_file}")
        
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _create_empty_state(self) -> Dict:
        """Create empty state dictionary."""
        return {
            "schema_version": self.SCHEMA_VERSION,
            "job_id": None,
            "parent_job_id": None,
            "job_type": "full",
            "created_at": None,
            "updated_at": None,
            "completed_at": None,
            "database_hash": "",
            "database_size": 0,
            "database_path": "",
            "analysis_completed": False,
            "total_papers": 0,
            "papers_analyzed": 0,
            "papers_skipped": 0,
            "total_pillars": 0,
            "overall_coverage": 0.0,
            "coverage_by_pillar": {},
            "gap_count": 0,
            "gap_threshold": 0.7,
            "gap_details": []
        }


def save_orchestrator_state_enhanced(
    database_hash: str,
    database_size: int,
    database_path: str,
    analysis_completed: bool = True,
    total_papers: int = 0,
    papers_analyzed: Optional[int] = None,
    papers_skipped: Optional[int] = None,
    total_pillars: int = 0,
    overall_coverage: float = 0.0,
    coverage_by_pillar: Optional[Dict] = None,
    gap_details: Optional[List] = None,
    gap_threshold: float = 0.7,
    state_file: str = "orchestrator_state.json"
) -> None:
    """
    Helper function to save enhanced orchestrator state.
    
    This is a convenience wrapper around StateManager.save_state().
    """
    manager = StateManager(state_file)
    manager.save_state(
        database_hash=database_hash,
        database_size=database_size,
        database_path=database_path,
        analysis_completed=analysis_completed,
        total_papers=total_papers,
        papers_analyzed=papers_analyzed,
        papers_skipped=papers_skipped,
        total_pillars=total_pillars,
        overall_coverage=overall_coverage,
        coverage_by_pillar=coverage_by_pillar,
        gap_details=gap_details,
        gap_threshold=gap_threshold
    )
