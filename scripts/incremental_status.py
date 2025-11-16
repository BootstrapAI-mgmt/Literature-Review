#!/usr/bin/env python3
"""Show incremental analysis status."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.utils.incremental_analyzer import get_incremental_analyzer


def main():
    analyzer = get_incremental_analyzer()
    
    # Detect current changes
    changes = analyzer.detect_changes(paper_dir='data/raw')
    stats = analyzer.get_stats()
    
    print("\n" + "="*60)
    print("INCREMENTAL ANALYSIS STATUS")
    print("="*60)
    
    print(f"\n📊 Cache Statistics:")
    print(f"   Last Run: {stats['last_run'] or 'Never'}")
    print(f"   Cached Papers: {stats['total_papers_cached']}")
    print(f"   With Analysis: {stats['papers_with_analysis']}")
    
    print(f"\n🔍 Current Status:")
    print(f"   New Papers: {len(changes['new'])}")
    print(f"   Modified Papers: {len(changes['modified'])}")
    print(f"   Unchanged Papers: {len(changes['unchanged'])}")
    print(f"   Removed Papers: {len(changes['removed'])}")
    
    total_papers = len(changes['new']) + len(changes['modified']) + len(changes['unchanged'])
    if total_papers > 0:
        cache_hit_rate = (len(changes['unchanged']) / total_papers) * 100
        print(f"\n💾 Cache Efficiency:")
        print(f"   Hit Rate: {cache_hit_rate:.1f}%")
        
        if changes['new'] or changes['modified']:
            time_saved = len(changes['unchanged']) * 15  # Assume 15s per paper
            print(f"   Est. Time Saved: ~{time_saved}s")
    
    if changes['new']:
        print(f"\n✨ New Papers:")
        for paper in changes['new'][:5]:
            print(f"   - {paper}")
        if len(changes['new']) > 5:
            print(f"   ... and {len(changes['new']) - 5} more")
    
    if changes['modified']:
        print(f"\n📝 Modified Papers:")
        for paper in changes['modified'][:5]:
            print(f"   - {paper}")
        if len(changes['modified']) > 5:
            print(f"   ... and {len(changes['modified']) - 5} more")
    
    print("\n" + "="*60)
    
    # Suggest action
    if changes['new'] or changes['modified']:
        print("💡 Run `python pipeline_orchestrator.py` to process changes")
    else:
        print("✅ All papers are up to date")
    
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
