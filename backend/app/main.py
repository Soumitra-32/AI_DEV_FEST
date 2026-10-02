"""FastAPI application for Shonchoy Copilot.

Phase 2 wires the shell: CORS for the Next.js app, settings-driven feature flags
and the health/identity routers. Phase 3 added the forecast and savings-plan
routers, and Phase 4 the explanation layer (``/chat-explain``); the anomaly,
signal and metrics routers arrive in later phases against the same contracts
already frozen in :mod:`backend.app.schemas`.
"""
from __future__ import annotations

from typing import Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .routers import chat_explain, forecast, health, savings_plan


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Build the application (a factory keeps tests free of global state)."""
    active = settings or get_settings()
    app = FastAPI(
        title=active.app_name,
        version=active.api_version,
        description=(
            "Bangla-first financial coach API. Synthetic data only, no PII, and the "
            "LLM never invents numbers — it only verbalises structured results."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(forecast.router)
    app.include_router(savings_plan.router)
    app.include_router(chat_explain.router)

    @app.get("/", include_in_schema=False)
    def root() -> Dict[str, str]:
        return {
            "service": active.app_name,
            "version": active.api_version,
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()

