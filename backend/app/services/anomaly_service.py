"""Spending Companion service (Phase 5): model scores + the fee switch.

Shapes two already-tested pieces into the frozen ``/anomalies`` contract:

* :mod:`backend.ml.anomaly` ranks each recent payment by how unusual it is *for
  this user*. When no forest has been trained the fixed-threshold rule answers
  instead — never a 500, but never silently either: the fallback is logged as a
  warning and the ``provenance.assumption`` text changes to describe the rule
  that actually ran (``provenance.source`` is ``"rule"``);
* :mod:`backend.rules.fee_switch` computes what the cash-out channel cost and what
  the same money would cost by app transfer.

The route stays thin: no arithmetic and no model loading live in the router, so a
slow or missing artifact degrades the answer instead of failing the request.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from backend.data import features as user_features
from backend.data import generator
from backend.ml import anomaly as ml_anomaly
from backend.rules import fee_switch

logger = logging.getLogger("shonchoy.anomaly_service")

DEFAULT_WINDOW_DAYS = 30
DEFAULT_LIMIT = 20

#: How far above the user's own average an amount has to sit before the card
#: calls it large.
LARGE_RATIO = 3.0


def _reason(features_row: pd.Series, timestamp: pd.Timestamp) -> str:
    """Plain-language reason for one ranked row, from its own features.

    The order mirrors the injected anomaly families (repeat, odd hour, large
    amount) but is derived purely from this user's numbers — the ground-truth
    ``anomaly_labels`` table is never read on the serving path.
    """
    rapid = float(features_row.get("is_rapid_repeat", 0.0))
    off_hours = float(features_row.get("is_off_hours", 0.0))
    ratio = float(features_row.get("amount_over_user_mean", 0.0))
    zscore = float(features_row.get("amount_zscore", 0.0))
    clock = pd.Timestamp(timestamp).strftime("%H:%M")
    if rapid and ratio >= 1.0:
        return f"Another very similar payment within {int(ml_anomaly.RAPID_REPEAT_MINUTES)} minutes"
    if off_hours:
        return f"Happened at {clock}, outside your usual hours"
    if ratio >= LARGE_RATIO or zscore >= 3.0:
        return f"About {ratio:.1f}x your own average payment"
    return f"Timing is unusual for you ({clock} is not one of your usual hours)"


def _item(row: pd.Series) -> dict[str, Any]:
    """One ``AnomalyItem`` payload (the router validates it against the schema)."""
    channel = str(row["channel"])
    is_cash_out = channel == "cash_out"
    return {
        "transaction_id": str(row["transaction_id"]),
        "timestamp": pd.Timestamp(row["timestamp"]).isoformat(),
        "amount_bdt": round(float(row["amount_bdt"]), 2),
        "channel": fee_switch.channel_label(channel),
        "category": str(row.get("category", "")),
        # ``anomaly_type`` is the ground-truth label, which the serving path never
        # reads; it stays None here rather than dressing a model score as truth.
        "anomaly_type": None,
        "score": round(float(row["anomaly_score"]), 4),
        "reason": _reason(row, row["timestamp"]),
        "suggested_action": "switch" if is_cash_out else "reduce",
        "suggested_channel": (
            fee_switch.channel_label(fee_switch.DEFAULT_ALTERNATIVE) if is_cash_out else None
        ),
    }


def _rank(window: pd.DataFrame, features: pd.DataFrame, directory: str | Path) -> ml_anomaly.AnomalyScores:
    """Score the window with the trained forest, degrading to the rule loudly.

    The rule fallback is deliberate — a missing artifact must not 500 the card —
    but it must not be *silent*: the rule is a single absolute taka cutoff, so
    ranking by it is a materially different (and much blunter) claim than ranking
    by per-user behaviour. The warning is the operator's signal that the trained
    artifact is missing from the deployment, and :func:`_provenance` tells the
    user which engine answered.
    """
    scores = ml_anomaly.predict(features, directory)
    if scores is not None:
        return scores
    logger.warning(
        "no IsolationForest artifact in %s; ranking %d transactions with the "
        "fixed-threshold rule instead. Run `make train`.",
        directory,
        len(window),
    )
    return ml_anomaly.rule_scores(window)


def _provenance(scores: ml_anomaly.AnomalyScores, items: int, days: int) -> dict[str, Any]:
    """The Prediction / Assumption / Explanation block, truthful about the source.

    The assumption text has to match the engine: claiming "not a fixed taka
    amount" while the fixed-threshold rule is what actually ran would be the
    worst kind of wrong, because it would describe a method the numbers did not
    come from.
    """
    if scores.source == "model":
        assumption = (
            "Unusual means far from your own recent pattern — the amount, the hour, "
            "and the gap since your previous payment — not a fixed taka amount. "
            "The fee figures use the simulated rate card."
        )
    else:
        assumption = (
            "The trained model is not available, so this uses a simple fallback: "
            "a payment is called unusual when it is several times the average "
            "payment of all users together. That misses anything small in taka "
            "but large for you, and also flags routine big payments from heavy "
            "spenders. The fee figures use the simulated rate card."
        )
    return {
        "prediction": (
            f"The {items} least typical payments of your last {days} days, "
            "ranked against your own history."
            if items
            else f"No payment of your last {days} days stands out against your own history."
        ),
        "assumption": assumption,
        "source": scores.source,
    }


def build_anomalies(
    user_id: str,
    window_days: int = DEFAULT_WINDOW_DAYS,
    limit: int = DEFAULT_LIMIT,
    db_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Rank the caller's recent payments and price the cash-out habit.

    Returns a plain dict whose keys line up with ``schemas.AnomalyResponse`` (plus
    ``flagged_count``/``source`` for the explanation layer). Raises ``KeyError``
    when the user has no transactions, which the router turns into a 404.
    """
    cfg = generator.load_config()
    path = Path(db_path) if db_path is not None else user_features.default_db_path()
    transactions = user_features.load_transactions(path, [user_id])
    if transactions.empty:
        raise KeyError(f"no transactions for user {user_id}")

    days = max(int(window_days), 1)
    cutoff = transactions["timestamp"].max() - pd.Timedelta(days=days)
    window = transactions.loc[transactions["timestamp"].ge(cutoff)].reset_index(drop=True)

    features = ml_anomaly.build_features(window)
    directory = artifact_dir if artifact_dir is not None else ml_anomaly.ARTIFACT_DIR
    scores = _rank(window, features, directory)

    ranked = window.join(features[ml_anomaly.FEATURE_COLUMNS])
    ranked["anomaly_score"] = scores.frame["anomaly_score"].to_numpy()
    ranked["is_anomaly"] = scores.frame["is_anomaly"].to_numpy()
    ranked = ranked.sort_values("anomaly_score", ascending=False, kind="stable").reset_index(drop=True)

    items = [_item(row) for _, row in ranked.head(max(int(limit), 1)).iterrows()]
    flagged = int(ranked["is_anomaly"].fillna(False).astype(bool).sum())

    switch = fee_switch.suggest(window, cfg, window_days=days)
    fee_payload = switch.as_dict() if switch.worth_suggesting else None

    if fee_payload is not None:
        explanation = (
            f"{switch.cash_out_count} cash-out(s) cost {switch.fee_paid_bdt:,.0f} taka in the "
            f"window; switching to {switch.alternative_channel} would cost "
            f"{switch.alternative_fee_bdt:,.0f}, a potential saving of "
            f"{switch.potential_saving_bdt:,.0f} taka."
        )
    else:
        explanation = "No cash-out fee stands out in this window, so there is nothing to switch."
    if not items:
        explanation = "Nothing in this window stands out against your own recent pattern. " + explanation

    provenance = _provenance(scores, len(items), days)
    provenance["explanation"] = explanation

    return {
        "user_id": user_id,
        "window_days": days,
        "items": items,
        "fee_switch": fee_payload,
        "flagged_count": flagged,
        "source": scores.source,
        "provenance": provenance,
    }


