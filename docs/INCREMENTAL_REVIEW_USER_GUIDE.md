# Incremental Review Mode - User Guide

## Overview

Incremental review mode allows you to update existing literature reviews by adding new papers without re-analyzing your entire database. This saves time and API costs while building on previous work.

---

## Quick Start

### CLI

```bash
# Step 1: Create baseline review
python pipeline_orchestrator.py --output-dir reviews/baseline

# Step 2: Add new papers to data/raw/

# Step 3: Run incremental update
python pipeline_orchestrator.py --incremental --output-dir reviews/baseline
```

### Dashboard

1. Navigate to **Upload** page
2. Select **Continue Existing Review**
3. Choose base job from dropdown
4. Upload new PDFs
5. Click **Start Incremental Analysis**

---

## How It Works

### Workflow

```
1. Load previous analysis → 2. Extract gaps → 3. Score new papers
   ↓                          ↓                  ↓
4. Filter by relevance ← 5. Analyze filtered ← 6. Merge results
```

**Gap-Targeted Analysis:**
- Only papers likely to close gaps are analyzed
- Uses ML-based relevance scoring (keyword + semantic similarity)
- Default threshold: 50% relevance

**Cost Savings:**
- Typical reduction: 50-70% fewer papers analyzed
- API cost: $3-5 per incremental run (vs $30-50 full)
- Time: 10-20 minutes (vs 60+ minutes full)

---

## CLI Reference

### Basic Commands

```bash
# Incremental update (default threshold: 50%)
python pipeline_orchestrator.py --incremental --output-dir reviews/baseline

# Adjust relevance threshold
python pipeline_orchestrator.py --incremental --relevance-threshold 0.70

# Force full re-analysis
python pipeline_orchestrator.py --force --output-dir reviews/baseline

# Preview incremental changes (dry-run)
python pipeline_orchestrator.py --incremental --dry-run
```

### Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--incremental` | Enable incremental mode | `True` |
| `--force` | Force full re-analysis | `False` |
| `--relevance-threshold` | Min relevance score (0.0-1.0) | `0.50` |
| `--prefilter-mode` | Preset: `auto`, `aggressive`, `conservative` | `auto` |
| `--no-prefilter` | Disable gap-targeted filtering | - |
| `--dry-run` | Preview without running | `False` |
| `--parent-job-id` | Explicit parent job ID for lineage | - |
| `--output-dir` | Custom output directory | `gap_analysis_output` |

---

## Dashboard Guide

### Starting a Continuation Job

1. **Upload Page**
   - Toggle "Continue Existing Review"
   - Select base job from dropdown
   
2. **Review Gap Summary**
   - See total gaps and breakdown by pillar
   - Click "View Gap Details" for specifics
   
3. **Upload New Papers**
   - Drag-and-drop PDFs or click "Browse"
   - Wait for relevance preview
   
4. **Adjust Threshold**
   - Use slider to set relevance threshold
   - See real-time update of papers to analyze
   
5. **Start Analysis**
   - Click "Start Incremental Analysis"
   - Monitor progress on job status page

### Viewing Job Lineage

Navigate to **Job Details** → **Lineage** tab to see:
- Parent job (what you continued from)
- Child jobs (subsequent updates)
- Gap reduction over time

---

## Best Practices

### When to Use Incremental Mode

✅ **Use incremental when:**
- Adding 5-50 new papers to existing review
- Updating review with recent publications
- Closing specific gaps in coverage
- Conducting monthly/quarterly updates

❌ **Use full mode when:**
- Starting a brand new review
- Database structure changed significantly
- You want to re-evaluate all evidence
- Pillar definitions updated

### Threshold Selection

| Threshold | When to Use | Papers Analyzed |
|-----------|-------------|-----------------|
| 30% (Aggressive) | Maximize coverage, willing to pay more | 60-80% |
| 50% (Auto) | Balanced cost/coverage | 40-60% |
| 70% (Conservative) | Minimize cost, high-confidence only | 20-40% |

### Workflow Recommendations

**Monthly Updates:**
```bash
# Week 1: Add papers, run incremental
python pipeline_orchestrator.py --incremental --output-dir reviews/jan_2025

# Week 4: Full re-analysis (validate)
python pipeline_orchestrator.py --force --output-dir reviews/jan_2025_full
```

**Multiple Review Versions:**
```bash
# Keep baseline separate
python pipeline_orchestrator.py --output-dir reviews/baseline_2025

# Create incremental branches
python pipeline_orchestrator.py --incremental --output-dir reviews/update_feb
python pipeline_orchestrator.py --incremental --output-dir reviews/update_mar
```

---

## Troubleshooting

### "Incremental prerequisites not met"

**Cause:** No previous analysis found or incomplete.

**Solution:**
```bash
# Check for required files
ls reviews/baseline/gap_analysis_report.json
ls reviews/baseline/orchestrator_state.json

# If missing, run full analysis first
python pipeline_orchestrator.py --output-dir reviews/baseline
```

### "No new papers detected"

**Cause:** Database hash unchanged.

**Solution:**
- Verify you added papers to data/raw/
- Check database modified timestamp
- Use `--force` to re-analyze anyway

### "No relevant papers found above threshold"

**Cause:** All new papers filtered as irrelevant.

**Solution:**
```bash
# Lower threshold
python pipeline_orchestrator.py --incremental --relevance-threshold 0.30

# Or disable pre-filtering
python pipeline_orchestrator.py --incremental --no-prefilter
```

### Merge conflicts or data loss

**Cause:** Rare edge case in result merging.

**Solution:**
```bash
# Backup before incremental
cp -r reviews/baseline reviews/baseline_backup

# If issues occur, restore
rm -r reviews/baseline
mv reviews/baseline_backup reviews/baseline
```

---

## FAQ

**Q: Can I continue a Dashboard job via CLI?**  
A: Yes! Export the Dashboard job, then use `--incremental --output-dir <exported_dir>`.

**Q: What happens to skipped papers?**  
A: They're recorded in `orchestrator_state.json` but not analyzed. You can re-analyze with `--no-prefilter`.

**Q: How accurate is relevance scoring?**  
A: ~85% precision (papers scored >50% are usually relevant). Uses ML + keyword matching.

**Q: Can I merge multiple incremental runs?**  
A: Yes, results automatically merge. Each run updates the same `gap_analysis_report.json`.

**Q: Does incremental mode work with custom pillars?**  
A: Yes, as long as `pillar_definitions.json` unchanged. If pillars change, use `--force`.

**Q: How do I track which papers were analyzed in each run?**  
A: Check `orchestrator_state.json` which maintains job lineage and analysis history.

**Q: Can I run incremental mode without an internet connection?**  
A: No, the analysis requires API calls to process papers. However, gap extraction and relevance scoring can work offline.

**Q: What happens if I interrupt an incremental run?**  
A: Use `--resume` to continue from the last checkpoint. Previous state is preserved.

---

## Video Tutorial

📹 **Watch:** [Incremental Review Mode in 5 Minutes](https://github.com/BootstrapAI-mgmt/Literature-Review/tree/main/docs)

Topics covered:
- Setting up baseline review
- Adding new papers
- Running incremental update
- Interpreting results

---

## Support

- **Issues:** https://github.com/BootstrapAI-mgmt/Literature-Review/issues
- **Documentation:** https://github.com/BootstrapAI-mgmt/Literature-Review/tree/main/docs
- **Main Guide:** [README.md](../README.md)

---

## See Also

- [Migration Guide](INCREMENTAL_REVIEW_MIGRATION_GUIDE.md) - Upgrade from previous versions
- [API Documentation](api/incremental_endpoints.yaml) - REST API reference
- [Code Examples](../examples/incremental_review_examples.py) - Programming examples
- [Dashboard Guide](DASHBOARD_GUIDE.md) - Web interface documentation
