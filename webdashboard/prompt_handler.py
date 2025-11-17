"""
Interactive Prompt Handler for WebDashboard

Handles interactive prompts for jobs by pausing execution, sending prompts to 
users via WebSocket, and resuming with user responses.
"""

import asyncio
import uuid
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PromptHandler:
    """Handles interactive prompts for jobs"""
    
    def __init__(self):
        self.pending_prompts: Dict[str, asyncio.Future] = {}
        self.prompt_timeouts: Dict[str, datetime] = {}
        self.prompt_job_ids: Dict[str, str] = {}  # Track job_id for each prompt
    
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
            User's response
        
        Raises:
            TimeoutError: If user doesn't respond in time
        """
        prompt_id = str(uuid.uuid4())
        
        # Create future for response
        future = asyncio.Future()
        self.pending_prompts[prompt_id] = future
        self.prompt_timeouts[prompt_id] = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        self.prompt_job_ids[prompt_id] = job_id
        
        logger.info(f"Requesting user input for job {job_id}, prompt {prompt_id}, type {prompt_type}")
        
        # Broadcast prompt to WebSocket clients
        await self._broadcast_prompt(job_id, prompt_id, prompt_type, prompt_data)
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout_seconds)
            logger.info(f"Received response for prompt {prompt_id}: {response}")
            return response
        except asyncio.TimeoutError:
            # Clean up
            self.pending_prompts.pop(prompt_id, None)
            self.prompt_timeouts.pop(prompt_id, None)
            self.prompt_job_ids.pop(prompt_id, None)
            
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
            "timestamp": datetime.utcnow().isoformat()
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
        
        # Resolve future with response
        future.set_result(response)
        
        # Clean up
        self.pending_prompts.pop(prompt_id, None)
        self.prompt_timeouts.pop(prompt_id, None)
        self.prompt_job_ids.pop(prompt_id, None)
    
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


# Global instance
prompt_handler = PromptHandler()
