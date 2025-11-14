# Evidence Triangulation - Usage Guide

## Overview

The Evidence Triangulation module (Task Card #20) groups similar claims across papers using semantic embeddings and analyzes cross-paper agreement to strengthen evidence quality assessment.

## Features

- **Semantic Clustering**: Groups similar claims using sentence-transformers (all-MiniLM-L6-v2)
- **Agreement Analysis**: Classifies consensus strength as strong/moderate/weak based on score variance
- **Contradiction Detection**: Identifies when similar claims have opposing verdicts (approved vs rejected)
- **Triangulation Reports**: Generates markdown reports summarizing findings

## Installation

The module requires additional dependencies:

```bash
pip install sentence-transformers scikit-learn
```

## Usage

### Basic Usage

```python
from literature_review.analysis.evidence_triangulation import (
    triangulate_evidence,
    generate_triangulation_report
)

# Prepare claims (from version history or database)
claims = [
    {
        "claim_id": "c1",
        "extracted_claim_text": "SNNs achieve 95% accuracy on DVS datasets",
        "filename": "paper1.pdf",
        "status": "approved",
        "evidence_quality": {"composite_score": 4.2}
    },
    {
        "claim_id": "c2",
        "extracted_claim_text": "Spiking networks reach 94% accuracy on event-based data",
        "filename": "paper2.pdf",
        "status": "approved",
        "evidence_quality": {"composite_score": 4.0}
    },
    # ... more claims
]

# Run triangulation analysis
results = triangulate_evidence(claims, similarity_threshold=0.85)

# Generate report
generate_triangulation_report(results, "triangulation_report.md")
```

### Integration with Orchestrator

To integrate triangulation into the main orchestrator workflow:

```python
from literature_review.analysis.evidence_triangulation import triangulate_evidence

def run_triangulation_analysis(db: pd.DataFrame, pillar_definitions: Dict) -> Dict:
    """Run triangulation analysis for each sub-requirement."""
    triangulation_by_sub_req = {}
    
    for pillar_name, pillar_data in pillar_definitions.items():
        for req_key, req_data in pillar_data.get("requirements", {}).items():
            for sub_req_list in req_data:
                for sub_req in sub_req_list.split(','):
                    sub_req = sub_req.strip()
                    
                    # Get all claims for this sub-requirement
                    matching_rows = db[db["Requirement(s)"].str.contains(sub_req, na=False)]
                    
                    # Extract claims from JSON
                    claims = []
                    for _, row in matching_rows.iterrows():
                        req_list = json.loads(row.get("Requirement(s)", "[]"))
                        for claim in req_list:
                            if sub_req in claim.get("sub_requirement", ""):
                                claims.append({
                                    **claim,
                                    "filename": row.get("Filename", "unknown")
                                })
                    
                    if len(claims) >= 2:  # Need at least 2 claims to triangulate
                        triangulation = triangulate_evidence(claims)
                        if triangulation:
                            triangulation_by_sub_req[sub_req] = triangulation
    
    return triangulation_by_sub_req
```

## Parameters

### `triangulate_evidence()`

- **claims** (List[Dict]): List of claim dictionaries with required fields:
  - `extracted_claim_text` or `claim_summary` or `evidence_chunk`: The claim text
  - `evidence_quality.composite_score`: Quality score (1-5)
  - `status`: Claim status (e.g., "approved", "rejected")
  - `filename`: Source paper
  - `claim_id`: Unique identifier

- **similarity_threshold** (float, default=0.85): Cosine similarity threshold (0-1)
  - Higher values = stricter clustering (more similar claims required)
  - Lower values = looser clustering (more diverse claims grouped)

### Agreement Level Classification

Based on score variance within a cluster:
- **Strong agreement**: variance < 0.3 (highly consistent scores)
- **Moderate agreement**: variance 0.3-0.7 (some variation)
- **Weak agreement**: variance > 0.7 (significant disagreement)

## Output Format

### Triangulation Results Dictionary

```python
{
    "cluster_0": {
        "representative_claim": "SNNs achieve 90%+ accuracy on DVS datasets",
        "supporting_papers": ["paper1.pdf", "paper2.pdf", "paper3.pdf"],
        "claim_ids": ["c1", "c2", "c3"],
        "num_supporting_papers": 3,
        "agreement_level": "strong",
        "average_score": 4.2,
        "score_variance": 0.15,
        "has_contradiction": False,
        "contradiction_details": None,
        "all_claims": [...]  # Full claim objects
    },
    # ... more clusters
}
```

### Markdown Report

The generated report includes:
- Total number of clusters found
- For each cluster:
  - Representative claim text
  - Number and list of supporting papers
  - Agreement level and quality metrics
  - Contradiction warnings (if applicable)

## Testing

Run unit tests:
```bash
pytest tests/unit/test_evidence_triangulation.py -v
```

Run integration tests:
```bash
python tests/integration/test_triangulation_integration.py
```

## Performance

- **Processing time**: <5% overhead (per acceptance criteria)
- **Minimum cluster size**: 2 claims (configurable via DBSCAN `min_samples`)
- **Embedding model**: Cached globally for efficiency
- **Clustering algorithm**: DBSCAN with cosine distance

## Troubleshooting

### Model Download Issues

If you encounter network issues downloading the sentence-transformers model:

1. Pre-download the model:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

2. Or use a local model cache by setting the `SENTENCE_TRANSFORMERS_HOME` environment variable.

### Memory Constraints

For very large claim sets (>1000 claims):
- Process claims in batches by sub-requirement
- Increase similarity threshold to reduce cluster sizes
- Use a lighter embedding model if needed

## Example Output

Sample triangulation report excerpt:

```markdown
# Evidence Triangulation Report

**Total Clusters Found:** 5

## Cluster 0

**Representative Claim:** SNNs achieve >90% accuracy on DVS gesture recognition datasets

**Supporting Papers:** 3
- 3664647.3680573.pdf, 3746709.3746943.pdf, 3219819.3220051.pdf

**Agreement Level:** strong
**Average Quality Score:** 4.1
**Score Variance:** 0.12

---

## Cluster 1

**Representative Claim:** Event-driven architectures reduce power consumption by >50%

**Supporting Papers:** 2
- paper_a.pdf, paper_b.pdf

**Agreement Level:** moderate
**Average Quality Score:** 3.8
**Score Variance:** 0.45

⚠️ **CONTRADICTION DETECTED**

- Approved: 1 papers
- Rejected: 1 papers
- Score Gap: 1.20

---
```

## Implementation Status

✅ **Complete**
- Semantic clustering with sentence-transformers
- Agreement analysis (strong/moderate/weak)
- Contradiction detection
- Markdown report generation
- Unit tests (13 tests, 100% passing)
- Integration test framework

## References

- Task Card #20: Evidence Triangulation
- Dependencies: Task Cards #16 (Scoring), #17 (Provenance)
- Embedding model: sentence-transformers/all-MiniLM-L6-v2
- Clustering: scikit-learn DBSCAN
