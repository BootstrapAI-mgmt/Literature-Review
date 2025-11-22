# PARITY-W2-3: Cache Management

**Priority:** 🟠 **HIGH**  
**Effort:** 6-8 hours  
**Wave:** 2 (High Priority Features)  
**Dependencies:** PARITY-W1-2 (Advanced Options Panel)

---

## 📋 Problem Statement

**Current State:**  
Dashboard has no visibility into cache state - users cannot see cache size, hit rate, age, or manually clear cache. CLI has `--clear-cache` flag but Dashboard lacks equivalent control.

**CLI Capability:**
```bash
python pipeline_orchestrator.py --clear-cache  # Delete all cached responses
```

**User Problems:**
- No way to see what's cached
- Cannot clear cache without CLI access or manual file deletion
- No visibility into cache hit rate (cost savings)
- Cannot selectively clear cache (e.g., just one model)
- Cache corruption invisible until analysis fails

**Gap:** Zero cache visibility or management in Dashboard.

---

## 🎯 Objective

Add comprehensive cache management to Dashboard: visibility (statistics dashboard), control (clear cache checkbox + selective clearing), and monitoring (hit rates, savings), matching and exceeding CLI's `--clear-cache` functionality.

---

## 📐 Design

### UI Components

**Location 1:** Advanced Options Panel (Clear Cache checkbox)

**Location 2:** New Cache Management page/section

**Advanced Options - Clear Cache Checkbox:**

```html
<!-- Clear Cache (in Advanced Options Panel) -->
<div class="mb-3">
    <div class="form-check form-switch">
        <input class="form-check-input" type="checkbox" 
               id="clearCache"
               onchange="updateClearCacheWarning()">
        <label class="form-check-label" for="clearCache">
            <strong>Clear Cache Before Starting</strong>
            <span class="badge bg-danger">CLI: --clear-cache</span>
        </label>
        <div class="form-text">
            Delete all cached API responses before starting analysis.
            Use when switching models or updating prompts.
        </div>
    </div>
    
    <!-- Clear Cache Warning -->
    <div id="clearCacheWarning" style="display: none;" class="alert alert-info mt-2">
        <strong>ℹ️ Cache Clearing</strong>
        <p class="mb-2">
            This will delete <strong id="cacheEntryCount">-</strong> cached responses
            (<strong id="cacheSizeMB">-</strong> MB).
        </p>
        <p class="mb-0">
            <small>
                First run after clearing will be slower and cost more.
                Subsequent runs will rebuild cache.
            </small>
        </p>
    </div>
    
    <!-- Link to Cache Management -->
    <a href="#" class="btn btn-sm btn-link p-0 mt-1" 
       onclick="showCacheManagement(); return false;">
        📊 View Cache Statistics
    </a>
</div>

<script>
// Update clear cache warning with current stats
async function updateClearCacheWarning() {
    const clearEnabled = document.getElementById('clearCache').checked;
    const warning = document.getElementById('clearCacheWarning');
    
    if (clearEnabled) {
        warning.style.display = 'block';
        
        // Fetch cache stats
        try {
            const response = await fetch('/api/cache/stats', {
                headers: { 'X-API-KEY': API_KEY }
            });
            const stats = await response.json();
            
            document.getElementById('cacheEntryCount').textContent = 
                stats.total_entries.toLocaleString();
            document.getElementById('cacheSizeMB').textContent = 
                stats.total_size_mb.toFixed(1);
                
        } catch (error) {
            console.error('Failed to fetch cache stats:', error);
        }
    } else {
        warning.style.display = 'none';
    }
}

// Include in job submission
function getAdvancedOptions() {
    return {
        // ... other options ...
        clear_cache: document.getElementById('clearCache').checked
    };
}
</script>
```

**Cache Management Dashboard Widget:**

```html
<!-- Cache Management Section (new page or modal) -->
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0">
            🗄️ Cache Management
            <button class="btn btn-sm btn-outline-primary float-end" 
                    onclick="refreshCacheStats()">
                🔄 Refresh
            </button>
        </h5>
    </div>
    <div class="card-body">
        
        <!-- Overall Statistics -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h6 class="text-muted mb-0">Total Entries</h6>
                        <h3 id="totalCacheEntries" class="mb-0">-</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h6 class="text-muted mb-0">Total Size</h6>
                        <h3 id="totalCacheSize" class="mb-0">-</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h6 class="text-muted mb-0">Hit Rate (7d)</h6>
                        <h3 id="cacheHitRate" class="mb-0">-</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h6 class="text-muted mb-0">Savings (7d)</h6>
                        <h3 id="cacheSavings" class="mb-0">-</h3>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Per-Cache Breakdown -->
        <h6>Cache Breakdown</h6>
        <div class="table-responsive">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Cache Type</th>
                        <th>Entries</th>
                        <th>Size</th>
                        <th>Oldest Entry</th>
                        <th>Newest Entry</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="cacheBreakdownTable">
                    <!-- Populated dynamically -->
                </tbody>
            </table>
        </div>
        
        <!-- Cache Actions -->
        <div class="mt-4">
            <h6>Cache Actions</h6>
            
            <!-- Clear All -->
            <button class="btn btn-danger" onclick="clearAllCache()">
                🗑️ Clear All Caches
            </button>
            
            <!-- Clear by Age -->
            <button class="btn btn-warning" onclick="showClearByAge()">
                📅 Clear Old Entries
            </button>
            
            <!-- Clear by Model -->
            <button class="btn btn-warning" onclick="showClearByModel()">
                🤖 Clear by Model
            </button>
            
            <!-- Export Cache Stats -->
            <button class="btn btn-outline-secondary" onclick="exportCacheStats()">
                💾 Export Statistics
            </button>
        </div>
        
        <!-- Clear by Age Modal -->
        <div id="clearByAgeSection" style="display: none;" class="mt-3">
            <div class="card">
                <div class="card-body">
                    <h6>Clear Entries Older Than:</h6>
                    <div class="row align-items-end">
                        <div class="col-md-4">
                            <label for="ageValue" class="form-label">Value</label>
                            <input type="number" class="form-control" 
                                   id="ageValue" value="30" min="1">
                        </div>
                        <div class="col-md-4">
                            <label for="ageUnit" class="form-label">Unit</label>
                            <select class="form-select" id="ageUnit">
                                <option value="days" selected>Days</option>
                                <option value="weeks">Weeks</option>
                                <option value="months">Months</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <button class="btn btn-warning w-100" 
                                    onclick="clearByAge()">
                                Clear Old Entries
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Clear by Model Modal -->
        <div id="clearByModelSection" style="display: none;" class="mt-3">
            <div class="card">
                <div class="card-body">
                    <h6>Clear Cache for Model:</h6>
                    <div class="row align-items-end">
                        <div class="col-md-8">
                            <label for="modelSelect" class="form-label">Model</label>
                            <select class="form-select" id="modelSelect">
                                <option value="">-- Select Model --</option>
                                <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                                <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                                <option value="gemini-2.0-flash-exp">gemini-2.0-flash-exp</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <button class="btn btn-warning w-100" 
                                    onclick="clearByModel()">
                                Clear Model Cache
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
    </div>
</div>

<script>
// Refresh cache statistics
async function refreshCacheStats() {
    try {
        const response = await fetch('/api/cache/stats', {
            headers: { 'X-API-KEY': API_KEY }
        });
        const stats = await response.json();
        
        // Update overall stats
        document.getElementById('totalCacheEntries').textContent = 
            stats.total_entries.toLocaleString();
        document.getElementById('totalCacheSize').textContent = 
            stats.total_size_mb.toFixed(1) + ' MB';
        document.getElementById('cacheHitRate').textContent = 
            (stats.hit_rate_7d * 100).toFixed(1) + '%';
        document.getElementById('cacheSavings').textContent = 
            '$' + stats.savings_7d.toFixed(2);
        
        // Update table
        const tbody = document.getElementById('cacheBreakdownTable');
        tbody.innerHTML = '';
        
        Object.entries(stats.caches).forEach(([name, cacheStats]) => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td><strong>${name}</strong></td>
                <td>${cacheStats.entry_count.toLocaleString()}</td>
                <td>${cacheStats.total_size_mb.toFixed(1)} MB</td>
                <td>${formatDate(cacheStats.oldest_entry)}</td>
                <td>${formatDate(cacheStats.newest_entry)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="clearSpecificCache('${name}')">
                        Clear
                    </button>
                </td>
            `;
        });
        
    } catch (error) {
        console.error('Failed to refresh cache stats:', error);
        alert('Failed to load cache statistics');
    }
}

// Clear all caches
async function clearAllCache() {
    if (!confirm('Clear ALL caches? This cannot be undone. First analysis after clearing will be slower and more expensive.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/cache/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            },
            body: JSON.stringify({ clear_all: true })
        });
        
        const result = await response.json();
        alert(`Cleared ${result.entries_deleted} cache entries (${result.size_freed_mb.toFixed(1)} MB)`);
        refreshCacheStats();
        
    } catch (error) {
        console.error('Failed to clear cache:', error);
        alert('Failed to clear cache');
    }
}

// Clear specific cache
async function clearSpecificCache(cacheName) {
    if (!confirm(`Clear ${cacheName} cache?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/cache/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            },
            body: JSON.stringify({ cache_name: cacheName })
        });
        
        const result = await response.json();
        alert(`Cleared ${result.entries_deleted} entries from ${cacheName}`);
        refreshCacheStats();
        
    } catch (error) {
        console.error('Failed to clear cache:', error);
        alert('Failed to clear cache');
    }
}

// Clear by age
async function clearByAge() {
    const value = document.getElementById('ageValue').value;
    const unit = document.getElementById('ageUnit').value;
    
    if (!confirm(`Clear cache entries older than ${value} ${unit}?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/cache/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            },
            body: JSON.stringify({
                older_than: { value: parseInt(value), unit: unit }
            })
        });
        
        const result = await response.json();
        alert(`Cleared ${result.entries_deleted} old cache entries`);
        refreshCacheStats();
        
    } catch (error) {
        console.error('Failed to clear cache:', error);
        alert('Failed to clear cache');
    }
}

// Clear by model
async function clearByModel() {
    const model = document.getElementById('modelSelect').value;
    
    if (!model) {
        alert('Please select a model');
        return;
    }
    
    if (!confirm(`Clear all cache entries for ${model}?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/cache/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            },
            body: JSON.stringify({ model: model })
        });
        
        const result = await response.json();
        alert(`Cleared ${result.entries_deleted} entries for ${model}`);
        refreshCacheStats();
        
    } catch (error) {
        console.error('Failed to clear cache:', error);
        alert('Failed to clear cache');
    }
}

// Helper functions
function formatDate(isoDate) {
    if (!isoDate) return '-';
    return new Date(isoDate).toLocaleDateString();
}

function showClearByAge() {
    document.getElementById('clearByAgeSection').style.display = 'block';
    document.getElementById('clearByModelSection').style.display = 'none';
}

function showClearByModel() {
    document.getElementById('clearByModelSection').style.display = 'block';
    document.getElementById('clearByAgeSection').style.display = 'none';
}

// Load stats on page load
document.addEventListener('DOMContentLoaded', refreshCacheStats);
</script>
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**Enhanced Cache Stats Endpoint:**

```python
from datetime import datetime, timedelta
import shutil

@app.get(
    "/api/cache/stats",
    tags=["Cache Management"],
    summary="Get comprehensive cache statistics"
)
async def get_cache_stats(
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get detailed cache statistics including hit rates and savings.
    """
    verify_api_key(api_key)
    
    cache_dirs = {
        "gap_extraction": BASE_DIR / "cache",
        "deep_review": BASE_DIR / "deep_reviewer_cache",
        "judge": BASE_DIR / "judge_cache"
    }
    
    stats = {}
    total_entries = 0
    total_size = 0
    
    for cache_name, cache_dir in cache_dirs.items():
        if not cache_dir.exists():
            stats[cache_name] = {
                "entry_count": 0,
                "total_size_mb": 0.0,
                "oldest_entry": None,
                "newest_entry": None
            }
            continue
        
        # Count files and size
        files = list(cache_dir.rglob("*.json"))
        size_bytes = sum(f.stat().st_size for f in files)
        
        # Get oldest and newest
        if files:
            oldest = min(files, key=lambda f: f.stat().st_mtime)
            newest = max(files, key=lambda f: f.stat().st_mtime)
            
            stats[cache_name] = {
                "entry_count": len(files),
                "total_size_mb": round(size_bytes / (1024 * 1024), 2),
                "oldest_entry": datetime.fromtimestamp(
                    oldest.stat().st_mtime
                ).isoformat(),
                "newest_entry": datetime.fromtimestamp(
                    newest.stat().st_mtime
                ).isoformat()
            }
            
            total_entries += len(files)
            total_size += size_bytes
        else:
            stats[cache_name] = {
                "entry_count": 0,
                "total_size_mb": 0.0,
                "oldest_entry": None,
                "newest_entry": None
            }
    
    # Calculate hit rate and savings (from job history)
    hit_rate_7d, savings_7d = calculate_cache_metrics(days=7)
    
    return {
        "caches": stats,
        "total_entries": total_entries,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "hit_rate_7d": hit_rate_7d,
        "savings_7d": savings_7d
    }


def calculate_cache_metrics(days: int = 7) -> tuple:
    """
    Calculate cache hit rate and cost savings from recent jobs.
    
    Returns (hit_rate, savings_in_dollars).
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    total_calls = 0
    cache_hits = 0
    total_savings = 0.0
    
    # Scan recent job cost reports
    cost_reports_dir = BASE_DIR / "cost_reports"
    if cost_reports_dir.exists():
        for report_file in cost_reports_dir.glob("*.json"):
            try:
                # Check if report is within date range
                mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                if mtime < cutoff_date:
                    continue
                
                with open(report_file) as f:
                    report = json.load(f)
                    
                    total_calls += report.get("total_api_calls", 0)
                    cache_hits += report.get("cache_hits", 0)
                    total_savings += report.get("cache_savings", 0.0)
                    
            except Exception as e:
                logger.warning(f"Failed to read cost report {report_file}: {e}")
                continue
    
    hit_rate = cache_hits / total_calls if total_calls > 0 else 0.0
    
    return hit_rate, total_savings


@app.post(
    "/api/cache/clear",
    tags=["Cache Management"],
    summary="Clear cache selectively or completely"
)
async def clear_cache(
    request: Dict[str, Any],
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Clear cache based on various criteria.
    
    Supported filters:
    - clear_all: bool - Clear everything
    - cache_name: str - Clear specific cache (gap_extraction, deep_review, judge)
    - older_than: {value: int, unit: str} - Clear entries older than X days/weeks/months
    - model: str - Clear entries for specific model
    """
    verify_api_key(api_key)
    
    cache_dirs = {
        "gap_extraction": BASE_DIR / "cache",
        "deep_review": BASE_DIR / "deep_reviewer_cache",
        "judge": BASE_DIR / "judge_cache"
    }
    
    entries_deleted = 0
    size_freed = 0
    
    # Clear all
    if request.get("clear_all"):
        for cache_dir in cache_dirs.values():
            if cache_dir.exists():
                deleted, freed = clear_directory(cache_dir)
                entries_deleted += deleted
                size_freed += freed
        
        logger.warning(f"Cleared ALL caches: {entries_deleted} entries, {size_freed / (1024*1024):.1f} MB")
        
        return {
            "status": "cleared",
            "entries_deleted": entries_deleted,
            "size_freed_mb": round(size_freed / (1024 * 1024), 2)
        }
    
    # Clear specific cache
    if cache_name := request.get("cache_name"):
        if cache_name not in cache_dirs:
            raise HTTPException(400, f"Invalid cache name: {cache_name}")
        
        cache_dir = cache_dirs[cache_name]
        if cache_dir.exists():
            entries_deleted, size_freed = clear_directory(cache_dir)
        
        logger.info(f"Cleared {cache_name} cache: {entries_deleted} entries")
        
        return {
            "status": "cleared",
            "cache_name": cache_name,
            "entries_deleted": entries_deleted,
            "size_freed_mb": round(size_freed / (1024 * 1024), 2)
        }
    
    # Clear by age
    if older_than := request.get("older_than"):
        value = older_than["value"]
        unit = older_than["unit"]
        
        # Convert to days
        days_multiplier = {"days": 1, "weeks": 7, "months": 30}
        age_days = value * days_multiplier.get(unit, 1)
        cutoff_date = datetime.now() - timedelta(days=age_days)
        cutoff_timestamp = cutoff_date.timestamp()
        
        for cache_dir in cache_dirs.values():
            if not cache_dir.exists():
                continue
            
            for cache_file in cache_dir.rglob("*.json"):
                if cache_file.stat().st_mtime < cutoff_timestamp:
                    size = cache_file.stat().st_size
                    cache_file.unlink()
                    entries_deleted += 1
                    size_freed += size
        
        logger.info(f"Cleared {entries_deleted} entries older than {value} {unit}")
        
        return {
            "status": "cleared",
            "criteria": f"older than {value} {unit}",
            "entries_deleted": entries_deleted,
            "size_freed_mb": round(size_freed / (1024 * 1024), 2)
        }
    
    # Clear by model
    if model := request.get("model"):
        # Cache entries typically include model name in filename or content
        for cache_dir in cache_dirs.values():
            if not cache_dir.exists():
                continue
            
            for cache_file in cache_dir.rglob("*.json"):
                # Check if model is in filename
                if model in cache_file.name:
                    size = cache_file.stat().st_size
                    cache_file.unlink()
                    entries_deleted += 1
                    size_freed += size
                else:
                    # Check if model is in cache content
                    try:
                        with open(cache_file) as f:
                            content = f.read()
                            if model in content:
                                size = cache_file.stat().st_size
                                cache_file.unlink()
                                entries_deleted += 1
                                size_freed += size
                    except:
                        pass
        
        logger.info(f"Cleared {entries_deleted} entries for model {model}")
        
        return {
            "status": "cleared",
            "model": model,
            "entries_deleted": entries_deleted,
            "size_freed_mb": round(size_freed / (1024 * 1024), 2)
        }
    
    raise HTTPException(400, "No valid clearing criteria specified")


def clear_directory(directory: Path) -> tuple:
    """
    Clear all files in directory, return (count, size).
    """
    count = 0
    size = 0
    
    for file in directory.rglob("*.json"):
        size += file.stat().st_size
        file.unlink()
        count += 1
    
    return count, size
```

**Modified Job Start with Clear Cache:**

```python
@app.post("/api/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    config: JobConfig,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Start job with optional cache clearing."""
    verify_api_key(api_key)
    
    # ... job validation ...
    
    # Clear cache if requested
    if config.clear_cache:
        logger.info(f"Clearing cache before job {job_id}")
        
        clear_result = await clear_cache({"clear_all": True}, api_key)
        
        job_metadata = load_job_metadata(job_id)
        job_metadata["cache_cleared_before_start"] = True
        job_metadata["cache_entries_cleared"] = clear_result["entries_deleted"]
        save_job_metadata(job_id, job_metadata)
    
    # Build CLI command
    cmd = ["python", "pipeline_orchestrator.py", "--batch-mode"]
    
    if config.clear_cache:
        cmd.append("--clear-cache")
    
    # ... rest of command building ...
    
    return {
        "status": "started",
        "job_id": job_id,
        "cache_cleared": config.clear_cache,
        "command": " ".join(cmd)
    }
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Clear Cache checkbox in Advanced Options functional
- [ ] Cache statistics dashboard shows current state
- [ ] Clear all cache button works
- [ ] Selective clearing (by age, by model, by cache type) works
- [ ] Cache hit rate calculated from job history
- [ ] Cost savings tracked and displayed
- [ ] `--clear-cache` flag passed to CLI when enabled

### User Experience  
- [ ] Cache stats load in < 2 seconds
- [ ] Clear operations show confirmation dialogs
- [ ] Success/failure messages after clearing
- [ ] Real-time stats refresh after clearing
- [ ] Hit rate and savings clearly displayed
- [ ] Table shows per-cache breakdown

### Cache Visibility
- [ ] Total entries, size, hit rate, savings shown
- [ ] Per-cache stats (gap extraction, deep review, judge)
- [ ] Oldest and newest entry dates
- [ ] Hit rate calculated over 7 days
- [ ] Cost savings in dollars

### Selective Clearing
- [ ] Clear all caches (nuclear option)
- [ ] Clear specific cache (gap/review/judge)
- [ ] Clear by age (days/weeks/months)
- [ ] Clear by model name
- [ ] Deletion count and size freed reported

### CLI Parity
- [ ] `--clear-cache` → Clear Cache checkbox (100%)
- [ ] Dashboard adds visibility CLI lacks (advantage)

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_cache_management.py

def test_get_cache_stats():
    """Test cache statistics endpoint."""
    response = client.get("/api/cache/stats",
                         headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert "caches" in data
    assert "total_entries" in data
    assert "hit_rate_7d" in data

def test_clear_all_cache():
    """Test clearing all caches."""
    response = client.post("/api/cache/clear",
                          json={"clear_all": True},
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    assert response.json()["status"] == "cleared"

def test_clear_specific_cache():
    """Test clearing specific cache."""
    response = client.post("/api/cache/clear",
                          json={"cache_name": "gap_extraction"},
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    assert response.json()["cache_name"] == "gap_extraction"

def test_clear_by_age():
    """Test clearing cache by age."""
    response = client.post("/api/cache/clear",
                          json={
                              "older_than": {"value": 30, "unit": "days"}
                          },
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200

def test_job_start_with_clear_cache():
    """Test starting job with cache clearing."""
    config = {"clear_cache": True}
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    assert response.json()["cache_cleared"] is True
    assert "--clear-cache" in response.json()["command"]
```

### Integration Tests

```python
def test_e2e_cache_management():
    """End-to-end: view stats → clear → verify cleared."""
    # 1. Get initial stats
    stats_before = client.get("/api/cache/stats").json()
    initial_entries = stats_before["total_entries"]
    
    # 2. Clear all
    clear_result = client.post("/api/cache/clear", 
                              json={"clear_all": True}).json()
    assert clear_result["entries_deleted"] == initial_entries
    
    # 3. Verify cleared
    stats_after = client.get("/api/cache/stats").json()
    assert stats_after["total_entries"] == 0
```

---

## 📚 Documentation Updates

### User Guide

```markdown
## Cache Management

The pipeline caches API responses to save time and money. View cache statistics and manage cache through the Dashboard.

### View Cache Statistics

Navigate to **Cache Management** to see:
- **Total Entries:** Number of cached responses
- **Total Size:** Disk space used by cache
- **Hit Rate:** % of API calls served from cache (last 7 days)
- **Savings:** Money saved by using cache (last 7 days)

### Clear Cache

**When to clear:**
- Switching to different models
- Updating prompts or analysis logic
- Cache corruption suspected
- Testing reproducibility

**How to clear:**

1. **Clear Before Job:** Check "Clear Cache Before Starting" in Advanced Options
2. **Clear All:** Click "Clear All Caches" in Cache Management
3. **Selective Clear:** Clear by age, model, or cache type

### Cost Impact

Clearing cache means next analysis will:
- Take longer (no cached responses)
- Cost more (fresh API calls)
- Rebuild cache for future use

Typical savings from cache: 60-80% of cost.
```

---

## 🚀 Deployment Checklist

- [ ] Clear Cache checkbox implemented (already in W1-2)
- [ ] Cache stats API deployed
- [ ] Cache clear API deployed with selective options
- [ ] Cache management dashboard UI created
- [ ] Hit rate calculation working
- [ ] Cost savings tracking working
- [ ] Unit tests passing (10+ tests)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Deployed to staging
- [ ] Manual testing completed
- [ ] Deployed to production

---

## 📊 Success Metrics

**After Deployment:**
- Cache management fully functional
- Dashboard parity increases by 2% (cache control + visibility)
- Users can see and manage cache effectively
- Cache hit rates visible (transparency)

**Monitoring:**
- Track cache clearing frequency
- Track hit rates over time
- Track cost savings attribution
- Collect user feedback on cache UI

---

**Task Card Version:** 1.0  
**Created:** November 21, 2025  
**Estimated Effort:** 6-8 hours  
**Priority:** 🟠 HIGH  
**Dependency:** Requires PARITY-W1-2 (Advanced Options Panel)
