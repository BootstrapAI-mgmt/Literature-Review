---
description: Test tiers for the literature review pipeline
domain: testing
type: skill-only
---

## When to Use

Use this skill to validate pipeline integrity at different levels: quick smoke tests (no API), enhanced pipeline tests (with API), or post-merge validation.

## Prerequisites

- Python 3.9+ with `literature_review` package installed
- For e2e tests: `GEMINI_API_KEY` in `.env` file
- For post-merge: relevant PR branches merged

## Test Tiers

### Tier 1: Post-Merge Validation (No API)

Validates module imports and core functions without making API calls.

```bash
python scripts/post_merge_validation.py
```

**Tests:**
1. Module import validation (Judge, DRA, Deep-Reviewer)
2. Version History functions
3. DRA prompting with pillar definitions
4. Large document chunking and batching

**When to run:** After merging PRs, after dependency updates.

### Tier 2: Enhanced Pipeline Smoke Test (With API)

Week 8 verification test covering all Wave 1-3 enhancements.

```bash
python smoke_test_enhanced_pipeline.py
```

**Enhancements tested:**
- Wave 1: Proof Scorecard, Cost Tracking
- Wave 2: Sufficiency Matrix, Proof Chain, Triangulation
- Wave 3: Search Optimizer, Smart Dedup, Evidence Decay
- Adaptive Consensus (enabled by default)

**Expected outputs:** 20+ files across all enhancement categories.
**Run mode:** Single iteration for quick verification.

### Tier 3: Full E2E Smoke Test (With API)

Complete end-to-end test with real Gemini API.

```bash
python e2e_smoke_test.py
```

**Process:**
1. Loads API key from `.env`
2. Runs complete pipeline
3. Verifies all expected outputs
4. Validates enhancement features

**When to run:** Before releases, after major refactors.

## Quick Reference

| Test | API Required | Duration | Scope |
|------|:-----------:|----------|-------|
| `post_merge_validation.py` | No | ~10s | Module imports, core functions |
| `smoke_test_enhanced_pipeline.py` | Yes | ~2-5 min | All enhancements, single iteration |
| `e2e_smoke_test.py` | Yes | ~5-15 min | Full pipeline, all outputs |

## Typical Workflow

```bash
# After code changes:
python scripts/post_merge_validation.py

# Before release:
python smoke_test_enhanced_pipeline.py

# Full validation:
python e2e_smoke_test.py
```

## Related Skills

- [Literature Pipeline](literature-pipeline.md) — The pipeline being tested
- [n8n Management](n8n-management.md) — n8n integration tests
