"""Outcomes — signal TP1/SL/EXPIRED results."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/outcomes")
async def outcomes(
    request: Request,
    date: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    api = request.app.state.engine_api
    data = await api.outcomes(date=date, limit=limit)
    rows = data if isinstance(data, list) else []
    error = data.get("error") if isinstance(data, dict) else None

    tp1 = sum(1 for r in rows if r.get("outcome") == "TP1_HIT")
    sl = sum(1 for r in rows if r.get("outcome") == "SL_HIT")
    expired = sum(1 for r in rows if r.get("outcome") == "EXPIRED")
    net_points = sum(r.get("points", 0) for r in rows)

    return request.app.state.templates.TemplateResponse(
        request, "outcomes.html", {
            "outcomes": rows,
            "error": error,
            "tp1_count": tp1,
            "sl_count": sl,
            "expired_count": expired,
            "net_points": net_points,
            "win_rate": round(tp1 / len(rows) * 100, 1) if rows else 0,
            "date_filter": date or "",
            "active": "outcomes",
        }
    )
