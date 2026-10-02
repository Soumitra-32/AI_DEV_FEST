"""Train every model with one command (forecast and consistency signal).

Reads the user-level splits, so the demo user never leaks into training or
evaluation. Phase 8 extends this to the anomaly model and the metrics page; the
consistency signal is here because it is the other model whose artifact the API
serves directly (``/signal`` degrades to a rule band without it).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.data import features as user_features
from backend.data import split as split_module
from backend.ml import dataset, evaluate, forecast, signal


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Train the Shonchoy models.")
    parser.add_argument("--db", default=None, help="path to the SQLite database")
    parser.add_argument("--artifacts", default=None, help="where to write model files")
    parser.add_argument(
        "--skip-signal", action="store_true", help="train the forecaster only"
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db) if args.db else user_features.default_db_path()
    artifacts = Path(args.artifacts) if args.artifacts else forecast.ARTIFACT_DIR

    frame = dataset.make_frame(db_path)
    splits = split_module.load_splits(db_path)
    info = forecast.train(frame.features, splits, artifact_dir=artifacts)
    metrics = evaluate.evaluate(frame.features, frame.daily, splits, artifacts)
    metrics["val"] = {
        "mae_inflow": round(info["val_mae_inflow"], 2),
        "mae_outflow": round(info["val_mae_outflow"], 2),
        "mae_net": round(info["val_mae_net"], 2),
    }

    if not args.skip_signal:
        # The signal model is per-user, so it trains on the user feature matrix
        # rather than the forecast frame's daily rows.
        user_rows = user_features.user_features(
            user_features.load_config(), user_features.load_transactions(db_path)
        )
        user_rows = user_features.attach_split(user_rows, splits)
        labels = user_features.load_user_labels(db_path)
        signal.train(user_rows, labels, splits, artifact_dir=artifacts)
        metrics["signal"] = signal.evaluate(user_rows, labels, splits)

    path = evaluate.write_metrics(metrics, artifacts)
    print(json.dumps(metrics, indent=2))
    print(f"artifacts: {artifacts}  metrics: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

