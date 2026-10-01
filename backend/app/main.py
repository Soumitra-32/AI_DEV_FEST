"""FastAPI application for Shonchoy Copilot.

Phase 2 wires the shell: CORS for the Next.js app, settings-driven feature flags
and the health/identity routers. The feature routers (forecast, savings plan,
anomalies, chat-explain, signal, metrics) are added in later phases against the
contracts already frozen in :mod:`backend.app.schemas`.
"""
from __future__ import annotations

from typing import Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .routers import health


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

