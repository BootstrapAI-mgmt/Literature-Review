# Output Management Strategy - Git Commit Policy

**Date:** November 19, 2025  
**Status:** RECOMMENDATION  
**Impact:** Repository size, workflow, CI/CD

---

## Current State Analysis

### What's Currently Committed

**Gap Analysis Output (48MB):**
```
✅ COMMITTED (28 files in gap_analysis_output/):
- gap_analysis_report.json
- executive_summary.md
- All waterfall charts (Pillar 1-7) - 4.6-4.8MB each
- All visualizations (_OVERALL_Research_Gap_Radar.html, _Paper_Network.html, _Research_Trends.html) - 4.6-5.2MB each
- proof_chain.html/json
- sufficiency_matrix.html/json
- triangulation.html/json
- evidence_decay.json
- suggested_searches.json/md
- sub_requirement_paper_contributions.md
- deep_review_directions.json
- optimized_search_plan.json
```

**Other Output Directories:**
```
✅ PARTIALLY COMMITTED:
- proof_scorecard_output/ (2 files, committed)
- outputs/ (smoke test data, not in .gitignore)

⚠️ GITIGNORED (ephemeral):
- workspace/ (dashboard job data) ✅ Correct
- cost_reports/ ✅ Correct
- cache directories ✅ Correct
- log files ✅ Correct
```

### Repository Impact

**Current Situation:**
- 📊 48MB of analysis output files committed
- 🔄 Files show as "Modified" after every run
- 📈 Repository grows with each analysis run
- 🚨 Large HTML files (4-5MB each) tracked in git

**Git Status Issues:**
```bash
$ git status --porcelain | grep gap_analysis
 M gap_analysis_output/_OVERALL_Research_Gap_Radar.html
 M gap_analysis_output/_Paper_Network.html
 M gap_analysis_output/_Research_Trends.html
 M gap_analysis_output/waterfall_Pillar 1.html
 M gap_analysis_output/waterfall_Pillar 2.html
 ... (more modified files)
```

---

## Problem Statement

### Why This is Problematic

1. **Repository Bloat**
   - 48MB baseline from a single analysis run
   - Binary-like HTML files with poor git diff performance
   - Each new analysis = another 48MB of changes
   - Accumulated history grows exponentially

2. **Workflow Confusion**
   - Users see constant "Modified" files
   - Unclear what should be committed
   - Accidental commits of test data
   - Merge conflicts on output files

3. **CI/CD Impact**
   - Slower clones (larger repo)
   - Unnecessary build artifacts in version control
   - Test outputs mixed with source code

4. **Collaboration Issues**
   - Different team members generate different outputs
   - Constant need to resolve output file conflicts
   - Unclear whether changes are intentional

---

## Recommended Strategy

### ✅ RECOMMENDATION: Treat ALL Analysis Outputs as Ephemeral

**Rationale:**
Gap analysis outputs are **generated artifacts**, not source code. They should be treated like:
- Build artifacts (e.g., compiled binaries)
- Test reports (e.g., coverage HTML)
- Log files
- Cache data

**Benefits:**
1. ✅ Clean repository (source code only)
2. ✅ Faster clones and fetches
3. ✅ No merge conflicts on generated files
4. ✅ Clear separation of concerns
5. ✅ Better disk usage
6. ✅ Easier CI/CD integration

---

## Implementation Plan

### Option A: Full Gitignore (RECOMMENDED)

**Action Items:**

1. **Update .gitignore:**
```gitignore
# Analysis outputs (generated artifacts)
gap_analysis_output/
proof_scorecard_output/
outputs/
*_output/
```

2. **Remove existing tracked files:**
```bash
# Move current outputs to safe location
mv gap_analysis_output gap_analysis_output.backup

# Remove from git tracking
git rm -r --cached gap_analysis_output/
git rm -r --cached proof_scorecard_output/
git rm -r --cached outputs/

# Commit cleanup
git commit -m "chore: Remove generated output files from version control

These are generated artifacts and should not be tracked.
Users can regenerate them by running the pipeline.
"

# Restore outputs locally (not tracked)
mv gap_analysis_output.backup gap_analysis_output
```

3. **Create example outputs (optional):**
```bash
# Keep ONE reference example as documentation
mkdir -p data/examples/gap_analysis_EXAMPLE/
cp gap_analysis_output/executive_summary.md data/examples/gap_analysis_EXAMPLE/
cp gap_analysis_output/gap_analysis_report.json data/examples/gap_analysis_EXAMPLE/
# (Keep small representative files only)
```

4. **Update documentation:**
   - README: Explain outputs are not tracked
   - Add note: "Run pipeline to generate outputs"
   - Document where to find example outputs

**Pros:**
- ✅ Clean repository
- ✅ No accidental commits
- ✅ Standard industry practice
- ✅ Scalable long-term

**Cons:**
- ⚠️ New users must run pipeline to see outputs
- ⚠️ No "instant preview" of results

---

### Option B: Keep Example Outputs Only

**Action Items:**

1. **Create examples directory:**
```bash
mkdir -p data/examples/gap_analysis_EXAMPLE/

# Keep small, representative files
cp gap_analysis_output/executive_summary.md data/examples/gap_analysis_EXAMPLE/
cp gap_analysis_output/gap_analysis_report.json data/examples/gap_analysis_EXAMPLE/
cp gap_analysis_output/proof_chain.json data/examples/gap_analysis_EXAMPLE/
# Skip large HTML visualizations (5MB each)
```

2. **Gitignore working outputs:**
```gitignore
# Working outputs (ephemeral)
gap_analysis_output/
proof_scorecard_output/
outputs/

# Keep examples
!data/examples/*_EXAMPLE/
```

3. **Update README:**
```markdown
## Example Outputs

See `data/examples/gap_analysis_EXAMPLE/` for sample output files.

To generate full outputs with visualizations, run:
```bash
python pipeline_orchestrator.py <your-paper.pdf>
```

Outputs will be saved to `gap_analysis_output/` (not tracked in git).
```

**Pros:**
- ✅ New users see example outputs immediately
- ✅ Small documentation footprint
- ✅ Still keeps working outputs untracked

**Cons:**
- ⚠️ Examples can become stale
- ⚠️ Requires maintenance to keep updated

---

### Option C: Keep Current (NOT RECOMMENDED)

**Why Not:**
- ❌ Repository will grow indefinitely
- ❌ Constant merge conflicts
- ❌ Slower for all users
- ❌ Against best practices
- ❌ Confusing for contributors

---

## Comparison Matrix

| Aspect | Option A (Full Gitignore) | Option B (Examples Only) | Option C (Current) |
|--------|--------------------------|-------------------------|-------------------|
| **Repo Size** | ✅ Minimal | ✅ Small (+5MB) | ❌ Large (+48MB+) |
| **Merge Conflicts** | ✅ None | ✅ None | ❌ Frequent |
| **New User Experience** | ⚠️ Must run pipeline | ✅ See examples | ✅ See full output |
| **Maintenance** | ✅ None | ⚠️ Keep examples updated | ❌ High |
| **Best Practices** | ✅ Standard | ✅ Acceptable | ❌ Anti-pattern |
| **CI/CD** | ✅ Fast | ✅ Fast | ⚠️ Slow |
| **Disk Usage** | ✅ Efficient | ✅ Efficient | ❌ Wasteful |

**Recommended:** Option A (Full Gitignore) with optional small examples

---

## Migration Steps

### Phase 1: Preparation (Day 1)

1. **Audit current outputs:**
```bash
# Check total size
du -sh gap_analysis_output/ proof_scorecard_output/ outputs/

# List all committed output files
git ls-files | grep -E "(output|result)" > committed_outputs.txt

# Review what needs archiving
```

2. **Create archive (if needed):**
```bash
# Compress for external storage
tar -czf gap_analysis_archive_$(date +%Y%m%d).tar.gz gap_analysis_output/

# Upload to external storage (S3, Google Drive, etc.)
# This preserves historical outputs if needed
```

3. **Update documentation:**
   - [ ] README.md - Add output generation instructions
   - [ ] CONTRIBUTING.md - Note outputs are not tracked
   - [ ] .gitignore - Add output patterns

### Phase 2: Cleanup (Day 2)

1. **Update .gitignore:**
```bash
cat >> .gitignore << 'EOF'

# Analysis outputs (generated artifacts - not tracked)
# Run pipeline to regenerate locally
gap_analysis_output/
proof_scorecard_output/
outputs/
*_output/
!/data/examples/*_EXAMPLE/
EOF
```

2. **Remove from tracking:**
```bash
git rm -r --cached gap_analysis_output/
git rm -r --cached proof_scorecard_output/
git rm -r --cached outputs/

git commit -m "chore: Remove generated output files from version control

Analysis outputs are generated artifacts and should not be tracked.
Users can regenerate them by running the literature review pipeline.

Rationale:
- Reduces repository size by ~50MB
- Eliminates merge conflicts on generated files
- Follows industry best practices for build artifacts
- Improves clone/fetch performance

See docs/OUTPUT_MANAGEMENT_STRATEGY.md for details.
"
```

3. **Create minimal examples (optional):**
```bash
mkdir -p data/examples/gap_analysis_EXAMPLE/

# Copy small, representative files only
cp gap_analysis_output/executive_summary.md data/examples/gap_analysis_EXAMPLE/
cp gap_analysis_output/gap_analysis_report.json data/examples/gap_analysis_EXAMPLE/

git add data/examples/gap_analysis_EXAMPLE/
git commit -m "docs: Add example gap analysis outputs"
```

### Phase 3: Documentation (Day 3)

Update all references:
- [ ] README.md
- [ ] docs/DASHBOARD_GUIDE.md
- [ ] docs/ORCHESTRATOR_V2_GUIDE.md
- [ ] CONTRIBUTING.md (if exists)

### Phase 4: Team Communication

**Notify team:**
```markdown
📢 HEADS UP: Output Files No Longer Tracked

Starting [DATE], gap analysis output files will no longer be committed to git.

**What changed:**
- `gap_analysis_output/` is now gitignored
- `proof_scorecard_output/` is now gitignored
- `outputs/` is now gitignored

**What to do:**
1. Pull latest changes
2. Run pipeline to regenerate outputs locally
3. Don't try to commit output files (git will ignore them)

**Why:**
- Reduces repo size from XXX MB to YYY MB
- Eliminates merge conflicts on generated files
- Standard practice for build artifacts

**Questions?** See docs/OUTPUT_MANAGEMENT_STRATEGY.md
```

---

## Dashboard Integration

### Current Dashboard Behavior

The dashboard already handles ephemeral outputs correctly:
- ✅ Jobs stored in `workspace/` (already gitignored)
- ✅ Each job gets unique ID and directory
- ✅ Import function copies external results to workspace
- ✅ No expectation of tracked outputs

**No changes needed!** Dashboard is already designed for ephemeral outputs.

### CLI Workflow

**Before:**
```bash
python pipeline_orchestrator.py paper.pdf
# Outputs appear in gap_analysis_output/
# Files show as "Modified" in git status
```

**After:**
```bash
python pipeline_orchestrator.py paper.pdf
# Outputs appear in gap_analysis_output/ (gitignored)
# Clean git status
# Can safely delete and regenerate anytime
```

---

## Alternative: Output Versioning (Advanced)

If you **really** need versioned outputs (rare), consider:

1. **Separate Repository:**
   - Create `Literature-Review-Results` repo
   - Store timestamped output snapshots
   - Link from main repo

2. **Git LFS (Large File Storage):**
   - Track large HTML files with LFS
   - Keeps repo small while versioning outputs
   - Requires LFS setup

3. **External Storage:**
   - S3, Google Drive, etc.
   - Link from main repo documentation
   - Archive old results periodically

**Recommendation:** None of these are necessary for typical use cases.

---

## Rollback Plan

If issues arise, easily revert:

```bash
# Restore outputs to tracking
git checkout <commit-before-removal> -- gap_analysis_output/

# Remove from .gitignore
sed -i '/gap_analysis_output/d' .gitignore

# Commit restoration
git add .gitignore gap_analysis_output/
git commit -m "Revert: Restore output tracking"
```

---

## Final Recommendation

### ✅ IMPLEMENT OPTION A: Full Gitignore

**Action Plan:**
1. Add output directories to `.gitignore`
2. Remove tracked output files via `git rm --cached`
3. Keep 1-2 small example files in `data/examples/`
4. Update documentation
5. Notify team

**Timeline:** 1 day

**Risk:** Low (easily reversible)

**Benefit:** Clean repo, better workflow, industry standard

---

## Questions & Answers

**Q: Will I lose my analysis results?**  
A: No. Files remain on your local disk, just not tracked by git.

**Q: How do I share results with teammates?**  
A: Use the dashboard import/export feature, or compress and share externally.

**Q: What about CI/CD tests?**  
A: Tests should generate outputs on-the-fly, not rely on committed artifacts.

**Q: Can I keep some outputs tracked?**  
A: Yes, use `!data/examples/` pattern in .gitignore for curated examples.

**Q: What if I accidentally delete outputs?**  
A: Re-run the pipeline. That's the point - outputs are reproducible!

---

**Prepared by:** GitHub Copilot  
**Review Status:** Pending Team Approval  
**Implementation Date:** TBD
