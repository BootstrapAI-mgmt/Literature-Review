# PARITY-W2-1: Config File Upload

**Priority:** 🟠 **HIGH**  
**Effort:** 8-10 hours  
**Wave:** 2 (High Priority Features)  
**Dependencies:** PARITY-W1-2 (Advanced Options Panel)

---

## 📋 Problem Statement

**Current State:**  
Dashboard uses hardcoded `pipeline_config.json` with no ability to customize. Users cannot override default settings for retry policies, model selection, pre-filtering, or ROI optimization.

**CLI Capability:**
```bash
python pipeline_orchestrator.py --config custom_config.json
```

**Use Cases:**
- Testing with different models (gemini-1.5-pro vs gemini-2.0-flash)
- Custom retry policies for unreliable networks
- Different pre-filtering thresholds per project
- Budget-specific ROI optimizer settings
- A/B testing different configurations

**Gap:** Users cannot customize pipeline configuration in Dashboard.

---

## 🎯 Objective

Add configuration file upload capability to Dashboard, allowing users to override default `pipeline_config.json` with custom settings, matching CLI's `--config` flag.

---

## 📐 Design

### UI Components

**Location:** Advanced Options Panel in `webdashboard/templates/index.html`

**Config File Upload Section:**

```html
<!-- Config File Upload (in Advanced Options Panel) -->
<div class="mb-3">
    <label for="configFileUpload" class="form-label">
        <strong>Custom Configuration File</strong>
        <span class="badge bg-secondary">CLI: --config</span>
    </label>
    
    <input class="form-control" type="file" 
           id="configFileUpload" 
           accept=".json"
           onchange="handleConfigUpload(this)">
    
    <div class="form-text">
        Upload custom pipeline_config.json to override defaults.
        <a href="/api/config/template" download>Download template</a>
    </div>
    
    <!-- Config Preview -->
    <div id="configPreview" style="display: none;" class="mt-3">
        <div class="card">
            <div class="card-header bg-light">
                <h6 class="mb-0">
                    📄 Configuration Preview
                    <button type="button" class="btn btn-sm btn-outline-danger float-end"
                            onclick="clearConfigUpload()">
                        ✕ Remove
                    </button>
                </h6>
            </div>
            <div class="card-body">
                <!-- Validation Status -->
                <div id="configValidation" class="alert" role="alert">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Validating...</span>
                    </div>
                    Validating configuration...
                </div>
                
                <!-- Config Details -->
                <div id="configDetails" style="display: none;">
                    <dl class="row mb-0">
                        <dt class="col-sm-4">Version:</dt>
                        <dd class="col-sm-8" id="configVersion">-</dd>
                        
                        <dt class="col-sm-4">Models:</dt>
                        <dd class="col-sm-8" id="configModels">-</dd>
                        
                        <dt class="col-sm-4">Pre-filtering:</dt>
                        <dd class="col-sm-8" id="configPrefilter">-</dd>
                        
                        <dt class="col-sm-4">ROI Optimizer:</dt>
                        <dd class="col-sm-8" id="configROI">-</dd>
                        
                        <dt class="col-sm-4">Overrides:</dt>
                        <dd class="col-sm-8" id="configOverrides">-</dd>
                    </dl>
                    
                    <!-- View Full Config -->
                    <button type="button" class="btn btn-sm btn-outline-primary mt-2"
                            data-bs-toggle="collapse" data-bs-target="#fullConfigView">
                        👁️ View Full Configuration
                    </button>
                    
                    <div id="fullConfigView" class="collapse mt-2">
                        <pre id="fullConfigJSON" class="bg-light p-3 rounded" 
                             style="max-height: 300px; overflow-y: auto; font-size: 0.85em;"></pre>
                    </div>
                </div>
                
                <!-- Validation Errors -->
                <div id="configErrors" style="display: none;" class="alert alert-danger mt-3">
                    <strong>⚠️ Validation Errors:</strong>
                    <ul id="configErrorList" class="mb-0 mt-2"></ul>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// Handle config file upload
async function handleConfigUpload(input) {
    const file = input.files[0];
    if (!file) return;
    
    // Show preview section
    document.getElementById('configPreview').style.display = 'block';
    document.getElementById('configValidation').style.display = 'block';
    document.getElementById('configDetails').style.display = 'none';
    document.getElementById('configErrors').style.display = 'none';
    
    // Read file
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const configText = e.target.result;
            const configJSON = JSON.parse(configText);
            
            // Validate config
            await validateConfig(configJSON);
            
        } catch (error) {
            showConfigError(['Invalid JSON format: ' + error.message]);
        }
    };
    reader.readAsText(file);
}

// Validate configuration via API
async function validateConfig(configJSON) {
    try {
        const response = await fetch('/api/config/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            },
            body: JSON.stringify(configJSON)
        });
        
        const result = await response.json();
        
        if (result.valid) {
            showConfigDetails(configJSON, result);
        } else {
            showConfigError(result.errors);
        }
        
    } catch (error) {
        showConfigError(['Validation failed: ' + error.message]);
    }
}

// Display config details
function showConfigDetails(configJSON, validation) {
    document.getElementById('configValidation').style.display = 'none';
    document.getElementById('configDetails').style.display = 'block';
    
    // Populate details
    document.getElementById('configVersion').textContent = 
        configJSON.version || 'Unknown';
    
    document.getElementById('configModels').innerHTML = 
        formatModels(configJSON.models || {});
    
    document.getElementById('configPrefilter').innerHTML = 
        formatPrefilter(configJSON.pre_filtering || {});
    
    document.getElementById('configROI').innerHTML = 
        formatROI(configJSON.roi_optimizer || {});
    
    document.getElementById('configOverrides').innerHTML = 
        `<span class="badge bg-info">${validation.overrides_count || 0} settings</span>`;
    
    // Show full JSON
    document.getElementById('fullConfigJSON').textContent = 
        JSON.stringify(configJSON, null, 2);
}

// Format helpers
function formatModels(models) {
    const modelList = [];
    if (models.gap_extraction) modelList.push(`Gap: ${models.gap_extraction}`);
    if (models.relevance) modelList.push(`Relevance: ${models.relevance}`);
    if (models.deep_review) modelList.push(`Review: ${models.deep_review}`);
    return modelList.join('<br>') || '<em>Default models</em>';
}

function formatPrefilter(prefilter) {
    if (!prefilter.enabled) return '<span class="badge bg-secondary">Disabled</span>';
    return `<span class="badge bg-success">Enabled</span> (${(prefilter.threshold || 0.5) * 100}%)`;
}

function formatROI(roi) {
    if (!roi.enabled) return '<span class="badge bg-secondary">Disabled</span>';
    return `<span class="badge bg-success">Enabled</span> (target: ${roi.target_roi || 2.0}x)`;
}

// Show validation errors
function showConfigError(errors) {
    document.getElementById('configValidation').style.display = 'none';
    document.getElementById('configErrors').style.display = 'block';
    
    const errorList = document.getElementById('configErrorList');
    errorList.innerHTML = '';
    
    errors.forEach(error => {
        const li = document.createElement('li');
        li.textContent = error;
        errorList.appendChild(li);
    });
}

// Clear config upload
function clearConfigUpload() {
    document.getElementById('configFileUpload').value = '';
    document.getElementById('configPreview').style.display = 'none';
}

// Include config in job submission
function getConfigFile() {
    const input = document.getElementById('configFileUpload');
    return input.files[0] || null;
}
</script>
```

---

### Backend Implementation

**File:** `webdashboard/app.py`

**Configuration Validation Endpoint:**

```python
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional
import json
from pathlib import Path

class PipelineConfig(BaseModel):
    """Pipeline configuration schema matching pipeline_config.json."""
    version: str = Field(..., description="Config version")
    models: Dict[str, str] = Field(default_factory=dict)
    pre_filtering: Dict[str, Any] = Field(default_factory=dict)
    roi_optimizer: Dict[str, Any] = Field(default_factory=dict)
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    evidence_decay: Optional[Dict[str, Any]] = None
    
    @validator('version')
    def validate_version(cls, v):
        """Validate version format."""
        if not v or not isinstance(v, str):
            raise ValueError("Version must be a non-empty string")
        return v
    
    @validator('models')
    def validate_models(cls, v):
        """Validate model names."""
        valid_models = [
            'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash-exp',
            'gemini-exp-1206', 'claude-3-5-sonnet-20241022'
        ]
        
        for stage, model in v.items():
            if model not in valid_models:
                raise ValueError(
                    f"Invalid model '{model}' for stage '{stage}'. "
                    f"Must be one of: {', '.join(valid_models)}"
                )
        
        return v


@app.post(
    "/api/config/validate",
    tags=["Configuration"],
    summary="Validate custom pipeline configuration"
)
async def validate_config(
    config: Dict[str, Any],
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Validate uploaded pipeline configuration against schema.
    
    Returns validation result with details about overrides.
    """
    verify_api_key(api_key)
    
    try:
        # Validate against schema
        validated_config = PipelineConfig(**config)
        
        # Load default config for comparison
        default_config_path = BASE_DIR / "pipeline_config.json"
        with open(default_config_path) as f:
            default_config = json.load(f)
        
        # Find overrides
        overrides = find_config_overrides(config, default_config)
        
        return {
            "valid": True,
            "config": validated_config.dict(),
            "overrides": overrides,
            "overrides_count": len(overrides)
        }
        
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "config": None,
            "overrides": [],
            "overrides_count": 0
        }


def find_config_overrides(
    custom: Dict[str, Any],
    default: Dict[str, Any],
    path: str = ""
) -> list:
    """
    Find all configuration overrides recursively.
    
    Returns list of override descriptions.
    """
    overrides = []
    
    for key, value in custom.items():
        current_path = f"{path}.{key}" if path else key
        
        if key not in default:
            overrides.append(f"Added: {current_path} = {value}")
            
        elif isinstance(value, dict) and isinstance(default[key], dict):
            # Recurse for nested dicts
            overrides.extend(
                find_config_overrides(value, default[key], current_path)
            )
            
        elif value != default[key]:
            overrides.append(
                f"Changed: {current_path} from {default[key]} to {value}"
            )
    
    return overrides


@app.get(
    "/api/config/template",
    tags=["Configuration"],
    summary="Download default configuration template"
)
async def download_config_template(
    api_key: str = Header(None, alias="X-API-KEY")
):
    """
    Download default pipeline_config.json as template.
    """
    verify_api_key(api_key)
    
    config_path = BASE_DIR / "pipeline_config.json"
    
    return FileResponse(
        path=config_path,
        filename="pipeline_config_template.json",
        media_type="application/json"
    )
```

**Modified Job Start Endpoint:**

```python
@app.post("/api/jobs/{job_id}/start")
async def start_job(
    job_id: str,
    config: JobConfig,
    config_file: Optional[UploadFile] = File(None),
    api_key: str = Header(None, alias="X-API-KEY")
):
    """Start job with optional custom configuration."""
    verify_api_key(api_key)
    
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404, f"Job {job_id} not found")
    
    # Build CLI command
    cmd = ["python", "pipeline_orchestrator.py", "--batch-mode"]
    
    # Handle custom config file
    custom_config_path = None
    if config_file:
        # Save uploaded config
        custom_config_path = job_dir / "custom_config.json"
        
        with open(custom_config_path, "wb") as f:
            content = await config_file.read()
            f.write(content)
        
        # Validate saved config
        try:
            with open(custom_config_path) as f:
                config_data = json.load(f)
                PipelineConfig(**config_data)  # Validate
        except Exception as e:
            custom_config_path.unlink()  # Delete invalid file
            raise HTTPException(400, f"Invalid configuration: {str(e)}")
        
        # Add to command
        cmd.extend(["--config", str(custom_config_path)])
        
        logger.info(f"Job {job_id} using custom config: {custom_config_path}")
    
    # ... rest of command building (advanced options, mode, etc.) ...
    
    # Store config info in job metadata
    job_metadata = load_job_metadata(job_id)
    job_metadata["custom_config"] = str(custom_config_path) if custom_config_path else None
    job_metadata["config_uploaded"] = config_file is not None
    save_job_metadata(job_id, job_metadata)
    
    # Execute pipeline
    asyncio.create_task(execute_pipeline_async(job_id, cmd))
    
    return {
        "status": "started",
        "job_id": job_id,
        "custom_config": bool(custom_config_path),
        "command": " ".join(cmd)
    }
```

---

## ✅ Acceptance Criteria

### Functional Requirements
- [ ] File input accepts `.json` files only
- [ ] Uploaded config validated against schema
- [ ] Validation shows specific errors (line numbers, field names)
- [ ] Preview shows key config settings (models, pre-filter, ROI)
- [ ] "Download template" link provides default config
- [ ] Custom config saved to job directory
- [ ] Pipeline executed with `--config` flag
- [ ] Job metadata tracks config usage

### User Experience
- [ ] Upload triggers automatic validation (< 2 seconds)
- [ ] Validation status clear (spinner → success/error)
- [ ] Preview shows overrides vs defaults
- [ ] Full JSON viewable in collapsible section
- [ ] Easy to remove uploaded config and revert to default
- [ ] Error messages actionable (tell user what to fix)

### Validation Rules
- [ ] Version field required
- [ ] Model names validated against allowed list
- [ ] Pre-filter threshold in range [0.0, 1.0]
- [ ] ROI target > 0
- [ ] Retry policy: max_retries ≥ 0
- [ ] No unknown/unsupported fields (strict mode)

### CLI Parity
- [ ] `--config X` → Config file upload (100%)
- [ ] Same validation as CLI
- [ ] Same config merging behavior (custom overrides default)

### Edge Cases
- [ ] Empty file → clear error
- [ ] Invalid JSON → syntax error highlighted
- [ ] Partial config (only overrides) → merge with defaults
- [ ] Huge file (>1MB) → reject with size limit message
- [ ] Concurrent uploads → handle race conditions

---

## 🧪 Testing Plan

### Unit Tests

```python
# test_config_upload.py

def test_validate_valid_config():
    """Test validation of valid configuration."""
    valid_config = {
        "version": "2.0.0",
        "models": {
            "gap_extraction": "gemini-1.5-pro"
        },
        "pre_filtering": {
            "enabled": True,
            "threshold": 0.6
        }
    }
    
    response = client.post("/api/config/validate",
                          json=valid_config,
                          headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert "overrides" in data

def test_validate_invalid_model():
    """Test validation rejects invalid model names."""
    invalid_config = {
        "version": "2.0.0",
        "models": {
            "gap_extraction": "gpt-4"  # Invalid
        }
    }
    
    response = client.post("/api/config/validate",
                          json=invalid_config,
                          headers={"X-API-KEY": "test-key"})
    
    data = response.json()
    assert data["valid"] is False
    assert any("Invalid model" in err for err in data["errors"])

def test_download_config_template():
    """Test downloading default config template."""
    response = client.get("/api/config/template",
                         headers={"X-API-KEY": "test-key"})
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    # Verify it's valid JSON
    config = json.loads(response.content)
    assert "version" in config
    assert "models" in config

def test_job_start_with_custom_config():
    """Test starting job with custom configuration."""
    # Create test config
    custom_config = {
        "version": "2.0.0",
        "models": {"gap_extraction": "gemini-2.0-flash-exp"}
    }
    config_file = BytesIO(json.dumps(custom_config).encode())
    
    response = client.post(
        f"/api/jobs/{job_id}/start",
        files={"config_file": ("config.json", config_file, "application/json")},
        headers={"X-API-KEY": "test-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["custom_config"] is True
    assert "--config" in data["command"]

def test_invalid_config_rejected():
    """Test that invalid config file is rejected."""
    invalid_config = {"invalid": "structure"}
    config_file = BytesIO(json.dumps(invalid_config).encode())
    
    response = client.post(
        f"/api/jobs/{job_id}/start",
        files={"config_file": ("config.json", config_file, "application/json")},
        headers={"X-API-KEY": "test-key"}
    )
    
    assert response.status_code == 400
    assert "Invalid configuration" in response.json()["detail"]

def test_find_config_overrides():
    """Test override detection."""
    default = {
        "version": "1.0",
        "models": {"gap": "gemini-1.5-pro"},
        "pre_filtering": {"enabled": True}
    }
    
    custom = {
        "version": "2.0",
        "models": {"gap": "gemini-2.0-flash-exp"},
        "pre_filtering": {"enabled": True}
    }
    
    overrides = find_config_overrides(custom, default)
    
    assert len(overrides) == 2
    assert any("version" in o for o in overrides)
    assert any("models.gap" in o for o in overrides)
```

### Integration Tests

```python
def test_e2e_custom_config_workflow():
    """End-to-end: upload config → validate → start job → verify usage."""
    # 1. Create custom config
    custom_config = {
        "version": "2.0.0",
        "models": {
            "gap_extraction": "gemini-2.0-flash-exp",
            "relevance": "gemini-1.5-flash"
        },
        "pre_filtering": {
            "enabled": True,
            "threshold": 0.8
        }
    }
    
    # 2. Validate config
    validation = client.post("/api/config/validate", json=custom_config)
    assert validation.json()["valid"] is True
    
    # 3. Upload files and start job with config
    job_id = upload_test_files()
    
    config_file = BytesIO(json.dumps(custom_config).encode())
    start_response = client.post(
        f"/api/jobs/{job_id}/start",
        files={"config_file": ("config.json", config_file, "application/json")}
    )
    assert start_response.json()["custom_config"] is True
    
    # 4. Verify config saved to job directory
    saved_config_path = JOBS_DIR / job_id / "custom_config.json"
    assert saved_config_path.exists()
    
    with open(saved_config_path) as f:
        saved_config = json.load(f)
        assert saved_config == custom_config
    
    # 5. Wait for job completion
    wait_for_job_completion(job_id)
    
    # 6. Verify custom config was actually used
    # (check logs or output for model names)
    job_metadata = load_job_metadata(job_id)
    assert job_metadata["custom_config"] is not None
```

### Manual Testing Checklist

- [ ] Upload valid config → see preview with correct details
- [ ] Upload invalid JSON → see syntax error
- [ ] Upload config with invalid model → see validation error
- [ ] Download template → verify it's default config
- [ ] View full config → see complete JSON
- [ ] Remove config → preview disappears
- [ ] Start job with config → verify --config in command
- [ ] Start job without config → verify default used

---

## 📚 Documentation Updates

### User Guide

```markdown
## Custom Pipeline Configuration

Upload a custom `pipeline_config.json` to override default settings for models, pre-filtering, ROI optimization, and retry policies.

### How to Upload Config

1. Click **Advanced Options** to expand
2. Find **Custom Configuration File** section
3. Click **Choose File** and select your `.json` file
4. Dashboard automatically validates and shows preview
5. Review overrides (what changed from defaults)
6. Start analysis - custom config will be used

### Download Template

Click "Download template" to get the default `pipeline_config.json` as a starting point.

### Common Customizations

**Use Faster Models:**
```json
{
  "version": "2.0.0",
  "models": {
    "gap_extraction": "gemini-2.0-flash-exp",
    "relevance": "gemini-1.5-flash",
    "deep_review": "gemini-1.5-flash"
  }
}
```

**Stricter Pre-filtering:**
```json
{
  "version": "2.0.0",
  "pre_filtering": {
    "enabled": true,
    "threshold": 0.8
  }
}
```

**Aggressive Retries:**
```json
{
  "version": "2.0.0",
  "retry_policy": {
    "max_retries": 5,
    "initial_delay": 2.0,
    "max_delay": 120.0
  }
}
```

### Validation Errors

If config validation fails:
- Check JSON syntax (use JSONLint.com)
- Verify model names against allowed list
- Ensure thresholds in valid ranges (0.0-1.0)
- Match schema structure (see template)
```

---

## 🚀 Deployment Checklist

- [ ] Frontend config upload UI implemented
- [ ] JavaScript validation and preview working
- [ ] Backend `/api/config/validate` endpoint deployed
- [ ] Backend `/api/config/template` endpoint deployed
- [ ] Job start modified to accept config file
- [ ] Config schema validation comprehensive
- [ ] Override detection working correctly
- [ ] Unit tests passing (10+ tests, 90% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Template file accessible
- [ ] Code reviewed and approved
- [ ] Deployed to staging
- [ ] Manual testing completed
- [ ] User acceptance testing passed
- [ ] Deployed to production

---

## 📊 Success Metrics

**After Deployment:**
- Config upload feature functional (100%)
- Dashboard parity increases by 2% (config customization)
- Users can test different model combinations
- Reduced requests for "CLI-only" config changes

**Monitoring:**
- Track % of jobs using custom configs
- Track most common config overrides (inform defaults)
- Track validation errors (improve error messages)
- Collect user feedback on config UX

---

**Task Card Version:** 1.0  
**Created:** November 21, 2025  
**Estimated Effort:** 8-10 hours  
**Priority:** 🟠 HIGH  
**Dependency:** Requires PARITY-W1-2 (Advanced Options Panel)
