"""Lumin India Ops — FastAPI entrypoint.

Owner-only diagnostic dashboard for the Lumin India NSE F&O signal engine.
Single-password session auth. Read-only in Phase 1 (no control plane writes
until the India engine has write endpoints).

Middleware ordering: AuthRedirectMiddleware added first (innermost),
SessionMiddleware added second (outermost) — session is populated before
the auth check runs.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth_mw import AuthRedirectMiddleware
from app.config import load_settings
from app.data_sources.engine_api import IndiaEngineApiClient
from app.routes import auth, outcomes, pulse, quality, signals, suppressed

settings = load_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO)
)
logger = logging.getLogger("india-ops")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = settings
    app.state.templates = templates
    app.state.engine_api = IndiaEngineApiClient(settings)
    logger.info(
        "india-ops up — engine_api=%s", settings.india_engine_api_base
    )
    try:
        yield
    finally:
        await app.state.engine_api.aclose()


app = FastAPI(
    title="Lumin India Ops",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(AuthRedirectMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,
)
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

app.include_router(auth.router)
app.include_router(pulse.router)
app.include_router(signals.router)
app.include_router(suppressed.router)
app.include_router(outcomes.router)
app.include_router(quality.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
