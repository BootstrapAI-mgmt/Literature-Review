# TASK CARD #17: Claim Provenance Tracking

**Priority:** 🟡 HIGH  
**Estimated Effort:** 4-6 hours  
**Risk Level:** LOW  
**Wave:** Wave 2 (Weeks 3-4)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Card #5 (Test Infrastructure)  
**Blocks:** None (can run in parallel with #16)

## Problem Statement

Current claims have filename but not page numbers, section names, or direct quotes. This prevents:
- Human verification of extracted claims
- Targeted re-review of specific sections
- Citation generation for reports
- Audit trail for systematic review compliance

Provenance tracking enables full traceability from claim back to exact source location with surrounding context.

## Acceptance Criteria

**Functional Requirements:**
- [ ] Journal-Reviewer extracts page-level metadata
- [ ] Claims include page numbers and section names
- [ ] Direct quotes stored with character offsets
- [ ] Context (before/after) preserved
- [ ] DOI/URL captured if available

**Technical Requirements:**
- [ ] Page detection works for standard PDFs
- [ ] Section heading detection >70% accurate
- [ ] Quote extraction preserves formatting
- [ ] Character offsets validated for accuracy
- [ ] Provenance adds <10% to claim size

## Implementation Guide

**Files to Modify:**

### 1. literature_review/reviewers/journal_reviewer.py (~120 lines new/modified)

```python
def extract_text_with_provenance(file_path: str) -> List[Dict]:
    """
    Extract text with page-level tracking and section detection.
    
    Returns:
        List of dicts with page metadata:
        [
            {
                "page_num": 1,
                "text": "...",
                "section": "Introduction",
                "char_start": 0,
                "char_end": 1250
            },
            ...
        ]
    """
    pages_with_metadata = []
    cumulative_chars = 0
    
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            
            # Detect section heading
            section = detect_section_heading(text)
            
            page_metadata = {
                "page_num": page_num,
                "text": text,
                "section": section or "Unknown",
                "char_start": cumulative_chars,
                "char_end": cumulative_chars + len(text)
            }
            
            pages_with_metadata.append(page_metadata)
            cumulative_chars += len(text)
    
    return pages_with_metadata

def detect_section_heading(text: str) -> Optional[str]:
    """
    Detect academic paper section headings.
    
    Looks for common patterns in first 200 characters.
    """
    headings = [
        "abstract", "introduction", "background", "related work",
        "methods", "methodology", "approach", "design",
        "results", "findings", "experiments", "evaluation",
        "discussion", "analysis", "interpretation",
        "conclusion", "future work", "limitations",
        "references", "bibliography", "acknowledgments"
    ]
    
    # Normalize and check first lines
    first_lines = text[:200].lower().strip()
    
    for heading in headings:
        # Match patterns like "1. Introduction" or "INTRODUCTION" or "1 Introduction"
        patterns = [
            f"\\d+\\.?\\s*{heading}",  # "1. Introduction"
            f"^{heading}$",             # "Introduction" (line by itself)
            f"\\b{heading}\\b"          # Word boundary match
        ]
        
        for pattern in patterns:
            if re.search(pattern, first_lines, re.IGNORECASE | re.MULTILINE):
                return heading.title()
    
    return None

def add_provenance_to_claim(
    claim: Dict,
    full_text: str,
    pages_metadata: List[Dict],
    evidence_text: str
) -> Dict:
    """
    Add provenance metadata to claim.
    
    Finds the evidence text in full document and adds:
    - Page numbers
    - Section name
    - Character offsets
    - Supporting quote
    - Context before/after
    """
    # Find evidence location
    evidence_start = full_text.find(evidence_text)
    
    if evidence_start == -1:
        # Evidence not found verbatim (might be paraphrased)
        # Fall back to fuzzy matching or skip provenance
        return claim
    
    evidence_end = evidence_start + len(evidence_text)
    
    # Find which page(s) contain this evidence
    pages_containing_evidence = []
    for page_meta in pages_metadata:
        if (evidence_start >= page_meta["char_start"] and 
            evidence_start < page_meta["char_end"]):
            pages_containing_evidence.append(page_meta["page_num"])
        elif (evidence_end > page_meta["char_start"] and 
              evidence_end <= page_meta["char_end"]):
            pages_containing_evidence.append(page_meta["page_num"])
    
    # Get section name from first page
    first_page_meta = next(
        (p for p in pages_metadata if p["page_num"] == pages_containing_evidence[0]),
        None
    )
    section = first_page_meta["section"] if first_page_meta else "Unknown"
    
    # Extract context (100 chars before/after)
    context_window = 100
    context_before = full_text[max(0, evidence_start - context_window):evidence_start]
    context_after = full_text[evidence_end:evidence_end + context_window]
    
    # Add provenance
    claim["provenance"] = {
        "page_numbers": pages_containing_evidence,
        "section": section,
        "char_start": evidence_start,
        "char_end": evidence_end,
        "supporting_quote": evidence_text[:500],  # Truncate long quotes
        "quote_page": pages_containing_evidence[0] if pages_containing_evidence else None,
        "context_before": context_before.strip(),
        "context_after": context_after.strip()
    }
    
    return claim
```

### 2. Version History Schema (~20 lines)

```python
# Enhanced claim with provenance
claim_with_provenance = {
    "claim_id": "c1a2b3",
    "status": "approved",
    "provenance": {
        "filename": "neuromorphic_snn_2024.pdf",
        "page_numbers": [5, 6],
        "section": "Results",
        "char_start": 12450,
        "char_end": 12890,
        "supporting_quote": "We achieved 94.3% accuracy on DVS128-Gesture using a 3-layer SNN...",
        "quote_page": 5,
        "context_before": "...previous methods required 15mJ per inference.",
        "context_after": "This represents a 12x improvement over baseline...",
        "doi": "10.1109/TNNLS.2024.12345",  # If available
        "url": "https://arxiv.org/abs/2401.12345"  # If available
    },
    "sub_requirement": "Sub-2.1.1",
    "extracted_claim_text": "Achieved 94.3% accuracy...",
    # ... rest of claim
}
```

## Testing Strategy

### Unit Tests

```python
@pytest.mark.unit
def test_section_heading_detection():
    """Test section heading detection."""
    text_intro = "1. Introduction\n\nThis paper presents..."
    assert detect_section_heading(text_intro) == "Introduction"
    
    text_methods = "METHODS\n\nWe used the following approach..."
    assert detect_section_heading(text_methods) == "Methods"
    
    text_no_heading = "This is body text without a heading..."
    assert detect_section_heading(text_no_heading) is None

@pytest.mark.unit
def test_provenance_addition():
    """Test adding provenance to claim."""
    full_text = "Some intro text. The key finding is that SNNs achieve 95% accuracy. More text."
    pages_metadata = [
        {"page_num": 1, "section": "Results", "char_start": 0, "char_end": 100}
    ]
    
    claim = {"extracted_claim_text": "SNNs achieve 95% accuracy"}
    evidence_text = "SNNs achieve 95% accuracy"
    
    enhanced_claim = add_provenance_to_claim(claim, full_text, pages_metadata, evidence_text)
    
    assert "provenance" in enhanced_claim
    assert enhanced_claim["provenance"]["page_numbers"] == [1]
    assert enhanced_claim["provenance"]["section"] == "Results"
    assert "The key finding is that" in enhanced_claim["provenance"]["context_before"]
```

### Integration Tests (Modify Task Card #6)

```python
from literature_review.reviewers.journal_reviewer import extract_text_with_provenance, add_provenance_to_claim

@pytest.mark.integration
def test_journal_reviewer_adds_provenance(temp_workspace):
    """Test Journal-Reviewer extracts provenance metadata."""
    # Create test PDF with known content
    # Extract claims
    # Verify provenance fields present
    # Check page numbers accurate
    pass
```

## Success Criteria

- [ ] Page-level text extraction preserves structure
- [ ] Section detection >70% accurate on test papers
- [ ] Provenance added to all new claims
- [ ] Character offsets validated for accuracy
- [ ] Context extraction works correctly
- [ ] Provenance adds <10% to claim JSON size
- [ ] Unit tests pass (90% coverage)
- [ ] Integration tests validate end-to-end

## Benefits

1. **Verifiable claims** - Human reviewers can check exact source
2. **Citation generation** - Auto-generate "According to Smith et al. (2024, p. 5)..."
3. **Conflict resolution** - Trace contradictory claims to different papers/sections
4. **Targeted re-review** - Re-analyze specific sections if needed
5. **Audit trail** - Full transparency for systematic review standards

---

**Status:** Ready for implementation  
**Wave:** Wave 2 (Weeks 3-4)  
**Next Steps:** Implement literature_review/reviewers/journal_reviewer.py page-level extraction, add provenance to claims
