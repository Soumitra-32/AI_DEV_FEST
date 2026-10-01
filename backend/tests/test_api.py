"""API shell tests (Phase 2): health, authentication and the frozen contracts.

Phase 8 extends this file once every endpoint is live; here we lock down the
shell: ``/health`` never breaks, the *token* decides the user (never the request),
and the contracts the frontend is written against stay valid.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.config import Settings, get_settings
from backend.app.main import create_app
from backend.app.schemas import (
    ConsistencySignalResponse,
    ExplainRequest,
    ForecastRequest,
    ForecastResponse,
    Provenance,
    SavingsPlanRequest,
    SavingsPlanResponse,
)

DEMO_TOKEN = "test-token"
DEMO_USER = "rahim"


@pytest.fixture(scope="module")
def api_settings(small_db) -> Settings:
    """Settings pointing at the small generated dataset from conftest."""
    return Settings(
        demo_auth_token=DEMO_TOKEN,
        demo_user_id=DEMO_USER,
        database_path=str(small_db),
    )


@pytest.fixture(scope="module")
def client(api_settings: Settings) -> TestClient:
    app = create_app(api_settings)
    app.dependency_overrides[get_settings] = lambda: api_settings
    return TestClient(app)


def _auth() -> dict:
    return {"X-Demo-Token": DEMO_TOKEN}


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------
def test_health_reports_ok_with_dataset_counts(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["available"] is True
    assert body["database"]["users"] > 0
    assert body["database"]["transactions"] > 0
    assert body["database"]["generated_at"]


def test_health_exposes_the_feature_flags(client: TestClient) -> None:
    features = client.get("/health").json()["features"]
    assert {
        "forecast",
        "savings_plan",
        "anomalies",
        "signal",
        "tips",
        "voice",
        "llm",
    } <= set(features)
    assert all(isinstance(value, bool) for value in features.values())


def test_health_degrades_instead_of_failing_without_a_dataset(tmp_path) -> None:
    settings = Settings(
        demo_auth_token=DEMO_TOKEN,
        database_path=str(tmp_path / "missing.db"),
    )
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database"]["available"] is False


# ---------------------------------------------------------------------------
# authentication: the token decides the user
# ---------------------------------------------------------------------------
def test_identity_requires_a_token(client: TestClient) -> None:
    assert client.get("/me").status_code == 401


def test_identity_rejects_a_wrong_token(client: TestClient) -> None:
    assert client.get("/me", headers={"X-Demo-Token": "not-the-token"}).status_code == 403


def test_identity_returns_the_user_behind_the_token(client: TestClient) -> None:
    response = client.get("/me", headers=_auth())
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == DEMO_USER
    assert body["cohort"] == "demo"
    assert body["is_demo_user"] is True
    assert body["persona"] == "daily_wage"
    assert body["language_pref"] == "bn"


def test_user_id_cannot_be_supplied_by_the_caller(client: TestClient) -> None:
    """A query-string user id must be ignored: the token wins."""
    response = client.get("/me?user_id=U0001", headers=_auth())
    assert response.status_code == 200
    assert response.json()["user_id"] == DEMO_USER


def test_bearer_header_is_accepted_as_well(client: TestClient) -> None:
    response = client.get("/me", headers={"Authorization": f"Bearer {DEMO_TOKEN}"})
    assert response.status_code == 200
    assert response.json()["user_id"] == DEMO_USER


# ---------------------------------------------------------------------------
# contracts
# ---------------------------------------------------------------------------
def test_openapi_exposes_the_phase_two_paths(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/health", "/me"} <= set(paths)


def test_forecast_request_bounds_the_horizon() -> None:
    assert ForecastRequest().horizon_days == 14
    with pytest.raises(ValidationError):
        ForecastRequest(horizon_days=0)
    with pytest.raises(ValidationError):
        ForecastRequest(horizon_days=999)


def test_savings_plan_request_requires_a_positive_goal() -> None:
    assert SavingsPlanRequest(goal_bdt=30000, months=6).months == 6
    with pytest.raises(ValidationError):
        SavingsPlanRequest(goal_bdt=-1, months=6)
    with pytest.raises(ValidationError):
        SavingsPlanRequest(goal_bdt=30000, months=0)


def test_explain_request_rejects_empty_messages() -> None:
    assert ExplainRequest(message="৬ মাসে ৩০,০০০ জমাতে চাই").language == "bn"
    with pytest.raises(ValidationError):
        ExplainRequest(message="")


def test_provenance_requires_all_three_parts() -> None:
    provenance = Provenance(prediction="p", assumption="a", explanation="e")
    assert provenance.source == "rule"
    with pytest.raises(ValidationError):
        Provenance(prediction="p", assumption="a")


def test_consistency_signal_is_a_band_not_a_score() -> None:
    signal = ConsistencySignalResponse(
        user_id=DEMO_USER,
        band="Steady",
        provenance=Provenance(prediction="p", assumption="a", explanation="e"),
    )
    assert signal.not_a_decision is True
    assert "loan" in signal.banner_en.lower()

    with pytest.raises(ValidationError):
        ConsistencySignalResponse(
            user_id=DEMO_USER,
            band="Excellent",  # not a valid band, and never a numeric score
            provenance=Provenance(prediction="p", assumption="a", explanation="e"),
        )
    with pytest.raises(ValidationError):
        ConsistencySignalResponse(
            user_id=DEMO_USER,
            band="Steady",
            score=812,  # a numeric score is deliberately absent from the contract
            provenance=Provenance(prediction="p", assumption="a", explanation="e"),
        )


def test_future_responses_can_be_constructed() -> None:
    """Phase 3+ shapes are already frozen, so the UI can be built against them."""
    forecast = ForecastResponse(
        user_id=DEMO_USER,
        horizon_days=14,
        generated_at="2025-07-01T00:00:00Z",
        provenance=Provenance(prediction="p", assumption="a", explanation="e"),
    )
    assert forecast.days == [] and forecast.pressure_days == []

    plan = SavingsPlanResponse(
        user_id=DEMO_USER,
        goal_bdt=30000,
        months=6,
        feasible=True,
        required_monthly_bdt=5000,
        forecasted_surplus_bdt=8600,
        safety_buffer_bdt=1200,
        feasible_monthly_bdt=7400,
        do_nothing={"description": "no change", "estimated_cost_bdt": 1920, "horizon_months": 6},
        provenance=Provenance(prediction="p", assumption="a", explanation="e"),
    )
    assert plan.arithmetic == [] and plan.trade_offs == []


