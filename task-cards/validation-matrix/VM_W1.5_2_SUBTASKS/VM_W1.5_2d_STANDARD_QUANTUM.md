# VM-W1.5-2d: Standard Paper Annotation - Quantum Computing

**Parent Task:** VM-W1.5-2 (Paper Annotation for Golden Dataset)  
**Created:** January 13, 2026  
**Effort:** 3 hours  
**Priority:** HIGH  
**Status:** Not Started  
**Parallelizable:** Yes (with VM-W1.5-2c, 2e-2h)

---

## Overview

Annotate 10 standard papers from the quantum computing domain with 5-8 claims each.

## Prerequisites

| Dependency | Status | Description |
|------------|--------|-------------|
| VM-W1.5-2a | Required | Anchor Neuromorphic (quality baseline) |
| VM-W1.5-2b | Required | Cross-Domain Anchors (methodology validated) |
| VM-W1.5-1B | Required | Paper Registry (quantum papers available) |

## Scope

### Papers to Annotate

10 papers from quantum computing domain:

| Paper ID | Title | Est. Claims | Status |
|----------|-------|-------------|--------|
| QUANTUM-001 | TBD | 5-8 | Not Started |
| QUANTUM-002 | TBD | 5-8 | Not Started |
| QUANTUM-003 | TBD | 5-8 | Not Started |
| QUANTUM-004 | TBD | 5-8 | Not Started |
| QUANTUM-005 | TBD | 5-8 | Not Started |
| QUANTUM-006 | TBD | 5-8 | Not Started |
| QUANTUM-007 | TBD | 5-8 | Not Started |
| QUANTUM-008 | TBD | 5-8 | Not Started |
| QUANTUM-009 | TBD | 5-8 | Not Started |
| QUANTUM-010 | TBD | 5-8 | Not Started |

### Deliverables

1. **Annotated Claims** (50-80 total)
2. **Verdict Distribution**: 50% approved, 30% rejected, 20% borderline
3. **Known Gaps** (20+ total)

## Domain-Specific Focus

### Quantum Computing Claim Types
- **Gate fidelity** claims (e.g., "99.9% two-qubit gate fidelity")
- **Coherence time** claims (e.g., "T2 coherence of 100μs")
- **Qubit count** claims (e.g., "72-qubit processor")
- **Error correction** claims (e.g., "below threshold error rate")
- **Algorithm performance** claims (e.g., "quantum speedup demonstrated")

### Pillar Mapping Guidance
| Claim Type | Likely Pillar |
|------------|---------------|
| Gate fidelity | Hardware Reliability |
| Coherence time | Stability |
| Qubit count | Scalability |
| Error rates | Error Correction |
| Algorithm speedup | Performance |

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
├── QUANTUM-001.json
├── QUANTUM-002.json
├── ... (through QUANTUM-010.json)
```

## Notes

- **Quantum terminology**: Familiarize with common metrics (fidelity, coherence, error rates)
- **Uncertainty language**: Quantum papers often use confidence intervals
- **Cross-reference with QUANTUM-ANCHOR-001**: Use anchor for consistency
