"use client";

import { useEffect, useState } from "react";
import TopBar from "@/components/TopBar";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import InsightCard from "@/components/InsightCard";
import DoNothingToggle from "@/components/DoNothingToggle";
import Stamp from "@/components/Stamp";
import { fetchExplain, fetchAnomalies, fetchSavingsPlan, trackEvent } from "@/lib/api";
import type { ExplainResponse, FeeSwitchSuggestion, SavingsPlanResponse } from "@/lib/api";
import { useLanguage } from "@/components/LangToggle";
import { FeedbackWidget } from "@/components/FeedbackWidget";
import { formatBDT, formatDigits, sanitizeBullet } from "@/lib/i18n";

export default function TipsPage() {
  const { lang, tr } = useLanguage();
  const [explainRes, setExplainRes] = useState<ExplainResponse | null>(null);
  const [feeSwitch, setFeeSwitch] = useState<FeeSwitchSuggestion | null>(null);
  const [plan, setPlan] = useState<SavingsPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionStates, setActionStates] = useState<
    Record<string, "idle" | "accepted" | "rejected" | "remind_later" | "completed">
  >({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const defaultTipsFallback: ExplainResponse = {
      intent: "tips",
      answer_bn: "আপনার আচরণের উপর ভিত্তি করে ৩টি টিপ বাছাই করা হয়েছে। প্রতিটি টিপের সাথে কারণটিও দেওয়া আছে।",
      answer_en: "These tips were chosen from your own behaviour. Each one shows the trigger that selected it.",
      bullets_bn: [
        "অ্যাপ ট্রান্সফারে টাকা পাঠান: ক্যাশ-আউট এই ফিরে সবচেয়ে বেশি। একই টাকা অ্যাপ ট্রান্সফারে গেলে একটা মাপযোগ্য অংশ আপনারই থাকে। (কারণ: মাসে ক্যাশ-আউট সংখ্যা ৫ বার (সাধারণত ৩ বারের বেশি হলে ফি বাড়ে))",
        "ক্যাশ-আউট নয়, মার্চেন্ট পেমেন্টে দিন: খরচের বড় অংশ ক্যাশ হয়ে বেরোলে, যে টাকা আপনি খরচই করতেন তার উপর ফি দিতে হয়। মার্চেন্ট পেমেন্টে সাধারণত ফি লাগে না। (কারণ: খরচের ৪৯% ক্যাশে হয় (সাধারণত ৪০% এর বেশি হলে ফি বাড়ে))",
        "বড় ক্যাশ-আউটের পরিকল্পনা করুন: বড় ক্যাশ-আউট সাধারণত পরিকল্পিত কেনাকাটা। সস্তা চ্যানেলে করলে কিছুই লাগে না, বড় টাকায় সঞ্চয় হয়। (কারণ: মাসিক ক্যাশ-আউট পরিমাণ ৳১৮,১৪০ (৳৮,০০০ এর বেশি))",
        "এটি ঋণ পাওয়ার সিদ্ধান্ত নয়। কোনো কিছু কেনা বা ধার নেওয়ার পরামর্শ দেওয়া হয় না।",
      ],
      bullets_en: [
        "Send money via app transfer: Cash-out fee is highest. Sending the same money via app transfer keeps a measurable share with you. (Reason: Cash-out count 5 times/month (typically above 3 increases fees))",
        "Merchant payment instead of cash-out: When a major part of spending is cash, you pay fees on what you would spend anyway. Merchant payment typically has 0 fee. (Reason: 49% of spending is in cash (typically above 40% increases fees))",
        "Plan large cash-outs: Large cash-outs are usually planned purchases. Doing them via low-cost channels saves more. (Reason: Monthly cash-out volume ৳18,140 (above ৳8,000))",
        "This is not a loan eligibility decision. We never suggest buying anything or taking a loan.",
      ],
      source: "template",
      blocked: false,
      provenance: {
        prediction:
          lang === "bn"
            ? "আপনার লেনদেনের নির্ভরযোগ্য খতিয়ান হিসাবের ভিত্তিতে পরামর্শটি সাজানো।"
            : "Verified guidance calculated directly from your transaction ledger.",
        assumption:
          lang === "bn"
            ? "আপনার পূর্বের লেনদেন ও ক্যাশ-আউট তথ্যের নির্ভুল পরিসংখ্যান ব্যবহার করা হয়েছে।"
            : "Calculated from your past transactions and verified spending patterns.",
        explanation:
          lang === "bn"
            ? "এই পরামর্শের প্রতিটি সংখ্যা ও হিসাব আপনার নিজস্ব লেনদেনের ইতিহাস থেকে প্রাপ্ত।"
            : "Every figure in this recommendation is derived directly from your personal transaction history.",
        source: "template",
      },
    };

    Promise.allSettled([
      fetchExplain({
        message:
          lang === "bn"
            ? "আমার লেনদেনের টিপস ও পরামর্শ দিন"
            : "Give me money tips and advice",
        language: lang,
      }),
      fetchAnomalies({ window_days: 30, limit: 20 }),
      fetchSavingsPlan({ goal_bdt: 30000, months: 6 }),
    ]).then(([explainResult, anomResult, planResult]) => {
      if (cancelled) return;

      if (explainResult.status === "fulfilled" && explainResult.value.intent === "tips") {
        setExplainRes(explainResult.value);
      } else {
        setExplainRes(defaultTipsFallback);
      }
      if (anomResult.status === "fulfilled" && anomResult.value.fee_switch) {
        setFeeSwitch(anomResult.value.fee_switch);
      }
      if (planResult.status === "fulfilled") {
        setPlan(planResult.value);
      }
      setLoading(false);

      // Track recommendation_shown for visible recommendations
      trackEvent("recommendation_shown", { recommendation_id: "tip-month-end-expenses", feature: "tips" });
      if (anomResult.status === "fulfilled" && (anomResult.value.fee_switch?.cash_out_count ?? 0) > 0) {
        trackEvent("recommendation_shown", { recommendation_id: "tip-fee-switch", feature: "tips" });
      }
      if (planResult.status === "fulfilled") {
        trackEvent("recommendation_shown", { recommendation_id: "tip-savings-assessment", feature: "tips" });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [lang]);

  const handleTryThis = (tipId: string) => {
    trackEvent("recommendation_accepted", { recommendation_id: tipId, feature: "tips" });
    setActionStates((prev) => ({ ...prev, [tipId]: "accepted" }));
  };

  const handleMarkCompleted = (tipId: string) => {
    trackEvent("recommendation_action_completed", { recommendation_id: tipId, feature: "tips" });
    setActionStates((prev) => ({ ...prev, [tipId]: "completed" }));
  };

  const handleNotRelevant = (tipId: string) => {
    trackEvent("recommendation_rejected", { recommendation_id: tipId, feature: "tips" });
    setActionStates((prev) => ({ ...prev, [tipId]: "rejected" }));
  };

  const handleRemindLater = (tipId: string) => {
    setActionStates((prev) => ({ ...prev, [tipId]: "remind_later" }));
  };

  // GAP-10: no ?? fallbacks. Without live fee data there is no fee card —
  // an explicit unavailable note instead of 5 / 3500 / 324 guesses.
  const feeCard =
    feeSwitch && feeSwitch.cash_out_count > 0
      ? (() => {
          const cashOutCount = feeSwitch.cash_out_count;
          const avgAmount = feeSwitch.cash_out_volume_bdt / feeSwitch.cash_out_count;
          const potentialSaving = feeSwitch.potential_saving_bdt;
          const qrCount = feeSwitch.bangla_qr_eligible_count ?? 0;
          const tip1DescBn = qrCount > 0
            ? `আপনি মাসে ${formatDigits(
                String(cashOutCount),
                "bn"
              )} বার গড়ে ${formatBDT(
                avgAmount,
                "bn"
              )} টাকা ক্যাশ-আউট করেন, যার মধ্যে ${formatDigits(
                String(qrCount),
                "bn"
              )}টি লেনদেন ২,০০০ টাকার মধ্যে। ১ অক্টোবর ২০২৬ তারিখের নির্দেশনা অনুযায়ী দোকানে বাংলা কিউআরে অর্থ পরিশোধ করলে ক্যাশ-আউট ফি ০%। এতে মাসে আনুমানিক ${formatBDT(
                potentialSaving,
                "bn"
              )} টাকা সাশ্রয় হতে পারে।`
            : `আপনি মাসে ${formatDigits(
                String(cashOutCount),
                "bn"
              )} বার গড়ে ${formatBDT(
                avgAmount,
                "bn"
              )} টাকা ক্যাশ-আউট করেন। ঘন ঘন ক্যাশ-আউট না করে এক বা দুইবারে উত্তোলন করলে অথবা সরাসরি অ্যাপের মাধ্যমে লেনদেন করলে প্রতি মাসে আনুমানিক ${formatBDT(
                potentialSaving,
                "bn"
              )} টাকা সাশ্রয় হতে পারে।`;
          const tip1DescEn = qrCount > 0
            ? `You make approximately ${cashOutCount} cash-out transactions per month averaging ${formatBDT(
                avgAmount,
                "en"
              )}. Under the 1 October 2026 regulation, merchant payments via Bangla QR incur 0% fee (${qrCount} of your transactions qualify under the ৳2,000 threshold), saving an estimated ${formatBDT(
                potentialSaving,
                "en"
              )} per month.`
            : `You make approximately ${cashOutCount} cash-out transactions per month averaging ${formatBDT(
                avgAmount,
                "en"
              )}. Consolidating withdrawals into fewer transactions or paying digitally can save an estimated ${formatBDT(
                potentialSaving,
                "en"
              )} per month.`;
          return {
            id: "tip-fee-switch",
            titleBn: qrCount > 0 ? "দোকানে ক্যাশ-আউটের বদলে বাংলা কিউআর" : "ক্যাশ-আউটের সংখ্যা কমান",
            titleEn: qrCount > 0 ? "Use Bangla QR instead of cash-out" : "Consolidate cash-out transactions",
            descBn: tip1DescBn,
            descEn: tip1DescEn,
            tagBn: "বাংলা কিউআর",
            tagEn: "Bangla QR",
            stampKey: "tips.stampRule" as const,
          };
        })()
      : null;

  // Live savings verdict for the worked example goal — never a hardcoded
  // claim. Unavailable instead of invented when the API is down.
  const planCard = plan
    ? {
        id: "tip-savings-assessment",
        titleBn: "সঞ্চয়ের লক্ষ্য মূল্যায়ন",
        titleEn: "Savings goal assessment",
        descBn: plan.feasible
          ? `উদাহরণ (৬ মাসে ৳৩০,০০০): জরুরি প্রয়োজনের অর্থ সংরক্ষণের পর প্রতি মাসে ${formatBDT(plan.feasible_monthly_bdt, "bn")} টাকা সঞ্চয় সম্ভব — এই লক্ষ্যটি বাস্তবসম্মত।`
          : `উদাহরণ (৬ মাসে ৳৩০,০০০): বর্তমানে প্রতি মাসে ${formatBDT(plan.feasible_monthly_bdt, "bn")} টাকা সঞ্চয় সম্ভব — সঞ্চয়ের লক্ষ্য কমান অথবা সময়সীমা বাড়ান।`,
        descEn: plan.feasible
          ? `Worked example (৳30,000 in 6 months): after reserving safety funds, an estimated ${formatBDT(plan.feasible_monthly_bdt, "en")} per month can be saved — this goal is feasible.`
          : `Worked example (৳30,000 in 6 months): currently only ${formatBDT(plan.feasible_monthly_bdt, "en")} per month can be saved — consider reducing the target or extending the timeline.`,
        tagBn: "সঞ্চয়",
        tagEn: "Savings",
        stampKey: "tips.stampPlan" as const,
      }
    : null;

  const curatedTips = [
    ...(feeCard ? [feeCard] : []),
    {
      id: "tip-month-end-expenses",
      titleBn: "মাসের শেষ দিনগুলোর ব্যয় ব্যবস্থাপনা",
      titleEn: "Manage month-end expenses",
      descBn:
        "মাসের শেষ সপ্তাহে নিয়মিত বিল ও নগদ খরচের চাপ বাড়ে। মাসের মাঝামাঝি থেকে প্রতিদিন ৳৫০ আলাদা রাখলে মাস শেষে আর্থিক চাপ কমে।",
      descEn:
        "Bills and cash expenses typically peak during the final week of the month. Setting aside ৳50 daily from mid-month prevents month-end cash shortages.",
      tagBn: "ক্যাশ-ফ্লো",
      tagEn: "Cash Flow",
      stampKey: "tips.stampForecast" as const,
    },
    ...(planCard ? [planCard] : []),
  ];
  const dataMissing = !loading && (!feeSwitch || !plan);

  return (
    <>
      <TopBar />
      <main className="space-y-6">
        <header className="border-b border-[#D8CFBB] pb-4 space-y-2">
          <div className="text-xs font-mono text-[#0054A6] uppercase tracking-wider flex items-center gap-2">
            <span>{tr("tips.headerTag")}</span>
            <span>•</span>
            <Stamp variant="blue">{tr("stamp.easyExplain")}</Stamp>
          </div>
          <h1 className="font-serif-bn font-bold text-3xl md:text-4xl text-[#1E1B16] tracking-tight">
            {tr("tips.title")}
          </h1>
          <p className="text-base text-[#6A6355] leading-relaxed font-hind">
            {tr("tips.subtitle")}
          </p>
        </header>

        <NotADecisionBanner />

        {/* Live Assistant Response if available */}
        {loading && (
          <div className="bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] p-6 text-center">
            <p className="font-mono text-sm text-[#6A6355] animate-pulse">
              {tr("tips.loading")}
            </p>
          </div>
        )}

        {explainRes && !loading && (
          <div className="bg-[#F1F4F9] border border-[#D8CFBB] rounded-[6px] p-5 md:p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#D8CFBB] pb-2">
              <span className="text-xs font-mono uppercase text-[#0054A6] font-bold">
                {tr("tips.coachAdvice")}
              </span>
              <Stamp variant="blue">
                {explainRes.source === "llm"
                  ? (lang === "bn" ? "এআই লিখেছে" : "Written by AI")
                  : tr("stamp.computed")}
              </Stamp>
            </div>

            <p className="font-serif-bn text-base md:text-lg font-bold text-ink leading-snug">
              {sanitizeBullet(lang === "bn" ? explainRes.answer_bn : explainRes.answer_en, lang)}
            </p>

            {((lang === "bn" ? explainRes.bullets_bn : explainRes.bullets_en) || []).length > 0 && (
              <ul className="space-y-1.5 pt-2 border-t border-rule font-hind text-sm text-ink-muted list-disc list-inside">
                {(lang === "bn" ? explainRes.bullets_bn : explainRes.bullets_en).map((bullet, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {sanitizeBullet(bullet, lang)}
                  </li>
                ))}
              </ul>
            )}

            {explainRes.provenance && (
              <InsightCard
                title={tr("common.howCalculated")}
                provenance={explainRes.provenance}
              />
            )}
          </div>
        )}

        {/* Curated Khata Advice - Ruled list, not separate cards */}
        <div className="space-y-4">
          <div className="border-b border-rule pb-2">
            <h2 className="font-serif-bn font-bold text-xl text-ink m-0">
              {tr("tips.coreGuidance")}
            </h2>
          </div>

          {dataMissing && (
            <div className="bg-surface/50 border-t border-b border-rule p-5">
              <p className="text-sm text-ink-muted leading-relaxed font-hind">
                {tr("tips.unavailable")}
              </p>
            </div>
          )}

          <div className="border-t border-b border-rule bg-surface/30 divide-y divide-rule/60">
            {curatedTips.map((tip, idx) => {
              const state = actionStates[tip.id] || "idle";
              return (
                <div
                  key={idx}
                  className="p-5 space-y-3 hover:bg-surface/60 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <Stamp variant="ink">
                      {lang === "bn" ? tip.tagBn : tip.tagEn}
                    </Stamp>
                    <span className="text-xs font-mono text-ink-muted">
                      [{tr(tip.stampKey)}]
                    </span>
                  </div>

                  <h3 className="font-serif-bn font-bold text-lg text-ink m-0">
                    {lang === "bn" ? tip.titleBn : tip.titleEn}
                  </h3>

                  <p className="text-sm text-ink-muted leading-relaxed font-hind">
                    {lang === "bn" ? tip.descBn : tip.descEn}
                  </p>

                  {/* Recommendation action tracking: shown -> accepted/rejected -> action_completed */}
                  <div className="pt-2 border-t border-rule/50 flex flex-wrap items-center justify-between gap-2">
                    {state === "completed" ? (
                      <span className="text-xs font-semibold text-[#0054A6] flex items-center gap-1.5 font-hind">
                        <span className="inline-block w-2 h-2 rounded-full bg-[#0054A6]" />
                        {lang === "bn" ? "পদক্ষেপ সম্পন্ন হয়েছে ✓" : "Action completed ✓"}
                      </span>
                    ) : state === "accepted" ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs text-[#1E1B16] font-medium font-hind">
                          {lang === "bn" ? "গ্রহণ করেছেন • কাজ শেষ হলে চিহ্নিত করুন:" : "Accepted • Mark when done:"}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleMarkCompleted(tip.id)}
                          className="px-3 py-1.5 bg-[#0054A6] hover:bg-[#003E7E] text-white text-xs font-medium rounded-[6px] transition-colors focus:outline-none focus:ring-1 focus:ring-[#0054A6]"
                        >
                          {lang === "bn" ? "✓ সম্পন্ন করেছি" : "✓ Mark completed"}
                        </button>
                      </div>
                    ) : state === "rejected" ? (
                      <span className="text-xs text-[#6A6355] font-hind">
                        {lang === "bn" ? "প্রাসঙ্গিক নয় হিসেবে চিহ্নিত" : "Marked as not relevant"}
                      </span>
                    ) : state === "remind_later" ? (
                      <span className="text-xs text-[#6A6355] font-hind">
                        {lang === "bn" ? "পরে মনে করিয়ে দেওয়া হবে" : "Will remind you later"}
                      </span>
                    ) : (
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleTryThis(tip.id)}
                          className="px-3 py-1.5 border border-[#0054A6] text-[#0054A6] hover:bg-[#0054A6] hover:text-white text-xs font-medium rounded-[6px] transition-colors focus:outline-none focus:ring-1 focus:ring-[#0054A6]"
                        >
                          {lang === "bn" ? "এটি চেষ্টা করব" : "I'll try this"}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleNotRelevant(tip.id)}
                          className="px-2.5 py-1.5 border border-[#D8CFBB] text-[#6A6355] hover:text-[#1E1B16] hover:border-[#1E1B16] text-xs font-medium rounded-[6px] transition-colors focus:outline-none focus:ring-1 focus:ring-[#1E1B16]"
                        >
                          {lang === "bn" ? "প্রাসঙ্গিক নয়" : "Not relevant"}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRemindLater(tip.id)}
                          className="px-2.5 py-1.5 border border-[#D8CFBB] text-[#6A6355] hover:text-[#1E1B16] hover:border-[#1E1B16] text-xs font-medium rounded-[6px] transition-colors focus:outline-none focus:ring-1 focus:ring-[#1E1B16]"
                        >
                          {lang === "bn" ? "পরে মনে করিয়ে দিন" : "Remind me later"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Feedback Loop */}
        <FeedbackWidget feature="tips" language={lang} />

        <DoNothingToggle
          costBdt={feeSwitch?.potential_saving_bdt ?? null}
          outcome={
            feeSwitch
              ? (lang === "bn"
                  ? `এই পরামর্শ গ্রহণ না করলে প্রতি মাসে আনুমানিক ${formatBDT(feeSwitch.potential_saving_bdt, lang)} টাকা অপ্রয়োজনীয় ফি বাবদ ব্যয় অব্যাহত থাকবে।`
                  : `If no action is taken, approximately ${formatBDT(feeSwitch.potential_saving_bdt, lang)} in avoidable fees will continue to be incurred each month.`)
              : (lang === "bn"
                  ? "বর্তমানে কোনো অতিরিক্ত ফি বাবদ খরচ চিহ্নিত হয়নি; তবে পূর্বপরিকল্পিত সঞ্চয় বিলম্বিত হতে পারে।"
                  : "No additional fee expense was identified; however, planned savings may be delayed.")
          }
        />
      </main>
    </>
  );
}
