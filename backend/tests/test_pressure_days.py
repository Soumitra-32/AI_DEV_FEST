"""Pressure-day tests (Phase 3): the month-end warning the demo is built on.

Pure rules over a forecast's per-day nets — no model, no database — so the
reason codes and the running balance are pinned exactly.
"""

from __future__ import annotations

from backend.rules import pressure_days


def _day(date: str, net: float) -> dict:
    return {"date": date, "predicted_net_bdt": net}


def test_flags_a_negative_net_day() -> None:
    flagged = pressure_days.detect(
        [_day("2025-07-01", 900), _day("2025-07-02", -250)],
        opening_balance_bdt=50000, safety_buffer_bdt=2000,
    )
    assert [item.date for item in flagged] == ["2025-07-02"]
    assert flagged[0].reason_code == "negative_net"
    assert flagged[0].predicted_net_bdt == -250


def test_running_balance_carries_forward_and_can_fall_below_the_buffer() -> None:
    flagged = pressure_days.detect(
        [_day("2025-07-01", 100), _day("2025-07-02", -1500), _day("2025-07-03", -600)],
        opening_balance_bdt=1500, safety_buffer_bdt=500,
    )
    assert [(item.date, item.reason_code) for item in flagged] == [
        ("2025-07-02", "both"),   # net negative *and* balance under the buffer
        ("2025-07-03", "both"),   # still negative net, balance further under
    ]
    assert flagged[0].predicted_balance_bdt == 100.0


def test_a_calm_window_flags_nothing() -> None:
    flagged = pressure_days.detect(
        [_day("2025-07-01", 800), _day("2025-07-02", 650)],
        opening_balance_bdt=9000, safety_buffer_bdt=2000,
    )
    assert flagged == []


def test_a_positive_net_can_still_be_a_pressure_day() -> None:
    """Thin days matter: a small positive net can leave the wallet under the buffer."""
    flagged = pressure_days.detect(
        [_day("2025-07-01", 120)],
        opening_balance_bdt=100, safety_buffer_bdt=1000,
    )
    assert len(flagged) == 1
    assert flagged[0].reason_code == "below_buffer"
    assert flagged[0].predicted_balance_bdt == 220.0


def test_flagged_days_keep_the_order_of_the_forecast() -> None:
    days = [_day(f"2025-07-{day:02d}", -100) for day in range(1, 6)]
    flagged = pressure_days.detect(days, opening_balance_bdt=1000, safety_buffer_bdt=0)
    assert [item.date for item in flagged] == [day["date"] for day in days]