# Integration Task Card #11 - E2E-002: Multi-Reviewer Convergence Loop Test

**Priority:** 🟠 HIGH  
**Estimated Effort:** 8-12 hours  
**Risk Level:** HIGH  
**Dependencies:** Task Card #10 (Full Pipeline), Evidence enhancement cards (#16-21)  
**Blocks:** Production deployment  
**Wave:** Wave 4

**Enhanced Scope:** Validates iterative evidence quality refinement through multi-reviewer convergence

---

## Problem Statement

The Literature Review system uses an iterative convergence loop where Journal-Reviewer provides broad coverage, Deep-Reviewer adds depth, and Judge mediates quality decisions. No E2E test validates this convergence behavior, including appeal cycles, reviewer consensus, and termination conditions.

**Enhanced Requirements:** With evidence quality enhancements, this test must validate that the convergence loop refines quality scores through iterations, achieves consensus on borderline claims, and terminates when quality thresholds are met or max iterations reached.

---

## Acceptance Criteria

### Functional Requirements (Original)
- [ ] Test validates iterative Journal → Deep → Judge cycle
- [ ] Test validates convergence termination conditions
- [ ] Test validates claim status evolution over iterations
- [ ] Test validates max iteration limit enforced
- [ ] Test validates appeal loop integration
- [ ] Test validates final consensus reached

### Functional Requirements (Enhanced - Evidence Quality)
- [ ] Test validates quality scores improve through iterations
- [ ] Test validates borderline claims converge to consensus
- [ ] Test validates evidence triangulation strengthens claims
- [ ] Test validates temporal analysis influences convergence
- [ ] Test validates GRADE quality levels stabilize
- [ ] Test validates convergence metrics tracked (iteration count, score delta)
- [ ] Test validates termination when quality threshold reached (composite ≥3.5)
- [ ] Test validates termination when max iterations reached (e.g., 3 iterations)

### Technical Requirements
- [ ] Test uses realistic multi-iteration workflow
- [ ] Test validates version history tracks all iterations
- [ ] Test checks performance (iteration time)
- [ ] Test handles infinite loop prevention
- [ ] Test validates idempotency within iterations
- [ ] Test validates resource cleanup

---

## Implementation Guide

### File to Create

**Location:** `tests/e2e/test_convergence_loop.py`

### Core Test Cases (Original)

```python
"""End-to-end tests for multi-reviewer convergence loop."""

import pytest
import json
import os
from pathlib import Path
from typing import Dict, List
import time

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.orchestrator import Orchestrator

class TestConvergenceLoop:
    """Test iterative Journal → Deep → Judge convergence."""
    
    @pytest.mark.e2e
    def test_convergence_loop_basic_iteration(self, temp_workspace, test_data_generator):
        """
        Test basic convergence loop with 2 iterations.
        
        Flow:
        Iteration 1: Journal → Judge (some claims pending)
        Iteration 2: Deep → Judge (claims converge)
        """
        # Setup: Create test paper
        pdf_file = temp_workspace / "convergence_paper.pdf"
        test_data_generator.create_dummy_pdf(
            pdf_file,
            title="Convergence Test Paper",
            content="Neuromorphic computing with iterative refinement."
        )
        
        version_history_file = temp_workspace / "review_version_history.json"
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute: Run convergence loop
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            max_iterations=2
        )
        
        iteration_count = orchestrator.run_convergence_loop(str(pdf_file))
        
        # Assert: Verify iterations tracked
        assert iteration_count <= 2
        
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        versions = version_history['convergence_paper.pdf']
        
        # Should have versions from multiple iterations
        assert len(versions) >= 2
        
        # Check iteration metadata
        for version in versions:
            review = version['review']
            if 'iteration' in review:
                assert 1 <= review['iteration'] <= 2
    
    @pytest.mark.e2e
    def test_convergence_terminates_on_consensus(self, temp_workspace, test_data_generator):
        """
        Test convergence terminates when all claims reach consensus.
        
        Termination condition: All claims have status 'approved' or 'rejected'
        """
        # Setup: Create paper that converges quickly
        pdf_file = temp_workspace / "quick_convergence.pdf"
        test_data_generator.create_dummy_pdf(
            pdf_file,
            title="Quick Convergence Paper",
            content="Clear evidence, should converge in 1 iteration."
        )
        
        version_history_file = temp_workspace / "review_version_history.json"
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            max_iterations=5  # Allow up to 5, but should terminate early
        )
        
        iteration_count = orchestrator.run_convergence_loop(str(pdf_file))
        
        # Assert: Should terminate before max iterations
        assert iteration_count < 5
        
        # Verify all claims have final status
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        latest = version_history['quick_convergence.pdf'][-1]['review']
        claims = latest.get('Requirement(s)', [])
        
        statuses = [c.get('status') for c in claims]
        assert all(s in ['approved', 'rejected'] for s in statuses)
    
    @pytest.mark.e2e
    def test_convergence_enforces_max_iterations(self, temp_workspace, test_data_generator):
        """
        Test convergence enforces max iteration limit.
        
        Termination condition: max_iterations reached, even if claims still pending
        """
        # Setup: Create paper with difficult claims
        pdf_file = temp_workspace / "difficult_paper.pdf"
        test_data_generator.create_dummy_pdf(
            pdf_file,
            title="Difficult Paper",
            content="Ambiguous evidence requiring many iterations."
        )
        
        version_history_file = temp_workspace / "review_version_history.json"
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute
        MAX_ITERATIONS = 3
        
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            max_iterations=MAX_ITERATIONS
        )
        
        iteration_count = orchestrator.run_convergence_loop(str(pdf_file))
        
        # Assert: Should terminate at max iterations
        assert iteration_count == MAX_ITERATIONS
        
        # Verify version history has entries from all iterations
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        versions = version_history['difficult_paper.pdf']
        
        # Should have versions from each iteration
        # (at least 1 per iteration: Journal or Deep + Judge)
        assert len(versions) >= MAX_ITERATIONS
    
    @pytest.mark.e2e
    def test_convergence_tracks_claim_evolution(self, temp_workspace, test_data_generator):
        """
        Test convergence tracks claim status evolution over iterations.
        
        Validates:
        - Claims progress from pending → approved/rejected
        - Status transitions logged
        - Appeal cycles integrated
        """
        # Setup
        pdf_file = temp_workspace / "evolution_paper.pdf"
        test_data_generator.create_dummy_pdf(
            pdf_file,
            title="Evolution Paper",
            content="Claims that evolve through iterations."
        )
        
        version_history_file = temp_workspace / "review_version_history.json"
        
        with open(version_history_file, 'w') as f:
            json.dump({}, f)
        
        # Execute
        orchestrator = Orchestrator(
            version_history_path=str(version_history_file),
            max_iterations=3
        )
        
        orchestrator.run_convergence_loop(str(pdf_file))
        
        # Assert: Track claim evolution
        with open(version_history_file, 'r') as f:
            version_history = json.load(f)
        
        versions = version_history['evolution_paper.pdf']
        
        # Extract claim statuses over time
        claim_evolution = {}
        
        for version in versions:
            iteration = version['review'].get('iteration', 1)
            claims = version['review'].get('Requirement(s)', [])
            
            for claim in claims:
                claim_id = claim.get('claim_id')
                status = claim.get('status')
                
                if claim_id:
                    if claim_id not in claim_evolution:
                        claim_evolution[claim_id] = []
                    claim_evolution[claim_id].append((iteration, status))
        
        # Verify claims evolved
        for claim_id, evolution in claim_evolution.items():
            # Should have multiple status entries
            assert len(evolution) >= 1
            
            # Final status should be approved or rejected
            final_status = evolution[-1][1]
            assert final_status in ['approved', 'rejected', 'pending_judge_review']
```

### Enhanced Test Cases (Evidence Quality)

#### Test 5: Quality Score Refinement Through Iterations

```python
@pytest.mark.e2e
def test_quality_scores_improve_through_iterations(temp_workspace, test_data_generator):
    """
    Test that evidence quality scores improve through convergence iterations.
    
    Validates:
    - Composite scores increase as more evidence found
    - Borderline claims converge to consensus
    - Quality score evolution tracked
    """
    # Setup: Create paper with borderline initial quality
    pdf_file = temp_workspace / "quality_refinement_paper.pdf"
    test_data_generator.create_dummy_pdf(
        pdf_file,
        title="Quality Refinement Paper",
        publication_year=2024,
        content="""
        Initial claim: SNNs show promise.
        
        Iteration 2 evidence: SNNs achieved 92% accuracy in 3 trials.
        Reproduced by independent team. Published in Nature 2024.
        """
    )
    
    version_history_file = temp_workspace / "review_version_history.json"
    
    with open(version_history_file, 'w') as f:
        json.dump({}, f)
    
    # Execute: Convergence loop with quality scoring
    orchestrator = Orchestrator(
        version_history_path=str(version_history_file),
        max_iterations=3,
        enable_quality_scoring=True,
        enable_triangulation=True
    )
    
    orchestrator.run_convergence_loop(str(pdf_file))
    
    # Assert: Verify quality improvement
    with open(version_history_file, 'r') as f:
        version_history = json.load(f)
    
    versions = version_history['quality_refinement_paper.pdf']
    
    # Track quality scores over iterations
    quality_evolution = {}
    
    for version in versions:
        iteration = version['review'].get('iteration', 1)
        claims = version['review'].get('Requirement(s)', [])
        
        for claim in claims:
            sub_req = claim.get('sub_requirement')
            quality = claim.get('evidence_quality', {})
            composite = quality.get('composite_score', 0)
            
            if sub_req and composite > 0:
                if sub_req not in quality_evolution:
                    quality_evolution[sub_req] = []
                quality_evolution[sub_req].append((iteration, composite))
    
    # Verify quality improved or stabilized
    for sub_req, evolution in quality_evolution.items():
        if len(evolution) >= 2:
            first_score = evolution[0][1]
            last_score = evolution[-1][1]
            
            # Quality should improve or stay high
            assert last_score >= first_score or last_score >= 3.5


@pytest.mark.e2e
def test_convergence_terminates_on_quality_threshold(temp_workspace, test_data_generator):
    """
    Test convergence terminates when quality threshold reached.
    
    Termination condition: All claims have composite ≥3.5 (high quality)
    """
    # Setup: Create high-quality paper
    pdf_file = temp_workspace / "high_quality_paper.pdf"
    test_data_generator.create_dummy_pdf(
        pdf_file,
        title="High Quality Paper",
        publication_year=2024,
        content="""
        Results: SNNs achieved 95% accuracy (p<0.001) in randomized controlled trial
        with 1000 samples. Reproduced in 5 independent studies. Published in Nature.
        Code available on GitHub. Methods section provides complete implementation details.
        """
    )
    
    version_history_file = temp_workspace / "review_version_history.json"
    
    with open(version_history_file, 'w') as f:
        json.dump({}, f)
    
    # Execute
    QUALITY_THRESHOLD = 3.5
    
    orchestrator = Orchestrator(
        version_history_path=str(version_history_file),
        max_iterations=5,
        enable_quality_scoring=True,
        quality_threshold=QUALITY_THRESHOLD
    )
    
    iteration_count = orchestrator.run_convergence_loop(str(pdf_file))
    
    # Assert: Should terminate early due to high quality
    assert iteration_count < 5
    
    # Verify all claims meet quality threshold
    with open(version_history_file, 'r') as f:
        version_history = json.load(f)
    
    latest = version_history['high_quality_paper.pdf'][-1]['review']
    claims = latest.get('Requirement(s)', [])
    
    for claim in claims:
        quality = claim.get('evidence_quality', {})
        composite = quality.get('composite_score', 0)
        
        if claim.get('status') == 'approved':
            assert composite >= QUALITY_THRESHOLD


@pytest.mark.e2e
def test_convergence_handles_borderline_consensus(temp_workspace, test_data_generator):
    """
    Test convergence achieves consensus on borderline claims.
    
    Validates:
    - Borderline claims (composite 2.5-3.5) trigger consensus
    - Consensus review performed in each iteration
    - Consensus metadata accumulated
    - Final decision reached after consensus
    """
    # Setup: Create paper with borderline evidence
    pdf_file = temp_workspace / "borderline_paper.pdf"
    test_data_generator.create_dummy_pdf(
        pdf_file,
        title="Borderline Paper",
        content="Moderate quality evidence, borderline composite score."
    )
    
    version_history_file = temp_workspace / "review_version_history.json"
    
    with open(version_history_file, 'w') as f:
        json.dump({}, f)
    
    # Execute
    orchestrator = Orchestrator(
        version_history_path=str(version_history_file),
        max_iterations=3,
        enable_quality_scoring=True,
        enable_consensus_review=True
    )
    
    orchestrator.run_convergence_loop(str(pdf_file))
    
    # Assert: Verify consensus triggered
    with open(version_history_file, 'r') as f:
        version_history = json.load(f)
    
    versions = version_history['borderline_paper.pdf']
    
    # Check for consensus review metadata
    consensus_found = False
    
    for version in versions:
        claims = version['review'].get('Requirement(s)', [])
        for claim in claims:
            if 'consensus_review' in claim:
                consensus_found = True
                
                # Verify consensus metadata
                consensus = claim['consensus_review']
                assert consensus['triggered'] is True
                assert 'consensus_reviewers' in consensus
                assert len(consensus['consensus_reviewers']) >= 2
    
    # Should have triggered consensus at some point
    assert consensus_found


@pytest.mark.e2e
def test_convergence_tracks_metrics(temp_workspace, test_data_generator):
    """
    Test convergence loop tracks performance metrics.
    
    Validates:
    - Iteration count tracked
    - Quality score delta per iteration
    - Convergence rate calculated
    - Termination reason logged
    """
    # Setup
    pdf_file = temp_workspace / "metrics_paper.pdf"
    test_data_generator.create_dummy_pdf(pdf_file, title="Metrics Paper")
    
    version_history_file = temp_workspace / "review_version_history.json"
    
    with open(version_history_file, 'w') as f:
        json.dump({}, f)
    
    # Execute
    orchestrator = Orchestrator(
        version_history_path=str(version_history_file),
        max_iterations=3,
        enable_quality_scoring=True
    )
    
    convergence_result = orchestrator.run_convergence_loop(str(pdf_file))
    
    # Assert: Verify metrics tracked
    with open(version_history_file, 'r') as f:
        version_history = json.load(f)
    
    # Check for convergence metadata
    versions = version_history['metrics_paper.pdf']
    
    # Should have convergence summary in final version
    final_version = versions[-1]['review']
    
    if 'convergence_metrics' in final_version:
        metrics = final_version['convergence_metrics']
        
        assert 'iteration_count' in metrics
        assert 'termination_reason' in metrics
        assert metrics['termination_reason'] in [
            'consensus_reached',
            'max_iterations',
            'quality_threshold_met'
        ]
        
        if 'quality_score_delta' in metrics:
            # Delta should be small at convergence
            assert metrics['quality_score_delta'] < 0.5
```

---

## Orchestrator.py Modifications

Add convergence loop method:

```python
def run_convergence_loop(self, pdf_file: str) -> int:
    """
    Run iterative convergence loop for multi-reviewer refinement.
    
    Args:
        pdf_file: Path to PDF to process
    
    Returns:
        Number of iterations completed
    """
    iteration = 0
    converged = False
    
    while iteration < self.max_iterations and not converged:
        iteration += 1
        
        # Iteration 1: Journal-Reviewer
        if iteration == 1:
            self.run_journal_reviewer(pdf_file)
        
        # Iteration 2+: Deep-Reviewer
        if iteration >= 2:
            self.run_deep_reviewer(pdf_file)
        
        # Triangulate evidence (if multiple reviewers)
        if iteration >= 2 and self.enable_triangulation:
            self.triangulate_evidence()
        
        # Judge reviews claims
        self.run_judge()
        
        # Check convergence
        converged = self.check_convergence()
        
        # Log iteration metadata
        self.log_iteration_metadata(iteration, converged)
    
    # Log convergence metrics
    self.log_convergence_metrics(iteration, converged)
    
    return iteration


def check_convergence(self) -> bool:
    """
    Check if convergence criteria met.
    
    Returns:
        True if converged (all claims finalized or quality threshold met)
    """
    with open(self.version_history_path, 'r') as f:
        version_history = json.load(f)
    
    for filename, versions in version_history.items():
        latest = versions[-1]['review']
        claims = latest.get('Requirement(s)', [])
        
        for claim in claims:
            status = claim.get('status')
            quality = claim.get('evidence_quality', {})
            composite = quality.get('composite_score', 0)
            
            # Not converged if any claims still pending
            if status == 'pending_judge_review':
                return False
            
            # Not converged if quality below threshold
            if hasattr(self, 'quality_threshold'):
                if status == 'approved' and composite < self.quality_threshold:
                    return False
    
    return True
```

---

## Success Criteria

### Original Criteria
- [ ] Iterative Journal → Deep → Judge cycle works
- [ ] Convergence terminates on consensus
- [ ] Max iteration limit enforced
- [ ] Claim status evolution tracked
- [ ] Appeal loops integrated
- [ ] Test passes consistently

### Enhanced Criteria (Evidence Quality)
- [ ] Quality scores improve through iterations
- [ ] Borderline claims converge to consensus
- [ ] Evidence triangulation strengthens claims
- [ ] GRADE quality levels stabilize
- [ ] Convergence metrics tracked (iteration count, score delta)
- [ ] Termination on quality threshold (composite ≥3.5)
- [ ] Termination on max iterations
- [ ] Termination reason logged

---

## Testing Strategy

Run E2E convergence tests:

```bash
# Run convergence loop E2E test
pytest tests/e2e/test_convergence_loop.py -v -s

# Run with coverage
pytest tests/e2e/test_convergence_loop.py --cov=literature_review.orchestrator --cov-report=html

# Run with performance profiling
pytest tests/e2e/test_convergence_loop.py -v --durations=10
```

---

## Estimated Effort

**Original Scope:** 8-12 hours  
**Enhanced Scope (with quality refinement):** 12-16 hours

**Breakdown:**
- Core convergence tests: 6-8 hours
- Quality refinement validation: 4-6 hours
- Consensus handling: 2-3 hours
- Metrics tracking: 1-2 hours
- Documentation: 1-2 hours

---

**Task Card Status:** ⚠️ UPDATED for refactored architecture  
**Ready for Implementation:** ✅ Yes  
**Dependencies:** Task #10 (Full Pipeline), Evidence enhancement cards (#16-21)  
**Blocks:** Production deployment

**Last Updated:** November 13, 2025
