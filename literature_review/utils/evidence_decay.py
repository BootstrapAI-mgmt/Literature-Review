"""Evidence Decay Tracker - temporal weighting of evidence."""

import json
from datetime import datetime
from typing import Dict, List, Optional
import math
import logging
import os

logger = logging.getLogger(__name__)


class EvidenceDecayTracker:
    """Track and weight evidence based on publication age."""
    
    def __init__(self, half_life_years: float = 5.0, config: Optional[Dict] = None):
        """
        Initialize decay tracker.
        
        Args:
            half_life_years: Years for evidence value to decay to 50%
            config: Optional configuration dictionary with evidence_decay settings
        """
        if config and 'evidence_decay' in config:
            decay_config = config['evidence_decay']
            self.half_life = decay_config.get('half_life_years', half_life_years)
            self.enabled = decay_config.get('enabled', True)
            self.weight_in_gap_analysis = decay_config.get('weight_in_gap_analysis', False)
            self.decay_weight = decay_config.get('decay_weight', 0.7)
            self.apply_to_pillars = decay_config.get('apply_to_pillars', ['all'])
            self.min_freshness_threshold = decay_config.get('min_freshness_threshold', 0.3)
        else:
            self.half_life = half_life_years
            self.enabled = True
            self.weight_in_gap_analysis = False
            self.decay_weight = 0.7
            self.apply_to_pillars = ['all']
            self.min_freshness_threshold = 0.3
        
        self.current_year = datetime.now().year
    
    def calculate_decay_weight(self, publication_year: int) -> float:
        """
        Calculate decay weight for a paper.
        
        Uses exponential decay: weight = 2^(-age / half_life)
        
        Args:
            publication_year: Year of publication
        
        Returns:
            Decay weight (0-1, where 1 = current year)
        """
        if publication_year > self.current_year:
            # Future publication (preprint?) - use current year
            publication_year = self.current_year
        
        age_years = self.current_year - publication_year
        
        # Exponential decay
        weight = math.pow(2, -age_years / self.half_life)
        
        return round(weight, 3)
    
    def calculate_freshness_for_paper(self, paper: Dict, version_history: Optional[Dict] = None) -> float:
        """
        Calculate freshness score for a single paper.
        
        Args:
            paper: Paper dictionary with 'filename' or 'year' field
            version_history: Optional version history to look up publication years
        
        Returns:
            Freshness score (0-1, where 1 = current year)
        """
        year = paper.get('year')
        
        # Try to get year from version history if not provided
        if not year and version_history:
            filename = paper.get('filename', '')
            if filename in version_history:
                versions = version_history[filename]
                if versions and isinstance(versions, list):
                    latest_version = versions[-1]
                    if 'review' in latest_version:
                        year = latest_version['review'].get('PUBLICATION_YEAR')
        
        # Use neutral freshness if year is unknown
        if not year:
            return 0.5
        
        return self.calculate_decay_weight(year)
    
    def should_apply_decay(self, pillar_name: Optional[str] = None) -> bool:
        """
        Check if decay should be applied to a given pillar.
        
        Args:
            pillar_name: Name of the pillar (optional)
        
        Returns:
            True if decay should be applied, False otherwise
        """
        if not self.enabled or not self.weight_in_gap_analysis:
            return False
        
        if 'all' in self.apply_to_pillars:
            return True
        
        return pillar_name in self.apply_to_pillars if pillar_name else True
    
    def analyze_evidence_freshness(self, review_log_file: str, gap_analysis_file: str) -> Dict:
        """Analyze freshness of evidence for each requirement."""
        logger.info("Analyzing evidence freshness...")
        
        # Load version history to get publication years
        version_history = self._load_version_history(review_log_file)
        
        with open(gap_analysis_file, 'r') as f:
            gap_data = json.load(f)
        
        # Analyze each requirement
        freshness_analysis = {}
        
        # The gap_data uses pillar names as keys, not a 'pillars' array
        for pillar_name, pillar_data in gap_data.items():
            if not isinstance(pillar_data, dict) or 'analysis' not in pillar_data:
                continue
            
            analysis = pillar_data['analysis']
            
            for req_name, req_data in analysis.items():
                for sub_req_name, sub_req_data in req_data.items():
                    # Get contributing papers
                    papers = sub_req_data.get('contributing_papers', [])
                    
                    if not papers:
                        continue
                    
                    # Add publication years to papers
                    papers_with_years = self._add_publication_years(papers, version_history)
                    
                    # Calculate freshness metrics
                    freshness = self._calculate_freshness_metrics(papers_with_years, sub_req_data)
                    
                    req_id = sub_req_name  # Use sub-requirement name as ID
                    
                    freshness_analysis[req_id] = {
                        'requirement': sub_req_name,
                        'pillar': pillar_name,
                        'paper_count': len(papers_with_years),
                        'avg_age_years': freshness['avg_age'],
                        'oldest_paper_year': freshness['oldest_year'],
                        'newest_paper_year': freshness['newest_year'],
                        'avg_decay_weight': freshness['avg_weight'],
                        'freshness_score': freshness['freshness_score'],
                        'needs_update': freshness['needs_update'],
                        'papers': freshness['papers']
                    }
        
        return {
            'analysis_date': datetime.now().isoformat(),
            'current_year': self.current_year,
            'half_life_years': self.half_life,
            'requirement_analysis': freshness_analysis,
            'summary': self._generate_summary(freshness_analysis)
        }
    
    def _load_version_history(self, review_log_file: str) -> Dict:
        """Load version history or return empty dict."""
        # First try to load review_version_history.json
        base_dir = os.path.dirname(review_log_file) if os.path.dirname(review_log_file) else '.'
        version_file = os.path.join(base_dir, 'review_version_history.json')
        
        if not os.path.exists(version_file):
            version_file = 'review_version_history.json'
        
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load version history from {version_file}: {e}")
        
        return {}
    
    def _add_publication_years(self, papers: List[Dict], version_history: Dict) -> List[Dict]:
        """Add publication years to papers from version history."""
        papers_with_years = []
        default_year = self.current_year - 3  # Default to 3 years ago
        
        for paper in papers:
            filename = paper.get('filename', '')
            pub_year = default_year
            
            # Try to get publication year from version history
            if filename in version_history:
                versions = version_history[filename]
                if versions and isinstance(versions, list):
                    latest_version = versions[-1]  # Get latest version
                    if 'review' in latest_version:
                        pub_year = latest_version['review'].get('PUBLICATION_YEAR', default_year)
            
            paper_with_year = {
                **paper,
                'year': pub_year,
                'title': filename,  # Use filename as title if not available
                'alignment': paper.get('estimated_contribution_percent', 0) / 100.0  # Convert percent to 0-1
            }
            papers_with_years.append(paper_with_year)
        
        return papers_with_years
    
    def _calculate_freshness_metrics(self, papers: List[Dict], sub_req_data: Dict) -> Dict:
        """Calculate freshness metrics for a set of papers."""
        if not papers:
            return {
                'avg_age': 0,
                'oldest_year': 0,
                'newest_year': 0,
                'avg_weight': 0,
                'freshness_score': 0,
                'needs_update': True,
                'papers': []
            }
        
        years = [p['year'] for p in papers]
        weights = [self.calculate_decay_weight(y) for y in years]
        
        avg_age = self.current_year - (sum(years) / len(years))
        avg_weight = sum(weights) / len(weights)
        
        # Freshness score: weighted average of alignment scores
        weighted_alignments = sum(p['alignment'] * self.calculate_decay_weight(p['year']) 
                                 for p in papers)
        total_weights = sum(self.calculate_decay_weight(p['year']) for p in papers)
        freshness_score = weighted_alignments / total_weights if total_weights > 0 else 0
        
        # Needs update if avg weight < 0.5 (evidence more than 1 half-life old)
        needs_update = avg_weight < 0.5
        
        # Add decay weights to papers
        papers_with_weights = [
            {
                **p,
                'decay_weight': self.calculate_decay_weight(p['year']),
                'age_years': self.current_year - p['year']
            }
            for p in papers
        ]
        
        return {
            'avg_age': round(avg_age, 1),
            'oldest_year': min(years),
            'newest_year': max(years),
            'avg_weight': round(avg_weight, 2),
            'freshness_score': round(freshness_score, 2),
            'needs_update': needs_update,
            'papers': papers_with_weights
        }
    
    def _generate_summary(self, freshness_analysis: Dict) -> Dict:
        """Generate summary statistics."""
        if not freshness_analysis:
            return {
                'total_requirements': 0,
                'needs_update_count': 0,
                'avg_evidence_age_years': 0,
                'avg_freshness_score': 0
            }
        
        needs_update = sum(1 for r in freshness_analysis.values() if r['needs_update'])
        avg_age = sum(r['avg_age_years'] for r in freshness_analysis.values()) / len(freshness_analysis)
        avg_freshness = sum(r['freshness_score'] for r in freshness_analysis.values()) / len(freshness_analysis)
        
        return {
            'total_requirements': len(freshness_analysis),
            'needs_update_count': needs_update,
            'avg_evidence_age_years': round(avg_age, 1),
            'avg_freshness_score': round(avg_freshness, 2)
        }


def generate_decay_report(review_log: str, gap_analysis: str, 
                         output_file: str = 'gap_analysis_output/evidence_decay.json',
                         half_life_years: float = 5.0):
    """Generate evidence decay report."""
    tracker = EvidenceDecayTracker(half_life_years=half_life_years)
    report = tracker.analyze_evidence_freshness(review_log, gap_analysis)
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n" + "="*60)
    print("EVIDENCE DECAY ANALYSIS")
    print("="*60)
    
    summary = report['summary']
    print(f"\nSummary:")
    print(f"  Requirements Analyzed: {summary['total_requirements']}")
    print(f"  Need Updated Searches: {summary['needs_update_count']}")
    print(f"  Avg Evidence Age: {summary['avg_evidence_age_years']} years")
    print(f"  Avg Freshness Score: {summary['avg_freshness_score']}")
    
    print(f"\n⚠️ Requirements Needing Update (Top 5):")
    stale = sorted(
        [(req_id, data) for req_id, data in report['requirement_analysis'].items() if data['needs_update']],
        key=lambda x: x[1]['avg_age_years'],
        reverse=True
    )
    for req_id, data in stale[:5]:
        req_text = data['requirement'][:60] + "..." if len(data['requirement']) > 60 else data['requirement']
        print(f"  {req_id}: {req_text}")
        print(f"    Avg Age: {data['avg_age_years']} years, Weight: {data['avg_decay_weight']}")
    
    print("\n" + "="*60)
    print(f"Full report saved to: {output_file}")
    print("="*60 + "\n")
    
    return report
