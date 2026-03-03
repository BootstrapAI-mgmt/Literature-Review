---
description: Master index of all CLI+Skills entries for the Literature Review project
---

# Literature Review CLI+Skills Index

This directory contains distilled knowledge from successful task completions.

## Entry Types

Every entry in this index falls into one of three categories:

| Type | Icon | When to Use | Example |
|------|:----:|-------------|---------|
| **CLI+Skill** | 🔧📘 | Repeatable command sequence paired with context docs | Annotation queries, Zotero search |
| **CLI-only** | 🔧 | Pure script, no contextual guidance needed | One-liner helper scripts |
| **Skill-only** | 📘 | Process/checklist where the *thinking* is the value, not a fixed command | Evidence analysis, pipeline orchestration |

> **Key distinction:** If the *output* differs every time but the *process* is repeatable → **Skill-only**.
> If both the process *and* commands are reproducible → **CLI+Skill**.

## How It Works

1. **Agent receives a task** → checks this index for a matching skill
2. **Match found (CLI+Skill or CLI-only)** → execute the CLI script directly
3. **Match found (Skill-only)** → follow the documented process/checklist
4. **No match** → solve normally, then run `/distill` to save for next time
5. **Fallback** → if CLI script fails, re-enable the corresponding MCP server

## Distillation

Run `/distill` after completing any task to save the process for future reuse.
See [distill.md](file:///.agents/workflows/distill.md) for the full workflow.

---

## Skills Registry

| Skill | Type | Domain | CLI Script | Replaces MCP |
|-------|:----:|--------|-----------|-------------|
| [Annotation Query](annotation-query.md) | 🔧📘 | annotation | `cli/annotation-query.sh` | `annotation-query` MCP server |
| [Zotero Pipeline](zotero-pipeline.md) | 📘 | zotero | — | `zotero-pipeline` MCP server |
| [Zotero Search](zotero-search.md) | 🔧📘 | zotero | `cli/zotero-search.sh` | `zotero` MCP (partial — MCP kept for discovery) |
| [Literature Pipeline](literature-pipeline.md) | 📘 | pipeline | — | — |
| [Evidence Analysis](evidence-analysis.md) | 📘 | analysis | — | — |
| [Cost Reporting](cost-reporting.md) | 📘 | analysis | — | — |
| [Data Migration](data-migration.md) | 📘 | data-processing | — | — |
| [n8n Management](n8n-management.md) | 🔧📘 | n8n-management | `cli/n8n-manage.sh` | — |
| [Testing Suite](testing-suite.md) | 📘 | testing | — | — |
| [Doc Update Checklist](doc-update-checklist.md) | 📘 | documentation | — | — |

## MCP Servers Still Active

These MCP servers remain active for use cases that **cannot** be reduced to static CLI scripts:

| MCP Server | Why It Stays |
|-----------|-------------|
| `zotero` (third-party, hybrid) | Complex Zotero library discovery/browsing; simple lookups converted to CLI |
| n8n workflows (10 total) | Stateful: task distribution, state reconciliation, staleness monitoring |
