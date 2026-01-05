"""
Validation Test Fixtures

Shared fixtures for validation matrix tests.
"""

import pytest
import json
from pathlib import Path


@pytest.fixture
def validation_workspace(tmp_path):
    """Create a temporary workspace for validation tests."""
    workspace = {
        "root": tmp_path,
        "papers_dir": tmp_path / "data" / "raw",
        "output_dir": tmp_path / "output",
        "cache_dir": tmp_path / "cache",
        "version_history": tmp_path / "review_version_history.json",
        "csv_db": tmp_path / "test_database.csv"
    }
    
    # Create directories
    workspace["papers_dir"].mkdir(parents=True)
    workspace["output_dir"].mkdir(parents=True)
    workspace["cache_dir"].mkdir(parents=True)
    
    # Initialize empty files
    with open(workspace["version_history"], 'w') as f:
        json.dump({}, f)
    
    with open(workspace["csv_db"], 'w') as f:
        f.write("filename,title,authors\n")
    
    return workspace


@pytest.fixture
def sample_claims():
    """Sample claims for validation testing."""
    return [
        {
            "claim_id": "test_claim_001",
            "sub_requirement": "Sub-1.1.1",
            "pillar": "Pillar 1: Biological Stimulus-Response",
            "extracted_claim_text": "The neural network demonstrates spike-timing dependent plasticity.",
            "evidence": "Figure 3 shows STDP curves with timing windows of ±20ms.",
            "evidence_quality": {
                "strength_score": 4,
                "rigor_score": 4,
                "relevance_score": 4,
                "directness": 3,
                "reproducibility_score": 4,
                "composite_score": 3.95
            },
            "status": "pending_judge_review"
        },
        {
            "claim_id": "test_claim_002",
            "sub_requirement": "Sub-1.2.1",
            "pillar": "Pillar 1: Biological Stimulus-Response",
            "extracted_claim_text": "Energy consumption is reduced by 10x compared to GPUs.",
            "evidence": "Table 2 shows power measurements across different workloads.",
            "evidence_quality": {
                "strength_score": 3,
                "rigor_score": 3,
                "relevance_score": 3,
                "directness": 2,
                "reproducibility_score": 3,
                "composite_score": 2.85
            },
            "status": "pending_judge_review"
        }
    ]


@pytest.fixture
def validation_pillar_definitions():
    """Minimal pillar definitions for validation testing."""
    return {
        "Pillar 1: Biological Stimulus-Response": {
            "description": "Test pillar for validation",
            "requirements": {
                "REQ-B1.1: Sensory Transduction & Encoding": [
                    "Sub-1.1.1: Conclusive model of how raw sensory data is transduced",
                    "Sub-1.1.2: Proven mechanism for sensory feature extraction"
                ],
                "REQ-B1.2: Neural Pathways & Integration": [
                    "Sub-1.2.1: Detailed mapping of thalamic relay pathways"
                ]
            }
        }
    }


@pytest.fixture
def golden_dataset_dir(tmp_path):
    """Create golden dataset directory structure."""
    golden_dir = tmp_path / "golden_dataset"
    golden_dir.mkdir()
    
    (golden_dir / "claims").mkdir()
    (golden_dir / "verdicts").mkdir()
    (golden_dir / "gaps").mkdir()
    
    return golden_dir
