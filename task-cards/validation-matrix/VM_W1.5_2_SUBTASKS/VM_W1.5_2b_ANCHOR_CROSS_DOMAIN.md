# VM-W1.5-2b: Anchor Paper Annotation - Cross-Domain

**Parent Task:** VM-W1.5-2 (Paper Annotation for Golden Dataset)  
**Created:** January 13, 2026  
**Effort:** 4 hours  
**Priority:** HIGH (Establishes cross-domain consistency)  
**Status:** Not Started

---

## Overview

Exhaustively annotate 3-5 anchor papers across multiple domains (Quantum, Microbiology, Climate). This ensures the annotation methodology generalizes beyond the neuromorphic domain and establishes cross-domain consistency.

## Prerequisites

| Dependency | Status | Description |
|------------|--------|-------------|
| VM-W1.5-0 | ✅ PR #142 | Ground Truth Design (schema, protocols) |
| VM-W1.5-2a | Required | Anchor Neuromorphic (methodology validation) |
| VM-W1.5-1B | Required | Paper Registry Population |

## Scope

### Papers to Annotate

| Paper ID | Domain | Title | Source | Est. Claims |
|----------|--------|-------|--------|-------------|
| QUANTUM-ANCHOR-001 | Quantum Computing | TBD | arXiv | 15-30 |
| MICROBIO-ANCHOR-001 | Microbiology | TBD | PMC | 15-30 |
| CLIMATE-ANCHOR-001 | Climate Science | TBD | arXiv/PMC | 15-30 |
| QUANTUM-ANCHOR-002 (optional) | Quantum | TBD | arXiv | 15-30 |
| MICROBIO-ANCHOR-002 (optional) | Microbiology | TBD | PMC | 15-30 |

### Deliverables

1. **Exhaustive Claim Inventory** (45-90 claims total)
   - 3-5 papers × 15-30 claims each
   - All claims classified by extractability
   - Full evidence quality scoring

2. **Non-Extraction Items** (15-45 total)
   - 5-15 per paper across domains
   - Validates FP-01 metric cross-domain

3. **Known Gaps** (30+ total)
   - Domain-specific gaps identified
   - Cross-domain gap patterns documented

4. **Cross-Domain Consistency Check**
   - Compare annotation quality with VM-W1.5-2a
   - Document any domain-specific annotation challenges

## Annotation Workflow

Same workflow as VM-W1.5-2a, with additional cross-domain validation:

```
┌─────────────────────────────────────────────────────────────┐
│                   Phase 1: Setup (30 min)                   │
├─────────────────────────────────────────────────────────────┤
│ 1. Select 1 paper from each domain: Quantum, Micro, Climate│
│ 2. Verify PDF availability and quality                     │
│ 3. Review VM-W1.5-2a annotations for consistency reference │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Phase 2: Exhaustive Pass (3h)                  │
├─────────────────────────────────────────────────────────────┤
│ For each paper:                                             │
│   1. Read entire paper identifying ALL potential claims     │
│   2. Apply same extractability classification scheme        │
│   3. Note any domain-specific challenges                    │
│   4. Document gaps relevant to domain pillar requirements   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         Phase 3: Cross-Domain Validation (30 min)          │
├─────────────────────────────────────────────────────────────┤
│ 1. Compare verdict distributions across domains            │
│ 2. Verify evidence quality scoring consistency             │
│ 3. Document domain-specific patterns                       │
│ 4. Run annotate_paper.py validate for all papers          │
└─────────────────────────────────────────────────────────────┘
```

## Output Files

| File | Domain | Purpose |
|------|--------|---------|
| `annotations/QUANTUM-ANCHOR-001.json` | Quantum | Anchor annotation |
| `annotations/MICROBIO-ANCHOR-001.json` | Microbiology | Anchor annotation |
| `annotations/CLIMATE-ANCHOR-001.json` | Climate | Anchor annotation |

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| Papers annotated | 3-5 | Count in annotations/ |
| Domains covered | 3 minimum | Quantum, Microbio, Climate |
| Claims per paper | 15-30 | JSON statistics |
| Non-extraction items | 5-15 per paper | JSON count |
| Gaps documented | 10+ per paper | JSON count |
| Schema valid | 100% | `annotate_paper.py validate` |
| Cross-domain consistency | Documented | Variance in scoring documented |

## Domain-Specific Considerations

### Quantum Computing
- Look for: Qubit counts, gate fidelities, coherence times
- Challenge: Highly technical terminology
- Pillar focus: Scalability, Energy Efficiency

### Microbiology
- Look for: Expression levels, growth rates, assay results
- Challenge: Statistical reporting variations
- Pillar focus: Biological Safety, Reproducibility

### Climate Science
- Look for: Temperature projections, model accuracy, confidence intervals
- Challenge: Uncertainty quantification language
- Pillar focus: Environmental Impact, Prediction Accuracy

## Notes

- **Apply lessons from VM-W1.5-2a**: Use insights from neuromorphic annotation
- **Document domain differences**: Note any scoring challenges
- **Maintain consistency**: Use same extractability thresholds across domains
- **Prioritize diversity**: Ensure different evidence types are represented
