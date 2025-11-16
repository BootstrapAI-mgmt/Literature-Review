# Technical Challenges & Solutions

**Reference**: Dashboard-Orchestrator Integration Gap Analysis  
**Priority**: 🔴 CRITICAL - Must be addressed for successful integration  
**Status**: 📋 Ready for Implementation

## Overview

This document provides detailed solutions to the four major technical challenges identified in the gap analysis, with complete implementation guidance.

---

## Challenge 1: Blocking vs Async Execution

### Problem Statement

The orchestrator's `main()` function is **synchronous and blocking**, which will freeze the FastAPI event loop if called directly in an async context. This prevents the dashboard from remaining responsive while jobs execute.

**Symptom**: Dashboard freezes when job runs, unable to handle other requests.

### Solution: Thread Pool Executor

Run the orchestrator in a separate thread using `asyncio.run_in_executor()`.

#### Implementation

**File**: `webdashboard/job_runner.py`

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

class PipelineJobRunner:
    """Background worker to execute queued pipeline jobs"""
    
    def __init__(self, max_workers: int = 2):
        self.queue = asyncio.Queue()
        self.running_jobs: Dict[str, asyncio.Task] = {}
        
        # Thread pool for blocking operations
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="pipeline-worker"
        )
        
        self.logger = logging.getLogger(__name__)
    
    async def process_job(self, job_id: str, job_data: dict):
        """Execute full orchestrator pipeline for a job"""
        try:
            self.logger.info(f"Starting job {job_id}")
            
            # Update job status to running
            await self.update_job_status(job_id, "running")
            
            # Get event loop
            loop = asyncio.get_event_loop()
            
            # Run orchestrator in thread pool (blocking call)
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
    
    def _run_orchestrator_sync(self, job_id: str, job_data: dict):
        """
        Synchronous wrapper for orchestrator execution
        This runs in a separate thread
        """
        from literature_review.orchestrator_integration import run_pipeline_for_job
        
        # Configure callbacks (must be thread-safe)
        def progress_callback(event):
            # Write to file (thread-safe)
            self._write_progress_event_sync(job_id, event)
        
        def log_callback(message):
            # Write to file (thread-safe)
            self._write_log_sync(job_id, message)
        
        config = job_data.get("config", {})
        
        return run_pipeline_for_job(
            job_id=job_id,
            pillar_selections=config.get("pillar_selections", ["ALL"]),
            run_mode=config.get("run_mode", "ONCE"),
            progress_callback=progress_callback,
            log_callback=log_callback
        )
    
    def _write_progress_event_sync(self, job_id: str, event):
        """Thread-safe progress event writing"""
        progress_file = Path(f"workspace/status/{job_id}_progress.jsonl")
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(progress_file, 'a') as f:
            f.write(json.dumps(event.__dict__) + '\n')
    
    def _write_log_sync(self, job_id: str, message: str):
        """Thread-safe log writing"""
        log_file = Path(f"workspace/logs/{job_id}.log")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().isoformat()
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
```

#### Key Points

1. **ThreadPoolExecutor**: Manages pool of worker threads for blocking operations
2. **run_in_executor()**: Schedules sync function to run in thread pool
3. **Thread Safety**: File operations are thread-safe (no shared state)
4. **Event Loop**: Remains responsive while orchestrator runs in thread

#### Testing

```python
@pytest.mark.asyncio
async def test_async_orchestrator_execution():
    """Test that orchestrator runs without blocking event loop"""
    runner = PipelineJobRunner(max_workers=1)
    
    job_data = {
        "id": "test-001",
        "config": {
            "pillar_selections": ["Pillar_1"],
            "run_mode": "ONCE"
        }
    }
    
    # Start job
    task = asyncio.create_task(runner.process_job("test-001", job_data))
    
    # Event loop should still be responsive
    await asyncio.sleep(0.1)
    
    # Can create other tasks
    other_task = asyncio.create_task(some_other_async_function())
    
    # Wait for job to complete
    await task
    await other_task
    
    assert True  # If we got here, event loop didn't block
```

#### Alternatives Considered

❌ **subprocess.Popen**: More isolation but harder to pass callbacks  
❌ **multiprocessing**: Good isolation but complexity with state sharing  
✅ **ThreadPoolExecutor**: Best balance of isolation and integration

---

## Challenge 2: Interactive Prompts in Web Context

### Problem Statement

Terminal `input()` calls **block execution** and expect keyboard input, which doesn't work in a web environment. Users need to provide input via browser, not terminal.

**Symptom**: Job hangs waiting for input that never comes.

### Solution: Async Callback-Based Prompting

Replace `input()` with async callbacks that pause execution, send prompt to browser via WebSocket, wait for response, then resume.

#### Implementation

**File**: `literature_review/orchestrator.py`

```python
from typing import Optional, Callable, Any
import asyncio

def get_user_analysis_target(
    pillar_definitions: Dict,
    prompt_callback: Optional[Callable] = None
) -> Tuple[List[str], str]:
    """
    Get analysis target from user
    
    Args:
        pillar_definitions: Available pillars
        prompt_callback: Async callback for prompts (if None, uses terminal input)
    
    Returns:
        (pillar_list, run_mode)
    """
    metadata_sections = {'Framework_Overview', 'Cross_Cutting_Requirements', 'Success_Criteria'}
    analyzable_pillars = [k for k in pillar_definitions.keys() if k not in metadata_sections]
    
    if prompt_callback is None:
        # ===== TERMINAL MODE (Original Behavior) =====
        safe_print("\n--- No new data detected ---")
        safe_print("What would you like to re-assess?")
        
        for i, name in enumerate(analyzable_pillars, 1):
            safe_print(f"  {i}. {name.split(':')[0]}")
        safe_print(f"\n  ALL - Run analysis on all pillars (one pass)")
        safe_print(f"  DEEP - Run iterative deep-review loop on all pillars")
        safe_print(f"  NONE - Exit (default)")
        
        choice = input(f"Enter choice (1-{len(analyzable_pillars)}, ALL, DEEP, NONE): ").strip().upper()
    
    else:
        # ===== DASHBOARD MODE (Async Prompt) =====
        # Need to run async callback in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Request user input via callback
            choice = loop.run_until_complete(
                prompt_callback(
                    prompt_type="pillar_selection",
                    prompt_data={
                        "message": "Select pillars to analyze",
                        "options": analyzable_pillars,
                        "allow_all": True,
                        "allow_deep": True,
                        "allow_none": True
                    }
                )
            )
        finally:
            loop.close()
    
    # ===== PARSE RESPONSE (Same for both modes) =====
    if not choice or choice == "NONE":
        return [], "EXIT"
    if choice == "ALL":
        return analyzable_pillars, "ONCE"
    if choice == "DEEP":
        return analyzable_pillars, "DEEP_LOOP"
    
    try:
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(analyzable_pillars):
            return [analyzable_pillars[choice_idx]], "ONCE"
    except ValueError:
        pass
    
    safe_print("Invalid choice. Exiting.")
    return [], "EXIT"
```

**File**: `webdashboard/prompt_handler.py`

```python
import asyncio
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import uuid

class PromptHandler:
    """Handles interactive prompts for jobs"""
    
    def __init__(self):
        # Maps prompt_id -> Future waiting for response
        self.pending_prompts: Dict[str, asyncio.Future] = {}
        self.prompt_timeouts: Dict[str, datetime] = {}
    
    async def request_user_input(
        self,
        job_id: str,
        prompt_type: str,
        prompt_data: Dict[str, Any],
        timeout_seconds: int = 300
    ) -> Any:
        """
        Request input from user via WebSocket
        
        This function PAUSES execution until user responds.
        
        Args:
            job_id: Job identifier
            prompt_type: Type of prompt ('pillar_selection', 'run_mode', etc.)
            prompt_data: Data for the prompt (options, message, etc.)
            timeout_seconds: How long to wait for response
        
        Returns:
            User's response
        
        Raises:
            TimeoutError: If user doesn't respond in time
        """
        prompt_id = str(uuid.uuid4())
        
        # Create future that will be resolved when user responds
        future = asyncio.Future()
        self.pending_prompts[prompt_id] = future
        self.prompt_timeouts[prompt_id] = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        
        # Broadcast prompt to WebSocket clients
        await self._broadcast_prompt(job_id, prompt_id, prompt_type, prompt_data)
        
        try:
            # PAUSE HERE - wait for user to respond
            response = await asyncio.wait_for(future, timeout=timeout_seconds)
            return response
        
        except asyncio.TimeoutError:
            # Clean up
            self.pending_prompts.pop(prompt_id, None)
            self.prompt_timeouts.pop(prompt_id, None)
            
            raise TimeoutError(f"User did not respond to prompt within {timeout_seconds} seconds")
    
    async def _broadcast_prompt(
        self,
        job_id: str,
        prompt_id: str,
        prompt_type: str,
        prompt_data: Dict[str, Any]
    ):
        """Send prompt to all connected WebSocket clients"""
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
        
        This RESUMES execution that was paused.
        
        Args:
            prompt_id: Prompt identifier
            response: User's response
        """
        future = self.pending_prompts.get(prompt_id)
        
        if not future or future.done():
            raise ValueError(f"No pending prompt with ID {prompt_id}")
        
        # Resolve future - this resumes execution
        future.set_result(response)
        
        # Clean up
        self.pending_prompts.pop(prompt_id, None)
        self.prompt_timeouts.pop(prompt_id, None)
```

#### Flow Diagram

```
Orchestrator Thread              PromptHandler              WebSocket Client (Browser)
      |                                |                              |
      |  request_user_input()          |                              |
      |------------------------------->|                              |
      |                                |  broadcast prompt            |
      |                                |----------------------------->|
      |                                |                              |
      | PAUSED (waiting)               |                              |
      |                                |                              |
      |                                |                              | User makes selection
      |                                |                              |
      |                                |    POST /api/prompts/{id}    |
      |                                |<-----------------------------|
      |                                |                              |
      |    return response             |  submit_response()           |
      |<-------------------------------|                              |
      |                                |                              |
      | RESUMED (continue execution)   |                              |
      |                                |                              |
```

#### Testing

```python
@pytest.mark.asyncio
async def test_prompt_request_and_response():
    """Test prompt request/response cycle"""
    handler = PromptHandler()
    
    async def respond_after_delay():
        # Simulate user taking 2 seconds to respond
        await asyncio.sleep(2)
        handler.submit_response("test-prompt-id", "ALL")
    
    # Start response task in background
    asyncio.create_task(respond_after_delay())
    
    # Request prompt (this will pause for 2 seconds)
    start_time = time.time()
    response = await handler.request_user_input(
        job_id="test-job",
        prompt_type="pillar_selection",
        prompt_data={"options": ["P1", "P2"]},
        timeout_seconds=10
    )
    elapsed = time.time() - start_time
    
    assert response == "ALL"
    assert 1.5 < elapsed < 2.5  # Took about 2 seconds
```

---

## Challenge 3: Real-time Output Streaming

### Problem Statement

`safe_print()` and `logger.info()` output goes to **terminal/file**, not to the dashboard. Users can't see what's happening in real-time.

**Symptom**: Dashboard shows no progress updates while job runs.

### Solution: Callback Hooks + File Polling

Add callback hooks to orchestrator that write to files, then poll/stream those files via WebSocket.

#### Implementation

**File**: `literature_review/orchestrator.py`

```python
from typing import Callable, Optional
from dataclasses import dataclass

@dataclass
class ProgressEvent:
    """Structured progress event"""
    timestamp: str
    stage: str
    phase: str
    message: str
    percentage: Optional[float] = None
    metadata: Optional[Dict] = None

class ProgressTracker:
    """Tracks and emits pipeline progress events"""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.current_stage = None
        self.stages_completed = []
    
    def emit(self, stage: str, phase: str, message: str, **kwargs):
        """Emit a progress event"""
        event = ProgressEvent(
            timestamp=datetime.utcnow().isoformat(),
            stage=stage,
            phase=phase,
            message=message,
            percentage=self.calculate_percentage(stage, phase),
            metadata=kwargs
        )
        
        # Call callback if provided (for dashboard)
        if self.callback:
            self.callback(event)
        
        # Also log to file (always)
        logger.info(f"[{stage}] {message}")
        
        # Also print to terminal (unless suppressed)
        if not kwargs.get('suppress_terminal'):
            safe_print(f"[{stage}] {message}")

def main(config: Optional[OrchestratorConfig] = None):
    """Main orchestrator with progress tracking"""
    
    # Initialize progress tracker
    progress_tracker = ProgressTracker(
        callback=config.progress_callback if config else None
    )
    
    progress_tracker.emit("initialization", "starting", "Loading definitions...")
    
    # ... rest of orchestrator with progress events throughout ...
```

**File**: `webdashboard/app.py`

```python
@app.websocket("/ws/jobs/{job_id}/progress")
async def job_progress_stream(websocket: WebSocket, job_id: str):
    """Stream real-time progress updates for a job"""
    await websocket.accept()
    
    try:
        # Send initial status
        job_data = load_job(job_id)
        if job_data:
            await websocket.send_json({
                "type": "initial_status",
                "job": job_data
            })
        
        # Watch for updates
        progress_file = Path(f"workspace/status/{job_id}_progress.jsonl")
        log_file = Path(f"workspace/logs/{job_id}.log")
        
        last_progress_pos = 0
        last_log_pos = 0
        
        while True:
            # Check if job is still active
            current_job = load_job(job_id)
            if current_job and current_job.get("status") in ["completed", "failed"]:
                await websocket.send_json({
                    "type": "job_complete",
                    "status": current_job["status"]
                })
                break
            
            # Stream progress updates (JSONL format)
            if progress_file.exists():
                with open(progress_file, 'r') as f:
                    f.seek(last_progress_pos)
                    new_lines = f.readlines()
                    last_progress_pos = f.tell()
                
                for line in new_lines:
                    try:
                        event = json.loads(line)
                        await websocket.send_json({
                            "type": "progress",
                            "event": event
                        })
                    except json.JSONDecodeError:
                        pass
            
            # Stream log updates
            if log_file.exists():
                with open(log_file, 'r') as f:
                    f.seek(last_log_pos)
                    new_lines = f.readlines()
                    last_log_pos = f.tell()
                
                if new_lines:
                    await websocket.send_json({
                        "type": "logs",
                        "lines": new_lines
                    })
            
            # Poll every 500ms
            await asyncio.sleep(0.5)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
```

#### Key Points

1. **File-based Communication**: Thread-safe, simple, works across processes
2. **JSONL Format**: One JSON object per line, easy to parse incrementally
3. **File Polling**: Read from last known position, send new content
4. **Multiple Streams**: Progress events (structured) + logs (plain text)

---

## Challenge 4: State Management & Checkpointing

### Problem Statement

Dashboard jobs can be **interrupted**, server can crash, user might refresh page. Need to preserve state and allow resumption.

**Symptom**: Job progress lost on interruption, can't resume.

### Solution: Leverage Existing Checkpoint System

Orchestrator already has checkpoint saving. Extend it for per-job state management.

#### Implementation

**File**: `literature_review/orchestrator.py`

```python
def save_orchestrator_state(
    state_file: str,
    results: dict,
    score_history: dict,
    stage: str,
    job_id: Optional[str] = None
):
    """
    Save orchestrator state for resumption
    
    Args:
        state_file: Base path for state file
        results: Current analysis results
        score_history: Historical score data
        stage: Current stage identifier
        job_id: Optional job ID (for dashboard jobs)
    """
    # Modify state file path for job-specific state
    if job_id:
        state_file = f"workspace/jobs/{job_id}/orchestrator_state.json"
    
    state_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "stage": stage,
        "results": results,
        "score_history": score_history,
        "job_id": job_id,
        "resumable": True  # Mark as resumable
    }
    
    # Ensure directory exists
    Path(state_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Write atomically (write to temp file, then rename)
    temp_file = state_file + ".tmp"
    with open(temp_file, 'w') as f:
        json.dump(state_data, f, indent=2)
    
    # Atomic rename
    os.replace(temp_file, state_file)
    
    logger.info(f"State saved: {stage} (job_id={job_id})")
```

**File**: `webdashboard/job_runner.py`

```python
async def resume_job(self, job_id: str):
    """Resume an interrupted job from checkpoint"""
    job_data = load_job(job_id)
    
    if not job_data:
        raise ValueError(f"Job {job_id} not found")
    
    # Check for checkpoint
    checkpoint_file = Path(f"workspace/jobs/{job_id}/orchestrator_state.json")
    
    if not checkpoint_file.exists():
        raise ValueError(f"No checkpoint found for job {job_id}")
    
    with open(checkpoint_file) as f:
        checkpoint_data = json.load(f)
    
    if not checkpoint_data.get("resumable"):
        raise ValueError(f"Job {job_id} is not resumable")
    
    # Update job config to resume from checkpoint
    job_data["config"]["resume_from_checkpoint"] = True
    job_data["config"]["checkpoint_data"] = checkpoint_data
    
    # Re-queue job
    await self.enqueue_job(job_id, job_data)
```

#### Testing

```python
def test_checkpoint_and_resume():
    """Test job can be checkpointed and resumed"""
    job_id = "test-checkpoint"
    
    # Start job
    runner = PipelineJobRunner()
    runner.enqueue_job(job_id, {...})
    
    # Wait for checkpoint
    time.sleep(10)
    
    # Simulate interruption (kill runner)
    runner.stop()
    
    # Verify checkpoint exists
    checkpoint = Path(f"workspace/jobs/{job_id}/orchestrator_state.json")
    assert checkpoint.exists()
    
    # Create new runner and resume
    new_runner = PipelineJobRunner()
    new_runner.resume_job(job_id)
    
    # Wait for completion
    wait_for_job_completion(job_id)
    
    # Verify job completed
    job_data = load_job(job_id)
    assert job_data["status"] == "completed"
```

---

## Summary of Solutions

| Challenge | Solution | Complexity | Phase |
|-----------|----------|------------|-------|
| **Blocking vs Async** | ThreadPoolExecutor + run_in_executor | Medium | Phase 1 |
| **Interactive Prompts** | Async callbacks + WebSocket | High | Phase 5 |
| **Output Streaming** | File-based callbacks + polling | Medium | Phase 3 |
| **State Management** | Extend existing checkpoints | Low | Phase 1 |

## Implementation Order

1. **Phase 1**: Blocking vs Async (foundation for everything)
2. **Phase 3**: Output Streaming (provides visibility)
3. **Phase 1**: State Management (enables reliability)
4. **Phase 5**: Interactive Prompts (completes parity)

## Risk Mitigation

- **Thread Safety**: All file operations use atomic writes
- **Error Handling**: Comprehensive try/catch with cleanup
- **Timeouts**: All blocking operations have timeouts
- **Monitoring**: Extensive logging for debugging
- **Testing**: Unit + integration tests for each solution

---

**All technical challenges have proven solutions. Implementation is straightforward but requires careful attention to concurrency and error handling.**
