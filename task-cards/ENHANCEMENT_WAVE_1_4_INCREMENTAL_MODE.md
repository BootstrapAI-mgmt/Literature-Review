# Task Card: Incremental Analysis Mode

**Task ID:** ENHANCE-W1-4  
**Wave:** 1 (Foundation & Quick Wins)  
**Priority:** HIGH  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** None

---

## Objective

Enable incremental analysis to only process new/changed papers, reducing runtime by 50-70%.

## Background

Neither third-party review addressed this, but it's essential for iterative workflow. Currently, re-running gap analysis on 100 papers takes ~30 minutes even if only 2 papers changed. Need file fingerprinting and change detection.

## Success Criteria

- [ ] Detect which papers are new or modified since last run
- [ ] Skip analysis for unchanged papers, reuse cached results
- [ ] Handle pillar definition changes (invalidate all)
- [ ] 50-70% runtime reduction for typical incremental updates
- [ ] Support --force flag to re-analyze everything

## Deliverables

### 1. Incremental Analyzer Module

**File:** `literature_review/utils/incremental_analyzer.py`

```python
"""
Incremental Analysis Support
Track paper fingerprints and detect changes for efficient incremental updates.
"""

import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger(__name__)


class IncrementalAnalyzer:
    """Manage incremental analysis state."""
    
    def __init__(self, state_file: str = 'analysis_cache/incremental_state.json'):
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load incremental analysis state."""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        
        return {
            'version': '1.0',
            'last_run': None,
            'pillar_hash': None,
            'paper_fingerprints': {},
            'analysis_results': {}
        }
    
    def _save_state(self):
        """Save incremental analysis state."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _calculate_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of a file."""
        hasher = hashlib.md5()
        
        with open(filepath, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _calculate_pillar_hash(self, pillar_file: str = 'pillar_definitions.json') -> str:
        """Calculate hash of pillar definitions."""
        if not os.path.exists(pillar_file):
            return 'no-pillars'
        
        with open(pillar_file, 'r') as f:
            pillar_data = json.load(f)
        
        # Hash the JSON structure (sorted for consistency)
        pillar_str = json.dumps(pillar_data, sort_keys=True)
        return hashlib.md5(pillar_str.encode()).hexdigest()
    
    def detect_changes(self, paper_dir: str, pillar_file: str = 'pillar_definitions.json',
                      force: bool = False) -> Dict[str, List[str]]:
        """
        Detect which papers need analysis.
        
        Args:
            paper_dir: Directory containing papers (JSON files)
            pillar_file: Path to pillar definitions
            force: Force re-analysis of all papers
        
        Returns:
            Dictionary with 'new', 'modified', 'unchanged', and 'removed' papers
        """
        logger.info("Detecting changes in papers...")
        
        # Check if pillar definitions changed
        current_pillar_hash = self._calculate_pillar_hash(pillar_file)
        pillar_changed = (current_pillar_hash != self.state.get('pillar_hash'))
        
        if pillar_changed:
            logger.warning("⚠️ Pillar definitions changed - all papers need re-analysis")
        
        if force:
            logger.warning("⚠️ Force flag set - re-analyzing all papers")
        
        # Find all current papers
        current_papers = {}
        if os.path.exists(paper_dir):
            for filename in os.listdir(paper_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(paper_dir, filename)
                    file_hash = self._calculate_file_hash(filepath)
                    current_papers[filename] = file_hash
        
        # Compare with previous state
        previous_papers = self.state.get('paper_fingerprints', {})
        
        new_papers = []
        modified_papers = []
        unchanged_papers = []
        removed_papers = []
        
        # Check each current paper
        for filename, current_hash in current_papers.items():
            if filename not in previous_papers:
                new_papers.append(filename)
            elif current_hash != previous_papers[filename]:
                modified_papers.append(filename)
            elif pillar_changed or force:
                modified_papers.append(filename)  # Treat as modified
            else:
                unchanged_papers.append(filename)
        
        # Find removed papers
        for filename in previous_papers:
            if filename not in current_papers:
                removed_papers.append(filename)
        
        changes = {
            'new': sorted(new_papers),
            'modified': sorted(modified_papers),
            'unchanged': sorted(unchanged_papers),
            'removed': sorted(removed_papers)
        }
        
        # Log summary
        logger.info(f"Change detection complete:")
        logger.info(f"  New: {len(new_papers)}")
        logger.info(f"  Modified: {len(modified_papers)}")
        logger.info(f"  Unchanged: {len(unchanged_papers)}")
        logger.info(f"  Removed: {len(removed_papers)}")
        
        return changes
    
    def get_cached_analysis(self, paper_filename: str, stage: str) -> Optional[Dict]:
        """
        Get cached analysis result for a paper.
        
        Args:
            paper_filename: Name of paper file
            stage: Analysis stage (journal_review, judge_analysis, etc.)
        
        Returns:
            Cached analysis result or None if not available
        """
        if paper_filename not in self.state['analysis_results']:
            return None
        
        paper_cache = self.state['analysis_results'][paper_filename]
        return paper_cache.get(stage)
    
    def save_analysis(self, paper_filename: str, stage: str, result: Dict):
        """
        Save analysis result to cache.
        
        Args:
            paper_filename: Name of paper file
            stage: Analysis stage
            result: Analysis result to cache
        """
        if paper_filename not in self.state['analysis_results']:
            self.state['analysis_results'][paper_filename] = {}
        
        self.state['analysis_results'][paper_filename][stage] = result
        self._save_state()
    
    def update_fingerprints(self, paper_dir: str, pillar_file: str = 'pillar_definitions.json'):
        """
        Update file fingerprints after successful analysis.
        
        Args:
            paper_dir: Directory containing papers
            pillar_file: Path to pillar definitions
        """
        logger.info("Updating incremental state...")
        
        # Update pillar hash
        self.state['pillar_hash'] = self._calculate_pillar_hash(pillar_file)
        
        # Update paper fingerprints
        new_fingerprints = {}
        if os.path.exists(paper_dir):
            for filename in os.listdir(paper_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(paper_dir, filename)
                    new_fingerprints[filename] = self._calculate_file_hash(filepath)
        
        self.state['paper_fingerprints'] = new_fingerprints
        self.state['last_run'] = datetime.now().isoformat()
        
        # Remove analysis cache for deleted papers
        for filename in list(self.state['analysis_results'].keys()):
            if filename not in new_fingerprints:
                del self.state['analysis_results'][filename]
                logger.debug(f"Removed cache for deleted paper: {filename}")
        
        self._save_state()
        logger.info("Incremental state updated successfully")
    
    def clear_cache(self, paper_filename: Optional[str] = None):
        """
        Clear analysis cache.
        
        Args:
            paper_filename: Clear cache for specific paper (or all if None)
        """
        if paper_filename:
            if paper_filename in self.state['analysis_results']:
                del self.state['analysis_results'][paper_filename]
                logger.info(f"Cleared cache for {paper_filename}")
        else:
            self.state['analysis_results'] = {}
            logger.info("Cleared all analysis cache")
        
        self._save_state()
    
    def get_stats(self) -> Dict:
        """Get incremental analysis statistics."""
        return {
            'last_run': self.state.get('last_run'),
            'total_papers_cached': len(self.state['paper_fingerprints']),
            'papers_with_analysis': len(self.state['analysis_results']),
            'cache_file': self.state_file,
            'pillar_hash': self.state.get('pillar_hash', 'not-set')
        }


# Singleton instance
_incremental_analyzer = None


def get_incremental_analyzer() -> IncrementalAnalyzer:
    """Get global incremental analyzer instance."""
    global _incremental_analyzer
    if _incremental_analyzer is None:
        _incremental_analyzer = IncrementalAnalyzer()
    return _incremental_analyzer
```

### 2. Orchestrator Integration

**File:** `pipeline_orchestrator.py` (modifications)

```python
from literature_review.utils.incremental_analyzer import get_incremental_analyzer

class PipelineOrchestrator:
    def __init__(self, config):
        # ... existing code ...
        self.incremental = config.get('incremental', True)
        self.force_full = config.get('force', False)
        self.incremental_analyzer = get_incremental_analyzer()
    
    def run(self):
        """Run pipeline with incremental support."""
        
        # Detect changes
        if self.incremental and not self.force_full:
            changes = self.incremental_analyzer.detect_changes(
                paper_dir='data/raw',
                pillar_file='pillar_definitions.json',
                force=self.force_full
            )
            
            papers_to_analyze = changes['new'] + changes['modified']
            
            if not papers_to_analyze:
                logger.info("✅ No changes detected - using cached results")
                # Generate reports from cached data
                self._generate_reports_from_cache()
                return
            
            logger.info(f"📊 Incremental mode: analyzing {len(papers_to_analyze)}/{len(changes['new']) + len(changes['modified']) + len(changes['unchanged'])} papers")
        else:
            # Full analysis
            papers_to_analyze = self._get_all_papers()
            logger.info(f"📊 Full analysis mode: {len(papers_to_analyze)} papers")
        
        # Run analysis stages
        results = {}
        
        for paper_file in papers_to_analyze:
            paper_results = {}
            
            # Stage 1: Journal Review
            cached_review = self.incremental_analyzer.get_cached_analysis(paper_file, 'journal_review')
            if cached_review and self.incremental:
                logger.debug(f"Using cached journal review for {paper_file}")
                paper_results['journal_review'] = cached_review
            else:
                logger.info(f"Running journal review for {paper_file}")
                review = self._run_journal_review(paper_file)
                paper_results['journal_review'] = review
                self.incremental_analyzer.save_analysis(paper_file, 'journal_review', review)
            
            # Stage 2: Judge Analysis
            cached_judge = self.incremental_analyzer.get_cached_analysis(paper_file, 'judge_analysis')
            if cached_judge and self.incremental:
                logger.debug(f"Using cached judge analysis for {paper_file}")
                paper_results['judge_analysis'] = cached_judge
            else:
                logger.info(f"Running judge analysis for {paper_file}")
                judge = self._run_judge_analysis(paper_file, paper_results['journal_review'])
                paper_results['judge_analysis'] = judge
                self.incremental_analyzer.save_analysis(paper_file, 'judge_analysis', judge)
            
            # ... similar pattern for other stages ...
            
            results[paper_file] = paper_results
        
        # Merge with cached results for unchanged papers
        if self.incremental:
            for paper_file in changes.get('unchanged', []):
                cached_results = self._load_all_cached_results(paper_file)
                if cached_results:
                    results[paper_file] = cached_results
        
        # Update fingerprints
        self.incremental_analyzer.update_fingerprints(
            paper_dir='data/raw',
            pillar_file='pillar_definitions.json'
        )
        
        # Generate final reports
        self._generate_gap_analysis(results)
    
    def _load_all_cached_results(self, paper_file: str) -> Optional[Dict]:
        """Load all cached analysis stages for a paper."""
        stages = ['journal_review', 'judge_analysis', 'gap_analysis']
        results = {}
        
        for stage in stages:
            cached = self.incremental_analyzer.get_cached_analysis(paper_file, stage)
            if cached:
                results[stage] = cached
            else:
                return None  # Incomplete cache
        
        return results
    
    def _generate_reports_from_cache(self):
        """Generate reports using only cached data."""
        logger.info("Generating reports from cached analysis...")
        
        # Collect all cached results
        all_results = {}
        for paper_file in self.incremental_analyzer.state['paper_fingerprints'].keys():
            cached = self._load_all_cached_results(paper_file)
            if cached:
                all_results[paper_file] = cached
        
        if not all_results:
            logger.error("No cached results available")
            return
        
        # Generate gap analysis report
        self._generate_gap_analysis(all_results)
        
        logger.info("✅ Reports generated from cache")
```

### 3. CLI Support

**File:** `pipeline_orchestrator.py` (argument parsing)

```python
import argparse

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Literature Review Pipeline')
    
    parser.add_argument(
        '--incremental',
        action='store_true',
        default=True,
        help='Use incremental analysis (default: True)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force full re-analysis of all papers'
    )
    
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear incremental analysis cache before running'
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    if args.clear_cache:
        analyzer = get_incremental_analyzer()
        analyzer.clear_cache()
        logger.info("Cache cleared")
    
    config = load_config('pipeline_config.json')
    config['incremental'] = args.incremental
    config['force'] = args.force
    
    orchestrator = PipelineOrchestrator(config)
    orchestrator.run()
```

### 4. Status Report Script

**File:** `scripts/incremental_status.py`

```python
#!/usr/bin/env python3
"""Show incremental analysis status."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.utils.incremental_analyzer import get_incremental_analyzer


def main():
    analyzer = get_incremental_analyzer()
    
    # Detect current changes
    changes = analyzer.detect_changes(paper_dir='data/raw')
    stats = analyzer.get_stats()
    
    print("\n" + "="*60)
    print("INCREMENTAL ANALYSIS STATUS")
    print("="*60)
    
    print(f"\n📊 Cache Statistics:")
    print(f"   Last Run: {stats['last_run'] or 'Never'}")
    print(f"   Cached Papers: {stats['total_papers_cached']}")
    print(f"   With Analysis: {stats['papers_with_analysis']}")
    
    print(f"\n🔍 Current Status:")
    print(f"   New Papers: {len(changes['new'])}")
    print(f"   Modified Papers: {len(changes['modified'])}")
    print(f"   Unchanged Papers: {len(changes['unchanged'])}")
    print(f"   Removed Papers: {len(changes['removed'])}")
    
    total_papers = len(changes['new']) + len(changes['modified']) + len(changes['unchanged'])
    if total_papers > 0:
        cache_hit_rate = (len(changes['unchanged']) / total_papers) * 100
        print(f"\n💾 Cache Efficiency:")
        print(f"   Hit Rate: {cache_hit_rate:.1f}%")
        
        if changes['new'] or changes['modified']:
            time_saved = len(changes['unchanged']) * 15  # Assume 15s per paper
            print(f"   Est. Time Saved: ~{time_saved}s")
    
    if changes['new']:
        print(f"\n✨ New Papers:")
        for paper in changes['new'][:5]:
            print(f"   - {paper}")
        if len(changes['new']) > 5:
            print(f"   ... and {len(changes['new']) - 5} more")
    
    if changes['modified']:
        print(f"\n📝 Modified Papers:")
        for paper in changes['modified'][:5]:
            print(f"   - {paper}")
        if len(changes['modified']) > 5:
            print(f"   ... and {len(changes['modified']) - 5} more")
    
    print("\n" + "="*60)
    
    # Suggest action
    if changes['new'] or changes['modified']:
        print("💡 Run `python pipeline_orchestrator.py` to process changes")
    else:
        print("✅ All papers are up to date")
    
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
```

## Testing Plan

### Unit Tests

```python
# tests/unit/test_incremental_analyzer.py

import pytest
import tempfile
import os
import json
from literature_review.utils.incremental_analyzer import IncrementalAnalyzer


def test_file_hash_calculation(tmp_path):
    """Test file hash is consistent."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    analyzer = IncrementalAnalyzer()
    hash1 = analyzer._calculate_file_hash(str(test_file))
    hash2 = analyzer._calculate_file_hash(str(test_file))
    
    assert hash1 == hash2


def test_change_detection(tmp_path):
    """Test change detection logic."""
    # Create test papers
    paper1 = tmp_path / "paper1.json"
    paper1.write_text('{"title": "Test Paper 1"}')
    
    analyzer = IncrementalAnalyzer()
    
    # First run - all new
    changes1 = analyzer.detect_changes(str(tmp_path))
    assert len(changes1['new']) == 1
    assert len(changes1['unchanged']) == 0
    
    # Update fingerprints
    analyzer.update_fingerprints(str(tmp_path))
    
    # Second run - no changes
    changes2 = analyzer.detect_changes(str(tmp_path))
    assert len(changes2['new']) == 0
    assert len(changes2['unchanged']) == 1
    
    # Modify paper
    paper1.write_text('{"title": "Modified Paper 1"}')
    
    # Third run - modified
    changes3 = analyzer.detect_changes(str(tmp_path))
    assert len(changes3['modified']) == 1
```

### Integration Tests

```bash
# Test incremental mode
python pipeline_orchestrator.py --incremental

# Add a new paper
cp new_paper.json data/raw/

# Run again - should only process new paper
python pipeline_orchestrator.py --incremental

# Check status
python scripts/incremental_status.py

# Force full re-analysis
python pipeline_orchestrator.py --force
```

## Acceptance Criteria

- [ ] Detects new, modified, and unchanged papers correctly
- [ ] Reuses cached results for unchanged papers
- [ ] Handles pillar definition changes (invalidates all)
- [ ] 50-70% runtime reduction demonstrated
- [ ] --force flag works correctly
- [ ] Cache survives across runs
- [ ] Status script shows accurate information

## Integration Points

- Modify `pipeline_orchestrator.py` to use incremental analyzer
- Add CLI arguments (--incremental, --force, --clear-cache)
- Update `USER_MANUAL.md` with incremental mode instructions

## Performance Impact

- **Expected speedup:** 50-70% for typical incremental updates
- **Example:** 100 papers, 2 changed → analyze 2 instead of 100
- **Runtime:** 30 minutes → 3 minutes

## Notes

- Cache invalidation strategy: conservative (pillar change = full reanalysis)
- File hashing: MD5 sufficient (not cryptographic use case)
- Cache location: `analysis_cache/incremental_state.json`

## Related Tasks

- ENHANCE-W1-3 (Cost Tracker) - Incremental mode reduces API costs
- ENHANCE-W3-3 (Smart Dedup) - Works well with incremental updates

---

**Created:** 2025-11-16  
**Assigned To:** TBD  
**Target Completion:** Wave 1 (Week 1-2)
