#!/usr/bin/env python3
"""
Evidence Triangulation Example
Demonstrates the triangulation module with sample claims.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from literature_review.analysis.evidence_triangulation import (
    triangulate_evidence,
    generate_triangulation_report,
)


def create_example_claims():
    """Create example claims for demonstration."""
    return [
        # Cluster 1: SNN Energy Efficiency (Strong Agreement)
        {
            "claim_id": "claim_001",
            "extracted_claim_text": "Spiking neural networks consume 90% less energy than traditional ANNs",
            "filename": "paper_smith_2024.pdf",
            "status": "approved",
            "evidence_quality": {"composite_score": 4.5},
        },
        {
            "claim_id": "claim_002",
            "extracted_claim_text": "SNNs demonstrate energy consumption reduction of 85-95% compared to ANNs",
            "filename": "paper_jones_2023.pdf",
            "status": "approved",
            "evidence_quality": {"composite_score": 4.3},
        },
        {
            "claim_id": "claim_003",
            "extracted_claim_text": "Neuromorphic spiking networks achieve >90% energy savings vs conventional neural nets",
            "filename": "paper_liu_2024.pdf",
            "status": "approved",
            "evidence_quality": {"composite_score": 4.6},
        },
    ]


def main():
    """Run triangulation example."""
    print("=" * 70)
    print("Evidence Triangulation Example")
    print("=" * 70)

    # Create sample claims
    claims = create_example_claims()
    print(f"\nCreated {len(claims)} example claims for analysis\n")

    # Run triangulation
    print("Running triangulation analysis (similarity threshold: 0.85)...")
    results = triangulate_evidence(claims, similarity_threshold=0.85)

    print(f"\nFound {len(results)} clusters\n")
    
    # Display results
    for cluster_id, cluster in results.items():
        print(f"\n{cluster_id.upper()}")
        print("-" * 70)
        claim_text = cluster["representative_claim"][:80] + "..."
        print(f"Representative Claim: {claim_text}")
        print(f"Supporting Papers:    {cluster['num_supporting_papers']}")
        print(f"Agreement Level:      {cluster['agreement_level'].upper()}")
        print(f"Average Score:        {cluster['average_score']}")
        print(f"Score Variance:       {cluster['score_variance']}")

    # Generate report
    output_dir = Path("/tmp/triangulation_demo")
    output_dir.mkdir(exist_ok=True)
    report_file = output_dir / "triangulation_report.md"

    print(f"\nGenerating report: {report_file}")
    generate_triangulation_report(results, str(report_file))
    
    if report_file.exists():
        print("✅ Report generated successfully!\n")
    else:
        print("❌ Report generation failed")

    print(f"\n{'=' * 70}")
    print("Example Complete")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
