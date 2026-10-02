"""Consistency signal (ML layer): LogisticRegression + SHAP, Phase 7.

The split this module exists to justify: *the consistency signal is a model*, so
that it can be scored (AUC) and explained (SHAP). The savings plan, fee switch
and pressure days stay plain Python rules because they must be exact, and the
LLM never touches this band.

Three deliberate constraints:

* **A band, never a score.** The serving path returns ``Building`` / ``Steady`` /
  ``Strong``. A probability exists for evaluation, but it is never shown to the
  user and never becomes a lending decision (``backend/tests/test_signal.py``
  asserts that).
* **The label is held out.** ``is_stable_next_2_months`` comes from a latent
  variable plus noise and shocks (``backend/data/labels.py``), never from this
  feature matrix, so the AUC means something rather than an identity.
* **Degradation over failure.** Entry points return ``None``/``{}`` rather than
  raising when the artifact is missing, so the API falls back to the
  observational band instead of returning a 500.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from backend.data import features as user_features

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_FILE = "signal_logreg.joblib"
META_FILE = "signal_meta.json"
MODEL_NAME = "logistic_regression_consistency"

#: Model inputs: the shared, label-free user features.
FEATURE_COLUMNS: list[str] = list(user_features.FEATURE_COLUMNS)

#: Label read only for training and evaluation, never for serving.
LABEL_COLUMN = "is_stable_next_2_months"

#: Probability cut-offs for the three bands, lowest first.
DEFAULT_BANDS: tuple[tuple[float, str], ...] = ((0.40, "Building"), (0.60, "Steady"))
TOP_BAND = "Strong"

PARAMS: dict[str, Any] = {
    "C": 1.0,
    "max_iter": 1000,
    "class_weight": "balanced",
    "solver": "lbfgs",
}

#: Features where a bigger number plainly means "more stable".
HIGHER_IS_STABLE = frozenset(
    {"income_days_per_month", "balance_mean_bdt", "balance_min_bdt", "months_observed"}
)


def band_for(probability: float, bands: Sequence[tuple[float, str]] = DEFAULT_BANDS) -> str:
    """Map a probability to a band using the given cut-offs."""
    for cutoff, name in bands:
        if float(probability) < float(cutoff):
            return name
    return TOP_BAND


@dataclass(frozen=True)
class SignalPrediction:
    """One user's signal. ``probability`` is for evaluation, not for display."""

    probability: float
    band: str
    source: str
    factors: list[dict[str, Any]]


def build_matrix(features: pd.DataFrame) -> np.ndarray:
    """Feature rows -> numeric matrix, with any missing value coerced to 0."""
    frame = features[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    return frame.fillna(0.0).to_numpy(dtype=float)


def _slice_split(features: pd.DataFrame, splits: Optional[pd.DataFrame], name: str) -> pd.DataFrame:
    """Rows whose user is in the named split (all rows when no split is given)."""
    if splits is None or splits.empty or "split" not in splits.columns:
        return features
    wanted = set(splits.loc[splits["split"].eq(name), "user_id"])
    if not wanted:
        return features.iloc[0:0]
    return features.loc[features["user_id"].isin(wanted)]


def _labeled(features: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Features joined to the user label, ready to train on."""
    if features is None or features.empty:
        raise ValueError("no features to train the signal model on")
    if labels is None or labels.empty:
        raise ValueError("no user labels to train the signal model on")
    merged = features.merge(labels[["user_id", LABEL_COLUMN]], on="user_id", how="inner")
    if merged.empty:
        raise ValueError("no users appear in both features and labels")
    merged[LABEL_COLUMN] = merged[LABEL_COLUMN].astype(int)
    return merged


def _bands_from_meta(meta: Mapping[str, Any]) -> list[tuple[float, str]]:
    """The cut-offs stored with the artifact, falling back to the defaults."""
    raw = meta.get("bands")
    if not raw:
        return list(DEFAULT_BANDS)
    return [(float(cutoff), str(name)) for cutoff, name in raw]
def train(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    splits: Optional[pd.DataFrame] = None,
    artifact_dir: str | Path = ARTIFACT_DIR,
    params: Optional[Mapping[str, Any]] = None,
    bands: Sequence[tuple[float, str]] = DEFAULT_BANDS,
) -> dict[str, Any]:
    """Fit the classifier on ``train`` users and write the artifact.

    When ``splits`` is given the fit uses train users only, so the demo user and
    the held-out cohorts stay untouched.
    """
    frame = _labeled(features, labels)
    train_rows = _slice_split(frame, splits, "train")
    if train_rows.empty:
        train_rows = frame
    if train_rows[LABEL_COLUMN].nunique() < 2:
        raise ValueError("the training split has a single class; cannot fit a classifier")

    options = dict(PARAMS)
    if params:
        options.update(params)

    scaler = StandardScaler()
    matrix = scaler.fit_transform(build_matrix(train_rows))
    model = LogisticRegression(**options)
    model.fit(matrix, train_rows[LABEL_COLUMN].to_numpy())

    artifact = Path(artifact_dir)
    artifact.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "scaler": scaler}, artifact / MODEL_FILE)

    info: dict[str, Any] = {
        "model_name": MODEL_NAME,
        "features": FEATURE_COLUMNS,
        "bands": [[float(cutoff), name] for cutoff, name in bands],
        "trained_rows": int(len(train_rows)),
        "positive_rate": round(float(train_rows[LABEL_COLUMN].mean()), 4),
        "coefficients": {
            name: round(float(value), 6)
            for name, value in zip(FEATURE_COLUMNS, model.coef_[0])
        },
    }
    (artifact / META_FILE).write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def load(artifact_dir: str | Path = ARTIFACT_DIR) -> Optional[tuple[Any, Any]]:
    """``(model, scaler)`` when the artifact exists, else ``None``."""
    path = Path(artifact_dir) / MODEL_FILE
    if not path.exists():
        return None
    try:
        payload = joblib.load(path)
    except Exception:  # pragma: no cover - a corrupt artifact must not 500
        return None
    if not isinstance(payload, dict) or "model" not in payload or "scaler" not in payload:
        return None
    return payload["model"], payload["scaler"]


def load_meta(artifact_dir: str | Path = ARTIFACT_DIR) -> dict[str, Any]:
    """The artifact's metadata (empty when it has not been trained yet)."""
    path = Path(artifact_dir) / META_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover
        return {}


def _shap_values(model: Any, scaler: Any, scaled: np.ndarray) -> np.ndarray:
    """SHAP values for a linear model.

    ``shap.LinearExplainer`` is exact here, so each value is that feature's real
    contribution to the log-odds. If the optional dependency is missing the
    closed form ``x*w + b`` gives the same number, so the card degrades rather
    than disappears.
    """
    try:
        import shap  # noqa: PLC0415 - optional dependency, imported lazily

        explainer = shap.LinearExplainer(model, shap.kmeans(scaled, min(10, len(scaled))))
        return np.asarray(explainer.shap_values(scaled), dtype=float).reshape(len(scaled), -1)
    except Exception:  # pragma: no cover - only reached without shap
        weights = np.asarray(model.coef_).reshape(-1)
        bias = float(np.asarray(model.intercept_).reshape(-1)[0])
        return scaled * weights + bias


#: Anything this module will accept as "one user's numbers". ``pd.Series`` is
#: named explicitly because pandas does *not* register it as a ``Mapping``
#: subclass -- it quacks like one (``row[name]``, ``row.get``), but the type
#: checkers are right to refuse it. Without this union every call site would need
#: a ``.to_dict()`` cast.
RowLike = Union["pd.Series", Mapping[str, float]]


def feature_mapping(row: RowLike) -> dict[str, float]:
    """The model's own inputs from any row-like object, as ``{str: float}``.

    Two jobs. It narrows the key type to ``str`` so the result is a real
    ``Mapping[str, float]``, and it coerces a missing or NaN feature to ``0.0``
    -- the same default :func:`build_matrix` applies, so the SHAP values and the
    model's own input for this user can never disagree about what the number was.
    """
    values: dict[str, float] = {}
    for name in FEATURE_COLUMNS:
        try:
            value = float(row[name]) if name in row else 0.0
        except (TypeError, ValueError):
            value = 0.0
        values[name] = 0.0 if pd.isna(value) else value
    return values


def shap_factors(
    model: Any,
    scaler: Any,
    row: RowLike,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """The strongest factors for one user, biggest contribution first.

    Each factor says which way the feature pushes this user and by roughly how
    much in log-odds. That is what makes the band arguable instead of magic, and
    it is the reason this signal is a model rather than a rule.
    """
    values = [list(feature_mapping(row).values())]
    scaled = scaler.transform(build_matrix(pd.DataFrame(values, columns=FEATURE_COLUMNS)))
    contributions = _shap_values(model, scaler, scaled)[0]

    ranked = sorted(zip(FEATURE_COLUMNS, contributions), key=lambda kv: abs(kv[1]), reverse=True)
    factors: list[dict[str, Any]] = []
    for name, value in ranked[: max(int(top_k), 1)]:
        higher_is_stable = name in HIGHER_IS_STABLE
        # "Improves" means "moves towards stable", not "a bigger number is nicer",
        # so the direction has to be read per feature.
        improving = value > 0 if higher_is_stable else value < 0
        factors.append(
            {
                "feature": name,
                "direction": "improves" if improving else "weakens",
                "magnitude": round(abs(float(value)), 4),
            }
        )
    return factors
def predict(
    features: pd.DataFrame,
    artifact_dir: str | Path = ARTIFACT_DIR,
    top_k: int = 3,
) -> Optional[SignalPrediction]:
    """Band one user from the trained model, or ``None`` without the artifact.

    ``None`` means "fall back to the rule band", never "error": the caller is
    expected to say so in the provenance.
    """
    loaded = load(artifact_dir)
    if loaded is None or features is None or features.empty:
        return None
    model, scaler = loaded
    bands = _bands_from_meta(load_meta(artifact_dir))

    probability = float(model.predict_proba(scaler.transform(build_matrix(features)))[0, 1])
    return SignalPrediction(
        probability=probability,
        band=band_for(probability, bands),
        source="model",
        factors=shap_factors(model, scaler, features.iloc[0], top_k=top_k),
    )


def rule_band(row: Mapping[str, float]) -> tuple[str, list[dict[str, Any]]]:
    """The fallback when there is no model: a band from three readable facts.

    Deliberately simple and inspectable. It is a reading of observed behaviour,
    not a prediction, and the provenance says ``rule`` so the card cannot imply
    more than it knows.
    """
    factors: list[dict[str, Any]] = []
    points = 0

    income_days = float(row.get("income_days_per_month", 0.0) or 0.0)
    if income_days >= 2:
        points += 1
    factors.append(
        {
            "feature": "income_days_per_month",
            "direction": "improves" if income_days >= 2 else "weakens",
            "magnitude": round(income_days, 2),
        }
    )

    shortfall_days = float(row.get("shortfall_days_per_month", 0.0) or 0.0)
    if shortfall_days < 1:
        points += 1
    factors.append(
        {
            "feature": "shortfall_days_per_month",
            "direction": "improves" if shortfall_days < 1 else "weakens",
            "magnitude": round(shortfall_days, 2),
        }
    )

    fee_share = float(row.get("fee_share_of_income", 0.0) or 0.0)
    if fee_share < 0.01:
        points += 1
    factors.append(
        {
            "feature": "fee_share_of_income",
            "direction": "improves" if fee_share < 0.01 else "weakens",
            "magnitude": round(fee_share, 4),
        }
    )

    band = "Building" if points <= 1 else "Steady" if points == 2 else "Strong"
    return band, factors


def evaluate(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    splits: Optional[pd.DataFrame] = None,
    artifact_dir: str | Path = ARTIFACT_DIR,
    seed: int = 7,
) -> dict[str, Any]:
    """Held-out AUC for the model and for a random baseline.

    Both numbers are reported because "AUC 0.61" only means something next to the
    trivial comparator. The demo user sits in the ``demo`` split, so Rahim is
    never part of the test cohort either.
    """
    frame = _labeled(features, labels)
    test_rows = _slice_split(frame, splits, "test")
    if test_rows.empty:
        test_rows = frame
    if test_rows[LABEL_COLUMN].nunique() < 2:
        return {"auc": None, "baseline_auc": None, "rows": int(len(test_rows))}

    truth = test_rows[LABEL_COLUMN].to_numpy()
    loaded = load(artifact_dir)
    if loaded is None:
        return {
            "auc": None,
            "baseline_auc": None,
            "rows": int(len(test_rows)),
            "note": "model not trained",
        }
    model, scaler = loaded
    scores = model.predict_proba(scaler.transform(build_matrix(test_rows)))[:, 1]

    noise = np.random.default_rng(seed).random(len(truth))
    return {
        "auc": round(float(roc_auc_score(truth, scores)), 4),
        "baseline_auc": round(float(roc_auc_score(truth, noise)), 4),
        "rows": int(len(test_rows)),
        "positive_rate": round(float(truth.mean()), 4),
    }