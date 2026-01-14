# VM-W1.5-2a: Anchor Paper Annotation - Neuromorphic Domain

**Parent Task:** VM-W1.5-2 (Paper Annotation for Golden Dataset)  
**Created:** January 13, 2026  
**Effort:** 3 hours  
**Priority:** CRITICAL (First batch - sets annotation standards)  
**Status:** Not Started

---

## Overview

Exhaustively annotate 2-3 anchor papers from the neuromorphic computing domain. These anchor papers establish the gold standard annotation quality and are used to validate that the extraction pipeline finds ALL extractable claims.

## Prerequisites

| Dependency | Status | Description |
|------------|--------|-------------|
| VM-W1.5-0 | ✅ PR #142 | Ground Truth Design (schema, protocols) |
| VM-W1.5-1 | ✅ Complete | Paper Sourcing Infrastructure |
| VM-W1.5-1B | Required | Paper Registry Population (neuromorphic papers) |

## Scope

### Papers to Annotate

| Paper ID | Title | Source | Est. Claims |
|----------|-------|--------|-------------|
| NEURO-ANCHOR-001 | TBD from paper registry | arXiv/PMC | 15-30 |
| NEURO-ANCHOR-002 | TBD from paper registry | arXiv/PMC | 15-30 |
| NEURO-ANCHOR-003 (optional) | TBD from paper registry | arXiv/PMC | 15-30 |

### Deliverables

1. **Exhaustive Claim Inventory** (30-60 claims total)
   - ALL quantitative claims extracted
   - Each claim classified by extractability (HIGH/MEDIUM/LOW/IRRELEVANT)
   - Full evidence quality scoring (strength, rigor, relevance, directness, reproducibility)

2. **Non-Extraction Items** (5-15 per paper)
   - Statements that look like claims but should NOT be extracted
   - Document why each is not extractable
   - Use for false positive testing (FP-01)

3. **Known Gaps** (10+ per paper)
   - Requirements the paper does NOT address
   - Verified by domain expert or careful analysis

4. **Inter-Rater Agreement** (if dual annotator)
   - Target: Cohen's κ ≥ 0.7
   - Document disagreements and resolutions

## Annotation Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                   Phase 1: Setup (30 min)                   │
├─────────────────────────────────────────────────────────────┤
│ 1. Select papers from paper_registry.json (neuromorphic)   │
│ 2. Verify PDF availability and quality                     │
│ 3. Create annotation session: annotate_paper.py start      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Phase 2: Exhaustive Pass (2h)                │
├─────────────────────────────────────────────────────────────┤
│ For each paper:                                             │
│   1. Read entire paper identifying ALL potential claims     │
│   2. Classify each by extractability:                       │
│      - HIGH: Clear quantitative claim with evidence         │
│      - MEDIUM: Needs inference, partial evidence            │
│      - LOW: Vague, qualitative only                         │
│      - IRRELEVANT: Not a claim (background, opinion)        │
│   3. For HIGH/MEDIUM: Full annotation with scores           │
│   4. For LOW/IRRELEVANT: Add to non_extraction_items        │
│   5. Document all gaps found                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Phase 3: Validation (30 min)                   │
├─────────────────────────────────────────────────────────────┤
│ 1. Run annotate_paper.py validate                          │
│ 2. Verify schema compliance                                 │
│ 3. Check verdict distribution (aim for balance)            │
│ 4. Export: annotate_paper.py export                        │
└─────────────────────────────────────────────────────────────┘
```

## Output Schema

Each annotated paper produces:

```json
{
  "paper_id": "NEURO-ANCHOR-001",
  "annotation_type": "exhaustive",
  "domain": "neuromorphic",
  "annotator_id": "annotator_001",
  "annotation_date": "2026-01-XX",
  "claims": [
    {
      "claim_id": "NEURO-ANCHOR-001-CLM-001",
      "extractability": "HIGH",
      "claim_text": "...",
      "evidence_text": "...",
      "correct_pillar": "Energy Efficiency",
      "expected_verdict": "approved",
      "evidence_quality": { ... }
    }
  ],
  "non_extraction_items": [
    {
      "item_id": "NEURO-ANCHOR-001-NEI-001",
      "text": "Future work will explore...",
      "location": "Section 5, Page 8",
      "reason": "future_work"
    }
  ],
  "gaps": [...],
  "statistics": {
    "total_claims": 25,
    "high_extractability": 15,
    "medium_extractability": 7,
    "low_extractability": 3,
    "non_extraction_items": 12
  }
}
```

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| Papers annotated | 2-3 | Count in annotations/ |
| Claims per paper | 15-30 | JSON statistics |
| Non-extraction items | 5-15 per paper | JSON count |
| Gaps documented | 10+ per paper | JSON count |
| Schema valid | 100% | `annotate_paper.py validate` |
| Extractability classified | 100% claims | All claims have extractability |

## Files to Create/Update

| File | Action | Purpose |
|------|--------|---------|
| `tests/golden_dataset/annotations/NEURO-ANCHOR-001.json` | Create | First anchor annotation |
| `tests/golden_dataset/annotations/NEURO-ANCHOR-002.json` | Create | Second anchor annotation |
| `tests/golden_dataset/data/anchor_papers.json` | Update | Add to anchor paper registry |

## Notes

- **Quality over speed**: Take time to capture every claim accurately
- **Document edge cases**: Note any annotation decisions for guideline refinement
- **Use EXHAUSTIVE_ANNOTATION_PROTOCOL.md**: Follow the protocol from VM-W1.5-0
- **Cross-reference with ANCHOR_PAPER_CRITERIA.md**: Ensure papers meet anchor criteria
