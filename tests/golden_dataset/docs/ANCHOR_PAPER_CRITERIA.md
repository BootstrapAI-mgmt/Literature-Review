# Anchor Paper Selection Criteria

## Purpose

Anchor papers are real academic papers that receive **exhaustive annotation** -
every extractable claim is documented, classified, and mapped. These provide
true ground truth for extraction validation.

## Selection Criteria

### Required Criteria (All must be met)

| Criterion | Requirement | Rationale |
|-----------|-------------|-----------|
| **Open Access** | CC-BY or equivalent license | Legal compliance |
| **Peer Reviewed** | Published in peer-reviewed venue | Quality assurance |
| **Claim Density** | 10-30 extractable claims | Testable volume |
| **Requirement Coverage** | Covers 3-6 requirements | Mapping diversity |
| **Text Extractable** | Selectable PDF text | Technical requirement |
| **Clear Structure** | Standard IMRAD format | Annotation consistency |
| **Recency** | Published 2020-2025 | Relevance |

### Preferred Criteria (At least 2)

| Criterion | Preference | Rationale |
|-----------|------------|-----------|
| **Quantitative Results** | Contains numerical benchmarks | Strongest evidence type |
| **Methodology Detail** | Complete methods section | Reproducibility testing |
| **Multi-Claim Types** | Mix of strong/weak/borderline | Verdict distribution |
| **Domain Diversity** | Different from other anchors | Cross-domain validation |
| **Available Data/Code** | Open source artifacts | Ground truth verification |

### Anti-Criteria (Disqualifying)

| Criterion | Disqualification |
|-----------|------------------|
| Review/survey paper | Too many indirect claims |
| < 5 pages | Insufficient content |
| Workshop paper only | Quality uncertainty |
| Heavy on figures/tables | Text extraction issues |
| Domain not in registry | Outside scope |

## Target Distribution

| Domain | Anchor Papers | Rationale |
|--------|---------------|-----------|
| Neuromorphic | 2 | Primary domain, most coverage |
| Quantum | 1 | Maximum domain distance |
| Microbiology | 1 | Life sciences representation |
| Climate | 1 | Earth sciences representation |
| Materials/Other | 1 | Additional diversity |
| **Total** | 5-7 | Manageable for exhaustive annotation |

## Candidate Identification Process

1. Review paper registry for papers meeting required criteria
2. Read abstract and methods for each candidate
3. Estimate claim density (target: 10-30 claims)
4. Score against preferred criteria
5. Select diverse set ensuring domain coverage
6. Document selection rationale

## Validation Scope by Paper Type

> **Critical Clarification:** Different paper types enable different validations.
> This table prevents over-claiming validation coverage.

| Validation ID | Anchor Papers (5-10) | Standard Papers (70+) | Notes |
|---------------|---------------------|----------------------|-------|
| **AV-01** (Precision) | ✅ Full (false positive tests) | ❌ Not validated | Requires exhaustive inventory |
| **AV-02** (Recall) | ✅ Full (must-find claims) | ❌ Not validated | Requires exhaustive inventory |
| **AV-03** (Judge Accuracy) | ✅ Full | ✅ Full | Forward-designed claims sufficient |
| **AV-04** (Calibration) | ✅ Full | ✅ Full | Forward-designed claims sufficient |
| **QB-02** (Pillar Mapping) | ✅ Full | ✅ Full | Forward-designed claims sufficient |
| **FV-07** (Gap Detection) | ✅ Via scenarios | ✅ Via scenarios | Uses controlled gap scenarios |
| **RA-01** (Recommendations) | ✅ Via scenarios | ✅ Via scenarios | Uses controlled gap scenarios |
| **FP-01** (Extraction FP) | ✅ Full | ❌ Not validated | Requires non-extraction items |
| **FP-02** (Gap FP) | ✅ Via scenarios | ✅ Via scenarios | Uses expected_non_gaps |
| **FP-03** (Decoy Contrib) | ✅ Via scenarios | ✅ Via scenarios | Uses decoy papers |

**Implication:** Extraction validation (AV-01, AV-02, FP-01) is **only possible with exhaustive annotation**.
Standard papers validate downstream processing (verdicts, mapping, gaps) but NOT extraction capability.
