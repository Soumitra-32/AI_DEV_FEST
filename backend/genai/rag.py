"""Tip retrieval over the curated bank (Phase 7).

This is the "retrieval, then LLM phrasing" half of the plan's split: the tips come
from ``genai/tips.json``, so the model can only *choose and rephrase* what a
human wrote. It cannot invent a tip, a number or a promise.

Retrieval is deliberately boring and deterministic:

* every tip carries a ``trigger`` -- one measured feature, one comparison -- so
  selection is explainable and testable;
* a tip fires when the user's own row satisfies its trigger, and every returned
  tip reports the trigger that fired, because "why am I seeing this?" is the
  whole point;
* ranking is ``priority`` first, then how far past the threshold the user is, so
  the most urgent behaviour leads.

No network, no model, no database: only the JSON file and one feature row.

:func:`phrase_tip` is the deliberate exception, and it is a *phrasing* step, not a
retrieval step: retrieval stays deterministic and offline, and the model may only
rewrite a tip that was already chosen. Its output is checked against the same
guardrails as every other generated answer and falls back to the curated text.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.rules import guardrails

from . import client as llm_client
from . import prompts

logger = logging.getLogger("shonchoy.rag")

TIPS_FILE = Path(__file__).resolve().parent / "tips.json"

#: Comparison operators a trigger may use.
OPERATORS = (">=", "<=", ">", "<", "==")


def _compare(actual: float, op: str, expected: float) -> bool:
    if op == ">=":
        return actual >= expected
    if op == "<=":
        return actual <= expected
    if op == ">":
        return actual > expected
    if op == "<":
        return actual < expected
    return actual == expected


@lru_cache(maxsize=4)
def load_bank(path: str | Path = TIPS_FILE) -> tuple[Mapping[str, Any], ...]:
    """The curated tips, loaded once and cached.

    A missing or malformed bank returns an empty tuple rather than raising: a
    broken tips file must degrade to "no tips", never to a 500.
    """
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    tips = payload.get("tips") if isinstance(payload, Mapping) else None
    if not isinstance(tips, list):
        return ()
    return tuple(tip for tip in tips if isinstance(tip, Mapping) and tip.get("id"))


def _severity(actual: float, op: str, expected: float) -> float:
    """How far past the threshold the user is, in units of the threshold.

    Used only for ordering. A threshold of 0 has no scale, so severity falls
    back to the raw difference.
    """
    gap = abs(float(actual) - float(expected))
    return gap / abs(float(expected)) if expected else gap


def triggered(
    tip: Mapping[str, Any],
    features: Mapping[str, float],
) -> Optional[dict[str, Any]]:
    """Match one tip against one user's feature row.

    Returns the evidence when the trigger fires, else ``None``.
    """
    trigger = tip.get("trigger")
    if not isinstance(trigger, Mapping):
        return None
    name = trigger.get("feature")
    op = str(trigger.get("op", ">="))
    if not name or op not in OPERATORS or name not in features:
        return None
    actual = float(features.get(name, 0.0) or 0.0)
    expected = float(trigger.get("value", 0.0) or 0.0)
    if not _compare(actual, op, expected):
        return None
    return {
        "feature": name,
        "op": op,
        "observed": round(actual, 4),
        "threshold": expected,
        "severity": round(_severity(actual, op, expected), 4),
    }
def _as_tip(tip: Mapping[str, Any]) -> dict[str, Any]:
    """One tip in the shape the API and the explanation layer expect."""
    return {
        "id": str(tip["id"]),
        "title": str(tip.get("title_en", "")),
        "title_bn": str(tip.get("title_bn", "")),
        "body": str(tip.get("body_en", "")),
        "body_bn": str(tip.get("body_bn", "")),
        "priority": float(tip.get("priority", 0)),
    }


def retrieve(
    features: Mapping[str, float],
    limit: int = 3,
    intent: Optional[str] = None,
    bank: Optional[Sequence[Mapping[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """The tips this user's own numbers trigger, most important first.

    ``intent`` narrows the bank when the caller already knows the topic (a
    "fees" question should not be answered with a balance tip); ``None`` means
    "any tip that fires".
    """
    tips = bank if bank is not None else load_bank()
    scored: list[tuple[float, float, dict[str, Any]]] = []
    for tip in tips:
        if intent is not None and intent not in tuple(tip.get("intents", ())):
            continue
        evidence = triggered(tip, features)
        if evidence is None:
            continue
        payload = _as_tip(tip)
        payload["trigger"] = (
            f"{evidence['feature']} {evidence['op']} {evidence['threshold']} "
            f"(observed {evidence['observed']})"
        )
        scored.append((float(tip.get("priority", 0)), evidence["severity"], payload))

    scored.sort(key=lambda item: (-item[0], -item[1]))
    return [tip for _, _, tip in scored[: max(int(limit), 1)]]


def search(
    query: str,
    bank: Optional[Sequence[Mapping[str, Any]]] = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Keyword search over the bank, for a free-text question.

    Matching is on the tip id and both languages' title and body. It is
    substring matching on purpose: the alternative is an embedding model and a
    vector index, which is a lot of machinery for a bank of hand-written tips.
    """
    tips = bank if bank is not None else load_bank()
    needle = (query or "").strip().lower()
    if not needle:
        return []
    words = [word for word in needle.split() if word]
    hits: list[dict[str, Any]] = []
    for tip in tips:
        haystack = " ".join(
            str(tip.get(key, ""))
            for key in ("id", "title_en", "title_bn", "body_en", "body_bn")
        ).lower()
        if needle not in haystack and not any(word in haystack for word in words):
            continue
        payload = _as_tip(tip)
        trigger = tip.get("trigger")
        payload["trigger"] = str(trigger.get("feature", "")) if isinstance(trigger, Mapping) else ""
        hits.append(payload)
    hits.sort(key=lambda item: -item["priority"])
    return hits[: max(int(limit), 1)]


def bank_ids(bank: Optional[Iterable[Mapping[str, Any]]] = None) -> list[str]:
    """Every tip id in the bank (the tests assert nothing outside it is ever shown)."""
    tips = list(bank) if bank is not None else list(load_bank())
    return [str(tip["id"]) for tip in tips if tip.get("id")]


# ---------------------------------------------------------------------------
# use 5: the LLM phrasing half -- retrieval above, wording here
# ---------------------------------------------------------------------------
#: Everything needed to phrase one tip and to check what came back. The check
#: runs against the *original* tip and the user's own facts, which is what makes
#: "the model may only rephrase, never invent" mechanically true rather than a
#: request in a prompt.
PhraseContext = Mapping[str, Any]


class PhrasedTip(BaseModel):
    """The exact shape the phraser must return."""

    model_config = ConfigDict(extra="forbid")

    body_bn: str
    body_en: str
    why_bn: str = ""


def _parse(raw: str) -> PhrasedTip:
    """Parse the model's JSON, tolerating a fenced code block."""
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text[3:]
        text = text.removeprefix("json").strip()
    return PhrasedTip.model_validate(json.loads(text))


def _allowed_numbers(*sources: Any) -> set[str]:
    """Numbers the phraser is allowed to repeat: the tip's own plus the facts."""
    allowed: set[str] = set()
    for source in sources:
        collected = guardrails.numbers_in(json.dumps(source, ensure_ascii=False, default=str))
        allowed.update(str(value) for value in collected if value is not None)
    return allowed


def phrase_tip(
    tip: Mapping[str, Any],
    facts: PhraseContext,
    settings: Any = None,
    client: Any = None,
) -> dict[str, Any]:
    """Rewrite one already-retrieved tip in simple Bangla, for this user.

    The curated tip is returned **unchanged** unless the model's wording passes
    every check: it must parse into the strict shape, must survive the
    banned-output filter, and may only repeat numbers that were already in the
    tip or in the user's own facts. A failure of any of those returns the human
    wording with ``phrased_by="template"``, so the demo never shows a worse
    sentence than the one we shipped.

    The id is copied from the input and never taken from the model, so the
    "only these tips exist" guarantee survives the LLM call.
    """
    payload = {key: tip.get(key) for key in ("title_bn", "body_bn", "trigger")}
    base = {
        "id": str(tip.get("id", "")),
        "body_bn": str(tip.get("body_bn") or tip.get("body") or ""),
        "body_en": str(tip.get("body") or ""),
        "why_bn": str(tip.get("trigger") or ""),
        "phrased_by": "template",
    }
    if client is None and not llm_client.enabled(settings):
        return base
    try:
        raw, provider = llm_client.complete(
            prompts.build_tip_messages(tip, facts),
            settings=settings,
            request_kwargs=prompts.request_kwargs(temperature=0.3, max_tokens=400),
            client=client,
        )
    except Exception as exc:
        logger.warning("tip phrasing fell back to the curated text: %s", type(exc).__name__)
        return base

    try:
        reply = _parse(raw)
    except (ValueError, ValidationError) as exc:
        logger.warning("tip phrasing rejected: %s", type(exc).__name__)
        return base

    parts = [reply.body_bn, reply.body_en, reply.why_bn]
    if not guardrails.screen_all(parts).clean:
        logger.warning("tip phrasing tripped the banned-output filter; using the curated text")
        return base
    allowed = _allowed_numbers(payload, facts)
    for part in parts:
        stray = [
            value
            for value in guardrails.numbers_in(part)
            if value is not None and str(value) not in allowed
        ]
        if stray:
            logger.warning("tip phrasing invented %s; using the curated text", stray[:3])
            return base

    return {
        "id": str(tip.get("id", "")),
        "body_bn": reply.body_bn.strip(),
        "body_en": reply.body_en.strip(),
        "why_bn": reply.why_bn.strip(),
        "phrased_by": f"llm:{provider}",
    }