"""
Smoke test for AdaptiveETACalculator

Tests basic functionality without complex setup.
Run with: python -m pytest tests/unit/test_eta_smoke.py -v
"""

import pytest
import tempfile
import os
from webdashboard.eta_calculator import AdaptiveETACalculator


def test_basic_eta_calculation():
    """Smoke test: Basic ETA calculation works"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = f.name
    
    try:
        calculator = AdaptiveETACalculator(history_file=temp_file)
        
        # Should work with no history (fallback mode)
        eta = calculator.calculate_eta('gap_analysis', paper_count=10)
        
        assert eta is not None
        assert 'total_eta_seconds' in eta
        assert 'confidence' in eta
        assert eta['confidence'] == 'low'  # No history
        assert eta['total_eta_seconds'] > 0
        
        print(f"✓ ETA calculation works: {eta['total_eta_seconds']}s estimated for 10 papers")
        
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_history_persistence():
    """Smoke test: History is saved and loaded correctly"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = f.name
    
    try:
        # Create calculator and record data
        calc1 = AdaptiveETACalculator(history_file=temp_file)
        calc1.record_stage_completion('gap_analysis', 300, 10)
        
        # Create new calculator and verify data was loaded
        calc2 = AdaptiveETACalculator(history_file=temp_file)
        
        assert 'gap_analysis' in calc2.history
        assert len(calc2.history['gap_analysis']) == 1
        assert calc2.history['gap_analysis'][0]['duration_seconds'] == 300
        
        print("✓ History persistence works")
        
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_confidence_progression():
    """Smoke test: Confidence improves with more data"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = f.name
    
    try:
        calculator = AdaptiveETACalculator(history_file=temp_file)
        
        # Start with low confidence
        eta = calculator.calculate_eta('gap_analysis', 10)
        assert eta['confidence'] == 'low'
        
        # Add some data for all remaining stages
        for stage in ['deep_review', 'proof_generation', 'final_report']:
            for i in range(5):
                calculator.record_stage_completion(stage, 100 * (i+1), 10)
        
        # Should now have medium confidence
        eta = calculator.calculate_eta('gap_analysis', 10)
        assert eta['confidence'] == 'medium'
        
        # Add more data
        for stage in ['deep_review', 'proof_generation', 'final_report']:
            for i in range(7):
                calculator.record_stage_completion(stage, 100 * (i+1), 10)
        
        # Should now have high confidence
        eta = calculator.calculate_eta('gap_analysis', 10)
        assert eta['confidence'] == 'high'
        
        print("✓ Confidence progression works: low → medium → high")
        
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_paper_count_scaling():
    """Smoke test: ETA scales with paper count"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_file = f.name
    
    try:
        calculator = AdaptiveETACalculator(history_file=temp_file)
        
        # Add consistent data (100s per paper)
        for stage in ['deep_review', 'proof_generation', 'final_report']:
            for _ in range(5):
                calculator.record_stage_completion(stage, 1000, 10)  # 1000s for 10 papers = 100s/paper
        
        # Get ETA for 10 papers
        eta_10 = calculator.calculate_eta('gap_analysis', 10)
        
        # Get ETA for 20 papers (should be ~2x)
        eta_20 = calculator.calculate_eta('gap_analysis', 20)
        
        ratio = eta_20['total_eta_seconds'] / eta_10['total_eta_seconds']
        
        # Should be roughly 2x (allow some variance)
        assert 1.8 < ratio < 2.2, f"Expected ~2x scaling, got {ratio}x"
        
        print(f"✓ Paper count scaling works: 10 papers={eta_10['total_eta_seconds']}s, 20 papers={eta_20['total_eta_seconds']}s (ratio={ratio:.2f})")
        
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


if __name__ == '__main__':
    print("\n=== Running ETA Calculator Smoke Tests ===\n")
    test_basic_eta_calculation()
    test_history_persistence()
    test_confidence_progression()
    test_paper_count_scaling()
    print("\n✅ All smoke tests passed!\n")
