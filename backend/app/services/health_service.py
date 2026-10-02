"""Financial Health Coach service (rules layer behind ``GET /health-coach``).

Shapes the already-tested :mod:`backend.rules.health_score` into the frozen
``HealthCoachResponse`` contract: a 0-100 reading, a plain-language Bangla
summary, and the per-factor arithmetic that produced it.

Three things this service is deliberate about:

* **The score is a coaching reading, never a credit score.** The band and the
  "not a credit score" banner travel in the payload, so no surface has to
  remember to add them.
* **The summary is derived from real factors.** It names the strongest habit and
  the one with the most room to improve, both taken from the same components the
  score summed — not written independently and left to drift.
* **Unknown users raise ``KeyError``**, which the router turns into a 404, rather
  than serving a score built from nothing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.data import features as user_features
from backend.rules import health_score
from backend.rules.health_score import HealthScore

#: Bangla label for each band (the card is Bangla-first).
BAND_BN: dict[str, str] = {
    "Strong": "শক্তিশালী",
    "Steady": "স্থিতিশীল",
    "Building": "গড়ার পথে",
    "Fragile": "দুর্বল",
}

#: One honest sentence per band, said the same way everywhere.
BAND_SUMMARY_BN: dict[str, str] = {
    "Strong": "আপনার অর্থনৈতিক অভ্যাস এখন বেশ শক্তিশালী।",
    "Steady": "আপনার অর্থনৈতিক অভ্যাস এখন স্থিতিশীল।",
    "Building": "আপনার অর্থনৈতিক অভ্যাস এখন গড়ে উঠছে।",
    "Fragile": "আপনার অর্থনৈতিক অভ্যাস এখন দুর্বল, তবে ছোট পদক্ষেপেই বদলানো যায়।",
}
BAND_SUMMARY_EN: dict[str, str] = {
    "Strong": "Your money habits are in strong shape right now.",
    "Steady": "Your money habits are steady right now.",
    "Building": "Your money habits are still building up.",
    "Fragile": "Your money habits are fragile right now, but small steps move them.",
}


def _biggest(graded: HealthScore) -> tuple[Any, Any]:
    """The best-served and worst-served components (largest/smallest share)."""
    ranked = sorted(graded.components, key=lambda item: item.share)
    return ranked[-1], ranked[0]


def build_health(
    user_id: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """The ``HealthCoachResponse`` payload for one user.

    Raises ``KeyError`` when the user has no features, so the router can answer
    404 instead of a 200 with a meaningless score.
    """
    path = db_path if db_path is not None else user_features.default_db_path()
    frame = user_features.user_features(
        user_features.load_config(), user_features.load_transactions(path)
    )
    graded = health_score.score_features(frame, user_id)

    best, worst = _biggest(graded)
    band_bn = BAND_BN.get(graded.band, graded.band)
    summary_bn = (
        f"আপনার অর্থনৈতিক স্বাস্থ্য স্কোর {graded.score}/{graded.score_max} — {band_bn}। "
        + BAND_SUMMARY_BN.get(graded.band, "")
    )
    summary_en = (
        f"Your financial health score is {graded.score}/{graded.score_max} "
        f"({graded.band}). " + BAND_SUMMARY_EN.get(graded.band, "")
    )
    if worst.share < 1.0:
        summary_bn += f" সবচেয়ে ভালো দিক: {best.label_bn}। উন্নতির জায়গা: {worst.label_bn}।"
        summary_en += (
            f" Strongest habit: {best.label_en}. Most room to improve: {worst.label_en}."
        )

    components = []
    for item in graded.components:
        components.append(
            {
                "key": item.key,
                "label_en": item.label_en,
                "label_bn": item.label_bn,
                "points": float(item.points),
                "max_points": float(item.max_points),
                "share": float(item.share),
                "detail_en": item.detail_en,
                "detail_bn": item.detail_bn,
            }
        )

    return {
        "user_id": user_id,
        "score": int(graded.score),
        "score_max": int(graded.score_max),
        "band": graded.band,
        "band_bn": band_bn,
        "summary_bn": summary_bn,
        "summary_en": summary_en,
        "factors": components,
        "arithmetic": list(graded.arithmetic),
        "is_not_a_credit_score": True,
        "provenance": {
            "prediction": summary_en,
            "assumption": (
                "Each of the five behaviours is scored against a documented best "
                "and worst value over the observed history; a missing input counts "
                "zero."
            ),
            "explanation": (
                "This is a coaching reading of behaviour, not a credit score and "
                "not a lending decision."
            ),
            "source": "rule",
        },
    }
