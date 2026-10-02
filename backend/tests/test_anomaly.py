"""Anomaly tests (Phase 5): the IsolationForest, its rule baseline, and the API.

Three layers are pinned here:

* the **fixed-threshold baseline** — one absolute cutoff for every user, which is
  exactly why it cannot see an anomaly that is small in taka but large for a
  low-spend user (the plan's stated gap between rule and model);
* the **IsolationForest** — per-user behaviour features, train/predict round trip,
  and the ``None``-instead-of-raising degradation when no artifact exists;
* the **measured claim** — :func:`anomaly.evaluate` scoring the forest and the
  rule on the same held-out rows, so "the model beats the rule" is pinned as
  numbers rather than prose;
* the **service** — which engine actually ranked, surfaced in
  ``provenance.source`` *and* in the assumption text, so the rule fallback can
  never quietly claim per-user behaviour.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.app.services import anomaly_service
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


# ---------------------------------------------------------------------------
# the IsolationForest itself: artifact, round trip, and ``None`` degradation
# ---------------------------------------------------------------------------
def test_train_writes_the_artifact_and_predict_round_trips(
    trained_artifact: str, features: pd.DataFrame
) -> None:
    loaded = anomaly.load(trained_artifact)
    assert loaded is not None

    meta = anomaly.load_meta(trained_artifact)
    assert meta["model_name"] == anomaly.MODEL_NAME
    assert meta["features"] == anomaly.FEATURE_COLUMNS
    assert meta["contamination"] > 0
    assert meta["n_train_transactions"] > 0

    scores = anomaly.predict(features, trained_artifact)
    assert scores is not None
    assert scores.source == "model"
    assert len(scores.frame) == len(features)
    assert scores.frame["anomaly_score"].notna().all()
    # higher score = odder, which is what the API's AnomalyItem.score documents
    assert scores.frame["anomaly_score"].min() < scores.frame["anomaly_score"].max()
    assert scores.threshold == pytest.approx(anomaly.load(trained_artifact).offset_)


def test_predict_returns_none_when_the_artifact_is_missing(tmp_path) -> None:
    """Degrade, never raise: a missing artifact must not become a 500."""
    empty = tmp_path / "no_artifacts_here"
    assert anomaly.load(empty) is None
    assert anomaly.load_meta(empty) == {}
    assert anomaly.predict(pd.DataFrame(), empty) is None


def test_train_uses_train_users_only(trained_artifact: str, small_db, features) -> None:
    """The fit must not see val/test, and never the demo user."""
    splits = split_module.load_splits(small_db)
    train_users = set(splits.loc[splits["split"].eq("train"), "user_id"])
    expected = int(features["user_id"].isin(train_users).sum())
    assert anomaly.load_meta(trained_artifact)["n_train_transactions"] == expected


# ---------------------------------------------------------------------------
# the measured claim: model vs the rule, on the same held-out rows
# ---------------------------------------------------------------------------
def test_evaluate_scores_model_against_the_rule_on_the_same_rows(
    trained_artifact: str, small_db, features: pd.DataFrame, transactions: pd.DataFrame
) -> None:
    labels = user_features.load_anomaly_labels(small_db)
    splits = split_module.load_splits(small_db)
    report = anomaly.evaluate(
        features,
        transactions,
        labels,
        splits,
        generator.load_config(),
        artifact_dir=trained_artifact,
    )

    assert report["model_name"] == anomaly.MODEL_NAME
    assert report["baseline_name"] == baselines.ANOMALY_BASELINE_NAME
    assert report["n_anomalies"] > 0
    assert report["n_test_transactions"] > report["n_anomalies"]

    for side in ("model", "baseline"):
        for metric in ("precision", "recall", "f1"):
            assert 0.0 <= report[side][metric] <= 100.0
        assert report[side]["auc"] is None or 0.0 <= report[side]["auc"] <= 1.0

    # The forest ranks better than one absolute cutoff even though the rule wins
    # raw recall: it gets there by flagging far fewer rows. Pin the direction of
    # each measured difference so a regression in either half is caught.
    assert report["model"]["auc"] > report["baseline"]["auc"]
    assert report["model"]["f1"] > report["baseline"]["f1"]
    assert report["model"]["precision"] > report["baseline"]["precision"]
    assert report["improvement_f1_pct"] > 0
    assert report["improvement_auc_pct"] > 0

    # The rule's specific blind spot: one absolute cutoff cannot see an
    # unusual_time injection, because those rows keep a normal-sized amount.
    by_type = report["by_type"]
    assert by_type
    for kind, row in by_type.items():
        assert row["count"] > 0
        assert 0.0 <= row["model_recall"] <= 100.0
        assert 0.0 <= row["baseline_recall"] <= 100.0
    if "unusual_time" in by_type:
        assert by_type["unusual_time"]["baseline_recall"] < by_type["unusual_time"]["model_recall"]


def test_evaluate_refuses_to_score_without_labels_or_artifact(
    trained_artifact: str, tmp_path, small_db, features: pd.DataFrame, transactions: pd.DataFrame
) -> None:
    splits = split_module.load_splits(small_db)
    labels = user_features.load_anomaly_labels(small_db)

    with pytest.raises(ValueError, match="no anomaly labels"):
        anomaly.evaluate(features, transactions, labels.iloc[0:0], splits, None, trained_artifact)

    with pytest.raises(ValueError, match="no anomaly artifact"):
        anomaly.evaluate(
            features, transactions, labels, splits, None, tmp_path / "empty_dir"
        )


# ---------------------------------------------------------------------------
# the service: which engine actually answered must be visible, not implied
# ---------------------------------------------------------------------------
def test_the_service_reports_the_model_when_the_forest_is_trained(
    small_db, trained_artifact: str
) -> None:
    payload = anomaly_service.build_anomalies(
        DEMO_USER, db_path=small_db, artifact_dir=trained_artifact
    )
    assert payload["source"] == "model"
    assert payload["provenance"]["source"] == "model"
    # the per-user assumption is only true of the forest, so it must be present
    assert "not a fixed taka amount" in payload["provenance"]["assumption"]


def test_the_service_falls_back_loudly_and_never_claims_the_model(
    small_db, tmp_path
) -> None:
    payload = anomaly_service.build_anomalies(
        DEMO_USER, db_path=small_db, artifact_dir=tmp_path / "no_artifact"
    )
    assert payload["source"] == "rule"
    assert payload["provenance"]["source"] == "rule"
    # The failure mode this pins: claiming per-user behaviour while a single
    # absolute cutoff did the ranking.
    assumption = payload["provenance"]["assumption"]
    assert "not a fixed taka amount" not in assumption
    assert "fallback" in assumption
    assert payload["items"]


def test_the_service_raises_for_a_user_with_no_transactions(small_db) -> None:
    with pytest.raises(KeyError):
        anomaly_service.build_anomalies("nobody-here", db_path=small_db)

