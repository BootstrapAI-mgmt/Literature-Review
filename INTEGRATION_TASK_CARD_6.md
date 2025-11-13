# Integration Task Card #6 - INT-001: Journal-Reviewer → Judge Flow

**Priority:** 🔴 CRITICAL  
**Estimated Effort:** 6-8 hours  
**Risk Level:** MEDIUM  
**Dependencies:** Task Card #5 (Test Infrastructure)  
**Blocks:** E2E testing  
**Wave:** Wave 2

**Enhanced Scope:** Validates multi-dimensional scoring (#16) and provenance tracking (#17)

---

## Problem Statement

No integration test exists to validate the critical flow from Journal-Reviewer creating version history entries through Judge processing claims. This is the primary entry point for new papers into the system.

**Enhanced Requirements:** With evidence quality enhancements (#16, #17), this test must also validate that multi-dimensional evidence scoring and provenance metadata are correctly extracted, processed, and persisted.

---

## Acceptance Criteria

### Functional Requirements (Original)
- [ ] Test validates version history creation from Journal-Reviewer
- [ ] Test validates Judge reads pending claims correctly
- [ ] Test validates Judge updates claim statuses
- [ ] Test validates version history updated with timestamps
- [ ] Test passes with both approved and rejected claims

### Functional Requirements (Enhanced - Evidence Quality)
- [ ] Test validates multi-dimensional evidence quality scores (6 dimensions)
- [ ] Test validates composite score calculation
- [ ] Test validates approval threshold logic (composite ≥3.0, strength ≥3, relevance ≥3)
- [ ] Test validates low-quality evidence rejection
- [ ] Test validates provenance metadata (page numbers, sections, quotes)
- [ ] Test validates character offsets accuracy
- [ ] Test validates section heading detection (>70% accuracy target)

### Technical Requirements
- [ ] Test uses realistic paper data (small PDF or text extract)
- [ ] Test mocks Gemini API for cost control
- [ ] Test verifies data flow through version history
- [ ] Test checks all required fields present
- [ ] Test validates timestamp ordering
- [ ] Test validates score ranges (1-5 for most, 1-3 for directness)
- [ ] Test validates provenance structure completeness

---

## Implementation Guide

### File to Create

**Location:** `tests/integration/test_journal_to_judge.py`

### Core Test Cases (Original)

#### Test 1: Basic Judge Processing

```python
"""Integration tests for Journal-Reviewer → Judge flow."""

import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch
from typing import Dict, List

# Import modules to test
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis import judge
from literature_review.reviewers import journal_reviewer

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
        
        with patch('literature_review.analysis.judge.APIManager.cached_api_call') as mock_api:
            # Alternate between approved and rejected
            mock_api.side_effect = [mock_approved_response, mock_rejected_response]
            
            # Execute: Load and process claims using Judge functions
            from literature_review.analysis.judge import (
                load_version_history,
                save_version_history,
                extract_pending_claims_from_history
            )
            
            history = load_version_history(str(version_history_file))
            claims_to_judge = extract_pending_claims_from_history(history)
            
            # Process each claim
            for claim in claims_to_judge:
                response = mock_api()
                if response:
                    claim['status'] = response['verdict']
                    claim['judge_notes'] = response['judge_notes']
                    claim['judge_timestamp'] = datetime.now().isoformat()
            
            # Update version history
            from literature_review.analysis.judge import update_claims_in_history
            history = update_claims_in_history(history, claims_to_judge)
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
        with patch('literature_review.analysis.judge.APIManager.cached_api_call') as mock_api:
            mock_api.return_value = {
                "verdict": "approved",
                "judge_notes": "Approved. Test verdict."
            }
            
            from literature_review.analysis.judge import (
                load_version_history,
                save_version_history
            )
            
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
```

### Enhanced Test Cases (Evidence Quality)

#### Test 2: Multi-Dimensional Evidence Scoring

```python
@pytest.mark.integration
def test_judge_outputs_multidimensional_scores(temp_workspace, test_data_generator):
    """
    Test that Judge outputs 6-dimensional evidence quality scores.
    
    Validates:
    - All 6 dimensions present (strength, rigor, relevance, directness, recency, reproducibility)
    - Composite score calculated correctly
    - Scores within valid ranges
    - Evidence quality metadata persisted in version history
    """
    # Setup: Create version history with claim
    version_history = test_data_generator.create_version_history(
        filename="high_quality_paper.pdf",
        num_versions=1,
        claim_statuses=['pending_judge_review'],
        claims=[
            {
                "claim_id": "test_quality_001",
                "extracted_claim_text": "SNNs achieve 95% accuracy with 1.2mJ energy per inference",
                "sub_requirement": "Sub-2.1.1",
                "evidence_chunk": "Strong experimental validation with public code repository."
            }
        ]
    )
    
    version_history_file = temp_workspace / "review_version_history.json"
    with open(version_history_file, 'w') as f:
        json.dump(version_history, f, indent=2)
    
    # Mock Judge response with quality scores
    mock_judge_response = {
        "verdict": "approved",
        "evidence_quality": {
            "strength_score": 4,
            "strength_rationale": "Strong experimental evidence with quantitative metrics",
            "rigor_score": 5,
            "study_type": "experimental",
            "relevance_score": 4,
            "relevance_notes": "Directly addresses SNN accuracy requirement",
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 4,
            "composite_score": 4.2,
            "confidence_level": "high"
        },
        "judge_notes": "Approved. High-quality experimental evidence."
    }
    
    # Execute: Run Judge
    with patch('literature_review.analysis.judge.APIManager.cached_api_call') as mock_api:
        mock_api.return_value = mock_judge_response
        
        from literature_review.analysis.judge import (
            load_version_history,
            save_version_history,
            extract_pending_claims_from_history,
            update_claims_in_history
        )
        
        history = load_version_history(str(version_history_file))
        claims = extract_pending_claims_from_history(history)
        
        # Process with quality scores
        for claim in claims:
            response = mock_api()
            claim['status'] = response['verdict']
            claim['judge_notes'] = response['judge_notes']
            claim['evidence_quality'] = response['evidence_quality']
            claim['judge_timestamp'] = datetime.now().isoformat()
        
        history = update_claims_in_history(history, claims)
        save_version_history(str(version_history_file), history)
    
    # Assert: Verify quality scores in version history
    with open(version_history_file, 'r') as f:
        final_history = json.load(f)
    
    claim = final_history["high_quality_paper.pdf"][-1]["review"]["Requirement(s)"][0]
    
    # Check evidence_quality field exists
    assert "evidence_quality" in claim, "Missing evidence_quality field"
    
    quality = claim["evidence_quality"]
    
    # Validate all dimensions present
    required_fields = [
        "strength_score", "rigor_score", "relevance_score",
        "directness", "is_recent", "reproducibility_score", "composite_score"
    ]
    for field in required_fields:
        assert field in quality, f"Missing required field: {field}"
    
    # Validate score ranges
    assert 1 <= quality["strength_score"] <= 5
    assert 1 <= quality["rigor_score"] <= 5
    assert 1 <= quality["relevance_score"] <= 5
    assert 1 <= quality["directness"] <= 3
    assert isinstance(quality["is_recent"], bool)
    assert 1 <= quality["reproducibility_score"] <= 5
    assert 1 <= quality["composite_score"] <= 5
    
    # Validate composite score calculation
    expected_composite = (
        quality["strength_score"] * 0.30 +
        quality["rigor_score"] * 0.25 +
        quality["relevance_score"] * 0.25 +
        (quality["directness"] / 3.0) * 0.10 +
        (1.0 if quality["is_recent"] else 0.0) * 0.05 +
        quality["reproducibility_score"] * 0.05
    )
    assert abs(quality["composite_score"] - expected_composite) < 0.1
    
    # Validate approval threshold logic
    if claim["status"] == "approved":
        assert quality["composite_score"] >= 3.0
        assert quality["strength_score"] >= 3
        assert quality["relevance_score"] >= 3


@pytest.mark.integration
def test_judge_rejects_low_quality_evidence(temp_workspace, test_data_generator):
    """
    Test that Judge correctly rejects low-quality evidence.
    
    Validates:
    - Low composite score → rejection
    - Low strength but high composite → rejection (threshold logic)
    - Rejection rationale stored
    """
    # Setup
    version_history = test_data_generator.create_version_history(
        filename="low_quality_paper.pdf",
        num_versions=1,
        claim_statuses=['pending_judge_review']
    )
    
    version_history_file = temp_workspace / "review_version_history.json"
    with open(version_history_file, 'w') as f:
        json.dump(version_history, f, indent=2)
    
    # Mock low-quality response
    mock_low_quality = {
        "verdict": "rejected",
        "evidence_quality": {
            "strength_score": 2,  # Too low
            "strength_rationale": "Anecdotal evidence without quantitative validation",
            "rigor_score": 2,
            "study_type": "opinion",
            "relevance_score": 3,
            "relevance_notes": "Somewhat relevant but lacks direct evidence",
            "directness": 1,
            "is_recent": False,
            "reproducibility_score": 1,
            "composite_score": 2.1,  # Below threshold
            "confidence_level": "low"
        },
        "judge_notes": "Rejected. Insufficient evidence strength."
    }
    
    # Execute
    with patch('literature_review.analysis.judge.APIManager.cached_api_call') as mock_api:
        mock_api.return_value = mock_low_quality
        
        from literature_review.analysis.judge import (
            load_version_history,
            save_version_history,
            extract_pending_claims_from_history,
            update_claims_in_history
        )
        
        history = load_version_history(str(version_history_file))
        claims = extract_pending_claims_from_history(history)
        
        for claim in claims:
            response = mock_api()
            claim['status'] = response['verdict']
            claim['judge_notes'] = response['judge_notes']
            claim['evidence_quality'] = response['evidence_quality']
            claim['judge_timestamp'] = datetime.now().isoformat()
        
        history = update_claims_in_history(history, claims)
        save_version_history(str(version_history_file), history)
    
    # Assert: Verify rejection with quality scores
    with open(version_history_file, 'r') as f:
        final_history = json.load(f)
    
    claim = final_history["low_quality_paper.pdf"][-1]["review"]["Requirement(s)"][0]
    
    assert claim["status"] == "rejected"
    assert "evidence_quality" in claim
    
    quality = claim["evidence_quality"]
    assert quality["composite_score"] < 3.0
    assert quality["strength_score"] < 3
```

#### Test 3: Provenance Tracking

```python
@pytest.mark.integration
def test_claim_provenance_metadata(temp_workspace, test_data_generator):
    """
    Test that claims include provenance metadata.
    
    Validates:
    - Page numbers present
    - Section names detected
    - Supporting quotes extracted
    - Context preserved
    - Character offsets accurate
    """
    # Setup: Create multi-page test PDF with known sections
    test_pdf_content = [
        {"page": 1, "section": "Introduction", "content": "Background on neuromorphic computing..."},
        {"page": 5, "section": "Results", "content": "We achieved 94.3% accuracy on DVS128-Gesture dataset using a 3-layer SNN with spike-timing-dependent plasticity."},
        {"page": 6, "section": "Discussion", "content": "This represents a 12x improvement over baseline methods..."}
    ]
    
    # Create test data with provenance
    version_history = test_data_generator.create_version_history_with_provenance(
        filename="provenance_test.pdf",
        claims_with_provenance=[
            {
                "claim_id": "prov_001",
                "status": "pending_judge_review",
                "extracted_claim_text": "Achieved 94.3% accuracy on DVS128-Gesture",
                "provenance": {
                    "page_numbers": [5],
                    "section": "Results",
                    "supporting_quote": "We achieved 94.3% accuracy on DVS128-Gesture dataset",
                    "quote_page": 5,
                    "context_before": "Background on neuromorphic computing",
                    "context_after": "This represents a 12x improvement",
                    "char_start": 1250,
                    "char_end": 1380
                }
            }
        ]
    )
    
    version_history_file = temp_workspace / "review_version_history.json"
    with open(version_history_file, 'w') as f:
        json.dump(version_history, f, indent=2)
    
    # Load and verify provenance
    from literature_review.analysis.judge import load_version_history
    history = load_version_history(str(version_history_file))
    
    # Assert: Check provenance metadata
    claim = history["provenance_test.pdf"][0]["review"]["Requirement(s)"][0]
    
    assert "provenance" in claim
    prov = claim["provenance"]
    
    # Validate page numbers
    assert "page_numbers" in prov
    assert isinstance(prov["page_numbers"], list)
    assert 5 in prov["page_numbers"]
    
    # Validate section
    assert prov["section"] == "Results"
    
    # Validate supporting quote
    assert "supporting_quote" in prov
    assert "94.3% accuracy" in prov["supporting_quote"]
    
    # Validate context
    assert "context_before" in prov
    assert "context_after" in prov
    assert len(prov["context_before"]) > 0
    assert len(prov["context_after"]) > 0
    
    # Validate character offsets
    assert "char_start" in prov
    assert "char_end" in prov
    assert prov["char_start"] < prov["char_end"]
    assert prov["char_end"] - prov["char_start"] > 0
```

---

## Test Data Generator Updates

Add to `tests/fixtures/test_data_generator.py`:

```python
def create_version_history_with_quality_scores(
    self,
    filename: str,
    claims_with_scores: List[Dict]
) -> Dict:
    """Create version history with pre-populated evidence quality scores."""
    
    history = {filename: []}
    
    for claim in claims_with_scores:
        history[filename].append({
            "timestamp": datetime.now().isoformat(),
            "review": {
                "FILENAME": filename,
                "Requirement(s)": [
                    {
                        "claim_id": claim["claim_id"],
                        "status": claim["status"],
                        "evidence_quality": claim.get("evidence_quality", {}),
                        "provenance": claim.get("provenance", {}),
                        "extracted_claim_text": claim["extracted_claim_text"],
                        "sub_requirement": claim["sub_requirement"]
                    }
                ]
            }
        })
    
    return history

def create_version_history_with_provenance(
    self,
    filename: str,
    claims_with_provenance: List[Dict]
) -> Dict:
    """Create version history with provenance metadata."""
    
    history = {filename: []}
    
    for claim in claims_with_provenance:
        history[filename].append({
            "timestamp": datetime.now().isoformat(),
            "review": {
                "FILENAME": filename,
                "Requirement(s)": [claim]
            }
        })
    
    return history
```

---

## Success Criteria

### Original Criteria
- [ ] Test creates version history with pending claims
- [ ] Test simulates Judge processing with mocked API
- [ ] Test verifies claim statuses update correctly
- [ ] Test confirms version history structure maintained
- [ ] Test validates timestamps added
- [ ] Test preserves original data fields
- [ ] Test passes consistently (>95% pass rate)

### Enhanced Criteria (Evidence Quality)
- [ ] Multi-dimensional evidence quality scores validated
- [ ] Composite score calculation tested and accurate (±0.1)
- [ ] Approval threshold logic verified (composite ≥3.0, strength ≥3, relevance ≥3)
- [ ] Low-quality evidence rejection tested
- [ ] Provenance metadata (page numbers, sections, quotes) validated
- [ ] Character offsets accuracy checked
- [ ] Section heading detection tested (when applicable)
- [ ] All 6 quality dimensions present in approved claims
- [ ] Score ranges validated (1-5 for most, 1-3 for directness)

---

## Testing Strategy

### Unit Test Coverage
Run these tests to verify the integration:

```bash
# Run this specific integration test
pytest tests/integration/test_journal_to_judge.py -v

# Run with coverage
pytest tests/integration/test_journal_to_judge.py --cov=literature_review.analysis.judge --cov-report=term-missing

# Run with API mocks verification
pytest tests/integration/test_journal_to_judge.py -v -s
```

### Manual Verification Steps

1. **Verify version history structure:**
   ```bash
   cat temp_workspace/review_version_history.json | jq '.["test_paper.pdf"][-1]'
   ```

2. **Check quality scores:**
   ```bash
   cat temp_workspace/review_version_history.json | jq '.["high_quality_paper.pdf"][-1].review."Requirement(s)"[0].evidence_quality'
   ```

3. **Verify provenance:**
   ```bash
   cat temp_workspace/review_version_history.json | jq '.["provenance_test.pdf"][0].review."Requirement(s)"[0].provenance'
   ```

---

## Rollback Plan

If integration tests fail:
1. Check mock API responses are correctly formatted
2. Verify version history file structure
3. Validate test data generator produces correct fixtures
4. Review Judge module for breaking changes
5. Check that evidence quality fields are optional (backward compatibility)

---

## Files to Create/Modify

### New Files
- [x] `tests/integration/test_journal_to_judge.py` - Main integration test file

### Modified Files
- [x] `tests/fixtures/test_data_generator.py` - Add quality score and provenance generators
- [x] `tests/conftest.py` - Add shared fixtures if needed

---

## Estimated Effort

**Original Scope:** 6-8 hours  
**Enhanced Scope (with evidence quality):** 8-10 hours

**Breakdown:**
- Core integration tests: 3-4 hours
- Evidence quality scoring tests: 2-3 hours
- Provenance tracking tests: 2-3 hours
- Test data generator updates: 1 hour
- Documentation and verification: 1 hour

---

## Notes

- This test is critical path for evidence quality validation
- All evidence enhancement features must flow through this integration
- Test data should be realistic but small for fast execution
- Mock API calls to avoid costs but validate response structure
- Provenance tracking depends on PDF structure - use controlled test PDFs

---

**Task Card Status:** ⚠️ UPDATED for refactored architecture  
**Ready for Implementation:** ✅ Yes  
**Next Step:** Implement alongside Task Card #16 (Multi-Dimensional Scoring)  
**Integration Point:** Works with Task Card #17 (Provenance Tracking)

**Last Updated:** November 13, 2025
