"""LightGBM 14-day cash-flow forecaster (ML layer).

Two small regressors — one for inflow, one for outflow — trained on the daily
feature matrix from ``backend.ml.dataset``. Each regressor predicts the
*average daily flow* over the next 14 days; serving spreads that average
across the horizon with each day's calendar shape (weekday/month-end), so the
API always returns 14 per-day rows.

A **third regressor predicts net directly**, and the served per-day net comes
from it rather than from ``inflow - outflow``. That is not redundancy: inflow
and outflow are each predicted to within ~5% of their own level, but the two
errors are independent, so they do not cancel when subtracted and the implied
net is several times worse than either flow. The savings solver consumes net
and nothing else, so net is the quantity that has to be modelled and measured
in its own right. ``evaluate.py`` scores it against the same baselines and
``metrics.json`` reports it beside the flow metrics so the gap cannot hide.

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
from typing import Any, Mapping, Optional, TypedDict

import lightgbm as lgb
import numpy as np
import pandas as pd

from .dataset import FORECAST_FEATURE_COLUMNS, HORIZON_DAYS

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
INFLOW_MODEL = "forecast_inflow.txt"
OUTFLOW_MODEL = "forecast_outflow.txt"
NET_MODEL = "forecast_net.txt"
META_FILE = "forecast_meta.json"


class LoadedModels(TypedDict, total=False):
    """What :func:`load` returns: boosters keyed by flow, plus ``_meta``.

    ``total=False`` because an artifact directory may be missing any booster —
    an older one has no ``forecast_net.txt``, and a partially-written directory
    should degrade rather than raise. ``_meta`` is always present when ``load``
    returns, but it shares the mapping so there is one object to pass around.
    """

    inflow: lgb.Booster
    outflow: lgb.Booster
    net: lgb.Booster
    _meta: dict[str, Any]

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
#:
#: ``net`` is anchored the same way, on ``roll_28_net``. Net is the one flow the
#: savings solver reads, so it gets its own model and its own anchor rather than
#: being inherited as a difference of two other models.
ANCHOR_COLUMNS: dict[str, str] = {
    "inflow": "roll_28_inflow",
    "outflow": "roll_28_outflow",
    "net": "roll_28_net",
}

#: The flows the API serves and ``metrics.json`` scores.
FLOWS = ("inflow", "outflow", "net")

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
    """14-day mean inflow/outflow/net per feature date (one row per date)."""

    frame: pd.DataFrame


def horizon_targets(daily: pd.DataFrame, horizon_days: int = HORIZON_DAYS) -> HorizonTargets:
    """Mean daily inflow/outflow/net over the next ``horizon_days`` days.

    ``target_net`` is the mean of the realised daily net over the same window,
    *not* ``target_inflow - target_outflow``: the sum of each day's net is the
    sum of its two flows, so the two agree on totals but the net series has
    cancellation built in and is far less noisy to learn.
    """
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
    # Subtracted by *position*, not by name: the inflow and lookahead frames
    # carry disjoint column names (_fwd_in_1 vs _fwd_out_1), so a plain
    # frame[cols_a] - frame[cols_b] aligns on the union of names and yields an
    # all-NaN column. That trains a booster on nothing while still "succeeding",
    # which is exactly the silent failure the guard below exists to catch.
    frame["target_net"] = (
        frame[inflow_cols].to_numpy(dtype=float)
        - frame[outflow_cols].to_numpy(dtype=float)
    ).mean(axis=1)
    targets = frame[["target_inflow", "target_outflow", "target_net"]]
    if targets.isna().any().any():
        raise ValueError("horizon_targets produced NaN targets; refusing to train on them")
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
    net_model, net_mae, net_bias = _fit("net")

    directory = Path(artifact_dir)
    directory.mkdir(parents=True, exist_ok=True)
    inflow_model.save_model(str(directory / INFLOW_MODEL))
    outflow_model.save_model(str(directory / OUTFLOW_MODEL))
    net_model.save_model(str(directory / NET_MODEL))
    meta = {
        "features": list(FORECAST_FEATURE_COLUMNS),
        "anchor_columns": dict(ANCHOR_COLUMNS),
        "horizon_days": horizon_days,
        "params": options,
        "bias_inflow": inflow_bias,
        "bias_outflow": outflow_bias,
        "bias_net": net_bias,
        "val_mae_inflow": inflow_mae,
        "val_mae_outflow": outflow_mae,
        "val_mae_net": net_mae,
    }
    (directory / META_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {
        "artifact_dir": str(directory),
        "val_mae_inflow": inflow_mae,
        "val_mae_outflow": outflow_mae,
        "val_mae_net": net_mae,
        "bias_inflow": inflow_bias,
        "bias_outflow": outflow_bias,
        "bias_net": net_bias,
    }


def load(artifact_dir: str | Path = ARTIFACT_DIR) -> LoadedModels:
    """Load the trained boosters, keyed by flow, plus their metadata under ``_meta``.

    Artifacts written before the net model existed have no ``forecast_net.txt``;
    that is tolerated so an older artifact directory still serves a forecast
    (with net falling back to the difference of the two flow models) instead of
    failing the request.

    Callers must go through the mapping (``models["inflow"]``), never unpack it:
    a 3-tuple unpack would silently yield the dict's *keys*.
    """
    directory = Path(artifact_dir)
    boosters: LoadedModels = {}
    for flow, filename in (("inflow", INFLOW_MODEL), ("outflow", OUTFLOW_MODEL), ("net", NET_MODEL)):
        path = directory / filename
        if path.exists():
            boosters[flow] = lgb.Booster(model_file=str(path))
    boosters["_meta"] = json.loads((directory / META_FILE).read_text(encoding="utf-8"))
    return boosters


def predict_mean(
    features: pd.DataFrame,
    artifact_dir: str | Path = ARTIFACT_DIR,
) -> pd.DataFrame:
    """Predict the 14-day mean daily inflow/outflow/net for each feature row.

    Each booster predicts a *residual* from the user's own trailing 4-week mean,
    so the served prediction is ``anchor + residual + validation bias``. The
    level can therefore never be shrunk toward the population mean, and
    predictions are clipped at zero because a negative daily flow is not a
    thing.

    ``mean_net`` comes from the net booster, not from ``mean_inflow -
    mean_outflow``. The two flows are each accurate but their errors are
    independent, so their difference accumulates both; the solver reads net, so
    net gets its own prediction. Without a net artifact the difference is used
    and ``net_source`` says so, which keeps the gap visible instead of silent.
    """
    boosters = load(artifact_dir)
    # ``_meta`` is written on every successful load, but the TypedDict marks it
    # optional so a partial artifact directory still type-checks; the empty
    # fallback keeps a missing metadata file from turning into a KeyError.
    meta = boosters.get("_meta") or {}
    matrix = features[FORECAST_FEATURE_COLUMNS]
    anchors = meta.get("anchor_columns", ANCHOR_COLUMNS)

    def _level(flow: str) -> np.ndarray:
        booster = boosters.get(flow)
        anchor = features[anchors[flow]].to_numpy(dtype=float)
        if booster is None:
            return anchor
        return anchor + booster.predict(matrix) + float(meta.get(f"bias_{flow}", 0.0))

    mean_inflow = _level("inflow")
    mean_outflow = _level("outflow")
    net_source = "model"
    if "net" in boosters:
        mean_net = _level("net")
        # a trained booster can still emit NaN (an all-NaN training label
        # produces a one-tree model that predicts 0 with a NaN bias). Falling
        # back keeps the request correct, and the reported source makes the
        # downgrade visible instead of silently serving a broken number.
        if not np.isfinite(mean_net).all():
            mean_net = mean_inflow - mean_outflow
            net_source = "difference"
    else:
        mean_net = mean_inflow - mean_outflow
        net_source = "difference"
    return pd.DataFrame({
        "mean_inflow": np.clip(mean_inflow, 0.0, None),
        "mean_outflow": np.clip(mean_outflow, 0.0, None),
        # net is deliberately NOT clipped: a day can legitimately lose money
        "mean_net": mean_net,
        "net_source": net_source,
    })

