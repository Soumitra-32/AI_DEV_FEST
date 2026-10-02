"""Financial health score (rules layer): a 0–100 reading with its own arithmetic.

Five behaviour components, each scored against a documented "best" and "worst"
value, add up to 100:

===============  ====  =========================================================
Component        Max   Reads
===============  ====  =========================================================
fee burden         20  ``fee_share_of_income`` (share of income lost to fees)
cash dependency    20  ``cash_out_share_of_outflow`` (how much leaves as cash)
income regularity  20  ``income_cv`` and ``income_days_per_month``
balance cushion    20  ``balance_mean_bdt`` against ``income_mean_bdt``
shortfall freedom  20  ``shortfall_days_per_month``
===============  ====  =========================================================

Two things this module is careful about:

* **Every point is traceable.** :attr:`HealthScore.components` carries the points
  and the sentence behind them, and :attr:`HealthScore.arithmetic` the sum, so the
  card can show its work instead of presenting a magic number.
* **It is not the consistency signal.** The consistency signal is deliberately a
  *band*, never a score, and never a lending decision. This score is a coaching
  reading of behaviour over the observed history; it says nothing about
  creditworthiness and is never sent to a lender.

Pure functions over a feature ``Mapping`` — no database, no model, no LLM. The
inputs are exactly the label-free columns from :mod:`backend.data.features`, so the
same row trains the models and drives this card.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import pandas as pd

#: Full marks.
SCORE_MAX = 100

#: ``(floor, band)`` from highest to lowest; the first floor a score reaches wins.
BANDS: tuple[tuple[int, str], ...] = (
    (80, "Strong"),
    (55, "Steady"),
    (30, "Building"),
    (0, "Fragile"),
)

#: The feature columns this module reads (all optional; a missing one counts 0).
SCORED_FEATURES: tuple[str, ...] = (
    "fee_share_of_income",
    "cash_out_share_of_outflow",
    "income_cv",
    "income_days_per_month",
    "balance_mean_bdt",
    "income_mean_bdt",
    "balance_min_bdt",
    "shortfall_days_per_month",
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _fraction(value: float, best: float, worst: float) -> float:
    """Linear 0–1 fraction of the way from ``worst`` to ``best`` (either order).

    ``best=0, worst=0.02`` scores 1.0 at zero and 0.0 at (or beyond) the worst
    value; ``best=20, worst=5`` does the same when bigger is better. Clamped, so a
    value outside the documented range can never earn negative points or more than
    the component's maximum.
    """
    if worst == best:
        return 1.0 if value == best else 0.0
    return _clamp((value - worst) / (best - worst))


@dataclass(frozen=True)
class HealthComponent:
    """One scored behaviour, with the sentence that explains its points."""

    key: str
    label_en: str
    label_bn: str
    points: float
    max_points: float
    detail_en: str
    detail_bn: str

    @property
    def share(self) -> float:
        """Fraction of this component's maximum that was earned (0–1)."""
        return 0.0 if self.max_points <= 0 else round(self.points / self.max_points, 4)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label_en": self.label_en,
            "label_bn": self.label_bn,
            "points": round(float(self.points), 1),
            "max_points": float(self.max_points),
            "share": self.share,
            "detail_en": self.detail_en,
            "detail_bn": self.detail_bn,
        }


#: Component maxima and the documented best/worst values behind them.
MAX_FEE_BURDEN = 20.0
MAX_CASH_DEPENDENCY = 20.0
MAX_INCOME_REGULARITY = 20.0
MAX_BALANCE_CUSHION = 20.0
MAX_SHORTFALL_FREEDOM = 20.0

FEE_SHARE_BEST, FEE_SHARE_WORST = 0.0, 0.02
CASH_SHARE_BEST, CASH_SHARE_WORST = 0.0, 0.50
INCOME_CV_BEST, INCOME_CV_WORST = 0.30, 1.50
INCOME_DAYS_BEST, INCOME_DAYS_WORST = 20.0, 5.0
CUSHION_BEST, CUSHION_WORST = 0.15, 0.0
SHORTFALL_BEST, SHORTFALL_WORST = 0.0, 4.0


@dataclass(frozen=True)
class HealthScore:
    """A 0–100 coaching score, its band, and the components that produced it."""

    score: int
    band: str
    components: list[HealthComponent] = field(default_factory=list)
    arithmetic: list[str] = field(default_factory=list)

    @property
    def score_max(self) -> int:
        return SCORE_MAX

    def component(self, key: str) -> HealthComponent | None:
        """The component with ``key`` (``None`` when it is not present)."""
        for item in self.components:
            if item.key == key:
                return item
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "score_max": SCORE_MAX,
            "band": self.band,
            "components": [item.as_dict() for item in self.components],
            "arithmetic": list(self.arithmetic),
        }


def band_for(score: float) -> str:
    """The band a score falls in (``Strong`` / ``Steady`` / ``Building`` / ``Fragile``)."""
    value = float(score)
    for floor, name in BANDS:
        if value >= floor:
            return name
    return BANDS[-1][1]


def score_row(row: Mapping[str, Any] | pd.Series) -> HealthScore:
    """Score one user's feature row.

    ``row`` is the label-free mapping from :mod:`backend.data.features` — or the
    ``Series`` slice of it you get straight out of a feature frame, which is
    accepted as-is rather than forcing every caller to convert first. A missing
    key counts as 0, which is the honest reading of "we did not observe it".
    """
    def value(key: str, default: float = 0.0) -> float:
        try:
            number = float(row.get(key, default))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default
        return number if number == number else default  # NaN -> default

    fee_share = max(value("fee_share_of_income"), 0.0)
    cash_share = max(value("cash_out_share_of_outflow"), 0.0)
    income_cv = max(value("income_cv"), 0.0)
    income_days = max(value("income_days_per_month"), 0.0)
    balance_mean = value("balance_mean_bdt")
    income_mean = max(value("income_mean_bdt"), 0.0)
    balance_min = value("balance_min_bdt")
    shortfall = max(value("shortfall_days_per_month"), 0.0)

    fee_points = MAX_FEE_BURDEN * _fraction(fee_share, FEE_SHARE_BEST, FEE_SHARE_WORST)
    cash_points = MAX_CASH_DEPENDENCY * _fraction(cash_share, CASH_SHARE_BEST, CASH_SHARE_WORST)

    # Regularity is half variability (steady inflows) and half frequency (how many
    # days money actually arrives), so a monthly remittance and an irregular daily
    # wage are not scored as if they were the same shape.
    cv_points = (MAX_INCOME_REGULARITY / 2.0) * _fraction(income_cv, INCOME_CV_BEST, INCOME_CV_WORST)
    days_points = (MAX_INCOME_REGULARITY / 2.0) * _fraction(
        income_days, INCOME_DAYS_BEST, INCOME_DAYS_WORST
    )
    regularity_points = cv_points + days_points

    cushion_ratio = (balance_mean / income_mean) if income_mean > 0 else 0.0
    cushion_points = MAX_BALANCE_CUSHION * _fraction(cushion_ratio, CUSHION_BEST, CUSHION_WORST)
    if balance_min < 0:
        # A window in which the wallet actually ran short earns nothing here, no
        # matter how healthy the average looks.
        cushion_points = 0.0

    shortfall_points = MAX_SHORTFALL_FREEDOM * _fraction(shortfall, SHORTFALL_BEST, SHORTFALL_WORST)

    components = [
        HealthComponent(
            key="fee_burden",
            label_en="Fees",
            label_bn="ফি",
            points=round(fee_points, 1),
            max_points=MAX_FEE_BURDEN,
            detail_en=f"{fee_share * 100:.2f}% of income goes to fees",
            detail_bn=f"আয়ের {fee_share * 100:.2f}% ফিতে যায়",
        ),
        HealthComponent(
            key="cash_dependency",
            label_en="Cash dependency",
            label_bn="ক্যাশ নির্ভরতা",
            points=round(cash_points, 1),
            max_points=MAX_CASH_DEPENDENCY,
            detail_en=f"{cash_share * 100:.1f}% of spending leaves as cash",
            detail_bn=f"খরচের {cash_share * 100:.1f}% ক্যাশ হিসেবে বেরিয়ে যায়",
        ),
        HealthComponent(
            key="income_regularity",
            label_en="Income regularity",
            label_bn="আয়ের নিয়মিততা",
            points=round(regularity_points, 1),
            max_points=MAX_INCOME_REGULARITY,
            detail_en=(
                f"income varies by a factor of {income_cv:.2f}, "
                f"with {income_days:.0f} income days a month"
            ),
            detail_bn=f"আয়ের ওঠানামা {income_cv:.2f}, মাসে আয়ের দিন {income_days:.0f}টি",
        ),
        HealthComponent(
            key="balance_cushion",
            label_en="Balance cushion",
            label_bn="ব্যালেন্সের সুরক্ষা",
            points=round(cushion_points, 1),
            max_points=MAX_BALANCE_CUSHION,
            detail_en=f"average balance is {cushion_ratio * 100:.1f}% of a month's income",
            detail_bn=f"গড় ব্যালেন্স মাসিক আয়ের {cushion_ratio * 100:.1f}%",
        ),
        HealthComponent(
            key="shortfall_freedom",
            label_en="Shortfall-free days",
            label_bn="ঘাটতিমুক্ত দিন",
            points=round(shortfall_points, 1),
            max_points=MAX_SHORTFALL_FREEDOM,
            detail_en=f"{shortfall:.1f} shortfall days a month",
            detail_bn=f"মাসে {shortfall:.1f} দিন ব্যালেন্স ঘাটতি",
        ),
    ]

    raw_total = sum(item.points for item in components)
    total = int(round(_clamp(raw_total, 0.0, float(SCORE_MAX))))
    band = band_for(total)
    arithmetic = [
        f"{item.key}: {item.points:.1f}/{item.max_points:.0f} ({item.detail_en})"
        for item in components
    ]
    arithmetic.append(f"total = {raw_total:.1f} -> {total} / {SCORE_MAX} ({band})")
    return HealthScore(score=total, band=band, components=components, arithmetic=arithmetic)


def score_features(features: pd.DataFrame, user_id: str) -> HealthScore:
    """Score one user out of an already-built feature frame.

    Raises ``KeyError`` when the user is absent, so a caller can turn that into a
    404 rather than showing a score built from nothing.
    """
    match = features.loc[features["user_id"].eq(user_id)]
    if match.empty:
        raise KeyError(f"no features for user {user_id}")
    return score_row(match.iloc[0])

