# PARITY-W3-4: Experimental Features Toggle

**Priority:** 🟡 **MEDIUM**  
**Effort:** 4-6 hours  
**Wave:** 3 (Enhancement Features)  
**Dependencies:** PARITY-W1-2 (Advanced Options Panel)

---

## 📋 Problem Statement

**Current State:**  
Dashboard has no way to enable experimental features currently in development. Users cannot test beta functionality, new models, or experimental analysis modes available in CLI.

**CLI Capability:**
```bash
# Enable experimental features
python pipeline_orchestrator.py --experimental

# Activates:
# - Beta models (GPT-4-turbo, Claude-3.5-Opus)
# - Experimental analysis modes (consensus, triangulation)
# - New caching strategies
# - Prototype visualizations
# - Unstable features under development
```

**User Problems:**
- Cannot access beta features for testing
- Cannot help validate experimental functionality
- Cannot use cutting-edge models before stable release
- No way to provide feedback on new features
- Miss out on performance improvements in testing

**Gap:** No experimental features toggle in Dashboard.

---

## 🎯 Objective

Add experimental features toggle matching CLI's `--experimental` flag, allowing users to opt-in to beta functionality with appropriate warnings and disclaimers.

---

## 📐 Design

### UI Components

**Location:** Advanced Options Panel in `webdashboard/templates/index.html`

**Experimental Features Toggle:**

```html
<!-- Experimental Features (in Advanced Options Panel) -->
<div class="card mb-3 border-danger">
    <div class="card-header bg-danger bg-opacity-10">
        <h6 class="mb-0">🧪 Experimental Features</h6>
    </div>
    <div class="card-body">
        
        <!-- Main Toggle -->
        <div class="form-check form-switch mb-3">
            <input class="form-check-input" type="checkbox" 
                   id="enableExperimental" onchange="toggleExperimental()">
            <label class="form-check-label" for="enableExperimental">
                <strong>Enable Experimental Features (Beta)</strong>
                <span class="badge bg-danger">CLI: --experimental</span>
            </label>
        </div>
        
        <!-- Warning (Always Visible) -->
        <div class="alert alert-warning">
            <h6>⚠️ Experimental Features Warning</h6>
            <p class="mb-2">
                Experimental features are <strong>unstable</strong> and <strong>under active development</strong>. 
                They may:
            </p>
            <ul class="mb-2">
                <li>Produce incorrect or incomplete results</li>
                <li>Change behavior without notice</li>
                <li>Consume more resources (time/cost)</li>
                <li>Fail unexpectedly</li>
                <li>Be removed in future versions</li>
            </ul>
            <p class="mb-0">
                <strong>Only enable if you understand the risks and want to help test beta functionality.</strong>
            </p>
        </div>
        
        <!-- Feature List (Collapsed by Default) -->
        <div id="experimentalFeaturesPanel" style="display: none;">
            
            <hr>
            
            <h6 class="mb-3">Available Experimental Features:</h6>
            
            <!-- Beta Models -->
            <div class="card mb-3 border-secondary">
                <div class="card-header bg-light">
                    <div class="form-check mb-0">
                        <input class="form-check-input experimental-feature" type="checkbox" 
                               id="expBetaModels" value="beta_models" disabled>
                        <label class="form-check-label" for="expBetaModels">
                            <strong>Beta Models</strong>
                        </label>
                    </div>
                </div>
                <div class="card-body">
                    <p class="small mb-2">
                        Access to latest unreleased models:
                    </p>
                    <ul class="small mb-0">
                        <li><strong>GPT-4-Turbo:</strong> Faster GPT-4 with 128k context</li>
                        <li><strong>Claude-3.5-Opus:</strong> Most capable Claude model</li>
                        <li><strong>Gemini-Pro-1.5:</strong> Google's latest multimodal model</li>
                    </ul>
                    <div class="alert alert-info mt-2 mb-0 small">
                        <strong>Note:</strong> Beta models may have higher costs and rate limits.
                    </div>
                </div>
            </div>
            
            <!-- Advanced Analysis Modes -->
            <div class="card mb-3 border-secondary">
                <div class="card-header bg-light">
                    <div class="form-check mb-0">
                        <input class="form-check-input experimental-feature" type="checkbox" 
                               id="expAdvancedModes" value="advanced_modes" disabled>
                        <label class="form-check-label" for="expAdvancedModes">
                            <strong>Advanced Analysis Modes</strong>
                        </label>
                    </div>
                </div>
                <div class="card-body">
                    <p class="small mb-2">
                        Experimental analysis techniques:
                    </p>
                    <ul class="small mb-0">
                        <li><strong>Consensus Mode:</strong> Multi-model gap extraction with voting</li>
                        <li><strong>Triangulation:</strong> Cross-validate findings across models</li>
                        <li><strong>Genealogy Tracking:</strong> Trace evidence provenance</li>
                    </ul>
                    <div class="alert alert-warning mt-2 mb-0 small">
                        <strong>Warning:</strong> These modes significantly increase API calls (3-5x) and cost.
                    </div>
                </div>
            </div>
            
            <!-- Smart Caching -->
            <div class="card mb-3 border-secondary">
                <div class="card-header bg-light">
                    <div class="form-check mb-0">
                        <input class="form-check-input experimental-feature" type="checkbox" 
                               id="expSmartCache" value="smart_cache" disabled>
                        <label class="form-check-label" for="expSmartCache">
                            <strong>Smart Caching (Beta)</strong>
                        </label>
                    </div>
                </div>
                <div class="card-body">
                    <p class="small mb-2">
                        Intelligent cache with semantic similarity matching:
                    </p>
                    <ul class="small mb-0">
                        <li>Reuse results for semantically similar papers</li>
                        <li>Adaptive cache expiration based on model updates</li>
                        <li>Cross-job cache sharing (privacy-aware)</li>
                    </ul>
                    <div class="alert alert-success mt-2 mb-0 small">
                        <strong>Benefit:</strong> Can reduce costs by 40-60% on similar datasets.
                    </div>
                </div>
            </div>
            
            <!-- Prototype Visualizations -->
            <div class="card mb-3 border-secondary">
                <div class="card-header bg-light">
                    <div class="form-check mb-0">
                        <input class="form-check-input experimental-feature" type="checkbox" 
                               id="expPrototypeViz" value="prototype_viz" disabled>
                        <label class="form-check-label" for="expPrototypeViz">
                            <strong>Prototype Visualizations</strong>
                        </label>
                    </div>
                </div>
                <div class="card-body">
                    <p class="small mb-2">
                        Experimental interactive visualizations:
                    </p>
                    <ul class="small mb-0">
                        <li><strong>3D Gap Network:</strong> Interactive network graph of gap relationships</li>
                        <li><strong>Timeline View:</strong> Temporal evolution of research gaps</li>
                        <li><strong>Evidence Dashboard:</strong> Real-time evidence quality metrics</li>
                    </ul>
                    <div class="alert alert-info mt-2 mb-0 small">
                        <strong>Status:</strong> May have rendering issues or incomplete features.
                    </div>
                </div>
            </div>
            
            <!-- Feedback Banner -->
            <div class="alert alert-primary">
                <strong>🙏 Help Us Improve!</strong><br>
                Your feedback on experimental features is valuable. Report issues or suggestions to:
                <a href="mailto:feedback@example.com">feedback@example.com</a>
            </div>
            
        </div>
        
        <!-- Consent Checkbox (Required) -->
        <div id="experimentalConsent" style="display: none;" class="mt-3">
            <div class="form-check">
                <input class="form-check-input" type="checkbox" 
                       id="experimentalConsentCheckbox" required>
                <label class="form-check-label" for="experimentalConsentCheckbox">
                    <strong>I understand the risks and accept that experimental features may produce 
                    unreliable results or fail.</strong>
                </label>
            </div>
            <div class="form-text">
                You must accept these terms to use experimental features.
            </div>
        </div>
        
    </div>
</div>

<script>
// Toggle experimental features panel
function toggleExperimental() {
    const enabled = document.getElementById('enableExperimental').checked;
    
    document.getElementById('experimentalFeaturesPanel').style.display = 
        enabled ? 'block' : 'none';
    document.getElementById('experimentalConsent').style.display = 
        enabled ? 'block' : 'none';
    
    // Enable/disable individual feature checkboxes
    document.querySelectorAll('.experimental-feature').forEach(checkbox => {
        checkbox.disabled = !enabled;
        if (!enabled) {
            checkbox.checked = false;
        }
    });
}

// Validate experimental consent before job start
function validateExperimentalConsent() {
    const experimentalEnabled = document.getElementById('enableExperimental').checked;
    
    if (experimentalEnabled) {
        const consentGiven = document.getElementById('experimentalConsentCheckbox').checked;
        
        if (!consentGiven) {
            alert('You must accept the experimental features terms to proceed.');
            return false;
        }
    }
    
    return true;
}

// Get experimental configuration for job submission
function getExperimentalConfig() {
    const enabled = document.getElementById('enableExperimental').checked;
    
    if (!enabled) {
        return {
            experimental: false,
            features: []
        };
    }
    
    const features = [];
    document.querySelectorAll('.experimental-feature:checked').forEach(checkbox => {
        features.push(checkbox.value);
    });
    
    return {
        experimental: true,
        features: features,
        consent_given: document.getElementById('experimentalConsentCheckbox').checked
    };
}

// Add validation to start analysis function
const originalStartAnalysis = startAnalysis;
startAnalysis = function() {
    if (!validateExperimentalConsent()) {
        return;
    }
    originalStartAnalysis();
};
</script>

<style>
.card.border-danger {
    border-width: 2px;
}

.experimental-feature:checked ~ label {
    color: #dc3545;
    font-weight: 600;
}
</style>
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**Experimental Features Support:**

```python
class ExperimentalConfig(BaseModel):
    """Experimental features configuration."""
    experimental: bool = False
    features: List[str] = []
    consent_given: bool = False


class JobConfig(BaseModel):
    """Job configuration with experimental options."""
    mode: str = "baseline"
    # ... other options ...
    
    # Experimental features
    experimental: Optional[ExperimentalConfig] = None


@app.post("/api/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    config: JobConfig,
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Start job with optional experimental features."""
    verify_api_key(api_key)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Validate experimental consent
    if config.experimental and config.experimental.experimental:
        if not config.experimental.consent_given:
            raise HTTPException(
                400,
                "Experimental features require explicit consent acceptance"
            )
    
    # Build CLI command
    cmd = ["python", "pipeline_orchestrator.py", "--batch-mode"]
    
    # Add experimental flag
    if config.experimental and config.experimental.experimental:
        cmd.append("--experimental")
        
        logger.warning(
            f"Job {job_id} using EXPERIMENTAL features: {config.experimental.features}"
        )
        
        # Log enabled features
        if config.experimental.features:
            # Note: CLI --experimental flag enables all experimental features
            # Individual feature selection may require additional flags in future
            logger.info(f"Job {job_id} experimental features: {config.experimental.features}")
    
    # ... rest of command building ...
    
    # Store experimental metadata
    job_metadata = load_job_metadata(job_id)
    job_metadata["experimental"] = config.experimental.experimental if config.experimental else False
    job_metadata["experimental_features"] = config.experimental.features if config.experimental else []
    job_metadata["experimental_consent"] = config.experimental.consent_given if config.experimental else False
    save_job_metadata(job_id, job_metadata)
    
    # Execute pipeline
    asyncio.create_task(execute_pipeline_async(job_id, cmd))
    
    return {
        "status": "started",
        "job_id": job_id,
        "experimental": job_metadata["experimental"],
        "experimental_features": job_metadata["experimental_features"],
        "command": " ".join(cmd)
    }


@app.get(
    "/api/experimental/features",
    tags=["Experimental"],
    summary="Get available experimental features"
)
async def get_experimental_features(
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Get list of available experimental features with descriptions.
    
    Returns current experimental features, their status, and warnings.
    """
    verify_api_key(api_key)
    
    # This data could come from a config file or database
    features = [
        {
            "id": "beta_models",
            "name": "Beta Models",
            "description": "Access to latest unreleased language models",
            "status": "active",
            "risk_level": "medium",
            "cost_impact": "high",
            "models": ["gpt-4-turbo", "claude-3-5-opus", "gemini-pro-1.5"],
            "warning": "Beta models may have higher costs and rate limits"
        },
        {
            "id": "advanced_modes",
            "name": "Advanced Analysis Modes",
            "description": "Experimental multi-model analysis techniques",
            "status": "active",
            "risk_level": "high",
            "cost_impact": "very_high",
            "modes": ["consensus", "triangulation", "genealogy"],
            "warning": "These modes significantly increase API calls (3-5x) and cost"
        },
        {
            "id": "smart_cache",
            "name": "Smart Caching (Beta)",
            "description": "Intelligent semantic similarity-based caching",
            "status": "active",
            "risk_level": "low",
            "cost_impact": "negative",  # Reduces cost
            "warning": "May reuse results for semantically similar but different papers"
        },
        {
            "id": "prototype_viz",
            "name": "Prototype Visualizations",
            "description": "Experimental interactive visualization modes",
            "status": "beta",
            "risk_level": "low",
            "cost_impact": "none",
            "warning": "May have rendering issues or incomplete features"
        }
    ]
    
    return {
        "features": features,
        "total_count": len(features),
        "disclaimer": "Experimental features are unstable and may change without notice. "
                     "Use at your own risk. Feedback appreciated."
    }
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] Experimental features toggle checkbox functional
- [ ] Warning always visible (cannot be dismissed)
- [ ] Feature list expands when toggle enabled
- [ ] 4 experimental features described
- [ ] Individual feature checkboxes (future extensibility)
- [ ] Consent checkbox required before job start
- [ ] Experimental flag passed to CLI (`--experimental`)
- [ ] Metadata stored (features enabled, consent given)

### User Experience
- [ ] Warning prominent and clear
- [ ] Risks explicitly stated
- [ ] Feature descriptions informative
- [ ] Consent requirement clear
- [ ] Cannot start without consent (validation error)
- [ ] Feedback email/link provided

### Safety
- [ ] Cannot enable without seeing warning
- [ ] Consent cannot be bypassed
- [ ] Experimental status logged
- [ ] Features clearly labeled as beta/unstable
- [ ] Cost/risk impact communicated

### CLI Parity
- [ ] Experimental toggle → `--experimental` (100% parity)
- [ ] Same features available as CLI
- [ ] Same warnings as CLI documentation

### Edge Cases
- [ ] Toggle on → toggle off → consent reset
- [ ] Start without consent → validation error
- [ ] Experimental features in job metadata → visible in job detail
- [ ] Failed experimental job → clear indication in logs

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_experimental_features.py

def test_start_with_experimental():
    """Test starting job with experimental features."""
    job_id = create_test_job()
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json={
                              "experimental": {
                                  "experimental": True,
                                  "features": ["beta_models"],
                                  "consent_given": True
                              }
                          },
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["experimental"] is True
    assert "--experimental" in data["command"]

def test_experimental_without_consent():
    """Test experimental features without consent rejected."""
    job_id = create_test_job()
    
    response = client.post(f"/api/jobs/{job_id}/start",
                          json={
                              "experimental": {
                                  "experimental": True,
                                  "features": ["beta_models"],
                                  "consent_given": False
                              }
                          },
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 400
    assert "consent" in response.json()["detail"].lower()

def test_get_experimental_features():
    """Test fetching available experimental features."""
    response = client.get("/api/experimental/features",
                         headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert "features" in data
    assert len(data["features"]) >= 4

def test_experimental_metadata_stored():
    """Test experimental settings stored in metadata."""
    job_id = create_test_job()
    
    client.post(f"/api/jobs/{job_id}/start",
               json={
                   "experimental": {
                       "experimental": True,
                       "features": ["smart_cache"],
                       "consent_given": True
                   }
               })
    
    metadata = load_job_metadata(job_id)
    assert metadata["experimental"] is True
    assert "smart_cache" in metadata["experimental_features"]
```

### Integration Tests

```python
def test_e2e_experimental_workflow():
    """End-to-end: enable experimental → consent → run → complete."""
    # 1. Upload files
    job_id = upload_test_files()
    
    # 2. Start with experimental features
    response = client.post(f"/api/jobs/{job_id}/start",
                          json={
                              "experimental": {
                                  "experimental": True,
                                  "features": ["beta_models"],
                                  "consent_given": True
                              }
                          })
    
    assert response.json()["experimental"] is True
    
    # 3. Wait for completion
    wait_for_job_completion(job_id)
    
    # 4. Verify experimental features used
    metadata = load_job_metadata(job_id)
    assert metadata["experimental"] is True
```

### Manual Testing Checklist

- [ ] Enable experimental → panel expands, warning shown
- [ ] Disable experimental → panel collapses
- [ ] Check individual features → checkboxes work
- [ ] Start without consent → error shown
- [ ] Check consent → can start
- [ ] Job metadata → experimental=true recorded
- [ ] Feature descriptions → clear and informative
- [ ] Warnings → appropriate risk communication

---

## 📚 Documentation Updates

### User Guide

```markdown
## Experimental Features

Experimental features are **unstable beta functionality** under active development. Use at your own risk.

### Enabling Experimental Features

1. Expand **Advanced Options**
2. Check **Enable Experimental Features (Beta)**
3. Review warning carefully
4. Explore available features (expand to see details)
5. Optionally select specific features (currently all enabled together)
6. Check consent checkbox: "I understand the risks..."
7. Proceed with analysis

### Available Experimental Features

**Beta Models:**
- GPT-4-Turbo, Claude-3.5-Opus, Gemini-Pro-1.5
- Higher costs, may have rate limits
- Cutting-edge performance

**Advanced Analysis Modes:**
- Consensus: Multi-model gap extraction with voting
- Triangulation: Cross-validate findings
- Genealogy: Evidence provenance tracking
- **Warning:** 3-5x API calls and cost

**Smart Caching (Beta):**
- Semantic similarity matching
- Adaptive expiration
- Cross-job sharing (privacy-aware)
- **Benefit:** 40-60% cost reduction

**Prototype Visualizations:**
- 3D Gap Network
- Timeline View
- Evidence Dashboard
- **Note:** May have rendering issues

### Risks

- **Incorrect Results:** Experimental algorithms may produce errors
- **Higher Costs:** Beta models and advanced modes expensive
- **Failures:** Features may crash or timeout
- **Changes:** Behavior may change without notice
- **Removal:** Features may be discontinued

### When to Use

- Testing new functionality
- Providing feedback to developers
- Accessing latest models
- Optimizing costs with smart cache

### Feedback

Help improve experimental features by reporting:
- Bugs or errors
- Unexpected behavior
- Performance issues
- Feature requests

Contact: feedback@example.com

### CLI Equivalent

Experimental Features: `--experimental`
