# Manual Annotation Plan for Golden Dataset

## Status: ACTIVE
Created: 2025-01-13
Triggered By: Verification failures in PR #144 and PR #145

---

## Background

### What Happened
Coding agent (Copilot) was used to create anchor paper annotations for the golden dataset. Verification against actual source papers revealed:

| Paper | Issue | Severity |
|-------|-------|----------|
| NEURO-ANCHOR-001 | arXiv ID points to completely wrong paper | **CRITICAL** |
| NEURO-ANCHOR-002 | Some author discrepancies, claims mostly verified | Minor |
| QUANTUM-ANCHOR-001 | ~33% of claims are fabricated numeric values | **CRITICAL** |
| MICROBIO-ANCHOR-001 | Authors completely fabricated | **CRITICAL** |

### Root Cause
The coding agent appears to:
- Have access to paper metadata/abstracts
- NOT reliably read full PDFs
- "Fill in" specific details with plausible-sounding fabrications
- Sometimes use completely wrong identifiers

### Impact
The golden dataset's purpose is ground truth validation. Fabricated claims completely undermine this purpose. **Manual annotation is required.**

---

## Manual Annotation Strategy

### Option 1: Full Manual (Recommended for Anchor Papers)
Human annotator reads paper, extracts claims, verifies each one.

**Pros:** Highest accuracy, true ground truth
**Cons:** Time-intensive (~2-4 hours per anchor paper)
**Use for:** 5-7 anchor papers requiring exhaustive annotation

### Option 2: AI-Assisted with Human Verification
AI extracts initial claims, human verifies each against source PDF.

**Pros:** Faster than full manual, still accurate
**Cons:** May miss claims AI doesn't identify
**Use for:** Standard papers (70+) requiring representative claims

### Option 3: Structured Template with Source Citations
Use forms requiring specific page/section citations for every claim.

**Pros:** Forces verification during annotation
**Cons:** Requires discipline to follow
**Use for:** Both anchor and standard papers

---

## Phase 1: Anchor Paper Annotation (Priority)

### Target: 5-7 Papers with Exhaustive Annotation

#### Selection Criteria
Per [ANCHOR_PAPER_CRITERIA.md](../../tests/golden_dataset/docs/ANCHOR_PAPER_CRITERIA.md):
- Open access (CC-BY or equivalent)
- Peer reviewed
- 10-30 extractable claims
- Text-extractable PDF
- Published 2020-2025

#### Domain Distribution
| Domain | Papers | Status |
|--------|--------|--------|
| Neuromorphic | 2 | ⏳ Pending |
| Quantum | 1 | ⏳ Pending |
| Microbiology | 1 | ⏳ Pending |
| Climate | 1 | ⏳ Pending |
| Materials/Other | 1 | ⏳ Pending |

### Recommended Papers (Verified as Real)

Based on our verification work, these papers ARE real and accessible:

1. **Quantum Computing** (arXiv:2408.13687)
   - Title: "Quantum Error Correction Below the Surface Code Threshold"
   - Authors: Google Quantum AI
   - ✅ Verified: Paper exists, published Nature 2025
   - Full PDF available at arxiv.org
   
2. **Neuromorphic/SNN** (arXiv:2403.00270)
   - Title: "Event-Driven Learning for Spiking Neural Networks"
   - Authors: Wenjie Wei, Malu Zhang, et al.
   - ✅ Verified: Paper exists, key claims match abstract

3. **Microbiology** (DOI:10.1371/journal.pone.0321881)
   - Title: CRISPR paper on genome editing
   - Authors: Ishrya Sharma, Kerisa Hall, Shannon Moonah (NOT Liu/Anzalone!)
   - ✅ Verified: Paper exists, PLOS ONE open access

4. **Climate** (arXiv:2308.02460) - NEEDS VERIFICATION
   - Should verify arXiv ID before proceeding

### Annotation Protocol

For each anchor paper:

#### Step 1: Paper Verification (30 min)
- [ ] Download actual PDF from source
- [ ] Verify title matches
- [ ] Verify all authors match
- [ ] Confirm publication venue
- [ ] Document DOI/arXiv ID

#### Step 2: Claim Extraction (2-3 hours)
- [ ] Read paper completely
- [ ] Mark EVERY claim in PDF
- [ ] For each claim, record:
  - Verbatim text
  - Page number
  - Section (Abstract/Intro/Methods/Results/Discussion)
  - Type (quantitative/qualitative/methodological)
  
#### Step 3: Claim Classification (1 hour)
- [ ] Classify extractability (HIGH/MEDIUM/LOW)
- [ ] Map to requirements (pillar coverage)
- [ ] Assign confidence level
- [ ] Note any ambiguities

#### Step 4: JSON Creation (30 min)
- [ ] Use schema from schema_anchor.py
- [ ] Include source citations for every claim
- [ ] Run validation tests

#### Step 5: Peer Verification (1 hour)
- [ ] Second annotator spot-checks 20% of claims
- [ ] Verify page/section citations are correct
- [ ] Calculate inter-annotator agreement

---

## Phase 2: Paper Registry Cleanup

### Issue
The paper_registry.json contains entries with fabricated data:
- NEURO entry 1: Uses arXiv:2204.13969 which is algebraic geometry paper
- MICROBIO entry 1: Lists wrong authors (Liu/Anzalone vs actual)

### Required Actions
1. [ ] Verify every paper ID resolves to correct paper
2. [ ] Verify every author list matches actual paper
3. [ ] Remove or fix entries that don't match
4. [ ] Add verification_date field to registry schema

---

## Phase 3: Standard Paper Annotation

After anchor papers are complete:
- Use AI-assisted extraction with human verification
- 5-8 claims per paper (not exhaustive)
- Still require source citations
- Spot-check 10% against actual PDFs

---

## Tooling Support

### Verification Script
```bash
# Verify a paper exists at given arXiv ID
curl -s "http://export.arxiv.org/api/query?id_list=ARXIV_ID" | \
  grep -E "<title>|<author>"
```

### PDF Download
```bash
# Download paper from arXiv
wget "https://arxiv.org/pdf/ARXIV_ID.pdf" -O paper.pdf

# Extract text for claim search
pdftotext paper.pdf - | head -500
```

### Claim Citation Template
```json
{
  "claim_id": "PAPER-001-CLM-001",
  "verbatim_text": "Exact quote from paper",
  "source_citation": {
    "page": 5,
    "section": "Results",
    "paragraph": 2,
    "pdf_location": "page 5, right column, lines 15-18"
  },
  "verification": {
    "verified_by": "human_annotator",
    "verified_date": "2025-01-13",
    "method": "PDF inspection"
  }
}
```

---

## Success Criteria

### For Anchor Papers
- [ ] 100% of claims verified against source PDF
- [ ] Every claim has page/section citation
- [ ] Schema validation passes
- [ ] Inter-annotator agreement κ ≥ 0.7

### For Paper Registry
- [ ] Every paper ID verified to resolve correctly
- [ ] Every author list matches actual paper
- [ ] No fabricated entries remain

### For Golden Dataset Overall
- [ ] 5-7 anchor papers with exhaustive annotation
- [ ] 70+ standard papers with representative claims
- [ ] Gap scenarios executable
- [ ] Validation framework tests pass

---

## Timeline Estimate

| Phase | Effort | Calendar Time |
|-------|--------|---------------|
| Anchor Paper 1 | 4-6 hours | Day 1 |
| Anchor Paper 2 | 4-6 hours | Day 2 |
| Anchor Paper 3 | 4-6 hours | Day 3 |
| Anchor Paper 4 | 4-6 hours | Day 4 |
| Anchor Paper 5 | 4-6 hours | Day 5 |
| Registry Cleanup | 2-4 hours | Day 6 |
| Standard Papers (AI-assisted) | 1-2 weeks | Week 2-3 |

---

## Next Steps

1. **Immediate:** Verify CLIMATE-ANCHOR-001 (arXiv:2308.02460)
2. **Today:** Select 5 anchor papers from verified sources
3. **This Week:** Complete exhaustive annotation for first 2 anchor papers
4. **Ongoing:** Develop verification checklist for AI-assisted work
