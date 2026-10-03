"""Pressure-day detection (rules layer).

A pressure day is a forecast day whose predicted closing balance drops below
the safety buffer — the "wallet will be tight that day" warning from the demo
story (days 28-31). Pure rules on top of the forecast: no model, no LLM,
fully explainable.

Deliberately balance-based, never net-based: a negative-net day against a
healthy balance (e.g. −৳30 with ৳58,000 in the wallet) is not pressure, and
flagging it cried wolf on the demo user. The net still matters for *why* —
``both`` marks a below-buffer day the day's own outflow drove.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PressureDay:
    date: str
    predicted_net_bdt: float
    predicted_balance_bdt: float
    reason_code: str  # "below_buffer" | "both"


def _reason(net: float, balance: float, buffer: float) -> str | None:
    if balance >= buffer:
        return None
    return "both" if net < 0 else "below_buffer"


def detect(
    days: list[dict],
    opening_balance_bdt: float,
    safety_buffer_bdt: float,
) -> list[PressureDay]:
    """Flag pressure days from a forecast's per-day nets.

    ``days`` carries ``date`` + ``predicted_net_bdt``; balances run forward
    from ``opening_balance_bdt``. Returns only the flagged days, in order.
    """
    flagged: list[PressureDay] = []
    balance = float(opening_balance_bdt)
    for day in days:
        net = float(day["predicted_net_bdt"])
        balance += net
        reason = _reason(net, balance, float(safety_buffer_bdt))
        if reason is not None:
            flagged.append(PressureDay(
                date=str(day["date"]),
                predicted_net_bdt=round(net, 2),
                predicted_balance_bdt=round(balance, 2),
                reason_code=reason,
            ))
    return flagged

