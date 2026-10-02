"""Anomalies endpoint (Phase 5): the Spending Companion card.

Thin by design — auth -> feature flag -> service -> frozen schema — like every
other router here. The interesting work lives in
:mod:`backend.app.services.anomaly_service` (model ranking + fee switch), which in
turn reads the already-tested :mod:`backend.ml.anomaly` and
:mod:`backend.rules.fee_switch`.

The ``user_id`` always comes from the demo token, never from the body, so one user
cannot ask about another's spending.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from ..config import Settings, get_settings
from ..deps import CurrentUser
from ..schemas import (
    AnomalyItem,
    AnomalyRequest,
    AnomalyResponse,
    FeeSwitchSuggestion,
    Provenance,
)
from ..services import anomaly_service

router = APIRouter(tags=["anomalies"])

_item_adapter = TypeAdapter(AnomalyItem)
_switch_adapter = TypeAdapter(FeeSwitchSuggestion)


@router.post(
    "/anomalies",
    response_model=AnomalyResponse,
    summary="Unusual payments for this user, plus the cash-out fee to switch",
)
def get_anomalies(
    body: AnomalyRequest,
    user_id: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnomalyResponse:
    """Rank the caller's recent payments and price the cash-out habit."""
    if not settings.feature_anomalies:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="anomalies are switched off (FEATURE_ANOMALIES=0)",
        )
    try:
        payload = anomaly_service.build_anomalies(
            user_id,
            window_days=body.window_days,
            limit=body.limit,
            db_path=settings.db_path,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    switch = payload["fee_switch"]
    return AnomalyResponse(
        user_id=user_id,
        window_days=payload["window_days"],
        items=[_item_adapter.validate_python(item) for item in payload["items"]],
        fee_switch=_switch_adapter.validate_python(switch) if switch else None,
        provenance=Provenance(**payload["provenance"]),
    )

