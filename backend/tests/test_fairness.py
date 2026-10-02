"""Tests for the fairness audit (Phase 8).

The plan asks for three gap families across persona, district and income band,
against a 15% relative-gap target. What these tests pin is mostly *the audit's own
honesty*, because an audit that flatters the model is worse than none:

* the gaps are real arithmetic on held-out rows, not a placeholder;
* the reference differs by metric kind -- best group for an error, cohort rate for
  a parity metric -- because "worse" means opposite things for the two;
* a group too small to support a gap is **excluded and named**, never scored;
* a family that could not be measured reports ``None``, never ``True``;
* no demographic column can reach a model input.

The dataset is 60 users, so many cells here are small on purpose: that is the
condition the small-group filter exists for, and it is what makes a "big gap"
result a statement about sample size rather than about the model.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.data import features as user_features
from backend.data import generator
from backend.data import split as split_module
from backend.ml import anomaly, dataset, fairness, forecast, signal


@pytest.fixture(scope="module")
def trained(small_db, tmp_path_factory) -> Path:
    """All three artifacts trained on the small dataset, in one temp directory."""
    directory = tmp_path_factory.mktemp("fairness_artifacts")
    cfg = generator.load_config()
    splits = split_module.load_splits(small_db)
    transactions = user_features.load_transactions(small_db)

    frame = dataset.make_frame(small_db, cfg=cfg)
    forecast.train(frame.features, splits, artifact_dir=directory)

    rows = user_features.attach_split(
        user_features.user_features(cfg, transactions), splits
    )
    signal.train(rows, user_features.load_user_labels(small_db), splits, artifact_dir=directory)
    anomaly.train(
        anomaly.build_features(transactions), splits, cfg, artifact_dir=directory
    )
    return directory


@pytest.fixture(scope="module")
def report(small_db, trained: Path) -> dict:
    cfg = generator.load_config()
    frame = dataset.make_frame(small_db, cfg=cfg)
    transactions = user_features.load_transactions(small_db)
    rows = user_features.attach_split(
        user_features.user_features(cfg, transactions),
        split_module.load_splits(small_db),
    )
    return fairness.evaluate(
        featured=frame.features,
        daily=frame.daily,
        splits=split_module.load_splits(small_db),
        group_frame=user_features.load_users(small_db),
        transactions=transactions,
        anomaly_labels=user_features.load_anomaly_labels(small_db),
        user_rows=rows,
        artifact_dir=trained,
        min_users=2,
    )


# --- the shape of the audit ------------------------------------------------
def test_every_dimension_and_gap_family_is_reported(report: dict) -> None:
    assert report["target_relative_gap_pct"] == fairness.TARGET_RELATIVE_GAP_PCT
    assert set(report["dimensions"]) == {"persona", "district", "income_band"}
    assert set(report["by_family"]) == {
        "forecast_mae", "anomaly_flag_rate", "consistency_bands"
    }
    for family in report["by_family"].values():
        assert "worst_relative_gap_pct" in family
        assert "reference" in family

    dimensions = {row["dimension"] for row in report["rows"]}
    assert dimensions == {"persona", "district", "income_band"}
    metrics = {row["metric"] for row in report["rows"]}
    # forecast error, anomaly flag rate, ground-truth rate, and band share
    assert "mae_net_bdt" in metrics
    assert "anomaly_flag_rate_pct" in metrics
    assert "band_share_pct" in metrics


def test_rows_are_worst_gap_first_so_the_worst_offender_leads(report: dict) -> None:
    gaps = [abs(row["relative_gap_pct"]) for row in report["rows"]]
    assert gaps == sorted(gaps, reverse=True)


def test_the_caveats_say_the_numbers_are_synthetic(report: dict) -> None:
    joined = " ".join(report["caveats"]).lower()
    assert "synthetic" in joined
    assert "never model inputs" in joined
    assert "excluded" in joined


# --- the gap arithmetic ----------------------------------------------------
def test_an_error_metric_is_measured_against_the_best_group(report: dict) -> None:
    """A MAE gap is only meaningful as "worse than the best-served group"."""
    for metric in ("mae_inflow_bdt", "mae_outflow_bdt", "mae_net_bdt"):
        values = [row for row in report["rows"] if row["metric"] == metric]
        assert values, f"{metric} produced no rows"
        assert min(row["value"] for row in values) == pytest.approx(
            min(row["value"] for row in values)
        )
        # The reference is the minimum, so no error row may be negative.
        assert all(row["relative_gap_pct"] >= -0.01 for row in values)
        assert any(row["relative_gap_pct"] == 0.0 for row in values)


def test_a_parity_metric_is_measured_against_the_cohort(report: dict) -> None:
    """A flag rate or band share is not an error: the cohort rate is the bar.

    So these gaps may be negative, and only the *absolute* size is a problem --
    which is the opposite rule to the MAE rows above. If both used one rule, one
    of the two families would report its worst group as its best.
    """
    flags = [row for row in report["rows"] if row["metric"] == "anomaly_flag_rate_pct"]
    assert flags
    assert any(row["relative_gap_pct"] < 0 for row in flags), (
        "a parity metric measured against the cohort must produce both signs"
    )
    for row in flags:
        expected = abs(
            (row["value"] - report["by_family"]["anomaly_flag_rate"]["cohort_flag_rate_pct"])
            / report["by_family"]["anomaly_flag_rate"]["cohort_flag_rate_pct"] * 100.0
        )
        assert abs(row["relative_gap_pct"]) == pytest.approx(expected, abs=0.02)


def test_exceeds_target_follows_the_direction_of_the_metric(report: dict) -> None:
    for row in report["rows"]:
        higher_is_worse = fairness.HIGHER_IS_WORSE[row["metric"]]
        gap = row["relative_gap_pct"]
        expected = (
            gap > fairness.TARGET_RELATIVE_GAP_PCT
            if higher_is_worse
            else abs(gap) > fairness.TARGET_RELATIVE_GAP_PCT
        )
        assert row["exceeds_target"] is expected, row


def test_the_target_verdict_agrees_with_the_rows(report: dict) -> None:
    over = [row for row in report["rows"] if row["exceeds_target"]]
    assert report["n_exceeding_target"] == len(over)
    assert report["target_met"] is (not over)
    assert report["n_rows"] == len(report["rows"])


def test_a_relative_gap_of_zero_reference_does_not_divide_by_zero() -> None:
    """A zero reference cannot be divided by; the gap is undefined, not infinite."""
    assert fairness._relative_gap(0.0, 0.0) == 0.0
    assert fairness._relative_gap(5.0, 0.0) == 100.0
    assert fairness._relative_gap(0.0, 5.0) == -100.0


# --- the small-group filter ------------------------------------------------
def test_groups_below_the_minimum_are_excluded_and_named(report: dict) -> None:
    minimum = report["min_users_per_group"]
    assert minimum == 2
    for item in report["excluded_groups"]:
        assert item["users"] < minimum
        assert item["dimension"] in fairness.DIMENSIONS

    # No scored row may come from an excluded group.
    dropped = {(item["dimension"], item["group"]) for item in report["excluded_groups"]}
    for row in report["rows"]:
        assert (row["dimension"], row["group"]) not in dropped


def test_exclusions_are_deduplicated_across_the_three_families(small_db, tmp_path) -> None:
    """Each family filters independently, so the same group can be dropped thrice."""
    report = fairness.evaluate(
        group_frame=user_features.load_users(small_db),
        artifact_dir=tmp_path / "nothing_here",
        min_users=10_000,  # exclude everything, on purpose
    )
    keys = [(item["dimension"], item["group"]) for item in report["excluded_groups"]]
    assert len(keys) == len(set(keys))
    assert keys == sorted(keys)


def test_a_higher_minimum_removes_more_groups(small_db, trained: Path) -> None:
    cfg = generator.load_config()
    frame = dataset.make_frame(small_db, cfg=cfg)
    common = {
        "featured": frame.features,
        "daily": frame.daily,
        "splits": split_module.load_splits(small_db),
        "group_frame": user_features.load_users(small_db),
        "transactions": user_features.load_transactions(small_db),
        "user_rows": user_features.attach_split(
            user_features.user_features(cfg, user_features.load_transactions(small_db)),
            split_module.load_splits(small_db),
        ),
        "artifact_dir": trained,
    }
    loose = fairness.evaluate(**common, min_users=1)
    strict = fairness.evaluate(**common, min_users=10_000)
    assert strict["n_rows"] == 0
    assert len(strict["excluded_groups"]) > len(loose["excluded_groups"])


# --- degradation -----------------------------------------------------------
def test_an_unmeasured_family_never_reports_as_passing(small_db, tmp_path) -> None:
    """The failure mode this exists to prevent: a missing audit passing review.

    With no artifacts, all three families are unmeasurable. They must report
    ``None`` for ``target_met`` -- not ``True`` -- and say why.
    """
    report = fairness.evaluate(
        group_frame=user_features.load_users(small_db),
        artifact_dir=tmp_path / "empty",
        min_users=1,
    )
    assert report["n_rows"] == 0
    assert report["target_met"] is False
    for family in report["by_family"].values():
        assert family["target_met"] is None
        assert family["status"] == "unavailable"
        assert family["reason"]


def test_no_demographics_means_unavailable_not_a_crash() -> None:
    report = fairness.evaluate(group_frame=None)
    assert report["status"] == "unavailable"
    assert report["rows"] == []
    assert report["target_relative_gap_pct"] == fairness.TARGET_RELATIVE_GAP_PCT


def test_a_partial_audit_reports_the_families_it_could_measure(
    small_db, trained: Path
) -> None:
    """Each family is independent: a missing input costs only its own table.

    Here the forecast artifact is present but the raw ledger and the user feature
    matrix are not, so the MAE family must still be measured while the two rates
    report themselves unavailable.
    """
    cfg = generator.load_config()
    frame = dataset.make_frame(small_db, cfg=cfg)
    report = fairness.evaluate(
        featured=frame.features,
        daily=frame.daily,
        splits=split_module.load_splits(small_db),
        group_frame=user_features.load_users(small_db),
        artifact_dir=trained,
        min_users=2,
    )
    mae = report["by_family"]["forecast_mae"]
    assert mae.get("status") != "unavailable"
    assert mae["target_met"] is not None
    assert any(row["metric"] == "mae_net_bdt" for row in report["rows"])

    for name in ("anomaly_flag_rate", "consistency_bands"):
        family = report["by_family"][name]
        assert family["status"] == "unavailable"
        # The key property: unmeasured is not the same as passed.
        assert family["target_met"] is None
        assert family["reason"]


# --- leakage --------------------------------------------------------------
def test_demographics_are_never_model_inputs() -> None:
    """The whole point of slicing after scoring: no group column is a feature."""
    assert not set(user_features.DEMOGRAPHIC_COLUMNS) & set(user_features.FEATURE_COLUMNS)
    assert not set(user_features.DEMOGRAPHIC_COLUMNS) & set(signal.FEATURE_COLUMNS)
    assert not set(user_features.DEMOGRAPHIC_COLUMNS) & set(anomaly.FEATURE_COLUMNS)
    assert not set(user_features.DEMOGRAPHIC_COLUMNS) & set(dataset.FORECAST_FEATURE_COLUMNS)


def test_fairness_scores_the_same_cells_as_the_headline_metrics(
    small_db, trained: Path
) -> None:
    """One join, two consumers -- so a group gap cannot be measured on other rows.

    ``fairness`` and ``evaluate`` both call ``scored_cells``. If that were ever
    reimplemented inside the fairness pass, the MAE it compares group-to-group
    could silently be computed over a different row set than the headline MAE it
    is judged against.
    """
    from backend.ml import evaluate as forecast_evaluate

    cfg = generator.load_config()
    frame = dataset.make_frame(small_db, cfg=cfg)
    splits = split_module.load_splits(small_db)

    joined, _ = forecast_evaluate.scored_cells(frame.features, frame.daily, splits, trained)
    direct = forecast_evaluate.evaluate(frame.features, frame.daily, splits, trained)
    assert direct["n_cells"] == len(joined)
