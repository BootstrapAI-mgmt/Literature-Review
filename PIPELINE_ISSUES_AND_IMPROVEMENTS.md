# Pipeline Issues & Robustness Improvements

> Session: February 22–23, 2026

---

## Issues Encountered

### 1. Overly Conservative Rate Limiting
**Symptom:** Frequent `429 Too Many Requests` errors slowing the pipeline to a crawl.

**Root Cause:** `global_rpm_limit` was set to **10 RPM** while Google's API quota allowed **1,000 RPM**. Additionally, the retry logic in `api_manager.py` had variable scope bugs and an enum unpacking crash.

**Fix Applied:**
- Raised `global_rpm_limit` from 10 → 60 in [global_rate_limiter.py](file:///c:/Users/jpcol/Documents/Literature-Review/Literature-Review/literature_review/utils/global_rate_limiter.py)
- Fixed retry logic bugs in [api_manager.py](file:///c:/Users/jpcol/Documents/Literature-Review/Literature-Review/literature_review/utils/api_manager.py)

---

### 2. Title Extraction False Positives → Valid Reviews Rejected
**Symptom:** Papers like `Image_Processing_Hardware_Acce.pdf` rejected as "hallucinated" despite valid API responses.

**Root Cause:** Two compounding bugs:
- `extract_title_from_text()` grabbed **author names** (e.g., `"Costin-Emanuel Vasile *"`) instead of paper titles
- `validate_review_quotes()` checked quotes against **original text** even when the AI generated them from a **map-reduce summary**

**Fix Applied** in [journal_reviewer.py](file:///c:/Users/jpcol/Documents/Literature-Review/Literature-Review/literature_review/reviewers/journal_reviewer.py):
- Added `_looks_like_author_line()` heuristic (commas, superscripts, institutional markers)
- Added filename fallback for title extraction
- Skipped quote validation for summarized documents

---

### 3. Disk Space Exhaustion → Silent Failures & Corruption
**Symptom:** C: drive hit 0 bytes free. File writes silently failed, `review_version_history.json` corrupted mid-write.

**Root Cause:** No disk space monitoring. A large pipeline run filled the disk, corrupting the 192MB version history file.

**Fix Applied:** Rebuilt version history from the database CSV (192MB corrupted → 19MB clean).

---

### 4. Version History Bloat (38K+ Duplicate Entries)
**Symptom:** `review_version_history.json` grew from ~28MB to 192MB across repeated runs.

**Root Cause:** Each pipeline run appends a new version entry per paper **without deduplication**. After many re-runs, ~900 papers accumulated ~38,883 version entries (~43 per paper).

**No fix applied yet** — see recommendations below.

---

### 5. Missing API Response Fields
**Symptom:** 7 papers failed with `Missing fields: ['SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE']`.

**Root Cause:** Gemini occasionally omits required fields from its JSON response. The pipeline treats this as a hard failure with no fallback.

**No fix applied yet** — see recommendations below.

---

## Recommended Robustness Improvements

### 🔴 Critical

| # | Improvement | File(s) | Effort |
|---|---|---|---|
| R1 | **Pre-flight disk space check** — Abort pipeline if < 500MB free | `pipeline_orchestrator.py` | Low |
| R2 | **Atomic JSON writes** — Write to `.tmp`, then rename (prevents mid-write corruption) | `journal_reviewer.py` | Low |
| R3 | **Version history deduplication** — Deduplicate by timestamp on write; cap at N versions per paper | `journal_reviewer.py` | Medium |

### 🟡 Important

| # | Improvement | File(s) | Effort |
|---|---|---|---|
| R4 | **Default missing API fields** — If `SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE` is missing, default to `"0"` and log a warning instead of hard-failing | `journal_reviewer.py` | Low |
| R5 | **Graceful shutdown handler** — Catch `SIGINT`/`KeyboardInterrupt`, save progress, and flush pending writes before exiting | `pipeline_orchestrator.py` | Medium |
| R6 | **Periodic disk space monitoring** — Check free space every N batches; pause if below threshold | `pipeline_orchestrator.py` | Low |

### 🟢 Nice to Have

| # | Improvement | File(s) | Effort |
|---|---|---|---|
| R7 | **Automatic backup rotation** — Auto-backup version history every N batches (keep last 3) | `journal_reviewer.py` | Medium |
| R8 | **Title extraction confidence score** — Log when the extracted title looks uncertain; skip title gate for low-confidence extractions | `journal_reviewer.py` | Low |
| R9 | **Pipeline health dashboard** — Log a summary of pass/fail/skip/reject counts per batch for quick triage | `pipeline_orchestrator.py` | Medium |
