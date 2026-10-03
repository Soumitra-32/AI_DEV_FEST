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
import { formatBDT, formatDigits } from "@/lib/i18n";

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
              )} করে ক্যাশ-আউট করেন, যার মধ্যে ${formatDigits(
                String(qrCount),
                "bn"
              )}টি ২,০০০ টাকার মধ্যে। ১ অক্টোবর ২০২৬ বাংলাদেশ ব্যাংক সংস্কারের ফলে দোকানে কেনাকাটায় ক্যাশ-আউটের বদলে সরাসরি বাংলা কিউআরে দিলে ০% ফি এবং মাসে আনুমানিক ${formatBDT(
                potentialSaving,
                "bn"
              )} সাশ্রয় হবে।`
            : `আপনি মাসে ${formatDigits(
                String(cashOutCount),
                "bn"
              )} বার গড়ে ${formatBDT(
                avgAmount,
                "bn"
              )} করে ক্যাশ-আউট করেন। বারবার ক্যাশ-আউট না করে একবার বা দুইবারে প্রয়োজনমতো তুললে বা সরাসরি অ্যাপ ট্রান্সফার করলে প্রতি মাসে আনুমানিক ${formatBDT(
                potentialSaving,
                "bn"
              )} ফি সাশ্রয় সম্ভব।`;
          const tip1DescEn = qrCount > 0
            ? `You cash out ~${cashOutCount} times/month averaging ${formatBDT(
                avgAmount,
                "en"
              )}. Under Bangladesh Bank's 1 Oct 2026 reform, merchant Bangla QR carries 0% fee (${qrCount} of your transactions are under the ৳2,000 cap), saving ~${formatBDT(
                potentialSaving,
                "en"
              )}/month.`
            : `You currently cash out ~${cashOutCount} times/month averaging ${formatBDT(
                avgAmount,
                "en"
              )}. Consolidating into 1-2 withdrawals or paying via app transfer can save ~${formatBDT(
                potentialSaving,
                "en"
              )} in monthly fees.`;
          return {
            titleBn: qrCount > 0 ? "দোকানে ক্যাশ-আউটের বদলে বাংলা কিউআর" : "ঘন ঘন ছোট ক্যাশ-আউট কমান",
            titleEn: qrCount > 0 ? "Pay Merchants by Bangla QR (0% Fee)" : "Consolidate Frequent Small Cash-Outs",
            descBn: tip1DescBn,
            descEn: tip1DescEn,
            tagBn: "বাংলা কিউআর",
            tagEn: "Bangla QR",
            stampKey: "tips.stampRule" as const,
          };
        })()
      : null;

  // Live savings verdict for the worked example goal — never a hardcoded
  // "fits" claim. Unavailable instead of invented when the API is down.
  const planCard = plan
    ? {
        titleBn: "সঞ্চয়ের বাস্তবসম্মত লক্ষ্য নির্ধারণ",
        titleEn: "Set a Realistic Surplus-Matched Goal",
        descBn: plan.feasible
          ? `উদাহরণ (৬ মাসে ৳৩০,০০০): উদ্বৃত্ত থেকে বাফার বাদে মাসে ${formatBDT(plan.feasible_monthly_bdt, "bn")} রাখা সম্ভব — লক্ষ্যটি মানানসই।`
          : `উদাহরণ (৬ মাসে ৳৩০,০০০): বর্তমান পূর্বাভাসে মাসে ${formatBDT(plan.feasible_monthly_bdt, "bn")} রাখা সম্ভব — লক্ষ্য বা সময়সীমা বদলাতে হবে।`,
        descEn: plan.feasible
          ? `Worked example (৳30,000 in 6 months): about ${formatBDT(plan.feasible_monthly_bdt, "en")}/month is keepable after the buffer — the goal fits.`
          : `Worked example (৳30,000 in 6 months): only about ${formatBDT(plan.feasible_monthly_bdt, "en")}/month is keepable — adjust the goal or timeline.`,
        tagBn: "সঞ্চয়",
        tagEn: "Savings",
        stampKey: "tips.stampPlan" as const,
      }
    : null;

  const curatedTips = [
    ...(feeCard ? [feeCard] : []),
    {
      titleBn: "২৮–৩১ তারিখের জন্য অগ্রিম বাফার রাখুন",
      titleEn: "Maintain Month-End Cash Buffer for Days 28–31",
      descBn:
        "মাসের শেষ সপ্তাহে আপনার মাসের বিল ও ক্যাশ খরচের চাপ বেশি থাকে। মাসের ১৫ তারিখ থেকেই দৈনিক ৳৫০ আলাদা রাখলে মাস শেষে টানাটানি পড়বে না।",
      descEn:
        "Outflows spike near month-end due to rent and utility schedules. Retaining a small safety buffer earlier prevents emergency borrowing.",
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
            <Stamp variant="muted">[{tr("stamp.easyExplain")}]</Stamp>
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
              <Stamp variant="muted">{explainRes.source}</Stamp>
            </div>

            <p className="font-serif-bn text-base md:text-lg font-bold text-ink leading-snug">
              {lang === "bn" ? explainRes.answer_bn : explainRes.answer_en}
            </p>

            {((lang === "bn" ? explainRes.bullets_bn : explainRes.bullets_en) || []).length > 0 && (
              <ul className="space-y-1.5 pt-2 border-t border-rule font-hind text-sm text-ink-muted list-disc list-inside">
                {(lang === "bn" ? explainRes.bullets_bn : explainRes.bullets_en).map((bullet, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {bullet}
                  </li>
                ))}
              </ul>
            )}

            {explainRes.provenance && (
              <InsightCard provenance={explainRes.provenance} />
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
                  ? `পরামর্শ অনুযায়ী ফি সাশ্রয় না করলে মাসে প্রায় ${formatBDT(feeSwitch.potential_saving_bdt, lang)} অপ্রয়োজনীয় খরচ হতে থাকবে।`
                  : `Ignoring fee-saving recommendations will continue to cost ~${formatBDT(feeSwitch.potential_saving_bdt, lang)}/month in avoidable fees.`)
              : (lang === "bn"
                  ? "কোনো আর্থিক ক্ষতি হিসাব করা যায়নি, তবে সঞ্চয়ের অভ্যাস তৈরি পিছিয়ে যাবে।"
                  : "No direct monetary loss computed, but financial habit building will be delayed.")
          }
        />
      </main>
    </>
  );
}
