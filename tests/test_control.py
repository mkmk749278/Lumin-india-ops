"""Control panel — owner maintenance actions proxied to the engine admin API."""
from __future__ import annotations

import os

os.environ.setdefault("OPS_SESSION_SECRET", "test-secret")
os.environ.setdefault("OPS_AUTH_TOKEN", "test-token")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


class _FakeAdminApi:
    """Records admin calls; returns engine-shaped responses."""

    def __init__(self, error: str | None = None):
        self.calls: list[tuple] = []
        self._error = error

    async def aclose(self):
        pass

    async def admin_clear_history(self, scope):
        self.calls.append(("clear-history", scope))
        if self._error:
            return {"error": self._error, "status_code": 403}
        return {
            "status": "ok",
            "scope": scope,
            "deleted": {"india_signals": 40, "india_signal_outcomes": 30,
                        "india_suppressions": 200, "india_session_summary": 4},
            "tracked_signals_dropped": 10,
            "gates_reset": True,
        }

    async def admin_reset_gates(self):
        self.calls.append(("reset-gates",))
        if self._error:
            return {"error": self._error, "status_code": 403}
        return {"status": "ok", "tracked_signals_dropped": 2, "gates_reset": True}


def _login(client):
    client.post("/login", data={"password": "test-token"})


def test_control_page_renders():
    with TestClient(app) as client:
        _login(client)
        r = client.get("/control")
        assert r.status_code == 200
        assert "Clear signal history" in r.text
        assert "Reset today" in r.text


def test_clear_history_requires_confirmation_word():
    with TestClient(app) as client:
        _login(client)
        fake = _FakeAdminApi()
        app.state.engine_api = fake
        r = client.post(
            "/control/clear-history", data={"scope": "all", "confirm": "yes"}
        )
        assert r.status_code == 200
        assert "Type CLEAR" in r.text
        assert fake.calls == []  # engine never called without confirmation


def test_clear_history_with_confirmation_calls_engine():
    with TestClient(app) as client:
        _login(client)
        fake = _FakeAdminApi()
        app.state.engine_api = fake
        r = client.post(
            "/control/clear-history", data={"scope": "all", "confirm": "CLEAR"}
        )
        assert r.status_code == 200
        assert fake.calls == [("clear-history", "all")]
        assert "Cleared history (all)" in r.text
        assert "india_signals: 40 rows deleted" in r.text


def test_clear_history_today_scope():
    with TestClient(app) as client:
        _login(client)
        fake = _FakeAdminApi()
        app.state.engine_api = fake
        client.post(
            "/control/clear-history", data={"scope": "today", "confirm": "CLEAR"}
        )
        assert fake.calls == [("clear-history", "today")]


def test_clear_history_surfaces_engine_error():
    with TestClient(app) as client:
        _login(client)
        app.state.engine_api = _FakeAdminApi(error="Admin token required")
        r = client.post(
            "/control/clear-history", data={"scope": "all", "confirm": "CLEAR"}
        )
        assert r.status_code == 200
        assert "Engine refused" in r.text


def test_reset_gates_calls_engine():
    with TestClient(app) as client:
        _login(client)
        fake = _FakeAdminApi()
        app.state.engine_api = fake
        r = client.post("/control/reset-gates")
        assert r.status_code == 200
        assert fake.calls == [("reset-gates",)]
        assert "Reset today" in r.text
