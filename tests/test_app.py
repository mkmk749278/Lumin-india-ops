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
            "/edge", "/allocator", "/control",
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

    async def allocator(self, days=30):
        return {
            "mode": "recommendation", "days": days, "sample": 40,
            "thresholds": {"min_sample": 20, "ev_floor": 0.0, "suppress_ev": -0.05},
            "allocation": {
                "tally": {"EMIT": 1, "SUPPRESS": 1},
                "recommendations": {
                    "by_market_vs_signal": [
                        {"key": "LONG_BIASED/LONG", "verdict": "EMIT", "n": 20,
                         "win_rate": 56.0, "ev_net_pct": 0.34,
                         "reason": "expectancy +0.340% ≥ floor"},
                        {"key": "LONG_BIASED/SHORT", "verdict": "SUPPRESS", "n": 20,
                         "win_rate": 13.0, "ev_net_pct": -0.26,
                         "reason": "expectancy -0.260% ≤ -0.050%"},
                    ],
                },
            },
        }

    async def edge_matrix(self, days=30):
        return {
            "days": days, "sample": 4, "cost_pct": 0.06,
            "matrix": {
                "overall": [{
                    "key": "ALL", "n": 4, "wins": 2, "losses": 2, "expired": 0,
                    "win_rate": 50.0, "net_pct": 0.4, "avg_pct": 0.1,
                    "ev_net_pct": 0.04,
                }],
                "by_market_vs_signal": [
                    {"key": "LONG_BIASED/LONG", "n": 2, "wins": 2, "losses": 0,
                     "expired": 0, "win_rate": 100.0, "net_pct": 0.8,
                     "avg_pct": 0.4, "ev_net_pct": 0.34},
                    {"key": "LONG_BIASED/SHORT", "n": 2, "wins": 0, "losses": 2,
                     "expired": 0, "win_rate": 0.0, "net_pct": -0.4,
                     "avg_pct": -0.2, "ev_net_pct": -0.26},
                ],
            },
        }


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


def test_edge_view_renders_matrix_cohorts():
    with TestClient(app) as client:
        client.post("/login", data={"password": "test-token"})
        app.state.engine_api = _FakeEngineApi()
        r = client.get("/edge")
        assert r.status_code == 200
        # The counter-trend cohort and the with-trend cohort both surface.
        assert "LONG_BIASED/SHORT" in r.text
        assert "LONG_BIASED/LONG" in r.text
        # Cost-adjusted expectancy is rendered.
        assert "Expectancy" in r.text


def test_allocator_view_shows_verdicts_and_observe_only_banner():
    with TestClient(app) as client:
        client.post("/login", data={"password": "test-token"})
        app.state.engine_api = _FakeEngineApi()
        r = client.get("/allocator")
        assert r.status_code == 200
        assert "EMIT" in r.text and "SUPPRESS" in r.text
        assert "LONG_BIASED/SHORT" in r.text
        # The observe-only guardrail must be visible.
        assert "observe-only" in r.text.lower()
