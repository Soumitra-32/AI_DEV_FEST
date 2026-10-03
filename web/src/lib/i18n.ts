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
  subTitle: "Simple money guidance • Bangla first",
  subTitleBadge: "Simple ledger-book style",
  tagline:
    "A Bangla-first coach that explains your transactions, plans a realistic saving goal, and warns you before the month-end squeeze — without selling you anything.",

  "nav.home": "Home",
  "nav.plan": "Savings",
  "nav.forecast": "Coming days",
  "nav.spending": "Spending",
  "nav.tips": "Tips",
  "nav.signal": "Steady habits",
  "nav.metrics": "Results",
  "nav.more": "More",

  "lang.switchTo": "Switch language",

  "stamp.computed": "Calculated",
  "stamp.easyExplain": "In plain words",
  "stamp.verified": "✓ Checked",

  "status.title": "Account Status",
  "status.checking": "Checking account status…",
  "status.apiReachable": "Connected",
  "status.apiUnreachable": "Not connected",
  "status.apiHint":
    "The app cannot reach the server. Start the server and refresh this page.",
  "status.serviceVersion": "Version",
  "status.database": "Database",
  "status.databaseReady": "Ready",
  "status.databaseMissing": "Not ready",
  "status.users": "Account holders",
  "status.transactions": "Transactions",
  "status.generatedAt": "Calculated on",
  "status.features": "Active features",
  "status.degraded": "Running slowly",

  "identity.title": "Account Holder",
  "identity.persona": "Occupation",
  "identity.district": "District",
  "identity.incomeBand": "Income Band",
  "identity.cohort": "Cohort",
  "identity.demoUser": "Demo Profile",

  "common.prediction": "Prediction",
  "common.assumption": "Assumption",
  "common.explanation": "Reason",
  "common.calculationTrace": "Calculation Trace",
  "common.howCalculated": "Calculation details",
  "common.source": "Source",
  "common.taka": "taka",
  "common.doNothing": "What happens if I do nothing?",
  "common.doNothingCost": "Doing nothing costs about",
  "common.doNothingConfirm": "Okay",
  "common.doNothingDismiss": "Later",
  "common.doNothingChosen": "Noted — no changes were made.",
  "common.doNothingHint":
    "Every suggestion is optional. No changes occur without your confirmation.",
  "common.doNothingOutcome":
    "If you save nothing for 6 months, you will have ৳0 saved.",
  "common.doNothingOutcomeN":
    "If you save nothing for {months} months, you will have ৳0 saved.",
  "common.doNothingOutcome1":
    "If you save nothing for 1 month, you will have ৳0 saved.",
  "common.doNothingDisclaimer":
    "No penalty applies. The app never transfers your funds.",

  "banner.title": "Please note",
  "banner.notADecision":
    "This is information only, not a decision about you.",
  "banner.notADecision.home":
    "This is information only. No funds move without your confirmation.",
  "banner.notADecision.forecast":
    "This is an estimate, not a promise.",
  "banner.notADecision.plan":
    "Here is the plan. Reaching it is not guaranteed.",
  "banner.notADecision.spending":
    "This is a summary of your spending. No changes were made.",
  "banner.notADecision.tips":
    "This is general information. Your case may be different.",
  "banner.notADecision.signal":
    "The bank decides the loan, not us.",
  "banner.notADecision.metrics":
    "These numbers show how the app performs. They promise nothing.",

  "assumption.forecast":
    "Assumes the past 60 days of inflow/outflow transaction patterns and baseline living expenses continue.",
  "assumption.plan":
    "Assumes monthly safety buffer remains intact and no major unplanned emergency expenses occur.",
  "assumption.spending":
    "Assumes cash withdrawal habits remain constant and Bangla QR merchant payment channels are accessible.",
  "assumption.tips":
    "Assumes past spending patterns and rules-based financial coaching heuristics apply.",

  "home.next.title": "Next Steps",
  "home.next.body":
    "Review the 14-day cash flow forecast, create a savings plan, and review spending below.",
  "home.startSavings": "Start Savings Plan",
  "home.viewDetails": "View details",
  "home.reformChangelog":
    "Since 1 October, merchants pay no fee to accept QR payments.",
  "home.reformChangelogTag": "1 October 2026",

  "comingSoon.title": "Coming Soon",
  "comingSoon.phase5": "Spending companion (Phase 5)",
  "comingSoon.phase7": "Tips and consistency signal (Phase 7)",
  "comingSoon.phase8": "Evidence and metrics (Phase 8)",

  "forecast.headerTag": "14-Day Outlook",
  "forecast.title": "14-Day Cash Flow Forecast",
  "forecast.subtitle":
    "Projected inflows, outflows, and net cash balance based on your verified transaction history.",
  "forecast.monthEndPreset": "Show days 28–31",
  "forecast.latestPreset": "Latest 14 days",
  "forecast.netSourceModel": "Our model",
  "forecast.netSourceAnchor": "Historical anchor",
  "forecast.netSourceDifference": "Simple average",
  "forecast.loading": "Calculating 14-day forecast…",
  "forecast.days": "Date",
  "forecast.inflow": "Money in",
  "forecast.outflow": "Money out",
  "forecast.net": "Net",
  "forecast.balance": "Balance",
  "forecast.pressureTitle": "Tight days",
  "forecast.pressureNone": "No tight days in this period — cash balance remains above the required safety buffer.",
  "forecast.pressureBadge": "Tight day",
  "forecast.reasonNegativeNet": "spending exceeds income",
  "forecast.reasonBelowBuffer": "balance falls below the safety buffer",
  "forecast.reasonBoth": "spending exceeds income and balance falls below the safety buffer",
  "forecast.modelAccuracy": "Model accuracy compared to simple average",
  "forecast.noMetrics": "Evaluation metrics will appear here once calculation completes.",
  "forecast.table": "Daily Breakdown",
  "forecast.tableSub": "14-day daily transaction ledger",
  "forecast.planSavingsPrompt": "Would you like to plan savings from this surplus?",

  "plan.headerTag": "Monthly Savings",
  "plan.title": "Your Savings Plan",
  "plan.subtitle":
    "Enter your target amount and timeline. Calculated from your actual monthly surplus, not a simple average.",
  "plan.goal": "Goal (৳)",
  "plan.months": "Months",
  "plan.submit": "Calculate Plan",
  "plan.calculating": "Calculating your savings plan…",
  "plan.feasible": "This plan works",
  "plan.infeasible": "This goal is too high for your current surplus",
  "plan.requiredMonthly": "Required monthly savings",
  "plan.feasibleMonthly": "Achievable monthly savings",
  "plan.surplus": "Monthly cash surplus",
  "plan.buffer": "Safety buffer kept aside",
  "plan.arithmetic": "Calculation Breakdown",
  "plan.tradeOffs": "Alternative Options",
  "plan.pressureWarning":
    "Some days near month-end may experience cash flow pressure. Keep your safety buffer intact.",
  "plan.action.reduce": "Lower the target",
  "plan.action.delay": "Extend the timeline",
  "plan.action.switch": "Switch to QR",
  "plan.action.do_nothing": "Keep things as they are",
  "plan.reviewForecastPrompt": "Review the 14-day cash flow forecast?",

  "spending.headerTag": "Spending Review",
  "spending.title": "Where Your Money Went",
  "spending.subtitle": "Review recent transactions and identify avoidable transaction fees.",
  "spending.loading": "Analyzing spending records…",
  "spending.summary": "Transaction Summary",
  "spending.cashOutCount": "Cash withdrawals",
  "spending.cashOutCountSub": "Total cash-outs in the last 30 days",
  "spending.cashOutVolume": "Total cash withdrawn",
  "spending.cashOutVolumeSub": "Cash withdrawn from agents or merchants",
  "spending.feePaid": "Fees paid",
  "spending.feePaidSub": "Cash-out fees incurred (1.85%)",
  "spending.singleRuleTop": "Total summary",
  "spending.anomalies": "Unusual Transactions",
  "spending.anomaliesNone": "No unusual transactions detected in this period.",
  "spending.reason": "Reason identified",
  "spending.action": "Recommended action",
  "spending.feeSwitch": "Reduce Cash-Out Fees",
  "spending.feeSwitchDesc": "Instead of paying cash-out fees at agents, paying merchants directly via Bangla QR or app transfer eliminates the fee.",
  "spending.doNothingOutcome": "If you make no changes, about {fee} continues to be spent on cash-out fees each month.",
  "spending.potentialSaving": "Potential monthly savings",
  "spending.currentFee": "Current monthly fees",
  "spending.altChannel": "Alternative method",
  "spending.altFee": "Fee with alternative",
  "spending.adoption": "Adoption range",
  "spending.perMonth": "per month",
  "spending.times": "times",
  "spending.daysUnit": "days",
  "spending.warningStripTitle": "Notice",
  "spending.warningStripText": "Days 28–31 typically experience higher cash flow pressure.",
  "spending.banglaQrTitle": "Pay Merchants by QR: Zero Fee",
  "spending.banglaQrDesc": "Since 1 October 2026, paying merchants via Bangla QR incurs a 0% fee instead of the 1.4% cash-out fee. The government incentive is paid to institutions, not the customer. (Source: Bangladesh Bank)",
  "spending.banglaQrNoFee": "0% customer fee",
  "spending.banglaQrEligible": "{count} cash-outs (total {volume}) could have been free QR payments at shops.",
  "spending.banglaQrCustomerBenefit": "QR at shops: 0% fee. Cash out: 1.4% fee.",
  "spending.banglaQrUpayBenefit": "The 0.20% government bonus goes to the bank, not to you.",
  "spending.banglaQrAntiMisuseTitle": "Compliance Notice",
  "spending.banglaQrAntiMisuseText": "Splitting payments near ৳2,000 or conducting unauthorized cash-outs through merchant QR is strictly prohibited under payment regulations.",

  "voice.label": "Enter your savings goal",
  "voice.speak": "Speak",
  "voice.listening": "Listening…",
  "voice.unsupported": "Voice does not work on this phone. Please type.",
  "voice.denied": "Please allow the mic.",
  "voice.nomic": "No microphone detected. Please type.",
  "voice.offline": "Voice input requires internet connection. Please connect and try again.",
  "voice.nospeech": "No speech detected. Please speak closer to the microphone.",
  "voice.heard": "Heard:",
  "voice.confirm": "Calculate",
  "voice.retry": "Speak again",
  "voice.needBoth": "Enter both the amount and the timeline, then calculate.",
  "voice.placeholder": "For example: I want to save ৳30,000 in 6 months",
  "voice.suggestedTitle": "Examples:",

  "tips.headerTag": "Guidance",
  "tips.title": "Financial Coaching",
  "tips.subtitle": "Personalized recommendations based on your transaction history.",
  "tips.loading": "Generating coaching guidance…",
  "tips.whyThisTip": "Why this guidance?",
  "tips.suggestedAction": "Recommended action",
  "tips.none": "No active concerns. Your transaction habits are consistent.",
  "tips.coachAdvice": "Ledger Analysis",
  "tips.coreGuidance": "Key Recommendations",
  "tips.unavailable": "Coaching guidance is currently unavailable. Please verify the connection and try again.",
  "tips.stampRule": "Regulatory rule",
  "tips.stampForecast": "From forecast",
  "tips.stampPlan": "For savings plan",

  "signal.headerTag": "Consistency",
  "signal.title": "Transaction Consistency",
  "signal.subtitle": "An educational rating across three tiers based on your regular financial habits.",
  "signal.loading": "Evaluating transaction patterns…",
  "signal.band": "Your level",
  "signal.factors": "Contributing factors",
  "signal.improvements": "Steps to improve consistency",
  "signal.improves": "Improves",
  "signal.weakens": "Lowers",
  "signal.comingSoon": "Consistency level will appear once evaluation completes.",
  "signal.educationalBadge": "Educational only",
  "signal.educationalNote": "This assessment is for educational purposes only. It does not constitute a credit decision.",
  "signal.guaranteeTitle": "Important notice",
  "signal.bandSteady": "Steady",
  "signal.bandBuilding": "Building",
  "signal.bandStrong": "Strong",
  "signal.unavailable": "Consistency rating is currently unavailable. Please verify connection and try again.",
  "signal.bandRating": "Consistent",
  "signal.bandRatingBuilding": "Developing",
  "signal.bandRatingStrong": "Highly consistent",
  "signal.step1": "1. Building",
  "signal.step2": "2. Steady",
  "signal.step3": "3. Strong",
  "signal.logisticRegression": "Consistency model",

  "metrics.headerTag": "Model Performance & Evaluation",
  "metrics.title": "Model Accuracy & Fairness",
  "metrics.subtitle": "How often our estimates are right, compared against simple baselines.",
  "metrics.loading": "Retrieving evaluation metrics…",
  "metrics.forecast": "Cash-Flow Forecast Model",
  "metrics.forecastBadge": "14-Day Model",
  "metrics.model": "Our model",
  "metrics.baseline": "Simple average",
  "metrics.mae": "MAE",
  "metrics.maeLong": "Average error",
  "metrics.rmse": "Root mean squared error",
  "metrics.improvement": "Better by",
  "metrics.anomaly": "Anomaly Detection Model",
  "metrics.anomalyBadge": "Isolation Forest",
  "metrics.anomalyDesc": "Identifies transactions significantly deviating from your established patterns, trained on your historical ledger.",
  "metrics.signal": "Consistency Model",
  "metrics.fairness": "Fairness Across Cohorts",
  "metrics.fairnessDesc": "Evaluated across 5 occupations and 10 districts to verify consistent performance across demographics.",
  "metrics.demoAudit": "Audit Run",
  "metrics.comingSoon": "Fairness evaluation will appear once the audit finishes.",
  "metrics.fairnessTable": "Demographic Parity Analysis",
  "metrics.dimension": "Dimension",
  "metrics.group": "Group",
  "metrics.metric": "Metric",
  "metrics.value": "Result",
  "metrics.gap": "Disparity",
  "metrics.impactTitle": "Impact & Evaluation",
  "metrics.precision": "Precision",
  "metrics.recall": "Recall",
  "metrics.f1": "F1 Score",
  "metrics.auc": "ROC-AUC",
  "metrics.outOf100": "out of 100",
  "metrics.requestsUnit": "requests",
  "metrics.inflow": "Money in (14 days)",
  "metrics.outflow": "Money out (14 days)",
  "metrics.net": "Net (14 days)",
  "metrics.macroContext":
    "Market context: Since 1 July, merchant QR payments grew 3.5× by volume and 5× by value to ৳143.54 crore daily (Source: Bangladesh Bank, September 2026).",
  "metrics.institutionalCaveat":
    "Regulatory rule: The 0.20% central-bank incentive applies strictly to transactions up to ৳2,000 via NPSB. Larger transactions follow standard commercial terms.",
  "metrics.notesTitle": "Model Limitations",
  "forecast.driversTitle": "Factors Behind Pressure Days",
  "forecast.driversBadge": "Factors",
  "forecast.increasesOutflow": "Increases spending",
  "forecast.decreasesOutflow": "Decreases spending",

  "footer.ledgerSystem": "Shonchoy Copilot",
  "footer.demoDisclaimer": "Practice data — all figures are synthetic.",

  "error.title": "An error occurred",
  "error.retry": "Try again",
} as const;

type TranslationKey = keyof typeof en;
type Dictionary = Record<TranslationKey, string>;

const bn: Dictionary = {
  appName: "সঞ্চয় Copilot",
  subTitle: "সহজ টাকার হিসাব • বাংলা আগে",
  subTitleBadge: "সহজ খতিয়ান ধরন",
  tagline:
    "দোকানের খাঁটি লাল-বাঁধানো জাবেদা ও খতিয়ান খাতার নান্দনিকতা। সম্পূর্ণ ফ্ল্যাট, শান্ত, উচ্চ পঠনযোগ্যতা এবং শূন্য অলঙ্করণ সহ সাধারণ মানুষের জন্য নির্মিত খাঁটি ডিজিটাল লেজার।",

  "nav.home": "হোম",
  "nav.plan": "সঞ্চয়",
  "nav.forecast": "আগাম হিসাব",
  "nav.spending": "খরচ",
  "nav.tips": "পরামর্শ",
  "nav.signal": "নিয়মিত অভ্যাস",
  "nav.metrics": "ফলাফল",
  "nav.more": "আরও",

  "lang.switchTo": "ভাষা নির্বাচন",

  "stamp.computed": "আমাদের হিসাবে",
  "stamp.easyExplain": "সহজ ভাষায়",
  "stamp.verified": "✓ যাচাইকৃত",

  "status.title": "অ্যাকাউন্টের অবস্থা",
  "status.checking": "তথ্য যাচাই করা হচ্ছে…",
  "status.apiReachable": "সংযোগ সক্রিয়",
  "status.apiUnreachable": "সংযোগ বিচ্ছিন্ন",
  "status.apiHint":
    "অ্যাপ সার্ভারের সাথে সংযোগ করা যাচ্ছে না। সার্ভার চালু করে পৃষ্ঠাটি পুনরায় লোড করুন।",
  "status.serviceVersion": "সংস্করণ",
  "status.database": "ডাটাবেজ",
  "status.databaseReady": "প্রস্তুত",
  "status.databaseMissing": "অনুপলব্ধ",
  "status.users": "ব্যবহারকারী",
  "status.transactions": "মোট লেনদেন",
  "status.generatedAt": "হিসাবের সময়",
  "status.features": "সক্রিয় সুবিধা",
  "status.degraded": "ধীরগতি",

  "identity.title": "হিসাবধারী",
  "identity.persona": "পেশা",
  "identity.district": "জেলা",
  "identity.incomeBand": "আয়ের স্তর",
  "identity.cohort": "দল",
  "identity.demoUser": "ডেমো প্রোফাইল",

  "common.prediction": "পূর্বাভাস",
  "common.assumption": "যা ধরে নিচ্ছি",
  "common.explanation": "কারণ",
  "common.calculationTrace": "হিসাবের বিবরণ",
  "common.howCalculated": "হিসাবের ভিত্তি",
  "common.source": "উৎস",
  "common.taka": "টাকা",
  "common.doNothing": "কিছু না করলে কী হবে?",
  "common.doNothingCost": "কিছু না করলে এই মাসে খরচ হবে প্রায়",
  "common.doNothingConfirm": "ঠিক আছে",
  "common.doNothingDismiss": "পরে দেখব",
  "common.doNothingChosen": "লিপিবদ্ধ করা হয়েছে — কোনো পরিবর্তন করা হয়নি।",
  "common.doNothingHint":
    "প্রতিটি পরামর্শ ঐচ্ছিক। আপনার নিশ্চিতকরণ ছাড়া কোনো পরিবর্তন হবে না।",
  "common.doNothingOutcome":
    "৬ মাসে কোনো টাকা না জমালে সঞ্চয়ের পরিমাণ হবে ৳০।",
  "common.doNothingOutcomeN":
    "{months} মাসে কোনো টাকা না জমালে সঞ্চয়ের পরিমাণ হবে ৳০।",
  "common.doNothingOutcome1":
    "১ মাসে কোনো টাকা না জমালে সঞ্চয়ের পরিমাণ হবে ৳০।",
  "common.doNothingDisclaimer":
    "কোনো জরিমানা নেই। অ্যাপ কখনো আপনার অর্থ স্থানান্তর করে না।",

  "banner.title": "মনে রাখুন",
  "banner.notADecision":
    "এটি শুধুমাত্র তথ্য — আপনার বিষয়ে কোনো সিদ্ধান্ত নয়।",
  "banner.notADecision.home":
    "এটি কেবল তথ্য। আপনার নিশ্চিতকরণ ছাড়া কোনো অর্থ স্থানান্তরিত হয় না।",
  "banner.notADecision.forecast":
    "এটি একটি ধারণা, কোনো নিশ্চিত প্রতিশ্রুতি নয়।",
  "banner.notADecision.plan":
    "পরিকল্পনা করা হয়েছে। পৌঁছানো নিশ্চিত নয়।",
  "banner.notADecision.spending":
    "এটি কেবল খরচের খতিয়ান। কোনো পরিবর্তন করা হয়নি।",
  "banner.notADecision.tips":
    "এগুলো সাধারণ তথ্য। আপনার বিষয় আলাদা হতে পারে।",
  "banner.notADecision.signal":
    "লোন দেবেন কি না, সেটা ব্যাংক ঠিক করবে।",
  "banner.notADecision.metrics":
    "এই সংখ্যাগুলো অ্যাপের কাজের মান দেখায়। এগুলো কোনো প্রতিশ্রুতি নয়।",

  "assumption.forecast":
    "ধরে নেওয়া হয়েছে বিগত ৬০ দিনের লেনদেনের ধারা বজায় থাকবে এবং নিয়মিত খরচ অপরিবর্তিত থাকবে।",
  "assumption.plan":
    "ধরে নেওয়া হয়েছে মাসিক বাফার অপরিবর্তিত থাকবে এবং নতুন কোনো বড় অপ্রত্যাশিত খরচ আসবে না।",
  "assumption.spending":
    "ধরে নেওয়া হয়েছে নগদ তোলার ধরণ অপরিবর্তিত থাকবে এবং কিউআর গ্রহণকারী মার্চেন্ট সেবা চালু থাকবে।",
  "assumption.tips":
    "ধরে নেওয়া হয়েছে বিগত মাসের ক্যাশ খরচ ও সঞ্চয় পরিকল্পনার নিয়মাবলী প্রযোজ্য।",

  "home.next.title": "পরবর্তী ধাপসমূহ",
  "home.next.body":
    "আগামী ১৪ দিনের ক্যাশ ফ্লো দেখুন, সঞ্চয় পরিকল্পনা করুন এবং খরচের খতিয়ান যাচাই করুন।",
  "home.startSavings": "সঞ্চয় পরিকল্পনা শুরু করুন",
  "home.viewDetails": "বিস্তারিত দেখুন",
  "home.reformChangelog":
    "১ অক্টোবর থেকে QR-এ লেনদেন গ্রহণে মার্চেন্টকে কোনো ফি দিতে হয় না।",
  "home.reformChangelogTag": "১ অক্টোবর ২০২৬",

  "comingSoon.title": "শীঘ্রই আসছে",
  "comingSoon.phase5": "খরচ সহযোগী (পঞ্চম ধাপ)",
  "comingSoon.phase7": "পরামর্শ ও ধারাবাহিকতা (সপ্তম ধাপ)",
  "comingSoon.phase8": "প্রমাণ ও মেট্রিক্স (অষ্টম ধাপ)",

  "forecast.headerTag": "১৪ দিনের পূর্বাভাস",
  "forecast.title": "আগামী ১৪ দিনের ক্যাশ ফ্লো",
  "forecast.subtitle":
    "আপনার পূর্ববর্তী লেনদেনের ভিত্তিতে আগামী ১৪ দিনের সম্ভাব্য আয়, ব্যয় ও উদ্বৃত্তের হিসাব।",
  "forecast.monthEndPreset": "মাস শেষের ২৮–৩১ তারিখ",
  "forecast.latestPreset": "সাম্প্রতিক ১৪ দিন",
  "forecast.netSourceModel": "আমাদের মডেল",
  "forecast.netSourceAnchor": "পূর্ববর্তী ধারা অনুযায়ী",
  "forecast.netSourceDifference": "সাধারণ গড়",
  "forecast.loading": "আগামী ১৪ দিনের হিসাব করা হচ্ছে…",
  "forecast.days": "তারিখ",
  "forecast.inflow": "টাকা আসছে",
  "forecast.outflow": "টাকা যাচ্ছে",
  "forecast.net": "উদ্বৃত্ত",
  "forecast.balance": "হাতে থাকা",
  "forecast.pressureTitle": "টানের দিনসমূহ",
  "forecast.pressureNone": "এই সময়ে কোনো টানের দিন নেই — উদ্বৃত্ত সবসময় নির্ধারিত সীমার উপরে থাকবে।",
  "forecast.pressureBadge": "টানের দিন",
  "forecast.reasonNegativeNet": "আয়ের চেয়ে খরচ বেশি",
  "forecast.reasonBelowBuffer": "ব্যালেন্স নিরাপদ সীমার নিচে নেমে আসছে",
  "forecast.reasonBoth": "আয়ের চেয়ে খরচ বেশি এবং ব্যালেন্স নিরাপদ সীমার নিচে",
  "forecast.modelAccuracy": "সাধারণ গড়ের তুলনায় আমাদের হিসাবের যথার্থতা",
  "forecast.noMetrics": "হিসাব শেষ হলে এখানে মূল্যায়নের মান প্রদর্শিত হবে।",
  "forecast.table": "দৈনিক হিসাব",
  "forecast.tableSub": "১৪ দিনের বিশদ খতিয়ান",
  "forecast.planSavingsPrompt": "এই উদ্বৃত্ত থেকে কি সঞ্চয় পরিকল্পনা করতে চান?",

  "plan.headerTag": "মাসিক সঞ্চয়",
  "plan.title": "আপনার সঞ্চয় পরিকল্পনা",
  "plan.subtitle":
    "আপনার লক্ষ্য ও সময়সীমা দিন। গড়ের ভিত্তিতে নয় — আপনার প্রকৃত উদ্বৃত্ত দিয়েই হিসাব।",
  "plan.goal": "লক্ষ্যের পরিমাণ (৳)",
  "plan.months": "সময়সীমা (মাস)",
  "plan.submit": "পরিকল্পনা হিসাব করুন",
  "plan.calculating": "পরিকল্পনা হিসাব করা হচ্ছে…",
  "plan.feasible": "এই পরিকল্পনা বাস্তবায়নযোগ্য",
  "plan.infeasible": "বর্তমান আয়ে এই লক্ষ্য অর্জন কঠিন",
  "plan.requiredMonthly": "প্রতি মাসে প্রয়োজনীয় সঞ্চয়",
  "plan.feasibleMonthly": "প্রতি মাসে জমাতে পারবেন",
  "plan.surplus": "মাসিক উদ্বৃত্ত টাকা",
  "plan.buffer": "নিরাপদ জমার জন্য সংরক্ষিত",
  "plan.arithmetic": "হিসাবের বিবরণ",
  "plan.tradeOffs": "বিকল্প সমাধান",
  "plan.pressureWarning":
    "মাসের শেষে কিছু দিন টান পড়তে পারে। সংরক্ষিত অর্থে হাত দেবেন না।",
  "plan.action.reduce": "লক্ষ্যের পরিমাণ কমান",
  "plan.action.delay": "সময়সীমা বাড়ান",
  "plan.action.switch": "ক্যাশ-আউট কমিয়ে QR ব্যবহার",
  "plan.action.do_nothing": "কিছু পরিবর্তন করব না",
  "plan.reviewForecastPrompt": "আগামী ১৪ দিনের ক্যাশ ফ্লো দেখতে চান?",

  "spending.headerTag": "খরচের পর্যালোচনা",
  "spending.title": "খরচের খতিয়ান ও পর্যালোচনা",
  "spending.subtitle": "সাম্প্রতিক লেনদেন দেখুন এবং অপ্রয়োজনীয় ফি কমানোর উপায় জানুন।",
  "spending.loading": "খরচের হিসাব পর্যালোচনা করা হচ্ছে…",
  "spending.summary": "লেনদেনের সারসংক্ষেপ",
  "spending.cashOutCount": "ক্যাশ-আউট সংখ্যা",
  "spending.cashOutCountSub": "গত ৩০ দিনে মোট কতবার ক্যাশ-আউট করেছেন",
  "spending.cashOutVolume": "ক্যাশ-আউট করা মোট অর্থ",
  "spending.cashOutVolumeSub": "এজেন্ট বা দোকান থেকে উত্তোলিত নগদ টাকা",
  "spending.feePaid": "পরিশোধিত ফি",
  "spending.feePaidSub": "ক্যাশ-আউটে কাটা ফি (১.৮৫%)",
  "spending.singleRuleTop": "মোট হিসাব",
  "spending.anomalies": "অস্বাভাবিক লেনদেন",
  "spending.anomaliesNone": "এই সময়ে কোনো অস্বাভাবিক লেনদেন দেখা যায়নি।",
  "spending.reason": "চিহ্নিত কারণ",
  "spending.action": "করণীয়",
  "spending.feeSwitch": "ক্যাশ-আউট ফি কমানোর উপায়",
  "spending.feeSwitchDesc": "এজেন্ট থেকে নগদ না তুলে দোকানে সরাসরি Bangla QR বা অ্যাপের মাধ্যমে দিলে ক্যাশ-আউট ফি লাগবে না।",
  "spending.doNothingOutcome": "কোনো পরিবর্তন না করলে প্রতি মাসে প্রায় {fee} ক্যাশ-আউট ফিতে ব্যয় হবে।",
  "spending.potentialSaving": "মাসিক সাশ্রয়",
  "spending.currentFee": "বর্তমান মাসিক ফি",
  "spending.altChannel": "বিকল্প মাধ্যম",
  "spending.altFee": "বিকল্প মাধ্যমে ফি",
  "spending.adoption": "সম্ভাব্য গ্রহণের হার",
  "spending.perMonth": "প্রতি মাসে",
  "spending.times": "বার",
  "spending.daysUnit": "দিন",
  "spending.warningStripTitle": "সতর্কতা",
  "spending.warningStripText": "২৮–৩১ তারিখ ব্যয়ের সম্ভাব্য চাপের সময়।",
  "spending.banglaQrTitle": "দোকানে QR পেমেন্ট: কোনো চার্জ নেই",
  "spending.banglaQrDesc": "১ অক্টোবর ২০২৬ থেকে দোকানে QR-এ লেনদেনে ০% ফি — ক্যাশ-আউটের ১.৪% ফি দিতে হয় না। সরকারি প্রণোদনা ব্যাংক পায়, আপনি পান না। (উৎস: বাংলাদেশ ব্যাংক)",
  "spending.banglaQrNoFee": "গ্রাহকের জন্য ০% ফি",
  "spending.banglaQrEligible": "{count}টি ক্যাশ-আউট (মোট {volume}) দোকানে সরাসরি QR-এ দিলে কোনো ফি লাগত না।",
  "spending.banglaQrCustomerBenefit": "QR-এ কোনো চার্জ লাগে না। ক্যাশ আউটে ১.৪% কাটে।",
  "spending.banglaQrUpayBenefit": "সরকারের ০.২০% প্রণোদনা ব্যাংক পায়, আপনি পান না।",
  "spending.banglaQrAntiMisuseTitle": "নিয়ম মেনে QR ব্যবহার করুন",
  "spending.banglaQrAntiMisuseText": "২,০০০ টাকার কাছাকাছি লেনদেন ভাগ করা বা দোকান থেকে অননুমোদিত নগদ গ্রহণ আইনত দণ্ডনীয়।",

  "voice.label": "আপনার সঞ্চয় লক্ষ্য লিখুন",
  "voice.speak": "বলুন",
  "voice.listening": "শোনা হচ্ছে…",
  "voice.unsupported": "এই ফোনে ভয়েস কাজ করে না। লিখে দিন।",
  "voice.denied": "মাইকে অনুমতি দিন।",
  "voice.nomic": "কোনো মাইক পাওয়া যায়নি। লিখে দিন।",
  "voice.offline": "ভয়েস ইনপুটের জন্য ইন্টারনেট সংযোগ প্রয়োজন। সংযোগ দিয়ে আবার চেষ্টা করুন।",
  "voice.nospeech": "কোনো কথা শোনা যায়নি। মাইকের কাছে এসে আবার বলুন।",
  "voice.heard": "যা শোনা গেছে:",
  "voice.confirm": "হিসাব করুন",
  "voice.retry": "আবার বলুন",
  "voice.needBoth": "টাকার পরিমাণ ও সময়সীমা দুটোই উল্লেখ করুন, তারপর হিসাব করুন।",
  "voice.placeholder": "উদাহরণ: ৬ মাসে ৳৩০,০০০ জমাতে চাই",
  "voice.suggestedTitle": "উদাহরণসমূহ:",

  "tips.headerTag": "দিকনির্দেশনা",
  "tips.title": "আর্থিক দিকনির্দেশনা",
  "tips.subtitle": "আপনার লেনদেনের খতিয়ান বিশ্লেষণ করে তৈরি দিকনির্দেশনা।",
  "tips.loading": "দিকনির্দেশনা তৈরি করা হচ্ছে…",
  "tips.whyThisTip": "কেন এই নির্দেশনা",
  "tips.suggestedAction": "করণীয় পদক্ষেপ",
  "tips.none": "এই মুহূর্তে কোনো সতর্কবার্তা নেই। আপনার লেনদেনের অভ্যাস স্থিতিশীল।",
  "tips.coachAdvice": "খতিয়ানভিত্তিক পরামর্শ",
  "tips.coreGuidance": "মূল দিকনির্দেশনা",
  "tips.unavailable": "এই মুহূর্তে পরামর্শ তৈরি করা সম্ভব হচ্ছে না। সংযোগ দেখে আবার চেষ্টা করুন।",
  "tips.stampRule": "নিয়ম অনুযায়ী",
  "tips.stampForecast": "পূর্বাভাসভিত্তিক",
  "tips.stampPlan": "পরিকল্পনাভিত্তিক",

  "signal.headerTag": "ধারাবাহিকতা",
  "signal.title": "লেনদেনের ধারাবাহিকতার মূল্যায়ন",
  "signal.subtitle": "নিয়মিত লেনদেনের অভ্যাসের ওপর ভিত্তি করে তিনটি স্তরে ধারাবাহিকতার মূল্যায়ন।",
  "signal.loading": "লেনদেনের ধারাবাহিকতা মূল্যায়ন করা হচ্ছে…",
  "signal.band": "আপনার স্তর",
  "signal.factors": "প্রভাবক কারণসমূহ",
  "signal.improvements": "ধারাবাহিকতা বাড়ানোর পদক্ষেপ",
  "signal.improves": "ইতিবাচক",
  "signal.weakens": "নেতিবাচক",
  "signal.comingSoon": "মূল্যায়ন সম্পন্ন হলে এখানে স্তর প্রদর্শিত হবে।",
  "signal.educationalBadge": "শিক্ষামূলক",
  "signal.educationalNote": "এটি শুধুমাত্র শিক্ষামূলক তথ্য। এটি কোনো ঋণের সিদ্ধান্ত নয়।",
  "signal.guaranteeTitle": "জরুরি তথ্য",
  "signal.bandSteady": "স্থিতিশীল",
  "signal.bandBuilding": "উন্নতিশীল",
  "signal.bandStrong": "দৃঢ়",
  "signal.unavailable": "এই মুহূর্তে ধারাবাহিকতা মূল্যায়ন অনুপলব্ধ। সংযোগ দেখে আবার চেষ্টা করুন।",
  "signal.bandRating": "স্থিতিশীল অভ্যাস",
  "signal.bandRatingBuilding": "বিকাশমান অভ্যাস",
  "signal.bandRatingStrong": "দৃঢ় ধারাবাহিকতা",
  "signal.step1": "১. উন্নতিশীল",
  "signal.step2": "২. স্থিতিশীল",
  "signal.step3": "৩. দৃঢ়",
  "signal.logisticRegression": "ধারাবাহিকতা যাচাই",

  "metrics.headerTag": "স্বচ্ছতা ও মডেল মূল্যায়ন",
  "metrics.title": "মডেলের কার্যকারিতা ও স্বচ্ছতা",
  "metrics.subtitle": "সাধারণ অনুমানের তুলনায় আমাদের মডেল কতটা নির্ভুল এবং স্বচ্ছ।",
  "metrics.loading": "মূল্যায়ন মেট্রিক্স লোড করা হচ্ছে…",
  "metrics.forecast": "ক্যাশ-ফ্লো পূর্বাভাস মডেল",
  "metrics.forecastBadge": "১৪ দিনের মডেল",
  "metrics.model": "আমাদের মডেল",
  "metrics.baseline": "সাধারণ গড়",
  "metrics.mae": "MAE",
  "metrics.maeLong": "গড় বিচ্যুতি",
  "metrics.rmse": "বড় বিচ্যুতির প্রভাব (RMSE)",
  "metrics.improvement": "উন্নত",
  "metrics.anomaly": "অস্বাভাবিক লেনদেন শনাক্তকারী",
  "metrics.anomalyBadge": "স্বয়ংক্রিয় শনাক্তকরণ",
  "metrics.anomalyDesc": "আপনার ঐতিহাসিক লেনদেনের ওপর ভিত্তি করে স্বাভাবিক ধারার বাইরের লেনদেন শনাক্ত করে।",
  "metrics.signal": "ধারাবাহিকতা মডেল",
  "metrics.fairness": "সকল ব্যবহারকারীর জন্য নিরপেক্ষতা",
  "metrics.fairnessDesc": "৫টি পেশা ও ১০টি জেলায় যাচাই করা হয়েছে, যাতে সবার জন্য হিসাবের মান সমান থাকে।",
  "metrics.demoAudit": "নিরপেক্ষতা নিরীক্ষা",
  "metrics.comingSoon": "নিরীক্ষা শেষ হলে এখানে নিরপেক্ষতার হিসাব দেখা যাবে।",
  "metrics.fairnessTable": "জনমিতিক সমতা বিশ্লেষণ",
  "metrics.dimension": "বিষয়",
  "metrics.group": "দল",
  "metrics.metric": "মেট্রিক",
  "metrics.value": "ফলাফল",
  "metrics.gap": "পার্থক্য",
  "metrics.impactTitle": "কার্যকারিতা ও মূল্যায়ন",
  "metrics.precision": "সঠিকতা",
  "metrics.recall": "শনাক্তকরণ",
  "metrics.f1": "সামগ্রিক নির্ভুলতা (F1)",
  "metrics.auc": "সঠিকতা যাচাই (ROC-AUC)",
  "metrics.outOf100": "১০০-এর মধ্যে",
  "metrics.requestsUnit": "টি অনুরোধ",
  "metrics.inflow": "আসা টাকা (১৪ দিন)",
  "metrics.outflow": "যাওয়া টাকা (১৪ দিন)",
  "metrics.net": "উদ্বৃত্ত (১৪ দিন)",
  "metrics.macroContext":
    "বাজার প্রেক্ষাপট: ১ জুলাই থেকে দোকানের কিউআর পেমেন্ট সংখ্যায় ৩.৫ গুণ এবং মানে ৫ গুণ বেড়ে দৈনিক ৳১৪৩.৫৪ কোটিতে পৌঁছেছে (উৎস: বাংলাদেশ ব্যাংক, সেপ্টেম্বর ২০২৬)।",
  "metrics.institutionalCaveat":
    "নিয়মাবলী: ০.২০% সরকারি প্রণোদনা কেবল NPSB মাধ্যমে ২,০০০ টাকা পর্যন্ত পেমেন্টে প্রযোজ্য। এর বেশি অঙ্কে সাধারণ মার্চেন্ট শর্তাবলী প্রযোজ্য।",
  "metrics.notesTitle": "মডেলের সীমাবদ্ধতা",
  "forecast.driversTitle": "টানের দিনগুলোর কারণ",
  "forecast.driversBadge": "প্রভাবক",
  "forecast.increasesOutflow": "খরচ বাড়ায়",
  "forecast.decreasesOutflow": "খরচ কমায়",

  "footer.ledgerSystem": "সঞ্চয় Copilot",
  "footer.demoDisclaimer": "অনুশীলনের তথ্য — সব সংখ্যা কৃত্রিম।",

  "error.title": "ত্রুটি ঘটেছে",
  "error.retry": "পুনরায় চেষ্টা করুন",
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

/** "2026-10-01" -> "1 October 2026" / "১ অক্টোবর ২০২৬". Never ISO on screen. */
export function formatWrittenDate(iso: string | null | undefined, lang: Lang): string {
  if (!iso) return "—";
  const m = iso.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return formatDigits(iso, lang);
  const monthsEn = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  const monthsBn = [
    "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
    "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর",
  ];
  const monthIndex = Math.min(Math.max(Number(m[2]), 1), 12) - 1;
  const day = String(Number(m[3]));
  const year = m[1];
  if (lang === "bn") {
    return `${formatDigits(day, lang)} ${monthsBn[monthIndex]} ${formatDigits(year, lang)}`;
  }
  return `${day} ${monthsEn[monthIndex]} ${year}`;
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
    return lang === "bn" ? "আমাদের মডেল" : "Our model";
  }
  if (lower.includes("trailing_average") || lower.includes("baseline") || lower.includes("average")) {
    return lang === "bn" ? "সাধারণ গড়" : "Simple average";
  }
  if (lower.includes("isolation")) {
    return lang === "bn" ? "অস্বাভাবিক লেনদেন শনাক্তকারী" : "Anomaly detector";
  }
  if (lower.includes("logistic")) {
    return lang === "bn" ? "ধারাবাহিকতা মডেল" : "Consistency model";
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
    return lang === "bn" ? "মাসে ঘাটতির দিন" : "Shortfall Days Per Month";
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
    clean = clean.replace(/shortfall_days_per_month/g, lang === "bn" ? "মাসে ঘাটতির দিন" : "shortfall days per month");
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
  if (lang === "en") {
    return persona
      .split("_")
      .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
      .join(" ");
  }
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
  if (lang === "en") return band ? band[0].toUpperCase() + band.slice(1) : band;
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
    "System Computed": "আমাদের হিসাবে",
    "Rule Verified": "✓ যাচাইকৃত",
    "Plain Language": "সহজ ভাষায়",
    "Logistic Regression": "ধারাবাহিকতা মডেল",
    "Isolation Forest": "অস্বাভাবিক লেনদেন শনাক্তকারী",
    LightGBM: "আমাদের মডেল",
    Educational: "শিক্ষামূলক",
  };
  return map[status] ?? status;
}

