"""
Domain Fixture System for Validation Tests

Provides domain-agnostic test fixtures that integrate with ResearchConfig
for parameterized testing across multiple research domains.
"""

from tests.validation.fixtures.domain_fixture import (
    DomainBaselines,
    GoldenDataset,
    DomainTestFixture,
    DomainRegistry,
    get_domain_registry,
    get_domain_fixture,
    list_available_domains,
)

__all__ = [
    "DomainBaselines",
    "GoldenDataset",
    "DomainTestFixture",
    "DomainRegistry",
    "get_domain_registry",
    "get_domain_fixture",
    "list_available_domains",
]
