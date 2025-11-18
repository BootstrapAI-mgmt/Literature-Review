#!/usr/bin/env python
"""
Generate A/B comparison report showing evidence decay impact on gap analysis.

This script compares gap analysis scores with and without evidence decay weighting,
showing how temporal freshness affects completeness scores.
"""

import json
import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from literature_review.analysis.gap_analyzer import GapAnalyzer


def load_gap_analysis(gap_file: str):
    """Load gap analysis report."""
    with open(gap_file, 'r') as f:
        return json.load(f)


def load_version_history(version_file: str):
    """Load version history for publication years."""
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            return json.load(f)
    return {}


def generate_comparison_report(gap_file: str, config_file: str, version_file: str, output_file: str):
    """Generate decay impact comparison report."""
    
    # Load config
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Load gap analysis
    gap_data = load_gap_analysis(gap_file)
    
    # Load version history
    version_history = load_version_history(version_file)
    
    # Create analyzer
    analyzer = GapAnalyzer(config=config)
    
    all_reports = {}
    
    # Generate report for each pillar
    for pillar_name, pillar_data in gap_data.items():
        if not isinstance(pillar_data, dict) or 'analysis' not in pillar_data:
            continue
        
        print(f"\nAnalyzing pillar: {pillar_name}")
        
        # Extract requirements structure
        requirements = {}
        analysis = pillar_data['analysis']
        
        for req_key, req_data in analysis.items():
            requirements[req_key] = list(req_data.keys())
        
        # Generate comparison report
        report = analyzer.generate_decay_impact_report(
            pillar_name=pillar_name,
            requirements=requirements,
            analysis_results=analysis,
            version_history=version_history
        )
        
        all_reports[pillar_name] = report
        
        # Print summary
        summary = report['summary']
        print(f"  Total Requirements: {summary['total_requirements']}")
        print(f"  Average Delta: {summary['avg_delta']:.1f}%")
        print(f"  Significant Changes: {summary['significant_changes']}")
        print(f"  Impact Breakdown:")
        print(f"    - Decreased: {summary['impact_breakdown']['decreased']}")
        print(f"    - Increased: {summary['impact_breakdown']['increased']}")
        print(f"    - Minimal: {summary['impact_breakdown']['minimal']}")
    
    # Save full report
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(all_reports, f, indent=2)
    
    print(f"\n✅ Decay impact report saved to: {output_file}")
    
    # Print top affected requirements
    print("\n" + "="*80)
    print("TOP 10 REQUIREMENTS MOST AFFECTED BY DECAY")
    print("="*80)
    
    all_requirements = []
    for pillar_name, report in all_reports.items():
        for req in report['requirements']:
            req['pillar'] = pillar_name
            all_requirements.append(req)
    
    # Sort by absolute delta
    all_requirements.sort(key=lambda x: abs(x['delta']), reverse=True)
    
    for i, req in enumerate(all_requirements[:10], 1):
        req_text = req['requirement'][:60] + "..." if len(req['requirement']) > 60 else req['requirement']
        print(f"\n{i}. {req_text}")
        print(f"   Pillar: {req['pillar']}")
        print(f"   Without Decay: {req['score_no_decay']:.1f}%")
        print(f"   With Decay: {req['score_with_decay']:.1f}%")
        print(f"   Delta: {req['delta']:+.1f}% ({req['delta_pct']:+.1f}%)")
        print(f"   Freshness: {req['freshness']:.1%}")
        print(f"   Impact: {req['impact'].upper()}")
    
    print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Generate evidence decay impact report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python scripts/generate_decay_impact_report.py
  
  # Custom files
  python scripts/generate_decay_impact_report.py \\
      --gap-analysis gap_analysis_output/gap_analysis_report.json \\
      --config pipeline_config.json \\
      --output gap_analysis_output/decay_impact.json
        """
    )
    
    parser.add_argument(
        '--gap-analysis',
        default='gap_analysis_output/gap_analysis_report.json',
        help='Path to gap analysis report (default: gap_analysis_output/gap_analysis_report.json)'
    )
    
    parser.add_argument(
        '--config',
        default='pipeline_config.json',
        help='Path to pipeline config (default: pipeline_config.json)'
    )
    
    parser.add_argument(
        '--version-history',
        default='review_version_history.json',
        help='Path to version history (default: review_version_history.json)'
    )
    
    parser.add_argument(
        '--output',
        default='gap_analysis_output/decay_impact_report.json',
        help='Output file path (default: gap_analysis_output/decay_impact_report.json)'
    )
    
    args = parser.parse_args()
    
    # Check files exist
    if not os.path.exists(args.gap_analysis):
        print(f"❌ Gap analysis file not found: {args.gap_analysis}")
        sys.exit(1)
    
    if not os.path.exists(args.config):
        print(f"❌ Config file not found: {args.config}")
        sys.exit(1)
    
    print("="*80)
    print("EVIDENCE DECAY IMPACT ANALYSIS")
    print("="*80)
    print(f"\nGap Analysis: {args.gap_analysis}")
    print(f"Config: {args.config}")
    print(f"Version History: {args.version_history}")
    print(f"Output: {args.output}")
    
    generate_comparison_report(
        gap_file=args.gap_analysis,
        config_file=args.config,
        version_file=args.version_history,
        output_file=args.output
    )


if __name__ == '__main__':
    main()
