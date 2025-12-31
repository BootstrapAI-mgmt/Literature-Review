# Task Card: Recommendation Quality Validation

**Task ID:** VM-W2.5-2  
**Wave:** 2.5 (Output Quality Validation)  
**Priority:** HIGH  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W2-1, VM-W1-4  
**Blocks:** VM-W4-2  
**Validation IDs:** OQ-03, OQ-04, OQ-05, RA-01, RA-02, RA-03, RA-04, RA-05

---

## Objective

Validate that pipeline-generated recommendations (suggested searches, optimized search plans) are accurate, actionable, and relevant to identified gaps. This ensures users receive high-quality guidance for addressing literature gaps.

## Background

The pipeline generates several recommendation-focused outputs:
- **suggested_searches.json** - Machine-readable search suggestions
- **suggested_searches.md** - Human-readable search suggestions
- **optimized_search_plan.json** - Strategically ordered search plan

These recommendations directly influence user actions and research direction. Poor recommendations waste time and resources. The third-party Output Gap Analysis identified that recommendation quality was not being validated.

## Success Criteria

- [ ] OQ-03: suggested_searches.json passes schema validation
- [ ] OQ-04: suggested_searches.md is human-readable with clear formatting
- [ ] OQ-05: optimized_search_plan.json contains coherent strategy
- [ ] RA-01: Search suggestions match known solutions in golden dataset (≥80%)
- [ ] RA-02: Priority ranking accuracy validated against human order
- [ ] RA-03: Every gap has traceable recommendations
- [ ] RA-04: Recommendations are parseable by downstream tools
- [ ] RA-05: No duplicate recommendations in output

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| OQ-03 | Suggested Searches Schema | suggested_searches.json | Valid JSON matching schema | All required fields present |
| OQ-04 | Suggested Searches Readable | suggested_searches.md | Human-readable format | Clear headers, descriptions, priorities |
| OQ-05 | Search Plan Coherence | optimized_search_plan.json | Logical strategy | Dependencies ordered, no circular refs |
| RA-01 | Suggestion Relevance | Golden dataset gaps + suggestions | Match rate ≥80% | Suggestions address known gaps |
| RA-02 | Priority Accuracy | Human-ranked priorities | Correlation ≥0.7 | Ranking matches expert judgment |
| RA-03 | Gap Traceability | All gaps + recommendations | 100% coverage | Every gap linked to recommendation |
| RA-04 | Actionability | Recommendation structure | Parseable output | Valid search query syntax |
| RA-05 | Deduplication | All recommendations | No duplicates | Unique suggestions only |

---

## Deliverables

### 1. JSON Schema Definitions

**File:** `tests/validation/outputs/schemas/suggested_searches.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "suggested_searches.schema.json",
  "title": "Suggested Searches",
  "description": "Schema for pipeline search suggestions output",
  "type": "object",
  "required": ["metadata", "suggestions"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["generated_at", "gap_count", "suggestion_count"],
      "properties": {
        "generated_at": {
          "type": "string",
          "format": "date-time"
        },
        "gap_count": {
          "type": "integer",
          "minimum": 0
        },
        "suggestion_count": {
          "type": "integer",
          "minimum": 0
        },
        "source_report": {
          "type": "string"
        }
      }
    },
    "suggestions": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/suggestion"
      }
    }
  },
  "definitions": {
    "suggestion": {
      "type": "object",
      "required": ["id", "gap_id", "query", "priority", "rationale"],
      "properties": {
        "id": {
          "type": "string"
        },
        "gap_id": {
          "type": "string"
        },
        "query": {
          "type": "string",
          "minLength": 5
        },
        "priority": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10
        },
        "rationale": {
          "type": "string",
          "minLength": 10
        },
        "expected_sources": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["arxiv", "pubmed", "ieee", "acm", "springer", "google_scholar"]
          }
        },
        "keywords": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

**File:** `tests/validation/outputs/schemas/optimized_search_plan.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "optimized_search_plan.schema.json",
  "title": "Optimized Search Plan",
  "description": "Schema for strategically ordered search execution plan",
  "type": "object",
  "required": ["metadata", "strategy", "phases"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["generated_at", "total_searches", "estimated_time_hours"],
      "properties": {
        "generated_at": {
          "type": "string",
          "format": "date-time"
        },
        "total_searches": {
          "type": "integer",
          "minimum": 0
        },
        "estimated_time_hours": {
          "type": "number",
          "minimum": 0
        },
        "optimization_criteria": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    },
    "strategy": {
      "type": "object",
      "required": ["approach", "priority_weights"],
      "properties": {
        "approach": {
          "type": "string",
          "enum": ["breadth_first", "depth_first", "priority_weighted", "gap_severity"]
        },
        "priority_weights": {
          "type": "object",
          "properties": {
            "gap_severity": {"type": "number"},
            "coverage_impact": {"type": "number"},
            "search_efficiency": {"type": "number"}
          }
        }
      }
    },
    "phases": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/phase"
      }
    }
  },
  "definitions": {
    "phase": {
      "type": "object",
      "required": ["phase_id", "name", "searches"],
      "properties": {
        "phase_id": {
          "type": "integer",
          "minimum": 1
        },
        "name": {
          "type": "string"
        },
        "description": {
          "type": "string"
        },
        "depends_on": {
          "type": "array",
          "items": {
            "type": "integer"
          }
        },
        "searches": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

### 2. Test Implementation

**File:** `tests/validation/outputs/test_recommendation_quality.py`

```python
"""
Recommendation Quality Validation Tests

Validates OQ-03, OQ-04, OQ-05, RA-01 through RA-05 from the validation matrix.
Ensures recommendation outputs are accurate, actionable, and properly formatted.
"""

import pytest
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter

import jsonschema
from jsonschema import Draft7Validator

from tests.validation.outputs.test_output_schemas import (
    validate_json_against_schema,
    SchemaValidationResult,
    SCHEMA_DIR
)


# =============================================================================
# Configuration
# =============================================================================

MARKDOWN_SUGGESTION_PATTERNS = {
    "priority_header": r"(?i)^#+\s*(priority|urgency|importance)",
    "search_query": r"(?i)^[-*]\s*\*\*search\*\*:|query:|search:",
    "rationale": r"(?i)^[-*]\s*\*\*rationale\*\*:|reason:|why:",
    "gap_reference": r"(?i)gap[-_]?\d+|addresses gap|for gap"
}

VALID_SEARCH_SYNTAX_PATTERNS = [
    r'^[\w\s\-"]+$',  # Simple keywords
    r'^[\w\s\-"]+\s+(AND|OR|NOT)\s+[\w\s\-"]+',  # Boolean operators
    r'^\(.*\)\s*(AND|OR)\s*\(.*\)$',  # Grouped queries
    r'^"[^"]+"$',  # Exact phrase
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RecommendationQualityMetrics:
    """Metrics for recommendation quality assessment."""
    total_suggestions: int
    unique_suggestions: int
    duplicate_count: int
    gaps_with_suggestions: int
    total_gaps: int
    coverage_rate: float
    avg_priority: float
    parseable_queries: int
    unparseable_queries: List[str] = field(default_factory=list)
    
    @property
    def deduplication_quality(self) -> float:
        """Percentage of unique suggestions."""
        if self.total_suggestions == 0:
            return 1.0
        return self.unique_suggestions / self.total_suggestions
    
    @property
    def actionability_rate(self) -> float:
        """Percentage of parseable queries."""
        if self.total_suggestions == 0:
            return 1.0
        return self.parseable_queries / self.total_suggestions


@dataclass
class TraceabilityResult:
    """Result of gap-to-recommendation traceability check."""
    all_gaps_covered: bool
    covered_gaps: Set[str]
    uncovered_gaps: Set[str]
    orphaned_recommendations: Set[str]  # Recommendations without valid gap reference


@dataclass
class PriorityCorrelation:
    """Result of priority ranking accuracy check."""
    correlation_coefficient: float
    sample_size: int
    system_ranking: List[str]
    expected_ranking: List[str]
    inversions: int  # Number of rank inversions


# =============================================================================
# Validation Functions
# =============================================================================

def validate_markdown_readability(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate that suggestion markdown is human-readable.
    
    Checks for:
    - Clear section headers
    - Structured suggestion format
    - Priority indicators
    - Gap references
    
    Returns:
        Tuple of (is_readable, issues_list)
    """
    issues = []
    
    if not file_path.exists():
        return False, [f"File not found: {file_path}"]
    
    content = file_path.read_text()
    lines = content.split("\n")
    
    # Check for headers
    has_headers = any(line.startswith("#") for line in lines)
    if not has_headers:
        issues.append("No section headers found")
    
    # Check for structured suggestions (bullet points or numbered)
    has_structure = any(
        line.strip().startswith(("-", "*", "1.", "2.", "3."))
        for line in lines
    )
    if not has_structure:
        issues.append("No structured list items found")
    
    # Check for priority indicators
    has_priority = any(
        re.search(r"(?i)(priority|urgent|high|medium|low|P[1-5])", line)
        for line in lines
    )
    if not has_priority:
        issues.append("No priority indicators found")
    
    # Check for gap references
    has_gap_refs = any(
        re.search(MARKDOWN_SUGGESTION_PATTERNS["gap_reference"], line)
        for line in lines
    )
    if not has_gap_refs:
        issues.append("No gap references found")
    
    # Check minimum content length
    content_lines = [l for l in lines if l.strip() and not l.startswith("#")]
    if len(content_lines) < 5:
        issues.append("Insufficient content (< 5 substantive lines)")
    
    return len(issues) == 0, issues


def check_search_plan_coherence(plan_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate search plan has coherent strategy.
    
    Checks for:
    - No circular dependencies between phases
    - Dependencies reference valid phases
    - Phases are properly ordered
    
    Returns:
        Tuple of (is_coherent, issues_list)
    """
    issues = []
    
    phases = plan_data.get("phases", [])
    phase_ids = {p.get("phase_id") for p in phases}
    
    for phase in phases:
        phase_id = phase.get("phase_id")
        depends_on = phase.get("depends_on", [])
        
        # Check for self-dependency
        if phase_id in depends_on:
            issues.append(f"Phase {phase_id} depends on itself")
        
        # Check for invalid dependencies
        for dep in depends_on:
            if dep not in phase_ids:
                issues.append(f"Phase {phase_id} depends on non-existent phase {dep}")
            if dep >= phase_id:
                issues.append(f"Phase {phase_id} depends on later phase {dep}")
    
    # Check for circular dependencies using DFS
    def has_cycle(phase_id: int, visited: Set[int], path: Set[int]) -> bool:
        visited.add(phase_id)
        path.add(phase_id)
        
        phase = next((p for p in phases if p.get("phase_id") == phase_id), None)
        if phase:
            for dep in phase.get("depends_on", []):
                if dep not in visited:
                    if has_cycle(dep, visited, path):
                        return True
                elif dep in path:
                    return True
        
        path.remove(phase_id)
        return False
    
    visited = set()
    for phase in phases:
        phase_id = phase.get("phase_id")
        if phase_id not in visited:
            if has_cycle(phase_id, visited, set()):
                issues.append("Circular dependency detected in phases")
                break
    
    return len(issues) == 0, issues


def check_gap_traceability(
    suggestions: List[Dict],
    known_gaps: Set[str]
) -> TraceabilityResult:
    """
    Check that all gaps have corresponding recommendations.
    
    RA-03: Every gap should be linked to at least one recommendation.
    """
    covered_gaps = set()
    orphaned_recs = set()
    
    for suggestion in suggestions:
        gap_id = suggestion.get("gap_id")
        suggestion_id = suggestion.get("id")
        
        if gap_id:
            covered_gaps.add(gap_id)
            if gap_id not in known_gaps:
                orphaned_recs.add(suggestion_id)
    
    uncovered_gaps = known_gaps - covered_gaps
    
    return TraceabilityResult(
        all_gaps_covered=len(uncovered_gaps) == 0,
        covered_gaps=covered_gaps,
        uncovered_gaps=uncovered_gaps,
        orphaned_recommendations=orphaned_recs
    )


def check_query_actionability(queries: List[str]) -> Tuple[int, List[str]]:
    """
    Check that search queries are parseable and actionable.
    
    RA-04: Recommendations should be usable by downstream search tools.
    """
    parseable_count = 0
    unparseable = []
    
    for query in queries:
        # Check if query matches any valid pattern
        is_valid = False
        for pattern in VALID_SEARCH_SYNTAX_PATTERNS:
            if re.match(pattern, query.strip(), re.IGNORECASE):
                is_valid = True
                break
        
        # Also accept any query with at least 3 words
        if not is_valid and len(query.split()) >= 3:
            is_valid = True
        
        if is_valid:
            parseable_count += 1
        else:
            unparseable.append(query)
    
    return parseable_count, unparseable


def check_deduplication(suggestions: List[Dict]) -> Tuple[int, List[str]]:
    """
    Check for duplicate recommendations.
    
    RA-05: No duplicate suggestions should appear.
    """
    queries = [s.get("query", "").lower().strip() for s in suggestions]
    query_counts = Counter(queries)
    
    duplicates = [q for q, count in query_counts.items() if count > 1]
    duplicate_count = sum(count - 1 for count in query_counts.values() if count > 1)
    
    return duplicate_count, duplicates


def calculate_priority_correlation(
    system_priorities: List[Tuple[str, int]],
    expected_priorities: List[Tuple[str, int]]
) -> PriorityCorrelation:
    """
    Calculate correlation between system and expected priority rankings.
    
    RA-02: Priority ranking should match expert judgment.
    Uses Spearman rank correlation.
    """
    if not system_priorities or not expected_priorities:
        return PriorityCorrelation(
            correlation_coefficient=0.0,
            sample_size=0,
            system_ranking=[],
            expected_ranking=[],
            inversions=0
        )
    
    # Sort by priority to get rankings
    system_sorted = sorted(system_priorities, key=lambda x: x[1])
    expected_sorted = sorted(expected_priorities, key=lambda x: x[1])
    
    system_ranking = [s[0] for s in system_sorted]
    expected_ranking = [s[0] for s in expected_sorted]
    
    # Count inversions (simple measure of ranking accuracy)
    inversions = 0
    common_ids = set(system_ranking) & set(expected_ranking)
    
    for id1 in common_ids:
        for id2 in common_ids:
            sys_pos1 = system_ranking.index(id1) if id1 in system_ranking else -1
            sys_pos2 = system_ranking.index(id2) if id2 in system_ranking else -1
            exp_pos1 = expected_ranking.index(id1) if id1 in expected_ranking else -1
            exp_pos2 = expected_ranking.index(id2) if id2 in expected_ranking else -1
            
            if sys_pos1 < sys_pos2 and exp_pos1 > exp_pos2:
                inversions += 1
    
    # Calculate simple correlation
    n = len(common_ids)
    if n < 2:
        correlation = 1.0 if n == 1 else 0.0
    else:
        max_inversions = n * (n - 1) / 2
        correlation = 1.0 - (inversions / max_inversions) if max_inversions > 0 else 1.0
    
    return PriorityCorrelation(
        correlation_coefficient=correlation,
        sample_size=n,
        system_ranking=system_ranking,
        expected_ranking=expected_ranking,
        inversions=inversions
    )


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_suggested_searches(tmp_path) -> Path:
    """Create sample suggested_searches.json for testing."""
    data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "gap_count": 3,
            "suggestion_count": 5,
            "source_report": "gap_analysis_report.json"
        },
        "suggestions": [
            {
                "id": "search-001",
                "gap_id": "gap-001",
                "query": "neuromorphic power consumption edge deployment",
                "priority": 1,
                "rationale": "Addresses critical gap in power efficiency evidence for edge cases",
                "expected_sources": ["arxiv", "ieee"],
                "keywords": ["neuromorphic", "power", "edge"]
            },
            {
                "id": "search-002",
                "gap_id": "gap-001",
                "query": "spiking neural network energy benchmark",
                "priority": 2,
                "rationale": "Complements search-001 with benchmark-focused papers",
                "expected_sources": ["arxiv", "acm"],
                "keywords": ["SNN", "energy", "benchmark"]
            },
            {
                "id": "search-003",
                "gap_id": "gap-002",
                "query": "on-chip learning scalability neuromorphic",
                "priority": 3,
                "rationale": "Addresses gap in learning algorithm scalability",
                "expected_sources": ["ieee", "springer"],
                "keywords": ["on-chip", "learning", "scalability"]
            }
        ]
    }
    
    output_path = tmp_path / "suggested_searches.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return output_path


@pytest.fixture
def sample_suggested_searches_md(tmp_path) -> Path:
    """Create sample suggested_searches.md for testing."""
    content = """# Suggested Literature Searches

## Priority 1 (Critical)

### Search: Neuromorphic Power Efficiency
- **Query**: neuromorphic power consumption edge deployment
- **Addresses Gap**: GAP-001 (Power efficiency in edge deployments)
- **Rationale**: Critical gap with no current evidence for edge deployment scenarios
- **Expected Sources**: arXiv, IEEE Xplore

## Priority 2 (High)

### Search: SNN Energy Benchmarks
- **Query**: spiking neural network energy benchmark
- **Addresses Gap**: GAP-001 (Power efficiency)
- **Rationale**: Benchmark data needed to validate power claims
- **Expected Sources**: arXiv, ACM DL

## Priority 3 (Medium)

### Search: On-Chip Learning
- **Query**: on-chip learning scalability neuromorphic
- **Addresses Gap**: GAP-002 (Learning algorithm scalability)
- **Rationale**: Scalability unclear for large-scale implementations
- **Expected Sources**: IEEE, Springer

---

*Generated by Literature Review Pipeline*
"""
    
    output_path = tmp_path / "suggested_searches.md"
    output_path.write_text(content)
    
    return output_path


@pytest.fixture
def sample_optimized_search_plan(tmp_path) -> Path:
    """Create sample optimized_search_plan.json for testing."""
    data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_searches": 5,
            "estimated_time_hours": 4.5,
            "optimization_criteria": ["gap_severity", "coverage_impact"]
        },
        "strategy": {
            "approach": "priority_weighted",
            "priority_weights": {
                "gap_severity": 0.5,
                "coverage_impact": 0.3,
                "search_efficiency": 0.2
            }
        },
        "phases": [
            {
                "phase_id": 1,
                "name": "Critical Gap Coverage",
                "description": "Address highest-severity gaps first",
                "depends_on": [],
                "searches": ["search-001", "search-002"]
            },
            {
                "phase_id": 2,
                "name": "Secondary Gap Coverage",
                "description": "Address high-priority gaps",
                "depends_on": [1],
                "searches": ["search-003"]
            },
            {
                "phase_id": 3,
                "name": "Validation Searches",
                "description": "Cross-validate findings from earlier phases",
                "depends_on": [1, 2],
                "searches": ["search-004", "search-005"]
            }
        ]
    }
    
    output_path = tmp_path / "optimized_search_plan.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return output_path


@pytest.fixture
def golden_dataset_gaps() -> Set[str]:
    """Known gaps from golden dataset for traceability testing."""
    return {"gap-001", "gap-002", "gap-003"}


@pytest.fixture
def expected_priority_ranking() -> List[Tuple[str, int]]:
    """Human-validated priority ranking for correlation testing."""
    return [
        ("search-001", 1),  # Most important
        ("search-002", 2),
        ("search-003", 3),
    ]


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.validation
@pytest.mark.output_quality
@pytest.mark.recommendation
class TestRecommendationSchemaValidation:
    """Test suite for recommendation output schema validation (OQ-03, OQ-04, OQ-05)."""
    
    # -------------------------------------------------------------------------
    # OQ-03: Suggested Searches JSON Schema
    # -------------------------------------------------------------------------
    
    def test_suggested_searches_schema_exists(self):
        """Verify schema definition file exists."""
        schema_path = SCHEMA_DIR / "suggested_searches.schema.json"
        assert schema_path.exists(), f"Schema file missing: {schema_path}"
    
    def test_suggested_searches_valid_schema(self, sample_suggested_searches):
        """
        OQ-03: Validate suggested_searches.json against schema.
        """
        result = validate_json_against_schema(
            sample_suggested_searches,
            "suggested_searches.schema.json"
        )
        
        assert result.valid, f"Schema validation failed: {result.errors}"
    
    def test_suggested_searches_missing_priority(self, tmp_path):
        """Test that missing priority field is caught."""
        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "gap_count": 1,
                "suggestion_count": 1
            },
            "suggestions": [{
                "id": "search-001",
                "gap_id": "gap-001",
                "query": "test query here",
                # Missing: priority
                "rationale": "Test rationale for this search"
            }]
        }
        
        output_path = tmp_path / "missing_priority.json"
        with open(output_path, "w") as f:
            json.dump(data, f)
        
        result = validate_json_against_schema(
            output_path,
            "suggested_searches.schema.json"
        )
        
        assert not result.valid
        assert any("priority" in e for e in result.errors)
    
    # -------------------------------------------------------------------------
    # OQ-04: Suggested Searches Markdown Readability
    # -------------------------------------------------------------------------
    
    def test_suggested_searches_md_readable(self, sample_suggested_searches_md):
        """
        OQ-04: Validate suggested_searches.md is human-readable.
        """
        is_readable, issues = validate_markdown_readability(sample_suggested_searches_md)
        
        assert is_readable, f"Readability issues: {issues}"
    
    def test_suggested_searches_md_missing_structure(self, tmp_path):
        """Test that unstructured markdown is flagged."""
        content = """Some suggestions for searches.

neuromorphic power consumption
spiking neural networks
edge deployment energy
"""
        
        output_path = tmp_path / "unstructured.md"
        output_path.write_text(content)
        
        is_readable, issues = validate_markdown_readability(output_path)
        
        assert not is_readable
        assert len(issues) > 0
    
    # -------------------------------------------------------------------------
    # OQ-05: Optimized Search Plan Coherence
    # -------------------------------------------------------------------------
    
    def test_optimized_search_plan_schema_exists(self):
        """Verify schema definition file exists."""
        schema_path = SCHEMA_DIR / "optimized_search_plan.schema.json"
        assert schema_path.exists(), f"Schema file missing: {schema_path}"
    
    def test_optimized_search_plan_valid_schema(self, sample_optimized_search_plan):
        """Validate optimized_search_plan.json against schema."""
        result = validate_json_against_schema(
            sample_optimized_search_plan,
            "optimized_search_plan.schema.json"
        )
        
        assert result.valid, f"Schema validation failed: {result.errors}"
    
    def test_search_plan_coherence(self, sample_optimized_search_plan):
        """
        OQ-05: Validate search plan has coherent strategy.
        """
        with open(sample_optimized_search_plan) as f:
            data = json.load(f)
        
        is_coherent, issues = check_search_plan_coherence(data)
        
        assert is_coherent, f"Coherence issues: {issues}"
    
    def test_search_plan_circular_dependency(self, tmp_path):
        """Test that circular dependencies are detected."""
        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_searches": 2,
                "estimated_time_hours": 1.0
            },
            "strategy": {
                "approach": "priority_weighted",
                "priority_weights": {}
            },
            "phases": [
                {
                    "phase_id": 1,
                    "name": "Phase 1",
                    "depends_on": [2],  # Circular!
                    "searches": ["s1"]
                },
                {
                    "phase_id": 2,
                    "name": "Phase 2",
                    "depends_on": [1],  # Circular!
                    "searches": ["s2"]
                }
            ]
        }
        
        is_coherent, issues = check_search_plan_coherence(data)
        
        assert not is_coherent
        assert any("circular" in issue.lower() or "depends on later" in issue.lower() 
                   for issue in issues)


@pytest.mark.validation
@pytest.mark.recommendation
@pytest.mark.accuracy
class TestRecommendationAccuracy:
    """Test suite for recommendation accuracy validation (RA-01 through RA-05)."""
    
    # -------------------------------------------------------------------------
    # RA-01: Suggestion Relevance
    # -------------------------------------------------------------------------
    
    def test_suggestion_relevance_golden_dataset(
        self,
        sample_suggested_searches,
        golden_dataset_gaps
    ):
        """
        RA-01: Search suggestions should address known gaps.
        
        Target: ≥80% of suggestions should match golden dataset gaps.
        """
        with open(sample_suggested_searches) as f:
            data = json.load(f)
        
        suggestions = data.get("suggestions", [])
        gaps_addressed = {s.get("gap_id") for s in suggestions}
        
        # Check coverage of known gaps
        covered = gaps_addressed & golden_dataset_gaps
        coverage_rate = len(covered) / len(golden_dataset_gaps) if golden_dataset_gaps else 1.0
        
        # For this test, we check that suggestions reference valid gaps
        valid_references = sum(
            1 for s in suggestions 
            if s.get("gap_id") in golden_dataset_gaps
        )
        relevance_rate = valid_references / len(suggestions) if suggestions else 1.0
        
        assert relevance_rate >= 0.80, (
            f"Suggestion relevance {relevance_rate:.1%} < 80% threshold. "
            f"Valid refs: {valid_references}/{len(suggestions)}"
        )
    
    # -------------------------------------------------------------------------
    # RA-02: Priority Ranking Accuracy
    # -------------------------------------------------------------------------
    
    def test_priority_ranking_correlation(
        self,
        sample_suggested_searches,
        expected_priority_ranking
    ):
        """
        RA-02: Priority ranking should correlate with expert judgment.
        
        Target: Correlation coefficient ≥0.7
        """
        with open(sample_suggested_searches) as f:
            data = json.load(f)
        
        system_priorities = [
            (s.get("id"), s.get("priority", 999))
            for s in data.get("suggestions", [])
        ]
        
        result = calculate_priority_correlation(system_priorities, expected_priority_ranking)
        
        assert result.correlation_coefficient >= 0.70, (
            f"Priority correlation {result.correlation_coefficient:.2f} < 0.70 threshold. "
            f"Inversions: {result.inversions}"
        )
    
    # -------------------------------------------------------------------------
    # RA-03: Gap-to-Recommendation Traceability
    # -------------------------------------------------------------------------
    
    def test_gap_traceability_complete(
        self,
        sample_suggested_searches,
        golden_dataset_gaps
    ):
        """
        RA-03: Every gap should have at least one recommendation.
        
        Target: 100% coverage
        """
        with open(sample_suggested_searches) as f:
            data = json.load(f)
        
        suggestions = data.get("suggestions", [])
        
        # Use subset of gaps that should be covered
        expected_gaps = {"gap-001", "gap-002"}  # From sample data
        
        result = check_gap_traceability(suggestions, expected_gaps)
        
        assert result.all_gaps_covered, (
            f"Uncovered gaps: {result.uncovered_gaps}. "
            f"Coverage: {len(result.covered_gaps)}/{len(expected_gaps)}"
        )
    
    def test_no_orphaned_recommendations(self, sample_suggested_searches):
        """Recommendations should reference valid gaps."""
        with open(sample_suggested_searches) as f:
            data = json.load(f)
        
        suggestions = data.get("suggestions", [])
        
        # All gap_ids referenced in suggestions
        referenced_gaps = {s.get("gap_id") for s in suggestions if s.get("gap_id")}
        
        # Verify no empty gap references
        assert all(
            s.get("gap_id") for s in suggestions
        ), "Some suggestions missing gap_id"
    
    # -------------------------------------------------------------------------
    # RA-04: Recommendation Actionability
    # -------------------------------------------------------------------------
    
    def test_query_actionability(self, sample_suggested_searches):
        """
        RA-04: Recommendations should be parseable by search tools.
        
        Target: All queries should be valid search syntax.
        """
        with open(sample_suggested_searches) as f:
            data = json.load(f)
        
        queries = [s.get("query", "") for s in data.get("suggestions", [])]
        parseable_count, unparseable = check_query_actionability(queries)
        
        actionability_rate = parseable_count / len(queries) if queries else 1.0
        
        assert actionability_rate >= 0.95, (
            f"Actionability {actionability_rate:.1%} < 95%. "
            f"Unparseable queries: {unparseable}"
        )
    
    # -------------------------------------------------------------------------
    # RA-05: Recommendation Deduplication
    # -------------------------------------------------------------------------
    
    def test_no_duplicate_suggestions(self, sample_suggested_searches):
        """
        RA-05: No duplicate recommendations should appear.
        
        Target: 0 duplicates
        """
        with open(sample_suggested_searches) as f:
            data = json.load(f)
        
        suggestions = data.get("suggestions", [])
        duplicate_count, duplicates = check_deduplication(suggestions)
        
        assert duplicate_count == 0, (
            f"Found {duplicate_count} duplicate suggestions: {duplicates}"
        )
    
    def test_deduplication_detects_duplicates(self, tmp_path):
        """Verify duplicate detection works correctly."""
        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "gap_count": 1,
                "suggestion_count": 3
            },
            "suggestions": [
                {"id": "s1", "gap_id": "g1", "query": "neuromorphic computing", 
                 "priority": 1, "rationale": "Test"},
                {"id": "s2", "gap_id": "g1", "query": "Neuromorphic Computing",  # Duplicate!
                 "priority": 2, "rationale": "Test"},
                {"id": "s3", "gap_id": "g1", "query": "spiking neural networks",
                 "priority": 3, "rationale": "Test"}
            ]
        }
        
        output_path = tmp_path / "with_duplicates.json"
        with open(output_path, "w") as f:
            json.dump(data, f)
        
        with open(output_path) as f:
            loaded = json.load(f)
        
        duplicate_count, duplicates = check_deduplication(loaded.get("suggestions", []))
        
        assert duplicate_count == 1
        assert "neuromorphic computing" in duplicates


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.validation
@pytest.mark.recommendation
@pytest.mark.integration
class TestActualRecommendationOutputs:
    """Test actual recommendation outputs from pipeline runs."""
    
    @pytest.fixture
    def latest_review_dir(self) -> Optional[Path]:
        """Find the most recent review output directory."""
        reviews_dir = Path(__file__).parent.parent.parent.parent / "reviews"
        if not reviews_dir.exists():
            return None
        
        review_dirs = sorted(
            [d for d in reviews_dir.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        return review_dirs[0] if review_dirs else None
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent.parent / "reviews").exists(),
        reason="No reviews directory found"
    )
    def test_actual_suggested_searches_json(self, latest_review_dir):
        """Validate actual suggested_searches.json."""
        if latest_review_dir is None:
            pytest.skip("No review outputs found")
        
        file_path = latest_review_dir / "suggested_searches.json"
        if not file_path.exists():
            pytest.skip(f"No suggested_searches.json in {latest_review_dir}")
        
        result = validate_json_against_schema(
            file_path,
            "suggested_searches.schema.json"
        )
        
        assert result.valid, f"Validation failed: {result.errors}"
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent.parent / "reviews").exists(),
        reason="No reviews directory found"
    )
    def test_actual_suggested_searches_md(self, latest_review_dir):
        """Validate actual suggested_searches.md readability."""
        if latest_review_dir is None:
            pytest.skip("No review outputs found")
        
        file_path = latest_review_dir / "suggested_searches.md"
        if not file_path.exists():
            pytest.skip(f"No suggested_searches.md in {latest_review_dir}")
        
        is_readable, issues = validate_markdown_readability(file_path)
        
        assert is_readable, f"Readability issues: {issues}"
```

---

## Implementation Plan

### Hour 1-2: Schema Design
1. Analyze actual suggested_searches.json structure
2. Create JSON schemas for all recommendation files
3. Define validation rules for each field

### Hour 3-4: Core Test Implementation
1. Implement OQ-03, OQ-04, OQ-05 tests
2. Create markdown readability validator
3. Implement search plan coherence checker

### Hour 5-6: Accuracy Tests
1. Implement RA-01 (relevance) with golden dataset integration
2. Implement RA-02 (priority correlation) calculator
3. Implement RA-03 (traceability) checker

### Hour 7: Quality Tests
1. Implement RA-04 (actionability) query validator
2. Implement RA-05 (deduplication) checker
3. Create comprehensive fixtures

### Hour 8: Integration & Documentation
1. Add integration tests for actual outputs
2. Document validation thresholds
3. Update pytest markers
4. Verify all tests pass

---

## Testing Instructions

```bash
# Run all recommendation quality tests
pytest tests/validation/outputs/test_recommendation_quality.py -v -m recommendation

# Run only schema validation tests
pytest tests/validation/outputs/test_recommendation_quality.py -v -k "schema"

# Run accuracy tests
pytest tests/validation/outputs/test_recommendation_quality.py -v -m accuracy

# Run integration tests
pytest tests/validation/outputs/test_recommendation_quality.py -v -m integration
```

---

## Dependencies

### Python Packages
- `jsonschema>=4.0.0` - JSON Schema validation
- `pytest>=7.0.0` - Test framework

### Internal Dependencies
- `tests/validation/outputs/test_output_schemas.py` - Shared validation functions
- `tests/golden_dataset/` - Golden dataset with known gaps
- `reviews/` - Pipeline output directory

---

## Acceptance Criteria

- [ ] OQ-03: suggested_searches.json passes schema validation
- [ ] OQ-04: suggested_searches.md passes readability check
- [ ] OQ-05: optimized_search_plan.json has coherent strategy
- [ ] RA-01: Suggestion relevance ≥80% against golden dataset
- [ ] RA-02: Priority correlation ≥0.70 with expert ranking
- [ ] RA-03: 100% gap-to-recommendation traceability
- [ ] RA-04: All queries are actionable/parseable
- [ ] RA-05: Zero duplicate suggestions
- [ ] Integration tests validate actual outputs
- [ ] Tests run in < 10 seconds

---

## Notes

- Priority correlation uses Spearman-like rank comparison
- Query actionability allows flexible search syntax patterns
- Deduplication is case-insensitive
- Golden dataset integration required for RA-01, RA-02
- Traceability test verifies bidirectional linking
