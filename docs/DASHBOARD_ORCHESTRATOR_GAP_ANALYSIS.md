# Dashboard-Orchestrator Integration Gap Analysis

**Date**: November 16, 2025  
**Status**: 🔴 Critical Gap Identified  
**Priority**: High - Dashboard does not run the actual pipeline

## Executive Summary

The current web dashboard (`webdashboard/app.py`) and the terminal-based orchestrator (`literature_review/orchestrator.py`) are **completely disconnected**. The dashboard implements a job queue system for single PDF uploads, but **does not execute the actual literature review pipeline**. This is a critical gap that prevents the dashboard from fulfilling its intended purpose.

## Current State Analysis

### Terminal-Based Orchestrator (`orchestrator.py`)

**What it does:**
1. **Input**: Processes a **directory** of research papers (CSV database: `neuromorphic-research_database.csv`)
2. **Pipeline Execution**:
   - Loads pillar definitions from `pillar_definitions_enhanced.json`
   - Runs Judge to validate claims
   - Executes Deep Reviewer for gap analysis
   - Performs iterative convergence loops
   - Generates comprehensive outputs (15 files)
3. **User Interaction**: 
   - Interactive prompts for analysis target selection
   - Asks user to select pillars (1-7) or modes (ALL, DEEP, NONE)
   - Processes entire research corpus together
4. **Output**: 15 production files including:
   - Waterfall plots for each pillar
   - Gap analysis reports (JSON, Markdown)
   - Research trends visualizations
   - Network analysis
   - Executive summaries

**Entry Point:**
```python
def main():
    # Interactive terminal-based workflow
    # 1. Load definitions
    # 2. Check for new data or prompt user
    # 3. Run Judge on claims
    # 4. Iterative analysis loop with Deep Reviewer
    # 5. Generate comprehensive reports
```

### Web Dashboard (`webdashboard/app.py`)

**What it does:**
1. **Input**: Single PDF file upload
2. **Job Queue**: Creates job metadata with status tracking
3. **No Pipeline Execution**: Jobs remain in "queued" status forever
4. **No Results**: Cannot generate or display any analysis results

**Critical Missing Components:**
- ❌ No connection to `orchestrator.main()`
- ❌ No pipeline execution worker/runner
- ❌ No directory-based processing (only single files)
- ❌ No user interaction handling (pillar selection)
- ❌ No results visualization
- ❌ No progress monitoring during execution
- ❌ No checkpoint/state management integration

## Gap Analysis: User Intent vs Current Implementation

### User's Intent (As Stated)

> "I was under the impression that our intent was to build the following into the dashboard:
> 1. A 1:1 process map, in other words dashboard should have the functionality to run the end to end pipeline and respond/insert feedback where necessary to keep the process moving e.g. when no data, user selects what to do.
> 2. Once a process is initiated, then the user can monitor that process (either similar to terminal output, or more visually informative)
> 3. Once a output has been provided, the user could visualize the output in the dashboard"

### Current Implementation Reality

| Feature | User Intent | Current Dashboard | Gap |
|---------|-------------|-------------------|-----|
| **Input** | Directory of papers | Single PDF upload | 🔴 CRITICAL |
| **Pipeline Execution** | Run full orchestrator pipeline | None - jobs stay queued | 🔴 CRITICAL |
| **User Interaction** | Handle prompts (pillar selection) | None | 🔴 CRITICAL |
| **Progress Monitoring** | Real-time output like terminal | None | 🔴 CRITICAL |
| **Results Display** | Visualize 15 output files | None | 🔴 CRITICAL |
| **Process Map** | 1:1 with terminal flow | Completely different | 🔴 CRITICAL |

## Detailed Component Comparison

### 1. Input Processing

**Terminal Orchestrator:**
```python
# Expects CSV database with all papers
RESEARCH_DB_FILE = 'neuromorphic-research_database.csv'
database_df_obj = ResearchDatabase(RESEARCH_DB_FILE)
all_db_records = load_research_db_records(RESEARCH_DB_FILE)
```

**Dashboard:**
```python
# Only handles single PDF upload
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    # Saves to: workspace/uploads/{job_id}.pdf
    # Creates job metadata but NO PROCESSING
```

**Gap:** Dashboard needs to either:
- Option A: Accept directory uploads/multiple files
- Option B: Build a research database from uploaded files
- Option C: Allow users to select from existing database

### 2. Pipeline Execution

**Terminal Orchestrator:**
```python
# Complete multi-stage pipeline
1. Load definitions and state
2. Determine run mode (new data vs user selection)
3. Run Judge to validate claims
4. Iterative analysis loop:
   - Deep Reviewer generates new claims
   - Judge validates claims
   - Gap Analyzer computes completeness
   - Check convergence (±5% threshold)
   - Repeat until convergence or user exits
5. Generate all reports and visualizations
```

**Dashboard:**
```python
# No pipeline execution at all
# Jobs are created but never processed
job_data = {
    "status": "queued",  # Stays queued forever
    # No worker to pick up and execute
}
```

**Gap:** Dashboard needs:
- Background worker to process queued jobs
- Integration with `orchestrator.main()`
- Async execution with progress tracking
- Error handling and retry logic

### 3. User Interaction

**Terminal Orchestrator:**
```python
def get_user_analysis_target(pillar_definitions):
    """Interactive prompt for analysis target selection"""
    safe_print("What would you like to re-assess?")
    for i, name in enumerate(analyzable_pillars, 1):
        safe_print(f"  {i}. {name.split(':')[0]}")
    safe_print(f"  ALL - Run analysis on all pillars")
    safe_print(f"  DEEP - Run iterative deep-review loop")
    
    choice = input(f"Enter choice (1-{len(analyzable_pillars)}, ALL, DEEP, NONE): ")
    # Returns: (pillar_list, run_mode)
```

**Dashboard:**
```python
# No user interaction mechanism
# No way to select pillars or run modes
# No prompts or decision points
```

**Gap:** Dashboard needs:
- UI for pillar selection (checkboxes/dropdown)
- Run mode selection (Single Pass vs Deep Loop)
- Interactive prompt handling via WebSocket
- State persistence for multi-step workflows

### 4. Progress Monitoring

**Terminal Orchestrator:**
```python
# Real-time streaming output
safe_print(f"--- Analyzing: {pillar_name} ---")
safe_print(f"Completeness: {completeness:.1f}%")
safe_print(f"Score Changes: +{diff['delta']:.1f}%")
logger.info(f"Iteration {iteration_count} complete")

# Subprocess output streaming
for line in iter(process.stdout.readline, ''):
    safe_print(f"  [{script_name}] {line}")
```

**Dashboard:**
```python
# No progress tracking
# WebSocket exists but not used for pipeline progress
# Logs endpoint exists but no logs are written
```

**Gap:** Dashboard needs:
- Real-time log streaming to WebSocket clients
- Progress percentage updates
- Stage/phase tracking (Judge, Deep Review, Gap Analysis)
- Iteration counter for convergence loops
- ETA estimation

### 5. Results Visualization

**Terminal Orchestrator Outputs:**
```
gap_analysis_output/
├── waterfall_Pillar_1.html          # 7 pillar waterfalls
├── waterfall_Pillar_2.html
├── ...
├── _OVERALL_Research_Gap_Radar.html # Radar chart
├── _Paper_Network.html              # Network graph
├── _Research_Trends.html            # Trend analysis
├── gap_analysis_report.json         # Machine-readable
├── executive_summary.md             # Human-readable
├── suggested_searches.json          # Research recommendations
├── suggested_searches.md
└── sub_requirement_paper_contributions.md
```

**Dashboard:**
```python
# No visualization endpoints
# No way to display HTML outputs
# No results retrieval
```

**Gap:** Dashboard needs:
- Results browser/gallery
- Embedded visualization viewer
- Download links for all outputs
- Summary cards with key metrics
- Comparison views (before/after)

## Architecture Mismatch

### Current Architecture

```
Terminal Flow:
[User Terminal] → [orchestrator.py main()] → [15 Output Files]
                         ↓
                  [Interactive Prompts]
                         ↓
                  [Judge + Deep Reviewer]
                         ↓
                  [Iterative Convergence Loop]

Dashboard Flow:
[Browser Upload] → [FastAPI] → [Job Queue] → ❌ NOTHING
                                      ↓
                                [Jobs stuck in "queued"]
```

### Required Architecture

```
Browser → Dashboard UI → FastAPI Backend → Job Queue
                              ↓
                        Background Worker
                              ↓
                    orchestrator.main() wrapper
                              ↓
            ┌─────────────────┴─────────────────┐
            ↓                 ↓                  ↓
         Judge          Deep Reviewer      Gap Analyzer
            ↓                 ↓                  ↓
        [Iterative Convergence Loop with State Management]
            ↓
    [15 Output Files + Progress Updates]
            ↓
    [Dashboard Visualization Layer]
            ↓
    [User Views Results in Browser]
```

## Required Implementation Components

### 1. Job Runner/Worker

**File**: `webdashboard/job_runner.py` (NEW)

```python
class PipelineJobRunner:
    """Background worker to execute queued pipeline jobs"""
    
    def __init__(self):
        self.queue = asyncio.Queue()
        self.running_jobs = {}
    
    async def process_job(self, job_id, job_data):
        """Execute full orchestrator pipeline for a job"""
        try:
            # 1. Prepare workspace
            # 2. Run orchestrator.main() with job parameters
            # 3. Stream progress via WebSocket
            # 4. Save results
            # 5. Update job status
        except Exception as e:
            # Handle errors, update job status to 'failed'
```

### 2. Orchestrator Integration Wrapper

**File**: `literature_review/orchestrator_integration.py` (EXISTS - needs expansion)

```python
def run_pipeline_async(
    job_id: str,
    input_files: List[Path],
    pillar_selections: List[str],
    run_mode: str,
    progress_callback: Callable,
    log_callback: Callable
):
    """
    Async wrapper around orchestrator.main() for dashboard integration
    
    Args:
        job_id: Unique job identifier
        input_files: Research papers to analyze
        pillar_selections: User-selected pillars or "ALL"
        run_mode: "ONCE", "DEEP_LOOP", or "EXIT"
        progress_callback: Function to call with progress updates
        log_callback: Function to call with log messages
    
    Returns:
        Dict with results paths and metadata
    """
```

### 3. Enhanced API Endpoints

**File**: `webdashboard/app.py` (MODIFY)

```python
# NEW: Multi-file upload endpoint
@app.post("/api/upload/batch")
async def upload_batch(files: List[UploadFile]):
    """Upload multiple PDFs for a single analysis job"""

# NEW: Job configuration endpoint
@app.post("/api/jobs/configure")
async def configure_job(job_id: str, config: JobConfig):
    """
    Configure job parameters:
    - pillar_selections: List[str]
    - run_mode: "ONCE" | "DEEP_LOOP"
    - convergence_threshold: float
    """

# NEW: Start job execution
@app.post("/api/jobs/{job_id}/start")
async def start_job(job_id: str):
    """Begin pipeline execution for configured job"""

# NEW: Get job results
@app.get("/api/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    """Retrieve all output files and metadata"""

# NEW: Stream job progress
@app.websocket("/ws/jobs/{job_id}/progress")
async def job_progress_stream(websocket: WebSocket, job_id: str):
    """Real-time progress updates for specific job"""
```

### 4. Frontend UI Updates

**File**: `webdashboard/templates/index.html` (MODIFY)

```html
<!-- NEW: Batch Upload -->
<input type="file" multiple accept=".pdf" id="batchFileInput">

<!-- NEW: Pipeline Configuration -->
<div id="pipelineConfig">
  <h5>Analysis Configuration</h5>
  
  <!-- Pillar Selection -->
  <div class="pillar-selector">
    <label><input type="checkbox" value="ALL"> All Pillars</label>
    <label><input type="checkbox" value="Pillar_1"> Pillar 1: Architecture</label>
    <!-- ... -->
  </div>
  
  <!-- Run Mode -->
  <select id="runMode">
    <option value="ONCE">Single Pass Analysis</option>
    <option value="DEEP_LOOP">Deep Iterative Loop</option>
  </select>
  
  <button onclick="startPipeline()">Start Analysis</button>
</div>

<!-- NEW: Real-time Progress Display -->
<div id="progressDisplay">
  <div class="progress-stage">Judge: ✅ Complete</div>
  <div class="progress-stage">Deep Review: ⏳ Running (Iteration 2/5)</div>
  <div class="progress-stage">Gap Analysis: ⏸ Pending</div>
  <div class="progress-bar">
    <div style="width: 45%">45%</div>
  </div>
</div>

<!-- NEW: Results Viewer -->
<div id="resultsViewer">
  <div class="result-card" data-type="waterfall">
    <iframe src="/api/jobs/{job_id}/output/waterfall_Pillar_1.html"></iframe>
  </div>
  <!-- ... -->
</div>
```

## Implementation Priority

### Phase 1: Core Pipeline Integration (CRITICAL - Week 1)
1. ✅ Create `PipelineJobRunner` class
2. ✅ Implement `orchestrator_integration.run_pipeline_async()`
3. ✅ Add job execution to background worker
4. ✅ Basic progress tracking and logging

**Outcome:** Dashboard can actually run the pipeline (even if UI is basic)

### Phase 2: Input Handling (HIGH - Week 1-2)
1. ✅ Multi-file upload endpoint
2. ✅ Research database builder from uploaded PDFs
3. ✅ Job configuration UI (pillar selection, run mode)
4. ✅ Parameter validation

**Outcome:** Dashboard accepts proper input format

### Phase 3: Progress Monitoring (HIGH - Week 2)
1. ✅ WebSocket progress streaming
2. ✅ Real-time log display
3. ✅ Stage tracking (Judge → Deep Review → Analysis)
4. ✅ Iteration counter for convergence loops

**Outcome:** Users can monitor running jobs

### Phase 4: Results Visualization (MEDIUM - Week 2-3)
1. ✅ Results retrieval endpoints
2. ✅ Embedded HTML visualization viewer
3. ✅ Results gallery/browser
4. ✅ Download all outputs as ZIP

**Outcome:** Users can view and download results

### Phase 5: Interactive Prompts (MEDIUM - Week 3)
1. ✅ WebSocket-based prompt handler
2. ✅ Modal dialogs for user decisions
3. ✅ State persistence for multi-step workflows

**Outcome:** Full 1:1 parity with terminal experience

## Technical Challenges

### Challenge 1: Blocking vs Async
**Problem:** `orchestrator.main()` is synchronous and blocking  
**Solution:** Run in thread pool executor or separate process

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def run_orchestrator_async(job_id, params):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        orchestrator.main,  # Blocking function
        params
    )
    return result
```

### Challenge 2: Interactive Prompts in Web Context
**Problem:** Terminal `input()` doesn't work in background worker  
**Solution:** Replace with callback-based decision making

```python
# Terminal version:
choice = input("Enter choice (1-7, ALL, DEEP, NONE): ")

# Dashboard version:
choice = await wait_for_user_input_via_websocket(
    job_id=job_id,
    prompt="Select analysis target",
    options=["1", "2", "3", "ALL", "DEEP", "NONE"]
)
```

### Challenge 3: Real-time Output Streaming
**Problem:** `safe_print()` and `logger.info()` go to terminal/file  
**Solution:** Add callback hooks for dashboard integration

```python
# In orchestrator.py:
def safe_print(message, callback=None):
    print(message)
    if callback:
        callback(message)  # Send to dashboard

# In dashboard:
def progress_callback(message):
    asyncio.create_task(
        websocket_manager.broadcast({
            "type": "log",
            "job_id": current_job_id,
            "message": message
        })
    )
```

### Challenge 4: State Management
**Problem:** Dashboard jobs can be interrupted/resumed  
**Solution:** Leverage existing checkpoint system

```python
# orchestrator.py already has:
save_orchestrator_state(
    ORCHESTRATOR_STATE_FILE,
    all_results,
    score_history,
    stage=f"gap_analysis_iteration_{iteration_count}"
)

# Dashboard needs to:
# 1. Store state per job_id
# 2. Allow resume from checkpoint
# 3. Clean up on completion
```

## Recommendation

**Immediate Action Required:**
1. Stop referring to current dashboard as "production-ready"
2. Acknowledge this is a prototype UI only
3. Implement Phase 1 (Core Pipeline Integration) ASAP
4. User should not perform manual smoke testing until pipeline is integrated

**Alternative Approach:**
If full integration is complex, consider:
- Dashboard as **viewer only** for terminal-generated outputs
- Separate "job creation" CLI tool that dashboard monitors
- Hybrid: Terminal for execution, dashboard for visualization

## Questions for User

1. **Priority**: Should we pause other work to fix this critical gap?
2. **Scope**: Do you want full 1:1 parity or a simplified dashboard workflow?
3. **Timeline**: What's the deadline for functional dashboard?
4. **Resources**: Can we focus solely on integration for next sprint?

## Next Steps

Based on user's decision:
- [ ] Get approval for implementation approach
- [ ] Create detailed task cards for Phase 1
- [ ] Begin core pipeline integration
- [ ] Update DASHBOARD_SMOKE_TEST.md to reflect integration requirements
- [ ] Document new architecture in ORCHESTRATOR_V2_GUIDE.md

---

**Bottom Line:** The current dashboard is a shell without the engine. It needs urgent integration work to become functional.
