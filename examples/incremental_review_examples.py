"""
Incremental Review Mode - Code Examples

This file demonstrates programmatic usage of the incremental review mode features.

Examples include:
1. Running incremental analysis programmatically
2. Extracting gaps from previous reports
3. Scoring paper relevance to gaps
4. Working with state management
5. Merging incremental results

Dependencies:
    - literature_review.orchestrator
    - literature_review.utils.gap_extractor
    - literature_review.utils.relevance_scorer
    - literature_review.utils.state_manager
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from literature_review.utils.gap_extractor import GapExtractor
from literature_review.utils.relevance_scorer import RelevanceScorer
from literature_review.utils.state_manager import StateManager, JobType


# =============================================================================
# Example 1: Run Incremental Analysis Programmatically
# =============================================================================

def run_incremental_analysis_example():
    """
    Demonstrates how to run incremental analysis programmatically instead of
    using the CLI.
    """
    print("\n" + "="*80)
    print("Example 1: Run Incremental Analysis Programmatically")
    print("="*80)
    
    from literature_review.orchestrator import PipelineOrchestrator
    
    # Configure incremental analysis
    config = {
        'output_dir': 'reviews/my_review',
        'incremental': True,
        'relevance_threshold': 0.60,
        'prefilter_enabled': True,
        'parent_job_id': None,  # Auto-detect from previous state
    }
    
    # Initialize orchestrator
    orchestrator = PipelineOrchestrator(
        output_folder=config['output_dir'],
        incremental=config['incremental'],
        force=False,
        relevance_threshold=config['relevance_threshold'],
    )
    
    print(f"Configured orchestrator for incremental mode:")
    print(f"  Output directory: {config['output_dir']}")
    print(f"  Relevance threshold: {config['relevance_threshold']}")
    print(f"  Prefilter enabled: {config['prefilter_enabled']}")
    
    # Check if prerequisites are met
    prerequisites_met = orchestrator._check_incremental_prerequisites()
    
    if prerequisites_met:
        print("\n✅ Prerequisites met - running incremental analysis")
        # Run incremental pipeline
        # orchestrator.run()  # Uncomment to actually run
    else:
        print("\n⚠️ Prerequisites not met - would fall back to full analysis")
        # orchestrator.run()  # Would run full mode instead
    
    print("\nNote: Uncomment orchestrator.run() to actually execute the pipeline")


# =============================================================================
# Example 2: Extract Gaps from Previous Analysis
# =============================================================================

def extract_gaps_example():
    """
    Demonstrates how to extract unfilled research gaps from a completed
    gap analysis report.
    """
    print("\n" + "="*80)
    print("Example 2: Extract Gaps from Previous Analysis")
    print("="*80)
    
    # Path to previous gap analysis report
    gap_report_path = 'reviews/baseline/gap_analysis_report.json'
    
    # Check if report exists
    if not Path(gap_report_path).exists():
        print(f"⚠️ Gap report not found at: {gap_report_path}")
        print("   Run a full analysis first to generate the report:")
        print(f"   python pipeline_orchestrator.py --output-dir reviews/baseline")
        return
    
    # Initialize gap extractor
    extractor = GapExtractor(
        gap_report_path=gap_report_path,
        threshold=0.7  # Gaps are requirements with coverage < 70%
    )
    
    # Extract gaps
    print(f"\nExtracting gaps from: {gap_report_path}")
    print(f"Coverage threshold: 70%")
    
    gaps = extractor.extract_gaps()
    
    print(f"\n📊 Found {len(gaps)} gaps:")
    print("-" * 80)
    
    # Display first few gaps
    for i, gap in enumerate(gaps[:5], 1):
        print(f"\n{i}. Gap in {gap.get('pillar_name', 'Unknown Pillar')}")
        print(f"   Sub-requirement: {gap.get('sub_requirement_id', 'N/A')}")
        print(f"   Current coverage: {gap.get('current_coverage', 0):.1%}")
        print(f"   Target coverage: {gap.get('target_coverage', 0.7):.1%}")
        print(f"   Gap severity: {gap.get('gap_severity', 'unknown')}")
        
        keywords = gap.get('keywords', [])
        if keywords:
            print(f"   Keywords: {', '.join(keywords[:5])}")
    
    if len(gaps) > 5:
        print(f"\n... and {len(gaps) - 5} more gaps")
    
    # Summary by pillar
    pillar_counts = {}
    for gap in gaps:
        pillar = gap.get('pillar_name', 'Unknown')
        pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1
    
    print("\n📈 Gaps by pillar:")
    for pillar, count in sorted(pillar_counts.items()):
        print(f"   {pillar}: {count} gaps")


# =============================================================================
# Example 3: Score Paper Relevance to Gaps
# =============================================================================

def score_paper_relevance_example():
    """
    Demonstrates how to score the relevance of papers to identified gaps.
    This is the core of gap-targeted pre-filtering.
    """
    print("\n" + "="*80)
    print("Example 3: Score Paper Relevance to Gaps")
    print("="*80)
    
    # Initialize relevance scorer
    scorer = RelevanceScorer()
    
    # Sample paper metadata
    paper = {
        'Title': 'Spike-Timing Dependent Plasticity in Memristive Neuromorphic Systems',
        'Abstract': (
            'This paper explores the implementation of spike-timing dependent '
            'plasticity (STDP) using memristive devices in neuromorphic hardware. '
            'We demonstrate that RRAM-based synapses can achieve biologically '
            'realistic learning dynamics with low power consumption.'
        ),
        'DOI': '10.1000/example.2025.001',
        'Authors': 'Smith, J., Doe, A., Johnson, B.',
        'Year': 2025
    }
    
    # Sample gap (from Example 2)
    gap = {
        'pillar_name': 'Pillar 1: Hardware Architectures',
        'sub_requirement_id': '1.2.1',
        'description': 'Memristive devices for synaptic plasticity',
        'keywords': ['memristor', 'RRAM', 'STDP', 'synaptic plasticity', 'neuromorphic'],
        'current_coverage': 0.45,
        'target_coverage': 0.70,
        'gap_severity': 'high'
    }
    
    print(f"\nScoring paper relevance:")
    print(f"  Paper: {paper['Title'][:60]}...")
    print(f"  Gap: {gap['description']}")
    print(f"  Gap keywords: {', '.join(gap['keywords'])}")
    
    # Score relevance
    relevance_score = scorer.score_relevance(paper, gap)
    
    print(f"\n📊 Relevance score: {relevance_score:.1%}")
    
    # Interpret score
    if relevance_score >= 0.70:
        print("   ✅ HIGH relevance - strongly recommended for analysis")
    elif relevance_score >= 0.50:
        print("   ⚠️ MEDIUM relevance - recommended for analysis (default threshold)")
    elif relevance_score >= 0.30:
        print("   ℹ️ LOW relevance - may be analyzed with aggressive filtering")
    else:
        print("   ❌ VERY LOW relevance - likely to be filtered out")
    
    # Score multiple papers
    print("\n" + "-"*80)
    print("Scoring multiple papers:")
    
    papers = [
        {
            'Title': 'Deep Learning on GPUs for Image Classification',
            'Abstract': 'We train ResNet models on ImageNet using CUDA...',
        },
        {
            'Title': 'Neuromorphic Computing with Spiking Neural Networks',
            'Abstract': 'Spiking neural networks implemented on neuromorphic hardware...',
        },
        {
            'Title': 'Memristive Synapses for Brain-Inspired Computing',
            'Abstract': 'We demonstrate RRAM-based synaptic plasticity in hardware...',
        }
    ]
    
    print(f"\nScoring {len(papers)} papers against gap '{gap['description']}':\n")
    for i, p in enumerate(papers, 1):
        score = scorer.score_relevance(p, gap)
        title = p['Title'][:50] + "..." if len(p['Title']) > 50 else p['Title']
        print(f"{i}. {title}")
        print(f"   Score: {score:.1%} {'✅' if score >= 0.5 else '❌'}")


# =============================================================================
# Example 4: Work with State Manager
# =============================================================================

def state_manager_example():
    """
    Demonstrates how job state and lineage tracking works in incremental mode.
    
    Note: This example shows the state file structure. The StateManager is
    typically used internally by the pipeline orchestrator.
    """
    print("\n" + "="*80)
    print("Example 4: Job State and Lineage Tracking")
    print("="*80)
    
    output_dir = Path('/tmp/incremental_examples/state')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Example 1: Full analysis job state
    print("\n1. Full Analysis Job State:")
    print("-" * 80)
    
    full_job_state = {
        'schema_version': '2.0',
        'job_id': 'review_20250115_103000',
        'job_type': 'full',
        'parent_job_id': None,  # No parent - this is a baseline
        'timestamp': '2025-01-15T10:30:00',
        'database_hash': 'abc123def456',
        'analysis_completed': True,
        'gap_metrics': {
            'total_gaps': 23,
            'gaps_by_pillar': {
                'Pillar 1: Hardware': 5,
                'Pillar 2: Algorithms': 8,
                'Pillar 3: Applications': 10
            }
        }
    }
    
    print(json.dumps(full_job_state, indent=2))
    
    # Save full job state
    full_state_file = output_dir / 'baseline_state.json'
    with open(full_state_file, 'w') as f:
        json.dump(full_job_state, f, indent=2)
    
    print(f"\n✓ Saved to: {full_state_file}")
    
    # Example 2: Incremental continuation job state
    print("\n2. Incremental Continuation Job State:")
    print("-" * 80)
    
    incremental_job_state = {
        'schema_version': '2.0',
        'job_id': 'review_20250120_143000',
        'job_type': 'incremental',
        'parent_job_id': 'review_20250115_103000',  # References the baseline
        'timestamp': '2025-01-20T14:30:00',
        'database_hash': 'abc123def456_updated',
        'analysis_completed': True,
        'gap_metrics': {
            'total_gaps': 18,  # 5 gaps closed!
            'gaps_by_pillar': {
                'Pillar 1: Hardware': 3,
                'Pillar 2: Algorithms': 6,
                'Pillar 3: Applications': 9
            }
        },
        'incremental_state': {
            'papers_analyzed': 15,  # Only 15 new papers analyzed
            'papers_filtered': 35,  # 35 papers skipped (irrelevant)
            'relevance_threshold': 0.50,
            'gaps_closed': 5
        }
    }
    
    print(json.dumps(incremental_job_state, indent=2))
    
    # Save incremental job state
    incremental_state_file = output_dir / 'incremental_state.json'
    with open(incremental_state_file, 'w') as f:
        json.dump(incremental_job_state, f, indent=2)
    
    print(f"\n✓ Saved to: {incremental_state_file}")
    
    # Example 3: Job lineage tracking
    print("\n3. Job Lineage:")
    print("-" * 80)
    
    print(f"Baseline Job:      {full_job_state['job_id']}")
    print(f"  ↓ (parent)")
    print(f"Continuation Job:  {incremental_job_state['job_id']}")
    print(f"\nGaps reduced: {full_job_state['gap_metrics']['total_gaps']} → "
          f"{incremental_job_state['gap_metrics']['total_gaps']} "
          f"({full_job_state['gap_metrics']['total_gaps'] - incremental_job_state['gap_metrics']['total_gaps']} closed)")
    
    print("\n✅ State and lineage tracking demonstration complete")


# =============================================================================
# Example 5: Filter Papers Based on Relevance
# =============================================================================

def filter_papers_example():
    """
    Demonstrates the complete workflow of filtering papers based on relevance
    to gaps before running expensive deep analysis.
    """
    print("\n" + "="*80)
    print("Example 5: Filter Papers Based on Relevance")
    print("="*80)
    
    # Sample gaps (in practice, loaded from gap_analysis_report.json)
    gaps = [
        {
            'pillar_name': 'Pillar 1: Hardware',
            'sub_requirement_id': '1.1',
            'keywords': ['memristor', 'RRAM', 'synaptic'],
            'current_coverage': 0.40,
        },
        {
            'pillar_name': 'Pillar 2: Algorithms',
            'sub_requirement_id': '2.1',
            'keywords': ['spiking', 'neural network', 'learning'],
            'current_coverage': 0.55,
        }
    ]
    
    # Sample new papers
    papers = [
        {'Title': 'Memristive Synaptic Devices for Neuromorphic Computing', 'Abstract': 'RRAM devices...'},
        {'Title': 'Deep Learning with Transformers', 'Abstract': 'Attention mechanisms...'},
        {'Title': 'Spiking Neural Networks on FPGAs', 'Abstract': 'Hardware implementation...'},
        {'Title': 'Quantum Computing Algorithms', 'Abstract': 'Quantum gates...'},
        {'Title': 'STDP in Biological and Artificial Neurons', 'Abstract': 'Synaptic plasticity...'},
    ]
    
    threshold = 0.50
    scorer = RelevanceScorer()
    
    print(f"\nFiltering {len(papers)} papers with threshold {threshold:.0%}:")
    print(f"Evaluating against {len(gaps)} gaps")
    print("-" * 80)
    
    papers_to_analyze = []
    papers_filtered = []
    
    for paper in papers:
        # Score against all gaps, take max
        max_score = max(scorer.score_relevance(paper, gap) for gap in gaps)
        
        title = paper['Title'][:50] + "..." if len(paper['Title']) > 50 else paper['Title']
        
        if max_score >= threshold:
            papers_to_analyze.append((paper, max_score))
            print(f"✅ ANALYZE ({max_score:.0%}): {title}")
        else:
            papers_filtered.append((paper, max_score))
            print(f"❌ SKIP ({max_score:.0%}): {title}")
    
    print("\n" + "="*80)
    print(f"📊 Filtering Results:")
    print(f"   Papers to analyze: {len(papers_to_analyze)} ({len(papers_to_analyze)/len(papers)*100:.0%}%)")
    print(f"   Papers filtered: {len(papers_filtered)} ({len(papers_filtered)/len(papers)*100:.0%}%)")
    
    if papers_to_analyze:
        print(f"\n   Cost savings: ~{len(papers_filtered)/len(papers)*100:.0%}% reduction in analysis")
        print(f"   Time savings: ~{len(papers_filtered)/len(papers)*100:.0%}% faster execution")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("INCREMENTAL REVIEW MODE - CODE EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates programmatic usage of incremental review features.")
    print("Each example is self-contained and can be run independently.")
    
    examples = [
        ("1", "Run Incremental Analysis Programmatically", run_incremental_analysis_example),
        ("2", "Extract Gaps from Previous Analysis", extract_gaps_example),
        ("3", "Score Paper Relevance to Gaps", score_paper_relevance_example),
        ("4", "Job State and Lineage Tracking", state_manager_example),
        ("5", "Filter Papers Based on Relevance", filter_papers_example),
    ]
    
    print("\nAvailable examples:")
    for num, title, _ in examples:
        print(f"  {num}. {title}")
    
    print("\nRunning all examples...\n")
    
    for num, title, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n⚠️ Error in Example {num}: {e}")
            print(f"   This is expected if prerequisite files don't exist.")
            print(f"   Run: python pipeline_orchestrator.py --output-dir reviews/baseline")
    
    print("\n" + "="*80)
    print("✅ Examples complete!")
    print("="*80)
    print("\nTo use these examples:")
    print("1. Run a baseline analysis to create required files")
    print("2. Modify the code to work with your specific data")
    print("3. Import functions into your own scripts")
    print("\nSee INCREMENTAL_REVIEW_USER_GUIDE.md for more information.")


if __name__ == '__main__':
    main()
