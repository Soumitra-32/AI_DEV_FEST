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


# --- the response is never a decision -------------------------------------
def test_response_carries_no_probability(client: TestClient) -> None:
    body = client.post("/signal", headers={"X-Demo-Token": TOKEN}).json()
    # The probability picks the band and is then dropped; nothing that could be
    # quoted as a credit score may appear in the payload.
    assert "probability" not in body
    assert "score" not in body
    assert "probability" not in json.dumps(body).lower()
    ConsistencySignalResponse.model_validate(body)


def test_response_is_pinned_to_not_a_decision(client: TestClient) -> None:
    body = client.post("/signal", headers={"X-Demo-Token": TOKEN}).json()
    assert body["not_a_decision"] is True
    assert body["banner_en"]
    assert body["banner_bn"]


def test_response_validates_against_the_frozen_schema(client: TestClient) -> None:
    response = client.post("/signal", headers={"X-Demo-Token": TOKEN})
    assert response.status_code == 200
    ConsistencySignalResponse.model_validate(response.json())


def test_factors_carry_plain_language_in_both_scripts(client: TestClient) -> None:
    for language in ("bn", "en"):
        body = client.post(
            "/signal", headers={"X-Demo-Token": TOKEN}, params={"language": language}
        ).json()
        for factor in body["factors"]:
            assert factor["plain_language"].strip()


def test_endpoint_requires_a_token(client: TestClient) -> None:
    assert client.post("/signal").status_code == 401
    assert client.post("/signal", headers={"X-Demo-Token": "wrong"}).status_code == 403


def test_feature_flag_switches_the_signal_off() -> None:
    settings = Settings(demo_auth_token=TOKEN, feature_signal=False)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    response = TestClient(app).post("/signal", headers={"X-Demo-Token": TOKEN})
    assert response.status_code == 503


def test_unknown_user_is_a_404_not_an_empty_band() -> None:
    settings = Settings(demo_auth_token=TOKEN, demo_user_id="nobody")
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    response = TestClient(app).post("/signal", headers={"X-Demo-Token": TOKEN})
    assert response.status_code == 404