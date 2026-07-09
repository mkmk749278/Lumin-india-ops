"""Control — owner maintenance panel.

Destructive/maintenance actions, each executed BY THE ENGINE via its
admin endpoints (ops never touches engine state directly):

* Clear signal history (all / today) — wipes signals, outcomes,
  suppressions and session summaries, then resets the engine's in-memory
  gate state and trade monitor so the live process matches the empty DB.
* Reset today's gates — clears caps/cooldowns/conflict windows in memory
  without deleting any stored history.

Every destructive action requires typing CLEAR into the confirmation box —
a stray tap on a phone must not wipe the quality window.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, Request

router = APIRouter()


def _render(request: Request, result: dict | None = None, error: str | None = None):
    return request.app.state.templates.TemplateResponse(
        request,
        "control.html",
        {"active": "control", "result": result, "error": error},
    )


@router.get("/control")
async def control(request: Request):
    return _render(request)


@router.post("/control/clear-history")
async def clear_history(
    request: Request,
    scope: str = Form("all"),
    confirm: str = Form(""),
):
    if confirm.strip() != "CLEAR":
        return _render(
            request,
            error='Type CLEAR (all caps) in the confirmation box to wipe history.',
        )
    if scope not in ("all", "today"):
        return _render(request, error=f"Unknown scope: {scope}")
    data = await request.app.state.engine_api.admin_clear_history(scope)
    if isinstance(data, dict) and data.get("error"):
        return _render(request, error=f"Engine refused: {data['error']}")
    return _render(request, result={"action": f"Cleared history ({scope})", **data})


@router.post("/control/reset-gates")
async def reset_gates(request: Request):
    data = await request.app.state.engine_api.admin_reset_gates()
    if isinstance(data, dict) and data.get("error"):
        return _render(request, error=f"Engine refused: {data['error']}")
    return _render(request, result={"action": "Reset today's gate state", **data})
