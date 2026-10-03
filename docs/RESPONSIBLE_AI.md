# Responsible AI — Shonchoy Copilot

Maps to `plan.txt` §10 (guideline §14). Every claim below is implemented in
code and covered by tests; measured numbers live in `REPORT.md` §§4–7.

## Privacy

- Synthetic data only (`backend/scripts/generate_data.py`, assumptions in
  `docs/DATA_ASSUMPTIONS.md`). No real PII exists anywhere: no NID, phone,
  or password fields in the schema.
- Request logs and feedback store carry provider labels / hashed ids only —
  never user ids or message text.

## Explainability

- Forecast: LightGBM gain + TreeSHAP top drivers per pressure day
  (`backend/ml/explain.py`, `POST /forecast`).
- Anomaly: the deviating behavior feature vs the user's own norm
  (`POST /anomalies`).
- Consistency signal: closed-form SHAP top-3 factors (`POST /credit-readiness`).
- Savings plan: rule trace — surplus, buffer, arithmetic step by step.
- Tips: the behavior flag that triggered each tip.
- Every card separates Prediction / Assumption / Explanation
  (`docs/LOGIC_CHAIN.md`).

## Fairness

- Gaps computed on held-out TEST users across persona, district, income band
  (`backend/ml/fairness.py`, `REPORT.md` §6).
- Forecast beats the best baseline in all 9 persona/income groups
  (+15.9% to +67.8%). Anomaly flag gaps reported in absolute points
  (rare-event artifact documented, not hidden). Band-share gaps honestly
  reported as unmeasurable at n=75 — re-run gated before any release.

## Security

- Prompt-injection defense: user text classified into whitelisted intents;
  free text reaching the model travels only as an inert
  `user_text_untrusted` field, never as an instruction; system/user roles
  separated (`backend/rules/guardrails.py`, `backend/genai/prompts.py`).
- Access control: `user_id` comes from the demo token, never the request
  body (`backend/app/deps.py`); 401/403 enforced; SQLite opened read-only.
- Validation (Pydantic), 20 req/min chat rate limit, banned-output filter
  (both languages), number grounding with template fallback.
- Live black-box probe: `backend/scripts/security_probe.py` — 34/34 passed;
  full `pytest backend/tests` suite green in CI.

## Human oversight & transparency

- Reduce / delay / switch suggestions only. No upsell, no loan push.
- Do-nothing option with cost on every plan; user confirms everything.
- Consistency signal is an educational band (Building / Steady / Strong)
  with a "not a lending decision" banner — never a score, never used for
  approve/deny, no auto-transfer anywhere.
