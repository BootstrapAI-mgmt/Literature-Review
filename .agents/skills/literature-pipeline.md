---
description: Run the full literature review pipeline with checkpoint/resume
domain: pipeline
type: skill-only
---

## When to Use

Use this skill to run the complete literature review pipeline, resume from failures, or execute specific stages. The pipeline orchestrates: Journal-Reviewer, Judge, Deep Requirements Analyzer (DRA), Sync, Orchestrator, and Proof Scorecard.

## Prerequisites

- Python 3.9+ with `literature_review` package installed
- `GEMINI_API_KEY` set in `.env` file
- `pipeline_config.json` and `research_config.json` present
- `pillar_definitions.json` present
- Input data in `data/raw/` or `neuromorphic-research_database.csv`

## Pipeline Stages

1. **Journal-Reviewer** — Reviews papers against pillar requirements
2. **Judge** — Evaluates review quality and relevance scoring
3. **DRA (Deep Requirements Analyzer)** — Deep-dives into requirement coverage
4. **Sync** — Synchronizes results across data stores
5. **Orchestrator** — Coordinates final analysis pass
6. **Proof Scorecard** — Generates evidence proof chain scores

## CLI Commands

### Full Pipeline Run
```bash
python pipeline_orchestrator.py
```

### With Logging
```bash
python pipeline_orchestrator.py --log-file pipeline.log
```

### Custom Config
```bash
python pipeline_orchestrator.py --config pipeline_config.json
```

### Resume from Checkpoint
```bash
python pipeline_orchestrator.py --resume
python pipeline_orchestrator.py --resume-from judge
```

### Dry Run (no API calls)
```bash
python pipeline_orchestrator.py --dry-run
```

### Experimental Features
```bash
python pipeline_orchestrator.py --enable-experimental
```

## Key Configuration (`pipeline_config.json`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `retry.max_attempts` | 3 | Max retries per stage |
| `retry.backoff` | exponential | Backoff strategy |
| `circuit_breaker.threshold` | 3 | Failures before circuit opens |
| `v2_features.max_workers` | 4 | Parallel processing workers |
| `evidence_decay.enabled` | true | Temporal decay weighting |
| `deduplication.enabled` | false | Smart dedup before gap analysis |
| `prefilter.threshold` | 0.50 | Relevance prefilter cutoff |

## Pipeline Features (v2.0)

- **Checkpoint/Resume** — Per-paper tracking, resume from any stage
- **Circuit Breaker** — Protects against cascading API failures
- **Cost Tracking** — Budget monitoring with per-module breakdown
- **Smart Error Classification** — Distinguishes transient vs permanent failures
- **API Quota Management** — Rate limiting and budget enforcement
- **Dry-Run Mode** — Validate pipeline without API calls

## Output Files

- `review_log.json` — Paper review results
- `review_version_history.json` — Versioned review history
- `gap_analysis_output/gap_analysis_report.json` — Gap analysis
- `gap_analysis_output/proof_chain.json` — Proof chain analysis
- `cost_reports/api_usage_report.json` — Cost tracking report

## Related Skills

- [Zotero Pipeline](zotero-pipeline.md) — Zotero collection sync
- [Evidence Analysis](evidence-analysis.md) — Post-pipeline analysis
- [Cost Reporting](cost-reporting.md) — API cost reports
- [Testing Suite](testing-suite.md) — Pipeline smoke tests
