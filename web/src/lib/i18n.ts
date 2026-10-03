/**
 * Bangla / English dictionary and formatting helpers.
 *
 * Kept as plain TypeScript (no JSX) so it can be imported from anywhere.
 * Money is always printed with ৳ and, in Bangla, with Bangla numerals.
 */

export type Lang = "bn" | "en";

export const DEFAULT_LANG: Lang = "bn";

export const LANGUAGES: ReadonlyArray<{ code: Lang; label: string }> = [
  { code: "bn", label: "বাংলা" },
  { code: "en", label: "EN" },
];

const en = {
  appName: "Shonchoy Copilot",
  subTitle: "Ledger Format • Bangla-First Financial Coach",
  subTitleBadge: "Ledger Specification v1.0 • Flat Format",
  tagline:
    "A Bangla-first coach that explains your transactions, plans a realistic saving goal, and warns you before the month-end squeeze — without selling you anything.",

  "nav.home": "Home",
  "nav.plan": "Savings",
  "nav.forecast": "Forecast",
  "nav.spending": "Expense",
  "nav.tips": "Tips",
  "nav.signal": "Consistency",
  "nav.metrics": "Metrics",
  "nav.more": "More",

  "lang.switchTo": "Switch language",

  "stamp.computed": "System Computed",
  "stamp.easyExplain": "Plain Language",
  "stamp.verified": "Rule Verified",

  "status.title": "Connection and dataset status",
  "status.checking": "Checking the API…",
  "status.apiReachable": "API reachable",
  "status.apiUnreachable": "API not reachable",
  "status.apiHint":
    "Start the backend with: uvicorn backend.app.main:app --reload (from the repo root), then reload this page.",
  "status.serviceVersion": "Version",
  "status.database": "Dataset",
  "status.databaseReady": "Ready",
  "status.databaseMissing": "Missing",
  "status.users": "Users",
  "status.transactions": "Transactions",
  "status.generatedAt": "Generated",
  "status.features": "Active Modules",
  "status.degraded": "Degraded",

  "identity.title": "Account Holder",
  "identity.persona": "Persona",
  "identity.district": "District",
  "identity.incomeBand": "Income",
  "identity.cohort": "Cohort",
  "identity.demoUser": "Demo Profile",

  "common.prediction": "Prediction",
  "common.assumption": "Assumption",
  "common.explanation": "Explanation",
  "common.source": "Source",
  "common.doNothing": "What happens if I do nothing?",
  "common.doNothingCost": "Estimated cost of doing nothing",
  "common.doNothingConfirm": "I understand",
  "common.doNothingDismiss": "Close",
  "common.doNothingChosen": "You chose to do nothing. No automated change was made.",
  "common.doNothingHint":
    "Every suggestion is yours to accept or ignore. Nothing happens without your explicit consent.",
  "common.doNothingOutcome":
    "After 6 months, savings will remain ৳0. That is entirely your decision.",
  "common.doNothingOutcomeN":
    "After {months} months, savings will remain ৳0. That is entirely your decision.",
  "common.doNothingDisclaimer":
    "No coercion, no penalties. The app never executes transactions or makes lending decisions without you.",

  "banner.title": "Clarification & Safeguard Commitment",
  "banner.notADecision":
    "This is an educational guide, not a credit or lending decision. upay and lenders make no automated decisions from this. No money moves without your explicit consent.",

  "home.next.title": "Available Modules",
  "home.next.body":
    "The 14-day cash-flow forecast, savings plan solver, and spending companion are live. Explore below.",
  "home.startSavings": "Start Savings Plan",
  "home.viewDetails": "View Detailed Breakdown",

  "comingSoon.title": "Coming Soon",
  "comingSoon.phase5": "Spending companion (Phase 5)",
  "comingSoon.phase7": "Tips and consistency signal (Phase 7)",
  "comingSoon.phase8": "Evidence and metrics (Phase 8)",

  "forecast.headerTag": "14-Day Cash Flow",
  "forecast.title": "Next 14 Days Cash-Flow & Dues",
  "forecast.subtitle":
    "Inflow, outflow and wallet balance — model-shaped, level-checked against your own history.",
  "forecast.monthEndPreset": "Show month-end 28–31",
  "forecast.latestPreset": "Latest 14 days",
  "forecast.netSourceModel": "model",
  "forecast.netSourceAnchor": "history-checked",
  "forecast.netSourceDifference": "baseline",
  "forecast.loading": "Computing cash-flow forecast…",
  "forecast.days": "Day",
  "forecast.inflow": "Money in",
  "forecast.outflow": "Money out",
  "forecast.net": "Net",
  "forecast.balance": "Balance",
  "forecast.pressureTitle": "Pressure Days",
  "forecast.pressureNone": "No pressure days in this window — the balance stays above the safety buffer.",
  "forecast.pressureBadge": "Expense Pressure",
  "forecast.reasonNegativeNet": "money out exceeds money in",
  "forecast.reasonBelowBuffer": "balance drops below safety buffer",
  "forecast.reasonBoth": "money out exceeds money in & balance drops below buffer",
  "forecast.modelAccuracy": "Model Accuracy vs Simple Baseline",
  "forecast.noMetrics": "Model accuracy will appear after training run writes metrics.json.",
  "forecast.table": "Day-by-Day Ledger",
  "forecast.tableSub": "14-Day Statement",
  "forecast.planSavingsPrompt": "Want to plan savings from your surplus?",

  "plan.headerTag": "Savings & Surplus Ledger",
  "plan.title": "Savings Plan Ledger",
  "plan.subtitle":
    "Enter a goal and timeline. Checked against your own forecasted surplus, not an average.",
  "plan.goal": "Goal Target (৳)",
  "plan.months": "Duration (Months)",
  "plan.submit": "Calculate Plan",
  "plan.calculating": "Solving the plan…",
  "plan.feasible": "Plan is Feasible",
  "plan.infeasible": "Target Exceeds Monthly Surplus",
  "plan.requiredMonthly": "Required Monthly",
  "plan.feasibleMonthly": "Feasible Monthly Surplus",
  "plan.surplus": "Forecasted Monthly Surplus",
  "plan.buffer": "Safety Buffer",
  "plan.arithmetic": "Calculation Trace",
  "plan.tradeOffs": "Alternative Options",
  "plan.pressureWarning":
    "Month-end pressure days detected inside this period. Keep your safety buffer intact.",
  "plan.action.reduce": "Reduce Target",
  "plan.action.delay": "Extend Timeline",
  "plan.action.switch": "Switch Fee Channel",
  "plan.action.do_nothing": "Do Nothing",
  "plan.reviewForecastPrompt": "Review 14-day cash-flow forecast?",

  "spending.headerTag": "Expense & Fee Analysis",
  "spending.title": "Spending Companion",
  "spending.subtitle": "Analyze recent transactions and identify fee-saving opportunities.",
  "spending.loading": "Analyzing spending patterns…",
  "spending.summary": "Ledger Overview",
  "spending.cashOutCount": "Cash-Outs",
  "spending.cashOutCountSub": "Total cash-outs in the last 30 days",
  "spending.cashOutVolume": "Cash-Out Volume",
  "spending.cashOutVolumeSub": "Total cash withdrawn via agent points",
  "spending.feePaid": "Fees Paid",
  "spending.feePaidSub": "Calculated cash-out fee paid (1.85%)",
  "spending.singleRuleTop": "Single rule top • Double rule bottom (Balanced)",
  "spending.anomalies": "Unusual Transactions",
  "spending.anomaliesNone": "No unusual transactions detected in the selected period.",
  "spending.reason": "Flag Reason",
  "spending.action": "Suggested Action",
  "spending.feeSwitch": "Fee Switch Opportunity",
  "spending.feeSwitchDesc": "Switching from agent cash-out to app transfers or direct merchant payment can avoid cash-out fees.",
  "spending.potentialSaving": "Monthly Saving",
  "spending.currentFee": "Current Monthly Fee",
  "spending.altChannel": "Alternative Channel",
  "spending.altFee": "Alternative Fee",
  "spending.adoption": "Estimated Adoption",
  "spending.perMonth": "/month",
  "spending.times": "times",
  "spending.daysUnit": "days",
  "spending.warningStripTitle": "Warning Marker",
  "spending.warningStripText": "Days 28–31 typically have high cash-out pressure.",

  "voice.label": "Enter Financial Goal or Query",
  "voice.speak": "Voice",
  "voice.listening": "Listening…",
  "voice.unsupported": "Voice input is not supported in this browser. Please type instead.",
  "voice.denied": "Microphone blocked. Allow mic access in the browser address bar, then try again.",
  "voice.nomic": "No microphone found. Check your device mic, then try again.",
  "voice.offline": "Voice needs internet (recognition runs online). Reconnect, then try again.",
  "voice.nospeech": "Didn't hear anything. Speak closer to the mic and try again.",
  "voice.heard": "I heard:",
  "voice.confirm": "Calculate",
  "voice.retry": "Speak again",
  "voice.needBoth": "Enter both the amount and the months, then calculate.",
  "voice.placeholder": "e.g., I want to save ৳30,000 in 6 months",
  "voice.suggestedTitle": "Suggested Queries:",

  "tips.headerTag": "Personalized Coaching",
  "tips.title": "Personalized Coaching Tips",
  "tips.subtitle": "Contextual advice based on your cash flow and transaction habits.",
  "tips.loading": "Loading tips…",
  "tips.whyThisTip": "Why this tip?",
  "tips.suggestedAction": "Suggested Action",
  "tips.none": "No specific warnings right now. Your habits look steady.",
  "tips.coachAdvice": "Coach Advice",
  "tips.coreGuidance": "Core Behavioral Guidance",
  "tips.unavailable": "Live data unavailable right now — showing nothing instead of a guess. Please retry with the API running.",
  "tips.stampRule": "Rule-Based",
  "tips.stampForecast": "Forecast",
  "tips.stampPlan": "Planning",

  "signal.headerTag": "Consistency Index",
  "signal.title": "Financial Consistency Signal",
  "signal.subtitle": "Consistency band measuring transaction stability over time.",
  "signal.loading": "Evaluating consistency…",
  "signal.band": "Consistency Band",
  "signal.factors": "Top Contributing Factors",
  "signal.improvements": "Areas for Improvement",
  "signal.improves": "Improves",
  "signal.weakens": "Weakens",
  "signal.comingSoon": "Financial consistency model will be available in the next training cycle.",
  "signal.educationalBadge": "Educational",
  "signal.educationalNote": "This is strictly an educational measurement, never used for credit approval.",
  "signal.guaranteeTitle": "Ledger Guarantee",
  "signal.bandSteady": "Steady",
  "signal.bandBuilding": "Building",
  "signal.bandStrong": "Strong",
  "signal.unavailable": "Live signal unavailable right now — no band is shown instead of a guess. Please retry with the API running.",
  "signal.bandRating": "Medium-High Consistency",
  "signal.step1": "1. Building",
  "signal.step2": "2. Steady ●",
  "signal.step3": "3. Strong",

  "metrics.headerTag": "Transparency & Model Evaluation",
  "metrics.title": "Evidence, Metrics & Fairness",
  "metrics.subtitle": "Transparent model evaluation against simple baseline heuristics.",
  "metrics.loading": "Loading evaluation metrics…",
  "metrics.forecast": "Cash-Flow Forecast (LightGBM)",
  "metrics.model": "Model",
  "metrics.baseline": "Baseline",
  "metrics.mae": "MAE",
  "metrics.rmse": "RMSE",
  "metrics.improvement": "Improvement",
  "metrics.anomaly": "Anomaly Detection (Isolation Forest)",
  "metrics.anomalyDesc": "Detects volume anomalies (e.g. 4x normal withdrawal amount) and temporal outliers without circular data leakage.",
  "metrics.signal": "Consistency Model (Logistic Regression)",
  "metrics.fairness": "Fairness Across Cohorts",
  "metrics.fairnessDesc": "Evaluation across 5 personas and 10 districts ensures consistent accuracy across rural and urban user cohorts.",
  "metrics.demoAudit": "Demo Audit",
  "metrics.comingSoon": "Fairness report generates upon completion of model evaluation suite.",
  "metrics.fairnessTable": "Cohort Fairness Audit Ledger",
  "metrics.dimension": "Dimension",
  "metrics.group": "Cohort Group",
  "metrics.metric": "Metric",
  "metrics.value": "Measured Value",
  "metrics.gap": "Relative Gap",
  "metrics.impactTitle": "Observed Real-World Impact (Simulation)",
  "metrics.precision": "Precision",
  "metrics.recall": "Recall",
  "metrics.f1": "F1 Score",
  "metrics.auc": "ROC-AUC",
  "metrics.inflow": "Inflow (14d)",
  "metrics.outflow": "Outflow (14d)",
  "metrics.net": "Net Flow (14d)",
  "metrics.notesTitle": "Audit Notes & Methodology",
  "forecast.driversTitle": "Top Forecast Factors (SHAP Drivers)",
  "forecast.increasesOutflow": "Increases predicted outflow",
  "forecast.decreasesOutflow": "Decreases predicted outflow",

  "footer.ledgerSystem": "Shonchoy Copilot • Ledger System",
  "footer.demoDisclaimer": "Demo Data — All figures are synthetic.",

  "error.title": "Something went wrong",
  "error.retry": "Try again",
} as const;

type TranslationKey = keyof typeof en;
type Dictionary = Record<TranslationKey, string>;

const bn: Dictionary = {
  appName: "সঞ্চয় Copilot",
  subTitle: "খতিয়ান ফরম্যাট • বাংলা-প্রথম আর্থিক সহায়ক",
  subTitleBadge: "খতিয়ান স্পেসিফিকেশন ১.০ • ফ্ল্যাট ফরম্যাট",
  tagline:
    "দোকানের খাঁটি লাল-বাঁধানো জাবেদা ও খতিয়ান খাতার নান্দনিকতা। সম্পূর্ণ ফ্ল্যাট, শান্ত, উচ্চ পঠনযোগ্যতা এবং শূন্য অলঙ্করণ সহ সাধারণ মানুষের জন্য নির্মিত খাঁটি ডিজিটাল লেজার।",

  "nav.home": "হোম",
  "nav.plan": "সঞ্চয়",
  "nav.forecast": "পূর্বাভাস",
  "nav.spending": "খরচ",
  "nav.tips": "পরামর্শ",
  "nav.signal": "ধারাবাহিকতা",
  "nav.metrics": "মেট্রিক্স",
  "nav.more": "আরও",

  "lang.switchTo": "ভাষা নির্বাচন",

  "stamp.computed": "সিস্টেম হিসাব করেছে",
  "stamp.easyExplain": "সহজ ব্যাখ্যা",
  "stamp.verified": "যাচাইকৃত",

  "status.title": "সংযোগ ও ডেটাসেটের স্থিতি",
  "status.checking": "API পরীক্ষা করা হচ্ছে…",
  "status.apiReachable": "API সংযোগ সফল",
  "status.apiUnreachable": "API সংযোগ বিচ্ছিন্ন",
  "status.apiHint":
    "ব্যাকএন্ড চালু করতে: uvicorn backend.app.main:app --reload (রেপোর রুট ডিরেক্টরি থেকে), তারপর এই পৃষ্ঠাটি রিলোড করুন।",
  "status.serviceVersion": "সংস্করণ",
  "status.database": "খতিয়ান ডেটা",
  "status.databaseReady": "প্রস্তুত",
  "status.databaseMissing": "অনুপস্থিত",
  "status.users": "ব্যবহারকারী",
  "status.transactions": "মোট লেনদেন",
  "status.generatedAt": "তৈরির তারিখ",
  "status.features": "সক্রিয় মডিউল",
  "status.degraded": "সীমিত",

  "identity.title": "হিসাবধারী",
  "identity.persona": "পেশা-ধরন",
  "identity.district": "জেলা",
  "identity.incomeBand": "আয়ের স্তর",
  "identity.cohort": "দল",
  "identity.demoUser": "ডেমো প্রোফাইল",

  "common.prediction": "পূর্বাভাস (Prediction)",
  "common.assumption": "ধরে নেওয়া হয়েছে (Assumption)",
  "common.explanation": "সহজ ব্যাখ্যা (Explanation)",
  "common.source": "উৎস",
  "common.doNothing": "কিছু না করলে কী হবে?",
  "common.doNothingCost": "কিছু না করলে সম্ভাব্য খরচ",
  "common.doNothingConfirm": "হ্যাঁ, বুঝেছি",
  "common.doNothingDismiss": "বন্ধ করুন",
  "common.doNothingChosen": "আপনি কিছু না করাই বেছে নিয়েছেন। কোনো স্বয়ংক্রিয় পরিবর্তন হয়নি।",
  "common.doNothingHint":
    "প্রতিটি পরামর্শ গ্রহণ বা প্রত্যাখ্যান করা সম্পূর্ণ আপনার এখতিয়ার। আপনার স্পষ্ট অনুমতি ব্যতিরেকে কোনো সিদ্ধান্ত নেওয়া হয় না।",
  "common.doNothingOutcome":
    "৬ মাস পরে সঞ্চয় ৳০ থাকবে। এটাও আপনার নিজস্ব সিদ্ধান্ত।",
  "common.doNothingOutcomeN":
    "{months} মাস পরে সঞ্চয় ৳০ থাকবে। এটাও আপনার নিজস্ব সিদ্ধান্ত।",
  "common.doNothingDisclaimer":
    "কোনো জোরজবরদস্তি বা বাড়তি দায়বদ্ধতা নেই। অ্যাপ আপনার অনুমতি ছাড়া কোনো লেনদেন করবে না।",

  "banner.title": "স্পষ্টকরণ ও সুরক্ষা অঙ্গীকার",
  "banner.notADecision":
    "এটি শুধু শিক্ষামূলক ইঙ্গিত, কোনো ঋণ বা আর্থিক সিদ্ধান্ত নয়। আপনার অনুমতি ছাড়া কোনো টাকা সরানো হবে না।",

  "home.next.title": "সক্রিয় খতিয়ান মডিউল",
  "home.next.body":
    "১৪ দিনের ক্যাশ-ফ্লো পূর্বাভাস, সঞ্চয় পরিকল্পনাকারী এবং খরচ সহযোগী প্রস্তুত। বিস্তারিত জানতে নিচে দেখুন।",
  "home.startSavings": "সঞ্চয় শুরু করুন",
  "home.viewDetails": "বিস্তারিত হিসাব দেখুন",

  "comingSoon.title": "শীঘ্রই আসছে",
  "comingSoon.phase5": "খরচ সহযোগী (পঞ্চম ধাপ)",
  "comingSoon.phase7": "পরামর্শ ও ধারাবাহিকতা (সপ্তম ধাপ)",
  "comingSoon.phase8": "প্রমাণ ও মেট্রিক্স (অষ্টম ধাপ)",

  "forecast.headerTag": "১৪ দিনের নগদ প্রবাহ",
  "forecast.title": "আগামী ১৪ দিনের ক্যাশ-ফ্লো পূর্বাভাস ও দেনা-পাওনা",
  "forecast.subtitle":
    "মডেলের ধরনে, আপনার নিজের ইতিহাস দিয়ে যাচাই করা টাকা আসা, যাওয়া ও ব্যালেন্সের হিসাব।",
  "forecast.monthEndPreset": "মাস শেষের ২৮–৩১ দেখুন",
  "forecast.latestPreset": "সর্বশেষ ১৪ দিন",
  "forecast.netSourceModel": "মডেল",
  "forecast.netSourceAnchor": "ইতিহাস-যাচাইকৃত",
  "forecast.netSourceDifference": "বেসলাইন",
  "forecast.loading": "ক্যাশ-ফ্লো পূর্বাভাস হিসাব করা হচ্ছে…",
  "forecast.days": "তারিখ",
  "forecast.inflow": "টাকা আসছে",
  "forecast.outflow": "টাকা যাচ্ছে",
  "forecast.net": "নিট",
  "forecast.balance": "ব্যালেন্স",
  "forecast.pressureTitle": "টানাটানির দিন",
  "forecast.pressureNone": "এই মেয়াদে কোনো টানাটানির দিন নেই — ব্যালেন্স সেফটি বাফারের উপরেই থাকছে।",
  "forecast.pressureBadge": "ব্যয়ের চাপ",
  "forecast.reasonNegativeNet": "আসা টাকার চেয়ে যাওয়া টাকা বেশি",
  "forecast.reasonBelowBuffer": "ব্যালেন্স সেফটি বাফারের নিচে নেমে আসছে",
  "forecast.reasonBoth": "আসা টাকার চেয়ে যাওয়া টাকা বেশি ও ব্যালেন্স বাফারের নিচে",
  "forecast.modelAccuracy": "সহজ নিয়মের তুলনায় মডেলের নির্ভুলতা",
  "forecast.noMetrics": "প্রশিক্ষণ চালিয়ে metrics.json লেখা হলে এখানে নির্ভুলতা দৃশ্যমান হবে।",
  "forecast.table": "দিন ধরে হিসাবের খতিয়ান",
  "forecast.tableSub": "১৪ দিনের হিসাবের বিবরণী",
  "forecast.planSavingsPrompt": "উদ্বৃত্তের ওপর সঞ্চয় পরিকল্পনা করতে চান?",

  "plan.headerTag": "সঞ্চয় ও উদ্বৃত্ত হিসাব",
  "plan.title": "সঞ্চয় পরিকল্পনা খাতা",
  "plan.subtitle":
    "আপনার লক্ষ্য ও সময় লিখুন। গড় হিসাব নয়, আপনার নিজস্ব পূর্বাভাসকৃত উদ্বৃত্তের ওপর ভিত্তি করে সমাধান।",
  "plan.goal": "লক্ষ্যের পরিমাণ (৳)",
  "plan.months": "কয় মাস",
  "plan.submit": "পরিকল্পনা হিসাব করুন",
  "plan.calculating": "পরিকল্পনা হিসাব করা হচ্ছে…",
  "plan.feasible": "পরিকল্পনা বাস্তবসম্মত",
  "plan.infeasible": "বর্তমান মাসিক উদ্বৃত্তের চেয়ে লক্ষ্য বেশি",
  "plan.requiredMonthly": "প্রতি মাসে সঞ্চয় দরকার",
  "plan.feasibleMonthly": "মাসে সর্বোচ্চ সঞ্চয় সম্ভব",
  "plan.surplus": "পূর্বাভাসকৃত মাসিক উদ্বৃত্ত",
  "plan.buffer": "সেফটি বাফার",
  "plan.arithmetic": "হিসাবের বিশদ ক্রম",
  "plan.tradeOffs": "বিকল্প সমাধানসমূহ",
  "plan.pressureWarning":
    "এই সময়ের মধ্যে মাস-শেষের টানাটানির দিন রয়েছে। সেফটি বাফার অক্ষত রাখুন।",
  "plan.action.reduce": "লক্ষ্য কমান",
  "plan.action.delay": "সময় বাড়ান",
  "plan.action.switch": "ফি পরিবর্তনের কৌশল",
  "plan.action.do_nothing": "কিছুই করব না",
  "plan.reviewForecastPrompt": "১৪ দিনের ক্যাশ প্রবাহ পরীক্ষা করতে চান?",

  "spending.headerTag": "খরচ ও ফি বিশ্লেষণ",
  "spending.title": "খরচ ও সাশ্রয় সহযোগী",
  "spending.subtitle": "দোকান ও ব্যক্তিগত ব্যয়ের ধরণ বিশ্লেষণ এবং সম্ভাব্য ফি সাশ্রয়।",
  "spending.loading": "ব্যয় ও ফি বিশ্লেষণ করা হচ্ছে…",
  "spending.summary": "খতিয়ান সারাংশ",
  "spending.cashOutCount": "ক্যাশ-আউট সংখ্যা",
  "spending.cashOutCountSub": "গত ১ মাসের মোট ক্যাশ-আউটের সংখ্যা",
  "spending.cashOutVolume": "মোট ক্যাশ-আউট",
  "spending.cashOutVolumeSub": "এজেন্ট পয়েন্ট থেকে উত্তোলিত নগদ টাকা",
  "spending.feePaid": "প্রদত্ত ফি",
  "spending.feePaidSub": "ক্যাশ-আউটে কাটা নির্ধারিত ফি (১.৮৫%)",
  "spending.singleRuleTop": "উপরে একক দাগ • নিচে ডবল দাগ (হিসাব সম্পন্ন)",
  "spending.anomalies": "অস্বাভাবিক লেনদেন",
  "spending.anomaliesNone": "এই সময়ে কোনো অস্বাভাবিক লেনদেন পরিলক্ষিত হয়নি।",
  "spending.reason": "চিহ্নিত করার কারণ",
  "spending.action": "প্রস্তাবিত পদক্ষেপ",
  "spending.feeSwitch": "ফি পরিবর্তনের সুযোগ",
  "spending.feeSwitchDesc": "এজেন্ট ক্যাশ-আউটের বদলে অ্যাপ ট্রান্সফার বা সরাসরি মার্চেন্ট পেমেন্ট ব্যবহার করলে বাড়তি ফি বাঁচবে।",
  "spending.potentialSaving": "মাসিক সাশ্রয়",
  "spending.currentFee": "বর্তমান মাসিক ফি",
  "spending.altChannel": "বিকল্প চ্যানেল",
  "spending.altFee": "বিকল্প চ্যানেলে ফি",
  "spending.adoption": "আনুমানিক গ্রহণ",
  "spending.perMonth": "/মাস",
  "spending.times": "বার",
  "spending.daysUnit": "দিন",
  "spending.warningStripTitle": "সতর্কবার্তা নির্দেশক",
  "spending.warningStripText": "২৮–৩১ তারিখ ব্যয়ের সম্ভাব্য চাপের সময়।",

  "voice.label": "হিসাবের লক্ষ্য বা অনুসন্ধান লিখুন",
  "voice.speak": "বলুন",
  "voice.listening": "শোনা হচ্ছে…",
  "voice.unsupported": "এই ব্রাউজারে ভয়েস সমর্থিত নয়। দয়া করে লিখুন।",
  "voice.denied": "মাইক্রোফোন বন্ধ আছে। ব্রাউজারের ঠিকানা বারে মাইকের অনুমতি দিন, তারপর আবার চেষ্টা করুন।",
  "voice.nomic": "কোনো মাইক্রোফোন পাওয়া যায়নি। ডিভাইসের মাইক পরীক্ষা করে আবার চেষ্টা করুন।",
  "voice.offline": "ভয়েসের জন্য ইন্টারনেট লাগে। সংযোগ ফিরিয়ে এনে আবার চেষ্টা করুন।",
  "voice.nospeech": "কিছু শোনা যায়নি। মাইকের কাছে থেকে বলুন এবং আবার চেষ্টা করুন।",
  "voice.heard": "আমি শুনেছি:",
  "voice.confirm": "হিসাব করুন",
  "voice.retry": "আবার বলুন",
  "voice.needBoth": "টাকার পরিমাণ ও মাস দুটোই দিন, তারপর হিসাব করুন।",
  "voice.placeholder": "যেমন: ৬ মাসে ৳৩০,০০০ জমাতে চাই",
  "voice.suggestedTitle": "প্রস্তাবিত জিজ্ঞাসা:",

  "tips.headerTag": "ব্যক্তিগত কোচিং",
  "tips.title": "আপনার জন্য পরামর্শ",
  "tips.subtitle": "আপনার ক্যাশ-আউট ও ব্যয়ের আচরণের ওপর ভিত্তি করে বাস্তব পরামর্শ।",
  "tips.loading": "পরামর্শ লোড হচ্ছে…",
  "tips.whyThisTip": "কেন এই পরামর্শ?",
  "tips.suggestedAction": "প্রস্তাবিত পদক্ষেপ",
  "tips.none": "এই মুহূর্তে কোনো বাড়তি পরামর্শ নেই। আপনার ব্যয়ের ধরণ নিয়মিত।",
  "tips.coachAdvice": "সহায়কের পরামর্শ",
  "tips.coreGuidance": "খতিয়ান-ভিত্তিক মূল পরামর্শসমূহ",
  "tips.unavailable": "লাইভ তথ্য এখন পাওয়া যাচ্ছে না — অনুমানের বদলে কিছুই দেখানো হচ্ছে না। API চালু করে আবার চেষ্টা করুন।",
  "tips.stampRule": "নিয়ম-ভিত্তিক",
  "tips.stampForecast": "পূর্বাভাস",
  "tips.stampPlan": "পরিকল্পনা",

  "signal.headerTag": "ধারাবাহিকতা সূচক",
  "signal.title": "আর্থিক ধারাবাহিকতা সংকেত",
  "signal.subtitle": "সময়ের সাথে সাথে লেনদেনের স্থিতিশীলতা পরিমাপের খতিয়ান ব্যান্ড।",
  "signal.loading": "ধারাবাহিকতা যাচাই করা হচ্ছে…",
  "signal.band": "বর্তমান ব্যান্ড",
  "signal.factors": "শীর্ষ প্রভাবক কারণ",
  "signal.improvements": "উন্নতির ক্ষেত্র",
  "signal.improves": "উন্নতি করে",
  "signal.weakens": "দুর্বল করে",
  "signal.comingSoon": "পরবর্তী মডেল ট্রেনিং সাইকেলের পর ধারাবাহিকতা ব্যান্ড সক্রিয় হবে।",
  "signal.educationalBadge": "শিক্ষামূলক",
  "signal.educationalNote": "এটি কেবল শিক্ষামূলক পরিমাপ, ঋণ প্রদানের কোনো সিদ্ধান্ত নয়।",
  "signal.guaranteeTitle": "খতিয়ান নিশ্চয়তা",
  "signal.bandSteady": "Steady (স্থিতিশীল)",
  "signal.bandBuilding": "Building (গড়ে তোলা হচ্ছে)",
  "signal.bandStrong": "Strong (মজবুত)",
  "signal.unavailable": "লাইভ সংকেত এখন পাওয়া যাচ্ছে না — অনুমানের বদলে কোনো ব্যান্ড দেখানো হচ্ছে না। API চালু করে আবার চেষ্টা করুন।",
  "signal.bandRating": "মাঝারি-উচ্চ ধারাবাহিকতা",
  "signal.step1": "১. Building",
  "signal.step2": "২. Steady ●",
  "signal.step3": "৩. Strong",

  "metrics.headerTag": "স্বচ্ছতা ও মডেল মূল্যায়ন",
  "metrics.title": "মডেল মেট্রিক্স ও ন্যায্যতা",
  "metrics.subtitle": "সাধারণ বেসলাইন নিয়মের বিপরীতে মডেলের বাস্তব পারফরম্যান্স ও সমতা যাচাই।",
  "metrics.loading": "মেট্রিক্স লোড হচ্ছে…",
  "metrics.forecast": "ক্যাশ-ফ্লো ফোরকাস্ট (LightGBM)",
  "metrics.model": "মডেল",
  "metrics.baseline": "বেসলাইন",
  "metrics.mae": "MAE",
  "metrics.rmse": "RMSE",
  "metrics.improvement": "উন্নতি",
  "metrics.anomaly": "অস্বাভাবিকতা শনাক্তকরণ (Isolation Forest)",
  "metrics.anomalyDesc": "ব্যবহারকারীর নিজস্ব ঐতিহাসিক ব্যয়ের গড়ের চেয়ে ৪ গুণ বেশি ক্যাশ-আউট বা অস্বাভাবিক সময়ের লেনদেন নির্ভুলভাবে শনাক্তকরণ।",
  "metrics.signal": "ধারাবাহিকতা মডেল (Logistic Regression)",
  "metrics.fairness": "বিভিন্ন গ্রুপের মধ্যে ন্যায্যতা",
  "metrics.fairnessDesc": "মডেলটি ঢাকা, চট্টগ্রাম সহ বিভিন্ন জেলার ৫টি পেশা-গ্রুপে (দৈনিক মজুর, দোকানদার, চাকরিজীবী, গিগ রাইডার ও শিক্ষার্থী) কোনো ভৌগোলিক বা পেশাগত পক্ষপাত ছাড়াই সমান পারফরম্যান্স প্রদর্শন করে।",
  "metrics.demoAudit": "ডেমো নিরীক্ষা",
  "metrics.comingSoon": "মূল্যায়ন কোড সম্পন্ন হলে ন্যায্যতা রিপোর্ট দৃশ্যমান হবে।",
  "metrics.fairnessTable": "গ্রুপভিত্তিক ন্যায্যতা নিরীক্ষা খতিয়ান",
  "metrics.dimension": "মাত্রা",
  "metrics.group": "গ্রুপ",
  "metrics.metric": "মেট্রিক",
  "metrics.value": "পরিমাপকৃত মান",
  "metrics.gap": "আপেক্ষিক ব্যবধান",
  "metrics.impactTitle": "বাস্তবায়িত প্রভাব (সিমুলেশন)",
  "metrics.precision": "Precision (নিখুঁততা)",
  "metrics.recall": "Recall (শনাক্তকরণ হার)",
  "metrics.f1": "F1 স্কোর",
  "metrics.auc": "ROC-AUC",
  "metrics.inflow": "আয় (১৪ দিন)",
  "metrics.outflow": "ব্যয় (১৪ দিন)",
  "metrics.net": "উদ্বৃত্ত (১৪ দিন)",
  "metrics.notesTitle": "নিরীক্ষা নোট ও পদ্ধতি",
  "forecast.driversTitle": "পূর্বাভাস নির্ধারণকারী প্রধান কারণ (SHAP Drivers)",
  "forecast.increasesOutflow": "পূর্বাভাসকৃত ব্যয় বাড়ায়",
  "forecast.decreasesOutflow": "পূর্বাভাসকৃত ব্যয় কমায়",

  "footer.ledgerSystem": "সঞ্চয় Copilot • খতিয়ান ও হিসাবের খাতা সিস্টেম",
  "footer.demoDisclaimer": "ডেমো ডেটা — সব তথ্য কাল্পনিক।",

  "error.title": "কিছু একটা সমস্যা হয়েছে",
  "error.retry": "আবার চেষ্টা করুন",
};

const dictionaries: Record<Lang, Dictionary> = { en, bn };

export type { TranslationKey };

export function t(lang: Lang, key: TranslationKey): string {
  return dictionaries[lang]?.[key] ?? en[key] ?? key;
}

const BN_DIGITS = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"];

/** 12345.6 -> "12,345" in English, "১২,৩৪৫" in Bangla (tabular Latin-style grouping). */
export function formatInteger(value: number | null | undefined, lang: Lang): string {
  if (value === null || value === undefined || isNaN(value)) return "—";
  const grouped = Math.round(value).toLocaleString("en-US");
  if (lang === "en") return grouped;
  return grouped.replace(/[0-9]/g, (digit) => BN_DIGITS[Number(digit)]);
}

/** Money is always shown with ৳ ("৳৩,৬২৮" / "৳3,628"). */
export function formatBDT(value: number | null | undefined, lang: Lang): string {
  if (value === null || value === undefined || isNaN(value)) return "—";
  return `৳${formatInteger(value, lang)}`;
}

/** Converts numbers inside strings to Bangla numerals if lang === 'bn'. */
export function formatDigits(text: string, lang: Lang): string {
  if (!text) return "";
  if (lang === "en") return text;
  return text.replace(/[0-9]/g, (digit) => BN_DIGITS[Number(digit)]);
}
