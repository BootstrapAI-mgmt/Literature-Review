---
description: Search Zotero library for papers by keyword, key, or tag
domain: zotero
converts_from: "zotero MCP server (partial — MCP kept for complex discovery)"
distilled_date: 2026-03-03
---

## When to Use

Use this skill for simple Zotero lookups: searching by keyword, retrieving entries by citation key, listing tags, or viewing recent papers. For complex Zotero library browsing and discovery, the `zotero` MCP server remains active.

## Prerequisites

- `all_bib_entries.json` present (run `zotero_pipeline.py` to generate)
- Python 3.9+

## CLI Commands

Run: `.agents/cli/zotero-search.sh {search|get|tags|recent} [args]`

| Command | Purpose |
|---------|---------|
| `zotero-search.sh search "spiking"` | Search across all fields |
| `zotero-search.sh get "smith2024"` | Get full entry by citation key |
| `zotero-search.sh tags` | List top 30 tags by frequency |
| `zotero-search.sh recent 20` | Show 20 most recent entries |

## Fallback to MCP

For complex browsing/discovery, the `zotero` MCP server stays active in `.mcp.json`:
```json
"zotero": {
  "command": "...",
  "args": ["-m", "zotero_mcp"],
  "env": {"ZOTERO_LOCAL": "true"}
}
```

## Related Skills

- [Zotero Pipeline](zotero-pipeline.md) — Full pipeline processing
- [Annotation Query](annotation-query.md) — Query annotation database
