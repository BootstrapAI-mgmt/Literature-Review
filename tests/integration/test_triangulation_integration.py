"""
Integration Test for Evidence Triangulation
Tests the complete flow with realistic claim data
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis.evidence_triangulation import (
    triangulate_evidence,
    generate_triangulation_report
)


def load_example_claims():
    """Load example claims from version history for testing."""
    # Use the example version history file
    example_file = Path(__file__).parent.parent.parent / "data" / "examples" / "review_version_history_EXAMPLE.json"
    
    if not example_file.exists():
        print(f"Example file not found: {example_file}")
        return []
    
    with open(example_file, 'r') as f:
        version_history = json.load(f)
    
    # Extract all claims from all papers
    all_claims = []
    for filename, versions in version_history.items():
        for version in versions:
            review = version.get("review", {})
            requirements = review.get("Requirement(s)", [])
            
            for req in requirements:
                if isinstance(req, dict):
                    # Add filename to claim for tracking
                    req["filename"] = filename
                    
                    # Ensure we have the right field names
                    if "claim_summary" in req and "extracted_claim_text" not in req:
                        req["extracted_claim_text"] = req["claim_summary"]
                    
                    # Add default evidence_quality if missing (for pending claims)
                    if "evidence_quality" not in req:
                        req["evidence_quality"] = {"composite_score": 3.0}
                    
                    all_claims.append(req)
    
    return all_claims


def test_triangulation_with_real_data():
    """Test triangulation with real claims from example data."""
    print("\n=== Testing Evidence Triangulation with Real Data ===\n")
    
    # Load claims
    claims = load_example_claims()
    print(f"Loaded {len(claims)} claims from example data")
    
    if len(claims) < 2:
        print("Not enough claims for testing. Need at least 2 claims.")
        return
    
    # Run triangulation
    print("\nRunning triangulation analysis...")
    triangulation_results = triangulate_evidence(claims, similarity_threshold=0.85)
    
    print(f"Found {len(triangulation_results)} clusters")
    
    # Display results
    for cluster_id, cluster_data in triangulation_results.items():
        print(f"\n{cluster_id}:")
        print(f"  Papers: {cluster_data['num_supporting_papers']}")
        print(f"  Agreement: {cluster_data['agreement_level']}")
        print(f"  Avg Score: {cluster_data['average_score']}")
        print(f"  Variance: {cluster_data['score_variance']}")
        if cluster_data['has_contradiction']:
            print(f"  ⚠️ CONTRADICTION DETECTED")
        
        # Show first 100 chars of representative claim
        rep = cluster_data['representative_claim'][:100]
        print(f"  Claim: {rep}...")
    
    # Generate report
    output_dir = Path("/tmp/triangulation_test")
    output_dir.mkdir(exist_ok=True)
    report_file = output_dir / "triangulation_report.md"
    
    print(f"\nGenerating report to {report_file}...")
    generate_triangulation_report(triangulation_results, str(report_file))
    
    if report_file.exists():
        print("✅ Report generated successfully")
        print(f"\nReport preview (first 500 chars):")
        with open(report_file, 'r') as f:
            preview = f.read()[:500]
            print(preview)
            print("...")
    else:
        print("❌ Report generation failed")
    
    print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    test_triangulation_with_real_data()
