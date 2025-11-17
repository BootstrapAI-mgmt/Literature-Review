#!/usr/bin/env python3
"""Analyze evidence freshness and temporal decay."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.utils.evidence_decay import generate_decay_report, EvidenceDecayTracker
import argparse
import json


def main():
    parser = argparse.ArgumentParser(
        description='Analyze evidence decay and freshness'
    )
    parser.add_argument(
        '--review-log',
        default='review_log.json',
        help='Path to review log'
    )
    parser.add_argument(
        '--gap-analysis',
        default='gap_analysis_output/gap_analysis_report.json',
        help='Path to gap analysis'
    )
    parser.add_argument(
        '--output',
        default='gap_analysis_output/evidence_decay.json',
        help='Output file'
    )
    parser.add_argument(
        '--half-life',
        type=float,
        default=5.0,
        help='Half-life in years (default: 5.0)'
    )
    parser.add_argument(
        '--show-weights',
        action='store_true',
        help='Show decay weights for each year'
    )
    
    args = parser.parse_args()
    
    if args.show_weights:
        print("\nDecay Weight Table (Half-life: {:.1f} years)".format(args.half_life))
        print("=" * 50)
        print(f"{'Year':<10} {'Age':<10} {'Weight':<10}")
        print("=" * 50)
        
        tracker = EvidenceDecayTracker(half_life_years=args.half_life)
        for year in range(tracker.current_year, tracker.current_year - 15, -1):
            weight = tracker.calculate_decay_weight(year)
            age = tracker.current_year - year
            print(f"{year:<10} {age:<10} {weight:.3f}")
        
        print("=" * 50 + "\n")
    
    # Generate report
    print("Analyzing evidence decay...")
    report = generate_decay_report(
        review_log=args.review_log,
        gap_analysis=args.gap_analysis,
        output_file=args.output,
        half_life_years=args.half_life
    )
    
    print(f"\n✅ Analysis complete!")
    print(f"   Report: {args.output}")


if __name__ == '__main__':
    main()
