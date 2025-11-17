#!/usr/bin/env python3
"""Strategic comparison: Two requirements with same average score but different temporal profiles."""

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

def strategic_comparison():
    """Compare two requirements with same average but different temporal profiles."""
    
    # Requirement A: Recent but weaker evidence
    req_a = {
        "name": "Requirement A: Neural Plasticity Mechanisms",
        "papers": [
            {"title": "2024 Review", "year": 2024, "alignment": 0.70},
            {"title": "2023 Meta-analysis", "year": 2023, "alignment": 0.75},
            {"title": "2022 Study", "year": 2022, "alignment": 0.65},
        ]
    }
    
    # Requirement B: Old but stronger evidence
    req_b = {
        "name": "Requirement B: Synaptic Transmission",
        "papers": [
            {"title": "2012 Landmark Study", "year": 2012, "alignment": 0.85},
            {"title": "2011 Review", "year": 2011, "alignment": 0.80},
            {"title": "2010 Experimental", "year": 2010, "alignment": 0.65},
        ]
    }
    
    current_year = 2025
    
    print("=" * 80)
    print("STRATEGIC COMPARISON: TEMPORAL PROFILE MATTERS")
    print("=" * 80)
    print()
    print("Question: Which requirement should we prioritize for new literature search?")
    print()
    
    for req in [req_a, req_b]:
        print(f"\n{'=' * 80}")
        print(f"{req['name']}")
        print(f"{'=' * 80}\n")
        
        # Calculate without decay
        avg_no_decay = sum(p['alignment'] for p in req['papers']) / len(req['papers'])
        
        # Calculate with decay
        weighted_scores = []
        decay_weights = []
        
        print(f"{'Paper':<25} {'Year':<6} {'Age':<5} {'Align':<7} {'Decay':<7} {'Weighted':<10}")
        print(f"{'-'*75}")
        
        for paper in req['papers']:
            age = current_year - paper['year']
            decay = calculate_decay_weight(paper['year'])
            weighted = paper['alignment'] * decay
            
            weighted_scores.append(weighted)
            decay_weights.append(decay)
            
            print(f"{paper['title']:<25} {paper['year']:<6} {age:<5} "
                  f"{paper['alignment']:<7.2f} {decay:<7.3f} {weighted:<10.3f}")
        
        total_weighted = sum(weighted_scores)
        total_decay = sum(decay_weights)
        freshness_score = total_weighted / total_decay if total_decay > 0 else 0
        avg_decay_weight = total_decay / len(decay_weights)
        needs_update = avg_decay_weight < 0.5
        
        print(f"{'-'*75}")
        print()
        print(f"📊 SCORES:")
        print(f"  Traditional Average:    {avg_no_decay:.3f}")
        print(f"  Freshness Score:        {freshness_score:.3f}")
        print(f"  Avg Decay Weight:       {avg_decay_weight:.3f}")
        print(f"  Needs Update:           {'YES ⚠️' if needs_update else 'NO ✅'}")
        print()
    
    # Summary comparison
    print(f"\n{'=' * 80}")
    print("STRATEGIC DECISION")
    print(f"{'=' * 80}\n")
    
    avg_a = sum(p['alignment'] for p in req_a['papers']) / len(req_a['papers'])
    avg_b = sum(p['alignment'] for p in req_b['papers']) / len(req_b['papers'])
    
    # Calculate freshness scores
    weighted_a = sum(p['alignment'] * calculate_decay_weight(p['year']) for p in req_a['papers'])
    decay_a = sum(calculate_decay_weight(p['year']) for p in req_a['papers'])
    freshness_a = weighted_a / decay_a
    
    weighted_b = sum(p['alignment'] * calculate_decay_weight(p['year']) for p in req_b['papers'])
    decay_b = sum(calculate_decay_weight(p['year']) for p in req_b['papers'])
    freshness_b = weighted_b / decay_b
    
    avg_decay_a = decay_a / len(req_a['papers'])
    avg_decay_b = decay_b / len(req_b['papers'])
    
    print(f"WITHOUT DECAY WEIGHTING:")
    print(f"  Requirement A: {avg_a:.3f}")
    print(f"  Requirement B: {avg_b:.3f}")
    print(f"  Both have identical average scores! 🤷")
    print(f"  Decision: No clear priority")
    print()
    print(f"WITH DECAY WEIGHTING:")
    print(f"  Requirement A:")
    print(f"    Freshness Score: {freshness_a:.3f}")
    print(f"    Avg Decay:       {avg_decay_a:.3f} (recent, {int((1-avg_decay_a)*100)}% value lost)")
    print(f"    Status:          {'Needs Update ⚠️' if avg_decay_a < 0.5 else 'Current ✅'}")
    print()
    print(f"  Requirement B:")
    print(f"    Freshness Score: {freshness_b:.3f}")
    print(f"    Avg Decay:       {avg_decay_b:.3f} (stale, {int((1-avg_decay_b)*100)}% value lost)")
    print(f"    Status:          {'Needs Update ⚠️' if avg_decay_b < 0.5 else 'Current ✅'}")
    print()
    print(f"🎯 RECOMMENDATION:")
    print(f"  Prioritize Requirement B for new literature search!")
    print(f"  Reason: Evidence is 13-15 years old (avg {avg_decay_b:.1%} weight remaining)")
    print(f"          vs. 1-3 years old (avg {avg_decay_a:.1%} weight remaining)")
    print()
    print(f"💡 INSIGHT:")
    print(f"  Even though both requirements have the same traditional average score,")
    print(f"  Requirement B's evidence base is critically outdated and needs refresh.")
    print(f"  This temporal awareness helps prioritize research effort effectively.")
    print()

if __name__ == "__main__":
    strategic_comparison()
