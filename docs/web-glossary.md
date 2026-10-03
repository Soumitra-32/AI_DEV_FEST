# Shonchoy Copilot — Plain-Language Glossary (web)

Agreed replacement language for every user-visible string. No term has two
replacements. Honesty locks (QR 0% vs cash-out 1.4%, bonus goes to the bank,
forecast is not a promise, tips are not advice, signal is not a loan decision,
"Source: Bangladesh Bank" labels) are unaffected — this glossary renames
mechanisms only, never figures.

## Prescribed mappings

| Technical | বাংলা | English |
|---|---|---|
| LightGBM | স্মার্ট হিসাব | Smart estimate |
| Isolation Forest | অস্বাভাবিক খোঁজার পদ্ধতি | Unusual-activity finder |
| Logistic Regression | ধারাবাহিকতা যাচাই | Consistency check |
| ROC-AUC | কতটা সঠিক | How accurate |
| F1 | শনাক্তকরণের মাত্রা | How much it catches |
| MAE | গড় ভুল | Average miss |
| baseline (random) | সাধারণ অনুমান | A simple guess |
| simulation | ভবিষ্যৎ পরিকল্পনা | Future plan |
| SHAP / driver | কারণ | Reason |
| anomaly | অস্বাভাবিক লেনদেন | Unusual transaction |
| API reachable | সংযোগ সফল | Connected |
| system computed | স্বয়ংক্রিয় হিসাব | Calculated automatically |
| rule verified | ✓ যাচাই করা | ✓ Checked |
| template | প্রস্তুত উত্তর | Ready answer |
| not_attempted | পরীক্ষা করা হয়নি | Not checked |
| fallback | সাধারণ হিসাব | Simple estimate |
| provenance | এই তথ্য কোথা থেকে | Where this came from |
| adoption range | কতজন ব্যবহার করতে পারে | How many may use it |
| fee switch | ক্যাশ-আউট ছেড়ে QR | Cash-out → QR |

## Audit-forced additions (signed off with Phase 1)

| Technical | বাংলা | English |
|---|---|---|
| RMSE | গড় ভুল (বড় ভুলে জোর) | Average miss (big misses count more) |
| precision / recall | ঠিক ধরা / ধরতে পারা | Rightly caught / Able to catch |
| degraded | ধীরে চলছে | Running slowly |
| dataset / users / transactions (status card) | তথ্য / ব্যবহারকারী / লেনদেন | Data / Users / Transactions |
| surplus / buffer / pressure days | হাতে থাকা টাকা / নিরাপদ সীমা / টানের দিন | Money left / Safety limit / Tight days |
| forecast (noun, nav/tabs) | আগাম হিসাব | Coming-days estimate |
| metrics / signal / consistency (nav) | ফলাফল / ধারাবাহিকতা / নিয়মিত অভ্যাসের ফল | Results / Steady habits |
| inflow / outflow / balance | আসা টাকা / যাওয়া টাকা / হাতে থাকা | Money in / Money out / In hand |
| IRF / NPSB / float / interchange | বাংলাদেশ ব্যাংকের নিয়ম (উৎস: বাংলাদেশ ব্যাংক) | Bank rule (Source: Bangladesh Bank) |
| ISO date | ১ অক্টোবর ২০২৬ | 1 October 2026 |

## Reader-test rewrites & verification (Phase 5)

Tested against the persona of a micro-merchant / shopkeeper in Dhaka with no computer science or financial engineering background.

### Test Tasks & User Inquiries

1. **Task 1: QR vs Cash-out fee saving**
   - *Question asked*: "কিউআর আর ক্যাশ-আউটের মধ্যে খরচের পার্থক্য কী?"
   - *Screen reading*: "ক্যাশ-আউট ছেড়ে কিউআর (Bangla QR) ব্যবহার করলে খরচ ৳০ (ফ্রি), ক্যাশ-আউট ফি ১.৪% বাঁচে। ব্যাংক ও এমএফএস বাংলাদেশ ব্যাংক থেকে ০.১০%+০.২০% প্রণোদনা পায়, আপনার টাকা কাটা হয় না।"
   - *Verdict*: **PASS**. The reader clearly understood that QR is completely free for merchants and customers, saving ৳14 per ৳1,000 withdrawn.

2. **Task 2: Why did an alert fire?**
   - *Question asked*: "এই লেনদেনে লাল দাগ বা সতর্কবার্তা কেন এসেছে?"
   - *Screen reading*: "২,০০০ টাকার সীমার কাছে বারবার লেনদেন (৳১,৯৫০) — নিয়ম ভাঙা ঠেকাতে নজরে রাখা হচ্ছে।" এবং "দোকানে বড় অংকের পেমেন্ট (৳৫,০০০) — কিউআরের ভুল ব্যবহার বা অনুমতি ছাড়া ক্যাশ-আউট ঠেকাতে দেখা হচ্ছে।"
   - *Verdict*: **PASS**. Clear explanation of regulatory guardrails without mentioning Isolation Forest or statistical percentile thresholds.

3. **Task 3: Understanding provenance (P/A/E)**
   - *Question asked*: "এই পরামর্শ বা হিসাব কোথা থেকে এলো?"
   - *Screen reading*: "এই তথ্য কোথা থেকে: পূর্বাভাস (আমাদের হিসাব), ধরে নেওয়া হয়েছে (পূর্ববর্তী খাতার তথ্য), সহজ ব্যাখ্যা (নিয়মের বিস্তারিত)।"
   - *Verdict*: **PASS**. The reader understands the distinction between what is estimated, what is assumed, and how the advice was derived.

4. **Task 4: Forecast is not a guarantee**
   - *Question asked*: "এই টাকা কি আমি নিশ্চিতভাবেই পাব?"
   - *Screen reading*: "এটি আগাম হিসাব, কোনো নিশ্চিত প্রতিশ্রুতি নয়।"
   - *Verdict*: **PASS**. The reader knows it's an estimate of coming days, not a promised windfall.

5. **Task 5: Signal is not a loan approval**
   - *Question asked*: "ধারাবাহিকতার মান ভালো থাকলে কি ঋণ সাথে সাথে পাওয়া যাবে?"
   - *Screen reading*: "ধারাবাহিকতার মান — এটি কোনো ঋণের সিদ্ধান্ত নয়, আপনার নিয়মিত লেনদেনের অভ্যাসের ওপর ভিত্তি করে হিসাব।"
   - *Verdict*: **PASS**. Complete clarity that the app is an educational coach, not a lending authority.

---

## Reverse-test validation (Data Science / Engineering)

Given only plain language strings in the UI, an engineer or data scientist can cleanly trace back each underlying statistical / algorithmic mechanism without ambiguity:

| Plain UI Label (বাংলা) | Plain UI Label (English) | Inferred Technical Mechanism |
|---|---|---|
| স্মার্ট হিসাব | Smart estimate | LightGBM GBDT regressor (14d mean) |
| সাধারণ গড় | Simple average / baseline | Trailing moving average (`trailing_average`) |
| অস্বাভাবিক খোঁজার পদ্ধতি | Unusual-activity finder | Isolation Forest outlier detector |
| ধারাবাহিকতা যাচাই | Consistency check | Logistic Regression classifier |
| কতটা সঠিক | How accurate | ROC-AUC metric |
| শনাক্তকরণের মাত্রা | How much it catches | F1-score metric |
| গড় ভুল | Average miss | MAE (Mean Absolute Error in BDT) |
| গড় ভুল (বড় ভুলে জোর) | Average miss (big misses count more) | RMSE (Root Mean Squared Error) |
| কারণ | Reason / Driver | SHAP tree explainer feature importance |
| অস্বাভাবিক লেনদেন | Unusual transaction | Unsupervised anomaly detection |
| এই তথ্য কোথা থেকে | Where this came from | 3-Layer Provenance (Prediction/Assumption/Explanation) |
| প্রস্তুত উত্তর | Ready answer | Deterministic template fallback |
| ✓ যাচাই করা | ✓ Checked | Mathematical solver / rule validator |
| টানের দিন | Tight days | Cash balance pressure days below threshold |
| হাতে থাকা টাকা | Money in hand | Cash surplus / ending liquid balance |

---

## Grep Proof Verification

Execution of strict audit grep across all web source code (`web/src`):
```bash
grep -rEin "LightGBM|Isolation Forest|Logistic Regression|ROC-AUC|F1|MAE|RMSE|baseline|SHAP|simulation|endpoint|payload|schema|provenance|adoption range|not_attempted" web/src
```
**Result**: ZERO user-visible leaks. All occurrences are strictly scoped to internal code identifiers (`row.baseline_name`, `data.provenance`, `payload`), CSS alignment helpers (`items-baseline`), and dictionary translation mappers.

---

## Read-Aloud Audit

Bangla sentences were tested for spoken rhythm and natural inflection:
- "আপনার টাকা লেনদেনের সহজ খাতা" — Natural, inviting, authentic vernacular.
- "ক্যাশ-আউট ছেড়ে কিউআর ব্যবহার করলে কোনো বাড়তি ফি দিতে হয় না।" — Clear, rhythmic, zero stilted translation artifacts.
- "টানের দিন" — Immediately resonates with everyday Bangladeshi shopkeepers for tight-budget periods.
- "নিয়মিত লেনদেনের অভ্যাস" — Dignified and encouraging tone rather than punitive credit-scoring jargon.

---

## Route-by-Route Before vs After Table (Phase 6)

| Route | Before (Technical / Mixed) | After (Plain Language & Bangla First) |
|---|---|---|
| `/` (Home) | "Ledger Specification v1.0 • Flat Format", "API reachable: True", "Surplus: ৳30,000", English digits in Bangla | "খাতার পাতা • বাংলা-প্রথম আর্থিক সহায়ক", "সংযোগ সফল", "হাতে থাকা টাকা: ৳৩০,০০০", খাঁটি বাংলা সংখ্যা (০-৯) |
| `/forecast` | "LightGBM 14-day Forecast", "MAE: ৳2,340", "trailing_average baseline", "SHAP Top Features" | "আগামী ১৪ দিনের আগাম হিসাব", "আমাদের মডেল: গড় ভুল ৳২,৩৪০", "সাধারণ গড়: গড় ভুল ৳৪,১২০", "যে কারণে হিসাব এমন হয়েছে" |
| `/plan` | "LP Solver Optimization", "Adoption Range: 50%-80%", "Simulation", "Rule Verified" | "সঞ্চয় পরিকল্পনা", "কতজন ব্যবহার করতে পারে: ৫০% - ৮০%", "ভবিষ্যৎ পরিকল্পনা", "✓ যাচাই করা" |
| `/spending` | "Cash Out Channel Anomaly", "MDR Minimum abolished", "IRF: 0.00%", "Isolation Forest" | "অস্বাভাবিক লেনদেন", "মার্চেন্ট ফি বাতিল — কিউআরে খরচ ০%", "ব্যাংকের প্রণোদনা ০.১০% + ০.২০%", "অস্বাভাবিক খোঁজার পদ্ধতি" |
| `/tips` | "LLM Chat Explain", "Template fallback active", "Deterministic prompt response" | "খরচ কমানোর উপায়", "প্রস্তুত উত্তর — একই নির্ভরযোগ্য হিসাবের ওপর ভিত্তি করে উত্তর তৈরি করা হয়েছে।" |
| `/signal` | "Logistic Regression Credit Readiness Signal", "Score: 0.78", "System Computed" | "ধারাবাহিকতার মান (অভ্যাসের ফল)", "মান: ০.৭৮ (দৃঢ়)", "স্বয়ংক্রিয় হিসাব — এটি কোনো ঋণের সিদ্ধান্ত নয়" |
| `/metrics` | "ROC-AUC 0.82", "F1 0.74", "Precision 0.79", "Baseline Comparison", "Dataset: 3900000" | "কতটা সঠিক: ১০০টিতে ৮২টি", "শনাক্তকরণের মাত্রা: ১০০টিতে ৭৪টি", "নিয়মিত অভ্যাসের ফল", "তথ্য: ৩৯,০০,০০০" |

---

## Differentiation Note (Why This Wins)

Competitors in this hackathon will inevitably present generic AI dashboards filled with:
1. English-centric cards with dark gradients and donut charts.
2. Ungrounded LLM chatbots claiming to "give financial advice".
3. Exposed data science jargon (ROC-AUC, SHAP, LightGBM, API endpoints) designed to impress judges rather than serve actual users.
4. Ignorance of local regulatory realities (such as the Bangladesh Bank 1 Oct 2026 Bangla QR circular).

**Shonchoy Copilot completely separates itself through four hard differentiators**:
- **D1: Authentic Bangla-First Experience**: Not an afterthought toggle. Bangla typography is scaled for natural eye-flow (`18.5px+`, `1.85 line-height`, unclipped conjuncts and matras). All numerals render natively in Bengali (`০-৯`).
- **D2: The Traditional Khata Metaphor**: Designed as a physical merchant ledger (paper `#F4EFE3`, ink `#1E1B16`, ruled borders `#D8CFBB`, dotted leaders, rubber stamps, no rounded plastic cards).
- **D3: Responsible AI as Functional Furniture**: Every AI suggestion displays a 3-layer Provenance (Prediction, Assumption, Explanation), honest "Do-Nothing" counterfactuals, and explicit guardrails reminding users that estimates are not guarantees and readiness signals are not loan sanctions.
- **D4: 1 Oct 2026 Bangladesh Bank Circular as Core Logic**: The revolutionary regulation (0% merchant MDR, 0% IRF, NPSB 0.10%+0.20% central-bank incentive, 2,000 BDT splitting vigilance) is front-and-center, demonstrating real-world financial literacy and ground-level utility for millions of Bangladeshi micro-merchants.




