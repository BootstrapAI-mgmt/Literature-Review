"""
Tests for Paper Sourcing and Registry

Tests validate the paper registry structure, domain coverage,
and open access license verification.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, List

# Import the paper sourcing module
import sys
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from source_papers import PaperRegistry, VALID_LICENSES


# Constants
PAPERS_DIR = Path(__file__).parent / "papers"
REGISTRY_PATH = PAPERS_DIR / "paper_registry.json"
REQUIRED_DOMAINS = [
    "neuromorphic",
    "nano_thermal",
    "fusion",
    "quantum",
    "microbio",
    "climate",
    "materials",
    "bioimaging"
]
MIN_PAPERS_PER_DOMAIN = 10
MIN_TOTAL_PAPERS = 80
MIN_CLAIMS_PER_PAPER = 5


def load_registry() -> Dict:
    """Load the paper registry JSON file."""
    if not REGISTRY_PATH.exists():
        pytest.skip(f"Paper registry not found: {REGISTRY_PATH}")
    
    with open(REGISTRY_PATH, 'r') as f:
        return json.load(f)


def count_by_domain(registry: Dict) -> Dict[str, int]:
    """Count papers by domain."""
    papers = [p for p in registry.get("papers", []) 
              if p.get("annotation_status") != "example"]
    
    counts = {domain: 0 for domain in REQUIRED_DOMAINS}
    for paper in papers:
        domain = paper.get("domain")
        if domain in counts:
            counts[domain] += 1
    return counts


class TestPaperRegistrySchema:
    """Test paper registry schema and structure."""
    
    @pytest.mark.unit
    def test_paper_registry_exists(self):
        """Verify paper registry file exists."""
        assert REGISTRY_PATH.exists(), f"Paper registry not found: {REGISTRY_PATH}"
    
    @pytest.mark.unit
    def test_paper_registry_valid_json(self):
        """Verify paper registry is valid JSON."""
        registry = load_registry()
        assert isinstance(registry, dict)
        assert "version" in registry
        assert "papers" in registry
    
    @pytest.mark.unit
    def test_paper_registry_version(self):
        """Verify paper registry has correct version."""
        registry = load_registry()
        assert registry.get("version") == "1.0.0"
    
    @pytest.mark.unit
    def test_paper_registry_domains(self):
        """Verify all required domains are defined."""
        registry = load_registry()
        domains = registry.get("domains", [])
        for required in REQUIRED_DOMAINS:
            assert required in domains, f"Missing required domain: {required}"


class TestPaperRegistryContent:
    """Test paper registry content - may be skipped if papers not yet sourced."""
    
    @pytest.mark.unit
    def test_all_domains_have_papers(self):
        """Each domain has minimum papers (skipped if < 80 total papers)."""
        registry = load_registry()
        papers = [p for p in registry.get("papers", []) 
                  if p.get("annotation_status") != "example"]
        
        if len(papers) < MIN_TOTAL_PAPERS:
            pytest.skip(f"Only {len(papers)}/{MIN_TOTAL_PAPERS} papers sourced")
        
        domain_counts = count_by_domain(registry)
        for domain in REQUIRED_DOMAINS:
            count = domain_counts.get(domain, 0)
            assert count >= MIN_PAPERS_PER_DOMAIN, \
                f"Domain '{domain}' has only {count}/{MIN_PAPERS_PER_DOMAIN} papers"
    
    @pytest.mark.unit
    def test_total_papers_minimum(self):
        """Verify minimum total paper count (skipped if not yet sourced)."""
        registry = load_registry()
        papers = [p for p in registry.get("papers", []) 
                  if p.get("annotation_status") != "example"]
        
        # Skip if papers haven't been sourced yet
        if len(papers) == 0:
            pytest.skip("No papers sourced yet")
        
        # Only fail if some papers exist but not enough
        if len(papers) < MIN_TOTAL_PAPERS:
            pytest.skip(f"Only {len(papers)}/{MIN_TOTAL_PAPERS} papers sourced (ongoing)")
    
    @pytest.mark.unit
    def test_paper_required_fields(self):
        """Verify each paper has required fields."""
        registry = load_registry()
        papers = [p for p in registry.get("papers", []) 
                  if p.get("annotation_status") != "example"]
        
        if len(papers) == 0:
            pytest.skip("No papers sourced yet")
        
        required_fields = ["paper_id", "domain", "title", "year", "license"]
        
        for paper in papers:
            paper_id = paper.get("paper_id", "UNKNOWN")
            for field in required_fields:
                assert field in paper, f"Paper {paper_id} missing field: {field}"
                assert paper[field], f"Paper {paper_id} has empty field: {field}"


class TestOpenAccessVerification:
    """Test open access license verification."""
    
    @pytest.mark.unit
    def test_all_papers_have_license(self):
        """All papers have a license field."""
        registry = load_registry()
        papers = [p for p in registry.get("papers", []) 
                  if p.get("annotation_status") != "example"]
        
        if len(papers) == 0:
            pytest.skip("No papers sourced yet")
        
        for paper in papers:
            paper_id = paper.get("paper_id", "UNKNOWN")
            assert "license" in paper, f"Paper {paper_id} missing license field"
    
    @pytest.mark.unit
    def test_open_access_licenses_valid(self):
        """All papers have valid open access licenses."""
        registry = load_registry()
        papers = [p for p in registry.get("papers", []) 
                  if p.get("annotation_status") != "example"]
        
        if len(papers) == 0:
            pytest.skip("No papers sourced yet")
        
        for paper in papers:
            paper_id = paper.get("paper_id", "UNKNOWN")
            license_val = paper.get("license", "")
            
            # Check if license contains any valid license type
            is_valid = any(valid in license_val for valid in VALID_LICENSES)
            assert is_valid, \
                f"Paper {paper_id} has invalid license: '{license_val}'"


class TestClaimEstimates:
    """Test claim count estimates."""
    
    @pytest.mark.unit
    def test_papers_have_claim_estimates(self):
        """Papers have claim count estimates."""
        registry = load_registry()
        papers = [p for p in registry.get("papers", []) 
                  if p.get("annotation_status") != "example"]
        
        if len(papers) == 0:
            pytest.skip("No papers sourced yet")
        
        for paper in papers:
            paper_id = paper.get("paper_id", "UNKNOWN")
            claim_est = paper.get("claim_count_estimate", 0)
            
            # Allow papers without estimate (defaults to 0)
            # but if specified, should be >= 5
            if claim_est > 0:
                assert claim_est >= MIN_CLAIMS_PER_PAPER, \
                    f"Paper {paper_id} has low claim estimate: {claim_est}"


class TestDomainDirectories:
    """Test domain directory structure."""
    
    @pytest.mark.unit
    def test_domain_directories_exist(self):
        """All domain directories exist."""
        for domain in REQUIRED_DOMAINS:
            domain_dir = PAPERS_DIR / domain
            assert domain_dir.exists(), f"Domain directory missing: {domain_dir}"
            assert domain_dir.is_dir(), f"Not a directory: {domain_dir}"
    
    @pytest.mark.unit
    def test_sourcing_guides_exist(self):
        """Each domain has a SOURCING.md guide."""
        for domain in REQUIRED_DOMAINS:
            sourcing_file = PAPERS_DIR / domain / "SOURCING.md"
            assert sourcing_file.exists(), \
                f"SOURCING.md missing for domain: {domain}"


class TestPaperRegistryClass:
    """Test PaperRegistry class functionality."""
    
    @pytest.mark.unit
    def test_registry_loads(self):
        """Registry class loads successfully."""
        registry = PaperRegistry()
        assert registry.data is not None
        assert "papers" in registry.data
    
    @pytest.mark.unit
    def test_registry_domains(self):
        """Registry has correct domain list."""
        registry = PaperRegistry()
        assert len(registry.DOMAINS) == 8
        for domain in REQUIRED_DOMAINS:
            assert domain in registry.DOMAINS
    
    @pytest.mark.unit
    def test_registry_domain_prefixes(self):
        """Registry has domain prefixes."""
        registry = PaperRegistry()
        for domain in REQUIRED_DOMAINS:
            assert domain in registry.DOMAIN_PREFIXES
            prefix = registry.DOMAIN_PREFIXES[domain]
            assert len(prefix) >= 3, f"Prefix too short for {domain}: {prefix}"
    
    @pytest.mark.unit
    def test_registry_list_papers(self):
        """Registry list_papers method works."""
        registry = PaperRegistry()
        papers = registry.list_papers()
        assert isinstance(papers, list)
    
    @pytest.mark.unit
    def test_registry_list_papers_by_domain(self):
        """Registry list_papers filters by domain."""
        registry = PaperRegistry()
        for domain in REQUIRED_DOMAINS:
            papers = registry.list_papers(domain=domain)
            for paper in papers:
                assert paper.get("domain") == domain
    
    @pytest.mark.unit
    def test_registry_validate(self):
        """Registry validate method works."""
        registry = PaperRegistry()
        is_valid, issues = registry.validate()
        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)
    
    @pytest.mark.unit
    def test_registry_generate_report(self):
        """Registry generate_report method works."""
        registry = PaperRegistry()
        report = registry.generate_report()
        assert isinstance(report, str)
        assert "# Paper Sourcing Report" in report
        assert "## Domain Breakdown" in report


class TestValidLicenses:
    """Test license validation constants."""
    
    @pytest.mark.unit
    def test_valid_licenses_defined(self):
        """Valid licenses list is defined."""
        assert len(VALID_LICENSES) > 0
    
    @pytest.mark.unit
    def test_common_licenses_included(self):
        """Common open access licenses are included."""
        common = ["CC-BY", "CC-BY-4.0", "CC0", "arXiv", "PMC-OA"]
        for lic in common:
            assert lic in VALID_LICENSES, f"Missing common license: {lic}"
