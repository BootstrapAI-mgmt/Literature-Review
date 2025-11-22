# Resume Controls - User Guide

## Overview

The Dashboard now supports resuming failed or partial jobs, matching the CLI's `--resume` and `--resume-from` capabilities. This allows you to:

- **Save time** by skipping completed stages
- **Save money** by not repeating expensive API calls
- **Recover from failures** by continuing from checkpoints
- **Re-run specific stages** without starting over

---

## Resume Methods

### 1. Resume from Stage

**Use when:** You want to skip completed stages and start from a specific point in the pipeline.

**Steps:**

1. Navigate to the job configuration page
2. Expand **Advanced Options**
3. In the **Resume Controls** card, check **Resume from Stage**
4. Select the stage to resume from:
   - Journal Reviewer (Stage 1)
   - Judge (Stage 2)
   - DRA Appeal (Stage 3)
   - Sync to Database (Stage 4)
   - Gap Analysis (Stage 5)
   - Proof Scorecard (Stage 6)
   - Sufficiency Matrix (Stage 7)
5. The stage progress diagram will highlight:
   - **Green boxes:** Completed stages (will be skipped)
   - **Yellow box:** Resume point (starts here)
   - **Gray boxes:** Pending stages (will execute)
6. Ensure your output directory contains results from previous stages
7. Start the analysis

**Example:** If you want to re-run only the visualization without re-analyzing papers, select "Sufficiency Matrix" as the resume stage.

**Requirements:**
- Output directory must contain results from previous stages
- Cannot resume from a stage if its prerequisites are missing

---

### 2. Resume from Checkpoint

**Use when:** A job failed or was interrupted, and you want to continue exactly where it left off.

**Steps:**

1. Navigate to the job configuration page
2. Expand **Advanced Options**
3. In the **Resume Controls** card, check **Resume from Checkpoint**
4. Choose how to provide the checkpoint:
   
   **Option A: Auto-detect**
   - Click **🔍 Auto-detect**
   - The system scans your output directory for checkpoint files
   - Select a checkpoint from the list
   - Review the checkpoint details (last stage, papers processed, resume point)
   
   **Option B: Upload**
   - Click **📤 Upload**
   - Select a `pipeline_checkpoint.json` file from your computer
   - Review the checkpoint details
5. Start the analysis

**Checkpoint Details Displayed:**
- **Modified:** When the checkpoint was last updated
- **Last Stage:** The last completed stage
- **Papers:** Number of papers processed
- **Will Resume From:** The stage where execution will continue

**Requirements:**
- Checkpoint file must be valid JSON
- Checkpoint must have required fields (pipeline_version, stages, status)

---

### 3. Auto-Resume Failed Jobs

**Use when:** A job failed and you want the Dashboard to automatically find and use the latest checkpoint.

**Steps:**

1. Navigate to the job detail page for a failed job
2. Click **♻️ Resume from Last Checkpoint**
3. The Dashboard:
   - Scans the output directory for checkpoints
   - Selects the most recent valid checkpoint
   - Restarts the job from that point

**This is the fastest way to recover from failures!**

---

## How Checkpoints Work

Checkpoints are automatically saved by the pipeline during execution:

- **Created:** After each stage completes successfully
- **Location:** `pipeline_checkpoint.json` in your output directory
- **Contains:**
  - Pipeline version and run ID
  - Status of each stage (completed, in_progress, not_started, failed)
  - Papers processed count
  - Timestamps for each stage

The pipeline uses checkpoints to:
- Track progress across stages
- Skip completed work when resuming
- Preserve state during interruptions

---

## Stage Progress Diagram

When you enable "Resume from Stage", the diagram shows:

```
[Journal Review] → [Judge] → [DRA] → [Sync] → [Gap Analysis] → [Proof] → [Sufficiency]
```

- **Green:** Already completed (will be skipped)
- **Yellow:** Resume point (execution starts here)
- **Gray:** Not yet executed (will run)

---

## Important Notes

### Mutual Exclusion

**Only one resume method can be used at a time:**
- If you enable "Resume from Stage", "Resume from Checkpoint" is automatically disabled
- If you enable "Resume from Checkpoint", "Resume from Stage" is automatically disabled
- If both are somehow enabled, checkpoint takes precedence

### File Requirements

**Resume from Stage requires:**
- Existing output directory
- Results from all previous stages
- Correct directory structure

**Resume from Checkpoint requires:**
- Valid checkpoint file
- Checkpoint matches your current job configuration

### Cost Savings

Resuming saves money by:
- **Skipping API calls** for completed stages
- **Reusing cached results** from previous runs
- **Not re-analyzing** papers that were already processed

Example: If a job fails at Stage 6 (Proof Scorecard), resuming from checkpoint skips:
- Stage 1: Journal Review (expensive API calls)
- Stage 2: Judge (expensive API calls)
- Stage 3: DRA (if applicable)
- Stage 4: Sync (database operations)
- Stage 5: Gap Analysis (expensive analysis)

You only re-run Stages 6 and 7, saving significant time and cost.

---

## Troubleshooting

### "No checkpoint files found"

**Cause:** The output directory doesn't contain any checkpoint files.

**Solution:**
- Verify the correct output directory is selected
- Check if the job actually ran (checkpoints are created during execution)
- Use "Resume from Stage" instead if you have partial results

### "Invalid checkpoint file format"

**Cause:** The checkpoint file is corrupted or missing required fields.

**Solution:**
- Try scanning for other checkpoints (multiple may exist)
- Check the checkpoint file manually for JSON errors
- Start a fresh run if no valid checkpoints exist

### "Directory not found"

**Cause:** The specified output directory doesn't exist.

**Solution:**
- Verify the directory path is correct
- Create the directory if using custom paths
- Use "auto" output mode to let the system manage directories

### Stage Resume Doesn't Work

**Cause:** Missing results from previous stages.

**Solution:**
- Verify all previous stages have completed successfully
- Check the output directory contains expected files
- Use "Resume from Checkpoint" for more precise resumption

---

## Best Practices

1. **Use Auto-Resume for failed jobs** - It's the fastest recovery method
2. **Keep checkpoints** - Don't delete checkpoint files until you're sure the job is complete
3. **Verify checkpoint details** - Review the checkpoint preview before resuming
4. **Match configurations** - Ensure job configuration matches the checkpoint (same papers, same settings)
5. **Monitor logs** - Check job logs to confirm resumption is working correctly

---

## CLI Equivalents

### Dashboard vs CLI

| Dashboard Feature | CLI Flag | Description |
|------------------|----------|-------------|
| Resume from Stage | `--resume-from STAGE` | Skip completed stages |
| Resume from Checkpoint | `--resume --checkpoint-file FILE` | Continue from checkpoint |
| Auto-Resume | Automatic | Find and use latest checkpoint |

### Examples

**CLI:**
```bash
# Resume from specific stage
python pipeline_orchestrator.py --resume-from orchestrator

# Resume from checkpoint file
python pipeline_orchestrator.py --resume --checkpoint-file pipeline_checkpoint.json
```

**Dashboard:**
- Use the Resume Controls in Advanced Options
- Select stage or upload/auto-detect checkpoint
- Start the job

---

## Support

For issues or questions:
- Check the job logs for detailed error messages
- Verify checkpoint files are valid JSON
- Ensure output directories have correct permissions
- Contact support if problems persist

---

**Version:** 1.0  
**Last Updated:** November 22, 2025
