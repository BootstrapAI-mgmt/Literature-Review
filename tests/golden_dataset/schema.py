"""
Golden Dataset Schema Definitions

Defines schemas for golden dataset entries used in validation testing.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class GoldenClaim:
    """Schema for a golden dataset claim."""
    claim_id: str
    pillar: str
    sub_requirement: str
    claim_text: str
    evidence_text: str
    expected_verdict: str  # "approved" or "rejected"
    expected_reasoning: Optional[str] = None
    evidence_quality_scores: Dict[str, float] = field(default_factory=dict)
    source_paper: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "claim_id": self.claim_id,
            "pillar": self.pillar,
            "sub_requirement": self.sub_requirement,
            "claim_text": self.claim_text,
            "evidence_text": self.evidence_text,
            "expected_verdict": self.expected_verdict,
            "expected_reasoning": self.expected_reasoning,
            "evidence_quality_scores": self.evidence_quality_scores,
            "source_paper": self.source_paper,
            "metadata": self.metadata
        }


@dataclass
class GoldenVerdict:
    """Schema for a golden dataset verdict."""
    verdict_id: str
    claim_id: str
    verdict: str  # "approved" or "rejected"
    reasoning: str
    confidence: float
    judge_model: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "verdict_id": self.verdict_id,
            "claim_id": self.claim_id,
            "verdict": self.verdict,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "judge_model": self.judge_model,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class GoldenGap:
    """Schema for a golden dataset gap analysis entry."""
    gap_id: str
    pillar: str
    sub_requirement: str
    gap_description: str
    severity: str  # "critical", "high", "medium", "low"
    suggested_searches: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "gap_id": self.gap_id,
            "pillar": self.pillar,
            "sub_requirement": self.sub_requirement,
            "gap_description": self.gap_description,
            "severity": self.severity,
            "suggested_searches": self.suggested_searches,
            "metadata": self.metadata
        }


@dataclass 
class GoldenDataset:
    """Container for a complete golden dataset."""
    name: str
    version: str
    description: str
    claims: List[GoldenClaim] = field(default_factory=list)
    verdicts: List[GoldenVerdict] = field(default_factory=list)
    gaps: List[GoldenGap] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "claims": [c.to_dict() for c in self.claims],
            "verdicts": [v.to_dict() for v in self.verdicts],
            "gaps": [g.to_dict() for g in self.gaps],
            "created_at": self.created_at,
            "metadata": self.metadata
        }
