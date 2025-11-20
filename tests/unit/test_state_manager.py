"""
Unit tests for StateManager class.

Tests cover:
- Creating new state
- State persistence (save/load)
- Gap metrics update
- Schema migration (v1 → v2)
- Incremental state tracking
- Atomic file operations
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.state_manager import (
    StateManager, JobType, GapDetail, GapMetrics, 
    IncrementalState, ExecutionMetrics, OrchestratorState
)


class TestStateManager:
    """Test suite for StateManager class."""
    
    def test_create_new_state(self):
        """Test creating new state."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
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
            assert state.database_hash == "abc123"
            assert state.database_path == "test.csv"
            assert state.total_papers == 100
            assert state.papers_analyzed == 0
            assert state.papers_skipped == 0
            assert state.gap_metrics.total_gaps == 0
            assert state.incremental_state.is_continuation == False
    
    def test_create_incremental_state(self):
        """Test creating incremental state with parent."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            manager = StateManager(str(state_file))
            
            parent_id = "review_20251120_120000"
            state = manager.create_new_state(
                database_path="test.csv",
                database_hash="abc123",
                database_size=100,
                job_type=JobType.INCREMENTAL,
                parent_job_id=parent_id
            )
            
            assert state.job_type == JobType.INCREMENTAL
            assert state.parent_job_id == parent_id
            assert state.incremental_state.is_continuation == True
            assert state.incremental_state.parent_job_id == parent_id
            assert state.incremental_state.gap_extraction_mode == "targeted"
    
    def test_save_and_load_state(self):
        """Test state persistence."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            manager = StateManager(str(state_file))
            
            # Create and save
            state = manager.create_new_state(
                database_path="test.csv",
                database_hash="abc123",
                database_size=100
            )
            assert manager.save_state(state)
            
            # Verify file exists
            assert state_file.exists()
            
            # Load
            loaded_state = manager.load_state()
            assert loaded_state is not None
            assert loaded_state.database_hash == "abc123"
            assert loaded_state.database_size == 100
            assert loaded_state.job_type == JobType.FULL
    
    def test_gap_metrics_update(self):
        """Test updating gap metrics."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
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
            assert "pillar_1" in state.gap_metrics.gaps_by_pillar
            assert state.gap_metrics.gaps_by_pillar["pillar_1"]["total_gaps"] == 2
    
    def test_schema_migration_v1_to_v2(self):
        """Test migrating old state format."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            
            # Create v1 state file (simple format)
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
            assert state.analysis_completed == True
            assert state.overall_coverage == 65.0
            assert state.job_type == JobType.FULL
            assert state.incremental_state.is_continuation == False
    
    def test_schema_migration_v1_nested_format(self):
        """Test migrating old nested state format (current orchestrator.py format)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            
            # Create v1 nested state file (current orchestrator format)
            v1_nested_state = {
                "last_run_timestamp": "2025-01-15T10:30:00",
                "last_completed_stage": "final",
                "last_run_state": {
                    "file_states": {
                        "neuromorphic-research_database.csv": 1234567890.123,
                        "review_version_history.json": 1234567890.456
                    }
                },
                "previous_results": {
                    "Pillar 1": {"completeness": 75.0},
                    "Pillar 2": {"completeness": 65.5},
                    "Pillar 3": {"completeness": 80.2}
                },
                "score_history": {
                    "iteration_timestamps": [],
                    "sub_req_scores": {}
                }
            }
            
            with open(state_file, 'w') as f:
                json.dump(v1_nested_state, f)
            
            # Load and migrate
            manager = StateManager(str(state_file))
            state = manager.load_state()
            
            assert state is not None
            assert state.schema_version == "2.0"
            assert state.analysis_completed == True  # last_completed_stage == "final"
            assert state.total_pillars == 3
            # Average of 75.0, 65.5, 80.2 = 73.57
            assert abs(state.overall_coverage - 73.57) < 0.1
            assert len(state.coverage_by_pillar) == 3
            assert state.coverage_by_pillar["Pillar 1"] == 75.0
            assert state.coverage_by_pillar["Pillar 2"] == 65.5
            assert state.coverage_by_pillar["Pillar 3"] == 80.2
    
    def test_incremental_state_tracking(self):
        """Test incremental job lineage."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
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
    
    def test_atomic_save(self):
        """Test atomic file writing (temp + rename)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
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
    
    def test_load_nonexistent_file(self):
        """Test loading state when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "nonexistent.json"
            manager = StateManager(str(state_file))
            
            state = manager.load_state()
            assert state is None
    
    def test_execution_metrics(self):
        """Test execution metrics tracking."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            manager = StateManager(str(state_file))
            
            state = manager.create_new_state(
                database_path="test.csv",
                database_hash="abc123",
                database_size=100
            )
            
            # Update execution metrics
            state.execution_metrics.duration_seconds = 120.5
            state.execution_metrics.api_calls = 50
            state.execution_metrics.api_cost_usd = 1.25
            state.execution_metrics.cache_hit_rate = 0.65
            state.execution_metrics.error_count = 2
            
            # Save and reload
            manager.save_state(state)
            loaded_state = manager.load_state()
            
            assert loaded_state.execution_metrics.duration_seconds == 120.5
            assert loaded_state.execution_metrics.api_calls == 50
            assert loaded_state.execution_metrics.api_cost_usd == 1.25
            assert loaded_state.execution_metrics.cache_hit_rate == 0.65
            assert loaded_state.execution_metrics.error_count == 2
    
    def test_coverage_by_pillar(self):
        """Test coverage by pillar tracking."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            manager = StateManager(str(state_file))
            
            state = manager.create_new_state(
                database_path="test.csv",
                database_hash="abc123",
                database_size=100
            )
            
            # Set coverage data
            state.coverage_by_pillar = {
                "pillar_1": 80.5,
                "pillar_2": 65.0,
                "pillar_3": 92.3
            }
            state.overall_coverage = 79.3
            state.total_pillars = 3
            
            # Save and reload
            manager.save_state(state)
            loaded_state = manager.load_state()
            
            assert len(loaded_state.coverage_by_pillar) == 3
            assert loaded_state.coverage_by_pillar["pillar_1"] == 80.5
            assert loaded_state.coverage_by_pillar["pillar_2"] == 65.0
            assert loaded_state.coverage_by_pillar["pillar_3"] == 92.3
            assert loaded_state.overall_coverage == 79.3
    
    def test_job_id_generation(self):
        """Test job ID generation format."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            manager = StateManager(str(state_file))
            
            state = manager.create_new_state(
                database_path="test.csv",
                database_hash="abc123",
                database_size=100
            )
            
            # Job ID should start with "review_"
            assert state.job_id.startswith("review_")
            # Should be followed by timestamp in format YYYYMMDD_HHMMSS
            assert len(state.job_id) == len("review_20251120_123456")
    
    def test_multiple_gaps_same_pillar(self):
        """Test handling multiple gaps in the same pillar."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            manager = StateManager(str(state_file))
            
            state = manager.create_new_state(
                database_path="test.csv",
                database_hash="abc123",
                database_size=100
            )
            
            # Add gaps from multiple pillars
            gaps = [
                GapDetail(
                    pillar_id="pillar_1",
                    requirement_id="req_1_1",
                    sub_requirement_id="sub_1_1_1",
                    current_coverage=0.45,
                    target_coverage=0.7,
                    gap_size=0.25,
                    keywords=["keyword1"],
                    evidence_count=3
                ),
                GapDetail(
                    pillar_id="pillar_1",
                    requirement_id="req_1_1",
                    sub_requirement_id="sub_1_1_2",
                    current_coverage=0.50,
                    target_coverage=0.7,
                    gap_size=0.20,
                    keywords=["keyword2"],
                    evidence_count=5
                ),
                GapDetail(
                    pillar_id="pillar_2",
                    requirement_id="req_2_1",
                    sub_requirement_id="sub_2_1_1",
                    current_coverage=0.30,
                    target_coverage=0.7,
                    gap_size=0.40,
                    keywords=["keyword3"],
                    evidence_count=2
                )
            ]
            
            state = manager.update_gap_metrics(state, gaps)
            
            assert state.gap_metrics.total_gaps == 3
            assert state.gap_metrics.gaps_by_pillar["pillar_1"]["total_gaps"] == 2
            assert state.gap_metrics.gaps_by_pillar["pillar_2"]["total_gaps"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
