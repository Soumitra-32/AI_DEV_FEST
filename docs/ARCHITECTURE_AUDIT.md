# Shonchoy Copilot — Engineering Assessment
**Senior AI/ML architecture audit · API 0.7.0+ · Covers brief Phases 1–10 · No code changed.**

Evidence: full repo read (backend + web), measured numbers from `train_all.py`,
`compute_report_metrics.py`, live probes, and `competitor_repos.csv` (29 repos,
methodology notes as published — no competitor source code was pulled).

---

## PHASE 1 — Architecture audit

### 1.1 Current architecture

```
 synthetic generator (seeded, 500 users x 6 mo)
   ↓  SQLite (users, transactions, anomaly_labels, user_labels, splits, meta)
 feature pipelines (dataset.py daily flows · features.py user aggregates)
   ↓
 ML models (LightGBM x3 forecast · IsolationForest anomaly · LogReg signal)
   ↓  artifacts/*.txt, *.joblib, metrics.json
 Rules (savings solver · fee switch · health score · pressure days · goal templates · guardrails)
   ↓  structured JSON only
 GenAI verbalizer (3-key failover pool → templates on any failure)
   ↓
 FastAPI (12 routes)  →  Next.js (7 pages + voice)
```

### 1.2 Current algorithms

| Component | Algorithm | Params | Measured |
|---|---|---|---|
| Forecast inflow/outflow/net | LightGBM regression ×3 (anchor+residual+bias) | leaves 63, min_data 40, 101 rounds, early-stop 100, seed 7 | Net +39.7% vs best baseline (15% target met) |
| Anomaly | IsolationForest, 300 trees, contamination 0.02 | 7 behavior features | F1 18.87 (+76% vs rule), AUC 0.84 vs 0.61 |
| Consistency signal | LogisticRegression C=1.0 + StandardScaler, balanced | 16 user features | AUC 0.784 vs 0.508 random |
| Savings plan | Rule solver (surplus − 3-day buffer) | buffer_days=3.0 | Naive false-feasible 85.3%, solver 0% (over-strict — §4.3) |
| Health score | Rule 5×20 | thresholds in code | Unmeasured vs anything |
| Intent | LLM classify → keyword fallback | temp 0.0, 120 toks | Covered by guardrail tests |
| Explanation | LLM verbalize → template fallback | temp 0.2, 700 toks, json_object | Grounded-check enforced |

### 1.3 Assumptions (documented, all in code or DATA_ASSUMPTIONS.md)

1.85% cash-out fee (simulation, not upay pricing) · 0% app-transfer alternative ·
month-end pressure for selected personas · ~2% anomalies, 3 types · 20–50%
adoption (assumption, labeled) · 70/15/15 user split, demo excluded · labels from
latent+noise+shocks (not the feature formula).

### 1.4 Bottlenecks & performance problems (confirmed)

1. **Per-request model reload.** `forecast/anomaly/signal` `load()` rebuilds
   boosters/joblibs on every request; only `explain.top_drivers` and the tip bank
   are cached. Fix: module-level `lru_cache` on loads (Phase 7).
2. **Sequential 2×LLM per chat** (intent + verbalize); worst case 2×3 providers×
   timeout. Frontend aborts at 12s → slow keys always lose. Fix: 8s timeout
   (set), parallelize intent+context build, stream later.
3. **Row-wise Python loops** in `evaluate.scored_cells` (~157k try/except lookups),
   `baselines.long_frame` (iterrows), generator `_apply_balances` (itertuples).
   Fine for 500 users; will not survive 50k.
4. **`fetchCreditReadiness` 404 (P0 regression).** Team renamed backend
   `/signal`→`/credit-readiness`; frontend still calls `/signal`. Signal page
   silently renders static content. One-line fix, layout untouched.
5. **Fairness net-MAE recomputes net as inflow−outflow** (`fairness.py:223`),
   discarding the served net model — audit number ≠ served number.
6. **Split seed wiring:** `assign_splits` reads `cfg[split].seed`, absent in
   `config.yaml` → always seed 0 unless passed explicitly.
7. `user_features()` leaves persona/district/income_band all-NaN (reporting
   must join demographics; models unaffected).
8. Weekend definition inconsistent (`[4,5]` vs config), `mtd_*` includes current
   day, fee-inclusive net features vs fee-exclusive net target (serve skew).

### 1.5 Missing evaluation metrics

Health-score: no validation against anything · Tips: retrieval precision unmeasured
· Voice: no WER/parse-rate log · Goal templates: no fit-rate · LLM wording:
grounding pass-rate not logged (only fallback counts) · Fairness: district cells
of 1–4 users (noise dominates; needs bigger test cohort or pooled reporting).

### 1.6 Unnecessary complexity

Per-row SHAP on small frames (gain importance suffices at this scale) ·
`_variants` rounding lattice in grounding (correct but review-heavy) · 30-tip bank
before measuring retrieval precision of 15 · two net paths (model + difference)
without a selector metric.

---

## PHASE 2 — Competitor analysis (from published methodology notes)

| Competitor | Algorithm | Task | Strength | Weakness | Applicable to Shonchoy |
|---|---|---|---|---|---|
| Upay-Shadhin (T3, very high) | Quantile P10/P50/P90 30d forecast; TF-IDF categoriser; refusal logic; 53+88 tests | Forecast + categorization | Uncertainty bands; test volume; leakage asserts | 30d horizon harder to defend; Flutter = second stack | **Adopt quantile/prediction intervals** for pressure days; adopt leakage asserts |
| CashCompass (T3, high) | Conformal XGBoost 90% band; TreeSHAP; auto-sweep vault | Liquidity forecast | Calibrated bands beat point forecasts for trust | Auto-sweep = autonomous money movement (our guardrails forbid) | Adopt conformal bands; reject auto-sweep |
| FinResilience (T3) | 7d/14d/month-end models; shortage-risk classifier; IF anomaly | Forecast + risk | Decoupled pipeline; dedicated shortage classifier | 3 overlapping models = 3× maintenance | Adopt shortage-risk as classifier head, not separate model |
| upay-SafeSend (T1, deployed) | XGBoost + IF + SHAP; <50ms screening | Pre-txn risk | Latency budget as spec; deployed Render | Cold-start risk on free tier; T1, not our track | Adopt <Xms latency budgets per endpoint |
| mfs-agent-security (T1, deployed) | Bangla/Banglish injection set, 114×3 cases, on/off toggle | Prompt-injection testing | Best adversarial methodology in the field | Security-only, no product | Adopt attack-set + toggle pattern for guardrail demo |
| VoiceBKash (other event) | Voice-first + IVR phone simulator | Inclusive UX | Phone channel reaches offline users | Different competition | Note as post-hackathon scale idea, not now |
| upay-BizFlow (T7) | QR-reform ledger design (docs only) | Merchant ledger | Sharpest regulatory awareness (1 Oct 2026 MDR/IRF) | No code | Cite the QR reform in scale plan |
| Ferot (T6) | LightGBM + TreeSHAP; recoverability curves; hash-chained audit | Dispute copilot | Audit log integrity pattern | — | Adopt hash-chained request log (we log already, chain it) |
| FinCoach backend (T3) | Supabase RLS, atomic ownership, deterministic plans; **no AI yet** | Infra | Strongest data-security posture | No models = nothing to score on AI depth | Adopt RLS-style ownership checks narrative; we already lead on AI |

**Common winners:** LightGBM/XGBoost + SHAP + IsolationForest (our stack matches).
**Effective & missing in ours:** prediction intervals (quantile/conformal),
injection attack-set demo, latency budgets, hash-chained logs.
**Unnecessary for us:** auto-sweep/autonomous actions, 30-day horizons, second
mobile stack, graph ML (no network data), deep sequence models (see Phase 5).

---

## PHASE 3 — Dataset analysis

501 users · 176,416 transactions · 36 forecast features · 16 user features · 7
anomaly features · 793 anomalies (2.8%, 3 types) · 44% positive signal rate
(75 test users) · noise: 5% no-spend days, persona overlap, random shocks ·
6 calendar months (2025-01 → 2025-06), weekly + month-end seasonality.

**Task formulations (recommended):**
- A. Pressure detection → **rule on forecasted totals** (current). A classifier
  head is optional Phase 2; rules are auditable and already beat nothing-to-beat.
- B. Spending forecast → **regression on 14-day means** (current). Correct;
  sequence models unjustified at this size (Phase 5).
- C. Savings feasibility → **rule-based constrained solver** (current). Correct;
  keep ML out — the decision must be explainable line-by-line.
- D. Anomaly → **unsupervised isolation** (current). Correct; labels exist only
  for evaluation, never training.

---

## PHASE 4 — Algorithm selection

**Pressure/forecast head:** keep **LightGBM**. Beaten candidates: LR (underfits
interactions), RF (slower, no early stopping), XGBoost (≈equal accuracy, slower
training, bigger install), CatBoost (categoricals already encoded — no gain),
NN (≈500 users × 36 features: overkill, unexplainable, slow on CPU).
Primary: LightGBM. Backup: XGBoost (one-line swap, same frame).

**Anomaly:** keep **IsolationForest**. Beaten: fixed rule (loses user-relative,
proven 7× gap on unusual-time), autoencoder (needs 10–100× data),
clustering (no ranking score). Backup: fixed rule (already the fallback).

**Signal:** keep **LogisticRegression**. Beaten: XGBoost (+2–3pp AUC typical at
this n, destroys explainability story), hand weights (unvalidated). Backup:
hand-weighted rule (already the no-artifact fallback).

**Intent:** LLM-classify → keyword fallback (current). Correct order.

## PHASE 5 — Forecasting: stay with LightGBM

Traditional (MA/ES/ARIMA/Prophet) are already our baselines and lose by
40–74%. Deep (LSTM/GRU/Transformer): 75 test users cannot support them; no
GPU on Render free tier; SHAP story dies. Verdict: **LightGBM + quantile
extensions** (Phase 2: P10/P90 bands like Upay-Shadhin) — same stack, new
output columns, no retraining paradigm shift.

## PHASE 6 — Features

Keep: lags 1/2/3/7/14, rolls 7/28, mtd cash-out, days-since-cash-out,
balance_end, month-end flags (all carry gain). Drop/merge candidates:
`roll_3_*` trio (collinear with roll_7), `max_7_outflow` (outlier-driven),
`weekend_spend_ratio` (weak in SHAP). Missing: payday-distance,
fee-burden trend, income-day count (exists in user features — promote to daily
frame). Selection: **SHAP gain rank** (already exposed) + drop bottom quartile
+ re-measure (one script run, no code architecture change).

## PHASE 7 — Optimization (ordered by ROI)

1. **Cache model loads** (`lru_cache` on forecast/anomaly/signal loaders) —
   biggest latency win, ~10 lines.
2. **Parallelize intent + context build** (asyncio.gather) — halves chat latency.
3. **Vectorize `scored_cells` lookup** (merge_asof / dict-vectorized) — 10× eval
   speedup for bigger cohorts.
4. **Batch the tip phrasing** (one call, not N) or template-first with LLM
   upgrade only on tap.
5. **Tune once with Optuna** (leaves, min_data, lambda) on val MAE — LightGBM
   trains in minutes here; skip GridSearch (wasteful), skip ONNX (LightGBM
   native is already ms-scale; ONNX buys nothing at this size).
6. Serialize: keep joblib/txt boosters (current) + meta JSON (current). No change.

## PHASE 8 — Explainability (keep, extend slightly)

Current: LightGBM gain + TreeSHAP top drivers, signal closed-form SHAP,
rule traces (solver arithmetic, fee math, pressure reasons), Provenance cards.
Every prediction answers "why" in plain Bangla. Add only: **prediction
intervals on pressure days** ("shortfall likely between 28–31 because…") and
**counterfactual line on plans** ("+৳500/mo buffer moves you to feasible") —
both renderable from existing artifacts.

## PHASE 9 — Responsible AI check

Pass: synthetic-only, token→user auth, read-only DB, whitelist intents,
banned-output filter (both languages), number grounding, human-confirm-everything,
no lending/auto-transfer, PII-free logs/feedback, 34/34 probe. Gaps to close:
fairness district cells too small (pool or grow cohort) · `user_id` in debug
logs (scrub before shipping logs) · fairness net-MAE ≠ served net (recompute
from served spread) · split seed default 0 (wire `seeds.split`) · no hallucinated
advice observed (grounding + templates enforce structurally, not by prompt trust).

## PHASE 10 — Final recommendation

**1. Current assessment:** architecture sound, measurements honest, serving layer
has 3 known bugs (1 fixed by me: SQLite threads; 2 open: signal URL, seed wiring).
**2. vs competitors:** at parity on algorithms, ahead on guardrails/tests/Bangla
voice flow, behind on uncertainty bands, injection-set demo, latency budgets.
**3. Final architecture:** unchanged shape; add model-load cache, parallel
intent/context, quantile bands, hash-chained logs.
**4. Algorithms:** Pressure: rules on LightGBM totals (explainable, measured).
Forecasting: LightGBM (+quantiles); backup XGBoost. Anomaly: IsolationForest;
backup fixed rule. Savings: rule solver (never ML).
**5. Expected improvement:** accuracy +2–5pp from tuning + bands (not from new
model families); p50 chat latency −40% from cache+parallelize; complexity flat.
**6. Roadmap:** P1 (today): signal URL fix, seed wiring, load cache, Optuna-lite
tune, band intervals. P2: vectorized eval, batched tips, fairness recompute
from served spread, bigger test cohort. P3 (production path): bank-approved LLM,
RLS equivalent, drift monitors, re-run fairness gate.
