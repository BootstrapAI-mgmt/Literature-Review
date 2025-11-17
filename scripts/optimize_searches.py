#!/usr/bin/env python3
"""Optimize search query execution order based on ROI."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.optimization.search_optimizer import generate_search_plan
import argparse
import json


def main():
    parser = argparse.ArgumentParser(
        description='Generate ROI-optimized search plan'
    )
    parser.add_argument(
        '--gap-file',
        default='gap_analysis_output/gap_analysis_report.json',
        help='Path to gap analysis report'
    )
    parser.add_argument(
        '--searches-file',
        default='gap_analysis_output/suggested_searches.json',
        help='Path to suggested searches'
    )
    parser.add_argument(
        '--output',
        default='gap_analysis_output/optimized_search_plan.json',
        help='Output file for optimized plan'
    )
    parser.add_argument(
        '--top-n',
        type=int,
        default=20,
        help='Number of top searches to execute'
    )
    parser.add_argument(
        '--priority',
        choices=['HIGH', 'MEDIUM', 'LOW'],
        help='Filter by priority level'
    )
    
    args = parser.parse_args()
    
    # Generate plan
    print("Optimizing search strategy...")
    plan = generate_search_plan(
        gap_file=args.gap_file,
        searches_file=args.searches_file,
        output_file=args.output
    )
    
    # Filter by priority if specified
    if args.priority:
        filtered = [s for s in plan['search_plan'] if s['priority'] == args.priority]
        print(f"\n{args.priority} Priority Searches ({len(filtered)}):")
        for i, search in enumerate(filtered[:args.top_n], 1):
            print(f"  {i}. {search['query']}")
            print(f"     ROI: {search['roi_score']:.2f}, Gap: {search['gap_severity']}")
    else:
        print(f"\nTop {args.top_n} Searches (Highest ROI):")
        for i, query in enumerate(plan['execution_order'][:args.top_n], 1):
            search = next(s for s in plan['search_plan'] if s['query'] == query)
            print(f"  {i}. {query}")
            print(f"     ROI: {search['roi_score']:.2f}, Priority: {search['priority']}")
    
    print(f"\n✅ Optimized plan saved to: {args.output}")


if __name__ == '__main__':
    main()
