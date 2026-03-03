---
description: Generate API cost reports and review direction recommendations
domain: analysis
type: skill-only
---

## When to Use

Use this skill after pipeline runs to analyze API costs, generate decay impact comparisons, identify high-priority research gaps, or produce visualization plots.

## Prerequisites

- Python 3.9+ with `literature_review` package installed
- Completed pipeline run (needs cost tracker data and gap analysis output)
- For plots: `matplotlib` installed

## Scripts

### 1. API Cost Report

Generates comprehensive cost breakdown by module, paper, and cache efficiency.

```bash
python scripts/generate_cost_report.py
```

**Output includes:**
- Total API calls and cost
- Token consumption breakdown
- Cache savings and efficiency metrics
- Budget status (spent vs remaining)
- Per-module cost breakdown
- Per-paper analysis
- Optimization recommendations

**Output file:** `cost_reports/api_usage_report.json`

### 2. Evidence Decay Impact Report

A/B comparison showing how temporal decay weighting affects gap analysis scores.

```bash
python scripts/generate_decay_impact_report.py
```

**Input files:** Gap analysis report, research config, version history (for publication years)

**Output:** Side-by-side comparison of scores with and without decay weighting.

### 3. Deep Review Directions

Identifies high-priority gaps and generates targeted review directions.

```bash
# Top 10 highest-priority gaps
python scripts/generate_deep_review_directions.py --top 10

# Gaps in a specific pillar below 30% completeness
python scripts/generate_deep_review_directions.py --pillar "Pillar 1" --completeness-max 30

# Only bottleneck gaps
python scripts/generate_deep_review_directions.py --bottlenecks-only
```

| Argument | Default | Purpose |
|----------|---------|---------|
| `--top N` | all | Focus on top N gaps |
| `--pillar` | all | Filter by pillar name |
| `--completeness-max` | 100 | Only gaps below this % |
| `--bottlenecks-only` | false | Only bottleneck gaps |

**Output file:** `gap_analysis_output/deep_review_directions.json`

### 4. Gap Analysis Plots

Generates radar plots and visualizations from gap analysis results.

```bash
python scripts/generate_plots.py
```

**Input:** `gap_analysis_output/gap_analysis_report.json`
**Output directory:** `generated_plots/`

Features: Radar plots with optional velocity data, comparison overlays.

## Typical Workflow

```bash
# After pipeline run:

# 1. Check what it cost
python scripts/generate_cost_report.py

# 2. See decay impact on scores
python scripts/generate_decay_impact_report.py

# 3. Find highest-priority gaps to investigate
python scripts/generate_deep_review_directions.py --top 5 --bottlenecks-only

# 4. Generate visual plots
python scripts/generate_plots.py
```

## Related Skills

- [Literature Pipeline](literature-pipeline.md) — Run pipeline first
- [Evidence Analysis](evidence-analysis.md) — Decay/triangulation/proof chain analysis
