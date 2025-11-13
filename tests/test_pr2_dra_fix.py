#!/usr/bin/env python3
"""
Test PR #2: Fix DRA prompting to align with Judge validation criteria

This test validates that Task Card #1 acceptance criteria are met:
- DRA loads pillar_definitions_enhanced.json
- DRA prompt includes full sub-requirement definition as "THE LAW"
- DRA prompt includes Judge's rejection reason
- DRA prompt instructs AI to address specific rejection points
"""

import sys
import os
import json
import pytest
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from literature_review.analysis.requirements import (
    run_analysis as run_dra_analysis,
    TextExtractor,
    load_pillar_definitions,
    find_sub_requirement_definition,
    build_dra_prompt,
    chunk_text_with_page_tracking,
    aggregate_chunk_results,
    DEFINITIONS_FILE
)


class TestTaskCard1AcceptanceCriteria:
    """Test acceptance criteria from Task Card #1"""
    
    def test_definitions_file_exists(self):
        """Verify pillar_definitions_enhanced.json exists"""
        assert os.path.exists(DEFINITIONS_FILE), f"{DEFINITIONS_FILE} not found in workspace"
    
    def test_definitions_file_is_valid_json(self):
        """Verify definitions file is valid JSON"""
        with open(DEFINITIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert isinstance(data, dict), "Definitions file should be a dictionary"
        assert len(data) > 0, "Definitions file should not be empty"
    
    def test_load_pillar_definitions_success(self):
        """✅ DRA loads pillar_definitions_enhanced.json"""
        definitions = load_pillar_definitions(DEFINITIONS_FILE)
        
        assert definitions is not None
        assert isinstance(definitions, dict)
        assert len(definitions) > 0
        
        # Should have 7 pillars (plus Framework_Overview)
        assert len(definitions) >= 7, f"Expected at least 7 pillars, got {len(definitions)}"
        
        # Check structure - only actual Pillars (numbered) should have requirements
        for pillar_name, pillar_data in definitions.items():
            # Skip meta sections that don't represent actual pillars
            if not pillar_name.startswith('Pillar '):
                continue
            assert 'requirements' in pillar_data, f"Pillar {pillar_name} missing 'requirements'"
            assert isinstance(pillar_data['requirements'], dict)
    
    def test_load_pillar_definitions_handles_missing_file(self):
        """Test error handling when file doesn't exist"""
        definitions = load_pillar_definitions('nonexistent_file.json')
        
        assert definitions == {}  # Should return empty dict, not crash
    
    def test_load_pillar_definitions_handles_invalid_json(self, tmp_path):
        """Test error handling for malformed JSON"""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("This is not JSON!")
        
        definitions = load_pillar_definitions(str(bad_file))
        
        assert definitions == {}  # Should return empty dict, not crash


class TestDefinitionLookup:
    """Test find_sub_requirement_definition function"""
    
    @pytest.fixture
    def pillar_definitions(self):
        """Load actual pillar definitions"""
        return load_pillar_definitions(DEFINITIONS_FILE)
    
    def test_find_existing_sub_requirement(self, pillar_definitions):
        """Test finding a valid sub-requirement definition"""
        # Test with Pillar 1 (Biological Stimulus-Response) - use actual name from file
        definition = find_sub_requirement_definition(
            pillar_definitions,
            "Pillar 1: Biological Stimulus-Response",
            "Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes"
        )
        
        assert definition is not None
        assert len(definition) > 0
        assert "Sub-1.1.1" in definition
    
    def test_find_sub_requirement_with_partial_match(self, pillar_definitions):
        """Test finding sub-requirement with prefix matching"""
        # Should work with just the key prefix
        definition = find_sub_requirement_definition(
            pillar_definitions,
            "Pillar 2",
            "Sub-2.1.1"
        )
        
        assert definition is not None
        assert "Sub-2.1.1" in definition
    
    def test_find_sub_requirement_returns_none_for_invalid(self, pillar_definitions):
        """Test that invalid sub-requirement returns None"""
        definition = find_sub_requirement_definition(
            pillar_definitions,
            "Pillar 999",
            "Sub-999.999.999"
        )
        
        assert definition is None
    
    def test_find_multiple_pillars(self, pillar_definitions):
        """Test finding definitions across multiple pillars"""
        test_cases = [
            ("Pillar 1", "Sub-1.1.1"),
            ("Pillar 2", "Sub-2.1.1"),
            ("Pillar 3", "Sub-3.1.1"),
            ("Pillar 4", "Sub-4.1.1"),
        ]
        
        for pillar_key, sub_req_key in test_cases:
            definition = find_sub_requirement_definition(
                pillar_definitions, pillar_key, sub_req_key
            )
            assert definition is not None, f"Failed to find {sub_req_key} in {pillar_key}"
            assert sub_req_key in definition


class TestPromptStructure:
    """Test that build_dra_prompt includes all required elements"""
    
    @pytest.fixture
    def pillar_definitions(self):
        """Load actual pillar definitions"""
        return load_pillar_definitions(DEFINITIONS_FILE)
    
    @pytest.fixture
    def sample_rejected_claims(self):
        """Sample rejected claims for testing"""
        return [
            {
                "claim_id": "test_001",
                "pillar": "Pillar 1: Biological Stimulus-Response",
                "sub_requirement": "Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes",
                "judge_notes": "Rejected. Evidence is too vague and does not demonstrate sensory transduction.",
                "evidence_chunk": "The paper mentions DVS cameras.",
                "status": "rejected_by_judge"
            },
            {
                "claim_id": "test_002",
                "pillar": "Pillar 2: AI Stimulus-Response (Bridge)",
                "sub_requirement": "Sub-2.1.1: Event-based sensor integration with SNNs",
                "judge_notes": "Rejected. No integration details provided.",
                "evidence_chunk": "Sensors are used in the system.",
                "status": "rejected_by_judge"
            }
        ]
    
    def test_prompt_includes_full_definition_as_law(self, pillar_definitions, sample_rejected_claims):
        """✅ DRA prompt includes full sub-requirement definition as 'THE LAW'"""
        full_text = "This is a sample paper text for testing."
        prompt = build_dra_prompt(sample_rejected_claims, full_text, pillar_definitions)
        
        # Should include "THE LAW" label
        assert 'THE LAW' in prompt, "Prompt should label definition as 'THE LAW'"
        assert 'FULL REQUIREMENT DEFINITION' in prompt
        
        # Should include actual definition text, not just the key
        # For claim 1, should have more than just "Sub-1.1.1"
        assert "Sub-1.1.1" in prompt
        # Definition text should be longer than the key
        assert len(prompt) > 500  # Prompt should be substantial
    
    def test_prompt_includes_judge_rejection_reason(self, pillar_definitions, sample_rejected_claims):
        """✅ DRA prompt includes Judge's rejection reason"""
        full_text = "This is a sample paper text for testing."
        prompt = build_dra_prompt(sample_rejected_claims, full_text, pillar_definitions)
        
        # Should include both rejection reasons
        assert "too vague" in prompt.lower() or "vague" in prompt
        assert "No integration details" in prompt
        
        # Should be clearly labeled
        assert "Judge's Rejection Reason" in prompt or "Judge's Reason" in prompt
    
    def test_prompt_includes_critical_instructions(self, pillar_definitions, sample_rejected_claims):
        """✅ DRA prompt instructs AI to address specific rejection points"""
        full_text = "This is a sample paper text for testing."
        prompt = build_dra_prompt(sample_rejected_claims, full_text, pillar_definitions)
        
        # Should have CRITICAL INSTRUCTIONS section
        assert "CRITICAL INSTRUCTIONS" in prompt
        
        # Should instruct to validate against FULL definition
        assert "FULL definition" in prompt or "FULL REQUIREMENT" in prompt
        
        # Should instruct to address Judge's reasons
        assert "address" in prompt.lower() and "rejection" in prompt.lower()
        
        # Should emphasize exact quotes
        assert "EXACT" in prompt or "exact" in prompt
        
        # Should mention high confidence threshold
        assert "HIGH confidence" in prompt or "confidence" in prompt
    
    def test_prompt_includes_all_rejected_claims(self, pillar_definitions, sample_rejected_claims):
        """Prompt should include all rejected claims"""
        full_text = "This is a sample paper text for testing."
        prompt = build_dra_prompt(sample_rejected_claims, full_text, pillar_definitions)
        
        # Should include both claim IDs
        assert "test_001" in prompt
        assert "test_002" in prompt
        
        # Should include both pillars
        assert "Pillar 1" in prompt
        assert "Pillar 2" in prompt
    
    def test_prompt_handles_missing_definition_gracefully(self, pillar_definitions):
        """Test prompt handles missing definition without crashing"""
        claims_with_invalid = [{
            "claim_id": "test_999",
            "pillar": "Pillar 999",
            "sub_requirement": "Sub-999.999.999: Nonexistent requirement",
            "judge_notes": "Rejected.",
            "evidence_chunk": "Test.",
            "status": "rejected_by_judge"
        }]
        
        full_text = "Sample text."
        prompt = build_dra_prompt(claims_with_invalid, full_text, pillar_definitions)
        
        # Should still generate prompt
        assert len(prompt) > 0
        
        # Should indicate definition not found
        assert "NOT FOUND" in prompt
    
    def test_prompt_structure_matches_expected_format(self, pillar_definitions, sample_rejected_claims):
        """Verify prompt has expected structure"""
        full_text = "This is a sample paper text for testing."
        prompt = build_dra_prompt(sample_rejected_claims, full_text, pillar_definitions)
        
        # Should have main sections
        assert "CRITICAL INSTRUCTIONS" in prompt
        assert "LIST OF REJECTED CLAIMS" in prompt
        assert "YOUR TASK" in prompt
        assert "Output Format" in prompt
        assert "FULL PAPER TEXT" in prompt
        
        # Should specify JSON output format
        assert "JSON" in prompt
        assert "new_claims_to_rejudge" in prompt


class TestPromptContentQuality:
    """Test that prompt content quality meets requirements"""
    
    @pytest.fixture
    def pillar_definitions(self):
        return load_pillar_definitions(DEFINITIONS_FILE)
    
    def test_prompt_emphasizes_alignment_with_judge(self, pillar_definitions):
        """Prompt should emphasize alignment with Judge's validation criteria"""
        claims = [{
            "claim_id": "test_001",
            "pillar": "Pillar 1: Biological Stimulus-Response",
            "sub_requirement": "Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes",
            "judge_notes": "Rejected. Too vague.",
            "evidence_chunk": "DVS cameras.",
            "status": "rejected_by_judge"
        }]
        
        full_text = "Sample paper."
        prompt = build_dra_prompt(claims, full_text, pillar_definitions)
        
        # Should mention Judge validation
        assert "Judge will validate" in prompt or "Judge will verify" in prompt
        
        # Should emphasize the EXACT criteria
        assert "EXACT" in prompt
    
    def test_prompt_discourages_weak_submissions(self, pillar_definitions):
        """Prompt should discourage submitting weak evidence"""
        claims = [{
            "claim_id": "test_001",
            "pillar": "Pillar 1: Biological Stimulus-Response",
            "sub_requirement": "Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes",
            "judge_notes": "Rejected. Too vague.",
            "evidence_chunk": "DVS cameras.",
            "status": "rejected_by_judge"
        }]
        
        full_text = "Sample paper."
        prompt = build_dra_prompt(claims, full_text, pillar_definitions)
        
        # Should tell AI when NOT to submit
        assert "DO NOT submit" in prompt or "cannot find" in prompt.lower()
        
        # Should mention confidence threshold
        assert "0.9" in prompt or "HIGH confidence" in prompt


class TestIntegrationWithRealData:
    """Integration tests with actual pillar definitions"""
    
    def test_loads_all_seven_pillars(self):
        """Verify all 7 pillars can be loaded"""
        definitions = load_pillar_definitions(DEFINITIONS_FILE)
        
        expected_pillars = [
            "Pillar 1: Sensory Encoding",
            "Pillar 2: AI Stimulus-Response",
            "Pillar 3: Plasticity & Learning",
            "Pillar 4: Memory & Consolidation",
            "Pillar 5: Skill Automatization",
            "Pillar 6: System Integration & Orchestration",
            "Pillar 7: Efficient Computing"
        ]
        
        pillar_names = list(definitions.keys())
        
        # Should have all 7 pillars (may have slight name variations)
        assert len(pillar_names) >= 7, f"Expected 7 pillars, got {len(pillar_names)}"
        
        # Check that major pillars exist
        for expected in ["Pillar 1", "Pillar 2", "Pillar 3", "Pillar 4", "Pillar 5", "Pillar 6", "Pillar 7"]:
            found = any(expected in name for name in pillar_names)
            assert found, f"Could not find pillar matching '{expected}'"
    
    def test_end_to_end_prompt_generation(self):
        """Test complete flow from loading definitions to generating prompt"""
        # 1. Load definitions
        definitions = load_pillar_definitions(DEFINITIONS_FILE)
        assert len(definitions) > 0
        
        # 2. Create realistic rejected claim (use actual pillar name from file)
        rejected_claim = {
            "claim_id": "claim_123",
            "pillar": "Pillar 1: Biological Stimulus-Response",
            "sub_requirement": "Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes",
            "judge_notes": "Rejected. Evidence does not demonstrate conclusive model of sensory transduction.",
            "evidence_chunk": "The paper uses DVS cameras for visual input.",
            "status": "rejected_by_judge",
            "filename": "test_paper.pdf"
        }
        
        # 3. Look up definition
        definition = find_sub_requirement_definition(
            definitions,
            rejected_claim['pillar'],
            rejected_claim['sub_requirement']
        )
        assert definition is not None
        assert len(definition) > 50  # Should be substantial
        
        # 4. Build prompt
        full_text = "This is a sample research paper about neuromorphic systems..."
        prompt = build_dra_prompt([rejected_claim], full_text, definitions)
        
        # 5. Verify prompt quality
        assert "THE LAW" in prompt
        assert definition in prompt  # Full definition should be in prompt
        assert rejected_claim['judge_notes'] in prompt
        assert "claim_123" in prompt
        assert "CRITICAL INSTRUCTIONS" in prompt
        assert full_text in prompt


def test_pr2_acceptance_summary():
    """
    Summary test that verifies all Task Card #1 acceptance criteria are met
    """
    print("\n" + "="*70)
    print("  PR #2 ACCEPTANCE CRITERIA VERIFICATION")
    print("="*70)
    
    # Load definitions
    definitions = load_pillar_definitions(DEFINITIONS_FILE)
    
    # Create test claim
    test_claim = {
        "claim_id": "test_final",
        "pillar": "Pillar 1: Biological Stimulus-Response",
        "sub_requirement": "Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes",
        "judge_notes": "Rejected. Evidence is too vague.",
        "evidence_chunk": "Uses cameras.",
        "status": "rejected_by_judge"
    }
    
    # Generate prompt
    prompt = build_dra_prompt([test_claim], "Sample paper text.", definitions)
    
    # Check all criteria
    criteria = {
        "✅ DRA loads pillar_definitions_enhanced.json": len(definitions) > 0,
        "✅ Prompt includes full definition as 'THE LAW'": 'THE LAW' in prompt and 'FULL REQUIREMENT DEFINITION' in prompt,
        "✅ Prompt includes Judge's rejection reason": test_claim['judge_notes'] in prompt,
        "✅ Prompt instructs AI to address rejection": 'CRITICAL INSTRUCTIONS' in prompt and 'address' in prompt.lower(),
        "✅ Error handling for missing definitions": load_pillar_definitions('fake.json') == {},
        "✅ Definition lookup works": find_sub_requirement_definition(definitions, "Pillar 1", "Sub-1.1.1") is not None,
    }
    
    print("\nAcceptance Criteria Results:")
    all_passed = True
    for criterion, passed in criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {criterion}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("  ✅ ALL ACCEPTANCE CRITERIA MET - PR #2 READY FOR MERGE")
    else:
        print("  ❌ SOME CRITERIA FAILED - REQUIRES FIXES")
    print("="*70 + "\n")
    
    assert all_passed, "Not all acceptance criteria were met"


if __name__ == "__main__":
    # Run acceptance summary
    test_pr2_acceptance_summary()
    
    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])
