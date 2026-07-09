"""CSV serialisation for signal downloads."""
from __future__ import annotations

import csv
import io

from fastapi import Response

# Full engine signal row, flattened. Order is stable so downloaded files
# diff cleanly and import predictably into a spreadsheet.
SIGNAL_FIELDS = [
    "created_at",
    "signal_id",
    "base",
    "symbol",
    "direction",
    "setup_class",
    "tier",
    "confidence",
    "rr_ratio",
    "entry",
    "sl",
    "tp1",
    "tp2",
    "sl_pct",
    "tp1_pct",
    "regime_60m",
    "regime_daily",
    "vix_at_entry",
    "pcr_at_entry",
    "expiry_date",
    "days_to_expiry",
    "status",
    "result_pct",
    "result_points",
]


def signals_csv_response(rows: list[dict], filename: str) -> Response:
    """Render signal rows to a downloadable CSV response."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(SIGNAL_FIELDS)
    for r in rows:
        writer.writerow([r.get(field, "") for field in SIGNAL_FIELDS])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
