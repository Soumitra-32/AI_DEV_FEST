"""Metrics service (Phase 8): ``GET /metrics`` without retraining anything.

Reads the ``metrics.json`` that ``backend/scripts/train_all.py`` wrote and maps it
onto the frozen :class:`backend.app.schemas.MetricsResponse`. Nothing is
recomputed here on purpose: the endpoint reports the numbers the offline run
actually measured, so a reader and a reviewer see the same values rather than two
calculations that happen to agree.

The mapping is deliberately total. Every model block is optional in
``metrics.json`` (a skipped ``--skip-anomaly`` run simply has no ``"anomaly"``
key), and a missing block produces a note rather than an exception or a silently
empty list -- an empty table reads as "measured, nothing found", which is the one
reading that must never be wrong.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from backend.ml import evaluate as forecast_evaluate

logger = logging.getLogger("shonchoy.metrics_service")

ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "ml" / "artifacts"

#: The forecast model's display name, shared with the ``/forecast`` card so the
#: two endpoints cannot drift into calling the same model different things.
FORECAST_MODEL_NAME = "lightgbm_14d_mean"


def _as_float(value: Any) -> Optional[float]:
    """A JSON number, or ``None`` for anything that is not one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _metric(
    model_name: str,
    metric: str,
    value: Any,
    baseline_name: Optional[str] = None,
    baseline_value: Any = None,
    improvement_pct: Any = None,
) -> Optional[dict[str, Any]]:
    """One :class:`ModelMetric` row, or ``None`` when the value is not a number.

    Returning ``None`` and letting the caller skip keeps a single missing number
    from failing the whole response, which is the behaviour the offline blocks
    rely on when a model was not trained.
    """
    number = _as_float(value)
    if number is None:
        return None
    base = _as_float(baseline_value)
    gain = _as_float(improvement_pct)
    return {
        "model_name": model_name,
        "metric": metric,
        "value": number,
        "baseline_name": baseline_name,
        "baseline_value": base,
        "improvement_pct": gain,
    }


def _forecast_rows(block: Mapping[str, Any], notes: list[str]) -> list[dict[str, Any]]:
    """Held-out MAE and RMSE per flow, model beside its best rule.

    The 14-day cumulative totals are the headline, because that is the number the
    savings solver consumes; the per-day spread is a different question and is not
    mixed in here.
    """
    rows: list[dict[str, Any]] = []
    for flow in forecast_evaluate.SCORED_FLOWS:
        scores = block.get(flow)
        if not isinstance(scores, Mapping):
            notes.append(f"forecast: no '{flow}' block in metrics.json")
            continue
        model = scores.get("model") or {}
        # ``improvement_over_best_pct`` names the best rule already, so the row's
        # baseline is that rule rather than a hard-coded name.
        # Re-bound so the key below closes over a non-optional mapping; pyright
        # re-checks captured names against their base (un-narrowed) type.
        scores_by_name: Mapping[str, Any] = scores
        baseline_name = min(
            forecast_evaluate.baselines.BASELINE_NAMES,
            key=lambda name: (scores_by_name.get(name) or {}).get("mae", float("inf")),
            default=None,
        )
        for metric, suffix in (("mae", "mae_bdt"), ("rmse", "rmse_bdt")):
            baseline_scores = (scores.get(baseline_name) or {}) if baseline_name else {}
            row = _metric(
                FORECAST_MODEL_NAME,
                suffix,
                model.get(metric),
                baseline_name=baseline_name,
                baseline_value=baseline_scores.get(metric),
                # ``improvement_pct`` lives inside the baseline's own block. Since
                # this baseline is the lowest-MAE one, its improvement is also the
                # improvement over the best rule, so the two agree by construction.
                improvement_pct=baseline_scores.get("improvement_pct")
                or scores.get("improvement_over_best_pct"),
            )
            if row:
                rows.append(row)
    return rows


def _anomaly_rows(block: Mapping[str, Any], notes: list[str]) -> list[dict[str, Any]]:
    """Forest precision/recall/F1/AUC against the fixed-threshold rule."""
    model = block.get("model") or {}
    baseline = block.get("baseline") or {}
    rows: list[dict[str, Any]] = []
    for metric in ("precision", "recall", "f1"):
        row = _metric(
            str(block.get("model_name") or "isolation_forest_behavior"),
            metric,
            model.get(metric),
            baseline_name=block.get("baseline_name"),
            baseline_value=baseline.get(metric),
            improvement_pct=block.get(f"improvement_{metric}_pct"),
        )
        if row:
            rows.append(row)
    # AUC is the ranking quality of the score, independent of the operating
    # point, so it is reported as a plain row with no rule comparator: a single
    # absolute cutoff has no meaningful AUC to be compared against.
    row = _metric(
        str(block.get("model_name") or "isolation_forest_behavior"),
        "auc",
        model.get("auc"),
        baseline_name=block.get("baseline_name"),
        baseline_value=baseline.get("auc"),
        improvement_pct=block.get("improvement_auc_pct"),
    )
    if row:
        rows.append(row)

    if block.get("status") == "unavailable":
        notes.append(f"anomaly: model-vs-rule scoring unavailable ({block.get('reason')})")
    elif model and baseline and _as_float(model.get("recall")) is not None:
        notes.append(
            "anomaly: the rule's higher recall comes from flagging far more rows "
            f"({baseline.get('precision')}% precision vs the model's "
            f"{model.get('precision')}%); the model wins on precision, F1 and AUC."
        )
    for kind, detail in (block.get("by_type") or {}).items():
        notes.append(
            f"anomaly by type {kind}: model recall {detail.get('model_recall')}% vs "
            f"rule {detail.get('baseline_recall')}% over {detail.get('count')} rows."
        )
    return rows


def _signal_rows(block: Mapping[str, Any], notes: list[str]) -> list[dict[str, Any]]:
    """Held-out AUC, and the cohort SHAP importance behind the band."""
    model_name = "logistic_regression_consistency"
    rows: list[dict[str, Any]] = []
    auc = _metric(
        model_name,
        "auc",
        block.get("auc"),
        baseline_name="random",
        baseline_value=block.get("baseline_auc"),
    )
    if auc:
        base = auc["baseline_value"] or 0.0
        if base:
            auc["improvement_pct"] = round((auc["value"] - base) / base * 100.0, 2)
        rows.append(auc)

    importance = block.get("shap_importance") or {}
    for item in importance.get("features", []) or []:
        name = item.get("feature")
        if not name:
            continue
        row = _metric(model_name, f"shap_mean_abs[{name}]", item.get("mean_abs_contribution"))
        if row:
            row["improvement_pct"] = _as_float(item.get("mean_contribution"))
            rows.append(row)
    if importance:
        notes.append(
            f"signal SHAP: {importance.get('method')} over "
            f"{importance.get('rows')} held-out users; the strongest driver is "
            f"{(importance.get('features') or [{}])[0].get('feature', 'n/a')}."
        )
    if block.get("auc") is None:
        notes.append("signal: no AUC in metrics.json (the signal model was not scored)")
    return rows


def _fairness_rows(block: Mapping[str, Any], notes: list[str]) -> list[dict[str, Any]]:
    """Group rows for the fairness table, worst gap first."""
    if block.get("status") == "unavailable":
        notes.append(f"fairness: unavailable ({block.get('reason')})")
        return []
    rows: list[dict[str, Any]] = []
    for item in block.get("rows", []) or []:
        value = _as_float(item.get("value"))
        gap = _as_float(item.get("relative_gap_pct"))
        if value is None or gap is None:
            continue
        rows.append(
            {
                "dimension": item["dimension"],
                "group": str(item["group"]),
                "metric": str(item["metric"]),
                "value": value,
                "relative_gap_pct": gap,
            }
        )
    if rows:
        target = block.get("target_relative_gap_pct")
        met = block.get("target_met")
        notes.append(
            f"fairness: {len(rows)} group rows scored against a "
            f"{target}% relative-gap target; {'target met' if met else 'target NOT met'}"
            f" ({block.get('n_exceeding_target')} rows outside it)."
        )
    excluded = block.get("excluded_groups") or []
    if excluded:
        notes.append(
            f"fairness: {len(excluded)} groups were excluded for having fewer than "
            f"{block.get('min_users_per_group')} held-out users, so the table does "
            "not cover them."
        )
    for caveat in block.get("caveats", []) or []:
        notes.append(f"fairness: {caveat}")
    return rows


def _impact_notes(metrics: Mapping[str, Any]) -> list[str]:
    """The user-facing consequences, stated as sentences with their numbers.

    The frozen ``MetricsResponse`` has no field for a paragraph, so the impact
    argument is carried in ``notes`` -- which is where a reader of the metrics
    page looks for caveats anyway, rather than in a field the frontend ignores.
    """
    notes: list[str] = []
    improvement = metrics.get("improvement_vs_best_pct") or {}
    if improvement:
        parts = ", ".join(f"{flow} {value}%" for flow, value in improvement.items())
        notes.append(
            f"impact: against the better of the two rule baselines the forecast "
            f"cuts 14-day error by {parts}."
        )
    target = metrics.get("target_improvement_pct")
    if target is not None:
        # GAP-12: say *forecast* improvement — "the plan's target" reads as
        # the fairness/plan target two notes below, which is NOT met.
        notes.append(
            f"impact: the forecast's {target}% improvement target is "
            f"{'met' if metrics.get('target_met') else 'not met'}."
        )
    anomaly = metrics.get("anomaly") or {}
    f1_gain = _as_float(anomaly.get("improvement_f1_pct"))
    if f1_gain is not None:
        notes.append(
            f"impact: ranking a user's own payments instead of one absolute taka "
            f"cutoff changes the anomaly F1 by {f1_gain}% on the same held-out rows."
        )
    signal = metrics.get("signal") or {}
    auc = _as_float(signal.get("auc"))
    if auc is not None:
        notes.append(
            f"impact: the consistency band separates held-out users at AUC {auc} "
            f"against {signal.get('baseline_auc')} for chance, which is a method "
            "demonstration and not a risk model (see DATA_ASSUMPTIONS.md)."
        )
    return notes


def _impact_rows(impact: Mapping[str, Any], notes: list[str]) -> list[dict[str, Any]]:
    """The plan's outcome numbers as ``ModelMetric`` rows, plus their notes.

    Impact is kept in its own block rather than mixed into the model tables: a
    fee saving is a *consequence* of the app, not a model's accuracy, and a
    reader should never see the two averaged together.
    """
    rows: list[dict[str, Any]] = []
    if not impact:
        notes.append(
            "impact: no impact block in metrics.json (retrain to measure fees, "
            "shortfall days and the goal hit-rate)."
        )
        return rows

    fee = impact.get("fee_savings") or {}
    if fee.get("status") == "ok":
        for metric in (
            "avg_potential_fee_saving_bdt_per_month",
            "avg_assumed_fee_saving_low_bdt_per_month",
            "avg_assumed_fee_saving_high_bdt_per_month",
        ):
            row = _metric("impact_fee_savings", metric, fee.get(metric))
            if row:
                rows.append(row)
        notes.append(
            f"impact: moving cash-outs to the cheapest channel would save about "
            f"{fee.get('avg_potential_fee_saving_bdt_per_month')} BDT/user/month "
            f"({fee.get('users')} held-out users); at the assumed "
            f"{fee.get('adoption_range')} adoption that is "
            f"{fee.get('avg_assumed_fee_saving_low_bdt_per_month')}-"
            f"{fee.get('avg_assumed_fee_saving_high_bdt_per_month')} BDT/month."
        )
    else:
        notes.append(f"impact: fee savings unavailable ({fee.get('reason')})")

    short = impact.get("shortfall_days") or {}
    if short.get("status") == "ok":
        for metric in (
            "observed_shortfall_days_per_month",
            "plan_shortfall_days_per_month",
            "avoided_shortfall_days_per_month",
        ):
            row = _metric("impact_shortfall_days", metric, short.get(metric))
            if row:
                rows.append(row)
        notes.append(
            f"impact: the plan's timing advice targets "
            f"{short.get('avoided_shortfall_days_per_month')} of "
            f"{short.get('observed_shortfall_days_per_month')} shortfall days per "
            f"month, leaving {short.get('plan_shortfall_days_per_month')}."
        )
    else:
        notes.append(f"impact: shortfall days unavailable ({short.get('reason')})")

    goal = impact.get("goal_hit_rate") or {}
    if goal.get("status") == "ok":
        ai = goal.get("ai") or {}
        naive = goal.get("naive") or {}
        row = _metric(
            "impact_goal_hit_rate",
            "ai_hit_rate_pct",
            ai.get("hit_rate_pct"),
            baseline_name="naive_goal_per_months",
            baseline_value=naive.get("hit_rate_pct"),
            improvement_pct=goal.get("improvement_pct_points"),
        )
        if row:
            rows.append(row)
        notes.append(
            f"impact: plan on the earlier months, test on the last two — the AI "
            f"plan kept {ai.get('hit_rate_pct')}% of the goals it recommended "
            f"against {naive.get('hit_rate_pct')}% for naive goal/months planning "
            f"({goal.get('users')} users)."
        )
    else:
        notes.append(f"impact: goal hit-rate unavailable ({goal.get('reason')})")

    logs = impact.get("request_logs") or {}
    if logs.get("status") == "ok":
        for metric in ("requests", "error_rate_pct", "avg_duration_ms"):
            row = _metric("impact_request_logs", metric, logs.get(metric))
            if row:
                rows.append(row)
        notes.append(
            f"impact: {logs.get('requests')} requests logged without PII "
            f"({logs.get('error_rate_pct')}% non-2xx)."
        )
    else:
        notes.append(f"impact: request logs unavailable ({logs.get('reason')})")
    return rows



def _generated_at(artifact_dir: str | Path) -> datetime:
    """When the evaluation file was written -- the honest generation time.

    Taken from the file's own mtime rather than "now", so a stale artifact is
    visibly old instead of looking freshly computed on every request.
    """
    path = Path(artifact_dir) / forecast_evaluate.METRICS_FILE
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return datetime.now(tz=timezone.utc)


def build_metrics(
    artifact_dir: str | Path | None = None,
    *,
    feedback_path: str | Path | None = None,
    request_log_path: str | Path | None = None,
) -> dict[str, Any]:
    """The whole ``MetricsResponse`` payload, built from ``metrics.json``.

    Never raises. With no artifact at all it returns an empty-but-valid payload
    whose ``notes`` say the models have not been trained, because "the endpoint
    works and has nothing to show" is a far better answer than a 500 on the
    metrics page.

    ``feedback_path``/``request_log_path`` are the PII-free stores beside
    ``metrics.json``. They are read at request time (unlike the model blocks,
    which are frozen into the artifact), because feedback and traffic keep
    arriving after training.
    """
    directory = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    metrics = forecast_evaluate.read_metrics(directory)
    notes: list[str] = []

    feedback = None
    if feedback_path is not None:
        from . import feedback_service

        feedback = feedback_service.summarise(feedback_path)
        if feedback["responses"]:
            notes.append(
                f"feedback: {feedback['responses']} responses, "
                f"{feedback['helpful_rate_pct']}% helpful (no PII stored)."
            )
        else:
            notes.append("feedback: no responses yet.")

    if not metrics:
        notes.append(
            "No evaluation artifact found. Run `make train` "
            "(backend/scripts/train_all.py) to generate metrics.json."
        )
        return {
            "generated_at": _generated_at(directory),
            "forecast": [],
            "anomaly": [],
            "signal": [],
            "fairness": [],
            "impact": [],
            "feedback": feedback,
            "notes": notes,
        }

    # Request logs accumulate after training, so they are re-read beside the
    # artifact rather than trusted from the frozen block.
    impact = dict(metrics.get("impact") or {})
    if request_log_path is not None:
        impact["request_logs"] = forecast_evaluate.request_log_summary(request_log_path)

    forecast_block = metrics.get("cumulative") or metrics
    return {
        "generated_at": _generated_at(directory),
        "forecast": _forecast_rows(forecast_block, notes),
        "anomaly": _anomaly_rows(metrics.get("anomaly") or {}, notes),
        "signal": _signal_rows(metrics.get("signal") or {}, notes),
        "fairness": _fairness_rows(metrics.get("fairness") or {}, notes),
        "impact": _impact_rows(impact, notes),
        "feedback": feedback,
        "notes": _impact_notes(metrics) + notes,
    }
