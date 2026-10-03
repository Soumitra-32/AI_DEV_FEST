"""Savings-plan solver (rules layer): feasible = surplus − buffer.

Takes the 14-day forecast's monthly surplus and answers the demo question
"can I save ৳30,000 in 6 months" with honest arithmetic:

* ``forecasted_surplus_bdt`` — monthly surplus from the forecast (scaled from
  the 14-day mean net, stated as an assumption);
* ``safety_buffer_bdt`` — a few days of typical outflow, so the plan survives
  the month-end squeeze (never invented by the LLM — computed here);
* ``feasible_monthly_bdt`` — what is left after the buffer;
* ``feasible`` — required ≤ feasible;
* three trade-offs always ship with the verdict (smaller goal, longer time,
  spending lever), plus the do-nothing cost (fees the user keeps paying).

The LLM (Phase 4) only verbalises these numbers; it never computes them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TradeOff:
    kind: str  # "smaller_goal" | "longer_time" | "spending_lever" | "do_nothing"
    description: str
    monthly_bdt: float | None = None
    goal_bdt: float | None = None
    months: int | None = None


@dataclass(frozen=True)
class SavingsPlan:
    feasible: bool
    required_monthly_bdt: float
    forecasted_surplus_bdt: float
    safety_buffer_bdt: float
    feasible_monthly_bdt: float
    arithmetic: list[str] = field(default_factory=list)
    trade_offs: list[TradeOff] = field(default_factory=list)
    do_nothing: dict | None = None


def _round2(value: float) -> float:
    return round(float(value), 2)


def solve(
    goal_bdt: float,
    months: int,
    monthly_surplus_bdt: float,
    monthly_outflow_bdt: float,
    monthly_fee_bdt: float = 0.0,
    buffer_days: float = 3.0,
) -> SavingsPlan:
    """Solve the savings plan from forecasted (not averaged) surplus.

    ``buffer_days`` is how many days of the user's typical outflow we insist on
    keeping in the wallet. Three days is the month-end squeeze window this
    product is about: long enough to absorb the pressure days the forecast
    flags, short enough that it does not silently eat a whole week of a daily
    wage earner's income.
    """
    if goal_bdt <= 0:
        raise ValueError("goal_bdt must be positive")
    if months < 1:
        raise ValueError("months must be >= 1")
    if monthly_surplus_bdt < 0:
        monthly_surplus_bdt = 0.0

    required = float(goal_bdt) / int(months)
    buffer_days = max(float(buffer_days), 0.0)
    safety_buffer = max(float(monthly_outflow_bdt) * buffer_days / 30.0, 0.0)
    feasible_monthly = max(float(monthly_surplus_bdt) - safety_buffer, 0.0)
    feasible = required <= feasible_monthly

    arithmetic = [
        f"required monthly = {goal_bdt:,.0f} / {months} = {required:,.2f}",
        f"safety buffer = {buffer_days:g} day(s) of typical outflow = {safety_buffer:,.2f}",
        f"feasible monthly = surplus {monthly_surplus_bdt:,.2f} - buffer {safety_buffer:,.2f} = {feasible_monthly:,.2f}",
        "feasible" if feasible else "not feasible with the buffer kept",
    ]

    # ``feasible_monthly`` is 0 when the buffer already eats the whole surplus.
    # In that case "aim for 0" and "stretch to the same N months" are not
    # options — they are nonsense that would read as advice. The two goal-shaping
    # trade-offs say so plainly and the spending lever carries the real number.
    has_room = feasible_monthly > 0
    smaller_goal = feasible_monthly * months
    # The timeline trade-off is "take longer", so it may never come back shorter
    # than what the user asked for: a feasible plan simply needs no extension.
    longer_time = (
        max(int(math.ceil(goal_bdt / feasible_monthly)), months) if has_room else None
    )
    lever_gap = max(required - feasible_monthly, 0.0)

    if not has_room:
        smaller_description = (
            "With the buffer kept there is no monthly room to save from — "
            "the goal is out of reach in this form."
        )
        longer_description = (
            f"Waiting longer does not help here: even {months * 2} months leaves "
            "nothing to set aside each month. Free up monthly cash first."
        )
    elif feasible:
        # The goal already fits: "reduce to a BIGGER number" would be nonsense,
        # so both goal-shaping trade-offs say plainly that no change is needed.
        smaller_description = (
            f"Keep {months} months and the full {goal_bdt:,.0f} — it already "
            f"fits in {_round2(feasible_monthly):,.0f}/month of room."
        )
        longer_description = (
            f"The goal already fits in {months} months — no extra time is needed."
        )
    elif longer_time <= months:
        smaller_description = (
            f"Keep {months} months and aim for {_round2(smaller_goal):,.0f} instead."
        )
        longer_description = (
            f"The goal already fits in {months} months — no extra time is needed."
        )
    else:
        smaller_description = (
            f"Keep {months} months and aim for {_round2(smaller_goal):,.0f} instead."
        )
        longer_description = (
            f"Keep the {goal_bdt:,.0f} goal and stretch to {longer_time} months."
        )

    # Three trade-offs ride with the verdict; the do-nothing cost lives in
    # ``do_nothing`` below (it is a cost of inaction, not a plan variant).
    # When the goal already fits, the goal-shaping options point at the goal
    # itself — never at a bigger number dressed up as a reduction.
    shaped_goal = _round2(float(goal_bdt)) if feasible else None
    shaped_months = months if feasible else None
    trade_offs = [
        TradeOff(
            kind="smaller_goal",
            description=smaller_description,
            goal_bdt=shaped_goal if feasible else (_round2(smaller_goal) if has_room else None),
            months=shaped_months if feasible else (months if has_room else None),
            monthly_bdt=_round2(feasible_monthly),
        ),
        TradeOff(
            kind="longer_time",
            description=longer_description,
            goal_bdt=_round2(float(goal_bdt)),
            months=longer_time,
            monthly_bdt=_round2(feasible_monthly),
        ),
        TradeOff(
            kind="spending_lever",
            description=(
                f"Free up {lever_gap:,.0f}/month (e.g. fewer cash-outs) to make the plan fit."
                if lever_gap > 0 else "No spending cut needed — the plan already fits."
            ),
            monthly_bdt=_round2(feasible_monthly),
        ),
        TradeOff(
            kind="do_nothing",
            description=f"Change nothing and keep paying about {float(monthly_fee_bdt):,.0f}/month in fees.",
        ),
    ]
    do_nothing = {
        "description": "No change to saving or cash-out habits.",
        "estimated_cost_bdt": _round2(float(monthly_fee_bdt) * months),
        "horizon_months": months,
    }
    return SavingsPlan(
        feasible=feasible,
        required_monthly_bdt=_round2(required),
        forecasted_surplus_bdt=_round2(float(monthly_surplus_bdt)),
        safety_buffer_bdt=_round2(safety_buffer),
        feasible_monthly_bdt=_round2(feasible_monthly),
        arithmetic=arithmetic,
        trade_offs=trade_offs,
        do_nothing=do_nothing,
    )

