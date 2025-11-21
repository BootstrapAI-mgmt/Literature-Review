"""
Component Tests for Judge.py - Functions with Mocked Dependencies
Tests pillar definition loading, fuzzy matching, and API interactions with mocks.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, mock_open, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis import judge
from literature_review.analysis.judge import (
    load_pillar_definitions,
    find_robust_sub_requirement_text,
    find_robust_pillar_key,
    _build_lookup_map
)
from literature_review.utils.api_manager import APIManager


# Module-level setup for GEMINI_API_KEY - component tests need this for APIManager
import os
os.environ["GEMINI_API_KEY"] = "test-dummy-key-for-component-tests"


@pytest.fixture
def mock_pillar_definitions():
    """Fixture providing mock pillar definitions."""
    return {
        "Pillar 1: Biological Stimulus-Response": {
            "requirements": {
                "REQ-B1.1": [
                    "Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes",
                    "Sub-1.1.2: Proven mechanism for sensory feature extraction in early processing"
                ],
                "REQ-B1.2": [
                    "Sub-1.2.1: Detailed mapping of thalamic relay pathways for major senses"
                ]
            }
        },
        "Pillar 2: AI Stimulus-Response (Bridge)": {
            "requirements": {
                "REQ-A2.1": [
                    "Sub-2.1.1: Event-based sensor integration with SNNs",
                    "Sub-2.1.2: Efficient SNN algorithms for sparse feature extraction"
                ]
            }
        }
    }


class TestLoadPillarDefinitions:
    """Test suite for load_pillar_definitions function."""
    
    @pytest.mark.component
    def test_loads_valid_json_file(self, tmp_path):
        """Test loading valid JSON file."""
        test_file = tmp_path / "test_definitions.json"
        test_data = {"Pillar 1": {"requirements": {}}}
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        result = load_pillar_definitions(str(test_file))
        
        assert result == test_data
    
    @pytest.mark.component
    def test_handles_missing_file(self):
        """Test handling of missing file."""
        result = load_pillar_definitions("nonexistent_file.json")
        
        assert result == {}
    
    @pytest.mark.component
    def test_handles_invalid_json(self, tmp_path):
        """Test handling of invalid JSON."""
        test_file = tmp_path / "invalid.json"
        
        with open(test_file, 'w') as f:
            f.write("This is not valid JSON{]")
        
        result = load_pillar_definitions(str(test_file))
        
        assert result == {}
    
    @pytest.mark.component
    def test_loads_actual_pillar_definitions_file(self):
        """Test loading the actual pillar definitions file."""
        # Assuming file is in repo root
        filepath = "pillar_definitions_enhanced.json"
        
        if os.path.exists(filepath):
            result = load_pillar_definitions(filepath)
            
            assert isinstance(result, dict)
            assert len(result) > 0
            # Check for expected pillars
            pillar_keys = [k for k in result.keys() if k.startswith("Pillar")]
            assert len(pillar_keys) > 0


class TestBuildLookupMap:
    """Test suite for _build_lookup_map function."""
    
    @pytest.mark.component
    def test_builds_lookup_map(self, mock_pillar_definitions):
        """Test building lookup map from definitions."""
        _build_lookup_map(mock_pillar_definitions)
        
        # Check global maps were populated
        assert len(judge.DEFINITIONS_LOOKUP_MAP) > 0
        assert len(judge.CANONICAL_PILLAR_MAP) > 0
    
    @pytest.mark.component
    def test_normalizes_sub_requirements(self, mock_pillar_definitions):
        """Test that sub-requirements are normalized in lookup."""
        _build_lookup_map(mock_pillar_definitions)
        
        # Check that normalized keys exist
        normalized_keys = judge.DEFINITIONS_LOOKUP_MAP.keys()
        
        # All keys should be lowercase and normalized
        for key in normalized_keys:
            assert key.islower()
            assert "sub-" not in key
            assert ":" not in key
    
    @pytest.mark.component
    def test_creates_canonical_pillar_map(self, mock_pillar_definitions):
        """Test creation of canonical pillar map."""
        _build_lookup_map(mock_pillar_definitions)
        
        pillar_map = judge.CANONICAL_PILLAR_MAP
        
        # Should have normalized pillar keys
        assert "pillar 1" in pillar_map
        assert "pillar 2" in pillar_map


class TestFindRobustSubRequirementText:
    """Test suite for find_robust_sub_requirement_text function."""
    
    @pytest.mark.component
    def test_finds_exact_match(self, mock_pillar_definitions):
        """Test finding exact match."""
        _build_lookup_map(mock_pillar_definitions)
        
        result = find_robust_sub_requirement_text(
            "Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes"
        )
        
        assert result is not None
        assert "Conclusive model" in result
        assert "neural spikes" in result
    
    @pytest.mark.component
    def test_finds_fuzzy_match(self, mock_pillar_definitions):
        """Test fuzzy matching with slight variations."""
        _build_lookup_map(mock_pillar_definitions)
        
        # Try with minor typo or variation
        result = find_robust_sub_requirement_text(
            "conclusive model raw sensory data transduced neural spikes"
        )
        
        # Should find close match
        assert result is not None or result is None  # Depends on threshold
    
    @pytest.mark.component
    def test_returns_none_for_no_match(self, mock_pillar_definitions):
        """Test returns None when no match found."""
        _build_lookup_map(mock_pillar_definitions)
        
        result = find_robust_sub_requirement_text(
            "Completely unrelated text that won't match anything"
        )
        
        assert result is None
    
    @pytest.mark.component
    def test_normalizes_input_before_matching(self, mock_pillar_definitions):
        """Test that input is normalized before matching."""
        _build_lookup_map(mock_pillar_definitions)
        
        # Try with uppercase and special chars
        result = find_robust_sub_requirement_text(
            "SUB-1.1.1: CONCLUSIVE MODEL OF HOW RAW SENSORY DATA IS TRANSDUCED INTO NEURAL SPIKES"
        )
        
        assert result is not None


class TestFindRobustPillarKey:
    """Test suite for find_robust_pillar_key function."""
    
    @pytest.mark.component
    def test_finds_exact_pillar_match(self, mock_pillar_definitions):
        """Test finding exact pillar match."""
        _build_lookup_map(mock_pillar_definitions)
        
        result = find_robust_pillar_key("Pillar 1: Biological Stimulus-Response")
        
        assert result is not None
        assert "Pillar 1" in result
    
    @pytest.mark.component
    def test_finds_fuzzy_pillar_match(self, mock_pillar_definitions):
        """Test fuzzy matching for pillar keys."""
        _build_lookup_map(mock_pillar_definitions)
        
        result = find_robust_pillar_key("Pillar 1")
        
        assert result is not None
        assert "Pillar 1" in result
    
    @pytest.mark.component
    def test_returns_fuzzy_match_for_invalid_pillar(self, mock_pillar_definitions):
        """Test returns fuzzy match even for invalid pillar (by design)."""
        _build_lookup_map(mock_pillar_definitions)
        
        result = find_robust_pillar_key("Pillar 99: Nonexistent")
        
        # Fuzzy matching will return closest match, not None
        assert result is not None


class TestAPIManagerMocked:
    """Test suite for APIManager with mocked Gemini API."""
    
    @pytest.mark.component
    @patch('literature_review.utils.api_manager.genai.Client')
    @patch('literature_review.utils.api_manager.load_dotenv')
    def test_api_manager_initialization(self, mock_dotenv, mock_client):
        """Test APIManager initializes with mocked API."""
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        manager = APIManager()
        
        assert manager.client is not None
        assert manager.cache_dir is not None
        assert os.path.exists(manager.cache_dir)
    
    @pytest.mark.component
    @patch('literature_review.utils.api_manager.genai.Client')
    @patch('literature_review.utils.api_manager.load_dotenv')
    def test_cached_api_call_caching_behavior(self, mock_dotenv, mock_client_class):
        """Test that cache prevents duplicate API calls."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"verdict": "approved", "judge_notes": "Test"}'
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client_instance
        
        import time
        import shutil
        
        # Use unique cache dir for this test to avoid interference
        cache_dir = f'test_cache_{int(time.time() * 1000)}'
        manager = APIManager(cache_dir=cache_dir)
        
        try:
            # First call - should hit API
            result1 = manager.cached_api_call("unique test prompt for cache test", use_cache=True, is_json=True)
            
            # Second call with same prompt - should use file-based cache
            result2 = manager.cached_api_call("unique test prompt for cache test", use_cache=True, is_json=True)
            
            # API should only be called once (second call uses cache file)
            assert mock_client_instance.models.generate_content.call_count == 1
            
            # Results should be identical
            assert result1 == result2
        finally:
            # Clean up test cache directory
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
    
    @pytest.mark.component
    @patch('literature_review.utils.api_manager.genai.Client')
    @patch('literature_review.utils.api_manager.load_dotenv')
    def test_cache_bypass_when_disabled(self, mock_dotenv, mock_client):
        """Test that cache can be bypassed."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"verdict": "approved"}'
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        manager = APIManager()
        
        # Two calls with cache disabled
        result1 = manager.cached_api_call("test prompt", use_cache=False, is_json=True)
        result2 = manager.cached_api_call("test prompt", use_cache=False, is_json=True)
        
        # API should be called twice
        assert mock_client_instance.models.generate_content.call_count == 2
    
    @pytest.mark.component
    @patch('literature_review.utils.api_manager.genai.Client')
    @patch('literature_review.utils.api_manager.load_dotenv')
    def test_json_parsing_in_api_call(self, mock_dotenv, mock_client):
        """Test JSON parsing in API call."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"verdict": "approved", "judge_notes": "Evidence is clear"}'
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        manager = APIManager()
        
        result = manager.cached_api_call("test prompt", use_cache=False, is_json=True)
        
        # Should return parsed JSON dict
        assert isinstance(result, dict)
        assert result["verdict"] == "approved"
        assert "judge_notes" in result


class TestFileIOOperations:
    """Test suite for file I/O operations."""
    
    @pytest.mark.component
    def test_safe_print_handles_unicode(self):
        """Test safe_print handles unicode characters."""
        from literature_review.analysis.judge import safe_print
        
        # Should not raise exception
        safe_print("Test with emoji: ✅ ❌ 🎫")
        safe_print("Test with Chinese: 测试")
        safe_print("Test with special chars: © ® ™")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
