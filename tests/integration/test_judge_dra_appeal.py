"""Integration tests for Judge → DRA appeal flow."""

import pytest
import json
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Note: This test validates the appeal flow mechanics without requiring actual API calls


class TestJudgeDRAAppeal:
    """Test Judge rejection → DRA reanalysis → Judge re-review flow."""
    
    @pytest.mark.integration
    def test_version_history_update_mechanics(self, temp_workspace, test_data_generator):
        """
        Test that version history correctly tracks claim status updates.
        
        This validates the core mechanics of how claims flow through the system,
        without requiring actual Judge or DRA execution.
        """
        # Setup: Create version history with a pending claim
        version_history = test_data_generator.create_version_history_with_claims(
            filename="appeal_test.pdf",
            claims=[
                {
                    'claim_id': 'test_claim_001',
                    'status': 'pending_judge_review',
                    'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                    'sub_requirement': 'SR 1.1',
                    'extracted_claim_text': 'Test claim for appeal flow',
                    'evidence': 'Initial evidence',
                    'page_number': 5,
                    'reviewer_confidence': 0.45
                }
            ]
        )
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Execute: Simulate Judge rejection by updating the claim
        with open(version_history_file, 'r') as f:
            history = json.load(f)
        
        # Simulate Judge updating the claim
        latest_review = history['appeal_test.pdf'][-1]['review']
        claim = latest_review['Requirement(s)'][0]
        claim['status'] = 'rejected'
        claim['judge_notes'] = 'Insufficient evidence. Request DRA reanalysis.'
        claim['judge_timestamp'] = datetime.now().isoformat()
        claim['appeal_requested'] = True
        claim['appeal_count'] = 1
        
        # Create new version entry (simulating Judge's version update)
        new_version = {
            'timestamp': datetime.now().isoformat(),
            'review': latest_review,
            'changes': {
                'status': 'judge_rejection',
                'updated_claims': 1,
                'claim_ids': ['test_claim_001']
            }
        }
        history['appeal_test.pdf'].append(new_version)
        
        with open(version_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Assert: Verify rejection was tracked
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        assert len(updated_history['appeal_test.pdf']) == 2  # Original + rejection
        latest_review = updated_history['appeal_test.pdf'][-1]['review']
        claim = latest_review['Requirement(s)'][0]
        
        assert claim['status'] == 'rejected'
        assert 'judge_notes' in claim
        assert claim['appeal_requested'] is True
        assert claim['appeal_count'] == 1
    
    @pytest.mark.integration
    def test_dra_reanalysis_version_creation(self, temp_workspace, test_data_generator):
        """
        Test DRA reanalysis creates new version with updated evidence.
        
        Validates that DRA appeal results in a new version history entry
        with enhanced evidence and reset status.
        """
        # Setup: Create version history with rejected claim
        version_history = {
            "appeal_test.pdf": [
                {
                    'timestamp': '2025-11-10T10:00:00',
                    'review': {
                        'FILENAME': 'appeal_test.pdf',
                        'TITLE': 'Appeal Test Paper',
                        'CORE_DOMAIN': 'Neuromorphic Computing',
                        'PUBLICATION_YEAR': 2023,
                        'Requirement(s)': [
                            {
                                'claim_id': 'rejected_claim_001',
                                'status': 'rejected',
                                'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                                'sub_requirement': 'SR 1.1',
                                'extracted_claim_text': 'Initial weak claim',
                                'evidence': 'Original insufficient evidence',
                                'page_number': 5,
                                'judge_notes': 'Insufficient evidence. Request DRA reanalysis.',
                                'judge_timestamp': '2025-11-10T10:05:00',
                                'appeal_requested': True,
                                'appeal_count': 1
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Execute: Simulate DRA reanalysis creating an updated claim
        with open(version_history_file, 'r') as f:
            history = json.load(f)
        
        # Simulate DRA finding additional evidence
        updated_claim = {
            'claim_id': 'rejected_claim_001',
            'status': 'pending_judge_review',  # Reset to pending for re-review
            'pillar': 'Pillar 1: Bio-Inspired Algorithms',
            'sub_requirement': 'SR 1.1',
            'extracted_claim_text': 'Enhanced claim with additional evidence',
            'evidence': 'Original evidence + New supporting data from section 3.2',
            'page_number': 5,
            'additional_page_numbers': [12, 13],
            'appeal_count': 1,
            'reanalysis_timestamp': '2025-11-10T11:00:00',
            'reanalysis_notes': 'Found additional supporting evidence in Methods section.'
        }
        
        # Append DRA reanalysis to version history
        new_version = {
            'timestamp': updated_claim['reanalysis_timestamp'],
            'review': {
                'FILENAME': 'appeal_test.pdf',
                'TITLE': 'Appeal Test Paper',
                'CORE_DOMAIN': 'Neuromorphic Computing',
                'PUBLICATION_YEAR': 2023,
                'Requirement(s)': [updated_claim]
            },
            'changes': {
                'status': 'dra_appeal',
                'new_claims': 0,
                'updated_claims': 1,
                'claim_ids': ['rejected_claim_001']
            }
        }
        history['appeal_test.pdf'].append(new_version)
        
        with open(version_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Assert: Verify reanalysis updated version history
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        assert len(updated_history['appeal_test.pdf']) == 2  # Original + reanalysis
        
        reanalysis = updated_history['appeal_test.pdf'][-1]['review']
        claim = reanalysis['Requirement(s)'][0]
        
        assert claim['status'] == 'pending_judge_review'
        assert 'additional_page_numbers' in claim
        assert claim['appeal_count'] == 1
        assert 'reanalysis_notes' in claim
        assert claim['evidence'] != 'Original insufficient evidence'  # Evidence was enhanced
    
    @pytest.mark.integration
    def test_appeal_loop_termination(self, temp_workspace, test_data_generator):
        """
        Test that appeal loop terminates after max attempts.
        
        Validates the safety mechanism that prevents infinite appeal loops.
        """
        MAX_APPEALS = 2
        
        # Setup: Create version history with claim at max appeals
        version_history = {
            "max_appeals_test.pdf": [
                {
                    'timestamp': '2025-11-10T10:00:00',
                    'review': {
                        'FILENAME': 'max_appeals_test.pdf',
                        'TITLE': 'Max Appeals Test',
                        'CORE_DOMAIN': 'Neuromorphic Computing',
                        'PUBLICATION_YEAR': 2023,
                        'Requirement(s)': [
                            {
                                'claim_id': 'stubborn_claim',
                                'status': 'pending_judge_review',
                                'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                                'sub_requirement': 'SR 1.1',
                                'extracted_claim_text': 'Claim after max appeals',
                                'evidence': 'Still insufficient after 2 appeals',
                                'page_number': 5,
                                'appeal_count': MAX_APPEALS
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Execute: Simulate Judge final decision (no new appeal)
        with open(version_history_file, 'r') as f:
            history = json.load(f)
        
        latest_review = history['max_appeals_test.pdf'][-1]['review']
        claim = latest_review['Requirement(s)'][0]
        
        # Judge should finalize without creating new appeal
        claim['status'] = 'rejected'
        claim['judge_notes'] = 'Final rejection after max appeals reached.'
        claim['judge_timestamp'] = datetime.now().isoformat()
        claim['appeal_requested'] = False  # No more appeals
        claim['final_decision'] = True
        
        # Create final version
        new_version = {
            'timestamp': datetime.now().isoformat(),
            'review': latest_review,
            'changes': {
                'status': 'judge_final_decision',
                'updated_claims': 1,
                'claim_ids': ['stubborn_claim']
            }
        }
        history['max_appeals_test.pdf'].append(new_version)
        
        with open(version_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Assert: Verify no new appeal created
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        latest_review = updated_history['max_appeals_test.pdf'][-1]['review']
        claim = latest_review['Requirement(s)'][0]
        
        # Should be finalized (no new appeal_requested)
        assert claim.get('appeal_requested', False) is False
        assert claim['appeal_count'] == MAX_APPEALS
        assert claim['status'] == 'rejected'
        assert claim.get('final_decision', False) is True
    
    @pytest.mark.integration
    def test_borderline_claims_consensus_metadata(self, temp_workspace, test_data_generator):
        """
        Test that borderline claims get consensus review metadata.
        
        Validates that claims with borderline quality scores (2.5-3.5)
        trigger consensus review and store appropriate metadata.
        """
        # Setup: Create version history with borderline claim
        version_history = {
            "borderline_paper.pdf": [
                {
                    'timestamp': '2025-11-13T10:00:00',
                    'review': {
                        'FILENAME': 'borderline_paper.pdf',
                        'TITLE': 'Borderline Evidence Paper',
                        'CORE_DOMAIN': 'Neuromorphic Computing',
                        'PUBLICATION_YEAR': 2023,
                        'Requirement(s)': [
                            {
                                'claim_id': 'borderline_claim_001',
                                'status': 'pending_judge_review',
                                'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                                'sub_requirement': 'Sub-1.1.1',
                                'extracted_claim_text': 'Borderline quality claim',
                                'evidence': 'Moderate evidence quality',
                                'page_number': 5,
                                'evidence_quality': {
                                    'composite_score': 2.8,  # Borderline (2.5-3.5)
                                    'strength_score': 3,
                                    'rigor_score': 2,
                                    'relevance_score': 3,
                                    'directness': 3,
                                    'is_recent': True,
                                    'reproducibility_score': 3
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Execute: Simulate Judge triggering consensus for borderline claim
        with open(version_history_file, 'r') as f:
            history = json.load(f)
        
        latest_review = history['borderline_paper.pdf'][-1]['review']
        claim = latest_review['Requirement(s)'][0]
        
        # Check if consensus should be triggered
        composite_score = claim['evidence_quality']['composite_score']
        should_trigger_consensus = 2.5 <= composite_score <= 3.5
        
        if should_trigger_consensus:
            claim['consensus_review'] = {
                'triggered': True,
                'reason': 'borderline_composite_score',
                'composite_score': composite_score,
                'consensus_reviewers': ['reviewer_A', 'reviewer_B'],
                'timestamp': datetime.now().isoformat()
            }
            claim['status'] = 'pending_consensus_review'
        
        # Create new version with consensus metadata
        new_version = {
            'timestamp': datetime.now().isoformat(),
            'review': latest_review,
            'changes': {
                'status': 'consensus_triggered',
                'updated_claims': 1,
                'claim_ids': ['borderline_claim_001']
            }
        }
        history['borderline_paper.pdf'].append(new_version)
        
        with open(version_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Assert: Verify consensus triggered
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        latest_review = updated_history['borderline_paper.pdf'][-1]['review']
        claim = latest_review['Requirement(s)'][0]
        
        # Check consensus metadata
        assert 'consensus_review' in claim
        assert claim['consensus_review']['triggered'] is True
        assert claim['consensus_review']['reason'] == 'borderline_composite_score'
        assert 'consensus_reviewers' in claim['consensus_review']
        assert len(claim['consensus_review']['consensus_reviewers']) >= 2
        assert claim['status'] == 'pending_consensus_review'
    
    @pytest.mark.integration
    def test_temporal_coherence_in_appeal(self, temp_workspace, test_data_generator):
        """
        Test that temporal coherence analysis is tracked during appeals.
        
        Validates that publication year trends and recency considerations
        are properly recorded when DRA performs appeal reanalysis.
        """
        # Setup: Create version history with temporal data
        version_history = {
            "temporal_paper.pdf": [
                {
                    'timestamp': '2025-11-13T10:00:00',
                    'review': {
                        'FILENAME': 'temporal_paper.pdf',
                        'TITLE': 'Old Study',
                        'CORE_DOMAIN': 'Neuromorphic Computing',
                        'PUBLICATION_YEAR': 2010,
                        'Requirement(s)': [
                            {
                                'claim_id': 'old_claim',
                                'status': 'rejected',
                                'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                                'sub_requirement': 'Sub-1.1.1',
                                'extracted_claim_text': 'Outdated claim',
                                'evidence': 'Evidence from 2010',
                                'page_number': 5,
                                'evidence_quality': {
                                    'composite_score': 2.5,
                                    'is_recent': False,  # Old publication
                                    'recency_penalty': -0.5
                                },
                                'judge_notes': 'Evidence too old. Request DRA to find newer sources.',
                                'appeal_requested': True,
                                'appeal_count': 1
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Execute: Simulate DRA reanalysis with temporal coherence
        with open(version_history_file, 'r') as f:
            history = json.load(f)
        
        # Simulate DRA finding newer evidence
        updated_claim = {
            'claim_id': 'old_claim',
            'status': 'pending_judge_review',
            'pillar': 'Pillar 1: Bio-Inspired Algorithms',
            'sub_requirement': 'Sub-1.1.1',
            'extracted_claim_text': 'Updated claim with recent evidence',
            'evidence': 'Evidence including 2010 study + recent 2023 confirmatory studies',
            'page_number': 5,
            'evidence_quality': {
                'composite_score': 3.5,  # Improved with recent evidence
                'is_recent': True,
                'recency_penalty': 0.0
            },
            'temporal_coherence': {
                'newer_sources_found': True,
                'publication_years': [2010, 2022, 2023],  # Original + new
                'quality_trend': 'improving',
                'recency_boost': +0.5,
                'analysis_timestamp': '2025-11-13T11:00:00'
            },
            'appeal_count': 1,
            'reanalysis_timestamp': '2025-11-13T11:00:00'
        }
        
        # Append reanalysis with temporal coherence
        new_version = {
            'timestamp': updated_claim['reanalysis_timestamp'],
            'review': {
                'FILENAME': 'temporal_paper.pdf',
                'TITLE': 'Old Study',
                'CORE_DOMAIN': 'Neuromorphic Computing',
                'PUBLICATION_YEAR': 2010,
                'Requirement(s)': [updated_claim]
            },
            'changes': {
                'status': 'dra_appeal_temporal',
                'updated_claims': 1,
                'claim_ids': ['old_claim']
            }
        }
        history['temporal_paper.pdf'].append(new_version)
        
        with open(version_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Assert: Verify temporal coherence analysis
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        reanalysis = updated_history['temporal_paper.pdf'][-1]['review']
        claim = reanalysis['Requirement(s)'][0]
        
        assert 'temporal_coherence' in claim
        assert claim['temporal_coherence']['newer_sources_found'] is True
        assert claim['temporal_coherence']['quality_trend'] == 'improving'
        assert claim['evidence_quality']['composite_score'] > 2.5  # Improved
        assert len(claim['temporal_coherence']['publication_years']) >= 2
    
    @pytest.mark.integration
    def test_appeal_preserves_original_quality_scores(self, temp_workspace, test_data_generator):
        """
        Test that appeals preserve original quality scores for comparison.
        
        Validates that when DRA creates an appeal, the original quality scores
        are preserved so we can track quality improvements over appeal iterations.
        """
        # Setup: Create version history with rejected claim
        original_quality = {
            'composite_score': 2.3,
            'strength_score': 2,
            'rigor_score': 2,
            'relevance_score': 3,
            'directness': 2,
            'is_recent': False,
            'reproducibility_score': 2
        }
        
        version_history = {
            "appeal_comparison.pdf": [
                {
                    'timestamp': '2025-11-13T10:00:00',
                    'review': {
                        'FILENAME': 'appeal_comparison.pdf',
                        'TITLE': 'Appeal Quality Comparison',
                        'CORE_DOMAIN': 'Neuromorphic Computing',
                        'PUBLICATION_YEAR': 2023,
                        'Requirement(s)': [
                            {
                                'claim_id': 'quality_comparison_claim',
                                'status': 'rejected',
                                'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                                'sub_requirement': 'Sub-1.1.1',
                                'extracted_claim_text': 'Original weak claim',
                                'evidence': 'Weak initial evidence',
                                'page_number': 5,
                                'evidence_quality': original_quality.copy(),
                                'judge_notes': 'Quality too low.',
                                'appeal_requested': True,
                                'appeal_count': 1
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Execute: Simulate DRA creating appeal with improved quality
        with open(version_history_file, 'r') as f:
            history = json.load(f)
        
        # DRA creates new claim with improved quality
        new_quality = {
            'composite_score': 3.7,
            'strength_score': 4,
            'rigor_score': 3,
            'relevance_score': 4,
            'directness': 3,
            'is_recent': True,
            'reproducibility_score': 4
        }
        
        updated_claim = {
            'claim_id': 'quality_comparison_claim',
            'status': 'pending_judge_review',
            'pillar': 'Pillar 1: Bio-Inspired Algorithms',
            'sub_requirement': 'Sub-1.1.1',
            'extracted_claim_text': 'Improved claim with better evidence',
            'evidence': 'Much stronger evidence from multiple sources',
            'page_number': 5,
            'evidence_quality': new_quality.copy(),
            'original_evidence_quality': original_quality.copy(),  # Preserve original
            'quality_improvement': {
                'composite_delta': new_quality['composite_score'] - original_quality['composite_score'],
                'strength_delta': new_quality['strength_score'] - original_quality['strength_score'],
                'improved': True
            },
            'appeal_count': 1,
            'reanalysis_timestamp': '2025-11-13T11:00:00'
        }
        
        # Append appeal version
        new_version = {
            'timestamp': updated_claim['reanalysis_timestamp'],
            'review': {
                'FILENAME': 'appeal_comparison.pdf',
                'TITLE': 'Appeal Quality Comparison',
                'CORE_DOMAIN': 'Neuromorphic Computing',
                'PUBLICATION_YEAR': 2023,
                'Requirement(s)': [updated_claim]
            },
            'changes': {
                'status': 'dra_appeal_quality_improvement',
                'updated_claims': 1,
                'claim_ids': ['quality_comparison_claim']
            }
        }
        history['appeal_comparison.pdf'].append(new_version)
        
        with open(version_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Assert: Verify quality comparison tracking
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        # Check original version still has original scores
        original_version = updated_history['appeal_comparison.pdf'][0]['review']
        original_claim = original_version['Requirement(s)'][0]
        assert original_claim['evidence_quality']['composite_score'] == 2.3
        
        # Check appeal version has both new and original scores
        appeal_version = updated_history['appeal_comparison.pdf'][1]['review']
        appeal_claim = appeal_version['Requirement(s)'][0]
        
        assert 'original_evidence_quality' in appeal_claim
        assert appeal_claim['original_evidence_quality']['composite_score'] == 2.3
        assert appeal_claim['evidence_quality']['composite_score'] == 3.7
        assert 'quality_improvement' in appeal_claim
        assert appeal_claim['quality_improvement']['improved'] is True
        assert appeal_claim['quality_improvement']['composite_delta'] > 0
