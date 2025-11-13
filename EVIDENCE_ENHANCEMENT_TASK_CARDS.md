# Evidence Enhancement Task Cards - Integrated Roadmap

**Date Created:** November 12, 2025  
**Integration Status:** Aligned with Parallel Development Strategy (Waves 2-4)  
**Total Cards:** 6 enhancement cards  
**Dependencies:** Automation Task Cards #13, Testing Task Cards #5-7  

---

## 📋 Overview

These task cards implement evidence extraction enhancements from `EVIDENCE_EXTRACTION_ENHANCEMENTS.md`, **integrated into the existing wave structure** from `PARALLEL_DEVELOPMENT_STRATEGY.md`.

**Key Alignment:**
- Evidence enhancements **depend on** automation and testing infrastructure
- Cards are **sequenced** to leverage existing integration tests
- **Wave 2-4 placement** ensures foundation is stable before enhancement
- **Testing track validates** enhancements as they're built

---

## 🎯 Wave Alignment Analysis

### Wave 1 (Weeks 1-2) - **NO EVIDENCE CARDS**
**Reason:** Foundation must be stable first
- ✅ Automation: Task Card #13 (Basic Pipeline Orchestrator)
- ✅ Testing: Task Card #5 (Test Infrastructure)
- **Evidence enhancements wait** until these are complete

### Wave 2 (Weeks 3-4) - **QUICK WINS**
**Add to existing automation track:**
- Task Card #13.1: Checkpointing (EXISTING)
- Task Card #13.2: Retry Logic (EXISTING)
- **Task Card #16: Multi-Dimensional Evidence Scoring** ← NEW
- **Task Card #17: Claim Provenance Tracking** ← NEW

**Add to existing testing track:**
- Task Card #6: INT-001 tests (EXISTING)
- Task Card #7: INT-003 tests (EXISTING)
- **Modify #6 and #7** to validate evidence quality scores

### Wave 3 (Weeks 5-6) - **ADVANCED FEATURES**
**Add to existing automation track:**
- Task Card #14.1: Parallel Processing (EXISTING)
- Task Card #14.2: Smart Retry (EXISTING)
- Task Card #14.3: API Quota Management (EXISTING)
- **Task Card #18: Inter-Rater Reliability** ← NEW
- **Task Card #19: Temporal Coherence Analysis** ← NEW

**Add to existing testing track:**
- Task Card #8: INT-002 (DRA flow) (EXISTING)
- Task Card #9: INT-004/005 (Orchestrator) (EXISTING)
- **Modify #8 and #9** to validate temporal analysis and triangulation

### Wave 4 (Weeks 7-8) - **PRODUCTION POLISH**
**Add to existing automation track:**
- Task Card #15: Web Dashboard (EXISTING)
- **Task Card #20: Evidence Triangulation** ← NEW
- **Task Card #21: Methodological Quality (GRADE)** ← NEW

**Add to existing testing track:**
- Task Card #10: E2E-001 (Full Pipeline) (EXISTING)
- Task Card #11: E2E-002 (Convergence) (EXISTING)
- Task Card #12: CI/CD (EXISTING)
- **Modify E2E tests** to validate full evidence quality workflow

---

## 🎫 WAVE 2 ENHANCEMENT CARDS

### TASK CARD #16: Multi-Dimensional Evidence Scoring

**Priority:** 🔴 CRITICAL  
**Estimated Effort:** 6-8 hours  
**Risk Level:** MEDIUM  
**Wave:** Wave 2 (Weeks 3-4)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Cards #13 (Orchestrator), #5 (Test Infrastructure)  
**Blocks:** Task Cards #18, #19, #20, #21 (all depend on scoring)

#### Problem Statement

Current system uses binary approve/reject decisions with no quality gradation. This prevents:
- Prioritizing high-quality evidence over weak evidence
- Identifying borderline claims needing human review
- Weighted gap analysis in Orchestrator
- Meta-analytic aggregation of findings

A multi-dimensional scoring system enables evidence tiers, quality-based prioritization, and transparent decision-making aligned with systematic review best practices.

#### Acceptance Criteria

**Functional Requirements:**
- [ ] Judge.py outputs 6-dimensional evidence quality scores
- [ ] Composite score calculated via weighted average
- [ ] Scores persisted in version history
- [ ] Orchestrator uses scores for weighted gap analysis
- [ ] Visualization shows evidence quality distribution

**Scoring Dimensions (1-5 scale except directness):**
- [ ] Strength of Evidence (1-5): Strong experimental → Weak observational
- [ ] Methodological Rigor (1-5): RCT → Case study → Opinion
- [ ] Relevance to Requirement (1-5): Perfect match → Tangential
- [ ] Evidence Directness (1-3): Direct statement → Inferred
- [ ] Recency Bonus (boolean): Published within 3 years
- [ ] Reproducibility (1-5): Code+data available → None

**Non-Functional Requirements:**
- [ ] Backward compatible with existing claims (default scores)
- [ ] Score calculation <10ms per claim
- [ ] Composite score formula: strength(0.3) + rigor(0.25) + relevance(0.25) + directness/3(0.1) + recency(0.05) + reproducibility(0.05)
- [ ] Approval threshold: composite ≥ 3.0 AND strength ≥ 3 AND relevance ≥ 3

#### Implementation Guide

**Files to Modify:**

1. **Judge.py** (~150 lines new/modified)

```python
def build_judge_prompt_enhanced(claim: Dict, sub_requirement_definition: str) -> str:
    """
    Enhanced prompt with multi-dimensional scoring.
    
    Returns prompt requesting 6-dimensional evidence quality scores
    following PRISMA systematic review standards.
    """
    return f"""
You are an impartial "Judge" AI evaluating scientific evidence quality.

**Claim to Evaluate:**
{json.dumps(claim, indent=2)}

**Target Requirement:**
{sub_requirement_definition}

**Your Task:**
Assess this claim using PRISMA systematic review standards across 6 dimensions:

1. **Strength of Evidence** (1-5):
   - 5: Strong (Multiple RCTs, meta-analysis, direct experimental proof)
   - 4: Moderate (Single well-designed study, clear experimental validation)
   - 3: Weak (Observational study, indirect evidence)
   - 2: Very Weak (Case reports, anecdotal evidence)
   - 1: Insufficient (Opinion, speculation, no empirical support)

2. **Methodological Rigor** (1-5):
   - 5: Gold standard (Randomized controlled trial, peer-reviewed, replicated)
   - 4: Controlled study (Experimental with controls, proper statistics)
   - 3: Observational (Real-world data, no controls)
   - 2: Case study (Single instance, n=1)
   - 1: Opinion (Expert opinion without empirical basis)

3. **Relevance to Requirement** (1-5):
   - 5: Perfect match (Directly addresses this exact requirement)
   - 4: Strong (Clearly related, minor gap)
   - 3: Moderate (Related but requires inference)
   - 2: Tangential (Peripherally related)
   - 1: Weak (Very indirect connection)

4. **Evidence Directness** (1-3):
   - 3: Direct (Paper explicitly states this finding)
   - 2: Indirect (Finding can be inferred from results)
   - 1: Inferred (Requires significant interpretation)

5. **Recency Bonus**:
   - true if published within last 3 years, false otherwise

6. **Reproducibility** (1-5):
   - 5: Code + data publicly available
   - 4: Detailed methods, replicable
   - 3: Basic methods described
   - 2: Vague methods
   - 1: No methodological detail

**Decision Criteria:**
- APPROVE if composite_score ≥ 3.0 AND strength_score ≥ 3 AND relevance_score ≥ 3
- REJECT otherwise

**Return Format (JSON only):**
{{
  "verdict": "approved|rejected",
  "evidence_quality": {{
    "strength_score": <1-5>,
    "strength_rationale": "<brief justification>",
    "rigor_score": <1-5>,
    "study_type": "experimental|observational|theoretical|review|opinion",
    "relevance_score": <1-5>,
    "relevance_notes": "<brief explanation>",
    "directness": <1-3>,
    "is_recent": <true|false>,
    "reproducibility_score": <1-5>,
    "composite_score": <calculated weighted average>,
    "confidence_level": "high|medium|low"
  }},
  "judge_notes": "<1-2 sentence summary>"
}}

**Composite Score Formula:**
composite_score = (strength × 0.30) + (rigor × 0.25) + (relevance × 0.25) + (directness/3 × 0.10) + (recency × 0.05) + (reproducibility × 0.05)
"""

def validate_judge_response_enhanced(response: Any) -> Optional[Dict]:
    """Validate enhanced Judge response with quality scores."""
    if not isinstance(response, dict):
        return None
    
    # Check required fields
    if "verdict" not in response or "evidence_quality" not in response:
        return None
    
    verdict = response["verdict"]
    if verdict not in ["approved", "rejected"]:
        return None
    
    quality = response["evidence_quality"]
    
    # Validate score ranges
    required_scores = {
        "strength_score": (1, 5),
        "rigor_score": (1, 5),
        "relevance_score": (1, 5),
        "directness": (1, 3),
        "reproducibility_score": (1, 5),
        "composite_score": (1, 5)
    }
    
    for score_name, (min_val, max_val) in required_scores.items():
        if score_name not in quality:
            return None
        score = quality[score_name]
        if not isinstance(score, (int, float)) or score < min_val or score > max_val:
            return None
    
    # Validate study type
    if quality.get("study_type") not in ["experimental", "observational", "theoretical", "review", "opinion"]:
        return None
    
    # Validate confidence level
    if quality.get("confidence_level") not in ["high", "medium", "low"]:
        return None
    
    return response

def calculate_composite_score(quality: Dict) -> float:
    """
    Calculate composite evidence quality score.
    
    Formula: (strength × 0.30) + (rigor × 0.25) + (relevance × 0.25) 
             + (directness/3 × 0.10) + (recency × 0.05) + (reproducibility × 0.05)
    """
    weights = {
        "strength_score": 0.30,
        "rigor_score": 0.25,
        "relevance_score": 0.25,
        "directness": 0.10,  # Normalized to 0-1 range (divide by 3)
        "is_recent": 0.05,   # Boolean treated as 0 or 1
        "reproducibility_score": 0.05
    }
    
    score = 0.0
    score += quality["strength_score"] * weights["strength_score"]
    score += quality["rigor_score"] * weights["rigor_score"]
    score += quality["relevance_score"] * weights["relevance_score"]
    score += (quality["directness"] / 3.0) * weights["directness"]  # Normalize to 0-1
    score += (1.0 if quality["is_recent"] else 0.0) * weights["is_recent"]
    score += quality["reproducibility_score"] * weights["reproducibility_score"]
    
    return round(score, 2)
```

2. **Update claim structure in version history** (~30 lines)

```python
# Example claim with enhanced evidence quality
enhanced_claim = {
    "claim_id": "c1a2b3",
    "status": "approved",
    "evidence_quality": {
        "strength_score": 4,
        "strength_rationale": "Direct experimental validation with quantitative metrics",
        "rigor_score": 5,
        "study_type": "experimental",
        "relevance_score": 4,
        "relevance_notes": "Directly addresses SNN feature extraction on DVS data",
        "directness": 3,
        "is_recent": True,
        "reproducibility_score": 4,
        "composite_score": 4.2,
        "confidence_level": "high"
    },
    "judge_notes": "Strong experimental evidence with public code repository.",
    "sub_requirement": "Sub-2.1.1",
    # ... other fields
}
```

3. **Orchestrator.py updates** (~80 lines)

```python
def calculate_weighted_gap_score(db: pd.DataFrame, pillar_definitions: Dict) -> Dict:
    """
    Calculate gap scores weighted by evidence quality.
    
    Prioritizes filling gaps where evidence is weak or missing.
    """
    gap_scores = {}
    
    for pillar_name, pillar_data in pillar_definitions.items():
        for req_key, req_data in pillar_data.get("requirements", {}).items():
            for sub_req in req_data:
                # Get all claims for this sub-requirement
                claims = db[db["Requirement(s)"].str.contains(sub_req, na=False)]
                
                if claims.empty:
                    # No evidence: highest priority
                    gap_scores[sub_req] = {
                        "priority": 1.0,
                        "reason": "no_evidence",
                        "avg_quality": 0.0,
                        "claim_count": 0
                    }
                else:
                    # Extract quality scores
                    quality_scores = []
                    for _, row in claims.iterrows():
                        req_list = json.loads(row["Requirement(s)"])
                        for claim in req_list:
                            if sub_req in claim.get("sub_requirement", ""):
                                quality = claim.get("evidence_quality", {})
                                composite = quality.get("composite_score", 3.0)
                                quality_scores.append(composite)
                    
                    avg_quality = np.mean(quality_scores) if quality_scores else 3.0
                    
                    # Priority inversely proportional to quality
                    # Low quality (1.0) = High priority (1.0)
                    # High quality (5.0) = Low priority (0.2)
                    priority = 1.0 - ((avg_quality - 1.0) / 4.0)
                    
                    gap_scores[sub_req] = {
                        "priority": priority,
                        "reason": "low_quality_evidence" if avg_quality < 3.5 else "sufficient_evidence",
                        "avg_quality": avg_quality,
                        "claim_count": len(quality_scores)
                    }
    
    return gap_scores

def plot_evidence_quality_distribution(db: pd.DataFrame, output_file: str):
    """Generate histogram of evidence quality scores."""
    import matplotlib.pyplot as plt
    
    quality_scores = []
    for _, row in db.iterrows():
        req_list = json.loads(row.get("Requirement(s)", "[]"))
        for claim in req_list:
            quality = claim.get("evidence_quality", {})
            score = quality.get("composite_score")
            if score:
                quality_scores.append(score)
    
    plt.figure(figsize=(10, 6))
    plt.hist(quality_scores, bins=20, edgecolor='black', alpha=0.7)
    plt.xlabel("Composite Evidence Quality Score")
    plt.ylabel("Number of Claims")
    plt.title("Distribution of Evidence Quality Scores")
    plt.axvline(x=3.0, color='r', linestyle='--', label='Approval Threshold')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
```

#### Testing Strategy

**Unit Tests** (`tests/unit/test_evidence_scoring.py`):
```python
@pytest.mark.unit
def test_composite_score_calculation():
    """Test composite score formula."""
    quality = {
        "strength_score": 4,
        "rigor_score": 5,
        "relevance_score": 4,
        "directness": 3,
        "is_recent": True,
        "reproducibility_score": 4
    }
    
    score = calculate_composite_score(quality)
    
    # Expected: (4*0.3) + (5*0.25) + (4*0.25) + (3/3*0.1) + (1*0.05) + (4*0.05)
    # = 1.2 + 1.25 + 1.0 + 0.1 + 0.05 + 0.2 = 3.8
    assert abs(score - 3.8) < 0.01

@pytest.mark.unit  
def test_approval_threshold():
    """Test that composite ≥3.0 AND strength ≥3 AND relevance ≥3 required."""
    # Should approve
    quality_approve = {
        "strength_score": 4,
        "rigor_score": 3,
        "relevance_score": 4,
        "directness": 3,
        "is_recent": False,
        "reproducibility_score": 3,
        "composite_score": 3.5
    }
    
    # Should reject (low strength)
    quality_reject = {
        "strength_score": 2,
        "rigor_score": 5,
        "relevance_score": 5,
        "directness": 3,
        "is_recent": True,
        "reproducibility_score": 5,
        "composite_score": 3.6  # Composite high but strength too low
    }
    
    assert meets_approval_criteria(quality_approve) == True
    assert meets_approval_criteria(quality_reject) == False
```

**Integration Tests** (Modify existing Task Card #6):
```python
@pytest.mark.integration
def test_judge_outputs_quality_scores(temp_workspace, test_data_generator):
    """Test Judge outputs evidence quality scores."""
    
    # Setup version history
    version_history = test_data_generator.create_version_history(
        filename="quality_test.pdf",
        num_versions=1,
        claim_statuses=['pending_judge_review']
    )
    
    # Mock Judge with quality scores
    mock_response = {
        "verdict": "approved",
        "evidence_quality": {
            "strength_score": 4,
            "strength_rationale": "Strong experimental evidence",
            "rigor_score": 5,
            "study_type": "experimental",
            "relevance_score": 4,
            "relevance_notes": "Directly relevant",
            "directness": 3,
            "is_recent": True,
            "reproducibility_score": 4,
            "composite_score": 4.2,
            "confidence_level": "high"
        },
        "judge_notes": "Approved. High quality evidence."
    }
    
    # Execute Judge
    with patch.object(Judge.APIManager, 'cached_api_call') as mock_api:
        mock_api.return_value = mock_response
        
        # ... (run Judge logic)
    
    # Assert quality scores present in version history
    with open(version_history_file) as f:
        history = json.load(f)
    
    claim = history["quality_test.pdf"][-1]["review"]["Requirement(s)"][0]
    assert "evidence_quality" in claim
    assert claim["evidence_quality"]["composite_score"] == 4.2
```

#### Success Criteria

- [ ] Judge.py prompt includes 6-dimensional scoring instructions
- [ ] Judge.py validates score ranges (1-5 for most, 1-3 for directness)
- [ ] Composite score calculation matches formula
- [ ] Approval threshold enforced (composite ≥3.0, strength ≥3, relevance ≥3)
- [ ] Version history stores quality scores
- [ ] Orchestrator uses scores for weighted gap analysis
- [ ] Visualization shows quality distribution
- [ ] Unit tests pass (100% coverage for scoring logic)
- [ ] Integration tests validate end-to-end flow
- [ ] Documentation updated with scoring methodology

#### Migration Strategy

**Backward Compatibility:**
```python
def migrate_existing_claims():
    """Add default scores to claims without evidence_quality."""
    with open('review_version_history.json', 'r') as f:
        history = json.load(f)
    
    for filename, versions in history.items():
        for version in versions:
            claims = version.get('review', {}).get('Requirement(s)', [])
            for claim in claims:
                if 'evidence_quality' not in claim and claim.get('status') == 'approved':
                    # Assign default moderate scores
                    claim['evidence_quality'] = {
                        "strength_score": 3,
                        "strength_rationale": "Legacy claim (default score)",
                        "rigor_score": 3,
                        "study_type": "unknown",
                        "relevance_score": 3,
                        "relevance_notes": "Legacy claim",
                        "directness": 2,
                        "is_recent": False,
                        "reproducibility_score": 3,
                        "composite_score": 3.0,
                        "confidence_level": "medium"
                    }
    
    with open('review_version_history.json', 'w') as f:
        json.dump(history, f, indent=2)
```

---

### TASK CARD #17: Claim Provenance Tracking

**Priority:** 🟡 HIGH  
**Estimated Effort:** 4-6 hours  
**Risk Level:** LOW  
**Wave:** Wave 2 (Weeks 3-4)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Card #5 (Test Infrastructure)  
**Blocks:** None (can run in parallel with #16)

#### Problem Statement

Current claims have filename but not page numbers, section names, or direct quotes. This prevents:
- Human verification of extracted claims
- Targeted re-review of specific sections
- Citation generation for reports
- Audit trail for systematic review compliance

Provenance tracking enables full traceability from claim back to exact source location with surrounding context.

#### Acceptance Criteria

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

#### Implementation Guide

**Files to Modify:**

1. **Journal-Reviewer.py** (~120 lines new/modified)

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

2. **Update claim structure** (~20 lines)

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

#### Testing Strategy

**Unit Tests:**
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

**Integration Tests** (Modify Task Card #6):
```python
@pytest.mark.integration
def test_journal_reviewer_adds_provenance(temp_workspace):
    """Test Journal-Reviewer extracts provenance metadata."""
    # Create test PDF with known content
    # Extract claims
    # Verify provenance fields present
    # Check page numbers accurate
    pass
```

#### Success Criteria

- [ ] Page-level text extraction preserves structure
- [ ] Section detection >70% accurate on test papers
- [ ] Provenance added to all new claims
- [ ] Character offsets validated for accuracy
- [ ] Context extraction works correctly
- [ ] Provenance adds <10% to claim JSON size
- [ ] Unit tests pass (90% coverage)
- [ ] Integration tests validate end-to-end

---

## 🎫 WAVE 3 ENHANCEMENT CARDS

### TASK CARD #18: Inter-Rater Reliability (Multi-Judge Consensus)

**Priority:** 🟡 MEDIUM  
**Estimated Effort:** 6-8 hours  
**Risk Level:** MEDIUM  
**Wave:** Wave 3 (Weeks 5-6)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Card #16 (Evidence Scoring)  
**Blocks:** None

*(Full implementation similar to Recommendation #3 in EVIDENCE_EXTRACTION_ENHANCEMENTS.md)*

---

### TASK CARD #19: Temporal Coherence Validation

**Priority:** 🟡 MEDIUM  
**Estimated Effort:** 8-10 hours  
**Risk Level:** LOW  
**Wave:** Wave 3 (Weeks 5-6)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Card #16 (Evidence Scoring), Task Card #9 (Orchestrator tests)  
**Blocks:** None

*(Full implementation similar to Recommendation #4 in EVIDENCE_EXTRACTION_ENHANCEMENTS.md)*

---

## 🎫 WAVE 4 ENHANCEMENT CARDS

### TASK CARD #20: Evidence Triangulation

**Priority:** 🟢 MEDIUM  
**Estimated Effort:** 10-12 hours  
**Risk Level:** MEDIUM  
**Wave:** Wave 4 (Weeks 7-8)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Cards #16, #17 (Scoring + Provenance)  
**Blocks:** None

*(Full implementation similar to Recommendation #5 in EVIDENCE_EXTRACTION_ENHANCEMENTS.md)*

---

### TASK CARD #21: Methodological Quality Assessment (GRADE)

**Priority:** 🟢 LOW  
**Estimated Effort:** 8-10 hours  
**Risk Level:** LOW  
**Wave:** Wave 4 (Weeks 7-8)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Card #16 (Evidence Scoring)  
**Blocks:** None

*(Full implementation similar to Recommendation #6 in EVIDENCE_EXTRACTION_ENHANCEMENTS.md)*

---

## 📊 Integrated Wave Summary

### Wave 1 (Weeks 1-2) - Foundation
**Automation Track:**
- Task Card #13: Basic Pipeline Orchestrator ✅ (MERGED)

**Testing Track:**
- Task Card #5: Test Infrastructure ✅ (MERGED)

**Evidence Track:**
- None (wait for foundation)

---

### Wave 2 (Weeks 3-4) - Quick Wins
**Automation Track:**
- Task Card #13.1: Checkpointing (4-6h)
- Task Card #13.2: Retry Logic (4-6h)
- **Task Card #16: Multi-Dimensional Scoring (6-8h)** ← NEW
- **Task Card #17: Provenance Tracking (4-6h)** ← NEW

**Testing Track:**
- Task Card #6: INT-001 (Journal→Judge) (6-8h) + **Validate scoring**
- Task Card #7: INT-003 (Version History→CSV) (4-6h)

**Total Wave 2 Effort:** 28-40 hours (was 20-28h)

---

### Wave 3 (Weeks 5-6) - Advanced Features
**Automation Track:**
- Task Card #14.1: Parallel Processing (6-8h)
- Task Card #14.2: Smart Retry (4-6h)
- Task Card #14.3: API Quota (4-6h)
- **Task Card #18: Inter-Rater Reliability (6-8h)** ← NEW
- **Task Card #19: Temporal Coherence (8-10h)** ← NEW

**Testing Track:**
- Task Card #8: INT-002 (DRA flow) (10-12h) + **Validate temporal**
- Task Card #9: INT-004/005 (Orchestrator) (8-10h)

**Total Wave 3 Effort:** 46-60 hours (was 32-42h)

---

### Wave 4 (Weeks 7-8) - Production Polish
**Automation Track:**
- Task Card #15: Web Dashboard (40-60h)
- **Task Card #20: Evidence Triangulation (10-12h)** ← NEW
- **Task Card #21: GRADE Quality (8-10h)** ← NEW

**Testing Track:**
- Task Card #10: E2E-001 (Full Pipeline) (12-16h) + **Validate all quality**
- Task Card #11: E2E-002 (Convergence) (10-12h)
- Task Card #12: CI/CD (6-8h)

**Total Wave 4 Effort:** 86-118 hours (was 68-96h)

---

## 📈 Priority Matrix

| Card # | Enhancement | Effort | Priority | Wave | Impact |
|--------|-------------|--------|----------|------|--------|
| #16 | Multi-Dimensional Scoring | 6-8h | 🔴 CRITICAL | Wave 2 | HIGH |
| #17 | Provenance Tracking | 4-6h | 🟡 HIGH | Wave 2 | MEDIUM |
| #18 | Inter-Rater Reliability | 6-8h | 🟡 MEDIUM | Wave 3 | MEDIUM |
| #19 | Temporal Coherence | 8-10h | 🟡 MEDIUM | Wave 3 | MEDIUM |
| #20 | Evidence Triangulation | 10-12h | 🟢 MEDIUM | Wave 4 | HIGH |
| #21 | GRADE Quality | 8-10h | 🟢 LOW | Wave 4 | MEDIUM |

---

## ✅ Integration Checklist

**Wave 2 Integration:**
- [ ] Task Card #16 (Scoring) scheduled alongside #13.1, #13.2
- [ ] Task Card #17 (Provenance) can run in parallel with #16
- [ ] INT-001 tests (Task #6) modified to validate evidence scores
- [ ] INT-003 tests (Task #7) validate provenance in CSV sync

**Wave 3 Integration:**
- [ ] Task Card #18 (Consensus) depends on #16 scores
- [ ] Task Card #19 (Temporal) uses scores for trend analysis
- [ ] INT-002 tests (Task #8) validate temporal analysis
- [ ] Orchestrator tests (Task #9) validate weighted gap analysis

**Wave 4 Integration:**
- [ ] Task Card #20 (Triangulation) uses #16, #17 data
- [ ] Task Card #21 (GRADE) builds on #16 scoring
- [ ] E2E tests (#10, #11) validate full quality pipeline
- [ ] Web dashboard (#15) displays quality metrics

---

## 🎯 Success Metrics

**Evidence Quality Improvements:**
- [ ] 100% of claims have multi-dimensional scores (Task #16)
- [ ] 90%+ of claims have page-level provenance (Task #17)
- [ ] Borderline claims get consensus review (Task #18)
- [ ] Evidence evolution tracked for all sub-requirements (Task #19)
- [ ] Contradictory findings automatically flagged (Task #20)
- [ ] GRADE quality levels assigned to all claims (Task #21)

**Process Improvements:**
- [ ] Gap analysis prioritizes low-quality evidence areas
- [ ] Visual quality dashboards available
- [ ] Temporal trends guide research priorities
- [ ] Publication-ready systematic review output

---

**Document Status:** ✅ Ready for Integration  
**Next Action:** Review alignment with team, schedule Wave 2 cards  
**Total Additional Effort:** 42-54 hours across all 6 cards (integrated into 8-week timeline)
