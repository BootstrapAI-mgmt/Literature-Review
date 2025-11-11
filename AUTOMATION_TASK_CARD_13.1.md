# Task Card #13.1 - Checkpoint/Resume Capability

**Priority:** 🟡 HIGH  
**Estimated Effort:** 4-6 hours  
**Risk Level:** LOW  
**Dependencies:** Task Card #13 (Basic Pipeline Orchestrator)  
**Wave:** Wave 2

---

## Problem Statement

The basic pipeline orchestrator (v1.0) runs all stages sequentially but lacks the ability to resume from failure points. When a pipeline fails mid-execution (due to network issues, API errors, or process interruption), users must restart from the beginning, wasting time and API quota on already-completed stages.

A checkpoint/resume system enables:
- Resuming pipelines after interruption
- Skipping already-completed stages
- Tracking pipeline progress for debugging
- Supporting long-running batch operations

---

## Acceptance Criteria

### Functional Requirements
- [ ] Pipeline writes checkpoint file after each successful stage
- [ ] `--resume` flag resumes from last successful checkpoint
- [ ] `--resume-from STAGE` flag starts from specific stage
- [ ] Checkpoint file is atomic (no partial writes that corrupt state)
- [ ] Clear error message if checkpoint file is invalid/corrupted
- [ ] Checkpoint includes timestamp, stage name, and status

### Non-Functional Requirements
- [ ] Checkpoint file is human-readable JSON
- [ ] Checkpoint write time <100ms per stage
- [ ] Backward compatible with v1.0 (no checkpoint is optional)
- [ ] Works across process restarts and system reboots
- [ ] Clear logging when resuming from checkpoint

### Security & Safety
- [ ] Checkpoint file doesn't contain sensitive data (API keys, credentials)
- [ ] Atomic writes prevent partial checkpoint corruption
- [ ] Validates checkpoint data before using it

---

## Design Contract

**Inputs:**
- Command-line flags: `--resume`, `--resume-from STAGE`, `--checkpoint-file PATH`
- Existing checkpoint file (if resuming)
- Pipeline configuration

**Outputs:**
- Checkpoint file (JSON) written after each stage
- Updated checkpoint on each successful stage completion
- Final checkpoint marked as "complete" when pipeline finishes

**Error Modes:**
- Invalid/corrupted checkpoint file → clear error, offer to restart
- Missing checkpoint file with `--resume` → error message
- Stage name mismatch → validate before resuming

**Success:**
- Pipeline resumes from correct stage
- No duplicate work performed
- Checkpoint accurately reflects pipeline state

---

## Edge Cases

1. **Checkpoint file corruption** - Partial write during crash
2. **Manual checkpoint editing** - User modifies checkpoint file
3. **Pipeline code changes** - v1.0 checkpoint used with v1.1 pipeline
4. **Concurrent runs** - Two orchestrators using same checkpoint file
5. **Checkpoint file location** - Different working directories
6. **Stage name changes** - Refactored stage names between runs

---

## Implementation Guide

### 1. Checkpoint Data Structure

**Checkpoint File:** `pipeline_checkpoint.json`

```json
{
  "run_id": "2025-11-11T14:30:00_abc123",
  "pipeline_version": "1.1.0",
  "started_at": "2025-11-11T14:30:00",
  "last_updated": "2025-11-11T14:45:30",
  "status": "in_progress",
  "stages": {
    "journal_reviewer": {
      "status": "completed",
      "started_at": "2025-11-11T14:30:05",
      "completed_at": "2025-11-11T14:35:12",
      "duration_seconds": 307,
      "exit_code": 0
    },
    "judge": {
      "status": "completed",
      "started_at": "2025-11-11T14:35:15",
      "completed_at": "2025-11-11T14:40:22",
      "duration_seconds": 307,
      "exit_code": 0
    },
    "dra": {
      "status": "skipped",
      "reason": "no_rejections"
    },
    "sync": {
      "status": "in_progress",
      "started_at": "2025-11-11T14:40:25",
      "error": "Connection timeout"
    }
  },
  "config": {
    "version_history_path": "review_version_history.json",
    "stage_timeout": 7200
  }
}
```

### 2. Code Changes to `pipeline_orchestrator.py`

**Add checkpoint methods to `PipelineOrchestrator` class:**

```python
import os
import uuid
from typing import Dict, Any, Optional

class PipelineOrchestrator:
    def __init__(self, log_file: Optional[str] = None, config: Optional[Dict[str, Any]] = None,
                 checkpoint_file: Optional[str] = None, resume: bool = False,
                 resume_from: Optional[str] = None):
        self.log_file = log_file
        self.config = config or {}
        self.start_time = datetime.now()
        self.checkpoint_file = checkpoint_file or 'pipeline_checkpoint.json'
        self.resume = resume
        self.resume_from = resume_from
        self.run_id = self._generate_run_id()
        self.checkpoint_data = self._load_or_create_checkpoint()
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}"
    
    def _load_or_create_checkpoint(self) -> Dict[str, Any]:
        """Load existing checkpoint or create new one."""
        if self.resume and os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                self.log(f"Loaded checkpoint from {self.checkpoint_file}", "INFO")
                self.log(f"Previous run: {checkpoint.get('run_id')}", "INFO")
                return checkpoint
            except Exception as e:
                self.log(f"Failed to load checkpoint: {e}", "ERROR")
                self.log("Starting fresh run", "WARNING")
        
        # Create new checkpoint
        return {
            "run_id": self.run_id,
            "pipeline_version": "1.1.0",
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "status": "in_progress",
            "stages": {},
            "config": self.config
        }
    
    def _write_checkpoint(self):
        """Atomically write checkpoint to file."""
        self.checkpoint_data["last_updated"] = datetime.now().isoformat()
        
        # Atomic write: write to temp file, then rename
        temp_file = f"{self.checkpoint_file}.tmp"
        try:
            with open(temp_file, 'w') as f:
                json.dump(self.checkpoint_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Ensure written to disk
            
            # Atomic rename
            os.replace(temp_file, self.checkpoint_file)
        except Exception as e:
            self.log(f"Failed to write checkpoint: {e}", "ERROR")
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def _should_run_stage(self, stage_name: str) -> bool:
        """Determine if stage should run based on checkpoint."""
        if not self.resume:
            return True
        
        # If resuming from specific stage, check if we've reached it
        if self.resume_from:
            stages_order = ['journal_reviewer', 'judge', 'dra', 'sync', 'orchestrator']
            try:
                resume_index = stages_order.index(self.resume_from)
                current_index = stages_order.index(stage_name)
                return current_index >= resume_index
            except ValueError:
                self.log(f"Invalid stage name: {self.resume_from}", "ERROR")
                return True
        
        # Check checkpoint status
        stage_data = self.checkpoint_data.get("stages", {}).get(stage_name, {})
        status = stage_data.get("status")
        
        if status == "completed":
            self.log(f"Skipping {stage_name} (already completed)", "INFO")
            return False
        elif status == "in_progress":
            self.log(f"Re-running {stage_name} (was interrupted)", "INFO")
            return True
        else:
            return True
    
    def _mark_stage_started(self, stage_name: str):
        """Mark stage as started in checkpoint."""
        if stage_name not in self.checkpoint_data["stages"]:
            self.checkpoint_data["stages"][stage_name] = {}
        
        self.checkpoint_data["stages"][stage_name].update({
            "status": "in_progress",
            "started_at": datetime.now().isoformat()
        })
        self._write_checkpoint()
    
    def _mark_stage_completed(self, stage_name: str, duration: float, exit_code: int):
        """Mark stage as completed in checkpoint."""
        self.checkpoint_data["stages"][stage_name].update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "duration_seconds": int(duration),
            "exit_code": exit_code
        })
        self._write_checkpoint()
    
    def _mark_stage_failed(self, stage_name: str, error: str):
        """Mark stage as failed in checkpoint."""
        self.checkpoint_data["stages"][stage_name].update({
            "status": "failed",
            "failed_at": datetime.now().isoformat(),
            "error": error
        })
        self._write_checkpoint()
    
    def _mark_stage_skipped(self, stage_name: str, reason: str):
        """Mark stage as skipped in checkpoint."""
        self.checkpoint_data["stages"][stage_name] = {
            "status": "skipped",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        self._write_checkpoint()
```

### 3. Update `run_stage()` Method

```python
def run_stage(self, stage_name: str, script: str, description: str, 
              required: bool = True) -> bool:
    """
    Run a pipeline stage with checkpoint support.
    
    Args:
        stage_name: Unique stage identifier (e.g., 'journal_reviewer')
        script: Python script to run
        description: Human-readable stage description
        required: If True, exit on failure; if False, continue
    
    Returns:
        True if successful, False otherwise
    """
    # Check if stage should run based on checkpoint
    if not self._should_run_stage(stage_name):
        return True  # Already completed
    
    self.log(f"Starting stage: {description}", "INFO")
    self._mark_stage_started(stage_name)
    
    stage_start = datetime.now()
    
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=self.config.get('stage_timeout', 3600)
        )
        
        duration = (datetime.now() - stage_start).total_seconds()
        
        if result.returncode == 0:
            self.log(f"✅ Stage complete: {description}", "SUCCESS")
            self._mark_stage_completed(stage_name, duration, result.returncode)
            return True
        else:
            self.log(f"❌ Stage failed: {description}", "ERROR")
            self.log(f"Error output:\n{result.stderr}", "ERROR")
            self._mark_stage_failed(stage_name, result.stderr[:500])  # Truncate error
            
            if required:
                self.log("Pipeline halted due to required stage failure", "ERROR")
                sys.exit(1)
            return False
            
    except subprocess.TimeoutExpired:
        self.log(f"⏱️ Stage timeout: {description}", "ERROR")
        self._mark_stage_failed(stage_name, "Timeout exceeded")
        if required:
            sys.exit(1)
        return False
    except Exception as e:
        self.log(f"💥 Stage exception: {description} - {e}", "ERROR")
        self._mark_stage_failed(stage_name, str(e))
        if required:
            sys.exit(1)
        return False
```

### 4. Update `run()` Method

```python
def run(self):
    """Execute the full pipeline with checkpoint support."""
    self.log("="*70, "INFO")
    self.log("Literature Review Pipeline Orchestrator v1.1", "INFO")
    if self.resume:
        self.log(f"RESUMING from checkpoint: {self.checkpoint_file}", "INFO")
    self.log("="*70, "INFO")
    
    # Stage 1: Journal Reviewer
    self.run_stage('journal_reviewer', 'Journal-Reviewer.py', 'Stage 1: Initial Paper Review')
    
    # Stage 2: Judge
    self.run_stage('judge', 'Judge.py', 'Stage 2: Judge Claims')
    
    # Stage 3: DRA (conditional)
    if self._should_run_stage('dra'):
        if self.check_for_rejections():
            self.log("Rejections detected, running DRA appeal process", "INFO")
            self.run_stage('dra', 'DeepRequirementsAnalyzer.py', 'Stage 3: DRA Appeal')
            self.run_stage('judge_dra', 'Judge.py', 'Stage 3b: Re-judge DRA Claims')
        else:
            self.log("No rejections found, skipping DRA", "INFO")
            self._mark_stage_skipped('dra', 'no_rejections')
    
    # Stage 4: Sync to Database
    self.run_stage('sync', 'sync_history_to_db.py', 'Stage 4: Sync to Database')
    
    # Stage 5: Orchestrator
    self.run_stage('orchestrator', 'Orchestrator.py', 'Stage 5: Gap Analysis & Convergence')
    
    # Mark pipeline complete
    self.checkpoint_data["status"] = "completed"
    self.checkpoint_data["completed_at"] = datetime.now().isoformat()
    self._write_checkpoint()
    
    # Summary
    elapsed = datetime.now() - self.start_time
    self.log("="*70, "INFO")
    self.log(f"🎉 Pipeline Complete!", "SUCCESS")
    self.log(f"Total time: {elapsed}", "INFO")
    self.log("="*70, "INFO")
```

### 5. Update `main()` Function

```python
def main():
    parser = argparse.ArgumentParser(
        description='Run the full Literature Review pipeline automatically'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help='Path to log file (default: no file logging)'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration JSON file'
    )
    parser.add_argument(
        '--checkpoint-file',
        type=str,
        default='pipeline_checkpoint.json',
        help='Path to checkpoint file (default: pipeline_checkpoint.json)'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint'
    )
    parser.add_argument(
        '--resume-from',
        type=str,
        choices=['journal_reviewer', 'judge', 'dra', 'sync', 'orchestrator'],
        help='Resume from specific stage'
    )
    
    args = parser.parse_args()
    
    # Load config if provided
    config = {}
    if args.config and Path(args.config).exists():
        with open(args.config) as f:
            config = json.load(f)
    
    # Run pipeline
    orchestrator = PipelineOrchestrator(
        log_file=args.log_file,
        config=config,
        checkpoint_file=args.checkpoint_file,
        resume=args.resume,
        resume_from=args.resume_from
    )
    orchestrator.run()

if __name__ == '__main__':
    main()
```

---

## Usage Examples

### Normal Run (Creates Checkpoint)
```bash
python pipeline_orchestrator.py
# Creates: pipeline_checkpoint.json
```

### Resume After Failure
```bash
# Pipeline failed at sync stage
python pipeline_orchestrator.py --resume
# Skips: journal_reviewer (✅ completed)
# Skips: judge (✅ completed)
# Re-runs: sync (⏸️ was in_progress)
```

### Resume From Specific Stage
```bash
# Re-run from sync onwards
python pipeline_orchestrator.py --resume-from sync
# Skips: journal_reviewer, judge
# Runs: sync, orchestrator
```

### Custom Checkpoint File
```bash
python pipeline_orchestrator.py --checkpoint-file batch_001_checkpoint.json
```

---

## Testing Strategy

### Unit Tests

Create `tests/automation/test_checkpoint.py`:

```python
import pytest
import json
import tempfile
import os
from pipeline_orchestrator import PipelineOrchestrator

class TestCheckpoint:
    
    def test_checkpoint_creation(self, temp_dir):
        """Test that checkpoint file is created."""
        checkpoint_path = os.path.join(temp_dir, 'test_checkpoint.json')
        orch = PipelineOrchestrator(checkpoint_file=checkpoint_path)
        
        # Should create checkpoint structure
        assert orch.checkpoint_data is not None
        assert 'run_id' in orch.checkpoint_data
        assert 'stages' in orch.checkpoint_data
    
    def test_atomic_write(self, temp_dir):
        """Test that checkpoint writes are atomic."""
        checkpoint_path = os.path.join(temp_dir, 'test_checkpoint.json')
        orch = PipelineOrchestrator(checkpoint_file=checkpoint_path)
        
        orch._mark_stage_started('test_stage')
        
        # Checkpoint file should exist
        assert os.path.exists(checkpoint_path)
        
        # Temp file should not exist (cleaned up)
        assert not os.path.exists(checkpoint_path + '.tmp')
        
        # Should be valid JSON
        with open(checkpoint_path) as f:
            data = json.load(f)
            assert 'test_stage' in data['stages']
    
    def test_resume_skips_completed(self, temp_dir):
        """Test that resume skips completed stages."""
        checkpoint_path = os.path.join(temp_dir, 'test_checkpoint.json')
        
        # Create checkpoint with completed stage
        checkpoint_data = {
            "run_id": "test_run",
            "stages": {
                "stage1": {"status": "completed"},
                "stage2": {"status": "in_progress"}
            }
        }
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f)
        
        orch = PipelineOrchestrator(
            checkpoint_file=checkpoint_path,
            resume=True
        )
        
        # Should skip completed stage
        assert not orch._should_run_stage('stage1')
        
        # Should re-run in-progress stage
        assert orch._should_run_stage('stage2')
```

### Integration Tests

Add to `tests/integration/test_orchestrator.py`:

```python
@pytest.mark.integration
def test_checkpoint_resume_after_failure(integration_temp_workspace, test_data_generator):
    """Test that pipeline can resume after failure."""
    workspace = integration_temp_workspace
    checkpoint_path = os.path.join(workspace['root'], 'checkpoint.json')
    
    # TODO: Mock pipeline failure at sync stage
    # Run pipeline, simulate failure
    # Re-run with --resume
    # Verify only remaining stages execute
```

### Manual Testing

```bash
# Test 1: Normal checkpoint creation
python pipeline_orchestrator.py --log-file test.log
ls -la pipeline_checkpoint.json
cat pipeline_checkpoint.json  # Verify structure

# Test 2: Interrupt and resume
python pipeline_orchestrator.py &
# Wait for 2 stages to complete
kill %1  # Interrupt
python pipeline_orchestrator.py --resume  # Should resume

# Test 3: Resume from specific stage
python pipeline_orchestrator.py --resume-from sync

# Test 4: Invalid checkpoint handling
echo "invalid json" > pipeline_checkpoint.json
python pipeline_orchestrator.py --resume  # Should error gracefully
```

---

## Success Criteria

### Functional
- [ ] Checkpoint file created after first stage completes
- [ ] `--resume` successfully skips completed stages
- [ ] `--resume-from STAGE` starts from correct point
- [ ] Pipeline completes successfully after resume
- [ ] Checkpoint shows correct stage statuses

### Performance
- [ ] Checkpoint write time <100ms per stage
- [ ] No noticeable performance impact on pipeline
- [ ] Checkpoint file size <10KB for typical run

### Reliability
- [ ] Atomic writes prevent corruption (tested with kill -9)
- [ ] Invalid checkpoint detected and handled gracefully
- [ ] Works across system restarts
- [ ] No data loss on interrupt

### Usability
- [ ] Clear log messages when resuming
- [ ] Checkpoint file is human-readable
- [ ] Error messages guide user to fix issues
- [ ] Documentation updated with examples

---

## Documentation Updates

### Update `README.md`

```markdown
### Resume After Failure

If the pipeline is interrupted, resume from the last checkpoint:

\`\`\`bash
python pipeline_orchestrator.py --resume
\`\`\`

Resume from a specific stage:

\`\`\`bash
python pipeline_orchestrator.py --resume-from sync
\`\`\`

Use a custom checkpoint file:

\`\`\`bash
python pipeline_orchestrator.py --checkpoint-file my_checkpoint.json
\`\`\`
```

### Update `WORKFLOW_EXECUTION_GUIDE.md`

Add section on checkpoint/resume functionality with examples.

---

## Rollout Plan

1. **Development:** Implement checkpoint functionality (4-6 hours)
2. **Testing:** Unit + integration tests (2 hours)
3. **Documentation:** Update README and guide (1 hour)
4. **Code Review:** Submit PR for review
5. **Merge:** Merge to main after approval
6. **Validation:** Test on production-like data

---

## Estimated Lines of Code

- New methods: ~150 lines
- Modified methods: ~50 lines
- Tests: ~100 lines
- Documentation: ~50 lines
- **Total: ~350 lines**

---

## Notes

- Checkpoint file is intentionally human-readable (JSON) for debugging
- Atomic writes using temp file + rename pattern prevent corruption
- Stage names are stable identifiers (don't use display names)
- Checkpoint includes config for auditing/debugging
- Consider adding `--clean` flag to remove checkpoint and start fresh
- Future enhancement: Support multiple concurrent runs with unique checkpoint files

---

**Task Card Status:** ✅ Ready for Implementation  
**Next Step:** Begin implementation after Task Card #13 (PR #6) is merged  
**Integration Point:** Works with Task Card #13.2 (retry logic)
