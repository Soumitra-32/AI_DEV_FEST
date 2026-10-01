"""User-level train / validation / test split.

Anti-circularity protocol (docs/DATA_ASSUMPTIONS.md §10):

* splits are assigned **per user**, never per row;
* the ``test`` users come from the separately seeded cohort
  (``seeds.test``), so they are not re-draws of the training stream;
* the demo user (cohort ``demo``) is excluded from train/val/test so demo data
  can never leak into an evaluation.

The split is written to its own ``splits`` table and is fully reproducible from
``seeds.split``.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

SPLIT_COLUMNS = ["user_id", "split"]

SPLIT_DDL = """
CREATE TABLE IF NOT EXISTS splits (
    user_id TEXT PRIMARY KEY,
    split TEXT NOT NULL
);
"""

EVALUATION_SPLITS = ("train", "val", "test")
DEMO_SPLIT = "demo"


def cohort_sizes(cfg: Mapping[str, Any], n_users: int) -> Tuple[int, int]:
    """How many users to generate for the training cohort and the test cohort.

    The global proportions in ``config.split`` decide the test cohort size, so
    the resulting splits match 70/15/15 of ``n_users`` exactly.
    """
    settings = cfg["split"]
    n_test = int(round(n_users * float(settings["test"])))
    return n_users - n_test, n_test


def assign_splits(
    cfg: Mapping[str, Any],
    users: pd.DataFrame,
    seed: int | None = None,
) -> pd.DataFrame:
    """Assign every user to exactly one of train / val / test / demo."""
    settings = cfg["split"]
    rng = np.random.default_rng(int(settings.get("seed", 0) if seed is None else seed))

    demo_mask = users["cohort"].eq(DEMO_SPLIT)
    test_mask = users["cohort"].eq("test")
    train_val_mask = users["cohort"].eq("train_val")

    n_eval = int((~demo_mask).sum())
    n_test_target = int(round(n_eval * float(settings["test"])))
    n_val_target = int(round(n_eval * float(settings["val"])))
    n_train_target = n_eval - n_test_target - n_val_target

    test_users = users.loc[test_mask, "user_id"].tolist()
    if len(test_users) != n_test_target:
        raise ValueError(
            "test cohort size does not match config.split.test: "
            f"generated {len(test_users)} users but expected {n_test_target}. "
            "Use backend.data.split.cohort_sizes() when generating cohorts."
        )

    train_val_users = users.loc[train_val_mask, "user_id"].to_numpy()
    if len(train_val_users) != n_train_target + n_val_target:
        raise ValueError(
            "train/val cohort size does not match config.split: "
            f"generated {len(train_val_users)} users but expected {n_train_target + n_val_target}."
        )

    order = rng.permutation(len(train_val_users))
    shuffled = train_val_users[order]
    train_users = shuffled[:n_train_target]
    val_users = shuffled[n_train_target:]

    rows: list[Dict[str, str]] = []
    rows += [{"user_id": user_id, "split": "train"} for user_id in train_users]
    rows += [{"user_id": user_id, "split": "val"} for user_id in val_users]
    rows += [{"user_id": user_id, "split": "test"} for user_id in test_users]
    rows += [{"user_id": user_id, "split": DEMO_SPLIT} for user_id in users.loc[demo_mask, "user_id"]]

    splits = pd.DataFrame(rows, columns=SPLIT_COLUMNS)
    return splits.sort_values("user_id", kind="stable").reset_index(drop=True)


def write_splits(connection: sqlite3.Connection, splits: pd.DataFrame) -> None:
    """Store the split assignment in its own table."""
    connection.execute(SPLIT_DDL)
    connection.executemany(
        "INSERT OR REPLACE INTO splits VALUES (?, ?)",
        splits[SPLIT_COLUMNS].to_numpy().tolist(),
    )
    connection.commit()


def load_splits(db_path: str | Path) -> pd.DataFrame:
    """Read the split assignment."""
    connection = sqlite3.connect(str(db_path))
    try:
        return pd.read_sql_query("SELECT user_id, split FROM splits", connection)
    finally:
        connection.close()


def split_sizes(splits: pd.DataFrame) -> Dict[str, int]:
    """Count users per split (``train`` / ``val`` / ``test`` / ``demo``)."""
    counts = splits["split"].value_counts()
    return {name: int(counts.get(name, 0)) for name in (*EVALUATION_SPLITS, DEMO_SPLIT)}


def users_in_split(splits: pd.DataFrame, split: str) -> Sequence[str]:
    """User ids belonging to one split."""
    return splits.loc[splits["split"].eq(split), "user_id"].tolist()

