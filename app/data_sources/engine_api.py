"""Async httpx client for the Lumin India engine API at lumintrade.app."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.config import Settings


class IndiaEngineApiClient:
    """Thin async client. Returns JSON or ``{"error": ...}`` on failure."""

    def __init__(self, settings: Settings) -> None:
        self._base = settings.india_engine_api_base.rstrip("/")
        self._token = settings.india_api_token
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            self._client = httpx.AsyncClient(
                base_url=self._base,
                headers=headers,
                timeout=httpx.Timeout(15.0),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str, **params: Any) -> Any:
        try:
            r = await self.client.get(path, params=params or None)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            detail: Any = None
            try:
                detail = exc.response.json().get("detail")
            except Exception:
                detail = exc.response.text[:200]
            return {
                "error": detail or str(exc),
                "status_code": exc.response.status_code,
                "endpoint": path,
            }
        except httpx.HTTPError as exc:
            return {"error": str(exc), "endpoint": path}

    async def health(self) -> Any:
        return await self._get("/api/health")

    async def pulse(self) -> Any:
        return await self._get("/api/pulse")

    async def signals(
        self,
        date: str | None = None,
        tier: str | None = None,
        setup_class: str | None = None,
        limit: int = 50,
    ) -> Any:
        params: dict[str, Any] = {"limit": limit}
        if date:
            params["date"] = date
        if tier:
            params["tier"] = tier
        if setup_class:
            params["setup_class"] = setup_class
        return await self._get("/api/signals", **params)

    async def signals_range(
        self,
        days: list[str],
        tier: str | None = None,
        setup_class: str | None = None,
        limit_per_day: int = 200,
    ) -> Any:
        """Concatenate `/api/signals` across a set of days.

        The engine only filters by a single date, so a window is one call per
        day, fanned out concurrently (owner tool, off the hot path). Returns
        the merged row list, or the first ``{"error": ...}`` encountered.
        """
        results = await asyncio.gather(
            *(
                self.signals(
                    date=d,
                    tier=tier,
                    setup_class=setup_class,
                    limit=limit_per_day,
                )
                for d in days
            )
        )
        rows: list[dict] = []
        for r in results:
            if isinstance(r, dict) and r.get("error"):
                return r
            if isinstance(r, list):
                rows.extend(r)
        return rows

    async def signal(self, signal_id: str) -> Any:
        return await self._get(f"/api/signals/{signal_id}")

    async def suppressed(self, limit: int = 100) -> Any:
        return await self._get("/api/suppressed", limit=limit)

    async def outcomes(
        self,
        date: str | None = None,
        limit: int = 100,
    ) -> Any:
        params: dict[str, Any] = {"limit": limit}
        if date:
            params["date"] = date
        return await self._get("/api/outcomes", **params)

    async def session_summary(self, limit: int = 30) -> Any:
        return await self._get("/api/session-summary", limit=limit)
