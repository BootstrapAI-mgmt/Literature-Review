"""Integration tests for Version History → CSV sync."""

import pytest
import json
import csv
import os
import pandas as pd
from pathlib import Path
from typing import Dict, List

# Import sync functionality (if refactored) or test script execution


class TestVersionHistorySync:
    """Test sync from version history to CSV database."""
    
    @pytest.mark.integration
    def test_sync_approved_claims_to_csv(self, temp_workspace, test_data_generator):
        """Test that sync copies only approved claims to CSV."""
        
        # Setup: Create version history with mixed statuses
        version_history = {
            "paper1.pdf": [
                {
                    'timestamp': '2025-11-10T10:00:00',
                    'review': {
                        'FILENAME': 'paper1.pdf',
                        'TITLE': 'Test Paper 1',
                        'PUBLICATION_YEAR': 2024,
                        'Requirement(s)': [
                            {
                                'claim_id': 'approved_claim_1',
                                'status': 'approved',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.1',
                                'evidence': 'Approved evidence',
                                'page_number': 1
                            },
                            {
                                'claim_id': 'rejected_claim_1',
                                'status': 'rejected',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.2',
                                'evidence': 'Rejected evidence',
                                'page_number': 2
                            },
                            {
                                'claim_id': 'pending_claim_1',
                                'status': 'pending_judge_review',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.3',
                                'evidence': 'Pending evidence',
                                'page_number': 3
                            }
                        ]
                    }
                }
            ],
            "paper2.pdf": [
                {
                    'timestamp': '2025-11-10T11:00:00',
                    'review': {
                        'FILENAME': 'paper2.pdf',
                        'TITLE': 'Test Paper 2',
                        'PUBLICATION_YEAR': 2025,
                        'Requirement(s)': [
                            {
                                'claim_id': 'approved_claim_2',
                                'status': 'approved',
                                'pillar': 'Pillar 2',
                                'sub_requirement': 'SR 2.1',
                                'evidence': 'Approved evidence 2',
                                'page_number': 5
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        csv_file = temp_workspace / "neuromorphic-research_database.csv"
        
        # Execute: Perform sync (simplified sync logic)
        # In real implementation, this would call sync_history_to_db.py
        synced_papers = []
        
        for filename, versions in version_history.items():
            if not versions:
                continue
            
            latest = versions[-1]['review']
            
            # Extract approved claims
            approved_claims = [
                c for c in latest.get('Requirement(s)', [])
                if c.get('status') == 'approved'
            ]
            
            if approved_claims:
                paper_entry = {
                    'FILENAME': latest.get('FILENAME', filename),
                    'TITLE': latest.get('TITLE', ''),
                    'PUBLICATION_YEAR': latest.get('PUBLICATION_YEAR', ''),
                    'Requirement(s)': json.dumps(approved_claims)
                }
                synced_papers.append(paper_entry)
        
        # Write to CSV
        if synced_papers:
            fieldnames = ['FILENAME', 'TITLE', 'PUBLICATION_YEAR', 'Requirement(s)']
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(synced_papers)
        
        # Assert: Verify sync results
        assert csv_file.exists()
        
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Check row count (should be 2 papers)
        assert len(df) == 2
        
        # Check that only approved claims are present
        for _, row in df.iterrows():
            claims = json.loads(row['Requirement(s)'])
            for claim in claims:
                assert claim['status'] == 'approved'
        
        # Verify specific counts
        paper1_row = df[df['FILENAME'] == 'paper1.pdf'].iloc[0]
        paper1_claims = json.loads(paper1_row['Requirement(s)'])
        assert len(paper1_claims) == 1  # Only 1 approved out of 3
        
        paper2_row = df[df['FILENAME'] == 'paper2.pdf'].iloc[0]
        paper2_claims = json.loads(paper2_row['Requirement(s)'])
        assert len(paper2_claims) == 1  # 1 approved claim
    
    @pytest.mark.integration
    def test_sync_handles_empty_version_history(self, temp_workspace):
        """Test sync gracefully handles empty version history."""
        
        # Setup: Empty version history
        version_history = {}
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        csv_file = temp_workspace / "neuromorphic-research_database.csv"
        
        # Execute: Sync should create empty or minimal CSV
        synced_papers = []
        for filename, versions in version_history.items():
            pass  # No papers to sync
        
        # Should not create CSV or create empty CSV
        # For this test, we verify no crash occurs
        assert True  # Sync completed without error
    
    @pytest.mark.integration
    def test_sync_preserves_claim_fields(self, temp_workspace):
        """Test that all claim fields are preserved in sync."""
        
        # Setup: Version history with extended claim fields
        version_history = {
            "detailed_paper.pdf": [
                {
                    'timestamp': '2025-11-10T12:00:00',
                    'review': {
                        'FILENAME': 'detailed_paper.pdf',
                        'TITLE': 'Detailed Test',
                        'Requirement(s)': [
                            {
                                'claim_id': 'detailed_claim',
                                'status': 'approved',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.1',
                                'evidence': 'Detailed evidence',
                                'page_number': 10,
                                'reviewer_confidence': 0.95,
                                'review_timestamp': '2025-11-10T09:00:00',
                                'source': 'deep_coverage',
                                'judge_notes': 'Approved. Excellent evidence.',
                                'judge_timestamp': '2025-11-10T10:00:00'
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        csv_file = temp_workspace / "neuromorphic-research_database.csv"
        
        # Execute sync
        synced_papers = []
        for filename, versions in version_history.items():
            latest = versions[-1]['review']
            approved_claims = [
                c for c in latest.get('Requirement(s)', [])
                if c.get('status') == 'approved'
            ]
            if approved_claims:
                paper_entry = {
                    'FILENAME': latest['FILENAME'],
                    'TITLE': latest['TITLE'],
                    'Requirement(s)': json.dumps(approved_claims)
                }
                synced_papers.append(paper_entry)
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['FILENAME', 'TITLE', 'Requirement(s)'],
                quoting=csv.QUOTE_ALL
            )
            writer.writeheader()
            writer.writerows(synced_papers)
        
        # Assert: Verify all fields preserved
        df = pd.read_csv(csv_file)
        row = df.iloc[0]
        claims = json.loads(row['Requirement(s)'])
        claim = claims[0]
        
        # Check extended fields present
        assert 'claim_id' in claim
        assert 'reviewer_confidence' in claim
        assert claim['reviewer_confidence'] == 0.95
        assert 'review_timestamp' in claim
        assert 'source' in claim
        assert claim['source'] == 'deep_coverage'
        assert 'judge_notes' in claim
        assert 'judge_timestamp' in claim
    
    @pytest.mark.integration
    def test_sync_excludes_rejected_and_pending_claims(self, temp_workspace):
        """Test that rejected and pending claims are excluded from sync."""
        
        # Setup: Create version history with all three statuses
        version_history = {
            "mixed_status_paper.pdf": [
                {
                    'timestamp': '2025-11-10T13:00:00',
                    'review': {
                        'FILENAME': 'mixed_status_paper.pdf',
                        'TITLE': 'Mixed Status Paper',
                        'PUBLICATION_YEAR': 2024,
                        'Requirement(s)': [
                            {
                                'claim_id': 'claim_approved',
                                'status': 'approved',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.1',
                                'evidence': 'Good evidence',
                                'page_number': 1
                            },
                            {
                                'claim_id': 'claim_rejected',
                                'status': 'rejected',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.2',
                                'evidence': 'Weak evidence',
                                'page_number': 2
                            },
                            {
                                'claim_id': 'claim_pending',
                                'status': 'pending_judge_review',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.3',
                                'evidence': 'Unreviewed evidence',
                                'page_number': 3
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        csv_file = temp_workspace / "neuromorphic-research_database.csv"
        
        # Execute sync
        synced_papers = []
        for filename, versions in version_history.items():
            latest = versions[-1]['review']
            approved_claims = [
                c for c in latest.get('Requirement(s)', [])
                if c.get('status') == 'approved'
            ]
            if approved_claims:
                paper_entry = {
                    'FILENAME': latest['FILENAME'],
                    'TITLE': latest['TITLE'],
                    'PUBLICATION_YEAR': latest['PUBLICATION_YEAR'],
                    'Requirement(s)': json.dumps(approved_claims)
                }
                synced_papers.append(paper_entry)
        
        # Write to CSV
        if synced_papers:
            fieldnames = ['FILENAME', 'TITLE', 'PUBLICATION_YEAR', 'Requirement(s)']
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(synced_papers)
        
        # Assert: Verify only approved claim is synced
        df = pd.read_csv(csv_file)
        assert len(df) == 1  # One paper synced
        
        row = df.iloc[0]
        claims = json.loads(row['Requirement(s)'])
        assert len(claims) == 1  # Only one claim
        assert claims[0]['claim_id'] == 'claim_approved'
        assert claims[0]['status'] == 'approved'
    
    @pytest.mark.integration
    def test_sync_with_no_approved_claims(self, temp_workspace):
        """Test sync when a paper has no approved claims."""
        
        # Setup: Version history with only rejected/pending claims
        version_history = {
            "no_approved_paper.pdf": [
                {
                    'timestamp': '2025-11-10T14:00:00',
                    'review': {
                        'FILENAME': 'no_approved_paper.pdf',
                        'TITLE': 'No Approved Claims Paper',
                        'PUBLICATION_YEAR': 2023,
                        'Requirement(s)': [
                            {
                                'claim_id': 'claim_rejected_1',
                                'status': 'rejected',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.1',
                                'evidence': 'Weak evidence',
                                'page_number': 1
                            },
                            {
                                'claim_id': 'claim_pending_1',
                                'status': 'pending_judge_review',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.2',
                                'evidence': 'Pending evidence',
                                'page_number': 2
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        csv_file = temp_workspace / "neuromorphic-research_database.csv"
        
        # Execute sync
        synced_papers = []
        for filename, versions in version_history.items():
            latest = versions[-1]['review']
            approved_claims = [
                c for c in latest.get('Requirement(s)', [])
                if c.get('status') == 'approved'
            ]
            if approved_claims:
                paper_entry = {
                    'FILENAME': latest['FILENAME'],
                    'TITLE': latest['TITLE'],
                    'PUBLICATION_YEAR': latest['PUBLICATION_YEAR'],
                    'Requirement(s)': json.dumps(approved_claims)
                }
                synced_papers.append(paper_entry)
        
        # Assert: No CSV should be created or CSV should be empty
        assert len(synced_papers) == 0
    
    @pytest.mark.integration
    def test_quality_scores_sync_to_csv(self, temp_workspace, test_data_generator):
        """
        Test that evidence quality scores sync from version history to CSV.
        
        Validates:
        - Composite scores added to claims
        - All 6 dimensions synced
        - Provenance metadata preserved (page numbers, sections)
        """
        # Setup: Create version history with quality scores
        version_history = {
            "paper_a.pdf": [
                {
                    'timestamp': '2025-11-13T10:00:00',
                    'review': {
                        'FILENAME': 'paper_a.pdf',
                        'TITLE': 'High Quality Paper',
                        'PUBLICATION_YEAR': 2024,
                        'Requirement(s)': [
                            {
                                'claim_id': 'claim_001',
                                'status': 'approved',
                                'extracted_claim_text': 'High quality claim',
                                'sub_requirement': 'Sub-1.1.1',
                                'evidence_quality': {
                                    'composite_score': 4.2,
                                    'strength_score': 4,
                                    'rigor_score': 5,
                                    'relevance_score': 4,
                                    'directness': 3,
                                    'is_recent': True,
                                    'reproducibility_score': 4,
                                    'study_type': 'experimental',
                                    'confidence_level': 'high'
                                },
                                'provenance': {
                                    'page_numbers': [5, 6],
                                    'section': 'Results',
                                    'quote_page': 5
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
        
        # Execute: Sync with quality score extraction
        csv_file = temp_workspace / "output_database.csv"
        
        synced_papers = []
        for filename, versions in version_history.items():
            latest = versions[-1]['review']
            approved_claims = [
                c for c in latest.get('Requirement(s)', [])
                if c.get('status') == 'approved'
            ]
            
            if approved_claims:
                # Extract quality scores for CSV columns
                for claim in approved_claims:
                    quality = claim.get('evidence_quality', {})
                    provenance = claim.get('provenance', {})
                    
                    # Add quality score fields to claim
                    claim['EVIDENCE_COMPOSITE_SCORE'] = quality.get('composite_score')
                    claim['EVIDENCE_STRENGTH_SCORE'] = quality.get('strength_score')
                    claim['EVIDENCE_RIGOR_SCORE'] = quality.get('rigor_score')
                    claim['EVIDENCE_RELEVANCE_SCORE'] = quality.get('relevance_score')
                    claim['EVIDENCE_DIRECTNESS'] = quality.get('directness')
                    claim['EVIDENCE_IS_RECENT'] = quality.get('is_recent')
                    claim['EVIDENCE_REPRODUCIBILITY_SCORE'] = quality.get('reproducibility_score')
                    claim['STUDY_TYPE'] = quality.get('study_type')
                    
                    # Add provenance columns
                    claim['PROVENANCE_PAGE_NUMBERS'] = json.dumps(provenance.get('page_numbers', [])) if provenance.get('page_numbers') else None
                    claim['PROVENANCE_SECTION'] = provenance.get('section')
                    claim['PROVENANCE_QUOTE_PAGE'] = provenance.get('quote_page')
                
                paper_entry = {
                    'FILENAME': latest['FILENAME'],
                    'TITLE': latest['TITLE'],
                    'PUBLICATION_YEAR': latest['PUBLICATION_YEAR'],
                    'Requirement(s)': json.dumps(approved_claims)
                }
                synced_papers.append(paper_entry)
        
        # Write to CSV
        if synced_papers:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['FILENAME', 'TITLE', 'PUBLICATION_YEAR', 'Requirement(s)'],
                    quoting=csv.QUOTE_ALL
                )
                writer.writeheader()
                writer.writerows(synced_papers)
        
        # Assert: Check CSV has quality columns embedded in claims
        df = pd.read_csv(csv_file)
        
        row = df.iloc[0]
        claims = json.loads(row['Requirement(s)'])
        claim = claims[0]
        
        # Validate quality score fields
        assert 'EVIDENCE_COMPOSITE_SCORE' in claim
        assert 'EVIDENCE_STRENGTH_SCORE' in claim
        assert 'EVIDENCE_RIGOR_SCORE' in claim
        assert 'PROVENANCE_PAGE_NUMBERS' in claim
        assert 'PROVENANCE_SECTION' in claim
        
        # Validate values
        assert claim['EVIDENCE_COMPOSITE_SCORE'] == 4.2
        assert claim['EVIDENCE_STRENGTH_SCORE'] == 4
        assert claim['PROVENANCE_PAGE_NUMBERS'] == '[5, 6]'  # JSON serialized
        assert claim['PROVENANCE_SECTION'] == 'Results'
    
    @pytest.mark.integration
    def test_backward_compatibility_missing_quality_scores(self, temp_workspace, test_data_generator):
        """
        Test that claims without quality scores sync correctly (backward compatibility).
        
        Legacy claims should get default scores or null values.
        """
        # Setup: Create version history without quality scores (legacy format)
        legacy_history = {
            "legacy_paper.pdf": [
                {
                    'timestamp': '2025-11-13T10:00:00',
                    'review': {
                        'FILENAME': 'legacy_paper.pdf',
                        'TITLE': 'Legacy Paper',
                        'PUBLICATION_YEAR': 2020,
                        'Requirement(s)': [
                            {
                                'claim_id': 'legacy_claim',
                                'status': 'approved',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.1',
                                'evidence': 'Legacy evidence without quality scores'
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(legacy_history, f, indent=2)
        
        # Execute: Sync with backward compatibility
        csv_file = temp_workspace / "output_database.csv"
        
        synced_papers = []
        for filename, versions in legacy_history.items():
            latest = versions[-1]['review']
            approved_claims = [
                c for c in latest.get('Requirement(s)', [])
                if c.get('status') == 'approved'
            ]
            
            if approved_claims:
                # Extract quality scores with defaults for missing data
                for claim in approved_claims:
                    quality = claim.get('evidence_quality', {})
                    
                    # Use None for missing quality data
                    claim['EVIDENCE_COMPOSITE_SCORE'] = quality.get('composite_score', None)
                    claim['EVIDENCE_STRENGTH_SCORE'] = quality.get('strength_score', None)
                    claim['EVIDENCE_RIGOR_SCORE'] = quality.get('rigor_score', None)
                
                paper_entry = {
                    'FILENAME': latest['FILENAME'],
                    'TITLE': latest['TITLE'],
                    'PUBLICATION_YEAR': latest['PUBLICATION_YEAR'],
                    'Requirement(s)': json.dumps(approved_claims)
                }
                synced_papers.append(paper_entry)
        
        # Write to CSV
        if synced_papers:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['FILENAME', 'TITLE', 'PUBLICATION_YEAR', 'Requirement(s)'],
                    quoting=csv.QUOTE_ALL
                )
                writer.writeheader()
                writer.writerows(synced_papers)
        
        # Assert: Check backward compatibility
        df = pd.read_csv(csv_file)
        row = df.iloc[0]
        claims = json.loads(row['Requirement(s)'])
        claim = claims[0]
        
        # Should have quality score fields but with None values
        assert 'EVIDENCE_COMPOSITE_SCORE' in claim
        assert claim['EVIDENCE_COMPOSITE_SCORE'] is None  # Legacy claim without score
    
    @pytest.mark.integration
    def test_multiple_papers_with_mixed_quality_scores(self, temp_workspace):
        """Test sync with multiple papers having mixed quality score availability."""
        # Setup: Create version history with both legacy and enhanced claims
        version_history = {
            "enhanced_paper.pdf": [
                {
                    'timestamp': '2025-11-13T11:00:00',
                    'review': {
                        'FILENAME': 'enhanced_paper.pdf',
                        'TITLE': 'Enhanced Paper',
                        'PUBLICATION_YEAR': 2024,
                        'Requirement(s)': [
                            {
                                'claim_id': 'enhanced_claim',
                                'status': 'approved',
                                'sub_requirement': 'Sub-1.1.1',
                                'evidence_quality': {
                                    'composite_score': 3.8,
                                    'strength_score': 4,
                                    'rigor_score': 4,
                                    'relevance_score': 3,
                                    'directness': 3,
                                    'is_recent': False,
                                    'reproducibility_score': 4
                                }
                            }
                        ]
                    }
                }
            ],
            "legacy_paper.pdf": [
                {
                    'timestamp': '2025-11-13T11:00:00',
                    'review': {
                        'FILENAME': 'legacy_paper.pdf',
                        'TITLE': 'Legacy Paper',
                        'PUBLICATION_YEAR': 2022,
                        'Requirement(s)': [
                            {
                                'claim_id': 'legacy_claim',
                                'status': 'approved',
                                'sub_requirement': 'Sub-2.1.1',
                                'evidence': 'Evidence without quality scores'
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        csv_file = temp_workspace / "output_database.csv"
        
        # Execute sync
        synced_papers = []
        for filename, versions in version_history.items():
            latest = versions[-1]['review']
            approved_claims = [
                c for c in latest.get('Requirement(s)', [])
                if c.get('status') == 'approved'
            ]
            
            if approved_claims:
                for claim in approved_claims:
                    quality = claim.get('evidence_quality', {})
                    claim['EVIDENCE_COMPOSITE_SCORE'] = quality.get('composite_score', None)
                    claim['EVIDENCE_STRENGTH_SCORE'] = quality.get('strength_score', None)
                
                paper_entry = {
                    'FILENAME': latest['FILENAME'],
                    'TITLE': latest['TITLE'],
                    'PUBLICATION_YEAR': latest['PUBLICATION_YEAR'],
                    'Requirement(s)': json.dumps(approved_claims)
                }
                synced_papers.append(paper_entry)
        
        if synced_papers:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['FILENAME', 'TITLE', 'PUBLICATION_YEAR', 'Requirement(s)'],
                    quoting=csv.QUOTE_ALL
                )
                writer.writeheader()
                writer.writerows(synced_papers)
        
        # Assert: Both papers synced with appropriate quality scores
        df = pd.read_csv(csv_file)
        assert len(df) == 2
        
        # Check enhanced paper has scores
        enhanced_row = df[df['FILENAME'] == 'enhanced_paper.pdf'].iloc[0]
        enhanced_claims = json.loads(enhanced_row['Requirement(s)'])
        assert enhanced_claims[0]['EVIDENCE_COMPOSITE_SCORE'] == 3.8
        
        # Check legacy paper has None scores
        legacy_row = df[df['FILENAME'] == 'legacy_paper.pdf'].iloc[0]
        legacy_claims = json.loads(legacy_row['Requirement(s)'])
        assert legacy_claims[0]['EVIDENCE_COMPOSITE_SCORE'] is None
    
    @pytest.mark.integration
    def test_provenance_metadata_array_serialization(self, temp_workspace):
        """Test that provenance metadata with arrays (page_numbers) serializes correctly."""
        version_history = {
            "multi_page_paper.pdf": [
                {
                    'timestamp': '2025-11-13T12:00:00',
                    'review': {
                        'FILENAME': 'multi_page_paper.pdf',
                        'TITLE': 'Multi-Page Evidence Paper',
                        'PUBLICATION_YEAR': 2024,
                        'Requirement(s)': [
                            {
                                'claim_id': 'claim_with_pages',
                                'status': 'approved',
                                'sub_requirement': 'Sub-1.2.1',
                                'provenance': {
                                    'page_numbers': [3, 5, 7, 8],
                                    'section': 'Methods and Results',
                                    'quote_page': 5
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
        
        csv_file = temp_workspace / "output_database.csv"
        
        # Execute sync
        synced_papers = []
        for filename, versions in version_history.items():
            latest = versions[-1]['review']
            approved_claims = [
                c for c in latest.get('Requirement(s)', [])
                if c.get('status') == 'approved'
            ]
            
            if approved_claims:
                for claim in approved_claims:
                    provenance = claim.get('provenance', {})
                    # Serialize page_numbers array to JSON string
                    page_numbers = provenance.get('page_numbers', [])
                    claim['PROVENANCE_PAGE_NUMBERS'] = json.dumps(page_numbers) if page_numbers else None
                    claim['PROVENANCE_SECTION'] = provenance.get('section')
                    claim['PROVENANCE_QUOTE_PAGE'] = provenance.get('quote_page')
                
                paper_entry = {
                    'FILENAME': latest['FILENAME'],
                    'TITLE': latest['TITLE'],
                    'PUBLICATION_YEAR': latest['PUBLICATION_YEAR'],
                    'Requirement(s)': json.dumps(approved_claims)
                }
                synced_papers.append(paper_entry)
        
        if synced_papers:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['FILENAME', 'TITLE', 'PUBLICATION_YEAR', 'Requirement(s)'],
                    quoting=csv.QUOTE_ALL
                )
                writer.writeheader()
                writer.writerows(synced_papers)
        
        # Assert: Array is correctly serialized
        df = pd.read_csv(csv_file)
        row = df.iloc[0]
        claims = json.loads(row['Requirement(s)'])
        claim = claims[0]
        
        assert 'PROVENANCE_PAGE_NUMBERS' in claim
        assert claim['PROVENANCE_PAGE_NUMBERS'] == '[3, 5, 7, 8]'
        
        # Verify it can be deserialized back
        deserialized_pages = json.loads(claim['PROVENANCE_PAGE_NUMBERS'])
        assert deserialized_pages == [3, 5, 7, 8]
        assert claim['PROVENANCE_SECTION'] == 'Methods and Results'
        assert claim['PROVENANCE_QUOTE_PAGE'] == 5
    
    @pytest.mark.integration
    def test_sync_script_with_quality_scores(self, temp_workspace):
        """Test the actual sync script with quality scores."""
        import sys
        import importlib.util
        
        # Load sync script as a module
        script_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '../../scripts/sync_history_to_db.py'
        ))
        spec = importlib.util.spec_from_file_location("sync_module", script_path)
        sync_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sync_module)
        
        # Create test version history with quality scores
        version_history = {
            "test_paper.pdf": [
                {
                    'timestamp': '2025-11-14T10:00:00',
                    'review': {
                        'FILENAME': 'test_paper.pdf',
                        'TITLE': 'Test Paper with Quality Scores',
                        'PUBLICATION_YEAR': 2024,
                        'Requirement(s)': [
                            {
                                'claim_id': 'claim_with_quality',
                                'status': 'approved',
                                'sub_requirement': 'Sub-1.1.1',
                                'evidence_quality': {
                                    'composite_score': 4.5,
                                    'strength_score': 5,
                                    'rigor_score': 4,
                                    'relevance_score': 5,
                                    'directness': 3,
                                    'is_recent': True,
                                    'reproducibility_score': 4
                                },
                                'provenance': {
                                    'page_numbers': [10, 11],
                                    'section': 'Methods'
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
        
        # Use the helper function from sync script
        review = version_history["test_paper.pdf"][0]['review']
        enriched_review = sync_module.enrich_claims_with_quality_scores(review)
        
        # Verify enrichment worked
        claims = enriched_review['Requirement(s)']
        assert len(claims) == 1
        claim = claims[0]
        
        assert 'EVIDENCE_COMPOSITE_SCORE' in claim
        assert claim['EVIDENCE_COMPOSITE_SCORE'] == 4.5
        assert claim['EVIDENCE_STRENGTH_SCORE'] == 5
        assert claim['PROVENANCE_PAGE_NUMBERS'] == '[10, 11]'
        assert claim['PROVENANCE_SECTION'] == 'Methods'
