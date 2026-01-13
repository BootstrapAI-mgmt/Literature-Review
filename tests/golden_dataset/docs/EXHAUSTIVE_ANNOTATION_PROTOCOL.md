# Exhaustive Annotation Protocol for Anchor Papers

## Overview

Exhaustive annotation differs from standard annotation:
- **Standard:** Extract 5-8 representative claims per paper
- **Exhaustive:** Document EVERY statement that could be a claim

This creates true ground truth for testing extraction completeness.

## Annotation Phases

### Phase 1: Claim Discovery (Annotator A)

**Goal:** Identify ALL potential claims in the paper

**Process:**
1. Read entire paper sequentially
2. Mark every statement that could be a claim
3. Include uncertain cases (err on side of inclusion)
4. Document location precisely (page, paragraph, sentence)

**What to mark:**
- Quantitative assertions with numerical evidence
- Qualitative assertions with supporting evidence
- Methodology descriptions with specific details
- Conclusions supported by results
- Comparative statements with baselines
- Performance metrics of any kind

**What NOT to mark:**
- Background/introduction context
- Related work summaries (unless comparative)
- Future work statements (mark separately)
- Pure definitions
- Acknowledgments

### Phase 2: Independent Discovery (Annotator B)

**Goal:** Independent claim identification for reliability measurement

**Process:**
- Same as Phase 1, completely independent
- No access to Annotator A's results
- Same paper, same guidelines

### Phase 3: Reconciliation

**Goal:** Create unified exhaustive claim inventory

**Process:**
1. Union both annotators' claims
2. Identify intersection (high confidence)
3. Identify differences (discuss)
4. Categorize each claim:
   - **Intersection:** Both found → High confidence
   - **A only:** Discuss → Accept or reject with rationale
   - **B only:** Discuss → Accept or reject with rationale
5. Document reconciliation decisions

**Agreement Calculation:**
```
Cohen's κ = (P_observed - P_expected) / (1 - P_expected)

P_observed = % of claims both annotators agreed on
P_expected = expected agreement by chance
```

Target: κ ≥ 0.7 (substantial agreement)

### Phase 4: Extractability Classification

**Goal:** Classify each claim by extraction expectation

For each claim in the unified inventory:

| Extractability | Description | Pipeline Expectation |
|----------------|-------------|----------------------|
| **HIGH** | Clear, prominent, well-structured claim | MUST be extracted |
| **MEDIUM** | Valid claim, may require inference | SHOULD be extracted |
| **LOW** | Edge case, technical jargon, embedded | BONUS if extracted |
| **IRRELEVANT** | Off-topic, future work, opinions | Must NOT be extracted |

**Classification Criteria:**

| Factor | High | Medium | Low | Irrelevant |
|--------|------|--------|-----|------------|
| Location | Results, abstract | Methods, discussion | Footnotes, captions | Background |
| Clarity | Explicit claim | Moderate clarity | Requires interpretation | Ambiguous |
| Evidence | Immediate support | Same section | Elsewhere in paper | None |
| Relevance | Core contribution | Supporting result | Tangential | Off-topic |

### Phase 5: Expected Behavior Documentation

For each claim, document:

```yaml
claim_id: "AP-001-C01"
claim_text: "We achieved 95.2% accuracy..."
location:
  page: 5
  paragraph: 2
  sentence: 1
extractability: "high"
extractability_rationale: "Clear quantitative result in Results section"

expected_extraction:
  should_be_extracted: true
  if_not_extracted_severity: "error"  # error, warning, acceptable
  
expected_mapping:
  pillar: "Pillar 1: Biological Stimulus-Response"
  requirement: "REQ-B1.1"
  sub_requirement: "Sub-1.1.1"
  mapping_confidence: "high"  # high, medium, low
  
expected_verdict:
  verdict: "approved"
  composite_score_range: [3.5, 4.5]
  confidence: "high"
```

### Phase 6: Non-Extraction Documentation

For each IRRELEVANT item:

```yaml
item_id: "AP-001-NE-01"
item_text: "Future work will explore..."
location:
  page: 10
  paragraph: 4
item_type: "future_work"

expected_behavior:
  should_be_extracted: false
  if_extracted_severity: "error"  # false positive
  reason_not_relevant: "Future work statement, not a current finding"
```

## Quality Assurance Checklist

Before finalizing anchor paper annotation:

- [ ] All sections of paper reviewed
- [ ] Both annotators completed independently
- [ ] Reconciliation meeting held
- [ ] Agreement score calculated (κ ≥ 0.7)
- [ ] All claims have extractability classification
- [ ] All claims have expected verdict
- [ ] All irrelevant items documented
- [ ] At least 15+ claims in inventory
- [ ] Mix of extractability levels (high/medium/low)
- [ ] Mix of expected verdicts (approved/rejected/borderline)
