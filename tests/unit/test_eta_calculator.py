"""
Unit tests for AdaptiveETACalculator

Tests historical data tracking, paper count scaling, confidence calculations,
and fallback behavior.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from webdashboard.eta_calculator import AdaptiveETACalculator


class TestAdaptiveETACalculator:
    """Test suite for AdaptiveETACalculator"""
    
    @pytest.fixture
    def temp_history_file(self):
        """Create a temporary file for history storage"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        yield temp_file
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    def test_eta_with_historical_data(self, temp_history_file):
        """Test ETA calculation with good historical data"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        # Mock historical data for all remaining stages
        calculator.history = {
            'deep_review': [
                {'duration_seconds': 1200, 'paper_count': 10, 'time_per_paper': 120, 'timestamp': '2025-01-01T00:00:00Z'},
                {'duration_seconds': 2400, 'paper_count': 20, 'time_per_paper': 120, 'timestamp': '2025-01-02T00:00:00Z'},
                {'duration_seconds': 600, 'paper_count': 5, 'time_per_paper': 120, 'timestamp': '2025-01-03T00:00:00Z'}
            ],
            'proof_generation': [
                {'duration_seconds': 450, 'paper_count': 10, 'time_per_paper': 45, 'timestamp': '2025-01-01T00:00:00Z'},
                {'duration_seconds': 900, 'paper_count': 20, 'time_per_paper': 45, 'timestamp': '2025-01-02T00:00:00Z'},
                {'duration_seconds': 225, 'paper_count': 5, 'time_per_paper': 45, 'timestamp': '2025-01-03T00:00:00Z'}
            ],
            'final_report': [
                {'duration_seconds': 150, 'paper_count': 10, 'time_per_paper': 15, 'timestamp': '2025-01-01T00:00:00Z'},
                {'duration_seconds': 300, 'paper_count': 20, 'time_per_paper': 15, 'timestamp': '2025-01-02T00:00:00Z'},
                {'duration_seconds': 75, 'paper_count': 5, 'time_per_paper': 15, 'timestamp': '2025-01-03T00:00:00Z'}
            ]
        }
        
        eta = calculator.calculate_eta('gap_analysis', paper_count=10)
        
        assert eta['confidence'] == 'medium'  # 3 data points for all stages
        assert 1500 < eta['total_eta_seconds'] < 2000  # ~(120+45+15)*10

    def test_eta_fallback_no_history(self, temp_history_file):
        """Test ETA falls back to estimates when no history"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        calculator.history = {}  # No historical data
        
        eta = calculator.calculate_eta('gap_analysis', paper_count=10)
        
        assert eta['confidence'] == 'low'
        assert eta['total_eta_seconds'] > 0

    def test_confidence_interval_calculation(self, temp_history_file):
        """Test confidence interval width based on confidence level"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        # High confidence: narrow interval (±5%) - need data for all remaining stages
        calculator.history = {
            'deep_review': [
                {'time_per_paper': 100, 'duration_seconds': 1000, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'}
                for _ in range(15)
            ],
            'proof_generation': [
                {'time_per_paper': 50, 'duration_seconds': 500, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'}
                for _ in range(15)
            ],
            'final_report': [
                {'time_per_paper': 20, 'duration_seconds': 200, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'}
                for _ in range(15)
            ]
        }
        eta_high = calculator.calculate_eta('gap_analysis', 10)
        high_range = eta_high['max_eta_seconds'] - eta_high['min_eta_seconds']
        
        # Low confidence: wide interval (±30%)
        calculator.history = {}
        eta_low = calculator.calculate_eta('gap_analysis', 10)
        low_range = eta_low['max_eta_seconds'] - eta_low['min_eta_seconds']
        
        assert low_range > high_range * 5  # Low confidence has much wider range

    def test_record_stage_completion(self, temp_history_file):
        """Test historical data recording"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        calculator.record_stage_completion('gap_analysis', duration_seconds=300, paper_count=10)
        
        assert 'gap_analysis' in calculator.history
        assert len(calculator.history['gap_analysis']) == 1
        assert calculator.history['gap_analysis'][0]['time_per_paper'] == 30
        
        # Verify persistence
        calculator2 = AdaptiveETACalculator(history_file=temp_history_file)
        assert 'gap_analysis' in calculator2.history
        assert len(calculator2.history['gap_analysis']) == 1

    def test_history_limit(self, temp_history_file):
        """Test that history is limited to 50 entries per stage"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        # Add 60 entries
        for i in range(60):
            calculator.record_stage_completion('gap_analysis', duration_seconds=100 + i, paper_count=10)
        
        # Should only keep last 50
        assert len(calculator.history['gap_analysis']) == 50
        # First entry should be from iteration 10 (0-9 were dropped)
        assert calculator.history['gap_analysis'][0]['duration_seconds'] == 110

    def test_paper_count_scaling(self, temp_history_file):
        """Test that ETA scales linearly with paper count"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        # Mock historical data with consistent time per paper
        calculator.history = {
            'deep_review': [
                {'duration_seconds': 1000, 'paper_count': 10, 'time_per_paper': 100, 'timestamp': '2025-01-01T00:00:00Z'},
                {'duration_seconds': 2000, 'paper_count': 20, 'time_per_paper': 100, 'timestamp': '2025-01-02T00:00:00Z'},
                {'duration_seconds': 500, 'paper_count': 5, 'time_per_paper': 100, 'timestamp': '2025-01-03T00:00:00Z'}
            ]
        }
        
        eta_10 = calculator.calculate_eta('gap_analysis', paper_count=10)
        eta_20 = calculator.calculate_eta('gap_analysis', paper_count=20)
        
        # ETA for 20 papers should be roughly 2x the ETA for 10 papers
        ratio = eta_20['total_eta_seconds'] / eta_10['total_eta_seconds']
        assert 1.8 < ratio < 2.2  # Allow some variance

    def test_confidence_levels(self, temp_history_file):
        """Test confidence level assignment based on data points"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        # Test low confidence (no data)
        calculator.history = {}
        eta = calculator.calculate_eta('gap_analysis', 10)
        assert eta['confidence'] == 'low'
        
        # Test medium confidence (3-9 data points) - need data for all remaining stages
        calculator.history = {
            'deep_review': [
                {'time_per_paper': 100, 'duration_seconds': 1000, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'}
                for _ in range(5)
            ],
            'proof_generation': [
                {'time_per_paper': 50, 'duration_seconds': 500, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'}
                for _ in range(5)
            ],
            'final_report': [
                {'time_per_paper': 20, 'duration_seconds': 200, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'}
                for _ in range(5)
            ]
        }
        eta = calculator.calculate_eta('gap_analysis', 10)
        assert eta['confidence'] == 'medium'
        
        # Test high confidence (10+ data points)
        calculator.history = {
            'deep_review': [
                {'time_per_paper': 100, 'duration_seconds': 1000, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'}
                for _ in range(12)
            ],
            'proof_generation': [
                {'time_per_paper': 50, 'duration_seconds': 500, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'}
                for _ in range(12)
            ],
            'final_report': [
                {'time_per_paper': 20, 'duration_seconds': 200, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'}
                for _ in range(12)
            ]
        }
        eta = calculator.calculate_eta('gap_analysis', 10)
        assert eta['confidence'] == 'high'

    def test_stage_breakdown(self, temp_history_file):
        """Test that stage breakdown is correctly calculated"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        calculator.history = {
            'deep_review': [
                {'time_per_paper': 100, 'duration_seconds': 1000, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'}
                for _ in range(5)
            ]
        }
        
        eta = calculator.calculate_eta('gap_analysis', 10)
        
        assert 'stage_breakdown' in eta
        assert 'deep_review' in eta['stage_breakdown']
        assert eta['stage_breakdown']['deep_review'] > 0

    def test_accuracy_report(self, temp_history_file):
        """Test accuracy report generation"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        # Add some data
        calculator.history = {
            'gap_analysis': [
                {'duration_seconds': 100, 'paper_count': 10, 'time_per_paper': 10, 'timestamp': '2025-01-01T00:00:00Z'},
                {'duration_seconds': 200, 'paper_count': 20, 'time_per_paper': 10, 'timestamp': '2025-01-02T00:00:00Z'},
                {'duration_seconds': 150, 'paper_count': 15, 'time_per_paper': 10, 'timestamp': '2025-01-03T00:00:00Z'}
            ]
        }
        
        report = calculator.get_accuracy_report()
        
        assert 'gap_analysis' in report
        assert report['gap_analysis']['sample_size'] == 3
        assert 'avg_duration' in report['gap_analysis']
        assert 'std_dev' in report['gap_analysis']

    def test_zero_paper_count_handling(self, temp_history_file):
        """Test that zero or negative paper counts are handled gracefully"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        # Record with zero papers shouldn't crash
        calculator.record_stage_completion('gap_analysis', duration_seconds=100, paper_count=0)
        
        # Should handle division by zero
        assert len(calculator.history['gap_analysis']) == 1
        
        # ETA calculation with zero papers
        eta = calculator.calculate_eta('gap_analysis', paper_count=0)
        assert eta['total_eta_seconds'] >= 0

    def test_invalid_stage_handling(self, temp_history_file):
        """Test handling of invalid stage names"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        # Calculate ETA from an unknown stage
        eta = calculator.calculate_eta('unknown_stage', paper_count=10)
        
        # Should return all stages
        assert len(eta['remaining_stages']) == len(calculator.STAGE_ORDER)

    def test_median_vs_mean(self, temp_history_file):
        """Test that calculator uses median for robustness against outliers"""
        calculator = AdaptiveETACalculator(history_file=temp_history_file)
        
        # Create data with outlier
        calculator.history = {
            'deep_review': [
                {'time_per_paper': 100, 'duration_seconds': 1000, 'paper_count': 10, 'timestamp': '2025-01-01T00:00:00Z'},
                {'time_per_paper': 100, 'duration_seconds': 1000, 'paper_count': 10, 'timestamp': '2025-01-02T00:00:00Z'},
                {'time_per_paper': 100, 'duration_seconds': 1000, 'paper_count': 10, 'timestamp': '2025-01-03T00:00:00Z'},
                {'time_per_paper': 1000, 'duration_seconds': 10000, 'paper_count': 10, 'timestamp': '2025-01-04T00:00:00Z'},  # Outlier
            ]
        }
        
        eta = calculator.calculate_eta('gap_analysis', paper_count=10)
        
        # Median should be around 100*10 = 1000, not affected much by outlier
        # If we used mean, it would be (100+100+100+1000)/4 * 10 = 3250
        assert eta['stage_breakdown']['deep_review'] < 1500  # Should be closer to median
