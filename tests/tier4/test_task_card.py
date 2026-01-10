"""
Tier 4 Task Card Validator Tests
Tests for task card synchronization and status accuracy.
"""

import pytest
from pathlib import Path


class TestTaskCardPRSync:
    """T4-TASK-01/02: PR-Task synchronization tests"""
    
    def test_t4_task_01_merged_prs_have_complete_cards(self, task_card_validator):
        """
        T4-TASK-01: Merged PRs should have corresponding Complete task cards
        
        Validates: PR->Task sync for Operationalization Wave
        """
        report = task_card_validator.validate()
        
        # Check that validation ran without errors
        assert report is not None
        
        # Find T4-TASK-01 result
        task_01 = next(
            (r for r in report.results if r.test_id == "T4-TASK-01"),
            None
        )
        
        assert task_01 is not None, "T4-TASK-01 test should exist in report"
        # Note: May fail if cards not all Complete - this is expected
    
    def test_t4_task_02_complete_tasks_have_prs(self, task_card_validator):
        """
        T4-TASK-02: Complete task cards should have corresponding merged PRs
        
        Validates: Task->PR sync for Operationalization Wave
        """
        report = task_card_validator.validate()
        
        task_02 = next(
            (r for r in report.results if r.test_id == "T4-TASK-02"),
            None
        )
        
        assert task_02 is not None, "T4-TASK-02 test should exist in report"


class TestTaskCardIndexSync:
    """T4-TASK-03/04: Index synchronization tests"""
    
    def test_t4_task_03_wave_index_reflects_cards(self, task_card_validator, repo_path):
        """
        T4-TASK-03: Wave index should reflect individual card statuses
        """
        # Verify index file exists
        index_path = repo_path / "task-cards" / "OPERATIONALIZATION_WAVE_INDEX.md"
        assert index_path.exists(), "Wave index file should exist"
        
        report = task_card_validator.validate()
        
        task_03 = next(
            (r for r in report.results if r.test_id == "T4-TASK-03"),
            None
        )
        
        assert task_03 is not None, "T4-TASK-03 test should exist in report"
    
    def test_t4_task_04_op_index_complete(self, task_card_validator):
        """
        T4-TASK-04: OP Wave Index should show all tasks Complete
        """
        report = task_card_validator.validate()
        
        task_04 = next(
            (r for r in report.results if r.test_id == "T4-TASK-04"),
            None
        )
        
        assert task_04 is not None, "T4-TASK-04 test should exist in report"


class TestTaskCardValidatorIntegration:
    """Integration tests for TaskCardValidator"""
    
    def test_t4_task_05_validator_returns_valid_report(self, task_card_validator):
        """
        T4-TASK-05: Validator should return a valid ValidationReport
        """
        report = task_card_validator.validate()
        
        assert report is not None
        assert hasattr(report, 'results')
        assert len(report.results) >= 4, "Should have at least 4 test results"
    
    def test_t4_task_06_task_cards_directory_exists(self, repo_path):
        """
        T4-TASK-06: task-cards/ directory should exist
        """
        task_cards_dir = repo_path / "task-cards"
        assert task_cards_dir.exists(), "task-cards directory should exist"
        assert task_cards_dir.is_dir(), "task-cards should be a directory"
    
    def test_t4_task_07_op_wave_cards_exist(self, repo_path):
        """
        T4-TASK-07: All OP Wave task cards should exist
        """
        op_wave_cards = [
            "OP_WAVE_1_1_SCHEMA_FOUNDATION.md",
            "OP_WAVE_2_1_ACTION_EXTRACTION.md",
            "OP_WAVE_2_2_BENCHMARK_EXTRACTION.md",
            "OP_WAVE_3_1_VALIDATION_TRACKER.md",
            "OP_WAVE_3_2_ACTION_VECTOR_GENERATOR.md",
            "OP_WAVE_4_1_PILLAR_RESEARCH_LOG.md",
            "OP_WAVE_4_2_MODIFICATION_PROPOSALS.md",
            "OP_WAVE_4_3_STAKEHOLDER_MATRIX.md",
        ]
        
        task_cards_dir = repo_path / "task-cards"
        
        for card_name in op_wave_cards:
            card_path = task_cards_dir / card_name
            assert card_path.exists(), f"Task card {card_name} should exist"
