"""Unit tests for the signal-quality analytics (pure, no network)."""
from __future__ import annotations

from app import analytics
from app.ranges import iter_days, resolve_range

# A tiny cohort: 2 wins, 1 loss, 1 expired, 1 still open.
_ROWS = [
    {"status": "TP1_HIT", "result_pct": 1.5, "tier": "A+", "direction": "LONG",
     "setup_class": "ORB", "base": "NIFTY", "confidence": 80, "rr_ratio": 2.0},
    {"status": "TP1_HIT", "result_pct": 0.8, "tier": "B", "direction": "SHORT",
     "setup_class": "ORB", "base": "SBIN", "confidence": 60, "rr_ratio": 1.5},
    {"status": "SL_HIT", "result_pct": -1.0, "tier": "B", "direction": "LONG",
     "setup_class": "SR_FLIP", "base": "SBIN", "confidence": 55, "rr_ratio": 1.5},
    {"status": "EXPIRED", "result_pct": 0.0, "tier": "A+", "direction": "SHORT",
     "setup_class": "SR_FLIP", "base": "NIFTY", "confidence": 82, "rr_ratio": 3.0},
    {"status": "OPEN", "result_pct": None, "tier": "A+", "direction": "LONG",
     "setup_class": "ORB", "base": "NIFTY", "confidence": 90, "rr_ratio": 2.0},
]


def test_summarize_counts_and_pct():
    s = analytics.summarize(_ROWS)
    assert s["total"] == 5
    assert s["resolved"] == 4
    assert s["open"] == 1
    assert s["tp1"] == 2 and s["sl"] == 1 and s["expired"] == 1
    assert s["win_rate"] == 50.0
    assert s["net_pct"] == 1.3  # 1.5 + 0.8 - 1.0 + 0.0
    assert s["profit_factor"] == 2.3  # (1.5+0.8)/1.0


def test_summarize_two_target_outcomes_count_as_wins():
    # Engine two-target plan (Session 19): TP1_BE / TP2_HIT / TP1_EXPIRED all
    # banked the TP1 leg — wins; result_pct arrives position-weighted.
    rows = [
        {"status": "TP2_HIT", "result_pct": 0.61},
        {"status": "TP1_BE", "result_pct": 0.23},
        {"status": "TP1_EXPIRED", "result_pct": 0.31},
        {"status": "SL_HIT", "result_pct": -0.20},
        {"status": "OPEN", "result_pct": None},
    ]
    s = analytics.summarize(rows)
    assert s["resolved"] == 4
    assert s["wins"] == 3
    assert s["tp2"] == 1 and s["tp1_be"] == 1 and s["tp1_expired"] == 1
    assert s["win_rate"] == 75.0
    assert s["net_pct"] == 0.95


def test_profit_factor_all_wins_is_infinite():
    wins_only = [r for r in _ROWS if r["status"] == "TP1_HIT"]
    assert analytics.summarize(wins_only)["profit_factor"] is None


def test_apply_filters_tier_and_min_conf():
    aplus = analytics.apply_filters(_ROWS, tier="A+")
    assert len(aplus) == 3
    hi = analytics.apply_filters(_ROWS, min_conf=80)
    assert len(hi) == 3  # 80, 82, 90
    orb = analytics.apply_filters(_ROWS, setups={"ORB"})
    assert {r["setup_class"] for r in orb} == {"ORB"}


def test_breakdown_sorted_by_net_desc():
    bd = analytics.breakdown(_ROWS, "setup_class")
    keys = [b["key"] for b in bd]
    assert keys[0] == "ORB"  # +2.3 net beats SR_FLIP's -1.0
    assert set(keys) == {"ORB", "SR_FLIP"}


def test_distinct():
    assert analytics.distinct(_ROWS, "base") == ["NIFTY", "SBIN"]


def test_resolve_range_days_preset_span():
    from_d, to_d = resolve_range(None, None, 7, default_days=1)
    assert (to_d - from_d).days == 6
    assert len(iter_days(from_d, to_d)) == 7


def test_resolve_range_clamps_reversed_and_span():
    # reversed inputs get ordered
    from_d, to_d = resolve_range("2026-07-10", "2026-07-01")
    assert from_d.isoformat() == "2026-07-01"
    assert to_d.isoformat() == "2026-07-10"
