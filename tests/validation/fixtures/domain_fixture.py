"""
Domain-Agnostic Test Fixture System

Enables validation tests to run against any research domain by providing:
- Domain-specific golden datasets
- Domain-specific expected baselines
- Integration with production ResearchConfig
- pytest parameterization support
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import logging

# Import production ResearchConfig
from literature_review.config.research_config import ResearchConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Domain Fixture Data Classes
# =============================================================================

@dataclass
class DomainBaselines:
    """Expected performance baselines for a specific domain."""
    # Accuracy baselines
    claim_precision: float = 0.85
    claim_recall: float = 0.80
    judge_accuracy: float = 0.90
    dra_recovery_rate: float = 0.40
    gap_false_negative_rate: float = 0.05
    
    # Efficiency baselines (may vary by domain complexity)
    max_runtime_per_paper: float = 120.0  # seconds
    max_cost_per_paper: float = 0.50      # dollars
    
    # Output quality baselines
    recommendation_relevance: float = 0.80
    gap_coverage: float = 1.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "DomainBaselines":
        """Create baselines from dictionary."""
        return cls(
            claim_precision=data.get("claim_precision", 0.85),
            claim_recall=data.get("claim_recall", 0.80),
            judge_accuracy=data.get("judge_accuracy", 0.90),
            dra_recovery_rate=data.get("dra_recovery_rate", 0.40),
            gap_false_negative_rate=data.get("gap_false_negative_rate", 0.05),
            max_runtime_per_paper=data.get("max_runtime_per_paper", 120.0),
            max_cost_per_paper=data.get("max_cost_per_paper", 0.50),
            recommendation_relevance=data.get("recommendation_relevance", 0.80),
            gap_coverage=data.get("gap_coverage", 1.0),
        )


@dataclass
class GoldenDataset:
    """Domain-specific golden dataset for validation."""
    domain_id: str
    papers: List[Dict[str, Any]] = field(default_factory=list)
    claims: List[Dict[str, Any]] = field(default_factory=list)
    expected_verdicts: List[Dict[str, Any]] = field(default_factory=list)
    known_gaps: List[Dict[str, Any]] = field(default_factory=list)
    expected_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def paper_count(self) -> int:
        return len(self.papers)
    
    @property
    def claim_count(self) -> int:
        return len(self.claims)
    
    @property
    def gap_count(self) -> int:
        return len(self.known_gaps)
    
    @classmethod
    def load(cls, path: Path, domain_id: str) -> "GoldenDataset":
        """Load golden dataset from JSON file."""
        if not path.exists():
            logger.warning(f"Golden dataset not found: {path}")
            return cls(domain_id=domain_id)
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(
            domain_id=domain_id,
            papers=data.get("papers", []),
            claims=data.get("claims", []),
            expected_verdicts=data.get("expected_verdicts", []),
            known_gaps=data.get("known_gaps", []),
            expected_recommendations=data.get("expected_recommendations", [])
        )
    
    def is_populated(self) -> bool:
        """Check if golden dataset has actual data."""
        return self.claim_count > 0 or self.paper_count > 0


@dataclass
class DomainTestFixture:
    """
    Complete domain-specific test fixture.
    
    Bundles together:
    - Production ResearchConfig for domain context
    - Golden dataset for accuracy validation
    - Expected baselines for threshold comparison
    """
    domain_id: str
    domain_name: str
    research_config: ResearchConfig
    golden_dataset: GoldenDataset
    baselines: DomainBaselines
    domain_dir: Path
    
    @classmethod
    def load(cls, domain_dir: Path) -> "DomainTestFixture":
        """
        Load domain fixture from directory.
        
        Expected directory structure:
            domains/{domain_id}/
            ├── research_config.json      # Required
            ├── pillar_definitions.json   # Required
            ├── golden_dataset.json       # Optional (for validation)
            └── test_baselines.json       # Optional (defaults applied)
        """
        domain_dir = Path(domain_dir)
        
        # Load production ResearchConfig
        config_path = domain_dir / "research_config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"research_config.json not found in {domain_dir}")
        
        research_config = ResearchConfig.load(str(config_path))
        domain_id = research_config.domain_id
        domain_name = research_config.domain_name
        
        # Load golden dataset (optional)
        golden_path = domain_dir / "golden_dataset.json"
        golden_dataset = GoldenDataset.load(golden_path, domain_id)
        
        # Load test baselines (optional, with defaults)
        baselines_path = domain_dir / "test_baselines.json"
        if baselines_path.exists():
            with open(baselines_path, 'r') as f:
                baselines_data = json.load(f)
            baselines = DomainBaselines.from_dict(baselines_data)
        else:
            baselines = DomainBaselines()
        
        logger.info(
            f"Loaded domain fixture: {domain_id} "
            f"({golden_dataset.claim_count} claims, "
            f"{golden_dataset.gap_count} gaps)"
        )
        
        return cls(
            domain_id=domain_id,
            domain_name=domain_name,
            research_config=research_config,
            golden_dataset=golden_dataset,
            baselines=baselines,
            domain_dir=domain_dir
        )
    
    def has_golden_dataset(self) -> bool:
        """Check if domain has a populated golden dataset."""
        return self.golden_dataset.is_populated()
    
    def get_pillar_definitions(self) -> Dict[str, Any]:
        """Get pillar definitions for this domain."""
        return self.research_config.pillar_definitions
    
    def get_pillar_names(self) -> List[str]:
        """Get list of pillar names for this domain."""
        pillars = self.research_config.pillar_definitions
        # Filter out special keys that aren't actual pillar definitions
        # Pillar keys typically start with "Pillar" or contain descriptive names
        # Exclude known metadata keys
        excluded_keys = {
            "Framework_Overview", "Cross_Cutting_Requirements", 
            "Success_Criteria", "metadata", "schema_version"
        }
        pillar_names = [
            k for k in pillars.keys() 
            if k not in excluded_keys and not k.startswith("_")
        ]
        return pillar_names


# =============================================================================
# Domain Registry
# =============================================================================

class DomainRegistry:
    """
    Registry of available domain fixtures.
    
    Discovers and manages domain fixtures from the domains/ directory.
    """
    
    def __init__(self, domains_dir: str = "domains"):
        self.domains_dir = Path(domains_dir)
        self._fixtures: Dict[str, DomainTestFixture] = {}
        self._discovered = False
    
    def discover(self) -> None:
        """Discover all available domain fixtures."""
        if not self.domains_dir.exists():
            logger.warning(f"Domains directory not found: {self.domains_dir}")
            return
        
        for subdir in self.domains_dir.iterdir():
            if not subdir.is_dir():
                continue
            
            # Skip hidden directories and template directories
            # Only skip 'example-domain' specifically, not all example-prefixed dirs
            if subdir.name.startswith((".", "_")) or subdir.name == "example-domain":
                continue
            
            # Check for research_config.json
            config_path = subdir / "research_config.json"
            if not config_path.exists():
                continue
            
            try:
                fixture = DomainTestFixture.load(subdir)
                self._fixtures[fixture.domain_id] = fixture
                logger.info(f"Registered domain: {fixture.domain_id}")
            except Exception as e:
                logger.error(f"Failed to load domain from {subdir}: {e}")
        
        self._discovered = True
    
    def get(self, domain_id: str) -> DomainTestFixture:
        """Get a specific domain fixture."""
        if not self._discovered:
            self.discover()
        
        if domain_id not in self._fixtures:
            raise KeyError(
                f"Unknown domain: {domain_id}. "
                f"Available: {list(self._fixtures.keys())}"
            )
        
        return self._fixtures[domain_id]
    
    def list_domains(self) -> List[str]:
        """List all available domain IDs."""
        if not self._discovered:
            self.discover()
        return list(self._fixtures.keys())
    
    def get_all(self) -> Dict[str, DomainTestFixture]:
        """Get all domain fixtures."""
        if not self._discovered:
            self.discover()
        return self._fixtures.copy()
    
    def get_domains_with_golden_data(self) -> List[str]:
        """Get domain IDs that have populated golden datasets."""
        if not self._discovered:
            self.discover()
        return [
            domain_id for domain_id, fixture in self._fixtures.items()
            if fixture.has_golden_dataset()
        ]


# =============================================================================
# Global Registry Instance
# =============================================================================

_domain_registry: Optional[DomainRegistry] = None


def get_domain_registry() -> DomainRegistry:
    """Get the global domain registry instance."""
    global _domain_registry
    if _domain_registry is None:
        _domain_registry = DomainRegistry()
    return _domain_registry


def get_domain_fixture(domain_id: str) -> DomainTestFixture:
    """Convenience function to get a domain fixture."""
    return get_domain_registry().get(domain_id)


def list_available_domains() -> List[str]:
    """Convenience function to list available domains."""
    return get_domain_registry().list_domains()
