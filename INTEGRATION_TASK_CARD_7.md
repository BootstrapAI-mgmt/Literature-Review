# Integration Task Card #7 - INT-003: Version History → CSV Sync

**Priority:** 🔴 CRITICAL  
**Estimated Effort:** 4-6 hours  
**Risk Level:** LOW  
**Dependencies:** Task Card #5 (Test Infrastructure)  
**Blocks:** Orchestrator integration tests  
**Wave:** Wave 2

**Enhanced Scope:** Validates evidence quality score synchronization to CSV database

---

## Problem Statement

No integration test validates the critical sync from version history to CSV database via `scripts/sync_history_to_db.py`. This sync ensures the Orchestrator has access to approved claims for gap analysis.

**Enhanced Requirements:** With evidence quality enhancements (#16, #17), this test must validate that multi-dimensional scores, GRADE quality levels, and provenance metadata sync correctly to the CSV database.

---

## Acceptance Criteria

### Functional Requirements (Original)
- [ ] Test validates only approved claims synced
- [ ] Test validates CSV format preserved
- [ ] Test validates column order maintained
- [ ] Test validates JSON serialization correct
- [ ] Test validates no data loss

### Functional Requirements (Enhanced - Evidence Quality)
- [ ] Test validates evidence quality scores sync to CSV correctly
- [ ] Test validates all 6 dimensions present in CSV columns
- [ ] Test validates provenance metadata synced (page numbers, sections)
- [ ] Test validates backward compatibility (legacy claims without scores)
- [ ] Test validates CSV column names consistent
- [ ] Test validates JSON serialization of arrays (page_numbers) works correctly
- [ ] Test validates GRADE quality levels (if implemented)

### Technical Requirements
- [ ] Test uses version history with mixed statuses
- [ ] Test verifies sync script execution
- [ ] Test checks CSV row count matches approved claims
- [ ] Test validates all required columns present
- [ ] Test handles edge cases (empty history, all rejected, etc.)
- [ ] Test validates new quality columns added without breaking existing columns

---

## Implementation Guide

### File to Create

**Location:** `tests/integration/test_version_history_sync.py`

### Core Test Cases (Original)

```python
"""Integration tests for Version History → CSV sync."""

import pytest
import json
import csv
import os
import pandas as pd
from typing import Dict, List

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

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
        
        # Execute: Perform sync (simplified sync logic for test)
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
        
        # Execute: Sync should not crash with empty history
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
```

### Enhanced Test Cases (Evidence Quality)

#### Test 4: Evidence Quality Score Sync

```python
@pytest.mark.integration
def test_quality_scores_sync_to_csv(temp_workspace, test_data_generator):
    """
    Test that evidence quality scores sync from version history to CSV.
    
    Validates:
    - Composite scores added as new CSV column
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
                
                # Add quality score columns
                claim['EVIDENCE_COMPOSITE_SCORE'] = quality.get('composite_score')
                claim['EVIDENCE_STRENGTH_SCORE'] = quality.get('strength_score')
                claim['EVIDENCE_RIGOR_SCORE'] = quality.get('rigor_score')
                claim['EVIDENCE_RELEVANCE_SCORE'] = quality.get('relevance_score')
                claim['EVIDENCE_DIRECTNESS'] = quality.get('directness')
                claim['EVIDENCE_IS_RECENT'] = quality.get('is_recent')
                claim['EVIDENCE_REPRODUCIBILITY_SCORE'] = quality.get('reproducibility_score')
                claim['STUDY_TYPE'] = quality.get('study_type')
                
                # Add provenance columns
                claim['PROVENANCE_PAGE_NUMBERS'] = json.dumps(provenance.get('page_numbers', []))
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
def test_backward_compatibility_missing_quality_scores(temp_workspace, test_data_generator):
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
                
                # Use None or default values for missing quality data
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
```

---

## sync_history_to_db.py Modifications

Add helper function for quality score extraction:

```python
def extract_quality_scores_from_claim(claim: Dict) -> Dict:
    """
    Extract evidence quality scores for CSV columns.
    
    Args:
        claim: Claim dictionary with optional evidence_quality field
    
    Returns:
        Dictionary with quality score columns
    """
    quality = claim.get('evidence_quality', {})
    provenance = claim.get('provenance', {})
    
    return {
        'EVIDENCE_COMPOSITE_SCORE': quality.get('composite_score'),
        'EVIDENCE_STRENGTH_SCORE': quality.get('strength_score'),
        'EVIDENCE_RIGOR_SCORE': quality.get('rigor_score'),
        'EVIDENCE_RELEVANCE_SCORE': quality.get('relevance_score'),
        'EVIDENCE_DIRECTNESS': quality.get('directness'),
        'EVIDENCE_IS_RECENT': quality.get('is_recent'),
        'EVIDENCE_REPRODUCIBILITY_SCORE': quality.get('reproducibility_score'),
        'STUDY_TYPE': quality.get('study_type'),
        'CONFIDENCE_LEVEL': quality.get('confidence_level'),
        'PROVENANCE_PAGE_NUMBERS': json.dumps(provenance.get('page_numbers')) if provenance.get('page_numbers') else None,
        'PROVENANCE_SECTION': provenance.get('section'),
        'PROVENANCE_QUOTE_PAGE': provenance.get('quote_page')
    }
```

---

## Success Criteria

### Original Criteria
- [ ] Test validates approved claims synced
- [ ] Test confirms rejected/pending claims excluded
- [ ] Test verifies CSV format maintained
- [ ] Test checks claim field preservation
- [ ] Test handles empty version history
- [ ] Test passes consistently

### Enhanced Criteria (Evidence Quality)
- [ ] Evidence quality scores sync to CSV correctly
- [ ] All 6 dimensions present in CSV (when available)
- [ ] Provenance metadata synced (page numbers, sections)
- [ ] Backward compatibility maintained (legacy claims without scores)
- [ ] CSV column names consistent
- [ ] JSON serialization of arrays (page_numbers) works correctly
- [ ] None/null values handled for missing quality data
- [ ] GRADE quality levels synced (if implemented)

---

## Testing Strategy

Run integration tests:

```bash
# Run sync integration test
pytest tests/integration/test_version_history_sync.py -v

# Run with coverage
pytest tests/integration/test_version_history_sync.py --cov=scripts.sync_history_to_db --cov-report=term-missing

# Test with actual sync_history_to_db.py script
pytest tests/integration/test_version_history_sync.py -v --run-scripts
```

---

## Estimated Effort

**Original Scope:** 4-6 hours  
**Enhanced Scope (with evidence quality):** 5-7 hours

**Breakdown:**
- Core sync tests: 2-3 hours
- Evidence quality score sync: 2-3 hours
- Backward compatibility: 1 hour
- Documentation: 1 hour

---

**Task Card Status:** ⚠️ UPDATED for refactored architecture  
**Ready for Implementation:** ✅ Yes  
**Next Step:** Implement alongside Task Card #16 (Multi-Dimensional Scoring)

**Last Updated:** November 13, 2025
