"""Intelligent Deep Reviewer Trigger System."""

import json
from typing import Dict, List
import logging
import os

logger = logging.getLogger(__name__)


class DeepReviewTriggerEngine:
    """Decide when to invoke Deep Reviewer based on 3 metrics."""
    
    THRESHOLDS = {
        'gap_severity': 0.7,      # Invoke if gap > 70%
        'paper_quality': 0.6,     # Invoke if quality > 60%
        'roi_potential': 5.0      # Invoke if ROI > 5 (hours saved / cost)
    }
    
    def __init__(self, gap_analysis_file: str, review_log_file: str):
        with open(gap_analysis_file, 'r') as f:
            raw_gap_data = json.load(f)
            # Transform gap data to expected format with pillars
            self.gap_data = self._transform_gap_data(raw_gap_data)
        
        with open(review_log_file, 'r') as f:
            self.reviews = json.load(f)
    
    def _transform_gap_data(self, raw_gap_data: Dict) -> Dict:
        """Transform gap analysis to expected format with pillars."""
        transformed = {
            'pillars': []
        }
        
        for pillar_name, pillar_data in raw_gap_data.items():
            pillar = {
                'name': pillar_name,
                'requirements': []
            }
            
            if 'analysis' in pillar_data:
                for req_name, req_data in pillar_data['analysis'].items():
                    for sub_req_name, sub_req_data in req_data.items():
                        # Extract gap severity from completeness_percent
                        completeness = sub_req_data.get('completeness_percent', 0)
                        if completeness < 30:
                            gap_severity = 'Critical'
                        elif completeness < 50:
                            gap_severity = 'High'
                        elif completeness < 70:
                            gap_severity = 'Medium'
                        else:
                            gap_severity = 'Low'
                        
                        pillar['requirements'].append({
                            'id': sub_req_name,
                            'gap_severity': gap_severity,
                            'completeness': completeness
                        })
            
            transformed['pillars'].append(pillar)
        
        return transformed
    
    def evaluate_triggers(self) -> List[Dict]:
        """Evaluate which papers should trigger Deep Review."""
        candidates = []
        
        for paper_file, review in self.reviews.items():
            # Metric 1: Gap Severity (does this paper fill critical gaps?)
            gap_score = self._calculate_gap_impact(paper_file)
            
            # Metric 2: Paper Quality (is it worth deep analysis?)
            quality_score = review.get('judge_analysis', {}).get('overall_alignment', 0.0)
            
            # Metric 3: ROI Potential (time saved vs. cost)
            roi_score = self._calculate_roi(paper_file, gap_score, quality_score)
            
            # Decision: trigger if ANY metric exceeds threshold
            should_trigger = (
                gap_score > self.THRESHOLDS['gap_severity'] or
                quality_score > self.THRESHOLDS['paper_quality'] or
                roi_score > self.THRESHOLDS['roi_potential']
            )
            
            if should_trigger:
                candidates.append({
                    'paper': paper_file,
                    'title': review.get('metadata', {}).get('title', paper_file),
                    'gap_score': round(gap_score, 2),
                    'quality_score': round(quality_score, 2),
                    'roi_score': round(roi_score, 1),
                    'trigger_reason': self._get_trigger_reason(gap_score, quality_score, roi_score)
                })
        
        # Rank by combined score
        candidates.sort(key=lambda x: x['gap_score'] + x['quality_score'] + (x['roi_score'] / 10), reverse=True)
        
        return candidates
    
    def _calculate_gap_impact(self, paper_file: str) -> float:
        """Calculate how much this paper fills critical gaps."""
        # Simplified: check if it addresses high-severity gaps
        review = self.reviews.get(paper_file, {})
        judge = review.get('judge_analysis', {})
        
        critical_contributions = 0
        total_contributions = 0
        
        for pillar_contrib in judge.get('pillar_contributions', []):
            pillar_name = pillar_contrib['pillar_name']
            
            for sub_req in pillar_contrib.get('sub_requirements_addressed', []):
                total_contributions += 1
                
                # Check if this requirement has high gap severity
                req_gap = self._get_requirement_gap_severity(sub_req['requirement_id'], pillar_name)
                
                if req_gap in ['High', 'Critical']:
                    critical_contributions += 1
        
        return critical_contributions / max(total_contributions, 1)
    
    def _get_requirement_gap_severity(self, req_id: str, pillar: str) -> str:
        """Get gap severity for a requirement."""
        for p in self.gap_data['pillars']:
            if p['name'] == pillar:
                for r in p['requirements']:
                    if r['id'] == req_id:
                        return r.get('gap_severity', 'Unknown')
        return 'Unknown'
    
    def _calculate_roi(self, paper_file: str, gap_score: float, quality_score: float) -> float:
        """Estimate ROI of Deep Review (hours saved / cost)."""
        # Simplified: high-gap + high-quality = high ROI
        # Assume Deep Review costs $0.50, saves 2 hours if valuable
        
        potential_value = gap_score * quality_score * 2.0  # Hours potentially saved
        cost = 0.5  # Deep Review API cost estimate
        
        return potential_value / cost
    
    def _get_trigger_reason(self, gap_score: float, quality_score: float, roi_score: float) -> str:
        """Explain why trigger fired."""
        reasons = []
        
        if gap_score > self.THRESHOLDS['gap_severity']:
            reasons.append(f"Critical gap coverage ({gap_score:.0%})")
        if quality_score > self.THRESHOLDS['paper_quality']:
            reasons.append(f"High quality ({quality_score:.0%})")
        if roi_score > self.THRESHOLDS['roi_potential']:
            reasons.append(f"Strong ROI ({roi_score:.1f}x)")
        
        return ", ".join(reasons) if reasons else "Below threshold"


def generate_trigger_report(gap_file: str, review_log: str, output_file: str = 'deep_reviewer_cache/trigger_decisions.json'):
    """Generate trigger decision report."""
    engine = DeepReviewTriggerEngine(gap_file, review_log)
    candidates = engine.evaluate_triggers()
    
    report = {
        'total_papers': len(engine.reviews),
        'triggered_papers': len(candidates),
        'trigger_rate': round(len(candidates) / max(len(engine.reviews), 1), 2),
        'candidates': candidates
    }
    
    output_dir = os.path.dirname(output_file)
    if output_dir:  # Only create directory if path contains one
        os.makedirs(output_dir, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDeep Review Trigger Analysis:")
    print(f"  Total Papers: {report['total_papers']}")
    print(f"  Triggered: {report['triggered_papers']} ({report['trigger_rate']:.0%})")
    print(f"\nTop 5 Candidates:")
    for c in candidates[:5]:
        print(f"  - {c['title'][:60]}")
        print(f"    Reason: {c['trigger_reason']}")
    
    return report
