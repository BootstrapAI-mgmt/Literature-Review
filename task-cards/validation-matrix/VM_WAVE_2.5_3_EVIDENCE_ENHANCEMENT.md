# Task Card: Evidence Enhancement Validation

**Task ID:** VM-W2.5-3  
**Wave:** 2.5 (Output Quality Validation)  
**Priority:** MEDIUM  
**Estimated Effort:** 6 hours  
**Status:** Not Started  
**Dependencies:** VM-W2-1  
**Blocks:** VM-W4-1  
**Validation IDs:** OQ-06, OQ-07, OQ-08, OQ-09, OQ-10

---

## Objective

Validate that evidence enhancement outputs (proof chains, sufficiency matrices, triangulation, decay calculations) are complete, accurate, and internally consistent. These outputs provide the evidentiary foundation for pipeline decisions.

## Background

The pipeline generates several evidence-focused outputs that document the reasoning chain:
- **proof_chain.json** - Links approved claims to supporting evidence
- **sufficiency_matrix.json** - Coverage analysis across all pillars
- **triangulation.json** - Cross-validation between multiple sources
- **evidence_decay.json** - Temporal weighting of evidence freshness

These files are critical for auditability and decision transparency. The third-party Output Gap Analysis identified that evidence chain integrity was not being validated.

## Success Criteria

- [ ] OQ-06: proof_chain.json links all approved claims to evidence
- [ ] OQ-07: sufficiency_matrix.json covers all defined pillars
- [ ] OQ-08: triangulation.json cross-references are accurate
- [ ] OQ-09: evidence_decay.json temporal weights are correct
- [ ] OQ-10: No orphaned references across output files
- [ ] Evidence chain integrity verified end-to-end

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| OQ-06 | Proof Chain Completeness | proof_chain.json + approved claims | All claims linked | 100% approved claims have evidence links |
| OQ-07 | Sufficiency Matrix Coverage | sufficiency_matrix.json + pillars | All pillars represented | Every pillar has coverage entry |
| OQ-08 | Triangulation Accuracy | triangulation.json | Valid cross-refs | All source IDs exist, scores consistent |
| OQ-09 | Evidence Decay Correctness | evidence_decay.json | Valid temporal weights | Weights follow decay formula, dates valid |
| OQ-10 | Output Consistency | All output files | No orphans | All IDs referenced exist in source files |

---

## Deliverables

### 1. JSON Schema Definitions

**File:** `tests/validation/outputs/schemas/proof_chain.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "proof_chain.schema.json",
  "title": "Proof Chain",
  "description": "Schema for evidence proof chain linking claims to sources",
  "type": "object",
  "required": ["metadata", "chains"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["generated_at", "total_claims", "total_sources"],
      "properties": {
        "generated_at": {
          "type": "string",
          "format": "date-time"
        },
        "total_claims": {
          "type": "integer",
          "minimum": 0
        },
        "total_sources": {
          "type": "integer",
          "minimum": 0
        },
        "pipeline_version": {
          "type": "string"
        }
      }
    },
    "chains": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/chain"
      }
    }
  },
  "definitions": {
    "chain": {
      "type": "object",
      "required": ["claim_id", "claim_text", "verdict", "evidence_links"],
      "properties": {
        "claim_id": {
          "type": "string"
        },
        "claim_text": {
          "type": "string",
          "minLength": 10
        },
        "verdict": {
          "type": "string",
          "enum": ["approved", "rejected", "pending", "appealed"]
        },
        "pillar": {
          "type": "string"
        },
        "composite_score": {
          "type": "number",
          "minimum": 0,
          "maximum": 5
        },
        "evidence_links": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/evidence_link"
          }
        }
      }
    },
    "evidence_link": {
      "type": "object",
      "required": ["source_id", "relevance_score"],
      "properties": {
        "source_id": {
          "type": "string"
        },
        "paper_title": {
          "type": "string"
        },
        "excerpt": {
          "type": "string"
        },
        "page_number": {
          "type": "integer",
          "minimum": 1
        },
        "relevance_score": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "contribution": {
          "type": "string",
          "enum": ["primary", "supporting", "corroborating"]
        }
      }
    }
  }
}
```

**File:** `tests/validation/outputs/schemas/sufficiency_matrix.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "sufficiency_matrix.schema.json",
  "title": "Sufficiency Matrix",
  "description": "Schema for pillar coverage sufficiency analysis",
  "type": "object",
  "required": ["metadata", "pillars", "overall_sufficiency"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["generated_at", "pillar_count"],
      "properties": {
        "generated_at": {
          "type": "string",
          "format": "date-time"
        },
        "pillar_count": {
          "type": "integer",
          "minimum": 1
        },
        "threshold_config": {
          "type": "object",
          "properties": {
            "minimum_claims_per_pillar": {"type": "integer"},
            "minimum_coverage_percent": {"type": "number"}
          }
        }
      }
    },
    "pillars": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/definitions/pillar_sufficiency"
      }
    },
    "overall_sufficiency": {
      "type": "object",
      "required": ["is_sufficient", "coverage_percent"],
      "properties": {
        "is_sufficient": {"type": "boolean"},
        "coverage_percent": {"type": "number", "minimum": 0, "maximum": 100},
        "gaps_identified": {"type": "integer", "minimum": 0}
      }
    }
  },
  "definitions": {
    "pillar_sufficiency": {
      "type": "object",
      "required": ["pillar_id", "name", "is_sufficient", "claim_count", "coverage_percent"],
      "properties": {
        "pillar_id": {"type": "string"},
        "name": {"type": "string"},
        "is_sufficient": {"type": "boolean"},
        "claim_count": {"type": "integer", "minimum": 0},
        "approved_claims": {"type": "integer", "minimum": 0},
        "coverage_percent": {"type": "number", "minimum": 0, "maximum": 100},
        "strength_avg": {"type": "number", "minimum": 0, "maximum": 5},
        "gaps": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    }
  }
}
```

**File:** `tests/validation/outputs/schemas/triangulation.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "triangulation.schema.json",
  "title": "Evidence Triangulation",
  "description": "Schema for cross-source evidence validation",
  "type": "object",
  "required": ["metadata", "triangulations"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["generated_at", "total_triangulations"],
      "properties": {
        "generated_at": {"type": "string", "format": "date-time"},
        "total_triangulations": {"type": "integer", "minimum": 0},
        "min_sources_required": {"type": "integer", "minimum": 2}
      }
    },
    "triangulations": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/triangulation_entry"
      }
    }
  },
  "definitions": {
    "triangulation_entry": {
      "type": "object",
      "required": ["claim_id", "source_count", "sources", "confidence_boost"],
      "properties": {
        "claim_id": {"type": "string"},
        "source_count": {"type": "integer", "minimum": 2},
        "sources": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["source_id", "agreement_score"],
            "properties": {
              "source_id": {"type": "string"},
              "agreement_score": {"type": "number", "minimum": 0, "maximum": 1}
            }
          },
          "minItems": 2
        },
        "confidence_boost": {"type": "number", "minimum": 0},
        "triangulation_type": {
          "type": "string",
          "enum": ["full_agreement", "partial_agreement", "complementary"]
        }
      }
    }
  }
}
```

**File:** `tests/validation/outputs/schemas/evidence_decay.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "evidence_decay.schema.json",
  "title": "Evidence Decay",
  "description": "Schema for temporal evidence weighting",
  "type": "object",
  "required": ["metadata", "decay_config", "entries"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["generated_at", "reference_date"],
      "properties": {
        "generated_at": {"type": "string", "format": "date-time"},
        "reference_date": {"type": "string", "format": "date"},
        "total_entries": {"type": "integer", "minimum": 0}
      }
    },
    "decay_config": {
      "type": "object",
      "required": ["decay_model", "half_life_years"],
      "properties": {
        "decay_model": {
          "type": "string",
          "enum": ["exponential", "linear", "step", "none"]
        },
        "half_life_years": {"type": "number", "minimum": 0.5},
        "minimum_weight": {"type": "number", "minimum": 0, "maximum": 1},
        "cutoff_years": {"type": "number", "minimum": 1}
      }
    },
    "entries": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/decay_entry"
      }
    }
  },
  "definitions": {
    "decay_entry": {
      "type": "object",
      "required": ["source_id", "publication_date", "age_years", "decay_weight"],
      "properties": {
        "source_id": {"type": "string"},
        "publication_date": {"type": "string", "format": "date"},
        "age_years": {"type": "number", "minimum": 0},
        "decay_weight": {"type": "number", "minimum": 0, "maximum": 1},
        "original_score": {"type": "number"},
        "weighted_score": {"type": "number"}
      }
    }
  }
}
```

### 2. Test Implementation

**File:** `tests/validation/outputs/test_evidence_outputs.py`

```python
"""
Evidence Enhancement Output Validation Tests

Validates OQ-06 through OQ-10 from the validation matrix.
Ensures evidence outputs are complete, accurate, and internally consistent.
"""

import pytest
import json
import math
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from collections import defaultdict

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

# Default decay parameters (should match pipeline config)
DEFAULT_DECAY_CONFIG = {
    "half_life_years": 5.0,
    "minimum_weight": 0.1,
    "decay_model": "exponential"
}

# Tolerance for floating point comparisons
DECAY_WEIGHT_TOLERANCE = 0.05


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CompletenessResult:
    """Result of completeness check."""
    complete: bool
    total_expected: int
    total_found: int
    missing: List[str]
    coverage_percent: float
    
    def __bool__(self) -> bool:
        return self.complete


@dataclass
class ConsistencyResult:
    """Result of cross-file consistency check."""
    consistent: bool
    orphaned_references: Dict[str, List[str]]  # file -> list of orphaned IDs
    missing_targets: Dict[str, List[str]]  # file -> list of missing target IDs
    total_issues: int
    
    def __bool__(self) -> bool:
        return self.consistent


@dataclass
class DecayValidationResult:
    """Result of decay weight validation."""
    valid: bool
    total_entries: int
    invalid_entries: List[Dict]
    max_deviation: float
    avg_deviation: float


# =============================================================================
# Validation Functions
# =============================================================================

def check_proof_chain_completeness(
    proof_chain_data: Dict,
    approved_claim_ids: Set[str]
) -> CompletenessResult:
    """
    OQ-06: Check that all approved claims have evidence links.
    
    Args:
        proof_chain_data: Parsed proof_chain.json
        approved_claim_ids: Set of claim IDs that were approved
        
    Returns:
        CompletenessResult with coverage details
    """
    chains = proof_chain_data.get("chains", [])
    
    # Get claim IDs that have chains
    chained_claims = set()
    for chain in chains:
        if chain.get("verdict") == "approved":
            claim_id = chain.get("claim_id")
            evidence_links = chain.get("evidence_links", [])
            if claim_id and len(evidence_links) > 0:
                chained_claims.add(claim_id)
    
    # Find missing claims
    missing = list(approved_claim_ids - chained_claims)
    coverage = len(chained_claims) / len(approved_claim_ids) if approved_claim_ids else 1.0
    
    return CompletenessResult(
        complete=len(missing) == 0,
        total_expected=len(approved_claim_ids),
        total_found=len(chained_claims),
        missing=missing,
        coverage_percent=coverage * 100
    )


def check_sufficiency_matrix_coverage(
    sufficiency_data: Dict,
    defined_pillars: Set[str]
) -> CompletenessResult:
    """
    OQ-07: Check that all defined pillars have coverage entries.
    
    Args:
        sufficiency_data: Parsed sufficiency_matrix.json
        defined_pillars: Set of pillar IDs from pillar_definitions.json
        
    Returns:
        CompletenessResult with coverage details
    """
    pillars_in_matrix = set(sufficiency_data.get("pillars", {}).keys())
    
    missing = list(defined_pillars - pillars_in_matrix)
    coverage = len(pillars_in_matrix & defined_pillars) / len(defined_pillars) if defined_pillars else 1.0
    
    return CompletenessResult(
        complete=len(missing) == 0,
        total_expected=len(defined_pillars),
        total_found=len(pillars_in_matrix & defined_pillars),
        missing=missing,
        coverage_percent=coverage * 100
    )


def check_triangulation_accuracy(
    triangulation_data: Dict,
    valid_source_ids: Set[str],
    valid_claim_ids: Set[str]
) -> Tuple[bool, List[str]]:
    """
    OQ-08: Check that triangulation cross-references are valid.
    
    Validates:
    - All source IDs exist in the source set
    - All claim IDs exist in the claim set
    - Agreement scores are consistent (between 0-1)
    - Source counts match actual sources listed
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    triangulations = triangulation_data.get("triangulations", [])
    
    for tri in triangulations:
        claim_id = tri.get("claim_id")
        sources = tri.get("sources", [])
        source_count = tri.get("source_count")
        
        # Check claim exists
        if claim_id and claim_id not in valid_claim_ids:
            issues.append(f"Triangulation references non-existent claim: {claim_id}")
        
        # Check source count matches
        if source_count != len(sources):
            issues.append(
                f"Claim {claim_id}: source_count ({source_count}) != "
                f"actual sources ({len(sources)})"
            )
        
        # Check each source
        for source in sources:
            source_id = source.get("source_id")
            agreement = source.get("agreement_score")
            
            if source_id and source_id not in valid_source_ids:
                issues.append(
                    f"Claim {claim_id}: references non-existent source {source_id}"
                )
            
            if agreement is not None and not (0 <= agreement <= 1):
                issues.append(
                    f"Claim {claim_id}: invalid agreement score {agreement}"
                )
    
    return len(issues) == 0, issues


def calculate_expected_decay_weight(
    publication_date: date,
    reference_date: date,
    half_life_years: float = 5.0,
    minimum_weight: float = 0.1,
    decay_model: str = "exponential"
) -> float:
    """
    Calculate expected decay weight using the pipeline's formula.
    
    Exponential decay: weight = max(min_weight, 0.5 ^ (age / half_life))
    """
    age_days = (reference_date - publication_date).days
    age_years = age_days / 365.25
    
    if decay_model == "exponential":
        weight = math.pow(0.5, age_years / half_life_years)
        return max(minimum_weight, weight)
    elif decay_model == "linear":
        weight = 1.0 - (age_years / (half_life_years * 2))
        return max(minimum_weight, weight)
    elif decay_model == "none":
        return 1.0
    else:
        return 1.0


def validate_decay_weights(decay_data: Dict) -> DecayValidationResult:
    """
    OQ-09: Validate that decay weights follow the decay formula.
    
    Returns:
        DecayValidationResult with validation details
    """
    config = decay_data.get("decay_config", DEFAULT_DECAY_CONFIG)
    entries = decay_data.get("entries", [])
    metadata = decay_data.get("metadata", {})
    
    half_life = config.get("half_life_years", 5.0)
    min_weight = config.get("minimum_weight", 0.1)
    decay_model = config.get("decay_model", "exponential")
    
    # Parse reference date
    ref_date_str = metadata.get("reference_date")
    if ref_date_str:
        reference_date = date.fromisoformat(ref_date_str)
    else:
        reference_date = date.today()
    
    invalid_entries = []
    deviations = []
    
    for entry in entries:
        pub_date_str = entry.get("publication_date")
        reported_weight = entry.get("decay_weight")
        
        if not pub_date_str or reported_weight is None:
            continue
        
        try:
            pub_date = date.fromisoformat(pub_date_str)
        except ValueError:
            invalid_entries.append({
                "source_id": entry.get("source_id"),
                "issue": f"Invalid date format: {pub_date_str}"
            })
            continue
        
        expected_weight = calculate_expected_decay_weight(
            pub_date, reference_date, half_life, min_weight, decay_model
        )
        
        deviation = abs(reported_weight - expected_weight)
        deviations.append(deviation)
        
        if deviation > DECAY_WEIGHT_TOLERANCE:
            invalid_entries.append({
                "source_id": entry.get("source_id"),
                "publication_date": pub_date_str,
                "reported_weight": reported_weight,
                "expected_weight": expected_weight,
                "deviation": deviation
            })
    
    max_dev = max(deviations) if deviations else 0.0
    avg_dev = sum(deviations) / len(deviations) if deviations else 0.0
    
    return DecayValidationResult(
        valid=len(invalid_entries) == 0,
        total_entries=len(entries),
        invalid_entries=invalid_entries,
        max_deviation=max_dev,
        avg_deviation=avg_dev
    )


def check_output_consistency(
    output_files: Dict[str, Dict]
) -> ConsistencyResult:
    """
    OQ-10: Check for orphaned references across output files.
    
    Validates that all IDs referenced in one file exist in the source file.
    
    Args:
        output_files: Dict mapping filename to parsed content
        
    Returns:
        ConsistencyResult with orphan details
    """
    orphaned = defaultdict(list)
    missing = defaultdict(list)
    
    # Collect all defined IDs
    defined_ids = {
        "claims": set(),
        "sources": set(),
        "gaps": set()
    }
    
    # Extract defined IDs from each file
    if "proof_chain.json" in output_files:
        for chain in output_files["proof_chain.json"].get("chains", []):
            defined_ids["claims"].add(chain.get("claim_id"))
            for link in chain.get("evidence_links", []):
                defined_ids["sources"].add(link.get("source_id"))
    
    if "gap_analysis_report.json" in output_files:
        for gap in output_files["gap_analysis_report.json"].get("gaps", []):
            defined_ids["gaps"].add(gap.get("id"))
    
    if "sufficiency_matrix.json" in output_files:
        for pillar_data in output_files["sufficiency_matrix.json"].get("pillars", {}).values():
            for gap_id in pillar_data.get("gaps", []):
                defined_ids["gaps"].add(gap_id)
    
    # Check references in triangulation
    if "triangulation.json" in output_files:
        for tri in output_files["triangulation.json"].get("triangulations", []):
            claim_id = tri.get("claim_id")
            if claim_id and claim_id not in defined_ids["claims"]:
                orphaned["triangulation.json"].append(f"claim:{claim_id}")
            
            for source in tri.get("sources", []):
                source_id = source.get("source_id")
                if source_id and source_id not in defined_ids["sources"]:
                    orphaned["triangulation.json"].append(f"source:{source_id}")
    
    # Check references in suggested_searches
    if "suggested_searches.json" in output_files:
        for suggestion in output_files["suggested_searches.json"].get("suggestions", []):
            gap_id = suggestion.get("gap_id")
            if gap_id and gap_id not in defined_ids["gaps"]:
                orphaned["suggested_searches.json"].append(f"gap:{gap_id}")
    
    # Check references in evidence_decay
    if "evidence_decay.json" in output_files:
        for entry in output_files["evidence_decay.json"].get("entries", []):
            source_id = entry.get("source_id")
            if source_id and source_id not in defined_ids["sources"]:
                orphaned["evidence_decay.json"].append(f"source:{source_id}")
    
    total_issues = sum(len(v) for v in orphaned.values())
    
    return ConsistencyResult(
        consistent=total_issues == 0,
        orphaned_references=dict(orphaned),
        missing_targets=dict(missing),
        total_issues=total_issues
    )


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_proof_chain(tmp_path) -> Path:
    """Create sample proof_chain.json for testing."""
    data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_claims": 10,
            "total_sources": 25,
            "pipeline_version": "1.0.0"
        },
        "chains": [
            {
                "claim_id": "claim-001",
                "claim_text": "Neuromorphic processors achieve 10x power efficiency compared to GPUs",
                "verdict": "approved",
                "pillar": "P4_Power_Efficiency",
                "composite_score": 3.8,
                "evidence_links": [
                    {
                        "source_id": "source-001",
                        "paper_title": "Energy-Efficient Neuromorphic Computing",
                        "excerpt": "Our measurements show 10.2x improvement...",
                        "page_number": 7,
                        "relevance_score": 0.92,
                        "contribution": "primary"
                    },
                    {
                        "source_id": "source-002",
                        "paper_title": "Benchmarking Neural Accelerators",
                        "relevance_score": 0.78,
                        "contribution": "corroborating"
                    }
                ]
            },
            {
                "claim_id": "claim-002",
                "claim_text": "Spiking neural networks enable real-time inference on edge devices",
                "verdict": "approved",
                "pillar": "P1_Hardware_Architecture",
                "composite_score": 3.5,
                "evidence_links": [
                    {
                        "source_id": "source-003",
                        "paper_title": "SNN Edge Deployment",
                        "relevance_score": 0.85,
                        "contribution": "primary"
                    }
                ]
            }
        ]
    }
    
    output_path = tmp_path / "proof_chain.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return output_path


@pytest.fixture
def sample_sufficiency_matrix(tmp_path) -> Path:
    """Create sample sufficiency_matrix.json for testing."""
    data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "pillar_count": 4,
            "threshold_config": {
                "minimum_claims_per_pillar": 5,
                "minimum_coverage_percent": 70.0
            }
        },
        "pillars": {
            "P1_Hardware_Architecture": {
                "pillar_id": "P1",
                "name": "Hardware Architecture",
                "is_sufficient": True,
                "claim_count": 15,
                "approved_claims": 12,
                "coverage_percent": 85.0,
                "strength_avg": 3.6,
                "gaps": []
            },
            "P2_Learning_Algorithms": {
                "pillar_id": "P2",
                "name": "Learning Algorithms",
                "is_sufficient": False,
                "claim_count": 8,
                "approved_claims": 5,
                "coverage_percent": 55.0,
                "strength_avg": 3.2,
                "gaps": ["gap-002"]
            },
            "P3_Applications": {
                "pillar_id": "P3",
                "name": "Applications",
                "is_sufficient": True,
                "claim_count": 20,
                "approved_claims": 18,
                "coverage_percent": 90.0,
                "strength_avg": 4.0,
                "gaps": []
            },
            "P4_Power_Efficiency": {
                "pillar_id": "P4",
                "name": "Power Efficiency",
                "is_sufficient": False,
                "claim_count": 6,
                "approved_claims": 3,
                "coverage_percent": 45.0,
                "strength_avg": 3.0,
                "gaps": ["gap-001"]
            }
        },
        "overall_sufficiency": {
            "is_sufficient": False,
            "coverage_percent": 68.75,
            "gaps_identified": 2
        }
    }
    
    output_path = tmp_path / "sufficiency_matrix.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return output_path


@pytest.fixture
def sample_triangulation(tmp_path) -> Path:
    """Create sample triangulation.json for testing."""
    data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_triangulations": 2,
            "min_sources_required": 2
        },
        "triangulations": [
            {
                "claim_id": "claim-001",
                "source_count": 3,
                "sources": [
                    {"source_id": "source-001", "agreement_score": 0.95},
                    {"source_id": "source-002", "agreement_score": 0.82},
                    {"source_id": "source-005", "agreement_score": 0.78}
                ],
                "confidence_boost": 0.15,
                "triangulation_type": "full_agreement"
            },
            {
                "claim_id": "claim-002",
                "source_count": 2,
                "sources": [
                    {"source_id": "source-003", "agreement_score": 0.88},
                    {"source_id": "source-004", "agreement_score": 0.75}
                ],
                "confidence_boost": 0.08,
                "triangulation_type": "partial_agreement"
            }
        ]
    }
    
    output_path = tmp_path / "triangulation.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return output_path


@pytest.fixture
def sample_evidence_decay(tmp_path) -> Path:
    """Create sample evidence_decay.json for testing."""
    reference_date = date.today()
    
    data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "reference_date": reference_date.isoformat(),
            "total_entries": 3
        },
        "decay_config": {
            "decay_model": "exponential",
            "half_life_years": 5.0,
            "minimum_weight": 0.1,
            "cutoff_years": 20
        },
        "entries": [
            {
                "source_id": "source-001",
                "publication_date": "2024-01-15",
                "age_years": 1.0,
                "decay_weight": 0.87,  # ~0.87 for 1 year with half-life 5
                "original_score": 4.0,
                "weighted_score": 3.48
            },
            {
                "source_id": "source-002",
                "publication_date": "2020-06-01",
                "age_years": 4.5,
                "decay_weight": 0.54,  # ~0.54 for 4.5 years
                "original_score": 3.5,
                "weighted_score": 1.89
            },
            {
                "source_id": "source-003",
                "publication_date": "2015-01-01",
                "age_years": 10.0,
                "decay_weight": 0.25,  # ~0.25 for 10 years
                "original_score": 4.5,
                "weighted_score": 1.125
            }
        ]
    }
    
    output_path = tmp_path / "evidence_decay.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return output_path


@pytest.fixture
def approved_claim_ids() -> Set[str]:
    """Set of approved claim IDs for completeness testing."""
    return {"claim-001", "claim-002"}


@pytest.fixture
def defined_pillars() -> Set[str]:
    """Set of defined pillar IDs for coverage testing."""
    return {
        "P1_Hardware_Architecture",
        "P2_Learning_Algorithms", 
        "P3_Applications",
        "P4_Power_Efficiency"
    }


@pytest.fixture
def valid_source_ids() -> Set[str]:
    """Set of valid source IDs for reference validation."""
    return {"source-001", "source-002", "source-003", "source-004", "source-005"}


@pytest.fixture
def valid_claim_ids() -> Set[str]:
    """Set of valid claim IDs for reference validation."""
    return {"claim-001", "claim-002", "claim-003"}


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.validation
@pytest.mark.output_quality
class TestEvidenceSchemaValidation:
    """Test suite for evidence output schema validation."""
    
    @pytest.mark.parametrize("schema_name", [
        "proof_chain.schema.json",
        "sufficiency_matrix.schema.json",
        "triangulation.schema.json",
        "evidence_decay.schema.json"
    ])
    def test_schema_files_exist(self, schema_name):
        """Verify all schema definition files exist."""
        schema_path = SCHEMA_DIR / schema_name
        assert schema_path.exists(), f"Schema file missing: {schema_path}"
    
    def test_proof_chain_valid_schema(self, sample_proof_chain):
        """Validate proof_chain.json against schema."""
        result = validate_json_against_schema(
            sample_proof_chain,
            "proof_chain.schema.json"
        )
        assert result.valid, f"Schema validation failed: {result.errors}"
    
    def test_sufficiency_matrix_valid_schema(self, sample_sufficiency_matrix):
        """Validate sufficiency_matrix.json against schema."""
        result = validate_json_against_schema(
            sample_sufficiency_matrix,
            "sufficiency_matrix.schema.json"
        )
        assert result.valid, f"Schema validation failed: {result.errors}"
    
    def test_triangulation_valid_schema(self, sample_triangulation):
        """Validate triangulation.json against schema."""
        result = validate_json_against_schema(
            sample_triangulation,
            "triangulation.schema.json"
        )
        assert result.valid, f"Schema validation failed: {result.errors}"
    
    def test_evidence_decay_valid_schema(self, sample_evidence_decay):
        """Validate evidence_decay.json against schema."""
        result = validate_json_against_schema(
            sample_evidence_decay,
            "evidence_decay.schema.json"
        )
        assert result.valid, f"Schema validation failed: {result.errors}"


@pytest.mark.validation
@pytest.mark.output_quality
class TestEvidenceCompleteness:
    """Test suite for evidence completeness validation (OQ-06, OQ-07)."""
    
    # -------------------------------------------------------------------------
    # OQ-06: Proof Chain Completeness
    # -------------------------------------------------------------------------
    
    def test_proof_chain_completeness(
        self, 
        sample_proof_chain,
        approved_claim_ids
    ):
        """
        OQ-06: All approved claims should have evidence links.
        
        Target: 100% of approved claims linked to evidence.
        """
        with open(sample_proof_chain) as f:
            data = json.load(f)
        
        result = check_proof_chain_completeness(data, approved_claim_ids)
        
        assert result.complete, (
            f"Proof chain incomplete: {result.coverage_percent:.1f}% coverage. "
            f"Missing claims: {result.missing}"
        )
    
    def test_proof_chain_detects_missing(self, tmp_path):
        """Test that missing claims are detected."""
        data = {
            "metadata": {"generated_at": datetime.now().isoformat(), 
                        "total_claims": 1, "total_sources": 1},
            "chains": [
                {
                    "claim_id": "claim-001",
                    "claim_text": "Test claim",
                    "verdict": "approved",
                    "evidence_links": [{"source_id": "s1", "relevance_score": 0.8}]
                }
                # Missing: claim-002
            ]
        }
        
        output_path = tmp_path / "incomplete_chain.json"
        with open(output_path, "w") as f:
            json.dump(data, f)
        
        with open(output_path) as f:
            loaded = json.load(f)
        
        result = check_proof_chain_completeness(
            loaded, 
            {"claim-001", "claim-002"}
        )
        
        assert not result.complete
        assert "claim-002" in result.missing
    
    # -------------------------------------------------------------------------
    # OQ-07: Sufficiency Matrix Coverage
    # -------------------------------------------------------------------------
    
    def test_sufficiency_matrix_coverage(
        self,
        sample_sufficiency_matrix,
        defined_pillars
    ):
        """
        OQ-07: All defined pillars should have coverage entries.
        
        Target: 100% pillar coverage.
        """
        with open(sample_sufficiency_matrix) as f:
            data = json.load(f)
        
        result = check_sufficiency_matrix_coverage(data, defined_pillars)
        
        assert result.complete, (
            f"Sufficiency matrix incomplete: {result.coverage_percent:.1f}% coverage. "
            f"Missing pillars: {result.missing}"
        )
    
    def test_sufficiency_matrix_detects_missing_pillar(self, tmp_path):
        """Test that missing pillars are detected."""
        data = {
            "metadata": {"generated_at": datetime.now().isoformat(), "pillar_count": 2},
            "pillars": {
                "P1_Hardware": {"pillar_id": "P1", "name": "Hardware", 
                               "is_sufficient": True, "claim_count": 10,
                               "coverage_percent": 80.0}
                # Missing: P2, P3, P4
            },
            "overall_sufficiency": {"is_sufficient": False, "coverage_percent": 25.0,
                                   "gaps_identified": 3}
        }
        
        output_path = tmp_path / "incomplete_matrix.json"
        with open(output_path, "w") as f:
            json.dump(data, f)
        
        with open(output_path) as f:
            loaded = json.load(f)
        
        result = check_sufficiency_matrix_coverage(
            loaded,
            {"P1_Hardware", "P2_Learning", "P3_Apps", "P4_Power"}
        )
        
        assert not result.complete
        assert len(result.missing) == 3


@pytest.mark.validation
@pytest.mark.output_quality
class TestEvidenceAccuracy:
    """Test suite for evidence accuracy validation (OQ-08, OQ-09)."""
    
    # -------------------------------------------------------------------------
    # OQ-08: Triangulation Accuracy
    # -------------------------------------------------------------------------
    
    def test_triangulation_references_valid(
        self,
        sample_triangulation,
        valid_source_ids,
        valid_claim_ids
    ):
        """
        OQ-08: Triangulation cross-references should be valid.
        
        All source and claim IDs should exist in the source data.
        """
        with open(sample_triangulation) as f:
            data = json.load(f)
        
        is_valid, issues = check_triangulation_accuracy(
            data, valid_source_ids, valid_claim_ids
        )
        
        assert is_valid, f"Triangulation issues: {issues}"
    
    def test_triangulation_detects_invalid_source(self, tmp_path):
        """Test that invalid source references are detected."""
        data = {
            "metadata": {"generated_at": datetime.now().isoformat(),
                        "total_triangulations": 1, "min_sources_required": 2},
            "triangulations": [{
                "claim_id": "claim-001",
                "source_count": 2,
                "sources": [
                    {"source_id": "source-001", "agreement_score": 0.9},
                    {"source_id": "INVALID-SOURCE", "agreement_score": 0.8}
                ],
                "confidence_boost": 0.1,
                "triangulation_type": "full_agreement"
            }]
        }
        
        is_valid, issues = check_triangulation_accuracy(
            data,
            {"source-001", "source-002"},  # INVALID-SOURCE not in set
            {"claim-001"}
        )
        
        assert not is_valid
        assert any("INVALID-SOURCE" in issue for issue in issues)
    
    # -------------------------------------------------------------------------
    # OQ-09: Evidence Decay Correctness
    # -------------------------------------------------------------------------
    
    def test_decay_weights_correct(self, sample_evidence_decay):
        """
        OQ-09: Decay weights should follow the decay formula.
        
        Validates exponential decay calculation.
        """
        with open(sample_evidence_decay) as f:
            data = json.load(f)
        
        result = validate_decay_weights(data)
        
        assert result.valid, (
            f"Decay validation failed. Invalid entries: {result.invalid_entries}"
        )
        assert result.avg_deviation < 0.05, (
            f"Average deviation {result.avg_deviation:.3f} exceeds threshold"
        )
    
    def test_decay_detects_wrong_weight(self, tmp_path):
        """Test that incorrect decay weights are detected."""
        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "reference_date": date.today().isoformat(),
                "total_entries": 1
            },
            "decay_config": {
                "decay_model": "exponential",
                "half_life_years": 5.0,
                "minimum_weight": 0.1
            },
            "entries": [{
                "source_id": "source-001",
                "publication_date": "2020-01-01",  # ~5 years old
                "age_years": 5.0,
                "decay_weight": 0.99  # Should be ~0.5, not 0.99
            }]
        }
        
        result = validate_decay_weights(data)
        
        assert not result.valid
        assert len(result.invalid_entries) == 1


@pytest.mark.validation
@pytest.mark.output_quality
class TestOutputConsistency:
    """Test suite for output consistency validation (OQ-10)."""
    
    def test_no_orphaned_references(self, tmp_path):
        """
        OQ-10: No orphaned references across output files.
        
        All IDs referenced in one file should exist in source files.
        """
        # Create consistent output files
        output_files = {
            "proof_chain.json": {
                "chains": [
                    {
                        "claim_id": "claim-001",
                        "verdict": "approved",
                        "evidence_links": [
                            {"source_id": "source-001", "relevance_score": 0.9}
                        ]
                    }
                ]
            },
            "gap_analysis_report.json": {
                "gaps": [{"id": "gap-001", "pillar": "P1", "description": "Test",
                         "severity": "high"}]
            },
            "triangulation.json": {
                "triangulations": [
                    {
                        "claim_id": "claim-001",  # Valid
                        "sources": [
                            {"source_id": "source-001", "agreement_score": 0.8}
                        ]
                    }
                ]
            },
            "suggested_searches.json": {
                "suggestions": [
                    {"id": "search-001", "gap_id": "gap-001", "query": "test",
                     "priority": 1, "rationale": "Test rationale"}
                ]
            }
        }
        
        result = check_output_consistency(output_files)
        
        assert result.consistent, (
            f"Consistency issues: {result.orphaned_references}"
        )
    
    def test_detects_orphaned_gap_reference(self):
        """Test that orphaned gap references are detected."""
        output_files = {
            "gap_analysis_report.json": {
                "gaps": [{"id": "gap-001", "pillar": "P1", "description": "Test",
                         "severity": "high"}]
            },
            "suggested_searches.json": {
                "suggestions": [
                    {"id": "search-001", "gap_id": "gap-INVALID", "query": "test",
                     "priority": 1, "rationale": "Test"}
                ]
            }
        }
        
        result = check_output_consistency(output_files)
        
        assert not result.consistent
        assert "suggested_searches.json" in result.orphaned_references


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.validation
@pytest.mark.output_quality
@pytest.mark.integration
class TestActualEvidenceOutputs:
    """Test actual evidence outputs from pipeline runs."""
    
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
    def test_actual_proof_chain(self, latest_review_dir):
        """Validate actual proof_chain.json."""
        if latest_review_dir is None:
            pytest.skip("No review outputs found")
        
        file_path = latest_review_dir / "proof_chain.json"
        if not file_path.exists():
            pytest.skip(f"No proof_chain.json in {latest_review_dir}")
        
        result = validate_json_against_schema(
            file_path,
            "proof_chain.schema.json"
        )
        
        assert result.valid, f"Validation failed: {result.errors}"
    
    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent.parent / "reviews").exists(),
        reason="No reviews directory found"
    )
    def test_actual_evidence_decay(self, latest_review_dir):
        """Validate actual evidence_decay.json weights."""
        if latest_review_dir is None:
            pytest.skip("No review outputs found")
        
        file_path = latest_review_dir / "evidence_decay.json"
        if not file_path.exists():
            pytest.skip(f"No evidence_decay.json in {latest_review_dir}")
        
        with open(file_path) as f:
            data = json.load(f)
        
        result = validate_decay_weights(data)
        
        assert result.valid, f"Decay validation failed: {result.invalid_entries}"
```

---

## Implementation Plan

### Hour 1-2: Schema Design
1. Analyze actual evidence output file structures
2. Create JSON schemas for all four evidence files
3. Define validation rules for each field

### Hour 3-4: Completeness Tests
1. Implement OQ-06 (proof chain completeness)
2. Implement OQ-07 (sufficiency matrix coverage)
3. Create fixtures with sample data

### Hour 5: Accuracy Tests
1. Implement OQ-08 (triangulation accuracy)
2. Implement OQ-09 (decay weight validation)
3. Create decay formula calculator

### Hour 6: Consistency & Integration
1. Implement OQ-10 (cross-file consistency)
2. Add integration tests for actual outputs
3. Document validation thresholds
4. Verify all tests pass

---

## Testing Instructions

```bash
# Run all evidence output tests
pytest tests/validation/outputs/test_evidence_outputs.py -v -m output_quality

# Run completeness tests only
pytest tests/validation/outputs/test_evidence_outputs.py -v -k "completeness"

# Run accuracy tests only
pytest tests/validation/outputs/test_evidence_outputs.py -v -k "accuracy"

# Run consistency tests only
pytest tests/validation/outputs/test_evidence_outputs.py -v -k "consistency"

# Run integration tests against real outputs
pytest tests/validation/outputs/test_evidence_outputs.py -v -m integration
```

---

## Dependencies

### Python Packages
- `jsonschema>=4.0.0` - JSON Schema validation
- `pytest>=7.0.0` - Test framework

### Internal Dependencies
- `tests/validation/outputs/test_output_schemas.py` - Shared validation functions
- `pillar_definitions.json` - Pillar ID source for OQ-07
- `reviews/` - Pipeline output directory

---

## Acceptance Criteria

- [ ] OQ-06: 100% of approved claims have evidence links
- [ ] OQ-07: 100% of pillars have sufficiency entries
- [ ] OQ-08: All triangulation references are valid
- [ ] OQ-09: Decay weights within 5% of expected values
- [ ] OQ-10: Zero orphaned references across files
- [ ] JSON schemas created for all 4 evidence files
- [ ] Integration tests validate actual outputs
- [ ] Tests run in < 10 seconds

---

## Notes

- Decay weight tolerance is 5% to account for rounding
- Cross-file consistency requires all output files present
- Pillar IDs come from pillar_definitions.json
- Consider caching parsed files for multi-file consistency checks
- Evidence chain validation is critical for audit trails
