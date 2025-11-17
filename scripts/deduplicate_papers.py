#!/usr/bin/env python3
"""Smart semantic deduplication of papers."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.utils.smart_dedup import run_smart_dedup
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Deduplicate papers using semantic similarity'
    )
    parser.add_argument(
        '--review-log',
        default='review_log.json',
        help='Path to review log'
    )
    parser.add_argument(
        '--output',
        default='review_log_deduped.json',
        help='Output file for deduplicated reviews'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.90,
        help='Similarity threshold (0-1, default: 0.90)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show duplicates without merging'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("Running in dry-run mode (no files will be modified)")
    
    # Run deduplication
    result = run_smart_dedup(
        review_log=args.review_log,
        output_file=None if args.dry_run else args.output
    )
    
    # Show duplicates
    if result['duplicates_found']:
        print("\nDuplicates Found:")
        for file1, file2, sim in result['duplicates_found']:
            print(f"  {file1}")
            print(f"  ≈ {file2}")
            print(f"  Similarity: {sim:.0%}\n")
    
    if not args.dry_run:
        print(f"\n✅ Deduplicated reviews saved to: {args.output}")
        print("\n⚠️ Remember to use the deduplicated file for gap analysis!")


if __name__ == '__main__':
    main()
