"""
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
    """Detailed gap information for state tracking."""
    
    pillar_id: str
    requirement_id: str
    sub_requirement_id: str
    current_coverage: float
    target_coverage: float
    gap_size: float
    keywords: List[str]
    evidence_count: int


class StateManager:
    """Manages orchestrator state with gap metrics."""
    
    SCHEMA_VERSION = "2.0"
    
    def __init__(self, state_file: str = "orchestrator_state.json"):
        """
        Initialize state manager.
        
        Args:
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
