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

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
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

#: Inverse-regularisation strengths searched on the **validation** split.
C_GRID: tuple[float, ...] = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0)

#: H4 (ML audit): ``class_weight="balanced"`` was applied to a 42/58 split.
#: It was justified as "handle the imbalance", but there is no meaningful
#: imbalance here -- and ``balanced`` re-weights the loss so the fitted
#: probabilities no longer estimate the real 42% prior. Since the bands are cut
#: from those probabilities, that distorted which people landed in which band.
#: Left in the code as an explicit, documented opt-in rather than the default.
PARAMS: dict[str, Any] = {
    "C": 1.0,
    "max_iter": 1000,
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
def _sign_conflicts(
    model: Any,
    train_rows: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Features whose fitted coefficient contradicts their own univariate direction.

    H1 (ML audit): with an exactly collinear pair in the design matrix
    (``fee_per_month_bdt`` was a deterministic multiple of
    ``cash_out_volume_per_month_bdt``), the fit used one as a suppressor for the
    other and produced a confidently wrong story -- ``income_mean_bdt`` carries a
    **positive** univariate correlation with the label (+0.148, and the positive
    rate rises monotonically across income quartiles) yet was fitted at -0.757,
    so the card told users "your income weakens your stability".

    Only features with |r| >= 0.10 are checked: a weak marginal correlation says
    nothing about the sign a multivariate model should assign, so flagging those
    would be noise.
    """
    y = train_rows[LABEL_COLUMN].to_numpy(dtype=int)
    if len(np.unique(y)) < 2:
        return []
    coefficients = np.asarray(model.coef_, dtype=float).reshape(-1)
    numeric = train_rows[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    conflicts: list[dict[str, Any]] = []
    for index, column in enumerate(FEATURE_COLUMNS):
        if index >= len(coefficients):
            break
        values = numeric[column].to_numpy(dtype=float)
        if values.std() == 0:
            continue
        r = float(np.corrcoef(values, y)[0, 1])
        if abs(r) < 0.10:
            continue
        if np.sign(r) != np.sign(coefficients[index]) and abs(coefficients[index]) > 1e-9:
            conflicts.append({
                "feature": column,
                "univariate_r": round(r, 4),
                "coefficient": round(float(coefficients[index]), 6),
            })
    return conflicts


def select_bands(
    model: Any,
    scaler: Any,
    val_rows: pd.DataFrame,
) -> list[tuple[float, str]]:
    """Pick the two band cut-offs on the **validation** split.

    H4 (ML audit): the cut-offs were hardcoded at 0.40 / 0.60 with no recorded
    justification and were never checked against held-out data. They are now
    placed at the validation terciles, which is what a *descriptive* three-way
    band should do -- the model is not a classifier whose output should be forced
    onto some external target prior, and a band nobody can fall into is useless.

    Falls back to :data:`DEFAULT_BANDS` when validation is unusable.
    """
    if val_rows is None or val_rows.empty:
        return list(DEFAULT_BANDS)
    scores = model.predict_proba(scaler.transform(build_matrix(val_rows)))[:, 1]
    lower_q, upper_q = np.quantile(scores, [1 / 3, 2 / 3])
    lower = float(np.round(np.clip(lower_q, 0.05, 0.90), 2))
    upper = float(np.round(np.clip(upper_q, lower + 0.05, 0.95), 2))
    if not (0.0 < lower < upper < 1.0):
        return list(DEFAULT_BANDS)
    return [(lower, "Building"), (upper, "Steady")]


def _select_c(
    c_search: list[dict[str, Any]],
    options: Mapping[str, Any],
    train_matrix: np.ndarray,
    train_labels: pd.Series | pd.DataFrame,
    y_val: np.ndarray,
    x_val: np.ndarray,
    seed: int = 7,
    min_gain: float = 0.02,
) -> tuple[float, str]:
    """Choose ``C``, but only move off the default for a *meaningful* gain.

    H4 follow-up (audit verification): the first implementation picked the
    smallest ``C`` within 0.005 AUC of the validation best, which selected
    ``C=0.05`` and cost **0.035 test AUC** (0.7518 vs 0.7864). The cause was
    chasing validation noise: with 75 validation users the AUC standard error is
    roughly 0.07, so the whole 0.73-0.75 spread across the grid is
    statistically flat, and the argmax was an artefact of which fold the noise
    fell into.

    The rule here is therefore deliberately conservative: keep the scikit-learn
    default unless some candidate beats it by more than ``min_gain`` **and** the
    improvement survives a bootstrap. Preferring the *larger* ``C`` among
    statistical ties keeps the model closer to unregularised, which is where the
    measured test AUC actually lives.
    """
    default_c = float(options.get("C", 1.0))
    if not c_search:
        return default_c, "default (empty search)"

    def auc_for(candidate: float) -> float:
        return float(roc_auc_score(y_val, auc_scores(options, candidate, train_matrix, train_labels, x_val)))

    base_auc = auc_for(default_c)
    best_row = max(c_search, key=lambda row: row["val_auc"])
    gain = float(best_row["val_auc"]) - base_auc

    if gain <= min_gain:
        return default_c, (
            f"default C={default_c:g} kept: best validation gain {gain:+.4f} "
            f"is below the {min_gain:g} materiality threshold, so the grid spread "
            "is validation noise on a small split"
        )

    # Bootstrap the gain so the decision rests on more than one noisy point.
    # Both models are fitted **once**; only the evaluation is resampled.
    challenger = auc_scores(options, best_row["C"], train_matrix, train_labels, x_val)
    incumbent = auc_scores(options, default_c, train_matrix, train_labels, x_val)
    rng = np.random.default_rng(seed)
    n = len(y_val)
    deltas: list[float] = []
    for _ in range(200):
        idx = rng.integers(0, n, n)
        if len(np.unique(y_val[idx])) < 2:
            continue
        try:
            # ``challenger[idx]`` / ``incumbent[idx]`` are numpy scalars, not
            # Python floats; ``deltas`` is a ``list[float]``, so the difference
            # is materialised as a real float rather than a ``np.floating``.
            deltas.append(
                float(
                    roc_auc_score(y_val[idx], challenger[idx])
                    - roc_auc_score(y_val[idx], incumbent[idx])
                )
            )
        except ValueError:  # pragma: no cover - degenerate resample
            continue
    if not deltas:  # pragma: no cover
        return default_c, "default kept (bootstrap produced no valid resample)"
    lower = float(np.quantile(deltas, 0.05))
    if lower <= 0:
        return default_c, (
            f"default C={default_c:g} kept: the {gain:+.4f} validation gain for "
            f"C={best_row['C']:g} does not survive bootstrap (5th pct {lower:+.4f})"
        )
    return float(best_row["C"]), (
        f"selected C={best_row['C']:g}: validation gain {gain:+.4f} over the default "
        f"C={default_c:g}, bootstrap 5th pct {lower:+.4f}"
    )


def auc_scores(options, candidate, train_matrix, train_labels, x_val) -> np.ndarray:
    """Validation scores for one ``C``, fitted once.

    ``train_labels`` may arrive as a DataFrame slice, so it is squeezed to a 1-D
    array here rather than at every call site.
    """
    y = np.asarray(
        train_labels[LABEL_COLUMN].to_numpy()
        if isinstance(train_labels, pd.DataFrame)
        else train_labels
    ).reshape(-1)
    probe = LogisticRegression(**{**options, "C": candidate})
    probe.fit(train_matrix, y)
    return probe.predict_proba(x_val)[:, 1]


def train(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    splits: Optional[pd.DataFrame] = None,
    artifact_dir: str | Path = ARTIFACT_DIR,
    params: Optional[Mapping[str, Any]] = None,
    bands: Optional[Sequence[tuple[float, str]]] = None,
) -> dict[str, Any]:
    """Fit the classifier on ``train`` users and write the artifact.

    ``C`` and the band cut-offs are chosen on the **validation** split (H4).
    ``test`` is never consulted. Passing ``bands`` pins the cut-offs explicitly,
    which is what the tests do for a deterministic configuration.

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

    val_rows = _slice_split(frame, splits, "val") if splits is not None else frame.iloc[0:0]

    # --- C chosen on validation, never on test -----------------------------
    chosen_c = float(options["C"])
    c_search: list[dict[str, Any]] = []
    selection_note = "default (no usable validation split)"
    if not val_rows.empty and val_rows[LABEL_COLUMN].nunique() > 1:
        y_val = val_rows[LABEL_COLUMN].to_numpy(dtype=int)
        x_val = scaler.transform(build_matrix(val_rows))
        for candidate in C_GRID:
            probe = LogisticRegression(**{**options, "C": candidate})
            probe.fit(matrix, train_rows[LABEL_COLUMN].to_numpy())
            c_search.append({
                "C": candidate,
                "val_auc": round(float(roc_auc_score(y_val, probe.predict_proba(x_val)[:, 1])), 4),
            })
        chosen_c, selection_note = _select_c(c_search, options, matrix, train_rows, y_val, x_val)

    model = LogisticRegression(**{**options, "C": chosen_c})
    model.fit(matrix, train_rows[LABEL_COLUMN].to_numpy())

    if bands:
        final_bands = list(bands)
        bands_source = "explicit"
    else:
        final_bands = select_bands(model, scaler, val_rows)
        bands_source = (
            "selected_on_val_terciles" if not val_rows.empty else "default_no_validation"
        )

    artifact = Path(artifact_dir)
    artifact.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "scaler": scaler}, artifact / MODEL_FILE)

    info: dict[str, Any] = {
        "model_name": MODEL_NAME,
        "features": FEATURE_COLUMNS,
        "bands": [[float(cutoff), name] for cutoff, name in final_bands],
        "bands_source": bands_source,
        "C": chosen_c,
        "C_source": "selected_on_val" if c_search else "default",
        "C_selection_note": selection_note,
        "C_search": c_search,
        "trained_rows": int(len(train_rows)),
        "positive_rate": round(float(train_rows[LABEL_COLUMN].mean()), 4),
        "intercept": round(float(model.intercept_[0]), 6),
        "coefficients": {
            name: round(float(value), 6)
            for name, value in zip(FEATURE_COLUMNS, model.coef_[0])
        },
        # H1: a coefficient contradicting its own univariate correlation means a
        # suppressor is still present, so it is recorded, not shipped silently.
        "sign_conflicts": _sign_conflicts(model, train_rows),
        **reproducibility_stamp(),
    }
    (artifact / META_FILE).write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def reproducibility_stamp() -> dict[str, Any]:
    """Dataset fingerprint, config hash and library versions for an artifact.

    M5 (ML audit): artifacts previously recorded no provenance beyond their own
    parameters, so nobody could tell whether a reported AUC came from this data
    in this environment. The live environment already drifts from the pins in
    ``requirements.txt`` (``numpy`` 2.0.0 installed vs 2.5.3 pinned), which is
    exactly the situation a stamp is meant to make visible.
    """
    import platform

    stamp: dict[str, Any] = {
        "library_versions": {},
        "python": platform.python_version(),
    }
    for name in ("numpy", "pandas", "sklearn", "lightgbm"):
        try:
            module = __import__(name)
            stamp["library_versions"][name] = getattr(module, "__version__", "unknown")
        except Exception:  # pragma: no cover - optional at runtime
            stamp["library_versions"][name] = "not_installed"
    try:
        from backend.data import generator as _generator

        cfg = _generator.load_config()
        stamp["config_hash"] = hashlib.sha256(
            json.dumps(cfg, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:16]
        stamp["generator_version"] = (cfg.get("meta") or {}).get("generator_version")
        db_path = _generator.resolve_db_path(cfg)
        if db_path.exists():
            stamp["dataset_path"] = db_path.name
            stamp["dataset_bytes"] = int(db_path.stat().st_size)
    except Exception:  # pragma: no cover - config unavailable
        pass
    return stamp


#: H1/L2: a value outside this range is not a real user's transaction, it is a
#: corrupt or crafted input. Rejecting it lets the service fall back to the rule
#: band instead of returning a confident answer derived from nonsense.
#: Keys are validated against :data:`FEATURE_COLUMNS` at import time below, so a
#: stale entry cannot linger after a feature is removed.
FEATURE_ABS_LIMITS: dict[str, float] = {
    "income_mean_bdt": 5_000_000.0,
    "spend_mean_bdt": 5_000_000.0,
    "cash_out_volume_per_month_bdt": 5_000_000.0,
    "balance_mean_bdt": 50_000_000.0,
    "balance_min_bdt": 50_000_000.0,
}
FEATURE_ABS_LIMITS = {
    key: value for key, value in FEATURE_ABS_LIMITS.items() if key in FEATURE_COLUMNS
}


def is_plausible(row: Mapping[str, float]) -> bool:
    """True when every feature is finite and inside :data:`FEATURE_ABS_LIMITS`.

    An all-zero row is *not* plausible: it means the features were never built,
    and the model would confidently answer from a fabricated average user.
    """
    values: list[float] = []
    for name in FEATURE_COLUMNS:
        try:
            value = float(row.get(name, float("nan")))
        except (TypeError, ValueError):
            return False
        if not np.isfinite(value):
            return False
        limit = FEATURE_ABS_LIMITS.get(name)
        if limit is not None and abs(value) > limit:
            return False
        values.append(value)
    return bool(values) and any(value != 0.0 for value in values)


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
    model = payload["model"]
    if hasattr(model, "predict_proba") and not hasattr(model, "multi_class"):
        model.multi_class = "auto"
    return model, payload["scaler"]


def load_meta(artifact_dir: str | Path = ARTIFACT_DIR) -> dict[str, Any]:
    """The artifact's metadata (empty when it has not been trained yet)."""
    path = Path(artifact_dir) / META_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover
        return {}


def _shap(model: Any, scaler: Any, scaled: np.ndarray) -> tuple[np.ndarray, float]:
    """Exact SHAP values and the base log-odds, for a linear model.

    For a linear model the SHAP value *is* the exact decomposition, so there is
    nothing to approximate and nothing to import:

    ``phi_i = w_i * x_i`` and ``base = intercept``

    where ``x`` is the **standardised** row the model was actually fitted on.

    Two failure modes are deliberately avoided here:

    * ``shap.LinearExplainer`` is not usable in this setup. It only accepts the
      Independent / Partition / Impute maskers, so pairing it with
      ``shap.kmeans`` (as an earlier revision did) raises ``NotImplementedError``
      on shap 0.52, and ``shap.kmeans`` on a single row raises ``ValueError``.
      Both were swallowed by a bare ``except``, which meant the exact path
      never ran.
    * The old fallback subtracted ``scaler.mean_`` from an **already
      standardised** matrix, i.e. it subtracted the raw training mean a second
      time. That produced ``base_value = -19849`` with contributions of ~23,000
      against a true log-odds of ~1.0. It *looked* correct because the two
      errors cancelled in ``base + sum(phi)``, so only an inspection of the
      individual contributions could catch it.

    The additivity property holds exactly: ``base + sum(contributions)``
    reconstructs this user's log-odds, and therefore the probability the band
    was chosen from.
    """
    weights = np.asarray(model.coef_, dtype=float).reshape(-1)
    intercept = np.asarray(model.intercept_, dtype=float).reshape(-1)
    values = np.asarray(scaled, dtype=float) * weights.reshape(1, -1)
    base = float(intercept[0]) if intercept.size else 0.0
    return values, base


#: Advertised in the response so a reader knows exactly how the numbers were
#: produced. This is the closed-form decomposition, which is *exact* for the
#: logistic regression actually in use -- not an approximation, and not the
#: `shap` package, which cannot be used with this model/masker combination.
SHAP_METHOD = "exact_linear_decomposition"


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


def shap_explanation(
    model: Any,
    scaler: Any,
    row: RowLike,
    bands: Sequence[tuple[float, str]] = DEFAULT_BANDS,
) -> dict[str, Any]:
    """The full ranked explanation for one user: base value and every contribution.

    Deliberately complete rather than top-3. :func:`shap_factors` keeps the three
    biggest for the card, but an audit needs the whole list to check that the
    contributions actually add up to the log-odds that chose the band.
    """
    values = [list(feature_mapping(row).values())]
    scaled = scaler.transform(build_matrix(pd.DataFrame(values, columns=FEATURE_COLUMNS)))
    contributions, base = _shap(model, scaler, scaled)
    log_odds = float(base + contributions[0].sum())

    ranked = sorted(
        zip(FEATURE_COLUMNS, contributions[0]), key=lambda kv: abs(float(kv[1])), reverse=True
    )
    features: list[dict[str, Any]] = []
    for rank, (name, value) in enumerate(ranked, start=1):
        higher_is_stable = name in HIGHER_IS_STABLE
        # "Improves" means "moves towards stable", not "a bigger number is nicer",
        # so the direction has to be read per feature.
        improving = value > 0 if higher_is_stable else value < 0
        features.append(
            {
                "feature": name,
                "contribution": round(float(value), 4),
                "direction": "improves" if improving else "weakens",
                "rank": rank,
            }
        )
    return {
        "method": SHAP_METHOD,
        "base_value": round(float(base), 4),
        "log_odds": round(log_odds, 4),
        "band_cutoffs": {name: float(cutoff) for cutoff, name in bands},
        "features": features,
    }


def shap_factors(
    model: Any,
    scaler: Any,
    row: RowLike,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """The strongest factors for one user, biggest contribution first.

    Each factor says which way the feature pushes this user and by roughly how
    much in log-odds. That is what makes the band arguable instead of magic, and
    it is the reason this signal is a model rather than a rule. The signed values
    behind these magnitudes are in :func:`shap_explanation`.
    """
    explanation = shap_explanation(model, scaler, row)
    return [
        {
            "feature": item["feature"],
            "direction": item["direction"],
            "magnitude": round(abs(float(item["contribution"])), 4),
        }
        for item in explanation["features"][: max(int(top_k), 1)]
    ]


def predict(
    features: pd.DataFrame,
    artifact_dir: str | Path = ARTIFACT_DIR,
    top_k: int = 3,
) -> Optional[SignalPrediction]:
    """Band one user from the trained model, or ``None`` without the artifact.

    ``None`` means "fall back to the rule band", never "error": the caller is
    expected to say so in the provenance. It is also returned for an
    **implausible** feature row (L2) -- see :func:`is_plausible`.
    """
    loaded = load(artifact_dir)
    if loaded is None or features is None or features.empty:
        return None
    # L2 (ML audit): refuse to answer from an implausible row. Before this, a
    # user whose features were all zero (or a crafted 1e18 income) got a
    # confident band computed from a fabricated average user. Returning ``None``
    # lets the caller degrade to the rule band and say so in its provenance.
    if not is_plausible(feature_mapping(features.iloc[0])):
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


def predict_bands(
    features: pd.DataFrame,
    artifact_dir: str | Path = ARTIFACT_DIR,
) -> Optional[pd.DataFrame]:
    """Band and probability for *every* row at once, or ``None`` without the artifact.

    :func:`predict` answers for one user because that is all the card needs, and
    it spends a SHAP explainer on the single row it returns. The fairness pass
    needs the band of every held-out user and no explanations, so this scores the
    whole cohort in one transform. Same model, same bands, same cut-offs -- the
    two paths cannot disagree about which band a user is in.
    """
    loaded = load(artifact_dir)
    if loaded is None or features is None or features.empty:
        return None
    model, scaler = loaded
    bands = _bands_from_meta(load_meta(artifact_dir))
    probabilities = model.predict_proba(scaler.transform(build_matrix(features)))[:, 1]
    return pd.DataFrame(
        {
            "probability": [float(value) for value in probabilities],
            "band": [band_for(value, bands) for value in probabilities],
        },
        index=features.index,
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


def shap_importance(
    features: pd.DataFrame,
    artifact_dir: str | Path = ARTIFACT_DIR,
    top_k: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Cohort-level SHAP importance: mean |contribution| per feature, ranked.

    The per-user :func:`shap_explanation` answers "why this band"; this answers
    "which habits does the band actually move on, across everyone", which is what
    the ``/metrics`` page plots. Mean absolute contribution is the right summary
    for that question: it measures how much a feature moves the log-odds in
    either direction, averaged over the cohort, with the sign reported
    separately so a feature that consistently weakens is not hidden by its size.

    ``None`` without the artifact, matching every other entry point here.
    """
    loaded = load(artifact_dir)
    if loaded is None or features is None or features.empty:
        return None
    model, scaler = loaded
    scaled = scaler.transform(build_matrix(features))
    contributions, base = _shap(model, scaler, scaled)
    mean_abs = np.abs(contributions).mean(axis=0)
    mean_signed = contributions.mean(axis=0)

    order = np.argsort(-mean_abs)
    limit = len(FEATURE_COLUMNS) if top_k is None else max(int(top_k), 1)
    ranked = [
        {
            "feature": FEATURE_COLUMNS[index],
            "mean_abs_contribution": round(float(mean_abs[index]), 4),
            "mean_contribution": round(float(mean_signed[index]), 4),
            "direction": (
                "improves"
                if (mean_signed[index] > 0) == (FEATURE_COLUMNS[index] in HIGHER_IS_STABLE)
                else "weakens"
            ),
            "rank": rank,
        }
        for rank, index in enumerate(order[:limit], start=1)
    ]
    return {
        "method": SHAP_METHOD,
        "base_value": round(float(base), 4),
        "rows": int(len(features)),
        "total_mean_abs": round(float(mean_abs.sum()), 4),
        "features": ranked,
    }


#: Bin edges for the calibration table. Fixed (not quantile-based) so two runs
#: are directly comparable and so every bin means the same probability range.
CALIBRATION_BINS = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


def calibration_table(truth: np.ndarray, scores: np.ndarray) -> list[dict[str, Any]]:
    """Predicted vs observed rate per probability bin, with the sample count.

    The bands are cut from these probabilities, so a mis-calibrated model
    silently mislabels people. Reporting the table makes that visible instead of
    leaving it to be assumed away.
    """
    if truth is None or scores is None or len(truth) == 0:
        return []
    frame = pd.DataFrame({"score": np.asarray(scores, dtype=float), "y": np.asarray(truth, dtype=int)})
    frame["bin"] = pd.cut(frame["score"], list(CALIBRATION_BINS), include_lowest=True)
    out: list[dict[str, Any]] = []
    for edge, part in frame.groupby("bin", observed=True):
        out.append({
            "bin": str(edge),
            "n": int(len(part)),
            "predicted": round(float(part["score"].mean()), 4),
            "observed": round(float(part["y"].mean()), 4),
        })
    return out


def _baseline_auc(truth: np.ndarray, frame: pd.DataFrame) -> tuple[Optional[float], Optional[str]]:
    """AUC of a one-feature logistic regression, on that feature's strongest correlation.

    M2 (ML audit): the previous baseline was ``np.random.default_rng(seed).random(n)``.
    A uniform draw has AUC 0.5 by construction, so quoting it as a comparator
    told the reader nothing and made the model look better than any real
    alternative. A single-feature model is the honest floor: it is the best any
    one habit can do on its own.
    """
    numeric = frame[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y = np.asarray(truth, dtype=int)
    best_feature: Optional[str] = None
    best_auc = 0.5
    for column in FEATURE_COLUMNS:
        values = numeric[column].to_numpy(dtype=float)
        if values.size == 0 or not np.isfinite(values).all():
            continue
        if values.std() == 0 or np.allclose(values, values[0]):
            continue  # constant column carries no signal
        try:
            auc = roc_auc_score(y, values)
        except ValueError:  # pragma: no cover - single-class
            continue
        # Orientation-free: a feature that separates the classes *downwards* is
        # just as useful as one that separates them upwards.
        if abs(auc - 0.5) > abs(best_auc - 0.5):
            best_auc, best_feature = float(auc), column
    if best_feature is None:
        return None, None
    return max(best_auc, 1.0 - best_auc), best_feature


def evaluate(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    splits: Optional[pd.DataFrame] = None,
    artifact_dir: str | Path = ARTIFACT_DIR,
    seed: int = 7,
) -> dict[str, Any]:
    """Held-out AUC for the model and for a real baseline.

    Both numbers are reported because "AUC 0.81" only means something next to a
    comparator. The comparator is a **logistic regression on the single feature
    with the strongest absolute univariate correlation** -- not random noise,
    which the previous revision used and which made the baseline meaningless: a
    uniform draw scores ~0.50 by construction and therefore flatters the model.

    The demo user sits in the ``demo`` split, so Rahim is never part of the test
    cohort either.
    """
    frame = _labeled(features, labels)
    # M1: never silently fall back to the training split. A run with no test
    # users must report "unavailable" rather than publish train metrics under a
    # test label.
    test_rows = _slice_split(frame, splits, "test")
    if test_rows.empty:
        return {
            "status": "unavailable",
            "reason": "no test users in the split; refusing to report train metrics as held-out",
            "auc": None, "baseline_auc": None, "rows": 0,
        }
    if test_rows[LABEL_COLUMN].nunique() < 2:
        return {
            "status": "unavailable",
            "reason": "single-class test split",
            "auc": None, "baseline_auc": None, "rows": int(len(test_rows)),
        }

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

    baseline_auc, baseline_feature = _baseline_auc(truth, test_rows)
    importance = shap_importance(test_rows, artifact_dir)
    return {
        "auc": round(float(roc_auc_score(truth, scores)), 4),
        "baseline_auc": None if baseline_auc is None else round(baseline_auc, 4),
        "baseline_feature": baseline_feature,
        "baseline_name": (
            f"logistic_regression_on_{baseline_feature}"
            if baseline_feature else "unavailable"
        ),
        "rows": int(len(test_rows)),
        "positive_rate": round(float(truth.mean()), 4),
        "calibration": calibration_table(truth, scores),
        "brier_score": round(float(brier_score_loss(truth, scores)), 4),
        "pr_auc": round(float(average_precision_score(truth, scores)), 4),
        # Cohort SHAP importance, so "which habit moves the band most" is a
        # measured table rather than a story told about the top-3 cards.
        "shap_importance": importance,
    }