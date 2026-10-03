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

  "home.next.title": "What you can do here",
  "home.next.body":
    "See the next 14 days, make a saving plan, and check your spending below.",
  "home.startSavings": "Start Savings Plan",
  "home.viewDetails": "See details",
  "home.reformChangelog":
    "Since 1 October, shops pay no fee to accept QR.",
  "home.reformChangelogTag": "1 October 2026",

  "comingSoon.title": "Coming Soon",
  "comingSoon.phase5": "Spending companion (Phase 5)",
  "comingSoon.phase7": "Tips and consistency signal (Phase 7)",
  "comingSoon.phase8": "Evidence and metrics (Phase 8)",

  "forecast.headerTag": "Next 14 days",
  "forecast.title": "Money in the next 14 days",
  "forecast.subtitle":
    "Money coming in, money going out, and what stays in hand — checked against your own past.",
  "forecast.monthEndPreset": "Show days 28–31",
  "forecast.latestPreset": "Last 14 days",
  "forecast.netSourceModel": "Our count",
  "forecast.netSourceAnchor": "Checked with past",
  "forecast.netSourceDifference": "Simple guess",
  "forecast.loading": "Counting the next 14 days…",
  "forecast.days": "Date",
  "forecast.inflow": "Money in",
  "forecast.outflow": "Money out",
  "forecast.net": "Left",
  "forecast.balance": "In hand",
  "forecast.pressureTitle": "Tight days",
  "forecast.pressureNone": "No tight days here — money in hand stays above the money kept aside.",
  "forecast.pressureBadge": "Tight day",
  "forecast.reasonNegativeNet": "more goes out than comes in",
  "forecast.reasonBelowBuffer": "in-hand money drops below the kept-aside money",
  "forecast.reasonBoth": "more goes out than comes in, and in-hand money drops below the kept-aside money",
  "forecast.modelAccuracy": "How close we get, vs a simple guess",
  "forecast.noMetrics": "Closeness numbers will appear here once counting finishes.",
  "forecast.table": "Day by day",
  "forecast.tableSub": "14 days, one by one",
  "forecast.planSavingsPrompt": "Want to plan saving from what's left?",

  "plan.headerTag": "Saving month by month",
  "plan.title": "Your saving plan",
  "plan.subtitle":
    "Write your goal and months. We check what is left in your hands — not an average.",
  "plan.goal": "Goal (৳)",
  "plan.months": "Months",
  "plan.submit": "Make my plan",
  "plan.calculating": "Making your plan…",
  "plan.feasible": "This plan works",
  "plan.infeasible": "Too big for right now",
  "plan.requiredMonthly": "Needed each month",
  "plan.feasibleMonthly": "You can save each month",
  "plan.surplus": "Extra money each month",
  "plan.buffer": "Kept aside for safety",
  "plan.arithmetic": "How we counted",
  "plan.tradeOffs": "Other ways to make it fit",
  "plan.pressureWarning":
    "Some days at month-end will be tight. Keep your safety money untouched.",
  "plan.action.reduce": "Lower the goal",
  "plan.action.delay": "Take more time",
  "plan.action.switch": "Pay by QR",
  "plan.action.do_nothing": "Do nothing",
  "plan.reviewForecastPrompt": "Want to see the next 14 days?",

  "spending.headerTag": "Spending",
  "spending.title": "Where your money went",
  "spending.subtitle": "Look at recent payments and find fees you can avoid.",
  "spending.loading": "Looking at your spending…",
  "spending.summary": "Your money, counted",
  "spending.cashOutCount": "Cash taken out",
  "spending.cashOutCountSub": "How many times in the last 30 days",
  "spending.cashOutVolume": "Cash taken home",
  "spending.cashOutVolumeSub": "All cash taken from shops or agents",
  "spending.feePaid": "Fees given",
  "spending.feePaidSub": "Cash-out fee already cut (1.85%)",
  "spending.singleRuleTop": "Added up, nothing hidden",
  "spending.anomalies": "Unusual Transactions",
  "spending.anomaliesNone": "Nothing unusual in these days.",
  "spending.reason": "Why it stood out",
  "spending.action": "What you can do",
  "spending.feeSwitch": "Pay less fee",
  "spending.feeSwitchDesc": "Take cash from an agent and you pay a fee. Pay the shop by QR or send in the app and the fee goes away.",
  "spending.doNothingOutcome": "If you change nothing, about {fee} a month keeps going to cash-out fees.",
  "spending.potentialSaving": "Saved every month",
  "spending.currentFee": "Fee you pay now",
  "spending.altChannel": "Other way",
  "spending.altFee": "Fee that way",
  "spending.adoption": "Who may use it",
  "spending.perMonth": "a month",
  "spending.times": "times",
  "spending.daysUnit": "days",
  "spending.warningStripTitle": "Watch out",
  "spending.warningStripText": "Days 28–31 typically have high cash-out pressure.",
  "spending.banglaQrTitle": "Pay shops by QR: no fee",
  "spending.banglaQrDesc": "Since 1 October 2026, paying shops by QR costs you 0% fee instead of the 1.4% cash-out fee. The government bonus goes to the bank, not to you. (Source: Bangladesh Bank)",
  "spending.banglaQrNoFee": "No fee for you",
  "spending.banglaQrEligible": "{count} small cash-outs (total {volume}) could have been free QR payments at shops.",
  "spending.banglaQrCustomerBenefit": "QR at shops: 0% fee. Cash out: 1.4% fee.",
  "spending.banglaQrUpayBenefit": "The 0.20% government bonus on these payments goes to the bank, not to you.",
  "spending.banglaQrAntiMisuseTitle": "Use QR only for real shopping",
  "spending.banglaQrAntiMisuseText": "Do not split payments near ৳2,000 or take cash from shops. Breaking the rules can bring punishment.",

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

  "tips.headerTag": "Ideas for you",
  "tips.title": "Ideas that fit you",
  "tips.subtitle": "Ideas picked from your money habits.",
  "tips.loading": "Finding ideas for you…",
  "tips.whyThisTip": "Why this tip?",
  "tips.suggestedAction": "You can try this",
  "tips.none": "Nothing to warn about. Your habits look steady.",
  "tips.coachAdvice": "Ideas from your ledger",
  "tips.coreGuidance": "Main ideas to remember",
  "tips.unavailable": "Fresh ideas are not available right now. Please check the connection and try again.",
  "tips.stampRule": "From a rule",
  "tips.stampForecast": "From coming days",
  "tips.stampPlan": "For your plan",

  "signal.headerTag": "Steady habits",
  "signal.title": "How steady are your habits?",
  "signal.subtitle": "One of three levels, from how regular your money habits are.",
  "signal.loading": "Looking at your habits…",
  "signal.band": "Your level",
  "signal.factors": "Why this level",
  "signal.improvements": "Easy ways to improve",
  "signal.improves": "Helps",
  "signal.weakens": "Hurts",
  "signal.comingSoon": "Your level will appear here once counting finishes.",
  "signal.educationalBadge": "Only information",
  "signal.educationalNote": "This only teaches. It never decides loans.",
  "signal.guaranteeTitle": "Our promise",
  "signal.bandSteady": "Steady",
  "signal.bandBuilding": "Starting out",
  "signal.bandStrong": "Strong",
  "signal.unavailable": "Your level is not available right now. Please check the connection and try again.",
  "signal.bandRating": "Fairly steady",
  "signal.bandRatingBuilding": "Just starting",
  "signal.bandRatingStrong": "Very steady",
  "signal.step1": "1. Starting out",
  "signal.step2": "2. Steady",
  "signal.step3": "3. Strong",
  "signal.logisticRegression": "Consistency check",

  "metrics.headerTag": "Transparency & Evaluation",
  "metrics.title": "How is the app doing?",
  "metrics.subtitle": "How close our counts are, compared with a simple guess.",
  "metrics.loading": "Counting how we are doing…",
  "metrics.forecast": "Smart Cash-Flow Forecast",
  "metrics.forecastBadge": "14-Day Forecast",
  "metrics.model": "Our count",
  "metrics.baseline": "Simple guess",
  "metrics.mae": "MAE",
  "metrics.maeLong": "Average miss",
  "metrics.rmse": "Big misses counted",
  "metrics.improvement": "Better by",
  "metrics.anomaly": "Anomaly Detection",
  "metrics.anomalyBadge": "Auto Detection",
  "metrics.anomalyDesc": "Finds payments far bigger than your usual, or paid at odd hours — learned from your own habits, not others'.",
  "metrics.signal": "Steady-habit check",
  "metrics.fairness": "Same for everyone",
  "metrics.fairnessDesc": "Checked across 5 kinds of work and 10 districts, so city and village users get the same quality.",
  "metrics.demoAudit": "Practice check",
  "metrics.comingSoon": "The fairness check appears here once counting finishes.",
  "metrics.fairnessTable": "Same results for different users",
  "metrics.dimension": "About",
  "metrics.group": "Who",
  "metrics.metric": "What was counted",
  "metrics.value": "Result",
  "metrics.gap": "Difference",
  "metrics.impactTitle": "What this app has changed",
  "metrics.precision": "Rightly caught",
  "metrics.recall": "Able to catch",
  "metrics.f1": "Catching well",
  "metrics.auc": "How accurate",
  "metrics.outOf100": "out of 100",
  "metrics.requestsUnit": "questions",
  "metrics.inflow": "Money in (14 days)",
  "metrics.outflow": "Money out (14 days)",
  "metrics.net": "Left (14 days)",
  "metrics.macroContext":
    "Around us: Since 1 July, QR payments by shops grew 3.5 times in count and 5 times in money, reaching ৳143.54 crore a day (Source: Bangladesh Bank, September 2026).",
  "metrics.institutionalCaveat":
    "One rule: the 0.20% government bonus counts only for payments up to ৳2,000 sent through the national network (NPSB). Bigger payments follow normal shop rules.",
  "metrics.notesTitle": "What these numbers don't say",
  "forecast.driversTitle": "Why those days look hard",
  "forecast.driversBadge": "Reasons",
  "forecast.increasesOutflow": "Pushes spending up",
  "forecast.decreasesOutflow": "Pulls spending down",

  "footer.ledgerSystem": "Shonchoy Copilot",
  "footer.demoDisclaimer": "Practice information — all numbers are made up.",

  "error.title": "Something went wrong",
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

  "home.next.title": "এখানে যা করতে পারবেন",
  "home.next.body":
    "নিচে আগামী ১৪ দিন দেখুন, সঞ্চয়ের পরিকল্পনা করুন আর খরচ যাচাই করুন।",
  "home.startSavings": "সঞ্চয় শুরু করুন",
  "home.viewDetails": "বিস্তারিত দেখুন",
  "home.reformChangelog":
    "১ অক্টোবর থেকে QR-এ টাকা নিলে দোকানদারকে চার্জ দিতে হয় না।",
  "home.reformChangelogTag": "১ অক্টোবর ২০২৬",

  "comingSoon.title": "শীঘ্রই আসছে",
  "comingSoon.phase5": "খরচ সহযোগী (পঞ্চম ধাপ)",
  "comingSoon.phase7": "পরামর্শ ও ধারাবাহিকতা (সপ্তম ধাপ)",
  "comingSoon.phase8": "প্রমাণ ও মেট্রিক্স (অষ্টম ধাপ)",

  "forecast.headerTag": "আগামী ১৪ দিন",
  "forecast.title": "আগামী ১৪ দিনে হাতে কত থাকবে",
  "forecast.subtitle":
    "কত টাকা আসবে, কত যাবে, আর হাতে কত থাকবে — আপনার নিজের পুরনো হিসাব মিলিয়ে দেখা।",
  "forecast.monthEndPreset": "মাস শেষের ২৮–৩১ দেখুন",
  "forecast.latestPreset": "শেষ ১৪ দিন",
  "forecast.netSourceModel": "আমাদের হিসাব",
  "forecast.netSourceAnchor": "পুরনো হিসাব মিলিয়ে",
  "forecast.netSourceDifference": "সাধারণ অনুমান",
  "forecast.loading": "আগামী ১৪ দিন গোনা হচ্ছে…",
  "forecast.days": "তারিখ",
  "forecast.inflow": "টাকা আসছে",
  "forecast.outflow": "টাকা যাচ্ছে",
  "forecast.net": "থাকবে",
  "forecast.balance": "হাতে থাকা",
  "forecast.pressureTitle": "টানাটানির দিন",
  "forecast.pressureNone": "এই সময়ে টানের দিন নেই — হাতে থাকা টাকা রাখা অংশের উপরেই থাকবে।",
  "forecast.pressureBadge": "টানের দিন",
  "forecast.reasonNegativeNet": "আসা টাকার চেয়ে যাওয়া টাকা বেশি",
  "forecast.reasonBelowBuffer": "হাতে থাকা টাকা রাখা অংশের নিচে নেমে আসছে",
  "forecast.reasonBoth": "আসা টাকার চেয়ে যাওয়া টাকা বেশি, আর হাতে থাকা টাকা রাখা অংশের নিচে",
  "forecast.modelAccuracy": "সাধারণ অনুমানের চেয়ে আমরা কতটা কাছাকাছি",
  "forecast.noMetrics": "গোনা শেষ হলে এখানে মিলের সংখ্যা দেখা যাবে।",
  "forecast.table": "দিন ধরে হিসাব",
  "forecast.tableSub": "১৪ দিন, একটা একটা করে",
  "forecast.planSavingsPrompt": "যা থাকবে তা দিয়ে সঞ্চয়ের পরিকল্পনা করবেন?",

  "plan.headerTag": "মাসে মাসে সঞ্চয়",
  "plan.title": "আপনার সঞ্চয় পরিকল্পনা",
  "plan.subtitle":
    "লক্ষ্য আর মাস লিখুন। গড় নয় — আপনার হাতে যা থাকে, তা দিয়েই হিসাব।",
  "plan.goal": "লক্ষ্যের পরিমাণ (৳)",
  "plan.months": "কয় মাস",
  "plan.submit": "পরিকল্পনা হিসাব করুন",
  "plan.calculating": "পরিকল্পনা হিসাব করা হচ্ছে…",
  "plan.feasible": "এই পরিকল্পনা চলবে",
  "plan.infeasible": "এখনকার জন্য লক্ষ্যটা বড়",
  "plan.requiredMonthly": "প্রতি মাসে সঞ্চয় দরকার",
  "plan.feasibleMonthly": "মাসে জমাতে পারবেন",
  "plan.surplus": "মাসে হাতে থাকা বাড়তি টাকা",
  "plan.buffer": "বিপদের জন্য রাখা টাকা",
  "plan.arithmetic": "হিসাবের বিবরণ",
  "plan.tradeOffs": "হিসাব মেলানোর বিকল্প উপায়",
  "plan.pressureWarning":
    "মাসের শেষে কিছু দিন টান পড়বে। নিরাপদ টাকায় হাত দেবেন না।",
  "plan.action.reduce": "লক্ষ্যের টাকা কমান",
  "plan.action.delay": "কয়েক মাস সময় বাড়ান",
  "plan.action.switch": "ফি বাঁচানোর উপায়",
  "plan.action.do_nothing": "কোনো পরিবর্তন করব না",
  "plan.reviewForecastPrompt": "আগামী ১৪ দিন দেখতে চান?",

  "spending.headerTag": "খরচ",
  "spending.title": "টাকা কোথায় গেল",
  "spending.subtitle": "সম্প্রতি কোথায় টাকা গেছে দেখুন, আর কোন ফি এড়ানো যায় তা জানুন।",
  "spending.loading": "আপনার খরচ দেখা হচ্ছে…",
  "spending.summary": "টাকার হিসাব",
  "spending.cashOutCount": "ক্যাশ-আউট সংখ্যা",
  "spending.cashOutCountSub": "গত ৩০ দিনে মোট কতবার ক্যাশ-আউট করেছেন",
  "spending.cashOutVolume": "ক্যাশ-আউট করা মোট টাকা",
  "spending.cashOutVolumeSub": "দোকান বা এজেন্ট থেকে তোলা নগদ টাকা",
  "spending.feePaid": "দেওয়া ফি",
  "spending.feePaidSub": "ক্যাশ-আউটে কাটা ফি (১.৮৫%)",
  "spending.singleRuleTop": "যোগ করে মিলিয়ে দেওয়া",
  "spending.anomalies": "অস্বাভাবিক লেনদেন",
  "spending.anomaliesNone": "এই দিনগুলোতে অস্বাভাবিক কিছু পাওয়া যায়নি।",
  "spending.reason": "কেন চোখে পড়ল",
  "spending.action": "আপনি যা করতে পারেন",
  "spending.feeSwitch": "ফি বাঁচানোর উপায়",
  "spending.feeSwitchDesc": "এজেন্টের কাছে ক্যাশ-আউট না করে দোকানে সরাসরি বাংলা কিউআরে দিলে বা অ্যাপে পাঠালে ক্যাশ-আউট ফি বাঁচবে।",
  "spending.doNothingOutcome": "বদল না করলে প্রতি মাসে প্রায় {fee} ক্যাশ-আউট ফিতে চলে যাবে।",
  "spending.potentialSaving": "মাসে বাঁচবে",
  "spending.currentFee": "এখন মাসে যে ফি দেন",
  "spending.altChannel": "অন্য উপায়",
  "spending.altFee": "ওই উপায়ে ফি",
  "spending.adoption": "কারা ব্যবহার করতে পারে",
  "spending.perMonth": "প্রতি মাসে",
  "spending.times": "বার",
  "spending.daysUnit": "দিন",
  "spending.warningStripTitle": "সাবধান",
  "spending.warningStripText": "২৮–৩১ তারিখ ব্যয়ের সম্ভাব্য চাপের সময়।",
  "spending.banglaQrTitle": "দোকানে কিউআরে দিন: ফি নেই",
  "spending.banglaQrDesc": "১ অক্টোবর ২০২৬ থেকে দোকানে কিউআরে দিলে আপনার ফি ০% — ক্যাশ-আউটের ১.৪% নয়। সরকারি বোনাস ব্যাংক পায়, আপনি নন। (উৎস: বাংলাদেশ ব্যাংক)",
  "spending.banglaQrNoFee": "আপনার কোনো ফি নেই",
  "spending.banglaQrEligible": "{count}টি ছোট ক্যাশ-আউট (মোট {volume}) দোকানে কিউআরে দিলে ফি লাগত না।",
  "spending.banglaQrCustomerBenefit": "দোকানে কিউআর: ০% ফি। ক্যাশ-আউট: ১.৪% ফি।",
  "spending.banglaQrUpayBenefit": "এই পেমেন্টে ০.২০% সরকারি বোনাস ব্যাংক পায়, আপনি নন।",
  "spending.banglaQrAntiMisuseTitle": "আসল কেনাকাটায় কিউআর",
  "spending.banglaQrAntiMisuseText": "২,০০০ টাকার কাছে লেনদেন ভেঙে বা দোকান থেকে নগদ নেবেন না — নিয়ম ভাঙলে শাস্তি হতে পারে।",

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

  "tips.headerTag": "আপনার জন্য পরামর্শ",
  "tips.title": "আপনার সাথে মানান পরামর্শ",
  "tips.subtitle": "আপনার টাকার অভ্যাস দেখে বাছাই করা পরামর্শ।",
  "tips.loading": "আপনার জন্য পরামর্শ খোঁজা হচ্ছে…",
  "tips.whyThisTip": "কেন এই পরামর্শ?",
  "tips.suggestedAction": "এটা চেষ্টা করতে পারেন",
  "tips.none": "এখন সতর্ক করার মতো কিছু নেই। আপনার অভ্যাস ঠিক আছে।",
  "tips.coachAdvice": "হিসাব থেকে পরামর্শ",
  "tips.coreGuidance": "মনে রাখার মূল কথা",
  "tips.unavailable": "এখন নতুন পরামর্শ পাওয়া যাচ্ছে না। সংযোগ দেখে আবার চেষ্টা করুন।",
  "tips.stampRule": "নিয়ম থেকে",
  "tips.stampForecast": "আগামী দিন থেকে",
  "tips.stampPlan": "পরিকল্পনার জন্য",

  "signal.headerTag": "নিয়মিত অভ্যাস",
  "signal.title": "আপনার অভ্যাস কতটা নিয়মিত?",
  "signal.subtitle": "টাকার অভ্যাস কতটা নিয়মিত, তা তিনটি ধাপে।",
  "signal.loading": "অভ্যাস দেখা হচ্ছে…",
  "signal.band": "আপনার ধাপ",
  "signal.factors": "যে কারণে এই মূল্যায়ন",
  "signal.improvements": "উন্নতি করার সহজ উপায়",
  "signal.improves": "ভালো করে",
  "signal.weakens": "ক্ষতি করে",
  "signal.comingSoon": "গোনা শেষ হলে এখানে আপনার ধাপ দেখা যাবে।",
  "signal.educationalBadge": "শুধু তথ্য",
  "signal.educationalNote": "এটি শুধু শেখায়। ঋণের সিদ্ধান্ত কখনো দেয় না।",
  "signal.guaranteeTitle": "আমাদের কথা",
  "signal.bandSteady": "স্থিতিশীল",
  "signal.bandBuilding": "শুরু",
  "signal.bandStrong": "দৃঢ়",
  "signal.unavailable": "এখন আপনার ধাপ পাওয়া যাচ্ছে না। সংযোগ দেখে আবার চেষ্টা করুন।",
  "signal.bandRating": "মোটামুটি নিয়মিত",
  "signal.bandRatingBuilding": "সবে শুরু",
  "signal.bandRatingStrong": "খুব নিয়মিত",
  "signal.step1": "১. শুরু",
  "signal.step2": "২. স্থিতিশীল",
  "signal.step3": "৩. দৃঢ়",
  "signal.logisticRegression": "ধারাবাহিকতা যাচাই",

  "metrics.headerTag": "স্বচ্ছতা ও মূল্যায়ন",
  "metrics.title": "অ্যাপ কেমন করছে?",
  "metrics.subtitle": "সাধারণ অনুমানের সাথে আমাদের গোনার তুলনা।",
  "metrics.loading": "আমরা কেমন করছি তা গোনা হচ্ছে…",
  "metrics.forecast": "স্মার্ট ক্যাশ-ফ্লো পূর্বাভাস",
  "metrics.forecastBadge": "১৪ দিনের পূর্বাভাস",
  "metrics.model": "আমাদের হিসাব",
  "metrics.baseline": "সাধারণ অনুমান",
  "metrics.mae": "MAE",
  "metrics.maeLong": "গড় ভুল",
  "metrics.rmse": "বড় ভুলের হিসাব",
  "metrics.improvement": "ভালো হয়েছে",
  "metrics.anomaly": "অস্বাভাবিক লেনদেন শনাক্তকরণ",
  "metrics.anomalyBadge": "স্বয়ংক্রিয় শনাক্তকরণ",
  "metrics.anomalyDesc": "আপনার স্বাভাবিকের চেয়ে অনেক বড় পেমেন্ট বা অদ্ভুত সময়ের লেনদেন খুঁজে বের করে — অন্যের নয়, আপনার নিজের অভ্যাস থেকে শেখা।",
  "metrics.signal": "নিয়মিত অভ্যাস যাচাই",
  "metrics.fairness": "সবার জন্য নিরপেক্ষতা",
  "metrics.fairnessDesc": "৫ ধরনের কাজ আর ১০ জেলায় যাচাই করা — শহর-গ্রাম সবাই একই মান পায়।",
  "metrics.demoAudit": "অনুশীলন যাচাই",
  "metrics.comingSoon": "গোনা শেষ হলে এখানে নিরপেক্ষতার হিসাব দেখা যাবে।",
  "metrics.fairnessTable": "সবার জন্য সমান ফল",
  "metrics.dimension": "কোন বিষয়ে",
  "metrics.group": "কারা",
  "metrics.metric": "যা গোনা হয়েছে",
  "metrics.value": "ফল",
  "metrics.gap": "পার্থক্য",
  "metrics.impactTitle": "এই অ্যাপ যা বদলেছে",
  "metrics.precision": "ঠিক ধরা",
  "metrics.recall": "ধরতে পারা",
  "metrics.f1": "ধরার মাত্রা",
  "metrics.auc": "কতটা সঠিক",
  "metrics.outOf100": "১০০-এর মধ্যে",
  "metrics.requestsUnit": "টি প্রশ্ন",
  "metrics.inflow": "আসা টাকা (১৪ দিন)",
  "metrics.outflow": "যাওয়া টাকা (১৪ দিন)",
  "metrics.net": "থাকছে (১৪ দিন)",
  "metrics.macroContext":
    "আশপাশের চিত্র: ১ জুলাই থেকে দোকানের কিউআর পেমেন্ট সংখ্যায় ৩.৫ গুণ, টাকায় ৫ গুণ বেড়ে দৈনিক ৳১৪৩.৫৪ কোটিতে পৌঁছেছে (উৎস: বাংলাদেশ ব্যাংক, সেপ্টেম্বর ২০২৬)।",
  "metrics.institutionalCaveat":
    "একটি নিয়ম: ০.২০% সরকারি বোনাস শুধু জাতীয় নেটওয়ার্ক (NPSB) দিয়ে ২,০০০ টাকা পর্যন্ত পেমেন্টে মেলে। বড় পেমেন্টে দোকানের সাধারণ নিয়ম চলে।",
  "metrics.notesTitle": "এই সংখ্যাগুলো যা বলে না",
  "forecast.driversTitle": "কেন ওই দিনগুলো কঠিন",
  "forecast.driversBadge": "কারণ",
  "forecast.increasesOutflow": "খরচ বাড়ায়",
  "forecast.decreasesOutflow": "খরচ কমায়",

  "footer.ledgerSystem": "সঞ্চয় Copilot",
  "footer.demoDisclaimer": "অনুশীলনের তথ্য — সব সংখ্যা বানানো।",

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
    return lang === "bn" ? "স্মার্ট হিসাব" : "Smart estimate";
  }
  if (lower.includes("trailing_average") || lower.includes("baseline") || lower.includes("average")) {
    return lang === "bn" ? "সাধারণ গড়" : "Simple Average";
  }
  if (lower.includes("isolation")) {
    return lang === "bn" ? "স্বয়ংক্রিয় শনাক্তকরণ" : "Auto Detection";
  }
  if (lower.includes("logistic")) {
    return lang === "bn" ? "ধারাবাহিকতা যাচাই" : "Consistency check";
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
    Building: "শুরু",
    Steady: "স্থিতিশীল",
    "System Computed": "স্বয়ংক্রিয় হিসাব",
    "Rule Verified": "✓ যাচাই করা",
    "Plain Language": "সহজ ভাষায়",
    "Logistic Regression": "ধারাবাহিকতা যাচাই",
    "Isolation Forest": "অস্বাভাবিক খোঁজার পদ্ধতি",
    LightGBM: "স্মার্ট হিসাব",
    Educational: "শুধু তথ্য",
  };
  return map[status] ?? status;
}

