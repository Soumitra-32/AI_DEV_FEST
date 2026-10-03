"""Forecast service: model predictions shaped into the frozen API contract.

Serving path: last-28-day history -> LightGBM 14-day means -> calendar
spread -> per-day rows + pressure days. Falls back to the trailing-average
shape when artifacts are missing, so the API degrades instead of failing
(the provenance ``source`` says which path served the request).
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from backend.data import features as user_features
from backend.data import generator
from backend.ml import dataset as forecast_dataset
from backend.ml import evaluate as forecast_evaluate
from backend.ml import explain as ml_explain
from backend.ml import forecast as forecast_model
from backend.rules import pressure_days as pressure_rules

SAFETY_BUFFER_DAYS = 3.0
METRICS_FILE = forecast_evaluate.METRICS_FILE

#: GAP-01 guard: the served window net must stay consistent with the served
#: flows. The net model is biased for earners outside the training support
#: (Rahim: residual ≈ −৳400/day against his own trailing mean, backtest bias
#: −৳5.4k/14d vs anchor −৳0.2k, confirmed across two retrains), so when the
#: model disagrees with the user's own flows beyond tolerance the trailing
#: 28-day anchor level is served instead — with model weekday shapes, and the
#: provenance says so. Anchors are mutually consistent by construction
#: (mean(net) == mean(inflow) − mean(outflow)), so the card always agrees
#: with itself. The tolerance floor keeps near-zero nets from flip-flopping.
NET_GUARD_TOLERANCE = 0.15
NET_GUARD_FLOOR_BDT = 500.0

#: Second, independent guard trigger, and the one that actually catches the
#: failure the tolerance check cannot see. ``model_total`` vs ``diff_total``
#: compares the net booster against the inflow and outflow boosters, and all
#: three are anchored on the *same* trailing mean and fitted on the same rows —
#: so they can agree with each other perfectly while sharing one wrong level.
#: Measured on the shipped artifacts: the net model's gap to
#: inflow−outflow is only ৳108 over the window (well inside tolerance) while its
#: 14-day level error against Rahim's actuals is −৳5.7k against the anchor's
#: −৳0.2k. The only way to see that is to score the model against reality, so
#: the guard rolls the net model over the user's own history and serves the
#: anchor when the model's level error is the larger of the two.
NET_LEVEL_BACKTEST_MIN_ORIGINS = 3

#: How much better than the anchor the model has to be before its level is
#: trusted. Zero would flip on noise; a small positive margin means "the model
#: must actually beat the naive answer on this user", which is the claim the
#: card makes when it serves a model number.
NET_LEVEL_REQUIRED_IMPROVEMENT = 0.0


def _metrics_block(artifact_dir: str | Path) -> Optional[dict[str, Any]]:
    """The trained model's held-out accuracy, for the ``/metrics`` card.

    Read from the evaluation written by ``backend/scripts/train_all.py`` so the
    API reports the number the offline run measured instead of recomputing one.
    """
    path = Path(artifact_dir) / METRICS_FILE
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        outflow = payload["cumulative"]["outflow"]
        baseline = min(
            forecast_evaluate.baselines.BASELINE_NAMES,
            key=lambda name: outflow[name]["mae"],
        )
        net = payload["cumulative"].get("net")
    except (KeyError, ValueError, OSError):
        return None
    block = {
        "model_name": "lightgbm_14d_mean",
        "mae_bdt": outflow["model"]["mae"],
        "rmse_bdt": outflow["model"]["rmse"],
        "baseline_name": baseline,
        "baseline_mae_bdt": outflow[baseline]["mae"],
        "improvement_pct": outflow["improvement_over_best_pct"],
    }
    if net:
        # net is the number the plan is solved from, so its own accuracy is
        # reported beside the flow metrics rather than being left implicit
        block["net_mae_bdt"] = net["model"]["mae"]
        block["net_baseline_name"] = min(
            forecast_evaluate.baselines.BASELINE_NAMES,
            key=lambda name: net[name]["mae"],
        )
        block["net_improvement_pct"] = net["improvement_over_best_pct"]
        block["net_source"] = payload.get("net_source", "difference")
    return block


def _month_scale(transactions: pd.DataFrame) -> dict[str, float]:
    """Scale observed daily means to a month (from this user's history)."""
    frame = transactions.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    days = int(frame["timestamp"].dt.normalize().nunique()) or 1
    is_income = frame["type"].eq("income")
    inflow = float(frame.loc[is_income, "amount_bdt"].sum())
    outflow = float(frame.loc[~frame["type"].eq("income"), "amount_bdt"].sum())
    fees = float(frame["fee_bdt"].sum())
    return {
        "monthly_inflow": inflow / days * 30.0,
        "monthly_outflow": outflow / days * 30.0,
        "monthly_fees": fees / days * 30.0,
        "monthly_net": (inflow - outflow - fees) / days * 30.0,
    }


def _last_feature_row(daily: pd.DataFrame):
    featured = forecast_dataset.add_history(daily)
    if featured.empty:
        raise ValueError("not enough history to forecast (need 28 days)")
    last = featured.sort_values("date").iloc[[-1]]
    return last, pd.to_datetime(last["date"].iloc[0])


def _opening_balance(transactions: pd.DataFrame) -> float:
    frame = transactions.sort_values("timestamp")
    if frame.empty:
        return 0.0
    return float(frame["balance_after"].iloc[-1])



def _net_level_check(
    daily: pd.DataFrame,
    boosters: Any,
    horizon_days: int = forecast_model.HORIZON_DAYS,
    min_origins: int = NET_LEVEL_BACKTEST_MIN_ORIGINS,
) -> Optional[tuple[float, float, int]]:
    """Roll the net model over this user's own history, goalpost-by-goalpost.

    Walks the user's calendar in ``horizon_days`` steps, and at each origin asks
    the model what the *next* ``horizon_days`` mean net would be, then compares
    that with what actually happened and with what the user's own trailing
    28-day mean would have said. Returns
    ``(mean model error, mean anchor error, origins)`` or ``None`` when there is
    not enough history to say anything.

    Every origin uses only data up to that origin (``add_history`` builds the
    lookback features from the passed slice), so this measures the model the way
    it will actually be used — no peeking at the window it is judging.
    """
    ordered = daily.sort_values("date").reset_index(drop=True)
    step = max(int(horizon_days), 1)
    model_error, anchor_error, origins = 0.0, 0.0, 0
    for end in range(60, len(ordered) - step, step):
        history = ordered.iloc[:end]
        future = ordered.iloc[end:end + step]
        if future.empty:
            continue
        featured = forecast_dataset.add_history(history)
        if featured.empty:
            continue
        actual = float((future["inflow_bdt"] - future["outflow_bdt"]).sum())
        means = forecast_model.predict_mean(
            featured.sort_values("date").iloc[[-1]], boosters=boosters
        )
        predicted = float(means["mean_net"].iloc[0]) * step
        tail = history.tail(28)
        anchor = float((tail["inflow_bdt"] - tail["outflow_bdt"]).mean()) * step
        model_error += predicted - actual
        anchor_error += anchor - actual
        origins += 1
    if origins < max(int(min_origins), 1):
        return None
    return model_error / origins, anchor_error / origins, origins


def build_forecast(
    user_id: str,
    horizon_days: int = 14,
    include_pressure_days: bool = True,
    db_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
    safety_buffer_bdt: Optional[float] = None,
    as_of: Any = None,
    include_drivers: bool = False,
    language: str = "bn",
) -> dict[str, Any]:
    """Build the ``ForecastResponse`` payload for one user.

    ``as_of`` (ISO date, server-side) places the window: only history on or
    before that date is used, so the 14-day outlook can cover month-end days
    28–31. Without it the window starts at the latest history (the dataset
    ends 2025-06-30, so the default window is always Jul 1–14 and the
    days-28–31 story can never appear).
    """
    path = Path(db_path) if db_path else user_features.default_db_path()
    artifacts = Path(artifact_dir) if artifact_dir else forecast_model.ARTIFACT_DIR
    transactions = user_features.load_transactions(path, [user_id])
    if transactions.empty:
        raise KeyError(f"unknown user {user_id}")
    cfg = generator.load_config()
    daily = forecast_dataset.daily_flows(transactions, cfg)
    if as_of is not None:
        try:
            cutoff = pd.to_datetime(as_of).normalize()
        except (ValueError, TypeError) as exc:
            raise ValueError(f"as_of must be an ISO date, got {as_of!r}") from exc
        daily = daily[pd.to_datetime(daily["date"]) <= cutoff]
        if daily.empty:
            raise ValueError(f"no history on or before as_of {as_of!r}")
    last_row, last_date = _last_feature_row(daily)
    start = last_date.normalize()
    horizon_days = max(1, min(int(horizon_days), 60))

    try:
        boosters: Any = forecast_model.load(artifacts)
        mean_flows = forecast_model.predict_mean(last_row, boosters=boosters)
        source = "model"
    except Exception:
        boosters = None
        tail = daily.sort_values("date").tail(7)
        mean_in = float(tail["inflow_bdt"].mean() or 0.0)
        mean_out = float(tail["outflow_bdt"].mean() or 0.0)
        mean_flows = pd.DataFrame({
            "mean_inflow": [mean_in],
            "mean_outflow": [mean_out],
            "mean_net": [mean_in - mean_out],
            "net_source": ["difference"],
        })
        source = "rule"
    spread = forecast_evaluate.spread_predictions(
        pd.DataFrame({"user_id": [user_id], "date": [start]}),
        mean_flows, daily, horizon_days,
    )
    # GAP-01 net guard: the net model is biased for earners outside the
    # training support, while the inflow/outflow models are well-measured.
    # When the model window total disagrees with inflow−outflow beyond
    # tolerance, serve the flow-consistent figure (per-day inflow−outflow)
    # and record it — never silently serve a contradictory net.
    inflow_total = float(spread["predicted_inflow"].sum())
    outflow_total = float(spread["predicted_outflow"].sum())
    model_total = float(spread["predicted_net"].sum())
    diff_total = inflow_total - outflow_total
    tolerance = max(NET_GUARD_TOLERANCE * abs(diff_total), NET_GUARD_FLOOR_BDT)
    guard_engaged = source == "model" and abs(model_total - diff_total) > tolerance
    guard_reason = "flows" if guard_engaged else ""
    level: Optional[tuple[float, float, int]] = None
    if source == "model" and not guard_engaged:
        # The tolerance check only proves the three boosters agree with *each
        # other*. Score the net model against what actually happened before
        # trusting its level -- see NET_LEVEL_BACKTEST_MIN_ORIGINS. The boosters
        # are the ones already loaded for the prediction above, so this costs
        # feature builds, not model parses.
        if boosters:
            level = _net_level_check(daily, boosters)
        if level is not None and abs(level[0]) > abs(level[1]) + NET_LEVEL_REQUIRED_IMPROVEMENT:
            guard_engaged = True
            guard_reason = "level"
    if guard_engaged:
        # Anchor fallback: the model is off for this user, so serve the
        # user's own trailing-28-day level with the model's calendar shape.
        # Re-spread from anchor means (no net_source column, so the spread
        # labels it "model"; corrected to "anchor" below).
        tail = daily.sort_values("date").tail(28)
        anchor_in = float(tail["inflow_bdt"].mean())
        anchor_out = float(tail["outflow_bdt"].mean())
        anchor_flows = pd.DataFrame({
            "mean_inflow": [anchor_in],
            "mean_outflow": [anchor_out],
            "mean_net": [anchor_in - anchor_out],
        })
        spread = forecast_evaluate.spread_predictions(
            pd.DataFrame({"user_id": [user_id], "date": [start]}),
            anchor_flows, daily, horizon_days,
        )
        net_source = "anchor"
    else:
        net_source = str(spread["net_source"].iloc[0]) if "net_source" in spread else "difference"
    month = _month_scale(transactions)
    if safety_buffer_bdt is not None:
        buffer_bdt = float(safety_buffer_bdt)
    else:
        buffer_bdt = month["monthly_outflow"] * SAFETY_BUFFER_DAYS / 30.0

    served_rows: list[tuple[str, float, float, float]] = []
    for _, row in spread.iterrows():
        day_date = (start + timedelta(days=int(row["horizon"]))).date()
        inflow = max(float(row["predicted_inflow"]), 0.0)
        outflow = max(float(row["predicted_outflow"]), 0.0)
        # Net is flow-consistent whenever the guard engages (or no net model
        # served one): the solver reads net, so it must never contradict the
        # served inflow and outflow on the same card. Under the anchor
        # fallback the spread was rebuilt from anchor totals, so per-day
        # inflow−outflow sums to the anchor level exactly.
        if guard_engaged or net_source == "difference":
            net = inflow - outflow
        else:
            net = float(row["predicted_net"])
        served_rows.append((day_date.isoformat(), inflow, outflow, net))

    opening = _opening_balance(transactions)
    days: list[dict[str, Any]] = []
    running = opening
    pressure_by_date = {}
    if include_pressure_days:
        preview = [
            {"date": day_date, "predicted_net_bdt": round(net, 2)}
            for day_date, _, _, net in served_rows
        ]
        for item in pressure_rules.detect(preview, opening, buffer_bdt):
            pressure_by_date[item.date] = item.reason_code
    for day_date, inflow, outflow, net in served_rows:
        running += net
        reason = pressure_by_date.get(day_date)
        days.append({
            "date": day_date,
            "predicted_inflow_bdt": round(inflow, 2),
            "predicted_outflow_bdt": round(outflow, 2),
            "predicted_net_bdt": round(net, 2),
            "predicted_balance_bdt": round(running, 2),
            "is_pressure_day": reason is not None,
            "pressure_reason": reason,
        })
    pressure_dates = sorted(pressure_by_date)
    n_pressure = len(pressure_dates)
    # The served total: what the daily rows (and balances) actually sum to.
    window_net = sum(day["predicted_net_bdt"] for day in days)
    window_inflow = sum(day["predicted_inflow_bdt"] for day in days)
    window_outflow = sum(day["predicted_outflow_bdt"] for day in days)
    scale = 30.0 / max(horizon_days, 1)
    monthly_net = window_net * scale
    # Monthly flows are the served window scaled up — never history means:
    # the card's net must equal its inflow minus outflow (GAP-01: the old
    # history-based inflow/outflow disagreed with the served net by ~৳7k/mo).
    monthly_inflow = window_inflow * scale
    monthly_outflow = window_outflow * scale

    range_start = (start + timedelta(days=1)).date().isoformat()
    range_end = (start + timedelta(days=horizon_days)).date().isoformat()
    if source == "model" and not guard_engaged:
        prediction = f"Next {horizon_days} days from {range_start}: net about {window_net:,.0f} taka."
        assumption = (
            "14-day mean flow from the trained model, spread by your own weekday "
            f"pattern; the wallet keeps a {SAFETY_BUFFER_DAYS:g}-day spending cushion."
        )
    elif source == "model":
        prediction = f"Next {horizon_days} days from {range_start}: net about {window_net:,.0f} taka."
        if guard_reason == "level" and level is not None:
            detail = (
                f"backtested on your own last {level[2]} two-week stretches, the net model "
                f"missed by {abs(level[0]):,.0f} taka against {abs(level[1]):,.0f} for your "
                "own trailing average"
            )
        else:
            detail = "the net model disagreed with your own flows beyond tolerance"
        assumption = (
            "Level from your own trailing-28-day average with the model's "
            f"weekday shape: {detail}, so its level was set aside "
            "(anchor fallback)."
        )
    else:
        prediction = f"Baseline outlook for {range_start} to {range_end} (model unavailable)."
        assumption = "Trailing 7-day average, because the trained model could not be loaded."
    if n_pressure:
        explanation = f"Tightest day is {pressure_dates[0]} ({pressure_by_date[pressure_dates[0]]}); {n_pressure} pressure day(s)."
    else:
        explanation = "No pressure day in this window — the wallet stays above the buffer."
    # The SHAP "why" behind the outflow model's number — what the forecast
    # card shows under the chart. ``ml.explain`` degrades to an empty list
    # when shap or the artifacts are unavailable, so serving never fails
    # here. It is opt-in because callers that only read the numbers (the
    # savings solver) should not pay for an explainer they never show.
    drivers: list[dict[str, Any]] = []
    if include_drivers:
        drivers = [
            driver.as_dict()
            for driver in ml_explain.top_drivers(
                last_row, flow="outflow", language=language, artifact_dir=str(artifacts)
            )
        ]
    return {
        "days": days, "pressure_days": pressure_dates,
        "drivers": drivers,
        "monthly_net": round(monthly_net, 2),
        "monthly_inflow": round(monthly_inflow, 2),
        "monthly_outflow": round(monthly_outflow, 2),
        "monthly_fees": round(month["monthly_fees"], 2),
        "safety_buffer_bdt": round(buffer_bdt, 2),
        "opening_balance_bdt": round(opening, 2),
        "generated_from": start.date().isoformat(),
        "net_source": net_source,
        "metrics": _metrics_block(artifacts),
        "provenance": {"prediction": prediction, "assumption": assumption,
                       "explanation": explanation, "source": source},
    }
