"""
Tier 4 Roadmap Validator Tests
Tests for roadmap completion accuracy and cross-reference validation.
"""

import pytest
from pathlib import Path


class TestRoadmapAccuracy:
    """T4-MAP: Roadmap accuracy tests"""
    
    def test_t4_map_01_validator_returns_report(self, roadmap_validator):
        """
        T4-MAP-01: RoadmapValidator should return valid report
        """
        report = roadmap_validator.validate()
        
        assert report is not None
        assert hasattr(report, 'results')
    
    def test_t4_map_02_roadmap_files_exist(self, repo_path):
        """
        T4-MAP-02: Key roadmap files should exist
        """
        roadmap_files = [
            "docs/CONSOLIDATED_ROADMAP.md",
            "docs/MASTER_REPOSITORY_ROADMAP.md",
        ]
        
        for file_path in roadmap_files:
            full_path = repo_path / file_path
            assert full_path.exists(), f"Roadmap file {file_path} should exist"
    
    def test_t4_map_03_gold_standard_exists(self, gold_standards_path):
        """
        T4-MAP-03: Gold standard roadmap should exist
        """
        roadmap_yaml = gold_standards_path / "repository_roadmap.yaml"
        assert roadmap_yaml.exists(), "repository_roadmap.yaml should exist"


class TestRoadmapCrossReferences:
    """Cross-reference validation tests"""
    
    def test_t4_map_04_consolidated_roadmap_readable(self, repo_path):
        """
        T4-MAP-04: Consolidated roadmap should be readable
        """
        roadmap_path = repo_path / "docs" / "CONSOLIDATED_ROADMAP.md"
        
        if roadmap_path.exists():
            content = roadmap_path.read_text(encoding='utf-8')
            assert len(content) > 100, "Roadmap should have substantial content"
