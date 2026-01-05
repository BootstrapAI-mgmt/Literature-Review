# Example Domain

This is a template domain directory showing the expected structure for
domain-agnostic testing.

## Files

- `research_config.json` - Required domain configuration
- `pillar_definitions.json` - Required pillar definitions
- `golden_dataset.json` - Optional validation dataset
- `test_baselines.json` - Optional domain-specific thresholds
- `golden_dataset.schema.json` - JSON schema for golden dataset validation

## Usage

```bash
# Validate this domain fixture
python scripts/validate_domain_fixture.py domains/example-domain/

# Run tests against this domain
pytest tests/validation/ --domain=example-domain
```

## Creating a New Domain

1. Copy this directory to `domains/your-domain-id/`
2. Edit `research_config.json` with your domain settings
3. Edit `pillar_definitions.json` with your research pillars
4. Optionally populate `golden_dataset.json` with annotated claims
5. Optionally adjust `test_baselines.json` thresholds

## Golden Dataset

The golden dataset should contain human-annotated claims with expected verdicts.
This enables accuracy validation of the pipeline against known correct answers.

See `golden_dataset.schema.json` for the required structure.

## Test Baselines

Test baselines define domain-specific performance thresholds:

| Metric | Default | Description |
|--------|---------|-------------|
| claim_precision | 0.85 | Precision of claim extraction |
| claim_recall | 0.80 | Recall of claim extraction |
| judge_accuracy | 0.90 | Accuracy of verdict assignment |
| dra_recovery_rate | 0.40 | Deep Review Agent recovery rate |
| gap_false_negative_rate | 0.05 | False negative rate for gap detection |
| max_runtime_per_paper | 120.0 | Maximum processing time per paper (seconds) |
| max_cost_per_paper | 0.50 | Maximum API cost per paper (dollars) |
| recommendation_relevance | 0.80 | Relevance score for recommendations |
| gap_coverage | 1.0 | Coverage of known gaps |
