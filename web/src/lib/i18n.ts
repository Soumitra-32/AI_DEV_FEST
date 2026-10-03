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
  { code: "en", label: "English" },
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

  "stamp.computed": "Calculated",
  "stamp.easyExplain": "In plain words",
  "stamp.verified": "✓ Checked",

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

  "common.prediction": "What we think will happen",
  "common.assumption": "What we're assuming",
  "common.explanation": "Why we're saying this",
  "common.calculationTrace": "Calculation Trace",
  "common.howCalculated": "How we calculated this",
  "common.source": "Source",
  "common.doNothing": "What happens if I do nothing?",
  "common.doNothingCost": "Doing nothing costs about",
  "common.doNothingConfirm": "Okay, I understand",
  "common.doNothingDismiss": "I'll decide later",
  "common.doNothingChosen": "Noted — nothing was changed.",
  "common.doNothingHint":
    "Every suggestion is yours to take or leave. Nothing happens without you.",
  "common.doNothingOutcome":
    "If you save nothing for 6 months, you will have ৳0 saved.",
  "common.doNothingOutcomeN":
    "If you save nothing for {months} months, you will have ৳0 saved.",
  "common.doNothingOutcome1":
    "If you save nothing for 1 month, you will have ৳0 saved.",
  "common.doNothingDisclaimer":
    "No pressure, no penalty. The app never moves your money.",

  "banner.title": "Please note",
  "banner.notADecision":
    "This is only information, not a decision about you.",
  "banner.notADecision.home":
    "This is only information. No money moves without you.",
  "banner.notADecision.forecast":
    "This is a guess about the future, not a promise.",
  "banner.notADecision.plan":
    "This is a plan, not a guarantee you'll reach it.",
  "banner.notADecision.spending":
    "This is only a summary of your spending. Nothing was changed.",
  "banner.notADecision.tips":
    "This is general information, not advice for your case.",
  "banner.notADecision.signal":
    "This is not a loan decision. Only a lender can decide.",
  "banner.notADecision.metrics":
    "These numbers show how the app is doing. They promise nothing.",

  "assumption.forecast":
    "Assumes the past 60 days of inflow/outflow transaction patterns and baseline living expenses continue.",
  "assumption.plan":
    "Assumes monthly safety buffer remains intact and no major unplanned emergency expenses occur.",
  "assumption.spending":
    "Assumes cash withdrawal habits remain constant and Bangla QR merchant payment channels are accessible.",
  "assumption.tips":
    "Assumes past spending patterns and rules-based financial coaching heuristics apply.",

  "home.next.title": "Available Modules",
  "home.next.body":
    "The 14-day cash-flow forecast, savings plan solver, and spending companion are live. Explore below.",
  "home.startSavings": "Start Savings Plan",
  "home.viewDetails": "View Detailed Breakdown",
  "home.reformChangelog":
    "Policy update · 1 Oct 2026: Bangladesh Bank abolished the 1% minimum MDR on Bangla QR. 0% user fee applies to merchant purchases.",
  "home.reformChangelogTag": "1 OCT 2026 DIRECTIVE",

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
  "spending.doNothingOutcome": "Without switching, about {fee} a month keeps going to cash-out fees. That is entirely your decision.",
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
  "spending.banglaQrTitle": "Bangla QR Reform (1 Oct 2026 Directive)",
  "spending.banglaQrDesc": "Under Bangladesh Bank's 1 Oct 2026 reform, merchant Bangla QR payments carry 0% user fee with instant settlement, zero interchange (IRF), and a 0.20% central-bank issuing subsidy for upay on transactions up to ৳2,000.",
  "spending.banglaQrEligible": "{count} small cash-outs (total {volume}) qualify for 0% merchant Bangla QR payment.",
  "spending.banglaQrCustomerBenefit": "0% fee on merchant purchases instead of 1.4% cash-out fee",
  "spending.banglaQrUpayBenefit": "upay earns 0.20% central bank incentive (up to ৳2,000 via NPSB) + float retention",
  "spending.banglaQrAntiMisuseTitle": "Payment & Settlement Systems Act, 2024 Notice",
  "spending.banglaQrAntiMisuseText": "Bangla QR is strictly for genuine purchases. Artificial transaction splitting near ৳2,000 or disguised cash-out through merchants is prohibited and subject to regulatory penalties.",

  "voice.label": "Write your money goal",
  "voice.speak": "Speak",
  "voice.listening": "Listening…",
  "voice.unsupported": "Voice does not work on this phone. Please type instead.",
  "voice.denied": "Please allow the mic, then try again.",
  "voice.nomic": "No mic found. Please type instead.",
  "voice.offline": "Voice needs internet. Please connect and try again.",
  "voice.nospeech": "We could not hear you. Please come closer and speak again.",
  "voice.heard": "I heard:",
  "voice.confirm": "Calculate",
  "voice.retry": "Speak again",
  "voice.needBoth": "Enter both the amount and the months, then calculate.",
  "voice.placeholder": "For example: I want to save ৳30,000 in 6 months",
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
  "signal.bandRatingBuilding": "Low Consistency",
  "signal.bandRatingStrong": "High Consistency",
  "signal.step1": "1. Building",
  "signal.step2": "2. Steady",
  "signal.step3": "3. Strong",
  "signal.logisticRegression": "Logistic Regression",

  "metrics.headerTag": "Transparency & Evaluation",
  "metrics.title": "Evidence, Metrics & Fairness",
  "metrics.subtitle": "Transparent model evaluation against simple baseline heuristics.",
  "metrics.loading": "Loading evaluation metrics…",
  "metrics.forecast": "Smart Cash-Flow Forecast",
  "metrics.forecastBadge": "14-Day Forecast",
  "metrics.model": "Model",
  "metrics.baseline": "Baseline",
  "metrics.mae": "MAE",
  "metrics.rmse": "RMSE",
  "metrics.improvement": "Improvement",
  "metrics.anomaly": "Anomaly Detection",
  "metrics.anomalyBadge": "Auto Detection",
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
  "metrics.macroContext":
    "Macro market context: Since 1 July, Bangla QR transaction count grew 3.5× and value surged 5× to ৳143.54 crore daily (Source: Bangladesh Bank September 2026 Report).",
  "metrics.institutionalCaveat":
    "Institutional caveat: The 0.20% central-bank incentive applies strictly to transactions up to ৳2,000 routed via NPSB. Transactions above this cap follow standard commercial terms.",
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

  "stamp.computed": "স্বয়ংক্রিয় হিসাব",
  "stamp.easyExplain": "সহজ ভাষায়",
  "stamp.verified": "✓ যাচাই করা",

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

  "common.prediction": "আমরা যা আন্দাজ করছি",
  "common.assumption": "কী ধরে নিচ্ছি",
  "common.explanation": "কেন এমন বলছি",
  "common.calculationTrace": "হিসাবের বিবরণ",
  "common.howCalculated": "এই হিসাবটি যেভাবে করা হয়েছে",
  "common.source": "উৎস",
  "common.doNothing": "কিছু না করলে কী হবে?",
  "common.doNothingCost": "কিছু না করলে খরচ হবে প্রায়",
  "common.doNothingConfirm": "ঠিক আছে, বুঝেছি",
  "common.doNothingDismiss": "পরে দেখব",
  "common.doNothingChosen": "ঠিক আছে — কিছুই বদলানো হয়নি।",
  "common.doNothingHint":
    "প্রতিটি পরামর্শ মানা বা না-মানা আপনার হাতে। আপনি না বললে কিছুই হবে না।",
  "common.doNothingOutcome":
    "৬ মাস কিছু না জমালে, জমানো থাকবে ৳০।",
  "common.doNothingOutcomeN":
    "{months} মাস কিছু না জমালে, জমানো থাকবে ৳০।",
  "common.doNothingOutcome1":
    "১ মাস কিছু না জমালে, জমানো থাকবে ৳০।",
  "common.doNothingDisclaimer":
    "কোনো চাপ নেই, জরিমানা নেই। অ্যাপ কখনো আপনার টাকা নাড়বে না।",

  "banner.title": "মনে রাখুন",
  "banner.notADecision":
    "এটি শুধু তথ্য — আপনার বিষয়ে কোনো সিদ্ধান্ত নয়।",
  "banner.notADecision.home":
    "এটি শুধু তথ্য। আপনি না বললে কোনো টাকা নড়বে না।",
  "banner.notADecision.forecast":
    "এটি ভবিষ্যতের আন্দাজ, প্রতিশ্রুতি নয়।",
  "banner.notADecision.plan":
    "এটি একটি পরিকল্পনা — লক্ষ্যে পৌঁছানোর নিশ্চয়তা নয়।",
  "banner.notADecision.spending":
    "এটি শুধু আপনার খরচের হিসাব। কিছু বদলানো হয়নি।",
  "banner.notADecision.tips":
    "এটি সাধারণ তথ্য — আপনার জন্য ব্যক্তিগত পরামর্শ নয়।",
  "banner.notADecision.signal":
    "এটি ঋণের সিদ্ধান্ত নয়। ঋণ দেবে কি না, তা শুধু ঋণদাতা ঠিক করতে পারে।",
  "banner.notADecision.metrics":
    "এই সংখ্যাগুলো অ্যাপ কেমন করছে তা দেখায়। এগুলো কোনো প্রতিশ্রুতি নয়।",

  "assumption.forecast":
    "ধরে নেওয়া হয়েছে বিগত ৬০ দিনের লেনদেনের ধারা বজায় থাকবে এবং নিয়মিত খরচ অপরিবর্তিত থাকবে।",
  "assumption.plan":
    "ধরে নেওয়া হয়েছে মাসিক বাফার অপরিবর্তিত থাকবে এবং নতুন কোনো বড় অপ্রত্যাশিত খরচ আসবে না।",
  "assumption.spending":
    "ধরে নেওয়া হয়েছে নগদ তোলার ধরণ অপরিবর্তিত থাকবে এবং কিউআর গ্রহণকারী মার্চেন্ট সেবা চালু থাকবে।",
  "assumption.tips":
    "ধরে নেওয়া হয়েছে বিগত মাসের ক্যাশ খরচ ও সঞ্চয় পরিকল্পনার নিয়মাবলী প্রযোজ্য।",

  "home.next.title": "সক্রিয় খতিয়ান মডিউল",
  "home.next.body":
    "১৪ দিনের ক্যাশ-ফ্লো পূর্বাভাস, সঞ্চয় পরিকল্পনাকারী এবং খরচ সহযোগী প্রস্তুত। বিস্তারিত জানতে নিচে দেখুন।",
  "home.startSavings": "সঞ্চয় শুরু করুন",
  "home.viewDetails": "বিস্তারিত হিসাব দেখুন",
  "home.reformChangelog":
    "নীতি আপডেট · ১ অক্টোবর ২০২৬: বাংলাদেশ ব্যাংক বাংলা কিউআর লেনদেনে ন্যূনতম ১% এমডিআর বাতিল করেছে। দোকানে কেনাকাটায় ০% ফি প্রযোজ্য।",
  "home.reformChangelogTag": "১ অক্টোবর ২০২৬ নির্দেশনা",

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
  "plan.feasible": "পরিকল্পনা সম্ভব ও বাস্তবসম্মত",
  "plan.infeasible": "বর্তমান আয়ের উদ্বৃত্তের চেয়ে জমার লক্ষ্য বেশি",
  "plan.requiredMonthly": "প্রতি মাসে সঞ্চয় দরকার",
  "plan.feasibleMonthly": "মাসে সর্বোচ্চ সঞ্চয় সম্ভব",
  "plan.surplus": "মাসে জমার মতো উদ্বৃত্ত টাকা",
  "plan.buffer": "জরুরি খরচের বাফার",
  "plan.arithmetic": "হিসাবের বিবরণ",
  "plan.tradeOffs": "হিসাব মেলানোর বিকল্প উপায়",
  "plan.pressureWarning":
    "এই সময়ের মধ্যে মাস-শেষের টানাটানির দিন রয়েছে। সেফটি বাফার অক্ষত রাখুন।",
  "plan.action.reduce": "লক্ষ্যের টাকা কমান",
  "plan.action.delay": "কয়েক মাস সময় বাড়ান",
  "plan.action.switch": "ফি বাঁচানোর উপায়",
  "plan.action.do_nothing": "কোনো পরিবর্তন করব না",
  "plan.reviewForecastPrompt": "১৪ দিনের ক্যাশ প্রবাহ পরীক্ষা করতে চান?",

  "spending.headerTag": "খরচ ও ফি বিশ্লেষণ",
  "spending.title": "খরচ ও সাশ্রয় সহযোগী",
  "spending.subtitle": "আপনার ব্যয়ের ধরণ বিশ্লেষণ এবং সম্ভাব্য ফি সাশ্রয়।",
  "spending.loading": "ব্যয় ও ফি বিশ্লেষণ করা হচ্ছে…",
  "spending.summary": "লেনদেনের হিসাব খতিয়ান",
  "spending.cashOutCount": "ক্যাশ-আউট সংখ্যা",
  "spending.cashOutCountSub": "গত ৩০ দিনে মোট কতবার ক্যাশ-আউট করেছেন",
  "spending.cashOutVolume": "ক্যাশ-আউট করা মোট টাকা",
  "spending.cashOutVolumeSub": "দোকান বা এজেন্ট থেকে তোলা নগদ টাকা",
  "spending.feePaid": "প্রদত্ত ফি",
  "spending.feePaidSub": "ক্যাশ-আউটে কাটা ফি",
  "spending.singleRuleTop": "উপরে একক দাগ • নিচে ডবল দাগ (হিসাব সম্পন্ন)",
  "spending.anomalies": "অস্বাভাবিক লেনদেন",
  "spending.anomaliesNone": "এই সময়ে কোনো অস্বাভাবিক লেনদেন পরিলক্ষিত হয়নি।",
  "spending.reason": "চিহ্নিত করার কারণ",
  "spending.action": "প্রস্তাবিত পদক্ষেপ",
  "spending.feeSwitch": "ফি বাঁচানোর উপায়",
  "spending.feeSwitchDesc": "এজেন্টের কাছে ক্যাশ-আউট না করে দোকানে সরাসরি বাংলা কিউআরে পেমেন্ট বা অ্যাপে পাঠালে ক্যাশ-আউট ফি বাঁচবে।",
  "spending.doNothingOutcome": "বদল না করলে প্রতি মাসে প্রায় {fee} ক্যাশ-আউট ফিতে চলে যাবে। এটাও আপনার নিজস্ব সিদ্ধান্ত।",
  "spending.potentialSaving": "মাসে বাঁচবে",
  "spending.currentFee": "বর্তমানে মাসে দেওয়া ফি",
  "spending.altChannel": "বিকল্প মাধ্যম",
  "spending.altFee": "নতুন মাধ্যমে ফি",
  "spending.adoption": "ধরে নেওয়া ব্যবহার",
  "spending.perMonth": "/মাস",
  "spending.times": "বার",
  "spending.daysUnit": "দিন",
  "spending.warningStripTitle": "সতর্কবার্তা নির্দেশক",
  "spending.warningStripText": "২৮–৩১ তারিখ ব্যয়ের সম্ভাব্য চাপের সময়।",
  "spending.banglaQrTitle": "বাংলা কিউআর সংস্কার (১ অক্টোবর ২০২৬ নির্দেশনা)",
  "spending.banglaQrDesc": "বাংলাদেশ ব্যাংকের ১ অক্টোবর ২০২৬ নির্দেশনা অনুযায়ী, মার্চেন্ট বাংলা কিউআর পেমেন্টে ০% গ্রাহক ফি, তাৎক্ষণিক সেটেলমেন্ট, শূন্য ইন্টারচেঞ্জ ফি (IRF), এবং ২,০০০ টাকা পর্যন্ত লেনদেনে উপায়-এর (upay) জন্য ০.২০% কেন্দ্রীয় ব্যাংক প্রণোদনা রয়েছে।",
  "spending.banglaQrEligible": "আপনার {count}টি ছোট ক্যাশ-আউট (মোট {volume}) ২,০০০ টাকার মধ্যে, যা দোকানে বাংলা কিউআরে দিলে সম্পূর্ণ ০% ফি।",
  "spending.banglaQrCustomerBenefit": "ক্যাশ-আউটে ১.৪% ফির বদলে দোকানে বাংলা কিউআরে সরাসরি ০% ফি",
  "spending.banglaQrUpayBenefit": "উপায় (upay) বাংলাদেশ ব্যাংক থেকে ০.২০% ইস্যুয়ার প্রণোদনা (NPSB মাধ্যমে ২,০০০ টাকা পর্যন্ত) ও ব্যালেন্স ধরে রাখার সুবিধা পায়",
  "spending.banglaQrAntiMisuseTitle": "পেমেন্ট অ্যান্ড সেটেলমেন্ট সিস্টেমস আইন, ২০২৪ সতর্কতা",
  "spending.banglaQrAntiMisuseText": "বাংলা কিউআর শুধুমাত্র প্রকৃত কেনাকাটার জন্য। ২,০০০ টাকার প্রণোদনা অপব্যবহার করতে কৃত্রিমভাবে লেনদেন ভাঙা বা মার্চেন্টের মাধ্যমে নগদ ক্যাশ-আউট আইনত দণ্ডনীয়।",

  "voice.label": "আপনার টাকার লক্ষ্য লিখুন",
  "voice.speak": "বলুন",
  "voice.listening": "শোনা হচ্ছে…",
  "voice.unsupported": "এই ফোনে কথা বলে লেখা যায় না। দয়া করে টাইপ করুন।",
  "voice.denied": "মাইকের অনুমতি দিন, তারপর আবার চেষ্টা করুন।",
  "voice.nomic": "মাইক পাওয়া যায়নি। দয়া করে টাইপ করুন।",
  "voice.offline": "কথা বলে লিখতে ইন্টারনেট লাগে। সংযোগ দিয়ে আবার চেষ্টা করুন।",
  "voice.nospeech": "শোনা যায়নি। কাছে এসে আবার বলুন।",
  "voice.heard": "আমি শুনেছি:",
  "voice.confirm": "হিসাব করুন",
  "voice.retry": "আবার বলুন",
  "voice.needBoth": "টাকার পরিমাণ ও মাস দুটোই দিন, তারপর হিসাব করুন।",
  "voice.placeholder": "যেমন: ৬ মাসে ৳৩০,০০০ জমাতে চাই",
  "voice.suggestedTitle": "প্রস্তাবিত জিজ্ঞাসা:",

  "tips.headerTag": "ব্যক্তিগত পরামর্শ",
  "tips.title": "খরচ ও জমার পরামর্শ",
  "tips.subtitle": "আপনার ক্যাশ-আউট ও ব্যয়ের আচরণের ওপর ভিত্তি করে বাস্তব পরামর্শ।",
  "tips.loading": "পরামর্শ লোড হচ্ছে…",
  "tips.whyThisTip": "কেন এই পরামর্শ?",
  "tips.suggestedAction": "প্রস্তাবিত পদক্ষেপ",
  "tips.none": "এই মুহূর্তে কোনো বাড়তি পরামর্শ নেই। আপনার ব্যয়ের ধরণ নিয়মিত।",
  "tips.coachAdvice": "খতিয়ানের পরামর্শ",
  "tips.coreGuidance": "মূল পরামর্শ ও হিসাব",
  "tips.unavailable": "লাইভ তথ্য এখন পাওয়া যাচ্ছে না — অনুমানের বদলে কিছুই দেখানো হচ্ছে না। API চালু করে আবার চেষ্টা করুন।",
  "tips.stampRule": "নিয়ম-ভিত্তিক",
  "tips.stampForecast": "পূর্বাভাস",
  "tips.stampPlan": "পরিকল্পনা",

  "signal.headerTag": "ধারাবাহিকতা সূচক",
  "signal.title": "লেনদেনের ধারাবাহিকতা খতিয়ান",
  "signal.subtitle": "নিয়মিত লেনদেনের ভিত্তিতে আপনার ব্যালেন্স ও খরচের স্থিতিশীলতার হিসাব।",
  "signal.loading": "ধারাবাহিকতা যাচাই করা হচ্ছে…",
  "signal.band": "বর্তমান ব্যান্ড",
  "signal.factors": "যে কারণে এই মূল্যায়ন",
  "signal.improvements": "উন্নতি করার সহজ উপায়",
  "signal.improves": "উন্নতি করে",
  "signal.weakens": "দুর্বল করে",
  "signal.comingSoon": "পরবর্তী মডেল ট্রেনিং সাইকেলের পর ধারাবাহিকতা ব্যান্ড সক্রিয় হবে।",
  "signal.educationalBadge": "শিক্ষামূলক",
  "signal.educationalNote": "এটি কেবল শিক্ষামূলক পরিমাপ, ঋণ প্রদানের কোনো সিদ্ধান্ত নয়।",
  "signal.guaranteeTitle": "খতিয়ান নিশ্চয়তা",
  "signal.bandSteady": "স্থিতিশীল",
  "signal.bandBuilding": "চলমান",
  "signal.bandStrong": "দৃঢ়",
  "signal.unavailable": "লাইভ সংকেত এখন পাওয়া যাচ্ছে না — অনুমানের বদলে কোনো ব্যান্ড দেখানো হচ্ছে না। API চালু করে আবার চেষ্টা করুন।",
  "signal.bandRating": "মাঝারি-উচ্চ ধারাবাহিকতা",
  "signal.bandRatingBuilding": "চলমান ধারাবাহিকতা",
  "signal.bandRatingStrong": "উচ্চ ধারাবাহিকতা",
  "signal.step1": "১. চলমান",
  "signal.step2": "২. স্থিতিশীল",
  "signal.step3": "৩. দৃঢ়",
  "signal.logisticRegression": "লজিস্টিক রিগ্রেশন",

  "metrics.headerTag": "স্বচ্ছতা ও মূল্যায়ন",
  "metrics.title": "মডেল মেট্রিক্স ও ন্যায্যতা",
  "metrics.subtitle": "সাধারণ বেসলাইন নিয়মের বিপরীতে মডেলের বাস্তব পারফরম্যান্স ও সমতা যাচাই।",
  "metrics.loading": "মেট্রিক্স লোড হচ্ছে…",
  "metrics.forecast": "স্মার্ট ক্যাশ-ফ্লো পূর্বাভাস",
  "metrics.forecastBadge": "১৪ দিনের পূর্বাভাস",
  "metrics.model": "মডেল",
  "metrics.baseline": "বেসলাইন",
  "metrics.mae": "MAE",
  "metrics.rmse": "RMSE",
  "metrics.improvement": "উন্নতি",
  "metrics.anomaly": "অস্বাভাবিক লেনদেন শনাক্তকরণ",
  "metrics.anomalyBadge": "স্বয়ংক্রিয় শনাক্তকরণ",
  "metrics.anomalyDesc": "ব্যবহারকারীর নিজস্ব ঐতিহাসিক ব্যয়ের গড়ের চেয়ে ৪ গুণ বেশি ক্যাশ-আউট বা অস্বাভাবিক সময়ের লেনদেন নির্ভুলভাবে শনাক্তকরণ।",
  "metrics.signal": "ধারাবাহিকতা মডেল (লজিস্টিক রিগ্রেশন)",
  "metrics.fairness": "সবার জন্য নিরপেক্ষতা",
  "metrics.fairnessDesc": "মডেলটি ঢাকা, চট্টগ্রাম সহ বিভিন্ন জেলার ৫টি পেশা-গ্রুপে (দৈনিক মজুর, দোকানদার, চাকরিজীবী, গিগ রাইডার ও শিক্ষার্থী) কোনো ভৌগোলিক বা পেশাগত পক্ষপাত ছাড়াই সমান পারফরম্যান্স প্রদর্শন করে।",
  "metrics.demoAudit": "ডেমো নিরীক্ষা",
  "metrics.comingSoon": "মূল্যায়ন কোড সম্পন্ন হলে ন্যায্যতা রিপোর্ট দৃশ্যমান হবে।",
  "metrics.fairnessTable": "পেশা ও জেলাভিত্তিক নিরপেক্ষতার খতিয়ান",
  "metrics.dimension": "মাত্রা",
  "metrics.group": "গ্রুপ",
  "metrics.metric": "মেট্রিক",
  "metrics.value": "পরিমাপকৃত মান",
  "metrics.gap": "আপেক্ষিক ব্যবধান",
  "metrics.impactTitle": "বাস্তবায়িত প্রভাব (সিমুলেশন)",
  "metrics.precision": "নিখুঁততা",
  "metrics.recall": "শনাক্তকরণ হার",
  "metrics.f1": "F1 স্কোর",
  "metrics.auc": "ROC-AUC",
  "metrics.inflow": "আয় (১৪ দিন)",
  "metrics.outflow": "ব্যয় (১৪ দিন)",
  "metrics.net": "উদ্বৃত্ত (১৪ দিন)",
  "metrics.macroContext":
    "বাজারের প্রেক্ষাপট: ১ জুলাই থেকে বাংলা কিউআর লেনদেন সংখ্যা ৩.৫ গুণ এবং মূল্য ৫ গুণ বৃদ্ধি পেয়ে দৈনিক ৳১৪৩.৫৪ কোটিতে পৌঁছেছে (সূত্র: বাংলাদেশ ব্যাংক সেপ্টেম্বর ২০২৬ প্রতিবেদন)।",
  "metrics.institutionalCaveat":
    "প্রতিষ্ঠানগত বিবেচনা: ০.২০% কেন্দ্রীয় ব্যাংক প্রণোদনা শুধুমাত্র এনপিএসবি (NPSB) নেটওয়ার্কে ২,০০০ টাকা পর্যন্ত লেনদেনে প্রযোজ্য। এর উপরের লেনদেনে সাধারণ বাণিজ্যিক হার কার্যকর।",
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

/** User-facing model name translations (no internal technical identifiers exposed). */
export function formatModelName(name: string | null | undefined, lang: Lang): string {
  if (!name) return "—";
  const lower = name.toLowerCase();
  if (lower.includes("lightgbm")) {
    return lang === "bn" ? "আমাদের মডেল" : "Smart Forecast";
  }
  if (lower.includes("trailing_average") || lower.includes("baseline") || lower.includes("average")) {
    return lang === "bn" ? "সাধারণ গড়" : "Simple Average";
  }
  if (lower.includes("isolation")) {
    return lang === "bn" ? "স্বয়ংক্রিয় শনাক্তকরণ" : "Auto Detection";
  }
  if (lower.includes("logistic")) {
    return lang === "bn" ? "লজিস্টিক রিগ্রেশন" : "Logistic Regression";
  }
  return name;
}

/** Human-friendly feature labels for SHAP drivers, metrics, and triggers. */
export function formatFeatureName(name: string | null | undefined, lang: Lang): string {
  if (!name) return "";
  const lower = name.toLowerCase();
  if (lower.includes("cash_out_count_per_month")) {
    return lang === "bn" ? "মাসে ক্যাশ-আউট সংখ্যা" : "Cash-Outs Per Month";
  }
  if (lower.includes("cash_out_share_of_outflow")) {
    return lang === "bn" ? "ক্যাশ-আউটের অনুপাত" : "Cash-Out Share of Outflow";
  }
  if (lower.includes("cash_out_volume_per_month_bdt")) {
    return lang === "bn" ? "মাসিক ক্যাশ-আউট পরিমাণ" : "Monthly Cash-Out Volume";
  }
  if (lower.includes("trailing_14d_outflow")) {
    return lang === "bn" ? "১৪ দিনের গড় খরচ" : "14-Day Average Outflow";
  }
  if (lower.includes("fee_share_of_income")) {
    return lang === "bn" ? "আয়ের ফিতে ব্যয় অনুপাত" : "Fee Share of Income";
  }
  if (lower.includes("shortfall_days_per_month")) {
    return lang === "bn" ? "মাসে টানাটানির দিন" : "Shortfall Days Per Month";
  }
  if (lower.includes("balance_min_bdt")) {
    return lang === "bn" ? "সর্বনিম্ন ব্যালেন্স" : "Minimum Balance";
  }
  if (lower.includes("weekend_spend_ratio")) {
    return lang === "bn" ? "সপ্তাহ শেষের খরচের অনুপাত" : "Weekend Spend Ratio";
  }
  if (lower.includes("month_end_spend_ratio")) {
    return lang === "bn" ? "মাস শেষের খরচের অনুপাত" : "Month-End Spend Ratio";
  }
  if (lower.includes("income_days_per_month")) {
    return lang === "bn" ? "মাসে আয়ের দিন" : "Income Days Per Month";
  }
  if (lower.includes("income_cv")) {
    return lang === "bn" ? "আয়ের তারতম্য" : "Income Variability";
  }
  if (lower.includes("spend_cv")) {
    return lang === "bn" ? "খরচের তারতম্য" : "Spending Variability";
  }
  return name.replace(/_/g, " ");
}

/**
 * Sanitizes coach bullets and backend triggers so raw variable names
 * like `cash_out_count_per_month >= 3.0 (observed 5.0)` become friendly text.
 */
export function sanitizeBullet(bullet: string, lang: Lang): string {
  if (!bullet) return "";
  let clean = bullet;

  if (clean.includes("cash_out_count_per_month")) {
    const match = clean.match(/cash_out_count_per_month\s*([><!=]+)\s*([\d.]+)\s*\(observed\s*([\d.]+)\)/i);
    if (match) {
      const [, , thresh, obs] = match;
      const tNum = Math.round(Number(thresh));
      const oNum = Math.round(Number(obs));
      const replacement =
        lang === "bn"
          ? `মাসে ক্যাশ-আউট সংখ্যা ${formatDigits(String(oNum), "bn")} বার (সাধারণত ${formatDigits(String(tNum), "bn")} বারের বেশি হলে ফি বাড়ে)`
          : `Cash-out count ~${oNum} times/month (typically above ${tNum})`;
      clean = clean.replace(match[0], replacement);
    } else {
      clean = clean.replace(/cash_out_count_per_month/g, lang === "bn" ? "মাসে ক্যাশ-আউট সংখ্যা" : "cash-out count per month");
    }
  }

  if (clean.includes("cash_out_share_of_outflow")) {
    const match = clean.match(/cash_out_share_of_outflow\s*([><!=]+)\s*([\d.]+)\s*\(observed\s*([\d.]+)\)/i);
    if (match) {
      const [, , thresh, obs] = match;
      const tPct = Math.round(Number(thresh) * 100);
      const oPct = Math.round(Number(obs) * 100);
      const replacement =
        lang === "bn"
          ? `খরচের ${formatDigits(String(oPct), "bn")}% ক্যাশে হয় (সাধারণত ${formatDigits(String(tPct), "bn")}% এর বেশি হলে ফি বাড়ে)`
          : `${oPct}% of spending is in cash (typically above ${tPct}%)`;
      clean = clean.replace(match[0], replacement);
    } else {
      clean = clean.replace(/cash_out_share_of_outflow/g, lang === "bn" ? "ক্যাশ-আউটের অনুপাত" : "cash-out share of outflow");
    }
  }

  if (clean.includes("cash_out_volume_per_month_bdt")) {
    const match = clean.match(/cash_out_volume_per_month_bdt\s*([><!=]+)\s*([\d.]+)\s*\(observed\s*([\d.]+)\)/i);
    if (match) {
      const [, , thresh, obs] = match;
      const tVal = Math.round(Number(thresh));
      const oVal = Math.round(Number(obs));
      const replacement =
        lang === "bn"
          ? `মাসিক ক্যাশ-আউট পরিমাণ ${formatBDT(oVal, "bn")} (${formatBDT(tVal, "bn")} এর বেশি)`
          : `Monthly cash-out volume ~${formatBDT(oVal, "en")} (above ${formatBDT(tVal, "en")})`;
      clean = clean.replace(match[0], replacement);
    } else {
      clean = clean.replace(/cash_out_volume_per_month_bdt/g, lang === "bn" ? "মাসিক ক্যাশ-আউট পরিমাণ" : "monthly cash-out volume");
    }
  }

  if (clean.includes("fee_share_of_income")) {
    clean = clean.replace(/fee_share_of_income/g, lang === "bn" ? "আয়ের ফিতে ব্যয় অনুপাত" : "fee share of income");
  }
  if (clean.includes("shortfall_days_per_month")) {
    clean = clean.replace(/shortfall_days_per_month/g, lang === "bn" ? "মাসে টানাটানির দিন" : "shortfall days per month");
  }
  if (clean.includes("balance_min_bdt")) {
    clean = clean.replace(/balance_min_bdt/g, lang === "bn" ? "সর্বনিম্ন ব্যালেন্স" : "minimum balance");
  }

  clean = clean.replace(/\(trigger:\s*([^)]+)\)/gi, (m, content) => {
    return lang === "bn" ? `(কারণ: ${formatDigits(content, "bn")})` : m;
  });

  if (lang === "bn") {
    clean = formatDigits(clean, "bn");
  }

  return clean;
}

/** Demographic and persona localization. */
export function formatPersona(persona: string | null | undefined, lang: Lang): string {
  if (!persona) return "—";
  if (lang === "en") return persona.replace(/_/g, " ");
  const map: Record<string, string> = {
    shopkeeper: "দোকানদার",
    daily_earner: "দৈনিক মজুর",
    salaried: "চাকরিজীবী",
    gig_rider: "গিগ রাইডার",
    student: "শিক্ষার্থী",
  };
  return map[persona] ?? persona.replace(/_/g, " ");
}

export function formatDistrict(district: string | null | undefined, lang: Lang): string {
  if (!district) return "—";
  if (lang === "en") return district;
  const map: Record<string, string> = {
    Dhaka: "ঢাকা",
    Chattogram: "চট্টগ্রাম",
    Sylhet: "সিলেট",
    Rajshahi: "রাজশাহী",
    Khulna: "খুলনা",
    Barishal: "বরিশাল",
    Rangpur: "রংপুর",
    Mymensingh: "ময়মনসিংহ",
    Cumilla: "কুমিল্লা",
    Bogura: "বগুড়া",
  };
  return map[district] ?? district;
}

export function formatIncomeBand(band: string | null | undefined, lang: Lang): string {
  if (!band) return "—";
  if (lang === "en") return band;
  const map: Record<string, string> = {
    low: "স্বল্প আয়",
    middle: "মধ্যম আয়",
    variable: "অনিয়মিত আয়",
    affluent: "উচ্চ আয়",
  };
  return map[band] ?? formatDigits(band, "bn");
}

export function formatStatusBadge(status: string | null | undefined, lang: Lang): string {
  if (!status) return "";
  if (lang === "en") return status;
  const map: Record<string, string> = {
    Strong: "দৃঢ়",
    Building: "চলমান",
    Steady: "স্থিতিশীল",
    "System Computed": "সিস্টেম গণনা",
    "Rule Verified": "যাচাইকৃত",
    "Plain Language": "সহজ ব্যাখ্যা",
    "Logistic Regression": "লজিস্টিক রিগ্রেশন",
    "Isolation Forest": "স্বয়ংক্রিয় শনাক্তকরণ",
    LightGBM: "আমাদের মডেল",
    Educational: "শিক্ষামূলক",
  };
  return map[status] ?? status;
}

