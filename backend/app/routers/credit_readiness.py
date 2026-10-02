"""Consistency-signal endpoint (Phase 7): ``POST /signal``.

Thin by design -- auth -> feature flag -> service -> frozen schema -- like every
other router here. The band is produced by :mod:`backend.app.services.signal_service`
from the trained model in :mod:`backend.ml.signal`, and the "this is not a loan
decision" banner travels in the payload rather than being left to the frontend.

The ``user_id`` comes from the demo token, never from the body, so one user cannot
ask about another's signal.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from ..config import Settings, get_settings
from ..deps import CurrentUser
from ..schemas import ConsistencySignalResponse
from ..services import signal_service

router = APIRouter(tags=["signal"])

_response_adapter = TypeAdapter(ConsistencySignalResponse)


@router.post(
    "/signal",
    response_model=ConsistencySignalResponse,
    summary="Consistency band for this user, with its strongest factors",
)
def get_signal(
    user_id: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
    language: str = "bn",
) -> ConsistencySignalResponse:
    """The caller's consistency band. Never a score, never a lending decision."""
    if not settings.feature_signal:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="the consistency signal is switched off (FEATURE_SIGNAL=0)",
        )
    try:
        payload = signal_service.build_signal(
            user_id,
            language=language,
            db_path=settings.db_path,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _response_adapter.validate_python(payload)