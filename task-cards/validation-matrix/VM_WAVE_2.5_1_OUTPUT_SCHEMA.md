# Task Card: Core Output Schema Validation

**Task ID:** VM-W2.5-1  
**Wave:** 2.5 (Output Quality Validation)  
**Priority:** HIGH  
**Estimated Effort:** 6 hours  
**Status:** Not Started  
**Dependencies:** VM-W2-1  
**Blocks:** VM-W2.5-2, VM-W4-1  
**Validation IDs:** OQ-01, OQ-02

---

## Objective

Validate that core pipeline outputs conform to expected schemas and contain all required sections. This ensures user-facing deliverables are structurally correct and complete.

## Background

The pipeline generates several critical output files that users consume directly:
- **gap_analysis_report.json** - Machine-readable gap analysis with structured findings
- **executive_summary.md** - Human-readable summary for stakeholders

These outputs were identified as lacking validation in the third-party Output Gap Analysis, which found 75% of user-facing outputs were not validated.

## Success Criteria

- [ ] OQ-01: gap_analysis_report.json passes JSON schema validation
- [ ] OQ-02: executive_summary.md contains all required sections
- [ ] Schema definitions created and documented
- [ ] Validation errors provide actionable feedback

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| OQ-01 | Gap Analysis Schema | gap_analysis_report.json | Valid JSON matching schema | All required fields present, correct types |
| OQ-02 | Executive Summary Completeness | executive_summary.md | All sections present | Contains: Overview, Key Findings, Gaps, Recommendations, Next Steps |

---

## Deliverables

### 1. JSON Schema Definitions

**File:** `tests/validation/outputs/schemas/gap_analysis_report.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "gap_analysis_report.schema.json",
  "title": "Gap Analysis Report",
  "description": "Schema for pipeline gap analysis output",
  "type": "object",
  "required": ["metadata", "summary", "gaps", "coverage"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["generated_at", "pipeline_version", "paper_count"],
      "properties": {
        "generated_at": {
          "type": "string",
          "format": "date-time"
        },
        "pipeline_version": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+\\.\\d+$"
        },
        "paper_count": {
          "type": "integer",
          "minimum": 0
        },
        "domain": {
          "type": "string"
        },
        "run_mode": {
          "type": "string",
          "enum": ["fresh", "incremental"]
        }
      }
    },
    "summary": {
      "type": "object",
      "required": ["total_gaps", "critical_gaps", "coverage_percentage"],
      "properties": {
        "total_gaps": {
          "type": "integer",
          "minimum": 0
        },
        "critical_gaps": {
          "type": "integer",
          "minimum": 0
        },
        "coverage_percentage": {
          "type": "number",
          "minimum": 0,
          "maximum": 100
        }
      }
    },
    "gaps": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/gap"
      }
    },
    "coverage": {
      "type": "object",
      "required": ["pillars"],
      "properties": {
        "pillars": {
          "type": "object",
          "additionalProperties": {
            "$ref": "#/definitions/pillar_coverage"
          }
        }
      }
    }
  },
  "definitions": {
    "gap": {
      "type": "object",
      "required": ["id", "pillar", "description", "severity"],
      "properties": {
        "id": {
          "type": "string"
        },
        "pillar": {
          "type": "string"
        },
        "description": {
          "type": "string",
          "minLength": 10
        },
        "severity": {
          "type": "string",
          "enum": ["critical", "high", "medium", "low"]
        },
        "suggested_searches": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    },
    "pillar_coverage": {
      "type": "object",
      "required": ["coverage_percent", "claim_count"],
      "properties": {
        "coverage_percent": {
          "type": "number",
          "minimum": 0,
          "maximum": 100
        },
        "claim_count": {
          "type": "integer",
          "minimum": 0
        },
        "approved_claims": {
          "type": "integer",
          "minimum": 0
        }
      }
    }
  }
}
```

### 2. Test Implementation

**File:** `tests/validation/outputs/test_output_schemas.py`

```python
"""
Core Output Schema Validation Tests

Validates OQ-01 and OQ-02 from the validation matrix.
Ensures user-facing outputs conform to expected schemas and contain required content.
"""

import pytest
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from datetime import datetime

import jsonschema
from jsonschema import Draft7Validator, ValidationError


# =============================================================================
# Configuration
# =============================================================================

SCHEMA_DIR = Path(__file__).parent / "schemas"
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "reviews"

REQUIRED_EXECUTIVE_SUMMARY_SECTIONS = [
    "overview",
    "key findings", 
    "gaps",
    "recommendations",
    "next steps"
]

SECTION_HEADER_PATTERNS = {
    "overview": r"(?i)^#+\s*(executive\s+)?overview|^#+\s*summary",
    "key findings": r"(?i)^#+\s*key\s+(findings?|results?)",
    "gaps": r"(?i)^#+\s*(identified\s+)?gaps?|^#+\s*coverage\s+gaps?",
    "recommendations": r"(?i)^#+\s*recommendations?",
    "next steps": r"(?i)^#+\s*next\s+steps?|^#+\s*(action\s+)?items?"
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SchemaValidationResult:
    """Result of JSON schema validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    schema_id: str
    file_path: str
    
    def __bool__(self) -> bool:
        return self.valid


@dataclass  
class SectionValidationResult:
    """Result of markdown section validation."""
    valid: bool
    found_sections: Set[str]
    missing_sections: Set[str]
    file_path: str
    
    def __bool__(self) -> bool:
        return self.valid


# =============================================================================
# Schema Loading
# =============================================================================

def load_schema(schema_name: str) -> Dict:
    """Load a JSON schema from the schemas directory."""
    schema_path = SCHEMA_DIR / schema_name
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    
    with open(schema_path) as f:
        return json.load(f)


def get_validator(schema_name: str) -> Draft7Validator:
    """Get a JSON schema validator instance."""
    schema = load_schema(schema_name)
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema)


# =============================================================================
# Validation Functions
# =============================================================================

def validate_json_against_schema(
    file_path: Path,
    schema_name: str
) -> SchemaValidationResult:
    """
    Validate a JSON file against a schema.
    
    Args:
        file_path: Path to JSON file to validate
        schema_name: Name of schema file in schemas directory
        
    Returns:
        SchemaValidationResult with validation details
    """
    errors = []
    warnings = []
    
    # Check file exists
    if not file_path.exists():
        return SchemaValidationResult(
            valid=False,
            errors=[f"File not found: {file_path}"],
            warnings=[],
            schema_id=schema_name,
            file_path=str(file_path)
        )
    
    # Load and parse JSON
    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return SchemaValidationResult(
            valid=False,
            errors=[f"Invalid JSON: {e}"],
            warnings=[],
            schema_id=schema_name,
            file_path=str(file_path)
        )
    
    # Validate against schema
    try:
        validator = get_validator(schema_name)
        validation_errors = list(validator.iter_errors(data))
        
        for error in validation_errors:
            path = ".".join(str(p) for p in error.absolute_path)
            if path:
                errors.append(f"{path}: {error.message}")
            else:
                errors.append(error.message)
                
    except FileNotFoundError as e:
        errors.append(str(e))
    
    return SchemaValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        schema_id=schema_name,
        file_path=str(file_path)
    )


def validate_markdown_sections(
    file_path: Path,
    required_sections: List[str],
    section_patterns: Dict[str, str]
) -> SectionValidationResult:
    """
    Validate that a markdown file contains required sections.
    
    Args:
        file_path: Path to markdown file
        required_sections: List of section names that must be present
        section_patterns: Regex patterns for each section header
        
    Returns:
        SectionValidationResult with validation details
    """
    if not file_path.exists():
        return SectionValidationResult(
            valid=False,
            found_sections=set(),
            missing_sections=set(required_sections),
            file_path=str(file_path)
        )
    
    content = file_path.read_text()
    lines = content.split("\n")
    
    found_sections = set()
    
    for line in lines:
        for section_name, pattern in section_patterns.items():
            if re.match(pattern, line.strip()):
                found_sections.add(section_name)
    
    missing_sections = set(required_sections) - found_sections
    
    return SectionValidationResult(
        valid=len(missing_sections) == 0,
        found_sections=found_sections,
        missing_sections=missing_sections,
        file_path=str(file_path)
    )


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_gap_analysis_report(tmp_path) -> Path:
    """Create a sample gap_analysis_report.json for testing."""
    report = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "pipeline_version": "1.0.0",
            "paper_count": 50,
            "domain": "neuromorphic_computing",
            "run_mode": "fresh"
        },
        "summary": {
            "total_gaps": 5,
            "critical_gaps": 2,
            "coverage_percentage": 75.5
        },
        "gaps": [
            {
                "id": "gap-001",
                "pillar": "P4_Power_Efficiency",
                "description": "Limited evidence for power consumption in edge deployments",
                "severity": "critical",
                "suggested_searches": [
                    "neuromorphic power consumption edge",
                    "spiking neural network energy efficiency"
                ]
            }
        ],
        "coverage": {
            "pillars": {
                "P1_Hardware_Architecture": {
                    "coverage_percent": 85.0,
                    "claim_count": 45,
                    "approved_claims": 38
                },
                "P4_Power_Efficiency": {
                    "coverage_percent": 45.0,
                    "claim_count": 12,
                    "approved_claims": 5
                }
            }
        }
    }
    
    output_path = tmp_path / "gap_analysis_report.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    
    return output_path


@pytest.fixture
def sample_executive_summary(tmp_path) -> Path:
    """Create a sample executive_summary.md for testing."""
    content = """# Literature Review: Neuromorphic Computing

## Executive Overview

This report summarizes the literature review findings for neuromorphic computing research.
A total of 50 papers were analyzed covering hardware architectures, learning algorithms,
and power efficiency.

## Key Findings

1. **Hardware maturity is high** - Strong evidence for viable architectures
2. **Learning algorithms need work** - Gap in on-chip learning validation
3. **Power efficiency claims vary** - Need more standardized benchmarks

## Identified Gaps

| Gap ID | Pillar | Severity | Description |
|--------|--------|----------|-------------|
| GAP-001 | P4 | Critical | Limited edge deployment power data |
| GAP-002 | P3 | High | On-chip learning scalability unclear |

## Recommendations

1. Prioritize power efficiency benchmarking studies
2. Seek on-chip learning implementation papers
3. Cross-validate hardware claims with independent sources

## Next Steps

- [ ] Execute suggested searches for GAP-001
- [ ] Schedule domain expert review
- [ ] Update pillar definitions based on findings
"""
    
    output_path = tmp_path / "executive_summary.md"
    output_path.write_text(content)
    
    return output_path


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.validation
@pytest.mark.output_quality
class TestOutputSchemaValidation:
    """Test suite for output schema validation (OQ-01, OQ-02)."""
    
    # -------------------------------------------------------------------------
    # OQ-01: Gap Analysis Report Schema Validation
    # -------------------------------------------------------------------------
    
    @pytest.mark.parametrize("schema_name", [
        "gap_analysis_report.schema.json"
    ])
    def test_schema_files_exist(self, schema_name):
        """Verify schema definition files exist."""
        schema_path = SCHEMA_DIR / schema_name
        assert schema_path.exists(), f"Schema file missing: {schema_path}"
    
    def test_gap_analysis_report_valid_schema(self, sample_gap_analysis_report):
        """
        OQ-01: Validate gap_analysis_report.json against schema.
        
        Verifies:
        - JSON is valid
        - All required fields present
        - Field types are correct
        - Enum values are valid
        """
        result = validate_json_against_schema(
            sample_gap_analysis_report,
            "gap_analysis_report.schema.json"
        )
        
        assert result.valid, f"Schema validation failed: {result.errors}"
        assert len(result.errors) == 0
    
    def test_gap_analysis_report_missing_required_field(self, tmp_path):
        """Test that missing required fields are caught."""
        # Create report missing 'summary' field
        incomplete_report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "pipeline_version": "1.0.0",
                "paper_count": 50
            },
            "gaps": [],
            "coverage": {"pillars": {}}
            # Missing: "summary"
        }
        
        output_path = tmp_path / "incomplete_report.json"
        with open(output_path, "w") as f:
            json.dump(incomplete_report, f)
        
        result = validate_json_against_schema(
            output_path,
            "gap_analysis_report.schema.json"
        )
        
        assert not result.valid
        assert any("summary" in error for error in result.errors)
    
    def test_gap_analysis_report_invalid_severity(self, tmp_path):
        """Test that invalid enum values are caught."""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "pipeline_version": "1.0.0",
                "paper_count": 50
            },
            "summary": {
                "total_gaps": 1,
                "critical_gaps": 0,
                "coverage_percentage": 80.0
            },
            "gaps": [
                {
                    "id": "gap-001",
                    "pillar": "P1",
                    "description": "Test gap description here",
                    "severity": "super-critical"  # Invalid enum value
                }
            ],
            "coverage": {"pillars": {}}
        }
        
        output_path = tmp_path / "bad_severity_report.json"
        with open(output_path, "w") as f:
            json.dump(report, f)
        
        result = validate_json_against_schema(
            output_path,
            "gap_analysis_report.schema.json"
        )
        
        assert not result.valid
        assert any("severity" in error.lower() or "enum" in error.lower() 
                   for error in result.errors)
    
    # -------------------------------------------------------------------------
    # OQ-02: Executive Summary Completeness
    # -------------------------------------------------------------------------
    
    def test_executive_summary_all_sections_present(self, sample_executive_summary):
        """
        OQ-02: Validate executive_summary.md contains all required sections.
        
        Required sections:
        - Overview
        - Key Findings
        - Gaps
        - Recommendations
        - Next Steps
        """
        result = validate_markdown_sections(
            sample_executive_summary,
            REQUIRED_EXECUTIVE_SUMMARY_SECTIONS,
            SECTION_HEADER_PATTERNS
        )
        
        assert result.valid, f"Missing sections: {result.missing_sections}"
        assert len(result.missing_sections) == 0
        assert "overview" in result.found_sections
        assert "key findings" in result.found_sections
        assert "gaps" in result.found_sections
        assert "recommendations" in result.found_sections
        assert "next steps" in result.found_sections
    
    def test_executive_summary_missing_section(self, tmp_path):
        """Test that missing sections are detected."""
        content = """# Literature Review

## Overview
Brief overview here.

## Key Findings
- Finding 1
- Finding 2

## Recommendations
1. Do this
2. Do that
"""
        # Missing: Gaps, Next Steps
        
        output_path = tmp_path / "incomplete_summary.md"
        output_path.write_text(content)
        
        result = validate_markdown_sections(
            output_path,
            REQUIRED_EXECUTIVE_SUMMARY_SECTIONS,
            SECTION_HEADER_PATTERNS
        )
        
        assert not result.valid
        assert "gaps" in result.missing_sections
        assert "next steps" in result.missing_sections
    
    def test_executive_summary_alternate_headers(self, tmp_path):
        """Test that alternate header formats are recognized."""
        content = """# Review Report

## Summary
Overview content here.

### Key Results
Results listed here.

## Coverage Gaps
Gaps identified.

## Recommendations
Actions to take.

## Action Items
Things to do next.
"""
        
        output_path = tmp_path / "alt_headers.md"
        output_path.write_text(content)
        
        result = validate_markdown_sections(
            output_path,
            REQUIRED_EXECUTIVE_SUMMARY_SECTIONS,
            SECTION_HEADER_PATTERNS
        )
        
        # Should recognize alternate headers
        assert "overview" in result.found_sections  # "Summary" matches
        assert "key findings" in result.found_sections  # "Key Results" matches
        assert "gaps" in result.found_sections  # "Coverage Gaps" matches
        assert "next steps" in result.found_sections  # "Action Items" matches


# =============================================================================
# Integration with Actual Outputs
# =============================================================================

@pytest.mark.validation
@pytest.mark.output_quality
@pytest.mark.integration
class TestActualOutputValidation:
    """Test actual pipeline outputs (requires prior pipeline run)."""
    
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
    def test_actual_gap_analysis_report(self, latest_review_dir):
        """Validate actual gap_analysis_report.json from last run."""
        if latest_review_dir is None:
            pytest.skip("No review outputs found")
        
        report_path = latest_review_dir / "gap_analysis_report.json"
        if not report_path.exists():
            pytest.skip(f"No gap_analysis_report.json in {latest_review_dir}")
        
        result = validate_json_against_schema(
            report_path,
            "gap_analysis_report.schema.json"
        )
        
        assert result.valid, f"Actual report failed validation: {result.errors}"
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent.parent / "reviews").exists(),
        reason="No reviews directory found"
    )
    def test_actual_executive_summary(self, latest_review_dir):
        """Validate actual executive_summary.md from last run."""
        if latest_review_dir is None:
            pytest.skip("No review outputs found")
        
        summary_path = latest_review_dir / "executive_summary.md"
        if not summary_path.exists():
            pytest.skip(f"No executive_summary.md in {latest_review_dir}")
        
        result = validate_markdown_sections(
            summary_path,
            REQUIRED_EXECUTIVE_SUMMARY_SECTIONS,
            SECTION_HEADER_PATTERNS
        )
        
        assert result.valid, f"Missing sections: {result.missing_sections}"
```

---

## Implementation Plan

### Hour 1-2: Schema Design
1. Analyze actual gap_analysis_report.json structure from existing runs
2. Create comprehensive JSON schema with all required/optional fields
3. Document field semantics and validation rules

### Hour 3-4: Test Implementation
1. Implement schema validation functions
2. Create markdown section validators with flexible pattern matching
3. Write unit tests with sample fixtures

### Hour 5: Integration Tests
1. Add tests for actual pipeline outputs
2. Create validation result reporting
3. Handle edge cases (empty files, malformed JSON)

### Hour 6: Documentation & Cleanup
1. Document validation error messages
2. Add schema documentation
3. Update pytest markers
4. Verify all OQ-01, OQ-02 tests pass

---

## Testing Instructions

```bash
# Run all output schema tests
pytest tests/validation/outputs/test_output_schemas.py -v -m output_quality

# Run only unit tests (with fixtures)
pytest tests/validation/outputs/test_output_schemas.py -v -k "not actual"

# Run integration tests against real outputs
pytest tests/validation/outputs/test_output_schemas.py -v -k "actual"

# Validate specific files manually
python -c "
from tests.validation.outputs.test_output_schemas import validate_json_against_schema
from pathlib import Path
result = validate_json_against_schema(
    Path('reviews/latest/gap_analysis_report.json'),
    'gap_analysis_report.schema.json'
)
print(f'Valid: {result.valid}')
for error in result.errors:
    print(f'  - {error}')
"
```

---

## Dependencies

### Python Packages
- `jsonschema>=4.0.0` - JSON Schema validation
- `pytest>=7.0.0` - Test framework

### Internal Dependencies
- `tests/validation/base.py` - Base validation classes
- `reviews/` - Pipeline output directory

---

## Acceptance Criteria

- [ ] JSON schema for gap_analysis_report.json created and documented
- [ ] Markdown section patterns handle common header variations
- [ ] OQ-01: gap_analysis_report.json passes schema validation
- [ ] OQ-02: executive_summary.md contains all 5 required sections
- [ ] Integration tests validate actual pipeline outputs
- [ ] Clear error messages for validation failures
- [ ] Tests run in < 5 seconds

---

## Notes

- Schema should be permissive enough to handle format evolution
- Section pattern matching uses case-insensitive regex
- Integration tests skip gracefully if no outputs exist
- Consider adding schema versioning for future compatibility
