"""Chat-explain endpoint (Phase 4): the Inclusive Assistant's brain.

Thin by design, same shape as the other routers: auth -> rate limit -> classify
-> context -> verbalize -> frozen schema. Every interesting decision lives in a
module that can be tested without HTTP:

* ``rules.guardrails`` decides the intent and owns the banned-output filter;
* ``services.explain_service`` builds the structured context from the tested
  services (never from the request body);
* ``genai.explain`` runs the model, checks its output, and falls back to
  ``genai.fallback`` templates.

Security properties this router is responsible for:

* the ``user_id`` comes from the token, never from the body, so one user cannot
  ask about another's transactions;
* the client's ``intent`` hint is **ignored** — the server always re-classifies,
  because trusting a client-supplied intent is how a prompt-injection attempt
  would get to choose its own context;
* the message is length-bounded by the schema and rate-limited per token;
* nothing user-written is logged.
"""
from __future__ import annotations

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.genai import explain as genai_explain
from backend.genai import fallback
from backend.rules import guardrails

from ..config import Settings, get_settings
from ..deps import CurrentUser
from ..schemas import ExplainRequest, ExplainResponse, Provenance
from ..services import explain_service

router = APIRouter(tags=["chat-explain"])

#: Fixed-window rate limit per authenticated user. Generous enough for the
#: demo conversation, low enough that a stuck client cannot burn the API key.
RATE_LIMIT_REQUESTS = 20
RATE_LIMIT_WINDOW_SECONDS = 60.0

#: In-process counters: {user_id: (window_start, count)}. A single-worker demo
#: does not need Redis; a multi-worker deploy would move this to the edge.
_HITS: dict[str, tuple[float, int]] = {}


def _check_rate_limit(user_id: str) -> None:
    """Reject a caller sending far more than a conversation needs."""
    now = time.monotonic()
    start, count = _HITS.get(user_id, (0.0, 0))
    if now - start > RATE_LIMIT_WINDOW_SECONDS:
        start, count = now, 0
    count += 1
    _HITS[user_id] = (start, count)
    if count > RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many questions, please wait a moment",
        )


def _provenance(outcome: Any, intent: str) -> Provenance:
    """Prediction / Assumption / Explanation for the answer card itself."""
    if outcome.used_llm:
        prediction = "The wording came from the language model, the numbers from our models."
        assumption = "The model may only repeat figures that our rules and models computed."
        source = "llm"
    else:
        prediction = "A fixed template answered, using the same numbers."
        assumption = (
            "The template path runs when no API key is set, or when the model's "
            "answer failed a check."
        )
        source = "template"
    note = f" (note: {outcome.fallback_reason})" if outcome.fallback_reason else ""
    explanation = (
        f"Intent: {intent}. Every figure in this answer comes from the user's own "
        f"transaction history{note}."
    )
    return Provenance(
        prediction=prediction, assumption=assumption, explanation=explanation, source=source
    )


@router.post(
    "/chat-explain",
    response_model=ExplainResponse,
    summary="Explain my money in Bangla or English",
)
def chat_explain(
    body: ExplainRequest,
    user_id: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExplainResponse:
    """Answer one whitelisted question about the caller's own money."""
    _check_rate_limit(user_id)
    language = body.language

    # The server always re-classifies; ``body.intent`` is a UI hint only.
    intent = guardrails.classify_intent(body.message)

    if intent == "unknown":
        # Off-intent or injection-shaped: safe template, no context loaded and
        # no model call.
        outcome = genai_explain.refusal_outcome(language)
        return ExplainResponse(
            intent="unknown",
            answer_bn=outcome.answer_bn,
            answer_en=outcome.answer_en,
            bullets_bn=outcome.bullets_bn,
            bullets_en=outcome.bullets_en,
            source="template",
            blocked=False,
            provenance=_provenance(outcome, "unknown"),
        )

    goal_bdt: float | None = None
    months: int | None = None
    if intent == "savings_plan":
        goal = fallback.parse_goal(body.message)
        if not goal.is_complete:
            # Ask for the missing half instead of inventing a horizon: the
            # solver must never run on a guessed number.
            bn = fallback.missing_goal_prompt(goal, "bn")
            en = fallback.missing_goal_prompt(goal, "en")
            return ExplainResponse(
                intent="savings_plan",
                answer_bn=bn.answer,
                answer_en=en.answer,
                bullets_bn=list(bn.bullets),
                bullets_en=list(en.bullets),
                source="template",
                blocked=False,
                provenance=Provenance(
                    prediction="I need one more detail before solving the plan.",
                    assumption="A goal amount and a horizon, both read from your message.",
                    explanation="The solver never runs on a guessed number.",
                    source="rule",
                ),
            )
        goal_bdt, months = goal.goal_bdt, goal.months

    context = explain_service.build_context(
        user_id,
        intent,
        db_path=settings.db_path,
        goal_bdt=goal_bdt,
        months=months,
        language=language,
    )
    outcome = genai_explain.verbalize(
        intent,
        context,
        language=language,
        user_text=body.message,
        settings=settings,
    )
    return ExplainResponse(
        intent=intent,  # type: ignore[arg-type]  # narrowed by the whitelist above
        answer_bn=outcome.answer_bn,
        answer_en=outcome.answer_en,
        bullets_bn=outcome.bullets_bn,
        bullets_en=outcome.bullets_en,
        source=outcome.source,  # type: ignore[arg-type]  # "template" | "llm"
        blocked=outcome.blocked,
        provenance=_provenance(outcome, intent),
    )

