"""Offline forecast evaluation: LightGBM vs the rule baselines.

Compares identical (user, date, horizon) cells and writes ``metrics.json``
for the Phase 8 ``/metrics`` endpoint.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

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


def scored_cells(
    featured: pd.DataFrame,
    daily: pd.DataFrame,
    splits: pd.DataFrame,
    artifact_dir: str | Path = ARTIFACT_DIR,
    horizon_days: int = HORIZON_DAYS,
):
    """Every held-out ``(user, date, horizon)`` cell, scored for model and rules.

    Returns ``(joined, test_features)``: the model's per-day spread beside both
    baselines on the same rows, with ``actual_*`` attached, plus the test-user
    feature frame the scores came from.

    This is the single place the scored cells are built, on purpose.
    :func:`evaluate` and :mod:`backend.ml.fairness` both call it, so a
    group-level error can never be measured on different rows than the headline
    MAE it is compared against. Rebuilding the join inside the fairness pass
    would be the easiest way to quietly break that, so it is not done.
    """
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
    return joined, test_features


def evaluate(
    featured: pd.DataFrame,
    daily: pd.DataFrame,
    splits: pd.DataFrame,
    artifact_dir: str | Path = ARTIFACT_DIR,
    horizon_days: int = HORIZON_DAYS,
    *,
    transactions: pd.DataFrame | None = None,
    cfg: Mapping[str, Any] | None = None,
    request_log_path: str | Path | None = None,
):
    """Score LightGBM vs both baselines, then the plan's impact numbers.

    ``transactions``/``cfg``/``request_log_path`` are optional so the forecast
    score can be computed on its own; when they are present the returned dict
    also carries an ``"impact"`` block (fee savings, shortfall days avoided,
    goal hit-rate and the PII-free request log).
    """
    joined, test_features = scored_cells(featured, daily, splits, artifact_dir, horizon_days)

    day_level = day_level_scores(joined)
    cumulative = cumulative_scores(joined)
    windows = int(joined[["user_id", "date"]].drop_duplicates().shape[0])
    improvement = {flow: cumulative[flow]["improvement_over_best_pct"] for flow in SCORED_FLOWS}
    net_source = str(joined["net_source"].iloc[0]) if "net_source" in joined else "difference"
    impact = impact_metrics(
        daily,
        splits,
        transactions=transactions,
        cfg=cfg,
        request_log_path=request_log_path,
    )
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
        # the plan's outcome numbers (plan.txt §11): consequences, not accuracy
        "impact": impact,
    }



# ---------------------------------------------------------------------------
# impact measurement (plan.txt §11)
# ---------------------------------------------------------------------------
#: The planning horizon the Goal Copilot offers.
GOAL_HORIZON_MONTHS = 6
#: The last two months are held out to test a plan built on the months before.
TEST_WINDOW_MONTHS = 2
#: An emergency-fund goal is a few months of spending, so the backtest has a
#: goal shape that does not depend on the answer.
EMERGENCY_FUND_MONTHS = 3.0
#: Days of typical outflow the plan insists on keeping (matches the solver).
SAFETY_BUFFER_DAYS = 3.0
#: Month-end squeeze window (docs/DATA_ASSUMPTIONS.md §4: last 4 days).
PRESSURE_WINDOW_START_DAY = 28


def _monthly_flows(daily: pd.DataFrame) -> pd.DataFrame:
    """One row per (user, month) with the flows the impact numbers need."""
    frame = daily.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["month"] = frame["date"].dt.to_period("M").astype(str)
    return frame.groupby(["user_id", "month"], as_index=False).agg(
        inflow_bdt=("inflow_bdt", "sum"),
        outflow_bdt=("outflow_bdt", "sum"),
        fee_bdt=("fee_bdt", "sum"),
        net_bdt=("net_bdt", "sum"),
        shortfall_days=("is_shortfall_day", "sum"),
    )


def _unavailable(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "reason": reason}


def fee_savings_metrics(
    transactions: pd.DataFrame | None,
    cfg: Mapping[str, Any],
    test_users: Sequence[str],
) -> dict[str, Any]:
    """Average fee saving per month if cash-outs moved to the cheapest channel.

    Uses the same :mod:`backend.rules.fee_switch` the Spending Companion shows, so
    the impact page and the card can never quote different fees. The saving is a
    *potential* (every cash-out, at the simulated rate card); the assumed
    adoption range is reported beside it, never folded into the headline.
    """
    from backend.rules import fee_switch

    if transactions is None or transactions.empty:
        return _unavailable("no transactions to price")
    frame = transactions[transactions["user_id"].isin(list(test_users))]
    if frame.empty:
        return _unavailable("no held-out transactions")

    rows: list[dict[str, float]] = []
    for _, part in frame.groupby("user_id"):
        stamps = pd.to_datetime(part["timestamp"])
        span_days = max(int((stamps.max() - stamps.min()).days), 1)
        months = max(span_days / 30.0, 1.0 / 30.0)
        suggestion = fee_switch.suggest(part, cfg, window_days=None)
        rows.append(
            {
                "potential": suggestion.potential_saving_bdt / months,
                "low": suggestion.assumed_saving_low_bdt / months,
                "high": suggestion.assumed_saving_high_bdt / months,
            }
        )
    count = len(rows)
    return {
        "status": "ok",
        "users": count,
        "avg_potential_fee_saving_bdt_per_month": round(
            sum(item["potential"] for item in rows) / count, 2
        ),
        "avg_assumed_fee_saving_low_bdt_per_month": round(
            sum(item["low"] for item in rows) / count, 2
        ),
        "avg_assumed_fee_saving_high_bdt_per_month": round(
            sum(item["high"] for item in rows) / count, 2
        ),
        "adoption_range": fee_switch.ADOPTION_RANGE,
        "note": (
            "Potential = every cash-out priced at the simulated cash-out rate "
            "minus the cheapest channel; the adoption range is an assumption, "
            "not a measured result."
        ),
    }


def shortfall_metrics(
    daily: pd.DataFrame,
    test_users: Sequence[str],
) -> dict[str, Any]:
    """Shortfall days avoided: the plan's timing advice versus the raw ledger.

    The plan targets the month-end squeeze (the last four days of the month,
    where the generator injects pressure). A shortfall on one of those days is
    what the plan's timing advice addresses, so it is counted as *avoided*; a
    shortfall elsewhere is residual and treated as not avoidable by timing. This
    is a stated assumption measured on real rows, not a simulated user.
    """
    frame = daily[daily["user_id"].isin(list(test_users))].copy()
    if frame.empty:
        return _unavailable("no held-out daily rows")
    frame["date"] = pd.to_datetime(frame["date"])
    frame["day_of_month"] = frame["date"].dt.day
    frame["month"] = frame["date"].dt.to_period("M").astype(str)

    observed_pm = avoided_pm = residual_pm = 0.0
    counted = 0
    for _, part in frame.groupby("user_id"):
        months = max(int(part["month"].nunique()), 1)
        observed = float(part["is_shortfall_day"].sum())
        pressure = part["day_of_month"] >= PRESSURE_WINDOW_START_DAY
        avoided = min(float(part.loc[pressure, "is_shortfall_day"].sum()), observed)
        observed_pm += observed / months
        avoided_pm += avoided / months
        residual_pm += (observed - avoided) / months
        counted += 1
    if not counted:
        return _unavailable("no held-out users")
    return {
        "status": "ok",
        "users": counted,
        "observed_shortfall_days_per_month": round(observed_pm / counted, 2),
        "plan_shortfall_days_per_month": round(residual_pm / counted, 2),
        "avoided_shortfall_days_per_month": round(avoided_pm / counted, 2),
        "note": (
            "Avoided counts shortfalls in the month-end squeeze window (day "
            f">= {PRESSURE_WINDOW_START_DAY}) that the plan's timing advice "
            "targets; residual shortfalls elsewhere are not counted as avoidable."
        ),
    }



def goal_hit_rate_backtest(
    daily: pd.DataFrame,
    test_users: Sequence[str],
) -> dict[str, Any]:
    """Plan on months 1..n-2, test on the last two months.

    Two planners are compared on the same realised outcome: the AI plan (which
    keeps a safety buffer) and the naive "goal / months" plan (which does not).
    The hit-rate is the share of the plans a planner *recommended* that the user
    actually kept up with in the held-out months, so a planner that says "yes" to
    everyone and is often wrong scores worse than one that declines the hopeless
    cases.
    """
    monthly = _monthly_flows(daily)
    frame = monthly[monthly["user_id"].isin(list(test_users))]
    if frame.empty:
        return _unavailable("no held-out months")

    records: list[dict[str, bool]] = []
    for _, part in frame.groupby("user_id"):
        part = part.sort_values("month")
        months = part["month"].tolist()
        if len(months) < 2:
            continue
        split = max(1, len(months) - TEST_WINDOW_MONTHS)
        if split >= len(months):
            split = len(months) - 1
        plan = part.iloc[:split]
        test = part.iloc[split:]
        plan_net = float(plan["net_bdt"].mean())
        plan_out = float(plan["outflow_bdt"].mean())
        test_net = float(test["net_bdt"].mean())
        goal = plan_out * EMERGENCY_FUND_MONTHS
        required = goal / GOAL_HORIZON_MONTHS
        buffer = plan_out * SAFETY_BUFFER_DAYS / 30.0
        records.append(
            {
                "ai_feasible": required <= max(plan_net - buffer, 0.0),
                "naive_feasible": required <= max(plan_net, 0.0),
                "hit": test_net >= required,
            }
        )
    if not records:
        return _unavailable("fewer than two months of history per user")

    def rate(flag: str) -> dict[str, Any]:
        recommended = [row for row in records if row[flag]]
        hits = sum(1 for row in recommended if row["hit"])
        pct = round(hits / len(recommended) * 100.0, 2) if recommended else None
        return {"recommended": len(recommended), "hits": hits, "hit_rate_pct": pct}

    ai = rate("ai_feasible")
    naive = rate("naive_feasible")
    improvement = (
        round(ai["hit_rate_pct"] - naive["hit_rate_pct"], 2)
        if ai["hit_rate_pct"] is not None and naive["hit_rate_pct"] is not None
        else None
    )
    return {
        "status": "ok",
        "users": len(records),
        "goal_horizon_months": GOAL_HORIZON_MONTHS,
        "ai": ai,
        "naive": naive,
        "improvement_pct_points": improvement,
        "note": (
            "Plans are built on the earlier months and tested on the last two; "
            "the naive planner is goal / months with no buffer. Hit-rate is over "
            "the plans each planner recommended, not over every user."
        ),
    }



def request_log_summary(path: str | Path | None = None) -> dict[str, Any]:
    """Aggregate the PII-free request log (method/path/status/latency only)."""
    if path is None:
        return _unavailable("no request log configured")
    target = Path(path)
    if not target.exists():
        return _unavailable("no request log yet")
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - unreadable log
        return _unavailable("request log is unreadable")

    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    if not records:
        return _unavailable("request log is empty")

    total = len(records)
    errors = sum(1 for item in records if int(item.get("status", 0) or 0) >= 400)
    durations = [
        float(item["duration_ms"])
        for item in records
        if isinstance(item.get("duration_ms"), (int, float))
    ]
    counts = Counter(str(item.get("path", "?")) for item in records)
    return {
        "status": "ok",
        "requests": total,
        "error_rate_pct": round(errors / total * 100.0, 2),
        "avg_duration_ms": round(sum(durations) / len(durations), 2) if durations else None,
        "by_path": [
            {"path": name, "requests": count} for name, count in counts.most_common(10)
        ],
        "note": (
            "Request logs carry method, path, status and latency only — the query "
            "string, headers, body and user are never logged."
        ),
    }


def impact_metrics(
    daily: pd.DataFrame,
    splits: pd.DataFrame | None = None,
    *,
    transactions: pd.DataFrame | None = None,
    cfg: Mapping[str, Any] | None = None,
    request_log_path: str | Path | None = None,
) -> dict[str, Any]:
    """The plan's four impact numbers, each degrading on its own.

    One missing input must cost only its own block, so every part is computed
    independently and an error is recorded as ``unavailable`` rather than raised.
    """
    test_users: list[str] = []
    if splits is not None and not splits.empty and "split" in splits.columns:
        test_users = splits.loc[splits["split"].eq("test"), "user_id"].tolist()
    if not test_users and daily is not None and not daily.empty:
        test_users = daily["user_id"].drop_duplicates().tolist()

    block: dict[str, Any] = {}
    try:
        if cfg is None:
            block["fee_savings"] = _unavailable("no dataset config")
        else:
            block["fee_savings"] = fee_savings_metrics(transactions, cfg, test_users)
    except Exception as exc:  # noqa: BLE001 - impact must never break the run
        block["fee_savings"] = _unavailable(type(exc).__name__)

    try:
        block["shortfall_days"] = shortfall_metrics(daily, test_users)
    except Exception as exc:  # noqa: BLE001
        block["shortfall_days"] = _unavailable(type(exc).__name__)

    try:
        block["goal_hit_rate"] = goal_hit_rate_backtest(daily, test_users)
    except Exception as exc:  # noqa: BLE001
        block["goal_hit_rate"] = _unavailable(type(exc).__name__)

    block["request_logs"] = request_log_summary(request_log_path)
    return block


def write_metrics(metrics: Mapping[str, Any], artifact_dir: str | Path = ARTIFACT_DIR) -> Path:
    """Persist the evaluation so ``/metrics`` can serve it without retraining."""
    path = Path(artifact_dir) / METRICS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(metrics), indent=2), encoding="utf-8")
    return path


def read_metrics(artifact_dir: str | Path = ARTIFACT_DIR) -> dict[str, Any]:
    """The last written evaluation, or ``{}`` when nothing has been trained.

    Never raises and never guesses: a missing, empty or corrupt ``metrics.json``
    comes back empty so the endpoint can answer "no evaluation yet" instead of
    turning a missing artifact into a 500. The file is written atomically enough
    for this purpose by :func:`write_metrics`, which finishes the write before
    returning.
    """
    path = Path(artifact_dir) / METRICS_FILE
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - truncated or hand-edited
        return {}
    return payload if isinstance(payload, dict) else {}

