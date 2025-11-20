# Literature Review Automation System

[![Integration Tests](https://github.com/BootstrapAI-mgmt/Literature-Review/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/BootstrapAI-mgmt/Literature-Review/actions/workflows/integration-tests.yml)
[![E2E Tests](https://github.com/BootstrapAI-mgmt/Literature-Review/actions/workflows/e2e-tests.yml/badge.svg)](https://github.com/BootstrapAI-mgmt/Literature-Review/actions/workflows/e2e-tests.yml)
[![codecov](https://codecov.io/gh/BootstrapAI-mgmt/Literature-Review/branch/main/graph/badge.svg)](https://codecov.io/gh/BootstrapAI-mgmt/Literature-Review)

Automated pipeline for conducting comprehensive literature reviews in neuromorphic computing research.

## Quick Start

### 🌐 Web Dashboard (NEW!)

Launch the web dashboard for a user-friendly interface:

```bash
./run_dashboard.sh
```

Then open http://localhost:8000 in your browser to:
- Upload PDFs
- Monitor job progress in real-time
- View logs and download reports
- Retry failed jobs

See [Dashboard Guide](docs/DASHBOARD_GUIDE.md) for detailed instructions.

### Automated Pipeline (Recommended)

Run the full 5-stage pipeline with a single command:

```bash
python pipeline_orchestrator.py
```

**With logging:**
```bash
python pipeline_orchestrator.py --log-file pipeline.log
```

**With custom configuration:**
```bash
python pipeline_orchestrator.py --config pipeline_config.json
```

**Resume from checkpoint:**
```bash
python pipeline_orchestrator.py --resume
```

**Resume from specific stage:**
```bash
python pipeline_orchestrator.py --resume-from judge
```

**Custom output directory:**
```bash
# Use custom output directory for gap analysis results
python pipeline_orchestrator.py --output-dir reviews/my_review

# Use environment variable
export LITERATURE_REVIEW_OUTPUT_DIR=reviews/my_review
python pipeline_orchestrator.py

# Multiple reviews in separate directories
python pipeline_orchestrator.py --output-dir reviews/baseline
python pipeline_orchestrator.py --output-dir reviews/update_jan_2025
```

**Priority:** CLI argument > Environment variable > Config file > Default (`gap_analysis_output`)

### Manual Execution

For step-by-step control, run each stage individually:

```bash
# Stage 1: Initial paper review
python Journal-Reviewer.py

# Stage 2: Judge claims
python Judge.py

# Stage 3: Deep requirements analysis (if rejections exist)
python DeepRequirementsAnalyzer.py
python Judge.py  # Re-judge DRA claims

# Stage 4: Sync to database
python sync_history_to_db.py

# Stage 5: Gap analysis and convergence
python Orchestrator.py
```

## Pipeline Stages

1. **Journal-Reviewer**: Screen papers and extract claims
2. **Judge**: Evaluate claims against requirements
3. **DeepRequirementsAnalyzer (DRA)**: Re-analyze rejected claims (conditional)
4. **Sync**: Update CSV database from version history
5. **Orchestrator**: Identify gaps, generate gap-closing search recommendations, and drive convergence

## Configuration

Create a `pipeline_config.json` file:

```json
{
  "version": "1.2.0",
  "version_history_path": "review_version_history.json",
  "output_dir": "gap_analysis_output",
  "stage_timeout": 7200,
  "log_level": "INFO",
  "retry_policy": {
    "enabled": true,
    "default_max_attempts": 3,
    "default_backoff_base": 2,
    "default_backoff_max": 60,
    "circuit_breaker_threshold": 3,
    "per_stage": {
      "journal_reviewer": {
        "max_attempts": 5,
        "backoff_base": 2,
        "backoff_max": 120,
        "retryable_patterns": ["timeout", "rate limit", "connection error"]
      }
    }
  }
}
```

**Configuration Options:**
- `output_dir`: Custom output directory for gap analysis results (default: `gap_analysis_output`)
- `version_history_path`: Path to version history JSON file
- `stage_timeout`: Maximum time (seconds) for each stage
- `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `retry_policy`: Automatic retry configuration (see below)

### Retry Configuration

The pipeline automatically retries transient failures like network timeouts and rate limits:

**Enable retry (default):**
```json
{
  "retry_policy": {
    "enabled": true,
    "default_max_attempts": 3
  }
}
```

**Disable retry:**
```json
{
  "retry_policy": {
    "enabled": false
  }
}
```

**Custom retry per stage:**
```json
{
  "retry_policy": {
    "per_stage": {
      "journal_reviewer": {
        "max_attempts": 5,
        "backoff_base": 2,
        "backoff_max": 120
      }
    }
  }
}
```

**Retryable errors:**
- Network timeouts and connection errors
- Rate limiting (429, "too many requests")
- Service unavailable (503, 502, 504)
- Temporary failures

**Non-retryable errors:**
- Syntax errors, import errors
- File not found
- Permission denied (401, 403)
- Invalid configuration

## Requirements

**Pipeline:**
```bash
pip install -r requirements-dev.txt
```

**Web Dashboard:**
```bash
pip install -r requirements-dashboard.txt
```

Create a `.env` file with your API key:
```
GEMINI_API_KEY=your_api_key_here
DASHBOARD_API_KEY=your-secure-api-key  # For dashboard authentication
```

## 📁 Repository Structure

```
Literature-Review/
├── docs/                          # 📚 All documentation
│   ├── README.md                  # Documentation guide
│   ├── DASHBOARD_GUIDE.md         # 🌐 Web dashboard guide
│   ├── CONSOLIDATED_ROADMAP.md    # ⭐ Master project roadmap
│   ├── architecture/              # System design & refactoring
│   ├── guides/                    # Workflow & strategy guides
│   ├── status-reports/            # Progress tracking
│   └── assessments/               # Technical evaluations
├── task-cards/                    # 📋 Implementation task cards
│   ├── README.md                  # Task cards guide
│   ├── agent/                     # Agent improvement tasks
│   ├── automation/                # Reliability & error handling
│   ├── integration/               # Integration test specs
│   ├── e2e/                       # End-to-end test specs
│   └── evidence-enhancement/      # Evidence quality features
├── reviews/                       # 🔍 Review documentation
│   ├── README.md                  # Reviews guide
│   ├── pull-requests/             # PR assessments
│   ├── architecture/              # Design reviews
│   └── third-party/               # External audits
├── literature_review/             # 🐍 Main package code
│   ├── analysis/                  # Judge, DRA, Recommendations
│   ├── reviewers/                 # Journal & Deep reviewers
│   ├── orchestrator.py            # Pipeline coordination
│   └── utils/                     # Shared utilities
├── webdashboard/                  # 🌐 Web dashboard
│   ├── app.py                     # FastAPI application
│   ├── templates/                 # HTML templates
│   └── static/                    # CSS, JS, images
├── tests/                         # 🧪 Test suite
│   ├── unit/                      # Unit tests
│   ├── component/                 # Component tests
│   ├── integration/               # Integration tests
│   ├── webui/                     # Dashboard tests
│   └── e2e/                       # End-to-end tests
└── scripts/                       # 🔧 Utility scripts
```

## Documentation

### 📖 Quick Links

**Getting Started:**
- **[docs/guides/WORKFLOW_EXECUTION_GUIDE.md](docs/guides/WORKFLOW_EXECUTION_GUIDE.md)** - How to run the pipeline
- **[docs/CONSOLIDATED_ROADMAP.md](docs/CONSOLIDATED_ROADMAP.md)** ⭐ - Complete project overview

**Architecture & Design:**
- **[docs/architecture/ARCHITECTURE_REFACTOR.md](docs/architecture/ARCHITECTURE_REFACTOR.md)** - Current repository structure
- **[docs/architecture/ARCHITECTURE_ANALYSIS.md](docs/architecture/ARCHITECTURE_ANALYSIS.md)** - System architecture

**Testing & Status:**
- **[docs/status-reports/TESTING_STATUS_SUMMARY.md](docs/status-reports/TESTING_STATUS_SUMMARY.md)** - Test coverage
- **[docs/TEST_MODIFICATIONS.md](docs/TEST_MODIFICATIONS.md)** - Enhanced test specifications

**Task Planning:**
- **[task-cards/README.md](task-cards/README.md)** - All implementation tasks (23 cards)
- **[task-cards/evidence-enhancement/](task-cards/evidence-enhancement/)** - Evidence quality features

See **[docs/README.md](docs/README.md)** for complete documentation index.

## Pipeline Orchestrator Features

- ✅ **Automated Execution**: Runs all 5 stages sequentially
- ✅ **Conditional DRA**: Only runs when rejections are detected
- ✅ **Progress Logging**: Timestamps and status for each stage
- ✅ **Error Handling**: Halts on failure with clear error messages
- ✅ **Configurable**: Customizable timeouts and paths
- ✅ **Checkpoint/Resume**: Resume from interruption points
- ✅ **Automatic Retry**: Retry transient failures with exponential backoff
- ✅ **Circuit Breaker**: Prevents infinite retry loops
- ✅ **Retry History**: Track all retry attempts in checkpoint file

### Checkpoint & Resume

The pipeline creates a `pipeline_checkpoint.json` file to track progress. If a pipeline fails, you can resume from the last successful stage:

```bash
# Resume from last checkpoint
python pipeline_orchestrator.py --resume

# Resume from specific stage
python pipeline_orchestrator.py --resume-from sync
```

**View checkpoint status:**
```bash
cat pipeline_checkpoint.json | jq '.stages'
```

**View retry history:**
```bash
cat pipeline_checkpoint.json | jq '.stages.journal_reviewer.retry_history'
```

### Error Recovery

The pipeline automatically retries transient failures:

1. **Network Timeout** → Retry with exponential backoff
2. **Rate Limit** → Wait and retry with increasing delays
3. **Syntax Error** → Fail immediately (no retry)
4. **Circuit Breaker** → Stop after 3 consecutive failures

**Example retry flow:**
- Attempt 1: Fails with "Connection timeout" → Wait 2s, retry
- Attempt 2: Fails with "Rate limit" → Wait 4s, retry
- Attempt 3: Succeeds → Continue to next stage

## Output Files

The pipeline generates analysis results in configurable directories:

```
gap_analysis_output/          # Research gap analysis results (default, customizable via --output-dir)
proof_scorecard_output/       # Proof scorecard outputs (CLI)
workspace/                    # Dashboard job data and results
```

**Custom Output Directory:**
You can specify a custom output directory for gap analysis results:
```bash
# Via CLI argument
python pipeline_orchestrator.py --output-dir reviews/baseline

# Via environment variable
export LITERATURE_REVIEW_OUTPUT_DIR=reviews/baseline

# Via config file
{
  "output_dir": "reviews/baseline"
}
```

This enables organizing multiple review projects:
```
reviews/
├── baseline_2025_01/         # Initial review
├── update_2025_02/           # Monthly update
└── comparative_study/        # Comparative analysis
```

**Note:** These directories are gitignored as they contain generated artifacts. Run the pipeline to regenerate outputs locally.

**Complete Output Reference:**
- **[docs/OUTPUT_FILE_REFERENCE.md](docs/OUTPUT_FILE_REFERENCE.md)** - Comprehensive list of all output files (CLI & Dashboard)
- **[docs/OUTPUT_MANAGEMENT_STRATEGY.md](docs/OUTPUT_MANAGEMENT_STRATEGY.md)** - Git policy and rationale
- **[docs/DASHBOARD_CLI_PARITY.md](docs/DASHBOARD_CLI_PARITY.md)** - Feature comparison

**Typical Output Structure:**
```
gap_analysis_output/
├── gap_analysis_report.json              # Master analysis report
├── executive_summary.md                  # Human-readable summary
├── waterfall_Pillar_1-7.html             # Pillar visualizations (7 files)
├── _OVERALL_Research_Gap_Radar.html      # Overall radar chart
├── _Paper_Network.html                   # Paper network graph
├── _Research_Trends.html                 # Trend analysis
├── proof_chain.html/json                 # Evidence proof chains
├── sufficiency_matrix.html/json          # Evidence sufficiency
├── triangulation.html/json               # Multi-source verification
└── suggested_searches.json/md            # Research recommendations
```

**Regenerate Outputs:**
```bash
# CLI
python pipeline_orchestrator.py path/to/paper.pdf

# Dashboard
# Use "Re-run Analysis" button or "Import Existing Results" feature
```

See [docs/OUTPUT_FILE_REFERENCE.md](docs/OUTPUT_FILE_REFERENCE.md) for complete file descriptions, sizes, and formats.

## Testing

Run the test suite:

```bash
pytest
```

Run specific test categories:

```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
```

## License

See [LICENSE](LICENSE) file for details.
