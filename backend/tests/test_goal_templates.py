"""Tests for the Goal Copilot templates (Phase 8).

The plan asks for templates for education, an emergency fund, travel, a device
and family. What these tests pin:

* all five exist, are bilingual, and are sized from the *user's* income;
* the arithmetic lives in the rules module and is quoted with its assumption;
* the endpoint degrades (401 / 404 / 503) rather than inventing a goal.
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
from backend.rules import goal_templates

DEMO_TOKEN = "test-token"
DEMO_USER = "rahim"

EXPECTED_KEYS = {"education", "emergency_fund", "travel", "device", "family"}


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
    return _client(_settings(tmp_path_factory.mktemp("goals"), small_db))


# --- the rules module ------------------------------------------------------
def test_all_five_plan_goals_exist() -> None:
    assert set(goal_templates.template_keys()) == EXPECTED_KEYS


def test_every_template_is_bilingual_and_rounded() -> None:
    for key in goal_templates.template_keys():
        template = goal_templates.get(key)
        assert template.label_bn.strip() and template.label_en.strip()
        assert template.description_bn.strip() and template.description_en.strip()
        goal = template.suggested_goal(10_000)
        assert goal % 500 == 0  # rounded, never a fake precise number
        assert goal > 0


def test_goal_scales_with_income() -> None:
    template = goal_templates.get("emergency_fund")
    assert template.suggested_goal(20_000) > template.suggested_goal(10_000)


def test_a_zero_income_user_still_gets_a_floor() -> None:
    """Never a zero-taka goal: the card offers a shape, not an empty target."""
    for key in goal_templates.template_keys():
        assert goal_templates.get(key).suggested_goal(0.0) >= goal_templates.get(key).min_goal_bdt


def test_unknown_template_raises() -> None:
    with pytest.raises(KeyError):
        goal_templates.get("not-a-goal")


def test_payload_carries_its_assumption() -> None:
    payload = goal_templates.resolve("travel", 12_000)
    assert payload["provenance"]["source"] == "template"
    assert "assumption" in payload["provenance"]["assumption"].lower()
    assert payload["goal_label_bn"].strip()


# --- the endpoint ----------------------------------------------------------
def test_goal_templates_endpoint_returns_all_five(client: TestClient) -> None:
    body = client.get("/goal-templates", headers=_auth()).json()
    assert body["user_id"] == DEMO_USER
    keys = {item["key"] for item in body["templates"]}
    assert keys == EXPECTED_KEYS
    for item in body["templates"]:
        assert item["suggested_goal_bdt"] >= 0
        assert item["default_months"] >= 1
        assert item["goal_label_bn"].strip()


def test_goal_templates_requires_a_token(client: TestClient) -> None:
    assert client.get("/goal-templates").status_code == 401


def test_goal_templates_can_be_switched_off(small_db, tmp_path) -> None:
    client = _client(_settings(tmp_path, small_db, feature_goal_templates=False))
    assert client.get("/goal-templates", headers=_auth()).status_code == 503


def test_goal_templates_unknown_user_is_a_404(small_db, tmp_path) -> None:
    client = _client(_settings(tmp_path, small_db, demo_user_id="nobody-here"))
    assert client.get("/goal-templates", headers=_auth()).status_code == 404
