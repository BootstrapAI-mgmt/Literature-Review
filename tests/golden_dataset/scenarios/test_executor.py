"""
Tests for Gap Scenario Executor

Tests the controlled gap scenario execution framework.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from tests.golden_dataset.scenarios.executor import (
    GapScenarioExecutor,
    ScenarioResult,
    MockPipelineRunner,
    MockDatabaseManager,
)
from tests.golden_dataset.schema_anchor import (
    GapScenario,
    GapScenarioPaper,
    ExpectedGap,
    ExpectedNonGap,
    DecoyPaper,
    DetectionSeverity,
)


class TestMockComponents:
    """Tests for mock components."""
    
    def test_mock_pipeline_runner(self):
        """Test mock pipeline runner."""
        outputs = {
            'full': {'gaps': [{'requirement_id': 'REQ-B1.4', 'severity': 'CRITICAL'}]},
            'incremental': {'gaps': [], 'contributions': []},
        }
        runner = MockPipelineRunner(outputs)
        
        result_full = runner.run(mode='full')
        assert 'gaps' in result_full
        assert len(result_full['gaps']) == 1
        
        result_incr = runner.run(mode='incremental')
        assert len(result_incr['gaps']) == 0
        assert runner.run_count == 2
    
    def test_mock_database_manager(self):
        """Test mock database manager."""
        db = MockDatabaseManager()
        
        # Add papers
        db.add_paper("PAPER-001")
        db.add_paper("PAPER-002")
        assert len(db.papers) == 2
        
        # Create snapshot
        snapshot = db.create_snapshot()
        assert snapshot.startswith("snapshot_")
        
        # Clear and verify
        db.clear()
        assert len(db.papers) == 0
        
        # Restore
        db.restore_snapshot(snapshot)
        assert len(db.papers) == 2


class TestScenarioResult:
    """Tests for ScenarioResult dataclass."""
    
    def test_scenario_result_passed(self):
        """Test successful scenario result."""
        result = ScenarioResult(
            scenario_id="GAP-001",
            passed=True,
            pass_1_gaps_detected=["REQ-B1.4"],
            pass_1_false_gaps=[],
            pass_1_missed_gaps=[],
        )
        assert result.passed is True
        assert len(result.failure_reasons) == 0
    
    def test_scenario_result_failed(self):
        """Test failed scenario result."""
        result = ScenarioResult(
            scenario_id="GAP-001",
            passed=False,
            pass_1_gaps_detected=[],
            pass_1_false_gaps=[],
            pass_1_missed_gaps=["REQ-B1.4"],
            failure_reasons=["Expected gap REQ-B1.4 not detected"],
        )
        assert result.passed is False
        assert len(result.failure_reasons) == 1


class TestGapScenarioExecutor:
    """Tests for GapScenarioExecutor."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def basic_scenario(self):
        """Create a basic gap scenario for testing."""
        return GapScenario(
            scenario_id="GAP-001",
            scenario_name="Test Gap Scenario",
            scenario_type="single_pass",
            initial_papers=[
                GapScenarioPaper(paper_id="NEURO-001", provides_coverage=[])
            ],
            expected_gaps=[
                ExpectedGap(
                    requirement_id="REQ-B1.4",
                    expected_severity="CRITICAL",
                    expected_completeness=0,
                    must_be_detected=True,
                )
            ],
            expected_non_gaps=[
                ExpectedNonGap(
                    requirement_id="REQ-B1.1",
                    current_completeness=45,
                    reason="Already covered",
                )
            ],
            designer="test_designer",
            design_date=datetime(2025, 1, 15),
        )
    
    def test_executor_initialization(self, temp_output_dir):
        """Test executor initialization."""
        runner = MockPipelineRunner()
        db = MockDatabaseManager()
        
        executor = GapScenarioExecutor(runner, db, temp_output_dir)
        assert executor.output_dir == temp_output_dir
    
    def test_execute_scenario_pass(self, temp_output_dir, basic_scenario):
        """Test executing a passing scenario."""
        outputs = {
            'full': {
                'gaps': [
                    {'requirement_id': 'REQ-B1.4', 'severity': 'CRITICAL'}
                ]
            }
        }
        runner = MockPipelineRunner(outputs)
        db = MockDatabaseManager()
        
        executor = GapScenarioExecutor(runner, db, temp_output_dir)
        result = executor.execute_scenario(basic_scenario)
        
        assert result.passed is True
        assert "REQ-B1.4" in result.pass_1_gaps_detected
        assert len(result.pass_1_missed_gaps) == 0
        assert len(result.pass_1_false_gaps) == 0
    
    def test_execute_scenario_missed_gap(self, temp_output_dir, basic_scenario):
        """Test scenario failing due to missed gap."""
        # Pipeline doesn't detect the expected gap
        outputs = {'full': {'gaps': []}}
        runner = MockPipelineRunner(outputs)
        db = MockDatabaseManager()
        
        executor = GapScenarioExecutor(runner, db, temp_output_dir)
        result = executor.execute_scenario(basic_scenario)
        
        assert result.passed is False
        assert "REQ-B1.4" in result.pass_1_missed_gaps
        assert any("not detected" in r for r in result.failure_reasons)
    
    def test_execute_scenario_false_gap(self, temp_output_dir, basic_scenario):
        """Test scenario failing due to false gap detection."""
        # Pipeline incorrectly flags REQ-B1.1 as a gap
        outputs = {
            'full': {
                'gaps': [
                    {'requirement_id': 'REQ-B1.4', 'severity': 'CRITICAL'},
                    {'requirement_id': 'REQ-B1.1', 'severity': 'HIGH'},  # False positive
                ]
            }
        }
        runner = MockPipelineRunner(outputs)
        db = MockDatabaseManager()
        
        executor = GapScenarioExecutor(runner, db, temp_output_dir)
        result = executor.execute_scenario(basic_scenario)
        
        assert result.passed is False
        assert "REQ-B1.1" in result.pass_1_false_gaps
        assert any("incorrectly flagged" in r for r in result.failure_reasons)
    
    def test_execute_iterative_scenario(self, temp_output_dir):
        """Test executing an iterative gap scenario."""
        scenario = GapScenario(
            scenario_id="GAP-002",
            scenario_name="Iterative Test",
            scenario_type="iterative",
            initial_papers=[GapScenarioPaper(paper_id="NEURO-001")],
            expected_gaps=[
                ExpectedGap(
                    requirement_id="REQ-B1.4",
                    expected_severity="CRITICAL",
                    expected_completeness=0,
                )
            ],
            gap_closing_papers=[GapScenarioPaper(paper_id="NEURO-002")],
            decoy_papers=[
                DecoyPaper(
                    paper_id="CLIMATE-001",
                    should_not_close=["REQ-B1.4"],
                    reason="Wrong domain",
                )
            ],
            expected_severity_changes={"REQ-B1.4": "CRITICAL → MEDIUM"},
            designer="test",
            design_date=datetime(2025, 1, 15),
        )
        
        outputs = {
            'full': {
                'gaps': [
                    {'requirement_id': 'REQ-B1.4', 'severity': 'CRITICAL'}
                ]
            },
            'incremental': {
                'gaps': [
                    {'requirement_id': 'REQ-B1.4', 'severity': 'MEDIUM'}
                ],
                'contributions': [
                    {'paper_id': 'NEURO-002', 'requirements': ['REQ-B1.4']}
                ]
            }
        }
        runner = MockPipelineRunner(outputs)
        db = MockDatabaseManager()
        
        executor = GapScenarioExecutor(runner, db, temp_output_dir)
        result = executor.execute_scenario(scenario)
        
        assert result.passed is True
        assert "REQ-B1.4" in result.pass_2_severity_changes
        assert len(result.pass_2_decoy_contributions) == 0
    
    def test_execute_scenario_decoy_contribution(self, temp_output_dir):
        """Test scenario failing due to decoy paper contribution."""
        scenario = GapScenario(
            scenario_id="GAP-003",
            scenario_name="Decoy Test",
            scenario_type="iterative",
            initial_papers=[GapScenarioPaper(paper_id="NEURO-001")],
            expected_gaps=[
                ExpectedGap(
                    requirement_id="REQ-B1.4",
                    expected_severity="CRITICAL",
                    expected_completeness=0,
                )
            ],
            decoy_papers=[
                DecoyPaper(
                    paper_id="CLIMATE-001",
                    should_not_close=["REQ-B1.4"],
                    reason="Wrong domain",
                )
            ],
            expected_severity_changes={"REQ-B1.4": "CRITICAL → MEDIUM"},
            designer="test",
            design_date=datetime(2025, 1, 15),
        )
        
        outputs = {
            'full': {
                'gaps': [{'requirement_id': 'REQ-B1.4', 'severity': 'CRITICAL'}]
            },
            'incremental': {
                'gaps': [{'requirement_id': 'REQ-B1.4', 'severity': 'MEDIUM'}],
                'contributions': [
                    {'paper_id': 'CLIMATE-001', 'requirements': ['REQ-B1.4']}  # Bad!
                ]
            }
        }
        runner = MockPipelineRunner(outputs)
        db = MockDatabaseManager()
        
        executor = GapScenarioExecutor(runner, db, temp_output_dir)
        result = executor.execute_scenario(scenario)
        
        assert result.passed is False
        assert "CLIMATE-001 → REQ-B1.4" in result.pass_2_decoy_contributions
        assert any("Decoy" in r for r in result.failure_reasons)
    
    def test_execute_all_scenarios(self, temp_output_dir):
        """Test executing multiple scenarios."""
        scenarios = [
            GapScenario(
                scenario_id="GAP-001",
                scenario_name="Test 1",
                scenario_type="single_pass",
                initial_papers=[GapScenarioPaper(paper_id="NEURO-001")],
                expected_gaps=[],
                designer="test",
                design_date=datetime(2025, 1, 15),
            ),
            GapScenario(
                scenario_id="GAP-002",
                scenario_name="Test 2",
                scenario_type="single_pass",
                initial_papers=[GapScenarioPaper(paper_id="NEURO-002")],
                expected_gaps=[],
                designer="test",
                design_date=datetime(2025, 1, 15),
            ),
        ]
        
        runner = MockPipelineRunner({'full': {'gaps': []}})
        db = MockDatabaseManager()
        
        executor = GapScenarioExecutor(runner, db, temp_output_dir)
        results = executor.execute_all(scenarios)
        
        assert len(results) == 2
        assert "GAP-001" in results
        assert "GAP-002" in results
        assert all(r.passed for r in results.values())
    
    def test_database_state_restored(self, temp_output_dir, basic_scenario):
        """Test that database state is restored after execution."""
        runner = MockPipelineRunner({'full': {'gaps': []}})
        db = MockDatabaseManager()
        
        # Pre-populate database
        db.add_paper("EXISTING-001")
        initial_papers = list(db.papers)
        
        executor = GapScenarioExecutor(runner, db, temp_output_dir)
        executor.execute_scenario(basic_scenario)
        
        # Database should be restored to initial state
        assert db.papers == initial_papers
    
    def test_execution_log_saved(self, temp_output_dir, basic_scenario):
        """Test that execution log is saved."""
        outputs = {'full': {'gaps': [{'requirement_id': 'REQ-B1.4', 'severity': 'CRITICAL'}]}}
        runner = MockPipelineRunner(outputs)
        db = MockDatabaseManager()
        
        executor = GapScenarioExecutor(runner, db, temp_output_dir)
        executor.execute_scenario(basic_scenario)
        
        log_file = temp_output_dir / "GAP-001_execution.json"
        assert log_file.exists()
