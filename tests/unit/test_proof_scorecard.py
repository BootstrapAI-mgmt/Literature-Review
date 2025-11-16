"""Unit tests for proof_scorecard module."""

import json
import os
import tempfile
import pytest
from literature_review.analysis.proof_scorecard import (
    ProofScorecardAnalyzer,
    generate_scorecard
)


@pytest.fixture
def sample_gap_report():
    """Sample gap report for testing."""
    return {
        "Pillar 1: Biological Stimulus-Response": {
            "completeness": 50.0,
            "analysis": {
                "REQ-B1.1": {
                    "Sub-1.1.1": {"completeness_percent": 80},
                    "Sub-1.1.2": {"completeness_percent": 0},
                    "Sub-1.1.3": {"completeness_percent": 50}
                }
            }
        },
        "Pillar 2: AI Stimulus-Response": {
            "completeness": 60.0,
            "analysis": {
                "REQ-A2.1": {
                    "Sub-2.1.1": {"completeness_percent": 60}
                }
            }
        },
        "Pillar 3: Biological Skill": {
            "completeness": 40.0,
            "analysis": {}
        },
        "Pillar 4: AI Skill": {
            "completeness": 70.0,
            "analysis": {}
        },
        "Pillar 5: Biological Memory": {
            "completeness": 30.0,
            "analysis": {}
        },
        "Pillar 6: AI Memory": {
            "completeness": 55.0,
            "analysis": {}
        },
        "Pillar 7: System Integration": {
            "completeness": 45.0,
            "analysis": {}
        }
    }


@pytest.fixture
def sample_version_history():
    """Sample version history for testing."""
    return {}


@pytest.fixture
def sample_pillar_definitions():
    """Sample pillar definitions for testing."""
    return {
        "Pillar 1": {"description": "Test pillar 1"},
        "Pillar 2": {"description": "Test pillar 2"}
    }


class TestProofScorecardAnalyzer:
    """Test ProofScorecardAnalyzer class."""
    
    def test_initialization(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test analyzer initialization."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        assert analyzer.gap_report == sample_gap_report
        assert analyzer.version_history == sample_version_history
        assert analyzer.pillar_definitions == sample_pillar_definitions
    
    def test_find_pillar_data(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test pillar data finding with partial name match."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        
        # Test exact match
        pillar1_data = analyzer._find_pillar_data("Pillar 1: Biological Stimulus-Response")
        assert pillar1_data['completeness'] == 50.0
        
        # Test partial match
        pillar2_data = analyzer._find_pillar_data("Pillar 2")
        assert pillar2_data['completeness'] == 60.0
        
        # Test non-existent pillar
        no_data = analyzer._find_pillar_data("Pillar 99")
        assert no_data == {}
    
    def test_calculate_overall_proof_readiness(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test overall proof readiness calculation."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        
        score = analyzer._calculate_overall_proof_readiness()
        
        # Score should be between 0 and 100
        assert 0 <= score <= 100
        
        # With sample data, should be around 50 (weighted average)
        assert 40 <= score <= 60
    
    def test_get_average_completeness(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test average completeness calculation."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        
        # Test single pillar
        avg = analyzer._get_average_completeness(["Pillar 1"])
        assert avg == 50.0
        
        # Test multiple pillars
        avg = analyzer._get_average_completeness(["Pillar 1", "Pillar 2", "Pillar 3"])
        assert avg == 50.0  # (50 + 60 + 40) / 3
        
        # Test non-existent pillar
        avg = analyzer._get_average_completeness(["Pillar 99"])
        assert avg == 0
    
    def test_estimate_sufficiency(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test evidence sufficiency estimation."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        
        sufficiency = analyzer._estimate_sufficiency(["Pillar 1"])
        
        # Sufficiency should be 70% of completeness (quality penalty)
        assert sufficiency == 35.0  # 50 * 0.7
    
    def test_get_proof_status(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test proof status determination."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        
        assert analyzer._get_proof_status(85) == 'PROVEN'
        assert analyzer._get_proof_status(70) == 'PROBABLE'
        assert analyzer._get_proof_status(50) == 'POSSIBLE'
        assert analyzer._get_proof_status(30) == 'INSUFFICIENT'
        assert analyzer._get_proof_status(10) == 'UNPROVEN'
    
    def test_estimate_papers_needed(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test papers needed estimation."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        
        # 15% deficit -> 1 paper
        assert analyzer._estimate_papers_needed(15) == 1
        
        # 30% deficit -> 2 papers
        assert analyzer._estimate_papers_needed(30) == 2
        
        # 45% deficit -> 3 papers
        assert analyzer._estimate_papers_needed(45) == 3
        
        # Minimum of 1 paper
        assert analyzer._estimate_papers_needed(5) == 1
    
    def test_estimate_timeline(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test timeline estimation."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        
        weeks = analyzer._estimate_timeline(30)
        
        # 30% deficit = 2 papers = 5 hours = ~1 week
        assert weeks >= 1
    
    def test_get_verdict(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test verdict determination."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        
        assert analyzer._get_verdict(85) == 'PUBLICATION_READY'
        assert analyzer._get_verdict(65) == 'NEAR_READY'
        assert analyzer._get_verdict(45) == 'PROGRESS_NEEDED'
        assert analyzer._get_verdict(25) == 'SIGNIFICANT_GAPS'
        assert analyzer._get_verdict(10) == 'INSUFFICIENT_FOR_PUBLICATION'
    
    def test_recommend_venue(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test venue recommendation."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        
        venue = analyzer._recommend_venue(85)
        assert 'Tier 1' in venue
        
        venue = analyzer._recommend_venue(65)
        assert 'Tier 2' in venue
        
        venue = analyzer._recommend_venue(45)
        assert 'Conference' in venue
        
        venue = analyzer._recommend_venue(25)
        assert 'Preprint' in venue
    
    def test_analyze(self, sample_gap_report, sample_version_history, sample_pillar_definitions):
        """Test full scorecard analysis."""
        analyzer = ProofScorecardAnalyzer(
            sample_gap_report,
            sample_version_history,
            sample_pillar_definitions
        )
        
        scorecard = analyzer.analyze()
        
        # Verify structure
        assert 'timestamp' in scorecard
        assert 'overall_proof_status' in scorecard
        assert 'research_goals' in scorecard
        assert 'proof_requirements_checklist' in scorecard
        assert 'publication_viability' in scorecard
        assert 'critical_next_steps' in scorecard
        assert 'pillar_7_readiness' in scorecard
        
        # Verify overall proof status
        assert 'proof_readiness_score' in scorecard['overall_proof_status']
        assert 'verdict' in scorecard['overall_proof_status']
        assert 'headline' in scorecard['overall_proof_status']
        
        # Verify research goals
        assert len(scorecard['research_goals']) == 3
        for goal in scorecard['research_goals']:
            assert 'goal' in goal
            assert 'pillars' in goal
            assert 'completeness' in goal
            assert 'sufficiency' in goal
            assert 'proof_status' in goal
        
        # Verify publication viability
        assert 'tier_1_journal' in scorecard['publication_viability']
        assert 'tier_2_journal' in scorecard['publication_viability']
        assert 'conference_paper' in scorecard['publication_viability']
        assert 'preprint' in scorecard['publication_viability']
        assert 'recommended_venue' in scorecard['publication_viability']


def test_generate_scorecard():
    """Test scorecard generation with file I/O."""
    # Create temporary files
    with tempfile.TemporaryDirectory() as tmpdir:
        gap_file = os.path.join(tmpdir, 'gap.json')
        version_file = os.path.join(tmpdir, 'version.json')
        pillar_file = os.path.join(tmpdir, 'pillar.json')
        output_dir = os.path.join(tmpdir, 'output')
        
        # Write sample data
        with open(gap_file, 'w') as f:
            json.dump({
                "Pillar 1: Test": {"completeness": 50.0, "analysis": {}},
                "Pillar 2: Test": {"completeness": 60.0, "analysis": {}}
            }, f)
        
        with open(version_file, 'w') as f:
            json.dump({}, f)
        
        with open(pillar_file, 'w') as f:
            json.dump({}, f)
        
        # Generate scorecard
        scorecard = generate_scorecard(gap_file, version_file, pillar_file, output_dir)
        
        # Verify output file was created
        assert os.path.exists(os.path.join(output_dir, 'proof_scorecard.json'))
        
        # Verify scorecard structure
        assert 'timestamp' in scorecard
        assert 'overall_proof_status' in scorecard


def test_generate_scorecard_missing_version_file():
    """Test scorecard generation with missing version history file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gap_file = os.path.join(tmpdir, 'gap.json')
        version_file = os.path.join(tmpdir, 'nonexistent.json')
        pillar_file = os.path.join(tmpdir, 'pillar.json')
        output_dir = os.path.join(tmpdir, 'output')
        
        # Write sample data
        with open(gap_file, 'w') as f:
            json.dump({
                "Pillar 1: Test": {"completeness": 50.0, "analysis": {}}
            }, f)
        
        with open(pillar_file, 'w') as f:
            json.dump({}, f)
        
        # Should not raise error even if version file is missing
        scorecard = generate_scorecard(gap_file, version_file, pillar_file, output_dir)
        
        # Verify scorecard was still generated
        assert 'timestamp' in scorecard
