"""FastAPI application for Shonchoy Copilot.

Phase 2 wires the shell: CORS for the Next.js app, settings-driven feature flags
and the health/identity routers. Phase 3 added the forecast and savings-plan
routers, Phase 4 the explanation layer (``/chat-explain``), Phase 5 the Spending
Companion (``/anomalies``), Phase 7 the consistency band (``/credit-readiness``)
and Phase 8 the evaluation surface (``/metrics``).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.data import features as user_features

from .config import Settings, get_settings
from .middleware import add_request_logging
from .routers import (
    anomalies,
    chat_explain,
    credit_readiness,
    events,
    feedback,
    forecast,
    goal_templates,
    health,
    health_coach,
    metrics,
    parse_goal,
    savings_plan,
)

logger = logging.getLogger("shonchoy.main")


def _warm_user_features(active: Settings) -> None:
    """Build the user feature matrix once at startup, off the request path.

    The first call to a feature-backed endpoint otherwise pays the whole
    dataset build (~10s here: read 176k transactions, recompute 501 users)
    while the browser's 12s abort ticks. Doing it here moves that cost into
    boot, so the demo's first click is as fast as the hundredth.

    Best-effort by design: a missing or broken dataset must surface as the
    endpoint's own 503/404, never stop the app from starting.
    """
    try:
        frame = user_features.user_features_cached(active.db_path)
        logger.info("warmed user features: %d users", len(frame))
    except Exception as exc:  # pragma: no cover - degraded start
        logger.warning("could not warm user features: %s", type(exc).__name__)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Build the application (a factory keeps tests free of global state)."""
    active = settings or get_settings()
    # GAP-11: refuse to boot on a placeholder token — a public demo must never
    # run with "change-me". Tests use explicit tokens; local dev sets
    # ALLOW_DEFAULT_TOKEN=1 (or any real token) to bypass.
    if active.demo_auth_token in {"", "change-me", "change-me-set-in-render-dashboard"}:
        if os.getenv("ALLOW_DEFAULT_TOKEN") != "1":
            raise RuntimeError(
                "refusing to boot with a placeholder DEMO_AUTH_TOKEN; "
                "set a real token (ALLOW_DEFAULT_TOKEN=1 bypasses locally)"
            )
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Warm the shared feature matrix before the first request arrives, so no
        # user-visible request ever pays the one-off dataset build.
        _warm_user_features(active)
        yield

    app = FastAPI(
        title=active.app_name,
        version=active.api_version,
        lifespan=lifespan,
        description=(
            "Bangla-first financial coach API. Synthetic data only, no PII, and the "
            "LLM never invents numbers — it only verbalises structured results."
        ),
    )
    # GAP-11: no allow_origin_regex — it admitted every origin and defeated
    # the allow-list below. Auth rides a header (never cookies), so
    # credentials stay off. Demo/LAN origins come from CORS_ORIGINS env.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active.cors_origin_list,
        allow_credentials=False,
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
    app.include_router(events.router)
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

