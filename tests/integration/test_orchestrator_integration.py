"""Integration tests for Orchestrator component coordination."""

import pytest
import json
import os
from pathlib import Path
from typing import Dict, List

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.orchestrator_integration import Orchestrator


class TestOrchestratorIntegration:
    """Test Orchestrator coordination of all components."""
    
    @pytest.mark.integration
    def test_orchestrator_coordinates_full_workflow(self, temp_workspace, test_data_generator):
        """Test Orchestrator runs Journal → Deep → Judge → CSV sync."""
        
        # Setup: Create input PDF and empty databases
        pdf_file = temp_workspace / "test_paper.pdf"
        # Create a dummy PDF file
        pdf_file.write_text("Dummy PDF content")
        
        version_history_file = temp_workspace / "review_version_history.json"
        csv_file = temp_workspace / "neuromorphic-research_database.csv"
        
        # Initialize empty version history
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute: Run full orchestration
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            csv_database_path=str(csv_file)
        )
        
        orchestrator.process_paper(str(pdf_file))
        
        # Assert: Verify all components ran
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        # Should have entries for test_paper.pdf
        assert "test_paper.pdf" in version_history
        
        # Check multiple versions (at least the initial one)
        versions = version_history["test_paper.pdf"]
        assert len(versions) >= 1
        
        # Verify component sequence
        latest = versions[-1]['review']
        assert 'source' in latest
        assert latest['source'] == 'journal'  # Journal-Reviewer ran
    
    @pytest.mark.integration
    def test_orchestrator_passes_data_between_components(self, temp_workspace, test_data_generator):
        """Test Orchestrator correctly passes data between components."""
        
        # Setup: Create version history with Journal-Reviewer output
        version_history = {
            "handoff_test.pdf": [
                {
                    'timestamp': '2025-11-10T10:00:00',
                    'review': {
                        'FILENAME': 'handoff_test.pdf',
                        'TITLE': 'Handoff Test Paper',
                        'Requirement(s)': [
                            {
                                'claim_id': 'journal_claim_001',
                                'status': 'pending_judge_review',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.1',
                                'extracted_claim_text': 'Claim from Journal-Reviewer',
                                'evidence': 'Evidence from journal review',
                                'page_number': 3,
                                'source': 'journal',
                                'reviewer_confidence': 0.85
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Execute: Run Judge via Orchestrator
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file)
        )
        
        orchestrator.run_judge()
        
        # Assert: Verify Judge processed Journal-Reviewer output
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        versions = updated_history['handoff_test.pdf']
        assert len(versions) >= 2  # Original + Judge update
        
        # Check Judge added decision
        latest = versions[-1]['review']
        claim = latest['Requirement(s)'][0]
        
        assert claim['status'] in ['approved', 'rejected']
        assert 'judge_notes' in claim
        assert claim.get('source') == 'journal'  # Preserved from Journal-Reviewer
    
    @pytest.mark.integration
    def test_orchestrator_triggers_csv_sync_after_approval(self, temp_workspace, test_data_generator):
        """Test Orchestrator syncs approved claims to CSV."""
        
        # Setup: Create version history with approved claims
        version_history = {
            "approved_paper.pdf": [
                {
                    'timestamp': '2025-11-10T10:00:00',
                    'review': {
                        'FILENAME': 'approved_paper.pdf',
                        'TITLE': 'Approved Paper',
                        'PUBLICATION_YEAR': 2024,
                        'Requirement(s)': [
                            {
                                'claim_id': 'approved_claim',
                                'status': 'approved',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.1',
                                'extracted_claim_text': 'Approved claim',
                                'evidence': 'Strong evidence',
                                'page_number': 5
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        csv_file = temp_workspace / "database.csv"
        
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Execute: Run CSV sync via Orchestrator
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            csv_database_path=str(csv_file)
        )
        
        orchestrator.sync_to_csv()
        
        # Assert: Verify CSV created with approved claim
        assert os.path.exists(csv_file)
        
        import pandas as pd
        df = pd.read_csv(csv_file)
        
        assert len(df) == 1
        assert df.iloc[0]['FILENAME'] == 'approved_paper.pdf'
        
        # Check claim synced
        claims = json.loads(df.iloc[0]['Requirement(s)'])
        assert len(claims) == 1
        assert claims[0]['status'] == 'approved'
    
    @pytest.mark.integration
    def test_orchestrator_handles_component_failures(self, temp_workspace, test_data_generator):
        """Test Orchestrator gracefully handles component failures."""
        
        # Setup: Create invalid input to trigger failure
        version_history_file = temp_workspace / "review_version_history.json"
        
        # Invalid JSON
        with open(version_history_file, 'w') as f:
            f.write("INVALID JSON{{{")
        
        # Execute: Run Orchestrator with error handling
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file)
        )
        
        # Should raise exception when trying to parse invalid JSON
        with pytest.raises((json.JSONDecodeError, ValueError)):
            orchestrator.run_judge()
    
    @pytest.mark.integration
    def test_orchestrator_triangulates_evidence_across_reviewers(self, temp_workspace, test_data_generator):
        """
        Test Orchestrator aggregates evidence from Journal + Deep reviewers for triangulation.
        
        Validates:
        - Cross-referencing between reviewers
        - Consensus score computation
        - Conflicting evidence resolution
        - Triangulation metadata storage
        """
        # Setup: Create version history with both Journal and Deep reviewer claims
        version_history = {
            "triangulation_paper.pdf": [
                # Journal-Reviewer version
                {
                    'timestamp': '2025-11-13T10:00:00',
                    'review': {
                        'FILENAME': 'triangulation_paper.pdf',
                        'TITLE': 'Triangulation Test',
                        'PUBLICATION_YEAR': 2024,
                        'Requirement(s)': [
                            {
                                'claim_id': 'journal_claim_001',
                                'status': 'pending_judge_review',
                                'sub_requirement': 'Sub-1.1.1',
                                'extracted_claim_text': 'Claim from journal review',
                                'source': 'journal',
                                'evidence_quality': {
                                    'composite_score': 3.5,
                                    'strength_score': 4,
                                    'rigor_score': 3
                                },
                                'provenance': {
                                    'page_numbers': [5],
                                    'section': 'Results'
                                }
                            }
                        ]
                    }
                },
                # Deep-Reviewer version (same sub-requirement)
                {
                    'timestamp': '2025-11-13T11:00:00',
                    'review': {
                        'FILENAME': 'triangulation_paper.pdf',
                        'TITLE': 'Triangulation Test',
                        'PUBLICATION_YEAR': 2024,
                        'Requirement(s)': [
                            {
                                'claim_id': 'deep_claim_001',
                                'status': 'pending_judge_review',
                                'sub_requirement': 'Sub-1.1.1',  # Same sub-req
                                'extracted_claim_text': 'Claim from deep review (more detailed)',
                                'source': 'deep_coverage',
                                'evidence_quality': {
                                    'composite_score': 4.0,
                                    'strength_score': 4,
                                    'rigor_score': 4
                                },
                                'provenance': {
                                    'page_numbers': [5, 6, 12],  # Additional pages
                                    'section': 'Results'
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
        
        # Execute: Orchestrator triangulates evidence
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file)
        )
        
        orchestrator.triangulate_evidence()
        
        # Read updated version history
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        # Assert: Verify triangulation performed
        versions = updated_history['triangulation_paper.pdf']
        
        # Should have triangulation metadata appended
        triangulation_version = versions[-1]['review']
        
        assert 'triangulation_analysis' in triangulation_version
        
        triangulation = triangulation_version['triangulation_analysis']
        
        # Check cross-referencing
        assert 'cross_references' in triangulation
        assert len(triangulation['cross_references']) >= 1
        
        # Check consensus score computed
        assert 'consensus_composite_score' in triangulation
        # Average of 3.5 and 4.0 = 3.75
        assert 3.5 <= triangulation['consensus_composite_score'] <= 4.0
        
        # Check combined provenance
        assert 'combined_provenance' in triangulation
        combined_pages = triangulation['combined_provenance']['page_numbers']
        assert set(combined_pages) == {5, 6, 12}  # Union of both reviewers
    
    @pytest.mark.integration
    def test_orchestrator_resolves_conflicting_evidence(self, temp_workspace, test_data_generator):
        """
        Test Orchestrator handles conflicting evidence from multiple reviewers.
        
        Validates:
        - Conflict detection (same sub-req, different quality scores)
        - Conflict resolution strategy (e.g., take higher score, average, or flag for manual review)
        - Conflict metadata stored
        """
        # Setup: Create version history with conflicting claims
        version_history = {
            "conflict_paper.pdf": [
                # Journal-Reviewer: low quality
                {
                    'timestamp': '2025-11-13T10:00:00',
                    'review': {
                        'FILENAME': 'conflict_paper.pdf',
                        'TITLE': 'Conflict Test',
                        'Requirement(s)': [
                            {
                                'claim_id': 'journal_low_quality',
                                'status': 'pending_judge_review',
                                'sub_requirement': 'Sub-1.1.1',
                                'extracted_claim_text': 'Low quality claim',
                                'source': 'journal',
                                'evidence_quality': {
                                    'composite_score': 2.0,
                                    'strength_score': 2,
                                    'rigor_score': 2
                                }
                            }
                        ]
                    }
                },
                # Deep-Reviewer: high quality for same sub-req
                {
                    'timestamp': '2025-11-13T11:00:00',
                    'review': {
                        'FILENAME': 'conflict_paper.pdf',
                        'TITLE': 'Conflict Test',
                        'Requirement(s)': [
                            {
                                'claim_id': 'deep_high_quality',
                                'status': 'pending_judge_review',
                                'sub_requirement': 'Sub-1.1.1',  # Same sub-req
                                'extracted_claim_text': 'High quality claim',
                                'source': 'deep_coverage',
                                'evidence_quality': {
                                    'composite_score': 4.5,
                                    'strength_score': 5,
                                    'rigor_score': 4
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
        
        # Execute: Orchestrator detects and resolves conflict
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file)
        )
        
        orchestrator.triangulate_evidence()
        
        # Read updated version history
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        # Assert: Verify conflict resolution
        versions = updated_history['conflict_paper.pdf']
        triangulation_version = versions[-1]['review']
        
        assert 'triangulation_analysis' in triangulation_version
        triangulation = triangulation_version['triangulation_analysis']
        
        # Check conflict detected
        assert 'conflicts_detected' in triangulation
        assert triangulation['conflicts_detected'] is True
        
        # Check conflict details
        assert 'conflict_resolution' in triangulation
        resolution = triangulation['conflict_resolution']
        
        assert resolution['strategy'] in ['take_higher_score', 'average', 'manual_review']
        
        # Verify resolved score (e.g., take higher = 4.5, average = 3.25)
        assert 'resolved_composite_score' in resolution
        resolved_score = resolution['resolved_composite_score']
        
        if resolution['strategy'] == 'take_higher_score':
            assert resolved_score == 4.5
        elif resolution['strategy'] == 'average':
            assert resolved_score == pytest.approx(3.25, rel=0.1)
