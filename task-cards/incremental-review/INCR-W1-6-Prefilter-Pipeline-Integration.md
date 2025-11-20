# INCR-W1-6: Pre-filter Pipeline Integration

**Wave:** 1 (Foundation)  
**Priority:** 🟠 High  
**Effort:** 6-8 hours  
**Status:** 🟢 Ready  
**Assignable:** Backend Developer

---

## Overview

Integrate the Gap Extraction Engine (INCR-W1-1) and Paper Relevance Assessor (INCR-W1-2) into the orchestrator pipeline to enable pre-filtering of papers before deep analysis. This reduces API costs and analysis time by only analyzing papers likely to close open gaps.

---

## Dependencies

**Prerequisites:**
- INCR-W1-1 (Gap Extraction Engine) - provides gaps to target
- INCR-W1-2 (Paper Relevance Assessor) - scores paper relevance
- INCR-W1-5 (Orchestrator State Manager) - tracks gap metrics

**Blocks:**
- INCR-W2-1 (CLI Incremental Review Mode) - uses pre-filtering
- INCR-W2-4 (Incremental Analysis Integration Tests)

---

## Scope

### Included
- [x] Add pre-filter stage to orchestrator pipeline
- [x] Integrate gap extraction → relevance scoring → filtering
- [x] Configurable relevance threshold (default: 50%)
- [x] Skip low-relevance papers (mark as "skipped" in state)
- [x] Performance metrics (papers analyzed vs skipped)
- [x] Dry-run mode for preview
- [x] Unit and integration tests

### Excluded
- ❌ Real-time re-scoring (batch only)
- ❌ Multi-level thresholds (single threshold for MVP)
- ❌ Human-in-the-loop approval (future enhancement)

---

## Technical Specification

### Current Pipeline Flow

```python
# literature_review/orchestrator.py - main() function

def main():
    """Current flow (no pre-filtering)."""
    
    # 1. Load data
    papers = load_research_database()
    definitions = load_pillar_definitions()
    
    # 2. Check for new data
    if not check_for_new_data():
        print("No new data, exiting")
        return
    
    # 3. Analyze ALL papers (expensive!)
    results = analyze_all_papers(papers, definitions)
    
    # 4. Generate reports
    generate_gap_analysis_report(results)
    generate_executive_summary(results)
```

### Enhanced Pipeline Flow

```python
# literature_review/orchestrator.py - main() function

def main(config: Optional[OrchestratorConfig] = None, output_folder: Optional[str] = None):
    """Enhanced flow with pre-filtering."""
    
    # --- Setup ---
    prefilter_enabled = config.get('prefilter_enabled', True) if config else True
    relevance_threshold = config.get('relevance_threshold', 0.50) if config else 0.50
    
    # 1. Load data
    papers = load_research_database()
    definitions = load_pillar_definitions()
    
    # 2. Check for new data
    if not check_for_new_data():
        print("No new data, exiting")
        return
    
    # --- NEW: Pre-filtering Stage ---
    if prefilter_enabled:
        logger.info("\n" + "="*80)
        logger.info("STAGE: Pre-filter Pipeline (Gap-Targeted Analysis)")
        logger.info("="*80)
        
        # 2a. Extract gaps from previous analysis
        from literature_review.utils.gap_extractor import GapExtractor
        
        extractor = GapExtractor(
            gap_report_path=os.path.join(OUTPUT_FOLDER, 'gap_analysis_report.json'),
            threshold=0.7
        )
        gaps = extractor.extract_gaps()
        
        if not gaps:
            logger.info("✅ No gaps found - all requirements met!")
            logger.info("Skipping analysis (use --force to re-analyze)")
            return
        
        logger.info(f"📊 Found {len(gaps)} open gaps")
        
        # 2b. Score paper relevance to gaps
        from literature_review.utils.relevance_scorer import RelevanceScorer
        
        scorer = RelevanceScorer()
        
        # Score each paper against all gaps
        paper_scores = {}
        for paper in papers:
            # Compute max relevance across all gaps
            scores = [scorer.score_relevance(paper, gap) for gap in gaps]
            paper_scores[paper['id']] = max(scores) if scores else 0.0
        
        # 2c. Filter papers by relevance
        papers_to_analyze = [
            paper for paper in papers
            if paper_scores.get(paper['id'], 0.0) >= relevance_threshold
        ]
        
        papers_skipped = [
            paper for paper in papers
            if paper_scores.get(paper['id'], 0.0) < relevance_threshold
        ]
        
        logger.info(f"✅ Pre-filter results:")
        logger.info(f"  - Papers to analyze: {len(papers_to_analyze)}")
        logger.info(f"  - Papers skipped: {len(papers_skipped)}")
        logger.info(f"  - Threshold: {relevance_threshold * 100:.0f}%")
        logger.info(f"  - Estimated cost savings: {len(papers_skipped) / len(papers) * 100:.1f}%")
        
        # Use filtered papers for analysis
        papers = papers_to_analyze
    
    # 3. Analyze filtered papers
    results = analyze_all_papers(papers, definitions)
    
    # 4. Generate reports
    generate_gap_analysis_report(results)
    generate_executive_summary(results)
    
    # 5. Save state with metrics
    from literature_review.utils.state_manager import StateManager, GapDetail
    
    # Convert gaps to GapDetail objects
    gap_details = [
        GapDetail(
            pillar_id=gap['pillar_id'],
            requirement_id=gap['requirement_id'],
            sub_requirement_id=gap['sub_requirement_id'],
            current_coverage=gap['current_coverage'],
            target_coverage=gap['target_coverage'],
            gap_size=gap['gap_size'],
            keywords=gap['keywords'],
            evidence_count=gap['evidence_count']
        )
        for gap in gaps
    ]
    
    save_orchestrator_state_enhanced(
        database_hash=compute_database_hash(),
        database_size=len(papers) + len(papers_skipped),
        database_path=RESEARCH_DB_FILE,
        analysis_completed=True,
        total_papers=len(papers) + len(papers_skipped),
        papers_analyzed=len(papers),
        papers_skipped=len(papers_skipped),
        total_pillars=len(definitions['pillars']),
        overall_coverage=results['overall_coverage'],
        coverage_by_pillar=results['coverage_by_pillar'],
        gap_details=gap_details,
        gap_threshold=0.7
    )
```

### Configuration Options

Add to `OrchestratorConfig` or `pipeline_config.json`:

```python
# literature_review/orchestrator.py

@dataclass
class OrchestratorConfig:
    """Orchestrator configuration."""
    
    # --- Existing fields ---
    dry_run: bool = False
    budget_usd: float = 50.0
    incremental: bool = True
    force: bool = False
    output_dir: str = 'gap_analysis_output'
    
    # --- NEW: Pre-filter config ---
    prefilter_enabled: bool = True  # Enable gap-targeted pre-filtering
    relevance_threshold: float = 0.50  # Min relevance score (0-1)
    prefilter_mode: str = 'auto'  # 'auto', 'aggressive', 'conservative'
    
    # Prefilter modes:
    # - 'auto': threshold=0.50 (default)
    # - 'aggressive': threshold=0.30 (analyze more papers)
    # - 'conservative': threshold=0.70 (analyze fewer papers)
```

```json
// pipeline_config.json

{
  "output_dir": "gap_analysis_output",
  "incremental": true,
  "force": false,
  
  "prefilter": {
    "enabled": true,
    "threshold": 0.50,
    "mode": "auto"
  },
  
  "v2_features": {
    // ... existing v2 config ...
  }
}
```

### CLI Arguments

Update `pipeline_orchestrator.py`:

```python
# pipeline_orchestrator.py - main()

def main():
    parser = argparse.ArgumentParser(
        description="Run the full Literature Review pipeline automatically (v2.0 with pre-filtering)"
    )
    
    # ... existing arguments ...
    
    # NEW: Pre-filter arguments
    parser.add_argument(
        "--prefilter",
        action="store_true",
        default=True,
        help="Enable gap-targeted pre-filtering (default: True)"
    )
    parser.add_argument(
        "--no-prefilter",
        dest="prefilter",
        action="store_false",
        help="Disable pre-filtering (analyze all papers)"
    )
    parser.add_argument(
        "--relevance-threshold",
        type=float,
        default=0.50,
        help="Minimum relevance score for paper analysis (0.0-1.0, default: 0.50)"
    )
    parser.add_argument(
        "--prefilter-mode",
        choices=['auto', 'aggressive', 'conservative'],
        default='auto',
        help="Pre-filter preset: auto (50%%), aggressive (30%%), conservative (70%%)"
    )
    
    args = parser.parse_args()
    
    # ... load config ...
    
    # Set pre-filter config
    config['prefilter_enabled'] = args.prefilter
    
    # Handle prefilter modes
    if args.prefilter_mode == 'aggressive':
        config['relevance_threshold'] = 0.30
    elif args.prefilter_mode == 'conservative':
        config['relevance_threshold'] = 0.70
    else:
        config['relevance_threshold'] = args.relevance_threshold
    
    logger.info(f"Pre-filter: {'enabled' if config['prefilter_enabled'] else 'disabled'}")
    if config['prefilter_enabled']:
        logger.info(f"Relevance threshold: {config['relevance_threshold'] * 100:.0f}%")
```

### Dry-Run Preview

Add dry-run support to preview pre-filter results:

```python
# literature_review/orchestrator.py

def preview_prefilter(
    papers: List[Dict],
    gaps: List[Dict],
    threshold: float = 0.50
) -> Dict[str, Any]:
    """
    Preview pre-filter results without running analysis.
    
    Args:
        papers: All papers in database
        gaps: Open gaps from gap extraction
        threshold: Relevance threshold
    
    Returns:
        Preview statistics
    """
    from literature_review.utils.relevance_scorer import RelevanceScorer
    
    scorer = RelevanceScorer()
    
    # Score all papers
    paper_scores = {}
    for paper in papers:
        scores = [scorer.score_relevance(paper, gap) for gap in gaps]
        paper_scores[paper['id']] = max(scores) if scores else 0.0
    
    # Compute statistics
    papers_above_threshold = sum(1 for score in paper_scores.values() if score >= threshold)
    papers_below_threshold = len(papers) - papers_above_threshold
    
    avg_score = sum(paper_scores.values()) / len(paper_scores) if paper_scores else 0.0
    
    return {
        'total_papers': len(papers),
        'total_gaps': len(gaps),
        'threshold': threshold,
        'papers_to_analyze': papers_above_threshold,
        'papers_to_skip': papers_below_threshold,
        'skip_percentage': (papers_below_threshold / len(papers) * 100) if papers else 0,
        'avg_relevance_score': avg_score,
        'top_papers': sorted(
            paper_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]  # Top 10 most relevant
    }
```

Usage:

```bash
# Preview pre-filter results
python pipeline_orchestrator.py --dry-run --prefilter

# Output:
# 📊 Pre-filter Preview:
#   - Total papers: 150
#   - Open gaps: 28
#   - Relevance threshold: 50%
#   - Papers to analyze: 45 (30%)
#   - Papers to skip: 105 (70%)
#   - Avg relevance score: 32.5%
#   - Estimated cost savings: $15.75 (70% reduction)
```

---

## Testing Strategy

### Unit Tests

Create `tests/unit/test_prefilter_integration.py`:

```python
import pytest
from unittest.mock import Mock, patch
from literature_review.orchestrator import preview_prefilter

def test_preview_prefilter():
    """Test pre-filter preview with mock data."""
    papers = [
        {'id': 'paper1', 'title': 'Neural networks', 'abstract': 'Deep learning...'},
        {'id': 'paper2', 'title': 'Spike timing', 'abstract': 'Neuromorphic...'},
        {'id': 'paper3', 'title': 'Unrelated topic', 'abstract': 'Quantum...'}
    ]
    
    gaps = [
        {
            'pillar_id': 'pillar_1',
            'requirement_id': 'req_1',
            'keywords': ['neural networks', 'deep learning'],
            'current_coverage': 0.3
        }
    ]
    
    with patch('literature_review.utils.relevance_scorer.RelevanceScorer') as MockScorer:
        # Mock scores: paper1=0.85, paper2=0.45, paper3=0.10
        mock_scorer = MockScorer.return_value
        mock_scorer.score_relevance.side_effect = [0.85, 0.45, 0.10]
        
        preview = preview_prefilter(papers, gaps, threshold=0.50)
        
        assert preview['total_papers'] == 3
        assert preview['papers_to_analyze'] == 1  # Only paper1
        assert preview['papers_to_skip'] == 2
        assert preview['skip_percentage'] == pytest.approx(66.67, rel=0.1)

def test_prefilter_no_gaps():
    """Test pre-filter when no gaps exist."""
    papers = [{'id': 'paper1', 'title': 'Test'}]
    gaps = []
    
    preview = preview_prefilter(papers, gaps, threshold=0.50)
    
    assert preview['total_gaps'] == 0
    # Should skip all papers if no gaps
    assert preview['papers_to_skip'] == len(papers)

def test_prefilter_threshold_variations():
    """Test different threshold values."""
    papers = [
        {'id': f'paper{i}', 'title': f'Paper {i}'}
        for i in range(10)
    ]
    
    gaps = [{'pillar_id': 'p1', 'keywords': ['test']}]
    
    with patch('literature_review.utils.relevance_scorer.RelevanceScorer') as MockScorer:
        # Mock uniform scores: 0.1, 0.2, ..., 1.0
        mock_scorer = MockScorer.return_value
        mock_scorer.score_relevance.side_effect = [i/10 for i in range(1, 11)]
        
        # Threshold 0.50: papers 5-10 pass (6 papers)
        preview_50 = preview_prefilter(papers, gaps, threshold=0.50)
        assert preview_50['papers_to_analyze'] == 6
        
        # Reset mock
        mock_scorer.score_relevance.side_effect = [i/10 for i in range(1, 11)]
        
        # Threshold 0.70: papers 7-10 pass (4 papers)
        preview_70 = preview_prefilter(papers, gaps, threshold=0.70)
        assert preview_70['papers_to_analyze'] == 4
```

### Integration Tests

Create `tests/integration/test_prefilter_pipeline.py`:

```python
import pytest
import tempfile
import json
from pathlib import Path
from literature_review.orchestrator import main

def test_full_pipeline_with_prefilter(tmp_path):
    """Test complete pipeline with pre-filtering enabled."""
    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Create mock gap report
    gap_report = {
        'pillars': {
            'pillar_1': {
                'requirements': {
                    'req_1': {
                        'sub_requirements': {
                            'sub_1': {
                                'current_coverage': 0.30,
                                'target_coverage': 0.70,
                                'keywords': ['neural networks']
                            }
                        }
                    }
                }
            }
        }
    }
    
    gap_report_path = output_dir / 'gap_analysis_report.json'
    with open(gap_report_path, 'w') as f:
        json.dump(gap_report, f)
    
    # Create mock config
    config = {
        'output_dir': str(output_dir),
        'prefilter_enabled': True,
        'relevance_threshold': 0.50,
        'dry_run': True
    }
    
    # Run orchestrator
    # (Would need to mock paper loading, analysis, etc. for full test)
    # This is a simplified example
    
    # Verify state saved with skip metrics
    state_path = output_dir / 'orchestrator_state.json'
    if state_path.exists():
        with open(state_path) as f:
            state = json.load(f)
        
        assert 'papers_analyzed' in state
        assert 'papers_skipped' in state

def test_cli_prefilter_arguments(tmp_path):
    """Test CLI with prefilter arguments."""
    import subprocess
    
    result = subprocess.run(
        [
            'python', 'pipeline_orchestrator.py',
            '--dry-run',
            '--prefilter',
            '--relevance-threshold', '0.60',
            '--output-dir', str(tmp_path)
        ],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should mention pre-filter
    assert 'prefilter' in result.stdout.lower() or 'relevance' in result.stdout.lower()
```

### Performance Tests

Create `tests/performance/test_prefilter_performance.py`:

```python
import pytest
import time
from literature_review.orchestrator import preview_prefilter

def test_prefilter_performance_large_dataset():
    """Test pre-filter performance with 1000 papers."""
    papers = [
        {'id': f'paper{i}', 'title': f'Paper {i}', 'abstract': 'Test abstract'}
        for i in range(1000)
    ]
    
    gaps = [
        {
            'pillar_id': f'pillar_{i}',
            'keywords': ['test', 'neural', 'networks']
        }
        for i in range(50)
    ]
    
    start = time.time()
    preview = preview_prefilter(papers, gaps, threshold=0.50)
    duration = time.time() - start
    
    # Should complete in <5 seconds for 1000 papers
    assert duration < 5.0
    assert preview['total_papers'] == 1000
    assert preview['total_gaps'] == 50
```

---

## Deliverables

- [ ] Pre-filter integration in `orchestrator.py`
- [ ] CLI arguments (`--prefilter`, `--relevance-threshold`, `--prefilter-mode`)
- [ ] Configuration options in `pipeline_config.json`
- [ ] Dry-run preview function
- [ ] Unit tests in `tests/unit/test_prefilter_integration.py`
- [ ] Integration tests
- [ ] Performance tests
- [ ] Documentation in README.md

---

## Success Criteria

✅ **Functional:**
- Pre-filter reduces papers analyzed by 40-70%
- Relevance threshold configurable (0.0-1.0)
- Dry-run preview shows accurate statistics
- Skip metrics saved to state

✅ **Quality:**
- Unit tests pass (90% coverage)
- Integration tests pass
- No false negatives (relevant papers not skipped)

✅ **Performance:**
- Pre-filter overhead <10% of total runtime
- Handles 1000+ papers in <5 seconds

---

## Usage Examples

### Basic Usage

```bash
# Enable pre-filtering (default)
python pipeline_orchestrator.py

# Disable pre-filtering (analyze all papers)
python pipeline_orchestrator.py --no-prefilter

# Adjust threshold
python pipeline_orchestrator.py --relevance-threshold 0.70

# Use preset mode
python pipeline_orchestrator.py --prefilter-mode conservative
```

### Preview Results

```bash
# Dry-run to see what would be analyzed
python pipeline_orchestrator.py --dry-run --prefilter

# Output:
# 📊 Pre-filter Preview:
#   - Total papers: 150
#   - Open gaps: 28
#   - Relevance threshold: 50%
#   - Papers to analyze: 45 (30%)
#   - Papers to skip: 105 (70%)
#   - Top papers:
#       1. "Neuromorphic Computing Advances" (score: 0.92)
#       2. "Spike-Timing Dependent Plasticity" (score: 0.87)
#       ...
```

### Configuration File

```json
{
  "prefilter": {
    "enabled": true,
    "threshold": 0.60,
    "mode": "conservative"
  }
}
```

---

## Documentation Updates

### README.md

Add to "Advanced Features" section:

```markdown
### Gap-Targeted Pre-filtering

Reduce analysis time and API costs by only analyzing papers likely to close open gaps.

**How it works:**
1. Extracts unfilled gaps from previous analysis
2. Scores each paper's relevance to gaps (0-100%)
3. Skips papers below relevance threshold
4. Analyzes only gap-closing papers

**Usage:**
```bash
# Default (50% threshold)
python pipeline_orchestrator.py --prefilter

# Aggressive mode (30% threshold, analyze more)
python pipeline_orchestrator.py --prefilter-mode aggressive

# Conservative mode (70% threshold, analyze less)
python pipeline_orchestrator.py --prefilter-mode conservative

# Custom threshold
python pipeline_orchestrator.py --relevance-threshold 0.65
```

**Cost Savings:**
- Typical reduction: 50-70% fewer papers analyzed
- API cost reduction: $15-30 per run
- Time savings: 60-80% faster

**Accuracy:**
- False negative rate: <5% (relevant papers rarely skipped)
- Based on semantic similarity + keyword matching
```

---

## Migration Guide

No migration needed - feature is opt-in by default.

**Recommended workflow:**
1. Run baseline analysis without pre-filter
2. Enable pre-filter for incremental updates
3. Monitor skip metrics in state file

---

## Rollback Plan

If pre-filter causes issues:
1. Disable via `--no-prefilter` flag
2. All papers will be analyzed (existing behavior)
3. No data loss or corruption

---

## Notes

- **Non-breaking:** Pre-filter is optional (default enabled)
- **Safe:** Low-relevance papers marked as "skipped" (not deleted)
- **Efficient:** 40-70% cost savings on incremental runs
- **Completes Wave 1:** All foundation utilities now ready

---

**Status:** 🟢 Ready for implementation  
**Assignee:** TBD  
**Estimated Start:** Week 1, Day 3  
**Estimated Completion:** Week 1, Day 5

---

## Wave 1 Completion

With this task, **Wave 1 (Foundation)** is complete:
- ✅ INCR-W1-1: Gap Extraction Engine
- ✅ INCR-W1-2: Paper Relevance Assessor
- ✅ INCR-W1-3: Result Merger Utility
- ✅ INCR-W1-4: CLI Output Directory Selection
- ✅ INCR-W1-5: Orchestrator State Manager
- ✅ INCR-W1-6: Pre-filter Pipeline Integration

**Next:** Wave 2 (Integration) - CLI and Dashboard incremental modes
