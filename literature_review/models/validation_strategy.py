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
