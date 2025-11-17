#!/usr/bin/env python3
"""Analyze evidence triangulation and source diversity."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.analysis.triangulation import generate_triangulation_report
from literature_review.visualization.triangulation_viz import (
    generate_triangulation_html,
)
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Analyze evidence triangulation and detect bias"
    )
    parser.add_argument(
        "--review-log", default="review_log.json", help="Path to review log"
    )
    parser.add_argument(
        "--gap-analysis",
        default="gap_analysis_output/gap_analysis_report.json",
        help="Path to gap analysis report",
    )
    parser.add_argument(
        "--output",
        default="gap_analysis_output/triangulation.json",
        help="Output file for analysis",
    )
    parser.add_argument(
        "--viz",
        default="gap_analysis_output/triangulation.html",
        help="Output file for visualization",
    )
    parser.add_argument(
        "--open", action="store_true", help="Open visualization in browser"
    )

    args = parser.parse_args()

    # Generate report
    print("Analyzing evidence triangulation...")
    generate_triangulation_report(
        review_log=args.review_log,
        gap_analysis=args.gap_analysis,
        output_file=args.output,
    )

    # Generate visualization
    print("\nGenerating visualization...")
    generate_triangulation_html(report_file=args.output, output_file=args.viz)

    print("\n✅ Analysis complete!")
    print(f"   Report: {args.output}")
    print(f"   Visualization: {args.viz}")

    # Open if requested
    if args.open:
        import webbrowser

        webbrowser.open(f"file://{os.path.abspath(args.viz)}")
        print("\n🌐 Opened in browser")


if __name__ == "__main__":
    main()
