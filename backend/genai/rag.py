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
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

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