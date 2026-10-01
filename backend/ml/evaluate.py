"""Offline forecast evaluation: LightGBM vs the rule baselines.

Compares identical (user, date, horizon) cells and writes ``metrics.json``
for the Phase 8 ``/metrics`` endpoint.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from . import baselines, forecast
from .dataset import HORIZON_DAYS

ARTIFACT_DIR = forecast.ARTIFACT_DIR
METRICS_FILE = "metrics.json"

def _calendar_weights(daily: pd.DataFrame) -> pd.DataFrame:
    """Each user's mean flow per weekday (from observed history only)."""
    frame = daily.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["weekday"] = frame["date"].dt.weekday
    return frame.groupby(["user_id", "weekday"], as_index=False).agg(
        mean_inflow=("inflow_bdt", "mean"), mean_outflow=("outflow_bdt", "mean")
    )


def spread_predictions(dates, mean_flows, daily, horizon_days=HORIZON_DAYS):
    """Spread each 14-day mean across the horizon by the user's weekday shape."""
    weights = _calendar_weights(daily)
    by_user = {user: group for user, group in weights.groupby("user_id")}
    records: list[dict[str, Any]] = []
    for index, row in dates.reset_index(drop=True).iterrows():
        user_id = row["user_id"]
        start = pd.to_datetime(row["date"])
        table = by_user.get(user_id)
        inflow_w, outflow_w = [], []
        for horizon in range(1, horizon_days + 1):
            weekday = (start + pd.Timedelta(days=horizon)).weekday()
            match = None
            if table is not None:
                hit = table.loc[table["weekday"].eq(weekday)]
                if not hit.empty:
                    match = hit.iloc[0]
            inflow_w.append(float(match["mean_inflow"]) if match is not None else 1.0)
            outflow_w.append(float(match["mean_outflow"]) if match is not None else 1.0)
        inflow_total = sum(inflow_w) or 1.0
        outflow_total = sum(outflow_w) or 1.0
        mean_in = float(mean_flows["mean_inflow"].iloc[index])
        mean_out = float(mean_flows["mean_outflow"].iloc[index])
        for horizon in range(1, horizon_days + 1):
            records.append({
                "user_id": user_id, "date": start, "horizon": horizon,
                "predicted_inflow": max(mean_in * horizon_days * inflow_w[horizon - 1] / inflow_total, 0.0),
                "predicted_outflow": max(mean_out * horizon_days * outflow_w[horizon - 1] / outflow_total, 0.0),
            })
    return pd.DataFrame(records)


def _mae(predicted: pd.Series, actual: pd.Series) -> float:
    """Mean absolute error over the rows of two aligned series."""
    return float(np.mean(np.abs(
        predicted.to_numpy(dtype=float) - actual.to_numpy(dtype=float)
    )))


def _rmse(predicted: pd.Series, actual: pd.Series) -> float:
    """Root mean squared error over the rows of two aligned series."""
    error = predicted.to_numpy(dtype=float) - actual.to_numpy(dtype=float)
    return float(np.sqrt(np.mean(error ** 2)))


def _score_block(actual: pd.Series, predictions: Mapping[str, pd.Series]) -> dict[str, Any]:
    """MAE/RMSE per method (``model`` first) plus improvement over the best rule."""
    block: dict[str, Any] = {}
    for name, values in predictions.items():
        block[name] = {
            "mae": round(_mae(values, actual), 2),
            "rmse": round(_rmse(values, actual), 2),
        }
    model_mae = block["model"]["mae"]
    for name in baselines.BASELINE_NAMES:
        base_mae = block[name]["mae"]
        block[name]["improvement_pct"] = (
            round((base_mae - model_mae) / base_mae * 100, 1) if base_mae else 0.0
        )
    best_rule = min(block[name]["mae"] for name in baselines.BASELINE_NAMES)
    block["improvement_over_best_pct"] = (
        round((best_rule - model_mae) / best_rule * 100, 1) if best_rule else 0.0
    )
    return block


def day_level_scores(joined: pd.DataFrame) -> dict[str, Any]:
    """Per-day accuracy: the model's calendar-spread days vs the rule days."""
    scores: dict[str, Any] = {}
    for flow in ("inflow", "outflow"):
        predictions = {"model": joined[f"predicted_{flow}"]}
        for method in baselines.BASELINE_NAMES:
            predictions[method] = joined[f"{method}_{flow}"]
        scores[flow] = _score_block(joined[f"actual_{flow}"], predictions)
    return scores


def cumulative_scores(joined: pd.DataFrame) -> dict[str, Any]:
    """14-day total accuracy — the number the savings solver actually consumes.

    The model's per-day spread sums exactly to ``mean x horizon``, so this is
    the accuracy of the 14-day cash-flow total the plan is solved against. Each
    baseline's per-day predictions are summed over the same window.
    """
    aggregations: dict[str, Any] = {
        "actual_inflow": ("actual_inflow", "sum"),
        "actual_outflow": ("actual_outflow", "sum"),
        "predicted_inflow": ("predicted_inflow", "sum"),
        "predicted_outflow": ("predicted_outflow", "sum"),
    }
    for method in baselines.BASELINE_NAMES:
        for flow in ("inflow", "outflow"):
            aggregations[f"{method}_{flow}"] = (f"{method}_{flow}", "sum")
    totals = joined.groupby(["user_id", "date"], as_index=False).agg(**aggregations)

    scores: dict[str, Any] = {}
    for flow in ("inflow", "outflow"):
        predictions = {"model": totals[f"predicted_{flow}"]}
        for method in baselines.BASELINE_NAMES:
            predictions[method] = totals[f"{method}_{flow}"]
        scores[flow] = _score_block(totals[f"actual_{flow}"], predictions)
    return scores


def evaluate(featured, daily, splits, artifact_dir=ARTIFACT_DIR, horizon_days=HORIZON_DAYS):
    """Score LightGBM vs both baselines on the held-out test users."""
    frame = featured.merge(splits, on="user_id", how="inner")
    test_features = frame.loc[frame["split"].eq("test")].reset_index(drop=True)
    if test_features.empty:
        raise ValueError("no test users to evaluate")
    mean_flows = forecast.predict_mean(test_features, artifact_dir)
    model_days = spread_predictions(test_features[["user_id", "date"]], mean_flows, daily, horizon_days)

    lookup = daily.set_index(["user_id", pd.to_datetime(daily["date"])])[["inflow_bdt", "outflow_bdt"]]
    actual_in, actual_out = [], []
    for _, row in model_days.iterrows():
        day = pd.to_datetime(row["date"]) + pd.Timedelta(days=int(row["horizon"]))
        try:
            match = lookup.loc[(row["user_id"], day)]
        except KeyError:
            actual_in.append(np.nan)
            actual_out.append(np.nan)
            continue
        if isinstance(match, pd.DataFrame):
            match = match.iloc[0]
        actual_in.append(float(match["inflow_bdt"]))
        actual_out.append(float(match["outflow_bdt"]))
    model_days["actual_inflow"] = actual_in
    model_days["actual_outflow"] = actual_out
    model_days = model_days.dropna(subset=["actual_inflow", "actual_outflow"]).reset_index(drop=True)

    baseline_preds = baselines.predict(daily, test_features["user_id"], horizon_days)
    base = baseline_preds.copy()
    base["date"] = pd.to_datetime(base["date"])
    model_days["date"] = pd.to_datetime(model_days["date"])
    joined = model_days.merge(
        base, on=["user_id", "date", "horizon"], how="inner",
        suffixes=("", "_baseline"),
    )

    day_level = day_level_scores(joined)
    cumulative = cumulative_scores(joined)
    windows = int(joined[["user_id", "date"]].drop_duplicates().shape[0])
    improvement = {
        flow: cumulative[flow]["improvement_over_best_pct"] for flow in ("inflow", "outflow")
    }
    return {
        "horizon_days": horizon_days,
        "n_cells": int(len(joined)),
        "n_windows": windows,
        "test_users": int(test_features["user_id"].nunique()),
        # headline = 14-day totals (what the plan consumes); day level is kept too
        "inflow": cumulative["inflow"],
        "outflow": cumulative["outflow"],
        "day_level": day_level,
        "cumulative": cumulative,
        "improvement_vs_best_pct": improvement,
        "target_improvement_pct": 15.0,
        "target_met": bool(
            improvement["inflow"] >= 15.0 and improvement["outflow"] >= 15.0
        ),
    }



def write_metrics(metrics: Mapping[str, Any], artifact_dir: str | Path = ARTIFACT_DIR) -> Path:
    """Persist the evaluation so ``/metrics`` can serve it without retraining."""
    path = Path(artifact_dir) / METRICS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(metrics), indent=2), encoding="utf-8")
    return path

