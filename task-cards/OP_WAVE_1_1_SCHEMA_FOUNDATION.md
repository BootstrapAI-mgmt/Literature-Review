# Task Card: Schema Foundation & Data Structures

**Task ID:** OP-W1-1  
**Wave:** 1 (Foundation)  
**Priority:** CRITICAL  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** None  
**Blocks:** OP-W2-1, OP-W2-2, OP-W3-1, OP-W3-2, OP-W4-1, OP-W4-2, OP-W4-3

---

## Objective

Create foundational data structures, schemas, and enhanced pillar definitions that all subsequent operationalization tasks depend on.

## Background

The current literature review system has:
- `pillar_definitions_enhanced.json` with `quantitative_metrics` and `validation_criteria`
- Evidence extraction and gap analysis pipelines
- No structured action vectors, benchmark linkage, or pillar evolution tracking

This task establishes the foundational schemas for:
1. Action Vectors - executable steps from research
2. Benchmark-Metric Linkage - connecting targets to validation
3. Validation Strategies - per-requirement validation definitions
4. Pillar Research Logs - tracking research status and saturation
5. Stakeholder Definitions - mapping beneficiaries to pillars

## Success Criteria

- [ ] `ActionVector` dataclass created with all required fields
- [ ] `ValidationStrategy` dataclass created with all required fields
- [ ] `pillar_definitions_enhanced.json` restructured with benchmark linkage
- [ ] `pillar_research_log.json` schema created
- [ ] `stakeholder_definitions.json` schema created
- [ ] All schemas validated with JSON Schema or Pydantic
- [ ] Unit tests pass for all dataclasses
- [ ] Migration script for existing pillar definitions

---

## Deliverables

### 1. ActionVector Dataclass

**File:** `literature_review/models/action_vector.py`

```python
"""
Action Vector Model - Executable steps derived from research findings.

This module defines the ActionVector dataclass that represents
operationalization outputs from the literature review process.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime
import json


class ActionType(Enum):
    """Types of actions that can be derived from research."""
    IMPLEMENT = "implement"           # Direct implementation step
    VALIDATE = "validate"             # Validation/testing step
    INTEGRATE = "integrate"           # Cross-pillar integration
    RESEARCH_FURTHER = "research_further"  # Need more research
    DEFINE_PROTOCOL = "define_protocol"    # Need to define methodology


class EffortLevel(Enum):
    """Estimated effort levels for actions."""
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"


@dataclass
class ResourceRequirements:
    """Resources needed to execute an action."""
    hardware: List[str] = field(default_factory=list)
    software: List[str] = field(default_factory=list)
    data: List[str] = field(default_factory=list)
    compute_time: Optional[str] = None
    personnel_skills: List[str] = field(default_factory=list)
    estimated_cost: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "hardware": self.hardware,
            "software": self.software,
            "data": self.data,
            "compute_time": self.compute_time,
            "personnel_skills": self.personnel_skills,
            "estimated_cost": self.estimated_cost
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ResourceRequirements":
        return cls(
            hardware=data.get("hardware", []),
            software=data.get("software", []),
            data=data.get("data", []),
            compute_time=data.get("compute_time"),
            personnel_skills=data.get("personnel_skills", []),
            estimated_cost=data.get("estimated_cost")
        )


@dataclass
class ReproducibilityInfo:
    """Reproducibility assessment for an action."""
    code_available: bool = False
    code_url: Optional[str] = None
    data_available: bool = False
    data_url: Optional[str] = None
    hyperparameters_specified: bool = False
    methodology_detail_level: str = "low"  # low, medium, high
    
    @property
    def reproducibility_score(self) -> float:
        """Calculate reproducibility score (0-1)."""
        score = 0.0
        if self.code_available:
            score += 0.35
        if self.data_available:
            score += 0.25
        if self.hyperparameters_specified:
            score += 0.15
        
        detail_scores = {"low": 0.0, "medium": 0.125, "high": 0.25}
        score += detail_scores.get(self.methodology_detail_level, 0.0)
        
        return min(score, 1.0)
    
    def to_dict(self) -> Dict:
        return {
            "code_available": self.code_available,
            "code_url": self.code_url,
            "data_available": self.data_available,
            "data_url": self.data_url,
            "hyperparameters_specified": self.hyperparameters_specified,
            "methodology_detail_level": self.methodology_detail_level,
            "reproducibility_score": self.reproducibility_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ReproducibilityInfo":
        return cls(
            code_available=data.get("code_available", False),
            code_url=data.get("code_url"),
            data_available=data.get("data_available", False),
            data_url=data.get("data_url"),
            hyperparameters_specified=data.get("hyperparameters_specified", False),
            methodology_detail_level=data.get("methodology_detail_level", "low")
        )


@dataclass
class ActionChainPosition:
    """Position of this action in the execution chain."""
    prerequisites: List[str] = field(default_factory=list)  # Action IDs that must complete first
    enables: List[str] = field(default_factory=list)         # Action IDs this enables
    gaps: List[str] = field(default_factory=list)            # Missing steps in the chain
    blocking_unknowns: List[str] = field(default_factory=list)  # Questions that must be answered
    
    def to_dict(self) -> Dict:
        return {
            "prerequisites": self.prerequisites,
            "enables": self.enables,
            "gaps": self.gaps,
            "blocking_unknowns": self.blocking_unknowns
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ActionChainPosition":
        return cls(
            prerequisites=data.get("prerequisites", []),
            enables=data.get("enables", []),
            gaps=data.get("gaps", []),
            blocking_unknowns=data.get("blocking_unknowns", [])
        )


@dataclass
class ActionVector:
    """
    Represents an executable step derived from research findings.
    
    Action vectors transform abstract research findings into concrete
    implementation steps that can be prioritized and tracked.
    """
    
    # Identification
    action_id: str                      # Unique identifier (e.g., "AV-P2-001")
    pillar: str                         # Source pillar name
    requirement_id: str                 # Source requirement ID
    sub_requirement_id: Optional[str] = None  # Source sub-requirement ID
    
    # Action definition
    action_type: ActionType = ActionType.IMPLEMENT
    action_description: str = ""        # Human-readable action
    implementation_approach: str = ""   # Specific technical approach
    
    # Evidence basis
    source_papers: List[str] = field(default_factory=list)
    evidence_strength: float = 0.0      # 0-1 confidence from evidence
    claim_ids: List[str] = field(default_factory=list)  # Source claim IDs
    
    # Operationalization metadata
    reproducibility: ReproducibilityInfo = field(default_factory=ReproducibilityInfo)
    resources: ResourceRequirements = field(default_factory=ResourceRequirements)
    estimated_effort: EffortLevel = EffortLevel.DAYS
    
    # Chain position
    chain_position: ActionChainPosition = field(default_factory=ActionChainPosition)
    
    # Dependencies on other pillars
    pillar_dependencies: List[Dict] = field(default_factory=list)  # [{pillar, min_completeness}]
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"             # pending, in_progress, completed, blocked
    notes: str = ""
    
    @property
    def is_actionable(self) -> bool:
        """Check if action can be started (no blocking unknowns or unmet prerequisites)."""
        return (
            len(self.chain_position.blocking_unknowns) == 0 and
            len(self.chain_position.prerequisites) == 0  # Simplified - should check completion
        )
    
    @property
    def is_reproducible(self) -> bool:
        """Check if action meets reproducibility threshold (>0.7)."""
        return self.reproducibility.reproducibility_score >= 0.7
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary for JSON output."""
        return {
            "action_id": self.action_id,
            "pillar": self.pillar,
            "requirement_id": self.requirement_id,
            "sub_requirement_id": self.sub_requirement_id,
            "action_type": self.action_type.value,
            "action_description": self.action_description,
            "implementation_approach": self.implementation_approach,
            "source_papers": self.source_papers,
            "evidence_strength": self.evidence_strength,
            "claim_ids": self.claim_ids,
            "reproducibility": self.reproducibility.to_dict(),
            "resources": self.resources.to_dict(),
            "estimated_effort": self.estimated_effort.value,
            "chain_position": self.chain_position.to_dict(),
            "pillar_dependencies": self.pillar_dependencies,
            "created_at": self.created_at,
            "status": self.status,
            "notes": self.notes,
            "is_actionable": self.is_actionable,
            "is_reproducible": self.is_reproducible
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ActionVector":
        """Deserialize from dictionary."""
        return cls(
            action_id=data["action_id"],
            pillar=data["pillar"],
            requirement_id=data["requirement_id"],
            sub_requirement_id=data.get("sub_requirement_id"),
            action_type=ActionType(data.get("action_type", "implement")),
            action_description=data.get("action_description", ""),
            implementation_approach=data.get("implementation_approach", ""),
            source_papers=data.get("source_papers", []),
            evidence_strength=data.get("evidence_strength", 0.0),
            claim_ids=data.get("claim_ids", []),
            reproducibility=ReproducibilityInfo.from_dict(data.get("reproducibility", {})),
            resources=ResourceRequirements.from_dict(data.get("resources", {})),
            estimated_effort=EffortLevel(data.get("estimated_effort", "days")),
            chain_position=ActionChainPosition.from_dict(data.get("chain_position", {})),
            pillar_dependencies=data.get("pillar_dependencies", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            status=data.get("status", "pending"),
            notes=data.get("notes", "")
        )


def generate_action_id(pillar: str, requirement_id: str, sequence: int) -> str:
    """
    Generate a unique action ID.
    
    Format: AV-P{pillar_num}-{req_short}-{sequence:03d}
    Example: AV-P2-A21-001
    """
    # Extract pillar number
    pillar_num = "".join(filter(str.isdigit, pillar.split(":")[0])) or "0"
    
    # Shorten requirement ID
    req_short = requirement_id.replace("REQ-", "").replace("-", "").replace(".", "")[:4]
    
    return f"AV-P{pillar_num}-{req_short}-{sequence:03d}"
```

### 2. ValidationStrategy Dataclass

**File:** `literature_review/models/validation_strategy.py`

```python
"""
Validation Strategy Model - Defines how requirements are validated.

This module defines data structures for tracking validation strategies
and their evidence coverage.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime


class ValidationStatus(Enum):
    """Validation coverage status for a requirement."""
    VALIDATED = "validated"           # Evidence matches defined strategy
    PARTIAL = "partial"               # Evidence exists but different method
    UNVALIDATED = "unvalidated"       # Strategy defined but no evidence
    NO_STRATEGY = "no_strategy"       # No validation approach defined


class EvidenceType(Enum):
    """Types of evidence that can validate a requirement."""
    EXPERIMENTAL = "experimental"           # Lab experiments
    SIMULATION = "simulation"               # Computational simulation
    THEORETICAL = "theoretical"             # Mathematical proof/derivation
    OBSERVATIONAL = "observational"         # Real-world observation
    BENCHMARK = "benchmark"                 # Standardized benchmark test
    COMPARATIVE = "comparative"             # Comparison with baseline
    REPLICATION = "replication"             # Replication of prior work


@dataclass
class BenchmarkLink:
    """Links a metric to a specific benchmark."""
    benchmark_name: str                    # e.g., "DVS128 Gesture"
    benchmark_type: str                    # "dataset", "protocol", "hardware_test"
    metric_measured: str                   # e.g., "inference_latency_ms"
    measurement_method: str                # How to measure
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "benchmark_name": self.benchmark_name,
            "benchmark_type": self.benchmark_type,
            "metric_measured": self.metric_measured,
            "measurement_method": self.measurement_method,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BenchmarkLink":
        return cls(
            benchmark_name=data["benchmark_name"],
            benchmark_type=data.get("benchmark_type", "dataset"),
            metric_measured=data.get("metric_measured", ""),
            measurement_method=data.get("measurement_method", ""),
            notes=data.get("notes")
        )


@dataclass
class MetricDefinition:
    """Enhanced metric definition with benchmark linkage."""
    metric_id: str                         # e.g., "P2-M1"
    metric_name: str                       # e.g., "latency_target"
    target_value: str                      # e.g., "< 10ms end-to-end"
    measurement_method: str                # How to measure this metric
    benchmarks: List[BenchmarkLink] = field(default_factory=list)
    benchmark_status: str = "no_benchmark"  # covered, partial, no_benchmark
    validation_evidence: List[str] = field(default_factory=list)  # Paper filenames
    
    def to_dict(self) -> Dict:
        return {
            "metric_id": self.metric_id,
            "metric_name": self.metric_name,
            "target_value": self.target_value,
            "measurement_method": self.measurement_method,
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "benchmark_status": self.benchmark_status,
            "validation_evidence": self.validation_evidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MetricDefinition":
        return cls(
            metric_id=data.get("metric_id", ""),
            metric_name=data.get("metric_name", ""),
            target_value=data.get("target_value", ""),
            measurement_method=data.get("measurement_method", ""),
            benchmarks=[BenchmarkLink.from_dict(b) for b in data.get("benchmarks", [])],
            benchmark_status=data.get("benchmark_status", "no_benchmark"),
            validation_evidence=data.get("validation_evidence", [])
        )


@dataclass
class ValidationStrategy:
    """
    Defines the validation strategy for a sub-requirement.
    
    Maps requirements to specific validation methods, benchmarks,
    and acceptance criteria.
    """
    
    # Identification
    requirement_id: str                    # e.g., "Sub-1.1.1"
    requirement_text: str                  # Full requirement text
    pillar: str                            # Parent pillar
    
    # Validation definition
    validation_method: str = ""            # Primary method description
    benchmark_protocol: str = ""           # Specific benchmark/test protocol
    acceptance_criteria: str = ""          # What constitutes passing
    
    # Evidence requirements
    required_evidence_types: List[EvidenceType] = field(default_factory=list)
    minimum_evidence_count: int = 1        # Minimum papers needed
    cross_validation_required: bool = False  # Need multiple independent validations
    
    # Current status
    status: ValidationStatus = ValidationStatus.NO_STRATEGY
    evidence_papers: List[str] = field(default_factory=list)
    evidence_summary: str = ""
    
    # Gap information
    gap_notes: str = ""                    # Why validation is incomplete
    suggested_approach: str = ""           # How to close the gap
    
    # Metadata
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def is_strategy_defined(self) -> bool:
        """Check if a validation strategy has been defined."""
        return bool(self.validation_method or self.benchmark_protocol)
    
    @property
    def is_fully_validated(self) -> bool:
        """Check if requirement meets all validation criteria."""
        return (
            self.status == ValidationStatus.VALIDATED and
            len(self.evidence_papers) >= self.minimum_evidence_count
        )
    
    def to_dict(self) -> Dict:
        return {
            "requirement_id": self.requirement_id,
            "requirement_text": self.requirement_text,
            "pillar": self.pillar,
            "validation_method": self.validation_method,
            "benchmark_protocol": self.benchmark_protocol,
            "acceptance_criteria": self.acceptance_criteria,
            "required_evidence_types": [e.value for e in self.required_evidence_types],
            "minimum_evidence_count": self.minimum_evidence_count,
            "cross_validation_required": self.cross_validation_required,
            "status": self.status.value,
            "evidence_papers": self.evidence_papers,
            "evidence_summary": self.evidence_summary,
            "gap_notes": self.gap_notes,
            "suggested_approach": self.suggested_approach,
            "last_updated": self.last_updated,
            "is_strategy_defined": self.is_strategy_defined,
            "is_fully_validated": self.is_fully_validated
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ValidationStrategy":
        return cls(
            requirement_id=data["requirement_id"],
            requirement_text=data.get("requirement_text", ""),
            pillar=data.get("pillar", ""),
            validation_method=data.get("validation_method", ""),
            benchmark_protocol=data.get("benchmark_protocol", ""),
            acceptance_criteria=data.get("acceptance_criteria", ""),
            required_evidence_types=[
                EvidenceType(e) for e in data.get("required_evidence_types", [])
            ],
            minimum_evidence_count=data.get("minimum_evidence_count", 1),
            cross_validation_required=data.get("cross_validation_required", False),
            status=ValidationStatus(data.get("status", "no_strategy")),
            evidence_papers=data.get("evidence_papers", []),
            evidence_summary=data.get("evidence_summary", ""),
            gap_notes=data.get("gap_notes", ""),
            suggested_approach=data.get("suggested_approach", ""),
            last_updated=data.get("last_updated", datetime.now().isoformat())
        )
```

### 3. Models Package Init

**File:** `literature_review/models/__init__.py`

```python
"""
Literature Review Models Package

This package contains data models for the operationalization features:
- ActionVector: Executable steps from research
- ValidationStrategy: Requirement validation definitions
"""

from literature_review.models.action_vector import (
    ActionVector,
    ActionType,
    EffortLevel,
    ResourceRequirements,
    ReproducibilityInfo,
    ActionChainPosition,
    generate_action_id
)

from literature_review.models.validation_strategy import (
    ValidationStrategy,
    ValidationStatus,
    EvidenceType,
    BenchmarkLink,
    MetricDefinition
)

__all__ = [
    # Action Vector
    "ActionVector",
    "ActionType", 
    "EffortLevel",
    "ResourceRequirements",
    "ReproducibilityInfo",
    "ActionChainPosition",
    "generate_action_id",
    
    # Validation Strategy
    "ValidationStrategy",
    "ValidationStatus",
    "EvidenceType",
    "BenchmarkLink",
    "MetricDefinition"
]
```

### 4. Pillar Research Log Schema

**File:** `pillar_research_log.json` (initial template)

```json
{
  "schema_version": "1.0.0",
  "last_updated": "2025-12-19T00:00:00Z",
  
  "pillars": {
    "Pillar 1: Biological Stimulus-Response": {
      "status": "active",
      "research_start_date": null,
      "last_evidence_date": null,
      "total_papers_reviewed": 0,
      "current_completeness": 0.0,
      "research_velocity": {
        "papers_per_month": 0.0,
        "completeness_gain_per_month": 0.0
      },
      "saturation_analysis": {
        "saturation_level": "unknown",
        "saturation_score": 0.0,
        "interpretation": "",
        "last_novel_finding_date": null,
        "open_questions": []
      },
      "research_focus_areas": [],
      "modification_proposals": [],
      "notes": ""
    }
  },
  
  "modification_log": [],
  
  "research_cycles": []
}
```

### 5. Stakeholder Definitions Schema

**File:** `stakeholder_definitions.json` (initial template)

```json
{
  "schema_version": "1.0.0",
  "last_updated": "2025-12-19T00:00:00Z",
  
  "stakeholder_categories": {
    "hardware_engineers": {
      "name": "Hardware Engineers",
      "description": "Engineers implementing neuromorphic chips and hardware",
      "primary_pillars": ["Pillar 2", "Pillar 4", "Pillar 6"],
      "key_requirements": [],
      "impact_areas": [
        "Validated efficiency metrics",
        "Hardware-specific benchmarks",
        "Deployment architectures"
      ],
      "contact_groups": []
    },
    "neuroscientists": {
      "name": "Neuroscientists",
      "description": "Researchers studying biological neural systems",
      "primary_pillars": ["Pillar 1", "Pillar 3", "Pillar 5"],
      "key_requirements": [],
      "impact_areas": [
        "Biological validation of models",
        "Experimental protocols",
        "Neural mechanism understanding"
      ],
      "contact_groups": []
    },
    "ml_practitioners": {
      "name": "ML Practitioners",
      "description": "ML engineers building practical SNN systems",
      "primary_pillars": ["Pillar 2", "Pillar 4", "Pillar 7"],
      "key_requirements": [],
      "impact_areas": [
        "Reproducible training pipelines",
        "Benchmark performance",
        "Framework integration"
      ],
      "contact_groups": []
    },
    "system_integrators": {
      "name": "System Integrators",
      "description": "Engineers building complete neuromorphic systems",
      "primary_pillars": ["Pillar 7"],
      "key_requirements": [],
      "impact_areas": [
        "Cross-pillar protocols",
        "Integration standards",
        "System-level validation"
      ],
      "contact_groups": []
    }
  },
  
  "gap_stakeholder_mappings": []
}
```

### 6. Enhanced Pillar Definitions Migration Script

**File:** `scripts/migrate_pillar_definitions.py`

```python
#!/usr/bin/env python3
"""
Migrate pillar_definitions_enhanced.json to include benchmark linkage.

This script:
1. Backs up the existing file
2. Restructures quantitative_metrics with benchmark linkage
3. Adds validation_strategy placeholders to requirements
4. Validates the output schema
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def backup_file(filepath: Path) -> Path:
    """Create timestamped backup of file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = filepath.with_suffix(f".backup_{timestamp}.json")
    shutil.copy(filepath, backup_path)
    print(f"✅ Backed up to: {backup_path}")
    return backup_path


def migrate_quantitative_metrics(metrics: Dict) -> Dict:
    """
    Migrate flat metrics to benchmark-linked structure.
    
    Before:
        {"latency_target": "< 10ms end-to-end"}
    
    After:
        {"latency_target": {
            "target_value": "< 10ms end-to-end",
            "measurement_method": "",
            "benchmarks": [],
            "benchmark_status": "no_benchmark",
            "validation_evidence": []
        }}
    """
    migrated = {}
    
    for metric_name, value in metrics.items():
        if isinstance(value, str):
            # Old format - migrate
            migrated[metric_name] = {
                "target_value": value,
                "measurement_method": "",
                "benchmarks": [],
                "benchmark_status": "no_benchmark",
                "validation_evidence": []
            }
        elif isinstance(value, dict):
            # Already new format or partially migrated
            migrated[metric_name] = {
                "target_value": value.get("target_value", str(value)),
                "measurement_method": value.get("measurement_method", ""),
                "benchmarks": value.get("benchmarks", []),
                "benchmark_status": value.get("benchmark_status", "no_benchmark"),
                "validation_evidence": value.get("validation_evidence", [])
            }
        else:
            # Unknown format - preserve as-is with wrapper
            migrated[metric_name] = {
                "target_value": str(value),
                "measurement_method": "",
                "benchmarks": [],
                "benchmark_status": "no_benchmark",
                "validation_evidence": []
            }
    
    return migrated


def add_validation_strategies(requirements: Dict) -> Dict:
    """
    Add validation_strategy placeholders to requirements.
    
    Transforms:
        ["Sub-1.1.1: Description", "Sub-1.1.2: Description"]
    
    To:
        [
            {
                "id": "Sub-1.1.1",
                "text": "Description",
                "validation_strategy": {...}
            }
        ]
    """
    migrated = {}
    
    for req_key, sub_reqs in requirements.items():
        if isinstance(sub_reqs, list):
            migrated_subs = []
            for sub_req in sub_reqs:
                if isinstance(sub_req, str):
                    # Parse "Sub-X.X.X: Description" format
                    if ": " in sub_req:
                        parts = sub_req.split(": ", 1)
                        sub_id = parts[0]
                        sub_text = parts[1] if len(parts) > 1 else ""
                    else:
                        sub_id = sub_req
                        sub_text = sub_req
                    
                    migrated_subs.append({
                        "id": sub_id,
                        "text": sub_text,
                        "validation_strategy": {
                            "method": "",
                            "benchmark_protocol": "",
                            "acceptance_criteria": "",
                            "required_evidence_types": [],
                            "status": "no_strategy"
                        }
                    })
                elif isinstance(sub_req, dict):
                    # Already structured - ensure validation_strategy exists
                    if "validation_strategy" not in sub_req:
                        sub_req["validation_strategy"] = {
                            "method": "",
                            "benchmark_protocol": "",
                            "acceptance_criteria": "",
                            "required_evidence_types": [],
                            "status": "no_strategy"
                        }
                    migrated_subs.append(sub_req)
            
            migrated[req_key] = migrated_subs
        else:
            migrated[req_key] = sub_reqs
    
    return migrated


def migrate_pillar(pillar_data: Dict) -> Dict:
    """Migrate a single pillar's data."""
    migrated = pillar_data.copy()
    
    # Migrate quantitative_metrics
    if "quantitative_metrics" in migrated:
        migrated["quantitative_metrics"] = migrate_quantitative_metrics(
            migrated["quantitative_metrics"]
        )
    
    # Add validation strategies to requirements
    if "requirements" in migrated:
        migrated["requirements"] = add_validation_strategies(
            migrated["requirements"]
        )
    
    return migrated


def migrate_pillar_definitions(input_path: str, output_path: str = None) -> Dict:
    """
    Main migration function.
    
    Args:
        input_path: Path to existing pillar_definitions_enhanced.json
        output_path: Path for migrated file (default: overwrite input)
    
    Returns:
        Migrated data dictionary
    """
    input_path = Path(input_path)
    output_path = Path(output_path) if output_path else input_path
    
    # Backup original
    backup_file(input_path)
    
    # Load existing data
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📖 Loaded {len(data)} top-level keys")
    
    # Migrate each pillar
    migrated = {}
    for key, value in data.items():
        if key.startswith("Pillar") or key in ["Cross_Cutting_Requirements", "Success_Criteria"]:
            if isinstance(value, dict):
                migrated[key] = migrate_pillar(value)
                print(f"  ✅ Migrated: {key}")
            else:
                migrated[key] = value
        else:
            # Preserve non-pillar keys (Framework_Overview, etc.)
            migrated[key] = value
    
    # Add schema version
    migrated["_schema_version"] = "2.0.0"
    migrated["_migrated_at"] = datetime.now().isoformat()
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(migrated, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Wrote migrated file to: {output_path}")
    
    return migrated


if __name__ == "__main__":
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else "pillar_definitions_enhanced.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    migrate_pillar_definitions(input_file, output_file)
```

---

## Unit Tests

**File:** `tests/unit/test_models.py`

```python
"""Unit tests for operationalization data models."""

import pytest
from datetime import datetime

from literature_review.models import (
    ActionVector,
    ActionType,
    EffortLevel,
    ResourceRequirements,
    ReproducibilityInfo,
    ActionChainPosition,
    generate_action_id,
    ValidationStrategy,
    ValidationStatus,
    EvidenceType,
    BenchmarkLink,
    MetricDefinition
)


class TestActionVector:
    """Tests for ActionVector dataclass."""
    
    def test_create_basic_action_vector(self):
        """Test creating a basic action vector."""
        av = ActionVector(
            action_id="AV-P2-001",
            pillar="Pillar 2: AI Stimulus-Response",
            requirement_id="REQ-A2.1",
            action_description="Implement DVS sensor integration"
        )
        
        assert av.action_id == "AV-P2-001"
        assert av.pillar == "Pillar 2: AI Stimulus-Response"
        assert av.action_type == ActionType.IMPLEMENT
        assert av.status == "pending"
    
    def test_reproducibility_score_calculation(self):
        """Test reproducibility score calculation."""
        repro = ReproducibilityInfo(
            code_available=True,
            data_available=True,
            hyperparameters_specified=True,
            methodology_detail_level="high"
        )
        
        assert repro.reproducibility_score == 1.0
    
    def test_reproducibility_score_partial(self):
        """Test partial reproducibility score."""
        repro = ReproducibilityInfo(
            code_available=True,
            data_available=False,
            hyperparameters_specified=False,
            methodology_detail_level="low"
        )
        
        assert repro.reproducibility_score == 0.35
    
    def test_action_vector_to_dict(self):
        """Test serialization to dictionary."""
        av = ActionVector(
            action_id="AV-P2-001",
            pillar="Pillar 2",
            requirement_id="REQ-A2.1",
            action_description="Test action",
            source_papers=["paper1.pdf", "paper2.pdf"]
        )
        
        data = av.to_dict()
        
        assert data["action_id"] == "AV-P2-001"
        assert data["source_papers"] == ["paper1.pdf", "paper2.pdf"]
        assert "is_actionable" in data
        assert "is_reproducible" in data
    
    def test_action_vector_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "action_id": "AV-P2-001",
            "pillar": "Pillar 2",
            "requirement_id": "REQ-A2.1",
            "action_type": "validate",
            "action_description": "Test action",
            "evidence_strength": 0.85
        }
        
        av = ActionVector.from_dict(data)
        
        assert av.action_id == "AV-P2-001"
        assert av.action_type == ActionType.VALIDATE
        assert av.evidence_strength == 0.85
    
    def test_is_actionable_true(self):
        """Test actionable check when no blockers."""
        av = ActionVector(
            action_id="AV-P2-001",
            pillar="Pillar 2",
            requirement_id="REQ-A2.1"
        )
        
        assert av.is_actionable is True
    
    def test_is_actionable_false_with_unknowns(self):
        """Test actionable check when blocking unknowns exist."""
        av = ActionVector(
            action_id="AV-P2-001",
            pillar="Pillar 2",
            requirement_id="REQ-A2.1",
            chain_position=ActionChainPosition(
                blocking_unknowns=["What hardware to use?"]
            )
        )
        
        assert av.is_actionable is False


class TestGenerateActionId:
    """Tests for action ID generation."""
    
    def test_generate_basic_id(self):
        """Test basic ID generation."""
        action_id = generate_action_id(
            pillar="Pillar 2: AI Stimulus-Response",
            requirement_id="REQ-A2.1",
            sequence=1
        )
        
        assert action_id.startswith("AV-P2-")
        assert action_id.endswith("-001")
    
    def test_generate_sequential_ids(self):
        """Test sequential ID generation."""
        id1 = generate_action_id("Pillar 2", "REQ-A2.1", 1)
        id2 = generate_action_id("Pillar 2", "REQ-A2.1", 2)
        
        assert id1 != id2
        assert id1.endswith("-001")
        assert id2.endswith("-002")


class TestValidationStrategy:
    """Tests for ValidationStrategy dataclass."""
    
    def test_create_basic_strategy(self):
        """Test creating a basic validation strategy."""
        vs = ValidationStrategy(
            requirement_id="Sub-1.1.1",
            requirement_text="Test requirement",
            pillar="Pillar 1"
        )
        
        assert vs.requirement_id == "Sub-1.1.1"
        assert vs.status == ValidationStatus.NO_STRATEGY
        assert vs.is_strategy_defined is False
    
    def test_strategy_defined_with_method(self):
        """Test is_strategy_defined with method."""
        vs = ValidationStrategy(
            requirement_id="Sub-1.1.1",
            requirement_text="Test requirement",
            pillar="Pillar 1",
            validation_method="fMRI comparison"
        )
        
        assert vs.is_strategy_defined is True
    
    def test_is_fully_validated(self):
        """Test fully validated check."""
        vs = ValidationStrategy(
            requirement_id="Sub-1.1.1",
            requirement_text="Test requirement",
            pillar="Pillar 1",
            validation_method="fMRI comparison",
            status=ValidationStatus.VALIDATED,
            evidence_papers=["paper1.pdf"],
            minimum_evidence_count=1
        )
        
        assert vs.is_fully_validated is True
    
    def test_serialization_roundtrip(self):
        """Test to_dict and from_dict roundtrip."""
        vs = ValidationStrategy(
            requirement_id="Sub-1.1.1",
            requirement_text="Test requirement",
            pillar="Pillar 1",
            validation_method="fMRI comparison",
            required_evidence_types=[EvidenceType.EXPERIMENTAL]
        )
        
        data = vs.to_dict()
        vs2 = ValidationStrategy.from_dict(data)
        
        assert vs.requirement_id == vs2.requirement_id
        assert vs.validation_method == vs2.validation_method


class TestBenchmarkLink:
    """Tests for BenchmarkLink dataclass."""
    
    def test_create_benchmark_link(self):
        """Test creating a benchmark link."""
        bl = BenchmarkLink(
            benchmark_name="DVS128 Gesture",
            benchmark_type="dataset",
            metric_measured="accuracy",
            measurement_method="Top-1 classification accuracy"
        )
        
        assert bl.benchmark_name == "DVS128 Gesture"
        assert bl.benchmark_type == "dataset"
    
    def test_serialization(self):
        """Test serialization."""
        bl = BenchmarkLink(
            benchmark_name="N-MNIST",
            benchmark_type="dataset",
            metric_measured="inference_time",
            measurement_method="Wall-clock time"
        )
        
        data = bl.to_dict()
        
        assert data["benchmark_name"] == "N-MNIST"
        assert data["benchmark_type"] == "dataset"


class TestMetricDefinition:
    """Tests for MetricDefinition dataclass."""
    
    def test_create_metric_with_benchmarks(self):
        """Test creating a metric with benchmarks."""
        md = MetricDefinition(
            metric_id="P2-M1",
            metric_name="latency_target",
            target_value="< 10ms end-to-end",
            measurement_method="End-to-end timing",
            benchmarks=[
                BenchmarkLink(
                    benchmark_name="DVS128 Gesture",
                    benchmark_type="dataset",
                    metric_measured="latency",
                    measurement_method="Wall-clock time"
                )
            ],
            benchmark_status="covered"
        )
        
        assert md.metric_name == "latency_target"
        assert len(md.benchmarks) == 1
        assert md.benchmark_status == "covered"
```

---

## Acceptance Criteria Checklist

- [ ] All dataclasses created with full field definitions
- [ ] Serialization (to_dict) works for all dataclasses
- [ ] Deserialization (from_dict) works for all dataclasses
- [ ] Property methods (is_actionable, is_reproducible, etc.) work correctly
- [ ] Action ID generation produces unique, parseable IDs
- [ ] Pillar definitions migration script runs without errors
- [ ] Migration creates backup before modifying
- [ ] Schema files are valid JSON
- [ ] Unit tests pass (>95% coverage for new code)
- [ ] Type hints are complete and correct

---

## Rollback Plan

If issues are discovered:

1. **Pillar Definitions:**
   - Backup files are created with timestamps
   - Restore: `cp pillar_definitions_enhanced.backup_*.json pillar_definitions_enhanced.json`

2. **New Files:**
   - Simply delete new model files if needed
   - No existing functionality depends on them yet

3. **Git:**
   - All changes in single commit for easy revert
   - `git revert <commit>` if needed

---

## Notes for Agent

1. **Create Directory First:**
   ```bash
   mkdir -p literature_review/models
   ```

2. **Run Tests After Creation:**
   ```bash
   pytest tests/unit/test_models.py -v
   ```

3. **Validate JSON Schemas:**
   ```bash
   python -c "import json; json.load(open('pillar_research_log.json'))"
   python -c "import json; json.load(open('stakeholder_definitions.json'))"
   ```

4. **Do NOT run migration script yet:**
   - Migration is optional for initial development
   - Will be run when Wave 2 needs the enhanced structure
