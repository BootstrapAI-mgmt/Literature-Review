# Research Loop Integration Assessment

> **Analysis Date:** December 19, 2025  
> **Scope:** Assessment of literature review I/O enhancement opportunities  
> **Status:** Active Analysis

---

## Executive Summary

This assessment analyzes how to integrate four key enhancements into the Literature Review system:

| Enhancement | Current Coverage | Gap Level | Integration Complexity |
|------------|-----------------|-----------|------------------------|
| 1. Action Vectors (Operationalization) | 🔴 Missing | HIGH | Medium |
| 2. Benchmark-Linked Requirement Matrices | 🟡 Partial | MEDIUM | Low |
| 3. Design-Validation Gap Closure | 🟡 Partial | MEDIUM | Medium |
| 4. Pillar Evolution Tracking | 🔴 Missing | HIGH | High |

---

## Current System Input/Output Analysis

### Current Pipeline Flow

```
┌─────────────────┐    ┌────────────────┐    ┌─────────────────┐
│  PDF Documents  │───▶│ Journal Review │───▶│  Deep Review    │
│  (data/raw/)    │    │   (Metadata)   │    │ (Evidence Ext.) │
└─────────────────┘    └────────────────┘    └─────────────────┘
                                                      │
                                                      ▼
┌─────────────────┐    ┌────────────────┐    ┌─────────────────┐
│ Proof Scorecard │◀───│  Gap Analysis  │◀───│     Judge       │
│  (Readiness)    │    │ (Completeness) │    │ (Claim Verify)  │
└─────────────────┘    └────────────────┘    └─────────────────┘
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │ Recommendations │
                                             │ (Search Queries)│
                                             └─────────────────┘
```

### Current Outputs (What Exists)

| Output | Location | Purpose |
|--------|----------|---------|
| Gap Analysis Report | `gap_analysis_output/gap_analysis_report.json` | Completeness per sub-requirement |
| Deep Review Directions | `gap_analysis_output/deep_review_directions.json` | Sub-requirements needing deep review |
| Proof Scorecard | `proof_scorecard_output/` | Publication readiness metrics |
| Version History | `review_version_history.json` | Paper metadata and scores |
| Suggested Searches | `suggested_searches.md` | Novel query recommendations |
| Sufficiency Matrix | In-code analysis | Quality vs quantity tradeoffs |
| Proof Chain | In-code analysis | Dependency graph between requirements |

### Current Gaps (What's Missing)

| Missing Output | Impact | Needed For |
|----------------|--------|------------|
| **Action Vectors** | Cannot translate findings → executable steps | Enhancement #1 |
| **Benchmark-Target Linkage** | Metrics without validation strategy | Enhancement #2 |
| **Validation Coverage Matrix** | Unknown testability of requirements | Enhancement #3 |
| **Pillar Evolution Log** | No audit trail for pillar changes | Enhancement #4 |
| **Stakeholder Impact Matrix** | Unknown beneficiaries of gap closure | Enhancement #4.3 |

---

## Enhancement #1: Action Vectors (Operationalization)

### Objective
Extract "action vectors" during research loops that outline executable plans for operationalizing Pillar components in a reproducible way.

### Current State Analysis

**What exists:**
- `recommendation.py`: Generates search query suggestions for gaps
- `proof_chain.py`: Maps logical dependencies between requirements
- `pillar_definitions_enhanced.json`: Has `quantitative_metrics` and `validation_criteria` per pillar

**What's missing:**
- Structured "action steps" output from research findings
- Mapping from evidence → implementation path
- Gap identification in action chain (i.e., "we found the algorithm but not deployment strategy")

### Proposed Integration

#### 1.1 New Data Structure: `ActionVector`

```python
@dataclass
class ActionVector:
    """Represents an executable step derived from research findings."""
    
    action_id: str                    # Unique identifier
    pillar: str                       # Source pillar
    requirement_id: str               # Source requirement
    action_type: str                  # "implement" | "validate" | "integrate" | "research_further"
    
    # What to do
    action_description: str           # Human-readable action
    implementation_approach: str      # Specific technical approach
    
    # Evidence basis
    source_papers: List[str]          # Papers supporting this action
    evidence_strength: float          # 0-1 confidence
    
    # Dependencies
    prerequisites: List[str]          # Other action_ids that must complete first
    pillar_dependencies: List[str]    # Pillars that must be at certain completeness
    
    # Operationalization metadata
    reproducibility_score: float      # Can this be reproduced? (0-1)
    resource_requirements: Dict       # {"compute": "GPU", "data": "labeled dataset", ...}
    estimated_effort: str             # "hours" | "days" | "weeks" | "months"
    
    # Gap tracking
    action_chain_gaps: List[str]      # Missing steps in the action chain
    blocking_unknowns: List[str]      # Questions that must be answered
```

#### 1.2 Integration Points

| Component | Modification | Purpose |
|-----------|-------------|---------|
| `deep_reviewer.py` | Add action extraction prompt | Extract implementation hints from papers |
| `judge.py` | Evaluate actionability of claims | Score how actionable evidence is |
| `gap_analyzer.py` | Generate action vectors from approved claims | Transform evidence → actions |
| `recommendation.py` | Include action chain gaps in recommendations | Target searches at action gaps |

#### 1.3 New Output: `action_vectors.json`

```json
{
  "timestamp": "2025-12-19T10:00:00Z",
  "pillar_summary": {
    "Pillar 2": {
      "total_actions": 12,
      "actionable": 8,
      "blocked": 4,
      "chain_completeness": 0.67
    }
  },
  "action_vectors": [
    {
      "action_id": "AV-P2-001",
      "pillar": "Pillar 2: AI Stimulus-Response",
      "requirement_id": "REQ-A2.1",
      "action_type": "implement",
      "action_description": "Deploy event-based sensor integration using DVS cameras",
      "implementation_approach": "Use aedat4 format with tonic preprocessing pipeline",
      "source_papers": ["paper_dvs_2024.pdf", "paper_tonic_2023.pdf"],
      "evidence_strength": 0.85,
      "prerequisites": [],
      "reproducibility_score": 0.9,
      "resource_requirements": {
        "hardware": "DVS camera (iniVation DAVIS346)",
        "software": "tonic, pytorch",
        "data": "DVS128 Gesture dataset"
      },
      "estimated_effort": "weeks",
      "action_chain_gaps": [
        "Missing: Calibration procedure for sensor-SNN interface"
      ],
      "blocking_unknowns": []
    }
  ]
}
```

#### 1.4 Deep Reviewer Prompt Extension

Add to evidence extraction prompt in `deep_reviewer.py`:

```python
OPERATIONALIZATION_PROMPT = """
For each approved claim, also extract:

1. **Implementation Approach**: What specific techniques, algorithms, or methods does the paper use that could be replicated?

2. **Reproducibility Assessment**:
   - Is code available? (URL if yes)
   - Is data available? (URL if yes)
   - Are hyperparameters specified?
   - Is the methodology detailed enough to reproduce?

3. **Resource Requirements**:
   - Hardware needed (GPU type, sensors, etc.)
   - Software dependencies
   - Dataset requirements
   - Estimated compute time

4. **Action Chain Position**:
   - What must be done BEFORE this can be applied?
   - What can be done AFTER this is applied?
   - Are there gaps in the action chain?

Return as JSON with field "operationalization":
{
  "implementation_approach": "...",
  "reproducibility": {"code_available": true/false, "data_available": true/false, "detail_level": "high/medium/low"},
  "resources": {"hardware": [...], "software": [...], "data": [...], "compute_time": "..."},
  "action_chain": {"prerequisites": [...], "enables": [...], "gaps": [...]}
}
"""
```

---

## Enhancement #2: Benchmark-Linked Requirement Matrices

### Objective
Requirement matrices should show how each performance target will be tested against selected benchmarks (or identify if no benchmark exists for a target).

### Current State Analysis

**What exists in `pillar_definitions_enhanced.json`:**
```json
"quantitative_metrics": {
  "latency_target": "< 10ms end-to-end",
  "power_efficiency": "< 1W for 1M neurons",
  ...
},
"validation_criteria": {
  "benchmark_datasets": ["N-MNIST", "DVS128 Gesture", "NCALTECH101"],
  "baseline_comparison": "Must exceed ANN baseline by 20% on efficiency",
  ...
}
```

**Gap:** No explicit linkage showing which benchmark tests which metric.

### Proposed Integration

#### 2.1 Enhanced Pillar Definition Structure

```json
"quantitative_metrics": {
  "latency_target": {
    "target_value": "< 10ms end-to-end",
    "measurement_method": "End-to-end inference timing",
    "benchmarks": [
      {
        "name": "DVS128 Gesture",
        "benchmark_metric": "inference_latency_ms",
        "notes": "Measure from event arrival to classification output"
      }
    ],
    "benchmark_status": "covered",
    "validation_evidence": ["paper_latency_2024.pdf"]
  },
  "power_efficiency": {
    "target_value": "< 1W for 1M neurons",
    "measurement_method": "Hardware power meter during inference",
    "benchmarks": [],
    "benchmark_status": "no_benchmark_identified",
    "validation_evidence": []
  }
}
```

#### 2.2 New Output: `requirement_benchmark_matrix.json`

```json
{
  "timestamp": "2025-12-19T10:00:00Z",
  "summary": {
    "total_metrics": 42,
    "fully_covered": 28,
    "partially_covered": 8,
    "no_benchmark": 6
  },
  "coverage_by_pillar": {
    "Pillar 2: AI Stimulus-Response": {
      "metrics": [
        {
          "metric_id": "P2-M1",
          "metric_name": "latency_target",
          "target": "< 10ms end-to-end",
          "benchmarks": ["DVS128 Gesture", "N-MNIST"],
          "coverage_status": "covered",
          "testing_approach": "Inference timing on standardized hardware",
          "evidence_papers": ["paper1.pdf"]
        },
        {
          "metric_id": "P2-M2",
          "metric_name": "power_efficiency",
          "target": "< 1W for 1M neurons",
          "benchmarks": [],
          "coverage_status": "no_benchmark",
          "gap_notes": "No standardized power measurement benchmark exists for neuromorphic systems",
          "suggested_approach": "Define custom power measurement protocol using Loihi/SpiNNaker hardware"
        }
      ]
    }
  },
  "gaps_requiring_action": [
    {
      "pillar": "Pillar 2",
      "metric": "power_efficiency",
      "issue": "no_benchmark_identified",
      "recommendation": "Search for neuromorphic power benchmarking methodologies",
      "priority": "HIGH"
    }
  ]
}
```

#### 2.3 Integration Points

| Component | Modification | Purpose |
|-----------|-------------|---------|
| `pillar_definitions_enhanced.json` | Restructure metrics with benchmark linkage | Central definition update |
| `gap_analyzer.py` | Extract benchmark coverage during analysis | Automated coverage assessment |
| `proof_scorecard.py` | Include benchmark coverage in readiness score | Publication-readiness gate |
| New: `benchmark_analyzer.py` | Dedicated benchmark-target analysis | Generate coverage matrix |

#### 2.4 Evidence Extraction Enhancement

During deep review, extract benchmark usage from papers:

```python
BENCHMARK_EXTRACTION_PROMPT = """
For each paper, identify:

1. **Benchmarks Used**: What standardized datasets or test protocols were used?
2. **Metrics Measured**: What quantitative metrics were reported?
3. **Measurement Method**: How were metrics measured? (timing method, power meter, etc.)
4. **Hardware Platform**: What hardware was used for benchmarking?
5. **Comparison Baselines**: What was the paper compared against?

Return as JSON:
{
  "benchmarks_used": [
    {
      "name": "DVS128 Gesture",
      "type": "dataset",
      "metrics_tested": ["accuracy", "latency"],
      "measurement_details": "..."
    }
  ],
  "novel_metrics": ["any metrics not in standard benchmarks"]
}
"""
```

---

## Enhancement #3: Design-Validation Gap Closure

### Objective
Drive towards closing gaps between design requirements and validation strategy.

### Current State Analysis

**What exists:**
- `proof_chain.py`: Dependency graph between requirements
- `proof_scorecard.py`: Publication readiness assessment
- `sufficiency_matrix.py`: Quality vs quantity analysis
- `validation_criteria` in pillar definitions

**What's missing:**
- Explicit tracking of "requirement → validation method → evidence" chain
- Identification of requirements with no validation strategy
- Tracking of validation strategy gaps (method exists but not executed)

### Proposed Integration

#### 3.1 Validation Coverage Model

```
Requirement ──────────────────────────────────────────────────────▶
     │
     ├── Validation Strategy (defined in pillar_definitions)
     │        │
     │        ├── Method: "fMRI comparison"
     │        ├── Benchmark: "HCP dataset"
     │        └── Acceptance Criteria: "> 0.8 correlation"
     │
     ├── Validation Evidence (from literature)
     │        │
     │        ├── Paper: "smith2024.pdf"
     │        ├── Method Used: "fMRI comparison"
     │        ├── Result: "0.85 correlation"
     │        └── Status: ✅ Validated
     │
     └── Validation Gap Status
              │
              ├── VALIDATED: Evidence matches strategy
              ├── PARTIAL: Evidence exists but different method
              ├── UNVALIDATED: Strategy defined, no evidence
              └── NO_STRATEGY: No validation approach defined
```

#### 3.2 New Output: `validation_gap_matrix.json`

```json
{
  "timestamp": "2025-12-19T10:00:00Z",
  "summary": {
    "total_requirements": 89,
    "validated": 34,
    "partially_validated": 22,
    "unvalidated": 18,
    "no_strategy": 15
  },
  "critical_gaps": [
    {
      "requirement_id": "Sub-1.1.3",
      "requirement": "Understanding of population coding for complex stimuli",
      "gap_type": "unvalidated",
      "defined_strategy": {
        "method": "Multi-electrode array recordings",
        "benchmark": "Natural scene presentation protocol",
        "acceptance": "Information-theoretic analysis > 0.7 bits/spike"
      },
      "evidence_status": "No papers found validating this approach",
      "recommendation": "Search for 'population coding information theory neural recording'"
    },
    {
      "requirement_id": "Sub-2.4.1",
      "requirement": "Sparse coding efficiency metrics (< 10% activation)",
      "gap_type": "no_strategy",
      "defined_strategy": null,
      "evidence_status": "3 papers discuss sparsity but no standard measurement",
      "recommendation": "Define sparsity measurement protocol before further research"
    }
  ],
  "by_pillar": {
    "Pillar 1: Biological Stimulus-Response": {
      "validated": 8,
      "partial": 4,
      "unvalidated": 3,
      "no_strategy": 1,
      "requirements": [...]
    }
  }
}
```

#### 3.3 Integration Points

| Component | Modification | Purpose |
|-----------|-------------|---------|
| `pillar_definitions_enhanced.json` | Add explicit `validation_strategy` per sub-requirement | Define expected validation |
| `judge.py` | Match evidence against defined validation strategy | Score strategy-alignment |
| `gap_analyzer.py` | Track validation coverage in gap report | Surface validation gaps |
| New: `validation_tracker.py` | Dedicated validation gap analysis | Generate validation matrix |
| `proof_scorecard.py` | Weight validation coverage in readiness | Gate on validated requirements |

#### 3.4 Pillar Definition Enhancement

```json
"requirements": {
  "REQ-B1.1: Sensory Transduction & Encoding": [
    {
      "id": "Sub-1.1.1",
      "text": "Conclusive model of how raw sensory data is transduced into neural spikes",
      "validation_strategy": {
        "method": "Spike-triggered averaging + receptive field mapping",
        "benchmark_protocol": "Drifting grating stimuli, natural scenes",
        "acceptance_criteria": "Predicted spike trains match actual with >0.8 correlation",
        "required_evidence_types": ["single-cell recordings", "computational model"]
      }
    }
  ]
}
```

---

## Enhancement #4: Pillar Evolution Tracking

### Objective
Research loops drive recommendations for Pillar additions or modifications (with approval workflow), including:
- 4.1: Documentation of current research topics/Pillars
- 4.2: Evidence tracking for existing Pillar research
- 4.3: Stakeholder impact analysis

### Current State Analysis

**What exists:**
- `pillar_definitions.json` and `pillar_definitions_enhanced.json`: Static definitions
- `review_version_history.json`: Paper-level version tracking
- `orchestrator_state.json`: Pipeline run state

**What's missing:**
- Version control for pillar definitions themselves
- Evidence that existing pillars are still relevant
- Tracking of research saturation (is a topic "solved"?)
- Stakeholder mapping

### Proposed Integration

#### 4.1 Pillar Documentation Enhancement

##### New File: `pillar_research_log.json`

```json
{
  "schema_version": "1.0",
  "last_updated": "2025-12-19T10:00:00Z",
  
  "pillars": {
    "Pillar 1: Biological Stimulus-Response": {
      "status": "active",
      "research_start_date": "2025-01-15",
      "last_evidence_date": "2025-12-18",
      "total_papers_reviewed": 47,
      "current_completeness": 62.3,
      "research_velocity": {
        "papers_per_month": 4.2,
        "completeness_gain_per_month": 3.1
      },
      "research_focus_areas": [
        {
          "area": "Sensory transduction",
          "sub_requirements": ["Sub-1.1.1", "Sub-1.1.2"],
          "status": "active_research",
          "recent_papers": ["paper1.pdf", "paper2.pdf"]
        }
      ],
      "modification_proposals": [],
      "notes": "Core biological foundation - high priority"
    }
  },
  
  "modification_log": [
    {
      "date": "2025-12-01",
      "pillar": "Pillar 2",
      "type": "sub_requirement_added",
      "change": "Added Sub-2.4.4: Dynamic voltage/frequency scaling based on task demands",
      "justification": "Multiple papers identified this as key efficiency mechanism",
      "evidence_papers": ["paper_dvfs_2024.pdf"],
      "approved_by": "research_lead",
      "status": "approved"
    }
  ]
}
```

#### 4.2 Evidence Saturation Tracking

Track whether existing research is still needed or if questions are "answered":

```json
"evidence_saturation": {
  "Sub-1.1.1": {
    "saturation_level": "high",
    "saturation_score": 0.92,
    "interpretation": "Well-established with multiple confirmatory studies",
    "recommendation": "Reduce search priority, focus on application",
    "key_consensus_papers": ["foundational_paper.pdf"],
    "open_questions": ["Edge cases in low-light conditions"],
    "last_novel_finding_date": "2024-08-15"
  },
  "Sub-2.3.2": {
    "saturation_level": "low",
    "saturation_score": 0.23,
    "interpretation": "Active research area with competing approaches",
    "recommendation": "Continue high-priority research",
    "competing_approaches": [
      {"approach": "Direct actor-critic", "papers": ["paper_a.pdf"]},
      {"approach": "Model-based", "papers": ["paper_b.pdf"]}
    ],
    "open_questions": ["Which approach scales better?", "Hardware efficiency comparison"]
  }
}
```

#### 4.3 Stakeholder Impact Matrix

##### New File: `stakeholder_impact_matrix.json`

```json
{
  "timestamp": "2025-12-19T10:00:00Z",
  
  "stakeholder_categories": {
    "hardware_engineers": {
      "description": "Engineers implementing neuromorphic chips",
      "primary_pillars": ["Pillar 2", "Pillar 4", "Pillar 6"],
      "key_requirements": ["Sub-2.1.3", "Sub-2.4.1", "Sub-4.3.3"],
      "impact_summary": "Hardware engineers need validated efficiency metrics and deployment architectures"
    },
    "neuroscientists": {
      "description": "Researchers studying biological neural systems",
      "primary_pillars": ["Pillar 1", "Pillar 3", "Pillar 5"],
      "key_requirements": ["Sub-1.1.1", "Sub-3.2.1", "Sub-5.1.1"],
      "impact_summary": "Biological validation of computational models"
    },
    "ml_practitioners": {
      "description": "ML engineers building practical systems",
      "primary_pillars": ["Pillar 2", "Pillar 4", "Pillar 7"],
      "key_requirements": ["Sub-2.2.1", "Sub-4.1.1", "Sub-7.1.1"],
      "impact_summary": "Need reproducible training pipelines and benchmark results"
    },
    "system_integrators": {
      "description": "Engineers building complete neuromorphic systems",
      "primary_pillars": ["Pillar 7"],
      "key_requirements": ["Sub-7.1.1", "Sub-7.2.1", "Sub-7.3.1"],
      "impact_summary": "Need integration protocols and cross-pillar communication standards"
    }
  },
  
  "gap_impact_analysis": [
    {
      "gap_id": "Sub-2.4.1",
      "gap_description": "Sparse coding efficiency metrics (< 10% activation)",
      "affected_stakeholders": ["hardware_engineers", "ml_practitioners"],
      "impact_severity": "HIGH",
      "why_it_matters": "Without sparsity metrics, hardware efficiency claims cannot be validated",
      "beneficiaries_of_closure": [
        "Intel Loihi team (hardware validation)",
        "SNN framework developers (training targets)",
        "Edge AI companies (deployment decisions)"
      ]
    }
  ]
}
```

#### 4.4 Pillar Modification Proposal Workflow

```
┌──────────────────┐     ┌────────────────────┐     ┌─────────────────┐
│ Research Loop    │────▶│ Proposal Generated │────▶│ Review Queue    │
│ Identifies Need  │     │ (Auto from gaps)   │     │ (Pending Approval)
└──────────────────┘     └────────────────────┘     └────────┬────────┘
                                                             │
                              ┌───────────────────────────────┘
                              ▼
                    ┌─────────────────────┐
                    │ Human Review        │
                    │ - Approve           │
                    │ - Reject with reason│
                    │ - Modify & Approve  │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Apply Change │  │ Archive with │  │ Apply with   │
    │ to Pillar    │  │ Rejection    │  │ Modifications│
    │ Definitions  │  │ Reason       │  │              │
    └──────────────┘  └──────────────┘  └──────────────┘
```

##### Proposal Data Structure

```json
{
  "proposal_id": "PROP-2025-012",
  "created_date": "2025-12-19",
  "proposal_type": "add_sub_requirement",
  "pillar": "Pillar 2: AI Stimulus-Response",
  "requirement": "REQ-A2.4: Metabolic Efficiency Validation",
  
  "proposed_change": {
    "action": "add",
    "content": "Sub-2.4.5: Power gating for inactive neuron populations",
    "rationale": "Multiple papers identify power gating as key efficiency mechanism not currently captured"
  },
  
  "evidence_basis": {
    "supporting_papers": ["paper_pg_2024.pdf", "paper_dormant_2023.pdf"],
    "evidence_strength": 0.78,
    "cross_paper_agreement": "strong",
    "triangulation_cluster": "cluster_17"
  },
  
  "impact_assessment": {
    "affected_requirements": ["Sub-2.4.1", "Sub-2.4.3"],
    "affected_stakeholders": ["hardware_engineers"],
    "validation_strategy_needed": true,
    "estimated_research_effort": "weeks"
  },
  
  "status": "pending_review",
  "reviewer": null,
  "review_date": null,
  "decision": null,
  "decision_rationale": null
}
```

---

## Implementation Roadmap

### Phase 1: Foundation (1-2 weeks)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Restructure `pillar_definitions_enhanced.json` with benchmark linkage | HIGH | 4h | None |
| Create `ActionVector` dataclass in `literature_review/models/` | HIGH | 2h | None |
| Create `pillar_research_log.json` schema | MEDIUM | 2h | None |
| Add `validation_strategy` fields to pillar definitions | HIGH | 3h | None |

### Phase 2: Extraction Enhancement (2-3 weeks)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Add operationalization prompt to `deep_reviewer.py` | HIGH | 4h | Phase 1 |
| Add benchmark extraction prompt to `deep_reviewer.py` | HIGH | 3h | Phase 1 |
| Modify `judge.py` to score actionability | MEDIUM | 4h | Phase 1 |
| Create `validation_tracker.py` module | HIGH | 6h | Phase 1 |
| Create `benchmark_analyzer.py` module | MEDIUM | 4h | Phase 1 |

### Phase 3: Output Generation (1-2 weeks)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Generate `action_vectors.json` output | HIGH | 4h | Phase 2 |
| Generate `requirement_benchmark_matrix.json` | MEDIUM | 3h | Phase 2 |
| Generate `validation_gap_matrix.json` | HIGH | 4h | Phase 2 |
| Generate `stakeholder_impact_matrix.json` | MEDIUM | 3h | Phase 1 |

### Phase 4: Pillar Evolution (2-3 weeks)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Implement saturation scoring in `gap_analyzer.py` | MEDIUM | 6h | Phase 2 |
| Create pillar modification proposal generator | HIGH | 8h | Phase 2 |
| Create proposal review CLI/dashboard UI | MEDIUM | 8h | Phase 4 |
| Implement pillar versioning system | HIGH | 6h | Phase 1 |

---

## Integration with Existing Components

### Modified Files

| File | Changes | Enhancement |
|------|---------|-------------|
| `pillar_definitions_enhanced.json` | Add benchmark linkage, validation strategies | #2, #3 |
| `literature_review/reviewers/deep_reviewer.py` | Add action/benchmark extraction prompts | #1, #2 |
| `literature_review/analysis/judge.py` | Score actionability, validation alignment | #1, #3 |
| `literature_review/analysis/gap_analyzer.py` | Generate action vectors, track saturation | #1, #4.2 |
| `literature_review/analysis/recommendation.py` | Include action gaps in recommendations | #1 |
| `literature_review/analysis/proof_scorecard.py` | Weight validation coverage | #3 |
| `literature_review/orchestrator.py` | Orchestrate new analysis modules | All |

### New Files

| File | Purpose | Enhancement |
|------|---------|-------------|
| `literature_review/models/action_vector.py` | ActionVector dataclass | #1 |
| `literature_review/analysis/benchmark_analyzer.py` | Benchmark-metric coverage | #2 |
| `literature_review/analysis/validation_tracker.py` | Validation gap analysis | #3 |
| `literature_review/analysis/pillar_evolution.py` | Pillar modification proposals | #4 |
| `pillar_research_log.json` | Pillar documentation and history | #4.1 |
| `stakeholder_impact_matrix.json` | Stakeholder mapping | #4.3 |

---

## Success Metrics

| Enhancement | Metric | Target |
|-------------|--------|--------|
| #1 Action Vectors | % of approved claims with action vectors | > 80% |
| #1 Action Vectors | Chain completeness (no gaps in action sequence) | > 70% |
| #2 Benchmark Linkage | % of metrics with defined benchmark | > 90% |
| #2 Benchmark Linkage | % of benchmarks with evidence | > 60% |
| #3 Validation Gap | % of requirements with validation strategy | > 95% |
| #3 Validation Gap | % of strategies with supporting evidence | > 50% |
| #4 Pillar Evolution | Proposals generated per research cycle | 1-3 |
| #4 Pillar Evolution | Proposal review turnaround time | < 48h |

---

## Next Steps

1. **Immediate**: Review and approve this assessment
2. **Week 1**: Implement Phase 1 (foundation structures)
3. **Week 2-3**: Implement Phase 2 (extraction enhancement)
4. **Week 4**: Implement Phase 3 (output generation)
5. **Week 5-6**: Implement Phase 4 (pillar evolution)
6. **Ongoing**: Integrate with dashboard UI for proposal review workflow
