"""Synthetic user and transaction generator for Shonchoy Copilot.

Everything here is simulated: there is no real upay data and no PII.

Assumptions live in ``backend/data/config.yaml`` and are explained in
``docs/DATA_ASSUMPTIONS.md``. Key design points:

* Two cohorts are generated with *different seeds* -- the train/validation
  cohort (``seeds.train``) and the held-out test cohort (``seeds.test``). This
  is part of the anti-circularity protocol.
* Month-end pressure is injected for a subset of users only, with random
  strength, so "day 28 is always bad" is never a deterministic rule.
* Balances are recomputed in chronological order per user. A negative balance
  means the user ran short that day (in reality covered by informal borrowing)
  and the row is flagged ``is_shortfall = 1``.
"""
from __future__ import annotations

import sqlite3
import zlib
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import yaml

from . import labels as labels_module

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

USER_COLUMNS = [
    "user_id",
    "persona",
    "district",
    "income_band",
    "age_band",
    "language_pref",
    "cohort",
]

TRANSACTION_COLUMNS = [
    "transaction_id",
    "user_id",
    "persona",
    "district",
    "income_band",
    "timestamp",
    "type",
    "channel",
    "category",
    "amount_bdt",
    "fee_bdt",
    "balance_after",
    "is_shortfall",
]

# columns available before balances are finalised
CORE_TRANSACTION_COLUMNS = [
    "transaction_id",
    "user_id",
    "persona",
    "district",
    "income_band",
    "timestamp",
    "type",
    "channel",
    "category",
    "amount_bdt",
    "fee_bdt",
]


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------
def load_config(path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load the YAML pipeline configuration (defaults to ``data/config.yaml``)."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    cfg["_config_path"] = str(config_path)
    return cfg


def resolve_db_path(cfg: Mapping[str, Any], override: Optional[str | Path] = None) -> Path:
    """Resolve the SQLite path; relative paths are relative to the repo root."""
    raw = Path(override or cfg["dataset"]["database"])
    return raw if raw.is_absolute() else REPO_ROOT / raw


def dataset_days(
    cfg: Mapping[str, Any],
    months: Optional[int] = None,
    start_date: Optional[str] = None,
) -> pd.DatetimeIndex:
    """Calendar days covered by a run (``months`` calendar months from the start)."""
    start = pd.Timestamp(start_date or cfg["dataset"]["start_date"])
    horizon = int(months or cfg["dataset"]["months"])
    end = start + pd.DateOffset(months=horizon)
    return pd.date_range(start, end - pd.Timedelta(days=1), freq="D")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _normalised(weights: Sequence[float]) -> np.ndarray:
    arr = np.asarray(weights, dtype=float)
    total = float(arr.sum())
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    return arr / total


def _choose(rng: np.random.Generator, options: Sequence[Any], weights: Optional[Sequence[float]] = None) -> Any:
    probs = None if weights is None else _normalised(weights)
    return options[int(rng.choice(len(options), p=probs))]


def user_rng(seed: int, user_id: str) -> np.random.Generator:
    """Deterministic per-user RNG (independent of iteration order and of PYTHONHASHSEED)."""
    return np.random.default_rng((int(seed) * 1_000_003 + zlib.crc32(user_id.encode())) % (2**32))


def round_bdt(value: float, round_to: float) -> float:
    """Round a taka amount to the nearest ``round_to`` (never below ``round_to``)."""
    if round_to <= 0:
        return float(round(value, 2))
    return float(max(round_to, int(round(value / round_to)) * round_to))


def _amount(rng: np.random.Generator, mean: float, std: float, round_to: float, multiplier: float = 1.0) -> float:
    draw = rng.normal(mean * multiplier, max(std * multiplier, 1.0))
    return round_bdt(draw, round_to)


def fee_for_amount(cfg: Mapping[str, Any], channel: str, amount: float) -> float:
    """Fee in BDT for ``amount`` on ``channel``, from the assumed rate table."""
    rates = cfg["fee_rates"]
    percent = float(rates["by_channel"].get(channel, 0.0))
    flat = float(rates.get("flat_bdt", {}).get(channel, 0.0))
    fee = max(amount * percent / 100.0 + flat, float(rates.get("min_fee_bdt", 0.0)))
    return round(fee, 2)


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------
def sample_users(
    cfg: Mapping[str, Any],
    seed: int,
    n_users: int,
    user_id_start: int = 1,
    cohort: str = "train_val",
) -> pd.DataFrame:
    """Sample users: district (its type drives the persona mix), band, age, language."""
    rng = np.random.default_rng(int(seed))
    districts = cfg["districts"]
    mixes = cfg["district_persona_mix"]
    district_weights = [float(d.get("population_weight", 1.0)) for d in districts]

    bands = cfg["income_bands"]
    band_names = list(bands)
    band_weights = [float(bands[b]["weight"]) for b in band_names]
    ages = cfg["age_bands"]
    age_names = list(ages)
    age_weights = [float(ages[a]) for a in age_names]
    langs = cfg["language_pref"]
    lang_names = list(langs)
    lang_weights = [float(langs[lang]) for lang in lang_names]

    rows: List[Dict[str, Any]] = []
    for index in range(n_users):
        district = _choose(rng, districts, district_weights)
        mix = mixes[district["type"]]
        persona = _choose(rng, list(mix), [float(value) for value in mix.values()])
        rows.append(
            {
                "user_id": f"U{user_id_start + index:04d}",
                "persona": persona,
                "district": district["name"],
                "income_band": _choose(rng, band_names, band_weights),
                "age_band": _choose(rng, age_names, age_weights),
                "language_pref": _choose(rng, lang_names, lang_weights),
                "cohort": cohort,
            }
        )
    return pd.DataFrame(rows, columns=USER_COLUMNS)


def pressure_for_user(
    cfg: Mapping[str, Any],
    persona: str,
    rng: np.random.Generator,
) -> Optional[Dict[str, float]]:
    """Month-end pressure applies to a *subset* of users, with random strength."""
    settings = cfg["month_end_pressure"]
    if persona not in settings["personas"]:
        return None
    if float(rng.random()) > float(settings["applies_prob"]):
        return None
    intensity = float(max(0.0, rng.normal(settings["intensity_mean"], settings["intensity_std"])))
    return {"intensity": intensity, "spike_days": int(settings["spike_days"])}


# ---------------------------------------------------------------------------
# transactions
# ---------------------------------------------------------------------------
def _timestamp(day: pd.Timestamp, rng: np.random.Generator, cfg: Mapping[str, Any]) -> pd.Timestamp:
    low, high = cfg["dataset"]["active_hours"]
    hour = int(rng.integers(int(low), int(high) + 1))
    minute = int(rng.integers(0, 60))
    second = int(rng.integers(0, 60))
    return day + pd.Timedelta(hours=hour, minutes=minute, seconds=second)


def _make_row(
    cfg: Mapping[str, Any],
    user: Mapping[str, Any],
    when: pd.Timestamp,
    category: str,
    amount: float,
    counter: List[int],
) -> Dict[str, Any]:
    """Build one transaction row; type/channel/fee all come from config."""
    channel = cfg["channel_by_category"][category]
    if category in cfg["income_categories"]:
        tx_type = "income"
    elif channel == "cash_out":
        tx_type = "cash_out"
    else:
        tx_type = "expense"
    counter[0] += 1
    rounded = round(float(amount), 2)
    return {
        "transaction_id": f"{user['user_id']}-{counter[0]:05d}",
        "user_id": user["user_id"],
        "persona": user["persona"],
        "district": user["district"],
        "income_band": user["income_band"],
        "timestamp": when,
        "type": tx_type,
        "channel": channel,
        "category": category,
        "amount_bdt": rounded,
        "fee_bdt": fee_for_amount(cfg, channel, rounded),
    }


def _income_rows(
    cfg: Mapping[str, Any],
    user: Mapping[str, Any],
    profile: Mapping[str, Any],
    month_days: List[pd.Timestamp],
    origin: pd.Timestamp,
    rng: np.random.Generator,
    band_multiplier: float,
    regularity: float,
    counter: List[int],
) -> List[Dict[str, Any]]:
    income = profile["income"]
    style = income["style"]
    round_to = float(cfg["dataset"]["round_to_bdt"])
    rows: List[Dict[str, Any]] = []

    if style in {"irregular_daily", "merchant_daily"}:
        probability = float(np.clip(income["days_per_week"] / 7.0 * regularity, 0.0, 1.0))
        weekend = set(cfg["dataset"]["weekend_weekdays"])
        for day in month_days:
            if float(rng.random()) > probability:
                continue
            amount = _amount(rng, income["mean_bdt"], income["std_bdt"], round_to, band_multiplier)
            if style == "merchant_daily" and day.weekday() in weekend:
                amount = round_bdt(amount * float(income.get("weekend_peak_multiplier", 1.0)), round_to)
            category = "wage" if style == "irregular_daily" else "sales"
            rows.append(_make_row(cfg, user, _timestamp(day, rng, cfg), category, amount, counter))

    elif style == "monthly_fixed":
        day = month_days[0] if income.get("salary_day", "first") == "first" else month_days[-1]
        amount = _amount(rng, income["mean_bdt"], income["std_bdt"], round_to, band_multiplier)
        rows.append(_make_row(cfg, user, _timestamp(day, rng, cfg), "salary", amount, counter))

    elif style == "weekly":
        weekday = int(income["payout_weekday"])
        for day in month_days:
            if day.weekday() != weekday:
                continue
            amount = _amount(rng, income["mean_bdt"], income["std_bdt"], round_to, band_multiplier)
            rows.append(_make_row(cfg, user, _timestamp(day, rng, cfg), "gig_payout", amount, counter))

    elif style == "periodic":
        every = int(income["every_n_days"])
        for day in month_days:
            if (day - origin).days % every != 0:
                continue
            amount = _amount(rng, income["mean_bdt"], income["std_bdt"], round_to, band_multiplier)
            rows.append(_make_row(cfg, user, _timestamp(day, rng, cfg), "remittance", amount, counter))

    else:  # pragma: no cover - guards a typo in config.yaml
        raise ValueError(f"unknown income style: {style!r}")

    return rows


def _spend_rows(
    cfg: Mapping[str, Any],
    user: Mapping[str, Any],
    profile: Mapping[str, Any],
    month_days: List[pd.Timestamp],
    rng: np.random.Generator,
    spend_multiplier: float,
    pressure: Optional[Mapping[str, float]],
    counter: List[int],
) -> List[Dict[str, Any]]:
    """Everyday spending, boosted on pressure days (last few days of the month)."""
    spend = profile["spend"]
    round_to = float(cfg["dataset"]["round_to_bdt"])
    categories = list(spend["categories"])
    spike_days = set(month_days[-int(pressure["spike_days"]):]) if pressure else set()

    rows: List[Dict[str, Any]] = []
    for day in month_days:
        if float(rng.random()) < 0.05:  # noise: some days simply have no spending
            continue
        total = _amount(rng, spend["daily_mean_bdt"], spend["daily_std_bdt"], round_to, spend_multiplier)
        if day in spike_days:
            total = round_bdt(total * (1.0 + float(pressure["intensity"])), round_to)
        splits = 2 if (len(categories) > 2 and float(rng.random()) < 0.30) else 1
        pieces = [total] if splits == 1 else [round_bdt(total * 0.6, round_to), round_bdt(total * 0.4, round_to)]
        for piece in pieces:
            if piece <= 0:
                continue
            category = _choose(rng, categories)
            rows.append(_make_row(cfg, user, _timestamp(day, rng, cfg), category, piece, counter))
    return rows


def _bill_rows(
    cfg: Mapping[str, Any],
    user: Mapping[str, Any],
    profile: Mapping[str, Any],
    month_days: List[pd.Timestamp],
    rng: np.random.Generator,
    band_multiplier: float,
    counter: List[int],
) -> List[Dict[str, Any]]:
    """Monthly utility bills plus a small weekly mobile top-up."""
    bills = profile["bills"]
    round_to = float(cfg["dataset"]["round_to_bdt"])
    rows: List[Dict[str, Any]] = []

    count = min(int(bills["count_per_month"]), len(month_days))
    picked = sorted(int(index) for index in rng.choice(len(month_days), size=count, replace=False))
    for index in picked:
        day = month_days[index]
        amount = _amount(rng, bills["mean_bdt"], bills["std_bdt"], round_to, band_multiplier)
        rows.append(_make_row(cfg, user, _timestamp(day, rng, cfg), "utilities", amount, counter))

    for day in month_days:
        if day.day % 7 == 1:
            amount = _amount(rng, 120, 40, round_to, 1.0)
            rows.append(_make_row(cfg, user, _timestamp(day, rng, cfg), "mobile_topup", amount, counter))
    return rows


def _cash_out_rows(
    cfg: Mapping[str, Any],
    user: Mapping[str, Any],
    profile: Mapping[str, Any],
    month_days: List[pd.Timestamp],
    rng: np.random.Generator,
    counter: List[int],
    volume: float,
) -> List[Dict[str, Any]]:
    """Split the month's cash-out *volume* into a few lumpy cash-outs.

    The volume is derived from the monthly budget (income minus other spending
    minus what the user keeps), so cash-outs scale with what the user actually
    earned instead of being a fixed amount. A share of the lumps is placed in the
    last week of the month, which is where the cash runs out.
    """
    cash = profile["cash_out"]
    round_to = float(cfg["dataset"]["round_to_bdt"])
    minimum = float(cash["min_lump_bdt"])
    lumps = int(cash["lumps_per_month"])
    if lumps <= 0 or volume < minimum * lumps:
        return []

    last_week = month_days[-7:]
    month_end_share = float(cash.get("month_end_share", 0.0))
    n_end = int(min(round(lumps * month_end_share), len(last_week)))
    picked: List[pd.Timestamp] = []
    if n_end > 0:
        picked += [last_week[int(index)] for index in rng.choice(len(last_week), size=n_end, replace=False)]
    earlier = month_days[: max(1, len(month_days) - len(last_week))]
    n_early = min(lumps - len(picked), len(earlier))
    if n_early > 0:
        picked += [earlier[int(index)] for index in rng.choice(len(earlier), size=n_early, replace=False)]
    picked = sorted(set(picked))
    if not picked:
        return []

    weights = np.clip(
        rng.normal(1.0, float(cash["size_std_ratio"]), size=len(picked)), 0.25, 2.0
    )
    weights = weights / weights.sum()

    rows: List[Dict[str, Any]] = []
    for day, weight in zip(picked, weights):
        amount = round_bdt(volume * float(weight), round_to)
        if amount < minimum:
            continue
        rows.append(_make_row(cfg, user, _timestamp(day, rng, cfg), "cash_out", amount, counter))
    return rows


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
def normalise_pressure(
    cfg: Mapping[str, Any],
    pressure: Optional[Mapping[str, Any]],
) -> Optional[Dict[str, float]]:
    """Fill missing keys of a pressure override (e.g. the demo profile's) from config."""
    if not pressure:
        return None
    defaults = cfg["month_end_pressure"]
    return {
        "intensity": float(pressure.get("intensity", defaults["intensity_mean"])),
        "spike_days": int(pressure.get("spike_days", defaults["spike_days"])),
    }


def savings_rate_for(cfg: Mapping[str, Any], user_id: str, seed: int, pressured: bool) -> float:
    """Per-user share of income kept aside (pressured users keep almost nothing).

    This is what makes the dataset economically coherent: cash-outs and spending
    consume the rest, so balances hover near zero and month-end pressure really
    does push some users short.
    """
    settings = cfg["dataset"]["savings_rate"]
    rng = user_rng(int(seed) + 101, user_id)
    rate = float(
        np.clip(rng.normal(settings["mean"], settings["std"]), settings["min"], settings["max"])
    )
    if pressured:
        rate *= float(cfg["dataset"]["pressure_savings_penalty"])
    return rate


def expected_daily_income(cfg: Mapping[str, Any], persona: str) -> float:
    """Average daily inflow for a persona, derived from its income style."""
    income = cfg["personas"][persona]["income"]
    style = income["style"]
    if style in {"irregular_daily", "merchant_daily"}:
        return float(income["mean_bdt"]) * float(income["days_per_week"]) / 7.0
    if style == "weekly":
        return float(income["mean_bdt"]) / 7.0
    if style == "monthly_fixed":
        return float(income["mean_bdt"]) / 30.0
    return float(income["mean_bdt"]) / float(income["every_n_days"])


def generate_user_transactions(
    cfg: Mapping[str, Any],
    user: Mapping[str, Any],
    profile: Mapping[str, Any],
    days: pd.DatetimeIndex,
    seed: int,
    latent: float = 0.0,
    pressure: Optional[Mapping[str, float]] = None,
) -> pd.DataFrame:
    """Generate the (pre-balance) transaction log for a single user.

    ``latent`` is the user's hidden stability value; it influences behaviour
    only weakly (see docs/DATA_ASSUMPTIONS.md §8).
    """
    rng = user_rng(seed, user["user_id"])
    if pressure is None:
        pressure = pressure_for_user(cfg, user["persona"], rng)
    else:
        pressure = normalise_pressure(cfg, pressure)

    influence = float(cfg["stability_label"]["behaviour_influence"])
    regularity = float(np.clip(1.0 + influence * latent, 0.6, 1.4))
    band_multiplier = float(cfg["income_bands"][user["income_band"]]["income_multiplier"])
    spend_multiplier = float(np.clip(1.0 - 0.30 * influence * latent, 0.7, 1.3)) * float(np.sqrt(band_multiplier))
    profile_savings_rate = profile.get("savings_rate")
    if profile_savings_rate is None:
        savings_rate = savings_rate_for(cfg, user["user_id"], seed, pressured=pressure is not None)
    else:
        savings_rate = float(profile_savings_rate)

    months: Dict[Tuple[int, int], List[pd.Timestamp]] = {}
    for day in days:
        months.setdefault((day.year, day.month), []).append(day)

    origin = days[0]
    counter = [0]
    rows: List[Dict[str, Any]] = []
    for key in sorted(months):
        month_days = months[key]
        income_rows = _income_rows(
            cfg, user, profile, month_days, origin, rng, band_multiplier, regularity, counter
        )
        spend_rows = _spend_rows(
            cfg, user, profile, month_days, rng, spend_multiplier, pressure, counter
        )
        bill_rows = _bill_rows(cfg, user, profile, month_days, rng, band_multiplier, counter)

        # Budget rule: what is left after everyday spending and saving is cashed out.
        inflow = float(sum(row["amount_bdt"] for row in income_rows))
        other_outflow = float(sum(row["amount_bdt"] for row in spend_rows + bill_rows))
        cash_volume = max(0.0, inflow - other_outflow - savings_rate * inflow)

        cash_rows = _cash_out_rows(cfg, user, profile, month_days, rng, counter, cash_volume)
        rows += income_rows + spend_rows + bill_rows + cash_rows

    frame = pd.DataFrame(rows, columns=CORE_TRANSACTION_COLUMNS)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame


def build_transactions(
    cfg: Mapping[str, Any],
    users: pd.DataFrame,
    latent: Mapping[str, float],
    seed: int,
) -> pd.DataFrame:
    """Generate pre-balance transactions for every user of a cohort."""
    days = dataset_days(cfg)
    frames = [
        generate_user_transactions(
            cfg,
            user,
            cfg["personas"][user["persona"]],
            days,
            seed,
            latent=float(latent.get(user["user_id"], 0.0)),
        )
        for user in users.to_dict("records")
    ]
    if not frames:
        return pd.DataFrame(columns=CORE_TRANSACTION_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def opening_balances(
    cfg: Mapping[str, Any],
    users: pd.DataFrame,
    seed: int,
    latent: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    """Opening wallet balance per user (a few days of expected income)."""
    buffer_days = float(cfg["dataset"]["start_balance_days"])
    influence = float(cfg["stability_label"]["behaviour_influence"])
    balances: Dict[str, float] = {}
    for user in users.to_dict("records"):
        rng = user_rng(seed + 7, user["user_id"])
        band_multiplier = float(cfg["income_bands"][user["income_band"]]["income_multiplier"])
        buffer_multiplier = 1.0 + 0.5 * influence * float((latent or {}).get(user["user_id"], 0.0))
        value = (
            expected_daily_income(cfg, user["persona"])
            * buffer_days
            * band_multiplier
            * buffer_multiplier
            * float(rng.normal(1.0, 0.15))
        )
        balances[user["user_id"]] = max(0.0, round(value, 2))
    return balances


def _apply_balances(
    cfg: Mapping[str, Any],
    frame: pd.DataFrame,
    starts: Mapping[str, float],
) -> pd.DataFrame:
    """Walk each user's history in order, funding what the wallet can afford.

    A wallet cannot go negative, so an outflow that exceeds the available balance
    is capped at what the wallet can fund and the row is flagged
    ``is_shortfall = 1``. Clipped rows are the "wallet hit zero" days the product
    is about; the arithmetic stays exact either way. An outflow the wallet cannot
    fund at all ends up at zero taka and is dropped by the caller.
    """
    rates = cfg["fee_rates"]["by_channel"]
    balances = np.zeros(len(frame), dtype=float)
    amounts = frame["amount_bdt"].to_numpy(dtype=float).copy()
    fees = frame["fee_bdt"].to_numpy(dtype=float).copy()
    shortfall = np.zeros(len(frame), dtype=int)

    balance = 0.0
    current_user = None
    for position, row in enumerate(frame.itertuples(index=False)):
        if row.user_id != current_user:
            current_user = row.user_id
            balance = float(starts[row.user_id])
        amount = float(amounts[position])
        fee = float(fees[position])
        if row.type == "income":
            balance += amount - fee
        else:
            need = amount + fee
            if need > balance:
                shortfall[position] = 1
                percent = float(rates.get(row.channel, 0.0)) / 100.0
                affordable = float(np.floor(max(0.0, balance / (1.0 + percent)) * 100) / 100)
                amount = affordable
                fee = round(amount * percent, 2)
                if amount + fee > balance:
                    amount = round(max(0.0, balance - fee), 2)
                balance -= amount + fee
                amounts[position] = amount
                fees[position] = fee
            else:
                balance -= need
        balances[position] = round(balance, 2)

    result = frame.copy()
    result["amount_bdt"] = amounts
    result["fee_bdt"] = fees
    result["balance_after"] = balances
    result["is_shortfall"] = shortfall
    return result


def finalize_balances(
    cfg: Mapping[str, Any],
    transactions: pd.DataFrame,
    users: pd.DataFrame,
    seed: int,
    latent: Optional[Mapping[str, float]] = None,
) -> pd.DataFrame:
    """Add ``balance_after`` and ``is_shortfall`` in strict chronological order."""
    frame = transactions.copy()
    if frame.empty:
        frame["balance_after"] = pd.Series(dtype=float)
        frame["is_shortfall"] = pd.Series(dtype=int)
        return frame[TRANSACTION_COLUMNS]

    starts = opening_balances(cfg, users, seed, latent)
    frame = frame.sort_values(["user_id", "timestamp", "transaction_id"], kind="stable").reset_index(drop=True)
    settled = _apply_balances(cfg, frame, starts)
    # an outflow the wallet could not fund at all never happened: drop the empty row
    settled = settled.loc[settled["amount_bdt"] > 0].reset_index(drop=True)
    return settled[TRANSACTION_COLUMNS]


def cohort_latent(cfg: Mapping[str, Any], users: pd.DataFrame, seed: int) -> Dict[str, float]:
    """Latent stability values for a cohort, drawn exactly as the generator does."""
    return labels_module.sample_latent_stability(cfg, users["user_id"].tolist(), seed=seed)


def generate_cohort(
    cfg: Mapping[str, Any],
    seed: int,
    n_users: int,
    user_id_start: int = 1,
    cohort: str = "train_val",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """Full pipeline for one cohort: users -> transactions -> anomalies -> balances."""
    users = sample_users(cfg, seed=seed, n_users=n_users, user_id_start=user_id_start, cohort=cohort)
    latent = cohort_latent(cfg, users, seed)
    transactions = build_transactions(cfg, users, latent, seed=seed)
    transactions, anomaly_labels = labels_module.inject_anomalies(
        cfg, transactions, seed=int(cfg["seeds"]["anomaly"]) + int(seed)
    )
    transactions = finalize_balances(cfg, transactions, users, seed=seed, latent=latent)
    # a label must never point at a transaction that the wallet could not fund
    known = set(transactions["transaction_id"])
    anomaly_labels = anomaly_labels.loc[anomaly_labels["transaction_id"].isin(known)].reset_index(drop=True)
    return users, transactions, anomaly_labels, latent


# ---------------------------------------------------------------------------
# persistence (SQLite)
# ---------------------------------------------------------------------------
USERS_DDL = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    persona TEXT NOT NULL,
    district TEXT NOT NULL,
    income_band TEXT NOT NULL,
    age_band TEXT NOT NULL,
    language_pref TEXT NOT NULL,
    cohort TEXT NOT NULL
);
"""

TRANSACTIONS_DDL = """
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    persona TEXT NOT NULL,
    district TEXT NOT NULL,
    income_band TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    channel TEXT NOT NULL,
    category TEXT NOT NULL,
    amount_bdt REAL NOT NULL,
    fee_bdt REAL NOT NULL,
    balance_after REAL NOT NULL,
    is_shortfall INTEGER NOT NULL DEFAULT 0
);
"""

META_DDL = "CREATE TABLE IF NOT EXISTS generation_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"

INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_tx_user_ts ON transactions(user_id, timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_tx_channel ON transactions(channel);",
    "CREATE INDEX IF NOT EXISTS idx_tx_type ON transactions(type);",
]


def connect(db_path: str | Path, replace: bool = False) -> sqlite3.Connection:
    """Open (and optionally recreate) the SQLite database."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if replace and path.exists():
        path.unlink()
    connection = sqlite3.connect(str(path))
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_core_tables(connection: sqlite3.Connection) -> None:
    """Create the tables owned by this module."""
    connection.execute(USERS_DDL)
    connection.execute(TRANSACTIONS_DDL)
    connection.execute(META_DDL)
    for statement in INDEX_DDL:
        connection.execute(statement)


def write_core(
    connection: sqlite3.Connection,
    users: pd.DataFrame,
    transactions: pd.DataFrame,
    meta: Optional[Mapping[str, Any]] = None,
) -> None:
    """Insert users, transactions and provenance metadata."""
    init_core_tables(connection)
    connection.executemany(
        "INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
        users[USER_COLUMNS].to_numpy().tolist(),
    )
    frame = transactions[TRANSACTION_COLUMNS].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    frame["is_shortfall"] = frame["is_shortfall"].astype(int)
    connection.executemany(
        "INSERT OR REPLACE INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        frame.to_numpy().tolist(),
    )
    if meta is not None:
        write_meta(connection, meta)
    connection.commit()


def write_meta(connection: sqlite3.Connection, meta: Mapping[str, Any]) -> None:
    """Store provenance rows (seeds, sizes, generator version) in ``generation_meta``."""
    connection.execute(META_DDL)
    connection.executemany(
        "INSERT OR REPLACE INTO generation_meta VALUES (?, ?)",
        [(str(key), str(value)) for key, value in meta.items()],
    )
    connection.commit()


def read_table(db_path: str | Path, table: str) -> pd.DataFrame:
    """Read a whole table into a DataFrame (timestamps parsed when present)."""
    connection = sqlite3.connect(str(db_path))
    try:
        frame = pd.read_sql_query(f"SELECT * FROM {table}", connection)
    finally:
        connection.close()
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame






