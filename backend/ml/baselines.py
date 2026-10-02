"""Rule-based forecast baselines the LightGBM model must beat.

Two baselines from the plan (section 4):

* ``seasonal_naive`` — same weekday last week (``lag_7`` of the flow);
* ``trailing_average`` — mean of the previous 7 days.

Both predict inflow and outflow for horizons 1..N directly from the daily
frame, so evaluation compares identical (date, horizon) cells across methods.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd

#: Baseline names, in the order reported by ``evaluate.py``.
BASELINE_NAMES = ("seasonal_naive", "trailing_average")


def _completed(daily: pd.DataFrame) -> pd.DataFrame:
    """One row per (user, day); quiet days are real zeros, not gaps."""
    users = daily["user_id"].drop_duplicates().sort_values()
    dates = pd.DatetimeIndex(sorted(pd.to_datetime(daily["date"]).unique()))
    full = pd.MultiIndex.from_product([users, dates], names=["user_id", "date"])
    frame = daily.set_index(["user_id", "date"]).reindex(full).reset_index()
    for column in ("inflow_bdt", "outflow_bdt"):
        frame[column] = frame[column].fillna(0.0)
    return frame.sort_values(["user_id", "date"], kind="stable")


def _signals(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach the two baseline signals inside each user (never across users)."""
    grouped = frame.groupby("user_id", sort=False)
    frame = frame.copy()
    frame["signal_seasonal_inflow"] = grouped["inflow_bdt"].shift(7)
    frame["signal_seasonal_outflow"] = grouped["outflow_bdt"].shift(7)
    frame["signal_trailing_inflow"] = grouped["inflow_bdt"].transform(
        lambda series: series.shift(1).rolling(7, min_periods=7).mean()
    )
    frame["signal_trailing_outflow"] = grouped["outflow_bdt"].transform(
        lambda series: series.shift(1).rolling(7, min_periods=7).mean()
    )
    return frame


def predict(
    daily: pd.DataFrame,
    user_ids: Sequence[str] | pd.Series | None = None,
    horizon_days: int = 14,
) -> pd.DataFrame:
    """Baseline predictions for horizons 1..N.

    Returns one row per (user_id, date, horizon) with ``pred_inflow`` and
    ``pred_outflow`` per baseline. The ``date`` is the *feature* date (the day
    the forecast is made from); the predicted day is ``date + horizon``.

    ``user_ids`` is a sequence of ids or the ``user_id`` column itself; ``None``
    predicts for every user in ``daily``.
    """
    frame = _signals(_completed(daily))
    if user_ids is not None:
        wanted = set(pd.Series(user_ids).tolist())
        frame = frame.loc[frame["user_id"].isin(wanted)].reset_index(drop=True)
    grouped = frame.groupby("user_id", sort=False)
    rows: list[pd.DataFrame] = []
    for horizon in range(1, horizon_days + 1):
        part = frame[["user_id", "date"]].copy()
        part["horizon"] = horizon
        actual_inflow = grouped["inflow_bdt"].shift(-horizon)
        actual_outflow = grouped["outflow_bdt"].shift(-horizon)
        part["actual_inflow"] = actual_inflow.to_numpy()
        part["actual_outflow"] = actual_outflow.to_numpy()
        # each baseline's net, so the net can be scored on the same footing as
        # the model's own net rather than only as a difference of two columns
        part["actual_net"] = (actual_inflow - actual_outflow).to_numpy()
        part["seasonal_naive_inflow"] = frame["signal_seasonal_inflow"].to_numpy()
        part["seasonal_naive_outflow"] = frame["signal_seasonal_outflow"].to_numpy()
        part["trailing_average_inflow"] = frame["signal_trailing_inflow"].to_numpy()
        part["trailing_average_outflow"] = frame["signal_trailing_outflow"].to_numpy()
        for method in BASELINE_NAMES:
            part[f"{method}_net"] = (part[f"{method}_inflow"] - part[f"{method}_outflow"]).to_numpy()
        rows.append(part)
    out = pd.concat(rows, ignore_index=True)
    signal_columns = [
        "seasonal_naive_inflow", "seasonal_naive_outflow",
        "trailing_average_inflow", "trailing_average_outflow",
        "actual_inflow", "actual_outflow",
    ]
    return out.dropna(subset=signal_columns).reset_index(drop=True)


def long_frame(predictions: pd.DataFrame) -> pd.DataFrame:
    """Tidy ``(method, flow, actual, predicted)`` rows for scoring."""
    records: list[dict] = []
    for _, row in predictions.iterrows():
        for method in BASELINE_NAMES:
            records.append({
                "user_id": row["user_id"], "date": row["date"], "horizon": row["horizon"],
                "method": method, "flow": "inflow",
                "actual": float(row["actual_inflow"]),
                "predicted": float(row[f"{method}_inflow"]),
            })
            records.append({
                "user_id": row["user_id"], "date": row["date"], "horizon": row["horizon"],
                "method": method, "flow": "outflow",
                "actual": float(row["actual_outflow"]),
                "predicted": float(row[f"{method}_outflow"]),
            })
    return pd.DataFrame(records)


def mae_by_method(predictions: pd.DataFrame) -> dict[str, float]:
    """Mean absolute error per baseline over all (user, date, horizon, flow) cells."""
    tidy = long_frame(predictions)
    tidy["abs_err"] = (tidy["actual"] - tidy["predicted"]).abs()
    return {method: float(tidy.loc[tidy["method"].eq(method), "abs_err"].mean()) for method in BASELINE_NAMES}

