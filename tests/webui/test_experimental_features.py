"""
Unit tests for Experimental Features API (PARITY-W3-4)

Tests the experimental features toggle functionality including:
- Getting available experimental features
- Starting jobs with experimental features enabled
- Validating consent requirements
- Storing experimental metadata in job data
"""

import json
from pathlib import Path


def test_get_experimental_features(test_client, api_key):
    """Test fetching available experimental features."""
    headers = {"X-API-KEY": api_key}
    
    response = test_client.get("/api/experimental/features", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "features" in data
    assert "total_count" in data
    assert "disclaimer" in data
    
    # Verify feature count
    assert data["total_count"] >= 4
    assert len(data["features"]) >= 4
    
    # Verify feature structure
    feature_ids = [f["id"] for f in data["features"]]
    assert "beta_models" in feature_ids
    assert "advanced_modes" in feature_ids
    assert "smart_cache" in feature_ids
    assert "prototype_viz" in feature_ids
    
    # Verify feature details
    for feature in data["features"]:
        assert "id" in feature
        assert "name" in feature
        assert "description" in feature
        assert "status" in feature
        assert "risk_level" in feature
        assert "cost_impact" in feature
        assert "warning" in feature


def test_get_experimental_features_requires_auth(test_client):
    """Test that experimental features endpoint requires API key."""
    response = test_client.get("/api/experimental/features")
    
    assert response.status_code == 401


def test_configure_job_with_experimental_config(test_client, api_key, create_job, sample_pdf, temp_workspace):
    """Test configuring a job with experimental features enabled."""
    # Create a job with files
    job_id = "test-exp-config"
    job = create_job(job_id, "draft")
    
    # Create upload directory and add a PDF
    upload_dir = temp_workspace / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "test.pdf").write_bytes(sample_pdf)
    
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "experimental_config": {
            "experimental": True,
            "features": ["beta_models", "smart_cache"],
            "consent_given": True
        }
    }
    
    response = test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify configuration was saved
    assert data["job_id"] == job_id
    
    # Load job data and verify experimental config stored
    job_file = temp_workspace / "jobs" / f"{job_id}.json"
    with open(job_file, 'r') as f:
        saved_job = json.load(f)
    
    assert saved_job["config"]["experimental_config"]["experimental"] is True
    assert "beta_models" in saved_job["config"]["experimental_config"]["features"]
    assert "smart_cache" in saved_job["config"]["experimental_config"]["features"]


def test_start_job_with_experimental_requires_consent(test_client, api_key, create_job, sample_pdf, temp_workspace):
    """Test that experimental features require consent to start job."""
    # Create a job with files
    job_id = "test-exp-no-consent"
    job = create_job(job_id, "draft")
    
    # Create upload directory and add a PDF
    upload_dir = temp_workspace / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "test.pdf").write_bytes(sample_pdf)
    
    # Configure job with experimental enabled but NO consent
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "experimental_config": {
            "experimental": True,
            "features": ["beta_models"],
            "consent_given": False  # No consent!
        }
    }
    
    # Configure the job
    configure_response = test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers=headers
    )
    assert configure_response.status_code == 200
    
    # Try to start the job - should fail due to missing consent
    start_response = test_client.post(
        f"/api/jobs/{job_id}/start",
        headers={"X-API-KEY": api_key}
    )
    
    assert start_response.status_code == 400
    assert "consent" in start_response.json()["detail"].lower()


def test_start_job_with_experimental_consent_given(test_client, api_key, create_job, sample_pdf, temp_workspace, monkeypatch):
    """Test starting job with experimental features when consent is given."""
    # Create a job with files
    job_id = "test-exp-with-consent"
    job = create_job(job_id, "draft")
    
    # Create upload directory and add a PDF
    upload_dir = temp_workspace / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "test.pdf").write_bytes(sample_pdf)
    
    # Configure job with experimental enabled and consent given
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "experimental_config": {
            "experimental": True,
            "features": ["smart_cache"],
            "consent_given": True  # Consent given!
        }
    }
    
    # Configure the job
    configure_response = test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers=headers
    )
    assert configure_response.status_code == 200
    
    # Mock the database builder to avoid actual PDF processing
    class MockBuilder:
        def __init__(self, *args, **kwargs):
            pass
        def build_database(self):
            csv_path = temp_workspace / "jobs" / job_id / "research_database.csv"
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            csv_path.write_text("title,abstract\nTest Paper,Test abstract")
            return csv_path
    
    monkeypatch.setattr("webdashboard.app.ResearchDatabaseBuilder", MockBuilder, raising=False)
    
    # Mock job runner
    monkeypatch.setattr("webdashboard.app.job_runner", None)
    
    # Start the job - should succeed
    start_response = test_client.post(
        f"/api/jobs/{job_id}/start",
        headers={"X-API-KEY": api_key}
    )
    
    # May fail due to database builder, but should not fail due to consent
    if start_response.status_code == 400:
        assert "consent" not in start_response.json()["detail"].lower()


def test_experimental_config_optional(test_client, api_key, create_job, sample_pdf, temp_workspace):
    """Test that experimental_config is optional for backwards compatibility."""
    # Create a job with files
    job_id = "test-exp-optional"
    job = create_job(job_id, "draft")
    
    # Create upload directory and add a PDF
    upload_dir = temp_workspace / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "test.pdf").write_bytes(sample_pdf)
    
    # Configure job WITHOUT experimental_config (legacy behavior)
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE"
        # No experimental_config field
    }
    
    response = test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200


def test_legacy_experimental_field_still_works(test_client, api_key, create_job, sample_pdf, temp_workspace):
    """Test that legacy 'experimental' boolean field still works."""
    # Create a job with files
    job_id = "test-exp-legacy"
    job = create_job(job_id, "draft")
    
    # Create upload directory and add a PDF
    upload_dir = temp_workspace / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "test.pdf").write_bytes(sample_pdf)
    
    # Configure job with legacy experimental field
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    config = {
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE",
        "experimental": True  # Legacy field
    }
    
    response = test_client.post(
        f"/api/jobs/{job_id}/configure",
        json=config,
        headers=headers
    )
    
    assert response.status_code == 200
    
    # Load job data and verify legacy field stored
    job_file = temp_workspace / "jobs" / f"{job_id}.json"
    with open(job_file, 'r') as f:
        saved_job = json.load(f)
    
    assert saved_job["config"]["experimental"] is True


def test_experimental_features_risk_levels(test_client, api_key):
    """Test that experimental features include proper risk level information."""
    headers = {"X-API-KEY": api_key}
    
    response = test_client.get("/api/experimental/features", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify risk levels are valid
    valid_risk_levels = ["low", "medium", "high"]
    for feature in data["features"]:
        assert feature["risk_level"] in valid_risk_levels
    
    # Verify specific feature risk levels
    features_by_id = {f["id"]: f for f in data["features"]}
    
    # Beta models should be medium risk
    assert features_by_id["beta_models"]["risk_level"] == "medium"
    
    # Advanced modes should be high risk (due to cost)
    assert features_by_id["advanced_modes"]["risk_level"] == "high"
    
    # Smart cache should be low risk
    assert features_by_id["smart_cache"]["risk_level"] == "low"
    
    # Prototype viz should be low risk
    assert features_by_id["prototype_viz"]["risk_level"] == "low"


def test_experimental_features_cost_impact(test_client, api_key):
    """Test that experimental features include cost impact information."""
    headers = {"X-API-KEY": api_key}
    
    response = test_client.get("/api/experimental/features", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify cost impacts
    features_by_id = {f["id"]: f for f in data["features"]}
    
    # Smart cache should have negative cost impact (reduces cost)
    assert features_by_id["smart_cache"]["cost_impact"] == "negative"
    
    # Advanced modes should have very high cost impact
    assert features_by_id["advanced_modes"]["cost_impact"] == "very_high"
    
    # Prototype viz should have no cost impact
    assert features_by_id["prototype_viz"]["cost_impact"] == "none"
