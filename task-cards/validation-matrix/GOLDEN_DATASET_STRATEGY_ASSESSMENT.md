# Golden Dataset Strategy Assessment

**Assessment Date:** January 12, 2026  
**Purpose:** Critical evaluation of golden dataset creation methodology  
**Status:** ACTION REQUIRED - Structural gaps identified

---

## Executive Summary

A critical review of the current golden dataset strategy reveals **significant structural gaps** that could undermine validation reliability. The primary issue is that the current approach uses **forward-designed validation** (defining what SHOULD be found), but the pipeline is an **extraction system** that requires **ground-truth validation** (verifying it finds what IS in papers).

### Risk Assessment Matrix

| Concern Area | Current State | Risk Level | Impact |
|--------------|---------------|------------|--------|
| **A. Annotation Reliability** | Single-annotator with optional inter-rater agreement | 🟡 MEDIUM | May introduce systematic bias |
| **B. Definitive Classification** | Forward-designed (claims → expected results) | 🔴 HIGH | Doesn't prove extraction capability |
| **C. "Working Backwards" Approach** | Not implemented | 🔴 CRITICAL | Missing ground-truth extraction validation |
| **D. Multi-Pass Validation** | Not designed | 🔴 HIGH | Can't validate iterative gap-closing |
| **E. Negative Case Handling** | Weak evidence claims only | 🟡 MEDIUM | Can't validate "correctly NOT finding" |

---

## Detailed Gap Analysis

### Problem 1: Forward-Designed vs. Ground-Truth Validation

#### Current Approach (VM-W1.5-2)
```
Forward Design Flow:
1. Annotator reads paper
2. Annotator extracts 5-8 "representative" claims
3. Each claim is scored and mapped
4. Pipeline is tested against these claims
```

**Critical Flaw:** This tests whether the pipeline can reproduce pre-defined claims, NOT whether it can discover claims from real papers.

#### Required Approach (Bi-Directional)
```
Ground-Truth Flow:
1. Expert exhaustively annotates ALL extractable claims in paper
2. Each claim is classified:
   - Must be found (high extractability)
   - Should be found (medium extractability)  
   - Bonus if found (low extractability)
   - Should NOT be found (irrelevant content)
3. Pipeline is tested for:
   - Finding what must be found (recall)
   - Not finding what should be excluded (precision)
```

### Problem 2: No Negative Case Coverage

The current golden dataset defines:
- ✅ Claims that should be APPROVED (true positives)
- ✅ Claims that should be REJECTED (true negatives based on weak evidence)
- ❌ Content that should NOT be extracted at all (false positive prevention)
- ❌ Papers that should NOT contribute to gaps (decoy papers)
- ❌ Requirements that should NOT be flagged as gaps (non-gap validation)

### Problem 3: No Multi-Pass Scenario Testing

The pipeline supports iterative gap closing, but the golden dataset provides no way to test:
- Whether initial gap detection is accurate
- Whether gap-closing papers are correctly attributed
- Whether decoy papers are correctly ignored
- Whether recommendations improve with additional evidence

---

## Recommended Structural Changes

### 1. Add Prerequisite Task: VM-W1.5-0 (Ground Truth Design Validation)

Before annotating 80+ papers with the current methodology, we MUST:
1. Define exhaustive annotation protocol
2. Create anchor paper selection criteria
3. Design controlled gap scenarios
4. Establish two-annotator reconciliation process
5. Pilot test with 3-5 anchor papers

### 2. Extend VM-W1.5-2 with Bi-Directional Elements

Add to the annotation task card:
1. **Exhaustive claim inventory** for anchor papers (not just representative claims)
2. **Extractability classification** for each claim
3. **Non-extraction markers** for irrelevant content
4. **Decoy paper annotation** (papers that look relevant but shouldn't contribute)

### 3. Add Gap Scenario Design

Create controlled test scenarios:
1. **Pass 1 State:** Known database with known gaps
2. **Pass 2 Addition:** Specific gap-closing papers
3. **Decoy Papers:** Papers that shouldn't close gaps
4. **Expected Outcomes:** Precise expectations for each state transition

---

## Validation Coverage Gap Analysis

### Current Coverage Map

| Validation ID | What It Tests | Ground Truth Source | Has Negative Cases? |
|--------------|---------------|---------------------|---------------------|
| AV-01 (Precision) | Extracted claims are valid | Forward-designed claims | ❌ No |
| AV-02 (Recall) | Expected claims are found | Forward-designed claims | ❌ No |
| AV-03 (Judge Accuracy) | Verdicts match expected | Synthetic/annotated verdicts | 🟡 Partial |
| FV-07 (Gap Detection) | Gaps are identified | Known gaps in schema | ❌ No non-gap validation |
| QB-03 (Gap Completeness) | All gaps found | Known gap list | ❌ No |
| RA-01 (Recommendations) | Themes are relevant | Expected themes | ❌ No |

### Required Coverage (Post-Enhancement)

| Validation ID | Ground Truth Source | Positive Case | Negative Case |
|--------------|---------------------|---------------|---------------|
| AV-01 | Anchor paper exhaustive inventory | Claims marked "must find" | Claims marked "irrelevant" |
| AV-02 | Anchor paper exhaustive inventory | High-extractability claims | N/A |
| AV-03 | Multi-annotator verdicts | Approved claims | Rejected claims |
| FV-07 | Gap scenario Pass 1 | Gaps that exist | Covered requirements |
| QB-03 | Gap scenario Pass 1 | Critical gaps | Non-gaps |
| RA-01 | Gap scenario with known closers | Papers that close gaps | Decoy papers |
| **NEW: FP-01** | Anchor paper exclusion list | N/A | Content not to extract |
| **NEW: GAP-NEG** | Gap scenario non-gaps | N/A | Requirements with coverage |
| **NEW: ITER-01** | Pass 2 gap closing | Gap reduction | Decoy paper rejection |

---

## Implementation Priorities

### Critical (Must Do Before VM-W1.5-2 Implementation)

1. **Create VM-W1.5-0 Task Card** (4 hours)
   - Ground truth design validation
   - Anchor paper selection criteria
   - Exhaustive annotation protocol
   - Two-annotator reconciliation process

2. **Select 5-10 Anchor Papers** (2 hours)
   - Diverse domains
   - Known content for exhaustive annotation
   - Mix of claim densities

3. **Design 3+ Gap Scenarios** (4 hours)
   - Pass 1 initial states
   - Pass 2 gap-closing papers
   - Decoy papers

### High Priority (Modify VM-W1.5-2)

4. **Add Exhaustive Claim Inventory** for anchor papers
5. **Add Extractability Classification** scheme
6. **Add Decoy Paper Annotations**
7. **Add Non-Extraction Markers**

### Medium Priority (Schema Updates)

8. **Extend schema with anchor paper model**
9. **Add gap scenario schema**
10. **Add decoy paper schema**

---

## Decision Required

Before proceeding with VM-W1.5-2 Paper Annotation:

- [ ] **Option A:** Add VM-W1.5-0 as prerequisite (Recommended - adds ~12 hours)
- [ ] **Option B:** Modify VM-W1.5-2 to include bi-directional elements (adds ~8 hours)
- [ ] **Option C:** Proceed with current approach, accept validation limitations
- [ ] **Option D:** Hybrid approach - anchor papers + forward-designed papers

### Recommendation: Option D (Hybrid Approach)

**Rationale:** 
- Use exhaustive annotation for 5-10 "anchor papers" (true ground truth)
- Use forward-designed annotation for remaining 70+ papers (volume)
- Create 3+ controlled gap scenarios for iterative testing
- Total additional effort: ~16 hours

This provides the structural rigor needed for validation confidence while maintaining practical implementation timelines.

---

## Proposed Wave Structure Update

```
Wave 1.5: Ground Truth Infrastructure (UPDATED)
├── VM-W1.5-0: Ground Truth Design Validation (NEW - PREREQUISITE)
│   ├── Anchor paper selection criteria
│   ├── Exhaustive annotation protocol  
│   ├── Gap scenario design template
│   └── Pilot annotation (3-5 papers)
├── VM-W1.5-1: Open Access Paper Sourcing (existing)
│   └── Add: Decoy paper sourcing (5+ papers)
├── VM-W1.5-2: Paper Annotation (existing, ENHANCED)
│   ├── Anchor paper exhaustive annotation (5-10 papers)
│   ├── Standard paper annotation (70+ papers)
│   └── Gap scenario creation
└── VM-W1.5-3: Gap Scenario Design & Validation (NEW)
    ├── Pass 1 database states
    ├── Pass 2 gap-closing papers
    └── Decoy paper validation
```

---

## Action Items

1. [ ] Review this assessment with stakeholders
2. [ ] Decide on implementation approach (A/B/C/D)
3. [ ] Create VM-W1.5-0 task card if approved
4. [ ] Update VM-W1.5-2 task card with enhancements
5. [ ] Update VALIDATION_MATRIX_WAVE_INDEX.md
6. [ ] Update golden dataset schema if needed

---

## References

- [VM_WAVE_1.5_2_PAPER_ANNOTATION.md](VM_WAVE_1.5_2_PAPER_ANNOTATION.md) - Current annotation task card
- [VM_WAVE_0_2_GOLDEN_DATASET_SPEC.md](VM_WAVE_0_2_GOLDEN_DATASET_SPEC.md) - Golden dataset specification
- [VALIDATION_MATRIX_WAVE_INDEX.md](VALIDATION_MATRIX_WAVE_INDEX.md) - Wave index and timeline
