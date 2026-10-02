"""FastAPI application for Shonchoy Copilot.

Phase 2 wires the shell: CORS for the Next.js app, settings-driven feature flags
and the health/identity routers. Phase 3 added the forecast and savings-plan
routers, Phase 4 the explanation layer (``/chat-explain``), Phase 5 the Spending
Companion (``/anomalies``), Phase 7 the consistency band (``/credit-readiness``)
and Phase 8 the evaluation surface (``/metrics``).
"""
from __future__ import annotations

from typing import Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .middleware import add_request_logging
from .routers import (
    anomalies,
    chat_explain,
    credit_readiness,
    feedback,
    forecast,
    goal_templates,
    health,
    health_coach,
    metrics,
    parse_goal,
    savings_plan,
)


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
        allow_origin_regex=r"^https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # PII-free request logging: method/path/status/ms only, beside metrics.json.
    add_request_logging(app, active.request_log_file)
    app.include_router(health.router)
    app.include_router(forecast.router)
    app.include_router(savings_plan.router)
    app.include_router(chat_explain.router)
    app.include_router(anomalies.router)
    app.include_router(credit_readiness.router)
    app.include_router(health_coach.router)
    app.include_router(goal_templates.router)
    app.include_router(feedback.router)
    app.include_router(metrics.router)
    app.include_router(parse_goal.router)

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

