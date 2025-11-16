# API Cost Tracker & Budget Management

## Overview

The API Cost Tracker provides real-time monitoring of API usage costs and budget management for the Literature Review system. It tracks costs per API call, module, and paper, generates comprehensive reports, and provides optimization recommendations.

## Features

- ✅ **Real-time Cost Tracking**: Know the exact cost of each pipeline run
- ✅ **Per-Module Analytics**: Track costs for Journal Reviewer, Judge, Deep Reviewer, etc.
- ✅ **Budget Warnings**: Get alerts before expensive operations exceed budget
- ✅ **Automated Reports**: Cost reports generated automatically after each pipeline run
- ✅ **Cache Efficiency**: Identify optimization opportunities through cache hit analysis
- ✅ **Cost Recommendations**: Actionable suggestions for reducing API costs

## Quick Start

### 1. Set a Budget

Set your monthly budget when running the pipeline:

```bash
python pipeline_orchestrator.py --budget 50.0
```

Or in your `pipeline_config.json`:

```json
{
  "budget_usd": 50.0
}
```

### 2. Run the Pipeline

The cost tracker automatically logs all API calls during pipeline execution:

```bash
python pipeline_orchestrator.py
```

You'll see budget status at the start and a cost report at the end:

```
💰 Budget status: $0.0000 / $50.00 used
...
📊 COST REPORT
Session Cost: $0.0245 (15 calls)
Total Cost: $1.2340 (250 calls)
Budget Remaining: $48.77
```

### 3. Generate a Cost Report

View detailed cost analytics anytime:

```bash
python scripts/generate_cost_report.py
```

## Cost Report Output

```
============================================================
API COST REPORT
============================================================

📊 Total Usage:
   API Calls: 250
   Total Cost: $1.2340
   Total Tokens: 2,450,000
   Cache Savings: $0.0520

💰 Budget Status:
   Budget: $50.00
   Spent: $1.23
   Remaining: $48.77
   Used: 2.5%

📦 By Module:
   journal_reviewer    : $0.8120 (180 calls)
   judge               : $0.3100 (50 calls)
   deep_reviewer       : $0.1120 (20 calls)

🗃️  Cache Efficiency:
   Hit Rate: 12.5%
   Savings: $0.0520

📄 Per-Paper Analysis:
   Papers Analyzed: 25
   Avg Cost/Paper: $0.0494
   Range: $0.0120 - $0.1250

💡 Recommendations:
   ✅ Cost efficiency looks good!
   💡 Consider using gemini-1.5-flash for routine tasks.

============================================================
Full report saved to: cost_reports/api_usage_report.json
============================================================
```

## Pricing Information

The cost tracker uses current Gemini API pricing (as of Nov 2025):

### Free Tier Models
- `gemini-2.5-flash`: **$0.00** per 1M tokens (input/output)
- `gemini-2.0-flash-thinking-exp`: **$0.00** per 1M tokens

### Paid Tier Models
- `gemini-1.5-flash`:
  - Input: **$0.075** per 1M tokens
  - Output: **$0.30** per 1M tokens
  - Cached Input: **$0.01875** per 1M tokens (75% discount)

- `gemini-1.5-pro`:
  - Input: **$1.25** per 1M tokens
  - Output: **$5.00** per 1M tokens
  - Cached Input: **$0.3125** per 1M tokens (75% discount)

> **Note**: Pricing is subject to change. Update `GEMINI_PRICING` in `literature_review/utils/cost_tracker.py` if rates change.

## Integration with API Manager

The cost tracker is automatically integrated with the API manager. All API calls are tracked with the following metadata:

```python
from literature_review.utils.api_manager import APIManager

api_manager = APIManager()

# Cost tracking is automatic!
result = api_manager.cached_api_call(
    prompt="Analyze this paper",
    module='journal_reviewer',      # For cost analytics
    operation='initial_review',     # Operation description
    paper='paper_name.pdf'          # Paper filename
)
```

## Budget Protection

The pipeline automatically checks budget status before running:

```python
# Budget exceeded - pipeline aborts
⚠️ Over budget! Spent $52.34 / $50.00
RuntimeError: Budget exceeded. Pipeline aborted.

# Budget at risk - warning issued
⚠️ Budget at risk: $8.50 remaining (83.0% used)
```

## Cost Optimization Tips

### 1. Enable Prompt Caching

Gemini's prompt caching can reduce costs by up to 75% for repeated content:

```python
# Reuse prompts when possible
# The API manager automatically caches responses
```

### 2. Use Appropriate Models

- **gemini-2.5-flash**: Free tier, best for most tasks
- **gemini-1.5-flash**: Low cost, good for routine analysis
- **gemini-1.5-pro**: Higher cost, use only for complex reasoning

### 3. Monitor Cache Efficiency

Low cache hit rates indicate opportunities for optimization:

```
⚠️ Low cache hit rate (5.2%). Consider enabling prompt caching.
```

### 4. Batch Processing

Process papers in batches to maximize cache efficiency and reduce redundant API calls.

## Files and Directories

```
literature_review/
└── utils/
    └── cost_tracker.py          # Core cost tracking module

scripts/
└── generate_cost_report.py      # CLI report generator

cost_reports/                     # Cost tracking data (git-ignored)
├── api_cost_log.json            # Detailed API call log
└── api_usage_report.json        # Latest comprehensive report

tests/
├── unit/
│   └── test_cost_tracker.py    # Unit tests (12 tests)
└── integration/
    └── test_cost_tracking_integration.py  # Integration tests (3 tests)
```

## API Reference

### CostTracker Class

```python
from literature_review.utils.cost_tracker import get_cost_tracker

tracker = get_cost_tracker()  # Singleton instance
```

#### Methods

- `log_api_call(module, model, input_tokens, output_tokens, cached_tokens, operation, paper)` - Log an API call
- `get_session_summary()` - Get cost summary for current session
- `get_total_summary()` - Get cost summary for all time
- `get_budget_status(budget_usd)` - Check budget status
- `cost_per_paper_analysis()` - Analyze cost efficiency per paper
- `generate_report(output_file)` - Generate comprehensive cost report

### Example: Custom Cost Tracking

```python
from literature_review.utils.cost_tracker import get_cost_tracker

tracker = get_cost_tracker()

# Log a custom API call
tracker.log_api_call(
    module='custom_analyzer',
    model='gemini-2.5-flash',
    input_tokens=5000,
    output_tokens=1000,
    cached_tokens=2000,
    operation='analyze_methodology',
    paper='smith2024.pdf'
)

# Check budget
status = tracker.get_budget_status(budget_usd=50.0)
print(f"Budget remaining: ${status['remaining']:.2f}")

# Generate report
report = tracker.generate_report()
```

## Testing

### Run Unit Tests

```bash
python -m pytest tests/unit/test_cost_tracker.py -v
```

### Run Integration Tests

```bash
python -m pytest tests/integration/test_cost_tracking_integration.py -v
```

### Run All Tests

```bash
python -m pytest tests/unit/test_cost_tracker.py tests/integration/test_cost_tracking_integration.py -v
```

## Configuration

### Pipeline Config (pipeline_config.json)

```json
{
  "budget_usd": 50.0,
  "retry_policy": {
    "enabled": true
  }
}
```

### Cost Tracker Configuration

Modify `literature_review/utils/cost_tracker.py` to:

- Update pricing models
- Change default log file location
- Adjust budget warning thresholds
- Customize recommendations

## Troubleshooting

### Cost Log Not Updating

**Problem**: Cost log file not being written

**Solution**:
- Ensure `cost_reports/` directory is writable
- Check file permissions
- Verify disk space

### Budget Warnings Not Showing

**Problem**: No budget warnings despite high usage

**Solution**:
- Check budget is set correctly (default: $50)
- Verify cost tracker is initialized in pipeline
- Ensure API calls include metadata parameters

### Inaccurate Cost Calculations

**Problem**: Costs don't match expected values

**Solution**:
- Verify pricing in `GEMINI_PRICING` dict is up-to-date
- Check model names match exactly
- Ensure token counts are being extracted correctly

## Future Enhancements

Potential improvements for future versions:

- [ ] Email alerts for budget warnings
- [ ] Cost forecasting based on historical trends
- [ ] Multi-currency support
- [ ] Cost allocation by project/team
- [ ] Real-time dashboard integration
- [ ] Export to CSV/Excel for accounting
- [ ] Integration with cloud billing APIs

## Support

For issues or questions:

1. Check this documentation first
2. Review test files for usage examples
3. Open an issue on GitHub with:
   - Cost report output
   - Relevant log files
   - Steps to reproduce

## License

This feature is part of the Literature Review system and follows the same license.
