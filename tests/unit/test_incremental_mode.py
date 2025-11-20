"""
Unit tests for incremental review mode in PipelineOrchestrator.

Tests cover:
- Prerequisite checking
- New paper detection
- Incremental vs full mode routing
- Parent job ID tracking
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pipeline_orchestrator import PipelineOrchestrator
from literature_review.utils.state_manager import (
    StateManager, JobType, GapDetail, GapMetrics, 
    IncrementalState, ExecutionMetrics, OrchestratorState
)


class TestIncrementalMode:
    """Test suite for incremental review mode."""
    
    def test_incremental_prerequisites_check_success(self, tmp_path):
        """Test checking for incremental prerequisites - success case."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create mock gap report
        gap_report = output_dir / "gap_analysis_report.json"
        gap_report.write_text(json.dumps({
            "pillars": {
                "Pillar 1": {
                    "requirements": {
                        "REQ-001": {
                            "sub_requirements": {
                                "SUB-001": {
                                    "completeness_percent": 50,
                                    "text": "Test requirement",
                                    "evidence": []
                                }
                            }
                        }
                    }
                }
            }
        }))
        
        # Create mock state (new format)
        state_file = output_dir / "orchestrator_state.json"
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100
        )
        state.analysis_completed = True
        state.completed_at = "2025-01-15T10:00:00"
        state_manager.save_state(state)
        
        config = {
            'output_dir': str(output_dir),
            'incremental': True,
            'force': False
        }
        
        orch = PipelineOrchestrator(config=config)
        
        result = orch._check_incremental_prerequisites()
        assert result == True
        assert orch.parent_job_id == state.job_id
    
    def test_incremental_prerequisites_check_missing_report(self, tmp_path):
        """Test incremental fails if no previous report."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        config = {
            'output_dir': str(output_dir),
            'incremental': True,
            'force': False
        }
        
        orch = PipelineOrchestrator(config=config)
        
        result = orch._check_incremental_prerequisites()
        assert result == False
    
    def test_incremental_prerequisites_check_missing_state(self, tmp_path):
        """Test incremental fails if no previous state."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create gap report but no state
        gap_report = output_dir / "gap_analysis_report.json"
        gap_report.write_text('{"pillars": {}}')
        
        config = {
            'output_dir': str(output_dir),
            'incremental': True,
            'force': False
        }
        
        orch = PipelineOrchestrator(config=config)
        
        result = orch._check_incremental_prerequisites()
        assert result == False
    
    def test_incremental_prerequisites_check_incomplete_analysis(self, tmp_path):
        """Test incremental fails if previous analysis incomplete."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create gap report
        gap_report = output_dir / "gap_analysis_report.json"
        gap_report.write_text('{"pillars": {}}')
        
        # Create incomplete state
        state_file = output_dir / "orchestrator_state.json"
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100
        )
        # Don't mark as completed
        state.analysis_completed = False
        state_manager.save_state(state)
        
        config = {
            'output_dir': str(output_dir),
            'incremental': True,
            'force': False
        }
        
        orch = PipelineOrchestrator(config=config)
        
        result = orch._check_incremental_prerequisites()
        assert result == False
    
    def test_incremental_prerequisites_check_old_state_format(self, tmp_path):
        """Test prerequisite check works with old state format."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create gap report
        gap_report = output_dir / "gap_analysis_report.json"
        gap_report.write_text('{"pillars": {}}')
        
        # Create old format state (dict)
        state_file = output_dir / "orchestrator_state.json"
        old_state = {
            "schema_version": "1.0",
            "job_id": "old_job_123",
            "analysis_completed": True,
            "database_hash": "abc123",
            "database_size": 100
        }
        with open(state_file, 'w') as f:
            json.dump(old_state, f)
        
        config = {
            'output_dir': str(output_dir),
            'incremental': True,
            'force': False
        }
        
        orch = PipelineOrchestrator(config=config)
        
        result = orch._check_incremental_prerequisites()
        assert result == True
        # When migrating v1 -> v2, a new job ID is created that starts with "migrated_"
        assert orch.parent_job_id is not None
        assert orch.parent_job_id.startswith("migrated_")
    
    def test_force_overrides_incremental(self):
        """Test that --force flag disables incremental mode."""
        config = {
            'incremental': True,
            'force': True
        }
        
        orch = PipelineOrchestrator(config=config)
        
        # Force should override incremental
        assert orch.incremental_mode == False
        assert orch.force_full_analysis == True
    
    def test_incremental_mode_initialization(self):
        """Test incremental mode is properly initialized."""
        config = {
            'incremental': True,
            'force': False
        }
        
        orch = PipelineOrchestrator(config=config)
        
        assert orch.incremental_mode == True
        assert orch.force_full_analysis == False
        assert orch.incremental_analyzer is not None
    
    def test_full_mode_initialization(self):
        """Test full mode initialization (no incremental)."""
        config = {
            'incremental': False,
            'force': False
        }
        
        orch = PipelineOrchestrator(config=config)
        
        assert orch.incremental_mode == False
        assert orch.incremental_analyzer is None
    
    def test_parent_job_id_from_config(self):
        """Test parent job ID can be set from config."""
        config = {
            'incremental': True,
            'force': False,
            'parent_job_id': 'custom_parent_123'
        }
        
        orch = PipelineOrchestrator(config=config)
        
        assert orch.parent_job_id == 'custom_parent_123'
    
    @patch('pipeline_orchestrator.PipelineOrchestrator._run_incremental_pipeline')
    @patch('pipeline_orchestrator.PipelineOrchestrator._check_incremental_prerequisites')
    def test_run_routes_to_incremental_mode(self, mock_check_prereqs, mock_run_incremental):
        """Test run() routes to incremental pipeline when mode is enabled."""
        mock_check_prereqs.return_value = True
        
        config = {
            'incremental': True,
            'force': False
        }
        
        with patch.object(PipelineOrchestrator, 'log'):
            orch = PipelineOrchestrator(config=config)
            
            # Mock cost tracker to avoid budget checks
            orch.cost_tracker = Mock()
            orch.cost_tracker.get_budget_status.return_value = {
                'over_budget': False,
                'at_risk': False,
                'spent': 0.0,
                'budget': 50.0,
                'remaining': 50.0,
                'percent_used': 0.0
            }
            orch.cost_tracker.generate_report.return_value = {
                'session_summary': {'total_cost': 0.0, 'total_calls': 0},
                'total_summary': {'total_cost': 0.0, 'total_calls': 0},
                'budget_status': {'remaining': 50.0},
                'recommendations': []
            }
            
            orch.run()
            
            # Should call incremental pipeline
            mock_run_incremental.assert_called_once()
    
    @patch('pipeline_orchestrator.PipelineOrchestrator._run_full_pipeline')
    @patch('pipeline_orchestrator.PipelineOrchestrator._check_incremental_prerequisites')
    def test_run_falls_back_to_full_when_prerequisites_fail(self, mock_check_prereqs, mock_run_full):
        """Test run() falls back to full mode when prerequisites not met."""
        mock_check_prereqs.return_value = False
        
        config = {
            'incremental': True,
            'force': False
        }
        
        with patch.object(PipelineOrchestrator, 'log'):
            orch = PipelineOrchestrator(config=config)
            
            # Mock cost tracker
            orch.cost_tracker = Mock()
            orch.cost_tracker.get_budget_status.return_value = {
                'over_budget': False,
                'at_risk': False,
                'spent': 0.0,
                'budget': 50.0,
                'remaining': 50.0,
                'percent_used': 0.0
            }
            orch.cost_tracker.generate_report.return_value = {
                'session_summary': {'total_cost': 0.0, 'total_calls': 0},
                'total_summary': {'total_cost': 0.0, 'total_calls': 0},
                'budget_status': {'remaining': 50.0},
                'recommendations': []
            }
            
            # Mock incremental analyzer to return no changes
            orch.incremental_analyzer = Mock()
            orch.incremental_analyzer.detect_changes.return_value = {
                'new': [],
                'modified': [],
                'unchanged': ['paper1.json'],
                'removed': []
            }
            
            # Mock to prevent early return
            with patch.object(orch, 'incremental_analyzer', None):
                orch.run()
                
                # Should call full pipeline
                mock_run_full.assert_called_once()


class TestIncrementalPipeline:
    """Test suite for _run_incremental_pipeline method."""
    
    @patch('pipeline_orchestrator.PipelineOrchestrator._run_full_pipeline')
    def test_incremental_pipeline_no_new_papers(self, mock_run_full, tmp_path):
        """Test incremental pipeline exits early if no new papers."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create gap report
        gap_report = output_dir / "gap_analysis_report.json"
        gap_report.write_text('{"pillars": {}}')
        
        # Create state
        state_file = output_dir / "orchestrator_state.json"
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100
        )
        state.analysis_completed = True
        state_manager.save_state(state)
        
        config = {
            'output_dir': str(output_dir),
            'incremental': True,
            'force': False
        }
        
        with patch.object(PipelineOrchestrator, 'log'):
            orch = PipelineOrchestrator(config=config)
            
            # Mock incremental analyzer to return no changes
            orch.incremental_analyzer = Mock()
            orch.incremental_analyzer.detect_changes.return_value = {
                'new': [],
                'modified': [],
                'unchanged': ['paper1.json'],
                'removed': []
            }
            
            orch._run_incremental_pipeline()
            
            # Should not call full pipeline
            mock_run_full.assert_not_called()
    
    @patch('pipeline_orchestrator.PipelineOrchestrator._run_full_pipeline')
    def test_incremental_pipeline_with_new_papers(self, mock_run_full, tmp_path):
        """Test incremental pipeline runs analysis with new papers."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create gap report
        gap_report = output_dir / "gap_analysis_report.json"
        gap_report.write_text(json.dumps({
            "pillars": {
                "Pillar 1": {
                    "requirements": {
                        "REQ-001": {
                            "sub_requirements": {
                                "SUB-001": {
                                    "completeness_percent": 50,
                                    "text": "neuromorphic computing architecture",
                                    "evidence": []
                                }
                            }
                        }
                    }
                }
            }
        }))
        
        # Create state
        state_file = output_dir / "orchestrator_state.json"
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100
        )
        state.analysis_completed = True
        state_manager.save_state(state)
        
        config = {
            'output_dir': str(output_dir),
            'incremental': True,
            'force': False
        }
        
        with patch.object(PipelineOrchestrator, 'log'):
            orch = PipelineOrchestrator(config=config)
            
            # Mock incremental analyzer to return new papers
            orch.incremental_analyzer = Mock()
            orch.incremental_analyzer.detect_changes.return_value = {
                'new': ['paper2.json', 'paper3.json'],
                'modified': ['paper1.json'],
                'unchanged': [],
                'removed': []
            }
            
            orch._run_incremental_pipeline()
            
            # Should call full pipeline for the new papers
            mock_run_full.assert_called_once()
            
            # Should update fingerprints
            orch.incremental_analyzer.update_fingerprints.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
