# Scale plan — Shonchoy Copilot

Maps to `plan.txt` §14 (guideline §13). Competition → review → validation →
POC → pilot → decision. Nothing here changes API contracts.

## Path

Competition → technical review → business review → controlled validation on
governed, anonymized upay data → POC → pilot → decision.

## Data mapping

Real upay transaction fields map onto our schema through an adapter
(`user_id, persona, district, income_band, timestamp, type, channel,
category, amount_bdt, fee_bdt, balance_after`); endpoints stay the same.
The consistency-signal label pipeline (`backend/data/labels.py`: latent
stability + noise + shocks) is re-fit on real outcomes, never on the
feature formula.

## Governance with real data

Consent, anonymization/aggregation, data minimization, role-based access,
audit logs. The current token→user auth, read-only DB, and PII-free logging
(`docs/LOGIC_CHAIN.md`, `REPORT.md` §7) carry over as the baseline.

## Model operations

Retrain on real data; monitor drift (MAE trend, feature distribution);
re-run the fairness gate (`backend/ml/fairness.py`, 15% target,
`REPORT.md` §6) before any release; version models beside
`backend/ml/artifacts/metrics.json`. Known pre-pilot tuning: day-level net
target (joint instead of inflow−outflow) and solver buffer calibration
against pressure-day dips (`REPORT.md` §§4–5).

## Integration

FastAPI services plug into the app backend unchanged; the LLM verbalizer
moves to a bank-approved provider behind the same JSON contract
(`backend/genai/client.py` failover pool). Frontend stays on the frozen
response schemas (`backend/app/schemas.py`).

## Business case

Engagement and trust, lower support load on "what is this transaction", and
a foundation for responsible financial products. No revenue claimed from
upsell — the product never upsells by design.
