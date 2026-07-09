"""Strategy — slice resolved signals by any dimension to test what pays.

A quality lens, not a trading ledger: pick a window and a filter (tier / setup /
side / base / min-confidence / min-RR), and see the realised win-rate, net %,
expectancy and profit factor of exactly the signals that filter would have
taken — plus a best-first breakdown per setup, tier, side and base.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app import analytics
from app.exports import signals_csv_response
from app.ranges import iter_days, resolve_range

router = APIRouter()


def _filtered(data: list[dict], q: dict) -> list[dict]:
    return analytics.apply_filters(
        data,
        tier=q["tier"],
        setups=set(q["setups"]),
        direction=q["direction"],
        base=q["base"],
        min_conf=q["min_conf"],
        min_rr=q["min_rr"],
    )


def _read_filters(
    tier: str, setup: list[str], direction: str, base: str,
    min_conf: float, min_rr: float,
) -> dict:
    return {
        "tier": tier or "",
        "setups": [s for s in setup if s],
        "direction": direction or "",
        "base": (base or "").upper(),
        "min_conf": min_conf,
        "min_rr": min_rr,
    }


@router.get("/strategy")
async def strategy(
    request: Request,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    days: str | None = Query(None),
    tier: str = Query(""),
    setup: list[str] = Query(default=[]),
    direction: str = Query(""),
    base: str = Query(""),
    min_conf: float = Query(0.0, ge=0, le=100),
    min_rr: float = Query(0.0, ge=0),
):
    api = request.app.state.engine_api
    from_d, to_d = resolve_range(date_from, date_to, days, default_days=30)
    data = await api.signals_range(iter_days(from_d, to_d))

    error = data.get("error") if isinstance(data, dict) else None
    rows = data if isinstance(data, list) else []
    q = _read_filters(tier, setup, direction, base, min_conf, min_rr)

    cohort = _filtered(rows, q)
    summary = analytics.summarize(cohort)

    return request.app.state.templates.TemplateResponse(
        request, "strategy.html", {
            "error": error,
            "from": from_d.isoformat(),
            "to": to_d.isoformat(),
            "summary": summary,
            "by_setup": analytics.breakdown(cohort, "setup_class"),
            "by_tier": analytics.breakdown(cohort, "tier"),
            "by_direction": analytics.breakdown(cohort, "direction"),
            "by_base": analytics.breakdown(cohort, "base"),
            # Option lists come from the whole window so filters stay usable
            # even after a narrow selection empties the cohort.
            "all_setups": analytics.distinct(rows, "setup_class"),
            "all_bases": analytics.distinct(rows, "base"),
            "f": q,
            "active": "strategy",
        }
    )


@router.get("/strategy/export.csv")
async def strategy_export(
    request: Request,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    days: str | None = Query(None),
    tier: str = Query(""),
    setup: list[str] = Query(default=[]),
    direction: str = Query(""),
    base: str = Query(""),
    min_conf: float = Query(0.0, ge=0, le=100),
    min_rr: float = Query(0.0, ge=0),
):
    api = request.app.state.engine_api
    from_d, to_d = resolve_range(date_from, date_to, days, default_days=30)
    data = await api.signals_range(iter_days(from_d, to_d))
    rows = data if isinstance(data, list) else []
    q = _read_filters(tier, setup, direction, base, min_conf, min_rr)
    cohort = sorted(
        _filtered(rows, q),
        key=lambda r: r.get("created_at") or "",
        reverse=True,
    )
    fname = f"india_strategy_{from_d.isoformat()}_{to_d.isoformat()}.csv"
    return signals_csv_response(cohort, fname)
