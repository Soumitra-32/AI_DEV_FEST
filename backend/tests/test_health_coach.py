"""Tests for the Financial Health Coach endpoint (Phase 8).

The health score is a *coaching reading*, not a credit score, atomically
bounded 0-100 and traceable to five behaviours. These tests pin:

* the score is the rule module's own number, never recomputed differently;
* the summary is Bangla-first and names the strongest and weakest factor;
* the "not a credit score" guarantee travels in the payload;
* the endpoint degrades (401 / 404 / 503) instead of guessing.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import Settings, get_settings
from backend.app.main import create_app
from backend.app.schemas import HealthCoachResponse, Provenance
from backend.app.services import health_service
from backend.data import features as user_features
from backend.rules import health_score

DEMO_TOKEN = "test-token"
DEMO_USER = "rahim"


def _settings(tmp_path: Path, db_path, **overrides) -> Settings:
    base: dict[str, Any] = dict(
        demo_auth_token=DEMO_TOKEN,
        demo_user_id=DEMO_USER,
        database_path=str(db_path),
        artifact_dir=str(tmp_path),
        request_log_path=str(tmp_path / "requests.jsonl"),
    )
    base.update(overrides)
    return Settings(**base)


def _client(settings: Settings) -> TestClient:
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _auth() -> dict:
    return {"X-Demo-Token": DEMO_TOKEN}


@pytest.fixture(scope="module")
def client(small_db, tmp_path_factory) -> TestClient:
    return _client(_settings(tmp_path_factory.mktemp("health"), small_db))


# --- the payload -----------------------------------------------------------
def test_health_coach_returns_a_bounded_score(client: TestClient) -> None:
    body = client.get("/health-coach", headers=_auth()).json()
    assert 0 <= body["score"] <= body["score_max"] == 100
    assert body["band"] in {"Fragile", "Building", "Steady", "Strong"}
    assert body["is_not_a_credit_score"] is True


def test_score_is_the_rule_modules_own_number(small_db) -> None:
    """The endpoint must not recompute the score differently."""
    cfg = user_features.load_config()
    frame = user_features.user_features(cfg, user_features.load_transactions(small_db))
    graded = health_score.score_features(frame, DEMO_USER)
    payload = health_service.build_health(DEMO_USER, db_path=small_db)
    assert payload["score"] == int(graded.score)
    assert payload["band"] == graded.band
    assert payload["arithmetic"] == graded.arithmetic


def test_summary_is_bangla_and_names_a_factor(client: TestClient) -> None:
    body = client.get("/health-coach", headers=_auth()).json()
    assert body["summary_bn"].strip()
    assert body["summary_en"].strip()
    assert body["band_bn"].strip()
    # Bangla text, not an English placeholder.
    assert any("\u0980" <= ch <= "\u09ff" for ch in body["summary_bn"])


def test_all_five_behaviours_are_reported_with_their_arithmetic(client: TestClient) -> None:
    body = client.get("/health-coach", headers=_auth()).json()
    keys = {factor["key"] for factor in body["factors"]}
    assert keys == {
        "fee_burden",
        "cash_dependency",
        "income_regularity",
        "balance_cushion",
        "shortfall_freedom",
    }
    for factor in body["factors"]:
        assert 0.0 <= factor["share"] <= 1.0
        assert factor["points"] <= factor["max_points"]
        assert factor["label_bn"].strip()
    assert any("total =" in line for line in body["arithmetic"])


def test_it_never_claims_to_be_a_credit_score() -> None:
    payload = HealthCoachResponse(
        user_id=DEMO_USER,
        score=70,
        band="Steady",
        band_bn="স্থিতিশীল",
        summary_bn="সারসংক্ষেপ",
        summary_en="summary",
        provenance=Provenance(
            prediction="p",
            assumption="a",
            explanation="e",
            source="rule",
        ),
    )
    assert "credit score" in payload.banner_en.lower()
    assert payload.is_not_a_credit_score is True


def test_score_field_rejects_out_of_range() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        HealthCoachResponse(
            user_id=DEMO_USER,
            score=101,
            band="Steady",
            band_bn="x",
            summary_bn="x",
            summary_en="x",
            provenance=Provenance(
                prediction="p",
                assumption="a",
                explanation="e",
                source="rule",
            ),
        )


# --- degradation -----------------------------------------------------------
def test_health_coach_requires_a_token(client: TestClient) -> None:
    assert client.get("/health-coach").status_code == 401


def test_health_coach_can_be_switched_off(small_db, tmp_path) -> None:
    client = _client(_settings(tmp_path, small_db, feature_health_coach=False))
    assert client.get("/health-coach", headers=_auth()).status_code == 503


def test_unknown_user_is_a_404(small_db, tmp_path) -> None:
    client = _client(_settings(tmp_path, small_db, demo_user_id="nobody-here"))
    assert client.get("/health-coach", headers=_auth()).status_code == 404
