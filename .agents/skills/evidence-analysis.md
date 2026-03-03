---
description: Run evidence analysis scripts (decay, triangulation, proof chains)
domain: analysis
type: skill-only
---

## When to Use

Use this skill after a pipeline run to analyze evidence quality, freshness, and coverage. Three complementary analyses provide different lenses on the literature base.

## Prerequisites

- Python 3.9+ with `literature_review` package installed
- Completed pipeline run (needs `review_log.json` and `gap_analysis_output/`)
- `pillar_definitions.json` present

## Analysis Scripts

### 1. Evidence Decay Analysis

Measures temporal freshness of cited evidence using configurable half-life decay.

```bash
python scripts/analyze_evidence_decay.py
python scripts/analyze_evidence_decay.py --half-life 3.0
python scripts/analyze_evidence_decay.py --show-weights
python scripts/analyze_evidence_decay.py --review-log review_log.json --output gap_analysis_output/evidence_decay.json
```

| Argument | Default | Purpose |
|----------|---------|---------|
| `--review-log` | `review_log.json` | Input review data |
| `--gap-analysis` | `gap_analysis_output/gap_analysis_report.json` | Gap analysis input |
| `--output` | `gap_analysis_output/evidence_decay.json` | Output file |
| `--half-life` | 5.0 | Decay half-life in years |
| `--show-weights` | false | Display per-year decay weights |

### 2. Proof Chain Analysis

Maps dependency chains between evidence claims and generates interactive visualization.

```bash
python scripts/analyze_proof_chain.py
python scripts/analyze_proof_chain.py --open
python scripts/analyze_proof_chain.py --viz gap_analysis_output/proof_chain.html
```

| Argument | Default | Purpose |
|----------|---------|---------|
| `--gap-file` | `gap_analysis_output/gap_analysis_report.json` | Gap analysis input |
| `--pillar-file` | `pillar_definitions.json` | Pillar definitions |
| `--output` | `gap_analysis_output/proof_chain.json` | JSON output |
| `--viz` | `gap_analysis_output/proof_chain.html` | HTML visualization |
| `--open` | false | Open HTML in browser |

### 3. Triangulation Analysis

Detects source diversity bias and measures cross-validation strength across evidence sources.

```bash
python scripts/analyze_triangulation.py
python scripts/analyze_triangulation.py --open
python scripts/analyze_triangulation.py --viz gap_analysis_output/triangulation.html
```

| Argument | Default | Purpose |
|----------|---------|---------|
| `--review-log` | `review_log.json` | Input review data |
| `--gap-analysis` | `gap_analysis_output/gap_analysis_report.json` | Gap analysis input |
| `--output` | `gap_analysis_output/triangulation.json` | JSON output |
| `--viz` | `gap_analysis_output/triangulation.html` | HTML visualization |
| `--open` | false | Open HTML in browser |

### 4. Decay Presets Demo

Shows available field-specific half-life presets and auto-detection capability.

```bash
python scripts/demo_decay_presets.py
```

Supported fields: AI/ML, Neuroscience, Materials Science, Chemical Engineering, Software Engineering, and more.

## Typical Workflow

```bash
# 1. Run pipeline first
python pipeline_orchestrator.py

# 2. Analyze evidence freshness
python scripts/analyze_evidence_decay.py --show-weights

# 3. Map proof chain dependencies
python scripts/analyze_proof_chain.py --open

# 4. Check source diversity
python scripts/analyze_triangulation.py --open
```

## Output Files

| Script | JSON Output | HTML Visualization |
|--------|-------------|-------------------|
| Evidence Decay | `gap_analysis_output/evidence_decay.json` | — |
| Proof Chain | `gap_analysis_output/proof_chain.json` | `gap_analysis_output/proof_chain.html` |
| Triangulation | `gap_analysis_output/triangulation.json` | `gap_analysis_output/triangulation.html` |

## Related Skills

- [Literature Pipeline](literature-pipeline.md) — Run pipeline first
- [Cost Reporting](cost-reporting.md) — API cost analysis
