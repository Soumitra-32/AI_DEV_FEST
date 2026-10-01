"""Seed the demo user "Rahim" (docs/DATA_ASSUMPTIONS.md §11).

Rahim is its own cohort (``demo``) and is never part of train/val/test.

His profile is fixed in ``backend/data/config.yaml`` -> ``demo_user``:

* 5 cash-outs per month averaging ৳3,500 -> ৳17,500 of cash-outs per month;
* at the assumed 1.85% cash-out rate that is ৳323.75 (~"৳320" in the demo).

Usage:
    python backend/scripts/seed_demo_user.py            # into the configured DB
    python backend/scripts/seed_demo_user.py --db tmp.db

The script always prints the *computed* monthly cash-out total and fee, so the
number quoted in the demo always follows from the data.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:  # allow running the file directly
    sys.path.insert(0, str(REPO_ROOT))

from backend.data import generator

DEMO_COHORT = "demo"


def demo_profile(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """The persona-shaped profile block the generator expects for Rahim."""
    settings = cfg["demo_user"]
    return {
        "income": settings["income"],
        "spend": settings["spend"],
        "bills": settings["bills"],
        "cash_out": settings["cash_out"],
        "savings_rate": settings.get("savings_rate"),
    }


def build_demo_user(cfg: Mapping[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Rahim's ``users`` row and his full transaction history (balances included)."""
    settings = cfg["demo_user"]
    user = {
        "user_id": settings["user_id"],
        "persona": settings["persona"],
        "district": settings["district"],
        "income_band": settings["income_band"],
        "age_band": settings["age_band"],
        "language_pref": settings["language_pref"],
        "cohort": DEMO_COHORT,
    }
    users = pd.DataFrame([user], columns=generator.USER_COLUMNS)
    # Rahim follows the dataset horizon so the demo profile always lines up with
    # the generated history (demo_user.months documents the expected 6 months).
    days = generator.dataset_days(cfg)
    transactions = generator.generate_user_transactions(
        cfg,
        user,
        demo_profile(cfg),
        days,
        int(settings["seed"]),
        latent=0.0,
        pressure=settings.get("month_end_pressure"),
    )
    transactions = generator.finalize_balances(cfg, transactions, users, seed=int(settings["seed"]))
    return users, transactions


def demo_fee_summary(transactions: pd.DataFrame) -> Dict[str, float]:
    """Computed cash-out volume and fee per month for Rahim (never hardcoded)."""
    cash_outs = transactions.loc[transactions["channel"].eq("cash_out")]
    months = int(transactions["timestamp"].dt.to_period("M").nunique()) or 1
    count = int(len(cash_outs))
    total_amount = float(cash_outs["amount_bdt"].sum())
    total_fee = float(cash_outs["fee_bdt"].sum())
    return {
        "months": months,
        "cash_out_count": count,
        "cash_outs_per_month": round(count / months, 2),
        "avg_cash_out_bdt": round(total_amount / count, 2) if count else 0.0,
        "monthly_cash_out_bdt": round(total_amount / months, 2),
        "monthly_fee_bdt": round(total_fee / months, 2),
    }


def seed_demo_user(
    db_path: str | Path,
    cfg: Optional[Mapping[str, Any]] = None,
    connection: Optional[Any] = None,
) -> Dict[str, float]:
    """Insert Rahim into an existing database (idempotent: rows are replaced)."""
    config = cfg if cfg is not None else generator.load_config()
    users, transactions = build_demo_user(config)
    owns_connection = connection is None
    conn = connection if connection is not None else generator.connect(db_path)
    try:
        generator.init_core_tables(conn)
        generator.write_core(conn, users, transactions)
    finally:
        if owns_connection:
            conn.close()
    return demo_fee_summary(transactions)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the demo user Rahim into SQLite.")
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument("--db", default=None, help="path to the SQLite database")
    args = parser.parse_args(argv)

    cfg = generator.load_config(args.config)
    db_path = generator.resolve_db_path(cfg, args.db)
    if not Path(db_path).exists():
        print(f"database not found: {db_path}")
        print("run: python backend/scripts/generate_data.py")
        return 1

    summary = seed_demo_user(db_path, cfg)
    expected = float(cfg["demo_user"]["expected_monthly_fee_bdt"])
    print(f"seeded demo user '{cfg['demo_user']['user_id']}' into {db_path}")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print(f"  expected_monthly_fee_bdt: {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

