#!/usr/bin/env python3
"""
Analyze proof chain dependencies and generate reports.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.analysis.proof_chain import generate_proof_chain_report
from literature_review.visualization.proof_chain_viz import generate_proof_chain_html
import argparse


def main():
    parser = argparse.ArgumentParser(description='Analyze proof chain dependencies')
    parser.add_argument(
        '--gap-file',
        default='gap_analysis_output/gap_analysis_report.json',
        help='Path to gap analysis report'
    )
    parser.add_argument(
        '--pillar-file',
        default='pillar_definitions.json',
        help='Path to pillar definitions'
    )
    parser.add_argument(
        '--output',
        default='gap_analysis_output/proof_chain.json',
        help='Output file for analysis report'
    )
    parser.add_argument(
        '--viz',
        default='gap_analysis_output/proof_chain.html',
        help='Output file for visualization'
    )
    parser.add_argument(
        '--open',
        action='store_true',
        help='Open visualization in browser'
    )
    
    args = parser.parse_args()
    
    # Generate analysis
    print("Analyzing proof chain dependencies...")
    report = generate_proof_chain_report(
        gap_file=args.gap_file,
        pillar_file=args.pillar_file,
        output_file=args.output
    )
    
    # Generate visualization
    print("\nGenerating interactive visualization...")
    generate_proof_chain_html(
        report_file=args.output,
        output_file=args.viz
    )
    
    print(f"\n✅ Analysis complete!")
    print(f"   Report: {args.output}")
    print(f"   Visualization: {args.viz}")
    
    # Open in browser if requested
    if args.open:
        import webbrowser
        webbrowser.open(f'file://{os.path.abspath(args.viz)}')
        print(f"\n🌐 Opened visualization in browser")


if __name__ == '__main__':
    main()
