# Phase 3: Progress Monitoring

**Priority**: 🟠 HIGH  
**Timeline**: Week 2  
**Dependencies**: Phase 1 Complete  
**Status**: 📋 Ready After Phase 1

## Overview

Implement real-time progress tracking and visualization for running jobs, providing users with visibility into pipeline execution similar to (or better than) the terminal output.

## Success Criteria

- [ ] Real-time log streaming to browser via WebSocket
- [ ] Progress percentage and stage tracking displayed
- [ ] Iteration counter for Deep Loop mode
- [ ] Visual progress indicators (progress bars, stage badges)
- [ ] Logs are searchable and filterable
- [ ] ETA estimation for job completion

## Task Cards

### Task 3.1: Enhanced Progress Callback System

**File**: `literature_review/orchestrator.py` (MODIFY)  
**Estimated Time**: 4 hours  
**Complexity**: Medium

#### Description
Modify orchestrator to emit structured progress events instead of just printing to terminal.

#### Implementation Steps

1. **Create ProgressTracker class**
   ```python
   from typing import Callable, Optional, Dict
   from dataclasses import dataclass
   from datetime import datetime
   
   @dataclass
   class ProgressEvent:
       """Structured progress event"""
       timestamp: str
       stage: str  # "judge", "deep_review", "gap_analysis", "visualization"
       phase: str  # "starting", "running", "complete", "error"
       message: str
       percentage: Optional[float] = None
       metadata: Optional[Dict] = None
   
   class ProgressTracker:
       """Tracks and emits pipeline progress events"""
       
       def __init__(self, callback: Optional[Callable] = None):
           self.callback = callback
           self.current_stage = None
           self.stages_completed = []
           
           # Define pipeline stages and weights
           self.stage_weights = {
               "initialization": 5,
               "judge": 15,
               "deep_review": 30,
               "gap_analysis": 35,
               "visualization": 10,
               "finalization": 5
           }
       
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
           
           if self.callback:
               self.callback(event)
           
           # Also log to file
           logger.info(f"[{stage}] {message}")
           
           # Also print to terminal if not suppressed
           if not kwargs.get('suppress_terminal'):
               safe_print(f"[{stage}] {message}")
       
       def calculate_percentage(self, stage: str, phase: str) -> float:
           """Calculate overall completion percentage"""
           total_weight = sum(self.stage_weights.values())
           completed_weight = sum(
               self.stage_weights[s] for s in self.stages_completed
           )
           
           if phase == "complete":
               if stage not in self.stages_completed:
                   self.stages_completed.append(stage)
               completed_weight += self.stage_weights.get(stage, 0)
           elif phase == "running":
               # Stage is partially complete
               completed_weight += self.stage_weights.get(stage, 0) * 0.5
           
           return (completed_weight / total_weight) * 100
   ```

2. **Integrate ProgressTracker into orchestrator.main()**
   ```python
   def main(config: Optional[OrchestratorConfig] = None):
       """Main orchestrator with progress tracking"""
       
       # Initialize progress tracker
       progress_tracker = ProgressTracker(
           callback=config.progress_callback if config else None
       )
       
       progress_tracker.emit("initialization", "starting", "Loading definitions...")
       
       # Load definitions
       try:
           with open(DEFINITIONS_FILE, 'r') as f:
               definitions = json.load(f)
           progress_tracker.emit(
               "initialization", 
               "complete", 
               f"Loaded {len(definitions)} pillar definitions"
           )
       except Exception as e:
           progress_tracker.emit("initialization", "error", str(e))
           return
       
       # ... rest of orchestrator logic with progress events ...
       
       # Judge stage
       if run_initial_judge:
           progress_tracker.emit("judge", "starting", "Running Judge to validate claims...")
           
           if not judge.main():
               progress_tracker.emit("judge", "error", "Judge failed")
               return
           
           progress_tracker.emit("judge", "complete", "Claims validated successfully")
       
       # Analysis loop
       while True:
           iteration_count += 1
           progress_tracker.emit(
               "gap_analysis",
               "running",
               f"Starting iteration {iteration_count}",
               iteration=iteration_count
           )
           
           # ... analysis logic ...
           
           progress_tracker.emit(
               "gap_analysis",
               "running",
               f"Iteration {iteration_count} complete",
               iteration=iteration_count,
               completeness_scores=radar_data
           )
   ```

#### Acceptance Criteria
- [ ] ProgressTracker emits structured events
- [ ] Percentage calculation is accurate
- [ ] Events include stage, phase, and metadata
- [ ] Terminal output still works when no callback provided
- [ ] All major pipeline stages emit progress events

---

### Task 3.2: WebSocket Progress Streaming

**File**: `webdashboard/app.py` (MODIFY)  
**Estimated Time**: 5 hours  
**Complexity**: High

#### Description
Implement WebSocket endpoint for streaming real-time progress updates to connected clients.

#### Implementation Steps

1. **Create job-specific WebSocket endpoint**
   ```python
   @app.websocket("/ws/jobs/{job_id}/progress")
   async def job_progress_stream(websocket: WebSocket, job_id: str):
       """
       WebSocket endpoint for real-time job progress updates
       
       Streams:
       - Progress percentage
       - Stage updates
       - Log messages
       - Iteration counts
       """
       await websocket.accept()
       
       try:
           # Send initial status
           job_data = load_job(job_id)
           if job_data:
               await websocket.send_json({
                   "type": "initial_status",
                   "job": job_data
               })
           
           # Watch for progress updates
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
               
               # Stream progress updates
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
               
               await asyncio.sleep(0.5)  # Poll every 500ms
       
       except WebSocketDisconnect:
           pass
       except Exception as e:
           logger.error(f"WebSocket error for job {job_id}: {e}")
   ```

2. **Modify JobRunner to write progress events**
   ```python
   # In webdashboard/job_runner.py
   
   def _write_progress_event(self, job_id: str, event: ProgressEvent):
       """Write progress event to JSONL file"""
       progress_file = Path(f"workspace/status/{job_id}_progress.jsonl")
       progress_file.parent.mkdir(parents=True, exist_ok=True)
       
       with open(progress_file, 'a') as f:
           f.write(json.dumps(event.__dict__) + '\n')
   
   def _run_orchestrator_sync(self, job_id: str, job_data: dict):
       """Run orchestrator with progress tracking"""
       from literature_review.orchestrator_integration import run_pipeline_for_job
       from literature_review.orchestrator import ProgressEvent
       
       def progress_callback(event: ProgressEvent):
           """Callback for progress events"""
           # Write to progress file
           self._write_progress_event(job_id, event)
           
           # Also write to log
           self._write_log(job_id, f"[{event.stage}] {event.message}")
       
       config = job_data.get("config", {})
       
       return run_pipeline_for_job(
           job_id=job_id,
           pillar_selections=config.get("pillar_selections", ["ALL"]),
           run_mode=config.get("run_mode", "ONCE"),
           progress_callback=progress_callback,
           log_callback=lambda msg: self._write_log(job_id, msg)
       )
   ```

#### Acceptance Criteria
- [ ] WebSocket streams progress events in real-time
- [ ] Multiple clients can connect to same job
- [ ] Connection handles job completion gracefully
- [ ] Progress file format is JSONL for easy parsing
- [ ] Disconnections are handled properly

---

### Task 3.3: Progress Visualization UI

**File**: `webdashboard/templates/index.html` (MODIFY)  
**Estimated Time**: 6 hours  
**Complexity**: Medium

#### Description
Create UI components to display real-time progress updates in an informative and visually appealing way.

#### Implementation Steps

1. **Add progress display to job detail modal**
   ```html
   <!-- Enhanced Job Detail Modal -->
   <div class="modal-body">
       <!-- Existing job info ... -->
       
       <!-- NEW: Real-time Progress Display -->
       <div id="progressContainer" style="display: none;">
           <h6>Pipeline Progress</h6>
           
           <!-- Overall Progress Bar -->
           <div class="mb-3">
               <div class="d-flex justify-content-between mb-1">
                   <span>Overall Completion</span>
                   <span id="progressPercentage">0%</span>
               </div>
               <div class="progress">
                   <div 
                       class="progress-bar progress-bar-striped progress-bar-animated" 
                       id="progressBar"
                       role="progressbar" 
                       style="width: 0%">
                   </div>
               </div>
           </div>
           
           <!-- Stage Indicators -->
           <div class="mb-3">
               <h6 class="small">Pipeline Stages</h6>
               <div id="stageIndicators">
                   <div class="stage-item" data-stage="initialization">
                       <span class="badge bg-secondary">⏸</span> Initialization
                   </div>
                   <div class="stage-item" data-stage="judge">
                       <span class="badge bg-secondary">⏸</span> Judge Validation
                   </div>
                   <div class="stage-item" data-stage="deep_review">
                       <span class="badge bg-secondary">⏸</span> Deep Review
                       <span class="iteration-counter" style="display: none;"></span>
                   </div>
                   <div class="stage-item" data-stage="gap_analysis">
                       <span class="badge bg-secondary">⏸</span> Gap Analysis
                       <span class="iteration-counter" style="display: none;"></span>
                   </div>
                   <div class="stage-item" data-stage="visualization">
                       <span class="badge bg-secondary">⏸</span> Visualization
                   </div>
                   <div class="stage-item" data-stage="finalization">
                       <span class="badge bg-secondary">⏸</span> Finalization
                   </div>
               </div>
           </div>
           
           <!-- Live Logs -->
           <div class="mb-3">
               <div class="d-flex justify-content-between align-items-center mb-2">
                   <h6 class="small mb-0">Live Logs</h6>
                   <div class="btn-group btn-group-sm" role="group">
                       <button type="button" class="btn btn-outline-secondary" onclick="clearLogs()">
                           Clear
                       </button>
                       <button type="button" class="btn btn-outline-secondary" onclick="toggleAutoScroll()">
                           <span id="autoScrollIcon">🔒</span> Auto-scroll
                       </button>
                   </div>
               </div>
               <div class="log-viewer-live" id="liveLogViewer">
                   <div class="text-muted text-center p-3">
                       Waiting for logs...
                   </div>
               </div>
           </div>
       </div>
   </div>
   ```

2. **Add CSS for progress display**
   ```css
   <style>
       .stage-item {
           padding: 8px;
           margin: 4px 0;
           border-left: 3px solid #dee2e6;
           background: #f8f9fa;
           transition: all 0.3s;
       }
       
       .stage-item.active {
           border-left-color: #0d6efd;
           background: #e7f1ff;
       }
       
       .stage-item.complete {
           border-left-color: #198754;
           background: #d1e7dd;
       }
       
       .stage-item.error {
           border-left-color: #dc3545;
           background: #f8d7da;
       }
       
       .iteration-counter {
           font-size: 0.875rem;
           color: #6c757d;
           margin-left: 8px;
       }
       
       .log-viewer-live {
           background-color: #1e1e1e;
           color: #d4d4d4;
           font-family: 'Courier New', monospace;
           font-size: 0.875rem;
           padding: 15px;
           border-radius: 5px;
           max-height: 400px;
           overflow-y: auto;
           white-space: pre-wrap;
           word-wrap: break-word;
       }
       
       .log-line {
           margin: 2px 0;
       }
       
       .log-line.error {
           color: #f48771;
       }
       
       .log-line.warning {
           color: #dcdcaa;
       }
       
       .log-line.success {
           color: #4ec9b0;
       }
   </style>
   ```

3. **Add JavaScript for WebSocket connection**
   ```javascript
   let progressWebSocket = null;
   let autoScroll = true;
   
   function connectProgressWebSocket(jobId) {
       // Close existing connection
       if (progressWebSocket) {
           progressWebSocket.close();
       }
       
       // Connect to job-specific progress stream
       const wsUrl = `ws://${window.location.host}/ws/jobs/${jobId}/progress`;
       progressWebSocket = new WebSocket(wsUrl);
       
       progressWebSocket.onopen = () => {
           console.log('Progress WebSocket connected');
           document.getElementById('progressContainer').style.display = 'block';
       };
       
       progressWebSocket.onmessage = (event) => {
           const data = JSON.parse(event.data);
           
           switch (data.type) {
               case 'initial_status':
                   handleInitialStatus(data.job);
                   break;
               case 'progress':
                   handleProgressEvent(data.event);
                   break;
               case 'logs':
                   handleLogLines(data.lines);
                   break;
               case 'job_complete':
                   handleJobComplete(data.status);
                   break;
           }
       };
       
       progressWebSocket.onerror = (error) => {
           console.error('Progress WebSocket error:', error);
       };
       
       progressWebSocket.onclose = () => {
           console.log('Progress WebSocket disconnected');
       };
   }
   
   function handleProgressEvent(event) {
       // Update progress bar
       if (event.percentage !== null) {
           const progressBar = document.getElementById('progressBar');
           const progressPercentage = document.getElementById('progressPercentage');
           
           progressBar.style.width = event.percentage + '%';
           progressPercentage.textContent = event.percentage.toFixed(1) + '%';
       }
       
       // Update stage indicator
       const stageItem = document.querySelector(`[data-stage="${event.stage}"]`);
       if (stageItem) {
           const badge = stageItem.querySelector('.badge');
           const iterationCounter = stageItem.querySelector('.iteration-counter');
           
           // Remove all status classes
           stageItem.classList.remove('active', 'complete', 'error');
           
           switch (event.phase) {
               case 'starting':
               case 'running':
                   stageItem.classList.add('active');
                   badge.className = 'badge bg-primary';
                   badge.textContent = '⏳';
                   break;
               case 'complete':
                   stageItem.classList.add('complete');
                   badge.className = 'badge bg-success';
                   badge.textContent = '✅';
                   break;
               case 'error':
                   stageItem.classList.add('error');
                   badge.className = 'badge bg-danger';
                   badge.textContent = '❌';
                   break;
           }
           
           // Show iteration counter if present
           if (event.metadata && event.metadata.iteration) {
               iterationCounter.textContent = `(Iteration ${event.metadata.iteration})`;
               iterationCounter.style.display = 'inline';
           }
       }
       
       // Add log line for event
       appendLogLine(`[${event.stage}] ${event.message}`, getLogClass(event.phase));
   }
   
   function handleLogLines(lines) {
       lines.forEach(line => {
           appendLogLine(line.trim());
       });
   }
   
   function appendLogLine(text, cssClass = '') {
       const logViewer = document.getElementById('liveLogViewer');
       
       // Remove "waiting" message if present
       if (logViewer.querySelector('.text-muted')) {
           logViewer.innerHTML = '';
       }
       
       const logLine = document.createElement('div');
       logLine.className = 'log-line ' + cssClass;
       logLine.textContent = text;
       
       logViewer.appendChild(logLine);
       
       // Auto-scroll if enabled
       if (autoScroll) {
           logViewer.scrollTop = logViewer.scrollHeight;
       }
   }
   
   function getLogClass(phase) {
       switch (phase) {
           case 'error':
               return 'error';
           case 'complete':
               return 'success';
           case 'running':
               return '';
           default:
               return '';
       }
   }
   
   function clearLogs() {
       document.getElementById('liveLogViewer').innerHTML = '';
   }
   
   function toggleAutoScroll() {
       autoScroll = !autoScroll;
       const icon = document.getElementById('autoScrollIcon');
       icon.textContent = autoScroll ? '🔒' : '🔓';
   }
   
   function handleJobComplete(status) {
       const progressBar = document.getElementById('progressBar');
       progressBar.classList.remove('progress-bar-animated');
       
       if (status === 'completed') {
           progressBar.classList.add('bg-success');
           progressBar.style.width = '100%';
           document.getElementById('progressPercentage').textContent = '100%';
       } else {
           progressBar.classList.add('bg-danger');
       }
   }
   
   // Modify showJobDetail to connect WebSocket
   async function showJobDetail(jobId) {
       // ... existing code ...
       
       // Connect to progress stream if job is running
       const job = await fetchJobDetails(jobId);
       if (job.status === 'running' || job.status === 'queued') {
           connectProgressWebSocket(jobId);
       }
       
       // ... rest of existing code ...
   }
   ```

#### Acceptance Criteria
- [ ] Progress bar updates in real-time
- [ ] Stage indicators show current pipeline phase
- [ ] Iteration counters display for Deep Loop mode
- [ ] Live logs stream and auto-scroll
- [ ] UI is responsive and doesn't freeze
- [ ] WebSocket reconnects on disconnect

---

### Task 3.4: ETA Estimation

**File**: `webdashboard/job_runner.py` (MODIFY)  
**Estimated Time**: 3 hours  
**Complexity**: Medium

#### Description
Add estimated time to completion based on historical job performance and current progress.

#### Implementation Steps

1. **Create ETA calculator**
   ```python
   from datetime import datetime, timedelta
   from typing import Optional
   
   class ETACalculator:
       """Estimates time to completion for pipeline jobs"""
       
       def __init__(self):
           self.stage_history = {}  # stage -> list of durations
       
       def record_stage_duration(self, stage: str, duration: float):
           """Record how long a stage took"""
           if stage not in self.stage_history:
               self.stage_history[stage] = []
           
           self.stage_history[stage].append(duration)
           
           # Keep last 10 measurements
           if len(self.stage_history[stage]) > 10:
               self.stage_history[stage].pop(0)
       
       def estimate_eta(
           self,
           current_stage: str,
           stage_started_at: datetime,
           remaining_stages: list
       ) -> Optional[timedelta]:
           """
           Estimate time to completion
           
           Args:
               current_stage: Stage currently executing
               stage_started_at: When current stage started
               remaining_stages: List of stages still to execute
           
           Returns:
               Estimated time remaining
           """
           # Estimate current stage remaining time
           if current_stage in self.stage_history:
               avg_duration = sum(self.stage_history[current_stage]) / len(self.stage_history[current_stage])
               elapsed = (datetime.utcnow() - stage_started_at).total_seconds()
               current_stage_remaining = max(0, avg_duration - elapsed)
           else:
               # No historical data, use default
               current_stage_remaining = 60  # 1 minute default
           
           # Estimate remaining stages
           remaining_time = current_stage_remaining
           
           for stage in remaining_stages:
               if stage in self.stage_history:
                   remaining_time += sum(self.stage_history[stage]) / len(self.stage_history[stage])
               else:
                   # Default estimates per stage
                   defaults = {
                       "judge": 180,  # 3 minutes
                       "deep_review": 300,  # 5 minutes
                       "gap_analysis": 240,  # 4 minutes
                       "visualization": 60  # 1 minute
                   }
                   remaining_time += defaults.get(stage, 60)
           
           return timedelta(seconds=remaining_time)
   ```

2. **Integrate ETA into progress events**
   ```python
   # In orchestrator.py ProgressTracker
   
   def __init__(self, callback: Optional[Callable] = None):
       self.callback = callback
       self.current_stage = None
       self.stages_completed = []
       self.stage_start_times = {}
       self.eta_calculator = ETACalculator()
   
   def emit(self, stage: str, phase: str, message: str, **kwargs):
       """Emit progress event with ETA"""
       
       # Track stage timing
       if phase == "starting":
           self.stage_start_times[stage] = datetime.utcnow()
           self.current_stage = stage
       elif phase == "complete" and stage in self.stage_start_times:
           duration = (datetime.utcnow() - self.stage_start_times[stage]).total_seconds()
           self.eta_calculator.record_stage_duration(stage, duration)
       
       # Calculate ETA
       eta = None
       if self.current_stage and self.current_stage in self.stage_start_times:
           remaining_stages = [
               s for s in self.stage_weights.keys()
               if s not in self.stages_completed and s != self.current_stage
           ]
           eta = self.eta_calculator.estimate_eta(
               self.current_stage,
               self.stage_start_times[self.current_stage],
               remaining_stages
           )
       
       event = ProgressEvent(
           timestamp=datetime.utcnow().isoformat(),
           stage=stage,
           phase=phase,
           message=message,
           percentage=self.calculate_percentage(stage, phase),
           metadata={
               **kwargs,
               "eta_seconds": eta.total_seconds() if eta else None
           }
       )
       
       if self.callback:
           self.callback(event)
   ```

3. **Display ETA in UI**
   ```javascript
   function handleProgressEvent(event) {
       // ... existing progress updates ...
       
       // Update ETA display
       if (event.metadata && event.metadata.eta_seconds) {
           const etaElement = document.getElementById('etaDisplay');
           if (etaElement) {
               const minutes = Math.floor(event.metadata.eta_seconds / 60);
               const seconds = Math.floor(event.metadata.eta_seconds % 60);
               etaElement.textContent = `ETA: ${minutes}m ${seconds}s`;
           }
       }
   }
   ```

#### Acceptance Criteria
- [ ] ETA is calculated based on historical data
- [ ] ETA updates as job progresses
- [ ] ETA is displayed in UI
- [ ] Accuracy improves with more job history
- [ ] ETA handles jobs with no historical data

---

### Task 3.5: Test Progress Monitoring

**File**: `tests/integration/test_progress_monitoring.py` (NEW)  
**Estimated Time**: 4 hours  
**Complexity**: Medium

#### Description
Create tests to verify progress tracking works correctly.

#### Implementation Steps

1. **Test progress event emission**
   ```python
   def test_progress_tracker_emits_events():
       """Test that ProgressTracker emits events correctly"""
       events = []
       
       def callback(event):
           events.append(event)
       
       tracker = ProgressTracker(callback=callback)
       
       tracker.emit("judge", "starting", "Starting Judge")
       tracker.emit("judge", "complete", "Judge complete")
       
       assert len(events) == 2
       assert events[0].stage == "judge"
       assert events[0].phase == "starting"
       assert events[1].phase == "complete"
   ```

2. **Test WebSocket streaming**
   ```python
   @pytest.mark.asyncio
   async def test_progress_websocket_streaming():
       """Test WebSocket streams progress correctly"""
       job_id = "test-progress-001"
       
       # Create test job and start it
       create_and_start_test_job(job_id)
       
       # Connect WebSocket client
       async with websockets.connect(f'ws://localhost:8000/ws/jobs/{job_id}/progress') as ws:
           # Receive initial status
           msg = await ws.recv()
           data = json.loads(msg)
           assert data['type'] == 'initial_status'
           
           # Receive progress events
           events_received = 0
           timeout = 60  # 1 minute
           
           try:
               async with asyncio.timeout(timeout):
                   while events_received < 5:
                       msg = await ws.recv()
                       data = json.loads(msg)
                       
                       if data['type'] == 'progress':
                           events_received += 1
                           assert 'event' in data
                           assert 'percentage' in data['event']
           except asyncio.TimeoutError:
               pass
           
           assert events_received > 0
   ```

3. **Test ETA calculation**
   ```python
   def test_eta_calculator():
       """Test ETA estimation"""
       calculator = ETACalculator()
       
       # Record some stage durations
       calculator.record_stage_duration("judge", 120)
       calculator.record_stage_duration("judge", 130)
       calculator.record_stage_duration("judge", 110)
       
       # Estimate ETA
       start_time = datetime.utcnow() - timedelta(seconds=60)
       eta = calculator.estimate_eta(
           current_stage="judge",
           stage_started_at=start_time,
           remaining_stages=["gap_analysis", "visualization"]
       )
       
       assert eta is not None
       assert eta.total_seconds() > 0
   ```

#### Acceptance Criteria
- [ ] Progress events are emitted correctly
- [ ] WebSocket streams events in real-time
- [ ] ETA calculation is reasonable
- [ ] Tests pass consistently
- [ ] No race conditions or timing issues

---

## Phase 3 Deliverables

- [ ] Modified `literature_review/orchestrator.py` - ProgressTracker class
- [ ] Modified `webdashboard/app.py` - Progress WebSocket endpoint
- [ ] Modified `webdashboard/job_runner.py` - Progress event writing
- [ ] Modified `webdashboard/templates/index.html` - Progress UI
- [ ] `tests/integration/test_progress_monitoring.py` - Tests
- [ ] Documentation of progress monitoring system

## Success Metrics

1. **Visibility**: Users can see real-time progress updates
2. **Accuracy**: Progress percentage reflects actual completion
3. **Performance**: Updates stream with <1 second latency
4. **Reliability**: WebSocket handles disconnects gracefully
5. **Usability**: ETA provides reasonable time estimates

## Known Limitations (Phase 3)

- ETA is estimate only (may not be accurate for first run)
- WebSocket requires HTTP/1.1 (not HTTP/2)
- Progress file can grow large for long jobs
- No progress replay for historical jobs

## Next Phase

After Phase 3 completion, proceed to **Phase 4: Results Visualization** to implement output file viewing and downloading.
