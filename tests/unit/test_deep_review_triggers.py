"""Unit tests for Deep Review Trigger System."""

import json
import os
import tempfile
import pytest
from literature_review.triggers.deep_review_triggers import (
    DeepReviewTriggerEngine,
    generate_trigger_report
)


@pytest.fixture
def mock_gap_analysis():
    """Create mock gap analysis data."""
    return {
        "Pillar 1: Biological Stimulus-Response": {
            "completeness": 7.5,
            "analysis": {
                "REQ-B1.1: Sensory Transduction": {
                    "Sub-1.1.1: Critical gap requirement": {
                        "completeness_percent": 0,
                        "gap_analysis": "No coverage",
                        "contributing_papers": []
                    },
                    "Sub-1.1.2: High gap requirement": {
                        "completeness_percent": 40,
                        "gap_analysis": "Partial coverage",
                        "contributing_papers": [
                            {"filename": "paper1.pdf", "estimated_contribution_percent": 40}
                        ]
                    },
                    "Sub-1.1.3: Medium gap requirement": {
                        "completeness_percent": 60,
                        "gap_analysis": "Good coverage",
                        "contributing_papers": []
                    },
                    "Sub-1.1.4: Low gap requirement": {
                        "completeness_percent": 80,
                        "gap_analysis": "Excellent coverage",
                        "contributing_papers": []
                    }
                }
            }
        },
        "Pillar 2: AI Stimulus-Response": {
            "completeness": 5.0,
            "analysis": {
                "REQ-A1.1: AI Architecture": {
                    "Sub-2.1.1: SNN requirement": {
                        "completeness_percent": 20,
                        "gap_analysis": "Low coverage",
                        "contributing_papers": []
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_review_log():
    """Create mock review log data."""
    return {
        "paper1.pdf": {
            "metadata": {"title": "High Quality Paper Addressing Critical Gap"},
            "judge_analysis": {
                "overall_alignment": 0.85,
                "pillar_contributions": [
                    {
                        "pillar_name": "Pillar 1: Biological Stimulus-Response",
                        "sub_requirements_addressed": [
                            {"requirement_id": "Sub-1.1.1: Critical gap requirement"}
                        ]
                    }
                ]
            }
        },
        "paper2.pdf": {
            "metadata": {"title": "Medium Quality Paper"},
            "judge_analysis": {
                "overall_alignment": 0.55,
                "pillar_contributions": [
                    {
                        "pillar_name": "Pillar 1: Biological Stimulus-Response",
                        "sub_requirements_addressed": [
                            {"requirement_id": "Sub-1.1.3: Medium gap requirement"}
                        ]
                    }
                ]
            }
        },
        "paper3.pdf": {
            "metadata": {"title": "Low Quality Paper"},
            "judge_analysis": {
                "overall_alignment": 0.35,
                "pillar_contributions": [
                    {
                        "pillar_name": "Pillar 2: AI Stimulus-Response",
                        "sub_requirements_addressed": [
                            {"requirement_id": "Sub-2.1.1: SNN requirement"}
                        ]
                    }
                ]
            }
        }
    }


class TestDeepReviewTriggerEngine:
    """Test the DeepReviewTriggerEngine class."""
    
    def test_initialization(self, tmp_path, mock_gap_analysis, mock_review_log):
        """Test engine initialization."""
        gap_file = tmp_path / "gap_analysis.json"
        review_file = tmp_path / "review_log.json"
        
        with open(gap_file, 'w') as f:
            json.dump(mock_gap_analysis, f)
        with open(review_file, 'w') as f:
            json.dump(mock_review_log, f)
        
        engine = DeepReviewTriggerEngine(str(gap_file), str(review_file))
        
        assert engine.gap_data is not None
        assert 'pillars' in engine.gap_data
        assert len(engine.reviews) == 3
    
    def test_transform_gap_data(self, tmp_path, mock_gap_analysis, mock_review_log):
        """Test gap data transformation."""
        gap_file = tmp_path / "gap_analysis.json"
        review_file = tmp_path / "review_log.json"
        
        with open(gap_file, 'w') as f:
            json.dump(mock_gap_analysis, f)
        with open(review_file, 'w') as f:
            json.dump(mock_review_log, f)
        
        engine = DeepReviewTriggerEngine(str(gap_file), str(review_file))
        
        # Check pillars exist
        assert len(engine.gap_data['pillars']) == 2
        
        # Check first pillar
        pillar1 = engine.gap_data['pillars'][0]
        assert pillar1['name'] == "Pillar 1: Biological Stimulus-Response"
        assert len(pillar1['requirements']) == 4
        
        # Check gap severity classification
        req1 = pillar1['requirements'][0]
        assert req1['gap_severity'] == 'Critical'  # 0% completeness
        
        req2 = pillar1['requirements'][1]
        assert req2['gap_severity'] == 'High'  # 40% completeness
        
        req3 = pillar1['requirements'][2]
        assert req3['gap_severity'] == 'Medium'  # 60% completeness
        
        req4 = pillar1['requirements'][3]
        assert req4['gap_severity'] == 'Low'  # 80% completeness
    
    def test_evaluate_triggers(self, tmp_path, mock_gap_analysis, mock_review_log):
        """Test trigger evaluation."""
        gap_file = tmp_path / "gap_analysis.json"
        review_file = tmp_path / "review_log.json"
        
        with open(gap_file, 'w') as f:
            json.dump(mock_gap_analysis, f)
        with open(review_file, 'w') as f:
            json.dump(mock_review_log, f)
        
        engine = DeepReviewTriggerEngine(str(gap_file), str(review_file))
        candidates = engine.evaluate_triggers()
        
        # Should trigger paper1 (high quality 0.85 > 0.6)
        # Should NOT trigger paper2 (quality 0.55 < 0.6, gap not critical enough)
        # Should NOT trigger paper3 (quality 0.35 < 0.6)
        assert len(candidates) >= 1
        
        # Check paper1 is in candidates
        paper1_triggered = any(c['paper'] == 'paper1.pdf' for c in candidates)
        assert paper1_triggered
        
        # Verify candidate structure
        for candidate in candidates:
            assert 'paper' in candidate
            assert 'title' in candidate
            assert 'gap_score' in candidate
            assert 'quality_score' in candidate
            assert 'roi_score' in candidate
            assert 'trigger_reason' in candidate
    
    def test_gap_impact_calculation(self, tmp_path, mock_gap_analysis, mock_review_log):
        """Test gap impact calculation."""
        gap_file = tmp_path / "gap_analysis.json"
        review_file = tmp_path / "review_log.json"
        
        with open(gap_file, 'w') as f:
            json.dump(mock_gap_analysis, f)
        with open(review_file, 'w') as f:
            json.dump(mock_review_log, f)
        
        engine = DeepReviewTriggerEngine(str(gap_file), str(review_file))
        
        # Paper1 addresses critical gap -> should have high gap score
        gap_score = engine._calculate_gap_impact('paper1.pdf')
        assert gap_score == 1.0  # 100% because it addresses 1/1 critical gap
        
        # Paper2 addresses medium gap -> should have low gap score
        gap_score = engine._calculate_gap_impact('paper2.pdf')
        assert gap_score == 0.0  # 0% because medium gap is not High/Critical
    
    def test_roi_calculation(self, tmp_path, mock_gap_analysis, mock_review_log):
        """Test ROI calculation."""
        gap_file = tmp_path / "gap_analysis.json"
        review_file = tmp_path / "review_log.json"
        
        with open(gap_file, 'w') as f:
            json.dump(mock_gap_analysis, f)
        with open(review_file, 'w') as f:
            json.dump(mock_review_log, f)
        
        engine = DeepReviewTriggerEngine(str(gap_file), str(review_file))
        
        # High gap + high quality = high ROI
        roi = engine._calculate_roi('paper1.pdf', 1.0, 0.85)
        assert roi > 0
        assert roi == (1.0 * 0.85 * 2.0) / 0.5  # 3.4
        
        # Low gap + low quality = low ROI
        roi = engine._calculate_roi('paper3.pdf', 0.0, 0.35)
        assert roi == 0.0
    
    def test_trigger_thresholds(self, tmp_path, mock_gap_analysis, mock_review_log):
        """Test that thresholds are correctly applied."""
        gap_file = tmp_path / "gap_analysis.json"
        review_file = tmp_path / "review_log.json"
        
        with open(gap_file, 'w') as f:
            json.dump(mock_gap_analysis, f)
        with open(review_file, 'w') as f:
            json.dump(mock_review_log, f)
        
        engine = DeepReviewTriggerEngine(str(gap_file), str(review_file))
        
        # Verify thresholds exist
        assert engine.THRESHOLDS['gap_severity'] == 0.7
        assert engine.THRESHOLDS['paper_quality'] == 0.6
        assert engine.THRESHOLDS['roi_potential'] == 5.0


class TestGenerateTriggerReport:
    """Test the generate_trigger_report function."""
    
    def test_generate_report(self, tmp_path, mock_gap_analysis, mock_review_log):
        """Test report generation."""
        gap_file = tmp_path / "gap_analysis.json"
        review_file = tmp_path / "review_log.json"
        output_file = tmp_path / "output" / "trigger_report.json"
        
        with open(gap_file, 'w') as f:
            json.dump(mock_gap_analysis, f)
        with open(review_file, 'w') as f:
            json.dump(mock_review_log, f)
        
        report = generate_trigger_report(
            str(gap_file),
            str(review_file),
            str(output_file)
        )
        
        # Verify report structure
        assert 'total_papers' in report
        assert 'triggered_papers' in report
        assert 'trigger_rate' in report
        assert 'candidates' in report
        
        assert report['total_papers'] == 3
        assert report['triggered_papers'] >= 1
        assert 0 <= report['trigger_rate'] <= 1
        
        # Verify output file was created
        assert output_file.exists()
        
        # Verify output file content
        with open(output_file, 'r') as f:
            saved_report = json.load(f)
        assert saved_report == report
    
    def test_report_without_directory(self, tmp_path, mock_gap_analysis, mock_review_log):
        """Test report generation with simple filename (no directory)."""
        gap_file = tmp_path / "gap_analysis.json"
        review_file = tmp_path / "review_log.json"
        output_file = tmp_path / "trigger_report.json"
        
        with open(gap_file, 'w') as f:
            json.dump(mock_gap_analysis, f)
        with open(review_file, 'w') as f:
            json.dump(mock_review_log, f)
        
        # Change to tmp_path so output file is created there
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            report = generate_trigger_report(
                str(gap_file),
                str(review_file),
                "trigger_report.json"
            )
            assert os.path.exists("trigger_report.json")
        finally:
            os.chdir(original_cwd)
