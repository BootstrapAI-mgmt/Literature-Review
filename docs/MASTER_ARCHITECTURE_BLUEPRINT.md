# Master Architecture Blueprint

> **Status:** Current State Snapshot  
> **Purpose:** Documents the implemented architecture as of this date. This is NOT a roadmap—see [MASTER_REPOSITORY_ROADMAP.md](MASTER_REPOSITORY_ROADMAP.md) for planned work.

**Version:** 1.0.0  
**Created:** December 19, 2025  
**Scope:** Repository architecture only (excludes external automation/n8n)

---

## Executive Summary

The Literature Review Automation System is an AI-powered pipeline for conducting comprehensive, domain-agnostic literature reviews. The system automates paper screening, claim extraction, evidence evaluation, gap analysis, and convergence tracking through a 5-stage orchestrated pipeline with web dashboard support.

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                      LITERATURE REVIEW AUTOMATION SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────┐ │
│  │   STAGE 1       │   │   STAGE 2       │   │   STAGE 3       │   │  STAGE 4    │ │
│  │  Journal        │──▶│   Judge         │──▶│  Deep Review    │──▶│   Sync      │ │
│  │  Reviewer       │   │  Evaluation     │   │  (Conditional)  │   │  to CSV     │ │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘   └─────────────┘ │
│          │                     │                     │                     │        │
│          ▼                     ▼                     ▼                     ▼        │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        review_log.json + review_version_history.json         │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                            │                                        │
│                                            ▼                                        │
│                              ┌─────────────────────────────┐                        │
│                              │         STAGE 5             │                        │
│                              │  Orchestrator Gap Analysis  │                        │
│                              └─────────────────────────────┘                        │
│                                            │                                        │
│                                            ▼                                        │
│                              ┌─────────────────────────────┐                        │
│                              │   gap_analysis_output/      │                        │
│                              │   - gaps_report.md          │                        │
│                              │   - search_recommendations  │                        │
│                              │   - convergence_status      │                        │
│                              └─────────────────────────────┘                        │
│                                                                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                         WEB DASHBOARD (FastAPI + HTMX)                               │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  Job Management │ Progress Tracking │ Evidence Browser │ Gap Visualization  │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Package Structure

### Root Directory Layout

```
Literature-Review/
├── literature_review/          # Core Python package
├── webdashboard/               # Web interface application
├── scripts/                    # Standalone utilities
├── tests/                      # Test suites
├── docs/                       # Documentation
├── task-cards/                 # Development task cards
├── domains/                    # Research domain configurations
├── data/                       # Data files
├── gap_analysis_output/        # Generated reports
├── pipeline_orchestrator.py    # Main entry point
├── pipeline_config.json        # Pipeline configuration
├── research_config.json        # Research domain settings
├── pillar_definitions.json     # Research pillar definitions
└── requirements.txt            # Python dependencies
```

### Core Package: `literature_review/`

```
literature_review/
├── __init__.py
├── orchestrator.py                 # Gap analysis & convergence
├── orchestrator_integration.py     # Pipeline coordination
├── metadata_extractor.py           # Paper metadata extraction
│
├── config/                         # Configuration management
│   ├── __init__.py
│   └── research_config.py          # ResearchConfig class
│
├── analysis/                       # Evaluation & scoring modules
│   ├── __init__.py
│   ├── judge.py                    # Claim evaluation (Accept/Reject/Flag)
│   ├── gap_analyzer.py             # Gap identification
│   ├── recommendation.py           # Search recommendations
│   ├── proof_chain.py              # Evidence chain analysis
│   ├── proof_scorecard.py          # Evidence scoring
│   ├── proof_scorecard_viz.py      # Scorecard visualization
│   ├── triangulation.py            # Cross-source validation
│   ├── evidence_triangulation.py   # Multi-source evidence
│   ├── publication_bias.py         # Bias detection
│   ├── grade_assessment.py         # GRADE quality assessment
│   ├── requirements.py             # Requirements analysis
│   ├── relevance_assessor.py       # Relevance scoring
│   ├── result_merger.py            # Result consolidation
│   └── sufficiency_matrix.py       # Evidence sufficiency
│
├── reviewers/                      # Paper processing
│   ├── __init__.py
│   ├── journal_reviewer.py         # Initial paper screening
│   └── deep_reviewer.py            # Deep analysis for appeals
│
├── triggers/                       # Automation triggers
│   ├── __init__.py
│   ├── README.md
│   └── deep_review_triggers.py     # Deep review trigger logic
│
├── pipeline/                       # Pipeline components
│   ├── __init__.py
│   └── orchestrator_v2.py          # V2 pipeline orchestrator
│
├── optimization/                   # Performance optimization
│   ├── __init__.py
│   └── search_optimizer.py         # Search query optimization
│
├── utils/                          # Shared utilities
│   ├── __init__.py
│   ├── cost_tracker.py             # API cost monitoring
│   ├── api_costs.py                # Cost calculation
│   ├── api_manager.py              # API client management
│   ├── data_helpers.py             # Data manipulation
│   ├── evidence_decay.py           # Temporal relevance decay
│   ├── decay_presets.py            # Decay configuration
│   ├── gap_extractor.py            # Gap extraction utilities
│   ├── global_rate_limiter.py      # Rate limiting
│   ├── incremental_analyzer.py     # Delta analysis
│   ├── plotter.py                  # Chart generation
│   ├── relevance_scorer.py         # Relevance scoring
│   ├── smart_dedup.py              # Duplicate detection
│   └── state_manager.py            # Checkpoint management
│
├── visualization/                  # Report generation
│   ├── __init__.py
│   ├── proof_chain_viz.py          # Proof chain diagrams
│   ├── sufficiency_matrix_viz.py   # Matrix visualization
│   └── triangulation_viz.py        # Triangulation diagrams
│
└── io/                             # Input/Output handling
    └── __init__.py
```

### Web Dashboard: `webdashboard/`

```
webdashboard/
├── __init__.py
├── app.py                      # FastAPI application
├── database_builder.py         # Job state persistence
├── duplicate_detector.py       # Paper deduplication
├── eta_calculator.py           # Progress estimation
├── job_runner.py               # Job execution
├── prompt_handler.py           # User prompt handling
├── api/                        # REST API endpoints
├── templates/                  # Jinja2 HTML templates
└── static/                     # CSS, JavaScript, assets
```

---

## Core Components

### 1. Pipeline Orchestrator

**File:** `pipeline_orchestrator.py`

The central entry point that manages the 5-stage review pipeline.

**Capabilities:**
- Sequential stage execution with dependency management
- Checkpoint/resume for interrupted runs
- Automatic retry with exponential backoff
- Circuit breaker for failure prevention
- Batch mode for CI/CD integration
- Incremental mode for delta analysis
- Gap-targeted paper pre-filtering

**Pipeline Stages:**

| Stage | Component | Purpose | Output |
|-------|-----------|---------|--------|
| 1 | Journal Reviewer | Screen papers, extract claims | `review_log.json` |
| 2 | Judge | Evaluate claims against pillars | Accept/Reject/Flag decisions |
| 3 | Deep Reviewer | Re-analyze rejected claims (conditional) | Enhanced evidence |
| 4 | Sync | Update CSV from version history | `*_database.csv` |
| 5 | Orchestrator | Gap analysis and convergence | `gap_analysis_output/` |

**CLI Flags:**
```bash
python pipeline_orchestrator.py \
  --research-config research_config.json \
  --resume                # Resume from last checkpoint
  --batch-mode            # Non-interactive execution
  --prefilter             # Gap-targeted paper filtering
  --incremental           # Only analyze new papers
  --max-workers 4         # Parallel processing workers
```

### 2. Journal Reviewer

**File:** `literature_review/reviewers/journal_reviewer.py`

Initial paper screening and claim extraction using LLM analysis.

**Capabilities:**
- PDF text extraction
- Relevance assessment against research pillars
- Claim extraction with evidence markers
- Page number and section tracking
- Provenance metadata capture

### 3. Judge

**File:** `literature_review/analysis/judge.py`

Evaluates extracted claims against research requirements.

**Capabilities:**
- Multi-dimensional evidence scoring (6 dimensions)
- Accept/Reject/Flag decisions
- Pillar alignment assessment
- Consensus review triggering for borderline claims
- Appeal routing to Deep Reviewer

**Evidence Scoring Dimensions:**
1. Source credibility
2. Methodological rigor
3. Reproducibility
4. Sample size adequacy
5. Temporal relevance
6. Cross-validation strength

### 4. Deep Reviewer

**File:** `literature_review/reviewers/deep_reviewer.py`

In-depth analysis for rejected or flagged claims.

**Capabilities:**
- Extended evidence extraction
- Multi-pass analysis
- Additional source discovery
- Enhanced provenance tracking

### 5. Gap Analyzer

**File:** `literature_review/analysis/gap_analyzer.py`

Identifies research gaps and generates recommendations.

**Capabilities:**
- Gap identification by pillar
- Gap severity scoring
- Search query recommendations
- Convergence tracking

### 6. Evidence Quality System

**Modules:**
- `proof_chain.py` - Evidence chain analysis
- `triangulation.py` - Cross-source validation
- `evidence_decay.py` - Temporal relevance decay
- `publication_bias.py` - Bias detection
- `sufficiency_matrix.py` - Evidence completeness

### 7. Web Dashboard

**File:** `webdashboard/app.py`

FastAPI-based web interface for job management.

**Capabilities:**
- Job creation and management
- Real-time progress via SSE
- Evidence browser
- Gap visualization
- SQLite persistence

**API Endpoints:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/jobs` | Create review job |
| GET | `/jobs/{id}` | Get job status |
| POST | `/jobs/{id}/retry` | Retry failed job |
| GET | `/jobs/{id}/stream` | SSE progress stream |
| GET | `/evidence` | Browse evidence |

---

## Data Flow

```
                                    ┌─────────────────────┐
                                    │   PDF Papers        │
                                    │   (data/raw/)       │
                                    └─────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            JOURNAL REVIEWER                                      │
│  - Extract text from PDFs                                                        │
│  - Assess relevance to research domain                                           │
│  - Extract claims with page/section markers                                      │
│  - Generate provenance metadata                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────────┐
                                    │  review_log.json    │
                                    └─────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   JUDGE                                          │
│  - Evaluate claims against pillar requirements                                   │
│  - Score evidence quality (6 dimensions)                                         │
│  - Make Accept/Reject/Flag decisions                                             │
│  - Trigger consensus review for borderline claims                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                          │                               │
                          ▼                               ▼
              ┌───────────────────────┐       ┌───────────────────────┐
              │  ACCEPTED CLAIMS      │       │  REJECTED/FLAGGED     │
              │  (Direct to sync)     │       │  (Route to Deep)      │
              └───────────────────────┘       └───────────────────────┘
                                                          │
                                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            DEEP REVIEWER                                         │
│  - Extended evidence extraction                                                  │
│  - Multi-pass analysis                                                           │
│  - Enhanced source discovery                                                     │
│  - Re-evaluation and appeal                                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────┐
                               │ review_version_history  │
                               │        .json            │
                               └─────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   SYNC                                           │
│  - Merge version history to structured database                                  │
│  - Update *_database.csv                                                         │
│  - Maintain consistency                                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            GAP ANALYZER                                          │
│  - Identify gaps by pillar                                                       │
│  - Score gap severity                                                            │
│  - Generate search recommendations                                               │
│  - Track convergence across iterations                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────┐
                               │   gap_analysis_output/  │
                               │   - gaps_report.md      │
                               │   - recommendations.json│
                               │   - convergence.json    │
                               └─────────────────────────┘
```

---

## Configuration Files

### Research Domain: `research_config.json`

Defines the research topic, keywords, and pillar definitions:

```json
{
  "domain_id": "neuromorphic-computing",
  "domain_name": "Neuromorphic Computing & Brain-Inspired AI",
  "research_topic": "neuromorphic computing and brain-inspired artificial intelligence",
  "pillar_definitions": [...],
  "search_keywords": [...]
}
```

### Pipeline Settings: `pipeline_config.json`

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
  },
  "parallel_processing": {
    "max_workers": 4,
    "enabled": true
  }
}
```

### Pillar Definitions: `pillar_definitions.json`

Defines research pillars with requirements and thresholds for evidence evaluation.

---

## Key Data Files

| File | Purpose | Format |
|------|---------|--------|
| `review_log.json` | Paper review records | JSON |
| `review_version_history.json` | Version-tracked changes | JSON |
| `*_database.csv` | Structured paper database | CSV |
| `orchestrator_state.json` | Checkpoint state | JSON |
| `gap_analysis_output/` | Generated reports | MD/JSON |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12+ |
| AI/LLM | Google Gemini API |
| Web Framework | FastAPI |
| Frontend | HTMX, Jinja2 |
| Database | SQLite (dashboard), JSON (pipeline) |
| Testing | pytest (unit/component/integration/e2e) |
| CI/CD | GitHub Actions |
| Containerization | Docker, docker-compose |

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Google AI API access |
| `DASHBOARD_API_KEY` | Dashboard authentication |
| `LITERATURE_REVIEW_OUTPUT_DIR` | Custom output path |
| `LITERATURE_REVIEW_DOMAIN` | Research domain config path |

---

## Test Infrastructure

```
tests/
├── unit/           # Isolated unit tests
├── component/      # Component tests with mocks
├── integration/    # Multi-component tests
├── e2e/            # End-to-end pipeline tests
└── fixtures/       # Test data generators
```

**Test Markers:**
- `@pytest.mark.unit` - Fast, isolated tests
- `@pytest.mark.component` - Single component tests
- `@pytest.mark.integration` - Cross-component tests
- `@pytest.mark.e2e` - Full pipeline tests
- `@pytest.mark.slow` - Long-running tests

---

## Docker Deployment

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./gap_analysis_output:/app/gap_analysis_output
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [MASTER_REPOSITORY_ROADMAP.md](MASTER_REPOSITORY_ROADMAP.md) | Completed and planned work |
| [RESEARCH_AGNOSTIC_ARCHITECTURE.md](RESEARCH_AGNOSTIC_ARCHITECTURE.md) | Multi-domain configuration |
| [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) | Web interface usage |
| [EVIDENCE_SCORING_DOCUMENTATION.md](EVIDENCE_SCORING_DOCUMENTATION.md) | Evidence quality framework |
| [INCREMENTAL_REVIEW_USER_GUIDE.md](INCREMENTAL_REVIEW_USER_GUIDE.md) | Incremental mode |

---

*This document is a current-state snapshot. For planned features and development roadmap, see [MASTER_REPOSITORY_ROADMAP.md](MASTER_REPOSITORY_ROADMAP.md).*
