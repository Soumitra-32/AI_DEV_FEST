"""Savings-plan service: forecast surplus shaped into the frozen plan contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.rules import savings_solver

from . import forecast_service


def build_plan(
    user_id: str,
    goal_bdt: float,
    months: int,
    db_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Solve the plan from the forecast's monthly surplus (never a raw average)."""
    outlook = forecast_service.build_forecast(
        user_id, horizon_days=14, include_pressure_days=True,
        db_path=db_path, artifact_dir=artifact_dir,
    )
    solved = savings_solver.solve(
        goal_bdt=float(goal_bdt),
        months=int(months),
        monthly_surplus_bdt=outlook["monthly_net"],
        monthly_outflow_bdt=outlook["monthly_outflow"],
        monthly_fee_bdt=outlook["monthly_fees"],
        buffer_days=forecast_service.SAFETY_BUFFER_DAYS,
    )
    feasible_text = (
        f"{goal_bdt:,.0f} in {months} months needs {solved.required_monthly_bdt:,.0f}/month; "
        f"you can keep about {solved.feasible_monthly_bdt:,.0f}/month after the buffer."
    )
    if solved.feasible:
        prediction = f"Feasible: {feasible_text}"
        explanation = "The forecast covers the goal with the safety buffer kept."
    else:
        prediction = f"Not feasible as stated: {feasible_text}"
        explanation = "Pick a trade-off below, or free up monthly cash to close the gap."
    return {
        "goal_bdt": float(goal_bdt),
        "months": int(months),
        "feasible": solved.feasible,
        "required_monthly_bdt": solved.required_monthly_bdt,
        "forecasted_surplus_bdt": solved.forecasted_surplus_bdt,
        "safety_buffer_bdt": solved.safety_buffer_bdt,
        "feasible_monthly_bdt": solved.feasible_monthly_bdt,
        "arithmetic": list(solved.arithmetic),
        "trade_offs": [
            {
                "kind": item.kind,
                "description": item.description,
                "monthly_bdt": item.monthly_bdt,
                "goal_bdt": item.goal_bdt,
                "months": item.months,
            }
            for item in solved.trade_offs
        ],
        "do_nothing": dict(solved.do_nothing or {}),
        "pressure_days": outlook["pressure_days"],
        "provenance": {
            "prediction": prediction,
            "assumption": (
                "Monthly surplus is the 14-day forecast scaled to a month; "
                f"the buffer keeps {forecast_service.SAFETY_BUFFER_DAYS:g} days of "
                "typical spending in the wallet."
            ),
            "explanation": explanation,
            "source": outlook["provenance"]["source"],
        },
    }

