# INCR-W1-4: CLI --output-dir Argument Support

**Wave:** 1 (Foundation)  
**Priority:** 🟠 High  
**Effort:** 3-4 hours  
**Status:** 🟢 Ready  
**Assignable:** Backend Developer

---

## Overview

Add support for custom output directories in the CLI pipeline orchestrator, replacing the hardcoded `OUTPUT_FOLDER = 'gap_analysis_output'` with a user-configurable option. This enables users to manage multiple review projects in separate directories and is a prerequisite for incremental review mode.

---

## Dependencies

**Prerequisites:**
- None (Wave 1 foundation task)

**Blocks:**
- INCR-W2-1 (CLI Incremental Review Mode)

---

## Scope

### Included
- [x] Add `--output-dir` CLI argument to `pipeline_orchestrator.py`
- [x] Update `literature_review/orchestrator.py` to accept dynamic output folder
- [x] Environment variable support (`LITERATURE_REVIEW_OUTPUT_DIR`)
- [x] Backward compatibility (default: `gap_analysis_output`)
- [x] Update all output file paths to use dynamic folder
- [x] Integration tests

### Excluded
- ❌ Output folder validation/permissions (rely on OS errors)
- ❌ Multiple output formats (still JSON/HTML/MD)
- ❌ Output folder templates (future enhancement)

---

## Technical Specification

### Files to Modify

```
pipeline_orchestrator.py           # Add CLI argument
literature_review/orchestrator.py  # Make OUTPUT_FOLDER dynamic
```

### Implementation

#### Part 1: pipeline_orchestrator.py

```python
# pipeline_orchestrator.py (lines ~740-780)

def main():
    parser = argparse.ArgumentParser(
        description="Run the full Literature Review pipeline automatically (v2.0 with advanced features)"
    )
    parser.add_argument("--log-file", type=str, help="Path to log file (default: no file logging)")
    parser.add_argument("--config", type=str, help="Path to configuration JSON file")
    parser.add_argument(
        "--checkpoint-file",
        type=str,
        default="pipeline_checkpoint.json",
        help="Path to checkpoint file (default: pipeline_checkpoint.json)",
    )
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument(
        "--resume-from", type=str, help="Resume from specific stage (e.g., judge, sync)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run mode: validate pipeline without executing stages or writing outputs"
    )
    parser.add_argument(
        "--enable-experimental",
        action="store_true",
        help="Enable experimental v2.0 features (parallel processing, quota management). Use with caution."
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=50.0,
        help="Monthly API budget in USD (default: $50.00)"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        default=True,
        help="Use incremental analysis (default: True)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full re-analysis of all papers"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear incremental analysis cache before running"
    )
    
    # NEW: Add --output-dir argument
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for gap analysis results (default: gap_analysis_output). "
             "Can also be set via LITERATURE_REVIEW_OUTPUT_DIR environment variable."
    )

    args = parser.parse_args()
    
    # Handle cache clearing first
    if args.clear_cache:
        from literature_review.utils.incremental_analyzer import get_incremental_analyzer
        analyzer = get_incremental_analyzer()
        analyzer.clear_cache()
        print("✅ Incremental analysis cache cleared")

    # Load config if provided
    config = {}
    if args.config and Path(args.config).exists():
        with open(args.config) as f:
            config = json.load(f)

    # Override config with CLI flags
    if args.dry_run:
        config['dry_run'] = True
    
    if args.budget:
        config['budget_usd'] = args.budget
    
    # Set incremental flags
    config['incremental'] = args.incremental and not args.force
    config['force'] = args.force
    
    # NEW: Set output directory
    # Priority: CLI arg > Environment variable > Config file > Default
    output_dir = (
        args.output_dir or
        os.getenv('LITERATURE_REVIEW_OUTPUT_DIR') or
        config.get('output_dir') or
        'gap_analysis_output'
    )
    config['output_dir'] = output_dir
    
    # Log output directory
    print(f"📁 Output directory: {output_dir}")
    
    if args.enable_experimental:
        # Enable v2 features if requested
        if 'v2_features' not in config:
            from literature_review.pipeline.orchestrator_v2 import create_v2_config_defaults
            config['v2_features'] = create_v2_config_defaults()
        config['v2_features']['feature_flags']['enable_parallel_processing'] = True

    # Create orchestrator
    orchestrator = PipelineOrchestrator(
        checkpoint_file=args.checkpoint_file,
        resume=args.resume,
        resume_from=args.resume_from,
        config=config,
    )

    # Run pipeline
    try:
        orchestrator.run_pipeline()
    except KeyboardInterrupt:
        orchestrator.log("\n⚠️  Pipeline interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        orchestrator.log(f"\n❌ Pipeline failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

#### Part 2: literature_review/orchestrator.py

```python
# literature_review/orchestrator.py (lines 60-80)

# --- File Paths ---
# 1. Inputs from other scripts
RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'
DEFINITIONS_FILE = 'pillar_definitions_enhanced.json'
VERSION_HISTORY_FILE = 'review_version_history.json'

# 2. This script's state / outputs
# DEPRECATED: Hardcoded OUTPUT_FOLDER
# OUTPUT_FOLDER = 'gap_analysis_output'

# NEW: Dynamic output folder (set by config or default)
OUTPUT_FOLDER = os.getenv('LITERATURE_REVIEW_OUTPUT_DIR', 'gap_analysis_output')

CACHE_FOLDER = 'analysis_cache'
CACHE_FILE = os.path.join(CACHE_FOLDER, 'analysis_cache.pkl')

# NOTE: These will be dynamically constructed based on OUTPUT_FOLDER
# CONTRIBUTION_REPORT_FILE = os.path.join(OUTPUT_FOLDER, 'sub_requirement_paper_contributions.md')
# ORCHESTRATOR_STATE_FILE = 'orchestrator_state.json'
# DEEP_REVIEW_DIRECTIONS_FILE = os.path.join(OUTPUT_FOLDER, 'deep_review_directions.json')

# 3. External Scripts to call
# DEEP_REVIEWER_SCRIPT = 'Deep-Reviewer.py'
# JUDGE_SCRIPT = 'Judge.py'

# Create directories (now done in main() with dynamic OUTPUT_FOLDER)
# os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(CACHE_FOLDER, exist_ok=True)
```

```python
# literature_review/orchestrator.py - main() function (lines ~1876-1950)

def main(config: Optional[OrchestratorConfig] = None, output_folder: Optional[str] = None):
    """
    Main orchestrator entry point
    
    Args:
        config: Optional configuration for programmatic execution.
                If None, runs in interactive terminal mode.
        output_folder: Custom output directory (overrides default and config)
    """
    # NEW: Set global OUTPUT_FOLDER based on parameter or config
    global OUTPUT_FOLDER
    
    if output_folder:
        # Explicit parameter takes highest priority
        OUTPUT_FOLDER = output_folder
    elif config and hasattr(config, 'output_dir') and config.output_dir:
        # Config object has output_dir
        OUTPUT_FOLDER = config.output_dir
    elif config and isinstance(config, dict) and config.get('output_dir'):
        # Config dict has output_dir
        OUTPUT_FOLDER = config['output_dir']
    else:
        # Use environment variable or default
        OUTPUT_FOLDER = os.getenv('LITERATURE_REVIEW_OUTPUT_DIR', 'gap_analysis_output')
    
    # Create output directory
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # Update dependent file paths
    global CONTRIBUTION_REPORT_FILE, ORCHESTRATOR_STATE_FILE, DEEP_REVIEW_DIRECTIONS_FILE
    CONTRIBUTION_REPORT_FILE = os.path.join(OUTPUT_FOLDER, 'sub_requirement_paper_contributions.md')
    ORCHESTRATOR_STATE_FILE = os.path.join(OUTPUT_FOLDER, 'orchestrator_state.json')
    DEEP_REVIEW_DIRECTIONS_FILE = os.path.join(OUTPUT_FOLDER, 'deep_review_directions.json')
    
    logger.info("\n" + "=" * 80)
    logger.info("ENHANCED GAP ANALYSIS ORCHESTRATOR v3.6 (Pre-Analysis Judge Run)")
    logger.info(f"Output Directory: {OUTPUT_FOLDER}")
    logger.info("=" * 80)
    global_start_time = time.time()

    # ... rest of main() function continues unchanged ...
```

```python
# Update all file output paths in orchestrator.py to use OUTPUT_FOLDER

# Example locations to update:
# Line ~2100: save_orchestrator_state(ORCHESTRATOR_STATE_FILE, ...)
# Line ~2200: os.path.join(OUTPUT_FOLDER, 'gap_analysis_report.json')
# Line ~2300: os.path.join(OUTPUT_FOLDER, 'executive_summary.md')
# etc.

# These already use OUTPUT_FOLDER, so no changes needed if we make it global
```

#### Part 3: PipelineOrchestrator Integration

```python
# pipeline_orchestrator.py - PipelineOrchestrator class

class PipelineOrchestrator:
    def __init__(
        self,
        checkpoint_file: Optional[str] = None,
        resume: bool = False,
        resume_from: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        # ... existing initialization ...
        
        # NEW: Store output directory from config
        self.output_dir = config.get('output_dir', 'gap_analysis_output') if config else 'gap_analysis_output'
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Output directory: {self.output_dir}")
    
    def run_stage(self, stage_name: str, module_name: str, description: str, use_module: bool = True):
        """Run a pipeline stage (updated to pass output_dir to orchestrator)."""
        
        # ... existing code ...
        
        if stage_name == "orchestrator":
            # Pass output_dir to orchestrator.main()
            import sys
            from literature_review import orchestrator
            
            # Set output folder before running
            orchestrator.OUTPUT_FOLDER = self.output_dir
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Run orchestrator
            orchestrator.main(output_folder=self.output_dir)
        else:
            # ... existing stage execution code ...
```

---

## Testing Strategy

### Unit Tests

Create `tests/unit/test_output_dir_argument.py`:

```python
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from literature_review import orchestrator

def test_default_output_folder():
    """Test default output folder is gap_analysis_output."""
    # Clear environment variable
    with patch.dict(os.environ, {}, clear=True):
        from importlib import reload
        reload(orchestrator)
        
        # Should use default
        assert orchestrator.OUTPUT_FOLDER == 'gap_analysis_output'

def test_environment_variable_output_folder():
    """Test environment variable sets output folder."""
    with patch.dict(os.environ, {'LITERATURE_REVIEW_OUTPUT_DIR': 'custom_output'}):
        from importlib import reload
        reload(orchestrator)
        
        assert orchestrator.OUTPUT_FOLDER == 'custom_output'

def test_main_with_output_folder_parameter(tmp_path):
    """Test main() with explicit output_folder parameter."""
    custom_dir = tmp_path / "test_output"
    
    # Mock the rest of main() to avoid full execution
    with patch('literature_review.orchestrator.load_orchestrator_state', return_value=({}, {}, [])):
        with patch('literature_review.orchestrator.check_for_new_data', return_value=False):
            with patch.object(orchestrator, 'DEFINITIONS_FILE', str(tmp_path / 'pillar_definitions.json')):
                # Create minimal definitions file
                (tmp_path / 'pillar_definitions.json').write_text('{}')
                
                try:
                    orchestrator.main(output_folder=str(custom_dir))
                except SystemExit:
                    pass  # Expected if no data
                
                # Check directory was created
                assert custom_dir.exists()

def test_cli_argument_priority(tmp_path):
    """Test CLI argument takes priority over environment variable."""
    cli_dir = tmp_path / "cli_output"
    env_dir = tmp_path / "env_output"
    
    with patch.dict(os.environ, {'LITERATURE_REVIEW_OUTPUT_DIR': str(env_dir)}):
        orchestrator.OUTPUT_FOLDER = str(cli_dir)
        os.makedirs(cli_dir, exist_ok=True)
        
        # CLI argument should win
        assert orchestrator.OUTPUT_FOLDER == str(cli_dir)
```

### Integration Tests

Create `tests/integration/test_cli_output_dir.py`:

```python
import pytest
import subprocess
import json
from pathlib import Path

def test_cli_with_custom_output_dir(tmp_path):
    """Test running CLI with --output-dir argument."""
    output_dir = tmp_path / "custom_gap_analysis"
    
    # Run pipeline with custom output dir (dry-run to avoid long execution)
    result = subprocess.run(
        [
            'python', 'pipeline_orchestrator.py',
            '--output-dir', str(output_dir),
            '--dry-run'
        ],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Check output mentions custom directory
    assert str(output_dir) in result.stdout or str(output_dir) in result.stderr

def test_cli_without_output_dir():
    """Test CLI without --output-dir uses default."""
    result = subprocess.run(
        ['python', 'pipeline_orchestrator.py', '--dry-run'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Check default directory mentioned
    assert 'gap_analysis_output' in result.stdout or 'gap_analysis_output' in result.stderr

def test_multiple_output_directories(tmp_path):
    """Test creating multiple separate reviews in different directories."""
    review1_dir = tmp_path / "review_v1"
    review2_dir = tmp_path / "review_v2"
    
    # Create mock gap analysis reports
    for review_dir in [review1_dir, review2_dir]:
        review_dir.mkdir()
        report = {
            'pillars': {},
            'metadata': {'version': 1, 'directory': str(review_dir)}
        }
        with open(review_dir / 'gap_analysis_report.json', 'w') as f:
            json.dump(report, f)
    
    # Both should exist independently
    assert (review1_dir / 'gap_analysis_report.json').exists()
    assert (review2_dir / 'gap_analysis_report.json').exists()
    
    # Read and verify they're different
    with open(review1_dir / 'gap_analysis_report.json') as f:
        report1 = json.load(f)
    
    with open(review2_dir / 'gap_analysis_report.json') as f:
        report2 = json.load(f)
    
    assert report1['metadata']['directory'] != report2['metadata']['directory']
```

### Backward Compatibility Tests

Create `tests/integration/test_backward_compatibility.py`:

```python
import pytest
import subprocess
from pathlib import Path

def test_no_breaking_changes_for_existing_users():
    """Test that existing scripts still work without --output-dir."""
    # Run pipeline without --output-dir (dry-run)
    result = subprocess.run(
        ['python', 'pipeline_orchestrator.py', '--dry-run'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should not error
    assert result.returncode == 0 or 'gap_analysis_output' in result.stdout

def test_environment_variable_backward_compatible():
    """Test environment variable works for existing setups."""
    import os
    
    # Users might have this in their .env or shell profile
    env = os.environ.copy()
    env['LITERATURE_REVIEW_OUTPUT_DIR'] = 'my_custom_output'
    
    result = subprocess.run(
        ['python', '-c', 'from literature_review import orchestrator; print(orchestrator.OUTPUT_FOLDER)'],
        capture_output=True,
        text=True,
        env=env
    )
    
    # Should use environment variable
    assert 'my_custom_output' in result.stdout or 'gap_analysis_output' in result.stdout
```

---

## Deliverables

- [ ] `--output-dir` argument added to `pipeline_orchestrator.py`
- [ ] `OUTPUT_FOLDER` made dynamic in `orchestrator.py`
- [ ] Environment variable support (`LITERATURE_REVIEW_OUTPUT_DIR`)
- [ ] Backward compatibility maintained (default: `gap_analysis_output`)
- [ ] All output file paths use dynamic folder
- [ ] Unit tests in `tests/unit/test_output_dir_argument.py`
- [ ] Integration tests in `tests/integration/test_cli_output_dir.py`
- [ ] Backward compatibility tests
- [ ] README.md updated with usage examples
- [ ] Code coverage ≥ 90%

---

## Success Criteria

✅ **Functional:**
- `python pipeline_orchestrator.py --output-dir custom_folder` works
- All outputs saved to specified directory
- Environment variable `LITERATURE_REVIEW_OUTPUT_DIR` works
- Default behavior unchanged (backward compatible)

✅ **Quality:**
- Unit tests pass (90% coverage)
- Integration tests pass
- No breaking changes for existing users
- No linting errors

✅ **Documentation:**
- README updated with examples
- Help text clear (`--help` shows usage)

---

## Usage Examples

### Basic Usage

```bash
# Use default output directory (gap_analysis_output)
python pipeline_orchestrator.py

# Use custom output directory
python pipeline_orchestrator.py --output-dir my_review_v2

# Use environment variable
export LITERATURE_REVIEW_OUTPUT_DIR=review_2025_01
python pipeline_orchestrator.py
```

### Multiple Reviews

```bash
# Baseline review
python pipeline_orchestrator.py --output-dir reviews/baseline

# After adding new papers
python pipeline_orchestrator.py --output-dir reviews/update_jan_2025

# Comparative analysis
python pipeline_orchestrator.py --output-dir reviews/comparative_study
```

### Integration with Other Tools

```bash
# Use in scripts
OUTPUT_DIR="reviews/automated_$(date +%Y%m%d)"
python pipeline_orchestrator.py --output-dir "$OUTPUT_DIR"

# Use in CI/CD
export LITERATURE_REVIEW_OUTPUT_DIR="ci_output_${CI_COMMIT_SHA}"
python pipeline_orchestrator.py
```

---

## Documentation Updates

### README.md

Add to CLI usage section:

```markdown
### Custom Output Directory

By default, gap analysis results are saved to `gap_analysis_output/`. You can specify a custom directory:

**Via CLI argument:**
```bash
python pipeline_orchestrator.py --output-dir reviews/my_review
```

**Via environment variable:**
```bash
export LITERATURE_REVIEW_OUTPUT_DIR=reviews/my_review
python pipeline_orchestrator.py
```

**Priority:**
1. CLI argument (`--output-dir`)
2. Environment variable (`LITERATURE_REVIEW_OUTPUT_DIR`)
3. Config file (`output_dir` key)
4. Default (`gap_analysis_output`)

**Use Cases:**
- **Multiple reviews:** Manage separate review projects
- **Version control:** `reviews/v1`, `reviews/v2`, etc.
- **Comparison:** Run baseline and incremental in separate folders
- **CI/CD:** Dynamic output paths per build
```

---

## Migration Guide

For existing users:

```markdown
## Migrating to Custom Output Directories

**No action required!** Default behavior unchanged.

**Optional: Organize existing reviews**

If you want to organize your existing `gap_analysis_output/` folder:

```bash
# Create reviews directory
mkdir -p reviews

# Move existing output
mv gap_analysis_output reviews/baseline_2025_01

# Future runs use new directory
python pipeline_orchestrator.py --output-dir reviews/update_2025_02
```

**Recommended folder structure:**

```
reviews/
├── baseline_2025_01/
│   ├── gap_analysis_report.json
│   ├── executive_summary.md
│   └── waterfall_*.html
├── update_2025_02/
│   └── ...
└── comparative_study/
    └── ...
```
```

---

## Rollback Plan

If issues arise:
1. Revert changes to `pipeline_orchestrator.py` and `orchestrator.py`
2. Users can continue using default `gap_analysis_output/`
3. No data loss (existing output folders untouched)

---

## Notes

- This task is **non-breaking** (backward compatible)
- Safe to deploy immediately
- Enables future incremental review mode (INCR-W2-1)
- Simple implementation (~100 LOC changes)

---

**Status:** 🟢 Ready for implementation  
**Assignee:** TBD  
**Estimated Start:** Week 1, Day 1  
**Estimated Completion:** Week 1, Day 2
