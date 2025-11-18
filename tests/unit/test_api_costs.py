"""Unit tests for API cost estimation."""

import pytest
from literature_review.utils.api_costs import CostEstimator, API_PRICING


class TestCostEstimator:
    """Test suite for CostEstimator class."""
    
    def test_estimate_free_api_cost(self):
        """Test cost estimation for free APIs (Semantic Scholar, arXiv)."""
        estimator = CostEstimator()
        
        # Test Semantic Scholar
        search = {'api': 'semantic_scholar', 'max_results': 100}
        cost = estimator.estimate_search_cost(search)
        
        assert cost['total_cost'] == 0.0, "Semantic Scholar should be free"
        assert cost['api'] == 'semantic_scholar'
        assert cost['num_calls'] == 10  # 100 results / 10 per call
        
        # Test arXiv
        search = {'api': 'arxiv', 'max_results': 50}
        cost = estimator.estimate_search_cost(search)
        
        assert cost['total_cost'] == 0.0, "arXiv should be free"
        assert cost['api'] == 'arxiv'
    
    def test_estimate_paid_api_cost(self):
        """Test cost estimation for paid APIs."""
        estimator = CostEstimator()
        
        # Test OpenAI embeddings
        search = {'api': 'openai_embedding', 'max_results': 10}
        cost = estimator.estimate_search_cost(search)
        
        assert cost['total_cost'] > 0, "OpenAI should have cost"
        assert cost['cost_per_call'] == 0.0001
        assert cost['num_calls'] == 1  # 10 results = 1 call
    
    def test_estimate_llm_api_cost(self):
        """Test cost estimation for LLM APIs with token-based pricing."""
        estimator = CostEstimator()
        
        # Test Claude API
        search = {'api': 'anthropic_claude', 'max_results': 10}
        cost = estimator.estimate_search_cost(search)
        
        assert cost['total_cost'] > 0, "Claude should have cost"
        
        # Verify token-based calculation
        # Input: 5000 tokens at $0.003 per 1K = $0.015
        # Output: 2000 tokens at $0.015 per 1K = $0.030
        # Total per call = $0.045
        expected_per_call = (5000 / 1000 * 0.003) + (2000 / 1000 * 0.015)
        assert cost['cost_per_call'] == round(expected_per_call, 4)
    
    def test_estimate_unknown_api(self):
        """Test handling of unknown APIs."""
        estimator = CostEstimator()
        
        search = {'api': 'unknown_api', 'max_results': 10}
        cost = estimator.estimate_search_cost(search)
        
        assert cost['total_cost'] == 0.0, "Unknown API should default to free"
        assert cost['api'] == 'unknown_api'
    
    def test_estimate_job_cost(self):
        """Test total cost estimation for multiple searches."""
        estimator = CostEstimator()
        
        searches = [
            {'query': 'free search 1', 'api': 'semantic_scholar', 'max_results': 10},
            {'query': 'free search 2', 'api': 'arxiv', 'max_results': 20},
            {'query': 'paid search', 'api': 'openai_embedding', 'max_results': 10}
        ]
        
        job_cost = estimator.estimate_job_cost(searches)
        
        assert job_cost['num_searches'] == 3
        assert job_cost['total_cost'] > 0, "Should have cost from paid API"
        assert len(job_cost['search_costs']) == 3
        
        # Verify individual search costs
        assert job_cost['search_costs'][0]['cost'] == 0.0  # Semantic Scholar
        assert job_cost['search_costs'][1]['cost'] == 0.0  # arXiv
        assert job_cost['search_costs'][2]['cost'] > 0  # OpenAI
    
    def test_default_api_selection(self):
        """Test that default API is semantic_scholar."""
        estimator = CostEstimator()
        
        search = {'max_results': 10}  # No 'api' key
        cost = estimator.estimate_search_cost(search)
        
        assert cost['api'] == 'semantic_scholar'
        assert cost['total_cost'] == 0.0
    
    def test_num_calls_calculation(self):
        """Test API call count estimation."""
        estimator = CostEstimator()
        
        # 10 results = 1 call
        search = {'api': 'semantic_scholar', 'max_results': 10}
        cost = estimator.estimate_search_cost(search)
        assert cost['num_calls'] == 1
        
        # 50 results = 5 calls (50 / 10)
        search = {'api': 'semantic_scholar', 'max_results': 50}
        cost = estimator.estimate_search_cost(search)
        assert cost['num_calls'] == 5
        
        # 5 results = 1 call (minimum)
        search = {'api': 'semantic_scholar', 'max_results': 5}
        cost = estimator.estimate_search_cost(search)
        assert cost['num_calls'] == 1
    
    def test_custom_pricing(self):
        """Test using custom pricing configuration."""
        custom_pricing = {
            'custom_api': {
                'cost_per_call': 0.05
            }
        }
        
        estimator = CostEstimator(pricing=custom_pricing)
        
        search = {'api': 'custom_api', 'max_results': 20}
        cost = estimator.estimate_search_cost(search)
        
        assert cost['total_cost'] == 0.1  # 2 calls * $0.05
        assert cost['cost_per_call'] == 0.05
    
    def test_avg_cost_per_search(self):
        """Test average cost per search calculation."""
        estimator = CostEstimator()
        
        searches = [
            {'query': 'search 1', 'api': 'openai_embedding', 'max_results': 10},
            {'query': 'search 2', 'api': 'openai_embedding', 'max_results': 10},
            {'query': 'search 3', 'api': 'semantic_scholar', 'max_results': 10}
        ]
        
        job_cost = estimator.estimate_job_cost(searches)
        
        # 2 searches * 0.0001 = 0.0002, average = 0.0002 / 3
        expected_avg = round(0.0002 / 3, 4)
        assert job_cost['avg_cost_per_search'] == expected_avg
    
    def test_empty_searches_list(self):
        """Test handling of empty searches list."""
        estimator = CostEstimator()
        
        job_cost = estimator.estimate_job_cost([])
        
        assert job_cost['total_cost'] == 0.0
        assert job_cost['num_searches'] == 0
        assert job_cost['avg_cost_per_search'] == 0
        assert job_cost['search_costs'] == []
    
    def test_cost_rounding(self):
        """Test that costs are properly rounded."""
        estimator = CostEstimator()
        
        search = {'api': 'anthropic_claude', 'max_results': 10}
        cost = estimator.estimate_search_cost(search)
        
        # Verify rounding to 4 decimal places
        assert isinstance(cost['total_cost'], float)
        assert isinstance(cost['cost_per_call'], float)
        
        # Check that values have at most 4 decimal places
        total_str = f"{cost['total_cost']:.4f}"
        assert cost['total_cost'] == float(total_str)


class TestAPIPricing:
    """Test API pricing configuration."""
    
    def test_api_pricing_structure(self):
        """Test that API_PRICING has expected structure."""
        # All APIs should have necessary fields
        for api_name, api_config in API_PRICING.items():
            assert isinstance(api_config, dict), f"{api_name} config should be dict"
            
            # Should have either cost_per_call or token-based pricing
            has_simple_pricing = 'cost_per_call' in api_config
            has_token_pricing = 'cost_per_1k_input_tokens' in api_config
            
            assert has_simple_pricing or has_token_pricing, \
                f"{api_name} should have pricing information"
    
    def test_free_apis(self):
        """Test that expected APIs are free."""
        free_apis = ['semantic_scholar', 'arxiv', 'crossref']
        
        for api_name in free_apis:
            assert api_name in API_PRICING, f"{api_name} should be in pricing"
            assert API_PRICING[api_name]['cost_per_call'] == 0.0, \
                f"{api_name} should be free"
    
    def test_paid_apis(self):
        """Test that expected APIs have costs."""
        paid_apis = ['openai_embedding', 'anthropic_claude']
        
        for api_name in paid_apis:
            assert api_name in API_PRICING, f"{api_name} should be in pricing"
