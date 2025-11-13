#!/usr/bin/env python3
"""
Fuzzy Matching and Normalization Demo

This demo shows how the Judge system uses string normalization and fuzzy
matching to robustly match claims to pillar definitions, handling variations
in text, typos, and formatting differences.

Run: python demos/demo_fuzzy_matching.py
"""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from literature_review.analysis.judge import (
    _normalize_string,
    load_pillar_definitions,
    _build_lookup_map,
    find_robust_sub_requirement_text,
    find_robust_pillar_key
)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_normalization():
    """Demonstrate string normalization."""
    print_section("STRING NORMALIZATION DEMO")
    
    print("\nNormalization removes prefixes, special chars, and standardizes text:")
    print()
    
    test_cases = [
        ("Sub-1.1.1: Conclusive model of sensory data", "Standard sub-requirement"),
        ("SR-2.3.5: Event-based sensor integration", "Alternative SR prefix"),
        ("  Sub 3.4.2:   Pathway shift from cognitive to motor  ", "Extra whitespace"),
        ("SUB-4.1.1: AI EQUIVALENT OF DECLARATIVE LEARNING", "All uppercase"),
        ("Sub-1.2.3: Model! with? special, chars:", "Special characters"),
        ("   ", "Empty/whitespace only"),
    ]
    
    for original, description in test_cases:
        normalized = _normalize_string(original)
        print(f"Description: {description}")
        print(f"  Original:    '{original}'")
        print(f"  Normalized:  '{normalized}'")
        print()


def demo_fuzzy_matching():
    """Demonstrate fuzzy matching with pillar definitions."""
    print_section("FUZZY MATCHING DEMO")
    
    # Load actual pillar definitions
    print("\nLoading pillar definitions...")
    definitions = load_pillar_definitions("pillar_definitions.json")
    
    if not definitions:
        print("❌ Could not load pillar definitions")
        return
    
    # Build lookup maps
    _build_lookup_map(definitions)
    print("✅ Lookup maps built")
    
    print("\n" + "-" * 70)
    print("EXACT MATCH TESTS")
    print("-" * 70)
    
    # Test exact matches
    exact_tests = [
        "Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes",
        "Sub-2.1.1: Event-based sensor integration with SNNs",
        "Sub-3.1.1: Procedural skill learning with explicit instruction",
    ]
    
    for query in exact_tests:
        result = find_robust_sub_requirement_text(query)
        status = "✅ FOUND" if result else "❌ NOT FOUND"
        print(f"\n{status}")
        print(f"  Query: '{query[:60]}...'")
        if result:
            print(f"  Match: '{result[:60]}...'")
    
    print("\n" + "-" * 70)
    print("FUZZY MATCH TESTS (variations and typos)")
    print("-" * 70)
    
    # Test fuzzy matches
    fuzzy_tests = [
        ("conclusive model sensory data neural spikes", "Missing prefix and formatting"),
        ("Event based sensor integration", "Missing hyphens"),
        ("procedural skill learning explicit instruction", "Lowercase, no punctuation"),
    ]
    
    for query, description in fuzzy_tests:
        result = find_robust_sub_requirement_text(query)
        status = "✅ FOUND" if result else "❌ NOT FOUND"
        print(f"\n{status} - {description}")
        print(f"  Query: '{query}'")
        if result:
            print(f"  Match: '{result[:60]}...'")
        else:
            print(f"  Match: None (may be below confidence threshold)")
    
    print("\n" + "-" * 70)
    print("NO MATCH TESTS (unrelated text)")
    print("-" * 70)
    
    # Test no matches
    no_match_tests = [
        "Completely unrelated text that won't match",
        "Random words with no connection",
        "xyz123 invalid nonsense",
    ]
    
    for query in no_match_tests:
        result = find_robust_sub_requirement_text(query)
        status = "✅ CORRECT (No Match)" if not result else "❌ FALSE MATCH"
        print(f"\n{status}")
        print(f"  Query: '{query}'")
        print(f"  Result: {result if result else 'None (as expected)'}")


def demo_pillar_matching():
    """Demonstrate pillar key matching."""
    print_section("PILLAR KEY MATCHING DEMO")
    
    # Load definitions
    definitions = load_pillar_definitions("pillar_definitions.json")
    if not definitions:
        print("❌ Could not load pillar definitions")
        return
    
    _build_lookup_map(definitions)
    
    print("\nTesting pillar key variations:")
    print()
    
    pillar_tests = [
        ("Pillar 1: Biological Stimulus-Response", "Full pillar name"),
        ("Pillar 1", "Pillar number only"),
        ("pillar 2: ai stimulus-response", "Lowercase variation"),
        ("PILLAR 3", "Uppercase"),
        ("Pillar 7: System Integration & Orchestration", "With special chars"),
    ]
    
    for query, description in pillar_tests:
        result = find_robust_pillar_key(query)
        status = "✅ FOUND" if result else "❌ NOT FOUND"
        print(f"{status} - {description}")
        print(f"  Query:  '{query}'")
        if result:
            print(f"  Match:  '{result}'")
        print()


def demo_statistics():
    """Show statistics about pillar definitions."""
    print_section("PILLAR DEFINITIONS STATISTICS")
    
    definitions = load_pillar_definitions("pillar_definitions.json")
    if not definitions:
        print("❌ Could not load pillar definitions")
        return
    
    pillar_keys = [k for k in definitions.keys() if k.startswith("Pillar")]
    
    print(f"\nTotal Pillars: {len(pillar_keys)}")
    print()
    
    for pillar_key in sorted(pillar_keys):
        pillar_data = definitions[pillar_key]
        requirements = pillar_data.get("requirements", {})
        
        total_sub_reqs = sum(len(sub_reqs) for sub_reqs in requirements.values())
        
        print(f"{pillar_key}")
        print(f"  Requirement categories: {len(requirements)}")
        print(f"  Total sub-requirements: {total_sub_reqs}")
        print()
    
    # Build lookup and show map size
    _build_lookup_map(definitions)
    
    from literature_review.analysis.judge import DEFINITIONS_LOOKUP_MAP, CANONICAL_PILLAR_MAP
    
    print("Lookup Maps:")
    print(f"  Sub-requirement entries: {len(DEFINITIONS_LOOKUP_MAP)}")
    print(f"  Pillar key entries: {len(CANONICAL_PILLAR_MAP)}")


def main():
    """Run all demos."""
    print("\n" + "█" * 70)
    print("  FUZZY MATCHING AND NORMALIZATION DEMO")
    print("█" * 70)
    
    # Run demos
    demo_normalization()
    demo_fuzzy_matching()
    demo_pillar_matching()
    demo_statistics()
    
    # Summary
    print("\n" + "=" * 70)
    print("  Demo complete!")
    print("  ")
    print("  Key Takeaways:")
    print("  - Normalization handles prefixes, case, and special chars")
    print("  - Fuzzy matching finds similar text even with variations")
    print("  - System is robust to common text formatting differences")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
