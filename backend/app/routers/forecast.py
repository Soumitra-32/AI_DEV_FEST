"""Forecast endpoint (Phase 3).

Thin by design: auth -> feature flag -> service -> frozen schema. All math
lives in ``backend.ml`` / ``backend.rules`` via ``forecast_service``; this
module only maps the payload onto ``ForecastResponse``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from ..config import Settings, get_settings
from ..deps import CurrentUser
from ..schemas import DayForecast, ForecastRequest, ForecastResponse
from ..services import forecast_service

router = APIRouter(tags=["forecast"])

_day_adapter = TypeAdapter(DayForecast)


def _disabled() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="forecast is switched off (FEATURE_FORECAST=0)",
    )


@router.post("/forecast", response_model=ForecastResponse, summary="14-day cash-flow forecast")
def get_forecast(
    body: ForecastRequest,
    user_id: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ForecastResponse:
    """Serve the LightGBM forecast plus pressure days for the caller's user."""
    if not settings.feature_forecast:
        raise _disabled()
    try:
        payload = forecast_service.build_forecast(
            user_id,
            horizon_days=body.horizon_days,
            include_pressure_days=body.include_pressure_days,
            db_path=settings.db_path,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    days = [_day_adapter.validate_python(item) for item in payload["days"]]
    return ForecastResponse(
        user_id=user_id,
        horizon_days=body.horizon_days,
        generated_at=datetime.now(timezone.utc),
        generated_from=payload["generated_from"],
        days=days,
        pressure_days=payload["pressure_days"],
        metrics=payload["metrics"],
        provenance=payload["provenance"],
    )


