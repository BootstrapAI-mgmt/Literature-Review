"""
Unit tests for Incremental Review API endpoints

Tests the incremental analysis endpoints for:
- Creating continuation jobs
- Extracting gaps from jobs
- Scoring paper relevance
- Merging incremental results
- Tracking job lineage
"""

import json
import io
from pathlib import Path
from datetime import datetime


def test_get_job_gaps_not_found(test_client, api_key):
    """Test GET /api/jobs/<job_id>/gaps with non-existent job"""
    headers = {"X-API-KEY": api_key}
    
    response = test_client.get("/api/jobs/nonexistent_job/gaps", headers=headers)
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_get_job_gaps_success(test_client, api_key, temp_workspace):
    """Test GET /api/jobs/<job_id>/gaps with valid job"""
    headers = {"X-API-KEY": api_key}
    
    # Create test job with gap analysis report
    job_id = "test_job_001"
    job_dir = temp_workspace / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Create mock gap analysis report
    gap_report = {
        "pillars": {
            "Pillar 1: Test Pillar": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "completeness": 0.45,
                                "target_coverage": 0.70,
                                "keywords": ["machine learning", "neural networks"],
                                "evidence_count": 2,
                                "requirement_text": "Test requirement"
                            }
                        }
                    }
                }
            }
        }
    }
    
    with open(job_dir / "gap_analysis_report.json", 'w') as f:
        json.dump(gap_report, f)
    
    response = test_client.get(f"/api/jobs/{job_id}/gaps", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == job_id
    assert "total_gaps" in data
    assert "gap_threshold" in data
    assert "gaps" in data
    assert "gaps_by_pillar" in data


def test_get_job_gaps_with_threshold(test_client, api_key, temp_workspace):
    """Test GET /api/jobs/<job_id>/gaps with custom threshold"""
    headers = {"X-API-KEY": api_key}
    
    # Create test job
    job_id = "test_job_002"
    job_dir = temp_workspace / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    gap_report = {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "completeness": 0.60,
                                "target_coverage": 0.70,
                                "keywords": ["test"],
                                "evidence_count": 1,
                                "requirement_text": "Test"
                            }
                        }
                    }
                }
            }
        }
    }
    
    with open(job_dir / "gap_analysis_report.json", 'w') as f:
        json.dump(gap_report, f)
    
    response = test_client.get(
        f"/api/jobs/{job_id}/gaps?threshold=0.5",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["gap_threshold"] == 0.5


def test_score_paper_relevance_no_job(test_client, api_key):
    """Test POST /api/jobs/<job_id>/relevance with non-existent job"""
    headers = {"X-API-KEY": api_key}
    
    payload = {
        "papers": [
            {
                "Title": "Test Paper",
                "Abstract": "Test abstract"
            }
        ],
        "threshold": 0.50
    }
    
    response = test_client.post(
        "/api/jobs/nonexistent_job/relevance",
        json=payload,
        headers=headers
    )
    
    assert response.status_code == 404


def test_score_paper_relevance_success(test_client, api_key, temp_workspace):
    """Test POST /api/jobs/<job_id>/relevance with valid job"""
    headers = {"X-API-KEY": api_key}
    
    # Create test job
    job_id = "test_job_003"
    job_dir = temp_workspace / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    gap_report = {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "completeness": 0.45,
                                "target_coverage": 0.70,
                                "keywords": ["machine learning", "neural networks"],
                                "evidence_count": 2,
                                "requirement_text": "Machine learning methods"
                            }
                        }
                    }
                }
            }
        }
    }
    
    with open(job_dir / "gap_analysis_report.json", 'w') as f:
        json.dump(gap_report, f)
    
    payload = {
        "papers": [
            {
                "DOI": "10.1000/test1",
                "Title": "Deep Learning with Neural Networks",
                "Abstract": "This paper explores machine learning using neural networks"
            }
        ],
        "threshold": 0.50
    }
    
    response = test_client.post(
        f"/api/jobs/{job_id}/relevance",
        json=payload,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == job_id
    assert "total_papers_scored" in data
    assert data["total_papers_scored"] == 1
    assert "papers_above_threshold" in data
    assert "papers_below_threshold" in data
    assert "scores" in data
    assert len(data["scores"]) == 1
    assert "avg_score" in data
    assert "recommendations" in data


def test_create_continuation_job_no_parent(test_client, api_key):
    """Test POST /api/jobs/<job_id>/continue with non-existent parent"""
    headers = {"X-API-KEY": api_key}
    
    payload = {
        "papers": [
            {
                "Title": "New Paper",
                "Abstract": "Test"
            }
        ],
        "relevance_threshold": 0.50,
        "prefilter_enabled": True
    }
    
    response = test_client.post(
        "/api/jobs/nonexistent_parent/continue",
        json=payload,
        headers=headers
    )
    
    assert response.status_code == 404


def test_create_continuation_job_success(test_client, api_key, temp_workspace):
    """Test POST /api/jobs/<job_id>/continue with valid parent job"""
    headers = {"X-API-KEY": api_key}
    
    # Create parent job
    parent_job_id = "parent_job_001"
    parent_dir = temp_workspace / "jobs" / parent_job_id
    parent_dir.mkdir(parents=True, exist_ok=True)
    
    gap_report = {
        "pillars": {
            "Pillar 1": {
                "requirements": {
                    "REQ-001": {
                        "sub_requirements": {
                            "SUB-001": {
                                "completeness": 0.45,
                                "target_coverage": 0.70,
                                "keywords": ["testing", "verification"],
                                "evidence_count": 2,
                                "requirement_text": "Testing methods"
                            }
                        }
                    }
                }
            }
        }
    }
    
    with open(parent_dir / "gap_analysis_report.json", 'w') as f:
        json.dump(gap_report, f)
    
    payload = {
        "papers": [
            {
                "DOI": "10.1000/new1",
                "Title": "Advanced Testing Techniques",
                "Abstract": "This paper discusses testing and verification methods"
            }
        ],
        "relevance_threshold": 0.50,
        "prefilter_enabled": True,
        "job_name": "Continuation Test"
    }
    
    response = test_client.post(
        f"/api/jobs/{parent_job_id}/continue",
        json=payload,
        headers=headers
    )
    
    assert response.status_code == 202
    data = response.json()
    
    assert "job_id" in data
    assert data["parent_job_id"] == parent_job_id
    assert data["status"] == "queued"
    assert "papers_to_analyze" in data
    assert "papers_skipped" in data
    assert "gaps_targeted" in data
    assert "estimated_cost_usd" in data
    assert "estimated_duration_minutes" in data
    
    # Verify job directory was created
    new_job_id = data["job_id"]
    new_job_dir = temp_workspace / "jobs" / new_job_id
    assert new_job_dir.exists()
    assert (new_job_dir / "papers_to_analyze.json").exists()
    assert (new_job_dir / "orchestrator_state.json").exists()


def test_merge_incremental_results_missing_jobs(test_client, api_key):
    """Test POST /api/jobs/<job_id>/merge with missing jobs"""
    headers = {"X-API-KEY": api_key}
    
    payload = {
        "incremental_job_id": "nonexistent_incr_job",
        "conflict_resolution": "highest_score"
    }
    
    response = test_client.post(
        "/api/jobs/nonexistent_base/merge",
        json=payload,
        headers=headers
    )
    
    assert response.status_code == 404


def test_merge_incremental_results_success(test_client, api_key, temp_workspace):
    """Test POST /api/jobs/<job_id>/merge with valid jobs"""
    headers = {"X-API-KEY": api_key}
    
    # Create base job
    base_job_id = "base_job_001"
    base_dir = temp_workspace / "jobs" / base_job_id
    base_dir.mkdir(parents=True, exist_ok=True)
    
    base_report = {
        "pillars": {
            "Pillar 1": {
                "completeness": 0.50,
                "requirements": {}
            }
        }
    }
    
    with open(base_dir / "gap_analysis_report.json", 'w') as f:
        json.dump(base_report, f)
    
    # Create incremental job
    incr_job_id = "incr_job_001"
    incr_dir = temp_workspace / "jobs" / incr_job_id
    incr_dir.mkdir(parents=True, exist_ok=True)
    
    incr_report = {
        "pillars": {
            "Pillar 1": {
                "completeness": 0.60,
                "requirements": {}
            }
        }
    }
    
    with open(incr_dir / "gap_analysis_report.json", 'w') as f:
        json.dump(incr_report, f)
    
    payload = {
        "incremental_job_id": incr_job_id,
        "conflict_resolution": "highest_score",
        "validation_mode": "strict"
    }
    
    response = test_client.post(
        f"/api/jobs/{base_job_id}/merge",
        json=payload,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "merge_id" in data
    assert data["base_job_id"] == base_job_id
    assert data["incremental_job_id"] == incr_job_id
    assert data["status"] == "completed"
    assert "statistics" in data
    assert "conflicts" in data
    assert "output_path" in data


def test_get_job_lineage_not_found(test_client, api_key):
    """Test GET /api/jobs/<job_id>/lineage with non-existent job"""
    headers = {"X-API-KEY": api_key}
    
    response = test_client.get("/api/jobs/nonexistent_job/lineage", headers=headers)
    
    assert response.status_code == 404


def test_get_job_lineage_success(test_client, api_key, temp_workspace):
    """Test GET /api/jobs/<job_id>/lineage with valid job"""
    headers = {"X-API-KEY": api_key}
    
    # Create test job with state
    job_id = "test_job_lineage"
    job_dir = temp_workspace / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Create orchestrator state
    state = {
        "schema_version": "1.0",
        "job_id": job_id,
        "parent_job_id": None,
        "job_type": "full",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "completed_at": None,
        "database_path": "test.csv",
        "database_hash": "abc123",
        "database_size": 10,
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE"
    }
    
    with open(job_dir / "orchestrator_state.json", 'w') as f:
        json.dump(state, f)
    
    response = test_client.get(f"/api/jobs/{job_id}/lineage", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == job_id
    assert data["job_type"] == "full"
    assert data["parent_job_id"] is None
    assert "child_job_ids" in data
    assert "ancestors" in data
    assert "descendants" in data
    assert "lineage_depth" in data
    assert "root_job_id" in data
    assert data["root_job_id"] == job_id  # Root is self when no parent


def test_get_job_lineage_with_parent(test_client, api_key, temp_workspace):
    """Test GET /api/jobs/<job_id>/lineage with parent job"""
    headers = {"X-API-KEY": api_key}
    
    # Create parent job
    parent_job_id = "parent_lineage_001"
    parent_dir = temp_workspace / "jobs" / parent_job_id
    parent_dir.mkdir(parents=True, exist_ok=True)
    
    parent_state = {
        "schema_version": "1.0",
        "job_id": parent_job_id,
        "parent_job_id": None,
        "job_type": "full",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "completed_at": "2024-01-01T01:00:00",
        "database_path": "parent.csv",
        "database_hash": "parent123",
        "database_size": 5,
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE"
    }
    
    with open(parent_dir / "orchestrator_state.json", 'w') as f:
        json.dump(parent_state, f)
    
    # Create child job
    child_job_id = "child_lineage_001"
    child_dir = temp_workspace / "jobs" / child_job_id
    child_dir.mkdir(parents=True, exist_ok=True)
    
    child_state = {
        "schema_version": "1.0",
        "job_id": child_job_id,
        "parent_job_id": parent_job_id,
        "job_type": "incremental",
        "created_at": "2024-01-02T00:00:00",
        "updated_at": "2024-01-02T00:00:00",
        "completed_at": None,
        "database_path": "child.csv",
        "database_hash": "child123",
        "database_size": 3,
        "pillar_selections": ["ALL"],
        "run_mode": "ONCE"
    }
    
    with open(child_dir / "orchestrator_state.json", 'w') as f:
        json.dump(child_state, f)
    
    response = test_client.get(f"/api/jobs/{child_job_id}/lineage", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == child_job_id
    assert data["job_type"] == "incremental"
    assert data["parent_job_id"] == parent_job_id
    assert len(data["ancestors"]) == 1
    assert data["ancestors"][0]["job_id"] == parent_job_id
    assert data["lineage_depth"] == 1
    assert data["root_job_id"] == parent_job_id
