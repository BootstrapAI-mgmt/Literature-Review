"""
Unit tests for CostTracker class.

Tests cover:
- Cost calculation for different models
- Budget status tracking
- Cache efficiency calculations
- Session vs total summaries
- Recommendations generation
- Per-paper analysis
"""

import pytest
import sys
import os
import json
import tempfile
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.cost_tracker import CostTracker


class TestCostTracker:
    """Test suite for CostTracker class."""
    
    def test_cost_calculation_free_tier(self):
        """Test cost calculation for free tier models."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            tracker = CostTracker(log_file=temp_file)
            
            # Test Gemini 2.5 Flash (free tier)
            cost = tracker._calculate_cost('gemini-2.5-flash', 1000, 500, 0)
            assert cost == 0.0, f"Free tier should be $0, got ${cost}"
            
            # Test with caching (still free)
            cost = tracker._calculate_cost('gemini-2.5-flash', 1000, 500, 500)
            assert cost == 0.0, f"Free tier with cache should be $0, got ${cost}"
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_cost_calculation_paid_tier(self):
        """Test cost calculation for paid tier models."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            tracker = CostTracker(log_file=temp_file)
            
            # Test Gemini 1.5 Flash
            # Input: 1000 tokens @ $0.075 per 1M = $0.000075
            # Output: 500 tokens @ $0.30 per 1M = $0.000150
            # Total: $0.000225
            cost = tracker._calculate_cost('gemini-1.5-flash', 1000, 500, 0)
            expected = (1000 * 0.075 / 1_000_000) + (500 * 0.30 / 1_000_000)
            assert abs(cost - expected) < 0.0000001, f"Expected ${expected:.6f}, got ${cost:.6f}"
            
            # Test Gemini 1.5 Pro
            # Input: 1000 tokens @ $1.25 per 1M = $0.00125
            # Output: 500 tokens @ $5.00 per 1M = $0.00250
            # Total: $0.00375
            cost = tracker._calculate_cost('gemini-1.5-pro', 1000, 500, 0)
            expected = (1000 * 1.25 / 1_000_000) + (500 * 5.00 / 1_000_000)
            assert abs(cost - expected) < 0.0000001, f"Expected ${expected:.6f}, got ${cost:.6f}"
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_cost_calculation_with_caching(self):
        """Test cost calculation with cached tokens."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            tracker = CostTracker(log_file=temp_file)
            
            # Test Gemini 1.5 Flash with caching
            # Regular input: 500 tokens @ $0.075 per 1M = $0.0000375
            # Cached input: 500 tokens @ $0.01875 per 1M = $0.00000938
            # Output: 500 tokens @ $0.30 per 1M = $0.000150
            cost = tracker._calculate_cost('gemini-1.5-flash', 1000, 500, 500)
            expected = (500 * 0.075 / 1_000_000) + (500 * 0.01875 / 1_000_000) + (500 * 0.30 / 1_000_000)
            assert abs(cost - expected) < 0.0000001, f"Expected ${expected:.6f}, got ${cost:.6f}"
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_unknown_model_defaults_to_free(self):
        """Test that unknown models default to free tier."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            tracker = CostTracker(log_file=temp_file)
            
            cost = tracker._calculate_cost('unknown-model', 1000, 500, 0)
            assert cost == 0.0, f"Unknown model should default to free tier, got ${cost}"
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_log_api_call(self):
        """Test logging an API call."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            tracker = CostTracker(log_file=temp_file)
            
            tracker.log_api_call(
                module='test_module',
                model='gemini-2.5-flash',
                input_tokens=1000,
                output_tokens=500,
                cached_tokens=0,
                operation='test_operation',
                paper='test_paper.pdf'
            )
            
            assert len(tracker.usage_log) == 1
            entry = tracker.usage_log[0]
            
            assert entry['module'] == 'test_module'
            assert entry['model'] == 'gemini-2.5-flash'
            assert entry['operation'] == 'test_operation'
            assert entry['paper'] == 'test_paper.pdf'
            assert entry['tokens']['input'] == 1000
            assert entry['tokens']['output'] == 500
            assert entry['tokens']['cached'] == 0
            assert entry['tokens']['total'] == 1500
            assert entry['cost_usd'] == 0.0  # Free tier
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_budget_status(self):
        """Test budget status tracking."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            tracker = CostTracker(log_file=temp_file)
            
            # Add some test data (using paid tier for non-zero costs)
            tracker.log_api_call('test', 'gemini-1.5-flash', 1_000_000, 1_000_000, 0)
            
            status = tracker.get_budget_status(50.0)
            
            assert 'budget' in status
            assert status['budget'] == 50.0
            assert 'spent' in status
            assert 'remaining' in status
            assert status['remaining'] == status['budget'] - status['spent']
            assert 'percent_used' in status
            assert 'at_risk' in status
            assert 'over_budget' in status
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_budget_at_risk(self):
        """Test budget at-risk detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            tracker = CostTracker(log_file=temp_file)
            
            # Mock a high-cost scenario by directly manipulating usage_log
            # 45M input tokens + 45M output tokens @ 1.5 flash rates = ~16.875
            tracker.log_api_call('test', 'gemini-1.5-flash', 45_000_000, 45_000_000, 0)
            
            status = tracker.get_budget_status(20.0)
            
            # Should be at risk (>80% of $20 budget)
            assert status['at_risk'] == True
            assert status['percent_used'] > 80
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_session_vs_total_summary(self):
        """Test session summary vs total summary."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Create log with existing data
            existing_data = [{
                'timestamp': '2025-01-01T00:00:00',
                'module': 'old_module',
                'model': 'gemini-2.5-flash',
                'operation': 'old_op',
                'paper': 'old.pdf',
                'tokens': {'input': 100, 'output': 50, 'cached': 0, 'total': 150},
                'cost_usd': 0.0,
                'cache_savings_usd': 0.0
            }]
            
            with open(temp_file, 'w') as f:
                json.dump(existing_data, f)
            
            # Create tracker (loads existing data)
            tracker = CostTracker(log_file=temp_file)
            
            # Add new session data
            tracker.log_api_call('new_module', 'gemini-2.5-flash', 200, 100, 0)
            
            session_summary = tracker.get_session_summary()
            total_summary = tracker.get_total_summary()
            
            # Session should have only 1 call
            assert session_summary['total_calls'] == 1
            # Total should have 2 calls
            assert total_summary['total_calls'] == 2
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_cache_efficiency_calculation(self):
        """Test cache efficiency calculation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            tracker = CostTracker(log_file=temp_file)
            
            # Add calls with caching
            tracker.log_api_call('test', 'gemini-1.5-flash', 1000, 500, 500)  # 50% cached
            tracker.log_api_call('test', 'gemini-1.5-flash', 1000, 500, 0)     # 0% cached
            
            cache_eff = tracker._calculate_cache_efficiency()
            
            # Total input: 2000, cached: 500 -> 25% hit rate
            assert cache_eff['cache_hit_rate_percent'] == 25.0
            assert cache_eff['total_tokens_cached'] == 500
            assert 'total_savings_usd' in cache_eff
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_per_paper_analysis(self):
        """Test per-paper cost analysis."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            tracker = CostTracker(log_file=temp_file)
            
            # Add calls for different papers
            tracker.log_api_call('test', 'gemini-1.5-flash', 1000, 500, 0, paper='paper1.pdf')
            tracker.log_api_call('test', 'gemini-1.5-flash', 2000, 1000, 0, paper='paper2.pdf')
            tracker.log_api_call('test', 'gemini-1.5-flash', 1000, 500, 0, paper='paper1.pdf')
            
            analysis = tracker.cost_per_paper_analysis()
            
            assert analysis['total_papers_analyzed'] == 2
            assert 'avg_cost_per_paper' in analysis
            assert 'min_cost' in analysis
            assert 'max_cost' in analysis
            assert 'most_expensive_papers' in analysis
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_recommendations_generation(self):
        """Test recommendations generation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            tracker = CostTracker(log_file=temp_file)
            
            # No data - should recommend everything is good
            recommendations = tracker._generate_recommendations()
            assert len(recommendations) > 0
            assert any('✅' in rec for rec in recommendations)
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_generate_report(self):
        """Test report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'cost_log.json')
            report_file = os.path.join(tmpdir, 'report.json')
            
            tracker = CostTracker(log_file=log_file)
            
            # Add some test data
            tracker.log_api_call('test', 'gemini-2.5-flash', 1000, 500, 0)
            
            report = tracker.generate_report(output_file=report_file)
            
            # Check report structure
            assert 'generated_at' in report
            assert 'session_summary' in report
            assert 'total_summary' in report
            assert 'budget_status' in report
            assert 'per_paper_analysis' in report
            assert 'cache_efficiency' in report
            assert 'recommendations' in report
            
            # Check file was created
            assert os.path.exists(report_file)
            
            # Verify JSON is valid
            with open(report_file, 'r') as f:
                saved_report = json.load(f)
            assert saved_report['session_summary']['total_calls'] == 1
