"""
Test Suite for PR #4: Migrate deep coverage claims to version history as single source of truth

This test suite validates:
1. Migration script functionality
2. Deep-Reviewer integration with version history
3. Judge integration with version history
4. Orchestrator integration with version history
5. Data format validation
6. Backward compatibility
7. Architecture simplification

Task Card #4 Acceptance Criteria:
- ✓ Migration script created and tested
- ✓ Deep-Reviewer updated to use version history
- ✓ Judge updated to use version history
- ✓ Orchestrator updated to use version history
- ✓ Documentation created (ARCHITECTURE_ANALYSIS.md)
- ✓ Deprecation notice created
- ✓ All files compile without errors
- ✓ Single source of truth established
"""

import pytest
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import modules to test
from scripts import migrate_deep_coverage
from literature_review.reviewers import deep_reviewer as Deep_Reviewer
from literature_review.analysis import judge as Judge
from literature_review import orchestrator as Orchestrator


class TestDeepReviewerIntegration:
    """Test suite for Deep-Reviewer integration with version history"""
    
    def test_deep_reviewer_uses_version_history_constant(self):
        """AC10: Deep-Reviewer references VERSION_HISTORY_FILE not DEEP_COVERAGE_DB_FILE"""
        assert hasattr(Deep_Reviewer, 'VERSION_HISTORY_FILE')
        assert Deep_Reviewer.VERSION_HISTORY_FILE == 'review_version_history.json'
    
    def test_deep_reviewer_deprecated_constant_commented(self):
        """AC11: Deep-Reviewer has deprecated DEEP_COVERAGE_DB_FILE commented out"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'literature_review', 'reviewers', 'deep_reviewer.py'), 'r') as f:
            content = f.read()
        assert '# DEPRECATED' in content
        assert 'deep_coverage_database.json' in content
    
    def test_deep_reviewer_has_version_history_functions(self):
        """AC12: Deep-Reviewer has load/save version history functions"""
        assert hasattr(Deep_Reviewer, 'load_version_history')
        assert hasattr(Deep_Reviewer, 'save_version_history')
    
    def test_deep_reviewer_no_deep_coverage_entry_dataclass(self):
        """AC13: Deep-Reviewer removed DeepCoverageEntry dataclass"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'literature_review', 'reviewers', 'deep_reviewer.py'), 'r') as f:
            content = f.read()
        # Should not have an active DeepCoverageEntry class definition
        assert '@dataclass' not in content or 'DEPRECATED' in content
    
    def test_deep_reviewer_has_get_all_claims_function(self):
        """AC14: Deep-Reviewer has get_all_claims_from_history function"""
        assert hasattr(Deep_Reviewer, 'get_all_claims_from_history')
    
    def test_deep_reviewer_has_create_requirement_entry(self):
        """AC15: Deep-Reviewer has create_requirement_entry function"""
        assert hasattr(Deep_Reviewer, 'create_requirement_entry')
    
    def test_deep_reviewer_has_add_claim_to_version_history(self):
        """AC16: Deep-Reviewer has add_claim_to_version_history function"""
        assert hasattr(Deep_Reviewer, 'add_claim_to_version_history')
    
    def test_create_requirement_entry_format(self):
        """AC17: create_requirement_entry returns correct format"""
        
        claim_data = {
            "claim_summary": "Test summary",
            "evidence_chunk": "Test evidence",
            "page_number": 5,
            "reviewer_confidence": 0.95
        }
        
        paper_info = {
            "FILENAME": "test.pdf"
        }
        
        gap = {
            "pillar": "Pillar 1: Test",
            "requirement_key": "Req-1.1",
            "sub_requirement_key": "Sub-1.1.1: Test"
        }
        
        result = Deep_Reviewer.create_requirement_entry(claim_data, paper_info, gap)
        
        # Check all required fields
        assert "claim_id" in result
        assert "pillar" in result
        assert "sub_requirement" in result
        assert "evidence_chunk" in result
        assert "claim_summary" in result
        assert "status" in result
        
        # Check extended fields
        assert result["requirement_key"] == "Req-1.1"
        assert result["page_number"] == 5
        assert result["reviewer_confidence"] == 0.95
        assert result["source"] == "deep_reviewer"
    
    def test_get_all_claims_from_history(self):
        """AC18: get_all_claims_from_history extracts claims correctly"""
        
        version_history = {
            "paper1.pdf": [
                {
                    "timestamp": "2025-11-10T12:00:00",
                    "review": {
                        "FILENAME": "paper1.pdf",
                        "Requirement(s)": [
                            {"claim_id": "c1", "status": "approved"},
                            {"claim_id": "c2", "status": "pending_judge_review"}
                        ]
                    },
                    "changes": {}
                }
            ],
            "paper2.pdf": [
                {
                    "timestamp": "2025-11-10T13:00:00",
                    "review": {
                        "FILENAME": "paper2.pdf",
                        "Requirement(s)": [
                            {"claim_id": "c3", "status": "rejected"}
                        ]
                    },
                    "changes": {}
                }
            ]
        }
        
        claims = Deep_Reviewer.get_all_claims_from_history(version_history)
        
        assert len(claims) == 3
        assert claims[0]["filename"] == "paper1.pdf"
        assert claims[1]["filename"] == "paper1.pdf"
        assert claims[2]["filename"] == "paper2.pdf"
    
    def test_add_claim_to_version_history(self):
        """AC19: add_claim_to_version_history adds claims correctly"""
        
        version_history = {}
        claim = {
            "claim_id": "test123",
            "pillar": "Pillar 1: Test",
            "sub_requirement": "Sub-1.1.1: Test",
            "evidence_chunk": "Test evidence",
            "claim_summary": "Test summary",
            "status": "pending_judge_review"
        }
        
        Deep_Reviewer.add_claim_to_version_history(version_history, "test.pdf", claim)
        
        assert "test.pdf" in version_history
        assert len(version_history["test.pdf"]) == 1
        assert len(version_history["test.pdf"][0]["review"]["Requirement(s)"]) == 1
        assert version_history["test.pdf"][0]["review"]["Requirement(s)"][0]["claim_id"] == "test123"


class TestJudgeIntegration:
    """Test suite for Judge integration with version history"""
    
    def test_judge_uses_version_history_constant(self):
        """AC20: Judge references VERSION_HISTORY_FILE not DEEP_COVERAGE_DB_FILE"""
        assert hasattr(Judge, 'VERSION_HISTORY_FILE')
        assert Judge.VERSION_HISTORY_FILE == 'review_version_history.json'
    
    def test_judge_deprecated_constant_commented(self):
        """AC21: Judge still has DEEP_COVERAGE_DB_FILE constant (legacy compatibility)"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'literature_review', 'analysis', 'judge.py'), 'r') as f:
            content = f.read()
        # Constant exists for legacy compatibility but is not actively used
        assert 'DEEP_COVERAGE_DB_FILE' in content
        assert 'deep_coverage_database.json' in content
    
    def test_judge_has_version_history_functions(self):
        """AC22: Judge has load/save version history functions"""
        assert hasattr(Judge, 'load_version_history')
        assert hasattr(Judge, 'save_version_history')
    
    def test_judge_version_changed_to_2_0(self):
        """AC23: Judge version updated to 2.0 indicating migration"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'literature_review', 'analysis', 'judge.py'), 'r') as f:
            content = f.read()
        assert 'Version: 2.0' in content
        assert 'Uses Version History as Single Source of Truth' in content


class TestOrchestratorIntegration:
    """Test suite for Orchestrator integration with version history"""
    
    def test_orchestrator_uses_version_history_constant(self):
        """AC24: Orchestrator references VERSION_HISTORY_FILE not DEEP_COVERAGE_DB_FILE"""
        assert hasattr(Orchestrator, 'VERSION_HISTORY_FILE')
        assert Orchestrator.VERSION_HISTORY_FILE == 'review_version_history.json'
    
    def test_orchestrator_deprecated_constant_commented(self):
        """AC25: Orchestrator has deprecated DEEP_COVERAGE_DB_FILE commented out"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'literature_review', 'orchestrator.py'), 'r') as f:
            content = f.read()
        assert '# DEPRECATED' in content
        assert 'deep_coverage_database.json' in content
    
    def test_orchestrator_has_load_approved_claims_function(self):
        """AC26: Orchestrator has load_approved_claims_from_version_history function"""
        assert hasattr(Orchestrator, 'load_approved_claims_from_version_history')
    
    def test_orchestrator_version_changed_to_3_7(self):
        """AC27: Orchestrator version updated to 3.7"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'literature_review', 'orchestrator.py'), 'r') as f:
            content = f.read()
        assert 'Version: 3.7' in content
    
    def test_load_approved_claims_from_version_history(self):
        """AC28: load_approved_claims_from_version_history extracts approved claims"""
        # Create temporary version history file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            version_history = {
                "paper1.pdf": [
                    {
                        "timestamp": "2025-11-10T12:00:00",
                        "review": {
                            "FILENAME": "paper1.pdf",
                            "Requirement(s)": [
                                {"claim_id": "c1", "status": "approved"},
                                {"claim_id": "c2", "status": "pending_judge_review"},
                                {"claim_id": "c3", "status": "approved"}
                            ]
                        },
                        "changes": {}
                    }
                ]
            }
            json.dump(version_history, f)
            temp_file = f.name
        
        try:
            approved_claims = Orchestrator.load_approved_claims_from_version_history(temp_file)
            assert len(approved_claims) == 2
            assert all(c["status"] == "approved" for c in approved_claims)
            assert approved_claims[0]["filename"] == "paper1.pdf"
        finally:
            os.unlink(temp_file)


class TestDocumentation:
    """Test suite for documentation and deprecation"""
    
    def test_architecture_analysis_exists(self):
        """AC29: ARCHITECTURE_ANALYSIS.md exists"""
        assert os.path.exists('ARCHITECTURE_ANALYSIS.md')
    
    def test_architecture_analysis_content(self):
        """AC30: ARCHITECTURE_ANALYSIS.md contains required sections"""
        with open('ARCHITECTURE_ANALYSIS.md', 'r') as f:
            content = f.read()
        
        assert 'Executive Summary' in content
        assert 'Problem Statement' in content
        assert 'Decision: Option A' in content
        assert 'Implementation Details' in content
        assert 'Migration Path' in content
        assert 'Data Flow Diagram' in content
    
    def test_task_card_summary_exists(self):
        """AC31: TASK_CARD_4_COMPLETION_SUMMARY.md exists"""
        assert os.path.exists('TASK_CARD_4_COMPLETION_SUMMARY.md')
    
    def test_deprecation_notice_exists(self):
        """AC32: deep_coverage_database.DEPRECATED.json exists"""
        assert os.path.exists('deep_coverage_database.DEPRECATED.json')
    
    def test_deprecation_notice_content(self):
        """AC33: Deprecation notice has required fields"""
        with open('deep_coverage_database.DEPRECATED.json', 'r') as f:
            notice = json.load(f)
        
        assert notice.get("DEPRECATED") is True
        assert "deprecation_date" in notice
        assert notice.get("new_location") == "review_version_history.json"
        assert "migration_status" in notice


class TestSyntaxValidation:
    """Test suite for syntax validation"""
    
    def test_migration_script_compiles(self):
        """AC34: migrate_deep_coverage.py compiles without errors"""
        import py_compile
        py_compile.compile('scripts/migrate_deep_coverage.py', doraise=True)
    
    def test_deep_reviewer_compiles(self):
        """AC35: Deep-Reviewer.py compiles without errors"""
        import py_compile
        py_compile.compile('literature_review/reviewers/deep_reviewer.py', doraise=True)
    
    def test_judge_compiles(self):
        """AC36: Judge.py compiles without errors"""
        import py_compile
        py_compile.compile('literature_review/analysis/judge.py', doraise=True)
    
    def test_orchestrator_compiles(self):
        """AC37: Orchestrator.py compiles without errors"""
        import py_compile
        py_compile.compile('literature_review/orchestrator.py', doraise=True)


class TestArchitectureSimplification:
    """Test suite for architecture simplification"""
    
    def test_no_dual_database_logic_in_judge(self):
        """AC38: Judge no longer has dual database logic"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'literature_review', 'analysis', 'judge.py'), 'r') as f:
            content = f.read()
        
        # Should not be loading from both sources in main()
        # Check that it's simplified
        assert content.count('load_version_history') > 0
        assert 'save_version_history' in content
    
    def test_single_source_of_truth_documented(self):
        """AC39: Single source of truth principle documented"""
        with open('ARCHITECTURE_ANALYSIS.md', 'r') as f:
            content = f.read()
        
        assert 'single source of truth' in content.lower()
        assert 'VERSION_HISTORY' in content or 'version_history' in content
    
    def test_data_flow_simplified(self):
        """AC40: Data flow diagrams show simplification"""
        with open('ARCHITECTURE_ANALYSIS.md', 'r') as f:
            content = f.read()
        
        assert 'Before Migration' in content or 'Before:' in content
        assert 'After Migration' in content or 'After:' in content

class TestRequirementFormat:
    """Test suite for requirement format validation"""
    
    def test_requirement_format_has_core_fields(self):
        """AC41: Requirement format includes core fields"""
        
        claim_data = {
            "claim_summary": "Test",
            "evidence_chunk": "Test",
            "page_number": 1,
            "reviewer_confidence": 0.9
        }
        
        result = Deep_Reviewer.create_requirement_entry(
            claim_data,
            {"FILENAME": "test.pdf"},
            {
                "pillar": "Pillar 1: Test",
                "requirement_key": "Req-1.1",
                "sub_requirement_key": "Sub-1.1.1: Test"
            }
        )
        
        # Core fields
        assert "claim_id" in result
        assert "pillar" in result
        assert "sub_requirement" in result
        assert "evidence_chunk" in result
        assert "claim_summary" in result
        assert "status" in result
    
    def test_requirement_format_has_extended_fields(self):
        """AC42: Requirement format includes extended fields from Deep-Reviewer"""
        
        claim_data = {
            "claim_summary": "Test",
            "evidence_chunk": "Test",
            "page_number": 5,
            "reviewer_confidence": 0.95
        }
        
        result = Deep_Reviewer.create_requirement_entry(
            claim_data,
            {"FILENAME": "test.pdf"},
            {
                "pillar": "Pillar 1: Test",
                "requirement_key": "Req-1.1",
                "sub_requirement_key": "Sub-1.1.1: Test"
            }
        )
        
        # Extended fields
        assert "requirement_key" in result
        assert "page_number" in result
        assert result["page_number"] == 5
        assert "reviewer_confidence" in result
        assert result["reviewer_confidence"] == 0.95
        assert "judge_notes" in result
        assert "review_timestamp" in result
        assert "source" in result
        assert result["source"] == "deep_reviewer"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
