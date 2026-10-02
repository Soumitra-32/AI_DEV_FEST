"""Context builder for the explanation layer.

``/chat-explain`` must never do arithmetic or read the database itself, so this
service assembles the *structured JSON* that the templates read and the model is
allowed to see. It reuses the already-tested services (``forecast_service``,
``plan_service``) and the shared feature pipeline, and it degrades section by
section: if the model artifacts are missing the forecast section falls back to
the trailing-average rule, and if a section cannot be built at all it is simply
absent — the template for that intent then says what it needs more of.

Two rules hold everywhere in this file:

* the ``user_id`` used here comes from the auth token, never from the request;
* nothing here writes anything, and every figure stays inside its named section,
  so the guardrail's number-grounding check has a context to check the model's
  wording against.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping, Optional

import pandas as pd

from backend.data import features as user_features
from backend.data import generator
from backend.genai import rag
from backend.ml import explain as ml_explain
from backend.rules import health_score

from . import anomaly_service, forecast_service, plan_service, signal_service

logger = logging.getLogger("shonchoy.explain_service")

#: Window used for the "recent activity" and fee numbers.
WINDOW_DAYS = 30

#: Cash-out fee and its cheapest alternative come from the dataset config, so
#: the number on the card is the same simulated rate the generator charged.
ALTERNATIVE_CHANNEL = "app transfer"

#: The adoption range we *assume*, never a measured result (plan §11).
ADOPTION_RANGE = "20%-50%"

#: Offered when the user asks about saving without naming a goal.
DEFAULT_GOAL_BDT = 30_000.0
DEFAULT_GOAL_MONTHS = 6


def _fee_rates(cfg: Mapping[str, Any]) -> tuple[float, float]:
    """``(cash_out_percent, alternative_percent)`` from the dataset config."""
    rates = cfg.get("fee_rates", {}).get("by_channel", {})
    return float(rates.get("cash_out", 0.0)), float(rates.get("app_transfer", 0.0))


def _recent_transactions(db_path: str | Path | None, user_id: str, days: int = WINDOW_DAYS) -> pd.DataFrame:
    """This user's transactions from the last ``days`` days (oldest first)."""
    path = db_path if db_path is not None else user_features.default_db_path()
    frame = user_features.load_transactions(path, [user_id])
    if frame.empty:
        return frame
    cutoff = frame["timestamp"].max() - pd.Timedelta(days=days)
    return frame.loc[frame["timestamp"].ge(cutoff)].reset_index(drop=True)


def _cashout_pattern(spent: pd.DataFrame, cash_outs: pd.DataFrame) -> dict[str, Any]:
    """Where and when this user's cash-outs actually cluster (use 4).

    This is what turns "I don't understand these transactions" into a *story*:
    "most of your cash-outs happen in the last week of the month" is a fact we
    computed here, and the LLM only phrases it. The window position is measured
    from each transaction's own date, and every count is reported next to the
    sample size so the template can say "of the N you did" rather than implying
    a certainty a 30-day window cannot support.
    """
    if cash_outs.empty:
        return {"cash_out_count": 0, "month_end_cash_out_share_pct": 0.0, "peak_weekday": None}
    stamps = pd.to_datetime(cash_outs["timestamp"])
    days = stamps.dt.day.to_numpy()
    # Day 21+ is the last third of a 30/31-day month.
    late = int((days >= 21).sum())
    weekdays = stamps.dt.dayofweek.to_numpy()
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    counts = pd.Series(weekdays).value_counts()
    # ``argsort`` rather than ``counts.index[0]``: the mode of a value-counts
    # index is untyped to a checker, and this keeps the peak an int.
    peak = names[int(counts.to_numpy()[int(counts.to_numpy().argmax())])] if len(counts) else None
    channel_counts = cash_outs["channel"].astype(str).value_counts().head(2)
    return {
        "cash_out_count": int(len(cash_outs)),
        "cash_out_total_bdt": round(float(cash_outs["amount_bdt"].sum()), 2),
        "month_end_cash_out_share_pct": round(late / len(cash_outs) * 100, 1),
        "peak_weekday": peak,
        "top_channels": [
            {"label": str(label), "count": int(value)} for label, value in channel_counts.items()
        ],
    }


def transactions_context(
    db_path: str | Path | None, user_id: str, days: int = WINDOW_DAYS
) -> dict[str, Any]:
    """Aggregated activity summary: totals, shortfall events, top categories.

    Also carries :func:`_cashout_pattern`, so the transaction story ("most of
    your cash-outs land in the last week of the month") is grounded in a
    measured share rather than generated.
    """
    frame = _recent_transactions(db_path, user_id, days)
    if frame.empty:
        return {}
    income = frame["type"].eq("income")
    spent = frame.loc[~income]
    totals = spent.groupby("category", as_index=False).agg(
        amount_bdt=("amount_bdt", "sum")
    )
    top = totals.sort_values(by="amount_bdt", ascending=False).head(3)
    return {
        "window_days": days,
        "count": int(len(frame)),
        "inflow_bdt": round(float(frame.loc[income, "amount_bdt"].sum()), 2),
        "outflow_bdt": round(float(frame.loc[~income, "amount_bdt"].sum()), 2),
        "fee_bdt": round(float(frame["fee_bdt"].sum()), 2),
        "shortfall_events": int(frame["is_shortfall"].sum()),
        "balance_bdt": round(float(frame.sort_values("timestamp")["balance_after"].iloc[-1]), 2),
        "top_categories": [
            {"label": str(row["category"]), "amount_bdt": round(float(row["amount_bdt"]), 2)}
            for _, row in top.iterrows()
        ],
        "pattern": _cashout_pattern(spent, spent.loc[spent["channel"].eq("cash_out")]),
    }


def fees_context(
    db_path: str | Path | None, user_id: str, days: int = WINDOW_DAYS
) -> dict[str, Any]:
    """What the cash-out channel cost, and what the same money would cost.

    Computed from this user's transactions and the simulated fee rate in
    ``config.yaml``. Phase 5's ``rules.fee_switch`` takes ownership of this
    arithmetic; until then it lives here so the explanation layer has real
    numbers rather than placeholders.
    """
    frame = _recent_transactions(db_path, user_id, days)
    if frame.empty:
        return {}
    cash_out = frame.loc[frame["channel"].eq("cash_out")]
    volume = float(cash_out["amount_bdt"].sum())
    fee_paid = float(cash_out["fee_bdt"].sum())
    cash_out_pct, alternative_pct = _fee_rates(generator.load_config())
    alternative_fee = round(volume * alternative_pct / 100.0, 2)
    return {
        "window_days": days,
        "cash_out_count": int(len(cash_out)),
        "cash_out_volume_bdt": round(volume, 2),
        "fee_paid_bdt": round(fee_paid, 2),
        "cash_out_fee_pct": cash_out_pct,
        "alternative_channel": ALTERNATIVE_CHANNEL,
        "alternative_fee_bdt": alternative_fee,
        "potential_saving_bdt": round(max(fee_paid - alternative_fee, 0.0), 2),
        "adoption_range": ADOPTION_RANGE,
        "note": "Fee rates are simulated for this demo, not official upay pricing.",
    }


def _drivers(
    user_id: str,
    db_path: str | Path | None,
    artifact_dir: str | Path | None,
    language: str,
) -> list[dict[str, Any]]:
    """Top SHAP drivers for this user's latest feature row (best effort).

    Returns ``[]`` when the model, the artifacts or shap are unavailable: the
    forecast card then shows days and pressure reasons without drivers, which is
    still a complete answer.
    """
    try:
        from backend.ml import dataset as forecast_dataset  # noqa: PLC0415 - heavy import

        frame = forecast_dataset.make_frame(db_path, [user_id])
        if frame.features.empty:
            return []
        row = frame.features.sort_values("date").iloc[[-1]]
        drivers = ml_explain.top_drivers(
            row,
            flow="outflow",
            language=language,
            artifact_dir=str(artifact_dir) if artifact_dir else None,
        )
        return [driver.as_dict() for driver in drivers]
    except Exception as exc:  # artifacts missing, shap missing, short history
        logger.info("no SHAP drivers for %s: %s", user_id, type(exc).__name__)
        return []


def forecast_context(
    user_id: str,
    db_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
    language: str = "bn",
) -> dict[str, Any]:
    """The 14-day outlook plus the SHAP drivers that explain it."""
    payload = forecast_service.build_forecast(
        user_id, horizon_days=14, include_pressure_days=True,
        db_path=db_path, artifact_dir=artifact_dir,
    )
    context = {key: value for key, value in payload.items() if key != "provenance"}
    context["source"] = payload["provenance"]["source"]
    context["drivers"] = _drivers(user_id, db_path, artifact_dir, language)
    return context


def plan_context(
    user_id: str,
    goal_bdt: float,
    months: int,
    db_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    """The solved savings plan, exactly as ``/savings-plan`` returns it."""
    return plan_service.build_plan(
        user_id, goal_bdt=goal_bdt, months=months, db_path=db_path, artifact_dir=artifact_dir
    )


def consistency_context(user_id: str, db_path: str | Path | None = None) -> dict[str, Any]:
    """The consistency band, from the trained model when one exists.

    Delegates to :mod:`backend.app.services.signal_service` so the chat answer
    and the ``/credit-readiness`` card can never disagree: same band, same factors, same
    "not a decision" wording. ``{}`` when the user is unknown, which
    :func:`build_context` treats as a missing section rather than an error.
    """
    try:
        return signal_service.build_signal(user_id, language="bn", db_path=db_path)
    except Exception as exc:  # unknown user or a missing artifact
        logger.info("no consistency context for %s: %s", user_id, type(exc).__name__)
        return {}


def tips_context(user_id: str, db_path: str | Path | None = None, limit: int = 3) -> list[dict[str, Any]]:
    """Behaviour-triggered tips, retrieved from the curated bank.

    This is the "retrieval, then LLM phrasing" split: :mod:`backend.genai.rag`
    picks tips whose trigger the user's own features satisfy, and the LLM can
    only rephrase those. Every tip carries the trigger that chose it, because
    "why am I seeing this?" is the point.

    Returns ``[]`` when the bank is missing or nothing fires, so the chat
    endpoint still answers without tips rather than failing.
    """
    path = Path(db_path) if db_path is not None else user_features.default_db_path()
    try:
        frame = user_features.user_features(
            user_features.load_config(), user_features.load_transactions(path)
        )
        row = user_features.feature_row(frame, user_id)
    except Exception as exc:
        logger.warning("tips retrieval failed for %s: %s", user_id, type(exc).__name__)
        return []
    return rag.retrieve(row, limit=limit)


def health_context(
    user_id: str, db_path: str | Path | None = None
) -> dict[str, Any]:
    """The health-score card, as the LLM and the template may see it.

    Reads :mod:`backend.rules.health_score` -- pure Python over the label-free
    features -- and ships only the components, the band and the three habit
    metrics named in the plan (cash dependency %, savings rate, fee burden).
    The raw score is *not* phrased as a grade; it is a coaching reading of
    behaviour, never a lending decision, so the banner travels with it.
    """
    path = db_path if db_path is not None else user_features.default_db_path()
    try:
        frame = user_features.user_features(
            user_features.load_config(), user_features.load_transactions(path)
        )
        row = user_features.feature_row(frame, user_id)
        graded = health_score.score_features(frame, user_id)
    except Exception as exc:  # unknown user or no transactions
        logger.info("no health context for %s: %s", user_id, type(exc).__name__)
        return {}
    components = [item.as_dict() for item in graded.components]
    return {
        "band": graded.band,
        "score": int(graded.score),
        "score_max": int(graded.score_max),
        "components": components,
        "habits": {
            "cash_dependency_pct": round(float(row.get("cash_out_share_of_outflow", 0.0)) * 100, 1),
            "fee_burden_pct": round(float(row.get("fee_share_of_income", 0.0)) * 100, 1),
            "income_regularity_days": float(row.get("income_days_per_month", 0.0)),
            "shortfall_days_per_month": float(row.get("shortfall_days_per_month", 0.0)),
        },
        "is_not_a_credit_score": True,
    }


def anomalies_context(
    user_id: str,
    db_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
    window_days: int = 30,
) -> dict[str, Any]:
    """The Spending Companion card: what was flagged, and what switching saves.

    Delegates to :mod:`backend.app.services.anomaly_service` so the chat answer
    and the ``/anomalies`` card can never disagree about the same payments.
    """
    try:
        return anomaly_service.build_anomalies(
            user_id, window_days=window_days, db_path=db_path, artifact_dir=artifact_dir
        )
    except Exception as exc:  # unknown user, or no transactions
        logger.info("no anomalies context for %s: %s", user_id, type(exc).__name__)
        return {}


def build_context(
    user_id: str,
    intent: str,
    db_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
    goal_bdt: Optional[float] = None,
    months: Optional[int] = None,
    language: str = "bn",
) -> dict[str, Any]:
    """Assemble the structured context for one whitelisted intent.

    Only the section the intent needs is computed, so a "fees" question never
    pays for a forecast. Every builder returns ``{}`` instead of raising, and a
    failure is logged rather than surfaced: a missing section can never turn the
    chat endpoint into a 500.
    """
    context: dict[str, Any] = {"user_id": user_id}
    try:
        if intent == "explain_transactions":
            context["transactions"] = transactions_context(db_path, user_id)
        elif intent == "fees":
            context["fees"] = fees_context(db_path, user_id)
        elif intent == "forecast":
            context["forecast"] = forecast_context(
                user_id, db_path=db_path, artifact_dir=artifact_dir, language=language
            )
        elif intent == "savings_plan":
            context["plan"] = plan_context(
                user_id,
                goal_bdt=float(goal_bdt if goal_bdt else DEFAULT_GOAL_BDT),
                months=int(months if months else DEFAULT_GOAL_MONTHS),
                db_path=db_path,
                artifact_dir=artifact_dir,
            )
        elif intent == "consistency":
            context["signal"] = consistency_context(user_id, db_path=db_path)
        elif intent == "tips":
            context["tips"] = tips_context(user_id, db_path=db_path)
        elif intent == "health_coach":
            context["health"] = health_context(user_id, db_path=db_path)
        elif intent == "anomalies":
            context["anomalies"] = anomalies_context(
                user_id, db_path=db_path, artifact_dir=artifact_dir
            )
        elif intent == "tradeoffs":
            # Trade-off wording describes options the solver already produced, so
            # it reuses the plan section rather than solving anything new.
            context["plan"] = plan_context(
                user_id,
                goal_bdt=float(goal_bdt if goal_bdt else DEFAULT_GOAL_BDT),
                months=int(months if months else DEFAULT_GOAL_MONTHS),
                db_path=db_path,
                artifact_dir=artifact_dir,
            )
    except Exception as exc:
        logger.warning(
            "context section %r failed for %s: %s", intent, user_id, type(exc).__name__
        )
    return context
