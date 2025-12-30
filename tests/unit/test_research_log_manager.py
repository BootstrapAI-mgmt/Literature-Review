"""Unit tests for research log manager."""

import pytest
import json
from pathlib import Path
from datetime import datetime

from literature_review.analysis.research_log_manager import (
    ResearchLogManager,
    ResearchSession,
    PillarResearchState,
    SaturationLevel,
    ResearchPhase,
    record_research_session
)


class TestResearchSession:
    """Tests for ResearchSession dataclass."""
    
    def test_create_session(self):
        """Test creating a session."""
        session = ResearchSession(
            session_id="20251219120000",
            timestamp="2025-12-19T12:00:00",
            papers_added=5,
            papers_removed=0,
            claims_extracted=15,
            claims_approved=10,
            coverage_delta=5.5
        )
        
        assert session.papers_added == 5
        assert session.coverage_delta == 5.5
    
    def test_to_dict(self):
        """Test serialization."""
        session = ResearchSession(
            session_id="test",
            timestamp="2025-12-19T12:00:00",
            papers_added=3,
            papers_removed=1,
            claims_extracted=10,
            claims_approved=7,
            coverage_delta=2.5
        )
        
        data = session.to_dict()
        assert data["papers_added"] == 3
        assert data["coverage_delta"] == 2.5


class TestPillarResearchState:
    """Tests for PillarResearchState."""
    
    def test_initial_state(self):
        """Test initial state values."""
        state = PillarResearchState(
            pillar_id="Pillar 1",
            pillar_name="Pillar 1: Biological Stimulus-Response"
        )
        
        assert state.current_coverage == 0.0
        assert state.saturation_level == SaturationLevel.UNSATURATED
        assert state.research_phase == ResearchPhase.INITIAL
    
    def test_to_dict(self):
        """Test serialization."""
        state = PillarResearchState(
            pillar_id="Pillar 1",
            pillar_name="Test Pillar",
            current_coverage=45.5,
            saturation_level=SaturationLevel.APPROACHING
        )
        
        data = state.to_dict()
        assert data["current_coverage"] == 45.5
        assert data["saturation_level"] == "approaching"


class TestResearchLogManager:
    """Tests for ResearchLogManager class."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {
            "Pillar 1: Biological Stimulus-Response": {
                "requirements": {
                    "REQ-B1.1": [{"id": "Sub-1.1.1", "text": "Test"}]
                }
            },
            "Pillar 2: AI Stimulus-Response": {
                "requirements": {
                    "REQ-A2.1": [{"id": "Sub-2.1.1", "text": "Test"}]
                }
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    @pytest.fixture
    def sample_gap_analysis(self, tmp_path):
        """Create sample gap analysis."""
        gap = {
            "Pillar 1: Biological Stimulus-Response": {
                "average_completeness": 45.5,
                "analysis": {
                    "REQ-B1.1": {
                        "Sub-1.1.1": {
                            "completeness_percent": 60,
                            "contributing_papers": [
                                {"filename": "paper1.pdf"},
                                {"filename": "paper2.pdf"}
                            ]
                        }
                    }
                }
            },
            "Pillar 2: AI Stimulus-Response": {
                "average_completeness": 25.0,
                "analysis": {}
            }
        }
        
        path = tmp_path / "gap_analysis.json"
        with open(path, 'w') as f:
            json.dump(gap, f)
        
        return str(path)
    
    @pytest.fixture
    def sample_version_history(self, tmp_path):
        """Create sample version history."""
        history = {
            "paper1.pdf": {
                "claims": [
                    {"pillar": "Pillar 1", "approved": True},
                    {"pillar": "Pillar 1", "approved": False}
                ]
            }
        }
        
        path = tmp_path / "version_history.json"
        with open(path, 'w') as f:
            json.dump(history, f)
        
        return str(path)
    
    def test_initialize(self, sample_pillar_definitions):
        """Test manager initialization."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        assert len(manager.pillar_states) == 2
        assert "Pillar 1" in manager.pillar_states
    
    def test_record_session(
        self, 
        sample_pillar_definitions, 
        sample_gap_analysis,
        sample_version_history,
        tmp_path
    ):
        """Test recording a session."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        with open(sample_version_history) as f:
            history = json.load(f)
        
        log = manager.record_session(gap, history, "test-session")
        
        assert "summary" in log
        assert "pillars" in log
        assert log["pillars"]["Pillar 1"]["current_coverage"] == 45.5
    
    def test_saturation_calculation(self, sample_pillar_definitions, tmp_path):
        """Test saturation calculation with multiple sessions."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        state = manager.pillar_states["Pillar 1"]
        
        # Add sessions with decreasing velocity
        for i in range(6):
            session = ResearchSession(
                session_id=f"session-{i}",
                timestamp=datetime.now().isoformat(),
                papers_added=5 - i,  # Decreasing papers
                papers_removed=0,
                claims_extracted=10 - i,  # Decreasing claims
                claims_approved=5 - i // 2,
                coverage_delta=10 - i * 2  # Decreasing coverage gain
            )
            state.sessions.append(session)
            state.current_coverage += session.coverage_delta
        
        manager._update_saturation_metrics(state)
        
        # Should detect some saturation due to decreasing velocity
        assert state.saturation_score > 0
    
    def test_phase_transitions(self, sample_pillar_definitions):
        """Test research phase transitions."""
        manager = ResearchLogManager(sample_pillar_definitions)
        state = manager.pillar_states["Pillar 1"]
        
        # Initial phase
        assert state.research_phase == ResearchPhase.INITIAL
        
        # Move to exploration
        state.current_coverage = 25
        manager._update_phase(state)
        assert state.research_phase == ResearchPhase.EXPLORATION
        
        # Move to consolidation
        state.current_coverage = 55
        manager._update_phase(state)
        assert state.research_phase == ResearchPhase.CONSOLIDATION
    
    def test_focus_recommendations(self, sample_pillar_definitions):
        """Test focus recommendations."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        # Set different coverage levels
        manager.pillar_states["Pillar 1"].current_coverage = 80
        manager.pillar_states["Pillar 2"].current_coverage = 20
        
        for pillar_id, state in manager.pillar_states.items():
            manager._generate_recommendation(state)
        
        focus = manager.get_pillar_needing_focus()
        
        # Pillar 2 should need more focus (lower coverage)
        assert focus == "Pillar 2"
    
    def test_save_log(
        self, 
        sample_pillar_definitions, 
        sample_gap_analysis,
        sample_version_history,
        tmp_path
    ):
        """Test saving log to file."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        with open(sample_version_history) as f:
            history = json.load(f)
        
        manager.record_session(gap, history)
        
        output_path = str(tmp_path / "research_log.json")
        log = manager.save_log(output_path)
        
        assert Path(output_path).exists()
        
        with open(output_path) as f:
            saved = json.load(f)
        
        assert saved["summary"]["total_pillars"] == 2
    
    def test_load_existing_log(self, sample_pillar_definitions, tmp_path):
        """Test loading existing log."""
        # Create a log file first
        existing_log = {
            "timestamp": "2025-12-19T10:00:00",
            "summary": {},
            "pillars": {
                "Pillar 1": {
                    "pillar_id": "Pillar 1",
                    "pillar_name": "Pillar 1: Biological",
                    "current_coverage": 55.0,
                    "total_papers": 10,
                    "total_claims": 25,
                    "approved_claims": 20,
                    "saturation_score": 0.4,
                    "research_phase": "consolidation",
                    "coverage_history": [("2025-12-18T10:00:00", 50.0)],
                    "sessions": []
                }
            }
        }
        
        log_path = tmp_path / "existing_log.json"
        with open(log_path, 'w') as f:
            json.dump(existing_log, f)
        
        manager = ResearchLogManager(sample_pillar_definitions, str(log_path))
        
        state = manager.pillar_states["Pillar 1"]
        assert state.current_coverage == 55.0
        assert state.research_phase == ResearchPhase.CONSOLIDATION
    
    def test_get_saturation_report(self, sample_pillar_definitions):
        """Test get_saturation_report method."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        report = manager.get_saturation_report()
        
        assert "Pillar 1" in report
        assert "saturation_score" in report["Pillar 1"]
        assert "saturation_level" in report["Pillar 1"]
        assert "velocity" in report["Pillar 1"]
        assert "phase" in report["Pillar 1"]
    
    def test_velocity_metrics(self, sample_pillar_definitions):
        """Test velocity metrics calculation."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        state = manager.pillar_states["Pillar 1"]
        
        # Add multiple sessions
        for i in range(5):
            session = ResearchSession(
                session_id=f"session-{i}",
                timestamp=datetime.now().isoformat(),
                papers_added=3,
                papers_removed=0,
                claims_extracted=6,
                claims_approved=4,
                coverage_delta=5.0
            )
            state.sessions.append(session)
            state.total_papers += 3
            state.total_claims += 6
        
        manager._update_velocity_metrics(state)
        
        assert state.coverage_velocity == 5.0
        assert state.papers_per_session == 3.0
        assert state.claims_per_paper == 2.0
    
    def test_saturation_levels(self, sample_pillar_definitions):
        """Test saturation level thresholds."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        state = manager.pillar_states["Pillar 1"]
        
        # Simulate high saturation scenario
        for i in range(10):
            # Earlier sessions have high coverage delta
            coverage_delta = 15 if i < 5 else 1
            session = ResearchSession(
                session_id=f"session-{i}",
                timestamp=datetime.now().isoformat(),
                papers_added=2,
                papers_removed=0,
                claims_extracted=5,
                claims_approved=3,
                coverage_delta=coverage_delta
            )
            state.sessions.append(session)
            state.current_coverage += coverage_delta
        
        manager._update_saturation_metrics(state)
        
        # Should show some level of saturation due to velocity decrease
        assert state.saturation_score > 0.3
    
    def test_recommendation_generation(self, sample_pillar_definitions):
        """Test recommendation generation for different states."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        state = manager.pillar_states["Pillar 1"]
        
        # Test low coverage recommendation
        state.current_coverage = 20
        manager._generate_recommendation(state)
        assert "gaps remain" in state.recommended_action.lower() or "intensity" in state.recommended_action.lower()
        
        # Test complete phase recommendation
        state.research_phase = ResearchPhase.COMPLETE
        manager._generate_recommendation(state)
        assert "concluded" in state.recommended_action.lower()
    
    def test_coverage_history_tracking(
        self, 
        sample_pillar_definitions,
        sample_gap_analysis,
        sample_version_history
    ):
        """Test that coverage history is properly tracked."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        with open(sample_version_history) as f:
            history = json.load(f)
        
        # Record multiple sessions
        manager.record_session(gap, history, "session-1")
        manager.record_session(gap, history, "session-2")
        
        state = manager.pillar_states["Pillar 1"]
        assert len(state.coverage_history) == 2


class TestRecordResearchSession:
    """Tests for the convenience function."""
    
    def test_record_session_function(
        self,
        tmp_path
    ):
        """Test the convenience function."""
        # Create test files
        pillar_def = {
            "Pillar 1: Test": {"requirements": {"REQ-1.1": [{"id": "Sub-1", "text": "Test"}]}}
        }
        gap = {"Pillar 1: Test": {"average_completeness": 50}}
        history = {}
        
        pillar_path = tmp_path / "pillar.json"
        gap_path = tmp_path / "gap.json"
        history_path = tmp_path / "history.json"
        output_path = tmp_path / "log.json"
        
        for path, data in [(pillar_path, pillar_def), (gap_path, gap), (history_path, history)]:
            with open(path, 'w') as f:
                json.dump(data, f)
        
        log = record_research_session(
            str(pillar_path),
            str(gap_path),
            str(history_path),
            str(output_path)
        )
        
        assert "summary" in log
        assert Path(output_path).exists()


class TestSaturationAndPhaseEdgeCases:
    """Test edge cases for saturation and phase calculations."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {
            "Pillar 1: Test Pillar": {
                "requirements": {"REQ-1.1": [{"id": "Sub-1", "text": "Test"}]}
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    def test_no_sessions_velocity(self, sample_pillar_definitions):
        """Test velocity with no sessions."""
        manager = ResearchLogManager(sample_pillar_definitions)
        state = manager.pillar_states["Pillar 1"]
        
        manager._update_velocity_metrics(state)
        
        assert state.coverage_velocity == 0
        assert state.papers_per_session == 0
    
    def test_single_session_velocity(self, sample_pillar_definitions):
        """Test velocity with single session."""
        manager = ResearchLogManager(sample_pillar_definitions)
        state = manager.pillar_states["Pillar 1"]
        
        session = ResearchSession(
            session_id="session-1",
            timestamp=datetime.now().isoformat(),
            papers_added=5,
            papers_removed=0,
            claims_extracted=10,
            claims_approved=7,
            coverage_delta=10.0
        )
        state.sessions.append(session)
        
        manager._update_velocity_metrics(state)
        
        assert state.coverage_velocity == 0
    
    def test_few_sessions_saturation(self, sample_pillar_definitions):
        """Test saturation with few sessions."""
        manager = ResearchLogManager(sample_pillar_definitions)
        state = manager.pillar_states["Pillar 1"]
        
        # Only 2 sessions - not enough for saturation calculation
        for i in range(2):
            session = ResearchSession(
                session_id=f"session-{i}",
                timestamp=datetime.now().isoformat(),
                papers_added=5,
                papers_removed=0,
                claims_extracted=10,
                claims_approved=7,
                coverage_delta=10.0
            )
            state.sessions.append(session)
        
        manager._update_saturation_metrics(state)
        
        assert state.saturation_score == 0
        assert state.saturation_level == SaturationLevel.UNSATURATED
    
    def test_high_coverage_validation_phase(self, sample_pillar_definitions):
        """Test phase transition to validation with high coverage."""
        manager = ResearchLogManager(sample_pillar_definitions)
        state = manager.pillar_states["Pillar 1"]
        
        # Set high coverage and saturation
        state.current_coverage = 80
        state.saturation_level = SaturationLevel.SATURATED
        state.total_claims = 100
        state.approved_claims = 50  # 50% approval, less than 70%
        
        manager._update_phase(state)
        
        assert state.research_phase == ResearchPhase.VALIDATION
    
    def test_complete_phase_with_high_approval(self, sample_pillar_definitions):
        """Test phase transition to complete with high approval rate."""
        manager = ResearchLogManager(sample_pillar_definitions)
        state = manager.pillar_states["Pillar 1"]
        
        # Set high coverage, saturation, and approval
        state.current_coverage = 85
        state.saturation_level = SaturationLevel.SATURATED
        state.total_claims = 100
        state.approved_claims = 80  # 80% approval, greater than 70%
        
        manager._update_phase(state)
        
        assert state.research_phase == ResearchPhase.COMPLETE
    
    def test_empty_pillar_states(self, tmp_path):
        """Test with pillar definitions that have no pillars."""
        definitions = {
            "Framework_Overview": {"description": "Not a pillar"},
            "Cross_Cutting_Requirements": {"description": "Also not a pillar"}
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        manager = ResearchLogManager(str(path))
        
        assert len(manager.pillar_states) == 0
        assert manager.get_pillar_needing_focus() is None
    
    def test_all_pillars_complete(self, sample_pillar_definitions):
        """Test get_pillar_needing_focus when all pillars are complete."""
        manager = ResearchLogManager(sample_pillar_definitions)
        
        for state in manager.pillar_states.values():
            state.research_phase = ResearchPhase.COMPLETE
        
        focus = manager.get_pillar_needing_focus()
        
        assert focus is None
