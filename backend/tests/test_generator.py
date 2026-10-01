"""Tests for the synthetic data generator (Phase 1 acceptance criteria).

These checks cover the things the rest of the project relies on: the schema the
API expects, fees that follow the assumed rate table, month-end pressure that is
only injected for some users, labelled anomalies, and — most importantly — that
Rahim's demo profile really does produce the ~৳320/month fee figure.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd
import pytest

from backend.data import generator
from backend.scripts import seed_demo_user

DOC_PATH = generator.REPO_ROOT / "docs" / "DATA_ASSUMPTIONS.md"

REQUIRED_SECTIONS = [
    "meta",
    "seeds",
    "dataset",
    "split",
    "fee_rates",
    "personas",
    "income_bands",
    "age_bands",
    "language_pref",
    "income_categories",
    "channel_by_category",
    "month_end_pressure",
    "anomalies",
    "stability_label",
    "districts",
    "district_persona_mix",
    "demo_user",
]


def _auc(scores: pd.Series, target: pd.Series) -> float:
    """Rank-based AUC (keeps the data tests free of scikit-learn)."""
    frame = pd.DataFrame(
        {"score": scores.to_numpy(dtype=float), "target": target.to_numpy(dtype=int)}
    )
    positives = int(frame["target"].sum())
    negatives = int(len(frame) - positives)
    if positives == 0 or negatives == 0:
        return 0.5
    ordered = frame.sort_values("score", kind="stable").reset_index(drop=True)
    ranks = pd.Series(np.arange(1, len(ordered) + 1))
    rank_sum = float(ranks[ordered["target"].eq(1)].sum())
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


# ---------------------------------------------------------------------------
# configuration and documentation
# ---------------------------------------------------------------------------
def test_config_exposes_every_section(base_config: dict) -> None:
    for section in REQUIRED_SECTIONS:
        assert section in base_config, f"missing config section: {section}"


def test_personas_and_districts_are_documented(base_config: dict) -> None:
    document = DOC_PATH.read_text(encoding="utf-8")
    for persona in base_config["personas"]:
        assert f"`{persona}`" in document, f"persona {persona} is not in DATA_ASSUMPTIONS.md"
    assert len(base_config["districts"]) >= 8
    for district in base_config["districts"]:
        assert district["type"] in base_config["district_persona_mix"]


def test_fee_rates_are_flagged_as_assumptions(base_config: dict) -> None:
    note = base_config["fee_rates"]["note"].lower()
    assert "assum" in note and "not official" in note
    assert float(base_config["fee_rates"]["by_channel"]["cash_out"]) > 0


# ---------------------------------------------------------------------------
# determinism and schema
# ---------------------------------------------------------------------------
def test_same_seed_produces_identical_data(small_config: dict) -> None:
    first_users, first_tx, first_labels, first_latent = generator.generate_cohort(
        small_config, seed=42, n_users=4
    )
    second_users, second_tx, second_labels, second_latent = generator.generate_cohort(
        small_config, seed=42, n_users=4
    )
    pd.testing.assert_frame_equal(first_users, second_users)
    pd.testing.assert_frame_equal(first_tx, second_tx)
    pd.testing.assert_frame_equal(first_labels, second_labels)
    assert first_latent == second_latent


def test_different_seeds_produce_different_behaviour(small_config: dict) -> None:
    _, train_tx, _, _ = generator.generate_cohort(small_config, seed=42, n_users=4)
    _, test_tx, _, _ = generator.generate_cohort(small_config, seed=1337, n_users=4)
    assert not np.array_equal(train_tx["amount_bdt"].to_numpy(), test_tx["amount_bdt"].to_numpy())


def test_users_table_schema(small_dataset) -> None:
    users = small_dataset.users
    assert list(users.columns) == generator.USER_COLUMNS
    assert users["user_id"].is_unique
    assert set(users["income_band"]).issubset(set(generator.load_config()["income_bands"]))
    assert users["persona"].isin(generator.load_config()["personas"]).all()


def test_transactions_table_schema(small_dataset, small_config: dict) -> None:
    transactions = small_dataset.transactions
    assert list(transactions.columns) == generator.TRANSACTION_COLUMNS
    assert transactions["transaction_id"].is_unique
    assert (transactions["amount_bdt"] > 0).all()
    assert (transactions["fee_bdt"] >= 0).all()
    assert set(transactions["type"]).issubset({"income", "expense", "cash_out"})
    assert set(transactions["is_shortfall"]).issubset({0, 1})
    assert transactions["user_id"].isin(small_dataset.users["user_id"]).all()
    days = generator.dataset_days(small_config)
    assert transactions["timestamp"].between(days[0], days[-1] + pd.Timedelta(days=1)).all()


# ---------------------------------------------------------------------------
# fees and balances (the numbers the demo quotes)
# ---------------------------------------------------------------------------
def test_cash_out_fee_follows_the_assumed_rate(base_config: dict, small_dataset) -> None:
    rate = float(base_config["fee_rates"]["by_channel"]["cash_out"]) / 100.0
    cash_outs = small_dataset.transactions.loc[small_dataset.transactions["channel"].eq("cash_out")]
    assert len(cash_outs) > 0
    # the fee is the assumed percentage rounded to the nearest paisa
    difference = (cash_outs["fee_bdt"] - cash_outs["amount_bdt"] * rate).abs()
    assert (difference <= 0.01).all(), float(difference.max())


def test_channels_with_zero_rate_carry_no_fee(base_config: dict, small_dataset) -> None:
    free_channels = [
        channel for channel, rate in base_config["fee_rates"]["by_channel"].items() if float(rate) == 0.0
    ]
    fee_free = small_dataset.transactions.loc[small_dataset.transactions["channel"].isin(free_channels)]
    assert len(fee_free) > 0
    assert (fee_free["fee_bdt"] == 0).all()


def test_balance_is_a_chronological_running_balance(small_dataset) -> None:
    transactions = small_dataset.transactions.sort_values(
        ["user_id", "timestamp", "transaction_id"], kind="stable"
    )
    sample_user = transactions["user_id"].iloc[0]
    rows = transactions.loc[transactions["user_id"].eq(sample_user)]

    deltas = np.where(
        rows["type"].eq("income"),
        rows["amount_bdt"] - rows["fee_bdt"],
        -(rows["amount_bdt"] + rows["fee_bdt"]),
    )
    opening = float(rows["balance_after"].iloc[0]) - float(deltas[0])
    expected = np.round(np.cumsum(deltas) + opening, 2)
    assert np.allclose(rows["balance_after"].to_numpy(), expected)
    # a wallet cannot go negative, and only outflows can be short
    assert (rows["balance_after"] > -1e-9).all()
    assert (rows.loc[rows["is_shortfall"].eq(1), "type"] != "income").all()


def test_month_end_pressure_raises_end_of_month_spending(small_config: dict) -> None:
    user = {
        "user_id": "U9001",
        "persona": "daily_wage",
        "district": "Dhaka",
        "income_band": "mid",
        "age_band": "25-34",
        "language_pref": "bn",
        "cohort": "test",
    }
    profile = small_config["personas"]["daily_wage"]
    days = generator.dataset_days(small_config)

    def end_of_month_ratio(frame: pd.DataFrame) -> float:
        spend = frame.loc[frame["type"].ne("income")].copy()
        day = spend["timestamp"].dt.day
        late = float(spend.loc[day >= 28, "amount_bdt"].mean())
        middle = float(spend.loc[day.between(10, 20), "amount_bdt"].mean())
        return late / middle

    quiet = generator.generate_user_transactions(
        small_config, user, profile, days, seed=5, pressure={}
    )
    pressured = generator.generate_user_transactions(
        small_config, user, profile, days, seed=5, pressure={"intensity": 0.6, "spike_days": 4}
    )
    assert end_of_month_ratio(pressured) > end_of_month_ratio(quiet)


# ---------------------------------------------------------------------------
# injected anomalies
# ---------------------------------------------------------------------------
def test_anomaly_labels_reference_real_transactions(small_dataset) -> None:
    labelled = set(small_dataset.anomaly_labels["transaction_id"])
    known = set(small_dataset.transactions["transaction_id"])
    assert labelled
    assert labelled <= known
    assert set(small_dataset.anomaly_labels["anomaly_type"]) == {
        "unusually_large",
        "unusual_time",
        "rapid_repeat",
    }


def test_anomaly_share_is_within_the_documented_range(small_dataset) -> None:
    share = len(small_dataset.anomaly_labels) / len(small_dataset.transactions)
    assert 0.015 <= share <= 0.04, share


def test_injected_anomalies_really_are_anomalous(small_dataset) -> None:
    labels = small_dataset.anomaly_labels
    transactions = small_dataset.transactions.set_index("transaction_id")

    large = labels.loc[labels["anomaly_type"].eq("unusually_large")]
    ratios = []
    for transaction_id, user_id in zip(large["transaction_id"], large["user_id"]):
        user_rows = transactions.loc[transactions["user_id"].eq(user_id)]
        median = float(user_rows["amount_bdt"].median())
        if median > 0:
            ratios.append(float(transactions.loc[transaction_id, "amount_bdt"]) / median)
    assert ratios and float(np.median(ratios)) > 1.5

    odd_hours = transactions.loc[
        labels.loc[labels["anomaly_type"].eq("unusual_time"), "transaction_id"], "timestamp"
    ]
    assert len(odd_hours) > 0
    assert odd_hours.dt.hour.between(0, 4).all()
    assert len(labels.loc[labels["anomaly_type"].eq("rapid_repeat")]) > 0


# ---------------------------------------------------------------------------
# stability label (anti-circularity)
# ---------------------------------------------------------------------------
def test_stability_label_has_both_classes(small_dataset) -> None:
    label = small_dataset.user_labels["is_stable_next_2_months"]
    assert label.isin([0, 1]).all()
    assert 0.15 <= float(label.mean()) <= 0.85


def test_stability_label_tracks_the_latent_variable(small_dataset) -> None:
    labels = small_dataset.user_labels
    auc = _auc(labels["latent_stability"], labels["is_stable_next_2_months"])
    assert auc > 0.80, f"the latent variable should drive the label (AUC={auc:.3f})"


def test_stability_label_is_not_a_deterministic_feature_rule(small_dataset) -> None:
    per_user = (
        small_dataset.transactions.groupby("user_id")
        .agg(
            n_transactions=("transaction_id", "count"),
            mean_amount=("amount_bdt", "mean"),
            shortfall_ratio=("is_shortfall", "mean"),
            mean_balance=("balance_after", "mean"),
            fee_burden=("fee_bdt", "sum"),
        )
        .reset_index()
    )
    merged = small_dataset.user_labels.merge(per_user, on="user_id", how="inner")
    for column in ["n_transactions", "mean_amount", "shortfall_ratio", "mean_balance", "fee_burden"]:
        auc = _auc(merged[column], merged["is_stable_next_2_months"])
        assert max(auc, 1 - auc) < 0.95, f"{column} reconstructs the label too well (AUC={auc:.3f})"


# ---------------------------------------------------------------------------
# demo user "Rahim" — the numbers the 3-minute demo quotes
# ---------------------------------------------------------------------------
def test_demo_profile_horizon_matches_the_dataset(base_config: dict) -> None:
    assert int(base_config["demo_user"]["months"]) == int(base_config["dataset"]["months"])


def test_rahim_cash_outs_reproduce_the_demo_fee(base_config: dict) -> None:
    users, transactions = seed_demo_user.build_demo_user(base_config)
    summary = seed_demo_user.demo_fee_summary(transactions)
    cash_out_settings = base_config["demo_user"]["cash_out"]
    expected_fee = float(base_config["demo_user"]["expected_monthly_fee_bdt"])
    expected_volume = float(base_config["demo_user"]["expected_monthly_cash_out_bdt"])

    assert users["cohort"].iloc[0] == "demo"
    assert summary["months"] == int(base_config["dataset"]["months"])
    assert summary["cash_outs_per_month"] == pytest.approx(
        float(cash_out_settings["lumps_per_month"]), abs=0.01
    )
    assert summary["monthly_cash_out_bdt"] == pytest.approx(expected_volume, rel=0.05)
    assert summary["avg_cash_out_bdt"] == pytest.approx(
        expected_volume / float(cash_out_settings["lumps_per_month"]), rel=0.05
    )
    assert summary["monthly_fee_bdt"] == pytest.approx(expected_fee, rel=0.05)

    # the fee is *computed* from the rate table, not hardcoded
    rate = float(base_config["fee_rates"]["by_channel"]["cash_out"]) / 100.0
    assert summary["monthly_fee_bdt"] == pytest.approx(summary["monthly_cash_out_bdt"] * rate, rel=0.01)


def test_rahim_has_a_monthly_surplus_for_the_demo_goal(base_config: dict) -> None:
    """The demo promises a feasible ৳5,000/month plan, so the profile must leave room."""
    _, transactions = seed_demo_user.build_demo_user(base_config)
    months = int(base_config["dataset"]["months"])
    inflow = float(transactions.loc[transactions["type"].eq("income"), "amount_bdt"].sum()) / months
    outflow = float(
        transactions.loc[transactions["type"].ne("income"), "amount_bdt"].sum()
        + transactions["fee_bdt"].sum()
    ) / months
    goal_months = float(base_config["demo_user"]["goal"]["months"])
    monthly_target = float(base_config["demo_user"]["goal"]["target_bdt"]) / goal_months
    assert inflow - outflow > monthly_target


# ---------------------------------------------------------------------------
# database output
# ---------------------------------------------------------------------------
def test_database_contains_every_table(small_db) -> None:
    connection = sqlite3.connect(str(small_db))
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        connection.close()
    assert {"users", "transactions", "anomaly_labels", "user_labels", "splits", "generation_meta"} <= tables


def test_database_holds_the_demo_user_and_provenance(small_db, small_config: dict) -> None:
    users = generator.read_table(small_db, "users")
    assert small_config["demo_user"]["user_id"] in set(users["user_id"])

    transactions = generator.read_table(small_db, "transactions")
    assert transactions["is_shortfall"].isin([0, 1]).all()

    connection = sqlite3.connect(str(small_db))
    try:
        meta = pd.read_sql_query("SELECT * FROM generation_meta", connection)
    finally:
        connection.close()
    keys = set(meta["key"])
    assert {"generator_version", "seed_train", "seed_test", "cash_out_fee_percent_assumed"} <= keys




