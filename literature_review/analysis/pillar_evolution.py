"""
Pillar Evolution System

Manages modification proposals, review workflows, and version tracking
for pillar definition evolution based on research evidence.
"""

import json
import logging
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from pathlib import Path
from datetime import datetime
from enum import Enum
from copy import deepcopy

logger = logging.getLogger(__name__)


class ProposalStatus(Enum):
    """Status of a modification proposal."""
    DRAFT = "draft"               # Initial creation, not submitted
    PROPOSED = "proposed"         # Submitted for review
    UNDER_REVIEW = "under_review" # Being reviewed
    APPROVED = "approved"         # Approved, ready to apply
    REJECTED = "rejected"         # Rejected with feedback
    APPLIED = "applied"           # Successfully applied
    SUPERSEDED = "superseded"     # Replaced by newer proposal


class ModificationType(Enum):
    """Type of modification to pillar definition."""
    ADD_REQUIREMENT = "add_requirement"
    MODIFY_REQUIREMENT = "modify_requirement"
    REMOVE_REQUIREMENT = "remove_requirement"
    ADD_VALIDATION = "add_validation"
    MODIFY_VALIDATION = "modify_validation"
    ADD_METRIC = "add_metric"
    MODIFY_METRIC = "modify_metric"
    REFINE_SCOPE = "refine_scope"


@dataclass
class EvidenceReference:
    """Reference to supporting evidence for a proposal."""
    paper_id: str
    claim_text: str
    relevance_score: float = 0.0
    claim_approved: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ImpactAssessment:
    """Assessment of impact from proposed change."""
    affected_requirements: List[str] = field(default_factory=list)
    evidence_to_remap: List[str] = field(default_factory=list)
    coverage_change_estimate: float = 0.0  # Estimated change in %
    risk_level: str = "low"  # low, medium, high
    migration_notes: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ReviewComment:
    """A review comment on a proposal."""
    comment_id: str
    reviewer: str
    timestamp: str
    comment: str
    decision: Optional[str] = None  # approve, reject, request_changes
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ModificationProposal:
    """
    A proposal to modify pillar definitions.
    
    Captures:
    - What to change
    - Why (evidence)
    - Impact assessment
    - Review status
    """
    proposal_id: str
    title: str
    description: str
    
    # Target
    target_pillar: str
    target_requirement: str = ""  # Optional: specific requirement
    modification_type: ModificationType = ModificationType.MODIFY_REQUIREMENT
    
    # Proposed change
    current_value: str = ""
    proposed_value: str = ""
    
    # For new additions
    new_requirement_id: str = ""
    new_requirement_text: str = ""
    
    # Evidence
    supporting_evidence: List[EvidenceReference] = field(default_factory=list)
    evidence_summary: str = ""
    
    # Impact
    impact_assessment: ImpactAssessment = field(default_factory=ImpactAssessment)
    
    # Status tracking
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "system"
    
    # Review
    review_comments: List[ReviewComment] = field(default_factory=list)
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    
    # Version tracking
    applies_to_version: str = ""  # Version of pillar defs this applies to
    resulting_version: str = ""   # Version after applying
    
    def to_dict(self) -> Dict:
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "description": self.description,
            "target_pillar": self.target_pillar,
            "target_requirement": self.target_requirement,
            "modification_type": self.modification_type.value,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "new_requirement_id": self.new_requirement_id,
            "new_requirement_text": self.new_requirement_text,
            "supporting_evidence": [e.to_dict() for e in self.supporting_evidence],
            "evidence_summary": self.evidence_summary,
            "impact_assessment": self.impact_assessment.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "review_comments": [c.to_dict() for c in self.review_comments],
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "applies_to_version": self.applies_to_version,
            "resulting_version": self.resulting_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModificationProposal':
        """Create from dictionary."""
        evidence = [
            EvidenceReference(**e) for e in data.get("supporting_evidence", [])
        ]
        impact = ImpactAssessment(**data.get("impact_assessment", {}))
        comments = [
            ReviewComment(**c) for c in data.get("review_comments", [])
        ]
        
        return cls(
            proposal_id=data["proposal_id"],
            title=data["title"],
            description=data["description"],
            target_pillar=data["target_pillar"],
            target_requirement=data.get("target_requirement", ""),
            modification_type=ModificationType(data.get("modification_type", "modify_requirement")),
            current_value=data.get("current_value", ""),
            proposed_value=data.get("proposed_value", ""),
            new_requirement_id=data.get("new_requirement_id", ""),
            new_requirement_text=data.get("new_requirement_text", ""),
            supporting_evidence=evidence,
            evidence_summary=data.get("evidence_summary", ""),
            impact_assessment=impact,
            status=ProposalStatus(data.get("status", "draft")),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            created_by=data.get("created_by", "system"),
            review_comments=comments,
            approved_by=data.get("approved_by"),
            approved_at=data.get("approved_at"),
            applies_to_version=data.get("applies_to_version", ""),
            resulting_version=data.get("resulting_version", "")
        )


class PillarEvolutionManager:
    """
    Manage pillar definition evolution through proposals.
    
    Provides:
    1. Proposal generation from research findings
    2. Review workflow management
    3. Version tracking for pillar definitions
    4. Impact analysis for changes
    """
    
    def __init__(
        self,
        pillar_definitions_path: str,
        proposals_path: Optional[str] = None
    ):
        """
        Initialize evolution manager.
        
        Args:
            pillar_definitions_path: Path to pillar definitions
            proposals_path: Optional path to existing proposals
        """
        self.pillar_definitions_path = pillar_definitions_path
        
        with open(pillar_definitions_path, 'r', encoding='utf-8') as f:
            self.pillar_definitions = json.load(f)
        
        self.proposals: Dict[str, ModificationProposal] = {}
        self.version_history: List[Dict] = []
        
        # Calculate current version
        self.current_version = self._calculate_version(self.pillar_definitions)
        
        # Load existing proposals
        if proposals_path and Path(proposals_path).exists():
            self._load_proposals(proposals_path)
    
    def _calculate_version(self, definitions: Dict) -> str:
        """Calculate version hash for definitions."""
        content = json.dumps(definitions, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def _load_proposals(self, path: str):
        """Load existing proposals."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for proposal_data in data.get("proposals", []):
            proposal = ModificationProposal.from_dict(proposal_data)
            self.proposals[proposal.proposal_id] = proposal
        
        self.version_history = data.get("version_history", [])
    
    def generate_proposal_from_gap(
        self,
        gap_analysis: Dict,
        requirement_id: str,
        proposal_type: str = "add_validation"
    ) -> ModificationProposal:
        """
        Generate a proposal based on gap analysis findings.
        
        Args:
            gap_analysis: Gap analysis report
            requirement_id: Requirement to create proposal for
            proposal_type: Type of proposal to generate
        
        Returns:
            Generated proposal
        """
        # Find requirement in gap analysis
        target_pillar = ""
        current_data = {}
        evidence = []
        
        for pillar_name, pillar_data in gap_analysis.items():
            analysis = pillar_data.get("analysis", {})
            for req_name, req_data in analysis.items():
                if isinstance(req_data, dict):
                    for sub_name, sub_data in req_data.items():
                        if requirement_id in sub_name:
                            target_pillar = pillar_name
                            current_data = sub_data
                            
                            # Collect evidence
                            for paper in sub_data.get("contributing_papers", []):
                                paper_id = paper.get("filename", paper) if isinstance(paper, dict) else paper
                                evidence.append(EvidenceReference(
                                    paper_id=paper_id,
                                    claim_text=f"Evidence from {paper_id}",
                                    relevance_score=0.8
                                ))
        
        # Generate proposal ID
        proposal_id = self._generate_unique_proposal_id()
        
        # Create proposal based on type
        mod_type = ModificationType.ADD_VALIDATION
        if proposal_type == "add_requirement":
            mod_type = ModificationType.ADD_REQUIREMENT
        elif proposal_type == "modify_requirement":
            mod_type = ModificationType.MODIFY_REQUIREMENT
        
        proposal = ModificationProposal(
            proposal_id=proposal_id,
            title=f"Update {requirement_id} based on research evidence",
            description=f"Proposal to update {requirement_id} based on {len(evidence)} papers",
            target_pillar=target_pillar,
            target_requirement=requirement_id,
            modification_type=mod_type,
            current_value=str(current_data.get("completeness_percent", 0)) + "% coverage",
            proposed_value="Add validation criteria from evidence",
            supporting_evidence=evidence,
            evidence_summary=f"Based on {len(evidence)} papers with total coverage {current_data.get('completeness_percent', 0)}%",
            status=ProposalStatus.DRAFT,
            applies_to_version=self.current_version
        )
        
        # Assess impact
        proposal.impact_assessment = self._assess_impact(proposal)
        
        # Store proposal
        self.proposals[proposal_id] = proposal
        
        return proposal
    
    def create_custom_proposal(
        self,
        title: str,
        description: str,
        target_pillar: str,
        modification_type: ModificationType,
        proposed_value: str,
        target_requirement: str = "",
        current_value: str = "",
        new_requirement_id: str = "",
        new_requirement_text: str = "",
        created_by: str = "user"
    ) -> ModificationProposal:
        """
        Create a custom modification proposal.
        
        Args:
            title: Proposal title
            description: Proposal description
            target_pillar: Target pillar name
            modification_type: Type of modification
            proposed_value: Proposed new value
            target_requirement: Optional target requirement
            current_value: Current value being changed
            new_requirement_id: ID for new requirement (for ADD_REQUIREMENT, ADD_METRIC)
            new_requirement_text: Text for new requirement
            created_by: Creator identifier
        
        Returns:
            Created proposal
        """
        proposal_id = self._generate_unique_proposal_id()
        
        proposal = ModificationProposal(
            proposal_id=proposal_id,
            title=title,
            description=description,
            target_pillar=target_pillar,
            target_requirement=target_requirement,
            modification_type=modification_type,
            current_value=current_value,
            proposed_value=proposed_value,
            new_requirement_id=new_requirement_id,
            new_requirement_text=new_requirement_text,
            status=ProposalStatus.DRAFT,
            created_by=created_by,
            applies_to_version=self.current_version
        )
        
        proposal.impact_assessment = self._assess_impact(proposal)
        self.proposals[proposal_id] = proposal
        
        return proposal
    
    def _generate_unique_proposal_id(self) -> str:
        """Generate a unique proposal ID."""
        base_id = f"PROP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Handle case where multiple proposals created in same second
        if base_id not in self.proposals:
            return base_id
        
        # Add suffix for uniqueness
        suffix = 1
        while f"{base_id}-{suffix}" in self.proposals:
            suffix += 1
        
        return f"{base_id}-{suffix}"
    
    def _assess_impact(self, proposal: ModificationProposal) -> ImpactAssessment:
        """Assess impact of a proposed change."""
        affected = []
        evidence_to_remap = []
        risk = "low"
        coverage_change = 0.0
        
        # Find affected requirements
        for pillar_name, pillar_data in self.pillar_definitions.items():
            if proposal.target_pillar in pillar_name:
                requirements = pillar_data.get("requirements", {})
                for req_name, sub_reqs in requirements.items():
                    if proposal.target_requirement in req_name:
                        affected.append(req_name)
                        
                        # If modifying, need to remap evidence
                        if proposal.modification_type == ModificationType.MODIFY_REQUIREMENT:
                            for evidence in proposal.supporting_evidence:
                                evidence_to_remap.append(evidence.paper_id)
        
        # Assess risk level
        if len(affected) > 3:
            risk = "high"
        elif len(affected) > 1:
            risk = "medium"
        
        if proposal.modification_type == ModificationType.REMOVE_REQUIREMENT:
            risk = "high"
        
        # Estimate coverage change
        if proposal.modification_type == ModificationType.ADD_REQUIREMENT:
            coverage_change = -5.0  # New requirement will lower coverage initially
        elif proposal.modification_type == ModificationType.ADD_VALIDATION:
            coverage_change = 0.0  # No immediate coverage change
        
        migration_notes = ""
        if evidence_to_remap:
            migration_notes = f"Need to remap evidence from {len(evidence_to_remap)} papers"
        
        return ImpactAssessment(
            affected_requirements=affected,
            evidence_to_remap=evidence_to_remap,
            coverage_change_estimate=coverage_change,
            risk_level=risk,
            migration_notes=migration_notes
        )
    
    def submit_for_review(self, proposal_id: str) -> ModificationProposal:
        """Submit a proposal for review."""
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        proposal = self.proposals[proposal_id]
        
        if proposal.status != ProposalStatus.DRAFT:
            raise ValueError(f"Can only submit DRAFT proposals, current: {proposal.status}")
        
        proposal.status = ProposalStatus.PROPOSED
        proposal.updated_at = datetime.now().isoformat()
        
        logger.info(f"Proposal {proposal_id} submitted for review")
        return proposal
    
    def start_review(self, proposal_id: str, reviewer: str) -> ModificationProposal:
        """Start reviewing a proposal."""
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        proposal = self.proposals[proposal_id]
        
        if proposal.status != ProposalStatus.PROPOSED:
            raise ValueError(f"Can only review PROPOSED proposals")
        
        proposal.status = ProposalStatus.UNDER_REVIEW
        proposal.updated_at = datetime.now().isoformat()
        
        # Add review start comment
        comment = ReviewComment(
            comment_id=f"CMT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            reviewer=reviewer,
            timestamp=datetime.now().isoformat(),
            comment="Review started"
        )
        proposal.review_comments.append(comment)
        
        logger.info(f"Review started for {proposal_id} by {reviewer}")
        return proposal
    
    def add_review_comment(
        self,
        proposal_id: str,
        reviewer: str,
        comment: str,
        decision: Optional[str] = None
    ) -> ModificationProposal:
        """Add a review comment to a proposal."""
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        proposal = self.proposals[proposal_id]
        
        review_comment = ReviewComment(
            comment_id=f"CMT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            reviewer=reviewer,
            timestamp=datetime.now().isoformat(),
            comment=comment,
            decision=decision
        )
        proposal.review_comments.append(review_comment)
        proposal.updated_at = datetime.now().isoformat()
        
        return proposal
    
    def approve_proposal(
        self,
        proposal_id: str,
        approver: str,
        comment: str = ""
    ) -> ModificationProposal:
        """Approve a proposal."""
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        proposal = self.proposals[proposal_id]
        
        if proposal.status not in [ProposalStatus.PROPOSED, ProposalStatus.UNDER_REVIEW]:
            raise ValueError(f"Cannot approve proposal with status {proposal.status}")
        
        proposal.status = ProposalStatus.APPROVED
        proposal.approved_by = approver
        proposal.approved_at = datetime.now().isoformat()
        proposal.updated_at = datetime.now().isoformat()
        
        if comment:
            self.add_review_comment(proposal_id, approver, comment, "approve")
        
        logger.info(f"Proposal {proposal_id} approved by {approver}")
        return proposal
    
    def reject_proposal(
        self,
        proposal_id: str,
        reviewer: str,
        reason: str
    ) -> ModificationProposal:
        """Reject a proposal."""
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        proposal = self.proposals[proposal_id]
        
        if proposal.status not in [ProposalStatus.PROPOSED, ProposalStatus.UNDER_REVIEW]:
            raise ValueError(f"Cannot reject proposal with status {proposal.status}")
        
        proposal.status = ProposalStatus.REJECTED
        proposal.updated_at = datetime.now().isoformat()
        
        self.add_review_comment(proposal_id, reviewer, reason, "reject")
        
        logger.info(f"Proposal {proposal_id} rejected: {reason}")
        return proposal
    
    def apply_proposal(
        self,
        proposal_id: str,
        output_path: Optional[str] = None
    ) -> Tuple[Dict, str]:
        """
        Apply an approved proposal to pillar definitions.
        
        Args:
            proposal_id: ID of approved proposal
            output_path: Optional path to save updated definitions
        
        Returns:
            Tuple of (updated definitions, new version)
        """
        if proposal_id not in self.proposals:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        proposal = self.proposals[proposal_id]
        
        if proposal.status != ProposalStatus.APPROVED:
            raise ValueError(f"Can only apply APPROVED proposals")
        
        # Create copy of definitions
        updated = deepcopy(self.pillar_definitions)
        
        # Apply modification
        updated = self._apply_modification(updated, proposal)
        
        # Calculate new version
        new_version = self._calculate_version(updated)
        
        # Update proposal
        proposal.resulting_version = new_version
        proposal.status = ProposalStatus.APPLIED
        proposal.updated_at = datetime.now().isoformat()
        
        # Track version history
        self.version_history.append({
            "version": new_version,
            "previous_version": self.current_version,
            "applied_proposal": proposal_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Save if path provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(updated, f, indent=2, ensure_ascii=False)
            logger.info(f"Updated pillar definitions saved to {output_path}")
        
        # Update current version
        self.pillar_definitions = updated
        self.current_version = new_version
        
        return updated, new_version
    
    def _apply_modification(
        self,
        definitions: Dict,
        proposal: ModificationProposal
    ) -> Dict:
        """Apply a modification to definitions."""
        
        for pillar_name, pillar_data in definitions.items():
            if proposal.target_pillar in pillar_name:
                if proposal.modification_type == ModificationType.ADD_REQUIREMENT:
                    # Add new requirement
                    requirements = pillar_data.get("requirements", {})
                    
                    # Find the appropriate parent
                    for req_name in requirements:
                        if proposal.target_requirement in req_name:
                            sub_reqs = requirements[req_name]
                            if isinstance(sub_reqs, list):
                                sub_reqs.append({
                                    "id": proposal.new_requirement_id,
                                    "text": proposal.new_requirement_text
                                })
                            break
                
                elif proposal.modification_type == ModificationType.ADD_VALIDATION:
                    # Add validation criteria
                    validation = pillar_data.get("validation_criteria", {})
                    validation[proposal.target_requirement] = proposal.proposed_value
                    pillar_data["validation_criteria"] = validation
                
                elif proposal.modification_type == ModificationType.MODIFY_REQUIREMENT:
                    # Modify existing requirement
                    requirements = pillar_data.get("requirements", {})
                    for req_name, sub_reqs in requirements.items():
                        if isinstance(sub_reqs, list):
                            for i, sub_req in enumerate(sub_reqs):
                                if isinstance(sub_req, dict):
                                    if proposal.target_requirement in sub_req.get("id", ""):
                                        sub_req["text"] = proposal.proposed_value
                                elif proposal.target_requirement in sub_req:
                                    sub_reqs[i] = proposal.proposed_value
                
                elif proposal.modification_type == ModificationType.ADD_METRIC:
                    # Add metric definition
                    metrics = pillar_data.get("quantitative_metrics", {})
                    metrics[proposal.new_requirement_id] = proposal.proposed_value
                    pillar_data["quantitative_metrics"] = metrics
                
                break
        
        return definitions
    
    def get_proposals_by_status(
        self,
        status: ProposalStatus
    ) -> List[ModificationProposal]:
        """Get proposals filtered by status."""
        return [
            p for p in self.proposals.values()
            if p.status == status
        ]
    
    def get_pending_proposals(self) -> List[ModificationProposal]:
        """Get proposals pending review."""
        return self.get_proposals_by_status(ProposalStatus.PROPOSED)
    
    def get_approved_proposals(self) -> List[ModificationProposal]:
        """Get approved proposals ready to apply."""
        return self.get_proposals_by_status(ProposalStatus.APPROVED)
    
    def save_proposals(self, output_path: str) -> Dict:
        """Save all proposals to file."""
        output = {
            "timestamp": datetime.now().isoformat(),
            "current_pillar_version": self.current_version,
            "version_history": self.version_history,
            "proposals": [p.to_dict() for p in self.proposals.values()],
            "summary": {
                "total": len(self.proposals),
                "draft": len(self.get_proposals_by_status(ProposalStatus.DRAFT)),
                "proposed": len(self.get_proposals_by_status(ProposalStatus.PROPOSED)),
                "under_review": len(self.get_proposals_by_status(ProposalStatus.UNDER_REVIEW)),
                "approved": len(self.get_proposals_by_status(ProposalStatus.APPROVED)),
                "rejected": len(self.get_proposals_by_status(ProposalStatus.REJECTED)),
                "applied": len(self.get_proposals_by_status(ProposalStatus.APPLIED))
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.proposals)} proposals to {output_path}")
        return output
