"""
Tier 4 Architecture Validator Tests
Tests for architecture blueprint accuracy.
"""

import pytest
from pathlib import Path


class TestArchitectureValidation:
    """T4-ARCH: Architecture validation tests"""
    
    def test_t4_arch_01_validator_returns_report(self, architecture_validator):
        """
        T4-ARCH-01: ArchitectureValidator should return valid report
        """
        report = architecture_validator.validate()
        
        assert report is not None
        assert hasattr(report, 'results')
    
    def test_t4_arch_02_blueprint_exists(self, repo_path):
        """
        T4-ARCH-02: Architecture blueprint should exist
        """
        blueprint_path = repo_path / "docs" / "MASTER_ARCHITECTURE_BLUEPRINT.md"
        assert blueprint_path.exists(), "Architecture blueprint should exist"
    
    def test_t4_arch_03_gold_standard_exists(self, gold_standards_path):
        """
        T4-ARCH-03: Gold standard architecture should exist
        """
        arch_yaml = gold_standards_path / "architecture_blueprint.yaml"
        assert arch_yaml.exists(), "architecture_blueprint.yaml should exist"


class TestArchitectureStructure:
    """Architecture structure validation"""
    
    def test_t4_arch_04_key_directories_exist(self, repo_path):
        """
        T4-ARCH-04: Key repository directories should exist
        """
        key_dirs = [
            "docs",
            "literature_review",
            "tests",
            "gold_standards",
            "task-cards",
            "validation_framework",
        ]
        
        for dir_name in key_dirs:
            dir_path = repo_path / dir_name
            assert dir_path.exists(), f"Directory {dir_name} should exist"
    
    def test_t4_arch_05_blueprint_yaml_parseable(self, gold_standards_path):
        """
        T4-ARCH-05: Architecture YAML should be parseable
        """
        import yaml
        
        arch_path = gold_standards_path / "architecture_blueprint.yaml"
        if arch_path.exists():
            content = arch_path.read_text(encoding='utf-8')
            data = yaml.safe_load(content)
            assert data is not None, "YAML should parse successfully"
