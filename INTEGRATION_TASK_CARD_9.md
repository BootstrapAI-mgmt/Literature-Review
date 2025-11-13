# Integration Task Card #9 - INT-004 & INT-005: Orchestrator Integration Tests

**Priority:** 🟠 HIGH  
**Estimated Effort:** 6-8 hours  
**Risk Level:** MEDIUM  
**Dependencies:** Task Cards #6, #7, #8 (Component Integration Tests)  
**Blocks:** E2E tests (#10, #11)  
**Wave:** Wave 3

**Enhanced Scope:** Validates evidence triangulation across multi-reviewer convergence

---

## Problem Statement

The Orchestrator coordinates Journal-Reviewer, Deep-Reviewer, Judge, and CSV sync in a complex workflow. No integration test validates this orchestration end-to-end at the component level, creating risk of coordination failures.

**Enhanced Requirements:** With evidence quality enhancements (#20 Evidence Triangulation), this test must validate that the Orchestrator correctly aggregates evidence from multiple reviewers, computes consensus scores, and handles cross-referencing between reviewers.

---

## Acceptance Criteria

### Functional Requirements (Original)
- [ ] Test validates Orchestrator calls all components in sequence
- [ ] Test validates component outputs passed correctly
- [ ] Test validates version history updated at each stage
- [ ] Test validates CSV sync triggered after approval
- [ ] Test validates error handling between components

### Functional Requirements (Enhanced - Evidence Quality)
- [ ] Test validates evidence triangulation across Journal + Deep reviewers
- [ ] Test validates cross-referencing between reviewer claims
- [ ] Test validates consensus score computation from multiple sources
- [ ] Test validates conflicting evidence resolution
- [ ] Test validates triangulation metadata stored in version history
- [ ] Test validates orchestrator aggregates quality scores from both reviewers

### Technical Requirements
- [ ] Test uses realistic multi-component workflow
- [ ] Test verifies component handoffs
- [ ] Test checks version history incremental updates
- [ ] Test validates idempotency (can rerun safely)
- [ ] Test handles partial failures gracefully

---

## Implementation Guide

### File to Create

**Location:** `tests/integration/test_orchestrator_integration.py`

### Core Test Cases (Original)

```python
"""Integration tests for Orchestrator component coordination."""

import pytest
import json
import os
from pathlib import Path
from typing import Dict, List

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.orchestrator import Orchestrator
from literature_review.reviewers.journal_reviewer import JournalReviewer
from literature_review.reviewers.deep_reviewer import DeepReviewer
from literature_review.analysis.judge import Judge

class TestOrchestratorIntegration:
    """Test Orchestrator coordination of all components."""
    
    @pytest.mark.integration
    def test_orchestrator_coordinates_full_workflow(self, temp_workspace, test_data_generator):
        """Test Orchestrator runs Journal → Deep → Judge → CSV sync."""
        
        # Setup: Create input PDF and empty databases
        pdf_file = temp_workspace / "test_paper.pdf"
        test_data_generator.create_dummy_pdf(pdf_file)
        
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
        
        # Check multiple versions (Journal, Deep, Judge)
        versions = version_history["test_paper.pdf"]
        assert len(versions) >= 2  # At least Journal + Judge
        
        # Verify component sequence
        sources = [v['review'].get('source', 'journal') for v in versions]
        assert 'journal' in sources  # Journal-Reviewer ran
        
        # Verify final status updated
        latest = versions[-1]['review']
        claims = latest.get('Requirement(s)', [])
        
        # At least one claim should have final status
        statuses = [c.get('status') for c in claims]
        assert any(s in ['approved', 'rejected'] for s in statuses)
    
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
        
        try:
            orchestrator.run_judge()
            assert False, "Should have raised exception"
        except (json.JSONDecodeError, ValueError) as e:
            # Expected error
            assert True
```

### Enhanced Test Cases (Evidence Quality)

#### Test 5: Evidence Triangulation Across Reviewers

```python
@pytest.mark.integration
def test_orchestrator_triangulates_evidence_across_reviewers(temp_workspace, test_data_generator):
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
def test_orchestrator_resolves_conflicting_evidence(temp_workspace, test_data_generator):
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
```

---

## Orchestrator.py Modifications

Add triangulation methods:

```python
def triangulate_evidence(self):
    """
    Perform evidence triangulation across Journal and Deep reviewers.
    
    Aggregates claims from multiple reviewers for the same sub-requirements,
    computes consensus scores, and detects conflicts.
    """
    with open(self.version_history_path, 'r') as f:
        version_history = json.load(f)
    
    for filename, versions in version_history.items():
        # Group claims by sub_requirement
        claims_by_subreq = {}
        
        for version in versions:
            claims = version['review'].get('Requirement(s)', [])
            for claim in claims:
                subreq = claim.get('sub_requirement')
                if subreq:
                    if subreq not in claims_by_subreq:
                        claims_by_subreq[subreq] = []
                    claims_by_subreq[subreq].append(claim)
        
        # Triangulate claims with multiple sources
        triangulation_data = {
            'cross_references': [],
            'conflicts_detected': False,
            'conflict_resolution': {}
        }
        
        for subreq, claims in claims_by_subreq.items():
            if len(claims) > 1:
                # Multiple reviewers covered same sub-req
                scores = [c.get('evidence_quality', {}).get('composite_score', 0) for c in claims]
                
                # Check for conflict (significant score difference)
                if max(scores) - min(scores) > 1.5:
                    triangulation_data['conflicts_detected'] = True
                    triangulation_data['conflict_resolution'] = {
                        'sub_requirement': subreq,
                        'strategy': 'take_higher_score',
                        'resolved_composite_score': max(scores)
                    }
                
                # Compute consensus
                triangulation_data['consensus_composite_score'] = sum(scores) / len(scores)
                
                # Combine provenance
                all_pages = []
                for c in claims:
                    pages = c.get('provenance', {}).get('page_numbers', [])
                    all_pages.extend(pages)
                
                triangulation_data['combined_provenance'] = {
                    'page_numbers': list(set(all_pages))
                }
        
        # Append triangulation analysis to version history
        versions.append({
            'timestamp': '2025-11-13T12:00:00',
            'review': {
                'FILENAME': filename,
                'TITLE': versions[-1]['review'].get('TITLE'),
                'triangulation_analysis': triangulation_data
            }
        })
    
    # Save updated version history
    with open(self.version_history_path, 'w') as f:
        json.dump(version_history, f, indent=2)
```

---

## Success Criteria

### Original Criteria
- [ ] Orchestrator coordinates all components
- [ ] Component outputs passed correctly
- [ ] Version history updated incrementally
- [ ] CSV sync triggered after approval
- [ ] Error handling works
- [ ] Test passes consistently

### Enhanced Criteria (Evidence Quality)
- [ ] Evidence triangulation performed across reviewers
- [ ] Cross-references detected and stored
- [ ] Consensus scores computed correctly
- [ ] Conflicting evidence detected
- [ ] Conflict resolution strategy applied
- [ ] Triangulation metadata stored in version history

---

## Testing Strategy

Run integration tests:

```bash
# Run orchestrator integration tests
pytest tests/integration/test_orchestrator_integration.py -v

# Run with coverage
pytest tests/integration/test_orchestrator_integration.py --cov=literature_review.orchestrator --cov-report=term-missing
```

---

## Estimated Effort

**Original Scope:** 6-8 hours  
**Enhanced Scope (with triangulation):** 8-10 hours

**Breakdown:**
- Core orchestration tests: 4-5 hours
- Evidence triangulation: 3-4 hours
- Conflict resolution: 1-2 hours
- Documentation: 1 hour

---

**Task Card Status:** ⚠️ UPDATED for refactored architecture  
**Ready for Implementation:** ✅ Yes  
**Dependencies:** Task #20 (Evidence Triangulation), Tasks #6-8 (Component tests)

**Last Updated:** November 13, 2025
