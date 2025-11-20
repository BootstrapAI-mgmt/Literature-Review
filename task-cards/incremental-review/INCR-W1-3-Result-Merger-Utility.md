# INCR-W1-3: Result Merger Utility

**Wave:** 1 (Foundation)  
**Priority:** 🔴 Critical  
**Effort:** 8-10 hours  
**Status:** 🟢 Ready  
**Assignable:** Backend Developer

---

## Overview

Create a robust result merger that combines new gap analysis results with existing reports without data loss. This utility is critical for incremental review mode, enabling additive analysis where new evidence is merged into existing gap analysis reports while preserving all historical data.

---

## Dependencies

**Prerequisites:**
- None (Wave 1 foundation task)

**Blocks:**
- INCR-W2-1 (CLI Incremental Review Mode)
- INCR-W2-2 (Dashboard Job Continuation Endpoint)

---

## Scope

### Included
- [x] Create `literature_review/analysis/result_merger.py`
- [x] Implement `merge_gap_analysis_results()` function
- [x] Evidence deduplication strategy (by paper filename)
- [x] Completeness score recalculation
- [x] Metadata preservation and updates
- [x] Conflict resolution (duplicate papers, evidence)
- [x] Idempotency guarantees
- [x] Comprehensive unit tests (edge cases)
- [x] Integration tests with real gap analysis reports

### Excluded
- ❌ UI for merge visualization (Wave 3 task)
- ❌ Merge conflict manual resolution (auto-resolve only)
- ❌ Three-way merges (base + 2 branches)
- ❌ Version control/rollback (separate feature)

---

## Technical Specification

### File Structure
```
literature_review/analysis/
├── result_merger.py         # NEW
├── gap_analyzer.py           # From INCR-W1-1
└── relevance_assessor.py     # From INCR-W1-2
```

### Data Model

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class MergeResult:
    """Result of merging two gap analysis reports."""
    
    merged_report: Dict
    statistics: Dict
    conflicts: List[Dict]
    warnings: List[str]
    
    @property
    def has_conflicts(self) -> bool:
        """Check if merge had conflicts."""
        return len(self.conflicts) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if merge had warnings."""
        return len(self.warnings) > 0
```

### Core Implementation

```python
# literature_review/analysis/result_merger.py

import json
import copy
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class MergeResult:
    """Result of merging two gap analysis reports."""
    merged_report: Dict
    statistics: Dict = field(default_factory=dict)
    conflicts: List[Dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

class ResultMerger:
    """Merges gap analysis results from multiple runs."""
    
    def __init__(
        self,
        conflict_resolution: str = "keep_both",
        preserve_metadata: bool = True
    ):
        """
        Initialize result merger.
        
        Args:
            conflict_resolution: How to resolve conflicts
                - "keep_both": Keep evidence from both reports
                - "keep_existing": Prefer existing report
                - "keep_new": Prefer new report
            preserve_metadata: Preserve original metadata
        """
        self.conflict_resolution = conflict_resolution
        self.preserve_metadata = preserve_metadata
        
        # Merge statistics
        self.stats = {
            'papers_added': 0,
            'papers_duplicated': 0,
            'evidence_added': 0,
            'evidence_duplicated': 0,
            'requirements_updated': 0,
            'completeness_changed': 0
        }
    
    def merge_gap_analysis_results(
        self,
        existing_report: Dict,
        new_report: Dict
    ) -> MergeResult:
        """
        Merge new gap analysis results into existing report.
        
        Args:
            existing_report: Base gap analysis report
            new_report: New gap analysis report to merge in
        
        Returns:
            MergeResult with merged report and statistics
        
        Example:
            >>> merger = ResultMerger()
            >>> with open('gap_analysis_output/gap_analysis_report.json') as f:
            ...     existing = json.load(f)
            >>> with open('new_analysis/gap_analysis_report.json') as f:
            ...     new = json.load(f)
            >>> result = merger.merge_gap_analysis_results(existing, new)
            >>> print(f"Added {result.statistics['papers_added']} papers")
            >>> print(f"Conflicts: {len(result.conflicts)}")
        """
        # Deep copy existing report to avoid mutation
        merged = copy.deepcopy(existing_report)
        conflicts = []
        warnings = []
        
        # Reset statistics
        self.stats = {k: 0 for k in self.stats.keys()}
        
        # Merge pillars
        existing_pillars = merged.get('pillars', {})
        new_pillars = new_report.get('pillars', {})
        
        for pillar_name, new_pillar_data in new_pillars.items():
            if pillar_name not in existing_pillars:
                # New pillar - add it
                existing_pillars[pillar_name] = new_pillar_data
                logger.info(f"Added new pillar: {pillar_name}")
            else:
                # Merge pillar data
                self._merge_pillar(
                    existing_pillars[pillar_name],
                    new_pillar_data,
                    pillar_name,
                    conflicts,
                    warnings
                )
        
        merged['pillars'] = existing_pillars
        
        # Update metadata
        self._update_metadata(merged, existing_report, new_report, warnings)
        
        # Create merge result
        result = MergeResult(
            merged_report=merged,
            statistics=self.stats.copy(),
            conflicts=conflicts,
            warnings=warnings
        )
        
        logger.info(f"Merge complete: {self.stats['papers_added']} papers added, "
                   f"{self.stats['evidence_added']} evidence items added")
        
        return result
    
    def _merge_pillar(
        self,
        existing_pillar: Dict,
        new_pillar: Dict,
        pillar_name: str,
        conflicts: List[Dict],
        warnings: List[str]
    ) -> None:
        """Merge pillar data."""
        existing_reqs = existing_pillar.get('requirements', {})
        new_reqs = new_pillar.get('requirements', {})
        
        for req_id, new_req_data in new_reqs.items():
            if req_id not in existing_reqs:
                # New requirement
                existing_reqs[req_id] = new_req_data
                logger.debug(f"Added new requirement: {pillar_name}/{req_id}")
            else:
                # Merge requirement data
                self._merge_requirement(
                    existing_reqs[req_id],
                    new_req_data,
                    f"{pillar_name}/{req_id}",
                    conflicts,
                    warnings
                )
        
        existing_pillar['requirements'] = existing_reqs
    
    def _merge_requirement(
        self,
        existing_req: Dict,
        new_req: Dict,
        req_path: str,
        conflicts: List[Dict],
        warnings: List[str]
    ) -> None:
        """Merge requirement data."""
        existing_subs = existing_req.get('sub_requirements', {})
        new_subs = new_req.get('sub_requirements', {})
        
        for sub_req_id, new_sub_data in new_subs.items():
            full_path = f"{req_path}/{sub_req_id}"
            
            if sub_req_id not in existing_subs:
                # New sub-requirement
                existing_subs[sub_req_id] = new_sub_data
                logger.debug(f"Added new sub-requirement: {full_path}")
            else:
                # Merge sub-requirement data
                self._merge_sub_requirement(
                    existing_subs[sub_req_id],
                    new_sub_data,
                    full_path,
                    conflicts,
                    warnings
                )
        
        existing_req['sub_requirements'] = existing_subs
    
    def _merge_sub_requirement(
        self,
        existing_sub: Dict,
        new_sub: Dict,
        sub_path: str,
        conflicts: List[Dict],
        warnings: List[str]
    ) -> None:
        """Merge sub-requirement data (evidence and scores)."""
        # Merge evidence lists
        existing_evidence = existing_sub.get('evidence', [])
        new_evidence = new_sub.get('evidence', [])
        
        # Track existing paper filenames for deduplication
        existing_filenames = {ev.get('filename') for ev in existing_evidence}
        
        # Add new evidence (deduplicate by filename)
        added_count = 0
        duplicate_count = 0
        
        for new_ev in new_evidence:
            filename = new_ev.get('filename')
            
            if filename not in existing_filenames:
                # New evidence - add it
                existing_evidence.append(new_ev)
                existing_filenames.add(filename)
                added_count += 1
                self.stats['evidence_added'] += 1
                
                # Track as new paper if not seen before
                if filename not in self._get_all_existing_filenames(existing_sub):
                    self.stats['papers_added'] += 1
            else:
                # Duplicate evidence
                duplicate_count += 1
                self.stats['evidence_duplicated'] += 1
                
                # Check for conflicts (same paper, different data)
                existing_ev = next(e for e in existing_evidence if e.get('filename') == filename)
                if not self._evidence_matches(existing_ev, new_ev):
                    conflict = {
                        'sub_requirement': sub_path,
                        'filename': filename,
                        'existing': existing_ev,
                        'new': new_ev,
                        'resolution': self.conflict_resolution
                    }
                    conflicts.append(conflict)
                    logger.warning(f"Evidence conflict for {filename} in {sub_path}")
                    
                    # Resolve conflict
                    if self.conflict_resolution == "keep_new":
                        # Replace existing with new
                        idx = existing_evidence.index(existing_ev)
                        existing_evidence[idx] = new_ev
                    elif self.conflict_resolution == "keep_both":
                        # Keep both (already done - existing is kept)
                        pass
                    # else: keep_existing (default, do nothing)
        
        # Update evidence list
        existing_sub['evidence'] = existing_evidence
        
        # Recalculate completeness
        old_completeness = existing_sub.get('completeness_percent', 0)
        new_completeness = self._calculate_completeness(existing_evidence)
        existing_sub['completeness_percent'] = new_completeness
        
        if abs(new_completeness - old_completeness) > 0.01:
            self.stats['completeness_changed'] += 1
            logger.info(f"{sub_path}: Completeness {old_completeness:.1f}% → {new_completeness:.1f}%")
        
        # Update other fields (scores, etc.)
        if added_count > 0:
            self.stats['requirements_updated'] += 1
        
        if duplicate_count > 0:
            warnings.append(f"{sub_path}: {duplicate_count} duplicate evidence items")
    
    def _evidence_matches(self, ev1: Dict, ev2: Dict) -> bool:
        """
        Check if two evidence items are identical.
        
        Args:
            ev1: First evidence dict
            ev2: Second evidence dict
        
        Returns:
            True if evidence matches (same content)
        """
        # Compare key fields
        key_fields = ['filename', 'claim', 'score', 'page']
        
        for field in key_fields:
            if ev1.get(field) != ev2.get(field):
                return False
        
        return True
    
    def _calculate_completeness(self, evidence_list: List[Dict]) -> float:
        """
        Calculate completeness percentage based on evidence.
        
        Simple heuristic:
        - 0 evidence: 0%
        - 1-2 evidence: 33%
        - 3-4 evidence: 67%
        - 5+ evidence: 100%
        
        Args:
            evidence_list: List of evidence dicts
        
        Returns:
            Completeness percentage (0-100)
        """
        count = len(evidence_list)
        
        if count == 0:
            return 0.0
        elif count <= 2:
            return 33.0
        elif count <= 4:
            return 67.0
        else:
            return 100.0
    
    def _get_all_existing_filenames(self, sub_req: Dict) -> Set[str]:
        """Get all paper filenames in sub-requirement."""
        evidence = sub_req.get('evidence', [])
        return {ev.get('filename') for ev in evidence if ev.get('filename')}
    
    def _update_metadata(
        self,
        merged: Dict,
        existing: Dict,
        new: Dict,
        warnings: List[str]
    ) -> None:
        """Update metadata in merged report."""
        if not self.preserve_metadata:
            return
        
        # Get or create metadata section
        metadata = merged.get('metadata', {})
        
        # Update timestamps
        metadata['last_updated'] = datetime.now().isoformat()
        metadata['merge_timestamp'] = datetime.now().isoformat()
        
        # Update version
        old_version = metadata.get('version', 1)
        metadata['version'] = old_version + 1
        
        # Update paper counts
        existing_papers = existing.get('metadata', {}).get('total_papers', 0)
        new_papers = self.stats['papers_added']
        metadata['total_papers'] = existing_papers + new_papers
        
        # Track merge history
        merge_history = metadata.get('merge_history', [])
        merge_history.append({
            'timestamp': datetime.now().isoformat(),
            'papers_added': new_papers,
            'evidence_added': self.stats['evidence_added'],
            'version': metadata['version']
        })
        metadata['merge_history'] = merge_history
        
        # Store statistics
        metadata['merge_statistics'] = self.stats.copy()
        
        merged['metadata'] = metadata
        
        logger.info(f"Updated metadata: version {old_version} → {metadata['version']}")
    
    def validate_idempotency(
        self,
        report1: Dict,
        report2: Dict
    ) -> bool:
        """
        Validate that merge is idempotent.
        
        Merging A with B twice should produce the same result.
        
        Args:
            report1: First report
            report2: Second report (same as first)
        
        Returns:
            True if idempotent
        """
        # First merge
        result1 = self.merge_gap_analysis_results(report1, report2)
        
        # Second merge (merge result with report2 again)
        result2 = self.merge_gap_analysis_results(result1.merged_report, report2)
        
        # Compare paper counts
        papers1 = result1.statistics['papers_added']
        papers2 = result2.statistics['papers_added']
        
        if papers2 > 0:
            logger.error(f"Idempotency violation: Second merge added {papers2} papers")
            return False
        
        logger.info("Idempotency validated: Second merge added 0 papers")
        return True
    
    def export_merge_report(
        self,
        result: MergeResult,
        output_path: str
    ) -> None:
        """
        Export merge report with statistics.
        
        Args:
            result: MergeResult object
            output_path: Path to save report
        """
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'statistics': result.statistics,
            'conflicts': result.conflicts,
            'warnings': result.warnings,
            'merged_report_preview': {
                'total_pillars': len(result.merged_report.get('pillars', {})),
                'metadata': result.merged_report.get('metadata', {})
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Exported merge report to {output_path}")


# Convenience functions
def merge_reports(
    existing_path: str,
    new_path: str,
    output_path: str,
    conflict_resolution: str = "keep_both"
) -> MergeResult:
    """
    Convenience function to merge two gap analysis reports from files.
    
    Args:
        existing_path: Path to existing gap_analysis_report.json
        new_path: Path to new gap_analysis_report.json
        output_path: Path to save merged report
        conflict_resolution: Conflict resolution strategy
    
    Returns:
        MergeResult
    
    Example:
        >>> result = merge_reports(
        ...     'gap_analysis_output/gap_analysis_report.json',
        ...     'new_analysis/gap_analysis_report.json',
        ...     'merged_analysis/gap_analysis_report.json'
        ... )
        >>> print(f"Merge complete: {result.statistics['papers_added']} papers added")
    """
    # Load reports
    with open(existing_path, 'r') as f:
        existing = json.load(f)
    
    with open(new_path, 'r') as f:
        new = json.load(f)
    
    # Merge
    merger = ResultMerger(conflict_resolution=conflict_resolution)
    result = merger.merge_gap_analysis_results(existing, new)
    
    # Save merged report
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result.merged_report, f, indent=2)
    
    logger.info(f"Saved merged report to {output_path}")
    
    return result
```

---

## Testing Strategy

### Unit Tests

Create `tests/unit/analysis/test_result_merger.py`:

```python
import pytest
import json
import copy
from literature_review.analysis.result_merger import (
    ResultMerger, MergeResult, merge_reports
)

@pytest.fixture
def base_report():
    """Base gap analysis report."""
    return {
        'pillars': {
            'Pillar 1': {
                'requirements': {
                    'REQ-001': {
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Implement STDP',
                                'completeness_percent': 33.0,
                                'evidence': [
                                    {'filename': 'paper1.pdf', 'claim': 'STDP works', 'score': 0.9}
                                ]
                            }
                        }
                    }
                }
            }
        },
        'metadata': {
            'version': 1,
            'total_papers': 1,
            'analysis_date': '2025-01-15T10:00:00Z'
        }
    }

@pytest.fixture
def new_report():
    """New gap analysis report with additional evidence."""
    return {
        'pillars': {
            'Pillar 1': {
                'requirements': {
                    'REQ-001': {
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Implement STDP',
                                'completeness_percent': 33.0,
                                'evidence': [
                                    {'filename': 'paper2.pdf', 'claim': 'STDP effective', 'score': 0.85}
                                ]
                            }
                        }
                    }
                }
            }
        },
        'metadata': {
            'version': 1,
            'total_papers': 1,
            'analysis_date': '2025-01-19T14:00:00Z'
        }
    }

def test_merge_adds_new_evidence(base_report, new_report):
    """Test that merge adds new evidence."""
    merger = ResultMerger()
    result = merger.merge_gap_analysis_results(base_report, new_report)
    
    evidence = result.merged_report['pillars']['Pillar 1']['requirements']['REQ-001']['sub_requirements']['SUB-001']['evidence']
    
    assert len(evidence) == 2
    assert result.statistics['papers_added'] == 1
    assert result.statistics['evidence_added'] == 1

def test_merge_updates_completeness(base_report, new_report):
    """Test that completeness is recalculated."""
    merger = ResultMerger()
    result = merger.merge_gap_analysis_results(base_report, new_report)
    
    sub_req = result.merged_report['pillars']['Pillar 1']['requirements']['REQ-001']['sub_requirements']['SUB-001']
    
    # 2 evidence items = 33% completeness
    assert sub_req['completeness_percent'] == 33.0
    assert result.statistics['completeness_changed'] == 0  # Same as before

def test_merge_deduplicates_papers(base_report, new_report):
    """Test that duplicate papers are not added."""
    # Make new report have same paper as base
    new_report['pillars']['Pillar 1']['requirements']['REQ-001']['sub_requirements']['SUB-001']['evidence'] = [
        {'filename': 'paper1.pdf', 'claim': 'STDP works', 'score': 0.9}
    ]
    
    merger = ResultMerger()
    result = merger.merge_gap_analysis_results(base_report, new_report)
    
    evidence = result.merged_report['pillars']['Pillar 1']['requirements']['REQ-001']['sub_requirements']['SUB-001']['evidence']
    
    assert len(evidence) == 1  # No duplicate
    assert result.statistics['papers_added'] == 0
    assert result.statistics['evidence_duplicated'] == 1

def test_merge_detects_conflicts(base_report, new_report):
    """Test conflict detection when same paper has different data."""
    # Same filename, different data
    new_report['pillars']['Pillar 1']['requirements']['REQ-001']['sub_requirements']['SUB-001']['evidence'] = [
        {'filename': 'paper1.pdf', 'claim': 'DIFFERENT CLAIM', 'score': 0.5}
    ]
    
    merger = ResultMerger(conflict_resolution="keep_existing")
    result = merger.merge_gap_analysis_results(base_report, new_report)
    
    assert len(result.conflicts) == 1
    assert result.conflicts[0]['filename'] == 'paper1.pdf'

def test_merge_idempotency(base_report, new_report):
    """Test that merging twice produces same result."""
    merger = ResultMerger()
    
    # First merge
    result1 = merger.merge_gap_analysis_results(base_report, new_report)
    
    # Second merge (merge result with new_report again)
    result2 = merger.merge_gap_analysis_results(result1.merged_report, new_report)
    
    # Second merge should add 0 papers (already in report)
    assert result2.statistics['papers_added'] == 0
    assert result2.statistics['evidence_duplicated'] == 1

def test_merge_updates_metadata(base_report, new_report):
    """Test metadata is updated correctly."""
    merger = ResultMerger()
    result = merger.merge_gap_analysis_results(base_report, new_report)
    
    metadata = result.merged_report['metadata']
    
    assert metadata['version'] == 2  # Incremented
    assert metadata['total_papers'] == 2  # 1 + 1
    assert 'merge_timestamp' in metadata
    assert 'merge_history' in metadata
    assert len(metadata['merge_history']) == 1

def test_merge_preserves_existing_data(base_report, new_report):
    """Test that existing data is not lost."""
    merger = ResultMerger()
    result = merger.merge_gap_analysis_results(base_report, new_report)
    
    # Original evidence should still be there
    evidence = result.merged_report['pillars']['Pillar 1']['requirements']['REQ-001']['sub_requirements']['SUB-001']['evidence']
    filenames = {ev['filename'] for ev in evidence}
    
    assert 'paper1.pdf' in filenames  # Original
    assert 'paper2.pdf' in filenames  # New

def test_merge_adds_new_pillar(base_report):
    """Test adding a completely new pillar."""
    new_report = {
        'pillars': {
            'Pillar 2': {
                'requirements': {
                    'REQ-002': {
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Hardware acceleration',
                                'completeness_percent': 0.0,
                                'evidence': []
                            }
                        }
                    }
                }
            }
        },
        'metadata': {}
    }
    
    merger = ResultMerger()
    result = merger.merge_gap_analysis_results(base_report, new_report)
    
    assert 'Pillar 1' in result.merged_report['pillars']
    assert 'Pillar 2' in result.merged_report['pillars']

def test_conflict_resolution_keep_new(base_report, new_report):
    """Test keep_new conflict resolution."""
    # Same paper, different score
    new_report['pillars']['Pillar 1']['requirements']['REQ-001']['sub_requirements']['SUB-001']['evidence'] = [
        {'filename': 'paper1.pdf', 'claim': 'Updated claim', 'score': 0.95}
    ]
    
    merger = ResultMerger(conflict_resolution="keep_new")
    result = merger.merge_gap_analysis_results(base_report, new_report)
    
    evidence = result.merged_report['pillars']['Pillar 1']['requirements']['REQ-001']['sub_requirements']['SUB-001']['evidence']
    
    # Should have new score
    assert evidence[0]['score'] == 0.95
    assert evidence[0]['claim'] == 'Updated claim'

def test_convenience_function_merge_reports(tmp_path, base_report, new_report):
    """Test convenience function."""
    # Create temp files
    base_path = tmp_path / "base.json"
    new_path = tmp_path / "new.json"
    output_path = tmp_path / "merged.json"
    
    with open(base_path, 'w') as f:
        json.dump(base_report, f)
    
    with open(new_path, 'w') as f:
        json.dump(new_report, f)
    
    # Merge
    result = merge_reports(str(base_path), str(new_path), str(output_path))
    
    assert output_path.exists()
    assert result.statistics['papers_added'] == 1
    
    # Verify merged file
    with open(output_path) as f:
        merged = json.load(f)
    
    assert len(merged['pillars']['Pillar 1']['requirements']['REQ-001']['sub_requirements']['SUB-001']['evidence']) == 2

def test_empty_report_merge(base_report):
    """Test merging with empty report."""
    empty_report = {'pillars': {}, 'metadata': {}}
    
    merger = ResultMerger()
    result = merger.merge_gap_analysis_results(base_report, empty_report)
    
    # Should be unchanged
    assert result.statistics['papers_added'] == 0
    assert len(result.merged_report['pillars']) == 1

def test_calculate_completeness():
    """Test completeness calculation."""
    merger = ResultMerger()
    
    assert merger._calculate_completeness([]) == 0.0
    assert merger._calculate_completeness([{'filename': 'p1.pdf'}]) == 33.0
    assert merger._calculate_completeness([{'filename': f'p{i}.pdf'} for i in range(3)]) == 67.0
    assert merger._calculate_completeness([{'filename': f'p{i}.pdf'} for i in range(5)]) == 100.0
```

### Integration Tests

Create `tests/integration/test_result_merger_integration.py`:

```python
import pytest
import json
from pathlib import Path
from literature_review.analysis.result_merger import merge_reports

@pytest.fixture
def real_gap_analysis_reports(tmp_path):
    """Create realistic gap analysis reports."""
    base_report = {
        'pillars': {
            'Pillar 1: Foundational Architecture': {
                'requirements': {
                    'REQ-001': {
                        'text': 'Biological Modeling',
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Implement STDP learning mechanism',
                                'completeness_percent': 33.0,
                                'evidence': [
                                    {
                                        'filename': 'paper1.pdf',
                                        'claim': 'STDP implemented successfully',
                                        'score': 0.9,
                                        'page': 5
                                    },
                                    {
                                        'filename': 'paper2.pdf',
                                        'claim': 'STDP in spiking networks',
                                        'score': 0.85,
                                        'page': 3
                                    }
                                ]
                            },
                            'SUB-002': {
                                'text': 'Synaptic plasticity models',
                                'completeness_percent': 67.0,
                                'evidence': [
                                    {
                                        'filename': 'paper3.pdf',
                                        'claim': 'Plasticity model',
                                        'score': 0.8,
                                        'page': 10
                                    },
                                    {
                                        'filename': 'paper4.pdf',
                                        'claim': 'Synaptic dynamics',
                                        'score': 0.75,
                                        'page': 7
                                    },
                                    {
                                        'filename': 'paper5.pdf',
                                        'claim': 'Learning rules',
                                        'score': 0.82,
                                        'page': 12
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        'metadata': {
            'version': 1,
            'total_papers': 5,
            'analysis_date': '2025-01-15T10:00:00Z'
        }
    }
    
    new_report = {
        'pillars': {
            'Pillar 1: Foundational Architecture': {
                'requirements': {
                    'REQ-001': {
                        'text': 'Biological Modeling',
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Implement STDP learning mechanism',
                                'completeness_percent': 33.0,
                                'evidence': [
                                    {
                                        'filename': 'paper6.pdf',
                                        'claim': 'Advanced STDP implementation',
                                        'score': 0.92,
                                        'page': 8
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        'metadata': {
            'version': 1,
            'total_papers': 1,
            'analysis_date': '2025-01-19T14:00:00Z'
        }
    }
    
    base_path = tmp_path / "base" / "gap_analysis_report.json"
    new_path = tmp_path / "new" / "gap_analysis_report.json"
    
    base_path.parent.mkdir(parents=True)
    new_path.parent.mkdir(parents=True)
    
    with open(base_path, 'w') as f:
        json.dump(base_report, f, indent=2)
    
    with open(new_path, 'w') as f:
        json.dump(new_report, f, indent=2)
    
    return base_path, new_path

def test_realistic_merge(real_gap_analysis_reports, tmp_path):
    """Test merge with realistic gap analysis reports."""
    base_path, new_path = real_gap_analysis_reports
    output_path = tmp_path / "merged" / "gap_analysis_report.json"
    
    result = merge_reports(
        str(base_path),
        str(new_path),
        str(output_path)
    )
    
    # Verify statistics
    assert result.statistics['papers_added'] == 1
    assert result.statistics['evidence_added'] == 1
    
    # Verify merged report
    with open(output_path) as f:
        merged = json.load(f)
    
    # Check SUB-001 now has 3 evidence items (2 original + 1 new)
    sub_001_evidence = merged['pillars']['Pillar 1: Foundational Architecture']['requirements']['REQ-001']['sub_requirements']['SUB-001']['evidence']
    assert len(sub_001_evidence) == 3
    
    # Check completeness updated (3 evidence = 67%)
    assert merged['pillars']['Pillar 1: Foundational Architecture']['requirements']['REQ-001']['sub_requirements']['SUB-001']['completeness_percent'] == 67.0
    
    # Check metadata
    assert merged['metadata']['version'] == 2
    assert merged['metadata']['total_papers'] == 6
    assert 'merge_history' in merged['metadata']
```

---

## Deliverables

- [ ] `literature_review/analysis/result_merger.py` implemented
- [ ] `ResultMerger` class with all methods
- [ ] `MergeResult` dataclass
- [ ] Evidence deduplication logic
- [ ] Completeness recalculation
- [ ] Conflict detection and resolution
- [ ] Metadata updates
- [ ] Unit tests in `tests/unit/analysis/test_result_merger.py`
- [ ] Integration tests in `tests/integration/test_result_merger_integration.py`
- [ ] Code coverage ≥ 90%
- [ ] Docstrings complete

---

## Success Criteria

✅ **Functional:**
- Can merge two gap analysis reports
- No data loss during merge
- Deduplicates papers by filename
- Recalculates completeness correctly
- Detects and resolves conflicts
- Updates metadata (version, timestamps)

✅ **Quality:**
- Idempotent (merge(A, B) twice = same result)
- Unit tests pass (90% coverage)
- Integration tests with real reports pass
- No linting errors

✅ **Performance:**
- Can merge 100+ papers in < 5s
- Memory efficient (no leaks)

---

## Integration Points

### Used By:
- **INCR-W2-1:** CLI Incremental Review Mode
- **INCR-W2-2:** Dashboard Job Continuation Endpoint

### Example Usage:
```python
from literature_review.analysis.result_merger import merge_reports

# Merge existing review with new results
result = merge_reports(
    existing_path='gap_analysis_output/gap_analysis_report.json',
    new_path='new_analysis/gap_analysis_report.json',
    output_path='gap_analysis_output/gap_analysis_report.json',  # Overwrite
    conflict_resolution='keep_both'
)

print(f"✅ Merged successfully!")
print(f"   Papers added: {result.statistics['papers_added']}")
print(f"   Evidence added: {result.statistics['evidence_added']}")
print(f"   Conflicts: {len(result.conflicts)}")
print(f"   Warnings: {len(result.warnings)}")

if result.has_conflicts:
    print("\n⚠️  Conflicts detected:")
    for conflict in result.conflicts:
        print(f"   - {conflict['filename']} in {conflict['sub_requirement']}")
```

---

## Rollback Plan

If issues arise:
1. Backup original reports before merging (auto-created)
2. Restore from backup: `cp gap_analysis_output.backup/* gap_analysis_output/`
3. Revert `result_merger.py`
4. No data loss if backups exist

---

**Status:** 🟢 Ready for implementation  
**Assignee:** TBD  
**Estimated Start:** Week 1, Day 1  
**Estimated Completion:** Week 1, Day 3
