"""Consistency signal service (Phase 7): the band card, end to end.

Shapes :mod:`backend.ml.signal` into the frozen ``/signal`` contract. The route
stays thin, like every router here: auth -> feature flag -> service -> schema.

What this service is careful about:

* **It returns a band.** The model's probability is used to pick the band and is
  reported as ``auc`` metadata, but no number that could be read as a score is
  ever put in the response body.
* **It degrades, loudly.** With no trained artifact the answer comes from
  :func:`backend.ml.signal.rule_band` and ``provenance.source`` says ``rule``,
  so the card cannot imply a model ran when none did.
* **It never decides anything about lending.** ``not_a_decision`` is pinned true
  by the schema and the banner is part of the payload, not a styling detail.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.data import features as user_features
from backend.ml import signal as ml_signal

logger = logging.getLogger("shonchoy.signal_service")

DEFAULT_WINDOW_DAYS = 90

#: How each SHAP factor is described to a person, in Bangla and English.
#: The model supplies the feature, the direction and the size; the sentence is
#: fixed text, because a model-written sentence is a claim we cannot check.
FACTOR_LANGUAGE: dict[str, dict[str, str]] = {
    "income_days_per_month": {
        "en": "income arrives on {value} days a month",
        "bn": "মাসে {value} দিনে আয় আসে",
    },
    "income_cv": {
        "en": "income varies month to month (variation {value})",
        "bn": "মাসে মাসে আয় বদলায় (পরিবর্তন {value})",
    },
    "income_mean_bdt": {
        "en": "average monthly income",
        "bn": "গড় মাসিক আয়",
    },
    "spend_mean_bdt": {
        "en": "average monthly spending",
        "bn": "গড় মাসিক খরচ",
    },
    "spend_cv": {
        "en": "spending swings month to month (variation {value})",
        "bn": "খরচ মাসে মাসে বদলায় (পরিবর্তন {value})",
    },
    "cash_out_count_per_month": {
        "en": "{value} cash-outs a month",
        "bn": "মাসে {value} বার ক্যাশ-আউট",
    },
    "cash_out_volume_per_month_bdt": {
        "en": "cash-out volume",
        "bn": "ক্যাশ-আউটের পরিমাণ",
    },
    "cash_out_share_of_outflow": {
        "en": "{value} of spending leaves as cash",
        "bn": "খরচের {value} ক্যাশ হিসেবে বেরিয়ে যায়",
    },
    "fee_per_month_bdt": {
        "en": "fees paid ({value} a month)",
        "bn": "প্রদত্ত ফি (মাসে {value})",
    },
    "fee_share_of_income": {
        "en": "fees take {value} of income",
        "bn": "আয়ের {value} ফিতে চলে যায়",
    },
    "balance_mean_bdt": {
        "en": "average balance ({value})",
        "bn": "গড় ব্যালেন্স ({value})",
    },
    "balance_min_bdt": {
        "en": "lowest balance reached ({value})",
        "bn": "সবচেয়ে কম ব্যালেন্স ({value})",
    },
    "balance_volatility": {
        "en": "balance moves around (variation {value})",
        "bn": "ব্যালেন্স ওঠানামা করে (পরিবর্তন {value})",
    },
    "shortfall_days_per_month": {
        "en": "{value} days a month run out of money",
        "bn": "মাসে {value} দিন টাকা শেষ হয়ে যায়",
    },
    "month_end_spend_ratio": {
        "en": "spending is {value}x higher at month end",
        "bn": "মাস শেষে খরচ {value} গুণ বেশি",
    },
    "weekend_spend_ratio": {
        "en": "weekend spending is {value}x the rest",
        "bn": "সপ্তাহ শেষের খরচ বাকি দিনের {value} গুণ",
    },
    "months_observed": {
        "en": "{value} months of history",
        "bn": "{value} মাসের ইতিহাস",
    },
}


def _plain_language(feature: str, magnitude: float, row: dict[str, float], language: str) -> str:
    """A fixed sentence for one factor, with the user's own number in it."""
    template = FACTOR_LANGUAGE.get(feature, {}).get(language)
    if template is None:
        template = FACTOR_LANGUAGE.get(feature, {}).get("en", "{feature} ({value})")
    value = row.get(feature, magnitude)
    if isinstance(value, float) and abs(value) < 10:
        shown = f"{value:.2f}".rstrip("0").rstrip(".")
    else:
        shown = f"{float(value):,.0f}"
    return template.format(value=shown, feature=feature)


def _factors(raw: list[dict[str, Any]], row: dict[str, float], language: str) -> list[dict[str, Any]]:
    """Model factors -> ``SignalFactor`` payloads with fixed wording."""
    return [
        {
            "feature": str(factor["feature"]),
            "direction": str(factor["direction"]),
            "magnitude": float(factor.get("magnitude", 0.0)),
            "plain_language": _plain_language(
                str(factor["feature"]), float(factor.get("magnitude", 0.0)), row, language
            ),
        }
        for factor in raw[:3]
    ]
def _improvements(band: str, language: str = "bn") -> list[str]:
    """What to do next, chosen by band. Fixed text, never model-generated."""
    table: dict[str, dict[str, list[str]]] = {
        "Building": {
            "bn": [
                "একটি ছোট লক্ষ্য দিয়ে শুরু করুন, যেটা বাদ পড়তে পারে",
                "মাসে এক-দুইবার ক্যাশ-আউটের বদলে অ্যাপ ট্রান্সফার ব্যবহার করুন",
                "মাস শেষের ৩-৪ দিনের বড় খরচ আগেই সাজিয়ে নিন",
            ],
            "en": [
                "Start with a goal small enough to miss",
                "Use an app transfer instead of one or two cash-outs a month",
                "Line up the large month-end payments a few days early",
            ],
        },
        "Steady": {
            "bn": [
                "মাস শেষের চাপটা ছড়িয়ে দিন",
                "যে চ্যানেলে বেশি খরচ হয়, সেটা কমান",
            ],
            "en": [
                "Spread out the month-end pressure",
                "Reduce the channel where most of your fees go",
            ],
        },
        "Strong": {
            "bn": [
                "এখন একটু বড় লক্ষ্য ঠিক করার সময়",
                "বাফারটা আরও এক মাসের খরচের সমান করুন",
            ],
            "en": [
                "This is the moment to set a larger goal",
                "Grow the buffer to cover a full month of spending",
            ],
        },
    }
    return list(table.get(band, table["Building"]).get(language, []))


def build_signal(
    user_id: str,
    language: str = "bn",
    db_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    """The consistency band for one user, shaped as ``ConsistencySignalResponse``.

    Raises ``KeyError`` when the user is unknown, which the router turns into a
    404 rather than an empty card pretending to be an answer.
    """
    path = Path(db_path) if db_path is not None else user_features.default_db_path()
    frame = user_features.user_features(user_features.load_config(), user_features.load_transactions(path))
    rows = frame.loc[frame["user_id"].eq(user_id)]
    if rows.empty:
        raise KeyError(f"no features for user {user_id}")
    row = user_features.feature_row(frame, user_id)

    directory = artifact_dir if artifact_dir is not None else ml_signal.ARTIFACT_DIR
    prediction = ml_signal.predict(rows, directory)

    if prediction is None:
        band, raw_factors = ml_signal.rule_band(row)
        source = "rule"
    else:
        band, raw_factors = prediction.band, prediction.factors
        source = "model"

    meta = ml_signal.load_meta(directory)
    auc = meta.get("auc")

    return {
        "user_id": user_id,
        "band": band,
        "factors": _factors(raw_factors, row, language),
        "improvements": _improvements(band, language),
        "not_a_decision": True,
        "auc": float(auc) if isinstance(auc, (int, float)) else None,
        "provenance": {
            "prediction": (
                "Your recent behaviour sits in the "
                f"{band} band over the next couple of months."
            ),
            "assumption": (
                "Based only on the transactions you can see, and on a label built "
                "from this simulated ledger."
            ),
            "explanation": (
                "This is a reading of your habits, not a judgement about you, and it "
                "is not used for any lending decision."
            ),
            "source": source,
        },
    }