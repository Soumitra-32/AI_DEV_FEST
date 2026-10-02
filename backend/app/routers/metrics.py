"""Metrics endpoint (Phase 8): ``GET /metrics``.

Thin by design -- auth -> feature flag -> service -> frozen schema -- like every
other router here. The interesting part is
:mod:`backend.app.services.metrics_service`, which maps the ``metrics.json`` that
``backend/scripts/train_all.py`` wrote onto :class:`MetricsResponse`; this file
holds no arithmetic and loads no model.

Every model block is optional in ``metrics.json``, so the endpoint degrades in
three different ways on purpose: no artifact at all returns an empty payload with
a note, a missing model block leaves that list empty with a note, and a fairness
gap outside the target is published rather than hidden. None of them is a 500,
and none of them is an empty list with no explanation -- an empty table reads as
"measured, nothing found", which is the one reading that must never be wrong.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from ..config import Settings, get_settings
from ..deps import CurrentUser
from ..schemas import MetricsResponse
from ..services import metrics_service

router = APIRouter(tags=["metrics"])

_response_adapter = TypeAdapter(MetricsResponse)


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Held-out model metrics, baselines, fairness gaps and impact notes",
)
def get_metrics(
    user_id: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> MetricsResponse:
    """Model evaluation as measured offline. Read-only, and it trains nothing."""
    if not settings.feature_metrics:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="the metrics page is switched off (FEATURE_METRICS=0)",
        )
    return _response_adapter.validate_python(
        metrics_service.build_metrics(
            settings.artifact_path,
            feedback_path=settings.feedback_path,
            request_log_path=settings.request_log_file,
        )
    )
