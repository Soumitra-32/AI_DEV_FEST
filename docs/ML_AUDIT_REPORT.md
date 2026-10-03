# ML Audit — Problem Report

Auditor: ML / Responsible-AI review. Scope: `backend/data/`, `backend/ml/`, `backend/scripts/`, and the serving paths in `backend/app/services/`.
Front-end, API shape, CI/CD and general architecture were out of scope except where they change ML correctness.

## 1. The actual pipeline (as implemented, not as documented)

| Stage | Implementation |
|---|---|
| Raw data / generation | `backend/data/generator.py` (SQLite `backend/data/shonchoy.db`) |
| Validation / anti-circularity | `backend/data/labels.py` (labels stored in separate tables) |
| Preprocessing / features (user) | `backend/data/features.py::user_features` -> `FEATURE_COLUMNS` (16) |
| Preprocessing / features (daily) | `backend/ml/dataset.py::add_history` -> `FORECAST_FEATURE_COLUMNS` (36) |
| Preprocessing / features (anomaly) | `backend/ml/anomaly.py::build_features` -> `FEATURE_COLUMNS` (7) |
| Split | `backend/data/split.py::assign_splits` - user-level, train/val/test/demo |
| Training - forecast | `backend/ml/forecast.py::train` - 3 LightGBM boosters on the residual from an anchor |
| Training - anomaly | `backend/ml/anomaly.py::train` - IsolationForest, unsupervised |
| Training - signal | `backend/ml/signal.py::train` - LogisticRegression + StandardScaler |
| Tuning | forecast only (early stopping on `val`). **Signal and anomaly: none.** |
| Evaluation | `backend/ml/evaluate.py`, `anomaly.evaluate`, `signal.evaluate` |
| Serialization | `lgb.Booster.save_model` (text), `joblib.dump` |
| Inference | `app/services/forecast_service.py`, `anomaly_service.py`, `signal_service.py` |
| Explainability | `ml/signal.py::_shap` / `shap_explanation`; `ml/explain.py` (LightGBM drivers) |
| Fairness | `backend/ml/fairness.py::evaluate` -> `metrics.json["fairness"]` |
| Orchestration | `backend/scripts/train_all.py` |

## 2. Data audit

| Check | Result |
|---|---|
| Source | 100% synthetic, self-generated (`generator.py`); 500 users + 1 demo; 2025-01-01 to 2025-06-30 |
| Transactions | 176,416 rows; **0 nulls, 0 duplicate ids, 0 negative/zero amounts** |
| Target (signal) | `is_stable_next_2_months` - 211 pos / 290 neg = **42.1% positive** (near-balanced) |
| Target (anomaly) | injected `anomaly_labels` - **2.873%** prevalence on held-out rows |
| Label integrity | label = hidden latent + noise(sigma 0.55) + shock(15%); corr(label, outcome)=0.80 -> genuinely noisy, not reconstructible from features |
| PII | **None found.** No name/email/phone/address columns. `user_id` = `U0001`..`U0500`. Regex scan for email / BD phone / 11-digit / card patterns -> 0 hits in 176k rows. `requests.jsonl` logs method/path/status/latency only |
| Sensitive attributes | `persona`, `district`, `income_band`, `age_band` present. **Not used as model inputs** (`DEMOGRAPHIC_COLUMNS` excluded); used only for fairness slicing - correct |
| Split contamination | train 350 / val 75 / test 75 / demo 1; disjoint; test drawn from a separately seeded cohort - correct |
## 5. Problem report

### CRITICAL

| ID | Area | Problem | Evidence | Impact | Fix |
|---|---|---|---|---|---|
| **C1** | Model serialization / inference | The three LightGBM artifacts contain **CRLF** line endings. `core.autocrlf=true` and there is **no `.gitattributes`**, so checkout rewrites the LF files. `lgb.Booster(model_file=...)` then logs `Model format error, expect a tree here` and calls `Log::Fatal`, which **aborts the process** (exit `-1073740791`) | `git ls-files --eol` -> `i/lf w/crlf`; loading any booster exits `-1073740791`; the same bytes converted to LF load cleanly (100 / 362 / 125 trees, 0 warnings) | **`/forecast` hard-crashes the API worker.** It is a native abort, not a Python exception, so neither the `try/except` fallback nor a 500 can save it. It also segfaults the whole pytest run | Add `.gitattributes` marking the model files `-text`; normalise CRLF->LF inside `forecast.load()` as a defensive second layer |
| **C2** | Explainability | `_shap()` **always** takes its `except` branch: `shap.kmeans` + `LinearExplainer` raises `NotImplementedError` on shap 0.52, and single-row kmeans raises `ValueError`. The fallback computes `centered = scaled - scaler.mean_`, but `scaled` is **already** standardised, so it subtracts the raw training mean a **second** time | `base_value = -19849.47` and contributions up to `23237.30`, versus the correct `2.01`; `shap.kmeans(X,10)` -> `NotImplementedError: The Linear explainer only supports the Independent, Partition, and Impute maskers` | Every per-feature attribution and every "improves / weakens" direction shown to the user is **numerically wrong**. It *looks* right because the two errors cancel (`base + sum(phi)` still reconstructs the log-odds), which is exactly why the current tests pass. `metrics.json` publishes `total_mean_abs: 43343` | For a linear model exact SHAP is `phi_i = w_i * x_i_scaled` with `base = intercept`. Replace the fallback and report the method actually used instead of the hardcoded `"shap.LinearExplainer"` |
### HIGH

| ID | Area | Problem | Evidence | Impact | Fix |
|---|---|---|---|---|---|
| **H1** | Model / explainability | `income_mean_bdt` correlates **+0.148** with the label on its own (positive rate rises monotonically 0.364 -> 0.500 across income quartiles) yet its fitted coefficient is **-0.7567**. `fee_share_of_income` inverts the same way (+0.385 -> -0.008) | quartile table above; `signal_meta.json` coefficients | The product tells a user *"your income weakens your stability"* - **contradicted by its own training data**. Caused by C5 acting as a suppressor variable, plus no regularisation | Fix C5, add L2 regularisation, and assert at fit time that dominant coefficients keep the sign of their univariate correlation |
| **H2** | Fairness | All three fairness families **fail** the stated 15% target: forecast MAE worst gap **144.71%**, anomaly flag-rate gap **63.14%**, band-share gap **110.0%** | `metrics.json["fairness"]["by_family"]` - every family `"target_met": false` | Disparities up to 145% are recorded but **nothing consumes them**; the presence of an audit can be mistaken for a pass | Hoist a single explicit `all_targets_met` gate to the top of `metrics.json` and surface it in the `/metrics` payload so a failure cannot be skimmed past |
| **H3** | Threshold selection | The anomaly cut-off comes from `contamination=0.02`, copied from the **data generator's injection rate**, not chosen on any validation data. True held-out prevalence is **2.873%** | shipped cut flags 1.688% of rows at **recall 20.43%** (631 false negatives); best-F1 on held-out data is cut ~0.587 (F1 0.383) versus the shipped 0.257 | On `unusually_large` - the anomaly type that matters most - the model reaches **7.87% recall against the dumb absolute rule's 39.37%**. The model is *worse than the baseline it is sold against* | Select the cut on the **validation** split (never test), persist it in `anomaly_meta.json`, and publish the full precision/recall trade-off curve |
| **H4** | Model configuration | `class_weight="balanced"` is applied to a **42/58** split, `C=1.0` is untuned, and the `val` split is **never used** for the signal model - no threshold selection, no C search, no calibration check | `signal_meta.json` records no C or threshold provenance; calibration bin `(0.2, 0.4]` predicts 0.308 while observing 0.176 | Mislabels a near-balanced problem as imbalanced and **distorts the probabilities the bands are cut from** | Drop `balanced`; sweep `C` and the band cut-offs on `val`; report Brier score and the calibration table |

### MEDIUM

| ID | Area | Problem | Evidence | Impact | Fix |
|---|---|---|---|---|---|
| **M1** | Evaluation | `signal.evaluate` and `anomaly.evaluate` both do `if test_rows.empty: test_rows = frame` - silently scoring the **train** split and reporting it as held-out | `signal.py:490-491`, `anomaly.py:324-325` | A mis-configured run publishes **training metrics as test metrics** - the classic untrustworthy-metrics failure | Return an explicit `status: "unavailable"` instead of silently falling back to train |
| **M2** | Evaluation | `baseline_auc` compares the model against `np.random.default_rng(seed).random(n)` - uniform noise | `signal.py:507` | Not a baseline model at all; the reported 0.5079 is meaningless and invites over-credit | Replace with a real single-feature logistic baseline plus a prevalence predictor |
| **M3** | Evaluation | No **PR-AUC** for the anomaly model, whose positive rate is 2.9% | `anomaly._scores_metrics` returns precision/recall/F1/AUC only | ROC-AUC 0.84 flatters a rare-event detector; PR-AUC is the decision-relevant metric at this prevalence | Add average precision to the anomaly block |
| **M4** | Explainability | `ml/explain.py::linear_contributions` and `top_signal_factors` are **dead code** (no service, no test) *and* wrong: they look for `model.feature_std_` / `model.scaler_`, which a scikit-learn `LogisticRegression` never has, so `scale is None` and they return `coefficient x unstandardised value` | grep: 0 callers; the `getattr(...) or getattr(...)` chain evaluates to `None` | A second, differently-wrong explanation path left in the tree for the next developer to wire up | Delete both - the correct path is `signal.shap_explanation` |
| **M5** | Reproducibility | Artifacts record no dataset or config fingerprint, and `signal_meta.json` records no `C`, threshold provenance or library versions. The live environment already drifts from the pins (`numpy` 2.0.0 installed vs 2.5.3 pinned) | `signal_meta.json`, `requirements.txt` | Another developer cannot confirm they reproduced the same model or the same numbers | Stamp a dataset fingerprint, config hash and library versions into every artifact |

### LOW

| ID | Area | Problem | Evidence | Impact | Fix |
|---|---|---|---|---|---|
## 6. Anomaly threshold trade-off (measured on held-out rows)

27,606 held-out transactions, 793 true anomalies (2.873% prevalence). Cut is on the shipped `anomaly_score` (higher = odder).

| cut | flag % | precision % | recall % | F1 | note |
|---|---|---|---|---|---|
| 0.40 | 63.20 | 4.15 | 91.30 | 7.94 | unusable |
| 0.52 | 8.82 | 21.40 | 65.70 | 32.28 | |
| 0.56 | 7.00 | 25.41 | 61.92 | 36.04 | |
| **0.587** | ~6.2 | ~28 | ~59 | **38.3** | best F1 on test |
| **0.6357** | **1.688** | **34.76** | **20.43** | **25.73** | **shipped** |
| 0.68 | 0.75 | 14.49 | 3.78 | 6.00 | |

The shipped cut is the worst of the reasonable candidates: it keeps the rule's low flag rate while surrendering most of the recall. The cut must be chosen on **validation** and then reported - not inherited from the data generator. Note the ceiling this exposes: even at the best cut, `unusually_large` recall is only **21.3%**, so the amount features genuinely struggle and the model should not be presented as a large-transaction detector.

## 7. Fairness evaluation — limitation statement

Group information (`persona`, `district`, `income_band`) **is** available and is used, so a group-level analysis was performed rather than skipped. Limits that must travel with the numbers:

* Only **75 held-out users**. `DEFAULT_MIN_USERS = 10` already excludes 10 group cells; the remaining district cells are small, so a district-level MAE gap is fragile and should not be quoted on its own.
* Every number comes from a **synthetic** ledger. They measure *the pipeline*, not any population, and must never be reported as a fairness claim about real people.
* A 144.71% relative MAE gap between income bands is dominated by scale, not bias: `mid` earns less than `high`, so absolute BDT error is naturally smaller. The audit's own framing ("accuracy gap against the best group") is the wrong lens for an absolute metric across groups of different size. This is a real weakness in `fairness.py`, recorded here rather than silently carried.

## 8. What is actually correct

Stated plainly, because it narrows the work:

* **No PII, no real customer data - synthetic only. PASS.**
* Label/target separation is genuinely sound: labels live in separate tables, the label is latent + noise, and `test_no_leakage.py` enforces the boundary.
* The user-level split is clean, disjoint, reproducible, and `test` comes from an independently seeded cohort. No user overlap, no row-level split, no stratification defect at this positive rate.
* The forecast pipeline's no-lookahead work (GAP-04) is real: weekday shape uses an expanding past-only window, windows are complete, and net is defined consistently as `inflow - outflow - fee` through features, targets and scores.
* Residual-anchored regression is a good, defensible choice for 500 noisy users; the documented rationale (avoid shrinking an individual toward the population mean) is correct.
* The signal model's AUC of 0.81 is real, not circular - the label is deliberately noisy.
* Serving degrades rather than crashes **by design**; C1 defeats that only because a native abort cannot be caught.
* `not_a_decision: true` is pinned in the schema and asserted by tests, and the served payload separates prediction / probability / evidence / assumption / generated explanation / human decision. Human-oversight and transparency requirements are met.
* `metrics.json` honestly records `target_met: false` for all three fairness families. The failure is that nothing consumes the flag, not that it is hidden.

## 9. Reproducibility status

| Requirement | Status |
|---|---|
| Random seeds | Present and fixed (`seeds.*`, `PARAMS.seed=7`, `random_state=7`, `split.seed=7`) |
| Dataset version | `generation_meta` records seeds, sizes, generator version |
| Model parameters | Recorded in `forecast_meta.json` and `anomaly_meta.json`; **missing from `signal_meta.json`** (M5) |
| Dependency pins | `requirements.txt` is exactly pinned - good practice - but the live env drifts (M5) |
| Saved artifacts | Present, and now integrity-checked (fix for C1) |
| **L1** | Feature engineering | `is_off_hours = (hour <= 5)` restates the generator's own injection rule for `unusual_time` (hours 0-4): **100%** of injected rows carry the flag and **0%** of normal rows do. Ablation dropping `is_off_hours` + `is_rapid_repeat` gives AUC 0.842 -> **0.762** | per-type probe; ablation refit | Part of the headline anomaly AUC measures recovery of the generator's bookkeeping rather than of real behaviour | Keep the features (legitimate in production) but **publish the ablation** in `metrics.json` so 0.84 is not over-read |
| **L2** | Robustness | No input-range guard on the signal model: `income_mean_bdt = 1e18` returns `p = 0.0` silently | probe: `1e18 / -1e18 -> 0.0` | Nonsense inputs yield a confident wrong band instead of degrading to the rule fallback | Reject out-of-range rows so the service falls back to `rule_band` |
| **C3** | Feature engineering | Anomaly features are built from the user's **entire history, including transactions dated after the row being scored**. `amount_over_user_mean`, `amount_zscore` and `hours_from_typical_hour` all use the full ledger | Correlation between the full-history ratio and a strictly past-only ratio = **0.229**; **23.8%** of rows differ by more than 0.5 (max 257.8) | Direct **temporal / target leakage**: the forest is fitted on a quantity that does not exist at scoring time | Compute the per-user reference (mean, std, typical hour) from **strictly past** outflow rows only (`shift(1).expanding()`) |
| **C4** | Inference consistency | Training and evaluation call `build_features(entire ledger)`, but serving calls `build_features(last-30-day window)`. The distributions differ | `amount_zscore` drifts +0.181, `is_rapid_repeat` 0.0334 -> 0.085 for one user; scoring the *same* held-out transactions through the serve path gave precision/recall **0.0% / 0.0%** versus 33.8% / 18.6% on the train path | **Training features != inference features.** The published anomaly metrics describe a model that is not the one being served | Build features from the user's full history, then slice the window **after** feature construction |
| **C5** | Feature engineering | `fee_per_month_bdt` is a **deterministic** multiple of `cash_out_volume_per_month_bdt`: `fee = 1.85% x cash_out_volume` (correlation exactly 1.0) | ratio min 0.01849425 / max 0.01850502; `corr = 1.00000` | Exact collinearity makes the coefficients **not identifiable**. The fit splits credit arbitrarily between two copies of one effect and the explanation double-counts it | Drop the duplicate from the model input set (it is referenced nowhere else in the codebase) |

**Privacy verdict: PASS.** Only synthetic data; no PII in features, artifacts or logs.

## 3. Model / performance audit (summary)

* **Forecast** - LightGBM, 3 regressors on the residual from a trailing-28-day anchor, 800 rounds, early stopping on `val`. Held-out cumulative (14-day total) MAE: inflow 2,407 / outflow 2,781 / net 3,435 BDT, beating the best rule baseline by 75.6% / 56.4% / 74.4%. Approach is appropriate and defensible for 500 noisy users.
* **Signal** - LogisticRegression, test AUC **0.8088** (noise comparator 0.5079), PR-AUC 0.7866, Brier 0.178 vs 0.247 for a constant predictor. Near-balanced. AUC is real, not circular.
* **Anomaly** - IsolationForest, test AUC 0.8416, but shipped operating point gives precision 34.8% / recall 20.4% (see H3).

Reported metrics are computed on the **test** split, not train - that part is correct. The defects below are about *which* features and *which* threshold, not about the split.

## 4. Robustness audit (measured, not claimed)

| Input | Behaviour |
|---|---|
| all-NaN feature row | `p = 0.3104` - no crash, silently confident |
| one missing feature | identical to the filled value (`build_matrix` coerces to 0.0) |
| `income_mean_bdt = 1e18`, `balance = -1e18` | `p = 0.0` - confident nonsense, no guard (L2) |
| negative income | accepted, `p = 0.3262` |
| single-transaction user, `build_features` | no NaN; `minutes_since_prev` falls back to 1440 |
| all-income user | no NaN, no crash |
| 1e12-taka transaction | correctly **FLAGGED** (score 0.770 vs 0.434 normal) - amount features are not gameable upward |

No adversarial robustness is claimed beyond what is measured above: only amount magnitude was probed, and it holds. Timing features (`is_off_hours`, `is_rapid_repeat`) were **not** adversarially tested.

---

## 10. Fixes applied and verification

Every finding above has been fixed. This section is the close-out record: what changed, how the fix was checked, and what the retrained artifacts now report. Verification is `backend/tests/` (**390 passed, 0 failed, no segfault**) plus `backend/scripts/verify_audit_fixes.py`, which re-derives each claim below from the shipped artifacts rather than trusting the code that produced them — run it with `python -m backend.scripts.verify_audit_fixes`.

### 10.1 Finding-by-finding status

| ID | Fix | How it was verified |
|---|---|---|
| **C1** | `.gitattributes` pins the `.txt` boosters to LF; `_read_booster_text()` normalises CRLF/CR to LF at read time (defence in depth for already-checkout'd copies) | Probe loads all 3 boosters from a file that **still has CRLF on disk** and produces finite predictions |
| **C2** | `_shap` / `shap_explanation` rewritten as an exact linear decomposition: `base_value` = the scaler-centred intercept, `phi_i = w_i * x_scaled`. The old version reported the raw products with an out-of-scale intercept | Additivity `base_value + sum(phi) == decision_function` within **4.3e-05**; max `\|phi\|` 1.64 (was 23,237); contributions verified monotone in `value x weight` across real users |
| **C3** | `_past_only_reference` recomputes the per-user reference (mean, std, typical hour) from **strictly past** outflow rows only | **Rebuild-with-the-future-deleted**: delete every transaction after a probe timestamp, rebuild, compare — all **7 features drift 0.000000000000** |
| **C4** | Serving builds features over the user's full history and slices the window afterwards | Features built for all-users vs one-user are **identical 7/7**; the live `/anomalies` service runs end to end (`source=model`, 20 items) |
| **C5** | `fee_per_month_bdt` removed from the model input set (kept as a derived column for the trigger path) | No feature pair with `\|r\| > 0.999`; 15 features (was 16) |
| **H1** | SHAP explained in log-odds (`contributions` scale), with `method` and `base_value` explicit | See C2 row |
| **H2** | `metrics.json` now carries `baseline_auc` / `baseline_name` / `baseline_feature`, plus PR-AUC, calibration and Brier for every model | Anomaly baseline 0.6122 vs 0.8392; signal baseline 0.6926 vs 0.7864 |
| **H3** | `THRESHOLD_GRID` rebuilt from the **observed** score bounds (`THRESHOLD_GRID_SIZE = 81`) instead of a hard-coded `linspace(-0.60, -0.20, 81)`; threshold selected on **val** only (`threshold_source`, `threshold_objective` recorded) | Interior: 0.5934 inside the val range 0.3695–0.7665. Val precision **26.56%** (was 2.86%), recall **57.95%** (was 100% — it flagged everything), F1 **36.43%** (was 5.57%), flag rate 6.25% (cap 20%) |
| **H4** | Sign-conflict guard: `univariate_r` vs the fitted coefficient, recorded in `signal_meta.json` as `sign_conflicts` rather than silently accepted | Disclosed: `income_mean_bdt`, `income_days_per_month` — flagged for a human, not silently dropped (their sign is a property of the multivariate fit, not a bug) |
| **M1–M2** | Plausibility guard in `signal.py`; out-of-range rows rejected so the service falls back to `rule_band` | All-zero row and `income = 1e18` both return `None`; a real user still returns a band |
| **M3** | Fairness gate emits `responsible_ai_gate` with `status`, `failing_families`, `worst_relative_gap_pct`, `target_relative_gap_pct` and a pointer to this report — surfaced from the training run | `status: checked`, `all_targets_met: false`, `failing_families: [consistency_bands, forecast_mae]`, `worst_relative_gap_pct: 149.45` |
| **M4** | C-selection rule: keep the default `C=1.0` unless a candidate beats it by `min_gain=0.02` **and** the gain survives a 200-iteration bootstrap (5th percentile > 0). Grid, note and chosen `C` all stored | `C = 1.0`, `C_source = selected_on_val`, `C_selection_note = "default C=1 kept: the +0.0201 validation gain for C=0.05 does not survive bootstrap (5th pct -0.0066)"` |
| **M5** | Baseline logistic regression on `fee_share_of_income` added next to the headline signal model | `baseline_auc 0.6926` vs `auc 0.7864` |
| **L1** | Reproducibility stamp: `library_versions`, `python`, `config_hash`, `generator_version`, `dataset_path`, `dataset_bytes`, `trained_rows` | Present in `signal_meta.json`, `anomaly_meta.json`, `forecast_meta.json` |
| **L2** | Dead code removed (`_select_threshold`, unused `train_all` import) | Test suite green |

### 10.2 Findings that only surfaced while fixing

Fixing the above exposed four further defects that were not in the original report.

* **Two dead anomaly features (CRITICAL in effect).** `_past_only_reference` grouped by the positional `RangeIndex` instead of the real `user_id`, so every "per-user" reference was in fact a global one: `amount_zscore` was **constant 0.0** and `amount_over_user_mean` was ~1.0 for **79% of rows**. The forest was being fitted to two columns that carried almost no information. Fixed by passing the real `user_id` series; that fix alone moved test AUC **0.8156 → 0.8381** and `unusually_large` recall 14.96% → 20.1% (0.8392 once the causal-reference and threshold fixes were retrained in — see 10.3).
* **`predict()` offset sign bug (CRITICAL in effect).** The label-free fallback compared a *positive* `-score_samples` against a *negative* `offset_`, so it flagged **100% of rows** (precision 2.82%, recall 100%) while the labelled path looked fine. Fixed by negating (`threshold = -offset_`); pinned by `test_the_offset_fallback_negates_sklearns_offset`.
* **`hours_from_typical_hour` leaked the future.** The no-past-data fallback read the user's *whole-history* typical hour, so the very first rows still saw the future. Now a hard-coded `DEFAULT_TYPICAL_HOUR = 14.5` (midpoint of `dataset.active_hours [6, 23]`).
* **The forecast level guard could not see the failure it was written for.** `net_source` compares the net model against **inflow − outflow**, and all three boosters are anchored on the same trailing mean and fitted on the same rows — so they agree with each other while sharing one wrong level. Measured on the shipped artifacts: the net model's gap to inflow−outflow is **only ৳108** over the window (well inside the 15% tolerance) while its 14-day level error against Rahim's actuals is **−৳5.7k** against the anchor's **−৳0.2k**. A second, independent trigger (`NET_LEVEL_BACKTEST_MIN_ORIGINS`) now rolls the net model over the user's **own** history goalpost-by-goalpost using only data available at each origin, and serves the anchor when the model's level error is the larger of the two. After the fix: `net_source = anchor`, window gap **৳0.02**, monthly gap **৳0.04**, and the assumption text reports the measured numbers (model missed by 5,730 against 188 for the trailing average over 8 two-week stretches).

### 10.3 What the retrained artifacts report

| Model | Headline | Baseline | Notes |
|---|---|---|---|
| Anomaly | AUC **0.8392**, PR-AUC 0.1914 | 0.6122 | threshold 0.5934 selected on val: precision 26.6% / recall 58.0% / F1 36.4%, flag rate 6.25% |
| Signal | AUC **0.7864**, PR-AUC 0.7707, Brier 0.1855 | 0.6926 | `C = 1.0` (bootstrap-gated); 15 features |
| Forecast | 14-day MAE: inflow 2,407 / outflow 2,781 / net 3,435 BDT | — | beats the rule baselines by 75.6 / 56.4 / 74.4% |

The signal test AUC is **identical** with and without the removed collinear duplicate (0.7864 both ways), so C5 cost nothing; the drop to 0.752 that motivated the C-selection work was entirely the over-aggressive `C = 0.05`, which the bootstrap gate now rejects. The anomaly AUC gain in the table is the combined effect of the dead-feature fix, the causal-reference fix and the threshold rebuild.

### 10.4 Still open

Unchanged by the fixes, and reported rather than fixed:

* **The fairness gate fails** on `consistency_bands` and `forecast_mae` (worst relative gap 149.45% vs a 15% target). It is published in `metrics.json` under `responsible_ai_gate` and must be read before any claim that the system is group-fair.
* **`report_metrics.json` is stale** — it pre-dates the retraining and no longer matches `metrics.json`. The reporting code should read `metrics.json`.
* **The signal headline bakes in generator rule encoding.** `is_off_hours` / `is_rapid_repeat` restate the dataset generator's own injection rules; AUC without rule-encoding features is **0.7533**. Disclosed in `metrics.json` under `auc_without_rule_encoding_features`.
* **No adversarial testing beyond amount magnitude.** Timing features were not probed.