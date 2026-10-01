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
from backend.ml import forecast as forecast_model
from backend.rules import pressure_days as pressure_rules

SAFETY_BUFFER_DAYS = 3.0
METRICS_FILE = forecast_evaluate.METRICS_FILE


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
    except (KeyError, ValueError, OSError):
        return None
    return {
        "model_name": "lightgbm_14d_mean",
        "mae_bdt": outflow["model"]["mae"],
        "rmse_bdt": outflow["model"]["rmse"],
        "baseline_name": baseline,
        "baseline_mae_bdt": outflow[baseline]["mae"],
        "improvement_pct": outflow["improvement_over_best_pct"],
    }


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



def build_forecast(
    user_id: str,
    horizon_days: int = 14,
    include_pressure_days: bool = True,
    db_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
    safety_buffer_bdt: Optional[float] = None,
) -> dict[str, Any]:
    """Build the ``ForecastResponse`` payload for one user."""
    path = Path(db_path) if db_path else user_features.default_db_path()
    artifacts = Path(artifact_dir) if artifact_dir else forecast_model.ARTIFACT_DIR
    transactions = user_features.load_transactions(path, [user_id])
    if transactions.empty:
        raise KeyError(f"unknown user {user_id}")
    cfg = generator.load_config()
    daily = forecast_dataset.daily_flows(transactions, cfg)
    last_row, last_date = _last_feature_row(daily)
    start = last_date.normalize()
    horizon_days = max(1, min(int(horizon_days), 60))

    try:
        mean_flows = forecast_model.predict_mean(last_row, artifacts)
        source = "model"
    except Exception:
        tail = daily.sort_values("date").tail(7)
        mean_flows = pd.DataFrame({
            "mean_inflow": [float(tail["inflow_bdt"].mean() or 0.0)],
            "mean_outflow": [float(tail["outflow_bdt"].mean() or 0.0)],
        })
        source = "rule"
    spread = forecast_evaluate.spread_predictions(
        pd.DataFrame({"user_id": [user_id], "date": [start]}),
        mean_flows, daily, horizon_days,
    )
    month = _month_scale(transactions)
    if safety_buffer_bdt is not None:
        buffer_bdt = float(safety_buffer_bdt)
    else:
        buffer_bdt = month["monthly_outflow"] * SAFETY_BUFFER_DAYS / 30.0

    opening = _opening_balance(transactions)
    days: list[dict[str, Any]] = []
    running = opening
    pressure_by_date = {}
    if include_pressure_days:
        preview = [
            {
                "date": (start + timedelta(days=int(row["horizon"]))).date().isoformat(),
                "predicted_net_bdt": round(max(float(row["predicted_inflow"]), 0.0) - max(float(row["predicted_outflow"]), 0.0), 2),
            }
            for _, row in spread.iterrows()
        ]
        for item in pressure_rules.detect(preview, opening, buffer_bdt):
            pressure_by_date[item.date] = item.reason_code
    for _, row in spread.iterrows():
        day_date = (start + timedelta(days=int(row["horizon"]))).date()
        inflow = max(float(row["predicted_inflow"]), 0.0)
        outflow = max(float(row["predicted_outflow"]), 0.0)
        net = inflow - outflow
        running += net
        reason = pressure_by_date.get(day_date.isoformat())
        days.append({
            "date": day_date.isoformat(),
            "predicted_inflow_bdt": round(inflow, 2),
            "predicted_outflow_bdt": round(outflow, 2),
            "predicted_net_bdt": round(net, 2),
            "predicted_balance_bdt": round(running, 2),
            "is_pressure_day": reason is not None,
            "pressure_reason": reason,
        })
    pressure_dates = sorted(pressure_by_date)
    n_pressure = len(pressure_dates)
    window_net = float(spread["predicted_inflow"].sum() - spread["predicted_outflow"].sum())
    monthly_net = window_net * 30.0 / max(horizon_days, 1)

    range_start = (start + timedelta(days=1)).date().isoformat()
    range_end = (start + timedelta(days=horizon_days)).date().isoformat()
    if source == "model":
        prediction = f"Next {horizon_days} days from {range_start}: net about {window_net:,.0f} taka."
        assumption = (
            "14-day mean flow from the trained model, spread by your own weekday "
            f"pattern; the wallet keeps a {SAFETY_BUFFER_DAYS:g}-day spending cushion."
        )
    else:
        prediction = f"Baseline outlook for {range_start} to {range_end} (model unavailable)."
        assumption = "Trailing 7-day average, because the trained model could not be loaded."
    if n_pressure:
        explanation = f"Tightest day is {pressure_dates[0]} ({pressure_by_date[pressure_dates[0]]}); {n_pressure} pressure day(s)."
    else:
        explanation = "No pressure day in this window — the wallet stays above the buffer."
    return {
        "days": days, "pressure_days": pressure_dates,
        "monthly_net": round(monthly_net, 2),
        "monthly_inflow": round(month["monthly_inflow"], 2),
        "monthly_outflow": round(month["monthly_outflow"], 2),
        "monthly_fees": round(month["monthly_fees"], 2),
        "safety_buffer_bdt": round(buffer_bdt, 2),
        "opening_balance_bdt": round(opening, 2),
        "generated_from": start.date().isoformat(),
        "metrics": _metrics_block(artifacts),
        "provenance": {"prediction": prediction, "assumption": assumption,
                       "explanation": explanation, "source": source},
    }
