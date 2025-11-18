# Search Optimization Guide

This guide explains the ROI-based search optimization features in the Literature Review system, including the new adaptive ROI recalculation capability.

## Table of Contents

- [Overview](#overview)
- [Static ROI Optimization](#static-roi-optimization)
- [Adaptive ROI Recalculation](#adaptive-roi-recalculation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

## Overview

The Literature Review system uses Return on Investment (ROI) scoring to prioritize search queries. This ensures that limited search resources are allocated to the most critical knowledge gaps first.

**ROI Calculation Formula:**
```
ROI = (Gap Severity × Papers Needed × Query Specificity) / Search Cost
```

Where:
- **Gap Severity**: Urgency of filling the gap (Critical=3.0, High=2.0, Medium=1.0, Low=0.5)
- **Papers Needed**: Number of papers required to fill the gap (normalized)
- **Query Specificity**: Estimated success rate based on query complexity (0.5-0.9)
- **Search Cost**: Estimated cost/time to execute the search (default=1.0)

## Static ROI Optimization

The basic `SearchOptimizer` calculates ROI once at the start and produces a prioritized search plan.

### Usage

```python
from literature_review.optimization.search_optimizer import SearchOptimizer

optimizer = SearchOptimizer(
    gap_analysis_file='gap_analysis_output/gap_analysis.json',
    suggested_searches_file='gap_analysis_output/suggested_searches.json'
)

plan = optimizer.optimize_search_plan()

print(f"Total searches: {plan['total_searches']}")
print(f"High priority: {plan['high_priority_searches']}")
print(f"Execution order: {plan['execution_order'][:10]}")
```

### Limitations

- ROI calculated once at job start
- Doesn't adapt as searches complete
- May waste effort on already-covered gaps
- Misses opportunities to reprioritize based on new findings

## Adaptive ROI Recalculation

The `AdaptiveSearchOptimizer` dynamically adjusts priorities after each search batch, enabling:

- **Real-time adaptation**: ROI recalculated after each batch completes
- **Gap coverage tracking**: Updates coverage as new papers are found
- **Smart skipping**: Automatically skips searches for fully-covered gaps (>95%)
- **Convergence detection**: Stops when critical gaps are sufficiently covered (>80%)
- **Diminishing returns**: Stops if next search ROI drops below threshold

### How It Works

**Workflow:**

1. **Initial Prioritization**: Calculate ROI for all searches
2. **Execute Batch**: Run top N searches (configurable batch size)
3. **Update Coverage**: Add found papers to gap evidence
4. **Recalculate ROI**: Adjust priorities based on new coverage
5. **Reorder Queue**: Re-sort remaining searches by updated ROI
6. **Check Convergence**: Stop if critical gaps are covered
7. **Repeat**: Continue until convergence or diminishing returns

### Example Workflow

```
Initial State:
  Gap 1 (severity 8, coverage 0%) → Search A (ROI 5.0)
  Gap 2 (severity 7, coverage 0%) → Search B (ROI 4.5)
  Gap 3 (severity 6, coverage 0%) → Search C (ROI 3.0)

After Search A completes (found 6 papers for Gap 1):
  Gap 1 (severity 8, coverage 75%) → ROI reduced to 2.0
  Gap 2 (severity 7, coverage 0%) → ROI stays 4.5
  Gap 3 (severity 6, coverage 0%) → ROI stays 3.0
  
Priority changes: Search B now first!

After Search B completes (found 7 papers for Gap 2):
  Gap 1 (severity 8, coverage 75%) → ROI 2.0
  Gap 2 (severity 7, coverage 88%) → ROI reduced to 0.8
  Gap 3 (severity 6, coverage 0%) → ROI stays 3.0
  
Priority changes: Search C now first!

Convergence Check:
  Critical gaps (severity ≥7): Gap 1 (75%), Gap 2 (88%)
  All critical gaps >80% covered? NO
  Continue searching...
```

### Usage

```python
from literature_review.optimization.search_optimizer import AdaptiveSearchOptimizer

# Load configuration
with open('pipeline_config.json') as f:
    config = json.load(f)

# Create adaptive optimizer
optimizer = AdaptiveSearchOptimizer(
    gap_analysis_file='gap_analysis_output/gap_analysis.json',
    suggested_searches_file='gap_analysis_output/suggested_searches.json',
    config=config
)

# Define search execution function
def execute_batch(batch):
    """Execute a batch of searches and return results."""
    results = []
    for search in batch:
        # Call actual search API
        papers = search_google_scholar(search['query'])
        results.append({
            'search': search,
            'papers': papers
        })
    return results

# Run adaptive optimization
result = optimizer.optimize_searches_adaptive(
    mock_execute_batch=execute_batch
)

print(f"Completed {len(result['completed_searches'])} searches")
print(f"Convergence reached: {result['convergence_reached']}")
print(f"ROI history entries: {len(result['roi_history'])}")

# Analyze ROI evolution
for i, entry in enumerate(result['roi_history']):
    print(f"Batch {i+1}: Avg ROI={entry['avg_roi']:.2f}, "
          f"Top ROI={entry['top_search_roi']:.2f}")
```

## Configuration

Configuration is specified in `pipeline_config.json`:

```json
{
  "roi_optimizer": {
    "enabled": true,
    "adaptive_recalculation": true,
    "recalculation_frequency": "per_batch",
    "batch_size": 5,
    "min_roi_threshold": 0.1,
    "convergence_threshold": 0.8,
    "diminishing_returns_threshold": 0.5
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable ROI optimization |
| `adaptive_recalculation` | boolean | `true` | Enable dynamic priority adjustment |
| `recalculation_frequency` | string | `"per_batch"` | When to recalculate ROI (`"per_batch"` or `"every_n_searches"`) |
| `batch_size` | integer | `5` | Number of searches to execute before recalculating |
| `min_roi_threshold` | float | `0.1` | Stop if top search ROI drops below this value |
| `convergence_threshold` | float | `0.8` | Coverage % to consider critical gaps "covered" |
| `diminishing_returns_threshold` | float | `0.5` | ROI must be >50% of initial average (future use) |

## Usage Examples

### Example 1: Small Search Queue

For small search queues (<10 searches), static optimization may be sufficient:

```python
# Disable adaptive recalculation for deterministic execution
config = {
    'roi_optimizer': {
        'adaptive_recalculation': false
    }
}

optimizer = SearchOptimizer(gap_file, searches_file)
plan = optimizer.optimize_search_plan()
# Execute all searches in order
```

### Example 2: Large Search Queue with Critical Gaps

For large queues (>20 searches) with time constraints:

```python
# Enable adaptive optimization with aggressive convergence
config = {
    'roi_optimizer': {
        'adaptive_recalculation': true,
        'batch_size': 3,
        'convergence_threshold': 0.75,  # Stop when critical gaps 75% covered
        'min_roi_threshold': 0.2  # Higher threshold for faster stopping
    }
}

optimizer = AdaptiveSearchOptimizer(gap_file, searches_file, config)
result = optimizer.optimize_searches_adaptive(execute_batch)
```

### Example 3: Comprehensive Coverage

For thorough coverage without time constraints:

```python
# Conservative settings for maximum coverage
config = {
    'roi_optimizer': {
        'adaptive_recalculation': true,
        'batch_size': 10,  # Larger batches
        'convergence_threshold': 0.95,  # Very high bar
        'min_roi_threshold': 0.05  # Allow low-ROI searches
    }
}

optimizer = AdaptiveSearchOptimizer(gap_file, searches_file, config)
result = optimizer.optimize_searches_adaptive(execute_batch)
```

## Best Practices

### When to Use Adaptive ROI

**Enable Adaptive ROI if:**
- Large search queue (>20 searches)
- Want to minimize wasted effort
- Critical gaps must be covered ASAP
- Limited time or API quota
- Want to track optimization progress

**Disable if:**
- Small search queue (<10 searches)
- Want to execute all searches regardless
- Deterministic execution required
- Debugging/testing specific searches

### Batch Size Selection

- **Small batches (2-3)**: More frequent recalculation, faster adaptation, higher overhead
- **Medium batches (5-7)**: Good balance for most use cases
- **Large batches (10+)**: Less overhead, slower adaptation, better for stable priorities

### Threshold Tuning

**Convergence Threshold:**
- `0.95`: Very strict (near-perfect coverage)
- `0.80`: Recommended (good coverage)
- `0.60`: Lenient (basic coverage)

**Min ROI Threshold:**
- `0.2`: Aggressive (stop early, save resources)
- `0.1`: Recommended (good balance)
- `0.05`: Conservative (execute more searches)

### Monitoring ROI Evolution

Track ROI history to understand optimization behavior:

```python
result = optimizer.optimize_searches_adaptive(execute_batch)

# Analyze ROI trends
roi_history = result['roi_history']
for entry in roi_history:
    print(f"Time: {entry['timestamp']}")
    print(f"  Completed: {entry['completed_count']}")
    print(f"  Pending: {entry['pending_count']}")
    print(f"  Avg ROI: {entry['avg_roi']:.2f}")
    print(f"  Top ROI: {entry['top_search_roi']:.2f}")
```

### Debugging Low Coverage

If convergence is not reached:

1. **Check gap severity**: Are critical gaps properly identified?
2. **Review search quality**: Are searches finding relevant papers?
3. **Adjust thresholds**: Lower convergence threshold or min ROI threshold
4. **Increase batch size**: Allow more searches before stopping

### Performance Considerations

- **Memory**: ROI history grows with number of batches (minimal impact)
- **Computation**: Recalculation is O(n) where n = pending searches (fast)
- **API calls**: Batch size affects API rate limiting strategy

## Advanced Features

### ROI History Export

```python
import json

result = optimizer.optimize_searches_adaptive(execute_batch)

# Export ROI history for analysis
with open('roi_history.json', 'w') as f:
    json.dump(result['roi_history'], f, indent=2)
```

### Custom Gap Severity Calculation

Extend `AdaptiveSearchOptimizer` to customize severity:

```python
class CustomOptimizer(AdaptiveSearchOptimizer):
    def _recalculate_severity(self, gap):
        """Custom severity calculation."""
        base_severity = gap['base_severity']
        coverage = gap['current_coverage']
        
        # Custom logic: exponential decay
        import math
        adjusted = base_severity * math.exp(-2 * coverage)
        
        return adjusted
```

### Integration with Search APIs

```python
from literature_review.search import GoogleScholarSearch

def execute_search_batch(batch):
    """Execute searches using Google Scholar API."""
    searcher = GoogleScholarSearch()
    results = []
    
    for search in batch:
        papers = searcher.search(
            query=search['query'],
            max_results=10
        )
        
        results.append({
            'search': search,
            'papers': papers,
            'target_gap_ids': [search['requirement']]
        })
    
    return results

optimizer = AdaptiveSearchOptimizer(gap_file, searches_file, config)
result = optimizer.optimize_searches_adaptive(execute_search_batch)
```

## Troubleshooting

### Issue: All searches skipped

**Cause**: All gaps marked as fully covered (>95%)

**Solution**: 
- Check gap initialization
- Review completeness calculations
- Lower skip threshold in code if needed

### Issue: Convergence never reached

**Cause**: Critical gaps not reaching threshold

**Solution**:
- Lower `convergence_threshold` in config
- Review search query quality
- Check if papers are being properly associated with gaps

### Issue: Too many searches executed

**Cause**: Min ROI threshold too low

**Solution**:
- Increase `min_roi_threshold` in config
- Reduce `batch_size` for more frequent checks
- Enable stricter convergence criteria

### Issue: Important gaps not prioritized

**Cause**: Gap severity calculation issue

**Solution**:
- Review completeness percentages in gap analysis
- Check severity mapping logic
- Verify base_severity is correctly calculated

## Summary

The adaptive ROI recalculation system provides intelligent, dynamic search prioritization that:

✅ Maximizes coverage of critical gaps  
✅ Minimizes wasted search effort  
✅ Adapts to findings in real-time  
✅ Provides transparency through ROI history  
✅ Offers flexible configuration for different use cases  

For most use cases, the recommended configuration is:

```json
{
  "roi_optimizer": {
    "adaptive_recalculation": true,
    "batch_size": 5,
    "min_roi_threshold": 0.1,
    "convergence_threshold": 0.8
  }
}
```

This provides a good balance between coverage, efficiency, and adaptability.
