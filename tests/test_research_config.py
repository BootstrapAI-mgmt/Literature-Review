"""
Tests for Research Configuration Module

Tests the ResearchConfig class and configuration loading functionality.
"""

import json
import os
import pytest
import tempfile
from pathlib import Path

from literature_review.config.research_config import (
    ResearchConfig,
    load_config,
    get_config,
    reset_config,
    is_config_loaded,
    get_research_topic_safe,
    get_short_description_safe,
    get_database_filename_safe,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_config_data():
    """Minimal valid configuration data."""
    return {
        "schema_version": "1.0.0",
        "domain": {
            "id": "test-domain",
            "name": "Test Research Domain",
            "version": "1.0.0",
            "created_at": "2025-12-10"
        },
        "research_topic": {
            "primary": "This is the primary research question for testing.",
            "short_description": "test domain focus"
        },
        "prompt_context": {
            "researcher_role": "Test researcher role",
            "domain_focus": "test focus",
            "example_domains": ["Domain A", "Domain B"],
            "example_subdomains": ["Sub A", "Sub B"],
            "example_keywords": ["Keyword A", "Keyword B"]
        },
        "vocabulary": {
            "primary_keywords": ["test", "keywords"],
            "secondary_keywords": ["more", "terms"]
        },
        "file_naming": {
            "database": "{domain_id}-research_database.csv",
            "non_journal": "{domain_id}-non_journal.csv"
        },
        "pillar_definitions_file": "pillar_definitions.json",
        "search_context": {
            "default_query_prefix": "test",
            "ai_pillar_context": "test context"
        },
        "proof_chain": {
            "ultimate_goal": "Test goal",
            "failure_message": "Test failure"
        }
    }


@pytest.fixture
def valid_pillar_data():
    """Minimal valid pillar definitions."""
    return {
        "Framework_Overview": {
            "vision": "Test vision",
            "core_principles": ["Principle 1"]
        },
        "Pillar 1: Test Pillar": {
            "description": "Test pillar description",
            "keywords": ["test"],
            "requirements": {
                "REQ-1.1: Test Requirement": [
                    "Sub-1.1.1: Test sub-requirement"
                ]
            }
        }
    }


@pytest.fixture
def temp_config_dir(valid_config_data, valid_pillar_data):
    """Create a temporary directory with valid config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "research_config.json"
        pillar_path = Path(tmpdir) / "pillar_definitions.json"
        
        with open(config_path, 'w') as f:
            json.dump(valid_config_data, f)
        
        with open(pillar_path, 'w') as f:
            json.dump(valid_pillar_data, f)
        
        yield tmpdir


@pytest.fixture(autouse=True)
def reset_config_state():
    """Reset config state before and after each test."""
    reset_config()
    yield
    reset_config()


# =============================================================================
# UNIT TESTS: ResearchConfig.load()
# =============================================================================

class TestResearchConfigLoad:
    """Tests for ResearchConfig.load() method."""
    
    def test_load_valid_config(self, temp_config_dir):
        """Test loading a valid configuration file."""
        config_path = Path(temp_config_dir) / "research_config.json"
        config = ResearchConfig.load(str(config_path))
        
        assert config.domain_id == "test-domain"
        assert config.domain_name == "Test Research Domain"
        assert config.research_topic == "This is the primary research question for testing."
        assert config.short_description == "test domain focus"
    
    def test_load_generates_database_filename(self, temp_config_dir):
        """Test that database filename is generated from template."""
        config_path = Path(temp_config_dir) / "research_config.json"
        config = ResearchConfig.load(str(config_path))
        
        assert config.database_filename == "test-domain-research_database.csv"
    
    def test_load_nonexistent_file_raises(self):
        """Test that loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ResearchConfig.load("/nonexistent/path/config.json")
    
    def test_load_invalid_json_raises(self, temp_config_dir):
        """Test that loading invalid JSON raises error."""
        bad_config = Path(temp_config_dir) / "bad_config.json"
        with open(bad_config, 'w') as f:
            f.write("{ invalid json }")
        
        with pytest.raises(json.JSONDecodeError):
            ResearchConfig.load(str(bad_config))
    
    def test_load_missing_required_field_raises(self, temp_config_dir, valid_config_data):
        """Test that missing required field raises KeyError."""
        del valid_config_data['domain']
        
        bad_config = Path(temp_config_dir) / "incomplete_config.json"
        with open(bad_config, 'w') as f:
            json.dump(valid_config_data, f)
        
        with pytest.raises(KeyError):
            ResearchConfig.load(str(bad_config))
    
    def test_load_pillar_definitions(self, temp_config_dir, valid_pillar_data):
        """Test that pillar definitions are loaded."""
        config_path = Path(temp_config_dir) / "research_config.json"
        config = ResearchConfig.load(str(config_path))
        
        assert "Framework_Overview" in config.pillar_definitions
        assert config.pillar_definitions["Framework_Overview"]["vision"] == "Test vision"


# =============================================================================
# UNIT TESTS: ResearchConfig methods
# =============================================================================

class TestResearchConfigMethods:
    """Tests for ResearchConfig instance methods."""
    
    def test_get_pillar_definitions_str(self, temp_config_dir):
        """Test pillar definitions string formatting."""
        config_path = Path(temp_config_dir) / "research_config.json"
        config = ResearchConfig.load(str(config_path))
        
        pillar_str = config.get_pillar_definitions_str()
        assert isinstance(pillar_str, str)
        assert "Framework_Overview" in pillar_str
        assert "Test vision" in pillar_str
    
    def test_get_example_domains_str(self, temp_config_dir):
        """Test example domains string formatting."""
        config_path = Path(temp_config_dir) / "research_config.json"
        config = ResearchConfig.load(str(config_path))
        
        domains_str = config.get_example_domains_str()
        assert '"Domain A"' in domains_str
        assert '"Domain B"' in domains_str


# =============================================================================
# UNIT TESTS: Global Config Management
# =============================================================================

class TestGlobalConfigManagement:
    """Tests for load_config(), get_config(), reset_config()."""
    
    def test_load_config_caches_instance(self, temp_config_dir):
        """Test that load_config caches the configuration."""
        config_path = Path(temp_config_dir) / "research_config.json"
        
        config1 = load_config(str(config_path))
        config2 = get_config()
        
        assert config1 is config2
    
    def test_get_config_before_load_raises(self):
        """Test that get_config before load raises RuntimeError."""
        with pytest.raises(RuntimeError) as exc_info:
            get_config()
        
        assert "not loaded" in str(exc_info.value)
    
    def test_is_config_loaded(self, temp_config_dir):
        """Test is_config_loaded function."""
        assert is_config_loaded() is False
        
        config_path = Path(temp_config_dir) / "research_config.json"
        load_config(str(config_path))
        
        assert is_config_loaded() is True
    
    def test_reset_config(self, temp_config_dir):
        """Test that reset_config clears the cached configuration."""
        config_path = Path(temp_config_dir) / "research_config.json"
        load_config(str(config_path))
        
        assert is_config_loaded() is True
        
        reset_config()
        
        assert is_config_loaded() is False


# =============================================================================
# UNIT TESTS: Legacy Fallback Helpers
# =============================================================================

class TestLegacyFallbacks:
    """Tests for backward-compatible fallback functions."""
    
    def test_get_research_topic_safe_with_config(self, temp_config_dir):
        """Test fallback returns config value when loaded."""
        config_path = Path(temp_config_dir) / "research_config.json"
        load_config(str(config_path))
        
        topic = get_research_topic_safe()
        assert topic == "This is the primary research question for testing."
    
    def test_get_research_topic_safe_without_config(self):
        """Test fallback returns legacy value with warning when not loaded."""
        with pytest.warns(DeprecationWarning):
            topic = get_research_topic_safe()
        
        assert "brain functions" in topic.lower() or "neuromorphic" in topic.lower()
    
    def test_get_database_filename_safe_without_config(self):
        """Test database filename fallback."""
        with pytest.warns(DeprecationWarning):
            filename = get_database_filename_safe()
        
        assert filename == "neuromorphic-research_database.csv"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests with real config files."""
    
    def test_load_root_research_config(self):
        """Test loading the actual research_config.json from repo root."""
        root_config = Path(__file__).parent.parent.parent / "research_config.json"
        
        if not root_config.exists():
            pytest.skip("Root research_config.json not found")
        
        config = ResearchConfig.load(str(root_config))
        
        assert config.domain_id == "neuromorphic-computing"
        assert "neuromorphic" in config.research_topic.lower()
        assert len(config.pillar_definitions) > 0
    
    def test_load_domain_config(self):
        """Test loading a domain-specific config."""
        domain_config = (
            Path(__file__).parent.parent.parent / 
            "domains" / "neuromorphic-computing" / "research_config.json"
        )
        
        if not domain_config.exists():
            pytest.skip("Domain config not found")
        
        config = ResearchConfig.load(str(domain_config))
        
        assert config.domain_id == "neuromorphic-computing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
