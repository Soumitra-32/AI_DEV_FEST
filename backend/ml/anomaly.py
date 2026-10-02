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
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score

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

#: How far back a gap is capped when a user has no previous transaction.
MAX_GAP_MINUTES = 1440.0

DEFAULT_CONTAMINATION = 0.02

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


def build_features(transactions: pd.DataFrame) -> pd.DataFrame:
    """Per-user behaviour features for every transaction row.

    Returns a frame with the same index as ``transactions`` and the columns in
    :data:`FEATURE_COLUMNS`, all numeric (no NaNs). Per-user statistics are
    computed inside each user only — a neighbour's spending never sets the bar.
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

    # --- per-user amount reference (outflow rows only) ---------------------
    reference = frame.loc[~is_income]
    by_user = reference.groupby("user_id")["amount_bdt"]
    user_mean = frame["user_id"].map(by_user.mean()).astype(float)
    user_std = frame["user_id"].map(by_user.std()).astype(float)
    fallback_mean = float(amount[~is_income].mean()) if bool((~is_income).any()) else float(amount.mean())
    if not np.isfinite(fallback_mean):
        fallback_mean = 0.0
    user_mean = user_mean.fillna(fallback_mean)

    safe_std = user_std.where(user_std.gt(0))
    zscore = ((amount - user_mean) / safe_std).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    positive_mean = user_mean.where(user_mean.gt(0))
    over_mean = (amount / positive_mean).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    # --- time shape --------------------------------------------------------
    hour = frame["timestamp"].dt.hour.astype(float)
    ref_hours = frame.loc[~is_income].assign(_hour=hour)
    typical = frame["user_id"].map(ref_hours.groupby("user_id")["_hour"].median())
    typical = typical.fillna(float(hour.median()) if len(hour) else 12.0)
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
    """Expected anomaly share, from the dataset config when it is available."""
    if cfg is None:
        return float(default)
    try:
        return float(cfg["anomalies"]["rate"])
    except (KeyError, TypeError, ValueError):
        return float(default)


def train(
    features: pd.DataFrame,
    splits: Optional[pd.DataFrame] = None,
    cfg: Optional[Mapping[str, Any]] = None,
    artifact_dir: str | Path = ARTIFACT_DIR,
    contamination: Optional[float] = None,
    params: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Fit the forest on the ``train`` users and write the artifact.

    The model is unsupervised: it never sees ``anomaly_labels``. ``contamination``
    is the expected anomalous share (the generator injects ~2%), which sets the
    ``predict == -1`` boundary; when ``splits`` is given the fit uses train users
    only, so ``val`` and ``test`` stay untouched.
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
    """
    model = load(artifact_dir)
    if model is None or features is None or features.empty:
        return None
    matrix = features[FEATURE_COLUMNS].to_numpy(dtype=float)
    score = -model.score_samples(matrix)
    flag = model.predict(matrix) == -1
    frame = pd.DataFrame(
        {"anomaly_score": score, "is_anomaly": flag}, index=features.index
    )
    return AnomalyScores(frame=frame, source="model", threshold=float(model.offset_))


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
    """Precision/recall/F1 at the operating point, plus ranking AUC."""
    precision, recall, f1, _ = precision_recall_fscore_support(
        truth, flags, average="binary", zero_division=0
    )
    auc: Optional[float] = None
    if truth.min() != truth.max():
        try:
            auc = round(float(roc_auc_score(truth, score)), 4)
        except ValueError:  # pragma: no cover - degenerate scores
            auc = None
    return {
        "precision": round(float(precision) * 100.0, 2),
        "recall": round(float(recall) * 100.0, 2),
        "f1": round(float(f1) * 100.0, 2),
        "auc": auc,
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
    """
    if features is None or features.empty:
        raise ValueError("no features to evaluate the anomaly model on")
    test_features = _slice_split(features, splits, "test")
    if test_features.empty:
        test_features = features
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
        "model": model_metrics,
        "baseline": {
            **baseline_metrics,
            "threshold_bdt": round(float(baselines.fixed_threshold_magnitude(
                test_transactions, threshold_multiplier
            )), 2),
        },
        "improvement_recall_pct": _gain("recall"),
        "improvement_f1_pct": _gain("f1"),
        "improvement_auc_pct": _gain("auc"),
    }

