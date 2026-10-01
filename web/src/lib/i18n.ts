/**
 * Bangla / English dictionary and formatting helpers.
 *
 * Kept as plain TypeScript (no JSX) so it can be imported from anywhere. The React
 * state that holds the chosen language lives in `components/LangToggle.tsx`
 * (`LanguageProvider` + `useLanguage`), which is wrapped around the app in
 * `app/layout.tsx`.
 *
 * Money is always printed with ৳ and, in Bangla, with Bangla numerals, because
 * that is how the people we are building for read numbers.
 */

export type Lang = "bn" | "en";

export const DEFAULT_LANG: Lang = "bn";

export const LANGUAGES: ReadonlyArray<{ code: Lang; label: string }> = [
  { code: "bn", label: "বাংলা" },
  { code: "en", label: "English" },
];

const en = {
  appName: "Shonchoy Copilot",
  tagline:
    "A Bangla-first coach that explains your transactions, plans a realistic saving goal, and warns you before the month-end squeeze — without selling you anything.",

  "nav.home": "Home",
  "nav.plan": "Savings plan",
  "nav.forecast": "Forecast",
  "nav.spending": "Spending",
  "nav.tips": "Tips",
  "nav.signal": "Consistency",
  "nav.metrics": "Evidence",

  "lang.switchTo": "Switch language",

  "status.title": "Connection and data",
  "status.checking": "Checking the API…",
  "status.apiReachable": "API reachable",
  "status.apiUnreachable": "API not reachable",
  "status.apiHint":
    "Start the backend with: uvicorn app.main:app --reload (from the backend folder), then reload this page.",
  "status.serviceVersion": "Service version",
  "status.database": "Dataset",
  "status.databaseReady": "ready",
  "status.databaseMissing": "missing",
  "status.users": "Users",
  "status.transactions": "Transactions",
  "status.generatedAt": "Generated",
  "status.features": "Modules switched on",
  "status.degraded": "Degraded",

  "identity.title": "You are signed in as",
  "identity.persona": "Persona",
  "identity.district": "District",
  "identity.incomeBand": "Income band",
  "identity.cohort": "Cohort",
  "identity.demoUser": "Demo user",

  "common.prediction": "Prediction",
  "common.assumption": "Assumption",
  "common.explanation": "Explanation",
  "common.source": "Source",
  "common.doNothing": "Do nothing",
  "common.doNothingCost": "Cost of doing nothing",
  "common.doNothingConfirm": "Yes, I understand",
  "common.doNothingDismiss": "Not now",
  "common.doNothingChosen": "You chose to do nothing. Nothing was changed.",
  "common.doNothingHint":
    "Every suggestion is yours to accept or ignore. Nothing happens without you.",

  "banner.notADecision":
    "This is not a loan eligibility decision. upay and lenders make no automatic decision from this.",

  "home.next.title": "What is ready",
  "home.next.body":
    "The data foundation (Phase 1), the API shell with frozen contracts (Phase 2), and the 14-day forecast with the savings solver (Phase 3) are in place. Open the plan or the forecast below.",

  "comingSoon.title": "Coming in a later phase",
  "comingSoon.phase3": "Forecast and savings plan (Phase 3)",
  "comingSoon.phase5": "Spending companion (Phase 5)",
  "comingSoon.phase7": "Tips and consistency signal (Phase 7)",
  "comingSoon.phase8": "Evidence and metrics (Phase 8)",

  "forecast.title": "Your next 14 days",
  "forecast.subtitle":
    "Inflow, outflow and the running balance, day by day, from the trained model.",
  "forecast.loading": "Working out your forecast…",
  "forecast.days": "Day",
  "forecast.inflow": "Money in",
  "forecast.outflow": "Money out",
  "forecast.net": "Net",
  "forecast.balance": "Balance",
  "forecast.pressureTitle": "Pressure days",
  "forecast.pressureNone": "No pressure day in this window — the wallet stays above the buffer.",
  "forecast.reasonNegativeNet": "money out is more than money in",
  "forecast.reasonBelowBuffer": "balance drops below the safety buffer",
  "forecast.reasonBoth": "money out is more than money in, and the balance falls under the buffer",
  "forecast.modelAccuracy": "Model accuracy vs the best simple rule",
  "forecast.noMetrics": "Model accuracy appears after the training run writes metrics.json.",
  "forecast.table": "Day by day",

  "plan.title": "Savings plan",
  "plan.subtitle":
    "Enter a goal and a time. We check it against your own forecasted surplus, not an average.",
  "plan.goal": "Goal amount (৳)",
  "plan.months": "How many months",
  "plan.submit": "Show my plan",
  "plan.calculating": "Solving the plan…",
  "plan.feasible": "This plan fits",
  "plan.infeasible": "This plan does not fit as stated",
  "plan.requiredMonthly": "Needed per month",
  "plan.feasibleMonthly": "You can keep per month",
  "plan.surplus": "Forecasted monthly surplus",
  "plan.buffer": "Safety buffer",
  "plan.arithmetic": "How we got here",
  "plan.tradeOffs": "Your options",
  "plan.pressureWarning":
    "Your forecast flags pressure days inside this plan. Keep the safety buffer.",
  "plan.action.reduce": "Reduce the goal",
  "plan.action.delay": "Take longer",
  "plan.action.switch": "Change spending",
  "plan.action.do_nothing": "Do nothing",

  "error.title": "Something went wrong",
  "error.retry": "Try again",
} as const;
type Dictionary = Record<TranslationKey, string>;

const bn: Dictionary = {
  appName: "সঞ্চয় কোপাইলট",
  tagline:
    "আপনার লেনদেন সহজ ভাষায় বুঝিয়ে দেওয়া, বাস্তবসম্মত সঞ্চয়ের পরিকল্পনা করা এবং মাস-শেষের টানাটানি আগেই জানিয়ে দেওয়ার বাংলা-প্রথম কোচ — কিছু বিক্রি না করেই।",
  "nav.home": "হোম",
  "nav.plan": "সঞ্চয় পরিকল্পনা",
  "nav.forecast": "পূর্বাভাস",
  "nav.spending": "খরচ",
  "nav.tips": "পরামর্শ",
  "nav.signal": "ধারাবাহিকতা",
  "nav.metrics": "প্রমাণ",
  "lang.switchTo": "ভাষা বদলান",
  "status.title": "সংযোগ ও তথ্য",
  "status.checking": "API পরীক্ষা করা হচ্ছে…",
  "status.apiReachable": "API-তে সংযোগ হয়েছে",
  "status.apiUnreachable": "API-তে সংযোগ হয়নি",
  "status.apiHint":
    "ব্যাকএন্ড চালু করুন: uvicorn backend.app.main:app --reload (রেপো রুট থেকে), তারপর পেজটি রিলোড করুন।",
  "status.serviceVersion": "সার্ভিস সংস্করণ",
  "status.database": "ডেটাসেট",
  "status.databaseReady": "প্রস্তুত",
  "status.databaseMissing": "নেই",
  "status.users": "ব্যবহারকারী",
  "status.transactions": "লেনদেন",
  "status.generatedAt": "তৈরি",
  "status.features": "চালু মডিউল",
  "status.degraded": "সীমিত",
  "identity.title": "আপনি সাইন ইন করেছেন",
  "identity.persona": "পেশা-ধরন",
  "identity.district": "জেলা",
  "identity.incomeBand": "আয়ের স্তর",
  "identity.cohort": "দল",
  "identity.demoUser": "ডেমো ব্যবহারকারী",
  "common.prediction": "পূর্বাভাস",
  "common.assumption": "অনুমান",
  "common.explanation": "ব্যাখ্যা",
  "common.source": "উৎস",
  "common.doNothing": "কিছুই করব না",
  "common.doNothingCost": "কিছু না করলে খরচ",
  "common.doNothingConfirm": "হ্যাঁ, বুঝেছি",
  "common.doNothingDismiss": "এখন নয়",
  "common.doNothingChosen": "আপনি কিছু না করাই বেছে নিয়েছেন। কিছুই বদলানো হয়নি।",
  "common.doNothingHint":
    "প্রতিটি পরামর্শ মানা বা এড়িয়ে যাওয়া আপনার হাতে। আপনার সম্মতি ছাড়া কিছুই হবে না।",
  "banner.notADecision":
    "এটি ঋণ পাওয়ার সিদ্ধান্ত নয়। এটি থেকে upay বা কোনো ঋণদাতা স্বয়ংক্রিয় সিদ্ধান্ত নেয় না।",
  "home.next.title": "যা প্রস্তুত",
  "home.next.body":
    "ডেটা ভিত্তি (প্রথম ধাপ), নির্ধারিত চুক্তিসহ API খোলস (দ্বিতীয় ধাপ), এবং ১৪ দিনের পূর্বাভাস ও সঞ্চয় সমাধান (তৃতীয় ধাপ) প্রস্তুত। নিচের পরিকল্পনা বা পূর্বাভাসে যান।",
  "comingSoon.title": "পরের ধাপে আসছে",
  "comingSoon.phase3": "পূর্বাভাস ও সঞ্চয় পরিকল্পনা (তৃতীয় ধাপ)",
  "comingSoon.phase5": "খরচ সহযোগী (পঞ্চম ধাপ)",
  "comingSoon.phase7": "পরামর্শ ও ধারাবাহিকতার সংকেত (সপ্তম ধাপ)",
  "comingSoon.phase8": "প্রমাণ ও মেট্রিক্স (অষ্টম ধাপ)",
  "forecast.title": "আপনার আগামী ১৪ দিন",
  "forecast.subtitle":
    "ঢাকা-টাকা আসা, যাওয়া এবং দিনশেষে ব্যালেন্স — প্রতিদিনের হিসাব, প্রশিক্ষিত মডেল থেকে।",
  "forecast.loading": "আপনার পূর্বাভাস হিসাব করা হচ্ছে…",
  "forecast.days": "দিন",
  "forecast.inflow": "টাকা আসছে",
  "forecast.outflow": "টাকা যাচ্ছে",
  "forecast.net": "নিট",
  "forecast.balance": "ব্যালেন্স",
  "forecast.pressureTitle": "টানাটানির দিন",
  "forecast.pressureNone": "এই সময়ে কোনো টানাটানির দিন নেই — ব্যালেন্স সেফটি বাফারের উপরেই থাকছে।",
  "forecast.reasonNegativeNet": "আসা টাকার চেয়ে যাওয়া টাকা বেশি",
  "forecast.reasonBelowBuffer": "ব্যালেন্স সেফটি বাফারের নিচে নেমে আসছে",
  "forecast.reasonBoth":
    "আসা টাকার চেয়ে যাওয়া টাকা বেশি, আর ব্যালেন্স বাফারের নিচে",
  "forecast.modelAccuracy": "সহজ নিয়মের তুলনায় মডেলের নির্ভুলতা",
  "forecast.noMetrics": "প্রশিক্ষণ চালিয়ে metrics.json লেখা হলে এখানে নির্ভুলতা দেখা যাবে।",
  "forecast.table": "দিন ধরে হিসাব",

  "plan.title": "সঞ্চয় পরিকল্পনা",
  "plan.subtitle":
    "লক্ষ্য আর সময় লিখুন। আমরা সাধারণ গড় নয়, আপনার নিজের পূর্বাভাসের ভিত্তিতে যাচাই করি।",
  "plan.goal": "লক্ষ্যের পরিমাণ (৳)",
  "plan.months": "কয় মাস",
  "plan.submit": "আমার পরিকল্পনা দেখান",
  "plan.calculating": "পরিকল্পনা হিসাব করা হচ্ছে…",
  "plan.feasible": "এই পরিকল্পনা চলবে",
  "plan.infeasible": "এই পরিকল্পনা এভাবে চলবে না",
  "plan.requiredMonthly": "মাসে দরকার",
  "plan.feasibleMonthly": "মাসে রাখতে পারবেন",
  "plan.surplus": "পূর্বাভাস অনুযায়ী মাসিক উদ্বৃত্ত",
  "plan.buffer": "সেফটি বাফার",
  "plan.arithmetic": "হিসাবটা এভাবে",
  "plan.tradeOffs": "আপনার উপায়গুলো",
  "plan.pressureWarning":
    "এই পরিকল্পনার মধ্যে আপনার পূর্বাভাসে টানাটানির দিন পড়ছে। সেফটি বাফারটা রেখে দিন।",
  "plan.action.reduce": "লক্ষ্য কমান",
  "plan.action.delay": "সময় বাড়ান",
  "plan.action.switch": "খরচ বদলান",
  "plan.action.do_nothing": "কিছুই করব না",

  "error.title": "কিছু একটা সমস্যা হয়েছে",
  "error.retry": "আবার চেষ্টা করুন",
};

const dictionaries: Record<Lang, Dictionary> = { en, bn };

export type TranslationKey = keyof typeof en;

export function t(lang: Lang, key: TranslationKey): string {
  return dictionaries[lang][key] ?? en[key];
}

const BN_DIGITS = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"];

/** 12345.6 -> "12,345" in English, "১২,৩৪৫" in Bangla (grouped Latin-style). */
export function formatInteger(value: number, lang: Lang): string {
  const grouped = Math.round(value).toLocaleString("en-US");
  if (lang === "en") return grouped;
  return grouped.replace(/[0-9]/g, (digit) => BN_DIGITS[Number(digit)]);
}

/** Money is always shown with ৳ ("৳৩,৬২৮" / "৳3,628"). */
export function formatBDT(value: number, lang: Lang): string {
  return `৳${formatInteger(value, lang)}`;
}


