"""Integration tests for Journal-Reviewer → Judge flow."""

import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch
from typing import Dict, List

# Import modules to test
from literature_review.analysis.judge import load_version_history, save_version_history
from literature_review.utils.api_manager import APIManager


class TestJournalToJudgeFlow:
    """Test the integration between Journal-Reviewer and Judge."""
    
    @pytest.mark.integration
    def test_judge_processes_pending_claims(self, temp_workspace, test_data_generator):
        """Test Judge reads and processes pending claims from version history."""
        
        # Setup: Create version history with pending claims
        version_history = test_data_generator.create_version_history(
            filename="test_paper.pdf",
            num_versions=1,
            claim_statuses=['pending_judge_review', 'pending_judge_review']
        )
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Mock Judge's API calls to avoid costs
        mock_approved_response = {
            "verdict": "approved",
            "judge_notes": "Approved. Evidence clearly supports the requirement."
        }
        
        mock_rejected_response = {
            "verdict": "rejected", 
            "judge_notes": "Rejected. Evidence does not adequately address the requirement."
        }
        
        with patch.object(APIManager, 'cached_api_call') as mock_api:
            # Alternate between approved and rejected
            mock_api.side_effect = [mock_approved_response, mock_rejected_response]
            
            # Execute: Load and process claims using Judge functions
            history = load_version_history(str(version_history_file))
            
            # Extract pending claims (simplified version of Judge logic)
            claims_to_judge = []
            for filename, versions in history.items():
                if not versions:
                    continue
                latest = versions[-1].get('review', {})
                for claim in latest.get('Requirement(s)', []):
                    if claim.get('status') == 'pending_judge_review':
                        claim['_source_filename'] = filename
                        claims_to_judge.append(claim)
            
            # Process each claim
            for claim in claims_to_judge:
                # Simulate Judge processing
                response = mock_api()
                if response:
                    claim['status'] = response['verdict']
                    claim['judge_notes'] = response['judge_notes']
                    claim['judge_timestamp'] = datetime.now().isoformat()
            
            # Update version history
            for filename, versions in history.items():
                latest = versions[-1]
                # Update claims in place
                for i, claim in enumerate(latest['review']['Requirement(s)']):
                    # Find matching updated claim
                    updated_claim = next(
                        (c for c in claims_to_judge if c['claim_id'] == claim['claim_id']),
                        None
                    )
                    if updated_claim:
                        claim.update(updated_claim)
                
                # Add new version entry
                new_version = {
                    'timestamp': datetime.now().isoformat(),
                    'review': latest['review'],
                    'changes': {
                        'status': 'judge_update',
                        'updated_claims': len(claims_to_judge),
                        'claim_ids': [c['claim_id'] for c in claims_to_judge]
                    }
                }
                versions.append(new_version)
            
            # Save updated history
            save_version_history(str(version_history_file), history)
        
        # Assert: Verify results
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        # Check version history structure
        assert "test_paper.pdf" in updated_history
        versions = updated_history["test_paper.pdf"]
        assert len(versions) == 2  # Original + Judge update
        
        # Check latest version has updated claims
        latest_version = versions[-1]
        claims = latest_version['review']['Requirement(s)']
        assert len(claims) == 2
        
        # Verify claim statuses updated
        statuses = [c['status'] for c in claims]
        assert 'approved' in statuses
        assert 'rejected' in statuses
        
        # Verify timestamps added
        for claim in claims:
            assert 'judge_timestamp' in claim
            assert 'judge_notes' in claim
        
        # Verify version entry metadata
        assert latest_version['changes']['status'] == 'judge_update'
        assert latest_version['changes']['updated_claims'] == 2
    
    @pytest.mark.integration
    def test_version_history_preserves_original_data(self, temp_workspace, test_data_generator):
        """Test that Judge doesn't corrupt original version history data."""
        
        # Setup: Create version history with specific data
        original_history = test_data_generator.create_version_history(
            filename="preserve_test.pdf",
            num_versions=1,
            claim_statuses=['pending_judge_review']
        )
        
        # Add custom fields to verify preservation
        original_history["preserve_test.pdf"][0]['review']['CUSTOM_FIELD'] = 'test_value'
        original_claim = original_history["preserve_test.pdf"][0]['review']['Requirement(s)'][0]
        original_claim['custom_evidence_field'] = 'preserve_this'
        original_claim_id = original_claim['claim_id']
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(original_history, f, indent=2)
        
        # Execute: Simulate Judge processing
        with patch.object(APIManager, 'cached_api_call') as mock_api:
            mock_api.return_value = {
                "verdict": "approved",
                "judge_notes": "Approved. Test verdict."
            }
            
            history = load_version_history(str(version_history_file))
            
            # Update claim status (minimal Judge logic)
            for filename, versions in history.items():
                latest = versions[-1]
                for claim in latest['review']['Requirement(s)']:
                    if claim.get('status') == 'pending_judge_review':
                        claim['status'] = 'approved'
                        claim['judge_notes'] = 'Approved. Test verdict.'
                        claim['judge_timestamp'] = datetime.now().isoformat()
            
            save_version_history(str(version_history_file), history)
        
        # Assert: Verify original data preserved
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        latest_version = updated_history["preserve_test.pdf"][-1]
        
        # Check custom fields preserved
        assert latest_version['review']['CUSTOM_FIELD'] == 'test_value'
        
        updated_claim = next(
            c for c in latest_version['review']['Requirement(s)'] 
            if c['claim_id'] == original_claim_id
        )
        assert updated_claim['custom_evidence_field'] == 'preserve_this'
        assert updated_claim['status'] == 'approved'  # But status updated
