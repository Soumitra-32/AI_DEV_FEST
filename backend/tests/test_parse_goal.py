"""Tests for POST /parse-goal (voice/text -> numbers).

Pure function behind a thin router: no token, no database. These lock the
contract the web home page depends on — missing halves stay missing (never
guessed), garbage validates as 422 via the schema.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings, get_settings
from backend.app.main import create_app

PARSE_TOKEN = "parse-goal-token"


@pytest.fixture(scope="module")
def client() -> TestClient:
    settings = Settings(demo_auth_token=PARSE_TOKEN)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


@pytest.mark.parametrize(
    ("message", "goal", "months", "complete"),
    [
        ("৬ মাসে ৳৩০,০০০ জমাতে চাই", 30000.0, 6, True),
        ("৫০ হাজার ১২ মাসে জমাতে চাই", 50000.0, 12, True),
        ("২ লাখ টাকা ১২ মাসে জমাবো", 200000.0, 12, True),
        ("I want to save 30000 taka in 6 months", 30000.0, 6, True),
        ("save 1.5 lakh in 10 months", 150000.0, 10, True),
        ("৬ মাসে কিছু জমাতে চাই", None, 6, False),
        ("৳৩০,০০০ জমাতে চাই", 30000.0, None, False),
        ("what is the weather tomorrow", None, None, False),
    ],
)
def test_parse_goal_contract(client: TestClient, message: str, goal, months, complete: bool) -> None:
    response = client.post("/parse-goal", json={"message": message})
    assert response.status_code == 200
    body = response.json()
    assert body["goal_bdt"] == goal
    assert body["months"] == months
    assert body["is_complete"] is complete


def test_parse_goal_rejects_empty_message(client: TestClient) -> None:
    assert client.post("/parse-goal", json={"message": ""}).status_code == 422


def test_metrics_serves_model_scoreboard() -> None:
    from fastapi.testclient import TestClient

    from backend.app.config import Settings, get_settings
    from backend.app.main import create_app

    # /metrics follows the demo-token convention like every other app router.
    settings = Settings(demo_auth_token=PARSE_TOKEN)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    response = TestClient(app).get(
        "/metrics", headers={"X-Demo-Token": PARSE_TOKEN}
    )
    assert response.status_code == 200
    body = response.json()
    assert {"forecast", "anomaly", "signal", "fairness", "notes"} <= set(body)
    assert body["generated_at"]


@pytest.mark.parametrize(
    ("message", "goal", "months"),
    [
        ("save thirty thousand in six months", 30000.0, 6),
        ("save fifty thousand in twelve months", 50000.0, 12),
        ("save thirty thousand six months", 30000.0, 6),
        ("save one hundred twenty thousand in a year", 120000.0, 12),
        ("save 50000 in a year", 50000.0, 12),
        ("save 50000 in 2 years", 50000.0, 24),
        ("ত্রিশ হাজার টাকা ছয় মাসে জমাতে চাই", 30000.0, 6),
        ("পঞ্চাশ হাজার বারো মাসে", 50000.0, 12),
        ("এক লাখ টাকা এক বছরে জমাবো", 100000.0, 12),
    ],
)
def test_parse_goal_reads_spoken_english(client: TestClient, message: str, goal: float, months: int) -> None:
    body = client.post("/parse-goal", json={"message": message}).json()
    assert body["goal_bdt"] == goal
    assert body["months"] == months
    assert body["is_complete"] is True
