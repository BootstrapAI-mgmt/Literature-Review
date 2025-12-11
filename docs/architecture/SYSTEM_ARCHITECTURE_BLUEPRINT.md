# System Architecture Blueprint

> **Living Document**: This architectural blueprint is automatically maintained by the n8n documentation chain. Updates are triggered when source code changes affect system architecture.

**Version:** 1.0.0  
**Last Updated:** December 11, 2025  
**Status:** Current

---

## Overview

The Literature Review Automation System is an AI-powered pipeline for conducting comprehensive literature reviews in neuromorphic computing research. The system automates paper screening, claim extraction, evidence evaluation, gap analysis, and convergence tracking.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Literature Review Automation                      │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Ingest    │→ │   Analyze   │→ │   Evaluate  │→ │  Converge  │ │
│  │   Papers    │  │   Claims    │  │   Evidence  │  │    Gaps    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│         ↓               ↓               ↓               ↓          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Web Dashboard (FastAPI + HTMX)                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Pipeline Orchestrator (`pipeline_orchestrator.py`)

The central coordinator that manages the 5-stage review pipeline.

**Responsibilities:**
- Sequential stage execution with dependency management
- Checkpoint/resume capability for interrupted runs
- Automatic retry with exponential backoff
- Circuit breaker for failure prevention
- Batch mode for CI/CD integration

**Pipeline Stages:**

| Stage | Component | Purpose |
|-------|-----------|---------|
| 1 | Journal-Reviewer | Screen papers, extract claims |
| 2 | Judge | Evaluate claims against requirements |
| 3 | DeepRequirementsAnalyzer | Re-analyze rejected claims (conditional) |
| 4 | Sync | Update CSV database from version history |
| 5 | Orchestrator | Gap analysis and convergence |

**Key Features:**
- `--resume` - Resume from last checkpoint
- `--batch-mode` - Non-interactive execution
- `--prefilter` - Gap-targeted paper filtering
- `--incremental` - Only analyze new papers

---

### 2. Literature Review Package (`literature_review/`)

Core analysis functionality organized into submodules:

```
literature_review/
├── analysis/           # Evaluation & scoring
│   ├── judge.py        # Claim evaluation
│   ├── proof_chain.py  # Evidence chain analysis
│   ├── triangulation.py # Cross-source validation
│   ├── gap_analyzer.py # Gap identification
│   └── recommendation.py # Search recommendations
├── reviewers/          # Paper processing
│   ├── journal_reviewer.py  # Initial screening
│   └── deep_reviewer.py     # Deep analysis
├── utils/              # Shared utilities
│   ├── cost_tracker.py      # API cost monitoring
│   ├── evidence_decay.py    # Temporal relevance
│   ├── global_rate_limiter.py # Rate limiting
│   └── incremental_analyzer.py # Delta analysis
├── visualization/      # Report generation
│   ├── proof_chain_viz.py
│   └── triangulation_viz.py
└── orchestrator.py     # Gap convergence
```

---

### 3. Web Dashboard (`webdashboard/`)

FastAPI-based web interface for job management and monitoring.

**Architecture:**
- **Backend:** FastAPI with async endpoints
- **Frontend:** HTMX for dynamic updates, Jinja2 templates
- **Database:** SQLite for job state persistence
- **Real-time:** Server-Sent Events (SSE) for progress

**Key Components:**

| Component | Purpose |
|-----------|---------|
| `app.py` | Main FastAPI application (183KB) |
| `database_builder.py` | Job state management |
| `eta_calculator.py` | Progress estimation |
| `api/` | REST API endpoints |
| `templates/` | HTML templates |
| `static/` | CSS, JavaScript, assets |

**API Endpoints:**
- `POST /jobs` - Create new review job
- `GET /jobs/{id}` - Get job status
- `POST /jobs/{id}/retry` - Retry failed job
- `GET /jobs/{id}/stream` - SSE progress stream

---

### 4. Evidence Quality System

Multi-dimensional evidence evaluation framework:

```
Evidence Quality Score
├── Source Triangulation    # Cross-validation across sources
├── Temporal Coherence      # Recency and temporal consistency
├── Proof Chain Validity    # Logical evidence chains
├── Publication Bias        # Bias detection and adjustment
└── Evidence Decay          # Time-based relevance decay
```

**Key Modules:**
- `evidence_triangulation.py` - Cross-source validation
- `evidence_decay.py` - Temporal relevance scoring
- `proof_chain.py` - Evidence chain analysis
- `publication_bias.py` - Bias detection

---

### 5. Incremental Review System

Optimized re-analysis for iterative literature reviews:

**Features:**
- Paper-level delta detection
- Previous results preservation
- 60-80% faster subsequent runs
- API cost reduction

**Components:**
- `incremental_analyzer.py` - Change detection
- `state_manager.py` - Checkpoint management
- Gap-targeted pre-filtering

---

## Data Flow

```
PDF Papers → Journal Reviewer → Claims Database
                    ↓
              Review Log (JSON)
                    ↓
         Judge → Accepted/Rejected Claims
                    ↓
    [If Rejections] → Deep Requirements Analyzer
                    ↓
              Sync to CSV Database
                    ↓
         Orchestrator → Gap Analysis Report
                    ↓
         Search Recommendations → Next Iteration
```

**Key Data Files:**
| File | Purpose |
|------|---------|
| `review_log.json` | Paper review records |
| `review_version_history.json` | Version tracking |
| `*_database.csv` | Structured paper data |
| `gap_analysis_output/` | Generated reports |

---

## Configuration

### Pipeline Configuration (`pipeline_config.json`)

```json
{
  "version": "1.2.0",
  "output_dir": "gap_analysis_output",
  "stage_timeout": 7200,
  "retry_policy": {
    "enabled": true,
    "default_max_attempts": 3,
    "circuit_breaker_threshold": 3
  },
  "prefilter": {
    "enabled": true,
    "threshold": 0.50
  }
}
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Google AI API access |
| `DASHBOARD_API_KEY` | Dashboard authentication |
| `LITERATURE_REVIEW_OUTPUT_DIR` | Custom output path |

---

## Integration Points

### External Services
- **Google Gemini AI** - LLM for analysis
- **GitHub** - Version control, CI/CD
- **n8n** - Documentation automation

### CI/CD Workflows
- `integration-tests.yml` - Integration test suite
- `e2e-tests.yml` - End-to-end tests
- `docker-compose.yml` - Containerized deployment

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12+ |
| AI/LLM | Google Gemini API |
| Web Framework | FastAPI |
| Frontend | HTMX, Jinja2 |
| Database | SQLite, JSON |
| Testing | pytest |
| CI/CD | GitHub Actions |
| Containerization | Docker |
| Documentation Automation | n8n |

---

## Future Architecture Considerations

1. **Scalability**: Worker queue for parallel paper processing
2. **Multi-tenancy**: Separate workspaces for different research projects
3. **API Gateway**: Rate limiting and authentication at edge
4. **Caching**: Redis for expensive computation results
5. **Monitoring**: OpenTelemetry integration for observability

---

## Related Documentation

- [WORKFLOW_EXECUTION_GUIDE.md](../guides/WORKFLOW_EXECUTION_GUIDE.md) - Pipeline execution
- [DASHBOARD_GUIDE.md](../DASHBOARD_GUIDE.md) - Web interface guide
- [EVIDENCE_SCORING_DOCUMENTATION.md](../EVIDENCE_SCORING_DOCUMENTATION.md) - Evidence quality
- [INCREMENTAL_REVIEW_USER_GUIDE.md](../INCREMENTAL_REVIEW_USER_GUIDE.md) - Incremental mode
- [ARCHITECTURE_REFACTOR.md](ARCHITECTURE_REFACTOR.md) - Repository structure

---

*This document is maintained by the automated documentation chain. See [N8N_DOCUMENTATION_CHAIN_BLUEPRINT.md](../N8N_DOCUMENTATION_CHAIN_BLUEPRINT.md) for details.*
