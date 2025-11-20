# INCR-W2-5: Documentation & Migration Guide

**Wave:** 2 (Integration)  
**Priority:** 🟠 High  
**Effort:** 4-6 hours  
**Status:** 🟡 Blocked (requires INCR-W2-1, W2-2, W2-3)  
**Assignable:** Technical Writer / Developer

---

## Overview

Create comprehensive documentation for incremental review mode, including user guides, API documentation, migration guides, and troubleshooting resources.

---

## Dependencies

**Prerequisites:**
- ✅ INCR-W2-1 (CLI Incremental Mode)
- ✅ INCR-W2-2 (Dashboard Job Continuation API)
- ✅ INCR-W2-3 (Dashboard Continuation UI)

---

## Scope

### Included
- [x] User guide (CLI & Dashboard)
- [x] API documentation (OpenAPI/Swagger)
- [x] Migration guide (existing users)
- [x] Troubleshooting guide
- [x] Video tutorial (script + recording)
- [x] FAQ section
- [x] Code examples

### Excluded
- ❌ Developer onboarding docs (separate)
- ❌ Architecture deep-dive (separate ADR)

---

## Deliverables

### 1. User Guide: Incremental Review Mode

Create `docs/INCREMENTAL_REVIEW_USER_GUIDE.md`:

```markdown
# Incremental Review Mode - User Guide

## Overview

Incremental review mode allows you to update existing literature reviews by adding new papers without re-analyzing your entire database. This saves time and API costs while building on previous work.

---

## Quick Start

### CLI

```bash
# Step 1: Create baseline review
python pipeline_orchestrator.py --output-dir reviews/baseline

# Step 2: Add new papers to neuromorphic-research_database.csv

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
| `--incremental` | Enable incremental mode | `False` |
| `--force` | Force full re-analysis | `False` |
| `--relevance-threshold` | Min relevance score (0.0-1.0) | `0.50` |
| `--prefilter-mode` | Preset: `auto`, `aggressive`, `conservative` | `auto` |
| `--no-prefilter` | Disable gap-targeted filtering | - |
| `--dry-run` | Preview without running | `False` |

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
- Verify you added papers to CSV
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

---

## Video Tutorial

📹 **Watch:** [Incremental Review Mode in 5 Minutes](https://example.com/tutorial)

Topics covered:
- Setting up baseline review
- Adding new papers
- Running incremental update
- Interpreting results

---

## Support

- **Issues:** https://github.com/org/repo/issues
- **Email:** support@example.com
- **Docs:** https://docs.example.com
```

---

### 2. API Documentation (OpenAPI)

Create `docs/api/incremental_endpoints.yaml`:

```yaml
openapi: 3.0.0
info:
  title: Incremental Review API
  version: 2.0.0
  description: API endpoints for incremental literature review

paths:
  /api/jobs/{job_id}/continue:
    post:
      summary: Create continuation job
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                papers:
                  type: array
                  items:
                    type: object
                relevance_threshold:
                  type: number
                  default: 0.50
                prefilter_enabled:
                  type: boolean
                  default: true
      responses:
        '202':
          description: Job queued
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ContinuationJobResponse'
  
  /api/jobs/{job_id}/gaps:
    get:
      summary: Extract gaps from job
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
        - name: threshold
          in: query
          schema:
            type: number
            default: 0.7
      responses:
        '200':
          description: Gaps extracted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GapsResponse'

components:
  schemas:
    ContinuationJobResponse:
      type: object
      properties:
        job_id:
          type: string
        parent_job_id:
          type: string
        status:
          type: string
        papers_to_analyze:
          type: integer
    
    GapsResponse:
      type: object
      properties:
        job_id:
          type: string
        total_gaps:
          type: integer
        gaps:
          type: array
```

---

### 3. Migration Guide

Create `docs/INCREMENTAL_REVIEW_MIGRATION_GUIDE.md`:

```markdown
# Migration Guide: Incremental Review Mode

## For Existing Users

Incremental mode is **fully backward compatible**. No changes required to existing workflows.

### Opt-In Migration

```bash
# Before (still works)
python pipeline_orchestrator.py

# After (optional)
python pipeline_orchestrator.py --incremental
```

### Recommended Steps

1. **Run one full analysis** to create baseline
2. **Enable incremental mode** for future updates
3. **Monitor performance** (should be 60-80% faster)
4. **Adjust threshold** if too aggressive/conservative

### State File Migration

Old `orchestrator_state.json` (v1) auto-migrates to v2:

**Before (v1):**
```json
{
  "timestamp": "2025-01-15T10:00:00",
  "database_hash": "abc123",
  "analysis_completed": true
}
```

**After (v2):**
```json
{
  "schema_version": "2.0",
  "job_id": "migrated_20250120",
  "job_type": "full",
  "gap_metrics": {...},
  "incremental_state": {...}
}
```

No data loss during migration.

---

## Rollback Instructions

If incremental mode causes issues:

```bash
# Disable incremental (use baseline mode)
python pipeline_orchestrator.py --force

# Or unset environment variable
unset LITERATURE_REVIEW_OUTPUT_DIR
```

---

## Breaking Changes

None. All existing commands work as before.
```

---

### 4. Code Examples

Create `examples/incremental_review_examples.py`:

```python
"""
Incremental Review Mode - Code Examples
"""

from literature_review.orchestrator import main
from literature_review.utils.gap_extractor import GapExtractor
from literature_review.utils.relevance_scorer import RelevanceScorer

# Example 1: Programmatic incremental analysis
def run_incremental_programmatically():
    config = {
        'output_dir': 'reviews/my_review',
        'incremental': True,
        'relevance_threshold': 0.60,
        'prefilter_enabled': True
    }
    
    main(config=config, output_folder='reviews/my_review')

# Example 2: Extract gaps from report
def extract_gaps_example():
    extractor = GapExtractor(
        gap_report_path='reviews/baseline/gap_analysis_report.json',
        threshold=0.7
    )
    
    gaps = extractor.extract_gaps()
    
    for gap in gaps:
        print(f"Gap: {gap['sub_requirement_id']}")
        print(f"  Current: {gap['current_coverage']:.1%}")
        print(f"  Target: {gap['target_coverage']:.1%}")
        print(f"  Keywords: {', '.join(gap['keywords'])}")

# Example 3: Score paper relevance
def score_paper_relevance_example():
    scorer = RelevanceScorer()
    
    paper = {
        'Title': 'Neuromorphic Computing Advances',
        'Abstract': 'This paper explores spike-timing dependent plasticity...'
    }
    
    gap = {
        'keywords': ['spike timing', 'STDP', 'neuromorphic'],
        'current_coverage': 0.3
    }
    
    score = scorer.score_relevance(paper, gap)
    print(f"Relevance score: {score:.1%}")
```

---

## Deliverables Checklist

- [ ] User guide (CLI & Dashboard)
- [ ] API documentation (OpenAPI spec)
- [ ] Migration guide
- [ ] Troubleshooting guide
- [ ] FAQ section
- [ ] Code examples
- [ ] Video tutorial script
- [ ] README updates

---

## Success Criteria

✅ **Completeness:**
- All features documented
- All API endpoints documented
- Migration path clear
- Troubleshooting covers common issues

✅ **Clarity:**
- Non-technical users can follow guide
- Code examples run without errors
- Screenshots/diagrams where helpful

✅ **Accuracy:**
- Technical review by developers
- User testing with documentation
- No broken links or outdated info

---

**Status:** 🟡 Blocked (requires W2-1, W2-2, W2-3)  
**Assignee:** TBD  
**Estimated Start:** Week 2, Day 4  
**Estimated Completion:** Week 2, Day 5
