# ENHANCE-P5-3: Add Prompt History to Job Metadata

**Category:** Interactive Prompts Enhancement  
**Priority:** 🟢 LOW  
**Effort:** 3 hours  
**Created:** November 17, 2025  
**Source:** PR #46 Review - Deferred Items Section #3

---

## Problem Statement

Past prompts and responses are not saved to job metadata. Once a job completes, there's no record of user decisions made during execution.

**Current Limitation:**
- Prompts only exist in memory during job execution
- No audit trail of user decisions
- Cannot reproduce interactive job runs
- No visibility into what choices led to specific results

---

## Use Cases

### 1. Job Audit
**Scenario:** User reviews completed job from last week  
**Question:** "Did I run this with ALL pillars or just one?"  
**Current:** No way to know  
**Desired:** View prompt history showing "Pillar Selection: ALL"

### 2. Reproducibility
**Scenario:** User wants to re-run job with same choices  
**Current:** Must remember and manually configure  
**Desired:** "Replay with same prompts" button

### 3. Compliance & Tracking
**Scenario:** Research team needs audit trail of decisions  
**Current:** No record of interactive choices  
**Desired:** Export job metadata including all user decisions

### 4. Debugging
**Scenario:** Job produced unexpected results  
**Question:** "What did I select for run_mode?"  
**Current:** Unknown  
**Desired:** View timeline of all prompts and responses

---

## Acceptance Criteria

- [ ] Prompt responses saved to job JSON file
- [ ] Display in job details modal (new "User Decisions" section)
- [ ] Include prompt metadata: type, response, timestamp, timeout status
- [ ] Filter/search by prompt type in UI
- [ ] Export prompt history with job results (ZIP download)
- [ ] Backward compatible (jobs without history still display)
- [ ] "Replay job" button to recreate config from prompt history

---

## Data Structure

### Job Metadata Schema

**File:** `workspace/jobs/<job_id>/job_data.json`

```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "created_at": "2025-11-17T10:00:00Z",
  "completed_at": "2025-11-17T10:45:00Z",
  
  "prompts": [
    {
      "prompt_id": "prompt_xyz789",
      "type": "pillar_selection",
      "response": "ALL",
      "timestamp": "2025-11-17T10:01:30Z",
      "timeout_seconds": 300,
      "timed_out": false,
      "prompt_data": {
        "message": "Select which pillars to analyze",
        "options": ["ALL", "DEEP", "P1: ...", "NONE"]
      }
    },
    {
      "prompt_id": "prompt_abc456",
      "type": "run_mode",
      "response": "DEEP_LOOP",
      "timestamp": "2025-11-17T10:02:15Z",
      "timeout_seconds": 120,
      "timed_out": false,
      "prompt_data": {
        "message": "Select analysis mode",
        "options": ["ONCE", "DEEP_LOOP"],
        "default": "ONCE"
      }
    },
    {
      "prompt_id": "prompt_def123",
      "type": "continue",
      "response": "No",
      "timestamp": "2025-11-17T10:30:00Z",
      "timeout_seconds": 60,
      "timed_out": false,
      "prompt_data": {
        "message": "Iteration 2 complete. Continue deep review loop?",
        "iteration": 2,
        "gap_count": 3
      }
    }
  ],
  
  "results": { ... }
}
```

### Legacy Support

Jobs created before this enhancement won't have `prompts` field:

```python
prompts = job_data.get('prompts', [])
if not prompts:
    # Show message: "No prompt history available (job created before feature)"
    pass
```

---

## Implementation Plan

### 1. Update PromptHandler to Save History

**File:** `webdashboard/prompt_handler.py`

```python
class PromptHandler:
    async def submit_response(self, prompt_id: str, response: str) -> bool:
        """Submit user response to pending prompt"""
        if prompt_id not in self.pending_prompts:
            return False
        
        prompt_info = self.pending_prompts[prompt_id]
        job_id = prompt_info['job_id']
        
        # Cancel timeout task
        timeout_task = self.timeout_tasks.get(prompt_id)
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()
        
        # Resolve prompt
        prompt_info['future'].set_result(response)
        
        # NEW: Save to job metadata
        await self._save_prompt_to_history(
            job_id=job_id,
            prompt_id=prompt_id,
            prompt_type=prompt_info['type'],
            response=response,
            prompt_data=prompt_info['data'],
            timeout_seconds=prompt_info['timeout'],
            timed_out=False
        )
        
        # Cleanup
        del self.pending_prompts[prompt_id]
        if prompt_id in self.timeout_tasks:
            del self.timeout_tasks[prompt_id]
        
        return True
    
    async def _save_prompt_to_history(
        self,
        job_id: str,
        prompt_id: str,
        prompt_type: str,
        response: str,
        prompt_data: dict,
        timeout_seconds: int,
        timed_out: bool
    ):
        """Save prompt response to job metadata"""
        from datetime import datetime, timezone
        import json
        
        job_file = f"workspace/jobs/{job_id}/job_data.json"
        
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
```

**Also update timeout handler:**

```python
async def _handle_timeout(self, prompt_id: str):
    """Handle prompt timeout"""
    if prompt_id in self.pending_prompts:
        prompt_info = self.pending_prompts[prompt_id]
        job_id = prompt_info['job_id']
        
        # NEW: Save timeout to history
        await self._save_prompt_to_history(
            job_id=job_id,
            prompt_id=prompt_id,
            prompt_type=prompt_info['type'],
            response=None,  # No response on timeout
            prompt_data=prompt_info['data'],
            timeout_seconds=prompt_info['timeout'],
            timed_out=True  # Mark as timed out
        )
        
        # Cancel job
        prompt_info['future'].set_exception(TimeoutError("Prompt timed out"))
        # ... rest of timeout logic
```

---

### 2. Update Job Details UI

**File:** `webdashboard/templates/index.html`

Add new section to job details modal:

```javascript
function renderJobDetails(jobId) {
    const job = jobs[jobId];
    
    // Existing sections: Status, Progress, Results...
    
    // NEW: Prompt History Section
    let promptHistoryHtml = '';
    if (job.prompts && job.prompts.length > 0) {
        promptHistoryHtml = `
            <h5 class="mt-4">User Decisions</h5>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Prompt Type</th>
                            <th>Response</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${job.prompts.map(p => `
                            <tr>
                                <td>${new Date(p.timestamp).toLocaleString()}</td>
                                <td><span class="badge bg-info">${p.type}</span></td>
                                <td><strong>${p.response || 'N/A'}</strong></td>
                                <td>
                                    ${p.timed_out 
                                        ? '<span class="badge bg-danger">Timed Out</span>' 
                                        : '<span class="badge bg-success">Responded</span>'}
                                </td>
                            </tr>
                            <tr>
                                <td colspan="4" class="text-muted small">
                                    ${p.prompt_data.message || ''}
                                    ${p.timed_out ? ` (${p.timeout_seconds}s timeout)` : ''}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } else {
        promptHistoryHtml = `
            <p class="text-muted mt-4">
                <em>No prompt history available (job created before this feature or no prompts required)</em>
            </p>
        `;
    }
    
    // Insert into modal
    $('#job-details-body').html(`
        <!-- Existing sections -->
        ${promptHistoryHtml}
    `);
}
```

---

### 3. Add "Replay Job" Feature

**Button in job details modal:**

```html
<button class="btn btn-secondary" onclick="replayJob('{{ job_id }}')">
    <i class="bi bi-arrow-repeat"></i> Replay with Same Prompts
</button>
```

**JavaScript handler:**

```javascript
function replayJob(jobId) {
    const job = jobs[jobId];
    
    if (!job.prompts || job.prompts.length === 0) {
        alert("No prompt history available for this job");
        return;
    }
    
    // Reconstruct config from prompt history
    const config = {};
    
    job.prompts.forEach(prompt => {
        switch (prompt.type) {
            case 'pillar_selection':
                config.pillar_selection = prompt.response;
                break;
            case 'run_mode':
                config.run_mode = prompt.response;
                break;
            // ... handle other prompt types
        }
    });
    
    // Start new job with reconstructed config
    startJob(config);
}
```

---

### 4. Export Prompt History in ZIP

**File:** `webdashboard/app.py`

Update `/api/jobs/<job_id>/download` endpoint:

```python
@app.route('/api/jobs/<job_id>/download')
def download_job_results(job_id):
    """Download job results as ZIP including prompt history"""
    # ... existing ZIP creation code
    
    # NEW: Add prompt_history.json to ZIP
    job_file = f"workspace/jobs/{job_id}/job_data.json"
    with open(job_file, 'r') as f:
        job_data = json.load(f)
    
    if 'prompts' in job_data and job_data['prompts']:
        prompt_history_json = json.dumps(job_data['prompts'], indent=2)
        zipf.writestr('prompt_history.json', prompt_history_json)
        
        # Also create human-readable summary
        summary = "Prompt History Summary\n" + "="*50 + "\n\n"
        for p in job_data['prompts']:
            summary += f"[{p['timestamp']}] {p['type']}\n"
            summary += f"  Response: {p['response']}\n"
            summary += f"  Status: {'TIMED OUT' if p['timed_out'] else 'OK'}\n\n"
        
        zipf.writestr('prompt_history.txt', summary)
    
    # ... rest of ZIP creation
```

---

## Testing Plan

### Unit Tests

**File:** `tests/integration/test_prompt_history.py`

```python
@pytest.mark.asyncio
async def test_prompt_saved_to_job_metadata():
    """Test prompt response is saved to job file"""
    handler = PromptHandler()
    
    # Request prompt
    prompt_id = await handler.request_user_input(
        job_id="test_job",
        prompt_type="pillar_selection",
        prompt_data={"message": "Select pillars"},
        timeout_seconds=300
    )
    
    # Submit response
    await handler.submit_response(prompt_id, "ALL")
    
    # Verify saved to job file
    with open("workspace/jobs/test_job/job_data.json") as f:
        job_data = json.load(f)
    
    assert len(job_data['prompts']) == 1
    assert job_data['prompts'][0]['type'] == 'pillar_selection'
    assert job_data['prompts'][0]['response'] == 'ALL'
    assert job_data['prompts'][0]['timed_out'] == False

@pytest.mark.asyncio
async def test_timeout_saved_to_history():
    """Test timeout event is recorded in history"""
    handler = PromptHandler()
    
    # Request prompt with 1-second timeout
    prompt_id = await handler.request_user_input(
        job_id="test_job",
        prompt_type="continue",
        prompt_data={"message": "Continue?"},
        timeout_seconds=1
    )
    
    # Wait for timeout
    await asyncio.sleep(2)
    
    # Verify timeout recorded
    with open("workspace/jobs/test_job/job_data.json") as f:
        job_data = json.load(f)
    
    assert job_data['prompts'][0]['timed_out'] == True
    assert job_data['prompts'][0]['response'] is None
```

### Integration Tests

1. **Full workflow:** Start job → respond to prompts → check job file
2. **Replay job:** Load completed job → replay → verify same config
3. **Export ZIP:** Download job → verify prompt_history.json exists
4. **UI display:** Open job details → verify prompt history table renders

### Manual Testing

1. Run job with multiple prompts (pillar_selection, run_mode, continue)
2. Open job details modal → verify "User Decisions" section displays
3. Download job ZIP → verify prompt_history.json and .txt files
4. Click "Replay Job" → verify new job starts with same config
5. Test legacy job (without prompts) → verify graceful fallback

---

## Backward Compatibility

### Jobs Without Prompts Field

```python
# In UI rendering
const prompts = job.prompts || [];
if (prompts.length === 0) {
    // Show "No history" message instead of error
}

# In export
if 'prompts' not in job_data:
    # Skip adding prompt_history files to ZIP
    pass
```

### Schema Migration

No migration needed - `prompts` field is optional. Old jobs will continue working without it.

---

## Future Enhancements (Out of Scope)

### Prompt Search/Filter
```javascript
// Filter prompts by type
$('#filter-prompts').on('change', function() {
    const filterType = $(this).val();
    // Show only prompts of selected type
});
```

### Prompt Analytics
- Average response time per prompt type
- Most common responses
- Timeout rate by prompt type

### Diff View for Replayed Jobs
- Compare original job config vs replayed config
- Highlight what changed

---

## Estimated Breakdown

- **PromptHandler updates:** 1 hour
  - Save to job file: 30 min
  - Timeout handling: 30 min
- **UI updates:** 1 hour
  - Job details table: 30 min
  - Replay button: 30 min
- **Export functionality:** 30 minutes
- **Testing:** 30 minutes
- **Total:** 3 hours

---

## Dependencies

**Requires:**
- ✅ `prompt_handler.py` (done in PR #46)
- ✅ Job metadata infrastructure (done in Phase 3)
- 🔄 ENHANCE-P5-2 (run_mode/continue prompts) - more prompts to record

**Synergy:**
- Works with any prompt type (pillar_selection, run_mode, continue, etc.)
- Enables reproducibility for research workflows
- Provides data for future analytics

---

## Success Metrics

- [ ] 100% of prompts saved to job metadata
- [ ] UI displays prompt history for all jobs with prompts
- [ ] "Replay Job" successfully recreates config
- [ ] ZIP export includes prompt history files
- [ ] Zero data loss or corruption in job files
- [ ] Backward compatible with old jobs
