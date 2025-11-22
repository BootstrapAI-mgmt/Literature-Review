# Dashboard-CLI Parity Task Cards - Wave 2 & 3

This file contains abbreviated task cards for Wave 2 (High Priority) and Wave 3 (Medium Priority) features. Full detailed task cards can be created for each as development begins.

---

## Wave 2: High Priority Features (Weeks 2-3)

### PARITY-W2-1: Config File Upload

**Priority:** 🟠 HIGH | **Effort:** 8-10 hours

**Problem:** CLI accepts `--config custom_config.json` to override defaults. Dashboard has no equivalent.

**Solution:**
- Add file upload input in Advanced Options panel (from W1-2)
- Backend receives uploaded JSON, validates schema
- Passed to pipeline as `--config` flag
- Stored in job metadata for reproducibility

**Key Features:**
- JSON schema validation (matches pipeline_config.json structure)
- Preview uploaded config before execution
- Download current config template
- Merge uploaded config with defaults (partial overrides)

**CLI Parity:** `--config X` → Config file upload (100%)

---

### PARITY-W2-2: Force Re-analysis Control

**Priority:** 🟠 HIGH | **Effort:** 4-6 hours

**Problem:** CLI has `--force` flag to ignore cache and re-run. Dashboard always uses cache when available.

**Solution:**
- Checkbox in Advanced Options: "Force Re-analysis" (already in W1-2 design)
- Backend passes `--force` flag to pipeline
- UI shows warning: "This will ignore cache and may increase costs"
- Job metadata tracks force mode usage

**Key Features:**
- Clear warning about cost implications
- Show estimated cost difference (cached vs fresh)
- Confirmation dialog if budget will be exceeded
- Works with `--clear-cache` (from W2-3)

**CLI Parity:** `--force` → Force Re-analysis checkbox (100%)

---

### PARITY-W2-3: Cache Management

**Priority:** 🟠 HIGH | **Effort:** 6-8 hours

**Problem:** CLI has `--clear-cache` to delete cached responses. Dashboard has no cache visibility or control.

**Solution:**
- Checkbox in Advanced Options: "Clear Cache" (already in W1-2 design)
- New endpoint: `GET /api/cache/stats` (show cache size, hit rate, age)
- New endpoint: `POST /api/cache/clear` (manual cache clearing)
- Dashboard widget showing cache statistics

**Key Features:**
- Cache statistics dashboard (size, entries, hit rate)
- Per-model cache breakdown
- Selective cache clearing (by model, by date, by job)
- Cache warming (pre-populate common queries)

**CLI Parity:** `--clear-cache` → Clear Cache checkbox + cache management UI (100%)

**Additional Value:** Dashboard adds cache visibility CLI doesn't have

---

### PARITY-W2-4: Resume Controls

**Priority:** 🟠 HIGH | **Effort:** 8-12 hours

**Problem:** CLI has `--resume-from-stage X` and `--resume-from-checkpoint X.json`. Dashboard must restart from beginning.

**Solution:**
- Stage selector dropdown in Advanced Options (already in W1-2 design)
- Checkpoint file selector (auto-detect or manual upload)
- Visual stage progress indicator showing completed/pending stages
- Resume button in job detail view for failed jobs

**Key Features:**
- Stage diagram: Gap Analysis → Relevance → Deep Review → Visualization
- Checkboxes to mark which stages to skip
- Checkpoint auto-detection (scans output directory)
- Manual checkpoint upload (for external checkpoints)
- Resume failed jobs from last successful checkpoint

**CLI Parity:** 
- `--resume-from-stage X` → Stage selector (100%)
- `--resume-from-checkpoint X` → Checkpoint selector (100%)

---

### PARITY-W2-5: Pre-filter Configuration

**Priority:** 🟠 HIGH | **Effort:** 6-8 hours

**Problem:** CLI allows configuring pre-filter percentage (`--pre-filter-percent`). Dashboard uses hardcoded default (50%).

**Solution:**
- Slider in Advanced Options: "Pre-filter Threshold" (0-100%)
- Real-time estimate of papers that will pass filter
- Tooltip explaining pre-filter purpose
- Show cost savings from pre-filtering

**Key Features:**
- Slider with percentage display (0-100%)
- Live preview: "Will pre-filter ~X of Y papers"
- Cost estimation: "Estimated savings: $X.XX"
- Default: 50% (matches current behavior)
- Toggle to disable pre-filtering entirely

**CLI Parity:** Pre-filter configuration exposed in UI (85%)

**Note:** CLI doesn't have explicit `--pre-filter-percent` flag yet, but config file has `pre_filtering.enabled`. This feature adds UI for config value.

---

## Wave 3: Medium Priority Enhancements (Week 4)

### PARITY-W3-1: Resource Monitoring Dashboard

**Priority:** 🟡 MEDIUM | **Effort:** 10-14 hours

**Problem:** CLI shows resource usage in logs. Dashboard has no visibility into CPU, memory, cost tracking during job execution.

**Solution:**
- Real-time resource monitoring widget
- Live cost tracker (updates as API calls made)
- CPU/Memory graphs (WebSocket updates)
- Budget progress bar with warnings

**Key Features:**
- Live cost updates (total spent vs budget)
- API call counter (by model, by stage)
- CPU/Memory line charts (last 5 minutes)
- Rate limit status (calls remaining, reset time)
- Budget warnings at 75%, 90%, 100%

**CLI Parity:** Resource monitoring UI (Dashboard advantage - CLI only has logs)

---

### PARITY-W3-2: Direct Directory Access

**Priority:** 🟡 MEDIUM | **Effort:** 12-16 hours

**Problem:** Dashboard import copies files from CLI output directories. Should work with directories directly (like CLI).

**Solution:**
- Allow "in-place" mode for existing directories
- Use symlinks instead of copying (when possible)
- Direct read/write to user-specified paths
- Eliminate import duplication

**Key Features:**
- "Work in-place" checkbox in output directory selector
- Symlink creation for input files (no copying)
- Direct output to user path (no job_id intermediary)
- Import-free continuation workflow

**CLI Parity:** Direct directory access (100%)

**Impact:** Reduces disk usage, improves CLI/Dashboard interoperability

---

### PARITY-W3-3: Dry-Run Mode

**Priority:** 🟡 MEDIUM | **Effort:** 6-8 hours

**Problem:** CLI has `--dry-run` to validate without execution. Dashboard has no preview capability.

**Solution:**
- Checkbox in Advanced Options: "Dry Run" (already in W1-2 design)
- Shows execution plan without running
- Displays: papers to analyze, estimated cost, stages to run
- "Convert to Real Run" button

**Key Features:**
- Execution plan preview (stages, papers, API calls)
- Cost estimation (model calls, pricing)
- Configuration validation (errors highlighted)
- One-click conversion from dry-run to real run
- Dry-run results saved for reference

**CLI Parity:** `--dry-run` → Dry Run checkbox (100%)

---

### PARITY-W3-4: Experimental Features Toggle

**Priority:** 🟡 MEDIUM | **Effort:** 4-6 hours

**Problem:** CLI has `--experimental` flag for cutting-edge features. Dashboard doesn't expose experimental features.

**Solution:**
- Checkbox in Advanced Options: "Enable Experimental Features" (already in W1-2 design)
- Warning about potential instability
- Feature flags for individual experimental features
- Opt-in consent for each experimental feature

**Key Features:**
- Master toggle: "Enable Experimental Features"
- Individual feature toggles (when multiple experimental features exist)
- Clear warnings about stability/support
- Changelog of experimental features
- Feedback form for experimental feature bugs

**CLI Parity:** `--experimental` → Experimental toggle (100%)

**Additional Value:** Dashboard can show experimental feature descriptions

---

## Summary Table

| Task | Priority | Effort | CLI Flag | Dashboard Control | Parity |
|------|----------|--------|----------|-------------------|--------|
| **WAVE 1** |
| W1-1: Output Directory | 🔴 CRITICAL | 12-16h | `--output-dir` | Directory selector | 100% |
| W1-2: Advanced Options | 🔴 CRITICAL | 10-14h | Multiple | Options panel | 85% |
| W1-3: Fresh Analysis | 🔴 CRITICAL | 6-8h | Implicit | Auto-detection | 100% |
| **WAVE 2** |
| W2-1: Config Upload | 🟠 HIGH | 8-10h | `--config` | File upload | 100% |
| W2-2: Force Re-analysis | 🟠 HIGH | 4-6h | `--force` | Checkbox | 100% |
| W2-3: Cache Management | 🟠 HIGH | 6-8h | `--clear-cache` | Checkbox + UI | 100% |
| W2-4: Resume Controls | 🟠 HIGH | 8-12h | `--resume-from-*` | Stage selector | 100% |
| W2-5: Pre-filter Config | 🟠 HIGH | 6-8h | Config value | Slider | 85% |
| **WAVE 3** |
| W3-1: Resource Monitor | 🟡 MEDIUM | 10-14h | Logs only | Live dashboard | 120% |
| W3-2: Direct Directory | 🟡 MEDIUM | 12-16h | Default | In-place mode | 100% |
| W3-3: Dry-Run | 🟡 MEDIUM | 6-8h | `--dry-run` | Checkbox | 100% |
| W3-4: Experimental | 🟡 MEDIUM | 4-6h | `--experimental` | Checkbox | 100% |

**Total Effort:** 92-126 hours  
**Expected Parity After All Waves:** 95%+

---

## Implementation Notes

### Wave 2 Dependencies
- W2-2, W2-3, W2-4, W2-5 all leverage Advanced Options Panel from W1-2
- Most backend logic already exists (CLI flags work), just need UI exposure
- Can parallelize W2-1 through W2-5 (minimal dependencies)

### Wave 3 Enhancements
- W3-1 (Resource Monitoring) requires WebSocket infrastructure (may already exist)
- W3-2 (Direct Directory) builds on W1-1 (Output Directory Selector)
- W3-3, W3-4 already designed in W1-2 (just need backend implementation)

### Quick Wins
Fastest to implement (4-6 hours each):
- W2-2: Force Re-analysis (checkbox + flag pass-through)
- W2-5: Pre-filter Config (slider + config update)
- W3-4: Experimental Features (checkbox + flag)

---

**Document Version:** 1.0  
**Created:** November 21, 2025  
**For:** Waves 2 & 3 of Dashboard-CLI Parity Initiative
