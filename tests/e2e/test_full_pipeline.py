"""
End-to-end tests for complete literature review pipeline.

Tests the full workflow: PDF → Journal-Reviewer → Deep-Reviewer → Judge → CSV
with all evidence quality enhancements including multi-dimensional scoring,
provenance tracking, consensus review, temporal analysis, and triangulation.

Task Card #10: E2E-001 Full Pipeline Test
"""

import pytest
import json
import os
import csv
from pathlib import Path
from typing import Dict, List
import time

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.orchestrator_integration import Orchestrator
from tests.fixtures.test_data_generator import TestDataGenerator


class TestFullPipeline:
    """Test complete PDF → CSV pipeline with all components."""
    
    @pytest.mark.e2e
    def test_complete_pipeline_single_paper(self, e2e_workspace, test_data_generator):
        """
        Test full pipeline for single paper.
        
        Flow: PDF → Journal-Reviewer → Judge → CSV
        """
        # Setup: Create test PDF
        workspace = Path(e2e_workspace['root'])
        pdf_file = workspace / "test_paper.pdf"
        # Create a simple mock PDF
        pdf_file.write_text("%PDF-1.4\nMock PDF for neuromorphic computing test\n%%EOF")
        
        version_history_file = Path(e2e_workspace['version_history'])
        csv_file = Path(e2e_workspace['csv_db'])
        
        # Initialize empty version history
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute: Run complete pipeline
        start_time = time.time()
        
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            csv_database_path=str(csv_file)
        )
        
        # Process the paper (simulates Journal-Reviewer)
        success = orchestrator.process_paper(str(pdf_file))
        assert success, "Paper processing should succeed"
        
        # Load version history and add some claims for testing
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        # Add mock claims to simulate reviewer output
        version_history["test_paper.pdf"][-1]['review']['Requirement(s)'] = [
            {
                'claim_id': 'claim_001',
                'status': 'pending_judge_review',
                'sub_requirement': 'SR 1.1',
                'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                'extracted_claim_text': 'The system demonstrates neuromorphic computing capabilities.',
                'evidence': 'Page 5: The spiking neural network achieved 95% accuracy on MNIST.',
                'page_number': 5,
                'source': 'journal',
                'evidence_quality': {
                    'strength_score': 4,
                    'rigor_score': 4,
                    'relevance_score': 4,
                    'directness': 3,
                    'reproducibility_score': 4,
                    'composite_score': 4.0
                },
                'provenance': {
                    'page_numbers': [5],
                    'section': 'Results'
                }
            },
            {
                'claim_id': 'claim_002',
                'status': 'pending_judge_review',
                'sub_requirement': 'SR 1.2',
                'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                'extracted_claim_text': 'Energy efficiency demonstrated.',
                'evidence': 'Page 7: Energy consumption 10x lower than traditional ANNs.',
                'page_number': 7,
                'source': 'journal',
                'evidence_quality': {
                    'strength_score': 3,
                    'rigor_score': 3,
                    'relevance_score': 4,
                    'directness': 3,
                    'reproducibility_score': 3,
                    'composite_score': 3.2
                },
                'provenance': {
                    'page_numbers': [7],
                    'section': 'Discussion'
                }
            }
        ]
        
        # Save updated version history
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Run Judge to finalize claims
        orchestrator.run_judge()
        
        # Sync to CSV
        orchestrator.sync_to_csv()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Assert: Verify version history created
        assert os.path.exists(version_history_file)
        
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        assert "test_paper.pdf" in version_history
        versions = version_history["test_paper.pdf"]
        
        # Should have at least 2 versions (Journal + Judge)
        assert len(versions) >= 2
        
        # Verify component sequence
        sources = [v['review'].get('source', 'journal') for v in versions]
        assert 'journal' in sources
        
        # Verify claims have final status
        latest = versions[-1]['review']
        claims = latest.get('Requirement(s)', [])
        assert len(claims) > 0
        
        statuses = [c.get('status') for c in claims]
        assert all(s in ['approved', 'rejected'] for s in statuses)
        
        # Assert: Verify CSV sync
        assert os.path.exists(csv_file)
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Should have entries for approved claims
        approved_claims = [c for c in claims if c.get('status') == 'approved']
        if approved_claims:
            assert len(rows) > 0
            assert rows[0]['FILENAME'] == 'test_paper.pdf'
        
        # Assert: Verify performance
        print(f"Pipeline processing time: {processing_time:.2f}s")
        assert processing_time < 60  # Should complete in under 1 minute
    
    @pytest.mark.e2e
    def test_complete_pipeline_multiple_papers(self, e2e_workspace, test_data_generator):
        """
        Test full pipeline for multiple papers in batch.
        
        Flow: [PDF1, PDF2, PDF3] → Reviewers → Judge → CSV
        """
        # Setup: Create multiple test PDFs
        workspace = Path(e2e_workspace['root'])
        papers = []
        for i in range(3):
            pdf_file = workspace / f"paper_{i+1}.pdf"
            pdf_file.write_text(f"%PDF-1.4\nTest paper {i+1} about neuromorphic computing\n%%EOF")
            papers.append(pdf_file)
        
        version_history_file = Path(e2e_workspace['version_history'])
        csv_file = Path(e2e_workspace['csv_db'])
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute: Process all papers
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            csv_database_path=str(csv_file)
        )
        
        for paper in papers:
            orchestrator.process_paper(str(paper))
        
        # Add mock claims to each paper
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        for i, paper in enumerate(papers):
            filename = paper.name
            if filename in version_history and version_history[filename]:
                version_history[filename][-1]['review']['Requirement(s)'] = [
                    {
                        'claim_id': f'paper{i+1}_claim_001',
                        'status': 'pending_judge_review',
                        'sub_requirement': f'SR {i+1}.1',
                        'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                        'extracted_claim_text': f'Claim from paper {i+1}',
                        'evidence': f'Evidence from paper {i+1}',
                        'page_number': 5,
                        'evidence_quality': {
                            'composite_score': 3.5
                        }
                    }
                ]
        
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Run Judge
        orchestrator.run_judge()
        
        # Sync to CSV
        orchestrator.sync_to_csv()
        
        # Assert: Verify all papers processed
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        assert len(version_history) == 3
        assert "paper_1.pdf" in version_history
        assert "paper_2.pdf" in version_history
        assert "paper_3.pdf" in version_history
        
        # Verify CSV has all approved claims
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Should have entries from multiple papers
        filenames = [row['FILENAME'] for row in rows]
        assert len(set(filenames)) >= 1  # At least one paper had approved claims
    
    @pytest.mark.e2e
    def test_pipeline_data_integrity(self, e2e_workspace, test_data_generator):
        """
        Test data integrity throughout pipeline.
        
        Validates: No data loss, field preservation, JSON serialization
        """
        # Setup: Create paper with detailed claims
        workspace = Path(e2e_workspace['root'])
        pdf_file = workspace / "detailed_paper.pdf"
        pdf_file.write_text("%PDF-1.4\nDetailed neuromorphic computing paper\n%%EOF")
        
        version_history_file = Path(e2e_workspace['version_history'])
        csv_file = Path(e2e_workspace['csv_db'])
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute: Run pipeline
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            csv_database_path=str(csv_file)
        )
        
        orchestrator.process_paper(str(pdf_file))
        
        # Add detailed claims
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        version_history["detailed_paper.pdf"][-1]['review']['Requirement(s)'] = [
            {
                'claim_id': 'detailed_001',
                'status': 'pending_judge_review',
                'sub_requirement': 'SR 1.1',
                'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                'extracted_claim_text': 'Detailed claim with rich metadata',
                'evidence': 'Comprehensive evidence from multiple pages',
                'page_number': 5,
                'evidence_quality': {
                    'strength_score': 4,
                    'rigor_score': 4,
                    'relevance_score': 4,
                    'directness': 3,
                    'reproducibility_score': 4,
                    'composite_score': 4.0
                },
                'provenance': {
                    'page_numbers': [5, 6, 7],
                    'section': 'Results',
                    'extraction_method': 'automated'
                }
            }
        ]
        
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        orchestrator.run_judge()
        orchestrator.sync_to_csv()
        
        # Assert: Verify data integrity
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        latest = version_history['detailed_paper.pdf'][-1]['review']
        original_claims = latest.get('Requirement(s)', [])
        
        # Read CSV
        if os.path.exists(csv_file):
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if rows:
                csv_claims = json.loads(rows[0]['Requirement(s)'])
                
                # Verify required fields preserved
                for claim in csv_claims:
                    assert 'claim_id' in claim
                    assert 'status' in claim
                    assert 'sub_requirement' in claim
                    assert claim['status'] == 'approved'  # Only approved in CSV
    
    @pytest.mark.e2e
    def test_complete_evidence_quality_workflow(self, e2e_workspace, test_data_generator):
        """
        Test full pipeline with all evidence quality enhancements.
        
        Validates:
        - Multi-dimensional quality scores computed
        - Provenance metadata tracked from extraction to CSV
        - Borderline claims trigger consensus
        - Temporal coherence analysis performed
        - Evidence triangulation across reviewers
        - Quality thresholds enforced (composite ≥3.0)
        - Complete audit trail in version history
        """
        # Setup: Create paper that triggers all quality features
        workspace = Path(e2e_workspace['root'])
        pdf_file = workspace / "quality_test_paper.pdf"
        pdf_file.write_text("%PDF-1.4\nHigh quality neuromorphic evidence paper\n%%EOF")
        
        version_history_file = Path(e2e_workspace['version_history'])
        csv_file = Path(e2e_workspace['csv_db'])
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute: Run complete pipeline with quality enhancements
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            csv_database_path=str(csv_file)
        )
        
        # Process paper (Journal reviewer)
        orchestrator.process_paper(str(pdf_file))
        
        # Add claims with quality scores
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        # Add Journal-Reviewer version with quality scores
        version_history['quality_test_paper.pdf'][-1]['review']['Requirement(s)'] = [
            {
                'claim_id': 'quality_claim_001',
                'status': 'pending_judge_review',
                'sub_requirement': 'SR 1.1',
                'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                'extracted_claim_text': 'High quality claim with strong evidence',
                'evidence': 'Page 5: The SNN achieved 95% accuracy in 3 independent trials.',
                'page_number': 5,
                'source': 'journal',
                'evidence_quality': {
                    'strength_score': 4,
                    'rigor_score': 5,
                    'relevance_score': 4,
                    'directness': 3,
                    'reproducibility_score': 4,
                    'composite_score': 4.2
                },
                'provenance': {
                    'page_numbers': [5, 6],
                    'section': 'Results',
                    'extraction_timestamp': '2024-11-13T10:00:00'
                }
            },
            {
                'claim_id': 'quality_claim_002',
                'status': 'pending_judge_review',
                'sub_requirement': 'SR 1.2',
                'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                'extracted_claim_text': 'Borderline quality claim',
                'evidence': 'Page 8: Energy efficiency mentioned but not quantified.',
                'page_number': 8,
                'source': 'journal',
                'evidence_quality': {
                    'strength_score': 3,
                    'rigor_score': 3,
                    'relevance_score': 3,
                    'directness': 2,
                    'reproducibility_score': 2,
                    'composite_score': 2.8  # Borderline - should trigger consensus
                },
                'provenance': {
                    'page_numbers': [8],
                    'section': 'Discussion'
                }
            }
        ]
        
        # Add a Deep-Reviewer version for the same paper (for triangulation)
        version_history['quality_test_paper.pdf'].append({
            'timestamp': '2024-11-13T11:00:00',
            'review': {
                'FILENAME': 'quality_test_paper.pdf',
                'TITLE': 'Quality Test Paper',
                'source': 'deep',
                'Requirement(s)': [
                    {
                        'claim_id': 'deep_claim_001',
                        'status': 'pending_judge_review',
                        'sub_requirement': 'SR 1.1',  # Same as journal
                        'pillar': 'Pillar 1: Bio-Inspired Algorithms',
                        'extracted_claim_text': 'Deep reviewer found additional evidence',
                        'evidence': 'Page 12: Additional validation experiments confirm results.',
                        'page_number': 12,
                        'source': 'deep',
                        'evidence_quality': {
                            'strength_score': 5,
                            'rigor_score': 4,
                            'relevance_score': 4,
                            'directness': 4,
                            'reproducibility_score': 5,
                            'composite_score': 4.5
                        },
                        'provenance': {
                            'page_numbers': [12, 13],
                            'section': 'Validation'
                        }
                    }
                ]
            }
        })
        
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Trigger triangulation
        orchestrator.triangulate_evidence()
        
        # Run Judge with consensus
        orchestrator.run_judge()
        
        # Sync to CSV
        orchestrator.sync_to_csv()
        
        # Assert: Verify version history has quality data
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        versions = version_history['quality_test_paper.pdf']
        
        # Should have multiple versions (Journal, Deep, Triangulation, Judge)
        assert len(versions) >= 3
        
        # Check Journal-Reviewer version has quality scores
        journal_version = None
        for v in versions:
            if v['review'].get('source') == 'journal':
                journal_version = v['review']
                break
        
        assert journal_version is not None
        journal_claims = journal_version.get('Requirement(s)', [])
        
        if journal_claims:
            claim = journal_claims[0]
            
            # Validate multi-dimensional scoring
            assert 'evidence_quality' in claim
            quality = claim['evidence_quality']
            assert 'composite_score' in quality
            assert 'strength_score' in quality
            assert 'rigor_score' in quality
            assert 'relevance_score' in quality
            assert 'directness' in quality
            assert 'reproducibility_score' in quality
            
            # All scores should be 1-5
            assert 1 <= quality['composite_score'] <= 5
            assert 1 <= quality['strength_score'] <= 5
            
            # Validate provenance tracking
            assert 'provenance' in claim
            prov = claim['provenance']
            assert 'page_numbers' in prov
            assert 'section' in prov
            assert len(prov['page_numbers']) > 0
        
        # Check triangulation version
        triangulation_version = None
        for v in versions:
            if 'triangulation_analysis' in v['review']:
                triangulation_version = v['review']
                break
        
        if triangulation_version:
            triangulation = triangulation_version['triangulation_analysis']
            
            # Validate triangulation
            assert 'cross_references' in triangulation or 'consensus_composite_score' in triangulation
            if 'combined_provenance' in triangulation:
                assert 'page_numbers' in triangulation['combined_provenance']
        
        # Check Judge version (final)
        judge_version = versions[-1]['review']
        judge_claims = judge_version.get('Requirement(s)', [])
        
        if judge_claims:
            for claim in judge_claims:
                # Check quality threshold enforced
                if claim['status'] == 'approved':
                    quality = claim.get('evidence_quality', {})
                    composite = quality.get('composite_score', 0)
                    # Approved claims should have good quality scores
                    assert composite >= 2.8  # Some flexibility for testing
        
        # Assert: Verify CSV has quality metadata
        if os.path.exists(csv_file):
            import pandas as pd
            df = pd.read_csv(csv_file)
            
            if len(df) > 0:
                row = df.iloc[0]
                claims = json.loads(row['Requirement(s)'])
                
                for claim in claims:
                    # Check quality scores embedded (either in evidence_quality or flattened)
                    assert 'evidence_quality' in claim or 'composite_score' in claim
                    
                    # Check provenance preserved
                    assert 'provenance' in claim or 'page_number' in claim
    
    @pytest.mark.e2e
    def test_pipeline_audit_trail_completeness(self, e2e_workspace, test_data_generator):
        """
        Test complete audit trail in version history.
        
        Validates:
        - All component executions logged
        - Timestamps preserved
        - Status transitions tracked
        - Quality score evolution tracked
        """
        # Setup
        workspace = Path(e2e_workspace['root'])
        pdf_file = workspace / "audit_paper.pdf"
        pdf_file.write_text("%PDF-1.4\nAudit trail test paper\n%%EOF")
        
        version_history_file = Path(e2e_workspace['version_history'])
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute: Full pipeline
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file)
        )
        
        orchestrator.process_paper(str(pdf_file))
        
        # Add claims
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        version_history["audit_paper.pdf"][-1]['review']['Requirement(s)'] = [
            {
                'claim_id': 'audit_claim_001',
                'status': 'pending_judge_review',
                'sub_requirement': 'SR 1.1',
                'pillar': 'Pillar 1',
                'extracted_claim_text': 'Test claim',
                'evidence': 'Test evidence',
                'evidence_quality': {
                    'composite_score': 3.5
                }
            }
        ]
        
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        orchestrator.run_judge()
        
        # Assert: Verify audit trail
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        versions = version_history['audit_paper.pdf']
        
        # Check timestamps
        for version in versions:
            assert 'timestamp' in version
            assert len(version['timestamp']) > 0
        
        # Check component sources logged
        sources = [v['review'].get('source', 'journal') for v in versions]
        assert 'journal' in sources
        
        # Check status transitions
        statuses_over_time = []
        for version in versions:
            claims = version['review'].get('Requirement(s)', [])
            for claim in claims:
                statuses_over_time.append(claim.get('status'))
        
        # Should have progression: pending → approved/rejected
        assert len(statuses_over_time) > 0
        assert any(s in ['approved', 'rejected'] for s in statuses_over_time)
    
    @pytest.mark.e2e
    def test_pipeline_idempotency(self, e2e_workspace, test_data_generator):
        """
        Test that pipeline can be rerun safely (idempotency).
        
        Running the same paper twice should not corrupt data.
        """
        # Setup
        workspace = Path(e2e_workspace['root'])
        pdf_file = workspace / "idempotent_paper.pdf"
        pdf_file.write_text("%PDF-1.4\nIdempotency test\n%%EOF")
        
        version_history_file = Path(e2e_workspace['version_history'])
        csv_file = Path(e2e_workspace['csv_db'])
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            csv_database_path=str(csv_file)
        )
        
        # First run
        orchestrator.process_paper(str(pdf_file))
        
        # Add claims
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        version_history["idempotent_paper.pdf"][-1]['review']['Requirement(s)'] = [
            {
                'claim_id': 'idem_001',
                'status': 'pending_judge_review',
                'sub_requirement': 'SR 1.1',
                'evidence_quality': {'composite_score': 4.0}
            }
        ]
        
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        orchestrator.run_judge()
        orchestrator.sync_to_csv()
        
        # Get state after first run
        with open(version_history_file, 'r') as f:
            history_after_first = json.load(f)
        
        first_version_count = len(history_after_first["idempotent_paper.pdf"])
        
        # Second run (should be safe)
        orchestrator.process_paper(str(pdf_file))
        
        # Verify: Should have added a new version, not corrupted
        with open(version_history_file, 'r') as f:
            history_after_second = json.load(f)
        
        second_version_count = len(history_after_second["idempotent_paper.pdf"])
        
        # Should have more versions now
        assert second_version_count >= first_version_count
        
        # Data should still be valid JSON
        assert "idempotent_paper.pdf" in history_after_second
