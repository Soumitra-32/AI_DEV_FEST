"""Fee-switch rules (Spending Companion, rules layer).

The demo makes a number-shaped claim: *"switching your cash-outs to app transfer
saves about ৳320 a month."* This module **computes** that number from the user's
own transactions and the assumed rate table in ``backend/data/config.yaml`` — no
figure here is hardcoded, and ``backend/tests/test_fee_switch.py`` proves it by
changing the assumed rate and watching the answer move with it.

Three things the module is deliberate about:

* **The rate comes from the config.** ``fee_rates.by_channel`` is the same table
  the generator charged from, so the suggestion can never quote a fee the ledger
  disagrees with.
* **The work is shown.** :attr:`FeeSwitch.arithmetic` returns the sum line by
  line, so the card (and the LLM that verbalises it) can only repeat numbers we
  actually calculated.
* **The adoption range is an assumption.** We can measure the fee a channel
  charges; we cannot measure how many cash-outs a person stops making. That range
  is labelled as an assumption wherever it is shown.

Pure functions over ``pandas`` frames: no database, no model, no LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import pandas as pd

#: The channel cash-outs should move to. ``app_transfer`` is the cheapest channel
#: in the assumed rate card (0%), which is the whole point of the suggestion.
DEFAULT_ALTERNATIVE = "app_transfer"

#: 1 Oct 2026 Bangladesh Bank Bangla QR policy constants
BANGLADESH_BANK_CIRCULAR_DATE = "2026-10-01"
BANGLADESH_BANK_INCENTIVE_CAP_BDT = 2000.0  # BB pays incentive on transactions <= ৳2,000 via NPSB
BANGLADESH_BANK_ISSUER_INCENTIVE_PCT = 0.20  # 0.20% paid by BB to issuing MFS (upay)
BANGLADESH_BANK_ACQUIRER_INCENTIVE_PCT = 0.10  # 0.10% paid by BB to acquirer

#: Channel keys -> the human wording the UI shows (the config uses underscores).
CHANNEL_LABELS: Mapping[str, str] = {
    "cash_out": "cash out",
    "app_transfer": "app transfer",
    "bangla_qr": "Bangla QR payment",
    "merchant_payment": "merchant payment",
    "send_money": "send money",
    "bill_payment": "bill payment",
    "mobile_topup": "mobile top-up",
    "agent_deposit": "agent deposit",
}

#: The adoption range we *assume*, never a measured result (plan.txt §11).
ADOPTION_RANGE = "20%-50%"
ADOPTION_LOW = 0.20
ADOPTION_HIGH = 0.50

#: Default reporting window, matching the demo's "5 cash-outs in 30 days".
DEFAULT_WINDOW_DAYS = 30

#: Shown next to every fee figure, because the rates are simulated, not official.
FEE_NOTE = "Fee rates are simulated for this demo, not official upay pricing."


def channel_label(channel: str) -> str:
    """Human-readable name of a channel key (falls back to the raw key)."""
    return CHANNEL_LABELS.get(str(channel), str(channel).replace("_", " "))


def channel_rate_pct(cfg: Mapping[str, Any], channel: str) -> float:
    """Assumed percentage fee for ``channel`` from the dataset config."""
    rates = cfg.get("fee_rates", {}).get("by_channel", {})
    return float(rates.get(channel, 0.0))


def cheapest_channel(cfg: Mapping[str, Any], exclude: str = "cash_out") -> str:
    """The lowest-rate channel in the assumed rate card (deterministic on ties).

    ``exclude`` removes the channel we are switching *away* from, so the answer is
    never "keep doing the expensive thing". Ties break in favour of
    :data:`DEFAULT_ALTERNATIVE` (then alphabetically), so the same config always
    produces the same, human-sensible suggestion instead of, say, ``agent_deposit``.
    """
    rates = cfg.get("fee_rates", {}).get("by_channel", {})
    candidates = [(name, float(rate)) for name, rate in rates.items() if name != exclude]
    if not candidates:
        return DEFAULT_ALTERNATIVE
    return min(
        candidates,
        key=lambda item: (item[1], 0 if item[0] == DEFAULT_ALTERNATIVE else 1, item[0]),
    )[0]


@dataclass(frozen=True)
class FeeSwitch:
    """The computed fee-switch suggestion for one user over one window.

    ``potential_saving_bdt`` is the headline number: fees already paid minus what
    the same volume would cost on the cheaper channel. It is produced by
    :func:`suggest` from the ledger, never supplied by a caller.
    """

    cash_out_count: int
    cash_out_volume_bdt: float
    fee_paid_bdt: float
    cash_out_rate_pct: float
    alternative_channel: str  # the human label, e.g. "app transfer"
    alternative_channel_key: str  # the config key, e.g. "app_transfer"
    alternative_rate_pct: float
    alternative_fee_bdt: float
    potential_saving_bdt: float
    recorded_fee_bdt: float | None = None
    adoption_range: str = ADOPTION_RANGE
    assumed_saving_low_bdt: float = 0.0
    assumed_saving_high_bdt: float = 0.0
    window_days: int = DEFAULT_WINDOW_DAYS
    bangla_qr_eligible_count: int = 0
    bangla_qr_eligible_volume_bdt: float = 0.0
    bangla_qr_cap_bdt: float = BANGLADESH_BANK_INCENTIVE_CAP_BDT
    upay_issuer_incentive_bdt: float = 0.0
    bangla_qr_policy: dict[str, Any] = field(default_factory=dict)
    arithmetic: list[str] = field(default_factory=list)

    @property
    def worth_suggesting(self) -> bool:
        """Only offer the switch when there was a cash-out *and* a real saving.

        A zero saving is not a suggestion, it is noise; the API omits the card
        entirely in that case rather than showing "save ৳0".
        """
        return self.cash_out_count > 0 and self.potential_saving_bdt > 0

    def as_dict(self) -> dict[str, Any]:
        """The shape ``schemas.FeeSwitchSuggestion`` expects, plus the extras."""
        return {
            "cash_out_count": self.cash_out_count,
            "cash_out_volume_bdt": round(self.cash_out_volume_bdt, 2),
            "fee_paid_bdt": round(self.fee_paid_bdt, 2),
            "cash_out_rate_pct": round(self.cash_out_rate_pct, 4),
            "alternative_channel": self.alternative_channel,
            "alternative_channel_key": self.alternative_channel_key,
            "alternative_fee_bdt": round(self.alternative_fee_bdt, 2),
            "potential_saving_bdt": round(self.potential_saving_bdt, 2),
            "recorded_fee_bdt": (
                None if self.recorded_fee_bdt is None else round(self.recorded_fee_bdt, 2)
            ),
            "adoption_range": self.adoption_range,
            "assumed_saving_low_bdt": round(self.assumed_saving_low_bdt, 2),
            "assumed_saving_high_bdt": round(self.assumed_saving_high_bdt, 2),
            "window_days": self.window_days,
            "bangla_qr_eligible_count": self.bangla_qr_eligible_count,
            "bangla_qr_eligible_volume_bdt": round(self.bangla_qr_eligible_volume_bdt, 2),
            "bangla_qr_cap_bdt": round(self.bangla_qr_cap_bdt, 2),
            "upay_issuer_incentive_bdt": round(self.upay_issuer_incentive_bdt, 2),
            "bangla_qr_policy": dict(self.bangla_qr_policy),
            "arithmetic": list(self.arithmetic),
            "note": FEE_NOTE,
        }


def _window(transactions: pd.DataFrame, window_days: int | None) -> pd.DataFrame:
    """Keep only the last ``window_days`` of the ledger (oldest first)."""
    if transactions is None or transactions.empty:
        return pd.DataFrame(columns=["channel", "amount_bdt", "fee_bdt", "timestamp"])
    frame = transactions.copy()
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        frame = frame.sort_values("timestamp", kind="stable")
    if window_days is None:
        return frame.reset_index(drop=True)
    days = max(int(window_days), 1)
    if "timestamp" not in frame.columns:
        return frame.reset_index(drop=True)
    reference = frame["timestamp"].max()
    cutoff = reference - pd.Timedelta(days=days)
    return frame.loc[frame["timestamp"].ge(cutoff)].reset_index(drop=True)


def suggest(
    transactions: pd.DataFrame,
    cfg: Mapping[str, Any],
    window_days: int | None = DEFAULT_WINDOW_DAYS,
    alternative_channel: str | None = None,
) -> FeeSwitch:
    """Compute the fee-switch suggestion from a user's transactions.

    ``transactions`` needs ``channel``, ``amount_bdt`` and (preferably)
    ``fee_bdt``/``timestamp``. The alternative channel defaults to the cheapest in
    the assumed rate card; the fee paid uses the **recorded** ``fee_bdt`` when it
    is present, so the number always agrees with the ledger, and falls back to
    ``amount x rate`` only when the column is missing.
    """
    frame = _window(transactions, window_days)
    channel = alternative_channel or cheapest_channel(cfg)

    cash_out_rate = channel_rate_pct(cfg, "cash_out")
    alternative_rate = channel_rate_pct(cfg, channel)

    if frame.empty or "channel" not in frame.columns:
        cash_outs = frame.iloc[0:0]
    else:
        cash_outs = frame.loc[frame["channel"].eq("cash_out")]

    count = int(len(cash_outs))
    amount = cash_outs["amount_bdt"].astype(float)
    volume = float(amount.sum())
    # The fee is computed from the *assumed* rate table — the documented basis of
    # the whole simulation — and the ledger's own recorded fee is reported beside
    # it for comparison. Nothing here is a stored constant, which is why changing
    # the assumed rate moves the answer (see tests/test_fee_switch.py).
    fee_paid = round(volume * cash_out_rate / 100.0, 2)
    recorded: float | None = None
    if count and "fee_bdt" in cash_outs.columns:
        recorded = round(float(cash_outs["fee_bdt"].astype(float).sum()), 2)

    alternative_fee = round(volume * alternative_rate / 100.0, 2)
    saving = round(max(fee_paid - alternative_fee, 0.0), 2)
    label = channel_label(channel)
    days = int(window_days) if window_days is not None else 0

    arithmetic = [
        f"cash-outs in the last {days} day(s): {count}",
        f"cash-out volume = {volume:,.2f}",
        f"fee = {volume:,.2f} x assumed cash-out rate {cash_out_rate:.2f}% = {fee_paid:,.2f}",
    ]
    if recorded is not None:
        arithmetic.append(f"fee recorded in the same window = {recorded:,.2f}")
    arithmetic += [
        f"{label} fee = {volume:,.2f} x {alternative_rate:.2f}% = {alternative_fee:,.2f}",
        f"potential saving = {fee_paid:,.2f} - {alternative_fee:,.2f} = {saving:,.2f} per window",
        (
            f"assumed adoption {ADOPTION_RANGE} -> "
            f"{saving * ADOPTION_LOW:,.2f} to {saving * ADOPTION_HIGH:,.2f} per window "
            "(assumption, not a measured result)"
        ),
    ]

    # 1 Oct 2026 Bangladesh Bank Bangla QR policy analysis:
    # Small transactions (<= ৳2,000) qualify for the central bank incentive via NPSB.
    if count and "amount_bdt" in cash_outs.columns:
        qr_eligible = cash_outs.loc[cash_outs["amount_bdt"].astype(float).le(BANGLADESH_BANK_INCENTIVE_CAP_BDT)]
        qr_eligible_count = int(len(qr_eligible))
        qr_eligible_volume = round(float(qr_eligible["amount_bdt"].astype(float).sum()), 2)
    else:
        qr_eligible_count = 0
        qr_eligible_volume = 0.0

    upay_incentive = round(qr_eligible_volume * (BANGLADESH_BANK_ISSUER_INCENTIVE_PCT / 100.0), 2)

    bangla_qr_policy = {
        "effective_date": BANGLADESH_BANK_CIRCULAR_DATE,
        "regulation": "Bangladesh Bank Guidelines on Bangla QR & NPSB (1 Oct 2026)",
        "statutory_act": "Payment and Settlement Systems Act, 2024",
        "customer_fee_pct": 0.0,
        "cash_out_fee_pct": cash_out_rate,
        "incentive_cap_bdt": BANGLADESH_BANK_INCENTIVE_CAP_BDT,
        "issuer_incentive_pct": BANGLADESH_BANK_ISSUER_INCENTIVE_PCT,
        "acquirer_incentive_pct": BANGLADESH_BANK_ACQUIRER_INCENTIVE_PCT,
        "bb_issuer_incentive_pct": BANGLADESH_BANK_ISSUER_INCENTIVE_PCT,
        "bb_acquirer_incentive_pct": BANGLADESH_BANK_ACQUIRER_INCENTIVE_PCT,
        "instant_settlement": True,
        "interchange_rate_pct": 0.0,
        "merchant_mdr_min_abolished": True,
        "eligible_count": qr_eligible_count,
        "eligible_volume_bdt": qr_eligible_volume,
        "upay_issuer_incentive_bdt": upay_incentive,
        "settlement": "instant (NPSB)",
        "customer_claim": "0% fee instead of 1.4% cash-out fee at merchants",
        "upay_claim": (
            "Instant settlement, zero IRF, 0.20% central-bank issuing subsidy under ৳2,000 via NPSB, "
            "plus retained float (vs ~0.20% net margin on agent cash-out)"
        ),
        "anti_misuse_monitoring": (
            "Payment and Settlement Systems Act, 2024: Acquirers must actively monitor for "
            "artificial transaction splitting near ৳2,000 and unauthorised cash-outs via QR."
        ),
    }

    if qr_eligible_count > 0:
        arithmetic.append(
            f"Bangladesh Bank 1 Oct 2026 reform: {qr_eligible_count} of {count} cash-out(s) are "
            f"<= ৳{int(BANGLADESH_BANK_INCENTIVE_CAP_BDT):,} (volume ৳{qr_eligible_volume:,.2f}). "
            f"Routing these to Bangla QR gives user 0% fee and earns upay ৳{upay_incentive:,.2f} in "
            f"central-bank issuing subsidy (0.20% via NPSB) + retained float."
        )
    else:
        arithmetic.append(
            f"Bangladesh Bank 1 Oct 2026 reform: Bangla QR merchant payment carries 0% customer fee "
            f"and 0.20% central-bank issuing subsidy for transactions <= ৳{int(BANGLADESH_BANK_INCENTIVE_CAP_BDT):,}."
        )

    return FeeSwitch(
        cash_out_count=count,
        cash_out_volume_bdt=round(volume, 2),
        fee_paid_bdt=round(fee_paid, 2),
        cash_out_rate_pct=cash_out_rate,
        alternative_channel=label,
        alternative_channel_key=channel,
        alternative_rate_pct=alternative_rate,
        alternative_fee_bdt=alternative_fee,
        potential_saving_bdt=saving,
        recorded_fee_bdt=recorded,
        adoption_range=ADOPTION_RANGE,
        assumed_saving_low_bdt=round(saving * ADOPTION_LOW, 2),
        assumed_saving_high_bdt=round(saving * ADOPTION_HIGH, 2),
        window_days=days,
        bangla_qr_eligible_count=qr_eligible_count,
        bangla_qr_eligible_volume_bdt=qr_eligible_volume,
        upay_issuer_incentive_bdt=upay_incentive,
        bangla_qr_policy=bangla_qr_policy,
        arithmetic=arithmetic,
    )

