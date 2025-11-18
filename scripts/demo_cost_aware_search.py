#!/usr/bin/env python3
"""
Demo script for cost-aware search optimization.

This script demonstrates the new cost-aware search ordering features.
"""

import json
import tempfile
from pathlib import Path

from literature_review.optimization.search_optimizer import AdaptiveSearchOptimizer
from literature_review.utils.api_costs import CostEstimator


def demo_cost_estimation():
    """Demonstrate cost estimation for different APIs."""
    print("\n" + "="*70)
    print("DEMO: API Cost Estimation")
    print("="*70 + "\n")
    
    estimator = CostEstimator()
    
    # Test different search APIs
    searches = [
        {'query': 'Machine Learning', 'api': 'semantic_scholar', 'max_results': 50},
        {'query': 'Deep Learning', 'api': 'arxiv', 'max_results': 30},
        {'query': 'Neural Networks', 'api': 'openai_embedding', 'max_results': 20},
        {'query': 'LLM Analysis', 'api': 'anthropic_claude', 'max_results': 10},
    ]
    
    print("Individual Search Cost Estimates:")
    print("-" * 70)
    
    for search in searches:
        cost = estimator.estimate_search_cost(search)
        print(f"\nQuery: {search['query']}")
        print(f"  API: {cost['api']}")
        print(f"  Max Results: {search['max_results']}")
        print(f"  Estimated Calls: {cost['num_calls']}")
        print(f"  Cost per Call: ${cost['cost_per_call']:.4f}")
        print(f"  Total Cost: ${cost['total_cost']:.4f}")
    
    # Job-level estimation
    job_cost = estimator.estimate_job_cost(searches)
    
    print("\n" + "="*70)
    print("Total Job Cost Estimate:")
    print("-" * 70)
    print(f"Number of Searches: {job_cost['num_searches']}")
    print(f"Total Cost: ${job_cost['total_cost']:.2f}")
    print(f"Average Cost per Search: ${job_cost['avg_cost_per_search']:.4f}")


def demo_optimization_modes():
    """Demonstrate different optimization modes."""
    print("\n" + "="*70)
    print("DEMO: Optimization Modes")
    print("="*70 + "\n")
    
    # Create sample gap data
    gap_data = {
        "Pillar 1: Test": {
            "completeness": 40.0,
            "analysis": {
                "REQ-1": {
                    "Sub-1.1: Critical Gap": {
                        "completeness_percent": 10,
                        "gap_analysis": "Critical gap",
                        "contributing_papers": [{"filename": "p1.pdf"}]
                    }
                }
            }
        }
    }
    
    search_data = [{
        "pillar": "Pillar 1",
        "requirement": "Critical Gap",
        "suggested_searches": [{"query": "test", "databases": ["Scholar"]}]
    }]
    
    # Create temp files
    with tempfile.TemporaryDirectory() as tmpdir:
        gap_file = Path(tmpdir) / "gaps.json"
        search_file = Path(tmpdir) / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(gap_data, f)
        with open(search_file, 'w') as f:
            json.dump(search_data, f)
        
        # Test different modes
        modes = ['coverage', 'cost', 'balanced']
        
        searches = [
            {'query': 'Expensive high-value', 'api': 'anthropic_claude', 'max_results': 100,
             'gap_severity': 'Critical', 'papers_needed': 8},
            {'query': 'Free high-value', 'api': 'semantic_scholar', 'max_results': 50,
             'gap_severity': 'Critical', 'papers_needed': 8},
            {'query': 'Free low-value', 'api': 'arxiv', 'max_results': 10,
             'gap_severity': 'Low', 'papers_needed': 2}
        ]
        
        for mode in modes:
            print(f"\n{mode.upper()} Mode:")
            print("-" * 70)
            
            config = {'roi_optimizer': {'mode': mode}}
            optimizer = AdaptiveSearchOptimizer(str(gap_file), str(search_file), config=config)
            
            prioritized = optimizer.prioritize_searches_with_cost(searches)
            
            for i, search in enumerate(prioritized, 1):
                print(f"\n  {i}. {search['query']}")
                print(f"     API: {search['api']}")
                print(f"     Cost: ${search['cost']:.4f}")
                print(f"     ROI: {search['roi']:.2f}")
                print(f"     Value/$: {search.get('value_per_dollar', 0):.2f}")


def demo_budget_constraint():
    """Demonstrate budget constraint enforcement."""
    print("\n" + "="*70)
    print("DEMO: Budget Constraint")
    print("="*70 + "\n")
    
    # Create sample data
    gap_data = {
        "Pillar 1: Test": {
            "completeness": 40.0,
            "analysis": {
                "REQ-1": {
                    "Sub-1.1: Gap": {
                        "completeness_percent": 50,
                        "gap_analysis": "Moderate gap",
                        "contributing_papers": []
                    }
                }
            }
        }
    }
    
    search_data = [{
        "pillar": "Pillar 1",
        "requirement": "Gap",
        "suggested_searches": [{"query": "test", "databases": ["Scholar"]}]
    }]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        gap_file = Path(tmpdir) / "gaps.json"
        search_file = Path(tmpdir) / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(gap_data, f)
        with open(search_file, 'w') as f:
            json.dump(search_data, f)
        
        # Create searches with different costs
        searches = [
            {'query': 'Search 1', 'api': 'anthropic_claude', 'max_results': 50,
             'gap_severity': 'Critical', 'papers_needed': 8},
            {'query': 'Search 2', 'api': 'openai_embedding', 'max_results': 30,
             'gap_severity': 'High', 'papers_needed': 5},
            {'query': 'Search 3', 'api': 'semantic_scholar', 'max_results': 20,
             'gap_severity': 'Medium', 'papers_needed': 3}
        ]
        
        # Test without budget limit
        print("WITHOUT Budget Limit:")
        print("-" * 70)
        
        config = {'roi_optimizer': {'mode': 'balanced', 'budget_limit': None}}
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(search_file), config=config)
        
        prioritized = optimizer.prioritize_searches_with_cost(searches)
        total_cost = sum(s['cost'] for s in prioritized if not s.get('skipped', False))
        
        print(f"Searches included: {len(prioritized)}")
        print(f"Total cost: ${total_cost:.2f}")
        
        # Test with budget limit
        print("\n\nWITH Budget Limit ($0.05):")
        print("-" * 70)
        
        config = {'roi_optimizer': {'mode': 'balanced', 'budget_limit': 0.05}}
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(search_file), config=config)
        
        prioritized = optimizer.prioritize_searches_with_cost(searches)
        
        included = [s for s in prioritized if not s.get('skipped', False)]
        skipped = [s for s in prioritized if s.get('skipped', False)]
        total_cost = sum(s['cost'] for s in included)
        
        print(f"Searches included: {len(included)}")
        print(f"Searches skipped: {len(skipped)}")
        print(f"Total cost: ${total_cost:.2f}")
        
        if included:
            print("\nIncluded searches:")
            for s in included:
                print(f"  - {s['query']} (${s['cost']:.4f})")
        
        if skipped:
            print("\nSkipped searches:")
            for s in skipped:
                print(f"  - {s['query']} - {s.get('skip_reason', 'Unknown')}")


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("COST-AWARE SEARCH OPTIMIZATION DEMO")
    print("="*70)
    
    try:
        demo_cost_estimation()
        demo_optimization_modes()
        demo_budget_constraint()
        
        print("\n" + "="*70)
        print("DEMO COMPLETE")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
