"""
Tests for observability endpoints and middleware.
"""

from sqlalchemy import create_engine


def test_healthz_ok(monkeypatch, client):
    # Patch the global engine used by /healthz to a lightweight SQLite engine.
    test_engine = create_engine("sqlite://")
    monkeypatch.setattr("main.engine", test_engine)
    monkeypatch.setattr("database.engine", test_engine)

    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert data["db"].startswith("ok")
    assert data["db_latency_ms"] is None or data["db_latency_ms"] >= 0


def test_metrics_and_request_id(monkeypatch, client):
    # Ensure health and root requests are recorded and return request_id headers.
    test_engine = create_engine("sqlite://")
    monkeypatch.setattr("main.engine", test_engine)
    monkeypatch.setattr("database.engine", test_engine)

    # Trigger a couple of requests to populate metrics
    r1 = client.get("/")
    r2 = client.get("/healthz")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert "x-request-id" in r1.headers
    assert "x-request-id" in r2.headers

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    body = metrics.text
    assert "pantrypilot_requests_total" in body
    # The root path should be represented in metrics labels
    assert 'method="GET",path="/",status="200"' in body
