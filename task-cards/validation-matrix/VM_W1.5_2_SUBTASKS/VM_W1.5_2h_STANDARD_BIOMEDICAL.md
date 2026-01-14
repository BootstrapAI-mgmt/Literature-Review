# VM-W1.5-2h: Standard Paper Annotation - Biomedical Imaging

**Parent Task:** VM-W1.5-2 (Paper Annotation for Golden Dataset)  
**Created:** January 13, 2026  
**Effort:** 3 hours  
**Priority:** HIGH  
**Status:** Not Started  
**Parallelizable:** Yes (with VM-W1.5-2c-2g)

---

## Overview

Annotate 10 standard papers from the biomedical imaging domain with 5-8 claims each.

## Prerequisites

| Dependency | Status | Description |
|------------|--------|-------------|
| VM-W1.5-2a | Required | Anchor Neuromorphic (quality baseline) |
| VM-W1.5-2b | Required | Cross-Domain Anchors (methodology validated) |
| VM-W1.5-1B | Required | Paper Registry (biomedical papers available) |

## Scope

### Papers to Annotate

10 papers from biomedical imaging domain:

| Paper ID | Title | Est. Claims | Status |
|----------|-------|-------------|--------|
| BIOMED-001 | TBD | 5-8 | Not Started |
| BIOMED-002 | TBD | 5-8 | Not Started |
| BIOMED-003 | TBD | 5-8 | Not Started |
| BIOMED-004 | TBD | 5-8 | Not Started |
| BIOMED-005 | TBD | 5-8 | Not Started |
| BIOMED-006 | TBD | 5-8 | Not Started |
| BIOMED-007 | TBD | 5-8 | Not Started |
| BIOMED-008 | TBD | 5-8 | Not Started |
| BIOMED-009 | TBD | 5-8 | Not Started |
| BIOMED-010 | TBD | 5-8 | Not Started |

### Deliverables

1. **Annotated Claims** (50-80 total)
2. **Verdict Distribution**: 50% approved, 30% rejected, 20% borderline
3. **Known Gaps** (20+ total)

## Domain-Specific Focus

### Biomedical Imaging Claim Types
- **Accuracy** claims (e.g., "95% classification accuracy")
- **Sensitivity/Specificity** claims (e.g., "sensitivity 92%, specificity 88%")
- **Resolution** claims (e.g., "sub-micron resolution achieved")
- **Speed** claims (e.g., "real-time imaging at 30 fps")
- **Comparison** claims (e.g., "outperforms MRI by 15%")
- **Clinical validation** claims (e.g., "validated on 500 patient cases")

### Pillar Mapping Guidance
| Claim Type | Likely Pillar |
|------------|---------------|
| Accuracy | Diagnostic Accuracy |
| Sensitivity/Specificity | Clinical Validity |
| Resolution | Image Quality |
| Speed | Efficiency |
| Comparison | Benchmarking |
| Clinical validation | Safety/Efficacy |

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
├── BIOMED-001.json
├── BIOMED-002.json
├── ... (through BIOMED-010.json)
```

## Notes

- **No anchor paper**: Use cross-domain methodology reference
- **Clinical terminology**: Familiarize with sensitivity, specificity, AUC
- **Regulatory context**: May reference FDA/CE approval claims
- **Dataset mentions**: Note if public datasets are used (supports reproducibility scoring)
