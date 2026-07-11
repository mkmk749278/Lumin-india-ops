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

    # Two-target plan: TP1_BE / TP2_HIT / TP1_EXPIRED all banked the TP1 leg
    # (the engine's result_pct is already position-weighted) — wins.
    wins = sum(
        1
        for r in rows
        if r.get("outcome") in ("TP1_HIT", "TP1_BE", "TP2_HIT", "TP1_EXPIRED")
    )
    tp1 = sum(1 for r in rows if r.get("outcome") == "TP1_HIT")
    sl = sum(1 for r in rows if r.get("outcome") == "SL_HIT")
    expired = sum(1 for r in rows if r.get("outcome") == "EXPIRED")
    tp1_be = sum(1 for r in rows if r.get("outcome") == "TP1_BE")
    tp2 = sum(1 for r in rows if r.get("outcome") == "TP2_HIT")
    tp1_expired = sum(1 for r in rows if r.get("outcome") == "TP1_EXPIRED")
    net_points = sum(r.get("points", 0) for r in rows)
    # % is the only cross-instrument-comparable measure — summing raw points
    # across the 46-base universe just weights by price level.
    net_pct = sum(r.get("pct", 0) for r in rows)
    avg_pct = round(net_pct / len(rows), 2) if rows else 0

    return request.app.state.templates.TemplateResponse(
        request, "outcomes.html", {
            "outcomes": rows,
            "error": error,
            "tp1_count": tp1,
            "sl_count": sl,
            "expired_count": expired,
            "tp1_be_count": tp1_be,
            "tp2_count": tp2,
            "tp1_expired_count": tp1_expired,
            "net_points": net_points,
            "net_pct": net_pct,
            "avg_pct": avg_pct,
            "win_rate": round(wins / len(rows) * 100, 1) if rows else 0,
            "date_filter": date or "",
            "active": "outcomes",
        }
    )
