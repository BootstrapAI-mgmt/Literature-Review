# VM-W1.5-2j: Annotation Merge & Validation

**Parent Task:** VM-W1.5-2 (Paper Annotation for Golden Dataset)  
**Created:** January 13, 2026  
**Effort:** 2 hours  
**Priority:** HIGH  
**Status:** Not Started

---

## Overview

Merge all annotations from sub-tasks 2a-2i into a unified golden dataset and validate completeness, quality, and schema compliance.

## Prerequisites

| Dependency | Status | Description |
|------------|--------|-------------|
| VM-W1.5-2a | Required | Anchor Neuromorphic annotations |
| VM-W1.5-2b | Required | Anchor Cross-Domain annotations |
| VM-W1.5-2c | Required | Standard Neuromorphic annotations |
| VM-W1.5-2d | Required | Standard Quantum annotations |
| VM-W1.5-2e | Required | Standard Microbiology annotations |
| VM-W1.5-2f | Required | Standard Fusion/Nano annotations |
| VM-W1.5-2g | Required | Standard Climate/Materials annotations |
| VM-W1.5-2h | Required | Standard Biomedical annotations |
| VM-W1.5-2i | Required | Gap scenarios and decoy annotations |

## Scope

### Merge Operations

1. **Combine all annotation files** into unified datasets:
   - `real_paper_claims.json` - All claims from real papers
   - `anchor_papers.json` - Exhaustive anchor annotations
   - `gap_scenarios.json` - Scenario definitions
   - `decoy_papers.json` - Decoy paper annotations

2. **Generate golden dataset v2.0**:
   - Merge synthetic claims (VM-W1-4) with real paper claims
   - Tag source type for each claim (synthetic vs real_paper)
   - Update version metadata

### Validation Checks

1. **Volume targets**
2. **Distribution balance**
3. **Schema compliance**
4. **Coverage verification**

## Expected Totals

Based on sub-task deliverables:

| Category | Sub-tasks | Expected Count |
|----------|-----------|----------------|
| **Anchor Claims** | 2a + 2b | 75-150 |
| **Standard Claims** | 2c-2h | 350-560 |
| **Total Claims** | All | 425-710 |
| **Non-extraction items** | 2a + 2b | 50+ |
| **Known Gaps** | All | 160+ |
| **Gap Scenarios** | 2i | 3+ |
| **Decoy Papers** | 2i | 5+ |

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                Phase 1: Collection (30 min)                 │
├─────────────────────────────────────────────────────────────┤
│ 1. Verify all annotation files present                     │
│ 2. Run annotate_paper.py status for inventory              │
│ 3. Document any missing files                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Phase 2: Merge (45 min)                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Run annotate_paper.py merge                             │
│ 2. Generate real_paper_claims.json                         │
│ 3. Merge with synthetic dataset → golden_dataset_v2.json   │
│ 4. Tag all claims with source_type                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               Phase 3: Validation (30 min)                  │
├─────────────────────────────────────────────────────────────┤
│ 1. Run annotate_paper.py validate                          │
│ 2. Check volume targets (table below)                      │
│ 3. Verify verdict distribution                             │
│ 4. Verify domain distribution                              │
│ 5. Check gap scenario completeness                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            Phase 4: Quality Report (15 min)                 │
├─────────────────────────────────────────────────────────────┤
│ 1. Generate annotation quality report                      │
│ 2. Document any issues found                               │
│ 3. Update paper registry with annotation status            │
│ 4. Create ANNOTATION_SUMMARY.md                            │
└─────────────────────────────────────────────────────────────┘
```

## Validation Criteria

### Volume Targets

| Criterion | Target | Threshold | Pass/Fail |
|-----------|--------|-----------|-----------|
| Total Claims | 400+ | ≥400 | |
| Per-Paper Average | 5-8 | ≥5 | |
| Anchor Claims | 75-150 | ≥75 | |
| Standard Claims | 350+ | ≥350 | |
| Non-extraction Items | 50+ | ≥50 | |
| Known Gaps | 160+ | ≥160 | |
| Gap Scenarios | 3+ | ≥3 | |
| Decoy Papers | 5+ | ≥5 | |

### Distribution Targets

| Criterion | Target | Threshold | Pass/Fail |
|-----------|--------|-----------|-----------|
| Approved Ratio | 45-55% | 40-60% | |
| Rejected Ratio | 25-35% | 20-40% | |
| Borderline Ratio | 15-25% | 10-30% | |
| Domain Variance | ≤10% | ≤15% | |

### Schema Compliance

| Check | Target | Pass/Fail |
|-------|--------|-----------|
| All claims valid | 100% | |
| All gaps valid | 100% | |
| All scenarios valid | 100% | |
| Required fields present | 100% | |

## Output Files

| File | Purpose |
|------|---------|
| `tests/golden_dataset/data/real_paper_claims.json` | Merged real paper annotations |
| `tests/golden_dataset/data/golden_dataset_v2.json` | Full merged dataset (synthetic + real) |
| `tests/golden_dataset/data/anchor_papers.json` | Anchor paper inventory |
| `tests/golden_dataset/scenarios/` | Gap scenario definitions |
| `tests/golden_dataset/ANNOTATION_SUMMARY.md` | Quality report |

## Merge Script

```python
# annotate_paper.py merge implementation
def merge_annotations():
    """Merge all annotations into unified dataset."""
    annotations_dir = Path("tests/golden_dataset/annotations")
    
    all_claims = []
    all_gaps = []
    all_recommendations = []
    anchor_papers = []
    decoy_papers = []
    
    for file in annotations_dir.glob("*.json"):
        with open(file) as f:
            data = json.load(f)
        
        # Categorize by type
        if data.get("annotation_type") == "exhaustive":
            anchor_papers.append(data)
        elif data.get("is_decoy"):
            decoy_papers.append(data)
        
        all_claims.extend(data.get("claims", []))
        all_gaps.extend(data.get("gaps", []))
        all_recommendations.extend(data.get("recommendations", []))
    
    # Generate merged files
    # ...
```

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| All sub-tasks merged | 2a-2i | All files present |
| Volume targets met | All pass | Validation report |
| Distribution targets met | All pass | Validation report |
| Schema valid | 100% | annotate_paper.py validate |
| golden_dataset_v2.json created | Exists | File verification |
| ANNOTATION_SUMMARY.md created | Exists | Report generation |

## Notes

- **Final gate**: This is the last step before annotations are usable
- **Fix issues**: Any validation failures should be traced to source sub-task
- **Version control**: Commit merged datasets to repository
- **Cross-reference VM-W1.5-3**: Gap Scenario Execution uses these files
