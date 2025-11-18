"""Gap Analysis with Evidence Decay Integration."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from literature_review.utils.evidence_decay import EvidenceDecayTracker

logger = logging.getLogger(__name__)


class GapAnalyzer:
    """
    Analyzes gaps with optional evidence decay weighting.
    
    This class integrates temporal evidence freshness into gap analysis completeness
    scoring. When enabled, it applies exponential decay weighting based on publication
    age, penalizing requirements supported by stale evidence.
    
    Example:
        >>> config = {'evidence_decay': {'weight_in_gap_analysis': True, 'decay_weight': 0.7}}
        >>> analyzer = GapAnalyzer(config=config)
        >>> papers = [{'filename': 'old.pdf', 'year': 2015, 'estimated_contribution_percent': 80}]
        >>> final_score, metadata = analyzer.apply_decay_weighting(80.0, papers)
        >>> print(f"Raw: {metadata['raw_score']}, Final: {metadata['final_score']}")
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize gap analyzer.
        
        Args:
            config: Configuration dictionary with evidence_decay settings
        """
        self.config = config or {}
        
        # Get decay configuration
        decay_config = self.config.get('evidence_decay', {})
        self.decay_enabled = decay_config.get('weight_in_gap_analysis', False)
        self.decay_weight = decay_config.get('decay_weight', 0.7)
        
        if self.decay_enabled:
            self.decay_tracker = EvidenceDecayTracker(config=self.config)
        else:
            self.decay_tracker = None
    
    def apply_decay_weighting(self, completeness_score: float, papers: List[Dict],
                             pillar_name: Optional[str] = None,
                             version_history: Optional[Dict] = None) -> Tuple[float, Dict]:
        """
        Apply decay weighting to a completeness score.
        
        Args:
            completeness_score: Raw completeness score (0-100)
            papers: List of contributing papers
            pillar_name: Name of the pillar being analyzed
            version_history: Version history for looking up publication years
        
        Returns:
            Tuple of (final_score, metadata_dict)
        """
        # Convert to 0-1 scale if needed
        raw_score = completeness_score / 100.0 if completeness_score > 1 else completeness_score
        
        # Check if decay should be applied
        if not self.decay_enabled or not self.decay_tracker:
            return completeness_score, {
                'raw_score': completeness_score,
                'final_score': completeness_score,
                'decay_applied': False
            }
        
        if not self.decay_tracker.should_apply_decay(pillar_name):
            return completeness_score, {
                'raw_score': completeness_score,
                'final_score': completeness_score,
                'decay_applied': False
            }
        
        if not papers:
            return completeness_score, {
                'raw_score': completeness_score,
                'final_score': completeness_score,
                'decay_applied': False,
                'reason': 'no_papers'
            }
        
        # Find the best contributing paper (highest contribution)
        # We use the paper with the highest estimated contribution as the basis for freshness
        best_paper = max(papers, key=lambda p: p.get('estimated_contribution_percent', 0))
        
        # Calculate freshness for the best paper
        freshness_score = self.decay_tracker.calculate_freshness_for_paper(
            best_paper, version_history
        )
        
        # Apply blended scoring: (1-weight)*raw + weight*decay_adjusted
        decay_adjusted_score = raw_score * freshness_score
        final_score = (1 - self.decay_weight) * raw_score + self.decay_weight * decay_adjusted_score
        
        # Convert back to 0-100 scale
        final_score_percent = final_score * 100 if completeness_score > 1 else final_score
        
        metadata = {
            'raw_score': completeness_score,
            'freshness_score': round(freshness_score, 3),
            'final_score': round(final_score_percent, 2),
            'best_paper': best_paper.get('filename', 'unknown'),
            'best_paper_year': best_paper.get('year'),
            'decay_applied': True,
            'decay_weight': self.decay_weight
        }
        
        return final_score_percent, metadata
    
    def generate_decay_impact_report(self, pillar_name: str, requirements: Dict,
                                    analysis_results: Dict,
                                    version_history: Optional[Dict] = None) -> Dict:
        """
        Generate A/B comparison report showing decay impact.
        
        Args:
            pillar_name: Name of the pillar
            requirements: Requirements dictionary
            analysis_results: Analysis results with contributing papers
            version_history: Version history for publication years
        
        Returns:
            Report dictionary with comparison data
        """
        # Create analyzers with/without decay
        config_no_decay = {**self.config}
        if 'evidence_decay' in config_no_decay:
            config_no_decay['evidence_decay'] = {
                **config_no_decay['evidence_decay'],
                'weight_in_gap_analysis': False
            }
        
        analyzer_no_decay = GapAnalyzer(config=config_no_decay)
        analyzer_with_decay = GapAnalyzer(config=self.config)
        
        comparison_report = []
        
        # Iterate through all requirements
        for req_key, req_data in requirements.items():
            if req_key not in analysis_results:
                continue
            
            for sub_req in req_data:
                if sub_req not in analysis_results[req_key]:
                    continue
                
                result = analysis_results[req_key][sub_req]
                raw_score = result.get('completeness_percent', 0)
                papers = result.get('contributing_papers', [])
                
                # Calculate scores with and without decay
                score_no_decay, _ = analyzer_no_decay.apply_decay_weighting(
                    raw_score, papers, pillar_name, version_history
                )
                score_with_decay, metadata = analyzer_with_decay.apply_decay_weighting(
                    raw_score, papers, pillar_name, version_history
                )
                
                delta = score_with_decay - score_no_decay
                delta_pct = (delta / score_no_decay * 100) if score_no_decay > 0 else 0
                
                impact = 'decreased' if delta < -0.05 else 'increased' if delta > 0.05 else 'minimal'
                
                comparison_report.append({
                    'requirement': sub_req,
                    'score_no_decay': round(score_no_decay, 3),
                    'score_with_decay': round(score_with_decay, 3),
                    'delta': round(delta, 3),
                    'delta_pct': round(delta_pct, 1),
                    'freshness': metadata.get('freshness_score', 0),
                    'impact': impact
                })
        
        # Calculate summary statistics
        if comparison_report:
            avg_delta = sum(r['delta'] for r in comparison_report) / len(comparison_report)
            significant_changes = [r for r in comparison_report if abs(r['delta']) > 0.1]
        else:
            avg_delta = 0
            significant_changes = []
        
        return {
            'pillar': pillar_name,
            'requirements': comparison_report,
            'summary': {
                'total_requirements': len(comparison_report),
                'avg_delta': round(avg_delta, 3),
                'significant_changes': len(significant_changes),
                'impact_breakdown': {
                    'decreased': len([r for r in comparison_report if r['impact'] == 'decreased']),
                    'increased': len([r for r in comparison_report if r['impact'] == 'increased']),
                    'minimal': len([r for r in comparison_report if r['impact'] == 'minimal'])
                }
            }
        }


def load_config(config_file: str = 'pipeline_config.json') -> Dict:
    """Load pipeline configuration."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load config from {config_file}: {e}")
        return {}
