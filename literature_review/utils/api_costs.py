"""
API Cost Estimator for Search Operations.

Estimates costs for different search APIs and provides budget management.
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


# API Pricing Configuration
API_PRICING = {
    'semantic_scholar': {
        'cost_per_call': 0.0,  # Free
        'rate_limit': 100,  # calls per 5 min
        'rate_limit_period': 300  # seconds
    },
    'arxiv': {
        'cost_per_call': 0.0,  # Free
        'rate_limit': 3,  # calls per second
        'rate_limit_period': 1
    },
    'crossref': {
        'cost_per_call': 0.0,  # Free
        'rate_limit': 50,
        'rate_limit_period': 1
    },
    'openai_embedding': {
        'cost_per_call': 0.0001,  # $0.0001 per 1K tokens (~1 call)
        'avg_tokens_per_call': 1000
    },
    'anthropic_claude': {
        'cost_per_1k_input_tokens': 0.003,  # $3 per 1M input tokens
        'cost_per_1k_output_tokens': 0.015,  # $15 per 1M output tokens
        'avg_input_tokens': 5000,
        'avg_output_tokens': 2000
    }
}


class CostEstimator:
    """Estimate API costs for searches."""
    
    def __init__(self, pricing: Optional[Dict] = None):
        """
        Initialize cost estimator.
        
        Args:
            pricing: Optional custom pricing dictionary. Uses API_PRICING by default.
        """
        self.pricing = pricing or API_PRICING
    
    def estimate_search_cost(self, search_config: Dict) -> Dict:
        """
        Estimate cost for a single search.
        
        Args:
            search_config: Search configuration dict with 'api' and 'max_results' keys
            
        Returns:
            Dict with cost information:
                - total_cost: Total estimated cost in USD
                - cost_per_call: Cost per API call
                - num_calls: Estimated number of API calls
                - api: API name
        """
        api = search_config.get('api', 'semantic_scholar')
        max_results = search_config.get('max_results', 10)
        
        # Estimate number of API calls (assume 10 results per call)
        num_calls = max(1, max_results // 10)
        
        if api not in self.pricing:
            logger.warning(f"Unknown API '{api}', assuming free")
            return {
                'total_cost': 0.0,
                'cost_per_call': 0.0,
                'num_calls': num_calls,
                'api': api
            }
        
        pricing = self.pricing[api]
        
        if 'cost_per_call' in pricing:
            # Simple per-call pricing
            cost_per_call = pricing['cost_per_call']
            total_cost = cost_per_call * num_calls
        
        elif 'cost_per_1k_input_tokens' in pricing:
            # Token-based pricing (LLM APIs)
            input_cost = (pricing['avg_input_tokens'] / 1000) * pricing['cost_per_1k_input_tokens']
            output_cost = (pricing['avg_output_tokens'] / 1000) * pricing['cost_per_1k_output_tokens']
            cost_per_call = input_cost + output_cost
            total_cost = cost_per_call * num_calls
        
        else:
            total_cost = 0.0
            cost_per_call = 0.0
        
        return {
            'total_cost': round(total_cost, 4),
            'cost_per_call': round(cost_per_call, 4),
            'num_calls': num_calls,
            'api': api
        }
    
    def estimate_job_cost(self, searches: List[Dict]) -> Dict:
        """
        Estimate total cost for all searches in a job.
        
        Args:
            searches: List of search configuration dicts
            
        Returns:
            Dict with job cost information:
                - total_cost: Total cost in USD
                - search_costs: List of per-search cost info
                - num_searches: Number of searches
                - avg_cost_per_search: Average cost per search
        """
        search_costs = []
        total_cost = 0.0
        
        for search in searches:
            cost_info = self.estimate_search_cost(search)
            search_costs.append({
                'query': search.get('query', ''),
                'cost': cost_info['total_cost'],
                'api': cost_info['api']
            })
            total_cost += cost_info['total_cost']
        
        return {
            'total_cost': round(total_cost, 4),
            'search_costs': search_costs,
            'num_searches': len(searches),
            'avg_cost_per_search': round(total_cost / len(searches), 4) if searches else 0
        }
