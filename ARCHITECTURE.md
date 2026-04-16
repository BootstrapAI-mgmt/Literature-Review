# Architecture — Literature Review Automation System

## What This Is

An AI-powered pipeline that automates systematic literature reviews. It ingests research PDFs, extracts and evaluates claims against configurable requirement frameworks, performs gap analysis across a body of evidence, and generates actionable recommendations with interactive visualizations. The system is research-domain-agnostic: switching domains requires only JSON configuration changes, not code modifications.

## Design Principles

1. **Research-domain agnosticism** — The pipeline processes any research domain through external JSON configuration (`research_config.json`, `pillar_definitions.json`). Domain vocabulary, evaluation criteria, and output naming are all config-driven, so no Python code changes are needed to study a new field.

2. **Single source of truth for evidence** — All claim evaluations flow through `review_version_history.json`, which records the full lineage of each claim (extraction, judgment, appeal, re-judgment). The CSV database is a derived artifact regenerated from this history during the Sync stage.

3. **Provider-agnostic LLM abstraction** — An abstract `LLMClient` base class with concrete implementations for Gemini, OpenAI, Anthropic, and local models. Switching providers requires one config change; the pipeline code never references a specific provider.

4. **Checkpoint-and-resume resilience** — Every pipeline stage writes progress to `pipeline_checkpoint.json`. Failures resume from the last completed stage. Circuit breakers, exponential backoff, and retry budgets prevent runaway API costs.

5. **Incremental analysis** — The system detects which papers are new or modified and only re-analyzes those, preserving prior results. Gap-targeted pre-filtering further reduces API calls by scoring papers against unfilled gaps before processing.

6. **Separation of analysis and presentation** — Analysis modules produce JSON outputs; visualization modules consume those JSONs to generate interactive HTML dashboards. The FastAPI web dashboard is a separate deployment surface that orchestrates the same pipeline stages.

## System Overview

```
                        ┌─────────────────────────────────────────────────────────────┐
                        │                    Configuration Layer                       │
                        │  research_config.json   pipeline_config.json   .env          │
                        │  pillar_definitions.json  domains/{id}/                      │
                        └────────────────────────────┬────────────────────────────────┘
                                                     │
                        ┌────────────────────────────▼────────────────────────────────┐
                        │              pipeline_orchestrator.py (v2.0)                 │
                        │   Checkpoint/Resume · Retry · Cost Tracking · ROI Optimizer  │
                        └──┬──────────┬──────────┬──────────┬──────────┬──────────────┘
                           │          │          │          │          │
                    ┌──────▼───┐ ┌────▼─────┐ ┌─▼────┐ ┌──▼───┐ ┌───▼──────────┐
                    │ Stage 1  │ │ Stage 2  │ │St. 3 │ │St. 4 │ │   Stage 5    │
                    │ Journal  │ │  Judge   │ │ DRA  │ │ Sync │ │ Orchestrator │
                    │ Reviewer │ │(3-judge  │ │(cond)│ │      │ │ Gap Analysis │
                    │(module)  │ │consensus)│ │      │ │      │ │ + Viz        │
                    └──────────┘ └──────────┘ └──────┘ └──────┘ └──────────────┘
                         │            │           │         │          │
                         ▼            ▼           ▼         ▼          ▼
                    ┌─────────────────────────────────────────────────────────────┐
                    │                    Data Layer                                │
                    │  review_version_history.json  ·  *_database.csv             │
                    │  gap_analysis_output/  ·  pipeline_checkpoint.json           │
                    └─────────────────────────────────────────────────────────────┘
                                                     │
                        ┌────────────────────────────▼────────────────────────────────┐
                        │                  webdashboard/ (FastAPI)                     │
                        │   REST API · WebSocket · Job Runner · PDF Upload · Reports   │
                        └─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
Literature-Review/
├── pipeline_orchestrator.py          # Main CLI entry point (5-stage pipeline v2.0)
│
├── literature_review/                # Main Python package (~26K LOC)
│   ├── analysis/                     # 21 analysis modules
│   │   ├── judge.py                  # v2.0 claim evaluation engine
│   │   ├── requirements.py           # DeepRequirementsAnalyzer (DRA)
│   │   ├── gap_analyzer.py           # Gap identification + ranking
│   │   ├── proof_scorecard.py        # Evidence completeness scoring
│   │   ├── proof_chain.py            # Evidence chain construction
│   │   ├── sufficiency_matrix.py     # Per-requirement evidence coverage
│   │   ├── evidence_triangulation.py # Multi-source verification
│   │   ├── action_generator.py       # Research → executable actions
│   │   ├── benchmark_analyzer.py     # Benchmark coverage analysis
│   │   ├── grade_assessment.py       # GRADE methodological quality
│   │   ├── publication_bias.py       # Publication bias detection
│   │   ├── recommendation.py         # Gap-closing recommendations
│   │   ├── relevance_assessor.py     # Paper relevance scoring
│   │   ├── result_merger.py          # Incremental result merging
│   │   ├── pillar_evolution.py       # Requirement modification tracking
│   │   ├── validation_tracker.py     # Requirement validation
│   │   ├── research_log_manager.py   # Version history management
│   │   ├── domain_stakeholder_extractor.py
│   │   ├── triangulation.py
│   │   └── proof_scorecard_viz.py
│   │
│   ├── reviewers/                    # Paper screening
│   │   ├── journal_reviewer.py       # PDF → structured claims
│   │   ├── deep_reviewer.py          # Deep operationalization review
│   │   └── prompts/                  # LLM prompt templates
│   │
│   ├── config/                       # Configuration management
│   │   ├── research_config.py        # Domain config loader (ResearchConfig)
│   │   └── model_config.py           # LLM provider abstraction (ModelConfig)
│   │
│   ├── models/                       # Data models
│   │   ├── action_vector.py          # Executable action structures
│   │   ├── validation_strategy.py    # Validation definitions
│   │   └── domain_stakeholder.py     # Stakeholder models
│   │
│   ├── utils/                        # 18 utility modules
│   │   ├── llm_client.py             # Abstract LLMClient + provider impls
│   │   ├── api_manager.py            # API orchestration + provider switching
│   │   ├── cost_tracker.py           # Per-model/stage cost tracking
│   │   ├── global_rate_limiter.py    # Token-bucket rate limiting
│   │   ├── model_cache.py            # Response caching (3600s TTL)
│   │   ├── model_fallback.py         # Fallback chain management
│   │   ├── relevance_scorer.py       # Gap-targeted paper scoring
│   │   ├── evidence_decay.py         # Temporal evidence weighting
│   │   ├── smart_dedup.py            # Intelligent deduplication
│   │   ├── incremental_analyzer.py   # New/modified paper detection
│   │   ├── state_manager.py          # Pipeline state persistence
│   │   ├── gap_extractor.py          # Gap extraction utilities
│   │   ├── api_costs.py              # Pricing tables per provider
│   │   ├── rate_limiter.py           # Legacy rate limiter
│   │   ├── data_helpers.py           # Data manipulation
│   │   ├── decay_presets.py          # Evidence decay field presets
│   │   └── plotter.py               # Visualization helpers
│   │
│   ├── cli/                          # Click CLI
│   │   └── evolution_cli.py          # Pillar evolution management
│   │
│   ├── optimization/                 # Cost optimization
│   │   └── search_optimizer.py       # ROI-based paper selection
│   │
│   ├── pipeline/                     # Pipeline variants
│   │   └── orchestrator_v2.py        # v2 orchestrator
│   │
│   ├── visualization/                # Interactive HTML generators
│   │   ├── proof_chain_viz.py
│   │   ├── sufficiency_matrix_viz.py
│   │   └── triangulation_viz.py
│   │
│   ├── triggers/                     # Analysis triggers
│   │   └── deep_review_triggers.py
│   │
│   └── io/                           # File I/O
│       └── __init__.py
│
├── webdashboard/                     # FastAPI web dashboard (v2.0.0)
│   ├── app.py                        # FastAPI application + route mounting
│   ├── job_runner.py                 # Job execution engine
│   ├── duplicate_detector.py         # Upload deduplication
│   ├── eta_calculator.py             # Time estimation
│   ├── prompt_handler.py             # WebSocket interactive prompts
│   ├── database_builder.py           # Database construction from uploads
│   ├── api/                          # API route modules
│   │   ├── incremental.py            # Incremental mode endpoints
│   │   ├── bulk_operations.py        # Batch processing
│   │   └── system_metrics.py         # System monitoring
│   ├── static/                       # Frontend assets
│   └── templates/                    # HTML templates
│
├── tests/                            # 170 test files
│   ├── unit/                         # Isolated module tests
│   ├── component/                    # Related module groups
│   ├── integration/                  # Multi-module flows
│   ├── tier1/ through tier4/         # Progressive integration levels
│   ├── e2e/                          # Full pipeline execution
│   ├── webui/                        # Playwright dashboard tests
│   ├── golden_dataset/               # Reference dataset validation
│   ├── benchmarks/                   # Performance benchmarks
│   ├── validation/                   # Validation framework tests
│   └── conftest.py                   # Shared fixtures
│
├── docs/                             # 67 documentation files
│   ├── architecture/                 # System design analysis
│   ├── guides/                       # Workflow execution guides
│   ├── assessments/                  # Technical evaluations
│   ├── status-reports/               # Progress tracking
│   ├── claude-integration/           # Claude Desktop integration
│   ├── api/                          # OpenAPI specs
│   └── archive/                      # Historical docs
│
├── domains/                          # Research domain configurations
│   ├── neuromorphic-computing/       # Default domain
│   │   ├── research_config.json
│   │   └── pillar_definitions.json
│   └── example-domain/               # Template for new domains
│
├── task-cards/                       # Implementation task specifications
│   ├── agent/                        # Agent-related cards
│   ├── automation/                   # Pipeline automation cards
│   ├── testing/                      # Test infrastructure cards
│   ├── evidence-enhancement/         # Evidence quality cards
│   └── dashboard-cli-parity/         # Dashboard feature cards
│
├── data/                             # Paper storage
│   └── raw/                          # Raw PDF inputs
│
├── scripts/                          # Utility scripts (diagnostics, migration, demos)
│
├── .github/workflows/                # CI/CD
│   ├── integration-tests.yml         # Unit + component + integration
│   ├── e2e-tests.yml                 # End-to-end pipeline
│   └── dashboard-e2e-tests.yml       # Playwright dashboard tests
│
├── research_config.json              # Active domain configuration
├── pipeline_config.json              # Pipeline behavior configuration
├── pillar_definitions.json           # Requirements framework
├── requirements.txt                  # Production dependencies
├── requirements-dev.txt              # Development dependencies
├── requirements-dashboard.txt        # Dashboard dependencies
└── .env.example                      # API key template
```

## Key Interfaces

### Pipeline Orchestrator CLI

**Inputs:**
- PDF files in `data/raw/` or configured input directory
- `research_config.json` — domain vocabulary, evaluation criteria, research questions
- `pipeline_config.json` — timeouts, retry policy, prefilter settings, ROI optimizer
- `pillar_definitions.json` — requirement framework (pillars) for claim evaluation

**Outputs:**
- `review_version_history.json` — complete claim evaluation lineage
- `*_database.csv` — paper metadata with 50+ columns
- `gap_analysis_output/` — JSON reports, executive summary, HTML visualizations
- `pipeline_checkpoint.json` — resumable pipeline state

**Example:**
```bash
python pipeline_orchestrator.py \
  --research-config domains/neuromorphic-computing/research_config.json \
  --config pipeline_config.json \
  --batch-mode \
  --log-file pipeline.log
```

### LLM Client Abstraction

**Inputs:**
- `prompt: str` — the generation prompt
- `system_prompt: str` — optional system context
- `json_mode: bool` — request structured JSON output

**Outputs:**
- `str` — generated text or JSON string
- Token counts available via `get_token_counts()`

**Example:**
```python
from literature_review.config.model_config import get_model_config
from literature_review.utils.llm_client import create_client

config = get_model_config()
client = create_client(config)
response = client.generate(prompt="Analyze this claim...", json_mode=True)
```

### FastAPI Dashboard API

**Inputs:**
- PDF uploads via `/api/uploads`
- Job configuration via `/api/jobs` (POST)
- WebSocket connections at `/ws/jobs`

**Outputs:**
- Job status and progress via REST and WebSocket
- Report downloads as ZIP via `/api/reports`
- System metrics via `/api/metrics`

**Example:**
```bash
# Start the dashboard
uvicorn webdashboard.app:app --host 0.0.0.0 --port 8000

# Create a job
curl -X POST http://localhost:8000/api/jobs \
  -H "Authorization: Bearer $DASHBOARD_API_KEY" \
  -F "files=@paper.pdf"
```

### Research Domain Configuration

**Inputs:**
- `research_config.json` — domain ID, name, research questions, vocabulary, scoring thresholds
- `pillar_definitions.json` — requirement definitions for claim evaluation

**Outputs:**
- `ResearchConfig` dataclass used by all pipeline stages
- Auto-generated database filename based on domain ID
- Domain-specific prompt context for LLM calls

**Example:**
```bash
# Create a new domain
cp -r domains/example-domain domains/my-research
# Edit domains/my-research/research_config.json
python pipeline_orchestrator.py --research-config domains/my-research/research_config.json
```

## Dependencies

### External

| Package | Version | Purpose |
|---------|---------|---------|
| pandas | >= 2.0.0 | Data processing, CSV database |
| google-generativeai | >= 0.3.0 | Gemini LLM SDK (v1) |
| google-genai | >= 0.1.0 | Gemini LLM SDK (v2) |
| fastapi | >= 0.104.0 | Web dashboard framework |
| uvicorn | >= 0.24.0 | ASGI server |
| plotly | >= 5.14.0 | Interactive visualizations |
| sentence-transformers | >= 2.2.0 | Semantic similarity / NLP |
| pdfplumber | >= 0.10.0 | PDF text extraction |
| pypdf | >= 3.15.0 | PDF metadata reading |
| PyMuPDF | >= 1.23.0 | Enhanced PDF processing |
| networkx | >= 3.0 | Citation graph analysis |
| scikit-learn | >= 1.3.0 | Clustering, ML utilities |
| scipy | >= 1.11.0 | Scientific computing |
| pytest | >= 7.4.0 | Testing framework |
| playwright | >= 1.40.0 | Browser-based UI testing |

### Internal (BootstrapAI-mgmt)

| Repo | Relationship |
|------|-------------|
| command-center | Governance validation (informational enforcement) |
