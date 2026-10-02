"""Fairness audit (ML layer): where a group is served worse than the rest.

The plan's responsible-AI row (section 11) asks for three gaps, each across
persona, district and income band:

* **MAE gap (forecast)** — is the model less accurate for some group than for the
  best-served one? Error is an *accuracy* metric, so the gap is measured against
  the best group and "worse" always means a larger number.
* **flag-rate gap (anomaly)** — does the forest call one group's payments odd
  more often than another's? This is a *parity* metric: neither a high nor a low
  rate is better, so the gap is measured against the whole population rate and
  the target is met only when the *absolute* gap is inside tolerance.
* **band-distribution gap (consistency signal)** — are "Building" / "Steady" /
  "Strong" assigned at the same rates to every group? Also parity, same
  reasoning.

That difference is why :data:`HIGHER_IS_WORSE` exists: it records which way
"exceeds the target" points for each metric, instead of leaving every reader to
re-derive it from the metric name.

Two honest limits, both carried in the output rather than glossed over:

* The target is a **relative** gap, per the plan. 500 users across 8 districts and
  5 personas means several district cells hold fewer than
  :data:`DEFAULT_MIN_USERS` held-out users, where a MAE is noise. Those groups are
  *excluded and listed* in ``excluded_groups`` rather than scored, because
  publishing a 90% "gap" computed from four people would be worse than silence.
* Every number here is from the synthetic ledger. ``DATA_ASSUMPTIONS.md`` already
  says 500 users is too small for real fairness claims; this module measures the
  pipeline, not the population.

No demographic column is ever a model input (``backend/data/features.py``
``DEMOGRAPHIC_COLUMNS``); they are joined here, after scoring, purely to slice
the results.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from . import anomaly, forecast, signal
# Aliased: this module's own public entry point is ``evaluate``, which would
# otherwise rebind the imported name and hide ``scored_cells`` behind itself.
from . import evaluate as forecast_evaluate
from .dataset import HORIZON_DAYS

ARTIFACT_DIR = forecast.ARTIFACT_DIR

#: The three slicing dimensions, in the order they are reported. These are the
#: only values the ``Dimension`` literal in ``app/schemas.py`` accepts.
DIMENSIONS: tuple[str, ...] = ("persona", "district", "income_band")

#: The three consistency bands, in the order the card presents them.
BANDS: tuple[str, ...] = ("Building", "Steady", signal.TOP_BAND)

#: The plan's target: no group worse than 15% relative gap.
TARGET_RELATIVE_GAP_PCT = 15.0

#: Below this many held-out users a group's MAE or rate is reported as noise.
DEFAULT_MIN_USERS = 10

#: True when a value above the target is a problem for that metric. ``None``
#: marks a metric that is neither (unused today, kept so a future one has to say
#: which way it points rather than defaulting silently).
HIGHER_IS_WORSE: dict[str, bool] = {
    "mae_inflow_bdt": True,
    "mae_outflow_bdt": True,
    "mae_net_bdt": True,
    "anomaly_flag_rate_pct": False,
    "anomaly_label_rate_pct": False,
    "band_share_pct": False,
}

FLOW_MEASURES: dict[str, str] = {
    "inflow": "mae_inflow_bdt",
    "outflow": "mae_outflow_bdt",
    "net": "mae_net_bdt",
}


def _relative_gap(value: float, reference: float) -> float:
    """``(value - reference) / reference`` as a percentage.

    A zero reference cannot be divided by, and the honest answer there is that
    the gap is undefined rather than infinite -- ``0.0`` for a zero value, and
    ``100.0`` for a non-zero one, so a group is still visibly flagged.
    """
    if not np.isfinite(value) or not np.isfinite(reference):
        return 0.0
    if reference == 0.0:
        return 0.0 if value == 0.0 else 100.0
    return round((float(value) - float(reference)) / float(reference) * 100.0, 2)


def _exceeds(gap_pct: float, metric: str) -> bool:
    """Is this gap outside the target, in the direction that hurts the group?"""
    higher_is_worse = HIGHER_IS_WORSE.get(metric)
    if higher_is_worse is None:  # pragma: no cover - no such metric today
        return abs(gap_pct) > TARGET_RELATIVE_GAP_PCT
    if higher_is_worse:
        return gap_pct > TARGET_RELATIVE_GAP_PCT
    return abs(gap_pct) > TARGET_RELATIVE_GAP_PCT


def _small_groups(frame: pd.DataFrame, min_users: int) -> list[dict[str, Any]]:
    """The groups in ``frame`` with fewer than ``min_users`` distinct users.

    One rule, used by all three families. The unit is always *users*, never rows:
    a group of three heavy spenders yields hundreds of rows, which would clear a
    row-count filter while still being three people whose rate is noise. Sharing
    the rule is also what makes the merged ``excluded_groups`` list honest -- if
    one family used a different denominator, the same group could be scored by
    one family and reported as excluded by another.
    """
    excluded: list[dict[str, Any]] = []
    for dimension in DIMENSIONS:
        if dimension not in frame.columns:
            continue
        for group, part in frame.groupby(dimension, dropna=False):
            users = int(part["user_id"].nunique())
            if users < min_users:
                excluded.append(
                    {"dimension": dimension, "group": str(group), "users": users}
                )
    return excluded


def _attach_groups(
    joined: pd.DataFrame,
    group_frame: pd.DataFrame,
    min_users: int,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Join demographics onto scored cells, dropping groups that are too small.

    The small-group filter is applied on **users**, not on scored cells, because
    a user contributes many cells: a group of 9 users can look large in cell
    count and still be 9 people.
    """
    if joined.empty or group_frame.empty:
        return joined, []
    columns = [column for column in ("user_id", *DIMENSIONS) if column in group_frame.columns]
    merged = joined.merge(group_frame[columns], on="user_id", how="left")

    excluded = _small_groups(merged, min_users)
    if excluded:
        keep = merged[list(DIMENSIONS)].apply(
            lambda row: not any(
                row[dimension] == item["group"] and item["users"] < min_users
                for dimension in DIMENSIONS
                for item in excluded
            ),
            axis=1,
        )
        merged = merged.loc[keep]
    return merged, excluded

def _rows_from_values(
    values: Mapping[tuple[str, str], float],
    reference: float,
    metric: str,
) -> list[dict[str, Any]]:
    """One :class:`FairnessRow`-shaped dict per group, from a value table.

    ``reference`` defines "the rest", and it is the caller's choice because it is
    the only thing that differs between the two kinds of metric: the best-scored
    group for an error, the whole cohort for a parity rate.
    """
    rows: list[dict[str, Any]] = []
    for (dimension, group), value in values.items():
        gap = _relative_gap(value, reference)
        rows.append(
            {
                "dimension": dimension,
                "group": group,
                "metric": metric,
                "value": round(float(value), 4),
                "relative_gap_pct": gap,
                "exceeds_target": _exceeds(gap, metric),
            }
        )
    return rows


def _forecast_gaps(
    featured: Optional[pd.DataFrame],
    daily: Optional[pd.DataFrame],
    splits: Optional[pd.DataFrame],
    group_frame: pd.DataFrame,
    artifact_dir: str | Path,
    horizon_days: int,
    min_users: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Cumulative-flow MAE per group, on the cells :func:`evaluate` scored."""
    if (
        featured is None
        or featured.empty
        or daily is None
        or daily.empty
        or splits is None
        or splits.empty
    ):
        return [], [], {"status": "unavailable", "reason": "no forecast frame to score"}
    try:
        joined, _ = forecast_evaluate.scored_cells(
            featured, daily, splits, artifact_dir, horizon_days
        )
    except (ValueError, KeyError) as exc:
        return [], [], {"status": "unavailable", "reason": str(exc)}

    merged, excluded = _attach_groups(joined, group_frame, min_users)
    if merged.empty:
        return [], excluded, {"status": "unavailable", "reason": "no group large enough"}

    totals = merged.groupby(["user_id", "date"], as_index=False).agg(
        actual_inflow=("actual_inflow", "sum"),
        predicted_inflow=("predicted_inflow", "sum"),
        actual_outflow=("actual_outflow", "sum"),
        predicted_outflow=("predicted_outflow", "sum"),
    )
    totals["actual_net"] = totals["actual_inflow"] - totals["actual_outflow"]
    totals["predicted_net"] = totals["predicted_inflow"] - totals["predicted_outflow"]

    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for flow, metric in FLOW_MEASURES.items():
        totals["_abs_error"] = (
            totals[f"predicted_{flow}"] - totals[f"actual_{flow}"]
        ).abs()
        per_user = totals.groupby("user_id", as_index=False).agg(
            _abs_error=("_abs_error", "sum"), _cells=("_abs_error", "size")
        )
        per_user["_mae"] = per_user["_abs_error"] / per_user["_cells"]
        merged_users = per_user.merge(group_frame, on="user_id", how="left")

        values: dict[tuple[str, str], float] = {}
        for dimension in DIMENSIONS:
            if dimension not in merged_users.columns:
                continue
            grouped = merged_users.groupby(dimension)["_mae"]
            # A plain dict, not ``Series[group]``: the group keys come back as
            # ``Hashable``, which ``Series.__getitem__`` has no overload for.
            sizes = grouped.size().to_dict()
            means = grouped.mean()
            for group, mean in means.items():
                if int(sizes.get(group, 0)) == 0:
                    continue
                values[(dimension, str(group))] = float(mean)

        # An error metric's reference is the best-served group, so every gap is
        # >= 0 and a positive number is unambiguously worse.
        reference = min(values.values()) if values else 0.0
        rows.extend(_rows_from_values(values, reference, metric))
        summary[flow] = {
            "best_mae_bdt": round(float(reference), 2),
            "worst_mae_bdt": round(float(max(values.values())), 2) if values else 0.0,
            "groups_scored": len(values),
        }
    return rows, excluded, summary


def _anomaly_gaps(
    transactions: Optional[pd.DataFrame],
    anomaly_labels: Optional[pd.DataFrame],
    splits: Optional[pd.DataFrame],
    group_frame: pd.DataFrame,
    artifact_dir: str | Path,
    min_users: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """How often the forest flags each group's payments, vs the cohort rate.

    Parity, not accuracy: a high flag rate is not automatically unfair, so the
    reference is the cohort rate and only the absolute gap is held to the target.
    The *ground-truth* rate is reported next to it so a genuine difference in
    injected anomalies is visible rather than mistaken for model bias.
    """
    if transactions is None or transactions.empty or group_frame.empty:
        return [], [], {"status": "unavailable", "reason": "no transactions"}

    test_users = set(splits.loc[splits["split"].eq("test"), "user_id"]) if splits is not None else set()
    if test_users:
        transactions = transactions.loc[transactions["user_id"].isin(test_users)]
    if transactions.empty:
        return [], [], {"status": "unavailable", "reason": "no test transactions"}

    features = anomaly.build_features(transactions)
    scores = anomaly.predict(features, artifact_dir)
    if scores is None:
        return [], [], {"status": "unavailable", "reason": "no anomaly artifact"}

    frame = features[["user_id", "transaction_id"]].copy()
    frame["_flagged"] = scores.frame["is_anomaly"].to_numpy().astype(int)
    if anomaly_labels is not None and not anomaly_labels.empty:
        labelled = set(anomaly_labels["transaction_id"])
        frame["_labelled"] = frame["transaction_id"].isin(labelled).astype(int)
    else:
        frame["_labelled"] = 0
    merged = frame.merge(group_frame, on="user_id", how="left")

    rows: list[dict[str, Any]] = []
    population_flag = float(merged["_flagged"].mean() * 100.0)
    population_label = float(merged["_labelled"].mean() * 100.0)
    for column, metric, reference in (
        ("_flagged", "anomaly_flag_rate_pct", population_flag),
        ("_labelled", "anomaly_label_rate_pct", population_label),
    ):
        values: dict[tuple[str, str], float] = {}
        for dimension in DIMENSIONS:
            if dimension not in merged.columns:
                continue
            for group, part in merged.groupby(dimension):
                # The filter is on **users**, not on transactions, to match the
                # other two families. A group of three heavy spenders produces
                # hundreds of rows and would clear a row-count filter, but it is
                # still three people -- and mixing denominators would let a group
                # be scored here and excluded by the MAE family at the same time.
                if int(part["user_id"].nunique()) < min_users:
                    continue
                values[(dimension, str(group))] = float(part[column].mean() * 100.0)
        rows.extend(_rows_from_values(values, reference, metric))

    excluded = _small_groups(merged, min_users)
    return rows, excluded, {
        # Rounded to the same 4 dp as the row ``value``s, not to 2. The gaps in
        # ``rows`` were computed against the unrounded rate, so publishing a
        # coarser reference makes the published arithmetic irreproducible -- and
        # the error is worst exactly where it matters, on a small cohort rate
        # where 0.01pp of rounding is a large *relative* share of the base.
        "cohort_flag_rate_pct": round(population_flag, 4),
        "cohort_label_rate_pct": round(population_label, 4),
        "transactions_scored": int(len(merged)),
    }


def _band_gaps(
    user_rows: Optional[pd.DataFrame],
    splits: Optional[pd.DataFrame],
    group_frame: pd.DataFrame,
    artifact_dir: str | Path,
    min_users: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """How the three consistency bands are distributed per group, vs the cohort."""
    if user_rows is None or user_rows.empty:
        return [], [], {"status": "unavailable", "reason": "no user features"}

    test_users = set(splits.loc[splits["split"].eq("test"), "user_id"]) if splits is not None else set()
    if test_users:
        user_rows = user_rows.loc[user_rows["user_id"].isin(test_users)]
    if user_rows.empty:
        return [], [], {"status": "unavailable", "reason": "no test users"}

    bands = signal.predict_bands(user_rows, artifact_dir)
    if bands is None:
        return [], [], {"status": "unavailable", "reason": "no signal artifact"}

    frame = user_rows[["user_id"]].copy()
    frame["band"] = bands["band"].to_numpy()
    merged = frame.merge(group_frame, on="user_id", how="inner")

    rows: list[dict[str, Any]] = []
    for band in BANDS:
        merged["_in_band"] = (merged["band"] == band).astype(int)
        population = float(merged["_in_band"].mean() * 100.0)
        values: dict[tuple[str, str], float] = {}
        for dimension in DIMENSIONS:
            if dimension not in merged.columns:
                continue
            for group, part in merged.groupby(dimension):
                if int(part["user_id"].nunique()) < min_users:
                    continue
                values[(dimension, str(group))] = float(part["_in_band"].mean() * 100.0)
        rows.extend(_rows_from_values(values, population, "band_share_pct"))

    return rows, _small_groups(merged, min_users), {
        "users_scored": int(len(merged)),
        "cohort_band_share_pct": {
            # Same 4 dp reasoning as ``cohort_flag_rate_pct``: the per-band gaps
            # in ``rows`` are measured against this rate, so the published share
            # has to carry enough precision to reproduce them.
            band: round(float((merged["band"] == band).mean() * 100.0), 4)
            for band in BANDS
        },
    }


def evaluate(
    featured: Optional[pd.DataFrame] = None,
    daily: Optional[pd.DataFrame] = None,
    splits: Optional[pd.DataFrame] = None,
    group_frame: Optional[pd.DataFrame] = None,
    transactions: Optional[pd.DataFrame] = None,
    anomaly_labels: Optional[pd.DataFrame] = None,
    user_rows: Optional[pd.DataFrame] = None,
    artifact_dir: str | Path = ARTIFACT_DIR,
    horizon_days: int = HORIZON_DAYS,
    min_users: int = DEFAULT_MIN_USERS,
) -> dict[str, Any]:
    """Run all three gap families and report the worst gap per family.

    Each family is independent and degrades on its own: a missing forecast
    artifact costs the MAE table, not the whole audit. Returns a dict shaped for
    ``metrics.json`` under ``"fairness"``:

    ``rows``
        Every scored ``(dimension, group, metric)`` with its value, its relative
        gap, and whether that gap is outside the target. Sorted worst-gap-first so
        a reader sees the worst offender without sorting.
    ``by_family``
        The headline number per family -- the largest gap of each kind -- plus
        whether the family is inside the 15% target.
    ``excluded_groups``
        The groups dropped for being too small, with the user count that dropped
        them, so a reader can see what the table does *not* cover.
    """
    if group_frame is None or group_frame.empty:
        return {
            "status": "unavailable",
            "reason": "no demographic columns to group by",
            "target_relative_gap_pct": TARGET_RELATIVE_GAP_PCT,
            "rows": [],
            "by_family": {},
            "excluded_groups": [],
        }

    dimensions = [column for column in ("user_id", *DIMENSIONS) if column in group_frame.columns]
    groups = group_frame[dimensions].dropna(subset=["user_id"]).drop_duplicates("user_id")

    families: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    mae_rows, mae_excluded, mae_summary = _forecast_gaps(
        featured, daily, splits, groups, artifact_dir, horizon_days, min_users
    )
    rows.extend(mae_rows)
    excluded.extend(mae_excluded)
    families["forecast_mae"] = {
        "metrics": list(FLOW_MEASURES.values()),
        "reference": "best-scored group (lower MAE is better)",
        "worst_relative_gap_pct": _worst(mae_rows, list(FLOW_MEASURES.values())),
        "target_met": _family_met(mae_rows, list(FLOW_MEASURES.values())),
        **mae_summary,
    }

    flag_rows, flag_excluded, flag_summary = _anomaly_gaps(
        transactions, anomaly_labels, splits, groups, artifact_dir, min_users
    )
    rows.extend(flag_rows)
    excluded.extend(flag_excluded)
    families["anomaly_flag_rate"] = {
        "metrics": ["anomaly_flag_rate_pct", "anomaly_label_rate_pct"],
        "reference": "cohort rate (parity, not accuracy)",
        "worst_relative_gap_pct": _worst(flag_rows, ["anomaly_flag_rate_pct"]),
        "target_met": _family_met(flag_rows, ["anomaly_flag_rate_pct"]),
        **flag_summary,
    }

    band_rows, band_excluded, band_summary = _band_gaps(
        user_rows, splits, groups, artifact_dir, min_users
    )
    rows.extend(band_rows)
    excluded.extend(band_excluded)
    families["consistency_bands"] = {
        "metrics": ["band_share_pct"],
        "reference": "cohort share (parity, not accuracy)",
        "worst_relative_gap_pct": _worst(band_rows, ["band_share_pct"]),
        "target_met": _family_met(band_rows, ["band_share_pct"]),
        **band_summary,
    }

    rows.sort(key=lambda row: -abs(float(row["relative_gap_pct"])))
    scored = [row for row in rows if not row.get("exceeds_target")]
    return {
        "target_relative_gap_pct": TARGET_RELATIVE_GAP_PCT,
        "min_users_per_group": int(min_users),
        "dimensions": list(DIMENSIONS),
        "n_rows": int(len(rows)),
        "n_exceeding_target": int(len(rows) - len(scored)),
        "target_met": bool(rows and not [row for row in rows if row["exceeds_target"]]),
        "rows": rows,
        "by_family": families,
        "excluded_groups": _dedupe_exclusions(excluded),
        "caveats": [
            "All numbers come from the synthetic ledger, so this measures the "
            "pipeline's behaviour across groups, not a real population.",
            "persona / district / income_band are reporting slices only and are "
            "never model inputs.",
            "Groups below min_users_per_group are excluded and listed in "
            "excluded_groups rather than scored on too few users.",
        ],
    }


def _dedupe_exclusions(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One entry per group.

    Each family excludes independently (on cells for MAE, on rows for the two
    rates), so the same small district can be dropped three times. Reporting it
    three times would read as three separate findings; the smallest user count
    seen is the one that explains why it was dropped everywhere.
    """
    seen: dict[tuple[str, str], int] = {}
    for item in items:
        key = (str(item["dimension"]), str(item["group"]))
        users = int(item.get("users", 0))
        seen[key] = min(users, seen[key]) if key in seen else users
    return [
        {"dimension": dimension, "group": group, "users": users}
        for (dimension, group), users in sorted(seen.items())
    ]


def _worst(rows: Sequence[Mapping[str, Any]], metrics: Sequence[str]) -> Optional[float]:
    """Largest gap magnitude among the given metrics, or ``None`` if unscored."""
    gaps = [
        abs(float(row["relative_gap_pct"]))
        for row in rows
        if row["metric"] in metrics
    ]
    return round(max(gaps), 2) if gaps else None


def _family_met(rows: Sequence[Mapping[str, Any]], metrics: Sequence[str]) -> Optional[bool]:
    """``True``/``False`` when the family was scored, ``None`` when it was not.

    ``None`` rather than ``True``: an unmeasured family must never be reported as
    having passed its target, which is how a gap quietly passes review.
    """
    relevant = [row for row in rows if row["metric"] in metrics]
    if not relevant:
        return None
    return not any(bool(row.get("exceeds_target")) for row in relevant)
