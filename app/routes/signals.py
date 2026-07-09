"""Signals — emitted signals over a date range, with CSV download."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.exports import signals_csv_response
from app.ranges import iter_days, resolve_range

router = APIRouter()

# Cap rows rendered into the HTML table (a wide window can be thousands).
# The full cohort is always available via the CSV download.
_TABLE_CAP = 400


def _sort_desc(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: r.get("created_at") or "", reverse=True)


@router.get("/signals")
async def signals(
    request: Request,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    days: str | None = Query(None),
    tier: str | None = Query(None),
):
    api = request.app.state.engine_api
    # Default view is today; presets/custom widen it.
    from_d, to_d = resolve_range(date_from, date_to, days, default_days=1)
    data = await api.signals_range(iter_days(from_d, to_d), tier=tier or None)

    error = data.get("error") if isinstance(data, dict) else None
    rows = _sort_desc(data) if isinstance(data, list) else []

    return request.app.state.templates.TemplateResponse(
        request, "signals.html", {
            "signals": rows[:_TABLE_CAP],
            "total": len(rows),
            "capped": len(rows) > _TABLE_CAP,
            "error": error,
            "from": from_d.isoformat(),
            "to": to_d.isoformat(),
            "tier_filter": tier or "",
            "active": "signals",
        }
    )


@router.get("/signals/export.csv")
async def signals_export(
    request: Request,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    days: str | None = Query(None),
    tier: str | None = Query(None),
):
    api = request.app.state.engine_api
    from_d, to_d = resolve_range(date_from, date_to, days, default_days=1)
    data = await api.signals_range(iter_days(from_d, to_d), tier=tier or None)
    rows = _sort_desc(data) if isinstance(data, list) else []
    fname = f"india_signals_{from_d.isoformat()}_{to_d.isoformat()}.csv"
    return signals_csv_response(rows, fname)
