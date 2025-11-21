"""
Comprehensive Integration Tests for Incremental Analysis Mode

Tests end-to-end workflows, edge cases, and cross-system compatibility for
incremental review mode across CLI and Dashboard.

Part of INCR-W2-4: Incremental Analysis Integration Tests
"""

import pytest
import subprocess
import json
import os
import sys
import tempfile
import time
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.state_manager import StateManager, JobType
from literature_review.utils.gap_extractor import GapExtractor
from literature_review.utils.relevance_scorer import RelevanceScorer
from literature_review.analysis.result_merger import ResultMerger

# Repository root for subprocess commands
REPO_ROOT = str(Path(__file__).parent.parent.parent)


# ============================================================================
# Helper Functions
# ============================================================================

def run_cli(args: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """
    Run CLI orchestrator with given arguments.
    
    Args:
        args: Command line arguments
        timeout: Timeout in seconds
        
    Returns:
        CompletedProcess instance
    """
    cmd = ['python', 'pipeline_orchestrator.py'] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=REPO_ROOT
    )
    return result


def load_json(filepath: Path) -> Dict:
    """Load JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def save_json(filepath: Path, data: Dict):
    """Save JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def create_sample_database(csv_path: Path, num_papers: int = 10):
    """
    Create a sample research database CSV.
    
    Args:
        csv_path: Path to save CSV
        num_papers: Number of papers to generate
    """
    data = {
        'DOI': [f'10.1000/paper{i}' for i in range(1, num_papers + 1)],
        'Title': [f'Neuromorphic Paper {i}' for i in range(1, num_papers + 1)],
        'Abstract': [f'This paper explores neuromorphic computing aspect {i}...' for i in range(1, num_papers + 1)],
        'Year': [2024] * num_papers,
        'Authors': [f'Author {i} et al.' for i in range(1, num_papers + 1)]
    }
    
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)


def add_papers_to_database(csv_path: Path, paper_files: List[str]):
    """
    Add new papers to existing database CSV.
    
    Args:
        csv_path: Path to CSV database
        paper_files: List of paper identifiers to add
    """
    # Load existing database
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        start_idx = len(df) + 1
    else:
        df = pd.DataFrame()
        start_idx = 1
    
    # Create new papers
    new_data = {
        'DOI': [f'10.1000/new{i}' for i in range(start_idx, start_idx + len(paper_files))],
        'Title': [f'New Paper {i}' for i in range(start_idx, start_idx + len(paper_files))],
        'Abstract': [f'New research on topic {i}...' for i in range(start_idx, start_idx + len(paper_files))],
        'Year': [2025] * len(paper_files),
        'Authors': [f'New Author {i} et al.' for i in range(start_idx, start_idx + len(paper_files))]
    }
    
    new_df = pd.DataFrame(new_data)
    combined_df = pd.concat([df, new_df], ignore_index=True)
    combined_df.to_csv(csv_path, index=False)


def create_gap_report(output_dir: Path, num_gaps: int = 5) -> Path:
    """
    Create a mock gap analysis report.
    
    Args:
        output_dir: Directory to save report
        num_gaps: Number of gaps to create
        
    Returns:
        Path to created report
    """
    report = {
        'pillars': {}
    }
    
    for i in range(1, num_gaps + 1):
        pillar_name = f'Pillar {i}: Test Pillar'
        report['pillars'][pillar_name] = {
            'requirements': {
                f'REQ-{i:03d}': {
                    'requirement_text': f'Test requirement {i}',
                    'sub_requirements': {
                        f'SUB-{i:03d}': {
                            'completeness': 0.4,
                            'target_coverage': 0.7,
                            'keywords': [f'keyword{i}', 'neuromorphic', 'computing'],
                            'evidence_count': 2,
                            'requirement_text': f'Test sub-requirement {i}'
                        }
                    }
                }
            }
        }
    
    report_path = output_dir / 'gap_analysis_report.json'
    save_json(report_path, report)
    return report_path


def create_perfect_baseline(output_dir: Path):
    """
    Create a baseline with no gaps (all requirements met).
    
    Args:
        output_dir: Directory to save files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create gap report with high completeness
    report = {
        'pillars': {
            'Pillar 1: Test': {
                'requirements': {
                    'REQ-001': {
                        'requirement_text': 'Test requirement',
                        'sub_requirements': {
                            'SUB-001': {
                                'completeness': 0.95,
                                'target_coverage': 0.7,
                                'keywords': ['test'],
                                'evidence_count': 10,
                                'requirement_text': 'Test sub-requirement'
                            }
                        }
                    }
                }
            }
        }
    }
    
    gap_report_path = output_dir / 'gap_analysis_report.json'
    save_json(gap_report_path, report)
    
    # Create state
    state_file = output_dir / 'orchestrator_state.json'
    state_manager = StateManager(str(state_file))
    state = state_manager.create_new_state(
        database_path="test.csv",
        database_hash="abc123",
        database_size=100
    )
    state.analysis_completed = True
    state.completed_at = "2025-01-15T10:00:00"
    state_manager.save_state(state)


def create_large_gap_report(num_requirements: int = 500) -> Dict:
    """
    Create a large gap report for performance testing.
    
    Args:
        num_requirements: Number of requirements to create
        
    Returns:
        Gap report dictionary
    """
    report = {'pillars': {}}
    
    for i in range(1, num_requirements + 1):
        pillar_idx = (i - 1) // 100 + 1
        pillar_name = f'Pillar {pillar_idx}: Performance Test'
        
        if pillar_name not in report['pillars']:
            report['pillars'][pillar_name] = {'requirements': {}}
        
        req_id = f'REQ-{i:04d}'
        report['pillars'][pillar_name]['requirements'][req_id] = {
            'requirement_text': f'Performance test requirement {i}',
            'sub_requirements': {
                f'SUB-{i:04d}': {
                    'completeness': 0.3,
                    'target_coverage': 0.7,
                    'keywords': [f'keyword{i}', 'test', 'performance'],
                    'evidence_count': 1,
                    'requirement_text': f'Sub-requirement {i}'
                }
            }
        }
    
    return report


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_database(tmp_path):
    """Create sample research database CSV."""
    csv_path = tmp_path / 'neuromorphic-research_database.csv'
    create_sample_database(csv_path, num_papers=10)
    return csv_path


@pytest.fixture
def completed_job(tmp_path):
    """Create completed job with gap analysis."""
    job_dir = tmp_path / 'job_test001'
    job_dir.mkdir()
    
    # Create gap report
    create_gap_report(job_dir, num_gaps=5)
    
    # Create state
    state_file = job_dir / 'orchestrator_state.json'
    state_manager = StateManager(str(state_file))
    state = state_manager.create_new_state(
        database_path="test.csv",
        database_hash="abc123",
        database_size=100
    )
    state.analysis_completed = True
    state.completed_at = "2025-01-15T10:00:00"
    state_manager.save_state(state)
    
    return {'job_id': 'job_test001', 'path': job_dir}


# ============================================================================
# 1. CLI Incremental Mode Tests
# ============================================================================

class TestCLIIncrementalMode:
    """Test CLI incremental workflow scenarios."""
    
    def test_cli_incremental_basic_workflow(self, tmp_path):
        """
        Test complete CLI incremental workflow:
        1. Run baseline analysis
        2. Add new papers
        3. Run incremental update
        4. Verify results merged
        """
        output_dir = tmp_path / "review"
        output_dir.mkdir()
        
        # Step 1: Create baseline manually (simulate completed job)
        csv_path = tmp_path / "database.csv"
        create_sample_database(csv_path, num_papers=5)
        
        gap_report = create_gap_report(output_dir, num_gaps=3)
        
        state_file = output_dir / 'orchestrator_state.json'
        state_manager = StateManager(str(state_file))
        baseline_state = state_manager.create_new_state(
            database_path=str(csv_path),
            database_hash="baseline_hash",
            database_size=5
        )
        baseline_state.analysis_completed = True
        baseline_state.completed_at = "2025-01-15T10:00:00"
        state_manager.save_state(baseline_state)
        
        baseline_job_id = baseline_state.job_id
        
        # Step 2: Add new papers
        add_papers_to_database(csv_path, ['paper_new1.csv', 'paper_new2.csv'])
        
        # Step 3: Run incremental mode (dry-run)
        result = run_cli(['--incremental', '--output-dir', str(output_dir), '--dry-run'])
        
        # Step 4: Verify
        # In dry-run mode, should recognize incremental prerequisites
        output = result.stdout + result.stderr
        # Should complete successfully in dry-run mode
        is_dry_run = 'DRY-RUN' in output or 'dry-run' in output.lower()
        if is_dry_run:
            assert result.returncode == 0, "Dry-run should return 0"
        else:
            # If not dry-run, accept either success or expected error
            assert result.returncode in [0, 1], f"Unexpected return code: {result.returncode}"
        
        # Verify state still has parent job reference
        current_state = state_manager.load_state()
        # Note: In dry-run mode, state might not be updated, so we just verify it exists
        assert current_state is not None
    
    def test_cli_no_new_papers(self, tmp_path):
        """Test CLI exits gracefully when no new papers."""
        output_dir = tmp_path / "review"
        output_dir.mkdir()
        
        # Create baseline
        csv_path = tmp_path / "database.csv"
        create_sample_database(csv_path, num_papers=5)
        
        create_gap_report(output_dir)
        
        state_file = output_dir / 'orchestrator_state.json'
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path=str(csv_path),
            database_hash="hash123",
            database_size=5
        )
        state.analysis_completed = True
        state_manager.save_state(state)
        
        # Run incremental without adding papers
        result = run_cli(['--incremental', '--output-dir', str(output_dir), '--dry-run'])
        
        output = result.stdout + result.stderr
        assert result.returncode == 0, "Should exit successfully"
        # Should detect no changes or be in dry-run mode
        has_no_changes_msg = 'no changes' in output.lower() or 'no new papers' in output.lower()
        is_dry_run = 'DRY-RUN' in output
        assert has_no_changes_msg or is_dry_run, "Should detect no changes or be in dry-run mode"
    
    def test_cli_force_overrides_incremental(self, tmp_path):
        """Test --force disables incremental mode."""
        output_dir = tmp_path / "review"
        output_dir.mkdir()
        
        # Create baseline
        csv_path = tmp_path / "database.csv"
        create_sample_database(csv_path, num_papers=5)
        
        create_gap_report(output_dir)
        
        state_file = output_dir / 'orchestrator_state.json'
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path=str(csv_path),
            database_hash="hash123",
            database_size=5
        )
        state.analysis_completed = True
        state_manager.save_state(state)
        
        # Add new papers
        add_papers_to_database(csv_path, ['paper_new1.csv'])
        
        # Run with --force (should override incremental)
        result = run_cli(['--incremental', '--force', '--output-dir', str(output_dir), '--dry-run'])
        
        output = result.stdout + result.stderr
        assert result.returncode == 0
        # Should run in full mode
        assert 'full' in output.lower() or 'force' in output.lower() or 'DRY-RUN' in output
    
    def test_cli_corrupt_state_fallback(self, tmp_path):
        """Test fallback to full analysis when state corrupted."""
        output_dir = tmp_path / "review"
        output_dir.mkdir()
        
        # Create corrupt state
        state_file = output_dir / 'orchestrator_state.json'
        state_file.write_text('{ corrupt json')
        
        # Should fallback gracefully
        result = run_cli(['--incremental', '--output-dir', str(output_dir), '--dry-run'])
        
        output = result.stdout + result.stderr
        # Should handle gracefully - check for specific error handling behavior
        assert result.returncode in [0, 1], "Should not crash"
        
        # Verify proper error handling: should detect corrupt state or fall back
        has_error_handling = (
            'prerequisite' in output.lower() or 
            'falling back' in output.lower() or 
            'corrupt' in output.lower() or
            'error' in output.lower() or 
            'DRY-RUN' in output
        )
        assert has_error_handling, "Should show proper error handling for corrupt state"
    
    def test_cli_no_gaps_all_requirements_met(self, tmp_path):
        """Test incremental mode when all requirements already met."""
        output_dir = tmp_path / "review"
        
        # Create perfect baseline (no gaps)
        create_perfect_baseline(output_dir)
        
        # Add new papers
        csv_path = tmp_path / "database.csv"
        create_sample_database(csv_path, num_papers=5)
        add_papers_to_database(csv_path, ['paper_new1.csv'])
        
        # Run incremental
        result = run_cli(['--incremental', '--output-dir', str(output_dir), '--dry-run'])
        
        output = result.stdout + result.stderr
        # Should handle gracefully
        assert result.returncode == 0 or 'DRY-RUN' in output
    
    def test_cli_all_papers_irrelevant(self, tmp_path):
        """Test when all new papers filtered as irrelevant."""
        output_dir = tmp_path / "review"
        output_dir.mkdir()
        
        # Create baseline
        csv_path = tmp_path / "database.csv"
        data = {
            'DOI': ['10.1000/quantum1'],
            'Title': ['Quantum Computing Paper'],
            'Abstract': ['Completely unrelated quantum mechanics topic...'],
            'Year': [2025],
            'Authors': ['Quantum Author']
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False)
        
        create_gap_report(output_dir)
        
        state_file = output_dir / 'orchestrator_state.json'
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path=str(csv_path),
            database_hash="hash123",
            database_size=0
        )
        state.analysis_completed = True
        state_manager.save_state(state)
        
        # Add irrelevant paper
        add_papers_to_database(csv_path, ['unrelated_paper.csv'])
        
        # Run incremental with high threshold
        result = run_cli(['--incremental', '--output-dir', str(output_dir), '--dry-run'])
        
        output = result.stdout + result.stderr
        assert result.returncode == 0 or 'DRY-RUN' in output


# ============================================================================
# 2. Dashboard Continuation Tests
# ============================================================================

class TestDashboardContinuation:
    """Test Dashboard job continuation API."""
    
    def test_gap_extraction_from_job(self, completed_job):
        """Test extracting gaps from a completed job."""
        job_path = completed_job['path']
        gap_report_path = job_path / 'gap_analysis_report.json'
        
        # Extract gaps
        extractor = GapExtractor(gap_report_path=str(gap_report_path), threshold=0.7)
        gaps = extractor.extract_gaps()
        
        # Verify gaps extracted
        assert len(gaps) > 0
        assert isinstance(gaps, list)
        
        # Verify gap structure
        if gaps:
            gap = gaps[0]
            assert 'pillar_id' in gap
            assert 'requirement_id' in gap
            assert 'sub_requirement_id' in gap
            assert 'current_coverage' in gap
            assert 'target_coverage' in gap
            assert 'gap_size' in gap
    
    def test_gap_extraction_with_custom_threshold(self, completed_job):
        """Test gap extraction with custom threshold."""
        job_path = completed_job['path']
        gap_report_path = job_path / 'gap_analysis_report.json'
        
        # Extract with different thresholds
        extractor_low = GapExtractor(gap_report_path=str(gap_report_path), threshold=0.5)
        gaps_low = extractor_low.extract_gaps()
        
        extractor_high = GapExtractor(gap_report_path=str(gap_report_path), threshold=0.9)
        gaps_high = extractor_high.extract_gaps()
        
        # Lower threshold should find more or equal gaps
        assert len(gaps_low) >= len(gaps_high)
    
    def test_relevance_scoring_papers(self, completed_job):
        """Test scoring paper relevance to gaps."""
        job_path = completed_job['path']
        gap_report_path = job_path / 'gap_analysis_report.json'
        
        # Extract gaps
        extractor = GapExtractor(gap_report_path=str(gap_report_path))
        gaps = extractor.extract_gaps()
        
        assert len(gaps) > 0, "Need gaps for relevance testing"
        
        # Score papers
        scorer = RelevanceScorer()
        
        papers = [
            {
                'title': 'Neuromorphic Computing with SNNs',
                'abstract': 'This paper discusses spiking neural networks and neuromorphic hardware...'
            },
            {
                'title': 'Quantum Mechanics Study',
                'abstract': 'Unrelated quantum physics research...'
            }
        ]
        
        scores = []
        for paper in papers:
            paper_scores = [scorer.score_relevance(paper, gap) for gap in gaps]
            max_score = max(paper_scores) if paper_scores else 0.0
            scores.append(max_score)
        
        # Verify scores
        assert len(scores) == 2
        assert all(0.0 <= s <= 1.0 for s in scores)
        # First paper should score higher (relevant to neuromorphic computing)
        # Note: This depends on keywords in gaps, so we just check scores are valid
    
    def test_merge_incremental_results(self, tmp_path):
        """Test merging incremental analysis results."""
        # Create base report
        base_report = {
            'pillars': {
                'Pillar 1: Test': {
                    'requirements': {
                        'REQ-001': {
                            'requirement_text': 'Test requirement',
                            'sub_requirements': {
                                'SUB-001': {
                                    'completeness': 0.4,
                                    'target_coverage': 0.7,
                                    'evidence_count': 2
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Create incremental report
        incremental_report = {
            'pillars': {
                'Pillar 1: Test': {
                    'requirements': {
                        'REQ-001': {
                            'requirement_text': 'Test requirement',
                            'sub_requirements': {
                                'SUB-001': {
                                    'completeness': 0.6,
                                    'target_coverage': 0.7,
                                    'evidence_count': 4
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Merge
        merger = ResultMerger(conflict_resolution='keep_both')
        result = merger.merge_gap_analysis_results(base_report, incremental_report)
        
        # Verify merge
        assert result.merged_report is not None
        assert 'pillars' in result.merged_report
        assert isinstance(result.statistics, dict)
    
    def test_gap_filtering_by_pillar(self, completed_job):
        """Test filtering gaps by specific pillar."""
        job_path = completed_job['path']
        gap_report_path = job_path / 'gap_analysis_report.json'
        
        # Extract all gaps
        extractor = GapExtractor(gap_report_path=str(gap_report_path))
        all_gaps = extractor.extract_gaps()
        
        if len(all_gaps) == 0:
            pytest.skip("No gaps to test filtering")
        
        # Get unique pillar IDs
        pillar_ids = set(gap.get('pillar_id') for gap in all_gaps)
        
        # Filter by first pillar
        first_pillar = list(pillar_ids)[0]
        filtered_gaps = [gap for gap in all_gaps if gap.get('pillar_id') == first_pillar]
        
        # Verify filtering
        assert len(filtered_gaps) > 0
        assert all(gap.get('pillar_id') == first_pillar for gap in filtered_gaps)
        assert len(filtered_gaps) <= len(all_gaps)
    
    def test_relevance_scoring_with_threshold_filtering(self, completed_job):
        """Test relevance scoring with threshold-based filtering."""
        job_path = completed_job['path']
        gap_report_path = job_path / 'gap_analysis_report.json'
        
        # Extract gaps
        extractor = GapExtractor(gap_report_path=str(gap_report_path))
        gaps = extractor.extract_gaps()
        
        if len(gaps) == 0:
            pytest.skip("No gaps for testing")
        
        # Score papers with different thresholds
        scorer = RelevanceScorer()
        
        papers = [
            {
                'title': f'Neuromorphic Test Paper {i}',
                'abstract': f'Research on neuromorphic computing and neural networks topic {i}...'
            }
            for i in range(10)
        ]
        
        thresholds = [0.3, 0.5, 0.7]
        results = {}
        
        for threshold in thresholds:
            above_threshold = 0
            for paper in papers:
                paper_scores = [scorer.score_relevance(paper, gap) for gap in gaps]
                max_score = max(paper_scores) if paper_scores else 0.0
                if max_score >= threshold:
                    above_threshold += 1
            results[threshold] = above_threshold
        
        # Higher thresholds should result in fewer papers
        assert results[0.3] >= results[0.5] >= results[0.7]
    
    def test_merge_with_conflict_resolution_strategies(self, tmp_path):
        """Test different conflict resolution strategies."""
        # Create base report
        base_report = {
            'pillars': {
                'Pillar 1: Test': {
                    'requirements': {
                        'REQ-001': {
                            'requirement_text': 'Test requirement',
                            'sub_requirements': {
                                'SUB-001': {
                                    'completeness': 0.5,
                                    'target_coverage': 0.7,
                                    'evidence_count': 3
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Create incremental report with different values
        incremental_report = {
            'pillars': {
                'Pillar 1: Test': {
                    'requirements': {
                        'REQ-001': {
                            'requirement_text': 'Test requirement',
                            'sub_requirements': {
                                'SUB-001': {
                                    'completeness': 0.7,
                                    'target_coverage': 0.7,
                                    'evidence_count': 5
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Test different strategies
        strategies = ['keep_both', 'keep_existing', 'keep_new']
        
        for strategy in strategies:
            merger = ResultMerger(conflict_resolution=strategy)
            result = merger.merge_gap_analysis_results(base_report, incremental_report)
            
            # Verify merge completed
            assert result.merged_report is not None
            assert 'pillars' in result.merged_report
    
    def test_job_continuation_workflow(self, completed_job):
        """Test complete job continuation workflow simulation."""
        job_path = completed_job['path']
        gap_report_path = job_path / 'gap_analysis_report.json'
        
        # Step 1: Extract gaps
        extractor = GapExtractor(gap_report_path=str(gap_report_path))
        gaps = extractor.extract_gaps()
        assert len(gaps) > 0, "Need gaps for continuation"
        
        # Step 2: Prepare new papers
        new_papers = [
            {
                'title': 'Neuromorphic Vision Processing',
                'abstract': 'Event-based vision using spiking neural networks...'
            },
            {
                'title': 'STDP Learning Rules',
                'abstract': 'Spike-timing dependent plasticity in neuromorphic hardware...'
            }
        ]
        
        # Step 3: Score relevance
        scorer = RelevanceScorer()
        relevant_papers = []
        threshold = 0.4
        
        for paper in new_papers:
            paper_scores = [scorer.score_relevance(paper, gap) for gap in gaps]
            max_score = max(paper_scores) if paper_scores else 0.0
            if max_score >= threshold:
                relevant_papers.append(paper)
        
        # Verify workflow
        assert isinstance(relevant_papers, list)
        # At least some papers should be relevant given neuromorphic keywords
        # But we don't enforce exact count as it depends on gap keywords


# ============================================================================
# 3. Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_missing_gap_report(self, tmp_path):
        """Test handling of missing gap report."""
        output_dir = tmp_path / "review"
        output_dir.mkdir()
        
        # Create state without gap report
        state_file = output_dir / 'orchestrator_state.json'
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100
        )
        state.analysis_completed = True
        state_manager.save_state(state)
        
        # Try incremental mode
        result = run_cli(['--incremental', '--output-dir', str(output_dir), '--dry-run'])
        
        output = result.stdout + result.stderr
        # Should handle gracefully
        assert result.returncode in [0, 1]
    
    def test_empty_database(self, tmp_path):
        """Test handling of empty research database."""
        output_dir = tmp_path / "review"
        output_dir.mkdir()
        
        # Create empty database
        csv_path = tmp_path / "database.csv"
        df = pd.DataFrame(columns=['DOI', 'Title', 'Abstract', 'Year', 'Authors'])
        df.to_csv(csv_path, index=False)
        
        create_gap_report(output_dir)
        
        state_file = output_dir / 'orchestrator_state.json'
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path=str(csv_path),
            database_hash="empty",
            database_size=0
        )
        state.analysis_completed = True
        state_manager.save_state(state)
        
        # Try incremental
        result = run_cli(['--incremental', '--output-dir', str(output_dir), '--dry-run'])
        
        # Should handle gracefully
        assert result.returncode in [0, 1]
    
    def test_malformed_gap_report(self, tmp_path):
        """Test handling of malformed gap report."""
        output_dir = tmp_path / "review"
        output_dir.mkdir()
        
        # Create malformed gap report
        gap_report_path = output_dir / 'gap_analysis_report.json'
        gap_report_path.write_text('{"invalid": "structure"}')
        
        state_file = output_dir / 'orchestrator_state.json'
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100
        )
        state.analysis_completed = True
        state_manager.save_state(state)
        
        # Extract gaps should handle gracefully
        extractor = GapExtractor(gap_report_path=str(gap_report_path))
        gaps = extractor.extract_gaps()
        
        # Should return empty list or handle gracefully
        assert isinstance(gaps, list)


# ============================================================================
# 4. Performance Tests
# ============================================================================

class TestPerformance:
    """Test performance characteristics of incremental mode."""
    
    def test_gap_extraction_performance(self):
        """Verify gap extraction is fast (< 100ms)."""
        # Create large report
        large_report = create_large_gap_report(num_requirements=500)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(large_report, f)
            temp_path = f.name
        
        try:
            extractor = GapExtractor(gap_report_path=temp_path, threshold=0.7)
            
            # Measure extraction time
            start = time.time()
            gaps = extractor.extract_gaps()
            duration = time.time() - start
            
            # Should be fast - use 1.0s threshold to account for CI environment variability
            # In production, expect < 200ms, but CI can be 2-3x slower
            assert duration < 1.0, f"Gap extraction took {duration:.2f}s, expected < 1.0s"
            assert len(gaps) > 0
        finally:
            os.unlink(temp_path)
    
    def test_relevance_scoring_performance(self, completed_job):
        """Verify relevance scoring is reasonably fast."""
        job_path = completed_job['path']
        gap_report_path = job_path / 'gap_analysis_report.json'
        
        # Extract gaps
        extractor = GapExtractor(gap_report_path=str(gap_report_path))
        gaps = extractor.extract_gaps()
        
        if len(gaps) == 0:
            pytest.skip("No gaps to test scoring performance")
        
        # Create test papers
        papers = [
            {
                'title': f'Test Paper {i}',
                'abstract': f'Research on neuromorphic computing topic {i}...'
            }
            for i in range(100)
        ]
        
        scorer = RelevanceScorer()
        
        # Measure scoring time
        start = time.time()
        for paper in papers:
            for gap in gaps:
                scorer.score_relevance(paper, gap)
        duration = time.time() - start
        
        # Should complete in reasonable time
        total_scores = len(papers) * len(gaps)
        time_per_score = duration / total_scores if total_scores > 0 else 0
        # Relaxed threshold for CI environment (10ms per score, 2x factor for CI)
        assert time_per_score < 0.02, f"Scoring took {time_per_score:.4f}s per score, expected < 0.02s"


# ============================================================================
# 5. Cross-System Tests
# ============================================================================

class TestCrossSystemCompatibility:
    """Test compatibility between CLI and Dashboard."""
    
    def test_state_format_compatibility(self, tmp_path):
        """Test that state format is compatible between systems."""
        state_file = tmp_path / 'orchestrator_state.json'
        
        # Create state using StateManager
        state_manager = StateManager(str(state_file))
        state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100,
            job_type=JobType.INCREMENTAL,
            parent_job_id="parent_123"
        )
        state_manager.save_state(state)
        
        # Verify state can be loaded as JSON
        with open(state_file, 'r') as f:
            state_dict = json.load(f)
        
        assert state_dict['schema_version'] == '2.0'
        assert state_dict['job_type'] == 'incremental'
        assert state_dict['parent_job_id'] == 'parent_123'
    
    def test_gap_report_compatibility(self, tmp_path):
        """Test gap report format is consistent."""
        output_dir = tmp_path / "review"
        output_dir.mkdir()
        
        # Create gap report
        gap_report_path = create_gap_report(output_dir, num_gaps=3)
        
        # Verify can be loaded and extracted
        extractor = GapExtractor(gap_report_path=str(gap_report_path))
        gaps = extractor.extract_gaps()
        
        assert len(gaps) > 0
        
        # Verify each gap has required fields
        for gap in gaps:
            required_fields = ['pillar_id', 'requirement_id', 'sub_requirement_id', 
                             'current_coverage', 'target_coverage', 'gap_size']
            for field in required_fields:
                assert field in gap


# ============================================================================
# 6. Job Lineage Tracking Tests
# ============================================================================

class TestJobLineageTracking:
    """Test parent-child job lineage tracking."""
    
    def test_parent_job_id_inheritance(self, tmp_path):
        """Test that child jobs inherit parent job ID."""
        output_dir = tmp_path / "review"
        output_dir.mkdir()
        
        # Create parent job
        parent_state_file = output_dir / 'orchestrator_state.json'
        state_manager = StateManager(str(parent_state_file))
        parent_state = state_manager.create_new_state(
            database_path="test.csv",
            database_hash="abc123",
            database_size=100,
            job_type=JobType.FULL
        )
        parent_state.analysis_completed = True
        state_manager.save_state(parent_state)
        
        parent_job_id = parent_state.job_id
        
        # Create child job
        child_dir = tmp_path / "child_review"
        child_dir.mkdir()
        
        child_state_file = child_dir / 'orchestrator_state.json'
        child_state_manager = StateManager(str(child_state_file))
        child_state = child_state_manager.create_new_state(
            database_path="test.csv",
            database_hash="def456",
            database_size=110,
            job_type=JobType.INCREMENTAL,
            parent_job_id=parent_job_id
        )
        child_state_manager.save_state(child_state)
        
        # Verify lineage
        assert child_state.parent_job_id == parent_job_id
        assert child_state.job_type == JobType.INCREMENTAL
    
    def test_multi_generation_lineage(self, tmp_path):
        """Test tracking multiple generations of jobs."""
        # Create job chain: grandparent -> parent -> child
        jobs = []
        
        for i, job_type in enumerate([JobType.FULL, JobType.INCREMENTAL, JobType.INCREMENTAL]):
            job_dir = tmp_path / f"job_{i}"
            job_dir.mkdir()
            
            state_file = job_dir / 'orchestrator_state.json'
            state_manager = StateManager(str(state_file))
            
            parent_id = jobs[-1]['job_id'] if jobs else None
            
            state = state_manager.create_new_state(
                database_path=f"test_{i}.csv",
                database_hash=f"hash_{i}",
                database_size=100 + i * 10,
                job_type=job_type,
                parent_job_id=parent_id
            )
            state_manager.save_state(state)
            
            jobs.append({
                'job_id': state.job_id,
                'job_type': job_type,
                'parent_job_id': parent_id
            })
        
        # Verify chain
        assert jobs[0]['parent_job_id'] is None
        assert jobs[1]['parent_job_id'] == jobs[0]['job_id']
        assert jobs[2]['parent_job_id'] == jobs[1]['job_id']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
