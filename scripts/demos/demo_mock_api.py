#!/usr/bin/env python3
"""
Mock API Interaction Demo

This demo shows how to test API-dependent code using mocks, allowing you to:
- Test without consuming API quota
- Test error handling and edge cases
- Develop and debug without network connectivity

Run: python demos/demo_mock_api.py
"""

import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from literature_review.analysis.judge import (
    build_judge_prompt,
    validate_judge_response
)
from literature_review.utils.api_manager import APIManager


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_mock_approved_verdict():
    """Demonstrate mocking an approved verdict from the API."""
    print_section("MOCK APPROVED VERDICT")
    
    print("\nScenario: Judge approves a claim")
    print()
    
    # Create a test claim
    claim = {
        "claim_id": "demo_001",
        "pillar": "Pillar 1: Biological Stimulus-Response",
        "sub_requirement": "Sub-1.1.1: Conclusive model of sensory transduction",
        "evidence_chunk": "The paper describes how DVS cameras transduce light into spikes...",
        "claim_summary": "DVS cameras provide sensory transduction model"
    }
    
    # Build the prompt (real function)
    prompt = build_judge_prompt(claim, "Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes")
    
    print(f"Claim ID: {claim['claim_id']}")
    print(f"Evidence: {claim['evidence_chunk'][:50]}...")
    print()
    
    # Create mock API response (approved)
    mock_response_text = json.dumps({
        "verdict": "approved",
        "judge_notes": "Evidence clearly demonstrates sensory transduction through DVS camera mechanism."
    })
    
    print("Mock API Response:")
    print(f"  {mock_response_text}")
    print()
    
    # Parse JSON and validate (real function)
    mock_response_dict = json.loads(mock_response_text)
    result = validate_judge_response(mock_response_dict)
    
    if result:
        print("Parsed Result:")
        print(f"  Verdict: {result['verdict']}")
        print(f"  Notes: {result['judge_notes']}")
        print()
        print("✅ No actual API call made - quota preserved!")
    else:
        print("❌ Validation failed!")


def demo_mock_rejected_verdict():
    """Demonstrate mocking a rejected verdict."""
    print_section("MOCK REJECTED VERDICT")
    
    print("\nScenario: Judge rejects a claim")
    print()
    
    claim = {
        "claim_id": "demo_002",
        "pillar": "Pillar 2: AI Stimulus-Response",
        "sub_requirement": "Sub-2.1.1: Event-based sensor integration",
        "evidence_chunk": "The paper mentions sensors but provides no integration details...",
        "claim_summary": "Paper discusses sensors"
    }
    
    print(f"Claim ID: {claim['claim_id']}")
    print(f"Evidence: {claim['evidence_chunk'][:50]}...")
    print()
    
    # Mock rejected response
    mock_response_text = json.dumps({
        "verdict": "rejected",
        "judge_notes": "Rejected. Evidence is too vague and does not demonstrate actual integration with SNNs."
    })
    
    print("Mock API Response:")
    print(f"  {mock_response_text}")
    print()
    
    # Parse JSON and validate (real function)
    mock_response_dict = json.loads(mock_response_text)
    result = validate_judge_response(mock_response_dict)
    
    if result:
        print("Parsed Result:")
        print(f"  Verdict: {result['verdict']}")
        print(f"  Notes: {result['judge_notes']}")
        print()
        print("✅ No actual API call made - quota preserved!")
    else:
        print("❌ Validation failed!")


def demo_mock_api_error():
    """Demonstrate mocking API errors."""
    print_section("MOCK API ERROR HANDLING")
    
    print("\nScenario: API returns invalid JSON")
    print()
    
    # Mock invalid response
    invalid_responses = [
        ("Empty string", ""),
        ("Invalid JSON", "This is not JSON"),
        ("Missing verdict", json.dumps({"judge_notes": "Notes but no verdict"})),
        ("Invalid verdict value", json.dumps({"verdict": "maybe", "judge_notes": "Unsure"})),
    ]
    
    for description, response_text in invalid_responses:
        print(f"Test: {description}")
        print(f"  Response: '{response_text[:50]}...'")
        
        try:
            mock_response_dict = json.loads(response_text) if response_text else {}
            result = validate_judge_response(mock_response_dict)
        except json.JSONDecodeError:
            result = None
        
        status = "✅ Handled correctly" if result is None else "❌ Should return None"
        print(f"  Result: {result}")
        print(f"  {status}")
        print()


def demo_mock_api_manager_caching():
    """Demonstrate mocking APIManager caching behavior."""
    print_section("MOCK API MANAGER CACHING")
    
    print("\nScenario: Testing cache prevents duplicate API calls")
    print()
    
    with patch('literature_review.utils.api_manager.genai.GenerativeModel') as mock_generative_model:
        # Setup mock
        mock_model_instance = MagicMock()
        mock_generative_model.return_value = mock_model_instance
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "verdict": "approved",
            "judge_notes": "Test response"
        })
        mock_model_instance.generate_content.return_value = mock_response
        
        # Create APIManager (will use mocked client)
        print("Creating APIManager with mocked Gemini client...")
        
        with patch('literature_review.utils.api_manager.load_dotenv'):
            # Mock os.getenv for GEMINI_API_KEY
            with patch('os.getenv', return_value='mock_api_key'):
                manager = APIManager()
        
        print("✅ APIManager created (no real API connection)")
        print()
        
        # Make first call
        print("First API call (with cache enabled)...")
        result1 = manager.cached_api_call("test prompt", use_cache=True, is_json=True)
        call_count_1 = mock_model_instance.generate_content.call_count
        print(f"  Result: {result1}")
        print(f"  API calls made: {call_count_1}")
        print()
        
        # Make second call with same prompt
        print("Second API call (same prompt, cache enabled)...")
        result2 = manager.cached_api_call("test prompt", use_cache=True, is_json=True)
        call_count_2 = mock_model_instance.generate_content.call_count
        print(f"  Result: {result2}")
        print(f"  API calls made: {call_count_2}")
        print()
        
        if call_count_2 == call_count_1:
            print("✅ Cache working! Second call didn't hit API")
        else:
            print("❌ Cache not working - both calls hit API")
        
        # Make third call with different prompt
        print("Third API call (different prompt)...")
        result3 = manager.cached_api_call("different prompt", use_cache=True, is_json=True)
        call_count_3 = mock_model_instance.generate_content.call_count
        print(f"  Result: {result3}")
        print(f"  API calls made: {call_count_3}")
        print()
        
        if call_count_3 == call_count_1 + 1:
            print("✅ New prompt triggered API call as expected")
        else:
            print("❌ Unexpected call count")


def demo_prompt_building():
    """Demonstrate prompt building without API calls."""
    print_section("PROMPT BUILDING (No API)")
    
    print("\nBuilding judge prompts without API calls:")
    print()
    
    claims = [
        {
            "claim_id": "test_001",
            "pillar": "Pillar 1",
            "sub_requirement": "Sub-1.1.1",
            "evidence_chunk": "Short evidence",
            "claim_summary": "Test claim 1"
        },
        {
            "claim_id": "test_002",
            "pillar": "Pillar 2",
            "sub_requirement": "Sub-2.1.1",
            "evidence_chunk": "Different evidence with more detail about the mechanism",
            "claim_summary": "Test claim 2"
        },
    ]
    
    for claim in claims:
        definition = f"{claim['sub_requirement']}: Full requirement definition here"
        prompt = build_judge_prompt(claim, definition)
        
        print(f"Claim ID: {claim['claim_id']}")
        print(f"  Prompt length: {len(prompt)} characters")
        print(f"  Contains claim ID: {'✅' if claim['claim_id'] in prompt else '❌'}")
        print(f"  Contains evidence: {'✅' if claim['evidence_chunk'] in prompt else '❌'}")
        print(f"  Contains definition: {'✅' if definition in prompt else '❌'}")
        print()


def main():
    """Run all mock API demos."""
    print("\n" + "█" * 70)
    print("  MOCK API INTERACTION DEMO")
    print("█" * 70)
    
    print("\n⚠️  NOTE: All demos use mocks - NO real API calls are made!")
    print("         This allows testing without consuming API quota.")
    
    # Run demos
    demo_mock_approved_verdict()
    demo_mock_rejected_verdict()
    demo_mock_api_error()
    demo_mock_api_manager_caching()
    demo_prompt_building()
    
    # Summary
    print("\n" + "=" * 70)
    print("  Demo complete!")
    print("  ")
    print("  Key Takeaways:")
    print("  - Mocks allow testing without real API calls")
    print("  - Can test error conditions safely")
    print("  - Cache behavior can be verified")
    print("  - Preserves API quota for actual work")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
