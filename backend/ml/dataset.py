"""Daily cash-flow dataset for the forecast models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from backend.data import features as user_features
from backend.data import generator

#: How far back the history features may look.
LOOKBACK_DAYS = 28

#: The forecast horizon the product promises.
HORIZON_DAYS = 14

#: Calendar columns (known for future days, usable at serve time).
CALENDAR_COLUMNS = [
    "day_of_month", "weekday", "is_weekend", "is_month_end", "days_to_month_end",
]

#: Lag/rolling columns (recomputed day-by-day from the user's own ledger).
FLOW_COLUMNS = [
    "lag_1_net",
    "lag_2_net",
    "lag_3_net",
    "lag_7_net",
    "lag_14_net",
    "lag_1_outflow",
    "lag_2_outflow",
    "lag_3_outflow",
    "lag_7_outflow",
    "lag_1_inflow",
    "roll_3_inflow",
    "roll_3_outflow",
    "roll_3_net",
    "roll_7_inflow",
    "roll_7_outflow",
    "roll_7_net",
    "roll_14_outflow",
    "roll_14_net",
    "roll_28_inflow",
    "roll_28_outflow",
    "roll_28_net",
    "max_7_outflow",
    "shortfall_last_7",
    "mtd_inflow",
    "mtd_outflow",
    "mtd_cash_out_bdt",
    "mtd_cash_out_count",
    "roll_7_cash_out_bdt",
    "roll_28_cash_out_bdt",
    "days_since_cash_out",
    "balance_end_bdt",
]

FORECAST_FEATURE_COLUMNS = CALENDAR_COLUMNS + FLOW_COLUMNS


@dataclass(frozen=True)
class ForecastFrame:
    """Per-user daily flows plus the feature matrix."""

    daily: pd.DataFrame
    features: pd.DataFrame


def _daily_flows(transactions: pd.DataFrame, cfg: Mapping[str, Any]) -> pd.DataFrame:
    """Aggregate transactions to one row per (user, day)."""
    frame = transactions.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame["date"] = frame["timestamp"].dt.normalize()
    is_income = frame["type"].eq("income").to_numpy()
    frame["_inflow"] = np.where(is_income, frame["amount_bdt"].to_numpy(dtype=float), 0.0)
    frame["_outflow"] = np.where(is_income, 0.0, frame["amount_bdt"].to_numpy(dtype=float))
    frame["_shortfall"] = frame["is_shortfall"].to_numpy(dtype=int)
    is_cash_out = frame["channel"].eq("cash_out").to_numpy()
    frame["_cash_out"] = np.where(is_cash_out, frame["amount_bdt"].to_numpy(dtype=float), 0.0)
    frame["_cash_out_count"] = is_cash_out.astype(int)

    daily = (
        frame.groupby(["user_id", "date"], as_index=False)
        .agg(
            inflow_bdt=("_inflow", "sum"),
            outflow_bdt=("_outflow", "sum"),
            fee_bdt=("fee_bdt", "sum"),
            tx_count=("transaction_id", "count"),
            shortfall_events=("_shortfall", "sum"),
            cash_out_bdt=("_cash_out", "sum"),
            cash_out_count=("_cash_out_count", "sum"),
            balance_end_bdt=("balance_after", "last"),
        )
        .sort_values(["user_id", "date"], kind="stable")
        .reset_index(drop=True)
    )
    daily["net_bdt"] = daily["inflow_bdt"] - daily["outflow_bdt"] - daily["fee_bdt"]
    daily["is_shortfall_day"] = (daily["shortfall_events"] > 0).astype(int)

    calendar = pd.DataFrame({"date": daily["date"].drop_duplicates().sort_values()})
    calendar["day_of_month"] = calendar["date"].dt.day
    calendar["weekday"] = calendar["date"].dt.weekday
    weekend = {int(day) for day in cfg["dataset"]["weekend_weekdays"]}
    calendar["is_weekend"] = calendar["date"].dt.weekday.isin(weekend).astype(int)
    calendar["is_month_end"] = (calendar["date"].dt.day >= 28).astype(int)
    return daily.merge(calendar, on="date", how="left")


def daily_flows(transactions: pd.DataFrame, cfg: Mapping[str, Any]) -> pd.DataFrame:
    """Public wrapper for :func:`_daily_flows` (stable import for services)."""
    return _daily_flows(transactions, cfg)


def _complete_calendar(daily: pd.DataFrame) -> pd.DataFrame:
    """Fill missing (user, day) pairs with zeros so lags stay honest.

    A day with no transactions is a real observation (nothing moved), not a
    gap — without completion the 7-day lag of a quiet week would silently
    point at a different weekday.
    """
    users = daily["user_id"].drop_duplicates().sort_values()
    dates = pd.DatetimeIndex(sorted(daily["date"].unique()))
    full = pd.MultiIndex.from_product([users, dates], names=["user_id", "date"])
    frame = daily.set_index(["user_id", "date"]).reindex(full).reset_index()
    for column in [
        "inflow_bdt", "outflow_bdt", "fee_bdt", "tx_count", "cash_out_bdt", "cash_out_count",
        "shortfall_events", "is_shortfall_day", "net_bdt",
    ]:
        frame[column] = frame[column].fillna(0.0)
    frame["balance_end_bdt"] = (
        frame.groupby("user_id")["balance_end_bdt"].ffill().fillna(0.0)
    )
    frame["day_of_month"] = frame["date"].dt.day
    frame["weekday"] = frame["date"].dt.weekday
    frame["is_weekend"] = frame["weekday"].isin([4, 5]).astype(int)
    frame["is_month_end"] = (frame["day_of_month"] >= 28).astype(int)
    return frame.sort_values(["user_id", "date"], kind="stable").reset_index(drop=True)


def _shift(grouped, column: str, periods: int) -> pd.Series:
    """Shift a column inside each user group (never across users)."""
    return grouped[column].shift(periods)


def _rolling_mean(grouped, column: str, window: int) -> pd.Series:
    """Mean of the previous ``window`` days inside each user group."""
    return grouped[column].transform(
        lambda series: series.shift(1).rolling(window, min_periods=window).mean()
    )


def add_history(daily: pd.DataFrame) -> pd.DataFrame:
    """Attach the 28-day lookback features; drop days without full history."""
    frame = _complete_calendar(daily).copy()
    frame["days_to_month_end"] = (
        frame["date"].dt.days_in_month - frame["date"].dt.day
    ).astype(int)
    grouped = frame.groupby("user_id", sort=False)
    frame["lag_1_net"] = _shift(grouped, "net_bdt", 1)
    frame["lag_2_net"] = _shift(grouped, "net_bdt", 2)
    frame["lag_3_net"] = _shift(grouped, "net_bdt", 3)
    frame["lag_7_net"] = _shift(grouped, "net_bdt", 7)
    frame["lag_14_net"] = _shift(grouped, "net_bdt", 14)
    frame["lag_1_outflow"] = _shift(grouped, "outflow_bdt", 1)
    frame["lag_2_outflow"] = _shift(grouped, "outflow_bdt", 2)
    frame["lag_3_outflow"] = _shift(grouped, "outflow_bdt", 3)
    frame["lag_7_outflow"] = _shift(grouped, "outflow_bdt", 7)
    frame["lag_1_inflow"] = _shift(grouped, "inflow_bdt", 1)
    frame["roll_3_inflow"] = _rolling_mean(grouped, "inflow_bdt", 3)
    frame["roll_3_outflow"] = _rolling_mean(grouped, "outflow_bdt", 3)
    frame["roll_3_net"] = _rolling_mean(grouped, "net_bdt", 3)
    frame["roll_14_outflow"] = _rolling_mean(grouped, "outflow_bdt", 14)
    frame["roll_14_net"] = _rolling_mean(grouped, "net_bdt", 14)
    frame["max_7_outflow"] = grouped["outflow_bdt"].transform(
        lambda series: series.shift(1).rolling(7, min_periods=7).max()
    )
    frame["roll_7_inflow"] = _rolling_mean(grouped, "inflow_bdt", 7)
    frame["roll_7_outflow"] = _rolling_mean(grouped, "outflow_bdt", 7)
    frame["roll_7_net"] = _rolling_mean(grouped, "net_bdt", 7)
    frame["roll_28_inflow"] = _rolling_mean(grouped, "inflow_bdt", 28)
    frame["roll_28_outflow"] = _rolling_mean(grouped, "outflow_bdt", 28)
    frame["roll_28_net"] = _rolling_mean(grouped, "net_bdt", 28)
    frame["shortfall_last_7"] = grouped["is_shortfall_day"].transform(
        lambda series: series.shift(1).rolling(7, min_periods=7).sum()
    )
    # --- month-to-date state: where the user is inside the monthly budget ---
    # The generator's budget rule is monthly (income - spending - savings ->
    # cash-outs), so "how much of this month has already moved" is the strongest
    # signal for what the *rest* of the month will look like. Without it the
    # model reads a month-end cash-out spike as "this user simply spends a lot".
    month_key = frame["date"].dt.to_period("M")
    by_month = frame.groupby([frame["user_id"], month_key], sort=False)
    frame["mtd_inflow"] = by_month["inflow_bdt"].cumsum()
    frame["mtd_outflow"] = by_month["outflow_bdt"].cumsum()
    frame["mtd_cash_out_bdt"] = by_month["cash_out_bdt"].cumsum()
    frame["mtd_cash_out_count"] = by_month["cash_out_count"].cumsum()
    frame["roll_7_cash_out_bdt"] = _rolling_mean(grouped, "cash_out_bdt", 7)
    frame["roll_28_cash_out_bdt"] = _rolling_mean(grouped, "cash_out_bdt", 28)
    last_cash_out = frame["date"].where(frame["cash_out_count"].gt(0))
    days_since = frame["date"] - last_cash_out.groupby(frame["user_id"], sort=False).ffill()
    frame["days_since_cash_out"] = (
        days_since.dt.days.fillna(LOOKBACK_DAYS).clip(0, LOOKBACK_DAYS).astype(int)
    )
    history_columns = [col for col in FLOW_COLUMNS if col != "balance_end_bdt"]
    return frame.dropna(subset=history_columns).reset_index(drop=True)


def make_frame(
    db_path: str | Path | None = None,
    user_ids: Optional[Sequence[str]] = None,
    cfg: Optional[Mapping[str, Any]] = None,
) -> ForecastFrame:
    """Build the daily dataset (features for every day with full history)."""
    config = cfg or generator.load_config()
    path = Path(db_path) if db_path else user_features.default_db_path()
    transactions = user_features.load_transactions(path, user_ids)
    daily = _daily_flows(transactions, config)
    return ForecastFrame(daily=daily, features=add_history(daily))


def split_matrices(
    featured: pd.DataFrame, splits: pd.DataFrame, horizon_days: int = HORIZON_DAYS,
) -> dict:
    """Slice ``(X, y_inflow, y_outflow)`` per split for horizons 1..N.

    The target for horizon ``h`` is the flow ``h`` days ahead of the feature
    date (``shift(-h)`` inside each user, so no future row of another user can
    leak in). Days without a full horizon are dropped.
    """
    if horizon_days < 1:
        raise ValueError("horizon_days must be >= 1")
    frame = featured.merge(splits, on="user_id", how="inner")
    frame = frame.sort_values(["user_id", "date"], kind="stable").reset_index(drop=True)
    out: dict = {}
    for name in ("train", "val", "test"):
        part = frame.loc[frame["split"].eq(name)].copy()
        if part.empty:
            out[name] = {"X": part[FORECAST_FEATURE_COLUMNS], "dates": part[["user_id", "date"]]}
            continue
        users = part.groupby("user_id", sort=False)
        for horizon in range(1, horizon_days + 1):
            part[f"target_inflow_h{horizon}"] = users["inflow_bdt"].shift(-horizon)
            part[f"target_outflow_h{horizon}"] = users["outflow_bdt"].shift(-horizon)
        target_columns = [
            f"target_{flow}_h{horizon}"
            for horizon in range(1, horizon_days + 1)
            for flow in ("inflow", "outflow")
        ]
        part = part.dropna(subset=target_columns).reset_index(drop=True)
        payload: dict = {
            "X": part[FORECAST_FEATURE_COLUMNS].reset_index(drop=True),
            "dates": part[["user_id", "date"]].reset_index(drop=True),
        }
        for horizon in range(1, horizon_days + 1):
            payload[f"y_inflow_h{horizon}"] = part[f"target_inflow_h{horizon}"].reset_index(drop=True)
            payload[f"y_outflow_h{horizon}"] = part[f"target_outflow_h{horizon}"].reset_index(drop=True)
        out[name] = payload
    return out
