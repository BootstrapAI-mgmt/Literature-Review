"""Unit tests for proof chain dependency analysis."""

import pytest
import tempfile
import json
import os
from literature_review.analysis.proof_chain import ProofChainAnalyzer


@pytest.fixture
def sample_gap_data():
    """Sample gap analysis data."""
    return {
        "pillars": [
            {
                "name": "Test Pillar",
                "requirements": [
                    {
                        "id": "P1-R1",
                        "requirement": "Test Requirement 1",
                        "papers_found": 5,
                        "gap_severity": "Medium",
                        "avg_alignment": 0.6
                    },
                    {
                        "id": "P1-R2",
                        "requirement": "Test Requirement 2",
                        "papers_found": 2,
                        "gap_severity": "High",
                        "avg_alignment": 0.4
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_pillar_data():
    """Sample pillar definitions with dependencies."""
    return [
        {
            "name": "Test Pillar",
            "requirements": [
                {
                    "id": "P1-R1",
                    "requirement": "Test Requirement 1",
                    "depends_on": []
                },
                {
                    "id": "P1-R2",
                    "requirement": "Test Requirement 2",
                    "depends_on": ["P1-R1"]
                },
                {
                    "id": "P1-R3",
                    "requirement": "Test Requirement 3",
                    "depends_on": ["P1-R2"]
                }
            ]
        }
    ]


def test_dependency_graph_construction(tmp_path, sample_gap_data, sample_pillar_data):
    """Test graph construction from pillar definitions."""
    # Create temp files
    gap_file = tmp_path / "gap.json"
    pillar_file = tmp_path / "pillars.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    with open(pillar_file, 'w') as f:
        json.dump(sample_pillar_data, f)
    
    # Create analyzer
    analyzer = ProofChainAnalyzer(str(gap_file), str(pillar_file))
    analyzer._build_dependency_graph()
    
    assert analyzer.dependency_graph.number_of_nodes() == 3
    assert analyzer.dependency_graph.number_of_edges() == 2


def test_critical_path_finding(tmp_path, sample_gap_data, sample_pillar_data):
    """Test critical path detection."""
    gap_file = tmp_path / "gap.json"
    pillar_file = tmp_path / "pillars.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    with open(pillar_file, 'w') as f:
        json.dump(sample_pillar_data, f)
    
    analyzer = ProofChainAnalyzer(str(gap_file), str(pillar_file))
    analyzer._build_dependency_graph()
    
    critical_paths = analyzer._find_critical_paths()
    
    assert len(critical_paths) > 0
    assert len(critical_paths[0]) == 3  # Path: P1-R1 -> P1-R2 -> P1-R3


def test_blocking_requirements_detection(tmp_path, sample_gap_data, sample_pillar_data):
    """Test blocking requirement detection."""
    gap_file = tmp_path / "gap.json"
    pillar_file = tmp_path / "pillars.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    with open(pillar_file, 'w') as f:
        json.dump(sample_pillar_data, f)
    
    analyzer = ProofChainAnalyzer(str(gap_file), str(pillar_file))
    report = analyzer.analyze_dependencies()
    
    # P1-R1 should not be blocking (only blocks 2 requirements, threshold is 3)
    blocking = report['blocking_requirements']
    assert len(blocking) == 0  # With only 3 nodes, none meet threshold


def test_proof_propagation(tmp_path, sample_gap_data, sample_pillar_data):
    """Test proof readiness propagation."""
    gap_file = tmp_path / "gap.json"
    pillar_file = tmp_path / "pillars.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    with open(pillar_file, 'w') as f:
        json.dump(sample_pillar_data, f)
    
    analyzer = ProofChainAnalyzer(str(gap_file), str(pillar_file))
    analyzer._build_dependency_graph()
    
    propagation = analyzer._calculate_proof_propagation()
    
    assert 'P1-R1' in propagation
    assert 'own_readiness' in propagation['P1-R1']
    assert 0 <= propagation['P1-R1']['own_readiness'] <= 1


def test_priority_calculation(tmp_path, sample_gap_data, sample_pillar_data):
    """Test requirement prioritization."""
    gap_file = tmp_path / "gap.json"
    pillar_file = tmp_path / "pillars.json"
    
    with open(gap_file, 'w') as f:
        json.dump(sample_gap_data, f)
    
    with open(pillar_file, 'w') as f:
        json.dump(sample_pillar_data, f)
    
    analyzer = ProofChainAnalyzer(str(gap_file), str(pillar_file))
    analyzer._build_dependency_graph()
    
    priorities = analyzer._prioritize_requirements()
    
    assert len(priorities) == 3
    assert all('priority_score' in p for p in priorities)
    # Priorities should be sorted (highest first)
    assert priorities[0]['priority_score'] >= priorities[-1]['priority_score']
