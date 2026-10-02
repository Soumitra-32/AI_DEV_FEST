"""Intent understanding (use 3): user text or voice transcript -> one whitelisted
intent plus validated parameters.

This is the one place where the model is allowed to look at what the user
*actually said*. It is still tightly fenced:

* the output is a strict JSON object (:class:`IntentDecision`) with
  ``extra="forbid"``, so a model that returns an action nobody whitelisted is a
  parse failure rather than a new capability;
* the intent is checked against :data:`backend.rules.guardrails.ALLOWED_INTENTS`
  in Python before it is used -- the prompt asking for a whitelist is a
  convenience, not the control;
* the parameters are **validated in Python afterwards**, never trusted from the
  model: the goal amount and horizon are re-parsed out of the raw text by
  :func:`backend.genai.fallback.parse_goal`, and that reading wins. A model cannot
  talk the solver into a ৳3 goal or a 400-month horizon;
* prompt-injection-shaped text never reaches the model at all -- it is screened
  first and answered with the off-intent template.

``understand`` therefore always returns a usable decision: the LLM answer when it
is usable, otherwise the existing keyword classifier. The demo cannot tell the
difference, which is the point.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.rules import guardrails

from . import client as llm_client
from . import prompts
from .fallback import GoalRequest, parse_goal

logger = logging.getLogger("shonchoy.intent")

#: Nothing user-written is longer than this before it is classified.
MAX_INPUT_CHARS = 500


class IntentDecision(BaseModel):
    """The exact shape the classifier must return."""

    model_config = ConfigDict(extra="forbid")

    intent: str
    confidence: float = 0.0
    goal_bdt: Optional[float] = None
    months: Optional[int] = None


@dataclass(frozen=True)
class IntentOutcome:
    """The classified intent, its parameters, and where they came from."""

    intent: str
    goal: GoalRequest
    source: str  # "llm" | "rules"
    fallback_reason: Optional[str] = None

    @property
    def used_llm(self) -> bool:
        return self.source == "llm"


def _parse(raw: str) -> IntentDecision:
    """Parse the model's JSON into a decision, tolerating a fenced block."""
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text[3:]
        text = text.removeprefix("json").strip()
    return IntentDecision.model_validate(json.loads(text))


def _validated_params(message: str) -> GoalRequest:
    """The goal as Python read it from the text, not as the model reported it.

    The regex reading is authoritative: it is the same code path the template
    fallback uses, it is unit-tested, and it cannot be talked into a number the
    user never typed. When the model supplied a goal but the text does not
    contain one, we keep ``None`` and let the caller ask a follow-up question.
    """
    return parse_goal(message)


def _rules_outcome(message: str, reason: str) -> IntentOutcome:
    """The keyword classifier -- always available, never fails."""
    intent = guardrails.classify_intent(message)
    return IntentOutcome(
        intent=intent, goal=parse_goal(message), source="rules", fallback_reason=reason
    )


def understand(
    message: str,
    settings: Any = None,
    language: str = "bn",
    client: Any = None,
) -> IntentOutcome:
    """Classify ``message`` into a whitelisted intent with validated parameters.

    Falls back to the keyword classifier when the LLM is off, unreachable, or
    returns anything unusable, so this function never raises for a caller.
    """
    text = str(message or "").strip()[:MAX_INPUT_CHARS]
    if not text or guardrails.looks_like_injection(text):
        # Nothing to classify, or an injection attempt: off-intent template, no
        # context loaded and no model call.
        return IntentOutcome(
            intent="unknown", goal=GoalRequest(), source="rules", fallback_reason="off_intent"
        )

    if client is None and not llm_client.enabled(settings):
        return _rules_outcome(text, "no_llm")

    try:
        raw, provider = llm_client.complete(
            prompts.build_intent_messages(text, language),
            settings=settings,
            request_kwargs=prompts.request_kwargs(temperature=0.0, max_tokens=120),
            client=client,
        )
    except Exception as exc:
        logger.warning("intent classification fell back to rules: %s", type(exc).__name__)
        return _rules_outcome(text, "llm_error")

    try:
        decision = _parse(raw)
    except (ValueError, ValidationError) as exc:
        logger.warning("intent reply rejected: %s", type(exc).__name__)
        return _rules_outcome(text, "bad_json")

    if not guardrails.is_allowed_intent(decision.intent):
        # The model invented an action. Drop it and use the rules.
        return _rules_outcome(text, "off_whitelist")

    goal = _validated_params(text)
    return IntentOutcome(
        intent=decision.intent,
        goal=goal,
        source="llm",
        fallback_reason=f"intent_llm:{provider}",
    )
