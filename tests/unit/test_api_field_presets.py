"""Test the field preset API endpoints."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastapi.testclient import TestClient
from webdashboard.app import app

client = TestClient(app)


def test_get_field_presets():
    """Test GET /api/field-presets endpoint."""
    response = client.get("/api/field-presets")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "presets" in data
    assert isinstance(data["presets"], dict)
    assert "ai_ml" in data["presets"]
    assert "mathematics" in data["presets"]
    
    # Check structure of a preset
    ai_preset = data["presets"]["ai_ml"]
    assert ai_preset["name"] == "AI & Machine Learning"
    assert ai_preset["half_life_years"] == 3.0
    assert "description" in ai_preset
    assert "examples" in ai_preset


def test_suggest_field_ai_ml():
    """Test POST /api/suggest-field with AI/ML papers."""
    papers = [
        {"title": "Deep Learning for Image Recognition", "abstract": "Neural networks and machine learning..."},
        {"title": "Attention Mechanisms in NLP", "abstract": "Artificial intelligence for language..."}
    ]
    
    response = client.post("/api/suggest-field", json={"papers": papers})
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["suggested_field"] == "ai_ml"
    assert data["field_name"] == "AI & Machine Learning"
    assert data["half_life_years"] == 3.0
    assert "description" in data
    assert data["confidence"] == "high"


def test_suggest_field_mathematics():
    """Test POST /api/suggest-field with mathematics papers."""
    papers = [
        {"title": "Proof of Mathematical Theorem", "abstract": "Mathematics and theorem..."},
        {"title": "Number Theory", "abstract": "Mathematical proof..."}
    ]
    
    response = client.post("/api/suggest-field", json={"papers": papers})
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["suggested_field"] == "mathematics"
    assert data["field_name"] == "Mathematics"
    assert data["half_life_years"] == 10.0


def test_suggest_field_no_papers():
    """Test POST /api/suggest-field with no papers (error case)."""
    response = client.post("/api/suggest-field", json={"papers": []})
    
    assert response.status_code == 400
    assert "No papers provided" in response.json()["detail"]


def test_suggest_field_custom_fallback():
    """Test POST /api/suggest-field falls back to custom when no match."""
    papers = [
        {"title": "Random Topic", "abstract": "Nothing specific..."}
    ]
    
    response = client.post("/api/suggest-field", json={"papers": papers})
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["suggested_field"] == "custom"
    assert data["confidence"] == "low"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
