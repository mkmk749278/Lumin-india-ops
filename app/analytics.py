"""Signal-quality analytics — pure functions over engine signal rows.

A "strategy" here is just a filter over emitted signals (tier / setup / side /
base / min-confidence / min-RR). We measure it on the signals the engine has
already resolved (TP1_HIT / SL_HIT / EXPIRED), using the signed realised
percent (`result_pct`) — the cross-instrument-comparable measure. Summing raw
points across a mixed-price universe is meaningless, so points are never
aggregated here.

Phase 1 has no execution: "profit" is the signal's realised % had you taken it,
not a booked P&L. This is a quality lens, not a trading ledger.
"""
from __future__ import annotations

from typing import Any

RESOLVED = ("TP1_HIT", "SL_HIT", "EXPIRED")


def _f(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def apply_filters(
    rows: list[dict],
    *,
    tier: str = "",
    setups: set[str] | None = None,
    direction: str = "",
    base: str = "",
    min_conf: float = 0.0,
    min_rr: float = 0.0,
) -> list[dict]:
    """Keep only the signals a strategy would have taken."""
    setups = setups or set()
    out: list[dict] = []
    for r in rows:
        if tier and r.get("tier") != tier:
            continue
        if setups and r.get("setup_class") not in setups:
            continue
        if direction and r.get("direction") != direction:
            continue
        if base and r.get("base") != base:
            continue
        if _f(r.get("confidence")) < min_conf:
            continue
        if _f(r.get("rr_ratio")) < min_rr:
            continue
        out.append(r)
    return out


def summarize(rows: list[dict]) -> dict:
    """Aggregate quality metrics over a cohort of signals."""
    resolved = [r for r in rows if r.get("status") in RESOLVED]
    n = len(resolved)
    tp1 = sum(1 for r in resolved if r.get("status") == "TP1_HIT")
    sl = sum(1 for r in resolved if r.get("status") == "SL_HIT")
    exp = sum(1 for r in resolved if r.get("status") == "EXPIRED")

    pcts = [_f(r.get("result_pct")) for r in resolved]
    net = sum(pcts)
    gross_win = sum(p for p in pcts if p > 0)
    gross_loss = sum(p for p in pcts if p < 0)

    # Profit factor: gross win / gross loss. None encodes "all wins, no losses"
    # (rendered as ∞); 0.0 when there are no wins.
    if gross_loss < 0:
        profit_factor: float | None = round(gross_win / abs(gross_loss), 2)
    elif gross_win > 0:
        profit_factor = None
    else:
        profit_factor = 0.0

    return {
        "total": len(rows),
        "open": len(rows) - n,
        "resolved": n,
        "tp1": tp1,
        "sl": sl,
        "expired": exp,
        "win_rate": round(tp1 / n * 100, 1) if n else 0.0,
        "net_pct": round(net, 2),
        "avg_pct": round(net / n, 3) if n else 0.0,
        "profit_factor": profit_factor,
        "gross_win": round(gross_win, 2),
        "gross_loss": round(gross_loss, 2),
        "best": round(max(pcts), 2) if pcts else 0.0,
        "worst": round(min(pcts), 2) if pcts else 0.0,
    }


def breakdown(rows: list[dict], key: str) -> list[dict]:
    """Per-value summaries for one dimension, best net-% first.

    Surfaces which setups / tiers / sides / bases actually pay — the whole
    point of the strategy view.
    """
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(str(r.get(key) or "—"), []).append(r)

    out: list[dict] = []
    for value, grp in groups.items():
        summary = summarize(grp)
        summary["key"] = value
        out.append(summary)

    out.sort(key=lambda s: (s["net_pct"], s["win_rate"]), reverse=True)
    return out


def distinct(rows: list[dict], key: str) -> list[str]:
    """Sorted distinct non-empty values for a column (populates filters)."""
    return sorted({str(r[key]) for r in rows if r.get(key)})
