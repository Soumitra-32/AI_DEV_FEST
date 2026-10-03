"use client";

import { useEffect, useState } from "react";
import TopBar from "@/components/TopBar";
import NotADecisionBanner from "@/components/NotADecisionBanner";
import InsightCard from "@/components/InsightCard";
import DoNothingToggle from "@/components/DoNothingToggle";
import Stamp from "@/components/Stamp";
import { useLanguage } from "@/components/LangToggle";
import { fetchExplain, fetchAnomalies, fetchSavingsPlan } from "@/lib/api";
import type { ExplainResponse, FeeSwitchSuggestion, SavingsPlanResponse } from "@/lib/api";
import { formatBDT, formatDigits, sanitizeBullet } from "@/lib/i18n";

export default function TipsPage() {
  const { lang, tr } = useLanguage();
  const [explainRes, setExplainRes] = useState<ExplainResponse | null>(null);
  const [feeSwitch, setFeeSwitch] = useState<FeeSwitchSuggestion | null>(null);
  const [plan, setPlan] = useState<SavingsPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.allSettled([
      fetchExplain({
        message:
          lang === "bn"
            ? "আমার ক্যাশ খরচ ও সঞ্চয়ের পরামর্শ দিন"
            : "Give me tips for savings and cash flow",
        language: lang,
      }),
      fetchAnomalies({ window_days: 30, limit: 20 }),
      // The savings card below renders from this live response — never from
      // hardcoded numbers (GAP-10). Demo goal shown as the worked example.
      fetchSavingsPlan({ goal_bdt: 30000, months: 6 }),
    ]).then(([explainResult, anomResult, planResult]) => {
      if (cancelled) return;

      if (explainResult.status === "fulfilled") {
        setExplainRes(explainResult.value);
      }
      if (anomResult.status === "fulfilled" && anomResult.value.fee_switch) {
        setFeeSwitch(anomResult.value.fee_switch);
      }
      if (planResult.status === "fulfilled") {
        setPlan(planResult.value);
      }
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [lang]);

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
        <header className="border-b border-rule pb-4 space-y-2">
          <div className="text-xs font-mono text-ink-muted uppercase tracking-wider flex items-center gap-2">
            <span>{tr("tips.headerTag")}</span>
            <span>•</span>
            <Stamp variant="muted">{tr("stamp.easyExplain")}</Stamp>
          </div>
          <h1 className="font-serif-bn font-bold text-3xl md:text-4xl text-ink tracking-tight">
            {tr("tips.title")}
          </h1>
          <p className="text-base text-ink-muted leading-relaxed font-hind">
            {tr("tips.subtitle")}
          </p>
        </header>

        <NotADecisionBanner />

        {/* Live Assistant Response if available */}
        {loading && (
          <div className="bg-surface/50 border-t border-b border-rule p-6 text-center">
            <p className="font-mono text-sm text-ink-muted animate-pulse">
              {tr("tips.loading")}
            </p>
          </div>
        )}

        {explainRes && !loading && (
          <div className="bg-surface/50 border-t border-b border-rule p-5 md:p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-rule pb-2">
              <span className="text-xs font-mono uppercase text-primaryGreen font-bold">
                {tr("tips.coachAdvice")}
              </span>
              <Stamp variant="muted">
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
            {curatedTips.map((tip, idx) => (
              <div
                key={idx}
                className="p-5 space-y-2 hover:bg-surface/60 transition-colors"
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
              </div>
            ))}
          </div>
        </div>

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
