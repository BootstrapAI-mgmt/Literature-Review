#!/usr/bin/env python3
"""Generate API cost report."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.utils.cost_tracker import get_cost_tracker


def main():
    tracker = get_cost_tracker()
    report = tracker.generate_report()
    
    print("\n" + "="*60)
    print("API COST REPORT")
    print("="*60)
    
    total = report['total_summary']
    print(f"\n📊 Total Usage:")
    print(f"   API Calls: {total['total_calls']}")
    print(f"   Total Cost: ${total['total_cost']:.4f}")
    print(f"   Total Tokens: {total['total_tokens']:,}")
    print(f"   Cache Savings: ${total['total_cache_savings']:.4f}")
    
    budget = report['budget_status']
    print(f"\n💰 Budget Status:")
    print(f"   Budget: ${budget['budget']:.2f}")
    print(f"   Spent: ${budget['spent']:.2f}")
    print(f"   Remaining: ${budget['remaining']:.2f}")
    print(f"   Used: {budget['percent_used']:.1f}%")
    
    if total['by_module']:
        print(f"\n📦 By Module:")
        for module, data in sorted(total['by_module'].items(), key=lambda x: x[1]['cost'], reverse=True):
            print(f"   {module:20s}: ${data['cost']:.4f} ({data['calls']} calls)")
    
    cache = report['cache_efficiency']
    print(f"\n🗃️  Cache Efficiency:")
    print(f"   Hit Rate: {cache['cache_hit_rate_percent']:.1f}%")
    print(f"   Savings: ${cache['total_savings_usd']:.4f}")
    
    if 'per_paper_analysis' in report and report['per_paper_analysis']:
        per_paper = report['per_paper_analysis']
        print(f"\n📄 Per-Paper Analysis:")
        print(f"   Papers Analyzed: {per_paper['total_papers_analyzed']}")
        print(f"   Avg Cost/Paper: ${per_paper['avg_cost_per_paper']:.4f}")
        print(f"   Range: ${per_paper['min_cost']:.4f} - ${per_paper['max_cost']:.4f}")
    
    if report['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"   {rec}")
    
    print("\n" + "="*60)
    print(f"Full report saved to: cost_reports/api_usage_report.json")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
