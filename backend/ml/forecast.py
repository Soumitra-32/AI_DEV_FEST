"""LightGBM 14-day cash-flow forecaster (ML layer).

Two small regressors — one for inflow, one for outflow — trained on the daily
feature matrix from ``backend.ml.dataset``. Each regressor predicts the
*average daily flow* over the next 14 days; serving spreads that average
across the horizon with each day's calendar shape (weekday/month-end), so the
API always returns 14 per-day rows.

Why the average, not 14 separate models: daily flows are noisy (a wage day
next to six quiet days), while the 14-day total is what the savings solver
actually consumes. One robust average plus a calendar spread beats fourteen
noisy day-models, and it trains in seconds on a laptop.

Anti-circularity: trained on ``train`` users, tuned on ``val``, reported on
``test`` (user-level splits from ``backend/data/split.py``). The demo user is
never in any split.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

import lightgbm as lgb
import numpy as np
import pandas as pd

from .dataset import FORECAST_FEATURE_COLUMNS, HORIZON_DAYS

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
INFLOW_MODEL = "forecast_inflow.txt"
OUTFLOW_MODEL = "forecast_outflow.txt"
META_FILE = "forecast_meta.json"

#: The prior each booster corrects. The model is trained on the *residual*
#: from the user's own trailing 4-week mean, not on the raw level.
#:
#: Why: with ~500 users and noisy daily flows, a plain level fit shrinks an
#: individual's prediction toward the population mean. That is invisible in the
#: aggregate metric but wrong for exactly the user we care about — Rahim's own
#: trailing mean says ৳1,433/day of income, the raw model said ৳1,240, and the
#: ৳6k/month difference decides whether his plan is feasible. Boosting on the
#: residual keeps the user's own level as the floor and lets the model add only
#: what it can actually explain (calendar shape, month-to-date budget state).
ANCHOR_COLUMNS: dict[str, str] = {
    "inflow": "roll_28_inflow",
    "outflow": "roll_28_outflow",
}

PARAMS: dict[str, Any] = {
    "objective": "regression",
    "metric": "mae",
    "verbosity": -1,
    "num_leaves": 63,
    "min_data_in_leaf": 40,
    "feature_fraction": 0.85,
    "bagging_fraction": 0.85,
    "bagging_freq": 1,
    "lambda_l1": 0.05,
    "lambda_l2": 0.05,
    "seed": 7,
    "deterministic": True,
    "num_threads": 1,
}

N_BOOST_ROUND = 800
EARLY_STOPPING = 100


@dataclass(frozen=True)
class HorizonTargets:
    """14-day mean inflow/outflow per feature date (one row per date)."""

    frame: pd.DataFrame


def horizon_targets(daily: pd.DataFrame, horizon_days: int = HORIZON_DAYS) -> HorizonTargets:
    """Mean daily inflow/outflow over the next ``horizon_days`` days."""
    frame = daily.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["user_id", "date"], kind="stable").reset_index(drop=True)
    grouped = frame.groupby("user_id", sort=False)
    inflow_cols = [f"_fwd_in_{h}" for h in range(1, horizon_days + 1)]
    outflow_cols = [f"_fwd_out_{h}" for h in range(1, horizon_days + 1)]
    for horizon in range(1, horizon_days + 1):
        frame[f"_fwd_in_{horizon}"] = grouped["inflow_bdt"].shift(-horizon)
        frame[f"_fwd_out_{horizon}"] = grouped["outflow_bdt"].shift(-horizon)
    frame = frame.dropna(subset=inflow_cols + outflow_cols).reset_index(drop=True)
    frame["target_inflow"] = frame[inflow_cols].mean(axis=1)
    frame["target_outflow"] = frame[outflow_cols].mean(axis=1)
    return HorizonTargets(frame=frame)


def train(
    featured: pd.DataFrame,
    splits: pd.DataFrame,
    horizon_days: int = HORIZON_DAYS,
    artifact_dir: str | Path = ARTIFACT_DIR,
    params: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Train inflow/outflow regressors; return paths and validation MAE."""
    targets = horizon_targets(featured, horizon_days).frame
    merged = targets.merge(splits, on="user_id", how="inner")
    options = dict(PARAMS)
    if params:
        options.update(params)

    def _fit(flow: str, extra: Optional[Mapping[str, Any]] = None) -> tuple[lgb.Booster, float, float]:
        target = f"target_{flow}"
        anchor_column = ANCHOR_COLUMNS[flow]
        anchor = merged[anchor_column].to_numpy(dtype=float)
        residual = merged[target].to_numpy(dtype=float) - anchor
        use = dict(options)
        if extra:
            use.update(extra)
        train_rows = merged["split"].eq("train").to_numpy()
        valid_rows = merged["split"].eq("val").to_numpy()
        train_set = lgb.Dataset(merged.loc[train_rows, FORECAST_FEATURE_COLUMNS], label=residual[train_rows])
        valid_set = lgb.Dataset(merged.loc[valid_rows, FORECAST_FEATURE_COLUMNS], label=residual[valid_rows], reference=train_set)
        booster = lgb.train(
            use, train_set, num_boost_round=N_BOOST_ROUND,
            valid_sets=[valid_set],
            callbacks=[lgb.early_stopping(EARLY_STOPPING, verbose=False)],
        )
        # score the *level* the API will serve, not the residual
        valid_labels = merged.loc[valid_rows, target].to_numpy(dtype=float)
        preds = anchor[valid_rows] + booster.predict(merged.loc[valid_rows, FORECAST_FEATURE_COLUMNS])
        mae = float(np.mean(np.abs(preds - valid_labels)))
        # Bias correction (mean residual measured on the *validation* users only),
        # so any remaining systematic offset is removed without touching ``test``.
        bias = float(np.mean(valid_labels - preds))
        return booster, mae, bias

    inflow_model, inflow_mae, inflow_bias = _fit("inflow")
    outflow_model, outflow_mae, outflow_bias = _fit("outflow")

    directory = Path(artifact_dir)
    directory.mkdir(parents=True, exist_ok=True)
    inflow_model.save_model(str(directory / INFLOW_MODEL))
    outflow_model.save_model(str(directory / OUTFLOW_MODEL))
    meta = {
        "features": list(FORECAST_FEATURE_COLUMNS),
        "anchor_columns": dict(ANCHOR_COLUMNS),
        "horizon_days": horizon_days,
        "params": options,
        "bias_inflow": inflow_bias,
        "bias_outflow": outflow_bias,
        "val_mae_inflow": inflow_mae,
        "val_mae_outflow": outflow_mae,
    }
    (directory / META_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {
        "artifact_dir": str(directory),
        "val_mae_inflow": inflow_mae,
        "val_mae_outflow": outflow_mae,
        "bias_inflow": inflow_bias,
        "bias_outflow": outflow_bias,
    }


def load(artifact_dir: str | Path = ARTIFACT_DIR) -> tuple[lgb.Booster, lgb.Booster, dict]:
    """Load the trained boosters and their metadata."""
    directory = Path(artifact_dir)
    inflow = lgb.Booster(model_file=str(directory / INFLOW_MODEL))
    outflow = lgb.Booster(model_file=str(directory / OUTFLOW_MODEL))
    meta = json.loads((directory / META_FILE).read_text(encoding="utf-8"))
    return inflow, outflow, meta


def predict_mean(
    features: pd.DataFrame,
    artifact_dir: str | Path = ARTIFACT_DIR,
) -> pd.DataFrame:
    """Predict the 14-day mean daily inflow/outflow for each feature row.

    Each booster predicts a *residual* from the user's own trailing 4-week mean,
    so the served prediction is ``anchor + residual + validation bias``. The
    level can therefore never be shrunk toward the population mean, and
    predictions are clipped at zero because a negative daily flow is not a thing.
    """
    inflow, outflow, meta = load(artifact_dir)
    matrix = features[FORECAST_FEATURE_COLUMNS]
    anchors = meta.get("anchor_columns", ANCHOR_COLUMNS)
    mean_inflow = (
        features[anchors["inflow"]].to_numpy(dtype=float)
        + inflow.predict(matrix) + float(meta.get("bias_inflow", 0.0))
    )
    mean_outflow = (
        features[anchors["outflow"]].to_numpy(dtype=float)
        + outflow.predict(matrix) + float(meta.get("bias_outflow", 0.0))
    )
    return pd.DataFrame({
        "mean_inflow": np.clip(mean_inflow, 0.0, None),
        "mean_outflow": np.clip(mean_outflow, 0.0, None),
    })

