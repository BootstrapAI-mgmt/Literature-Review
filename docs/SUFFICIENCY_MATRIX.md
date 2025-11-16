# Evidence Sufficiency Matrix

## Overview

The Evidence Sufficiency Matrix is an analysis tool that evaluates the quality vs. quantity tradeoffs in evidence collection across research requirements. It helps identify critical gaps and provides actionable recommendations for improving research coverage.

## Features

- **Quadrant Analysis**: Categorizes requirements into 4 quadrants based on evidence quality and quantity
- **Visual Dashboard**: Interactive HTML scatter plot showing the quality-quantity distribution
- **Actionable Recommendations**: Specific guidance for each quadrant
- **Automated Integration**: Runs as part of the pipeline orchestrator

## Quadrants

### Q1: Strong Foundation (High Quantity + High Quality)
- **Criteria**: 8+ papers with 70%+ average alignment
- **Status**: ✅ Publication-ready
- **Action**: Consider consolidating into review papers

### Q2: Promising Seeds (Low Quantity + High Quality)
- **Criteria**: <8 papers with 70%+ average alignment
- **Status**: ⚠️ Needs expansion
- **Action**: Run targeted searches to find 3-5 more high-quality papers

### Q3: Critical Gap (Low Quantity + Low Quality)
- **Criteria**: <8 papers with <70% average alignment
- **Status**: 🚨 Urgent attention needed
- **Action**: Expand searches, relax criteria, or refine requirements

### Q4: Hollow Coverage (High Quantity + Low Quality)
- **Criteria**: 8+ papers with <70% average alignment
- **Status**: ⚠️ Needs refinement
- **Action**: Review requirement definitions, apply stricter inclusion criteria

## Usage

### Standalone Execution

```bash
# Run the sufficiency matrix analyzer
python -m literature_review.analysis.sufficiency_matrix

# Or with custom paths
python -c "
from literature_review.analysis.sufficiency_matrix import generate_sufficiency_report
generate_sufficiency_report(
    gap_analysis_file='gap_analysis_output/gap_analysis_report.json',
    output_file='gap_analysis_output/sufficiency_matrix.json'
)
"
```

### Pipeline Integration

The sufficiency matrix runs automatically as Stage 7 of the pipeline:

```bash
python pipeline_orchestrator.py
```

## Outputs

### JSON Report (`sufficiency_matrix.json`)

```json
{
  "summary": {
    "total_requirements_analyzed": 32,
    "quadrant_distribution": {
      "Q3_Critical_Gap": 27,
      "Q2_Promising_Seeds": 5
    }
  },
  "requirement_analysis": { ... },
  "quadrant_groups": { ... },
  "recommendations": { ... },
  "matrix_visualization": { ... }
}
```

### HTML Visualization (`sufficiency_matrix.html`)

Interactive Plotly scatter plot with:
- Color-coded quadrants
- Hover tooltips showing paper details
- Quadrant divider lines
- Legend explaining each quadrant

## Configuration

### Thresholds

Modify thresholds in `sufficiency_matrix.py`:

```python
QUANTITY_THRESHOLDS = {
    'low': 3,      # <3 papers
    'medium': 8,   # 3-8 papers
    'high': 8      # >8 papers
}

QUALITY_THRESHOLDS = {
    'low': 0.4,    # <40% avg alignment
    'medium': 0.7,  # 40-70% avg alignment
    'high': 0.7    # >70% avg alignment
}
```

### Input Data

The analyzer expects:
- **gap_analysis_report.json**: Output from the gap analysis orchestrator
- Structure: Pillars → Requirements → Sub-requirements → Contributing papers

## Integration with Other Tools

### Proof Scorecard (ENHANCE-W1-2)
The sufficiency matrix complements the proof scorecard by providing:
- Granular quality/quantity analysis per requirement
- Identification of hollow coverage vs. strong foundation
- Specific recommendations for closing gaps

### Search Optimizer (ENHANCE-W3-2)
The sufficiency matrix informs search optimization by:
- Identifying Q2 (Promising Seeds) for targeted expansion
- Flagging Q4 (Hollow Coverage) for search refinement
- Highlighting Q3 (Critical Gap) for new search strategies

## Interpreting Results

### Example Output

```
Analyzed 32 requirements

Quadrant Distribution:
  Q3_Critical_Gap: 27
  Q2_Promising_Seeds: 5

Recommendations:

Q2_Promising_Seeds:
  ⚠️ 5 requirements have high-quality but limited evidence
  🎯 Priority action: Run targeted searches to find more papers in these areas
  💡 These could become Q1 with 3-5 more high-quality papers
```

### Action Priorities

1. **Immediate**: Address Q3 Critical Gaps with urgent searches
2. **High Priority**: Expand Q2 Promising Seeds to Q1 Strong Foundation
3. **Medium Priority**: Refine Q4 Hollow Coverage requirements
4. **Maintenance**: Monitor Q1 Strong Foundation for updates

## Testing

Run unit tests:

```bash
pytest tests/unit/test_sufficiency_matrix.py -v
```

## Troubleshooting

### No requirements analyzed
- Check that gap_analysis_report.json exists and has contributing_papers
- Ensure papers have estimated_contribution_percent field

### Unexpected quadrant assignments
- Review thresholds in configuration
- Check quality calculation (based on estimated_contribution_percent)

### Visualization not loading
- Verify sufficiency_matrix.html was generated
- Check browser console for JavaScript errors
- Ensure Plotly CDN is accessible

## Related Documentation

- Task Card: ENHANCE-W2-1
- Proof Scorecard: `literature_review/analysis/proof_scorecard.py`
- Gap Analysis: `literature_review/orchestrator.py`

## Version History

- **v1.0** (2025-11-16): Initial implementation
  - Quadrant categorization
  - HTML visualization
  - Pipeline integration
  - Unit tests
