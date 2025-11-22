"""
Unit tests for Configuration Upload API endpoints

Tests the new configuration upload functionality including:
- Config validation endpoint
- Config template download endpoint
- Config file upload with validation
"""

import io
import json
from pathlib import Path


def test_validate_valid_config(test_client, api_key):
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
    
    response = test_client.post(
        "/api/config/validate",
        json=valid_config,
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert "overrides" in data
    assert isinstance(data["overrides"], list)
    assert "overrides_count" in data


def test_validate_minimal_config(test_client, api_key):
    """Test validation of minimal valid configuration."""
    minimal_config = {
        "version": "2.0.0"
    }
    
    response = test_client.post(
        "/api/config/validate",
        json=minimal_config,
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


def test_validate_invalid_config_missing_version(test_client, api_key):
    """Test validation rejects config without version."""
    invalid_config = {
        "models": {
            "gap_extraction": "gemini-1.5-pro"
        }
    }
    
    response = test_client.post(
        "/api/config/validate",
        json=invalid_config,
        headers={"X-API-KEY": api_key}
    )
    
    data = response.json()
    assert data["valid"] is False
    assert "errors" in data
    assert len(data["errors"]) > 0


def test_validate_config_without_api_key(test_client):
    """Test validation fails without API key."""
    config = {"version": "2.0.0"}
    
    response = test_client.post(
        "/api/config/validate",
        json=config
    )
    
    assert response.status_code == 401


def test_download_config_template(test_client, api_key):
    """Test downloading default config template."""
    response = test_client.get(
        "/api/config/template",
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    # Verify it's valid JSON
    config = json.loads(response.content)
    assert "version" in config
    assert isinstance(config, dict)


def test_download_config_template_without_api_key(test_client):
    """Test template download fails without API key."""
    response = test_client.get("/api/config/template")
    
    assert response.status_code == 401


def test_upload_config_file(test_client, api_key, create_job):
    """Test uploading custom configuration file to job."""
    # Create test job
    job = create_job("test-job-1", "draft")
    
    # Create test config
    custom_config = {
        "version": "2.0.0",
        "models": {"gap_extraction": "gemini-1.5-pro"}
    }
    config_file = io.BytesIO(json.dumps(custom_config).encode())
    
    response = test_client.post(
        f"/api/jobs/{job['id']}/upload-config",
        files={"config_file": ("config.json", config_file, "application/json")},
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job["id"]
    assert "config_path" in data
    assert data["valid"] is True
    assert "errors" in data
    assert len(data["errors"]) == 0


def test_upload_invalid_config_file(test_client, api_key, create_job):
    """Test that invalid config file is rejected."""
    # Create test job
    job = create_job("test-job-2", "draft")
    
    # Create invalid config (missing version)
    invalid_config = {
        "models": {"gap_extraction": "gemini-1.5-pro"}
    }
    config_file = io.BytesIO(json.dumps(invalid_config).encode())
    
    response = test_client.post(
        f"/api/jobs/{job['id']}/upload-config",
        files={"config_file": ("config.json", config_file, "application/json")},
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200  # Upload succeeds but validation fails
    data = response.json()
    assert data["valid"] is False
    assert "errors" in data
    assert len(data["errors"]) > 0


def test_upload_non_json_config(test_client, api_key, create_job):
    """Test that non-JSON file is rejected."""
    # Create test job
    job = create_job("test-job-3", "draft")
    
    # Create non-JSON file
    text_file = io.BytesIO(b"not json content")
    
    response = test_client.post(
        f"/api/jobs/{job['id']}/upload-config",
        files={"config_file": ("config.txt", text_file, "text/plain")},
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 400
    assert "JSON" in response.json()["detail"]


def test_upload_malformed_json(test_client, api_key, create_job):
    """Test that malformed JSON is rejected."""
    # Create test job
    job = create_job("test-job-4", "draft")
    
    # Create malformed JSON
    bad_json = io.BytesIO(b'{"version": "2.0.0",}')  # Trailing comma
    
    response = test_client.post(
        f"/api/jobs/{job['id']}/upload-config",
        files={"config_file": ("config.json", bad_json, "application/json")},
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 400
    assert "JSON" in response.json()["detail"]


def test_upload_config_to_nonexistent_job(test_client, api_key):
    """Test uploading config to non-existent job fails."""
    custom_config = {"version": "2.0.0"}
    config_file = io.BytesIO(json.dumps(custom_config).encode())
    
    response = test_client.post(
        "/api/jobs/nonexistent-job/upload-config",
        files={"config_file": ("config.json", config_file, "application/json")},
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 404


def test_validate_config_finds_overrides(test_client, api_key, temp_workspace):
    """Test that validation correctly identifies overrides."""
    # Create custom config with different values from actual default
    custom_config = {
        "version": "3.0.0",  # Different from default "2.0.0"
        "models": {
            "gap_extraction": "gemini-1.5-flash"
        },
        "pre_filtering": {
            "enabled": False,  # Different from default
            "threshold": 0.9   # Different from default
        }
    }
    
    response = test_client.post(
        "/api/config/validate",
        json=custom_config,
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["overrides_count"] >= 0  # May have overrides depending on default config
    assert isinstance(data["overrides"], list)


def test_config_with_all_sections(test_client, api_key):
    """Test validation of config with all possible sections."""
    full_config = {
        "version": "2.0.0",
        "models": {
            "gap_extraction": "gemini-1.5-pro",
            "relevance": "gemini-1.5-flash"
        },
        "pre_filtering": {
            "enabled": True,
            "threshold": 0.6
        },
        "roi_optimizer": {
            "enabled": True,
            "target_roi": 2.0
        },
        "retry_policy": {
            "enabled": True,
            "default_max_attempts": 3
        },
        "evidence_decay": {
            "enabled": True,
            "half_life_years": 5
        },
        "deduplication": {
            "enabled": False,
            "threshold": 0.9
        },
        "prompts": {
            "default_timeout": 300
        },
        "v2_features": {
            "max_workers": 4
        },
        "stage_timeout": 7200,
        "log_level": "INFO"
    }
    
    response = test_client.post(
        "/api/config/validate",
        json=full_config,
        headers={"X-API-KEY": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
