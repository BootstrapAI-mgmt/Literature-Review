# Phase 5: Interactive Prompts & Full 1:1 Parity

**Priority**: 🟡 MEDIUM  
**Timeline**: Week 3  
**Dependencies**: Phase 1, 2, 3 Complete  
**Status**: 📋 Ready After Phases 1-3

## Overview

Implement the final piece for complete 1:1 parity with terminal experience: interactive prompts handled via WebSocket, allowing the dashboard to pause execution and ask user for decisions exactly like the terminal version.

## Success Criteria

- [ ] Dashboard can pause job for user input
- [ ] User prompts appear as modal dialogs
- [ ] User can make selections (pillar choices, mode changes)
- [ ] Job resumes after user provides input
- [ ] All terminal prompts have dashboard equivalents
- [ ] Timeout handling for inactive users

## Task Cards

### Task 5.1: Prompt Handler System

**File**: `webdashboard/prompt_handler.py` (NEW)  
**Estimated Time**: 5 hours  
**Complexity**: High

#### Description
Create system for pausing job execution, sending prompts to user via WebSocket, and resuming with user's response.

#### Implementation Steps

1. **Create PromptHandler class**
   ```python
   import asyncio
   from typing import Any, Optional, Dict
   from datetime import datetime, timedelta
   import uuid
   
   class PromptHandler:
       """Handles interactive prompts for jobs"""
       
       def __init__(self):
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
           
           Args:
               job_id: Job identifier
               prompt_type: Type of prompt ('pillar_selection', 'run_mode', 'continue')
               prompt_data: Data for the prompt (options, message, etc.)
               timeout_seconds: How long to wait for response
           
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
           
           # Broadcast prompt to WebSocket clients
           await self._broadcast_prompt(job_id, prompt_id, prompt_type, prompt_data)
           
           try:
               # Wait for response with timeout
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
           """
           future = self.pending_prompts.get(prompt_id)
           
           if not future or future.done():
               raise ValueError(f"No pending prompt with ID {prompt_id}")
           
           # Resolve future with response
           future.set_result(response)
           
           # Clean up
           self.pending_prompts.pop(prompt_id, None)
           self.prompt_timeouts.pop(prompt_id, None)
       
       def get_pending_prompts(self, job_id: str) -> list:
           """Get list of pending prompts for a job"""
           # Note: Would need to track job_id with prompts
           # Simplified for example
           return list(self.pending_prompts.keys())
   
   # Global instance
   prompt_handler = PromptHandler()
   ```

2. **Add prompt response endpoint**
   ```python
   # In webdashboard/app.py
   
   from webdashboard.prompt_handler import prompt_handler
   from pydantic import BaseModel
   
   class PromptResponse(BaseModel):
       """User response to a prompt"""
       response: Any
   
   @app.post("/api/prompts/{prompt_id}/respond")
   async def respond_to_prompt(
       prompt_id: str,
       response: PromptResponse,
       api_key: str = Header(None, alias="X-API-KEY")
   ):
       """
       Submit user response to a prompt
       
       Args:
           prompt_id: Prompt identifier
           response: User's response
       """
       verify_api_key(api_key)
       
       try:
           prompt_handler.submit_response(prompt_id, response.response)
           return {"status": "success", "prompt_id": prompt_id}
       except ValueError as e:
           raise HTTPException(status_code=404, detail=str(e))
   ```

#### Acceptance Criteria
- [ ] PromptHandler can create and track prompts
- [ ] Prompts are broadcast via WebSocket
- [ ] Responses are received and routed correctly
- [ ] Timeouts are handled gracefully
- [ ] Multiple simultaneous prompts are supported

---

### Task 5.2: Integrate Prompts into Orchestrator

**File**: `literature_review/orchestrator.py` (MODIFY)  
**Estimated Time**: 4 hours  
**Complexity**: High

#### Description
Modify orchestrator to use PromptHandler instead of terminal `input()` when running in dashboard mode.

#### Implementation Steps

1. **Add prompt callback to OrchestratorConfig**
   ```python
   class OrchestratorConfig:
       """Configuration for orchestrator execution"""
       def __init__(
           self,
           job_id: str,
           analysis_target: List[str],
           run_mode: str,
           skip_user_prompts: bool = True,
           progress_callback: Optional[Callable] = None,
           log_callback: Optional[Callable] = None,
           prompt_callback: Optional[Callable] = None  # NEW
       ):
           self.job_id = job_id
           self.analysis_target = analysis_target
           self.run_mode = run_mode
           self.skip_user_prompts = skip_user_prompts
           self.progress_callback = progress_callback
           self.log_callback = log_callback
           self.prompt_callback = prompt_callback
   ```

2. **Modify get_user_analysis_target() to use callback**
   ```python
   async def get_user_analysis_target_async(
       pillar_definitions: Dict,
       prompt_callback: Optional[Callable] = None
   ) -> Tuple[List[str], str]:
       """
       Get analysis target from user (async version for dashboard)
       
       Args:
           pillar_definitions: Available pillars
           prompt_callback: Async callback for prompts (if None, uses terminal input)
       
       Returns:
           (pillar_list, run_mode)
       """
       metadata_sections = {'Framework_Overview', 'Cross_Cutting_Requirements', 'Success_Criteria'}
       analyzable_pillars = [k for k in pillar_definitions.keys() if k not in metadata_sections]
       
       if prompt_callback is None:
           # Terminal mode - original behavior
           safe_print("\n--- No new data detected ---")
           safe_print("What would you like to re-assess?")
           
           for i, name in enumerate(analyzable_pillars, 1):
               safe_print(f"  {i}. {name.split(':')[0]}")
           safe_print(f"\n  ALL - Run analysis on all pillars (one pass)")
           safe_print(f"  DEEP - Run iterative deep-review loop on all pillars")
           safe_print(f"  NONE - Exit (default)")
           
           choice = input(f"Enter choice (1-{len(analyzable_pillars)}, ALL, DEEP, NONE): ").strip().upper()
       else:
           # Dashboard mode - use prompt callback
           choice = await prompt_callback(
               prompt_type="pillar_selection",
               prompt_data={
                   "message": "Select pillars to analyze",
                   "options": analyzable_pillars,
                   "allow_all": True,
                   "allow_deep": True,
                   "allow_none": True
               }
           )
       
       # Parse response (same logic for both modes)
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

3. **Create wrapper for async prompts in sync context**
   ```python
   def get_user_analysis_target(
       pillar_definitions: Dict,
       prompt_callback: Optional[Callable] = None
   ) -> Tuple[List[str], str]:
       """
       Sync wrapper for get_user_analysis_target_async
       """
       if prompt_callback is None:
           # Terminal mode - use original sync code
           # ... (existing terminal code) ...
           pass
       else:
           # Dashboard mode - run async callback
           import asyncio
           loop = asyncio.new_event_loop()
           asyncio.set_event_loop(loop)
           try:
               return loop.run_until_complete(
                   get_user_analysis_target_async(pillar_definitions, prompt_callback)
               )
           finally:
               loop.close()
   ```

4. **Integrate into main()**
   ```python
   def main(config: Optional[OrchestratorConfig] = None):
       """Main orchestrator with prompt support"""
       
       # ... initialization ...
       
       # Determine run mode
       if has_new_data:
           # Auto-analyze all pillars
           analysis_target_pillars = [k for k in definitions.keys() if k not in metadata_sections]
           run_mode = "DEEP_LOOP"
       else:
           if config and config.prompt_callback:
               # Dashboard mode with prompts
               analysis_target_pillars, run_mode = get_user_analysis_target(
                   definitions,
                   prompt_callback=config.prompt_callback
               )
           elif config and config.skip_user_prompts:
               # Dashboard mode without prompts (use config)
               analysis_target_pillars = config.analysis_target
               run_mode = config.run_mode
           else:
               # Terminal mode
               analysis_target_pillars, run_mode = get_user_analysis_target(definitions)
       
       # ... rest of orchestrator ...
   ```

#### Acceptance Criteria
- [ ] Orchestrator can use async prompt callbacks
- [ ] Terminal mode still works unchanged
- [ ] Dashboard mode pauses for user input
- [ ] Prompts are properly formatted
- [ ] Responses are validated

---

### Task 5.3: Prompt UI Components

**File**: `webdashboard/templates/index.html` (MODIFY)  
**Estimated Time**: 5 hours  
**Complexity**: Medium

#### Description
Create UI modals for displaying prompts and collecting user responses.

#### Implementation Steps

1. **Add prompt modal**
   ```html
   <!-- Interactive Prompt Modal -->
   <div class="modal fade" id="promptModal" tabindex="-1" data-bs-backdrop="static">
       <div class="modal-dialog">
           <div class="modal-content">
               <div class="modal-header bg-warning">
                   <h5 class="modal-title">
                       ⏸️ Job Paused - Input Required
                   </h5>
               </div>
               <div class="modal-body">
                   <div class="alert alert-info">
                       <strong>Job ID:</strong> <span id="promptJobId"></span>
                   </div>
                   
                   <h6 id="promptMessage"></h6>
                   
                   <!-- Prompt content (varies by type) -->
                   <div id="promptContent"></div>
                   
                   <!-- Timeout warning -->
                   <div class="alert alert-warning mt-3">
                       ⏰ Please respond within <span id="promptTimeout">5:00</span>
                   </div>
               </div>
               <div class="modal-footer">
                   <button type="button" class="btn btn-secondary" onclick="cancelPrompt()">
                       Cancel Job
                   </button>
                   <button type="button" class="btn btn-primary" onclick="submitPromptResponse()">
                       Submit
                   </button>
               </div>
           </div>
       </div>
   </div>
   ```

2. **Add JavaScript for prompt handling**
   ```javascript
   let currentPromptId = null;
   let promptTimeoutInterval = null;
   
   // Listen for prompt requests via WebSocket
   function handleWebSocketMessage(data) {
       if (data.type === 'prompt_request') {
           showPrompt(data);
       }
       // ... other message types ...
   }
   
   function showPrompt(promptData) {
       currentPromptId = promptData.prompt_id;
       
       // Set job ID
       document.getElementById('promptJobId').textContent = promptData.job_id;
       
       // Set message
       document.getElementById('promptMessage').textContent = promptData.prompt_data.message;
       
       // Render prompt content based on type
       const content = document.getElementById('promptContent');
       
       switch (promptData.prompt_type) {
           case 'pillar_selection':
               content.innerHTML = renderPillarSelectionPrompt(promptData.prompt_data);
               break;
           case 'run_mode':
               content.innerHTML = renderRunModePrompt(promptData.prompt_data);
               break;
           case 'continue':
               content.innerHTML = renderContinuePrompt(promptData.prompt_data);
               break;
           default:
               content.innerHTML = '<p>Unknown prompt type</p>';
       }
       
       // Start timeout countdown
       startTimeoutCountdown(300); // 5 minutes
       
       // Show modal
       const modal = new bootstrap.Modal(document.getElementById('promptModal'));
       modal.show();
   }
   
   function renderPillarSelectionPrompt(promptData) {
       const pillars = promptData.options || [];
       
       let html = '<div class="mb-3">';
       
       if (promptData.allow_all) {
           html += `
               <div class="form-check">
                   <input class="form-check-input" type="radio" name="promptChoice" value="ALL" id="choice_all">
                   <label class="form-check-label" for="choice_all">
                       <strong>ALL</strong> - Analyze all pillars
                   </label>
               </div>
           `;
       }
       
       if (promptData.allow_deep) {
           html += `
               <div class="form-check">
                   <input class="form-check-input" type="radio" name="promptChoice" value="DEEP" id="choice_deep">
                   <label class="form-check-label" for="choice_deep">
                       <strong>DEEP</strong> - Run iterative deep-review loop
                   </label>
               </div>
           `;
       }
       
       html += '<hr>';
       
       pillars.forEach((pillar, index) => {
           html += `
               <div class="form-check">
                   <input class="form-check-input" type="radio" name="promptChoice" value="${index + 1}" id="choice_${index}">
                   <label class="form-check-label" for="choice_${index}">
                       ${index + 1}. ${pillar.split(':')[0]}
                   </label>
               </div>
           `;
       });
       
       if (promptData.allow_none) {
           html += `
               <hr>
               <div class="form-check">
                   <input class="form-check-input" type="radio" name="promptChoice" value="NONE" id="choice_none">
                   <label class="form-check-label" for="choice_none">
                       <strong>NONE</strong> - Cancel analysis
                   </label>
               </div>
           `;
       }
       
       html += '</div>';
       return html;
   }
   
   function renderRunModePrompt(promptData) {
       return `
           <div class="mb-3">
               <div class="form-check">
                   <input class="form-check-input" type="radio" name="promptChoice" value="ONCE" id="mode_once" checked>
                   <label class="form-check-label" for="mode_once">
                       <strong>ONCE</strong> - Single pass analysis
                   </label>
               </div>
               <div class="form-check">
                   <input class="form-check-input" type="radio" name="promptChoice" value="DEEP_LOOP" id="mode_deep_loop">
                   <label class="form-check-label" for="mode_deep_loop">
                       <strong>DEEP_LOOP</strong> - Iterative analysis until convergence
                   </label>
               </div>
           </div>
       `;
   }
   
   function renderContinuePrompt(promptData) {
       return `
           <p>${promptData.details || 'Continue?'}</p>
           <div class="mb-3">
               <div class="form-check">
                   <input class="form-check-input" type="radio" name="promptChoice" value="yes" id="continue_yes" checked>
                   <label class="form-check-label" for="continue_yes">
                       Yes, continue
                   </label>
               </div>
               <div class="form-check">
                   <input class="form-check-input" type="radio" name="promptChoice" value="no" id="continue_no">
                   <label class="form-check-label" for="continue_no">
                       No, stop here
                   </label>
               </div>
           </div>
       `;
   }
   
   function startTimeoutCountdown(seconds) {
       const display = document.getElementById('promptTimeout');
       let remaining = seconds;
       
       if (promptTimeoutInterval) {
           clearInterval(promptTimeoutInterval);
       }
       
       promptTimeoutInterval = setInterval(() => {
           const minutes = Math.floor(remaining / 60);
           const secs = remaining % 60;
           display.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;
           
           if (remaining <= 0) {
               clearInterval(promptTimeoutInterval);
               alert('Prompt timed out. Job will be cancelled.');
               cancelPrompt();
           }
           
           remaining--;
       }, 1000);
   }
   
   async function submitPromptResponse() {
       const selected = document.querySelector('input[name="promptChoice"]:checked');
       
       if (!selected) {
           alert('Please select an option');
           return;
       }
       
       const response = selected.value;
       const apiKey = document.getElementById('apiKeyInput').value;
       
       try {
           const result = await fetch(`/api/prompts/${currentPromptId}/respond`, {
               method: 'POST',
               headers: {
                   'Content-Type': 'application/json',
                   'X-API-KEY': apiKey
               },
               body: JSON.stringify({ response })
           });
           
           if (!result.ok) throw new Error('Failed to submit response');
           
           // Close modal
           bootstrap.Modal.getInstance(document.getElementById('promptModal')).hide();
           
           // Clear timeout
           if (promptTimeoutInterval) {
               clearInterval(promptTimeoutInterval);
           }
           
           // Show notification
           alert('Response submitted. Job will continue.');
           
       } catch (error) {
           alert('Failed to submit response: ' + error.message);
       }
   }
   
   function cancelPrompt() {
       // Submit "NONE" or cancellation response
       submitPromptResponse();
   }
   ```

#### Acceptance Criteria
- [ ] Prompt modals appear when job pauses
- [ ] All prompt types are rendered correctly
- [ ] User can make selection and submit
- [ ] Timeout countdown is displayed
- [ ] Modal is non-dismissible (backdrop static)

---

### Task 5.4: Integrate Prompt Handler with JobRunner

**File**: `webdashboard/job_runner.py` (MODIFY)  
**Estimated Time**: 3 hours  
**Complexity**: Medium

#### Description
Connect PromptHandler to orchestrator execution in JobRunner.

#### Implementation Steps

1. **Modify _run_orchestrator_sync to use prompt handler**
   ```python
   def _run_orchestrator_sync(self, job_id: str, job_data: dict):
       """Run orchestrator with prompt support"""
       from literature_review.orchestrator_integration import run_pipeline_for_job
       from literature_review.orchestrator import ProgressEvent
       from webdashboard.prompt_handler import prompt_handler
       
       def progress_callback(event: ProgressEvent):
           """Callback for progress events"""
           self._write_progress_event(job_id, event)
           self._write_log(job_id, f"[{event.stage}] {event.message}")
       
       async def prompt_callback(prompt_type: str, prompt_data: dict):
           """Async callback for user prompts"""
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
           log_callback=lambda msg: self._write_log(job_id, msg),
           prompt_callback=prompt_callback  # NEW
       )
   ```

2. **Update orchestrator_integration wrapper**
   ```python
   # In literature_review/orchestrator_integration.py
   
   def run_pipeline_for_job(
       job_id: str,
       pillar_selections: List[str],
       run_mode: str,
       progress_callback: Optional[Callable] = None,
       log_callback: Optional[Callable] = None,
       prompt_callback: Optional[Callable] = None  # NEW
   ) -> Dict:
       """Execute orchestrator pipeline with full callback support"""
       
       config = OrchestratorConfig(
           job_id=job_id,
           analysis_target=pillar_selections,
           run_mode=run_mode,
           skip_user_prompts=(prompt_callback is None),
           progress_callback=progress_callback,
           log_callback=log_callback,
           prompt_callback=prompt_callback  # NEW
       )
       
       # Execute pipeline
       result = orchestrator_main(config)
       
       return result
   ```

#### Acceptance Criteria
- [ ] JobRunner passes prompt callback to orchestrator
- [ ] Prompts are properly awaited during execution
- [ ] Job resumes after receiving response
- [ ] Timeouts cause job to fail gracefully

---

### Task 5.5: Test Interactive Prompts

**File**: `tests/integration/test_interactive_prompts.py` (NEW)  
**Estimated Time**: 4 hours  
**Complexity**: High

#### Implementation Steps

```python
import pytest
import asyncio
from webdashboard.prompt_handler import PromptHandler

@pytest.mark.asyncio
async def test_prompt_handler_basic():
    """Test basic prompt request and response"""
    handler = PromptHandler()
    
    async def respond_after_delay():
        await asyncio.sleep(1)
        handler.submit_response("test-prompt", "ALL")
    
    # Start response task
    asyncio.create_task(respond_after_delay())
    
    # Request prompt (will block until response)
    response = await handler.request_user_input(
        job_id="test-job",
        prompt_type="pillar_selection",
        prompt_data={"options": ["P1", "P2"]},
        timeout_seconds=5
    )
    
    assert response == "ALL"

@pytest.mark.asyncio
async def test_prompt_timeout():
    """Test that prompts timeout correctly"""
    handler = PromptHandler()
    
    with pytest.raises(TimeoutError):
        await handler.request_user_input(
            job_id="test-job",
            prompt_type="pillar_selection",
            prompt_data={"options": ["P1"]},
            timeout_seconds=1  # 1 second timeout
        )

def test_orchestrator_with_prompts():
    """Test orchestrator uses prompt callback"""
    from literature_review.orchestrator import get_user_analysis_target
    
    responses = ["ALL"]
    response_idx = [0]
    
    async def mock_prompt_callback(prompt_type, prompt_data):
        response = responses[response_idx[0]]
        response_idx[0] += 1
        return response
    
    pillars, mode = get_user_analysis_target(
        pillar_definitions={"P1": {}, "P2": {}},
        prompt_callback=mock_prompt_callback
    )
    
    assert mode == "ONCE"
    assert len(pillars) == 2
```

#### Acceptance Criteria
- [ ] Prompt handler tests pass
- [ ] Timeout handling works correctly
- [ ] Orchestrator integration works
- [ ] WebSocket broadcast is tested

---

## Phase 5 Deliverables

- [ ] `webdashboard/prompt_handler.py` - Prompt management system
- [ ] Modified `literature_review/orchestrator.py` - Prompt callback support
- [ ] Modified `webdashboard/job_runner.py` - Prompt integration
- [ ] Modified `webdashboard/templates/index.html` - Prompt UI
- [ ] Modified `webdashboard/app.py` - Prompt response endpoint
- [ ] `tests/integration/test_interactive_prompts.py` - Tests
- [ ] Documentation of interactive prompt system

## Success Metrics

1. **Functionality**: All terminal prompts work in dashboard
2. **UX**: Prompts are clear and easy to respond to
3. **Reliability**: Timeouts and errors handled gracefully
4. **Parity**: 100% feature parity with terminal mode

## Known Limitations (Phase 5)

- Single user per job (no multi-user collaboration)
- WebSocket required (fallback to polling not implemented)
- Prompt history not saved (no replay capability)

## Final Outcome

After Phase 5 completion, the dashboard achieves **full 1:1 parity** with the terminal-based orchestrator:

✅ **Input**: Batch upload, directory processing  
✅ **Execution**: Full pipeline with Judge + Deep Reviewer  
✅ **Progress**: Real-time monitoring with ETA  
✅ **Results**: Complete visualization and download  
✅ **Interaction**: Interactive prompts via WebSocket  

The dashboard is now a **complete replacement** for the terminal experience.
