# n8n → GitHub Actions Migration Outline

> **Status:** Exploratory - Decision pending

## High-Level Migration Map

| n8n Workflow | → | GitHub Actions + Python |
|--------------|---|------------------------|
| Doc Chain - Trigger | → | `.github/workflows/doc-trigger.yml` + `scripts/doc_chain_trigger.py` |
| Doc Chain - Distributor | → | `scripts/task_distributor.py` (called by trigger) |
| Doc Chain - Agent | → | `scripts/doc_chain_agent.py` (Gemini API direct) |
| Doc Chain - PR Review | → | `.github/workflows/pr-review.yml` + `scripts/pr_reviewer.py` |
| Doc Chain - Staleness | → | `.github/workflows/staleness-check.yml` (cron) + `scripts/staleness_checker.py` |
| Doc Chain - State Reconciliation | → | `scripts/state_reconciliation.py` (manual trigger) |
| Doc Chain - Errors | → | Native try/except + GitHub Issues API |
| Doc Chain - Release | → | `.github/workflows/release.yml` |

---

## Proposed Directory Structure

```
.github/
  workflows/
    doc-trigger.yml          # on: push
    pr-review.yml             # on: pull_request
    staleness-check.yml       # on: schedule (cron)
    release.yml               # on: release

scripts/
  doc_chain/
    __init__.py
    trigger.py                # Parse changes, determine affected docs
    distributor.py            # Route to appropriate handler
    agent.py                  # Execute doc updates via AI
    pr_reviewer.py            # PR impact analysis
    staleness_checker.py      # Scheduled staleness detection
    reconciliation.py         # Deep state analysis
  utils/
    ai_client.py              # Gemini/Claude API wrapper
    github_client.py          # GitHub API (via PyGithub or gh CLI)
    matrix_parser.py          # documentation_matrix.json handling
```

---

## Key Translations

### 1. GitHub Webhook → GitHub Actions Trigger
```yaml
# n8n: Webhook node receiving POST
# GitHub Actions equivalent:
on:
  push:
    branches: [main]
    paths: ['docs/**', '*.md', 'literature_review/**']
```

### 2. n8n Code Node → Python Script
```python
# n8n: JavaScript in Code node
# Python equivalent in scripts/doc_chain/trigger.py
def parse_changes(event):
    files = []
    for commit in event.get('commits', []):
        files.extend(commit.get('added', []))
        files.extend(commit.get('modified', []))
    return list(set(files))
```

### 3. n8n AI Node → Direct API Call
```python
# n8n: Gemini node with prompt
# Python equivalent:
import google.generativeai as genai
def generate_tasks(context):
    response = genai.generate_content(SYSTEM_PROMPT + context)
    return json.loads(response.text)
```

### 4. n8n HTTP Request → GitHub API
```python
# n8n: HTTP Request to GitHub API
# Python equivalent using gh CLI or PyGithub:
subprocess.run(['gh', 'issue', 'create', '--title', title, '--body', body])
```

---

## Migration Phases (If Pursued)

### Phase 1: Foundation
- [ ] Create `scripts/doc_chain/` package structure
- [ ] Implement `ai_client.py` (Gemini wrapper)
- [ ] Implement `github_client.py` (gh CLI wrapper)
- [ ] Port `documentation_matrix.json` parser

### Phase 2: Core Workflows
- [ ] Migrate Trigger → `doc-trigger.yml` + `trigger.py`
- [ ] Migrate Distributor → `distributor.py`
- [ ] Migrate Agent → `agent.py`

### Phase 3: Supporting Workflows
- [ ] Migrate PR Review → `pr-review.yml`
- [ ] Migrate Staleness → `staleness-check.yml`
- [ ] Migrate State Reconciliation → `reconciliation.py`

### Phase 4: Cleanup
- [ ] Update test suite for new architecture
- [ ] Deprecate n8n-server/ directory
- [ ] Update documentation

---

## Effort Estimate

| Phase | Effort | Complexity |
|-------|--------|------------|
| Phase 1: Foundation | 2-3 hours | Low |
| Phase 2: Core | 4-6 hours | Medium |
| Phase 3: Supporting | 3-4 hours | Medium |
| Phase 4: Cleanup | 2-3 hours | Low |
| **Total** | **11-16 hours** | Medium |

---

## Decision Factors

**Migrate if:**
- n8n API key issues persist
- Need full Antigravity control
- Want to reduce external dependencies
- Cost is a concern

**Keep n8n if:**
- Visual editing is valuable
- n8n execution history is useful
- API key issues get resolved
- Team prefers low-code approach
