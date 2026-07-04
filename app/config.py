"""Environment-driven configuration for Lumin India Ops."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if value is None and required:
        raise RuntimeError(f"Missing required env var: {name}")
    return value or ""


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    session_secret: str
    auth_token: str
    india_engine_api_base: str
    india_api_token: str
    port: int
    log_level: str


def load_settings() -> Settings:
    return Settings(
        session_secret=_env("OPS_SESSION_SECRET", required=True),
        auth_token=_env("OPS_AUTH_TOKEN", required=True),
        india_engine_api_base=_env(
            "INDIA_ENGINE_API_BASE", "https://lumintrade.app"
        ),
        india_api_token=_env("INDIA_API_TOKEN"),
        port=_env_int("OPS_PORT", 8080),
        log_level=_env("LOG_LEVEL", "INFO"),
    )
