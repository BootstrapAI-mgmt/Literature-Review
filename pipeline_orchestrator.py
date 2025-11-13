#!/usr/bin/env python3
"""
Pipeline Orchestrator v1.1 - Checkpoint/Resume Support

Runs the full Literature Review pipeline automatically:
1. Journal-Reviewer → 2. Judge → 3. DRA (conditional) → 4. Sync → 5. Orchestrator

Features:
- Checkpoint/resume capability for interrupted pipelines
- Atomic checkpoint writes to prevent corruption
- Resume from last successful checkpoint or specific stage

Usage:
    python pipeline_orchestrator.py
    python pipeline_orchestrator.py --log-file pipeline.log
    python pipeline_orchestrator.py --config pipeline_config.json
    python pipeline_orchestrator.py --resume
    python pipeline_orchestrator.py --resume-from sync
"""

import subprocess
import sys
import json
import argparse
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class PipelineOrchestrator:
    """Orchestrates the full literature review pipeline with checkpoint/resume support."""

    def __init__(
        self,
        log_file: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        checkpoint_file: Optional[str] = None,
        resume: bool = False,
        resume_from: Optional[str] = None,
    ):
        self.log_file = log_file
        self.config = config or {}
        self.start_time = datetime.now()
        self.checkpoint_file = checkpoint_file or "pipeline_checkpoint.json"
        self.resume = resume
        self.resume_from = resume_from
        self.run_id = self._generate_run_id()
        self.checkpoint_data = self._load_or_create_checkpoint()

    def log(self, message: str, level: str = "INFO"):
        """Log message to console and optionally to file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(log_message + "\n")

    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}"

    def _load_or_create_checkpoint(self) -> Dict[str, Any]:
        """Load existing checkpoint or create new one."""
        if self.resume and os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r") as f:
                    checkpoint = json.load(f)
                self.log(f"Loaded checkpoint from {self.checkpoint_file}", "INFO")
                self.log(f"Previous run: {checkpoint.get('run_id')}", "INFO")
                return checkpoint
            except json.JSONDecodeError as e:
                self.log(f"Failed to load checkpoint: Invalid JSON - {e}", "ERROR")
                self.log("Checkpoint file is corrupted. Please delete it or use a different checkpoint file.", "ERROR")
                self.log(f"To start fresh: rm {self.checkpoint_file}", "ERROR")
                sys.exit(1)
            except Exception as e:
                self.log(f"Failed to load checkpoint: {e}", "ERROR")
                self.log("Starting fresh run", "WARNING")

        # Create new checkpoint
        return {
            "run_id": self.run_id,
            "pipeline_version": "1.1.0",
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "status": "in_progress",
            "stages": {},
            "config": self.config,
        }

    def _write_checkpoint(self):
        """Atomically write checkpoint to file."""
        self.checkpoint_data["last_updated"] = datetime.now().isoformat()

        # Atomic write: write to temp file, then rename
        temp_file = f"{self.checkpoint_file}.tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump(self.checkpoint_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Ensure written to disk

            # Atomic rename
            os.replace(temp_file, self.checkpoint_file)
        except Exception as e:
            self.log(f"Failed to write checkpoint: {e}", "ERROR")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def _should_run_stage(self, stage_name: str) -> bool:
        """Determine if stage should run based on checkpoint."""
        if not self.resume:
            return True

        # If resuming from specific stage, check if we've reached it
        if self.resume_from:
            stages_order = ["journal_reviewer", "judge", "dra", "judge_dra", "sync", "orchestrator"]
            try:
                resume_index = stages_order.index(self.resume_from)
                current_index = stages_order.index(stage_name)
                return current_index >= resume_index
            except ValueError:
                self.log(f"Invalid stage name: {self.resume_from or stage_name}", "ERROR")
                return True

        # Check checkpoint status
        stage_data = self.checkpoint_data.get("stages", {}).get(stage_name, {})
        status = stage_data.get("status")

        if status == "completed":
            self.log(f"Skipping {stage_name} (already completed)", "INFO")
            return False
        elif status == "in_progress":
            self.log(f"Re-running {stage_name} (was interrupted)", "INFO")
            return True
        else:
            return True

    def _mark_stage_started(self, stage_name: str):
        """Mark stage as started in checkpoint."""
        if stage_name not in self.checkpoint_data["stages"]:
            self.checkpoint_data["stages"][stage_name] = {}

        self.checkpoint_data["stages"][stage_name].update(
            {"status": "in_progress", "started_at": datetime.now().isoformat()}
        )
        self._write_checkpoint()

    def _mark_stage_completed(self, stage_name: str, duration: float, exit_code: int):
        """Mark stage as completed in checkpoint."""
        self.checkpoint_data["stages"][stage_name].update(
            {
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "duration_seconds": int(duration),
                "exit_code": exit_code,
            }
        )
        self._write_checkpoint()

    def _mark_stage_failed(self, stage_name: str, error: str):
        """Mark stage as failed in checkpoint."""
        self.checkpoint_data["stages"][stage_name].update(
            {
                "status": "failed",
                "failed_at": datetime.now().isoformat(),
                "error": error[:500],  # Truncate error to avoid large checkpoint files
            }
        )
        self._write_checkpoint()

    def _mark_stage_skipped(self, stage_name: str, reason: str):
        """Mark stage as skipped in checkpoint."""
        self.checkpoint_data["stages"][stage_name] = {
            "status": "skipped",
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
        self._write_checkpoint()

    def run_stage(self, stage_name: str, script: str, description: str, required: bool = True, use_module: bool = False) -> bool:
        """
        Run a pipeline stage with checkpoint support.

        Args:
            stage_name: Unique stage identifier (e.g., 'journal_reviewer')
            script: Python script path or module name
            description: Human-readable stage description
            required: If True, exit on failure; if False, continue
            use_module: If True, use -m to run as module; if False, run as script

        Returns:
            True if successful, False otherwise
        """
        # Check if stage should run based on checkpoint
        if not self._should_run_stage(stage_name):
            return True  # Already completed

        self.log(f"Starting stage: {description}", "INFO")
        self._mark_stage_started(stage_name)

        stage_start = datetime.now()

        try:
            # Build command based on execution type
            if use_module:
                cmd = [sys.executable, "-m", script]
            else:
                cmd = [sys.executable, script]
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.config.get("stage_timeout", 3600)
            )

            duration = (datetime.now() - stage_start).total_seconds()

            if result.returncode == 0:
                self.log(f"✅ Stage complete: {description}", "SUCCESS")
                self._mark_stage_completed(stage_name, duration, result.returncode)
                return True
            else:
                self.log(f"❌ Stage failed: {description}", "ERROR")
                self.log(f"Error output:\n{result.stderr}", "ERROR")
                self._mark_stage_failed(stage_name, result.stderr)

                if required:
                    self.log("Pipeline halted due to required stage failure", "ERROR")
                    sys.exit(1)
                return False

        except subprocess.TimeoutExpired:
            self.log(f"⏱️ Stage timeout: {description}", "ERROR")
            self._mark_stage_failed(stage_name, "Timeout exceeded")
            if required:
                sys.exit(1)
            return False
        except Exception as e:
            self.log(f"💥 Stage exception: {description} - {e}", "ERROR")
            self._mark_stage_failed(stage_name, str(e))
            if required:
                sys.exit(1)
            return False

    def check_for_rejections(self) -> bool:
        """Check if version history has rejected claims."""
        version_history_path = self.config.get("version_history_path", "review_version_history.json")

        try:
            with open(version_history_path, "r") as f:
                history = json.load(f)

            for filename, versions in history.items():
                if not versions:
                    continue
                latest = versions[-1].get("review", {})
                for claim in latest.get("Requirement(s)", []):
                    if claim.get("status") == "rejected":
                        self.log(f"Found rejection in {filename}", "INFO")
                        return True

            return False

        except FileNotFoundError:
            self.log(f"Version history not found: {version_history_path}", "WARNING")
            return False
        except Exception as e:
            self.log(f"Error checking rejections: {e}", "WARNING")
            return False

    def run(self):
        """Execute the full pipeline with checkpoint support."""
        self.log("=" * 70, "INFO")
        self.log("Literature Review Pipeline Orchestrator v1.1", "INFO")
        if self.resume:
            self.log(f"RESUMING from checkpoint: {self.checkpoint_file}", "INFO")
            if self.resume_from:
                self.log(f"Starting from stage: {self.resume_from}", "INFO")
        self.log("=" * 70, "INFO")

        # Stage 1: Journal Reviewer
        self.run_stage("journal_reviewer", "literature_review.reviewers.journal_reviewer", 
                       "Stage 1: Initial Paper Review", use_module=True)

        # Stage 2: Judge
        self.run_stage("judge", "literature_review.analysis.judge", 
                       "Stage 2: Judge Claims", use_module=True)

        # Stage 3: DRA (conditional)
        if self._should_run_stage("dra"):
            if self.check_for_rejections():
                self.log("Rejections detected, running DRA appeal process", "INFO")
                self.run_stage("dra", "literature_review.analysis.requirements", 
                               "Stage 3: DRA Appeal", use_module=True)
                self.run_stage("judge_dra", "literature_review.analysis.judge", 
                               "Stage 3b: Re-judge DRA Claims", use_module=True)
            else:
                self.log("No rejections found, skipping DRA", "INFO")
                self._mark_stage_skipped("dra", "no_rejections")

        # Stage 4: Sync to Database
        self.run_stage("sync", "scripts/sync_history_to_db.py", 
                       "Stage 4: Sync to Database", use_module=False)

        # Stage 5: Orchestrator
        self.run_stage("orchestrator", "literature_review.orchestrator", 
                       "Stage 5: Gap Analysis & Convergence", use_module=True)

        # Mark pipeline complete
        self.checkpoint_data["status"] = "completed"
        self.checkpoint_data["completed_at"] = datetime.now().isoformat()
        self._write_checkpoint()

        # Summary
        elapsed = datetime.now() - self.start_time
        self.log("=" * 70, "INFO")
        self.log("🎉 Pipeline Complete!", "SUCCESS")
        self.log(f"Total time: {elapsed}", "INFO")
        self.log("=" * 70, "INFO")


def main():
    parser = argparse.ArgumentParser(description="Run the full Literature Review pipeline automatically")
    parser.add_argument("--log-file", type=str, help="Path to log file (default: no file logging)")
    parser.add_argument("--config", type=str, help="Path to configuration JSON file")
    parser.add_argument(
        "--checkpoint-file",
        type=str,
        default="pipeline_checkpoint.json",
        help="Path to checkpoint file (default: pipeline_checkpoint.json)",
    )
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument(
        "--resume-from",
        type=str,
        choices=["journal_reviewer", "judge", "dra", "sync", "orchestrator"],
        help="Resume from specific stage",
    )

    args = parser.parse_args()

    # Load config if provided
    config = {}
    if args.config and Path(args.config).exists():
        with open(args.config) as f:
            config = json.load(f)

    # Run pipeline
    orchestrator = PipelineOrchestrator(
        log_file=args.log_file,
        config=config,
        checkpoint_file=args.checkpoint_file,
        resume=args.resume,
        resume_from=args.resume_from,
    )
    orchestrator.run()


if __name__ == "__main__":
    main()
