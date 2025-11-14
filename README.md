# Literature Review Automation System

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
5. **Orchestrator**: Identify gaps and drive convergence

## Configuration

Create a `pipeline_config.json` file:

```json
{
  "version": "1.2.0",
  "version_history_path": "review_version_history.json",
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
