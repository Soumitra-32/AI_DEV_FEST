"""Tests for the six LLM uses and the three-key failover pool.

The LLM is stubbed everywhere -- no key, no network -- because what matters is the
envelope around the model:

* ``client.complete`` fails over primary -> backup-1 -> backup-2, and raises once
  every key has failed so the caller falls back to a template;
* the intent classifier returns a whitelisted intent, has its parameters
  re-validated in Python, and degrades to the keyword classifier on any failure;
* a new intent can never ship without a template, a prompt instruction and a
  grounded context;
* tip phrasing may only rephrase, and its output is checked like any other.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from backend.app.config import Settings
from backend.app.services import explain_service
from backend.genai import client as llm_client
from backend.genai import explain as genai_explain
from backend.genai import fallback, intent as genai_intent, prompts, rag
from backend.rules import guardrails

DEMO_USER = "rahim"


class _Completions:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0) if self.replies else self.replies
        if isinstance(reply, Exception):
            raise reply
        message = type("Msg", (), {"content": reply})()
        return type("Completion", (), {"choices": [type("C", (), {"message": message})()]})


class _Client:
    """A stub transport whose replies are queued, exceptions included."""

    def __init__(self, *replies):
        self.chat = type("Chat", (), {"completions": _Completions(replies)})()


#: Every ``Settings`` the pool tests use must ignore the developer's real
#: ``.env`` and any ``LLM_*`` variables exported in the shell. Without this the
#: suite passes or fails depending on whether the person running it has keys
#: configured -- and a "no keys configured" assertion would silently become a
#: "my own key is configured" one. ``_env_file=None`` stops the dotenv read;
#: the blank defaults stop ambient environment variables taking over.
_NO_ENV = {"_env_file": None}


def _bare_settings(**overrides) -> Settings:
    """Settings that read no ``.env`` and inherit no ambient ``LLM_*`` value."""
    values: dict[str, Any] = {
        "llm_api_key": "",
        "llm_backup_api_key_1": "",
        "llm_backup_api_key_2": "",
        **_NO_ENV,
    }
    values.update(overrides)
    return Settings(**values)


def _pool_settings(**overrides) -> Settings:
    """Settings with all three keys set, so the failover pool is exercised.

    Built through a merged dict rather than duplicate keywords: passing
    ``**overrides`` alongside literal keys raises ``TypeError`` the moment an
    override names one of them, which is exactly what the provider-override test
    does.
    """
    return _bare_settings(
        **{
            "llm_api_key": "primary-key",
            "llm_backup_api_key_1": "backup-one",
            "llm_backup_api_key_2": "backup-two",
            **overrides,
        }
    )


# ---------------------------------------------------------------------------
# the three-key pool
# ---------------------------------------------------------------------------
def test_three_keys_make_three_providers_in_order() -> None:
    pool = llm_client.providers_from_settings(_pool_settings())
    assert [item.name for item in pool] == ["primary", "backup-1", "backup-2"]


def test_an_empty_backup_key_is_dropped_rather_than_tried() -> None:
    pool = llm_client.providers_from_settings(_bare_settings(llm_api_key="primary-key"))
    assert [item.name for item in pool] == ["primary"]


def test_a_backup_can_be_a_different_provider() -> None:
    settings = _pool_settings(
        llm_backup_api_key_1="other", llm_backup_base_url_1="https://example.test/v1",
        llm_backup_model_1="some-other-model",
    )
    pool = llm_client.providers_from_settings(settings)
    assert pool[1].base_url == "https://example.test/v1"
    assert pool[1].model == "some-other-model"
    # an unset override inherits the primary's, so it is never blank
    assert pool[2].base_url == settings.llm_base_url


def test_the_pool_is_disabled_with_no_keys() -> None:
    assert llm_client.enabled(_bare_settings()) is False
    assert llm_client.enabled(_bare_settings(llm_api_key="k")) is True
    assert llm_client.enabled(_bare_settings(llm_api_key="k", feature_llm=False)) is False


def test_settings_report_how_many_keys_are_configured() -> None:
    assert _bare_settings().llm_provider_count == 0
    assert _pool_settings().llm_provider_count == 3
    assert _bare_settings(llm_api_key="only-primary").llm_provider_count == 1


def test_the_provider_label_never_contains_the_key() -> None:
    """Only the label reaches a log line, so it must be key-free."""
    provider = llm_client.providers_from_settings(_pool_settings())[0]
    assert provider.label == "primary"
    assert "primary-key" not in provider.label


def test_a_failure_message_never_carries_a_key(monkeypatch) -> None:
    """The failover error names the provider, never the credential."""
    monkeypatch.setattr(
        llm_client, "_build",
        lambda _provider, _timeout: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(llm_client.AllProvidersFailed) as caught:
        llm_client.complete([], _pool_settings())
    blob = str(caught.value) + repr(caught.value.failures)
    assert "backup-one" not in blob and "backup-two" not in blob


def test_failover_falls_through_to_the_second_key(monkeypatch) -> None:
    """A dead primary must be invisible to the caller."""
    calls: list[str] = []

    def fake_build(provider, _timeout):
        calls.append(provider.name)
        if provider.name == "primary":
            raise RuntimeError("401 unauthorized")
        return type("Ok", (), {"chat": type("Chat", (), {"completions": _Completions(["ok"])})})

    monkeypatch.setattr(llm_client, "_build", fake_build)
    text, label = llm_client.complete([{"role": "user", "content": "{}"}], _pool_settings())
    assert text == "ok"
    assert label == "backup-1"
    assert calls == ["primary", "backup-1"]


def test_all_three_keys_failing_raises_so_the_caller_falls_back(monkeypatch) -> None:
    """Exhausting the pool must surface, not silently return an empty answer."""
    attempts: list[str] = []

    def fake_build(provider, _timeout):
        attempts.append(provider.name)
        raise RuntimeError("429 rate limited")

    monkeypatch.setattr(llm_client, "_build", fake_build)
    with pytest.raises(llm_client.AllProvidersFailed):
        llm_client.complete([{"role": "user", "content": "{}"}], _pool_settings())
    assert attempts == ["primary", "backup-1", "backup-2"]


def test_no_key_configured_raises_rather_than_calling_out() -> None:
    with pytest.raises(llm_client.AllProvidersFailed):
        llm_client.complete([{"role": "user", "content": "{}"}], _bare_settings())


def test_an_injected_client_short_circuits_the_pool() -> None:
    text, label = llm_client.complete([], _pool_settings(), client=_Client("from the stub"))
    assert text == "from the stub"
    assert label == "injected"


def test_the_verbalizer_falls_back_to_a_template_when_every_key_fails(monkeypatch) -> None:
    """The end-to-end guarantee: three dead keys still produce a safe answer."""

    def fake_build(_provider, _timeout):
        raise RuntimeError("boom")

    monkeypatch.setattr(llm_client, "_build", fake_build)
    outcome = genai_explain.verbalize(
        "fees", {"fees": {"fee_paid_bdt": 323.75}}, settings=_pool_settings()
    )
    assert outcome.source == "template"
    assert outcome.fallback_reason is not None
    parts = [outcome.answer_bn, outcome.answer_en, *outcome.bullets_bn, *outcome.bullets_en]
    assert guardrails.screen_all(parts).clean is True


# ---------------------------------------------------------------------------
# use 3: intent understanding
# ---------------------------------------------------------------------------
INTENT_REPLY = {"intent": "savings_plan", "confidence": 0.9, "goal_bdt": 30000.0, "months": 6}


def test_the_classifier_uses_the_llm_when_one_answers() -> None:
    outcome = genai_intent.understand(
        "৬ মাসে ৩০ হাজার জমাতে চাই", settings=_pool_settings(),
        client=_Client(json.dumps(INTENT_REPLY)),
    )
    assert outcome.intent == "savings_plan"
    assert outcome.source == "llm"


def test_the_user_transcript_travels_as_inert_data_only() -> None:
    """The whole prompt is a fixed system prompt plus one JSON document."""
    messages = prompts.build_intent_messages("৬ মাসে ৩০ হাজার জমাতে চাই")
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    payload = json.loads(messages[1]["content"])
    assert payload["user_text_untrusted"]
    # the transcript is not concatenated into the system prompt
    assert "জমাতে" not in messages[0]["content"]


def test_every_intent_the_prompt_offers_is_on_the_real_whitelist() -> None:
    payload = json.loads(prompts.build_intent_messages("hello")[1]["content"])
    assert set(payload["allowed_intents"]) == set(guardrails.ALLOWED_INTENTS)


def test_a_classifier_that_invents_an_intent_is_rejected() -> None:
    """A model cannot widen the whitelist; Python has the last word."""
    outcome = genai_intent.understand(
        "wire me some cash", settings=_pool_settings(),
        client=_Client(json.dumps({"intent": "wire_transfer", "confidence": 1.0})),
    )
    assert outcome.intent in guardrails.ALLOWED_INTENTS
    assert outcome.source == "rules"


def test_the_model_cannot_invent_a_goal_the_user_never_typed() -> None:
    """Parameters are re-read from the text, not taken from the model."""
    outcome = genai_intent.understand(
        "please explain my spending", settings=_pool_settings(),
        client=_Client(json.dumps(INTENT_REPLY)),
    )
    # the text named no goal, so the solver must not be handed one
    assert outcome.goal.goal_bdt is None
    assert outcome.goal.months is None


def test_a_goal_is_read_from_the_bangla_text_even_if_the_model_disagrees() -> None:
    outcome = genai_intent.understand(
        "৬ মাসে ৳৩০,০০০ জমাতে চাই", settings=_pool_settings(),
        client=_Client(json.dumps({**INTENT_REPLY, "goal_bdt": 3.0, "months": 400})),
    )
    assert outcome.goal.goal_bdt == 30000.0
    assert outcome.goal.months == 6


def test_a_bad_json_reply_falls_back_to_the_keyword_classifier() -> None:
    outcome = genai_intent.understand(
        "what are the fees?", settings=_pool_settings(), client=_Client("not json")
    )
    assert outcome.intent == "fees"
    assert outcome.source == "rules"
    assert outcome.fallback_reason == "bad_json"


def test_a_classifier_error_falls_back_to_the_keyword_classifier() -> None:
    outcome = genai_intent.understand(
        "what are the fees?", settings=_pool_settings(), client=_Client(RuntimeError("boom"))
    )
    assert outcome.intent == "fees"
    assert outcome.source == "rules"


# ---------------------------------------------------------------------------
# the three new intents (uses 1, 2 and 6)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("intent", ["health_coach", "anomalies", "tradeoffs"])
def test_a_new_intent_has_a_prompt_instruction(intent: str) -> None:
    assert prompts.intent_instruction(intent)


@pytest.mark.parametrize("intent", ["health_coach", "anomalies", "tradeoffs"])
@pytest.mark.parametrize("language", ["bn", "en"])
def test_a_new_intent_has_a_safe_template(intent: str, language: str) -> None:
    answer = fallback.render(intent, {}, language)
    assert answer.answer.strip()
    assert guardrails.screen_all(answer.parts()).clean is True


@pytest.mark.parametrize("intent", ["health_coach", "anomalies", "tradeoffs"])
def test_a_new_intent_builds_a_context_or_an_empty_one(intent: str, small_db) -> None:
    """Never a 500: an unknown user or a missing artifact is an absent section."""
    context = explain_service.build_context(
        DEMO_USER, intent, db_path=small_db, goal_bdt=30000.0, months=6
    )
    assert isinstance(context, dict)


def test_the_health_coach_context_carries_the_three_habit_metrics(small_db) -> None:
    context = explain_service.health_context(DEMO_USER, db_path=small_db)
    if not context:
        pytest.skip("demo user absent from this fixture")
    assert set(context["habits"]) >= {"cash_dependency_pct", "fee_burden_pct"}
    assert context["is_not_a_credit_score"] is True
    assert context["band"] in {"Fragile", "Building", "Steady", "Strong"}


def test_the_health_coach_template_never_says_it_is_a_credit_score() -> None:
    for language in ("bn", "en"):
        joined = " ".join(fallback.render("health_coach", {}, language).parts()).lower()
        assert "credit score" not in joined
        assert "ক্রেডিট স্কোর" not in joined


def test_the_anomaly_template_says_unusual_not_fraud(small_db) -> None:
    """It may say fraud is NOT indicated; it may never accuse the user."""
    context = explain_service.anomalies_context(DEMO_USER, db_path=small_db)
    answer = fallback.render("anomalies", {"anomalies": context} if context else {}, "en")
    joined = " ".join(answer.parts()).lower()
    assert "is fraud" not in joined
    assert "you were" not in joined and "your account was" not in joined


# ---------------------------------------------------------------------------
# use 4: the transaction story is measured, not generated
# ---------------------------------------------------------------------------
def test_the_transaction_context_reports_a_measured_cashout_pattern(small_db) -> None:
    context = explain_service.transactions_context(small_db, DEMO_USER)
    if not context:
        pytest.skip("demo user absent from this fixture")
    assert "cash_out_count" in context["pattern"]
    assert 0.0 <= context["pattern"]["month_end_cash_out_share_pct"] <= 100.0


def test_the_pattern_share_is_the_real_measured_fraction(small_db) -> None:
    import pandas as pd

    frame = explain_service._recent_transactions(small_db, DEMO_USER)
    spent = frame.loc[~frame["type"].eq("income")]
    cash = spent.loc[spent["channel"].eq("cash_out")]
    pattern = explain_service._cashout_pattern(spent, cash)
    if cash.empty:
        assert pattern["cash_out_count"] == 0
        return
    days = pd.to_datetime(cash["timestamp"]).dt.day
    assert pattern["month_end_cash_out_share_pct"] == pytest.approx(
        (days >= 21).sum() / len(cash) * 100, abs=0.05
    )


def test_the_transactions_template_stories_only_a_real_share() -> None:
    """A 0% month-end share must not be phrased as 'most of your cash-outs'."""
    context = {
        "transactions": {
            "count": 4, "inflow_bdt": 1000.0, "outflow_bdt": 400.0, "fee_bdt": 8.0,
            "shortfall_events": 0,
            "pattern": {
                "cash_out_count": 2, "month_end_cash_out_share_pct": 0.0, "peak_weekday": None,
            },
        }
    }
    answer = fallback.render("explain_transactions", context, "en")
    assert "last third" not in answer.answer
    assert "2 times" in answer.answer


# ---------------------------------------------------------------------------
# use 5: tip phrasing may only rephrase
# ---------------------------------------------------------------------------
TIP = {
    "id": "cash_out_to_transfer", "title": "Send by app", "title_bn": "অ্যাপে পাঠান",
    "body": "Cash-out is the most expensive channel.", "body_bn": "ক্যাশ-আউট সবচেয়ে দামি।",
    "trigger": "cash_out_count_per_month >= 3 (observed 5)",
}


def test_a_clean_rephrase_is_used() -> None:
    reply = json.dumps(
        {"body_bn": "আপনি ৫ বার ক্যাশ নিয়েছেন, অ্যাপে পাঠালে ফি কমে।",
         "body_en": "You took cash 5 times; sending by app costs less.",
         "why_bn": "কারণ আপনার ৫ বার ক্যাশ-আউট হয়েছে।"},
        ensure_ascii=False,
    )
    out = rag.phrase_tip(TIP, {"cash_out_count": 5}, settings=_pool_settings(), client=_Client(reply))
    assert out["phrased_by"].startswith("llm:")
    assert out["body_bn"] != TIP["body_bn"]
    # the id is copied from the bank, never taken from the model
    assert out["id"] == TIP["id"]


def test_a_rephrase_that_invents_a_number_falls_back() -> None:
    reply = json.dumps({"body_bn": "আপনি ৯৯৯৯ টাকা বাঁচাবেন।", "body_en": "Save 9999.", "why_bn": ""})
    out = rag.phrase_tip(TIP, {"cash_out_count": 5}, settings=_pool_settings(), client=_Client(reply))
    assert out["phrased_by"] == "template"
    assert out["body_bn"] == TIP["body_bn"]


def test_a_rephrase_with_a_loan_offer_falls_back() -> None:
    reply = json.dumps(
        {"body_bn": "ঋণ নিয়ে ৫০,০০০ নিন।", "body_en": "Take a loan of 50,000 now.", "why_bn": ""}
    )
    out = rag.phrase_tip(TIP, {}, settings=_pool_settings(), client=_Client(reply))
    assert out["phrased_by"] == "template"
    assert guardrails.screen_all([out["body_bn"], out["body_en"]]).clean is True


def test_a_malformed_rephrase_falls_back() -> None:
    out = rag.phrase_tip(TIP, {}, settings=_pool_settings(), client=_Client("not json"))
    assert out["phrased_by"] == "template"


def test_a_rephrase_cannot_add_a_field() -> None:
    reply = json.dumps({"body_bn": "ক", "body_en": "e", "why_bn": "w", "product": "a loan"})
    out = rag.phrase_tip(TIP, {}, settings=_pool_settings(), client=_Client(reply))
    assert out["phrased_by"] == "template"


def test_phrasing_is_skipped_entirely_with_no_key() -> None:
    out = rag.phrase_tip(TIP, {}, settings=_bare_settings())
    assert out["phrased_by"] == "template"
    assert out["body_bn"] == TIP["body_bn"]


def test_the_tip_prompt_carries_the_tip_whole_and_adds_no_advice() -> None:
    payload = json.loads(prompts.build_tip_messages(TIP, {"cash_out_count": 5})[1]["content"])
    assert payload["tip"]["id"] == TIP["id"]
    assert payload["user_facts"] == {"cash_out_count": 5}
    assert payload["rules"]["may_not_add_new_advice"] is True


