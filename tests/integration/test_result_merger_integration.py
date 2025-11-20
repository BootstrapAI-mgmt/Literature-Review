"""
Integration tests for Result Merger Utility.

Tests realistic scenarios with complete gap analysis reports.
"""

import pytest
import json
from pathlib import Path
from literature_review.analysis.result_merger import merge_reports


@pytest.fixture
def real_gap_analysis_reports(tmp_path):
    """Create realistic gap analysis reports."""
    base_report = {
        "pillars": {
            "Pillar 1: Foundational Architecture": {
                "requirements": {
                    "REQ-001": {
                        "text": "Biological Modeling",
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Implement STDP learning mechanism",
                                "completeness_percent": 33.0,
                                "evidence": [
                                    {
                                        "filename": "paper1.pdf",
                                        "claim": "STDP implemented successfully",
                                        "score": 0.9,
                                        "page": 5,
                                    },
                                    {
                                        "filename": "paper2.pdf",
                                        "claim": "STDP in spiking networks",
                                        "score": 0.85,
                                        "page": 3,
                                    },
                                ],
                            },
                            "SUB-002": {
                                "text": "Synaptic plasticity models",
                                "completeness_percent": 67.0,
                                "evidence": [
                                    {
                                        "filename": "paper3.pdf",
                                        "claim": "Plasticity model",
                                        "score": 0.8,
                                        "page": 10,
                                    },
                                    {
                                        "filename": "paper4.pdf",
                                        "claim": "Synaptic dynamics",
                                        "score": 0.75,
                                        "page": 7,
                                    },
                                    {
                                        "filename": "paper5.pdf",
                                        "claim": "Learning rules",
                                        "score": 0.82,
                                        "page": 12,
                                    },
                                ],
                            },
                        },
                    }
                }
            }
        },
        "metadata": {
            "version": 1,
            "total_papers": 5,
            "analysis_date": "2025-01-15T10:00:00Z",
        },
    }

    new_report = {
        "pillars": {
            "Pillar 1: Foundational Architecture": {
                "requirements": {
                    "REQ-001": {
                        "text": "Biological Modeling",
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Implement STDP learning mechanism",
                                "completeness_percent": 33.0,
                                "evidence": [
                                    {
                                        "filename": "paper6.pdf",
                                        "claim": "Advanced STDP implementation",
                                        "score": 0.92,
                                        "page": 8,
                                    }
                                ],
                            }
                        },
                    }
                }
            }
        },
        "metadata": {
            "version": 1,
            "total_papers": 1,
            "analysis_date": "2025-01-19T14:00:00Z",
        },
    }

    base_path = tmp_path / "base" / "gap_analysis_report.json"
    new_path = tmp_path / "new" / "gap_analysis_report.json"

    base_path.parent.mkdir(parents=True)
    new_path.parent.mkdir(parents=True)

    with open(base_path, "w") as f:
        json.dump(base_report, f, indent=2)

    with open(new_path, "w") as f:
        json.dump(new_report, f, indent=2)

    return base_path, new_path


@pytest.mark.integration
def test_realistic_merge(real_gap_analysis_reports, tmp_path):
    """Test merge with realistic gap analysis reports."""
    base_path, new_path = real_gap_analysis_reports
    output_path = tmp_path / "merged" / "gap_analysis_report.json"

    result = merge_reports(str(base_path), str(new_path), str(output_path))

    # Verify statistics
    assert result.statistics["papers_added"] == 1
    assert result.statistics["evidence_added"] == 1

    # Verify merged report
    with open(output_path) as f:
        merged = json.load(f)

    # Check SUB-001 now has 3 evidence items (2 original + 1 new)
    sub_001_evidence = merged["pillars"]["Pillar 1: Foundational Architecture"][
        "requirements"
    ]["REQ-001"]["sub_requirements"]["SUB-001"]["evidence"]
    assert len(sub_001_evidence) == 3

    # Check completeness updated (3 evidence = 67%)
    assert (
        merged["pillars"]["Pillar 1: Foundational Architecture"]["requirements"][
            "REQ-001"
        ]["sub_requirements"]["SUB-001"]["completeness_percent"]
        == 67.0
    )

    # Check metadata
    assert merged["metadata"]["version"] == 2
    assert merged["metadata"]["total_papers"] == 6
    assert "merge_history" in merged["metadata"]


@pytest.mark.integration
def test_multiple_successive_merges(real_gap_analysis_reports, tmp_path):
    """Test performing multiple successive merges."""
    base_path, new_path = real_gap_analysis_reports
    output_path = tmp_path / "merged" / "gap_analysis_report.json"

    # First merge
    result1 = merge_reports(str(base_path), str(new_path), str(output_path))

    # Create another new report
    new_report2 = {
        "pillars": {
            "Pillar 1: Foundational Architecture": {
                "requirements": {
                    "REQ-001": {
                        "text": "Biological Modeling",
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Implement STDP learning mechanism",
                                "completeness_percent": 67.0,
                                "evidence": [
                                    {
                                        "filename": "paper7.pdf",
                                        "claim": "Another STDP paper",
                                        "score": 0.88,
                                        "page": 15,
                                    }
                                ],
                            }
                        },
                    }
                }
            }
        },
        "metadata": {
            "version": 1,
            "total_papers": 1,
            "analysis_date": "2025-01-20T10:00:00Z",
        },
    }

    new_path2 = tmp_path / "new2" / "gap_analysis_report.json"
    new_path2.parent.mkdir(parents=True)
    with open(new_path2, "w") as f:
        json.dump(new_report2, f, indent=2)

    # Second merge (on top of first)
    result2 = merge_reports(str(output_path), str(new_path2), str(output_path))

    # Verify cumulative results
    assert result2.statistics["papers_added"] == 1

    with open(output_path) as f:
        merged = json.load(f)

    # Should now have 4 evidence items (2 + 1 + 1)
    sub_001_evidence = merged["pillars"]["Pillar 1: Foundational Architecture"][
        "requirements"
    ]["REQ-001"]["sub_requirements"]["SUB-001"]["evidence"]
    assert len(sub_001_evidence) == 4

    # Version should be 3 (1 -> 2 -> 3)
    assert merged["metadata"]["version"] == 3

    # Total papers: 5 + 1 + 1 = 7
    assert merged["metadata"]["total_papers"] == 7

    # Should have 2 merge history entries
    assert len(merged["metadata"]["merge_history"]) == 2


@pytest.mark.integration
def test_merge_with_overlapping_evidence(tmp_path):
    """Test merge when new report has some overlapping evidence."""
    base_report = {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Test requirement",
                                "completeness_percent": 67.0,
                                "evidence": [
                                    {
                                        "filename": "paper1.pdf",
                                        "claim": "Claim 1",
                                        "score": 0.9,
                                    },
                                    {
                                        "filename": "paper2.pdf",
                                        "claim": "Claim 2",
                                        "score": 0.8,
                                    },
                                    {
                                        "filename": "paper3.pdf",
                                        "claim": "Claim 3",
                                        "score": 0.85,
                                    },
                                ],
                            }
                        }
                    }
                }
            }
        },
        "metadata": {"version": 1, "total_papers": 3},
    }

    new_report = {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Test requirement",
                                "completeness_percent": 67.0,
                                "evidence": [
                                    {
                                        "filename": "paper2.pdf",
                                        "claim": "Claim 2",
                                        "score": 0.8,
                                    },  # Duplicate
                                    {
                                        "filename": "paper4.pdf",
                                        "claim": "Claim 4",
                                        "score": 0.95,
                                    },  # New
                                    {
                                        "filename": "paper5.pdf",
                                        "claim": "Claim 5",
                                        "score": 0.87,
                                    },  # New
                                ],
                            }
                        }
                    }
                }
            }
        },
        "metadata": {"version": 1, "total_papers": 3},
    }

    base_path = tmp_path / "base.json"
    new_path = tmp_path / "new.json"
    output_path = tmp_path / "merged.json"

    with open(base_path, "w") as f:
        json.dump(base_report, f)
    with open(new_path, "w") as f:
        json.dump(new_report, f)

    result = merge_reports(str(base_path), str(new_path), str(output_path))

    # Should add 2 new papers (paper4, paper5) and skip duplicate (paper2)
    assert result.statistics["papers_added"] == 2
    assert result.statistics["evidence_added"] == 2
    assert result.statistics["evidence_duplicated"] == 1

    # Should have warning about duplicate
    assert result.has_warnings

    with open(output_path) as f:
        merged = json.load(f)

    # Total evidence: 3 + 2 = 5
    evidence = merged["pillars"]["Pillar 1"]["requirements"]["REQ-001"][
        "sub_requirements"
    ]["SUB-001"]["evidence"]
    assert len(evidence) == 5

    # Completeness should be 100% (5+ evidence)
    assert (
        merged["pillars"]["Pillar 1"]["requirements"]["REQ-001"]["sub_requirements"][
            "SUB-001"
        ]["completeness_percent"]
        == 100.0
    )


@pytest.mark.integration
def test_merge_with_conflict_detection(tmp_path):
    """Test that conflicts are properly detected and reported."""
    base_report = {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Test requirement",
                                "completeness_percent": 33.0,
                                "evidence": [
                                    {
                                        "filename": "paper1.pdf",
                                        "claim": "Original claim",
                                        "score": 0.9,
                                        "page": 5,
                                    }
                                ],
                            }
                        }
                    }
                }
            }
        },
        "metadata": {"version": 1, "total_papers": 1},
    }

    new_report = {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Test requirement",
                                "completeness_percent": 33.0,
                                "evidence": [
                                    {
                                        "filename": "paper1.pdf",
                                        "claim": "Different claim",
                                        "score": 0.7,
                                        "page": 8,
                                    }
                                ],
                            }
                        }
                    }
                }
            }
        },
        "metadata": {"version": 1, "total_papers": 1},
    }

    base_path = tmp_path / "base.json"
    new_path = tmp_path / "new.json"
    output_path = tmp_path / "merged.json"

    with open(base_path, "w") as f:
        json.dump(base_report, f)
    with open(new_path, "w") as f:
        json.dump(new_report, f)

    # Test with keep_existing
    result = merge_reports(
        str(base_path),
        str(new_path),
        str(output_path),
        conflict_resolution="keep_existing",
    )

    # Should detect conflict
    assert result.has_conflicts
    assert len(result.conflicts) == 1
    assert result.conflicts[0]["filename"] == "paper1.pdf"

    # Should keep original data
    with open(output_path) as f:
        merged = json.load(f)

    evidence = merged["pillars"]["Pillar 1"]["requirements"]["REQ-001"][
        "sub_requirements"
    ]["SUB-001"]["evidence"]
    assert evidence[0]["claim"] == "Original claim"
    assert evidence[0]["score"] == 0.9


@pytest.mark.integration
def test_large_scale_merge(tmp_path):
    """Test merging reports with many pillars and requirements."""
    # Create a larger report
    base_report = {"pillars": {}, "metadata": {"version": 1, "total_papers": 0}}

    # Create 5 pillars with 3 requirements each
    for pillar_idx in range(1, 6):
        pillar_name = f"Pillar {pillar_idx}"
        base_report["pillars"][pillar_name] = {"requirements": {}}

        for req_idx in range(1, 4):
            req_id = f"REQ-{pillar_idx:03d}-{req_idx:03d}"
            base_report["pillars"][pillar_name]["requirements"][req_id] = {
                "sub_requirements": {
                    "SUB-001": {
                        "text": f"Requirement {req_id}",
                        "completeness_percent": 33.0,
                        "evidence": [
                            {
                                "filename": f"paper_{pillar_idx}_{req_idx}_1.pdf",
                                "claim": "Test",
                                "score": 0.8,
                            }
                        ],
                    }
                }
            }
            base_report["metadata"]["total_papers"] += 1

    # Create new report adding one more evidence to each sub-requirement
    new_report = {"pillars": {}, "metadata": {"version": 1, "total_papers": 0}}

    for pillar_idx in range(1, 6):
        pillar_name = f"Pillar {pillar_idx}"
        new_report["pillars"][pillar_name] = {"requirements": {}}

        for req_idx in range(1, 4):
            req_id = f"REQ-{pillar_idx:03d}-{req_idx:03d}"
            new_report["pillars"][pillar_name]["requirements"][req_id] = {
                "sub_requirements": {
                    "SUB-001": {
                        "text": f"Requirement {req_id}",
                        "completeness_percent": 33.0,
                        "evidence": [
                            {
                                "filename": f"paper_{pillar_idx}_{req_idx}_2.pdf",
                                "claim": "Test 2",
                                "score": 0.85,
                            }
                        ],
                    }
                }
            }
            new_report["metadata"]["total_papers"] += 1

    base_path = tmp_path / "base.json"
    new_path = tmp_path / "new.json"
    output_path = tmp_path / "merged.json"

    with open(base_path, "w") as f:
        json.dump(base_report, f)
    with open(new_path, "w") as f:
        json.dump(new_report, f)

    # Merge
    result = merge_reports(str(base_path), str(new_path), str(output_path))

    # Should add 15 new papers (5 pillars * 3 requirements)
    assert result.statistics["papers_added"] == 15
    assert result.statistics["evidence_added"] == 15

    # Verify merged report structure
    with open(output_path) as f:
        merged = json.load(f)

    assert len(merged["pillars"]) == 5

    # Check one pillar in detail
    pillar1_reqs = merged["pillars"]["Pillar 1"]["requirements"]
    assert len(pillar1_reqs) == 3

    # Each sub-requirement should have 2 evidence items now
    for req_id, req_data in pillar1_reqs.items():
        evidence = req_data["sub_requirements"]["SUB-001"]["evidence"]
        assert len(evidence) == 2


@pytest.mark.integration
def test_output_directory_creation(tmp_path):
    """Test that output directories are created if they don't exist."""
    base_report = {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Test",
                                "completeness_percent": 0.0,
                                "evidence": [],
                            }
                        }
                    }
                }
            }
        },
        "metadata": {"version": 1, "total_papers": 0},
    }

    base_path = tmp_path / "base.json"
    new_path = tmp_path / "new.json"

    # Output path with non-existent nested directories
    output_path = tmp_path / "deeply" / "nested" / "output" / "merged.json"

    with open(base_path, "w") as f:
        json.dump(base_report, f)
    with open(new_path, "w") as f:
        json.dump(base_report, f)

    # Should create directories automatically
    result = merge_reports(str(base_path), str(new_path), str(output_path))

    assert output_path.exists()
    assert output_path.parent.exists()
