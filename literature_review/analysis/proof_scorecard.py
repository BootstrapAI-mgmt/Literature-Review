"""
Proof Completeness Scorecard
Assesses publication readiness and provides strategic guidance.
"""

import json
import os
from typing import Dict, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProofScorecardAnalyzer:
    """Analyze publication readiness across research goals."""
    
    # Publication thresholds
    TIER_1_JOURNAL_THRESHOLD = 80  # Nature, Science
    TIER_2_JOURNAL_THRESHOLD = 60  # Specialized journals
    CONFERENCE_THRESHOLD = 40      # Conference papers
    PREPRINT_THRESHOLD = 0         # arXiv (any quality)
    
    # Minimum viable completeness per pillar for system integration
    PILLAR_7_REQUIREMENTS = {
        'Pillar 1': 40,
        'Pillar 2': 50,
        'Pillar 3': 40,
        'Pillar 4': 60,
        'Pillar 5': 30,
        'Pillar 6': 40,
        'Pillar 7': 50
    }
    
    def __init__(self, gap_report: Dict, version_history: Dict, pillar_definitions: Dict):
        self.gap_report = gap_report
        self.version_history = version_history
        self.pillar_definitions = pillar_definitions
    
    def _find_pillar_data(self, pillar_short_name: str) -> Dict:
        """Find pillar data by short name (e.g., 'Pillar 1' matches 'Pillar 1: ...')."""
        # Try exact match first
        if pillar_short_name in self.gap_report:
            return self.gap_report[pillar_short_name]
        
        # Try prefix match
        for key, value in self.gap_report.items():
            if key.startswith(pillar_short_name + ':') or key.startswith(pillar_short_name + ' '):
                return value
        
        return {}
    
    def analyze(self) -> Dict:
        """Generate complete proof scorecard."""
        
        # Overall proof readiness
        overall_score = self._calculate_overall_proof_readiness()
        
        # Research goal breakdown
        research_goals = self._analyze_research_goals()
        
        # Proof requirements checklist
        proof_checklist = self._generate_proof_checklist()
        
        # Publication viability
        pub_viability = self._assess_publication_viability(overall_score)
        
        # Critical next steps
        next_steps = self._generate_critical_next_steps(research_goals)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_proof_status': {
                'proof_readiness_score': overall_score,
                'verdict': self._get_verdict(overall_score),
                'headline': self._generate_headline(overall_score)
            },
            'research_goals': research_goals,
            'proof_requirements_checklist': proof_checklist,
            'publication_viability': pub_viability,
            'critical_next_steps': next_steps,
            'pillar_7_readiness': self._assess_pillar_7_readiness()
        }
    
    def _calculate_overall_proof_readiness(self) -> float:
        """
        Calculate overall proof readiness (0-100).
        
        Weighted average of pillar completeness, with bonus for:
        - Evidence quality (triangulation, methodological rigor)
        - Cross-pillar integration (bio-AI bridges)
        """
        total_weighted_score = 0
        total_weight = 0
        
        for pillar_name, pillar_data in self.gap_report.items():
            if not isinstance(pillar_data, dict):
                continue
            
            # Base completeness
            completeness = pillar_data.get('completeness', pillar_data.get('average_completeness', 0))
            
            # Weight: Foundational pillars count more
            weight = 1.5 if pillar_name in ['Pillar 1', 'Pillar 3', 'Pillar 5'] else 1.0
            
            total_weighted_score += completeness * weight
            total_weight += weight
        
        avg_score = total_weighted_score / total_weight if total_weight > 0 else 0
        
        return round(avg_score, 1)
    
    def _analyze_research_goals(self) -> List[Dict]:
        """
        Analyze each major research goal.
        
        Goals:
        1. Biological mechanisms fully characterized (Pillars 1, 3, 5)
        2. AI implementations faithfully emulate biology (Pillars 2, 4, 6)
        3. Integrated system demonstrates bio-fidelity (Pillar 7)
        """
        goals = []
        
        # Goal 1: Biological Foundations
        bio_pillars = ['Pillar 1', 'Pillar 3', 'Pillar 5']
        bio_completeness = self._get_average_completeness(bio_pillars)
        bio_sufficiency = self._estimate_sufficiency(bio_pillars)
        
        goals.append({
            'goal': 'Biological stimulus-response mechanisms are fully characterized',
            'pillars': bio_pillars,
            'completeness': bio_completeness,
            'sufficiency': bio_sufficiency,
            'proof_status': self._get_proof_status(bio_sufficiency),
            'blocking_factors': self._identify_blocking_factors(bio_pillars),
            'minimum_viable': 40,
            'current_deficit': max(0, 40 - bio_completeness),
            'estimated_papers_needed': self._estimate_papers_needed(40 - bio_completeness),
            'estimated_timeline_weeks': self._estimate_timeline(40 - bio_completeness)
        })
        
        # Goal 2: AI Implementation Fidelity
        ai_pillars = ['Pillar 2', 'Pillar 4', 'Pillar 6']
        ai_completeness = self._get_average_completeness(ai_pillars)
        ai_sufficiency = self._estimate_sufficiency(ai_pillars)
        
        goals.append({
            'goal': 'AI implementations faithfully emulate biological mechanisms',
            'pillars': ai_pillars,
            'completeness': ai_completeness,
            'sufficiency': ai_sufficiency,
            'proof_status': self._get_proof_status(ai_sufficiency),
            'blocking_factors': self._identify_blocking_factors(ai_pillars),
            'dependency': 'Requires Goal 1 (biological foundations) to be proven first',
            'minimum_viable': 50,
            'current_deficit': max(0, 50 - ai_completeness),
            'estimated_papers_needed': self._estimate_papers_needed(50 - ai_completeness),
            'estimated_timeline_weeks': self._estimate_timeline(50 - ai_completeness)
        })
        
        # Goal 3: System Integration
        p7_completeness = self._get_average_completeness(['Pillar 7'])
        p7_sufficiency = self._estimate_sufficiency(['Pillar 7'])
        
        goals.append({
            'goal': 'Integrated neuromorphic system demonstrates biological fidelity and computational efficiency',
            'pillars': ['Pillar 7'],
            'completeness': p7_completeness,
            'sufficiency': p7_sufficiency,
            'proof_status': self._get_proof_status(p7_sufficiency),
            'blocking_factors': ['ALL other pillars must reach minimum thresholds first'],
            'dependency': 'Requires Goals 1 and 2',
            'minimum_viable': 50,
            'current_deficit': max(0, 50 - p7_completeness),
            'blocking_pillars': self._identify_blocking_pillars_for_p7()
        })
        
        return goals
    
    def _get_average_completeness(self, pillars: List[str]) -> float:
        """Calculate average completeness for a set of pillars."""
        total = 0
        count = 0
        
        for pillar_name in pillars:
            pillar_data = self._find_pillar_data(pillar_name)
            if pillar_data and isinstance(pillar_data, dict):
                total += pillar_data.get('completeness', pillar_data.get('average_completeness', 0))
                count += 1
        
        return round(total / count, 1) if count > 0 else 0
    
    def _estimate_sufficiency(self, pillars: List[str]) -> float:
        """
        Estimate evidence sufficiency (quality-adjusted completeness).
        
        Simplified version - full version in Wave 2 (Evidence Sufficiency Matrix)
        """
        completeness = self._get_average_completeness(pillars)
        
        # Simple quality penalty for now
        # Assume 30% reduction due to single-source claims, lack of triangulation
        sufficiency = completeness * 0.7
        
        return round(sufficiency, 1)
    
    def _get_proof_status(self, sufficiency: float) -> str:
        """Determine proof status based on sufficiency."""
        if sufficiency >= 80:
            return 'PROVEN'
        elif sufficiency >= 60:
            return 'PROBABLE'
        elif sufficiency >= 40:
            return 'POSSIBLE'
        elif sufficiency >= 20:
            return 'INSUFFICIENT'
        else:
            return 'UNPROVEN'
    
    def _identify_blocking_factors(self, pillars: List[str]) -> List[str]:
        """Identify specific blockers preventing proof."""
        blockers = []
        
        for pillar_name in pillars:
            pillar_data = self._find_pillar_data(pillar_name)
            if not pillar_data or not isinstance(pillar_data, dict):
                continue
            
            completeness = pillar_data.get('completeness', pillar_data.get('average_completeness', 0))
            
            if completeness < 10:
                blockers.append(f"{pillar_name} severely incomplete ({completeness:.0f}%)")
            
            # Check for 0% sub-requirements
            if 'analysis' in pillar_data:
                zero_gaps = []
                for req_key, req_data in pillar_data['analysis'].items():
                    for sub_req_key, sub_req_data in req_data.items():
                        if sub_req_data.get('completeness_percent', 0) == 0:
                            zero_gaps.append(sub_req_key)
                
                if len(zero_gaps) > 5:
                    blockers.append(f"{pillar_name}: {len(zero_gaps)} completely unfilled gaps")
        
        return blockers if blockers else ['Insufficient evidence quality and triangulation']
    
    def _estimate_papers_needed(self, deficit: float) -> int:
        """Estimate papers needed to close deficit."""
        # Assume each paper provides ~15% coverage on average
        return max(1, int(deficit / 15))
    
    def _estimate_timeline(self, deficit: float) -> int:
        """Estimate weeks to close deficit."""
        papers_needed = self._estimate_papers_needed(deficit)
        # Assume 2.5 hours per paper (search + review + judge)
        hours_needed = papers_needed * 2.5
        # Assume 10 hours research per week
        weeks = max(1, int(hours_needed / 10))
        return weeks
    
    def _generate_proof_checklist(self) -> Dict:
        """Generate proof requirements checklist."""
        total_reqs = 0
        proven = 0
        probable = 0
        possible = 0
        insufficient = 0
        unproven = 0
        
        for pillar_name, pillar_data in self.gap_report.items():
            if not isinstance(pillar_data, dict) or 'analysis' not in pillar_data:
                continue
            
            for req_key, req_data in pillar_data['analysis'].items():
                for sub_req_key, sub_req_data in req_data.items():
                    total_reqs += 1
                    
                    # Estimate sufficiency (simplified)
                    completeness = sub_req_data.get('completeness_percent', 0)
                    sufficiency = completeness * 0.7  # Quality penalty
                    
                    if sufficiency >= 80:
                        proven += 1
                    elif sufficiency >= 60:
                        probable += 1
                    elif sufficiency >= 40:
                        possible += 1
                    elif sufficiency >= 20:
                        insufficient += 1
                    else:
                        unproven += 1
        
        return {
            'total_requirements': total_reqs,
            'proven': proven,
            'probable': probable,
            'possible': possible,
            'insufficient': insufficient,
            'unproven': unproven,
            'percent_proven': round((proven / total_reqs * 100), 1) if total_reqs > 0 else 0
        }
    
    def _assess_publication_viability(self, overall_score: float) -> Dict:
        """Assess which publication venues are viable."""
        return {
            'tier_1_journal': overall_score >= self.TIER_1_JOURNAL_THRESHOLD,
            'tier_2_journal': overall_score >= self.TIER_2_JOURNAL_THRESHOLD,
            'conference_paper': 'MAYBE' if overall_score >= self.CONFERENCE_THRESHOLD else 'NO',
            'preprint': True,
            'recommended_venue': self._recommend_venue(overall_score)
        }
    
    def _recommend_venue(self, overall_score: float) -> str:
        """Recommend publication venue based on score."""
        if overall_score >= 80:
            return 'Tier 1 journal (Nature, Science, etc.)'
        elif overall_score >= 60:
            return 'Tier 2 specialized journal'
        elif overall_score >= 40:
            return 'Conference paper or workshop'
        else:
            return 'Preprint → build evidence → resubmit in 3-6 months'
    
    def _generate_critical_next_steps(self, research_goals: List[Dict]) -> List[str]:
        """Generate prioritized action items."""
        steps = []
        
        # Find most critical blockers
        for i, goal in enumerate(research_goals, 1):
            if goal['proof_status'] in ['UNPROVEN', 'INSUFFICIENT']:
                if 'blocking_factors' in goal and goal['blocking_factors']:
                    steps.append(
                        f"{i}. Address {goal['goal'][:50]}... - "
                        f"{goal['blocking_factors'][0]}"
                    )
        
        # Add strategic recommendations
        if len(steps) < 3:
            steps.append("3. Find independent replications for single-source claims (triangulation)")
            steps.append("4. Re-assess in 4-6 weeks after targeted search")
        
        return steps[:5]  # Top 5 only
    
    def _assess_pillar_7_readiness(self) -> Dict:
        """Assess readiness for Pillar 7 (system integration)."""
        blocking_pillars = self._identify_blocking_pillars_for_p7()
        
        current_readiness = self._get_average_completeness(['Pillar 7'])
        
        return {
            'description': 'System Integration requires ALL pillars to reach minimum thresholds',
            'current_readiness': current_readiness,
            'target_readiness': 60,
            'blocking_pillars': blocking_pillars,
            'ready_for_integration': len(blocking_pillars) == 0,
            'estimated_papers_to_readiness': sum(p['papers_needed'] for p in blocking_pillars),
            'earliest_possible_date': self._estimate_earliest_integration_date(blocking_pillars)
        }
    
    def _identify_blocking_pillars_for_p7(self) -> List[Dict]:
        """Identify pillars blocking Pillar 7 integration."""
        blockers = []
        
        for pillar_name, min_threshold in self.PILLAR_7_REQUIREMENTS.items():
            if pillar_name == 'Pillar 7':
                continue
            
            pillar_data = self._find_pillar_data(pillar_name)
            if not pillar_data or not isinstance(pillar_data, dict):
                continue
            
            completeness = pillar_data.get('completeness', pillar_data.get('average_completeness', 0))
            
            if completeness < min_threshold:
                deficit = min_threshold - completeness
                blockers.append({
                    'pillar': pillar_name,
                    'completeness': completeness,
                    'threshold': min_threshold,
                    'deficit': deficit,
                    'papers_needed': self._estimate_papers_needed(deficit)
                })
        
        return blockers
    
    def _estimate_earliest_integration_date(self, blocking_pillars: List[Dict]) -> str:
        """Estimate when Pillar 7 integration could begin."""
        if not blocking_pillars:
            return 'NOW - All prerequisites met'
        
        total_deficit = sum(p['deficit'] for p in blocking_pillars)
        weeks = self._estimate_timeline(total_deficit)
        
        # Add buffer for comprehensive testing
        weeks += 4
        
        if weeks <= 12:
            return f'{weeks} weeks (Q1 2026)'
        elif weeks <= 26:
            return f'{weeks} weeks (Q2 2026)'
        else:
            return f'{weeks} weeks (Q3-Q4 2026)'
    
    def _get_verdict(self, score: float) -> str:
        """Get overall verdict."""
        if score >= 80:
            return 'PUBLICATION_READY'
        elif score >= 60:
            return 'NEAR_READY'
        elif score >= 40:
            return 'PROGRESS_NEEDED'
        elif score >= 20:
            return 'SIGNIFICANT_GAPS'
        else:
            return 'INSUFFICIENT_FOR_PUBLICATION'
    
    def _generate_headline(self, score: float) -> str:
        """Generate headline summary."""
        if score >= 80:
            return 'Research goals sufficiently proven for publication'
        elif score >= 60:
            return 'Close to publication readiness - address key gaps'
        elif score >= 40:
            return 'Moderate progress - targeted search needed'
        elif score >= 20:
            return 'Significant gaps remain - systematic literature search required'
        else:
            return 'Cannot prove neuromorphic framework with current evidence'


def generate_scorecard(gap_analysis_file: str, version_history_file: str, 
                      pillar_definitions_file: str, output_dir: str):
    """Generate proof scorecard and save outputs."""
    
    # Load data
    with open(gap_analysis_file, 'r') as f:
        gap_report = json.load(f)
    
    # Handle version history (may not exist, use empty dict as fallback)
    version_history = {}
    if os.path.exists(version_history_file):
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
    else:
        logger.warning(f"Version history file not found: {version_history_file}, using empty dict")
    
    with open(pillar_definitions_file, 'r') as f:
        pillar_definitions = json.load(f)
    
    # Analyze
    analyzer = ProofScorecardAnalyzer(gap_report, version_history, pillar_definitions)
    scorecard = analyzer.analyze()
    
    # Save JSON
    os.makedirs(output_dir, exist_ok=True)
    json_output = os.path.join(output_dir, 'proof_scorecard.json')
    with open(json_output, 'w') as f:
        json.dump(scorecard, f, indent=2)
    
    logger.info(f"Saved scorecard to {json_output}")
    
    return scorecard


def main():
    """CLI entry point."""
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    scorecard = generate_scorecard(
        gap_analysis_file='gap_analysis_output/gap_analysis_report.json',
        version_history_file='review_version_history.json',
        pillar_definitions_file='pillar_definitions.json',
        output_dir='proof_scorecard_output'
    )
    
    # Generate HTML visualization
    try:
        from .proof_scorecard_viz import generate_html
        html_output = os.path.join('proof_scorecard_output', 'proof_readiness.html')
        generate_html(scorecard, html_output)
        logger.info(f"Saved HTML visualization to {html_output}")
    except Exception as e:
        logger.warning(f"Could not generate HTML visualization: {e}")
    
    # Print summary
    print("\n" + "="*60)
    print("PROOF COMPLETENESS SCORECARD")
    print("="*60)
    print(f"\nOverall Readiness: {scorecard['overall_proof_status']['proof_readiness_score']:.1f}%")
    print(f"Verdict: {scorecard['overall_proof_status']['verdict']}")
    print(f"\n{scorecard['overall_proof_status']['headline']}")
    print("\nPublication Viability:")
    for venue, viable in scorecard['publication_viability'].items():
        if venue != 'recommended_venue':
            print(f"  {venue}: {viable}")
    print(f"\nRecommended: {scorecard['publication_viability']['recommended_venue']}")
    print("\nCritical Next Steps:")
    for step in scorecard['critical_next_steps']:
        print(f"  {step}")
    print("\n" + "="*60)


if __name__ == '__main__':
    main()
