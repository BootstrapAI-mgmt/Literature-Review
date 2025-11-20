"""Unit tests for gap_analyzer module - Gap Extraction & Analysis Engine."""

import pytest
import json
from pathlib import Path

from literature_review.analysis.gap_analyzer import (
    GapAnalyzer, 
    Gap, 
    extract_gaps_from_file
)


@pytest.fixture
def sample_report():
    """Sample gap analysis report."""
    return {
        'pillars': {
            'Pillar 1: Foundational Architecture': {
                'requirements': {
                    'REQ-001': {
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Implement spike-based learning',
                                'completeness_percent': 25.0,
                                'evidence': [{'filename': 'paper1.pdf'}],
                                'suggested_searches': ['spike-timing plasticity']
                            },
                            'SUB-002': {
                                'text': 'Implement STDP mechanism',
                                'completeness_percent': 85.0,
                                'evidence': [
                                    {'filename': 'paper1.pdf'},
                                    {'filename': 'paper2.pdf'},
                                    {'filename': 'paper3.pdf'}
                                ]
                            }
                        }
                    }
                }
            },
            'Pillar 2: Technical Implementation': {
                'requirements': {
                    'REQ-002': {
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Hardware acceleration',
                                'completeness_percent': 60.0,
                                'evidence': [{'filename': 'paper4.pdf'}]
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def empty_report():
    """Empty gap analysis report."""
    return {
        'pillars': {}
    }


@pytest.fixture
def report_with_no_gaps():
    """Report where all sub-requirements meet threshold."""
    return {
        'pillars': {
            'Pillar 1': {
                'requirements': {
                    'REQ-001': {
                        'sub_requirements': {
                            'SUB-001': {
                                'text': 'Complete requirement',
                                'completeness_percent': 95.0,
                                'evidence': [
                                    {'filename': 'paper1.pdf'},
                                    {'filename': 'paper2.pdf'}
                                ]
                            }
                        }
                    }
                }
            }
        }
    }


class TestGapDataclass:
    """Tests for the Gap dataclass."""
    
    def test_gap_creation(self):
        """Test basic Gap object creation."""
        gap = Gap(
            pillar="Pillar 1",
            requirement_id="REQ-001",
            sub_requirement_id="SUB-001",
            requirement_text="Test requirement",
            current_completeness=50.0,
            evidence_count=2,
            severity="MEDIUM",
            suggested_searches=["search1", "search2"]
        )
        
        assert gap.pillar == "Pillar 1"
        assert gap.requirement_id == "REQ-001"
        assert gap.sub_requirement_id == "SUB-001"
        assert gap.requirement_text == "Test requirement"
        assert gap.current_completeness == 50.0
        assert gap.evidence_count == 2
        assert gap.severity == "MEDIUM"
        assert gap.suggested_searches == ["search1", "search2"]
    
    def test_gap_id_property(self):
        """Test Gap.gap_id property."""
        gap = Gap(
            pillar="Pillar 1",
            requirement_id="REQ-001",
            sub_requirement_id="SUB-002",
            requirement_text="Test",
            current_completeness=50.0,
            evidence_count=1,
            severity="MEDIUM"
        )
        assert gap.gap_id == "REQ-001-SUB-002"
    
    def test_gap_percentage_property(self):
        """Test Gap.gap_percentage property."""
        gap = Gap(
            pillar="Pillar 1",
            requirement_id="REQ-001",
            sub_requirement_id="SUB-001",
            requirement_text="Test",
            current_completeness=30.0,
            evidence_count=1,
            severity="CRITICAL"
        )
        assert gap.gap_percentage == 70.0
    
    def test_gap_default_suggested_searches(self):
        """Test that suggested_searches defaults to empty list."""
        gap = Gap(
            pillar="Pillar 1",
            requirement_id="REQ-001",
            sub_requirement_id="SUB-001",
            requirement_text="Test",
            current_completeness=50.0,
            evidence_count=1,
            severity="MEDIUM"
        )
        assert gap.suggested_searches == []


class TestGapAnalyzerInit:
    """Tests for GapAnalyzer initialization."""
    
    def test_default_initialization(self):
        """Test default initialization."""
        analyzer = GapAnalyzer()
        assert analyzer.completeness_threshold == 0.8
        assert not analyzer.decay_enabled
        assert analyzer.decay_tracker is None
    
    def test_custom_threshold(self):
        """Test initialization with custom threshold."""
        analyzer = GapAnalyzer(completeness_threshold=0.7)
        assert analyzer.completeness_threshold == 0.7
    
    def test_severity_thresholds(self):
        """Test severity thresholds are correctly set."""
        analyzer = GapAnalyzer()
        assert analyzer.severity_thresholds["CRITICAL"] == 0.3
        assert analyzer.severity_thresholds["HIGH"] == 0.5
        assert analyzer.severity_thresholds["MEDIUM"] == 0.7
        assert analyzer.severity_thresholds["LOW"] == 0.8


class TestClassifyGapSeverity:
    """Tests for classify_gap_severity method."""
    
    def test_critical_severity(self):
        """Test CRITICAL severity classification."""
        analyzer = GapAnalyzer()
        assert analyzer.classify_gap_severity(0.1) == "CRITICAL"
        assert analyzer.classify_gap_severity(0.29) == "CRITICAL"
    
    def test_high_severity(self):
        """Test HIGH severity classification."""
        analyzer = GapAnalyzer()
        assert analyzer.classify_gap_severity(0.3) == "HIGH"
        assert analyzer.classify_gap_severity(0.4) == "HIGH"
        assert analyzer.classify_gap_severity(0.49) == "HIGH"
    
    def test_medium_severity(self):
        """Test MEDIUM severity classification."""
        analyzer = GapAnalyzer()
        assert analyzer.classify_gap_severity(0.5) == "MEDIUM"
        assert analyzer.classify_gap_severity(0.6) == "MEDIUM"
        assert analyzer.classify_gap_severity(0.69) == "MEDIUM"
    
    def test_low_severity(self):
        """Test LOW severity classification."""
        analyzer = GapAnalyzer()
        assert analyzer.classify_gap_severity(0.7) == "LOW"
        assert analyzer.classify_gap_severity(0.75) == "LOW"
        assert analyzer.classify_gap_severity(0.79) == "LOW"


class TestExtractGaps:
    """Tests for extract_gaps method."""
    
    def test_extract_gaps_default_threshold(self, sample_report):
        """Test gap extraction with default 80% threshold."""
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(sample_report)
        
        # Should find 2 gaps: SUB-001 (25%) and REQ-002-SUB-001 (60%)
        assert len(gaps) == 2
        assert gaps[0].current_completeness == 25.0
        assert gaps[1].current_completeness == 60.0
    
    def test_extract_gaps_custom_threshold(self, sample_report):
        """Test gap extraction with custom threshold."""
        analyzer = GapAnalyzer(completeness_threshold=0.5)
        gaps = analyzer.extract_gaps(sample_report)
        
        # Should find only 1 gap: SUB-001 (25%)
        assert len(gaps) == 1
        assert gaps[0].current_completeness == 25.0
    
    def test_extract_gaps_override_threshold(self, sample_report):
        """Test gap extraction with override threshold parameter."""
        analyzer = GapAnalyzer(completeness_threshold=0.8)
        gaps = analyzer.extract_gaps(sample_report, threshold=0.3)
        
        # Should find only 1 gap: SUB-001 (25%)
        assert len(gaps) == 1
        assert gaps[0].current_completeness == 25.0
    
    def test_extract_gaps_empty_report(self, empty_report):
        """Test gap extraction from empty report."""
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(empty_report)
        assert len(gaps) == 0
    
    def test_extract_gaps_no_gaps(self, report_with_no_gaps):
        """Test gap extraction when no gaps exist."""
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(report_with_no_gaps)
        assert len(gaps) == 0
    
    def test_gap_fields_populated(self, sample_report):
        """Test that all gap fields are correctly populated."""
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(sample_report)
        
        # Check first gap
        gap = gaps[0]
        assert gap.pillar == 'Pillar 1: Foundational Architecture'
        assert gap.requirement_id == 'REQ-001'
        assert gap.sub_requirement_id == 'SUB-001'
        assert gap.requirement_text == 'Implement spike-based learning'
        assert gap.current_completeness == 25.0
        assert gap.evidence_count == 1
        assert gap.severity == 'CRITICAL'
        assert gap.suggested_searches == ['spike-timing plasticity']
    
    def test_gaps_sorted_by_severity(self, sample_report):
        """Test that gaps are sorted by severity (critical first)."""
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(sample_report)
        
        # First gap should be CRITICAL (25%)
        assert gaps[0].severity == 'CRITICAL'
        # Second gap should be MEDIUM (60%)
        assert gaps[1].severity == 'MEDIUM'
    
    def test_gaps_sorted_by_completeness_within_severity(self):
        """Test that gaps with same severity are sorted by completeness."""
        report = {
            'pillars': {
                'Pillar 1': {
                    'requirements': {
                        'REQ-001': {
                            'sub_requirements': {
                                'SUB-001': {
                                    'text': 'Test 1',
                                    'completeness_percent': 75.0,
                                    'evidence': []
                                },
                                'SUB-002': {
                                    'text': 'Test 2',
                                    'completeness_percent': 72.0,
                                    'evidence': []
                                }
                            }
                        }
                    }
                }
            }
        }
        
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(report)
        
        # Both are LOW severity, should be sorted by completeness
        assert gaps[0].current_completeness == 72.0
        assert gaps[1].current_completeness == 75.0


class TestGenerateGapSummary:
    """Tests for generate_gap_summary method."""
    
    def test_generate_gap_summary(self, sample_report):
        """Test gap summary generation."""
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(sample_report)
        summary = analyzer.generate_gap_summary(gaps)
        
        assert summary['total_gaps'] == 2
        assert summary['by_severity']['CRITICAL'] == 1  # 25%
        assert summary['by_severity']['MEDIUM'] == 1    # 60%
        assert summary['by_severity']['HIGH'] == 0
        assert summary['by_severity']['LOW'] == 0
        assert summary['average_completeness'] == 42.5  # (25 + 60) / 2
    
    def test_summary_by_pillar(self, sample_report):
        """Test summary by pillar breakdown."""
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(sample_report)
        summary = analyzer.generate_gap_summary(gaps)
        
        assert summary['by_pillar']['Pillar 1: Foundational Architecture'] == 1
        assert summary['by_pillar']['Pillar 2: Technical Implementation'] == 1
    
    def test_summary_extremes(self, sample_report):
        """Test most/least incomplete gap identification."""
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(sample_report)
        summary = analyzer.generate_gap_summary(gaps)
        
        assert summary['most_incomplete'].current_completeness == 25.0
        assert summary['least_incomplete'].current_completeness == 60.0
    
    def test_summary_empty_gaps(self):
        """Test summary generation with empty gap list."""
        analyzer = GapAnalyzer()
        summary = analyzer.generate_gap_summary([])
        
        assert summary['total_gaps'] == 0
        assert summary['by_severity']['CRITICAL'] == 0
        assert summary['average_completeness'] == 0.0
        assert summary['most_incomplete'] is None
        assert summary['least_incomplete'] is None


class TestLoadReport:
    """Tests for load_report method."""
    
    def test_load_report_success(self, tmp_path, sample_report):
        """Test successful report loading."""
        report_path = tmp_path / "gap_analysis_report.json"
        with open(report_path, 'w') as f:
            json.dump(sample_report, f)
        
        analyzer = GapAnalyzer()
        loaded_report = analyzer.load_report(str(report_path))
        
        assert loaded_report == sample_report
    
    def test_load_report_file_not_found(self):
        """Test error when report file doesn't exist."""
        analyzer = GapAnalyzer()
        
        with pytest.raises(FileNotFoundError, match="Gap analysis report not found"):
            analyzer.load_report("/nonexistent/path/report.json")
    
    def test_load_report_invalid_json(self, tmp_path):
        """Test error when report is not valid JSON."""
        report_path = tmp_path / "invalid.json"
        with open(report_path, 'w') as f:
            f.write("{ invalid json }")
        
        analyzer = GapAnalyzer()
        
        with pytest.raises(json.JSONDecodeError):
            analyzer.load_report(str(report_path))


class TestExportGapsJson:
    """Tests for export_gaps_json method."""
    
    def test_export_gaps_json(self, tmp_path, sample_report):
        """Test gap export to JSON."""
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(sample_report)
        
        output_path = tmp_path / "gaps.json"
        analyzer.export_gaps_json(gaps, str(output_path))
        
        assert output_path.exists()
        
        with open(output_path) as f:
            exported = json.load(f)
        
        assert len(exported) == 2
        assert exported[0]['gap_id'] == "REQ-001-SUB-001"
        assert exported[0]['current_completeness'] == 25.0
        assert exported[0]['gap_percentage'] == 75.0
        assert exported[0]['severity'] == 'CRITICAL'
    
    def test_export_gaps_json_all_fields(self, tmp_path, sample_report):
        """Test that all fields are exported."""
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(sample_report)
        
        output_path = tmp_path / "gaps.json"
        analyzer.export_gaps_json(gaps, str(output_path))
        
        with open(output_path) as f:
            exported = json.load(f)
        
        gap = exported[0]
        assert 'gap_id' in gap
        assert 'pillar' in gap
        assert 'requirement_id' in gap
        assert 'sub_requirement_id' in gap
        assert 'requirement_text' in gap
        assert 'current_completeness' in gap
        assert 'gap_percentage' in gap
        assert 'evidence_count' in gap
        assert 'severity' in gap
        assert 'suggested_searches' in gap


class TestExtractGapsFromFile:
    """Tests for extract_gaps_from_file convenience function."""
    
    def test_extract_gaps_from_file(self, tmp_path, sample_report):
        """Test convenience function for file-based extraction."""
        report_path = tmp_path / "gap_analysis_report.json"
        with open(report_path, 'w') as f:
            json.dump(sample_report, f)
        
        gaps = extract_gaps_from_file(str(report_path))
        
        assert len(gaps) == 2
        assert gaps[0].current_completeness == 25.0
    
    def test_extract_gaps_from_file_custom_threshold(self, tmp_path, sample_report):
        """Test convenience function with custom threshold."""
        report_path = tmp_path / "gap_analysis_report.json"
        with open(report_path, 'w') as f:
            json.dump(sample_report, f)
        
        gaps = extract_gaps_from_file(str(report_path), threshold=0.5)
        
        assert len(gaps) == 1
        assert gaps[0].current_completeness == 25.0


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_missing_completeness_percent(self):
        """Test handling of missing completeness_percent field."""
        report = {
            'pillars': {
                'Pillar 1': {
                    'requirements': {
                        'REQ-001': {
                            'sub_requirements': {
                                'SUB-001': {
                                    'text': 'Test',
                                    # Missing completeness_percent
                                    'evidence': []
                                }
                            }
                        }
                    }
                }
            }
        }
        
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(report)
        
        # Should treat missing as 0% and create a gap
        assert len(gaps) == 1
        assert gaps[0].current_completeness == 0.0
    
    def test_missing_evidence_list(self):
        """Test handling of missing evidence field."""
        report = {
            'pillars': {
                'Pillar 1': {
                    'requirements': {
                        'REQ-001': {
                            'sub_requirements': {
                                'SUB-001': {
                                    'text': 'Test',
                                    'completeness_percent': 50.0
                                    # Missing evidence
                                }
                            }
                        }
                    }
                }
            }
        }
        
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(report)
        
        assert len(gaps) == 1
        assert gaps[0].evidence_count == 0
    
    def test_missing_suggested_searches(self):
        """Test handling of missing suggested_searches field."""
        report = {
            'pillars': {
                'Pillar 1': {
                    'requirements': {
                        'REQ-001': {
                            'sub_requirements': {
                                'SUB-001': {
                                    'text': 'Test',
                                    'completeness_percent': 50.0,
                                    'evidence': []
                                    # Missing suggested_searches
                                }
                            }
                        }
                    }
                }
            }
        }
        
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(report)
        
        assert len(gaps) == 1
        assert gaps[0].suggested_searches == []
    
    def test_missing_text_field(self):
        """Test handling of missing text field."""
        report = {
            'pillars': {
                'Pillar 1': {
                    'requirements': {
                        'REQ-001': {
                            'sub_requirements': {
                                'SUB-001': {
                                    # Missing text
                                    'completeness_percent': 50.0,
                                    'evidence': []
                                }
                            }
                        }
                    }
                }
            }
        }
        
        analyzer = GapAnalyzer()
        gaps = analyzer.extract_gaps(report)
        
        assert len(gaps) == 1
        assert gaps[0].requirement_text == 'N/A'


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with decay integration."""
    
    def test_decay_config_still_works(self):
        """Test that existing decay configuration still works."""
        config = {
            'evidence_decay': {
                'weight_in_gap_analysis': True,
                'decay_weight': 0.7
            }
        }
        
        analyzer = GapAnalyzer(config=config)
        assert analyzer.decay_enabled is True
        assert analyzer.decay_weight == 0.7
    
    def test_apply_decay_weighting_still_works(self):
        """Test that apply_decay_weighting method still works."""
        analyzer = GapAnalyzer()
        papers = [{'filename': 'test.pdf', 'estimated_contribution_percent': 80}]
        
        score, metadata = analyzer.apply_decay_weighting(80.0, papers)
        
        # Without decay enabled, should return original score
        assert score == 80.0
        assert metadata['decay_applied'] is False
