from fastapi.testclient import TestClient
from app.main import app


def test_metrics_endpoint_exposes_http_metrics():
    client = TestClient(app)

    # call a known endpoint
    r = client.get("/health")
    assert r.status_code == 200

    # fetch metrics
    m = client.get("/metrics")
    assert m.status_code == 200
    text = m.text

    # metrics should expose our http requests counter name
    assert "cc_http_requests_total" in text


def test_request_metrics_have_labels():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    m = client.get("/metrics")
    assert m.status_code == 200
    text = m.text
    # basic label presence
    assert "method=\"GET\"" in text or "GET" in text
