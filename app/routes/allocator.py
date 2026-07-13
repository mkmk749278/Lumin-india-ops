"""Allocator — the engine's observe-only strategy recommendations.

Reads `/api/allocator`: per-cohort EMIT / SUPPRESS / HOLD / INSUFFICIENT_DATA
verdicts derived from the measured edge matrix. It is the "what the allocator
would do" surface — it changes nothing the engine emits (recommendation mode).
Read-only; engine is the source of truth.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

router = APIRouter()

_DIMENSIONS: list[tuple[str, str]] = [
    ("by_market_vs_signal", "Market direction × signal side"),
    ("by_setup_direction", "Setup × side"),
    ("by_setup", "Setup"),
]


@router.get("/allocator")
async def allocator(
    request: Request,
    days: int = Query(30, ge=1, le=90),
):
    api = request.app.state.engine_api
    data = await api.allocator(days=days)
    if not isinstance(data, dict):
        data = {}

    error = data.get("error")
    alloc = data.get("allocation") or {}
    recs = alloc.get("recommendations") or {}
    dimensions = [
        (label, recs.get(key, []))
        for key, label in _DIMENSIONS
        if recs.get(key)
    ]

    return request.app.state.templates.TemplateResponse(
        request, "allocator.html", {
            "error": error,
            "mode": data.get("mode", "recommendation"),
            "days": days,
            "sample": data.get("sample", 0),
            "thresholds": data.get("thresholds", {}),
            "tally": alloc.get("tally", {}),
            "dimensions": dimensions,
            "active": "allocator",
        }
    )
