"""Health-score tests (Phase 5): a coaching reading with visible arithmetic.

The score is pure rules over the label-free feature row, so these tests pin the
bounds (0 and 100 are reachable but never exceeded), the component breakdown, and
the two properties that matter for trust: every point is traceable, and a worse
behaviour can never raise the score.
"""
from __future__ import annotations

import pytest

from backend.data import features as user_features
from backend.data import generator
from backend.rules import health_score
from backend.rules.health_score import HealthComponent, HealthScore


def component_of(graded: HealthScore, key: str) -> HealthComponent:
    """``graded.component(key)`` for a key the score is known to contain.

    :meth:`HealthScore.component` returns ``None`` for an unknown key; these tests
    only ever ask for documented components, so the assertion is the point.
    """
    found = graded.component(key)
    assert found is not None, f"no component {key!r} in {[c.key for c in graded.components]}"
    return found

#: A row that should score full marks on every component.
IDEAL = {
    "fee_share_of_income": 0.0,
    "cash_out_share_of_outflow": 0.0,
    "income_cv": 0.10,
    "income_days_per_month": 24.0,
    "income_mean_bdt": 40000.0,
    "balance_mean_bdt": 9000.0,
    "balance_min_bdt": 1200.0,
    "shortfall_days_per_month": 0.0,
}

#: A row that should score the floor.
WORST = {
    "fee_share_of_income": 0.05,
    "cash_out_share_of_outflow": 0.80,
    "income_cv": 2.0,
    "income_days_per_month": 2.0,
    "income_mean_bdt": 10000.0,
    "balance_mean_bdt": 0.0,
    "balance_min_bdt": -50.0,
    "shortfall_days_per_month": 8.0,
}


def test_the_extremes_are_bounded() -> None:
    assert health_score.score_row(IDEAL).score == 100
    assert health_score.score_row(IDEAL).band == "Strong"
    assert health_score.score_row(WORST).score == 0
    assert health_score.score_row(WORST).band == "Fragile"


def test_every_component_is_present_and_caps_sum_to_one_hundred() -> None:
    graded = health_score.score_row(IDEAL)
    keys = [item.key for item in graded.components]
    assert keys == [
        "fee_burden",
        "cash_dependency",
        "income_regularity",
        "balance_cushion",
        "shortfall_freedom",
    ]
    assert sum(item.max_points for item in graded.components) == health_score.SCORE_MAX
    for item in graded.components:
        assert 0.0 <= item.points <= item.max_points
        assert 0.0 <= item.share <= 1.0
        assert item.detail_en and item.detail_bn


def test_the_score_is_the_sum_of_its_components() -> None:
    graded = health_score.score_row(
        {
            "fee_share_of_income": 0.01,
            "cash_out_share_of_outflow": 0.25,
            "income_cv": 0.9,
            "income_days_per_month": 12.0,
            "income_mean_bdt": 20000.0,
            "balance_mean_bdt": 1500.0,
            "balance_min_bdt": 100.0,
            "shortfall_days_per_month": 1.0,
        }
    )
    assert graded.score == int(round(sum(item.points for item in graded.components)))
    assert 0 < graded.score < 100
    trace = " | ".join(graded.arithmetic)
    for item in graded.components:
        assert item.key in trace
    assert f"/ {health_score.SCORE_MAX}" in trace
    assert graded.band in trace


def test_worse_behaviour_can_never_raise_the_score() -> None:
    """Each component moves the score in exactly one direction."""
    better = health_score.score_row(
        {**IDEAL, "fee_share_of_income": 0.0, "shortfall_days_per_month": 0.0}
    )
    worse_fees = health_score.score_row({**IDEAL, "fee_share_of_income": 0.015})
    worse_shortfall = health_score.score_row({**IDEAL, "shortfall_days_per_month": 3.0})
    worse_cash = health_score.score_row({**IDEAL, "cash_out_share_of_outflow": 0.4})

    assert worse_fees.score < better.score
    assert worse_shortfall.score < better.score
    assert worse_cash.score < better.score
    assert component_of(worse_fees, "fee_burden").points < component_of(better, "fee_burden").points
    assert component_of(worse_cash, "cash_dependency").points < component_of(better, "cash_dependency").points


def test_a_window_that_ran_short_earns_no_cushion_points() -> None:
    """An average balance means nothing if the wallet actually hit zero."""
    healthy = health_score.score_row({**IDEAL, "balance_min_bdt": 500.0})
    dipped = health_score.score_row({**IDEAL, "balance_min_bdt": -10.0})
    assert component_of(healthy, "balance_cushion").points == health_score.MAX_BALANCE_CUSHION
    assert component_of(dipped, "balance_cushion").points == 0.0
    assert dipped.score < healthy.score


def test_missing_features_are_treated_as_zero_not_as_an_error() -> None:
    graded = health_score.score_row({})
    assert 0 <= graded.score <= 100
    assert component_of(graded, "fee_burden").points == health_score.MAX_FEE_BURDEN
    assert component_of(graded, "balance_cushion").points == 0.0


@pytest.mark.parametrize(
    ("value", "band"),
    [(100, "Strong"), (80, "Strong"), (79, "Steady"), (55, "Steady"),
     (54, "Building"), (30, "Building"), (29, "Fragile"), (0, "Fragile")],
)
def test_band_boundaries(value: int, band: str) -> None:
    assert health_score.band_for(value) == band


def test_as_dict_is_json_ready() -> None:
    payload = health_score.score_row(IDEAL).as_dict()
    assert payload["score"] == 100
    assert payload["score_max"] == 100
    assert payload["band"] == "Strong"
    assert len(payload["components"]) == 5
    assert isinstance(payload["arithmetic"], list)


# ---------------------------------------------------------------------------
# against the real pipeline
# ---------------------------------------------------------------------------
def test_rahim_scores_inside_the_band_range(small_db) -> None:
    """The demo user's own features produce a usable, in-range reading."""
    cfg = generator.load_config()
    transactions = user_features.load_transactions(small_db, ["rahim"])
    features = user_features.user_features(cfg, transactions)
    graded = health_score.score_features(features, "rahim")
    assert 0 <= graded.score <= 100
    assert graded.band in {"Fragile", "Building", "Steady", "Strong"}
    assert len(graded.components) == 5
    # the row-level entry point agrees with the frame-level one
    assert graded.score == health_score.score_row(features.iloc[0]).score


def test_an_unknown_user_raises_instead_of_scoring_nothing(small_db) -> None:
    cfg = generator.load_config()
    features = user_features.user_features(
        cfg, user_features.load_transactions(small_db, ["rahim"])
    )
    with pytest.raises(KeyError):
        health_score.score_features(features, "nobody")


def test_the_scored_columns_are_exactly_the_label_free_features() -> None:
    """No label column may ever reach this card."""
    for column in health_score.SCORED_FEATURES:
        assert column in user_features.FEATURE_COLUMNS
    assert "is_stable_next_2_months" not in health_score.SCORED_FEATURES
