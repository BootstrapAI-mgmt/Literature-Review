# Literature Review Automation System

Automated pipeline for conducting comprehensive literature reviews in neuromorphic computing research.

## Quick Start

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
  "version_history_path": "review_version_history.json",
  "stage_timeout": 7200,
  "log_level": "INFO"
}
```

## Requirements

```bash
pip install -r requirements-dev.txt
```

Create a `.env` file with your API key:
```
GEMINI_API_KEY=your_api_key_here
```

## Documentation

- **[WORKFLOW_EXECUTION_GUIDE.md](WORKFLOW_EXECUTION_GUIDE.md)**: Detailed workflow documentation
- **[ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md)**: System architecture
- **[TESTING_STATUS_SUMMARY.md](TESTING_STATUS_SUMMARY.md)**: Test coverage and status

## Pipeline Orchestrator Features

- ✅ **Automated Execution**: Runs all 5 stages sequentially
- ✅ **Conditional DRA**: Only runs when rejections are detected
- ✅ **Progress Logging**: Timestamps and status for each stage
- ✅ **Error Handling**: Halts on failure with clear error messages
- ✅ **Configurable**: Customizable timeouts and paths
- ✅ **Checkpoint/Resume**: Resume from interruptions automatically

### Resume After Failure

If the pipeline is interrupted, resume from the last checkpoint:

```bash
python pipeline_orchestrator.py --resume
```

Resume from a specific stage:

```bash
python pipeline_orchestrator.py --resume-from sync
```

Use a custom checkpoint file:

```bash
python pipeline_orchestrator.py --checkpoint-file my_checkpoint.json
```

The checkpoint file (`pipeline_checkpoint.json`) tracks pipeline progress and allows resumption after:
- Network failures or API errors
- Manual interruption (Ctrl+C)
- System crashes or restarts
- Process timeouts

Completed stages are automatically skipped when resuming, saving time and API quota.

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
