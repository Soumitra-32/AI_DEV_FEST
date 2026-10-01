"""Leakage checks for the user-level split.

Phase 1 gate: *"the split has no user overlap"*. These tests also pin down the
anti-circularity protocol: test users come from the separately seeded cohort, the
demo user is excluded from evaluation, and no label column leaks into the tables
the models read features from.
"""
from __future__ import annotations

from itertools import combinations

import pandas as pd
import pytest

from backend.data import generator, split

EVAL_SPLITS = ("train", "val", "test")


def test_every_user_is_assigned_exactly_once(small_dataset) -> None:
    splits = small_dataset.splits
    assert splits["user_id"].is_unique
    assert set(splits["user_id"]) == set(small_dataset.users["user_id"])


def test_splits_do_not_overlap(small_dataset) -> None:
    splits = small_dataset.splits
    groups = {
        name: set(split.users_in_split(splits, name))
        for name in (*EVAL_SPLITS, split.DEMO_SPLIT)
    }
    for left, right in combinations(groups, 2):
        overlap = groups[left] & groups[right]
        assert not overlap, f"{left} and {right} share {len(overlap)} users: {sorted(overlap)[:5]}"


def test_split_proportions_match_config(small_dataset, small_config: dict) -> None:
    sizes = split.split_sizes(small_dataset.splits)
    evaluated = sizes["train"] + sizes["val"] + sizes["test"]
    for name in EVAL_SPLITS:
        assert sizes[name] == pytest.approx(evaluated * float(small_config["split"][name]), abs=1)
    assert sum(sizes.values()) == len(small_dataset.users)


def test_cohort_sizes_follow_the_configured_proportions(small_config: dict) -> None:
    n_train_val, n_test = split.cohort_sizes(small_config, 500)
    assert n_test == 75
    assert n_train_val + n_test == 500


def test_test_users_come_from_the_other_cohort(small_dataset) -> None:
    users = small_dataset.users.set_index("user_id")
    splits = small_dataset.splits
    for name in ("train", "val"):
        cohorts = set(users.loc[split.users_in_split(splits, name), "cohort"])
        assert cohorts == {"train_val"}, f"{name} users must come from the training cohort"
    assert set(users.loc[split.users_in_split(splits, "test"), "cohort"]) == {"test"}


def test_demo_user_is_excluded_from_evaluation(small_dataset, small_config: dict) -> None:
    splits = small_dataset.splits
    demo_id = small_config["demo_user"]["user_id"]
    assert demo_id in set(split.users_in_split(splits, split.DEMO_SPLIT))
    for name in EVAL_SPLITS:
        assert demo_id not in set(split.users_in_split(splits, name))


def test_split_assignment_is_reproducible(small_config: dict, small_dataset) -> None:
    first = split.assign_splits(small_config, small_dataset.users)
    second = split.assign_splits(small_config, small_dataset.users)
    pd.testing.assert_frame_equal(first, second)


def test_every_transaction_belongs_to_a_single_split(small_db) -> None:
    users = generator.read_table(small_db, "users")
    transactions = generator.read_table(small_db, "transactions")
    splits = split.load_splits(small_db)

    assert len(splits) == len(users) == splits["user_id"].nunique()
    assert set(users["user_id"]) == set(splits["user_id"])
    assert set(transactions["user_id"]) <= set(splits["user_id"])


def test_label_columns_stay_out_of_the_model_tables(small_db) -> None:
    """The stability label lives in its own table, so it cannot leak into features."""
    users = generator.read_table(small_db, "users")
    transactions = generator.read_table(small_db, "transactions")
    for frame in (users, transactions):
        for column in ("is_stable_next_2_months", "latent_stability", "outcome_score", "split"):
            assert column not in frame.columns


def test_anomaly_truth_is_not_a_transaction_column(small_db) -> None:
    """Ground truth is stored separately so a model cannot read the answer."""
    transactions = generator.read_table(small_db, "transactions")
    for column in ("is_anomaly", "anomaly_type", "anomaly_label"):
        assert column not in transactions.columns

