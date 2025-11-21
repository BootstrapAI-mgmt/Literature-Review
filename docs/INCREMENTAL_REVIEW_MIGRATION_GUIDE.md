# Migration Guide: Incremental Review Mode

## For Existing Users

Incremental mode is **fully backward compatible**. No changes required to existing workflows.

---

## Overview

The incremental review mode was introduced in Wave 2 of the Literature Review Automation System to enable efficient updates to existing reviews. This guide helps existing users adopt incremental mode while maintaining their current workflows.

**Key Points:**
- ✅ Fully backward compatible - all existing commands work as before
- ✅ Opt-in feature - use `--incremental` flag to enable
- ✅ Automatic fallback - if prerequisites missing, runs full mode
- ✅ No breaking changes - state files auto-migrate
- ✅ Preserves data - no risk of data loss during migration

---

## Quick Migration Path

### Step 1: Update Dependencies

Ensure you have the latest version installed:

```bash
git pull origin main
pip install -r requirements.txt
```

### Step 2: Run Baseline Analysis

Create a baseline review with the current version:

```bash
python pipeline_orchestrator.py --output-dir reviews/baseline
```

This creates the necessary state files for incremental mode.

### Step 3: Try Incremental Mode

Add new papers to your database and run:

```bash
python pipeline_orchestrator.py --incremental --output-dir reviews/baseline
```

That's it! The system will automatically:
1. Detect previous analysis
2. Extract gaps from baseline
3. Score new papers for relevance
4. Analyze only relevant papers
5. Merge results into existing report

---

## Opt-In Migration

You can continue using the system exactly as before. Incremental mode is opt-in via the `--incremental` flag.

### Before (still works)

```bash
# Traditional workflow - still fully supported
python pipeline_orchestrator.py
python pipeline_orchestrator.py --output-dir reviews/my_review
```

### After (optional)

```bash
# Enable incremental mode for faster updates
python pipeline_orchestrator.py --incremental
python pipeline_orchestrator.py --incremental --output-dir reviews/my_review
```

---

## Recommended Migration Steps

### 1. Create Baseline Review

Start with one full analysis to establish a baseline:

```bash
# First time - full analysis
python pipeline_orchestrator.py --output-dir reviews/baseline_2025_01
```

This creates:
- `gap_analysis_report.json` - Complete gap analysis
- `orchestrator_state.json` - Pipeline state with job metadata

### 2. Add New Papers

Add new papers to your data source:
- CLI: Add to `data/raw/` directory or update CSV database
- Dashboard: Upload new PDFs via the upload page

### 3. Run Incremental Update

```bash
# Subsequent runs - incremental mode
python pipeline_orchestrator.py --incremental --output-dir reviews/baseline_2025_01
```

### 4. Monitor Performance

Check the logs to see performance improvements:
- Papers analyzed: Should be 40-60% of total new papers (with default 50% threshold)
- Time saved: Typically 60-80% faster
- Cost saved: $15-30 per incremental run

### 5. Adjust Threshold (Optional)

If too many or too few papers are being filtered:

```bash
# More aggressive filtering (analyze fewer papers)
python pipeline_orchestrator.py --incremental --relevance-threshold 0.70

# Less aggressive filtering (analyze more papers)
python pipeline_orchestrator.py --incremental --relevance-threshold 0.30
```

---

## State File Migration

The system automatically migrates old state files to the new format.

### Old Format (v1)

```json
{
  "timestamp": "2025-01-15T10:00:00",
  "database_hash": "abc123",
  "analysis_completed": true,
  "file_states": {
    "neuromorphic-research_database.csv": 1234567890
  }
}
```

### New Format (v2)

```json
{
  "schema_version": "2.0",
  "job_id": "review_20250115_100000",
  "job_type": "full",
  "timestamp": "2025-01-15T10:00:00",
  "database_hash": "abc123",
  "analysis_completed": true,
  "parent_job_id": null,
  "gap_metrics": {
    "total_gaps": 23,
    "gaps_by_pillar": {
      "Pillar 1": 5,
      "Pillar 2": 8,
      "Pillar 3": 10
    }
  },
  "incremental_state": {
    "papers_analyzed": 0,
    "papers_filtered": 0,
    "relevance_threshold": 0.50
  },
  "file_states": {
    "neuromorphic-research_database.csv": 1234567890
  }
}
```

**Migration happens automatically:**
- First run after update detects v1 format
- Auto-converts to v2 during execution
- Preserves all existing data
- Adds new fields with sensible defaults
- No user intervention required

**Data preserved during migration:**
- ✅ Timestamp
- ✅ Database hash
- ✅ Analysis completion status
- ✅ File modification times
- ✅ All gap analysis results

**New fields added:**
- `schema_version`: Version tracking
- `job_id`: Unique job identifier
- `job_type`: "full", "incremental", or "continuation"
- `parent_job_id`: For tracking job lineage
- `gap_metrics`: Summary of gaps from analysis
- `incremental_state`: Tracking for incremental runs

---

## Configuration Migration

### Old Configuration

```json
{
  "version": "1.2.0",
  "output_dir": "gap_analysis_output",
  "stage_timeout": 7200
}
```

### New Configuration (with incremental options)

```json
{
  "version": "2.0.0",
  "output_dir": "gap_analysis_output",
  "stage_timeout": 7200,
  "incremental": {
    "enabled": true,
    "relevance_threshold": 0.50,
    "prefilter_enabled": true,
    "prefilter_mode": "auto"
  }
}
```

**Note:** Old configuration files continue to work. New fields are optional.

---

## Dashboard Migration

### For Dashboard Users

The dashboard automatically supports incremental mode via the UI:

1. **New UI Element**: "Continue Existing Review" toggle on upload page
2. **Job Selection**: Dropdown to select base job for continuation
3. **Gap Preview**: View gaps before starting continuation
4. **Threshold Control**: Slider to adjust relevance threshold

**Migration steps:**
1. Update dashboard: `git pull && pip install -r requirements-dashboard.txt`
2. Restart dashboard: `./run_dashboard.sh`
3. Upload page now shows incremental options
4. Select previous job → Upload new papers → Start continuation

**No changes to existing workflows** - you can continue using the dashboard as before.

---

## Rollback Instructions

If incremental mode causes issues, you can easily revert to traditional full-analysis mode.

### Option 1: Disable via Flag

```bash
# Force full re-analysis (bypasses incremental mode)
python pipeline_orchestrator.py --force --output-dir reviews/baseline
```

### Option 2: Disable via Configuration

Edit `pipeline_config.json`:

```json
{
  "incremental": {
    "enabled": false
  }
}
```

### Option 3: Remove State Files

To completely reset and start fresh:

```bash
# Backup existing results
cp -r reviews/baseline reviews/baseline_backup

# Remove state files (forces full mode)
rm reviews/baseline/orchestrator_state.json

# Run fresh analysis
python pipeline_orchestrator.py --output-dir reviews/baseline
```

### Option 4: Revert Code Version

If you need to revert to pre-incremental version:

```bash
# Find last commit before incremental mode
git log --oneline | grep -B5 "INCR-W2-1"

# Checkout that commit
git checkout <commit-hash-before-incremental>

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Breaking Changes

**None.** Incremental mode was designed to be fully backward compatible.

### What Still Works

✅ All existing CLI commands  
✅ All existing flags and arguments  
✅ Existing configuration files  
✅ Existing state files (auto-migrated)  
✅ Existing output directories  
✅ Dashboard workflows  
✅ All Python imports and APIs  

### What's New (Optional)

- `--incremental` flag (opt-in)
- `--force` flag (explicit full mode)
- `--relevance-threshold` flag (customization)
- `--parent-job-id` flag (lineage tracking)
- New fields in state files (auto-added)
- Dashboard continuation UI (opt-in)

---

## Troubleshooting Migration Issues

### "Incremental prerequisites not met"

**Cause:** No previous analysis in output directory.

**Solution:**
```bash
# Run full analysis first to create baseline
python pipeline_orchestrator.py --force --output-dir reviews/baseline
```

### State file format errors

**Cause:** Corrupted state file.

**Solution:**
```bash
# Remove corrupted state
rm reviews/baseline/orchestrator_state.json

# Re-run analysis
python pipeline_orchestrator.py --output-dir reviews/baseline
```

### Unexpected results after migration

**Cause:** Gap metrics calculated differently.

**Solution:**
```bash
# Force full re-analysis to regenerate all metrics
python pipeline_orchestrator.py --force --output-dir reviews/baseline

# Compare with backup if available
diff reviews/baseline/gap_analysis_report.json reviews/baseline_backup/gap_analysis_report.json
```

### Performance not improved

**Cause:** Few or no gaps to target, or threshold too low.

**Solution:**
```bash
# Check gap report
cat reviews/baseline/gap_analysis_report.json | jq '.summary.total_gaps'

# If gaps are low, incremental mode may not help much
# Consider using full mode or adjusting threshold

# Try more aggressive filtering
python pipeline_orchestrator.py --incremental --relevance-threshold 0.70
```

---

## Support

If you encounter issues during migration:

1. **Check logs**: Review `pipeline.log` for detailed error messages
2. **Backup first**: Always backup your data before making changes
3. **Use --force**: Force full mode as a fallback
4. **Report issues**: https://github.com/BootstrapAI-mgmt/Literature-Review/issues

---

## See Also

- [User Guide](INCREMENTAL_REVIEW_USER_GUIDE.md) - Complete incremental mode documentation
- [API Documentation](api/incremental_endpoints.yaml) - REST API reference
- [Code Examples](../examples/incremental_review_examples.py) - Programming examples
- [README](../README.md) - Main documentation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | Jan 2025 | Initial incremental mode release |
| 1.2.0 | Dec 2024 | Pre-incremental baseline |
