# Task Card: API Cost Tracker & Budget Management

**Task ID:** ENHANCE-W1-3  
**Wave:** 1 (Foundation & Quick Wins)  
**Priority:** HIGH  
**Estimated Effort:** 6 hours  
**Status:** Not Started  
**Dependencies:** None

---

## Objective

Track API costs in real-time and prevent surprise bills by monitoring usage against budgets.

## Background

Neither third-party review addressed API costs, but this is critical for production use. Current system uses Gemini API with varying costs per model. Need visibility into costs to make informed decisions.

## Success Criteria

- [ ] Know exact cost of each pipeline run
- [ ] Track costs per module (Journal Reviewer, Judge, Deep Reviewer)
- [ ] Budget warnings before expensive operations
- [ ] Cost reports generated automatically
- [ ] Identify optimization opportunities (cache hits, model selection)

## Deliverables

### 1. Cost Tracking Module

**File:** `literature_review/utils/cost_tracker.py`

```python
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
            with open(self.log_file, 'r') as f:
                return json.load(f)
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
        
        # Check cache efficiency
        if cache_eff['cache_hit_rate_percent'] < 20:
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
        if per_paper and per_paper['avg_cost_per_paper'] > 2.0:
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
```

### 2. Integration with API Manager

**File:** `literature_review/utils/api_manager.py` (modifications)

```python
# Add at top of file
from literature_review.utils.cost_tracker import get_cost_tracker

class APIManager:
    # ... existing code ...
    
    def call_api(self, prompt: str, model: str = None, **kwargs):
        """Make API call (MODIFIED to track costs)."""
        
        # ... existing API call logic ...
        
        response = self.client.models.generate_content(...)
        
        # NEW: Track cost
        cost_tracker = get_cost_tracker()
        
        # Extract token counts from response
        usage_metadata = response.usage_metadata
        input_tokens = usage_metadata.prompt_token_count
        output_tokens = usage_metadata.candidates_token_count
        cached_tokens = usage_metadata.cached_content_token_count if hasattr(usage_metadata, 'cached_content_token_count') else 0
        
        # Log the API call
        cost_tracker.log_api_call(
            module=kwargs.get('module', 'unknown'),
            model=model or self.default_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            operation=kwargs.get('operation', ''),
            paper=kwargs.get('paper', '')
        )
        
        return response
```

### 3. Budget Check in Orchestrator

**File:** `pipeline_orchestrator.py` (additions)

```python
from literature_review.utils.cost_tracker import get_cost_tracker

class PipelineOrchestrator:
    def __init__(self, config):
        # ... existing code ...
        self.cost_tracker = get_cost_tracker()
        self.budget_usd = config.get('budget_usd', 50.0)
    
    def run(self):
        """Run pipeline with budget monitoring."""
        
        # Check budget at start
        budget_status = self.cost_tracker.get_budget_status(self.budget_usd)
        
        if budget_status['over_budget']:
            logger.error(f"⚠️ Over budget! Spent ${budget_status['spent']:.2f} / ${budget_status['budget']:.2f}")
            raise RuntimeError("Budget exceeded. Increase budget or clear cost log.")
        
        if budget_status['at_risk']:
            logger.warning(f"⚠️ Budget at risk: ${budget_status['remaining']:.2f} remaining")
        
        # ... run pipeline stages ...
        
        # Generate cost report at end
        logger.info("\n=== COST REPORT ===")
        report = self.cost_tracker.generate_report()
        
        session_cost = report['session_summary']['total_cost']
        logger.info(f"Session cost: ${session_cost:.4f}")
        logger.info(f"Total cost: ${report['total_summary']['total_cost']:.4f}")
        logger.info(f"Budget remaining: ${budget_status['remaining']:.2f}")
        
        if report['recommendations']:
            logger.info("\nRecommendations:")
            for rec in report['recommendations']:
                logger.info(f"  {rec}")
```

### 4. Cost Report CLI

**File:** `scripts/generate_cost_report.py`

```python
#!/usr/bin/env python3
"""Generate API cost report."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.utils.cost_tracker import get_cost_tracker


def main():
    tracker = get_cost_tracker()
    report = tracker.generate_report()
    
    print("\n" + "="*60)
    print("API COST REPORT")
    print("="*60)
    
    total = report['total_summary']
    print(f"\n📊 Total Usage:")
    print(f"   API Calls: {total['total_calls']}")
    print(f"   Total Cost: ${total['total_cost']:.4f}")
    print(f"   Total Tokens: {total['total_tokens']:,}")
    print(f"   Cache Savings: ${total['total_cache_savings']:.4f}")
    
    budget = report['budget_status']
    print(f"\n💰 Budget Status:")
    print(f"   Budget: ${budget['budget']:.2f}")
    print(f"   Spent: ${budget['spent']:.2f}")
    print(f"   Remaining: ${budget['remaining']:.2f}")
    print(f"   Used: {budget['percent_used']:.1f}%")
    
    if total['by_module']:
        print(f"\n📦 By Module:")
        for module, data in sorted(total['by_module'].items(), key=lambda x: x[1]['cost'], reverse=True):
            print(f"   {module:20s}: ${data['cost']:.4f} ({data['calls']} calls)")
    
    cache = report['cache_efficiency']
    print(f"\n🗃️  Cache Efficiency:")
    print(f"   Hit Rate: {cache['cache_hit_rate_percent']:.1f}%")
    print(f"   Savings: ${cache['total_savings_usd']:.4f}")
    
    if 'per_paper_analysis' in report and report['per_paper_analysis']:
        per_paper = report['per_paper_analysis']
        print(f"\n📄 Per-Paper Analysis:")
        print(f"   Papers Analyzed: {per_paper['total_papers_analyzed']}")
        print(f"   Avg Cost/Paper: ${per_paper['avg_cost_per_paper']:.4f}")
        print(f"   Range: ${per_paper['min_cost']:.4f} - ${per_paper['max_cost']:.4f}")
    
    if report['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"   {rec}")
    
    print("\n" + "="*60)
    print(f"Full report saved to: cost_reports/api_usage_report.json")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
```

## Testing Plan

### Unit Tests

```python
# tests/unit/test_cost_tracker.py

import pytest
from literature_review.utils.cost_tracker import CostTracker

def test_cost_calculation():
    """Test cost calculation for different models."""
    tracker = CostTracker()
    
    # Test Gemini Flash
    cost = tracker._calculate_cost('gemini-1.5-flash', 1000, 500, 0)
    expected = (1000 * 0.075 / 1_000_000) + (500 * 0.30 / 1_000_000)
    assert abs(cost - expected) < 0.000001

def test_budget_status():
    """Test budget status tracking."""
    tracker = CostTracker()
    # Add some test data
    # ...
    status = tracker.get_budget_status(50.0)
    assert 'budget' in status
    assert 'spent' in status
```

### Integration Tests

```bash
# Test cost tracking in real pipeline
python pipeline_orchestrator.py --budget 10.0

# Generate cost report
python scripts/generate_cost_report.py
```

## Acceptance Criteria

- [ ] Costs tracked accurately for all API calls
- [ ] Cost report generated automatically after pipeline
- [ ] Budget warnings trigger before expensive operations
- [ ] Cache efficiency calculated correctly
- [ ] Recommendations are actionable
- [ ] Cost per paper analysis works
- [ ] Integration with API manager is seamless

## Integration Points

- Modify `api_manager.py` to call `cost_tracker.log_api_call()`
- Add budget check to `pipeline_orchestrator.py`
- Generate cost report in gap analysis output

## Notes

- Pricing may change - keep `GEMINI_PRICING` dict updated
- Consider adding email alerts for budget warnings
- Track free tier usage separately

## Related Tasks

- ENHANCE-W1-4 (Incremental Mode) - Will reduce costs through caching
- ENHANCE-W3-1 (Intelligent Triggers) - Will optimize Deep Reviewer costs

---

**Created:** 2025-11-16  
**Assigned To:** TBD  
**Target Completion:** Wave 1 (Week 1)
