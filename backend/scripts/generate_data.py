"""Generate the full synthetic dataset and write it to SQLite.

Pipeline (docs/DATA_ASSUMPTIONS.md):

1. train/validation cohort  -> users + transactions (seed ``seeds.train``)
2. held-out test cohort     -> users + transactions (seed ``seeds.test``)
3. anomaly injection        -> ``anomaly_labels`` (ground truth, separate table)
4. balances                 -> ``balance_after``, ``is_shortfall``
5. demo user "Rahim"        -> cohort ``demo``, excluded from evaluation
6. user-level split         -> ``splits`` (70/15/15, no user overlap)
7. stability labels         -> ``user_labels`` (latent + noise + shocks)
8. provenance               -> ``generation_meta``

Usage:
    python backend/scripts/generate_data.py
    python backend/scripts/generate_data.py --n-users 60 --months 3 --db tmp.db
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # allow running the file directly
    sys.path.insert(0, str(REPO_ROOT))

from backend.data import generator, labels, split
from backend.scripts import seed_demo_user


def baseline_summary(users: pd.DataFrame, transactions: pd.DataFrame) -> Dict[str, float]:
    """The rule-based baselines the models must beat (plan.txt section 4)."""
    months = int(transactions["timestamp"].dt.to_period("M").nunique()) or 1
    user_count = int(users["user_id"].nunique()) or 1
    cash_outs = transactions.loc[transactions["channel"].eq("cash_out")]
    outflow = transactions.loc[transactions["type"].ne("income")]
    shortfall_events = transactions.loc[transactions["is_shortfall"].eq(1), ["user_id", "timestamp"]]
    shortfall_days = int(
        shortfall_events.assign(day=shortfall_events["timestamp"].dt.normalize())
        .groupby("user_id")["day"]
        .nunique()
        .sum()
    )
    outflow_total = float(outflow["amount_bdt"].sum()) or 1.0

    return {
        "users": user_count,
        "transactions": int(len(transactions)),
        "months": months,
        "users_with_cash_outs": int(cash_outs["user_id"].nunique()),
        "cash_out_share_of_outflow": round(float(cash_outs["amount_bdt"].sum()) / outflow_total, 4),
        "avg_monthly_fee_bdt": round(float(transactions["fee_bdt"].sum()) / months / user_count, 2),
        "avg_shortfall_days_per_user_month": round(shortfall_days / months / user_count, 2),
    }


def build_dataset(
    cfg: Mapping[str, Any],
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the whole generator pipeline in memory (no file writes).

    Returns ``(users, transactions, anomaly_labels, splits, user_labels)``.
    """
    n_users = int(cfg["dataset"]["n_users"])
    n_train_val, n_test = split.cohort_sizes(cfg, n_users)

    users_train, tx_train, labels_train, latent_train = generator.generate_cohort(
        cfg, seed=int(cfg["seeds"]["train"]), n_users=n_train_val, user_id_start=1, cohort="train_val"
    )
    users_test, tx_test, labels_test, latent_test = generator.generate_cohort(
        cfg,
        seed=int(cfg["seeds"]["test"]),
        n_users=n_test,
        user_id_start=n_train_val + 1,
        cohort="test",
    )
    users_demo, tx_demo = seed_demo_user.build_demo_user(cfg)

    users = pd.concat([users_train, users_test, users_demo], ignore_index=True)
    transactions = pd.concat([tx_train, tx_test, tx_demo], ignore_index=True)
    anomaly_labels = pd.concat([labels_train, labels_test], ignore_index=True)
    latent = {**latent_train, **latent_test, cfg["demo_user"]["user_id"]: 0.0}

    # GAP-02: the configured split seed was dead (assign_splits fell back to
    # seed 0). Wire it so seeds.split in config.yaml actually governs the split.
    splits = split.assign_splits(cfg, users, seed=int(cfg["seeds"]["split"]))
    user_labels = labels.generate_stability_labels(
        cfg, users, seed=int(cfg["seeds"]["label"]), latent=latent
    )
    return users, transactions, anomaly_labels, splits, user_labels


def write_dataset(
    db_path: str | Path,
    cfg: Mapping[str, Any],
    users: pd.DataFrame,
    transactions: pd.DataFrame,
    anomaly_labels: pd.DataFrame,
    splits: pd.DataFrame,
    user_labels: pd.DataFrame,
) -> None:
    """Write every table into a freshly created SQLite database."""
    meta = {
        "generator_version": cfg["meta"]["generator_version"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_users": cfg["dataset"]["n_users"],
        "months": cfg["dataset"]["months"],
        "start_date": cfg["dataset"]["start_date"],
        "seed_train": cfg["seeds"]["train"],
        "seed_test": cfg["seeds"]["test"],
        "seed_split": cfg["seeds"]["split"],
        "seed_anomaly": cfg["seeds"]["anomaly"],
        "seed_label": cfg["seeds"]["label"],
        "cash_out_fee_percent_assumed": cfg["fee_rates"]["by_channel"]["cash_out"],
    }
    connection = generator.connect(db_path, replace=True)
    try:
        generator.write_core(connection, users, transactions, meta=meta)
        labels.write_anomaly_labels(connection, anomaly_labels)
        labels.write_user_labels(connection, user_labels)
        split.write_splits(connection, splits)
    finally:
        connection.close()


def report(
    db_path: str | Path,
    cfg: Mapping[str, Any],
    users: pd.DataFrame,
    transactions: pd.DataFrame,
    anomaly_labels: pd.DataFrame,
    splits: pd.DataFrame,
    user_labels: pd.DataFrame,
) -> None:
    """Print the Phase 1 check: sizes, splits, baselines and the Rahim numbers."""
    sizes = split.split_sizes(splits)
    stable_rate = float(user_labels["is_stable_next_2_months"].mean())

    print(f"database: {db_path}")
    print(f"users: {len(users)}  transactions: {len(transactions)}")
    print(f"anomalies injected: {len(anomaly_labels)} ({len(anomaly_labels) / max(len(transactions), 1):.2%})")
    print("splits: " + "  ".join(f"{name}={count}" for name, count in sizes.items()) + f"  total={sum(sizes.values())}")
    print(f"stable-rate (label): {stable_rate:.3f}")
    for key, value in baseline_summary(users, transactions).items():
        print(f"baseline {key}: {value}")

    rahim_id = cfg["demo_user"]["user_id"]
    rahim = seed_demo_user.demo_fee_summary(transactions.loc[transactions["user_id"].eq(rahim_id)])
    expected = float(cfg["demo_user"]["expected_monthly_fee_bdt"])
    print(
        "demo user Rahim: "
        f"{rahim['cash_outs_per_month']} cash-outs/month, "
        f"avg taka {rahim['avg_cash_out_bdt']:.0f}, "
        f"monthly fee taka {rahim['monthly_fee_bdt']:.2f} (expected {expected:.2f})"
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the synthetic Shonchoy dataset.")
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument("--db", default=None, help="path to the SQLite database")
    parser.add_argument("--n-users", type=int, default=None, help="override dataset.n_users")
    parser.add_argument("--months", type=int, default=None, help="override dataset.months")
    args = parser.parse_args(argv)

    cfg = generator.load_config(args.config)
    if args.n_users is not None:
        cfg["dataset"]["n_users"] = int(args.n_users)
    if args.months is not None:
        cfg["dataset"]["months"] = int(args.months)

    db_path = generator.resolve_db_path(cfg, args.db)
    users, transactions, anomaly_labels, splits, user_labels = build_dataset(cfg)
    write_dataset(db_path, cfg, users, transactions, anomaly_labels, splits, user_labels)

    stored_transactions = generator.read_table(db_path, "transactions")
    report(db_path, cfg, users, stored_transactions, anomaly_labels, splits, user_labels)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


