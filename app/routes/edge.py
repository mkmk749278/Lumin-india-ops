"""Edge — the engine's Strategy×Context edge matrix.

Where Strategy is an ops-side lab (fan out signals, filter, aggregate), Edge
reads the engine-computed matrix from `/api/edge-matrix`: realised win% /
net% / cost-adjusted expectancy per cohort. This is the surface that showed,
on 2026-07-13, the counter-trend `LONG_BIASED/SHORT` cohort bleeding while
`LONG_BIASED/LONG` led — and it is what the tier recalibration and the
allocator read. Read-only; engine is the source of truth.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

router = APIRouter()

# Order + human labels for the matrix dimensions the template renders.
_DIMENSIONS: list[tuple[str, str]] = [
    ("by_market_vs_signal", "Market direction × signal side"),
    ("by_setup_direction", "Setup × side"),
    ("by_setup", "Setup"),
    ("by_tier", "Confidence tier"),
    ("by_session_phase", "Session phase"),
    ("by_vix_regime", "VIX regime"),
]


@router.get("/edge")
async def edge(
    request: Request,
    days: int = Query(30, ge=1, le=90),
):
    api = request.app.state.engine_api
    data = await api.edge_matrix(days=days)

    error = data.get("error") if isinstance(data, dict) else None
    matrix = data.get("matrix", {}) if isinstance(data, dict) else {}
    overall = (matrix.get("overall") or [{}])[0] if matrix else {}
    dimensions = [
        (label, matrix.get(key, []))
        for key, label in _DIMENSIONS
        if matrix.get(key)
    ]

    return request.app.state.templates.TemplateResponse(
        request, "edge.html", {
            "error": error,
            "days": days,
            "sample": data.get("sample", 0) if isinstance(data, dict) else 0,
            "cost_pct": data.get("cost_pct", 0.0) if isinstance(data, dict) else 0.0,
            "overall": overall,
            "dimensions": dimensions,
            "active": "edge",
        }
    )
