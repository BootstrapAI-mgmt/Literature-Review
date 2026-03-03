---
description: Distill a completed task into reusable CLI commands and Skills documentation
---

# Distillation Workflow

This workflow captures the "journal method" — after any successful task or process,
the agent distills the session into reusable CLI+Skills entries so that identical or similar
work in the future can be executed immediately without rediscovery.

## When to Trigger

Use this workflow when the user says any of the following:
- "Run the distillation process for [task/session]"
- "Distill this session"
- "Journal what we just did"
- "Save the CLI/skills for [task name]"

## Inputs

The user will specify one of:
- **A specific task** — e.g., "distill the annotation query" → distill that single task
- **A workflow** — e.g., "distill the evidence analysis process" → distill a logical group
- **This session** — e.g., "distill this session" → distill all novel work from the current conversation

## Process

### Step 1: Identify What Was Done

Review the conversation/session and extract:
1. **Every CLI command** that was run successfully
2. **Every MCP tool** that was invoked and what it accomplished
3. **Every manual action** the user performed
4. **The order** in which things happened and any dependencies between steps

### Step 2: Classify Each Action

| Category | Action | Destination | Entry Type |
|----------|--------|-------------|:-----------:|
| **CLI+Skill** | `python3 bridge.py`, `zotero-search`, etc. | `.agents/cli/` + `.agents/skills/` | 🔧📘 |
| **Skill-only** | Decision points, analysis interpretation, pipeline orchestration | `.agents/skills/` only | 📘 |
| **MCP-keep** | Live Zotero browsing, n8n workflow CRUD | Note in skill as "use MCP" | — |
| **Not distillable** | One-off edge case, not repeatable | Skip | — |

### Step 3: Write the CLI Script

Create or update a script in `.agents/cli/` following standard conventions:
- `set -euo pipefail`
- Idempotent, parameterized, self-documenting, error-handled

### Step 4: Write the Skill File

Create or update a skill in `.agents/skills/` with YAML frontmatter:
```yaml
---
description: [one-line summary]
domain: [annotation | zotero | pipeline | analysis | data-processing | n8n-management | testing | documentation]
converts_from: [MCP server name, if converting]
distilled_date: [date]
---
```

### Step 5-8: Verify, Update Index, Disable MCP, Commit

Same process as the standard distillation workflow. Update `.agents/skills/SKILL.md` master index, optionally disable replaced MCP entries in `.mcp.json`, and commit with `distill:` prefix.
