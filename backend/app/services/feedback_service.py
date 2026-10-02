"""Feedback store (Phase 8): the "was this helpful?" loop, without PII.

The plan's feedback loop closes INPUT -> ACTION -> outcome: a user taps
"was this helpful?" and that tap is recorded so the metrics page can report how
often an answer landed. Two design choices make that safe:

* **No PII is written.** The user id is replaced by a salted SHA-256 hash (a
  *respondent* token), and any free-text comment is deliberately dropped — only
  the fact that a comment was offered is stored. What lands on disk is a small
  JSON object with a surface, a boolean and a coarse timestamp.
* **The store is the metrics store.** Records are appended as JSONL to the same
  artifacts directory that holds ``metrics.json``, so ``GET /metrics`` can read
  the aggregate without a second datastore, and the offline evaluation can see
  the same file.

Pure file I/O with no database and no model. A missing or corrupt store reads as
"no responses yet" rather than raising, so a broken line can never take the
metrics page down.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("shonchoy.feedback")

#: The fields that are actually persisted. Kept explicit so a reader can see at
#: a glance that no user id and no free text are on the list.
STORED_FIELDS: tuple[str, ...] = (
    "recorded_at",
    "respondent",
    "surface",
    "intent",
    "helpful",
    "has_comment",
)

DEFAULT_CONTEXT_WINDOW_MINUTES = 1


def respondent_token(user_id: str, salt: str) -> str:
    """A stable, salted hash of the user id — never the id itself."""
    digest = hashlib.sha256(f"{salt}:{user_id}".encode("utf-8")).hexdigest()
    return digest[:12]


def default_store_path() -> Path:
    """Where feedback lands by default: beside ``metrics.json``."""
    return Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "feedback.jsonl"


def record(
    user_id: str,
    surface: str,
    helpful: bool,
    *,
    intent: Optional[str] = None,
    comment: Optional[str] = None,
    salt: str = "shonchoy-feedback-v1",
    path: str | Path | None = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Append one anonymised feedback record and return the stored payload.

    Raises ``OSError`` only when the append itself fails, so the router can turn
    a full disk into a 503 instead of pretending the tap was saved.
    """
    target = Path(path) if path is not None else default_store_path()
    stamped = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    # Minute granularity: enough to see a trend, not a precise fingerprint.
    stamped = stamped.replace(second=0, microsecond=0)
    record_obj = {
        "recorded_at": stamped.isoformat(),
        "respondent": respondent_token(user_id, salt),
        "surface": str(surface)[:40],
        "intent": (str(intent)[:40] if intent else None),
        "helpful": bool(helpful),
        "has_comment": bool(comment and comment.strip()),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record_obj, ensure_ascii=False) + "\n")
    logger.info("feedback recorded: surface=%s helpful=%s", record_obj["surface"], record_obj["helpful"])
    return record_obj


def read_records(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Every stored record, skipping blank/corrupt lines instead of raising."""
    target = Path(path) if path is not None else default_store_path()
    if not target.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - unreadable store
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _rate(helpful: int, total: int) -> float:
    return round(helpful / total * 100.0, 2) if total else 0.0


def summarise(path: str | Path | None = None) -> dict[str, Any]:
    """The ``FeedbackSummary`` aggregate for the metrics payload."""
    records = read_records(path)
    total = len(records)
    helpful = sum(1 for item in records if item.get("helpful"))

    buckets: dict[str, dict[str, int]] = {}
    for item in records:
        surface = str(item.get("surface") or "unknown")
        bucket = buckets.setdefault(surface, {"responses": 0, "helpful": 0})
        bucket["responses"] += 1
        if item.get("helpful"):
            bucket["helpful"] += 1

    by_surface: list[dict[str, Any]] = [
        {
            "surface": surface,
            "responses": data["responses"],
            "helpful": data["helpful"],
            "helpful_rate_pct": _rate(data["helpful"], data["responses"]),
        }
        for surface, data in sorted(
            buckets.items(), key=lambda pair: pair[1]["responses"], reverse=True
        )
    ]
    return {
        "responses": total,
        "helpful": int(helpful),
        "helpful_rate_pct": _rate(int(helpful), total),
        "by_surface": by_surface,
    }
