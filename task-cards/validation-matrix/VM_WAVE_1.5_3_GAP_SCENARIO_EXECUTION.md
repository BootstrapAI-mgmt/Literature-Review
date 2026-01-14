# Task Card: Gap Scenario Execution Framework

**Task ID:** VM-W1.5-3  
**Wave:** 1.5 (Ground Truth Infrastructure)  
**Priority:** HIGH  
**Estimated Effort:** 6 hours  
**Status:** Not Started  
**Dependencies:** VM-W1.5-0, VM-W1.5-2  
**Blocks:** VM-W2-1, VM-W4-2  
**Validation IDs:** FP-02, FP-03, GAP-NEG, ITER-01

---

## Objective

Create an executable test framework for running controlled gap scenarios defined in VM-W1.5-0. This framework bridges the gap between gap scenario **design** (documented in VM-W1.5-0) and actual **execution** for validation testing.

### Why This Task is Critical

The gap scenario design template (VM-W1.5-0) defines WHAT to test, but we need:
1. **Isolated database states** - Create clean databases with only Pass 1 papers
2. **Scenario execution** - Run the pipeline and capture gap detection results
3. **Automated validation** - Compare actual vs expected gap behavior
4. **Decoy paper verification** - Confirm irrelevant papers don't contribute
5. **Severity transition tracking** - Validate gap closure across passes

This framework enables the following validation IDs:
- **FP-02:** Gap Detection False Positive Rate (0%)
- **FP-03:** Decoy Paper Contribution Rate (0%)
- **GAP-NEG:** Non-Gap Accuracy (100%)
- **ITER-01:** Iterative Gap Closure Accuracy (≥95%)

---

## Background

### Gap Scenario Structure (from VM-W1.5-0)

```yaml
scenario_id: "GAP-001"
scenario_type: "iterative"  # single_pass, iterative, edge_case

# Pass 1: Initial State
initial_papers: [...]
expected_gaps: [...]
expected_non_gaps: [...]

# Pass 2: Gap Closing
gap_closing_papers: [...]
decoy_papers: [...]

# Expected Outcomes
expected_final_coverage: {...}
expected_severity_changes: {...}
```

### Current Gap

The design is complete but no executable framework exists to:
1. Set up isolated database states
2. Run the pipeline with controlled inputs
3. Validate outputs against expectations
4. Generate pass/fail reports

---

## Success Criteria

- [ ] GapScenarioExecutor class fully implemented
- [ ] DatabaseStateManager for snapshot/restore operations
- [ ] ScenarioResult dataclass with validation logic
- [ ] pytest test suite for gap scenarios
- [ ] 3+ gap scenarios executable and passing
- [ ] FP-02, FP-03, GAP-NEG, ITER-01 metrics computable
- [ ] Scenario execution time <5 minutes per scenario
- [ ] CI integration ready (can run in GitHub Actions)

---

## Deliverables

### 1. Gap Scenario Executor

**File:** `tests/validation/gap_scenarios/executor.py`

```python
"""
Gap Scenario Execution Framework

Executes controlled gap scenarios to validate:
1. Correct gap detection (finding gaps that exist)
2. Correct non-gap handling (not flagging covered requirements)
3. Iterative gap closing (Pass 2 paper attribution)
4. Decoy paper rejection (irrelevant paper handling)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Pass1Result:
    """Result of Pass 1 gap detection."""
    gaps_detected: Dict[str, Dict]  # {req_id: {severity, completeness}}
    expected_gaps_found: List[str]
    expected_gaps_missed: List[str]
    non_gaps_correctly_ignored: List[str]
    non_gaps_incorrectly_flagged: List[str]  # False positives
    
    @property
    def all_required_gaps_detected(self) -> bool:
        return len(self.expected_gaps_missed) == 0
    
    @property
    def no_false_positive_gaps(self) -> bool:
        return len(self.non_gaps_incorrectly_flagged) == 0


@dataclass
class Pass2Result:
    """Result of Pass 2 gap closing."""
    severity_changes: Dict[str, str]  # {req_id: "CRITICAL → MEDIUM"}
    expected_changes: Dict[str, str]
    severity_changes_correct: bool
    decoy_paper_contributions: List[str]  # Should be empty
    
    @property
    def decoy_papers_rejected(self) -> bool:
        return len(self.decoy_paper_contributions) == 0


@dataclass
class ScenarioResult:
    """Complete result of gap scenario execution."""
    scenario_id: str
    scenario_type: str
    passed: bool
    
    pass_1_result: Pass1Result
    pass_2_result: Optional[Pass2Result] = None
    
    failure_reasons: List[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    
    # Metrics for validation IDs
    @property
    def fp_02_gap_false_positive_rate(self) -> float:
        """FP-02: Gap Detection False Positive Rate."""
        total_non_gaps = (
            len(self.pass_1_result.non_gaps_correctly_ignored) +
            len(self.pass_1_result.non_gaps_incorrectly_flagged)
        )
        if total_non_gaps == 0:
            return 0.0
        return len(self.pass_1_result.non_gaps_incorrectly_flagged) / total_non_gaps
    
    @property
    def fp_03_decoy_contribution_rate(self) -> float:
        """FP-03: Decoy Paper Contribution Rate."""
        if self.pass_2_result is None:
            return 0.0  # No Pass 2, no decoys
        # Would need total decoy count from scenario
        return len(self.pass_2_result.decoy_paper_contributions)
    
    @property
    def gap_neg_accuracy(self) -> float:
        """GAP-NEG: Non-Gap Accuracy."""
        total_non_gaps = (
            len(self.pass_1_result.non_gaps_correctly_ignored) +
            len(self.pass_1_result.non_gaps_incorrectly_flagged)
        )
        if total_non_gaps == 0:
            return 1.0
        return len(self.pass_1_result.non_gaps_correctly_ignored) / total_non_gaps
    
    @property
    def iter_01_accuracy(self) -> float:
        """ITER-01: Iterative Gap Closure Accuracy."""
        if self.pass_2_result is None:
            return 1.0  # No iteration to validate
        return 1.0 if self.pass_2_result.severity_changes_correct else 0.0


class GapScenarioExecutor:
    """Execute controlled gap scenarios for validation."""
    
    def __init__(
        self,
        pipeline_runner: Callable,
        database_manager: 'DatabaseStateManager',
        output_dir: Path
    ):
        """
        Initialize the executor.
        
        Args:
            pipeline_runner: Callable that runs the pipeline with given config
            database_manager: Manages database state snapshots
            output_dir: Directory for scenario output files
        """
        self.pipeline = pipeline_runner
        self.db = database_manager
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def execute_scenario(self, scenario: 'GapScenario') -> ScenarioResult:
        """
        Execute a gap scenario and validate results.
        
        Steps:
        1. Create isolated database with Pass 1 papers only
        2. Run gap detection pipeline
        3. Validate detected gaps against expected_gaps
        4. Validate non-flagged against expected_non_gaps
        5. (If iterative) Add Pass 2 papers and rerun
        6. Validate severity changes and decoy rejection
        """
        import time
        start_time = time.time()
        
        failure_reasons = []
        snapshot_id = None
        
        try:
            # Create snapshot for restoration
            snapshot_id = self.db.create_snapshot()
            
            # === PASS 1: INITIAL STATE ===
            logger.info(f"Executing Pass 1 for scenario {scenario.scenario_id}")
            
            # Set up database with only Pass 1 papers
            self.db.clear()
            for paper in scenario.initial_papers:
                self.db.add_paper(paper.paper_id, paper.provides_coverage)
            
            # Run pipeline
            pass_1_output = self.pipeline(mode='full')
            pass_1_gaps = self._parse_gap_report(pass_1_output)
            
            # Validate Pass 1 - expected gaps detected
            expected_gaps_found = []
            expected_gaps_missed = []
            for expected in scenario.expected_gaps:
                if expected.must_be_detected:
                    if expected.requirement_id in pass_1_gaps:
                        expected_gaps_found.append(expected.requirement_id)
                    else:
                        expected_gaps_missed.append(expected.requirement_id)
                        failure_reasons.append(
                            f"Pass 1: Expected gap {expected.requirement_id} not detected"
                        )
            
            # Validate Pass 1 - non-gaps not flagged
            non_gaps_correct = []
            non_gaps_flagged = []
            for non_gap in scenario.expected_non_gaps:
                if non_gap.requirement_id in pass_1_gaps:
                    non_gaps_flagged.append(non_gap.requirement_id)
                    failure_reasons.append(
                        f"Pass 1: Non-gap {non_gap.requirement_id} incorrectly flagged"
                    )
                else:
                    non_gaps_correct.append(non_gap.requirement_id)
            
            pass_1_result = Pass1Result(
                gaps_detected=pass_1_gaps,
                expected_gaps_found=expected_gaps_found,
                expected_gaps_missed=expected_gaps_missed,
                non_gaps_correctly_ignored=non_gaps_correct,
                non_gaps_incorrectly_flagged=non_gaps_flagged
            )
            
            # === PASS 2: GAP CLOSING (if iterative) ===
            pass_2_result = None
            
            if scenario.scenario_type == 'iterative':
                logger.info(f"Executing Pass 2 for scenario {scenario.scenario_id}")
                
                # Add gap-closing papers
                for paper in scenario.gap_closing_papers:
                    self.db.add_paper(paper.paper_id, paper.provides_coverage)
                
                # Add decoy papers
                for decoy in scenario.decoy_papers:
                    self.db.add_paper(decoy.paper_id, [])
                
                # Run pipeline in incremental mode
                pass_2_output = self.pipeline(mode='incremental')
                pass_2_gaps = self._parse_gap_report(pass_2_output)
                
                # Check severity changes
                severity_changes = {}
                severity_correct = True
                for req_id, expected_change in scenario.expected_severity_changes.items():
                    pass_1_severity = pass_1_gaps.get(req_id, {}).get('severity', 'NONE')
                    pass_2_severity = pass_2_gaps.get(req_id, {}).get('severity', 'NONE')
                    actual_change = f"{pass_1_severity} → {pass_2_severity}"
                    severity_changes[req_id] = actual_change
                    
                    if actual_change != expected_change:
                        severity_correct = False
                        failure_reasons.append(
                            f"Pass 2: {req_id} change was {actual_change}, expected {expected_change}"
                        )
                
                # Check decoy papers didn't contribute
                contributions = self._parse_contributions(pass_2_output)
                decoy_contributions = []
                for decoy in scenario.decoy_papers:
                    for req_id in decoy.should_not_close:
                        if self._paper_contributed(contributions, decoy.paper_id, req_id):
                            decoy_contributions.append(f"{decoy.paper_id} → {req_id}")
                            failure_reasons.append(
                                f"Pass 2: Decoy {decoy.paper_id} incorrectly contributed to {req_id}"
                            )
                
                pass_2_result = Pass2Result(
                    severity_changes=severity_changes,
                    expected_changes=scenario.expected_severity_changes,
                    severity_changes_correct=severity_correct,
                    decoy_paper_contributions=decoy_contributions
                )
            
            execution_time = time.time() - start_time
            passed = len(failure_reasons) == 0
            
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                scenario_type=scenario.scenario_type,
                passed=passed,
                pass_1_result=pass_1_result,
                pass_2_result=pass_2_result,
                failure_reasons=failure_reasons,
                execution_time_seconds=execution_time
            )
            
        finally:
            # Restore database state
            if snapshot_id:
                self.db.restore_snapshot(snapshot_id)
    
    def _parse_gap_report(self, output: Dict) -> Dict[str, Dict]:
        """Parse gap_analysis_report.json output."""
        gaps = {}
        for gap in output.get('gaps', []):
            gaps[gap['requirement_id']] = {
                'severity': gap.get('severity'),
                'completeness': gap.get('completeness')
            }
        return gaps
    
    def _parse_contributions(self, output: Dict) -> List[Dict]:
        """Parse paper contributions from output."""
        return output.get('contributions', [])
    
    def _paper_contributed(
        self, contributions: List[Dict], paper_id: str, req_id: str
    ) -> bool:
        """Check if a paper contributed to a specific requirement."""
        for contrib in contributions:
            if contrib.get('paper_id') == paper_id:
                if req_id in contrib.get('requirements', []):
                    return True
        return False
```

### 2. Database State Manager

**File:** `tests/validation/gap_scenarios/state_manager.py`

```python
"""
Database State Management for Gap Scenario Testing

Provides isolated database states for controlled testing scenarios.
"""

from pathlib import Path
from typing import List, Dict, Optional
import shutil
import json
import sqlite3
import uuid


class DatabaseStateManager:
    """Manage database states for scenario testing."""
    
    def __init__(self, base_db_path: Path, snapshots_dir: Path):
        """
        Initialize the state manager.
        
        Args:
            base_db_path: Path to the main database file
            snapshots_dir: Directory for storing database snapshots
        """
        self.base_db_path = base_db_path
        self.snapshots_dir = snapshots_dir
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.current_papers: Dict[str, Dict] = {}
    
    def create_snapshot(self) -> str:
        """
        Create named database snapshot.
        
        Returns:
            Snapshot ID for restoration
        """
        snapshot_id = str(uuid.uuid4())[:8]
        snapshot_path = self.snapshots_dir / f"snapshot_{snapshot_id}"
        
        if self.base_db_path.exists():
            if self.base_db_path.is_dir():
                shutil.copytree(self.base_db_path, snapshot_path)
            else:
                snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.base_db_path, snapshot_path)
        
        # Also snapshot in-memory state
        state_file = snapshot_path.with_suffix('.state.json')
        with open(state_file, 'w') as f:
            json.dump(self.current_papers, f)
        
        return snapshot_id
    
    def restore_snapshot(self, snapshot_id: str):
        """
        Restore database to named snapshot.
        
        Args:
            snapshot_id: ID from create_snapshot()
        """
        snapshot_path = self.snapshots_dir / f"snapshot_{snapshot_id}"
        
        if snapshot_path.exists():
            if self.base_db_path.exists():
                if self.base_db_path.is_dir():
                    shutil.rmtree(self.base_db_path)
                else:
                    self.base_db_path.unlink()
            
            if snapshot_path.is_dir():
                shutil.copytree(snapshot_path, self.base_db_path)
            else:
                shutil.copy2(snapshot_path, self.base_db_path)
        
        # Restore in-memory state
        state_file = snapshot_path.with_suffix('.state.json')
        if state_file.exists():
            with open(state_file) as f:
                self.current_papers = json.load(f)
        
        # Cleanup snapshot
        self._cleanup_snapshot(snapshot_id)
    
    def _cleanup_snapshot(self, snapshot_id: str):
        """Remove snapshot files."""
        snapshot_path = self.snapshots_dir / f"snapshot_{snapshot_id}"
        state_file = snapshot_path.with_suffix('.state.json')
        
        if snapshot_path.exists():
            if snapshot_path.is_dir():
                shutil.rmtree(snapshot_path)
            else:
                snapshot_path.unlink()
        
        if state_file.exists():
            state_file.unlink()
    
    def clear(self):
        """Clear current database state."""
        self.current_papers = {}
        # Actual database clearing would depend on implementation
    
    def add_paper(self, paper_id: str, coverage: Optional[List[Dict]] = None):
        """
        Add a paper to the current database state.
        
        Args:
            paper_id: Paper identifier
            coverage: List of requirement coverage contributions
        """
        self.current_papers[paper_id] = {
            'paper_id': paper_id,
            'coverage': coverage or []
        }
    
    def create_isolated_state(self, papers: List[str]) -> Path:
        """
        Create isolated database with specific papers.
        
        Args:
            papers: List of paper IDs to include
            
        Returns:
            Path to isolated database
        """
        isolated_id = str(uuid.uuid4())[:8]
        isolated_path = self.snapshots_dir / f"isolated_{isolated_id}"
        
        # Create new database with only specified papers
        self.clear()
        for paper_id in papers:
            self.add_paper(paper_id)
        
        return isolated_path
    
    def get_paper_count(self) -> int:
        """Return number of papers in current state."""
        return len(self.current_papers)
```

### 3. Scenario Test Suite

**File:** `tests/validation/gap_scenarios/test_scenarios.py`

```python
"""
Gap Scenario Test Suite

Pytest tests for executing controlled gap scenarios.
"""

import pytest
from pathlib import Path
from typing import Dict, List
import json

from .executor import GapScenarioExecutor, ScenarioResult
from .state_manager import DatabaseStateManager


# Fixture paths
SCENARIOS_DIR = Path(__file__).parent / "scenarios"
OUTPUT_DIR = Path(__file__).parent / "output"


@pytest.fixture
def gap_scenarios() -> Dict[str, 'GapScenario']:
    """Load all gap scenarios from YAML/JSON files."""
    from tests.golden_dataset.schema_anchor import GapScenario
    
    scenarios = {}
    for scenario_file in SCENARIOS_DIR.glob("*.json"):
        with open(scenario_file) as f:
            data = json.load(f)
            scenario = GapScenario(**data)
            scenarios[scenario.scenario_id] = scenario
    
    return scenarios


@pytest.fixture
def database_manager(tmp_path) -> DatabaseStateManager:
    """Create a temporary database state manager."""
    db_path = tmp_path / "test_db"
    snapshots_dir = tmp_path / "snapshots"
    return DatabaseStateManager(db_path, snapshots_dir)


@pytest.fixture
def mock_pipeline():
    """Create a mock pipeline runner for testing."""
    def run_pipeline(mode: str = 'full') -> Dict:
        # Return mock gap analysis output
        return {
            'gaps': [
                {'requirement_id': 'REQ-B1.4', 'severity': 'CRITICAL', 'completeness': 0},
            ],
            'contributions': []
        }
    return run_pipeline


class TestGapScenarios:
    """Test suite for gap scenario validation."""
    
    @pytest.mark.parametrize("scenario_id", ["GAP-001", "GAP-002", "GAP-003"])
    def test_gap_scenario_execution(
        self,
        scenario_id: str,
        gap_scenarios: Dict,
        database_manager: DatabaseStateManager,
        mock_pipeline
    ):
        """Execute and validate each gap scenario."""
        if scenario_id not in gap_scenarios:
            pytest.skip(f"Scenario {scenario_id} not found")
        
        scenario = gap_scenarios[scenario_id]
        executor = GapScenarioExecutor(
            pipeline_runner=mock_pipeline,
            database_manager=database_manager,
            output_dir=OUTPUT_DIR
        )
        
        result = executor.execute_scenario(scenario)
        
        # Assert Pass 1 validations
        assert result.pass_1_result.all_required_gaps_detected, \
            f"Missing gaps: {result.pass_1_result.expected_gaps_missed}"
        assert result.pass_1_result.no_false_positive_gaps, \
            f"False positive gaps: {result.pass_1_result.non_gaps_incorrectly_flagged}"
        
        # Assert Pass 2 validations (if iterative)
        if result.pass_2_result:
            assert result.pass_2_result.severity_changes_correct, \
                f"Incorrect severity changes"
            assert result.pass_2_result.decoy_papers_rejected, \
                f"Decoy papers contributed: {result.pass_2_result.decoy_paper_contributions}"
        
        # Assert overall pass
        assert result.passed, f"Scenario failed: {result.failure_reasons}"
    
    def test_fp_02_gap_false_positive_rate(
        self,
        gap_scenarios: Dict,
        database_manager: DatabaseStateManager,
        mock_pipeline
    ):
        """FP-02: Validate gap detection false positive rate is 0%."""
        executor = GapScenarioExecutor(
            pipeline_runner=mock_pipeline,
            database_manager=database_manager,
            output_dir=OUTPUT_DIR
        )
        
        total_fp_rate = 0.0
        scenario_count = 0
        
        for scenario_id, scenario in gap_scenarios.items():
            result = executor.execute_scenario(scenario)
            total_fp_rate += result.fp_02_gap_false_positive_rate
            scenario_count += 1
        
        avg_fp_rate = total_fp_rate / scenario_count if scenario_count > 0 else 0.0
        assert avg_fp_rate == 0.0, f"Gap false positive rate: {avg_fp_rate}"
    
    def test_fp_03_decoy_contribution_rate(
        self,
        gap_scenarios: Dict,
        database_manager: DatabaseStateManager,
        mock_pipeline
    ):
        """FP-03: Validate decoy papers don't contribute to gaps."""
        executor = GapScenarioExecutor(
            pipeline_runner=mock_pipeline,
            database_manager=database_manager,
            output_dir=OUTPUT_DIR
        )
        
        decoy_contributions = 0
        
        for scenario_id, scenario in gap_scenarios.items():
            if scenario.scenario_type == 'iterative':
                result = executor.execute_scenario(scenario)
                decoy_contributions += len(result.pass_2_result.decoy_paper_contributions) \
                    if result.pass_2_result else 0
        
        assert decoy_contributions == 0, f"Decoy contributions: {decoy_contributions}"
    
    def test_gap_neg_accuracy(
        self,
        gap_scenarios: Dict,
        database_manager: DatabaseStateManager,
        mock_pipeline
    ):
        """GAP-NEG: Validate non-gap accuracy is 100%."""
        executor = GapScenarioExecutor(
            pipeline_runner=mock_pipeline,
            database_manager=database_manager,
            output_dir=OUTPUT_DIR
        )
        
        total_accuracy = 0.0
        scenario_count = 0
        
        for scenario_id, scenario in gap_scenarios.items():
            result = executor.execute_scenario(scenario)
            total_accuracy += result.gap_neg_accuracy
            scenario_count += 1
        
        avg_accuracy = total_accuracy / scenario_count if scenario_count > 0 else 1.0
        assert avg_accuracy == 1.0, f"Non-gap accuracy: {avg_accuracy}"
    
    def test_iter_01_accuracy(
        self,
        gap_scenarios: Dict,
        database_manager: DatabaseStateManager,
        mock_pipeline
    ):
        """ITER-01: Validate iterative gap closure accuracy ≥95%."""
        executor = GapScenarioExecutor(
            pipeline_runner=mock_pipeline,
            database_manager=database_manager,
            output_dir=OUTPUT_DIR
        )
        
        total_accuracy = 0.0
        iterative_count = 0
        
        for scenario_id, scenario in gap_scenarios.items():
            if scenario.scenario_type == 'iterative':
                result = executor.execute_scenario(scenario)
                total_accuracy += result.iter_01_accuracy
                iterative_count += 1
        
        if iterative_count > 0:
            avg_accuracy = total_accuracy / iterative_count
            assert avg_accuracy >= 0.95, f"Iterative accuracy: {avg_accuracy}"


class TestScenarioMetrics:
    """Tests for scenario-derived metrics."""
    
    def test_all_metrics_computable(
        self,
        gap_scenarios: Dict,
        database_manager: DatabaseStateManager,
        mock_pipeline
    ):
        """Verify all validation metrics can be computed."""
        executor = GapScenarioExecutor(
            pipeline_runner=mock_pipeline,
            database_manager=database_manager,
            output_dir=OUTPUT_DIR
        )
        
        for scenario_id, scenario in gap_scenarios.items():
            result = executor.execute_scenario(scenario)
            
            # All metrics should be computable without errors
            assert isinstance(result.fp_02_gap_false_positive_rate, float)
            assert isinstance(result.fp_03_decoy_contribution_rate, (int, float))
            assert isinstance(result.gap_neg_accuracy, float)
            assert isinstance(result.iter_01_accuracy, float)
            
            # Metrics should be in valid ranges
            assert 0.0 <= result.fp_02_gap_false_positive_rate <= 1.0
            assert result.fp_03_decoy_contribution_rate >= 0
            assert 0.0 <= result.gap_neg_accuracy <= 1.0
            assert 0.0 <= result.iter_01_accuracy <= 1.0
```

### 4. Sample Scenario Definition

**File:** `tests/validation/gap_scenarios/scenarios/GAP-001.json`

```json
{
  "scenario_id": "GAP-001",
  "scenario_name": "STDP Learning Rule Gap",
  "scenario_type": "iterative",
  
  "initial_papers": [
    {
      "paper_id": "NEURO-001",
      "provides_coverage": [
        {"requirement": "REQ-B1.1", "completeness_contribution": 45}
      ]
    },
    {
      "paper_id": "NEURO-002",
      "provides_coverage": [
        {"requirement": "REQ-B1.2", "completeness_contribution": 30}
      ]
    }
  ],
  
  "expected_gaps": [
    {
      "requirement_id": "REQ-B1.4",
      "expected_severity": "CRITICAL",
      "expected_completeness": 0,
      "must_be_detected": true,
      "if_not_detected_severity": "error"
    }
  ],
  
  "expected_non_gaps": [
    {
      "requirement_id": "REQ-B1.1",
      "current_completeness": 45,
      "reason": "45% exceeds gap threshold",
      "if_flagged_as_gap_severity": "error"
    }
  ],
  
  "gap_closing_papers": [
    {
      "paper_id": "NEURO-003",
      "provides_coverage": [
        {"requirement": "REQ-B1.4", "completeness_contribution": 60}
      ]
    }
  ],
  
  "decoy_papers": [
    {
      "paper_id": "CLIMATE-001",
      "should_not_close": ["REQ-B1.4"],
      "reason": "Climate paper, not relevant to neuromorphic",
      "if_contributes_severity": "critical_error"
    },
    {
      "paper_id": "NEURO-004",
      "should_not_close": ["REQ-B1.4"],
      "reason": "Addresses inference, not learning",
      "if_contributes_severity": "error"
    }
  ],
  
  "expected_final_coverage": {
    "REQ-B1.1": 45,
    "REQ-B1.2": 30,
    "REQ-B1.4": 60
  },
  
  "expected_severity_changes": {
    "REQ-B1.4": "CRITICAL → MEDIUM"
  },
  
  "designer": "validation_team",
  "design_date": "2026-01-13T00:00:00Z",
  "validated": false
}
```

---

## Implementation Plan

### Phase 1: Core Framework (2 hours)
1. Implement `DatabaseStateManager` class
2. Implement `GapScenarioExecutor` class
3. Create `ScenarioResult` and helper dataclasses

### Phase 2: Test Suite (2 hours)
1. Create pytest fixtures for scenarios
2. Implement test classes for each validation ID
3. Add metric computation tests

### Phase 3: Scenario Files (1 hour)
1. Create GAP-001, GAP-002, GAP-003 scenario JSON files
2. Validate scenarios against schema
3. Document scenario design rationale

### Phase 4: Integration (1 hour)
1. Integrate with actual pipeline runner
2. Add CI configuration for scenario tests
3. Generate execution reports

---

## Acceptance Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Executor class implemented | Complete | Unit tests pass |
| State manager implemented | Complete | Snapshot/restore works |
| Test suite created | Complete | pytest collects all tests |
| Scenarios defined | ≥3 | JSON files validated |
| FP-02 metric | 0.0 | Test assertion |
| FP-03 metric | 0 contributions | Test assertion |
| GAP-NEG metric | 1.0 | Test assertion |
| ITER-01 metric | ≥0.95 | Test assertion |
| Execution time | <5 min/scenario | Timing assertion |

---

## Integration with Other Tasks

### Dependencies

| Task | Provides |
|------|----------|
| VM-W1.5-0 | GapScenario schema, scenario design template |
| VM-W1.5-2 | Annotated anchor papers, decoy paper annotations |

### Enables

| Task | Uses |
|------|------|
| VM-W2-1 | FP-02, GAP-NEG metrics for accuracy baseline |
| VM-W4-2 | ITER-01 metric for quality benchmarks |

---

## Directory Structure

```
tests/validation/gap_scenarios/
├── __init__.py
├── executor.py           # GapScenarioExecutor class
├── state_manager.py      # DatabaseStateManager class
├── test_scenarios.py     # Pytest test suite
├── scenarios/            # Scenario definition files
│   ├── GAP-001.json
│   ├── GAP-002.json
│   └── GAP-003.json
└── output/               # Execution output files
    └── .gitkeep
```

---

## Notes

- **Mock pipeline:** Start with mocked pipeline for faster iteration
- **Real integration:** Add flag to use actual pipeline for full validation
- **Performance:** Consider parallel scenario execution if needed
- **CI compatibility:** Ensure tests can run in GitHub Actions environment
- **Cleanup:** Snapshots are auto-deleted after restoration to avoid disk buildup
