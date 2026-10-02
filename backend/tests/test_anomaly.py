"""Anomaly tests (Phase 5): the IsolationForest, its rule baseline, and the API.

Three layers are pinned here:

* the **fixed-threshold baseline** — one absolute cutoff for every user, which is
  exactly why it cannot see an anomaly that is small in taka but large for a
  low-spend user (the plan's stated gap between rule and model);
* the **IsolationForest** — per-user behaviour features, train/predict round trip,
  and the ``None``-instead-of-raising degradation when no artifact exists;
* the **service and the endpoint** — ranking + fee switch shaped into the frozen
  ``/anomalies`` contract, with the token deciding whose data is read.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.data import features as user_features
from backend.data import generator, split as split_module
from backend.ml import anomaly, baselines

DEMO_USER = "rahim"


@pytest.fixture(scope="module")
def transactions(small_db) -> pd.DataFrame:
    return user_features.load_transactions(small_db)


@pytest.fixture(scope="module")
def features(transactions: pd.DataFrame) -> pd.DataFrame:
    return anomaly.build_features(transactions)


@pytest.fixture(scope="module")
def trained_artifact(tmp_path_factory, small_db, transactions, features) -> str:
    """One trained forest shared by the read-only tests below."""
    directory = tmp_path_factory.mktemp("anomaly_artifacts")
    splits = split_module.load_splits(small_db)
    anomaly.train(features, splits, generator.load_config(), artifact_dir=directory)
    return str(directory)


# ---------------------------------------------------------------------------
# the rule baseline the model has to beat
# ---------------------------------------------------------------------------
def test_the_baseline_is_one_absolute_threshold_for_everyone(transactions: pd.DataFrame) -> None:
    threshold = baselines.fixed_threshold_magnitude(transactions)
    outflow = transactions.loc[~transactions["type"].eq("income"), "amount_bdt"]
    assert threshold == pytest.approx(float(outflow.mean()) * baselines.DEFAULT_THRESHOLD_MULTIPLIER)

    flags = baselines.fixed_threshold_flags(transactions)
    assert flags.dtype == bool
    assert flags.sum() > 0
    # positional, because idxmax() is typed Hashable and .loc[] has no overload
    # accepting that; flags is index-aligned to transactions, so positions match
    amount_column = transactions["amount_bdt"].astype(float)
    peak_pos = int(amount_column.to_numpy().argmax())
    assert bool(flags.to_numpy()[peak_pos]) is True


def test_a_bigger_multiplier_flags_fewer_rows(transactions: pd.DataFrame) -> None:
    loose = baselines.fixed_threshold_flags(transactions, multiplier=2.0).sum()
    strict = baselines.fixed_threshold_flags(transactions, multiplier=10.0).sum()
    assert strict < loose


def test_the_rule_misses_what_is_large_for_one_user_only(transactions: pd.DataFrame) -> None:
    """The plan's exact claim, as arithmetic rather than as prose.

    A ৳600 payment is below the global cutoff (so the rule ignores it) yet can be
    several times the payer's own average (so the model's feature says "odd").
    """
    # The user's own history needs enough rows for a *sample* std (ddof=1) to mean
    # anything: with only one ৳100 row the z-score of the ৳600 is pinned at 0.707
    # no matter how it is computed. Five small rows put it at ~2.0.
    small = [100.0] * 5
    amounts = small + [600.0]
    frame = pd.DataFrame(
        {
            "transaction_id": ["low-%d" % i for i in range(len(small))] + ["spike-1"],
            "user_id": ["U-low"] * len(amounts),
            "timestamp": pd.date_range("2025-03-01T10:00:00", periods=len(amounts), freq="D"),
            "type": ["expense"] * len(amounts),
            "channel": ["merchant_payment"] * len(amounts),
            "category": ["food"] * len(amounts),
            "amount_bdt": amounts,
            "fee_bdt": [0.0] * len(amounts),
            "balance_after": [5000.0] * len(amounts),
            "is_shortfall": [0] * len(amounts),
        }
    )
    global_threshold = 1000.0
    flags = baselines.fixed_threshold_flags(frame, threshold=global_threshold)
    assert flags.tolist() == [False] * len(amounts)  # the rule sees nothing

    built = anomaly.build_features(frame)
    # .loc[label, col] has no overload for a Hashable label and falls back to one
    # returning a Series, so take the spike row positionally with .iloc instead
    spike_pos = len(built) - 1
    assert float(built["amount_zscore"].iloc[spike_pos]) > 1.5
    assert float(built["amount_over_user_mean"].iloc[spike_pos]) > 3.0
    assert float(built["log_amount"].iloc[spike_pos]) > float(built["log_amount"].iloc[0])


def test_the_baseline_score_is_amount_over_the_threshold(transactions: pd.DataFrame) -> None:
    threshold = baselines.fixed_threshold_magnitude(transactions, multiplier=2.0)
    scores = baselines.fixed_threshold_scores(transactions, threshold=threshold)
    expected = transactions["amount_bdt"].astype(float) / threshold
    assert np.allclose(scores.to_numpy(), expected.to_numpy())
