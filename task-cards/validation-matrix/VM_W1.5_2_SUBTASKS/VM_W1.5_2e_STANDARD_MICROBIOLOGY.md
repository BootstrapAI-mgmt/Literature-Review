# VM-W1.5-2e: Standard Paper Annotation - Microbiology

**Parent Task:** VM-W1.5-2 (Paper Annotation for Golden Dataset)  
**Created:** January 13, 2026  
**Effort:** 3 hours  
**Priority:** HIGH  
**Status:** Not Started  
**Parallelizable:** Yes (with VM-W1.5-2c, 2d, 2f-2h)

---

## Overview

Annotate 10 standard papers from the microbiology domain with 5-8 claims each.

## Prerequisites

| Dependency | Status | Description |
|------------|--------|-------------|
| VM-W1.5-2a | Required | Anchor Neuromorphic (quality baseline) |
| VM-W1.5-2b | Required | Cross-Domain Anchors (methodology validated) |
| VM-W1.5-1B | Required | Paper Registry (microbiology papers available) |

## Scope

### Papers to Annotate

10 papers from microbiology domain:

| Paper ID | Title | Est. Claims | Status |
|----------|-------|-------------|--------|
| MICROBIO-001 | TBD | 5-8 | Not Started |
| MICROBIO-002 | TBD | 5-8 | Not Started |
| MICROBIO-003 | TBD | 5-8 | Not Started |
| MICROBIO-004 | TBD | 5-8 | Not Started |
| MICROBIO-005 | TBD | 5-8 | Not Started |
| MICROBIO-006 | TBD | 5-8 | Not Started |
| MICROBIO-007 | TBD | 5-8 | Not Started |
| MICROBIO-008 | TBD | 5-8 | Not Started |
| MICROBIO-009 | TBD | 5-8 | Not Started |
| MICROBIO-010 | TBD | 5-8 | Not Started |

### Deliverables

1. **Annotated Claims** (50-80 total)
2. **Verdict Distribution**: 50% approved, 30% rejected, 20% borderline
3. **Known Gaps** (20+ total)

## Domain-Specific Focus

### Microbiology Claim Types
- **Expression level** claims (e.g., "3-fold increase in protein expression")
- **Growth rate** claims (e.g., "doubling time of 45 minutes")
- **Assay results** claims (e.g., "IC50 of 2.5 μM")
- **Statistical significance** claims (e.g., "p < 0.001")
- **Reproducibility** claims (e.g., "results replicated across 3 labs")

### Pillar Mapping Guidance
| Claim Type | Likely Pillar |
|------------|---------------|
| Expression levels | Efficacy |
| Growth rates | Viability |
| Assay results | Safety/Toxicity |
| Statistical significance | Reproducibility |
| Lab replication | Validation |

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| Papers annotated | 10 | Count in annotations/ |
| Claims per paper | 5-8 | Average ≥6 |
| Total claims | 50-80 | Sum across papers |
| Gaps documented | 20+ | Total across papers |
| Schema valid | 100% | `annotate_paper.py validate` |

## Output Files

```
tests/golden_dataset/annotations/
├── MICROBIO-001.json
├── MICROBIO-002.json
├── ... (through MICROBIO-010.json)
```

## Notes

- **Statistical language**: Microbiology papers often use p-values, confidence intervals
- **Methodology details**: Pay attention to sample sizes, controls
- **Cross-reference with MICROBIO-ANCHOR-001**: Use anchor for consistency
