# CLAUDE.md - Literature Review Automation System

## What This Is

AI-powered pipeline for conducting comprehensive literature reviews. Ingests PDFs, extracts claims, evaluates evidence quality, performs gap analysis, and generates actionable research recommendations. Research-domain-agnostic via JSON configuration.

## Quick Reference

```bash
# Run full pipeline
python pipeline_orchestrator.py

# Resume from checkpoint
python pipeline_orchestrator.py --resume

# Resume from specific stage
python pipeline_orchestrator.py --resume-from judge

# Batch mode (non-interactive, CI/CD)
python pipeline_orchestrator.py --batch-mode

# Custom research domain
python pipeline_orchestrator.py --research-config domains/my-domain/research_config.json

# Run dashboard
./run_dashboard.sh  # http://localhost:8000

# Run tests
pytest                         # all tests
pytest -m unit                 # unit only
pytest -m integration          # integration only
pytest -m e2e                  # end-to-end only
pytest --cov=. --cov-report=xml  # with coverage
```

## Project Structure

```
literature_review/           # Main Python package (70 modules, ~26K LOC)
  analysis/                  # 21 analysis modules (judge, gap, proof chain, etc.)
  reviewers/                 # Paper screening + deep review
  config/                    # ResearchConfig + ModelConfig loaders
  models/                    # Data models (action vectors, validation strategies)
  utils/                     # 19 utilities (LLM client, cost tracker, rate limiter, etc.)
  cli/                       # Click-based CLI (pillar evolution)
  optimization/              # ROI-based search optimizer
  pipeline/                  # v2 orchestrator
  visualization/             # Proof chain, sufficiency, triangulation viz
  io/                        # File handlers
  triggers/                  # Trigger definitions
webdashboard/                # FastAPI dashboard (REST + WebSocket)
tests/                       # 170 test files across 11 tiers
docs/                        # 67 markdown docs
domains/                     # Research domain configs (JSON)
task-cards/                  # Implementation task specifications
data/                        # Paper storage
scripts/                     # Utility scripts
```

## 5-Stage Pipeline

1. **Journal-Reviewer** (`literature_review.reviewers.journal_reviewer`) - PDF ingestion, metadata extraction, preliminary claims
2. **Judge** (`literature_review.analysis.judge`) - Multi-step claim evaluation with consensus (3 judges)
3. **DRA** (`literature_review.analysis.requirements`) - Conditional deep analysis of rejected claims
4. **Sync** (`scripts.sync_history_to_db`) - Database synchronization from version history
5. **Orchestrator** (`literature_review.orchestrator`) - Gap analysis, recommendations, visualizations

## Key Data Files

- `review_version_history.json` - Single source of truth for all claim evaluations
- `*_database.csv` - Central paper metadata repository (50+ columns)
- `gap_analysis_output/` - Reports, visualizations, state files
- `pipeline_checkpoint.json` - Resume state
- `research_config.json` - Active domain configuration
- `pipeline_config.json` - Pipeline behavior configuration
- `pillar_definitions.json` - Requirements framework (pillars)

## LLM Provider Abstraction

Supports Gemini (primary), OpenAI, Anthropic, and local (Ollama). Switch via:
```python
from literature_review.config.model_config import set_model
set_model("gemini-2.5-flash")  # or "gpt-4-turbo", "claude-3-opus"
```
Or environment: `MODEL_NAME=claude-3-opus python pipeline_orchestrator.py`

## Configuration

- **Research domain**: `research_config.json` or `domains/{id}/research_config.json`
- **Pipeline behavior**: `pipeline_config.json` (timeouts, retry, prefilter, ROI, decay, dedup)
- **API keys**: `.env` file (`GEMINI_API_KEY`, `DASHBOARD_API_KEY`)
- **Model selection**: `ModelConfig` in `literature_review/config/model_config.py`

## Testing Tiers

| Tier | Location | What |
|------|----------|------|
| Unit | `tests/unit/` | Isolated module tests |
| Component | `tests/component/` | Related module groups |
| Integration | `tests/integration/` | Multi-module flows |
| Tier 1-4 | `tests/tier1/` through `tests/tier4/` | Progressive integration |
| E2E | `tests/e2e/` | Full pipeline execution |
| WebUI | `tests/webui/` | Dashboard Playwright tests |
| Golden Dataset | `tests/golden_dataset/` | Reference dataset validation |
| Benchmarks | `tests/benchmarks/` | Performance benchmarks |

## CI/CD

Three GitHub Actions workflows:
- `integration-tests.yml` - Unit + component + integration (PR/push to main)
- `e2e-tests.yml` - End-to-end pipeline
- `dashboard-e2e-tests.yml` - Dashboard Playwright tests

## Conventions

- Python 3.12+
- Formatting: black, flake8, mypy
- Test markers: `@pytest.mark.unit`, `.integration`, `.e2e`
- All pipeline outputs go to `gap_analysis_output/` by default (override with `LITERATURE_REVIEW_OUTPUT_DIR`)
- CSV database filename is auto-generated from domain config
- Version history JSON is the single source of truth; CSV is derived

## Governance

This repo is tracked by [command-center](https://github.com/BootstrapAI-mgmt/command-center) at enforcement level `informational`. Standard governance docs (ARCHITECTURE.md, ROADMAP.md, TODO-MASTER.md, task cards) follow command-center schemas.
