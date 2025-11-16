# Phase 1: Core Pipeline Integration

**Priority**: 🔴 CRITICAL  
**Timeline**: Week 1  
**Dependencies**: None  
**Status**: 📋 Ready to Start

## Overview

Implement the fundamental connection between the web dashboard and the orchestrator pipeline. This phase establishes the basic ability for the dashboard to execute the literature review pipeline, even with a minimal UI.

## Success Criteria

- [ ] Dashboard can execute `orchestrator.main()` via background worker
- [ ] Jobs transition from "queued" → "running" → "completed/failed"
- [ ] Basic progress updates are logged and accessible
- [ ] Pipeline outputs are saved to job-specific directories
- [ ] All existing terminal functionality remains intact

## Task Cards

### Task 1.1: Create Background Job Runner

**File**: `webdashboard/job_runner.py` (NEW)  
**Estimated Time**: 4 hours  
**Complexity**: Medium

#### Description
Create an async background worker that processes queued jobs by executing the orchestrator pipeline.

#### Implementation Steps

1. **Create JobRunner class with async queue**
   ```python
   import asyncio
   from concurrent.futures import ThreadPoolExecutor
   from typing import Dict, Optional
   import logging
   
   class PipelineJobRunner:
       """Background worker to execute queued pipeline jobs"""
       
       def __init__(self, max_workers: int = 2):
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
   ```

2. **Implement job processing method**
   ```python
   async def process_job(self, job_id: str, job_data: dict):
       """Execute full orchestrator pipeline for a job"""
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
   ```

3. **Add job queue management methods**
   ```python
   async def enqueue_job(self, job_id: str, job_data: dict):
       """Add a job to the processing queue"""
       await self.queue.put((job_id, job_data))
       self.logger.info(f"Job {job_id} queued")
   
   def get_running_jobs(self) -> list:
       """Get list of currently running job IDs"""
       return list(self.running_jobs.keys())
   ```

#### Acceptance Criteria
- [ ] JobRunner starts and processes jobs from queue
- [ ] Multiple jobs can be queued and processed sequentially
- [ ] Job status updates correctly (queued → running → completed/failed)
- [ ] Errors are caught and logged properly
- [ ] Thread pool executor prevents blocking the event loop

#### Testing
```python
# test_job_runner.py
async def test_job_runner_basic():
    runner = PipelineJobRunner(max_workers=1)
    asyncio.create_task(runner.start())
    
    # Enqueue test job
    await runner.enqueue_job("test-123", {"config": "test"})
    
    # Wait and verify
    await asyncio.sleep(2)
    assert "test-123" not in runner.get_running_jobs()
```

---

### Task 1.2: Create Orchestrator Integration Wrapper

**File**: `literature_review/orchestrator_integration.py` (MODIFY/EXPAND)  
**Estimated Time**: 6 hours  
**Complexity**: High

#### Description
Create a wrapper around `orchestrator.main()` that allows it to be called programmatically with parameters, without interactive prompts.

#### Implementation Steps

1. **Add configuration parameters to orchestrator**
   ```python
   # In orchestrator.py
   class OrchestratorConfig:
       """Configuration for orchestrator execution"""
       def __init__(
           self,
           job_id: str,
           analysis_target: List[str],
           run_mode: str,
           skip_user_prompts: bool = True,
           progress_callback: Optional[Callable] = None,
           log_callback: Optional[Callable] = None
       ):
           self.job_id = job_id
           self.analysis_target = analysis_target
           self.run_mode = run_mode
           self.skip_user_prompts = skip_user_prompts
           self.progress_callback = progress_callback
           self.log_callback = log_callback
   ```

2. **Modify orchestrator.main() to accept config**
   ```python
   def main(config: Optional[OrchestratorConfig] = None):
       """
       Main orchestrator entry point
       
       Args:
           config: Optional configuration for programmatic execution.
                   If None, runs in interactive terminal mode.
       """
       if config is None:
           # Original interactive mode
           config = OrchestratorConfig(
               job_id="terminal",
               analysis_target=[],
               run_mode="INTERACTIVE",
               skip_user_prompts=False
           )
       
       # Use config instead of prompting user
       if config.skip_user_prompts:
           analysis_target_pillars = config.analysis_target
           run_mode = config.run_mode
       else:
           # Original interactive prompt logic
           analysis_target_pillars, run_mode = get_user_analysis_target(definitions)
   ```

3. **Create integration wrapper in orchestrator_integration.py**
   ```python
   from literature_review.orchestrator import main as orchestrator_main, OrchestratorConfig
   from pathlib import Path
   from typing import Callable, List, Optional, Dict
   
   def run_pipeline_for_job(
       job_id: str,
       pillar_selections: List[str],
       run_mode: str,
       progress_callback: Optional[Callable] = None,
       log_callback: Optional[Callable] = None
   ) -> Dict:
       """
       Execute orchestrator pipeline for a dashboard job
       
       Args:
           job_id: Unique job identifier
           pillar_selections: List of pillar names or ["ALL"]
           run_mode: "ONCE" (single pass) or "DEEP_LOOP" (iterative)
           progress_callback: Function to call with progress updates
           log_callback: Function to call with log messages
       
       Returns:
           Dict with execution results and output file paths
       """
       # Create job-specific output directory
       output_dir = Path(f"workspace/jobs/{job_id}/outputs")
       output_dir.mkdir(parents=True, exist_ok=True)
       
       # Configure orchestrator
       config = OrchestratorConfig(
           job_id=job_id,
           analysis_target=pillar_selections,
           run_mode=run_mode,
           skip_user_prompts=True,
           progress_callback=progress_callback,
           log_callback=log_callback
       )
       
       # Execute pipeline
       try:
           result = orchestrator_main(config)
           
           # Collect output file paths
           output_files = list(output_dir.glob("**/*"))
           
           return {
               "status": "success",
               "output_dir": str(output_dir),
               "output_files": [str(f) for f in output_files],
               "result": result
           }
       except Exception as e:
           return {
               "status": "failed",
               "error": str(e)
           }
   ```

#### Acceptance Criteria
- [ ] `orchestrator.main()` can be called with config object
- [ ] Interactive prompts are skipped when `skip_user_prompts=True`
- [ ] Pipeline executes with specified pillars and run mode
- [ ] Progress/log callbacks are invoked during execution
- [ ] Terminal mode still works without config parameter
- [ ] Job-specific output directories are created

#### Testing
```python
def test_orchestrator_integration():
    result = run_pipeline_for_job(
        job_id="test-001",
        pillar_selections=["Pillar_1"],
        run_mode="ONCE",
        progress_callback=lambda msg: print(f"Progress: {msg}"),
        log_callback=lambda msg: print(f"Log: {msg}")
    )
    
    assert result["status"] == "success"
    assert Path(result["output_dir"]).exists()
```

---

### Task 1.3: Integrate JobRunner with Dashboard API

**File**: `webdashboard/app.py` (MODIFY)  
**Estimated Time**: 3 hours  
**Complexity**: Medium

#### Description
Connect the JobRunner to the dashboard FastAPI application to automatically process uploaded jobs.

#### Implementation Steps

1. **Initialize JobRunner on app startup**
   ```python
   from webdashboard.job_runner import PipelineJobRunner
   
   # Global job runner instance
   job_runner: Optional[PipelineJobRunner] = None
   
   @app.on_event("startup")
   async def startup_event():
       """Initialize background services on app startup"""
       global job_runner
       job_runner = PipelineJobRunner(max_workers=2)
       
       # Start background worker
       asyncio.create_task(job_runner.start())
       
       logger.info("Dashboard started with background job runner")
   ```

2. **Modify upload endpoint to enqueue jobs**
   ```python
   @app.post("/api/upload")
   async def upload_file(
       file: UploadFile = File(...),
       api_key: str = Header(None, alias="X-API-KEY")
   ):
       verify_api_key(api_key)
       
       # ... existing upload logic ...
       
       job_data = {
           "id": job_id,
           "status": "queued",
           "filename": file.filename,
           "file_path": str(target_path),
           "created_at": datetime.utcnow().isoformat(),
           "config": {
               "pillar_selections": ["ALL"],  # Default
               "run_mode": "ONCE"  # Default
           }
       }
       
       save_job(job_id, job_data)
       
       # ENQUEUE JOB FOR PROCESSING
       await job_runner.enqueue_job(job_id, job_data)
       
       await manager.broadcast({
           "type": "job_created",
           "job": job_data
       })
       
       return {"job_id": job_id, "status": "queued", "filename": file.filename}
   ```

3. **Add job configuration endpoint**
   ```python
   from pydantic import BaseModel
   
   class JobConfig(BaseModel):
       pillar_selections: List[str]
       run_mode: str  # "ONCE" or "DEEP_LOOP"
   
   @app.post("/api/jobs/{job_id}/configure")
   async def configure_job(
       job_id: str,
       config: JobConfig,
       api_key: str = Header(None, alias="X-API-KEY")
   ):
       """Configure job parameters before execution"""
       verify_api_key(api_key)
       
       job_data = load_job(job_id)
       if not job_data:
           raise HTTPException(status_code=404, detail="Job not found")
       
       # Update job configuration
       job_data["config"] = config.dict()
       save_job(job_id, job_data)
       
       return {"job_id": job_id, "config": config.dict()}
   ```

#### Acceptance Criteria
- [ ] JobRunner initializes on app startup
- [ ] Upload endpoint enqueues jobs automatically
- [ ] Jobs are processed in background
- [ ] Job configuration can be updated before execution
- [ ] Dashboard remains responsive during job execution

---

### Task 1.4: Implement Basic Progress Tracking

**File**: `webdashboard/job_runner.py` (MODIFY)  
**Estimated Time**: 3 hours  
**Complexity**: Medium

#### Description
Add basic progress logging and status updates that can be viewed via the API.

#### Implementation Steps

1. **Create progress logging helper**
   ```python
   async def update_job_status(
       self,
       job_id: str,
       status: str,
       progress: Optional[Dict] = None,
       error: Optional[str] = None,
       result: Optional[Dict] = None
   ):
       """Update job status and save to file"""
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
       await manager.broadcast({
           "type": "job_update",
           "job": status_data
       })
   ```

2. **Add log file writer**
   ```python
   def _write_log(self, job_id: str, message: str):
       """Write message to job log file"""
       log_file = Path(f"workspace/logs/{job_id}.log")
       log_file.parent.mkdir(parents=True, exist_ok=True)
       
       timestamp = datetime.utcnow().isoformat()
       with open(log_file, 'a') as f:
           f.write(f"[{timestamp}] {message}\n")
   ```

3. **Create callback functions for orchestrator**
   ```python
   def _run_orchestrator_sync(self, job_id: str, job_data: dict):
       """Run orchestrator synchronously (called in thread pool)"""
       from literature_review.orchestrator_integration import run_pipeline_for_job
       
       def progress_callback(message: str):
           """Callback for progress updates"""
           self._write_log(job_id, f"PROGRESS: {message}")
       
       def log_callback(message: str):
           """Callback for log messages"""
           self._write_log(job_id, f"LOG: {message}")
       
       config = job_data.get("config", {})
       
       return run_pipeline_for_job(
           job_id=job_id,
           pillar_selections=config.get("pillar_selections", ["ALL"]),
           run_mode=config.get("run_mode", "ONCE"),
           progress_callback=progress_callback,
           log_callback=log_callback
       )
   ```

#### Acceptance Criteria
- [ ] Job status updates are saved to status files
- [ ] Log messages are written to job log files
- [ ] Progress updates are broadcast via WebSocket
- [ ] Logs are accessible via `/api/logs/{job_id}` endpoint
- [ ] Status reflects current execution stage

---

### Task 1.5: Test End-to-End Pipeline Execution

**File**: `tests/integration/test_dashboard_pipeline.py` (NEW)  
**Estimated Time**: 4 hours  
**Complexity**: Medium

#### Description
Create comprehensive integration tests to verify the dashboard can execute the full pipeline.

#### Implementation Steps

1. **Create test fixtures**
   ```python
   import pytest
   from pathlib import Path
   import asyncio
   
   @pytest.fixture
   def test_job_data():
       return {
           "id": "test-pipeline-001",
           "filename": "test.pdf",
           "config": {
               "pillar_selections": ["Pillar_1"],
               "run_mode": "ONCE"
           }
       }
   
   @pytest.fixture
   def job_runner():
       from webdashboard.job_runner import PipelineJobRunner
       runner = PipelineJobRunner(max_workers=1)
       return runner
   ```

2. **Test job queuing and execution**
   ```python
   @pytest.mark.asyncio
   async def test_job_execution(job_runner, test_job_data):
       """Test that jobs execute and complete"""
       # Start runner
       runner_task = asyncio.create_task(job_runner.start())
       
       # Enqueue job
       await job_runner.enqueue_job(
           test_job_data["id"],
           test_job_data
       )
       
       # Wait for completion (with timeout)
       max_wait = 300  # 5 minutes
       waited = 0
       while waited < max_wait:
           if test_job_data["id"] not in job_runner.get_running_jobs():
               break
           await asyncio.sleep(1)
           waited += 1
       
       # Verify job completed
       assert waited < max_wait, "Job timed out"
       
       # Check status file
       status_file = Path(f"workspace/status/{test_job_data['id']}.json")
       assert status_file.exists()
       
       with open(status_file) as f:
           status = json.load(f)
       
       assert status["status"] in ["completed", "failed"]
       
       # Cleanup
       runner_task.cancel()
   ```

3. **Test API integration**
   ```python
   from fastapi.testclient import TestClient
   
   def test_upload_and_execute(test_client: TestClient):
       """Test full workflow: upload → queue → execute"""
       # Upload file
       with open("tests/fixtures/test.pdf", "rb") as f:
           response = test_client.post(
               "/api/upload",
               files={"file": ("test.pdf", f, "application/pdf")},
               headers={"X-API-KEY": "dev-key-change-in-production"}
           )
       
       assert response.status_code == 200
       job_id = response.json()["job_id"]
       
       # Wait for job to process
       import time
       max_wait = 300
       for _ in range(max_wait):
           job_response = test_client.get(
               f"/api/jobs/{job_id}",
               headers={"X-API-KEY": "dev-key-change-in-production"}
           )
           status = job_response.json()["status"]
           
           if status in ["completed", "failed"]:
               break
           
           time.sleep(1)
       
       assert status == "completed"
   ```

#### Acceptance Criteria
- [ ] Jobs can be queued and executed via API
- [ ] Pipeline runs to completion without errors
- [ ] Status transitions correctly (queued → running → completed)
- [ ] Output files are generated in job directory
- [ ] Logs are created and accessible
- [ ] Tests pass consistently

---

## Phase 1 Deliverables

- [ ] `webdashboard/job_runner.py` - Background job processing
- [ ] `literature_review/orchestrator_integration.py` - Enhanced wrapper
- [ ] Modified `literature_review/orchestrator.py` - Accepts config parameter
- [ ] Modified `webdashboard/app.py` - Integrated with JobRunner
- [ ] `tests/integration/test_dashboard_pipeline.py` - E2E tests
- [ ] Documentation of new architecture

## Success Metrics

1. **Functional**: Dashboard can execute full pipeline without manual intervention
2. **Reliability**: 95%+ success rate for job execution
3. **Performance**: Jobs complete in similar time to terminal execution
4. **Stability**: No memory leaks or zombie processes
5. **Compatibility**: Terminal mode still works unchanged

## Known Limitations (Phase 1)

- Single file upload only (batch upload in Phase 2)
- No interactive pillar selection UI (Phase 2)
- Basic progress tracking only (enhanced in Phase 3)
- No results visualization (Phase 4)
- No interactive prompts via WebSocket (Phase 5)

## Next Phase

After Phase 1 completion, proceed to **Phase 2: Input Handling** to implement batch uploads and job configuration UI.
