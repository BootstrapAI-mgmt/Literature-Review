# Deep Review Trigger System

## Overview

The Deep Review Trigger System is an intelligent automation component that decides when to invoke the Deep Reviewer based on three key metrics. This helps optimize resource usage by focusing Deep Review on high-value papers while avoiding wasteful analysis of weak or irrelevant papers.

## Architecture

### 3-Metric Evaluation System

The system evaluates each paper against three independent metrics:

1. **Gap Severity** (threshold: 70%)
   - Measures how much this paper fills critical research gaps
   - Analyzes whether the paper addresses requirements with High or Critical gap severity
   - Calculated as: `critical_contributions / total_contributions`

2. **Paper Quality** (threshold: 60%)
   - Based on the Judge's overall_alignment score
   - Indicates whether the paper is worth deep analysis
   - Higher scores indicate better alignment with research goals

3. **ROI Potential** (threshold: 5.0x)
   - Estimates return on investment of performing Deep Review
   - Formula: `(gap_score × quality_score × 2.0) / 0.5`
   - Assumes Deep Review costs $0.50 and saves 2 hours if valuable

### Trigger Decision

A paper triggers Deep Review if **ANY** of the three metrics exceeds its threshold:
- Gap Severity > 70%, **OR**
- Paper Quality > 60%, **OR**
- ROI Potential > 5.0x

This OR logic ensures that:
- High-quality papers get deep analysis regardless of gap coverage
- Papers addressing critical gaps get analyzed even if quality is moderate
- High-ROI papers are prioritized for efficiency

## Usage

### As a Standalone Tool

```python
from literature_review.triggers.deep_review_triggers import generate_trigger_report

# Generate trigger report
report = generate_trigger_report(
    gap_file='gap_analysis_output/gap_analysis_report.json',
    review_log='review_version_history.json',
    output_file='deep_reviewer_cache/trigger_decisions.json'
)

print(f"Triggered {report['triggered_papers']} out of {report['total_papers']} papers")
```

### As Part of Pipeline

The trigger system is automatically run as Stage 8 in the pipeline orchestrator, after the Evidence Sufficiency Matrix stage. It runs silently and logs results.

```bash
python pipeline_orchestrator.py
```

### Command Line

```bash
python -c "from literature_review.triggers.deep_review_triggers import generate_trigger_report; generate_trigger_report('gap_analysis_output/gap_analysis_report.json', 'review_version_history.json')"
```

## Input Requirements

### Gap Analysis File

Expected structure:
```json
{
  "Pillar 1: Biological Stimulus-Response": {
    "completeness": 7.5,
    "analysis": {
      "REQ-B1.1: Sensory Transduction": {
        "Sub-1.1.1: Requirement name": {
          "completeness_percent": 0,
          "gap_analysis": "...",
          "contributing_papers": [...]
        }
      }
    }
  }
}
```

The system automatically transforms this to the internal format with gap severity classification:
- 0-29% completeness → Critical gap
- 30-49% completeness → High gap
- 50-69% completeness → Medium gap
- 70-100% completeness → Low gap

### Review Log File

Expected structure:
```json
{
  "paper1.pdf": {
    "metadata": {
      "title": "Paper Title"
    },
    "judge_analysis": {
      "overall_alignment": 0.85,
      "pillar_contributions": [
        {
          "pillar_name": "Pillar 1: Biological Stimulus-Response",
          "sub_requirements_addressed": [
            {
              "requirement_id": "Sub-1.1.1: Requirement name",
              "contribution_score": 0.8
            }
          ]
        }
      ]
    }
  }
}
```

## Output Format

The system generates a JSON report with the following structure:

```json
{
  "total_papers": 5,
  "triggered_papers": 3,
  "trigger_rate": 0.6,
  "candidates": [
    {
      "paper": "paper1.pdf",
      "title": "Paper Title",
      "gap_score": 1.0,
      "quality_score": 0.85,
      "roi_score": 3.4,
      "trigger_reason": "Critical gap coverage (100%), High quality (85%)"
    }
  ]
}
```

### Output Fields

- `total_papers`: Total number of papers evaluated
- `triggered_papers`: Number of papers that triggered Deep Review
- `trigger_rate`: Percentage of papers triggered (0.0 to 1.0)
- `candidates`: Array of triggered papers, sorted by priority
  - `paper`: Filename of the paper
  - `title`: Paper title from metadata
  - `gap_score`: Gap impact score (0.0 to 1.0)
  - `quality_score`: Quality alignment score (0.0 to 1.0)
  - `roi_score`: ROI potential score (0.0+)
  - `trigger_reason`: Human-readable explanation

## Performance Targets

- **Trigger Rate**: 20-40% of papers (not all, not none)
- **Cost Reduction**: 60-80% reduction in unnecessary Deep Review calls
- **Precision**: Prioritize high-value papers for deep analysis
- **Transparency**: All trigger decisions logged with reasons

## Customization

Thresholds can be adjusted by modifying the `THRESHOLDS` constant in `DeepReviewTriggerEngine`:

```python
THRESHOLDS = {
    'gap_severity': 0.7,      # Invoke if gap > 70%
    'paper_quality': 0.6,     # Invoke if quality > 60%
    'roi_potential': 5.0      # Invoke if ROI > 5 (hours saved / cost)
}
```

## Testing

Run the unit tests:

```bash
pytest tests/unit/test_deep_review_triggers.py -v
```

All tests should pass with >95% coverage.

## Dependencies

- `json`: For data loading and saving
- `typing`: For type hints
- `logging`: For structured logging
- `os`: For file operations

## Error Handling

The system gracefully handles:
- Missing input files (logs warning, skips analysis)
- Malformed JSON data (logs error, continues)
- Missing fields in review data (uses defaults)
- Empty review logs (returns empty candidate list)

## Integration Points

### Pipeline Orchestrator

Added as Stage 8 in `pipeline_orchestrator.py`:

```python
# Stage 8: Deep Review Trigger Analysis (NEW)
self._run_deep_review_trigger_analysis()
```

The method `_run_deep_review_trigger_analysis()` handles:
- Checking if required files exist
- Importing the trigger module
- Running the analysis
- Logging results
- Graceful failure if files are missing

## Future Enhancements

Potential improvements for future waves:

1. **Machine Learning Models**: Train ML models to predict ROI more accurately
2. **Historical Performance**: Track actual Deep Review value vs. predictions
3. **Dynamic Thresholds**: Adjust thresholds based on budget and time constraints
4. **Multi-Criteria Ranking**: Use weighted scoring across all three metrics
5. **Batch Optimization**: Consider paper combinations for maximum coverage
6. **Cost-Aware Scheduling**: Prioritize based on available budget

## Task Card Reference

- **Task ID**: ENHANCE-W3-1
- **Wave**: 3 (Automation & Optimization)
- **Priority**: LOW
- **Estimated Effort**: 12 hours
- **Dependencies**: ENHANCE-W1-1 (Manual Deep Review), ENHANCE-W2-1 (Sufficiency Matrix)
