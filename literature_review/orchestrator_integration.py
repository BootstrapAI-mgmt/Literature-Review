"""
Orchestrator Integration Module

Coordinates Journal-Reviewer, Deep-Reviewer, Judge, and CSV sync.
Implements evidence triangulation across multiple reviewers.
Provides programmatic interface for dashboard integration.

Version: 2.0 (Phase 1: Core Pipeline Integration)
"""

import json
import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict


def run_pipeline_for_job(
    job_id: str,
    pillar_selections: List[str],
    run_mode: str,
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
    log_callback: Optional[Callable] = None,
    prompt_callback: Optional[Callable] = None
) -> Dict:
    """
    Execute orchestrator pipeline for a dashboard job
    
    Args:
        job_id: Unique job identifier
        pillar_selections: List of pillar names or ["ALL"]
        run_mode: "ONCE" (single pass) or "DEEP_LOOP" (iterative)
        output_dir: Custom output directory path (optional)
        progress_callback: Function to call with progress updates
        log_callback: Function to call with log messages
        prompt_callback: Async function to call for user prompts
    
    Returns:
        Dict with execution results and output file paths
    """
    from literature_review.orchestrator import main as orchestrator_main, OrchestratorConfig
    
    # Determine output directory
    if output_dir:
        # Use custom output directory from job config
        actual_output_dir = Path(output_dir)
    else:
        # Create job-specific output directory (legacy behavior)
        actual_output_dir = Path("workspace") / "jobs" / job_id / "outputs" / "gap_analysis_output"
    
    actual_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure orchestrator
    config = OrchestratorConfig(
        job_id=job_id,
        analysis_target=pillar_selections,
        run_mode=run_mode,
        skip_user_prompts=(prompt_callback is None),
        progress_callback=progress_callback,
        log_callback=log_callback,
        prompt_callback=prompt_callback,
        output_dir=str(actual_output_dir)
    )
    
    # Execute pipeline
    try:
        if log_callback:
            log_callback(f"Starting orchestrator for job {job_id}")
            log_callback(f"Output directory: {actual_output_dir}")
        
        if progress_callback:
            progress_callback("Initializing pipeline")
        
        result = orchestrator_main(config)
        
        if progress_callback:
            progress_callback("Pipeline execution completed")
        
        # Collect output file paths from actual output directory
        output_files = []
        
        if actual_output_dir.exists():
            output_files = [str(f) for f in actual_output_dir.glob("**/*") if f.is_file()]
        
        return {
            "status": "success",
            "output_dir": str(actual_output_dir),
            "output_files": output_files,
            "result": result
        }
    except Exception as e:
        if log_callback:
            log_callback(f"Pipeline failed: {str(e)}")
        
        return {
            "status": "failed",
            "error": str(e)
        }


class Orchestrator:
    """
    Orchestrates the literature review workflow.

    Coordinates:
    - Journal-Reviewer: Initial paper analysis
    - Deep-Reviewer: Detailed evidence extraction
    - Judge: Claim validation
    - CSV Sync: Database updates
    - Evidence Triangulation: Cross-reviewer aggregation
    """

    def __init__(
        self,
        version_history_path: str,
        csv_database_path: Optional[str] = None,
        max_iterations: int = 3,
        enable_quality_scoring: bool = True,
        enable_triangulation: bool = True,
        enable_consensus_review: bool = True,
        quality_threshold: float = 3.5,
    ):
        """
        Initialize Orchestrator.

        Args:
            version_history_path: Path to review_version_history.json
            csv_database_path: Path to CSV database (optional)
            max_iterations: Maximum convergence loop iterations (default: 3)
            enable_quality_scoring: Enable evidence quality scoring (default: True)
            enable_triangulation: Enable evidence triangulation (default: True)
            enable_consensus_review: Enable consensus review for borderline claims (default: True)
            quality_threshold: Composite score threshold for approval (default: 3.5)
        """
        self.version_history_path = version_history_path
        self.csv_database_path = csv_database_path
        self.max_iterations = max_iterations
        self.enable_quality_scoring = enable_quality_scoring
        self.enable_triangulation = enable_triangulation
        self.enable_consensus_review = enable_consensus_review
        self.quality_threshold = quality_threshold

    def process_paper(self, pdf_path: str) -> bool:
        """
        Process a paper through the full workflow.

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if successful, False otherwise
        """
        try:
            # This is a simplified implementation for testing
            # In production, this would call the actual reviewer modules

            # For now, just verify the file exists
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF not found: {pdf_path}")

            # Load version history
            with open(self.version_history_path, "r") as f:
                version_history = json.load(f)

            # Create a basic entry if processing is successful
            filename = os.path.basename(pdf_path)

            if filename not in version_history:
                version_history[filename] = []

            # Add a version entry (simulated)
            version_history[filename].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "review": {
                        "FILENAME": filename,
                        "TITLE": "Processed Paper",
                        "source": "journal",
                        "Requirement(s)": [],
                    },
                }
            )

            # Save updated history
            with open(self.version_history_path, "w") as f:
                json.dump(version_history, f, indent=2)

            return True

        except Exception as e:
            print(f"Error processing paper: {e}")
            return False

    def run_judge(self) -> bool:
        """
        Run Judge on pending claims in version history.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load version history
            with open(self.version_history_path, "r") as f:
                version_history = json.load(f)

            # Process pending claims
            for filename, versions in version_history.items():
                if not versions:
                    continue

                latest_version = versions[-1]
                claims = latest_version.get("review", {}).get("Requirement(s)", [])

                # Find pending claims
                has_pending = any(claim.get("status") == "pending_judge_review" for claim in claims)

                if has_pending:
                    # Create a new version with updated statuses
                    import copy

                    new_version = {
                        "timestamp": datetime.now().isoformat(),
                        "review": copy.deepcopy(latest_version["review"]),
                    }

                    # Update claim statuses (simplified - real implementation would call Judge)
                    for claim in new_version["review"]["Requirement(s)"]:
                        if claim.get("status") == "pending_judge_review":
                            # Simple logic: approve if has evidence
                            if claim.get("evidence"):
                                claim["status"] = "approved"
                                claim["judge_notes"] = "Approved by automated judge"
                            else:
                                claim["status"] = "rejected"
                                claim["judge_notes"] = "Rejected - insufficient evidence"

                    versions.append(new_version)

            # Save updated history
            with open(self.version_history_path, "w") as f:
                json.dump(version_history, f, indent=2)

            return True

        except (json.JSONDecodeError, ValueError) as e:
            raise e
        except Exception as e:
            print(f"Error running judge: {e}")
            return False

    def sync_to_csv(self) -> bool:
        """
        Sync approved claims to CSV database.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.csv_database_path:
                raise ValueError("CSV database path not set")

            # Load version history
            with open(self.version_history_path, "r") as f:
                version_history = json.load(f)

            # Collect approved claims
            rows = []
            for filename, versions in version_history.items():
                if not versions:
                    continue

                latest_version = versions[-1]
                review = latest_version.get("review", {})

                # Check if there are approved claims
                approved_claims = [
                    claim for claim in review.get("Requirement(s)", []) if claim.get("status") == "approved"
                ]

                if approved_claims:
                    row = {
                        "FILENAME": review.get("FILENAME", filename),
                        "TITLE": review.get("TITLE", ""),
                        "PUBLICATION_YEAR": review.get("PUBLICATION_YEAR", ""),
                        "Requirement(s)": json.dumps(approved_claims),
                    }
                    rows.append(row)

            # Create DataFrame and save to CSV
            if rows:
                df = pd.DataFrame(rows)
                df.to_csv(self.csv_database_path, index=False)

            return True

        except Exception as e:
            print(f"Error syncing to CSV: {e}")
            return False

    def triangulate_evidence(self) -> bool:
        """
        Perform evidence triangulation across Journal and Deep reviewers.

        Aggregates claims from multiple reviewers for the same sub-requirements,
        computes consensus scores, and detects conflicts.

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.version_history_path, "r") as f:
                version_history = json.load(f)

            for filename, versions in version_history.items():
                # Group claims by sub_requirement
                claims_by_subreq = {}

                for version in versions:
                    claims = version.get("review", {}).get("Requirement(s)", [])
                    for claim in claims:
                        subreq = claim.get("sub_requirement")
                        if subreq:
                            if subreq not in claims_by_subreq:
                                claims_by_subreq[subreq] = []
                            claims_by_subreq[subreq].append(claim)

                # Triangulate claims with multiple sources
                triangulation_data = {"cross_references": [], "conflicts_detected": False, "conflict_resolution": {}}

                for subreq, claims in claims_by_subreq.items():
                    if len(claims) > 1:
                        # Multiple reviewers covered same sub-req
                        # Extract quality scores
                        scores = []
                        for c in claims:
                            quality = c.get("evidence_quality", {})
                            composite = quality.get("composite_score", 0)
                            if composite > 0:
                                scores.append(composite)

                        if not scores:
                            continue

                        # Add cross-reference
                        triangulation_data["cross_references"].append(
                            {
                                "sub_requirement": subreq,
                                "num_reviewers": len(claims),
                                "sources": [c.get("source", "unknown") for c in claims],
                            }
                        )

                        # Check for conflict (significant score difference)
                        if max(scores) - min(scores) > 1.5:
                            triangulation_data["conflicts_detected"] = True
                            triangulation_data["conflict_resolution"] = {
                                "sub_requirement": subreq,
                                "strategy": "take_higher_score",
                                "resolved_composite_score": max(scores),
                            }

                        # Compute consensus
                        triangulation_data["consensus_composite_score"] = sum(scores) / len(scores)

                        # Combine provenance
                        all_pages = []
                        for c in claims:
                            provenance = c.get("provenance", {})
                            pages = provenance.get("page_numbers", [])
                            if isinstance(pages, list):
                                all_pages.extend(pages)
                            # Also check for single page_number field
                            elif c.get("page_number"):
                                all_pages.append(c.get("page_number"))

                        triangulation_data["combined_provenance"] = {"page_numbers": sorted(list(set(all_pages)))}

                # Append triangulation analysis to version history
                if triangulation_data["cross_references"] or triangulation_data["conflicts_detected"]:
                    versions.append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "review": {
                                "FILENAME": filename,
                                "TITLE": versions[-1].get("review", {}).get("TITLE", ""),
                                "triangulation_analysis": triangulation_data,
                            },
                        }
                    )

            # Save updated version history
            with open(self.version_history_path, "w") as f:
                json.dump(version_history, f, indent=2)

            return True

        except Exception as e:
            print(f"Error in triangulation: {e}")
            return False

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

    def run_journal_reviewer(self, pdf_file: str) -> bool:
        """
        Run Journal-Reviewer on a paper.

        Args:
            pdf_file: Path to PDF file

        Returns:
            True if successful
        """
        # This is a simplified implementation for testing
        # In production, this would call the actual Journal-Reviewer module
        return self.process_paper(pdf_file)

    def run_deep_reviewer(self, pdf_file: str) -> bool:
        """
        Run Deep-Reviewer on a paper.

        Args:
            pdf_file: Path to PDF file

        Returns:
            True if successful
        """
        try:
            import copy

            # Load version history
            with open(self.version_history_path, "r") as f:
                version_history = json.load(f)

            filename = os.path.basename(pdf_file)

            if filename not in version_history or not version_history[filename]:
                return False

            # Get latest version
            latest = version_history[filename][-1]["review"]

            # Create a new version with deep review enhancements
            new_version = {
                "timestamp": datetime.now().isoformat(),
                "review": {
                    "FILENAME": filename,
                    "TITLE": latest.get("TITLE", "Deep Review"),
                    "source": "deep",
                    "Requirement(s)": [],
                },
            }

            # Enhance existing claims with deeper evidence (simplified)
            for claim in latest.get("Requirement(s)", []):
                enhanced_claim = copy.deepcopy(claim)

                # Add deeper evidence quality scores if enabled
                if self.enable_quality_scoring and "evidence_quality" not in enhanced_claim:
                    enhanced_claim["evidence_quality"] = {
                        "strength_score": 3,
                        "rigor_score": 3,
                        "relevance_score": 3,
                        "directness": 3,
                        "reproducibility_score": 3,
                        "composite_score": 3.0,
                    }

                # Update source to indicate deep review
                enhanced_claim["source"] = "deep"
                new_version["review"]["Requirement(s)"].append(enhanced_claim)

            version_history[filename].append(new_version)

            # Save updated history
            with open(self.version_history_path, "w") as f:
                json.dump(version_history, f, indent=2)

            return True

        except Exception as e:
            print(f"Error running deep reviewer: {e}")
            return False

    def check_convergence(self) -> bool:
        """
        Check if convergence criteria met.

        Returns:
            True if converged (all claims finalized or quality threshold met)
        """
        try:
            with open(self.version_history_path, "r") as f:
                version_history = json.load(f)

            # Track if we found any claims at all
            total_claims = 0

            for filename, versions in version_history.items():
                if not versions:
                    continue

                latest = versions[-1]["review"]
                claims = latest.get("Requirement(s)", [])

                if not claims:
                    continue

                total_claims += len(claims)

                for claim in claims:
                    status = claim.get("status")
                    quality = claim.get("evidence_quality", {})
                    composite = quality.get("composite_score", 0)

                    # Not converged if any claims still pending
                    if status == "pending_judge_review":
                        return False

                    # Not converged if quality below threshold for approved claims
                    if self.enable_quality_scoring and status == "approved":
                        if composite > 0 and composite < self.quality_threshold:
                            return False

            # If no claims exist, not converged (need to continue processing)
            if total_claims == 0:
                return False

            return True

        except Exception as e:
            print(f"Error checking convergence: {e}")
            return False

    def log_iteration_metadata(self, iteration: int, converged: bool):
        """
        Log metadata for current iteration.

        Args:
            iteration: Current iteration number
            converged: Whether convergence was reached
        """
        try:
            with open(self.version_history_path, "r") as f:
                version_history = json.load(f)

            # Add iteration number to latest versions
            for filename, versions in version_history.items():
                if versions:
                    latest = versions[-1]
                    if "review" in latest:
                        latest["review"]["iteration"] = iteration
                        latest["review"]["converged"] = converged

            # Save updated history
            with open(self.version_history_path, "w") as f:
                json.dump(version_history, f, indent=2)

        except Exception as e:
            print(f"Error logging iteration metadata: {e}")

    def log_convergence_metrics(self, iteration: int, converged: bool):
        """
        Log final convergence metrics.

        Args:
            iteration: Final iteration number
            converged: Whether convergence was reached
        """
        try:
            with open(self.version_history_path, "r") as f:
                version_history = json.load(f)

            # Determine termination reason
            if converged:
                termination_reason = "consensus_reached"
            elif iteration >= self.max_iterations:
                termination_reason = "max_iterations"
            else:
                termination_reason = "unknown"

            # Calculate quality score delta (if applicable)
            quality_score_delta = 0.0

            for filename, versions in version_history.items():
                if len(versions) >= 2:
                    # Get first and last quality scores
                    first_scores = []
                    last_scores = []

                    for claim in versions[0]["review"].get("Requirement(s)", []):
                        quality = claim.get("evidence_quality", {})
                        composite = quality.get("composite_score", 0)
                        if composite > 0:
                            first_scores.append(composite)

                    for claim in versions[-1]["review"].get("Requirement(s)", []):
                        quality = claim.get("evidence_quality", {})
                        composite = quality.get("composite_score", 0)
                        if composite > 0:
                            last_scores.append(composite)

                    if first_scores and last_scores:
                        avg_first = sum(first_scores) / len(first_scores)
                        avg_last = sum(last_scores) / len(last_scores)
                        quality_score_delta = abs(avg_last - avg_first)

                # Add convergence metrics to final version
                if versions:
                    latest = versions[-1]
                    if "review" in latest:
                        latest["review"]["convergence_metrics"] = {
                            "iteration_count": iteration,
                            "termination_reason": termination_reason,
                            "quality_score_delta": quality_score_delta,
                        }

            # Save updated history
            with open(self.version_history_path, "w") as f:
                json.dump(version_history, f, indent=2)

        except Exception as e:
            print(f"Error logging convergence metrics: {e}")
