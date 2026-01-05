"""
Cross-Domain Validation Tests

Validates that the pipeline performs consistently across different research domains.
These tests are parameterized to run on all registered domains.

Usage:
    # Run on default domain
    pytest tests/validation/test_cross_domain.py
    
    # Run on specific domain
    pytest tests/validation/test_cross_domain.py --domain thermophoresis
    
    # Run on all domains
    pytest tests/validation/test_cross_domain.py --all-domains
"""

import pytest
from typing import Dict, Any

from tests.validation.fixtures.domain_fixture import (
    get_domain_fixture,
    DomainTestFixture,
    list_available_domains
)


class TestDomainFixtureLoading:
    """DF-01: Verify all domain fixtures load correctly."""
    
    @pytest.mark.domain_agnostic
    def test_domain_fixture_loads(self, domain_id: str):
        """Each domain fixture should load without errors."""
        fixture = get_domain_fixture(domain_id)
        
        assert fixture.domain_id == domain_id
        assert fixture.research_config is not None
        assert fixture.baselines is not None
        assert fixture.domain_dir.exists()
    
    @pytest.mark.domain_agnostic
    def test_domain_has_pillar_definitions(self, domain_id: str):
        """Each domain should have pillar definitions."""
        fixture = get_domain_fixture(domain_id)
        
        pillars = fixture.get_pillar_definitions()
        assert pillars is not None
        assert len(pillars) > 0
    
    @pytest.mark.domain_agnostic
    def test_domain_research_config_valid(self, domain_id: str):
        """Each domain's research config should have required fields."""
        fixture = get_domain_fixture(domain_id)
        config = fixture.research_config
        
        assert config.domain_id == domain_id
        assert len(config.domain_name) > 0
        assert len(config.research_topic) > 0


class TestCrossDomainExecution:
    """DF-02: Verify tests can execute across all domains."""
    
    @pytest.mark.domain_agnostic
    def test_pillar_mapping_cross_domain(self, domain_fixture: DomainTestFixture):
        """
        Pillar mapping should work for any domain's pillar definitions.
        
        Note: This is a structural test, not an accuracy test.
        Accuracy tests require populated golden datasets.
        """
        pillars = domain_fixture.get_pillar_names()
        
        # Every domain should have at least one pillar
        assert len(pillars) >= 1, (
            f"Domain {domain_fixture.domain_id} has no pillars defined"
        )
    
    @pytest.mark.domain_agnostic
    def test_baselines_reasonable(self, domain_fixture: DomainTestFixture):
        """Domain baselines should be within reasonable ranges."""
        baselines = domain_fixture.baselines
        
        # Accuracy thresholds should be 0.5-1.0
        assert 0.5 <= baselines.claim_precision <= 1.0
        assert 0.5 <= baselines.claim_recall <= 1.0
        assert 0.5 <= baselines.judge_accuracy <= 1.0
        
        # Efficiency thresholds should be positive
        assert baselines.max_runtime_per_paper > 0
        assert baselines.max_cost_per_paper > 0
    
    @pytest.mark.domain_agnostic
    def test_golden_dataset_structure(self, domain_fixture: DomainTestFixture):
        """Golden datasets should follow the expected structure."""
        if not domain_fixture.has_golden_dataset():
            pytest.skip(f"No golden dataset for {domain_fixture.domain_id}")
        
        golden = domain_fixture.golden_dataset
        
        # Verify structure
        assert golden.domain_id == domain_fixture.domain_id
        
        # If claims exist, they should have required fields
        for claim in golden.claims:
            assert "id" in claim
            assert "text" in claim
            assert "expected_verdict" in claim


class TestDomainRegistry:
    """Test domain registry functionality."""
    
    def test_list_domains_returns_list(self):
        """list_available_domains should return a list."""
        domains = list_available_domains()
        assert isinstance(domains, list)
    
    def test_registry_discovers_neuromorphic(self):
        """Registry should discover neuromorphic-computing domain."""
        domains = list_available_domains()
        assert "neuromorphic-computing" in domains
    
    def test_get_fixture_returns_fixture(self):
        """get_domain_fixture should return a DomainTestFixture."""
        fixture = get_domain_fixture("neuromorphic-computing")
        assert isinstance(fixture, DomainTestFixture)
    
    def test_invalid_domain_raises_keyerror(self):
        """get_domain_fixture should raise KeyError for unknown domain."""
        with pytest.raises(KeyError):
            get_domain_fixture("nonexistent-domain")
