# Evidence Decay Tracker

Track temporal freshness of evidence and weight recent papers more heavily in gap analysis.

## Quick Start

```bash
# Generate evidence decay report
python scripts/analyze_evidence_decay.py

# Show decay weight table
python scripts/analyze_evidence_decay.py --show-weights

# Custom half-life for fast-moving fields
python scripts/analyze_evidence_decay.py --half-life 3.0
```

## What It Does

The Evidence Decay Tracker analyzes how fresh your evidence is by calculating temporal weights based on publication years. Older papers are weighted less heavily, encouraging you to refresh evidence with recent publications.

### Key Metrics

- **Decay Weight**: How much value a paper retains based on age (0-1 scale)
- **Freshness Score**: Weighted average of alignment scores considering paper age
- **Needs Update**: Flag indicating if evidence is stale (avg weight < 0.5)

## Decay Model

Uses exponential decay: `weight = 2^(-age / half_life)`

With a 5-year half-life:
- Current year: 100% value
- 5 years old: 50% value (half-life)
- 10 years old: 25% value
- 15 years old: 12.5% value

## Configuration

Edit `pipeline_config.json`:

```json
{
  "evidence_decay": {
    "enabled": true,
    "half_life_years": 5.0,
    "stale_threshold": 0.5,
    "weight_in_gap_analysis": true
  }
}
```

### Half-Life by Field

Choose based on your research domain:
- **AI/ML**: 3-4 years (fast-moving)
- **Engineering**: 5-7 years (moderate)
- **Mathematics**: 10+ years (slow-moving)
- **Medicine**: 5 years (guidelines-driven)

## CLI Options

```bash
python scripts/analyze_evidence_decay.py [OPTIONS]

Options:
  --review-log PATH         Path to review log (default: review_log.json)
  --gap-analysis PATH       Path to gap analysis (default: gap_analysis_output/gap_analysis_report.json)
  --output PATH            Output file (default: gap_analysis_output/evidence_decay.json)
  --half-life YEARS        Half-life in years (default: 5.0)
  --show-weights           Show decay weight table
  --help                   Show help message
```

## Output

Generates `gap_analysis_output/evidence_decay.json` with:

- **Summary**: Overall statistics (total requirements, needs update count, average age)
- **Requirement Analysis**: Per-requirement freshness metrics
- **Paper Details**: Individual paper ages, weights, and contributions

## Integration

The tracker automatically runs during gap analysis if enabled in config. You can also run it standalone for analysis.

## Python API

```python
from literature_review.utils.evidence_decay import EvidenceDecayTracker, generate_decay_report

# Calculate decay weight for a specific year
tracker = EvidenceDecayTracker(half_life_years=5.0)
weight = tracker.calculate_decay_weight(2020)  # Returns 0.5

# Generate full report
report = generate_decay_report(
    review_log='review_log.json',
    gap_analysis='gap_analysis_output/gap_analysis_report.json',
    output_file='gap_analysis_output/evidence_decay.json',
    half_life_years=5.0
)

# Access summary
print(f"Requirements needing update: {report['summary']['needs_update_count']}")
```

## Interpreting Results

### Freshness Score
- **0.8-1.0**: Excellent (very recent evidence)
- **0.6-0.8**: Good (fresh evidence)
- **0.4-0.6**: Fair (aging evidence)
- **< 0.4**: Poor (stale evidence, needs update)

### Needs Update Flag
Triggered when average decay weight < 0.5, meaning evidence is on average older than one half-life.

## Example Output

```
============================================================
EVIDENCE DECAY ANALYSIS
============================================================

Summary:
  Requirements Analyzed: 32
  Need Updated Searches: 0
  Avg Evidence Age: 3.0 years
  Avg Freshness Score: 0.4

⚠️ Requirements Needing Update (Top 5):
  Sub-1.1.1: Conclusive model of how raw sensory data...
    Avg Age: 7.2 years, Weight: 0.28

============================================================
Full report saved to: gap_analysis_output/evidence_decay.json
============================================================
```

## Testing

Run unit tests:
```bash
python -m pytest tests/unit/test_evidence_decay.py -v
```

All 8 tests should pass with 93%+ coverage.
