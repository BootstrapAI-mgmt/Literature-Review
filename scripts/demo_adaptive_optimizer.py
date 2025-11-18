#!/usr/bin/env python
"""
Demonstration script for Adaptive ROI Search Optimizer.

This script shows how the adaptive optimizer dynamically adjusts
search priorities based on gap coverage.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import tempfile
from literature_review.optimization.search_optimizer import (
    SearchOptimizer,
    AdaptiveSearchOptimizer
)


def create_demo_data():
    """Create demonstration gap analysis and search data."""
    gap_data = {
        "Pillar 1: Core Requirements": {
            "completeness": 35.0,
            "analysis": {
                "REQ-1.1: Security": {
                    "Sub-1.1.1: Authentication methods": {
                        "completeness_percent": 15,
                        "gap_analysis": "Critical gap - need modern auth patterns",
                        "confidence_level": "high",
                        "contributing_papers": [
                            {"filename": "oauth_paper.pdf", "title": "OAuth 2.0 Guide"}
                        ]
                    },
                    "Sub-1.1.2: Encryption protocols": {
                        "completeness_percent": 60,
                        "gap_analysis": "Moderate coverage",
                        "confidence_level": "medium",
                        "contributing_papers": [
                            {"filename": f"crypto{i}.pdf", "title": f"Crypto Paper {i}"} 
                            for i in range(4)
                        ]
                    }
                },
                "REQ-1.2: Performance": {
                    "Sub-1.2.1: Caching strategies": {
                        "completeness_percent": 5,
                        "gap_analysis": "Critical gap - minimal coverage",
                        "confidence_level": "high",
                        "contributing_papers": []
                    }
                }
            }
        }
    }
    
    search_data = [
        {
            "pillar": "Pillar 1",
            "requirement": "Authentication methods",
            "current_completeness": 15,
            "priority": "CRITICAL",
            "urgency": 1,
            "gap_description": "Critical gap - need modern auth patterns",
            "suggested_searches": [
                {
                    "query": 'modern authentication AND "multi-factor"',
                    "rationale": "Target MFA implementations",
                    "databases": ["Google Scholar", "IEEE"]
                },
                {
                    "query": 'passwordless authentication AND biometric',
                    "rationale": "Emerging auth methods",
                    "databases": ["Google Scholar"]
                }
            ]
        },
        {
            "pillar": "Pillar 1",
            "requirement": "Caching strategies",
            "current_completeness": 5,
            "priority": "CRITICAL",
            "urgency": 1,
            "gap_description": "Critical gap - minimal coverage",
            "suggested_searches": [
                {
                    "query": 'distributed caching AND "redis patterns"',
                    "rationale": "Popular caching solutions",
                    "databases": ["Google Scholar"]
                }
            ]
        },
        {
            "pillar": "Pillar 1",
            "requirement": "Encryption protocols",
            "current_completeness": 60,
            "priority": "MEDIUM",
            "urgency": 3,
            "gap_description": "Moderate coverage",
            "suggested_searches": [
                {
                    "query": "TLS 1.3 performance",
                    "rationale": "Latest protocol improvements",
                    "databases": ["Google Scholar"]
                }
            ]
        }
    ]
    
    return gap_data, search_data


def demonstrate_static_optimization():
    """Show static ROI optimization."""
    print("\n" + "="*70)
    print("DEMONSTRATION: STATIC ROI OPTIMIZATION")
    print("="*70)
    
    # Create temporary files
    with tempfile.TemporaryDirectory() as tmpdir:
        gap_file = Path(tmpdir) / "gaps.json"
        search_file = Path(tmpdir) / "searches.json"
        
        gap_data, search_data = create_demo_data()
        
        with open(gap_file, 'w') as f:
            json.dump(gap_data, f, indent=2)
        with open(search_file, 'w') as f:
            json.dump(search_data, f, indent=2)
        
        # Run static optimization
        optimizer = SearchOptimizer(str(gap_file), str(search_file))
        plan = optimizer.optimize_search_plan()
        
        print(f"\nTotal Searches: {plan['total_searches']}")
        print(f"High Priority: {plan['high_priority_searches']}")
        print("\nSearch Plan (by ROI):")
        
        for i, search in enumerate(plan['search_plan'], 1):
            print(f"\n{i}. {search['query']}")
            print(f"   Requirement: {search['requirement']}")
            print(f"   Gap Severity: {search['gap_severity']}")
            print(f"   Papers Needed: {search['papers_needed']}")
            print(f"   ROI Score: {search['roi_score']:.2f}")
            print(f"   Priority: {search['priority']}")
        
        print("\n" + "="*70)


def demonstrate_adaptive_optimization():
    """Show adaptive ROI optimization."""
    print("\n" + "="*70)
    print("DEMONSTRATION: ADAPTIVE ROI OPTIMIZATION")
    print("="*70)
    
    # Create temporary files
    with tempfile.TemporaryDirectory() as tmpdir:
        gap_file = Path(tmpdir) / "gaps.json"
        search_file = Path(tmpdir) / "searches.json"
        
        gap_data, search_data = create_demo_data()
        
        with open(gap_file, 'w') as f:
            json.dump(gap_data, f, indent=2)
        with open(search_file, 'w') as f:
            json.dump(search_data, f, indent=2)
        
        # Configure adaptive optimizer
        config = {
            'roi_optimizer': {
                'batch_size': 1,  # Small batch to see adaptation
                'min_roi_threshold': 0.05,
                'convergence_threshold': 0.7
            }
        }
        
        optimizer = AdaptiveSearchOptimizer(
            str(gap_file), 
            str(search_file), 
            config
        )
        
        # Mock search execution
        batch_count = [0]  # Use list to allow modification in nested function
        
        def mock_search_execution(batch):
            """Simulate finding papers for searches."""
            batch_count[0] += 1
            print(f"\n--- EXECUTING BATCH {batch_count[0]} ---")
            
            results = []
            for search in batch:
                print(f"\nExecuting: {search['query']}")
                print(f"  Target: {search['requirement']}")
                print(f"  Current ROI: {search.get('roi', search['roi_score']):.2f}")
                
                # Simulate finding papers
                papers = [
                    {'title': f"Found Paper {i} for {search['requirement']}"} 
                    for i in range(5)
                ]
                
                print(f"  Found: {len(papers)} papers")
                
                results.append({
                    'search': search,
                    'papers': papers
                })
            
            return results
        
        # Run adaptive optimization
        print("\nStarting adaptive optimization...")
        result = optimizer.optimize_searches_adaptive(
            mock_execute_batch=mock_search_execution
        )
        
        # Display results
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"\nCompleted Searches: {len(result['completed_searches'])}")
        print(f"Total Papers Found: {len(result['search_results']) * 5}")  # 5 per search
        print(f"Convergence Reached: {result['convergence_reached']}")
        
        print("\n--- ROI EVOLUTION ---")
        for i, entry in enumerate(result['roi_history'], 1):
            print(f"\nAfter Batch {i}:")
            print(f"  Completed: {entry['completed_count']}")
            print(f"  Pending: {entry['pending_count']}")
            print(f"  Avg ROI: {entry['avg_roi']:.2f}")
            print(f"  Top ROI: {entry['top_search_roi']:.2f}")
        
        print("\n--- FINAL GAP COVERAGE ---")
        for gap_cov in result['gaps_final_coverage']:
            print(f"\n{gap_cov['requirement']}")
            print(f"  Coverage: {gap_cov['coverage']*100:.1f}%")
            print(f"  Papers: {gap_cov['papers_count']}")
        
        print("\n" + "="*70)


def demonstrate_convergence():
    """Show convergence detection."""
    print("\n" + "="*70)
    print("DEMONSTRATION: CONVERGENCE DETECTION")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        gap_file = Path(tmpdir) / "gaps.json"
        search_file = Path(tmpdir) / "searches.json"
        
        gap_data, search_data = create_demo_data()
        
        with open(gap_file, 'w') as f:
            json.dump(gap_data, f, indent=2)
        with open(search_file, 'w') as f:
            json.dump(search_data, f, indent=2)
        
        config = {
            'roi_optimizer': {
                'batch_size': 1,
                'min_roi_threshold': 0.01,
                'convergence_threshold': 0.7
            }
        }
        
        optimizer = AdaptiveSearchOptimizer(
            str(gap_file), 
            str(search_file), 
            config
        )
        
        def mock_search_with_high_coverage(batch):
            """Simulate finding many papers to trigger convergence."""
            results = []
            for search in batch:
                # Find many papers to quickly fill gaps
                papers = [
                    {'title': f"Paper {i}"} for i in range(8)
                ]
                results.append({
                    'search': search,
                    'papers': papers
                })
            return results
        
        result = optimizer.optimize_searches_adaptive(
            mock_execute_batch=mock_search_with_high_coverage
        )
        
        print(f"\nSearches executed before convergence: {len(result['completed_searches'])}")
        print(f"Convergence reached: {result['convergence_reached']}")
        print("\nFinal coverage:")
        for gap_cov in result['gaps_final_coverage']:
            if gap_cov['coverage'] > 0:
                print(f"  {gap_cov['requirement']}: {gap_cov['coverage']*100:.1f}%")
        
        print("\n" + "="*70)


if __name__ == '__main__':
    print("\n" + "#"*70)
    print("# ADAPTIVE ROI SEARCH OPTIMIZER - DEMONSTRATION")
    print("#"*70)
    
    # Run demonstrations
    demonstrate_static_optimization()
    demonstrate_adaptive_optimization()
    demonstrate_convergence()
    
    print("\n" + "#"*70)
    print("# DEMONSTRATION COMPLETE")
    print("#"*70)
    print("\nKey Takeaways:")
    print("  1. Static optimization calculates ROI once at start")
    print("  2. Adaptive optimization recalculates ROI after each batch")
    print("  3. Search priorities change based on gap coverage")
    print("  4. Convergence detection stops when critical gaps are covered")
    print("  5. ROI history tracks optimization progress over time")
    print()
