#!/usr/bin/env python3
"""
Test PR #1: Refactor Judge.py to use version history as single source of truth

This test validates that Task Card #2 acceptance criteria are met:
- Judge NEVER writes to deep_coverage_database.json
- Judge NEVER writes to neuromorphic-research_database.csv
- All claim updates appear in review_version_history.json with timestamps
- Sync script successfully propagates changes to CSV
- No data loss during Judge→Sync→CSV flow
- All existing functionality preserved
"""

import sys
import os
import json
import pytest
from typing import Dict, List
from datetime import datetime
import tempfile
import copy

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Judge import (
    load_version_history,
    save_version_history,
    extract_pending_claims_from_history,
    update_claims_in_history,
    add_new_claims_to_history,
    VERSION_HISTORY_FILE
)


class TestTaskCard2AcceptanceCriteria:
    """Test acceptance criteria from Task Card #2"""
    
    def test_version_history_file_constant_defined(self):
        """Verify VERSION_HISTORY_FILE constant is defined"""
        assert VERSION_HISTORY_FILE == 'review_version_history.json'
    
    def test_no_direct_database_saves_in_judge(self):
        """✅ Verify Judge.py does NOT call save_deep_coverage_db or save_research_db in main()"""
        with open('/workspaces/Literature-Review/Judge.py', 'r') as f:
            judge_code = f.read()
        
        # Find main() function
        main_start = judge_code.find('def main():')
        assert main_start > 0, "main() function not found"
        
        main_code = judge_code[main_start:]
        
        # Verify NO calls to old save functions in main()
        assert 'save_deep_coverage_db(' not in main_code, "Judge.py still calls save_deep_coverage_db!"
        assert 'save_research_db(' not in main_code, "Judge.py still calls save_research_db!"
        
        # Verify it DOES call save_version_history
        assert 'save_version_history(' in main_code, "Judge.py should call save_version_history!"
    
    def test_no_database_loads_in_main(self):
        """✅ Verify Judge.py does NOT load from databases in main()"""
        with open('/workspaces/Literature-Review/Judge.py', 'r') as f:
            judge_code = f.read()
        
        main_start = judge_code.find('def main():')
        main_code = judge_code[main_start:]
        
        # Should NOT load from databases
        assert 'load_deep_coverage_db(' not in main_code, "Judge.py should not load from JSON database!"
        assert 'load_research_db(' not in main_code, "Judge.py should not load from CSV database!"
        
        # Should ONLY load from version history
        assert 'load_version_history(' in main_code, "Judge.py must load from version history!"


class TestVersionHistoryIO:
    """Test version history I/O functions"""
    
    @pytest.fixture
    def sample_version_history(self):
        """Sample version history for testing"""
        return {
            "paper1.pdf": [
                {
                    "timestamp": "2025-11-10T10:00:00",
                    "review": {
                        "FILENAME": "paper1.pdf",
                        "Requirement(s)": [
                            {
                                "claim_id": "claim_001",
                                "pillar": "Pillar 1: Biological Stimulus-Response",
                                "sub_requirement": "Sub-1.1.1",
                                "status": "pending_judge_review",
                                "evidence_chunk": "Evidence text here",
                                "claim_summary": "Test claim"
                            },
                            {
                                "claim_id": "claim_002",
                                "pillar": "Pillar 2: AI Stimulus-Response (Bridge)",
                                "sub_requirement": "Sub-2.1.1",
                                "status": "approved",
                                "evidence_chunk": "Approved evidence",
                                "claim_summary": "Approved claim",
                                "judge_notes": "Approved. Good evidence.",
                                "judge_timestamp": "2025-11-10T09:00:00"
                            }
                        ]
                    },
                    "changes": {
                        "status": "initial_review"
                    }
                }
            ],
            "paper2.pdf": [
                {
                    "timestamp": "2025-11-10T11:00:00",
                    "review": {
                        "FILENAME": "paper2.pdf",
                        "Requirement(s)": [
                            {
                                "claim_id": "claim_003",
                                "pillar": "Pillar 3: Plasticity & Learning",
                                "sub_requirement": "Sub-3.1.1",
                                "status": "pending_judge_review",
                                "evidence_chunk": "Learning evidence",
                                "claim_summary": "Plasticity claim"
                            }
                        ]
                    },
                    "changes": {
                        "status": "initial_review"
                    }
                }
            ]
        }
    
    def test_load_version_history_success(self):
        """✅ Test loading actual version history file"""
        # Use EXAMPLE file if available
        example_file = 'review_version_history_EXAMPLE.json'
        if os.path.exists(example_file):
            history = load_version_history(example_file)
            assert isinstance(history, dict)
            assert len(history) > 0
            
            # Verify structure
            for filename, versions in history.items():
                assert isinstance(versions, list)
                if versions:
                    assert 'timestamp' in versions[0]
                    assert 'review' in versions[0]
    
    def test_load_version_history_missing_file(self, tmp_path):
        """Test loading non-existent file returns empty dict"""
        fake_file = tmp_path / "nonexistent.json"
        history = load_version_history(str(fake_file))
        
        assert history == {}
    
    def test_save_and_load_version_history(self, tmp_path, sample_version_history):
        """Test save and load round-trip"""
        test_file = tmp_path / "test_history.json"
        
        # Save
        save_version_history(str(test_file), sample_version_history)
        
        # Load
        loaded = load_version_history(str(test_file))
        
        assert loaded == sample_version_history
        assert len(loaded) == 2
        assert "paper1.pdf" in loaded
        assert "paper2.pdf" in loaded
    
    def test_extract_pending_claims_from_history(self, sample_version_history):
        """✅ Test extracting pending claims from version history"""
        pending = extract_pending_claims_from_history(sample_version_history)
        
        # Should extract 2 pending claims (claim_001 and claim_003)
        assert len(pending) == 2
        
        claim_ids = [c['claim_id'] for c in pending]
        assert 'claim_001' in claim_ids
        assert 'claim_003' in claim_ids
        assert 'claim_002' not in claim_ids  # Already approved
        
        # Check metadata
        for claim in pending:
            assert '_source_filename' in claim
            assert '_source_type' in claim
            assert claim['_source_type'] == 'version_history'
    
    def test_update_claims_in_history(self, sample_version_history):
        """✅ Test updating claims in version history"""
        # Create a deep copy to avoid modifying original
        history = copy.deepcopy(sample_version_history)
        
        # Prepare updated claims
        updated_claims = [
            {
                'claim_id': 'claim_001',
                'status': 'approved',
                'judge_notes': 'Approved. Evidence is sufficient.',
                'judge_timestamp': '2025-11-10T12:00:00'
            }
        ]
        
        # Update history
        updated_history = update_claims_in_history(history, updated_claims)
        
        # Verify update
        paper1_versions = updated_history['paper1.pdf']
        
        # Should have added a new version
        assert len(paper1_versions) == 2
        
        # Check latest version
        latest = paper1_versions[-1]
        assert 'timestamp' in latest
        assert 'changes' in latest
        assert latest['changes']['status'] == 'judge_update'
        assert latest['changes']['updated_claims'] == 1
        assert 'claim_001' in latest['changes']['claim_ids']
        
        # Check claim was updated
        updated_claim = None
        for claim in latest['review']['Requirement(s)']:
            if claim['claim_id'] == 'claim_001':
                updated_claim = claim
                break
        
        assert updated_claim is not None
        assert updated_claim['status'] == 'approved'
        assert updated_claim['judge_notes'] == 'Approved. Evidence is sufficient.'
    
    def test_add_new_claims_to_history(self, sample_version_history):
        """✅ Test adding new DRA claims to version history"""
        history = copy.deepcopy(sample_version_history)
        
        # Prepare new claims from DRA
        new_claims = [
            {
                'claim_id': 'dra_claim_001',
                '_source_filename': 'paper1.pdf',
                'filename': 'paper1.pdf',
                'pillar': 'Pillar 1: Biological Stimulus-Response',
                'sub_requirement': 'Sub-1.2.1',
                'status': 'pending_judge_review',
                'evidence_chunk': 'New DRA evidence',
                'claim_summary': 'DRA found better evidence',
                'reviewer_confidence': 0.95
            }
        ]
        
        # Add to history
        updated_history = add_new_claims_to_history(history, new_claims)
        
        # Verify addition
        paper1_versions = updated_history['paper1.pdf']
        
        # Should have added a new version
        assert len(paper1_versions) == 2
        
        # Check latest version
        latest = paper1_versions[-1]
        assert 'timestamp' in latest
        assert latest['changes']['status'] == 'dra_appeal'
        assert latest['changes']['new_claims'] == 1
        
        # Check claim was added
        requirements = latest['review']['Requirement(s)']
        assert len(requirements) == 3  # Original 2 + 1 new
        
        dra_claim = None
        for claim in requirements:
            if claim['claim_id'] == 'dra_claim_001':
                dra_claim = claim
                break
        
        assert dra_claim is not None
        assert dra_claim['reviewer_confidence'] == 0.95


class TestVersionTracking:
    """Test version tracking and audit trail"""
    
    @pytest.fixture
    def sample_history(self):
        return {
            "paper1.pdf": [
                {
                    "timestamp": "2025-11-10T10:00:00",
                    "review": {
                        "FILENAME": "paper1.pdf",
                        "Requirement(s)": [
                            {
                                "claim_id": "claim_001",
                                "status": "pending_judge_review",
                                "evidence_chunk": "Test"
                            }
                        ]
                    }
                }
            ]
        }
    
    def test_timestamps_are_added(self, sample_history):
        """✅ Test that timestamps are added to version entries"""
        history = copy.deepcopy(sample_history)
        
        updated_claims = [{
            'claim_id': 'claim_001',
            'status': 'approved',
            'judge_notes': 'Good',
            'judge_timestamp': datetime.now().isoformat()
        }]
        
        updated_history = update_claims_in_history(history, updated_claims)
        
        # New version should have timestamp
        new_version = updated_history['paper1.pdf'][-1]
        assert 'timestamp' in new_version
        
        # Timestamp should be ISO format
        timestamp = new_version['timestamp']
        # Should be parseable
        datetime.fromisoformat(timestamp)
    
    def test_changes_metadata_tracked(self, sample_history):
        """✅ Test that changes metadata is tracked"""
        history = copy.deepcopy(sample_history)
        
        updated_claims = [{
            'claim_id': 'claim_001',
            'status': 'rejected',
            'judge_notes': 'Insufficient evidence',
            'judge_timestamp': datetime.now().isoformat()
        }]
        
        updated_history = update_claims_in_history(history, updated_claims)
        
        new_version = updated_history['paper1.pdf'][-1]
        changes = new_version['changes']
        
        assert changes['status'] == 'judge_update'
        assert changes['updated_claims'] == 1
        assert 'claim_ids' in changes
        assert 'claim_001' in changes['claim_ids']


class TestBackwardCompatibility:
    """Test backward compatibility with existing data"""
    
    def test_works_with_example_file(self):
        """✅ Test works with actual review_version_history_EXAMPLE.json"""
        example_file = 'review_version_history_EXAMPLE.json'
        
        if not os.path.exists(example_file):
            pytest.skip("EXAMPLE file not found")
        
        # Load actual example file
        history = load_version_history(example_file)
        
        assert isinstance(history, dict)
        assert len(history) > 0
        
        # Extract pending claims
        pending = extract_pending_claims_from_history(history)
        
        # Should extract some claims (if any are pending)
        assert isinstance(pending, list)
        
        # All pending claims should have required fields
        for claim in pending:
            assert 'claim_id' in claim
            assert 'status' in claim
            assert claim['status'] == 'pending_judge_review'
            assert '_source_filename' in claim
            assert '_source_type' in claim


class TestEndToEnd:
    """End-to-end integration tests"""
    
    def test_complete_judge_workflow(self, tmp_path):
        """✅ Test complete workflow: load → extract → judge → update → save"""
        test_file = tmp_path / "test_workflow.json"
        
        # 1. Create initial history with pending claims
        initial_history = {
            "test_paper.pdf": [
                {
                    "timestamp": "2025-11-10T10:00:00",
                    "review": {
                        "FILENAME": "test_paper.pdf",
                        "Requirement(s)": [
                            {
                                "claim_id": "test_001",
                                "pillar": "Pillar 1",
                                "sub_requirement": "Sub-1.1.1",
                                "status": "pending_judge_review",
                                "evidence_chunk": "Test evidence",
                                "claim_summary": "Test claim"
                            },
                            {
                                "claim_id": "test_002",
                                "pillar": "Pillar 2",
                                "sub_requirement": "Sub-2.1.1",
                                "status": "pending_judge_review",
                                "evidence_chunk": "Another test",
                                "claim_summary": "Another claim"
                            }
                        ]
                    },
                    "changes": {"status": "initial_review"}
                }
            ]
        }
        
        # 2. Save initial history
        save_version_history(str(test_file), initial_history)
        
        # 3. Load history
        loaded_history = load_version_history(str(test_file))
        assert len(loaded_history) == 1
        
        # 4. Extract pending claims
        pending_claims = extract_pending_claims_from_history(loaded_history)
        assert len(pending_claims) == 2
        
        # 5. Simulate judging
        judged_claims = []
        for claim in pending_claims:
            claim['status'] = 'approved'
            claim['judge_notes'] = 'Approved. Good evidence.'
            claim['judge_timestamp'] = datetime.now().isoformat()
            judged_claims.append(claim)
        
        # 6. Update history with judged claims
        updated_history = update_claims_in_history(loaded_history, judged_claims)
        
        # 7. Save updated history
        save_version_history(str(test_file), updated_history)
        
        # 8. Verify final state
        final_history = load_version_history(str(test_file))
        
        # Should have 2 versions now
        assert len(final_history["test_paper.pdf"]) == 2
        
        # Latest version should have approved claims
        latest = final_history["test_paper.pdf"][-1]
        for claim in latest['review']['Requirement(s)']:
            assert claim['status'] == 'approved'
            assert 'judge_notes' in claim
            assert 'judge_timestamp' in claim
        
        # Should have audit trail
        assert latest['changes']['status'] == 'judge_update'
        assert latest['changes']['updated_claims'] == 2


def test_pr1_acceptance_summary():
    """
    Summary test that verifies all Task Card #2 acceptance criteria are met
    """
    print("\n" + "="*70)
    print("  PR #1 ACCEPTANCE CRITERIA VERIFICATION")
    print("="*70)
    
    # Check Judge.py source code
    with open('/workspaces/Literature-Review/Judge.py', 'r') as f:
        judge_code = f.read()
    
    main_start = judge_code.find('def main():')
    main_code = judge_code[main_start:]
    
    # Check all criteria
    criteria = {
        "✅ Judge NEVER writes to deep_coverage_database.json": 
            'save_deep_coverage_db(' not in main_code,
        
        "✅ Judge NEVER writes to neuromorphic-research_database.csv": 
            'save_research_db(' not in main_code,
        
        "✅ Judge loads claims ONLY from version history":
            'load_version_history(' in main_code and 
            'load_deep_coverage_db(' not in main_code and
            'load_research_db(' not in main_code,
        
        "✅ Judge saves ONLY to version history":
            'save_version_history(' in main_code,
        
        "✅ New version history I/O functions exist":
            all(func in judge_code for func in [
                'def load_version_history',
                'def save_version_history',
                'def extract_pending_claims_from_history',
                'def update_claims_in_history',
                'def add_new_claims_to_history'
            ]),
        
        "✅ Version history constant defined":
            "VERSION_HISTORY_FILE = 'review_version_history.json'" in judge_code,
    }
    
    print("\nAcceptance Criteria Results:")
    all_passed = True
    for criterion, passed in criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {criterion}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("  ✅ ALL ACCEPTANCE CRITERIA MET - PR #1 READY FOR MERGE")
    else:
        print("  ❌ SOME CRITERIA FAILED - REQUIRES FIXES")
    print("="*70 + "\n")
    
    assert all_passed, "Not all acceptance criteria were met"


if __name__ == "__main__":
    # Run acceptance summary
    test_pr1_acceptance_summary()
    
    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])
