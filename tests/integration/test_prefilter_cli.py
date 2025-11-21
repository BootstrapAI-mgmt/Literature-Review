"""Integration tests for pre-filter CLI arguments (INCR-W1-6)."""

import pytest
import subprocess
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def test_pipeline_orchestrator_prefilter_help():
    """Test that pre-filter arguments show in help."""
    result = subprocess.run(
        ['python', 'pipeline_orchestrator.py', '--help'],
        capture_output=True,
        text=True,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    )
    
    assert result.returncode == 0
    assert '--prefilter' in result.stdout
    assert '--no-prefilter' in result.stdout
    assert '--relevance-threshold' in result.stdout
    assert '--prefilter-mode' in result.stdout


def test_pipeline_config_has_prefilter():
    """Test that pipeline_config.json contains prefilter section."""
    import json
    from pathlib import Path
    
    config_path = Path(__file__).parent.parent.parent / 'pipeline_config.json'
    
    with open(config_path) as f:
        config = json.load(f)
    
    assert 'prefilter' in config
    assert 'enabled' in config['prefilter']
    assert 'threshold' in config['prefilter']
    assert 'mode' in config['prefilter']
    
    # Check default values
    assert config['prefilter']['enabled'] is True
    assert config['prefilter']['threshold'] == 0.50
    assert config['prefilter']['mode'] == 'auto'


def test_orchestrator_config_accepts_prefilter_params():
    """Test that OrchestratorConfig accepts pre-filter parameters."""
    try:
        from literature_review.orchestrator import OrchestratorConfig
    except ImportError:
        pytest.skip("google.genai not available - skipping orchestrator import test")
    
    # Test with default values
    config1 = OrchestratorConfig(
        job_id='test_job',
        analysis_target=['ALL'],
        run_mode='ONCE'
    )
    assert config1.prefilter_enabled is True
    assert config1.relevance_threshold == 0.50
    assert config1.prefilter_mode == 'auto'
    
    # Test with custom values
    config2 = OrchestratorConfig(
        job_id='test_job',
        analysis_target=['ALL'],
        run_mode='ONCE',
        prefilter_enabled=False,
        relevance_threshold=0.60
    )
    assert config2.prefilter_enabled is False
    assert config2.relevance_threshold == 0.60
    
    # Test aggressive mode
    config3 = OrchestratorConfig(
        job_id='test_job',
        analysis_target=['ALL'],
        run_mode='ONCE',
        prefilter_mode='aggressive'
    )
    assert config3.relevance_threshold == 0.30
    
    # Test conservative mode
    config4 = OrchestratorConfig(
        job_id='test_job',
        analysis_target=['ALL'],
        run_mode='ONCE',
        prefilter_mode='conservative'
    )
    assert config4.relevance_threshold == 0.70


def test_gap_extractor_relevance_scorer_integration():
    """Test integration between GapExtractor and RelevanceScorer."""
    import tempfile
    import json
    from literature_review.utils.gap_extractor import GapExtractor
    from literature_review.utils.relevance_scorer import RelevanceScorer
    
    # Create sample gap report
    gap_report = {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Neural network spike timing mechanisms",
                                "completeness_percent": 40,
                                "evidence": ["paper1.pdf"]
                            }
                        }
                    }
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(gap_report, f)
        temp_path = f.name
    
    try:
        # Extract gaps
        extractor = GapExtractor(temp_path, threshold=0.70)
        gaps = extractor.extract_gaps()
        
        assert len(gaps) == 1
        
        # Score papers against gaps
        scorer = RelevanceScorer(use_semantic=False)
        
        papers = [
            {
                'id': 'paper_relevant',
                'title': 'Spike Timing in Neural Networks',
                'abstract': 'We study spike timing dependent plasticity mechanisms'
            },
            {
                'id': 'paper_irrelevant',
                'title': 'Quantum Computing',
                'abstract': 'Quantum algorithms for optimization'
            }
        ]
        
        scores = scorer.batch_score(papers, gaps)
        
        # Relevant paper should score higher
        assert scores['paper_relevant'] > scores['paper_irrelevant']
        assert scores['paper_relevant'] > 0.3
        assert scores['paper_irrelevant'] < 0.2
    
    finally:
        os.unlink(temp_path)


def test_state_manager_gap_details():
    """Test StateManager can save and load gap details."""
    import tempfile
    from literature_review.utils.state_manager import StateManager, GapDetail
    
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, 'state.json')
        manager = StateManager(state_file)
        
        # Create gap details
        gaps = [
            GapDetail(
                pillar_id='Pillar 1',
                requirement_id='REQ-001',
                sub_requirement_id='SUB-001',
                current_coverage=0.45,
                target_coverage=0.70,
                gap_size=0.25,
                keywords=['neural', 'spike'],
                evidence_count=2
            ),
            GapDetail(
                pillar_id='Pillar 2',
                requirement_id='REQ-002',
                sub_requirement_id='SUB-002',
                current_coverage=0.30,
                target_coverage=0.70,
                gap_size=0.40,
                keywords=['learning', 'algorithm'],
                evidence_count=1
            )
        ]
        
        # Create initial state
        state = manager.create_new_state(
            database_path='/test/path',
            database_hash='test_hash',
            database_size=100
        )
        
        # Update state with gap details
        state.total_papers = 100
        state.papers_analyzed = 30
        state.papers_skipped = 70
        state.gap_metrics.gap_details = gaps
        state.gap_metrics.total_gaps = len(gaps)
        
        # Save state
        manager.save_state(state)
        
        # Load and verify
        loaded = manager.load_state()
        
        assert loaded.gap_metrics.total_gaps == 2
        assert len(loaded.gap_metrics.gap_details) == 2
        
        # Verify first gap
        gap1 = loaded.gap_metrics.gap_details[0]
        assert gap1.pillar_id == 'Pillar 1'
        assert gap1.current_coverage == 0.45
        assert gap1.gap_size == 0.25
        assert 'neural' in gap1.keywords
