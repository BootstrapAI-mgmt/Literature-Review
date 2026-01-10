"""
Tier 4 Cascade Validator Tests
Tests for cascade update validation and dependency tracking.
"""

import pytest
from pathlib import Path


class TestCascadeValidation:
    """T4-CASC: Cascade validation tests"""
    
    def test_t4_casc_01_validator_returns_report(self, cascade_validator):
        """
        T4-CASC-01: CascadeValidator should return valid report
        """
        report = cascade_validator.validate()
        
        assert report is not None
        assert hasattr(report, 'results')
    
    def test_t4_casc_02_documentation_matrix_exists(self, repo_path):
        """
        T4-CASC-02: Documentation matrix should exist
        """
        matrix_path = repo_path / "docs" / "documentation_matrix.json"
        assert matrix_path.exists(), "documentation_matrix.json should exist"


class TestCascadeDependencies:
    """Dependency tracking tests"""
    
    def test_t4_casc_03_matrix_parseable(self, repo_path):
        """
        T4-CASC-03: Documentation matrix should be valid JSON
        """
        import json
        
        matrix_path = repo_path / "docs" / "documentation_matrix.json"
        if matrix_path.exists():
            content = matrix_path.read_text(encoding='utf-8')
            data = json.loads(content)
            assert data is not None, "JSON should parse successfully"
            assert "documents" in data or "owner_domains" in data, "Matrix should have expected structure"
    
    def test_t4_casc_04_gold_standard_deps_exist(self, gold_standards_path):
        """
        T4-CASC-04: Gold standard with dependency info should exist
        """
        # Check for any gold standard that defines dependencies
        yaml_files = list(gold_standards_path.glob("*.yaml"))
        assert len(yaml_files) > 0, "Should have gold standard YAML files"
