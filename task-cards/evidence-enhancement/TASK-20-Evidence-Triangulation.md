# TASK CARD #20: Evidence Triangulation

**Priority:** 🟢 MEDIUM  
**Estimated Effort:** 10-12 hours  
**Risk Level:** MEDIUM  
**Wave:** Wave 4 (Weeks 7-8)  
**Track:** 🧪 Evidence Quality  
**Dependencies:** Task Cards #16 (Scoring), #17 (Provenance)  
**Blocks:** None

## Problem Statement

Current system evaluates each claim independently without cross-paper validation. This prevents:
- Detecting when multiple papers support the same finding (strengthens evidence)
- Identifying contradictory findings across papers (requires investigation)
- Understanding field-level consensus vs. debate
- Prioritizing well-supported claims over isolated findings

Evidence triangulation clusters similar claims and analyzes cross-paper agreement, enabling confidence assessment based on replication.

## Acceptance Criteria

**Functional Requirements:**
- [ ] Group similar claims using semantic embeddings
- [ ] Detect claim clusters (3+ papers supporting same finding)
- [ ] Identify contradictions (similar claims with opposite verdicts)
- [ ] Calculate consensus strength (score variance within cluster)
- [ ] Generate triangulation report for all sub-requirements

**Cluster Classifications:**
- [ ] **Strong consensus**: 3+ papers, low score variance (<0.3)
- [ ] **Moderate consensus**: 2-3 papers, medium variance (0.3-0.7)
- [ ] **Weak consensus**: 2+ papers, high variance (>0.7)
- [ ] **Contradictory**: Similar claims with approved + rejected verdicts

**Technical Requirements:**
- [ ] Semantic similarity threshold: 0.85 (cosine similarity)
- [ ] DBSCAN clustering for robust grouping
- [ ] Sentence-BERT embeddings (all-MiniLM-L6-v2)
- [ ] Triangulation adds <5% to processing time

## Implementation Guide

**Files to Modify:**

### 1. New Module: literature_review/analysis/evidence_triangulation.py (~200 lines)

```python
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
import numpy as np
from typing import List, Dict

# Load embedding model (cache globally)
_embedding_model = None

def get_embedding_model():
    """Get cached sentence embedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model

def triangulate_evidence(claims: List[Dict], similarity_threshold: float = 0.85) -> Dict:
    """
    Group similar claims and analyze cross-paper agreement.
    
    Args:
        claims: List of claim dicts with evidence_quality and metadata
        similarity_threshold: Cosine similarity threshold (0-1)
        
    Returns:
        {
            "cluster_0": {
                "representative_claim": "SNNs achieve 90%+ accuracy on DVS datasets",
                "supporting_papers": ["paper1.pdf", "paper2.pdf", "paper3.pdf"],
                "claim_ids": ["c1", "c2", "c3"],
                "num_supporting_papers": 3,
                "agreement_level": "strong",  # strong|moderate|weak
                "average_score": 4.2,
                "score_variance": 0.15,
                "has_contradiction": False,
                "all_claims": [...]
            },
            ...
        }
    """
    if not claims:
        return {}
    
    # Embed all claim texts
    model = get_embedding_model()
    claim_texts = [c["extracted_claim_text"] for c in claims]
    embeddings = model.encode(claim_texts)
    
    # Cluster similar claims (DBSCAN uses cosine distance)
    # eps = 1 - similarity_threshold (lower eps = tighter clusters)
    clustering = DBSCAN(
        eps=1 - similarity_threshold, 
        min_samples=2,  # Require at least 2 claims for cluster
        metric='cosine'
    )
    labels = clustering.fit_predict(embeddings)
    
    # Analyze each cluster
    triangulation_results = {}
    
    for cluster_id in set(labels):
        if cluster_id == -1:  # Noise cluster (isolated claims)
            continue
        
        cluster_mask = labels == cluster_id
        cluster_claims = [claims[i] for i in np.where(cluster_mask)[0]]
        
        # Extract metadata
        supporting_papers = list(set(c.get("filename", "unknown") for c in cluster_claims))
        claim_ids = [c.get("claim_id", f"unknown_{i}") for i, c in enumerate(cluster_claims)]
        
        # Analyze agreement
        scores = [
            c.get("evidence_quality", {}).get("composite_score", 3.0) 
            for c in cluster_claims
        ]
        
        if scores:
            score_variance = float(np.var(scores))
            avg_score = float(np.mean(scores))
            
            # Classify agreement strength
            if score_variance < 0.3:
                agreement = "strong"
            elif score_variance < 0.7:
                agreement = "moderate"
            else:
                agreement = "weak"
        else:
            score_variance = None
            avg_score = None
            agreement = "unknown"
        
        # Find contradictions (claims with opposite verdicts)
        verdicts = [c.get("status", "unknown") for c in cluster_claims]
        has_contradiction = "approved" in verdicts and "rejected" in verdicts
        
        triangulation_results[f"cluster_{cluster_id}"] = {
            "representative_claim": cluster_claims[0]["extracted_claim_text"],
            "supporting_papers": supporting_papers,
            "claim_ids": claim_ids,
            "num_supporting_papers": len(supporting_papers),
            "agreement_level": agreement,
            "average_score": round(avg_score, 2) if avg_score else None,
            "score_variance": round(score_variance, 3) if score_variance else None,
            "has_contradiction": has_contradiction,
            "contradiction_details": _analyze_contradiction(cluster_claims) if has_contradiction else None,
            "all_claims": cluster_claims
        }
    
    return triangulation_results

def _analyze_contradiction(claims: List[Dict]) -> Dict:
    """Analyze contradictory claims in detail."""
    approved = [c for c in claims if c.get("status") == "approved"]
    rejected = [c for c in claims if c.get("status") == "rejected"]
    
    return {
        "num_approved": len(approved),
        "num_rejected": len(rejected),
        "approved_papers": [c.get("filename") for c in approved],
        "rejected_papers": [c.get("filename") for c in rejected],
        "score_gap": abs(
            np.mean([c.get("evidence_quality", {}).get("composite_score", 3.0) for c in approved]) -
            np.mean([c.get("evidence_quality", {}).get("composite_score", 3.0) for c in rejected])
        )
    }

def generate_triangulation_report(triangulation_results: Dict, output_file: str):
    """Generate markdown report of triangulation findings."""
    
    with open(output_file, 'w') as f:
        f.write("# Evidence Triangulation Report\n\n")
        f.write(f"**Total Clusters Found:** {len(triangulation_results)}\n\n")
        
        # Sort by number of supporting papers (descending)
        sorted_clusters = sorted(
            triangulation_results.items(),
            key=lambda x: x[1]["num_supporting_papers"],
            reverse=True
        )
        
        for cluster_name, cluster_data in sorted_clusters:
            f.write(f"## {cluster_name.replace('_', ' ').title()}\n\n")
            f.write(f"**Representative Claim:** {cluster_data['representative_claim']}\n\n")
            f.write(f"**Supporting Papers:** {cluster_data['num_supporting_papers']}\n")
            f.write(f"- {', '.join(cluster_data['supporting_papers'])}\n\n")
            f.write(f"**Agreement Level:** {cluster_data['agreement_level']}\n")
            f.write(f"**Average Quality Score:** {cluster_data['average_score']}\n")
            f.write(f"**Score Variance:** {cluster_data['score_variance']}\n\n")
            
            if cluster_data["has_contradiction"]:
                f.write(f"⚠️ **CONTRADICTION DETECTED**\n\n")
                details = cluster_data["contradiction_details"]
                f.write(f"- Approved: {details['num_approved']} papers\n")
                f.write(f"- Rejected: {details['num_rejected']} papers\n")
                f.write(f"- Score Gap: {details['score_gap']:.2f}\n\n")
            
            f.write("---\n\n")
```

### 2. Integration with literature_review/orchestrator.py (~40 lines)

```python
def run_triangulation_analysis(db: pd.DataFrame, pillar_definitions: Dict) -> Dict:
    """Run triangulation analysis for each sub-requirement."""
    
    from literature_review.analysis.evidence_triangulation import triangulate_evidence
    
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

## Testing Strategy

### Unit Tests

```python
from literature_review.analysis.evidence_triangulation import triangulate_evidence, _analyze_contradiction

@pytest.mark.unit
def test_claim_clustering():
    """Test semantic clustering of similar claims."""
    claims = [
        {"claim_id": "c1", "extracted_claim_text": "SNNs achieve 95% accuracy on DVS gesture dataset"},
        {"claim_id": "c2", "extracted_claim_text": "Spiking neural networks reach 94% accuracy on event-based gestures"},
        {"claim_id": "c3", "extracted_claim_text": "Transformers achieve 87% accuracy on ImageNet"}  # Different
    ]
    
    triangulation = triangulate_evidence(claims, similarity_threshold=0.85)
    
    # Should have 1 cluster (c1 and c2 are similar)
    assert len(triangulation) == 1
    cluster = list(triangulation.values())[0]
    assert cluster["num_supporting_papers"] == 2

@pytest.mark.unit
def test_contradiction_detection():
    """Test detection of contradictory claims."""
    claims = [
        {
            "claim_id": "c1",
            "extracted_claim_text": "SNNs are energy efficient",
            "status": "approved",
            "evidence_quality": {"composite_score": 4.0}
        },
        {
            "claim_id": "c2",
            "extracted_claim_text": "Spiking networks are energy-efficient",
            "status": "rejected",
            "evidence_quality": {"composite_score": 2.5}
        }
    ]
    
    triangulation = triangulate_evidence(claims)
    cluster = list(triangulation.values())[0]
    
    assert cluster["has_contradiction"] == True
    assert cluster["contradiction_details"]["num_approved"] == 1
    assert cluster["contradiction_details"]["num_rejected"] == 1
```

## Success Criteria

- [ ] Semantic embedding model loaded and cached
- [ ] DBSCAN clustering groups similar claims correctly
- [ ] Consensus strength calculated accurately
- [ ] Contradictions detected and reported
- [ ] Triangulation report generated in markdown
- [ ] Processing time increase <5%
- [ ] Unit tests pass (90% coverage)
- [ ] Integration tests validate cross-paper validation

## Benefits

1. **Strengthen evidence** - Multiple papers supporting same claim
2. **Flag contradictions** - Different conclusions requiring investigation
3. **Identify consensus** - Field-wide agreement on findings
4. **Quality signal** - Replication indicates reliability

---

**Status:** Ready for implementation  
**Wave:** Wave 4 (Weeks 7-8)  
**Next Steps:** Create literature_review/analysis/evidence_triangulation.py module, integrate with literature_review/orchestrator.py, add triangulation to gap analysis report
