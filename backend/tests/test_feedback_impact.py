"""Tests for feedback collection, telemetry events, and customer impact aggregation.

Verifies:
- Authenticated user only (401/403 on missing or invalid tokens)
- User isolation: server-side resolution and salted-hash respondent tokens (never raw user IDs)
- Strict validation of feedback and product events
- Discarding of free text and prevention of PII leakage
- Complete recommendation lifecycle tracking (shown -> accepted/rejected -> action_completed)
- Customer impact aggregation with correct denominators and safe zero-data handling
- GET /metrics integration with customer_impact block
"""
from __future__ import annotations

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from backend.app.config import Settings, get_settings
from backend.app.main import create_app
from backend.app.services import feedback_service

DEMO_TOKEN = "test-token-impact"
DEMO_USER = "rahim"


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {DEMO_TOKEN}"}


@pytest.fixture
def test_app_and_client(tmp_path: Path):
    feedback_file = tmp_path / "feedback.jsonl"
    events_file = tmp_path / "events.jsonl"
    settings = Settings(
        demo_auth_token=DEMO_TOKEN,
        demo_user_id=DEMO_USER,
        artifact_dir=str(tmp_path),
    )

    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    return client, settings, feedback_file, events_file


# ---------------------------------------------------------------------------
# 1. Feedback API & Authentication
# ---------------------------------------------------------------------------
def test_feedback_requires_authentication(test_app_and_client):
    client, _, _, _ = test_app_and_client
    resp = client.post("/feedback", json={"feature": "savings_plan", "helpful": True})
    assert resp.status_code == 401

    resp = client.post(
        "/feedback",
        headers={"Authorization": "Bearer wrong-token"},
        json={"feature": "savings_plan", "helpful": True},
    )
    assert resp.status_code == 403


def test_feedback_validates_payload(test_app_and_client):
    client, _, _, _ = test_app_and_client
    # Missing both surface and feature
    resp = client.post("/feedback", headers=_auth(), json={"helpful": True})
    assert resp.status_code == 422

    # Rating out of bounds (< 1 or > 5)
    resp = client.post(
        "/feedback",
        headers=_auth(),
        json={"feature": "forecast", "helpful": True, "rating": 6},
    )
    assert resp.status_code == 422

    resp = client.post(
        "/feedback",
        headers=_auth(),
        json={"feature": "forecast", "helpful": True, "rating": 0},
    )
    assert resp.status_code == 422


def test_feedback_records_successfully_and_anonymises(test_app_and_client):
    client, settings, feedback_file, _ = test_app_and_client
    payload = {
        "feature": "savings_plan",
        "helpful": True,
        "understood": True,
        "acted_on": True,
        "rating": 5,
        "comment": "This was super clear and helpful! My phone is 01700000000",
    }
    resp = client.post("/feedback", headers=_auth(), json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "recorded"
    assert data["feature"] == "savings_plan"
    assert data["helpful"] is True
    assert data["understood"] is True
    assert data["acted_on"] is True
    assert data["rating"] == 5

    # Respondent must be a 12-char salted hash, NEVER the raw user_id
    assert data["respondent"] != DEMO_USER
    assert len(data["respondent"]) == 12

    # Raw comment text must NOT be in the response
    assert "01700000000" not in str(data)

    # Verify on disk
    assert feedback_file.exists()
    line = feedback_file.read_text(encoding="utf-8").strip()
    saved = json.loads(line)
    assert saved["respondent"] == data["respondent"]
    assert saved["has_comment"] is True
    assert "01700000000" not in line


# ---------------------------------------------------------------------------
# 2. Product Events Telemetry
# ---------------------------------------------------------------------------
def test_events_require_authentication(test_app_and_client):
    client, _, _, _ = test_app_and_client
    resp = client.post("/events", json={"event_type": "forecast_viewed"})
    assert resp.status_code == 401


def test_events_validates_event_type(test_app_and_client):
    client, _, _, _ = test_app_and_client
    resp = client.post(
        "/events",
        headers=_auth(),
        json={"event_type": "invalid_event_type"},
    )
    assert resp.status_code == 422


def test_events_records_and_sanitizes_properties(test_app_and_client):
    client, _, _, events_file = test_app_and_client
    payload = {
        "event_type": "recommendation_shown",
        "feature": "tips",
        "recommendation_id": "tip-mfs-fee",
        "properties": {
            "channel": "app",
            "account_number": "1234567890",  # Should be stripped by sanitizer
            "savings_bdt": 45.0,
        },
    }
    resp = client.post("/events", headers=_auth(), json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert data["event_type"] == "recommendation_shown"
    assert data["recommendation_id"] == "tip-mfs-fee"
    assert "account_number" not in data["properties"]
    assert data["properties"]["channel"] == "app"
    assert data["properties"]["savings_bdt"] == 45.0

    # Verify on disk
    assert events_file.exists()
    line = events_file.read_text(encoding="utf-8").strip()
    saved = json.loads(line)
    assert saved["event_type"] == "recommendation_shown"
    assert "account_number" not in saved["properties"]


# ---------------------------------------------------------------------------
# 3. Recommendation Lifecycle Tracking
# ---------------------------------------------------------------------------
def test_recommendation_lifecycle_measurement(tmp_path: Path):
    feedback_file = tmp_path / "fb.jsonl"
    events_file = tmp_path / "ev.jsonl"

    # 1. Recommendation shown (3 times)
    for i in range(3):
        feedback_service.record_event(
            DEMO_USER,
            "recommendation_shown",
            recommendation_id=f"rec-{i}",
            path=events_file,
        )

    impact1 = feedback_service.compute_customer_impact(
        events_path=events_file, feedback_path=feedback_file
    )
    assert impact1["recommendations_shown"] == 3
    assert impact1["recommendations_accepted"] == 0
    assert impact1["actions_completed"] == 0
    assert impact1["action_completion_rate_pct"] is None  # no accepts yet

    # 2. Recommendation accepted (2 of them)
    feedback_service.record_event(
        DEMO_USER,
        "recommendation_accepted",
        recommendation_id="rec-0",
        path=events_file,
    )
    feedback_service.record_event(
        DEMO_USER,
        "recommendation_accepted",
        recommendation_id="rec-1",
        path=events_file,
    )
    # And 1 rejected
    feedback_service.record_event(
        DEMO_USER,
        "recommendation_rejected",
        recommendation_id="rec-2",
        path=events_file,
    )

    impact2 = feedback_service.compute_customer_impact(
        events_path=events_file, feedback_path=feedback_file
    )
    assert impact2["recommendations_shown"] == 3
    assert impact2["recommendations_accepted"] == 2
    assert impact2["recommendations_rejected"] == 1
    assert impact2["recommendation_acceptance_rate_pct"] == 66.7
    assert impact2["actions_completed"] == 0
    assert impact2["action_completion_rate_pct"] == 0.0

    # 3. Action completed (1 completed)
    feedback_service.record_event(
        DEMO_USER,
        "recommendation_action_completed",
        recommendation_id="rec-0",
        path=events_file,
    )

    impact3 = feedback_service.compute_customer_impact(
        events_path=events_file, feedback_path=feedback_file
    )
    assert impact3["actions_completed"] == 1
    # 1 completed out of 2 accepted = 50.0%
    assert impact3["action_completion_rate_pct"] == 50.0


# ---------------------------------------------------------------------------
# 4. Zero Data State & Safety
# ---------------------------------------------------------------------------
def test_zero_data_handling_safe_and_unfabricated(tmp_path: Path):
    feedback_file = tmp_path / "empty_fb.jsonl"
    events_file = tmp_path / "empty_ev.jsonl"

    impact = feedback_service.compute_customer_impact(
        events_path=events_file, feedback_path=feedback_file
    )
    assert impact["has_data"] is False
    assert impact["message"] == "No interaction data collected yet"
    assert impact["total_feedback"] == 0
    assert impact["helpful_feedback_rate_pct"] is None
    assert impact["understanding_rate_pct"] is None
    assert impact["action_completion_rate_pct"] is None
    assert impact["recommendations_shown"] == 0
    assert impact["actions_completed"] == 0


# ---------------------------------------------------------------------------
# 5. GET /metrics returns customer_impact
# ---------------------------------------------------------------------------
def test_metrics_endpoint_includes_customer_impact(test_app_and_client):
    client, _, _, _ = test_app_and_client
    resp = client.get("/metrics", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()
    assert "customer_impact" in data
    assert data["customer_impact"]["has_data"] is False
    assert data["customer_impact"]["message"] == "No interaction data collected yet"

    # Now add feedback and events
    client.post(
        "/feedback",
        headers=_auth(),
        json={"feature": "savings_plan", "helpful": True, "understood": True},
    )
    client.post(
        "/events",
        headers=_auth(),
        json={"event_type": "savings_plan_created", "feature": "savings_plan"},
    )

    resp2 = client.get("/metrics", headers=_auth())
    assert resp2.status_code == 200
    data2 = resp2.json()
    ci = data2["customer_impact"]
    assert ci["has_data"] is True
    assert ci["total_feedback"] >= 1
    assert ci["helpful_feedback_rate_pct"] == 100.0
    assert ci["understanding_rate_pct"] == 100.0
    assert ci["savings_plans_created"] >= 1
