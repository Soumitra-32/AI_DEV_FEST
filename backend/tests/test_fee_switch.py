"""Fee-switch tests (Phase 5): the ৳320 is *computed*, never hardcoded.

The demo's headline number is "switching cash-outs saves about ৳320/month". These
tests make that claim falsifiable: they rebuild Rahim's ledger, recompute the
figure from his own rows, and then change the assumed rate table and watch the
answer move. If the number were a constant, the second test would fail.
"""
from __future__ import annotations

import copy

import pandas as pd
import pytest

from backend.rules import fee_switch
from backend.scripts import seed_demo_user

DEMO_USER = "rahim"


@pytest.fixture(scope="module")
def rahim_transactions(base_config: dict) -> pd.DataFrame:
    """Rahim's generated ledger (the same rows the demo is built on)."""
    _, transactions = seed_demo_user.build_demo_user(base_config)
    return transactions


def _cash_out_volume(transactions: pd.DataFrame) -> float:
    cash_outs = transactions.loc[transactions["channel"].eq("cash_out")]
    return float(cash_outs["amount_bdt"].sum())


# ---------------------------------------------------------------------------
# the demo number, recomputed from the ledger
# ---------------------------------------------------------------------------
def test_rahim_fee_switch_reproduces_the_demo_number(
    base_config: dict, rahim_transactions: pd.DataFrame
) -> None:
    """Each figure equals an independent calculation over Rahim's own rows."""
    whole = fee_switch.suggest(rahim_transactions, base_config, window_days=None)
    volume = _cash_out_volume(rahim_transactions)
    rate = float(base_config["fee_rates"]["by_channel"]["cash_out"]) / 100.0
    months = int(rahim_transactions["timestamp"].dt.to_period("M").nunique())

    assert whole.cash_out_count == int(rahim_transactions["channel"].eq("cash_out").sum())
    assert whole.cash_out_volume_bdt == pytest.approx(volume, abs=0.01)
    assert whole.fee_paid_bdt == pytest.approx(volume * rate, abs=0.05)
    assert whole.potential_saving_bdt == pytest.approx(volume * rate, abs=0.05)
    assert whole.alternative_channel_key == "app_transfer"
    assert whole.alternative_fee_bdt == 0.0
    assert whole.adoption_range == "20%-50%"
    assert whole.assumed_saving_low_bdt == pytest.approx(whole.potential_saving_bdt * 0.20, abs=0.01)
    assert whole.assumed_saving_high_bdt == pytest.approx(whole.potential_saving_bdt * 0.50, abs=0.01)

    # ... and the monthly figure matches the number documented for the demo user
    documented = float(base_config["demo_user"]["expected_monthly_fee_bdt"])
    assert whole.potential_saving_bdt / months == pytest.approx(documented, rel=0.05)
    assert whole.potential_saving_bdt / months == pytest.approx(320, rel=0.10)


def test_the_saving_follows_the_assumed_rate_table(
    base_config: dict, rahim_transactions: pd.DataFrame
) -> None:
    """The decisive anti-hardcode check: change the rate, the saving changes."""
    doubled = copy.deepcopy(base_config)
    doubled["fee_rates"]["by_channel"]["cash_out"] = 2.0
    free = copy.deepcopy(base_config)
    free["fee_rates"]["by_channel"]["cash_out"] = 0.0

    baseline = fee_switch.suggest(rahim_transactions, base_config, window_days=None)
    higher = fee_switch.suggest(rahim_transactions, doubled, window_days=None)
    none = fee_switch.suggest(rahim_transactions, free, window_days=None)

    volume = baseline.cash_out_volume_bdt
    assert higher.fee_paid_bdt == pytest.approx(volume * 0.02, abs=0.05)
    assert higher.potential_saving_bdt > baseline.potential_saving_bdt
    # a 0% cash-out rate leaves nothing to save, which a constant could not do
    assert none.fee_paid_bdt == pytest.approx(0.0)
    assert none.potential_saving_bdt == pytest.approx(0.0)
    assert none.worth_suggesting is False


def test_the_saving_is_zero_without_cash_outs(base_config: dict) -> None:
    """Sending money by app transfer is already free, so there is no suggestion."""
    frame = pd.DataFrame(
        [
            {"channel": "app_transfer", "amount_bdt": 5000.0, "fee_bdt": 0.0},
            {"channel": "merchant_payment", "amount_bdt": 1200.0, "fee_bdt": 0.0},
        ]
    )
    switch = fee_switch.suggest(frame, base_config, window_days=None)
    assert switch.cash_out_count == 0
    assert switch.cash_out_volume_bdt == 0.0
    assert switch.potential_saving_bdt == 0.0
    assert switch.worth_suggesting is False


def test_only_cash_outs_are_counted(base_config: dict, rahim_transactions: pd.DataFrame) -> None:
    """Other channels are ignored, even when they are large."""
    frame = rahim_transactions
    switch = fee_switch.suggest(frame, base_config, window_days=None)
    assert switch.cash_out_count == int(frame["channel"].eq("cash_out").sum())
    assert switch.cash_out_volume_bdt == pytest.approx(_cash_out_volume(frame), abs=0.01)


# ---------------------------------------------------------------------------
# rate card and window behaviour
# ---------------------------------------------------------------------------
def test_the_alternative_is_the_cheapest_channel_in_the_rate_card(base_config: dict) -> None:
    assert fee_switch.cheapest_channel(base_config) == "app_transfer"
    assert fee_switch.channel_rate_pct(base_config, "app_transfer") == 0.0
    assert fee_switch.channel_rate_pct(base_config, "cash_out") > 0


def test_a_custom_alternative_uses_its_own_rate(base_config: dict) -> None:
    """Choosing a *charged* alternative must reduce the saving, not fake it."""
    frame = pd.DataFrame([{"channel": "cash_out", "amount_bdt": 10000.0, "fee_bdt": 185.0}])
    config = copy.deepcopy(base_config)
    config["fee_rates"]["by_channel"]["send_money"] = 1.0

    cheap = fee_switch.suggest(frame, config, window_days=None, alternative_channel="app_transfer")
    costly = fee_switch.suggest(frame, config, window_days=None, alternative_channel="send_money")

    assert cheap.alternative_fee_bdt == 0.0
    assert costly.alternative_fee_bdt == pytest.approx(100.0)
    assert costly.potential_saving_bdt == pytest.approx(185.0 - 100.0)


def test_the_window_limits_which_rows_count(base_config: dict) -> None:
    """A 30-day window must ignore older cash-outs."""
    frame = pd.DataFrame(
        [
            {"channel": "cash_out", "amount_bdt": 4000.0, "fee_bdt": 74.0,
             "timestamp": "2025-01-05T10:00:00"},
            {"channel": "cash_out", "amount_bdt": 6000.0, "fee_bdt": 111.0,
             "timestamp": "2025-03-01T10:00:00"},
        ]
    )
    windowed = fee_switch.suggest(frame, base_config, window_days=30)
    whole = fee_switch.suggest(frame, base_config, window_days=None)
    assert windowed.cash_out_count == 1
    assert windowed.cash_out_volume_bdt == pytest.approx(6000.0)
    assert whole.cash_out_count == 2
    assert whole.cash_out_volume_bdt == pytest.approx(10000.0)


# ---------------------------------------------------------------------------
# the trace, and the API shape
# ---------------------------------------------------------------------------
def test_the_arithmetic_shows_every_step(base_config: dict, rahim_transactions: pd.DataFrame) -> None:
    switch = fee_switch.suggest(rahim_transactions, base_config, window_days=None)
    trace = " | ".join(switch.arithmetic)
    assert "assumed" in trace and "cash-out rate" in trace
    assert switch.alternative_channel in trace
    assert "assumption, not a measured result" in trace
    # the ledger's own fee is reported beside the computed one
    assert "recorded" in trace


def test_as_dict_matches_the_api_field_names(
    base_config: dict, rahim_transactions: pd.DataFrame
) -> None:
    from backend.app.schemas import FeeSwitchSuggestion

    switch = fee_switch.suggest(rahim_transactions, base_config, window_days=None)
    payload = switch.as_dict()
    fields = set(FeeSwitchSuggestion.model_fields)
    # every contract field is present and typed, extra fields are allowed
    assert fields <= set(payload)
    assert FeeSwitchSuggestion(**{key: payload[key] for key in fields})

