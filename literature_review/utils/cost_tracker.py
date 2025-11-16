"""
API Cost Tracker
Track and analyze API usage costs across all modules.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class CostTracker:
    """Track API costs across all modules."""
    
    # Gemini API Pricing (as of Nov 2025)
    # https://ai.google.dev/pricing
    GEMINI_PRICING = {
        'gemini-2.0-flash-thinking-exp': {
            'input': 0.0,           # Free tier
            'output': 0.0,          # Free tier
            'cached_input': 0.0     # Free tier
        },
        'gemini-2.5-flash': {
            'input': 0.0,           # Free tier
            'output': 0.0,          # Free tier
            'cached_input': 0.0     # Free tier
        },
        'gemini-1.5-pro': {
            'input': 1.25 / 1_000_000,      # $1.25 per 1M tokens
            'output': 5.00 / 1_000_000,     # $5.00 per 1M tokens
            'cached_input': 0.3125 / 1_000_000  # 75% discount on cached
        },
        'gemini-1.5-flash': {
            'input': 0.075 / 1_000_000,     # $0.075 per 1M tokens
            'output': 0.30 / 1_000_000,     # $0.30 per 1M tokens
            'cached_input': 0.01875 / 1_000_000  # 75% discount
        }
    }
    
    def __init__(self, log_file: str = 'cost_reports/api_cost_log.json'):
        self.log_file = log_file
        self.usage_log = self._load_log()
        self.session_start = datetime.now().isoformat()
    
    def _load_log(self) -> List[Dict]:
        """Load existing cost log."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load cost log from {self.log_file}: {e}")
        return []
    
    def _save_log(self):
        """Save cost log to file."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'w') as f:
            json.dump(self.usage_log, f, indent=2)
    
    def log_api_call(self, module: str, model: str, input_tokens: int, 
                    output_tokens: int, cached_tokens: int = 0, 
                    operation: str = '', paper: str = ''):
        """
        Log a single API call with cost calculation.
        
        Args:
            module: Module name (journal_reviewer, judge, deep_reviewer, etc.)
            model: Gemini model used
            input_tokens: Input token count
            output_tokens: Output token count
            cached_tokens: Cached input tokens (already processed)
            operation: Optional operation description
            paper: Optional paper filename
        """
        cost = self._calculate_cost(model, input_tokens, output_tokens, cached_tokens)
        
        # Calculate cache savings
        cache_savings = 0
        if cached_tokens > 0 and model in self.GEMINI_PRICING:
            pricing = self.GEMINI_PRICING[model]
            full_cost = cached_tokens * pricing['input']
            cached_cost = cached_tokens * pricing.get('cached_input', pricing['input'])
            cache_savings = full_cost - cached_cost
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'module': module,
            'model': model,
            'operation': operation,
            'paper': paper,
            'tokens': {
                'input': input_tokens,
                'output': output_tokens,
                'cached': cached_tokens,
                'total': input_tokens + output_tokens
            },
            'cost_usd': round(cost, 6),
            'cache_savings_usd': round(cache_savings, 6)
        }
        
        self.usage_log.append(entry)
        self._save_log()
        
        logger.debug(f"API call logged: {module} - ${cost:.4f}")
    
    def _calculate_cost(self, model: str, input_tokens: int, 
                       output_tokens: int, cached_tokens: int) -> float:
        """Calculate cost for an API call."""
        if model not in self.GEMINI_PRICING:
            logger.warning(f"Unknown model: {model}, assuming free tier")
            return 0.0
        
        pricing = self.GEMINI_PRICING[model]
        
        # Regular input tokens (not cached)
        regular_input_tokens = input_tokens - cached_tokens
        
        cost = (
            regular_input_tokens * pricing['input'] +
            output_tokens * pricing['output'] +
            cached_tokens * pricing.get('cached_input', pricing['input'])
        )
        
        return cost
    
    def get_session_summary(self) -> Dict:
        """Get cost summary for current session."""
        session_calls = [
            call for call in self.usage_log
            if call['timestamp'] >= self.session_start
        ]
        
        return self._summarize_calls(session_calls)
    
    def get_total_summary(self) -> Dict:
        """Get cost summary for all time."""
        return self._summarize_calls(self.usage_log)
    
    def _summarize_calls(self, calls: List[Dict]) -> Dict:
        """Summarize a list of API calls."""
        if not calls:
            return {
                'total_calls': 0,
                'total_cost': 0.0,
                'total_tokens': 0,
                'total_cache_savings': 0.0,
                'by_module': {},
                'by_model': {}
            }
        
        total_cost = sum(call['cost_usd'] for call in calls)
        total_tokens = sum(call['tokens']['total'] for call in calls)
        total_cache_savings = sum(call.get('cache_savings_usd', 0) for call in calls)
        
        # Group by module
        by_module = {}
        for call in calls:
            module = call['module']
            if module not in by_module:
                by_module[module] = {
                    'calls': 0,
                    'cost': 0.0,
                    'tokens': 0,
                    'cache_savings': 0.0
                }
            by_module[module]['calls'] += 1
            by_module[module]['cost'] += call['cost_usd']
            by_module[module]['tokens'] += call['tokens']['total']
            by_module[module]['cache_savings'] += call.get('cache_savings_usd', 0)
        
        # Group by model
        by_model = {}
        for call in calls:
            model = call['model']
            if model not in by_model:
                by_model[model] = {
                    'calls': 0,
                    'cost': 0.0,
                    'tokens': 0
                }
            by_model[model]['calls'] += 1
            by_model[model]['cost'] += call['cost_usd']
            by_model[model]['tokens'] += call['tokens']['total']
        
        return {
            'total_calls': len(calls),
            'total_cost': round(total_cost, 4),
            'total_tokens': total_tokens,
            'total_cache_savings': round(total_cache_savings, 4),
            'by_module': by_module,
            'by_model': by_model
        }
    
    def get_budget_status(self, budget_usd: float = 50.0) -> Dict:
        """
        Check budget status.
        
        Args:
            budget_usd: Monthly budget in USD
        
        Returns:
            Budget status dictionary
        """
        summary = self.get_total_summary()
        total_cost = summary['total_cost']
        
        return {
            'budget': budget_usd,
            'spent': total_cost,
            'remaining': budget_usd - total_cost,
            'percent_used': round((total_cost / budget_usd) * 100, 1) if budget_usd > 0 else 0,
            'at_risk': total_cost > (budget_usd * 0.8),
            'over_budget': total_cost > budget_usd
        }
    
    def cost_per_paper_analysis(self) -> Dict:
        """Analyze cost efficiency per paper."""
        analysis = {}
        
        # Group by paper
        paper_costs = {}
        for call in self.usage_log:
            paper = call.get('paper', 'unknown')
            if not paper or paper == 'unknown':
                continue
            
            if paper not in paper_costs:
                paper_costs[paper] = {
                    'calls': 0,
                    'cost': 0.0,
                    'modules': set()
                }
            
            paper_costs[paper]['calls'] += 1
            paper_costs[paper]['cost'] += call['cost_usd']
            paper_costs[paper]['modules'].add(call['module'])
        
        # Calculate averages
        if paper_costs:
            total_papers = len(paper_costs)
            avg_cost_per_paper = sum(p['cost'] for p in paper_costs.values()) / total_papers
            
            analysis = {
                'total_papers_analyzed': total_papers,
                'avg_cost_per_paper': round(avg_cost_per_paper, 4),
                'min_cost': round(min(p['cost'] for p in paper_costs.values()), 4),
                'max_cost': round(max(p['cost'] for p in paper_costs.values()), 4),
                'most_expensive_papers': sorted(
                    [
                        {'paper': p, 'cost': data['cost']}
                        for p, data in paper_costs.items()
                    ],
                    key=lambda x: x['cost'],
                    reverse=True
                )[:5]
            }
        
        return analysis
    
    def generate_report(self, output_file: str = 'cost_reports/api_usage_report.json'):
        """Generate comprehensive cost report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'session_summary': self.get_session_summary(),
            'total_summary': self.get_total_summary(),
            'budget_status': self.get_budget_status(),
            'per_paper_analysis': self.cost_per_paper_analysis(),
            'cache_efficiency': self._calculate_cache_efficiency(),
            'recommendations': self._generate_recommendations()
        }
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Cost report saved to {output_file}")
        return report
    
    def _calculate_cache_efficiency(self) -> Dict:
        """Calculate cache hit efficiency."""
        total_input_tokens = sum(call['tokens']['input'] for call in self.usage_log)
        total_cached_tokens = sum(call['tokens']['cached'] for call in self.usage_log)
        
        cache_hit_rate = 0
        if total_input_tokens > 0:
            cache_hit_rate = (total_cached_tokens / total_input_tokens) * 100
        
        total_savings = sum(call.get('cache_savings_usd', 0) for call in self.usage_log)
        
        return {
            'cache_hit_rate_percent': round(cache_hit_rate, 1),
            'total_tokens_cached': total_cached_tokens,
            'total_savings_usd': round(total_savings, 4)
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        summary = self.get_total_summary()
        cache_eff = self._calculate_cache_efficiency()
        
        # Only generate recommendations if there's actual data
        if summary['total_calls'] == 0:
            recommendations.append("✅ No API calls logged yet. Start using the system to get recommendations!")
            return recommendations
        
        # Check cache efficiency (only if there are calls)
        if cache_eff['cache_hit_rate_percent'] < 20 and summary['total_calls'] > 5:
            recommendations.append(
                "⚠️ Low cache hit rate ({:.1f}%). Consider enabling prompt caching.".format(
                    cache_eff['cache_hit_rate_percent']
                )
            )
        
        # Check model usage
        if 'by_model' in summary:
            pro_usage = summary['by_model'].get('gemini-1.5-pro', {}).get('cost', 0)
            total_cost = summary['total_cost']
            
            if pro_usage > total_cost * 0.5 and total_cost > 5:
                recommendations.append(
                    "💡 Consider using gemini-1.5-flash for routine tasks. "
                    "Pro model costs are {:.0f}% of total.".format((pro_usage / total_cost) * 100)
                )
        
        # Check per-paper efficiency
        per_paper = self.cost_per_paper_analysis()
        if per_paper and per_paper.get('avg_cost_per_paper', 0) > 2.0:
            recommendations.append(
                "💡 High cost per paper (${:.2f}). Consider document chunking or model optimization.".format(
                    per_paper['avg_cost_per_paper']
                )
            )
        
        if not recommendations:
            recommendations.append("✅ Cost efficiency looks good!")
        
        return recommendations


# Singleton instance
_cost_tracker = None


def get_cost_tracker() -> CostTracker:
    """Get global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
