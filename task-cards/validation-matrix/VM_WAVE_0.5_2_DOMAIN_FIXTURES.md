# Task Card: Domain Fixture System

**Task ID:** VM-W0.5-2  
**Wave:** 0.5 (Modularization Infrastructure)  
**Priority:** HIGH (P2 - Builds on existing ResearchConfig)  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** VM-W0-2 (Golden Dataset Spec)  
**Blocks:** Cross-domain validation testing  
**Validation IDs:** DF-01, DF-02

---

## Objective

Create a domain-agnostic test fixture system that enables validation tests to run against any research domain (neuromorphic computing, thermophoresis, climate science, etc.) by loading domain-specific golden datasets and expected baselines.

## Background

The third-party modularization assessment (Score: 7/10) identified that while the production code has excellent domain-agnostic infrastructure via `ResearchConfig`, the validation layer doesn't leverage this for parameterized testing:

```python
# Production code: Already domain-agnostic ✓
config = ResearchConfig.load("domains/thermophoresis/research_config.json")

# Validation code: Hardcoded to neuromorphic ✗
golden = load_golden_dataset("tests/golden_dataset/neuromorphic.json")  # Hardcoded!
```

This prevents:
- Running validation tests against multiple research domains
- Comparing pipeline performance across domains
- Creating domain-specific golden datasets for accuracy validation
- Switching research focus without modifying test code

## Success Criteria

- [ ] DF-01: All domain fixtures load correctly from their directories
- [ ] DF-02: Cross-domain tests execute on all registered domains
- [ ] Domain fixture integrates with existing `ResearchConfig`
- [ ] Per-domain golden datasets follow standard schema
- [ ] Per-domain expected baselines (accuracy thresholds) are configurable
- [ ] pytest parameterization works across domains

---

## Validation Matrix Mapping

| ID | Test | Input | Expected Output | Success Criteria |
|----|------|-------|-----------------|------------------|
| DF-01 | Domain Fixture Validation | All registered domains | Fixtures load correctly | No load errors, all paths valid |
| DF-02 | Cross-Domain Execution | Parameterized tests | Tests run on each domain | All domains tested, results collected |

---

## Deliverables

### 1. Domain Fixture Module

**File:** `tests/validation/fixtures/domain_fixture.py`

```python
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
        pillars = self.research_config.pillar_definitions.get("pillars", [])
        return [p.get("name", p.get("id", "unknown")) for p in pillars]


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
            
            # Skip template/example directories
            if subdir.name.startswith((".", "_", "example")):
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
```

### 2. Golden Dataset Schema Template

**File:** `domains/example-domain/golden_dataset.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "golden_dataset.schema.json",
  "title": "Domain Golden Dataset",
  "description": "Schema for domain-specific golden datasets used in validation testing",
  "type": "object",
  "required": ["metadata", "claims"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["domain_id", "created_at", "version"],
      "properties": {
        "domain_id": {
          "type": "string",
          "description": "Must match domain's research_config.json domain.id"
        },
        "created_at": {
          "type": "string",
          "format": "date-time"
        },
        "version": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+$"
        },
        "annotator_count": {
          "type": "integer",
          "minimum": 1
        },
        "description": {
          "type": "string"
        }
      }
    },
    "papers": {
      "type": "array",
      "description": "Reference papers with known claims",
      "items": {
        "type": "object",
        "required": ["id", "title", "expected_claim_count"],
        "properties": {
          "id": {"type": "string"},
          "title": {"type": "string"},
          "pdf_path": {"type": "string"},
          "expected_claim_count": {"type": "integer", "minimum": 0}
        }
      }
    },
    "claims": {
      "type": "array",
      "description": "Human-annotated claims with expected verdicts",
      "items": {
        "type": "object",
        "required": ["id", "text", "pillar", "expected_verdict"],
        "properties": {
          "id": {"type": "string"},
          "paper_id": {"type": "string"},
          "text": {"type": "string", "minLength": 10},
          "pillar": {"type": "string"},
          "expected_verdict": {
            "type": "string",
            "enum": ["APPROVE", "REJECT", "DEEP_REVIEW"]
          },
          "expected_scores": {
            "type": "object",
            "properties": {
              "strength": {"type": "number", "minimum": 1, "maximum": 5},
              "relevance": {"type": "number", "minimum": 1, "maximum": 5},
              "specificity": {"type": "number", "minimum": 1, "maximum": 5},
              "composite": {"type": "number", "minimum": 1, "maximum": 5}
            }
          },
          "annotation_notes": {"type": "string"},
          "difficulty": {
            "type": "string",
            "enum": ["easy", "medium", "hard", "boundary"]
          }
        }
      }
    },
    "expected_verdicts": {
      "type": "array",
      "description": "Summary of expected verdict distribution",
      "items": {
        "type": "object",
        "required": ["claim_id", "verdict"],
        "properties": {
          "claim_id": {"type": "string"},
          "verdict": {"type": "string"},
          "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        }
      }
    },
    "known_gaps": {
      "type": "array",
      "description": "Known gaps that should be detected",
      "items": {
        "type": "object",
        "required": ["id", "pillar", "description"],
        "properties": {
          "id": {"type": "string"},
          "pillar": {"type": "string"},
          "description": {"type": "string"},
          "severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low"]
          },
          "expected_search_terms": {
            "type": "array",
            "items": {"type": "string"}
          }
        }
      }
    },
    "expected_recommendations": {
      "type": "array",
      "description": "Expected search recommendations for gaps",
      "items": {
        "type": "object",
        "required": ["gap_id", "recommendation"],
        "properties": {
          "gap_id": {"type": "string"},
          "recommendation": {"type": "string"},
          "expected_databases": {
            "type": "array",
            "items": {"type": "string"}
          }
        }
      }
    }
  }
}
```

### 3. Golden Dataset Template

**File:** `domains/example-domain/golden_dataset.json`

```json
{
  "metadata": {
    "domain_id": "example-domain",
    "created_at": "2026-01-01T00:00:00Z",
    "version": "1.0",
    "annotator_count": 0,
    "description": "Template golden dataset - replace with actual annotated data"
  },
  "papers": [],
  "claims": [],
  "expected_verdicts": [],
  "known_gaps": [],
  "expected_recommendations": []
}
```

### 4. Test Baselines Template

**File:** `domains/example-domain/test_baselines.json`

```json
{
  "$schema": "Test baselines for domain-specific validation",
  "claim_precision": 0.85,
  "claim_recall": 0.80,
  "judge_accuracy": 0.90,
  "dra_recovery_rate": 0.40,
  "gap_false_negative_rate": 0.05,
  "max_runtime_per_paper": 120.0,
  "max_cost_per_paper": 0.50,
  "recommendation_relevance": 0.80,
  "gap_coverage": 1.0
}
```

### 5. pytest Integration

**File:** `tests/conftest.py` (additions for domain fixtures)

```python
# =============================================================================
# Domain Fixture Integration
# =============================================================================

import pytest

# Import domain fixtures (will be created by VM-W0.5-2)
try:
    from tests.validation.fixtures.domain_fixture import (
        get_domain_registry,
        get_domain_fixture,
        DomainTestFixture,
        list_available_domains
    )
    DOMAINS_AVAILABLE = True
except ImportError:
    DOMAINS_AVAILABLE = False


def pytest_addoption(parser):
    """Add domain-related command-line options."""
    parser.addoption(
        "--domain",
        action="store",
        default="neuromorphic-computing",
        help="Domain to test (default: neuromorphic-computing)"
    )
    parser.addoption(
        "--all-domains",
        action="store_true",
        default=False,
        help="Run tests on all available domains"
    )


@pytest.fixture(scope="session")
def domain_fixture(request) -> "DomainTestFixture":
    """Load domain fixture for single-domain tests."""
    if not DOMAINS_AVAILABLE:
        pytest.skip("Domain fixtures not available")
    
    domain_id = request.config.getoption("--domain")
    try:
        return get_domain_fixture(domain_id)
    except KeyError as e:
        pytest.fail(str(e))


@pytest.fixture(scope="session")
def all_domain_fixtures(request) -> dict:
    """Load all domain fixtures for cross-domain tests."""
    if not DOMAINS_AVAILABLE:
        pytest.skip("Domain fixtures not available")
    
    return get_domain_registry().get_all()


def pytest_generate_tests(metafunc):
    """Parameterize tests across domains if requested."""
    if not DOMAINS_AVAILABLE:
        return
    
    if "domain_id" in metafunc.fixturenames:
        all_domains_flag = metafunc.config.getoption("--all-domains", default=False)
        
        if all_domains_flag:
            domains = list_available_domains()
        else:
            domains = [metafunc.config.getoption("--domain", default="neuromorphic-computing")]
        
        metafunc.parametrize("domain_id", domains)


@pytest.fixture
def domain_golden_dataset(domain_fixture):
    """Get golden dataset from domain fixture."""
    if not domain_fixture.has_golden_dataset():
        pytest.skip(f"No golden dataset for domain: {domain_fixture.domain_id}")
    return domain_fixture.golden_dataset


@pytest.fixture
def domain_baselines(domain_fixture):
    """Get expected baselines from domain fixture."""
    return domain_fixture.baselines


@pytest.fixture
def domain_pillars(domain_fixture):
    """Get pillar names from domain fixture."""
    return domain_fixture.get_pillar_names()
```

### 6. Cross-Domain Validation Tests

**File:** `tests/validation/test_cross_domain.py`

```python
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
        assert "pillars" in pillars or len(pillars) > 0
    
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
    @pytest.mark.skipif(
        not any(get_domain_fixture(d).has_golden_dataset() 
                for d in list_available_domains()),
        reason="No domains have golden datasets"
    )
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
```

---

## Usage Examples

### Command-Line Usage

```bash
# Run on default domain (neuromorphic-computing)
pytest tests/validation/ --domain neuromorphic-computing

# Run on a different domain
pytest tests/validation/ --domain thermophoresis

# Run on all available domains
pytest tests/validation/ --all-domains

# Run cross-domain tests only
pytest tests/validation/test_cross_domain.py --all-domains
```

### Creating a New Domain for Testing

```bash
# 1. Create domain directory
mkdir -p domains/my-new-domain

# 2. Copy templates
cp domains/example-domain/research_config.json domains/my-new-domain/
cp domains/example-domain/pillar_definitions.json domains/my-new-domain/
cp domains/example-domain/golden_dataset.json domains/my-new-domain/
cp domains/example-domain/test_baselines.json domains/my-new-domain/

# 3. Edit configs for your domain
# 4. Populate golden_dataset.json with annotated claims
# 5. Adjust test_baselines.json if needed

# 6. Run tests on new domain
pytest tests/validation/ --domain my-new-domain
```

### In-Test Usage

```python
# Access domain-specific context
def test_with_domain_context(domain_fixture):
    config = domain_fixture.research_config
    golden = domain_fixture.golden_dataset
    baselines = domain_fixture.baselines
    
    # Use domain-specific threshold
    assert accuracy >= baselines.judge_accuracy

# Parameterized across all domains
@pytest.mark.domain_agnostic
def test_across_domains(domain_id):
    fixture = get_domain_fixture(domain_id)
    # Test runs once per domain
```

---

## Dependencies

### Python Packages
- `pytest>=7.0.0` - Test framework
- `pyyaml>=6.0.0` - YAML parsing (if needed)

### Internal Dependencies
- `literature_review.config.research_config.ResearchConfig` - Production config loader
- VM-W0-2 (Golden Dataset Spec) - Schema for golden datasets

---

## Acceptance Criteria

- [ ] DF-01: All domain fixtures load without errors
- [ ] DF-02: Cross-domain tests execute on all domains
- [ ] Domain registry discovers domains automatically
- [ ] `--domain` and `--all-domains` CLI flags work
- [ ] Golden dataset schema documented
- [ ] Test baselines configurable per domain
- [ ] Example domain template complete
- [ ] Tests run in < 2 seconds (fixture loading)

---

## Notes

- Start with neuromorphic-computing as the primary domain
- Other domains can be added incrementally
- Golden datasets are the long-pole—focus on schema first
- Consider adding domain validation script similar to metrics
- Domain fixtures should be lightweight (lazy loading where possible)

---

## Additional Deliverables

### Domain Fixture Validation Script

**File:** `scripts/validate_domain_fixture.py`

```python
#!/usr/bin/env python3
"""
Domain Fixture Validation Script

Validates domain fixtures similar to metrics configuration validation.
Checks for required files, schema compliance, and cross-references.

Usage:
    python scripts/validate_domain_fixture.py domains/neuromorphic-computing/
    python scripts/validate_domain_fixture.py --all
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def validate_domain(domain_dir: Path) -> Dict[str, Any]:
    """Validate a single domain fixture."""
    result = {
        "domain_dir": str(domain_dir),
        "valid": True,
        "errors": [],
        "warnings": [],
        "stats": {}
    }
    
    # Check required files
    required_files = [
        "research_config.json",
        "pillar_definitions.json"
    ]
    
    for req_file in required_files:
        if not (domain_dir / req_file).exists():
            result["errors"].append(f"Missing required file: {req_file}")
            result["valid"] = False
    
    # Check optional files
    optional_files = [
        "golden_dataset.json",
        "test_baselines.json"
    ]
    
    for opt_file in optional_files:
        if not (domain_dir / opt_file).exists():
            result["warnings"].append(f"Missing optional file: {opt_file}")
    
    # Validate research_config.json
    config_path = domain_dir / "research_config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            result["stats"]["domain_id"] = config.get("domain", {}).get("id", "unknown")
            result["stats"]["domain_name"] = config.get("domain", {}).get("name", "unknown")
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid JSON in research_config.json: {e}")
            result["valid"] = False
    
    # Validate golden_dataset.json if present
    golden_path = domain_dir / "golden_dataset.json"
    if golden_path.exists():
        try:
            with open(golden_path) as f:
                golden = json.load(f)
            result["stats"]["claim_count"] = len(golden.get("claims", []))
            result["stats"]["gap_count"] = len(golden.get("known_gaps", []))
            result["stats"]["paper_count"] = len(golden.get("papers", []))
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid JSON in golden_dataset.json: {e}")
            result["valid"] = False
    
    return result


def validate_all_domains(domains_dir: Path) -> List[Dict[str, Any]]:
    """Validate all domains in the domains directory."""
    results = []
    
    for subdir in sorted(domains_dir.iterdir()):
        if not subdir.is_dir():
            continue
        if subdir.name.startswith((".", "_")):
            continue
        
        # Check if it looks like a domain directory
        if (subdir / "research_config.json").exists():
            results.append(validate_domain(subdir))
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Validate domain fixtures")
    parser.add_argument("domain_dir", nargs="?", help="Path to domain directory")
    parser.add_argument("--all", action="store_true", help="Validate all domains")
    parser.add_argument("--domains-dir", default="domains", help="Domains directory")
    args = parser.parse_args()
    
    if args.all:
        results = validate_all_domains(Path(args.domains_dir))
    elif args.domain_dir:
        results = [validate_domain(Path(args.domain_dir))]
    else:
        parser.print_help()
        sys.exit(1)
    
    # Print results
    all_valid = True
    for result in results:
        status = "✓ VALID" if result["valid"] else "✗ INVALID"
        print(f"\n{status}: {result['domain_dir']}")
        
        if result.get("stats"):
            print(f"  Domain: {result['stats'].get('domain_name', 'unknown')}")
            if "claim_count" in result["stats"]:
                print(f"  Claims: {result['stats']['claim_count']}")
                print(f"  Gaps: {result['stats']['gap_count']}")
        
        for error in result["errors"]:
            print(f"  ERROR: {error}")
        for warning in result["warnings"]:
            print(f"  WARNING: {warning}")
        
        if not result["valid"]:
            all_valid = False
    
    print(f"\n{'='*50}")
    print(f"Total: {len(results)} domains, {'all valid' if all_valid else 'some invalid'}")
    
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
```

### Example Domain Template

**Directory:** `domains/example-domain/`

```
domains/example-domain/
├── README.md                    # Domain documentation
├── research_config.json         # Required: Domain configuration
├── pillar_definitions.json      # Required: Research pillars
├── golden_dataset.json          # Optional: Validation data
├── test_baselines.json          # Optional: Domain-specific thresholds
└── sample_papers/               # Optional: Test PDFs
    └── sample_paper_001.pdf
```

**File:** `domains/example-domain/README.md`

```markdown
# Example Domain

This is a template domain directory showing the expected structure for
domain-agnostic testing.

## Files

- `research_config.json` - Required domain configuration
- `pillar_definitions.json` - Required pillar definitions
- `golden_dataset.json` - Optional validation dataset
- `test_baselines.json` - Optional domain-specific thresholds

## Usage

```bash
# Validate this domain fixture
python scripts/validate_domain_fixture.py domains/example-domain/

# Run tests against this domain
pytest tests/validation/ --domain=example-domain
```
```

**File:** `domains/example-domain/test_baselines.json`

```json
{
  "claim_precision": 0.85,
  "claim_recall": 0.80,
  "judge_accuracy": 0.90,
  "dra_recovery_rate": 0.40,
  "gap_false_negative_rate": 0.05,
  "max_runtime_per_paper": 120.0,
  "max_cost_per_paper": 0.50,
  "recommendation_relevance": 0.80,
  "gap_coverage": 1.0
}
```

---

## Cross-Task Integration

This task integrates with the other Wave 0.5 tasks:

### Integration with VM-W0.5-1 (Metrics Configuration)

Domain fixtures can reference metrics config for domain-specific thresholds:

```python
from tests.validation.config.metrics_config import get_metrics_config

class DomainTestFixture:
    def get_domain_threshold(self, metric_id: str) -> float:
        """Get threshold, with optional domain override."""
        base_config = get_metrics_config()
        base = base_config.get_threshold(metric_id)
        
        # Check for domain-specific override in baselines
        domain_override = getattr(self.baselines, metric_id.lower().replace("-", "_"), None)
        return domain_override if domain_override is not None else base
    
    def check_metric(self, metric_id: str, value: float) -> bool:
        """Check value against domain-aware threshold."""
        threshold = self.get_domain_threshold(metric_id)
        return value >= threshold
```

### Integration with VM-W0.5-3 (Model Abstraction)

Consider domain-model matrix testing for comprehensive validation:

```python
@pytest.fixture(params=["gemini-flash", "gpt-4-turbo"])
def model_fixture(request):
    """Parameterized model fixture."""
    from literature_review.config.model_config import set_model
    return set_model(request.param)

@pytest.mark.domain_model_matrix
def test_domain_model_combination(domain_fixture, model_fixture):
    """Test all domain × model combinations."""
    # Run validation with specific domain and model
    results = run_validation(
        domain=domain_fixture,
        model=model_fixture
    )
    assert results.passed
```

### Combined Validation Context Fixture

```python
# tests/conftest.py - Combined fixture for all Wave 0.5 features
@pytest.fixture
def validation_context(metrics_config, domain_fixture, request):
    """Combined validation context with all modularization features."""
    from literature_review.config.model_config import get_model_config
    
    model_name = request.config.getoption("--model", default=None)
    
    return {
        "metrics": metrics_config,
        "domain": domain_fixture,
        "model": get_model_config() if model_name else None,
        "profile": metrics_config.active_profile,
    }
```
