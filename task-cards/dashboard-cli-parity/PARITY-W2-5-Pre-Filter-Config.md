# PARITY-W2-5: Pre-Filter Configuration UI

**Priority:** 🟠 **HIGH**  
**Effort:** 6-8 hours  
**Wave:** 2 (High Priority Features)  
**Dependencies:** PARITY-W1-2 (Advanced Options Panel)

---

## 📋 Problem Statement

**Current State:**  
Dashboard uses default pre-filter configuration (title/abstract/intro). Users cannot customize which paper sections to include in gap analysis, forcing them to analyze all sections or none.

**CLI Capability:**
```bash
# Custom pre-filter (only analyze abstracts and introductions)
python pipeline_orchestrator.py --pre-filter abstract,introduction

# Analyze all sections (no pre-filter)
python pipeline_orchestrator.py --pre-filter ""

# Default (title, abstract, intro)
python pipeline_orchestrator.py  # no flag = default
```

**User Problems:**
- Cannot target specific sections (e.g., only methods for methodology review)
- Cannot disable pre-filter to analyze full papers
- Cannot optimize for speed (fewer sections = faster analysis)
- Cannot optimize for cost (fewer tokens = lower cost)
- No control over analysis scope

**Gap:** No UI controls for pre-filter configuration.

---

## 🎯 Objective

Add pre-filter configuration UI matching CLI's `--pre-filter` flag, allowing users to select which paper sections to analyze for gap extraction.

---

## 📐 Design

### UI Components

**Location:** Advanced Options Panel in `webdashboard/templates/index.html`

**Pre-Filter Configuration Card:**

```html
<!-- Pre-Filter Configuration (in Advanced Options Panel) -->
<div class="card mb-3 border-secondary">
    <div class="card-header bg-secondary bg-opacity-10">
        <h6 class="mb-0">📄 Pre-Filter: Paper Sections</h6>
    </div>
    <div class="card-body">
        
        <!-- Mode Selector -->
        <div class="mb-3">
            <label class="form-label">
                <strong>Analysis Scope</strong>
                <span class="badge bg-secondary">CLI: --pre-filter</span>
            </label>
            
            <div class="btn-group w-100" role="group">
                <input type="radio" class="btn-check" name="prefilterMode" 
                       id="prefilterDefault" value="default" checked
                       onchange="updatePreFilterMode()">
                <label class="btn btn-outline-secondary" for="prefilterDefault">
                    ✅ Default<br>
                    <small class="text-muted">Title + Abstract + Intro</small>
                </label>
                
                <input type="radio" class="btn-check" name="prefilterMode" 
                       id="prefilterCustom" value="custom"
                       onchange="updatePreFilterMode()">
                <label class="btn btn-outline-primary" for="prefilterCustom">
                    🎛️ Custom<br>
                    <small class="text-muted">Choose Sections</small>
                </label>
                
                <input type="radio" class="btn-check" name="prefilterMode" 
                       id="prefilterFull" value="full"
                       onchange="updatePreFilterMode()">
                <label class="btn btn-outline-warning" for="prefilterFull">
                    📖 Full Paper<br>
                    <small class="text-muted">All Sections</small>
                </label>
            </div>
            
            <div class="form-text">
                Control which sections to analyze for gap extraction. 
                Fewer sections = faster analysis and lower cost.
            </div>
        </div>
        
        <!-- Custom Section Selector -->
        <div id="customSectionsPanel" style="display: none;" class="mb-3">
            <label class="form-label">Select Sections to Analyze:</label>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="form-check">
                        <input class="form-check-input section-checkbox" type="checkbox" 
                               id="section_title" value="title" checked>
                        <label class="form-check-label" for="section_title">
                            <strong>Title</strong>
                            <small class="text-muted d-block">Paper title and keywords</small>
                        </label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input section-checkbox" type="checkbox" 
                               id="section_abstract" value="abstract" checked>
                        <label class="form-check-label" for="section_abstract">
                            <strong>Abstract</strong>
                            <small class="text-muted d-block">High-level summary</small>
                        </label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input section-checkbox" type="checkbox" 
                               id="section_introduction" value="introduction" checked>
                        <label class="form-check-label" for="section_introduction">
                            <strong>Introduction</strong>
                            <small class="text-muted d-block">Background and motivation</small>
                        </label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input section-checkbox" type="checkbox" 
                               id="section_methods" value="methods">
                        <label class="form-check-label" for="section_methods">
                            <strong>Methods</strong>
                            <small class="text-muted d-block">Experimental design</small>
                        </label>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="form-check">
                        <input class="form-check-input section-checkbox" type="checkbox" 
                               id="section_results" value="results">
                        <label class="form-check-label" for="section_results">
                            <strong>Results</strong>
                            <small class="text-muted d-block">Findings and data</small>
                        </label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input section-checkbox" type="checkbox" 
                               id="section_discussion" value="discussion">
                        <label class="form-check-label" for="section_discussion">
                            <strong>Discussion</strong>
                            <small class="text-muted d-block">Interpretation and implications</small>
                        </label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input section-checkbox" type="checkbox" 
                               id="section_conclusion" value="conclusion">
                        <label class="form-check-label" for="section_conclusion">
                            <strong>Conclusion</strong>
                            <small class="text-muted d-block">Summary and future work</small>
                        </label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input section-checkbox" type="checkbox" 
                               id="section_references" value="references">
                        <label class="form-check-label" for="section_references">
                            <strong>References</strong>
                            <small class="text-muted d-block">Citations (rarely useful)</small>
                        </label>
                    </div>
                </div>
            </div>
            
            <!-- Selection Summary -->
            <div class="mt-3 p-2 bg-light rounded">
                <small>
                    <strong>Selected sections:</strong> 
                    <span id="selectedSectionsPreview">title, abstract, introduction</span>
                </small>
            </div>
        </div>
        
        <!-- Impact Preview -->
        <div class="alert alert-info mb-0">
            <div class="row">
                <div class="col-md-4 text-center">
                    <div class="small text-muted">Estimated Sections</div>
                    <div class="fs-5 fw-bold" id="prefilterSectionCount">3</div>
                </div>
                <div class="col-md-4 text-center">
                    <div class="small text-muted">Relative Speed</div>
                    <div class="fs-5 fw-bold" id="prefilterSpeed">Fast ⚡</div>
                </div>
                <div class="col-md-4 text-center">
                    <div class="small text-muted">Relative Cost</div>
                    <div class="fs-5 fw-bold" id="prefilterCost">Low 💰</div>
                </div>
            </div>
            <hr>
            <div class="small">
                <strong>💡 Recommendation:</strong> <span id="prefilterRecommendation">
                    Default configuration balances coverage and efficiency for most reviews.
                </span>
            </div>
        </div>
        
        <!-- Common Presets -->
        <div class="mt-3">
            <label class="form-label"><small><strong>Quick Presets:</strong></small></label>
            <div class="btn-group btn-group-sm w-100">
                <button type="button" class="btn btn-outline-secondary" 
                        onclick="applyPreset('default')">
                    Default (Title+Abstract+Intro)
                </button>
                <button type="button" class="btn btn-outline-secondary" 
                        onclick="applyPreset('abstract-only')">
                    Abstract Only
                </button>
                <button type="button" class="btn btn-outline-secondary" 
                        onclick="applyPreset('methods-focus')">
                    Methods Focus
                </button>
                <button type="button" class="btn btn-outline-secondary" 
                        onclick="applyPreset('comprehensive')">
                    Comprehensive
                </button>
            </div>
        </div>
        
    </div>
</div>

<style>
.section-checkbox:checked ~ label {
    font-weight: 600;
    color: #0d6efd;
}

#selectedSectionsPreview {
    font-family: monospace;
    color: #0d6efd;
}
</style>

<script>
// Update pre-filter mode
function updatePreFilterMode() {
    const mode = document.querySelector('input[name="prefilterMode"]:checked').value;
    
    const customPanel = document.getElementById('customSectionsPanel');
    const checkboxes = document.querySelectorAll('.section-checkbox');
    
    if (mode === 'default') {
        customPanel.style.display = 'none';
        updateImpactPreview(['title', 'abstract', 'introduction']);
        
    } else if (mode === 'custom') {
        customPanel.style.display = 'block';
        updateSelectedSections();
        
    } else if (mode === 'full') {
        customPanel.style.display = 'none';
        updateImpactPreview([
            'title', 'abstract', 'introduction', 'methods', 
            'results', 'discussion', 'conclusion', 'references'
        ]);
    }
}

// Update selected sections preview
function updateSelectedSections() {
    const checkboxes = document.querySelectorAll('.section-checkbox:checked');
    const sections = Array.from(checkboxes).map(cb => cb.value);
    
    document.getElementById('selectedSectionsPreview').textContent = 
        sections.length > 0 ? sections.join(', ') : 'none';
    
    updateImpactPreview(sections);
}

// Listen to checkbox changes
document.querySelectorAll('.section-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', updateSelectedSections);
});

// Update impact preview (speed/cost estimates)
function updateImpactPreview(sections) {
    const count = sections.length;
    
    document.getElementById('prefilterSectionCount').textContent = count;
    
    // Speed estimate
    let speed, speedEmoji;
    if (count <= 2) {
        speed = 'Very Fast';
        speedEmoji = '⚡⚡';
    } else if (count <= 3) {
        speed = 'Fast';
        speedEmoji = '⚡';
    } else if (count <= 5) {
        speed = 'Moderate';
        speedEmoji = '⏱️';
    } else {
        speed = 'Slow';
        speedEmoji = '🐌';
    }
    document.getElementById('prefilterSpeed').textContent = `${speed} ${speedEmoji}`;
    
    // Cost estimate
    let cost, costEmoji;
    if (count <= 2) {
        cost = 'Very Low';
        costEmoji = '💰';
    } else if (count <= 3) {
        cost = 'Low';
        costEmoji = '💰💰';
    } else if (count <= 5) {
        cost = 'Moderate';
        costEmoji = '💰💰💰';
    } else {
        cost = 'High';
        costEmoji = '💰💰💰💰';
    }
    document.getElementById('prefilterCost').textContent = `${cost} ${costEmoji}`;
    
    // Recommendation
    let recommendation;
    if (count === 0) {
        recommendation = '⚠️ Warning: No sections selected! Gap analysis will fail.';
    } else if (count === 1 && sections.includes('abstract')) {
        recommendation = '✅ Great for quick screening or very large datasets (100+ papers).';
    } else if (count >= 1 && count <= 3) {
        recommendation = '✅ Good balance of coverage and efficiency for most reviews.';
    } else if (count >= 4 && count <= 6) {
        recommendation = '📊 Comprehensive analysis - use for detailed reviews or small datasets.';
    } else {
        recommendation = '⚠️ Full paper analysis is slow and expensive. Consider if necessary.';
    }
    document.getElementById('prefilterRecommendation').textContent = recommendation;
}

// Apply preset configurations
function applyPreset(presetName) {
    // Switch to custom mode
    document.getElementById('prefilterCustom').checked = true;
    updatePreFilterMode();
    
    // Uncheck all first
    document.querySelectorAll('.section-checkbox').forEach(cb => cb.checked = false);
    
    // Apply preset
    const presets = {
        'default': ['title', 'abstract', 'introduction'],
        'abstract-only': ['abstract'],
        'methods-focus': ['abstract', 'methods', 'results'],
        'comprehensive': ['title', 'abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']
    };
    
    const sections = presets[presetName] || [];
    sections.forEach(section => {
        const checkbox = document.getElementById(`section_${section}`);
        if (checkbox) checkbox.checked = true;
    });
    
    updateSelectedSections();
}

// Get pre-filter configuration for submission
function getPreFilterConfig() {
    const mode = document.querySelector('input[name="prefilterMode"]:checked').value;
    
    if (mode === 'default') {
        return null;  // Use pipeline default
    } else if (mode === 'full') {
        return '';  // Empty string = no pre-filter (analyze all)
    } else {
        // Custom: return comma-separated sections
        const checkboxes = document.querySelectorAll('.section-checkbox:checked');
        return Array.from(checkboxes).map(cb => cb.value).join(',');
    }
}

// Initialize
updatePreFilterMode();
</script>
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**Modified Job Start:**

```python
class JobConfig(BaseModel):
    """Job configuration with pre-filter options."""
    mode: str = "baseline"
    # ... other options ...
    
    # Pre-filter configuration
    pre_filter: Optional[str] = None  # None=default, ""=full, "section1,section2"=custom


@app.post("/api/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    config: JobConfig,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Start job with optional pre-filter configuration."""
    verify_api_key(api_key)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Build CLI command
    cmd = ["python", "pipeline_orchestrator.py", "--batch-mode"]
    
    # Add pre-filter configuration
    if config.pre_filter is not None:
        # Validate sections if custom
        if config.pre_filter:  # Non-empty string
            valid_sections = [
                'title', 'abstract', 'introduction', 'methods',
                'results', 'discussion', 'conclusion', 'references'
            ]
            
            sections = [s.strip() for s in config.pre_filter.split(',')]
            invalid_sections = [s for s in sections if s not in valid_sections]
            
            if invalid_sections:
                raise HTTPException(
                    400,
                    f"Invalid sections: {', '.join(invalid_sections)}. "
                    f"Valid sections: {', '.join(valid_sections)}"
                )
            
            if len(sections) == 0:
                raise HTTPException(
                    400,
                    "Pre-filter cannot be empty list. Use empty string for full paper."
                )
        
        cmd.extend(["--pre-filter", config.pre_filter])
        
        logger.info(f"Job {job_id} pre-filter: {config.pre_filter or 'full paper'}")
    
    # ... rest of command building ...
    
    # Store pre-filter in metadata
    job_metadata = load_job_metadata(job_id)
    job_metadata["pre_filter"] = config.pre_filter
    job_metadata["pre_filter_mode"] = (
        "default" if config.pre_filter is None else
        "full" if config.pre_filter == "" else
        "custom"
    )
    save_job_metadata(job_id, job_metadata)
    
    # Execute pipeline
    asyncio.create_task(execute_pipeline_async(job_id, cmd))
    
    return {
        "status": "started",
        "job_id": job_id,
        "pre_filter": config.pre_filter,
        "pre_filter_mode": job_metadata["pre_filter_mode"],
        "command": " ".join(cmd)
    }


@app.get(
    "/api/prefilter/recommendations",
    tags=["Pre-Filter"],
    summary="Get pre-filter recommendations"
)
async def get_prefilter_recommendations(
    paper_count: int = Query(..., description="Number of papers to analyze"),
    review_type: str = Query("general", description="Type of review: general, methodology, survey")
):
    """
    Get recommended pre-filter configuration based on review characteristics.
    
    Returns optimal section selection for speed/cost balance.
    """
    recommendations = {
        "general": {
            "small": ["title", "abstract", "introduction", "discussion"],
            "medium": ["title", "abstract", "introduction"],
            "large": ["abstract"]
        },
        "methodology": {
            "small": ["abstract", "methods", "results"],
            "medium": ["abstract", "methods"],
            "large": ["abstract"]
        },
        "survey": {
            "small": ["title", "abstract", "introduction", "methods", "results", "discussion"],
            "medium": ["title", "abstract", "introduction", "discussion"],
            "large": ["title", "abstract", "introduction"]
        }
    }
    
    # Determine dataset size
    if paper_count < 20:
        size = "small"
    elif paper_count < 100:
        size = "medium"
    else:
        size = "large"
    
    sections = recommendations.get(review_type, recommendations["general"])[size]
    
    return {
        "recommended_sections": sections,
        "section_string": ",".join(sections),
        "paper_count": paper_count,
        "review_type": review_type,
        "dataset_size": size,
        "rationale": f"For {review_type} reviews with {size} datasets ({paper_count} papers), "
                    f"analyzing {len(sections)} sections balances coverage and efficiency."
    }
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Three mode buttons: Default, Custom, Full Paper
- [ ] Default mode uses pipeline default (title+abstract+intro)
- [ ] Custom mode shows 8 section checkboxes
- [ ] Full paper mode analyzes all sections (no pre-filter)
- [ ] Selected sections preview updates live
- [ ] Pre-filter config passes to CLI (`--pre-filter`)
- [ ] Empty selection prevented (validation error)

### User Experience
- [ ] Mode selection clear and intuitive
- [ ] Section checkboxes grouped logically
- [ ] Impact preview shows section count, speed, cost
- [ ] Recommendations helpful and context-aware
- [ ] Quick presets (4) apply common configurations instantly
- [ ] Selected sections highlighted visually

### Validation
- [ ] Invalid section names rejected
- [ ] Empty custom selection rejected
- [ ] Default mode sends no flag (uses pipeline default)
- [ ] Full mode sends empty string `--pre-filter ""`
- [ ] Custom mode sends comma-separated list

### CLI Parity
- [ ] Default → no flag (100% parity)
- [ ] Custom → `--pre-filter section1,section2` (100% parity)
- [ ] Full → `--pre-filter ""` (100% parity)
- [ ] Same section names as CLI

### Impact Preview
- [ ] Section count accurate
- [ ] Speed estimate logical (fewer sections = faster)
- [ ] Cost estimate logical (fewer sections = cheaper)
- [ ] Recommendations adapt to selection

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_prefilter_config.py

def test_default_prefilter():
    """Test default mode sends no pre-filter flag."""
    config = {"pre_filter": None}
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    command = response.json()["command"]
    assert "--pre-filter" not in command

def test_full_paper_prefilter():
    """Test full paper mode sends empty string."""
    config = {"pre_filter": ""}
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    command = response.json()["command"]
    assert '--pre-filter ""' in command or "--pre-filter ''" in command

def test_custom_prefilter():
    """Test custom sections sent correctly."""
    config = {"pre_filter": "abstract,methods,results"}
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    command = response.json()["command"]
    assert "--pre-filter abstract,methods,results" in command

def test_invalid_sections_rejected():
    """Test invalid section names rejected."""
    config = {"pre_filter": "abstract,invalid_section,methods"}
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json=config,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 400
    assert "Invalid sections" in response.json()["detail"]

def test_prefilter_recommendations():
    """Test recommendation endpoint."""
    response = client.get("/api/prefilter/recommendations",
                         params={"paper_count": 50, "review_type": "general"})
    
    assert response.status_code == 200
    data = response.json()
    assert "recommended_sections" in data
    assert len(data["recommended_sections"]) > 0
```

### Integration Tests

```python
def test_e2e_custom_prefilter():
    """End-to-end: custom pre-filter → job runs → metadata saved."""
    # 1. Upload files
    job_id = upload_test_files()
    
    # 2. Start with custom pre-filter
    config = {"pre_filter": "abstract,introduction"}
    client.post(f"/api/jobs/{job_id}/start", json=config)
    
    # 3. Wait for completion
    wait_for_job_completion(job_id)
    
    # 4. Verify metadata
    metadata = load_job_metadata(job_id)
    assert metadata["pre_filter"] == "abstract,introduction"
    assert metadata["pre_filter_mode"] == "custom"
```

### Manual Testing Checklist

- [ ] Select Default → custom panel hidden
- [ ] Select Custom → checkboxes appear
- [ ] Check/uncheck sections → preview updates
- [ ] Select Full Paper → panel hidden, impact shows 8 sections
- [ ] Click preset → checkboxes update correctly
- [ ] Impact preview shows reasonable estimates
- [ ] Start job with custom sections → runs successfully
- [ ] Recommendations endpoint returns logical suggestions

---

## 📚 Documentation Updates

### User Guide

```markdown
## Pre-Filter Configuration

Control which paper sections to analyze for gap extraction. Analyzing fewer sections increases speed and reduces cost.

### Modes

**Default (Recommended):**
- Analyzes: Title, Abstract, Introduction
- Best for: Most literature reviews
- Speed: Fast ⚡
- Cost: Low 💰

**Custom:**
- Choose specific sections from 8 options:
  - Title, Abstract, Introduction, Methods
  - Results, Discussion, Conclusion, References
- Best for: Specialized reviews (e.g., methods-only for methodology surveys)
- Speed/Cost: Depends on selection

**Full Paper:**
- Analyzes all sections
- Best for: Detailed reviews of small datasets (<20 papers)
- Speed: Slow 🐌
- Cost: High 💰💰💰💰

### Quick Presets

- **Default:** Title + Abstract + Introduction
- **Abstract Only:** Fastest, cheapest (good for initial screening)
- **Methods Focus:** Abstract + Methods + Results (methodology reviews)
- **Comprehensive:** All except references (thorough analysis)

### Tips

- **Start conservative:** Use Default, expand only if needed
- **Large datasets (100+):** Abstract only to reduce cost
- **Small datasets (<20):** Comprehensive or Full Paper OK
- **Methods review:** Use Methods Focus preset
- **References:** Rarely useful for gap analysis

### Impact Estimates

The UI shows estimated impact of your selection:
- **Section Count:** Number of sections analyzed per paper
- **Speed:** Relative analysis time (more sections = slower)
- **Cost:** Relative API costs (more sections = more expensive)
- **Recommendation:** Context-aware guidance

### CLI Equivalent

- Default: `(no flag)`
- Custom: `--pre-filter abstract,methods`
- Full: `--pre-filter ""`
```

---

## 🚀 Deployment Checklist

- [ ] Pre-filter UI card implemented in Advanced Options
- [ ] Three mode buttons functional
- [ ] 8 section checkboxes with descriptions
- [ ] Selected sections preview updating live
- [ ] Impact preview showing count/speed/cost
- [ ] Recommendations updating dynamically
- [ ] 4 quick presets working
- [ ] Job start modified to accept pre_filter
- [ ] Section validation working
- [ ] Recommendations endpoint deployed
- [ ] Unit tests passing (5+ tests, 90% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Deployed to staging
- [ ] Manual testing completed
- [ ] User acceptance testing passed
- [ ] Deployed to production

---

## 📊 Success Metrics

**After Deployment:**
- Pre-filter configuration functional (100%)
- Dashboard parity increases by 1% (pre-filter control)
- Users can optimize for speed/cost
- Default mode maintains current behavior

**Monitoring:**
- Track % of users using custom pre-filter
- Track most common custom configurations
- Track correlation between sections and analysis time/cost
- Collect user feedback on presets

---

**Task Card Version:** 1.0  
**Created:** November 22, 2025  
**Estimated Effort:** 6-8 hours  
**Priority:** 🟠 HIGH  
**Dependency:** Requires PARITY-W1-2 (Advanced Options Panel)
