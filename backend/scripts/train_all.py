"""Train every model with one command (Phase 3: forecast only).

Phase 8 extends this to the anomaly and signal models; for now it trains the
LightGBM forecaster and writes ``metrics.json``. Reads the user-level splits
so the demo user never leaks into training or evaluation.
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
from backend.ml import dataset, evaluate, forecast


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Train the Shonchoy forecast model.")
    parser.add_argument("--db", default=None, help="path to the SQLite database")
    parser.add_argument("--artifacts", default=None, help="where to write model files")
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
    path = evaluate.write_metrics(metrics, artifacts)
    print(json.dumps(metrics, indent=2))
    print(f"artifacts: {artifacts}  metrics: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

