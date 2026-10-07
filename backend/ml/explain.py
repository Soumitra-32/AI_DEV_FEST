"""Feature importance and SHAP helpers (ML layer).

One job: turn a model into *reasons a person can read*. The forecast cards and
the consistency-signal card both need "which feature moved this prediction, and
by how much", and the plan's §5 requires SHAP for the signal model.

Two entry points:

* :func:`global_importance` — LightGBM gain/split importance, cheap and always
  available (used for the ``/metrics`` page's "what drives the forecast").
* :func:`shap_contributions` / :func:`top_drivers` — per-row SHAP values for one
  user's latest feature row, turned into the ``Driver`` shape the API returns.

The consistency signal's per-user explanation does **not** live here: it belongs
to :mod:`backend.ml.signal`, whose :func:`~backend.ml.signal.shap_explanation`
produces the exact decomposition for the logistic regression the signal actually
uses. An earlier revision carried a second ``linear_contributions`` /
``top_signal_factors`` pair here; the audit found them dead code *and* wrong
(they looked for ``feature_std_`` / ``scaler_``, which a scikit-learn
``LogisticRegression`` never has, so they silently returned ``coef x raw value``).
They were removed rather than left as a second, differently-wrong explanation
path for someone to wire up later (audit M4).

Design rules:

* **Sign, not size, is the message.** A driver says "cash-outs this month push
  next month's outflow *up* by ৳X" — never a bare percentage of importance.
* **Anchored, like the model.** The forecast boosters predict a *residual* from
  the user's own trailing mean (``ml.forecast.ANCHOR_COLUMNS``), so a driver
  reports ``anchor + shap`` as the modelled level. That keeps the reason
  consistent with the number the user was shown.
* **Degrade, never crash.** SHAP is optional (it is a heavy import) and the
  artifacts may be missing; every function returns an empty result instead of
  raising, and the caller falls back to templates.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping

import numpy as np
import pandas as pd

from . import forecast as forecast_model

ARTIFACT_DIR = forecast_model.ARTIFACT_DIR

#: How many drivers the forecast card shows (the UI has room for three).
MAX_DRIVERS = 3

#: Human-readable names for the forecast features. Only the features that
#: actually carry meaning for a non-technical reader are listed; anything else
#: falls back to the raw column name, which is still honest.
FEATURE_LABELS: Mapping[str, tuple[str, str]] = {
    "day_of_month": ("মাসের কত তারিখ", "day of the month"),
    "weekday": ("সপ্তাহের দিন", "weekday"),
    "is_weekend": ("সাপ্তাহিক ছুটি", "is weekend"),
    "is_month_end": ("মাস শেষ", "is month end"),
    "days_to_month_end": ("মাস শেষ হতে বাকি দিন", "days to month end"),
    "lag_1_net": ("গতকালের নেট", "yesterday's net"),
    "lag_7_net": ("গত সপ্তাহের নেট", "last week's net"),
    "lag_14_net": ("২ সপ্তাহ আগের নেট", "net two weeks ago"),
    "lag_1_outflow": ("গতকালের খরচ", "yesterday's spending"),
    "lag_7_outflow": ("গত সপ্তাহের খরচ", "last week's spending"),
    "roll_3_inflow": ("গত ৩ দিনের আয়", "income over 3 days"),
    "roll_3_outflow": ("গত ৩ দিনের খরচ", "spending over 3 days"),
    "roll_7_inflow": ("গত ৭ দিনের আয়", "income over 7 days"),
    "roll_7_outflow": ("গত ৭ দিনের খরচ", "spending over 7 days"),
    "roll_14_outflow": ("গত ১৪ দিনের খরচ", "spending over 14 days"),
    "roll_28_inflow": ("গত ২৮ দিনের আয়", "income over 28 days"),
    "roll_28_outflow": ("গত ২৮ দিনের খরচ", "spending over 28 days"),
    "roll_28_net": ("গত ২৮ দিনের নেট", "net over 28 days"),
    "max_7_outflow": ("সপ্তাহের সবচেয়ে বেশি খরচের দিন", "biggest spending day this week"),
    "shortfall_last_7": ("গত ৭ দিনে ব্যালেন্স ঘাটতি", "shortfall days in the last 7"),
    "mtd_inflow": ("এই মাসে এখন পর্যন্ত আয়", "income so far this month"),
    "mtd_outflow": ("এই মাসে এখন পর্যন্ত খরচ", "spending so far this month"),
    "mtd_cash_out_bdt": ("এই মাসে ক্যাশ-আউট", "cash-outs so far this month"),
    "mtd_cash_out_count": ("এই মাসে ক্যাশ-আউট সংখ্যা", "number of cash-outs this month"),
    "roll_7_cash_out_bdt": ("গত ৭ দিনে ক্যাশ-আউট", "cash-outs over 7 days"),
    "roll_28_cash_out_bdt": ("গত ২৮ দিনে ক্যাশ-আউট", "cash-outs over 28 days"),
    "days_since_cash_out": ("শেষ ক্যাশ-আউটের পর দিন", "days since the last cash-out"),
    "balance_end_bdt": ("ওয়ালেটের বর্তমান ব্যালেন্স", "current wallet balance"),
}


def feature_label(feature: str, language: str = "en") -> str:
    """Plain-language name of a feature, falling back to the raw column."""
    entry = FEATURE_LABELS.get(feature)
    if entry is None:
        return feature
    return entry[0] if language == "bn" else entry[1]


def format_taka(amount: float) -> str:
    """Taka with no decimals and the Bangla-friendly grouping."""
    return f"৳{abs(float(amount)):,.0f}"


@dataclass(frozen=True)
class Driver:
    """One reason behind a prediction, in the shape the API returns."""

    feature: str
    direction: str  # "increases" | "decreases"
    impact_bdt: float
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "direction": self.direction,
            "impact_bdt": round(float(self.impact_bdt), 2),
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# global importance (no SHAP needed)
# ---------------------------------------------------------------------------
def global_importance(
    artifact_dir: str | None = None,
    flow: str = "outflow",
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Gain and split importance of the trained forecast booster.

    ``flow`` is ``"inflow"`` or ``"outflow"``. Returns ``[]`` when the artifact
    is missing, so a page that wants this can simply render nothing.
    """
    directory = artifact_dir or ARTIFACT_DIR
    try:
        models = forecast_model.load(directory)
    except (OSError, ValueError, KeyError):
        return []
    meta = models.get("_meta") or {}
    booster = models.get("inflow" if flow == "inflow" else "outflow")
    if booster is None:
        return []
    names = list(meta.get("features", []))
    try:
        gain = booster.feature_importance(importance_type="gain")
        split = booster.feature_importance(importance_type="split")
    except (AttributeError, ValueError):
        return []
    total = float(np.sum(gain)) or 1.0
    rows = [
        {
            "feature": names[index] if index < len(names) else f"f{index}",
            "gain": float(gain[index]),
            "gain_share_pct": round(100.0 * float(gain[index]) / total, 2),
            "splits": int(split[index]),
        }
        for index in range(len(gain))
    ]
    rows.sort(key=lambda row: row["gain"], reverse=True)
    return rows[: max(int(top_k), 1)]


# ---------------------------------------------------------------------------
# SHAP (per-row reasons)
# ---------------------------------------------------------------------------
def _shap_module():
    """Import shap lazily, or ``None`` when it is not installed.

    shap is a heavy import and the demo must run without it, so nothing in the
    request path may import it at module level.
    """
    try:
        import shap  # noqa: PLC0415 - deliberately lazy
    except Exception:  # pragma: no cover - depends on the environment
        return None
    return shap


@lru_cache(maxsize=4)
def _explainer(artifact_dir: str, flow: str):
    """A cached ``TreeExplainer`` for one booster (building it is expensive)."""
    shap = _shap_module()
    if shap is None:
        return None
    try:
        models = forecast_model.load(artifact_dir)
        booster = models.get("inflow" if flow == "inflow" else "outflow")
        if booster is None:
            return None
        return shap.TreeExplainer(booster)
    except Exception:  # pragma: no cover - artifact/version problems
        return None


@lru_cache(maxsize=8)
def _model_features(artifact_dir: str, flow: str) -> tuple[str, ...]:
    """The exact feature order the trained booster was fitted on.

    Serving must slice the row to this list: passing extra columns (user_id,
    date, ...) makes LightGBM refuse the prediction outright.
    """
    try:
        meta = forecast_model.load(artifact_dir).get("_meta") or {}
        return tuple(str(name) for name in meta.get("features", []))
    except Exception:  # pragma: no cover - artifact/version problems
        return ()


def shap_contributions(
    row: pd.DataFrame,
    flow: str = "outflow",
    artifact_dir: str | None = None,
) -> dict[str, float]:
    """SHAP values for a single feature row, keyed by feature name.

    The row is sliced to the feature order the model was trained on. Returns
    ``{}`` when shap is unavailable or the artifact cannot be loaded — the caller
    then has no SHAP reasons, not an exception to handle.
    """
    directory = str(artifact_dir or ARTIFACT_DIR)
    explainer = _explainer(directory, flow)
    features = list(_model_features(directory, flow))
    if explainer is None or row.empty or not features:
        return {}
    usable = [name for name in features if name in row.columns]
    if not usable:
        return {}
    matrix = row[usable].to_numpy(dtype=float)
    try:
        values = np.asarray(explainer.shap_values(matrix)).reshape(len(usable), -1)[:, 0]
    except Exception:  # pragma: no cover - shap version differences
        return {}
    # NaN/inf guard: a TreeExplainer can emit non-finite values for degenerate
    # trees or inputs. A NaN impact would render as "৳nan" in the UI and a
    # comparison against it is always False, so the driver silently vanishes.
    # Drop non-finite contributions rather than serve them.
    return {
        name: float(values[index])
        for index, name in enumerate(usable)
        if np.isfinite(values[index])
    }


def _driver_text(
    feature: str,
    value: float,
    impact: float,
    flow: str,
    language: str,
) -> str:
    """One readable sentence: label, value, direction, taka impact."""
    label = feature_label(feature, language)
    money = format_taka(impact)
    if language == "bn":
        movement = "বাড়ায়" if impact > 0 else "কমায়"
        target = "আয়" if flow == "inflow" else "খরচ"
        return f"{label} ({value:,.0f}) আগামী {target} {movement} প্রায় {money}"
    movement = "pushes up" if impact > 0 else "pulls down"
    target = "income" if flow == "inflow" else "spending"
    return f"{label} ({value:,.0f}) {movement} next {target} by about {money}"


def top_drivers(
    row: pd.DataFrame,
    flow: str = "outflow",
    language: str = "en",
    artifact_dir: str | None = None,
    limit: int = MAX_DRIVERS,
) -> list[Driver]:
    """The biggest SHAP reasons for one user's latest feature row.

    ``impact_bdt`` is the absolute taka effect on the modelled daily flow, and
    ``direction`` is its sign: ``increases`` raises the predicted flow,
    ``decreases`` lowers it. With no SHAP available the list is empty and the
    forecast card simply shows no drivers.
    """
    contributions = shap_contributions(row, flow=flow, artifact_dir=artifact_dir)
    if not contributions:
        return []
    ranked = sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)
    drivers: list[Driver] = []
    for feature, impact in ranked[: max(int(limit), 1)]:
        if abs(impact) < 1.0:
            # Below one taka a day there is nothing worth telling a user.
            continue
        value = float(row.iloc[0][feature]) if feature in row.columns else 0.0
        drivers.append(
            Driver(
                feature=feature,
                direction="increases" if impact > 0 else "decreases",
                impact_bdt=abs(float(impact)),
                detail=_driver_text(feature, value, float(impact), flow, language),
            )
        )
    return drivers


# ---------------------------------------------------------------------------
# consistency-signal model (Phase 5) — linear contributions
# ---------------------------------------------------------------------------
#: Signal features whose plain-language wording we can write by hand. The
#: consistency card shows at most three, so a short curated list is enough.
SIGNAL_LABELS: Mapping[str, tuple[str, str]] = {
    "income_days_per_month": ("মাসে কত দিন আয় হয়", "days with income in a month"),
    "income_cv": ("আয়ের ওঠানামা", "income variability"),
    "cash_out_count_per_month": ("মাসে ক্যাশ-আউট সংখ্যা", "cash-outs per month"),
    "fee_share_of_income": ("আয়ের কত অংশ ফিতে যায়", "share of income lost to fees"),
    "balance_mean_bdt": ("গড় ব্যালেন্স", "average balance"),
    "balance_min_bdt": ("সবচেয়ে কম ব্যালেন্স", "lowest balance"),
    "shortfall_days_per_month": ("মাসে ব্যালেন্স ঘাটতির দিন", "shortfall days per month"),
    "month_end_spend_ratio": ("মাস শেষে বেশি খরচ", "month-end spending pattern"),
    "balance_volatility": ("ব্যালেন্সের ওঠানামা", "balance volatility"),
}


def signal_label(feature: str, language: str = "en") -> str:
    """Plain-language name of a signal feature."""
    entry = SIGNAL_LABELS.get(feature)
    if entry is None:
        return feature_label(feature, language)
    return entry[0] if language == "bn" else entry[1]
