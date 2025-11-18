"""
Interactive Prompt Handler for WebDashboard

Handles interactive prompts for jobs by pausing execution, sending prompts to 
users via WebSocket, and resuming with user responses.
"""

import asyncio
import uuid
from typing import Any, Optional, Dict
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


class PromptHandler:
    """Handles interactive prompts for jobs"""
    
    def __init__(self):
        self.pending_prompts: Dict[str, asyncio.Future] = {}
        self.prompt_timeouts: Dict[str, datetime] = {}
        self.prompt_job_ids: Dict[str, str] = {}  # Track job_id for each prompt
        self.prompt_metadata: Dict[str, Dict[str, Any]] = {}  # Track prompt metadata for history
    
    async def request_user_input(
        self,
        job_id: str,
        prompt_type: str,
        prompt_data: Dict[str, Any],
        timeout_seconds: int = 300
    ) -> Any:
        """
        Request input from user via WebSocket
        
        Args:
            job_id: Job identifier
            prompt_type: Type of prompt ('pillar_selection', 'run_mode', 'continue')
            prompt_data: Data for the prompt (options, message, etc.)
            timeout_seconds: How long to wait for response (default: 300 = 5 minutes)
        
        Returns:
            User's response. For pillar_selection, can be:
                - str: Special options like "ALL", "DEEP", "NONE"
                - List[str]: Multi-select pillar subset like ["P1: Pillar 1", "P3: Pillar 3"]
            For other prompt types, returns str.
        
        Raises:
            TimeoutError: If user doesn't respond in time
        """
        prompt_id = str(uuid.uuid4())
        
        # Create future for response
        future = asyncio.Future()
        self.pending_prompts[prompt_id] = future
        self.prompt_timeouts[prompt_id] = datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)
        self.prompt_job_ids[prompt_id] = job_id
        
        # Store prompt metadata for history tracking
        self.prompt_metadata[prompt_id] = {
            'prompt_type': prompt_type,
            'prompt_data': prompt_data,
            'timeout_seconds': timeout_seconds,
            'job_id': job_id
        }
        
        logger.info(f"Requesting user input for job {job_id}, prompt {prompt_id}, type {prompt_type}")
        
        # Broadcast prompt to WebSocket clients
        await self._broadcast_prompt(job_id, prompt_id, prompt_type, prompt_data)
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout_seconds)
            logger.info(f"Received response for prompt {prompt_id}: {response}")
            return response
        except asyncio.TimeoutError:
            # Save timeout to history before cleanup
            metadata = self.prompt_metadata.get(prompt_id)
            if metadata:
                await self._save_prompt_to_history(
                    job_id=job_id,
                    prompt_id=prompt_id,
                    prompt_type=metadata['prompt_type'],
                    response=None,
                    prompt_data=metadata['prompt_data'],
                    timeout_seconds=metadata['timeout_seconds'],
                    timed_out=True
                )
            
            # Clean up
            self.pending_prompts.pop(prompt_id, None)
            self.prompt_timeouts.pop(prompt_id, None)
            self.prompt_job_ids.pop(prompt_id, None)
            self.prompt_metadata.pop(prompt_id, None)
            
            logger.error(f"Prompt {prompt_id} timed out after {timeout_seconds} seconds")
            raise TimeoutError(f"User did not respond to prompt within {timeout_seconds} seconds")
    
    async def _broadcast_prompt(
        self,
        job_id: str,
        prompt_id: str,
        prompt_type: str,
        prompt_data: Dict[str, Any]
    ):
        """Broadcast prompt to WebSocket clients"""
        from webdashboard.app import manager
        
        await manager.broadcast({
            "type": "prompt_request",
            "job_id": job_id,
            "prompt_id": prompt_id,
            "prompt_type": prompt_type,
            "prompt_data": prompt_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def submit_response(self, prompt_id: str, response: Any):
        """
        Submit user response to a prompt
        
        Args:
            prompt_id: Prompt identifier
            response: User's response
        
        Raises:
            ValueError: If no pending prompt with the given ID
        """
        future = self.pending_prompts.get(prompt_id)
        
        if not future or future.done():
            raise ValueError(f"No pending prompt with ID {prompt_id}")
        
        logger.info(f"Submitting response for prompt {prompt_id}: {response}")
        
        # Save to history before resolving (use asyncio.create_task to not block)
        metadata = self.prompt_metadata.get(prompt_id)
        if metadata:
            job_id = metadata['job_id']
            asyncio.create_task(self._save_prompt_to_history(
                job_id=job_id,
                prompt_id=prompt_id,
                prompt_type=metadata['prompt_type'],
                response=response,
                prompt_data=metadata['prompt_data'],
                timeout_seconds=metadata['timeout_seconds'],
                timed_out=False
            ))
        
        # Resolve future with response
        future.set_result(response)
        
        # Clean up
        self.pending_prompts.pop(prompt_id, None)
        self.prompt_timeouts.pop(prompt_id, None)
        self.prompt_job_ids.pop(prompt_id, None)
        self.prompt_metadata.pop(prompt_id, None)
    
    def get_pending_prompts(self, job_id: Optional[str] = None) -> list:
        """
        Get list of pending prompts, optionally filtered by job_id
        
        Args:
            job_id: Optional job ID to filter by
        
        Returns:
            List of pending prompt IDs
        """
        if job_id is None:
            return list(self.pending_prompts.keys())
        
        return [
            prompt_id for prompt_id, jid in self.prompt_job_ids.items()
            if jid == job_id
        ]
    
    async def _save_prompt_to_history(
        self,
        job_id: str,
        prompt_id: str,
        prompt_type: str,
        response: Any,
        prompt_data: Dict[str, Any],
        timeout_seconds: int,
        timed_out: bool
    ):
        """
        Save prompt response to job metadata
        
        Args:
            job_id: Job identifier
            prompt_id: Prompt identifier
            prompt_type: Type of prompt
            response: User's response (None if timed out)
            prompt_data: Original prompt data
            timeout_seconds: Configured timeout
            timed_out: Whether the prompt timed out
        """
        import json
        from pathlib import Path
        
        try:
            # Construct job file path
            job_file = Path(f"workspace/jobs/{job_id}.json")
            
            if not job_file.exists():
                logger.warning(f"Job file not found for job {job_id}, cannot save prompt history")
                return
            
            # Load existing job data
            with open(job_file, 'r') as f:
                job_data = json.load(f)
            
            # Initialize prompts array if not exists
            if 'prompts' not in job_data:
                job_data['prompts'] = []
            
            # Append prompt record
            job_data['prompts'].append({
                'prompt_id': prompt_id,
                'type': prompt_type,
                'response': response,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'timeout_seconds': timeout_seconds,
                'timed_out': timed_out,
                'prompt_data': prompt_data
            })
            
            # Save back to file
            with open(job_file, 'w') as f:
                json.dump(job_data, f, indent=2)
            
            logger.info(f"Saved prompt {prompt_id} to job {job_id} history")
            
        except Exception as e:
            logger.error(f"Failed to save prompt history for job {job_id}: {e}")


# Global instance
prompt_handler = PromptHandler()
