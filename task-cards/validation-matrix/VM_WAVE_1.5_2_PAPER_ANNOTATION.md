# VM-W1.5-2: Paper Annotation for Golden Dataset

**Status:** Decomposed into Sub-Tasks  
**Created:** January 13, 2026  
**Total Effort:** 28 hours  
**Priority:** HIGH

---

## Overview

This task has been decomposed into 10 sub-tasks to ensure manageable scope and quality execution. The original monolithic task card has been archived.

## Sub-Task Structure

```
                    ┌─────────────────┐
                    │   VM-W1.5-2a    │ Anchor Papers - Neuromorphic (3h)
                    │   (Anchors-NM)  │ 2-3 papers, exhaustive annotation
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   VM-W1.5-2b    │ Anchor Papers - Cross-Domain (4h)
                    │   (Anchors-XD)  │ 3-5 papers: Quantum, Micro, Climate
                    └────────┬────────┘
                             │
    ┌──────────┬──────────┬──┴──┬──────────┬──────────┐
    ▼          ▼          ▼     ▼          ▼          ▼
 VM-W1.5-2c VM-W1.5-2d VM-W1.5-2e VM-W1.5-2f VM-W1.5-2g VM-W1.5-2h
 (NM std)   (Quantum)  (Micro)   (Fus/Nano) (Clim/Mat) (Biomed)
   3h         3h         3h        4h         4h         3h
    │          │          │        │          │          │
    └──────────┴──────────┴────┬───┴──────────┴──────────┘
                               │
                    ┌──────────▼──────────┐
                    │     VM-W1.5-2i      │ Gap Scenario Design (3h)
                    │  (Gap Scenarios)    │ 3+ scenarios, 5+ decoys
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │     VM-W1.5-2j      │ Merge & Validation (2h)
                    │  (Merge/Validate)   │ Final dataset generation
                    └─────────────────────┘
```

## Sub-Task Index

| ID | Name | Effort | Papers | Claims | Status |
|----|------|--------|--------|--------|--------|
| [VM-W1.5-2a](VM_W1.5_2_SUBTASKS/VM_W1.5_2a_ANCHOR_NEUROMORPHIC.md) | Anchor Neuromorphic | 3h | 2-3 | 30-60 | Not Started |
| [VM-W1.5-2b](VM_W1.5_2_SUBTASKS/VM_W1.5_2b_ANCHOR_CROSS_DOMAIN.md) | Anchor Cross-Domain | 4h | 3-5 | 45-90 | Not Started |
| [VM-W1.5-2c](VM_W1.5_2_SUBTASKS/VM_W1.5_2c_STANDARD_NEUROMORPHIC.md) | Standard Neuromorphic | 3h | 8 | 40-64 | Not Started |
| [VM-W1.5-2d](VM_W1.5_2_SUBTASKS/VM_W1.5_2d_STANDARD_QUANTUM.md) | Standard Quantum | 3h | 10 | 50-80 | Not Started |
| [VM-W1.5-2e](VM_W1.5_2_SUBTASKS/VM_W1.5_2e_STANDARD_MICROBIOLOGY.md) | Standard Microbiology | 3h | 10 | 50-80 | Not Started |
| [VM-W1.5-2f](VM_W1.5_2_SUBTASKS/VM_W1.5_2f_STANDARD_FUSION_NANO.md) | Standard Fusion/Nano | 4h | 20 | 100-160 | Not Started |
| [VM-W1.5-2g](VM_W1.5_2_SUBTASKS/VM_W1.5_2g_STANDARD_CLIMATE_MATERIALS.md) | Standard Climate/Materials | 4h | 20 | 100-160 | Not Started |
| [VM-W1.5-2h](VM_W1.5_2_SUBTASKS/VM_W1.5_2h_STANDARD_BIOMEDICAL.md) | Standard Biomedical | 3h | 10 | 50-80 | Not Started |
| [VM-W1.5-2i](VM_W1.5_2_SUBTASKS/VM_W1.5_2i_GAP_SCENARIOS.md) | Gap Scenario Design | 3h | 5+ decoys | 3+ scenarios | Not Started |
| [VM-W1.5-2j](VM_W1.5_2_SUBTASKS/VM_W1.5_2j_MERGE_VALIDATE.md) | Merge & Validation | 2h | - | - | Not Started |

## Expected Totals

| Metric | Target | Sub-task Sources |
|--------|--------|------------------|
| **Anchor Claims** | 75-150 | 2a + 2b |
| **Standard Claims** | 350-560 | 2c + 2d + 2e + 2f + 2g + 2h |
| **Total Claims** | 425-710 | All |
| **Non-extraction Items** | 50+ | 2a + 2b |
| **Known Gaps** | 160+ | All annotation tasks |
| **Gap Scenarios** | 3+ | 2i |
| **Decoy Papers** | 5+ | 2i |
| **Papers Annotated** | 80+ | All |

## Execution Strategy

### Phase 1: Anchors (Sequential)
1. **VM-W1.5-2a** → Establishes annotation standards
2. **VM-W1.5-2b** → Validates cross-domain consistency

### Phase 2: Standard Papers (Parallel)
After anchors complete, 2c-2h can execute in parallel:
- **VM-W1.5-2c** (Neuromorphic)
- **VM-W1.5-2d** (Quantum)
- **VM-W1.5-2e** (Microbiology)
- **VM-W1.5-2f** (Fusion/Nano)
- **VM-W1.5-2g** (Climate/Materials)
- **VM-W1.5-2h** (Biomedical)

### Phase 3: Scenarios & Merge (Sequential)
3. **VM-W1.5-2i** → Gap scenarios and decoys
4. **VM-W1.5-2j** → Final merge and validation

## Validation IDs Covered

| Metric ID | Description | Sub-tasks |
|-----------|-------------|-----------|
| QB-01 | Golden dataset size | All |
| QB-02 | Domain coverage | All |
| QB-03 | Verdict distribution | 2c-2h, 2j |
| QB-04 | False positive tests | 2a, 2b (non-extraction items) |
| QB-05 | Recommendation samples | All annotation tasks |
| FP-01 | Extraction false positive rate | 2a, 2b |
| FP-02 | Gap detection false positive | 2i |
| FP-03 | Decoy paper contribution | 2i |
| ITER-01 | Iterative gap closure | 2i |

## Archived Original

The original monolithic task card is archived at:
`task-cards/validation-matrix/archive/VM_WAVE_1.5_2_PAPER_ANNOTATION_ORIGINAL.md`

## Notes

- **Quality over speed**: Each sub-task should maintain annotation quality
- **Parallel execution**: 2c-2h can run simultaneously after 2a-2b
- **Checkpoint validation**: Run `annotate_paper.py validate` after each sub-task
- **Dependencies**: 2j cannot start until all others complete
