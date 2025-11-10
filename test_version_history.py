#!/usr/bin/env python3
"""
Test script for version history I/O functions
"""
import json
import sys
from datetime import datetime

# Import the functions we need to test
sys.path.insert(0, '/home/runner/work/Literature-Review/Literature-Review')
from Judge import (
    load_version_history, 
    extract_pending_claims_from_history,
    update_claims_in_history,
    add_new_claims_to_history,
    save_version_history
)

def test_load_version_history():
    """Test loading version history"""
    print("Testing load_version_history()...")
    history = load_version_history('review_version_history.json')
    assert isinstance(history, dict), "History should be a dictionary"
    assert len(history) > 0, "History should not be empty"
    print(f"✅ Loaded {len(history)} files from version history")
    return history

def test_extract_pending_claims(history):
    """Test extracting pending claims"""
    print("\nTesting extract_pending_claims_from_history()...")
    claims = extract_pending_claims_from_history(history)
    assert isinstance(claims, list), "Claims should be a list"
    print(f"✅ Extracted {len(claims)} pending claims")
    
    # Check that claims have the required metadata
    if claims:
        sample_claim = claims[0]
        assert '_source_filename' in sample_claim, "Claims should have _source_filename"
        assert '_source_type' in sample_claim, "Claims should have _source_type"
        assert sample_claim['_source_type'] == 'version_history', "Source type should be version_history"
        print(f"✅ Sample claim has required metadata")
    
    return claims

def test_update_claims_in_history(history, claims):
    """Test updating claims in history"""
    print("\nTesting update_claims_in_history()...")
    
    if not claims:
        print("⚠️ No claims to test with, skipping update test")
        return history
    
    # Simulate judging the first claim
    test_claim = claims[0].copy()
    test_claim['status'] = 'approved'
    test_claim['judge_notes'] = 'Test approval'
    test_claim['judge_timestamp'] = datetime.now().isoformat()
    
    updated_history = update_claims_in_history(history, [test_claim])
    assert isinstance(updated_history, dict), "Updated history should be a dictionary"
    print(f"✅ Successfully updated claims in history")
    
    return updated_history

def test_add_new_claims_to_history(history):
    """Test adding new claims to history"""
    print("\nTesting add_new_claims_to_history()...")
    
    # Get a filename from history
    if not history:
        print("⚠️ No history to test with, skipping add claims test")
        return history
    
    filename = list(history.keys())[0]
    
    # Create a test claim
    test_claim = {
        'claim_id': 'test_claim_123',
        'pillar': 'Test Pillar',
        'sub_requirement': 'Test Sub-Requirement',
        'status': 'pending_judge_review',
        '_source_filename': filename,
        '_source_type': 'dra_appeal'
    }
    
    updated_history = add_new_claims_to_history(history, [test_claim])
    assert isinstance(updated_history, dict), "Updated history should be a dictionary"
    print(f"✅ Successfully added new claims to history")
    
    return updated_history

def main():
    print("=" * 60)
    print("Testing Version History I/O Functions")
    print("=" * 60)
    
    try:
        # Test 1: Load version history
        history = test_load_version_history()
        
        # Test 2: Extract pending claims
        claims = test_extract_pending_claims(history)
        
        # Test 3: Update claims in history
        updated_history = test_update_claims_in_history(history, claims)
        
        # Test 4: Add new claims to history
        final_history = test_add_new_claims_to_history(updated_history)
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
