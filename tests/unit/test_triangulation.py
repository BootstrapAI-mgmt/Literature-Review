"""Unit tests for evidence triangulation analysis."""

import pytest
import json
from literature_review.analysis.triangulation import TriangulationAnalyzer


@pytest.fixture
def sample_review_log():
    """Sample review log with author/institution data."""
    return {
        "paper1.json": {
            "metadata": {
                "title": "Paper 1",
                "authors": ["Author A"],
                "affiliation": "MIT",
            },
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.8,
                            }
                        ],
                    }
                ]
            },
        },
        "paper2.json": {
            "metadata": {
                "title": "Paper 2",
                "authors": ["Author B"],
                "affiliation": "Stanford",
            },
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.7,
                            }
                        ],
                    }
                ]
            },
        },
        "paper3.json": {
            "metadata": {
                "title": "Paper 3",
                "authors": ["Author A"],
                "affiliation": "MIT",
            },
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.6,
                            }
                        ],
                    }
                ]
            },
        },
    }


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
                        "requirement": "Test Req 1",
                        "papers_found": 3,
                        "gap_severity": "Low",
                    }
                ],
            }
        ]
    }


def test_author_grouping(tmp_path, sample_review_log, sample_gap_data):
    """Test grouping papers by author."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"

    with open(review_file, "w") as f:
        json.dump(sample_review_log, f)
    with open(gap_file, "w") as f:
        json.dump(sample_gap_data, f)

    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    author_groups = analyzer._group_by_authors()

    assert "Author A" in author_groups
    assert len(author_groups["Author A"]) == 2  # paper1 and paper3


def test_institution_grouping(tmp_path, sample_review_log, sample_gap_data):
    """Test grouping papers by institution."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"

    with open(review_file, "w") as f:
        json.dump(sample_review_log, f)
    with open(gap_file, "w") as f:
        json.dump(sample_gap_data, f)

    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    inst_groups = analyzer._group_by_institutions()

    assert "MIT" in inst_groups
    assert "Stanford" in inst_groups
    assert len(inst_groups["MIT"]) == 2


def test_source_diversity_calculation(tmp_path, sample_review_log, sample_gap_data):
    """Test source diversity score calculation."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"

    with open(review_file, "w") as f:
        json.dump(sample_review_log, f)
    with open(gap_file, "w") as f:
        json.dump(sample_gap_data, f)

    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    author_groups = analyzer._group_by_authors()
    inst_groups = analyzer._group_by_institutions()

    papers = ["paper1.json", "paper2.json", "paper3.json"]
    diversity = analyzer._calculate_source_diversity(papers, author_groups, inst_groups)

    # 3 papers from 2 institutions = 2/3 = 0.67 diversity
    assert diversity["unique_institutions"] == 2
    assert 0.6 <= diversity["diversity_score"] <= 0.7


def test_echo_chamber_detection(tmp_path, sample_review_log, sample_gap_data):
    """Test echo chamber risk detection."""
    # Modify to have all papers from same institution
    echo_review_log = sample_review_log.copy()
    for paper in echo_review_log.values():
        paper["metadata"]["affiliation"] = "MIT"

    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"

    with open(review_file, "w") as f:
        json.dump(echo_review_log, f)
    with open(gap_file, "w") as f:
        json.dump(sample_gap_data, f)

    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    report = analyzer.analyze_triangulation()

    # Should detect echo chamber risk
    assert report["summary"]["echo_chamber_risks"] > 0


def test_full_analysis(tmp_path, sample_review_log, sample_gap_data):
    """Test complete triangulation analysis."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"

    with open(review_file, "w") as f:
        json.dump(sample_review_log, f)
    with open(gap_file, "w") as f:
        json.dump(sample_gap_data, f)

    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    report = analyzer.analyze_triangulation()

    assert "requirement_analysis" in report
    assert "summary" in report
    assert report["summary"]["total_requirements_analyzed"] == 1


def test_empty_reviews(tmp_path):
    """Test with empty review log."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"

    with open(review_file, "w") as f:
        json.dump({}, f)
    with open(gap_file, "w") as f:
        json.dump({"pillars": []}, f)

    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    report = analyzer.analyze_triangulation()

    assert report["summary"]["total_requirements_analyzed"] == 0
    assert report["summary"]["needs_independent_validation"] == 0


def test_missing_metadata(tmp_path, sample_gap_data):
    """Test with missing metadata in reviews."""
    review_log = {
        "paper1.json": {
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.8,
                            }
                        ],
                    }
                ]
            }
        }
    }

    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"

    with open(review_file, "w") as f:
        json.dump(review_log, f)
    with open(gap_file, "w") as f:
        json.dump(sample_gap_data, f)

    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    author_groups = analyzer._group_by_authors()

    # Should handle missing metadata gracefully
    assert "Unknown" in author_groups


def test_get_contributing_papers(tmp_path, sample_review_log, sample_gap_data):
    """Test getting papers that contribute to a requirement."""
    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"

    with open(review_file, "w") as f:
        json.dump(sample_review_log, f)
    with open(gap_file, "w") as f:
        json.dump(sample_gap_data, f)

    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    papers = analyzer._get_contributing_papers("P1-R1", "Test Pillar")

    assert len(papers) == 3
    assert "paper1.json" in papers
    assert "paper2.json" in papers
    assert "paper3.json" in papers


def test_validation_threshold(tmp_path, sample_gap_data):
    """Test that low diversity scores trigger validation flag."""
    # Create review log with only one institution
    review_log = {
        "paper1.json": {
            "metadata": {"authors": ["Author A"], "affiliation": "MIT"},
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.8,
                            }
                        ],
                    }
                ]
            },
        },
        "paper2.json": {
            "metadata": {"authors": ["Author B"], "affiliation": "MIT"},
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.7,
                            }
                        ],
                    }
                ]
            },
        },
    }

    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"

    with open(review_file, "w") as f:
        json.dump(review_log, f)
    with open(gap_file, "w") as f:
        json.dump(sample_gap_data, f)

    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    report = analyzer.analyze_triangulation()

    # Diversity score should be 1/2 = 0.5, which does NOT trigger validation (threshold is < 0.5)
    req_analysis = report["requirement_analysis"]["P1-R1"]
    assert req_analysis["needs_validation"] is False
    assert req_analysis["diversity_score"] == 0.5


def test_validation_threshold_low_diversity(tmp_path, sample_gap_data):
    """Test that very low diversity scores trigger validation flag."""
    # Create review log with 3 papers from 1 institution
    review_log = {
        "paper1.json": {
            "metadata": {"authors": ["Author A"], "affiliation": "MIT"},
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.8,
                            }
                        ],
                    }
                ]
            },
        },
        "paper2.json": {
            "metadata": {"authors": ["Author B"], "affiliation": "MIT"},
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.7,
                            }
                        ],
                    }
                ]
            },
        },
        "paper3.json": {
            "metadata": {"authors": ["Author C"], "affiliation": "MIT"},
            "judge_analysis": {
                "pillar_contributions": [
                    {
                        "pillar_name": "Test Pillar",
                        "sub_requirements_addressed": [
                            {
                                "requirement_id": "P1-R1",
                                "requirement": "Test Req 1",
                                "alignment_score": 0.6,
                            }
                        ],
                    }
                ]
            },
        },
    }

    review_file = tmp_path / "review.json"
    gap_file = tmp_path / "gap.json"

    with open(review_file, "w") as f:
        json.dump(review_log, f)
    with open(gap_file, "w") as f:
        json.dump(sample_gap_data, f)

    analyzer = TriangulationAnalyzer(str(review_file), str(gap_file))
    report = analyzer.analyze_triangulation()

    # Diversity score should be 1/3 = 0.33, which triggers validation (< 0.5)
    req_analysis = report["requirement_analysis"]["P1-R1"]
    assert req_analysis["needs_validation"] is True
    assert req_analysis["diversity_score"] == 0.33
