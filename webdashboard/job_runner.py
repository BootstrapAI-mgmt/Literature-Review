"""
Background Job Runner for Literature Review Pipeline

Processes queued jobs by executing the orchestrator pipeline in a background worker.
Manages job lifecycle: queued → running → completed/failed
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from webdashboard.eta_calculator import AdaptiveETACalculator

logger = logging.getLogger(__name__)


class PipelineJobRunner:
    """Background worker to execute queued pipeline jobs"""
    
    def __init__(self, max_workers: int = 2):
        """
        Initialize job runner
        
        Args:
            max_workers: Maximum number of concurrent jobs to process
        """
        self.queue = asyncio.Queue()
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = logging.getLogger(__name__)
        self.eta_calculator = AdaptiveETACalculator()
        self.stage_timings: Dict[str, Dict] = {}  # job_id -> {stage -> start_time}
        
    async def start(self):
        """Start the background worker loop"""
        self.logger.info("Job runner started")
        while True:
            job_id, job_data = await self.queue.get()
            task = asyncio.create_task(self.process_job(job_id, job_data))
            self.running_jobs[job_id] = task
            
    async def process_job(self, job_id: str, job_data: dict):
        """
        Execute full orchestrator pipeline for a job
        
        Args:
            job_id: Unique job identifier
            job_data: Job configuration and metadata
        """
        try:
            self.logger.info(f"Starting job {job_id}")
            
            # Update job status to running
            await self.update_job_status(job_id, "running")
            
            # Run orchestrator in thread pool (it's blocking/sync)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._run_orchestrator_sync,
                job_id,
                job_data
            )
            
            # Update job status to completed
            await self.update_job_status(job_id, "completed", result=result)
            
        except Exception as e:
            self.logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            await self.update_job_status(job_id, "failed", error=str(e))
        finally:
            self.running_jobs.pop(job_id, None)
            
    async def enqueue_job(self, job_id: str, job_data: dict):
        """
        Add a job to the processing queue
        
        Args:
            job_id: Unique job identifier
            job_data: Job configuration and metadata
        """
        await self.queue.put((job_id, job_data))
        self.logger.info(f"Job {job_id} queued")
        
    def get_running_jobs(self) -> list:
        """
        Get list of currently running job IDs
        
        Returns:
            List of job IDs currently being processed
        """
        return list(self.running_jobs.keys())
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[Dict] = None,
        error: Optional[str] = None,
        result: Optional[Dict] = None
    ):
        """
        Update job status and save to file
        
        Args:
            job_id: Job identifier
            status: Job status (running, completed, failed)
            progress: Optional progress information
            error: Optional error message
            result: Optional result data
        """
        status_data = {
            "id": job_id,
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if status == "running":
            status_data["started_at"] = datetime.utcnow().isoformat()
        elif status in ["completed", "failed"]:
            status_data["completed_at"] = datetime.utcnow().isoformat()
        
        if progress:
            status_data["progress"] = progress
        if error:
            status_data["error"] = error
        if result:
            status_data["result"] = result
        
        # Save to status file
        status_file = Path(f"workspace/status/{job_id}.json")
        status_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
        
        # Broadcast WebSocket update
        try:
            # Import here to avoid circular dependency
            from webdashboard.app import manager
            await manager.broadcast({
                "type": "job_update",
                "job": status_data
            })
        except Exception as e:
            self.logger.warning(f"Failed to broadcast status update: {e}")
    
    def _write_log(self, job_id: str, message: str):
        """
        Write message to job log file
        
        Args:
            job_id: Job identifier
            message: Log message
        """
        log_file = Path(f"workspace/logs/{job_id}.log").resolve()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().isoformat()
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def _write_progress_event(self, job_id: str, event):
        """
        Write progress event to JSONL file and track stage durations
        
        Args:
            job_id: Job identifier
            event: ProgressEvent object
        """
        from pathlib import Path
        import json
        
        progress_file = Path(f"workspace/status/{job_id}_progress.jsonl")
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Track stage timing for ETA calculation
        self._track_stage_timing(job_id, event)
        
        # Convert ProgressEvent to dict for JSON serialization
        event_dict = {
            'timestamp': event.timestamp,
            'stage': event.stage,
            'phase': event.phase,
            'message': event.message,
            'percentage': event.percentage,
            'metadata': event.metadata
        }
        
        with open(progress_file, 'a') as f:
            f.write(json.dumps(event_dict) + '\n')
    
    def _track_stage_timing(self, job_id: str, event):
        """
        Track stage start/end times for ETA calculation
        
        Args:
            job_id: Job identifier
            event: ProgressEvent object
        """
        if job_id not in self.stage_timings:
            self.stage_timings[job_id] = {}
        
        stage = event.stage
        phase = event.phase
        
        if phase == 'starting':
            # Record stage start time
            self.stage_timings[job_id][stage] = {
                'start_time': datetime.now(timezone.utc),
                'stage': stage
            }
        elif phase == 'complete' and stage in self.stage_timings[job_id]:
            # Calculate duration and record to history
            timing = self.stage_timings[job_id][stage]
            end_time = datetime.now(timezone.utc)
            duration_seconds = (end_time - timing['start_time']).total_seconds()
            
            # Get paper count from job data
            paper_count = self._get_paper_count(job_id)
            
            # Record to ETA calculator history
            self.eta_calculator.record_stage_completion(
                stage_name=stage,
                duration_seconds=duration_seconds,
                paper_count=paper_count
            )
            
            # Store in timing info
            timing['end_time'] = end_time
            timing['duration_seconds'] = duration_seconds
            
            self.logger.info(
                f"Stage '{stage}' completed in {duration_seconds:.1f}s "
                f"({duration_seconds/max(paper_count, 1):.1f}s per paper)"
            )
    
    def _get_paper_count(self, job_id: str) -> int:
        """
        Get the number of papers being processed in this job
        
        Args:
            job_id: Job identifier
            
        Returns:
            Number of papers, defaults to 10 if not found
        """
        try:
            job_file = Path(f"workspace/jobs/{job_id}/job.json")
            if job_file.exists():
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                    return len(job_data.get('papers', []))
        except Exception as e:
            self.logger.warning(f"Could not determine paper count for job {job_id}: {e}")
        
        # Default to 10 papers if we can't determine
        return 10
    
    def get_job_eta(self, job_id: str, current_stage: str) -> Dict:
        """
        Get ETA for remaining stages in a job
        
        Args:
            job_id: Job identifier
            current_stage: Current stage name
            
        Returns:
            ETA information dictionary
        """
        paper_count = self._get_paper_count(job_id)
        return self.eta_calculator.calculate_eta(current_stage, paper_count)
    
    def _run_orchestrator_sync(self, job_id: str, job_data: dict):
        """
        Run orchestrator synchronously (called in thread pool)
        
        Args:
            job_id: Job identifier
            job_data: Job configuration and metadata
            
        Returns:
            Result dictionary from orchestrator execution
        """
        import subprocess
        import sys
        from pathlib import Path
        
        # Default relevance threshold constant
        DEFAULT_RELEVANCE_THRESHOLD = 0.7
        
        
        config = job_data.get("config", {})
        
        # Build CLI command for pipeline orchestrator
        cmd = [sys.executable, "pipeline_orchestrator.py"]
        
        # Add batch mode (non-interactive)
        cmd.append("--batch-mode")
        
        # Add job ID for incremental tracking
        cmd.extend(["--parent-job-id", job_id])
        
        # Add advanced options
        if config.get("dry_run"):
            cmd.append("--dry-run")
        
        if config.get("force"):
            cmd.append("--force")
        
        if config.get("clear_cache"):
            cmd.append("--clear-cache")
        
        if config.get("budget"):
            cmd.extend(["--budget", str(config["budget"])])
        
        relevance_threshold = config.get("relevance_threshold", DEFAULT_RELEVANCE_THRESHOLD)
        if relevance_threshold != DEFAULT_RELEVANCE_THRESHOLD:  # Only add if non-default
            cmd.extend(["--relevance-threshold", str(relevance_threshold)])
        
        if config.get("resume_from_stage"):
            cmd.extend(["--resume-from", config["resume_from_stage"]])
        
        if config.get("resume_from_checkpoint"):
            cmd.extend(["--checkpoint-file", config["resume_from_checkpoint"]])
            cmd.append("--resume")
        
        if config.get("experimental"):
            cmd.append("--enable-experimental")
        
        # Add pre-filter configuration (PARITY-W2-5)
        if "pre_filter" in config:
            pre_filter = config["pre_filter"]
            if pre_filter is not None:  # None means use default (don't add flag)
                # Validate sections if custom (non-empty string)
                if pre_filter:  # Non-empty string = custom sections
                    valid_sections = [
                        'title', 'abstract', 'introduction', 'methods',
                        'results', 'discussion', 'conclusion', 'references'
                    ]
                    sections = [s.strip() for s in pre_filter.split(',')]
                    
                    # Check if all sections are empty strings
                    if not any(s for s in sections):
                        error_msg = "Pre-filter cannot be empty list. Use empty string for full paper."
                        self._write_log(job_id, f"❌ {error_msg}")
                        raise ValueError(error_msg)
                    
                    # Validate section names
                    invalid_sections = [s for s in sections if s and s not in valid_sections]
                    if invalid_sections:
                        error_msg = (
                            f"Invalid sections: {', '.join(invalid_sections)}. "
                            f"Valid sections: {', '.join(valid_sections)}"
                        )
                        self._write_log(job_id, f"❌ {error_msg}")
                        raise ValueError(error_msg)
                
                cmd.extend(["--pre-filter", pre_filter])
                
                if pre_filter == "":
                    self._write_log(job_id, "📄 Pre-filter: Full paper (all sections)")
                else:
                    self._write_log(job_id, f"📄 Pre-filter: {pre_filter}")
        
        # Handle custom config file
        custom_config_path = job_data.get("custom_config_path")
        if custom_config_path and Path(custom_config_path).exists():
            cmd.extend(["--config", custom_config_path])
        
        # Handle input method: directory vs upload (PARITY-W3-2)
        input_method = job_data.get("input_method", "upload")
        
        if input_method == "directory":
            # Directory input: pass server directory path directly to CLI
            data_dir = job_data.get("data_dir")
            if not data_dir:
                error_msg = "Directory input method requires data_dir in job data"
                self._write_log(job_id, f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            cmd.extend(["--data-dir", data_dir])
            self._write_log(job_id, f"📁 Using server directory: {data_dir}")
            
            # Log file counts
            pdf_count = job_data.get("pdf_count", 0)
            csv_count = job_data.get("csv_count", 0)
            self._write_log(job_id, f"📊 Found {pdf_count} PDFs and {csv_count} CSVs")
        else:
            # Upload method: point to job's upload directory
            upload_dir = Path(f"workspace/uploads/{job_id}")
            
            # Check if we have uploaded files
            if upload_dir.exists() and any(upload_dir.glob("*.pdf")):
                cmd.extend(["--data-dir", str(upload_dir)])
                self._write_log(job_id, f"📤 Using uploaded files from: {upload_dir}")
            elif job_data.get("file_path"):
                # Single file upload (legacy) - use file path directly
                single_file = Path(job_data["file_path"])
                if single_file.exists():
                    cmd.extend(["--data-dir", str(single_file.parent)])
                    self._write_log(job_id, f"📄 Using single uploaded file: {single_file}")
            else:
                self._write_log(job_id, "⚠️ No input files specified - pipeline will use defaults")
        
        # Set output directory for this job
        # Use custom output directory if specified, otherwise use default job directory
        # Use absolute paths to avoid issues with --data-dir changing working directory
        if config.get("output_dir"):
            output_dir = Path(config["output_dir"]).resolve()
        else:
            output_dir = Path(f"workspace/jobs/{job_id}/outputs/gap_analysis_output").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        cmd.extend(["--output-dir", str(output_dir)])
        
        # Set log file (use absolute path to avoid issues with --data-dir)
        log_file = Path(f"workspace/logs/{job_id}.log").resolve()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        cmd.extend(["--log-file", str(log_file)])
        
        # Log the command being executed
        self._write_log(job_id, f"Executing command: {' '.join(cmd)}")
        
        # Log force flag usage if enabled
        if config.get("force"):
            self._write_log(
                job_id,
                f"⚠️  Force re-analysis enabled (cache disabled, costs may be higher)"
            )
        
        try:
            # Execute pipeline orchestrator
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).parent.parent),  # Run from repo root
                timeout=7200  # 2 hour timeout
            )
            
            # Log stdout and stderr
            if result.stdout:
                self._write_log(job_id, f"STDOUT:\n{result.stdout}")
            if result.stderr:
                self._write_log(job_id, f"STDERR:\n{result.stderr}")
            
            if result.returncode != 0:
                error_msg = f"Pipeline failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                raise RuntimeError(error_msg)
            
            return {
                "status": "success",
                "output_dir": str(output_dir),
                "command": " ".join(cmd),
                "dry_run": config.get("dry_run", False),
                "force_enabled": config.get("force", False),
                "force_confirmed": config.get("force_confirmed", False),
                "cache_disabled": config.get("force", False)
            }
            
        except subprocess.TimeoutExpired:
            error_msg = "Pipeline execution timed out after 2 hours"
            self._write_log(job_id, error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            self._write_log(job_id, f"Pipeline execution failed: {str(e)}")
            raise

