# Shonchoy Copilot — Project Report
**AI DEV FEST 2026 · DIU CPC × upay · Track 03: Customer Innovation & Financial Independence**
**API version 0.7.0 · All numbers measured, none invented (see §8 for method).**

## 1. Problem statement (guideline §10 template)

For cash-dependent, irregular-income upay users, month-end cash shortfalls and
repeated avoidable cash-out fees cause missed savings goals, borrowing stress,
and lost money every month. We built Shonchoy Copilot, a Bangla-first AI
financial coach that uses transaction history to forecast cash flow, detect
avoidable spending, and generate a feasible savings plan, with success measured
by (a) taka saved in avoidable fees, (b) shortfall days avoided, (c) savings-goal
hit-rate, and (d) forecast MAE vs baseline.

## 2. What we built

Next.js Bangla/English app with voice, backed by FastAPI. Flow: transactions
explained → health/coach → 14-day forecast with pressure days → savings plan
with trade-offs → fee-switch suggestion → behavior-triggered tips →
consistency signal (band, never a score) → do-nothing comparison. Voice on the
home page parses spoken Bangla into goal + months (`POST /parse-goal`) and
routes straight into a computed plan.

Live endpoints: `GET /health`, `GET /me`, `POST /forecast`,
`POST /savings-plan`, `POST /anomalies`, `POST /credit-readiness`,
`POST /chat-explain`, `POST /parse-goal`.

## 3. Data (synthetic, privacy by design)

Fully synthetic SQLite dataset (`backend/scripts/generate_data.py`, assumptions
in `docs/DATA_ASSUMPTIONS.md`): **501 users × 6 months, 176,416 transactions**,
split by user 70/15/15 (350 train / 75 val / 75 test) plus 1 demo user (Rahim,
excluded from every evaluation). 4,946 injected anomalies (2.80%) with ground
truth in a separate table. Documented assumptions: 1.85% cash-out fee
(simulation rate, not official upay pricing), 0% app-transfer alternative,
month-end pressure for selected personas, ~2–3% anomalies in 3 types. No real
PII anywhere; request logs carry provider labels only.

## 4. Model results (held-out TEST users, demo excluded)

### 4.1 Cash-flow forecast — LightGBM vs baselines (14-day horizon, 75 test users)

Headline = 14-day totals (what the savings solver consumes), complete
windows only (truncated windows are dropped, so every total covers 14 days):

| Flow | Model MAE | Seasonal-naive MAE | Trailing-avg MAE | Improvement vs best |
|---|---|---|---|---|
| Inflow | 2,407.02 | 13,970.11 | 9,878.65 | **+75.6%** |
| Outflow | 2,780.92 | 12,252.64 | 6,378.28 | **+56.4%** |
| Net | 3,435.20 | 20,875.83 | 13,418.24 | **+74.4%** |

Target (plan §4): ≥15% better than the best baseline on every flow — **met on
all three** (`target_met: true`, 109,914 scored cells = 7,851 complete
windows × 14).

**What changed vs the previous report:** the evaluation now scores complete
windows only, builds weekday shapes strictly before each window (no
look-ahead), spreads net additively (no division by signed weekday sums),
and defines net fee-inclusively everywhere (GAP-04). The net jump (+40% →
+74%) comes mostly from dropping truncated windows and the fee-consistent
target, not from a better booster.

**Remaining weak spot:** day-level *outflow* beats the best baseline by only
+2.6% (model MAE 870 vs 894). Day-level net now wins too (+11.6%: 1,400 vs
1,583) — the old 7.7× loss was the unstable spread, now fixed — but outflow
at single-day resolution is the next thing to improve with real data.

**Serving guard (GAP-01):** the net residual booster is biased for earners
whose corner has no training mass (demo backtest: model −৳5.4k/14d vs the
user's own trailing mean −৳0.2k, confirmed across two retrains). When the
model window total disagrees with the user's own flows beyond 15% (floor
৳500), the served level falls back to the trailing-28-day anchor with the
model's weekday shape, and the provenance says so (`net_source: "anchor"`).
Anchors agree by construction, so the card never contradicts itself; the
demo plan verifies feasible end-to-end in `test_demo_acceptance.py`.

### 4.2 Anomaly detection — IsolationForest vs fixed-threshold rule

27,606 test transactions, 793 injected anomalies, contamination 0.02:

| Metric | IsolationForest | Fixed rule (global cutoff ৳2,487) |
|---|---|---|
| Precision | **34.76** | 7.85 |
| Recall | 20.43 | **16.90** |
| F1 | **25.73 (+140%)** | 10.72 |
| AUC | **0.8416 (+37%)** | 0.6122 |

Recall by injected type (the plan §4 claim, as arithmetic):

| Type (count) | Model recall | Rule recall |
|---|---|---|
| Rapid repeats (372) | **6.99** | 6.99 |
| Unusual time (167) | **69.46** | 4.79 |
| Unusually large (254) | 7.87 | **39.37** |

Honest reading: the rule wins on huge amounts — its home turf, a single
absolute cutoff is built for that. The model wins big on user-relative
timing (unusual hour: 69.5 vs 4.8) and ranks far better overall (AUC 0.84
vs 0.61). Overall recall leads by 3.5pp here, but the margin is thin and
the rapid-repeat type is tied — a per-user rule tuned on validation users
matches this precision with higher recall (GAP-07: documented limitation,
hybrid detector planned). For a companion that must not cry wolf, precision +
ranking is the right trade — stated here, not hidden.

### 4.3 Consistency signal — LogisticRegression, AUC on held-out users

| Metric | Model | Random baseline |
|---|---|---|
| AUC (75 test users, 44% positive rate) | **0.8088** | 0.5079 |

Educational band only (Building / Steady / Strong) with top-3 SHAP factors and
a "not a lending decision" banner on every view. Labels come from a latent
stability variable + noise + shocks, never from the feature formula
(anti-circularity, plan §5).

## 5. Impact simulation (synthetic data; adoption is an assumption)

Fee math follows the generator rate: 1.85% on cash-outs, 0% app-transfer
alternative. Measured on all 493 simulated users with cash-outs: mean fee
**৳222.25/month** on mean cash-out volume ৳12,013.63; Rahim pays **৳335.58**.
Potential saving at assumed adoption: **৳44–111/month** (20–50% of 222.25).
Adoption is an assumption, not a measurement — labeled as such everywhere it
appears, including the app's own fee card.

Goal backtest (75 test users, goal ৳10,000 over months 5–6 = ৳5,000/mo,
planned on months 1–4): the naive plan (goal ÷ months) is feasible-by-definition
yet the actual months-5–6 income meets it only 14.7% of the time — a
**85.3% false-feasible rate**. The solver (surplus minus a 1-std buffer in this
simulation; 3-days-outflow buffer in the shipped app) blessed 0 users and was
wrong 0% of the time: over-strict here, but it demonstrates the failure mode it
exists to prevent — the naive plan failing during tight months. Buffer tuning
against pressure-day dips is listed as pre-pilot work, not a solved problem.

## 6. Fairness (plan §10: no group worse than 15% relative gap)

Headline first: **the forecast model beats the best baseline in all 9
persona/income groups** (+51.9% to +86.0% improvement, complete windows).
Raw MAE differs widely across groups, but MAE scales with money moved —
salaried users' MAE (4,305) is ~2× daily-wage users' (2,171) because their
flows are larger, not because the model serves them worse.

| Persona (test users) | Net MAE | Improvement vs best baseline |
|---|---|---|
| daily_wage (16) | 2,170.80 | +63.2% |
| gig_rider (9) | 2,106.20 | +51.9% |
| remittance_receiver (4) | 7,371.70 | +77.0% |
| salaried (19) | 4,305.30 | +86.0% |
| shopkeeper (23) | 3,859.90 | +60.3% |
| student (4) | 1,346.30 | +82.8% |

| Income band (test users) | Net MAE | Improvement vs best baseline |
|---|---|---|
| high (14) | 4,279.60 | +70.1% |
| low (31) | 2,430.10 | +76.0% |
| mid (30) | 4,066.90 | +75.4% |

Anomaly flag rates are 0.77%–2.75% across personas (max absolute gap
1.98pp), 0.88%–2.33% across districts (1.44pp), 1.33%–1.89% across income
bands (0.56pp). Relative gaps look alarming only because the base rates
are tiny — a textbook rare-event artifact, reported here in absolute points.

Consistency-signal band shares vary widely, but with 75 test users spread
over 10 districts some cells hold 1–4 users — noise dominates. Stated
plainly: this demo cannot clear a 15% bar on band shares, and we do not
claim it. Required follow-up with real data: larger cohorts, then re-run
this exact table before any release (governance gate, §9).

## 7. Responsible AI & security (guideline §14)

- **Privacy:** synthetic data only; `/me` returns the token owner's demo
  profile; no NID/phone/password fields exist.
- **Access control:** `user_id` comes from the demo token, never the body
  (IDOR probed: `user_id` in body ignored); 401/403 enforced; SQLite opened
  read-only; `check_same_thread=False` so parallel frontend calls never 500
  (30/30 under burst, was 3/30).
- **Prompt injection:** user text is classified into a whitelist. Free text
  that reaches the model travels only as an inert `user_text_untrusted`
  JSON field (never an instruction); 10 EN+BN injection payloads sink to
  the safe `unknown` template.
- **Banned output:** loan/urgency/guarantee/promo/lending/score filters screen
  every answer in both languages; refusals and banners survive the filter.
- **Number grounding:** every figure in LLM output is checked against the
  structured context; failures fall back to templates (observed live).
- **Human oversight & transparency:** reduce/delay/switch only, do-nothing
  option with cost, user confirms everything; Prediction/Assumption/Explanation
  on every card. No lending, approve/deny, or auto-transfer anywhere.
- **Live black-box probe:** `backend/scripts/security_probe.py` —
  **34/34 passed** (auth ×5, injection ×10, banned-output ×6, grounding ×2,
  validation ×9, rate-limit, privacy).
- **Unit tests:** full suite green in CI (`pytest backend/tests`, backend-test job).

## 8. How to reproduce every number

```bash
backend/.venv/bin/python backend/scripts/generate_data.py   # dataset
backend/.venv/bin/python backend/scripts/train_all.py       # §4.1 + §4.3 -> ml/artifacts/metrics.json
backend/.venv/bin/python backend/scripts/compute_report_metrics.py  # §4.2 + §5 + §6
backend/.venv/bin/python -m pytest backend/tests -q         # full suite, green in CI
backend/.venv/bin/python backend/scripts/security_probe.py  # 34 checks (needs server up)
```

Model IDs and keys used for the LLM verbalizer are listed in `.env.example`
(failover pool: Groq → Gemini → OpenRouter-free → template). The LLM is not
given computation tasks: its output is rejected when it contains a number
absent from the computed context, so wording cannot introduce new figures.

## 9. Scale path (guideline §13)

Competition → technical/business review → controlled validation on governed,
anonymized upay data → POC → pilot. Real transaction fields map to our schema
through an adapter; endpoints stay the same. With real data: consent,
minimization, RBAC, audit logs, retrain, drift + fairness re-checks, and the
LLM layer moves to a bank-approved provider. No revenue is claimed from
upsell — value is engagement, trust, and lower support load.
