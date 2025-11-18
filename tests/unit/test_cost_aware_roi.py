"""Unit tests for cost-aware search optimization."""

import pytest
import json
import tempfile
from pathlib import Path
from literature_review.optimization.search_optimizer import AdaptiveSearchOptimizer


@pytest.fixture
def sample_gap_data():
    """Sample gap analysis data for testing."""
    return {
        "Pillar 1: Test Pillar": {
            "completeness": 40.0,
            "analysis": {
                "REQ-T1.1: Test Requirement Group": {
                    "Sub-1.1.1: Critical gap requirement": {
                        "completeness_percent": 10,
                        "gap_analysis": "Critical gap",
                        "confidence_level": "high",
                        "contributing_papers": [
                            {"filename": "paper1.pdf", "title": "Paper 1"}
                        ]
                    },
                    "Sub-1.1.2: Low priority requirement": {
                        "completeness_percent": 95,
                        "gap_analysis": "Well covered",
                        "confidence_level": "high",
                        "contributing_papers": [
                            {"filename": f"paper{i}.pdf", "title": f"Paper {i}"} for i in range(10)
                        ]
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_searches():
    """Sample search queries for testing."""
    return [
        {
            "pillar": "Pillar 1",
            "requirement": "Critical gap requirement",
            "current_completeness": 10,
            "priority": "CRITICAL",
            "urgency": 1,
            "gap_description": "Critical gap",
            "suggested_searches": [
                {
                    "query": 'critical topic AND "specific method"',
                    "rationale": "Direct match",
                    "databases": ["Google Scholar"]
                }
            ]
        }
    ]


class TestCostAwareSearchOptimizer:
    """Test suite for cost-aware search optimization."""
    
    def test_prioritize_with_free_apis(self, tmp_path, sample_gap_data, sample_searches):
        """Test prioritization with free APIs."""
        gap_file = tmp_path / "gap.json"
        searches_file = tmp_path / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_data, f)
        with open(searches_file, 'w') as f:
            json.dump(sample_searches, f)
        
        config = {'roi_optimizer': {'mode': 'balanced'}}
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(searches_file), config=config)
        
        searches = [
            {'query': 'test query 1', 'api': 'semantic_scholar', 'max_results': 10, 
             'gap_severity': 'Critical', 'papers_needed': 5},
            {'query': 'test query 2', 'api': 'arxiv', 'max_results': 20,
             'gap_severity': 'High', 'papers_needed': 3}
        ]
        
        prioritized = optimizer.prioritize_searches_with_cost(searches)
        
        assert len(prioritized) == 2
        assert 'roi' in prioritized[0]
        assert 'cost' in prioritized[0]
        assert prioritized[0]['cost'] == 0.0  # Free API
        assert prioritized[1]['cost'] == 0.0  # Free API
    
    def test_prioritize_with_paid_apis(self, tmp_path, sample_gap_data, sample_searches):
        """Test prioritization with paid APIs."""
        gap_file = tmp_path / "gap.json"
        searches_file = tmp_path / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_data, f)
        with open(searches_file, 'w') as f:
            json.dump(sample_searches, f)
        
        config = {'roi_optimizer': {'mode': 'cost'}}
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(searches_file), config=config)
        
        searches = [
            {'query': 'expensive search', 'api': 'anthropic_claude', 'max_results': 100,
             'gap_severity': 'High', 'papers_needed': 5},
            {'query': 'free search', 'api': 'semantic_scholar', 'max_results': 10,
             'gap_severity': 'High', 'papers_needed': 5}
        ]
        
        prioritized = optimizer.prioritize_searches_with_cost(searches)
        
        # In 'cost' mode, free search should be prioritized
        assert prioritized[0]['query'] == 'free search'
        assert prioritized[0]['cost'] == 0.0
        assert prioritized[1]['cost'] > 0.0
    
    def test_coverage_mode(self, tmp_path, sample_gap_data, sample_searches):
        """Test coverage mode ignores cost."""
        gap_file = tmp_path / "gap.json"
        searches_file = tmp_path / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_data, f)
        with open(searches_file, 'w') as f:
            json.dump(sample_searches, f)
        
        config = {'roi_optimizer': {'mode': 'coverage'}}
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(searches_file), config=config)
        
        searches = [
            {'query': 'high severity', 'api': 'anthropic_claude', 'max_results': 100,
             'gap_severity': 'Critical', 'papers_needed': 8},
            {'query': 'low severity', 'api': 'semantic_scholar', 'max_results': 10,
             'gap_severity': 'Low', 'papers_needed': 2}
        ]
        
        prioritized = optimizer.prioritize_searches_with_cost(searches)
        
        # In coverage mode, high severity should be first regardless of cost
        assert prioritized[0]['query'] == 'high severity'
        assert prioritized[0]['cost_weight'] == 0.0
    
    def test_balanced_mode(self, tmp_path, sample_gap_data, sample_searches):
        """Test balanced mode considers both coverage and cost."""
        gap_file = tmp_path / "gap.json"
        searches_file = tmp_path / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_data, f)
        with open(searches_file, 'w') as f:
            json.dump(sample_searches, f)
        
        config = {'roi_optimizer': {'mode': 'balanced'}}
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(searches_file), config=config)
        
        searches = [
            {'query': 'search 1', 'api': 'semantic_scholar', 'max_results': 10,
             'gap_severity': 'High', 'papers_needed': 5}
        ]
        
        prioritized = optimizer.prioritize_searches_with_cost(searches)
        
        assert prioritized[0]['cost_weight'] == 0.5
    
    def test_budget_constraint(self, tmp_path, sample_gap_data, sample_searches):
        """Test budget limit enforcement."""
        gap_file = tmp_path / "gap.json"
        searches_file = tmp_path / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_data, f)
        with open(searches_file, 'w') as f:
            json.dump(sample_searches, f)
        
        config = {'roi_optimizer': {'mode': 'balanced', 'budget_limit': 0.05}}
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(searches_file), config=config)
        
        searches = [
            {'query': 'search 1', 'api': 'openai_embedding', 'max_results': 10,
             'gap_severity': 'Critical', 'papers_needed': 8},
            {'query': 'search 2', 'api': 'anthropic_claude', 'max_results': 100,
             'gap_severity': 'High', 'papers_needed': 5},
            {'query': 'search 3', 'api': 'semantic_scholar', 'max_results': 10,
             'gap_severity': 'Medium', 'papers_needed': 3}
        ]
        
        prioritized = optimizer.prioritize_searches_with_cost(searches)
        
        # Should include searches within budget
        # Budget is $0.05, search 2 (Claude) is expensive and might be excluded
        total_cost = sum(s.get('cost', 0) for s in prioritized if not s.get('skipped', False))
        assert total_cost <= 0.05
    
    def test_apply_budget_constraint_directly(self, tmp_path, sample_gap_data, sample_searches):
        """Test budget constraint application."""
        gap_file = tmp_path / "gap.json"
        searches_file = tmp_path / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_data, f)
        with open(searches_file, 'w') as f:
            json.dump(sample_searches, f)
        
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(searches_file))
        
        searches = [
            {'query': 'search 1', 'cost': 5.0, 'roi': 10.0},
            {'query': 'search 2', 'cost': 3.0, 'roi': 8.0},
            {'query': 'search 3', 'cost': 4.0, 'roi': 6.0}
        ]
        
        constrained = optimizer._apply_budget_constraint(searches, budget_limit=8.0)
        
        # Only first two searches fit in $8 budget
        assert len(constrained) == 2
        assert constrained[0]['query'] == 'search 1'
        assert constrained[1]['query'] == 'search 2'
    
    def test_severity_to_numeric(self, tmp_path, sample_gap_data, sample_searches):
        """Test severity conversion to numeric values."""
        gap_file = tmp_path / "gap.json"
        searches_file = tmp_path / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_data, f)
        with open(searches_file, 'w') as f:
            json.dump(sample_searches, f)
        
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(searches_file))
        
        assert optimizer._severity_to_numeric('Critical') == 9.0
        assert optimizer._severity_to_numeric('High') == 7.0
        assert optimizer._severity_to_numeric('Medium') == 5.0
        assert optimizer._severity_to_numeric('Low') == 3.0
        assert optimizer._severity_to_numeric('Covered') == 1.0
        assert optimizer._severity_to_numeric('Unknown') == 5.0  # Default
    
    def test_estimate_total_cost(self, tmp_path, sample_gap_data, sample_searches):
        """Test total cost estimation."""
        gap_file = tmp_path / "gap.json"
        searches_file = tmp_path / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_data, f)
        with open(searches_file, 'w') as f:
            json.dump(sample_searches, f)
        
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(searches_file))
        
        searches = [
            {'query': 'search 1', 'api': 'semantic_scholar', 'max_results': 10},
            {'query': 'search 2', 'api': 'openai_embedding', 'max_results': 10}
        ]
        
        cost_estimate = optimizer.estimate_total_cost(searches)
        
        assert 'total_cost' in cost_estimate
        assert 'search_costs' in cost_estimate
        assert cost_estimate['num_searches'] == 2
        assert cost_estimate['total_cost'] > 0  # Has cost from OpenAI
    
    def test_value_per_dollar_calculation(self, tmp_path, sample_gap_data, sample_searches):
        """Test value per dollar metric."""
        gap_file = tmp_path / "gap.json"
        searches_file = tmp_path / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_data, f)
        with open(searches_file, 'w') as f:
            json.dump(sample_searches, f)
        
        config = {'roi_optimizer': {'mode': 'balanced'}}
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(searches_file), config=config)
        
        searches = [
            {'query': 'paid search', 'api': 'openai_embedding', 'max_results': 10,
             'gap_severity': 'Critical', 'papers_needed': 5},
            {'query': 'free search', 'api': 'semantic_scholar', 'max_results': 10,
             'gap_severity': 'Critical', 'papers_needed': 5}
        ]
        
        prioritized = optimizer.prioritize_searches_with_cost(searches)
        
        # Free search should have infinite value per dollar
        free_search = next((s for s in prioritized if s['query'] == 'free search'), None)
        assert free_search is not None
        assert free_search['value_per_dollar'] == float('inf')
        
        # Paid search should have finite value per dollar
        paid_search = next((s for s in prioritized if s['query'] == 'paid search'), None)
        assert paid_search is not None
        assert paid_search['value_per_dollar'] < float('inf')
    
    def test_no_budget_limit(self, tmp_path, sample_gap_data, sample_searches):
        """Test that all searches are included when no budget limit."""
        gap_file = tmp_path / "gap.json"
        searches_file = tmp_path / "searches.json"
        
        with open(gap_file, 'w') as f:
            json.dump(sample_gap_data, f)
        with open(searches_file, 'w') as f:
            json.dump(sample_searches, f)
        
        config = {'roi_optimizer': {'mode': 'balanced', 'budget_limit': None}}
        optimizer = AdaptiveSearchOptimizer(str(gap_file), str(searches_file), config=config)
        
        searches = [
            {'query': 'search 1', 'api': 'anthropic_claude', 'max_results': 100,
             'gap_severity': 'Critical', 'papers_needed': 8},
            {'query': 'search 2', 'api': 'anthropic_claude', 'max_results': 100,
             'gap_severity': 'High', 'papers_needed': 5}
        ]
        
        prioritized = optimizer.prioritize_searches_with_cost(searches)
        
        # All searches should be included
        assert len(prioritized) == 2
        assert all(not s.get('skipped', False) for s in prioritized)
