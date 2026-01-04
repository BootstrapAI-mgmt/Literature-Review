# Golden Dataset Requirements

## Purpose

The golden dataset provides human-verified ground truth data for:
1. **Accuracy Testing** - Measuring precision, recall, and F1 scores
2. **Calibration Analysis** - Validating confidence score reliability
3. **Regression Detection** - Ensuring model updates don't degrade quality
4. **Quality Benchmarking** - Establishing quality baselines

## Dataset Components

### 1. Annotated Claims (50+ samples)
Human-labeled claims from research papers with:
- Correct pillar assignment
- Correct sub-requirement mapping
- Evidence quality scores (1-5 scale)
- Expected verdict (approve/reject)
- Confidence level for the expected verdict

### 2. Evidence Quality Ratings (100+ samples)
Human-rated evidence with:
- Strength score (1-5)
- Rigor score (1-5)
- Relevance score (1-5)
- Directness rating (1-3)
- Reproducibility score (1-5)
- Overall composite assessment

### 3. Pillar Mapping Ground Truth (100+ samples)
Claims with verified pillar/requirement mappings:
- Paper context
- Claim text
- Correct pillar
- Correct requirement
- Correct sub-requirement
- Rationale for mapping

### 4. Known Gaps (20+ samples)
Deliberately constructed database states with known gaps:
- Input database state
- Pillar definitions
- Expected gaps identified
- Severity classifications

### 5. Recommendation Quality (10+ samples)
Gaps with expert-recommended solutions:
- Gap description
- Expected recommendation themes
- Quality rating criteria

### 6. Search Suggestion Ground Truth (15+ samples) *(Added for Wave 2.5)*
Validated search suggestions for RA-01/RA-02 testing:
- Gap with known solution papers
- Expected search queries that would find solutions
- Human-validated priority ranking
- Expected source databases (arxiv, ieee, etc.)
- Relevance match criteria

### 7. Output Sample Collection (5+ complete runs) *(Added for Wave 2.5)*
Complete pipeline output snapshots for OQ-* validation:
- gap_analysis_report.json with verified content
- executive_summary.md with all required sections
- suggested_searches.json/md pairs
- proof_chain.json with verified links
- Evidence enhancement files (triangulation, decay, sufficiency)

## Annotation Standards

### Inter-Rater Reliability
- Minimum 2 independent annotators per sample
- Cohen's Kappa > 0.7 required for inclusion
- Disagreements resolved by third annotator

### Annotator Qualifications
- PhD or equivalent research experience
- Domain expertise in neuromorphic computing OR
- Extensive literature review experience

### Quality Assurance
- 10% of samples re-annotated for consistency
- Systematic bias checks across annotators
- Quarterly dataset review and refresh

## Versioning

- Semantic versioning (MAJOR.MINOR.PATCH)
- MAJOR: Schema changes or >20% content change
- MINOR: New samples added, annotations updated
- PATCH: Error corrections

## Storage & Access

- Location: `tests/golden_dataset/data/`
- Format: JSON with schema validation
- Version controlled with Git LFS for large files

## Related Documentation

- [Annotation Guidelines](./GOLDEN_DATASET_ANNOTATION_GUIDELINES.md) - Detailed annotation process
- [Golden Dataset README](../tests/golden_dataset/README.md) - Usage patterns and examples
