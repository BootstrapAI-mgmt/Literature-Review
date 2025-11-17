#!/usr/bin/env python3
"""Demonstrate impact of decay weighting on total evidence scores."""

import math
from datetime import datetime

def calculate_decay_weight(publication_year: int, half_life: float = 5.0) -> float:
    """Calculate decay weight for a paper."""
    current_year = datetime.now().year
    if publication_year > current_year:
        publication_year = current_year
    age_years = current_year - publication_year
    weight = math.pow(2, -age_years / half_life)
    return round(weight, 3)

def scenario_analysis():
    """Analyze several mock scenarios showing decay impact."""
    current_year = 2025
    
    scenarios = [
        {
            "name": "Scenario 1: Recent High-Quality Evidence",
            "description": "3 papers, all recent (2023-2024), high alignment",
            "papers": [
                {"title": "Paper A", "year": 2024, "alignment": 0.9},
                {"title": "Paper B", "year": 2023, "alignment": 0.85},
                {"title": "Paper C", "year": 2023, "alignment": 0.8},
            ]
        },
        {
            "name": "Scenario 2: Old High-Quality Evidence",
            "description": "3 papers, all old (2012-2015), high alignment",
            "papers": [
                {"title": "Paper A", "year": 2015, "alignment": 0.9},
                {"title": "Paper B", "year": 2013, "alignment": 0.85},
                {"title": "Paper C", "year": 2012, "alignment": 0.8},
            ]
        },
        {
            "name": "Scenario 3: Mixed Age Evidence",
            "description": "5 papers, mixed ages (2015-2024), varying alignment",
            "papers": [
                {"title": "Recent Strong", "year": 2024, "alignment": 0.9},
                {"title": "Recent Weak", "year": 2023, "alignment": 0.5},
                {"title": "Mid-age Strong", "year": 2020, "alignment": 0.85},
                {"title": "Old Strong", "year": 2015, "alignment": 0.9},
                {"title": "Old Weak", "year": 2012, "alignment": 0.4},
            ]
        },
        {
            "name": "Scenario 4: Stale Evidence Needing Update",
            "description": "4 papers, all very old (2010-2012), decent alignment",
            "papers": [
                {"title": "Paper A", "year": 2012, "alignment": 0.75},
                {"title": "Paper B", "year": 2011, "alignment": 0.7},
                {"title": "Paper C", "year": 2010, "alignment": 0.65},
                {"title": "Paper D", "year": 2010, "alignment": 0.6},
            ]
        },
    ]
    
    print("=" * 80)
    print("DECAY IMPACT ANALYSIS")
    print(f"Current Year: {current_year}")
    print(f"Half-Life: 5.0 years")
    print("=" * 80)
    print()
    
    for scenario in scenarios:
        print(f"\n{'=' * 80}")
        print(f"{scenario['name']}")
        print(f"{scenario['description']}")
        print(f"{'=' * 80}\n")
        
        # Calculate scores without decay
        total_alignment_no_decay = sum(p['alignment'] for p in scenario['papers'])
        avg_score_no_decay = total_alignment_no_decay / len(scenario['papers'])
        
        # Calculate scores with decay
        weighted_scores = []
        decay_weights = []
        
        print(f"{'Paper':<20} {'Year':<6} {'Age':<5} {'Align':<7} {'Decay':<7} {'Weighted':<10}")
        print(f"{'-'*70}")
        
        for paper in scenario['papers']:
            age = current_year - paper['year']
            decay = calculate_decay_weight(paper['year'])
            weighted = paper['alignment'] * decay
            
            weighted_scores.append(weighted)
            decay_weights.append(decay)
            
            print(f"{paper['title']:<20} {paper['year']:<6} {age:<5} "
                  f"{paper['alignment']:<7.2f} {decay:<7.3f} {weighted:<10.3f}")
        
        # Calculate with-decay metrics
        total_weighted = sum(weighted_scores)
        total_decay = sum(decay_weights)
        freshness_score = total_weighted / total_decay if total_decay > 0 else 0
        avg_decay_weight = total_decay / len(decay_weights)
        needs_update = avg_decay_weight < 0.5
        
        print(f"{'-'*70}")
        print()
        print(f"📊 SCORING COMPARISON:")
        print()
        print(f"  WITHOUT DECAY (traditional average):")
        print(f"    Total Alignment:  {total_alignment_no_decay:.3f}")
        print(f"    Average Score:    {avg_score_no_decay:.3f}")
        print()
        print(f"  WITH DECAY (temporal weighting):")
        print(f"    Total Weighted:   {total_weighted:.3f}")
        print(f"    Freshness Score:  {freshness_score:.3f}")
        print(f"    Avg Decay Weight: {avg_decay_weight:.3f}")
        print(f"    Needs Update:     {'YES ⚠️' if needs_update else 'NO ✅'}")
        print()
        print(f"  IMPACT:")
        score_diff = freshness_score - avg_score_no_decay
        percent_change = (score_diff / avg_score_no_decay * 100) if avg_score_no_decay > 0 else 0
        
        if score_diff > 0:
            print(f"    Score Change:     +{score_diff:.3f} ({percent_change:+.1f}%) ⬆️ BOOSTED")
            print(f"    Interpretation:   Recent evidence strengthens this requirement")
        elif score_diff < 0:
            print(f"    Score Change:     {score_diff:.3f} ({percent_change:+.1f}%) ⬇️ PENALIZED")
            print(f"    Interpretation:   Old evidence weakens this requirement")
        else:
            print(f"    Score Change:     {score_diff:.3f} (0.0%) ➡️ NEUTRAL")
        
        print()

if __name__ == "__main__":
    scenario_analysis()
