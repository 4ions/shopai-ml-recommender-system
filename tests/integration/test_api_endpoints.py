"""Integration tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from src.api.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_services():
    """Mock services for testing."""
    with patch("src.api.main.recommendation_service") as mock_rec, \
         patch("src.api.main.search_service") as mock_search:
        
        # Mock recommendation service
        mock_rec.get_recommendations.return_value = [
            {"product_id": "P001", "score": 0.9, "name": "Product 1"},
            {"product_id": "P002", "score": 0.8, "name": "Product 2"},
        ]
        
        # Mock search service
        mock_search.search.return_value = {
            "results": [
                {"product_id": "P001", "score": 0.95, "name": "Product 1"},
            ],
            "query_embedding_time_ms": 100.0,
            "search_time_ms": 50.0,
            "total_time_ms": 150.0,
        }
        
        yield mock_rec, mock_search


def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_recommendations_endpoint(client, mock_services):
    """Test recommendations endpoint."""
    mock_rec, _ = mock_services
    
    response = client.post(
        "/api/v1/recommendations",
        json={"user_id": "U001", "top_k": 5}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0
    mock_rec.get_recommendations.assert_called_once()


def test_recommendations_endpoint_invalid_user(client):
    """Test recommendations endpoint with invalid user."""
    response = client.post(
        "/api/v1/recommendations",
        json={"user_id": "INVALID", "top_k": 5}
    )
    # Should return 200 with empty recommendations or 404
    assert response.status_code in [200, 404]


def test_search_endpoint(client, mock_services):
    """Test search endpoint."""
    _, mock_search = mock_services
    
    response = client.post(
        "/api/v1/search",
        json={"query": "electronics", "top_k": 5}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "query_embedding_time_ms" in data
    mock_search.search.assert_called_once()


def test_search_endpoint_empty_query(client):
    """Test search endpoint with empty query."""
    response = client.post(
        "/api/v1/search",
        json={"query": "", "top_k": 5}
    )
    # Should return 200 or 400
    assert response.status_code in [200, 400]


def test_feedback_endpoint(client):
    """Test feedback endpoint."""
    response = client.post(
        "/api/v1/feedback",
        json={
            "user_id": "U001",
            "product_id": "P001",
            "rating": 5,
            "feedback_type": "explicit"
        }
    )
    # Should return 200 or 201
    assert response.status_code in [200, 201]


def test_docs_endpoint(client):
    """Test OpenAPI docs endpoint."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_endpoint(client):
    """Test ReDoc endpoint."""
    response = client.get("/redoc")
    assert response.status_code == 200


def test_openapi_json_endpoint(client):
    """Test OpenAPI JSON endpoint."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data

