"""Metrics endpoint: model scoreboard for the /metrics page.

Thin by design: everything here is read from the artifact files written by
``train_all.py`` (forecast/signal) and ``compute_report_metrics.py``
(anomaly/fairness/fees/backtest). Nothing is computed per request, so this
endpoint is fast and can never 500 on model code — missing files degrade to
empty lists with an explanatory note, like /health.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from ..schemas import FairnessRow, MetricsResponse, ModelMetric

router = APIRouter(tags=["metrics"])

ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "ml" / "artifacts"


def _read(name: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads((ARTIFACT_DIR / name).read_text())
    except (OSError, ValueError):
        return None


def _forecast_metrics(stored: Dict[str, Any]) -> List[ModelMetric]:
    rows: List[ModelMetric] = []
    for flow in ("inflow", "outflow", "net"):
        block = stored.get(flow)
        if not isinstance(block, dict):
            continue
        model = block.get("model", {})
        best_name: Optional[str] = None
        best_mae: Optional[float] = None
        for base in ("seasonal_naive", "trailing_average"):
            cand = block.get(base, {})
            if isinstance(cand.get("mae"), (int, float)) and (
                best_mae is None or cand["mae"] < best_mae
            ):
                best_name, best_mae = base, float(cand["mae"])
        rows.append(
            ModelMetric(
                model_name="lightgbm_forecast",
                metric=f"{flow}_mae_14d",
                value=float(model.get("mae", 0.0)),
                baseline_name=best_name,
                baseline_value=best_mae,
                improvement_pct=float(block.get("improvement_over_best_pct", 0.0)),
            )
        )
    return rows


def _signal_metrics(stored: Dict[str, Any]) -> List[ModelMetric]:
    block = stored.get("signal")
    if not isinstance(block, dict):
        return []
    return [
        ModelMetric(
            model_name="logistic_signal",
            metric="auc",
            value=float(block.get("auc") or 0.0),
            baseline_name="random",
            baseline_value=block.get("baseline_auc"),
            improvement_pct=None,
        )
    ]


def _anomaly_metrics(extra: Dict[str, Any]) -> List[ModelMetric]:
    block = extra.get("anomaly")
    if not isinstance(block, dict):
        return []
    model, baseline = block.get("model", {}), block.get("baseline", {})
    return [
        ModelMetric(
            model_name="isolation_forest",
            metric="f1",
            value=float(model.get("f1", 0.0)),
            baseline_name="fixed_threshold",
            baseline_value=float(baseline.get("f1", 0.0)) if baseline.get("f1") is not None else None,
            improvement_pct=float(block.get("improvement_f1_pct", 0.0)),
        ),
        ModelMetric(
            model_name="isolation_forest",
            metric="auc",
            value=float(model.get("auc") or 0.0),
            baseline_name="fixed_threshold",
            baseline_value=baseline.get("auc"),
            improvement_pct=float(block.get("improvement_auc_pct", 0.0)),
        ),
    ]


def _fairness_rows(extra: Dict[str, Any]) -> List[FairnessRow]:
    rows: List[FairnessRow] = []
    mapping = (
        ("fairness_forecast", "groups", "mae_net", "forecast_net_mae"),
        ("fairness_anomaly", "flag_rate", None, "anomaly_flag_rate"),
        ("fairness_signal", "strong_share", None, "signal_strong_share"),
    )
    for section, _, _, metric in mapping:
        block = extra.get(section)
        if not isinstance(block, dict):
            continue
        for dim in ("persona", "district", "income_band"):
            cell = block.get(dim)
            if not isinstance(cell, dict):
                continue
            groups = cell.get("groups", cell.get("flag_rate", cell.get("strong_share", {})))
            gap = cell.get("max_relative_gap_pct")
            if not isinstance(groups, dict) or gap is None:
                continue
            for group, value in groups.items():
                number = value.get("mae_net") if isinstance(value, dict) else value
                if not isinstance(number, (int, float)):
                    continue
                rows.append(
                    FairnessRow(
                        dimension=dim,  # type: ignore[arg-type]
                        group=str(group),
                        metric=metric,
                        value=float(number),
                        relative_gap_pct=float(gap),
                    )
                )
    return rows


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Model scoreboard (measured, never invented)",
)
def get_metrics() -> MetricsResponse:
    """Serve the offline evaluation numbers the /metrics page renders."""
    stored = _read("metrics.json") or {}
    extra = _read("report_metrics.json") or {}
    notes: List[str] = [
        "Measured on held-out test users; demo user excluded.",
        "Anomaly/fairness rows need report_metrics.json "
        "(backend/scripts/compute_report_metrics.py).",
        "Relative gaps mislead on tiny groups/rates; REPORT.md reports absolute gaps too.",
    ]
    return MetricsResponse(
        generated_at=datetime.now(timezone.utc),
        forecast=_forecast_metrics(stored),
        anomaly=_anomaly_metrics(extra),
        signal=_signal_metrics(stored),
        fairness=_fairness_rows(extra),
        notes=notes,
    )
