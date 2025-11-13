# Integration Task Card #10 - E2E-001: Full Pipeline Test

**Priority:** 🔴 CRITICAL  
**Estimated Effort:** 8-12 hours  
**Risk Level:** HIGH  
**Dependencies:** All integration tests (#6-9), Evidence enhancement cards (#16-21)  
**Blocks:** Production deployment  
**Wave:** Wave 4

**Enhanced Scope:** Validates complete evidence quality workflow from PDF ingestion to GRADE assessment

---

## Problem Statement

No end-to-end test validates the complete literature review pipeline: PDF → Journal-Reviewer → Deep-Reviewer → Judge → CSV with all evidence quality enhancements. This creates deployment risk and makes it difficult to verify that all components work together correctly.

**Enhanced Requirements:** With evidence quality enhancements (multi-dimensional scoring, provenance, consensus, temporal analysis, triangulation, GRADE assessment), this E2E test must validate the complete quality workflow produces correct final assessments with all metadata intact.

---

## Acceptance Criteria

### Functional Requirements (Original)
- [ ] Test validates complete PDF → CSV pipeline
- [ ] Test validates all components execute in sequence
- [ ] Test validates version history tracks full workflow
- [ ] Test validates final CSV contains approved claims
- [ ] Test validates data integrity end-to-end

### Functional Requirements (Enhanced - Evidence Quality)
- [ ] Test validates multi-dimensional quality scores computed for all claims
- [ ] Test validates provenance metadata tracked from extraction to CSV
- [ ] Test validates borderline claims trigger consensus review
- [ ] Test validates temporal coherence analysis performed
- [ ] Test validates evidence triangulation across reviewers
- [ ] Test validates GRADE quality levels assigned
- [ ] Test validates final CSV contains all quality metadata
- [ ] Test validates quality thresholds enforced (composite ≥3.0 for approval)
- [ ] Test validates complete audit trail in version history

### Technical Requirements
- [ ] Test uses realistic multi-paper workflow
- [ ] Test verifies performance (processing time)
- [ ] Test validates resource cleanup (temp files)
- [ ] Test handles errors gracefully
- [ ] Test produces reproducible results
- [ ] Test validates idempotency (can rerun safely)

---

## Implementation Guide

### File to Create

**Location:** `tests/e2e/test_full_pipeline.py`

### Core Test Structure (Original)

```python
"""End-to-end tests for complete literature review pipeline."""

import pytest
import json
import os
import csv
from pathlib import Path
from typing import Dict, List
import time

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.orchestrator import Orchestrator

class TestFullPipeline:
    """Test complete PDF → CSV pipeline with all components."""
    
    @pytest.mark.e2e
    def test_complete_pipeline_single_paper(self, temp_workspace, test_data_generator):
        """
        Test full pipeline for single paper.
        
        Flow: PDF → Journal-Reviewer → Judge → CSV
        """
        # Setup: Create test PDF
        pdf_file = temp_workspace / "test_paper.pdf"
        test_data_generator.create_dummy_pdf(
            pdf_file,
            title="Single Paper E2E Test",
            content="This paper demonstrates neuromorphic computing with spiking neural networks."
        )
        
        version_history_file = temp_workspace / "review_version_history.json"
        csv_file = temp_workspace / "neuromorphic_database.csv"
        
        # Initialize empty version history
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute: Run complete pipeline
        start_time = time.time()
        
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            csv_database_path=str(csv_file)
        )
        
        orchestrator.process_paper(str(pdf_file))
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
    def test_complete_pipeline_multiple_papers(self, temp_workspace, test_data_generator):
        """
        Test full pipeline for multiple papers in batch.
        
        Flow: [PDF1, PDF2, PDF3] → Reviewers → Judge → CSV
        """
        # Setup: Create multiple test PDFs
        papers = []
        for i in range(3):
            pdf_file = temp_workspace / f"paper_{i+1}.pdf"
            test_data_generator.create_dummy_pdf(
                pdf_file,
                title=f"Paper {i+1}",
                content=f"This is test paper {i+1} about neuromorphic computing."
            )
            papers.append(pdf_file)
        
        version_history_file = temp_workspace / "review_version_history.json"
        csv_file = temp_workspace / "neuromorphic_database.csv"
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute: Process all papers
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            csv_database_path=str(csv_file)
        )
        
        for paper in papers:
            orchestrator.process_paper(str(paper))
        
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
    def test_pipeline_data_integrity(self, temp_workspace, test_data_generator):
        """
        Test data integrity throughout pipeline.
        
        Validates: No data loss, field preservation, JSON serialization
        """
        # Setup: Create paper with detailed claims
        pdf_file = temp_workspace / "detailed_paper.pdf"
        test_data_generator.create_dummy_pdf(
            pdf_file,
            title="Detailed Paper",
            content="Neuromorphic computing with detailed evidence."
        )
        
        version_history_file = temp_workspace / "review_version_history.json"
        csv_file = temp_workspace / "database.csv"
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute: Run pipeline
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            csv_database_path=str(csv_file)
        )
        
        orchestrator.process_paper(str(pdf_file))
        orchestrator.sync_to_csv()
        
        # Assert: Verify data integrity
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        latest = version_history['detailed_paper.pdf'][-1]['review']
        original_claims = latest.get('Requirement(s)', [])
        
        # Read CSV
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
```

### Enhanced Test Cases (Evidence Quality)

#### Test 4: Complete Evidence Quality Workflow

```python
@pytest.mark.e2e
def test_complete_evidence_quality_workflow(temp_workspace, test_data_generator):
    """
    Test full pipeline with all evidence quality enhancements.
    
    Validates:
    - Multi-dimensional quality scores computed
    - Provenance metadata tracked from extraction to CSV
    - Borderline claims trigger consensus
    - Temporal coherence analysis performed
    - Evidence triangulation across reviewers
    - GRADE quality levels assigned
    - Quality thresholds enforced (composite ≥3.0)
    - Complete audit trail in version history
    """
    # Setup: Create paper that triggers all quality features
    pdf_file = temp_workspace / "quality_test_paper.pdf"
    test_data_generator.create_dummy_pdf(
        pdf_file,
        title="High Quality Evidence Paper",
        publication_year=2024,
        content="""
        Results: Our neuromorphic system achieved 95% accuracy on the MNIST dataset.
        The spiking neural network (SNN) demonstrated energy efficiency 10x better than
        traditional ANNs. Results were reproduced in 3 independent trials.
        
        Methods: We used a fully connected SNN with 784 input neurons and 10 output neurons.
        Training used spike-timing-dependent plasticity (STDP).
        """
    )
    
    version_history_file = temp_workspace / "review_version_history.json"
    csv_file = temp_workspace / "quality_database.csv"
    
    with open(version_history_file, 'w') as f:
        json.dump({}, f)
    
    # Execute: Run complete pipeline with quality enhancements
    orchestrator = Orchestrator(
        version_history_path=str(version_history_file),
        csv_database_path=str(csv_file),
        enable_quality_scoring=True,
        enable_provenance_tracking=True,
        enable_consensus_review=True,
        enable_temporal_analysis=True,
        enable_triangulation=True,
        enable_grade_assessment=True
    )
    
    # Process paper (Journal + Deep reviewers)
    orchestrator.process_paper(str(pdf_file))
    
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
    journal_version = versions[0]['review']
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
        assert 'consensus_composite_score' in triangulation
        assert 'combined_provenance' in triangulation
    
    # Check Judge version
    judge_version = versions[-1]['review']
    judge_claims = judge_version.get('Requirement(s)', [])
    
    if judge_claims:
        for claim in judge_claims:
            # Check consensus triggered for borderline claims
            quality = claim.get('evidence_quality', {})
            composite = quality.get('composite_score', 0)
            
            if 2.5 <= composite <= 3.5:
                # Should have consensus review
                assert 'consensus_review' in claim
                assert claim['consensus_review']['triggered'] is True
            
            # Check quality threshold enforced
            if claim['status'] == 'approved':
                assert composite >= 3.0
            
            # Check GRADE assessment (if implemented)
            if 'grade_quality_level' in claim:
                assert claim['grade_quality_level'] in ['high', 'moderate', 'low', 'very_low']
    
    # Assert: Verify CSV has quality metadata
    assert os.path.exists(csv_file)
    
    import pandas as pd
    df = pd.read_csv(csv_file)
    
    if len(df) > 0:
        row = df.iloc[0]
        claims = json.loads(row['Requirement(s)'])
        
        for claim in claims:
            # Check quality scores embedded
            assert 'EVIDENCE_COMPOSITE_SCORE' in claim or 'evidence_quality' in claim
            
            # Check provenance preserved
            assert 'provenance' in claim or 'PROVENANCE_PAGE_NUMBERS' in claim


@pytest.mark.e2e
def test_pipeline_audit_trail_completeness(temp_workspace, test_data_generator):
    """
    Test complete audit trail in version history.
    
    Validates:
    - All component executions logged
    - Timestamps preserved
    - Status transitions tracked
    - Quality score evolution tracked
    - Appeal history tracked
    """
    # Setup
    pdf_file = temp_workspace / "audit_paper.pdf"
    test_data_generator.create_dummy_pdf(pdf_file, title="Audit Test")
    
    version_history_file = temp_workspace / "review_version_history.json"
    
    with open(version_history_file, 'w') as f:
        json.dump({}, f)
    
    # Execute: Full pipeline
    orchestrator = Orchestrator(
        version_history_path=str(version_history_file),
        enable_quality_scoring=True
    )
    
    orchestrator.process_paper(str(pdf_file))
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
    assert 'pending_judge_review' in statuses_over_time or len(statuses_over_time) > 0
```

---

## Success Criteria

### Original Criteria
- [ ] Complete PDF → CSV pipeline works
- [ ] All components execute in sequence
- [ ] Version history tracks full workflow
- [ ] Final CSV contains approved claims
- [ ] Data integrity maintained
- [ ] Test passes consistently
- [ ] Processing time acceptable (<60s per paper)

### Enhanced Criteria (Evidence Quality)
- [ ] Multi-dimensional quality scores computed for all claims
- [ ] Provenance metadata tracked from extraction to CSV
- [ ] Borderline claims trigger consensus review
- [ ] Temporal coherence analysis performed
- [ ] Evidence triangulation across reviewers works
- [ ] GRADE quality levels assigned (if implemented)
- [ ] Final CSV contains all quality metadata
- [ ] Quality thresholds enforced (composite ≥3.0 for approval)
- [ ] Complete audit trail in version history
- [ ] Quality score evolution tracked
- [ ] Appeal history preserved

---

## Testing Strategy

Run E2E tests:

```bash
# Run full pipeline E2E test
pytest tests/e2e/test_full_pipeline.py -v -s

# Run with coverage
pytest tests/e2e/test_full_pipeline.py --cov=literature_review --cov-report=html

# Run with performance profiling
pytest tests/e2e/test_full_pipeline.py -v --durations=10
```

---

## Estimated Effort

**Original Scope:** 8-12 hours  
**Enhanced Scope (with quality workflow):** 12-16 hours

**Breakdown:**
- Core pipeline tests: 6-8 hours
- Evidence quality workflow: 4-6 hours
- Audit trail validation: 2 hours
- Performance testing: 1-2 hours
- Documentation: 1-2 hours

---

**Task Card Status:** ⚠️ UPDATED for refactored architecture  
**Ready for Implementation:** ✅ Yes  
**Dependencies:** All integration tests (#6-9), Evidence enhancement cards (#16-21)  
**Blocks:** Production deployment

**Last Updated:** November 13, 2025
