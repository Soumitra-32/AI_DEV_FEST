"""Savings-plan endpoint (Phase 3).

Same thin shape as ``/forecast``: auth -> flag -> service -> schema. The
solver's verdict, trade-offs and do-nothing cost are computed in
``plan_service``; this module only validates them against the contract.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from ..config import Settings, get_settings
from ..deps import CurrentUser
from ..schemas import (
    DoNothingOutcome,
    SavingsPlanRequest,
    SavingsPlanResponse,
    TradeOffOption,
)
from ..services import plan_service

router = APIRouter(tags=["savings-plan"])

_tradeoff_adapter = TypeAdapter(TradeOffOption)
_do_nothing_adapter = TypeAdapter(DoNothingOutcome)

#: Solver kinds -> the frozen contract's action vocabulary.
_ACTION_BY_KIND = {
    "smaller_goal": "reduce",
    "longer_time": "delay",
    "spending_lever": "switch",
    "do_nothing": "do_nothing",
}


def _pressure_dates(raw: list[object]) -> list[date_type]:
    """Coerce the service's ISO date strings to ``date`` for the contract."""
    out: list[date_type] = []
    for item in raw:
        out.append(date_type.fromisoformat(str(item)))
    return out


@router.post("/savings-plan", response_model=SavingsPlanResponse, summary="Feasible savings plan")
def get_plan(
    body: SavingsPlanRequest,
    user_id: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SavingsPlanResponse:
    """Solve the savings plan from the forecast surplus for the caller's user."""
    if not settings.feature_savings_plan:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="savings plan is switched off (FEATURE_SAVINGS_PLAN=0)",
        )
    try:
        payload = plan_service.build_plan(
            user_id, goal_bdt=body.goal_bdt, months=body.months, db_path=settings.db_path
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    trade_offs = [
        _tradeoff_adapter.validate_python({
            "action": _ACTION_BY_KIND.get(item["kind"], "reduce"),
            "title": item["description"],
            "description": item["description"],
            "months": item.get("months"),
            "target_bdt": item.get("goal_bdt"),
            "monthly_amount_bdt": item.get("monthly_bdt"),
            "monthly_effect_bdt": None,
        })
        for item in payload["trade_offs"]
        if item["kind"] != "do_nothing"
    ]
    return SavingsPlanResponse(
        user_id=user_id,
        goal_bdt=payload["goal_bdt"],
        months=payload["months"],
        feasible=payload["feasible"],
        required_monthly_bdt=payload["required_monthly_bdt"],
        forecasted_surplus_bdt=payload["forecasted_surplus_bdt"],
        safety_buffer_bdt=payload["safety_buffer_bdt"],
        feasible_monthly_bdt=payload["feasible_monthly_bdt"],
        arithmetic=payload["arithmetic"],
        trade_offs=trade_offs,
        do_nothing=_do_nothing_adapter.validate_python(payload["do_nothing"]),
        pressure_days=_pressure_dates(payload["pressure_days"]),
        provenance=payload["provenance"],
    )


