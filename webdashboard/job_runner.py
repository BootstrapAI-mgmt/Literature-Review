"""
Background Job Runner for Literature Review Pipeline

Processes queued jobs by executing the orchestrator pipeline in a background worker.
Manages job lifecycle: queued → running → completed/failed
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

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
        log_file = Path(f"workspace/logs/{job_id}.log")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().isoformat()
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def _write_progress_event(self, job_id: str, event):
        """
        Write progress event to JSONL file
        
        Args:
            job_id: Job identifier
            event: ProgressEvent object
        """
        from pathlib import Path
        import json
        
        progress_file = Path(f"workspace/status/{job_id}_progress.jsonl")
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
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
    
    def _run_orchestrator_sync(self, job_id: str, job_data: dict):
        """
        Run orchestrator synchronously (called in thread pool)
        
        Args:
            job_id: Job identifier
            job_data: Job configuration and metadata
            
        Returns:
            Result dictionary from orchestrator execution
        """
        from literature_review.orchestrator_integration import run_pipeline_for_job
        from literature_review.orchestrator import ProgressEvent
        
        def progress_callback(event):
            """Callback for progress events"""
            # Write to progress file
            self._write_progress_event(job_id, event)
            
            # Also write to log
            self._write_log(job_id, f"[{event.stage}] {event.message}")
        
        def log_callback(message: str):
            """Callback for log messages"""
            self._write_log(job_id, f"LOG: {message}")
        
        async def prompt_callback(prompt_type: str, prompt_data: dict):
            """Async callback for user prompts"""
            from webdashboard.prompt_handler import prompt_handler
            
            # Request user input via PromptHandler
            response = await prompt_handler.request_user_input(
                job_id=job_id,
                prompt_type=prompt_type,
                prompt_data=prompt_data,
                timeout_seconds=300
            )
            return response
        
        config = job_data.get("config", {})
        
        return run_pipeline_for_job(
            job_id=job_id,
            pillar_selections=config.get("pillar_selections", ["ALL"]),
            run_mode=config.get("run_mode", "ONCE"),
            progress_callback=progress_callback,
            log_callback=log_callback,
            prompt_callback=prompt_callback
        )
