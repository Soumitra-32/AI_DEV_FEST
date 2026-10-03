"""IsolationForest anomaly detector (ML layer) for the Spending Companion.

The plan's comparison (section 4) is explicit: the *rule* baseline is "amount
> X", one absolute cutoff for everybody, and the *model* reads each user's own
behaviour instead. This module is the model half; the rule half lives in
:mod:`backend.ml.baselines` (``fixed_threshold_*``), so the two are always scored
on the same rows by :func:`evaluate`.

Features are **per-user relative** — how big the amount is against *this person's*
own mean, how far the hour is from *their* usual hour, how close it sits to the
previous transaction — because a ৳2,000 cash-out is routine for a shopkeeper and
abnormal for a student. Nothing in the feature matrix reads ``anomaly_labels``:
the injected ground truth is only ever used to *score* the result, never to train
it (``backend/tests/test_no_leakage.py`` holds that line).

Degradation is deliberate throughout: every entry point returns ``None`` or ``{}``
rather than raising when an artifact is missing, so the API can fall back to the
rule baseline instead of returning a 500.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    average_precision_score,
    precision_recall_fscore_support,
    roc_auc_score,
)

from . import baselines

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_FILE = "anomaly_iforest.joblib"
META_FILE = "anomaly_meta.json"

MODEL_NAME = "isolation_forest_behavior"

#: Columns carried alongside the features so a caller can line a score up with
#: the row it came from (the IDs are never model inputs).
CONTEXT_COLUMNS = ["transaction_id", "user_id", "timestamp", "amount_bdt", "channel", "category"]

#: The per-user behaviour features the forest reads.
#:
#: Chosen on the **validation** split and then frozen (never on test — the same
#: anti-circularity rule the forecast follows). Three "how large is this for *me*"
#: features plus four "does the timing look like me" ones: on validation this set
#: scored AUC 0.83 against 0.80 for the wider matrix that also carried wallet and
#: channel columns, because extra weakly-informative dimensions dilute a tree
#: isolation forest. ``backend/scripts/train_all.py`` re-measures the held-out
#: numbers every run, so the choice is checked rather than assumed.
FEATURE_COLUMNS = [
    "log_amount",
    "amount_zscore",
    "amount_over_user_mean",
    "hours_from_typical_hour",
    "is_off_hours",
    "minutes_since_prev",
    "is_rapid_repeat",
]

#: The dataset's documented active window starts at 06:00, so 00:00–05:59 is the
#: "unusual time" region (the generator injects ``unusual_time`` into it).
OFF_HOURS_END = 5

#: Two near-identical transactions inside this many minutes read as a repeat.
RAPID_REPEAT_MINUTES = 20

#: ``amount_over_user_mean`` when the user has no past outflow to compare to.
#: 1.0 says "about your usual size", which is the honest answer when the question
#: is unanswerable; 0.0 would assert the row is far below average.
NEUTRAL_AMOUNT_RATIO = 1.0

#: Floor on the per-user std used by ``amount_zscore``. A user whose past amounts
#: are all identical has a sample std of exactly 0, which leaves the z-score
#: undefined -- and "identical so far" is precisely when a deviation matters most.
#: The floor is the larger of an absolute value (one generator rounding unit,
#: ``dataset.round_to_bdt``) and this fraction of the user's own past mean, so a
#: perfectly consistent user still gets a finite, strongly positive score.
MIN_ZSCORE_STD_BDT = 10.0
MIN_ZSCORE_RELATIVE_STD = 0.05

#: Winsorising bound for ``amount_zscore``. The floored denominator above can
#: otherwise produce scores in the hundreds, which would swamp every other input
#: to the forest and let one feature decide the answer.
ZSCORE_CAP = 12.0
#: Hard-coded rather than derived from the frame so that training and serving
#: cannot disagree -- whatever slice a caller passes in must not change how any
#: row is encoded. Mirrors ``dataset.active_hours`` ``[6, 23]`` in the generator
#: config; the midpoint is the least-assuming single number for it. Using the
#: user's whole-ledger median here instead leaked the future (truncation moved
#: the feature by up to 8.0 hours).
DEFAULT_TYPICAL_HOUR = 14.5

#: How far back a gap is capped when a user has no previous transaction.
MAX_GAP_MINUTES = 1440.0

DEFAULT_CONTAMINATION = 0.02

#: How many candidate cut-offs are evaluated between the observed score bounds.
THRESHOLD_GRID_SIZE = 81

#: Product guard on the selected operating point: no cut that flags more than
#: this share of validation rows is eligible, however good its raw F1 looks.
MAX_FLAG_RATE = 0.20

#: Objective for :func:`select_threshold`. F1 is the right default here because
#: the card shows a *ranked* list to one person: a false positive costs the user
#: one row of attention, a false negative costs a missed anomaly. Ties are
#: broken towards the higher cut-off (fewer false alarms), because a spending
#: companion that cries wolf is abandoned.
THRESHOLD_OBJECTIVE = "f1"

#: Small, deterministic, single-threaded: trains in a few seconds on a laptop.
PARAMS: dict[str, Any] = {
    "n_estimators": 300,
    "max_samples": "auto",
    "random_state": 7,
    "n_jobs": 1,
}


@dataclass(frozen=True)
class AnomalyScores:
    """Per-row scores plus where they came from."""

    frame: pd.DataFrame  # anomaly_score (higher = odder), is_anomaly
    source: str  # "model" | "rule"
    threshold: Optional[float] = None


def _past_only_reference(
    amount: pd.Series,
    is_income: pd.Series,
    user_id: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """Per-user outflow mean and std computed from **strictly past** rows only.

    The audit found this was the single worst feature defect in the repository:
    the reference was the user's mean over the *whole* ledger, so a transaction
    dated 3 January was scored against a mean that included March. Correlation
    between that version and a genuinely causal one is only 0.229, and 23.8% of
    rows moved by more than 0.5 once the future was removed.

    ``shift(1).expanding()`` gives each row the statistics of everything strictly
    before it, which is what "how big is this for *me*" has to mean at scoring
    time.

    ``user_id`` must be the **real** user column. An earlier revision of this
    fix reconstructed the key from ``amount.index``, which after the
    ``reset_index(drop=True)`` inside :func:`build_features` is a positional
    RangeIndex -- so every row formed its own one-row group, ``shift(1)`` was
    always NaN, and the whole-ledger fallback took over. That silently reduced
    ``amount_zscore`` to the constant 0.0 for all 176 416 rows and left
    ``amount_over_user_mean`` at exactly 1.0 for 79% of them, i.e. two of the
    seven inputs to the isolation forest were dead.

    Rows with no past outflow (a user's first transactions) get NaN here; the
    caller turns that into a neutral encoding rather than borrowing the user's
    own future.
    """
    frame = pd.DataFrame(
        {
            "user_id": pd.Series(user_id).to_numpy(),
            "amount": amount.where(~is_income).to_numpy(dtype=float),
        }
    )
    grouped = frame.groupby("user_id", sort=False)["amount"]
    past_mean = grouped.transform(lambda s: s.shift(1).expanding().mean())
    past_std = grouped.transform(lambda s: s.shift(1).expanding().std())
    return (
        past_mean.astype(float).set_axis(amount.index),
        past_std.astype(float).set_axis(amount.index),
    )


def build_features(transactions: pd.DataFrame) -> pd.DataFrame:
    """Per-user behaviour features for every transaction row.

    Returns a frame with the same index as ``transactions`` and the columns in
    :data:`FEATURE_COLUMNS`, all numeric (no NaNs). Per-user statistics are
    computed inside each user only - a neighbour's spending never sets the bar -
    and from **strictly past** rows only, so a feature never encodes the future
    (see :func:`_past_only_reference`).

    Callers must pass the user's **whole** history, not a recent window. The
    per-user reference is a function of history length, so a window produces a
    different feature distribution than the one the model was fitted on; the
    serving path builds features first and slices the window afterwards.
    """
    if transactions is None or transactions.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)
    frame = transactions.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame = frame.sort_values(
        ["user_id", "timestamp", "transaction_id"], kind="stable"
    ).reset_index(drop=True)

    is_income = (
        frame["type"].eq("income")
        if "type" in frame.columns
        else pd.Series(False, index=frame.index)
    )
    amount = frame["amount_bdt"].astype(float)

    # --- per-user amount reference (strictly past outflow rows only) --------
    user_mean, user_std = _past_only_reference(amount, is_income, frame["user_id"])
    # Denominator floor: see :data:`MIN_ZSCORE_STD_BDT`. Rows with no past outflow
    # keep a NaN mean, so the ratio below falls back to the neutral encoding.
    std_floor = pd.concat(
        [
            pd.Series(MIN_ZSCORE_STD_BDT, index=user_mean.index, dtype=float),
            user_mean.abs() * MIN_ZSCORE_RELATIVE_STD,
        ],
        axis=1,
    ).max(axis=1)
    safe_std = user_std.clip(lower=std_floor).where(user_mean.notna())
    zscore = (
        ((amount - user_mean) / safe_std)
        .replace([np.inf, -np.inf], np.nan)
        .clip(-ZSCORE_CAP, ZSCORE_CAP)
        .fillna(0.0)
    )
    positive_mean = user_mean.where(user_mean.gt(0))
    # No past outflow yet -> the ratio is unknown, and the neutral value is 1.0
    # ("about your usual size"). It used to fall back to 0.0, which asserts the
    # row is far *below* average -- a claim we have no evidence for.
    over_mean = (
        (amount / positive_mean)
        .replace([np.inf, -np.inf], np.nan)
        .fillna(NEUTRAL_AMOUNT_RATIO)
    )

    # --- time shape --------------------------------------------------------
    hour = frame["timestamp"].dt.hour.astype(float)
    hours = pd.DataFrame(
        {
            "user_id": frame["user_id"],
            "_hour": hour.where(~is_income),
        }
    )
    past_median = hours.groupby("user_id", sort=False)["_hour"].transform(
        lambda s: s.shift(1).expanding().median()
    )
    # A user's opening rows have no past hour to compare against, so they get the
    # fixed mid-window hour from :data:`DEFAULT_TYPICAL_HOUR`. The previous
    # fallback was the user's own whole-ledger median hour, which leaked the
    # future (truncation moved this feature by up to 8.0 hours) and made the
    # encoding depend on which slice a caller passed in.
    typical = past_median.fillna(DEFAULT_TYPICAL_HOUR).astype(float)
    hours_from_typical = (hour - typical).abs()

    previous = frame.groupby("user_id")["timestamp"].shift(1)
    gap = (frame["timestamp"] - previous).dt.total_seconds() / 60.0
    minutes_since_prev = gap.clip(0.0, MAX_GAP_MINUTES).fillna(MAX_GAP_MINUTES)

    features = pd.DataFrame(
        {
            "log_amount": np.log1p(amount.clip(lower=0.0)),
            "amount_zscore": zscore,
            "amount_over_user_mean": over_mean,
            "hours_from_typical_hour": hours_from_typical,
            "is_off_hours": (hour <= OFF_HOURS_END).astype(float),
            "minutes_since_prev": minutes_since_prev.astype(float),
            "is_rapid_repeat": (minutes_since_prev <= RAPID_REPEAT_MINUTES).astype(float),
        },
        index=frame.index,
    )
    context = [column for column in CONTEXT_COLUMNS if column in frame.columns]
    output = frame[context].copy()
    for column in FEATURE_COLUMNS:
        output[column] = features[column]
    return output


def _slice_split(features: pd.DataFrame, splits: Optional[pd.DataFrame], name: str) -> pd.DataFrame:
    """Rows belonging to one split (by user). No split -> the whole frame."""
    if splits is None or "user_id" not in features.columns:
        return features
    wanted = set(splits.loc[splits["split"].eq(name), "user_id"])
    return features.loc[features["user_id"].isin(wanted)]


def contamination_from(cfg: Optional[Mapping[str, Any]], default: float = DEFAULT_CONTAMINATION) -> float:
    """Expected anomaly share, from the dataset config when it is available.

    NOTE: this is only the *fitting-time* hint for the forest. It is deliberately
    **not** the shipped decision threshold -- see :func:`select_threshold`.
    """
    if cfg is None:
        return float(default)
    try:
        return float(cfg["anomalies"]["rate"])
    except (KeyError, TypeError, ValueError):
        return float(default)


def candidate_thresholds(
    score: np.ndarray,
    size: int = THRESHOLD_GRID_SIZE,
) -> np.ndarray:
    """Candidate cut-offs derived from the *observed* score distribution.

    H3 follow-up (audit verification): the first implementation hard-coded
    ``np.linspace(-0.60, -0.20, 81)`` -- the sign convention of
    ``decision_function``, not of the ``-score_samples`` values this module
    actually ranks by. Those scores span roughly 0.37-0.80, so **all 81
    candidates sat below the entire distribution** and were the identical
    "flag everything" point: precision 2.86%, recall 100%, F1 5.57%, 25 903 rows
    flagged. The reported optimum also sat on the grid's upper edge, which is the
    signature of an unsearched range.

    Deriving the grid from the scores removes the failure class outright: it
    cannot be out of range by construction, and because a row can only be flagged
    by a cut that is one of the observed values, the attainable F1 optimum is
    always inside it.

    The ``-score_samples`` orientation (higher = odder) is decided by the caller;
    this function is sign-agnostic.
    """
    values = np.asarray(score, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return np.array([0.0])
    unique = np.unique(values)
    if unique.size <= size:
        return unique
    # Keep the extremes and interpolate between them on a quantile grid, so
    # resolution follows where the rows actually are rather than the range.
    return np.unique(np.quantile(values, np.linspace(0.0, 1.0, size)))


def threshold_curve(
    truth: np.ndarray,
    score: np.ndarray,
    grid: Optional[Sequence[float]] = None,
) -> list[dict[str, Any]]:
    """Precision / recall / F1 at every candidate cut, for one labelled split.

    Published rather than hidden so the trade-off is a reader's decision: at
    these prevalences (2.9%) the same score can buy 92% recall at 4% precision
    or 20% recall at 35% precision, and the operating point is a product choice.

    ``grid`` defaults to :func:`candidate_thresholds` evaluated on ``score``.
    """
    score = np.asarray(score, dtype=float)
    if grid is None:
        # ``candidate_thresholds`` returns an ndarray, which is not a
        # ``Sequence[float]`` under the numpy stubs -- materialise a real list
        # so ``grid`` is narrowed to a concrete type instead of staying
        # ``Optional`` for the loop below.
        grid = [float(cut) for cut in candidate_thresholds(score)]
    out: list[dict[str, Any]] = []
    for cut in grid:
        flagged = score >= float(cut)
        tp = int(np.sum(flagged & (truth == 1)))
        fp = int(np.sum(flagged & (truth == 0)))
        fn = int(np.sum(~flagged & (truth == 1)))
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        out.append({
            "threshold": round(float(cut), 4),
            "flagged": int(flagged.sum()),
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision * 100.0, 2),
            "recall": round(recall * 100.0, 2),
            "f1": round(f1 * 100.0, 2),
        })
    return out


def select_threshold(
    truth: np.ndarray,
    score: np.ndarray,
    grid: Optional[Sequence[float]] = None,
    max_flag_rate: float = MAX_FLAG_RATE,
) -> tuple[Optional[float], list[dict[str, Any]]]:
    """Pick the operating cut on **validation** data.

    Returns ``(threshold, curve)``; ``threshold`` is ``None`` when the split has
    no labelled anomaly, in which case the caller keeps the forest's own
    ``offset_``.

    H3 (ML audit): the shipped cut used to be
    ``contamination = cfg["anomalies"]["rate"]`` -- the *data generator's*
    injection rate. That is not a decision anyone made about the product; it just
    happened to be 2%, while the true held-out prevalence is 2.873%. The result was
    the worst realistic operating point: recall 20.4% against a best-on-validation
    F1 of ~38%, and on the ``unusually_large`` family -- the one the product most
    needs to catch -- the model scored 7.9% recall while the dumb absolute rule
    it is sold against scored 39.4%.

    Ties go to the **higher** cut (fewer false alarms) via ``>=`` on F1, and
    ``max_flag_rate`` additionally refuses any cut that would flag more than that
    share of validation rows. At a 2.9% prevalence the raw F1 maximum is
    insensitive over a wide range, so without the cap a run of bad luck on 75
    validation users can land the product on an operating point where one in five
    transactions is an "anomaly".
    """
    truth = np.asarray(truth).astype(int)
    score = np.asarray(score, dtype=float)
    if truth.size == 0 or int(truth.sum()) == 0 or truth.min() == truth.max():
        return None, []
    if grid is None:
        grid = [float(cut) for cut in candidate_thresholds(score)]
    curve = threshold_curve(truth, score, grid)
    rate_cap = max(int(np.ceil(max_flag_rate * truth.size)), 1)
    usable = [row for row in curve if row["flagged"] <= rate_cap]
    if not usable:
        return None, curve
    best = max(usable, key=lambda row: (row["f1"], row["threshold"]))
    return float(best["threshold"]), curve


def train(
    features: pd.DataFrame,
    splits: Optional[pd.DataFrame] = None,
    cfg: Optional[Mapping[str, Any]] = None,
    artifact_dir: str | Path = ARTIFACT_DIR,
    contamination: Optional[float] = None,
    params: Optional[Mapping[str, Any]] = None,
    anomaly_labels: Optional[pd.DataFrame] = None,
) -> dict[str, Any]:
    """Fit the forest on the ``train`` users and write the artifact.

    The model is unsupervised: it never sees ``anomaly_labels`` **for fitting**.
    When labels *are* supplied they are used on the ``val`` split only, to pick
    the operating threshold -- never to train the forest and never on ``test``.

    ``contamination`` is the fitting-time hint only; the shipped decision cut
    comes from :func:`select_threshold`.
    """
    if features is None or features.empty:
        raise ValueError("no features to train the anomaly model on")
    options = dict(PARAMS)
    if params:
        options.update(params)
    rate = float(contamination) if contamination is not None else contamination_from(cfg)
    rate = min(max(rate, 1e-4), 0.5)

    train_rows = _slice_split(features, splits, "train")
    if train_rows.empty:
        train_rows = features
    matrix = train_rows[FEATURE_COLUMNS].to_numpy(dtype=float)

    model = IsolationForest(contamination=rate, **options)
    model.fit(matrix)

    # --- operating threshold, chosen on validation only --------------------
    threshold: Optional[float] = None
    curve: list[dict[str, Any]] = []
    threshold_source = "isolation_forest_offset"
    val_summary: dict[str, Any] = {}
    if anomaly_labels is not None and not anomaly_labels.empty and splits is not None:
        val_rows = _slice_split(features, splits, "val")
        if not val_rows.empty:
            labelled = set(anomaly_labels["transaction_id"])
            val_truth = val_rows["transaction_id"].isin(labelled).to_numpy().astype(int)
            if int(val_truth.sum()) > 0:
                val_score = -model.score_samples(val_rows[FEATURE_COLUMNS].to_numpy(dtype=float))
                threshold, curve = select_threshold(val_truth, val_score)
                if threshold is not None:
                    threshold_source = "selected_on_val_f1"
                    chosen = min(
                        curve,
                        key=lambda row: (abs(row["threshold"] - threshold), -row["flagged"]),
                    )
                    val_summary = {
                        "n_rows": int(val_truth.size),
                        "n_anomalies": int(val_truth.sum()),
                        "prevalence_pct": round(100.0 * float(val_truth.mean()), 3),
                        "score_min": round(float(np.min(val_score)), 4),
                        "score_max": round(float(np.max(val_score)), 4),
                        "selected_precision": chosen["precision"],
                        "selected_recall": chosen["recall"],
                        "selected_f1": chosen["f1"],
                        "selected_flag_rate_pct": round(
                            100.0 * chosen["flagged"] / max(int(val_truth.size), 1), 3
                        ),
                        "max_flag_rate_cap_pct": round(100.0 * MAX_FLAG_RATE, 2),
                    }

    directory = Path(artifact_dir)
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, directory / MODEL_FILE)
    meta = {
        "model_name": MODEL_NAME,
        "features": list(FEATURE_COLUMNS),
        "contamination": rate,
        "params": {key: value for key, value in options.items() if key != "n_jobs"},
        "n_train_transactions": int(len(matrix)),
        "offset": float(model.offset_),
        # ``None`` means "use offset_"; kept explicit so a reader never has to
        # guess which cut is live.
        "threshold": threshold,
        "threshold_source": threshold_source,
        "threshold_objective": THRESHOLD_OBJECTIVE,
        "threshold_validation": val_summary,
        "validation_curve": curve,
    }
    (directory / META_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def load(artifact_dir: str | Path = ARTIFACT_DIR) -> Optional[IsolationForest]:
    """Load the fitted forest, or ``None`` when no artifact has been written."""
    path = Path(artifact_dir) / MODEL_FILE
    if not path.exists():
        return None
    try:
        return joblib.load(path)
    except Exception:  # pragma: no cover - a corrupt/stale artifact
        return None


def load_meta(artifact_dir: str | Path = ARTIFACT_DIR) -> dict[str, Any]:
    """The artifact's metadata (empty when it has not been trained yet)."""
    path = Path(artifact_dir) / META_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover
        return {}


def predict(
    features: pd.DataFrame,
    artifact_dir: str | Path = ARTIFACT_DIR,
) -> Optional[AnomalyScores]:
    """Score rows with the forest, or ``None`` when the artifact is missing.

    ``anomaly_score`` is ``-score_samples`` so that *higher means odder*, which is
    what every caller (and the API's ``AnomalyItem.score``) expects.

    ``is_anomaly`` uses the threshold chosen on the **validation** split and
    stored in ``anomaly_meta.json``. When none was stored (no labelled validation
    anomaly) it falls back to the forest's own ``offset_``.

    That fallback is **negated**, because sklearn's ``offset_`` lives in
    ``score_samples`` units and is negative here: it defines
    ``decision_function(X) = score_samples(X) - offset_`` and calls a row an
    outlier when ``score_samples < offset_``, which in this module's orientation
    (``score = -score_samples``, higher = odder) is ``score > -offset_``.
    Comparing the positive ``score`` against the raw negative ``offset_`` is true
    for every row, so the fallback used to mark the entire ledger anomalous
    (measured on the 60-user test dataset: precision 2.82%, recall 100%).
    """
    model = load(artifact_dir)
    if model is None or features is None or features.empty:
        return None
    matrix = features[FEATURE_COLUMNS].to_numpy(dtype=float)
    score = -model.score_samples(matrix)
    stored = load_meta(artifact_dir).get("threshold")
    threshold = float(stored) if isinstance(stored, (int, float)) else -float(model.offset_)
    flag = score >= threshold
    frame = pd.DataFrame(
        {"anomaly_score": score, "is_anomaly": flag}, index=features.index
    )
    return AnomalyScores(frame=frame, source="model", threshold=threshold)


def rule_scores(
    transactions: pd.DataFrame,
    multiplier: float = baselines.DEFAULT_THRESHOLD_MULTIPLIER,
) -> AnomalyScores:
    """The fixed-threshold baseline as :class:`AnomalyScores` (the fallback path).

    Used when no forest artifact is present: the API still answers, the provenance
    ``source`` says ``rule``, and the user is never left without a response.
    """
    scores = baselines.fixed_threshold_scores(transactions, multiplier=multiplier)
    flags = baselines.fixed_threshold_flags(transactions, multiplier=multiplier)
    frame = pd.DataFrame(
        {"anomaly_score": scores, "is_anomaly": flags}, index=transactions.index
    )
    threshold = baselines.fixed_threshold_magnitude(transactions, multiplier)
    return AnomalyScores(frame=frame, source="rule", threshold=threshold)


def _scores_metrics(truth: np.ndarray, flags: np.ndarray, score: np.ndarray) -> dict[str, Any]:
    """Precision/recall/F1 at the operating point, PR-AUC and ranking AUC.

    M3 (ML audit): PR-AUC (average precision) is now reported because at a 2.9%
    positive rate ROC-AUC flatters a rare-event detector -- 0.84 sounds strong
    while precision at the operating point is 35%. The two have to be read
    together.
    """
    precision, recall, f1, _ = precision_recall_fscore_support(
        truth, flags, average="binary", zero_division=0
    )
    auc: Optional[float] = None
    pr_auc: Optional[float] = None
    if truth.min() != truth.max():
        try:
            auc = round(float(roc_auc_score(truth, score)), 4)
        except ValueError:  # pragma: no cover - degenerate scores
            auc = None
        try:
            pr_auc = round(float(average_precision_score(truth, score)), 4)
        except ValueError:  # pragma: no cover
            pr_auc = None
    # FPR / FNR: the two rates that decide whether the card is usable or merely
    # interesting. FPR is the false-alarm tax on a paying user's attention.
    positives = int((truth == 1).sum())
    negatives = int((truth == 0).sum())
    fn = positives - int(((flags == 1) & (truth == 1)).sum())
    fp = int(((flags == 1) & (truth == 0)).sum())
    return {
        "precision": round(float(precision) * 100.0, 2),
        "recall": round(float(recall) * 100.0, 2),
        "f1": round(float(f1) * 100.0, 2),
        "auc": auc,
        "pr_auc": pr_auc,
        "false_positive_rate": round(fp / negatives, 5) if negatives else None,
        "false_negative_rate": round(fn / positives, 5) if positives else None,
        "true_positive_rate": round(float(recall), 5),
        "specificity": round(1 - (fp / negatives), 5) if negatives else None,
    }


def evaluate(
    features: pd.DataFrame,
    transactions: pd.DataFrame,
    anomaly_labels: pd.DataFrame,
    splits: Optional[pd.DataFrame] = None,
    cfg: Optional[Mapping[str, Any]] = None,
    artifact_dir: str | Path = ARTIFACT_DIR,
    threshold_multiplier: float = baselines.DEFAULT_THRESHOLD_MULTIPLIER,
) -> dict[str, Any]:
    """Score the forest against the fixed-threshold rule on the held-out users.

    Truth comes from the ``anomaly_labels`` table (injected rows only); the model
    has never seen it. Both methods are scored on the *same* test rows, with the
    same precision/recall machinery, so "the model beats the rule" is a measured
    statement rather than a claim.

    L1 (ML audit): the returned block also carries a **rule-encoding ablation**.
    ``is_off_hours`` is ``hour <= 5`` and ``is_rapid_repeat`` is
    ``minutes_since_prev <= 20`` -- which are, in this synthetic dataset, exactly
    the generator's own injection rules for the ``unusual_time`` and
    ``rapid_repeat`` families. 100% of injected ``unusual_time`` rows carry the
    flag and 0% of normal rows do, so part of the headline AUC measures recovery
    of the data generator's bookkeeping rather than of behaviour. The ablation
    reports the AUC without those two columns so the headline number cannot be
    over-read.
    """
    if features is None or features.empty:
        raise ValueError("no features to evaluate the anomaly model on")
    # M1: never silently fall back to the whole frame (which includes train
    # users). A mis-configured run must say so rather than publish train metrics
    # under a test label.
    test_features = _slice_split(features, splits, "test")
    if test_features.empty:
        raise ValueError(
            "no test users in the split; refusing to report train metrics as held-out"
        )
    if anomaly_labels is None or anomaly_labels.empty:
        raise ValueError("no anomaly labels to evaluate against")

    labelled = set(anomaly_labels["transaction_id"])
    truth = test_features["transaction_id"].isin(labelled).to_numpy()
    truth_int = truth.astype(int)
    if int(truth_int.sum()) == 0:
        raise ValueError("no labelled anomalies in the evaluated rows")

    model_scores = predict(test_features, artifact_dir)
    if model_scores is None:
        raise ValueError("no anomaly artifact; run backend/scripts/train_all.py first")

    # The baseline is scored on exactly the same rows, matched by id so the two
    # orderings can never drift apart.
    test_transactions = transactions.loc[
        transactions["transaction_id"].isin(set(test_features["transaction_id"]))
    ].copy()
    baseline_flags = baselines.fixed_threshold_flags(
        test_transactions, multiplier=threshold_multiplier
    )
    baseline_scores = baselines.fixed_threshold_scores(
        test_transactions, multiplier=threshold_multiplier
    )
    flag_lookup = dict(zip(test_transactions["transaction_id"], baseline_flags.to_numpy()))
    score_lookup = dict(zip(test_transactions["transaction_id"], baseline_scores.to_numpy()))
    ids = test_features["transaction_id"]
    baseline_flag = ids.map(flag_lookup).fillna(False).astype(bool).to_numpy()
    baseline_score = ids.map(score_lookup).fillna(0.0).astype(float).to_numpy()

    model_metrics = _scores_metrics(
        truth_int,
        model_scores.frame["is_anomaly"].to_numpy().astype(int),
        model_scores.frame["anomaly_score"].to_numpy(dtype=float),
    )
    baseline_metrics = _scores_metrics(truth_int, baseline_flag.astype(int), baseline_score)

    # The plan's core claim, measured directly: the absolute rule cannot see an
    # anomaly that is *small but unusual* for one user, so its recall on the two
    # amount-preserving types should collapse to ~zero while the model still
    # catches some. Reported per injected type, not as an assertion.
    model_flag = model_scores.frame["is_anomaly"].to_numpy().astype(bool)
    type_by_id = dict(zip(anomaly_labels["transaction_id"], anomaly_labels["anomaly_type"]))
    kinds = test_features["transaction_id"].map(type_by_id)
    by_type: dict[str, Any] = {}
    for kind in sorted(str(value) for value in kinds.dropna().unique()):
        mask = kinds.eq(kind).to_numpy()
        total = int(mask.sum())
        if total == 0:
            continue
        by_type[kind] = {
            "count": total,
            "model_recall": round(float(model_flag[mask].sum()) / total * 100.0, 2),
            "baseline_recall": round(float(baseline_flag[mask].sum()) / total * 100.0, 2),
        }

    def _gain(key: str) -> Optional[float]:
        base = baseline_metrics.get(key)
        model = model_metrics.get(key)
        if base is None or model is None:
            return None
        if base == 0:
            return round(float(model), 2) if model else 0.0
        return round((float(model) - float(base)) / float(base) * 100.0, 2)

    return {
        "model_name": MODEL_NAME,
        "baseline_name": baselines.ANOMALY_BASELINE_NAME,
        "n_test_transactions": int(len(test_features)),
        "n_anomalies": int(truth_int.sum()),
        "by_type": by_type,
        "contamination": contamination_from(cfg),
        "threshold": model_scores.threshold,
        "threshold_source": load_meta(artifact_dir).get("threshold_source"),
        "threshold_objective": THRESHOLD_OBJECTIVE,
        "model": model_metrics,
        "baseline": {
            **baseline_metrics,
            "threshold_bdt": round(float(baselines.fixed_threshold_magnitude(
                test_transactions, threshold_multiplier
            )), 2),
        },
        "rule_encoding_ablation": _rule_encoding_ablation(features, splits, test_features, truth_int, artifact_dir),
        "improvement_recall_pct": _gain("recall"),
        "improvement_f1_pct": _gain("f1"),
        "improvement_auc_pct": _gain("auc"),
    }


def _rule_encoding_ablation(
    features: pd.DataFrame,
    splits: Optional[pd.DataFrame],
    test_features: pd.DataFrame,
    truth: np.ndarray,
    artifact_dir: str | Path,
) -> dict[str, Any]:
    """AUC with the two injection-rule columns removed, refitted on train only.

    L1 (ML audit). Reports the honest ceiling so the headline AUC is not read as
    pure behavioural detection.
    """
    dropped = ("is_off_hours", "is_rapid_repeat")
    keep = [c for c in FEATURE_COLUMNS if c not in dropped]
    train_rows = _slice_split(features, splits, "train")
    if train_rows.empty or len(keep) == 0:
        return {"status": "unavailable", "reason": "no training rows"}
    probe = IsolationForest(
        contamination=DEFAULT_CONTAMINATION, **{
            k: v for k, v in PARAMS.items() if k != "contamination"
        }
    )
    probe.fit(train_rows[keep].to_numpy(dtype=float))
    score = -probe.score_samples(test_features[keep].to_numpy(dtype=float))
    if truth.min() == truth.max():  # pragma: no cover - degenerate split
        return {"status": "unavailable", "reason": "single-class test split"}
    return {
        "status": "ok",
        "dropped_features": list(dropped),
        "auc_without_rule_encoding_features": round(float(roc_auc_score(truth, score)), 4),
        "note": (
            "is_off_hours / is_rapid_repeat restate this dataset generator's own "
            "injection rules, so part of the headline AUC measures recovery of the "
            "generator rather than of user behaviour."
        ),
    }

