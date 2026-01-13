# VM-W1.5-2i: Gap Scenario Design & Decoy Annotation

**Parent Task:** VM-W1.5-2 (Paper Annotation for Golden Dataset)  
**Created:** January 13, 2026  
**Effort:** 3 hours  
**Priority:** HIGH  
**Status:** Not Started

---

## Overview

Design controlled gap scenarios for iterative validation testing (ITER-01) and annotate decoy papers for false positive testing (FP-03). This task creates the test infrastructure for bi-directional validation.

## Prerequisites

| Dependency | Status | Description |
|------------|--------|-------------|
| VM-W1.5-0 | ✅ PR #142 | Gap Scenario Design template |
| VM-W1.5-2a | Required | Anchor papers with exhaustive gaps |
| VM-W1.5-2b | Required | Cross-domain anchor gaps |
| VM-W1.5-2c-2h | Required | Standard paper gaps (160+ total) |

## Scope

### Gap Scenario Design

Design 3+ controlled gap scenarios following the GAP_SCENARIO_DESIGN.md template from VM-W1.5-0:

| Scenario ID | Domain | Gap Type | Pass 1 State | Pass 2 Resolution |
|-------------|--------|----------|--------------|-------------------|
| GAP-001 | Neuromorphic | Missing energy efficiency data | 60% completeness | Add paper proving 10x efficiency |
| GAP-002 | Quantum | Missing error correction threshold | 40% completeness | Add paper with error rates |
| GAP-003 | Cross-domain | Missing reproducibility evidence | 30% completeness | Add multi-lab validation paper |

### Decoy Paper Annotation

Annotate 5+ decoy papers that should NOT close any gaps:

| Decoy ID | Domain | Why It's a Decoy | Expected Gap Contribution |
|----------|--------|------------------|---------------------------|
| DECOY-001 | Neuromorphic | Different architecture entirely | 0% (irrelevant topic) |
| DECOY-002 | Quantum | Theoretical only, no experimental data | 0% (no evidence) |
| DECOY-003 | Microbiology | Outdated methodology | 0% (weak evidence) |
| DECOY-004 | Climate | Simulation only, no validation | 0% (insufficient rigor) |
| DECOY-005 | Materials | Industry press release, not peer-reviewed | 0% (low reliability) |

### Deliverables

1. **Gap Scenario Definitions** (3+ scenarios)
   - JSON files following GapScenario schema from VM-W1.5-0
   - Pass 1 initial state with expected gaps
   - Gap-closing papers identified for Pass 2
   - Expected outcomes documented

2. **Decoy Paper Annotations** (5+ papers)
   - Full standard annotation (5-8 claims each)
   - `is_decoy: true` flag set
   - Documentation of why each is a decoy
   - Expected contribution: 0% for all

3. **Test Data Files**
   - `tests/golden_dataset/scenarios/GAP-001.json`
   - `tests/golden_dataset/scenarios/GAP-002.json`
   - `tests/golden_dataset/scenarios/GAP-003.json`
   - `tests/golden_dataset/data/decoy_papers.json`

## Gap Scenario Schema

Each scenario follows the schema from VM-W1.5-0:

```json
{
  "scenario_id": "GAP-001",
  "scenario_name": "Energy Efficiency Gap Resolution",
  "description": "Test detection and closure of energy efficiency gap",
  "domain": "neuromorphic",
  "gap_definition": {
    "pillar": "Energy Efficiency",
    "requirement_id": "EE-001",
    "initial_completeness": 0.6,
    "why_is_gap": "Missing comparative energy measurements"
  },
  "pass_1": {
    "database_state_file": "state_pass1_gap001.json",
    "expected_gaps": ["EE-001"],
    "expected_non_gaps": ["SC-001", "PE-001"]
  },
  "pass_2": {
    "closing_papers": ["NEURO-CLOSING-001"],
    "database_state_file": "state_pass2_gap001.json",
    "expected_gaps_remaining": [],
    "expected_closed": ["EE-001"]
  },
  "decoy_papers": ["DECOY-001"],
  "expected_decoy_contribution": 0.0
}
```

## Decoy Paper Annotation Schema

```json
{
  "paper_id": "DECOY-001",
  "is_decoy": true,
  "decoy_reason": "Different architecture entirely - spintronic not neuromorphic",
  "domain": "neuromorphic",
  "expected_gap_contribution": 0.0,
  "claims": [...],
  "gaps": [],
  "annotation_note": "Claims are valid but irrelevant to neuromorphic requirements"
}
```

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│              Phase 1: Gap Selection (1h)                    │
├─────────────────────────────────────────────────────────────┤
│ 1. Review gaps from VM-W1.5-2a through 2h annotations      │
│ 2. Select 3+ gaps suitable for controlled scenarios        │
│ 3. Verify gap-closing papers exist in registry             │
│ 4. Design Pass 1/Pass 2 state transitions                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            Phase 2: Decoy Selection (30 min)                │
├─────────────────────────────────────────────────────────────┤
│ 1. Identify 5+ papers that appear relevant but aren't      │
│ 2. Document why each is a decoy                            │
│ 3. Verify PDFs available                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            Phase 3: Decoy Annotation (1h)                   │
├─────────────────────────────────────────────────────────────┤
│ 1. Annotate each decoy paper (standard workflow)           │
│ 2. Set is_decoy: true                                      │
│ 3. Document expected_gap_contribution: 0.0                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            Phase 4: Scenario Finalization (30 min)          │
├─────────────────────────────────────────────────────────────┤
│ 1. Create scenario JSON files                              │
│ 2. Create database state snapshots                         │
│ 3. Validate scenarios against schema                       │
└─────────────────────────────────────────────────────────────┘
```

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| Gap scenarios | 3+ | Count in scenarios/ |
| Decoy papers | 5+ | Count with is_decoy=true |
| Pass 1/Pass 2 defined | All scenarios | Each scenario has both |
| Expected outcomes | Documented | All scenarios have expectations |
| Schema valid | 100% | Validation passes |

## Metrics Enabled

This task directly enables testing of:

| Metric | Description | Target |
|--------|-------------|--------|
| FP-02 | Gap detection false positive rate | 0% |
| FP-03 | Decoy paper contribution rate | 0% |
| ITER-01 | Iterative gap closure accuracy | ≥95% |

## Notes

- **Use real gaps**: Select from actual annotation gaps, not synthetic
- **Realistic decoys**: Decoys should look plausible to catch FP issues
- **Document reasoning**: Clear rationale for each scenario and decoy choice
- **Cross-reference VM-W1.5-3**: Gap Scenario Execution Framework uses these files
