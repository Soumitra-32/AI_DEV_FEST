"""Tests for POST /parse-goal (voice/text -> numbers).

Pure function behind a thin router: no token, no database. These lock the
contract the web home page depends on — missing halves stay missing (never
guessed), garbage validates as 422 via the schema.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


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
