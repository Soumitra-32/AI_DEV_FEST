# Data Assumptions — Shonchoy Copilot (synthetic data only)

This document is the single source of truth for every number the data pipeline
invents. The generator (`backend/data/generator.py`) reads these values from
`backend/data/config.yaml`; this file explains **why** they are what they are.

> **Everything in this project is synthetic.** There is no real upay data, no
> real customer data and no PII anywhere in the repo or the database. Fee rates
> are **assumed for simulation** and are **not official upay pricing**.

---

## 1. Scale and shape

| Item | Value | File |
|---|---|---|
| Users | 500 | `dataset.n_users` |
| History | 6 calendar months | `dataset.months` |
| Start date | 2025-01-01 | `dataset.start_date` |
| Storage | SQLite | `dataset.database` |
| Currency | BDT | `dataset.currency` |

Roughly 200,000+ transactions are expected (about 400 per user over 6 months).

## 2. Personas

Six personas, each with a documented income pattern. Persona mix depends on the
**district type** (metro / urban / rural), so districts differ from each other
but the rules stay in one place.

| Persona | Income pattern | Typical monthly inflow | Cash-out behaviour |
|---|---|---|---|
| `daily_wage` | irregular daily work, ~5 days/week | ৳18k–22k | 3 cash-outs/month |
| `shopkeeper` | daily sales, weekend peak (Fri/Sat) | ৳35k–50k | 4 cash-outs/month |
| `salaried` | one fixed credit on salary day (1st or last) | ৳25k–35k | 3 cash-outs/month |
| `student` | small periodic family remittance | ৳6k–10k | 1 cash-out/month |
| `gig_rider` | weekly payouts on a fixed weekday | ৳20k–28k | 4 cash-outs/month |
| `remittance_receiver` | large periodic inflow every 30 days | ৳30k–60k | 5 cash-outs/month |

**Budget rule — why the numbers add up.** Each month is generated in a fixed
order: income first, then everyday spending, bills and the weekly mobile top-up,
and finally the cash-outs. The cash-out *volume* is whatever is left over:

```
cash_out_volume = income - other_spending - savings_rate x income
```

`savings_rate` is drawn per user (mean 0.06, sd 0.06, clipped to 0–0.18) and a user
under month-end pressure keeps only 40% of it. So a typical user keeps a small
buffer and slowly grows it, while a pressured user spends nearly everything and
sits close to zero — which is what makes month-end shortfalls a real outcome
rather than a scripted one.

This rule exists because of a bug we hit first time round: with *fixed* cash-out
amounts every user drifted either permanently positive or permanently negative, and
"shortfall days" became a constant instead of a signal. Observed result now: every
persona keeps a positive net (৳0.8k–8k per month), balances never go negative, and
roughly half of all users hit at least one shortfall day.

The volume is split into a few uneven lumps, and `month_end_share` of them land in
the last week of the month — where cash actually runs out.

Income bands (`low` / `mid` / `high`, weights 0.40 / 0.40 / 0.20) multiply the
persona income by 0.75 / 1.00 / 1.35 so genuinely different income levels exist
inside a single persona. Age bands and language preference are sampled from
documented weights (90% `bn`).

## 3. Fee rates (assumed, not official pricing)

| Channel | Assumed fee |
|---|---|
| `cash_out` | **1.85%** of the amount |
| `app_transfer`, `merchant_payment`, `send_money`, `bill_payment`, `mobile_topup`, `agent_deposit` | 0% |

`fee_bdt` is computed as `round(amount_bdt * rate / 100, 2)` for every
transaction, so the fee saving quoted in the app is arithmetic on the data, not
a hardcoded number.

**Demo-number consistency.** 1.85% of ৳17,500 is ৳323.75, which is the
"about ৳320/month" figure in the demo. That requires ৳17,500 of monthly
cash-outs, i.e. **5 cash-outs averaging ৳3,500** — not 4 × ৳500 (which would
save only ~৳37). The Rahim demo profile in `demo_user:` encodes exactly this and
`backend/tests/test_generator.py` asserts it.

## 4. Month-end pressure (the core problem, deliberately injected)

For a **subset** of users (probability `month_end_pressure.applies_prob = 0.55`,
and only for personas `daily_wage`, `shopkeeper`, `salaried`, `gig_rider`) the
discretionary outflow is multiplied by `1 + intensity` on the **last 4 days of
each month**, where `intensity ~ N(0.45, 0.18)` and is clipped to ≥ 0.

* Not all 500 users are affected — this is intentional so the anomaly detector
  and the forecaster cannot trivially memorise "day 28 is always bad".
* Intensity is random per user, so pressure days have different magnitudes.
* Pressured users also keep only 40% of their savings rate
  (`dataset.pressure_savings_penalty`), so the pressure days are exactly what
  pushes their balance down to zero.
* Consequence: a realistic shortfall appears near month-end for pressured users,
  which is what the forecast must predict and the savings plan must survive.

## 5. Injected anomalies (with ground truth kept separate)

About **2%** of transactions (`anomalies.rate`) are selected for injection, split
across three types. Because a `rapid_repeat` injection adds extra rows, the final
share of anomalous rows lands at roughly **2.5–3%** of all transactions.

| Type | Share of injections | Injection rule |
|---|---|---|
| `unusually_large` | 45% | the transaction amount is multiplied by 4.0 |
| `unusual_time` | 35% | timestamp moved to 00:00–04:59, outside the 06:00–23:00 window |
| `rapid_repeat` | 20% | 3 near-identical transactions within 20 minutes |

Ground truth is written to a **separate `anomaly_labels` table** containing one
row per injected transaction; absence of a row means "normal". Any model scores
against this table, never against its own output.

## 6. Noise and overlap (so nothing is perfectly separable)

* Random missing days: not every viable income day produces a transaction.
* Irregular timing of everyday spending, amounts drawn from distributions.
* Persona behaviours overlap by design (a student can receive a large one-off
  transfer; a shopkeeper can have a slow week).
* `anomalies` are injected on top of normal behaviour rather than replacing it.

## 7. Districts (8–10 districts with different persona mixes)

10 districts spanning three types; persona mix is defined once per type and each
district has a population weight so Dhaka/Chattogram dominate:

* **metro** — Dhaka, Chattogram, Sylhet
* **urban** — Khulna, Rajshahi, Barishal, Cumilla, Mymensingh
* **rural** — Rangpur, Cox's Bazar

The `district` column is used only for the fairness analysis (metric gaps across
districts) — never as a model feature.

## 8. Financial consistency label (anti-circularity)

The label `is_stable_next_2_months` ("kept a stable balance and met obligations
over the next 2 months") is generated as:

```
latent_stability   ~ N(0, 1)                     # unobserved, per user
shock              ~ N(0,0.4) with prob 0.15, 0 otherwise
outcome_score      = latent_stability + N(0, 0.55) + shock
is_stable          = 1 if outcome_score > 0 else 0
```

* The label is **not** computed from the same formula as the model features
  (income regularity, balance buffer, fee burden, volatility).
* The latent variable **weakly influences behaviour** (higher latent → slightly
  higher balance buffer and more regular income), so the prediction task is
  learnable — but noisy, so no rule can reach a perfect AUC.
* `user_labels` stores `latent_stability`, `outcome_score`, `shock` and the
  binary label, so the score can be inspected honestly. A demo of the method,
  **not** a validated risk model.

## 9. Tables produced

| Table | Key columns |
|---|---|
| `users` | `user_id, persona, district, income_band, age_band, language_pref, cohort` |
| `transactions` | `transaction_id, user_id, persona, district, income_band, timestamp, type, channel, category, amount_bdt, fee_bdt, balance_after, is_shortfall` |
| `anomaly_labels` | `transaction_id, user_id, anomaly_type, detail` (injected rows only) |
| `user_labels` | `user_id, latent_stability, outcome_score, shock, is_stable_next_2_months` |
| `splits` | `user_id, split` (`train` / `val` / `test` / `demo`) |
| `generation_meta` | key/value provenance: seeds, sizes, generator version |

`transaction_id`, `is_shortfall` and the `cohort` column are additions beyond the
minimum schema; they exist for labelling, shortfall metrics and leakage checks.

`balance_after` is a running balance per user, computed in strict chronological
order from an opening balance of about **7 days of expected income**. **A wallet
cannot go negative**: if an outflow is larger than the available balance it is
clipped to what the wallet can fund and the row is flagged `is_shortfall = 1`
(clipped rows are the "wallet hit zero" days the product is about). An outflow the
wallet cannot fund at all is dropped instead of being stored as a zero-taka row.
Clipping keeps the arithmetic exact — `balance_after` always equals the previous
balance plus the recorded amount minus any fee.

Observed baseline in the generated data: ~0.3 shortfall days per user-month, with
roughly half of all users hitting at least one shortfall day over 6 months.

## 10. Anti-circularity protocol

1. **Split by user, never by row**: 70% train / 15% validation / 15% test.
2. The **test cohort is generated with a different seed** (`seeds.test = 1337`)
   from the train/validation cohort (`seeds.train = 42`), so the held-out users
   are not merely re-draws of the same random stream.
3. The test set is never used for tuning.
4. Noise and persona overlap are added so patterns are not perfectly separable.
5. Honest metrics are reported, including cases where a model is weak.
6. README and report state that the patterns are **injected** and that the real
   test is controlled validation with real data.

## 11. Demo user "Rahim"

Generated by `backend/scripts/seed_demo_user.py`, cohort `demo`, and **excluded
from train/val/test** so demo data never leaks into evaluation.

| Field | Value |
|---|---|
| Persona / district | `daily_wage` / Dhaka, income band `mid` |
| Income | ৳1,750/day, 6 days/week (≈ ৳45,500/month) |
| Spending | ৳550/day average + ~৳1,500 monthly bills |
| Savings rate | **20% of income** — the ৳8k–10k/month that makes the goal feasible |
| Cash-outs | **5 lumps per month**, volume from the budget rule: ≈ ৳17,500/month → **৳323.75 fee** (measured 6-month average ≈ ৳336) |
| Pressure | last 4 days of each month, intensity 0.60, with 40% of his cash-outs in the last week |
| Goal (demo) | save ৳30,000 in 6 months (৳5,000/month) |

The profile leaves roughly ৳8k–9k of monthly surplus, so a ৳5,000/month plan is
feasible, and the fee-switch suggestion is worth ≈৳320/month for Rahim. His wallet
balance stays positive (minimum ≈ ৳3.5k in the generated history), and the
month-end pressure shows up as the spending spike on days 28–31 that the forecast
must flag — not as an artificially forced shortfall.

## 12. Known limitations (stated honestly)

* Distributions are **chosen by us**, so model accuracy here does not transfer
  to real users; only controlled validation with real data can establish that.
* Fee rates are assumptions, not published upay pricing.
* Month-end pressure is injected, not observed.
* 500 users is small for fairness claims; group-level gaps are reported with
  that caveat.
* The stability label is synthetic and weakly driven by latent behaviour, so its
  AUC should be read as a demonstration of method, not a risk-model result.



