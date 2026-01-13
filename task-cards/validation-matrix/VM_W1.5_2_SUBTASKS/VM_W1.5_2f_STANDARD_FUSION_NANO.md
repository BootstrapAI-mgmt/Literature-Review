# VM-W1.5-2f: Standard Paper Annotation - Fusion & Nanoparticle

**Parent Task:** VM-W1.5-2 (Paper Annotation for Golden Dataset)  
**Created:** January 13, 2026  
**Effort:** 4 hours  
**Priority:** HIGH  
**Status:** Not Started  
**Parallelizable:** Yes (with VM-W1.5-2c-2e, 2g-2h)

---

## Overview

Annotate 20 standard papers across Fusion Energy (10) and Nanoparticle Heat Transfer (10) domains with 5-8 claims each. These domains do not have anchor papers, so extra care is needed for consistency.

## Prerequisites

| Dependency | Status | Description |
|------------|--------|-------------|
| VM-W1.5-2a | Required | Anchor Neuromorphic (quality baseline) |
| VM-W1.5-2b | Required | Cross-Domain Anchors (methodology validated) |
| VM-W1.5-1B | Required | Paper Registry (fusion/nano papers available) |

## Scope

### Fusion Energy Papers (10)

| Paper ID | Title | Est. Claims | Status |
|----------|-------|-------------|--------|
| FUSION-001 | TBD | 5-8 | Not Started |
| FUSION-002 | TBD | 5-8 | Not Started |
| FUSION-003 | TBD | 5-8 | Not Started |
| FUSION-004 | TBD | 5-8 | Not Started |
| FUSION-005 | TBD | 5-8 | Not Started |
| FUSION-006 | TBD | 5-8 | Not Started |
| FUSION-007 | TBD | 5-8 | Not Started |
| FUSION-008 | TBD | 5-8 | Not Started |
| FUSION-009 | TBD | 5-8 | Not Started |
| FUSION-010 | TBD | 5-8 | Not Started |

### Nanoparticle Heat Transfer Papers (10)

| Paper ID | Title | Est. Claims | Status |
|----------|-------|-------------|--------|
| NANO-001 | TBD | 5-8 | Not Started |
| NANO-002 | TBD | 5-8 | Not Started |
| NANO-003 | TBD | 5-8 | Not Started |
| NANO-004 | TBD | 5-8 | Not Started |
| NANO-005 | TBD | 5-8 | Not Started |
| NANO-006 | TBD | 5-8 | Not Started |
| NANO-007 | TBD | 5-8 | Not Started |
| NANO-008 | TBD | 5-8 | Not Started |
| NANO-009 | TBD | 5-8 | Not Started |
| NANO-010 | TBD | 5-8 | Not Started |

### Deliverables

1. **Annotated Claims** (100-160 total)
   - 50-80 from Fusion
   - 50-80 from Nanoparticle
2. **Verdict Distribution**: 50% approved, 30% rejected, 20% borderline
3. **Known Gaps** (40+ total)

## Domain-Specific Focus

### Fusion Energy Claim Types
- **Plasma confinement** claims (e.g., "H-mode sustained for 10s")
- **Energy gain** claims (e.g., "Q > 1 achieved")
- **Temperature** claims (e.g., "100M degrees Celsius plasma")
- **Stability** claims (e.g., "ELM-free operation")

### Nanoparticle Heat Transfer Claim Types
- **Thermal conductivity** claims (e.g., "40% enhancement vs base fluid")
- **Heat transfer coefficient** claims
- **Particle concentration** effects
- **Stability** claims (e.g., "stable for 30 days")

### Pillar Mapping Guidance

**Fusion:**
| Claim Type | Likely Pillar |
|------------|---------------|
| Confinement | Stability |
| Energy gain | Efficiency |
| Temperature | Performance |
| Stability | Reliability |

**Nanoparticle:**
| Claim Type | Likely Pillar |
|------------|---------------|
| Thermal conductivity | Performance |
| Heat transfer | Efficiency |
| Concentration effects | Optimization |
| Stability | Durability |

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| Papers annotated | 20 | Count in annotations/ |
| Claims per paper | 5-8 | Average ≥6 |
| Total claims | 100-160 | Sum across papers |
| Gaps documented | 40+ | Total across papers |
| Schema valid | 100% | `annotate_paper.py validate` |

## Output Files

```
tests/golden_dataset/annotations/
├── FUSION-001.json through FUSION-010.json
├── NANO-001.json through NANO-010.json
```

## Notes

- **No anchor papers**: Extra care for consistency without domain anchor
- **Use cross-domain anchors**: Reference VM-W1.5-2b for methodology
- **Larger batch**: 20 papers total - maintain focus and quality
- **Domain separation**: Consider doing Fusion first, then Nano, for consistency within domain
