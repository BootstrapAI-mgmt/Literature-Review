# Integration Sync Point #1: Week 3 Integration

**Priority**: 🔴 CRITICAL  
**Timeline**: Week 3 (Wednesday)  
**Dependencies**: Phase 1-3 Complete, Wave 1-2.1 Complete  
**Effort**: 5 hours  
**Who**: Both developers

---

## Objective

Integrate dashboard and enhancement branches at the midpoint to ensure dashboard can display enhanced analytical outputs (Proof Scorecard, Cost Summary, Sufficiency Matrix).

## Context

By Week 3:
- **Dashboard has**: Phases 1-3 complete (pipeline execution, input handling, progress monitoring)
- **Enhancements have**: Wave 1 complete + Wave 2.1 in progress (Proof Scorecard, Cost Tracker, Sufficiency Matrix)

This sync ensures the dashboard's results viewer (Phase 4, starting this week) can display the new enhanced outputs.

---

## Pre-Integration Checklist

### Dashboard Developer
- [ ] Phase 1: Core Pipeline Integration ✅
- [ ] Phase 2: Input Handling ✅
- [ ] Phase 3: Progress Monitoring ✅
- [ ] All Phase 1-3 tests passing
- [ ] Feature branch `feature/dashboard-integration` up to date

### Enhancement Developer
- [ ] Wave 1.1: Manual Deep Review ✅
- [ ] Wave 1.2: Proof Scorecard ✅
- [ ] Wave 1.3: Cost Tracker ✅
- [ ] Wave 1.4: Incremental Mode ✅
- [ ] Wave 2.1: Sufficiency Matrix ✅ (or in progress)
- [ ] All Wave 1 tests passing
- [ ] Feature branch `feature/enhancement-waves` up to date

---

## Integration Tasks

### Task 1: Create Integration Branch (0.5 hours)

**Who**: Either developer

**Steps**:
```bash
# Ensure both feature branches are pushed
git checkout feature/dashboard-integration
git push origin feature/dashboard-integration

git checkout feature/enhancement-waves
git push origin feature/enhancement-waves

# Create integration branch from main
git checkout main
git pull origin main
git checkout -b integration/week3-sync

# Document current state
git log --oneline --graph --all --decorate | head -20
```

**Deliverable**: Clean integration branch ready for merging

---

### Task 2: Merge Dashboard Branch (0.5 hours)

**Who**: Dashboard developer (primary), Enhancement developer (review)

**Steps**:
```bash
# Merge dashboard changes
git merge feature/dashboard-integration

# Expected changes:
# - webdashboard/job_runner.py (NEW)
# - webdashboard/app.py (MODIFIED - many changes)
# - webdashboard/templates/index.html (MODIFIED)
# - webdashboard/database_builder.py (NEW)
# - literature_review/orchestrator.py (MODIFIED - config param, ProgressTracker)
# - literature_review/orchestrator_integration.py (ENHANCED)
# - tests/integration/test_dashboard_*.py (NEW - 3 files)

# Run tests
pytest tests/integration/test_dashboard_pipeline.py
pytest tests/integration/test_dashboard_input_pipeline.py
pytest tests/integration/test_progress_monitoring.py
```

**Expected Conflicts**: None (first merge)

**Deliverable**: Dashboard code integrated

---

### Task 3: Merge Enhancement Branch (0.5 hours)

**Who**: Enhancement developer (primary), Dashboard developer (review)

**Steps**:
```bash
# Merge enhancement changes
git merge feature/enhancement-waves

# Expected changes:
# - literature_review/analysis/proof_scorecard.py (NEW)
# - literature_review/analysis/proof_scorecard_viz.py (NEW)
# - literature_review/analysis/sufficiency_matrix.py (NEW)
# - literature_review/visualization/sufficiency_matrix_viz.py (NEW)
# - literature_review/utils/cost_tracker.py (NEW)
# - literature_review/utils/incremental_analyzer.py (NEW)
# - api_manager.py (MODIFIED - cost logging)
# - pipeline_orchestrator.py (MODIFIED - enhanced workflow)
# - docs/USER_MANUAL.md (UPDATED)
# - scripts/generate_deep_review_directions.py (NEW)

# Run tests
pytest tests/unit/test_proof_scorecard.py
pytest tests/unit/test_cost_tracker.py
pytest tests/integration/test_incremental_mode.py
```

**Expected Conflicts**: Possibly `api_manager.py` if both modified  
**Resolution**: Keep both changes (cost logging + any dashboard hooks)

**Deliverable**: Enhancement code integrated

---

### Task 4: Resolve Conflicts (0.5 hours)

**Who**: Both developers together

**Potential Conflict #1**: `literature_review/orchestrator.py`

**Dashboard Changes**:
```python
def main(config: Optional[OrchestratorConfig] = None):
    """Run orchestrator with optional config."""
    
    # Initialize progress tracker if callback provided
    progress_tracker = None
    if config and config.progress_callback:
        progress_tracker = ProgressTracker(config.progress_callback)
    
    # ... rest of function
```

**Enhancement Changes**:
```python
# None in Week 3 - enhancements don't modify orchestrator.py yet
```

**Resolution**: ✅ No conflict expected

---

**Potential Conflict #2**: `api_manager.py`

**Dashboard Changes**: None

**Enhancement Changes**:
```python
# Add cost tracking
from literature_review.utils.cost_tracker import CostTracker

class APIManager:
    def __init__(self):
        self.cost_tracker = CostTracker()
    
    def make_api_call(self, ...):
        response = # ... API call
        
        # Log cost
        self.cost_tracker.log_api_call(
            module=module_name,
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens
        )
```

**Resolution**: ✅ No conflict expected (dashboard doesn't modify api_manager.py)

---

### Task 5: Extend Phase 4 for Enhanced Outputs (2 hours)

**Who**: Dashboard developer (primary)

**File**: `webdashboard/app.py`

**Objective**: Add special API endpoints for enhanced outputs

**Implementation**:

```python
# Add Proof Scorecard endpoint
@app.get("/api/jobs/{job_id}/proof-scorecard")
async def get_proof_scorecard(job_id: str):
    """Get proof scorecard summary for a job."""
    scorecard_file = f"workspace/jobs/{job_id}/outputs/proof_scorecard_output/proof_scorecard.json"
    
    if not os.path.exists(scorecard_file):
        raise HTTPException(status_code=404, detail="Proof scorecard not found")
    
    with open(scorecard_file, 'r') as f:
        scorecard = json.load(f)
    
    return {
        "overall_score": scorecard['overall_proof_status']['proof_readiness_score'],
        "verdict": scorecard['overall_proof_status']['verdict'],
        "headline": scorecard['overall_proof_status']['headline'],
        "publication_viability": scorecard['publication_viability'],
        "research_goals": scorecard['research_goals'][:3],  # Top 3
        "next_steps": scorecard['critical_next_steps'][:5]  # Top 5
    }

# Add Cost Summary endpoint
@app.get("/api/jobs/{job_id}/cost-summary")
async def get_cost_summary(job_id: str):
    """Get API cost summary for a job."""
    cost_file = f"workspace/jobs/{job_id}/outputs/cost_reports/api_usage_report.json"
    
    if not os.path.exists(cost_file):
        return {"total_cost": 0, "message": "No cost data available"}
    
    with open(cost_file, 'r') as f:
        cost_data = json.load(f)
    
    return {
        "total_cost": cost_data.get("total_cost_usd", 0),
        "budget_percent": cost_data.get("budget_percent_used", 0),
        "per_paper_cost": cost_data.get("cost_per_paper", 0),
        "module_breakdown": cost_data.get("module_breakdown", {}),
        "cache_savings": cost_data.get("cache_savings_usd", 0)
    }

# Add Sufficiency Matrix summary
@app.get("/api/jobs/{job_id}/sufficiency-summary")
async def get_sufficiency_summary(job_id: str):
    """Get evidence sufficiency summary."""
    sufficiency_file = f"workspace/jobs/{job_id}/outputs/gap_analysis_output/sufficiency_matrix.json"
    
    if not os.path.exists(sufficiency_file):
        return {"quadrants": {}, "message": "No sufficiency data available"}
    
    with open(sufficiency_file, 'r') as f:
        data = json.load(f)
    
    # Summarize by quadrant
    quadrant_summary = {}
    for req in data.get("requirements", []):
        quadrant = req["quadrant"]
        if quadrant not in quadrant_summary:
            quadrant_summary[quadrant] = 0
        quadrant_summary[quadrant] += 1
    
    return {
        "quadrants": quadrant_summary,
        "total_requirements": len(data.get("requirements", [])),
        "recommendations": data.get("recommendations", [])[:5]
    }
```

**HTML Template Updates** (`webdashboard/templates/index.html`):

```html
<!-- Add enhanced output cards to job details section -->
<div class="enhanced-outputs" v-if="job.status === 'completed'">
    <h3>📊 Enhanced Analysis</h3>
    
    <!-- Proof Scorecard Card -->
    <div class="card proof-scorecard-card" v-if="job.proof_scorecard">
        <div class="card-header">
            <h4>🎯 Proof Completeness Scorecard</h4>
        </div>
        <div class="card-body">
            <div class="score-display" :class="getScoreClass(job.proof_scorecard.overall_score)">
                {{ job.proof_scorecard.overall_score }}%
            </div>
            <div class="verdict">{{ job.proof_scorecard.verdict }}</div>
            <p class="headline">{{ job.proof_scorecard.headline }}</p>
            <a :href="`/api/jobs/${job.id}/files/proof_scorecard_output/proof_scorecard.html`" 
               target="_blank" class="btn btn-primary">
                View Full Report
            </a>
        </div>
    </div>
    
    <!-- Cost Summary Card -->
    <div class="card cost-summary-card" v-if="job.cost_summary">
        <div class="card-header">
            <h4>💰 API Cost Summary</h4>
        </div>
        <div class="card-body">
            <div class="cost-metrics">
                <div class="metric">
                    <span class="label">Total Cost:</span>
                    <span class="value">${{ job.cost_summary.total_cost.toFixed(2) }}</span>
                </div>
                <div class="metric">
                    <span class="label">Per Paper:</span>
                    <span class="value">${{ job.cost_summary.per_paper_cost.toFixed(2) }}</span>
                </div>
                <div class="metric">
                    <span class="label">Budget Used:</span>
                    <span class="value budget-bar">
                        <div class="progress">
                            <div class="progress-bar" 
                                 :style="{width: job.cost_summary.budget_percent + '%'}"
                                 :class="getBudgetClass(job.cost_summary.budget_percent)">
                                {{ job.cost_summary.budget_percent }}%
                            </div>
                        </div>
                    </span>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Sufficiency Matrix Card -->
    <div class="card sufficiency-card" v-if="job.sufficiency_summary">
        <div class="card-header">
            <h4>📈 Evidence Sufficiency Matrix</h4>
        </div>
        <div class="card-body">
            <div class="quadrant-summary">
                <div class="quadrant q1" v-if="job.sufficiency_summary.quadrants.Q1">
                    <strong>Strong Foundation</strong><br>
                    {{ job.sufficiency_summary.quadrants.Q1 }} requirements
                </div>
                <div class="quadrant q2" v-if="job.sufficiency_summary.quadrants.Q2">
                    <strong>Promising Seeds</strong><br>
                    {{ job.sufficiency_summary.quadrants.Q2 }} requirements
                </div>
                <div class="quadrant q3" v-if="job.sufficiency_summary.quadrants.Q3">
                    <strong>Hollow Coverage</strong><br>
                    {{ job.sufficiency_summary.quadrants.Q3 }} requirements
                </div>
                <div class="quadrant q4" v-if="job.sufficiency_summary.quadrants.Q4">
                    <strong>Critical Gaps</strong><br>
                    {{ job.sufficiency_summary.quadrants.Q4 }} requirements
                </div>
            </div>
            <a :href="`/api/jobs/${job.id}/files/gap_analysis_output/sufficiency_matrix.html`" 
               target="_blank" class="btn btn-primary">
                View Interactive Matrix
            </a>
        </div>
    </div>
</div>

<script>
// Add methods to fetch enhanced data
async fetchEnhancedOutputs(jobId) {
    try {
        const proofScorecard = await fetch(`/api/jobs/${jobId}/proof-scorecard`);
        if (proofScorecard.ok) {
            this.selectedJob.proof_scorecard = await proofScorecard.json();
        }
    } catch (e) {
        console.log("No proof scorecard available");
    }
    
    try {
        const costSummary = await fetch(`/api/jobs/${jobId}/cost-summary`);
        if (costSummary.ok) {
            this.selectedJob.cost_summary = await costSummary.json();
        }
    } catch (e) {
        console.log("No cost summary available");
    }
    
    try {
        const sufficiency = await fetch(`/api/jobs/${jobId}/sufficiency-summary`);
        if (sufficiency.ok) {
            this.selectedJob.sufficiency_summary = await sufficiency.json();
        }
    } catch (e) {
        console.log("No sufficiency data available");
    }
}

// Helper methods
getScoreClass(score) {
    if (score >= 60) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
}

getBudgetClass(percent) {
    if (percent > 80) return 'bg-danger';
    if (percent > 50) return 'bg-warning';
    return 'bg-success';
}
</script>
```

**Deliverable**: Dashboard displays Proof Scorecard, Cost Summary, and Sufficiency Matrix cards

---

### Task 6: Update ProgressTracker Stage Weights (1 hour)

**Who**: Dashboard developer

**File**: `literature_review/orchestrator.py`

**Objective**: Add new enhancement stages to progress tracking

**Current Stage Weights** (Phase 3):
```python
STAGE_WEIGHTS = {
    "initialization": 5,
    "judge": 15,
    "deep_review": 30,
    "gap_analysis": 35,
    "visualization": 10,
    "finalization": 5
}
```

**Updated Stage Weights** (with enhancements):
```python
STAGE_WEIGHTS = {
    # Existing stages
    "initialization": 5,
    "judge": 12,
    "deep_review": 25,
    "gap_analysis": 20,
    
    # New enhancement stages (Wave 1-2)
    "proof_scorecard": 5,
    "sufficiency_analysis": 8,
    "proof_chain_analysis": 8,
    "triangulation_analysis": 7,
    
    # Existing stages
    "visualization": 7,
    "finalization": 3
}
```

**Add Progress Hooks** in `pipeline_orchestrator.py`:

```python
# In enhanced orchestrator
if progress_tracker:
    progress_tracker.emit("proof_scorecard", "starting", "Generating proof scorecard...")

generate_scorecard(...)

if progress_tracker:
    progress_tracker.emit("proof_scorecard", "complete", "Proof scorecard complete")
```

**Deliverable**: Progress bar accurately reflects enhanced pipeline stages

---

### Task 7: Integration Testing (0.5 hours)

**Who**: Both developers

**Test Scenarios**:

1. **Basic Pipeline with Enhanced Outputs**
   ```bash
   # Start dashboard
   cd webdashboard
   python app.py
   
   # Upload papers via UI
   # Run pipeline
   # Verify:
   # - Proof Scorecard card appears
   # - Cost Summary shows usage
   # - Sufficiency Matrix summary displays
   ```

2. **Progress Tracking with New Stages**
   ```bash
   # Run pipeline
   # Watch WebSocket progress
   # Verify new stages appear:
   # - "proof_scorecard" (5%)
   # - "sufficiency_analysis" (8%)
   # Progress bar reaches 100%
   ```

3. **Enhanced Output Links**
   ```bash
   # Click "View Full Report" on Proof Scorecard
   # Verify HTML opens in new tab
   # Click "View Interactive Matrix"
   # Verify Plotly visualization works
   ```

**Acceptance Criteria**:
- [ ] All enhanced output cards display when data available
- [ ] Progress tracking includes new stages
- [ ] Links to full reports work
- [ ] No regression in basic dashboard functionality

---

### Task 8: Merge Back to Feature Branches (0.5 hours)

**Who**: Both developers

**Steps**:
```bash
# Merge integration branch back to dashboard branch
git checkout feature/dashboard-integration
git merge integration/week3-sync
git push origin feature/dashboard-integration

# Merge integration branch back to enhancement branch
git checkout feature/enhancement-waves
git merge integration/week3-sync
git push origin feature/enhancement-waves

# Both developers now have integrated code
```

**Deliverable**: Both feature branches include Week 3 integration

---

## Post-Integration Validation

### Checklist

**Dashboard Developer**:
- [ ] Phase 4 development can now use integrated code
- [ ] Enhanced output cards display correctly
- [ ] Progress tracking includes all stages
- [ ] No breaking changes to Phases 1-3

**Enhancement Developer**:
- [ ] Wave 2.2 development can proceed
- [ ] Dashboard successfully displays Wave 1 outputs
- [ ] No breaking changes to existing enhancements

---

## Expected Deliverables

1. ✅ Integrated branch `integration/week3-sync`
2. ✅ Dashboard displays Proof Scorecard, Cost Summary, Sufficiency Matrix
3. ✅ Progress tracking includes enhancement stages
4. ✅ All tests passing (dashboard + enhancements)
5. ✅ Both feature branches updated with integration

---

## Timeline

**Total Effort**: 5 hours  
**When**: Week 3, Wednesday afternoon  
**Duration**: Half day

**Schedule**:
```
1:00 PM - Create integration branch (0.5h)
1:30 PM - Merge dashboard branch (0.5h)
2:00 PM - Merge enhancement branch (0.5h)
2:30 PM - Resolve conflicts (0.5h)
3:00 PM - Break
3:15 PM - Extend Phase 4 for enhanced outputs (2h)
5:15 PM - Update ProgressTracker (1h)
6:15 PM - Integration testing (0.5h)
6:45 PM - Merge back to feature branches (0.5h)
7:15 PM - Done ✅
```

---

## Risk Mitigation

**Risk**: Unexpected conflicts during merge  
**Mitigation**: Both developers available for pair debugging  
**Contingency**: Revert to pre-merge state, redesign conflict resolution

**Risk**: Enhanced outputs don't display correctly  
**Mitigation**: Gradual rollout (Proof Scorecard → Cost → Sufficiency)  
**Contingency**: Display generic file links instead of special cards

**Risk**: Progress tracking breaks with new stages  
**Mitigation**: Extensive testing before merge  
**Contingency**: Fallback to basic progress (just percentage)

---

## Success Metrics

- [ ] Integration completed in ≤5 hours
- [ ] Zero critical bugs introduced
- [ ] All existing tests still passing
- [ ] Dashboard displays ≥2 enhanced output cards
- [ ] Both developers unblocked for Week 4 work

---

**Document Status**: ✅ Ready for Execution  
**Next Action**: Schedule Week 3 Wednesday integration session  
**Owner**: Both developers  
**Created**: November 16, 2025
