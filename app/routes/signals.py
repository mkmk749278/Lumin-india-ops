"""Signals — today's emitted signals."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/signals")
async def signals(
    request: Request,
    date: str | None = Query(None),
    tier: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    api = request.app.state.engine_api
    data = await api.signals(date=date, tier=tier, limit=limit)
    return request.app.state.templates.TemplateResponse(
        request, "signals.html", {
            "signals": data if isinstance(data, list) else [],
            "error": data.get("error") if isinstance(data, dict) else None,
            "date_filter": date or "",
            "tier_filter": tier or "",
            "active": "signals",
        }
    )
