import pytest
from fastapi.testclient import TestClient
from server import app, job_store


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "ffmpeg_installed" in data
    assert "manim_installed" in data
    assert "ollama_running" in data


def test_generate_endpoint_validation(client):
    # Empty topic should fail with 400
    response = client.post("/api/generate", json={"topic": "   "})
    assert response.status_code == 400
    assert "Topic is required" in response.json()["detail"]


import uuid

def test_job_lifecycle(client):
    # 1. Create a job directly in store
    job_id = f"test_job_{uuid.uuid4().hex[:8]}"
    job_store.create_job(job_id, topic="Test Topic")

    # 2. Poll status
    res = client.get(f"/api/status/{job_id}")
    assert res.status_code == 200
    assert res.json()["job_id"] == job_id
    assert res.json()["status"] == "running"

    # 3. Update progress
    job_store.update_progress(job_id, 0.5, "Halfway done")
    res = client.get(f"/api/status/{job_id}")
    assert res.json()["progress"] == 0.5
    assert res.json()["message"] == "Halfway done"

    # 4. Complete job
    dummy_result = {"video_path": "storage/output/dummy.mp4", "quality_report": {"overall_success_rate": 100.0}}
    job_store.complete_job(job_id, dummy_result)
    res = client.get(f"/api/status/{job_id}")
    assert res.json()["status"] == "completed"
    assert res.json()["progress"] == 1.0


def test_not_found_job(client):
    response = client.get("/api/status/non_existent_job_xyz")
    assert response.status_code == 404


def test_cleanup_endpoint(client):
    response = client.post("/api/cleanup?max_age_hours=1")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_spa_root_serves_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "<div id=\"root\">" in response.text
