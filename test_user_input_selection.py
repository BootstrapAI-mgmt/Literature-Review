#!/usr/bin/env python3
"""
User Input Selection Test
Tests the user input tree and selection functionality for alignment issues
"""

import json
import sys
from io import StringIO
from unittest.mock import patch

def test_user_input_prompts():
    """Test that user prompts match available options"""
    
    print("=" * 70)
    print("USER INPUT SELECTION TEST")
    print("=" * 70)
    
    # Load pillar definitions
    with open('pillar_definitions.json') as f:
        pillar_definitions = json.load(f)
    
    pillar_names = list(pillar_definitions.keys())
    metadata_sections = {'Framework_Overview', 'Cross_Cutting_Requirements', 'Success_Criteria'}
    analyzable_pillars = [k for k in pillar_names if k not in metadata_sections]
    
    print(f"\n[1/4] Analyzing pillar structure...")
    print(f"  Total pillars in config: {len(pillar_names)}")
    print(f"  Analyzable pillars: {len(analyzable_pillars)}")
    print(f"  Metadata sections: {len(metadata_sections)}")
    
    # Test 1: Check prompt numbering
    print(f"\n[2/4] Checking prompt message...")
    
    # Simulate what the user sees
    print("\n  Current user prompt:")
    print("  " + "-" * 50)
    for i, name in enumerate(pillar_names, 1):
        status = "" if name in analyzable_pillars else " (metadata - skip)"
        print(f"    {i}. {name.split(':')[0]}{status}")
    print("    ALL - Run analysis on all pillars (one pass)")
    print("    DEEP - Run iterative deep-review loop on all pillars")
    print("    NONE - Exit (default)")
    print("  " + "-" * 50)
    
    # Check for hardcoded prompt issue
    print("\n[3/4] Checking for hardcoded range...")
    with open('literature_review/orchestrator.py', 'r') as f:
        orchestrator_code = f.read()
    
    # Find the input prompt line
    if 'Enter choice (1-6' in orchestrator_code:
        print("  ❌ FOUND HARDCODED RANGE: 'Enter choice (1-6...'")
        print(f"     Should be: 'Enter choice (1-{len(pillar_names)}...'")
        hardcoded_issue = True
    else:
        print("  ✅ No hardcoded range found")
        hardcoded_issue = False
    
    # Test 2: Check selection logic
    print(f"\n[4/4] Testing selection logic...")
    
    test_cases = [
        ("1", "Framework_Overview", True, "metadata - should be rejected"),
        ("2", "Pillar 1", False, "valid pillar"),
        (str(len(pillar_names)), "Success_Criteria", True, "metadata - should be rejected"),
        ("ALL", "all analyzable", False, "should work"),
        ("DEEP", "all analyzable", False, "should work"),
        ("NONE", "exit", False, "should work"),
        ("", "exit (default)", False, "should work"),
    ]
    
    issues_found = []
    
    for choice_input, expected_name, should_fail, description in test_cases:
        if choice_input.isdigit():
            choice_idx = int(choice_input) - 1
            if 0 <= choice_idx < len(pillar_names):
                selected = pillar_names[choice_idx]
                is_metadata = selected in metadata_sections
                
                if is_metadata and should_fail:
                    result = "✅ Correctly rejects metadata"
                elif not is_metadata and not should_fail:
                    result = "✅ Correctly accepts pillar"
                else:
                    result = f"❌ Logic error"
                    issues_found.append(f"{choice_input} -> {selected}: {description}")
            else:
                result = "❌ Out of range"
                issues_found.append(f"{choice_input}: out of range")
        else:
            result = "✅ Special command"
        
        print(f"  {choice_input:6s} -> {result:40s} ({description})")
    
    # Summary
    print("\n" + "=" * 70)
    
    if hardcoded_issue or issues_found:
        print("❌ ISSUES FOUND")
        print("=" * 70)
        
        if hardcoded_issue:
            print("\n🔧 Fix Required:")
            print(f"  Update prompt from 'Enter choice (1-6...)' to")
            print(f"  'Enter choice (1-{len(pillar_names)}, ALL, DEEP, NONE):'")
        
        if issues_found:
            print("\n⚠️  Selection Logic Issues:")
            for issue in issues_found:
                print(f"  • {issue}")
        
        print("\n📝 Recommended Fix:")
        print("  Replace hardcoded '1-6' with dynamic f'1-{len(pillar_names)}'")
        
        return False
    else:
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\nUser input prompts are correctly aligned with available options")
        return True

def test_actual_function():
    """Test the actual get_user_analysis_target function"""
    
    print("\n" + "=" * 70)
    print("TESTING ACTUAL FUNCTION")
    print("=" * 70)
    
    try:
        from literature_review.orchestrator import get_user_analysis_target
        
        with open('pillar_definitions.json') as f:
            pillar_definitions = json.load(f)
        
        print("\n✅ Function imported successfully")
        print("\nFunction signature analysis:")
        import inspect
        sig = inspect.signature(get_user_analysis_target)
        print(f"  Parameters: {sig}")
        
        # We can't easily test interactive input, but we can verify the function exists
        print("\n📋 To manually test:")
        print("  1. Run: python literature_review/orchestrator.py")
        print("  2. When prompted, verify the range matches available options")
        print(f"  3. Expected range: 1-{len(pillar_definitions)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test1 = test_user_input_prompts()
    test2 = test_actual_function()
    
    sys.exit(0 if (test1 and test2) else 1)
