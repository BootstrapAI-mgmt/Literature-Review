"""
Pillar Research Log Manager

Tracks research progress per pillar with saturation scoring,
velocity metrics, and coverage trend analysis.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class SaturationLevel(Enum):
    """Research saturation levels."""
    UNSATURATED = "unsaturated"       # Much room for research
    APPROACHING = "approaching"        # Nearing saturation
    SATURATED = "saturated"           # Diminishing returns
    OVER_SATURATED = "over_saturated" # Should shift focus


class ResearchPhase(Enum):
    """Research phase for a pillar."""
    INITIAL = "initial"              # Just started
    EXPLORATION = "exploration"       # Actively exploring
    CONSOLIDATION = "consolidation"   # Refining findings
    VALIDATION = "validation"         # Validating conclusions
    COMPLETE = "complete"             # Research concluded


@dataclass
class ResearchSession:
    """A single research session entry."""
    session_id: str
    timestamp: str
    papers_added: int
    papers_removed: int
    claims_extracted: int
    claims_approved: int
    coverage_delta: float  # Change in coverage %
    requirements_addressed: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PillarResearchState:
    """Research state for a single pillar."""
    pillar_id: str
    pillar_name: str
    
    # Current metrics
    current_coverage: float = 0.0
    total_papers: int = 0
    total_claims: int = 0
    approved_claims: int = 0
    
    # Saturation metrics
    saturation_score: float = 0.0  # 0-1, higher = more saturated
    saturation_level: SaturationLevel = SaturationLevel.UNSATURATED
    
    # Velocity metrics
    coverage_velocity: float = 0.0  # Coverage change per session
    papers_per_session: float = 0.0
    claims_per_paper: float = 0.0
    
    # Phase tracking
    research_phase: ResearchPhase = ResearchPhase.INITIAL
    phase_started_at: str = ""
    sessions_in_phase: int = 0
    
    # History
    sessions: List[ResearchSession] = field(default_factory=list)
    coverage_history: List[Tuple[str, float]] = field(default_factory=list)
    
    # Recommendations
    focus_priority: float = 0.0  # Higher = needs more focus
    recommended_action: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "pillar_id": self.pillar_id,
            "pillar_name": self.pillar_name,
            "current_coverage": self.current_coverage,
            "total_papers": self.total_papers,
            "total_claims": self.total_claims,
            "approved_claims": self.approved_claims,
            "saturation_score": self.saturation_score,
            "saturation_level": self.saturation_level.value,
            "coverage_velocity": self.coverage_velocity,
            "papers_per_session": self.papers_per_session,
            "claims_per_paper": self.claims_per_paper,
            "research_phase": self.research_phase.value,
            "phase_started_at": self.phase_started_at,
            "sessions_in_phase": self.sessions_in_phase,
            "sessions": [s.to_dict() for s in self.sessions],
            "coverage_history": self.coverage_history,
            "focus_priority": self.focus_priority,
            "recommended_action": self.recommended_action
        }


class ResearchLogManager:
    """
    Manage research progress tracking for all pillars.
    
    Provides:
    1. Session-by-session progress tracking
    2. Saturation detection (diminishing returns)
    3. Research velocity metrics
    4. Focus recommendations based on coverage gaps and velocity
    """
    
    def __init__(
        self,
        pillar_definitions_path: str,
        log_path: Optional[str] = None
    ):
        """
        Initialize research log manager.
        
        Args:
            pillar_definitions_path: Path to pillar definitions
            log_path: Optional path to existing research log
        """
        with open(pillar_definitions_path, 'r', encoding='utf-8') as f:
            self.pillar_definitions = json.load(f)
        
        self.log_path = log_path
        self.pillar_states: Dict[str, PillarResearchState] = {}
        
        # Initialize pillar states
        self._initialize_pillar_states()
        
        # Load existing log if available
        if log_path and Path(log_path).exists():
            self._load_existing_log(log_path)
    
    def _initialize_pillar_states(self):
        """Initialize state for each pillar."""
        for pillar_name, pillar_data in self.pillar_definitions.items():
            if not pillar_name.startswith("Pillar"):
                continue
            
            # Extract pillar ID (e.g., "1" from "Pillar 1: ...")
            pillar_id = pillar_name.split(":")[0].strip()
            
            self.pillar_states[pillar_id] = PillarResearchState(
                pillar_id=pillar_id,
                pillar_name=pillar_name
            )
    
    def _load_existing_log(self, log_path: str):
        """Load existing research log."""
        with open(log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for pillar_id, pillar_data in data.get("pillars", {}).items():
            if pillar_id in self.pillar_states:
                state = self.pillar_states[pillar_id]
                
                # Restore metrics
                state.current_coverage = pillar_data.get("current_coverage", 0)
                state.total_papers = pillar_data.get("total_papers", 0)
                state.total_claims = pillar_data.get("total_claims", 0)
                state.approved_claims = pillar_data.get("approved_claims", 0)
                state.saturation_score = pillar_data.get("saturation_score", 0)
                state.coverage_velocity = pillar_data.get("coverage_velocity", 0)
                
                # Restore phase
                phase_str = pillar_data.get("research_phase", "initial")
                state.research_phase = ResearchPhase(phase_str)
                
                # Restore history
                state.coverage_history = pillar_data.get("coverage_history", [])
                
                # Restore sessions
                for session_data in pillar_data.get("sessions", []):
                    session = ResearchSession(
                        session_id=session_data["session_id"],
                        timestamp=session_data["timestamp"],
                        papers_added=session_data["papers_added"],
                        papers_removed=session_data.get("papers_removed", 0),
                        claims_extracted=session_data["claims_extracted"],
                        claims_approved=session_data["claims_approved"],
                        coverage_delta=session_data["coverage_delta"],
                        requirements_addressed=session_data.get("requirements_addressed", [])
                    )
                    state.sessions.append(session)
    
    def record_session(
        self,
        gap_analysis: Dict,
        version_history: Dict,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Record a research session based on current state.
        
        Args:
            gap_analysis: Current gap analysis report
            version_history: Current version history
            session_id: Optional custom session ID
        
        Returns:
            Updated research log
        """
        session_id = session_id or datetime.now().strftime("%Y%m%d%H%M%S")
        timestamp = datetime.now().isoformat()
        
        logger.info(f"Recording research session: {session_id}")
        
        # Process each pillar
        for pillar_id, state in self.pillar_states.items():
            # Get current metrics from gap analysis
            pillar_metrics = self._extract_pillar_metrics(
                pillar_id, gap_analysis, version_history
            )
            
            # Calculate deltas from previous state
            coverage_delta = pillar_metrics["coverage"] - state.current_coverage
            papers_delta = pillar_metrics["papers"] - state.total_papers
            claims_delta = pillar_metrics["claims"] - state.total_claims
            
            # Create session record
            session = ResearchSession(
                session_id=session_id,
                timestamp=timestamp,
                papers_added=max(0, papers_delta),
                papers_removed=max(0, -papers_delta),
                claims_extracted=max(0, claims_delta),
                claims_approved=pillar_metrics["approved_claims"] - state.approved_claims,
                coverage_delta=coverage_delta,
                requirements_addressed=pillar_metrics.get("addressed_requirements", [])
            )
            
            # Update state
            state.sessions.append(session)
            state.current_coverage = pillar_metrics["coverage"]
            state.total_papers = pillar_metrics["papers"]
            state.total_claims = pillar_metrics["claims"]
            state.approved_claims = pillar_metrics["approved_claims"]
            
            # Record coverage history
            state.coverage_history.append((timestamp, pillar_metrics["coverage"]))
            
            # Recalculate metrics
            self._update_velocity_metrics(state)
            self._update_saturation_metrics(state)
            self._update_phase(state)
            self._generate_recommendation(state)
        
        return self._generate_log()
    
    def _extract_pillar_metrics(
        self,
        pillar_id: str,
        gap_analysis: Dict,
        version_history: Dict
    ) -> Dict:
        """Extract current metrics for a pillar from gap analysis."""
        metrics = {
            "coverage": 0.0,
            "papers": 0,
            "claims": 0,
            "approved_claims": 0,
            "addressed_requirements": []
        }
        
        # Find matching pillar in gap analysis
        for pillar_name, pillar_data in gap_analysis.items():
            if pillar_id in pillar_name:
                # Get coverage
                metrics["coverage"] = pillar_data.get(
                    "average_completeness",
                    pillar_data.get("completeness", 0)
                )
                
                # Count papers
                papers = set()
                analysis = pillar_data.get("analysis", {})
                for req_name, req_data in analysis.items():
                    if isinstance(req_data, dict):
                        for sub_name, sub_data in req_data.items():
                            if isinstance(sub_data, dict):
                                for paper in sub_data.get("contributing_papers", []):
                                    paper_id = paper.get("filename", paper) if isinstance(paper, dict) else paper
                                    papers.add(paper_id)
                                
                                if sub_data.get("completeness_percent", 0) > 50:
                                    metrics["addressed_requirements"].append(sub_name)
                
                metrics["papers"] = len(papers)
                break
        
        # Count claims from version history
        for paper_id, paper_data in version_history.items():
            claims = paper_data.get("claims", [])
            for claim in claims:
                pillar_mapping = claim.get("pillar", "")
                if pillar_id in pillar_mapping:
                    metrics["claims"] += 1
                    if claim.get("approved") or claim.get("status") == "approved":
                        metrics["approved_claims"] += 1
        
        return metrics
    
    def _update_velocity_metrics(self, state: PillarResearchState):
        """Update velocity metrics for a pillar."""
        if len(state.sessions) < 2:
            state.coverage_velocity = 0
            state.papers_per_session = 0
            return
        
        # Calculate coverage velocity (avg coverage change per session)
        recent_sessions = state.sessions[-5:]  # Last 5 sessions
        coverage_deltas = [s.coverage_delta for s in recent_sessions]
        state.coverage_velocity = statistics.mean(coverage_deltas) if coverage_deltas else 0
        
        # Calculate papers per session
        papers_added = sum(s.papers_added for s in recent_sessions)
        state.papers_per_session = papers_added / len(recent_sessions)
        
        # Calculate claims per paper
        if state.total_papers > 0:
            state.claims_per_paper = state.total_claims / state.total_papers
    
    def _update_saturation_metrics(self, state: PillarResearchState):
        """Update saturation metrics for a pillar."""
        if len(state.sessions) < 3:
            state.saturation_score = 0
            state.saturation_level = SaturationLevel.UNSATURATED
            return
        
        # Calculate saturation based on diminishing coverage gains
        recent_sessions = state.sessions[-5:]
        older_sessions = state.sessions[:-5] if len(state.sessions) > 5 else state.sessions[:2]
        
        recent_velocity = statistics.mean([s.coverage_delta for s in recent_sessions])
        
        if older_sessions:
            older_velocity = statistics.mean([s.coverage_delta for s in older_sessions])
        else:
            older_velocity = recent_velocity
        
        # Saturation increases when velocity decreases
        if older_velocity > 0:
            velocity_ratio = recent_velocity / older_velocity
            # Lower ratio = more saturation
            saturation_from_velocity = max(0, 1 - velocity_ratio)
        else:
            saturation_from_velocity = 0.5  # Neutral
        
        # Saturation also considers absolute coverage
        saturation_from_coverage = min(1, state.current_coverage / 100)
        
        # Combine factors
        state.saturation_score = (
            saturation_from_velocity * 0.6 + 
            saturation_from_coverage * 0.4
        )
        
        # Determine saturation level
        if state.saturation_score < 0.3:
            state.saturation_level = SaturationLevel.UNSATURATED
        elif state.saturation_score < 0.6:
            state.saturation_level = SaturationLevel.APPROACHING
        elif state.saturation_score < 0.85:
            state.saturation_level = SaturationLevel.SATURATED
        else:
            state.saturation_level = SaturationLevel.OVER_SATURATED
    
    def _update_phase(self, state: PillarResearchState):
        """Update research phase for a pillar."""
        previous_phase = state.research_phase
        
        # Determine phase based on coverage and saturation
        if state.current_coverage < 20:
            new_phase = ResearchPhase.INITIAL
        elif state.current_coverage < 50:
            new_phase = ResearchPhase.EXPLORATION
        elif state.current_coverage < 75:
            new_phase = ResearchPhase.CONSOLIDATION
        elif state.saturation_level in [SaturationLevel.SATURATED, SaturationLevel.OVER_SATURATED]:
            if state.approved_claims > 0 and state.approved_claims / max(1, state.total_claims) > 0.7:
                new_phase = ResearchPhase.COMPLETE
            else:
                new_phase = ResearchPhase.VALIDATION
        else:
            new_phase = ResearchPhase.CONSOLIDATION
        
        # Update phase tracking
        if new_phase != previous_phase:
            state.research_phase = new_phase
            state.phase_started_at = datetime.now().isoformat()
            state.sessions_in_phase = 0
        else:
            state.sessions_in_phase += 1
    
    def _generate_recommendation(self, state: PillarResearchState):
        """Generate focus recommendation for a pillar."""
        # Calculate focus priority (higher = needs more focus)
        
        # Low coverage = high priority
        coverage_factor = max(0, 1 - state.current_coverage / 100)
        
        # Low saturation = high priority (room to grow)
        saturation_factor = 1 - state.saturation_score
        
        # High velocity = high priority (productive area)
        velocity_factor = min(1, max(0, state.coverage_velocity / 5))
        
        state.focus_priority = (
            coverage_factor * 0.5 +
            saturation_factor * 0.3 +
            velocity_factor * 0.2
        )
        
        # Generate action recommendation
        if state.research_phase == ResearchPhase.COMPLETE:
            state.recommended_action = "Research concluded. Maintain and validate existing evidence."
        elif state.saturation_level == SaturationLevel.OVER_SATURATED:
            state.recommended_action = "Shift focus to other pillars. Diminishing returns detected."
        elif state.saturation_level == SaturationLevel.SATURATED:
            state.recommended_action = "Consider concluding research soon. Focus on validation."
        elif state.coverage_velocity > 3:
            state.recommended_action = "Continue current research strategy. Good progress."
        elif state.coverage_velocity < 0:
            state.recommended_action = "Review research strategy. Coverage is decreasing."
        elif state.current_coverage < 30:
            state.recommended_action = "Increase research intensity. Significant gaps remain."
        else:
            state.recommended_action = "Maintain steady research pace."
    
    def _generate_log(self) -> Dict:
        """Generate complete research log."""
        summary = self._calculate_summary()
        focus_recommendations = self._get_focus_recommendations()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "focus_recommendations": focus_recommendations,
            "pillars": {
                pillar_id: state.to_dict()
                for pillar_id, state in self.pillar_states.items()
            }
        }
    
    def _calculate_summary(self) -> Dict:
        """Calculate overall summary."""
        total_coverage = statistics.mean([
            s.current_coverage for s in self.pillar_states.values()
        ]) if self.pillar_states else 0
        
        total_papers = sum(s.total_papers for s in self.pillar_states.values())
        total_claims = sum(s.total_claims for s in self.pillar_states.values())
        total_approved = sum(s.approved_claims for s in self.pillar_states.values())
        
        saturated_count = sum(
            1 for s in self.pillar_states.values()
            if s.saturation_level in [SaturationLevel.SATURATED, SaturationLevel.OVER_SATURATED]
        )
        
        complete_count = sum(
            1 for s in self.pillar_states.values()
            if s.research_phase == ResearchPhase.COMPLETE
        )
        
        return {
            "total_pillars": len(self.pillar_states),
            "average_coverage": round(total_coverage, 1),
            "total_papers": total_papers,
            "total_claims": total_claims,
            "total_approved_claims": total_approved,
            "approval_rate": round(total_approved / max(1, total_claims) * 100, 1),
            "saturated_pillars": saturated_count,
            "complete_pillars": complete_count,
            "overall_velocity": round(statistics.mean([
                s.coverage_velocity for s in self.pillar_states.values()
            ]), 2) if self.pillar_states else 0
        }
    
    def _get_focus_recommendations(self) -> List[Dict]:
        """Get prioritized focus recommendations."""
        recommendations = []
        
        for pillar_id, state in self.pillar_states.items():
            recommendations.append({
                "pillar_id": pillar_id,
                "pillar_name": state.pillar_name,
                "focus_priority": state.focus_priority,
                "current_coverage": state.current_coverage,
                "saturation_level": state.saturation_level.value,
                "research_phase": state.research_phase.value,
                "recommended_action": state.recommended_action
            })
        
        # Sort by focus priority (highest first)
        return sorted(recommendations, key=lambda x: x["focus_priority"], reverse=True)
    
    def save_log(self, output_path: str) -> Dict:
        """Save research log to file."""
        log = self._generate_log()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved research log to {output_path}")
        return log
    
    def get_saturation_report(self) -> Dict:
        """Get saturation report for all pillars."""
        return {
            pillar_id: {
                "saturation_score": state.saturation_score,
                "saturation_level": state.saturation_level.value,
                "velocity": state.coverage_velocity,
                "phase": state.research_phase.value
            }
            for pillar_id, state in self.pillar_states.items()
        }
    
    def get_pillar_needing_focus(self) -> Optional[str]:
        """Get the pillar that most needs research focus."""
        if not self.pillar_states:
            return None
        
        # Filter out complete pillars
        active_pillars = [
            (pillar_id, state) for pillar_id, state in self.pillar_states.items()
            if state.research_phase != ResearchPhase.COMPLETE
        ]
        
        if not active_pillars:
            return None
        
        # Return pillar with highest focus priority
        return max(active_pillars, key=lambda x: x[1].focus_priority)[0]


def record_research_session(
    pillar_definitions_path: str,
    gap_analysis_path: str,
    version_history_path: str,
    output_path: str
) -> Dict:
    """
    Convenience function to record a research session.
    
    Args:
        pillar_definitions_path: Path to pillar definitions
        gap_analysis_path: Path to gap analysis report
        version_history_path: Path to version history
        output_path: Path to save research log
    
    Returns:
        Updated research log
    """
    with open(gap_analysis_path, 'r', encoding='utf-8') as f:
        gap_analysis = json.load(f)
    
    with open(version_history_path, 'r', encoding='utf-8') as f:
        version_history = json.load(f)
    
    manager = ResearchLogManager(
        pillar_definitions_path=pillar_definitions_path,
        log_path=output_path if Path(output_path).exists() else None
    )
    
    manager.record_session(gap_analysis, version_history)
    return manager.save_log(output_path)
