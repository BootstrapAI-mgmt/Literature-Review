# INCR-W1-1: Gap Extraction & Analysis Engine

**Wave:** 1 (Foundation)  
**Priority:** 🔴 Critical  
**Effort:** 6-8 hours  
**Status:** 🟢 Ready  
**Assignable:** Backend Developer

---

## Overview

Create core gap extraction engine that analyzes `gap_analysis_report.json` files to identify sub-requirements with low completeness scores. This is a foundational component required by both CLI incremental mode and Dashboard continuation mode.

---

## Dependencies

**Prerequisites:**
- None (Wave 1 foundation task)

**Blocks:**
- INCR-W2-1 (CLI Incremental Review Mode)
- INCR-W2-2 (Dashboard Job Continuation Endpoint)
- INCR-W4-1 (ML-Based Gap Prioritization)

---

## Scope

### Included
- [x] Create `literature_review/analysis/gap_analyzer.py`
- [x] Implement `Gap` dataclass
- [x] Implement `GapAnalyzer` class with methods:
  - `extract_gaps()` - Main gap extraction from report JSON
  - `classify_gap_severity()` - Categorize by completeness level
  - `generate_gap_summary()` - Create summary statistics
- [x] Comprehensive unit tests (90% coverage target)
- [x] API documentation (docstrings)

### Excluded
- ❌ ML-based gap prioritization (Wave 4)
- ❌ Gap visualization (existing waterfall charts handle this)
- ❌ User-facing UI (Dashboard task)

---

## Technical Specification

### File Structure
```
literature_review/analysis/
├── __init__.py
├── gap_analyzer.py          # NEW
├── judge.py                 # Existing
├── requirements.py          # Existing
└── proof_scorecard.py       # Existing
```

### Data Model

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Gap:
    """Represents a research gap (sub-requirement with low completeness)."""
    
    pillar: str                    # e.g., "Pillar 1: Foundational Architecture"
    requirement_id: str            # e.g., "REQ-001"
    sub_requirement_id: str        # e.g., "SUB-001"
    requirement_text: str          # Full text of the requirement
    current_completeness: float    # 0-100 percentage
    evidence_count: int            # Number of supporting papers
    severity: str                  # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    suggested_searches: List[str]  # Optional: From gap analysis report
    
    @property
    def gap_id(self) -> str:
        """Unique identifier for this gap."""
        return f"{self.requirement_id}-{self.sub_requirement_id}"
    
    @property
    def gap_percentage(self) -> float:
        """Inverse of completeness (100 - completeness)."""
        return 100.0 - self.current_completeness
```

### Main Implementation

```python
# literature_review/analysis/gap_analyzer.py

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class Gap:
    """Represents a research gap."""
    # (see Data Model above)

class GapAnalyzer:
    """Analyzes gap analysis reports to extract and categorize gaps."""
    
    def __init__(self, completeness_threshold: float = 0.8):
        """
        Initialize gap analyzer.
        
        Args:
            completeness_threshold: Threshold below which a sub-requirement
                                   is considered a gap (0.0-1.0). Default: 0.8 (80%)
        """
        self.completeness_threshold = completeness_threshold
        self.severity_thresholds = {
            "CRITICAL": 0.3,   # < 30% completeness
            "HIGH": 0.5,       # 30-50% completeness
            "MEDIUM": 0.7,     # 50-70% completeness
            "LOW": 0.8         # 70-80% completeness
        }
    
    def extract_gaps(
        self,
        report: Dict,
        threshold: Optional[float] = None
    ) -> List[Gap]:
        """
        Extract gaps from gap analysis report.
        
        Args:
            report: Gap analysis report (loaded from gap_analysis_report.json)
            threshold: Override default completeness threshold
        
        Returns:
            List of Gap objects sorted by severity (critical first)
        
        Example:
            >>> analyzer = GapAnalyzer()
            >>> with open('gap_analysis_output/gap_analysis_report.json') as f:
            ...     report = json.load(f)
            >>> gaps = analyzer.extract_gaps(report)
            >>> print(f"Found {len(gaps)} gaps")
            Found 23 gaps
        """
        threshold = threshold or self.completeness_threshold
        gaps = []
        
        # Navigate report structure
        pillars = report.get('pillars', {})
        
        for pillar_name, pillar_data in pillars.items():
            requirements = pillar_data.get('requirements', {})
            
            for req_id, req_data in requirements.items():
                sub_requirements = req_data.get('sub_requirements', {})
                
                for sub_req_id, sub_req_data in sub_requirements.items():
                    completeness = sub_req_data.get('completeness_percent', 0) / 100.0
                    
                    # Check if this is a gap
                    if completeness < threshold:
                        gap = Gap(
                            pillar=pillar_name,
                            requirement_id=req_id,
                            sub_requirement_id=sub_req_id,
                            requirement_text=sub_req_data.get('text', 'N/A'),
                            current_completeness=completeness * 100,
                            evidence_count=len(sub_req_data.get('evidence', [])),
                            severity=self.classify_gap_severity(completeness),
                            suggested_searches=sub_req_data.get('suggested_searches', [])
                        )
                        gaps.append(gap)
        
        # Sort by severity (critical first)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        gaps.sort(key=lambda g: (severity_order[g.severity], g.current_completeness))
        
        logger.info(f"Extracted {len(gaps)} gaps (threshold: {threshold*100:.0f}%)")
        return gaps
    
    def classify_gap_severity(self, completeness: float) -> str:
        """
        Classify gap severity based on completeness score.
        
        Args:
            completeness: Completeness percentage (0.0-1.0)
        
        Returns:
            Severity level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
        """
        if completeness < self.severity_thresholds["CRITICAL"]:
            return "CRITICAL"
        elif completeness < self.severity_thresholds["HIGH"]:
            return "HIGH"
        elif completeness < self.severity_thresholds["MEDIUM"]:
            return "MEDIUM"
        else:
            return "LOW"
    
    def generate_gap_summary(self, gaps: List[Gap]) -> Dict:
        """
        Generate summary statistics for gaps.
        
        Args:
            gaps: List of Gap objects
        
        Returns:
            Summary dictionary with counts, percentages, and breakdowns
        
        Example:
            >>> summary = analyzer.generate_gap_summary(gaps)
            >>> print(summary['total_gaps'])
            23
            >>> print(summary['by_severity']['CRITICAL'])
            5
        """
        summary = {
            'total_gaps': len(gaps),
            'by_severity': {
                'CRITICAL': 0,
                'HIGH': 0,
                'MEDIUM': 0,
                'LOW': 0
            },
            'by_pillar': {},
            'average_completeness': 0.0,
            'most_incomplete': None,
            'least_incomplete': None
        }
        
        if not gaps:
            return summary
        
        # Count by severity
        for gap in gaps:
            summary['by_severity'][gap.severity] += 1
            
            # Count by pillar
            if gap.pillar not in summary['by_pillar']:
                summary['by_pillar'][gap.pillar] = 0
            summary['by_pillar'][gap.pillar] += 1
        
        # Calculate average completeness
        summary['average_completeness'] = sum(g.current_completeness for g in gaps) / len(gaps)
        
        # Find extremes
        summary['most_incomplete'] = min(gaps, key=lambda g: g.current_completeness)
        summary['least_incomplete'] = max(gaps, key=lambda g: g.current_completeness)
        
        return summary
    
    def load_report(self, report_path: str) -> Dict:
        """
        Load gap analysis report from file.
        
        Args:
            report_path: Path to gap_analysis_report.json
        
        Returns:
            Parsed report dictionary
        
        Raises:
            FileNotFoundError: If report file doesn't exist
            json.JSONDecodeError: If report is not valid JSON
        """
        path = Path(report_path)
        if not path.exists():
            raise FileNotFoundError(f"Gap analysis report not found: {report_path}")
        
        with open(path, 'r') as f:
            return json.load(f)
    
    def export_gaps_json(self, gaps: List[Gap], output_path: str) -> None:
        """
        Export gaps to JSON file.
        
        Args:
            gaps: List of Gap objects
            output_path: Path to output JSON file
        """
        gaps_data = [
            {
                'gap_id': gap.gap_id,
                'pillar': gap.pillar,
                'requirement_id': gap.requirement_id,
                'sub_requirement_id': gap.sub_requirement_id,
                'requirement_text': gap.requirement_text,
                'current_completeness': gap.current_completeness,
                'gap_percentage': gap.gap_percentage,
                'evidence_count': gap.evidence_count,
                'severity': gap.severity,
                'suggested_searches': gap.suggested_searches
            }
            for gap in gaps
        ]
        
        with open(output_path, 'w') as f:
            json.dump(gaps_data, f, indent=2)
        
        logger.info(f"Exported {len(gaps)} gaps to {output_path}")


# Convenience functions
def extract_gaps_from_file(
    report_path: str,
    threshold: float = 0.8
) -> List[Gap]:
    """
    Extract gaps from gap analysis report file (convenience function).
    
    Args:
        report_path: Path to gap_analysis_report.json
        threshold: Completeness threshold (0.0-1.0)
    
    Returns:
        List of Gap objects
    """
    analyzer = GapAnalyzer(completeness_threshold=threshold)
    report = analyzer.load_report(report_path)
    return analyzer.extract_gaps(report)
```

---

## Testing Strategy

### Unit Tests

Create `tests/unit/analysis/test_gap_analyzer.py`:

```python
import pytest
import json
from literature_review.analysis.gap_analyzer import GapAnalyzer, Gap, extract_gaps_from_file

@pytest.fixture
def sample_report():
    """Sample gap analysis report."""
    return {
        'pillars': {
            'Pillar 1: Foundational Architecture': {
                'requirements': {
                    'REQ-001': {
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Implement spike-based learning',
                                'completeness_percent': 25.0,
                                'evidence': [{'filename': 'paper1.pdf'}],
                                'suggested_searches': ['spike-timing plasticity']
                            },
                            'SUB-002': {
                                'text': 'Implement STDP mechanism',
                                'completeness_percent': 85.0,
                                'evidence': [
                                    {'filename': 'paper1.pdf'},
                                    {'filename': 'paper2.pdf'},
                                    {'filename': 'paper3.pdf'}
                                ]
                            }
                        }
                    }
                }
            },
            'Pillar 2: Technical Implementation': {
                'requirements': {
                    'REQ-002': {
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Hardware acceleration',
                                'completeness_percent': 60.0,
                                'evidence': [{'filename': 'paper4.pdf'}]
                            }
                        }
                    }
                }
            }
        }
    }

def test_extract_gaps_default_threshold(sample_report):
    """Test gap extraction with default 80% threshold."""
    analyzer = GapAnalyzer()
    gaps = analyzer.extract_gaps(sample_report)
    
    # Should find 2 gaps: SUB-001 (25%) and REQ-002-SUB-001 (60%)
    assert len(gaps) == 2
    assert gaps[0].current_completeness == 25.0
    assert gaps[1].current_completeness == 60.0

def test_extract_gaps_custom_threshold(sample_report):
    """Test gap extraction with custom threshold."""
    analyzer = GapAnalyzer(completeness_threshold=0.5)
    gaps = analyzer.extract_gaps(sample_report)
    
    # Should find only 1 gap: SUB-001 (25%)
    assert len(gaps) == 1
    assert gaps[0].current_completeness == 25.0

def test_classify_gap_severity():
    """Test gap severity classification."""
    analyzer = GapAnalyzer()
    
    assert analyzer.classify_gap_severity(0.2) == "CRITICAL"
    assert analyzer.classify_gap_severity(0.4) == "HIGH"
    assert analyzer.classify_gap_severity(0.6) == "MEDIUM"
    assert analyzer.classify_gap_severity(0.75) == "LOW"

def test_generate_gap_summary(sample_report):
    """Test gap summary generation."""
    analyzer = GapAnalyzer()
    gaps = analyzer.extract_gaps(sample_report)
    summary = analyzer.generate_gap_summary(gaps)
    
    assert summary['total_gaps'] == 2
    assert summary['by_severity']['CRITICAL'] == 1  # 25%
    assert summary['by_severity']['MEDIUM'] == 1    # 60%
    assert summary['average_completeness'] == 42.5  # (25 + 60) / 2

def test_gap_id_property():
    """Test Gap.gap_id property."""
    gap = Gap(
        pillar="Pillar 1",
        requirement_id="REQ-001",
        sub_requirement_id="SUB-002",
        requirement_text="Test",
        current_completeness=50.0,
        evidence_count=1,
        severity="MEDIUM"
    )
    assert gap.gap_id == "REQ-001-SUB-002"

def test_gap_percentage_property():
    """Test Gap.gap_percentage property."""
    gap = Gap(
        pillar="Pillar 1",
        requirement_id="REQ-001",
        sub_requirement_id="SUB-001",
        requirement_text="Test",
        current_completeness=30.0,
        evidence_count=1,
        severity="CRITICAL"
    )
    assert gap.gap_percentage == 70.0

def test_extract_gaps_from_file(tmp_path):
    """Test convenience function for file-based extraction."""
    report = {
        'pillars': {
            'Pillar 1': {
                'requirements': {
                    'REQ-001': {
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Test',
                                'completeness_percent': 50.0,
                                'evidence': []
                            }
                        }
                    }
                }
            }
        }
    }
    
    report_path = tmp_path / "gap_analysis_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f)
    
    gaps = extract_gaps_from_file(str(report_path))
    assert len(gaps) == 1
    assert gaps[0].current_completeness == 50.0

def test_export_gaps_json(tmp_path, sample_report):
    """Test gap export to JSON."""
    analyzer = GapAnalyzer()
    gaps = analyzer.extract_gaps(sample_report)
    
    output_path = tmp_path / "gaps.json"
    analyzer.export_gaps_json(gaps, str(output_path))
    
    assert output_path.exists()
    with open(output_path) as f:
        exported = json.load(f)
    
    assert len(exported) == 2
    assert exported[0]['gap_id'] == "REQ-001-SUB-001"
```

### Coverage Target
- **Minimum:** 90%
- **Stretch:** 95%

---

## Deliverables

- [ ] `literature_review/analysis/gap_analyzer.py` implemented
- [ ] `Gap` dataclass with properties
- [ ] `GapAnalyzer` class with all methods
- [ ] Unit tests in `tests/unit/analysis/test_gap_analyzer.py`
- [ ] Code coverage ≥ 90%
- [ ] Docstrings for all public methods (Google style)
- [ ] Code review approved

---

## Success Criteria

✅ **Functional:**
- Can extract gaps from real `gap_analysis_report.json`
- Correctly filters by completeness threshold
- Returns structured `Gap` objects with all fields
- Severity classification accurate

✅ **Performance:**
- Can process 100+ gaps in < 1 second
- No memory leaks (tested with large reports)

✅ **Quality:**
- Unit tests pass (90% coverage)
- No linting errors (`pylint`, `mypy`)
- Docstrings complete

---

## Integration Points

### Used By:
- **INCR-W2-1:** CLI Incremental Review Mode
- **INCR-W2-2:** Dashboard Job Continuation Endpoint
- **INCR-W4-1:** ML-Based Gap Prioritization

### Example Usage:
```python
from literature_review.analysis.gap_analyzer import GapAnalyzer

# Initialize analyzer
analyzer = GapAnalyzer(completeness_threshold=0.8)

# Load report
report = analyzer.load_report('gap_analysis_output/gap_analysis_report.json')

# Extract gaps
gaps = analyzer.extract_gaps(report)

# Print summary
summary = analyzer.generate_gap_summary(gaps)
print(f"Total gaps: {summary['total_gaps']}")
print(f"Critical: {summary['by_severity']['CRITICAL']}")

# Filter critical gaps
critical_gaps = [g for g in gaps if g.severity == "CRITICAL"]
```

---

## Rollback Plan

If issues arise:
1. Revert `gap_analyzer.py`
2. Remove from imports in dependent modules
3. No data loss (read-only operation)

---

## Out of Scope

- Gap visualization (handled by existing waterfall charts)
- User-facing UI (Dashboard Wave 2-3 tasks)
- ML-based prioritization (Wave 4)
- Automated gap-closing recommendations (separate task)

---

## Notes

- This is a **read-only** operation (no state modification)
- Safe to retry on failure
- Can be used independently of incremental review
- Useful for analytics and reporting

---

**Status:** 🟢 Ready for implementation  
**Assignee:** TBD  
**Estimated Start:** Week 1, Day 1  
**Estimated Completion:** Week 1, Day 2
