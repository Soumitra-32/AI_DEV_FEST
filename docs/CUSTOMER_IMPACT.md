# Customer Impact Instrumentation & Telemetry

Shonchoy Copilot (*সঞ্চয় Copilot*) features rigorous customer-impact instrumentation that closes the loop between **AI insights**, **user action**, and **verifiable outcomes** without fabricating numbers, altering machine learning models, or imposing live A/B testing dependencies.

---

## 1. Architecture: The Three Evidence Layers

Shonchoy Copilot explicitly separates financial intelligence into three transparent evidence layers across both API responses (`GET /metrics`) and user interface dashboards (`/metrics`):

```text
┌────────────────────────────────────────────────────────────────────────┐
│  Evidence Layer 1: Model Evaluation & Offline Accuracy                 │
│  - LightGBM 14-day cash-flow forecast (MAE/RMSE vs trailing baselines) │
│  - Isolation Forest anomaly detector (Precision, Recall, F1, AUC)      │
│  - Logistic Regression consistency signal (AUC vs chance)              │
│  - Demographic fairness audit (72 group slices across personas)        │
├────────────────────────────────────────────────────────────────────────┤
│  Evidence Layer 2: Product Interaction Data & Customer Impact (Live)   │
│  - Real feedback: Total feedback, helpfulness rate, understanding rate │
│  - Recommendation lifecycle: shown → accepted/rejected → completed     │
│  - Action completion rate = actions completed / accepted               │
│  - Feature telemetry: savings plans created, forecast & anomaly views  │
│  - Zero fabrication guarantee: displays "No interaction data" if empty │
├────────────────────────────────────────────────────────────────────────┤
│  Evidence Layer 3: Simulation & Policy Context (Counterfactual)        │
│  - Bangladesh Bank 1 Oct 2026 MFS cash-out reform policy simulation    │
│  - Simulated fee savings (BDT/user/month) switching to Bangla QR / app │
│  - Counterfactual shortfall days avoided by budget timing buffer       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Recommendation Lifecycle Measurement

Recommendations are treated as measurable commitments, not passive impressions:

$$\text{Recommendation Shown} \xrightarrow{\text{User Choice}} \begin{cases} \text{Accepted} \xrightarrow{\text{Execution}} \text{Action Completed} \\ \text{Rejected} \\ \text{Reminded Later} \end{cases}$$

### Actions Supported in UI
On each recommendation card (such as fee-saving channel switches or month-end budgeting buffers):
* **`[I'll try this / এটি চেষ্টা করব]`**: Emits structured event `recommendation_accepted`.
* **`[Not relevant / প্রাসঙ্গিক নয়]`**: Emits structured event `recommendation_rejected`.
* **`[Remind me later / পরে মনে করিয়ে দিন]`**: Defers the recommendation without marking as rejected.
* **`[Mark completed / সম্পন্ন করেছি]`**: Emits `recommendation_action_completed` once the user executes the guidance.

### Denominator Integrity
* $\text{Recommendation Acceptance Rate} = \frac{\text{recommendations accepted}}{\text{recommendations shown}}$
* $\text{Action Completion Rate} = \frac{\text{actions completed}}{\text{recommendations accepted}}$
* *An action is NEVER counted merely because a recommendation was shown.*
* When denominators are zero, rates safely evaluate to `null` instead of raising or fabricating percentages.

---

## 3. Privacy-First Telemetry & Feedback APIs

All telemetry and feedback endpoints strictly adhere to **Privacy by Design**:
1. **Authenticated Users Only**: Requires valid token (`Authorization: Bearer <token>` or `X-Demo-Token`). Requests lacking tokens fail with `401 Unauthorized`.
2. **Server-Derived Identity**: The client cannot submit spoofed user IDs. Identity is resolved server-side.
3. **Salted Hash Respondent Tokens**: The internal user ID is salted and hashed (`SHA-256`, truncated to 12 hex characters). Raw user IDs never touch disk.
4. **Discarding Free-Text Comment PII**: Any free-text comments submitted are intentionally discarded after noting a boolean `has_comment: true`. No potential phone numbers, account digits, or personal text are ever stored.
5. **PII-Stripped Telemetry Properties**: Telemetry property dictionaries automatically strip keys containing sensitive markers (such as `account`, `pin`, `password`, `token`, or `phone`).

### `POST /feedback`
```json
{
  "feature": "savings_plan",
  "helpful": true,
  "understood": true,
  "acted_on": true,
  "rating": 5
}
```

Response:
```json
{
  "status": "recorded",
  "recorded_at": "2026-10-07T11:45:00+00:00",
  "respondent": "a1b2c3d4e5f6",
  "surface": "savings_plan",
  "feature": "savings_plan",
  "helpful": true,
  "understood": true,
  "acted_on": true,
  "rating": 5,
  "recommendation_id": null,
  "stored_fields": ["recorded_at", "respondent", "surface", "feature", "helpful", "understood", "acted_on", "rating", "intent", "recommendation_id", "has_comment"],
  "note": "No PII is stored: the user id is salted-hashed and any comment text is discarded."
}
```

### `POST /events`
Accepts structured telemetry events:
* `forecast_viewed`
* `savings_plan_viewed`
* `savings_plan_created`
* `recommendation_shown`
* `recommendation_accepted`
* `recommendation_rejected`
* `recommendation_action_completed`
* `recommendation_feedback`
* `anomaly_viewed`
* `copilot_used`
* `feedback_submitted`

Example:
```json
{
  "event_type": "recommendation_accepted",
  "feature": "tips",
  "recommendation_id": "tip-fee-switch",
  "properties": {
    "channel": "app",
    "potential_saving_bdt": 320
  }
}
```

---

## 4. Zero Fabrication & Safe Zero-Data State

When Shonchoy Copilot starts with fresh or empty artifact stores:
* `has_data` is `false`.
* `helpful_feedback_rate_pct`, `understanding_rate_pct`, and `action_completion_rate_pct` evaluate to `null`.
* Counts remain `0`.
* The `/metrics` UI renders the designated zero-data empty state:
  > **No interaction data collected yet (কোনো ইন্টারঅ্যাকশন ডেটা এখনো সংগৃহীত হয়নি)**
  > *Customer impact metrics update in real time as authenticated users interact with recommendations and submit feedback.*

Numbers are aggregated strictly from lines in `events.jsonl` and `feedback.jsonl`.

---

## 5. Demo Mode & Presets

For judging, demonstrations, and offline testing, Shonchoy Copilot features a persistent Demo Mode banner in the navigation bar:
* **Banner**: `DEMO MODE — Using synthetic transaction data`
* **Scenarios Available**:
  1. **Healthy Cash Flow**: Typical daily-wage or retail shopkeeper surplus with steady inflows.
  2. **Month-End Pressure**: Simulates scheduled rent and utility bills clustering on days 28–31.
  3. **High Avoidable Fees**: Simulates frequent cash-outs qualifying for 0% Bangla QR or digital app transfer savings.
  4. **Unusual Transaction**: Highlights spending anomalies detected by the Isolation Forest.
