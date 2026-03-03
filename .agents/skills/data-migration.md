---
description: Data migration and maintenance scripts for literature review data
domain: data-processing
type: skill-only
---

## When to Use

Use these scripts for one-time migrations, data cleanup, deduplication, and format conversions. Most are idempotent and create backups before modifying data.

## Prerequisites

- Python 3.9+ with `literature_review` package installed
- Relevant data files present (see per-script requirements)

## Scripts

### 1. Convert Reviews to Markdown

Converts `review_version_history.json` entries to human-readable Markdown reports.

```bash
# Single paper
python scripts/convert_review_to_markdown.py 3604281

# All papers
python scripts/convert_review_to_markdown.py --all

# Custom output directory
python scripts/convert_review_to_markdown.py --all --output-dir reviews/generated
```

**Input:** `review_version_history.json`
**Output:** `reviews/generated/` (follows `sample_review` format)

### 2. Smart Deduplication

Semantic similarity-based paper deduplication with configurable threshold.

```bash
# Preview duplicates (dry run)
python scripts/deduplicate_papers.py --dry-run

# Run deduplication
python scripts/deduplicate_papers.py

# Custom threshold
python scripts/deduplicate_papers.py --threshold 0.85
```

| Argument | Default | Purpose |
|----------|---------|---------|
| `--review-log` | `review_log.json` | Input file |
| `--output` | `review_log_deduped.json` | Output file |
| `--threshold` | 0.90 | Similarity threshold (0-1) |
| `--dry-run` | false | Preview only |

### 3. Migrate Deep Coverage

Merges deprecated `deep_coverage_database.json` into `review_version_history.json`.

```bash
python scripts/migrate_deep_coverage.py
```

- Creates `.backup_before_migration` backups
- Merges deep coverage claims into paper Requirement(s) lists
- Creates deprecation notice for old file

### 4. Migrate Pillar Definitions

Restructures `pillar_definitions_enhanced.json` to include benchmark linkage.

```bash
python scripts/migrate_pillar_definitions.py
```

- Creates timestamped backup
- Adds `measurement_method`, `benchmarks`, `benchmark_status`, `validation_evidence` fields
- Adds `validation_strategy` placeholders to requirements
- Validates output schema

### 5. Migrate Orchestrator State

Converts orchestrator state files from v1 to v2 format.

```bash
python scripts/migrate_state.py
python scripts/migrate_state.py custom_state.json
```

- Default input: `orchestrator_state.json`
- Creates timestamped backup (`*.backup_YYYYMMDD_HHMMSS.json`)

### 6. Rebuild Version History

Rebuilds clean `review_version_history.json` from authoritative CSV database.

```bash
python scripts/rebuild_version_history.py
```

**Problem solved:** Original file was corrupted/bloated (192MB, 38K+ duplicate entries for ~900 papers).
**Input:** `neuromorphic-research_database.csv`
**Output:** `review_version_history_REBUILT.json` (one clean entry per paper)

### 7. Post-Merge Validation

Validates PR merge integrity without requiring API calls.

```bash
python scripts/post_merge_validation.py
```

**Tests:**
1. Module import validation (Judge, DRA, Deep-Reviewer)
2. Version History functions
3. DRA prompting with pillar definitions
4. Large document chunking and batching

## Safety Notes

- All migration scripts create backups before modifying data
- Use `--dry-run` where available to preview changes
- Deduplication and migration scripts are designed to be idempotent
- `rebuild_version_history.py` writes to a new file (`_REBUILT` suffix) — does not overwrite original

## Related Skills

- [Literature Pipeline](literature-pipeline.md) — Pipeline that produces data these scripts process
- [Evidence Analysis](evidence-analysis.md) — Analysis scripts that consume migrated data
