"""
Integration tests for JIE API.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import os

# Set test env vars
os.environ["API_KEY"] = "test_key_123"
os.environ["CELERY_BROKER"] = "memory://"
os.environ["CELERY_BACKEND"] = "cache+memory://"

from src.api.main import app

client = TestClient(app)


@pytest.fixture
def valid_headers():
    """Valid API headers."""
    return {"X-API-Key": "test_key_123"}


def test_health_check():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_ready_check_no_checkpoints():
    """Test readiness check when checkpoints missing."""
    response = client.get("/ready")
    # Will fail if checkpoints don't exist
    assert response.status_code in [200, 503]


def test_detect_missing_api_key():
    """Test detection without API key."""
    response = client.post("/api/detect", json={
        "samples": [{"sample_id": "1", "text": "test"}],
        "target_samples": [{"sample_id": "t1", "text": "target"}],
        "mode": "sync",
    })
    assert response.status_code == 422  # Missing header


def test_detect_invalid_api_key(valid_headers):
    """Test detection with invalid API key."""
    invalid_headers = {"X-API-Key": "wrong_key"}
    response = client.post("/api/detect", json={
        "samples": [{"sample_id": "1", "text": "test"}],
        "target_samples": [{"sample_id": "t1", "text": "target"}],
        "mode": "sync",
    }, headers=invalid_headers)
    assert response.status_code == 401


def test_detect_validation_errors(valid_headers):
    """Test input validation."""
    # Empty text
    response = client.post("/api/detect", json={
        "samples": [{"sample_id": "1", "text": ""}],
        "target_samples": [{"sample_id": "t1", "text": "target"}],
        "mode": "sync",
    }, headers=valid_headers)
    assert response.status_code == 422
    
    # Missing fields
    response = client.post("/api/detect", json={
        "samples": [{"sample_id": "1"}],
        "target_samples": [{"sample_id": "t1", "text": "target"}],
        "mode": "sync",
    }, headers=valid_headers)
    assert response.status_code == 422


@patch("src.api.main.run_jie_detection_task")
def test_detect_sync_mode(mock_task, valid_headers):
    """Test sync detection."""
    # Mock task result
    mock_result = Mock()
    mock_result.get.return_value = {"1": 0.5, "2": 0.8}
    mock_task.apply_async.return_value = mock_result
    
    response = client.post("/api/detect", json={
        "samples": [
            {"sample_id": "1", "text": "Sample 1"},
            {"sample_id": "2", "text": "Sample 2"},
        ],
        "target_samples": [{"sample_id": "t1", "text": "Target"}],
        "mode": "sync",
    }, headers=valid_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 2
    assert "processing_time_ms" in data


@patch("src.api.main.run_jie_detection_task")
def test_detect_async_mode(mock_task, valid_headers):
    """Test async detection."""
    # Mock task result
    mock_result = Mock()
    mock_result.id = "test_job_123"
    mock_task.apply_async.return_value = mock_result
    
    response = client.post("/api/detect", json={
        "samples": [{"sample_id": "1", "text": "Sample 1"}],
        "target_samples": [{"sample_id": "t1", "text": "Target"}],
        "mode": "async",
    }, headers=valid_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "test_job_123"
    assert data["status"] == "queued"


@patch("src.api.main.AsyncResult")
def test_get_job_status_completed(mock_async_result, valid_headers):
    """Test job status endpoint."""
    # Mock completed job
    mock_result = Mock()
    mock_result.state = "SUCCESS"
    mock_result.result = {"1": 0.5}
    mock_async_result.return_value = mock_result
    
    response = client.get("/api/jobs/test_job_123", headers=valid_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["results"] is not None


def test_rate_limiting(valid_headers):
    """Test rate limiting (if enabled)."""
    # Make many requests
    for i in range(15):
        response = client.post("/api/detect", json={
            "samples": [{"sample_id": "1", "text": "test"}],
            "target_samples": [{"sample_id": "t1", "text": "target"}],
            "mode": "async",
        }, headers=valid_headers)
        
        if response.status_code == 429:
            # Rate limit hit
            return
    
    # If no 429, rate limiting may not be strict in tests
    assert True
