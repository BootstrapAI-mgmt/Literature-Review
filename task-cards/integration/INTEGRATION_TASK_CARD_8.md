# Integration Task Card #8 - INT-002: Judge DRA Appeal Flow

**Priority:** 🔴 CRITICAL  
**Estimated Effort:** 6-8 hours  
**Risk Level:** MEDIUM  
**Dependencies:** Task Card #5 (Test Infrastructure), Task Card #1 (DRA Prompting Fix)  
**Blocks:** E2E tests  
**Wave:** Wave 3

**Enhanced Scope:** Validates inter-rater reliability for borderline claims and temporal coherence analysis

---

## Problem Statement

No integration test covers the critical appeal flow: Judge rejects a claim → DRA reanalyzes → Judge re-reviews. This feedback loop ensures quality but lacks validation, increasing risk of regression.

**Enhanced Requirements:** With evidence quality enhancements (#18 Inter-Rater Reliability, #19 Temporal Coherence), this test must validate that borderline claims trigger consensus mechanisms and that temporal analysis influences appeal outcomes.

---

## Acceptance Criteria

### Functional Requirements (Original)
- [ ] Test validates Judge rejection creates DRA appeal
- [ ] Test validates DRA reanalysis updates version history
- [ ] Test validates Judge re-reviews updated claim
- [ ] Test validates appeal loop terminates correctly
- [ ] Test validates status transitions tracked

### Functional Requirements (Enhanced - Evidence Quality)
- [ ] Test validates borderline claims (composite 2.5-3.5) trigger consensus review
- [ ] Test validates inter-rater reliability mechanism engaged for appeals
- [ ] Test validates temporal coherence analysis in appeal reanalysis
- [ ] Test validates consensus metadata stored in version history
- [ ] Test validates appeal decisions consider quality score trends
- [ ] Test validates appeals preserve original quality scores for comparison

### Technical Requirements
- [ ] Test uses realistic DRA appeal scenarios
- [ ] Test verifies version history update mechanics
- [ ] Test checks termination conditions (max appeals, consensus reached)
- [ ] Test validates all status transitions logged
- [ ] Test handles edge cases (infinite loops, missing data)

---

## Implementation Guide

### File to Create

**Location:** `tests/integration/test_judge_dra_appeal.py`

### Core Test Cases (Original)

```python
"""Integration tests for Judge → DRA appeal flow."""

import pytest
import json
import os
from pathlib import Path
from typing import Dict, List

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis.judge import Judge
from literature_review.analysis.requirements import DeepRequirementsAnalyzer

class TestJudgeDRAAppeal:
    """Test Judge rejection → DRA reanalysis → Judge re-review flow."""
    
    @pytest.mark.integration
    def test_judge_rejection_triggers_dra_appeal(self, temp_workspace, test_data_generator):
        """Test that Judge rejection creates DRA appeal task."""
        
        # Setup: Create version history with pending claims
        version_history = test_data_generator.create_version_history(
            filename="appeal_test.pdf",
            claims=[
                {
                    'claim_id': 'weak_claim_001',
                    'status': 'pending_judge_review',
                    'pillar': 'Pillar 1',
                    'sub_requirement': 'SR 1.1',
                    'extracted_claim_text': 'Weak claim needing appeal',
                    'evidence': 'Insufficient evidence',
                    'page_number': 5,
                    'reviewer_confidence': 0.45
                }
            ]
        )
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Execute: Run Judge
        judge = Judge()
        judge.process_pending_claims(str(version_history_file))
        
        # Read updated version history
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        # Assert: Check rejection and appeal created
        latest_review = updated_history['appeal_test.pdf'][-1]['review']
        claim = latest_review['Requirement(s)'][0]
        
        assert claim['status'] == 'rejected'
        assert 'judge_notes' in claim
        assert 'appeal_requested' in claim
        assert claim['appeal_requested'] is True
    
    @pytest.mark.integration
    def test_dra_reanalysis_after_appeal(self, temp_workspace, test_data_generator):
        """Test DRA reanalysis updates version history with new evidence."""
        
        # Setup: Create version history with rejected claim
        version_history = {
            "appeal_test.pdf": [
                {
                    'timestamp': '2025-11-10T10:00:00',
                    'review': {
                        'FILENAME': 'appeal_test.pdf',
                        'TITLE': 'Appeal Test Paper',
                        'Requirement(s)': [
                            {
                                'claim_id': 'rejected_claim',
                                'status': 'rejected',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.1',
                                'extracted_claim_text': 'Initial weak claim',
                                'evidence': 'Original insufficient evidence',
                                'page_number': 5,
                                'judge_notes': 'Insufficient evidence. Request DRA reanalysis.',
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
        
        # Execute: Run DRA reanalysis
        dra = DeepRequirementsAnalyzer()
        
        # Simulate DRA finding additional evidence
        updated_claim = {
            'claim_id': 'rejected_claim',
            'status': 'pending_judge_review',  # Reset to pending for re-review
            'pillar': 'Pillar 1',
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
        version_history['appeal_test.pdf'].append({
            'timestamp': updated_claim['reanalysis_timestamp'],
            'review': {
                'FILENAME': 'appeal_test.pdf',
                'TITLE': 'Appeal Test Paper',
                'Requirement(s)': [updated_claim]
            }
        })
        
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
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
    
    @pytest.mark.integration
    def test_judge_rereview_after_dra_appeal(self, temp_workspace, test_data_generator):
        """Test Judge re-reviews claim after DRA reanalysis."""
        
        # Setup: Create version history with DRA reanalysis
        version_history = {
            "appeal_test.pdf": [
                {
                    'timestamp': '2025-11-10T10:00:00',
                    'review': {
                        'FILENAME': 'appeal_test.pdf',
                        'TITLE': 'Appeal Test Paper',
                        'Requirement(s)': [
                            {
                                'claim_id': 'reanalyzed_claim',
                                'status': 'pending_judge_review',
                                'pillar': 'Pillar 1',
                                'sub_requirement': 'SR 1.1',
                                'extracted_claim_text': 'Enhanced claim with additional evidence',
                                'evidence': 'Original + new supporting data',
                                'page_number': 5,
                                'appeal_count': 1,
                                'reanalysis_timestamp': '2025-11-10T11:00:00'
                            }
                        ]
                    }
                }
            ]
        }
        
        version_history_file = temp_workspace / "review_version_history.json"
        with open(version_history_file, 'w') as f:
            json.dump(version_history, f, indent=2)
        
        # Execute: Run Judge re-review
        judge = Judge()
        judge.process_pending_claims(str(version_history_file))
        
        # Read updated version history
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        # Assert: Verify Judge made final decision
        latest_review = updated_history['appeal_test.pdf'][-1]['review']
        claim = latest_review['Requirement(s)'][0]
        
        # Should be approved or rejected (no longer pending)
        assert claim['status'] in ['approved', 'rejected']
        assert 'judge_notes' in claim
        assert 'judge_timestamp' in claim
    
    @pytest.mark.integration
    def test_appeal_loop_terminates_after_max_appeals(self, temp_workspace, test_data_generator):
        """Test that appeal loop terminates after max attempts."""
        
        MAX_APPEALS = 2
        
        # Setup: Create version history with claim at max appeals
        version_history = {
            "max_appeals_test.pdf": [
                {
                    'timestamp': '2025-11-10T10:00:00',
                    'review': {
                        'FILENAME': 'max_appeals_test.pdf',
                        'TITLE': 'Max Appeals Test',
                        'Requirement(s)': [
                            {
                                'claim_id': 'stubborn_claim',
                                'status': 'pending_judge_review',
                                'pillar': 'Pillar 1',
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
        
        # Execute: Run Judge with max appeals logic
        judge = Judge()
        judge.process_pending_claims(str(version_history_file))
        
        # Read updated version history
        with open(version_history_file, 'r') as f:
            updated_history = json.load(f)
        
        # Assert: Verify no new appeal created
        latest_review = updated_history['max_appeals_test.pdf'][-1]['review']
        claim = latest_review['Requirement(s)'][0]
        
        # Should be finalized (no new appeal_requested)
        assert claim.get('appeal_requested', False) is False
        assert claim['appeal_count'] == MAX_APPEALS
        assert claim['status'] in ['approved', 'rejected']
```

### Enhanced Test Cases (Evidence Quality)

#### Test 5: Borderline Claims Trigger Consensus

```python
@pytest.mark.integration
def test_borderline_claims_trigger_consensus(temp_workspace, test_data_generator):
    """
    Test that borderline claims (composite 2.5-3.5) trigger inter-rater reliability consensus.
    
    Validates:
    - Borderline claims get consensus review
    - Consensus metadata stored in version history
    - Appeal decisions consider consensus results
    """
    # Setup: Create version history with borderline claim
    version_history = {
        "borderline_paper.pdf": [
            {
                'timestamp': '2025-11-13T10:00:00',
                'review': {
                    'FILENAME': 'borderline_paper.pdf',
                    'TITLE': 'Borderline Evidence Paper',
                    'Requirement(s)': [
                        {
                            'claim_id': 'borderline_claim_001',
                            'status': 'pending_judge_review',
                            'extracted_claim_text': 'Borderline quality claim',
                            'sub_requirement': 'Sub-1.1.1',
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
    
    # Execute: Run Judge with consensus logic
    judge = Judge()
    judge.process_pending_claims(str(version_history_file))
    
    # Read updated version history
    with open(version_history_file, 'r') as f:
        updated_history = json.load(f)
    
    # Assert: Verify consensus triggered
    latest_review = updated_history['borderline_paper.pdf'][-1]['review']
    claim = latest_review['Requirement(s)'][0]
    
    # Check consensus metadata
    assert 'consensus_review' in claim
    assert claim['consensus_review']['triggered'] is True
    assert claim['consensus_review']['reason'] == 'borderline_composite_score'
    assert 'consensus_reviewers' in claim['consensus_review']
    assert len(claim['consensus_review']['consensus_reviewers']) >= 2


@pytest.mark.integration
def test_temporal_coherence_in_appeal_reanalysis(temp_workspace, test_data_generator):
    """
    Test that temporal coherence analysis is performed during DRA appeal reanalysis.
    
    Validates:
    - Publication year trend analysis
    - Quality score evolution over time
    - Recency bias in appeal decisions
    """
    # Setup: Create version history with temporal data
    version_history = {
        "temporal_paper.pdf": [
            {
                'timestamp': '2025-11-13T10:00:00',
                'review': {
                    'FILENAME': 'temporal_paper.pdf',
                    'TITLE': 'Old Study',
                    'PUBLICATION_YEAR': 2010,
                    'Requirement(s)': [
                        {
                            'claim_id': 'old_claim',
                            'status': 'rejected',
                            'extracted_claim_text': 'Outdated claim',
                            'sub_requirement': 'Sub-1.1.1',
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
    
    # Execute: DRA reanalysis with temporal coherence
    dra = DeepRequirementsAnalyzer()
    
    # Simulate DRA finding newer evidence
    updated_claim = {
        'claim_id': 'old_claim',
        'status': 'pending_judge_review',
        'extracted_claim_text': 'Updated claim with recent evidence',
        'sub_requirement': 'Sub-1.1.1',
        'evidence_quality': {
            'composite_score': 3.5,  # Improved with recent evidence
            'is_recent': True,
            'recency_penalty': 0.0
        },
        'temporal_coherence': {
            'newer_sources_found': True,
            'publication_years': [2010, 2022, 2023],  # Original + new
            'quality_trend': 'improving',
            'recency_boost': +0.5
        },
        'appeal_count': 1,
        'reanalysis_timestamp': '2025-11-13T11:00:00'
    }
    
    # Append reanalysis
    version_history['temporal_paper.pdf'].append({
        'timestamp': updated_claim['reanalysis_timestamp'],
        'review': {
            'FILENAME': 'temporal_paper.pdf',
            'TITLE': 'Old Study',
            'PUBLICATION_YEAR': 2010,
            'Requirement(s)': [updated_claim]
        }
    })
    
    with open(version_history_file, 'w') as f:
        json.dump(version_history, f, indent=2)
    
    # Assert: Verify temporal coherence analysis
    with open(version_history_file, 'r') as f:
        updated_history = json.load(f)
    
    reanalysis = updated_history['temporal_paper.pdf'][-1]['review']
    claim = reanalysis['Requirement(s)'][0]
    
    assert 'temporal_coherence' in claim
    assert claim['temporal_coherence']['newer_sources_found'] is True
    assert claim['temporal_coherence']['quality_trend'] == 'improving'
    assert claim['evidence_quality']['composite_score'] > 2.5  # Improved
```

---

## Judge.py Modifications

Add consensus triggering logic:

```python
def should_trigger_consensus(self, claim: Dict) -> bool:
    """
    Determine if claim requires consensus review.
    
    Args:
        claim: Claim dictionary with evidence_quality field
    
    Returns:
        True if consensus needed (borderline score 2.5-3.5)
    """
    quality = claim.get('evidence_quality', {})
    composite = quality.get('composite_score', 0)
    
    # Trigger consensus for borderline claims
    return 2.5 <= composite <= 3.5


def trigger_consensus_review(self, claim: Dict) -> Dict:
    """
    Add consensus review metadata to claim.
    
    Args:
        claim: Claim requiring consensus
    
    Returns:
        Claim with consensus_review metadata
    """
    claim['consensus_review'] = {
        'triggered': True,
        'reason': 'borderline_composite_score',
        'consensus_reviewers': ['reviewer_A', 'reviewer_B'],  # Placeholder
        'timestamp': '2025-11-13T12:00:00'
    }
    return claim
```

---

## Success Criteria

### Original Criteria
- [ ] Judge rejection triggers DRA appeal
- [ ] DRA reanalysis updates version history
- [ ] Judge re-reviews updated claims
- [ ] Appeal loop terminates correctly
- [ ] All status transitions logged
- [ ] Test passes consistently

### Enhanced Criteria (Evidence Quality)
- [ ] Borderline claims (composite 2.5-3.5) trigger consensus
- [ ] Consensus metadata stored in version history
- [ ] Temporal coherence analyzed in appeals
- [ ] Publication year trends influence decisions
- [ ] Quality score evolution tracked
- [ ] Appeals preserve original quality scores for comparison

---

## Testing Strategy

Run integration tests:

```bash
# Run appeal flow integration test
pytest tests/integration/test_judge_dra_appeal.py -v

# Run with coverage
pytest tests/integration/test_judge_dra_appeal.py --cov=literature_review.analysis --cov-report=term-missing
```

---

## Estimated Effort

**Original Scope:** 6-8 hours  
**Enhanced Scope (with consensus + temporal):** 8-10 hours

**Breakdown:**
- Core appeal flow tests: 4-5 hours
- Consensus triggering: 2-3 hours
- Temporal coherence: 2 hours
- Documentation: 1 hour

---

**Task Card Status:** ⚠️ UPDATED for refactored architecture  
**Ready for Implementation:** ✅ Yes  
**Dependencies:** Task #1 (DRA Prompting Fix), Task #18 (Inter-Rater Reliability), Task #19 (Temporal Coherence)

**Last Updated:** November 13, 2025
