"""
Evidence Sufficiency Matrix
Analyze quality vs. quantity tradeoffs in evidence collection.
"""

import json
from typing import Dict, List, Tuple
from collections import defaultdict
import logging
import os

logger = logging.getLogger(__name__)


class SufficiencyMatrixAnalyzer:
    """Analyze evidence sufficiency across quality/quantity dimensions."""
    
    # Thresholds for categorization
    QUANTITY_THRESHOLDS = {
        'low': 3,      # <3 papers
        'medium': 8,   # 3-8 papers
        'high': 8      # >8 papers
    }
    
    QUALITY_THRESHOLDS = {
        'low': 0.4,    # <40% avg alignment
        'medium': 0.7,  # 40-70% avg alignment
        'high': 0.7    # >70% avg alignment
    }
    
    def __init__(self, gap_analysis_file: str):
        """
        Initialize analyzer.
        
        Args:
            gap_analysis_file: Path to gap_analysis_report.json
        """
        self.gap_analysis_file = gap_analysis_file
        
        with open(gap_analysis_file, 'r') as f:
            self.gap_data = json.load(f)
    
    def analyze_sufficiency(self) -> Dict:
        """
        Perform complete sufficiency analysis.
        
        Returns:
            Sufficiency matrix report
        """
        logger.info("Analyzing evidence sufficiency...")
        
        # Analyze each requirement
        requirement_analysis = {}
        
        for pillar_name, pillar_data in self.gap_data.items():
            if 'analysis' not in pillar_data:
                continue
                
            for req_name, req_data in pillar_data['analysis'].items():
                for sub_req_name, sub_req_data in req_data.items():
                    # Create unique ID for sub-requirement
                    req_id = f"{pillar_name}::{req_name}::{sub_req_name}"
                    
                    # Get contributing papers
                    papers = sub_req_data.get('contributing_papers', [])
                    
                    if not papers:
                        continue
                    
                    # Calculate metrics
                    quantity = len(papers)
                    quality = self._calculate_avg_alignment(papers)
                    
                    # Categorize
                    quantity_level = self._categorize_quantity(quantity)
                    quality_level = self._categorize_quality(quality)
                    quadrant = self._assign_quadrant(quantity_level, quality_level)
                    
                    # Store analysis
                    requirement_analysis[req_id] = {
                        'requirement': sub_req_name,
                        'pillar': pillar_name,
                        'parent_requirement': req_name,
                        'quantity': quantity,
                        'quality': quality,
                        'quantity_level': quantity_level,
                        'quality_level': quality_level,
                        'quadrant': quadrant,
                        'papers': [
                            {
                                'filename': p['filename'],
                                'alignment': p.get('estimated_contribution_percent', 0) / 100.0,
                                'contribution_summary': p.get('contribution_summary', '')
                            }
                            for p in papers
                        ]
                    }
        
        # Group by quadrant
        quadrant_groups = self._group_by_quadrant(requirement_analysis)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(quadrant_groups)
        
        return {
            'summary': {
                'total_requirements_analyzed': len(requirement_analysis),
                'quadrant_distribution': {
                    quadrant: len(reqs)
                    for quadrant, reqs in quadrant_groups.items()
                }
            },
            'requirement_analysis': requirement_analysis,
            'quadrant_groups': quadrant_groups,
            'recommendations': recommendations,
            'matrix_visualization': self._create_matrix_data(requirement_analysis)
        }
    
    def _calculate_avg_alignment(self, papers: List[Dict]) -> float:
        """Calculate average alignment score from contributing papers."""
        if not papers:
            return 0.0
        
        # Extract alignment scores (convert from percentage to decimal)
        alignments = []
        for p in papers:
            score = p.get('estimated_contribution_percent', 0)
            if score > 0:
                alignments.append(score / 100.0)
        
        if not alignments:
            return 0.0
        
        return sum(alignments) / len(alignments)
    
    def _categorize_quantity(self, quantity: int) -> str:
        """Categorize quantity level."""
        if quantity < self.QUANTITY_THRESHOLDS['low']:
            return 'low'
        elif quantity <= self.QUANTITY_THRESHOLDS['medium']:
            return 'medium'
        else:
            return 'high'
    
    def _categorize_quality(self, quality: float) -> str:
        """Categorize quality level."""
        if quality < self.QUALITY_THRESHOLDS['low']:
            return 'low'
        elif quality <= self.QUALITY_THRESHOLDS['medium']:
            return 'medium'
        else:
            return 'high'
    
    def _assign_quadrant(self, quantity_level: str, quality_level: str) -> str:
        """
        Assign quadrant based on quality/quantity levels.
        
        Quadrants:
        - Q1 (High Quantity, High Quality): Strong Foundation
        - Q2 (Low Quantity, High Quality): Promising Seeds
        - Q3 (Low Quantity, Low Quality): Critical Gap
        - Q4 (High Quantity, Low Quality): Hollow Coverage
        """
        if quantity_level == 'high' and quality_level == 'high':
            return 'Q1_Strong_Foundation'
        elif quantity_level in ['low', 'medium'] and quality_level == 'high':
            return 'Q2_Promising_Seeds'
        elif quantity_level in ['low', 'medium'] and quality_level in ['low', 'medium']:
            return 'Q3_Critical_Gap'
        else:  # high quantity, low/medium quality
            return 'Q4_Hollow_Coverage'
    
    def _group_by_quadrant(self, requirement_analysis: Dict) -> Dict[str, List[str]]:
        """Group requirements by quadrant."""
        quadrants = defaultdict(list)
        
        for req_id, analysis in requirement_analysis.items():
            quadrant = analysis['quadrant']
            quadrants[quadrant].append(req_id)
        
        return dict(quadrants)
    
    def _generate_recommendations(self, quadrant_groups: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Generate actionable recommendations per quadrant."""
        recommendations = {}
        
        # Q1: Strong Foundation
        q1_count = len(quadrant_groups.get('Q1_Strong_Foundation', []))
        if q1_count > 0:
            recommendations['Q1_Strong_Foundation'] = [
                f"✅ {q1_count} requirements have strong evidence foundation",
                "✅ These are publication-ready - consider consolidating into review papers",
                "💡 Use these as benchmarks for evidence quality in other requirements"
            ]
        
        # Q2: Promising Seeds
        q2_count = len(quadrant_groups.get('Q2_Promising_Seeds', []))
        if q2_count > 0:
            recommendations['Q2_Promising_Seeds'] = [
                f"⚠️ {q2_count} requirements have high-quality but limited evidence",
                "🎯 Priority action: Run targeted searches to find more papers in these areas",
                "💡 These could become Q1 with 3-5 more high-quality papers",
                "💡 Consider Deep Reviewer to extract maximum value from existing papers"
            ]
        
        # Q3: Critical Gap
        q3_count = len(quadrant_groups.get('Q3_Critical_Gap', []))
        if q3_count > 0:
            recommendations['Q3_Critical_Gap'] = [
                f"🚨 {q3_count} requirements have critical evidence gaps",
                "🎯 Urgent action: Expand searches or relax inclusion criteria",
                "💡 Consider whether requirements are too specific or poorly defined",
                "💡 May need expert consultation or primary research"
            ]
        
        # Q4: Hollow Coverage
        q4_count = len(quadrant_groups.get('Q4_Hollow_Coverage', []))
        if q4_count > 0:
            recommendations['Q4_Hollow_Coverage'] = [
                f"⚠️ {q4_count} requirements have many papers but low alignment",
                "🎯 Action: Review and refine requirement definitions",
                "🎯 Action: Apply stricter inclusion criteria to filter weak papers",
                "💡 Quality > Quantity - consider removing weakly aligned papers",
                "💡 May indicate search queries are too broad"
            ]
        
        return recommendations
    
    def _create_matrix_data(self, requirement_analysis: Dict) -> Dict:
        """Create data for matrix visualization."""
        matrix_data = {
            'requirements': [],
            'quadrants': {
                'Q1_Strong_Foundation': {'min_quantity': 8, 'min_quality': 0.7, 'color': '#28a745'},
                'Q2_Promising_Seeds': {'max_quantity': 8, 'min_quality': 0.7, 'color': '#ffc107'},
                'Q3_Critical_Gap': {'max_quantity': 8, 'max_quality': 0.7, 'color': '#dc3545'},
                'Q4_Hollow_Coverage': {'min_quantity': 8, 'max_quality': 0.7, 'color': '#fd7e14'}
            }
        }
        
        for req_id, analysis in requirement_analysis.items():
            # Truncate requirement text for display
            req_text = analysis['requirement']
            if len(req_text) > 50:
                req_text = req_text[:50] + '...'
            
            matrix_data['requirements'].append({
                'id': req_id,
                'requirement': req_text,
                'pillar': analysis['pillar'],
                'x': analysis['quantity'],
                'y': analysis['quality'],
                'quadrant': analysis['quadrant'],
                'papers': analysis['papers']
            })
        
        return matrix_data


def generate_sufficiency_report(gap_analysis_file: str,
                               output_file: str = 'gap_analysis_output/sufficiency_matrix.json'):
    """
    Generate evidence sufficiency matrix report.
    
    Args:
        gap_analysis_file: Path to gap analysis report
        output_file: Output file path
    """
    analyzer = SufficiencyMatrixAnalyzer(gap_analysis_file)
    report = analyzer.analyze_sufficiency()
    
    # Save report
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Sufficiency matrix report saved to {output_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("EVIDENCE SUFFICIENCY MATRIX")
    print("="*60)
    
    summary = report['summary']
    print(f"\nAnalyzed {summary['total_requirements_analyzed']} requirements\n")
    
    print("Quadrant Distribution:")
    for quadrant, count in summary['quadrant_distribution'].items():
        print(f"  {quadrant}: {count}")
    
    print("\nRecommendations:")
    for quadrant, recs in report['recommendations'].items():
        print(f"\n{quadrant}:")
        for rec in recs:
            print(f"  {rec}")
    
    print("\n" + "="*60)
    
    return report


def main():
    """CLI entry point."""
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    report = generate_sufficiency_report(
        gap_analysis_file='gap_analysis_output/gap_analysis_report.json',
        output_file='gap_analysis_output/sufficiency_matrix.json'
    )
    
    # Generate HTML visualization
    try:
        from literature_review.visualization.sufficiency_matrix_viz import generate_sufficiency_matrix_html
        html_output = os.path.join('gap_analysis_output', 'sufficiency_matrix.html')
        generate_sufficiency_matrix_html(
            report_file='gap_analysis_output/sufficiency_matrix.json',
            output_file=html_output
        )
        logger.info(f"Saved HTML visualization to {html_output}")
    except Exception as e:
        logger.warning(f"Could not generate HTML visualization: {e}")


if __name__ == '__main__':
    main()
