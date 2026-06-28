"""A smoke test for the API — boots the app and hits /health."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    with TestClient(app) as client:  # `with` runs startup/shutdown (scheduler)
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["app"] == "InsightForge"


def test_data_analyze_with_csv():
    csv = b"name,score\nA,10\nB,20\nB,\n"
    with TestClient(app) as client:
        r = client.post("/data/analyze", files={"file": ("t.csv", csv, "text/csv")})
        assert r.status_code == 200
        data = r.json()
        assert data["rows"] == 3
        assert data["columns"] == 2
