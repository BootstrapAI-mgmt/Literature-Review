"""Unit tests for validation tracker."""

import pytest
import json
from pathlib import Path

from literature_review.analysis.validation_tracker import (
    ValidationTracker,
    ValidationCoverageItem,
    CoverageLevel,
    generate_validation_matrix
)
from literature_review.models import ValidationStatus


class TestValidationCoverageItem:
    """Tests for ValidationCoverageItem dataclass."""
    
    def test_create_coverage_item(self):
        """Test creating a coverage item."""
        item = ValidationCoverageItem(
            requirement_id="Sub-1.1.1",
            requirement_text="Test requirement",
            pillar="Pillar 1",
            parent_requirement="REQ-1.1",
            has_strategy=True,
            validation_method="fMRI comparison"
        )
        
        assert item.requirement_id == "Sub-1.1.1"
        assert item.has_strategy is True
    
    def test_to_dict(self):
        """Test serialization."""
        item = ValidationCoverageItem(
            requirement_id="Sub-1.1.1",
            requirement_text="Test",
            pillar="Pillar 1",
            parent_requirement="REQ-1.1",
            coverage_status=ValidationStatus.VALIDATED,
            coverage_level=CoverageLevel.FULL
        )
        
        data = item.to_dict()
        assert data["coverage_status"] == "validated"
        assert data["coverage_level"] == "full"


class TestValidationTracker:
    """Tests for ValidationTracker class."""
    
    @pytest.fixture
    def sample_pillar_definitions(self, tmp_path):
        """Create sample pillar definitions with validation strategies."""
        definitions = {
            "Pillar 1: Biological Stimulus-Response": {
                "requirements": {
                    "REQ-B1.1: Sensory Transduction": [
                        {
                            "id": "Sub-1.1.1",
                            "text": "Sensory data transduction model",
                            "validation_strategy": {
                                "method": "fMRI comparison",
                                "benchmark_protocol": "Natural scene presentation",
                                "acceptance_criteria": "> 0.8 correlation"
                            }
                        },
                        {
                            "id": "Sub-1.1.2",
                            "text": "Feature extraction mechanism",
                            "validation_strategy": {}  # No strategy defined
                        }
                    ]
                },
                "validation_criteria": {
                    "required_evidence": "fMRI, EEG, single-cell recordings"
                }
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        return str(path)
    
    @pytest.fixture
    def sample_gap_analysis(self, tmp_path):
        """Create sample gap analysis report."""
        gap_data = {
            "Pillar 1: Biological Stimulus-Response": {
                "analysis": {
                    "REQ-B1.1: Sensory Transduction": {
                        "Sub-1.1.1": {
                            "completeness_percent": 70,
                            "contributing_papers": [
                                {"filename": "paper1.pdf"},
                                {"filename": "paper2.pdf"}
                            ]
                        },
                        "Sub-1.1.2": {
                            "completeness_percent": 30,
                            "contributing_papers": []
                        }
                    }
                }
            }
        }
        
        path = tmp_path / "gap_analysis.json"
        with open(path, 'w') as f:
            json.dump(gap_data, f)
        
        return str(path)
    
    def test_extract_requirements(self, sample_pillar_definitions):
        """Test requirement extraction."""
        tracker = ValidationTracker(sample_pillar_definitions)
        requirements = tracker._extract_requirements_with_strategies()
        
        assert len(requirements) == 2
    
    def test_analyze_coverage(self, sample_pillar_definitions, sample_gap_analysis):
        """Test coverage analysis."""
        tracker = ValidationTracker(
            sample_pillar_definitions,
            gap_analysis_path=sample_gap_analysis
        )
        
        result = tracker.analyze_validation_coverage()
        
        assert "summary" in result
        assert result["summary"]["total_requirements"] == 2
    
    def test_coverage_status_validated(self, sample_pillar_definitions, sample_gap_analysis):
        """Test validated status detection."""
        tracker = ValidationTracker(
            sample_pillar_definitions,
            gap_analysis_path=sample_gap_analysis
        )
        
        tracker.analyze_validation_coverage()
        
        # Sub-1.1.1 has strategy and evidence
        validated_items = [
            item for item in tracker.coverage_items.values()
            if item.requirement_id == "Sub-1.1.1"
        ]
        
        # Should be at least partial since we have evidence
        assert len(validated_items) > 0
    
    def test_no_strategy_detection(self, sample_pillar_definitions):
        """Test no-strategy detection."""
        tracker = ValidationTracker(sample_pillar_definitions)
        tracker.analyze_validation_coverage()
        
        # Sub-1.1.2 has empty validation_strategy
        no_strategy_items = [
            item for item in tracker.coverage_items.values()
            if item.coverage_status == ValidationStatus.NO_STRATEGY
        ]
        
        assert len(no_strategy_items) >= 1
    
    def test_save_matrix(self, sample_pillar_definitions, tmp_path):
        """Test saving matrix to file."""
        tracker = ValidationTracker(sample_pillar_definitions)
        output_path = str(tmp_path / "validation_matrix.json")
        
        matrix = tracker.save_matrix(output_path)
        
        assert Path(output_path).exists()
        with open(output_path) as f:
            saved = json.load(f)
        
        assert saved["summary"]["total_requirements"] == 2
    
    def test_validation_score(self, sample_pillar_definitions):
        """Test validation score calculation."""
        tracker = ValidationTracker(sample_pillar_definitions)
        score = tracker.get_validation_score()
        
        assert 0 <= score <= 100
    
    def test_critical_gaps_identification(self, sample_pillar_definitions):
        """Test critical gap identification."""
        tracker = ValidationTracker(sample_pillar_definitions)
        result = tracker.analyze_validation_coverage()
        
        critical_gaps = result["critical_gaps"]
        
        assert isinstance(critical_gaps, list)
        for gap in critical_gaps:
            assert "recommendation" in gap
            assert "priority" in gap


class TestGenerateValidationMatrix:
    """Tests for the generate_validation_matrix helper function."""
    
    def test_generate_validation_matrix(self, tmp_path):
        """Test the convenience function for generating validation matrix."""
        # Create sample pillar definitions
        definitions = {
            "Pillar 1: Test": {
                "requirements": {
                    "REQ-1.1": [
                        {
                            "id": "Sub-1.1.1",
                            "text": "Test requirement",
                            "validation_strategy": {
                                "method": "unit test",
                                "benchmark_protocol": "pytest",
                                "acceptance_criteria": "100% pass"
                            }
                        }
                    ]
                },
                "validation_criteria": {}
            }
        }
        
        pillar_path = tmp_path / "pillar_definitions.json"
        with open(pillar_path, 'w') as f:
            json.dump(definitions, f)
        
        # Create sample gap analysis
        gap_data = {
            "Pillar 1: Test": {
                "analysis": {
                    "REQ-1.1": {
                        "Sub-1.1.1": {
                            "completeness_percent": 100,
                            "contributing_papers": [{"filename": "test.pdf"}]
                        }
                    }
                }
            }
        }
        
        gap_path = tmp_path / "gap_analysis.json"
        with open(gap_path, 'w') as f:
            json.dump(gap_data, f)
        
        output_path = str(tmp_path / "validation_matrix.json")
        
        # Generate the matrix
        matrix = generate_validation_matrix(
            pillar_definitions_path=str(pillar_path),
            gap_analysis_path=str(gap_path),
            output_path=output_path
        )
        
        assert Path(output_path).exists()
        assert "summary" in matrix
        assert matrix["summary"]["total_requirements"] == 1


class TestOldFormatRequirements:
    """Tests for handling old-format string requirements."""
    
    def test_old_format_requirements(self, tmp_path):
        """Test extracting requirements from old string format."""
        definitions = {
            "Pillar 1: Test": {
                "requirements": {
                    "REQ-1.1: Test Requirement": [
                        "Sub-1.1.1: First sub-requirement",
                        "Sub-1.1.2: Second sub-requirement"
                    ]
                },
                "validation_criteria": {
                    "required_evidence": "test evidence"
                }
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        tracker = ValidationTracker(str(path))
        requirements = tracker._extract_requirements_with_strategies()
        
        assert len(requirements) == 2
        
        # All should have pillar-level validation criteria
        for req_info in requirements.values():
            assert req_info["pillar_validation_criteria"] is not None


class TestCoverageStatus:
    """Tests for coverage status determination."""
    
    def test_no_strategy_no_evidence(self, tmp_path):
        """Test no strategy and no evidence."""
        definitions = {
            "Pillar 1: Test": {
                "requirements": {
                    "REQ-1.1": [
                        {
                            "id": "Sub-1.1.1",
                            "text": "Test",
                            "validation_strategy": {}
                        }
                    ]
                }
                # No validation_criteria
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        tracker = ValidationTracker(str(path))
        tracker.analyze_validation_coverage()
        
        item = list(tracker.coverage_items.values())[0]
        assert item.coverage_status == ValidationStatus.NO_STRATEGY
        assert item.priority == "HIGH"
    
    def test_strategy_but_no_evidence(self, tmp_path):
        """Test strategy defined but no evidence."""
        definitions = {
            "Pillar 1: Test": {
                "requirements": {
                    "REQ-1.1": [
                        {
                            "id": "Sub-1.1.1",
                            "text": "Test",
                            "validation_strategy": {
                                "method": "fMRI comparison"
                            }
                        }
                    ]
                },
                "validation_criteria": {}
            }
        }
        
        path = tmp_path / "pillar_definitions.json"
        with open(path, 'w') as f:
            json.dump(definitions, f)
        
        tracker = ValidationTracker(str(path))
        tracker.analyze_validation_coverage()
        
        item = list(tracker.coverage_items.values())[0]
        assert item.coverage_status == ValidationStatus.UNVALIDATED
        assert item.coverage_level == CoverageLevel.NONE
    
    def test_strategy_with_evidence_partial(self, tmp_path):
        """Test strategy with evidence but partial alignment."""
        definitions = {
            "Pillar 1: Test": {
                "requirements": {
                    "REQ-1.1": [
                        {
                            "id": "Sub-1.1.1",
                            "text": "Test",
                            "validation_strategy": {
                                "method": "fMRI comparison"
                            }
                        }
                    ]
                },
                "validation_criteria": {}
            }
        }
        
        pillar_path = tmp_path / "pillar_definitions.json"
        with open(pillar_path, 'w') as f:
            json.dump(definitions, f)
        
        gap_data = {
            "Pillar 1: Test": {
                "analysis": {
                    "REQ-1.1": {
                        "Sub-1.1.1": {
                            "completeness_percent": 50,
                            "contributing_papers": [{"filename": "paper.pdf"}]
                        }
                    }
                }
            }
        }
        
        gap_path = tmp_path / "gap_analysis.json"
        with open(gap_path, 'w') as f:
            json.dump(gap_data, f)
        
        tracker = ValidationTracker(
            str(pillar_path),
            gap_analysis_path=str(gap_path)
        )
        tracker.analyze_validation_coverage()
        
        item = list(tracker.coverage_items.values())[0]
        # Should be PARTIAL since we have evidence but no method alignment
        assert item.coverage_status == ValidationStatus.PARTIAL
        assert item.coverage_level == CoverageLevel.PARTIAL
