"""Ground-truth labels for the synthetic dataset.

Two kinds of labels live here, both **stored separately from the features**:

1. ``anomaly_labels`` -- which transactions were deliberately injected as
   anomalies and of which type (docs/DATA_ASSUMPTIONS.md §5).
2. ``user_labels`` -- the financial-consistency label
   ``is_stable_next_2_months``, produced from a hidden latent stability variable
   plus noise and random shocks (docs/DATA_ASSUMPTIONS.md §8). It is *not*
   computed from the same formula as the model features, which is what keeps the
   downstream evaluation non-circular.

This module never imports the API layer and is safe to use on its own.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# NOTE: generator imports this module, so the generator helpers are imported
# lazily inside the functions that need them (avoids a circular import).

ANOMALY_LABEL_COLUMNS = ["transaction_id", "user_id", "anomaly_type", "detail"]

USER_LABEL_COLUMNS = [
    "user_id",
    "latent_stability",
    "outcome_score",
    "shock",
    "is_stable_next_2_months",
]

ANOMALY_LABEL_DDL = """
CREATE TABLE IF NOT EXISTS anomaly_labels (
    transaction_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    anomaly_type TEXT NOT NULL,
    detail TEXT
);
"""

USER_LABEL_DDL = """
CREATE TABLE IF NOT EXISTS user_labels (
    user_id TEXT PRIMARY KEY,
    latent_stability REAL NOT NULL,
    outcome_score REAL NOT NULL,
    shock REAL NOT NULL,
    is_stable_next_2_months INTEGER NOT NULL
);
"""


def _choose(rng: np.random.Generator, options: Sequence[Any], weights: Optional[Sequence[float]] = None) -> Any:
    probabilities = None
    if weights is not None:
        array = np.asarray(weights, dtype=float)
        probabilities = array / array.sum()
    return options[int(rng.choice(len(options), p=probabilities))]


# ---------------------------------------------------------------------------
# latent variable (shared by the generator and the label)
# ---------------------------------------------------------------------------
def sample_latent_stability(cfg: Mapping[str, Any], user_ids: Sequence[str], seed: int) -> Dict[str, float]:
    """Draw the hidden stability value per user.

    The generator uses the same function (with the same seed) so that the weak
    behavioural influence and the final label refer to the *same* latent value.
    """
    from .generator import user_rng

    settings = cfg["stability_label"]
    values: Dict[str, float] = {}
    for user_id in user_ids:
        rng = user_rng(int(seed) + 13, user_id)
        values[user_id] = float(rng.normal(settings["latent_mean"], settings["latent_std"]))
    return values


def generate_stability_labels(
    cfg: Mapping[str, Any],
    users: pd.DataFrame,
    seed: int,
    latent: Optional[Mapping[str, float]] = None,
) -> pd.DataFrame:
    """Observed outcome = latent stability + noise + random shock.

    Nothing here reads the transaction features, so the label cannot be
    reconstructed exactly from them (anti-circularity protocol).
    """
    settings = cfg["stability_label"]
    user_ids = users["user_id"].tolist()
    latent_values = dict(latent) if latent is not None else sample_latent_stability(cfg, user_ids, seed)
    threshold = float(settings["threshold"])

    from .generator import user_rng

    rows: List[Dict[str, Any]] = []
    for user_id in user_ids:
        rng = user_rng(int(seed) + 31, user_id)
        noise = float(rng.normal(0.0, float(settings["noise_std"])))
        shock = 0.0
        if float(rng.random()) < float(settings["shock_prob"]):
            shock = float(rng.normal(settings["shock_mean"], settings["shock_std"]))
        score = float(latent_values[user_id]) + noise + shock
        rows.append(
            {
                "user_id": user_id,
                "latent_stability": round(float(latent_values[user_id]), 4),
                "outcome_score": round(score, 4),
                "shock": round(shock, 4),
                "is_stable_next_2_months": int(score > threshold),
            }
        )
    return pd.DataFrame(rows, columns=USER_LABEL_COLUMNS)


# ---------------------------------------------------------------------------
# injected anomalies
# ---------------------------------------------------------------------------
def inject_anomalies(
    cfg: Mapping[str, Any],
    transactions: pd.DataFrame,
    seed: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Inject ~``anomalies.rate`` of transactions as anomalies and label them.

    Returns the modified transactions plus a ground-truth label frame. Only the
    injected rows appear in the label frame; a missing row means "normal".
    """
    from .generator import fee_for_amount

    settings = cfg["anomalies"]
    frame = transactions.copy()
    if frame.empty:
        return frame, pd.DataFrame(columns=ANOMALY_LABEL_COLUMNS)

    rng = np.random.default_rng(int(seed))
    target = int(round(len(frame) * float(settings["rate"])))
    if target <= 0:
        return frame, pd.DataFrame(columns=ANOMALY_LABEL_COLUMNS)

    kinds = list(settings["types"])
    kind_weights = [float(settings["types"][kind]) for kind in kinds]
    chosen = sorted(int(index) for index in rng.choice(frame.index.to_numpy(), size=min(target, len(frame)), replace=False))

    labels: List[Dict[str, Any]] = []
    extra_rows: List[Dict[str, Any]] = []

    for index in chosen:
        row = frame.loc[index]
        kind = _choose(rng, kinds, kind_weights)

        if kind == "unusually_large":
            multiplier = float(settings["unusually_large_multiplier"])
            original = float(row["amount_bdt"])
            inflated = round(original * multiplier, 2)
            frame.at[index, "amount_bdt"] = inflated
            frame.at[index, "fee_bdt"] = fee_for_amount(cfg, row["channel"], inflated)
            detail = f"amount x{multiplier} ({original:.0f} -> {inflated:.0f})"

        elif kind == "unusual_time":
            hours = settings["unusual_time_hours"]
            hour = int(_choose(rng, hours))
            minute = int(rng.integers(0, 60))
            original_hour = int(pd.Timestamp(row["timestamp"]).hour)
            frame.at[index, "timestamp"] = pd.Timestamp(row["timestamp"]).normalize() + pd.Timedelta(
                hours=hour, minutes=minute
            )
            detail = f"hour {original_hour} -> {hour} (outside the normal window)"

        else:  # rapid_repeat
            repeat = settings["rapid_repeat"]
            count = int(repeat["count"])
            window = int(repeat["window_minutes"])
            base_ts = pd.Timestamp(row["timestamp"])
            for copy_index in range(1, count):
                clone = row.copy()
                clone["transaction_id"] = f"{row['transaction_id']}-r{copy_index}"
                clone["timestamp"] = base_ts + pd.Timedelta(minutes=int(rng.integers(1, window + 1)))
                extra_rows.append(clone)
                labels.append(
                    {
                        "transaction_id": clone["transaction_id"],
                        "user_id": clone["user_id"],
                        "anomaly_type": "rapid_repeat",
                        "detail": f"copy {copy_index + 1} of {count} within {window} min",
                    }
                )
            detail = f"{count} near-identical transactions within {window} min"

        labels.append(
            {
                "transaction_id": row["transaction_id"],
                "user_id": row["user_id"],
                "anomaly_type": kind,
                "detail": detail,
            }
        )

    if extra_rows:
        frame = pd.concat([frame, pd.DataFrame(extra_rows)], ignore_index=True)

    label_frame = pd.DataFrame(labels, columns=ANOMALY_LABEL_COLUMNS)
    label_frame = label_frame.drop_duplicates(subset=["transaction_id"]).reset_index(drop=True)
    return frame, label_frame


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------
def write_anomaly_labels(connection: sqlite3.Connection, labels: pd.DataFrame) -> None:
    """Store the ground-truth anomaly labels in their own table."""
    connection.execute(ANOMALY_LABEL_DDL)
    if not labels.empty:
        connection.executemany(
            "INSERT OR REPLACE INTO anomaly_labels VALUES (?, ?, ?, ?)",
            labels[ANOMALY_LABEL_COLUMNS].to_numpy().tolist(),
        )
    connection.commit()


def write_user_labels(connection: sqlite3.Connection, labels: pd.DataFrame) -> None:
    """Store the financial-consistency labels in their own table."""
    connection.execute(USER_LABEL_DDL)
    if not labels.empty:
        frame = labels[USER_LABEL_COLUMNS].copy()
        frame["is_stable_next_2_months"] = frame["is_stable_next_2_months"].astype(int)
        connection.executemany(
            "INSERT OR REPLACE INTO user_labels VALUES (?, ?, ?, ?, ?)",
            frame.to_numpy().tolist(),
        )
    connection.commit()


def load_anomaly_labels(db_path: str | Path) -> pd.DataFrame:
    """Read the anomaly labels table."""
    connection = sqlite3.connect(str(db_path))
    try:
        return pd.read_sql_query("SELECT * FROM anomaly_labels", connection)
    finally:
        connection.close()


def load_user_labels(db_path: str | Path) -> pd.DataFrame:
    """Read the financial-consistency labels table."""
    connection = sqlite3.connect(str(db_path))
    try:
        return pd.read_sql_query("SELECT * FROM user_labels", connection)
    finally:
        connection.close()


