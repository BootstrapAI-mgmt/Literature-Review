---
description: Run the Zotero library processing pipeline
domain: zotero
converts_from: zotero-pipeline MCP server
distilled_date: 2026-03-03
---

## When to Use

Use this skill to process Zotero library data through the automated pipeline. This replaces the `zotero-pipeline` MCP server (158-line `zotero_pipeline_mcp.py`) — the actual pipeline logic lives in `zotero_pipeline.py` (1006 lines), which is already a standalone script.

## Prerequisites

- Python 3.9+ with required dependencies
- Zotero library accessible (local mode: `ZOTERO_LOCAL=true`)
- Pipeline configuration in `pipeline_config.json`

## CLI Commands

### Run Full Pipeline
```bash
python3 zotero_pipeline.py
```

### Run Specific Stage
```bash
python3 zotero_pipeline.py --stage fetch
python3 zotero_pipeline.py --stage process
python3 zotero_pipeline.py --stage analyze
```

## Pipeline Stages

1. **Fetch** — Retrieve papers from Zotero library
2. **Process** — Extract metadata, annotations, tags
3. **Analyze** — Run evidence analysis (decay, triangulation, proof chains)
4. **Report** — Generate output reports

## Expected Output

- Processed paper metadata in data directory
- Analysis reports
- Updated annotation database

## Fallback to MCP

Re-enable in `.mcp.json`:
```json
"zotero-pipeline": {
  "command": "C:\\Python313\\python.exe",
  "args": ["zotero_pipeline_mcp.py"]
}
```

## Related Skills

- [Zotero Search](zotero-search.md) — Individual paper lookups
- [Evidence Analysis](evidence-analysis.md) — Analysis scripts
- [Literature Pipeline](literature-pipeline.md) — Full pipeline orchestration
