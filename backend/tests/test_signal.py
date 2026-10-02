"""Tests for the consistency signal (Phase 7).

Three things are worth proving here, and the third is the one that matters:

1. the model is a model -- it trains, it beats the random baseline on held-out
   users, and its factors come from SHAP;
2. the API still answers with **no artifact at all**, degrading to the rule band
   and *saying so* in the provenance;
3. the response can never be read as a credit decision -- a band, no probability
   in the body, and the banner pinned on.

The LLM is not involved anywhere: this signal is a model plus rules, and the
tests must keep it that way.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import Settings, get_settings
from backend.app.main import create_app
from backend.app.schemas import ConsistencySignalResponse
from backend.app.services import signal_service
from backend.data import features as user_features
from backend.data import split as split_module
from backend.ml import signal

TOKEN = "signal-token"


def _user_rows(db_path: Path | None = None) -> pd.DataFrame:
    path = db_path or user_features.default_db_path()
    frame = user_features.user_features(
        user_features.load_config(), user_features.load_transactions(path)
    )
    return user_features.attach_split(frame, split_module.load_splits(path))


def _labels(db_path: Path | None = None) -> pd.DataFrame:
    return user_features.load_user_labels(db_path or user_features.default_db_path())


def _splits(db_path: Path | None = None):
    return split_module.load_splits(db_path or user_features.default_db_path())


@pytest.fixture(scope="module")
def trained(tmp_path_factory) -> Path:
    """A trained artifact in a temp directory, shared by the read-only tests."""
    directory = tmp_path_factory.mktemp("signal_artifacts")
    signal.train(_user_rows(), _labels(), _splits(), artifact_dir=directory)
    return directory


@pytest.fixture()
def client() -> TestClient:
    settings = Settings(demo_auth_token=TOKEN, demo_user_id="rahim", feature_llm=False)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


# --- the model ------------------------------------------------------------
def test_band_boundaries_are_the_documented_three() -> None:
    assert signal.band_for(0.10) == "Building"
    assert signal.band_for(0.39) == "Building"
    assert signal.band_for(0.40) == "Steady"
    assert signal.band_for(0.59) == "Steady"
    assert signal.band_for(0.60) == "Strong"
    assert signal.band_for(0.99) == "Strong"


def test_training_writes_the_artifact_and_its_metadata(trained: Path) -> None:
    meta = signal.load_meta(trained)
    assert meta["model_name"] == signal.MODEL_NAME
    assert meta["features"] == signal.FEATURE_COLUMNS
    assert meta["trained_rows"] > 0
    # The label must never appear among the model's own inputs.
    assert signal.LABEL_COLUMN not in meta["features"]


def test_the_label_is_not_a_model_feature() -> None:
    """No derived label column may leak into the feature matrix."""
    assert signal.FEATURE_COLUMNS == list(user_features.FEATURE_COLUMNS)
    assert not any("label" in name or "stable" in name for name in signal.FEATURE_COLUMNS)


def test_beats_the_random_baseline_on_held_out_users(trained: Path) -> None:
    rows, labels = _user_rows(), _labels()
    result = signal.evaluate(rows, labels, _splits(), trained)
    assert result["auc"] is not None
    assert result["auc"] > result["baseline_auc"]
    assert result["auc"] > 0.6


def test_prediction_carries_shap_factors_with_a_direction(trained: Path) -> None:
    rows = _user_rows()
    prediction = signal.predict(rows.loc[rows["user_id"].eq("rahim")], trained)
    assert prediction is not None
    assert prediction.source == "model"
    assert prediction.band in {"Building", "Steady", "Strong"}
    assert 1 <= len(prediction.factors) <= 3
    for factor in prediction.factors:
        assert factor["feature"] in signal.FEATURE_COLUMNS
        assert factor["direction"] in {"improves", "weakens"}
        assert factor["magnitude"] >= 0


def test_the_demo_user_is_not_in_the_test_cohort() -> None:
    """Rahim is held out, so his band is not something the model was fitted on."""
    splits = _splits()
    demo_rows = splits.loc[splits["user_id"].eq("rahim"), "split"]
    assert not demo_rows.empty
    assert demo_rows.iloc[0] == "demo"
# --- degradation ----------------------------------------------------------
def test_predict_returns_none_without_an_artifact(tmp_path: Path) -> None:
    assert signal.predict(_user_rows().head(1), tmp_path) is None
    assert signal.load(tmp_path) is None


def test_a_corrupt_artifact_is_ignored_not_raised(tmp_path: Path) -> None:
    (tmp_path / signal.MODEL_FILE).write_text("not a model", encoding="utf-8")
    assert signal.load(tmp_path) is None
    assert signal.predict(_user_rows().head(1), tmp_path) is None


def test_evaluate_reports_no_auc_when_untrained(tmp_path: Path) -> None:
    result = signal.evaluate(_user_rows(), _labels(), None, tmp_path)
    assert result["auc"] is None
    assert "not trained" in result["note"]


def test_service_falls_back_to_the_rule_band_and_says_so(tmp_path: Path) -> None:
    payload = signal_service.build_signal("rahim", artifact_dir=tmp_path)
    assert payload["provenance"]["source"] == "rule"
    assert payload["band"] in {"Building", "Steady", "Strong"}
    assert payload["factors"]


def test_the_rule_band_moves_with_the_numbers() -> None:
    """The fallback must be a reading of behaviour, not a constant."""
    thin = {
        "income_days_per_month": 1.0,
        "shortfall_days_per_month": 5.0,
        "fee_share_of_income": 0.05,
    }
    strong = {
        "income_days_per_month": 4.0,
        "shortfall_days_per_month": 0.0,
        "fee_share_of_income": 0.0,
    }
    assert signal.rule_band(thin)[0] == "Building"
    assert signal.rule_band(strong)[0] == "Strong"


# --- the SHAP explanation --------------------------------------------------
def test_shap_contributions_reconstruct_the_log_odds(trained: Path) -> None:
    """The audit property: base + every contribution == the model's log-odds.

    This is the test that would catch a wrong SHAP implementation. A plausible
    mistake -- adding the intercept to each feature, or summing against the wrong
    reference -- still produces plausible-looking per-feature numbers, but the sum
    no longer reconstructs the score. Checking the arithmetic pins the semantics.
    """
    model, scaler = signal.load(trained)
    rows = _user_rows()
    one = rows.loc[rows["user_id"].eq("rahim")]

    explanation = signal.shap_explanation(model, scaler, one.iloc[0])
    total = explanation["base_value"] + sum(
        item["contribution"] for item in explanation["features"]
    )
    assert total == pytest.approx(explanation["log_odds"], abs=0.05)

    # The cross-check that matters: the same number the model itself produces.
    probability = float(model.predict_proba(scaler.transform(signal.build_matrix(one)))[0, 1])
    assert probability == pytest.approx(
        1.0 / (1.0 + pow(2.718281828459045, -explanation["log_odds"])), abs=1e-3
    )


def test_shap_explanation_covers_every_feature_and_ranks_by_size(trained: Path) -> None:
    model, scaler = signal.load(trained)
    explanation = signal.shap_explanation(model, scaler, _user_rows().iloc[0])

    features = explanation["features"]
    # Every model input is explained, in magnitude order rather than column order.
    assert {item["feature"] for item in features} == set(signal.FEATURE_COLUMNS)
    assert [item["rank"] for item in features] == list(range(1, len(features) + 1))
    magnitudes = [abs(item["contribution"]) for item in features]
    assert magnitudes == sorted(magnitudes, reverse=True)
    assert explanation["method"] == signal.SHAP_METHOD
    assert set(explanation["band_cutoffs"]) == {"Building", "Steady"}


def test_shap_factors_agree_with_the_explanation(trained: Path) -> None:
    """The card's top-3 and the audit list are one derivation, not two."""
    model, scaler = signal.load(trained)
    row = _user_rows().iloc[0]
    factors = signal.shap_factors(model, scaler, row, top_k=3)
    explanation = signal.shap_explanation(model, scaler, row)

    assert [factor["feature"] for factor in factors] == [
        item["feature"] for item in explanation["features"][:3]
    ]
    for factor, item in zip(factors, explanation["features"][:3]):
        assert factor["direction"] == item["direction"]
        assert factor["magnitude"] == pytest.approx(abs(item["contribution"]), abs=1e-3)


def test_shap_importance_is_ranked_and_never_raises(trained: Path, tmp_path: Path) -> None:
    rows = _user_rows()
    importance = signal.shap_importance(rows, trained)
    assert importance is not None
    assert importance["rows"] == len(rows)
    assert {item["feature"] for item in importance["features"]} == set(signal.FEATURE_COLUMNS)
    totals = [item["mean_abs_contribution"] for item in importance["features"]]
    assert totals == sorted(totals, reverse=True)
    assert importance["total_mean_abs"] > 0
    assert importance["method"] == signal.SHAP_METHOD
    for item in importance["features"]:
        assert item["direction"] in ("improves", "weakens")
    assert signal.shap_importance(rows, tmp_path / "empty") is None


def test_the_endpoint_returns_the_shap_block(client: TestClient) -> None:
    body = client.post("/credit-readiness", headers={"X-Demo-Token": TOKEN}).json()
    shap = body["shap"]
    assert shap is not None, "the model path must expose its exact contributions"
    assert shap["method"]
    assert isinstance(shap["base_value"], float)
    total = shap["base_value"] + sum(item["contribution"] for item in shap["features"])
    assert total == pytest.approx(shap["log_odds"], abs=0.05)
    for item in shap["features"]:
        assert item["direction"] in ("improves", "weakens")
        assert item["rank"] >= 1
    ConsistencySignalResponse.model_validate(body)


def test_the_shap_block_is_null_on_the_rule_path(tmp_path: Path) -> None:
    """No artifact means no SHAP values -- and an empty list would be a lie.

    ``factors: []`` reads as "nothing moved this user"; ``shap: null`` reads as
    "nothing was explained", which is what actually happened.
    """
    payload = signal_service.build_signal(
        "rahim", db_path=None, artifact_dir=tmp_path / "no_artifact"
    )
    assert payload["provenance"]["source"] == "rule"
    assert payload["shap"] is None


# --- the route contract ----------------------------------------------------
def test_the_frontend_path_is_credit_readiness(client: TestClient) -> None:
    """``web/src/lib/api.ts`` posts here, and posts an empty JSON body."""
    response = client.post("/credit-readiness", json={}, headers={"X-Demo-Token": TOKEN})
    assert response.status_code == 200
    body = response.json()
    for field in ("user_id", "band", "factors", "improvements", "not_a_decision",
                  "banner_en", "banner_bn", "auc", "provenance"):
        assert field in body, f"the frontend contract requires {field}"


def test_the_old_signal_path_is_gone(client: TestClient) -> None:
    """One route, one path: an alias is how two cards start to disagree."""
    assert client.post("/signal", headers={"X-Demo-Token": TOKEN}).status_code == 404


# --- the response is never a decision -------------------------------------
def test_response_carries_no_probability(client: TestClient) -> None:
    body = client.post("/credit-readiness", headers={"X-Demo-Token": TOKEN}).json()
    # The probability picks the band and is then dropped; nothing that could be
    # quoted as a credit score may appear in the payload.
    assert "probability" not in body
    assert "score" not in body
    assert "probability" not in json.dumps(body).lower()
    ConsistencySignalResponse.model_validate(body)


def test_response_is_pinned_to_not_a_decision(client: TestClient) -> None:
    body = client.post("/credit-readiness", headers={"X-Demo-Token": TOKEN}).json()
    assert body["not_a_decision"] is True
    assert body["banner_en"]
    assert body["banner_bn"]


def test_response_validates_against_the_frozen_schema(client: TestClient) -> None:
    response = client.post("/credit-readiness", headers={"X-Demo-Token": TOKEN})
    assert response.status_code == 200
    ConsistencySignalResponse.model_validate(response.json())


def test_factors_carry_plain_language_in_both_scripts(client: TestClient) -> None:
    for language in ("bn", "en"):
        body = client.post(
            "/credit-readiness", headers={"X-Demo-Token": TOKEN}, params={"language": language}
        ).json()
        for factor in body["factors"]:
            assert factor["plain_language"].strip()


def test_endpoint_requires_a_token(client: TestClient) -> None:
    assert client.post("/credit-readiness").status_code == 401
    assert client.post("/credit-readiness", headers={"X-Demo-Token": "wrong"}).status_code == 403


def test_feature_flag_switches_the_signal_off() -> None:
    settings = Settings(demo_auth_token=TOKEN, feature_signal=False)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    response = TestClient(app).post("/credit-readiness", headers={"X-Demo-Token": TOKEN})
    assert response.status_code == 503


def test_unknown_user_is_a_404_not_an_empty_band() -> None:
    settings = Settings(demo_auth_token=TOKEN, demo_user_id="nobody")
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    response = TestClient(app).post("/credit-readiness", headers={"X-Demo-Token": TOKEN})
    assert response.status_code == 404