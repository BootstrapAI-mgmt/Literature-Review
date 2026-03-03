---
description: Query annotation database for literature review papers
domain: annotation
converts_from: annotation-query MCP server
distilled_date: 2026-03-03
---

## When to Use

Use this skill to search and retrieve annotations from the literature review annotation database. This replaces the `annotation-query` MCP server (490-line `annotation-server/annotation_mcp.py`) with direct SQLite queries via a CLI script.

## Prerequisites

- Python 3.9+ with `sqlite3` (standard library)
- Annotation database built: `python3 annotation-server/build_db.py`
- Database file at `annotation-server/annotations.db`

## CLI Commands

Run: `.agents/cli/annotation-query.sh {search|paper|stats|rebuild} [args]`

| Command | Purpose |
|---------|---------|
| `annotation-query.sh search "neuromorphic"` | Full-text search across annotations |
| `annotation-query.sh paper "smith2024"` | Get all annotations for a specific paper |
| `annotation-query.sh stats` | Database statistics (table counts) |
| `annotation-query.sh rebuild` | Rebuild database from source data |

## Expected Output

Search results with paper ID, section, and content excerpt. Stats show table names and row counts.

## Human Checkpoints

- After `rebuild`, verify row counts match expectations
- Review search results for relevance

## Fallback to MCP

If the CLI script is insufficient for complex queries, re-enable the annotation-query MCP server. In `.mcp.json`, ensure the `annotation-query` entry is present:
```json
"annotation-query": {
  "command": "C:\\Python313\\python.exe",
  "args": ["annotation-server/annotation_mcp.py"]
}
```

## Related Skills

- [Zotero Search](zotero-search.md) — Search Zotero library
- [Literature Pipeline](literature-pipeline.md) — Full pipeline orchestration
