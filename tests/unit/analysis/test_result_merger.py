"""
Unit tests for Result Merger Utility.

Tests cover:
- Evidence merging and deduplication
- Completeness recalculation
- Conflict detection and resolution
- Metadata updates
- Idempotency
- Edge cases
"""

import pytest
import json
import copy
from literature_review.analysis.result_merger import (
    ResultMerger,
    MergeResult,
    merge_reports,
)


@pytest.fixture
def base_report():
    """Base gap analysis report."""
    return {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Implement STDP",
                                "completeness_percent": 33.0,
                                "evidence": [
                                    {
                                        "filename": "paper1.pdf",
                                        "claim": "STDP works",
                                        "score": 0.9,
                                    }
                                ],
                            }
                        }
                    }
                }
            }
        },
        "metadata": {
            "version": 1,
            "total_papers": 1,
            "analysis_date": "2025-01-15T10:00:00Z",
        },
    }


@pytest.fixture
def new_report():
    """New gap analysis report with additional evidence."""
    return {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "text": "Implement STDP",
                                "completeness_percent": 33.0,
                                "evidence": [
                                    {
                                        "filename": "paper2.pdf",
                                        "claim": "STDP effective",
                                        "score": 0.85,
                                    }
                                ],
                            }
                        }
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


class TestBasicMerging:
    """Test basic merging functionality."""

    @pytest.mark.unit
    def test_merge_adds_new_evidence(self, base_report, new_report):
        """Test that merge adds new evidence."""
        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        evidence = result.merged_report["pillars"]["Pillar 1"]["requirements"][
            "REQ-001"
        ]["sub_requirements"]["SUB-001"]["evidence"]

        assert len(evidence) == 2
        assert result.statistics["papers_added"] == 1
        assert result.statistics["evidence_added"] == 1

    @pytest.mark.unit
    def test_merge_updates_completeness(self, base_report, new_report):
        """Test that completeness is recalculated."""
        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        sub_req = result.merged_report["pillars"]["Pillar 1"]["requirements"][
            "REQ-001"
        ]["sub_requirements"]["SUB-001"]

        # 2 evidence items = 33% completeness
        assert sub_req["completeness_percent"] == 33.0
        assert result.statistics["completeness_changed"] == 0  # Same as before

    @pytest.mark.unit
    def test_merge_preserves_existing_data(self, base_report, new_report):
        """Test that existing data is not lost."""
        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        # Original evidence should still be there
        evidence = result.merged_report["pillars"]["Pillar 1"]["requirements"][
            "REQ-001"
        ]["sub_requirements"]["SUB-001"]["evidence"]
        filenames = {ev["filename"] for ev in evidence}

        assert "paper1.pdf" in filenames  # Original
        assert "paper2.pdf" in filenames  # New


class TestDeduplication:
    """Test evidence deduplication."""

    @pytest.mark.unit
    def test_merge_deduplicates_papers(self, base_report, new_report):
        """Test that duplicate papers are not added."""
        # Make new report have same paper as base
        new_report["pillars"]["Pillar 1"]["requirements"]["REQ-001"][
            "sub_requirements"
        ]["SUB-001"]["evidence"] = [
            {"filename": "paper1.pdf", "claim": "STDP works", "score": 0.9}
        ]

        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        evidence = result.merged_report["pillars"]["Pillar 1"]["requirements"][
            "REQ-001"
        ]["sub_requirements"]["SUB-001"]["evidence"]

        assert len(evidence) == 1  # No duplicate
        assert result.statistics["papers_added"] == 0
        assert result.statistics["evidence_duplicated"] == 1


class TestConflictResolution:
    """Test conflict detection and resolution."""

    @pytest.mark.unit
    def test_merge_detects_conflicts(self, base_report, new_report):
        """Test conflict detection when same paper has different data."""
        # Same filename, different data
        new_report["pillars"]["Pillar 1"]["requirements"]["REQ-001"][
            "sub_requirements"
        ]["SUB-001"]["evidence"] = [
            {"filename": "paper1.pdf", "claim": "DIFFERENT CLAIM", "score": 0.5}
        ]

        merger = ResultMerger(conflict_resolution="keep_existing")
        result = merger.merge_gap_analysis_results(base_report, new_report)

        assert len(result.conflicts) == 1
        assert result.conflicts[0]["filename"] == "paper1.pdf"

    @pytest.mark.unit
    def test_conflict_resolution_keep_new(self, base_report, new_report):
        """Test keep_new conflict resolution."""
        # Same paper, different score
        new_report["pillars"]["Pillar 1"]["requirements"]["REQ-001"][
            "sub_requirements"
        ]["SUB-001"]["evidence"] = [
            {"filename": "paper1.pdf", "claim": "Updated claim", "score": 0.95}
        ]

        merger = ResultMerger(conflict_resolution="keep_new")
        result = merger.merge_gap_analysis_results(base_report, new_report)

        evidence = result.merged_report["pillars"]["Pillar 1"]["requirements"][
            "REQ-001"
        ]["sub_requirements"]["SUB-001"]["evidence"]

        # Should have new score
        assert evidence[0]["score"] == 0.95
        assert evidence[0]["claim"] == "Updated claim"

    @pytest.mark.unit
    def test_conflict_resolution_keep_existing(self, base_report, new_report):
        """Test keep_existing conflict resolution."""
        # Same paper, different score
        new_report["pillars"]["Pillar 1"]["requirements"]["REQ-001"][
            "sub_requirements"
        ]["SUB-001"]["evidence"] = [
            {"filename": "paper1.pdf", "claim": "Updated claim", "score": 0.95}
        ]

        merger = ResultMerger(conflict_resolution="keep_existing")
        result = merger.merge_gap_analysis_results(base_report, new_report)

        evidence = result.merged_report["pillars"]["Pillar 1"]["requirements"][
            "REQ-001"
        ]["sub_requirements"]["SUB-001"]["evidence"]

        # Should have original score
        assert evidence[0]["score"] == 0.9
        assert evidence[0]["claim"] == "STDP works"


class TestIdempotency:
    """Test idempotency guarantees."""

    @pytest.mark.unit
    def test_merge_idempotency(self, base_report, new_report):
        """Test that merging twice produces same result."""
        merger = ResultMerger()

        # First merge
        result1 = merger.merge_gap_analysis_results(base_report, new_report)

        # Second merge (merge result with new_report again)
        result2 = merger.merge_gap_analysis_results(result1.merged_report, new_report)

        # Second merge should add 0 papers (already in report)
        assert result2.statistics["papers_added"] == 0
        assert result2.statistics["evidence_duplicated"] == 1

    @pytest.mark.unit
    def test_validate_idempotency(self, base_report, new_report):
        """Test idempotency validation method."""
        merger = ResultMerger()

        # Validate idempotency
        is_idempotent = merger.validate_idempotency(base_report, new_report)

        assert is_idempotent is True


class TestMetadata:
    """Test metadata updates."""

    @pytest.mark.unit
    def test_merge_updates_metadata(self, base_report, new_report):
        """Test metadata is updated correctly."""
        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        metadata = result.merged_report["metadata"]

        assert metadata["version"] == 2  # Incremented
        assert metadata["total_papers"] == 2  # 1 + 1
        assert "merge_timestamp" in metadata
        assert "merge_history" in metadata
        assert len(metadata["merge_history"]) == 1

    @pytest.mark.unit
    def test_merge_history_tracking(self, base_report, new_report):
        """Test merge history is tracked."""
        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        history = result.merged_report["metadata"]["merge_history"]

        assert len(history) == 1
        assert history[0]["papers_added"] == 1
        assert history[0]["evidence_added"] == 1
        assert history[0]["version"] == 2

    @pytest.mark.unit
    def test_merge_without_metadata_preservation(self, base_report, new_report):
        """Test merge when metadata preservation is disabled."""
        merger = ResultMerger(preserve_metadata=False)
        result = merger.merge_gap_analysis_results(base_report, new_report)

        # Metadata should not be updated
        metadata = result.merged_report["metadata"]
        assert "merge_timestamp" not in metadata
        assert "merge_history" not in metadata


class TestStructureAdditions:
    """Test adding new pillars, requirements, etc."""

    @pytest.mark.unit
    def test_merge_adds_new_pillar(self, base_report):
        """Test adding a completely new pillar."""
        new_report = {
            "pillars": {
                "Pillar 2": {
                    "requirements": {
                        "REQ-002": {
                            "sub_requirements": {
                                "SUB-001": {
                                    "text": "Hardware acceleration",
                                    "completeness_percent": 0.0,
                                    "evidence": [],
                                }
                            }
                        }
                    }
                }
            },
            "metadata": {},
        }

        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        assert "Pillar 1" in result.merged_report["pillars"]
        assert "Pillar 2" in result.merged_report["pillars"]

    @pytest.mark.unit
    def test_merge_adds_new_requirement(self, base_report):
        """Test adding a new requirement to existing pillar."""
        new_report = {
            "pillars": {
                "Pillar 1": {
                    "requirements": {
                        "REQ-002": {
                            "sub_requirements": {
                                "SUB-001": {
                                    "text": "New requirement",
                                    "completeness_percent": 0.0,
                                    "evidence": [],
                                }
                            }
                        }
                    }
                }
            },
            "metadata": {},
        }

        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        reqs = result.merged_report["pillars"]["Pillar 1"]["requirements"]
        assert "REQ-001" in reqs
        assert "REQ-002" in reqs


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.unit
    def test_empty_report_merge(self, base_report):
        """Test merging with empty report."""
        empty_report = {"pillars": {}, "metadata": {}}

        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, empty_report)

        # Should be unchanged
        assert result.statistics["papers_added"] == 0
        assert len(result.merged_report["pillars"]) == 1

    @pytest.mark.unit
    def test_merge_with_missing_metadata(self, base_report, new_report):
        """Test merge when reports are missing metadata."""
        del base_report["metadata"]
        del new_report["metadata"]

        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        # Should still work and create metadata
        assert "metadata" in result.merged_report
        assert result.merged_report["metadata"]["version"] == 2

    @pytest.mark.unit
    def test_merge_with_no_evidence(self):
        """Test merge when both reports have no evidence."""
        report1 = {
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
            "metadata": {},
        }

        report2 = copy.deepcopy(report1)

        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(report1, report2)

        assert result.statistics["papers_added"] == 0
        assert result.statistics["evidence_added"] == 0


class TestCompletenessCalculation:
    """Test completeness score calculation."""

    @pytest.mark.unit
    def test_calculate_completeness(self):
        """Test completeness calculation."""
        merger = ResultMerger()

        assert merger._calculate_completeness([]) == 0.0
        assert merger._calculate_completeness([{"filename": "p1.pdf"}]) == 33.0
        assert (
            merger._calculate_completeness(
                [{"filename": f"p{i}.pdf"} for i in range(3)]
            )
            == 67.0
        )
        assert (
            merger._calculate_completeness(
                [{"filename": f"p{i}.pdf"} for i in range(5)]
            )
            == 100.0
        )

    @pytest.mark.unit
    def test_completeness_update_on_merge(self, base_report, new_report):
        """Test that completeness updates when evidence count changes."""
        # Add more papers to reach 67% threshold
        new_report["pillars"]["Pillar 1"]["requirements"]["REQ-001"][
            "sub_requirements"
        ]["SUB-001"]["evidence"] = [
            {"filename": "paper2.pdf", "claim": "Test 2", "score": 0.85},
            {"filename": "paper3.pdf", "claim": "Test 3", "score": 0.80},
        ]

        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        sub_req = result.merged_report["pillars"]["Pillar 1"]["requirements"][
            "REQ-001"
        ]["sub_requirements"]["SUB-001"]

        # 3 evidence items = 67% completeness
        assert sub_req["completeness_percent"] == 67.0
        assert result.statistics["completeness_changed"] == 1


class TestConvenienceFunction:
    """Test the merge_reports convenience function."""

    @pytest.mark.unit
    def test_convenience_function_merge_reports(
        self, tmp_path, base_report, new_report
    ):
        """Test convenience function."""
        # Create temp files
        base_path = tmp_path / "base.json"
        new_path = tmp_path / "new.json"
        output_path = tmp_path / "merged.json"

        with open(base_path, "w") as f:
            json.dump(base_report, f)

        with open(new_path, "w") as f:
            json.dump(new_report, f)

        # Merge
        result = merge_reports(str(base_path), str(new_path), str(output_path))

        assert output_path.exists()
        assert result.statistics["papers_added"] == 1

        # Verify merged file
        with open(output_path) as f:
            merged = json.load(f)

        assert (
            len(
                merged["pillars"]["Pillar 1"]["requirements"]["REQ-001"][
                    "sub_requirements"
                ]["SUB-001"]["evidence"]
            )
            == 2
        )


class TestMergeResult:
    """Test MergeResult dataclass."""

    @pytest.mark.unit
    def test_merge_result_has_conflicts_property(self):
        """Test has_conflicts property."""
        result = MergeResult(
            merged_report={},
            statistics={},
            conflicts=[{"filename": "test.pdf"}],
            warnings=[],
        )

        assert result.has_conflicts is True

    @pytest.mark.unit
    def test_merge_result_has_warnings_property(self):
        """Test has_warnings property."""
        result = MergeResult(
            merged_report={}, statistics={}, conflicts=[], warnings=["Test warning"]
        )

        assert result.has_warnings is True

    @pytest.mark.unit
    def test_merge_result_no_conflicts_or_warnings(self):
        """Test when no conflicts or warnings."""
        result = MergeResult(merged_report={}, statistics={}, conflicts=[], warnings=[])

        assert result.has_conflicts is False
        assert result.has_warnings is False


class TestExportMergeReport:
    """Test merge report export."""

    @pytest.mark.unit
    def test_export_merge_report(self, tmp_path, base_report, new_report):
        """Test exporting merge report."""
        merger = ResultMerger()
        result = merger.merge_gap_analysis_results(base_report, new_report)

        export_path = tmp_path / "merge_report.json"
        merger.export_merge_report(result, str(export_path))

        assert export_path.exists()

        with open(export_path) as f:
            export_data = json.load(f)

        assert "statistics" in export_data
        assert "conflicts" in export_data
        assert "warnings" in export_data
        assert "merged_report_preview" in export_data
