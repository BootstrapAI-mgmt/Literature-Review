"""
Tier 4 Staleness Validator Tests
Tests for document freshness and staleness detection.
"""

import pytest
from pathlib import Path


class TestStalenessValidation:
    """T4-STALE: Staleness validation tests"""
    
    def test_t4_stale_01_validator_returns_report(self, staleness_validator):
        """
        T4-STALE-01: StalenessValidator should return valid report
        """
        report = staleness_validator.validate()
        
        assert report is not None
        assert hasattr(report, 'results')
    
    def test_t4_stale_02_freshness_thresholds_exist(self, gold_standards_path):
        """
        T4-STALE-02: Freshness thresholds gold standard should exist
        """
        thresholds_path = gold_standards_path / "freshness_thresholds.yaml"
        assert thresholds_path.exists(), "freshness_thresholds.yaml should exist"
    
    def test_t4_stale_03_docs_directory_exists(self, repo_path):
        """
        T4-STALE-03: docs/ directory should exist for staleness checking
        """
        docs_dir = repo_path / "docs"
        assert docs_dir.exists(), "docs directory should exist"
        assert docs_dir.is_dir(), "docs should be a directory"


class TestFreshnessThresholds:
    """Freshness threshold validation"""
    
    def test_t4_stale_04_thresholds_parseable(self, gold_standards_path):
        """
        T4-STALE-04: Freshness thresholds should be parseable YAML
        """
        import yaml
        
        thresholds_path = gold_standards_path / "freshness_thresholds.yaml"
        if thresholds_path.exists():
            content = thresholds_path.read_text(encoding='utf-8')
            data = yaml.safe_load(content)
            assert data is not None, "YAML should parse successfully"
