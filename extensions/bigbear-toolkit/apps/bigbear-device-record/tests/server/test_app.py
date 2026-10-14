import pytest
from fastapi.testclient import TestClient
from bigbear_device_record.server.app import create_app


def test_app_starts_and_root_returns_html():
    app = create_app(output_dir="./_test_output", static_dir=None)
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "bigbear-device-record" in resp.text.lower() or "<html" in resp.text.lower()


def test_health_endpoint():
    app = create_app(output_dir="./_test_output", static_dir=None)
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
