"""Gap Analysis with Evidence Decay Integration and Gap Extraction Engine."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from literature_review.utils.evidence_decay import EvidenceDecayTracker

logger = logging.getLogger(__name__)


@dataclass
class Gap:
    """Represents a research gap (sub-requirement with low completeness)."""
    
    pillar: str                    # e.g., "Pillar 1: Foundational Architecture"
    requirement_id: str            # e.g., "REQ-001"
    sub_requirement_id: str        # e.g., "SUB-001"
    requirement_text: str          # Full text of the requirement
    current_completeness: float    # 0-100 percentage
    evidence_count: int            # Number of supporting papers
    severity: str                  # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    suggested_searches: List[str] = field(default_factory=list)  # Optional: From gap analysis report
    
    @property
    def gap_id(self) -> str:
        """Unique identifier for this gap."""
        return f"{self.requirement_id}-{self.sub_requirement_id}"
    
    @property
    def gap_percentage(self) -> float:
        """Inverse of completeness (100 - completeness)."""
        return 100.0 - self.current_completeness


class GapAnalyzer:
    """
    Analyzes gaps with optional evidence decay weighting and extracts research gaps.
    
    This class integrates temporal evidence freshness into gap analysis completeness
    scoring. When enabled, it applies exponential decay weighting based on publication
    age, penalizing requirements supported by stale evidence.
    
    It also provides gap extraction functionality to identify sub-requirements with
    low completeness scores from gap analysis reports.
    
    Example:
        >>> config = {'evidence_decay': {'weight_in_gap_analysis': True, 'decay_weight': 0.7}}
        >>> analyzer = GapAnalyzer(config=config)
        >>> papers = [{'filename': 'old.pdf', 'year': 2015, 'estimated_contribution_percent': 80}]
        >>> final_score, metadata = analyzer.apply_decay_weighting(80.0, papers)
        >>> print(f"Raw: {metadata['raw_score']}, Final: {metadata['final_score']}")
        
        >>> # Gap extraction example
        >>> with open('gap_analysis_output/gap_analysis_report.json') as f:
        ...     report = json.load(f)
        >>> gaps = analyzer.extract_gaps(report)
        >>> print(f"Found {len(gaps)} gaps")
    """
    
    def __init__(self, config: Optional[Dict] = None, completeness_threshold: float = 0.8):
        """
        Initialize gap analyzer.
        
        Args:
            config: Configuration dictionary with evidence_decay settings
            completeness_threshold: Threshold below which a sub-requirement
                                   is considered a gap (0.0-1.0). Default: 0.8 (80%)
        """
        self.config = config or {}
        self.completeness_threshold = completeness_threshold
        self.severity_thresholds = {
            "CRITICAL": 0.3,   # < 30% completeness
            "HIGH": 0.5,       # 30-50% completeness
            "MEDIUM": 0.7,     # 50-70% completeness
            "LOW": 0.8         # 70-80% completeness
        }
        
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
    
    def extract_gaps(
        self,
        report: Dict,
        threshold: Optional[float] = None
    ) -> List[Gap]:
        """
        Extract gaps from gap analysis report.
        
        Args:
            report: Gap analysis report (loaded from gap_analysis_report.json)
            threshold: Override default completeness threshold
        
        Returns:
            List of Gap objects sorted by severity (critical first)
        
        Example:
            >>> analyzer = GapAnalyzer()
            >>> with open('gap_analysis_output/gap_analysis_report.json') as f:
            ...     report = json.load(f)
            >>> gaps = analyzer.extract_gaps(report)
            >>> print(f"Found {len(gaps)} gaps")
            Found 23 gaps
        """
        threshold = threshold or self.completeness_threshold
        gaps = []
        
        # Navigate report structure
        pillars = report.get('pillars', {})
        
        for pillar_name, pillar_data in pillars.items():
            requirements = pillar_data.get('requirements', {})
            
            for req_id, req_data in requirements.items():
                sub_requirements = req_data.get('sub_requirements', {})
                
                for sub_req_id, sub_req_data in sub_requirements.items():
                    completeness = sub_req_data.get('completeness_percent', 0) / 100.0
                    
                    # Check if this is a gap
                    if completeness < threshold:
                        gap = Gap(
                            pillar=pillar_name,
                            requirement_id=req_id,
                            sub_requirement_id=sub_req_id,
                            requirement_text=sub_req_data.get('text', 'N/A'),
                            current_completeness=completeness * 100,
                            evidence_count=len(sub_req_data.get('evidence', [])),
                            severity=self.classify_gap_severity(completeness),
                            suggested_searches=sub_req_data.get('suggested_searches', [])
                        )
                        gaps.append(gap)
        
        # Sort by severity (critical first)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        gaps.sort(key=lambda g: (severity_order[g.severity], g.current_completeness))
        
        logger.info(f"Extracted {len(gaps)} gaps (threshold: {threshold*100:.0f}%)")
        return gaps
    
    def classify_gap_severity(self, completeness: float) -> str:
        """
        Classify gap severity based on completeness score.
        
        Args:
            completeness: Completeness percentage (0.0-1.0)
        
        Returns:
            Severity level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
        """
        if completeness < self.severity_thresholds["CRITICAL"]:
            return "CRITICAL"
        elif completeness < self.severity_thresholds["HIGH"]:
            return "HIGH"
        elif completeness < self.severity_thresholds["MEDIUM"]:
            return "MEDIUM"
        else:
            return "LOW"
    
    def generate_gap_summary(self, gaps: List[Gap]) -> Dict:
        """
        Generate summary statistics for gaps.
        
        Args:
            gaps: List of Gap objects
        
        Returns:
            Summary dictionary with counts, percentages, and breakdowns
        
        Example:
            >>> summary = analyzer.generate_gap_summary(gaps)
            >>> print(summary['total_gaps'])
            23
            >>> print(summary['by_severity']['CRITICAL'])
            5
        """
        summary = {
            'total_gaps': len(gaps),
            'by_severity': {
                'CRITICAL': 0,
                'HIGH': 0,
                'MEDIUM': 0,
                'LOW': 0
            },
            'by_pillar': {},
            'average_completeness': 0.0,
            'most_incomplete': None,
            'least_incomplete': None
        }
        
        if not gaps:
            return summary
        
        # Count by severity
        for gap in gaps:
            summary['by_severity'][gap.severity] += 1
            
            # Count by pillar
            if gap.pillar not in summary['by_pillar']:
                summary['by_pillar'][gap.pillar] = 0
            summary['by_pillar'][gap.pillar] += 1
        
        # Calculate average completeness
        summary['average_completeness'] = sum(g.current_completeness for g in gaps) / len(gaps)
        
        # Find extremes
        summary['most_incomplete'] = min(gaps, key=lambda g: g.current_completeness)
        summary['least_incomplete'] = max(gaps, key=lambda g: g.current_completeness)
        
        return summary
    
    def load_report(self, report_path: str) -> Dict:
        """
        Load gap analysis report from file.
        
        Args:
            report_path: Path to gap_analysis_report.json
        
        Returns:
            Parsed report dictionary
        
        Raises:
            FileNotFoundError: If report file doesn't exist
            json.JSONDecodeError: If report is not valid JSON
        """
        path = Path(report_path)
        if not path.exists():
            raise FileNotFoundError(f"Gap analysis report not found: {report_path}")
        
        with open(path, 'r') as f:
            return json.load(f)
    
    def export_gaps_json(self, gaps: List[Gap], output_path: str) -> None:
        """
        Export gaps to JSON file.
        
        Args:
            gaps: List of Gap objects
            output_path: Path to output JSON file
        """
        gaps_data = [
            {
                'gap_id': gap.gap_id,
                'pillar': gap.pillar,
                'requirement_id': gap.requirement_id,
                'sub_requirement_id': gap.sub_requirement_id,
                'requirement_text': gap.requirement_text,
                'current_completeness': gap.current_completeness,
                'gap_percentage': gap.gap_percentage,
                'evidence_count': gap.evidence_count,
                'severity': gap.severity,
                'suggested_searches': gap.suggested_searches
            }
            for gap in gaps
        ]
        
        with open(output_path, 'w') as f:
            json.dump(gaps_data, f, indent=2)
        
        logger.info(f"Exported {len(gaps)} gaps to {output_path}")
    
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


# Convenience functions
def extract_gaps_from_file(
    report_path: str,
    threshold: float = 0.8
) -> List[Gap]:
    """
    Extract gaps from gap analysis report file (convenience function).
    
    Args:
        report_path: Path to gap_analysis_report.json
        threshold: Completeness threshold (0.0-1.0)
    
    Returns:
        List of Gap objects
    """
    analyzer = GapAnalyzer(completeness_threshold=threshold)
    report = analyzer.load_report(report_path)
    return analyzer.extract_gaps(report)

