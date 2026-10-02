"""LLM verbalizer: structured JSON in, guarded structured JSON out.

The contract with the model, enforced here rather than trusted:

1. The model only ever sees ``prompts.build_messages`` — a system prompt and a
   JSON document of numbers our own services computed. User text travels as an
   inert ``user_text_untrusted`` string.
2. The reply is parsed into :class:`Verbalization` (a strict pydantic model), so
   a missing field or an unexpected key is a failure, not a shrug.
3. The reply is screened by ``rules.guardrails`` (the banned-output filter).
4. Every number in the reply must be grounded in the context
   (``guardrails.ungrounded_numbers``).
5. If *any* of 2-4 fails, or the API errors, times out or is not configured, the
   answer is the deterministic template from :mod:`backend.genai.fallback`.

So the LLM can improve the wording and can never change a number, make an
offer, or break the demo.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.rules import guardrails

from . import fallback, prompts

logger = logging.getLogger("shonchoy.explain")

#: Never ask for more than this; the reply is a screen or two of text.
MAX_BULLETS = 5


class Verbalization(BaseModel):
    """The exact shape the model must return.

    ``extra="forbid"`` matters: a model that adds a ``disclaimer`` or
    ``recommended_product`` field is trying to widen its own remit, and the
    strict model turns that into a fallback instead of a silently accepted key.
    """

    model_config = ConfigDict(extra="forbid")

    answer_bn: str
    answer_en: str
    bullets_bn: list[str] = field(default_factory=list)
    bullets_en: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExplainOutcome:
    """Everything the endpoint needs, in both languages, plus why."""

    intent: str
    answer_bn: str
    answer_en: str
    bullets_bn: list[str]
    bullets_en: list[str]
    source: str  # "template" | "llm"
    blocked: bool = False
    #: Why the template was used instead of the model — for logs and for the
    #: "why does this sound robotic?" question. Never contains user text.
    fallback_reason: Optional[str] = None

    @property
    def used_llm(self) -> bool:
        return self.source == "llm"


def _template_outcome(intent: str, context: Mapping[str, Any] | None, reason: str) -> ExplainOutcome:
    """Both languages from the template layer, tagged ``template``."""
    answers = fallback.both_languages(intent, context)
    bn, en = answers["bn"], answers["en"]
    return ExplainOutcome(
        intent=intent,
        answer_bn=bn.answer,
        answer_en=en.answer,
        bullets_bn=list(bn.bullets),
        bullets_en=list(en.bullets),
        source="template",
        fallback_reason=reason,
    )


def _clean(values: Sequence[str]) -> list[str]:
    """Trim, drop empties and cap the bullet count."""
    return [str(item).strip() for item in values if str(item).strip()][:MAX_BULLETS]


def parse_reply(raw: str) -> Verbalization:
    """Parse a model reply into a normalised :class:`Verbalization`.

    Tolerates a fenced code block (some providers wrap JSON anyway) but nothing
    else: prose around the object is a parse failure, so the template is used.
    """
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        _, _, text = text.partition("\n")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("model reply was not a JSON object")
    reply = Verbalization.model_validate(payload)
    return Verbalization(
        answer_bn=reply.answer_bn.strip(),
        answer_en=reply.answer_en.strip(),
        bullets_bn=_clean(reply.bullets_bn),
        bullets_en=_clean(reply.bullets_en),
    )


def is_acceptable(reply: Verbalization, context: Mapping[str, Any] | None) -> tuple[bool, str]:
    """Run both post-filters over a parsed reply; returns ``(ok, reason)``.

    The reason strings are stable and contain no user text, so they are safe to
    log and to show as a "template used instead" hint.
    """
    parts = [reply.answer_bn, reply.answer_en, *reply.bullets_bn, *reply.bullets_en]
    screen = guardrails.screen_all(parts)
    if not screen.clean:
        return False, f"banned:{','.join(screen.categories)}"
    stray: list[str] = []
    for part in parts:
        stray.extend(guardrails.ungrounded_numbers(part, context or {}))
    if stray:
        return False, f"ungrounded_numbers:{','.join(sorted(set(stray))[:5])}"
    return True, "ok"


def _client(settings: Any) -> Any:
    """Build an OpenAI-compatible client, or ``None`` when not configured."""
    if settings is None or not getattr(settings, "llm_enabled", False):
        return None
    try:
        from openai import OpenAI  # noqa: PLC0415 - optional dependency
    except Exception:  # pragma: no cover - openai not installed
        logger.info("openai package missing; using the template fallback")
        return None
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=1,
    )


def _ask_model(
    client: Any,
    settings: Any,
    intent: str,
    context: Mapping[str, Any] | None,
    language: str,
    user_text: str | None,
) -> str:
    """One chat completion, returning the raw assistant text."""
    completion = client.chat.completions.create(
        model=getattr(settings, "llm_model", "gpt-4o-mini"),
        messages=prompts.build_messages(intent, context, language, user_text),
        **prompts.request_kwargs(),
    )
    return completion.choices[0].message.content or ""


def verbalize(
    intent: str,
    context: Mapping[str, Any] | None,
    language: str = "bn",
    user_text: str | None = None,
    settings: Any = None,
    client: Any = None,
) -> ExplainOutcome:
    """Explain ``context`` in both languages, using the LLM only when it is safe.

    ``client`` exists so the tests can inject a stub with no key and no network.
    Any failure — off-intent, no key, API error, bad JSON, banned content,
    invented number — returns the template with ``source="template"``.
    """
    if not guardrails.is_allowed_intent(intent):
        return refusal_outcome(language)

    template = _template_outcome(intent, context, "not_attempted")
    active = client if client is not None else _client(settings)
    if active is None:
        return template

    try:
        raw = _ask_model(active, settings, intent, context, language, user_text)
    except Exception as exc:  # network, auth, timeout, provider error
        logger.warning("llm call failed, using templates: %s", type(exc).__name__)
        return _template_outcome(intent, context, f"llm_error:{type(exc).__name__}")

    try:
        reply = parse_reply(raw)
    except (ValueError, ValidationError) as exc:
        logger.warning("llm reply rejected (%s); using templates", type(exc).__name__)
        return _template_outcome(intent, context, "bad_json")

    ok, reason = is_acceptable(reply, context)
    if not ok:
        # Not trusted even though it was reachable: nothing it wrote is shown.
        logger.warning("llm reply failed the guardrails (%s); using templates", reason)
        return ExplainOutcome(
            intent=template.intent,
            answer_bn=template.answer_bn,
            answer_en=template.answer_en,
            bullets_bn=template.bullets_bn,
            bullets_en=template.bullets_en,
            source="template",
            blocked=reason.startswith("banned:"),
            fallback_reason=reason,
        )

    return ExplainOutcome(
        intent=intent,
        answer_bn=reply.answer_bn,
        answer_en=reply.answer_en,
        bullets_bn=reply.bullets_bn,
        bullets_en=reply.bullets_en,
        source="llm",
        blocked=False,
        fallback_reason=None,
    )


def refusal_outcome(language: str = "bn") -> ExplainOutcome:
    """The safe answer for a request that is off-intent or injection-shaped."""
    bn = fallback.render("unknown", {}, "bn")
    en = fallback.render("unknown", {}, "en")
    prefer_bn = str(language).lower().startswith("bn")
    return ExplainOutcome(
        intent="unknown",
        answer_bn=bn.answer,
        answer_en=en.answer,
        bullets_bn=list(bn.bullets if prefer_bn else en.bullets),
        bullets_en=list(en.bullets),
        source="template",
        blocked=False,
        fallback_reason="off_intent",
    )

