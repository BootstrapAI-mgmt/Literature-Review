#!/usr/bin/env python3
"""
Demonstration of field-specific half-life presets for Evidence Decay Tracker.

This script shows how to:
1. Use research field presets
2. Auto-detect fields from papers
3. Compare decay rates across different fields
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from literature_review.utils.decay_presets import (
    get_preset,
    suggest_field_from_papers,
    list_all_presets,
    FIELD_PRESETS
)
from literature_review.utils.evidence_decay import EvidenceDecayTracker


def demo_presets():
    """Demonstrate all available presets."""
    print("=" * 80)
    print("AVAILABLE RESEARCH FIELD PRESETS")
    print("=" * 80)
    print()
    
    presets = list_all_presets()
    
    for field_key, preset in presets.items():
        if field_key == 'custom':
            continue  # Skip custom for now
        
        print(f"🔬 {preset['name']}")
        print(f"   Half-Life: {preset['half_life_years']} years")
        print(f"   Description: {preset['description']}")
        print(f"   Examples: {', '.join(preset['examples'][:3])}")
        print()


def demo_auto_detection():
    """Demonstrate auto-detection of research fields."""
    print("=" * 80)
    print("AUTO-DETECTION OF RESEARCH FIELDS")
    print("=" * 80)
    print()
    
    # Test different paper sets
    test_cases = [
        {
            'name': 'AI/ML Papers',
            'papers': [
                {'title': 'Deep Learning for Image Recognition', 'abstract': 'Neural networks and machine learning...'},
                {'title': 'Attention Mechanisms in NLP', 'abstract': 'Artificial intelligence for language...'},
                {'title': 'Reinforcement Learning Algorithms', 'abstract': 'Deep learning agent training...'}
            ]
        },
        {
            'name': 'Mathematics Papers',
            'papers': [
                {'title': 'Proof of the Riemann Hypothesis', 'abstract': 'Mathematical theorem and proof...'},
                {'title': 'Number Theory Applications', 'abstract': 'Mathematics in cryptography...'}
            ]
        },
        {
            'name': 'Biology Papers',
            'papers': [
                {'title': 'Genetic Markers in Disease', 'abstract': 'Molecular biology and genetics research...'},
                {'title': 'Cell Biology Studies', 'abstract': 'Biological processes at cellular level...'}
            ]
        },
        {
            'name': 'Mixed Papers',
            'papers': [
                {'title': 'Machine Learning in Biology', 'abstract': 'AI for genetic analysis...'},
                {'title': 'Random Topic', 'abstract': 'Something else entirely...'}
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"📚 {test_case['name']}:")
        
        # Show paper titles
        for paper in test_case['papers']:
            print(f"   - {paper['title']}")
        
        # Auto-detect field
        suggested_field = suggest_field_from_papers(test_case['papers'])
        preset = get_preset(suggested_field)
        
        print(f"   ✅ Detected Field: {preset['name']}")
        print(f"   ⏱️  Half-Life: {preset['half_life_years']} years")
        print()


def demo_decay_comparison():
    """Compare decay rates across different fields."""
    print("=" * 80)
    print("DECAY RATE COMPARISON ACROSS FIELDS")
    print("=" * 80)
    print()
    
    current_year = datetime.now().year
    test_years = [
        current_year,      # Current
        current_year - 3,  # 3 years ago
        current_year - 5,  # 5 years ago
        current_year - 10, # 10 years ago
    ]
    
    # Select a few representative fields
    fields_to_compare = ['ai_ml', 'software_engineering', 'computer_science', 'mathematics']
    
    # Create trackers for each field
    trackers = {}
    for field_key in fields_to_compare:
        config = {
            'evidence_decay': {
                'research_field': field_key,
                'half_life_years': None
            }
        }
        trackers[field_key] = EvidenceDecayTracker(config=config)
    
    # Print header
    print(f"{'Year':<12}", end='')
    for field_key in fields_to_compare:
        preset = get_preset(field_key)
        print(f"{preset['name']:<25}", end='')
    print()
    print("-" * 100)
    
    # Print decay weights for each year
    for year in test_years:
        age = current_year - year
        print(f"{year} ({age}y)  ", end='')
        
        for field_key in fields_to_compare:
            tracker = trackers[field_key]
            weight = tracker.calculate_decay_weight(year)
            print(f"{weight:>6.1%} ({tracker.half_life:>2.0f}y half-life)   ", end='')
        
        print()
    
    print()
    print("Observations:")
    print("- AI/ML (3-year half-life): Fastest decay, 3-year-old papers at 50%")
    print("- Software Eng (5-year half-life): Moderate decay")
    print("- Computer Science (7-year half-life): Slower decay")
    print("- Mathematics (10-year half-life): Slowest decay, retains value longest")
    print()


def demo_config_usage():
    """Demonstrate configuration usage."""
    print("=" * 80)
    print("CONFIGURATION EXAMPLES")
    print("=" * 80)
    print()
    
    # Example 1: Using preset
    print("1️⃣  Using a Preset (Recommended)")
    print("-" * 40)
    config1 = {
        'evidence_decay': {
            'enabled': True,
            'research_field': 'ai_ml',
            'half_life_years': None  # Use preset
        }
    }
    tracker1 = EvidenceDecayTracker(config=config1)
    print(f"Config: research_field='ai_ml', half_life_years=null")
    print(f"Result: Using {tracker1.field_name} preset")
    print(f"Half-Life: {tracker1.half_life} years")
    print()
    
    # Example 2: Custom override
    print("2️⃣  Custom Override")
    print("-" * 40)
    config2 = {
        'evidence_decay': {
            'enabled': True,
            'research_field': 'ai_ml',  # Ignored
            'half_life_years': 4.5  # Custom value
        }
    }
    tracker2 = EvidenceDecayTracker(config=config2)
    print(f"Config: research_field='ai_ml', half_life_years=4.5")
    print(f"Result: Using {tracker2.field_name} mode")
    print(f"Half-Life: {tracker2.half_life} years (custom override)")
    print()
    
    # Example 3: Legacy mode
    print("3️⃣  Legacy Mode (Backward Compatible)")
    print("-" * 40)
    tracker3 = EvidenceDecayTracker(half_life_years=6.0)
    print(f"Direct initialization: EvidenceDecayTracker(half_life_years=6.0)")
    print(f"Result: Using {tracker3.field_name} mode")
    print(f"Half-Life: {tracker3.half_life} years")
    print()


def main():
    """Run all demonstrations."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "EVIDENCE DECAY PRESETS DEMO" + " " * 31 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    demo_presets()
    demo_auto_detection()
    demo_decay_comparison()
    demo_config_usage()
    
    print("=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print()
    print("For more information, see:")
    print("  - docs/EVIDENCE_DECAY_README.md")
    print("  - tests/unit/test_decay_presets.py")
    print()


if __name__ == '__main__':
    main()
