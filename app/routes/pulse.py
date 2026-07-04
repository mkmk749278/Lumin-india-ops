"""Pulse — engine state, session status, uptime."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def pulse(request: Request):
    api = request.app.state.engine_api
    pulse_data = await api.pulse()
    health = await api.health()
    return request.app.state.templates.TemplateResponse(
        request, "pulse.html", {"pulse": pulse_data, "health": health, "active": "pulse"}
    )
