"""
Evidence Triangulation Module (Task Card #20)

This module groups similar claims using semantic embeddings and analyzes 
cross-paper agreement to strengthen evidence quality assessment.

Author: AI Research System
Version: 1.0
Date: 2025-11-14
"""

from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
import numpy as np
from typing import List, Dict, Optional
import os

# Global embedding model cache
_embedding_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """
    Get cached sentence embedding model.
    
    Returns:
        SentenceTransformer: The cached embedding model (all-MiniLM-L6-v2)
    """
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


def triangulate_evidence(
    claims: List[Dict], 
    similarity_threshold: float = 0.85
) -> Dict:
    """
    Group similar claims and analyze cross-paper agreement.
    
    This function uses DBSCAN clustering with cosine similarity to identify
    groups of semantically similar claims across papers, then analyzes:
    - Agreement strength (score variance)
    - Number of supporting papers
    - Presence of contradictions (approved vs rejected)
    
    Args:
        claims: List of claim dicts with evidence_quality and metadata.
               Expected keys: extracted_claim_text, evidence_quality, 
               status, filename, claim_id
        similarity_threshold: Cosine similarity threshold (0-1). 
                            Higher = stricter clustering. Default: 0.85
        
    Returns:
        Dictionary mapping cluster IDs to cluster analysis:
        {
            "cluster_0": {
                "representative_claim": "SNNs achieve 90%+ accuracy...",
                "supporting_papers": ["paper1.pdf", "paper2.pdf"],
                "claim_ids": ["c1", "c2"],
                "num_supporting_papers": 2,
                "agreement_level": "strong",  # strong|moderate|weak
                "average_score": 4.2,
                "score_variance": 0.15,
                "has_contradiction": False,
                "contradiction_details": None,
                "all_claims": [...]
            },
            ...
        }
    """
    if not claims:
        return {}
    
    # Extract claim texts for embedding
    claim_texts = []
    for claim in claims:
        # Support both direct text field and evidence_chunk fallback
        text = claim.get("extracted_claim_text") or \
               claim.get("claim_summary") or \
               claim.get("evidence_chunk", "")
        claim_texts.append(text)
    
    # Generate embeddings
    model = get_embedding_model()
    embeddings = model.encode(claim_texts)
    
    # Cluster similar claims using DBSCAN with cosine distance
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
        
        # Get claims in this cluster
        cluster_mask = labels == cluster_id
        cluster_indices = np.where(cluster_mask)[0]
        cluster_claims = [claims[i] for i in cluster_indices]
        
        # Extract metadata
        supporting_papers = list(set(
            c.get("filename", "unknown") for c in cluster_claims
        ))
        claim_ids = [
            c.get("claim_id", f"unknown_{i}") 
            for i, c in enumerate(cluster_claims)
        ]
        
        # Analyze agreement using composite scores
        scores = []
        for claim in cluster_claims:
            evidence_quality = claim.get("evidence_quality", {})
            score = evidence_quality.get("composite_score", 3.0)
            scores.append(score)
        
        if scores:
            score_variance = float(np.var(scores))
            avg_score = float(np.mean(scores))
            
            # Classify agreement strength based on variance
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
        
        # Detect contradictions (claims with opposite verdicts)
        verdicts = [c.get("status", "unknown") for c in cluster_claims]
        has_contradiction = "approved" in verdicts and "rejected" in verdicts
        
        # Get representative claim (first one in cluster)
        representative_text = (
            cluster_claims[0].get("extracted_claim_text") or
            cluster_claims[0].get("claim_summary") or
            cluster_claims[0].get("evidence_chunk", "Unknown claim")
        )
        
        triangulation_results[f"cluster_{cluster_id}"] = {
            "representative_claim": representative_text,
            "supporting_papers": supporting_papers,
            "claim_ids": claim_ids,
            "num_supporting_papers": len(supporting_papers),
            "agreement_level": agreement,
            "average_score": round(avg_score, 2) if avg_score else None,
            "score_variance": round(score_variance, 3) if score_variance else None,
            "has_contradiction": has_contradiction,
            "contradiction_details": (
                _analyze_contradiction(cluster_claims) 
                if has_contradiction else None
            ),
            "all_claims": cluster_claims
        }
    
    return triangulation_results


def _analyze_contradiction(claims: List[Dict]) -> Dict:
    """
    Analyze contradictory claims in detail.
    
    Args:
        claims: List of claims in the same cluster with contradictions
        
    Returns:
        Dictionary with contradiction analysis:
        {
            "num_approved": int,
            "num_rejected": int,
            "approved_papers": [filenames],
            "rejected_papers": [filenames],
            "score_gap": float
        }
    """
    approved = [c for c in claims if c.get("status") == "approved"]
    rejected = [c for c in claims if c.get("status") == "rejected"]
    
    # Calculate average scores for each group
    approved_scores = [
        c.get("evidence_quality", {}).get("composite_score", 3.0) 
        for c in approved
    ]
    rejected_scores = [
        c.get("evidence_quality", {}).get("composite_score", 3.0) 
        for c in rejected
    ]
    
    avg_approved = np.mean(approved_scores) if approved_scores else 0
    avg_rejected = np.mean(rejected_scores) if rejected_scores else 0
    
    return {
        "num_approved": len(approved),
        "num_rejected": len(rejected),
        "approved_papers": [c.get("filename", "unknown") for c in approved],
        "rejected_papers": [c.get("filename", "unknown") for c in rejected],
        "score_gap": abs(avg_approved - avg_rejected)
    }


def generate_triangulation_report(
    triangulation_results: Dict, 
    output_file: str
) -> None:
    """
    Generate markdown report of triangulation findings.
    
    Args:
        triangulation_results: Output from triangulate_evidence()
        output_file: Path to output markdown file
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Evidence Triangulation Report\n\n")
        f.write(f"**Total Clusters Found:** {len(triangulation_results)}\n\n")
        
        # Sort by number of supporting papers (descending)
        sorted_clusters = sorted(
            triangulation_results.items(),
            key=lambda x: x[1]["num_supporting_papers"],
            reverse=True
        )
        
        for cluster_name, cluster_data in sorted_clusters:
            # Format cluster header
            cluster_title = cluster_name.replace('_', ' ').title()
            f.write(f"## {cluster_title}\n\n")
            
            # Representative claim
            rep_claim = cluster_data['representative_claim']
            # Truncate if very long
            if len(rep_claim) > 200:
                rep_claim = rep_claim[:200] + "..."
            f.write(f"**Representative Claim:** {rep_claim}\n\n")
            
            # Support metrics
            f.write(f"**Supporting Papers:** {cluster_data['num_supporting_papers']}\n")
            f.write(f"- {', '.join(cluster_data['supporting_papers'])}\n\n")
            
            # Agreement analysis
            f.write(f"**Agreement Level:** {cluster_data['agreement_level']}\n")
            f.write(f"**Average Quality Score:** {cluster_data['average_score']}\n")
            f.write(f"**Score Variance:** {cluster_data['score_variance']}\n\n")
            
            # Contradiction details
            if cluster_data["has_contradiction"]:
                f.write("⚠️ **CONTRADICTION DETECTED**\n\n")
                details = cluster_data["contradiction_details"]
                f.write(f"- Approved: {details['num_approved']} papers\n")
                f.write(f"- Rejected: {details['num_rejected']} papers\n")
                f.write(f"- Score Gap: {details['score_gap']:.2f}\n\n")
            
            f.write("---\n\n")
