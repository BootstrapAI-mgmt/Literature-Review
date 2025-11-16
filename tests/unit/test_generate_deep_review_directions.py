"""
Unit tests for generate_deep_review_directions.py

Tests the helper script functionality for generating Deep Review directions.
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
import sys
import subprocess

# Get the root directory
ROOT_DIR = Path(__file__).parent.parent.parent
SCRIPT_PATH = ROOT_DIR / 'scripts' / 'generate_deep_review_directions.py'

# Add scripts directory to path for direct imports
sys.path.insert(0, str(ROOT_DIR / 'scripts'))

# Import the functions we need to test
import importlib.util
spec = importlib.util.spec_from_file_location("generate_deep_review_directions", SCRIPT_PATH)
gen_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen_module)

identify_high_priority_gaps = gen_module.identify_high_priority_gaps
calculate_priority_score = gen_module.calculate_priority_score
generate_directions = gen_module.generate_directions


@pytest.fixture
def sample_gap_report():
    """Sample gap analysis report for testing."""
    return {
        "Pillar 1: Test Pillar": {
            "completeness": 25.0,
            "analysis": {
                "REQ-1.1: Test Requirement": {
                    "Sub-1.1.1: High priority gap": {
                        "completeness_percent": 10,
                        "gap_analysis": "Major gap requiring Deep Review",
                        "confidence_level": "high",
                        "contributing_papers": [
                            {"filename": "paper1.pdf"},
                            {"filename": "paper2.pdf"}
                        ],
                        "description": "Test gap 1"
                    },
                    "Sub-1.1.2: Low priority gap": {
                        "completeness_percent": 80,
                        "gap_analysis": "Minor gap",
                        "confidence_level": "medium",
                        "contributing_papers": [
                            {"filename": "paper3.pdf"}
                        ],
                        "description": "Test gap 2"
                    },
                    "Sub-1.1.3: No papers gap": {
                        "completeness_percent": 5,
                        "gap_analysis": "Critical gap with no papers",
                        "confidence_level": "high",
                        "contributing_papers": [],
                        "description": "Test gap 3"
                    },
                    "Sub-1.1.4: Low confidence gap": {
                        "completeness_percent": 20,
                        "gap_analysis": "Uncertain gap",
                        "confidence_level": "low",
                        "contributing_papers": [
                            {"filename": "paper4.pdf"}
                        ],
                        "description": "Test gap 4"
                    }
                }
            }
        },
        "Pillar 2: Another Pillar": {
            "completeness": 30.0,
            "analysis": {
                "REQ-2.1: Another Requirement": {
                    "Sub-2.1.1: Another gap": {
                        "completeness_percent": 30,
                        "gap_analysis": "Medium priority gap",
                        "confidence_level": "medium",
                        "contributing_papers": [
                            {"filename": "paper5.pdf"}
                        ],
                        "description": "Test gap 5"
                    }
                }
            }
        }
    }


class TestIdentifyHighPriorityGaps:
    """Test gap identification logic."""
    
    def test_basic_filtering(self, sample_gap_report):
        """Test basic gap filtering with default criteria."""
        criteria = {
            'completeness_max': 50,
            'has_papers': True,
            'min_confidence': 'medium'
        }
        
        gaps = identify_high_priority_gaps(sample_gap_report, criteria)
        
        # Should find gaps that meet criteria
        assert len(gaps) > 0
        
        # All gaps should meet completeness criteria
        for gap in gaps:
            assert gap['completeness'] <= 50
        
        # All gaps should have papers
        for gap in gaps:
            assert gap['paper_count'] > 0
    
    def test_pillar_filter(self, sample_gap_report):
        """Test filtering by specific pillar."""
        criteria = {
            'pillar': 'Pillar 1: Test Pillar',
            'completeness_max': 50,
            'has_papers': True,
            'min_confidence': 'medium'
        }
        
        gaps = identify_high_priority_gaps(sample_gap_report, criteria)
        
        # All gaps should be from Pillar 1
        for gap in gaps:
            assert gap['pillar'] == 'Pillar 1: Test Pillar'
    
    def test_completeness_threshold(self, sample_gap_report):
        """Test completeness threshold filtering."""
        criteria = {
            'completeness_max': 20,
            'has_papers': True,
            'min_confidence': 'medium'
        }
        
        gaps = identify_high_priority_gaps(sample_gap_report, criteria)
        
        # All gaps should be <= 20% complete
        for gap in gaps:
            assert gap['completeness'] <= 20
    
    def test_paper_requirement(self, sample_gap_report):
        """Test that gaps without papers are filtered out."""
        criteria = {
            'completeness_max': 50,
            'has_papers': True,
            'min_confidence': 'medium'
        }
        
        gaps = identify_high_priority_gaps(sample_gap_report, criteria)
        
        # No gap should have 0 papers
        for gap in gaps:
            assert gap['paper_count'] > 0
            assert len(gap['contributing_papers']) > 0
    
    def test_confidence_filtering(self, sample_gap_report):
        """Test confidence level filtering."""
        criteria = {
            'completeness_max': 50,
            'has_papers': True,
            'min_confidence': 'high'
        }
        
        gaps = identify_high_priority_gaps(sample_gap_report, criteria)
        
        # All gaps should have high confidence
        for gap in gaps:
            assert gap['confidence'] == 'high'


class TestCalculatePriorityScore:
    """Test priority scoring algorithm."""
    
    def test_completeness_factor(self):
        """Test that lower completeness yields higher priority."""
        score_0_percent = calculate_priority_score(0, 2, "Pillar 1", {})
        score_50_percent = calculate_priority_score(50, 2, "Pillar 1", {})
        
        assert score_0_percent > score_50_percent
    
    def test_paper_count_factor(self):
        """Test that more papers yield higher priority."""
        score_1_paper = calculate_priority_score(20, 1, "Pillar 1", {})
        score_3_papers = calculate_priority_score(20, 3, "Pillar 1", {})
        
        assert score_3_papers > score_1_paper
    
    def test_foundational_pillar_bonus(self):
        """Test that foundational pillars get priority bonus."""
        score_foundational = calculate_priority_score(20, 2, "Pillar 1", {})
        score_regular = calculate_priority_score(20, 2, "Pillar 2", {})
        
        # Pillar 1 is foundational
        assert score_foundational > score_regular
    
    def test_bottleneck_bonus(self):
        """Test that bottlenecks get priority bonus."""
        score_bottleneck = calculate_priority_score(20, 2, "Pillar 1", {"is_bottleneck": True})
        score_regular = calculate_priority_score(20, 2, "Pillar 1", {"is_bottleneck": False})
        
        assert score_bottleneck > score_regular


class TestGenerateDirections:
    """Test direction file generation."""
    
    def test_generate_directions_structure(self, tmp_path):
        """Test that generated directions have correct structure."""
        gaps = [
            {
                'sub_req': 'Sub-1.1.1',
                'pillar': 'Pillar 1',
                'requirement': 'REQ-1.1',
                'description': 'Test gap',
                'completeness': 10,
                'contributing_papers': ['paper1.pdf', 'paper2.pdf'],
                'priority_score': 85,
                'gap_analysis': 'Test analysis'
            }
        ]
        
        output_file = tmp_path / "test_directions.json"
        generate_directions(gaps, str(output_file))
        
        # File should exist
        assert output_file.exists()
        
        # Load and verify structure
        with open(output_file, 'r') as f:
            directions = json.load(f)
        
        assert 'Sub-1.1.1' in directions
        assert directions['Sub-1.1.1']['pillar'] == 'Pillar 1'
        assert directions['Sub-1.1.1']['requirement'] == 'REQ-1.1'
        assert directions['Sub-1.1.1']['current_completeness'] == 10
        assert directions['Sub-1.1.1']['priority'] == 'HIGH'
        assert len(directions['Sub-1.1.1']['contributing_papers']) == 2
    
    def test_priority_classification(self, tmp_path):
        """Test HIGH vs MEDIUM priority classification."""
        gaps = [
            {
                'sub_req': 'High-Priority',
                'pillar': 'Pillar 1',
                'requirement': 'REQ-1.1',
                'description': 'High priority gap',
                'completeness': 5,
                'contributing_papers': ['paper1.pdf'],
                'priority_score': 85,  # >= 80
                'gap_analysis': 'Test'
            },
            {
                'sub_req': 'Medium-Priority',
                'pillar': 'Pillar 1',
                'requirement': 'REQ-1.1',
                'description': 'Medium priority gap',
                'completeness': 30,
                'contributing_papers': ['paper2.pdf'],
                'priority_score': 50,  # < 80
                'gap_analysis': 'Test'
            }
        ]
        
        output_file = tmp_path / "test_directions.json"
        generate_directions(gaps, str(output_file))
        
        with open(output_file, 'r') as f:
            directions = json.load(f)
        
        assert directions['High-Priority']['priority'] == 'HIGH'
        assert directions['Medium-Priority']['priority'] == 'MEDIUM'


class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_full_workflow(self, sample_gap_report, tmp_path):
        """Test complete workflow from gap report to directions."""
        criteria = {
            'completeness_max': 50,
            'has_papers': True,
            'min_confidence': 'medium'
        }
        
        # Identify gaps
        gaps = identify_high_priority_gaps(sample_gap_report, criteria)
        assert len(gaps) > 0
        
        # Sort by priority
        gaps.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Select top 3
        top_gaps = gaps[:3]
        
        # Generate directions
        output_file = tmp_path / "directions.json"
        generate_directions(top_gaps, str(output_file))
        
        # Verify output
        assert output_file.exists()
        with open(output_file, 'r') as f:
            directions = json.load(f)
        
        assert len(directions) <= 3
        
        # Verify all required fields are present
        for sub_req, data in directions.items():
            assert 'pillar' in data
            assert 'requirement' in data
            assert 'current_completeness' in data
            assert 'contributing_papers' in data
            assert 'priority' in data
            assert 'gap_analysis' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
