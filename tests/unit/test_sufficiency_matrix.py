"""Unit tests for sufficiency_matrix module."""

import json
import os
import tempfile
import pytest
from literature_review.analysis.sufficiency_matrix import (
    SufficiencyMatrixAnalyzer,
    generate_sufficiency_report
)


@pytest.fixture
def sample_gap_report():
    """Sample gap report for testing."""
    return {
        "Pillar 1: Biological Stimulus-Response": {
            "completeness": 50.0,
            "analysis": {
                "REQ-B1.1": {
                    "Sub-1.1.1": {
                        "completeness_percent": 80,
                        "contributing_papers": [
                            {"filename": "paper1.pdf", "estimated_contribution_percent": 80, "contribution_summary": "Test 1"},
                            {"filename": "paper2.pdf", "estimated_contribution_percent": 90, "contribution_summary": "Test 2"}
                        ]
                    },
                    "Sub-1.1.2": {
                        "completeness_percent": 0,
                        "contributing_papers": []
                    },
                    "Sub-1.1.3": {
                        "completeness_percent": 50,
                        "contributing_papers": [
                            {"filename": "paper3.pdf", "estimated_contribution_percent": 50, "contribution_summary": "Test 3"}
                        ]
                    }
                }
            }
        },
        "Pillar 2: AI Stimulus-Response": {
            "completeness": 60.0,
            "analysis": {
                "REQ-A2.1": {
                    "Sub-2.1.1": {
                        "completeness_percent": 60,
                        "contributing_papers": [
                            {"filename": "paper4.pdf", "estimated_contribution_percent": 30, "contribution_summary": "Test 4"},
                            {"filename": "paper5.pdf", "estimated_contribution_percent": 20, "contribution_summary": "Test 5"}
                        ]
                    },
                    "Sub-2.1.2": {
                        "completeness_percent": 70,
                        "contributing_papers": [
                            {"filename": f"paper{i}.pdf", "estimated_contribution_percent": 75, "contribution_summary": f"Test {i}"}
                            for i in range(10)
                        ]
                    }
                }
            }
        }
    }


class TestSufficiencyMatrixAnalyzer:
    """Test SufficiencyMatrixAnalyzer class."""
    
    def test_initialization(self, sample_gap_report, tmp_path):
        """Test analyzer initialization."""
        # Create temp file with sample data
        gap_file = tmp_path / "gap_analysis.json"
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_report, f)
        
        analyzer = SufficiencyMatrixAnalyzer(str(gap_file))
        assert analyzer.gap_data == sample_gap_report
    
    def test_categorize_quantity(self, sample_gap_report, tmp_path):
        """Test quantity categorization."""
        gap_file = tmp_path / "gap_analysis.json"
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_report, f)
        
        analyzer = SufficiencyMatrixAnalyzer(str(gap_file))
        
        assert analyzer._categorize_quantity(2) == 'low'
        assert analyzer._categorize_quantity(3) == 'medium'
        assert analyzer._categorize_quantity(5) == 'medium'
        assert analyzer._categorize_quantity(8) == 'medium'
        assert analyzer._categorize_quantity(9) == 'high'
        assert analyzer._categorize_quantity(20) == 'high'
    
    def test_categorize_quality(self, sample_gap_report, tmp_path):
        """Test quality categorization."""
        gap_file = tmp_path / "gap_analysis.json"
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_report, f)
        
        analyzer = SufficiencyMatrixAnalyzer(str(gap_file))
        
        assert analyzer._categorize_quality(0.3) == 'low'
        assert analyzer._categorize_quality(0.4) == 'medium'
        assert analyzer._categorize_quality(0.5) == 'medium'
        assert analyzer._categorize_quality(0.7) == 'medium'
        assert analyzer._categorize_quality(0.71) == 'high'
        assert analyzer._categorize_quality(0.9) == 'high'
    
    def test_assign_quadrant(self, sample_gap_report, tmp_path):
        """Test quadrant assignment logic."""
        gap_file = tmp_path / "gap_analysis.json"
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_report, f)
        
        analyzer = SufficiencyMatrixAnalyzer(str(gap_file))
        
        # Q1: Strong Foundation
        assert analyzer._assign_quadrant('high', 'high') == 'Q1_Strong_Foundation'
        
        # Q2: Promising Seeds
        assert analyzer._assign_quadrant('low', 'high') == 'Q2_Promising_Seeds'
        assert analyzer._assign_quadrant('medium', 'high') == 'Q2_Promising_Seeds'
        
        # Q3: Critical Gap
        assert analyzer._assign_quadrant('low', 'low') == 'Q3_Critical_Gap'
        assert analyzer._assign_quadrant('low', 'medium') == 'Q3_Critical_Gap'
        assert analyzer._assign_quadrant('medium', 'low') == 'Q3_Critical_Gap'
        assert analyzer._assign_quadrant('medium', 'medium') == 'Q3_Critical_Gap'
        
        # Q4: Hollow Coverage
        assert analyzer._assign_quadrant('high', 'low') == 'Q4_Hollow_Coverage'
        assert analyzer._assign_quadrant('high', 'medium') == 'Q4_Hollow_Coverage'
    
    def test_calculate_avg_alignment(self, sample_gap_report, tmp_path):
        """Test alignment score calculation."""
        gap_file = tmp_path / "gap_analysis.json"
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_report, f)
        
        analyzer = SufficiencyMatrixAnalyzer(str(gap_file))
        
        # Test with multiple papers
        papers = [
            {"estimated_contribution_percent": 80},
            {"estimated_contribution_percent": 90}
        ]
        assert abs(analyzer._calculate_avg_alignment(papers) - 0.85) < 0.001
        
        # Test with single paper
        papers = [{"estimated_contribution_percent": 50}]
        assert analyzer._calculate_avg_alignment(papers) == 0.5
        
        # Test with no papers
        assert analyzer._calculate_avg_alignment([]) == 0.0
    
    def test_analyze_sufficiency(self, sample_gap_report, tmp_path):
        """Test complete sufficiency analysis."""
        gap_file = tmp_path / "gap_analysis.json"
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_report, f)
        
        analyzer = SufficiencyMatrixAnalyzer(str(gap_file))
        report = analyzer.analyze_sufficiency()
        
        # Check structure
        assert 'summary' in report
        assert 'requirement_analysis' in report
        assert 'quadrant_groups' in report
        assert 'recommendations' in report
        assert 'matrix_visualization' in report
        
        # Check summary
        assert 'total_requirements_analyzed' in report['summary']
        assert 'quadrant_distribution' in report['summary']
        
        # Should have analyzed requirements with papers (3-4 with papers in this sample)
        assert report['summary']['total_requirements_analyzed'] >= 3
        assert report['summary']['total_requirements_analyzed'] <= 4
        
        # Check that we have some quadrant assignments
        assert len(report['quadrant_groups']) > 0
    
    def test_generate_recommendations(self, sample_gap_report, tmp_path):
        """Test recommendations generation."""
        gap_file = tmp_path / "gap_analysis.json"
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_report, f)
        
        analyzer = SufficiencyMatrixAnalyzer(str(gap_file))
        report = analyzer.analyze_sufficiency()
        
        # Should have recommendations for non-empty quadrants
        assert 'recommendations' in report
        assert isinstance(report['recommendations'], dict)
        
        # Each recommendation list should have items
        for quadrant, recs in report['recommendations'].items():
            assert isinstance(recs, list)
            assert len(recs) > 0


def test_generate_sufficiency_report(sample_gap_report, tmp_path):
    """Test report generation function."""
    gap_file = tmp_path / "gap_analysis.json"
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_report, f)
    
    output_file = tmp_path / "sufficiency_matrix.json"
    
    report = generate_sufficiency_report(
        gap_analysis_file=str(gap_file),
        output_file=str(output_file)
    )
    
    # Check report was created
    assert output_file.exists()
    
    # Check report structure
    assert 'summary' in report
    assert 'requirement_analysis' in report
    assert 'quadrant_groups' in report
    
    # Verify file contents
    with open(output_file, 'r') as f:
        saved_report = json.load(f)
    
    assert saved_report == report


def test_matrix_visualization_data(sample_gap_report, tmp_path):
    """Test matrix visualization data structure."""
    gap_file = tmp_path / "gap_analysis.json"
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_report, f)
    
    analyzer = SufficiencyMatrixAnalyzer(str(gap_file))
    report = analyzer.analyze_sufficiency()
    
    viz_data = report['matrix_visualization']
    
    # Check structure
    assert 'requirements' in viz_data
    assert 'quadrants' in viz_data
    
    # Check requirements data
    for req in viz_data['requirements']:
        assert 'id' in req
        assert 'requirement' in req
        assert 'pillar' in req
        assert 'x' in req  # quantity
        assert 'y' in req  # quality
        assert 'quadrant' in req
        assert 'papers' in req
    
    # Check quadrants config
    assert len(viz_data['quadrants']) == 4
    for quadrant, config in viz_data['quadrants'].items():
        assert 'color' in config
