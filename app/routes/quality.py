"""Quality — 30-day session summary ledger."""
from __future__ import annotations

import json

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/quality")
async def quality(request: Request):
    api = request.app.state.engine_api
    data = await api.session_summary(limit=30)
    rows = data if isinstance(data, list) else []
    error = data.get("error") if isinstance(data, dict) else None

    # Decode gates_fired JSON strings into dicts for template rendering
    for row in rows:
        gf = row.get("gates_fired", "{}")
        if isinstance(gf, str):
            try:
                row["gates_fired"] = json.loads(gf)
            except Exception:
                row["gates_fired"] = {}

    total_signals = sum(r.get("signal_count", 0) for r in rows)
    total_tp1 = sum(r.get("tp1_count", 0) for r in rows)
    total_sl = sum(r.get("sl_count", 0) for r in rows)
    total_expired = sum(r.get("expired_count", 0) for r in rows)
    total_points = sum(r.get("total_points", 0) for r in rows)
    # Cross-instrument-comparable P&L — summing raw points across a 46-base
    # universe is meaningless (it just weights by price level).
    total_pct = sum(r.get("total_pct", 0) for r in rows)
    # Win = every TP1-banked outcome, not just literal TP1_HIT. Counting
    # tp1_count alone read 0% on days where every win ran to TP2, trailed to
    # BE, or expired past TP1 (e.g. 2026-07-14). Matches analytics.WINS.
    total_wins = total_tp1 + sum(
        r.get("tp2_count", 0)
        + r.get("tp1_be_count", 0)
        + r.get("tp1_expired_count", 0)
        for r in rows
    )
    total_resolved = total_wins + total_sl + total_expired
    overall_win = round(total_wins / total_resolved * 100, 1) if total_resolved else 0

    return request.app.state.templates.TemplateResponse(
        request, "quality.html", {
            "summaries": rows,
            "error": error,
            "total_signals": total_signals,
            "total_tp1": total_tp1,
            "total_wins": total_wins,
            "total_sl": total_sl,
            "total_points": total_points,
            "total_pct": total_pct,
            "overall_win_rate": overall_win,
            "active": "quality",
        }
    )
