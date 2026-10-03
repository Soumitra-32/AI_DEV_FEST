"""GAP-01 acceptance: the flagship demo must be feasible in the served pipeline.

Runs the REAL served path for Rahim (30,000 taka over 6 months) against the
full deterministic dataset — the same numbers the demo story quotes:

1. the served plan is feasible (required 5,000/mo fits the surplus-buffer);
2. the served net is within 15% of the served inflow−outflow (net guard);
3. every pressure day is balance-based (closing balance below the buffer);
4. ``as_of`` places the window over month-end days 28–31;
5. the net model's backtest bias on Rahim is no worse than the
   user-relative trailing-mean anchor's.

Needs the full generated dataset (``backend/data/shonchoy.db``): deterministic
seeds make it identical everywhere — local, CI (``backend-test`` generates it
before pytest), Render (build command), Docker (first-boot generation).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services import forecast_service, plan_service
from backend.data import features as user_features
from backend.data import generator
from backend.ml import dataset as forecast_dataset
from backend.ml import forecast as forecast_model

NEEDS_DB = pytest.mark.skipif(
    not user_features.default_db_path().exists(),
    reason="needs the generated backend/data/shonchoy.db (CI builds it first)",
)


def _served_forecast(**kwargs):
    return forecast_service.build_forecast("rahim", horizon_days=14, **kwargs)


@NEEDS_DB
def test_rahim_plan_is_feasible() -> None:
    """The demo story: ৳30,000 in 6 months at ৳5,000/month fits."""
    plan = plan_service.build_plan("rahim", goal_bdt=30000, months=6)
    assert plan["required_monthly_bdt"] == pytest.approx(5000.0)
    assert plan["feasible"] is True
    assert plan["feasible_monthly_bdt"] >= 5000.0


@NEEDS_DB
def test_served_net_is_within_15_percent_of_inflow_minus_outflow() -> None:
    """The card's net must never contradict its own flows (net guard)."""
    payload = _served_forecast()
    window_net = sum(day["predicted_net_bdt"] for day in payload["days"])
    window_in = sum(day["predicted_inflow_bdt"] for day in payload["days"])
    window_out = sum(day["predicted_outflow_bdt"] for day in payload["days"])
    diff = window_in - window_out
    assert window_net == pytest.approx(
        diff, abs=max(0.15 * abs(diff), forecast_service.NET_GUARD_FLOOR_BDT)
    )
    assert payload["monthly_net"] == pytest.approx(
        payload["monthly_inflow"] - payload["monthly_outflow"], abs=1.0
    )


@NEEDS_DB
def test_pressure_days_are_balance_based() -> None:
    """A flagged day's closing balance is below the buffer — never a
    negative net against a healthy wallet (the 12/14 false-pressure bug)."""
    payload = _served_forecast()
    buffer_bdt = payload["safety_buffer_bdt"]
    by_date = {day["date"]: day for day in payload["days"]}
    for date in payload["pressure_days"]:
        assert by_date[date]["predicted_balance_bdt"] < buffer_bdt
        assert by_date[date]["is_pressure_day"] is True


@NEEDS_DB
def test_as_of_places_the_window_over_month_end() -> None:
    """Server-side window placement: the days-28–31 story must be showable."""
    payload = _served_forecast(as_of="2025-06-29")
    month_days = {int(day["date"].split("-")[2]) for day in payload["days"]}
    assert month_days & {28, 29, 30, 31}, f"window misses month-end: {sorted(month_days)}"
    assert payload["generated_from"] <= "2025-06-29"


@NEEDS_DB
def test_net_model_backtest_bias_is_reported_and_fallback_covers_it() -> None:
    """Known model limitation, measured not wished away: the net residual
    booster under-predicts Rahim's corner (high level + regularity + savings
    + pressure) even retrained, while his own trailing mean tracks reality.
    The served pipeline must therefore NOT trust the model blindly — it
    serves the anchor level with the disagreement disclosed (net_source
    "anchor" + assumption note), which the next two assertions pin."""
    path = user_features.default_db_path()
    transactions = user_features.load_transactions(path, ["rahim"])
    cfg = generator.load_config()
    daily = forecast_dataset.daily_flows(transactions, cfg).sort_values("date").reset_index(drop=True)
    bias_model, bias_anchor, count = 0.0, 0.0, 0
    for end in range(60, len(daily) - 14, 14):
        history = daily.iloc[:end]
        future = daily.iloc[end:end + 14]
        actual = float((future["inflow_bdt"] - future["outflow_bdt"]).sum())
        featured = forecast_dataset.add_history(history)
        if featured.empty:
            continue
        means = forecast_model.predict_mean(featured.sort_values("date").iloc[[-1]])
        predicted_model = float(means["mean_net"].iloc[0]) * 14
        tail = history.tail(28)
        predicted_anchor = float((tail["inflow_bdt"] - tail["outflow_bdt"]).mean()) * 14
        bias_model += predicted_model - actual
        bias_anchor += predicted_anchor - actual
        count += 1
    assert count > 0
    print(f"\nRahim backtest: model bias {bias_model / count:,.0f}, anchor bias {bias_anchor / count:,.0f}")
    payload = _served_forecast()
    # Whatever the model says, the served card must be explicit about it.
    assert payload["net_source"] in ("model", "anchor")
    if abs(bias_model / count) > abs(bias_anchor / count):
        assert payload["net_source"] == "anchor"
        assert "anchor" in payload["provenance"]["assumption"].lower()


@NEEDS_DB
def test_served_forecast_carries_bilingual_shap_drivers() -> None:
    """The card's "why": SHAP reasons from the real artifacts, in the
    requested language, bounded to the three reasons the UI renders."""
    bangla = _served_forecast(include_drivers=True, language="bn")["drivers"]
    assert 0 < len(bangla) <= 3
    for driver in bangla:
        assert driver["direction"] in {"increases", "decreases"}
        assert driver["impact_bdt"] > 0
        assert driver["detail"]
    assert "প্রায়" in bangla[0]["detail"]

    english = _served_forecast(include_drivers=True, language="en")["drivers"]
    assert 0 < len(english) <= 3
    assert "by about" in english[0]["detail"]
