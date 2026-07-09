"""Date-range resolution for the signals/strategy views.

The engine keys every row on `DATE(created_at)` in IST (its container TZ), so
all range maths here is done in IST — computed as UTC+5:30, independent of
wherever the ops container runs.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

_IST = timezone(timedelta(hours=5, minutes=30))

# Upper bound on a single query span. Each day is one engine call, so this
# caps fan-out (owner tool, not a hot path) and keeps HTML/CSV bounded.
MAX_RANGE_DAYS = 92


def ist_today() -> date:
    """Today's calendar date in IST."""
    return datetime.now(_IST).date()


def parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


def resolve_range(
    date_from: str | None,
    date_to: str | None,
    days: str | int | None = None,
    *,
    default_days: int = 7,
) -> tuple[date, date]:
    """Resolve the effective [from, to] window (inclusive).

    Precedence: an explicit from/to wins; else a `days` preset (last N days
    ending today); else `default_days` ending today. The span is clamped to
    MAX_RANGE_DAYS and from/to are ordered.
    """
    today = ist_today()

    if date_from or date_to:
        to_d = parse_date(date_to, today)
        from_d = parse_date(date_from, to_d)
    elif days is not None:
        try:
            n = max(1, int(days))
        except (TypeError, ValueError):
            n = default_days
        to_d = today
        from_d = today - timedelta(days=n - 1)
    else:
        to_d = today
        from_d = today - timedelta(days=default_days - 1)

    if from_d > to_d:
        from_d, to_d = to_d, from_d

    span = (to_d - from_d).days + 1
    if span > MAX_RANGE_DAYS:
        from_d = to_d - timedelta(days=MAX_RANGE_DAYS - 1)

    return from_d, to_d


def iter_days(from_d: date, to_d: date) -> list[str]:
    """Every calendar day in [from_d, to_d] as `YYYY-MM-DD` strings."""
    out: list[str] = []
    d = from_d
    while d <= to_d:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out
