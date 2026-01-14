# Agent Annotation Prompt Template

**Version:** 1.0  
**Purpose:** Standardized prompt for agent-based paper annotation  
**Usage:** Replace `{{PLACEHOLDER}}` values for each paper

---

## Master Prompt

```markdown
# Scientific Paper Annotation Task

You are annotating a research paper for a golden dataset that will be used to validate an automated literature review system. Your annotations must be **accurate, verifiable, and traceable** to specific locations in the paper.

## Paper Information

- **Paper ID:** {{PAPER_ID}}
- **Title:** {{PAPER_TITLE}}
- **Authors:** {{AUTHORS}}
- **Year:** {{YEAR}}
- **Source:** {{SOURCE_TYPE}} {{SOURCE_ID}}
- **Domain:** {{DOMAIN}}

## Your Task

Read the attached PDF carefully and extract:

1. **Quantitative Claims** - Specific numeric results, performance metrics, measurements
2. **Qualitative Claims** - Non-numeric findings, conclusions, methodological innovations
3. **Research Gaps** - Limitations acknowledged, future work suggested, open questions
4. **Methodology Details** - Key methods, datasets, experimental setups

---

## Extraction Requirements

### For Each Claim:

You MUST provide:

| Field | Description | Required |
|-------|-------------|----------|
| `claim_id` | Unique ID (e.g., "NEURO-002-C001") | Yes |
| `claim_type` | "quantitative" or "qualitative" | Yes |
| `claim_text` | The exact claim in your words | Yes |
| `verbatim_quote` | Direct quote from paper (≤100 words) | Yes |
| `page_number` | Page where claim appears | Yes |
| `section` | Section name (e.g., "Results", "Abstract") | Yes |
| `confidence` | Your confidence: high/medium/low | Yes |
| `verification_notes` | How to verify this claim | Yes |

### For Each Gap:

| Field | Description | Required |
|-------|-------------|----------|
| `gap_id` | Unique ID (e.g., "NEURO-002-G001") | Yes |
| `gap_type` | "limitation", "future_work", "open_question" | Yes |
| `gap_text` | Description of the gap | Yes |
| `verbatim_quote` | Direct quote if available | If available |
| `page_number` | Page where gap is mentioned | Yes |
| `section` | Section name | Yes |
| `implied_vs_explicit` | "explicit" (stated) or "implied" (inferred) | Yes |

---

## Output Schema

Provide your annotations in the following JSON structure:

```json
{
  "paper_id": "{{PAPER_ID}}",
  "annotator": "agent",
  "annotation_date": "YYYY-MM-DD",
  "annotation_version": "1.0",
  
  "paper_metadata": {
    "title": "{{PAPER_TITLE}}",
    "authors": ["Author 1", "Author 2"],
    "year": {{YEAR}},
    "source": "{{SOURCE_TYPE}}:{{SOURCE_ID}}",
    "domain": "{{DOMAIN}}",
    "page_count": null,
    "abstract_summary": "2-3 sentence summary of the paper"
  },
  
  "claims": [
    {
      "claim_id": "{{PAPER_ID}}-C001",
      "claim_type": "quantitative",
      "claim_text": "Description of the claim",
      "verbatim_quote": "Exact text from paper",
      "location": {
        "page": 5,
        "section": "Results",
        "paragraph": 2
      },
      "confidence": "high",
      "verification_notes": "How to verify",
      "metadata": {
        "metric_name": "accuracy",
        "metric_value": 95.2,
        "metric_unit": "%",
        "comparison_baseline": "previous SOTA",
        "statistical_significance": "p < 0.05"
      }
    }
  ],
  
  "gaps": [
    {
      "gap_id": "{{PAPER_ID}}-G001",
      "gap_type": "limitation",
      "gap_text": "Description of the gap",
      "verbatim_quote": "Exact text if available",
      "location": {
        "page": 12,
        "section": "Discussion"
      },
      "implied_vs_explicit": "explicit",
      "research_direction": "What future work could address this"
    }
  ],
  
  "methodology_summary": {
    "approach": "Brief description of methodology",
    "datasets_used": ["Dataset 1", "Dataset 2"],
    "key_techniques": ["Technique 1", "Technique 2"],
    "evaluation_metrics": ["Metric 1", "Metric 2"]
  },
  
  "quality_metadata": {
    "total_claims": 0,
    "quantitative_claims": 0,
    "qualitative_claims": 0,
    "total_gaps": 0,
    "annotation_confidence": "high/medium/low",
    "notes": "Any issues encountered during annotation"
  }
}
```

---

## Quality Criteria

### DO:
- ✓ Quote exact text from the paper
- ✓ Include page numbers for every claim
- ✓ Distinguish between results and claims about methods
- ✓ Note when claims are qualified (e.g., "up to 30%", "approximately")
- ✓ Capture uncertainty ranges when provided
- ✓ Mark your confidence level honestly

### DO NOT:
- ✗ Invent or extrapolate numbers not in the paper
- ✗ Claim something is in the paper if you cannot locate it
- ✗ Conflate claims from the abstract with detailed results
- ✗ Ignore confidence intervals, error bars, or qualifications
- ✗ Assume common author names without verification
- ✗ Fill in "likely" values based on domain knowledge

---

## Example Annotation

For a hypothetical paper "Event-Driven Learning for SNNs":

```json
{
  "paper_id": "NEURO-002",
  "annotator": "agent",
  "annotation_date": "2026-01-13",
  "annotation_version": "1.0",
  
  "claims": [
    {
      "claim_id": "NEURO-002-C001",
      "claim_type": "quantitative",
      "claim_text": "The proposed event-driven learning method achieves 30x energy reduction compared to traditional backpropagation on neuromorphic hardware",
      "verbatim_quote": "Our event-driven approach demonstrates a 30× reduction in energy consumption when deployed on Intel's Loihi neuromorphic processor compared to GPU-based backpropagation training.",
      "location": {
        "page": 1,
        "section": "Abstract",
        "paragraph": 1
      },
      "confidence": "high",
      "verification_notes": "Key result stated in abstract, should be supported in Results section",
      "metadata": {
        "metric_name": "energy_reduction",
        "metric_value": 30,
        "metric_unit": "x (factor)",
        "comparison_baseline": "GPU backpropagation",
        "hardware": "Intel Loihi"
      }
    },
    {
      "claim_id": "NEURO-002-C002",
      "claim_type": "quantitative",
      "claim_text": "STD-ED method improves accuracy by 2.51% on image classification benchmarks",
      "verbatim_quote": "STD-ED achieves 2.51% higher accuracy on CIFAR-100 compared to surrogate gradient methods",
      "location": {
        "page": 1,
        "section": "Abstract",
        "paragraph": 1
      },
      "confidence": "high",
      "verification_notes": "Verify exact percentage in Results table",
      "metadata": {
        "metric_name": "accuracy_improvement",
        "metric_value": 2.51,
        "metric_unit": "%",
        "dataset": "CIFAR-100",
        "comparison_baseline": "surrogate gradient methods"
      }
    }
  ],
  
  "gaps": [
    {
      "gap_id": "NEURO-002-G001",
      "gap_type": "limitation",
      "gap_text": "Method has not been validated on larger-scale datasets like ImageNet",
      "verbatim_quote": "Future work will extend evaluation to ImageNet-scale datasets",
      "location": {
        "page": 11,
        "section": "Conclusion"
      },
      "implied_vs_explicit": "explicit",
      "research_direction": "Scale validation to ImageNet or larger datasets"
    }
  ]
}
```

---

## Verification Checklist

Before submitting your annotation, verify:

- [ ] All claims have page numbers
- [ ] All verbatim quotes are exact (can be found in PDF)
- [ ] No numeric values are invented or estimated
- [ ] Author names match the paper exactly
- [ ] Quantitative claims include units and context
- [ ] Gaps distinguish between explicit limitations and implied ones
- [ ] Confidence levels are honest (use "low" when uncertain)

---

## Domain-Specific Guidance

### {{DOMAIN}} Papers

{{DOMAIN_SPECIFIC_GUIDANCE}}

---

## Attached PDF

The paper PDF is attached to this conversation. Read it completely before beginning annotation.

**File:** {{PDF_FILENAME}}

Begin your annotation now.
```

---

## Domain-Specific Guidance Templates

### Neuromorphic Computing

```markdown
For neuromorphic computing papers, pay special attention to:
- Energy consumption metrics (often compared to GPU/CPU baselines)
- Accuracy on standard benchmarks (MNIST, CIFAR, DVS datasets)
- Temporal dynamics and spike timing claims
- Hardware-specific results (Loihi, TrueNorth, SpiNNaker)
- Claims about biological plausibility
```

### Quantum Computing

```markdown
For quantum computing papers, pay special attention to:
- Qubit counts and coherence times
- Gate fidelity percentages (1-qubit, 2-qubit)
- Error rates (logical vs physical)
- Quantum volume or other benchmarks
- Claims about quantum advantage or supremacy
- Temperature and environmental requirements
```

### Fusion Energy

```markdown
For fusion energy papers, pay special attention to:
- Plasma parameters (temperature, density, confinement time)
- Energy gain factors (Q values)
- Pulse durations and stability
- Disruption prediction accuracy
- Comparison to ITER baselines
```

### Climate Science

```markdown
For climate science papers, pay special attention to:
- Projection uncertainties and confidence intervals
- Model validation metrics (RMSE, skill scores)
- Temporal and spatial resolution
- Comparison to CMIP ensembles
- Sea level rise projections with uncertainty bounds
```

### Microbiology / Genomics

```markdown
For microbiology papers, pay special attention to:
- Editing efficiency percentages (for CRISPR papers)
- Off-target rates and detection methods
- Sample sizes and statistical power
- Sequencing depth and coverage
- Reproducibility across conditions
```

### Materials Science

```markdown
For materials science papers, pay special attention to:
- Conductivity, capacity, or efficiency metrics
- Operating conditions (temperature, pressure)
- Cycle stability (number of cycles tested)
- Comparison to commercial materials
- Synthesis reproducibility
```

### Nano Thermal

```markdown
For nanofluid/thermal papers, pay special attention to:
- Thermal conductivity enhancement percentages
- Nanoparticle concentration and size
- Temperature ranges tested
- Viscosity and stability measurements
- Comparison to base fluid
```

### Biomedical Imaging

```markdown
For biomedical imaging papers, pay special attention to:
- Image quality metrics (SNR, CNR, resolution)
- Diagnostic accuracy (sensitivity, specificity)
- Dataset sizes and patient counts
- Comparison to clinical gold standards
- Reconstruction time for real-time claims
```

---

## Usage Instructions

1. Copy the Master Prompt above
2. Replace all `{{PLACEHOLDER}}` values with paper-specific information
3. Add the appropriate domain-specific guidance section
4. Attach the paper PDF
5. Submit to the agent for annotation
6. Validate output against the verification checklist
