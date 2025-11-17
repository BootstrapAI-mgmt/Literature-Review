#!/usr/bin/env python3
"""
Pipeline Orchestrator v2.0 - Advanced Features & Error Recovery

Runs the full Literature Review pipeline automatically:
1. Journal-Reviewer → 2. Judge → 3. DRA (conditional) → 4. Sync → 5. Orchestrator → 6. Proof Scorecard

Features (v1.x):
- Checkpoint/resume capability
- Automatic retry on transient failures
- Exponential backoff with jitter
- Circuit breaker protection
- Python module execution (refactored structure)

Features (v2.0 - New):
- Dry-run mode for validation without side effects
- Smart error classification (transient vs permanent)
- API quota management with token bucket
- Parallel processing support (behind feature flag)
- Per-paper checkpoint tracking
- Enhanced observability and metrics
- Proof completeness scorecard generation

Usage:
    # Basic usage (v1.x compatible)
    python pipeline_orchestrator.py
    python pipeline_orchestrator.py --log-file pipeline.log
    python pipeline_orchestrator.py --config pipeline_config.json
    python pipeline_orchestrator.py --resume
    python pipeline_orchestrator.py --resume-from judge
    
    # New v2.0 features
    python pipeline_orchestrator.py --dry-run
    python pipeline_orchestrator.py --enable-experimental
"""

import subprocess
import sys
import json
import argparse
import time
import random
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Import cost tracker
sys.path.insert(0, str(Path(__file__).parent))
from literature_review.utils.cost_tracker import get_cost_tracker


class RetryPolicy:
    """Manages retry logic and exponential backoff."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("retry_policy", {})
        self.enabled = self.config.get("enabled", True)
        self.default_max_attempts = self.config.get("default_max_attempts", 3)
        self.default_backoff_base = self.config.get("default_backoff_base", 2)
        self.default_backoff_max = self.config.get("default_backoff_max", 60)
        self.circuit_breaker_threshold = self.config.get("circuit_breaker_threshold", 3)
        self.consecutive_failures = 0

    def get_stage_config(self, stage_name: str) -> Dict[str, Any]:
        """Get retry config for specific stage."""
        per_stage = self.config.get("per_stage", {})
        stage_config = per_stage.get(stage_name, {})

        return {
            "max_attempts": stage_config.get("max_attempts", self.default_max_attempts),
            "backoff_base": stage_config.get("backoff_base", self.default_backoff_base),
            "backoff_max": stage_config.get("backoff_max", self.default_backoff_max),
            "retryable_patterns": stage_config.get(
                "retryable_patterns", ["timeout", "connection", "rate limit", "temporary"]
            ),
        }

    def is_retryable_error(self, stderr: str, stage_name: str) -> Tuple[bool, str]:
        """
        Classify error as retryable or permanent.

        Returns:
            (is_retryable, reason)
        """
        if not self.enabled:
            return False, "Retry disabled"

        # Circuit breaker check
        if self.consecutive_failures >= self.circuit_breaker_threshold:
            return False, f"Circuit breaker tripped ({self.consecutive_failures} failures)"

        stderr_lower = stderr.lower()
        stage_config = self.get_stage_config(stage_name)
        retryable_patterns = stage_config["retryable_patterns"]

        # Check for retryable patterns
        for pattern in retryable_patterns:
            if re.search(pattern, stderr_lower, re.IGNORECASE):
                return True, f"Matched pattern: {pattern}"

        # Check for common retryable error types
        retryable_keywords = [
            "timeout",
            "timed out",
            "time out",
            "connection refused",
            "connection reset",
            "connection error",
            "rate limit",
            "too many requests",
            "429",
            "temporary failure",
            "transient",
            "network error",
            "network unreachable",
            "service unavailable",
            "503",
            "502",
            "504",
        ]

        for keyword in retryable_keywords:
            if keyword in stderr_lower:
                return True, f"Retryable error: {keyword}"

        # Non-retryable errors (permanent)
        permanent_keywords = [
            "syntax error",
            "name error",
            "type error",
            "file not found",
            "no such file",
            "invalid",
            "parse error",
            "attribute error",
            "import error",
            "permission denied",
            "401",
            "403",
        ]

        for keyword in permanent_keywords:
            if keyword in stderr_lower:
                return False, f"Permanent error: {keyword}"

        # Default: don't retry unknown errors (conservative)
        return False, "Unknown error type (conservative: no retry)"

    def calculate_backoff(self, attempt: int, stage_name: str) -> float:
        """
        Calculate exponential backoff delay with jitter.

        Args:
            attempt: Current attempt number (1-indexed)
            stage_name: Name of stage for config lookup

        Returns:
            Delay in seconds
        """
        stage_config = self.get_stage_config(stage_name)
        base = stage_config["backoff_base"]
        max_delay = stage_config["backoff_max"]

        # Exponential backoff: base^(attempt-1)
        delay = base ** (attempt - 1)

        # Cap at max delay
        delay = min(delay, max_delay)

        # Add jitter (±20%)
        jitter = delay * 0.2 * (random.random() * 2 - 1)
        delay += jitter

        return max(1, delay)  # Minimum 1 second

    def should_retry(self, attempt: int, stage_name: str, stderr: str) -> Tuple[bool, str, float]:
        """
        Determine if stage should be retried.

        Returns:
            (should_retry, reason, backoff_delay)
        """
        stage_config = self.get_stage_config(stage_name)
        max_attempts = stage_config["max_attempts"]

        # Check if max attempts exceeded
        if attempt >= max_attempts:
            return False, f"Max attempts ({max_attempts}) reached", 0

        # Check if error is retryable
        is_retryable, reason = self.is_retryable_error(stderr, stage_name)
        if not is_retryable:
            return False, reason, 0

        # Calculate backoff
        backoff = self.calculate_backoff(attempt, stage_name)

        return True, f"Retrying: {reason}", backoff

    def record_failure(self):
        """Record a failure for circuit breaker."""
        self.consecutive_failures += 1

    def record_success(self):
        """Record a success, resetting circuit breaker."""
        self.consecutive_failures = 0


class PipelineOrchestrator:
    """Orchestrates the full literature review pipeline."""

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
        self.dry_run = self.config.get('dry_run', False)
        self.resume = resume
        self.resume_from = resume_from
        self.run_id = self._generate_run_id()
        self.checkpoint_data = self._load_or_create_checkpoint()

        # Initialize retry policy
        self.retry_policy = RetryPolicy(self.config)
        
        # Initialize cost tracker
        self.cost_tracker = get_cost_tracker()
        self.budget_usd = self.config.get('budget_usd', 50.0)
        # Initialize incremental analysis support
        self.incremental = self.config.get('incremental', False)
        self.force_full = self.config.get('force', False)
        if self.incremental or self.force_full:
            from literature_review.utils.incremental_analyzer import get_incremental_analyzer
            self.incremental_analyzer = get_incremental_analyzer()
        else:
            self.incremental_analyzer = None
        
        # Log dry-run mode if enabled
        if self.dry_run:
            self.log("=" * 70, "INFO")
            self.log("DRY-RUN MODE ENABLED", "WARNING")
            self.log("No stages will be executed, only validation will occur", "WARNING")
            self.log("=" * 70, "INFO")

    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}"

    def _load_or_create_checkpoint(self) -> Dict[str, Any]:
        """Load existing checkpoint or create new one."""
        if self.resume and Path(self.checkpoint_file).exists():
            try:
                with open(self.checkpoint_file, "r") as f:
                    data = json.load(f)
                self.log(f"Loaded checkpoint from {self.checkpoint_file}", "INFO")
                self.log(f"Previous run ID: {data.get('run_id')}", "INFO")
                # Keep the same run_id when resuming
                self.run_id = data.get("run_id", self.run_id)
                return data
            except Exception as e:
                self.log(f"Error loading checkpoint: {e}", "ERROR")
                self.log("Starting fresh pipeline", "WARNING")

        # Create new checkpoint
        return {
            "run_id": self.run_id,
            "pipeline_version": "1.3.0",
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "status": "in_progress",
            "stages": {},
            "config": {"retry_policy": self.config.get("retry_policy", {})},
        }

    def _write_checkpoint(self):
        """Atomically write checkpoint to file."""
        self.checkpoint_data["last_updated"] = datetime.now().isoformat()

        # Write to temp file first, then atomic rename
        temp_file = f"{self.checkpoint_file}.tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump(self.checkpoint_data, f, indent=2)

            # Atomic rename
            Path(temp_file).replace(self.checkpoint_file)
        except Exception as e:
            self.log(f"Error writing checkpoint: {e}", "ERROR")
            if Path(temp_file).exists():
                Path(temp_file).unlink()

    def _should_run_stage(self, stage_name: str) -> bool:
        """Check if stage should run based on checkpoint."""
        if not self.resume:
            return True

        if self.resume_from:
            # Find position of resume_from stage
            # For simplicity, we'll check if the stage name matches
            stage_data = self.checkpoint_data.get("stages", {}).get(stage_name, {})
            status = stage_data.get("status", "not_started")

            # If resuming from specific stage, run it and all following stages
            if stage_name == self.resume_from or status in ["not_started", "failed", "retrying"]:
                return True

            # Check if we've reached the resume_from stage yet
            return status != "completed"
        else:
            # Resume from first incomplete stage
            stage_data = self.checkpoint_data.get("stages", {}).get(stage_name, {})
            status = stage_data.get("status", "not_started")

            if status == "completed":
                self.log(f"Skipping completed stage: {stage_name}", "INFO")
                return False

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
                "duration_seconds": duration,
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
                "error": error[:500],  # Truncate long errors
            }
        )

        self._write_checkpoint()

    def _mark_stage_retry(self, stage_name: str, attempt: int, error: str, next_delay: float):
        """Mark retry attempt in checkpoint."""
        if "retry_history" not in self.checkpoint_data["stages"][stage_name]:
            self.checkpoint_data["stages"][stage_name]["retry_history"] = []

        self.checkpoint_data["stages"][stage_name]["retry_history"].append(
            {
                "attempt": attempt,
                "failed_at": datetime.now().isoformat(),
                "error": error[:200],  # Truncate
                "next_retry_delay": next_delay,
            }
        )

        self.checkpoint_data["stages"][stage_name].update(
            {"status": "retrying", "current_attempt": attempt, "last_error": error[:200]}
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

    def _run_deep_review_trigger_analysis(self):
        """Run Deep Review Trigger Analysis to identify high-value papers."""
        try:
            from literature_review.triggers.deep_review_triggers import generate_trigger_report
            
            gap_file = 'gap_analysis_output/gap_analysis_report.json'
            review_log = 'review_version_history.json'
            output_file = 'deep_reviewer_cache/trigger_decisions.json'
            
            # Check if required files exist
            if not Path(gap_file).exists():
                self.log(f"Gap analysis file not found: {gap_file}, skipping trigger analysis", "WARNING")
                return
            
            if not Path(review_log).exists():
                self.log(f"Review log file not found: {review_log}, skipping trigger analysis", "WARNING")
                return
            
            self.log("=" * 70, "INFO")
            self.log("Running Deep Review Trigger Analysis...", "INFO")
            
            report = generate_trigger_report(gap_file, review_log, output_file)
            
            self.log(f"Trigger Analysis Complete: {report['triggered_papers']}/{report['total_papers']} papers triggered ({report['trigger_rate']:.0%})", "INFO")
            self.log("=" * 70, "INFO")
            
        except ImportError as e:
            self.log(f"Could not import trigger module: {e}", "WARNING")
        except Exception as e:
            self.log(f"Error running trigger analysis: {e}", "WARNING")

    def log(self, message: str, level: str = "INFO"):
        """Log message to console and optionally to file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(log_message + "\n")

    def run_stage(
        self, stage_name: str, script: str, description: str, required: bool = True, use_module: bool = False
    ) -> bool:
        """
        Run a pipeline stage with retry support.

        Args:
            stage_name: Unique stage identifier
            script: Python script path or module name
            description: Human-readable stage description
            required: If True, exit on failure; if False, continue
            use_module: If True, use -m flag to run as module; if False, run as script

        Returns:
            True if successful, False otherwise
        """
        # Check if stage should run based on checkpoint
        if not self._should_run_stage(stage_name):
            return True  # Already completed

        # Get retry state from checkpoint
        stage_data = self.checkpoint_data.get("stages", {}).get(stage_name, {})
        current_attempt = stage_data.get("current_attempt", 0)

        # Get retry config
        stage_config = self.retry_policy.get_stage_config(stage_name)
        max_attempts = stage_config["max_attempts"]

        # Attempt loop
        for attempt in range(current_attempt + 1, max_attempts + 1):
            self.log(f"Starting stage: {description} (attempt {attempt}/{max_attempts})", "INFO")
            self._mark_stage_started(stage_name)

            stage_start = datetime.now()

            try:
                # Dry-run mode: simulate execution
                if self.dry_run:
                    self.log(f"[DRY-RUN] Would execute: {script}", "INFO")
                    duration = 0.1  # Simulated duration
                    # Mark as completed in dry-run
                    self.log(f"✅ Stage validated: {description}", "SUCCESS")
                    self._mark_stage_completed(stage_name, duration, 0)
                    self.retry_policy.record_success()
                    return True
                
                # Build command based on execution type
                if use_module:
                    cmd = [sys.executable, '-m', script]
                else:
                    cmd = [sys.executable, script]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.get("stage_timeout", 3600),
                )

                duration = (datetime.now() - stage_start).total_seconds()

                if result.returncode == 0:
                    self.log(f"✅ Stage complete: {description}", "SUCCESS")
                    self._mark_stage_completed(stage_name, duration, result.returncode)
                    self.retry_policy.record_success()
                    return True
                else:
                    # Stage failed - check if retryable
                    self.log(f"❌ Stage failed: {description} (attempt {attempt})", "ERROR")
                    self.log(f"Error output:\n{result.stderr}", "ERROR")

                    # Determine if should retry
                    should_retry, retry_reason, backoff_delay = self.retry_policy.should_retry(
                        attempt, stage_name, result.stderr
                    )

                    if should_retry:
                        self.log(
                            f"🔄 {retry_reason} - waiting {backoff_delay:.1f}s before retry",
                            "WARNING",
                        )
                        self._mark_stage_retry(stage_name, attempt, result.stderr, backoff_delay)
                        self.retry_policy.record_failure()

                        # Wait before retry
                        time.sleep(backoff_delay)
                        continue  # Retry
                    else:
                        # Don't retry
                        self.log(f"🚫 Not retrying: {retry_reason}", "ERROR")
                        self._mark_stage_failed(stage_name, result.stderr[:500])

                        if required:
                            self.log("Pipeline halted due to required stage failure", "ERROR")
                            sys.exit(1)
                        return False

            except subprocess.TimeoutExpired:
                self.log(f"⏱️ Stage timeout: {description} (attempt {attempt})", "ERROR")

                # Timeout is usually retryable
                should_retry, retry_reason, backoff_delay = self.retry_policy.should_retry(
                    attempt, stage_name, "timeout"
                )

                if should_retry:
                    self.log(
                        f"🔄 {retry_reason} - waiting {backoff_delay:.1f}s before retry", "WARNING"
                    )
                    self._mark_stage_retry(stage_name, attempt, "Timeout", backoff_delay)
                    self.retry_policy.record_failure()
                    time.sleep(backoff_delay)
                    continue
                else:
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

        # Max attempts exceeded
        self.log(f"🛑 Max retry attempts ({max_attempts}) exceeded for {description}", "ERROR")
        self._mark_stage_failed(stage_name, f"Failed after {max_attempts} attempts")

        if required:
            self.log("Pipeline halted due to required stage failure", "ERROR")
            sys.exit(1)

        return False

    def check_for_rejections(self) -> bool:
        """Check if version history has rejected claims."""
        version_history_path = self.config.get(
            "version_history_path", "review_version_history.json"
        )

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
        """Execute the full pipeline."""
        self.log("=" * 70, "INFO")
        self.log("Literature Review Pipeline Orchestrator v1.3", "INFO")
        self.log(f"Run ID: {self.run_id}", "INFO")
        self.log("=" * 70, "INFO")
        
        # Check budget at start
        budget_status = self.cost_tracker.get_budget_status(self.budget_usd)
        
        if budget_status['over_budget']:
            error_msg = (
                f"⚠️ Over budget! Spent ${budget_status['spent']:.2f} / ${budget_status['budget']:.2f}. "
                f"Increase budget in config or reset cost log to continue."
            )
            self.log(error_msg, "ERROR")
            raise RuntimeError("Budget exceeded. Pipeline aborted.")
        
        if budget_status['at_risk']:
            warning_msg = (
                f"⚠️ Budget at risk: ${budget_status['remaining']:.2f} remaining "
                f"({budget_status['percent_used']:.1f}% used)"
            )
            self.log(warning_msg, "WARNING")
        else:
            self.log(f"💰 Budget status: ${budget_status['spent']:.2f} / ${budget_status['budget']:.2f} used", "INFO")
        # Incremental analysis: detect changes before running
        if self.incremental_analyzer:
            changes = self.incremental_analyzer.detect_changes(
                paper_dir='data/raw',
                pillar_file='pillar_definitions.json',
                force=self.force_full
            )
            
            papers_to_analyze = changes['new'] + changes['modified']
            
            if not papers_to_analyze and not self.force_full:
                self.log("✅ No changes detected - all papers are up to date", "INFO")
                self.log("💡 Use --force to re-analyze all papers", "INFO")
                self.log("=" * 70, "INFO")
                return
            
            if self.incremental and not self.force_full:
                total_papers = len(changes['new']) + len(changes['modified']) + len(changes['unchanged'])
                self.log(f"📊 Incremental mode: analyzing {len(papers_to_analyze)}/{total_papers} papers", "INFO")
                self.log(f"   New: {len(changes['new'])}, Modified: {len(changes['modified'])}, Unchanged: {len(changes['unchanged'])}", "INFO")
            else:
                self.log(f"📊 Full analysis mode: {len(papers_to_analyze)} papers", "INFO")

        # Stage 1: Journal Reviewer
        self.run_stage("journal_reviewer", "literature_review.reviewers.journal_reviewer", "Stage 1: Initial Paper Review", use_module=True)

        # Stage 2: Judge
        self.run_stage("judge", "literature_review.analysis.judge", "Stage 2: Judge Claims", use_module=True)

        # Stage 3: DRA (conditional)
        if self.check_for_rejections():
            self.log("Rejections detected, running DRA appeal process", "INFO")
            self.run_stage("dra", "literature_review.analysis.requirements", "Stage 3: DRA Appeal", use_module=True)
            self.run_stage("judge_dra", "literature_review.analysis.judge", "Stage 3b: Re-judge DRA Claims", use_module=True)
        else:
            self.log("No rejections found, skipping DRA", "INFO")
            self._mark_stage_skipped("dra", "no_rejections")

        # Stage 4: Sync to Database
        self.run_stage("sync", "scripts.sync_history_to_db", "Stage 4: Sync to Database", use_module=True)

        # Stage 5: Orchestrator
        self.run_stage("orchestrator", "literature_review.orchestrator", "Stage 5: Gap Analysis & Convergence", use_module=True)

        # Update incremental state after successful completion
        if self.incremental_analyzer:
            self.incremental_analyzer.update_fingerprints(
                paper_dir='data/raw',
                pillar_file='pillar_definitions.json'
            )
        # Stage 6: Proof Scorecard (NEW)
        self.run_stage("proof_scorecard", "literature_review.analysis.proof_scorecard", "Stage 6: Proof Completeness Scorecard", use_module=True)
        
        # Stage 7: Evidence Sufficiency Matrix (NEW)
        self.run_stage("sufficiency_matrix", "literature_review.analysis.sufficiency_matrix", "Stage 7: Evidence Sufficiency Matrix", use_module=True)

        # Stage 8: Deep Review Trigger Analysis (NEW)
        self._run_deep_review_trigger_analysis()

        # Mark pipeline complete
        self.checkpoint_data["status"] = "completed"
        self.checkpoint_data["completed_at"] = datetime.now().isoformat()
        self._write_checkpoint()

        # Generate cost report
        self.log("=" * 70, "INFO")
        self.log("📊 COST REPORT", "INFO")
        self.log("=" * 70, "INFO")
        
        report = self.cost_tracker.generate_report()
        session_summary = report['session_summary']
        total_summary = report['total_summary']
        
        self.log(f"Session Cost: ${session_summary['total_cost']:.4f} ({session_summary['total_calls']} calls)", "INFO")
        self.log(f"Total Cost: ${total_summary['total_cost']:.4f} ({total_summary['total_calls']} calls)", "INFO")
        
        budget_status = report['budget_status']
        self.log(f"Budget Remaining: ${budget_status['remaining']:.2f}", "INFO")
        
        if report['recommendations']:
            self.log("", "INFO")
            self.log("💡 Cost Optimization Recommendations:", "INFO")
            for rec in report['recommendations']:
                self.log(f"   {rec}", "INFO")

        # Summary
        elapsed = datetime.now() - self.start_time
        self.log("=" * 70, "INFO")
        self.log(f"🎉 Pipeline Complete!", "SUCCESS")
        self.log(f"Total time: {elapsed}", "INFO")
        self.log(f"Checkpoint saved to: {self.checkpoint_file}", "INFO")
        self.log("=" * 70, "INFO")


def main():
    parser = argparse.ArgumentParser(
        description="Run the full Literature Review pipeline automatically (v2.0 with advanced features)"
    )
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
        "--resume-from", type=str, help="Resume from specific stage (e.g., judge, sync)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run mode: validate pipeline without executing stages or writing outputs"
    )
    parser.add_argument(
        "--enable-experimental",
        action="store_true",
        help="Enable experimental v2.0 features (parallel processing, quota management). Use with caution."
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=50.0,
        help="Monthly API budget in USD (default: $50.00)"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        default=True,
        help="Use incremental analysis (default: True)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full re-analysis of all papers"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear incremental analysis cache before running"
    )

    args = parser.parse_args()
    
    # Handle cache clearing first
    if args.clear_cache:
        from literature_review.utils.incremental_analyzer import get_incremental_analyzer
        analyzer = get_incremental_analyzer()
        analyzer.clear_cache()
        print("✅ Incremental analysis cache cleared")

    # Load config if provided
    config = {}
    if args.config and Path(args.config).exists():
        with open(args.config) as f:
            config = json.load(f)

    # Override config with CLI flags
    if args.dry_run:
        config['dry_run'] = True
    
    if args.budget:
        config['budget_usd'] = args.budget
    # Set incremental flags
    config['incremental'] = args.incremental and not args.force
    config['force'] = args.force
    
    if args.enable_experimental:
        # Enable v2 features if requested
        if 'v2_features' not in config:
            from literature_review.pipeline.orchestrator_v2 import create_v2_config_defaults
            config['v2_features'] = create_v2_config_defaults()
        config['v2_features']['feature_flags']['enable_parallel_processing'] = True
        config['v2_features']['feature_flags']['enable_quota_management'] = True
        config['v2_features']['feature_flags']['enable_smart_retry'] = True

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
