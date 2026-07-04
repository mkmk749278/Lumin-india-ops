"""Suppressed — gate rejection telemetry."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/suppressed")
async def suppressed(request: Request):
    api = request.app.state.engine_api
    data = await api.suppressed(limit=200)
    return request.app.state.templates.TemplateResponse(
        request, "suppressed.html", {
            "suppressions": data if isinstance(data, list) else [],
            "error": data.get("error") if isinstance(data, dict) else None,
            "active": "suppressed",
        }
    )
