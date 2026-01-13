# VM-W1.5-2g: Standard Paper Annotation - Climate & Materials

**Parent Task:** VM-W1.5-2 (Paper Annotation for Golden Dataset)  
**Created:** January 13, 2026  
**Effort:** 4 hours  
**Priority:** HIGH  
**Status:** Not Started  
**Parallelizable:** Yes (with VM-W1.5-2c-2f, 2h)

---

## Overview

Annotate 20 standard papers across Climate Science (10) and Materials Science (10) domains with 5-8 claims each.

## Prerequisites

| Dependency | Status | Description |
|------------|--------|-------------|
| VM-W1.5-2a | Required | Anchor Neuromorphic (quality baseline) |
| VM-W1.5-2b | Required | Cross-Domain Anchors (includes CLIMATE-ANCHOR-001) |
| VM-W1.5-1B | Required | Paper Registry (climate/materials papers available) |

## Scope

### Climate Science Papers (10)

| Paper ID | Title | Est. Claims | Status |
|----------|-------|-------------|--------|
| CLIMATE-001 | TBD | 5-8 | Not Started |
| CLIMATE-002 | TBD | 5-8 | Not Started |
| CLIMATE-003 | TBD | 5-8 | Not Started |
| CLIMATE-004 | TBD | 5-8 | Not Started |
| CLIMATE-005 | TBD | 5-8 | Not Started |
| CLIMATE-006 | TBD | 5-8 | Not Started |
| CLIMATE-007 | TBD | 5-8 | Not Started |
| CLIMATE-008 | TBD | 5-8 | Not Started |
| CLIMATE-009 | TBD | 5-8 | Not Started |
| CLIMATE-010 | TBD | 5-8 | Not Started |

### Materials Science Papers (10)

| Paper ID | Title | Est. Claims | Status |
|----------|-------|-------------|--------|
| MATERIAL-001 | TBD | 5-8 | Not Started |
| MATERIAL-002 | TBD | 5-8 | Not Started |
| MATERIAL-003 | TBD | 5-8 | Not Started |
| MATERIAL-004 | TBD | 5-8 | Not Started |
| MATERIAL-005 | TBD | 5-8 | Not Started |
| MATERIAL-006 | TBD | 5-8 | Not Started |
| MATERIAL-007 | TBD | 5-8 | Not Started |
| MATERIAL-008 | TBD | 5-8 | Not Started |
| MATERIAL-009 | TBD | 5-8 | Not Started |
| MATERIAL-010 | TBD | 5-8 | Not Started |

### Deliverables

1. **Annotated Claims** (100-160 total)
   - 50-80 from Climate Science
   - 50-80 from Materials Science
2. **Verdict Distribution**: 50% approved, 30% rejected, 20% borderline
3. **Known Gaps** (40+ total)

## Domain-Specific Focus

### Climate Science Claim Types
- **Temperature projections** (e.g., "2.5°C warming by 2100")
- **Model accuracy** claims (e.g., "RMSE of 0.5K")
- **Emission estimates** (e.g., "50Gt CO2 per year")
- **Attribution** claims (e.g., "95% confidence human-caused")
- **Impact projections** (e.g., "30% more extreme events")

### Materials Science Claim Types
- **Mechanical properties** (e.g., "tensile strength 500 MPa")
- **Thermal properties** (e.g., "thermal conductivity 150 W/mK")
- **Electrical properties** (e.g., "resistivity 10⁻⁶ Ω·m")
- **Durability** claims (e.g., "10,000 cycle fatigue life")
- **Novel material** claims (e.g., "first synthesis of...")

### Pillar Mapping Guidance

**Climate:**
| Claim Type | Likely Pillar |
|------------|---------------|
| Temperature projections | Prediction Accuracy |
| Model accuracy | Validation |
| Emission estimates | Environmental Impact |
| Attribution | Confidence |

**Materials:**
| Claim Type | Likely Pillar |
|------------|---------------|
| Mechanical properties | Performance |
| Thermal properties | Efficiency |
| Electrical properties | Functionality |
| Durability | Reliability |

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
├── CLIMATE-001.json through CLIMATE-010.json
├── MATERIAL-001.json through MATERIAL-010.json
```

## Notes

- **Climate has anchor**: Use CLIMATE-ANCHOR-001 from VM-W1.5-2b for consistency
- **Materials no anchor**: Use cross-domain methodology reference
- **Uncertainty quantification**: Climate papers often use confidence intervals
- **Materials terminology**: Familiarize with standard property units
