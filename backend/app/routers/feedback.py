"""Feedback endpoint: ``POST /feedback`` (the "was this helpful?" loop).

Thin by design -- auth -> feature flag -> service -> frozen schema. The record
is written by :mod:`backend.app.services.feedback_service` to the same artifacts
directory as ``metrics.json``, so the loop closes without a second datastore.

The ``user_id`` comes from the demo token, never the body, and the service
stores only a salted hash of it. Any comment text is discarded on purpose; the
response says exactly which fields were stored.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from ..config import Settings, get_settings
from ..deps import CurrentUser
from ..schemas import FeedbackRequest, FeedbackResponse
from ..services import feedback_service

router = APIRouter(tags=["feedback"])

_response_adapter = TypeAdapter(FeedbackResponse)


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Record a 'was this helpful?' tap (no PII stored)",
)
def post_feedback(
    body: FeedbackRequest,
    user_id: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> FeedbackResponse:
    """Append one anonymised feedback record to the metrics store."""
    if not settings.feature_feedback:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="the feedback loop is switched off (FEATURE_FEEDBACK=0)",
        )
    try:
        stored = feedback_service.record(
            user_id,
            surface=body.surface,
            helpful=body.helpful,
            intent=body.intent,
            comment=body.comment,
            salt=settings.feedback_salt,
            path=settings.feedback_path,
        )
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"feedback store is not writable: {exc}",
        ) from exc
    return _response_adapter.validate_python(
        {
            "status": "recorded",
            "recorded_at": stored["recorded_at"],
            "respondent": stored["respondent"],
            "surface": stored["surface"],
            "helpful": stored["helpful"],
            "stored_fields": list(feedback_service.STORED_FIELDS),
        }
    )
