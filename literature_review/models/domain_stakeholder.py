"""
Domain Stakeholder Models - Stakeholder impacts as stated in research literature.

This module defines data structures for capturing explicit statements from papers
that link research gaps to affected stakeholders.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class StakeholderCategory(Enum):
    """Broad categories for domain stakeholders."""
    RESEARCHER = "researcher"           # Academic researchers
    ENGINEER = "engineer"               # Hardware/software engineers
    CLINICIAN = "clinician"             # Medical/clinical professionals
    PRACTITIONER = "practitioner"       # Industry practitioners
    POLICY_MAKER = "policy_maker"       # Policy/regulatory bodies
    END_USER = "end_user"               # End users of systems
    OTHER = "other"


@dataclass
class DomainStakeholder:
    """
    A stakeholder type as mentioned in research literature.
    
    This represents a domain-specific stakeholder (e.g., "neuroscientists",
    "hardware engineers") as explicitly mentioned in papers, distinct from
    organizational stakeholders (internal team roles).
    """
    stakeholder_type: str           # e.g., "neuroscientists", "hardware engineers"
    category: StakeholderCategory   # Broad category
    description: str                # Context from paper
    source_papers: List[str] = field(default_factory=list)  # Papers mentioning this stakeholder
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "stakeholder_type": self.stakeholder_type,
            "category": self.category.value,
            "description": self.description,
            "source_papers": self.source_papers
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DomainStakeholder":
        """Deserialize from dictionary."""
        return cls(
            stakeholder_type=data["stakeholder_type"],
            category=StakeholderCategory(data.get("category", "other")),
            description=data.get("description", ""),
            source_papers=data.get("source_papers", [])
        )


@dataclass
class LiteratureStakeholderImpact:
    """
    A stakeholder impact as stated in research literature.
    
    Captures the explicit statement from a paper that a specific gap
    affects a specific stakeholder type.
    
    Attributes:
        impact_id: Unique identifier for this impact
        gap_id: Links to gap analysis
        gap_description: Gap as stated in paper
        affected_stakeholder: Stakeholder type as stated (e.g., "neuroscientists")
        stakeholder_category: Broad category for the stakeholder
        impact_statement: How the gap affects the stakeholder
        source_quote: Direct quote if available
        source_paper: Paper filename
        paper_section: Where in paper (e.g., "Discussion")
        extraction_confidence: 0-1 confidence score
        gap_filled: Updated when gap is closed
        filled_by_paper: Paper that filled the gap
        filled_date: Date when gap was filled
    """
    impact_id: str                      # Unique identifier
    
    # Gap information
    gap_id: str                         # Links to gap analysis
    gap_description: str                # Gap as stated in paper
    
    # Stakeholder information
    affected_stakeholder: str           # Stakeholder type as stated (e.g., "neuroscientists")
    stakeholder_category: StakeholderCategory
    
    # Impact details
    impact_statement: str               # How the gap affects the stakeholder
    source_quote: Optional[str] = None  # Direct quote if available
    
    # Provenance
    source_paper: str = ""              # Paper filename
    paper_section: Optional[str] = None # Where in paper (e.g., "Discussion")
    extraction_confidence: float = 0.8  # 0-1 confidence score
    
    # Resolution tracking
    gap_filled: bool = False            # Updated when gap is closed
    filled_by_paper: Optional[str] = None  # Paper that filled the gap
    filled_date: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "impact_id": self.impact_id,
            "gap_id": self.gap_id,
            "gap_description": self.gap_description,
            "affected_stakeholder": self.affected_stakeholder,
            "stakeholder_category": self.stakeholder_category.value,
            "impact_statement": self.impact_statement,
            "source_quote": self.source_quote,
            "source_paper": self.source_paper,
            "paper_section": self.paper_section,
            "extraction_confidence": self.extraction_confidence,
            "gap_filled": self.gap_filled,
            "filled_by_paper": self.filled_by_paper,
            "filled_date": self.filled_date
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "LiteratureStakeholderImpact":
        """Deserialize from dictionary."""
        return cls(
            impact_id=data["impact_id"],
            gap_id=data["gap_id"],
            gap_description=data["gap_description"],
            affected_stakeholder=data["affected_stakeholder"],
            stakeholder_category=StakeholderCategory(data.get("stakeholder_category", "other")),
            impact_statement=data["impact_statement"],
            source_quote=data.get("source_quote"),
            source_paper=data.get("source_paper", ""),
            paper_section=data.get("paper_section"),
            extraction_confidence=data.get("extraction_confidence", 0.8),
            gap_filled=data.get("gap_filled", False),
            filled_by_paper=data.get("filled_by_paper"),
            filled_date=data.get("filled_date")
        )
    
    def mark_resolved(self, filled_by_paper: str, filled_date: str) -> None:
        """Mark this impact as resolved when gap is filled."""
        self.gap_filled = True
        self.filled_by_paper = filled_by_paper
        self.filled_date = filled_date


def generate_impact_id(source_paper: str, gap_id: str, stakeholder: str, sequence: int) -> str:
    """
    Generate a unique impact ID.
    
    Format: LSI-{paper_short}-{sequence:03d}
    Example: LSI-snn_review-001
    """
    # Shorten paper name
    paper_short = source_paper.replace(".pdf", "").replace(".html", "")[:10]
    paper_short = "".join(c for c in paper_short if c.isalnum() or c == "_")
    
    return f"LSI-{paper_short}-{sequence:03d}"
