"""Smoke tests for Lumin India Ops dashboard."""
from __future__ import annotations

import os

os.environ.setdefault("OPS_SESSION_SECRET", "test-secret")
os.environ.setdefault("OPS_AUTH_TOKEN", "test-token")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_healthz_is_public():
    with TestClient(app) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_unauthenticated_redirect():
    with TestClient(app) as client:
        for path in [
            "/", "/signals", "/signals/export.csv", "/suppressed",
            "/outcomes", "/quality", "/strategy", "/strategy/export.csv",
        ]:
            r = client.get(path, follow_redirects=False)
            assert r.status_code == 302, f"{path} should redirect"
            assert "/login" in r.headers["location"]


def test_login_page_renders():
    with TestClient(app) as client:
        r = client.get("/login")
        assert r.status_code == 200
        assert "Lumin India Ops" in r.text


def test_login_wrong_password():
    with TestClient(app) as client:
        r = client.post(
            "/login", data={"password": "wrong"}, follow_redirects=False
        )
        assert r.status_code == 401
        assert "Invalid password" in r.text


def test_login_correct_password_redirects():
    with TestClient(app) as client:
        r = client.post(
            "/login", data={"password": "test-token"}, follow_redirects=False
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/"
