"""
Unit Tests for Temporal Coherence Analysis (Task Card #19)
Tests maturity classification, quality trend detection, and temporal analysis.
"""

import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.orchestrator import (
    classify_maturity,
    analyze_evidence_evolution
)


class TestMaturityClassification:
    """Test suite for classify_maturity function."""
    
    @pytest.mark.unit
    def test_emerging_classification(self):
        """Test maturity level classification for emerging evidence."""
        # Emerging: <2 years, <5 papers
        assert classify_maturity(evidence_span=1, total_papers=3, recent_papers=3) == "emerging"
        assert classify_maturity(evidence_span=0, total_papers=1, recent_papers=1) == "emerging"
        assert classify_maturity(evidence_span=1, total_papers=4, recent_papers=2) == "emerging"
    
    @pytest.mark.unit
    def test_growing_classification(self):
        """Test maturity level classification for growing evidence."""
        # Growing: 2-5 years, 5-10 papers (or intermediate cases)
        assert classify_maturity(evidence_span=3, total_papers=7, recent_papers=2) == "growing"
        assert classify_maturity(evidence_span=4, total_papers=9, recent_papers=3) == "growing"
        assert classify_maturity(evidence_span=2, total_papers=5, recent_papers=1) == "growing"
    
    @pytest.mark.unit
    def test_established_classification(self):
        """Test maturity level classification for established evidence."""
        # Established: 5+ years, 10+ papers (but not mature)
        assert classify_maturity(evidence_span=6, total_papers=12, recent_papers=3) == "established"
        assert classify_maturity(evidence_span=7, total_papers=15, recent_papers=4) == "established"
        assert classify_maturity(evidence_span=10, total_papers=19, recent_papers=4) == "established"
    
    @pytest.mark.unit
    def test_mature_classification(self):
        """Test maturity level classification for mature evidence."""
        # Mature: 10+ years, 20+ papers, 5+ recent papers
        assert classify_maturity(evidence_span=10, total_papers=25, recent_papers=6) == "mature"
        assert classify_maturity(evidence_span=12, total_papers=30, recent_papers=7) == "mature"
        assert classify_maturity(evidence_span=15, total_papers=50, recent_papers=10) == "mature"
    
    @pytest.mark.unit
    def test_edge_cases(self):
        """Test edge cases for maturity classification."""
        # Exactly at thresholds
        assert classify_maturity(evidence_span=2, total_papers=5, recent_papers=1) == "growing"
        assert classify_maturity(evidence_span=5, total_papers=10, recent_papers=4) == "established"
        
        # Just below mature threshold
        assert classify_maturity(evidence_span=10, total_papers=20, recent_papers=4) == "established"
        assert classify_maturity(evidence_span=10, total_papers=19, recent_papers=5) == "established"


class TestQualityTrendDetection:
    """Test suite for quality trend detection using linear regression."""
    
    @pytest.mark.unit
    def test_improving_trend(self):
        """Test detection of improving quality trend."""
        from scipy.stats import linregress
        
        # Improving trend
        years = [2020, 2021, 2022, 2023, 2024]
        scores = [2.5, 2.8, 3.1, 3.4, 3.7]
        
        slope, _, _, p_value, _ = linregress(years, scores)
        
        assert slope > 0.1, "Slope should indicate improvement"
        assert p_value < 0.05, "Trend should be statistically significant"
    
    @pytest.mark.unit
    def test_declining_trend(self):
        """Test detection of declining quality trend."""
        from scipy.stats import linregress
        
        # Declining trend
        years = [2020, 2021, 2022, 2023, 2024]
        scores = [4.0, 3.7, 3.4, 3.1, 2.8]
        
        slope, _, _, p_value, _ = linregress(years, scores)
        
        assert slope < -0.1, "Slope should indicate decline"
        assert p_value < 0.05, "Trend should be statistically significant"
    
    @pytest.mark.unit
    def test_stable_trend(self):
        """Test detection of stable quality trend."""
        from scipy.stats import linregress
        
        # Stable trend (small variations around mean)
        years = [2020, 2021, 2022, 2023, 2024]
        scores = [3.0, 3.05, 2.95, 3.02, 2.98]
        
        slope, _, _, p_value, _ = linregress(years, scores)
        
        # Small slope (between -0.1 and 0.1)
        assert abs(slope) < 0.1, "Slope should be small for stable trend"


class TestTemporalAnalysisGeneration:
    """Test suite for analyze_evidence_evolution function."""
    
    @pytest.mark.unit
    def test_temporal_analysis_with_valid_data(self):
        """Test temporal analysis generation with valid data."""
        # Create test database
        db_data = {
            "FILENAME": ["paper1.pdf", "paper2.pdf", "paper3.pdf"],
            "Requirement(s)": ["Sub-1.1.1", "Sub-1.1.1", "Sub-1.1.1"],
            "PUBLICATION_YEAR": [2020, 2022, 2024],
            "EVIDENCE_COMPOSITE_SCORE": [3.0, 3.5, 4.0]
        }
        db = pd.DataFrame(db_data)
        
        pillar_defs = {
            "Pillar 1": {
                "requirements": {
                    "REQ-1.1": ["Sub-1.1.1"]
                }
            }
        }
        
        # Run temporal analysis
        temporal = analyze_evidence_evolution(db, pillar_defs)
        
        assert "Sub-1.1.1" in temporal
        assert temporal["Sub-1.1.1"]["earliest_evidence"] == 2020
        assert temporal["Sub-1.1.1"]["latest_evidence"] == 2024
        assert temporal["Sub-1.1.1"]["evidence_span_years"] == 4
        assert temporal["Sub-1.1.1"]["total_papers"] == 3
    
    @pytest.mark.unit
    def test_temporal_analysis_year_counts(self):
        """Test that evidence count by year is correctly calculated."""
        db_data = {
            "FILENAME": ["p1.pdf", "p2.pdf", "p3.pdf", "p4.pdf", "p5.pdf"],
            "Requirement(s)": ["Sub-2.1.1"] * 5,
            "PUBLICATION_YEAR": [2020, 2020, 2022, 2022, 2024]
        }
        db = pd.DataFrame(db_data)
        
        pillar_defs = {
            "Pillar 2": {
                "requirements": {
                    "REQ-2.1": ["Sub-2.1.1"]
                }
            }
        }
        
        temporal = analyze_evidence_evolution(db, pillar_defs)
        
        assert temporal["Sub-2.1.1"]["evidence_count_by_year"][2020] == 2
        assert temporal["Sub-2.1.1"]["evidence_count_by_year"][2022] == 2
        assert temporal["Sub-2.1.1"]["evidence_count_by_year"][2024] == 1
    
    @pytest.mark.unit
    def test_temporal_analysis_recent_activity(self):
        """Test recent activity detection."""
        current_year = datetime.now().year
        
        # Create data with recent activity
        db_data = {
            "FILENAME": ["p1.pdf", "p2.pdf", "p3.pdf", "p4.pdf"],
            "Requirement(s)": ["Sub-3.1.1"] * 4,
            "PUBLICATION_YEAR": [current_year-1, current_year-1, current_year-2, 2015]
        }
        db = pd.DataFrame(db_data)
        
        pillar_defs = {
            "Pillar 3": {
                "requirements": {
                    "REQ-3.1": ["Sub-3.1.1"]
                }
            }
        }
        
        temporal = analyze_evidence_evolution(db, pillar_defs)
        
        # Should have recent activity (3 papers in last 3 years)
        assert temporal["Sub-3.1.1"]["recent_activity"] is True
        assert temporal["Sub-3.1.1"]["recent_papers"] == 3
    
    @pytest.mark.unit
    def test_temporal_analysis_empty_data(self):
        """Test temporal analysis with empty database."""
        db = pd.DataFrame(columns=["FILENAME", "Requirement(s)", "PUBLICATION_YEAR"])
        
        pillar_defs = {
            "Pillar 1": {
                "requirements": {
                    "REQ-1.1": ["Sub-1.1.1"]
                }
            }
        }
        
        temporal = analyze_evidence_evolution(db, pillar_defs)
        
        # Should return empty dict for sub-req with no data
        assert "Sub-1.1.1" not in temporal
    
    @pytest.mark.unit
    def test_temporal_analysis_filters_invalid_years(self):
        """Test that invalid publication years are filtered out."""
        db_data = {
            "FILENAME": ["p1.pdf", "p2.pdf", "p3.pdf"],
            "Requirement(s)": ["Sub-4.1.1"] * 3,
            "PUBLICATION_YEAR": [2020, 1800, 2022]  # 1800 should be filtered
        }
        db = pd.DataFrame(db_data)
        
        pillar_defs = {
            "Pillar 4": {
                "requirements": {
                    "REQ-4.1": ["Sub-4.1.1"]
                }
            }
        }
        
        temporal = analyze_evidence_evolution(db, pillar_defs)
        
        # Should only count valid years
        assert temporal["Sub-4.1.1"]["total_papers"] == 3  # All papers counted
        assert temporal["Sub-4.1.1"]["earliest_evidence"] == 2020
        assert 1800 not in temporal["Sub-4.1.1"]["evidence_count_by_year"]
    
    @pytest.mark.unit
    def test_maturity_level_integration(self):
        """Test that maturity level is correctly assigned in temporal analysis."""
        # Create data for mature evidence
        db_data = {
            "FILENAME": [f"p{i}.pdf" for i in range(25)],
            "Requirement(s)": ["Sub-5.1.1"] * 25,
            "PUBLICATION_YEAR": [2010] * 5 + [2015] * 5 + [2020] * 5 + [2023] * 5 + [2024] * 5
        }
        db = pd.DataFrame(db_data)
        
        pillar_defs = {
            "Pillar 5": {
                "requirements": {
                    "REQ-5.1": ["Sub-5.1.1"]
                }
            }
        }
        
        temporal = analyze_evidence_evolution(db, pillar_defs)
        
        # Should be classified as mature (14 year span, 25 papers, 10 recent)
        assert temporal["Sub-5.1.1"]["maturity_level"] == "mature"
