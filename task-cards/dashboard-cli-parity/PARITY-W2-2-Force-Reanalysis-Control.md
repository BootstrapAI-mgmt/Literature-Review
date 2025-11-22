# PARITY-W2-2: Force Re-analysis Control

**Priority:** 🟠 **HIGH**  
**Effort:** 4-6 hours  
**Wave:** 2 (High Priority Features)  
**Dependencies:** PARITY-W1-2 (Advanced Options Panel)

---

## 📋 Problem Statement

**Current State:**  
Dashboard always uses cached results when available, with no user control. This prevents re-running analysis when:
- Testing configuration changes
- Updating prompts or models
- Verifying reproducibility
- Comparing different runs on same data

**CLI Capability:**
```bash
python pipeline_orchestrator.py --force  # Ignore cache, re-run everything
```

**User Impact:**
- Cannot force fresh analysis on same papers
- Cannot verify changes to models/prompts worked
- Must manually delete cache files (error-prone)
- No way to ensure "clean slate" run

**Gap:** No user control over cache usage in Dashboard.

---

## 🎯 Objective

Add "Force Re-analysis" checkbox to Dashboard that passes `--force` flag to pipeline, giving users control over cache bypass, matching CLI behavior.

---

## 📐 Design

### UI Components

**Location:** Advanced Options Panel in `webdashboard/templates/index.html` (already designed in W1-2)

**Force Re-analysis Control:**

```html
<!-- Force Re-analysis (in Advanced Options Panel) -->
<div class="mb-3">
    <div class="form-check form-switch">
        <input class="form-check-input" type="checkbox" 
               id="forceReanalysis"
               onchange="updateForceWarning()">
        <label class="form-check-label" for="forceReanalysis">
            <strong>Force Re-analysis</strong>
            <span class="badge bg-warning text-dark">CLI: --force</span>
        </label>
        <div class="form-text">
            Re-run analysis even if recent results exist. Ignores all cached responses.
        </div>
    </div>
    
    <!-- Cost Warning (shown when force enabled) -->
    <div id="forceWarning" style="display: none;" class="alert alert-warning mt-2">
        <strong>⚠️ Cost Impact</strong>
        <p class="mb-2">
            Forcing re-analysis will make fresh API calls instead of using cached responses.
            This may significantly increase costs.
        </p>
        
        <!-- Cost Estimation -->
        <div id="costEstimate" class="mt-2">
            <small>
                <strong>Estimated Impact:</strong><br>
                Cached run: ~$<span id="cachedCost">0.50</span><br>
                Fresh run: ~$<span id="freshCost">5.00</span><br>
                <strong>Difference: +$<span id="costDiff">4.50</span></strong>
            </small>
        </div>
        
        <div class="form-check mt-2">
            <input class="form-check-input" type="checkbox" 
                   id="forceConfirm" required>
            <label class="form-check-label" for="forceConfirm">
                <small>I understand this will increase costs</small>
            </label>
        </div>
    </div>
    
    <!-- Use Cases Help -->
    <div class="collapse mt-2" id="forceUseCases">
        <div class="card card-body bg-light">
            <h6>When to Use Force Re-analysis:</h6>
            <ul class="mb-0 small">
                <li>Testing new models or prompts</li>
                <li>Verifying configuration changes</li>
                <li>Ensuring reproducibility (fresh run)</li>
                <li>Cache corruption suspected</li>
                <li>Model API behavior changed</li>
            </ul>
        </div>
    </div>
    
    <button type="button" class="btn btn-sm btn-link p-0 mt-1"
            data-bs-toggle="collapse" data-bs-target="#forceUseCases">
        ℹ️ When should I use this?
    </button>
</div>

<script>
// Update force warning visibility and cost estimate
function updateForceWarning() {
    const forceEnabled = document.getElementById('forceReanalysis').checked;
    const warning = document.getElementById('forceWarning');
    
    if (forceEnabled) {
        warning.style.display = 'block';
        estimateForceCost();
    } else {
        warning.style.display = 'none';
        document.getElementById('forceConfirm').checked = false;
    }
}

// Estimate cost impact of forcing re-analysis
async function estimateForceCost() {
    try {
        // Get uploaded file count or base job info
        const fileCount = getUploadedFileCount();
        
        const response = await fetch('/api/cost/estimate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            },
            body: JSON.stringify({
                paper_count: fileCount,
                use_cache: false  // Force fresh
            })
        });
        
        const estimate = await response.json();
        
        // Update display
        document.getElementById('cachedCost').textContent = 
            estimate.cached_cost.toFixed(2);
        document.getElementById('freshCost').textContent = 
            estimate.fresh_cost.toFixed(2);
        document.getElementById('costDiff').textContent = 
            (estimate.fresh_cost - estimate.cached_cost).toFixed(2);
            
    } catch (error) {
        console.error('Cost estimation failed:', error);
        // Show generic warning
        document.getElementById('costEstimate').style.display = 'none';
    }
}

// Validate force confirmation before submission
function validateForceOptions() {
    const forceEnabled = document.getElementById('forceReanalysis').checked;
    const confirmed = document.getElementById('forceConfirm').checked;
    
    if (forceEnabled && !confirmed) {
        alert('Please confirm you understand the cost impact of forcing re-analysis.');
        return false;
    }
    
    return true;
}

// Include in job submission
function getAdvancedOptions() {
    return {
        // ... other options ...
        force: document.getElementById('forceReanalysis').checked,
        force_confirmed: document.getElementById('forceConfirm').checked
    };
}
</script>
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**Cost Estimation Endpoint:**

```python
from typing import Optional

class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""
    paper_count: int = Field(..., ge=1, le=1000)
    use_cache: bool = True
    model: Optional[str] = "gemini-1.5-pro"


@app.post(
    "/api/cost/estimate",
    tags=["Cost Management"],
    summary="Estimate analysis cost with/without cache"
)
async def estimate_cost(
    request: CostEstimateRequest,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Estimate cost for analysis with and without cache.
    
    Used by force re-analysis warning to show cost impact.
    """
    verify_api_key(api_key)
    
    # Model pricing (input/output per 1M tokens)
    model_pricing = {
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-2.0-flash-exp": {"input": 0.00, "output": 0.00},  # Free tier
    }
    
    pricing = model_pricing.get(request.model, model_pricing["gemini-1.5-pro"])
    
    # Estimate tokens per paper per stage
    tokens_per_paper = {
        "gap_extraction": {"input": 3000, "output": 500},
        "relevance": {"input": 2000, "output": 200},
        "deep_review": {"input": 5000, "output": 1500}
    }
    
    # Calculate fresh cost (no cache)
    fresh_cost = 0.0
    for stage, tokens in tokens_per_paper.items():
        input_cost = (tokens["input"] * request.paper_count / 1_000_000) * pricing["input"]
        output_cost = (tokens["output"] * request.paper_count / 1_000_000) * pricing["output"]
        fresh_cost += input_cost + output_cost
    
    # Cached cost (assume 80% cache hit rate)
    cache_hit_rate = 0.8 if request.use_cache else 0.0
    cached_cost = fresh_cost * (1 - cache_hit_rate)
    
    return {
        "paper_count": request.paper_count,
        "model": request.model,
        "fresh_cost": round(fresh_cost, 2),
        "cached_cost": round(cached_cost, 2),
        "savings": round(fresh_cost - cached_cost, 2),
        "cache_hit_rate": cache_hit_rate
    }
```

**Modified Job Start with Force Flag:**

```python
@app.post("/api/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    config: JobConfig,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Start job with optional force re-analysis."""
    verify_api_key(api_key)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Build CLI command
    cmd = ["python", "pipeline_orchestrator.py", "--batch-mode"]
    
    # Add force flag
    if config.force:
        if not config.force_confirmed:
            raise HTTPException(
                400,
                "Force re-analysis requires cost impact confirmation"
            )
        
        cmd.append("--force")
        logger.warning(
            f"Job {job_id} starting with --force (cache disabled, "
            "costs may be higher)"
        )
    
    # ... rest of command building ...
    
    # Store force flag in metadata
    job_metadata = load_job_metadata(job_id)
    job_metadata["force_enabled"] = config.force
    job_metadata["force_confirmed"] = config.force_confirmed
    
    if config.force:
        job_metadata["cache_disabled"] = True
        job_metadata["expected_higher_cost"] = True
    
    save_job_metadata(job_id, job_metadata)
    
    # Execute pipeline
    asyncio.create_task(execute_pipeline_async(job_id, cmd))
    
    return {
        "status": "started",
        "job_id": job_id,
        "force_enabled": config.force,
        "cache_disabled": config.force,
        "command": " ".join(cmd)
    }
```

**Cache Statistics Endpoint (bonus):**

```python
@app.get(
    "/api/cache/stats",
    tags=["Cache Management"],
    summary="Get cache statistics"
)
async def get_cache_stats(
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get cache statistics for all cache directories.
    
    Shows size, entry count, hit rate, age.
    """
    verify_api_key(api_key)
    
    cache_dirs = [
        BASE_DIR / "cache",
        BASE_DIR / "deep_reviewer_cache",
        BASE_DIR / "judge_cache"
    ]
    
    stats = {}
    
    for cache_dir in cache_dirs:
        if not cache_dir.exists():
            continue
        
        # Count files and size
        files = list(cache_dir.rglob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        
        # Get oldest and newest
        if files:
            oldest = min(files, key=lambda f: f.stat().st_mtime)
            newest = max(files, key=lambda f: f.stat().st_mtime)
            
            stats[cache_dir.name] = {
                "entry_count": len(files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_entry": datetime.fromtimestamp(
                    oldest.stat().st_mtime
                ).isoformat(),
                "newest_entry": datetime.fromtimestamp(
                    newest.stat().st_mtime
                ).isoformat()
            }
        else:
            stats[cache_dir.name] = {
                "entry_count": 0,
                "total_size_mb": 0.0,
                "oldest_entry": None,
                "newest_entry": None
            }
    
    return {
        "caches": stats,
        "total_entries": sum(s["entry_count"] for s in stats.values()),
        "total_size_mb": sum(s["total_size_mb"] for s in stats.values())
    }
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Force Re-analysis checkbox functional in Advanced Options
- [ ] Checking box shows cost warning with confirmation
- [ ] Cost estimate API returns accurate fresh vs cached costs
- [ ] Confirmation checkbox required when force enabled
- [ ] `--force` flag passed to CLI when enabled
- [ ] Job metadata tracks force flag usage
- [ ] Job submission blocked if force enabled but not confirmed

### User Experience
- [ ] Warning clearly explains cost impact
- [ ] Cost estimate shows specific dollar amounts
- [ ] "When to use" help text accessible
- [ ] Confirmation checkbox prevents accidental usage
- [ ] Warning dismisses when force unchecked
- [ ] Clear visual distinction (warning badge, yellow alert)

### Cost Estimation
- [ ] Estimates based on uploaded file count
- [ ] Shows both cached and fresh costs
- [ ] Displays cost difference (savings lost)
- [ ] Updates when file count changes
- [ ] Handles free models (gemini-2.0-flash-exp) correctly

### CLI Parity
- [ ] `--force` → Force Re-analysis checkbox (100%)
- [ ] Same cache bypass behavior as CLI
- [ ] Works with all pipeline stages

### Edge Cases
- [ ] Force enabled but no files uploaded → estimate uses placeholder
- [ ] Free model selected → warning shows $0 impact
- [ ] Huge file count (>100) → warning emphasizes high cost
- [ ] Network error during cost estimate → generic warning shown

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_force_reanalysis.py

def test_cost_estimate_api():
    """Test cost estimation endpoint."""
    request = {
        "paper_count": 10,
        "use_cache": False,
        "model": "gemini-1.5-pro"
    }
    
    response = client.post("/api/cost/estimate",
                          json=request,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert "fresh_cost" in data
    assert "cached_cost" in data
    assert data["fresh_cost"] > data["cached_cost"]

def test_job_start_with_force():
    """Test starting job with force flag."""
    config = {
        "force": True,
        "force_confirmed": True
    }
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["force_enabled"] is True
    assert "--force" in data["command"]

def test_force_without_confirmation_rejected():
    """Test that force without confirmation is rejected."""
    config = {
        "force": True,
        "force_confirmed": False  # Not confirmed
    }
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 400
    assert "confirmation" in response.json()["detail"].lower()

def test_cache_stats_api():
    """Test cache statistics endpoint."""
    response = client.get("/api/cache/stats",
                         headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert "caches" in data
    assert "total_entries" in data

def test_cost_estimate_with_free_model():
    """Test cost estimate with free model (gemini-2.0-flash-exp)."""
    request = {
        "paper_count": 10,
        "use_cache": False,
        "model": "gemini-2.0-flash-exp"
    }
    
    response = client.post("/api/cost/estimate", json=request)
    data = response.json()
    
    # Free model should have $0 cost
    assert data["fresh_cost"] == 0.0
    assert data["cached_cost"] == 0.0
```

### Integration Tests

```python
def test_e2e_force_reanalysis():
    """End-to-end: enable force → confirm → run → verify fresh API calls."""
    # 1. Upload files
    job_id = upload_test_files()
    
    # 2. Get cost estimate
    estimate_response = client.post("/api/cost/estimate", json={
        "paper_count": 3,
        "use_cache": False
    })
    estimate = estimate_response.json()
    assert estimate["fresh_cost"] > 0
    
    # 3. Start job with force enabled
    config = {
        "force": True,
        "force_confirmed": True
    }
    start_response = client.post(f"/api/jobs/{job_id}/start", json=config)
    assert start_response.json()["force_enabled"] is True
    
    # 4. Wait for completion
    wait_for_job_completion(job_id)
    
    # 5. Verify cache was not used (check logs or API call count)
    job_metadata = load_job_metadata(job_id)
    assert job_metadata["force_enabled"] is True
    assert job_metadata["cache_disabled"] is True
    
    # 6. Verify fresh API calls were made
    cost_report = load_cost_report(job_id)
    assert cost_report["cache_hits"] == 0  # No cache hits
```

### Manual Testing Checklist

- [ ] Check force box → warning appears
- [ ] Uncheck force box → warning disappears
- [ ] Cost estimate shows realistic values
- [ ] Confirmation required before submission
- [ ] Submit without confirmation → error shown
- [ ] Submit with force → --force in command
- [ ] Run with force → verify fresh API calls (check logs)
- [ ] Cache stats show current cache size

---

## 📚 Documentation Updates

### User Guide

```markdown
## Force Re-analysis

By default, the pipeline uses cached API responses to save time and money. Use **Force Re-analysis** when you need a completely fresh run.

### When to Use

✅ **Use Force when:**
- Testing new models or prompts
- Verifying configuration changes worked
- Ensuring reproducibility (no cache influence)
- Cache corruption suspected
- Model behavior has changed

❌ **Don't use Force when:**
- Running analysis for the first time (no cache exists)
- Continuing previous analysis (use continuation mode)
- Just viewing existing results

### How to Enable

1. Expand **Advanced Options**
2. Check **Force Re-analysis**
3. Review cost warning (fresh vs cached costs)
4. Check "I understand this will increase costs"
5. Start analysis

### Cost Impact

Force re-analysis makes fresh API calls instead of using cache:

| Papers | Cached Cost | Fresh Cost | Difference |
|--------|------------|------------|------------|
| 10     | ~$0.50     | ~$5.00     | +$4.50     |
| 50     | ~$2.50     | ~$25.00    | +$22.50    |
| 100    | ~$5.00     | ~$50.00    | +$45.00    |

*Costs vary by model selection.*

### Verify Cache Bypass

After job completes:
1. Go to job detail page
2. Check "Configuration" section
3. Verify "Force Enabled: Yes"
4. Check cost report for "Cache Hits: 0"
```

---

## 🚀 Deployment Checklist

- [ ] Frontend force checkbox implemented (already in W1-2)
- [ ] Cost warning UI implemented
- [ ] Cost estimate API deployed (`/api/cost/estimate`)
- [ ] Cache stats API deployed (`/api/cache/stats`)
- [ ] Job start modified to handle force flag
- [ ] Confirmation validation implemented
- [ ] Unit tests passing (8+ tests)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Deployed to staging
- [ ] Manual testing completed
- [ ] Cost estimates verified accurate
- [ ] Deployed to production

---

## 📊 Success Metrics

**After Deployment:**
- Force re-analysis control functional (100%)
- Dashboard parity increases by 1% (cache control)
- Users can force fresh analysis when needed
- Cost warnings prevent accidental expensive runs

**Monitoring:**
- Track % of jobs using force flag
- Track cost difference (forced vs normal jobs)
- Track confirmation bypass attempts (blocked)
- Collect user feedback on cost estimates accuracy

---

**Task Card Version:** 1.0  
**Created:** November 21, 2025  
**Estimated Effort:** 4-6 hours  
**Priority:** 🟠 HIGH  
**Dependency:** Requires PARITY-W1-2 (Advanced Options Panel)
