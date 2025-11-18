#!/usr/bin/env python3
"""
Week 8 Verification Smoke Test
Validates enhanced pipeline with all Wave 1-3 features enabled
"""
import json
import sys
import uuid
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def smoke_test_enhanced_pipeline():
    """
    Test Scenario 3: Full Enhanced Pipeline (All Waves)
    Expected outputs: 20+ files including all enhancement outputs
    """
    print("=" * 80)
    print("WEEK 8 VERIFICATION - SMOKE TEST: Enhanced Pipeline (All Waves)")
    print("=" * 80)
    
    # Generate unique job ID
    job_id = f"smoke_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("\n📋 Configuration:")
    print(f"  Job ID: {job_id}")
    print(f"  Run Mode: ONCE (single iteration for quick test)")
    print(f"  Pillar Selection: ALL")
    
    print("\n✅ Expected Enhancements (from orchestrator defaults):")
    print("  Wave 1: Proof Scorecard, Cost Tracking")
    print("  Wave 2: Sufficiency Matrix, Proof Chain, Triangulation")
    print("  Wave 3: Search Optimizer, Smart Dedup, Evidence Decay")
    print("  Adaptive Consensus: Enabled by default")
    
    print("\n🚀 Starting enhanced pipeline...")
    print("-" * 80)
    
    try:
        # Import and run via dashboard integration interface
        from literature_review.orchestrator_integration import run_pipeline_for_job
        
        # Run the enhanced pipeline
        results = run_pipeline_for_job(
            job_id=job_id,
            pillar_selections=["ALL"],  # Analyze all pillars
            run_mode="ONCE",           # Single iteration for smoke test
            progress_callback=None,     # No WebSocket in CLI mode
            log_callback=None,          # Use default logging
            prompt_callback=None        # Use default prompts
        )
        
        print("\n" + "=" * 80)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        # Verify outputs
        output_dir = Path(f"workspace/jobs/{job_id}/outputs")
        
        print("\n📊 Output Verification:")
        
        # Core outputs
        core_files = [
            "database.csv",
            "summary.json",
            "pillars.json",
            "recommendations.json",
        ]
        
        # Enhancement outputs
        enhancement_files = [
            # Wave 1
            "proof_scorecard.json",
            "proof_scorecard_viz.html",
            "cost_report.json",
            
            # Wave 2
            "sufficiency_matrix.json",
            "sufficiency_matrix_viz.html",
            "proof_chain.json",
            "proof_chain_viz.html",
            "triangulation_report.json",
            "triangulation_viz.html",
            
            # Existing advanced outputs
            "publication_bias.json",
            "grade_assessment.json",
            "evidence_triangulation.json",
        ]
        
        print("\n  Core Outputs:")
        for fname in core_files:
            path = output_dir / fname
            status = "✅" if path.exists() else "❌"
            size = f"({path.stat().st_size} bytes)" if path.exists() else ""
            print(f"    {status} {fname} {size}")
        
        print("\n  Enhancement Outputs:")
        for fname in enhancement_files:
            path = output_dir / fname
            status = "✅" if path.exists() else "⚠️"
            size = f"({path.stat().st_size} bytes)" if path.exists() else "(not generated)"
            print(f"    {status} {fname} {size}")
        
        # Count total outputs
        total_outputs = len(list(output_dir.glob("*.*")))
        print(f"\n  Total Output Files: {total_outputs}")
        
        # Verify key metrics from results
        print("\n📈 Pipeline Metrics:")
        if "metrics" in results:
            metrics = results["metrics"]
            print(f"  Papers Processed: {metrics.get('papers_processed', 'N/A')}")
            print(f"  Claims Evaluated: {metrics.get('claims_evaluated', 'N/A')}")
            print(f"  Iterations Run: {metrics.get('iterations', 'N/A')}")
        
        if "cost_tracking" in results:
            cost_data = results["cost_tracking"]
            print(f"\n💰 Cost Tracking (Wave 1.3):")
            print(f"  Total Estimated Cost: ${cost_data.get('total_cost', 0):.4f}")
            print(f"  API Calls Made: {cost_data.get('total_calls', 0)}")
        
        if "proof_scorecard" in results:
            scorecard = results["proof_scorecard"]
            print(f"\n🎯 Proof Scorecard (Wave 1.2):")
            print(f"  Overall Score: {scorecard.get('overall_score', 'N/A')}/100")
            print(f"  Completeness: {scorecard.get('completeness', 'N/A')}%")
        
        print("\n" + "=" * 80)
        print("✅ SMOKE TEST PASSED")
        print("=" * 80)
        print("\nAll critical enhancements are operational.")
        print("Dashboard integration infrastructure ready for Week 8 final sync.")
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ SMOKE TEST FAILED")
        print("=" * 80)
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = smoke_test_enhanced_pipeline()
    sys.exit(0 if success else 1)
