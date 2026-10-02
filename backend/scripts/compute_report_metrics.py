"""Supplementary REPORT metrics: anomaly, fairness, fees, backtest.

Reads the trained artifacts from ``train_all.py`` (forecast + signal) and adds
what it does not cover:

1. anomaly IsolationForest train + evaluate (model vs fixed rule, test users)
2. fairness gaps: forecast net-MAE by persona/income, anomaly flag-rate and
   signal-band gaps by persona/district/income_band (<=15% relative = pass)
3. fee-savings simulation from the documented 1.85% rate (measured volumes x
   assumed 20-50% adoption — an assumption, stated as one)
4. goal backtest: plan on months 1-4, check months 5-6; naive vs solver
   false-feasible rate (plan.txt section 4: where the naive plan fails)

Everything is measured on held-out TEST users (demo user excluded by split).
Prints one JSON document whose numbers go straight into REPORT.md.

Usage:
    backend/.venv/bin/python backend/scripts/compute_report_metrics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.data import features as user_features
from backend.data import generator, split as split_module
from backend.ml import anomaly, baselines, dataset, evaluate, signal

ARTIFACTS = Path(evaluate.ARTIFACT_DIR)


def pct_gap(values: list[float]) -> float | None:
    """Max relative gap (%) across groups; None when undefined."""
    vals = [v for v in values if v is not None and np.isfinite(v)]
    if len(vals) < 2 or min(vals) == 0:
        return None
    return round((max(vals) - min(vals)) / abs(min(vals)) * 100.0, 2)


def abs_gap(values: list[float]) -> float | None:
    """Max absolute gap across groups (percentage-points for rates)."""
    vals = [v for v in values if v is not None and np.isfinite(v)]
    if len(vals) < 2:
        return None
    return round(max(vals) - min(vals), 4)


def main() -> int:
    db = user_features.default_db_path()
    cfg = generator.load_config()
    tx = user_features.load_transactions(db)
    splits = split_module.load_splits(db)
    out: dict = {"db": str(db)}

    # --- 1. anomaly: train (train users) + evaluate (test users) ---
    feats = anomaly.build_features(tx)
    labels = _anomaly_labels(db)
    anomaly.train(feats, splits, cfg, artifact_dir=str(ARTIFACTS))
    out["anomaly"] = anomaly.evaluate(feats, tx, labels, splits, cfg, artifact_dir=str(ARTIFACTS))

    # --- 2a. forecast fairness: net MAE by persona + income_band ---
    frame = dataset.make_frame(db)
    out["fairness_forecast"] = _forecast_gaps(frame.features, frame.daily, splits, tx)

    # --- 2b. anomaly flag-rate gaps + 2c. signal band gaps ---
    out["fairness_anomaly"] = _flag_gaps(feats, splits, tx)
    out["fairness_signal"] = _signal_gaps(db, splits)

    # --- 3. fees + 4. backtest ---
    out["fees"] = _fee_stats(tx, cfg)
    out["backtest"] = _backtest(tx, splits)

    print(json.dumps(out, indent=2, default=str))
    (ARTIFACTS / "report_metrics.json").write_text(json.dumps(out, indent=2, default=str))
    return 0


def _anomaly_labels(db) -> pd.DataFrame:
    import sqlite3

    with sqlite3.connect(f"file:{Path(db).as_posix()}?mode=ro", uri=True) as c:
        try:
            return pd.read_sql_query("SELECT * FROM anomaly_labels", c)
        except Exception:
            return pd.DataFrame()


def _forecast_gaps(featured, daily, splits, tx) -> dict:
    """Per-group net MAE via the tested evaluate() on group-filtered splits."""
    users = tx[["user_id", "persona", "income_band"]].drop_duplicates()
    result: dict = {}
    for dim in ("persona", "income_band"):
        per_group: dict = {}
        for name, grp in users.groupby(dim):
            g_test = splits.merge(grp[["user_id"]], on="user_id", how="inner")
            g_test = g_test.loc[g_test["split"].eq("test")]
            if g_test["user_id"].nunique() < 3:
                continue
            try:
                ev = evaluate.evaluate(featured, daily, g_test, ARTIFACTS)
                per_group[str(name)] = {
                    "mae_net": ev["net"]["model"]["mae"],
                    "improvement_vs_best_pct": ev["improvement_vs_best_pct"]["net"],
                    "test_users": ev["test_users"],
                }
            except Exception as exc:
                per_group[str(name)] = {"error": str(exc)[:100]}
        maes = [v["mae_net"] for v in per_group.values() if "mae_net" in v]
        result[dim] = {
            "groups": per_group,
            "max_relative_gap_pct": pct_gap(maes),
            "max_absolute_gap_bdt": abs_gap(maes),
        }
    return result


def _flag_gaps(feats: pd.DataFrame, splits, tx) -> dict:
    """Flag-rate gap: share of test transactions flagged, by group."""
    test_users = set(splits.loc[splits["split"].eq("test"), "user_id"])
    f = feats.loc[feats["user_id"].isin(test_users)].copy()
    scored = anomaly.predict(f, artifact_dir=str(ARTIFACTS))
    f["flagged"] = scored.frame["is_anomaly"].to_numpy() if scored is not None else False
    meta = tx[["transaction_id", "persona", "district", "income_band"]].drop_duplicates()
    f = f.merge(meta, on="transaction_id", how="left")
    result: dict = {}
    for dim in ("persona", "district", "income_band"):
        rates = {str(n): round(float(g["flagged"].mean()), 4) for n, g in f.groupby(dim)}
        result[dim] = {
            "flag_rate": rates,
            "max_relative_gap_pct": pct_gap(list(rates.values())),
            "max_absolute_gap_pp": abs_gap([v * 100 for v in rates.values()]),
        }
    return result


def _signal_gaps(db, splits) -> dict:
    """Band-distribution gap: share 'Strong' by group on test users."""
    users = user_features.user_features(user_features.load_config(), user_features.load_transactions(db))
    users = user_features.attach_split(users, splits)
    # user_features() leaves demographics NaN (numeric-only matrix); join them
    # from transactions for the group split (reporting only, models unaffected).
    demo = (
        user_features.load_transactions(db)[["user_id", "persona", "district", "income_band"]]
        .drop_duplicates()
    )
    users = users.drop(columns=["persona", "district", "income_band"], errors="ignore").merge(
        demo, on="user_id", how="left"
    )
    labels = user_features.load_user_labels(db)
    test = users.loc[users["split"].eq("test")].copy()
    if test.empty:
        return {"note": "no test users"}
    loaded = signal.load(str(ARTIFACTS))
    if loaded is None:
        test["band"] = test.apply(lambda r: signal.rule_band(signal.feature_mapping(r.to_dict()))[0], axis=1)
    else:
        model, scaler = loaded
        mat = signal.build_matrix(test)
        proba = model.predict_proba(scaler.transform(mat))[:, 1]
        test["band"] = [signal.band_for(p) for p in proba]
    result: dict = {}
    for dim in ("persona", "district", "income_band"):
        shares = {str(n): round(float((g["band"] == "Strong").mean()), 4) for n, g in test.groupby(dim)}
        result[dim] = {
            "strong_share": shares,
            "max_relative_gap_pct": pct_gap(list(shares.values())),
            "max_absolute_gap_pp": abs_gap([v * 100 for v in shares.values()]),
        }
    result["test_users"] = int(len(test))
    return result


def _fee_stats(tx: pd.DataFrame, cfg) -> dict:
    cash = tx.loc[tx["channel"].eq("cash_out")].copy()
    cash["month"] = pd.to_datetime(cash["timestamp"]).dt.to_period("M").astype(str)
    per_user_month = cash.groupby(["user_id", "month"])["fee_bdt"].sum()
    monthly = per_user_month.groupby("user_id").mean()
    rate = float(cfg.get("fee_rates", {}).get("cash_out", 1.85)) / 100.0
    vol = cash.groupby(["user_id", cash["month"]])["amount_bdt"].sum().groupby("user_id").mean()
    return {
        "fee_rate_assumed_pct": round(rate * 100, 2),
        "users_with_cash_outs": int(monthly.shape[0]),
        "mean_monthly_fee_all_cashout_users_bdt": round(float(monthly.mean()), 2),
        "mean_monthly_cashout_volume_bdt": round(float(vol.mean()), 2),
        "rahim_monthly_fee_bdt": round(float(monthly.get("rahim", 0.0)), 2),
        "potential_saving_100pct_bdt": round(float(monthly.mean()), 2),
        "potential_saving_20_50pct_bdt": [
            round(float(monthly.mean()) * 0.2, 2),
            round(float(monthly.mean()) * 0.5, 2),
        ],
        "note": "volumes measured on synthetic data; 20-50% adoption is an assumption, not measured",
    }


def _backtest(tx: pd.DataFrame, splits) -> dict:
    """Plan on months 1-4, check months 5-6. Goal 10000 over 2 months (5000/mo).

    AI plan: feasible_monthly = mean(monthly net, months 1-4) - std (buffer).
    Naive plan: always feasible (goal/months by definition).
    Metric: false-feasible rate = said feasible but actual months 5-6 avg < 5000.
    """
    t = tx.copy()
    t["timestamp"] = pd.to_datetime(t["timestamp"])
    t["month_rank"] = t["timestamp"].dt.to_period("M").rank(method="dense").astype(int) - 1
    net = t.assign(net=t["amount_bdt"].where(t["type"].eq("income"), -t["amount_bdt"]))
    monthly = net.groupby(["user_id", "month_rank"])["net"].sum().unstack(fill_value=0.0)
    test_users = [u for u in splits.loc[splits["split"].eq("test"), "user_id"] if u in monthly.index]
    req, ai_ff, naive_ff, ai_n, hits = 5000.0, 0, 0, 0, 0
    for u in test_users:
        row = monthly.loc[u]
        early, late = row.iloc[:4], row.iloc[4:6]
        feas = float(early.mean() - early.std()) if len(early) else 0.0
        actual = float(late.mean()) if len(late) else 0.0
        naive_ok = actual >= req
        if not naive_ok:
            naive_ff += 1
        if feas >= req:
            ai_n += 1
            if actual >= req:
                hits += 1
            else:
                ai_ff += 1
    n = max(len(test_users), 1)
    return {
        "test_users": len(test_users),
        "required_monthly_bdt": req,
        "ai_feasible_users": ai_n,
        "ai_hit_rate_given_feasible_pct": round(hits / max(ai_n, 1) * 100, 1),
        "ai_false_feasible_rate_pct": round(ai_ff / n * 100, 1),
        "naive_false_feasible_rate_pct": round(naive_ff / n * 100, 1),
        "note": "simulation on synthetic data; solver buffer = 1 std of monthly net",
    }


if __name__ == "__main__":
    sys.exit(main())
