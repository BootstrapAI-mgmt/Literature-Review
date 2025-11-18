# Cost-Aware Search Optimization Guide

## Overview

The cost-aware search optimization feature enhances the ROI-based search prioritization by considering API costs. This allows researchers to make budget-conscious decisions when planning literature searches.

## Features

### 1. API Cost Estimation

The system tracks costs for different search APIs:

**Free APIs:**
- Semantic Scholar: $0
- arXiv: $0
- CrossRef: $0

**Paid APIs:**
- OpenAI Embeddings: ~$0.0001 per search
- Anthropic Claude: ~$0.02-$0.10 per search (token-based)

### 2. Optimization Modes

The system supports three optimization modes:

#### Coverage Mode (`mode: "coverage"`)
- **Goal:** Maximize gap coverage
- **Behavior:** Ignores API costs, prioritizes high-severity gaps
- **Use Case:** When budget is not a constraint
- **Formula:** ROI = gap_severity × expected_papers

#### Cost Mode (`mode: "cost"`)
- **Goal:** Minimize API costs while maintaining quality
- **Behavior:** Strongly favors free or low-cost APIs
- **Use Case:** Tight budget constraints
- **Formula:** ROI = (gap_severity × expected_papers) / (cost + 0.01)

#### Balanced Mode (`mode: "balanced"`) - **Default**
- **Goal:** Balance coverage and cost efficiency
- **Behavior:** Considers both gap importance and cost
- **Use Case:** General research with moderate budget awareness
- **Formula:** ROI = (gap_severity × expected_papers) × (1 / (1 + cost))

### 3. Budget Constraints

Set a hard budget limit to automatically filter searches:

```json
{
  "roi_optimizer": {
    "mode": "balanced",
    "budget_limit": 50.0  // Max $50 USD
  }
}
```

**Behavior:**
1. Searches are sorted by cost-adjusted ROI
2. Searches are selected until budget is reached
3. Remaining searches are marked as "skipped"
4. Total cost stays within budget

### 4. Cost Metrics

Each prioritized search includes:

- **`cost`**: Estimated cost in USD
- **`roi`**: Cost-adjusted ROI score
- **`value_per_dollar`**: Gap value / cost ratio
- **`cost_weight`**: How much cost influenced prioritization (0.0-1.0)

## Configuration

### Basic Setup

Edit `pipeline_config.json`:

```json
{
  "roi_optimizer": {
    "enabled": true,
    "mode": "balanced",           // "coverage", "cost", or "balanced"
    "budget_limit": null,          // Set to USD amount or null for unlimited
    "show_cost_estimates": true,   // Display cost estimates before searches
    "cost_tracking": {
      "enabled": true,
      "alert_threshold": 0.8       // Alert at 80% of budget
    }
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `mode` | string | `"balanced"` | Optimization mode: `"coverage"`, `"cost"`, or `"balanced"` |
| `budget_limit` | number/null | `null` | Maximum budget in USD (null = unlimited) |
| `show_cost_estimates` | boolean | `true` | Show cost estimates before starting searches |
| `cost_tracking.enabled` | boolean | `true` | Enable cost tracking |
| `cost_tracking.alert_threshold` | number | `0.8` | Alert when this fraction of budget is used |

## Usage Examples

### Example 1: Budget-Constrained Research

```json
{
  "roi_optimizer": {
    "mode": "cost",
    "budget_limit": 25.0
  }
}
```

**Result:** Prioritizes free APIs, stays within $25 budget.

### Example 2: Maximum Coverage

```json
{
  "roi_optimizer": {
    "mode": "coverage",
    "budget_limit": null
  }
}
```

**Result:** Prioritizes critical gaps regardless of cost.

### Example 3: Balanced Approach (Recommended)

```json
{
  "roi_optimizer": {
    "mode": "balanced",
    "budget_limit": 100.0
  }
}
```

**Result:** Balances gap importance and cost, stays within $100.

## Cost Estimation Output

When cost tracking is enabled, you'll see output like:

```
=== Cost Estimate ===
Total Estimated Cost: $12.45

Search Breakdown:
  1. "machine learning papers" (Semantic Scholar) - $0.00
  2. "deep learning survey" (arXiv) - $0.00
  3. "LLM analysis" (Claude API) - $12.45

Budget Status: 2/3 searches within $25.00 budget
Skipped: 1 search (budget exceeded)
```

## API Pricing Details

### Token-Based Pricing (LLMs)

For APIs like Claude, cost is calculated based on tokens:

```
Cost = (input_tokens / 1000) × input_rate + (output_tokens / 1000) × output_rate
```

Default assumptions:
- Input tokens: 5,000 per search
- Output tokens: 2,000 per search

### Call-Based Pricing

For APIs with simple per-call pricing:

```
Cost = num_calls × cost_per_call
```

Number of calls is estimated as: `max_results / 10`

## Programmatic Usage

```python
from literature_review.optimization.search_optimizer import AdaptiveSearchOptimizer
from literature_review.utils.api_costs import CostEstimator

# Initialize optimizer with config
config = {
    'roi_optimizer': {
        'mode': 'balanced',
        'budget_limit': 50.0
    }
}

optimizer = AdaptiveSearchOptimizer(
    gap_analysis_file='gap_analysis.json',
    suggested_searches_file='searches.json',
    config=config
)

# Prioritize searches with cost awareness
searches = [
    {
        'query': 'neural networks',
        'api': 'semantic_scholar',
        'max_results': 50,
        'gap_severity': 'Critical',
        'papers_needed': 8
    }
]

prioritized = optimizer.prioritize_searches_with_cost(searches)

# Estimate total cost
cost_estimate = optimizer.estimate_total_cost(searches)
print(f"Total cost: ${cost_estimate['total_cost']:.2f}")
```

## Best Practices

1. **Start with Balanced Mode**: Good default for most use cases
2. **Set Realistic Budgets**: Include buffer for unexpected costs
3. **Review Cost Estimates**: Check estimates before running searches
4. **Monitor Actual Costs**: Compare estimates vs. actual usage
5. **Prioritize Free APIs**: For exploratory research, favor free sources
6. **Use Cost Mode for Tight Budgets**: When funds are limited
7. **Use Coverage Mode for Critical Research**: When quality trumps cost

## Troubleshooting

### Issue: All searches skipped

**Cause:** Budget too low for any search
**Solution:** Increase `budget_limit` or switch to `"cost"` mode

### Issue: Costs higher than expected

**Cause:** Token usage exceeded estimates
**Solution:** Review actual API usage, adjust token estimates

### Issue: Free APIs not prioritized in Cost mode

**Cause:** Gap severity differences override cost savings
**Solution:** Verify gap severity ratings are accurate

## Advanced Features

### Custom API Pricing

You can define custom pricing for additional APIs:

```python
from literature_review.utils.api_costs import CostEstimator

custom_pricing = {
    'my_api': {
        'cost_per_call': 0.05
    }
}

estimator = CostEstimator(pricing=custom_pricing)
```

### Cost Tracking Integration

Cost estimates integrate with existing cost tracking:

```python
from literature_review.utils.cost_tracker import CostTracker

tracker = CostTracker()
# Use tracker to log actual costs and compare with estimates
```

## Future Enhancements

Planned features for future releases:

- Real-time cost monitoring during searches
- Multi-tier API pricing support
- Cost optimization recommendations
- Historical cost analysis
- Budget allocation suggestions

## See Also

- [ROI Optimizer Documentation](../ENHANCE_W3_2A_IMPLEMENTATION_SUMMARY.md)
- [Search Optimization Guide](../README.md#search-optimization)
- [Pipeline Configuration Reference](../pipeline_config.json)
