"""Feedback and customer-impact event store: measurable outcomes without PII.

The feedback loop closes INPUT -> ACTION -> outcome:
1. Users view features, receive recommendations, and act on them (events).
2. Users provide feedback ("was this useful?", ratings, understanding).
3. The metrics surface reports true customer impact aggregated strictly from
   persisted records with zero fabrication and explicit handling for zero-data states.

Security & privacy:
* No PII or raw transaction content is persisted.
* User IDs are anonymised via salted SHA-256 respondent tokens.
* Free text is discarded; only boolean indicators and safe category tokens are saved.
* Storage is append-only JSONL files beside ``metrics.json`` in the artifacts directory.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("shonchoy.feedback")

#: The fields that are persisted for feedback records.
STORED_FIELDS: tuple[str, ...] = (
    "recorded_at",
    "respondent",
    "surface",
    "feature",
    "helpful",
    "understood",
    "acted_on",
    "rating",
    "intent",
    "recommendation_id",
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


def default_events_path() -> Path:
    """Where product telemetry events land by default: beside ``feedback.jsonl``."""
    return Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "events.jsonl"


def record(
    user_id: str,
    surface: str,
    helpful: bool,
    *,
    feature: Optional[str] = None,
    understood: Optional[bool] = None,
    acted_on: Optional[bool] = None,
    rating: Optional[int] = None,
    intent: Optional[str] = None,
    recommendation_id: Optional[str] = None,
    comment: Optional[str] = None,
    salt: str = "shonchoy-feedback-v1",
    path: str | Path | None = None,
    events_path: str | Path | None = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Append one anonymised feedback record and return the stored payload.

    Also records a corresponding product event to link telemetry.
    Raises ``OSError`` only when the append itself fails.
    """
    target = Path(path) if path is not None else default_store_path()
    stamped = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    # Minute granularity: enough to see a trend, not a precise fingerprint.
    stamped = stamped.replace(second=0, microsecond=0)

    resolved_surface = str(surface or feature or "unknown")[:50]
    resolved_feature = str(feature or surface or "unknown")[:50]

    record_obj = {
        "recorded_at": stamped.isoformat(),
        "respondent": respondent_token(user_id, salt),
        "surface": resolved_surface,
        "feature": resolved_feature,
        "helpful": bool(helpful),
        "understood": (bool(understood) if understood is not None else None),
        "acted_on": (bool(acted_on) if acted_on is not None else None),
        "rating": (int(rating) if rating is not None else None),
        "intent": (str(intent)[:50] if intent else None),
        "recommendation_id": (str(recommendation_id)[:100] if recommendation_id else None),
        "has_comment": bool(comment and comment.strip()),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record_obj, ensure_ascii=False) + "\n")

    logger.info(
        "feedback recorded: surface=%s helpful=%s respondent=%s",
        record_obj["surface"],
        record_obj["helpful"],
        record_obj["respondent"],
    )

    # Automatically record structured telemetry event
    try:
        record_event(
            user_id,
            event_type="recommendation_feedback" if recommendation_id else "feedback_submitted",
            feature=resolved_feature,
            recommendation_id=recommendation_id,
            properties={
                "surface": resolved_surface,
                "helpful": record_obj["helpful"],
                "understood": record_obj["understood"],
                "acted_on": record_obj["acted_on"],
                "rating": record_obj["rating"],
            },
            salt=salt,
            path=events_path,
            now=stamped,
        )
    except Exception as exc:
        logger.warning("could not record companion event for feedback: %s", exc)

    return record_obj


def record_event(
    user_id: str,
    event_type: str,
    *,
    feature: Optional[str] = None,
    recommendation_id: Optional[str] = None,
    properties: Optional[dict[str, Any]] = None,
    salt: str = "shonchoy-feedback-v1",
    path: str | Path | None = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Append one structured product telemetry event and return the stored payload.

    Sanitizes properties to prevent logging raw transaction details or PII.
    """
    target = Path(path) if path is not None else default_events_path()
    stamped = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stamped = stamped.replace(second=0, microsecond=0)

    # Sanitize properties: strip any keys that look like transaction PII
    sanitized: dict[str, Any] = {}
    if properties and isinstance(properties, dict):
        for k, v in properties.items():
            k_clean = str(k)[:50]
            if any(term in k_clean.lower() for term in ("account", "pin", "password", "token", "phone")):
                continue
            if isinstance(v, (bool, int, float)):
                sanitized[k_clean] = v
            elif isinstance(v, str):
                sanitized[k_clean] = v[:100]

    record_obj = {
        "recorded_at": stamped.isoformat(),
        "respondent": respondent_token(user_id, salt),
        "event_type": str(event_type)[:50],
        "feature": (str(feature)[:50] if feature else None),
        "recommendation_id": (str(recommendation_id)[:100] if recommendation_id else None),
        "properties": sanitized,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record_obj, ensure_ascii=False) + "\n")

    logger.info(
        "event recorded: type=%s feature=%s respondent=%s",
        record_obj["event_type"],
        record_obj["feature"],
        record_obj["respondent"],
    )
    return record_obj


def read_records(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Every stored feedback record, skipping blank/corrupt lines instead of raising."""
    target = Path(path) if path is not None else default_store_path()
    if not target.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
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


def read_events(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Every stored telemetry event, skipping blank/corrupt lines instead of raising."""
    target = Path(path) if path is not None else default_events_path()
    if not target.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
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
            events.append(payload)
    return events


def _rate(helpful: int, total: int) -> float:
    return round(helpful / total * 100.0, 2) if total else 0.0


def summarise(path: str | Path | None = None) -> dict[str, Any]:
    """The legacy ``FeedbackSummary`` aggregate for the metrics payload."""
    records = read_records(path)
    total = len(records)
    helpful = sum(1 for item in records if item.get("helpful") is True)

    buckets: dict[str, dict[str, int]] = {}
    for item in records:
        surface = str(item.get("surface") or item.get("feature") or "unknown")
        bucket = buckets.setdefault(surface, {"responses": 0, "helpful": 0})
        bucket["responses"] += 1
        if item.get("helpful") is True:
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


def compute_customer_impact(
    events_path: str | Path | None = None,
    feedback_path: str | Path | None = None,
) -> dict[str, Any]:
    """Calculate customer-impact metrics from stored events and feedback.

    Handles zero/empty datasets safely with correct denominators.
    Zero fabrication: all values are calculated from real stored lines.
    """
    feedback_records = read_records(feedback_path)
    event_records = read_events(events_path)

    total_feedback = len(feedback_records)
    helpful_responses = sum(1 for item in feedback_records if item.get("helpful") is True)
    helpful_status_count = sum(1 for item in feedback_records if item.get("helpful") is not None)
    helpful_rate = (
        round(helpful_responses / helpful_status_count * 100.0, 1)
        if helpful_status_count > 0
        else None
    )

    understood_responses = sum(1 for item in feedback_records if item.get("understood") is True)
    understood_status_count = sum(1 for item in feedback_records if item.get("understood") is not None)
    understanding_rate = (
        round(understood_responses / understood_status_count * 100.0, 1)
        if understood_status_count > 0
        else None
    )

    event_counts: dict[str, int] = {}
    for ev in event_records:
        etype = ev.get("event_type")
        if etype:
            event_counts[etype] = event_counts.get(etype, 0) + 1

    recommendations_shown = event_counts.get("recommendation_shown", 0)
    recommendations_accepted = event_counts.get("recommendation_accepted", 0)
    recommendations_rejected = event_counts.get("recommendation_rejected", 0)
    actions_completed = event_counts.get("recommendation_action_completed", 0)
    savings_plans_created = event_counts.get("savings_plan_created", 0)
    savings_plans_viewed = event_counts.get("savings_plan_viewed", 0)
    forecast_views = event_counts.get("forecast_viewed", 0)
    anomaly_views = event_counts.get("anomaly_viewed", 0)
    copilot_usage = event_counts.get("copilot_used", 0)

    recommendation_acceptance_rate = (
        round(recommendations_accepted / recommendations_shown * 100.0, 1)
        if recommendations_shown > 0
        else None
    )

    action_completion_rate = (
        round(actions_completed / recommendations_accepted * 100.0, 1)
        if recommendations_accepted > 0
        else None
    )

    has_data = bool(total_feedback > 0 or len(event_records) > 0)
    message = (
        "Real customer interaction telemetry aggregated without fabrication"
        if has_data
        else "No interaction data collected yet"
    )

    return {
        "total_feedback": total_feedback,
        "helpful_responses": helpful_responses,
        "helpful_feedback_rate_pct": helpful_rate,
        "understanding_responses": understood_status_count,
        "understood_count": understood_responses,
        "understanding_rate_pct": understanding_rate,
        "recommendations_shown": recommendations_shown,
        "recommendations_accepted": recommendations_accepted,
        "recommendations_rejected": recommendations_rejected,
        "actions_completed": actions_completed,
        "recommendation_acceptance_rate_pct": recommendation_acceptance_rate,
        "action_completion_rate_pct": action_completion_rate,
        "savings_plans_created": savings_plans_created,
        "savings_plans_viewed": savings_plans_viewed,
        "forecast_views": forecast_views,
        "anomaly_views": anomaly_views,
        "copilot_usage": copilot_usage,
        "has_data": has_data,
        "message": message,
    }
