"""Savings-solver tests (Phase 3): feasible = surplus − buffer, always honest.

The solver is pure rules — no model, no database — so these tests pin the
arithmetic directly: feasibility, the buffer formula, the three trade-offs
plus do-nothing, and the validation errors.
"""

from __future__ import annotations

import pytest

from backend.rules import savings_solver


def test_feasible_plan_keeps_the_buffer() -> None:
    solved = savings_solver.solve(
        goal_bdt=30000, months=6,
        monthly_surplus_bdt=8600, monthly_outflow_bdt=24000, monthly_fee_bdt=320,
    )
    assert solved.feasible is True
    assert solved.required_monthly_bdt == pytest.approx(5000.0)
    assert solved.safety_buffer_bdt == pytest.approx(2400.0)  # 3 days of outflow
    assert solved.feasible_monthly_bdt == pytest.approx(8600 - 2400)
    assert len(solved.arithmetic) == 4
    assert "required monthly" in solved.arithmetic[0]
    assert "day(s)" in solved.arithmetic[1]


def test_infeasible_goal_says_so() -> None:
    solved = savings_solver.solve(
        goal_bdt=30000, months=6,
        monthly_surplus_bdt=5000, monthly_outflow_bdt=24000, monthly_fee_bdt=320,
    )
    assert solved.feasible is False
    assert solved.arithmetic[-1].startswith("not feasible")


def test_three_trade_offs_and_do_nothing_always_ship() -> None:
    solved = savings_solver.solve(
        goal_bdt=30000, months=6,
        monthly_surplus_bdt=5000, monthly_outflow_bdt=24000, monthly_fee_bdt=320,
    )
    kinds = [item.kind for item in solved.trade_offs]
    assert kinds == ["smaller_goal", "longer_time", "spending_lever", "do_nothing"]
    assert solved.do_nothing is not None
    assert solved.do_nothing["estimated_cost_bdt"] == pytest.approx(320 * 6)
    assert solved.do_nothing["horizon_months"] == 6


def test_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        savings_solver.solve(goal_bdt=0, months=6, monthly_surplus_bdt=5000, monthly_outflow_bdt=20000)
    with pytest.raises(ValueError):
        savings_solver.solve(goal_bdt=30000, months=0, monthly_surplus_bdt=5000, monthly_outflow_bdt=20000)


def test_negative_surplus_is_treated_as_zero() -> None:
    solved = savings_solver.solve(
        goal_bdt=30000, months=6,
        monthly_surplus_bdt=-100, monthly_outflow_bdt=20000,
    )
    assert solved.feasible is False
    assert solved.feasible_monthly_bdt == 0.0


def test_a_bigger_buffer_can_only_make_the_plan_harder() -> None:
    """The cushion is money kept aside, so more of it can never add feasibility."""
    tight = savings_solver.solve(
        goal_bdt=30000, months=6,
        monthly_surplus_bdt=8000, monthly_outflow_bdt=24000, buffer_days=1,
    )
    loose = savings_solver.solve(
        goal_bdt=30000, months=6,
        monthly_surplus_bdt=8000, monthly_outflow_bdt=24000, buffer_days=7,
    )
    assert loose.safety_buffer_bdt > tight.safety_buffer_bdt
    assert loose.feasible_monthly_bdt <= tight.feasible_monthly_bdt


def test_goal_is_split_across_the_months_exactly() -> None:
    solved = savings_solver.solve(
        goal_bdt=30000, months=7,
        monthly_surplus_bdt=9000, monthly_outflow_bdt=24000,
    )
    assert solved.required_monthly_bdt == pytest.approx(30000 / 7)


def test_no_room_never_offers_a_zero_goal_or_the_same_timeline() -> None:
    """With no monthly room, the goal-shaping trade-offs must not fake a number.

    ``aim for 0`` and ``stretch to 6 months`` for a 6-month goal read as advice
    but are meaningless, so both degrade to an honest "not this way".
    """
    solved = savings_solver.solve(
        goal_bdt=30000, months=6,
        monthly_surplus_bdt=2483.30, monthly_outflow_bdt=37060.80, monthly_fee_bdt=320,
    )
    assert solved.feasible is False
    assert solved.feasible_monthly_bdt == 0.0
    by_kind = {item.kind: item for item in solved.trade_offs}
    assert by_kind["smaller_goal"].goal_bdt is None
    assert by_kind["smaller_goal"].months is None
    assert "0" not in by_kind["smaller_goal"].description
    assert by_kind["longer_time"].months is None
    assert "6" not in by_kind["longer_time"].description
    # the spending lever is then the only real option, so it must state the gap
    assert "5,000" in by_kind["spending_lever"].description


def test_timeline_trade_off_never_shortens_the_requested_time() -> None:
    """A feasible 6-month plan must not be "improved" into 5 months."""
    solved = savings_solver.solve(
        goal_bdt=30000, months=6,
        monthly_surplus_bdt=8600, monthly_outflow_bdt=24000,
    )
    longer = next(item for item in solved.trade_offs if item.kind == "longer_time")
    smaller = next(item for item in solved.trade_offs if item.kind == "smaller_goal")
    assert solved.feasible is True
    assert longer.months == 6
    assert "no extra time" in longer.description
    assert smaller.months == 6
    assert smaller.goal_bdt == pytest.approx(6200 * 6)


def test_timeline_trade_off_extends_when_the_goal_is_too_big() -> None:
    """6,200/month reaches 30,000 in 5 months, but the user asked for 6 — so with
    a tight-but-real budget the solver must stretch past the request, never below it."""
    solved = savings_solver.solve(
        goal_bdt=30000, months=3,
        monthly_surplus_bdt=8600, monthly_outflow_bdt=24000,
    )
    longer = next(item for item in solved.trade_offs if item.kind == "longer_time")
    assert longer.months == 5  # ceil(30,000 / 6,200) = 5, which is more than the 3 asked
    assert "5 months" in longer.description

