# Logic chain — how an answer is produced

This file traces one user question from the transaction history to the sentence
on screen, and names the module that owns each step. The rule the whole project
runs on: **math and decisions live in Python; the LLM only verbalises structured
results and never invents a number.**

```
POST /chat-explain {"message": "৬ মাসে ৳৩০,০০০ জমাতে চাই", "language": "bn"}
  |
  |- 1. auth         app/deps.py            user_id comes from the token, never the body
  |- 2. rate limit   routers/chat_explain.py    20 questions / 60 s per token
  |- 3. classify     rules/guardrails.py    text -> whitelisted intent (+ injection check)
  |                                            unknown -> safe template, stop here
  |- 4. parse goal   genai/fallback.py      "৬ মাসে ৳৩০,০০০" -> (30000, 6)
  |                                            a missing half is asked for, never guessed
  |- 5. context      services/explain_service.py   rules + models -> one JSON document
  |     |- savings_solver.solve()      feasibility, trade-offs, do-nothing cost
  |     |- forecast_service            14-day outlook + pressure days (rule or model)
  |     |- ml/explain.top_drivers()    SHAP reasons behind that outlook
  |     `- data/features.py            fee, cash-out and behaviour aggregates
  |- 6. template     genai/fallback.py      deterministic bn + en answer (always built first)
  |- 7. verbalize    genai/explain.py       optional LLM call (genai/prompts.py)
  |     `- accepted only if: strict JSON schema AND banned-output filter AND number grounding
  `- 8. response     app/schemas.py         ExplainResponse + Prediction/Assumption/Explanation
```

## Why each check exists

| Check | Module | What it stops |
|---|---|---|
| Intent whitelist | `rules/guardrails.classify_intent` | A question outside our scope reaching the model together with our user's data |
| Prompt-injection detection | `guardrails.looks_like_injection` | "Ignore your instructions..." becoming an instruction instead of `unknown` |
| Roles separated, JSON only | `genai/prompts` | User text being concatenated into a prompt, and prose leaking out of the JSON contract |
| Strict response schema | `genai/explain.Verbalization` (`extra="forbid"`) | A model inventing new fields such as `recommended_product` |
| Banned-output filter | `guardrails.screen` | Loan offers, urgency, guaranteed returns, promotion, approve/deny, numeric scores |
| Number grounding | `guardrails.ungrounded_numbers` | A figure that exists nowhere in the computed context |
| Template fallback | `genai/fallback.render` | The demo breaking when the API is slow, down, unkeyed, or answered badly |

## Source of every number in an answer

| Number | Computed by |
|---|---|
| goal, monthly amount, buffer, do-nothing cost | `rules/savings_solver.py` |
| 14-day inflow/outflow, pressure days | `app/services/forecast_service.py` (LightGBM, or the trailing-average rule) |
| "why" behind a forecast day | `ml/explain.top_drivers` (LightGBM SHAP) |
| cash-out fee and the cheaper channel | `services/explain_service.fees_context`, from `data/features.py` |
| consistency band and its reasons | `services/explain_service.consistency_context` (behavioural for now; the trained model arrives in phase 5) |

The LLM appears nowhere in that table. That is the point.

## Note on the synthetic data

Every figure above comes from the generated dataset (`backend/data/generator.py`),
and the fee rates are simulated for the demo, not official upay pricing — the
answers say so in the text, and `docs/DATA_ASSUMPTIONS.md` documents each one.

