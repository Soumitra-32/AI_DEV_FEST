"""Financial Health Coach endpoint: ``GET /health-coach``.

Thin by design -- auth -> feature flag -> service -> frozen schema -- like every
other router here. The score, the Bangla summary and the per-factor arithmetic
come from :mod:`backend.app.services.health_service`, which reads the pure rule
module :mod:`backend.rules.health_score`. This file holds no arithmetic.

The number here is a coaching reading of behaviour in 0-100, never a credit
score and never a lending decision; that guarantee travels in the payload.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from ..config import Settings, get_settings
from ..deps import CurrentUser
from ..schemas import HealthCoachResponse
from ..services import health_service

router = APIRouter(tags=["health-coach"])

_response_adapter = TypeAdapter(HealthCoachResponse)


@router.get(
    "/health-coach",
    response_model=HealthCoachResponse,
    summary="0-100 financial health reading with its Bangla summary and factors",
)
def get_health_coach(
    user_id: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthCoachResponse:
    """The caller's health reading. Derived from their own ledger, never a grade."""
    if not settings.feature_health_coach:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="the health coach is switched off (FEATURE_HEALTH_COACH=0)",
        )
    try:
        payload = health_service.build_health(user_id, db_path=settings.db_path)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _response_adapter.validate_python(payload)
