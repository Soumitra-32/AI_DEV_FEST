"""Tests for tip retrieval (Phase 7).

The point of the "retrieval, then LLM phrasing" split is that the model cannot
invent advice. These tests hold that line:

* every returned tip comes from the curated bank -- nothing else can be shown;
* selection is driven by the user's *own* measured features, not by a constant;
* each tip reports the trigger that fired, so "why am I seeing this?" is answerable;
* a missing or malformed bank degrades to "no tips" instead of raising.

No LLM and no network are involved, by design.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.data import features as user_features
from backend.genai import rag

#: A user who trips every high-signal trigger.
HEAVY_SPENDER = {
    "cash_out_count_per_month": 8.0,
    "cash_out_share_of_outflow": 0.55,
    "fee_share_of_income": 0.04,
    "shortfall_days_per_month": 4.0,
    "balance_min_bdt": 200.0,
    "income_days_per_month": 1.0,
    "month_end_spend_ratio": 1.9,
}

#: A user whose numbers trip nothing.
QUIET_USER = {
    "cash_out_count_per_month": 0.0,
    "cash_out_share_of_outflow": 0.0,
    "fee_share_of_income": 0.0,
    "shortfall_days_per_month": 0.0,
    "balance_min_bdt": 50000.0,
    "income_days_per_month": 4.0,
    "month_end_spend_ratio": 1.0,
}


def test_the_bank_loads_and_is_not_empty() -> None:
    bank = rag.load_bank()
    assert len(bank) >= 15
    assert all(tip.get("id") for tip in bank)


def test_every_tip_is_written_in_both_languages() -> None:
    """A Bangla-first product may not ship an English-only tip."""
    for tip in rag.load_bank():
        assert tip["title_bn"].strip(), tip["id"]
        assert tip["body_bn"].strip(), tip["id"]
        assert tip["title_en"].strip(), tip["id"]
        assert tip["body_en"].strip(), tip["id"]


def test_every_trigger_is_a_real_feature_and_operator() -> None:
    """A trigger naming an unknown feature could never fire -- a silent dead tip."""
    known = set(user_features.FEATURE_COLUMNS) | {"months_observed"}
    for tip in rag.load_bank():
        trigger = tip["trigger"]
        assert trigger["feature"] in known, tip["id"]
        assert trigger["op"] in rag.OPERATORS, tip["id"]
        assert isinstance(trigger["value"], (int, float)), tip["id"]


def test_retrieval_returns_only_curated_tips() -> None:
    """The core guarantee: nothing outside the bank is ever shown."""
    allowed = set(rag.bank_ids())
    for tip in rag.retrieve(HEAVY_SPENDER, limit=10):
        assert tip["id"] in allowed


def test_a_heavy_spender_gets_tips() -> None:
    assert rag.retrieve(HEAVY_SPENDER, limit=5)


def test_a_quiet_user_gets_fewer_tips_than_a_heavy_one() -> None:
    """Tips must be earned by the user's behaviour, not always shown."""
    assert len(rag.retrieve(QUIET_USER, limit=10)) < len(rag.retrieve(HEAVY_SPENDER, limit=10))


def test_no_trigger_no_tip() -> None:
    """Each tip must be individually falsifiable."""
    assert rag.retrieve({"cash_out_count_per_month": 0.0}, limit=10) == []
    assert rag.retrieve({"fee_share_of_income": 0.0}, limit=10) == []


def test_every_returned_tip_shows_the_trigger_that_fired() -> None:
    for tip in rag.retrieve(HEAVY_SPENDER, limit=5):
        assert "observed" in tip["trigger"]
        assert tip["trigger"] not in ("", None)


def test_limit_is_respected() -> None:
    assert len(rag.retrieve(HEAVY_SPENDER, limit=2)) <= 2
    assert len(rag.retrieve(HEAVY_SPENDER, limit=0)) >= 1  # never empty-handed by accident


def test_intent_narrows_the_bank() -> None:
    """A "fees" question should not be answered with a balance tip."""
    fees = {tip["id"] for tip in rag.retrieve(HEAVY_SPENDER, limit=5, intent="fees")}
    tips = {tip["id"] for tip in rag.retrieve(HEAVY_SPENDER, limit=5, intent="tips")}
    assert fees and tips
    assert fees != tips


def test_unknown_features_do_not_crash_retrieval() -> None:
    assert rag.retrieve({"not_a_feature": 99.0}, limit=3) == []


def test_a_missing_bank_returns_no_tips_rather_than_raising(tmp_path: Path) -> None:
    assert rag.load_bank(tmp_path / "nope.json") == ()
    assert rag.retrieve(HEAVY_SPENDER, limit=3, bank=()) == []


def test_a_malformed_bank_is_ignored(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert rag.load_bank(broken) == ()


def test_search_finds_a_tip_by_its_own_words() -> None:
    hits = rag.search("cash out transfer")
    assert hits
    assert "cash_out_to_transfer" in {hit["id"] for hit in hits}


def test_search_on_an_empty_query_returns_nothing() -> None:
    assert rag.search("") == []
    assert rag.search("   ") == []


def test_search_only_ever_returns_curated_tips() -> None:
    allowed = set(rag.bank_ids())
    for hit in rag.search("saving money fee balance"):
        assert hit["id"] in allowed


def test_the_bank_file_is_valid_json_with_a_version() -> None:
    payload = json.loads((rag.TIPS_FILE).read_text(encoding="utf-8"))
    assert payload["version"]
    assert len(payload["tips"]) == len(rag.load_bank())


def test_rahims_own_numbers_retrieve_tips(small_db) -> None:
    """End to end against the generated demo user, not a fixture."""
    path = small_db
    frame = user_features.user_features(
        user_features.load_config(), user_features.load_transactions(path)
    )
    row = user_features.feature_row(frame, "rahim")
    tips = rag.retrieve(row, limit=3)
    assert tips
    # Rahim is seeded with five cash-outs, so the fee tip must be there.
    assert "cash_out_to_transfer" in {tip["id"] for tip in tips}