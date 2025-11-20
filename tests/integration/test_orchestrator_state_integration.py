"""
Integration tests for Orchestrator State Manager.

Tests the full workflow of state management within the orchestrator context.
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


class TestOrchestratorStateIntegration:
    """Integration tests for orchestrator state management."""
    
    def test_full_workflow_state_persistence(self):
        """Test complete workflow: create → update → load."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "orchestrator_state.json"
            manager = StateManager(str(state_file))
            
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
            
            # Create initial state
            state = manager.create_new_state(
                database_path="test.csv",
                database_hash="abc123",
                database_size=100,
                job_type=JobType.FULL
            )
            
            # Update with analysis results
            state.analysis_completed = True
            state.analysis_timestamp = datetime.now().isoformat()
            state.total_pillars = 6
            state.overall_coverage = 72.5
            state.coverage_by_pillar = {"pillar_1": 80.0}
            state.papers_analyzed = 100
            
            # Update gap metrics
            state = manager.update_gap_metrics(state, gaps, gap_threshold=0.7)
            
            # Update execution metrics
            state.execution_metrics.duration_seconds = 1800.0
            state.execution_metrics.api_calls = 450
            state.execution_metrics.api_cost_usd = 2.35
            state.execution_metrics.cache_hit_rate = 0.67
            state.execution_metrics.error_count = 0
            
            # Mark as completed
            state.completed_at = datetime.now().isoformat()
            
            # Save state
            assert manager.save_state(state)
            
            # Load and verify
            loaded_state = manager.load_state()
            
            assert loaded_state is not None
            assert loaded_state.gap_metrics.total_gaps == 1
            assert loaded_state.overall_coverage == 72.5
            assert loaded_state.analysis_completed == True
            assert loaded_state.total_pillars == 6
            assert loaded_state.papers_analyzed == 100
            assert loaded_state.execution_metrics.duration_seconds == 1800.0
            assert loaded_state.execution_metrics.api_calls == 450
            assert loaded_state.completed_at is not None
    
    def test_incremental_job_chain(self):
        """Test chaining incremental jobs."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "orchestrator_state.json"
            manager = StateManager(str(state_file))
            
            # Create parent job
            parent_state = manager.create_new_state(
                database_path="test.csv",
                database_hash="hash1",
                database_size=100,
                job_type=JobType.FULL
            )
            parent_state.analysis_completed = True
            parent_state.papers_analyzed = 100
            manager.save_state(parent_state)
            parent_job_id = parent_state.job_id
            
            # Create first incremental job
            incr1_state = manager.create_new_state(
                database_path="test.csv",
                database_hash="hash2",
                database_size=110,
                job_type=JobType.INCREMENTAL,
                parent_job_id=parent_job_id
            )
            incr1_state.incremental_state.papers_added_since_parent = 10
            incr1_state.incremental_state.gaps_closed_since_parent = 2
            incr1_state.analysis_completed = True
            manager.save_state(incr1_state)
            incr1_job_id = incr1_state.job_id
            
            # Create second incremental job
            incr2_state = manager.create_new_state(
                database_path="test.csv",
                database_hash="hash3",
                database_size=120,
                job_type=JobType.INCREMENTAL,
                parent_job_id=incr1_job_id
            )
            incr2_state.incremental_state.papers_added_since_parent = 10
            incr2_state.incremental_state.gaps_closed_since_parent = 1
            incr2_state.incremental_state.new_gaps_identified = 3
            manager.save_state(incr2_state)
            
            # Verify chain
            loaded_state = manager.load_state()
            assert loaded_state.parent_job_id == incr1_job_id
            assert loaded_state.incremental_state.is_continuation == True
            assert loaded_state.incremental_state.papers_added_since_parent == 10
            assert loaded_state.incremental_state.new_gaps_identified == 3
    
    def test_state_persistence_across_restarts(self):
        """Test that state persists across multiple manager instances."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "orchestrator_state.json"
            
            # Create and save with first manager
            manager1 = StateManager(str(state_file))
            state1 = manager1.create_new_state(
                database_path="test.csv",
                database_hash="abc123",
                database_size=100
            )
            state1.overall_coverage = 75.5
            manager1.save_state(state1)
            job_id = state1.job_id
            
            # Load with new manager instance
            manager2 = StateManager(str(state_file))
            state2 = manager2.load_state()
            
            assert state2 is not None
            assert state2.job_id == job_id
            assert state2.overall_coverage == 75.5
            
            # Update and save with second manager
            state2.overall_coverage = 80.0
            manager2.save_state(state2)
            
            # Load with third manager instance
            manager3 = StateManager(str(state_file))
            state3 = manager3.load_state()
            
            assert state3.overall_coverage == 80.0
    
    def test_gap_metrics_evolution(self):
        """Test tracking gap metrics evolution over iterations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "orchestrator_state.json"
            manager = StateManager(str(state_file))
            
            # Initial state with 5 gaps
            state = manager.create_new_state(
                database_path="test.csv",
                database_hash="hash1",
                database_size=100
            )
            
            gaps = [
                GapDetail(
                    pillar_id="pillar_1",
                    requirement_id="req_1_1",
                    sub_requirement_id=f"sub_1_1_{i}",
                    current_coverage=0.4,
                    target_coverage=0.7,
                    gap_size=0.3,
                    keywords=["keyword"],
                    evidence_count=i
                )
                for i in range(1, 6)
            ]
            
            state = manager.update_gap_metrics(state, gaps)
            assert state.gap_metrics.total_gaps == 5
            manager.save_state(state)
            
            # Reload and verify
            loaded_state = manager.load_state()
            assert loaded_state.gap_metrics.total_gaps == 5
            assert len(loaded_state.gap_metrics.gap_details) == 5
            
            # Simulate gap closure - remove 2 gaps
            remaining_gaps = gaps[:3]
            loaded_state = manager.update_gap_metrics(loaded_state, remaining_gaps)
            assert loaded_state.gap_metrics.total_gaps == 3
            manager.save_state(loaded_state)
            
            # Verify reduction persists
            final_state = manager.load_state()
            assert final_state.gap_metrics.total_gaps == 3
            assert len(final_state.gap_metrics.gap_details) == 3
    
    def test_migration_preserves_data(self):
        """Test that v1→v2 migration preserves important data."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "orchestrator_state.json"
            
            # Create a v1 state file with specific values
            v1_state = {
                "timestamp": "2025-01-15T10:30:00",
                "database_hash": "migration_test_hash",
                "database_size": 150,
                "analysis_completed": True,
                "analysis_timestamp": "2025-01-15T11:00:00",
                "total_papers": 150,
                "total_pillars": 6,
                "overall_coverage": 72.5
            }
            
            with open(state_file, 'w') as f:
                json.dump(v1_state, f)
            
            # Load with StateManager (triggers migration)
            manager = StateManager(str(state_file))
            migrated_state = manager.load_state()
            
            # Verify critical data is preserved
            assert migrated_state.database_hash == "migration_test_hash"
            assert migrated_state.database_size == 150
            assert migrated_state.total_papers == 150
            assert migrated_state.total_pillars == 6
            assert migrated_state.overall_coverage == 72.5
            assert migrated_state.analysis_completed == True
            
            # Verify new fields have sensible defaults
            assert migrated_state.schema_version == "2.0"
            assert migrated_state.job_type == JobType.FULL
            assert migrated_state.papers_analyzed == 150
            assert migrated_state.papers_skipped == 0
            assert migrated_state.gap_metrics.total_gaps == 0
            assert migrated_state.incremental_state.is_continuation == False
    
    def test_concurrent_read_operations(self):
        """Test that multiple reads don't corrupt state."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "orchestrator_state.json"
            
            # Create initial state
            manager = StateManager(str(state_file))
            state = manager.create_new_state(
                database_path="test.csv",
                database_hash="abc123",
                database_size=100
            )
            manager.save_state(state)
            
            # Simulate multiple concurrent reads
            managers = [StateManager(str(state_file)) for _ in range(5)]
            states = [m.load_state() for m in managers]
            
            # All should load the same data
            for s in states:
                assert s is not None
                assert s.database_hash == "abc123"
                assert s.database_size == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
