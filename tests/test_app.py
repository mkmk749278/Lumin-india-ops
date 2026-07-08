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
        for path in ["/", "/signals", "/suppressed", "/outcomes", "/quality"]:
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


class _FakeEngineApi:
    """Stubs the engine endpoints the outcomes/quality views read."""

    async def aclose(self):
        pass

    async def outcomes(self, date=None, limit=100):
        return [
            {"outcome": "TP1_HIT", "base": "NIFTY", "direction": "LONG",
             "points": 67.1, "pct": 0.28, "entry": 24000.0, "exit_price": 24067.1,
             "resolved_at": "2026-07-08 11:30"},
            {"outcome": "TP1_HIT", "base": "TATASTEEL", "direction": "SHORT",
             "points": 0.4, "pct": 0.21, "entry": 189.6, "exit_price": 189.2,
             "resolved_at": "2026-07-08 12:25"},
        ]

    async def session_summary(self, limit=30):
        return [{
            "date": "2026-07-08", "signal_count": 23, "a_plus_count": 3,
            "b_count": 20, "avg_confidence": 62.0, "total_suppressed": 40,
            "gates_fired": "{}", "tp1_count": 8, "sl_count": 3, "expired_count": 5,
            "total_points": 3657.4, "total_pct": 0.49, "avg_pct": 0.03,
        }]


def test_outcomes_view_shows_percent_not_summed_points():
    with TestClient(app) as client:
        client.post("/login", data={"password": "test-token"})
        # Override the engine client after lifespan startup has created it.
        app.state.engine_api = _FakeEngineApi()
        r = client.get("/outcomes")
        assert r.status_code == 200
        # Cross-instrument-comparable %: net 0.28 + 0.21 = 0.49%.
        assert "+0.49%" in r.text
        assert "Net P&amp;L" in r.text
        # Per-row realised % is shown for both bases.
        assert "+0.28%" in r.text
        assert "+0.21%" in r.text


def test_quality_view_shows_percent_pl():
    with TestClient(app) as client:
        client.post("/login", data={"password": "test-token"})
        app.state.engine_api = _FakeEngineApi()
        r = client.get("/quality")
        assert r.status_code == 200
        assert "+0.49%" in r.text
        assert "Net P&amp;L" in r.text
