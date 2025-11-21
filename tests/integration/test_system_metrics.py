"""
Integration tests for system metrics API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from webdashboard.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_get_system_metrics(client):
    """Test the GET /api/system/metrics endpoint."""
    response = client.get("/api/system/metrics")
    
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify structure
    assert "timestamp" in data
    assert "cpu" in data
    assert "memory" in data
    assert "disk" in data
    
    # Verify CPU data
    assert "percent" in data["cpu"]
    assert "count" in data["cpu"]
    assert isinstance(data["cpu"]["percent"], (int, float))
    assert isinstance(data["cpu"]["count"], int)
    assert 0 <= data["cpu"]["percent"] <= 100
    assert data["cpu"]["count"] > 0
    
    # Verify memory data
    assert "total" in data["memory"]
    assert "used" in data["memory"]
    assert "percent" in data["memory"]
    assert isinstance(data["memory"]["total"], int)
    assert isinstance(data["memory"]["used"], int)
    assert isinstance(data["memory"]["percent"], (int, float))
    assert data["memory"]["total"] > 0
    assert data["memory"]["used"] >= 0
    assert 0 <= data["memory"]["percent"] <= 100
    
    # Verify disk data
    assert "total" in data["disk"]
    assert "used" in data["disk"]
    assert "percent" in data["disk"]
    assert isinstance(data["disk"]["total"], int)
    assert isinstance(data["disk"]["used"], int)
    assert isinstance(data["disk"]["percent"], (int, float))
    assert data["disk"]["total"] > 0
    assert data["disk"]["used"] >= 0
    assert 0 <= data["disk"]["percent"] <= 100


def test_metrics_multiple_calls(client):
    """Test that metrics endpoint returns consistent data structure across calls."""
    response1 = client.get("/api/system/metrics")
    response2 = client.get("/api/system/metrics")
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Should have same structure
    assert set(data1.keys()) == set(data2.keys())
    assert set(data1["cpu"].keys()) == set(data2["cpu"].keys())
    assert set(data1["memory"].keys()) == set(data2["memory"].keys())
    assert set(data1["disk"].keys()) == set(data2["disk"].keys())
    
    # CPU count should be consistent
    assert data1["cpu"]["count"] == data2["cpu"]["count"]


def test_websocket_metrics_stream(client):
    """Test WebSocket connection for metrics streaming."""
    with client.websocket_connect("/api/system/ws/monitor") as websocket:
        # Should receive initial metrics update
        data = websocket.receive_json()
        
        assert data["type"] == "metrics_update"
        assert "data" in data
        
        # Verify data structure
        metrics = data["data"]
        assert "timestamp" in metrics
        assert "cpu" in metrics
        assert "memory" in metrics
        assert "disk" in metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
