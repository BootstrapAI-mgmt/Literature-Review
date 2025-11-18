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

### Research Field Presets (Recommended)

The easiest way to configure evidence decay is to use a research field preset. This automatically sets an appropriate half-life based on typical publication cycles for your field:

```json
{
  "evidence_decay": {
    "enabled": true,
    "research_field": "ai_ml",
    "half_life_years": null
  }
}
```

**Available Presets:**

| Field Key | Field Name | Half-Life | Characteristics |
|-----------|------------|-----------|-----------------|
| `ai_ml` | AI & Machine Learning | 3 years | Rapidly evolving. Papers older than 3 years may be outdated. |
| `software_engineering` | Software Engineering | 5 years | Moderate pace. Practices evolve but core principles remain valid. |
| `computer_science` | Computer Science (General) | 7 years | Broad field with varied sub-areas. Moderate decay rate. |
| `mathematics` | Mathematics | 10 years | Slow-changing field. Theorems and proofs remain valid indefinitely. |
| `medicine` | Medicine & Healthcare | 5 years | Clinical guidelines update regularly. Moderate decay. |
| `biology` | Biology & Life Sciences | 6 years | Research builds incrementally. Moderate-slow decay. |
| `physics` | Physics | 8 years | Foundational science. Discoveries endure. |
| `chemistry` | Chemistry | 7 years | Established field with ongoing discoveries. |
| `custom` | Custom | 5 years | Set your own half-life value (see below). |

**Example Configurations:**

```json
// AI/ML Research (3-year half-life)
{
  "evidence_decay": {
    "enabled": true,
    "research_field": "ai_ml",
    "half_life_years": null  // Use preset
  }
}

// Mathematics Research (10-year half-life)
{
  "evidence_decay": {
    "enabled": true,
    "research_field": "mathematics",
    "half_life_years": null
  }
}

// Custom Override (use your own value)
{
  "evidence_decay": {
    "enabled": true,
    "research_field": "ai_ml",  // Will be ignored
    "half_life_years": 4.5  // Custom: 4.5 years
  }
}
```

**How Presets Work:**
- When `half_life_years` is `null`, the system uses the preset value for the specified `research_field`
- When `half_life_years` is a number, it overrides the preset (custom mode)
- If `research_field` is omitted, defaults to `"custom"` preset (5 years)

### Manual Configuration (Legacy)

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

**Parameters:**
- `enabled`: Enable/disable decay tracking (default: true)
- `research_field`: Preset key for research field (e.g., "ai_ml", "mathematics") (default: "custom")
- `half_life_years`: Years for evidence value to decay to 50%. If `null`, uses preset value. If a number, overrides preset. (default: null)
- `stale_threshold`: Threshold for marking evidence as stale (default: 0.5)
- `weight_in_gap_analysis`: Apply decay weighting to gap analysis scores (default: true)
- `decay_weight`: Blend factor for decay weighting, 0.0-1.0 (default: 0.7)
- `apply_to_pillars`: Which pillars to apply decay to, or ["all"] (default: ["all"])
- `min_freshness_threshold`: Alert threshold for stale evidence (default: 0.3)

### Auto-Detection of Research Field

You can also use the Python API to auto-detect the research field from your papers:

```python
from literature_review.utils.decay_presets import suggest_field_from_papers

# Load your papers
papers = [
    {'title': 'Deep Learning for Image Recognition', 'abstract': 'Neural networks...'},
    {'title': 'Attention Mechanisms in NLP', 'abstract': 'Machine learning...'}
]

# Auto-suggest field
suggested_field = suggest_field_from_papers(papers)
print(f"Suggested field: {suggested_field}")  # Output: "ai_ml"

# Get preset for that field
from literature_review.utils.decay_presets import get_preset
preset = get_preset(suggested_field)
print(f"Half-life: {preset['half_life_years']} years")  # Output: "3.0 years"
```

The auto-detection function analyzes paper titles and abstracts to identify keywords associated with different research fields, then suggests the field with the highest keyword match count.

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

# Using a preset
config = {
    'evidence_decay': {
        'research_field': 'ai_ml',
        'half_life_years': None  # Use preset
    }
}
tracker = EvidenceDecayTracker(config=config)
print(f"Using {tracker.field_name} preset with {tracker.half_life} year half-life")

# Calculate decay weight for a specific year
weight = tracker.calculate_decay_weight(2020)  # Returns 0.5

# Using custom half-life (legacy mode)
tracker_custom = EvidenceDecayTracker(half_life_years=5.0)
weight_custom = tracker_custom.calculate_decay_weight(2020)

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

### Working with Presets

```python
from literature_review.utils.decay_presets import (
    get_preset, 
    suggest_field_from_papers,
    list_all_presets,
    FIELD_PRESETS
)

# Get a specific preset
ai_preset = get_preset('ai_ml')
print(f"{ai_preset['name']}: {ai_preset['half_life_years']} years")
print(f"Description: {ai_preset['description']}")

# List all available presets
all_presets = list_all_presets()
for field_key, preset in all_presets.items():
    print(f"{preset['name']}: {preset['half_life_years']} years")

# Auto-detect field from papers
papers = load_papers()  # Your papers list
suggested_field = suggest_field_from_papers(papers)
preset = get_preset(suggested_field)
print(f"Suggested: {preset['name']} ({preset['half_life_years']} years)")
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

## Gap Analysis Integration

### Overview

When enabled, evidence decay weighting is automatically applied to gap analysis completeness scores. This penalizes requirements supported by old evidence and boosts those with recent evidence.

### How It Works

**Without Decay:**
```
Requirement: "System must support X"
Old Paper (2015): 90% alignment → 90% completeness
New Paper (2024): 90% alignment → 90% completeness
```

**With Decay (5-year half-life, 0.7 weight):**
```
Requirement: "System must support X"
Old Paper (2015): 90% alignment × 25% freshness → ~45% final completeness
New Paper (2024): 90% alignment × 87% freshness → ~87% final completeness
```

### Blended Scoring Formula

The decay weight parameter (0.0-1.0) controls how much to trust the decay adjustment:

```
final_score = (1 - decay_weight) × raw_score + decay_weight × (raw_score × freshness)
```

- `decay_weight = 0.0`: No decay applied (same as disabled)
- `decay_weight = 0.7`: 70% decay, 30% raw score (default)
- `decay_weight = 1.0`: Full decay weighting

### When to Enable

**Enable decay weighting if:**
- Research field changes rapidly (AI/ML, medicine, semiconductors)
- Recent evidence is more trustworthy than old evidence
- You want to prioritize finding fresh papers
- Standards or best practices have evolved

**Disable decay weighting if:**
- Research field changes slowly (mathematics, physics, theoretical CS)
- Historical evidence is equally valid (foundational results)
- Paper age doesn't correlate with relevance
- You're doing historical analysis

### Configuration Examples

**Fast-Moving Field (AI/ML):**
```json
{
  "evidence_decay": {
    "enabled": true,
    "half_life_years": 3.0,
    "weight_in_gap_analysis": true,
    "decay_weight": 0.8,
    "apply_to_pillars": ["all"]
  }
}
```

**Pillar-Specific Decay:**
```json
{
  "evidence_decay": {
    "enabled": true,
    "half_life_years": 5.0,
    "weight_in_gap_analysis": true,
    "decay_weight": 0.7,
    "apply_to_pillars": ["Security", "Performance"],
    "min_freshness_threshold": 0.3
  }
}
```

### Interpreting Results

The gap analysis report includes evidence metadata for each requirement:

```json
{
  "Sub-1.1": {
    "completeness_percent": 45.2,
    "evidence_metadata": {
      "raw_score": 90.0,
      "freshness_score": 0.25,
      "final_score": 45.2,
      "best_paper": "old_paper.pdf",
      "best_paper_year": 2015,
      "decay_applied": true,
      "decay_weight": 0.7
    }
  }
}
```

**Freshness Score Interpretation:**
- 🟢 **>70%**: Recent evidence (last 3 years)
- 🟡 **40-70%**: Moderate age (3-7 years)
- 🔴 **<40%**: Stale evidence (>7 years)

### A/B Comparison Reports

Generate side-by-side comparison showing decay impact:

```python
from literature_review.analysis.gap_analyzer import GapAnalyzer

analyzer = GapAnalyzer(config=pipeline_config)
report = analyzer.generate_decay_impact_report(
    pillar_name='Security',
    requirements=requirements,
    analysis_results=analysis_results,
    version_history=version_history
)

# Report includes:
# - per-requirement comparison (with vs without decay)
# - delta and delta_pct for each requirement
# - impact classification (decreased/increased/minimal)
# - summary statistics
```

**Sample A/B Report:**
```
Decay Impact Report for Pillar: Security
=========================================
Total Requirements: 15
Average Delta: -8.5%
Significant Changes: 5

Requirements:
1. "Authentication required" 
   - Without Decay: 85%
   - With Decay: 45% (-40%)
   - Freshness: 30% (evidence from 2016)
   - Impact: DECREASED

2. "Encryption standard"
   - Without Decay: 92%
   - With Decay: 88% (-4%)
   - Freshness: 82% (evidence from 2023)
   - Impact: MINIMAL
```

### Python API

```python
from literature_review.analysis.gap_analyzer import GapAnalyzer

# Initialize with config
config = {
    'evidence_decay': {
        'enabled': True,
        'half_life_years': 5.0,
        'weight_in_gap_analysis': True,
        'decay_weight': 0.7,
        'apply_to_pillars': ['all']
    }
}

analyzer = GapAnalyzer(config=config)

# Apply decay to a completeness score
papers = [
    {
        'filename': 'paper.pdf',
        'contribution_summary': 'Main contribution',
        'estimated_contribution_percent': 80,
        'year': 2020
    }
]

final_score, metadata = analyzer.apply_decay_weighting(
    completeness_score=80.0,
    papers=papers,
    pillar_name='Security',
    version_history=version_history
)

print(f"Raw score: {metadata['raw_score']}")
print(f"Freshness: {metadata['freshness_score']}")
print(f"Final score: {metadata['final_score']}")
```

### Testing

Run integration tests:
```bash
python -m pytest tests/unit/test_decay_integration.py -v
```

All 14 tests should pass with 100% coverage.

### Backward Compatibility

Decay weighting is **disabled by default** to preserve backward compatibility. Existing gap analysis scores remain unchanged unless you explicitly enable `weight_in_gap_analysis: true` in the config.

