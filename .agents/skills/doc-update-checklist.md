---
description: Checklist for updating documentation after code changes
domain: documentation
type: skill-only
---

## When to Use

Use this checklist after completing any significant code change, feature addition, or pipeline modification to ensure documentation stays current.

## Post-Change Documentation Checklist

### 1. Skill Files
- [ ] If a new script was added, create a skill doc in `.agents/skills/`
- [ ] If a script's CLI interface changed, update its skill doc
- [ ] If a script was removed, remove or archive its skill doc
- [ ] Update `SKILL.md` master index if entries changed

### 2. Pipeline Documentation
- [ ] If pipeline stages changed, update `literature-pipeline.md`
- [ ] If config schema changed, update relevant skill docs
- [ ] If new output files are produced, document them

### 3. Configuration
- [ ] If `pipeline_config.json` schema changed, update skill docs
- [ ] If `research_config.json` changed, update relevant references
- [ ] If `.mcp.json` changed, update `n8n-management.md` or relevant skill

### 4. n8n Workflows
- [ ] If workflows were added/removed, update `n8n-management.md` workflow table
- [ ] If workflow sync process changed, update CLI script

### 5. Testing
- [ ] If new test tiers were added, update `testing-suite.md`
- [ ] If test prerequisites changed, update skill docs
- [ ] Run post-merge validation after documentation changes

### 6. Cross-Repo Consistency
- [ ] If `.agents/` structure patterns changed, check alignment with:
  - `dissertation-formatting/.agents/`
  - `Automated-Digital-Content/.agents/`
- [ ] If distillation workflow was refined, update `distill.md` in all repos

## Distillation Trigger

After completing a multi-step task, consider whether it should be distilled into a reusable skill:

1. Was the task repeated or likely to recur?
2. Did it involve 3+ steps or non-obvious commands?
3. Would another agent benefit from a documented procedure?

If yes to any, follow the [Distillation Workflow](../workflows/distill.md).

## Related Skills

- [Distillation Workflow](../workflows/distill.md) — How to create new skills
- [SKILL.md](SKILL.md) — Master skill index
