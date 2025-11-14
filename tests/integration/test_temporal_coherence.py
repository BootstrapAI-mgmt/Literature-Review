"""
Integration Tests for Temporal Coherence Analysis (Task Card #19)
Tests end-to-end temporal analysis workflow with realistic data.
"""

import pytest
import json
import os
import pandas as pd
from pathlib import Path
from typing import Dict

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.orchestrator import (
    analyze_evidence_evolution,
    classify_maturity
)
from literature_review.utils.plotter import (
    plot_evidence_evolution,
    plot_maturity_distribution
)


class TestTemporalAnalysisIntegration:
    """Integration tests for temporal coherence analysis workflow."""
    
    @pytest.mark.integration
    def test_temporal_analysis_generation(self, temp_workspace):
        """Test temporal analysis generation with realistic data."""
        
        # Create test database with temporal data
        db_data = {
            "FILENAME": [f"paper{i}.pdf" for i in range(15)],
            "Requirement(s)": ["Sub-1.1.1"] * 5 + ["Sub-2.2.3"] * 7 + ["Sub-3.1.1"] * 3,
            "PUBLICATION_YEAR": [2018, 2020, 2021, 2023, 2024] + 
                                [2015, 2016, 2018, 2019, 2020, 2022, 2024] +
                                [2022, 2023, 2024],
            "EVIDENCE_COMPOSITE_SCORE": [2.5, 2.8, 3.0, 3.5, 4.0] +
                                         [2.0, 2.5, 2.8, 3.0, 3.2, 3.5, 3.8] +
                                         [3.0, 3.2, 3.5]
        }
        db = pd.DataFrame(db_data)
        
        # Create pillar definitions
        pillar_defs = {
            "Pillar 1: Biological Stimulus-Response": {
                "requirements": {
                    "REQ-B1.1": ["Sub-1.1.1"]
                }
            },
            "Pillar 2: AI Stimulus-Response (Bridge)": {
                "requirements": {
                    "REQ-A2.2": ["Sub-2.2.3"]
                }
            },
            "Pillar 3: Biological Memory": {
                "requirements": {
                    "REQ-B3.1": ["Sub-3.1.1"]
                }
            }
        }
        
        # Run temporal analysis
        temporal = analyze_evidence_evolution(db, pillar_defs)
        
        # Assert: Verify analysis for Sub-1.1.1
        assert "Sub-1.1.1" in temporal
        assert temporal["Sub-1.1.1"]["earliest_evidence"] == 2018
        assert temporal["Sub-1.1.1"]["latest_evidence"] == 2024
        assert temporal["Sub-1.1.1"]["evidence_span_years"] == 6
        assert temporal["Sub-1.1.1"]["total_papers"] == 5
        assert temporal["Sub-1.1.1"]["quality_trend"] == "improving"
        assert temporal["Sub-1.1.1"]["maturity_level"] in ["growing", "established"]
        
        # Assert: Verify analysis for Sub-2.2.3
        assert "Sub-2.2.3" in temporal
        assert temporal["Sub-2.2.3"]["earliest_evidence"] == 2015
        assert temporal["Sub-2.2.3"]["latest_evidence"] == 2024
        assert temporal["Sub-2.2.3"]["evidence_span_years"] == 9
        assert temporal["Sub-2.2.3"]["total_papers"] == 7
        assert temporal["Sub-2.2.3"]["maturity_level"] in ["established", "growing"]
        
        # Assert: Verify analysis for Sub-3.1.1
        assert "Sub-3.1.1" in temporal
        assert temporal["Sub-3.1.1"]["recent_activity"] is True
        assert temporal["Sub-3.1.1"]["recent_papers"] == 3
    
    @pytest.mark.integration
    def test_temporal_visualization_generation(self, temp_workspace):
        """Test temporal visualization functions."""
        
        # Create test temporal analysis data
        temporal_analysis = {
            "Sub-1.1.1": {
                "earliest_evidence": 2018,
                "latest_evidence": 2024,
                "evidence_span_years": 6,
                "total_papers": 15,
                "recent_papers": 8,
                "evidence_count_by_year": {2018: 2, 2020: 5, 2022: 3, 2024: 5},
                "quality_trend": "improving",
                "maturity_level": "established",
                "consensus_strength": "strong",
                "recent_activity": True
            },
            "Sub-2.2.3": {
                "earliest_evidence": 2015,
                "latest_evidence": 2024,
                "evidence_span_years": 9,
                "total_papers": 12,
                "recent_papers": 4,
                "evidence_count_by_year": {2015: 2, 2018: 3, 2020: 2, 2022: 3, 2024: 2},
                "quality_trend": "stable",
                "maturity_level": "established",
                "consensus_strength": "moderate",
                "recent_activity": True
            },
            "Sub-3.1.1": {
                "earliest_evidence": 2022,
                "latest_evidence": 2024,
                "evidence_span_years": 2,
                "total_papers": 4,
                "recent_papers": 4,
                "evidence_count_by_year": {2022: 1, 2023: 2, 2024: 1},
                "quality_trend": "unknown",
                "maturity_level": "emerging",
                "consensus_strength": "weak",
                "recent_activity": True
            }
        }
        
        # Generate visualizations
        heatmap_path = temp_workspace / "evidence_evolution_heatmap.png"
        maturity_path = temp_workspace / "maturity_distribution.png"
        
        plot_evidence_evolution(temporal_analysis, str(heatmap_path))
        plot_maturity_distribution(temporal_analysis, str(maturity_path))
        
        # Assert: Verify files were created
        assert heatmap_path.exists(), "Evidence evolution heatmap should be created"
        assert maturity_path.exists(), "Maturity distribution plot should be created"
        
        # Assert: Verify files have content
        assert heatmap_path.stat().st_size > 0, "Heatmap file should not be empty"
        assert maturity_path.stat().st_size > 0, "Maturity plot file should not be empty"
    
    @pytest.mark.integration
    def test_temporal_analysis_with_missing_scores(self, temp_workspace):
        """Test temporal analysis when EVIDENCE_COMPOSITE_SCORE is missing."""
        
        # Create test database WITHOUT composite scores
        db_data = {
            "FILENAME": ["p1.pdf", "p2.pdf", "p3.pdf"],
            "Requirement(s)": ["Sub-4.1.1"] * 3,
            "PUBLICATION_YEAR": [2020, 2022, 2024]
        }
        db = pd.DataFrame(db_data)
        
        pillar_defs = {
            "Pillar 4": {
                "requirements": {
                    "REQ-4.1": ["Sub-4.1.1"]
                }
            }
        }
        
        # Run temporal analysis
        temporal = analyze_evidence_evolution(db, pillar_defs)
        
        # Assert: Should still work but quality_trend should be "unknown"
        assert "Sub-4.1.1" in temporal
        assert temporal["Sub-4.1.1"]["quality_trend"] == "unknown"
        assert temporal["Sub-4.1.1"]["consensus_strength"] == "unknown"
        assert temporal["Sub-4.1.1"]["total_papers"] == 3
    
    @pytest.mark.integration
    def test_temporal_analysis_consensus_detection(self, temp_workspace):
        """Test consensus strength detection based on score variance."""
        
        # Strong consensus: Low variance
        db_strong = pd.DataFrame({
            "FILENAME": ["p1.pdf", "p2.pdf", "p3.pdf"],
            "Requirement(s)": ["Sub-5.1.1"] * 3,
            "PUBLICATION_YEAR": [2020, 2021, 2022],
            "EVIDENCE_COMPOSITE_SCORE": [4.0, 4.1, 4.0]  # Low variance
        })
        
        pillar_defs = {
            "Pillar 5": {
                "requirements": {
                    "REQ-5.1": ["Sub-5.1.1"]
                }
            }
        }
        
        temporal = analyze_evidence_evolution(db_strong, pillar_defs)
        
        # Assert: Should detect strong consensus
        assert temporal["Sub-5.1.1"]["consensus_strength"] == "strong"
        
        # Weak consensus: High variance
        db_weak = pd.DataFrame({
            "FILENAME": ["p1.pdf", "p2.pdf", "p3.pdf"],
            "Requirement(s)": ["Sub-5.1.2"] * 3,
            "PUBLICATION_YEAR": [2020, 2021, 2022],
            "EVIDENCE_COMPOSITE_SCORE": [1.5, 4.0, 2.0]  # High variance
        })
        
        pillar_defs_2 = {
            "Pillar 5": {
                "requirements": {
                    "REQ-5.1": ["Sub-5.1.2"]
                }
            }
        }
        
        temporal_weak = analyze_evidence_evolution(db_weak, pillar_defs_2)
        
        # Assert: Should detect weak or no consensus
        assert temporal_weak["Sub-5.1.2"]["consensus_strength"] in ["weak", "none"]
    
    @pytest.mark.integration
    def test_temporal_analysis_handles_multiple_sub_requirements(self, temp_workspace):
        """Test temporal analysis with multiple sub-requirements in same requirement."""
        
        db_data = {
            "FILENAME": ["p1.pdf", "p2.pdf", "p3.pdf", "p4.pdf"],
            "Requirement(s)": ["Sub-6.1.1", "Sub-6.1.2", "Sub-6.1.1", "Sub-6.1.3"],
            "PUBLICATION_YEAR": [2020, 2021, 2022, 2023]
        }
        db = pd.DataFrame(db_data)
        
        pillar_defs = {
            "Pillar 6": {
                "requirements": {
                    "REQ-6.1": ["Sub-6.1.1", "Sub-6.1.2", "Sub-6.1.3"]
                }
            }
        }
        
        temporal = analyze_evidence_evolution(db, pillar_defs)
        
        # Assert: Should analyze each sub-requirement separately
        assert "Sub-6.1.1" in temporal
        assert temporal["Sub-6.1.1"]["total_papers"] == 2
        
        assert "Sub-6.1.2" in temporal
        assert temporal["Sub-6.1.2"]["total_papers"] == 1
        
        assert "Sub-6.1.3" in temporal
        assert temporal["Sub-6.1.3"]["total_papers"] == 1
