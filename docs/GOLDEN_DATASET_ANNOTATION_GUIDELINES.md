# Golden Dataset Annotation Guidelines

## Overview

This document provides guidelines for annotating claims, evidence, and verdicts
for the Literature Review golden dataset. Consistent annotation is critical for
accurate validation testing.

## Claim Annotation Process

### Step 1: Read the Full Paper Context
- Read at least 2 pages around the claim
- Understand the paper's methodology
- Note the publication date and venue

### Step 2: Evaluate Claim-Requirement Mapping
1. Read the claim text carefully
2. Review all pillar definitions
3. Select the BEST matching pillar (primary topic)
4. Select the specific requirement
5. Select the sub-requirement
6. Document your rationale

**Mapping Rules:**
- If claim spans multiple pillars, choose the PRIMARY one
- If uncertain, mark as edge case
- Never force a mapping - mark as "unmappable" if no fit

### Step 3: Evaluate Evidence Quality

Rate each dimension independently:

#### Strength (1-5)
- 5: Direct experimental proof with statistical significance
- 4: Strong quantitative data with clear methodology
- 3: Good qualitative or limited quantitative evidence
- 2: Weak or indirect evidence
- 1: Anecdotal or unsupported claims

#### Rigor (1-5)
- 5: Peer-reviewed, replicated, validated methodology
- 4: Peer-reviewed with sound methodology
- 3: Reasonable methodology, minor issues
- 2: Methodology concerns or limited description
- 1: No methodology described or major flaws

#### Relevance (1-5)
- 5: Directly addresses the sub-requirement
- 4: Strongly related to the sub-requirement
- 3: Moderately relevant
- 2: Tangentially related
- 1: Not relevant

#### Directness (1-3)
- 3: Direct evidence (first-hand experimental results)
- 2: Indirect evidence (derived or secondary analysis)
- 1: Tertiary evidence (citations, reviews)

#### Reproducibility (1-5)
- 5: Complete code/data available, fully reproducible
- 4: Detailed methodology, could be reproduced
- 3: Moderate detail, reproduction possible with effort
- 2: Limited details, reproduction difficult
- 1: Cannot be reproduced

### Step 4: Determine Expected Verdict

Apply the Judge's criteria:
- **APPROVE** if: composite ≥ 3.0 AND strength ≥ 3 AND relevance ≥ 3
- **REJECT** if: criteria not met
- **BORDERLINE** if: composite between 2.8-3.2 (for calibration)

Document your confidence:
- **HIGH**: 90%+ confident in verdict
- **MEDIUM**: 70-90% confident
- **LOW**: 50-70% confident

### Step 5: Identify Edge Cases

Flag as edge case if:
- Mapping is ambiguous
- Evidence quality is borderline
- Multiple reasonable interpretations exist
- Technical domain knowledge required
- Claim is unusually complex

## Quality Assurance

### Self-Check
Before submitting, verify:
- [ ] All fields are completed
- [ ] Rationales are clear and specific
- [ ] Scores are justified
- [ ] Verdict matches score thresholds
- [ ] Edge cases are flagged

### Disagreement Resolution
When annotators disagree:
1. Document both perspectives
2. Third annotator reviews independently
3. Majority vote determines final
4. Significant disagreements trigger discussion
5. Unresolvable cases marked as edge cases

## Examples

### Example 1: Clear Approval
```json
{
  "claim_text": "Our SNN achieved 98.2% accuracy on DVS gesture recognition",
  "evidence_text": "Table 3: Cross-validation results (n=10) show 98.2% ± 0.4%",
  "expected_verdict": "approved",
  "evidence_quality": {
    "strength_score": 5,
    "rigor_score": 4,
    "relevance_score": 5,
    "directness": 3,
    "reproducibility_score": 4
  },
  "verdict_rationale": "Clear quantitative results with proper validation"
}
```

### Example 2: Clear Rejection
```json
{
  "claim_text": "Neuromorphic systems are more efficient",
  "evidence_text": "As commonly known in the field...",
  "expected_verdict": "rejected",
  "evidence_quality": {
    "strength_score": 1,
    "rigor_score": 1,
    "relevance_score": 3,
    "directness": 1,
    "reproducibility_score": 1
  },
  "verdict_rationale": "No quantitative evidence, unsupported assertion"
}
```

### Example 3: Borderline Case
```json
{
  "claim_text": "Our chip shows promise for real-time processing",
  "evidence_text": "Preliminary tests indicate sub-10ms latency",
  "expected_verdict": "borderline",
  "evidence_quality": {
    "strength_score": 3,
    "rigor_score": 3,
    "relevance_score": 3,
    "directness": 2,
    "reproducibility_score": 2
  },
  "verdict_rationale": "Composite ~3.0, on threshold boundary"
}
```

## Composite Score Calculation

The composite score is calculated using weighted averages:

```
composite = strength * 0.30 + rigor * 0.25 + relevance * 0.25 + 
            (directness / 3) * 0.10 + recency_bonus * 0.05 + 
            reproducibility * 0.05
```

### Weight Rationale
- **Strength (30%)**: Most important - evidence must be strong
- **Rigor (25%)**: Methodology quality is critical for trustworthiness
- **Relevance (25%)**: Evidence must address the requirement
- **Directness (10%)**: First-hand evidence is preferred
- **Recency (5%)**: Newer research is often more relevant
- **Reproducibility (5%)**: Reproducible research is more valuable

## Related Documentation

- [Golden Dataset Requirements](./GOLDEN_DATASET_REQUIREMENTS.md) - Dataset specifications
- [Golden Dataset README](../tests/golden_dataset/README.md) - Usage patterns
