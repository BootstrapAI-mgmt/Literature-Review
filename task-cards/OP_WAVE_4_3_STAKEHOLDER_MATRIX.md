# Task Card: Stakeholder Impact Matrix

**Task ID:** OP-W4-3  
**Wave:** 4 (Evolution & Governance)  
**Priority:** MEDIUM  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** OP-W1-1 (Schema Foundation), OP-W3-1 (Validation Tracker)  
**Blocks:** None (final output module)

---

## Objective

Create a stakeholder impact matrix that maps gaps to their beneficiaries, enabling prioritized research and development based on stakeholder value. Output `stakeholder_impact_matrix.json` to inform resource allocation decisions.

## Background

Current gap analysis lacks stakeholder context. This task adds:

1. **Stakeholder definitions**: Define stakeholder roles and interests
2. **Gap-to-stakeholder mapping**: Which stakeholders benefit from closing which gaps
3. **Priority scoring**: Weight gaps by stakeholder importance
4. **Impact visualization**: Clear view of stakeholder-gap relationships

## Success Criteria

- [ ] `stakeholder_definitions.json` schema implemented
- [ ] `stakeholder_analyzer.py` module created
- [ ] Gap-to-stakeholder mapping algorithm working
- [ ] Impact scoring based on stakeholder weights
- [ ] `stakeholder_impact_matrix.json` generated
- [ ] Integration with recommendation engine
- [ ] Unit tests with >90% coverage

---

## Deliverables

### 1. Stakeholder Definitions Schema

**File:** `stakeholder_definitions.json`

```json
{
  "$schema": "stakeholder_definitions_v1",
  "version": "1.0.0",
  "description": "Stakeholder definitions for research prioritization",
  "stakeholders": {
    "core_research": {
      "name": "Core Research Team",
      "description": "Primary researchers developing the neuromorphic system",
      "priority_weight": 1.0,
      "interests": [
        "Biological accuracy",
        "Novel architectures",
        "Reproducible results"
      ],
      "primary_pillars": ["Pillar 1", "Pillar 3", "Pillar 5"],
      "decision_authority": "high",
      "notification_threshold": "medium"
    },
    "engineering": {
      "name": "Engineering Team",
      "description": "Implementation and infrastructure",
      "priority_weight": 0.9,
      "interests": [
        "Clear specifications",
        "Performance benchmarks",
        "Scalability requirements"
      ],
      "primary_pillars": ["Pillar 2", "Pillar 4"],
      "decision_authority": "medium",
      "notification_threshold": "high"
    },
    "domain_experts": {
      "name": "Neuroscience Domain Experts",
      "description": "External advisors on biological plausibility",
      "priority_weight": 0.8,
      "interests": [
        "Biological validation",
        "Neuroscience alignment",
        "Experimental protocols"
      ],
      "primary_pillars": ["Pillar 1", "Pillar 3"],
      "decision_authority": "advisory",
      "notification_threshold": "high"
    },
    "product": {
      "name": "Product Team",
      "description": "Product direction and market fit",
      "priority_weight": 0.7,
      "interests": [
        "Market differentiation",
        "Competitive benchmarks",
        "Use case validation"
      ],
      "primary_pillars": ["Pillar 6", "Pillar 7"],
      "decision_authority": "medium",
      "notification_threshold": "medium"
    },
    "operations": {
      "name": "Operations Team",
      "description": "Deployment and infrastructure",
      "priority_weight": 0.6,
      "interests": [
        "Resource efficiency",
        "Deployment complexity",
        "Maintenance requirements"
      ],
      "primary_pillars": ["Pillar 4", "Pillar 6"],
      "decision_authority": "low",
      "notification_threshold": "low"
    },
    "executive": {
      "name": "Executive Leadership",
      "description": "Strategic direction and funding",
      "priority_weight": 0.95,
      "interests": [
        "Overall progress",
        "Milestone achievement",
        "Strategic alignment"
      ],
      "primary_pillars": ["All"],
      "decision_authority": "high",
      "notification_threshold": "critical_only"
    }
  },
  "interest_categories": {
    "biological_accuracy": {
      "description": "Alignment with biological neural systems",
      "relevant_pillars": ["Pillar 1", "Pillar 3"],
      "stakeholders": ["core_research", "domain_experts"]
    },
    "performance": {
      "description": "Computational efficiency and speed",
      "relevant_pillars": ["Pillar 2", "Pillar 4"],
      "stakeholders": ["engineering", "operations"]
    },
    "scalability": {
      "description": "Ability to scale to larger systems",
      "relevant_pillars": ["Pillar 4", "Pillar 6"],
      "stakeholders": ["engineering", "operations", "executive"]
    },
    "novelty": {
      "description": "Novel contributions to the field",
      "relevant_pillars": ["Pillar 5", "Pillar 7"],
      "stakeholders": ["core_research", "product"]
    },
    "validation": {
      "description": "Rigorous experimental validation",
      "relevant_pillars": ["All"],
      "stakeholders": ["core_research", "domain_experts", "executive"]
    }
  }
}
```

---

### 2. Stakeholder Analyzer Module

**File:** `literature_review/analysis/stakeholder_analyzer.py`

```python
"""
Stakeholder Impact Analyzer

Maps gaps to stakeholders and generates prioritized impact matrix.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from pathlib import Path
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ImpactLevel(Enum):
    """Impact level on stakeholder."""
    CRITICAL = "critical"      # Major impact on core interests
    HIGH = "high"              # Significant impact
    MEDIUM = "medium"          # Moderate impact
    LOW = "low"                # Minor impact
    NONE = "none"              # No direct impact


class NotificationPriority(Enum):
    """Priority for stakeholder notification."""
    IMMEDIATE = "immediate"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    NONE = "none"


@dataclass
class Stakeholder:
    """Stakeholder definition."""
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
class GapImpact:
    """Impact of a gap on a stakeholder."""
    gap_id: str
    gap_description: str
    pillar: str
    requirement: str
    
    stakeholder_id: str
    stakeholder_name: str
    
    impact_level: ImpactLevel = ImpactLevel.MEDIUM
    impact_score: float = 0.0  # 0-1
    
    interest_alignment: List[str] = field(default_factory=list)
    why_impactful: str = ""
    
    notification_priority: NotificationPriority = NotificationPriority.MONTHLY
    action_required: bool = False
    recommended_action: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "gap_id": self.gap_id,
            "gap_description": self.gap_description,
            "pillar": self.pillar,
            "requirement": self.requirement,
            "stakeholder_id": self.stakeholder_id,
            "stakeholder_name": self.stakeholder_name,
            "impact_level": self.impact_level.value,
            "impact_score": self.impact_score,
            "interest_alignment": self.interest_alignment,
            "why_impactful": self.why_impactful,
            "notification_priority": self.notification_priority.value,
            "action_required": self.action_required,
            "recommended_action": self.recommended_action
        }


@dataclass
class StakeholderGapSummary:
    """Summary of all gaps impacting a stakeholder."""
    stakeholder_id: str
    stakeholder_name: str
    
    total_impacts: int = 0
    critical_impacts: int = 0
    high_impacts: int = 0
    medium_impacts: int = 0
    
    most_impactful_gaps: List[str] = field(default_factory=list)
    primary_pillar_gaps: Dict[str, int] = field(default_factory=dict)
    
    overall_impact_score: float = 0.0
    attention_required: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)


class StakeholderAnalyzer:
    """
    Analyze gap impact on stakeholders.
    
    Provides:
    1. Gap-to-stakeholder mapping
    2. Impact scoring and prioritization
    3. Notification recommendations
    4. Resource allocation guidance
    """
    
    def __init__(
        self,
        stakeholder_definitions_path: str,
        pillar_definitions_path: str
    ):
        """
        Initialize stakeholder analyzer.
        
        Args:
            stakeholder_definitions_path: Path to stakeholder definitions
            pillar_definitions_path: Path to pillar definitions
        """
        with open(stakeholder_definitions_path, 'r', encoding='utf-8') as f:
            self.stakeholder_defs = json.load(f)
        
        with open(pillar_definitions_path, 'r', encoding='utf-8') as f:
            self.pillar_definitions = json.load(f)
        
        # Parse stakeholders
        self.stakeholders: Dict[str, Stakeholder] = {}
        self._parse_stakeholders()
        
        # Impact results
        self.impacts: List[GapImpact] = []
        self.stakeholder_summaries: Dict[str, StakeholderGapSummary] = {}
    
    def _parse_stakeholders(self):
        """Parse stakeholder definitions."""
        for stakeholder_id, data in self.stakeholder_defs.get("stakeholders", {}).items():
            self.stakeholders[stakeholder_id] = Stakeholder(
                id=stakeholder_id,
                name=data.get("name", stakeholder_id),
                description=data.get("description", ""),
                priority_weight=data.get("priority_weight", 1.0),
                interests=data.get("interests", []),
                primary_pillars=data.get("primary_pillars", []),
                decision_authority=data.get("decision_authority", "medium"),
                notification_threshold=data.get("notification_threshold", "medium")
            )
    
    def analyze_gap_impacts(self, gap_analysis: Dict) -> Dict:
        """
        Analyze impact of gaps on all stakeholders.
        
        Args:
            gap_analysis: Gap analysis report
        
        Returns:
            Stakeholder impact matrix
        """
        logger.info("Analyzing stakeholder impacts...")
        
        # Extract gaps
        gaps = self._extract_gaps(gap_analysis)
        logger.info(f"Found {len(gaps)} gaps to analyze")
        
        # Calculate impacts for each gap-stakeholder pair
        for gap in gaps:
            for stakeholder_id, stakeholder in self.stakeholders.items():
                impact = self._calculate_impact(gap, stakeholder)
                if impact.impact_level != ImpactLevel.NONE:
                    self.impacts.append(impact)
        
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
                            completeness = sub_data.get("completeness_percent", 100)
                            
                            # Consider anything below 100% as a gap
                            if completeness < 100:
                                gaps.append({
                                    "gap_id": f"{pillar_name}::{req_name}::{sub_name}",
                                    "pillar": pillar_name,
                                    "requirement": req_name,
                                    "sub_requirement": sub_name,
                                    "completeness": completeness,
                                    "severity": self._calculate_severity(completeness),
                                    "description": sub_data.get("gap_reason", 
                                                                f"{100-completeness}% coverage gap")
                                })
        
        return gaps
    
    def _calculate_severity(self, completeness: float) -> str:
        """Calculate gap severity from completeness."""
        if completeness < 30:
            return "critical"
        elif completeness < 50:
            return "high"
        elif completeness < 70:
            return "medium"
        else:
            return "low"
    
    def _calculate_impact(
        self,
        gap: Dict,
        stakeholder: Stakeholder
    ) -> GapImpact:
        """Calculate impact of a gap on a stakeholder."""
        
        pillar = gap["pillar"]
        severity = gap["severity"]
        
        # Check pillar relevance
        pillar_relevant = any(
            p in pillar or pillar in p or p == "All"
            for p in stakeholder.primary_pillars
        )
        
        # Check interest alignment
        aligned_interests = self._check_interest_alignment(gap, stakeholder)
        
        # Calculate base impact score
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
        final_score = base_score * stakeholder.priority_weight
        
        # Determine impact level
        if final_score >= 0.8:
            impact_level = ImpactLevel.CRITICAL
        elif final_score >= 0.6:
            impact_level = ImpactLevel.HIGH
        elif final_score >= 0.3:
            impact_level = ImpactLevel.MEDIUM
        elif final_score > 0:
            impact_level = ImpactLevel.LOW
        else:
            impact_level = ImpactLevel.NONE
        
        # Determine notification priority
        notification = self._determine_notification(
            impact_level, stakeholder.notification_threshold
        )
        
        # Generate why impactful
        why = self._generate_impact_reason(gap, stakeholder, aligned_interests)
        
        # Determine if action required
        action_required = impact_level in [ImpactLevel.CRITICAL, ImpactLevel.HIGH]
        
        # Generate recommended action
        action = self._generate_action_recommendation(
            gap, stakeholder, impact_level
        ) if action_required else ""
        
        return GapImpact(
            gap_id=gap["gap_id"],
            gap_description=gap["description"],
            pillar=pillar,
            requirement=gap["requirement"],
            stakeholder_id=stakeholder.id,
            stakeholder_name=stakeholder.name,
            impact_level=impact_level,
            impact_score=round(final_score, 3),
            interest_alignment=aligned_interests,
            why_impactful=why,
            notification_priority=notification,
            action_required=action_required,
            recommended_action=action
        )
    
    def _check_interest_alignment(
        self,
        gap: Dict,
        stakeholder: Stakeholder
    ) -> List[str]:
        """Check which stakeholder interests align with gap."""
        aligned = []
        
        gap_text = f"{gap['description']} {gap['requirement']} {gap['pillar']}".lower()
        
        for interest in stakeholder.interests:
            interest_lower = interest.lower()
            
            # Check for keyword matches
            keywords = interest_lower.split()
            if any(kw in gap_text for kw in keywords):
                aligned.append(interest)
        
        # Also check interest categories
        categories = self.stakeholder_defs.get("interest_categories", {})
        for cat_name, cat_data in categories.items():
            if stakeholder.id in cat_data.get("stakeholders", []):
                if any(p in gap["pillar"] for p in cat_data.get("relevant_pillars", [])):
                    if cat_name not in aligned:
                        aligned.append(cat_name)
        
        return aligned
    
    def _determine_notification(
        self,
        impact_level: ImpactLevel,
        threshold: str
    ) -> NotificationPriority:
        """Determine notification priority based on impact and threshold."""
        
        threshold_map = {
            "critical_only": {
                ImpactLevel.CRITICAL: NotificationPriority.IMMEDIATE,
            },
            "high": {
                ImpactLevel.CRITICAL: NotificationPriority.IMMEDIATE,
                ImpactLevel.HIGH: NotificationPriority.WEEKLY,
            },
            "medium": {
                ImpactLevel.CRITICAL: NotificationPriority.IMMEDIATE,
                ImpactLevel.HIGH: NotificationPriority.WEEKLY,
                ImpactLevel.MEDIUM: NotificationPriority.MONTHLY,
            },
            "low": {
                ImpactLevel.CRITICAL: NotificationPriority.IMMEDIATE,
                ImpactLevel.HIGH: NotificationPriority.IMMEDIATE,
                ImpactLevel.MEDIUM: NotificationPriority.WEEKLY,
                ImpactLevel.LOW: NotificationPriority.MONTHLY,
            }
        }
        
        mapping = threshold_map.get(threshold, threshold_map["medium"])
        return mapping.get(impact_level, NotificationPriority.NONE)
    
    def _generate_impact_reason(
        self,
        gap: Dict,
        stakeholder: Stakeholder,
        aligned_interests: List[str]
    ) -> str:
        """Generate explanation of why gap impacts stakeholder."""
        
        reasons = []
        
        if aligned_interests:
            reasons.append(f"Aligns with interests: {', '.join(aligned_interests)}")
        
        if any(p in gap["pillar"] for p in stakeholder.primary_pillars):
            reasons.append(f"In primary pillar focus area")
        
        severity = gap["severity"]
        if severity == "critical":
            reasons.append("Gap severity is critical")
        elif severity == "high":
            reasons.append("Gap severity is high")
        
        return ". ".join(reasons) if reasons else "General relevance to stakeholder domain"
    
    def _generate_action_recommendation(
        self,
        gap: Dict,
        stakeholder: Stakeholder,
        impact_level: ImpactLevel
    ) -> str:
        """Generate action recommendation."""
        
        authority = stakeholder.decision_authority
        severity = gap["severity"]
        
        if authority == "high":
            if impact_level == ImpactLevel.CRITICAL:
                return "Immediate review and decision required. Consider resource reallocation."
            else:
                return "Schedule review in next planning cycle."
        elif authority == "medium":
            if impact_level == ImpactLevel.CRITICAL:
                return "Escalate to leadership. Provide impact assessment."
            else:
                return "Include in weekly status update."
        else:  # low or advisory
            if impact_level == ImpactLevel.CRITICAL:
                return "Notify primary stakeholders. Provide domain expertise if requested."
            else:
                return "Monitor progress. No immediate action required."
    
    def _generate_summaries(self):
        """Generate per-stakeholder summaries."""
        
        for stakeholder_id, stakeholder in self.stakeholders.items():
            stakeholder_impacts = [
                i for i in self.impacts 
                if i.stakeholder_id == stakeholder_id
            ]
            
            summary = StakeholderGapSummary(
                stakeholder_id=stakeholder_id,
                stakeholder_name=stakeholder.name,
                total_impacts=len(stakeholder_impacts)
            )
            
            # Count by level
            for impact in stakeholder_impacts:
                if impact.impact_level == ImpactLevel.CRITICAL:
                    summary.critical_impacts += 1
                elif impact.impact_level == ImpactLevel.HIGH:
                    summary.high_impacts += 1
                elif impact.impact_level == ImpactLevel.MEDIUM:
                    summary.medium_impacts += 1
            
            # Find most impactful gaps
            sorted_impacts = sorted(
                stakeholder_impacts, 
                key=lambda x: x.impact_score, 
                reverse=True
            )
            summary.most_impactful_gaps = [
                i.gap_id for i in sorted_impacts[:5]
            ]
            
            # Count by pillar
            pillar_counts = defaultdict(int)
            for impact in stakeholder_impacts:
                pillar_counts[impact.pillar] += 1
            summary.primary_pillar_gaps = dict(pillar_counts)
            
            # Calculate overall impact score
            if stakeholder_impacts:
                summary.overall_impact_score = sum(
                    i.impact_score for i in stakeholder_impacts
                ) / len(stakeholder_impacts)
            
            # Determine if attention required
            summary.attention_required = (
                summary.critical_impacts > 0 or 
                summary.high_impacts >= 3
            )
            
            self.stakeholder_summaries[stakeholder_id] = summary
    
    def _generate_matrix(self) -> Dict:
        """Generate complete stakeholder impact matrix."""
        
        # Calculate overall summary
        total_gaps = len(set(i.gap_id for i in self.impacts))
        stakeholders_affected = len([
            s for s in self.stakeholder_summaries.values()
            if s.total_impacts > 0
        ])
        
        critical_total = sum(
            s.critical_impacts for s in self.stakeholder_summaries.values()
        )
        
        # Prioritized gaps (by total stakeholder impact)
        gap_priority = defaultdict(float)
        for impact in self.impacts:
            gap_priority[impact.gap_id] += impact.impact_score
        
        prioritized_gaps = sorted(
            gap_priority.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_gaps_analyzed": total_gaps,
                "total_stakeholder_impacts": len(self.impacts),
                "stakeholders_affected": stakeholders_affected,
                "critical_impacts": critical_total,
                "stakeholders_requiring_attention": len([
                    s for s in self.stakeholder_summaries.values()
                    if s.attention_required
                ])
            },
            "stakeholder_summaries": {
                sid: s.to_dict() 
                for sid, s in self.stakeholder_summaries.items()
            },
            "prioritized_gaps": [
                {"gap_id": gap_id, "total_impact_score": round(score, 3)}
                for gap_id, score in prioritized_gaps[:20]
            ],
            "all_impacts": [i.to_dict() for i in self.impacts],
            "notification_queue": self._generate_notification_queue()
        }
    
    def _generate_notification_queue(self) -> Dict[str, List[Dict]]:
        """Generate notification queue by priority."""
        queue = defaultdict(list)
        
        for impact in self.impacts:
            if impact.notification_priority != NotificationPriority.NONE:
                queue[impact.notification_priority.value].append({
                    "stakeholder": impact.stakeholder_name,
                    "gap_id": impact.gap_id,
                    "impact_level": impact.impact_level.value,
                    "action_required": impact.action_required,
                    "recommended_action": impact.recommended_action
                })
        
        return dict(queue)
    
    def get_stakeholder_report(self, stakeholder_id: str) -> Optional[Dict]:
        """Get report for specific stakeholder."""
        if stakeholder_id not in self.stakeholder_summaries:
            return None
        
        summary = self.stakeholder_summaries[stakeholder_id]
        impacts = [
            i.to_dict() for i in self.impacts 
            if i.stakeholder_id == stakeholder_id
        ]
        
        return {
            "stakeholder": self.stakeholders[stakeholder_id].to_dict(),
            "summary": summary.to_dict(),
            "impacts": sorted(impacts, key=lambda x: x["impact_score"], reverse=True)
        }
    
    def get_gap_stakeholder_report(self, gap_id: str) -> Dict:
        """Get all stakeholder impacts for a specific gap."""
        impacts = [i.to_dict() for i in self.impacts if i.gap_id == gap_id]
        
        return {
            "gap_id": gap_id,
            "stakeholder_impacts": sorted(
                impacts, 
                key=lambda x: x["impact_score"], 
                reverse=True
            ),
            "total_stakeholders_affected": len(impacts)
        }
    
    def save_matrix(self, output_path: str) -> Dict:
        """Save stakeholder impact matrix to file."""
        matrix = self._generate_matrix()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(matrix, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved stakeholder impact matrix to {output_path}")
        return matrix


def generate_stakeholder_matrix(
    stakeholder_definitions_path: str,
    pillar_definitions_path: str,
    gap_analysis_path: str,
    output_path: str
) -> Dict:
    """
    Convenience function to generate stakeholder impact matrix.
    
    Args:
        stakeholder_definitions_path: Path to stakeholder definitions
        pillar_definitions_path: Path to pillar definitions
        gap_analysis_path: Path to gap analysis report
        output_path: Path to save output matrix
    
    Returns:
        Generated matrix dictionary
    """
    with open(gap_analysis_path, 'r', encoding='utf-8') as f:
        gap_analysis = json.load(f)
    
    analyzer = StakeholderAnalyzer(
        stakeholder_definitions_path=stakeholder_definitions_path,
        pillar_definitions_path=pillar_definitions_path
    )
    
    analyzer.analyze_gap_impacts(gap_analysis)
    return analyzer.save_matrix(output_path)
```

---

### 3. Orchestrator Integration

**File:** `literature_review/orchestrator.py` (additions)

```python
# Add to imports
from literature_review.analysis.stakeholder_analyzer import (
    StakeholderAnalyzer,
    generate_stakeholder_matrix
)

# Add method to orchestrator
def generate_stakeholder_impact_matrix(
    self,
    stakeholder_definitions_path: Optional[str] = None,
    output_path: Optional[str] = None
) -> Dict:
    """
    Generate stakeholder impact matrix.
    
    Args:
        stakeholder_definitions_path: Optional custom path
        output_path: Optional custom output path
    
    Returns:
        Stakeholder impact matrix
    """
    stakeholder_definitions_path = stakeholder_definitions_path or os.path.join(
        os.path.dirname(self.pillar_definitions_path),
        "stakeholder_definitions.json"
    )
    
    gap_analysis_path = os.path.join(self.output_dir, "gap_analysis_report.json")
    output_path = output_path or os.path.join(
        self.output_dir, "stakeholder_impact_matrix.json"
    )
    
    matrix = generate_stakeholder_matrix(
        stakeholder_definitions_path=stakeholder_definitions_path,
        pillar_definitions_path=self.pillar_definitions_path,
        gap_analysis_path=gap_analysis_path,
        output_path=output_path
    )
    
    logger.info(f"Generated stakeholder matrix: {matrix['summary']}")
    return matrix
```

---

## Unit Tests

**File:** `tests/unit/test_stakeholder_analyzer.py`

```python
"""Unit tests for stakeholder analyzer."""

import pytest
import json
from pathlib import Path

from literature_review.analysis.stakeholder_analyzer import (
    StakeholderAnalyzer,
    Stakeholder,
    GapImpact,
    ImpactLevel,
    NotificationPriority,
    generate_stakeholder_matrix
)


class TestStakeholder:
    """Tests for Stakeholder dataclass."""
    
    def test_create_stakeholder(self):
        """Test creating a stakeholder."""
        stakeholder = Stakeholder(
            id="core_research",
            name="Core Research Team",
            description="Primary researchers",
            priority_weight=1.0,
            interests=["Biological accuracy"],
            primary_pillars=["Pillar 1", "Pillar 3"]
        )
        
        assert stakeholder.id == "core_research"
        assert stakeholder.priority_weight == 1.0
    
    def test_to_dict(self):
        """Test serialization."""
        stakeholder = Stakeholder(
            id="test",
            name="Test",
            description="Test",
            priority_weight=0.8,
            interests=[],
            primary_pillars=[]
        )
        
        data = stakeholder.to_dict()
        assert data["priority_weight"] == 0.8


class TestGapImpact:
    """Tests for GapImpact dataclass."""
    
    def test_create_impact(self):
        """Test creating an impact."""
        impact = GapImpact(
            gap_id="Pillar 1::REQ-1.1::Sub-1.1.1",
            gap_description="Test gap",
            pillar="Pillar 1",
            requirement="REQ-1.1",
            stakeholder_id="core_research",
            stakeholder_name="Core Research",
            impact_level=ImpactLevel.HIGH,
            impact_score=0.75
        )
        
        assert impact.impact_level == ImpactLevel.HIGH
        assert impact.impact_score == 0.75
    
    def test_to_dict(self):
        """Test serialization."""
        impact = GapImpact(
            gap_id="test",
            gap_description="test",
            pillar="Pillar 1",
            requirement="REQ-1.1",
            stakeholder_id="test",
            stakeholder_name="Test",
            impact_level=ImpactLevel.CRITICAL
        )
        
        data = impact.to_dict()
        assert data["impact_level"] == "critical"


class TestStakeholderAnalyzer:
    """Tests for StakeholderAnalyzer class."""
    
    @pytest.fixture
    def sample_stakeholder_definitions(self, tmp_path):
        """Create sample stakeholder definitions."""
        definitions = {
            "$schema": "stakeholder_definitions_v1",
            "stakeholders": {
                "core_research": {
                    "name": "Core Research Team",
                    "description": "Primary researchers",
                    "priority_weight": 1.0,
                    "interests": ["Biological accuracy", "Novel architectures"],
                    "primary_pillars": ["Pillar 1", "Pillar 3"],
                    "decision_authority": "high",
                    "notification_threshold": "medium"
                },
                "engineering": {
                    "name": "Engineering Team",
                    "description": "Implementation",
                    "priority_weight": 0.9,
                    "interests": ["Performance", "Scalability"],
                    "primary_pillars": ["Pillar 2", "Pillar 4"],
                    "decision_authority": "medium",
                    "notification_threshold": "high"
                }
            },
            "interest_categories": {
                "biological_accuracy": {
                    "description": "Bio alignment",
                    "relevant_pillars": ["Pillar 1", "Pillar 3"],
                    "stakeholders": ["core_research"]
                }
            }
        }
        
        path = tmp_path / "stakeholder.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions."""
        definitions = {
            "Pillar 1: Biological Stimulus-Response": {
                "requirements": {
                    "REQ-B1.1": [{"id": "Sub-1.1.1", "text": "Test"}]
                }
            },
            "Pillar 2: AI Stimulus-Response": {
                "requirements": {
                    "REQ-A2.1": [{"id": "Sub-2.1.1", "text": "Test"}]
                }
            }
        }
        
        path = tmp_path / "pillar.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    @pytest.fixture
    def sample_gap_analysis(self, tmp_path):
        """Create sample gap analysis."""
        gap = {
            "Pillar 1: Biological Stimulus-Response": {
                "average_completeness": 45,
                "analysis": {
                    "REQ-B1.1": {
                        "Sub-1.1.1": {
                            "completeness_percent": 25,
                            "gap_reason": "Missing biological validation data"
                        }
                    }
                }
            },
            "Pillar 2: AI Stimulus-Response": {
                "average_completeness": 60,
                "analysis": {
                    "REQ-A2.1": {
                        "Sub-2.1.1": {
                            "completeness_percent": 60,
                            "gap_reason": "Performance benchmarks incomplete"
                        }
                    }
                }
            }
        }
        
        path = tmp_path / "gap.json"
        with open(path, 'w') as f:
            json.dump(gap, f)
        
        return str(path)
    
    def test_initialize(
        self, 
        sample_stakeholder_definitions, 
        sample_pillar_definitions
    ):
        """Test analyzer initialization."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        assert len(analyzer.stakeholders) == 2
        assert "core_research" in analyzer.stakeholders
    
    def test_analyze_impacts(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test impact analysis."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        result = analyzer.analyze_gap_impacts(gap)
        
        assert "summary" in result
        assert result["summary"]["total_gaps_analyzed"] == 2
    
    def test_pillar_relevance(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test that pillar relevance affects impact score."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        analyzer.analyze_gap_impacts(gap)
        
        # Core research should have higher impact on Pillar 1 gaps
        pillar1_impacts = [
            i for i in analyzer.impacts
            if "Pillar 1" in i.pillar and i.stakeholder_id == "core_research"
        ]
        
        pillar2_impacts = [
            i for i in analyzer.impacts
            if "Pillar 2" in i.pillar and i.stakeholder_id == "core_research"
        ]
        
        if pillar1_impacts and pillar2_impacts:
            assert pillar1_impacts[0].impact_score >= pillar2_impacts[0].impact_score
    
    def test_notification_priority(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions
    ):
        """Test notification priority determination."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        # High threshold stakeholder
        notification = analyzer._determine_notification(
            ImpactLevel.CRITICAL, "high"
        )
        assert notification == NotificationPriority.IMMEDIATE
        
        # Low impact on high threshold
        notification = analyzer._determine_notification(
            ImpactLevel.LOW, "high"
        )
        assert notification == NotificationPriority.NONE
    
    def test_stakeholder_report(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test per-stakeholder report generation."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        analyzer.analyze_gap_impacts(gap)
        
        report = analyzer.get_stakeholder_report("core_research")
        
        assert report is not None
        assert "stakeholder" in report
        assert "summary" in report
        assert "impacts" in report
    
    def test_gap_report(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis
    ):
        """Test per-gap report generation."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        analyzer.analyze_gap_impacts(gap)
        
        # Get a gap ID from impacts
        if analyzer.impacts:
            gap_id = analyzer.impacts[0].gap_id
            report = analyzer.get_gap_stakeholder_report(gap_id)
            
            assert "gap_id" in report
            assert "stakeholder_impacts" in report
    
    def test_save_matrix(
        self,
        sample_stakeholder_definitions,
        sample_pillar_definitions,
        sample_gap_analysis,
        tmp_path
    ):
        """Test saving matrix to file."""
        analyzer = StakeholderAnalyzer(
            sample_stakeholder_definitions,
            sample_pillar_definitions
        )
        
        with open(sample_gap_analysis) as f:
            gap = json.load(f)
        
        analyzer.analyze_gap_impacts(gap)
        
        output_path = str(tmp_path / "matrix.json")
        matrix = analyzer.save_matrix(output_path)
        
        assert Path(output_path).exists()
        
        with open(output_path) as f:
            saved = json.load(f)
        
        assert "summary" in saved
        assert "stakeholder_summaries" in saved


class TestConvenienceFunction:
    """Test the convenience function."""
    
    def test_generate_matrix(self, tmp_path):
        """Test the convenience function."""
        # Create test files
        stakeholder_def = {
            "stakeholders": {
                "test": {
                    "name": "Test",
                    "description": "Test",
                    "priority_weight": 1.0,
                    "interests": [],
                    "primary_pillars": ["Pillar 1"]
                }
            }
        }
        
        pillar_def = {
            "Pillar 1: Test": {"requirements": {}}
        }
        
        gap = {
            "Pillar 1: Test": {
                "average_completeness": 50,
                "analysis": {
                    "REQ-1.1": {
                        "Sub-1.1.1": {"completeness_percent": 50}
                    }
                }
            }
        }
        
        stakeholder_path = tmp_path / "stakeholder.json"
        pillar_path = tmp_path / "pillar.json"
        gap_path = tmp_path / "gap.json"
        output_path = tmp_path / "matrix.json"
        
        for path, data in [
            (stakeholder_path, stakeholder_def),
            (pillar_path, pillar_def),
            (gap_path, gap)
        ]:
            with open(path, 'w') as f:
                json.dump(data, f)
        
        matrix = generate_stakeholder_matrix(
            str(stakeholder_path),
            str(pillar_path),
            str(gap_path),
            str(output_path)
        )
        
        assert "summary" in matrix
        assert Path(output_path).exists()
```

---

## Output Schema: `stakeholder_impact_matrix.json`

```json
{
  "timestamp": "2025-12-19T10:00:00Z",
  "summary": {
    "total_gaps_analyzed": 45,
    "total_stakeholder_impacts": 180,
    "stakeholders_affected": 5,
    "critical_impacts": 12,
    "stakeholders_requiring_attention": 2
  },
  "stakeholder_summaries": {
    "core_research": {
      "stakeholder_id": "core_research",
      "stakeholder_name": "Core Research Team",
      "total_impacts": 35,
      "critical_impacts": 5,
      "high_impacts": 12,
      "medium_impacts": 18,
      "most_impactful_gaps": [
        "Pillar 1::REQ-B1.1::Sub-1.1.1",
        "Pillar 3::REQ-M3.1::Sub-3.1.1"
      ],
      "primary_pillar_gaps": {
        "Pillar 1: Biological Stimulus-Response": 15,
        "Pillar 3: Memory Formation": 12
      },
      "overall_impact_score": 0.65,
      "attention_required": true
    }
  },
  "prioritized_gaps": [
    {
      "gap_id": "Pillar 1::REQ-B1.1::Sub-1.1.1",
      "total_impact_score": 2.85
    },
    {
      "gap_id": "Pillar 3::REQ-M3.1::Sub-3.1.1",
      "total_impact_score": 2.45
    }
  ],
  "all_impacts": [
    {
      "gap_id": "Pillar 1::REQ-B1.1::Sub-1.1.1",
      "gap_description": "Missing biological validation data",
      "pillar": "Pillar 1: Biological Stimulus-Response",
      "requirement": "REQ-B1.1",
      "stakeholder_id": "core_research",
      "stakeholder_name": "Core Research Team",
      "impact_level": "critical",
      "impact_score": 0.95,
      "interest_alignment": ["Biological accuracy", "biological_accuracy"],
      "why_impactful": "Aligns with interests: Biological accuracy, biological_accuracy. In primary pillar focus area. Gap severity is critical",
      "notification_priority": "immediate",
      "action_required": true,
      "recommended_action": "Immediate review and decision required. Consider resource reallocation."
    }
  ],
  "notification_queue": {
    "immediate": [
      {
        "stakeholder": "Core Research Team",
        "gap_id": "Pillar 1::REQ-B1.1::Sub-1.1.1",
        "impact_level": "critical",
        "action_required": true,
        "recommended_action": "Immediate review..."
      }
    ],
    "weekly": [],
    "monthly": []
  }
}
```

---

## Acceptance Criteria Checklist

- [ ] Stakeholder definitions schema complete
- [ ] StakeholderAnalyzer correctly parses definitions
- [ ] Gap-to-stakeholder mapping uses pillar relevance
- [ ] Interest alignment detection working
- [ ] Impact scores correctly weighted
- [ ] Notification priorities determined by threshold
- [ ] Per-stakeholder and per-gap reports generated
- [ ] Matrix saved in correct JSON format
- [ ] Unit tests pass with >90% coverage

---

## Notes for Agent

1. **Run standalone for testing:**
   ```python
   from literature_review.analysis.stakeholder_analyzer import StakeholderAnalyzer
   
   analyzer = StakeholderAnalyzer(
       "stakeholder_definitions.json",
       "pillar_definitions_enhanced.json"
   )
   
   with open("gap_analysis_report.json") as f:
       gap = json.load(f)
   
   result = analyzer.analyze_gap_impacts(gap)
   print(json.dumps(result["summary"], indent=2))
   ```

2. **Stakeholder weights:**
   - Weights affect impact score calculation
   - Higher weight = higher impact for same gap severity
   - Adjust weights in stakeholder_definitions.json

3. **Notification threshold behavior:**
   - `critical_only`: Only notified for CRITICAL impacts
   - `high`: Notified for CRITICAL and HIGH
   - `medium`: Notified for CRITICAL, HIGH, and MEDIUM
   - `low`: Notified for all impact levels
