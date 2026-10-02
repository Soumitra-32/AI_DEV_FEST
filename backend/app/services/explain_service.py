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
from backend.ml import explain as ml_explain

from . import forecast_service, plan_service

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


def transactions_context(
    db_path: str | Path | None, user_id: str, days: int = WINDOW_DAYS
) -> dict[str, Any]:
    """Aggregated activity summary: totals, shortfall events, top categories."""
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
    """Provisional consistency context from the feature pipeline.

    Phase 5 replaces this with the trained model's band and SHAP factors. Until
    then it is a *behavioural* summary and says so, which keeps the "not a score,
    not a decision" wording honest instead of dressing a rule up as a model.
    """
    path = db_path if db_path is not None else user_features.default_db_path()
    try:
        features = user_features.user_features(
            generator.load_config(), user_features.load_transactions(path, [user_id])
        )
        if features.empty:
            return {}
        row = features.iloc[0]
    except Exception as exc:  # unknown user or an empty slice
        logger.info("no consistency context for %s: %s", user_id, type(exc).__name__)
        return {}
    fee_share = float(row["fee_share_of_income"])
    shortfall = float(row["shortfall_days_per_month"])
    cash_outs = float(row["cash_out_count_per_month"])
    factors = [
        {
            "feature": "fee_share_of_income",
            "direction": "weakens" if fee_share > 0.01 else "improves",
            "magnitude": round(fee_share, 4),
            "plain_language": (
                f"আয়ের প্রায় {fee_share * 100:.1f}% ফিতে চলে যায়।"
                if fee_share > 0.01
                else "ফিতে যাওয়া টাকার হার খুব কম।"
            ),
        },
        {
            "feature": "shortfall_days_per_month",
            "direction": "weakens" if shortfall > 1 else "improves",
            "magnitude": round(shortfall, 2),
            "plain_language": (
                f"মাসে গড়ে {shortfall:.1f} দিন ব্যালেন্স ঘাটতি হয়।"
                if shortfall > 1
                else "ব্যালেন্স ঘাটতির দিন খুব কম।"
            ),
        },
        {
            "feature": "cash_out_count_per_month",
            "direction": "weakens" if cash_outs >= 4 else "improves",
            "magnitude": round(cash_outs, 2),
            "plain_language": (
                f"মাসে {cash_outs:.0f} বার ক্যাশ-আউট করেন।"
                if cash_outs >= 4
                else "ক্যাশ-আউটের সংখ্যা কম।"
            ),
        },
    ]
    return {
        "band": "Building",
        "factors": factors[:3],
        "improvements": [
            "মাসে এক-দুইবার ক্যাশ-আউটের বদলে অ্যাপ ট্রান্সফার ব্যবহার করুন",
            "মাস শেষের ৩-৪ দিনের বড় খরচ আগেই সাজিয়ে নিন",
        ],
        "provisional": True,
        "note": "Behavioural summary only; the trained signal model arrives in phase 5.",
    }


def tips_context(user_id: str, db_path: str | Path | None = None, limit: int = 3) -> list[dict[str, Any]]:
    """Behaviour-triggered tips, each carrying the trigger that chose it.

    Phase 6 replaces this with the RAG retriever over ``genai/tips.json``; the
    trigger is shown either way, because "why am I seeing this?" is the point.
    """
    fees = fees_context(db_path, user_id)
    cash_outs = int(fees.get("cash_out_count", 0))
    tips: list[dict[str, Any]] = []
    if cash_outs >= 3:
        tips.append({
            "title": "Send money by app transfer",
            "title_bn": "অ্যাপ ট্রান্সফারে টাকা পাঠান",
            "body": (
                f"You took cash out {cash_outs} times in 30 days, and cash-out is "
                f"the feeliest channel in the simulated rate card."
            ),
            "body_bn": f"৩০ দিনে {cash_outs} বার ক্যাশ-আউট করেছেন, এই ফিরে সবচেয়ে বেশি।",
            "trigger": f"cash_out_count >= 3 in 30 days (observed {cash_outs})",
        })
    if float(fees.get("fee_paid_bdt", 0.0)) > 0:
        tips.append({
            "title": "Move the monthly fee into the goal",
            "title_bn": "মাসিক ফি টাকাটা লক্ষ্যে দিন",
            "body": "What the fee already costs you is the easiest first saving.",
            "body_bn": "ফিতে যাওয়া মাসিক টাকাই সবচেয়ে সহজ প্রথম সঞ্চয়।",
            "trigger": "fee_paid_bdt > 0 in the last 30 days",
        })
    tips.append({
        "title": "Spread the month-end lump",
        "title_bn": "মাস শেষের বড় খরচ ছড়িয়ে দিন",
        "body": "Two large cash-outs in the last week are what create the squeeze.",
        "body_bn": "মাসের শেষ সপ্তাহে দুটি বড় ক্যাশ-আউটই চাপ তৈরি করে।",
        "trigger": "month-end spending pattern (calendar rule, always shown)",
    })
    return tips[: max(int(limit), 1)]


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
    except Exception as exc:
        logger.warning(
            "context section %r failed for %s: %s", intent, user_id, type(exc).__name__
        )
    return context
