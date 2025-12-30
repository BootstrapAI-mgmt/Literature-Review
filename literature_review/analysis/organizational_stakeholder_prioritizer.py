"""
Organizational Stakeholder Prioritization Matrix

Algorithmically maps research gaps to organizational stakeholder roles based on
pillar relevance, priority weights, and interest alignment. This provides guidance
for internal resource allocation and notification priorities.

NOTE: This is distinct from domain stakeholder impacts extracted directly from
research literature. See literature_review/analysis/domain_stakeholder_extractor.py
for extraction of stakeholder impacts as stated in papers.
"""

import json
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from pathlib import Path
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Completeness threshold constants
COMPLETE_THRESHOLD = 100  # Anything below this is considered a gap

# Severity threshold constants (based on completeness percentage)
SEVERITY_CRITICAL_THRESHOLD = 30  # < 30% completeness
SEVERITY_HIGH_THRESHOLD = 50      # 30-50% completeness  
SEVERITY_MEDIUM_THRESHOLD = 70    # 50-70% completeness
# > 70% completeness is considered LOW severity


class PriorityLevel(Enum):
    """Priority level for organizational stakeholder attention."""
    CRITICAL = "critical"      # Major priority for core interests
    HIGH = "high"              # Significant priority
    MEDIUM = "medium"          # Moderate priority
    LOW = "low"                # Minor priority
    NONE = "none"              # No direct priority


class NotificationPriority(Enum):
    """Priority for organizational stakeholder notification."""
    IMMEDIATE = "immediate"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    NONE = "none"


@dataclass
class OrganizationalStakeholder:
    """
    Organizational stakeholder definition.
    
    Represents internal team roles (e.g., Core Research, Engineering, Product)
    rather than domain stakeholders mentioned in research literature.
    """
    id: str
    name: str
    description: str
    priority_weight: float
    interests: List[str]
    primary_pillars: List[str]
    decision_authority: str = "medium"
    notification_threshold: str = "medium"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class OrganizationalGapPriority:
    """
    Priority of a gap for an organizational stakeholder.
    
    Represents algorithmically computed relevance of a gap to an
    organizational role, NOT extracted stakeholder impacts from literature.
    """
    gap_id: str
    gap_description: str
    pillar: str
    requirement: str
    
    org_stakeholder_id: str
    org_stakeholder_name: str
    
    priority_level: PriorityLevel = PriorityLevel.MEDIUM
    priority_score: float = 0.0  # 0-1
    
    interest_alignment: List[str] = field(default_factory=list)
    why_prioritized: str = ""
    
    notification_priority: NotificationPriority = NotificationPriority.MONTHLY
    action_required: bool = False
    recommended_action: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "gap_id": self.gap_id,
            "gap_description": self.gap_description,
            "pillar": self.pillar,
            "requirement": self.requirement,
            "org_stakeholder_id": self.org_stakeholder_id,
            "org_stakeholder_name": self.org_stakeholder_name,
            "priority_level": self.priority_level.value,
            "priority_score": self.priority_score,
            "interest_alignment": self.interest_alignment,
            "why_prioritized": self.why_prioritized,
            "notification_priority": self.notification_priority.value,
            "action_required": self.action_required,
            "recommended_action": self.recommended_action
        }


@dataclass
class OrganizationalStakeholderSummary:
    """Summary of all gaps prioritized for an organizational stakeholder."""
    org_stakeholder_id: str
    org_stakeholder_name: str
    
    total_priorities: int = 0
    critical_priorities: int = 0
    high_priorities: int = 0
    medium_priorities: int = 0
    
    most_prioritized_gaps: List[str] = field(default_factory=list)
    primary_pillar_gaps: Dict[str, int] = field(default_factory=dict)
    
    overall_priority_score: float = 0.0
    attention_required: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)


class OrganizationalStakeholderPrioritizer:
    """
    Algorithmically prioritize gaps for organizational stakeholders.
    
    This module maps research gaps to internal organizational roles based on:
    1. Pillar relevance to stakeholder focus areas
    2. Interest alignment with stakeholder responsibilities  
    3. Priority weights assigned to each stakeholder role
    4. Notification threshold preferences
    
    This is DISTINCT from domain stakeholder impacts extracted from literature.
    Use this for internal resource allocation and notification guidance.
    """
    
    def __init__(
        self,
        org_stakeholder_definitions_path: str,
        pillar_definitions_path: str
    ):
        """
        Initialize organizational stakeholder prioritizer.
        
        Args:
            org_stakeholder_definitions_path: Path to organizational stakeholder definitions
            pillar_definitions_path: Path to pillar definitions
        """
        with open(org_stakeholder_definitions_path, 'r', encoding='utf-8') as f:
            self.org_stakeholder_defs = json.load(f)
        
        with open(pillar_definitions_path, 'r', encoding='utf-8') as f:
            self.pillar_definitions = json.load(f)
        
        # Parse organizational stakeholders
        self.org_stakeholders: Dict[str, OrganizationalStakeholder] = {}
        self._parse_org_stakeholders()
        
        # Priority results
        self.priorities: List[OrganizationalGapPriority] = []
        self.org_stakeholder_summaries: Dict[str, OrganizationalStakeholderSummary] = {}
    
    def _parse_org_stakeholders(self):
        """Parse organizational stakeholder definitions."""
        for stakeholder_id, data in self.org_stakeholder_defs.get("organizational_stakeholders", {}).items():
            self.org_stakeholders[stakeholder_id] = OrganizationalStakeholder(
                id=stakeholder_id,
                name=data.get("name", stakeholder_id),
                description=data.get("description", ""),
                priority_weight=data.get("priority_weight", 1.0),
                interests=data.get("interests", []),
                primary_pillars=data.get("primary_pillars", []),
                decision_authority=data.get("decision_authority", "medium"),
                notification_threshold=data.get("notification_threshold", "medium")
            )
    
    def analyze_gap_priorities(self, gap_analysis: Dict) -> Dict:
        """
        Analyze priority of gaps for all organizational stakeholders.
        
        Args:
            gap_analysis: Gap analysis report
        
        Returns:
            Organizational stakeholder prioritization matrix
        """
        logger.info("Analyzing organizational stakeholder priorities...")
        
        # Extract gaps
        gaps = self._extract_gaps(gap_analysis)
        logger.info(f"Found {len(gaps)} gaps to prioritize")
        
        # Calculate priorities for each gap-stakeholder pair
        for gap in gaps:
            for stakeholder_id, stakeholder in self.org_stakeholders.items():
                priority = self._calculate_priority(gap, stakeholder)
                if priority.priority_level != PriorityLevel.NONE:
                    self.priorities.append(priority)
        
        # Generate stakeholder summaries
        self._generate_summaries()
        
        return self._generate_matrix()
    
    def _extract_gaps(self, gap_analysis: Dict) -> List[Dict]:
        """Extract gaps from gap analysis report."""
        gaps = []
        
        for pillar_name, pillar_data in gap_analysis.items():
            if not isinstance(pillar_data, dict):
                continue
            
            analysis = pillar_data.get("analysis", {})
            
            for req_name, req_data in analysis.items():
                if isinstance(req_data, dict):
                    for sub_name, sub_data in req_data.items():
                        if isinstance(sub_data, dict):
                            completeness = sub_data.get("completeness_percent", COMPLETE_THRESHOLD)
                            
                            # Consider anything below complete threshold as a gap
                            if completeness < COMPLETE_THRESHOLD:
                                gaps.append({
                                    "gap_id": f"{pillar_name}::{req_name}::{sub_name}",
                                    "pillar": pillar_name,
                                    "requirement": req_name,
                                    "sub_requirement": sub_name,
                                    "completeness": completeness,
                                    "severity": self._calculate_severity(completeness),
                                    "description": sub_data.get("gap_reason", 
                                                                f"{COMPLETE_THRESHOLD-completeness}% coverage gap")
                                })
        
        return gaps
    
    def _calculate_severity(self, completeness: float) -> str:
        """Calculate gap severity from completeness."""
        if completeness < SEVERITY_CRITICAL_THRESHOLD:
            return "critical"
        elif completeness < SEVERITY_HIGH_THRESHOLD:
            return "high"
        elif completeness < SEVERITY_MEDIUM_THRESHOLD:
            return "medium"
        else:
            return "low"
    
    def _calculate_priority(
        self,
        gap: Dict,
        org_stakeholder: OrganizationalStakeholder
    ) -> OrganizationalGapPriority:
        """Calculate priority of a gap for an organizational stakeholder."""
        
        pillar = gap["pillar"]
        severity = gap["severity"]
        
        # Check pillar relevance
        pillar_relevant = any(
            p in pillar or pillar in p or p == "All"
            for p in org_stakeholder.primary_pillars
        )
        
        # Check interest alignment
        aligned_interests = self._check_interest_alignment(gap, org_stakeholder)
        
        # Calculate base priority score
        severity_scores = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
        base_score = severity_scores.get(severity, 0.5)
        
        # Apply pillar relevance
        if pillar_relevant:
            base_score *= 1.2
        else:
            base_score *= 0.5
        
        # Apply interest alignment
        interest_boost = len(aligned_interests) * 0.1
        base_score = min(1.0, base_score + interest_boost)
        
        # Apply stakeholder weight
        final_score = base_score * org_stakeholder.priority_weight
        
        # Determine priority level
        if final_score >= 0.8:
            priority_level = PriorityLevel.CRITICAL
        elif final_score >= 0.6:
            priority_level = PriorityLevel.HIGH
        elif final_score >= 0.3:
            priority_level = PriorityLevel.MEDIUM
        elif final_score > 0:
            priority_level = PriorityLevel.LOW
        else:
            priority_level = PriorityLevel.NONE
        
        # Determine notification priority
        notification = self._determine_notification(
            priority_level, org_stakeholder.notification_threshold
        )
        
        # Generate why prioritized
        why = self._generate_priority_reason(gap, org_stakeholder, aligned_interests)
        
        # Determine if action required
        action_required = priority_level in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]
        
        # Generate recommended action
        action = self._generate_action_recommendation(
            gap, org_stakeholder, priority_level
        ) if action_required else ""
        
        return OrganizationalGapPriority(
            gap_id=gap["gap_id"],
            gap_description=gap["description"],
            pillar=pillar,
            requirement=gap["requirement"],
            org_stakeholder_id=org_stakeholder.id,
            org_stakeholder_name=org_stakeholder.name,
            priority_level=priority_level,
            priority_score=round(final_score, 3),
            interest_alignment=aligned_interests,
            why_prioritized=why,
            notification_priority=notification,
            action_required=action_required,
            recommended_action=action
        )
    
    def _check_interest_alignment(
        self,
        gap: Dict,
        org_stakeholder: OrganizationalStakeholder
    ) -> List[str]:
        """Check which organizational stakeholder interests align with gap."""
        aligned = []
        
        gap_text = f"{gap['description']} {gap['requirement']} {gap['pillar']}".lower()
        
        for interest in org_stakeholder.interests:
            interest_lower = interest.lower()
            
            # Check for keyword matches
            keywords = interest_lower.split()
            if any(kw in gap_text for kw in keywords):
                aligned.append(interest)
        
        # Also check interest categories
        categories = self.org_stakeholder_defs.get("interest_categories", {})
        for cat_name, cat_data in categories.items():
            if org_stakeholder.id in cat_data.get("organizational_stakeholders", []):
                if any(p in gap["pillar"] for p in cat_data.get("relevant_pillars", [])):
                    if cat_name not in aligned:
                        aligned.append(cat_name)
        
        return aligned
    
    def _determine_notification(
        self,
        priority_level: PriorityLevel,
        threshold: str
    ) -> NotificationPriority:
        """Determine notification priority based on priority level and threshold."""
        
        threshold_map = {
            "critical_only": {
                PriorityLevel.CRITICAL: NotificationPriority.IMMEDIATE,
            },
            "high": {
                PriorityLevel.CRITICAL: NotificationPriority.IMMEDIATE,
                PriorityLevel.HIGH: NotificationPriority.WEEKLY,
            },
            "medium": {
                PriorityLevel.CRITICAL: NotificationPriority.IMMEDIATE,
                PriorityLevel.HIGH: NotificationPriority.WEEKLY,
                PriorityLevel.MEDIUM: NotificationPriority.MONTHLY,
            },
            "low": {
                PriorityLevel.CRITICAL: NotificationPriority.IMMEDIATE,
                PriorityLevel.HIGH: NotificationPriority.IMMEDIATE,
                PriorityLevel.MEDIUM: NotificationPriority.WEEKLY,
                PriorityLevel.LOW: NotificationPriority.MONTHLY,
            }
        }
        
        mapping = threshold_map.get(threshold, threshold_map["medium"])
        return mapping.get(priority_level, NotificationPriority.NONE)
    
    def _generate_priority_reason(
        self,
        gap: Dict,
        org_stakeholder: OrganizationalStakeholder,
        aligned_interests: List[str]
    ) -> str:
        """Generate explanation of why gap is prioritized for this stakeholder."""
        
        reasons = []
        
        if aligned_interests:
            reasons.append(f"Aligns with interests: {', '.join(aligned_interests)}")
        
        if any(p in gap["pillar"] for p in org_stakeholder.primary_pillars):
            reasons.append("In primary pillar focus area")
        
        severity = gap["severity"]
        if severity == "critical":
            reasons.append("Gap severity is critical")
        elif severity == "high":
            reasons.append("Gap severity is high")
        
        return ". ".join(reasons) if reasons else "General relevance to organizational stakeholder domain"
    
    def _generate_action_recommendation(
        self,
        gap: Dict,
        org_stakeholder: OrganizationalStakeholder,
        priority_level: PriorityLevel
    ) -> str:
        """Generate action recommendation."""
        
        authority = org_stakeholder.decision_authority
        
        if authority == "high":
            if priority_level == PriorityLevel.CRITICAL:
                return "Immediate review and decision required. Consider resource reallocation."
            else:
                return "Schedule review in next planning cycle."
        elif authority == "medium":
            if priority_level == PriorityLevel.CRITICAL:
                return "Escalate to leadership. Provide priority assessment."
            else:
                return "Include in weekly status update."
        else:  # low or advisory
            if priority_level == PriorityLevel.CRITICAL:
                return "Notify primary organizational stakeholders. Provide domain expertise if requested."
            else:
                return "Monitor progress. No immediate action required."
    
    def _generate_summaries(self):
        """Generate per-organizational-stakeholder summaries."""
        
        for stakeholder_id, stakeholder in self.org_stakeholders.items():
            stakeholder_priorities = [
                p for p in self.priorities 
                if p.org_stakeholder_id == stakeholder_id
            ]
            
            summary = OrganizationalStakeholderSummary(
                org_stakeholder_id=stakeholder_id,
                org_stakeholder_name=stakeholder.name,
                total_priorities=len(stakeholder_priorities)
            )
            
            # Count by level
            for priority in stakeholder_priorities:
                if priority.priority_level == PriorityLevel.CRITICAL:
                    summary.critical_priorities += 1
                elif priority.priority_level == PriorityLevel.HIGH:
                    summary.high_priorities += 1
                elif priority.priority_level == PriorityLevel.MEDIUM:
                    summary.medium_priorities += 1
            
            # Find most prioritized gaps
            sorted_priorities = sorted(
                stakeholder_priorities, 
                key=lambda x: x.priority_score, 
                reverse=True
            )
            summary.most_prioritized_gaps = [
                p.gap_id for p in sorted_priorities[:5]
            ]
            
            # Count by pillar
            pillar_counts: Dict[str, int] = defaultdict(int)
            for priority in stakeholder_priorities:
                pillar_counts[priority.pillar] += 1
            summary.primary_pillar_gaps = dict(pillar_counts)
            
            # Calculate overall priority score
            if stakeholder_priorities:
                summary.overall_priority_score = sum(
                    p.priority_score for p in stakeholder_priorities
                ) / len(stakeholder_priorities)
            
            # Determine if attention required
            summary.attention_required = (
                summary.critical_priorities > 0 or 
                summary.high_priorities >= 3
            )
            
            self.org_stakeholder_summaries[stakeholder_id] = summary
    
    def _generate_matrix(self) -> Dict:
        """Generate complete organizational stakeholder prioritization matrix."""
        
        # Calculate overall summary
        total_gaps = len(set(p.gap_id for p in self.priorities))
        stakeholders_affected = len([
            s for s in self.org_stakeholder_summaries.values()
            if s.total_priorities > 0
        ])
        
        critical_total = sum(
            s.critical_priorities for s in self.org_stakeholder_summaries.values()
        )
        
        # Prioritized gaps (by total stakeholder priority)
        gap_priority: Dict[str, float] = defaultdict(float)
        for priority in self.priorities:
            gap_priority[priority.gap_id] += priority.priority_score
        
        prioritized_gaps = sorted(
            gap_priority.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return {
            "matrix_type": "organizational_stakeholder_prioritization",
            "description": "Algorithmic prioritization of gaps for internal organizational roles",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_gaps_analyzed": total_gaps,
                "total_stakeholder_priorities": len(self.priorities),
                "org_stakeholders_affected": stakeholders_affected,
                "critical_priorities": critical_total,
                "org_stakeholders_requiring_attention": len([
                    s for s in self.org_stakeholder_summaries.values()
                    if s.attention_required
                ])
            },
            "org_stakeholder_summaries": {
                sid: s.to_dict() 
                for sid, s in self.org_stakeholder_summaries.items()
            },
            "prioritized_gaps": [
                {"gap_id": gap_id, "total_priority_score": round(score, 3)}
                for gap_id, score in prioritized_gaps[:20]
            ],
            "all_priorities": [p.to_dict() for p in self.priorities],
            "notification_queue": self._generate_notification_queue()
        }
    
    def _generate_notification_queue(self) -> Dict[str, List[Dict]]:
        """Generate notification queue by priority."""
        queue: Dict[str, List[Dict]] = defaultdict(list)
        
        for priority in self.priorities:
            if priority.notification_priority != NotificationPriority.NONE:
                queue[priority.notification_priority.value].append({
                    "org_stakeholder": priority.org_stakeholder_name,
                    "gap_id": priority.gap_id,
                    "priority_level": priority.priority_level.value,
                    "action_required": priority.action_required,
                    "recommended_action": priority.recommended_action
                })
        
        return dict(queue)
    
    def get_org_stakeholder_report(self, org_stakeholder_id: str) -> Optional[Dict]:
        """Get report for specific organizational stakeholder."""
        if org_stakeholder_id not in self.org_stakeholder_summaries:
            return None
        
        summary = self.org_stakeholder_summaries[org_stakeholder_id]
        priorities = [
            p.to_dict() for p in self.priorities 
            if p.org_stakeholder_id == org_stakeholder_id
        ]
        
        return {
            "org_stakeholder": self.org_stakeholders[org_stakeholder_id].to_dict(),
            "summary": summary.to_dict(),
            "priorities": sorted(priorities, key=lambda x: x["priority_score"], reverse=True)
        }
    
    def get_gap_org_stakeholder_report(self, gap_id: str) -> Dict:
        """Get all organizational stakeholder priorities for a specific gap."""
        priorities = [p.to_dict() for p in self.priorities if p.gap_id == gap_id]
        
        return {
            "gap_id": gap_id,
            "org_stakeholder_priorities": sorted(
                priorities, 
                key=lambda x: x["priority_score"], 
                reverse=True
            ),
            "total_org_stakeholders_affected": len(priorities)
        }
    
    def save_matrix(self, output_path: str) -> Dict:
        """Save organizational stakeholder prioritization matrix to file."""
        matrix = self._generate_matrix()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved organizational stakeholder prioritization matrix to {output_path}")
        return matrix


# Backward compatibility aliases
StakeholderAnalyzer = OrganizationalStakeholderPrioritizer
Stakeholder = OrganizationalStakeholder
GapImpact = OrganizationalGapPriority
StakeholderGapSummary = OrganizationalStakeholderSummary
ImpactLevel = PriorityLevel


def generate_org_stakeholder_prioritization_matrix(
    org_stakeholder_definitions_path: str,
    pillar_definitions_path: str,
    gap_analysis_path: str,
    output_path: str
) -> Dict:
    """
    Convenience function to generate organizational stakeholder prioritization matrix.
    
    Args:
        org_stakeholder_definitions_path: Path to organizational stakeholder definitions
        pillar_definitions_path: Path to pillar definitions
        gap_analysis_path: Path to gap analysis report
        output_path: Path to save output matrix
    
    Returns:
        Generated matrix dictionary
    """
    with open(gap_analysis_path, 'r', encoding='utf-8') as f:
        gap_analysis = json.load(f)
    
    prioritizer = OrganizationalStakeholderPrioritizer(
        org_stakeholder_definitions_path=org_stakeholder_definitions_path,
        pillar_definitions_path=pillar_definitions_path
    )
    
    prioritizer.analyze_gap_priorities(gap_analysis)
    return prioritizer.save_matrix(output_path)


# Backward compatibility alias
generate_stakeholder_matrix = generate_org_stakeholder_prioritization_matrix
