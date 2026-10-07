"""Telemetry endpoint: ``POST /events`` (Product events for customer impact).

Accepts structured product telemetry events:
- forecast_viewed
- savings_plan_viewed
- savings_plan_created
- recommendation_shown
- recommendation_accepted
- recommendation_rejected
- recommendation_action_completed
- recommendation_feedback
- anomaly_viewed
- copilot_used
- feedback_submitted

Security & privacy:
- Requires authenticated user via demo token header.
- user_id is never accepted from body; it is resolved server-side and hashed with salt.
- Properties are sanitized to strip any transaction details or PII.
- Written to append-only events.jsonl beside metrics.json.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from ..config import Settings, get_settings
from ..deps import CurrentUser
from ..schemas import ProductEventRequest, ProductEventResponse
from ..services import feedback_service

router = APIRouter(tags=["events"])

_response_adapter = TypeAdapter(ProductEventResponse)


@router.post(
    "/events",
    response_model=ProductEventResponse,
    summary="Record a structured product event for customer-impact measurement",
)
def post_event(
    body: ProductEventRequest,
    user_id: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProductEventResponse:
    """Append one structured product telemetry event to the events store."""
    if not settings.feature_events:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="product telemetry event tracking is switched off (FEATURE_EVENTS=0)",
        )
    try:
        stored = feedback_service.record_event(
            user_id,
            event_type=body.event_type,
            feature=body.feature,
            recommendation_id=body.recommendation_id,
            properties=body.properties,
            salt=settings.feedback_salt,
            path=settings.events_path,
        )
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"events store is not writable: {exc}",
        ) from exc

    return _response_adapter.validate_python(
        {
            "status": "recorded",
            "recorded_at": stored["recorded_at"],
            "respondent": stored["respondent"],
            "event_type": stored["event_type"],
            "feature": stored["feature"],
            "recommendation_id": stored["recommendation_id"],
            "properties": stored["properties"],
        }
    )
