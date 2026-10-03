"""Train every model with one command (forecast, anomaly detection, consistency signal).

Reads the user-level splits, so the demo user never leaks into training or
evaluation. All three models write their artifact under ``ml/artifacts/`` and are
served directly by the API, and all three have a rule-shaped fallback
(``/anomalies`` degrades to a fixed threshold, ``/credit-readiness`` to a band),
which is why a missing artifact is a degradation and not a failure.

Two blocks in ``metrics.json`` exist to make claims checkable rather than
asserted. ``"anomaly"`` scores the forest and the fixed-threshold rule on the
*same* held-out rows, so "the model beats the rule" is reproducible from the
artifact. ``"fairness"`` slices every model's held-out error by persona, district
and income band and holds each gap to the plan's 15% relative-gap target, so a
group that is served worse is published instead of averaged away.

The fairness pass runs **last**, on purpose: it scores the artifacts the two
model blocks above just wrote, so a skipped model shows up there as an
unavailable family rather than a gap of zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.data import features as user_features
from backend.data import generator
from backend.data import split as split_module
from backend.ml import anomaly, dataset, evaluate, fairness, forecast, signal


def _train_fairness(
    frame,
    db_path: Path,
    splits,
    transactions,
    user_rows,
    artifacts: Path,
    min_users: int,
) -> dict:
    """Slice every model's held-out error by persona, district and income band.

    The demographics come from the ``users`` table and are joined *after*
    scoring, so no group column can reach a model input. Groups too small to
    support a gap are dropped and listed rather than scored; see
    :mod:`backend.ml.fairness` for why that matters at this dataset size.
    """
    groups = user_features.load_users(db_path)[
        ["user_id", "persona", "district", "income_band"]
    ]
    return fairness.evaluate(
        featured=frame.features,
        daily=frame.daily,
        splits=splits,
        group_frame=groups,
        transactions=transactions,
        anomaly_labels=user_features.load_anomaly_labels(db_path),
        user_rows=user_rows,
        artifact_dir=artifacts,
        min_users=min_users,
    )


def _train_anomaly(
    transactions, labels, splits, artifacts: Path, cfg
) -> dict:
    """Fit the forest, then score it against the fixed-threshold rule.

    The anomaly model works per *transaction*, not per day, so it reads the raw
    ledger and builds its own features rather than reusing the forecast frame.
    Training and scoring are separate because only the training half may be
    optional: a missing artifact would leave ``/anomalies`` on the rule, but a
    missing *evaluation* only means the claim is unproven this run, which is
    recorded rather than raised.

    ``labels`` is handed to ``anomaly.train`` **only** so the operating threshold
    can be chosen on the ``val`` split (audit H3). The forest itself stays
    unsupervised: it is never fitted on labels, and ``test`` is never consulted.
    """
    features = anomaly.build_features(transactions)
    anomaly.train(
        features, splits, cfg, artifact_dir=artifacts, anomaly_labels=labels
    )
    try:
        return anomaly.evaluate(
            features, transactions, labels, splits, cfg, artifact_dir=artifacts
        )
    except ValueError as exc:
        # No labelled anomaly in the held-out rows, or the artifact did not
        # land. Either way the model is trained and served; only the
        # model-vs-rule claim is unavailable.
        return {"status": "unavailable", "reason": str(exc)}


def _fairness_gate(metrics: Mapping[str, Any]) -> dict:
    """Hoist a single honest verdict on the fairness families (audit H2).

    The audit found all three families failing the plan's 15% target while
    ``metrics.json`` recorded ``target_met: false`` inside a deeply nested block
    that nothing consumed. The failure was visible only to a reader who went
    looking for it -- which is exactly how a failed responsible-AI check becomes
    an assumed pass. This puts one boolean at the top level, beside the numbers
    it summarises, and warns on stdout.
    """
    block = metrics.get("fairness") or {}
    families = block.get("by_family") or {}
    if not families:
        return {
            "status": "unavailable",
            "all_targets_met": None,
            "reason": block.get("reason", "no fairness block computed"),
        }
    failing = sorted(
        name for name, family in families.items()
        if isinstance(family, dict) and family.get("target_met") is False
    )
    return {
        "status": "checked",
        "all_targets_met": not failing,
        "families_checked": sorted(families),
        "failing_families": failing,
        "worst_relative_gap_pct": round(max(
            (float(f.get("worst_relative_gap_pct") or 0.0) for f in families.values()),
            default=0.0,
        ), 2),
        "target_relative_gap_pct": fairness.TARGET_RELATIVE_GAP_PCT,
        "note": (
            "A failure here is a published finding, not a crash: the models still "
            "train and serve. It must be read before any claim that the system is "
            "group-fair. See docs/ML_AUDIT_REPORT.md."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Train the Shonchoy models.")
    parser.add_argument("--db", default=None, help="path to the SQLite database")
    parser.add_argument("--artifacts", default=None, help="where to write model files")
    parser.add_argument(
        "--skip-signal", action="store_true", help="train the forecaster only"
    )
    parser.add_argument(
        "--skip-anomaly", action="store_true", help="train everything but the forest"
    )
    parser.add_argument(
        "--skip-fairness", action="store_true", help="skip the group-gap audit"
    )
    parser.add_argument(
        "--min-group-users",
        type=int,
        default=fairness.DEFAULT_MIN_USERS,
        help="drop a fairness group below this many held-out users",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db) if args.db else user_features.default_db_path()
    artifacts = Path(args.artifacts) if args.artifacts else forecast.ARTIFACT_DIR
    cfg = generator.load_config()

    frame = dataset.make_frame(db_path, cfg=cfg)
    splits = split_module.load_splits(db_path)
    # The raw ledger is read once and shared by the impact, anomaly, signal and
    # fairness blocks; only the forecast frame is per-day, so it cannot supply it.
    transactions = user_features.load_transactions(db_path)
    info = forecast.train(frame.features, splits, artifact_dir=artifacts)
    metrics = evaluate.evaluate(
        frame.features, frame.daily, splits, artifacts,
        transactions=transactions, cfg=cfg,
        # The PII-free request log the middleware writes beside metrics.json.
        request_log_path=artifacts / "requests.jsonl",
    )
    metrics["val"] = {
        "mae_inflow": round(info["val_mae_inflow"], 2),
        "mae_outflow": round(info["val_mae_outflow"], 2),
        "mae_net": round(info["val_mae_net"], 2),
    }

    if not args.skip_anomaly:
        metrics["anomaly"] = _train_anomaly(
            transactions,
            user_features.load_anomaly_labels(db_path),
            splits,
            artifacts,
            cfg,
        )

    if not args.skip_signal:
        # The signal model is per-user, so it trains on the user feature matrix
        # rather than the forecast frame's daily rows.
        user_rows = user_features.user_features(cfg, transactions)
        user_rows = user_features.attach_split(user_rows, splits)
        labels = user_features.load_user_labels(db_path)
        signal.train(user_rows, labels, splits, artifact_dir=artifacts)
        metrics["signal"] = signal.evaluate(user_rows, labels, splits)
    else:
        user_rows = None

    if not args.skip_fairness:
        if user_rows is None:
            user_rows = user_features.user_features(cfg, transactions)
        metrics["fairness"] = _train_fairness(
            frame, db_path, splits, transactions, user_rows, artifacts,
            max(int(args.min_group_users), 1),
        )
    metrics["responsible_ai_gate"] = _fairness_gate(metrics)

    path = evaluate.write_metrics(metrics, artifacts)
    print(json.dumps(metrics, indent=2))
    print(f"artifacts: {artifacts}  metrics: {path}")
    gate = metrics.get("responsible_ai_gate") or {}
    if gate.get("all_targets_met") is False:
        print(
            "WARNING: fairness target NOT met for: "
            + ", ".join(gate.get("failing_families", []))
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
