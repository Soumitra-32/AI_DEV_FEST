"""Shared feature pipeline (data layer).

Both the offline evaluation in ``backend/ml`` and the online services in
``backend/app/services`` build their inputs here, so a feature can never mean two
different things in training and in the app.

Everything here is **label-free**: the financial-consistency label lives in the
``user_labels`` table and is deliberately never joined in (see
``backend/tests/test_no_leakage.py``). Demographic columns are returned for the
fairness analysis only and are excluded from :data:`FEATURE_COLUMNS`.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from .generator import load_config, resolve_db_path

# ---------------------------------------------------------------------------
# column contracts
# ---------------------------------------------------------------------------
ID_COLUMNS = ["user_id"]
DEMOGRAPHIC_COLUMNS = ["persona", "district", "income_band"]

#: Model inputs. Nothing here is derived from the label tables.
FEATURE_COLUMNS: List[str] = [
    "income_mean_bdt",
    "income_cv",
    "income_days_per_month",
    "spend_mean_bdt",
    "spend_cv",
    "cash_out_count_per_month",
    "cash_out_volume_per_month_bdt",
    "cash_out_share_of_outflow",
    "fee_per_month_bdt",
    "fee_share_of_income",
    "balance_mean_bdt",
    "balance_min_bdt",
    "balance_volatility",
    "shortfall_days_per_month",
    "month_end_spend_ratio",
    "weekend_spend_ratio",
]

USER_FEATURE_COLUMNS = ID_COLUMNS + DEMOGRAPHIC_COLUMNS + ["months_observed"] + FEATURE_COLUMNS


def default_db_path() -> Path:
    """Database path from ``backend/data/config.yaml``."""
    return resolve_db_path(load_config())


def _connect(db_path: str | Path) -> sqlite3.Connection:
    """Read-only connection: features can never mutate the dataset."""
    path = Path(db_path)
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def _read(db_path: str | Path, query: str, params: Sequence[Any] = ()) -> pd.DataFrame:
    connection = _connect(db_path)
    try:
        return pd.read_sql_query(query, connection, params=tuple(params))
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# loaders
# ---------------------------------------------------------------------------
def load_transactions(db_path: str | Path, user_ids: Optional[Sequence[str]] = None) -> pd.DataFrame:
    """Transactions, oldest first, with ``timestamp`` parsed."""
    if user_ids is None:
        frame = _read(db_path, "SELECT * FROM transactions")
    else:
        ids = list(user_ids)
        if not ids:
            return pd.DataFrame(columns=["transaction_id", "user_id", "timestamp"])
        placeholders = ", ".join("?" for _ in ids)
        frame = _read(
            db_path, f"SELECT * FROM transactions WHERE user_id IN ({placeholders})", ids
        )
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame.sort_values(["user_id", "timestamp", "transaction_id"], kind="stable").reset_index(drop=True)


def load_users(db_path: str | Path, user_ids: Optional[Sequence[str]] = None) -> pd.DataFrame:
    """User rows (persona, district, income band, cohort)."""
    if user_ids is None:
        return _read(db_path, "SELECT * FROM users")
    ids = list(user_ids)
    if not ids:
        return pd.DataFrame(columns=["user_id", "persona", "district", "income_band", "cohort"])
    placeholders = ", ".join("?" for _ in ids)
    return _read(db_path, f"SELECT * FROM users WHERE user_id IN ({placeholders})", ids)


def load_splits(db_path: str | Path) -> pd.DataFrame:
    """The user-level train/val/test/demo assignment."""
    return _read(db_path, "SELECT user_id, split FROM splits")


def load_user_labels(db_path: str | Path) -> pd.DataFrame:
    """The evaluation label — never merged into features automatically."""
    return _read(db_path, "SELECT * FROM user_labels")


def load_anomaly_labels(db_path: str | Path) -> pd.DataFrame:
    """Ground-truth anomaly rows — kept separate from the features too."""
    return _read(db_path, "SELECT * FROM anomaly_labels")


# ---------------------------------------------------------------------------
# per user-day flows (forecasting input)
# ---------------------------------------------------------------------------
def daily_flows(transactions: pd.DataFrame) -> pd.DataFrame:
    """Collapse transactions into one row per user per day.

    Columns: inflow, outflow, fees, cash-out volume, transaction count, whether the
    wallet came up short that day, and the closing balance.
    """
    if transactions.empty:
        return pd.DataFrame(
            columns=[
                "user_id",
                "date",
                "inflow_bdt",
                "outflow_bdt",
                "fee_bdt",
                "cash_out_bdt",
                "tx_count",
                "is_shortfall_day",
                "balance_end_bdt",
                "net_bdt",
            ]
        )

    frame = transactions.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame["date"] = frame["timestamp"].dt.normalize()
    is_income = frame["type"].eq("income").to_numpy()
    is_cash_out = frame["channel"].eq("cash_out").to_numpy()
    frame["_inflow"] = np.where(is_income, frame["amount_bdt"].to_numpy(dtype=float), 0.0)
    frame["_outflow"] = np.where(is_income, 0.0, frame["amount_bdt"].to_numpy(dtype=float))
    frame["_cash_out"] = np.where(is_cash_out, frame["amount_bdt"].to_numpy(dtype=float), 0.0)
    frame = frame.sort_values(["user_id", "timestamp", "transaction_id"], kind="stable")

    flows = frame.groupby(["user_id", "date"], as_index=False).agg(
        inflow_bdt=("_inflow", "sum"),
        outflow_bdt=("_outflow", "sum"),
        fee_bdt=("fee_bdt", "sum"),
        cash_out_bdt=("_cash_out", "sum"),
        tx_count=("transaction_id", "count"),
        shortfall_events=("is_shortfall", "sum"),
        balance_end_bdt=("balance_after", "last"),
    )
    flows["is_shortfall_day"] = (flows["shortfall_events"] > 0).astype(int)
    flows["net_bdt"] = (
        flows["inflow_bdt"] - flows["outflow_bdt"] - flows["fee_bdt"]
    ).round(2)
    return flows.drop(columns=["shortfall_events"])


# ---------------------------------------------------------------------------
# per-user features
# ---------------------------------------------------------------------------
def _ratio(frame: pd.DataFrame, numerator: pd.Series, denominator: pd.Series, column: str) -> float:
    """Mean of ``column`` over the numerator rows vs the denominator rows."""
    top = frame.loc[numerator, column]
    bottom = frame.loc[denominator, column]
    if top.empty or bottom.empty or float(bottom.mean()) <= 0:
        return 1.0
    return round(float(top.mean() / bottom.mean()), 4)


def user_features(
    cfg: Mapping[str, Any],
    transactions: pd.DataFrame,
    users: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """One row per user with the label-free features the models consume.

    Missing values default to 0 for levels and 1.0 for the two spending ratios
    (a ratio of 1.0 means "no month-end or weekend pattern"), so a model never has
    to deal with NaNs.
    """
    if transactions.empty:
        return pd.DataFrame(columns=USER_FEATURE_COLUMNS)

    frame = transactions.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame["date"] = frame["timestamp"].dt.normalize()
    frame["month"] = frame["timestamp"].dt.to_period("M").astype(str)
    frame["day_of_month"] = frame["timestamp"].dt.day
    frame["weekday"] = frame["timestamp"].dt.weekday
    frame = frame.sort_values(["user_id", "timestamp", "transaction_id"], kind="stable")

    is_income = frame["type"].eq("income").to_numpy()
    is_cash_out = frame["channel"].eq("cash_out").to_numpy()
    frame["_inflow"] = np.where(is_income, frame["amount_bdt"].to_numpy(dtype=float), 0.0)
    frame["_outflow"] = np.where(is_income, 0.0, frame["amount_bdt"].to_numpy(dtype=float))
    frame["_cash_out"] = np.where(is_cash_out, frame["amount_bdt"].to_numpy(dtype=float), 0.0)
    frame["_shortfall"] = frame["is_shortfall"].to_numpy(dtype=int)

    monthly = frame.groupby(["user_id", "month"], as_index=False).agg(
        inflow_bdt=("_inflow", "sum"),
        outflow_bdt=("_outflow", "sum"),
        cash_out_bdt=("_cash_out", "sum"),
        fee_bdt=("fee_bdt", "sum"),
    )
    monthly["non_cash_out_outflow_bdt"] = monthly["outflow_bdt"] - monthly["cash_out_bdt"]

    cash_out_months = (
        frame.loc[frame["_cash_out"] > 0]
        .groupby(["user_id", "month"], as_index=False)
        .agg(cash_out_count=("transaction_id", "count"))
    )
    income_days = (
        frame.loc[frame["_inflow"] > 0]
        .groupby(["user_id", "month"], as_index=False)
        .agg(income_days=("date", "nunique"))
    )
    shortfall_days = (
        frame.loc[frame["_shortfall"] > 0]
        .groupby(["user_id", "month"], as_index=False)
        .agg(shortfall_days=("date", "nunique"))
    )
    for extra in (cash_out_months, income_days, shortfall_days):
        monthly = monthly.merge(extra, on=["user_id", "month"], how="left")
    for column in ("cash_out_count", "income_days", "shortfall_days"):
        monthly[column] = monthly[column].fillna(0.0)

    summary = monthly.groupby("user_id", as_index=False).agg(
        months_observed=("month", "nunique"),
        income_mean_bdt=("inflow_bdt", "mean"),
        income_std_bdt=("inflow_bdt", "std"),
        spend_mean_bdt=("non_cash_out_outflow_bdt", "mean"),
        spend_std_bdt=("non_cash_out_outflow_bdt", "std"),
        cash_out_count_per_month=("cash_out_count", "mean"),
        cash_out_volume_per_month_bdt=("cash_out_bdt", "mean"),
        fee_per_month_bdt=("fee_bdt", "mean"),
        income_days_per_month=("income_days", "mean"),
        shortfall_days_per_month=("shortfall_days", "mean"),
        inflow_total=("inflow_bdt", "sum"),
        outflow_total=("outflow_bdt", "sum"),
        cash_out_total=("cash_out_bdt", "sum"),
        fee_total=("fee_bdt", "sum"),
    )

    safe_divide = lambda top, bottom: (top / bottom).replace([np.inf, -np.inf], np.nan)  # noqa: E731
    summary["income_cv"] = safe_divide(summary["income_std_bdt"], summary["income_mean_bdt"])
    summary["spend_cv"] = safe_divide(summary["spend_std_bdt"], summary["spend_mean_bdt"])
    summary["cash_out_share_of_outflow"] = safe_divide(
        summary["cash_out_total"], summary["outflow_total"]
    )
    summary["fee_share_of_income"] = safe_divide(summary["fee_total"], summary["inflow_total"])

    daily_balance = frame.groupby(["user_id", "date"], as_index=False).agg(
        balance_end_bdt=("balance_after", "last")
    )
    balance_stats = daily_balance.groupby("user_id", as_index=False).agg(
        balance_mean_bdt=("balance_end_bdt", "mean"),
        balance_min_bdt=("balance_end_bdt", "min"),
        balance_volatility=("balance_end_bdt", "std"),
    )
    summary = summary.merge(balance_stats, on="user_id", how="left")

    daily = frame.groupby(["user_id", "date", "day_of_month", "weekday"], as_index=False).agg(
        outflow=("_outflow", "sum")
    )
    weekend_days = [int(day) for day in cfg["dataset"]["weekend_weekdays"]]
    month_end_ratio = (
        daily.groupby("user_id")
        .apply(
            lambda part: _ratio(
                part, part["day_of_month"] >= 28, part["day_of_month"].between(10, 20), "outflow"
            ),
            include_groups=False,
        )
        .rename("month_end_spend_ratio")
        .reset_index()
    )
    weekend_ratio = (
        daily.groupby("user_id")
        .apply(
            lambda part: _ratio(
                part,
                part["weekday"].isin(weekend_days),
                ~part["weekday"].isin(weekend_days),
                "outflow",
            ),
            include_groups=False,
        )
        .rename("weekend_spend_ratio")
        .reset_index()
    )
    summary = summary.merge(month_end_ratio, on="user_id", how="left")
    summary = summary.merge(weekend_ratio, on="user_id", how="left")

    if users is not None:
        summary = summary.merge(users[["user_id", *DEMOGRAPHIC_COLUMNS]], on="user_id", how="left")
    else:
        for column in DEMOGRAPHIC_COLUMNS:
            summary[column] = None

    # ratios default to 1.0 ("no pattern"), levels to 0
    ratio_defaults = {"month_end_spend_ratio": 1.0, "weekend_spend_ratio": 1.0}
    for column in FEATURE_COLUMNS:
        values = pd.to_numeric(summary[column], errors="coerce")
        summary[column] = values.fillna(ratio_defaults.get(column, 0.0))

    return (
        summary[USER_FEATURE_COLUMNS]
        .sort_values("user_id", kind="stable")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# helpers for services and evaluation
# ---------------------------------------------------------------------------
def feature_row(features: pd.DataFrame, user_id: str) -> Dict[str, float]:
    """Feature dict for a single user (KeyError when the user has no features)."""
    match = features.loc[features["user_id"].eq(user_id)]
    if match.empty:
        raise KeyError(f"no features for user {user_id}")
    row = match.iloc[0]
    return {column: float(row[column]) for column in FEATURE_COLUMNS}


def attach_split(features: pd.DataFrame, splits: pd.DataFrame) -> pd.DataFrame:
    """Merge the evaluation split. Never a model input — only for scoring."""
    return features.merge(splits, on="user_id", how="left")




