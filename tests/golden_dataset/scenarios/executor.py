"""
Gap Scenario Execution Framework

Executes controlled gap scenarios to validate:
1. Correct gap detection (finding gaps that exist)
2. Correct non-gap handling (not flagging covered requirements)
3. Iterative gap closing (Pass 2 paper attribution)
4. Decoy paper rejection (irrelevant paper handling)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Protocol, TYPE_CHECKING
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..schema_anchor import GapScenario


class PipelineRunner(Protocol):
    """Protocol for pipeline runners."""
    def run(self, mode: str = 'full') -> Dict[str, Any]:
        """Run the pipeline and return output."""
        ...


class DatabaseManager(Protocol):
    """Protocol for database state management."""
    def create_snapshot(self) -> str:
        """Create a snapshot and return its ID."""
        ...
    
    def restore_snapshot(self, snapshot_id: str) -> None:
        """Restore database to a snapshot state."""
        ...
    
    def clear(self) -> None:
        """Clear all papers from the database."""
        ...
    
    def add_paper(self, paper_id: str) -> None:
        """Add a paper to the database."""
        ...


@dataclass
class ScenarioResult:
    """Result of executing a gap scenario."""
    scenario_id: str
    passed: bool
    
    # Pass 1 results
    pass_1_gaps_detected: List[str] = field(default_factory=list)
    pass_1_false_gaps: List[str] = field(default_factory=list)  # Non-gaps incorrectly flagged
    pass_1_missed_gaps: List[str] = field(default_factory=list)  # Expected gaps not detected
    
    # Pass 2 results (if iterative scenario)
    pass_2_severity_changes: Dict[str, str] = field(default_factory=dict)
    pass_2_expected_changes: Dict[str, str] = field(default_factory=dict)
    pass_2_decoy_contributions: List[str] = field(default_factory=list)  # Should be empty
    
    failure_reasons: List[str] = field(default_factory=list)


class GapScenarioExecutor:
    """
    Execute controlled gap scenarios for validation.
    
    This executor manages the lifecycle of gap scenario testing:
    1. Database state management (snapshot/restore)
    2. Pipeline execution in controlled modes
    3. Result comparison against expected outcomes
    4. Decoy paper contribution validation
    """
    
    def __init__(
        self,
        pipeline_runner: PipelineRunner,
        database_manager: DatabaseManager,
        output_dir: Path
    ):
        """
        Initialize the executor.
        
        Args:
            pipeline_runner: Callable that runs the pipeline
            database_manager: Manages database state
            output_dir: Directory for execution outputs
        """
        self.pipeline = pipeline_runner
        self.db = database_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def execute_scenario(self, scenario: "GapScenario") -> ScenarioResult:
        """
        Execute a gap scenario and validate results.
        
        Steps:
        1. Initialize database with Pass 1 papers only
        2. Run gap detection pipeline
        3. Validate detected gaps against expected_gaps
        4. Validate non-detected against expected_non_gaps
        5. Add Pass 2 papers (gap-closing + decoys)
        6. Re-run gap detection
        7. Validate severity changes
        8. Validate decoy papers didn't contribute
        
        Args:
            scenario: GapScenario to execute
        
        Returns:
            ScenarioResult with pass/fail status and details
        """
        failure_reasons = []
        
        # === PRE-EXECUTION ===
        # Create isolated database state
        snapshot_id = self.db.create_snapshot()
        
        try:
            # === PASS 1: INITIAL STATE ===
            logger.info(f"Executing scenario {scenario.scenario_id} - Pass 1")
            
            # Load only Pass 1 papers
            self.db.clear()
            for paper in scenario.initial_papers:
                self.db.add_paper(paper.paper_id)
            
            # Run pipeline
            pass_1_output = self.pipeline.run(mode='full')
            pass_1_gaps = self._parse_gap_report(pass_1_output)
            
            # Validate Pass 1 - expected gaps detected
            pass_1_missed = []
            for expected in scenario.expected_gaps:
                if expected.must_be_detected:
                    if expected.requirement_id not in pass_1_gaps:
                        pass_1_missed.append(expected.requirement_id)
                        failure_reasons.append(
                            f"Pass 1: Expected gap {expected.requirement_id} not detected"
                        )
            
            # Validate Pass 1 - non-gaps not flagged
            pass_1_false = []
            for non_gap in scenario.expected_non_gaps:
                if non_gap.requirement_id in pass_1_gaps:
                    pass_1_false.append(non_gap.requirement_id)
                    failure_reasons.append(
                        f"Pass 1: Non-gap {non_gap.requirement_id} incorrectly flagged"
                    )
            
            # === PASS 2: GAP CLOSING (if iterative) ===
            pass_2_changes: Dict[str, str] = {}
            pass_2_expected = dict(scenario.expected_severity_changes)
            pass_2_decoys: List[str] = []
            
            if scenario.scenario_type == 'iterative':
                logger.info(f"Executing scenario {scenario.scenario_id} - Pass 2")
                
                # Add gap-closing papers
                for paper in scenario.gap_closing_papers:
                    self.db.add_paper(paper.paper_id)
                
                # Add decoy papers
                for decoy in scenario.decoy_papers:
                    self.db.add_paper(decoy.paper_id)
                
                # Run pipeline in incremental mode
                pass_2_output = self.pipeline.run(mode='incremental')
                pass_2_gaps = self._parse_gap_report(pass_2_output)
                
                # Check severity changes
                # Support both unicode arrow (→) and ASCII arrow (->) for compatibility
                for req_id, expected_change in pass_2_expected.items():
                    actual_severity = pass_2_gaps.get(req_id, {}).get('severity', 'NONE')
                    # Parse expected change with either arrow style
                    if '→' in expected_change:
                        expected_after = expected_change.split('→')[1].strip()
                    elif '->' in expected_change:
                        expected_after = expected_change.split('->')[1].strip()
                    else:
                        expected_after = expected_change
                    if actual_severity != expected_after:
                        failure_reasons.append(
                            f"Pass 2: {req_id} severity is {actual_severity}, expected {expected_after}"
                        )
                    pass_1_severity = pass_1_gaps.get(req_id, {}).get('severity', 'NONE')
                    pass_2_changes[req_id] = f"{pass_1_severity} -> {actual_severity}"
                
                # Check decoy papers didn't contribute
                contributions = self._parse_contributions(pass_2_output)
                for decoy in scenario.decoy_papers:
                    for req_id in decoy.should_not_close:
                        if self._paper_contributed(contributions, decoy.paper_id, req_id):
                            pass_2_decoys.append(f"{decoy.paper_id} → {req_id}")
                            failure_reasons.append(
                                f"Pass 2: Decoy {decoy.paper_id} incorrectly contributed to {req_id}"
                            )
            
            passed = len(failure_reasons) == 0
            
            # Save execution log
            self._save_execution_log(scenario.scenario_id, {
                'passed': passed,
                'pass_1_gaps': list(pass_1_gaps.keys()),
                'pass_1_missed': pass_1_missed,
                'pass_1_false': pass_1_false,
                'pass_2_changes': pass_2_changes,
                'pass_2_decoys': pass_2_decoys,
                'failure_reasons': failure_reasons
            })
            
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                passed=passed,
                pass_1_gaps_detected=list(pass_1_gaps.keys()),
                pass_1_false_gaps=pass_1_false,
                pass_1_missed_gaps=pass_1_missed,
                pass_2_severity_changes=pass_2_changes,
                pass_2_expected_changes=pass_2_expected,
                pass_2_decoy_contributions=pass_2_decoys,
                failure_reasons=failure_reasons
            )
            
        finally:
            # Restore database state
            self.db.restore_snapshot(snapshot_id)
    
    def execute_all(self, scenarios: List["GapScenario"]) -> Dict[str, ScenarioResult]:
        """
        Execute multiple scenarios and return all results.
        
        Args:
            scenarios: List of GapScenario to execute
        
        Returns:
            Dict mapping scenario_id to ScenarioResult
        """
        results = {}
        for scenario in scenarios:
            try:
                results[scenario.scenario_id] = self.execute_scenario(scenario)
            except Exception as e:
                logger.error(f"Error executing scenario {scenario.scenario_id}: {e}")
                results[scenario.scenario_id] = ScenarioResult(
                    scenario_id=scenario.scenario_id,
                    passed=False,
                    failure_reasons=[f"Execution error: {str(e)}"]
                )
        return results
    
    def _parse_gap_report(self, output: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Parse gap_analysis_report.json output."""
        gaps = {}
        for gap in output.get('gaps', []):
            gaps[gap['requirement_id']] = {
                'severity': gap.get('severity'),
                'completeness': gap.get('completeness')
            }
        return gaps
    
    def _parse_contributions(self, output: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse paper contributions from output."""
        return output.get('contributions', [])
    
    def _paper_contributed(
        self, contributions: List[Dict[str, Any]], paper_id: str, req_id: str
    ) -> bool:
        """Check if a paper contributed to a specific requirement."""
        for contrib in contributions:
            if contrib.get('paper_id') == paper_id:
                if req_id in contrib.get('requirements', []):
                    return True
        return False
    
    def _save_execution_log(self, scenario_id: str, log_data: Dict[str, Any]) -> None:
        """Save execution log to output directory."""
        log_file = self.output_dir / f"{scenario_id}_execution.json"
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)


# === Mock implementations for testing ===

class MockPipelineRunner:
    """Mock pipeline runner for testing the executor."""
    
    def __init__(self, outputs: Optional[Dict[str, Dict[str, Any]]] = None):
        self.outputs = outputs or {}
        self.run_count = 0
    
    def run(self, mode: str = 'full') -> Dict[str, Any]:
        self.run_count += 1
        return self.outputs.get(mode, {'gaps': [], 'contributions': []})


class MockDatabaseManager:
    """Mock database manager for testing the executor."""
    
    def __init__(self):
        self.papers: List[str] = []
        self.snapshots: Dict[str, List[str]] = {}
        self.snapshot_counter = 0
    
    def create_snapshot(self) -> str:
        self.snapshot_counter += 1
        snapshot_id = f"snapshot_{self.snapshot_counter}"
        self.snapshots[snapshot_id] = list(self.papers)
        return snapshot_id
    
    def restore_snapshot(self, snapshot_id: str) -> None:
        if snapshot_id in self.snapshots:
            self.papers = list(self.snapshots[snapshot_id])
    
    def clear(self) -> None:
        self.papers = []
    
    def add_paper(self, paper_id: str) -> None:
        self.papers.append(paper_id)
