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
