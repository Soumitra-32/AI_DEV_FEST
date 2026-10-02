"""Goal Copilot service: the curated goal shapes, sized to this user.

The plan's Goal Copilot starts a savings conversation from a realistic target
rather than a blank box. This service joins the caller's own monthly income to
:mod:`backend.rules.goal_templates`, so the suggested amount is always scaled
from *their* ledger — the rules module owns the multiplier, this module only
supplies the income and shapes the payload.

Raising ``KeyError`` for an unknown user lets the router answer 404 rather than
offer templates sized from nothing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.data import features as user_features
from backend.rules import goal_templates

#: Feature read for the scaling (monthly, BDT).
INCOME_FEATURE = "income_mean_bdt"


def build_templates(
    user_id: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Every Goal Copilot template, with its goal scaled to the user's income."""
    path = db_path if db_path is not None else user_features.default_db_path()
    frame = user_features.user_features(
        user_features.load_config(), user_features.load_transactions(path)
    )
    row = user_features.feature_row(frame, user_id)
    monthly_income = float(row.get(INCOME_FEATURE, 0.0))
    return {
        "user_id": user_id,
        "templates": goal_templates.all_payloads(monthly_income),
    }
