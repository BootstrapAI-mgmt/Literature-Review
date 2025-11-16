#!/usr/bin/env python3
"""
Generate deep_review_directions.json for high-priority gaps.

Usage:
  python scripts/generate_deep_review_directions.py --top 10
  python scripts/generate_deep_review_directions.py --pillar "Pillar 1" --completeness-max 30
  python scripts/generate_deep_review_directions.py --bottlenecks-only
"""

import json
import argparse
import os
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GAP_ANALYSIS_FILE = 'gap_analysis_output/gap_analysis_report.json'
DIRECTIONS_FILE = 'gap_analysis_output/deep_review_directions.json'


def load_gap_analysis():
    """Load gap analysis report."""
    if not os.path.exists(GAP_ANALYSIS_FILE):
        raise FileNotFoundError(
            f"Gap analysis not found at {GAP_ANALYSIS_FILE}. "
            "Run pipeline_orchestrator.py first."
        )
    
    with open(GAP_ANALYSIS_FILE, 'r') as f:
        return json.load(f)


def identify_high_priority_gaps(gap_report: Dict, criteria: Dict) -> List[Dict]:
    """
    Identify gaps suitable for Deep Review.
    
    Args:
        gap_report: Gap analysis report
        criteria: Filter criteria
    
    Returns:
        List of gap dictionaries with metadata
    """
    candidate_gaps = []
    
    for pillar_name, pillar_data in gap_report.items():
        if not isinstance(pillar_data, dict) or 'analysis' not in pillar_data:
            continue
        
        # Filter by pillar if specified
        if criteria.get('pillar') and pillar_name != criteria['pillar']:
            continue
        
        for req_key, req_data in pillar_data['analysis'].items():
            for sub_req_key, sub_req_data in req_data.items():
                # Check if gap meets criteria
                completeness = sub_req_data.get('completeness_percent', 100)
                contributing_papers = sub_req_data.get('contributing_papers', [])
                confidence = sub_req_data.get('confidence_level', 'low')
                
                # Core criteria: 0-50% complete, has papers, medium+ confidence
                if not (0 <= completeness <= criteria.get('completeness_max', 50)):
                    continue
                
                if criteria.get('has_papers', True) and not contributing_papers:
                    continue
                
                # Filter by minimum confidence level
                min_confidence = criteria.get('min_confidence', 'medium')
                if min_confidence == 'high' and confidence != 'high':
                    continue
                elif min_confidence == 'medium' and confidence not in ['medium', 'high']:
                    continue
                
                # Calculate priority score
                priority_score = calculate_priority_score(
                    completeness, 
                    len(contributing_papers),
                    pillar_name,
                    sub_req_data
                )
                
                candidate_gaps.append({
                    'sub_req': sub_req_key,
                    'pillar': pillar_name,
                    'requirement': req_key,
                    'description': sub_req_data.get('description', ''),
                    'completeness': completeness,
                    'contributing_papers': [p.get('filename') for p in contributing_papers],
                    'paper_count': len(contributing_papers),
                    'confidence': confidence,
                    'priority_score': priority_score,
                    'gap_analysis': sub_req_data.get('gap_analysis', '')
                })
    
    return candidate_gaps


def calculate_priority_score(completeness, paper_count, pillar, sub_req_data):
    """
    Calculate priority score for a gap.
    
    Higher score = higher priority for Deep Review
    
    Factors:
    - Lower completeness = higher priority (more room for improvement)
    - More papers = higher priority (more to mine)
    - Foundational pillars = higher priority (blocks downstream)
    - Bottleneck status = bonus priority
    """
    score = 0
    
    # Completeness factor (inverse): 0% = 50 points, 50% = 0 points
    score += (50 - completeness)
    
    # Paper count factor: 1-3 papers good, 4+ excellent
    score += min(paper_count * 10, 40)
    
    # Foundational pillar bonus
    if pillar in ['Pillar 1', 'Pillar 3', 'Pillar 5']:
        score += 20
    
    # Bottleneck bonus (if data available)
    if sub_req_data.get('is_bottleneck', False):
        score += 30
    
    return score


def generate_directions(gaps: List[Dict], output_file: str):
    """Generate deep_review_directions.json."""
    directions = {}
    
    for gap in gaps:
        directions[gap['sub_req']] = {
            'pillar': gap['pillar'],
            'requirement': gap['requirement'],
            'description': gap['description'],
            'current_completeness': gap['completeness'],
            'contributing_papers': gap['contributing_papers'],
            'priority': 'HIGH' if gap['priority_score'] >= 80 else 'MEDIUM',
            'gap_analysis': gap['gap_analysis']
        }
    
    with open(output_file, 'w') as f:
        json.dump(directions, f, indent=2)
    
    logger.info(f"Generated directions for {len(gaps)} gaps")
    logger.info(f"Saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate Deep Review directions for high-priority gaps'
    )
    parser.add_argument(
        '--top', 
        type=int, 
        help='Select top N gaps by priority score'
    )
    parser.add_argument(
        '--pillar',
        type=str,
        help='Filter by pillar (e.g., "Pillar 1")'
    )
    parser.add_argument(
        '--completeness-max',
        type=int,
        default=50,
        help='Maximum completeness percentage (default: 50)'
    )
    parser.add_argument(
        '--has-papers',
        action='store_true',
        default=True,
        help='Only gaps with contributing papers (default: True)'
    )
    parser.add_argument(
        '--bottlenecks-only',
        action='store_true',
        help='Only bottleneck gaps'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=DIRECTIONS_FILE,
        help=f'Output file (default: {DIRECTIONS_FILE})'
    )
    
    args = parser.parse_args()
    
    # Load gap analysis
    logger.info("Loading gap analysis...")
    gap_report = load_gap_analysis()
    
    # Build criteria
    criteria = {
        'pillar': args.pillar,
        'completeness_max': args.completeness_max,
        'has_papers': args.has_papers,
        'bottlenecks_only': args.bottlenecks_only
    }
    
    # Identify candidate gaps
    logger.info("Identifying high-priority gaps...")
    candidate_gaps = identify_high_priority_gaps(gap_report, criteria)
    
    if not candidate_gaps:
        logger.warning("No gaps found matching criteria")
        return
    
    # Sort by priority
    candidate_gaps.sort(key=lambda x: x['priority_score'], reverse=True)
    
    # Select top N if specified
    if args.top:
        candidate_gaps = candidate_gaps[:args.top]
    
    # Display summary
    logger.info(f"\nSelected {len(candidate_gaps)} gaps for Deep Review:")
    for i, gap in enumerate(candidate_gaps[:10], 1):
        logger.info(
            f"{i}. {gap['sub_req']} - "
            f"{gap['completeness']:.0f}% complete, "
            f"{gap['paper_count']} papers, "
            f"priority: {gap['priority_score']:.0f}"
        )
    
    if len(candidate_gaps) > 10:
        logger.info(f"... and {len(candidate_gaps) - 10} more")
    
    # Generate directions
    generate_directions(candidate_gaps, args.output)
    
    logger.info(f"\n✅ Ready to run Deep Reviewer:")
    logger.info(f"   python -m literature_review.reviewers.deep_reviewer")


if __name__ == '__main__':
    main()
