# VM-W1.5-2c: Standard Paper Annotation - Neuromorphic

**Parent Task:** VM-W1.5-2 (Paper Annotation for Golden Dataset)  
**Created:** January 13, 2026  
**Effort:** 3 hours  
**Priority:** HIGH  
**Status:** Not Started  
**Parallelizable:** Yes (with VM-W1.5-2d through VM-W1.5-2h)

---

## Overview

Annotate 8 standard papers from the neuromorphic computing domain with 5-8 claims each. This complements the exhaustive anchor annotations with volume coverage for robust testing.

## Prerequisites

| Dependency | Status | Description |
|------------|--------|-------------|
| VM-W1.5-2a | Required | Anchor Neuromorphic (quality baseline) |
| VM-W1.5-2b | Required | Cross-Domain Anchors (methodology validated) |
| VM-W1.5-1B | Required | Paper Registry (neuromorphic papers available) |

## Scope

### Papers to Annotate

8 papers from neuromorphic domain (excluding anchor papers):

| Paper ID | Title | Est. Claims | Status |
|----------|-------|-------------|--------|
| NEURO-001 | TBD | 5-8 | Not Started |
| NEURO-002 | TBD | 5-8 | Not Started |
| NEURO-003 | TBD | 5-8 | Not Started |
| NEURO-004 | TBD | 5-8 | Not Started |
| NEURO-005 | TBD | 5-8 | Not Started |
| NEURO-006 | TBD | 5-8 | Not Started |
| NEURO-007 | TBD | 5-8 | Not Started |
| NEURO-008 | TBD | 5-8 | Not Started |

### Deliverables

1. **Annotated Claims** (40-64 total)
   - 8 papers × 5-8 claims each
   - Focus on HIGH extractability claims
   - Full evidence quality scoring

2. **Verdict Distribution**
   - Target: 50% approved, 30% rejected, 20% borderline
   - At least 1 borderline claim per 3 papers

3. **Known Gaps** (16+ total)
   - 2+ gaps per paper

## Annotation Workflow

```
┌─────────────────────────────────────────────────────────────┐
│            Standard Annotation (20-25 min/paper)            │
├─────────────────────────────────────────────────────────────┤
│ 1. Skim paper for key claims (Abstract, Results, Conclusion)│
│ 2. Select 5-8 strongest quantitative claims                │
│ 3. Score evidence quality for each                         │
│ 4. Assign expected verdict                                  │
│ 5. Document 2+ gaps                                         │
│ 6. Export annotation JSON                                   │
└─────────────────────────────────────────────────────────────┘
```

## Quality Guidelines

### Claim Selection Priority
1. **Quantitative performance claims** (accuracy, speed, efficiency)
2. **Comparative claims** (vs baseline, vs prior work)
3. **Novel contribution claims** (first to achieve X)
4. **Reproducibility claims** (open source, dataset available)

### Evidence Quality Quick Reference

| Score | Strength | Rigor | Relevance |
|-------|----------|-------|-----------|
| 5 | Meta-analysis | Gold standard | Exact match |
| 4 | Multiple studies | Statistical tests | Direct comparison |
| 3 | Single study | Standard methods | Related task |
| 2 | Single observation | Incomplete methods | Loosely related |
| 1 | Anecdotal | No methodology | Tangential |

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| Papers annotated | 8 | Count in annotations/ |
| Claims per paper | 5-8 | Average ≥6 |
| Total claims | 40-64 | Sum across papers |
| Approved ratio | 45-55% | Verdict distribution |
| Rejected ratio | 25-35% | Verdict distribution |
| Borderline claims | ≥3 | At least 1 per 3 papers |
| Gaps per paper | 2+ | Total ≥16 |
| Schema valid | 100% | `annotate_paper.py validate` |

## Output Files

```
tests/golden_dataset/annotations/
├── NEURO-001.json
├── NEURO-002.json
├── NEURO-003.json
├── NEURO-004.json
├── NEURO-005.json
├── NEURO-006.json
├── NEURO-007.json
└── NEURO-008.json
```

## Notes

- **Faster than anchors**: Standard annotation is ~20-25 min vs 60-90 min for exhaustive
- **Focus on extractable claims**: Skip LOW/IRRELEVANT content
- **Maintain quality**: Use same scoring rigor as anchor papers
- **Parallel execution**: Can run alongside VM-W1.5-2d through VM-W1.5-2h
