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


def _net_weights(daily: pd.DataFrame) -> pd.DataFrame:
    """Each user's mean *net* per weekday, spread so the day can be negative."""
    frame = daily.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["weekday"] = frame["date"].dt.weekday
    frame["net_bdt"] = frame["inflow_bdt"] - frame["outflow_bdt"]
    return frame.groupby(["user_id", "weekday"], as_index=False).agg(
        mean_net=("net_bdt", "mean")
    )


def spread_predictions(dates, mean_flows, daily, horizon_days=HORIZON_DAYS):
    """Spread each 14-day mean across the horizon by the user's weekday shape.

    Inflow and outflow are spread independently and clipped at zero. Net is
    spread from its own model and its own weekday shape, so the served per-day
    nets sum to exactly the net model's total instead of accumulating the two
    flow models' independent errors. ``net_source`` records which produced it.

    Without a net model the net falls back to the difference of the spread
    flows; the shape is still the calendar one, but the level is the weaker
    number and the reported ``net_source`` says exactly that.
    """
    weights = _calendar_weights(daily)
    net_shape = _net_weights(daily)
    by_user = {user: group for user, group in weights.groupby("user_id")}
    net_by_user = {user: group for user, group in net_shape.groupby("user_id")}
    # The caller's own label wins when it is present: the service can supply a
    # net built from the trailing-average rule, and that is a "difference" even
    # though the column exists. Deriving it from column presence alone would
    # report "model" for a number no model produced.
    declared = None
    if "net_source" in mean_flows and len(mean_flows["net_source"]):
        declared = str(mean_flows["net_source"].iloc[0])
    if declared in ("model", "difference"):
        net_source = declared
        has_net_model = declared == "model" and bool(
            np.isfinite(mean_flows["mean_net"].to_numpy(dtype=float)).all()
        )
    else:
        has_net_model = "mean_net" in mean_flows and bool(
            np.isfinite(mean_flows["mean_net"].to_numpy(dtype=float)).all()
        )
    records: list[dict[str, Any]] = []
    for index, row in dates.reset_index(drop=True).iterrows():
        user_id = row["user_id"]
        start = pd.to_datetime(row["date"])
        table = by_user.get(user_id)
        net_table = net_by_user.get(user_id)
        inflow_w: list[float] = []
        outflow_w: list[float] = []
        net_w: list[float | None] = []
        for horizon in range(1, horizon_days + 1):
            weekday = (start + pd.Timedelta(days=horizon)).weekday()
            match = None
            if table is not None:
                hit = table.loc[table["weekday"].eq(weekday)]
                if not hit.empty:
                    match = hit.iloc[0]
            inflow_w.append(float(match["mean_inflow"]) if match is not None else 1.0)
            outflow_w.append(float(match["mean_outflow"]) if match is not None else 1.0)
            net_match = None
            if net_table is not None:
                hit = net_table.loc[net_table["weekday"].eq(weekday)]
                if not hit.empty:
                    net_match = hit.iloc[0]
            # a weekday with no history falls back to the user's overall mean
            # net, not to 1.0, which would bias every spread toward positive
            net_w.append(float(net_match["mean_net"]) if net_match is not None else None)
        if any(value is None for value in net_w):
            overall = None
            if net_table is not None and len(net_table):
                overall = float(net_table["mean_net"].mean())
            net_w = [overall if value is None else value for value in net_w]
            if overall is None:
                net_w = [0.0] * horizon_days
        # the None sentinels above are all resolved by now; the explicit
        # conversion is what lets the spread arithmetic below stay float-only
        net_weights: list[float] = [
            0.0 if value is None else float(value) for value in net_w
        ]
        inflow_total = sum(inflow_w) or 1.0
        outflow_total = sum(outflow_w) or 1.0
        net_total = sum(net_weights)
        mean_in = float(mean_flows["mean_inflow"].iloc[index])
        mean_out = float(mean_flows["mean_outflow"].iloc[index])
        mean_net = (
            float(mean_flows["mean_net"].iloc[index])
            if has_net_model
            else mean_in - mean_out
        )
        for horizon in range(1, horizon_days + 1):
            records.append({
                "user_id": user_id, "date": start, "horizon": horizon,
                "predicted_inflow": max(mean_in * horizon_days * inflow_w[horizon - 1] / inflow_total, 0.0),
                "predicted_outflow": max(mean_out * horizon_days * outflow_w[horizon - 1] / outflow_total, 0.0),
                "predicted_net": (
                    mean_net * horizon_days * net_weights[horizon - 1] / net_total
                    if net_total
                    else mean_net
                ),
                "net_source": "model" if has_net_model else "difference",
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


#: ``net`` is the flow the savings solver consumes, so it is scored like the
#: others and reported beside them.
SCORED_FLOWS = ("inflow", "outflow", "net")


def day_level_scores(joined: pd.DataFrame) -> dict[str, Any]:
    """Per-day accuracy: the model's calendar-spread days vs the rule days."""
    scores: dict[str, Any] = {}
    for flow in SCORED_FLOWS:
        actual = joined[f"actual_{flow}"]
        predictions = {"model": joined[f"predicted_{flow}"]}
        for method in baselines.BASELINE_NAMES:
            predictions[method] = joined[f"{method}_{flow}"]
        scores[flow] = _score_block(actual, predictions)
    return scores


def cumulative_scores(joined: pd.DataFrame) -> dict[str, Any]:
    """14-day total accuracy — the number the savings solver actually consumes.

    The model's per-day spread sums exactly to ``mean x horizon``, so this is
    the accuracy of the 14-day cash-flow total the plan is solved against. Each
    baseline's per-day predictions are summed over the same window.
    """
    aggregations: dict[str, Any] = {}
    for flow in SCORED_FLOWS:
        aggregations[f"actual_{flow}"] = (f"actual_{flow}", "sum")
        aggregations[f"predicted_{flow}"] = (f"predicted_{flow}", "sum")
    for method in baselines.BASELINE_NAMES:
        for flow in SCORED_FLOWS:
            aggregations[f"{method}_{flow}"] = (f"{method}_{flow}", "sum")
    totals = joined.groupby(["user_id", "date"], as_index=False).agg(**aggregations)

    scores: dict[str, Any] = {}
    for flow in SCORED_FLOWS:
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
    # net is the flow the solver reads, so it is scored against the realised net
    model_days["actual_net"] = model_days["actual_inflow"] - model_days["actual_outflow"]
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
    improvement = {flow: cumulative[flow]["improvement_over_best_pct"] for flow in SCORED_FLOWS}
    net_source = str(joined["net_source"].iloc[0]) if "net_source" in joined else "difference"
    return {
        "horizon_days": horizon_days,
        "n_cells": int(len(joined)),
        "n_windows": windows,
        "test_users": int(test_features["user_id"].nunique()),
        # headline = 14-day totals (what the plan consumes); day level is kept too
        "inflow": cumulative["inflow"],
        "outflow": cumulative["outflow"],
        # net is reported first-class: it is the number the savings solver reads,
        # so its accuracy can no longer hide behind the two flow metrics
        "net": cumulative["net"],
        "net_source": net_source,
        "day_level": day_level,
        "cumulative": cumulative,
        "improvement_vs_best_pct": improvement,
        "target_improvement_pct": 15.0,
        "target_met": bool(
            all(improvement[flow] >= 15.0 for flow in SCORED_FLOWS)
        ),
    }



def write_metrics(metrics: Mapping[str, Any], artifact_dir: str | Path = ARTIFACT_DIR) -> Path:
    """Persist the evaluation so ``/metrics`` can serve it without retraining."""
    path = Path(artifact_dir) / METRICS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(metrics), indent=2), encoding="utf-8")
    return path

