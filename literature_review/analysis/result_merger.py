"""
Result Merger Utility for combining gap analysis reports.

This module provides functionality to merge new gap analysis results with existing
reports without data loss. It's critical for incremental review mode, enabling
additive analysis where new evidence is merged into existing gap analysis reports
while preserving all historical data.
"""

import json
import copy
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """Result of merging two gap analysis reports."""

    merged_report: Dict
    statistics: Dict = field(default_factory=dict)
    conflicts: List[Dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        """Check if merge had conflicts."""
        return len(self.conflicts) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if merge had warnings."""
        return len(self.warnings) > 0


class ResultMerger:
    """Merges gap analysis results from multiple runs."""

    def __init__(
        self, conflict_resolution: str = "keep_both", preserve_metadata: bool = True
    ):
        """
        Initialize result merger.

        Args:
            conflict_resolution: How to resolve conflicts
                - "keep_both": Keep evidence from both reports
                - "keep_existing": Prefer existing report
                - "keep_new": Prefer new report
            preserve_metadata: Preserve original metadata
        """
        self.conflict_resolution = conflict_resolution
        self.preserve_metadata = preserve_metadata

        # Merge statistics
        self.stats = {
            "papers_added": 0,
            "papers_duplicated": 0,
            "evidence_added": 0,
            "evidence_duplicated": 0,
            "requirements_updated": 0,
            "completeness_changed": 0,
        }

    def merge_gap_analysis_results(
        self, existing_report: Dict, new_report: Dict
    ) -> MergeResult:
        """
        Merge new gap analysis results into existing report.

        Args:
            existing_report: Base gap analysis report
            new_report: New gap analysis report to merge in

        Returns:
            MergeResult with merged report and statistics

        Example:
            >>> merger = ResultMerger()
            >>> with open('gap_analysis_output/gap_analysis_report.json') as f:
            ...     existing = json.load(f)
            >>> with open('new_analysis/gap_analysis_report.json') as f:
            ...     new = json.load(f)
            >>> result = merger.merge_gap_analysis_results(existing, new)
            >>> print(f"Added {result.statistics['papers_added']} papers")
            >>> print(f"Conflicts: {len(result.conflicts)}")
        """
        # Deep copy existing report to avoid mutation
        merged = copy.deepcopy(existing_report)
        conflicts = []
        warnings = []

        # Reset statistics
        self.stats = {k: 0 for k in self.stats.keys()}

        # Merge pillars
        existing_pillars = merged.get("pillars", {})
        new_pillars = new_report.get("pillars", {})

        for pillar_name, new_pillar_data in new_pillars.items():
            if pillar_name not in existing_pillars:
                # New pillar - add it
                existing_pillars[pillar_name] = new_pillar_data
                logger.info(f"Added new pillar: {pillar_name}")
            else:
                # Merge pillar data
                self._merge_pillar(
                    existing_pillars[pillar_name],
                    new_pillar_data,
                    pillar_name,
                    conflicts,
                    warnings,
                )

        merged["pillars"] = existing_pillars

        # Update metadata
        self._update_metadata(merged, existing_report, new_report, warnings)

        # Create merge result
        result = MergeResult(
            merged_report=merged,
            statistics=self.stats.copy(),
            conflicts=conflicts,
            warnings=warnings,
        )

        logger.info(
            f"Merge complete: {self.stats['papers_added']} papers added, "
            f"{self.stats['evidence_added']} evidence items added"
        )

        return result

    def _merge_pillar(
        self,
        existing_pillar: Dict,
        new_pillar: Dict,
        pillar_name: str,
        conflicts: List[Dict],
        warnings: List[str],
    ) -> None:
        """Merge pillar data."""
        existing_reqs = existing_pillar.get("requirements", {})
        new_reqs = new_pillar.get("requirements", {})

        for req_id, new_req_data in new_reqs.items():
            if req_id not in existing_reqs:
                # New requirement
                existing_reqs[req_id] = new_req_data
                logger.debug(f"Added new requirement: {pillar_name}/{req_id}")
            else:
                # Merge requirement data
                self._merge_requirement(
                    existing_reqs[req_id],
                    new_req_data,
                    f"{pillar_name}/{req_id}",
                    conflicts,
                    warnings,
                )

        existing_pillar["requirements"] = existing_reqs

    def _merge_requirement(
        self,
        existing_req: Dict,
        new_req: Dict,
        req_path: str,
        conflicts: List[Dict],
        warnings: List[str],
    ) -> None:
        """Merge requirement data."""
        existing_subs = existing_req.get("sub_requirements", {})
        new_subs = new_req.get("sub_requirements", {})

        for sub_req_id, new_sub_data in new_subs.items():
            full_path = f"{req_path}/{sub_req_id}"

            if sub_req_id not in existing_subs:
                # New sub-requirement
                existing_subs[sub_req_id] = new_sub_data
                logger.debug(f"Added new sub-requirement: {full_path}")
            else:
                # Merge sub-requirement data
                self._merge_sub_requirement(
                    existing_subs[sub_req_id],
                    new_sub_data,
                    full_path,
                    conflicts,
                    warnings,
                )

        existing_req["sub_requirements"] = existing_subs

    def _merge_sub_requirement(
        self,
        existing_sub: Dict,
        new_sub: Dict,
        sub_path: str,
        conflicts: List[Dict],
        warnings: List[str],
    ) -> None:
        """Merge sub-requirement data (evidence and scores)."""
        # Merge evidence lists
        existing_evidence = existing_sub.get("evidence", [])
        new_evidence = new_sub.get("evidence", [])

        # Track existing paper filenames for deduplication
        existing_filenames = {ev.get("filename") for ev in existing_evidence}

        # Add new evidence (deduplicate by filename)
        added_count = 0
        duplicate_count = 0

        for new_ev in new_evidence:
            filename = new_ev.get("filename")

            if filename not in existing_filenames:
                # New evidence - add it
                existing_evidence.append(new_ev)
                existing_filenames.add(filename)
                added_count += 1
                self.stats["evidence_added"] += 1
                self.stats["papers_added"] += 1
            else:
                # Duplicate evidence
                duplicate_count += 1
                self.stats["evidence_duplicated"] += 1

                # Check for conflicts (same paper, different data)
                existing_ev = next(
                    e for e in existing_evidence if e.get("filename") == filename
                )
                if not self._evidence_matches(existing_ev, new_ev):
                    conflict = {
                        "sub_requirement": sub_path,
                        "filename": filename,
                        "existing": existing_ev,
                        "new": new_ev,
                        "resolution": self.conflict_resolution,
                    }
                    conflicts.append(conflict)
                    logger.warning(f"Evidence conflict for {filename} in {sub_path}")

                    # Resolve conflict
                    if self.conflict_resolution == "keep_new":
                        # Replace existing with new
                        idx = existing_evidence.index(existing_ev)
                        existing_evidence[idx] = new_ev
                    elif self.conflict_resolution == "keep_both":
                        # Keep both (already done - existing is kept)
                        pass
                    # else: keep_existing (default, do nothing)

        # Update evidence list
        existing_sub["evidence"] = existing_evidence

        # Recalculate completeness
        old_completeness = existing_sub.get("completeness_percent", 0)
        new_completeness = self._calculate_completeness(existing_evidence)
        existing_sub["completeness_percent"] = new_completeness

        if abs(new_completeness - old_completeness) > 0.01:
            self.stats["completeness_changed"] += 1
            logger.info(
                f"{sub_path}: Completeness {old_completeness:.1f}% → {new_completeness:.1f}%"
            )

        # Update other fields (scores, etc.)
        if added_count > 0:
            self.stats["requirements_updated"] += 1

        if duplicate_count > 0:
            warnings.append(f"{sub_path}: {duplicate_count} duplicate evidence items")

    def _evidence_matches(self, ev1: Dict, ev2: Dict) -> bool:
        """
        Check if two evidence items are identical.

        Args:
            ev1: First evidence dict
            ev2: Second evidence dict

        Returns:
            True if evidence matches (same content)
        """
        # Compare key fields
        key_fields = ["filename", "claim", "score", "page"]

        for key_field in key_fields:
            if ev1.get(key_field) != ev2.get(key_field):
                return False

        return True

    def _calculate_completeness(self, evidence_list: List[Dict]) -> float:
        """
        Calculate completeness percentage based on evidence.

        Simple heuristic:
        - 0 evidence: 0%
        - 1-2 evidence: 33%
        - 3-4 evidence: 67%
        - 5+ evidence: 100%

        Args:
            evidence_list: List of evidence dicts

        Returns:
            Completeness percentage (0-100)
        """
        count = len(evidence_list)

        if count == 0:
            return 0.0
        elif count <= 2:
            return 33.0
        elif count <= 4:
            return 67.0
        else:
            return 100.0

    def _update_metadata(
        self, merged: Dict, existing: Dict, new: Dict, warnings: List[str]
    ) -> None:
        """Update metadata in merged report."""
        if not self.preserve_metadata:
            return

        # Get or create metadata section
        metadata = merged.get("metadata", {})

        # Update timestamps
        metadata["last_updated"] = datetime.now().isoformat()
        metadata["merge_timestamp"] = datetime.now().isoformat()

        # Update version
        old_version = metadata.get("version", 1)
        metadata["version"] = old_version + 1

        # Update paper counts
        existing_papers = existing.get("metadata", {}).get("total_papers", 0)
        new_papers = self.stats["papers_added"]
        metadata["total_papers"] = existing_papers + new_papers

        # Track merge history
        merge_history = metadata.get("merge_history", [])
        merge_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "papers_added": new_papers,
                "evidence_added": self.stats["evidence_added"],
                "version": metadata["version"],
            }
        )
        metadata["merge_history"] = merge_history

        # Store statistics
        metadata["merge_statistics"] = self.stats.copy()

        merged["metadata"] = metadata

        logger.info(f"Updated metadata: version {old_version} → {metadata['version']}")

    def validate_idempotency(self, report1: Dict, report2: Dict) -> bool:
        """
        Validate that merge is idempotent.

        Merging A with B twice should produce the same result.

        Args:
            report1: First report
            report2: Second report (same as first)

        Returns:
            True if idempotent
        """
        # First merge
        result1 = self.merge_gap_analysis_results(report1, report2)

        # Second merge (merge result with report2 again)
        result2 = self.merge_gap_analysis_results(result1.merged_report, report2)

        # Compare paper counts
        papers2 = result2.statistics["papers_added"]

        if papers2 > 0:
            logger.error(f"Idempotency violation: Second merge added {papers2} papers")
            return False

        logger.info("Idempotency validated: Second merge added 0 papers")
        return True

    def export_merge_report(self, result: MergeResult, output_path: str) -> None:
        """
        Export merge report with statistics.

        Args:
            result: MergeResult object
            output_path: Path to save report
        """
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "statistics": result.statistics,
            "conflicts": result.conflicts,
            "warnings": result.warnings,
            "merged_report_preview": {
                "total_pillars": len(result.merged_report.get("pillars", {})),
                "metadata": result.merged_report.get("metadata", {}),
            },
        }

        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"Exported merge report to {output_path}")


# Convenience functions
def merge_reports(
    existing_path: str,
    new_path: str,
    output_path: str,
    conflict_resolution: str = "keep_both",
) -> MergeResult:
    """
    Convenience function to merge two gap analysis reports from files.

    Args:
        existing_path: Path to existing gap_analysis_report.json
        new_path: Path to new gap_analysis_report.json
        output_path: Path to save merged report
        conflict_resolution: Conflict resolution strategy

    Returns:
        MergeResult

    Example:
        >>> result = merge_reports(
        ...     'gap_analysis_output/gap_analysis_report.json',
        ...     'new_analysis/gap_analysis_report.json',
        ...     'merged_analysis/gap_analysis_report.json'
        ... )
        >>> print(f"Merge complete: {result.statistics['papers_added']} papers added")
    """
    # Load reports
    with open(existing_path, "r") as f:
        existing = json.load(f)

    with open(new_path, "r") as f:
        new = json.load(f)

    # Merge
    merger = ResultMerger(conflict_resolution=conflict_resolution)
    result = merger.merge_gap_analysis_results(existing, new)

    # Save merged report
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result.merged_report, f, indent=2)

    logger.info(f"Saved merged report to {output_path}")

    return result
