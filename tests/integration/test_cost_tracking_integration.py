"""
Integration test for cost tracking with API manager.

This test creates a mock API response to verify that cost tracking
is properly integrated with the API manager.
"""

import pytest
import sys
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.api_manager import APIManager
from literature_review.utils.cost_tracker import CostTracker


class TestCostTrackingIntegration:
    """Test suite for cost tracking integration."""
    
    def test_api_manager_logs_costs(self):
        """Test that API manager logs costs to cost tracker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create temporary cache and cost log directories
            cache_dir = os.path.join(tmpdir, 'api_cache')
            cost_log = os.path.join(tmpdir, 'cost_log.json')
            
            # Create cost tracker with temp log
            tracker = CostTracker(log_file=cost_log)
            
            # Mock the API response
            mock_response = Mock()
            mock_response.text = '{"result": "test"}'
            
            # Mock usage metadata
            mock_usage = Mock()
            mock_usage.prompt_token_count = 1000
            mock_usage.candidates_token_count = 500
            mock_usage.cached_content_token_count = 0
            mock_response.usage_metadata = mock_usage
            
            # Patch the genai.Client initialization and SentenceTransformer
            with patch('literature_review.utils.api_manager.genai.Client'):
                with patch('literature_review.utils.api_manager.SentenceTransformer'):
                    with patch('literature_review.utils.api_manager.get_cost_tracker') as mock_get_tracker:
                        mock_get_tracker.return_value = tracker
                        
                        api_manager = APIManager(cache_dir=cache_dir)
                        
                        # Patch the actual API call
                        with patch.object(api_manager.client.models, 'generate_content', return_value=mock_response):
                            # Make an API call with tracking metadata
                            result = api_manager.cached_api_call(
                                prompt="Test prompt",
                                use_cache=False,
                                module='test_module',
                                operation='test_operation',
                                paper='test_paper.pdf'
                            )
                            
                            # Verify result
                            assert result is not None
                            assert result == {"result": "test"}
                            
                            # Verify cost was logged
                            assert len(tracker.usage_log) == 1
                            
                            entry = tracker.usage_log[0]
                            assert entry['module'] == 'test_module'
                            assert entry['model'] == 'gemini-2.5-flash'
                            assert entry['operation'] == 'test_operation'
                            assert entry['paper'] == 'test_paper.pdf'
                            assert entry['tokens']['input'] == 1000
                            assert entry['tokens']['output'] == 500
                            assert entry['tokens']['cached'] == 0
                            assert entry['cost_usd'] == 0.0  # Free tier
    
    def test_api_manager_handles_missing_usage_metadata(self):
        """Test that API manager handles responses without usage metadata gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, 'api_cache')
            cost_log = os.path.join(tmpdir, 'cost_log.json')
            
            tracker = CostTracker(log_file=cost_log)
            
            # Mock response without usage metadata
            mock_response = Mock()
            mock_response.text = '{"result": "test"}'
            # Don't set usage_metadata attribute
            
            with patch('literature_review.utils.api_manager.genai.Client'):
                with patch('literature_review.utils.api_manager.SentenceTransformer'):
                    with patch('literature_review.utils.api_manager.get_cost_tracker') as mock_get_tracker:
                        mock_get_tracker.return_value = tracker
                        
                        api_manager = APIManager(cache_dir=cache_dir)
                        
                        with patch.object(api_manager.client.models, 'generate_content', return_value=mock_response):
                            # Should not crash even without usage metadata
                            result = api_manager.cached_api_call(
                                prompt="Test prompt",
                                use_cache=False,
                                module='test_module'
                            )
                            
                            # Verify result still works
                            assert result is not None
                            assert result == {"result": "test"}
                        
                        # Cost tracking may have failed gracefully
                        # (no usage_log entry is acceptable)
    
    def test_cost_tracking_does_not_fail_api_call(self):
        """Test that cost tracking errors don't cause API calls to fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, 'api_cache')
            
            # Mock response with usage metadata
            mock_response = Mock()
            mock_response.text = '{"result": "test"}'
            mock_usage = Mock()
            mock_usage.prompt_token_count = 1000
            mock_usage.candidates_token_count = 500
            mock_response.usage_metadata = mock_usage
            
            with patch('literature_review.utils.api_manager.genai.Client'):
                with patch('literature_review.utils.api_manager.SentenceTransformer'):
                    with patch('literature_review.utils.api_manager.get_cost_tracker') as mock_get_tracker:
                        # Make get_cost_tracker raise an error
                        mock_get_tracker.side_effect = Exception("Cost tracker error")
                        
                        api_manager = APIManager(cache_dir=cache_dir)
                        
                        with patch.object(api_manager.client.models, 'generate_content', return_value=mock_response):
                            # Should still work even if cost tracking fails
                            result = api_manager.cached_api_call(
                                prompt="Test prompt",
                                use_cache=False,
                                module='test_module'
                            )
                            
                            # Verify result
                            assert result is not None
                            assert result == {"result": "test"}
